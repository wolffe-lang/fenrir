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
                if spelling.replace('.', '', 1).isdigit() and '.' in spelling:
                    return 'float'
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
        # `str_from_utf8` is in the core as a call; as a value it is the
        # builtin-as-value refusal every prelude function answers.
        utf8 = f.call(f.name('str_from_utf8'), ('List', '', [('Literal', '1', [])]))
        self.assertIsNone(self.classify(f.function('main', [('Tail', '', [utf8])])))
        self.assertIsNotNone(self.classify(f.function('main', [f.let('f', f.name('str_from_utf8')), ('Tail', '', [f.name('f')])])))

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

    def test_multiline_interpolation_retains_its_named_scope_refusal(self):
        f = Needs()
        class MultilineTree(f.Tree):
            def tok(self, node):
                return 'multi-open' if self.kind(node) == 'String' else super().tok(node)
        text = ('String', '', [('Interpolation', '', [('Literal', '1', [])])])
        tree = MultilineTree(('Unit', '', [('Item', '', [f.function('main', [('Tail', '', [text])])])]))
        self.assertEqual(censuslib.scope_blocker(tree, f.NAMES)[0], 'interpolation in a multiline string')

    def test_nested_receiver_walk_does_not_revisit_subtrees(self):
        f = Needs()
        value = ('Literal', 'raw', [])
        for _ in range(12):
            value = ('Index', '', [value, ('IndexArguments', '', [('Argument', '', [
                ('Range', '', [('Literal', '0', []), ('Operator', '..', []), ('Literal', '1', [])])])])])
        class CountingTree(f.Tree):
            visits = 0
            def kind(self, node):
                self.visits += 1
                return super().kind(node)
        tree = CountingTree(('Unit', '', [('Item', '', [f.function('main', [('Tail', '', [value])])])]))
        self.assertEqual(censuslib.scope_blocker(tree, f.NAMES), (None, None))
        self.assertLess(tree.visits, 100 * len(tree.nodes))

    def test_map_header_methods_keep_their_result_types(self):
        f = Needs()
        for method in ('len', 'count', 'is_empty', 'clear'):
            value = f.call(('Member', '', [f.name('m'), ('MemberName', method, [])]))
            text = ('String', '', [('Interpolation', '', [value])])
            self.assertIsNone(self.classify(f.function('main', [
                f.let('m', f.call(f.generic('Map', 'str', 'int'))), ('Tail', '', [text])])), method)

    def test_map_rendering_is_a_named_lowering_refusal_not_a_typing_barrier(self):
        f = Needs()
        value = f.call(f.generic('Map', 'str', 'int'))
        text = ('String', '', [('Interpolation', '', [value])])
        self.assertIsNone(self.classify(f.function('main', [('Tail', '', [text])])))


class NumericScope(unittest.TestCase):
    """New live integer scope must not widen the sealed historical model."""
    def classify(self, *items):
        f = Needs()
        tree = f.Tree(('Unit', '', [('Item', '', [item]) for item in items]))
        return censuslib.scope_blocker(tree, f.NAMES | {'char', 'byte', 'str_from_utf8',
                                                     'i8', 'i16', 'u16', 'u32', 'wrapping', 'f64', 'f32'})[0]
    def test_all_integer_widths_are_live(self):
        f = Needs()
        for kind in ('i8', 'i16', 'u16', 'u32'):
            self.assertIsNone(self.classify(f.function('f', [], f.named_type(kind))), kind)

    def test_integer_cast_target_is_a_type_not_an_unknown_value(self):
        f = Needs()
        cast = ('Cast', '', [('Literal', '65', []), ('Operator', 'as', []), f.named_type('char')])
        text = ('String', '', [('Interpolation', '', [cast])])
        self.assertIsNone(self.classify(f.function('main', [('Tail', '', [text])])))

    def test_wrapping_is_numeric_not_user_generics(self):
        f = Needs()
        inner = f.generic('wrapping', 'u64')
        value = f.call(('Index', '', [f.name('List'), ('IndexArguments', '', [('Argument', '', [inner])])]))
        self.assertIsNone(self.classify(f.function('main', [('Tail', '', [value])])))

    def test_integer_operators_are_live(self):
        f = Needs()
        for op in ('&', '|', '^', '<<', '>>'):
            value = ('Binary', '', [('Literal', '1', []), ('Operator', op, []), ('Literal', '1', [])])
            self.assertIsNone(self.classify(f.function('main', [('Tail', '', [value])])), op)

    def test_float_cast_is_live(self):
        f = Needs()
        cast = ('Cast', '', [('Literal', '1', []), ('Operator', 'as', []), f.named_type('f64')])
        self.assertIsNone(self.classify(f.function('main', [('Tail', '', [cast])])))

    def test_float_literal_is_live(self):
        f = Needs()
        text = ('String', '', [('Interpolation', '', [('Literal', '1.5', [])])])
        self.assertIsNone(self.classify(f.function('main', [('Tail', '', [text])])))

    def test_float_remainder_is_a_blocker(self):
        f = Needs()
        rem = ('Binary', '', [('Literal', '7.5', []), ('Operator', '%', []), ('Literal', '3.0', [])])
        self.assertEqual(self.classify(f.function('main', [('Tail', '', [rem])])), 'float remainder')

    def test_missing_field_of_a_known_struct_stays_in_scope(self):
        # The checker refuses `c.radbus` itself (E0403); an unknown name elsewhere stays a blocker.
        f = Needs()
        shape = ('Struct', '', [f.name('Circle'), ('Fields', '', [('Field', '', [f.name('radius'), f.named_type('int')])])])
        value = ('StructLiteral', '', [f.name('Circle'), ('FieldInit', '', [f.name('radius'), ('Literal', '2', [])])])
        typo = ('Member', '', [f.name('c'), ('MemberName', 'radbus', [])])
        main = f.function('main', [f.let('c', value), ('Tail', '', [typo])])
        self.assertIsNone(self.classify(shape, main))
        unknown = ('Member', '', [f.call(f.name('print'), ('Literal', 'raw', [])), ('MemberName', 'radbus', [])])
        self.assertIsNotNone(self.classify(f.function('main', [('Tail', '', [unknown])])))

    def test_f32_cast_is_still_a_blocker(self):
        f = Needs()
        cast = ('Cast', '', [('Literal', '1', []), ('Operator', 'as', []), f.named_type('f32')])
        self.assertIsNotNone(self.classify(f.function('main', [('Tail', '', [cast])])))

    def test_wrapping_float_does_not_hide_its_unimplemented_inner_type(self):
        f = Needs()
        value = f.named_type('wrapping', 'f64')
        self.assertIsNotNone(self.classify(f.function('f', [], value)))


class Blockers(unittest.TestCase):
    """The census's `blockers`: every live construct a row meets, each once, in source order."""
    def blockers(self, *items):
        f = Needs()
        tree = f.Tree(('Unit', '', [('Item', '', [item]) for item in items]))
        return censuslib.blockers(tree, f.NAMES)

    def labels(self, *items):
        return [b[0] for b in self.blockers(*items)]

    def mut_fn(self):
        f = Needs()
        param = ('Parameter', '', [('Mode', 'mut', []), f.name('a'), f.named_type('int')])
        return ('Function', '', [f.name('bump'), ('Parameters', '', [param]), ('Block', '', [])])

    def test_every_blocker_in_source_order(self):
        f = Needs()
        region = ('Region', '', [f.name('r'), ('Block', '', [])])
        main = f.function('main', [('Statement', '', [region])])
        found = self.blockers(self.mut_fn(), main)
        self.assertEqual([b[0] for b in found], ['mode:parameter `mut`', 'other:region'])
        self.assertEqual(found, sorted(found, key=lambda b: (b[1], b[2], b[0])))
        self.assertTrue(all(len(b) == 3 for b in found), found)

    def test_a_core_program_has_no_blocker(self):
        f = Needs()
        body = [('Tail', '', [f.call(f.name('print'), ('Literal', 'raw', []))])]
        self.assertEqual(self.blockers(f.function('main', body)), [])

    def test_the_first_blocker_is_the_census_construct(self):
        f = Needs()
        tree = f.Tree(('Unit', '', [('Item', '', [self.mut_fn()])]))
        first = censuslib.blockers(tree, f.NAMES)[0]
        self.assertEqual(first[0].split(':', 1)[1], censuslib.scope_blocker(tree, f.NAMES)[0])

    def test_a_copy_out_block_is_not_a_plain_copy(self):
        f = Needs()
        copy_out = ('Prefix', '', [('Operator', 'copy', []), ('Region', '', [f.name('r'), ('Block', '', [])])])
        plain = ('Prefix', '', [('Operator', 'copy', []), f.name('a')])
        labels = self.labels(f.function('main', [('Statement', '', [copy_out])]))
        self.assertIn('other:copy region block', labels)
        self.assertNotIn('other:prefix `copy`', labels)
        self.assertIn('other:prefix `copy`', self.labels(f.function('main', [('Statement', '', [plain])])))

    def test_a_generic_application_names_its_head(self):
        f = Needs()
        pool = f.call(f.generic('Pool', 'int'))
        user = f.call(f.generic('pick', 'int'))
        self.assertIn('other:generic application `Pool`', self.labels(f.function('main', [('Tail', '', [pool])])))
        self.assertIn('other:generic application `pick`', self.labels(f.function('main', [('Tail', '', [user])])))

    def test_an_attribute_names_its_first_entry(self):
        f = Needs()
        entry = ('AttributeEntry', '', [('Path', '', [f.name('repr')]), ('AttributeEntry', '', [('Path', '', [f.name('c')])])])
        shape = ('Struct', '', [f.name('S'), ('Fields', '', [])])
        tree = f.Tree(('Unit', '', [('Item', '', [('Attribute', '', [entry]), shape])]))
        self.assertIn('other:attribute `repr`', [b[0] for b in censuslib.blockers(tree, f.NAMES)])

    def test_a_nested_item_names_its_kind(self):
        f = Needs()
        inner = ('Statement', '', [('Item', '', [('Function', '', [f.name('inner'), ('Parameters', '', []),
                                                                  ('Block', '', [])])])])
        self.assertIn('other:nested item `Function`', self.labels(f.function('main', [inner])))

    def test_refining_never_adds_or_drops_a_blocker(self):
        # The refinement names what is recorded; it records exactly what the live scope records.
        import needslib
        f = Needs()
        copy_out = ('Prefix', '', [('Operator', 'copy', []), ('Region', '', [f.name('r'), ('Block', '', [])])])
        tree = f.Tree(('Unit', '', [('Item', '', [self.mut_fn()]),
                                    ('Item', '', [f.function('main', [('Statement', '', [copy_out])])])]))
        live = [label for label in needslib.LiveNeeds(tree, f.NAMES).run() if label != 'render:map']
        self.assertEqual(len(censuslib.blockers(tree, f.NAMES)), len(live))


class MembershipGate(unittest.TestCase):
    """F3's frozen membership against the census's blockers: each failure named, red by itself."""
    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
        import f3membership
        self.m = f3membership

    def census(self):
        def r(file, cls, blockers, oracle='accepted'):
            return dict(file=file, cls=cls, oracle=oracle, blockers=[[b, 1, 1] for b in blockers])
        return [r('corpus/a.lu', 'out-of-core', ['mode:parameter `mut`']),
                r('corpus/b.lu', 'out-of-core', ['mode:parameter `mut`', 'other:region', 'unknown:index']),
                r('corpus/c.lu', 'out-of-core', ['other:`import c`']),
                r('corpus/d.lu', 'out-of-core', ['other:region', 'other:closure']),
                r('corpus/e.lu', 'out-of-core', ['mode:argument `take`', 'other:an empty list literal']),
                r('corpus/k.lu', 'out-of-core', ['other:`const`']),
                r('corpus/z.lu', 'out-of-core', ['other:region'], oracle='refused'),
                r('corpus/done.lu', 'core', [])]

    def oracle(self):
        heads = {'corpus/c.lu': 'run(exit=trap(ub))'}
        return [dict(file=f, expected=heads.get(f, 'run(exit=0)'))
                for f in ('corpus/a.lu', 'corpus/b.lu', 'corpus/c.lu', 'corpus/d.lu', 'corpus/e.lu', 'corpus/k.lu',
                          'corpus/z.lu', 'corpus/done.lu')]

    def membership(self):
        return dict(rules={'F3b': ['mode:parameter `mut`', 'mode:argument `take`'], 'F3c': ['other:region'],
                           'F3e-1': ['other:`import c`', 'other:`const`']},
                    members={'F3b': ['corpus/a.lu', 'corpus/e.lu', 'corpus/done.lu'], 'F3c': ['corpus/b.lu'],
                             'F3e-1': ['corpus/c.lu']},
                    owed=[dict(file='corpus/e.lu', label='other:an empty list literal', unit='F3b', question='Q')],
                    outside={'F7 by an earlier ruling': ['corpus/k.lu']},
                    reference_refuses={'cannot build': ['corpus/z.lu']},
                    ub=['corpus/c.lu'],
                    counts={'members': 5, 'ub': 1, 'parity': 4, 'owed': 1, 'F3b': 3, 'F3c': 1, 'F3d': 0,
                            'F3e-1': 1, 'F3e-2': 0})

    def problems(self, membership):
        return self.m.problems(membership, self.census(), self.oracle())

    def test_the_frozen_fixture_passes(self):
        self.assertEqual(self.problems(self.membership()), [])

    def named(self, membership, expected):
        found = self.problems(membership)
        self.assertIn(expected, found)
        print('PASS f3-membership-rejects ' + expected)

    def test_a_row_dropped_from_its_unit_is_placed_nowhere(self):
        m = self.membership()
        m['members']['F3b'].remove('corpus/a.lu')
        self.named(m, 'f3-membership corpus/a.lu placed nowhere')

    def test_a_row_placed_twice(self):
        m = self.membership()
        m['members']['F3c'].append('corpus/a.lu')
        self.named(m, 'f3-membership corpus/a.lu placed twice (F3b, F3c)')

    def test_a_row_placed_before_its_last_blocker(self):
        m = self.membership()
        m['members']['F3c'].remove('corpus/b.lu')
        m['members']['F3b'].append('corpus/b.lu')
        self.named(m, 'f3-membership corpus/b.lu placed in F3b, its blockers place it in F3c')

    def test_a_member_blocked_outside_f3(self):
        m = self.membership()
        m['members']['F3c'].append('corpus/d.lu')
        self.named(m, 'f3-membership corpus/d.lu blocker other:closure is outside F3 and not owed')

    def test_an_owed_construct_must_be_listed(self):
        m = self.membership()
        m['owed'] = []
        self.named(m, 'f3-membership corpus/e.lu blocker other:an empty list literal is outside F3 and not owed')

    def test_a_ruled_exclusion_must_be_listed(self):
        m = self.membership()
        m['outside'] = {}
        self.named(m, 'f3-membership corpus/k.lu placed nowhere')

    def test_the_ub_list_is_the_trap_ub_headers(self):
        m = self.membership()
        m['ub'] = []
        self.named(m, 'f3-membership the UB list differs from the members whose header expects trap(ub): '
                      'listed 0, found 1')

    def test_a_reference_defect_that_builds_is_named(self):
        m = self.membership()
        m['reference_refuses']['cannot build'].append('corpus/a.lu')
        self.named(m, 'f3-membership corpus/a.lu is listed as refused by the reference (cannot build), but it runs')

    def test_the_frozen_counts_are_the_lists_own(self):
        m = self.membership()
        m['counts']['F3b'] = 2
        self.named(m, 'f3-membership count F3b is 3, frozen 2')

    def test_fenrir_first_refusal_must_be_a_blocker(self):
        rows = self.census()
        rows[0]['code'] = ['F0001', 7, 3, 'parameter mode `mut`']
        found = self.m.problems(self.membership(), rows, self.oracle())
        self.assertIn('f3-membership corpus/a.lu fenrir refuses first at 7:3, not among its blockers', found)
        rows[0]['code'] = ['F0001', 1, 1, 'parameter mode `mut`']
        self.assertEqual(self.m.problems(self.membership(), rows, self.oracle()), [])
        print('PASS f3-membership-rejects f3-membership corpus/a.lu fenrir refuses first at 7:3, not among its blockers')

    def test_a_non_run_row_cannot_be_a_member(self):
        m = self.membership()
        m['members']['F3c'].append('corpus/z.lu')
        self.named(m, 'f3-membership corpus/z.lu is not a native-comparable run row')


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
