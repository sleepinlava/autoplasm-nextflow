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
if not args or Path(args[0]).name != 'isescan_runtime_resources.py':
    os.execv(sys.executable, [sys.executable] + args)

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
