#!/usr/bin/env -S python3 -I
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from frame import ROOT, extract, twice
from differlib import (comparison, corpus_rows, directives, fenrir_verdict,
                       lupin_observation, native_observation, oracle_relation, reconcile)
from constructs import inventory, lex


class Oracle(unittest.TestCase):
    def test_member_census_and_header_expectations(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as work:
            root = Path(work) / 'corpus'
            root.mkdir()
            (root / 'entry.lu').write_text('//! check: run(exit=0)\n//! phase: run\nfn main() -> int { 0 }\n')
            (root / 'member.lu').write_text('fn sibling() {}\n')
            rows = corpus_rows(root)
            self.assertEqual([r['member'] for r in rows], [False, True])
            self.assertEqual(rows[0]['expected'], 'run(exit=0)')
            self.assertEqual(len(rows[0]['sha256']), 64)
            (root / 'bad.lu').write_text('//! member: true\n//! phase: run\n')
            with self.assertRaises(ValueError):
                corpus_rows(root)

    def test_trap_site_and_program_output_are_separate(self):
        observed = native_observation((134, b'before\n', b'wolf-trap: assert\n  at corpus/x.lu:9:4\n', False), None, [])
        self.assertEqual(observed['verdict'], 'trap(assert)')
        self.assertEqual(observed['trap_site'], {'file': 'corpus/x.lu', 'line': 9, 'column': 4})
        self.assertEqual(base64.b64decode(observed['stdout_base64']), b'before\n')
        self.assertEqual(observed['stdout_sha256'], hashlib.sha256(b'before\n').hexdigest())
        other = dict(observed, trap_site={'file': 'corpus/x.lu', 'line': 1, 'column': 1})
        self.assertEqual(fenrir_verdict(observed, other), 'differs')
        self.assertEqual(fenrir_verdict(observed, dict(observed, trap_message='changed')), 'differs')

    def test_compiler_ice_refusal_and_legal_program_exit(self):
        oracle = {'verdict': 'exit(0)', 'stdout': ''}
        self.assertEqual(fenrir_verdict(oracle, {'verdict': 'refused', 'build_exit': 2}), 'fenrir-refuses')
        self.assertEqual(fenrir_verdict(oracle, {'verdict': 'refused', 'build_exit': 70}), 'fenrir-crashes')
        self.assertEqual(native_observation((70, b'', b'', False), None, [])['verdict'], 'exit(70)')
        self.assertEqual(native_observation((-11, b'', b'', False), None, [])['verdict'], 'crash')
        self.assertEqual(native_observation((-9, b'', b'', True), None, [])['verdict'], 'timeout')

    def test_oracle_gap_is_not_dynamic_agreement(self):
        def obs(verdict, digest=None):
            return {'verdict': verdict, 'stdout_sha256': digest}
        self.assertEqual(oracle_relation(obs('unsupported'), obs('unsupported')), 'scope-gap')
        self.assertEqual(oracle_relation(obs('pass'), obs('exit(0)')), 'not-dynamically-comparable')
        self.assertEqual(oracle_relation(obs('exit(0)', 'a'), obs('exit(0)', 'b')), 'differs')
        self.assertEqual(oracle_relation(obs('tool-error'), obs('exit(0)')), 'oracle-error')

    def test_bad_protocol_is_rejected(self):
        with self.assertRaises(ValueError):
            lupin_observation((0, json.dumps({'protocol': 99}).encode(), b'', False), None, [])

    def test_digest_plant_is_rejected_before_use(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as work:
            path = Path(work) / 'archive'
            path.write_bytes(b'pinned')
            digest = twice(path)
            path.write_bytes(b'planted')
            with self.assertRaises(ValueError):
                twice(path, digest)

    def test_recorded_cli_regressions_use_real_run_argv_and_do_not_mix(self):
        import differlib
        fixtures = json.loads((ROOT / 'tests/oracle-cli-regression.json').read_text())['rows']
        for row in fixtures:
            calls = []
            def replay(args, cwd, env, timeout):
                calls.append(list(map(str, args)))
                if args[1:] == ['run', row['file']]:
                    record = row['native_protocol']
                    return 0, record['stdout_inline'].encode(), b'', False
                return 2, b'', b'wolf run: unknown flag `--native`\n', False
            native = differlib.observe_native('wolf', row['file'], '.', {}, 30, [], runner=replay)
            lupus = lupin_observation((0, json.dumps(row['lupin_protocol']).encode(), b'', False), None, [])
            self.assertEqual(calls, [['wolf', 'run', row['file']]])
            self.assertEqual(oracle_relation(native, lupus), 'same-observed', row['file'])
        # An invalid command is not repaired by borrowing a successful record.
        def invalid(args, cwd, env, timeout):
            if args[1] == 'run':
                return 2, b'', b'wolf run: unknown flag `--native`\n', False
            return 0, json.dumps(fixtures[0]['native_protocol']).encode(), b'', False
        observed = differlib.observe_native('wolf', fixtures[0]['file'], '.', {}, 30, [], runner=invalid)
        self.assertEqual(observed['verdict'], 'tool-error')
        self.assertEqual(observed['stdout'], '')
        self.assertEqual(observed['exit'], 2)

    def test_repeat_observations_are_retained_and_changes_named(self):
        import copy
        row = dict(file='corpus/hello.lu', sha256='source', member=False, directives={}, expected='run(exit=0)', phase='run',
                   wolf={'verdict': 'exit(0)', 'stdout_sha256': 'first'},
                   lupin={'verdict': 'exit(0)', 'stdout_sha256': 'first'}, relation='same-observed')
        first = dict(format=2, identity={'pin': 'one'}, complete=True, rows=[row])
        second = copy.deepcopy(first)
        second['rows'][0]['wolf']['stdout_sha256'] = 'changed'
        second['rows'][0]['relation'] = 'differs'
        result = reconcile(first, second)
        self.assertEqual(result['recordings'], 2)
        self.assertEqual(result['repeat_changes'], ['corpus/hello.lu'])
        self.assertEqual(result['rows'][0]['wolf']['stdout_sha256'], 'first')
        self.assertEqual(result['rows'][0]['repeat_wolf']['stdout_sha256'], 'changed')
        second['identity']['pin'] = 'two'
        with self.assertRaises(ValueError):
            reconcile(first, second)

    def test_construct_lexer_ignores_comments_and_names_literals(self):
        kinds = [kind for kind, _ in lex('/* outer /* enum */ nested */ fn f() { let s = r#"enum"#; 1 + 2.0 }')]
        self.assertNotIn('keyword:enum', kinds)
        self.assertIn('keyword:fn', kinds)
        self.assertIn('literal:raw-string', kinds)
        self.assertIn('literal:float', kinds)
        self.assertIn('operator:arithmetic-or-pointer', kinds)


if __name__ == '__main__':
    (ROOT / 'target').mkdir(exist_ok=True)
    unittest.main()
