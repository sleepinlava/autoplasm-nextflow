#!/usr/bin/env python3
"""Independent SAM/count/DNA oracle for the long-read execution fixture.

SAM is exported by SAMtools; production consumes BAM through Rsamtools. No
production parser is imported. This checks evidence counts, not host biology.
"""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re


def text_file(path):
    return gzip.open(path, 'rt') if str(path).endswith('.gz') else Path(path).open()


def fasta(path):
    result = {}
    name = None
    with text_file(path) as stream:
        for line in stream:
            if line.startswith('>'):
                name = line[1:].split()[0]
                assert name not in result, 'Duplicate FASTA ID'
                result[name] = ''
            elif line.strip():
                assert name is not None
                result[name] += line.strip()
    assert result and all(result.values())
    return result


def check(assembly, plasmids, reads, sam, links, sample, control=None):
    source, selected = fasta(assembly), fasta(plasmids)
    assert list(selected) == list(source)[:5], 'First-five partition differs'
    assert all(dna == source[key] for key, dna in selected.items()), 'Partition DNA differs'
    read_ids = set()
    with text_file(reads) as stream:
        while True:
            header = stream.readline()
            if not header:
                break
            dna, plus, quality = stream.readline().strip(), stream.readline(), stream.readline().strip()
            assert header.startswith('@') and plus.startswith('+') and len(dna) == len(quality)
            name = header[1:].split()[0]
            assert name not in read_ids, 'Duplicate FASTQ ID'
            read_ids.add(name)
    references, groups = {}, defaultdict(lambda: [set(), set()])
    accepted = 0
    with text_file(sam) as stream:
        for line in stream:
            if line.startswith('@SQ\t'):
                fields = dict(cell.split(':', 1) for cell in line.rstrip().split('\t')[1:])
                assert fields['SN'] not in references
                references[fields['SN']] = int(fields['LN'])
            elif not line.startswith('@') and line.strip():
                row = line.rstrip('\n').split('\t')
                assert len(row) >= 11 and row[0] in read_ids
                flag, mapq = int(row[1]), int(row[4])
                # Contract defaults: unpaired primary/supplementary, MAPQ>=20.
                if flag & (0x4 | 0x100 | 0x200 | 0x400 | 0x1) or mapq < 20:
                    continue
                assert row[2] in source
                assert re.fullmatch(r'(?:[0-9]+[MIDNSHP=X])+', row[5])
                accepted += 1
                groups[row[0]][bool(flag & 0x800)].add(row[2])
    assert references == {key: len(dna) for key, dna in source.items()}, 'SAM reference domain/length differs'
    assert accepted > 0
    supporting = defaultdict(set)
    for qname, (primary, supplementary) in groups.items():
        if not primary or not supplementary:
            continue
        targets = primary | supplementary
        for plasmid in targets.intersection(selected):
            for host in targets.difference(selected).intersection(source):
                supporting[plasmid, host].add(qname)
    expected = {key: len(value) for key, value in supporting.items() if len(value) >= 2}
    if control:
        truth = json.loads(Path(control).read_text())
        assert truth['kind'] == 'synthetic_spanning_read_execution_control'
        assert expected == {(truth['plasmid_id'], truth['host_id']): 2}, 'Known spanning-read control missing'
    with Path(links).open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        assert reader.fieldnames == ['plasmid_id', 'host_id', 'sample_id', 'evidence_type', 'score', 'supporting_data']
        table = list(reader)
    assert len(table) == len(expected)
    actual = {(row['plasmid_id'], row['host_id']): row for row in table}
    assert len(actual) == len(table) and set(actual) == set(expected), 'Link domain differs'
    for key, count in expected.items():
        row = actual[key]
        assert row['sample_id'] == sample and row['evidence_type'] == 'long_read_bridge'
        assert row['score'] == str(count)
        notes = dict(cell.split('=', 1) for cell in row['supporting_data'].split(';'))
        assert notes['host_id_type'] == 'contig' and int(notes['bridging_reads']) == count
        strength = count / ((len(source[key[0]]) / 1000) * (len(source[key[1]]) / 1000))
        assert math.isfinite(float(notes['strength'])) and math.isclose(float(notes['strength']), strength, rel_tol=5e-4)
        ranked = sorted({n for (plasmid, _), n in expected.items() if plasmid == key[0]}, reverse=True)
        assert int(notes['host_rank']) == ranked.index(count) + 1
    return {'pass': True, 'accepted_alignments': accepted, 'input_reads': len(read_ids),
            'expected_links': [{'plasmid_id': p, 'host_id': h, 'reads': n} for (p, h), n in sorted(expected.items())],
            'known_positive_control': bool(control),
            'scope': 'Native evidence-count/DNA/reference contract; upstream minigut and the explicit positive control are synthetic, no host biology/accuracy claim'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['assembly', 'plasmids', 'reads', 'sam', 'links', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--sample-id', default='minigut_ont')
    parser.add_argument('--control-manifest', type=Path)
    args = parser.parse_args()
    result = check(args.assembly, args.plasmids, args.reads, args.sam, args.links, args.sample_id, args.control_manifest)
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('PASS independent long-read evidence oracle; links', len(result['expected_links']))


if __name__ == '__main__':
    main()
