#!/usr/bin/env python3
"""An OUTSIDE typed row stays outside until its own unit lands.

Each `mem.*` anchor outside the typed core owns one row that fenrir refuses with F0001
(tests/types/memory_rows.py). The row holds only while its program uses a construct of a unit
that has not landed. A program that uses only constructs of met units turns typeable the day
the last of them lands, and the row reads red for a reason that is not its own (the value
tier's `bump(mut a)` row did exactly that). This check holds, with no compiler, that the program
of every OUTSIDE row whose anchor belongs to a later unit names a construct no met unit owns.
The anchor's unit is its scope in docs/MEMORY.md; the met units are F2 and the F3 units up to
`met_through` in tests/types/f3-membership.json. A row whose anchor belongs to a met unit is that
unit's own work (it moves in scope with the unit, and the typed coverage counts it), so it is
reported apart and never fails here.

  outside_unit.py

Cost: linear in the rows.
"""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/types'))
import memory_rows  # noqa: E402

F3_UNITS = ('F3b', 'F3c', 'F3d', 'F3e-1', 'F3e-2')
# The spellings of each later unit's constructs, as a program writes them.
CONSTRUCTS = {
    'F3d': ('freeze ', 'copy region', 'Pool[', 'handle ', 'RegionStrategy', '.has('),
    'F3e-1': ('unsafe', 'extern ', 'import c', 'const ', '#[repr', 'assume'),
    'F3e-2': ('fence(', 'seq_cst', 'acquire', 'release', 'relaxed', 'acq_rel'),
    'F4': ('trait ', 'impl ', 'dyn '),
    'F6': ('.{', '&'),
    'F7': ('spawn ', 'Proc[', 'channel['),
    'none': ('shared ', 'weak '),
}


def scopes(text):
    """Each anchor's unit, from MEMORY.md's anchor table."""
    found = {}
    for line in text.splitlines():
        m = re.match(r'^\| `([a-z0-9.\-]+)` \| ([A-Za-z0-9\-]+) \|', line)
        if m:
            found[m.group(1)] = m.group(2)
    return found


def met_units(membership):
    met = membership.get('met_through')
    return {'F2'} | set(F3_UNITS[:F3_UNITS.index(met) + 1] if met in F3_UNITS else ())


def problems(outside, scope, met):
    """(failures, the anchors of met units still outside)."""
    out, own = [], []
    for anchor, body, items in outside:
        unit = scope.get(anchor)
        if unit is None:
            out.append(f'{anchor} has no scope in docs/MEMORY.md')
            continue
        if unit in met:
            own.append(anchor)
            continue
        if unit not in CONSTRUCTS:
            out.append(f'{anchor} belongs to {unit}, which names no constructs here')
            continue
        later = [s for u, names in CONSTRUCTS.items() if u not in met for s in names]
        if not any(s in items + body for s in later):
            out.append(f'{anchor} belongs to {unit}, but its program names no construct of a unit that has not '
                       f'landed: it turns typeable when the met units do (give it one of '
                       f'{", ".join(CONSTRUCTS[unit])})')
    return out, own


def main():
    scope = scopes((ROOT / 'docs/MEMORY.md').read_text())
    met = met_units(json.loads((ROOT / 'tests/types/f3-membership.json').read_text()))
    found, own = problems(memory_rows.OUTSIDE, scope, met)
    for line in found:
        print(f'FAIL outside-unit {line}', flush=True)
    if own:
        print(f'INFO outside-unit {len(own)} anchors of met units still outside, their unit\'s own work: '
              + ', '.join(own), flush=True)
    if not found:
        print(f'PASS outside-unit {len(memory_rows.OUTSIDE)} rows, every later unit\'s row names a construct no '
              f'met unit owns',
              flush=True)
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
