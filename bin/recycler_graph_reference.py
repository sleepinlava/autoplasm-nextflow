#!/usr/bin/env python
"""Export canonical forward FASTG sequences for Recycler's unprimed BAM lookup.

Unlike Recycler 0.7's first-orientation extractor, always use the graph's
actual unprimed sequence, even when its reverse record appears first.
Python 2/3 compatible; this does not infer assembly k.
"""
from __future__ import print_function
import argparse
import sys
from validate_recycler_inputs import graph_sequences, graph_provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--graph', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--provenance')
    args = parser.parse_args()
    try:
        sequences = graph_sequences(args.graph)
        if args.provenance:
            graph_provenance(args.graph, args.provenance)
    except Exception as error:
        print('Recycler graph reference violation: graph=%s: %s' %
              (args.graph, error), file=sys.stderr)
        return 2
    with open(args.out, 'w') as stream:
        for name in sorted(sequences):
            stream.write('>%s\n%s\n' % (name, sequences[name]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
