#!/usr/bin/env -S python3 -I
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Gates(unittest.TestCase):
    def invoke(self, tool, *args):
        return subprocess.run([str(ROOT / 'tools' / tool), *map(str, args)], capture_output=True, text=True)

    def test_subset_rejects_added_construct(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as temp:
            source = Path(temp) / 'src'
            source.mkdir()
            (source / 'main.lu').write_text('trait Planted {}\n')
            result = self.invoke('check-subset', '--source', source)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('subset', result.stdout)

    def test_diagnostics_both_directions(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as temp:
            source = Path(temp) / 'src'
            source.mkdir()
            catalog = Path(temp) / 'catalog.md'
            catalog.write_text('# Empty\n')
            (source / 'bad.lu').write_text('fn f() { eprint("E9999: planted") }\n')
            result = self.invoke('check-diagnostics', '--source', source, '--catalog', catalog)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('E9999', result.stdout)
            (source / 'bad.lu').write_text('// E9999: only a comment\n')
            catalog.write_text('| `E9999` | planted unused code |\n')
            result = self.invoke('check-diagnostics', '--source', source, '--catalog', catalog)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('E9999', result.stdout)

    def test_determinism_red_and_green(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as temp:
            a, b = Path(temp) / 'a', Path(temp) / 'b'
            a.write_bytes(b'one')
            b.write_bytes(b'one')
            self.assertEqual(self.invoke('check-determinism', '--compare', a, b).returncode, 0)
            b.write_bytes(b'two')
            result = self.invoke('check-determinism', '--compare', a, b)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('determinism', result.stdout)

    def test_skip_loud_and_strict(self):
        loose = self.invoke('check-skips', '--skip', 'planted environment gap')
        self.assertEqual(loose.returncode, 0)
        self.assertIn('SKIP planted environment gap', loose.stdout)
        strict = self.invoke('check-skips', '--strict', '--skip', 'planted environment gap')
        self.assertNotEqual(strict.returncode, 0)
        self.assertIn('SKIP planted environment gap', strict.stdout)

    def test_subset_stale_counts_unproved_claim_and_closed_gap(self):
        import re
        original = (ROOT / 'docs/SUBSET.md').read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as temp:
            catalog = Path(temp) / 'subset.md'
            variants = [
                ('stale used count', re.sub(r'(\| `identifier` \| )\d+', r'\g<1>999999', original)),
                ('compiled claim lacks passing row', original.replace('| no |', '| F1:tests/subset/missing.py |', 1)),
                ('compiled subset gap', original.replace('close_gap: false', 'close_gap: true')),
            ]
            for expected, text in variants:
                catalog.write_text(text)
                result = self.invoke('check-subset', '--subset', catalog)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout)

    def test_named_fir_diagnostic_requires_catalog_entry(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as temp:
            source = Path(temp) / 'src'
            source.mkdir()
            catalog = Path(temp) / 'catalog.md'
            catalog.write_text('# Empty\n')
            (source / 'bad.lu').write_text('fn f() { eprint("FIR_TYPE: planted") }\n')
            result = self.invoke('check-diagnostics', '--source', source, '--catalog', catalog)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('FIR_TYPE', result.stdout)
            catalog.write_text('| `FIR_TYPE` | mismatched FIR type |\n')
            self.assertEqual(self.invoke('check-diagnostics', '--source', source, '--catalog', catalog).returncode, 0)

    def test_refusal_is_not_agreement(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as temp:
            table = Path(temp) / 'observations.json'
            table.write_text(json.dumps({'rows': [{'file': 'hello.lu', 'expected': 'run(exit=0)',
                'wolf': {'verdict': 'exit(0)', 'stdout': ''},
                'lupin': {'verdict': 'exit(0)', 'stdout': ''},
                'fenrir': {'verdict': 'refused', 'stdout': '', 'exit': 2}}]}))
            result = self.invoke('differ', 'compare', '--input', table)
            self.assertNotEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertEqual(data['rows'][0]['verdict'], 'fenrir-refuses')
            self.assertEqual(data['coverage']['same'], 0)

    def test_selection_narrows_and_names_known_rows(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as temp:
            table = Path(temp) / 'observations.json'
            same = {'verdict': 'exit(0)', 'stdout': ''}
            table.write_text(json.dumps({'identity': {}, 'rows': [
                {'file': 'corpus/a.lu', 'expected': 'run(exit=0)', 'wolf': same, 'lupin': same, 'fenrir': same},
                {'file': 'corpus/b.lu', 'expected': 'run(exit=0)', 'wolf': same, 'lupin': same,
                 'fenrir': {'verdict': 'refused', 'stdout': '', 'exit': 4, 'build_exit': 4}}]}))
            chosen = Path(temp) / 'core.json'
            chosen.write_text(json.dumps({'core': ['corpus/a.lu']}))
            compact = Path(temp) / 'verdicts.json'
            result = self.invoke('differ', 'compare', '--input', table, '--select', chosen, '--table', compact)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(compact.read_text())
            self.assertEqual([r['file'] for r in data['rows']], ['corpus/a.lu'])
            self.assertEqual(data['counts']['same'], 1)
            whole = self.invoke('differ', 'compare', '--input', table)
            self.assertNotEqual(whole.returncode, 0)
            self.assertEqual(json.loads(whole.stdout)['counts']['fenrir-refuses'], 1)
            chosen.write_text(json.dumps({'rows': [{'file': 'corpus/a.lu', 'cls': 'core'}, {'file': 'corpus/b.lu', 'cls': 'out-of-core'}]}))
            census = self.invoke('differ', 'compare', '--input', table, '--select', chosen)
            self.assertEqual(census.returncode, 0, census.stderr)
            self.assertEqual([r['file'] for r in json.loads(census.stdout)['rows']], ['corpus/a.lu'])
            chosen.write_text(json.dumps(['corpus/missing.lu']))
            self.assertNotEqual(self.invoke('differ', 'compare', '--input', table, '--select', chosen).returncode, 0)


class SourcePins(unittest.TestCase):
    def setUp(self):
        import importlib.machinery
        import importlib.util
        loader = importlib.machinery.SourceFileLoader('pin_toolchain', str(ROOT / 'tools/pin-toolchain'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.tool = importlib.util.module_from_spec(spec)
        loader.exec_module(self.tool)

    def test_repin_changes_only_selected_source(self):
        import tomllib
        from unittest.mock import patch
        original = (ROOT / 'wolf-toolchain.toml').read_text()
        revision = '6cec81a' + '0' * 33
        with patch.object(self.tool, 'stable', return_value={'sha': revision}) as api, \
             patch.object(self.tool, 'download', return_value=Path('sealed.tar.gz')) as download, \
             patch.object(self.tool, 'twice', return_value='1' * 64) as digest:
            changed = self.tool.repin_source(original, 'ligature', '6cec81a')
        api.assert_called_once_with('repos/wolffe-lang/ligature/commits/6cec81a')
        url = f'https://codeload.github.com/wolffe-lang/ligature/tar.gz/{revision}'
        download.assert_called_once_with(url, self.tool.STAGE / 'downloads' / f'ligature-{revision}.tar.gz')
        digest.assert_called_once_with(Path('sealed.tar.gz'))
        before, after = tomllib.loads(original), tomllib.loads(changed)
        for old, new in zip(before['artifact'], after['artifact'], strict=True):
            if old['name'] == 'ligature':
                self.assertEqual(new, dict(old, rev=revision, url=url, sha256='1' * 64))
            else:
                self.assertEqual(old, new)

    def test_repin_refuses_non_backend_sources(self):
        from unittest.mock import patch
        original = (ROOT / 'wolf-toolchain.toml').read_text()
        with patch.object(self.tool, 'stable') as api:
            for name in ('reference', 'runtime', 'unknown'):
                with self.assertRaises(ValueError):
                    self.tool.repin_source(original, name, '6cec81a')
        api.assert_not_called()

    def test_repin_refuses_unresolved_revision(self):
        from unittest.mock import patch
        original = (ROOT / 'wolf-toolchain.toml').read_text()
        with patch.object(self.tool, 'stable', return_value={'sha': 'trunk'}), \
             patch.object(self.tool, 'download') as download:
            with self.assertRaises(ValueError):
                self.tool.repin_source(original, 'ligature', '6cec81a')
        download.assert_not_called()


if __name__ == '__main__':
    (ROOT / 'target').mkdir(exist_ok=True)
    unittest.main()
