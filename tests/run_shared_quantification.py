#!/usr/bin/env python3
"""Native reference remapping on locked real DNA with explicit simulated reads.

Independent oracle: exact source sequences, predeclared coordinates and read
names. No classifier/assembly inference, wet-lab or abundance accuracy benchmark.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def rc(dna):
    return dna.translate(str.maketrans('ACGT', 'TGCA'))[::-1]


def seq(path):
    return ''.join(path.read_text().splitlines()[1:]).upper()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def run(base, references, bowtie, coverm, minimap, python_prefix, modes):
    lock = json.loads((ROOT / 'tests/structure-reference.lock.json').read_text())
    dna = {}
    for ref in lock['references']:
        p = references / (ref['accession'] + '.fasta')
        assert digest(p) == ref['files']['fasta']
        dna[ref['accession']] = seq(p)
    sequences = {'A': dna['NC_007941.1'], 'B': dna['NC_003903.1'], 'C': rc(dna['NC_007941.1']), 'D': ''}
    # Exact whole-sequence/RC oracle independently computes two reference IDs.
    feature = {sid: 'seq_' + hashlib.sha256(min(s, rc(s)).encode()).hexdigest() for sid, s in sequences.items() if s}
    fixture = base / 'fixtures'
    fixture.mkdir()
    coordinates = {}
    for sid, source in sequences.items():
        folder = fixture / sid
        folder.mkdir()
        cid = 'renamed' if sid == 'C' else 'NODE_1'
        fasta = '>' + cid + '\n' + source + '\n' if source else ''
        (folder / 'assembly.fasta').write_text(fasta)
        (folder / 'plasmids.fasta').write_text(fasta if sid in ['A', 'B'] else '')
        # Controlled detection products for the report interface only.
        (folder / 'consensus.tsv').write_text('sample_id\tcontig_id\tplasmid_call\tsupporting_tools\n' + (sid + '\t' + cid + '\tplasmid\tcontrolled_input\n' if sid in ['A', 'B'] else ''))
        (folder / 'structure.tsv').write_text('sample_id\tplasmid_id\tis_circular\n' + (sid + '\t' + cid + '\tfalse\n' if sid in ['A', 'B'] else ''))
        (folder / (sid + '.metaphlan.tsv')).write_text('clade_name\trelative_abundance\ns__controlled_host\t' + ('10' if sid in ['A', 'C'] else '0') + '\n')
        short = [[], []]
        long_reads = []
        # Select from a fixed coordinate grid using reference DNA only. Some
        # real references contain repeats; reject those coordinates before any
        # mapper executes rather than changing truth to match its output.
        starts = []
        lower = 100000 if sid == 'B' else 15000
        for start in range(lower, (len(source) - 2000) if source else lower + 14000, 700):
            reads = [source[start:start + 150], rc(source[start + 350:start + 500]), source[start:start + 2000]]
            if not source or all(sum(s.count(read) + s.count(rc(read)) for s in dna.values()) == 1 for read in reads):
                starts.append(start)
            if len(starts) == 20:
                break
        assert len(starts) == 20
        coordinates[sid] = starts
        for i, start in enumerate(starts):
            one = source[start:start + 150] if source else 'N' * 150
            two = rc(source[start + 350:start + 500]) if source else 'N' * 150
            long_seq = source[start:start + 2000] if source else 'N' * 2000
            # Exact full-read origin is independently unique across both DNA
            # references. Inference output never defines expected counts.
            if source:
                for read in [one, two, long_seq]:
                    assert sum(s.count(read) + s.count(rc(read)) for s in dna.values()) == 1
            for mate, read in enumerate([one, two]):
                short[mate].append(f'@{sid}_{i}/{mate + 1}\n{read}\n+\n' + 'I' * len(read) + '\n')
            long_reads.append(f'@{sid}_{i}\n{long_seq}\n+\n' + 'I' * len(long_seq) + '\n')
        for mate in [1, 2]:
            (folder / f'R{mate}.fastq').write_text(''.join(short[mate - 1]))
        (folder / 'long.fastq').write_text(''.join(long_reads))
    (base / 'coordinate-oracle.json').write_text(json.dumps({'source_accessions': {'A': 'NC_007941.1', 'B': 'NC_003903.1', 'C': 'reverse complement NC_007941.1', 'D': 'explicit unmapped Ns'}, 'zero_based_starts': coordinates, 'short': '150bp mates at start and start+350, reverse second mate', 'long': '2000bp at start', 'count_unit': 'primary_read_alignment'}, indent=2) + '\n')
    (fixture / 'samples.tsv').write_text('sample_id\tgroup\nA\tgroup1\nB\tgroup1\nC\tgroup2\nD\tgroup2\n')
    sources = ['bin/statistics_input_contract.R', 'bin/validate_statistics_inputs.py', 'modules/cross_sample/statistics_inputs.nf', 'modules/cross_sample/diversity.nf', 'bin/build_shared_catalogue.py', 'bin/collect_shared_abundance.py', 'modules/cross_sample/shared_catalogue.nf',
               'modules/cross_sample/shared_abundance.nf', 'subworkflows/shared_quantification.nf', 'conf/shared_quantification.config',
               'tests/nextflow/shared_quantification.nf', 'tests/run_shared_quantification.py', 'subworkflows/cross_sample.nf',
               'bin/diversity.R', 'bin/differential_abundance.R', 'bin/generate_report.R', 'subworkflows/host_linking.nf', 'bin/coabundance_link.R']
    hashes = {n: digest(ROOT / n) for n in sources}
    fixture_hashes = {str(p.relative_to(fixture)): digest(p) for p in fixture.rglob('*') if p.is_file()}
    runs = []
    for mode in modes:
        p = base / mode
        p.mkdir()
        out = p / 'out'
        config = p / 'native.config'
        config.write_text(f"includeConfig '{ROOT}/conf/shared_quantification.config'\n"
            "process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nprocess.maxForks=1\n"
            "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\nparams.publish_dir_mode='copy'\n"
            "process {\n" + f"withName: 'COVERM_SHARED' {{ beforeScript = 'export PATH=\"{coverm}/bin:$PATH\"' }}\n"
            + f"withName: 'SHARED_CATALOGUE|SHARED_ABUNDANCE_TABLES|STATISTICS_INPUTS' {{ beforeScript = 'export PATH=\"{python_prefix}/bin:$PATH\"' }}\n"
            + f"withName: 'MINIMAP2_ALIGN_SHARED' {{ beforeScript = 'export PATH=\"{minimap}/bin:$PATH\"' }}\n"
            + f"withName: 'SAMTOOLS_VIEW_SHARED' {{ beforeScript = 'export PATH=\"{coverm}/bin:$PATH\"' }}\n"
            + "}\n")
        params = {'outdir': str(out), 'fixture_dir': str(fixture), 'read_mode': mode,
                  'samplesheet': str(fixture / 'samples.tsv'), 'run_cross_sample': True,
                  'platform': 'illumina' if mode == 'short' else ('ont' if mode == 'map-ont' else 'pacbio_hifi'),
                  'run_diversity': True, 'min_diversity_samples': 3, 'run_differential_internal': True,
                  'min_group_replicates': 3, 'run_differential_deseq2': False, 'run_network': False,
                  'project_name': 'shared_reference_real_DNA_simulated_reads', 'host_plasmid_linking': True,
                  'host_linking_methods': ['co_abundance'], 'host_linking_optional_methods': [],
                  'link_correlation_method': 'pearson', 'link_min_correlation': 0.9}
        (p / 'params.json').write_text(json.dumps(params))
        command = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(ROOT / 'tests/nextflow/shared_quantification.nf'),
                   '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(bowtie / 'bin') + ':' + str(minimap / 'bin') + ':' + str(ROOT / 'bin') + ':' + env['PATH']
        result = subprocess.run(command, text=True, capture_output=True, env=env)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        tasks = table(p / 'trace.tsv')
        assert len(tasks) == (20 if mode == 'short' else 19), len(tasks)
        assert all(t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks)
        catalogue = out / '10_abundance/shared_reference/catalogue'
        features = table(catalogue / 'features.tsv')
        assert {r['feature_id'] for r in features} == set(feature.values())
        assert sorted(r['source_count'] for r in features) == ['1', '2']
        assert all(r['is_plasmid'] == '1' for r in features)
        for name in ['contig_abundance.tsv', 'plasmid_abundance.tsv']:
            rows = table(out / 'tables' / name)
            assert len(rows) == 8, rows
            observed = {(r['sample_id'], r['contig_id' if name.startswith('contig') else 'plasmid_id']): r for r in rows}
            for sid, source in sequences.items():
                for row in features:
                    fid = row['feature_id']
                    expected = (40 if mode == 'short' else 20) if fid == feature.get(sid) else 0
                    val = observed[(sid, fid)]
                    assert int(val['raw_count']) == expected, (mode, sid, fid, val, expected)
                    expected_mean = expected * (150 if mode == 'short' else 2000) / int(row['length_bp'])
                    assert math.isclose(float(val['coverage']), expected_mean, rel_tol=1e-5, abs_tol=1e-7)
                    assert val['count_unit'] == 'primary_read_alignment'
        states = table(out / 'tables/sample_states.tsv')
        assert {r['sample_id'] for r in states} == set(sequences)
        assert next(r for r in states if r['sample_id'] == 'D')['quantification_status'] == 'measured_zero'
        metrics = table(out / '11_diversity/diversity_metrics.tsv')
        assert {r['sample_id'] for r in metrics} == set(sequences)
        beta = table(out / '11_diversity/bray_curtis_matrix.tsv')
        # Independent TSS Bray-Curtis truth: A and C share DNA; B differs
        # despite the same original NODE_1 name. D is a measured zero sample.
        for row in beta:
            sid = row[next(iter(row))]
            for other in sequences:
                expected_distance = 0 if sid == other or {sid, other} == {'A', 'C'} else 1
                assert math.isclose(float(row[other]), expected_distance, abs_tol=1e-6), (sid, other, row)
        assert (out / 'report/report.md').exists()
        links = table(out / '07_host_prediction/coabundance_links.tsv')
        assert len(links) == 1, links
        assert links[0]['plasmid_id'] == feature['A'] and links[0]['sample_id'] == 'A,B,C,D'
        assert float(links[0]['score']) == 1.0
        # Check actual retained BAMs independently of CoverM counts.
        for task in [t for t in tasks if 'SAMTOOLS_VIEW_SHARED' in t['name']]:
            work = Path(task['workdir']) if task.get('workdir') else None
            # Trace default omits workdir; resolve by task hash.
            if work is None:
                prefix, suffix = task['hash'].split('/')
                work = next((p / 'work' / prefix).glob(suffix + '*'))
            bam = next(work.glob('*.shared.eligible.bam'))
            sid = bam.name.split('.')[0]
            mapped = subprocess.run([str(bowtie / 'bin/samtools'), 'view', str(bam)], capture_output=True, text=True, check=True).stdout.splitlines()
            assert len(mapped) == (0 if sid == 'D' else (40 if mode == 'short' else 20))
            assert all(line.split('\t')[2] == feature[sid] and not (int(line.split('\t')[1]) & 2308) and 10 <= int(line.split('\t')[4]) < 255 for line in mapped)
        runs.append({'mode': mode, 'command': command, 'exit': result.returncode, 'tasks': tasks, 'checks': 'two exact/RC references, colliding local IDs, C no own candidates still measured, D true zero, full sample-feature rectangle, raw counts/coverage and retained BAM oracle'})
        receipt = {'pass': len(runs) == len(modes), 'expected_modes': modes, 'runs': runs, 'source_sha256': hashes, 'fixture_sha256': fixture_hashes,
                   'limitations': ['locked real reference DNA with explicit in-silico reads and controlled host profiles, not wet-lab abundance/biological accuracy',
                                   'actual shared quantification plus CROSS_SAMPLE diversity/internal replication guard/report; platform calls changed but full platform/classifier execution not certified',
                                   'near-homologue ambiguity/globally empty cases are recorded separately; not image/nf-test/full platform/scientific accuracy certification']}
        assert hashes == {n: digest(ROOT / n) for n in sources}
        assert fixture_hashes == {str(q.relative_to(fixture)): digest(q) for q in fixture.rglob('*') if q.is_file()}
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print('PASS', mode, len(tasks), 'actual tasks', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    parser.add_argument('--references', required=True)
    parser.add_argument('--bowtie-prefix', required=True)
    parser.add_argument('--coverm-prefix', required=True)
    parser.add_argument('--minimap-prefix', required=True)
    parser.add_argument('--python-prefix', required=True)
    parser.add_argument('--modes', nargs='+', default=['short'], choices=['short', 'map-ont', 'map-hifi'])
    args = parser.parse_args()
    base = Path(args.work_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    run(base, Path(args.references).resolve(), Path(args.bowtie_prefix).resolve(), Path(args.coverm_prefix).resolve(), Path(args.minimap_prefix).resolve(), Path(args.python_prefix).resolve(), args.modes)
