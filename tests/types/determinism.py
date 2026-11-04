#!/usr/bin/env python3
"""--emit=typed is deterministic: every corpus file, typed twice, gives the
same bytes on stdout and stderr and the same status."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def observe(binary, source):
    r = subprocess.run([str(binary), '--emit=typed', str(source)], capture_output=True, timeout=30)
    return r.returncode, hashlib.sha256(r.stdout).hexdigest(), hashlib.sha256(r.stderr).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('binary', type=Path)
    p.add_argument('--corpus', type=Path, default=ROOT / '.wolf-bin/reference/corpus')
    a = p.parse_args()
    sources = sorted(a.corpus.rglob('*.lu'))
    with ThreadPoolExecutor(4) as pool:
        first = list(pool.map(lambda s: observe(a.binary, s), sources))
        second = list(pool.map(lambda s: observe(a.binary, s), sources))
    differ = [str(s) for s, x, y in zip(sources, first, second) if x != y]
    typed = sum(x[0] == 0 for x in first)
    for name in differ:
        print('FAIL typed-determinism ' + name)
    print(f'typed determinism: {len(sources)} files typed twice, {typed} typed trees, {len(differ)} differ')
    return 1 if differ else 0


if __name__ == '__main__':
    sys.exit(main())
