#!/usr/bin/env python3
"""Classify independent candidate records with an explicitly staged COPLA installation."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HEADER = ['contig_id', 'length', 'topology', 'entity_scope', 'predicted_ptu', 'host_range', 'score', 'notes']
PREDICTION = ['#Predicted_PTU', 'Host_Range', 'Score', 'Notes']


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def candidates(path):
    """Preserve complete input DNA and explicit topology; never join records."""
    records, seen = [], set()
    header, sequence = None, []

    def append():
        if header is None:
            return
        parts = header.split()
        if not parts or parts[0] in seen:
            raise ValueError('COPLA requires nonempty unique candidate IDs')
        identifier = parts[0]
        dna = ''.join(sequence)
        if not dna or re.search('[^ACGTRYSWKMBDHVNacgtryswkmbdhvn]', dna):
            raise ValueError('Invalid or empty COPLA candidate DNA: ' + identifier)
        annotations = set(parts[1:])
        circular = bool({'topology=circular', 'circular=true'} & annotations)
        linear = bool({'topology=linear', 'circular=false'} & annotations)
        if circular and linear:
            raise ValueError('Conflicting COPLA candidate topology: ' + identifier)
        records.append({'id': identifier, 'header': header, 'dna': dna,
                        'topology': 'circular' if circular else 'linear',
                        'topology_source': 'explicit_header' if circular or linear else 'unknown_treated_as_linear'})
        seen.add(identifier)

    opener = gzip.open if str(path).lower().endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            if line.startswith('>'):
                append()
                header, sequence = line[1:], []
            else:
                if header is None:
                    raise ValueError('COPLA FASTA sequence precedes its header')
                sequence.append(line)
    append()
    return records


def reference_files(installation, reflist):
    """References must be declared within the installation, not hidden global files."""
    installation = Path(installation).resolve()
    result, seen = [], set()
    for line in Path(reflist).read_text().splitlines():
        if not line.strip():
            raise ValueError('COPLA reference list contains a blank entry')
        path = Path(line)
        path = path.resolve() if path.is_absolute() else (installation / path).resolve()
        if not path.is_relative_to(installation):
            raise ValueError('COPLA reference is outside the declared installation: ' + str(path))
        if not path.is_file() or not path.stat().st_size:
            raise ValueError('Missing COPLA reference: ' + str(path))
        if path.suffix != '.fna' or not re.fullmatch(r'[A-Za-z0-9_.-]+\.fna', path.name):
            raise ValueError('COPLA requires safe uncompressed reference FASTA filenames')
        if path.stem in seen:
            raise ValueError('Duplicate COPLA reference accession: ' + path.stem)
        seen.add(path.stem)
        result.append(path)
    if not result:
        raise ValueError('COPLA reference list is empty')
    return result


def one_row(path, fields):
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames != fields:
            raise ValueError('Unexpected COPLA table header: ' + str(path))
        rows = list(reader)
    if len(rows) != 1 or None in rows[0] or any(value is None for value in rows[0].values()):
        raise ValueError('COPLA must emit exactly one complete result per candidate: ' + str(path))
    return rows[0]


def prediction(path):
    row = one_row(path, PREDICTION)
    try:
        score = float(row['Score'])
    except ValueError as error:
        raise ValueError('Invalid COPLA score') from error
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError('COPLA score must be finite and within [0,1]')
    if not row['#Predicted_PTU'] or not row['Notes'] or row['Host_Range'] not in ['-', 'I', 'II', 'III', 'IV', 'V', 'VI']:
        raise ValueError('Incomplete COPLA PTU or host-range result')
    return row


def prepare_program(installation, work, macsyfinder, threads):
    """Private, exact-version integration corrections; preserve all scientific parameters."""
    source = Path(installation) / 'bin'
    target = work / 'bin'
    target.mkdir()
    for path in source.iterdir():
        if path.is_file():
            shutil.copyfile(path, target / path.name)
            (target / path.name).chmod(0o755)
    script = target / 'copla.py'
    original = sha(script)
    # Known official 6b89285e source; another compatible source is recorded unchanged.
    if original != 'a27f52f1f9af475f0de2de70ef46b1c4c9079c96ddb39b93126d9d03df51d7e5':
        return {'applied': False, 'original_copla_sha256': original}
    expected_helpers = {
        'get_ani_identity.pl': 'fcac3e4a2a8a6cbc94956cd5ad1fb68c5f4ef7910147594ce083c6aa968986ac',
        'get_ani_identity_job.pl': '56711294d80f033c0806886092669b6e6a8824b2ae3cd9f68476dbf80e1effc9',
        'check_conjugation_systems.sh': 'dcc640e343b2289a4c7fbe8229cac43bbf5e435dee26d39454045242720dbe48',
        'ani.rb': '0151a14698c02b6ec7adfe3400e6693066cb0ab300077a4274a39d41a7878cb1'}
    for name, expected in expected_helpers.items():
        if sha(source / name) != expected:
            raise ValueError('Pinned COPLA helper source does not match: ' + name)
    text = script.read_text()
    text = text.replace("cmd = ['hmmscan', '--cpu', '9',", "cmd = ['hmmscan', '--cpu', str(int(os.environ['COPLA_THREADS'])),")
    text = text.replace('import graph_tool.all as gt\n', 'import graph_tool.all as gt\ngt.openmp_set_num_threads(int(os.environ["COPLA_THREADS"]))\n')
    text = text.replace('shutil.copy2(', 'shutil.copyfile(')
    # The first copy is into an output directory, so supply its final filename explicitly.
    text = text.replace('shutil.copyfile(args.sequence, args.outdir)',
                        'shutil.copyfile(args.sequence, os.path.join(args.outdir, os.path.basename(args.sequence)))')
    text = text.replace('shutil.copyfile(args.aminoacid, args.outdir)',
                        'shutil.copyfile(args.aminoacid, os.path.join(args.outdir, os.path.basename(args.aminoacid)))')
    text = text.replace('except subprocess.CalledProcessError:\n        mob_label',
                        'except subprocess.CalledProcessError:\n        if os.path.getsize(fname) != 0: raise\n        mob_label')
    text = text.replace('    pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)\n\n    # Check why',
                        '    pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)\n'
                        '    if os.path.getsize(fname) == 0: return "-"\n\n    # Check why')
    lines = []
    for line in text.splitlines(True):
        if 'cp = subprocess.run(' in line and not line.lstrip().startswith('#') and 'check=True' not in line:
            line = line.replace('stderr=subprocess.DEVNULL)', 'stderr=None, check=True)')
        elif 'stderr=subprocess.DEVNULL, shell=True)' in line:
            line = line.replace('stderr=subprocess.DEVNULL, shell=True)', 'stderr=None, shell=True, check=True)')
        lines.append(line)
    script.write_text(''.join(lines))
    # Helper scripts previously hid GNU Parallel, Ruby and MacSyFinder errors.
    for name in ['get_ani_identity.pl', 'get_ani_identity_job.pl']:
        path = target / name
        text = path.read_text()
        lines = []
        for line in text.splitlines(True):
            if line.startswith('system('):
                line = line.replace('> /dev/null 2>&1', '> $fname_tsv.stdout 2> $fname_tsv.stderr')
                line = line.rstrip('\n')[:-1] + ' == 0 or die "COPLA helper child failed: $?\\n";\n'
            lines.append(line)
        text = ''.join(lines)
        if name == 'get_ani_identity_job.pl':
            text += ('\nopen my $STATUS, ">", "$fname_tsv.status" or die $!;\n'
                     'print $STATUS (-e "$fname_tsv.not_evaluable" ? "not_evaluable_no_fragments" : '
                     '(-s $fname_tsv ? "edge" : "no_edge_insufficient_reciprocal_hits"));\nclose $STATUS;\n')
        else:
            marker = 'system("rm -r $work_dir")'
            diagnostics = ('open my $EVAL, ">", "$fname_qry.ani_evaluation.tsv" or die $!;\n'
                'print $EVAL "reference\\tstatus\\n";\n'
                'open my $DIAG, ">", "$fname_qry.ani_diagnostics.log" or die $!;\n'
                'for my $file (sort glob("$work_dir*.status")) {\n'
                '    my $ref = basename($file); $ref =~ s/\\.tsv\\.status$//;\n'
                '    open my $S, "<", $file or die $!; my $status = <$S>; close $S;\n'
                '    print $EVAL "$ref\\t$status\\n";\n'
                '    my $prefix = substr($file, 0, length($file)-7);\n'
                '    for my $kind ("stdout", "stderr") {\n'
                '        open my $L, "<", "$prefix.$kind" or die $!;\n'
                '        print $DIAG "== $ref $kind ==\\n";\n'
                '        while (my $line = <$L>) { print $DIAG $line; } close $L;\n'
                '    }\n}\nclose $EVAL; close $DIAG;\n\n')
            if text.count(marker) != 1:
                raise ValueError('Unexpected pinned COPLA ANI cleanup')
            text = text.replace(marker, diagnostics + marker)
        path.write_text(text)
    path = target / 'check_conjugation_systems.sh'
    text = path.read_text()
    begin = text.index('source "$(dirname')
    end = text.index('\n\nQRYFILE=', begin)
    text = text[:begin] + 'set -euo pipefail\nexport PATH="${COPLA_MACSYFINDER%/*}:$PATH"\n' + text[end:]
    text = text.replace('THREADS=20', 'THREADS=${COPLA_THREADS:?}')
    text = text.replace('    macsyfinder ${conj_type}', '    "${COPLA_MACSYFINDER:?}" ${conj_type}')
    text = text.replace('rm ${QRYFILE}.*', 'rm -f -- ${QRYFILE}.*')
    path.write_text(text)
    # ani.rb uses backticks and ignored failed BLAST children. Require success,
    # while a successful comparison with insufficient reciprocal hits stays valid.
    path = target / 'ani.rb'
    text = path.read_text()
    text = text.replace('`"#{o[:bin]}makeblastdb" -in "#{dir}/#{seq.to_s}.fa" -dbtype nucl`',
                        'system("#{o[:bin]}makeblastdb", "-in", "#{dir}/#{seq.to_s}.fa", "-dbtype", "nucl", :out=>File::NULL) or abort "makeblastdb failed"')
    old = '`"#{o[:bin]}blastn" -db "#{s}" -query "#{q}" \\\n      -dust no -max_target_seqs 1 \\\n      -num_threads #{o[:thr]} -outfmt 6 -out "#{dir}/#{i}.tab"`'
    if text.count(old) != 1:
        raise ValueError('Unexpected pinned Enveomics BLAST command')
    text = text.replace(old, 'system("#{o[:bin]}blastn", "-db", s, "-query", q, "-dust", "no", "-max_target_seqs", "1", "-num_threads", o[:thr].to_s, "-outfmt", "6", "-out", "#{dir}/#{i}.tab") or abort "blastn failed"')
    marker = '    case o[:program].downcase\n'
    # Preserve the existing 1000bp/200bp eligibility rule. A reference with no
    # informative window is explicitly unevaluable, rather than a BLAST failure.
    if text.count(marker) != 2:
        raise ValueError('Unexpected pinned ANI fragment generation boundary')
    text = text.replace(marker,
                        '    if frgs == 0\n'
                        '      File.write(o[:tab] + ".not_evaluable", "no_informative_fragments\\t" + seq.to_s) unless o[:tab].nil?\n'
                        '      exit 0\n    end\n' + marker, 1)
    path.write_text(text)
    return {'applied': True, 'original_copla_sha256': original,
            'source_commit': '6b89285ef16d721d93d3c84f3645e76455ba8621',
            'scope': 'child failure propagation, resource/thread paths and byte-only copies; no ANI threshold, reference parser or graph/model change',
            'private_source_sha256': {p.name: sha(p) for p in target.iterdir() if p.is_file()}}


def run(args):
    installation = Path(args.installation).resolve()
    graph = Path(args.refgraph).resolve()
    macsy = Path(args.macsyfinder).resolve()
    for path in [graph, Path(args.reflist), installation / 'bin/copla.py', installation / 'bin/ani.rb', macsy / 'bin/macsyfinder']:
        if not path.is_file() or not path.stat().st_size:
            raise ValueError('Missing COPLA resource: ' + str(path))
    for name in ['MOBscan_171004', 'MacSyFinder_190530/Conjugation', 'PlasmidFinder_190731', 'CARD_201015']:
        if not (installation / 'databases' / name).is_dir():
            raise ValueError('Missing COPLA database directory: ' + name)
    if args.threads < 1:
        raise ValueError('COPLA threads must be positive')
    if Path(args.output).exists() or Path(args.raw).exists() or Path('copla_program').exists():
        raise ValueError('COPLA refuses pre-existing output/program paths')
    refs = reference_files(installation, args.reflist)
    records = candidates(args.assembly)
    for exe in ['prodigal', 'hmmscan', 'plasmidfinder.py', 'blastn', 'makeblastdb', 'parallel', 'ruby', 'perl']:
        if not shutil.which(exe):
            raise ValueError('Missing COPLA executable: ' + exe)
    work = Path('copla_program');work.mkdir()
    (work / 'databases').symlink_to(installation / 'databases', target_is_directory=True)
    (work / 'reference.pickle').symlink_to(graph)
    references = work / 'reference_sequences'
    references.mkdir()
    for path in refs:
        (references / path.name).symlink_to(path)
    (work / 'references.fofn').write_text(''.join('reference_sequences/' + p.name + '\n' for p in refs))
    patch = prepare_program(installation, work, macsy, args.threads)
    (work / 'queries').mkdir();(work / 'results').mkdir()
    environment = os.environ.copy()
    if (installation / 'lib').is_dir():
        environment['LD_LIBRARY_PATH'] = str(installation / 'lib') + (os.pathsep + environment['LD_LIBRARY_PATH'] if environment.get('LD_LIBRARY_PATH') else '')
    environment.update(COPLA_THREADS=str(args.threads), COPLA_MACSYFINDER=str(macsy / 'bin/macsyfinder'),
                       OMP_NUM_THREADS=str(args.threads), PARALLEL='--jobs ' + str(args.threads) + ' --halt soon,fail=1',
                       MPLCONFIGDIR=str((work / 'mpl-cache').resolve()))
    manifest = {'entity_scope': 'independent_candidate_record_not_reconstructed_multicontig_plasmid',
                'input_sha256': sha(args.assembly), 'reference_graph_sha256': sha(graph),
                'reference_list_sha256': sha(args.reflist), 'reference_count': len(refs),
                'source_patch': patch, 'threads': args.threads, 'entities': []}
    if patch['applied']:
        import pickle
        import graph_tool.all as gt
        import numpy
        import pandas
        gt.openmp_set_num_threads(args.threads)
        with graph.open('rb') as stream:
            network, state = pickle.load(stream)
        accessions = list(network.vp.AccessionVersion)
        if len(accessions) != len(set(accessions)) or set(accessions) != {p.stem for p in refs}:
            raise ValueError('COPLA graph accessions do not match declared reference FASTAs')
        manifest['runtime_versions'] = {'graph_tool': gt.__version__, 'numpy': numpy.__version__, 'pandas': pandas.__version__}
        manifest['reference_graph_vertices'] = network.num_vertices()
        del network, state
    rows = []
    for index, record in enumerate(records, 1):
        key = 'candidate_%06d' % index
        query = work / 'queries' / (key + '.fna')
        query.write_text('>' + record['header'] + '\n' + record['dna'] + '\n')
        out = work / 'results' / key
        command = [sys.executable, 'bin/copla.py', 'queries/' + query.name,
                   'reference.pickle', 'references.fofn', 'results/' + key, '-t', record['topology']]
        with (work / (key + '.stdout')).open('w') as stdout, (work / (key + '.stderr')).open('w') as stderr:
            result = subprocess.run(command, cwd=work, env=environment, stdout=stdout, stderr=stderr)
        if result.returncode:
            raise ValueError('COPLA failed for candidate ' + record['id'] + '; inspect ' + str(work / (key + '.stderr')))
        prefix = out / query.name
        for suffix in ['', '.faa', '.ani.tsv', '.related_plasmids.tsv', '.qry_info.tsv', '.ptu_prediction.tsv']:
            if not Path(str(prefix) + suffix).is_file():
                raise ValueError('Missing exact COPLA product for ' + record['id'] + ': ' + suffix)
        if candidates(prefix) != [record]:
            raise ValueError('COPLA output query DNA/identity changed')
        if patch['applied']:
            evaluation = Path(str(prefix) + '.ani_evaluation.tsv')
            with evaluation.open(newline='') as stream:
                reader = csv.DictReader(stream, delimiter='\t')
                if reader.fieldnames != ['reference', 'status']:
                    raise ValueError('Missing COPLA ANI assessment contract')
                assessments = list(reader)
            if (len(assessments) != len(refs) or {r['reference'] for r in assessments} != {p.name for p in refs}
                    or any(r['status'] not in ['edge', 'no_edge_insufficient_reciprocal_hits', 'not_evaluable_no_fragments'] for r in assessments)):
                raise ValueError('COPLA did not assess every declared reference')
        info = one_row(str(prefix) + '.qry_info.tsv', ['#Total bp', 'MOB', 'MPF', 'Replicon', 'AMR'])
        if info['#Total bp'] != str(len(record['dna'])):
            raise ValueError('COPLA query length does not match its individual record')
        value = prediction(str(prefix) + '.ptu_prediction.tsv')
        rows.append([record['id'], str(len(record['dna'])), record['topology'], 'candidate_record',
                     value['#Predicted_PTU'], value['Host_Range'], value['Score'], value['Notes']])
        manifest['entities'].append({'id': record['id'], 'length': len(record['dna']), 'key': key,
                                     'topology': record['topology'], 'topology_source': record['topology_source'],
                                     'DNA_sha256': hashlib.sha256(record['dna'].encode()).hexdigest(),
                                     'command': command, 'exit': result.returncode})
    # Only publish aggregate and raw results after every candidate has passed.
    (work / 'entities.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (work / 'databases').unlink()
    (work / 'reference.pickle').unlink()
    shutil.rmtree(work / 'reference_sequences')
    with Path(args.output).open('w', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(HEADER);writer.writerows(rows)
    work.rename(args.raw)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['assembly', 'installation', 'refgraph', 'reflist', 'macsyfinder', 'output', 'raw']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--threads', type=int, required=True)
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, OSError, EOFError, UnicodeError, csv.Error) as error:
        print('COPLA candidate adapter: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
