#!/usr/bin/env python3
"""Native optional FragGeneScan resource/cache controls, full SemiBin fixture."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from module_harness import run_session_uuid
from run_semibin_states import dna

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(base, prefix, fgs_prefix, fixture):
    base.mkdir(parents=True, exist_ok=False)
    tool = base / 'private-tools'
    tool.mkdir()
    shutil.copy2(fgs_prefix / 'bin/FragGeneScan', tool / 'FragGeneScan')
    shutil.copytree(fgs_prefix / 'bin/train', tool / 'train')
    watched = [tool / 'FragGeneScan', *sorted((tool / 'train').iterdir())]
    originals = {p: (p.read_bytes(), p.stat()) for p in watched}
    for p in watched:
        original = fgs_prefix / 'bin' / p.relative_to(tool)
        assert sha(p) == sha(original)
        assert (p.stat().st_dev, p.stat().st_ino) != (original.stat().st_dev, original.stat().st_ino)
    params = dict(fasta=str(fixture / 'input.fasta'), bam=str(fixture / 'input.sorted.bam'))
    (base / 'params.json').write_text(json.dumps(params))
    config = base / 'config'
    config.write_text("process { executor='local'; cpus=2; memory='2 GB'; errorStrategy='terminate'; maxRetries=0; withName: 'SEMIBIN|SEMIBIN_RESOURCE_PROBE' { ext.args2='--random-seed 0 --orf-finder fraggenescan' } }\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    env = dict(os.environ, PATH=str(tool) + ':' + str(prefix / 'bin') + ':' + os.environ['PATH'],
               OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
    source = dna(fixture / 'input.fasta')
    assert len(source) == 40 and sum(map(len, source.values())) == 800000
    sources = ['tests/run_semibin_fgs_runtime.py', 'bin/semibin_runtime_resources.py',
               'lib/semibin_runtime.nf', 'tests/nextflow/semibin_runtime_native.nf',
               'modules/nf-core/semibin/singleeasybin/main.nf', 'bin/semibin_output_state.py']
    before = {p: sha(ROOT / p) for p in sources}
    # Native original executable provides a software-output baseline, not
    # biological truth. All phases retain complete/w0 and the full input.
    golden = base / 'original-fgs'
    golden.mkdir()
    golden_cmd = [str(fgs_prefix / 'bin/FragGeneScan'), '-s', params['fasta'],
                  '-o', str(golden / 'contigs'), '-w', '0', '-t', 'complete', '-p', '2']
    baseline = subprocess.run(golden_cmd, capture_output=True, text=True, timeout=120)
    (golden / 'stdout').write_text(baseline.stdout)
    (golden / 'stderr').write_text(baseline.stderr)
    assert baseline.returncode == 0
    suffixes = ['faa', 'ffn', 'gff']
    assert all((golden / ('contigs.' + suffix)).stat().st_size > 0 for suffix in suffixes)
    (golden / 'command.json').write_text(json.dumps(golden_cmd))
    runs = []
    session = None

    def execute(name, expected):
        nonlocal session
        case = base / name
        case.mkdir()
        trace = case / 'trace.tsv'
        cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config),
               'run', str(ROOT / 'tests/nextflow/semibin_runtime_native.nf'), '-params-file', str(base / 'params.json'),
               '-work-dir', str(base / 'work'), '-with-trace', str(trace), '-ansi-log', 'false']
        cmd += ['-name', 'semibin_fgs_runtime'] if session is None else ['-resume', session]
        result = subprocess.run(cmd, cwd=base, env=env, text=True, capture_output=True, timeout=900)
        (case / 'stdout').write_text(result.stdout)
        (case / 'stderr').write_text(result.stderr)
        tasks = list(csv.DictReader(trace.open(), delimiter='\t')) if trace.exists() else []
        record = dict(case=name, command=cmd, exit_code=result.returncode, tasks=tasks,
                      resource_sha256={str(p.relative_to(tool)): sha(p) if p.exists() else None for p in watched})
        runs.append(record)
        (base / 'progress.json').write_text(json.dumps(runs, indent=2) + '\n')
        if expected == 'PROBE_FAILED':
            assert result.returncode != 0 and len(tasks) == 1 and tasks[0]['status'] == 'FAILED', record
            assert tasks[0]['name'].startswith('SEMIBIN_RESOURCE_PROBE'), record
            assert 'Missing selected FragGeneScan training file' in (Path(tasks[0]['workdir']) / '.command.log').read_text()
            record['no_consumer_submitted'] = True
        else:
            assert result.returncode == 0 and len(tasks) == 2, record
            probe = next(t for t in tasks if t['name'].startswith('SEMIBIN_RESOURCE_PROBE'))
            task = next(t for t in tasks if t['name'].startswith('SEMIBIN ('))
            assert probe['status'] == 'COMPLETED' and task['status'] == expected, record
            identity_path = Path(probe['workdir']) / 'semibin_runtime_identity.json'
            identity = json.loads(identity_path.read_text())
            fgs = identity['resources']['fraggenescan']
            assert fgs['selected_model'] == 'complete' and fgs['whole_genome'] == 0
            assert fgs['invoked_binary'] == str(tool / 'FragGeneScan')
            assert fgs['training_directory'] == str(tool / 'train')
            assert fgs['binary'][0]['sha256'] == sha(tool / 'FragGeneScan')
            record.update(consumer_hash=task['hash'], identity_sha256=sha(identity_path))
            if expected == 'COMPLETED':
                out = Path(task['workdir']) / 'sample'
                log = (Path(task['workdir']) / '.command.log').read_text()
                assert '15/15' in log and 'fraggenescan' in log.lower(), log[-2000:]
                state = json.loads((out / 'binning_status.json').read_text())
                bins = list((out / 'output_bins').glob('*.fa.gz'))
                assert bins and state['state'] == 'bins_ready' and state['bin_count'] == len(bins)
                seen = set()
                for path in bins:
                    seqs = dna(path)
                    assert seqs and not seen.intersection(seqs)
                    assert all(source[k] == seq for k, seq in seqs.items())
                    seen.update(seqs)
                assert (out / 'model.pt').is_file()
                # Upstream intentionally deletes temporary marker output.
                # Exercise its real ORF adapter on the complete original input.
                raw = case / 'native-orfs'
                raw.mkdir()
                adapter_cmd = [str(prefix / 'bin/python'), '-c',
                               'from SemiBin.orffinding import run_fraggenescan; import sys; run_fraggenescan(sys.argv[1], 2, sys.argv[2])',
                               params['fasta'], str(raw)]
                native_orfs = subprocess.run(adapter_cmd, env=env, text=True, capture_output=True, timeout=120)
                (raw / 'stdout').write_text(native_orfs.stdout)
                (raw / 'stderr').write_text(native_orfs.stderr)
                assert native_orfs.returncode == 0
                for suffix in suffixes:
                    assert (raw / ('contigs.faa.' + suffix)).read_bytes() == (golden / ('contigs.' + suffix)).read_bytes(), suffix
                record.update(native_ORF_adapter_command=adapter_cmd,
                              full_FGS_faa_ffn_gff_equal_original=True,
                              FGS_output_sha256={suffix: sha(raw / ('contigs.faa.' + suffix)) for suffix in suffixes})
                record.update(independent_bin_DNA_and_state_checks=True, bin_count=len(bins), binned_contigs=len(seen))
        if session is None:
            session = run_session_uuid('semibin_fgs_runtime', base)
        print(name, expected, flush=True)

    def restore(p):
        data, st = originals[p]
        p.write_bytes(data)
        p.chmod(st.st_mode & 0o777)
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))

    def mutate(p, data):
        original, st = originals[p]
        assert len(data) == len(original)
        p.write_bytes(data)
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        assert p.stat().st_size == st.st_size and p.stat().st_mtime_ns == st.st_mtime_ns

    try:
        execute('cold', 'COMPLETED')
        execute('unchanged', 'CACHED')
        for name in ['complete', 'gene']:
            p = tool / 'train' / name
            original = originals[p][0]
            # Whitespace-delimited numeric tokens remain exactly unchanged.
            i = next(i for i, c in enumerate(original) if c in (9, 32))
            change = bytearray(original)
            change[i] = 32 if original[i] == 9 else 9
            assert original.split() == bytes(change).split()
            mutate(p, bytes(change))
            execute(name + '-whitespace-change', 'COMPLETED')
            restore(p)
            execute(name + '-restored', 'CACHED')
        binary = tool / 'FragGeneScan'
        sections = subprocess.check_output(['readelf', '-SW', str(binary)], text=True)
        (base / 'binary-sections.txt').write_text(sections)
        match = re.search(r'\.comment\s+PROGBITS\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+\S+\s+(\S+)', sections)
        assert match and 'A' not in match[3]
        offset, size = int(match[1], 16), int(match[2], 16)
        changed = bytearray(originals[binary][0])
        i = changed.index(b'GCC:', offset, offset + size) + 2
        changed[i] = ord('D')
        mutate(binary, bytes(changed))
        execute('binary-comment-change', 'COMPLETED')
        restore(binary)
        execute('binary-restored', 'CACHED')
        complete = tool / 'train/complete'
        complete.unlink()
        execute('missing-selected-model', 'PROBE_FAILED')
    finally:
        for p in watched:
            restore(p)
    execute('all-restored', 'CACHED')
    cached = [r['consumer_hash'] for r in runs if r.get('consumer_hash') and r['case'] in
              ['cold', 'unchanged', 'complete-restored', 'gene-restored', 'binary-restored', 'all-restored']]
    assert len(set(cached)) == 1
    for p in watched:
        original = fgs_prefix / 'bin' / p.relative_to(tool)
        assert sha(p) == sha(original)
        assert (p.stat().st_mode & 0o777) == (original.stat().st_mode & 0o777)
    assert before == {p: sha(ROOT / p) for p in sources}
    receipt = dict(pass_checks=True, runs=runs, session_uuid=session, source_sha256=before,
                   source_unchanged=True, private_resources_restored=True,
                   original_resource_sha256={str(p.relative_to(tool)): sha(p) for p in watched},
                   fixture_sha256={p: sha(fixture / p) for p in ['input.fasta', 'input.sorted.bam']},
                   scope='Actual production2.4.1 optional FragGeneScan1.32 complete/w0 branch; full original40contig800000bp fixture,15epochs/seed0/CPU. Same-stat numerical-token-preserving model and nonallocated binary comment mutations; independent bin DNA/state, not accuracy/full environment/OCI/provider certification.')
    (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS: optional FragGeneScan native resources/cache', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--fgs-prefix', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    args = parser.parse_args()
    run(args.out.resolve(), args.prefix.resolve(), args.fgs_prefix.resolve(), args.fixture.resolve())
