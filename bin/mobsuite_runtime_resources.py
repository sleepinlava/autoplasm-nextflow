#!/usr/bin/env python3
"""Read-only resource identity for the fixed MOB-suite 3.1.9 native parser.

Candidate inspector, not yet a production cache gate. No initializer or native
science is run. BLAST aliases and mutating --filter_db are deliberately refused
until their full read/write contracts are implemented. The production preflight
retains its existing native optional-argument support.
"""
import argparse
import base64
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import mobsuite_preflight as preflight


def resource(path):
    """Hash bytes/layout, following links but rejecting cycles and special files.

    Timestamps/inodes detect concurrent changes but are not part of the identity:
    restored content can reuse an earlier cache entry. This is not an atomic
    snapshot of a concurrently mutable tree; consumers must recheck before use.
    """
    entries = []

    def stamp(value):
        return (value.st_dev, value.st_ino, value.st_size, value.st_mode,
                value.st_mtime_ns, value.st_ctime_ns)

    def visit(path, relative, ancestors):
        local_before = path.lstat()
        link = os.readlink(path) if path.is_symlink() else None
        before = path.stat()
        entry = dict(path=relative, mode=stat.S_IMODE(before.st_mode), link=link)
        if stat.S_ISDIR(before.st_mode):
            key = (before.st_dev, before.st_ino)
            if key in ancestors:
                raise ValueError('Resource directory symlink cycle: ' + str(path))
            children = sorted(path.iterdir(), key=lambda item: item.name)
            entry['kind'] = 'directory'
            entries.append(entry)
            for child in children:
                visit(child, relative + '/' + child.name, ancestors | {key})
            if [p.name for p in children] != sorted(p.name for p in path.iterdir()):
                raise ValueError('Resource directory changed while hashing: ' + str(path))
        elif stat.S_ISREG(before.st_mode):
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                if stamp(os.fstat(stream.fileno())) != stamp(before):
                    raise ValueError('Resource replaced before hashing: ' + str(path))
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
                if stamp(os.fstat(stream.fileno())) != stamp(before):
                    raise ValueError('Resource changed while hashing: ' + str(path))
            entry.update(kind='file', bytes=before.st_size, sha256=digest.hexdigest())
            entries.append(entry)
        else:
            raise ValueError('Resource is not a regular file/directory: ' + str(path))
        if stamp(before) != stamp(path.stat()) or stamp(local_before) != stamp(path.lstat()):
            raise ValueError('Resource changed while hashing: ' + str(path))

    visit(Path(path), '.', set())
    return entries


def blast_database(prefix, executable):
    """Resolve actual BLAST volumes; hash each prefix member, never a glob guess.

    A .nal may reference other alias files and selection lists not exposed by
    -info. Refuse aliases rather than claiming those hidden dependencies closed.
    """
    prefix = Path(prefix).absolute()
    if Path(str(prefix) + '.nal').exists():
        raise ValueError('BLAST alias resource closure is not implemented: ' + str(prefix))
    completed = subprocess.run([executable, '-db', str(prefix), '-dbtype', 'nucl', '-info'],
                               capture_output=True, text=True, check=True)
    lines = completed.stdout.splitlines()
    positions = [i for i, line in enumerate(lines) if line.strip() == 'Volumes:']
    if len(positions) != 1:
        raise ValueError('Unexpected blastdbcmd volume report: ' + str(prefix))
    volumes = [line.strip() for line in lines[positions[0] + 1:] if line.strip()]
    if not volumes or any(not Path(value).is_absolute() for value in volumes):
        raise ValueError('BLAST did not report absolute database volumes: ' + str(prefix))
    members = {}
    for value in [str(prefix), *volumes]:
        base = Path(value)
        if Path(str(base) + '.nal').exists():
            raise ValueError('BLAST alias resource closure is not implemented: ' + str(base))
        matches = [p for p in base.parent.iterdir()
                   if p.name == base.name or p.name.startswith(base.name + '.')]
        if not matches:
            raise ValueError('BLAST volume has no readable members: ' + str(base))
        for path in sorted(matches):
            members[str(path)] = resource(path)
    return dict(info=completed.stdout, volumes=volumes, members=members)


def capture(runtime, native_args, tool='mob_recon'):
    args, paths = preflight.native_resource_paths(native_args, tool)
    if getattr(args, 'filter_db', None):
        raise ValueError('--filter_db native preparation can mutate its source; runtime identity is not implemented')
    # Preserve existing source/schema checks and never initialize a database.
    preparation = preflight.check(native_args, tool, allow_optional=True)
    program = importlib.import_module('mob_suite.' + tool)
    from mob_suite.constants import default_database_dir
    package = Path(program.__file__).parent
    executables = {}
    for name in ['blastn', 'tblastn', 'makeblastdb', 'blastdbcmd', 'mash']:
        value = shutil.which(name)
        if value is None:
            raise ValueError('MOB resource executable missing: ' + name)
        executables[name] = os.path.abspath(value)
    database_dir = os.path.abspath(args.database_directory)
    selected = {name: dict(location=str(path), content=resource(path))
                for name, path in paths.items()}
    # Repetitive DNA is a query against the task's newly built input-contig
    # database, not a prebuilt reference BLAST database (native blast_mge).
    prefixes = {name: paths[name] for name in ['plasmid_ref_db']
                if name in paths}
    genome = getattr(args, 'genome_filter_db_prefix', None)
    if genome:
        prefixes['genome_filter_db_prefix'] = genome
        selected['genome_filter_mash'] = dict(location=genome + '.msh', content=resource(genome + '.msh'))
    databases = {name: blast_database(value, executables['blastdbcmd'])
                 for name, value in prefixes.items()}
    # MOB package code is a selected-source boundary, not all Python dependencies
    # or shared libraries. Exclude installed tests/fixtures and generated pycache.
    code = {str(path.relative_to(package)): resource(path)
            for path in sorted(package.rglob('*.py'))
            if not {'tests', '__pycache__'}.intersection(path.relative_to(package).parts)}
    return dict(schema_version=1, tool=tool, version='3.1.9', runtime=runtime,
                parsed_arguments=vars(args), selection_branch='default' if database_dir == default_database_dir else 'explicit',
                database_directory=database_dir, package_location=str(package),
                taxonomy_schema_version=preparation['taxonomy_schema_version'],
                selected_resources=selected, blast_databases=databases,
                resources=dict(database=resource(database_dir), package_code=code,
                               resolver=resource(__file__), preflight=resource(preflight.__file__),
                               interpreter=resource(sys.executable),
                               executables={name: dict(location=value, content=resource(value))
                                            for name, value in executables.items()}),
                environment={name: os.environ.get(name) for name in
                             ['PATH', 'PYTHONPATH', 'LD_LIBRARY_PATH', 'BLASTDB', 'NCBI', 'NCBI_CONFIG__BLAST__DATA_LOADERS']},
                input=resource(args.infile),
                limitations=['Candidate inspector; production pre-cache wiring not yet installed.',
                             'Selected native sources/binaries, not complete environment or OCI closure.',
                             'No atomic snapshot or protection against concurrent writes after verification.',
                             'BLAST aliases and mutating filter_db explicitly unsupported by this inspector.',
                             'Identity is not database biological purity, accuracy, or compatibility certification.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', choices=['mob_recon', 'mob_typer'], default='mob_recon')
    parser.add_argument('--runtime-base64', default='e30=')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    options = parser.parse_args()
    native = options.native_args[1:] if options.native_args[:1] == ['--'] else options.native_args
    try:
        identity = capture(json.loads(base64.b64decode(options.runtime_base64, validate=True)), native, options.tool)
        if options.verify and json.loads(options.verify.read_text()) != identity:
            raise ValueError('MOB runtime resources/arguments differ from the recorded identity')
        if options.output:
            options.output.write_text(json.dumps(identity, sort_keys=True, separators=(',', ':')) + '\n')
        elif not options.verify:
            print(json.dumps(identity, sort_keys=True))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
