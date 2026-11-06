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
                row('out-of-core', 0, construct='module member'), row('checked', 0, construct='`match`')]
        self.assertEqual(censuslib.gate(rows), [])

    def test_each_failure_is_named(self):
        cases = [row('core', 2, ['E0401', 1, 1]), row('core', 134), row('out-of-core', 0, construct='`match`'),
                 row('out-of-core', 2, ['E0301', 1, 1], construct='`match`'), row('syntax-refused', 0, ast=2),
                 row('oracle-refused', 2, ['E0402', 3, 5], oracle='refused', oracle_code='E0401', oracle_at=[3, 5]),
                 row('oracle-refused', 2, ['E0401', 4, 5], oracle='refused', oracle_code='E0401', oracle_at=[3, 5]),
                 row('out-of-core', 70, construct='module member'),
                 row('checked', 2, ['E0801', 1, 1], construct='`match`'), row('checked', 4, ['F0001', 1, 1], construct='`match`')]
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


if __name__ == '__main__':
    unittest.main(verbosity=1)
