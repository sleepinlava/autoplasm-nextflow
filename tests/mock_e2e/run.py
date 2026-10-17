#!/usr/bin/env python3
"""Execute production main.nf with isolated external-tool mocks and real Python steps."""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from generate import generate, SAMPLES

ROOT = Path(__file__).resolve().parents[2]
COMMANDS = ['fastp', 'fastqc', 'multiqc', 'megahit', 'metaquast.py', 'genomad',
            'bowtie2-build', 'bowtie2', 'samtools', 'coverm', 'python', 'mob_typer',
            'bakta', 'amrfinder', 'isescan.py', 'integron_finder', 'metaphlan', 'mmseqs',
            'NanoPlot', 'filtlong', 'hifiadapterfilt.sh', 'flye', 'hifiasm', 'hifiasm_meta',
            'minimap2', 'OPERA-MS.pl', 'spades.py', 'dorado']


def rows(path):
    with path.open() as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def validate(base, empty, platform='illumina', assembler='opera_ms', long_input='fastq'):
    out = base / 'out'
    trace = rows(base / 'trace.tsv')
    assert trace and all(row['status'] == 'COMPLETED' for row in trace), 'Failed/missing tasks'
    counts = {}
    for row in trace:
        name = row['name'].split(' (')[0].split(':')[-1]
        counts[name] = counts.get(name, 0) + 1
    expected = {name: 6 for name in ['QUAST', 'GENOMAD', 'PLASMID_CONSENSUS',
        'PLASMID_STRUCTURE', 'SAMTOOLS_MERGE', 'COVERM_CONTIG', 'METAPHLAN']}
    expected.update({name: 1 for name in ['MERGE_ABUNDANCE',
        'MERGE_ABUNDANCE_PLASMID', 'DIVERSITY', 'DIFFERENTIAL_ABUNDANCE', 'REPORT']})
    if platform in ['illumina', 'hybrid']:
        expected.update({name: 6 for name in ['FASTP', 'FASTQC', 'FASTQC_CLEAN',
                                             'BOWTIE2_CONTIG_COVERAGE', 'SAMTOOLS_SORT']})
        expected['MULTIQC'] = 1
    if platform != 'illumina':
        expected.update(MINIMAP2_CONTIG_COVERAGE=6, SAMTOOLS_SORT_LONG=6)
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
        expected.update({name: 6 for name in ['PLASMIDFINDER', 'MOB_TYPER', 'BAKTA',
            'AMRFINDERPLUS', 'ISESCAN', 'INTEGRONFINDER']})
        if platform in ['illumina', 'hybrid']:
            expected.update(BOWTIE2_ABUNDANCE=6, SAMTOOLS_SORT_ABUND=6, COVERM_ABUNDANCE=6)
        if platform != 'illumina':
            expected.update(MINIMAP2_ABUNDANCE=6, SAMTOOLS_SORT_ABUND_LONG=6, COVERM_ABUNDANCE_LONG=6)
        expected.update(PLASMID_CATALOG_PREPARE=1, MMSEQS2=1)
    assert counts == expected, f'Process coverage differs: actual={counts}, expected={expected}'
    contigs = rows(out / 'tables/contig_abundance.tsv')
    plasmids = rows(out / 'tables/plasmid_abundance.tsv')
    assert len(contigs) == 12 and {r['sample_id'] for r in contigs} == set(SAMPLES)
    assert len(plasmids) == (0 if empty else 6)
    for row in contigs + plasmids:
        index = SAMPLES.index(row['sample_id'])
        feature = row.get('contig_id', row.get('plasmid_id'))
        scale = (3 if platform == 'hybrid' else 1 if platform == 'illumina' else 2) if 'contig_id' in row else (
            1 if platform in ['illumina', 'hybrid'] else 2)
        assert float(row['coverage']) == (10 + index * 2 if feature == 'plasmid_1' else 30 - index) * scale
    for sid in SAMPLES:
        consensus = rows(out / f'04_plasmid_detection/consensus/{sid}.plasmid_consensus.tsv')
        assert len(consensus) == (0 if empty else 1), f'{sid}: unexpected consensus count'
        assert sum(row['plasmid_call'] == 'plasmid' for row in consensus) == (0 if empty else 1)
    # diversity.R emits 4 metrics per sample (richness/shannon/simpson/pielou)
    assert len(rows(out / '11_diversity/diversity_metrics.tsv')) == 24
    assert len(rows(out / '11_diversity/differential_abundance.tsv')) == 2
    report = (out / 'report/report.md').read_text()
    assert '- Samples: 6' in report, 'Report lost samples'
    assert '- [x] `11_diversity`' in report, 'Report ran before diversity outputs were available'
    assert all(f'| {sid} | {0 if empty else 1} |' in report for sid in SAMPLES)
    assert f'- Platform: `{platform}`' in report
    profiles = list((out / '07_host_prediction/metaphlan').glob('*.metaphlan.tsv'))
    assert len(profiles) == 6, 'Host profiles must be unique per sample'
    audits = [json.loads(a.read_text())['argv']
              for a in (base / 'work').rglob('mock-metaphlan.json')]
    real = [argv for argv in audits if '--input_type' in argv]
    assert len(real) == 6, f'Expected 6 metaphlan audits, got {len(real)}: {audits}'
    for argv in real:
        # nf-core metaphlan/metaphlan puts flags first; the comma-separated
        # reads are the token right after `--input_type fastq`.
        reads = argv[argv.index('--input_type') + 2].split(',')
        assert len(reads) == (2 if platform in ['illumina', 'hybrid'] else 1)
        if platform == 'hybrid':
            assert all('.clean.fastq.gz' in name for name in reads), 'Hybrid host profile must use short reads'
    if platform == 'hybrid' and not empty:
        for sid in SAMPLES:
            short = rows(out / f'10_abundance/coverm/{sid}.short.coverm.tsv')
            long = rows(out / f'10_abundance/coverm/{sid}.long.coverm.tsv')
            assert len(short) == len(long) == 1
            assert float(long[0]['MOCK Mean']) == 2 * float(short[0]['MOCK Mean'])
    if not empty:
        catalog = (out / '09_comparative_genomics/plasmid_catalog_input.fasta').read_text()
        assert all(f'>{sid}|plasmid_1' in catalog for sid in SAMPLES)
    return {'status': 'PASS', 'mode': 'mock external tools; real Nextflow and repository R',
            'tasks': len(trace), 'process_counts': counts, 'empty_plasmids': empty,
            'platform': platform, 'hybrid_assembler': assembler if platform == 'hybrid' else None,
            'long_input': long_input if platform != 'illumina' else None}


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
                path.write_text(json.dumps({'mock': True, 'format': extension, 'fastq': row['long_reads']}))
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
    parser.add_argument('--platform', choices=['illumina', 'ont', 'pacbio_hifi', 'hybrid'], default='illumina')
    parser.add_argument('--hybrid-assembler', choices=['opera_ms', 'hybridspades'], default='opera_ms')
    parser.add_argument('--long-input', choices=['fastq', 'bam', 'pod5', 'mixed'], default='fastq')
    args = parser.parse_args()
    if args.platform == 'illumina' and args.long_input != 'fastq':
        parser.error('Illumina does not accept a long-read source')
    if args.platform == 'pacbio_hifi' and args.long_input == 'pod5':
        parser.error('PacBio HiFi does not accept POD5')
    base = Path(args.outdir).resolve()
    base.mkdir(parents=True, exist_ok=False)
    fixture = generate(base / 'fixture')
    configure_long_input(fixture, args.platform, args.long_input)
    bindir = base / 'mock-bin'
    bindir.mkdir()
    mock = Path(__file__).with_name('mock_tool.py')
    # Use a wrapper so executable permissions on source files are not required.
    for command in COMMANDS:
        target = bindir / command
        target.write_text('#!' + sys.executable + '\n' + mock.read_text().split('\n', 1)[1])
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
    executable = shutil.which(args.nextflow)
    if not executable:
        raise RuntimeError(f'Nextflow unavailable: {args.nextflow}')
    command = [executable, '-log', str(base / 'nextflow.log'), '-c', str(base / 'test.config'),
        '-c', str(ROOT / 'conf/nfcore_host_comparative.config'),
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
