#!/usr/bin/env python3
"""Compile an external consumer of `types.load`, the typed entry every driver
command shares, from tracked module bytes, and run it on fixtures: a module
member must be refused (F0001, status 4), not typed as one file."""
from pathlib import Path
import os
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/front'))
from check import invoke  # noqa: E402

os.environ['WOLF_STD'] = str(ROOT / '.wolf-bin/std')
(ROOT / 'target').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='types-api-', dir=ROOT / 'target') as work:
    work = Path(work)
    build = work / 'consumer'
    build.mkdir()
    for module in ('coverage', 'front', 'resolve', 'sem', 'types'):
        shutil.copytree(ROOT / 'src' / module, build / module)
    shutil.copyfile(ROOT / 'tests/types/api.lu', build / 'main.lu')
    built = invoke([str(ROOT / '.wolf-bin/wolf'), 'build', '--deny-warnings', str(build / 'main.lu'), '-o',
                    str(work / 'consumer.bin')], timeout=120)
    if built.returncode:
        print('FAIL typed-load-build: ' + built.stderr.decode(errors='replace')[:800])
        sys.exit(1)
    module = work / 'module'
    module.mkdir()
    (module / 'entry.lu').write_text('fn main() -> int { helper() }\n')
    (module / 'helper.lu').write_text('fn helper() -> int { 0 }\n')
    single = work / 'single'
    single.mkdir()
    (single / 'hello.lu').write_text('fn main() -> int {\n    print("hello, wolf")\n    0\n}\n')
    broken = work / 'broken'
    broken.mkdir()
    (broken / 'bad.lu').write_text('fn main() -> int { let x = ( }\n')
    result = invoke([str(work / 'consumer.bin'), str(module / 'entry.lu'), str(single / 'hello.lu'), str(broken / 'bad.lu')])
    if result.returncode or result.stdout != b'typed entry: ok\n':
        print(f'FAIL typed-load-module-member status={result.returncode} stdout={result.stdout!r} '
              f'stderr={result.stderr.decode(errors="replace")[:400]}')
        sys.exit(1)
print('PASS typed-load-module-member')
print('PASS typed-load-one-file')
print('PASS typed-load-syntax-refusal')
