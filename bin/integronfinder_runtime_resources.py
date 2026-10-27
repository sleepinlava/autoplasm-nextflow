#!/usr/bin/env python3
"""Fixed IntegronFinder2.0.5 native resource identity and explicit topology policy."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import stat
import sys

def resource(path):
    """Content/layout identity; reject incomplete, cyclic or special resources."""
    root = Path(path)
    entries = []

    def visit(p, relative, ancestors):
        link = os.readlink(p) if p.is_symlink() else None
        before = p.stat()
        mode = stat.S_IMODE(before.st_mode)
        if stat.S_ISDIR(before.st_mode):
            key = (before.st_dev, before.st_ino)
            if key in ancestors:
                raise ValueError('Resource directory symlink cycle: ' + str(p))
            entries.append(dict(path=relative, kind='directory', mode=mode, link=link))
            for child in sorted(p.iterdir(), key=lambda x: x.name):
                visit(child, relative + '/' + child.name, ancestors | {key})
        elif stat.S_ISREG(before.st_mode):
            digest = hashlib.sha256()
            with p.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            after = p.stat()
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                    before.st_mode) != (after.st_dev, after.st_ino, after.st_size,
                                        after.st_mtime_ns, after.st_mode):
                raise ValueError('Resource changed while hashing: ' + str(p))
            entries.append(dict(path=relative, kind='file', bytes=after.st_size,
                                sha256=digest.hexdigest(), mode=mode, link=link))
        else:
            raise ValueError('Resource member is not regular file/directory: ' + str(p))

    visit(root, '.', set())
    return entries



def verify_entrypoint_interpreter(entry):
    lines=Path(entry).read_text().splitlines()
    command=shlex.split(lines[0][2:]) if lines and lines[0].startswith('#!') else []
    if command and Path(command[0]).name in ['sh','bash']:
        # Conda's long-prefix console entry point uses this exact exec form.
        command=shlex.split(lines[1],comments=True) if len(lines)>1 and lines[1].startswith(chr(39)*3+"exec' ") else []
        if len(command)!=4 or command[0]!='exec' or command[2:]!=['$0','$@']:
            raise ValueError('Unsupported IntegronFinder console entry point')
        interpreter=command[1]
    elif command and Path(command[0]).name=='env':
        interpreter=shutil.which(command[1]) if len(command)==2 else None
    else:
        interpreter=command[0] if len(command)==1 else None
    if not interpreter or Path(interpreter).resolve()!=Path(sys.executable).resolve():
        raise ValueError('IntegronFinder entry point interpreter differs from resource probe Python')
    return str(interpreter)


def capture(runtime, native_args):
    import integron_finder
    from integron_finder.scripts.finder import parse_args
    from integron_finder.hmm import scan_hmm_bank
    from integron_finder.prot_db import GembaseDB
    from integronfinder_topology import topology_plan
    if integron_finder.__version__ != '2.0.5':
        raise ValueError('IntegronFinder resolver requires native2.0.5')
    entry=shutil.which('integron_finder')
    if entry is None: raise ValueError('IntegronFinder executable not found')
    declared_interpreter=verify_entrypoint_interpreter(entry)
    cfg = parse_args(list(native_args))
    package = Path(integron_finder.__file__).parent
    resources = dict(package_code={str(p.relative_to(package)): resource(p) for p in sorted(package.rglob('*.py'))},
                     input=resource(cfg.replicon),
                     models={name:resource(getattr(cfg,name)) for name in ['model_integrase','model_phage_int','model_attc_path']},
                     executables={name:resource(getattr(cfg,name)) for name in ['prodigal','cmsearch','hmmsearch']},
                     interpreter=resource(sys.executable), entrypoint=resource(entry),
                     resolver=resource(__file__), topology_helper=resource(Path(__file__).with_name('integronfinder_topology.py')))
    locations = dict(entrypoint=entry,declared_interpreter=declared_interpreter,package=str(package),models={name:str(getattr(cfg,name)) for name in ['model_integrase','model_phage_int','model_attc_path']},
                     executables={name:str(getattr(cfg,name)) for name in ['prodigal','cmsearch','hmmsearch']})
    for name in ['topology_file','prot_file','annot_parser']:
        if getattr(cfg,name): resources[name]=resource(getattr(cfg,name))
    if cfg.gembase or cfg.gembase_path:
        root = Path(cfg.gembase_path).resolve() if cfg.gembase_path else Path(cfg.input_seq_path).resolve().parent.parent
        lst = GembaseDB.get_lst_dir(str(root))
        name = GembaseDB.find_gembase_file_basename(str(root),cfg.input_seq_path)
        resources['gembase_list']=resource(Path(lst)/(name+'.lst'))
        resources['gembase_proteins']=resource(root/'Proteins'/(name+'.prt'))
    bank = None
    if cfg.func_annot and not cfg.no_proteins and not cfg.path_func_annot:
        bank = 'bank_hmm' if Path('bank_hmm').exists() else cfg.func_annot_path
    elif cfg.path_func_annot and not cfg.no_proteins:
        bank = cfg.path_func_annot
    if bank is not None:
        resources['functional_bank_source']=resource(bank)
        selected = scan_hmm_bank(bank)
        resources['functional_profiles']=[dict(path=name,identity=resource(name)) for name in selected]
        locations['functional_bank_source']=str(bank)
        locations['functional_profiles']=selected
    parsed = vars(cfg._args).copy()
    parsed.pop('cpu',None)
    return dict(schema_version=1,tool='IntegronFinder',version=integron_finder.__version__,runtime=runtime,
                parsed_arguments=parsed,resources=resources,resolved_locations=locations,topology=topology_plan(cfg))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-base64',required=True)
    p.add_argument('--output',type=Path)
    p.add_argument('--verify',type=Path)
    p.add_argument('--execute',action='store_true')
    p.add_argument('native_args',nargs=argparse.REMAINDER)
    args=p.parse_args()
    native=args.native_args[1:] if args.native_args[:1]==['--'] else args.native_args
    identity=capture(json.loads(base64.b64decode(args.runtime_base64)),native)
    if args.verify is not None and json.loads(args.verify.read_text())!=identity:
        raise ValueError('IntegronFinder runtime resources/arguments/topology differ from pre-lookup identity')
    if args.output is not None: args.output.write_text(json.dumps(identity,sort_keys=True,separators=(',',':'))+'\n')
    if args.execute:
        if args.verify is None: raise ValueError('--execute requires verified pre-lookup receipt')
        target=Path('integronfinder_effective_topology.tsv')
        if target.is_symlink(): raise ValueError('Reserved generated topology path is a symbolic link')
        if identity['parsed_arguments']['topology_file'] and Path(identity['parsed_arguments']['topology_file']).resolve()==target.resolve():
            raise ValueError('User topology input conflicts with reserved generated topology path')
        target.write_text(identity['topology']['content'])
        os.execvp('integron_finder',['integron_finder']+native+['--topology-file',str(target)])


if __name__=='__main__': main()
