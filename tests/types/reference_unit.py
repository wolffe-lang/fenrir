#!/usr/bin/env python3
"""Reference fixture policy: unsupported never passes an ordinary positive."""
from pathlib import Path
import importlib.util
import unittest

spec = importlib.util.spec_from_file_location('typed_reference', Path(__file__).with_name('reference.py'))
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


class Policy(unittest.TestCase):
    def test_unsupported_is_not_positive_agreement(self):
        ok, kind, seen = reference.assess(dict(exit=0), 'unsupported', None, None)
        self.assertFalse(ok)
        self.assertEqual((kind, seen), ('reference', 'unsupported'))

    def test_candidate_only_is_explicit_and_not_parity(self):
        row = dict(exit=4, code='F0001', candidate_only=True, differs='unsupported')
        self.assertEqual(reference.assess(row, 'unsupported', None, None), (True, 'candidate-only', 'unsupported'))

    def test_candidate_only_cannot_be_an_unpinned_escape(self):
        with self.assertRaises(AssertionError):
            reference.assess(dict(exit=0, candidate_only=True), 'unsupported', None, None)

    def test_recorded_disagreement_rejects_diagnostic_drift(self):
        row = dict(exit=0, candidate_only=True, differs='fail(E0401) E0401@3:23')
        ok, kind, _ = reference.assess(row, 'fail(E0402)', {'code': 'E0402'}, (3, 23))
        self.assertFalse(ok)
        self.assertEqual(kind, 'candidate-only')

    def test_normal_refusal_matches_code_and_site(self):
        row = dict(exit=2, reference=True, code='E0401', location=[2, 19])
        self.assertTrue(reference.assess(row, 'fail(E0401)', {'code': 'E0401'}, (2, 19))[0])
        self.assertFalse(reference.assess(row, 'fail(E0401)', {'code': 'E0401'}, (2, 20))[0])

    def test_scope_only_is_not_called_reference_parity(self):
        self.assertEqual(reference.assess(dict(exit=4, code='F0001'), 'unsupported', None, None),
                         (True, 'scope-only', 'unsupported'))


if __name__ == '__main__':
    unittest.main()
