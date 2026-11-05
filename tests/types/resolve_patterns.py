#!/usr/bin/env python3
"""External resolver consumer: enum identity, constructors and arm scopes."""
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
    with tempfile.TemporaryDirectory(prefix='resolve-patterns-', dir=ROOT / 'target') as work:
        work = Path(work)
        source = work / 'source'
        source.mkdir()
        for module in ('front', 'resolve'):
            shutil.copytree(ROOT / 'src' / module, source / module)
        shutil.copyfile(ROOT / 'tests/types/resolve_patterns.lu', source / 'main.lu')
        binary = work / 'consumer'
        built = subprocess.run([str(ROOT / '.wolf-bin/wolf'), 'build', '--no-cache', '--deny-warnings',
                                str(source / 'main.lu'), '-o', str(binary)],
                               env=env, capture_output=True, timeout=120)
        if built.returncode:
            print(f'FAIL enum-pattern-resolver-build status={built.returncode} ' + built.stderr.decode(errors='replace')[:6000])
            return 1
        result = subprocess.run([str(binary)], capture_output=True, timeout=15)
        if (result.returncode, result.stdout, result.stderr) != (0, b'enum-pattern-resolution: ok\n', b''):
            print(f'FAIL enum-pattern-resolution status={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}')
            return 1
    print('PASS enum-pattern-resolution')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
