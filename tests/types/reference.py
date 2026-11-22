#!/usr/bin/env python3
"""Run the pinned reference compiler, as a black box, over the typed rows.

A row marked `reference` must be rejected by the reference with the row's code
at the row's line:column. An ordinary positive row must be accepted by it.
`differs` pins a named reference disagreement, rather than claiming parity.
`candidate_only` requires such an explicit observation and always prints zero
parity credit, even when fenrir accepts the source. Other fenrir-only scope
refusals are reported without a comparison claim."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rows as data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def position(text, offset):
    prefix = text.encode()[:offset].decode()
    line = prefix.count('\n') + 1
    return line, len(prefix) - (prefix.rfind('\n') + 1) + 1


def assess(row, verdict, first, where):
    seen = f'{verdict} {first["code"]}@{where[0]}:{where[1]}' if first else verdict
    if row.get('candidate_only'):
        assert row.get('differs'), 'candidate-only rows require a pinned reference answer'
        return seen == row['differs'], 'candidate-only', seen
    if row.get('differs'):
        return seen == row['differs'], 'difference', seen
    if row.get('reference'):
        ok = first is not None and first['code'] == row['code'] and list(where) == row['location']
        return ok, 'reference', seen
    if row['exit'] == 0:
        return not verdict.startswith('fail') and verdict != 'unsupported', 'reference', seen
    return True, 'scope-only', seen


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--work', required=True, type=Path)
    p.add_argument('--wolf', type=Path, default=ROOT / '.wolf-bin/wolf')
    a = p.parse_args()
    a.work = a.work.resolve()
    env = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'), WOLF_RT_LIB=str(ROOT / '.wolf-bin/libwolf_rt.a'))
    failures = 0
    for row in data.ROWS:
        home = a.work / row['name']
        home.mkdir(parents=True, exist_ok=True)
        source = home / 'row.lu'
        source.write_text(row['source'])
        for name, text in row.get('siblings', {}).items():
            (home / name).write_text(text)
        r = subprocess.run([str(a.wolf), 'conform-run', str(source), '--native', '--json'],
                           capture_output=True, timeout=120, cwd=home, env=env)
        try:
            record = json.loads(r.stdout)
        except ValueError:
            print(f'FAIL {row["name"]} reference gave no record: {r.stderr.decode()[:200]}')
            failures += 1
            continue
        verdict = record['verdict']
        errors = [d for d in record.get('diagnostics', []) if d.get('severity') == 'error']
        first = min(errors, key=lambda d: d['span'][0]) if errors else None
        where = position(row['source'], first['span'][0]) if first else None
        ok, kind, seen = assess(row, verdict, first, where)
        if kind == 'scope-only':
            print(f'INFO {row["name"]} scope-only fenrir {row["code"]}; reference {seen}; no parity credit')
            continue
        if kind == 'candidate-only' and ok:
            print(f'INFO {row["name"]} candidate-only reference {seen}; no parity credit')
        else:
            print(('PASS ' if ok else 'FAIL ') + f'{row["name"]} reference {seen}', flush=True)
        failures += not ok
    print(f'reference rows: {failures} disagree', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
