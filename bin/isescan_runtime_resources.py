#!/usr/bin/env python3
"""ISEScan1.7.3 runtime read-set identity; fixed default scientific arguments."""
import argparse
import ast
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
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


ISESCAN_SOURCE = ['isescan.py', 'constants.py', 'isPredict.py', 'is_analysis.py',
                  'pred.py', 'tools.py', 'ssw_wrap.py', 'pyssw.py']


def executable(name):
    value = shutil.which(name)
    if value is None:
        raise ValueError('Required ISEScan executable not found: ' + name)
    return Path(value).absolute()


def loaded_ssw_path():
    # Resolve the object containing the same symbol used by ssw_wrap.Aligner.
    # Ask the dynamic loader; do not assume prefix/lib, procfs paths, or
    # that LD_LIBRARY_PATH wins over an interpreter RPATH.
    library = ctypes.CDLL('libssw.so')
    class DlInfo(ctypes.Structure):
        _fields_ = [('filename',ctypes.c_char_p),('base',ctypes.c_void_p),
                    ('symbol',ctypes.c_char_p),('address',ctypes.c_void_p)]
    loader = ctypes.CDLL(None)
    function = loader.dladdr
    function.argtypes = [ctypes.c_void_p,ctypes.POINTER(DlInfo)]
    function.restype = ctypes.c_int
    info = DlInfo()
    address = ctypes.cast(library.ssw_init,ctypes.c_void_p)
    if function(address,ctypes.byref(info)) == 0 or info.filename is None:
        raise ValueError('Cannot identify the loaded ISEScan SSW object')
    return Path(os.fsdecode(info.filename)).resolve(strict=True)


def capture(runtime, seqfile, result_prefix):
    entry = executable('isescan.py')
    source_root = entry.resolve().parent
    version = None
    for node in ast.parse(entry.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'version' for t in node.targets):
            version = ast.literal_eval(node.value)
    if version != '1.7.3':
        raise ValueError('ISEScan runtime resolver requires native1.7.3, found ' + str(version))
    # constants derives pHMM locations from sys.argv[0], not __file__.
    original_argv = sys.argv
    try:
        sys.argv = [str(entry)]
        constants_path = source_root / 'constants.py'
        constants = {'__file__': str(constants_path), '__name__': 'isescan_resource_constants'}
        # runpy.run_path temporarily overwrites argv[0] with constants.py.
        # Execute this trusted fixed-tool module with the actual CLI argv[0].
        exec(compile(constants_path.read_bytes(), str(constants_path), 'exec'), constants)
    finally:
        sys.argv = original_argv
    wrapper = executable(constants['FragGeneScan'])
    # Fixed FragGeneScan1.32 Perl wrapper and C run_hmm.c derive train/ from
    # argv[0]. Include all17 files, covering both illumina_5 and shared tables.
    frag = wrapper.parent / 'FragGeneScan'
    ssw = loaded_ssw_path()
    tools = {key: executable(constants[key]) for key in ['phmmer','hmmsearch','blastn','blastp','makeblastdb']}
    interpreters = {name: executable(name) for name in ['python3','perl']}
    resources = dict(
        source={name: resource(source_root / name) for name in ISESCAN_SOURCE},
        sequence=resource(seqfile),
        phmmer_sequences=resource(constants['file4clusterSeqFile4phmmer']),
        hmm_profiles=resource(constants['file4clusterHMM']),
        fraggenescan_wrapper=resource(wrapper),
        fraggenescan_binary=resource(frag),
        fraggenescan_training=resource(wrapper.parent / 'train'),
        ssw_loaded_object=resource(ssw),
        executables={key: resource(path) for key,path in tools.items()},
        interpreters={name: resource(path) for name,path in interpreters.items()})
    return dict(schema_version=1, tool='ISEScan', version=version, runtime=runtime,
                scientific_arguments=dict(seqfile=str(seqfile), output=str(result_prefix)),
                resolved_locations=dict(entrypoint=str(entry), source_directory=str(source_root),
                    phmmer_sequences=constants['file4clusterSeqFile4phmmer'],
                    hmm_profiles=constants['file4clusterHMM'],
                    fraggenescan_wrapper=str(wrapper), fraggenescan_binary=str(frag),
                    fraggenescan_training=str(wrapper.parent/'train'), ssw_loaded_object=str(ssw),
                    executables={key:str(path) for key,path in tools.items()},
                    interpreters={key:str(path) for key,path in interpreters.items()}),
                resources=resources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-base64', required=True)
    parser.add_argument('--seqfile', required=True)
    parser.add_argument('--result-prefix', required=True)
    parser.add_argument('--threads', type=int, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    runtime = json.loads(base64.b64decode(args.runtime_base64).decode('utf-8'))
    identity = capture(runtime, args.seqfile, args.result_prefix)
    if args.verify is not None and json.loads(args.verify.read_text()) != identity:
        raise ValueError('ISEScan runtime resources differ from pre-lookup identity')
    if args.output is not None:
        args.output.write_text(json.dumps(identity, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n')
    if args.execute:
        if args.verify is None:
            raise ValueError('--execute requires verified pre-lookup identity')
        entry = executable('isescan.py')
        os.execv(str(entry), [str(entry), '--seqfile', args.seqfile,
                             '--output', args.result_prefix, '--nthread', str(args.threads)])


if __name__ == '__main__':
    main()
