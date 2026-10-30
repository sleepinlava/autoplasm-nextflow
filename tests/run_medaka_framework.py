#!/usr/bin/env python3
"""Execute actual native/stub Medaka nf-test cases using the full ONT sample."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-root', type=Path, required=True)
    parser.add_argument('--native-reference', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assembly', type=Path, help='Optional complete reviewed gzip/BGZF copy of the same draft')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=False)
    native = args.native_reference.resolve()
    result = json.loads((native / 'run.json').read_text())
    assert result['pass_native_computation_checks']
    expected = native / 'native/consensus.fasta'
    assert sha(expected) == result['consensus_fasta_sha256']
    fixture = args.fixture_root.resolve()
    reads = fixture / 'sample_1_1/sample_1_1.filtered.fastq.gz'
    assembly = args.assembly.resolve() if args.assembly else native / 'published-same-sample-draft.fasta'
    review = json.loads((native / 'input-review.json').read_text())
    assert sha(reads) == review['reads_sha256']
    import gzip
    with assembly.open('rb') as stream:
        compressed = stream.read(2) == b'\x1f\x8b'
    draft_bytes = gzip.decompress(assembly.read_bytes()) if compressed else assembly.read_bytes()
    assert hashlib.sha256(draft_bytes).hexdigest() == review['draft_sha256']
    prefix = args.prefix.resolve()
    stage = Path(tempfile.mkdtemp(prefix='autoplasm-medaka-real-nft-'))
    sources = ['modules/nf-core/medaka/' + p for p in ['main.nf', 'environment.yml', 'tests/main.nf.test', 'tests/main.nf.test.snap']]
    sources += ['tests/run_medaka_framework.py']
    sources += ['lib/medaka_runtime.nf', 'tests/nextflow/medaka_runtime_resources.nf']
    helper_names = ['medaka_runtime_resources.py','medaka_model_resources.py',
                    'medaka_model_selection.py','medaka_index_resources.py']
    sources += ['bin/' + name for name in helper_names]
    before = {p: sha(root / p) for p in sources}
    for path in sources:
        dest = stage / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, dest)
        assert sha(dest) == before[path] and dest.stat().st_mode == (root / path).stat().st_mode
    (base / 'bin').mkdir()
    shutil.copy2(root / 'results/tool-audit/20261026-plasmidfinder-runtime/nextflow-no-log', base / 'bin/nextflow')
    params = {'medaka_bacterial_reads': str(reads), 'medaka_bacterial_assembly': str(assembly), 'medaka_bacterial_expected_fasta': str(expected)}
    # Nextflow config params are not nf-test assertion-context params. Load the
    # same reviewed paths in setup, before expensive computation can start.
    text = ''.join('params.' + key + '=' + json.dumps(value) + '\n' for key, value in params.items())
    text += "process.executor='local'\nprocess.cpus=4\nprocess.memory='10 GB'\nprocess.maxForks=1\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
    (base / 'native.config').write_text(text)
    (base / 'nf-test.config').write_text("config { testsDir='modules/nf-core/medaka'; workDir='" + str(base / 'work') + "'; configFile='" + str(base / 'native.config') + "'; profile='' }\n")
    java = '/home/sleepinlava/.local/share/mise/installs/java/21.0.12+101.0.LTS/bin/java'
    command = [java, '-jar', str(root / 'results/tool-audit/runtime/nf-test-0.9.5/nf-test.jar'), 'test', '--ci', 'modules/nf-core/medaka/tests/main.nf.test', '--config', str(base / 'nf-test.config'), '--junitxml', str(base / 'junit.xml'), '--log', str(base / 'framework.log')]
    (base / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    env = dict(os.environ, PATH=str(base / 'bin') + ':' + str(prefix / 'bin') + ':' + os.environ['PATH'], JAVA_HOME=str(Path(java).parent.parent), PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', CUDA_VISIBLE_DEVICES='', MEDAKA_TEST_PARAMS=str(base / 'fixture-params.json'))
    bootstrap = [str(base / 'bin/nextflow'), '-C', str(base / 'native.config'),
                 '-log', str(base / 'probe-nextflow.log'), 'run',
                 str(stage / 'tests/nextflow/medaka_runtime_resources.nf'),
                 '--medaka_reads', str(reads), '--medaka_assembly', str(assembly),
                 '--probe_only', 'true', '-work-dir', str(base / 'probe-work'),
                 '-with-trace', str(base / 'probe-trace.tsv')]
    (base / 'probe-command.json').write_text(json.dumps(bootstrap, indent=2) + '\n')
    with (base / 'probe-stdout').open('w') as stdout, (base / 'probe-stderr').open('w') as stderr:
        probe = subprocess.run(bootstrap, cwd=base, env=env, stdout=stdout, stderr=stderr)
    (base / 'probe-exit.json').write_text(json.dumps({'returncode': probe.returncode}) + '\n')
    assert probe.returncode == 0, 'Actual resource probe failed before nf-test'
    receipts = list((base / 'probe-work').glob('*/*/medaka_runtime_identity.json'))
    assert len(receipts) == 1
    params['medaka_runtime_receipt'] = str(receipts[0])
    params['medaka_runtime_helpers'] = [str(stage / 'bin' / name) for name in helper_names]
    (base / 'fixture-params.json').write_text(json.dumps(params, indent=2) + '\n')
    with (base / 'stdout').open('w') as stdout, (base / 'stderr').open('w') as stderr:
        proc = subprocess.run(command, cwd=stage, env=env, stdout=stdout, stderr=stderr)
    report = {'command': command, 'returncode': proc.returncode, 'source_sha256': before, 'source_copy': str(stage), 'source_unchanged': before == {p: sha(root / p) for p in sources}, 'scope': 'Actual nf-test0.9.5 native full published ONT sample+separate stub. Full FASTA software oracle is original native CLI on the same already-polished draft, not independent biological truth. CI mode/no snapshots updated. No production resource/cache gate, complete platform/OCI or scientific error-rate benchmark claim.'}
    (base / 'run.json').write_text(json.dumps(report, indent=2) + '\n')
    assert proc.returncode == 0 and report['source_unchanged']
    tree = ET.parse(base / 'junit.xml')
    assert len(tree.findall('.//testcase')) == 2 and not tree.findall('.//failure') and not tree.findall('.//error')
    assert before == {p: sha(stage / p) for p in sources}, 'Snapshots or staged source changed'
    report.update(pass_native_and_stub_framework_checks=True, actual_testcases=2, native_cases=1, stub_cases=1)
    (base / 'run.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed_actual_testcases': 2, 'native': 1, 'stub': 1, 'output': str(base)}))


if __name__ == '__main__':
    main()
