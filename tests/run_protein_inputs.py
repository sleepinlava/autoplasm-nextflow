#!/usr/bin/env python3
"""Actual downstream protein routing with native Prodigal/MSF/eggNOG.

The only command adapter replaces msf_data's Internet acquisition of the
locked model with its native local-archive installation of the same release.
It never fabricates a model, gene, hit, annotation or tool result.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from Bio import SeqIO
from Bio.Seq import Seq

ROOT = Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def records(path):
    opener = gzip.open if Path(path).read_bytes()[:2] == b'\x1f\x8b' else open
    with opener(path, 'rt') as stream:
        return {r.id:r for r in SeqIO.parse(stream, 'fasta')}


def native_facts(folder, source):
    dna = records(source)
    proteins = records(folder/'proteins.faa')
    mapping = list(csv.DictReader((folder/'gene_map.tsv').open(), delimiter='\t'))
    manifest = json.loads((folder/'manifest.json').read_text())
    assert set(proteins) == {r['protein_id'] for r in mapping}
    assert len(proteins) == len(mapping) == manifest['protein_count']
    assert {r['contig_id'] for r in manifest['replicons']} == set(dna)
    previous = (-1, -1)
    index = {identifier:i for i,identifier in enumerate(dna)}
    for row in mapping:
        pid, cid = row['protein_id'], row['contig_id']
        start, end = int(row['start']), int(row['end'])
        position = (index[cid], start)
        assert position >= previous; previous = position
        assert pid.rsplit('_',1)[0] == cid
        segment = dna[cid].seq[start-1:end]
        if row['strand'] == '-': segment = segment.reverse_complement()
        translated = str(segment.translate(table=int(row['translation_table'])))
        # Prodigal translates a complete alternative start codon as methionine.
        if row['partial'][0] == '0': translated = 'M'+translated[1:]
        assert str(proteins[pid].seq) == translated, (pid, translated, proteins[pid].seq)
    topo = {}
    for line in (folder/'replicon_topology.txt').read_text().splitlines():
        identifier, value = line.split(':');topo[identifier] = value.strip()
    for row in manifest['replicons']:
        marker = 'topology=circular' in dna[row['contig_id']].description.split()[1:]
        assert row['topology'] == ('circular' if marker else 'linear')
        if row['protein_count']:
            assert topo.get(row['contig_id'], 'linear') == row['topology']
    return {'genes':len(proteins), 'contigs':len(dna), 'state':manifest['state'],
            'independent_translation_checked':True, 'protein_ids':sorted(proteins)}


def run(base, macsy, eggnog, models_archive, fixture, plasmid):
    base.mkdir(parents=True)
    lock=json.loads((ROOT/'tests/protein-input-native.lock.json').read_text())
    assert sha(models_archive)==lock['models']['archive_sha256']
    for name, expected in lock['eggnog_fixture']['files'].items():
        assert sha(fixture/name)==expected['sha256'],name
    data=base/'fixtures';data.mkdir()
    plasmid_records=records(plasmid);assert len(plasmid_records)==1
    plasmid_record=next(iter(plasmid_records.values()))
    # Use the nucleotide companion of the official annotated ychF protein.
    # The separate genepred_contig fixture uses a different search database
    # and cannot serve as a positive annotation oracle for this database.
    official=records(fixture/'test_queries.fna')['1000565.METUNv1_03812']
    # Header-only topology perturbation; DNA bytes/coordinates are retained.
    s1=data/'S1.fna.gz'
    s1.write_bytes(gzip.compress(('>'+plasmid_record.id+' topology=circular\n'+str(plasmid_record.seq)+'\n>fragment_with_underscores\n'+str(official.seq)+'\n').encode(),mtime=0))
    s2=data/'S.2.fna';s2.write_text('>single_contig\n'+str(official.seq)+'\n')
    zero=data/'Zero.fna';zero.write_text('>short_fragment\n'+str(official.seq[:30])+'\n')
    inputs=[{'id':'S.2','fasta':str(s2)},{'id':'Zero','fasta':str(zero)},{'id':'S1','fasta':str(s1)}]
    nativebin=base/'native-bin';nativebin.mkdir()
    wrapper=nativebin/'msf_data'
    wrapper.write_text('#!'+str(macsy/'bin/python')+'\n'+
        'import os,sys,json\nfrom pathlib import Path\n'
        'args=sys.argv[1:]\noriginal=list(args)\n'
        'if "install" in args:\n'
        ' assert args[-1]=="CONJScan==2.1.0",args\n'
        ' args[-1]='+repr(str(models_archive))+'\n'
        ' Path("model_acquisition_transport.json").write_text(json.dumps({"original":original,"actual":args,"scope":"native local archive acquisition"}))\n'
        'os.execv('+repr(str(macsy/'bin/msf_data'))+', ["msf_data"]+args)\n')
    wrapper.chmod(0o755)
    common={
        'typing_tools':[], 'typing_optional_tools':[], 'annotation_tools':[], 'annotation_optional_tools':[],
        'plasmid_binning_tools':[], 'publish_dir_mode':'copy', 'eggnog_db':str(fixture),
    }
    runs=[]
    def execute(name, selections, chosen=inputs, resume=False):
        folder=base/name;folder.mkdir(exist_ok=resume)
        config=folder/'nextflow.config'
        if not resume:
            config.write_text('includeConfig '+repr(str(ROOT/'conf/nfcore_downstream.config'))+'\n'
                "process.executor='local'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                "process { cpus=1; memory='1 GB'; errorStrategy='terminate'; maxRetries=0\n"
                "withName: 'EGGNOG_MAPPER' { beforeScript="+repr('export PATH='+str(eggnog/'bin')+':$PATH')+" }\n}\n")
            params={**common,**selections,'records':chosen,'outdir':str(folder/'out')}
            (folder/'params.json').write_text(json.dumps(params,indent=2))
        suffix='-resume' if resume else ''
        trace=folder/('trace'+suffix+'.tsv')
        run_name='protein_'+hashlib.sha256(str(folder).encode()).hexdigest()[:12]
        command=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(ROOT/'tests/nextflow/protein_inputs.nf'),'-params-file',str(folder/'params.json'),'-work-dir',str(folder/'work'),'-with-trace',str(trace),'-ansi-log','false']
        if resume:command+=['-resume',run_name]
        else:command+=['-name',run_name]
        env={**os.environ,'PATH':str(nativebin)+':'+str(macsy/'bin')+':'+os.environ['PATH']}
        result=subprocess.run(command,capture_output=True,text=True,env=env)
        (folder/('stdout'+suffix+'.log')).write_text(result.stdout);(folder/('stderr'+suffix+'.log')).write_text(result.stderr)
        tasks=list(csv.DictReader(trace.open(),delimiter='\t')) if trace.exists() else []
        record={'scenario':name+suffix,'command':command,'exit_code':result.returncode,'trace':tasks}
        runs.append(record);(base/'runs-progress.json').write_text(json.dumps(runs,indent=2)+'\n')
        assert result.returncode==0,(name,result.stdout[-4000:],result.stderr[-3000:])
        if not selections or not chosen:
            assert not tasks
            record['checks']={'no_analysis_tasks':True};return
        states={t['status'] for t in tasks};assert states==({'CACHED'} if resume else {'COMPLETED'}),states
        process_counts={}
        for task in tasks:
            process=task['name'].split(' (')[0].rsplit(':',1)[-1]
            process_counts[process]=process_counts.get(process,0)+1
        assert process_counts.get('PRODIGAL')==len(chosen),process_counts
        if not selections.get('typing_optional_tools') and not selections.get('annotation_optional_tools'):
            assert process_counts=={'PRODIGAL':len(chosen)}
            for row in chosen:
                path=folder/'out/08_annotation/prodigal'/(row['id']+'.prodigal.faa.gz')
                assert records(path)
                assert not (folder/'out/08_annotation/protein_inputs').exists()
            record['checks']={'original_prodigal_only_route':True,'counts':process_counts};return
        expected_nonempty=sum(r['id']!='Zero' for r in chosen)
        expected={'PRODIGAL':len(chosen),'PROTEIN_INPUTS':len(chosen)}
        if selections.get('typing_optional_tools'):
            if expected_nonempty:
                expected['MACSYFINDER_DOWNLOAD']=1
                for tool in selections['typing_optional_tools']:expected['CONJSCAN' if tool=='conjscan' else 'MACSYFINDER']=expected_nonempty
        if selections.get('annotation_optional_tools') and expected_nonempty:expected['EGGNOG_MAPPER']=expected_nonempty
        assert process_counts==expected,(process_counts,expected)
        facts={}
        for row in chosen:
            sid=row['id'];out=folder/'out/08_annotation/protein_inputs'/sid/'protein_inputs'
            facts[sid]=native_facts(out,row['fasta'])
        if selections.get('annotation_optional_tools'):
            for row in chosen:
                path=folder/'out/08_annotation/eggnog'/(row['id']+'.emapper.annotations')
                if row['id']=='Zero':assert not path.exists();continue
                lines=[l.split('\t') for l in path.read_text().splitlines() if l and not l.startswith('#')]
                assert lines, (row['id'],'official fixture should annotate ychF')
                assert {r[0] for r in lines}.issubset(facts[row['id']]['protein_ids'])
                assert any(r[8]=='ychF' for r in lines),lines
        if selections.get('typing_optional_tools'):
            for tool in selections['typing_optional_tools']:
                for row in chosen:
                    # Nextflow retains the declared sample-specific prefix
                    # directory in this output glob; it is not flattened.
                    path=folder/'out/06_plasmid_typing'/tool/(row['id']+'.'+tool)/'all_systems.tsv'
                    if row['id']=='Zero':assert not path.exists();continue
                    lines=[l for l in path.read_text().splitlines() if not l.startswith('#')]
                    hits=list(csv.DictReader(lines,delimiter='\t'))
                    assert all(h['hit_id'] in facts[row['id']]['protein_ids'] and h['replicon']==h['hit_id'].rsplit('_',1)[0] for h in hits)
                    if row['id']=='S1':assert any(h['model_fqn']=='CONJScan/Plasmids/T4SS_typeF' for h in hits)
                    else:assert not hits
        record['checks']={'counts':process_counts,'independent_inputs':facts,'no_zero_gene_consumer_tasks':True,
                          'sample_scoped_publication':True,'positive_eggnog_gene_names':True,
                          'macsy_positive_and_no_system':True}
    execute('combined',{'typing_optional_tools':['conjscan','macsyfinder'],'annotation_tools':['prodigal'],'annotation_optional_tools':['eggnog_mapper']})
    execute('combined',{'typing_optional_tools':['conjscan','macsyfinder'],'annotation_tools':['prodigal'],'annotation_optional_tools':['eggnog_mapper']},resume=True)
    execute('eggnog-only',{'annotation_optional_tools':['eggnog_mapper']},inputs[:1])
    execute('prodigal-only',{'annotation_tools':['prodigal']},inputs[:1])
    execute('zero-proteins',{'typing_optional_tools':['conjscan'],'annotation_optional_tools':['eggnog_mapper']},inputs[1:2])
    execute('disabled',{})
    execute('no-input',{'typing_optional_tools':['conjscan'],'annotation_optional_tools':['eggnog_mapper']},[])
    payload={'pass':True,'runs':runs,'native_prefixes':{'macsy':str(macsy),'eggnog':str(eggnog)},
             'source_sha256':{p:sha(ROOT/p) for p in ['subworkflows/plasmid_downstream.nf','conf/nfcore_downstream.config','modules/annotation/protein_inputs.nf','modules/nf-core/macsyfinder/search/main.nf','modules/nf-core/macsyfinder/download/main.nf','modules/nf-core/eggnogmapper/main.nf','modules/nf-core/prodigal/main.nf','bin/prepare_prodigal_inputs.py','tests/run_protein_inputs.py','tests/nextflow/protein_inputs.nf','tests/protein-input-native.lock.json']},
             'inputs':{str(p):sha(p) for p in [models_archive,plasmid,fixture/'test_queries.fna']},
             'limitations':['Official small eggNOG fixture database, not full production database or scientific annotation benchmark.',
                            'Model acquisition uses native local-archive installer through an explicitly logged transport adapter; production remote acquisition is not certified.',
                            'Topology header perturbations and cropped zero-gene boundary are interface controls, not independent biological replicates.',
                            'Current Nextflow native backend only; image/nf-test/full platform certification remains open.']}
    (base/'run.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'pass':True,'scenarios':len(runs),'trace_entries':sum(len(r['trace']) for r in runs)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['output','macsy-prefix','eggnog-prefix','models-archive','fixture','plasmid']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    run(args.output.resolve(),args.macsy_prefix.resolve(),args.eggnog_prefix.resolve(),args.models_archive.resolve(),args.fixture.resolve(),args.plasmid.resolve())
