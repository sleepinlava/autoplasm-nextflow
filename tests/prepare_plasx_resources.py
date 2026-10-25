#!/usr/bin/env python3
"""Prepare complete, pinned PlasX references and fixed source trees; no cloud resources."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'bin' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def matches(path, expected):
    return path.is_file() and path.stat().st_size == expected['bytes'] and sha256(path) == expected['sha256']


def fetch(expected, destination, cache=None, cache_relative=None):
    if destination.exists():
        if not matches(destination, expected):
            raise ValueError('Existing file differs from lock: ' + str(destination))
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if cache:
        for candidate in [cache / (cache_relative or destination.name), cache / destination.name]:
            if matches(candidate, expected):
                shutil.copyfile(candidate, destination)
                print('verified cached download', destination.name, flush=True)
                return
    partial = destination.with_name(destination.name + '.part')
    for attempt in range(2):
        try:
            with urllib.request.urlopen(expected['url'], timeout=45) as response, partial.open('wb') as stream:
                size = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    stream.write(block)
                    size += len(block)
                if response.headers.get('Content-Length') and size != int(response.headers['Content-Length']):
                    raise ValueError('Incomplete HTTP download: ' + destination.name)
            if not matches(partial, expected):
                raise ValueError('Download differs from pinned bytes/SHA256: ' + destination.name)
            if expected.get('md5') and hashlib.md5(partial.read_bytes()).hexdigest() != expected['md5']:
                raise ValueError('Download differs from recorded MD5: ' + destination.name)
            partial.rename(destination)
            print('verified public download', destination.name, flush=True)
            return
        except Exception:
            if attempt:
                raise
            time.sleep(3)


def extract(archive, destination, strip_root=False):
    destination.mkdir(exist_ok=False, parents=True)
    destination = destination.resolve()
    seen = set()
    with tarfile.open(archive) as stream:
        for member in stream:
            parts = Path(member.name).parts[1:] if strip_root else Path(member.name).parts
            relative = Path(*parts)
            if not parts or relative == Path('.'):
                continue
            if relative.is_absolute() or '..' in relative.parts or str(relative) in seen:
                raise ValueError('Unsafe or duplicate archive member: ' + member.name)
            seen.add(str(relative))
            path = destination / relative
            # Existing archive-created symlinks cannot redirect later members.
            path.parent.resolve().relative_to(destination)
            if member.isdir():
                path.mkdir(exist_ok=True, parents=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(member) as source, path.open('xb') as out:
                    shutil.copyfileobj(source, out)
                path.chmod(0o755 if member.mode & 0o111 else 0o644)
            elif member.issym():
                if Path(member.linkname).is_absolute():
                    raise ValueError('Absolute archive symlink')
                (path.parent / member.linkname).resolve().relative_to(destination)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(member.linkname)
            else:
                raise ValueError('Unsupported archive member: ' + member.name)


def format_databases(directory, threads):
    source = (directory / 'sources/anvio').resolve()
    load_helper('anvio_checked').verify_source(source)
    sys.path.insert(0, str(source))
    os.environ['PATH'] = str(source / 'bin') + os.pathsep + os.environ.get('PATH', '')
    from anvio.cogs import COGsSetup, COG_DATA_VERSION
    from anvio.pfam import PfamSetup
    import anvio.utils as utils
    command_log = directory / 'database-format-commands.jsonl'
    command_log.write_text('')
    utils.run_command = load_helper('anvio_checked').checked_command(utils.run_command, command_log)
    setup = COGsSetup(argparse.Namespace(cog_data_dir=str(directory / 'COG_2014'), cog_version='COG14',
                      num_threads=threads, reset=False, just_do_it=False))
    # Complete raw data were preloaded with locked checksums. The native
    # formatter requires this layout marker before it can consume that data.
    Path(setup.COG_data_dir_version).write_text(COG_DATA_VERSION)
    setup.create()
    pfam = PfamSetup(argparse.Namespace(pfam_data_dir=str(directory / 'Pfam_v32'), pfam_version='32.0', reset=False))
    pfam.decompress_files()
    pfam.hmmpress_files()


def prepare(args):
    directory = args.outdir.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    lock = json.loads(args.lock.read_text())
    downloads = directory / 'downloads'
    for item in lock['sources']:
        path = downloads / item['archive']
        fetch(item, path, args.cache)
        extract(path, directory / 'sources' / ('anvio' if item['repository'] == 'merenlab/anvio' else 'plasx'), strip_root=True)
    load_helper('anvio_checked').verify_source(directory / 'sources/anvio')
    load_helper('plasx_checked').verify_source(directory / 'sources/plasx/plasx')
    for name, item in lock['downloads'].items():
        fetch(item, downloads / name, args.cache)
    extract(downloads / 'PlasX_mmseqs_profiles.tar.gz', directory / 'profiles')
    for item in lock['profiles']['files']:
        if not matches(directory / 'profiles' / item['path'], item):
            raise ValueError('Profile extraction differs from complete pinned archive: ' + item['path'])
    model = directory / 'model/PlasX_coefficients_and_gene_enrichments.txt'
    model.parent.mkdir()
    with gzip.open(downloads / 'PlasX_coefficients_and_gene_enrichments.txt.gz', 'rb') as source, model.open('wb') as out:
        shutil.copyfileobj(source, out)
    if sha256(model) != lock['model_sha256']:
        raise ValueError('Coefficient decompression mismatch')
    for item in lock['raw_annotation_resources']:
        path = downloads / Path(item['file']).name
        fetch(item, path, args.cache, item['file'])
        staged = directory / item['file']
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, staged)
    command = [str(args.anvio_prefix.resolve() / 'bin/python'), str(Path(__file__).resolve()),
               'format', '--outdir', str(directory), '--threads', str(args.threads)]
    environment = dict(os.environ, PATH=str(args.anvio_prefix.resolve() / 'bin') + os.pathsep + os.environ.get('PATH', ''),
                       PYTHONDONTWRITEBYTECODE='1', MPLCONFIGDIR=str(directory / 'matplotlib'))
    with (directory / 'format.stdout').open('w') as stdout, (directory / 'format.stderr').open('w') as stderr:
        process = subprocess.run(command, env=environment, stdout=stdout, stderr=stderr)
    (directory / 'format-run.json').write_text(json.dumps({'command': command, 'exit_code': process.returncode}, indent=2) + '\n')
    process.check_returncode()
    load_helper('plasx_inputs').check_resources(directory / 'COG_2014', directory / 'Pfam_v32', directory / 'profiles', model)
    files = []
    for folder in ['sources', 'profiles', 'model', 'COG_2014', 'Pfam_v32']:
        for path in sorted((directory / folder).rglob('*')):
            if path.is_file():
                files.append({'path': str(path.relative_to(directory)), 'bytes': path.stat().st_size, 'sha256': sha256(path)})
    receipt = {'lock_sha256': sha256(args.lock), 'source_lock_status': lock['status'], 'format_exit_code': process.returncode,
               'scope': 'complete fixed source/COG2014/Pfam32/de-novo/model preparation; no classifier or biological validation claim',
               'files': files, 'parameters': {'plasx_anvio_source': str(directory / 'sources/anvio'),
               'plasx_source': str(directory / 'sources/plasx'), 'plasx_cog_db': str(directory / 'COG_2014'),
               'plasx_pfam_db': str(directory / 'Pfam_v32'), 'plasx_profiles': str(directory / 'profiles'), 'plasx_model': str(model)}}
    (directory / 'prepared-resources.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Complete resource preparation verified:', directory / 'prepared-resources.json', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'format'])
    parser.add_argument('--outdir', type=Path, required=True, help='New dedicated output directory for prepare')
    parser.add_argument('--anvio-prefix', type=Path, help='Environment created from envs/plasx-anvio-linux-64.lock')
    parser.add_argument('--cache', type=Path, help='Optional existing verified-download cache')
    parser.add_argument('--lock', type=Path, default=ROOT / 'tests/plasx-native.lock.json')
    parser.add_argument('--threads', type=int, default=2)
    args = parser.parse_args()
    if args.threads <= 0 or (args.mode == 'prepare' and args.anvio_prefix is None):
        parser.error('positive --threads and --anvio-prefix are required')
    if args.mode == 'format':
        format_databases(args.outdir.resolve(), args.threads)
    else:
        prepare(args)


if __name__ == '__main__':
    main()
