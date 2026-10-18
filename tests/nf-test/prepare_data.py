#!/usr/bin/env python3
"""Download pinned nf-core fixtures and translate their input layout to AutoPlasm.

This is only a dataset adapter: no simulated commands, random sequences, fake
replicates, or alternative workflow/test engine. Requires Python >= 3.12.
"""
import argparse
import csv
import gzip
import hashlib
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def prepare(destination, dataset="platforms"):
    if dataset not in ('platforms', 'plasmid', 'real-nodes', 'ena-multi'):
        raise ValueError(f'Unknown dataset: {dataset}')
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=False)
    lockfile = {'plasmid': 'plasmid-datasets.lock.json', 'real-nodes': 'real-nodes-datasets.lock.json',
                'ena-multi': 'ena-multisample.lock.json',
                'platforms': 'datasets.lock.json'}[dataset]
    lock = json.loads((HERE / lockfile).read_text())
    receipt = []
    for entry in lock['files']:
        if 'url' in entry:
            # Generic pinned artifact (Zenodo/Bitbucket/ENA/...): identity is
            # size + sha256 recorded in the lock entry.
            url = entry['url']
            target = root / entry.get('dest', f'extra/{url.rstrip("/").rsplit("/", 1)[-1]}')
        else:
            url = f'https://raw.githubusercontent.com/{lock["source"]}/{entry["revision"]}/{entry["path"]}'
            target = root / entry['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=600) as response, target.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        content = target.read_bytes()
        if 'url' in entry:
            ok = len(content) == entry['size']
            if 'sha256' in entry:
                ok = ok and hashlib.sha256(content).hexdigest() == entry['sha256']
            if 'md5' in entry:
                ok = ok and hashlib.md5(content).hexdigest() == entry['md5']
            if not ok:
                raise ValueError(f'Upstream artifact identity mismatch: {url}')
            receipt.append({'url': url, 'dest': str(target.relative_to(root)),
                            'size': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
                            **({'md5': entry['md5']} if 'md5' in entry else {})})
        else:
            actual = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
            if len(content) != entry['size'] or actual != entry['git_blob_sha1']:
                raise ValueError(f'Upstream fixture identity mismatch: {entry["path"]}')
            receipt.append({**entry, 'url': url, 'sha256': hashlib.sha256(content).hexdigest()})
        print(f'Verified {target.relative_to(root)}: {len(content)} bytes', flush=True)
        if entry.get('extract_to'):
            dest_dir = root / entry['extract_to']
            dest_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(target) as stream:
                stream.extractall(dest_dir, filter='data')
    archive = root / 'databases/genomad/genomad_db_subset_v1.9.tar.gz'
    if archive.exists():
        with tarfile.open(archive) as stream:
            stream.extractall(root / 'databases', filter='data')
    if dataset == 'ena-multi':
        # Real ENA runs (PRJNA848809, sugarbeet bacteriome): groups come from
        # the lock's ena_groups map (sample_title: d6_I_* infected, d6_C_* control).
        groups = lock.get('ena_groups', {})
        sheets = {'illumina': [dict(sample_id=run, group=grp,
                                    read1=str(root / 'ena' / f'{run}_1.fastq.gz'),
                                    read2=str(root / 'ena' / f'{run}_2.fastq.gz'))
                               for run, grp in sorted(groups.items())]}
    elif dataset in ('plasmid', 'real-nodes'):
        assembly = root / 'pUTI89.fasta'
        with gzip.open(root / 'data/genomics/prokaryotes/plasmids/pUTI89/pUTI89.fna.gz', 'rb') as source, assembly.open('wb') as out:
            shutil.copyfileobj(source, out)
        # Sample-tagged alias for the catalog/consensus conventions
        # (<sample>.plasmid_contigs.fasta); identical real bytes.
        shutil.copyfile(assembly, root / 'pUTI89.plasmid_contigs.fasta')
        sheets = {'assembly': [dict(sample_id='pUTI89', group='reference', assembly=str(assembly))]}
        if dataset == 'real-nodes':
            sars = root / 'data/genomics/sarscov2'
            minigut = root / 'minigut.fasta'
            with gzip.open(root / 'assemblies/MEGAHIT-test_minigut.contigs.fa.gz', 'rb') as source, minigut.open('wb') as out:
                shutil.copyfileobj(source, out)
            sheets['illumina'] = [dict(sample_id='sarscov2', group='reference',
                                      read1=str(sars / 'illumina/fastq/test_1.fastq.gz'),
                                      read2=str(sars / 'illumina/fastq/test_2.fastq.gz'))]
            sheets['ont'] = [dict(sample_id='sarscov2_ont', group='reference',
                                 long_reads=str(sars / 'nanopore/fastq/test.fastq.gz'))]
            sheets['pacbio_hifi'] = [dict(sample_id='gallus_hifi', group='reference',
                long_reads=str(root / 'data/genomics/eukaryotes/gallus_gallus/pacbio_metagenome.fastq.gz'))]

    else:
        assembly = root / 'assemblies/minigut.fasta'
        with gzip.open(root / 'assemblies/MEGAHIT-test_minigut.contigs.fa.gz', 'rb') as source, assembly.open('wb') as out:
            shutil.copyfileobj(source, out)
        # Keep two independent upstream samples, not six renamed copies of one sample.
        # Both are one group: no unsupported differential comparison is invented.
        paired = [dict(sample_id=sid, group='minigut', read1=str(root / f'test_data/{sid}_R1.fastq.gz'),
                       read2=str(root / f'test_data/{sid}_R2.fastq.gz'))
                  for sid in ('test_minigut', 'test_minigut_sample2')]
        sheets = {
            'illumina': paired,
            'assembly': [dict(sample_id='test_minigut', group='minigut', assembly=str(assembly))],
            'ont': [dict(sample_id='minigut_ont', group='minigut', long_reads=str(root / 'test_data/minigut_reads.fastq.gz'))],
            'hybrid': [{**paired[0], 'long_reads': str(root / 'test_data/minigut_reads.fastq.gz')}],
            'pacbio_hifi': [dict(sample_id='gallus_hifi', group='gallus', long_reads=str(
                root / 'data/genomics/eukaryotes/gallus_gallus/pacbio_metagenome.fastq.gz'))],
        }
    for platform, entries in sheets.items():
        with (root / f'{platform}.tsv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(entries[0]), delimiter='\t', lineterminator='\n')
            writer.writeheader()
            writer.writerows(entries)
    (root / 'download-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'Dataset ready: {root}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--outdir', required=True, help='A new directory')
    ap.add_argument('--dataset', choices=['platforms', 'plasmid', 'real-nodes', 'ena-multi'], default='platforms',
                    help='All platform fixtures, or one small real plasmid plus test database')
    args = ap.parse_args()
    prepare(args.outdir, dataset=args.dataset)
