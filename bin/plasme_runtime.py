#!/usr/bin/env python3
"""Launch the pinned PLASMe source with explicit resources and private ABI compatibility."""
import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys


def sha(path):
    with path.open('rb') as stream:
        digest=hashlib.sha256()
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        return digest.hexdigest()


def stack_flags(path):
    with path.open('rb') as stream:
        header=stream.read(64)
        if header[:6]!=b'\x7fELF\x02\x01':raise ValueError('Expected a Linux64 little-endian ELF library')
        offset=struct.unpack_from('<Q',header,32)[0]
        size,count=struct.unpack_from('<HH',header,54)
        if size!=56:raise ValueError('Invalid ELF program header size')
        matches=[]
        for i in range(count):
            stream.seek(offset+i*size);entry=stream.read(size)
            if len(entry)!=size:raise ValueError('Truncated ELF program header')
            if struct.unpack_from('<I',entry)[0]==0x6474e551:
                matches.append((offset+i*size+4,struct.unpack_from('<I',entry,4)[0]))
    if len(matches)!=1:raise ValueError('Expected one GNU_STACK header')
    return matches[0]


def clear_stack(path):
    """Copy/replace avoids writing through shared Conda package-cache hardlinks."""
    path=Path(path)
    offset,flags=stack_flags(path)
    before=sha(path)
    if flags & 1:
        temporary=path.with_name(path.name+'.private-compat')
        shutil.copyfile(path,temporary)
        shutil.copymode(path,temporary)
        with temporary.open('r+b') as stream:
            stream.seek(offset);stream.write(struct.pack('<I',flags & ~1))
        os.replace(temporary,path)
    return {'flags_before':flags,'flags_after':flags & ~1,'before_sha256':before,'after_sha256':sha(path),
            'scope':'GNU_STACK PF_X only; executable code and model bytes unchanged'}


def runtime_environment(work):
    spec=importlib.util.find_spec('torch')
    if spec is None or spec.origin is None:raise ValueError('PLASMe requires the pinned PyTorch environment')
    torch_lib=Path(spec.origin).parent/'lib'
    library=torch_lib/'libtorch_cpu.so'
    _,flags=stack_flags(library)
    environment=os.environ.copy()
    search=[]
    compatibility=None
    if flags & 1:
        work.mkdir()
        private=work/library.name
        shutil.copyfile(library,private)
        compatibility=clear_stack(private)
        search.append(str(work.resolve()))
        # torch extensions use an RPATH which takes precedence over LD_LIBRARY_PATH.
        # Preload the private corrected object for this Python child only.
        environment['LD_PRELOAD']=str(private.resolve())+(' '+environment['LD_PRELOAD'] if environment.get('LD_PRELOAD') else '')
    search += [str(torch_lib.resolve()),str(Path(sys.prefix)/'lib')]
    if environment.get('LD_LIBRARY_PATH'):search.append(environment['LD_LIBRARY_PATH'])
    environment['LD_LIBRARY_PATH']=os.pathsep.join(search)
    versions={name:importlib.metadata.version(name) for name in ['torch','numpy','pandas','biopython']}
    return environment,{'versions':versions,'torch_cpu_library_sha256':sha(library),'private_elf_compatibility':compatibility}


def prepare_program(source):
    """Version-scoped boundary fixes; keep the configured checkout unchanged."""
    program=source/'PLASMe.py'
    if sha(program)!='d9f9f3d1f2f2e2e420d73bb7d0ad21862f62c7fa54ce5a284abaae4ee3fd4f09':
        return program,{'applied':False,'reason':'not the fixed official4405d5aa source'}
    if sha(source/'bio_script.py')!='db7a2363e33fa6cdecee486ba20116e8391402a63b56ab06455eee63cedb4e3c':
        raise ValueError('Fixed PLASMe source requires its matching bio_script.py')
    private=Path('plasme_program')
    private.mkdir()
    for name in ['PLASMe.py','bio_script.py','trans_data.py','trans_model.py']:
        # Do not copy host security xattrs into a rootless container's task.
        shutil.copyfile(source/name,private/name)
    text=(private/'PLASMe.py').read_text()
    marker='    ### run PC transformer in the non-overlapped region\n'
    if text.count(marker)!=1:raise ValueError('Unexpected fixed PLASMe no-hit boundary')
    empty=('    # Local boundary fix: zero BLAST hits implies no eligible Transformer queries.\n'
           '    if not query_set:\n'
           '        with open(out_path, "w") as empty_result:\n'
           '            empty_result.write("order,query,identity,coverage,PLASMe,overlap\\n")\n'
           '        return\n\n')
    text=text.replace(marker,empty+marker)
    lines=text.splitlines(True);changed=0
    for i,line in enumerate(lines):
        if line.lstrip().startswith('subprocess.call(f"blastn -query'):
            lines[i]=line.replace('subprocess.call(','subprocess.run(',1).replace('shell=True)','shell=True, check=True)')
            changed+=1
    if changed!=1:raise ValueError('Unexpected fixed PLASMe BLAST call')
    (private/'PLASMe.py').write_text(''.join(lines))
    bio=(private/'bio_script.py').read_text()
    start='    for temp_id in range(threads):\n'
    job='        pool.apply_async(prodigal, [f"{contig_path}.{temp_id}"])'
    if bio.count(start)!=1 or bio.count(job)!=1 or bio.count('    pool.join()\n')!=1:
        raise ValueError('Unexpected fixed PLASMe Prodigal worker boundary')
    bio=bio.replace(start,'    jobs = []\n'+start).replace(job,'        jobs.append(pool.apply_async(prodigal, [f"{contig_path}.{temp_id}"]))')
    bio=bio.replace('    pool.join()\n','    pool.join()\n    for job in jobs:\n        job.get()\n')
    lines=bio.splitlines(True);changed=0
    for i,line in enumerate(lines):
        if line.lstrip().startswith('subprocess.run('):
            lines[i]=line.replace('shell=True)','shell=True, check=True)');changed+=1
    if changed!=4:raise ValueError('Unexpected fixed PLASMe helper subprocess calls')
    (private/'bio_script.py').write_text(''.join(lines))
    return private/'PLASMe.py',{'applied':True,'source_commit':'4405d5aa82065cf23a9d78de8b70ba261342ad40',
        'scope':'no-hit empty result and external-command failure propagation only; no model/threshold/feature changes',
        'patched_source_sha256':{p.name:sha(p) for p in private.iterdir() if p.is_file()}}


def run(args):
    source=Path(args.source_dir)
    sources=[source/name for name in ['PLASMe.py','bio_script.py','trans_data.py','trans_model.py']]
    for path in sources:
        if not path.is_file():raise ValueError('Missing PLASMe source file: '+str(path))
    if not Path(args.assembly).is_file():raise ValueError('Missing PLASMe input assembly')
    database=Path(args.database)
    for name in ['plsdb_Mar30.dmnd','plsdb_taxon.tsv','plas_overlap.csv','plas_chrom_thres.csv','plsdb_Mar30.clusters.p2a']:
        path=database/name
        if not path.is_file() or not path.stat().st_size:raise ValueError('Missing prepared PLASMe resource: '+str(path))
    for extension in ['nin','nhr','nsq']:
        if not any(p.stat().st_size for p in database.glob('plsdb_Mar30*.'+extension) if p.is_file()):
            raise ValueError('Missing prepared PLASMe BLAST index: '+extension)
    if not (database/'trans_model').is_dir():raise ValueError('Missing PLASMe model directory')
    if args.threads<1:raise ValueError('PLASMe threads must be positive')
    if Path(args.output).exists() or Path(args.output+'_report.csv').exists() or Path('plasme_temp').exists():
        raise ValueError('PLASMe outputs/temp already exist; refusing stale result reuse')
    for binary in ['blastn','diamond','prodigal']:
        if not shutil.which(binary):raise ValueError('Missing PLASMe executable: '+binary)
    work=Path('.plasme_private_compat')
    if work.exists():raise ValueError('PLASMe private compatibility directory already exists')
    environment,metadata=runtime_environment(work)
    environment['OMP_NUM_THREADS']=str(args.threads)
    environment['MKL_NUM_THREADS']=str(args.threads)
    metadata['source_sha256']={p.name:sha(p) for p in sources}
    metadata['threads']=args.threads
    try:
        program,patch=prepare_program(source)
        metadata['local_source_patch']=patch
        command=[sys.executable]
        if metadata['private_elf_compatibility']:
            # The interpreter has loaded the private SONAME already. Do not
            # inject Torch into BLAST/Prodigal/DIAMOND children via LD_PRELOAD.
            bootstrap=('import os,sys,runpy;os.environ.pop("LD_PRELOAD",None);'
                       'sys.argv=sys.argv[1:];sys.path.insert(0,os.path.dirname(os.path.abspath(sys.argv[0])));'
                       'runpy.run_path(sys.argv[0],run_name="__main__")')
            command+=['-c',bootstrap]
        command += [str(program),args.assembly,args.output,'-d',args.database,
                    '-t',str(args.threads),'--temp','plasme_temp']
        metadata['command']=command
        result=subprocess.run(command,env=environment)
        metadata['exit_code']=result.returncode
        candidates=Path('plasme_temp/PLASMe_candidate.csv')
        if patch['applied'] and result.returncode==0 and candidates.is_file():
            with candidates.open(newline='') as stream:rows=list(csv.DictReader(stream))
            metadata['candidate_records']=len(rows)
            metadata['transformer_scores']=sum(float(row['PLASMe'])>=0 for row in rows)
            metadata['scope']='no eligible BLAST queries' if not rows else 'fixed classifier candidate outputs; no accuracy claim'
        Path(args.runtime_record).write_text(json.dumps(metadata,indent=2)+'\n')
        return result.returncode
    finally:
        if work.exists():shutil.rmtree(work)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='action',required=True)
    fix=commands.add_parser('fix-elf');fix.add_argument('library',type=Path)
    launch=commands.add_parser('run')
    for name in ['source-dir','assembly','database','output']:launch.add_argument('--'+name,required=True)
    launch.add_argument('--threads',type=int,required=True)
    launch.add_argument('--runtime-record',default='plasme_runtime.json')
    args=parser.parse_args()
    try:
        if args.action=='fix-elf':print(json.dumps(clear_stack(args.library)));return 0
        return run(args)
    except (ValueError,OSError,importlib.metadata.PackageNotFoundError) as error:
        print('PLASMe runtime: '+str(error),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
