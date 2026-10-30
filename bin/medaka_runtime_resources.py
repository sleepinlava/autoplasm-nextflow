#!/usr/bin/env python3
"""Resolve Medaka resources before cache lookup and verify before execution.

Use exact native selection/loading, immutable task-private model/reference, and
default canonical indexes. RLE and forced-index modes keep their native flags;
external indexes are not consumed in those modes. No automatic model download.
"""
import argparse
import base64
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import medaka_index_resources as indexes
import medaka_model_resources as models
from medaka_model_selection import sha


def content(record):
    return {k: v for k, v in record.items() if k != 'resolved_path'}


def normalize_selection(record):
    record = json.loads(json.dumps(record))
    record.pop('native_argv')
    record['original_bash_state'].pop('THREADS')
    for value in record['inputs'].values():
        value.pop('path')
    record['source_sha256'] = {Path(k).name: v for k, v in record['source_sha256'].items()}
    return record


def prepare_reference(source, dest):
    with Path(source).open('rb') as stream:
        compressed = stream.read(2) == b'\x1f\x8b'
    opener = gzip.open if compressed else open
    with opener(source, 'rb') as stream, Path(dest).open('xb') as output:
        shutil.copyfileobj(stream, output)
    return compressed


def capture(runtime, reads, assembly, native_args):
    observed = models.capture(reads, assembly, native_args, threads='1')
    observed['selection'] = normalize_selection(observed['selection'])
    import medaka
    package = Path(medaka.__file__).parent
    observed['source_sha256'] = {
        ('medaka/' + str(Path(k).relative_to(package))) if Path(k).is_relative_to(package)
        else Path(k).name: v for k, v in observed['source_sha256'].items()}
    selection = observed['selection']
    source = Path(assembly).resolve(strict=True)
    state = selection['original_bash_state']
    from medaka.medaka import is_rle_encoder
    rle = is_rle_encoder(selection['selected_model']['resolved_path'])
    force = state['xflag'] == 'true'
    adjacent = None
    # Native RLE creates a transformed draft in its own output directory;
    # -x discards existing indexes. Do not bind resources it never reads.
    if not rle and not force:
        with source.open('rb') as stream:
            header = stream.read(18)
        compressed = header[:2] == b'\x1f\x8b'
        # samtools cannot index ordinary gzip. Its effective draft is the
        # complete decompressed private copy; adjacent source indexes cannot
        # be valid native indexes of this compressed byte stream.
        bgzf = compressed and header[3] & 4 and header[12:14] == b'BC'
        if compressed and not bgzf:
            if any(os.path.lexists(str(source) + suffix) for suffix in ['.fai', '.gzi', '.map-ont.mmi']):
                raise ValueError('Ordinary gzip draft has ambiguous adjacent indexes; prepare a clean compressed input or validated plain/BGZF reference')
            adjacent = {'ordinary_gzip': True, 'source_indexes': 'absent'}
        else:
            adjacent = indexes.capture(source)
    with tempfile.TemporaryDirectory(prefix='medaka-effective-reference-') as directory:
        draft = Path(directory) / 'draft.fasta'
        compressed = prepare_reference(source, draft)
        effective = indexes.capture(draft)
        canonical = effective['canonical']
        reference_content = content(effective['assembly'])
        # A copied file's mode is an implementation detail, not input identity.
        reference_content.pop('mode')
    bed = state['BED_PATH']
    bed_identity = indexes.identity(bed) if bed else None
    helpers = {p.name: sha(p) for p in [Path(__file__).resolve(),
               Path(indexes.__file__).resolve(), Path(models.__file__).resolve(),
               Path(__file__).with_name('medaka_model_selection.py')]}
    # The full input stream is checked again after reference/index preparation.
    if sha(source) != selection['inputs']['assembly']['sha256']:
        raise ValueError('Draft changed during resource preparation')
    return {'schema': 1, 'runtime': runtime, 'native_args': native_args,
            'model': observed, 'source_reference': indexes.identity(source),
            'compressed_reference': compressed, 'effective_reference': reference_content,
            'effective_indexes': canonical, 'source_indexes': adjacent,
            'rle': rle, 'force_indexes': force, 'regions': bed_identity,
            'index_tools': effective['tools'], 'mini_align': effective['native'],
            'helper_sha256': helpers}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-base64', required=True)
    parser.add_argument('--reads', type=Path, required=True)
    parser.add_argument('--assembly', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--threads', default='1')
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    native_args = args.native_args[1:] if args.native_args[:1] == ['--'] else args.native_args
    runtime = json.loads(base64.b64decode(args.runtime_base64))
    observed = capture(runtime, args.reads, args.assembly, native_args)
    if args.verify and observed != json.loads(args.verify.read_text()):
        raise ValueError('Medaka resource/context identity differs from pre-cache receipt')
    if args.output:
        with args.output.open('x') as stream:
            stream.write(json.dumps(observed, sort_keys=True, separators=(',', ':')) + '\n')
    if args.execute:
        if not args.verify:
            raise ValueError('Execution requires a pre-cache receipt')
        private = Path('medaka_private')
        private.mkdir(exist_ok=False)
        draft = private / 'draft.fasta'
        prepare_reference(args.assembly, draft)
        if sha(draft) != observed['effective_reference']['sha256']:
            raise ValueError('Private draft differs from verified complete reference')
        source_model = Path(observed['model']['selection']['selected_model']['resolved_path'])
        model = private / source_model.name
        shutil.copyfile(source_model, model)
        if sha(model) != observed['model']['selection']['selected_model']['sha256']:
            raise ValueError('Private model differs from verified model')
        # Last native option wins: bind the exact already-selected model and
        # complete effective draft while retaining every other original flag.
        command = [str(Path(sys.prefix) / 'bin/medaka_consensus'), '-t', args.threads,
                   *native_args, '-m', str(model.resolve()), '-i', str(args.reads.resolve()),
                   '-d', str(draft.resolve()), '-o', './']
        subprocess.run(command, check=True)
        if sha(model) != observed['model']['selection']['selected_model']['sha256']:
            raise ValueError('Private model changed during execution')
        if observed != capture(runtime, args.reads, args.assembly, native_args):
            raise ValueError('Resources changed during Medaka execution')


if __name__ == '__main__':
    main()
