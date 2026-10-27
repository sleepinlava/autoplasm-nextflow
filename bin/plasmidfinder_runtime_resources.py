#!/usr/bin/env python3
"""Fixed PlasmidFinder2.1.6 native parser and runtime resource identity."""
import argparse
import ast
import re
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
            raise ValueError('Unsupported PlasmidFinder console entry point')
        interpreter=command[1]
    elif command and Path(command[0]).name=='env':
        interpreter=shutil.which(command[1]) if len(command)==2 else None
    else:
        interpreter=command[0] if len(command)==1 else None
    if not interpreter or Path(interpreter).resolve()!=Path(sys.executable).resolve():
        raise ValueError('PlasmidFinder entry point interpreter differs from resource probe Python')
    return str(interpreter)


# Fixed upstream source hash, after reversing only the Bioconda database-path
# assignment/default substitution. Do not execute a different monolithic CLI.
SOURCE_SHA256 = 'df9f23b382f8851daa2dcdbabcc1a5956e93a2f51760ffa4f1bbc81abccf1811'


def native_configuration(entry, native_args):
    source = Path(entry).read_text()
    normal = re.sub(r'^PLASMIDFINDER_SHARE="[^"\n]+"\n\n', '', source, flags=re.M)
    normal = normal.replace('default=PLASMIDFINDER_SHARE)', "default='/database')")
    if hashlib.sha256(normal.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError('PlasmidFinder resolver requires exact native2.1.6 source with packaging-only DB relocation')
    tree = ast.parse(source, filename=str(entry))
    stop = [i for i, n in enumerate(tree.body) if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'file_format' for t in n.targets)]
    if len(stop) != 1:
        raise ValueError('Unexpected native2.1.6 file-format parser boundary')
    tree.body = tree.body[:stop[0] + 1]
    namespace = dict(__name__='plasmidfinder_native_configuration', __file__=str(entry))
    original_argv, original_stdout = sys.argv, sys.stdout
    try:
        sys.argv = [str(entry)] + list(native_args)
        # Runs the original argparse, config/taxonomy selection, validation and
        # file-format detection, stopping before any BLAST/KMA scientific call.
        exec(compile(tree, str(entry), 'exec'), namespace)
    finally:
        sys.argv = original_argv
        if sys.stdout is not original_stdout:
            redirected = sys.stdout
            sys.stdout = original_stdout
            redirected.close()
    return namespace


def capture(runtime, native_args):
    import cgecore
    entry = shutil.which('plasmidfinder.py')
    if not entry:
        raise ValueError('PlasmidFinder executable not found')
    interpreter = verify_entrypoint_interpreter(entry)
    cfg = native_configuration(entry, native_args)
    args = cfg['args']
    kind = cfg['file_format']
    if kind not in ['fasta', 'fastq']:
        raise ValueError('Native PlasmidFinder input must be fasta or fastq: ' + kind)
    method = args.method_path or ('blastn' if kind == 'fasta' else 'kma')
    executable = cfg['find_executable'](method)
    if executable is None:
        raise ValueError('Native PlasmidFinder method executable not found: ' + method)
    if kind == 'fasta' and len(args.infile) != 1:
        raise ValueError('Native PlasmidFinder accepts only one assembled FASTA')
    if kind == 'fastq' and len(args.infile) > 2:
        raise ValueError('Native PlasmidFinder accepts at most two read files')
    package = Path(cgecore.__file__).parent
    return dict(schema_version=1, tool='PlasmidFinder', version='2.1.6',
                version_basis='Exact fixed upstream source after packaging-only normalization, not CLI version output',
                runtime=runtime, parsed_arguments=vars(args), file_format=kind,
                selected_databases=list(cfg['databases']),
                resolved_locations=dict(entrypoint=entry, declared_interpreter=interpreter,
                                        database=args.db_path, method=executable, cgecore=str(package)),
                resources=dict(entrypoint=resource(entry), interpreter=resource(sys.executable),
                               resolver=resource(__file__), database=resource(args.db_path),
                               method=resource(executable),
                               cgecore_code={str(p.relative_to(package)): resource(p)
                                             for p in sorted(package.rglob('*.py'))},
                               inputs=[resource(p) for p in args.infile]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-base64', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    native = args.native_args[1:] if args.native_args[:1] == ['--'] else args.native_args
    identity = capture(json.loads(base64.b64decode(args.runtime_base64)), native)
    if args.verify is not None and json.loads(args.verify.read_text()) != identity:
        raise ValueError('PlasmidFinder runtime resources/arguments differ from pre-lookup identity')
    if args.output is not None:
        args.output.write_text(json.dumps(identity, sort_keys=True, separators=(',', ':')) + '\n')
    if args.execute:
        if args.verify is None:
            raise ValueError('--execute requires verified pre-lookup receipt')
        os.execvp('plasmidfinder.py', ['plasmidfinder.py'] + native)


if __name__ == '__main__':
    main()
