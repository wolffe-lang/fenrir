#!/usr/bin/env python3
"""Mutation controls for the pattern suite's declaration-table invariants."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import patterns


def declaration(kind, name, node, ty, owner=-1, index=-1, count=0):
    return dict(kind=kind, name=name, node=node, ty=ty, owner=owner, index=index, count=count)


def table():
    return dict(types=[{}, {}, {}, {}], decls=[
        declaration('prelude-fn', 'print', -1, 2),
        declaration('prelude-fn', 'assert', -1, -1),
        declaration('prelude-type', 'int', -1, 1),
        declaration('prelude-type', 'wrapping', -1, -1),
        declaration('enum', 'Color', 0, 3, count=2),
        declaration('variant', 'Red', 1, 3, owner=4, index=0),
        declaration('variant', 'Rgb', 2, 2, owner=4, index=1),
        declaration('function', 'main', 3, 2),
    ])


class PatternDeclarationInvariants(unittest.TestCase):
    def check(self, tree):
        patterns.typed_invariants(tree)

    def test_documented_intrinsic_and_constructor_are_not_source_values(self):
        self.check(table())

    def test_extended_prelude_does_not_change_the_source_boundary(self):
        tree = table()
        extras = [declaration('prelude-type', 'scalar' + str(i), -1, 1) for i in range(13)]
        tree['decls'][4:4] = extras
        tree['decls'][18]['owner'] = tree['decls'][19]['owner'] = 17
        self.check(tree)
        tree['decls'][-1]['ty'] = -1
        with self.assertRaises(AssertionError):
            self.check(tree)

    def test_untyped_source_declaration_is_never_hidden_by_a_prefix_length(self):
        for index in (4, 5, 6, 7):
            with self.subTest(index=index):
                tree = table()
                tree['decls'][index]['ty'] = -1
                with self.assertRaises(AssertionError):
                    self.check(tree)

    def test_source_name_wrapping_is_not_a_constructor_exemption(self):
        tree = table()
        tree['decls'][-1].update(name='wrapping', ty=-1)
        with self.assertRaises(AssertionError):
            self.check(tree)

    def test_source_requires_a_declaring_node(self):
        tree = table()
        tree['decls'][-1]['node'] = -1
        with self.assertRaises(AssertionError):
            self.check(tree)

    def test_source_type_id_must_exist(self):
        tree = table()
        tree['decls'][-1]['ty'] = len(tree['types'])
        with self.assertRaises(AssertionError):
            self.check(tree)

    def test_prelude_kind_cannot_hide_a_source_node(self):
        tree = table()
        tree['decls'][-1].update(kind='prelude-type', name='wrapping', ty=-1)
        with self.assertRaises(AssertionError):
            self.check(tree)

    def test_only_documented_unsolved_prelude_entries_are_allowed(self):
        for update in (dict(name='other'), dict(kind='prelude-fn'), dict(ty=-2), dict(ty=4)):
            with self.subTest(update=update):
                tree = table()
                tree['decls'][3].update(update)
                with self.assertRaises(AssertionError):
                    self.check(tree)

    def test_candidate_and_discard_declarations_still_fail(self):
        for kind in ('candidate', 'discard'):
            with self.subTest(kind=kind):
                tree = table()
                tree['decls'][-1]['kind'] = kind
                with self.assertRaises(AssertionError):
                    self.check(tree)

    def test_enum_variant_layout_is_not_weakened(self):
        for update in (dict(kind='field'), dict(owner=0), dict(index=1)):
            with self.subTest(update=update):
                tree = copy.deepcopy(table())
                tree['decls'][5].update(update)
                with self.assertRaises(AssertionError):
                    self.check(tree)
        tree = table()
        tree['decls'][4]['count'] = len(tree['decls'])
        with self.assertRaises(AssertionError):
            self.check(tree)


if __name__ == '__main__':
    unittest.main()
