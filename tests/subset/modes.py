#!/usr/bin/env python3
"""The compiled claims `keyword:mut`, `keyword:move` and `keyword:copy` (docs/SUBSET.md, F3).

Each witness uses its keyword the way fenrir's own source does: `mut` parameters, `mut` arguments
naming a variable, a field and an element, and `mut` receivers of list methods; `move` out of a
variable into a binding and into a struct field, a `take` argument, and a store that makes the moved
variable live again; `copy` of a struct and of a nested list, each copy grown without touching its
source. Each is built to FIR by `target/fenrir` and run by its interpreter, so the row runs on every
OS that runs `ci/check`; the answers are the pinned wolf's (`wolf run`, native), recorded below.
Exit 0 only when every witness prints its answer.

  python3 -I tests/subset/modes.py
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FENRIR = ROOT / 'target/fenrir'

WITNESSES = {
    'mut': ('''struct Acc {
    items: List[int],
    n: int,
}

fn bump(mut a: int, by: int) {
    a += by
}

fn grow(mut acc: Acc, v: int) -> int {
    (mut acc.items).push(v)
    acc.n += 1
    acc.n
}

fn main() {
    var acc = Acc { items: [1], n: 1 }
    var xs = [10, 20]
    let k = grow(mut acc, 7)
    bump(mut acc.n, 5)
    bump(mut xs[1], 2)
    (mut xs).push(k)
    print("{acc.items.len} {acc.n} {xs[1]} {xs.len} {k}")
}
''', '2 7 22 3 2\n'),
    'move': ('''struct Box {
    items: List[int],
}

fn total(take xs: List[int]) -> int {
    var t = 0
    for x in xs {
        t += x
    }
    t
}

fn main() {
    var xs = [1, 2, 3]
    let ys = move xs
    xs = [4]
    let b = Box { items: move xs }
    print("{ys.len} {b.items[0]} {total(take ys)}")
}
''', '3 4 6\n'),
    'copy': ('''struct Node {
    vals: List[int],
    tag: str,
}

fn main() {
    let a = Node { vals: [1, 2], tag: "a" }
    var b = copy a
    (mut b.vals).push(3)
    b.tag = "b"
    let grid = [[1], [2, 3]]
    var g = copy grid
    (mut g[0]).push(9)
    print("{a.vals.len} {b.vals.len} {a.tag}{b.tag} {grid[0].len} {g[0].len}")
}
''', '2 3 ab 1 2\n'),
}


def main():
    if not FENRIR.is_file():
        print(f'FAIL subset-modes no compiler at {FENRIR}', flush=True)
        return 1
    env = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'))
    failed = 0
    (ROOT / 'target').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='subset-modes-', dir=ROOT / 'target') as temp:
        for name, (source, answer) in WITNESSES.items():
            # Every `.lu` file in a directory joins its module: one directory per witness.
            work = Path(temp) / name
            work.mkdir()
            (work / 'main.lu').write_text(source)
            fir = subprocess.run([str(FENRIR), '--emit=fir', 'main.lu'], cwd=work, env=env, capture_output=True, timeout=120)
            if fir.returncode != 0:
                failed += 1
                print(f'FAIL subset-modes {name} fir exit {fir.returncode}: {fir.stderr.decode(errors="replace")[:300]}', flush=True)
                continue
            (work / 'main.fir').write_bytes(fir.stdout)
            ran = subprocess.run([str(FENRIR), 'interpret', 'main.fir', '--steps', '20000000', '--bytes', '67108864',
                                  '--report', 'outcome.txt'], cwd=work, env=env, capture_output=True, timeout=120)
            got = ran.stdout.decode(errors='replace')
            if ran.returncode != 0 or got != answer:
                failed += 1
                print(f'FAIL subset-modes {name} exit {ran.returncode} printed {got!r}, the reference {answer!r}', flush=True)
            else:
                print(f'PASS subset-modes {name}', flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
