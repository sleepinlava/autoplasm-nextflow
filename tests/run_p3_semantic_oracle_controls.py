#!/usr/bin/env python3
"""Counterfactual checks against copies of actual completed P3 products."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import traceback

from check_longread_native import check as longread_check
from check_metabat2_native import check as metabat_check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['data', 'control-dir', 'metabat-products', 'longread-products', 'work-dir']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=False)
    records = []
    fixture = args.data / 'data/genomics/prokaryotes/metagenome/binning/multisample'
    control = args.control_dir
    original = [p for root in [args.metabat_products, args.longread_products] for p in root.rglob('*') if p.is_file()]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in original}

    def evaluate(name, expected, callback):
        try:
            callback()
            actual, error = True, None
        except AssertionError as exc:
            actual = False
            frame = traceback.extract_tb(exc.__traceback__)[-1]
            error = {'message': str(exc), 'file': frame.filename, 'line': frame.lineno}
        assert actual == expected, (name, actual, error)
        records.append({'case': name, 'expected_pass': expected, 'actual_pass': actual, 'assertion': error})

    evaluate('actual-metabat-products', True, lambda: metabat_check(fixture, args.metabat_products, 'upstream-nonempty'))
    for name in ['drop-bin', 'changed-bin-DNA', 'wrong-membership-partition', 'nonfinite-depth', 'arbitrary-label-permutation']:
        folder = args.work_dir / name
        shutil.copytree(args.metabat_products, folder)
        if name in ['drop-bin', 'changed-bin-DNA']:
            path = sorted(folder.glob('*.fa.gz'))[0]
            if name == 'drop-bin':
                path.unlink()
            else:
                with gzip.open(path, 'rt') as stream:
                    lines = stream.read().splitlines()
                index = next(i for i, line in enumerate(lines) if line and not line.startswith('>'))
                lines[index] = ('C' if lines[index][0] != 'C' else 'A') + lines[index][1:]
                with gzip.open(path, 'wt') as stream:
                    stream.write('\n'.join(lines) + '\n')
        elif name == 'nonfinite-depth':
            path = folder / 'depth/binning_s1.txt.gz'
            with gzip.open(path, 'rt') as stream:
                lines = stream.read().splitlines()
            cells = lines[1].split('\t'); cells[2] = 'NaN'; lines[1] = '\t'.join(cells)
            with gzip.open(path, 'wt') as stream:
                stream.write('\n'.join(lines) + '\n')
        else:
            path = folder / 'binning_s1.tsv.gz'
            with gzip.open(path, 'rt') as stream:
                rows = [line.rstrip().split('\t') for line in stream]
            if name == 'wrong-membership-partition':
                first = next(row for row in rows if row[1] != '0')
                second = next(row for row in rows if row[1] not in ['0', first[1]])
                second[1] = first[1]
            else:
                for row in rows:
                    if row[1] != '0': row[1] = str(int(row[1]) + 10000)
            with gzip.open(path, 'wt') as stream:
                stream.write(''.join('\t'.join(row) + '\n' for row in rows))
        evaluate(name, name == 'arbitrary-label-permutation', lambda folder=folder: metabat_check(fixture, folder, 'upstream-nonempty'))

    def long_check(folder):
        return longread_check(control / 'minigut.fasta', folder / 'test_inputs/longread/plasmid_contigs.fasta',
                              control / 'test_data/minigut_reads.fastq.gz', folder / 'test_inputs/longread/minigut_ont.sam.gz',
                              folder / '07_host_prediction/linking/longread/minigut_ont.longread_bridge_links.tsv',
                              'minigut_ont', control / 'control.json')

    evaluate('actual-known-longread-positive', True, lambda: long_check(args.longread_products))
    for name in ['header-only-links', 'wrong-score', 'wrong-sample', 'wrong-SAM-reference', 'changed-partition-DNA']:
        folder = args.work_dir / name
        shutil.copytree(args.longread_products, folder)
        path = folder / '07_host_prediction/linking/longread/minigut_ont.longread_bridge_links.tsv'
        lines = path.read_text().splitlines()
        if name == 'header-only-links':
            path.write_text(lines[0] + '\n')
        elif name in ['wrong-score', 'wrong-sample']:
            cells = lines[1].split('\t'); cells[4 if name == 'wrong-score' else 2] = '3' if name == 'wrong-score' else 'foreign_sample'
            lines[1] = '\t'.join(cells); path.write_text('\n'.join(lines) + '\n')
        elif name == 'wrong-SAM-reference':
            path = folder / 'test_inputs/longread/minigut_ont.sam.gz'
            with gzip.open(path, 'rt') as stream: text = stream.read()
            with gzip.open(path, 'wt') as stream: stream.write(text.replace('SN:', 'SN:foreign_', 1))
        else:
            path = folder / 'test_inputs/longread/plasmid_contigs.fasta'
            lines = path.read_text().splitlines(); index = next(i for i, line in enumerate(lines) if line and not line.startswith('>'))
            lines[index] = ('C' if lines[index][0] != 'C' else 'A') + lines[index][1:]; path.write_text('\n'.join(lines) + '\n')
        evaluate(name, False, lambda folder=folder: long_check(folder))
    assert hashes == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in original}
    result = {'pass': True, 'cases': records, 'original_products_unchanged': True,
              'source_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                for name in ['run_p3_semantic_oracle_controls.py', 'check_metabat2_native.py', 'check_longread_native.py']},
              'scope': 'Actual product-copy counterfactuals only; no additional scientific analyses or accuracy benchmark'}
    (args.work_dir / 'run.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS semantic oracle counterfactuals', len(records))


if __name__ == '__main__':
    main()
