#!/usr/bin/env python3
"""Full real inference execution for Medaka optional branches -x and -B.

Native medaka_consensus baselines first, then the unmodified production
probe+consumer processes via tests/nextflow/medaka_runtime_resources.nf.
-x must reproduce the default native consensus byte record; -B must reproduce
its own native baseline. Only private fixture copies are used; originals are
hashed before and after. RLE remains uncovered (no prepared RLE model).
"""
import argparse
import csv
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
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=False)
    native = args.native_reference.resolve()
    prefix = args.prefix.resolve()
    reference = json.loads((native / 'run.json').read_text())
    assert reference['pass_native_computation_checks']
    default_consensus = native / 'native/consensus.fasta'
    assert sha(default_consensus) == reference['consensus_fasta_sha256']
    expected_default = fasta(default_consensus)
    reads = args.fixture_root.resolve() / 'sample_1_1/sample_1_1.filtered.fastq.gz'
    review = json.loads((native / 'input-review.json').read_text())
    assert sha(reads) == review['reads_sha256']
    original_draft = native / 'published-same-sample-draft.fasta'
    assert sha(original_draft) == review['draft_sha256']
    original_model = Path(json.loads((native / 'selection.json').read_text())['selected_model']['resolved_path'])
    originals = {str(p): sha(p) for p in [original_model, original_draft,
                 Path(str(original_draft) + '.fai'), Path(str(original_draft) + '.map-ont.mmi'), reads]}

    fixture = base / 'fixture'
    fixture.mkdir()
    draft = fixture / 'draft.fasta'
    for suffix in ['', '.fai', '.map-ont.mmi']:
        shutil.copy2(Path(str(original_draft) + suffix), Path(str(draft) + suffix))
    model = fixture / original_model.name
    shutil.copy2(original_model, model)
    bed = fixture / 'regions.bed'
    bed.write_text('contig_2\t0\t81815\n')

    env = dict(os.environ, PATH=str(prefix / 'bin') + ':' + os.environ['PATH'],
               PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4',
               CUDA_VISIBLE_DEVICES='')
    record = {'phase': 'optional-exec', 'runs': {}, 'pass': False}

    def native_run(name, extra):
        out = base / name
        command = [str(prefix / 'bin/medaka_consensus'), '-t', '4', *extra,
                   '-m', str(model), '-i', str(reads), '-d', str(draft), '-o', str(out)]
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=1200)
        assert result.returncode == 0, name + ': ' + result.stderr[-2000:]
        consensus = out / 'consensus.fasta'
        assert consensus.is_file()
        return consensus

    def production_run(name, extra_args):
        attempt = base / name
        attempt.mkdir()
        config = attempt / 'native.config'
        config.write_text("process.executor='local'\nprocess.cpus=4\nprocess.memory='10 GB'\n"
                          "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                          'process.ext.args=' + json.dumps(' '.join(['-m', shlex.quote(str(model)), *extra_args])) + '\n'
                          "trace.fields=['task_id','hash','name','status','exit','workdir']\n")
        command = [str(root / 'results/tool-audit/20261026-plasmidfinder-runtime/nextflow-no-log'),
                   '-C', str(config), '-log', str(attempt / 'nextflow.log'), 'run',
                   str(root / 'tests/nextflow/medaka_runtime_resources.nf'),
                   '--medaka_reads', str(reads), '--medaka_assembly', str(draft),
                   '--probe_only', 'false', '-work-dir', str(attempt / 'work'),
                   '-with-trace', str(attempt / 'trace.tsv')]
        with (attempt / 'stdout').open('w') as stdout, (attempt / 'stderr').open('w') as stderr:
            result = subprocess.run(command, cwd=attempt, env=env, stdout=stdout, stderr=stderr)
        assert result.returncode == 0, name + ': see ' + str(attempt)
        trace = list(csv.DictReader((attempt / 'trace.tsv').open(), delimiter='\t'))
        assert [t['status'] for t in trace] == ['COMPLETED', 'COMPLETED'], trace
        receipt_path = Path(trace[0]['workdir']) / 'medaka_runtime_identity.json'
        receipt = json.loads(receipt_path.read_text())
        output = Path(trace[1]['workdir']) / 'test.fa.gz'
        import gzip
        decompressed = base / (name + '.consensus.fasta')
        decompressed.write_bytes(gzip.decompress(output.read_bytes()))
        gaps = Path(trace[1]['workdir']) / 'consensus.fasta.gaps_in_draft_coords.bed'
        gaps_text = gaps.read_text() if gaps.is_file() else None
        return receipt, fasta(decompressed), gaps_text

    # -x: native baseline must equal the default native consensus; production must match.
    consensus_x = native_run('native-x', ['-x'])
    assert fasta(consensus_x) == expected_default, 'native -x changed the consensus'
    receipt, produced, gaps_x = production_run('production-x', ['-x'])
    assert receipt['force_indexes'] is True and receipt['source_indexes'] is None
    assert produced == expected_default, 'production -x differs from native baseline'
    gaps_native_x = (base / 'native-x/consensus.fasta.gaps_in_draft_coords.bed').read_text()
    assert gaps_x == gaps_native_x, 'production -x gaps differ from native baseline'
    record['runs']['x'] = {'native_equals_default': True, 'production_equals_native': True,
                           'force_indexes': True}

    # -B: native baseline is the ground truth; production must match it exactly.
    # Native restricts inference to the BED regions, but stitch still emits every
    # contig, gap-filling non-region contigs from the draft (gaps BED). On this
    # already-polished draft the sequences are indistinguishable, so the
    # discriminating oracle is the gaps BED, not the FASTA alone.
    consensus_b = native_run('native-b', ['-B', str(bed)])
    expected_b = fasta(consensus_b)
    gaps_native = (base / 'native-b/consensus.fasta.gaps_in_draft_coords.bed').read_text()
    assert gaps_native == 'contig_1\t0\t4724790\n', gaps_native
    receipt, produced, gaps_produced = production_run('production-b', ['-B', str(bed)])
    assert receipt['regions'] is not None and receipt['regions']['sha256'] == sha(bed)
    assert produced == expected_b, 'production -B differs from native baseline'
    assert gaps_produced == gaps_native, 'production -B gaps differ from native baseline'
    record['runs']['b'] = {'native_gaps_bed': gaps_native.strip(),
                           'production_equals_native': True, 'gaps_equal': True,
                           'regions_sha256': sha(bed)}

    assert originals == {p: sha(Path(p)) for p in originals}, 'Original resource changed'
    record['originals_unchanged'] = True
    record['pass'] = True
    with (base / 'run.json').open('x') as stream:
        stream.write(json.dumps(record, indent=2, default=str) + '\n')
    print('optional-exec verification passed')


if __name__ == '__main__':
    main()
