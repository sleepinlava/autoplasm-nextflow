#!/usr/bin/env python3
"""Probe-level verification of Medaka optional CLI branches (-x force, -B regions, RLE detection).

Only private fixture copies are mutated. Original reads/draft/model/indexes are
hashed before and after and must not change. Probe-only: no polishing inference
is executed in this driver; RLE real-transform execution remains open because
no RLE model is prepared locally and downloads are prohibited.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


REPO = Path(__file__).resolve().parent.parent
BIN = REPO / 'bin'
HELPERS = ['medaka_runtime_resources.py', 'medaka_index_resources.py',
           'medaka_model_resources.py', 'medaka_model_selection.py']


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def probe(reads, assembly, native_args, receipt, runtime):
    encoded = base64.b64encode(json.dumps(runtime).encode()).decode()
    command = [sys.executable, 'medaka_runtime_resources.py',
               '--runtime-base64', encoded,
               '--reads', str(reads), '--assembly', str(assembly),
               '--output', str(receipt), '--', *native_args]
    env = dict(os.environ, PATH=str(Path(sys.prefix) / 'bin') + ':' + os.environ.get('PATH', ''))
    return subprocess.run(command, cwd=BIN, capture_output=True, text=True, timeout=600, env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reads', type=Path, required=True)
    parser.add_argument('--draft', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.reads = args.reads.resolve(strict=True)
    args.draft = args.draft.resolve(strict=True)
    out = args.output.resolve()
    if out.exists():
        parser.error('Use a fresh output directory')
    out.mkdir(parents=True)

    import medaka
    assert medaka.__version__ == '2.2.2', 'Driver must run under the fixed native prefix'
    originals = {p: sha(p) for p in [args.reads, args.draft,
                                     Path(str(args.draft) + '.fai'),
                                     Path(str(args.draft) + '.map-ont.mmi')]}
    package_data = Path(medaka.__file__).parent / 'data'
    local_models = sorted(p.name for p in package_data.glob('*_model_pt.tar.gz'))
    rle_models = [name for name in local_models if 'rle' in name.lower()]
    runtime = {'engine': 'local', 'probe': 'optional-branches', 'conda': str(Path(sys.prefix))}
    record = {'phase': 'optional-branches', 'scenarios': {}, 'local_models': local_models,
              'rle_models_prepared': rle_models, 'helper_sha256': {}, 'pass': False}

    fixture = out / 'fixture'
    fixture.mkdir()
    draft = fixture / 'draft.fasta'
    shutil.copyfile(args.draft, draft)

    # Scenario 1+2: corrupt adjacent indexes; -x must skip them, default must refuse.
    Path(str(draft) + '.map-ont.mmi').write_bytes(b'BADMAGIC-not-a-minimap2-index' + b'\0' * 64)
    Path(str(draft) + '.fai').write_text('contig_1\t999999\t0\t80\t81\n')
    receipt = out / 'force-corrupt-adjacent.receipt.json'
    result = probe(args.reads, draft, ['-x'], receipt, runtime)
    assert result.returncode == 0, result.stderr
    observed = json.loads(receipt.read_text())
    assert observed['force_indexes'] is True and observed['source_indexes'] is None
    assert observed['rle'] is False and observed['regions'] is None
    record['scenarios']['force-corrupt-adjacent'] = {
        'returncode': result.returncode, 'force_indexes': observed['force_indexes'],
        'source_indexes': observed['source_indexes'],
        'note': 'corrupt adjacent FAI/MMI ignored under -x, matching native mini_align -f rebuild'}

    result = probe(args.reads, draft, [], out / 'default-corrupt-adjacent.receipt.json', runtime)
    assert result.returncode != 0
    assert 'Adjacent Medaka index differs from native reference rebuild' in result.stderr
    record['scenarios']['default-corrupt-adjacent'] = {
        'returncode': result.returncode, 'refused_before_receipt': True,
        'stderr_tail': result.stderr.strip().splitlines()[-1]}

    # Scenario 3: regions BED identity captured; control without -B records null.
    for path in [str(draft) + '.map-ont.mmi', str(draft) + '.fai']:
        os.unlink(path)
    bed = fixture / 'regions.bed'
    bed.write_text('contig_2\t0\t81815\n')
    result = probe(args.reads, draft, ['-B', str(bed)], out / 'regions.receipt.json', runtime)
    assert result.returncode == 0, result.stderr
    observed = json.loads((out / 'regions.receipt.json').read_text())
    assert observed['regions'] is not None
    assert observed['regions']['sha256'] == sha(bed)
    assert observed['native_args'] == ['-B', str(bed)]
    record['scenarios']['regions'] = {
        'returncode': result.returncode, 'regions_sha256': observed['regions']['sha256'],
        'native_args': observed['native_args']}

    result = probe(args.reads, draft, [], out / 'no-regions.receipt.json', runtime)
    assert result.returncode == 0, result.stderr
    observed = json.loads((out / 'no-regions.receipt.json').read_text())
    assert observed['regions'] is None and observed['force_indexes'] is False
    selected = observed['model']['selection']['selected_model']['resolved_path']
    record['scenarios']['no-regions'] = {'returncode': result.returncode,
                                         'regions': None, 'selected_model': selected}
    record['helper_sha256'] = observed['helper_sha256']

    # Scenario 4: native RLE detection CLI agrees with the helper gate on the
    # selected model. No prepared RLE model exists, so no real RLE transform run.
    env = dict(os.environ, PATH=str(Path(sys.prefix) / 'bin') + ':' + os.environ.get('PATH', ''))
    native = subprocess.run(['medaka', 'tools', 'is_rle_model', '--model', selected],
                            capture_output=True, text=True, env=env, timeout=240)
    assert native.returncode == 0, native.stderr
    native_flag = native.stdout.strip().splitlines()[-1] == 'True'
    from medaka.medaka import is_rle_encoder
    assert native_flag == is_rle_encoder(selected) == observed['rle'] == False
    record['scenarios']['rle-detection-equivalence'] = {
        'native_cli_is_rle_model': native_flag, 'helper_is_rle_encoder': False,
        'receipt_rle': observed['rle'],
        'gap': 'no prepared RLE model; transformed-draft branch grounded only in pinned native source'}

    for helper, recorded in record['helper_sha256'].items():
        assert (BIN / helper).is_file() and sha(BIN / helper) == recorded, helper
    assert originals == {p: sha(p) for p in originals}, 'Original resource changed'
    record['originals_unchanged'] = True
    record['pass'] = True
    with (out / 'run.json').open('x') as stream:
        stream.write(json.dumps(record, indent=2, default=str) + '\n')
    print('optional-branches verification passed')


if __name__ == '__main__':
    main()
