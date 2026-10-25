#!/usr/bin/env python3
"""Filename and explicit threshold controls in four original statistics wrappers.

Only disposable fixtures may be overwritten by predecessor modules. The old
DESeq mutation control explicitly needs native1.52, allowed by the old Conda
constraint; fixed1.42 is used for the repaired production DESeq wrapper.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from run_deseq2_model import ROOT, generate, read, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--before-dir', type=Path, required=True)
    parser.add_argument('--deseq-prefix', type=Path, required=True)
    parser.add_argument('--legacy-rscript', type=Path, required=True)
    a = parser.parse_args()
    base, before = a.work_dir.resolve(), a.before_dir.resolve()
    prefix, legacy = a.deseq_prefix.resolve(), a.legacy_rscript.resolve()
    base.mkdir(parents=True, exist_ok=False)
    version = subprocess.run([str(legacy), '-e', 'cat(as.character(packageVersion("DESeq2")))'], capture_output=True, text=True, check=True).stdout.strip()
    assert version == '1.52.0', 'Old wrapper mutation control needs the recorded1.52 native stack, not the default1.42 image'
    sources = ['modules/cross_sample/deseq2.nf', 'modules/cross_sample/differential.nf',
               'modules/cross_sample/diversity.nf','modules/cross_sample/network_prepare.nf',
               'bin/diversity.R','bin/network_prepare.R',
               'bin/deseq2_plasmid.R', 'bin/differential_abundance.R', 'bin/statistics_input_contract.R',
               'tests/nextflow/statistics_input_names.nf', 'tests/run_statistics_input_names.py', 'tests/run_deseq2_model.py']
    hashes = {n: sha(ROOT / n) for n in sources}
    cases = [('before-deseq', True, 'deseq', False), ('before-internal', True, 'internal', False),
             ('before-diversity',True,'diversity',False),('before-network',True,'network',False),
             ('deseq-same-input-output-name', False, 'deseq', True),
             ('deseq-metadata-status-name', False, 'deseq', False),
             ('internal-same-input-output-name', False, 'internal', True),
             ('diversity-same-input-output-name',False,'diversity',True),
             ('network-same-input-output-name',False,'network',True),
             ('before-network-min0',True,'network',False),('network-min0',False,'network',False)]
    outputs = {'deseq':'differential_plasmids.tsv','internal':'differential_abundance.tsv',
               'diversity':'diversity_metrics.tsv','network':'fastspar_input.tsv'}
    programs = {'deseq':'deseq2_plasmid.R','internal':'differential_abundance.R',
                'diversity':'diversity.R','network':'network_prepare.R'}
    runs = []
    for name, old, tool, same in cases:
        d = base / name
        d.mkdir()
        fixture = d / 'fixture'
        ids, features = generate(fixture, 'positive')
        result_name = outputs[tool]
        (fixture / 'abundance').mkdir()
        (fixture / 'cohort').mkdir()
        zero_minimum = name.endswith('min0')
        ab = fixture / 'abundance' / ('counts.tsv' if zero_minimum else result_name)
        meta = fixture / 'cohort' / (result_name if same else 'deseq2_status.tsv' if not old else 'samples.tsv')
        table_name = 'plasmids.tsv' if tool in ['deseq','network'] else 'contigs.tsv'
        shutil.copyfile(fixture / table_name, ab)
        shutil.copyfile(fixture / 'samples.tsv', meta)
        inputs = {str(p): sha(p) for p in [ab, meta]}
        code = before / 'bin' if old else ROOT / 'bin'
        params = {'outdir': str(d / 'out'), 'publish_dir_mode': 'copy', 'min_group_replicates': 3,
                  'test_tool': tool, 'program': programs[tool],
                  'abundance': str(ab), 'metadata': str(meta), 'code_dir': str(code)}
        params['network_min_samples'] = 0 if zero_minimum else 20
        pf = d / 'params.json'
        pf.write_text(json.dumps(params))
        harness = ROOT / 'tests/nextflow/statistics_input_names.nf'
        if old:
            harness = d / 'old.nf'
            text = (ROOT / 'tests/nextflow/statistics_input_names.nf').read_text()
            for module in ['deseq2', 'differential','diversity','network_prepare']:
                text = text.replace("'../../modules/cross_sample/" + module + "'", repr(str(before / 'modules/cross_sample' / module)))
            harness.write_text(text)
        setup = 'export PATH=' + shlex.quote(str(legacy.parent)) + ':"$PATH"'
        if not old and tool == 'deseq':
            setup = 'export PATH=' + shlex.quote(str(prefix / 'bin')) + ':"$PATH"\nexport R_LIBS_USER=' + shlex.quote(str(prefix / 'lib/R/library')) + '\nexport R_LIBS_SITE=' + shlex.quote(str(prefix / 'lib/R/library'))
        literal = "'" + setup.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"
        config = d / 'native.config'
        config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\nprocess.beforeScript=" + literal + '\n')
        cmd = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(harness), '-params-file', str(pf),
               '-work-dir', str(d / 'work'), '-with-trace', str(d / 'trace.tsv'), '-ansi-log', 'false']
        result = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
        (d / 'console.log').write_text(result.stdout + result.stderr)
        tasks = read(d / 'trace.tsv')
        after = {str(p): sha(p) for p in [ab, meta]}
        failure = name=='network-min0'
        assert (result.returncode!=0)==failure and len(tasks)==1, result.stdout+result.stderr
        if failure:
            assert tasks[0]['status']=='FAILED' and inputs==after
            assert '--min-samples' in (Path(tasks[0]['workdir'])/'.command.err').read_text()
            assert not (d/'out/12_network/fastspar_input.tsv').exists()
        elif old and zero_minimum:
            assert tasks[0]['status']=='COMPLETED' and inputs==after
            state=json.loads((d/'out/12_network/network_status.json').read_text())
            assert state['min_samples']==20
        elif old:
            assert tasks[0]['status']=='COMPLETED'
            assert inputs[str(ab)] != after[str(ab)] and inputs[str(meta)] == after[str(meta)]
            assert set(read(ab)[0]) != set(read(fixture / table_name)[0])
        else:
            assert tasks[0]['status']=='COMPLETED'
            assert inputs == after
            output = d / ('out/12_network' if tool == 'network' else 'out/11_diversity')
            rows = read(output / result_name)
            if tool in ['deseq','internal']:
                key = 'plasmid_id' if tool == 'deseq' else 'contig_id'
                assert len(rows) == 100 and {r[key] for r in rows} == set(features)
            elif tool == 'diversity':
                assert len(rows)==24 and {r['sample_id'] for r in rows}==set(ids)
            else:
                assert len(rows)==100 and {r['#OTU ID'] for r in rows}==set(features)
                state=json.loads((output/'network_status.json').read_text())
                assert not state['eligible'] and state['reason']=='insufficient_samples'
            if tool == 'deseq':
                status = read(output / 'deseq2_status.tsv')
                assert {r['sample_id'] for r in status} == set(ids)
                assert {r['deseq2_version'] for r in status} == {'1.42.0'}
                assert {r['model_fitted'] for r in status} == {'TRUE'}
        assert hashes == {n: sha(ROOT / n) for n in sources}
        runs.append({'case': name, 'command': cmd, 'exit': result.returncode, 'tasks': tasks,
                     'before_sha256': inputs, 'after_sha256': after, 'source_mutation_expected': old and not zero_minimum})
        (base / 'run.json').write_text(json.dumps({'pass': len(runs) == len(cases), 'expected_cases': len(cases),
            'runs': runs, 'source_sha256': hashes, 'legacy_DESeq2': version,
            'limitations': ['Only private fixtures overwritten; default CROSS_SAMPLE canonical names were not colliding',
                            'Legacy1.52 stack proves predecessor overwrite, not fixed1.42 biological/model validity',
                            'Current DESeq uses native fixed1.42; internal uses native R/data.table; no image/framework/scientific accuracy certification']}, indent=2) + '\n')
        print('PASS', name, 'input overwritten' if old and not zero_minimum else 'inputs unchanged', flush=True)


if __name__ == '__main__':
    main()
