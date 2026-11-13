#!/usr/bin/env python3
"""The frozen string Prediction, through lowering or either execution path.

Every selected row must pass. Refusal, crash, missing output and disagreement
are failures; the suite never borrows a prior verdict table as a result.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--mode', choices=('lower', 'interpreter', 'native'), default='lower')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--corpus-root', type=Path, default=ROOT / '.wolf-bin/reference')
    parser.add_argument('--oracle', type=Path, default=ROOT / 'tests/oracle.json')
    args = parser.parse_args()
    prediction = json.loads((ROOT / 'tests/types/fn07-needs.json').read_text())
    names = prediction['groups']['str']
    assert len(names) == 32 and len(set(names)) == 32, 'the frozen string Prediction changed'
    args.out.mkdir(parents=True, exist_ok=True)
    selection = args.out / 'selection.json'
    selection.write_text(json.dumps(names, indent=1) + '\n')
    if args.mode == 'lower':
        results = []
        source_hashes = {r['file']: r['sha256'] for r in prediction['rows']}
        for index, name in enumerate(names):
            source = args.corpus_root / name
            assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hashes[name], name
            command = [str(args.compiler.resolve()), '--emit=fir', str(source.resolve())]
            run = subprocess.run(command, capture_output=True, timeout=30)
            (args.out / f'{index}.fir').write_bytes(run.stdout)
            (args.out / f'{index}.stderr').write_bytes(run.stderr)
            ok = run.returncode == 0 and run.stdout.startswith(b'fir ')
            print(('PASS' if ok else 'FAIL') + ' string-' + name + ' lower exit=' + str(run.returncode), flush=True)
            results.append(dict(file=name, passed=ok, status=run.returncode))
        (args.out / 'lower.json').write_text(json.dumps(results, indent=1) + '\n')
        return int(any(not result['passed'] for result in results))
    command = [str(ROOT / 'tools/differ'), 'compare', '--input', str(args.oracle),
               '--fenrir', str(args.compiler.resolve()), '--select', str(selection),
               '--output', str(args.out / 'comparison.json'), '--table', str(args.out / 'verdicts.json')]
    if args.mode == 'interpreter':
        command.append('--interpreter')
    with (args.out / 'compare.stdout').open('wb') as stdout:
        run = subprocess.run(command, cwd=ROOT, stdout=stdout, env=os.environ.copy())
    table = json.loads((args.out / 'verdicts.json').read_text())
    assert [row['file'] for row in table['rows']] == sorted(names), 'incomplete string differential'
    for row in table['rows']:
        print(('PASS' if row['verdict'] == 'same' else 'FAIL') + ' string-' + row['file'] + ' ' + row['verdict'], flush=True)
    print('STRING-VERDICTS ' + json.dumps(table['counts'], sort_keys=True), flush=True)
    return int(run.returncode != 0 or table['counts']['same'] != len(names))


if __name__ == '__main__':
    raise SystemExit(main())
