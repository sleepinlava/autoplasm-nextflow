#!/usr/bin/env python3
"""Reject absent, duplicate and mismatched graph sample metadata in the real branch."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve(); base.mkdir(exist_ok=False)
    assembly = base / 'assembly.fasta'; assembly.write_text('>unrelated_contig\nACGT\n')
    graph = base / 'graph.gfa'; graph.write_text('S\t1\t' + 'ACGT' * 300 + '\tKC:i:4000\n')
    row = dict(id='A.1', assembly=str(assembly), graph=str(graph))
    cases = [('missing-graph', [dict(row, graph=None)], 'Join mismatch'),
             # Both inputs contain this duplicate; arrival order determines
             # which side Nextflow detects first.
             ('duplicate-sample', [row, row], r'Detected join operation duplicate emission on (?:left|right) channel -- offending element: key=A\.1;'),
             ('different-metadata', [dict(row, graph_group='foreign')], 'gplas graph metadata differs from assembly sample A.1')]
    config = base / 'config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='256 MB'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\nparams.publish_dir_mode='copy'\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    sources = ['subworkflows/gplas_binning.nf', 'tests/nextflow/gplas_workflow.nf']
    sha = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
    hashes = {p: sha(p) for p in sources}

    def run(case):
        name, records, diagnostic = case
        folder = base / name; folder.mkdir()
        params = dict(records=records, plasmid_binning_tools=['gplas2'], plasmid_detection_tools=['genomad'],
                      genomad_db=str(base), gplas_source=str(args.source.resolve()), outdir=str(folder / 'out'))
        pf = folder / 'params.json'; pf.write_text(json.dumps(params))
        trace = folder / 'trace.tsv'
        cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config), 'run',
               str(ROOT / 'tests/nextflow/gplas_workflow.nf'), '-params-file', str(pf),
               '-work-dir', str(folder / 'work'), '-with-trace', str(trace), '-ansi-log', 'false']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        (folder / 'stdout').write_text(result.stdout); (folder / 'stderr').write_text(result.stderr)
        tasks = list(csv.DictReader(trace.open(), delimiter='\t')) if trace.exists() else []
        pattern = diagnostic if name == 'duplicate-sample' else re.escape(diagnostic)
        checks = dict(rejected=result.returncode != 0, diagnostic=re.search(pattern, result.stdout + result.stderr) is not None,
                      no_native_binning=not any(re.search(r':GPLAS2 \(', task['name']) for task in tasks),
                      no_final_bins=not list((folder / 'out').rglob('*_results.tab')))
        return dict(case=name, command=cmd, exit_code=result.returncode, tasks=tasks, diagnostic_pattern=pattern, checks=checks)

    with ThreadPoolExecutor(max_workers=2) as executor:
        runs = list(executor.map(run, cases))
    result = dict(pass_=all(all(r['checks'].values()) for r in runs), runs=runs, source_sha256=hashes,
                  source_unchanged=hashes == {p: sha(p) for p in sources})
    result['pass'] = result.pop('pass_') and result['source_unchanged']
    (base / 'run.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
