#!/usr/bin/env python3
"""Recompute the row-complete delta of F3b (tier 0: modes, moves, `copy`, lends, local borrows) from
sealed measured inputs, and check it against the committed table.

  f3b_delta.py [--self-test]
  f3b_delta.py --write --measurement-head SHA --record-sha256 DIGEST

The before inputs are the census and core verdict table at the base (trunk `653ed2c`, 290 rows
`same`); the after inputs are the census and both engines' verdict tables measured at the
measurement head. Every F3b member of the frozen F3 membership must be `same` on both engines, no row
that was `same` may be lost, and no row outside F3b may enter the core. Typing changes are listed row
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
    'before_census': 'tests/types/f3b-baseline-census.json',
    'before_verdicts': 'tests/types/f3b-baseline-verdicts.json',
    'after_census': 'tests/types/f3b-measured-census.json',
    'native': 'tests/types/f3b-measured-native.json',
    'interpreter': 'tests/types/f3b-measured-interpreter.json',
    # Sealed at F3b's census: the live membership's `met_through` moves with each unit.
    'membership': 'tests/types/f3b-membership.json',
    'oracle': 'tests/oracle.json',
}
UNITS = ('F3b', 'F3c', 'F3d', 'F3e-1', 'F3e-2')


def f3_groups(model):
    """F3's units as groups, in order, each with its frozen members."""
    return [dict(id=unit, rows=model['members'][unit]) for unit in UNITS]


SPEC = dict(label='f3b-delta', files=FILES, table=base.ROOT / 'tests/types/f3b-language-delta.json',
            base='653ed2ca17fb973879c1f7c79da6adcbafc7c7d7', tranches=('F3b',), baseline=290, frozen=87, predicted=87,
            groups=f3_groups,
            scope='Complete typing/classification observations and native/interpreter execution gains of F3b, tier 0.')

if __name__ == '__main__':
    raise SystemExit(base.main(SPEC, __doc__))
