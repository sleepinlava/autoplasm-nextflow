#!/usr/bin/env python3
"""Bind a completed SPAdes 4.1.0 FASTG to its actual final iteration k.

Run inside the assembler task, while its plan and iteration files still exist.
The generated plan's final graph copy, config and graph bytes must agree.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def collect(assembly_dir, graph, log, plan):
    assembly_dir = assembly_dir.resolve()
    copies = [stage for stage in plan if stage.get('short_name') == 'copy_files']
    if len(copies) != 1:
        raise ValueError('expected exactly one final copy_files stage')
    args = copies[0].get('args', [])
    if not args or Path(args[0]).name != 'copy_files.py' or len(args[1:]) % 2:
        raise ValueError('invalid copy_files argument pairs')
    pairs = list(zip(args[1::2], args[2::2]))
    matches = [(Path(a).resolve(), Path(b).resolve()) for a, b in pairs
               if Path(b).resolve() == assembly_dir / 'assembly_graph.fastg']
    if len(matches) != 1:
        raise ValueError('expected exactly one final FASTG copy')
    source, target = matches[0]
    match = re.fullmatch(r'K([0-9]+)', source.parent.name)
    if (not match or source.parent.parent != assembly_dir or
            source.name != 'assembly_graph.fastg'):
        raise ValueError('final graph source is not this assembly K directory')
    k = int(match.group(1))
    config = source.parent / 'configs/config.info'
    text = config.read_text()
    config_k = re.findall(r'^K\s+(\d+)\s*$', text, re.M)
    if config_k != [str(k)] or k <= 0 or k % 2 != 1:
        raise ValueError('final iteration K/config mismatch')
    if not re.search(r'^main_iteration\s+true\s*$', text, re.M):
        raise ValueError('graph source is not the main iteration')
    if graph.stat().st_size == 0 or not (digest(source) == digest(target) == digest(graph)):
        raise ValueError('final graph/source/export bytes mismatch or empty graph')
    log_text = log.read_text()
    for marker in ['===== K%d finished.' % k, '===== Copy files finished.',
                   '======= SPAdes pipeline finished.']:
        if marker not in log_text:
            raise ValueError('missing assembler completion marker: ' + marker)
    return {'schema': 1, 'producer': 'spades', 'version': '4.1.0', 'max_k': k,
            'graph_sha256': digest(graph), 'graph_file': graph.name,
            'copy_source': str(source.relative_to(assembly_dir)),
            'config_sha256': digest(config), 'log_sha256': digest(log)}


def load_plan(path):
    # Use the same bundled safe YAML reader as the declared SPAdes version.
    binary = shutil.which('spades.py')
    if not binary:
        raise ValueError('spades.py is not available in this task environment')
    sys.path.insert(0, str(Path(binary).resolve().parent))
    import spades_init
    spades_init.init()
    if spades_init.spades_version != '4.1.0':
        raise ValueError('unsupported SPAdes provenance version: ' + spades_init.spades_version)
    sys.path.insert(0, spades_init.ext_python_modules_home)
    import pyyaml3
    with path.open() as stream:
        plan = pyyaml3.safe_load(stream)
    if not isinstance(plan, list) or not all(isinstance(s, dict) for s in plan):
        raise ValueError('invalid SPAdes execution plan')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembly-dir', type=Path, required=True)
    parser.add_argument('--graph', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        plan_file = args.assembly_dir / 'run_spades.yaml'
        result = collect(args.assembly_dir, args.graph, args.log, load_plan(plan_file))
        result['plan_sha256'] = digest(plan_file)
    except Exception as error:
        print('SPAdes graph provenance violation: graph=%s: %s' %
              (args.graph, error), file=sys.stderr)
        return 2
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
