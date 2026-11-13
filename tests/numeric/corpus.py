#!/usr/bin/env python3
"""Frozen integer corpus contracts: typing, verified lowering and both engines."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def selected():
    membership = json.loads((ROOT / 'tests/types/fn08-membership.json').read_text())
    tranche, = [r for r in membership['ordered_F2_tranches'] if r['id'] == 'integer']
    names = tranche['rows']
    assert len(names) == 60 and len(set(names)) == 60
    return names, {r['file']: r['sha256'] for r in membership['rows']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--mode', choices=('typed', 'lower', 'interpreter', 'native'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    names, hashes = selected()
    args.out.mkdir(parents=True, exist_ok=True)
    for name in names:
        assert hashlib.sha256((ROOT / '.wolf-bin/reference' / name).read_bytes()).hexdigest() == hashes[name], name
    if args.mode in ('typed', 'lower'):
        view = 'typed' if args.mode == 'typed' else 'fir'
        rows = []
        for index, name in enumerate(names):
            run = subprocess.run([str(args.compiler.resolve()), '--emit=' + view,
                                  str(ROOT / '.wolf-bin/reference' / name)], capture_output=True, timeout=30)
            (args.out / f'{index}.{view}').write_bytes(run.stdout)
            (args.out / f'{index}.stderr').write_bytes(run.stderr)
            ok = run.returncode == 0 and run.stdout.startswith((view + ('/1' if view == 'typed' else ' ')).encode())
            print(('PASS' if ok else 'FAIL') + ' integer-' + args.mode + '-' + name + ' exit=' + str(run.returncode), flush=True)
            rows.append(dict(file=name, passed=ok, status=run.returncode))
        (args.out / 'results.json').write_text(json.dumps(rows, indent=2) + '\n')
        return int(any(not r['passed'] for r in rows))
    assert sys.platform == 'linux', 'Linux execution required, not a skip'
    selection = args.out / 'selection.json'
    selection.write_text(json.dumps(names) + '\n')
    table = args.out / 'verdicts.json'
    comparison = args.out / 'comparison.json'
    table.unlink(missing_ok=True)
    comparison.unlink(missing_ok=True)
    command = [str(ROOT / 'tools/differ'), 'compare', '--input', str(ROOT / 'tests/oracle.json'),
               '--fenrir', str(args.compiler.resolve()), '--select', str(selection),
               '--output', str(comparison), '--table', str(table)]
    if args.mode == 'interpreter':
        command.append('--interpreter')
    env = dict(os.environ, FENRIR_ORACLE_SANDBOX='1',
               FENRIR_TOOLCHAIN=os.environ.get('FENRIR_TOOLCHAIN', str(ROOT / '.wolf-bin')))
    with (args.out / 'compare.stdout').open('wb') as output:
        run = subprocess.run(command, cwd=ROOT, stdout=output, env=env)
    if not table.is_file():
        print(f'FAIL integer-differential missing result table status={run.returncode}', flush=True)
        return 1
    result = json.loads(table.read_text())
    assert [r['file'] for r in result['rows']] == sorted(names), 'incomplete integer differential'
    for row in result['rows']:
        print(('PASS' if row['verdict'] == 'same' else 'FAIL') + ' integer-' + args.mode + '-' + row['file'] + ' ' + row['verdict'], flush=True)
    print('INTEGER-VERDICTS ' + json.dumps(result['counts'], sort_keys=True), flush=True)
    return int(run.returncode != 0 or result['counts']['same'] != 60)


if __name__ == '__main__':
    raise SystemExit(main())
