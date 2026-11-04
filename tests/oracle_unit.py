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
            self.assertEqual(rows[1]['inherited_expectation']['entry'], 'corpus/entry.lu')
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

    def test_nonoracle_tool_pin_changes_leave_oracle_identity_fresh(self):
        import copy
        import importlib.machinery
        import importlib.util
        import tomllib
        loader = importlib.machinery.SourceFileLoader('differ_identity_fixture', str(ROOT / 'tools/differ'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        tool = importlib.util.module_from_spec(spec)
        loader.exec_module(tool)
        original = (ROOT / 'wolf-toolchain.toml').read_text()
        manifest = tomllib.loads(original)
        clef = next(p for p in manifest['artifact'] if p['name'] == 'clef')
        wolf = next(p for p in manifest['artifact'] if p['name'] == 'wolf-x86_64-unknown-linux-gnu')
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as work:
            path = Path(work) / 'wolf-toolchain.toml'
            path.write_text(original)
            tool.ROOT = Path(work)
            tool.pins = lambda: tomllib.loads(path.read_text())
            captured = tool.identity()
            path.write_text(original.replace(clef['sha256'], '0' * 64))
            self.assertEqual(tool.identity(), captured)
            path.write_text(original.replace(wolf['sha256'], '1' * 64))
            self.assertNotEqual(tool.identity(), captured)

    def test_root_domain_death_compares_nonzero_class_only_when_declared(self):
        import copy
        row = json.loads((ROOT / 'tests/oracle-root-status-regression.json').read_text())['row']
        first = dict(format=4, identity={'pin': 'fixture'}, complete=False, rows=[row],
                     counts={'same-observed': 0, 'differs': 1, 'scope-gap': 0,
                             'not-dynamically-comparable': 0, 'oracle-error': 0, 'module-member': 0})
        merged = reconcile(first, copy.deepcopy(first))
        self.assertEqual(merged['rows'][0]['relation'], 'same-observed')
        self.assertEqual(merged['counts']['same-observed'], 1)
        self.assertEqual(merged['rows'][0]['wolf']['exit'], 121)
        self.assertEqual(merged['rows'][0]['lupin']['exit'], 1)
        candidate = dict(row, fenrir=dict(row['lupin'], build_exit=0))
        self.assertEqual(comparison({'rows': [candidate]})['rows'][0]['verdict'], 'same')
        for changed in (
            dict(candidate, directives={'conforms': ''}),
            dict(candidate, expected='run(exit=0)'),
            dict(candidate, fenrir={'verdict': 'trap(assert)', 'build_exit': 0}),
            dict(candidate, fenrir={'verdict': 'refused', 'build_exit': 2}),
        ):
            self.assertNotEqual(comparison({'rows': [changed]})['rows'][0]['verdict'], 'same')

    def test_program_exit_two_with_diagnostic_like_stderr_uses_protocol(self):
        import differlib
        text = b'usage\n'
        record = dict(protocol=1, impl='fixture', impl_version='1', commit='fixture', file='case.lu',
                      phase_reached='run', seeded=False, diagnostics=[], verdict='exit(2)',
                      stdout_inline=text.decode(), stdout_sha256=hashlib.sha256(text).hexdigest())
        def replay(args, cwd, env, timeout):
            if args[1] == 'run':
                return 2, text, b'error[E0401]: unknown flag chosen by the program\n', False
            return 0, json.dumps(record).encode(), b'', False
        observed = differlib.observe_native('wolf', 'case.lu', '.', {}, 30, [], runner=replay)
        self.assertEqual(observed['verdict'], 'exit(2)')
        self.assertEqual(observed['stdout'], text.decode())
        record['stdout_inline'] = 'different invocation'
        record['stdout_sha256'] = hashlib.sha256(b'different invocation').hexdigest()
        self.assertEqual(differlib.observe_native('wolf', 'case.lu', '.', {}, 30, [], runner=replay)['verdict'], 'tool-error')

    def test_warning_code_does_not_reject_a_successful_native_run(self):
        row = json.loads((ROOT / 'tests/oracle-warning-regression.json').read_text())['row']
        raw = row['native_run']
        observed = native_observation((raw['exit'], base64.b64decode(raw['stdout_base64']), raw['stderr'].encode(), False), None, [])
        self.assertEqual(observed['verdict'], 'exit(0)')
        self.assertEqual(observed['stdout'], 'one\n')
        self.assertEqual(oracle_relation(observed, row['lupin']), 'same-observed')
        # A program's own stderr may look exactly like a compiler diagnostic.
        self.assertEqual(native_observation((1, b'', b'error[E0401]: program text\n', False), None, [])['verdict'], 'exit(1)')

    def test_oracle_package_tree_is_unchanged_after_each_invocation(self):
        import differlib
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as work:
            root = Path(work)
            package, private = root / 'package', root / 'private'
            package.mkdir()
            private.mkdir()
            source = package / 'main.lu'
            source.write_text('unchanged source')
            def owned(args, cwd, env, timeout):
                (Path(cwd) / 'native-program').write_bytes(b'owned output')
                return 0, b'ok', b'', False
            checked = differlib.package_guard(package, owned)
            before = differlib.package_snapshot(package)
            checked(['fixture'], private, {}, 30)
            self.assertEqual(before, differlib.package_snapshot(package))
            self.assertEqual(checked.invocations, 1)
            self.assertEqual(checked.digest, checked.after_digest)
            def escaped(args, cwd, env, timeout):
                source.write_text('an oracle changed source outside its private directory')
                return 0, b'ok', b'', False
            with self.assertRaisesRegex(ValueError, 'changed the read-only package'):
                differlib.package_guard(package, escaped)(['fixture'], private, {}, 30)

    def test_readonly_package_requires_private_output_and_no_cache(self):
        import differlib
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as work:
            root = Path(work)
            package, cwd = root / 'package', root / 'cwd'
            package.mkdir()
            cwd.mkdir()
            source = package / 'hello.lu'
            source.write_text('fn main() { print("hello, wolf") }\n')
            source.chmod(0o444)
            package.chmod(0o555)
            before = [(p.name, p.read_bytes()) for p in package.iterdir()]
            record = json.loads((ROOT / 'tests/oracle-cli-regression.json').read_text())['rows'][0]['native_protocol']
            def replay(args, invocation_cwd, env, timeout):
                if args[1] == 'run':
                    if '--no-cache' not in args or '-o' not in args:
                        # Measured with pinned stage 0 on an actually read-only package.
                        return 2, b'', b'wolf run: create package/.lu-cache/bin: Permission denied (os error 13)\n', False
                    output = Path(args[args.index('-o') + 1])
                    self.assertEqual(output.parent, Path(invocation_cwd))
                    output.write_bytes(b'private executable')
                    return 0, b'hello, wolf\n', b'', False
                return 0, json.dumps(record).encode(), b'', False
            observed = differlib.observe_native('wolf', source, cwd, {}, 30, [], runner=replay)
            self.assertEqual(observed['verdict'], 'exit(0)')
            self.assertEqual(observed['stdout'], 'hello, wolf\n')
            self.assertEqual(before, [(p.name, p.read_bytes()) for p in package.iterdir()])
            package.chmod(0o755)

    def test_cleanup_does_not_follow_directory_symlinks(self):
        import differlib
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as work:
            outside = Path(work) / 'outside'
            outside.mkdir()
            outside.chmod(0o555)
            owned = Path(work) / 'owned'
            owned.mkdir()
            (owned / 'link').symlink_to(outside, target_is_directory=True)
            differlib.remove_owned_scratch(owned)
            actual = outside.stat().st_mode & 0o777
            outside.chmod(0o755)
            self.assertEqual(actual, 0o555)

    def test_contexts_and_read_only_package_are_owned(self):
        import differlib
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as work:
            root = Path(work)
            first, first_env = differlib.isolated_context(root, 'first', {})
            second, second_env = differlib.isolated_context(root, 'second', {})
            (first / 'leftover').write_text('one oracle wrote this')
            self.assertFalse((second / 'leftover').exists())
            self.assertNotEqual(first_env['HOME'], second_env['HOME'])
            self.assertNotEqual(first_env['TMPDIR'], second_env['TMPDIR'])
            package = root / 'package'
            package.mkdir()
            (package / 'main.lu').write_text('source')
            differlib.freeze_package(package)
            self.assertEqual((package / 'main.lu').stat().st_mode & 0o222, 0)
            differlib.remove_owned_scratch(package)
            self.assertFalse(package.exists())

    def test_protocol_path_normalization_never_changes_program_output(self):
        text = '/private-row/path\n'
        record = dict(protocol=1, impl='fixture', impl_version='1', commit='fixture', file='/private-row/main.lu',
                      phase_reached='run', seeded=False, diagnostics=[], verdict='exit(0)',
                      stdout_inline=text, stdout_sha256=hashlib.sha256(text.encode()).hexdigest())
        observed = lupin_observation((0, json.dumps(record).encode(), b'', False), None, [('/private-row', '<scratch>')])
        self.assertEqual(observed['record']['file'], '<scratch>/main.lu')
        self.assertEqual(observed['record']['stdout_inline'], text)
        self.assertEqual(observed['stdout'], text)
        self.assertEqual(native_observation((2, b'', b'error[E0401]: program text', False), None, [])['verdict'], 'exit(2)')

    def test_leftover_file_cannot_change_classification_invocation(self):
        import differlib
        with tempfile.TemporaryDirectory(dir=ROOT / 'target') as work:
            native, classify = Path(work) / 'native', Path(work) / 'classify'
            native.mkdir()
            classify.mkdir()
            record = dict(protocol=1, impl='fixture', impl_version='1', commit='fixture', file='case.lu',
                          phase_reached='run', seeded=False, diagnostics=[], verdict='exit(2)',
                          stdout_inline='usage\n', stdout_sha256=hashlib.sha256(b'usage\n').hexdigest())
            def replay(args, cwd, env, timeout):
                marker = Path(cwd) / 'leftover'
                if args[1] == 'run':
                    marker.write_text('state left by first invocation')
                    return 2, b'usage\n', b'', False
                answer = dict(record, verdict='exit(1)' if marker.exists() else 'exit(2)')
                return 0, json.dumps(answer).encode(), b'', False
            observed = differlib.observe_native('wolf', 'case.lu', native, {}, 30, [], runner=replay,
                                                classification_context=(classify, {}))
            self.assertEqual(observed['verdict'], 'exit(2)')
            self.assertEqual(observed['stdout'], 'usage\n')
            self.assertFalse((classify / 'leftover').exists())

    def test_recorded_cli_regressions_use_real_run_argv_and_do_not_mix(self):
        import differlib
        fixtures = json.loads((ROOT / 'tests/oracle-cli-regression.json').read_text())['rows']
        for row in fixtures:
            calls = []
            def replay(args, cwd, env, timeout):
                calls.append(list(map(str, args)))
                if args[1:4] == ['run', '--no-cache', '-o'] and args[-1] == row['file']:
                    record = row['native_protocol']
                    return 0, record['stdout_inline'].encode(), b'', False
                return 2, b'', b'wolf run: unknown flag `--native`\n', False
            native = differlib.observe_native('wolf', row['file'], '.', {}, 30, [], runner=replay)
            lupus = lupin_observation((0, json.dumps(row['lupin_protocol']).encode(), b'', False), None, [])
            self.assertEqual(calls, [['wolf', 'run', '--no-cache', '-o', 'native-program', row['file']]])
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
        first = dict(format=4, identity={'pin': 'one'}, complete=True, rows=[row])
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
