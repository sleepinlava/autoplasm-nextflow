#!/usr/bin/env python3
"""Observe fixed Medaka model selection without downloading or polishing.

This is a standalone candidate, not a production execution or cache gate.
It runs the exact native consensus Bash prefix, delegates CLI parsing to
Medaka, and refuses model download attempts even when native Bash would
hide the failure by falling back. A selected file hash does not validate
the model format, compatibility, or biological/scientific correctness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch


EXPECTED = {
    'models.py': '83f5d3293b23baad2ea9ba7b07c2cc0a5c75d2629c883e77f15215a79925cff1',
    'options.py': 'daa0150a00a2144c700b03a854b7161036ad04563b9910fe12d94417a6f26144',
    'medaka.py': 'e101e5b1ffad0e42893db1af62bfec109fd817968a67100645f71fcedb06e909',
    '__init__.py': '45d8c7d81643c7e84d0b8e941bd39cfaf6c58c4d80c8707e91c0a61f18ab3c14',
}
CONSENSUS_SHA = 'ed51264a7d108a10773dca2f2e6561fad2e0f3012a595d6d57fb6e5157d75f8c'
BOUNDARY = '\necho "Checking program versions"\n'
STATE_FIELDS = ['MODEL', 'BASECALLS', 'DRAFT', 'OUTPUT', 'THREADS', 'BATCH_SIZE',
                'PREFIX', 'NOFILLGAPS', 'GAPFILLCHAR', 'QUALITIES', 'MIN_MAPQ',
                'BACTERIA', 'BED_PATH', 'FORCE', 'xflag', 'mflag']


class SelectionRefused(ValueError):
    pass


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(path):
    p = Path(path)
    resolved = p.resolve(strict=True)
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise SelectionRefused(f'Requires regular file: {p}')
    return {'path': str(p.absolute()), 'resolved_path': str(resolved),
            'sha256': sha(resolved), 'size': resolved.stat().st_size,
            'mode': stat.S_IMODE(resolved.stat().st_mode)}


def verified_native():
    import medaka
    import medaka.models as models
    import medaka.options as options
    if medaka.__version__ != '2.2.2':
        raise SelectionRefused('Requires native Medaka2.2.2')
    package = Path(models.__file__).parent
    paths = [package / name for name in EXPECTED]
    for name, expected in EXPECTED.items():
        if sha(package / name) != expected:
            raise SelectionRefused(f'Fixed Medaka source differs: {name}')
    consensus = Path(sys.prefix) / 'bin/medaka_consensus'
    if sha(consensus) != CONSENSUS_SHA:
        raise SelectionRefused('Fixed medaka_consensus source differs')
    return models, options, consensus, paths + [consensus]


def refuse_download(url, *args, **kwargs):
    marker = os.environ.get('MEDAKA_SELECTION_NETWORK_MARKER')
    if marker:
        with open(marker, 'a') as stream:
            stream.write(json.dumps({'url': url}) + '\n')
    raise SelectionRefused('Model preparation required; automatic download prohibited: ' + url)


def native_cli(arguments):
    # This mode is only called by the private medaka shim. No other native
    # command is permitted to cross the prefix boundary into computation.
    allowed = (arguments == ['--version'] or arguments == ['tools', 'list_models']
               or arguments[:2] == ['tools', 'resolve_model'])
    if not allowed or not os.environ.get('MEDAKA_SELECTION_NETWORK_MARKER'):
        raise SelectionRefused('Unsupported internal Medaka CLI call')
    models, _, _, _ = verified_native()
    from medaka.medaka import main
    with patch.object(models.requests, 'get', refuse_download):
        sys.argv = ['medaka', *arguments]
        main()


def select(reads, assembly, native_args=(), threads='1', diagnostics=None):
    models, options, consensus, source_paths = verified_native()
    reads, assembly = str(reads), str(assembly)
    initial_inputs = {'reads': identity(reads), 'assembly': identity(assembly)}
    source_hashes = {str(p): sha(p) for p in source_paths}
    source_hashes[str(Path(__file__).resolve())] = sha(__file__)
    argv = ['-t', str(threads), *native_args, '-i', reads, '-d', assembly, '-o', './']
    with tempfile.TemporaryDirectory(prefix='medaka-selection-') as directory:
        work = Path(directory)
        marker = work / 'network.jsonl'
        state = work / 'state.bin'
        shim = work / 'medaka'
        shim.write_text('#!/bin/sh\nexec ' + shlex.join([sys.executable, str(Path(__file__).resolve()), '_native_cli']) + ' "$@"\n')
        shim.chmod(0o755)
        text = consensus.read_text()
        if text.count(BOUNDARY) != 1:
            raise SelectionRefused('Unexpected original Bash prefix boundary')
        probe = work / 'prefix.sh'
        probe.write_text(text.split(BOUNDARY)[0] + '\nprintf \'%s\\0\' ' +
                         ' '.join('"$' + name + '"' for name in STATE_FIELDS) +
                         ' > "$MEDAKA_SELECTION_STATE"\n')
        env = dict(os.environ, PATH=f'{work}:{Path(sys.prefix) / "bin"}:' + os.environ.get('PATH', ''),
                   MEDAKA_SELECTION_STATE=str(state), MEDAKA_SELECTION_NETWORK_MARKER=str(marker),
                   PYTHONDONTWRITEBYTECODE='1')
        process = subprocess.run(['bash', str(probe), *argv], capture_output=True,
                                 text=True, env=env, timeout=240)
        attempts = [json.loads(line) for line in marker.read_text().splitlines()] if marker.exists() else []
        if diagnostics is not None:
            diagnostics.update(stdout=process.stdout, stderr=process.stderr,
                               returncode=process.returncode, download_attempts_refused=attempts,
                               native_argv=argv, prefix_sha256=sha(probe))
        if attempts:
            raise SelectionRefused('Model preparation required; native download attempt refused (including any hidden fallback)')
        if process.returncode != 0 or not state.is_file():
            raise SelectionRefused(f'Original Medaka selection prefix failed: exit{process.returncode}')
        values = state.read_bytes().split(b'\0')
        if len(values) != len(STATE_FIELDS) + 1 or values[-1] != b'':
            raise SelectionRefused('Incomplete original Bash selection state')
        selected = dict(zip(STATE_FIELDS, (x.decode() for x in values[:-1])))
        # Native fallback keeps an ID. Resolve that ID using the same installed
        # resolver; refusing a download here must also refuse this observation.
        def refuse_final_resolution(url, *args, **kwargs):
            attempts.append({'url': url, 'phase': 'final-model-resolution'})
            if diagnostics is not None:
                diagnostics['download_attempts_refused'] = attempts
            raise SelectionRefused('Final selected model is not prepared; download prohibited')

        try:
            with patch.object(models.requests, 'get', refuse_final_resolution):
                model = models.resolve_model(selected['MODEL'])
        except (ValueError, OSError) as error:
            raise SelectionRefused('Final selected model cannot be resolved without preparation: ' + str(error)) from error
        model_identity = identity(model)
    final_inputs = {'reads': identity(reads), 'assembly': identity(assembly)}
    if initial_inputs != final_inputs:
        raise SelectionRefused('Input changed during selection')
    return {'schema': 1, 'scope': 'model-selection identity only',
            'scientific_readiness_certified': False, 'production_gate': False,
            'native_version': '2.2.2', 'inputs': final_inputs,
            'native_argv': argv, 'original_bash_state': selected,
            'selected_model': model_identity, 'source_sha256': source_hashes,
            'context': {'python': sys.executable, 'python_version': sys.version,
                        'home': str(Path.home()), 'model_stores': [str(p) for p in options.model_stores]},
            'model_format_and_compatibility_checked': False}


def main():
    if sys.argv[1:2] == ['_native_cli']:
        native_cli(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reads', required=True)
    parser.add_argument('--assembly', required=True)
    parser.add_argument('--threads', default='1')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect', type=Path, help='Require identical prior selection identity')
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    diagnostic_path = args.output.with_suffix(args.output.suffix + '.diagnostics.json')
    if args.output.exists() or diagnostic_path.exists():
        parser.error('Use fresh output paths; previous observations must not be overwritten')
    extra = args.native_args[1:] if args.native_args[:1] == ['--'] else args.native_args
    diagnostics = {}
    try:
        result = select(args.reads, args.assembly, extra, args.threads, diagnostics)
        if args.expect and json.loads(args.expect.read_text()) != result:
            raise SelectionRefused('Selection identity differs from expected observation')
        with args.output.open('x') as stream:
            stream.write(json.dumps(result, indent=2) + '\n')
    except (SelectionRefused, OSError, subprocess.SubprocessError) as error:
        print('Medaka model selection refused: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
    finally:
        with diagnostic_path.open('x') as stream:
            stream.write(json.dumps(diagnostics, indent=2) + '\n')


if __name__ == '__main__':
    main()
