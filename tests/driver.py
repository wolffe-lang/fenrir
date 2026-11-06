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
    for args in ([], ['--bogus'], [str(source)], ['asm', str(source), '-o', str(output)],
                 ['fir', str(source), '-o', str(output)], ['link', str(source), '-o', str(output)],
                 ['build', str(source), '-o', ''], ['build', str(source), '-o', str(source)]):
        result = invoke([str(ROOT / 'target/fenrir'), *args])
        if result.returncode != 2 or b'fenrir:' not in result.stderr:
            raise SystemExit(f'driver refusal failed: {args}: {result.returncode}: {result.stderr!r}')
        if output.read_bytes() != b'preserve existing output':
            raise SystemExit('driver replaced output on refusal')
    # Source commands: a rejection is 2, a refusal outside the core 4 (F0001, or
    # F0003 with no main), each before any link, with the output untouched.
    cases = [('fn f() { let = 1 }\n', 2, b'error[E0207]'), ('fn main() { let xs = [1, 2] }\n', 4, b'error[F0001]'),
             ('fn helper() -> int { 1 }\n', 4, b'error[F0003]'), ('fn main() { print(1) }\n', 2, b'error[E0401]')]
    for text, status, code in cases:
        source.write_text(text)
        for args in (['build', str(source), '-o', str(output)], ['run', str(source)], ['--emit=fir', str(source)], ['--emit=asm', str(source)]):
            result = invoke([str(ROOT / 'target/fenrir'), *args])
            if result.returncode != status or code not in result.stderr or result.stdout:
                raise SystemExit(f'source refusal failed: {args}: {text!r}: {result.returncode}: {result.stderr!r}')
            if output.read_bytes() != b'preserve existing output':
                raise SystemExit('a source refusal replaced the output')
    # A file with a sibling joins its directory's module, which is outside the
    # one-file core: every source command refuses it as the typed view does.
    package = work / 'package'
    package.mkdir()
    (package / 'main.lu').write_text('fn main() { print("hello, wolf") }\n')
    (package / 'sibling.lu').write_text('fn helper() -> int { 1 }\n')
    for args in (['build', str(package / 'main.lu'), '-o', str(output)], ['--emit=fir', str(package / 'main.lu')]):
        result = invoke([str(ROOT / 'target/fenrir'), *args])
        if result.returncode != 4 or b'error[F0001]' not in result.stderr or result.stdout:
            raise SystemExit(f'module member not refused: {args}: {result.returncode}: {result.stderr!r}')
        if output.read_bytes() != b'preserve existing output':
            raise SystemExit('a module-member refusal replaced the output')
    source.write_text('fn main() { print("hello, wolf") }\n')
    for mode, head in (('fir', b'fir 1\n'), ('asm', b'.text\n')):
        first = invoke([str(ROOT / 'target/fenrir'), '--emit=' + mode, str(source)])
        again = invoke([str(ROOT / 'target/fenrir'), '--emit=' + mode, str(source)])
        if first.returncode != 0 or not first.stdout.startswith(head) or first.stdout != again.stdout or first.stderr:
            raise SystemExit(f'--emit={mode} failed or differs between runs: {first.returncode}: {first.stderr!r}')
    source.write_text('fn main() -> int { 0 }\n')
    for mode in ('tokens', 'ast'):
        result = invoke([str(ROOT / 'target/fenrir'), '--emit=' + mode, str(source)])
        if result.returncode != 0 or not result.stdout.startswith((mode + '/1 ').encode()):
            raise SystemExit(f'front-end driver failed: {mode}: {result.stderr!r}')
    source.write_text('fn f() { let = 1 }\n')
    result = invoke([str(ROOT / 'target/fenrir'), '--emit=ast', str(source)])
    if result.returncode != 2 or b'error[E0207]' not in result.stderr or result.stdout:
        raise SystemExit('syntax refusal lost its code or produced an AST')
print('driver integration: front-end acceptance and syntax refusal; backend and source refusals preserve output; --emit=fir|asm stable')
