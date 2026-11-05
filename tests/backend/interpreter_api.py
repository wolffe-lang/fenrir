#!/usr/bin/env python3
"""Build an external in-memory FIR interpreter consumer from tracked modules."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    (ROOT / 'target').mkdir(exist_ok=True)
    env = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'),
               WOLF_RT_LIB=str(ROOT / '.wolf-bin/libwolf_rt.a'))
    with tempfile.TemporaryDirectory(prefix='interpreter-api-', dir=ROOT / 'target') as work:
        work = Path(work)
        source = work / 'source'
        source.mkdir()
        for module in ('fir', 'sem', 'interp'):
            if (ROOT / 'src' / module).is_dir():
                shutil.copytree(ROOT / 'src' / module, source / module)
        shutil.copyfile(ROOT / 'tests/backend/interpreter_api.lu', source / 'main.lu')
        binary = work / 'consumer'
        built = subprocess.run([str(ROOT / '.wolf-bin/wolf'), 'build', '--no-cache', '--deny-warnings',
                                str(source / 'main.lu'), '-o', str(binary)],
                               env=env, capture_output=True, timeout=120)
        if built.returncode:
            print(f'FAIL interpreter-api-build status={built.returncode} ' + built.stderr.decode(errors='replace')[:1600])
            return 1
        result = subprocess.run([str(binary)], capture_output=True, timeout=15)
        if (result.returncode, result.stdout, result.stderr) != (0, b'in-memory interpreter: ok\n', b''):
            print(f'FAIL interpreter-api-outcomes status={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}')
            return 1
        # Inject an internal failure behind the real CLI boundary. Its status
        # must remain 70, never input rejection 2 or budget refusal 4.
        (source / 'main.lu').write_text('use interp\nfn main() -> int { interp.command(env_args()) }\n')
        (source / 'interp/run.lu').write_text('''//! member: true
use fir
/// Probe failures: Bad rejects input; Internal injects an invariant failure.
pub error ProbeFailure = {Bad(str), Internal(str)}
/// Verify input, then return Internal without executing the program.
pub fn run(m: fir.Module, max_steps: int, max_bytes: int) -> Outcome ! ProbeFailure {
    fir.verify(m)?
    if max_steps < 0 || max_bytes < 0 { return Bad("FIR_LIMIT invalid budgets") }
    return Internal("FIR_INTERNAL planted invariant failure")
}
''')
        built = subprocess.run([str(ROOT / '.wolf-bin/wolf'), 'build', '--no-cache', '--deny-warnings',
                                str(source / 'main.lu'), '-o', str(binary)],
                               env=env, capture_output=True, timeout=120)
        if built.returncode:
            print(f'FAIL interpreter-api-internal-build status={built.returncode} ' + built.stderr.decode(errors='replace')[:1600])
            return 1
        report = work / 'outcome'
        report.write_text('preserve\n')
        result = subprocess.run([str(binary), str(ROOT / 'examples/hello.fir'), '--steps', '1000',
                                 '--bytes', '1048576', '--report', str(report)], capture_output=True, timeout=15)
        if result.returncode != 70 or result.stdout or b'FIR_INTERNAL' not in result.stderr or report.read_text() != 'preserve\n':
            print(f'FAIL interpreter-api-internal-status status={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}')
            return 1
    print('PASS interpreter-api-outcomes')
    print('PASS interpreter-api-internal-status')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
