"""F3's frozen membership, checked against the live census in both directions.

`tests/types/f3-membership.json` freezes F3's rows (docs/MEMORY.md, "F3's
membership"): native-comparable run rows, each placed at the last F3 unit
among its blockers. This module holds the frozen lists to the census's
`blockers` on every run:

- every member is a run row the reference runs, placed exactly once;
- a member that is not yet in the core is placed where its blockers place it;
- fenrir's own first refusal of a member is at one of its blockers' sites
  (the scope model may name it differently: tests/types/scope-model-gap.json);
- every blocker of a member is an F3 construct of a unit, a consequence the
  scope model cannot type (`unknown:`), or listed under `owed` for that row;
- every run row whose known blockers are all F3 constructs is a member, or is
  listed outside with the ruling that keeps it out ("placed nowhere" otherwise);
- the UB list is exactly the members whose header expects `trap(ub)`;
- the F3 rows the reference refuses (it cannot build them, or refuses them
  statically where the header expects a run) are still refused by it;
- the frozen counts are the lists' own.

`problems()` answers every failed condition as a line; an empty list is a pass.

Spec: mem.ub (UB rows carry no parity credit); conf.directive (run headers).
"""
import json
from pathlib import Path

UNITS = ('F3b', 'F3c', 'F3d', 'F3e-1', 'F3e-2')


def run_rows(census_rows, oracle_rows):
    """Native-comparable run rows outside the core or in it, by file: the census row."""
    expected = {r['file']: (r.get('expected') or '') for r in oracle_rows}
    return {r['file']: r for r in census_rows
            if expected.get(r['file'], '').startswith('run(') and r['oracle'] == 'accepted'}


def known(row):
    """A row's blockers the scope model could name (an `unknown:` label is a consequence, not a construct)."""
    return [b[0] for b in row.get('blockers', []) if not b[0].startswith('unknown:')]


def placement(row, rules, owed):
    units = [rules[label] for label in known(row) if label in rules]
    units += [entry['unit'] for entry in owed if entry['label'] in known(row)]
    return max(units, key=UNITS.index) if units else None


def problems(membership, census_rows, oracle_rows):
    out = []
    rules = {label: unit for unit, labels in membership['rules'].items() for label in labels}
    runs = run_rows(census_rows, oracle_rows)
    everything = {r['file']: r for r in census_rows}
    expected = {r['file']: (r.get('expected') or '') for r in oracle_rows}
    placed = {}
    for unit in UNITS:
        for name in membership['members'].get(unit, []):
            if name in placed:
                out.append(f'f3-membership {name} placed twice ({placed[name]}, {unit})')
            placed[name] = unit
    owed = {}
    for entry in membership.get('owed', []):
        owed.setdefault(entry['file'], []).append(entry)
    outside = {name: reason for reason, names in membership['outside'].items() for name in names}
    for name, unit in sorted(placed.items()):
        row = runs.get(name)
        if row is None:
            out.append(f'f3-membership {name} is not a native-comparable run row')
            continue
        if row['cls'] == 'core':
            continue
        mine = owed.get(name, [])
        for label in known(row):
            if label not in rules and not any(e['label'] == label for e in mine):
                out.append(f'f3-membership {name} blocker {label} is outside F3 and not owed')
        for entry in mine:
            if entry['label'] not in known(row):
                out.append(f'f3-membership {name} owes {entry["label"]}, no longer a blocker')
        code = row.get('code') or []
        if len(code) > 2 and code[0] == 'F0001' and code[1:3] not in [b[1:3] for b in row.get('blockers', [])]:
            out.append(f'f3-membership {name} fenrir refuses first at {code[1]}:{code[2]}, not among its blockers')
        where = placement(row, rules, mine)
        if where is None:
            out.append(f'f3-membership {name} has no F3 blocker')
        elif where != unit:
            out.append(f'f3-membership {name} placed in {unit}, its blockers place it in {where}')
    for name, row in sorted(runs.items()):
        if row['cls'] != 'out-of-core' or name in placed or name in outside:
            continue
        labels = known(row)
        if labels and all(label in rules for label in labels):
            out.append(f'f3-membership {name} placed nowhere')
    for name in sorted(owed):
        if name not in placed:
            out.append(f'f3-membership {name} owes a construct but is not a member')
    for name in sorted(outside):
        if name in placed:
            out.append(f'f3-membership {name} is both a member and outside')
    for reason, names in membership['reference_refuses'].items():
        for name in names:
            row = everything.get(name)
            if row is None or row['oracle'] != 'refused':
                out.append(f'f3-membership {name} is listed as refused by the reference ({reason}), but it runs')
    ub = sorted(name for name in placed if 'trap(ub' in expected.get(name, ''))
    if ub != sorted(membership['ub']):
        out.append(f'f3-membership the UB list differs from the members whose header expects trap(ub): '
                   f'listed {len(membership["ub"])}, found {len(ub)}')
    counts = dict(members=len(placed), ub=len(ub), parity=len(placed) - len(ub),
                  owed=len(membership.get('owed', [])),
                  **{unit: len(membership['members'].get(unit, [])) for unit in UNITS})
    for key, value in counts.items():
        if membership['counts'].get(key) != value:
            out.append(f'f3-membership count {key} is {value}, frozen {membership["counts"].get(key)}')
    return out


def summary(membership, census_rows):
    cls = {r['file']: r['cls'] for r in census_rows}
    members = [name for unit in UNITS for name in membership['members'].get(unit, [])]
    met = sum(cls.get(name) == 'core' for name in members)
    units = ', '.join(f'{unit} {len(membership["members"].get(unit, []))}' for unit in UNITS)
    return (f'f3-membership: {len(members)} members ({units}); {len(membership["ub"])} UB with no credit; '
            f'{len(members) - len(membership["ub"])} parity; {len(membership.get("owed", []))} owed; '
            f'{sum(len(v) for v in membership["outside"].values())} outside by ruling; {met} met')


def load(path):
    return json.loads(Path(path).read_text())
