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


if __name__ == '__main__':
    (ROOT / 'target').mkdir(exist_ok=True)
    unittest.main()
