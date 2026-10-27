"""Native1.0.1 parser and actual BLAST read-set controls; no search inference."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = Path(os.environ['ABRICATE_NATIVE_PREFIX']).resolve()
HELPER = ROOT / 'bin/abricate_runtime_resources.pl'


class Resources(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.fasta = self.base / 'input.fa'
        self.fasta.write_text('>EXPLICIT_READ_SET_ONLY\nACGT\n')
        self.env = dict(os.environ, PATH=str(PREFIX / 'bin') + ':' + os.environ['PATH'])

    def tearDown(self):
        self.temp.cleanup()

    def probe(self, *args, env=None, success=True):
        output = self.base / 'identity.json'
        cmd = [str(PREFIX / 'bin/perl'), str(HELPER), '--runtime-base64', 'e30=', '--output', str(output), '--', str(self.fasta), *args]
        p = subprocess.run(cmd, env=env or self.env, capture_output=True, text=True, timeout=60)
        if not success:
            self.assertNotEqual(p.returncode, 0)
            return p.stderr
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(output.read_text())

    def test_native_default_and_abbreviation_last_option_precedence(self):
        first = self.probe()
        self.assertEqual(first['parsed_arguments']['db'], 'ncbi')
        self.assertEqual(first['resolved_locations']['datadir'], str(PREFIX / 'db'))
        other = self.probe('--DB', 'plasmidfinder', '--db=ncbi', '--dat', str(PREFIX / 'db'), '--minc', '80', '--MINID', '80', '--threads', '7')
        self.assertEqual(first['resources'], other['resources'])
        self.assertEqual(other['parsed_arguments']['db'], 'ncbi')
        self.assertNotIn('threads', other['parsed_arguments'])

    def test_native_entrypoint_alias_uses_realbin(self):
        tools = self.base / 'alias tools'
        tools.mkdir()
        (tools / 'abricate').symlink_to(PREFIX / 'bin/abricate')
        env = dict(self.env, PATH=str(tools) + ':' + self.env['PATH'])
        value = self.probe(env=env)
        self.assertEqual(value['resolved_locations']['datadir'], str(PREFIX / 'db'))
        self.assertEqual(value['resources']['entrypoint'][0]['link'], str(PREFIX / 'bin/abricate'))

    def test_explicit_directory_and_hidden_newline_same_stat_member(self):
        db = self.base / 'db'
        shutil.copytree(PREFIX / 'db/ncbi', db / 'ncbi')
        sidecar = db / 'ncbi/.extra\nmember'
        sidecar.write_bytes(b'old\n')
        st = sidecar.stat()
        first = self.probe('--datadir', str(db))
        sidecar.write_bytes(b'new\n')
        os.utime(sidecar, ns=(st.st_atime_ns, st.st_mtime_ns))
        second = self.probe('--datadir', str(db))
        self.assertNotEqual(first['resources']['selected_database_directory'], second['resources']['selected_database_directory'])

    def test_alias_external_volume_is_recorded(self):
        db = self.base / 'db'
        (db / 'alias').mkdir(parents=True)
        subprocess.run([str(PREFIX / 'bin/blastdb_aliastool'), '-dblist', str(PREFIX / 'db/ncbi/sequences'), '-dbtype', 'nucl', '-out', str(db / 'alias/sequences'), '-title', 'explicit external volume'], check=True, capture_output=True)
        value = self.probe('--datadir', str(db), '--db', 'alias')
        volume = str(PREFIX / 'db/ncbi/sequences')
        self.assertEqual(value['resolved_locations']['blast_volumes'], [volume])
        self.assertIn('sequences.nhr', value['resources']['blast_volumes'][volume])

    def test_fofn_uses_native_override_instead_of_unused_argv(self):
        fofn = self.base / 'fofn.txt'
        fofn.write_text(str(self.fasta) + '\n')
        value = self.probe(str(self.base / 'unused-missing.fa'), '--fofn', str(fofn))
        self.assertEqual(len(value['resources']['inputs']), 1)
        self.assertIn('fofn', value['resources'])

    def test_invalid_database_and_unprepared_setup_are_refused(self):
        self.assertIn('Missing resource', self.probe('--db', 'NO_SUCH_DB', success=False))
        self.assertIn('Prepare ABRicate databases', self.probe('--setupdb', success=False))

    def test_cycle_dangling_and_special_database_members_fail(self):
        db = self.base / 'db'
        (db / 'ncbi').mkdir(parents=True)
        member = db / 'ncbi/member'
        member.symlink_to(db / 'ncbi', target_is_directory=True)
        self.assertIn('symlink cycle', self.probe('--datadir', str(db), success=False))
        member.unlink()
        member.symlink_to(db / 'missing')
        self.assertIn('Missing resource', self.probe('--datadir', str(db), success=False))
        member.unlink()
        os.mkfifo(member)
        self.assertIn('not regular', self.probe('--datadir', str(db), success=False))


if __name__ == '__main__':
    unittest.main()
