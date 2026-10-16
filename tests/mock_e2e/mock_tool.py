#!/usr/bin/env python3
"""External command doubles ONLY for wiring tests. Never use for biological results.

The real production process scripts execute these commands via an isolated PATH.
Each invocation validates its upstream input and leaves an audit JSON in work/.
SAM/BAM placeholders are explicitly NOT real alignments.
"""
import gzip
import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

args = sys.argv[1:]
tool = Path(sys.argv[0]).name


def arg(flag):
    return args[args.index(flag) + 1]


def write(path, text='MOCK external tool output\n'):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def require(path):
    path = Path(path)
    if not path.is_file() or not path.stat().st_size:
        raise ValueError(f'{tool}: missing or empty upstream input: {path}')
    return path


def fastq(path):
    path = require(path)
    opener = gzip.open if path.name.endswith('.gz') else open
    with opener(path, 'rt') as fh:
        lines = fh.read().splitlines()
    assert lines and len(lines) % 4 == 0, path
    for i in range(0, len(lines), 4):
        assert lines[i].startswith('@') and lines[i + 2] == '+'
        assert len(lines[i + 1]) == len(lines[i + 3]) > 0
    return '\n'.join(lines) + '\n'


def fasta(path):
    records = {}
    for line in require(path).read_text().splitlines():
        if line.startswith('>'):
            name = line[1:].split()[0]
            records[name] = ''
        elif line:
            records[name] += line
    assert records and all(records.values()), path
    return records


fixture = Path(os.environ['AUTOPLASM_MOCK_FIXTURE'])
write(f'mock-{tool}.json', json.dumps({'mock': True, 'tool': tool, 'argv': args}))
if tool == 'fastp':
    for src, dst in [('-i', '-o'), ('-I', '-O')]:
        fastq(arg(src))
        shutil.copyfile(arg(src), arg(dst))
    write(arg('--html'), '<html>MOCK fastp</html>')
    write(arg('--json'), '{"mock": true, "summary": {}}\n')
elif tool == 'fastqc':
    for read in args[-2:]:
        fastq(read)
        prefix = Path(read).name.removesuffix('.gz').removesuffix('.fastq').removesuffix('.fq') + '_fastqc'
        write(prefix + '.html', '<html>MOCK FastQC</html>')
        with zipfile.ZipFile(prefix + '.zip', 'w') as archive:
            archive.writestr(prefix + '/fastqc_data.txt', 'MOCK\n')
elif tool == 'multiqc':
    if 'ont' in arg('--filename'):
        reports = [Path(root) / name for root, dirs, files in os.walk('.', followlinks=True)
                   for name in files if name == 'NanoPlot-report.html']
        assert len(reports) == 6, f'Lost NanoPlot sample reports: {reports}'
    else:
        assert len(list(Path('.').rglob('*.fastp.json'))) == 6, 'Lost fastp sample reports'
    write(arg('--filename'), '<html>MOCK MultiQC</html>')
elif tool == 'megahit':
    fastq(arg('-1')); fastq(arg('-2'))
    write(Path(arg('-o')) / 'final.contigs.fa', (fixture / 'reference.fasta').read_text())
elif tool == 'metaquast.py':
    fasta(args[0])
    write(Path(arg('-o')) / 'report.tsv', 'Assembly\tMOCK\n# contigs\t2\n')
elif tool == 'genomad':
    assembly, output, database = map(Path, args[-3:])
    records = fasta(assembly)
    assert (database / 'MOCK_ONLY').is_file()
    summary = output / (assembly.stem + '_summary')
    prefix = summary / assembly.stem
    empty = os.environ.get('AUTOPLASM_MOCK_EMPTY') == '1'
    write(str(prefix) + '_plasmid_summary.tsv', 'seq_name\tlength\tplasmid_score\n' +
          ('' if empty else f'plasmid_1\t{len(records["plasmid_1"])}\t0.99\n'))
    write(str(prefix) + '_plasmid.fna', '' if empty else f'>plasmid_1\n{records["plasmid_1"]}\n')
    write(str(prefix) + '_virus_summary.tsv', 'seq_name\tvirus_score\n')
    write(output / 'MOCK_ONLY')
elif tool == 'bowtie2-build':
    write(args[1] + '.mock.json', json.dumps(fasta(args[0])))
elif tool == 'bowtie2':
    fastq(arg('-1')); fastq(arg('-2'))
    write(arg('-S'), json.dumps({'records': json.loads(require(arg('-x') + '.mock.json').read_text()),
                               'mappers': ['short']}))
elif tool == 'minimap2':
    fastq(args[-1])
    assert arg('-ax') == ('map-hifi' if os.environ['AUTOPLASM_MOCK_PLATFORM'] == 'pacbio_hifi' else 'map-ont')
    print(json.dumps({'records': fasta(args[-2]), 'mappers': ['long']}))
elif tool == 'samtools':
    if args[0] == 'fastq':
        source = json.loads(require(args[-1]).read_text())
        assert source['mock'] and source['format'] == 'bam'
        write(arg('-o'), fastq(source['fastq']))
    elif args[0] == 'sort':
        write(arg('-o'), require(args[-1]).read_text())
    elif args[0] == 'merge':
        inputs = args[args.index('-o') + 2:]
        payloads = [json.loads(require(path).read_text()) for path in inputs]
        mappers = [mapper for payload in payloads for mapper in payload['mappers']]
        expected = ['short', 'long'] if os.environ['AUTOPLASM_MOCK_PLATFORM'] == 'hybrid' else [
            'short' if os.environ['AUTOPLASM_MOCK_PLATFORM'] == 'illumina' else 'long']
        assert sorted(mappers) == sorted(expected), f'Merge lost or duplicated a mapper: {mappers}'
        assert all(payload['records'] == payloads[0]['records'] for payload in payloads)
        write(arg('-o'), json.dumps({'records': payloads[0]['records'], 'mappers': mappers}))
    else:
        raise ValueError(f'Unsupported samtools command: {args}')
elif tool == 'coverm':
    payload = json.loads(require(arg('--bam-files')).read_text())
    records = payload['records']
    scale = sum(1 if mapper == 'short' else 2 for mapper in payload['mappers'])
    output = arg('--output-file')
    samples = json.loads((fixture / 'truth.json').read_text())['samples']
    index = next(i for i, sid in enumerate(samples) if output.startswith(sid + '.'))
    rows = ['Contig\tMOCK Mean\tMOCK TPM\tMOCK RPKM']
    for name in records:
        value = (10 + 2 * index if name == 'plasmid_1' else 30 - index) * scale
        rows.append(f'{name}\t{value}\t{value * 100}\t{value * 10}')
    write(output, '\n'.join(rows) + '\n')
elif tool == 'python':
    assert args[:2] == ['-m', 'plasmidfinder'], args
    fasta(arg('-i'))
    write(Path(arg('-o')) / 'results_tab.tsv', 'contig\treplicon\nplasmid_1\tMOCK\n')
elif tool == 'mob_typer':
    fasta(arg('--infile'))
    write(arg('--out_file'), 'sample_id\tmobility\nplasmid_1\tMOCK\n')
elif tool == 'bakta':
    fasta(args[-1])
    time.sleep(float(os.environ.get('AUTOPLASM_MOCK_DELAY', '0')))
    write(Path(arg('--output')) / (arg('--prefix') + '.tsv'), 'contig\tannotation\nplasmid_1\tMOCK\n')
    write(Path(arg('--output')) / (arg('--prefix') + '.gbff'))
elif tool == 'amrfinder':
    fasta(arg('-n')); write(arg('-o'), 'Contig id\tGene symbol\nplasmid_1\tMOCK\n')
elif tool == 'isescan.py':
    fasta(arg('--seqfile')); write(Path(arg('--output')) / 'MOCK.tsv')
elif tool == 'integron_finder':
    fasta(args[-1]); write(Path(arg('--outdir')) / 'MOCK.tsv')
elif tool == 'metaphlan':
    for read in args[0].split(','):
        fastq(read)
    write(arg('-o'), '#clade_name\tNCBI_tax_id\trelative_abundance\tadditional_species\n'
          'k__Bacteria|s__Mock_host\t0\t100\t\n')
    write(arg('--mapout'))
elif tool == 'mmseqs':
    records = fasta(args[1])
    write(args[2] + '_cluster.tsv', ''.join(f'{name}\t{name}\n' for name in records))
    shutil.copyfile(args[1], args[2] + '_rep_seq.fasta')
elif tool == 'NanoPlot':
    fastq(arg('--fastq'))
    write(Path(arg('--outdir')) / 'NanoPlot-report.html', '<html>MOCK NanoPlot</html>')
elif tool == 'filtlong':
    print(fastq(args[-1]), end='')
elif tool == 'hifiadapterfilt.sh':
    assert len(args) % 2 == 0 and all(args[i] in ['-p', '-t', '-o'] for i in range(0, len(args), 2)), args
    prefix = arg('-p') if '-p' in args else ''
    inputs = [p for p in Path('.').glob(prefix + '*') if p.name.endswith(('.fastq', '.fq', '.fastq.gz', '.fq.gz'))]
    assert len(inputs) == 1, f'Expected one input in working directory, got {inputs}'
    source = inputs[0]
    stem = source.name.removesuffix('.gz').removesuffix('.fastq').removesuffix('.fq')
    output = Path(arg('-o') if '-o' in args else '.') / (stem + '.filt.fastq.gz')
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, 'wt') as fh:
        fh.write(fastq(source))
elif tool == 'flye':
    fastq(arg('--nano-raw'))
    assert '--meta' in args
    write(Path(arg('--out-dir')) / 'assembly.fasta', (fixture / 'reference.fasta').read_text())
    write(Path(arg('--out-dir')) / 'assembly_graph.gfa', 'H\tVN:Z:1.0\n')
elif tool in ['hifiasm', 'hifiasm_meta']:
    fastq(args[-1])
    suffix = '.p_ctg.gfa' if tool == 'hifiasm_meta' else '.bp.p_ctg.gfa'
    write(arg('-o') + suffix, ''.join(f'S\t{name}\t{seq}\n' for name, seq in fasta(fixture / 'reference.fasta').items()))
elif tool in ['OPERA-MS.pl', 'spades.py']:
    flags = ['--short-read1', '--short-read2', '--long-read'] if tool == 'OPERA-MS.pl' else ['-1', '-2', '--nanopore']
    for flag in flags:
        fastq(arg(flag))
    if tool == 'OPERA-MS.pl':
        assert int(arg('--num-processors')) >= 2, 'OPERA-MS requires at least two processors'
    else:
        assert '--meta' in args
    output = Path(arg('--out-dir') if tool == 'OPERA-MS.pl' else arg('-o'))
    write(output / 'contigs.fasta', (fixture / 'reference.fasta').read_text())
elif tool == 'dorado':
    assert args[0] == 'basecaller' and '--emit-fastq' in args
    source = json.loads(require(args[2]).read_text())
    assert source['mock'] and source['format'] == 'pod5'
    print(fastq(source['fastq']), end='')
else:
    raise ValueError(f'Unsupported mock command: {tool} {args}')
