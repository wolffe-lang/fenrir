#!/usr/bin/env python3
"""Typing and warning rows (enum and match, or lists, maps and rows); the pinned
compiler is a black box."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def position(source, offset):
    prefix = source.encode()[:offset].decode()
    return f"{prefix.count(chr(10)) + 1}:{len(prefix) - (prefix.rfind(chr(10)) + 1) + 1}"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import typed
import importlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fenrir', type=Path, default=ROOT / 'target/fenrir')
    parser.add_argument('--reference', action='store_true')
    parser.add_argument('--probe', action='store_true', help='record reference observations without inferring expectations')
    parser.add_argument('--work', type=Path, default=ROOT / 'target/pattern-types')
    parser.add_argument('--rows', default='pattern_rows', help='the rows module: pattern_rows or collection_rows')
    args = parser.parse_args()
    ROWS = importlib.import_module(args.rows).ROWS
    args.work = args.work.resolve()
    env = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'),
               WOLF_RT_LIB=str(ROOT / '.wolf-bin/libwolf_rt.a'))
    failures = 0
    observations = []
    for row in ROWS:
        home = args.work / row['name']
        home.mkdir(parents=True, exist_ok=True)
        source = home / 'row.lu'
        source.write_text(row['source'])
        if args.reference and row['differs']:
            print(f'INFO {row["name"]} not compared with the reference: {row["differs"]}', flush=True)
            continue
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
            errors = sorted((d for d in diagnostics if d.get('severity') == 'error'), key=lambda d: d['span'][0])
            code = errors[0]['code'] if errors else ''
            at = position(row['source'], errors[0]['span'][0]) if errors else None
            marks = [d for d in diagnostics if d.get('severity') == 'warning' and d['code'] == 'E0802']
            warnings = [d['code'] for d in marks] if not errors else row['warnings']
            warn_at = [position(row['source'], d['span'][0]) for d in marks] if not errors else row['warn_at']
            # A native refusal after type checking (a later phase's "unsupported")
            # still answers this typing row; one before it does not.
            checked = record['verdict'] != 'unsupported' or record.get('phase_reached') in ('mem', 'run')
            if record['verdict'] == 'unsupported' and checked:
                print(f'INFO {row["name"]} the reference typed it, then refused it at {record.get("phase_reached")}: '
                      f'{record.get("x-unsupported-construct")}', flush=True)
            ok = (code == row['code'] and at == row['at'] and warnings == row['warnings']
                  and warn_at == row['warn_at'] and checked)
            seen = dict(name=row['name'], verdict=record['verdict'], code=code, at=at, warnings=warnings,
                        warn_at=warn_at, diagnostics=diagnostics, record=record)
            observations.append(seen)
            if args.probe:
                print('OBSERVED ' + json.dumps(seen, sort_keys=True), flush=True)
                continue
        else:
            result = subprocess.run([str(args.fenrir), '--emit=typed', str(source)],
                                    capture_output=True, env=env, timeout=30)
            stderr = result.stderr.decode(errors='replace')
            errors = re.findall(r':(\d+):(\d+): error\[([^]]+)\]', stderr)
            marks = re.findall(r':(\d+):(\d+): warning\[(E0802)\]', stderr)
            code = errors[0][2] if errors else ''
            at = f'{errors[0][0]}:{errors[0][1]}' if errors else None
            warnings = [m[2] for m in marks]
            warn_at = [f'{m[0]}:{m[1]}' for m in marks]
            status = 0 if not row['code'] else 4 if row['code'][0] == 'F' else 2
            ok = (result.returncode == status and code == row['code'] and at == row['at']
                  and warnings == row['warnings'] and warn_at == row['warn_at'])
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
        print(('PASS ' if ok else 'FAIL ') + row['name'] + f' code={code or "-"}@{at} warnings={warnings}@{warn_at}', flush=True)
        failures += not ok
    if observations:
        (args.work / 'reference.json').write_text(json.dumps(observations, indent=2, sort_keys=True) + '\n')
    print(f'{args.rows}: {failures} failures', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
