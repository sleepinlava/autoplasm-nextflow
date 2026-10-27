#!/usr/bin/env python3
"""Complete the pinned anvi'o source using verified, locally cached gitlink archives."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hydrate(source, archives_dir):
    lock_path = ROOT / 'tests/anvio-submodules.lock.json'
    lock = json.loads(lock_path.read_text())
    output = Path(source).resolve()
    archives = {sha(path): path for path in Path(archives_dir).glob('*.tar.gz')}
    for row in lock['submodules']:
        relative = PurePosixPath(row['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        archive = archives.get(row['archive_sha256'])
        if archive is None:
            raise ValueError('Missing locked archive: ' + row['url'])
        target = output / relative
        if not target.is_dir() or list(target.iterdir()):
            raise ValueError('Expected an empty original gitlink directory: ' + str(target))
        with tempfile.TemporaryDirectory(prefix='anvio-gitlink-', dir=output.parent) as temporary:
            with tarfile.open(archive) as stream:
                stream.extractall(temporary, filter='data')
            roots = list(Path(temporary).iterdir())
            assert len(roots) == 1 and roots[0].is_dir()
            shutil.copytree(roots[0], target, symlinks=True, dirs_exist_ok=True)
    spec = importlib.util.spec_from_file_location('anvio_checked', ROOT / 'bin/anvio_checked.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    primary_digest = module.verify_source(output)
    dangling = [str(path.relative_to(output)) for path in output.rglob('*') if path.is_symlink() and not path.exists()]
    assert not dangling, dangling
    (output / 'resource_provenance.json').write_text(json.dumps({
        'upstream_commit': lock['upstream_commit'], 'primary_source_digest': primary_digest,
        'gitlink_lock_sha256': sha(lock_path), 'submodules': lock['submodules'],
        'scope': 'Original scientific source plus all exact gitlink archives; no method or source substitutions.'
    }, indent=2) + '\n')
    return primary_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'archives', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    shutil.copytree(args.source.resolve(), output, symlinks=True)
    hydrate(output, args.archives)
    print('Verified original source and all 13 pinned submodules')


if __name__ == '__main__':
    main()
