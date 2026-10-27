#!/usr/bin/env python3
"""Execute the fixed anvi'o 7.1 source used by PlasX's complete annotation method."""
import argparse
import hashlib
import difflib
import inspect
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import textwrap

SOURCE_DIGEST = '7956da22fe2d89cf113ab0416b9a98e96a6b85db32c36be543158d60ce033004'
SOURCE_FILES = 1185
# Exact Git submodule commits from the pinned anvi'o source tree; hydrated
# independently so adding their contents does not weaken the primary source lock.
SOURCE_SUBMODULES = {'anvio/data/interactive/lib/JavaScript-MD5': {'commit': '9756d82db70b0f678bc6cd055e7aa08f5c1a0390',
                                               'digest': 'ed23a37172d63601928e6ca2a4e38cb79b905b455d40106896cb14298a06e15a',
                                               'files': 16},
 'anvio/data/interactive/lib/bootstrap': {'commit': '16b48259a62f576e52c903c476bd42b90ab22482',
                                          'digest': '5490896d35904851c6e3f5f040ff7ef88e09a664c1e9e6ca1f4704b4830e50c4',
                                          'files': 361},
 'anvio/data/interactive/lib/bootstrap-markdown': {'commit': '0320bec0bdb3fa49754d8fc26bfe2159c5fbe4d2',
                                                   'digest': '14150e5032cc01ae771b1eb8d8c7a146cb4a3677ee21f3f5ef765cc53277231c',
                                                   'files': 32},
 'anvio/data/interactive/lib/bootstrap-sortable': {'commit': '159505ae6ad99aefd727e8ffd9dc31cad58905b7',
                                                   'digest': 'ce51d07097129b25136d4ca36f9a63577d53bdb7b61f01a44e0121f46eeb6d72',
                                                   'files': 6},
 'anvio/data/interactive/lib/bootstrap-waitingfor': {'commit': '6ea63523247fe772bca0e633dc51a62e9dfbc9ce',
                                                     'digest': '1304a4f3e65c7df9c7e014a46b06ec73b4b864de219309a05145f76496ad0668',
                                                     'files': 14},
 'anvio/data/interactive/lib/d3.js': {'commit': 'b48420930f3848b1498c034387fac2588903d7cf',
                                      'digest': 'ce0d46a9eb17cb07d48bb6f1d93b23889bccae9f5c51b45b3f8d170fc686b3bb',
                                      'files': 546},
 'anvio/data/interactive/lib/jquery': {'commit': '1472290917f17af05e98007136096784f9051fab',
                                       'digest': 'fd9c2189760b96519bc6cb53cc53943c49f62f73db214bff889a85cd3f642752',
                                       'files': 226},
 'anvio/data/interactive/lib/jquery-ui': {'commit': 'd6713024e16de90ea71dc0544ba34e1df01b4d8a',
                                          'digest': '609f745769431803ee0258063671c536cd203fffd598185ac57d9fdf646978a4',
                                          'files': 663},
 'anvio/data/interactive/lib/marked': {'commit': '8f9d0b72f5606ed32057049f387161dd41c36ade',
                                       'digest': 'dec4c0040f626e0e0a18f997b8c17c03e89fdb7123d7582294f71cac03d08aa3',
                                       'files': 228},
 'anvio/data/interactive/lib/randomColor': {'commit': '455f347ecde2f61f9d32d9d1dbe4f6f28e54fc9e',
                                            'digest': 'd4b7eb0ed07bf2adbc7f7d7cf20377b81042cbd8e46a8a81ff6e81a86ba1572b',
                                            'files': 11},
 'anvio/data/interactive/lib/toastr': {'commit': 'b957ae9f38e6856346a0200e83281b08ca717a7d',
                                       'digest': 'dfc5bdda96e1105e55fe8c5a319bb0190a091f59ab7f69275fc69734332dd13c',
                                       'files': 74},
 'anvio/data/static/content/bootstrap-sortable': {'commit': '64e1a43425d3b87605f2bf365d681056a14cd30a',
                                                  'digest': '7c652716eec427110c8afdcd3dec66025a34b4c181d5b461d3d30e563aaf5f3f',
                                                  'files': 6},
 'anvio/data/static/content/chartsjs': {'commit': 'cc57b9e58192e28e061eec93ec5e646ba9cfd99b',
                                        'digest': 'cb697fcf716471cfb023d1480169090e25fe15a54be92e5f9556a8088d8fae42',
                                        'files': 33}}
PROGRAMS = {'anvi-gen-contigs-database', 'anvi-export-gene-calls', 'anvi-run-ncbi-cogs',
            'anvi-run-pfams', 'anvi-export-functions'}


def checked_command(native, record_path):
    """Check inside each forked worker; parent Popen lists cannot see its children."""
    record_path = Path(record_path).resolve()

    def run(*positional, **keywords):
        row = {'pid': os.getpid(), 'command': positional[0] if positional else keywords.get('cmdline')}
        try:
            status = native(*positional, **keywords)
            row['exit_code'] = status
            if status != 0:
                raise RuntimeError('anvi\'o external command failed with exit ' + str(status) + ': ' + repr(row['command']))
            return status
        except BaseException as error:
            row['error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            descriptor = os.open(str(record_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.write(descriptor, (json.dumps(row) + '\n').encode())
            finally:
                os.close(descriptor)

    return run


def verify_source(source):
    rows = []
    for folder in ['anvio', 'bin']:
        for path in sorted((source / folder).rglob('*')):
            relative = path.relative_to(source)
            if any(relative.as_posix().startswith(prefix + '/') for prefix in SOURCE_SUBMODULES):
                continue
            if '__pycache__' in relative.parts or path.suffix == '.pyc':
                continue
            if path.is_symlink():
                path.resolve().relative_to(source)
                data = os.readlink(path).encode()
            elif path.is_file():
                data = path.read_bytes()
            else:
                continue
            rows.append((relative.as_posix(), hashlib.sha256(data).hexdigest()))
    digest = hashlib.sha256(json.dumps(sorted(rows), separators=(',', ':')).encode()).hexdigest()
    if len(rows) != SOURCE_FILES or digest != SOURCE_DIGEST:
        raise ValueError('anvi\'o source differs from fixed 7.1 commit 258991a5bc0f483c958040a55d339e1f447429ac')
    for relative, expected in SOURCE_SUBMODULES.items():
        target = source / relative
        entries = []
        for member in sorted(target.rglob('*')):
            if member.is_symlink():
                member.resolve(strict=True).relative_to(source)
                data = os.readlink(member).encode()
            elif member.is_file():
                data = member.read_bytes()
            else:
                continue
            entries.append((member.relative_to(target).as_posix(), hashlib.sha256(data).hexdigest()))
        actual = hashlib.sha256(json.dumps(sorted(entries), separators=(',', ':')).encode()).hexdigest()
        if len(entries) != expected['files'] or actual != expected['digest']:
            raise ValueError('Missing or changed pinned anvi\'o submodule: ' + relative + '@' + expected['commit'])
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    native_args = args.native_args[1:] if args.native_args[:1] == ['--'] else args.native_args
    if not native_args or native_args[0] not in PROGRAMS:
        parser.error('Expected one of ' + ', '.join(sorted(PROGRAMS)))
    source = args.source.resolve()
    original_popen, original_argv = subprocess.Popen, sys.argv
    children = []
    record = {'source_commit': '258991a5bc0f483c958040a55d339e1f447429ac', 'python_executable': sys.executable,
              'native_args': native_args, 'success': False}
    command_log = args.record.resolve().with_name(args.record.name + '.commands.jsonl')
    command_log.write_text('')

    def popen(command, *positional, **kwargs):
        child = original_popen(command, *positional, **kwargs)
        children.append((child, command))
        return child

    try:
        record['source_digest'] = verify_source(source)
        record['source_submodules'] = SOURCE_SUBMODULES
        sys.path.insert(0, str(source))
        # anvi'o's argument documentation resolves its own scripts through PATH.
        # The verified source bin/ supplies those scripts in a fresh dependency-
        # only Conda environment, without requiring an installed anvi'o package.
        os.environ['PATH'] = str(source / 'bin') + os.pathsep + os.environ.get('PATH', '')
        import anvio
        if Path(anvio.__file__).resolve().parent != source / 'anvio' or anvio.anvio_version != '7.1':
            raise ValueError('Unexpected imported anvi\'o source/version')
        import anvio.utils as native_utils
        native_utils.run_command = checked_command(native_utils.run_command, command_log)
        record['worker_execution_transport'] = 'native run_command with positive-exit checks inside forked workers and a shared append-only command receipt'
        if native_args[0] == 'anvi-run-ncbi-cogs':
            # Fixed 7.1 requests --outfmt 6 directly in blastp, then forces view
            # of a nonexistent DAA. Remove only that redundant conversion call.
            # No search arguments, score thresholds, output parsing, or source
            # files are modified. All actual child failures remain fatal.
            import anvio.cogs as cogs
            original = textwrap.dedent(inspect.getsource(cogs.COGs.search_with_diamond))
            before = '    diamond.view()\n'
            if original.count(before) != 1:
                raise ValueError('Unexpected fixed anvi\'o DIAMOND conversion implementation')
            effective = original.replace(before, '')
            namespace = dict(cogs.__dict__)
            exec(compile(effective, '<anvio7.1-direct-tsv-conversion-repair>', 'exec'), namespace)
            cogs.COGs.search_with_diamond = namespace['search_with_diamond']
            record['compatibility_repair'] = {
                'scope': 'skip redundant DAA conversion after direct tabular blastp output; scientific search unchanged',
                'original_function_sha256': hashlib.sha256(original.encode()).hexdigest(),
                'effective_function_sha256': hashlib.sha256(effective.encode()).hexdigest(),
                'diff': ''.join(difflib.unified_diff(original.splitlines(True), effective.splitlines(True), fromfile='original/search_with_diamond', tofile='effective/search_with_diamond'))}
        subprocess.Popen = popen
        sys.argv = [str(source / 'bin' / native_args[0])] + native_args[1:]
        try:
            runpy.run_path(sys.argv[0], run_name='__main__')
        except SystemExit as exit_status:
            if exit_status.code not in [None, 0]:
                raise
        failed = [(command, child.poll()) for child, command in children if child.poll() != 0]
        if failed:
            raise RuntimeError('anvi\'o child failed or remained running: ' + repr(failed))
        record['success'] = True
    except BaseException as error:
        record['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        subprocess.Popen, sys.argv = original_popen, original_argv
        record['children'] = [{'command': command, 'exit_code': child.poll()} for child, command in children]
        record['native_commands'] = [json.loads(line) for line in command_log.read_text().splitlines()]
        args.record.write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
