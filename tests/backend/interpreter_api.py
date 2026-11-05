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
    print('PASS interpreter-api-outcomes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
