#!/usr/bin/env python3
"""Freeze local test evidence without executing tests or downloading dependencies.

Installed software and package caches are inventoried, not duplicated; environment
receipts and model weights inside them are retained. All other scoped files are
CoW copied, hashed and independently verifiable. Never follows directory symlinks.
"""
import argparse
import ast
import collections
import datetime as dt
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

FICLONE = 0x40049409
MODEL_EXT = {'.h5', '.hdf5', '.hdf', '.pt', '.pth', '.ckpt', '.onnx', '.safetensors', '.pkl', '.pickle', '.joblib', '.tflite'}
DATA_EXT = {'.fa', '.fna', '.fasta', '.fastq', '.fq', '.bam', '.sam', '.cram', '.gfa', '.fastg', '.gbk', '.gbff', '.dmnd', '.mmi', '.msh', '.bwt', '.bt2', '.bt2l'}


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def command(root, args):
    p = subprocess.run(args, cwd=root, capture_output=True, timeout=120)
    if p.returncode:
        raise RuntimeError(f'Failed {args[0:2]}: {p.stderr[:300]!r}')
    return p.stdout


def roles(rel):
    p = Path(rel); lower = rel.lower(); name = p.name.lower()
    r = []
    if p.suffix.lower() in MODEL_EXT or any(x in {'models', 'weights', 'checkpoints'} for x in p.parts): r.append('model_or_model_asset')
    if p.suffix.lower() in DATA_EXT or (p.suffix == '.gz' and Path(p.stem).suffix.lower() in DATA_EXT): r.append('sequence_data_or_index')
    if any(x in {'fixtures', 'r_mock', 'mock_e2e'} for x in p.parts): r.append('fixture_or_mock')
    if name.endswith('.lock') or '.lock.' in name or name == 'uv.lock': r.append('dependency_or_data_lock')
    if name.endswith('.nf.test') or (p.suffix == '.py' and name.startswith(('test_', 'run_', 'check_')) and 'tests' in p.parts): r.append('test_entry_or_harness')
    if name.endswith('.snap'): r.append('expected_snapshot')
    if 'conda-meta' in p.parts or name in {'pyvenv.cfg', 'direct_url.json'}: r.append('environment_receipt')
    if rel.startswith('results/') or name.startswith('.nextflow.log') or name == '.nf-test.log': r.append('historical_result_or_runtime')
    if rel.startswith('docs/tool-audit/'): r.append('audit_evidence')
    if not r: r.append('supporting_file')
    return r


def walk(root, archive):
    excluded_root = {'.git', '.agents', '.aws', '.codex', '.code', 'lazygit'}
    def descend(directory, mode='retained'):
        # An environment boundary is explicit, rather than inferred from 'lib'.
        if (directory / 'conda-meta').is_dir() or (directory / 'pyvenv.cfg').is_file(): mode = 'installed_environment'
        rel = directory.relative_to(root).as_posix()
        if rel == 'results/tool-audit/runtime/mamba-root/pkgs': mode = 'package_cache'
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda x: x.name):
                p = Path(entry.path)
                if p == archive or (directory == root and entry.name in excluded_root): continue
                if entry.is_dir(follow_symlinks=False):
                    # VCS data for third-party installations is reconstructible.
                    yield from descend(p, 'software_vcs' if entry.name == '.git' else mode)
                else:
                    yield p, mode
    yield from descend(root)


def clone(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with src.open('rb') as i, dest.open('xb') as o:
        fcntl.ioctl(o.fileno(), FICLONE, i.fileno())
    shutil.copystat(src, dest, follow_symlinks=False)


def capture_empty_directories(root, archive):
    rows=[]
    def visit(p):
        if p==archive or p.name in {'.git','.agents','.aws','.codex','.code'}:return
        if (p/'conda-meta').is_dir() or (p/'pyvenv.cfg').is_file() or p==root/'results/tool-audit/runtime/mamba-root/pkgs':return
        entries=list(os.scandir(p))
        if not entries:
            s=p.stat();rel=p.relative_to(root).as_posix();q=archive/'snapshot'/rel
            q.mkdir(parents=True,exist_ok=True);os.chmod(q,stat.S_IMODE(s.st_mode))
            rows.append({'path':rel,'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns})
        for e in entries:
            if e.is_dir(follow_symlinks=False):visit(Path(e.path))
    visit(root);dump(archive/'empty-directories.json',rows)
    return rows


def build(root, archive):
    archive.mkdir(parents=True, exist_ok=False)
    snapshot = archive / 'snapshot'; snapshot.mkdir()
    meta = archive / 'metadata'; meta.mkdir()
    start = time.time(); counts = collections.Counter(); sizes = collections.Counter(); errors = []
    inode_hash = {}; model_rows = []; test_rows = []; junit_rows = []; refs = set(); symlinks = []
    free = shutil.disk_usage(root).free
    for name, args in [('git-status.txt', ['git', 'status', '--porcelain=v1', '--untracked-files=all']),
                       ('git-head.txt', ['git', 'rev-parse', 'HEAD']),
                       ('git-diff.patch', ['git', 'diff', '--binary', 'HEAD']),
                       ('git-log.txt', ['git', 'log', '-15', '--format=%H %aI %s'])]:
        (meta / name).write_bytes(command(root, args))
    command(root, ['git', 'bundle', 'create', str(meta / 'repository.bundle'), '--all'])
    dump(meta / 'capture.json', {'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'original_root': str(root),
         'archive': str(archive), 'git_head': (meta / 'git-head.txt').read_text().strip(), 'free_before_bytes': free,
         'python': sys.version, 'excluded_root': ['.git (bundle and dirty diff retained)', '.agents', '.aws', '.codex', '.code', 'lazygit'],
         'scope': 'All other root files recursively; no directory symlinks followed; installed software/cache/VCS metadata inventoried, receipts and model weights retained',
         'consistency': 'per-file stat before/after clone and hash; not an atomic filesystem-wide snapshot',
         'reflink': 'required; independent copy-on-write inodes, never original hardlinks'})
    with gzip.open(archive / 'inventory.jsonl.gz', 'wt', encoding='utf-8', compresslevel=2) as inventory:
        for src, scope in walk(root, archive):
            rel = src.relative_to(root).as_posix()
            try:
                before = src.lstat(); kind = 'symlink' if stat.S_ISLNK(before.st_mode) else ('file' if stat.S_ISREG(before.st_mode) else 'special')
                tags = roles(rel)
                retained = scope == 'retained' or 'model_or_model_asset' in tags or 'environment_receipt' in tags
                if '__pycache__' in src.parts or src.suffix == '.pyc': retained = False; scope = 'python_cache'
                if kind == 'special': retained = False
                row = {'path': rel, 'kind': kind, 'scope': scope, 'roles': tags, 'bytes': before.st_size,
                       'mtime_ns': before.st_mtime_ns, 'mode': stat.S_IMODE(before.st_mode), 'retained': retained,
                       'original_dev': before.st_dev, 'original_inode': before.st_ino, 'original_nlink': before.st_nlink}
                dest = snapshot / rel
                if kind == 'symlink':
                    target = os.readlink(src); row['target'] = target
                    row['original_target_exists'] = src.exists()
                    row['target_absolute'] = os.path.isabs(target)
                    symlinks.append(dict(row))
                    if retained:
                        dest.parent.mkdir(parents=True, exist_ok=True); os.symlink(target, dest)
                elif retained and kind == 'file':
                    clone(src, dest)
                    key = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                    if key not in inode_hash: inode_hash[key] = sha(dest)
                    row['sha256'] = inode_hash[key]
                    after = src.lstat()
                    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                        raise RuntimeError('file changed during capture')
                    if any(t in tags for t in ['model_or_model_asset', 'sequence_data_or_index', 'dependency_or_data_lock', 'fixture_or_mock']): model_rows.append(row)
                    if 'test_entry_or_harness' in tags:
                        entry = {k: row[k] for k in ['path', 'roles', 'sha256', 'bytes']}
                        entry['definitions'] = []
                        text = dest.read_text(errors='replace')
                        if src.suffix == '.py':
                            try:
                                tree = ast.parse(text)
                                entry['definitions'] = [{'name': n.name, 'line': n.lineno} for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_')]
                            except SyntaxError as exc: entry['parse_error'] = str(exc)
                        entry['method'] = 'Python AST; nf-test/harness files indexed without counting lexical occurrences as executed cases'
                        test_rows.append(entry)
                    if src.suffix.lower() == '.xml' and before.st_size < 30_000_000:
                        try:
                            tree = ET.parse(dest).getroot()
                            if tree.tag in {'testsuite', 'testsuites'}:
                                for case in tree.iter('testcase'):
                                    status = 'error' if case.find('error') is not None else 'failed' if case.find('failure') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
                                    junit_rows.append({'report': rel, 'report_sha256': row['sha256'], 'suite': case.get('classname'), 'name': case.get('name'), 'status': status, 'time': case.get('time'), 'interpretation': 'raw historical JUnit; attempts may overlap; stub/native/scientific scope requires source report'})
                        except ET.ParseError: pass
                counts[('retained_' if retained else 'metadata_only_') + kind] += 1
                sizes['retained' if retained else 'metadata_only'] += before.st_size
                inventory.write(json.dumps(row, ensure_ascii=False) + '\n')
                if sum(counts.values()) % 100000 == 0:
                    inventory.flush(); print(json.dumps({'files_seen': sum(counts.values()), 'retained_bytes': sizes['retained'], 'elapsed_s': round(time.time()-start)}), flush=True)
            except Exception as exc:
                errors.append({'path': rel, 'error': str(exc)})
                print('CAPTURE_ERROR ' + rel + ': ' + str(exc), flush=True)
    empty_directories=capture_empty_directories(root,archive)
    dump(archive / 'assets.json', model_rows)
    dump(archive / 'test-entries.json', test_rows)
    dump(archive / 'junit-cases.json', junit_rows)
    dump(archive / 'symlinks.json', symlinks)
    dump(archive / 'capture-errors.json', errors)
    runs = snapshot / 'docs/tool-audit/runs.jsonl'
    run_rows = []; parse_errors = []
    if runs.exists():
        for line_no, line in enumerate(runs.read_text().splitlines(), 1):
            try:
                record = json.loads(line)
                run_rows.append({'line': line_no, 'record': record})
                def visit(value):
                    if isinstance(value, dict):
                        for v in value.values(): visit(v)
                    elif isinstance(value, list):
                        for v in value: visit(v)
                    elif isinstance(value, str):
                        p = value.removeprefix(str(root) + '/')
                        if p.startswith(('results/', 'tests/', 'docs/', 'bin/', 'modules/', 'subworkflows/', 'conf/', 'envs/', 'lib/')) and not any(c in p for c in '\n\t *|;'):
                            refs.add(p)
                visit(record)
            except Exception as exc: parse_errors.append({'line': line_no, 'error': str(exc)})
    dump(archive / 'historical-runs.json', run_rows)
    dump(archive / 'run-parse-errors.json', parse_errors)
    dump(archive / 'evidence-references.json', [{'path': p, 'original_exists': (root/p).exists(), 'snapshot_exists': (snapshot/p).exists(), 'note': 'literal path strings in runs.jsonl; commands/embedded prose require manual review'} for p in sorted(refs)])
    summary = {'capture_complete': not errors, 'file_counts': dict(counts), 'logical_bytes': dict(sizes),
               'test_entry_files': len(test_rows), 'python_test_definitions': sum(len(r['definitions']) for r in test_rows),
               'asset_files': len(model_rows), 'junit_cases_raw': len(junit_rows), 'junit_status_raw': dict(collections.Counter(r['status'] for r in junit_rows)),
               'historical_run_records': len(run_rows), 'run_parse_errors': len(parse_errors),
               'symlinks': len(symlinks), 'broken_original_symlinks': sum(not r['original_target_exists'] for r in symlinks),
               'absolute_symlinks': sum(r['target_absolute'] for r in symlinks), 'elapsed_seconds': round(time.time()-start, 2),
               'free_after_capture_bytes': shutil.disk_usage(root).free, 'errors': len(errors),'empty_directories':len(empty_directories)}
    dump(archive / 'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if errors: raise RuntimeError('Capture has errors; cleanup is forbidden')


def verify(archive, report_path=None):
    count = 0; failures = []; start = time.time()
    with gzip.open(archive / 'inventory.jsonl.gz', 'rt', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            if not row['retained']: continue
            p = archive / 'snapshot' / row['path']
            if row['kind'] == 'symlink':
                ok = p.is_symlink() and os.readlink(p) == row['target']
            else:
                ok = p.is_file() and not p.is_symlink() and p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
            count += 1
            if not ok: failures.append(row['path'])
            if count % 50000 == 0: print(json.dumps({'verified': count, 'elapsed_s': round(time.time()-start)}), flush=True)
    empty=archive/'empty-directories.json';empty_rows=json.loads(empty.read_text()) if empty.exists() else []
    for row in empty_rows:
        p=archive/'snapshot'/row['path']
        if not p.is_dir() or p.is_symlink():failures.append(row['path']+': empty directory missing')
    report = {'verified_entries': count, 'verified_empty_directories':len(empty_rows),'failures': failures, 'ok': not failures, 'elapsed_seconds': round(time.time()-start, 2),
              'verified_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    dump(report_path or archive / 'verification.json', report); print(json.dumps(report), flush=True)
    if failures: raise RuntimeError('Archive integrity failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'verify'])
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--verification-report',type=Path,help='write check result outside the sealed archive when desired')
    args = parser.parse_args(); root=args.root.resolve(); archive=args.archive.resolve()
    if args.action == 'build': build(root, archive)
    else: verify(archive,args.verification_report)


if __name__ == '__main__': main()
