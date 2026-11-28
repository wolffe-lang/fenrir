#!/usr/bin/env python3
"""Oracle transport regressions, with no network, package installation or assembler execution.

Prediction: live URLs are tried first; only their HTTP 404 may fetch the SAME
locked bytes from the dated snapshot. All five packages retain two hash checks.
Corrupt bytes, non-404 errors and snapshot failures remain hard failures.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
LIVE = 'https://archive.ubuntu.com/ubuntu/'
SNAPSHOT = 'https://snapshot.ubuntu.com/ubuntu/20261127T000000Z/'
NAMES = ('binutils-x86-64-linux-gnu', 'libbinutils', 'libctf-nobfd0', 'libctf0', 'libsframe1')


class FetchGas(unittest.TestCase):
    def setUp(self):
        (ROOT / 'target').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='fetch-gas-unit-', dir=ROOT / 'target')
        self.work = Path(self.tmp.name)
        self.clef = self.work / 'clef'
        (self.clef / 'ci').mkdir(parents=True)
        self.payloads = {name: ('locked fixture bytes: ' + name).encode() for name in NAMES}
        self.packages = [dict(name=name, version='2.42-4ubuntu2.10', filename=name + '.deb',
                              url=LIVE + 'pool/main/b/binutils/' + name + '.deb',
                              sha256=hashlib.sha256(self.payloads[name]).hexdigest()) for name in NAMES]
        self.write_lock()
        spec = importlib.util.spec_from_file_location('fetch_gas_tested', ROOT / 'tests/backend/fetch-gas.py')
        self.fetch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.fetch)
        self.requests, self.extracts = [], []
        self.status, self.content = {}, {}
        self.number = 0
        self.run_patch = mock.patch.object(self.fetch.subprocess, 'run', side_effect=self.fake_run)
        self.run_patch.start()
        original_hash = hashlib.sha256
        self.hash_patch = mock.patch.object(self.fetch.hashlib, 'sha256', wraps=original_hash)
        self.hashes = self.hash_patch.start()

    def tearDown(self):
        self.hash_patch.stop()
        self.run_patch.stop()
        self.tmp.cleanup()

    def write_lock(self):
        (self.clef / 'ci/oracle-lock.json').write_text(json.dumps({'packages': self.packages}))
        self.routes = {}
        for p in self.packages:
            self.routes[p['url']] = ('live', p['name'])
            if p['url'].startswith(LIVE):
                self.routes[SNAPSHOT + p['url'][len(LIVE):]] = ('snapshot', p['name'])

    def fake_run(self, argv, check=False, **kwargs):
        argv = [str(a) for a in argv]
        if argv[0] == 'curl':
            url = next(a for a in argv if a.startswith('https://'))
            self.requests.append(url)
            route = self.routes[url]
            status = self.status.get(route, 200)
            if status == 200:
                Path(argv[argv.index('-o') + 1]).write_bytes(self.content.get(route, self.payloads[route[1]]))
            code = 0 if status == 200 else (7 if status == 0 else 22)
            result = subprocess.CompletedProcess(argv, code, stdout=str(status), stderr=f'fixture HTTP {status}\n')
            if check:
                result.check_returncode()
            return result
        if argv[:2] == ['dpkg-deb', '-x']:
            self.extracts.append(argv)
            dest = Path(argv[3])
            (dest / 'usr/lib/x86_64-linux-gnu').mkdir(parents=True)
            (dest / 'usr/bin').mkdir(parents=True)
            (dest / 'usr/bin/x86_64-linux-gnu-as').write_bytes(b'fixture only; never executed')
            return subprocess.CompletedProcess(argv, 0)
        raise AssertionError('unexpected external command: ' + repr(argv))

    def invoke(self):
        self.number += 1
        out = self.work / f'out-{self.number}'
        with mock.patch.object(sys, 'argv', ['fetch-gas.py', '--clef-source', str(self.clef), '--out', str(out)]):
            self.fetch.main()
        return json.loads((out / 'gas.json').read_text())

    def test_live_404_same_pinned_bytes_all_five(self):
        self.status = {('live', name): 404 for name in NAMES}
        got = self.invoke()
        expected = [url for p in self.packages for url in (p['url'], SNAPSHOT + p['url'][len(LIVE):])]
        self.assertEqual(self.requests, expected)
        self.assertEqual(got['packages'], self.packages)
        self.assertEqual(len(self.extracts), 5)
        self.assertEqual(self.hashes.call_count, 10, 'two independent hash checks per package')

    def test_live_success_never_uses_snapshot_all_five(self):
        got = self.invoke()
        self.assertEqual(self.requests, [p['url'] for p in self.packages])
        self.assertEqual(got['packages'], self.packages)
        self.assertEqual(self.hashes.call_count, 10)

    def test_snapshot_hash_mismatch_is_hard_failure(self):
        self.status['live', NAMES[0]] = 404
        self.content['snapshot', NAMES[0]] = b'not the locked bytes'
        with self.assertRaises(AssertionError):
            self.invoke()
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.extracts, [])

    def test_live_hash_mismatch_is_not_a_fallback(self):
        self.content['live', NAMES[0]] = b'not the locked bytes'
        with self.assertRaises(AssertionError):
            self.invoke()
        self.assertEqual(self.requests, [self.packages[0]['url']])
        self.assertEqual(self.extracts, [])

    def test_non_404_error_never_falls_back_all_five(self):
        for name in NAMES:
            self.status = {('live', name): 503}
            self.requests.clear()
            with self.assertRaises(subprocess.CalledProcessError):
                self.invoke()
            self.assertFalse(any(url.startswith(SNAPSHOT) for url in self.requests), name)

    def test_network_error_is_not_a_fallback(self):
        self.status['live', NAMES[0]] = 0
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke()
        self.assertEqual(self.requests, [self.packages[0]['url']])

    def test_snapshot_failure_is_hard_failure(self):
        self.status['live', NAMES[0]] = 404
        self.status['snapshot', NAMES[0]] = 503
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke()
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.extracts, [])

    def test_other_origin_404_is_not_a_fallback(self):
        self.packages[0]['url'] = 'https://example.invalid/oracle.deb'
        self.write_lock()
        self.status['live', NAMES[0]] = 404
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke()
        self.assertEqual(self.requests, [self.packages[0]['url']])


class Rows(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        print('PASS fetch-gas-' + test._testMethodName.removeprefix('test_').replace('_', '-'), flush=True)

    def addFailure(self, test, error):
        super().addFailure(test, error)
        print('FAIL fetch-gas-' + test._testMethodName.removeprefix('test_').replace('_', '-'), flush=True)

    def addError(self, test, error):
        super().addError(test, error)
        print('FAIL fetch-gas-' + test._testMethodName.removeprefix('test_').replace('_', '-'), flush=True)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FetchGas)
    result = unittest.TextTestRunner(verbosity=0, resultclass=Rows).run(suite)
    raise SystemExit(not result.wasSuccessful())
