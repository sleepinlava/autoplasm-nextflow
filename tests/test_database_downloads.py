#!/usr/bin/env python3
"""Exercise the complete asset downloader with real curl and local HTTP/files."""
import functools
import hashlib
import http.server
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import threading
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parent / 'nf-test/download_databases.sh'


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Handler(http.server.SimpleHTTPRequestHandler):
    requests = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.requests.append(self.path)
        if self.path == '/truncated':
            self.send_response(200)
            self.send_header('Content-Length', '1000')
            self.end_headers()
            self.wfile.write(b'incomplete')
            self.close_connection = True
        else:
            super().do_GET()


class Downloads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.served = tempfile.TemporaryDirectory()
        cls.web = Path(cls.served.name)
        (cls.web / 'good.dat').write_bytes(b'complete reference\n')
        (cls.web / 'empty.dat').touch()
        (cls.web / 'bad.tar.gz').write_bytes(b'<html>not an archive</html>')
        with tarfile.open(cls.web / 'good.tar.gz', 'w:gz') as archive:
            data = b'fixture database\n'
            info = tarfile.TarInfo('database.txt')
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        with zipfile.ZipFile(cls.web / 'good.zip', 'w') as archive:
            archive.writestr('database.txt', 'fixture database\n')
        cls.server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(Handler, directory=cls.web))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.served.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / 'assets with spaces'
        self.out.mkdir()
        self.assets = self.root / 'assets.tsv'
        Handler.requests.clear()

    def run_list(self, rows, *extra):
        self.assets.write_text(''.join('\t'.join(row) + '\n' for row in rows))
        return subprocess.run(
            ['bash', str(SCRIPT), '--outdir', str(self.out), '--asset-list', str(self.assets), *extra],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, 'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'})

    def row(self, name='good.dat', path=None, sha=None):
        return (name, self.base + '/' + (path or name), *(() if sha is None else (sha,)))

    def lock(self, name, sha):
        with (self.out / 'manifest.txt').open('a') as stream:
            stream.write(f'ARTIFACT {name} size=1 sha256={sha} url={self.base}/{name}\n')

    def assert_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('ALL DONE', result.stdout)
        self.assertFalse(list(self.out.glob('.*.part')))

    def test_success_and_verified_replay_without_transfer(self):
        rows = [self.row(), self.row('good.tar.gz'), self.row('good.zip')]
        first = self.run_list(rows)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(len(Handler.requests), 3)
        for name in ['good.dat', 'good.tar.gz', 'good.zip']:
            self.assertEqual((self.out / name).read_bytes(), (self.web / name).read_bytes())
        self.assertIn('ALL DONE', first.stdout)
        Handler.requests.clear()
        second = self.run_list(rows)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(Handler.requests, [])
        self.assertEqual((self.out / 'manifest.txt').read_text().count('ARTIFACT '), 3)

    def test_mixed_failure_continues_and_never_reports_success(self):
        result = self.run_list([self.row('missing.dat'), self.row()])
        self.assert_failure(result)
        self.assertIn('FAILED 1 of 2 artifacts', result.stdout)
        self.assertFalse((self.out / 'missing.dat').exists())
        self.assertEqual((self.out / 'good.dat').read_bytes(), (self.web / 'good.dat').read_bytes())
        self.assertEqual(Handler.requests, ['/missing.dat', '/good.dat'])

    def test_recorded_corruption_is_preserved_and_fails(self):
        (self.out / 'good.dat').write_bytes(b'corrupted')
        self.lock('good.dat', digest((self.web / 'good.dat').read_bytes()))
        result = self.run_list([self.row()])
        self.assert_failure(result)
        self.assertIn('CORRUPT', result.stderr)
        self.assertEqual((self.out / 'good.dat').read_bytes(), b'corrupted')
        self.assertEqual(Handler.requests, [])

    def test_unrecorded_partial_is_not_blessed(self):
        (self.out / 'good.dat').write_bytes(b'partial')
        result = self.run_list([self.row()])
        self.assert_failure(result)
        self.assertNotIn('ARTIFACT ', (self.out / 'manifest.txt').read_text())
        self.assertEqual((self.out / 'good.dat').read_bytes(), b'partial')

    def test_independent_digest_can_adopt_existing_file(self):
        data = (self.web / 'good.dat').read_bytes()
        (self.out / 'good.dat').write_bytes(data)
        result = self.run_list([self.row(sha=digest(data))])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'sha256={digest(data)}', (self.out / 'manifest.txt').read_text())
        self.assertEqual(Handler.requests, [])

    def test_empty_existing_file_is_not_blessed(self):
        (self.out / 'good.dat').touch()
        self.lock('good.dat', digest(b''))
        self.assert_failure(self.run_list([self.row()]))

    def test_truncated_response_does_not_publish(self):
        self.assert_failure(self.run_list([self.row('good.dat', 'truncated')]))
        self.assertFalse((self.out / 'good.dat').exists())

    def test_empty_http_success_does_not_publish(self):
        self.assert_failure(self.run_list([self.row('good.dat', 'empty.dat')]))
        self.assertFalse((self.out / 'good.dat').exists())

    def test_wrong_digest_does_not_publish(self):
        self.assert_failure(self.run_list([self.row(sha='0' * 64)]))
        self.assertFalse((self.out / 'good.dat').exists())

    def test_invalid_archive_is_rejected_even_with_matching_digest(self):
        data = (self.web / 'bad.tar.gz').read_bytes()
        self.assert_failure(self.run_list([self.row('bad.tar.gz', sha=digest(data))]))
        self.assertFalse((self.out / 'bad.tar.gz').exists())

    def test_stale_partial_does_not_replace_download(self):
        stale = self.out / '.good.dat.old.part'
        stale.write_bytes(b'old interrupted bytes')
        result = self.run_list([self.row()])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stale.read_bytes(), b'old interrupted bytes')
        self.assertEqual((self.out / 'good.dat').read_bytes(), (self.web / 'good.dat').read_bytes())

    def test_missing_locked_file_cannot_be_relocked_to_new_bytes(self):
        self.lock('good.dat', digest(b'older upstream bytes'))
        self.assert_failure(self.run_list([self.row()]))
        self.assertFalse((self.out / 'good.dat').exists())
        self.assertEqual((self.out / 'manifest.txt').read_text().count('ARTIFACT '), 1)

    def test_manifest_names_are_literal(self):
        (self.out / 'good.dat').write_bytes(b'partial')
        self.lock('goodXdat', digest(b'partial'))
        self.assert_failure(self.run_list([self.row()]))
        self.assertEqual(Handler.requests, [])

    def test_conflicting_or_invalid_locks_fail_without_transfer(self):
        for values in [('0' * 64, '1' * 64), ('INVALID',), ('0' * 64,)]:
            with self.subTest(values=values):
                (self.out / 'manifest.txt').write_text('')
                for value in values:
                    self.lock('good.dat', value)
                expected = '2' * 64 if len(values) == 1 and values[0] != 'INVALID' else None
                self.assert_failure(self.run_list([self.row(sha=expected)]))
                self.assertEqual(Handler.requests, [])

    def test_invalid_lists_are_rejected_before_any_transfer(self):
        for bad in [('../escape', self.base + '/good.dat'), ('manifest.txt', self.base + '/good.dat'),
                    ('bad name', self.base + '/good.dat'), ('x', 'https://bad url'),
                    ('x', self.base + '/good.dat', 'x'), ('x', self.base + '/good.dat', '', 'extra')]:
            with self.subTest(bad=bad):
                self.assert_failure(self.run_list([self.row(), bad]))
                self.assertEqual(Handler.requests, [])
        self.assert_failure(self.run_list([self.row(), self.row()]))
        self.assert_failure(self.run_list([]))
        self.assert_failure(self.run_list([('not TSV',)]))

    def test_symlink_asset_and_manifest_are_not_followed(self):
        target = self.root / 'target'
        target.write_bytes(b'keep me')
        artifact = self.out / 'good.dat'
        artifact.symlink_to(target)
        self.assert_failure(self.run_list([self.row(sha=digest(b'keep me'))]))
        self.assertEqual(target.read_bytes(), b'keep me')
        artifact.unlink()
        (self.out / 'manifest.txt').unlink()
        (self.out / 'manifest.txt').symlink_to(target)
        self.assert_failure(self.run_list([self.row()]))
        self.assertEqual(target.read_bytes(), b'keep me')

    def test_file_transport_and_missing_file(self):
        result = self.run_list([('file.dat', (self.web / 'good.dat').as_uri()),
                                ('missing.dat', (self.web / 'missing.dat').as_uri())])
        self.assert_failure(result)
        self.assertEqual((self.out / 'file.dat').read_bytes(), (self.web / 'good.dat').read_bytes())

    def test_invalid_manifest_destination_fails_before_transfer(self):
        (self.out / 'manifest.txt').mkdir()
        self.assert_failure(self.run_list([self.row()]))
        self.assertEqual(Handler.requests, [])

    def test_manifest_append_failure_is_not_reported_as_success(self):
        # Only tee is an I/O failure observer; HTTP and curl remain real.
        shim = self.root / 'shim'
        shim.mkdir()
        tee = shim / 'tee'
        tee.write_text('#!/usr/bin/env bash\ntext=$(cat)\n'
                       'if [[ "$text" == ARTIFACT* ]]; then exit 1; fi\n'
                       'printf "%s\\n" "$text" | /usr/bin/tee "$@"\n')
        tee.chmod(0o755)
        previous = os.environ.get('PATH', '')
        try:
            os.environ['PATH'] = str(shim) + os.pathsep + previous
            result = self.run_list([self.row()])
        finally:
            os.environ['PATH'] = previous
        self.assert_failure(result)
        self.assertTrue((self.out / 'good.dat').is_file())
        self.assertNotIn('ARTIFACT ', (self.out / 'manifest.txt').read_text())
        # Fully transferred but unrecorded bytes remain untrusted on replay.
        self.assert_failure(self.run_list([self.row()]))

    def test_default_list_attempts_all_ten_assets_and_aggregates_failures(self):
        # Explicit transport observer: avoid downloading the multi-GB default DBs.
        shim = self.root / 'shim'
        shim.mkdir()
        curl = shim / 'curl'
        calls = self.root / 'calls.txt'
        curl.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "${@: -1}" >> "$CALLS"\nexit 22\n')
        curl.chmod(0o755)
        result = subprocess.run(['bash', str(SCRIPT), '--outdir', str(self.out)],
                                capture_output=True, text=True, timeout=10,
                                env={**os.environ, 'PATH': str(shim) + os.pathsep + os.environ['PATH'],
                                     'CALLS': str(calls)})
        self.assert_failure(result)
        urls = calls.read_text().splitlines()
        self.assertEqual(len(urls), 10)
        self.assertEqual(len(set(urls)), 10)
        self.assertIn('FAILED 10 of 10 artifacts', result.stdout)


if __name__ == '__main__':
    unittest.main()
