#!/usr/bin/env python3
"""Every type.*, conf.resolve*, gram.item.* and mem.* anchor owns typed rows.

In-scope anchors own a positive row and a refusal row whose code is pinned;
anchors outside the F1 core own an F0001 row and no positive one. Both key sets
are compared in both directions against the pinned anchor registry.

A `mem.*` anchor in scope (docs/MEMORY.md) owns a positive row and a negative
row: a refusal fenrir shares with the reference (`reference`, exit 2), or a
named difference, a program the reference refuses with an E1xxx code and
fenrir accepts until the milestone in its `closes`. Every named difference is
listed in tests/types/memory-differences.json with its count, both directions
checked, so the list cannot grow or shrink quietly."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rows as data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ('type.', 'conf.resolve', 'gram.item', 'mem.')
MEM = 'mem.'
DIFFERENCES = ROOT / 'tests/types/memory-differences.json'


def named(row):
    return 'closes' in row


def differences(rows, listed):
    """A named difference row is exact in shape, and the committed list is the rows' own."""
    found = []
    for row in rows:
        if not named(row):
            continue
        m = re.fullmatch(r'fail\((E1\d{3})\) (E1\d{3})@(\d+):(\d+)', row.get('differs', ''))
        assert m and m.group(1) == m.group(2), 'named difference without an E1xxx reference answer: ' + row['name']
        assert row['exit'] == 0 and row.get('candidate_only'), 'named difference fenrir does not accept: ' + row['name']
        assert row['closes'] == 'F6', 'named difference closed by another milestone: ' + row['name']
        found.append(dict(name=row['name'], anchor=row['anchor'], code=m.group(1),
                          site=[int(m.group(3)), int(m.group(4))], closes=row['closes']))
    mine = sorted(found, key=lambda d: d['name'])
    theirs = sorted(listed['differences'], key=lambda d: d['name'])
    unlisted = sorted({d['name'] for d in mine} - {d['name'] for d in theirs})
    assert not unlisted, 'named differences missing from memory-differences.json: ' + ', '.join(unlisted)
    stale = sorted({d['name'] for d in theirs} - {d['name'] for d in mine})
    assert not stale, 'listed named differences with no row: ' + ', '.join(stale)
    assert mine == theirs, 'a listed named difference disagrees with its row'
    assert listed['count'] == len(mine), f'named differences: {len(mine)} rows, the list says {listed["count"]}'
    return len(mine)


def check(rows, outside, anchors):
    family = {k for k in anchors if k.startswith(FAMILIES)}
    assert outside <= family, 'outside names an unknown anchor: ' + ', '.join(sorted(outside - family))
    owned = {}
    for row in rows:
        assert row['anchor'] in anchors, 'unknown anchor ' + row['anchor']
        assert row['exit'] in (0, 2, 4), 'unexecutable row ' + row['name']
        if row['exit']:
            assert re.fullmatch(r'[EF]\d{4}', row.get('code', '')), 'refusal without a pinned code: ' + row['name']
            assert (row['exit'] == 4) == (row['code'] == 'F0001'), 'F0001 is status 4 and only it: ' + row['name']
        owned.setdefault(row['anchor'], set()).add(row['exit'])
    missing = family - set(owned)
    assert not missing, 'anchors without rows: ' + ', '.join(sorted(missing))
    for anchor in family:
        verdicts = owned[anchor]
        if anchor.startswith(MEM) and anchor not in outside:
            mine = [r for r in rows if r['anchor'] == anchor]
            positive = [r for r in mine if r['exit'] == 0 and not r.get('candidate_only')]
            negative = [r for r in mine if (r['exit'] == 2 and r.get('reference')) or named(r)]
            assert positive and negative, 'in-scope mem anchor without a positive and a negative row: ' + anchor
            continue
        if anchor in outside:
            assert 4 in verdicts and 0 not in verdicts, 'outside anchor without its F0001 row, or with a positive: ' + anchor
        else:
            assert 0 in verdicts and verdicts & {2, 4}, 'in-scope anchor without a positive and a refusal row: ' + anchor
    return len(family), len(outside)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('spec', type=Path)
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    try:
        anchors = set(json.loads((a.spec / 'anchors.json').read_text())['anchors'])
        outside = {entry[0] for entry in data.OUTSIDE} | data.OUTSIDE_ITEMS
        outside |= {entry[0] for entry in getattr(data, 'MEMORY_OUTSIDE', [])}
        total, scoped = check(data.ROWS, outside, anchors)
        listed = json.loads(DIFFERENCES.read_text()) if DIFFERENCES.exists() else dict(count=0, differences=[])
        named_count = differences(data.ROWS, listed)
        if a.self_test:
            for anchor in sorted({r['anchor'] for r in data.ROWS if r['exit'] == 0 and r['anchor'].startswith(FAMILIES)}):
                broken = [r for r in data.ROWS if not (r['anchor'] == anchor and r['exit'] == 0)]
                try:
                    check(broken, outside, anchors)
                except AssertionError:
                    print('PASS coverage-rejects-missing-positive ' + anchor)
                else:
                    raise AssertionError('coverage cannot reject a missing positive row: ' + anchor)
            for anchor in sorted({r['anchor'] for r in data.ROWS if r['anchor'].startswith(MEM)} - outside):
                broken = [r for r in data.ROWS if not (r['anchor'] == anchor and (named(r) or r.get('reference')))]
                try:
                    check(broken, outside, anchors)
                except AssertionError:
                    print('PASS coverage-rejects-missing-negative ' + anchor)
                else:
                    raise AssertionError('coverage cannot reject a missing negative row: ' + anchor)
            if named_count:
                try:
                    differences(data.ROWS, dict(listed, differences=listed['differences'][1:]))
                except AssertionError:
                    print('PASS differences-reject-an-unlisted-row')
                else:
                    raise AssertionError('the named-difference list cannot reject an unlisted row')
            dropped = {k for k in anchors if k != 'type.numlit.default'}
            try:
                check(data.ROWS, outside, dropped)
            except AssertionError:
                print('PASS registry-rejects-unknown-anchor')
            else:
                raise AssertionError('coverage cannot reject a row whose anchor left the registry')
        print(f'typed coverage: {total} anchors, {total - scoped} in scope with positive and refusal rows, '
              f'{scoped} outside the core with F0001 rows; {len(data.ROWS)} rows; '
              f'{named_count} named differences closed at F6')
        return 0
    except (AssertionError, OSError, KeyError, ValueError) as exc:
        print('FAIL typed-coverage: ' + str(exc))
        return 1


if __name__ == '__main__':
    sys.exit(main())
