#!/usr/bin/env python3
"""Resolve fixed SemiBin's actual CLI read set inside its execution environment."""
import argparse
import base64
import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
import shutil
import stat
import sys


def resource(path):
    """Content/layout identity; reject incomplete, cyclic or special resources."""
    root = Path(path)
    entries = []

    def visit(p, relative, ancestors):
        link = os.readlink(p) if p.is_symlink() else None
        before = p.stat()
        mode = stat.S_IMODE(before.st_mode)
        if stat.S_ISDIR(before.st_mode):
            key = (before.st_dev, before.st_ino)
            if key in ancestors:
                raise ValueError('Resource directory symlink cycle: ' + str(p))
            entries.append(dict(path=relative, kind='directory', mode=mode, link=link))
            for child in sorted(p.iterdir(), key=lambda x: x.name):
                visit(child, relative + '/' + child.name, ancestors | {key})
        elif stat.S_ISREG(before.st_mode):
            digest = hashlib.sha256()
            with p.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            after = p.stat()
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                    before.st_mode) != (after.st_dev, after.st_ino, after.st_size,
                                        after.st_mtime_ns, after.st_mode):
                raise ValueError('Resource changed while hashing: ' + str(p))
            entries.append(dict(path=relative, kind='file', bytes=after.st_size,
                                sha256=digest.hexdigest(), mode=mode, link=link))
        else:
            raise ValueError('Resource member is not regular file/directory: ' + str(p))

    visit(root, '.', set())
    return entries


def capture(runtime, native_args):
    version = importlib.import_module('SemiBin.semibin_version')
    if version.__version__ != '2.4.1':
        raise ValueError('SemiBin resource resolver requires native 2.4.1')
    main = importlib.import_module('SemiBin.main')
    utils = importlib.import_module('SemiBin.utils')
    args = main.parse_args(native_args)
    if args.cmd != 'single_easy_bin':
        raise ValueError('Expected SemiBin single_easy_bin command')
    utils.set_training_type(logging.getLogger('semibin-resources'), args)
    package = Path(version.__file__).parent
    resources = {'bundled_marker': resource(package / 'marker.hmm'),
                 'package_code': {p.name: resource(p) for p in sorted(package.glob('*.py'))}}
    if args.orf_finder == 'fraggenescan' and args.prodigal_output_faa is None:
        # SemiBin2.4.1 calls the binary directly, with -w0 -t complete.
        # FragGeneScan1.32 derives train/ from the *invoked argv[0]*, so do
        # not resolve an executable symlink before locating its models.
        binary = shutil.which('FragGeneScan')
        if binary is None:
            raise ValueError('Selected SemiBin FragGeneScan binary not found in PATH')
        training = Path(binary).parent / 'train'
        required = ['gene', 'rgene', 'noncoding', 'start', 'stop', 'stop1',
                    'start1', 'pwm', 'complete']
        for name in required:
            if not (training / name).is_file():
                raise ValueError('Missing selected FragGeneScan training file: ' + str(training / name))
        resources['fraggenescan'] = dict(
            invoked_binary=binary, training_directory=str(training),
            whole_genome=0, selected_model='complete',
            binary=resource(binary), training=resource(training))
    # Capture explicit overrides too; the real native parser applies aliases and
    # precedence. Input files already staged by Nextflow are checked as well.
    file_fields = ['contig_fasta', 'bams', 'abundances', 'depth_metabat2',
                   'prodigal_output_faa', 'taxonomy_results_fname']
    for field in file_fields:
        value = getattr(args, field, None)
        if value is not None:
            values = value if isinstance(value, list) else [value]
            resources[field] = [resource(v) for v in values]
    if args.environment is not None:
        resources['pretrained_model'] = resource(utils.get_model_path(args.environment))
    elif args.training_type == 'semi' and args.taxonomy_results_fname is None:
        ref = args.GTDB_reference
        if ref is None:
            ref = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'SemiBin/mmseqs2-GTDB'
        ref = Path(ref)
        if not (ref / 'GTDB').exists():
            raise ValueError('Prepare the selected SemiBin GTDB reference before cache lookup (SemiBin2 download_GTDB --reference-db PATH); missing ' + str(ref / 'GTDB'))
        # GTDB is an MMseqs prefix: all neighbouring index/taxonomy files matter.
        resources['gtdb_reference_directory'] = resource(ref)
    parsed = vars(args).copy()
    # CPUs are already present in the consumer task script/cache key. A probe
    # needs no GPU inference or the consumer's full CPU allocation to hash bytes.
    parsed.pop('num_process', None)
    return dict(schema_version=1, tool='SemiBin', version=version.__version__,
                runtime=runtime, parsed_arguments=parsed, resources=resources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-base64', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    native_args = args.native_args[1:] if args.native_args[:1] == ['--'] else args.native_args
    runtime = json.loads(base64.b64decode(args.runtime_base64).decode('utf-8'))
    identity = capture(runtime, native_args)
    if args.verify is not None and json.loads(args.verify.read_text()) != identity:
        raise ValueError('SemiBin runtime resources or resolved arguments differ from pre-lookup identity')
    if args.output is not None:
        args.output.write_text(json.dumps(identity, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n')
    if args.execute:
        if args.verify is None:
            raise ValueError('--execute requires a verified pre-lookup receipt')
        # Use this exact, already resolved argv. Expanding ext.args a second
        # time in a separate shell command could select different parameters.
        os.execvp('SemiBin2', ['SemiBin2'] + native_args)


if __name__ == '__main__':
    main()
