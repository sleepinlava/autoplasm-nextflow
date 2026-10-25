#!/usr/bin/env python3
"""Original modules: real fastp1.3.6 outputs plus explicit IntegronFinder stubs."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_fastq(path):
    with gzip.open(path, 'rt') as stream:
        lines = stream.read().splitlines()
    assert len(lines) % 4 == 0, path
    assert all(lines[i].startswith('@') and lines[i+2] == '+' and
               len(lines[i+1]) == len(lines[i+3]) for i in range(0, len(lines), 4)), path
    return [(lines[i][1:], lines[i+1], lines[i+3]) for i in range(0, len(lines), 4)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--before-dir', type=Path, required=True)
    parser.add_argument('--fastp-prefix', type=Path, required=True)
    parser.add_argument('--phase', choices=['before', 'current'], required=True)
    args = parser.parse_args()
    base, before, prefix = args.work_dir.resolve(), args.before_dir.resolve(), args.fastp_prefix.resolve()
    base.mkdir(parents=True, exist_ok=False)
    version = subprocess.run([str(prefix/'bin/fastp'), '--version'], text=True, capture_output=True, check=True)
    assert (version.stdout+version.stderr).strip() == 'fastp 1.3.6'
    fixture = base / 'fixture'
    fixture.mkdir()
    rng = random.Random(201034)
    expected = {mate:[(f'read{i}/{mate}', ''.join(rng.choices('ACGT', k=100)), 'I'*100)
                     for i in range(12)] for mate in [1,2]}
    for name, records in [('r1',expected[1]), ('r2',expected[2]),
                          ('il',[record for pair in zip(expected[1],expected[2]) for record in pair])]:
        with gzip.open(fixture/f'{name}.fastq.gz', 'wt') as stream:
            for rid, dna, qual in records:
                stream.write(f'@{rid}\n{dna}\n+\n{qual}\n')
    fasta = fixture / 'sample.fna'
    fasta.write_text('>sample\nACGTACGT\n')
    shim = base / 'stub-version-observer'
    shim.mkdir()
    # No native IntegronFinder analysis is claimed. Only its stub body is tested.
    observer = shim / 'integron_finder'
    observer.write_text('#!/usr/bin/env bash\n[[ "$1" == --version ]] || exit 90\necho "integron_finder version 2.0.5"\n')
    observer.chmod(0o755)
    sources = ['modules/nf-core/fastp/main.nf','modules/nf-core/integronfinder/main.nf',
               'tests/nextflow/qc_output_contract.nf','tests/run_qc_output_contract.py']
    hashes = {name:sha(ROOT/name) for name in sources}
    before_hashes = {name:sha(before/name) for name in ['fastp.nf','integronfinder.nf']}
    runs = []
    cases = [('fastp',mode,stub,False) for stub in [False,True] for mode in ['se','pe','il']]
    cases += [('integronfinder','fasta',True,gbk) for gbk in [False,True]]
    for tool, mode, stub, gbk in cases:
        name = f'{tool}-{mode}-' + ('stub' if stub else 'native') + ('-gbk' if gbk else '')
        d = base/name
        d.mkdir()
        reads = [str(fixture/'r1.fastq.gz'),str(fixture/'r2.fastq.gz')] if mode == 'pe' else [str(fixture/('il.fastq.gz' if mode == 'il' else 'r1.fastq.gz'))]
        params = {'contract_tool':tool, 'input_mode':mode, 'reads':reads, 'fasta':str(fasta),
                  'observe_dir':str(d/'observed')}
        pf = d/'params.json'
        pf.write_text(json.dumps(params))
        fastp_args = '--disable_adapter_trimming --disable_trim_poly_g --disable_quality_filtering --disable_length_filtering'
        if mode == 'il':
            fastp_args += ' --interleaved_in'
        setup = 'export PATH='+shlex.quote(str(prefix/'bin'))+':'+shlex.quote(str(shim))+':"$PATH"'
        literal = "'" + setup.replace('\\', '\\\\').replace("'", "\\'") + "'"
        config = d/'native.config'
        config.write_text("process.executor='local'\nprocess.cpus=4\nprocess.memory='1 GB'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                          "trace.fields='task_id,hash,name,status,exit,workdir'\nprocess.beforeScript="+literal+"\n"
                          "process { withName: FASTP { ext.args="+repr(fastp_args)+" }\n"
                          "withName: INTEGRONFINDER { ext.args="+repr('--gbk' if gbk else '')+" } }\n")
        harness = ROOT/'tests/nextflow/qc_output_contract.nf'
        if args.phase == 'before':
            old = d/'old.nf'
            text = harness.read_text().replace("'../../modules/nf-core/fastp'", repr(str(before/'fastp.nf')))
            text = text.replace("'../../modules/nf-core/integronfinder'", repr(str(before/'integronfinder.nf')))
            old.write_text(text)
            harness = old
        cmd = [shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(harness),'-params-file',str(pf),
               '-work-dir',str(d/'work'),'-with-trace',str(d/'trace.tsv'),'-ansi-log','false']
        if stub:
            cmd += ['-stub-run']
        result = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
        (d/'console.log').write_text(result.stdout+result.stderr)
        assert (d/'trace.tsv').exists(), result.stdout+result.stderr
        with (d/'trace.tsv').open() as stream:
            tasks = list(csv.DictReader(stream, delimiter='\t'))
        assert len(tasks) == 1, tasks
        work = Path(tasks[0]['workdir'])
        failure = args.phase == 'before' and tool == 'integronfinder' and gbk
        assert (result.returncode != 0) == failure, result.stdout+result.stderr
        channel_file = d/'observed'/('reads-channel.json' if tool == 'fastp' else 'gbk-channel.json')
        emitted = json.loads(channel_file.read_text()) if channel_file.exists() else []
        if failure:
            assert tasks[0]['status'] == 'FAILED' and 'command not found' not in (work/'.command.err').read_text()
            assert 'No such file or directory' in (work/'.command.err').read_text()
        else:
            assert tasks[0]['status'] == 'COMPLETED'
            if tool == 'fastp':
                missing = args.phase == 'before' and mode in ['se','il']
                assert bool(emitted) != missing, emitted
                names = ['sample_R1.clean.fastq.gz','sample_R2.clean.fastq.gz'] if mode == 'pe' else ['sample.clean.fastq.gz']
                if not missing:
                    assert len(emitted) == 1 and emitted[0]['id'] == 'sample'
                    assert sorted(Path(p).name for p in emitted[0]['files']) == names
                if not stub:
                    actual_names = names if not missing else ['sample.fastp.fastq.gz']
                    actual = [record for name in actual_names for record in read_fastq(work/name)]
                    wanted = expected[1] + expected[2] if mode == 'pe' else ([r for pair in zip(expected[1],expected[2]) for r in pair] if mode == 'il' else expected[1])
                    assert actual == wanted, (name, actual[:2], wanted[:2])
                    report = json.loads((work/'sample.fastp.json').read_text())
                    assert report['summary']['before_filtering']['total_reads'] == len(wanted)
                    assert report['summary']['after_filtering']['total_reads'] == len(wanted)
                    for ext in ['html','log']:
                        assert (work/f'sample.fastp.{ext}').stat().st_size > 0
            else:
                assert bool(emitted) == gbk, emitted
                if gbk:
                    assert emitted[0]['id'] == 'sample' and Path(emitted[0]['files'][0]).name == 'sample.gbk'
        assert hashes == {name:sha(ROOT/name) for name in sources}
        assert before_hashes == {name:sha(before/name) for name in before_hashes}
        runs.append({'case':name,'command':cmd,'exit':result.returncode,'tasks':tasks,'emitted':emitted,
                     'expected_old_failure':failure})
        (base/'run.json').write_text(json.dumps({'pass':len(runs)==len(cases),'runs':runs,'source_sha256':hashes,
            'before_sha256':before_hashes,'fastp_version':'1.3.6','phase':args.phase,
            'limitations':['fastp real native controlled DNA/quality, not biological QC performance or container certification',
                           'IntegronFinder stub only; version command is explicit observer; no native annotation',
                           'Module contract only; no single-end or interleaved full pipeline support implied']},indent=2)+'\n')
        print('PASS',name,flush=True)


if __name__ == '__main__':
    main()
