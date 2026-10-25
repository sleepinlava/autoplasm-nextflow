#!/usr/bin/env python3
"""Resolve literal vendored test scripts and verify pinned test-only helpers."""
import argparse
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--table', type=Path)
    args = parser.parse_args()
    rows = []
    for suite in sorted((ROOT / 'modules/nf-core').rglob('*.nf.test')):
        text = re.sub(r'/\*.*?\*/', '', suite.read_text(), flags=re.S)
        text = re.sub(r'(?m)^\s*//.*$', '', text)
        for match in re.finditer(r'\bscript\s+([\"\x27])([^\n]*?)\1', text):
            reference = match[2]
            resolved = None
            if '$' not in reference:
                for base in [suite.parent / reference, ROOT / reference]:
                    candidates = [base, Path(str(base) + '.nf'), base / 'main.nf']
                    resolved = next((p.resolve() for p in candidates if p.is_file()), None)
                    if resolved is not None:
                        break
            state = 'dynamic' if '$' in reference else 'resolved' if resolved else 'missing'
            rows.append(dict(suite=str(suite.relative_to(ROOT)), script_reference=reference,
                             resolved_path=str(resolved.relative_to(ROOT)) if resolved else '', state=state,
                             limitation='Literal-path resolution only; native execution and test assertion validity are separate'))
    helper_root = ROOT / 'tests/nf-test/prerequisites'
    lock = json.loads((helper_root / 'source-lock.json').read_text())
    helpers = []
    for entry in lock['files']:
        path = ROOT / entry['path']
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        ok = not path.is_symlink() and sha == entry['sha256'] and all(blob == ref['git_blob'] for ref in entry['source_refs'])
        helpers.append(dict(path=entry['path'], sha256=sha, git_blob=blob, source_ref_count=len(entry['source_refs']), matches=ok))
    modules = json.loads((ROOT / 'modules.json').read_text())['repos']['https://github.com/nf-core/modules.git']['modules']['nf-core']
    expected = Counter((x['suite'], 'tests/nf-test/prerequisites/nf-core/' + x['dependency'] + '/main.nf') for x in lock['consumers'])
    observed = Counter((x['suite'], x['script_reference']) for x in rows if x['script_reference'].startswith('tests/nf-test/prerequisites/'))
    revisions = all(modules[x['consumer']]['git_sha'] == x['revision'] for x in lock['consumers'])
    license_ok = hashlib.sha256((helper_root / lock['license']['path']).read_bytes()).hexdigest() == lock['license']['sha256']
    missing = [x for x in rows if x['state'] == 'missing']
    result = dict(rows=rows, helper_files=helpers, missing_literal_scripts=missing,
                  dynamic_reference_count=sum(x['state'] == 'dynamic' for x in rows),
                  expected_setup_reference_count=sum(expected.values()), actual_setup_reference_count=sum(observed.values()),
                  consumer_revisions_match=revisions, setup_references_match=expected == observed,
                  license_matches=license_ok,
                  scope='Current vendored test literal scripts plus24 fixed upstream helper definitions/environment/metadata and14 consumer setup references. No native P1 or scientific accuracy certification.')
    result['pass'] = not missing and all(x['matches'] for x in helpers) and revisions and expected == observed and license_ok
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    if args.table:
        with args.table.open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)
    print(f'{len(rows)} literal references; {len(missing)} missing; {len(helpers)} helper files; {sum(expected.values())} setup references')
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
