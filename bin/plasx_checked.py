#!/usr/bin/env python3
"""Run the fixed native PlasX source, propagating failures through its tee pipes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SOURCE_SHA256 = {
    '__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'compress_utils.py': '2992c40e346c19f1ec97e6eb7e618d462305ac7fef47b1b251b47ccc942bbf21',
    'constants.py': '3b95d18c34755a2f0e05dddf36145c3b96e78330eb012116447b033f4fcfc935',
    'fasta_utils.py': '8cdce78e2ac9de525429268be0f7640079b452fcd08a910d5c6c323b94498dc7',
    'learn.py': '2bc8b6514f12ac506b76c03109dfaf018f16711cbe12e8572667a859be450010',
    'mmseqs.py': '97b6ae9100473e52c9345e292bf4c29aadd4ed3bf79e5fa5ff1c0a0602165c03',
    'model.py': '68cff35789ada7491e69c91e1af90a226d9e88ed9c1fb96c324ba73fec42a5a4',
    'nb_utils.py': '5bc6eceb2bb9d0c0ba716ea6e59b929c116f2c816bac9f750a0ae918cb55529e',
    'pd_utils.py': 'e5f7b7efe17dd55781928e22c134fafc024d9392f4871839952ff25ab0baa961',
    'plasx_script.py': '68d46395dd3cca5b5b3f0f22cf7112d2510481276c372766231b57a23278d603',
    'utils.py': '218cbfd6bf0d66739e528937c35c374615754e64cd0c7f27bc24e02ac13b687c',
}


class CheckedProcesses:
    def __init__(self):
        self.original = subprocess.Popen
        self.children = []

    def popen(self, args, *positional, **kwargs):
        original_args = args
        if kwargs.get('shell'):
            if not isinstance(args, str) or positional or kwargs.get('executable'):
                raise ValueError('Unexpected PlasX shell invocation')
            args = ['/bin/bash', '-o', 'pipefail', '-c', args]
            kwargs['shell'] = False
        child = self.original(args, *positional, **kwargs)
        self.children.append((child, {'command': original_args, 'effective_command': args}))
        return child

    def records(self):
        return [dict(row, exit_code=child.poll()) for child, row in self.children]


def verify_source(directory):
    directory = Path(directory)
    actual = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in SOURCE_SHA256}
    if actual != SOURCE_SHA256:
        raise ValueError('PlasX runtime differs from fixed commit 5c9acfd00a597da27ef5261acf72dbaf2117b645')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', required=True)
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    native_args = args.native_args[1:] if args.native_args[:1] == ['--'] else args.native_args
    if not native_args or native_args[0] not in ['search_de_novo_families', 'predict']:
        parser.error('Expected search_de_novo_families or predict')
    record = {'source_commit': '5c9acfd00a597da27ef5261acf72dbaf2117b645', 'python_executable': sys.executable,
              'native_args': native_args, 'shell_transport': 'bash -o pipefail; original scientific source unchanged', 'success': False}
    audit = CheckedProcesses()
    try:
        import plasx
        record['source_sha256'] = verify_source(Path(plasx.__file__).parent)
        from plasx.plasx_script import run
        subprocess.Popen = audit.popen
        run(native_args)
        failed = [row for row in audit.records() if row['exit_code'] != 0]
        if failed:
            raise RuntimeError('PlasX child process failed or remained running: ' + repr(failed))
        record['success'] = True
    except BaseException as error:
        record['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        subprocess.Popen = audit.original
        record['children'] = audit.records()
        Path(args.record).write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
