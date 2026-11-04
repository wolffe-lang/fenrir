#!/usr/bin/env python3
"""Compile an external arena consumer from tracked fixture and module bytes."""
from pathlib import Path
import os
import shutil
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/front'))
from check import invoke
os.environ['WOLF_STD'] = str(ROOT / '.wolf-bin/std')
with tempfile.TemporaryDirectory(prefix='front-api-', dir=ROOT / 'target') as work:
    work = Path(work)
    shutil.copytree(ROOT / 'src/front', work / 'front')
    shutil.copyfile(ROOT / 'tests/front/api.lu', work / 'main.lu')
    built = invoke([str(ROOT / '.wolf-bin/wolf'), 'build', '--deny-warnings', str(work / 'main.lu'), '-o', str(work / 'consumer')], timeout=120)
    if built.returncode:
        raise SystemExit('FAIL public-arena-build: ' + built.stderr.decode(errors='replace'))
    result = invoke([str(work / 'consumer')])
    if result.returncode or result.stdout != b'public arena interface: ok\n':
        raise SystemExit('FAIL public-arena-run: ' + repr(result))
print('PASS public-arena-consumer')
