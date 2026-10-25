#!/usr/bin/env python3
"""Native complete CONCOCT MAG branch on fixed real DNA and controlled BAM.

The BAM is a deliberately constructed valid mapped-fragment fixture, not an
aligner performance test or wet-lab input. All binning/coverage helpers are
real1.1.0, and the production cut/clustering defaults are unchanged.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

from run_concoct_io import COMPOSITION_BLOB, ROOT, fasta


def run(base, fixture, prefix):
    data = fixture.read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == COMPOSITION_BLOB
    original = fasta(fixture)
    env = os.environ.copy()
    env['PATH'] = str(prefix / 'bin') + ':' + env['PATH']
    inputs = base / 'fixtures'
    inputs.mkdir()
    plain = inputs / 'official composition.fna'
    plain.write_bytes(data)
    compressed = inputs / 'official composition.fna.gz'
    with gzip.open(compressed, 'wb') as stream:
        stream.write(data)
    sam = inputs / 'controlled.sam'
    with sam.open('w') as stream:
        stream.write('@HD\tVN:1.6\tSO:unsorted\n')
        for cid, dna in original.items():
            stream.write('@SQ\tSN:' + cid + '\tLN:' + str(len(dna)) + '\n')
        for index, (cid, dna) in enumerate(original.items()):
            for start in range(0, len(dna) - 99, 200):
                for repeat in range(1 + index % 4):
                    stream.write('\t'.join([cid + '_' + str(start) + '_' + str(repeat), '0', cid, str(start + 1), '60', '100M', '*', '0', '0', dna[start:start + 100], 'I' * 100]) + '\n')
    bam = inputs / 'controlled.bam'
    command = [str(prefix / 'bin/samtools'), 'sort', '-O', 'BAM', '-o', str(bam), str(sam)]
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    (base / 'prepare-bam.stderr.log').write_text(result.stderr)
    assert result.returncode == 0
    inputs_sha = {q.name: hashlib.sha256(q.read_bytes()).hexdigest() for q in inputs.iterdir()}
    config = base / 'config'
    config.write_text("includeConfig '" + str(ROOT / 'conf/nfcore_mag.config') + "'\n"
                      "params.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=1\n"
                      "process.memory='2 GB'\nprocess.maxForks=1\nconda.enabled=false\n"
                      "docker.enabled=false\nsingularity.enabled=false\n")
    records = [{'id': sid, 'group': group, 'fasta': str(assembly), 'bam': str(bam)} for sid, group, assembly in [('S1', 'G1', plain), ('S.2', 'G2', compressed)]]
    params = {'records': records, 'mag_tools': ['concoct'], 'outdir': str(base / 'out')}
    (base / 'params.json').write_text(json.dumps(params))
    command = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config), 'run', str(ROOT / 'tests/nextflow/concoct_mag.nf'), '-params-file', str(base / 'params.json'), '-work-dir', str(base / 'work'), '-with-trace', str(base / 'trace.tsv'), '-ansi-log', 'false']
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    (base / 'stdout.log').write_text(result.stdout)
    (base / 'stderr.log').write_text(result.stderr)
    tasks = list(csv.DictReader((base / 'trace.tsv').open(), delimiter='\t')) if (base / 'trace.tsv').exists() else []
    expected_nodes = ['SAMTOOLS_INDEX', 'CONCOCT_CUTUPFASTA', 'CONCOCT_CONCOCTCOVERAGETABLE', 'CONCOCT_CONCOCT', 'CONCOCT_MERGECUTUPCLUSTERING', 'CONCOCT']
    checks = {'success': result.returncode == 0, 'twelve_native_completed_tasks': len(tasks) == 12 and all(t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks), 'each_native_node_once_per_sample': all(sum(t['name'].split(':')[-1].split(' (')[0] == name for t in tasks) == 2 for name in expected_nodes), 'all_inputs_unchanged': inputs_sha == {q.name: hashlib.sha256(q.read_bytes()).hexdigest() for q in inputs.iterdir()}}
    if checks['success']:
        out = base / 'out/07_host_prediction/mag/concoct'
        all_bins = {}
        for sid, group in [('S1', 'G1'), ('S.2', 'G2')]:
            checks[sid + '_one_meta_tuple'] = result.stdout.count('FINAL_BINS=' + sid + ':' + group + ':') == 1
            merged = list(csv.DictReader((out / (sid + '.csv')).open()))
            expected = {}
            for row in merged:
                expected.setdefault(sid + '_' + row['cluster_id'] + '.fa.gz', {})[row['contig_id']] = original[row['contig_id']]
            bins = {q.name: fasta(q) for q in (out / 'bins' / sid).glob('*.fa.gz')}
            checks[sid + '_nonempty_final_bins'] = bool(bins)
            checks[sid + '_all_bin_IDs_DNA_equal_membership_and_original'] = bins == expected
            checks[sid + '_no_contig_duplicated_across_bins'] = len([cid for members in bins.values() for cid in members]) == len({cid for members in bins.values() for cid in members})
            parts = fasta(out / 'cutup_fasta' / (sid + '.fasta'))
            rows = list(csv.reader((out / 'cutup_fasta' / (sid + '.bed')).open(), delimiter='\t'))
            checks[sid + '_coverage_BED_maps_exact_part_DNA'] = len(rows) == len(parts) and all(0 <= int(row[1]) < int(row[2]) <= len(original[row[0]]) and original[row[0]][int(row[1]):int(row[2])] == parts[row[3]] for row in rows)
            all_bins[sid] = {frozenset(members) for members in bins.values()}
        checks['plain_gzip_same_cluster_memberships'] = all_bins['S1'] == all_bins['S.2']
    sources = ['bin/run_concoct_cut_checked.py', 'modules/nf-core/concoct/cutupfasta/main.nf', 'modules/nf-core/concoct/extractfastabins/main.nf', 'subworkflows/mag_host.nf', 'tests/nextflow/concoct_mag.nf', 'tests/run_concoct_mag.py']
    receipt = {'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks, 'pass': all(checks.values()), 'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sources}, 'limitations': ['actual native SAMtools1.24 and CONCOCT1.1.0 full original MAG branch; same real official DNA in plain/gzip; explicitly controlled valid BAM', 'cluster membership checks format/reference consistency and reproducibility, not independent biological binning accuracy', 'no quality/taxonomy/database, image/nf-test framework or complete platform/P4 certification']}
    (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(checks, flush=True)
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--fixture', required=True, type=Path)
    parser.add_argument('--prefix', required=True, type=Path)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run(args.work_dir.resolve(), args.fixture.resolve(), args.prefix.resolve()) else 1)
