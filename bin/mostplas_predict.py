#!/usr/bin/env python3
"""Use the original MOSTPLAS model/feature implementation on qualified near-complete candidate representatives."""
import argparse
import ast
import json
import importlib.metadata
from pathlib import Path
import runpy
import shutil
import os
from protocol_catalogue import rows, fasta
from build_shared_catalogue import records, file_digest, write_tsv


def predict(source,catalogue,complete_ids,output,threshold=0.4):
    output.mkdir()
    eligible={r['plasmid_id'] for r in rows(catalogue/'structure.tsv') if r['completeness'] in ('independently_supported','predicted_near_complete')}
    dna=dict(records(catalogue/'plasmids.fasta'))
    if not eligible <= set(dna):raise ValueError('MOSTPLAS complete IDs absent from catalogue')
    write_tsv(output/'host_range.tsv',['plasmid_id','predicted_genera','evidence_grade'],[])
    status=dict(status='no_eligible_near_complete_candidates',threshold=threshold,eligible_ids=sorted(eligible))
    if eligible:
        runtime=output/'runtime';shutil.copytree(source,runtime,ignore=shutil.ignore_patterns('.git','__pycache__','input_fasta','output'))
        # Upstream functions.py uses Seq without importing it. Supply the
        # missing import in the task-local copy; preserve its feature algorithm.
        functions=runtime/'functions.py'
        functions.write_text('from Bio.Seq import Seq\n'+functions.read_text())
        fasta(runtime/'query.fasta',((fid,dna[fid]) for fid in sorted(eligible)))
        # Upstream has no CLI. Change only its input/output/threshold constants
        # in a task-local copy and execute its model and feature code unchanged.
        tree=ast.parse((runtime/'test.py').read_text(encoding='gbk'))
        replacements={'input_path':'./query.fasta','output_path':'./prediction.txt','threshold':threshold}
        for node in tree.body:
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in replacements:
                node.value=ast.Constant(replacements[node.targets[0].id])
        (runtime/'predict.py').write_text(ast.unparse(ast.fix_missing_locations(tree)))
        cwd=Path.cwd();os.chdir(runtime)
        import sys
        sys.path.insert(0,str(Path.cwd()))
        try:runpy.run_path('predict.py',run_name='__main__')
        finally:os.chdir(cwd)
        predictions=[]
        for line in (runtime/'prediction.txt').read_text().splitlines():
            fields=line.rstrip('\t').split('\t');predictions.append([fields[0],'|'.join(fields[1:]),'model_prediction' if len(fields)>1 else 'unknown'])
        write_tsv(output/'host_range.tsv',['plasmid_id','predicted_genera','evidence_grade'],predictions)
        status.update(versions={name:importlib.metadata.version(name) for name in ['torch','biopython','numpy']},
            compatibility_changes=['functions.py: import Bio.Seq.Seq'],source_files_sha256={p.name:file_digest(p) for p in source.glob('*.py')},genus_index_sha256=file_digest(source/'genus_index.txt'),status='measured',model_sha256=file_digest(source/'checkpoint/checkpoint.pth.tar'),source_sha256=file_digest(source/'test.py'))
        shutil.rmtree(runtime)
    (output/'status.json').write_text(json.dumps(status,indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['source','catalogue','complete-ids','output']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--threshold',type=float,default=.4)
 predict(**vars(p.parse_args()))
