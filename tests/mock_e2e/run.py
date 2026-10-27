#!/usr/bin/env python3
"""Execute production main.nf with isolated external-tool mocks and real Python steps."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

from generate import generate, SAMPLES

ROOT = Path(__file__).resolve().parents[2]
COMMANDS = ['fastp', 'fastqc', 'multiqc', 'megahit', 'quast.py', 'genomad',
            'bowtie2-build', 'bowtie2', 'samtools', 'coverm', 'plasmidfinder.py', 'mob_typer',
            'bakta', 'amrfinder', 'isescan.py', 'integron_finder', 'metaphlan', 'mmseqs',
            'NanoPlot', 'filtlong', 'hifiadapterfilt.sh', 'flye', 'hifiasm', 'hifiasm_meta',
            'minimap2', 'OPERA-MS.pl', 'spades.py', 'dorado', 'pigz', 'perl', 'python3']


def rows(path):
    with path.open() as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def fastq_records(path):
    with (gzip.open(path, 'rt') if str(path).endswith('.gz') else path.open()) as stream:
        lines = stream.read().splitlines()
    assert len(lines) % 4 == 0
    records = {}
    for i in range(0, len(lines), 4):
        assert lines[i].startswith('@') and lines[i + 2].startswith('+')
        assert len(lines[i + 1]) == len(lines[i + 3])
        name = lines[i][1:].split()[0]
        assert name not in records, f'Duplicate read ID: {name}'
        records[name] = [lines[i + 1], lines[i + 3]]
    return records


def current_audits(base, pattern, tasks=None):
    """Only inspect attempts referenced by this execution's explicit trace."""
    tasks = rows(base / 'trace.tsv') if tasks is None else tasks
    for audit in (base / 'work').rglob(pattern):
        matches = [t for t in tasks if str(audit.parent.relative_to(base / 'work')).startswith(t['hash'])]
        if matches:
            assert len(matches) == 1, 'Ambiguous task evidence: ' + str(audit)
            yield audit, matches[0]


def validate_native_long_host_reads(base, platform, assembler):
    truth = json.loads((base / 'fixture/truth.json').read_text())
    tool = {'ont': 'flye', 'pacbio_hifi': 'hifiasm_meta', 'hybrid': 'OPERA-MS.pl' if assembler == 'opera_ms' else 'spades.py'}[platform]
    audits = list(current_audits(base, 'mock-' + tool + '.json'))
    assert len(audits) == len(SAMPLES)
    for audit, task in audits:
        argv = json.loads(audit.read_text())['argv']
        if platform == 'ont': name = argv[argv.index('--nano-raw') + 1]
        elif platform == 'pacbio_hifi': name = argv[-1]
        else: name = argv[argv.index('--long-read' if assembler == 'opera_ms' else '--nanopore') + 1]
        sid = task['name'].rsplit(' (', 1)[1][:-1]
        allowed = set(truth['long_read_expected_after_host_removal'][sid])
        original = fastq_records(base / 'fixture' / sid / 'long.fastq.gz')
        expected = {key: value for key, value in original.items() if key in allowed}
        assert fastq_records(audit.parent / name) == expected, f'{sid}: assembler received wrong IDs/DNA/qualities'
    return True


def validate_report(base, platform, empty):
    out = base / 'out/report'
    assert all((out / name).is_file() for name in ['report.md', 'report.html', 'methods.md', 'report_data.json', 'report_inputs.json'])
    data = json.loads((out / 'report_data.json').read_text())
    manifest = json.loads((out / 'report_inputs.json').read_text())
    assert {r['sample_id'] for r in data['samples']} == set(SAMPLES)
    assert all(r['consensus_plasmids'] == (0 if empty else 1) for r in data['samples'])
    producers = {r['producer'] for r in manifest['records']}
    executed = {r['name'].split(' (')[0].split(':')[-1] for r in rows(base / 'trace.tsv')}
    assert executed - {'REPORT'} <= producers, f'Undocumented process outputs: {executed - producers - {"REPORT"}}'
    assert not next(r for r in data['sections'] if r['name'] == '12_network')['present']
    if platform == 'assembly':
        assert not producers.intersection({'FASTP', 'FILTLONG', 'METAPHLAN', 'COVERM_SHARED'})
        assert not next(r for r in data['sections'] if r['name'] == '01_qc')['present']
    assert 'OLD_SAMPLE' not in json.dumps(data)
    assert 'Reads were quality-filtered' not in data['methods']
    sys.path.insert(0, str(ROOT / 'tests'))
    from run_report_inputs import Cells
    parser = Cells(); parser.feed((out / 'report.html').read_text())
    for row in data['samples']:
        assert [row['sample_id'], str(row['consensus_plasmids']), str(row['circular']), row['detection_tools']] in parser.rows


def validate_assembly(base, empty):
    tasks = rows(base / 'trace.tsv')
    assert all(t['status'] in ['COMPLETED', 'CACHED'] and t['exit'] == '0' for t in tasks)
    counts = {}
    for task in tasks:
        name = task['name'].split(' (')[0].split(':')[-1]
        counts[name] = counts.get(name, 0) + 1
    expected = {name: 6 for name in ['QUAST', 'GENOMAD', 'PLASMID_CONSENSUS', 'PLASMID_STRUCTURE']}
    if not empty:
        expected.update({name: 6 for name in ['PLASMIDFINDER', 'PLASMIDFINDER_RESOURCE_PROBE', 'MOB_TYPER', 'BAKTA', 'AMRFINDERPLUS', 'ISESCAN', 'ISESCAN_RESOURCE_PROBE', 'INTEGRONFINDER', 'INTEGRONFINDER_RESOURCE_PROBE']})
        expected.update(PLASMID_CATALOG_PREPARE=1, MMSEQS2=1)
    expected['REPORT'] = 1
    assert counts == expected, (counts, expected)
    validate_report(base, 'assembly', empty)
    truth = json.loads((base / 'fixture/truth.json').read_text())
    for sid in SAMPLES:
        text = (base / 'out/04_plasmid_detection/consensus' / (sid + '.plasmid_contigs.fasta')).read_text()
        observed = {}
        current = None
        for line in text.splitlines():
            if line.startswith('>'):
                current = line[1:].split()[0]
                assert current not in observed, 'Duplicate consensus FASTA identifier'
                observed[current] = ''
            elif line:
                assert current is not None, 'Malformed consensus FASTA'
                observed[current] += line.strip()
        expected_fasta = {} if empty else {'plasmid_1': truth['reference_sequences'][sid]['plasmid_1']}
        assert observed == expected_fasta, f'{sid}: assembly consensus DNA belongs to another sample'
    return {'status': 'PASS', 'platform': 'assembly', 'empty_plasmids': empty,
            'tasks': len(tasks), 'mode': 'controlled external CLI observers, actual assembly workflow/R/report'}


def validate_observer_read_provenance(base, truth):
    """Compare mapper queries to generator truth and task metadata, not filenames."""
    tasks = rows(base / 'trace.tsv')
    checked = 0
    expected_hashes = {task['hash'] for task in tasks if any(task['name'].split(' (', 1)[0].split(':')[-1].startswith(prefix)
                       for prefix in ['BOWTIE2_ALIGN_', 'MINIMAP2_ALIGN_']) and not
                       (truth['host_removal'] and task['name'].split(' (', 1)[0].split(':')[-1] == 'MINIMAP2_ALIGN_HOST')}
    observed_hashes = set()
    for tool in ['bowtie2', 'minimap2']:
        for audit, task in current_audits(base, 'mock-' + tool + '.json', tasks):
            argv = json.loads(audit.read_text())['argv']
            if '--version' in argv:
                continue
            assert task['hash'] in expected_hashes, 'Unexpected observer in a native-only mapping task'
            assert task['hash'] not in observed_hashes, 'Duplicate current mapper evidence'
            observed_hashes.add(task['hash'])
            sid = task['name'].rsplit(' (', 1)[1][:-1]
            payloads = [json.loads(path.read_text()) for path in audit.parent.glob('*.bam')]
            assert len(payloads) == 1, f'{sid}: ambiguous mapper payload'
            payload = payloads[0]
            component = task['name'].split(' (', 1)[0].split(':')[-1]
            if component.endswith('_SHARED'):
                expected_reference = {}
                for sample_sequences in truth['reference_sequences'].values():
                    for sequence in sample_sequences.values():
                        canonical = min(sequence, sequence.translate(str.maketrans('ACGT', 'TGCA'))[::-1])
                        expected_reference['seq_' + hashlib.sha256(canonical.encode()).hexdigest()] = canonical
            elif component.endswith('_ABUNDANCE'):
                expected_reference = {'plasmid_1': truth['reference_sequences'][sid]['plasmid_1']}
            elif component.endswith('_HOST'):
                host = truth['host_reference_contigs'][sid]
                expected_reference = {host: truth['reference_sequences'][sid][host]}
            else:
                assert component.endswith('_COVERAGE'), 'Unknown alignment observer consumer: ' + component
                expected_reference = truth['reference_sequences'][sid]
            assert payload['records'] == expected_reference, f'{sid}: aligner index/reference differs from intended sample/catalogue'
            assert len(payload['mappers']) == 1
            kind = payload['mappers'][0]
            actual = {row['read_id']: row for row in payload['input_reads']}
            expected = {rid: origin for rid, origin in truth['read_origins'].items()
                        if origin['sample_id'] == sid and origin['kind'] == kind}
            if kind == 'long' and truth['host_removal']:
                allowed = set(truth['long_read_expected_after_host_removal'][sid])
                expected = {rid: origin for rid, origin in expected.items() if rid in allowed}
            assert set(actual) == set(expected), f'{sid}: mapper query sample/read attribution differs'
            for rid, origin in expected.items():
                dna = truth['reference_sequences'][sid][origin['contig']][origin['start']:origin['start'] + origin['length']]
                if origin['strand'] == '-':dna = dna.translate(str.maketrans('ACGT', 'TGCA'))[::-1]
                assert actual[rid]['length'] == len(dna) and actual[rid]['dna_sha256'] == hashlib.sha256(dna.encode()).hexdigest(), f'{sid}: mapper query DNA differs'
            checked += 1
    assert checked and observed_hashes == expected_hashes, 'Missing current mapper evidence'
    return checked


def validate(base, empty, platform='illumina', assembler='opera_ms', long_input='fastq'):
    if platform == 'assembly': return validate_assembly(base, empty)
    out = base / 'out'
    trace = rows(base / 'trace.tsv')
    assert trace and all(row['status'] in ['COMPLETED', 'CACHED'] and row['exit'] == '0' for row in trace), 'Failed/missing tasks'
    counts = {}
    for row in trace:
        name = row['name'].split(' (')[0].split(':')[-1]
        counts[name] = counts.get(name, 0) + 1
    expected = {name: 6 for name in ['QUAST', 'GENOMAD', 'PLASMID_CONSENSUS',
        'PLASMID_STRUCTURE', 'SAMTOOLS_MERGE', 'COVERM_CONTIG', 'METAPHLAN']}
    expected.update({name: 1 for name in ['STATISTICS_INPUTS', 'SHARED_CATALOGUE', 'SHARED_ABUNDANCE_TABLES',
        'DIVERSITY', 'DIFFERENTIAL_ABUNDANCE', 'REPORT']})
    expected.update(SAMTOOLS_VIEW_SHARED=6, COVERM_SHARED=6)
    truth = json.loads((base / 'fixture/truth.json').read_text())
    host_removal = truth.get('host_removal', False)
    if host_removal:
        expected.update(MINIMAP2_ALIGN_HOST=2, SAMTOOLS_VIEW_HOST=2, SAMTOOLS_FASTQ_HOST=2)
        if platform == 'hybrid': expected.update(BOWTIE2_BUILD_HOST=2, BOWTIE2_ALIGN_HOST=2)
    if platform in ['illumina', 'hybrid']:
        expected.update(BOWTIE2_BUILD_SHARED=1, BOWTIE2_ALIGN_SHARED=6)
    else:
        expected['MINIMAP2_ALIGN_SHARED'] = 6
    if platform in ['illumina', 'hybrid']:
        expected.update({name: 6 for name in ['FASTP', 'FASTQC', 'FASTQC_CLEAN',
                                             'BOWTIE2_BUILD_COVERAGE', 'BOWTIE2_ALIGN_COVERAGE']})
        expected['MULTIQC'] = 1
    if platform != 'illumina':
        expected.update(MINIMAP2_ALIGN_COVERAGE=6)
    if platform in ['ont', 'hybrid']:
        expected.update(NANOPLOT=6, FILTLONG=6)
        expected['MULTIQC_ONT' if platform == 'hybrid' else 'MULTIQC'] = 1
    if platform == 'pacbio_hifi':
        expected['HIFIADAPTERFILT'] = 6
    assembly_process = {'illumina': 'MEGAHIT', 'ont': 'METAFLYE', 'pacbio_hifi': 'HIFIASM_META',
                        'hybrid': 'OPERA_MS' if assembler == 'opera_ms' else 'HYBRIDSPADES'}[platform]
    expected[assembly_process] = 6
    if long_input in ['bam', 'mixed']:
        expected['SAMTOOLS_FASTQ'] = 6 if long_input == 'bam' else (3 if platform == 'pacbio_hifi' else 2)
    if long_input == 'pod5' or (long_input == 'mixed' and platform != 'pacbio_hifi'):
        expected['DORADO_BASECALL'] = 6 if long_input == 'pod5' else 2
    if not empty:
        expected.update({name: 6 for name in ['PLASMIDFINDER', 'PLASMIDFINDER_RESOURCE_PROBE', 'MOB_TYPER', 'BAKTA',
            'AMRFINDERPLUS', 'ISESCAN', 'ISESCAN_RESOURCE_PROBE', 'INTEGRONFINDER', 'INTEGRONFINDER_RESOURCE_PROBE']})
        if platform in ['illumina', 'hybrid']:
            expected.update(BOWTIE2_BUILD_ABUNDANCE=6, BOWTIE2_ALIGN_ABUNDANCE=6,
                            COVERM_ABUNDANCE=6)
        if platform != 'illumina':
            expected.update(MINIMAP2_ALIGN_ABUNDANCE=6, COVERM_ABUNDANCE_LONG=6)
        expected.update(PLASMID_CATALOG_PREPARE=1, MMSEQS2=1)
    assert counts == expected, f'Process coverage differs: actual={counts}, expected={expected}'
    validate_report(base, platform, empty)
    contigs = rows(out / 'tables/contig_abundance.tsv')
    plasmids = rows(out / 'tables/plasmid_abundance.tsv')
    assert len(contigs) == 2 * len(SAMPLES) ** 2 and {r['sample_id'] for r in contigs} == set(SAMPLES)
    assert len(plasmids) == (0 if empty else len(SAMPLES) ** 2)
    labels = {'seq_' + hashlib.sha256(min(dna, dna.translate(str.maketrans('ACGT', 'TGCA'))[::-1]).encode()).hexdigest():
              {'owner': sid, 'local_id': label, 'length': len(dna)}
              for sid, sequences in truth['reference_sequences'].items() for label, dna in sequences.items()}
    assert len(labels) == 2 * len(SAMPLES), 'Fixture sample DNA must be distinguishable'
    assert {row['contig_id'] for row in contigs} == set(labels)
    kind = 'short' if platform in ['illumina', 'hybrid'] else 'long'
    for row in contigs + plasmids:
        sid = row['sample_id']
        feature = labels[row.get('contig_id', row.get('plasmid_id'))]
        expected_count = truth['expected_primary_reads'][sid][kind][feature['local_id']]['count'] if feature['owner'] == sid else 0
        expected_bases = truth['expected_primary_reads'][sid][kind][feature['local_id']]['bases'] if feature['owner'] == sid else 0
        assert math.isclose(float(row['coverage']), expected_bases / feature['length'], abs_tol=1e-10), f'{sid}: incorrect read-derived coverage'
        assert int(row['raw_count']) == expected_count, f'{sid}: incorrect read-derived primary count'
        assert row['count_unit'] == 'primary_read_alignment'
    for sid in SAMPLES:
        consensus = rows(out / f'04_plasmid_detection/consensus/{sid}.plasmid_consensus.tsv')
        assert len(consensus) == (0 if empty else 1), f'{sid}: unexpected consensus count'
        assert sum(row['plasmid_call'] == 'plasmid' for row in consensus) == (0 if empty else 1)
    # diversity.R emits 4 metrics per sample (richness/shannon/simpson/pielou)
    assert len(rows(out / '11_diversity/diversity_metrics.tsv')) == 24
    expected_tested = sum(truth['expected_primary_reads'][feature['owner']][kind][feature['local_id']]['count'] > 0 for feature in labels.values())
    assert len(rows(out / '11_diversity/differential_abundance.tsv')) == expected_tested
    report = (out / 'report/report.md').read_text()
    assert '- Samples: 6' in report, 'Report lost samples'
    assert '- [x] `11_diversity`' in report, 'Report ran before diversity outputs were available'
    assert all(f'| {sid} | {0 if empty else 1} |' in report for sid in SAMPLES)
    assert f'- Platform: `{platform}`' in report
    cohort = json.loads((out / 'tables/statistics_inputs/validation.json').read_text())
    assert cohort['status'] == 'validated' and set(cohort['sample_ids']) == set(SAMPLES)
    metrics = rows(out / '11_diversity/diversity_metrics.tsv')
    assert len(metrics) == 4 * len(SAMPLES) and {r['sample_id'] for r in metrics} == set(SAMPLES)
    assert all(math.isfinite(float(r['value'])) for r in metrics), 'Nonfinite diversity value'
    beta = rows(out / '11_diversity/bray_curtis_matrix.tsv')
    assert len(beta) == len(SAMPLES) and {r['sample_id'] for r in beta} == set(SAMPLES)
    assert all(set(row) == {'sample_id', *SAMPLES} for row in beta)
    assert all(math.isfinite(float(row[sid])) for row in beta for sid in SAMPLES)
    profiles = list((out / '07_host_prediction/metaphlan').glob('*.metaphlan.tsv'))
    assert len(profiles) == 6, 'Host profiles must be unique per sample'
    audits = [(a, task, json.loads(a.read_text())['argv'])
              for a, task in current_audits(base, 'mock-metaphlan.json', trace)]
    real = [(audit, task, argv) for audit, task, argv in audits if '--input_type' in argv]
    assert len(real) == 6, f'Expected 6 metaphlan audits, got {len(real)}: {audits}'
    for audit, task, argv in real:
        # nf-core metaphlan/metaphlan puts flags first; the comma-separated
        # reads are the token right after `--input_type fastq`.
        reads = argv[argv.index('--input_type') + 2].split(',')
        assert len(reads) == (2 if platform in ['illumina', 'hybrid'] else 1)
        if platform == 'hybrid':
            sid = task['name'].rsplit(' (', 1)[1][:-1]
            # Host removal changes filenames. Check the staged paired short
            # records against the explicit pass-through observer fixture.
            for mate, name in enumerate(reads, 1):
                assert fastq_records(audit.parent / name) == fastq_records(base / 'fixture' / sid / f'R{mate}.fastq.gz'), 'Hybrid host profile must use short reads'
    if platform == 'hybrid' and not empty:
        for sid in SAMPLES:
            short = rows(out / f'10_abundance/coverm/{sid}.short.coverm.tsv')
            long = rows(out / f'10_abundance/coverm/{sid}.long.coverm.tsv')
            assert len(short) == len(long) == 1
            length = len(truth['reference_sequences'][sid]['plasmid_1'])
            for method, observed in [('short', short[0]), ('long', long[0])]:
                expected = truth['expected_primary_reads'][sid][method]['plasmid_1']
                assert math.isclose(float(observed['MOCK Mean']), expected['bases'] / length, abs_tol=1e-10)
                # These local abundance wrappers request mean/TPM/RPKM only;
                # the mandatory raw-count contract is checked on shared tables.
                assert math.isclose(float(observed['MOCK TPM']), 1e6 if expected['count'] else 0, abs_tol=1e-8)
                total_reads = sum(value['count'] for value in truth['expected_primary_reads'][sid][method].values())
                expected_rpkm = expected['count'] * 1e9 / length / total_reads if total_reads else 0
                assert math.isclose(float(observed['MOCK RPKM']), expected_rpkm, abs_tol=1e-8)
    if not empty:
        catalog = (out / '09_comparative_genomics/plasmid_catalog_input.fasta').read_text()
        assert all(f'>{sid}|plasmid_1' in catalog for sid in SAMPLES)
    checked_mappers = validate_observer_read_provenance(base, truth)
    if host_removal: validate_native_long_host_reads(base, platform, assembler)
    return {'status': 'PASS', 'mode': 'mock external tools; real Nextflow and repository R',
            'tasks': len(trace), 'process_counts': counts, 'empty_plasmids': empty,
            'platform': platform, 'hybrid_assembler': assembler if platform == 'hybrid' else None,
            'long_input': long_input if platform != 'illumina' else None,
            'native_long_host_retention_checked': host_removal, 'read_provenance_mapper_tasks': checked_mappers,
            'limitations': 'Toy unique exact-match alignments/assembler/classifier observers; no native assembler, quantifier, classifier, or biological accuracy claim. With host removal, only the long-host mapper/filter/FASTQ are native; paired short-host unmapped output remains an explicit pass-through interface observer.'}


def configure_long_input(fixture, platform, source):
    """BAM/POD5 are explicit JSON doubles, only meaningful to mock commands."""
    sheet = rows(fixture / 'samples.tsv')
    fields = list(sheet[0]) + ['bam', 'pod5']
    for index, row in enumerate(sheet):
        kind = source
        if source == 'mixed':
            options = ['bam', 'fastq'] if platform == 'pacbio_hifi' else ['pod5', 'bam', 'fastq']
            kind = options[index % len(options)]
        row.update(bam='', pod5='')
        # Keep FASTQ as well to verify POD5 > BAM > FASTQ routing priority.
        if kind in ['bam', 'pod5']:
            for extension in (['bam', 'pod5'] if kind == 'pod5' else ['bam']):
                path = fixture / row['sample_id'] / ('reads.mock.' + extension)
                path.write_text(json.dumps({'mock': True, 'unpaired': True, 'format': extension, 'fastq': row['long_reads']}))
                row[extension] = str(path)
    with (fixture / 'samples.tsv').open('w') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(sheet)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', required=True, help='New run directory; existing directories are rejected')
    parser.add_argument('--nextflow', default='nextflow')
    parser.add_argument('--empty-plasmids', action='store_true')
    parser.add_argument('--platform', choices=['illumina', 'ont', 'pacbio_hifi', 'hybrid', 'assembly'], default='illumina')
    parser.add_argument('--hybrid-assembler', choices=['opera_ms', 'hybridspades'], default='opera_ms')
    parser.add_argument('--long-input', choices=['fastq', 'bam', 'pod5', 'mixed'], default='fastq')
    parser.add_argument('--with-host-removal', action='store_true', help='Exercise real long-read host removal on two distinct references')
    parser.add_argument('--host-minimap-prefix', type=Path)
    parser.add_argument('--host-samtools-prefix', type=Path)
    args = parser.parse_args()
    if args.platform == 'illumina' and args.long_input != 'fastq':
        parser.error('Illumina does not accept a long-read source')
    if args.platform == 'pacbio_hifi' and args.long_input == 'pod5':
        parser.error('PacBio HiFi does not accept POD5')
    if args.with_host_removal and (args.platform not in ['ont', 'pacbio_hifi', 'hybrid'] or not args.host_minimap_prefix or not args.host_samtools_prefix):
        parser.error('Host-retention test requires a long-read platform and both native runtime prefixes')
    base = Path(args.outdir).resolve()
    base.mkdir(parents=True, exist_ok=False)
    fixture = generate(base / 'fixture', host_removal=args.with_host_removal)
    # Existing publication is deliberately untrusted input for the report.
    stale = base / 'out/04_plasmid_detection/consensus'
    stale.mkdir(parents=True)
    (stale / 'OLD_SAMPLE.plasmid_contigs.fasta').write_text('>old\nACGT\n')
    (base / 'out/12_network').mkdir()
    configure_long_input(fixture, args.platform, args.long_input)
    bindir = base / 'mock-bin'
    bindir.mkdir()
    mock = Path(__file__).with_name('mock_tool.py')
    # Use a wrapper so executable permissions on source files are not required.
    for command in COMMANDS:
        target = bindir / command
        source = Path(__file__).with_name('mock_python.py') if command == 'python3' else mock
        target.write_text('#!' + sys.executable + '\n' + source.read_text().split('\n', 1)[1])
        target.chmod(0o755)
    database = fixture / 'mock-db'
    database.mkdir()
    (database / 'MOCK_ONLY').write_text('Not a biological database\n')
    params = {name: str(database) for name in ['genomad_db', 'bakta_db', 'plasmidfinder_db',
        'mob_suite_db', 'amrfinderplus_db', 'metaphlan_db']}
    params.update(samplesheet=str(fixture / 'samples.tsv'), outdir=str(base / 'out'),
                  project_name='MOCK_E2E_NOT_BIOLOGICAL_RESULTS', run_fastqc=True,
                  platform=args.platform, hybrid_assembler=args.hybrid_assembler)
    (base / 'params.json').write_text(json.dumps(params, indent=2))
    (base / 'test.config').write_text('''process {
    executor = 'local'
    withName: '.*' { cpus = 1; memory = '256 MB'; time = '5 min' }
    withName: '.*:OPERA_MS' { cpus = 2 }
}
executor.queueSize = 6
conda.enabled = false
docker.enabled = false
singularity.enabled = false
''')
    if args.with_host_removal:
        mini = args.host_minimap_prefix.resolve() / 'bin'
        sam = args.host_samtools_prefix.resolve() / 'bin'
        minimap_version = subprocess.run([str(mini / 'minimap2'), '--version'], text=True, capture_output=True, check=True).stdout
        samtools_version = subprocess.run([str(sam / 'samtools'), '--version'], text=True, capture_output=True, check=True).stdout
        assert minimap_version.strip() == '2.30-r1287' and samtools_version.startswith('samtools 1.24\n')
        (base / 'native-host-environment.json').write_text(json.dumps({'minimap2': minimap_version, 'samtools': samtools_version,
            'scope': 'native long-host mapping/filter/FASTQ only; other tools including short-read host chain are explicit observers'}, indent=2) + '\n')
        with (base / 'test.config').open('a') as stream:
            stream.write("process {\n" + f"withName: '.*:MINIMAP2_ALIGN_HOST' {{ beforeScript = 'export PATH=\"{mini}:$PATH\"' }}\n"
                         + f"withName: '.*:SAMTOOLS_VIEW_HOST|.*:SAMTOOLS_FASTQ_HOST' {{ beforeScript = 'export PATH=\"{sam}:$PATH\"' }}\n}}\n")
    executable = shutil.which(args.nextflow)
    if not executable:
        raise RuntimeError(f'Nextflow unavailable: {args.nextflow}')
    command = [executable, '-log', str(base / 'nextflow.log'), '-c', str(base / 'test.config'),
        'run', str(ROOT / 'main.nf'), '-params-file', str(base / 'params.json'),
        '-work-dir', str(base / 'work'), '-with-trace', str(base / 'trace.tsv'), '-ansi-log', 'false']
    env = os.environ.copy()
    env.update(PATH=str(bindir) + os.pathsep + env['PATH'], AUTOPLASM_MOCK_FIXTURE=str(fixture),
               AUTOPLASM_MOCK_EMPTY='1' if args.empty_plasmids else '0', AUTOPLASM_MOCK_PLATFORM=args.platform)
    (base / 'command.json').write_text(json.dumps(command, indent=2))
    with (base / 'console.log').open('w') as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    print((base / 'console.log').read_text())
    if result.returncode:
        (base / 'validation.json').write_text(json.dumps({'status': 'FAIL', 'exit_code': result.returncode}))
        return result.returncode
    try:
        summary = validate(base, args.empty_plasmids, args.platform, args.hybrid_assembler, args.long_input)
    except (AssertionError, OSError, KeyError) as exc:
        summary = {'status': 'FAIL', 'reason': str(exc) or repr(exc)}
    (base / 'validation.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 0 if summary['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
