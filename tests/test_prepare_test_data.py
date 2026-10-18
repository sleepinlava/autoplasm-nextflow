"""Offline adapter tests; these do not stand in for real-tool P1/P2 runs."""
import gzip
import hashlib
import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_data', ROOT / 'tests/nf-test/prepare_data.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


@pytest.fixture
def source(tmp_path, monkeypatch):
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w:gz') as stream:
        content = b'test database placeholder for adapter unit tests only\n'
        info = tarfile.TarInfo('genomad_db/README')
        info.size = len(content)
        stream.addfile(info, io.BytesIO(content))
    payloads = {
        'databases/genomad/genomad_db_subset_v1.9.tar.gz': archive.getvalue(),
        'assemblies/MEGAHIT-test_minigut.contigs.fa.gz': gzip.compress(b'>c1\nACGT\n'),
    }
    lock = {'source': 'nf-core/test-datasets', 'files': [
        {'path': path, 'revision': 'a' * 40, 'size': len(data),
         'git_blob_sha1': hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()}
        for path, data in payloads.items()
    ]}
    (tmp_path / 'datasets.lock.json').write_text(json.dumps(lock))
    monkeypatch.setattr(adapter, 'HERE', tmp_path)
    requests = []

    def download(url, timeout):
        requests.append(url)
        prefix = 'https://raw.githubusercontent.com/nf-core/test-datasets/' + 'a' * 40 + '/'
        assert url.startswith(prefix)
        return io.BytesIO(payloads[url.removeprefix(prefix)])

    monkeypatch.setattr(adapter.urllib.request, 'urlopen', download)
    return payloads, requests


def test_verified_download_receipt_and_layout(source, tmp_path):
    payloads, requests = source
    out = tmp_path / 'prepared'
    adapter.prepare(out)
    assert len(requests) == len(payloads)
    assert (out / 'assemblies/minigut.fasta').read_text() == '>c1\nACGT\n'
    assert (out / 'databases/genomad_db/README').is_file()
    receipts = json.loads((out / 'download-receipt.json').read_text())
    assert {r['path']: r['sha256'] for r in receipts} == {
        path: hashlib.sha256(data).hexdigest() for path, data in payloads.items()
    }
    import csv
    sheets = {}
    for platform in ('illumina', 'assembly', 'ont', 'hybrid', 'pacbio_hifi'):
        with (out / f'{platform}.tsv').open() as stream:
            sheets[platform] = list(csv.DictReader(stream, delimiter='\t'))
    assert [r['sample_id'] for r in sheets['illumina']] == ['test_minigut', 'test_minigut_sample2']
    assert sheets['illumina'][0]['read1'] != sheets['illumina'][1]['read1']
    assert sheets['hybrid'][0]['read1'] == sheets['illumina'][0]['read1']
    assert sheets['hybrid'][0]['long_reads'] == sheets['ont'][0]['long_reads']
    assert sheets['assembly'][0]['assembly'] == str(out / 'assemblies/minigut.fasta')


@pytest.mark.parametrize('same_size', [True, False])
def test_corrupt_upstream_bytes_are_rejected(source, tmp_path, same_size):
    payloads, _ = source
    first = next(iter(payloads))
    data = payloads[first]
    payloads[first] = bytes([data[0] ^ 1]) + data[1:] if same_size else data[:-1]
    out = tmp_path / 'corrupt'
    with pytest.raises(ValueError, match='Upstream fixture identity mismatch'):
        adapter.prepare(out)
    assert not (out / 'download-receipt.json').exists()
    assert not (out / 'illumina.tsv').exists()


def test_existing_destination_is_not_overwritten(source, tmp_path):
    _, requests = source
    out = tmp_path / 'existing'
    out.mkdir()
    marker = out / 'keep'
    marker.write_text('original')
    with pytest.raises(FileExistsError):
        adapter.prepare(out)
    assert marker.read_text() == 'original'
    assert requests == []


def test_small_plasmid_dataset_uses_only_reference_and_database(source, tmp_path):
    payloads, requests = source
    old = 'assemblies/MEGAHIT-test_minigut.contigs.fa.gz'
    new = 'data/genomics/prokaryotes/plasmids/pUTI89/pUTI89.fna.gz'
    payloads[new] = payloads.pop(old)
    lock = json.loads((tmp_path / 'datasets.lock.json').read_text())
    for entry in lock['files']:
        if entry['path'] == old:
            entry['path'] = new
    (tmp_path / 'plasmid-datasets.lock.json').write_text(json.dumps(lock))
    out = tmp_path / 'small'
    adapter.prepare(out, dataset='plasmid')
    assert len(requests) == 2
    assert (out / 'pUTI89.fasta').read_text() == '>c1\nACGT\n'
    assert (out / 'assembly.tsv').read_text().splitlines() == [
        'sample_id\tgroup\tassembly', f'pUTI89\treference\t{out}/pUTI89.fasta',
    ]
    assert not (out / 'illumina.tsv').exists()


@pytest.fixture
def real_nodes_source(tmp_path, monkeypatch):
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w:gz') as stream:
        content = b'test database placeholder for adapter unit tests only\n'
        info = tarfile.TarInfo('genomad_db/README')
        info.size = len(content)
        stream.addfile(info, io.BytesIO(content))
    gbk = io.BytesIO()
    with tarfile.open(fileobj=gbk, mode='w:gz') as stream:
        content = b'LOCUS       fake\n'
        info = tarfile.TarInfo('cluster1.gbk')
        info.size = len(content)
        stream.addfile(info, io.BytesIO(content))
    github_payloads = {
        'databases/genomad/genomad_db_subset_v1.9.tar.gz': archive.getvalue(),
        'data/genomics/prokaryotes/plasmids/pUTI89/pUTI89.fna.gz': gzip.compress(b'>c1\nACGT\n'),
        'data/genomics/sarscov2/genome/genome.fasta': b'>s\nACGT\n',
        'data/genomics/sarscov2/illumina/fastq/test_1.fastq.gz': b'@r\n',
        'data/genomics/sarscov2/illumina/fastq/test_2.fastq.gz': b'@r\n',
        'data/genomics/sarscov2/nanopore/fastq/test.fastq.gz': b'@r\n',
        'assemblies/MEGAHIT-test_minigut.contigs.fa.gz': gzip.compress(b'>m1\nACGT\n>m2\nTT\n'),
        'test_data/minigut_reads.fastq.gz': b'@l\n',
        'test_data/test_minigut_R1.fastq.gz': b'@p1\n',
        'test_data/test_minigut_R2.fastq.gz': b'@p2\n',
        'data/genomics/eukaryotes/gallus_gallus/pacbio_metagenome.fastq.gz': b'@h\n',
        'data/genomics/prokaryotes/streptomyces_coelicolor/fixtures_bigslice_gbk.tar.gz': gbk.getvalue(),
    }
    generic = b'generic model bytes\n'
    files = [
        {'path': path, 'revision': 'a' * 40, 'size': len(data),
         'git_blob_sha1': hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest(),
         **({'extract_to': 'gbk/streptomyces_coelicolor'} if path.endswith('gbk.tar.gz') else {})}
        for path, data in github_payloads.items()
    ]
    files.append({'url': 'https://example.org/model.bin', 'dest': 'models/model.bin',
                  'size': len(generic), 'sha256': hashlib.sha256(generic).hexdigest()})
    lock = {'source': 'nf-core/test-datasets', 'files': files}
    (tmp_path / 'real-nodes-datasets.lock.json').write_text(json.dumps(lock))
    monkeypatch.setattr(adapter, 'HERE', tmp_path)

    def download(url, timeout):
        prefix = 'https://raw.githubusercontent.com/nf-core/test-datasets/' + 'a' * 40 + '/'
        if url.startswith(prefix):
            return io.BytesIO(github_payloads[url.removeprefix(prefix)])
        assert url == 'https://example.org/model.bin'
        return io.BytesIO(generic)

    monkeypatch.setattr(adapter.urllib.request, 'urlopen', download)
    return github_payloads


def test_real_nodes_layout_generic_url_and_extraction(real_nodes_source, tmp_path):
    out = tmp_path / 'real'
    adapter.prepare(out, dataset='real-nodes')
    # github fixtures verified and transformed
    assert (out / 'pUTI89.fasta').read_text() == '>c1\nACGT\n'
    assert (out / 'pUTI89.plasmid_contigs.fasta').read_text() == '>c1\nACGT\n'
    assert (out / 'minigut.fasta').read_text() == '>m1\nACGT\n>m2\nTT\n'
    # tar archive unpacked to the requested directory
    assert (out / 'gbk/streptomyces_coelicolor/cluster1.gbk').is_file()
    # generic url artifact verified by sha256 and placed at dest
    assert (out / 'models/model.bin').read_bytes() == b'generic model bytes\n'
    receipts = json.loads((out / 'download-receipt.json').read_text())
    generic_receipts = [r for r in receipts if r.get('dest') == 'models/model.bin']
    assert len(generic_receipts) == 1
    assert generic_receipts[0]['sha256'] == hashlib.sha256(b'generic model bytes\n').hexdigest()
    # sample sheets for the four real-nodes platforms
    for platform in ('assembly', 'illumina', 'ont', 'pacbio_hifi'):
        assert (out / f'{platform}.tsv').is_file()


def test_generic_url_sha256_mismatch_is_rejected(real_nodes_source, tmp_path):
    lock_path = tmp_path / 'real-nodes-datasets.lock.json'
    lock = json.loads(lock_path.read_text())
    entry = next(e for e in lock['files'] if 'url' in e)
    entry['sha256'] = '0' * 64
    lock_path.write_text(json.dumps(lock))
    with pytest.raises(ValueError, match='Upstream artifact identity mismatch'):
        adapter.prepare(tmp_path / 'bad', dataset='real-nodes')


def test_ena_multi_dataset_layout(tmp_path, monkeypatch):
    payloads = {}
    files = []
    groups = {'SRR000001': 'infected', 'SRR000002': 'control'}
    for run in groups:
        for mate in ('1', '2'):
            data = f'@{run}_{mate}\n'.encode()
            name = f'ena/{run}_{mate}.fastq.gz'
            payloads[f'https://ftp.sra.ebi.ac.uk/vol1/fastq/x/{run}_{mate}.fastq.gz'] = data
            files.append({'url': f'https://ftp.sra.ebi.ac.uk/vol1/fastq/x/{run}_{mate}.fastq.gz',
                          'dest': name, 'size': len(data),
                          'md5': hashlib.md5(data).hexdigest()})
    lock = {'source': 'ENA test', 'ena_groups': groups, 'files': files}
    (tmp_path / 'ena-multisample.lock.json').write_text(json.dumps(lock))
    monkeypatch.setattr(adapter, 'HERE', tmp_path)
    monkeypatch.setattr(adapter.urllib.request, 'urlopen',
                        lambda url, timeout: io.BytesIO(payloads[url]))
    out = tmp_path / 'ena'
    adapter.prepare(out, dataset='ena-multi')
    import csv
    with (out / 'illumina.tsv').open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert [r['sample_id'] for r in rows] == ['SRR000001', 'SRR000002']
    assert [r['group'] for r in rows] == ['infected', 'control']
    assert rows[0]['read1'].endswith('ena/SRR000001_1.fastq.gz')
    # md5 tampering is rejected
    lock['files'][0]['md5'] = '0' * 32
    (tmp_path / 'ena-multisample.lock.json').write_text(json.dumps(lock))
    with pytest.raises(ValueError, match='Upstream artifact identity mismatch'):
        adapter.prepare(tmp_path / 'ena-bad', dataset='ena-multi')
