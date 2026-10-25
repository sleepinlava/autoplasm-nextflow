#!/usr/bin/env python3
"""Generate lexical include/config evidence; never infer runtime coverage."""
from pathlib import Path
import csv
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/tool-audit'
INCLUDE = re.compile(r"include\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]")

def table(name, fields, rows):
    with (OUT / name).open('w') as handle:
        writer = csv.writer(handle, delimiter='\t', lineterminator='\n')
        writer.writerow(fields)
        writer.writerows(rows)

def main():
    files = sorted([*ROOT.glob('modules/**/*.nf'), *ROOT.glob('subworkflows/**/*.nf'), *ROOT.glob('lib/**/*.nf'), ROOT / 'main.nf'])
    texts = {p: p.read_text() for p in files}
    edges = []
    for path, text in texts.items():
        # Exclude comments so illustrative include statements do not become edges.
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        text = re.sub(r'//[^\n]*', '', text)
        for match in INCLUDE.finditer(text):
            names, target = match.groups()
            base = path.parent / target
            candidates = [Path(str(base) + '.nf'), base / 'main.nf']
            resolved = next((p.resolve() for p in candidates if p.is_file()), None)
            line = texts[path][:texts[path].find(match.group(0))].count('\n') + 1
            for item in names.split(';'):
                parts = re.split(r'\s+as\s+', item.strip())
                edges.append([str(path.relative_to(ROOT)), parts[0], parts[-1], str(resolved.relative_to(ROOT)) if resolved else target, 'resolved' if resolved else 'missing', line])
    table('include-edges.tsv', ['caller', 'symbol', 'alias', 'target', 'resolution', 'line'], edges)
    reached = {'main.nf'}
    while True:
        expanded = reached | {row[3] for row in edges if row[0] in reached and row[4] == 'resolved'}
        if expanded == reached:
            break
        reached = expanded
    table('reachability.tsv', ['path', 'include_reachable', 'runtime_status'], [[str(p.relative_to(ROOT)), str(p.relative_to(ROOT)) in reached, 'unknown; includes do not prove branch execution'] for p in files])
    selectors = []
    for path in sorted(ROOT.glob('conf/*.config')) + [ROOT / 'nextflow.config']:
        text = path.read_text()
        for n, line in enumerate(text.splitlines(), 1):
            if re.search(r'withName\s*:|withLabel\s*:|includeConfig\s|ext\.(args|args2|prefix|when)\s*=|container\s*=|conda\s*=', line):
                selectors.append([str(path.relative_to(ROOT)), n, line.strip(), 'lexical; evaluate profile and selector precedence with Nextflow'])
    table('config-selectors.tsv', ['path', 'line', 'declaration', 'limitations'], selectors)
    print(f'{len(files)} files; {len(edges)} include symbols; {len(reached)} include-reachable files; {sum(row[4] == "missing" for row in edges)} unresolved includes; {len(selectors)} config declarations')

if __name__ == '__main__':
    main()
