#!/usr/bin/env python3
"""Actual CLI controls for standalone selection identity; no polishing."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    helper = root / 'bin/medaka_model_selection.py'
    import medaka.models as models
    import medaka.options as options
    stores = lambda: {str(s): {str(p.relative_to(s)): sha(p) for p in sorted(Path(s).rglob('*')) if p.is_file()} for s in options.model_stores}
    before = stores()
    assembly = out / 'control.fa'
    assembly.write_text('>metadata_control_only\nN\n')
    reads = out / 'tagged.fastq'
    reads.write_text('@control RG:Z:run_dna_r10.4.1_e8.2_400bps_sup@v5.2.0_barcode01\nN\n+\n!\n')
    no_meta = out / 'no-metadata.fastq'
    no_meta.write_text('@control\nN\n+\n!\n')
    old = out / 'old.fastq'
    old.write_text('@control model_version_id=dna_r9.4.1_e8_sup@v3.3\nN\n+\n!\n')
    sup = Path(models.resolve_model('r1041_e82_400bps_sup_v5.2.0'))
    hac = Path(models.resolve_model('r1041_e82_400bps_hac_v6.0.0'))
    runs = []

    def run(name, input_reads=reads, extra=(), expected=0, expect=None):
        target = out / f'{name}.json'
        cmd = [sys.executable, str(helper), '--reads', str(input_reads), '--assembly', str(assembly), '--output', str(target)]
        if expect:
            cmd += ['--expect', str(expect)]
        cmd += ['--', *extra]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=300,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2'))
        (out / f'{name}.stdout').write_text(proc.stdout)
        (out / f'{name}.stderr').write_text(proc.stderr)
        (out / f'{name}.command.json').write_text(json.dumps(cmd, indent=2) + '\n')
        assert proc.returncode == expected, (name, proc.returncode, proc.stderr)
        assert target.exists() == (expected == 0), name
        diagnostics = json.loads(target.with_suffix('.json.diagnostics.json').read_text())
        result = json.loads(target.read_text()) if target.exists() else None
        if result:
            assert result['scientific_readiness_certified'] is False and result['production_gate'] is False
        runs.append({'name': name, 'returncode': proc.returncode, 'diagnostics': diagnostics, 'observation': str(target) if result else None})
        print(name + ': expected exit' + str(expected), flush=True)
        return result, diagnostics

    auto, _ = run('auto')
    assert auto['selected_model']['resolved_path'] == str(sup.resolve())
    assert auto['selected_model']['sha256'] == sha(sup)
    fallback, _ = run('fallback', no_meta)
    assert fallback['selected_model'] == auto['selected_model']
    assert fallback['original_bash_state']['MODEL'] == 'r1041_e82_400bps_sup_v5.2.0'
    explicit, _ = run('explicit-bacteria', extra=['--bacteria', '-m', str(hac), '-b', '12', '-q', '-M', '7', '-g'])
    assert explicit['selected_model']['resolved_path'] == str(hac.resolve())
    state = explicit['original_bash_state']
    assert (state['BACTERIA'], state['BATCH_SIZE'], state['QUALITIES'], state['MIN_MAPQ'], state['NOFILLGAPS']) == ('_bacteria', '12', 'true', '7', 'true')
    _, bacteria = run('unprepared-bacteria', extra=['--bacteria'], expected=2)
    assert bacteria['returncode'] == 1 and len(bacteria['download_attempts_refused']) == 1
    _, hidden = run('hidden-fallback', old, expected=2)
    assert hidden['returncode'] == 0 and len(hidden['download_attempts_refused']) == 1
    assert 'will use default' in hidden['stdout']

    copy = out / 'private-model.tar.gz'
    shutil.copyfile(sup, copy)
    base, _ = run('private-baseline', extra=['-m', str(copy)])
    old_stat = copy.stat()
    original = copy.read_bytes()
    mutated = bytearray(original)
    mutated[-1] ^= 1
    copy.write_bytes(mutated)
    os.utime(copy, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    assert copy.stat().st_size == old_stat.st_size and copy.stat().st_mtime_ns == old_stat.st_mtime_ns
    changed, _ = run('private-changed', extra=['-m', str(copy)])
    assert changed['selected_model']['sha256'] != base['selected_model']['sha256']
    run('expected-rejects-change', extra=['-m', str(copy)], expected=2, expect=out / 'private-baseline.json')
    copy.write_bytes(original)
    os.utime(copy, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    restored, _ = run('expected-restored', extra=['-m', str(copy)], expect=out / 'private-baseline.json')
    assert restored == base
    # Explicit observer: only the parent resolver sees an empty store; the
    # native child still sees the actual installation. This exercises a late
    # model loss/refusal boundary, not a real package mutation or science run.
    spec = importlib.util.spec_from_file_location('medaka_selection_candidate', helper)
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)
    diagnostics = {}
    with patch.object(options, 'model_stores', (out / 'empty-observer-store',)):
        try:
            observer.select(no_meta, assembly, diagnostics=diagnostics)
        except observer.SelectionRefused as error:
            assert 'cannot be resolved without preparation' in str(error)
        else:
            raise AssertionError('Late missing default model was not refused')
    assert diagnostics['returncode'] == 0
    assert len(diagnostics['download_attempts_refused']) == 1
    assert diagnostics['download_attempts_refused'][0]['phase'] == 'final-model-resolution'
    (out / 'late-resolution-observer.json').write_text(json.dumps(diagnostics, indent=2) + '\n')
    assert before == stores(), 'Native model stores changed'
    report = {'pass_bounded_checks': True, 'formal_acceptance': False, 'scope': '9 actual standalone CLI observations/refusals plus1 explicitly injected late-resolution observer; metadata controls only, no inference/native polishing/production/cache execution', 'source_sha256': {str(helper.relative_to(root)): sha(helper), str(Path(__file__).resolve().relative_to(root)): sha(__file__)}, 'runs': runs, 'late_resolution_observers': 1, 'model_stores_unchanged': True, 'private_same_size_mtime_mutation_and_restore': True, 'full_polishing_runs': 0}
    (out / 'run.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'cases': len(runs), 'full_polishing': 0, 'output': str(out)}))


if __name__ == '__main__':
    main()
