#!/usr/bin/env python3
"""Original detection workflow with explicit classifier CLI observers and native R consumers."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PLASX_PYTHON_OBSERVER = r'''
import sys,json,shutil,csv
from pathlib import Path
if len(sys.argv)>1 and Path(sys.argv[1]).name in ['plasx_inputs.py','anvio_checked.py','plasx_checked.py']:
 # Routing only: deliberately bypass every PlasX producer/validator/model.
 a=sys.argv[2:];name=Path(sys.argv[1]).name
 def value(flag):return a[a.index(flag)+1]
 if name=='plasx_inputs.py':
  if a[0]=='prepare':
   prefix=value('--prefix');source=Path(value('--assembly'));cid=source.read_text().splitlines()[0][1:]
   Path(prefix+'.contigs.fasta').write_bytes(source.read_bytes())
   Path(prefix+'.id_map.tsv').write_text('contig\toriginal_contig\n'+cid+'\t'+cid+'\n')
  elif a[0]=='finalize':
   shutil.copyfile(value('--scores'),value('--output'))
   Path(value('--state')).write_text('sample_id\tcontig\tstatus\n'+value('--sample')+'\tOBSERVER\tstub_not_validated\n')
 elif name=='anvio_checked.py':
  command=a[a.index('--')+1]
  if command=='anvi-gen-contigs-database':Path(value('-o')).write_text('EXPLICIT_OBSERVER_NOT_A_REAL_DATABASE\n')
  elif command=='anvi-export-gene-calls':
   source=next(Path('.').glob('*.contigs.fasta'));cid=source.read_text().splitlines()[0][1:]
   Path(value('-o')).write_text('gene_callers_id\tcontig\n0\t'+cid+'\n')
  elif command=='anvi-export-functions':Path(value('-o')).write_text('gene_callers_id\tsource\taccession\te_value\n')
 elif name=='plasx_checked.py':
  command=a[a.index('--')+1]
  if command=='search_de_novo_families':Path(value('-o')).write_text('gene_callers_id\tcontig\taccession\te_value\n')
  elif command=='predict':
   with Path(value('-g')).open() as stream:cid=next(csv.DictReader(stream,delimiter='\t'))['contig']
   Path(value('-o')).write_text('contig\tscore\n'+cid+'\t0.9\n')
 if '--record' in a:Path(value('--record')).write_text(json.dumps({'scope':'EXPLICIT_PLASX_ANNOTATION_AND_CLASSIFIER_TRANSPORT_OBSERVER','state':'stub_not_validated'}))
 raise SystemExit(0)
'''
OBSERVER = '''#!/usr/bin/env python3
# Controlled interface output only; no classification/model/database inference.
from pathlib import Path
import sys,time
tool=Path(sys.argv[0]).name;args=sys.argv[1:]
if '--version' in args:
 print('geNomad, version INTERFACE_OBSERVER');raise SystemExit()
if tool=='prodigal':
 for flag in ['-o','-a','-d']:Path(args[args.index(flag)+1]).write_text('')
 raise SystemExit()
if tool=='genomad':
 source=Path(args[1]);out=Path(args[2]);prefix=source.stem
 if prefix=='S1':time.sleep(1)
 for kind in ['annotate','find_proviruses','summary']:(out/(prefix+'_'+kind)).mkdir(parents=True)
 (out/(prefix+'_annotate')/(prefix+'_taxonomy.tsv')).write_text('')
 (out/(prefix+'_find_proviruses')/(prefix+'_provirus.tsv')).write_text('')
 summary=out/(prefix+'_summary');cid=source.read_text().splitlines()[0][1:]
 for entity in ['plasmid','virus']:
  for suffix in ['.fna','_proteins.faa','_genes.tsv','_summary.tsv']:
   text=('seq_name\\tplasmid_score\\n'+(cid+'\\t0.99\\n' if prefix=='S1' else '')) if suffix=='_summary.tsv' else ''
   (summary/(prefix+'_'+entity+suffix)).write_text(text)
elif tool=='PLASMe.py':
 source=Path(args[0]);out=Path(args[1]);cid=source.read_text().splitlines()[0][1:];dna=''.join(source.read_text().splitlines()[1:])
 out.write_text(source.read_text())
 Path(args[1]+'_report.csv').write_text('contig\\tlength\\treference\\torder\\tevidence\\tscore\\tamb_region\\n'+cid+'\\t'+str(len(dna))+'\\treference\\tBacteria\\tTransformer\\t0.9\\t\\n')
elif tool=='platon':
 source=Path(args[-1]);out=Path(args[args.index('--prefix')+1]+'.tsv');cid=source.read_text().splitlines()[0][1:]
 out.write_text('contig_id\\tclassification\\n'+cid+'\\tplasmid\\n')
elif tool=='plasx':
 out=Path(args[args.index('-o')+1]);sid=out.name.removesuffix('.plasx.tsv')
 out.write_text('contig\\tscore\\n'+sid+'_contig\\t0.9\\n')
else:raise SystemExit('Unexpected observer CLI '+tool)
'''


def run_checks(base, python):
    fixture = base / 'fixtures'
    fixture.mkdir()
    sequences = {'S1': 'ACGT' * 300, 'S.2': 'GCGC' * 350}
    for sid, dna in sequences.items():
        (fixture / (sid + '.fasta')).write_text('>' + sid + '_contig\n' + dna + '\n')
    (fixture / 'db').mkdir()
    for name in ['plsdb_Mar30.dmnd','plsdb_taxon.tsv','plas_overlap.csv','plas_chrom_thres.csv','plsdb_Mar30.clusters.p2a',
                 'plsdb_Mar30.nin','plsdb_Mar30.nhr','plsdb_Mar30.nsq']:
        (fixture/'db'/name).write_text('INTERFACE_OBSERVER_ONLY_NOT_A_REAL_DATABASE\n')
    (fixture/'db/trans_model').mkdir()
    for name in ['annotations', 'model']:
        (fixture / name).write_text('INTERFACE_OBSERVER_ONLY\n')
    observer_bin = base / 'observer-bin'
    observer_bin.mkdir()
    for tool in ['genomad', 'PLASMe.py', 'plasx', 'platon', 'prodigal']:
        script = observer_bin / tool
        script.write_text(OBSERVER)
        script.chmod(0o755)
    # The production Platon auditor executes its fixed Python package directly.
    # This explicit test-only Python transport replaces that classifier boundary;
    # it never claims to validate the auditor, model, DB, or output format.
    shim=observer_bin/'python3'
    shim.write_text('#!'+str(python)+'\n'+PLASX_PYTHON_OBSERVER+"import os,sys,json\nfrom pathlib import Path\nif len(sys.argv)>1 and Path(sys.argv[1]).name=='platon_checked.py':\n a=sys.argv[2:];source=Path(a[a.index('--assembly')+1]);prefix=a[a.index('--prefix')+1];cid=source.read_text().splitlines()[0][1:]\n Path(prefix+'.tsv').write_text('contig_id\\tclassification\\n'+cid+'\\tplasmid\\n')\n Path(prefix+'.plasmid.fasta').write_bytes(source.read_bytes())\n for suffix in ['.json','.platon_state.json']:\n  Path(prefix+suffix).write_text(json.dumps({'sample_id':prefix,'state':'stub_not_validated','scope':'EXPLICIT_CLASSIFIER_OBSERVER'}))\n Path(a[a.index('--record')+1]).write_text(json.dumps({'sample_id':prefix,'scope':'EXPLICIT_CLASSIFIER_OBSERVER_NO_NATIVE_PLATON'}));raise SystemExit(0)\nos.execv('PYTHON_EXECUTABLE',[sys.argv[0],*sys.argv[1:]])\n".replace('PYTHON_EXECUTABLE',str(python)))
    shim.chmod(0o755)
    for name in ['bio_script.py','trans_data.py','trans_model.py']:
        (observer_bin/name).write_text('# Explicit classifier CLI observer\n')
    config = base / 'config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\n"
                      "params.publish_dir_mode='copy'\nparams.consensus_method='weighted_vote'\n"
                      "params.consensus_weights='genomad:0.6,platon:0.15,plasme:0.15,plasx:0.1'\n"
                      "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n")
    runs = []
    for case, tools in [('disabled', []), ('platon', [' platon ']), ('all', ['plasme', 'plasx', 'platon'])]:
        p = base / case
        p.mkdir()
        params = {'fixture_dir': str(fixture), 'outdir': str(p / 'out'), 'plasmid_detection_tools': tools,
                  'genomad_db': str(fixture / 'db'), 'platon_db': str(fixture / 'db'),
                  'plasme_db': str(fixture / 'db'), 'plasme_dir':str(observer_bin),
                  'plasx_anvio_source':str(observer_bin),'plasx_source':str(observer_bin),
                  'plasx_cog_db':str(fixture/'db'),'plasx_pfam_db':str(fixture/'db'),
                  'plasx_profiles':str(fixture/'db'),'plasx_splits':32,'plasx_model': str(fixture / 'model')}
        (p / 'params.json').write_text(json.dumps(params))
        command = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run',
                   str(ROOT / 'tests/nextflow/detection_selection.nf'), '-params-file', str(p / 'params.json'),
                   '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(observer_bin) + ':' + str(python.parent) + ':' + str(ROOT / 'bin') + ':' + env['PATH']
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
        selected = {tool.strip() for tool in tools}
        checks = {'success': result.returncode == 0, 'task_count': len(tasks) == 2 * (3 + len(selected) + int('plasx' in selected)),
                  'completed': bool(tasks) and all(t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks),
                  'no_retired_tasks': all('SCAPP' not in t['name'] for t in tasks)}
        if checks['success']:
            out = p / 'out/04_plasmid_detection'
            for sid, dna in sequences.items():
                contigs = (out / 'consensus' / (sid + '.plasmid_contigs.fasta')).read_text()
                rows = list(csv.DictReader((out / 'consensus' / (sid + '.plasmid_consensus.tsv')).open(), delimiter='\t'))
                checks[sid + '_DNA'] = contigs.replace('\n', '') == ('>' + sid + '_contig' + dna if sid == 'S1' else '')
                checks[sid + '_rows'] = len(rows) == (1 if sid == 'S1' or selected else 0)
                checks[sid + '_identity_metrics'] = all(r['contig_id'] == sid + '_contig' and r['sample_id'] == sid and int(r['length']) == len(dna) and float(r['gc_content']) == (0.5 if sid == 'S1' else 1) for r in rows)
                checks[sid + '_classification'] = all(r['plasmid_call'] == ('plasmid' if sid == 'S1' else 'chromosome') and 'scapp' not in r for r in rows)
                checks[sid + '_optional_columns'] = all(all(r[t] == ('plasmid' if t in selected else 'NA') for t in ['plasme', 'plasx', 'platon']) for r in rows)
                structure = list(csv.DictReader((out / 'structure' / (sid + '.plasmid_structure.tsv')).open(), delimiter='\t'))
                checks[sid + '_structure'] = {r['plasmid_id'] for r in structure} == ({sid + '_contig'} if sid == 'S1' else set())
        runs.append({'case': case, 'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks})
        print(case, checks, flush=True)
        sources = ['subworkflows/plasmid_detection.nf', 'bin/plasmid_consensus.R', 'tests/nextflow/detection_selection.nf', 'tests/run_detection_selection.py','modules/detection/platon.nf','bin/platon_checked.py']
        receipt = {'runs': runs, 'pass': all(all(r['checks'].values()) for r in runs),
                   'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sources},
                   'limitations': ['classifier CLI observers including explicit Platon and both PlasX stages checked-runtime/validator Python transport; production annotation, auditor, classifier, and format validation are NOT evaluated by this routing test', 'native original full detection subworkflow and R consumers; no classifier inference, real DB/models, image or scientific accuracy']}
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    parser.add_argument('--python',required=True,type=Path,help='Actual pinned PLASMe CPU Python environment; classifier remains an explicit observer')
    args = parser.parse_args()
    base = Path(args.work_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run_checks(base,args.python.resolve()) else 1)
