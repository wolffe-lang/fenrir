#!/usr/bin/env python3
"""Every type.*, conf.resolve* and gram.item.* anchor owns typed rows.

In-scope anchors own a positive row and a refusal row whose code is pinned;
anchors outside the F1 core own an F0001 row and no positive one. Both key sets
are compared in both directions against the pinned anchor registry."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rows as data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ('type.', 'conf.resolve', 'gram.item')


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
        total, scoped = check(data.ROWS, outside, anchors)
        if a.self_test:
            for anchor in sorted({r['anchor'] for r in data.ROWS if r['exit'] == 0 and r['anchor'].startswith(FAMILIES)}):
                broken = [r for r in data.ROWS if not (r['anchor'] == anchor and r['exit'] == 0)]
                try:
                    check(broken, outside, anchors)
                except AssertionError:
                    print('PASS coverage-rejects-missing-positive ' + anchor)
                else:
                    raise AssertionError('coverage cannot reject a missing positive row: ' + anchor)
            dropped = {k for k in anchors if k != 'type.numlit.default'}
            try:
                check(data.ROWS, outside, dropped)
            except AssertionError:
                print('PASS registry-rejects-unknown-anchor')
            else:
                raise AssertionError('coverage cannot reject a row whose anchor left the registry')
        print(f'typed coverage: {total} anchors, {total - scoped} in scope with positive and refusal rows, '
              f'{scoped} outside the core with F0001 rows; {len(data.ROWS)} rows')
        return 0
    except (AssertionError, OSError, KeyError, ValueError) as exc:
        print('FAIL typed-coverage: ' + str(exc))
        return 1


if __name__ == '__main__':
    sys.exit(main())
