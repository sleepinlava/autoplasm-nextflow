#!/usr/bin/env python3
"""Exercise literal resource roots through the real Nextflow shared entry point."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(base, nextflow):
    base.mkdir(parents=True, exist_ok=False)
    config = base / 'config'
    config.write_text("process.executor='local'\nconda.enabled=false\ndocker.enabled=false\n")
    sources = ['lib/resource_inputs.nf', 'lib/ResourceIdentity.groovy',
               'tests/nextflow/resource_input_import.nf', 'tests/run_resource_root.py']
    before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
    records = []
    reference = None
    for i, name in enumerate(['plain', 'root[1]', 'root*literal', 'root?literal',
                              "space ' quote", 'Unicode-质粒', 'missing[1]']):
        case = base / str(i)
        case.mkdir()
        resource = case / name
        missing = name.startswith('missing')
        if not missing:
            resource.mkdir()
            (resource / 'data').write_bytes(b'expected\n')
        # A matching sibling must never substitute for the literal root.
        alternate_name = name.replace('[1]', '1').replace('*', 'X').replace('?', 'X')
        if alternate_name == name:
            alternate_name += '-other'
        alternate = case / alternate_name
        alternate.mkdir()
        (alternate / 'data').write_bytes(b'WRONG\n')
        cmd = [str(nextflow), '-C', str(config), 'run',
               str(ROOT / 'tests/nextflow/resource_input_import.nf'),
               '--resource', str(resource), '-ansi-log', 'false']
        result = subprocess.run(cmd, cwd=case, text=True, capture_output=True, timeout=120)
        (case / 'stdout').write_text(result.stdout)
        (case / 'stderr').write_text(result.stderr)
        combined = result.stdout + '\n' + result.stderr
        identities = [json.loads(line.split('RESOURCE_IMPORT=', 1)[1])
                      for line in combined.splitlines() if line.startswith('RESOURCE_IMPORT=')]
        if missing:
            assert result.returncode != 0 and not identities, combined
            assert 'No such file or directory' in combined, combined
        else:
            assert result.returncode == 0 and len(identities) == 1, combined
            if reference is None:
                reference = identities[0]
            assert identities[0] == reference, (name, identities, reference)
        records.append(dict(name=name, command=cmd, exit_code=result.returncode,
                            expected_missing=missing, identity=identities))
    assert before == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
    receipt = dict(pass_checks=True, runs=records, source_sha256=before,
                   source_unchanged=True,
                   scope='7 real Nextflow root-locator cases; identical resource identities across literal special roots; missing literal cannot select sibling. No tasks/inference or whole-audit acceptance.')
    (base / 'run.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print('PASS: 6 literal roots and 1 missing-root refusal; no analysis tasks')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--nextflow', type=Path, required=True)
    args = parser.parse_args()
    run(args.out.resolve(), args.nextflow.resolve())
