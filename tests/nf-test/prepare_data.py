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


def prepare(destination):
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=False)
    lock = json.loads((HERE / 'datasets.lock.json').read_text())
    receipt = []
    for entry in lock['files']:
        url = f'https://raw.githubusercontent.com/{lock["source"]}/{entry["revision"]}/{entry["path"]}'
        target = root / entry['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as response, target.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        content = target.read_bytes()
        actual = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
        if len(content) != entry['size'] or actual != entry['git_blob_sha1']:
            raise ValueError(f'Upstream fixture identity mismatch: {entry["path"]}')
        receipt.append({**entry, 'url': url, 'sha256': hashlib.sha256(content).hexdigest()})
        print(f'Verified {entry["path"]}: {len(content)} bytes', flush=True)
    archive = root / 'databases/genomad/genomad_db_subset_v1.9.tar.gz'
    with tarfile.open(archive) as stream:
        stream.extractall(root / 'databases', filter='data')
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
    prepare(ap.parse_args().outdir)
