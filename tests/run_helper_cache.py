#!/usr/bin/env python3
"""Exercise the actual node adapter cache with an equal-size/mtime helper edit."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve(); base.mkdir(exist_ok=False)
    project = base / 'project'
    (project / 'modules/binning').mkdir(parents=True); (project / 'bin').mkdir()
    names = ['modules/binning/gplas_inputs.nf', 'bin/gplas_inputs.py']
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
    for name in names:
        shutil.copy2(ROOT / name, project / name)
    graph = project / 'input.gfa'; graph.write_text('S\t1\t' + 'ACGT' * 300 + '\tKC:i:4000\n')
    (project / 'main.nf').write_text('''include { GPLAS2_NODES } from './modules/binning/gplas_inputs'
workflow {
    GPLAS2_NODES(Channel.value(tuple([id:'nodes',gplas_original_meta:[id:'sample']],file("${projectDir}/input.gfa"))),
        Channel.value(file("${projectDir}/bin/gplas_inputs.py",checkIfExists:true)))
}
''')
    config = base / 'config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='256 MB'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\nparams.publish_dir_mode='copy'\nparams.outdir='" + str(base / 'out') + "'\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    helper = project / 'bin/gplas_inputs.py'; original = helper.read_bytes(); stamp = helper.stat()
    changed = original.replace(b"'nodes_ready'", b"'NODES_READY'")
    assert len(original) == len(changed) and original != changed
    session = None; runs = []; name = 'helper_' + uuid.uuid4().hex[:16]
    try:
        for phase in ['cold', 'unchanged', 'changed', 'restored']:
            helper.write_bytes(changed if phase == 'changed' else original)
            os.utime(helper, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            assert helper.stat().st_mtime_ns == stamp.st_mtime_ns
            trace = base / (phase + '.trace.tsv')
            cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config), 'run',
                   str(project / 'main.nf'), '-work-dir', str(base / 'work'), '-with-trace', str(trace), '-ansi-log', 'false']
            cmd += ['-name', name] if phase == 'cold' else ['-resume', session]
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=180)
            (base / (phase + '.stdout')).write_text(result.stdout); (base / (phase + '.stderr')).write_text(result.stderr)
            tasks = list(csv.DictReader(trace.open(), delimiter='\t')) if trace.exists() else []
            assert result.returncode == 0 and len(tasks) == 1, (phase, result.stderr)
            expected = 'COMPLETED' if phase in ['cold', 'changed'] else 'CACHED'
            assert tasks[0]['status'] == expected, (phase, tasks)
            state = json.loads((Path(tasks[0]['workdir']) / 'nodes.gplas_nodes.json').read_text())['state']
            assert state == ('NODES_READY' if phase == 'changed' else 'nodes_ready'), (phase, state)
            if phase == 'cold':
                history = [row.split('\t') for row in (ROOT / '.nextflow/history').read_text().splitlines()]
                matching = [row for row in history if len(row) > 5 and row[2] == name]
                assert len(matching) == 1
                session = str(uuid.UUID(matching[0][5]))
            runs.append(dict(phase=phase, command=cmd, exit_code=result.returncode, tasks=tasks, state=state))
            (base / 'progress.json').write_text(json.dumps(runs, indent=2) + '\n')
    finally:
        helper.write_bytes(original); os.utime(helper, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    record = dict(source_sha256=hashes, source_unchanged=hashes == {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names},
                  original_helper_sha256=hashlib.sha256(original).hexdigest(), changed_helper_sha256=hashlib.sha256(changed).hexdigest(),
                  bytes=len(original), mtime_ns=stamp.st_mtime_ns, session_uuid=session, runs=runs,
                  scope='Actual current copied production adapter, explicit deep helper input, native Python; same size/mtime controlled metadata-string mutation in private copy, no classifier or accuracy claim')
    record['pass'] = record['source_unchanged']
    (base / 'run.json').write_text(json.dumps(record, indent=2) + '\n')
    return 0 if record['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
