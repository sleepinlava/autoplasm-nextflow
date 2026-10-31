#!/usr/bin/env python3
"""Input pair identity, original byte checksums and native fastp retention."""
import argparse
import gzip
import itertools
import json
from pathlib import Path
from build_shared_catalogue import file_digest,write_tsv


def names(path):
    with (gzip.open(path,'rt') if path.suffix.lower()=='.gz' else path.open()) as f:
        while header:=f.readline():
            sequence,plus,quality=f.readline(),f.readline(),f.readline()
            if not header.startswith('@') or not plus.startswith('+') or len(sequence.rstrip())!=len(quality.rstrip()):raise ValueError(f'{path}: malformed FASTQ record')
            name=header[1:].split()[0]
            yield name[:-2] if name.endswith(('/1','/2')) else name


def audit(sample,reads,output):
    output.mkdir();n=0
    for a,b in itertools.zip_longest(names(reads[0]),names(reads[1])):
        if a is None or b is None or a!=b:raise ValueError(f'{sample}: paired FASTQ IDs/order differ at pair {n+1}')
        n+=1
    write_tsv(output/'checksums.tsv',['sample_id','mate','path','sha256','pairs'],([sample,i,str(path),file_digest(path),n] for i,path in enumerate(reads,1)))


def retention(sample,fastp,reads,output):
    data=json.loads(fastp.read_text());before=int(data['summary']['before_filtering']['total_reads']);after=int(data['summary']['after_filtering']['total_reads'])
    final=sum(1 for _ in names(reads[0]))*2
    write_tsv(output,['sample_id','raw_reads','post_fastp_reads','post_host_reads','fastp_retention','host_step_retention'],[[sample,before,after,final,after/before if before else 0,final/after if after else 0]])

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 for command in ['audit','retention']:
  q=sub.add_parser(command);q.add_argument('--sample',required=True);q.add_argument('--reads',type=Path,nargs=2,required=True);q.add_argument('--output',type=Path,required=True)
  if command=='retention':q.add_argument('--fastp',type=Path,required=True)
 a=vars(p.parse_args());fn=a.pop('command');globals()[fn](**a)
