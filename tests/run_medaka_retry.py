#!/usr/bin/env python3
"""Real Nextflow retry after an explicitly injected early native CLI failure.

The version-report shim fails once, after private inputs are prepared but
before alignment/inference. The retry uses the untouched real native tools.
This is a failure-injection control, not an observed native tool defect.
"""
import argparse
import csv
import gzip
import json
import os
from pathlib import Path
import shlex
import subprocess

from run_medaka_production_cache import fasta, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-root', type=Path, required=True)
    parser.add_argument('--native-reference', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=False)
    fixture, native, prefix = args.fixture_root.resolve(), args.native_reference.resolve(), args.prefix.resolve()
    expected = native / 'native/consensus.fasta'
    native_record = json.loads((native / 'run.json').read_text())
    assert native_record['pass_native_computation_checks'] and sha(expected) == native_record['consensus_fasta_sha256']
    reads = fixture / 'sample_1_1/sample_1_1.filtered.fastq.gz'
    draft = native / 'published-same-sample-draft.fasta'
    model = Path(json.loads((native / 'selection.json').read_text())['selected_model']['resolved_path'])
    originals = {str(p): sha(p) for p in [reads, draft, model,
                 Path(str(draft) + '.fai'), Path(str(draft) + '.map-ont.mmi')]}
    source_files = ['modules/nf-core/medaka/main.nf', 'lib/medaka_runtime.nf',
                    'tests/nextflow/medaka_runtime_resources.nf', 'tests/run_medaka_retry.py',
                    'tests/run_medaka_production_cache.py']
    source_files += ['bin/' + p for p in ['medaka_runtime_resources.py','medaka_model_resources.py',
                                         'medaka_model_selection.py','medaka_index_resources.py']]
    sources = {p: sha(root / p) for p in source_files}
    bindir = base / 'shim-bin'
    bindir.mkdir()
    marker = base / 'injected-failure-once'
    shim = bindir / 'medaka_version_report'
    shim.write_text('#!/bin/bash\nset -euo pipefail\nif [ ! -f ' + shlex.quote(str(marker)) + ' ]; then\n'
                    '  printf "%s\\n" "EXPLICIT_MEDAKA_RETRY_CONTROL" > ' + shlex.quote(str(marker)) + '\n'
                    '  echo "EXPLICIT_MEDAKA_RETRY_CONTROL: injected version-report exit7" >&2\n'
                    '  exit 7\nfi\nexec ' + shlex.quote(str(prefix / 'bin/medaka_version_report')) + ' "$@"\n')
    shim.chmod(0o755)
    config = base / 'native.config'
    before = 'export PATH=' + shlex.quote(str(bindir)) + ':$PATH'
    before_literal = "'" + before.replace('\\', '\\\\').replace("'", "\\'") + "'"
    config.write_text("process.executor='local'\nprocess.cpus=4\nprocess.memory='10 GB'\n"
                      "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                      'process.beforeScript=' + before_literal + '\n'
                      "process { withName: 'MEDAKA' { errorStrategy='retry'; maxRetries=1 } }\n"
                      "trace.fields=['task_id','hash','name','status','exit','attempt','workdir']\n")
    command = [str(root / 'results/tool-audit/20261026-plasmidfinder-runtime/nextflow-no-log'),
               '-C',str(config),'-log',str(base / 'nextflow.log'),'run',
               str(root / 'tests/nextflow/medaka_runtime_resources.nf'),
               '--medaka_reads',str(reads),'--medaka_assembly',str(draft),'--probe_only','false',
               '-work-dir',str(base / 'work'),'-with-trace',str(base / 'trace.tsv')]
    (base / 'command.json').write_text(json.dumps(command,indent=2) + '\n')
    with (base / 'stdout').open('w') as stdout,(base / 'stderr').open('w') as stderr:
        result = subprocess.run(command,cwd=base,env=dict(os.environ,
            PATH=str(prefix / 'bin')+':'+os.environ['PATH'],OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',
            PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''),stdout=stdout,stderr=stderr)
    trace = list(csv.DictReader((base / 'trace.tsv').open(),delimiter='\t')) if (base / 'trace.tsv').exists() else []
    consumers = [r for r in trace if r['name'].startswith('MEDAKA (')]
    report = {'returncode':result.returncode,'formal_acceptance':False,'trace':trace,
              'source_sha256':sources,'original_sha256':originals,'shim_sha256':sha(shim),
              'scope':'Actual fixed Nextflow26.10 local retry, complete bacterial reads/draft/original model. First native version-report failure is an explicit shim; retry real native computation. Not late-inference failure, resume-after-external-kill, all retry policies, OCI retry or biological accuracy.'}
    (base / 'run.json').write_text(json.dumps(report,indent=2) + '\n')
    assert result.returncode == 0 and len(consumers) == 2, report
    failed, completed = sorted(consumers,key=lambda r:int(r['attempt']))
    assert failed['status']=='FAILED' and failed['exit']!='0' and completed['status']=='COMPLETED', consumers
    first, second = Path(failed['workdir']), Path(completed['workdir'])
    assert (first / 'medaka_private/draft.fasta').is_file()
    assert 'EXPLICIT_MEDAKA_RETRY_CONTROL' in (first / '.command.err').read_text()
    assert not (first / 'test.fa.gz').exists(), 'Failed attempt published a success product'
    assert not (first / 'consensus_probs.hdf').exists(), 'Injected failure was expected before inference'
    output = second / 'test.fa.gz'
    assert fasta(output,True) == fasta(expected), 'Full retry output differs from original native software baseline'
    assert sources == {p: sha(root / p) for p in source_files}
    assert originals == {p: sha(Path(p)) for p in originals}
    report.update(pass_bounded_retry=True,distinct_attempt_workdirs=first!=second,
                  complete_fasta_matches_native=True,output_sha256=sha(output),
                  originals_unchanged=True,sources_unchanged=True)
    (base / 'run.json').write_text(json.dumps(report,indent=2) + '\n')
    print(json.dumps({'retry_pass':True,'distinct_attempt_workdirs':first!=second,'actual_consumer_attempts':2}))


if __name__ == '__main__':
    main()
