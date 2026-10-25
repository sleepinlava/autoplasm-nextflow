#!/usr/bin/env python3
"""Actual MAG_HOST/host linking with controlled CLI observers, native R/converter.

Assertions cover IDs, DNA, metadata, multiplicity and consumer staging. They do
not certify classifiers, GTDB file selection, quality models or binning accuracy.
"""
import argparse
import csv
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def fasta(path):
    with (gzip.open(path, 'rt') if path.suffix == '.gz' else path.open()) as stream:
        records = {}
        for line in stream:
            if line.startswith('>'):
                cid = line[1:].split()[0]
                assert cid not in records
                records[cid] = ''
            else:
                records[cid] += line.strip()
    return records


def run(base, das_prefix, bgzip_prefix, concoct_prefix, cases, mag_host=None):
    fixtures = base / 'fixtures'
    fixtures.mkdir()
    records = []
    sequences = {}
    rng = random.Random(886)
    for sid, group in [('S1', 'G1'), ('S.2', 'G2')]:
        template = ''.join(rng.choices('ACGT', k=400))
        seqs = {sid + '_' + letter: template * copies for letter, copies in [('A', 3), ('B', 4), ('C', 5)]}
        sequences[sid] = seqs
        assembly = fixtures / (sid + '.contigs.fna')
        assembly.write_text(''.join('>' + k + '\n' + v + '\n' for k, v in seqs.items()))
        bam = fixtures / (sid + '.bam')
        bam.write_text(json.dumps({'id': sid, 'explicitly_fake_BAM': True}))
        records.append({'id': sid, 'group': group, 'fasta': str(assembly), 'bam': str(bam)})
    (fixtures / 'checkm2.dmnd').write_text('INTERFACE_OBSERVER_NOT_A_DATABASE\n')
    (fixtures / 'gtdb/metadata').mkdir(parents=True)
    (fixtures / 'gtdb/metadata/metadata.txt').write_text('VERSION_DATA=INTERFACE_OBSERVER\n')
    observer_bin = base / 'observer-bin'
    observer_bin.mkdir()
    tools = ['samtools', 'jgi_summarize_bam_contig_depths', 'metabat2', 'cut_up_fasta.py', 'concoct_coverage_table.py', 'concoct', 'merge_cutup_clustering.py', 'extract_fasta_bins.py', 'SemiBin2', 'DAS_Tool', 'checkm2', 'gtdbtk', 'python']
    for tool in tools:
        path = observer_bin / tool
        shutil.copyfile(ROOT / 'tests/mag_interface_observer.py', path)
        path.chmod(0o755)
    # Fixed real CONCOCT I/O helpers, including the reviewed source for the
    # production BED-stride adapter. No fake helper bypasses its source check.
    for tool in ['cut_up_fasta.py', 'merge_cutup_clustering.py', 'extract_fasta_bins.py']:
        shutil.copyfile(concoct_prefix / 'bin' / tool, observer_bin / tool)
        (observer_bin / tool).chmod(0o755)
    shutil.copyfile(das_prefix / 'bin/Fasta_to_Contig2Bin.sh', observer_bin / 'Fasta_to_Contig2Bin.sh')
    (observer_bin / 'Fasta_to_Contig2Bin.sh').chmod(0o755)
    selections = [('disabled', [], {}), ('metabat2', [' metabat2 '], {}), ('concoct', ['concoct'], {}), ('semibin', ['semibin'], {}), ('single-das', ['semibin', 'das_tool'], {})]
    for combination in itertools.combinations(['metabat2', 'concoct', 'semibin'], 2):
        selections.append(('-'.join(combination), list(combination) + ['das_tool'], {}))
    selections += [('all', ['metabat2', 'concoct', 'semibin', 'das_tool'], {}),
                   ('duplicate-selector', ['metabat2', 'metabat2'], {}),
                   ('empty-metabat', ['metabat2'], {'MAG_EMPTY_METABAT': 'S1'}),
                   ('empty-concoct', ['concoct'], {'MAG_EMPTY_CONCOCT': 'S1'}),
                   ('empty-semibin', ['semibin'], {'MAG_EMPTY_SEMIBIN': 'S1'}),
                   ('all-empty-semibin', ['semibin'], {'MAG_EMPTY_SEMIBIN': 'S1,S.2'}),
                   ('empty-semibin-component', ['metabat2', 'semibin', 'das_tool'], {'MAG_EMPTY_SEMIBIN': 'S1'}),
                   ('all-empty-semibin-das', ['semibin', 'das_tool'], {'MAG_EMPTY_SEMIBIN': 'S1,S.2'}),
                   ('empty-component', ['metabat2', 'semibin', 'das_tool'], {'MAG_EMPTY_METABAT': 'S1'}),
                   ('tool-failure', ['semibin'], {'MAG_FAIL_SEMIBIN': '1'})]
    workflow = ROOT / 'tests/nextflow/mag_selection.nf'
    if mag_host:
        workflow = base / 'original-module-probe.nf'
        workflow.write_text((ROOT / 'tests/nextflow/mag_selection.nf').read_text()
                            .replace("'../../subworkflows/mag_host'", repr(str(mag_host.with_suffix(''))))
                            .replace("'../../subworkflows/host_linking'", repr(str(ROOT / 'subworkflows/host_linking'))))
    runs = []
    for name, binners, extra_env in selections:
        if cases and name not in cases:
            continue
        p = base / name
        p.mkdir()
        config = p / 'config'
        config.write_text("includeConfig '" + str(ROOT / 'conf/nfcore_mag.config') + "'\n"
                          "params.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=1\n"
                          "process.memory='512 MB'\nprocess.maxForks=2\nconda.enabled=false\n"
                          "docker.enabled=false\nsingularity.enabled=false\n"
                          "process { withName: 'SEMIBIN|CHECKM2|GTDBTK' { cpus=1; memory='512 MB' } }\n")
        selected = {s.strip() for s in binners}
        params = {'records': records, 'outdir': str(p / 'out'), 'mag_tools': binners + (['checkm2', 'gtdbtk'] if binners else []), 'checkm2_db': str(fixtures / 'checkm2.dmnd'), 'gtdbtk_db': str(fixtures / 'gtdb'), 'host_plasmid_linking': True, 'host_linking_methods': ['sequence'], 'host_linking_optional_methods': [], 'link_min_similarity': 0}
        (p / 'params.json').write_text(json.dumps(params))
        command = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(workflow), '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env.update(extra_env)
        env['MAG_NATIVE_PYTHON'] = str(concoct_prefix / 'bin/python')
        env['PATH'] = str(observer_bin) + ':' + str(ROOT / 'bin') + ':' + str(concoct_prefix / 'bin') + ':' + str(bgzip_prefix / 'bin') + ':' + env['PATH']
        # Avoid a dependency prefix's Rscript: linking is the installed native R.
        rscript = observer_bin / 'Rscript'
        rscript.write_text('#!/bin/sh\nexec /usr/bin/Rscript "$@"\n')
        rscript.chmod(0o755)
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
        checks = {}
        if name == 'tool-failure':
            checks = {'fails': result.returncode != 0, 'diagnostic': 'CONTROLLED_SEMIBIN_FAILURE' in result.stdout + result.stderr, 'no_fake_final_bins': 'FINAL_BINS=' not in result.stdout}
        else:
            checks = {'success': result.returncode == 0, 'all_completed': bool(tasks) and all(t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks)}
            if checks['success']:
                expected_consumer_count = 0
                for sid, seqs in sequences.items():
                    available = selected - ({'metabat2'} if sid in extra_env.get('MAG_EMPTY_METABAT', '').split(',') else set())
                    if sid in extra_env.get('MAG_EMPTY_CONCOCT', '').split(','):
                        available -= {'concoct'}
                    if sid in extra_env.get('MAG_EMPTY_SEMIBIN', '').split(','):
                        available -= {'semibin'}
                    expected_bins = {}
                    if 'das_tool' in selected and available & {'metabat2', 'concoct', 'semibin'}:
                        letters = set()
                        for binner, values in [('metabat2', 'AB'), ('concoct', 'BC'), ('semibin', 'C')]:
                            if binner in available:
                                letters.update(values)
                        expected_bins = {'controlled.fa': {sid + '_' + v: seqs[sid + '_' + v] for v in letters}}
                    elif 'metabat2' in available:
                        expected_bins = {sid + '.' + str(i) + '.fa.gz': {sid + '_' + v: seqs[sid + '_' + v]} for i, v in enumerate('AB', 1)}
                    elif 'concoct' in available:
                        expected_bins = {sid + '_' + str(i) + '.fa.gz': {sid + '_' + v: seqs[sid + '_' + v]} for i, v in enumerate('BC', 1)}
                    elif 'semibin' in available:
                        expected_bins = {'SemiBin_0.fa.gz': {sid + '_C': seqs[sid + '_C']}}
                    expected_consumer_count += 2 if expected_bins else 0
                    if 'semibin' in selected:
                        states = [q for q in (p / 'work').rglob('binning_status.json')
                                  if q.parent.name == sid and not q.is_symlink()]
                        checks[sid + '_semibin_state_once'] = len(states) == 1
                        if states:
                            state = json.loads(states[0].read_text())
                            has_bins = 'semibin' in available
                            checks[sid + '_semibin_explicit_state'] = state['state'] == ('bins_ready' if has_bins else 'no_bins') and state['bin_count'] == int(has_bins)
                    checks[sid + '_one_meta_row'] = result.stdout.count('FINAL_BINS=' + sid + ':' + ('G1' if sid == 'S1' else 'G2') + ':') == bool(expected_bins)
                    hashes = {n: {k: hashlib.sha256(v.encode()).hexdigest() for k, v in members.items()} for n, members in expected_bins.items()}
                    for consumer in ['checkm2', 'gtdbtk']:
                        # GTDB's private copies have one extension; the final
                        # bin channel and CheckM2 inputs keep producer names.
                        wanted = ({n.removesuffix('.gz').removesuffix('.fa') + '.fna': members
                                   for n, members in hashes.items()} if consumer == 'gtdbtk' else hashes)
                        captures = [q for q in (p / 'work').rglob('observer-' + consumer + '-staged.json') if json.loads(q.read_text()) == wanted]
                        checks[sid + '_' + consumer + '_all_IDs_DNA_names'] = len(captures) == bool(expected_bins)
                    link_dirs = [q.parent for q in (p / 'work').rglob(sid + '.sequence_links.tsv') if not q.is_symlink()]
                    checks[sid + '_one_link_task'] = len(link_dirs) == 1
                    if link_dirs:
                        staged = {q.name: fasta(q) for q in (link_dirs[0] / 'mag_bins').glob('*')} if (link_dirs[0] / 'mag_bins').exists() else {}
                        checks[sid + '_native_link_staged_DNA'] = staged == expected_bins
                        links = list(csv.DictReader((link_dirs[0] / (sid + '.sequence_links.tsv')).open(), delimiter='\t'))
                        checks[sid + '_uncalibrated_host_links_disabled'] = not links
                        rows = list(csv.DictReader((link_dirs[0] / (sid + '.sequence_scores.tsv')).open(), delimiter='\t'))
                        expected_hosts = {n.removesuffix('.gz').removesuffix('.fa') for n in expected_bins}
                        checks[sid + '_native_score_rows'] = len(rows) == 3 * len(expected_hosts) and {r['host_id'] for r in rows} == expected_hosts and all(r['sample_id'] == sid and r['plasmid_id'] in seqs for r in rows)
                    if 'das_tool' in selected:
                        inputs = [json.loads(q.read_text()) for q in (p / 'work').rglob('observer-DAS-inputs.json') if json.loads(q.read_text())['sample'] == sid]
                        checks[sid + '_all_available_binners'] = len(inputs) == bool(expected_bins) and (not inputs or set(inputs[0]['tables']) == {sid + '.' + b + '.tsv' for b in available & {'metabat2', 'concoct', 'semibin'}})
                consumer_count = sum('CHECKM2' in t['name'] or 'GTDBTK' in t['name'] for t in tasks)
                checks['no_dropped_or_duplicate_consumer_tasks'] = consumer_count == expected_consumer_count
        runs.append({'case': name, 'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks})
        print(name, checks, flush=True)
        source_names = ['main.nf', 'lib/mag_selection.nf', 'subworkflows/mag_host.nf', 'conf/nfcore_mag.config', 'modules/nf-core/gtdbtk/classifywf/main.nf', 'bin/normalize_gtdb_bins.py', 'modules/nf-core/semibin/singleeasybin/main.nf', 'bin/semibin_output_state.py', 'tests/nextflow/mag_selection.nf', 'tests/mag_interface_observer.py', 'tests/run_mag_routing.py', 'subworkflows/host_linking.nf', 'modules/linking/sequence.nf', 'bin/sequence_similarity_link.R']
        receipt = {'runs': runs, 'pass': all(all(r['checks'].values()) for r in runs), 'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in source_names}, 'limitations': ['explicit synthetic binner/DAS/CheckM/GTDB observers, fake BAM/db inputs; no tool inference or scientific accuracy claim', 'actual original workflow + gzip/converter helper + native R host linking; per-sample bin identity/DNA/metadata/multiplicity checks', 'GTDB observer verifies private normalized staging and unchanged final-bin identities, not the actual classifier; separate real2.7.2 parser/selection tests, no image/nf-test framework/full platform']}
        if mag_host:
            receipt['source_sha256']['subworkflows/mag_host.nf'] = hashlib.sha256(mag_host.read_bytes()).hexdigest()
            receipt['module_override'] = str(mag_host)
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--das-prefix', required=True, type=Path)
    parser.add_argument('--bgzip-prefix', required=True, type=Path)
    parser.add_argument('--concoct-prefix', required=True, type=Path)
    parser.add_argument('--cases', default='')
    parser.add_argument('--mag-host', type=Path, help='Optional frozen original module, with include paths resolved')
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run(args.work_dir.resolve(), args.das_prefix.resolve(), args.bgzip_prefix.resolve(), args.concoct_prefix.resolve(), args.cases.split(',') if args.cases else [], args.mag_host.resolve() if args.mag_host else None) else 1)
