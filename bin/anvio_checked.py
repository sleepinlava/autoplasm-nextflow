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
