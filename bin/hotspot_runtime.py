#!/usr/bin/env python3
"""Run unchanged HOTSPOT programs with explicit resources and private Torch ABI support."""
import argparse
import gzip
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

SOURCE_SHA256 = {
    'hotspot.py': '556cbcebdb78469763f9d50b6f75ee04e36c59e58947304eeac6a6824cd8b1d0',
    'model.py': '76e2bc8f2097da137d947f2a7343bd07281f9dd6b22043eb39a1dab740f47259',
    'preprocessing.py': '02dccd4e17aa86495885ca7860b66b12e06326e16b3655a9d1442b7617fd47b6',
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024*1024), b''): digest.update(data)
    return digest.hexdigest()


def stack_flags(path):
    with Path(path).open('rb') as stream:
        header = stream.read(64)
        if header[:6] != b'\x7fELF\x02\x01':
            raise ValueError('Expected a Linux64 little-endian ELF library')
        offset = struct.unpack_from('<Q', header, 32)[0]
        size, count = struct.unpack_from('<HH', header, 54)
        if size != 56: raise ValueError('Invalid ELF program header size')
        matches = []
        for index in range(count):
            position = offset+index*size
            stream.seek(position); entry = stream.read(size)
            if len(entry) != size: raise ValueError('Truncated ELF program header')
            if struct.unpack_from('<I', entry)[0] == 0x6474e551:
                matches.append((position+4, struct.unpack_from('<I', entry, 4)[0]))
    if len(matches) != 1: raise ValueError('Expected one GNU_STACK header')
    return matches[0]


def runtime_environment(work):
    spec = importlib.util.find_spec('torch')
    if spec is None or spec.origin is None: raise ValueError('HOTSPOT requires PyTorch')
    torch_lib = Path(spec.origin).parent/'lib'
    library = torch_lib/'libtorch_cpu.so'
    offset, flags = stack_flags(library)
    environment = os.environ.copy()
    compatibility = None
    if flags & 1:
        work.mkdir()
        private = work/library.name
        # Never write through a shared Conda package-cache hardlink.
        shutil.copyfile(library, private)
        with private.open('r+b') as stream:
            stream.seek(offset); stream.write(struct.pack('<I', flags & ~1))
        compatibility = {'before_sha256': sha(library), 'after_sha256': sha(private),
                         'flag_offset': offset, 'flags_before': flags, 'flags_after': flags & ~1,
                         'scope': 'private GNU_STACK PF_X only; executable code and model bytes unchanged'}
        environment['LD_PRELOAD'] = str(private.resolve())+(' '+environment['LD_PRELOAD'] if environment.get('LD_PRELOAD') else '')
    search = [str(torch_lib.resolve()), str(Path(sys.prefix)/'lib')]
    if environment.get('LD_LIBRARY_PATH'): search.append(environment['LD_LIBRARY_PATH'])
    environment['LD_LIBRARY_PATH'] = os.pathsep.join(search)
    versions = {name: importlib.metadata.version(name) for name in ['torch','numpy','pandas','biopython','bidict','treelib']}
    return environment, {'versions': versions, 'torch_cpu_library_sha256': sha(library), 'private_elf_compatibility': compatibility}


def command(program, arguments, private_compatibility):
    values = [sys.executable]
    if private_compatibility:
        # The interpreter has already loaded the private SONAME. Do not preload
        # Torch into the original program's BLAST/Prodigal/DIAMOND children.
        bootstrap = ('import os,sys,runpy;os.environ.pop("LD_PRELOAD",None);'
                     'sys.argv=sys.argv[1:];sys.path.insert(0,os.path.dirname(os.path.abspath(sys.argv[0])));'
                     'runpy.run_path(sys.argv[0],run_name="__main__")')
        values += ['-c', bootstrap]
    return values+[str(program), *map(str, arguments)]


def fingerprint(directory):
    return {str(p.relative_to(directory)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(directory.rglob('*')) if p.is_file()}


def run(args):
    source, database, models = map(Path, [args.source_dir, args.database, args.models])
    for name in SOURCE_SHA256:
        if not (source/name).is_file(): raise ValueError('Missing HOTSPOT source: '+name)
    source_hashes = {name: sha(source/name) for name in SOURCE_SHA256}
    if source_hashes != SOURCE_SHA256:
        raise ValueError('Unsupported HOTSPOT inference source; expected fixed commit 0e3e3013')
    for name in ['Phylum','Class','Order','Family','Genus','Species']:
        if not (models/(name+'.pth')).is_file(): raise ValueError('Missing HOTSPOT model: '+name)
    for name in ['labels.dict','parent.dict','host_phylogenetic_tree.pkl']:
        if not (models/name).is_file(): raise ValueError('Missing HOTSPOT model metadata: '+name)
    if not database.is_dir() or not Path(args.fasta).is_file() or args.threads < 1:
        raise ValueError('Missing HOTSPOT input/resources or invalid threads')
    for binary in ['prodigal','diamond','blastn','hmmscan']:
        if not shutil.which(binary): raise ValueError('Missing HOTSPOT executable: '+binary)
    work = Path('.hotspot_private_compat')
    for name in [work, Path('hotspot_tmp'), Path('hotspot_results'), Path('hotspot_input.fasta'), Path(args.runtime_record)]:
        if name.exists(): raise ValueError('HOTSPOT task output already exists: '+str(name))
    data = Path(args.fasta).read_bytes()
    decoded = gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data
    if not decoded.lstrip().startswith(b'>'): raise ValueError('HOTSPOT input is not FASTA')
    Path('hotspot_input.fasta').write_bytes(decoded)
    environment, metadata = runtime_environment(work)
    environment['OMP_NUM_THREADS'] = str(args.threads)
    environment['MKL_NUM_THREADS'] = str(args.threads)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    metadata.update(source_sha256=source_hashes, python_executable=sys.executable, python_version=sys.version,
                    database=fingerprint(database), models=fingerprint(models),
                    input_sha256=sha(Path(args.fasta)), decoded_input_sha256=hashlib.sha256(decoded).hexdigest(),
                    threads=args.threads, steps=[], method='unchanged upstream normal CPU inference; no MC-dropout or threshold override')
    metadata['source_commit'] = '0e3e3013a6a29fbdadc8e58180c9eb259877ce99' if metadata['source_sha256'] == SOURCE_SHA256 else None
    try:
        preprocessing = command(source/'preprocessing.py', ['--fasta','hotspot_input.fasta','--database',database,'--model_path',models,'--midfolder','hotspot_tmp','--threads',args.threads], metadata['private_elf_compatibility'])
        inference = command(source/'hotspot.py', ['--model_path',models,'--midfolder','hotspot_tmp','--out','hotspot_results','--device','cpu','--threads',args.threads], metadata['private_elf_compatibility'])
        for name, values in [('preprocessing',preprocessing), ('inference',inference)]:
            if name == 'inference' and not Path('hotspot_tmp/test_feat.dict').is_file():
                raise ValueError('HOTSPOT preprocessing produced no feature dictionary; no host inference was performed')
            result = subprocess.run(values, env=environment)
            metadata['steps'].append({'name':name,'command':values,'exit_code':result.returncode})
            if result.returncode: return result.returncode
        if not Path('hotspot_results/host_lineage.tsv').is_file():
            raise ValueError('HOTSPOT produced no lineage table')
        return 0
    finally:
        Path(args.runtime_record).write_text(json.dumps(metadata, indent=2)+'\n')
        if work.exists(): shutil.rmtree(work)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source-dir','database','models','fasta']: parser.add_argument('--'+name, required=True)
    parser.add_argument('--threads', type=int, required=True)
    parser.add_argument('--runtime-record', default='hotspot_runtime.json')
    try:
        raise SystemExit(run(parser.parse_args()))
    except (ValueError,OSError,importlib.metadata.PackageNotFoundError) as error:
        print('HOTSPOT runtime: '+str(error), file=sys.stderr); raise SystemExit(1)
