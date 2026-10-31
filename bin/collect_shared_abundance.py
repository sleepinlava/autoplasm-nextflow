#!/usr/bin/env python3
"""Validate complete shared-reference CoverM tables and retain real read counts.

Input BAMs must contain only primary mapped alignments with known MAPQ >= 10.
Count unit: read alignment; paired mates count separately, never fragments.
"""
import argparse
import csv
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import shutil
import tempfile


def read_rows(path):
    with path.open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f'{path}: missing or duplicate TSV header')
        return reader.fieldnames, list(reader)


def number(text, location, integer=False):
    try:
        value = Decimal(text)
    except (InvalidOperation, TypeError):
        raise ValueError(f'{location}: invalid measurement {text!r}') from None
    if not value.is_finite() or value < 0 or (integer and value != value.to_integral_value()):
        raise ValueError(f'{location}: expected finite nonnegative ' + ('integer count' if integer else 'measurement'))
    return str(int(value)) if integer else text


def collect(catalogue, sample_ids, tables, mapper, output, count_unit="primary_read_alignment", min_breadth=0.75, min_depth=1.0):
    _, features = read_rows(catalogue / 'features.tsv')
    _, samples = read_rows(catalogue / 'samples.tsv')
    expected = [r['sample_id'] for r in samples]
    if len(expected) != len(set(expected)) or len(sample_ids) != len(set(sample_ids)) or len(sample_ids) != len(tables):
        raise ValueError('duplicate samples or table/sample count mismatch')
    if len(features) != len({r['feature_id'] for r in features}):
        raise ValueError('duplicate catalogue feature')
    if (features and set(expected) != set(sample_ids)) or (not features and tables):
        raise ValueError('missing/unexpected sample measurement; only a globally empty catalogue may skip mapping')
    if output.exists():
        raise ValueError(f'refusing to overwrite {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.' + output.name + '-', dir=output.parent))
    try:
        measured = dict(zip(sample_ids, tables))
        states = []
        paired = count_unit == "proper_paired_fragment"
        prevalence = dict.fromkeys((r["feature_id"] for r in features), 0)
        with (stage / 'contig_abundance.tsv').open('w') as all_stream, (stage / 'plasmid_abundance.tsv').open('w') as plasmid_stream:
            writers = [csv.writer(s, delimiter='\t', lineterminator='\n') for s in [all_stream, plasmid_stream]]
            common = ['sample_id', 'rpkm', 'tpm', 'coverage', 'raw_count', 'mapper', 'count_unit']
            extra = ['median_depth','breadth','ambiguous_alignment_fraction'] if paired else []
            writers[0].writerow(['contig_id'] + common + extra)
            writers[1].writerow(['plasmid_id'] + common + extra)
            for sample in expected:
                values = {}
                if features:
                    fields, rows = read_rows(measured[sample])
                    columns = {}
                    measurements = [('coverage', ' Mean'), ('rpkm', ' RPKM'), ('tpm', ' TPM'), ('raw_count', ' Read Count')]
                    if paired: measurements += [('median_depth',' Median'),('breadth',' Covered Fraction'),('ambiguous_alignment_fraction',' Ambiguous Alignment Fraction')]
                    for key, suffix in measurements:
                        matches = [f for f in fields[1:] if f.endswith(suffix)]
                        if len(matches) != 1:
                            raise ValueError(f'{measured[sample]}: expected exactly one {suffix.strip()} column')
                        columns[key] = matches[0]
                    for line, row in enumerate(rows, 2):
                        fid = row[fields[0]]
                        if fid in values:
                            raise ValueError(f'{sample}: duplicate feature {fid}')
                        values[fid] = {key: number(row[col], f'{sample}:{line}:{fid}:{key}', key == 'raw_count') for key, col in columns.items()}
                    if set(values) != {r['feature_id'] for r in features}:
                        raise ValueError(f'{sample}: measured features differ from shared reference')
                total = 0
                for feature in features:
                    fid = feature['feature_id']
                    val = values[fid]
                    total += int(val['raw_count'])
                    row = [fid, sample, val['rpkm'], val['tpm'], val['coverage'], val['raw_count'], mapper, count_unit] + [val[k] for k in extra]
                    prevalence[fid] += (float(val['breadth']) >= min_breadth and float(val['coverage']) >= min_depth) if paired else float(val['coverage']) > 0
                    writers[0].writerow(row)
                    if feature['is_plasmid'] == '1':
                        writers[1].writerow(row)
                plasmid_total = sum(int(values[r["feature_id"]]["raw_count"]) for r in features if r["is_plasmid"] == "1")
                states.append([sample, len(features), sum(r["is_plasmid"] == "1" for r in features), total, plasmid_total, 'empty_catalogue' if not features else ('measured_zero' if total == 0 else 'measured')])
        with (stage / 'sample_states.tsv').open('w') as stream:
            writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
            writer.writerow(['sample_id', 'reference_features', 'plasmid_features', 'eligible_read_alignments', 'plasmid_read_alignments', 'quantification_status'])
            writer.writerows(states)
        with (stage / 'prevalence.tsv').open('w') as stream:
            writer=csv.writer(stream,delimiter='\t',lineterminator='\n')
            writer.writerow(['feature_id','detected_samples','total_samples','prevalence','detection_rule'])
            for fid,n in sorted(prevalence.items()): writer.writerow([fid,n,len(expected),n/len(expected),'breadth>='+str(min_breadth)+';depth>='+str(min_depth) if paired else 'coverage>0'])
        (stage / 'method.json').write_text(json.dumps({'mapper': mapper, 'count_unit': count_unit,
            'paired_end': 'proper primary same-reference pairs, both MAPQ>=10 and !=255; once per query name' if paired else 'each eligible mate counts separately; not fragment counts',
            'alignment_filter': 'exclude unmapped, secondary and supplementary; MAPQ >= 10 and != 255',
            'ambiguity': 'MAPQ below 10 excluded (Bowtie2 ties may have MAPQ 1); MAPQ is aligner confidence, not proof of unique biological origin',
            'coverage': 'pysam paired-fragment depth, overlapping mates once per base; breadth/median across all positions; RPKM/TPM from fragment counts' if paired else 'CoverM mean/TPM/RPKM/count over the same filtered BAM; end exclusion 0',
            'reference': 'all samples compete against one assembly-sequence catalogue; plasmid subset by source union'}, indent=2) + '\n')
        stage.rename(output)
    except BaseException:
        shutil.rmtree(stage)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalogue', type=Path, required=True)
    parser.add_argument('--sample-ids', nargs='*', default=[])
    parser.add_argument('--tables', nargs='*', type=Path, default=[])
    parser.add_argument('--mapper', required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--count-unit',choices=['primary_read_alignment','proper_paired_fragment'],default='primary_read_alignment')
    parser.add_argument('--min-breadth',type=float,default=0.75)
    parser.add_argument('--min-depth',type=float,default=1.0)
    args = parser.parse_args()
    try:
        collect(args.catalogue, args.sample_ids, args.tables, args.mapper, args.out_dir, args.count_unit, args.min_breadth, args.min_depth)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, str(error) + '\n')
