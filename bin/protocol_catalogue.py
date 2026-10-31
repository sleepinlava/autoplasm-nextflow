#!/usr/bin/env python3
"""Protocol candidate provenance and conservative catalogue; external clustering is MMseqs2."""
import argparse
import csv
import json
from pathlib import Path
import shutil
from build_shared_catalogue import build, canonical, digest, records, write_tsv, file_digest


def rows(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f, delimiter='\t'))


def fasta(path, sequences):
    with Path(path).open('w') as f:
        for name, dna in sequences:
            f.write(f'>{name}\n{dna}\n')


def integrate(assembly, bins, summary, structure, sample, output, bin_score_threshold=.7):
    """Native bins are entities, their contigs remain separate DNA records."""
    dna = dict(records(assembly))
    membership = {}
    for path in sorted(bins.glob('*.fna')):
        for cid, seq in records(path):
            if cid in membership or dna[cid] != seq:
                raise ValueError(f'{sample}: inconsistent PlasMAAG membership/DNA: {cid}')
            membership[cid] = path.stem
    # geNomad supplements only unbinned calls. It is not an independent vote
    # for a bin already classified by PlasMAAG using geNomad.
    calls = {r['seq_name']: r for r in rows(summary)}
    topology = {r['plasmid_id']: r for r in rows(structure)}
    output.mkdir()
    native_evidence = {r["bin_id"]:r for r in rows(bins/"bin_evidence.tsv")} if (bins/"bin_evidence.tsv").exists() else {}
    evidence = []
    for cid in sorted(set(membership) | set(calls)):
        is_bin = cid in membership
        entity = f'{sample}:{membership[cid]}' if is_bin else f'{sample}:supplement:{cid}'
        circular = topology.get(cid, {}).get('topology_status') == 'circular_candidate'
        # A repeat/circularity prediction does not establish a closed plasmid.
        bin_record=native_evidence.get(membership.get(cid,''),{})
        score=bin_record.get('plasmid_score','')
        grade='high_confidence_bin' if is_bin and score and float(score)>=bin_score_threshold else 'unresolved_fragment' if is_bin else 'plasmid_like_contig'
        single_bin = is_bin and sum(b==membership[cid] for b in membership.values())==1
        predicted_near_complete = grade=='high_confidence_bin' and single_bin and circular and bin_record.get('graph_support')=='assembly_graph_available_not_independently_validated'
        evidence.append([sample, cid, entity, membership.get(cid, ''),
                         'plasmaag_bin' if is_bin else 'genomad_supplement',
                         grade, 'near_complete_candidate' if predicted_near_complete else 'circular_candidate' if circular else 'fragment_or_unknown',
                         'predicted_near_complete' if predicted_near_complete else 'not_established', 'plasmaag_genomad' if is_bin else 'genomad',
                         calls.get(cid, {}).get('plasmid_score', ''), len(dna[cid]),score,'plasmid' if cid in calls else 'not_called',bin_record.get('graph_support','not_assessed')])
    fasta(output / 'candidates.fasta', ((r[1], dna[r[1]]) for r in evidence))
    write_tsv(output / 'evidence.tsv', ['sample_id', 'contig_id', 'entity_id', 'bin_id', 'origin',
              'identity_grade', 'structure_grade', 'completeness', 'classification_evidence', 'plasmid_score','length_bp','plasmaag_score','genomad_class','assembly_graph_evidence'], evidence)
    shutil.copyfile(output/'evidence.tsv',output/'candidate_provenance.tsv')


def prepare(ids, assemblies, candidates, evidence, output, complete_ids=None):
    build(ids, assemblies, candidates, output, len(ids))
    sources = rows(output / 'sources.tsv')
    lookup = {(r['sample_id'], r['contig_id']): r['feature_id'] for r in sources}
    provenance = [dict(r, feature_id=lookup[r['sample_id'], r['contig_id']]) for p in evidence for r in rows(p)]
    fields = list(provenance[0]) if provenance else ['sample_id','contig_id','entity_id','bin_id','origin','identity_grade','structure_grade','completeness','classification_evidence','plasmid_score','length_bp','plasmaag_score','genomad_class','assembly_graph_evidence','feature_id']
    write_tsv(output / 'candidate_evidence.tsv', fields, ([r[k] for k in fields] for r in provenance))
    circular = {r['feature_id'] for r in provenance if r['structure_grade'] in ('circular_candidate','near_complete_candidate')}
    plasmids = {r['feature_id'] for r in sources if r['is_plasmid_in_source'] == '1'}
    sequences = dict(records(output / 'reference.fasta'))
    complete=set(complete_ids.read_text().split()) if complete_ids is not None and complete_ids.is_file() else set()
    if not complete <= plasmids:raise ValueError('Complete IDs must identify exact candidate sequence IDs')
    for name, members in [('complete',complete),('circular', circular-complete), ('fragment', plasmids - circular - complete)]:
        fasta(output / f'{name}.fasta', ((fid, sequences[fid]) for fid in sorted(members)))


def finalize(exact, clusters, output, identity, coverage, complete_ids=None):
    output.mkdir()
    features = rows(exact / 'features.tsv')
    mapping = {r['feature_id']: r['feature_id'] for r in features}
    for path in clusters:
        with path.open() as stream:
            for rep, member in csv.reader(stream, delimiter='\t'):
                mapping[member] = rep
    sequences = dict(records(exact / 'reference.fasta'))
    source = rows(exact / 'sources.tsv')
    evidence = rows(exact / 'candidate_evidence.tsv')
    circular = {mapping[r['feature_id']] for r in evidence if r['structure_grade'] in ('circular_candidate','near_complete_candidate')}
    merged = {}
    for row in features:
        rep = mapping[row['feature_id']]
        if rep not in merged:
            merged[rep] = dict(row, feature_id=rep, length_bp=str(len(sequences[rep])), sequence_sha256=rep[4:], source_count=0, plasmid_source_count=0)
        merged[rep]['source_count'] += int(row['source_count'])
        merged[rep]['plasmid_source_count'] += int(row['plasmid_source_count'])
    for row in merged.values():
        row['is_plasmid'] = int(row['plasmid_source_count'] > 0)
    for row in source:
        old = row['feature_id']; row['feature_id'] = mapping[old]
        if old != row['feature_id']:
            row['orientation'] = 'alignment_required'
    for row in evidence:
        row['member_id'] = row['feature_id']; row['feature_id'] = mapping[row['feature_id']]
    write_tsv(output / 'features.tsv', list(features[0]) if features else ['feature_id','length_bp','is_plasmid','sequence_sha256','source_count','plasmid_source_count'],
              ([r[k] for k in ['feature_id','length_bp','is_plasmid','sequence_sha256','source_count','plasmid_source_count']] for r in sorted(merged.values(), key=lambda r:r['feature_id'])))
    for name, table, fields in [('sources.tsv', source, ['sample_id','contig_id','feature_id','orientation','is_plasmid_in_source']),
         ('candidate_evidence.tsv', evidence, list(evidence[0]) if evidence else ['sample_id','contig_id','entity_id','bin_id','origin','identity_grade','structure_grade','completeness','classification_evidence','plasmid_score','length_bp','plasmaag_score','genomad_class','assembly_graph_evidence','feature_id','member_id'])]:
        write_tsv(output / name, fields, ([r[k] for k in fields] for r in table))
    write_tsv(output / 'members.tsv', ['member_id','representative_id','relation'],
              ([m,r,'exact' if m == r else 'near_duplicate'] for m,r in sorted(mapping.items())))
    plasmid_ids = {fid for fid,r in merged.items() if r['is_plasmid']}
    complete=set(complete_ids.read_text().split()) if complete_ids is not None and complete_ids.is_file() else set()
    if not complete <= set(mapping): raise ValueError('Confirmed IDs are absent from exact candidate catalogue')
    complete={mapping[fid] for fid in complete}
    fasta(output / 'reference.fasta', ((fid,sequences[fid]) for fid in sorted(merged)))
    fasta(output / 'plasmids.fasta', ((fid,sequences[fid]) for fid in sorted(plasmid_ids)))
    fasta(output / 'fragments.fasta', ((fid,sequences[fid]) for fid in sorted(plasmid_ids - circular - complete)))
    # Keep circularity prediction separate from independent completeness support.
    write_tsv(output / 'circularity.tsv', ['contig','circularity_candidate','independently_supported'], ([fid,str(fid in circular),str(fid in complete)] for fid in sorted(plasmid_ids)))
    predicted={r['feature_id'] for r in evidence if r['completeness']=='predicted_near_complete' and r['member_id']==r['feature_id']}
    write_tsv(output / 'structure.tsv', ['plasmid_id','structure_grade','completeness'],
              ([fid,'near_complete_candidate' if fid in complete or fid in predicted else 'circular_candidate' if fid in circular else 'fragment_or_unknown','independently_supported' if fid in complete else 'predicted_near_complete' if fid in predicted else 'not_established'] for fid in sorted(plasmid_ids)))
    shutil.copyfile(exact / 'samples.tsv', output / 'samples.tsv')
    manifest = json.loads((exact / 'manifest.json').read_text())
    manifest.update(schema_version=2, identity='strand-invariant exact identity followed by conservative MMseqs2 near-duplicate clustering', features=len(merged), clustering=dict(tool='MMseqs2',identity=identity,coverage=coverage,cov_mode=0,cluster_mode=2,
        strata='independently supported, circular candidates, and fragments clustered separately; background remains exact-only'),
        limitations=['contig representatives are not reconstructed closed plasmids; bin entities retained in candidate_evidence.tsv',
                     'circular candidate is not proof of completeness; complete IDs are an independent user-supplied evidence assertion',
                     'near-duplicate membership does not transfer exact coordinates; annotations use representative coordinates'])
    manifest['complete_ids_sha256'] = file_digest(complete_ids) if complete_ids is not None and complete_ids.is_file() else None
    manifest['files_sha256'] = {p.name:file_digest(p) for p in sorted(output.iterdir())}
    (output / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('integrate')
    for k in ['assembly','bins','summary','structure','output']: q.add_argument('--'+k,type=Path,required=True)
    q.add_argument('--sample',required=True);q.add_argument('--bin-score-threshold',type=float,default=.7)
    q=sub.add_parser('prepare')
    q.add_argument('--ids',nargs='+',required=True)
    for k in ['assemblies','candidates','evidence']: q.add_argument('--'+k,nargs='+',type=Path,required=True)
    q.add_argument('--output',type=Path,required=True);q.add_argument('--complete-ids',type=Path)
    q=sub.add_parser('finalize');q.add_argument('--exact',type=Path,required=True);q.add_argument('--clusters',nargs='*',type=Path,default=[])
    q.add_argument('--output',type=Path,required=True);q.add_argument('--identity',type=float,required=True);q.add_argument('--coverage',type=float,required=True);q.add_argument('--complete-ids',type=Path)
    a=vars(p.parse_args());command=a.pop('command');globals()[command](**a)
