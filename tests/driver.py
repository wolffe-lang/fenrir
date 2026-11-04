#!/usr/bin/env -S python3 -I
"""Exercise the actual stage-0-built frame through every public driver seam."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='driver-', dir=ROOT / 'target') as work:
    work = Path(work)
    source = work / 'input.lu'
    source.write_text('fn main() -> int { 0 }\n')
    output = work / 'output'
    output.write_bytes(b'preserve existing output')
    for args in ([], ['--bogus'], [str(source)], ['build', str(source), '-o', str(output)],
                 ['run', str(source)], ['--emit=tokens', str(source)], ['--emit=ast', str(source)],
                 ['asm', str(source), '-o', str(output)], ['fir', str(source), '-o', str(output)],
                 ['link', str(source), '-o', str(output)]):
        result = subprocess.run([str(ROOT / 'target/fenrir'), *args], capture_output=True)
        if result.returncode != 2 or b'fenrir:' not in result.stderr:
            raise SystemExit(f'driver refusal failed: {args}: {result.returncode}: {result.stderr!r}')
        if output.read_bytes() != b'preserve existing output':
            raise SystemExit('driver replaced output on refusal')
print('driver integration: every dispatch refuses with status 2; existing output preserved')
