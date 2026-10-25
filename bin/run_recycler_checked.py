#!/usr/bin/env python
"""Run Recycler after input validation; report edge-free graphs explicitly.

Recycler 0.7 crashes in percentile([]) after removing all isolated nodes.
A graph with zero edges has no cycles. No tool exception is converted to zero.
Python 2/3 compatible, executed in the fixed Recycler environment.
"""
from __future__ import print_function
import argparse
import json
import os
import runpy
import sys
from distutils.spawn import find_executable
from recyclelib import utils
from recyclelib.utils import get_fastg_digraph


def configure_k_defaults(k):
    # v0.7 CLI passes max_k explicitly to some calls but omits it from
    # self-loop selection, output names and nested coverage calculations.
    # Apply the same requested k to those omitted defaults. Explicit arguments
    # still win. Refuse unexpected signatures rather than patching blindly.
    expected = [('get_seq_from_path', (55, True)),
                ('get_wgtd_path_coverage_CV', (55,)),
                ('get_path_mean_std', (55,))]
    for name, defaults in expected:
        function = getattr(utils, name)
        if function.__defaults__ != defaults:
            raise ValueError('unsupported Recycler helper defaults: ' + name)
    for name, defaults in expected:
        getattr(utils, name).__defaults__ = (k,) + defaults[1:]
    return [name for name, _ in expected]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--graph', required=True)
    parser.add_argument('--bam', required=True)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    with open(args.contract) as stream:
        contract = json.load(stream)
    graph = get_fastg_digraph(args.graph)
    contract['graph_edges'] = graph.number_of_edges()
    if graph.number_of_edges() == 0:
        os.mkdir(args.out)
        stem = os.path.splitext(os.path.basename(args.graph))[0]
        for suffix in ['.cycs.fasta', '.cycs.paths_w_cov.txt']:
            with open(os.path.join(args.out, stem + suffix), 'w'):
                pass
        contract['execution_state'] = 'skipped_no_graph_edges'
        print('Recycler: no graph edges; no candidate cycles; reconstruction skipped')
    else:
        # A failing Recycler remains a failing task, including unexpected errors.
        contract['max_k_default_adapter'] = configure_k_defaults(contract['max_k'])
        executable = find_executable('recycle.py')
        if executable is None:
            raise ValueError('recycle.py is not available')
        sys.argv = [executable, '-g', args.graph, '-k', str(contract['max_k']),
                    '-b', args.bam, '-o', args.out]
        runpy.run_path(executable, run_name='__main__')
        contract['execution_state'] = 'recycler_completed'
    with open(args.contract, 'w') as stream:
        json.dump(contract, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
