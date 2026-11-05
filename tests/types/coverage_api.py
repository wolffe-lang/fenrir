#!/usr/bin/env python3
"""Standalone bounded coverage API, truth-table and worklist integration tests."""
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def capped():
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))


def main():
    (ROOT / 'target').mkdir(exist_ok=True)
    env = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'),
               WOLF_RT_LIB=str(ROOT / '.wolf-bin/libwolf_rt.a'))
    records = {}
    with tempfile.TemporaryDirectory(prefix='coverage-api-', dir=ROOT / 'target') as work:
        work = Path(work)
        source = work / 'source'
        source.mkdir()
        if (ROOT / 'src/coverage').is_dir():
            shutil.copytree(ROOT / 'src/coverage', source / 'coverage')
        shutil.copyfile(ROOT / 'tests/types/coverage_api.lu', source / 'main.lu')
        binary = work / 'consumer'
        built = subprocess.run([str(ROOT / '.wolf-bin/wolf'), 'build', '--no-cache', '--deny-warnings',
                                str(source / 'main.lu'), '-o', str(binary)],
                               env=env, capture_output=True, timeout=120)
        if built.returncode:
            print(f'FAIL coverage-api-build status={built.returncode} ' + built.stderr.decode(errors='replace')[:6000])
            return 1
        for mode in ('algebra', 'linear', 'adversarial'):
            takes = []
            for _ in range(2):
                result = subprocess.run([str(binary), mode], capture_output=True,
                                        preexec_fn=capped, timeout=60)
                if result.returncode or result.stderr:
                    print(f'FAIL coverage-{mode} status={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}')
                    return 1
                takes.append(result.stdout.decode())
            if takes[0] != takes[1]:
                print(f'FAIL coverage-{mode}-determinism {takes!r}')
                return 1
            if mode == 'adversarial' and not takes[0].startswith('refused cap='):
                print('FAIL coverage-adversarial-missing-refusal')
                return 1
            records[mode] = takes[0]
            print(f'PASS coverage-{mode} ' + takes[0].strip().replace('\n', '; '))
    (ROOT / 'target/coverage-api.json').write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
