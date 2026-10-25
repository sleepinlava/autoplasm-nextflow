#!/usr/bin/env python3
"""Main-entry gplas resource/platform controls; previews are parser controls only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve()
    base.mkdir(exist_ok=False)
    fixture = base / 'fixture'; fixture.mkdir()
    data = fixture / 'input.fastq'; data.write_text('@input\nACGT\n+\nIIII\n')
    sheet = fixture / 'samples.tsv'
    sheet.write_text('sample_id\tgroup\tread1\tread2\tlong_reads\tassembly\nS1\tA\t' + '\t'.join([str(data)] * 4) + '\n')
    options = {key: [] for key in ['polishing_tools', 'typing_tools', 'typing_optional_tools', 'host_prediction_tools',
               'mag_tools', 'host_linking_methods', 'host_linking_optional_methods', 'annotation_tools',
               'annotation_optional_tools', 'comparative_tools', 'comparative_optional_tools']}
    options.update(platform='illumina', short_read_assembler='metaspades', hybrid_assembler='hybridspades',
                   plasmid_binning_tools=['gplas2'], plasmid_detection_tools=['genomad'],
                   gplas_source=str(args.source.resolve()), genomad_db=str(fixture),
                   samplesheet=str(sheet), host_plasmid_linking=False)
    cases = [('missing-source', dict(options, gplas_source=None), 'an enabled tool requires --gplas_source', False)]
    for platform in ['ont', 'pacbio_hifi', 'assembly']:
        cases.append((platform, dict(options, platform=platform), 'gplas2 requires illumina/metaspades or hybrid/hybridspades', False))
    cases += [('illumina-megahit', dict(options, short_read_assembler='megahit'), 'gplas2 requires illumina/metaspades or hybrid/hybridspades', False),
              ('hybrid-operams', dict(options, platform='hybrid', hybrid_assembler='opera_ms'), 'gplas2 requires illumina/metaspades or hybrid/hybridspades', False),
              ('unsupported-source-layout', dict(options, gplas_source=str(fixture)), '--gplas_source missing fixed source file gplas/gplas.py', False),
              ('illumina-allowed-preview', options, '', True),
              ('hybrid-allowed-preview', dict(options, platform='hybrid'), '', True)]
    source_hash = hashlib.sha256((ROOT / 'main.nf').read_bytes()).hexdigest()

    def run(case):
        name, params, diagnostic, preview = case
        folder = base / name; folder.mkdir()
        params = dict(params, outdir=str(folder / 'out'))
        (folder / 'params.json').write_text(json.dumps(params, indent=2) + '\n')
        cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C',
               str(ROOT / 'results/tool-audit/20261020-main-p0/combined.config'), 'run', str(ROOT / 'main.nf'),
               '-params-file', str(folder / 'params.json'), '-work-dir', str(folder / 'work'),
               '-with-trace', str(folder / 'trace.tsv'), '-ansi-log', 'false'] + (['-preview'] if preview else [])
        result = subprocess.run(cmd, text=True, capture_output=True)
        (folder / 'stdout').write_text(result.stdout); (folder / 'stderr').write_text(result.stderr)
        tasks = list(csv.DictReader((folder / 'trace.tsv').open(), delimiter='\t')) if (folder / 'trace.tsv').exists() else []
        checks = {'expected_exit': (result.returncode == 0) if preview else (result.returncode != 0),
                  'diagnostic': preview or diagnostic in result.stdout + result.stderr,
                  'no_analysis_tasks': not tasks,
                  'no_task_commands': not list((folder / 'work').rglob('.command.sh'))}
        return {'case': name, 'preview_only': preview, 'command': cmd, 'exit_code': result.returncode,
                'diagnostic': diagnostic, 'checks': checks}

    with ThreadPoolExecutor(max_workers=2) as executor:
        rows = list(executor.map(run, cases))
    result = {'main_sha256': source_hash, 'source_unchanged': source_hash == hashlib.sha256((ROOT / 'main.nf').read_bytes()).hexdigest(),
              'scope': '7 main-entry rejections + 2 allowed parser previews, all zero tool tasks; no execution/biological support inferred from previews',
              'pass': all(all(row['checks'].values()) for row in rows), 'runs': rows}
    (base / 'run.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['pass'] and result['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
