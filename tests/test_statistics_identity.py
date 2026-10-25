import csv
import math
import random
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StatisticsIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def inputs(self, name, ids, values, features=None, id_column="contig_id", groups=("A", "B")):
        folder = self.root / name
        folder.mkdir()
        features = features or [f"p{i}" for i in range(len(values))]
        abundance = folder / "abundance.tsv"
        with abundance.open("w") as fh:
            fh.write(f"sample_id\t{id_column}\traw_count\tcoverage\n")
            for feature, counts in zip(features, values):
                for sid, count in zip(ids, counts):
                    fh.write(f"{sid}\t{feature}\t{count}\t{count}\n")
        metadata = folder / "metadata.tsv"
        metadata.write_text("sample_id\tgroup\n" + "".join(
            f"{sid}\t{groups[0 if i < 3 else 1]}\n" for i, sid in enumerate(ids)
        ))
        return folder, abundance, metadata

    def run_script(self, script, *args):
        result = subprocess.run(["Rscript", str(ROOT / "bin" / script), *map(str, args)],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    @staticmethod
    def rows(path):
        with path.open() as fh:
            return list(csv.DictReader(fh, delimiter="\t"))

    def test_diversity_preserves_numeric_and_literal_na_sample_names(self):
        values = [[1, 3, 4, 2, 1, 5], [4, 1, 2, 5, 3, 2], [2, 2, 1, 3, 4, 1]]
        baseline = None
        cases = [[f"S{i}" for i in range(6)], ["001", "1", "2", "3", "4", "5"],
                 ["NA", "10", "20", "30", "40", "50"], ["10", "20", "30", "40", "50", "60"]]
        for i, ids in enumerate(cases):
            with self.subTest(ids=ids):
                folder, ab, meta = self.inputs(str(i), ids, values)
                metrics, beta = folder / "metrics.tsv", folder / "beta.tsv"
                self.run_script("diversity.R", "--abundance", ab, "--metadata", meta,
                                "--out-metrics", metrics, "--out-beta", beta)
                rows = self.rows(metrics)
                self.assertEqual({row["sample_id"] for row in rows}, set(ids))
                alpha = {(ids.index(row["sample_id"]), row["metric"]): (row["value"], row["group"])
                         for row in rows}
                distances = {(ids.index(row["sample_id"]), j): row[sid]
                             for row in self.rows(beta) for j, sid in enumerate(ids)}
                if baseline is None:
                    baseline = alpha, distances
                else:
                    self.assertEqual((alpha, distances), baseline)

    def test_network_preserves_sample_and_feature_identifiers(self):
        ids = ["001", "1", "NA", "10", "20", "30"]
        features = ["001", "1", "NA"]
        values = [[11, 12, 13, 14, 15, 16], [21, 22, 23, 24, 25, 26], [31, 32, 33, 34, 35, 36]]
        folder, ab, _ = self.inputs("network", ids, values, features)
        output = folder / "matrix.tsv"
        self.run_script("network_prepare.R", "--abundance", ab, "--out", output)
        rows = self.rows(output)
        self.assertEqual(set(rows[0]) - {"#OTU ID"}, set(ids))
        self.assertEqual({row["#OTU ID"] for row in rows}, set(features))
        observed = {(row["#OTU ID"], sid): int(row[sid]) for row in rows for sid in ids}
        self.assertEqual(observed, {(feature, sid): values[i][j]
                                    for i, feature in enumerate(features) for j, sid in enumerate(ids)})

    def test_network_missing_count_token_is_not_replaced_by_coverage(self):
        folder = self.root / "missing-count"
        folder.mkdir()
        ab = folder / "ab.tsv"
        ab.write_text("sample_id\tcontig_id\traw_count\tcoverage\n"
                      "S1\tp1\tNA\t12\nS2\tp1\t13\t99\n")
        output = folder / "matrix.tsv"
        result = subprocess.run(["Rscript", str(ROOT / "bin/network_prepare.R"),
                                 "--abundance", str(ab), "--out", str(output)],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("coverage is not a count", result.stderr)
        self.assertFalse(output.exists())

    def test_internal_differential_is_invariant_to_sample_and_feature_renaming(self):
        values = [[1, 2, 4, 8, 11, 14], [3, 7, 4, 2, 3, 8], [9, 4, 6, 1, 5, 3]]
        baseline = None
        for i, ids in enumerate([[f"S{j}" for j in range(6)], ["001", "1", "2", "3", "4", "5"],
                                 ["NA", "S1", "S2", "S3", "S4", "S5"]]):
            features = ["001", "1", "NA"] if i else ["p0", "p1", "p2"]
            with self.subTest(ids=ids):
                folder, ab, meta = self.inputs(str(i), ids, values, features)
                output = folder / "diff.tsv"
                self.run_script("differential_abundance.R", "--abundance", ab, "--metadata", meta,
                                "--out", output)
                rows = self.rows(output)
                self.assertEqual({row["contig_id"] for row in rows}, set(features))
                normalized = {features.index(row["contig_id"]):
                              {k: v for k, v in row.items() if k != "contig_id"} for row in rows}
                if baseline is None:
                    baseline = normalized
                else:
                    self.assertEqual(normalized, baseline)

    @staticmethod
    def count_values():
        rng = random.Random(20261020)

        def count():
            limit = math.exp(-rng.gammavariate(10, 4))
            product, n = 1.0, 0
            while product > limit:
                product *= rng.random()
                n += 1
            return n - 1 + 10

        return [[count() for _ in range(6)] for _ in range(120)]

    def test_deseq_sample_renaming_keeps_all_rows_and_statistics(self):
        values = self.count_values()
        baseline = None
        for i, ids in enumerate([["S001", "S1", "S2", "S3", "S4", "S5"],
                                 ["001", "1", "2", "3", "4", "5"],
                                 ["NA", "S1", "S2", "S3", "S4", "S5"]]):
            with self.subTest(ids=ids):
                folder, ab, meta = self.inputs(str(i), ids, values, id_column="plasmid_id")
                output = folder / "deseq.tsv"
                self.run_script("deseq2_plasmid.R", "--abundance", ab, "--metadata", meta,
                                "--output", output)
                rows = self.rows(output)
                self.assertEqual(len(rows), 120)
                normalized = {row["plasmid_id"]: row for row in rows}
                if baseline is None:
                    baseline = normalized
                else:
                    self.assertEqual(normalized, baseline)

    def test_numeric_group_labels_keep_two_distinct_groups_and_same_statistics(self):
        ids = [f"S{i}" for i in range(6)]
        for script, id_column, group_columns, output_flag in [
            ("differential_abundance.R", "contig_id", ("group1", "group2"), "--out"),
            ("deseq2_plasmid.R", "plasmid_id", ("group_a", "group_b"), "--output"),
        ]:
            baseline = None
            for i, groups in enumerate([("A", "B"), ("001", "1")]):
                with self.subTest(script=script, groups=groups):
                    folder, ab, meta = self.inputs(f"groups-{script}-{i}", ids, self.count_values(),
                                                   id_column=id_column, groups=groups)
                    output = folder / "results.tsv"
                    self.run_script(script, "--abundance", ab, "--metadata", meta, output_flag, output)
                    rows = self.rows(output)
                    self.assertEqual(len(rows), 120)
                    for row in rows:
                        self.assertEqual((row[group_columns[0]], row[group_columns[1]]), groups)
                        row[group_columns[0]], row[group_columns[1]] = "A", "B"
                    normalized = {row[id_column]: row for row in rows}
                    if baseline is None:
                        baseline = normalized
                    else:
                        self.assertEqual(normalized, baseline)

    def test_deseq_feature_ids_keep_leading_zeros_and_literal_na(self):
        ids = [f"S{i}" for i in range(6)]
        features = [f"p{i}" for i in range(120)]
        baseline = None
        for i, names in enumerate([features, ["001", "1", "NA", *features[3:]]]):
            folder, ab, meta = self.inputs(f"features-{i}", ids, self.count_values(), names,
                                           id_column="plasmid_id")
            output = folder / "deseq.tsv"
            self.run_script("deseq2_plasmid.R", "--abundance", ab, "--metadata", meta,
                            "--output", output)
            rows = self.rows(output)
            self.assertEqual({row["plasmid_id"] for row in rows}, set(names))
            normalized = {names.index(row["plasmid_id"]): row for row in rows}
            if baseline is None:
                baseline = normalized
                continue
            for index, row in normalized.items():
                for field in ("group_a", "group_b", "method", "warnings"):
                    self.assertEqual(row[field], baseline[index][field])
                for field in ("log2_fold_change", "p_value", "q_value"):
                    if not baseline[index][field]:
                        self.assertEqual(row[field], "")
                    else:
                        self.assertTrue(math.isclose(float(row[field]), float(baseline[index][field]),
                                                     rel_tol=1e-6, abs_tol=1e-8), (index, field))


if __name__ == "__main__":
    unittest.main()
