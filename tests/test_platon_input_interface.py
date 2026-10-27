"""Actual fixed Platon/full-DB FASTA transport; missing native prerequisites skip explicitly."""
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlatonInputInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required=['AUTOPLASM_PLATON_PREFIX','AUTOPLASM_PLATON_NATIVE_DB','AUTOPLASM_PLATON_INTERFACE_FASTA']
        if any(not os.environ.get(k) for k in required):
            raise unittest.SkipTest('Real Platon prefix, full database and locked positive FASTA must be explicit')
        cls.prefix=Path(os.environ[required[0]]).resolve();cls.db=Path(os.environ[required[1]]).resolve()
        cls.reference=Path(os.environ[required[2]]).resolve()
        if not shutil.which('nextflow'):raise unittest.SkipTest('Nextflow required')

    def run_case(self,corrupt=False):
        directory=os.environ.get('AUTOPLASM_PLATON_INTERFACE_ROOT')
        if directory:Path(directory).mkdir(parents=True,exist_ok=True)
        base=Path(tempfile.mkdtemp(prefix='platon-input-interface-',dir=directory))
        if not os.environ.get('AUTOPLASM_KEEP_INTERFACE'):self.addCleanup(lambda:shutil.rmtree(base))
        data=self.reference.read_bytes();modes=['corrupt'] if corrupt else ['plain','gzip','uppercase'];tuples=[]
        for mode in modes:
            path=base/(mode+('.fa' if mode=='plain' else '.fa.GZ' if mode=='uppercase' else '.fa.gz'))
            path.write_bytes(b'not a gzip file' if corrupt else data if mode=='plain' else gzip.compress(data,mtime=0))
            tuples.append("tuple([id:'"+mode+"'],file('"+str(path)+"'))")
        (base/'probe.nf').write_text(
            "nextflow.enable.dsl=2\ninclude { PLATON } from '"+str(ROOT/'modules/detection/platon')+"'\n"
            "include { resourceInput } from '"+str(ROOT/'lib/resource_inputs')+"'\n"
            "workflow { PLATON(Channel.of("+','.join(tuples)+"),Channel.value(resourceInput('"+str(self.db)+"')),"
            "Channel.value(file('"+str(ROOT/'bin/platon_checked.py')+"',checkIfExists:true))) }\n")
        (base/'config').write_text("params.outdir='"+str(base/'out')+"'\nparams.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=2\nprocess.memory='4 GB'\nprocess.maxForks=2\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n")
        command=['nextflow','-C',str(base/'config'),'run',str(base/'probe.nf'),'-work-dir',str(base/'work'),'-with-trace',str(base/'trace.tsv'),'-ansi-log','false']
        env={**os.environ,'PATH':str(self.prefix/'bin')+':'+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'}
        p=subprocess.run(command,env=env,text=True,capture_output=True);(base/'stdout.log').write_text(p.stdout);(base/'stderr.log').write_text(p.stderr)
        (base/'run.json').write_text(json.dumps({'command':command,'exit_code':p.returncode,'input_sha256':hashlib.sha256(data).hexdigest(),'scope':'Actual source-checked1.7 and explicit full DB; no classifier observer'},indent=2)+'\n')
        print('PLATON_INTERFACE_ARTIFACT',base,'exit='+str(p.returncode),flush=True)
        if corrupt:
            self.assertNotEqual(p.returncode,0)
            records=list((base/'work').rglob('corrupt.platon_runtime.json'));self.assertEqual(len(records),1)
            record=json.loads(records[0].read_text());self.assertEqual(record['commands'],[])
            self.assertIn('gzipped',record['error']);self.assertFalse(list((base/'out').rglob('*.platon.tsv')))
        else:
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            expected=''.join(data.decode().splitlines()[1:])
            for mode in modes:
                out=base/'out/04_plasmid_detection/platon'
                with (out/(mode+'.platon.tsv')).open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
                self.assertEqual(len(rows),1);self.assertEqual(rows[0]['ID'],'NC_007941.1');self.assertEqual(int(rows[0]['Length']),len(expected))
                actual=(out/(mode+'.plasmid.fasta')).read_text().splitlines()
                self.assertEqual(actual[0],'>NC_007941.1');self.assertEqual(''.join(actual[1:]),expected)
                record=json.loads((out/(mode+'.platon_runtime.json')).read_text())
                self.assertEqual(record['decoded_input_sha256'],hashlib.sha256(data).hexdigest())
                self.assertEqual(record['source_commit'],'3cce2dd295348e25be4b5bd64f3622c2603d6ba0')
                self.assertEqual(record['failed_children'],[]);self.assertEqual(record['worker_errors'],[])
                self.assertGreater(len(record['commands']),6)
                state=json.loads((out/(mode+'.platon_state.json')).read_text());self.assertEqual(state['sample_id'],mode);self.assertEqual(state['state'],'plasmids_found')

    def test_plain_and_gzip_fasta_transport_parity(self):self.run_case()
    def test_corrupt_gzip_stops_before_tool(self):self.run_case(corrupt=True)


if __name__=='__main__':unittest.main()
