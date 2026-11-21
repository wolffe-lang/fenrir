#!/usr/bin/env python3
"""Recompute the row-complete delta of the float tranche from sealed measured inputs, and check it
against the committed table.

  fn09b_delta.py [--self-test]
  fn09b_delta.py --write --measurement-head SHA --record-sha256 DIGEST

The before inputs are the census and core verdict table at the base (the trunk the tranche started
from, 275 rows `same`); the after inputs are the census and both engines' verdict tables measured
at the measurement head. Every frozen row of the float tranche must be `same` on both engines, no
row that was `same` may be lost, and no row outside the frozen F2 membership may enter the core.
Typing changes are listed row by row. The checks are the earlier delta's (fn09_delta.py).
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fn09_delta', HERE / 'fn09_delta.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

FILES = {
    'before_census': 'tests/types/fn09b-baseline-census.json',
    'before_verdicts': 'tests/types/fn09b-baseline-verdicts.json',
    'after_census': 'tests/types/fn09b-measured-census.json',
    'native': 'tests/types/fn09b-measured-native.json',
    'interpreter': 'tests/types/fn09b-measured-interpreter.json',
    'membership': 'tests/types/fn08-membership.json',
    'oracle': 'tests/oracle.json',
}
SPEC = dict(label='fn09b-delta', files=FILES, table=base.ROOT / 'tests/types/fn09b-language-delta.json',
            base='a8756581a8ea235b580ccf088595ecccc347b16f', tranches=('float',), baseline=275, frozen=15, predicted=15,
            scope='Complete typing/classification observations and native/interpreter execution gains of the frozen float tranche.')

if __name__ == '__main__':
    raise SystemExit(base.main(SPEC, __doc__))
