#!/usr/bin/env python3
"""Enum/match typing and warning rows; the pinned compiler is a black box."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pattern_rows import ROWS
from check import typed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fenrir', type=Path, default=ROOT / 'target/fenrir')
    parser.add_argument('--reference', action='store_true')
    parser.add_argument('--probe', action='store_true', help='record reference observations without inferring expectations')
    parser.add_argument('--work', type=Path, default=ROOT / 'target/pattern-types')
    args = parser.parse_args()
    env = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'),
               WOLF_RT_LIB=str(ROOT / '.wolf-bin/libwolf_rt.a'))
    failures = 0
    observations = []
    for row in ROWS:
        home = args.work / row['name']
        home.mkdir(parents=True, exist_ok=True)
        source = home / 'row.lu'
        source.write_text(row['source'])
        if args.reference or args.probe:
            result = subprocess.run([str(ROOT / '.wolf-bin/wolf'), 'conform-run', str(source), '--native', '--json'],
                                    capture_output=True, env=env, cwd=home, timeout=120)
            try:
                record = json.loads(result.stdout)
            except ValueError:
                print(f'FAIL {row["name"]} reference protocol {result.stdout!r} {result.stderr!r}', flush=True)
                failures += 1
                continue
            diagnostics = record.get('diagnostics', [])
            errors = [d['code'] for d in diagnostics if d.get('severity') == 'error']
            warnings = [d['code'] for d in diagnostics if d.get('severity') == 'warning' and d['code'] == 'E0802']
            code = errors[0] if errors else ''
            ok = code == row['code'] and warnings == row['warnings'] and record['verdict'] != 'unsupported'
            seen = dict(name=row['name'], verdict=record['verdict'], code=code, warnings=warnings,
                        diagnostics=diagnostics)
            observations.append(seen)
            if args.probe:
                print('OBSERVED ' + json.dumps(seen, sort_keys=True), flush=True)
                continue
        else:
            result = subprocess.run([str(args.fenrir), '--emit=typed', str(source)],
                                    capture_output=True, env=env, timeout=30)
            stderr = result.stderr.decode(errors='replace')
            errors = re.findall(r'error\[([^]]+)\]', stderr)
            warnings = re.findall(r'warning\[(E0802)\]', stderr)
            code = errors[0] if errors else ''
            ok = result.returncode == (2 if row['code'] else 0) and code == row['code'] and warnings == row['warnings']
            if ok and not row['code']:
                try:
                    tree = typed(result.stdout)
                    assert all(d['kind'] not in ('candidate', 'discard') for d in tree['decls'])
                    assert all(d['ty'] >= 0 for d in tree['decls'][10:])
                    for i, d in enumerate(tree['decls']):
                        if d['kind'] == 'enum':
                            for index in range(d['count']):
                                variant = tree['decls'][i + 1 + index]
                                assert (variant['kind'], variant['owner'], variant['index']) == ('variant', i, index)
                except (AssertionError, ValueError, IndexError) as e:
                    print(f'FAIL {row["name"]} typed-invariants {e}', flush=True)
                    ok = False
            if not ok:
                print(f'  observed status={result.returncode} stderr={stderr[:1200]!r}', flush=True)
        print(('PASS ' if ok else 'FAIL ') + row['name'] + f' code={code or "-"} warnings={warnings}', flush=True)
        failures += not ok
    if observations:
        (args.work / 'reference.json').write_text(json.dumps(observations, indent=2, sort_keys=True) + '\n')
    print(f'enum/match rows: {failures} failures', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
