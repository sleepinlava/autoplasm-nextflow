#!/usr/bin/env python3
"""Full published NO-MISS sample, original Medaka CLI; no subsampling.

The released assembly is an already-polished same-sample draft, not an
independent biological truth. This verifies native computation/output and
creates a software reference for later module comparison, not error-rate gains.
"""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def fasta(path):
    records = {}
    name = None
    with open(path) as stream:
        for line in stream:
            if line.startswith('>'):
                name = line[1:].split()[0]
                assert name not in records
                records[name] = []
            else:
                assert name is not None
                records[name].append(line.strip())
    return {name: ''.join(parts) for name, parts in records.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=False)
    fixture = args.fixture_root.resolve()
    download = json.loads((fixture / 'sample-downloads.json').read_text())
    assert len(download) == 3
    for item in download:
        path = root / item['path']
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'] and item['etag_verified']
    reads = fixture / 'sample_1_1/sample_1_1.filtered.fastq.gz'
    published = fixture / 'sample_1_1/sample_1_1.medaka.fasta.gz'
    metadata = json.loads((fixture / 'sample_1_1/metamap.json').read_text())
    file_stats = list(csv.DictReader((fixture / 'metadata/per-file-stats.tsv').open(), delimiter='\t'))
    assert len(file_stats) == 1 and file_stats[0]['filename'] == reads.name
    file_stats = file_stats[0]
    stats_source = json.loads((fixture / 'metadata/readstats-download.json').read_text())
    assert sha(fixture / 'metadata/per-file-stats.tsv') == stats_source['sha256']
    assert metadata['alias'] == 'sample_1_1' and metadata['barcode'] == 'barcode01'
    assert metadata['basecall_models'] == ['dna_r10.4.1_e8.2_400bps_sup@v5.2.0']
    draft = base / 'published-same-sample-draft.fasta'
    with gzip.open(published, 'rb') as source:
        draft.write_bytes(source.read())
    reference = fasta(draft)
    assert sum(map(len, reference.values())) > 4_000_000
    import pysam
    n = bases = tagged = 0
    min_length = 10**12
    max_length = 0
    for_model = Counter()
    with pysam.FastxFile(str(reads)) as stream:
        for rec in stream:
            n += 1
            bases += len(rec.sequence)
            min_length = min(min_length, len(rec.sequence))
            max_length = max(max_length, len(rec.sequence))
            assert rec.quality is not None and len(rec.sequence) == len(rec.quality)
            if rec.comment:
                tagged += 1
                for caller in metadata['basecall_models']:
                    if caller in rec.comment:
                        for_model[caller] += 1
    review = {'records': n, 'bases': bases, 'min_length': min_length, 'max_length': max_length,
              'records_with_comments': tagged, 'model_comment_counts': dict(for_model),
              'metamap_n_seqs': metadata['n_seqs'], 'matches_metamap_n_seqs': n == metadata['n_seqs'],
              'official_target_file_stats': file_stats,
              'exact_file_stats_match': (n, bases, min_length, max_length) == tuple(int(file_stats[k]) for k in ['n_seqs', 'n_bases', 'min_length', 'max_length']),
              'draft_records': {name: len(seq) for name, seq in reference.items()},
              'draft_sha256': sha(draft), 'reads_sha256': sha(reads),
              'scope': 'Complete released filtered FASTQ and same-sample published polished assembly; no local read selection or relabeling, not entire raw flowcell or biological truth.'}
    (base / 'input-review.json').write_text(json.dumps(review, indent=2) + '\n')
    print(json.dumps(review), flush=True)
    # Exact target-file metadata is the independent oracle. The separately
    # retained metamap describes a different stage/count; never rewrite it.
    assert review['exact_file_stats_match'], review
    helper = root / 'bin/medaka_model_selection.py'
    spec = importlib.util.spec_from_file_location('medaka_selection', helper)
    selection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selection)
    diagnostics = {}
    observed = selection.select(reads, draft, threads=str(args.threads), diagnostics=diagnostics)
    (base / 'selection.json').write_text(json.dumps(observed, indent=2) + '\n')
    (base / 'selection-diagnostics.json').write_text(json.dumps(diagnostics, indent=2) + '\n')
    assert observed['selected_model']['resolved_path'].endswith('/r1041_e82_400bps_sup_v5.2.0_model_pt.tar.gz')
    import medaka.options as options
    store_state = lambda: {str(store): {str(p.relative_to(store)): sha(p) for p in sorted(Path(store).rglob('*')) if p.is_file()} for store in options.model_stores}
    before = store_state()
    env = dict(os.environ, PATH=str(Path(sys.prefix) / 'bin') + ':' + os.environ['PATH'],
               PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS=str(args.threads), MKL_NUM_THREADS=str(args.threads), CUDA_VISIBLE_DEVICES='')
    cli = Path(sys.prefix) / 'bin/medaka_consensus'
    command = [str(cli), '-t', str(args.threads), '-i', str(reads), '-d', str(draft), '-o', str(base / 'native')]
    sources = [Path(__file__).resolve(), helper, cli, Path(sys.prefix) / 'bin/mini_align']
    source_hashes = {str(p.relative_to(root)): sha(p) for p in sources}
    (base / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    (base / 'state.json').write_text(json.dumps({'state': 'starting_native_original_cli', 'command': command}, indent=2) + '\n')
    print('Starting original medaka_consensus, full sample', flush=True)
    with (base / 'stdout').open('w') as stdout, (base / 'stderr').open('w') as stderr:
        proc = subprocess.run(command, cwd=base, env=env, stdout=stdout, stderr=stderr)
    (base / 'state.json').write_text(json.dumps({'state': 'terminal', 'returncode': proc.returncode}, indent=2) + '\n')
    assert proc.returncode == 0, proc.returncode
    consensus = base / 'native/consensus.fasta'
    result = fasta(consensus)
    assert set(result) == set(reference) and all(result.values())
    from medaka.datastore import DataStore
    with DataStore(str(base / 'native/consensus_probs.hdf'), 'r') as store:
        samples = sorted(store.sample_registry)
        assert len(samples) > 0
        rows = []
        for key in samples:
            sample = store.load_sample(key)
            assert sample.label_probs is not None and len(sample.label_probs) > 0
            rows.append({'sample': key, 'positions': len(sample.positions), 'probability_rows': len(sample.label_probs)})
    coverage = base / 'coverage.tsv'
    subprocess.run([str(Path(sys.prefix) / 'bin/samtools'), 'coverage', '-o', str(coverage), str(base / 'native/calls_to_draft.bam')], env=env, check=True)
    covered = list(csv.DictReader(coverage.open(), delimiter='\t'))
    assert {x['#rname'] for x in covered} == set(reference)
    covered_bases = sum(int(row['covbases']) for row in covered)
    assert covered_bases > sum(map(len, reference.values())) * 0.95, covered
    assert store_state() == before
    assert sha(reads) == review['reads_sha256'] and sha(draft) == review['draft_sha256']
    assert source_hashes == {str(p.relative_to(root)): sha(p) for p in sources}
    report = {'pass_native_computation_checks': True, 'formal_acceptance': False, 'source_sha256': source_hashes,
              'command': command, 'returncode': proc.returncode, 'reads_records': n, 'read_bases': bases,
              'draft_sequence_lengths': {name: len(seq) for name, seq in reference.items()},
              'consensus_sequence_lengths': {name: len(seq) for name, seq in result.items()},
              'consensus_sequence_sha256': {name: hashlib.sha256(seq.encode()).hexdigest() for name, seq in result.items()},
              'consensus_fasta_sha256': sha(consensus), 'consensus_equals_published_draft_DNA': result == reference,
              'native_hdf_samples': rows, 'coverage': covered, 'covered_reference_bases': covered_bases,
              'model_stores_unchanged': True, 'scope': 'Actual original fixed Medaka2.2.2 CLI, full published real bacterial sample/complete same-sample already-polished draft. Positive neural probability outputs and >95% reference coverage, full contig/DNA identity recorded. Software baseline for later producer comparison, not independent genome truth/error-rate improvement, not production resource/cache gate or full platform acceptance.'}
    (base / 'run.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'completed': True, 'native_hdf_samples': len(rows), 'covered_reference_bases': covered_bases}), flush=True)


if __name__ == '__main__':
    main()
