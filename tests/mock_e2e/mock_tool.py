#!/usr/bin/env python3
"""External command doubles ONLY for wiring tests. Never use for biological results.

The real production process scripts execute these commands via an isolated PATH.
Each invocation validates its upstream input and leaves an audit JSON in work/.
SAM/BAM placeholders are explicitly NOT real alignments.

Adapted to the nf-core module command shapes of branch refactor/nf-core-modules
(version probes, stdout SAM pipes, gzipped assembly inputs, renamed outputs).
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
    return path


def require(path):
    path = Path(path)
    if not path.is_file() or not path.stat().st_size:
        raise ValueError(f'{tool}: missing or empty upstream input: {path}')
    return path


def _open_text(path):
    path = Path(path)
    with open(path, 'rb') as fh:
        magic = fh.read(2)
    # Assemblies are gzip products now; sniff the magic bytes instead of
    # trusting the file name so both plain and .gz inputs work.
    return gzip.open(path, 'rt') if magic == b'\x1f\x8b' else open(path, 'rt')


def fastq(path):
    path = require(path)
    with _open_text(path) as fh:
        lines = fh.read().splitlines()
    assert lines and len(lines) % 4 == 0, path
    for i in range(0, len(lines), 4):
        assert lines[i].startswith('@') and lines[i + 2] == '+'
        assert len(lines[i + 1]) == len(lines[i + 3]) > 0
    return '\n'.join(lines) + '\n'


def fasta(path):
    records = {}
    with _open_text(require(path)) as fh:
        for line in fh.read().splitlines():
            if line.startswith('>'):
                name = line[1:].split()[0]
                records[name] = ''
            elif line:
                records[name] += line
    assert records and all(records.values()), path
    return records


def positionals(tokens, flags_with_value=()):
    """Non-flag tokens minus the values consumed by flags that take one."""
    found = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token in flags_with_value:
            skip = True
            continue
        if not token.startswith('-'):
            found.append(token)
    return found


fixture = Path(os.environ['AUTOPLASM_MOCK_FIXTURE'])
# Version probes (nf-core `eval` version outputs invoke the tool a second time
# inside the task directory) must not clobber the real invocation audit.
probe = '-version' if args in (['--version'], ['version'], ['-v']) else ''
write(f'mock-{tool}{probe}.json', json.dumps({'mock': True, 'tool': tool, 'argv': args}))

if tool == 'pigz':
    if '--version' in args:
        print('pigz 2.8')
    else:
        # gzip each existing file argument in place (skip flags, flag values
        # and unmatched glob literals); megahit relies on this to compress
        # its *.fa products.
        for name in args:
            if name.startswith('-'):
                continue
            path = Path(name)
            if path.is_file():
                data = path.read_bytes()
                path.with_name(path.name + '.gz').write_bytes(gzip.compress(data, mtime=0))
                path.unlink()
elif tool == 'fastp':
    if '--version' in args:
        print('fastp 0.23.4')
    else:
        # nf-core fastp paired mode: --in1/--in2 inputs (symlinked aliases),
        # --out1/--out2 clean reads, --json/--html reports; the .log file is
        # produced by the module's own `2>| >(tee ...)` stderr pipe.
        for src, dst in [('--in1', '--out1'), ('--in2', '--out2')]:
            fastq(arg(src))
            shutil.copyfile(arg(src), arg(dst))
        write(arg('--html'), '<html>MOCK fastp</html>')
        write(arg('--json'), '{"mock": true, "summary": {}}\n')
        print('mock fastp log line', file=sys.stderr)
elif tool == 'fastqc':
    if '--version' in args:
        print('FastQC v0.13.0')
    else:
        # nf-core fastqc (local alias patch): `fastqc [args] --threads N
        # --memory M <renamed inputs>`; the renamed symlinks are the last
        # positional tokens.
        for read in positionals(args, ('--threads', '--memory', '-t', '-m')):
            fastq(read)
            prefix = Path(read).name.removesuffix('.gz').removesuffix('.fastq').removesuffix('.fq') + '_fastqc'
            write(prefix + '.html', '<html>MOCK FastQC</html>')
            with zipfile.ZipFile(prefix + '.zip', 'w') as archive:
                archive.writestr(prefix + '/fastqc_data.txt', 'MOCK\n')
elif tool == 'multiqc':
    if '--version' in args:
        print('multiqc, version 1.35')
    else:
        if 'ont' in arg('--filename'):
            reports = [Path(root) / name for root, dirs, files in os.walk('.', followlinks=True)
                       for name in files if name == 'NanoPlot-report.html']
            assert len(reports) == 6, f'Lost NanoPlot sample reports: {reports}'
        else:
            assert len(list(Path('.').rglob('*.fastp.json'))) == 6, 'Lost fastp sample reports'
        write(arg('--filename'), '<html>MOCK MultiQC</html>')
        # The *_data emit is non-optional in the vendored module.
        write(Path(arg('--filename')).stem + '_data/mock_data.txt', 'MOCK\n')
elif tool == 'megahit':
    if args == ['-v']:
        print('MEGAHIT v1.2.9')
    else:
        fastq(arg('-1')); fastq(arg('-2'))
        # nf-core megahit: no -o; the tool writes ./megahit_out and the module
        # pigz's the *.fa files and moves them up afterwards.
        prefix = arg('--out-prefix')
        write(Path('megahit_out') / (prefix + '.contigs.fa'),
              (fixture / 'reference.fasta').read_text())
        write(Path('megahit_out') / (prefix + '.log'), 'MOCK megahit log\n')
        for suffix in ['contigs.fa', 'addi.fa', 'local.fa', 'final.contigs.fa']:
            write(Path('megahit_out/intermediate_contigs') / f'k21.{suffix}',
                  (fixture / 'reference.fasta').read_text())
elif tool == 'quast.py':
    if '--version' in args:
        print('QUAST v5.3.0')
    else:
        # nf-core quast: `quast.py --output-dir <prefix> [--threads N] [args]
        # <assembly...>`; assemblies are the trailing positionals.
        fasta(positionals(args, ('--output-dir', '--threads', '-t', '--max-ref-number', '-r',
                                 '--features', '--min-contig', '-m'))[-1])
        write(Path(arg('--output-dir')) / 'report.tsv', 'Assembly\tMOCK\n# contigs\t2\n')
elif tool == 'genomad':
    if '--version' in args:
        print('geNomad, version 1.12.0')
    else:
        # nf-core genomad/endtoend: `genomad end-to-end <fasta> <prefix>/
        # <db> --threads N [args]`; the module gzips **/*.fna|*.faa itself.
        _subcommand, assembly, output, database = map(Path, positionals(args, ('--threads',)))
        records = fasta(assembly)
        assert (database / 'MOCK_ONLY').is_file()
        stem = assembly.name
        for ext in ['.gz', '.fa', '.fasta', '.fna']:
            stem = stem.removesuffix(ext)
        empty = os.environ.get('AUTOPLASM_MOCK_EMPTY') == '1'
        write(str(output / 'MOCK_ONLY'))
        summary = output / (stem + '_summary')
        prefix = summary / stem
        write(str(prefix) + '_plasmid_summary.tsv', 'seq_name\tlength\tplasmid_score\n' +
              ('' if empty else f'plasmid_1\t{len(records["plasmid_1"])}\t0.99\n'))
        write(str(prefix) + '_plasmid.fna', '' if empty else f'>plasmid_1\n{records["plasmid_1"]}\n')
        write(str(prefix) + '_plasmid_genes.tsv', 'mock\n')
        write(str(prefix) + '_plasmid_proteins.faa', '' if empty else '>p1\nM\n')
        write(str(prefix) + '_virus_summary.tsv', 'seq_name\tvirus_score\n')
        write(str(prefix) + '_virus.fna', '>virus_1\n' + ('A' * 100) + '\n')
        write(str(prefix) + '_virus_genes.tsv', 'mock\n')
        write(str(prefix) + '_virus_proteins.faa', '>vp1\nM\n')
        # non-optional emits of the vendored module
        write(output / (stem + '_annotate') / (stem + '_taxonomy.tsv'), 'mock\ttaxonomy\n')
        write(output / (stem + '_find_proviruses') / (stem + '_provirus.tsv'), 'mock\tprovirus\n')
elif tool == 'bowtie2-build':
    if '--version' in args:
        print('bowtie2-build-s version 2.5.4')
    else:
        # nf-core bowtie2/build: `bowtie2-build [args] --threads N <fasta>
        # bowtie2/<basename>`; the align module discovers the index via
        # `find -L ./ -name "*.rev.1.bt2"`, so the full fake index set plus
        # the payload JSON must live under bowtie2/.
        fasta_arg, index = positionals(args, ('--threads',))[:2]
        records = fasta(fasta_arg)
        write(index + '.mock.json', json.dumps(records))
        for suffix in ['.1.bt2', '.2.bt2', '.3.bt2', '.4.bt2', '.rev.1.bt2', '.rev.2.bt2']:
            write(index + suffix)
elif tool == 'bowtie2':
    if '--version' in args:
        print('bowtie2-align-s version 2.5.4')
    else:
        # nf-core bowtie2/align: SAM goes to stdout through a samtools pipe;
        # host removal additionally requests --un-conc-gz unmapped pairs.
        fastq(arg('-1')); fastq(arg('-2'))
        if '--un-conc-gz' in args:
            target = arg('--un-conc-gz')
            with gzip.open(target + '.1.gz', 'wt') as fh:
                fh.write(fastq(arg('-1')))
            with gzip.open(target + '.2.gz', 'wt') as fh:
                fh.write(fastq(arg('-2')))
        print(json.dumps({'records': json.loads(require(arg('-x') + '.mock.json').read_text()),
                          'mappers': ['short']}))
        print('mock bowtie2 alignment stats', file=sys.stderr)
elif tool == 'minimap2':
    if '--version' in args:
        print('2.28-r1209')
    else:
        # nf-core minimap2/align: `minimap2 -ax <preset> -t N <ref> <reads>
        # [-a] | samtools sort ...`; the trailing -a must be skipped when
        # locating the positional ref/reads arguments.
        positional = positionals(args, ('-ax', '-t', '-o', '-c'))
        fasta_ref, reads = positional[0], positional[1]
        data = fastq(reads)
        assert arg('-ax') == ('map-hifi' if os.environ['AUTOPLASM_MOCK_PLATFORM'] == 'pacbio_hifi' else 'map-ont')
        print(json.dumps({'records': fasta(fasta_ref), 'mappers': ['long'], 'fastq': data}))
elif tool == 'samtools':
    if args[0] == 'version':
        print('samtools 1.24')
    elif args[0] == 'cat':
        for name in args[1:]:
            if not name.startswith('-'):
                sys.stdout.write(require(name).read_text())
    elif args[0] == 'fastq':
        bam = next(a for a in args if a.endswith('.bam'))
        source = json.loads(require(bam).read_text())
        assert source['mock']
        if source.get('format') == 'bam':
            # uBAM double: the reads live in a fixture FASTQ path
            data = fastq(source['fastq'])
        elif 'fastq' in source:
            # alignment payload (host-removal chain): unmapped reads survive
            data = source['fastq']
        else:
            raise ValueError(f'{tool}: unsupported fastq payload: {source}')
        if '-1' in args:
            # separate mode (basecalling uBAM): unpaired records land in -0
            with gzip.open(arg('-0'), 'wt') as fh:
                fh.write(data)
        else:
            # interleave mode: stdout redirect to <prefix>_interleaved.fastq
            print(data, end='')
    elif args[0] == 'sort':
        # `samtools sort [args] -T prefix --threads N -o <out> [-]`; input is
        # stdin when the only positional is '-' (or none, e.g. minimap2 pipe).
        tokens = positionals(args[1:], ('--threads', '-@', '-o', '-T', '-m', '--reference', '-O',
                                        '--output-fmt'))
        data = sys.stdin.read() if not tokens or tokens[-1] == '-' else require(tokens[-1]).read_text()
        write(arg('-o'), data)
    elif args[0] == 'merge':
        # `samtools merge --threads N <out> 1/<in1> [2/<in2>]` (inputs staged
        # into numbered subdirectories; output is the first positional).
        tokens = positionals(args[1:], ('--threads', '--reference'))
        output, inputs = tokens[0], tokens[1:]
        payloads = [json.loads(require(path).read_text()) for path in inputs]
        mappers = [mapper for payload in payloads for mapper in payload['mappers']]
        expected = ['short', 'long'] if os.environ['AUTOPLASM_MOCK_PLATFORM'] == 'hybrid' else [
            'short' if os.environ['AUTOPLASM_MOCK_PLATFORM'] == 'illumina' else 'long']
        assert sorted(mappers) == sorted(expected), f'Merge lost or duplicated a mapper: {mappers}'
        assert all(payload['records'] == payloads[0]['records'] for payload in payloads)
        write(output, json.dumps({'records': payloads[0]['records'], 'mappers': mappers}))
    elif args[0] == 'view':
        # view either copies a payload BAM (`-f 4` host filtering) or collects
        # the aligner's stdout pipe (host-removal bowtie2 chain, input '-').
        tokens = positionals(args[1:], ('--threads', '-@', '-o', '-f', '-F', '-q', '-L', '--qname-file',
                                        '--output-unselected', '--reference'))
        data = sys.stdin.read() if not tokens or tokens[-1] == '-' else require(tokens[-1]).read_text()
        write(arg('-o'), data)
    elif args[0] == 'index':
        # local MAG bridge: `samtools index -@ N <bam>` next to the payload BAM
        target = positionals(args[1:], ('-@', '--threads', '-c', '-m'))[-1]
        write(target + '.bai')
    else:
        raise ValueError(f'Unsupported samtools command: {args}')
elif tool == 'coverm':
    if '--version' in args:
        print('coverm 0.7.0')
    else:
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
elif tool == 'plasmidfinder.py':
    # nf-core plasmidfinder: `plasmidfinder.py --legacy -i <fasta> -o ./ -x`;
    # the module renames the five hard-coded products with the task prefix.
    fasta(arg('-i'))
    outdir = Path(arg('-o'))
    write(outdir / 'data.json', '{"mock": true}\n')
    write(outdir / 'results.txt', 'MOCK results\n')
    write(outdir / 'results_tab.tsv', 'contig\treplicon\nplasmid_1\tMOCK\n')
    write(outdir / 'Hit_in_genome_seq.fsa', '>plasmid_1\n' + 'A' * 100 + '\n')
    write(outdir / 'Plasmid_seqs.fsa', '>plasmid_1\n' + 'A' * 100 + '\n')
elif tool == 'mob_typer':
    if '--version' in args:
        print('mob_typer 3.1.9')
    else:
        fasta(arg('--infile'))
        write(arg('--out_file'), 'sample_id\tmobility\nplasmid_1\tMOCK\n')
elif tool == 'bakta':
    if '--version' in args:
        print('bakta 1.11.0')
    else:
        # nf-core bakta/bakta: `bakta <fasta> --skip-sorf --threads N
        # --prefix <id> --db <db>`; all 11 products land flat in the task dir.
        fasta(args[0])
        time.sleep(float(os.environ.get('AUTOPLASM_MOCK_DELAY', '0')))
        prefix = arg('--prefix')
        write(prefix + '.tsv', 'contig\tannotation\nplasmid_1\tMOCK\n')
        for suffix in ['.embl', '.faa', '.ffn', '.fna', '.gbff', '.gff3',
                       '.hypotheticals.tsv', '.hypotheticals.faa', '.txt', '.json']:
            write(prefix + suffix)
elif tool == 'amrfinder':
    if '--version' in args:
        print('3.13.7')
    elif '--database_version' in args:
        print('Database version 2026-01-01.1')
    else:
        fasta(arg('-n') if '-n' in args else arg('-p'))
        # the module redirects stdout into <prefix>.tsv
        print('Contig id\tGene symbol\nplasmid_1\tMOCK')
elif tool == 'isescan.py':
    fasta(arg('--seqfile')); write(Path(arg('--output')) / 'MOCK.tsv')
elif tool == 'integron_finder':
    if '--version' in args:
        print('integron_finder version 2.0.5')
    else:
        # `integron_finder [args] --cpu N <fasta>`; products live in
        # Results_Integron_Finder_<basename>/ (input may arrive decompressed
        # by the module, so the basename is whatever positional was passed).
        target = positionals(args, ('--cpu',))[-1]
        fasta(target)
        base = Path(target).name
        outdir = Path(f'Results_Integron_Finder_{base}')
        write(outdir / (base + '.integrons'), 'mock\tintegrons\n')
        write(outdir / (base + '.summary'), 'mock\tsummary\n')
        write(outdir / 'integron_finder.out', 'MOCK\n')
elif tool == 'metaphlan':
    # nf-core metaphlan/metaphlan command shape:
    #   metaphlan --nproc <cpus> --input_type fastq <reads[,reads]> \
    #       --bowtie2out <prefix>.bowtie2out.txt --bowtie2db <dir> --index <name> \
    #       --biom <prefix>.biom --output_file <prefix>_profile.txt
    # The reads are the single token right after `--input_type fastq` (comma
    # separated for paired-end samples).
    if '--version' in args:
        print('MetaPhlAn version 4.1.1 (mock)')
    else:
        assert args[args.index('--input_type') + 1] == 'fastq', args
        for read in args[args.index('--input_type') + 2].split(','):
            fastq(read)
        write(arg('--output_file'), '#clade_name\tNCBI_tax_id\trelative_abundance\tadditional_species\n'
              'k__Bacteria|s__Mock_host\t0\t100\t\n')
        write(arg('--bowtie2out'), 'MOCK bowtie2 alignment\n')
        write(arg('--biom'), '{"mock": true}\n')
elif tool == 'mmseqs':
    # nf-core mmseqs/easycluster command shape:
    #   mmseqs easy-cluster <sequence> <prefix> tmp1 <args> --threads <cpus>
    if args[0] == 'version':
        print('MOCK mmseqs version 13.45111')
    else:
        assert args[0] == 'easy-cluster', args
        records = fasta(args[1])
        write(args[2] + '_cluster.tsv', ''.join(f'{name}\t{name}\n' for name in records))
        shutil.copyfile(args[1], args[2] + '_rep_seq.fasta')
        shutil.copyfile(args[1], args[2] + '_all_seqs.fasta')
elif tool == 'NanoPlot':
    if '--version' in args:
        print('NanoPlot 1.47.0')
    else:
        # nf-core nanoplot has no --outdir; reports land in the task directory
        fastq(arg('--fastq'))
        write('NanoPlot-report.html', '<html>MOCK NanoPlot</html>')
        write('NanoStats.txt', 'MOCK NanoStats\n')
elif tool == 'filtlong':
    if '--version' in args:
        print('Filtlong v0.2.1')
    else:
        # `filtlong [flags] <reads> 2>| >(tee <prefix>.log >&2) | gzip -n >
        # <prefix>.fastq.gz`; the clean reads go to stdout, the shell tee
        # writes the (non-optional) log file.
        print(fastq(args[-1]), end='')
        print('mock filtlong log line', file=sys.stderr)
elif tool == 'hifiadapterfilt.sh':
    if '--version' in args:
        print('HiFiAdapterFilt 3.0.0')
    else:
        # nf-core hifiadapterfilt: `hifiadapterfilt.sh -t N -o . [args]` after
        # the module symlinks the input to <prefix>.fastq.gz; the staged input
        # and the alias share the cwd, so process every FASTQ present and let
        # the module pick its own prefix's products.
        inputs = sorted(p for p in Path('.').glob('*') if p.name.endswith(('.fastq', '.fq', '.fastq.gz', '.fq.gz')))
        assert inputs, 'Expected at least one input in working directory'
        outdir = Path(arg('-o')) if '-o' in args else Path('.')
        for source in inputs:
            stem = source.name.removesuffix('.gz').removesuffix('.fastq').removesuffix('.fq')
            with gzip.open(outdir / (stem + '.filt.fastq.gz'), 'wt') as fh:
                fh.write(fastq(source))
            write(outdir / (stem + '.stats'), 'MOCK stats\n')
            write(outdir / (stem + '.contaminant.blastout'), 'MOCK\n')
            write(outdir / (stem + '.blocklist'), 'MOCK\n')
elif tool == 'flye':
    if '--version' in args:
        print('2.9.5')
    else:
        fastq(arg('--nano-raw'))
        assert '--meta' in args
        out = Path(arg('--out-dir'))
        write(out / 'assembly.fasta', (fixture / 'reference.fasta').read_text())
        write(out / 'assembly_graph.gfa', 'H\tVN:Z:1.0\nS\tcontig_1\t*\n')
        write(out / 'assembly_graph.gv', 'digraph { }\n')
        write(out / 'assembly_info.txt', '#seq_name\tlength\tcov.\tcircular\ncontig_1\t1000\t10\tN\n')
        write(out / 'flye.log', 'MOCK flye log\n')
        write(out / 'params.json', '{"mock": true}\n')
elif tool in ['hifiasm', 'hifiasm_meta']:
    fastq(args[-1])
    suffix = '.p_ctg.gfa' if tool == 'hifiasm_meta' else '.bp.p_ctg.gfa'
    write(arg('-o') + suffix, ''.join(f'S\t{name}\t{seq}\n' for name, seq in fasta(fixture / 'reference.fasta').items()))
elif tool in ['OPERA-MS.pl', 'spades.py']:
    if '--version' in args:
        print('SPAdes genome assembler v4.1.0')
    else:
        flags = ['--short-read1', '--short-read2', '--long-read'] if tool == 'OPERA-MS.pl' else ['-1', '-2', '--nanopore']
        for flag in flags:
            if flag in args:
                fastq(arg(flag))
        if tool == 'OPERA-MS.pl':
            assert int(arg('--num-processors')) >= 2, 'OPERA-MS requires at least two processors'
        else:
            assert '--meta' in args
        # nf-core spades writes into -o ./ and the module renames/gzips the
        # products; the FASTG copy is a local patch for SCAPP.
        output = Path(arg('--out-dir') if tool == 'OPERA-MS.pl' else arg('-o'))
        write(output / 'contigs.fasta', (fixture / 'reference.fasta').read_text())
        write(output / 'scaffolds.fasta', (fixture / 'reference.fasta').read_text())
        write(output / 'spades.log', 'MOCK spades log\n')
        write(output / 'assembly_graph.fastg', '### mock fastg\n')
        write(output / 'assembly_graph_with_scaffolds.gfa', 'H\tVN:Z:1.0\n')
elif tool == 'dorado':
    assert args[0] == 'basecaller' and '--emit-fastq' in args
    source = json.loads(require(args[2]).read_text())
    assert source['mock'] and source['format'] == 'pod5'
    print(fastq(source['fastq']), end='')
else:
    raise ValueError(f'Unsupported mock command: {tool} {args}')
