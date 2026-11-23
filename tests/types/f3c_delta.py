#!/usr/bin/env python3
"""Recompute the row-complete delta of F3c (tier 1: regions, the region ledger and its cap, `reserve` and `reset`) from
sealed measured inputs, and check it against the committed table.

  f3c_delta.py [--self-test]
  f3c_delta.py --write --measurement-head SHA --record-sha256 DIGEST

The before inputs are the census and core verdict table at the base (trunk `8cb589c`, 377 rows
`same`); the after inputs are the census and both engines' verdict tables measured at the
measurement head. Every F3c member of the frozen F3 membership must be `same` on both engines, no row
that was `same` may be lost, and no row outside F3c may enter the core. Typing changes are listed row
by row. The checks are the earlier deltas' (fn09_delta.py); only the groups come from
`tests/types/f3-membership.json`.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fn09_delta', HERE / 'fn09_delta.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

FILES = {
    'before_census': 'tests/types/f3c-baseline-census.json',
    'before_verdicts': 'tests/types/f3c-baseline-verdicts.json',
    'after_census': 'tests/types/f3c-measured-census.json',
    'native': 'tests/types/f3c-measured-native.json',
    'interpreter': 'tests/types/f3c-measured-interpreter.json',
    'membership': 'tests/types/f3-membership.json',
    'oracle': 'tests/oracle.json',
}
UNITS = ('F3b', 'F3c', 'F3d', 'F3e-1', 'F3e-2')


def f3_groups(model):
    """F3's units as groups, in order, each with its frozen members."""
    return [dict(id=unit, rows=model['members'][unit]) for unit in UNITS]


SPEC = dict(label='f3c-delta', files=FILES, table=base.ROOT / 'tests/types/f3c-language-delta.json',
            base='8cb589c1fe9d1ac6f169703b60894317c955f86a', tranches=('F3c',), baseline=377, frozen=46, predicted=46,
            groups=f3_groups,
            scope='Complete typing/classification observations and native/interpreter execution gains of F3c, tier 1.')

if __name__ == '__main__':
    raise SystemExit(base.main(SPEC, __doc__))
