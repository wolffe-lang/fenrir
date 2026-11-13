#!/usr/bin/env python3
"""Cheap classification checks for the Linux-only fixture readiness gate."""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('linux_readiness',HERE/'linux_readiness.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class Readiness(unittest.TestCase):
    def test_only_completed_reference_typechecking_is_accepted(self):
        good=dict(protocol=1,verdict='pass',phase_reached='typecheck',diagnostics=[])
        self.assertTrue(module.reference_accepted(0,good))
        for status,record in [(2,good),(0,{}),(0,dict(good,phase_reached='resolve')),
                              (0,dict(good,verdict='unsupported')),
                              (0,dict(good,verdict='fail(E0410)',diagnostics=[dict(severity='error',code='E0410')]))]:
            self.assertFalse(module.reference_accepted(status,record))

    def test_warning_is_not_an_error(self):
        self.assertTrue(module.reference_accepted(0,dict(protocol=1,verdict='pass',phase_reached='typecheck',
                         diagnostics=[dict(severity='warning',code='E0802')])))

    def test_every_fixture_family_and_both_previous_failures_are_present(self):
        rows=module.catalog()
        keys=[(family,name) for family,name,_ in rows]
        self.assertEqual(len(keys),len(set(keys)))
        self.assertIn(('backend','blob-boundaries'),keys)
        self.assertIn(('lower','match-loop-statement'),keys)
        self.assertGreater(len(keys),100)
        self.assertTrue(all('fn main()' in source for _,_,source in rows))


if __name__=='__main__':unittest.main()
