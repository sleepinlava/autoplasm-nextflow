import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "generate_report.R"


class GenerateReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.published = self.root / "published"
        self.output = self.root / "report"
        self.output.mkdir()
        self.records = []
        self.sample_ids = []

    def tearDown(self):
        self.temp.cleanup()

    def sample(self, sample_id, contigs, circular, tool):
        consensus = self.published / "04_plasmid_detection" / "consensus"
        structure = self.published / "04_plasmid_detection" / "structure"
        consensus.mkdir(parents=True, exist_ok=True)
        structure.mkdir(parents=True, exist_ok=True)
        (consensus / f"{sample_id}.plasmid_contigs.fasta").write_text(
            "".join(f">p{i}\nACGT\n" for i in range(contigs))
        )
        (consensus / f"{sample_id}.plasmid_consensus.tsv").write_text(
            "contig_id\tsample_id\tplasmid_call\tsupporting_tools\n" +
            "".join(f"p{i}\t{sample_id}\tplasmid\t{tool}\n" for i in range(contigs))
        )
        (structure / f"{sample_id}.plasmid_structure.tsv").write_text(
            "sample_id\tplasmid_id\tis_circular\n" +
            "".join(f"{sample_id}\tp{i}\t{'true' if i < circular else 'false'}\n"
                    for i in range(contigs))
        )
        self.sample_ids.append(sample_id)
        for kind, path in [('plasmid_fasta', consensus / f'{sample_id}.plasmid_contigs.fasta'),
                           ('consensus', consensus / f'{sample_id}.plasmid_consensus.tsv'),
                           ('structure', structure / f'{sample_id}.plasmid_structure.tsv')]:
            self.records.append({'sample_id': sample_id, 'section': '04_plasmid_detection',
                                 'producer': 'controlled_detection', 'kind': kind, 'files': [str(path)]})

    def invoke(self):
        manifest = self.root / 'inputs.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'records': self.records,
                                      'settings': {'platform': 'assembly', 'project_name': 'identity_test'}}))
        samplesheet = self.root / 'samples.tsv'
        samplesheet.write_text('sample_id\n' + '\n'.join(self.sample_ids) + '\n')
        return subprocess.run(['Rscript', str(SCRIPT), '--manifest', str(manifest),
                               '--samplesheet', str(samplesheet), '--out-prefix', str(self.output)],
                              text=True, capture_output=True)

    def run_report(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((self.output / "report_data.json").read_text())

    def test_suffix_tokens_in_sample_names_keep_independent_summaries(self):
        expected = {
            "S": (1, 1, "genomad"),
            "S.plasmid_contigs.fasta": (2, 0, "platon"),
            "S.plasmid_contigs.fasta.extra": (3, 2, "plasme"),
        }
        for sample, values in expected.items():
            self.sample(sample, *values)
        data = self.run_report()
        self.assertEqual(len(data["samples"]), len(expected))
        observed = {row["sample_id"]: (row["consensus_plasmids"], row["circular"],
                                        row["detection_tools"])
                    for row in data["samples"]}
        self.assertEqual(observed, expected)
        markdown = (self.output / "report.md").read_text()
        html = (self.output / "report.html").read_text()
        self.assertIn("- Samples: 3", markdown)
        self.assertIn("TETRA composition scores are not host assignments", markdown)
        self.assertIn("uncalibrated TETRA host links are disabled", markdown)
        self.assertIn("uncalibrated TETRA host links are disabled", html)
        for sample, (contigs, circular, tool) in expected.items():
            line = f"| {sample} | {contigs} | {circular} | {tool} |"
            self.assertIn(line, markdown)
            self.assertIn(line, html)

    def test_zero_calls_still_preserve_the_complete_sample_id(self):
        sample = "S.plasmid_contigs.fasta"
        self.sample(sample, 0, 0, "genomad")
        data = self.run_report()
        self.assertEqual(data["samples"], [{"sample_id": sample, "consensus_plasmids": 0,
                                            "circular": 0, "detection_tools": ""}])
        self.assertIn(f"| {sample} | 0 | 0 |  |", (self.output / "report.md").read_text())

    def test_ordinary_sample_report_remains_compatible(self):
        self.sample("S1", 2, 1, "genomad")
        data = self.run_report()
        self.assertEqual(data["samples"], [{"sample_id": "S1", "consensus_plasmids": 2,
                                            "circular": 1, "detection_tools": "genomad"}])
        self.assertIn("| S1 | 2 | 1 | genomad |", (self.output / "report.md").read_text())

    def assert_rejected(self, diagnostic):
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(diagnostic, result.stderr)
        self.assertFalse((self.output / 'report_data.json').exists())
        self.assertFalse((self.output / 'report.md').exists())

    def test_stale_samples_and_empty_published_directories_are_ignored(self):
        self.sample('CURRENT', 1, 0, 'genomad')
        records, ids = self.records.copy(), self.sample_ids.copy()
        self.sample('OLD', 2, 2, 'platon')
        (self.published / '08_annotation').mkdir()
        self.records, self.sample_ids = records, ids
        data = self.run_report()
        self.assertEqual([r['sample_id'] for r in data['samples']], ['CURRENT'])
        section = next(r for r in data['sections'] if r['name'] == '08_annotation')
        self.assertEqual((section['present'], section['status']), (False, 'not_observed'))

    def test_missing_current_sample_input_is_not_zero_detection(self):
        self.sample('CURRENT', 0, 0, 'genomad')
        self.records.pop()
        self.assert_rejected('Missing report input')

    def test_duplicate_role_is_rejected(self):
        self.sample('CURRENT', 1, 0, 'genomad')
        self.records.append(self.records[0].copy())
        self.assert_rejected('Duplicate report input')

    def test_unexpected_sample_is_rejected(self):
        self.sample('CURRENT', 1, 0, 'genomad')
        self.records[0]['sample_id'] = 'OLD'
        self.assert_rejected('unexpected sample ID')

    def test_wrong_table_sample_id_is_rejected(self):
        self.sample('CURRENT', 1, 0, 'genomad')
        path = Path(self.records[1]['files'][0])
        path.write_text(path.read_text().replace('\tCURRENT\t', '\tOTHER\t'))
        self.assert_rejected('sample identity mismatch')

    def test_missing_or_broken_table_cannot_silently_produce_zero(self):
        self.sample('CURRENT', 1, 0, 'genomad')
        path = Path(self.records[1]['files'][0])
        path.write_text('broken\n')
        self.assert_rejected('missing required columns')

    def test_disagreeing_feature_sets_are_rejected(self):
        self.sample('CURRENT', 1, 0, 'genomad')
        path = Path(self.records[2]['files'][0])
        path.write_text(path.read_text().replace('p0', 'unrelated'))
        self.assert_rejected('feature mismatch')

    def test_duplicate_table_header_is_rejected(self):
        self.sample('CURRENT', 1, 0, 'genomad')
        path = Path(self.records[1]['files'][0])
        path.write_text(path.read_text().replace('supporting_tools', 'contig_id'))
        self.assert_rejected('duplicate TSV columns')

    def test_observed_optional_output_drives_section_and_methods(self):
        self.sample('CURRENT', 0, 0, 'genomad')
        self.records.append({'section': '08_annotation', 'producer': 'LATE_TOOL', 'kind': 'evidence',
                             'output': 'versions_tool', 'evidence': ['LATE_TOOL', 'tool', '1.2.3'], 'files': []})
        data = self.run_report()
        self.assertTrue(next(r for r in data['sections'] if r['name'] == '08_annotation')['present'])
        self.assertIn('LATE_TOOL/versions_tool', data['methods'])
        self.assertNotIn('Reads were quality-filtered', data['methods'])
        self.assertNotIn('Typing used PlasmidFinder', data['methods'])

    def test_literal_numeric_and_na_sample_ids_preserve_identity(self):
        for sid in ['001', '1', 'NA']:
            self.sample(sid, 1, 0, 'genomad')
        self.assertEqual([r['sample_id'] for r in self.run_report()['samples']], ['001', '1', 'NA'])


if __name__ == "__main__":
    unittest.main()
