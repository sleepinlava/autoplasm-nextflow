#!/usr/bin/env python3
"""Explicit synthetic CLI observers for MAG routing; never biological evidence.

The real production Nextflow processes run unchanged. This observer only
checks staged identities and supplies controlled predictions/consumer records.
GTDB-Tk records staged files here; its real extension filter is NOT exercised.
"""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import re

tool = Path(sys.argv[0]).name
args = sys.argv[1:]


def arg(flag):
    return args[args.index(flag) + 1]


def read_fasta(path):
    path = Path(path)
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as stream:
        seqs = {}
        for line in stream:
            if line.startswith('>'):
                cid = line[1:].split()[0]
                assert cid not in seqs
                seqs[cid] = ''
            else:
                seqs[cid] += line.strip()
    assert seqs and all(seqs.values())
    return seqs


def write_fasta(path, seqs):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with (gzip.open(path, 'wt') if path.suffix == '.gz' else path.open('w')) as stream:
        stream.write(''.join('>' + k + '\n' + v + '\n' for k, v in seqs.items()))


def record(kind, bins):
    payload = {Path(p).name: {k: hashlib.sha256(v.encode()).hexdigest() for k, v in read_fasta(p).items()} for p in bins}
    Path('observer-' + kind + '.json').write_text(json.dumps(payload, sort_keys=True))


if '--version' in args:
    print({'samtools': 'samtools 1.24', 'concoct': 'concoct 1.1.0', 'DAS_Tool': 'DAS Tool 1.1.7', 'gtdbtk': 'GTDB-Tk v2.7.2'}.get(tool, 'INTERFACE_OBSERVER'))
    raise SystemExit()
if tool == 'metabat2' and '--help' in args:
    print('INTERFACE_OBSERVER\nversion:2.17')
    raise SystemExit()
if tool == 'samtools':
    assert args[0] == 'index'
    payload = json.loads(Path(args[-1]).read_text())
    Path(args[-1] + '.bai').write_text(json.dumps(payload))
elif tool == 'jgi_summarize_bam_contig_depths':
    bam = Path(args[-1])
    payload = json.loads(bam.read_text())
    assert json.loads(Path(str(bam) + '.bai').read_text()) == payload
    Path(arg('--outputDepth')).write_text(json.dumps(payload))
elif tool == 'metabat2':
    seqs = read_fasta(arg('-i'))
    sid = next(iter(seqs)).rsplit('_', 1)[0]
    assert json.loads(Path(arg('-a')).read_text())['id'] == sid
    time.sleep(0.4 if sid == 'S1' else 0)
    prefix = arg('-o')
    Path(prefix).write_text('INTERFACE_OBSERVER membership\n')
    # A successful optional no-bin case, distinct from a tool failure.
    if sid not in os.environ.get('MAG_EMPTY_METABAT', '').split(','):
        for i, letter in enumerate(['A', 'B'], 1):
            write_fasta(prefix + '.' + str(i) + '.fa', {sid + '_' + letter: seqs[sid + '_' + letter]})
elif tool == 'cut_up_fasta.py':
    seqs = read_fasta(args[0])
    Path(arg('-b')).write_text(json.dumps(seqs))
    print(''.join('>' + k + '\n' + v + '\n' for k, v in seqs.items()), end='')
elif tool == 'concoct_coverage_table.py':
    rows = [line.split('\t') for line in Path(args[0]).read_text().splitlines()]
    sid = rows[0][0].rsplit('_', 1)[0]
    assert all(row[0].rsplit('_', 1)[0] == sid and 0 <= int(row[1]) < int(row[2]) for row in rows)
    assert json.loads(Path(args[1]).read_text())['id'] == sid
    assert Path(args[1] + '.bai').exists()
    print(sid)
elif tool == 'concoct':
    seqs = read_fasta(arg('--composition_file'))
    originals = {cid: re.sub(r'\.concoct_part_\d+$', '', cid) for cid in seqs}
    sid = next(iter(originals.values())).rsplit('_', 1)[0]
    assert Path(arg('--coverage_file')).read_text().strip() == sid
    prefix = arg('-b')
    for suffix in ['_args.txt', '_log.txt', '_original_data_gt1000.csv', '_PCA_components_data_gt1000.csv', '_PCA_transformed_data_gt1000.csv']:
        Path(prefix + suffix).write_text('INTERFACE_OBSERVER\n')
    rows = '' if sid in os.environ.get('MAG_EMPTY_CONCOCT', '').split(',') else ''.join(cid + ',' + ('1' if original.endswith('_B') else '2') + '\n' for cid, original in originals.items() if original.endswith(('_B', '_C')))
    Path(prefix + '_clustering_gt1000.csv').write_text('contig_id,cluster_id\n' + rows)
elif tool == 'merge_cutup_clustering.py':
    print(Path(args[-1]).read_text(), end='')
elif tool == 'extract_fasta_bins.py':
    seqs = read_fasta(args[0])
    for row in Path(args[1]).read_text().splitlines()[1:]:
        cid, cluster = row.split(',')
        write_fasta(Path(arg('--output_path')) / (cluster + '.fa'), {cid: seqs[cid]})
elif tool == 'SemiBin2':
    seqs = read_fasta(arg('--input-fasta'))
    sid = next(iter(seqs)).rsplit('_', 1)[0]
    assert json.loads(Path(arg('--input-bam')).read_text())['id'] == sid
    if os.environ.get('MAG_FAIL_SEMIBIN'):
        raise SystemExit('CONTROLLED_SEMIBIN_FAILURE')
    out = Path(arg('--output'))
    out.mkdir()
    (out / 'contig_bins.tsv').write_text('contig\tbin\n' + sid + '_C\t0\n')
    (out / 'data.csv').write_text('INTERFACE_OBSERVER\n')
    (out / 'output_bins').mkdir()
    header = 'filename\tnbps\tnr_contigs\tN50\tL50\n'
    empty_samples = os.environ.get('MAG_EMPTY_SEMIBIN', '').split(',')
    if sid in empty_samples:
        (out / 'contig_bins.tsv').write_text('contig\tbin\n' + sid + '_C\t-1\n')
        (out / 'recluster_bins_info.tsv').write_text(header)
    else:
        bin_path = out / 'output_bins/SemiBin_0.fa.gz'
        write_fasta(bin_path, {sid + '_C': seqs[sid + '_C']})
        length = len(seqs[sid + '_C'])
        (out / 'recluster_bins_info.tsv').write_text(header + str(bin_path) + f'\t{length}\t1\t{length}\t1\n')
elif tool == 'DAS_Tool':
    seqs = read_fasta(arg('-c'))
    sid = next(iter(seqs)).rsplit('_', 1)[0]
    names = set()
    members = set()
    for table in arg('-i').split(','):
        names.add(Path(table).name)
        for row in Path(table).read_text().splitlines():
            cid, bid = row.split('\t')
            assert cid in seqs and cid.startswith(sid + '_')
            members.add(cid)
    Path('observer-DAS-inputs.json').write_text(json.dumps({'sample': sid, 'tables': sorted(names), 'members': sorted(members)}))
    prefix = arg('-o')
    Path(prefix + '_DASTool.log').write_text('INTERFACE_OBSERVER_ONLY\n')
    if '--write_bins' in args:
        write_fasta(prefix + '_DASTool_bins/controlled.fa', {k: seqs[k] for k in sorted(members)})
elif tool == 'checkm2':
    start = args.index('--input') + 1
    bins = args[start:args.index('--output-directory')]
    record('checkm2-staged', bins)
    out = Path(arg('--output-directory'))
    out.mkdir()
    (out / 'quality_report.tsv').write_text('Name\tCompleteness\tContamination\n')
elif tool == 'gtdbtk':
    bins = sorted(Path(arg('--genome_dir')).iterdir())
    record('gtdbtk-staged', bins)
    out = Path(arg('--out_dir'))
    (out / 'classify').mkdir(parents=True)
    (out / 'classify/observer.bac120.summary.tsv').write_text('user_genome\tclassification\n')
    for name in ['gtdbtk.log', 'gtdbtk.warnings.log']:
        (out / name).write_text('INTERFACE_OBSERVER_ONLY\n')
elif tool == 'python':
    if args and Path(args[0]).name == 'semibin_runtime_resources.py':
        # This routing fixture deliberately supplies fake BAMs/classifications.
        # The resource scan is also an explicit observer, never native evidence.
        wrapper_args = args[1:args.index('--')]
        runtime = json.loads(base64.b64decode(wrapper_args[wrapper_args.index('--runtime-base64') + 1]))
        identity = {'schema_version': 1, 'runtime': runtime,
                    'scope': 'EXPLICIT_MAG_ROUTING_OBSERVER_NO_RESOURCE_SCAN'}
        if '--verify' in wrapper_args:
            assert json.loads(Path(wrapper_args[wrapper_args.index('--verify')+1]).read_text()) == identity
        if '--output' in wrapper_args:
            Path(wrapper_args[wrapper_args.index('--output')+1]).write_text(json.dumps(identity,sort_keys=True)+'\n')
        if '--execute' in wrapper_args:
            os.execvp('SemiBin2', ['SemiBin2'] + args[args.index('--')+1:])
        raise SystemExit(0)
    # Only the SemiBin CUDA version eval; no real torch/model execution.
    if args == ['-c', "import torch; print(torch.version.cuda or 'no CUDA available')"]:
        print('INTERFACE_OBSERVER_NO_CUDA')
    else:
        executable = os.environ['MAG_NATIVE_PYTHON']
        os.execv(executable, [executable] + args)
else:
    raise SystemExit('Unsupported MAG observer: ' + tool)
