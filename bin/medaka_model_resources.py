#!/usr/bin/env python3
"""Candidate full native model-load/compatibility gate after exact CLI selection.

No model downloads, inference, production wiring or cache acceptance is implied.
The original Medaka resolver, compatibility check and weight loader are used.
"""
import argparse
import gzip
import json
from pathlib import Path
from types import SimpleNamespace

from medaka_model_selection import select, sha


def capture(reads, assembly, native_args=(), threads='1'):
    observed = select(reads, assembly, native_args, threads)
    model_path = Path(observed['selected_model']['resolved_path'])
    import medaka.models as models
    import medaka.medaka as cli
    import medaka.datastore as datastore
    import torch
    package = Path(models.__file__).parent
    sources = {str(p): sha(p) for p in sorted(package.rglob('*.py'))}
    sources[str(Path(__file__).resolve())] = sha(__file__)
    # Reading the complete stream detects corrupted/truncated gzip trailers
    # which extracting just the TAR members need not read.
    if model_path.name.endswith('.gz'):
        with gzip.open(model_path, 'rb') as stream:
            while stream.read(1024 * 1024):
                pass
    cli.check_compatible(SimpleNamespace(model=str(model_path), data=str(reads)))
    with models.open_model(str(model_path)) as store:
        model = store.load_model(device=torch.device('cpu'))
        state = model.state_dict()
        if not state:
            raise ValueError('Native model has no state tensors')
        for name, tensor in state.items():
            if not torch.isfinite(tensor).all().item():
                raise ValueError('Non-finite native model tensor: ' + name)
        tensors = {name: {'shape': list(value.shape), 'dtype': str(value.dtype)}
                   for name, value in state.items()}
    # Re-run native selection so changed inputs/default resolution/source/model
    # cannot be certified using only the earlier observation.
    if observed != select(reads, assembly, native_args, threads):
        raise ValueError('Model selection identity changed during validation')
    if sources != {p: sha(p) for p in sources}:
        raise ValueError('Model loading source changed during validation')
    return {'schema': 1, 'scope': 'native model selection, full weight loading and native data compatibility only',
            'production_gate': False, 'formal_acceptance': False,
            'selection': observed, 'source_sha256': sources,
            'native_compatibility_passed': True, 'full_weights_loaded_cpu': True,
            'finite_state_tensors': tensors, 'torch_version': torch.__version__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reads', type=Path, required=True)
    parser.add_argument('--assembly', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect', type=Path)
    parser.add_argument('--threads', default='1')
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output path')
    native_args = args.native_args[1:] if args.native_args[:1] == ['--'] else args.native_args
    observed = capture(args.reads, args.assembly, native_args, args.threads)
    if args.expect and observed != json.loads(args.expect.read_text()):
        raise ValueError('Medaka model identity differs from expected receipt')
    with args.output.open('x') as stream:
        stream.write(json.dumps(observed, sort_keys=True, indent=2) + '\n')


if __name__ == '__main__':
    main()
