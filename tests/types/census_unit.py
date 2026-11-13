#!/usr/bin/env python3
"""The census gate and classifier, each failure condition shown red."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import censuslib  # noqa: E402


def row(cls, typed, code=None, **extra):
    base = dict(file='corpus/x.lu', cls=cls, construct=None, at=None, oracle='accepted', oracle_code=None,
                oracle_at=None, ast=0, typed=typed, code=code)
    base.update(extra)
    return base


class Gate(unittest.TestCase):
    def test_passing_rows(self):
        rows = [row('core', 0), row('out-of-core', 4, ['F0001', 1, 1, '`match`'], construct='`match`'),
                row('syntax-refused', 2, ['E0201', 1, 1], ast=2),
                row('oracle-refused', 2, ['E0401', 3, 5], oracle='refused', oracle_code='E0401', oracle_at=[3, 5]),
                row('oracle-refused', 0, oracle='refused', oracle_code='E0401', oracle_at=[3, 5]),
                row('out-of-core', 0, construct='module member')]
        self.assertEqual(censuslib.gate(rows), [])

    def test_each_failure_is_named(self):
        cases = [row('core', 2, ['E0401', 1, 1]), row('core', 134), row('out-of-core', 0, construct='`match`'),
                 row('out-of-core', 2, ['E0301', 1, 1], construct='`match`'), row('syntax-refused', 0, ast=2),
                 row('oracle-refused', 2, ['E0402', 3, 5], oracle='refused', oracle_code='E0401', oracle_at=[3, 5]),
                 row('oracle-refused', 2, ['E0401', 4, 5], oracle='refused', oracle_code='E0401', oracle_at=[3, 5]),
                 row('out-of-core', 70, construct='module member')]
        for case in cases:
            problems = censuslib.gate([case])
            self.assertEqual(len(problems), 1, case)
            print('PASS gate-rejects ' + problems[0])

    def test_classifier_names_the_first_construct(self):
        tree = censuslib.Tree('\n'.join([
            'ast/1 "x.lu" root=0',
            'token 0 fn 0 2 1 1 1 3 "fn"', 'token 1 ident 3 4 1 4 1 5 "f"',
            'node 0 Unit 0 1 1 -1 0 4 1 1 1 5', 'node 1 Item 0 2 2 -1 0 4 1 1 1 5',
            'node 2 Enum 0 -1 -1 -1 0 4 1 1 1 5']))
        self.assertEqual(censuslib.Classify(tree, set()).run(), ('`enum`', [1, 1]))


class Prediction(unittest.TestCase):
    class Tree:
        """Small AST-interface fixtures, independent of a compiler binary."""
        def __init__(self, node):
            self.nodes, self.parts = [], []
            def add(n):
                kind, spelling, children = n
                ident = len(self.nodes)
                self.nodes.append((kind, spelling))
                self.parts.append([])
                self.parts[ident] = [add(c) for c in children]
                return ident
            self.root = add(node)
        def kind(self, n): return self.nodes[n][0]
        def spell(self, n): return self.nodes[n][1]
        def tok(self, n): return self.nodes[n][1] if self.kind(n) == 'Literal' else 'ident'
        def children(self, n): return self.parts[n]
        def where(self, n): return [n + 1, 1]

    def classify(self, *items):
        import predictlib
        tree = self.Tree(('Unit', '', [('Item', '', [item]) for item in items]))
        classifier = predictlib.Classify(tree, {'int', 'str', 'List', 'print'})
        return classifier.run(), classifier.features

    def function(self, expr):
        return ('Function', '', [('Name', 'main', []), ('Parameters', '', []),
                                  ('Block', '', [('Tail', '', [expr])])])

    def named_type(self, name):
        return ('NamedType', '', [('Path', '', [('Name', name, [])])])

    def test_enum_payload_and_guarded_match(self):
        variant = ('Variant', '', [('Name', 'Value', []), self.named_type('int')])
        enum = ('Enum', '', [('Name', 'E', []), ('Variants', '', [variant])])
        pattern = ('ConstructorPattern', '', [('Path', '', [('Name', 'Value', [])]),
                    ('NamePattern', '', [('Path', '', [('Name', 'print', [])])])])
        match = ('Match', '', [('Name', 'x', []), ('Arm', '', [pattern,
                    ('Guard', '', [('Literal', 'true', [])]), ('Name', 'print', [])])])
        result, features = self.classify(enum, self.function(match))
        self.assertEqual(result, (None, None))
        self.assertEqual(features, {'enum', 'match'})

    def test_extra_feature_after_enum_is_not_hidden(self):
        payload = ('NamedType', '', [('Path', '', [('Name', 'List', [])]),
                                     ('TypeArguments', '', [self.named_type('int')])])
        enum = ('Enum', '', [('Name', 'E', []), ('Variants', '', [
                    ('Variant', '', [('Name', 'V', []), payload])])])
        result, _ = self.classify(enum)
        self.assertEqual(result[0], 'generic type `List`')

    def implemented(self, *items):
        import predictlib
        tree = self.Tree(('Unit', '', [('Item', '', [item]) for item in items]))
        return predictlib.Implemented(tree, {'int', 'str', 'List', 'print'}).run()

    def test_or_pattern_bindings_are_refused_as_fenrir_refuses_them(self):
        enum = ('Enum', '', [('Name', 'E', []), ('Variants', '', [
                    ('Variant', '', [('Name', 'A', []), self.named_type('int')]),
                    ('Variant', '', [('Name', 'B', [])])])])
        def arm(*alternatives):
            return ('Match', '', [('Name', 'x', []), ('Arm', '', [('OrPattern', '', list(alternatives)),
                                                                 ('Literal', 'true', [])])])
        bare = lambda name: ('NamePattern', '', [('Path', '', [('Name', name, [])])])
        binding = ('ConstructorPattern', '', [('Path', '', [('Name', 'A', [])]), bare('y')])
        self.assertEqual(self.implemented(enum, self.function(arm(bare('A'), bare('B')))), (None, None))
        self.assertEqual(self.implemented(enum, self.function(arm(binding, bare('B'))))[0],
                         'an or-pattern that binds names')

    def test_enum_constructor_is_not_an_arbitrary_method(self):
        enum = ('Enum', '', [('Name', 'E', []), ('Variants', '', [
                    ('Variant', '', [('Name', 'V', [])])])])
        def call(name):
            return ('Call', '', [('Member', '', [('Name', name, []), ('MemberName', 'V', [])]),
                                  ('Arguments', '', [])])
        result, _ = self.classify(enum, self.function(call('E')))
        self.assertEqual(result, (None, None))
        result, _ = self.classify(enum, self.function(call('x')))
        self.assertEqual(result[0], 'method call')

    def test_oracle_refusal_is_not_predicted_native_coverage(self):
        import predictlib
        rows = [dict(file='a', within=True, run=True, baseline=True, native='exit(0)', lupin='exit(0)'),
                dict(file='b', within=True, run=True, baseline=False, native='exit(0)', lupin='exit(0)'),
                dict(file='c', within=True, run=True, baseline=False, native='unsupported', lupin='exit(0)'),
                dict(file='d', within=False, run=True, baseline=False, native='exit(0)', lupin='exit(0)'),
                dict(file='e', within=True, run=False, baseline=False, native='exit(0)', lupin='exit(0)')]
        result = predictlib.summary(rows)
        self.assertEqual(result['new_native_same'], ['b'])
        self.assertEqual(result['reference_interpreter_only'], ['c'])
        self.assertEqual(result['interpreter_parity'], ['a', 'b'])


class Needs(unittest.TestCase):
    """The every-construct walk: each family's labels from fixture trees."""
    class Tree(Prediction.Tree):
        def tok(self, n):
            spelling = self.nodes[n][1]
            if self.kind(n) == 'Literal':
                return 'int' if spelling.isdigit() else spelling
            return 'ident'

    NAMES = {'int', 'str', 'bool', 'List', 'Map', 'print', 'assert'}

    def name(self, spelling):
        return ('Name', spelling, [])

    def named_type(self, name, *args):
        children = [('Path', '', [self.name(name)])]
        if args:
            children.append(('TypeArguments', '', [self.name(a) for a in args]))
        return ('NamedType', '', children)

    def let(self, binder, value, kind='let'):
        return ('Statement', '', [('Item', '', [('Bindings', '', [('BindingKind', kind, []),
                ('Binder', '', [('NamePattern', '', [('Path', '', [self.name(binder)])]), value])])])])

    def call(self, receiver, *args):
        return ('Call', '', [receiver, ('CallArguments', '', [('Argument', '', [a]) for a in args])])

    def generic(self, head, *args):
        return ('Index', '', [self.name(head), ('IndexArguments', '', [('Argument', '', [self.name(a)]) for a in args])])

    def function(self, name, statements, result=None):
        children = [self.name(name), ('Parameters', '', [])]
        if result is not None:
            children.append(('ReturnType', '', [result]))
        children.append(('Block', '', statements))
        return ('Function', '', children)

    def needs(self, *items):
        import needslib
        tree = self.Tree(('Unit', '', [('Item', '', [item]) for item in items]))
        return sorted(needslib.Needs(tree, self.NAMES).run())

    def test_list_construct_push_index_len(self):
        push = ('Call', '', [('Member', '', [('Receiver', '', [('Mode', 'mut', []), self.name('xs')]),
                                             ('MemberName', 'push', [])]),
                             ('CallArguments', '', [('Argument', '', [('Literal', '1', [])])])])
        index = ('Index', '', [self.name('xs'), ('IndexArguments', '', [('Argument', '', [('Literal', '0', [])])])])
        length = ('Member', '', [self.name('xs'), ('MemberName', 'len', [])])
        body = [self.let('xs', self.call(self.generic('List', 'int')), 'var'), ('Statement', '', [push]),
                ('Statement', '', [index]), ('Tail', '', [length])]
        self.assertEqual(self.needs(self.function('main', body)),
                         ['list:`len`', 'list:constructor', 'list:index', 'list:method `push`'])

    def test_map_read_is_a_row(self):
        read = ('Index', '', [self.name('m'), ('IndexArguments', '', [('Argument', '', [('Literal', 'raw', [])])])])
        body = [self.let('m', self.call(self.generic('Map', 'str', 'int'))),
                ('Tail', '', [('Default', '', [read, ('Operator', 'else', []), ('Literal', '0', [])])])]
        self.assertEqual(self.needs(self.function('main', body)),
                         ['err:`else` default', 'map:constructor', 'map:index'])

    def test_fallible_call_and_raise(self):
        row = ('ErrorType', '', [self.named_type('int'), ('ErrorRow', '', [('RowEntry', '', [('Path', '', [self.name('empty')])])])])
        fetch = self.function('fetch', [('Tail', '', [self.name('empty')])], row)
        main = self.function('main', [('Tail', '', [('Default', '', [self.call(self.name('fetch')),
                                                     ('Operator', 'else', []), ('Literal', '0', [])])])])
        self.assertEqual(self.needs(fetch, main),
                         ['err:`else` default', 'err:a call of a fallible function', 'err:error tag', 'err:row type'])

    def test_unread_receiver_is_unknown_not_hidden(self):
        length = ('Member', '', [self.call(self.name('print'), ('Literal', 'raw', [])), ('MemberName', 'len', [])])
        self.assertEqual(self.needs(self.function('main', [('Tail', '', [length])])), ['unknown:`len`'])

    def test_core_program_needs_nothing(self):
        body = [('Tail', '', [self.call(self.name('print'), ('Literal', 'raw', []))])]
        self.assertEqual(self.needs(self.function('main', body)), [])

    def test_summary_groups(self):
        import needslib
        def r(file, families, native='exit(0)', cls='out-of-core'):
            return dict(file=file, families=families, native=native, cls=cls)
        rows = [r('base', [], cls='core'), r('l', ['list']), r('lr', ['list', 'range']), r('m', ['map', 'err']),
                r('e', ['err']), r('ls', ['list', 'str']), r('lm', ['list', 'mode']), r('o', ['list', 'other']),
                r('u', ['list'], native='unsupported')]
        g = needslib.summary(rows)
        self.assertEqual(g['list'], ['l', 'lr'])
        self.assertEqual(g['err'], ['e'])
        self.assertEqual(g['map+err'], ['m', 'e'])
        self.assertEqual(g['list+map+err'], ['l', 'lr', 'm', 'e'])
        self.assertEqual(g['also-strings'], ['ls'])
        self.assertEqual(g['also-modes'], ['lm'])
        self.assertEqual(g['baseline'], ['base'])


class CurrentNeeds(unittest.TestCase):
    """The current core is measured, not the earlier collection prediction."""
    def classify(self, *items):
        import needslib
        fixture = Needs()
        tree = fixture.Tree(('Unit', '', [('Item', '', [item]) for item in items]))
        return sorted(needslib.CurrentNeeds(tree, fixture.NAMES).run())

    def test_implemented_collection_operations_are_not_missing(self):
        f = Needs()
        length = ('Member', '', [f.name('xs'), ('MemberName', 'len', [])])
        body = [f.let('xs', f.call(f.generic('List', 'int')), 'var'), ('Tail', '', [length])]
        self.assertEqual(self.classify(f.function('main', body)), [])

    def test_unimplemented_collection_methods_stay_missing(self):
        f = Needs()
        reserve = f.call(('Member', '', [f.name('xs'), ('MemberName', 'reserve', [])]), ('Literal', '4', []))
        body = [f.let('xs', f.call(f.generic('List', 'int')), 'var'), ('Tail', '', [reserve])]
        self.assertEqual(self.classify(f.function('main', body)), ['list:method `reserve`'])

    def test_strings_and_rendering_are_separate(self):
        f = Needs()
        enum = ('Enum', '', [f.name('E'), ('Variants', '', [('Variant', '', [f.name('V')])])])
        hole = ('String', '', [('Interpolation', '', [('Member', '', [f.name('E'), ('MemberName', 'V', [])])])])
        self.assertEqual(self.classify(enum, f.function('main', [('Tail', '', [hole])])), ['render:enum'])
        length = ('Member', '', [('Literal', 'raw', []), ('MemberName', 'len', [])])
        self.assertEqual(self.classify(f.function('main', [('Tail', '', [length])])), ['str:`len`'])

    def test_tuple_binding_and_tuple_match_are_not_conflated(self):
        f = Needs()
        pat = ('TuplePattern', '', [('WildcardPattern', '', []), ('WildcardPattern', '', [])])
        match = ('Match', '', [('Tuple', '', [('Literal', '1', []), ('Literal', '2', [])]),
                               ('Arm', '', [pat, ('Literal', '3', [])])])
        self.assertEqual(self.classify(f.function('main', [('Tail', '', [match])])), ['pattern:tuple'])

    def test_string_scalar_results_keep_their_types(self):
        f = Needs()
        parsed = f.call(('Member', '', [('Literal', 'raw', []), ('MemberName', 'to_int', [])]))
        fallback = ('Default', '', [parsed, ('Operator', 'else', []), ('Literal', '0', [])])
        text = ('String', '', [('Interpolation', '', [fallback])])
        self.assertEqual(self.classify(f.function('main', [('Tail', '', [text])])), ['str:method `to_int`'])

    def test_conditional_result_does_not_invent_an_unknown_receiver(self):
        f = Needs()
        branch = lambda: ('Block', '', [('Tail', '', [('Literal', 'raw', [])])])
        choice = ('If', '', [('Literal', 'true', []), branch(), branch()])
        length = ('Member', '', [f.name('s'), ('MemberName', 'len', [])])
        body = [f.let('s', choice), ('Tail', '', [length])]
        self.assertEqual(self.classify(f.function('main', body)), ['str:`len`'])

    def test_enum_payload_binding_carries_its_declared_type(self):
        f = Needs()
        enum = ('Enum', '', [f.name('E'), ('Variants', '', [
            ('Variant', '', [f.name('V'), f.named_type('str')])])])
        value = f.call(('Member', '', [f.name('E'), ('MemberName', 'V', [])]), ('Literal', 'raw', []))
        pattern = ('ConstructorPattern', '', [('Path', '', [f.name('V')]),
                     ('NamePattern', '', [('Path', '', [f.name('s')])])])
        match = ('Match', '', [value, ('Arm', '', [pattern,
                    ('Member', '', [f.name('s'), ('MemberName', 'len', [])])])])
        self.assertEqual(self.classify(enum, f.function('main', [('Tail', '', [match])])), ['str:`len`'])

    def test_unknown_receiver_remains_a_blocker(self):
        f = Needs()
        length = ('Member', '', [f.call(f.name('print'), ('Literal', 'raw', [])), ('MemberName', 'len', [])])
        self.assertEqual(self.classify(f.function('main', [('Tail', '', [length])])), ['unknown:`len`'])

    def test_scope_summary_uses_measured_same_and_excludes_oracle_refusals(self):
        import needslib
        rows = [dict(file='base', families=[], baseline=True, native='exit(0)'),
                dict(file='s', families=['str'], baseline=False, native='exit(0)'),
                dict(file='r', families=['render'], baseline=False, native='exit(0)'),
                dict(file='both', families=['str', 'render'], baseline=False, native='exit(0)'),
                dict(file='no', families=['str'], baseline=False, native='unsupported'),
                dict(file='unknown', families=['str', 'unknown'], baseline=False, native='exit(0)')]
        result = needslib.current_summary(rows)
        self.assertEqual(result['baseline'], ['base'])
        self.assertEqual(result['str'], ['s'])
        self.assertEqual(result['render'], ['r'])
        self.assertEqual(result['trap'], [])
        self.assertEqual(result['str+render+trap'], ['s', 'r', 'both'])


class LiveScope(unittest.TestCase):
    """Live typing scope changes without rewriting the frozen prediction model."""
    def classify(self, *items):
        f = Needs()
        tree = f.Tree(('Unit', '', [('Item', '', [item]) for item in items]))
        return censuslib.scope_blocker(tree, f.NAMES | {'char', 'byte', 'str_from_utf8'})[0]

    def test_string_methods_and_scalar_types_are_in_scope(self):
        f = Needs()
        for method in ('to_int', 'rfind', 'split', 'words', 'lines', 'bytes', 'chars'):
            call = f.call(('Member', '', [('Literal', 'raw', []), ('MemberName', method, [])]))
            self.assertIsNone(self.classify(f.function('main', [('Tail', '', [call])])), method)
        for scalar in ('char', 'byte'):
            self.assertIsNone(self.classify(f.function('f', [], f.named_type(scalar))))

    def test_formatting_and_enum_rendering_are_in_scope(self):
        f = Needs()
        enum = ('Enum', '', [f.name('E'), ('Variants', '', [('Variant', '', [f.name('V')])])])
        hole = ('String', '', [('Interpolation', '', [
            ('Member', '', [f.name('E'), ('MemberName', 'V', [])]), ('FormatSpec', '', [])])])
        self.assertIsNone(self.classify(enum, f.function('main', [('Tail', '', [hole])])))

    def test_bound_or_and_tuple_patterns_are_in_scope(self):
        f = Needs()
        enum = ('Enum', '', [f.name('E'), ('Variants', '', [
            ('Variant', '', [f.name(name), f.named_type('int')]) for name in ('A', 'B')])])
        alternatives = [('ConstructorPattern', '', [('Path', '', [f.name(name)]),
            ('NamePattern', '', [('Path', '', [f.name('x')])])]) for name in ('A', 'B')]
        value = f.call(('Member', '', [f.name('E'), ('MemberName', 'A', [])]), ('Literal', '1', []))
        match = ('Match', '', [value, ('Arm', '', [('OrPattern', '', alternatives), f.name('x')])])
        self.assertIsNone(self.classify(enum, f.function('main', [('Tail', '', [match])])))
        tuple_match = ('Match', '', [('Tuple', '', [('Literal', '1', []), ('Literal', '2', [])]),
            ('Arm', '', [('TuplePattern', '', [('WildcardPattern', '', []), ('WildcardPattern', '', [])]),
                         ('Literal', '3', [])])])
        self.assertIsNone(self.classify(f.function('main', [('Tail', '', [tuple_match])])))

    def test_unknown_and_unimplemented_string_features_stay_blockers(self):
        f = Needs()
        for receiver, method in [(('Literal', 'raw', []), 'to_upper'),
                                  (f.call(f.name('print'), ('Literal', 'raw', [])), 'len')]:
            call = f.call(('Member', '', [receiver, ('MemberName', method, [])]))
            self.assertIsNotNone(self.classify(f.function('main', [('Tail', '', [call])])), method)
        utf8 = f.call(f.name('str_from_utf8'), ('List', '', [('Literal', '1', [])]))
        self.assertIsNotNone(self.classify(f.function('main', [('Tail', '', [utf8])])))

    def test_fallback_range_is_not_a_slice_range(self):
        f = Needs()
        fallback = ('Default', '', [
            f.call(('Member', '', [('Literal', 'raw', []), ('MemberName', 'find', [])]), ('Literal', 'raw', [])),
            ('Operator', 'else', []), ('Range', '', [('Literal', '0', []), ('Operator', '..', [])])])
        value = ('Index', '', [('Literal', 'raw', []), ('IndexArguments', '', [('Argument', '', [fallback])])])
        self.assertIsNotNone(self.classify(f.function('main', [('Tail', '', [value])])))

    def test_tuple_type_expression_preserves_element_types(self):
        f = Needs()
        element = ('Tuple', '', [f.name('str'), f.name('int')])
        constructor = f.call(('Index', '', [f.name('List'), ('IndexArguments', '', [('Argument', '', [element])])]))
        index = ('Index', '', [f.name('xs'), ('IndexArguments', '', [('Argument', '', [('Literal', '0', [])])])])
        value = ('Member', '', [index, ('Literal', '0', [])])
        text = ('String', '', [('Interpolation', '', [value])])
        self.assertIsNone(self.classify(f.function('main', [f.let('xs', constructor), ('Tail', '', [text])])))

    def test_handler_binding_is_a_known_row_not_unknown_rendering(self):
        f = Needs()
        result = ('ErrorType', '', [f.named_type('int'), ('ErrorRow', '', [('RowEntry', '', [('Path', '', [f.name('gone')])])])])
        fetch = f.function('fetch', [('Tail', '', [f.name('gone')])], result)
        text = ('String', '', [('Interpolation', '', [f.name('e')])])
        handled = ('Default', '', [f.call(f.name('fetch')), ('Operator', 'else', []),
            ('Handler', '', [('NamePattern', '', [('Path', '', [f.name('e')])]),
                             ('Block', '', [('Statement', '', [text]), ('Tail', '', [('Literal', '0', [])])])])])
        self.assertIsNone(self.classify(fetch, f.function('main', [('Tail', '', [handled])])))

    def test_map_rendering_is_a_named_lowering_refusal_not_a_typing_barrier(self):
        f = Needs()
        value = f.call(f.generic('Map', 'str', 'int'))
        text = ('String', '', [('Interpolation', '', [value])])
        self.assertIsNone(self.classify(f.function('main', [('Tail', '', [text])])))


class MilestoneBound(unittest.TestCase):
    def test_only_explicit_later_milestone_constructs_are_barriers(self):
        import needslib
        self.assertEqual(needslib.later_milestones(['mode:parameter `mut`']), ['F3'])
        self.assertEqual(needslib.later_milestones(['other:`use`', 'other:closure']), ['F4'])
        self.assertEqual(needslib.later_milestones(['other:prelude `fs_exists`']), ['F7'])
        self.assertEqual(needslib.later_milestones(['str:`len`', 'cast:`as`', 'unknown:rendering',
                                                  'other:generic application', 'other:`unsafe`']), [])
        self.assertEqual(needslib.later_milestones(['mode:argument `take`', 'other:generics',
                                                  'other:prelude `os_pid`']), ['F3', 'F4', 'F7'])


class CurrentProjection(unittest.TestCase):
    def test_projection_cli_requires_explicit_observation_and_verdict_inputs(self):
        import subprocess
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run([str(root / 'tools/census'), 'project', '--table', 'unused.json'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('project requires --ast-table and --verdicts', result.stderr)

    def fixture(self):
        ast = 'ast/1 "x.lu" root=0\nnode 0 Unit 0 -1 -1 -1 0 0 1 1 1 1\n'
        capture = [dict(file='corpus/x.lu', sha256='0' * 64, ast_status=0, ast=ast)]
        census = [dict(file='corpus/x.lu', sha256='0' * 64, ast=0, cls='out-of-core',
                       construct='an open range', typed=4, code=['F0001', 1, 1])]
        oracle = [dict(file='corpus/x.lu', sha256='0' * 64, expected='run(exit=0)', member=False,
                       wolf={'verdict': 'exit(0)'}, lupin={'verdict': 'exit(0)'})]
        return capture, census, oracle

    def test_unmodelled_unmeasured_row_is_not_predicted_as_baseline(self):
        import needslib
        capture, census, oracle = self.fixture()
        rows = needslib.project(capture, census, oracle, [], set())
        self.assertFalse(rows[0]['baseline'])
        self.assertEqual(rows[0]['labels'], ['other:unmodelled an open range'])
        self.assertEqual(needslib.current_summary(rows)['str+render+trap'], [])

    def test_execution_establishes_baseline_without_hiding_inventory(self):
        import needslib
        capture, census, oracle = self.fixture()
        verdicts = [dict(file='corpus/x.lu', verdict='same')]
        rows = needslib.project(capture, census, oracle, verdicts, set())
        self.assertTrue(rows[0]['baseline'])
        self.assertEqual(rows[0]['labels'], [])
        self.assertEqual(needslib.current_summary(rows)['baseline'], ['corpus/x.lu'])

    def test_stale_or_incomplete_capture_is_rejected(self):
        import needslib
        capture, census, oracle = self.fixture()
        with self.assertRaises(ValueError):
            needslib.project([], census, oracle, [], set())
        with self.assertRaises(ValueError):
            needslib.project(capture + capture, census, oracle, [], set())
        capture[0]['sha256'] = '1' * 64
        with self.assertRaises(ValueError):
            needslib.project(capture, census, oracle, [], set())


if __name__ == '__main__':
    unittest.main(verbosity=1)
