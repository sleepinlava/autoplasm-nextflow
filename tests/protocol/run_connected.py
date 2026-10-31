#!/usr/bin/env python3
"""Exercise the connected production protocol when no plasmids/MAGs qualify.

Reuses the native core fixture. This tests completion and explicit empty states,
not positive scientific results, reconstruction or a performance benchmark.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'bin'))
from protocol_catalogue import rows
from build_shared_catalogue import write_tsv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['outdir','core-fixture','runtime-root','extension-root','python','mostplas-source']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.outdir=a.outdir.resolve();a.outdir.mkdir(parents=True)
    fixture=a.outdir/'fixture';shutil.copytree(a.core_fixture,fixture)
    samples=sorted(d.name for d in fixture.glob('sample*') if d.is_dir())
    for sample in samples:
        folder=fixture/sample
        shutil.rmtree(folder/'bins');(folder/'bins/cellular').mkdir(parents=True)
        write_tsv(folder/'summary.tsv',['seq_name','plasmid_score'],[])
        write_tsv(folder/'structure.tsv',['plasmid_id','topology_status'],[])
    write_tsv(fixture/'metadata.tsv',['sample_id','group'],[[s,'G'] for s in samples])
    write_tsv(fixture/'reference_hosts.tsv',['reference_id','host_taxonomy'],[])
    config=f"""params {{
        fixture='{fixture}'
        samplesheet='{fixture}/metadata.tsv'
        outdir='{a.outdir}/out'
        short_read_protocol=true
        protocol_host_models=true
        protocol_evolution=true
        protocol_strain=true
        run_ancombc2=true
        beta_normalization='tss'
        mostplas_source='{a.mostplas_source.resolve()}'
        plsdb_fasta='{fixture}/{samples[0]}/assembly.fasta'
        plsdb_hosts='{fixture}/reference_hosts.tsv'
        publish_dir_mode='copy'
    }}
    process {{
        withName: '.*' {{ cpus=1;memory='2 GB';time='10 min' }}
        withName: 'MOBMESS_SYSTEMS' {{ beforeScript='export PATH={a.extension_root.resolve()}/mobmess/bin:$PATH' }}
        withName: 'SYSTEM_DIVERSITY|PLASMID_DIVERSITY' {{ beforeScript='export PATH={Path(shutil.which("Rscript")).parent}:$PATH' }}
    }}
    conda.enabled=false
    docker.enabled=false
    report.enabled=false
    timeline.enabled=false
    """
    (a.outdir/'native.config').write_text(config)
    paths=[a.python.absolute().parent,a.runtime_root.resolve()/'bowtie2-2.5.4/bin',a.runtime_root.resolve()/'genomad-1.12.0/bin',
           a.extension_root.resolve()/'ancombc2/bin',a.extension_root.resolve()/'evolution/bin',a.extension_root.resolve()/'amrfinderplus/bin']
    env=os.environ.copy();env['PATH']=os.pathsep.join(map(str,paths))+os.pathsep+env['PATH']
    env.update(NXF_OFFLINE='true',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    name='protocol_connected_'+hashlib.sha256(str(a.outdir).encode()).hexdigest()[:10]
    command=['nextflow','-log',str(a.outdir/'nextflow.log'),'-c',str(a.outdir/'native.config'),'run',str(ROOT/'tests/protocol/connected.nf'),
             '-name',name,'-work-dir',str(a.outdir/'work'),'-with-trace',str(a.outdir/'trace.tsv'),'-ansi-log','false']
    (a.outdir/'command.json').write_text(json.dumps(command,indent=2))
    with (a.outdir/'console.log').open('w') as log:r=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    if r.returncode:
        print('\n'.join((a.outdir/'console.log').read_text().splitlines()[-70:]));return r.returncode
    tasks=rows(a.outdir/'trace.tsv');assert tasks and all(t['status']=='COMPLETED' and t['exit']=='0' for t in tasks)
    names={t['name'].split(' (')[0].split(':')[-1] for t in tasks}
    assert {'PLASMID_DIVERSITY','PLASMID_ANCOMBC2','SYSTEM_DIVERSITY','SYSTEM_ANCOMBC2','PROTOCOL_DELIVERY'}<=names
    delivery=a.outdir/'out/final/delivery';assert (delivery/'final_report.pdf').read_bytes().startswith(b'%PDF')
    assert not rows(delivery/'risk_profile.tsv') and not rows(delivery/'dissemination_candidates.tsv')
    assert not rows(delivery/'plasmid_abundance_matrix.tsv')
    evidence=delivery/'execution_evidence'
    for label in ['plasmids.ecology','systems.ecology','plasmids.ancombc2','systems.ancombc2']:
        assert len(list(evidence.glob('*_'+label)))==1,label
    assert rows(delivery/'software_manifest.tsv')
    assert (delivery/'database_manifest.tsv').is_file() and (delivery/'execution_records.json').is_file()
    states=[json.loads(p.read_text()) for p in evidence.rglob('status.json')]
    assert any(s.get('status')=='ineligible' for s in states)
    assert any(s.get('status')=='no_eligible_near_complete_candidates' for s in states)
    assert {r['sample_id'] for r in rows(delivery/'samples.tsv')}==set(samples)
    summary={'status':'PASS','scope':'connected production protocol empty-qualification path; native tools; not positive-cohort acceptance or benchmark',
             'tasks':len(tasks),'samples':samples,'delivery':str(delivery)}
    (a.outdir/'validation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return 0


if __name__=='__main__':sys.exit(main())
