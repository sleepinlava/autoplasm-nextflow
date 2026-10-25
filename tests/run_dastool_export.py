#!/usr/bin/env python3
"""Real DAS Tool 1.1.7 export, using its fixed official gut sample/oracle.

Requires the four versioned contig2bin tables, full assembly, and Run1
membership/summary from cmks/DAS_Tool tag 1.1.7; never replaces the oracle.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from prepare_dastool_sample import verify

ROOT = Path(__file__).resolve().parents[1]


def fasta(path):
    seqs = {}
    for line in path.read_text().splitlines():
        if line.startswith('>'):
            key = line[1:].split()[0]
            assert key not in seqs
            seqs[key] = ''
        else:
            seqs[key] += line
    return seqs


def run(base, fixture, prefix, old_config=None, selected_cases=None):
    verify(fixture)
    assembly = fixture / 'sample.human.gut_contigs.fa'
    assert hashlib.sha1(b'blob ' + str(assembly.stat().st_size).encode() + b'\0' + assembly.read_bytes()).hexdigest() == 'de08c9dbe68cd5978b06e0db88a242d45538cfb7'
    predictions = [fixture / ('sample.human.gut_' + s + '_contigs2bin.tsv') for s in ['concoct', 'maxbin2', 'metabat', 'tetraESOM']]
    original = fasta(assembly)
    expected = {}
    for cid, bid in csv.reader((fixture / 'DASToolRun1_DASTool_contig2bin.tsv').open(), delimiter='\t'):
        expected.setdefault(bid, {})[cid] = original[cid]
    assert len(expected) == 15
    runs = []
    cases = [('after', ROOT / 'conf/nfcore_mag.config', '', predictions)]
    if old_config:
        cases.insert(0, ('before', old_config, '', predictions))
    # A genuine low-completeness bin, with an explicit stricter test threshold.
    negative = base / 'one-low-score-bin.tsv'
    negative.write_text(''.join(line + '\n' for line in predictions[2].read_text().splitlines() if line.split('\t')[1] == 'metabat.25'))
    assert negative.stat().st_size
    cases.append(('no-accepted-bins', ROOT / 'conf/nfcore_mag.config', ' --score_threshold 0.9', [negative]))
    for name, production_config, extra, tables in cases:
        if selected_cases and name not in selected_cases:
            continue
        p = base / name
        p.mkdir()
        config = p / 'config'
        # Positive runs consume the actual production args unchanged. The
        # reference bin IDs are unique, so labels only affect bin_set names.
        config.write_text("includeConfig '" + str(production_config) + "'\n"
                          "params.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=1\n"
                          "process.memory='3 GB'\nprocess.maxForks=1\nconda.enabled=false\n"
                          "docker.enabled=false\nsingularity.enabled=false\n")
        if extra:
            with config.open('a') as stream:
                stream.write("process { withName: 'DAS_TOOL' { ext.args='--write_bins" + extra + "' } }\n")
        params = {'assembly': str(assembly), 'predictions': list(map(str, tables)), 'outdir': str(p / 'out')}
        (p / 'params.json').write_text(json.dumps(params))
        command = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(ROOT / 'tests/nextflow/dastool_export.nf'), '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(prefix / 'bin') + ':' + env['PATH']
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
        out = p / 'out/07_host_prediction/mag/das_tool'
        bins = list(out.glob('*_DASTool_bins/*.fa'))
        if name == 'no-accepted-bins':
            # Fixed upstream cherry_pick explicitly uses write.log(type='stop')
            # here. Preserve that failure; never turn it into empty success.
            logs = list((p / 'work').rglob('DASToolRun1_DASTool.log'))
            checks = {'upstream_rejection_preserved': result.returncode != 0,
                      'one_failed_task': len(tasks) == 1 and tasks[0]['status'] == 'FAILED',
                      'native_no_bins_diagnostic': len(logs) == 1 and 'No bins with bin-score >0.9 found' in logs[0].read_text(),
                      'no_exported_bins': not bins,
                      'no_partial_published_files': not [q for q in out.rglob('*') if q.is_file()]}
        else:
            checks = {'success': result.returncode == 0, 'one_completed': len(tasks) == 1 and tasks[0]['status'] == 'COMPLETED', 'export_setting': bool(bins) == (name == 'after')}
        if name != 'no-accepted-bins' and checks['success']:
            actual = dict(csv.reader((out / 'DASToolRun1_DASTool_contig2bin.tsv').open(), delimiter='\t'))
            oracle = {cid: bid for bid, members in expected.items() for cid in members}
            checks['independent_membership'] = actual == oracle
            summary = list(csv.DictReader((out / 'DASToolRun1_DASTool_summary.tsv').open(), delimiter='\t'))
            checks['independent_bin_count_and_sizes'] = len(summary) == 15 and all(int(row['size']) == sum(map(len, expected[row['bin']].values())) and int(row['contigs']) == len(expected[row['bin']]) for row in summary)
            if name == 'after':
                checks['all_exported_IDs_and_DNA'] = {q.stem: fasta(q) for q in bins} == expected
        runs.append({'case': name, 'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks})
        print(name, checks, flush=True)
        receipt = {'runs': runs, 'pass': all(all(r['checks'].values()) for r in runs), 'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in ['conf/nfcore_mag.config', 'modules/nf-core/dastool/dastool/main.nf', 'tests/run_dastool_export.py', 'tests/nextflow/dastool_export.nf']}, 'limitations': ['actual native DAS1.1.7 full official sample; fixed independent Run1 membership oracle', 'positive uses unchanged production args/default score0.5; negative uses one genuine bin with stricter test-only threshold0.9', 'not binner/CheckM2/GTDB model, image, nf-test framework or full platform certification']}
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--fixture-dir', required=True, type=Path)
    parser.add_argument('--prefix', required=True, type=Path)
    parser.add_argument('--old-config', type=Path)
    parser.add_argument('--cases', default='')
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run(args.work_dir.resolve(), args.fixture_dir.resolve(), args.prefix.resolve(), args.old_config.resolve() if args.old_config else None, args.cases.split(',') if args.cases else []) else 1)
