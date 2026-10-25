#!/usr/bin/env python3
"""Standalone Recycler input-guard tests using native SAMtools/PySAM; no reconstruction."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
NODE='EDGE_1_length_1200_cov_1'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recycler-prefix',required=True,type=Path)
    parser.add_argument('--samtools-prefix',required=True,type=Path)
    parser.add_argument('--work-dir',type=Path)
    args=parser.parse_args()
    base=(args.work_dir or Path(tempfile.mkdtemp(prefix='recycler-input-guard-'))).resolve()
    if base.exists() and any(base.iterdir()):parser.error('--work-dir must be empty')
    base.mkdir(parents=True,exist_ok=True)
    samtools=args.samtools_prefix.resolve()/'bin/samtools'
    python=args.recycler_prefix.resolve()/'bin/python'
    env=os.environ.copy();env['PATH']=str(python.parent)+':'+env['PATH']
    versions=subprocess.run([str(python),'-c',"import sys,pysam; print(sys.version.split()[0]); print(pysam.__version__)"],env=env,capture_output=True,text=True,check=True).stdout
    (base/'versions.txt').write_text(versions)
    results=[]
    for case in ['valid','reverse-first','reverse-reference','missing-index','wrong-reference','wrong-length','partial-dictionary','corrupt-index','sort-metadata','not-fastg','duplicate-node','empty-sequence']:
        p=base/case;p.mkdir();graph=p/'graph.fastg';bam=p/'nodes.bam';out=p/'validated.json'
        sequence='ACGT'*300
        graph.write_text(f'>{NODE};\n{sequence}\n>{NODE}\';\n{sequence}\n')
        if case=='reverse-first':
            graph.write_text(f'>{NODE}\';\n'+('G'*600+'T'*600)+f'\n>{NODE};\n'+('A'*600+'C'*600)+'\n')
        elif case=='partial-dictionary':
            with graph.open('a') as stream:stream.write('>EDGE_2_length_1200_cov_1;\n'+sequence+'\n')
        elif case=='not-fastg':graph.write_text(f'>{NODE}\n{sequence}\n')
        elif case=='duplicate-node':
            with graph.open('a') as stream:stream.write(f'>{NODE};\n{sequence}\n')
        elif case=='empty-sequence':graph.write_text(f'>{NODE};\n>{NODE}\';\n')
        reference='contig_from_unrelated_assembly' if case=='wrong-reference' else NODE
        if case=='reverse-reference':reference=NODE+"'"
        length=1201 if case=='wrong-length' else 1200
        sam=p/'reads.sam'
        sam.write_text('@HD\tVN:1.6\tSO:coordinate\n'+f'@SQ\tSN:{reference}\tLN:{length}\n'+
            f'pair\t99\t{reference}\t101\t60\t100M\t=\t301\t300\t'+('ACGT'*25)+'\t'+('I'*100)+'\n'+
            f'pair\t147\t{reference}\t301\t60\t100M\t=\t101\t-300\t'+('ACGT'*25)+'\t'+('I'*100)+'\n')
        subprocess.run([str(samtools),'view','-b','-o',str(bam),str(sam)],check=True,capture_output=True)
        subprocess.run([str(samtools),'index',str(bam)],check=True,capture_output=True)
        if case=='missing-index':Path(str(bam)+'.bai').unlink()
        elif case=='corrupt-index':Path(str(bam)+'.bai').write_bytes(b'not an index')
        elif case=='sort-metadata':
            header=p/'bad-header.sam';header.write_text(f'@HD\tVN:1.6\tSO:queryname\n@SQ\tSN:{reference}\tLN:{length}\n')
            replaced=p/'reheader.bam'
            with replaced.open('wb') as stream:subprocess.run([str(samtools),'reheader',str(header),str(bam)],stdout=stream,check=True)
            replaced.replace(bam)
        command=[str(python),str(ROOT/'bin/validate_recycler_inputs.py'),'--graph',str(graph),'--bam',str(bam),'--out',str(out)]
        r=subprocess.run(command,env=env,capture_output=True,text=True);(p/'stdout.log').write_text(r.stdout);(p/'stderr.log').write_text(r.stderr)
        diagnostic={'reverse-reference':'reference mismatch','missing-index':'missing adjacent BAM index','wrong-reference':'reference mismatch','wrong-length':'reference length mismatch','partial-dictionary':'reference mismatch','corrupt-index':'index','sort-metadata':'coordinate sort order','not-fastg':'FASTG header','duplicate-node':'duplicate graph node','empty-sequence':'empty sequence'}.get(case)
        if case in ['valid','reverse-first']:
            data=json.loads(out.read_text()) if out.exists() else {}
            checks={'exit':r.returncode==0,'reference_count':data.get('graph_references')==1,
                    'bam_digest':data.get('sha256',{}).get('bam')==hashlib.sha256(bam.read_bytes()).hexdigest()}
        else:
            checks={'exit':r.returncode!=0,'precise_contract_error':'Recycler input contract violation' in r.stderr and diagnostic in r.stderr,
                    'source_context':str(graph) in r.stderr and str(bam) in r.stderr,'no_output':not out.exists()}
        results.append({'case':case,'command':command,'exit':r.returncode,'checks':checks});print(case,checks,flush=True)
    receipt={'cases':results,'pass':all(all(x['checks'].values()) for x in results),'source_sha256':hashlib.sha256((ROOT/'bin/validate_recycler_inputs.py').read_bytes()).hexdigest(),
             'limitations':['synthetic paired SAM converted/indexed by actual SAMtools; native validator/PySAM only, not mapper or Recycler biological result','guard not yet wired into production; graph-specific BAM/index producer remains required']}
    (base/'run.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if receipt['pass'] else 1


if __name__=='__main__':raise SystemExit(main())
