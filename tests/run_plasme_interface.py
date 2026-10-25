#!/usr/bin/env python3
"""Run the original PLASMe wrapper and R consumers with its pinned output writer.

Only upstream plasme_output/merge_ranges/argument parsing execute. Candidate
scores and BLAST hits are controlled fixtures; no model or database inference.
"""
from pathlib import Path
import argparse
import ast
import csv
import gzip
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SHIM = '''
import argparse,ast,os
from pathlib import Path
import pandas as pd
from Bio import SeqIO
source=Path(__file__).with_name('pinned_PLASMe.py')
tree=ast.parse(source.read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['plasme_cmd','merge_ranges','plasme_output']]
assert len(functions)==3
exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'))
args=plasme_cmd();sid=Path(args.output).name.removesuffix('.plasme')
assert Path(args.database).is_dir(), 'database argument must preserve the complete path'
Path('writer.invoked').write_text('upstream output writer only; controlled candidates; no inference')
if sid=='TOOL_FAIL':raise SystemExit(23)
table='order,query,identity,coverage,PLASMe,overlap\\n'
for cid,ident,cov,score in [('blast',.99,.99,0),('transformer',.1,.1,.9),('both',.99,.99,.2),('tie',.1,.1,.5),('low',.1,.1,.1)]:
 if sid=='NEGATIVE':ident,cov,score=.1,.1,.1
 table+='Bacteria,'+cid+','+str(ident)+','+str(cov)+','+str(score)+',none\\n'
Path('candidates.csv').write_text(table)
Path('blast.csv').write_text(''.join(cid+' reference\\n' for cid in ['blast','transformer','both','tie','low']))
plasme_output('candidates.csv','blast.csv',args.input,args.identity,args.coverage,args.probability,args.output)
if sid=='MISSING_REPORT':Path(args.output+'_report.csv').unlink()
if sid=='MISSING_FASTA':Path(args.output).unlink()
'''


def run_checks(base, python, module, cases, podman=False, conda=False):
    cached = json.loads((ROOT / 'docs/tool-audit/evidence/score-tools-upstream.json').read_text())
    source = next(s for s in cached['sources'] if s['key'] == 'plasme-cli')
    data = source['content'].encode()
    blob = hashlib.sha1(('blob ' + str(len(data)) + '\0').encode() + data).hexdigest()
    assert blob == source['sha'] == '7f0718071849b73111a4e641b27e0f528d3356a2'
    (base / 'PLASMe.py').write_bytes(data)
    scripts = base / 'writer-bin'
    scripts.mkdir()
    shim = scripts / 'PLASMe.py'
    shim.write_text('#!' + str(python) + '\n' + SHIM)
    shim.chmod(0o755)
    (scripts/'pinned_PLASMe.py').write_bytes(data)
    fixture = base / 'fixtures'
    fixture.mkdir()
    (fixture / "db directory's").mkdir()
    database = fixture / "db directory's"
    for name in ['plsdb_Mar30.dmnd','plsdb_taxon.tsv','plas_overlap.csv','plas_chrom_thres.csv','plsdb_Mar30.clusters.p2a',
                 'plsdb_Mar30.nin','plsdb_Mar30.nhr','plsdb_Mar30.nsq']:
        (database/name).write_text('WRITER_OBSERVER_ONLY_NOT_A_REAL_DATABASE\n')
    (database/'trans_model').mkdir()
    for name in ['bio_script.py','trans_data.py','trans_model.py']:
        (scripts/name).write_text('# Explicit writer observer; no classifier or weights\n')
    sequences = {cid: 'ACGT' * (300 + i) for i, cid in enumerate(['blast', 'transformer', 'both', 'tie', 'low'])}
    fasta = ''.join('>' + cid + ' description\n' + seq + '\n' for cid, seq in sequences.items()).encode()
    mapping = {'PLAIN': 'fa', 'GZIP': 'fa.gz', 'UPPER': 'fa.GZ', 'NEGATIVE': 'fa',
               'MISSING_REPORT': 'fa', 'MISSING_FASTA': 'fa', 'TOOL_FAIL': 'fa', 'CORRUPT': 'fa.gz'}
    for sid, suffix in mapping.items():
        path = fixture / (sid + " input's." + suffix)
        path.write_bytes(b'not gzip' if sid == 'CORRUPT' else gzip.compress(fasta, mtime=0) if suffix.lower().endswith('.gz') else fasta)
        (fixture / (sid + '.genomad.tsv')).write_text('seq_name\tplasmid_score\n')
    config = base / 'config'
    config.write_text("params.publish_dir_mode='copy'\nparams.consensus_method='weighted_vote'\n"
                      "params.consensus_weights='genomad:0,plasme:1'\nprocess.executor='local'\n"
                      "process.cpus=1\nprocess.memory='1 GB'\nconda.enabled=false\n"
                      "docker.enabled=false\nsingularity.enabled=false\n")
    if podman:
        with config.open('a') as stream:
            stream.write("podman.enabled=true\nprocess { withName: 'PLASMID_CONSENSUS|PLASMID_STRUCTURE' { container=null } }\n")
    if conda:
        with config.open('a') as stream:
            stream.write("conda.enabled=true\nconda.useMicromamba=true\nconda.cacheDir="+repr(str(base/'conda-cache'))+"\nprocess { withName: 'PLASMID_CONSENSUS|PLASMID_STRUCTURE' { conda=null } }\n")
    probe = base / 'probe.nf'
    probe.write_text("""nextflow.enable.dsl=2
include { PLASME } from 'MODULE'
include { PLASMID_CONSENSUS } from 'CONSENSUS'
include { PLASMID_STRUCTURE } from 'STRUCTURE'
workflow {
    assemblies=Channel.fromList(params.inputs).map { row -> tuple([id:row.id],file(row.path)) }
    PLASME(assemblies,Channel.value(file(params.db)),Channel.value(file(params.source)))
    inputs=PLASME.out.predictions.join(assemblies).map { meta,pred,assembly ->
        tuple(meta,assembly,file("${params.fixture_dir}/${meta.id}.genomad.tsv"),[pred])
    }
    PLASMID_CONSENSUS(inputs)
    PLASMID_STRUCTURE(PLASMID_CONSENSUS.out.contigs)
}
""".replace("'MODULE'", repr(str(module))).replace("'CONSENSUS'", repr(str(ROOT / 'modules/detection/consensus'))).replace("'STRUCTURE'", repr(str(ROOT / 'modules/detection/structure'))))
    all_cases = [('plain', ['PLAIN'], None), ('compressed', ['GZIP', 'UPPER'], None),
                 ('negative', ['NEGATIVE'], None), ('missing-report', ['MISSING_REPORT'], 'Missing PLASMe'),
                 ('missing-fasta', ['MISSING_FASTA'], 'Missing PLASMe'), ('tool-failure', ['TOOL_FAIL'], '23'),
                 ('corrupt-gzip', ['CORRUPT'], 'gzip')]
    runs = []
    for case, ids, error in all_cases:
        if cases and case not in cases:
            continue
        p = base / case
        p.mkdir()
        (p / 'params.json').write_text(json.dumps({'inputs': [{'id': sid, 'path': str(fixture / (sid + " input's." + mapping[sid]))} for sid in ids],
                                                 'db': str(fixture / "db directory's"), 'source':str(scripts), 'fixture_dir': str(fixture), 'outdir': str(p / 'out')}))
        command = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(probe),
                   '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(scripts) + ':' + str(python.parent) + ':' + str(ROOT / 'bin') + ':' + env['PATH']
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
        if error:
            checks = {'nonzero': result.returncode != 0, 'diagnostic': error in result.stdout + result.stderr,
                      'one_failed_producer': len(tasks) == 1 and tasks[0]['status'] == 'FAILED',
                      'no_published_files': not [f for f in (p / 'out').rglob('*') if f.is_file()]}
            if case == 'corrupt-gzip':
                checks['writer_not_called'] = not list((p / 'work').rglob('writer.invoked'))
        else:
            checks = {'success': result.returncode == 0, 'completed_tasks': len(tasks) == len(ids) * 3 and all(t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks)}
            if checks['success']:
                for sid in ids:
                    expected = set() if sid == 'NEGATIVE' else {'blast', 'transformer', 'both'}
                    out = p / 'out/04_plasmid_detection'
                    normalized = out / 'plasme' / (sid + '.plasme.tsv')
                    rows = list(csv.DictReader(normalized.open(), delimiter='\t'))
                    checks[sid + '_positive_IDs'] = {r['contig_id'] for r in rows} == expected
                    checks[sid + '_evidence_preserved'] = {r['contig_id']: (r.get('source_score'), r.get('evidence')) for r in rows} == ({} if not expected else {'blast': ('nan', 'BLASTn'), 'transformer': ('0.9', 'Transformer'), 'both': ('0.2', 'Transformer')})
                    checks[sid + '_raw_outputs_published'] = all((out / 'plasme' / name).is_file() for name in [sid + '.plasme.fasta', sid + '.plasme_report.csv'])
                    consensus = list(csv.DictReader((out / 'consensus' / (sid + '.plasmid_consensus.tsv')).open(), delimiter='\t'))
                    checks[sid + '_consensus_IDs'] = {r['contig_id'] for r in consensus if r['plasmid_call'] == 'plasmid'} == expected
                    got = (out / 'consensus' / (sid + '.plasmid_contigs.fasta')).read_text().replace('\n', '')
                    checks[sid + '_exact_DNA'] = got == ''.join('>' + cid + seq for cid, seq in sequences.items() if cid in expected)
        runs.append({'case': case, 'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks})
        print(case, checks, flush=True)
        receipt = {'runs': runs, 'pass': all(all(r['checks'].values()) for r in runs), 'upstream_blob': blob,
                   'module': str(module), 'source_sha256': hashlib.sha256((Path(str(module) + '.nf')).read_bytes()).hexdigest(),
                   'limitations': ['real pinned upstream output writer only; candidates and BLAST hits controlled, no PLASMe model/database inference', 'native original wrapper and R consumers, not nf-test/image/full platform certification']}
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--python', required=True, type=Path)
    parser.add_argument('--module', type=Path, default=ROOT / 'modules/detection/plasme')
    parser.add_argument('--cases', default='')
    parser.add_argument('--podman',action='store_true',help='PLASME image only; R consumers remain native and classifier is still an explicit writer observer')
    parser.add_argument('--conda',action='store_true',help='Create the actual PLASME Conda environment; R consumers remain native and classifier is still a writer observer')
    args = parser.parse_args()
    args.work_dir = args.work_dir.resolve()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    if args.podman and args.conda:parser.error('Choose only one isolated backend')
    raise SystemExit(0 if run_checks(args.work_dir, args.python.resolve(), args.module.resolve(), args.cases.split(',') if args.cases else [],args.podman,args.conda) else 1)
