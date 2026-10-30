#!/usr/bin/env python3
"""Check a real REPORT task against explicit expected samples and producers.

This verifies technical provenance, not tool accuracy or biological validity.
Run against a retained task work directory, not just its published report.
"""
import argparse
import hashlib
import json
from pathlib import Path


def check(workdir, samples, producers):
    data = json.loads((workdir / 'report_data.json').read_text())
    manifest = json.loads((workdir / 'report_inputs.json').read_text())
    assert {r['sample_id'] for r in data['samples']} == set(samples)
    records = [r for r in manifest['records'] if r['kind'] == 'runtime_command']
    commands = data['runtime_commands']
    assert len(commands) == len(records)
    assert {r['producer'] for r in commands} == set(producers)
    key = lambda r: (r['task_process'], r['sample_id'], r['analysis_sample_id'])
    by_key = {key(r): r for r in records}
    assert len(by_key) == len(records)
    for command in commands:
        record = by_key[key(command)]
        staged = workdir / record['files'][0]
        origin = staged.resolve()
        payload = origin.read_bytes()
        assert payload == (origin.parent / '.command.sh').read_bytes()
        assert payload == command['script'].encode()
        assert hashlib.sha256(payload).hexdigest() == command['script_sha256'] == record['script_sha256']
        assert command['runtime_probe'] == record['runtime_probe']
        assert command['runtime_probe']['stdout'].strip()
        if record.get('cohort'):
            assert command['cohort'] is True
            members = command['cohort_samples']
            assert members == record['cohort_samples']
            assert len(members) == len(set(members)) and set(members) == set(samples)
            assert command['sample_id'] == 'cohort:' + command['task_process']
        else:
            assert command['sample_id'] in samples
        assert command['script_sha256'] in (workdir / 'methods.md').read_text()
        assert command['script_sha256'] in (workdir / 'report.html').read_text()
    assert (workdir / 'REPORT.task_command.sh').read_bytes() == (workdir / '.command.sh').read_bytes()
    return {'samples': len(samples), 'runtime_records': len(commands),
            'cohort_records': sum(bool(r.get('cohort')) for r in commands),
            'producers': sorted(producers), 'pass': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-workdir', type=Path, required=True)
    parser.add_argument('--samples', nargs='+', required=True)
    parser.add_argument('--producers', nargs='+', required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.report_workdir, args.samples, args.producers), indent=2))
