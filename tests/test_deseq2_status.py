"""Model-ineligible states preserve the cohort and never manufacture counts."""
import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DESeq2StatusTests(unittest.TestCase):
    def invoke(self, values, groups=None, extra=(), ids=None):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            ids = ids if ids is not None else ['001', '1', 'NA', 'S3', 'S4', 'S5']
            groups = groups if groups is not None else ['A'] * (len(ids) // 2) + ['B'] * (len(ids) - len(ids) // 2)
            ab = d / 'counts.tsv'
            ab.write_text('sample_id\tplasmid_id\traw_count\tcoverage\n' + ''.join(
                f'{sid}\tF{j}\t{value}\t123.5\n'
                for j, row in enumerate(values) for sid, value in zip(ids, row)))
            meta = d / 'samples.tsv'
            with meta.open('w') as stream:
                writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
                writer.writerow(['sample_id', 'group'])
                writer.writerows(zip(ids, groups))
            cmd = ['Rscript', str(ROOT / 'bin/deseq2_plasmid.R'), '--abundance', str(ab),
                   '--metadata', str(meta), '--output', str(d / 'out.tsv'),
                   '--out-status', str(d / 'status.tsv'), *extra]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode:
                self.assertFalse((d / 'out.tsv').exists())
                self.assertFalse((d / 'status.tsv').exists())
                return result, [], []
            with (d / 'out.tsv').open() as stream:
                rows = list(csv.DictReader(stream, delimiter='\t'))
            with (d / 'status.tsv').open() as stream:
                status = list(csv.DictReader(stream, delimiter='\t'))
            self.assertEqual([r['sample_id'] for r in status], ids)
            self.assertEqual({r['model_fitted'] for r in status}, {'FALSE'})
            self.assertEqual({r['used_in_fit'] for r in status}, {'FALSE'})
            return result, rows, status

    def check_state(self, values, reason, **kwargs):
        result, rows, status = self.invoke(values, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rows, [])
        self.assertEqual({r['reason'] for r in status}, {reason})
        return status

    def test_empty_feature_set_retains_metadata(self):
        self.check_state([], 'zero_features')

    def test_all_measured_zero_is_explicit_without_loading_model(self):
        status = self.check_state([[0] * 6 for _ in range(4)], 'all_zero_counts')
        self.assertEqual({r['input_library_size'] for r in status}, {'0'})
        self.assertEqual({r['deseq2_version'] for r in status}, {'not_loaded'})

    def test_positive_low_counts_are_filtered_without_model(self):
        self.check_state([[1, 2, 3, 4, 5, 6]], 'no_features_after_count_filter')

    def test_zero_library_is_not_dropped_or_imputed(self):
        status = self.check_state([[0, 50, 40, 60, 30, 70]], 'zero_count_samples')
        self.assertEqual(status[0]['in_design'], 'TRUE')
        self.assertEqual(status[0]['model_library_size'], '0')

    def test_filter_can_create_a_zero_library_without_dropping_the_sample(self):
        values = [[0,50,40,60,30,70] for _ in range(4)] + [[5,0,0,0,0,0]]
        status = self.check_state(values,'zero_count_samples')
        self.assertEqual(status[0]['input_library_size'],'5')
        self.assertEqual(status[0]['model_library_size'],'0')
        self.assertEqual(status[0]['in_design'],'TRUE')
        self.assertEqual({r['features_used'] for r in status},{'4'})

    def test_ratio_without_shared_positive_features_does_not_switch_estimator(self):
        values = [[0 if i == j else 40 + j for i in range(6)] for j in range(6)]
        status = self.check_state(values, 'no_positive_geometric_means')
        self.assertEqual({r['sf_type'] for r in status}, {'ratio'})

    def test_unassigned_groups_remain_visible(self):
        status = self.check_state([[50] * 6], 'insufficient_groups', groups=[''] * 6)
        self.assertEqual({r['in_design'] for r in status}, {'FALSE'})
        self.assertEqual({r['model_library_size'] for r in status}, {''})

    def test_single_group_is_not_a_comparison(self):
        self.check_state([[50] * 6], 'insufficient_groups', groups=['A'] * 6)

    def test_configured_larger_threshold_is_used(self):
        status = self.check_state([[50] * 6], 'insufficient_replication', extra=['--min-replicates', '4'])
        self.assertEqual({r['min_replicates'] for r in status}, {'4'})

    def test_one_sample_per_group_has_no_residual_degrees_of_freedom(self):
        self.check_state([[50, 70]], 'insufficient_residual_degrees_of_freedom',
                         ids=['001', 'NA'], extra=['--min-replicates', '1'])

    def test_status_preserves_quoted_tab_and_newline_group_labels(self):
        groups = ['"A\tcontrol'] * 3 + ['"B\ncase'] * 3
        status = self.check_state([[50] * 6], 'insufficient_replication',
                                  groups=groups, extra=['--min-replicates', '4'])
        self.assertEqual([r['group'] for r in status], groups)

    def test_invalid_thresholds_rejected_without_products(self):
        for value in ['0', '-1', '1.5', 'NaN', 'Inf', 'bad', str(2**31)]:
            with self.subTest(value=value):
                result, _, _ = self.invoke([[50] * 6], extra=['--min-replicates', value])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('--min-replicates', result.stderr)

    def test_missing_duplicate_unknown_flags_are_errors(self):
        for flags in [['--min-replicates'], ['--min-replicates', '3', '--min-replicates', '4'], ['--typo', '3']]:
            with self.subTest(flags=flags):
                result, _, _ = self.invoke([[50] * 6], extra=flags)
                self.assertNotEqual(result.returncode, 0)

    def test_invalid_counts_are_not_replaced_by_positive_coverage(self):
        for value in ['', 'NA', '0.5', '-1', 'NaN', 'Inf', str(2**31)]:
            with self.subTest(value=value):
                result, _, _ = self.invoke([[value] * 6])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('coverage is not a count', result.stderr)

    def test_internal_comparison_rejects_the_same_invalid_shared_thresholds(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'out.tsv'
            for value in ['0', '-1', '1.5', 'NaN', 'Inf', 'bad', str(2**31)]:
                with self.subTest(value=value):
                    result = subprocess.run(['Rscript', str(ROOT / 'bin/differential_abundance.R'),
                        '--abundance', str(Path(directory) / 'not_read.tsv'),
                        '--metadata', str(Path(directory) / 'not_read_meta.tsv'),
                        '--min-replicates', value, '--out', str(out)], capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('--min-replicates', result.stderr)
                    self.assertFalse(out.exists())

    def internal(self, groups, tool='internal'):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            ids = ['001', '1', 'NA', 'S3', 'S4', 'S5']
            ab = d / 'counts.tsv'
            ab.write_text('sample_id\tcontig_id\tcoverage\n' + ''.join(f'{sid}\tF1\t{i+10}\n' for i,sid in enumerate(ids)))
            meta = d / 'samples.tsv'
            with meta.open('w') as stream:
                writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
                writer.writerow(['sample_id','group'])
                writer.writerows(zip(ids, groups))
            script = 'diversity.R' if tool=='diversity' else 'differential_abundance.R'
            outputs = ['--out-metrics',str(d/'out.tsv'),'--out-beta',str(d/'beta.tsv')] if tool=='diversity' else ['--out',str(d/'out.tsv')]
            result = subprocess.run(['Rscript',str(ROOT/'bin'/script),
                '--abundance',str(ab),'--metadata',str(meta),*outputs],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with (d/'out.tsv').open() as stream: return list(csv.DictReader(stream,delimiter='\t'))

    def test_internal_comparison_preserves_encoded_group_labels(self):
        a, b = '"A\tcontrol', '"B\ncase'
        rows = self.internal([a]*3+[b]*3)
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['group1'],rows[0]['group2']),(a,b))

    def test_missing_group_is_not_a_biological_group_named_na(self):
        self.assertEqual(self.internal(['A']*3+['NA']*3),[])

    def test_diversity_preserves_encoded_group_labels(self):
        a, b = '"A\tcontrol', '"B\ncase'
        rows = self.internal([a]*3+[b]*3, tool='diversity')
        self.assertEqual(len(rows),24)
        expected = dict(zip(['001','1','NA','S3','S4','S5'],[a]*3+[b]*3))
        self.assertTrue(all(row['group']==expected[row['sample_id']] for row in rows))


if __name__ == '__main__':
    unittest.main()
