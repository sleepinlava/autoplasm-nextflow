#!/usr/bin/env python
"""Check complete FASTG-node BAM/BAI inputs before Recycler (Python2/3).

This validates representation and index usability, not assembly k or biology.
The producer must generate this BAM and its adjacent index from this graph.
"""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import sys


def graph_sequences(path):
    oriented = {}
    name = None
    sequence = []
    with open(path) as stream:
        for number, line in enumerate(stream, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith('>'):
                if name is not None:
                    oriented[name] = ''.join(sequence)
                fields = line[1:].split()
                if not fields:
                    raise ValueError('%s:%d: empty FASTG header' % (path, number))
                header = fields[0]
                if not header.endswith(';'):
                    raise ValueError('%s:%d: FASTG header must end with semicolon' % (path, number))
                name = header[:-1].split(':', 1)[0]
                if not name or name in oriented:
                    raise ValueError('%s:%d: empty or duplicate graph node %r' % (path, number, name))
                sequence = []
            else:
                if name is None:
                    raise ValueError('%s:%d: sequence before graph header' % (path, number))
                sequence.append(line)
    if name is not None:
        if name in oriented:
            raise ValueError('%s: duplicate graph node %r' % (path, name))
        oriented[name] = ''.join(sequence)
    if not oriented or any(not seq for seq in oriented.values()):
        raise ValueError('%s: graph has no nodes or an empty sequence' % path)
    forward = dict((name, seq) for name, seq in oriented.items() if not name.endswith("'"))
    if not forward or any(name[:-1] not in forward for name in oriented if name.endswith("'")):
        raise ValueError('%s: reverse graph node lacks its forward reference' % path)
    return forward


def graph_references(path):
    return dict((name, len(seq)) for name, seq in graph_sequences(path).items())


def digest(path):
    value = hashlib.sha256()
    with open(path, 'rb') as stream:
        while True:
            data = stream.read(1024 * 1024)
            if not data:
                break
            value.update(data)
    return value.hexdigest()


def graph_provenance(graph, path):
    with open(path) as stream:
        record = json.load(stream)
    k = record.get('max_k')
    if (record.get('schema') != 1 or record.get('producer') != 'spades' or
            record.get('version') != '4.1.0'):
        raise ValueError('unsupported graph provenance schema/producer/version: %s' % path)
    # bool is an int in both Python2 and Python3; exclude it explicitly.
    if isinstance(k, bool) or not isinstance(k, type(1)) or k <= 0 or k % 2 != 1:
        raise ValueError('invalid graph maximum k: %r' % k)
    if record.get('graph_sha256') != digest(graph):
        raise ValueError('graph/provenance SHA256 mismatch: %s' % path)
    return record


def validate(graph, bam_path):
    import pysam
    references = graph_references(graph)
    index = bam_path + '.bai'
    if not os.path.isfile(index):
        raise ValueError('missing adjacent BAM index: %s' % index)
    bam = pysam.AlignmentFile(bam_path, 'rb')
    try:
        if not bam.has_index() or not bam.check_index():
            raise ValueError('unusable BAM index: %s' % index)
        header = bam.header.to_dict() if hasattr(bam.header, 'to_dict') else dict(bam.header)
        if header.get('HD', {}).get('SO') != 'coordinate':
            raise ValueError('BAM must declare coordinate sort order: %s' % bam_path)
        actual = dict(zip(bam.references, bam.lengths))
        unexpected = sorted(set(actual) - set(references))
        missing = sorted(set(references) - set(actual))
        if unexpected or missing:
            raise ValueError('graph/BAM reference mismatch: unexpected=%s missing=%s (first3 each)' %
                             (unexpected[:3], missing[:3]))
        for name in sorted(references):
            if actual[name] != references[name]:
                raise ValueError('graph/BAM reference length mismatch for %s: graph=%d BAM=%d' %
                                 (name, references[name], actual[name]))
            # Force an indexed lookup; an empty but valid reference is allowed.
            try:
                next(bam.fetch(name))
            except StopIteration:
                pass
    finally:
        bam.close()
    return {'graph': graph, 'bam': bam_path, 'index': index,
            'graph_references': len(references),
            'sha256': dict((key, digest(value)) for key, value in
                           [('graph', graph), ('bam', bam_path), ('index', index)])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--graph', required=True)
    parser.add_argument('--bam', required=True)
    parser.add_argument('--out')
    parser.add_argument('--provenance')
    args = parser.parse_args()
    try:
        result = validate(args.graph, args.bam)
        if args.provenance:
            record = graph_provenance(args.graph, args.provenance)
            result['max_k'] = record['max_k']
            result['provenance_sha256'] = digest(args.provenance)
    except Exception as error:
        print('Recycler input contract violation: graph=%s bam=%s: %s' %
              (args.graph, args.bam, error), file=sys.stderr)
        return 2
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.out:
        with open(args.out, 'w') as stream:
            stream.write(text)
    else:
        print(text, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
