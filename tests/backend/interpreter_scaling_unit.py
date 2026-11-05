#!/usr/bin/env python3
"""The interpreter CPU gate's arithmetic and witness construction."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


class ScalingGate(unittest.TestCase):
    def tool(self):
        spec = importlib.util.spec_from_file_location('interpreter_scaling', HERE / 'interpreter_scaling.py')
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        return value

    def points(self, times):
        return [dict(shape=shape, n=n, cpu_samples=[cpu] * 5)
                for shape in ('instructions', 'functions')
                for n, cpu in zip((1000, 10000, 100000), times)]

    def test_linear_points_pass(self):
        self.assertEqual(self.tool().problems(self.points((0.01, 0.1, 1.0))), [])

    def test_quadratic_points_fail_even_below_timer_floor(self):
        failures = self.tool().problems(self.points((0.001, 0.1, 10.0)))
        self.assertEqual(len(failures), 2)
        self.assertTrue(all('superlinear' in failure for failure in failures))

    def test_incomplete_or_invalid_samples_fail(self):
        tool = self.tool()
        for invalid in (-1.0, float('inf'), float('nan')):
            points = self.points((0.01, 0.1, 1.0))
            points[-1]['cpu_samples'][0] = invalid
            self.assertTrue(tool.problems(points))
        points = self.points((0.01, 0.1, 1.0))
        self.assertTrue(tool.problems(points[:-1]))
        points[-1]['cpu_samples'].pop()
        self.assertTrue(tool.problems(points))

    def test_witnesses_have_dependent_work_and_exact_step_counts(self):
        tool = self.tool()
        text, steps = tool.program('instructions', 3)
        self.assertEqual(text.count('\nadd '), 3)
        self.assertEqual(steps, 8)
        text, steps = tool.program('functions', 3)
        self.assertEqual(text.count('\nfunction '), 4)
        self.assertEqual(text.count('\ncall '), 3)
        self.assertEqual(text.count('\nadd '), 3)
        self.assertEqual(steps, 16)


if __name__ == '__main__':
    unittest.main()
