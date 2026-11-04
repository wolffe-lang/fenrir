#!/usr/bin/env -S python3 -I
"""Exercise the actual built driver through every public command seam."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/front'))
from check import invoke

with tempfile.TemporaryDirectory(prefix='driver-', dir=ROOT / 'target') as work:
    work = Path(work)
    source = work / 'input.lu'
    source.write_text('fn main() -> int { 0 }\n')
    output = work / 'output'
    output.write_bytes(b'preserve existing output')
    for args in ([], ['--bogus'], [str(source)], ['build', str(source), '-o', str(output)],
                 ['run', str(source)], ['asm', str(source), '-o', str(output)],
                 ['fir', str(source), '-o', str(output)], ['link', str(source), '-o', str(output)]):
        result = invoke([str(ROOT / 'target/fenrir'), *args])
        if result.returncode != 2 or b'fenrir:' not in result.stderr:
            raise SystemExit(f'driver refusal failed: {args}: {result.returncode}: {result.stderr!r}')
        if output.read_bytes() != b'preserve existing output':
            raise SystemExit('driver replaced output on refusal')
    for mode in ('tokens', 'ast'):
        result = invoke([str(ROOT / 'target/fenrir'), '--emit=' + mode, str(source)])
        if result.returncode != 0 or not result.stdout.startswith((mode + '/1 ').encode()):
            raise SystemExit(f'front-end driver failed: {mode}: {result.stderr!r}')
    source.write_text('fn f() { let = 1 }\n')
    result = invoke([str(ROOT / 'target/fenrir'), '--emit=ast', str(source)])
    if result.returncode != 2 or b'error[E0207]' not in result.stderr or result.stdout:
        raise SystemExit('syntax refusal lost its code or produced an AST')
print('driver integration: front-end acceptance and syntax refusal; backend refusals preserve output')
