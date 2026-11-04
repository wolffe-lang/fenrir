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


if __name__ == '__main__':
    unittest.main(verbosity=1)
