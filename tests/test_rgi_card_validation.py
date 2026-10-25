"""CARD identity is derived from JSON, not an arbitrary FASTA filename match."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('card_validation', ROOT / 'bin/validate_rgi_card.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class RgiCardValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.card = Path(self.directory.name) / 'declared'
        self.card.mkdir()
        (self.card / 'card.json').write_text(json.dumps({'_version': '3.3.0', '6038': {'ARO_name': 'VIM-77'}}))
        for suffix in ['', '_all']:
            (self.card / ('card_database_v3.3.0' + suffix + '.fasta')).write_text('>reference\nMELPNIM\n')

    def loaded(self):
        p = Path(self.directory.name) / 'localDB'
        p.mkdir()
        (p / 'card.json').write_bytes((self.card / 'card.json').read_bytes())
        (p / 'loaded_databases.json').write_text(json.dumps({'card_json': {'data_version': '3.3.0'}}))
        return p

    def test_json_version_wins_over_additional_annotation_versions(self):
        (self.card / 'card_database_v9.9.9_all.fasta').write_text('>old\nMEL\n')
        self.assertEqual(validator.validate(self.card), '3.3.0')

    def test_missing_expected_annotations_rejected(self):
        (self.card / 'card_database_v3.3.0_all.fasta').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing CARD annotation file'):
            validator.validate(self.card)

    def test_invalid_json_root_version_and_missing_models_rejected(self):
        for data in [[], {}, {'_version': 3.3}, {'_version': '../escape'}, {'_version': '3.3.0\n'}, {'_version': '3.3.0'}]:
            with self.subTest(data=data):
                (self.card / 'card.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    validator.validate(self.card)

    def test_exact_loaded_copy_and_metadata_pass(self):
        self.assertEqual(validator.validate(self.card, self.loaded()), '3.3.0')

    def test_loaded_different_content_is_rejected_even_with_same_version(self):
        p = self.loaded()
        (p / 'card.json').write_text(json.dumps({'_version': '3.3.0', '391': {'ARO_name': 'VIM-2'}}))
        with self.assertRaisesRegex(ValueError, 'Loaded CARD JSON differs'):
            validator.validate(self.card, p)

    def test_stale_loaded_version_metadata_is_rejected(self):
        p = self.loaded()
        (p / 'loaded_databases.json').write_text(json.dumps({'card_json': {'data_version': '3.2.8'}}))
        with self.assertRaisesRegex(ValueError, 'Loaded CARD version metadata differs'):
            validator.validate(self.card, p)


if __name__ == '__main__':
    unittest.main()
