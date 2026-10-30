#!/usr/bin/env python3
"""Podman backend boundary check for the production Medaka probe+consumer.

Runs the unmodified production processes via tests/nextflow/medaka_runtime_resources.nf
with the pinned biocontainers image on the full real bacterial fixture, then compares
the complete FASTA (headers+DNA) against the recorded native software baseline.
Originals are hashed before and after; no model/DNA/threshold change.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fasta(path):
    records = {}
    header = None
    with open(path) as stream:
        for line in stream:
            if line.startswith('>'):
                header = line.rstrip()
                assert header not in records
                records[header] = ''
            else:
                assert header is not None
                records[header] += line.strip()
    assert records and all(records.values())
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-root', type=Path, required=True)
    parser.add_argument('--native-reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=False)
    native = args.native_reference.resolve()
    reference = json.loads((native / 'run.json').read_text())
    assert reference['pass_native_computation_checks']
    expected = fasta(native / 'native/consensus.fasta')
    reads = args.fixture_root.resolve() / 'sample_1_1/sample_1_1.filtered.fastq.gz'
    review = json.loads((native / 'input-review.json').read_text())
    assert sha(reads) == review['reads_sha256']
    original_draft = native / 'published-same-sample-draft.fasta'
    assert sha(original_draft) == review['draft_sha256']
    original_model = Path(json.loads((native / 'selection.json').read_text())['selected_model']['resolved_path'])
    originals = {str(p): sha(p) for p in [original_model, original_draft,
                 Path(str(original_draft) + '.fai'), Path(str(original_draft) + '.map-ont.mmi'), reads]}

    inspect = subprocess.run(['podman', 'inspect',
                              'quay.io/biocontainers/medaka:2.2.2--py312h3050eb1_0',
                              '--format', '{{.Digest}}'], capture_output=True, text=True, check=True)
    digest = inspect.stdout.strip()
    assert digest.startswith('sha256:'), digest

    fixture = base / 'fixture'
    fixture.mkdir()
    draft = fixture / 'draft.fasta'
    for suffix in ['', '.fai', '.map-ont.mmi']:
        shutil.copy2(Path(str(original_draft) + suffix), Path(str(draft) + suffix))
    model = fixture / original_model.name
    shutil.copy2(original_model, model)

    config = base / 'podman.config'
    config.write_text("process.executor='local'\nprocess.cpus=4\nprocess.memory='10 GB'\n"
                      "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                      "podman.enabled=true\n"
                      'process.ext.args=' + json.dumps('-m ' + shlex.quote(str(model))) + '\n'
                      "trace.fields=['task_id','hash','name','status','exit','workdir','container']\n")
    command = [str(root / 'results/tool-audit/20261026-plasmidfinder-runtime/nextflow-no-log'),
               '-C', str(config), '-log', str(base / 'nextflow.log'), 'run',
               str(root / 'tests/nextflow/medaka_runtime_resources.nf'),
               '--medaka_reads', str(reads), '--medaka_assembly', str(draft),
               '--probe_only', 'false', '-work-dir', str(base / 'work'),
               '-with-trace', str(base / 'trace.tsv')]
    (base / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (base / 'stdout').open('w') as stdout, (base / 'stderr').open('w') as stderr:
        result = subprocess.run(command, cwd=base, stdout=stdout, stderr=stderr)
    assert result.returncode == 0, 'see ' + str(base)
    trace = list(csv.DictReader((base / 'trace.tsv').open(), delimiter='\t'))
    assert [t['status'] for t in trace] == ['COMPLETED', 'COMPLETED'], trace
    assert all('medaka:2.2.2--py312h3050eb1_0' in t['container'] for t in trace), trace

    receipt = json.loads((Path(trace[0]['workdir']) / 'medaka_runtime_identity.json').read_text())
    out_fasta = base / 'production.consensus.fasta'
    out_fasta.write_bytes(gzip.decompress((Path(trace[1]['workdir']) / 'test.fa.gz').read_bytes()))
    produced = fasta(out_fasta)
    assert produced == expected, 'podman-backend production output differs from native baseline'

    assert originals == {p: sha(Path(p)) for p in originals}, 'Original resource changed'
    record = {'phase': 'podman-backend', 'image_digest': digest, 'pass': True,
              'containers': [t['container'] for t in trace],
              'production_equals_native': True, 'originals_unchanged': True,
              'receipt_schema': receipt['schema']}
    with (base / 'run.json').open('x') as stream:
        stream.write(json.dumps(record, indent=2) + '\n')
    print('podman-backend verification passed, image', digest)


if __name__ == '__main__':
    main()
