#!/usr/bin/env python3
"""Explicit resource-scan observer for mock integration; no model inference."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
if not args or Path(args[0]).name not in ['isescan_runtime_resources.py','integronfinder_runtime_resources.py','plasmidfinder_runtime_resources.py']:
    os.execv(sys.executable, [sys.executable] + args)

if Path(args[0]).name == 'plasmidfinder_runtime_resources.py':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-base64', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    request = parser.parse_args(args[1:])
    native = request.native_args[1:] if request.native_args[:1] == ['--'] else request.native_args
    identity = dict(schema_version=1, runtime=json.loads(base64.b64decode(request.runtime_base64)),
                    scope='EXPLICIT_MOCK_PLASMIDFINDER_RESOURCE_SCAN_NO_NATIVE_CLASSIFICATION',
                    native_arguments=native, sequence_sha256=hashlib.sha256(Path(native[native.index('-i')+1]).read_bytes()).hexdigest())
    if request.verify is not None:
        assert json.loads(request.verify.read_text()) == identity
    if request.output is not None:
        request.output.write_text(json.dumps(identity,sort_keys=True)+'\n')
    if request.execute:
        assert request.verify is not None
        os.execvp('plasmidfinder.py',['plasmidfinder.py']+native)
    sys.exit(0)

if Path(args[0]).name == 'integronfinder_runtime_resources.py':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-base64', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('native_args', nargs=argparse.REMAINDER)
    request = parser.parse_args(args[1:])
    native = request.native_args[1:] if request.native_args[:1] == ['--'] else request.native_args
    stable = list(native)
    if '--cpu' in stable:
        index = stable.index('--cpu')
        del stable[index:index+2]
    identity = dict(schema_version=1, runtime=json.loads(base64.b64decode(request.runtime_base64)),
                    scope='EXPLICIT_MOCK_INTEGRON_RESOURCE_SCAN_NO_MODEL_OR_TOPOLOGY_INFERENCE',
                    native_arguments=stable, sequence_sha256=hashlib.sha256(Path(native[-1]).read_bytes()).hexdigest())
    if request.verify is not None:
        assert json.loads(request.verify.read_text()) == identity
    if request.output is not None:
        request.output.write_text(json.dumps(identity,sort_keys=True)+'\n')
    if request.execute:
        assert request.verify is not None
        os.execvp('integron_finder',['integron_finder']+native)
    sys.exit(0)

parser = argparse.ArgumentParser()
parser.add_argument('--runtime-base64', required=True)
parser.add_argument('--seqfile', required=True)
parser.add_argument('--result-prefix', required=True)
parser.add_argument('--threads', required=True)
parser.add_argument('--output', type=Path)
parser.add_argument('--verify', type=Path)
parser.add_argument('--execute', action='store_true')
request = parser.parse_args(args[1:])
runtime = json.loads(base64.b64decode(request.runtime_base64))
identity = dict(schema_version=1, runtime=runtime,
                scope='EXPLICIT_MOCK_RESOURCE_SCAN_NO_NATIVE_MODEL',
                sequence_sha256=hashlib.sha256(Path(request.seqfile).read_bytes()).hexdigest(),
                output=request.result_prefix)
if request.verify is not None:
    assert json.loads(request.verify.read_text()) == identity
if request.output is not None:
    request.output.write_text(json.dumps(identity,sort_keys=True)+'\n')
if request.execute:
    assert request.verify is not None
    os.execvp('isescan.py',['isescan.py','--seqfile',request.seqfile,
                          '--output',request.result_prefix,'--nthread',request.threads])
