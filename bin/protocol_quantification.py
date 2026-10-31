#!/usr/bin/env python3
"""Paired-fragment measurements on the frozen competitive reference (pysam)."""
import argparse
from collections import Counter
from pathlib import Path
import statistics
import json
import pysam
from protocol_catalogue import rows
from build_shared_catalogue import write_tsv


def measure(bam, catalogue, sample, output, min_mapq=10, max_mismatch_rate=0.02, filtered_bam=None):
    features=rows(catalogue/'features.tsv'); counts=Counter(); ambiguous=Counter(); mapped=Counter(); mismatch_pairs=0
    with pysam.AlignmentFile(str(bam),'rb') as stream:
        for read in stream.fetch(until_eof=True):
            if read.is_unmapped or read.is_secondary or read.is_supplementary: continue
            fid=read.reference_name; mapped[fid]+=1
            if read.mapping_quality<min_mapq or read.mapping_quality==255:
                ambiguous[fid]+=1;continue
            # Each proper pair has a single read1; both ends must map to the
            # same reference and each meet MAPQ (checked via mate in name-sort).
    # Name-sorted streaming avoids retaining all read pairs in memory.
    pysam.sort('-n','-o',str(output)+'.names.bam',str(bam))
    with pysam.AlignmentFile(str(output)+'.names.bam','rb') as stream, pysam.AlignmentFile(str(output)+'.pairs.bam','wb',template=stream) as pairs:
        import itertools
        for _,group in itertools.groupby(stream,key=lambda r:r.query_name):
            pair=[r for r in group if not(r.is_unmapped or r.is_secondary or r.is_supplementary)]
            if len(pair)!=2: continue
            a,b=pair
            if a.is_read1==b.is_read1 or not(a.is_proper_pair and b.is_proper_pair) or a.reference_id!=b.reference_id: continue
            if any(r.mapping_quality<min_mapq or r.mapping_quality==255 for r in pair):continue
            if any(r.get_tag('NM')/max(1,r.query_alignment_length)>max_mismatch_rate for r in pair):
                mismatch_pairs+=1;continue
            counts[a.reference_name]+=1
            pairs.write(a);pairs.write(b)
    Path(str(output)+'.names.bam').unlink()
    paired=filtered_bam if filtered_bam is not None else Path(str(output)+'.eligible.bam')
    pysam.sort('-o',str(paired),str(output)+'.pairs.bam')
    Path(str(output)+'.pairs.bam').unlink()
    pysam.index(str(paired))
    result=[]
    with pysam.AlignmentFile(str(paired),'rb') as stream:
        total=sum(counts.values()); rates={r['feature_id']:counts[r['feature_id']]/(int(r['length_bp'])/1000) for r in features};den=sum(rates.values())
        for feature in features:
            fid=feature['feature_id'];length=int(feature['length_bp']);depths=[0]*length
            # Both eligible ends were retained above; overlapping mates count once per base.
            for column in stream.pileup(fid,0,length,truncate=True,stepper='nofilter',min_base_quality=0,ignore_overlaps=False,max_depth=10000000):
                fragments=set()
                for item in column.pileups:
                    r=item.alignment
                    if item.is_del or item.is_refskip or r.is_unmapped or r.is_secondary or r.is_supplementary or not r.is_proper_pair or r.reference_id!=r.next_reference_id:continue
                    if r.mapping_quality<min_mapq or r.mapping_quality==255:continue
                    fragments.add(r.query_name)
                depths[column.reference_pos]=len(fragments)
            result.append([fid,sample,counts[fid],sum(depths)/length,statistics.median(depths),sum(d>0 for d in depths)/length,
                counts[fid]*1e9/(length*total) if total else 0,rates[fid]*1e6/den if den else 0,
                ambiguous[fid]/mapped[fid] if mapped[fid] else 0,feature['is_plasmid']])
    if filtered_bam is None:
        paired.unlink();Path(str(paired)+'.bai').unlink()
    output.with_suffix('.mapping_stats.json').write_text(json.dumps(dict(sample_id=sample,primary_mapped_ends=sum(mapped.values()),ambiguous_ends=sum(ambiguous.values()),mismatch_filtered_pairs=mismatch_pairs,eligible_paired_fragments=sum(counts.values()),min_mapq=min_mapq,max_mismatch_rate=max_mismatch_rate,pysam_version=pysam.__version__,overlapping_mates='once_per_base'),indent=2)+'\n')
    write_tsv(output,['feature_id','sample_id','paired_fragments','coverage','median_depth','breadth','rpkm','tpm','ambiguous_alignment_fraction','is_plasmid'],result)


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--bam',type=Path,required=True);p.add_argument('--catalogue',type=Path,required=True);p.add_argument('--sample',required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--max-mismatch-rate',type=float,default=.02)
 p.add_argument('--filtered-bam',type=Path)
 a=p.parse_args();measure(**vars(a))
 # Reuse the existing shared-table collector with native CoverM column names.
 data=rows(a.output)
 write_tsv(a.output.with_suffix('.coverm.tsv'),['Contig','sample Mean','sample RPKM','sample TPM','sample Read Count','sample Median','sample Covered Fraction','sample Ambiguous Alignment Fraction'],
  ([r[k] for k in ['feature_id','coverage','rpkm','tpm','paired_fragments','median_depth','breadth','ambiguous_alignment_fraction']] for r in data))
