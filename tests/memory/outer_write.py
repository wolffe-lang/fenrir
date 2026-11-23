#!/usr/bin/env python3
"""[mem.region.outer-write]: where fenrir makes a `copy` stored into an outer value, and what it refuses.

A `copy` written at a store into an outer value is made in the outer value's region (docs/LOWERING.md). fenrir
names that region statically, so a store it cannot place is refused by name (F0001) before lowering, never placed
in the wrong region. Each refused shape is a row; `born-by-call` is a named over-refusal: fenrir's stand-in would
place it right, but fenrir cannot prove it. Each placed program runs on the given engine and must print the
reference's answer, recorded here from the pinned release (macOS native; lupin 0.1.62 agrees on every one).
One placed program reads its caller's entry ambient through a probe region: its FIR frees that region in the same
block that made it, right after it is left, so no path leaves it live.

  outer_write.py check --compiler FENRIR --engine interpreter|native --out DIR

Cost: four refusals and three small programs.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

MK = 'fn mk(r: region) -> List[str] {\n    in r {\n        List[str]()\n    }\n}\n'
REPAIR = 'declare it with a literal, a constructor or a `copy` there'
# (name, source, refusal site, the reference's answer, over-refusal)
REFUSED = [
    ('ledger-in-s', MK + '''fn main() {
    let v = region()
    region s {
        var xs = mk(v)
        let vb = region_bytes(v)
        let sb = region_bytes(s)
        region t {
            (mut xs).push(copy "x{1}")
        }
        print("{xs.len} {xs[0]} {region_bytes(v) > vb} {region_bytes(s) > sb}")
    }
}
''', [13, 13], 'exit(0) "1 x1 true false\\n"', False),
    ('returned-out', MK + '''fn build(v: region) -> List[str] {
    region s {
        var xs = mk(v)
        region t {
            (mut xs).push(copy "x{1}")
        }
        return xs
    }
    List[str]()
}

fn main() {
    let v = region()
    let xs = build(v)
    region other {
        let z = "ZZZZZZZZZZZZZZZZZZZZZZZZ{1}"
        print("{z.len}")
    }
    print("{xs.len} {xs[0]}")
}
''', [10, 13], 'fail(E1010)', False),
    ('mut-param', MK + '''fn fill(mut xs: List[str]) {
    region t {
        (mut xs).push(copy "y{2}")
    }
}

fn main() {
    let v = region()
    var keep = mk(v)
    let vb = region_bytes(v)
    region s {
        fill(mut keep)
    }
    region other {
        let z = "ZZZZZZZZZZZZZZZZZZZZZZZZ{1}"
        print("{z.len}")
    }
    print("{keep.len} {keep[0]} {region_bytes(v) > vb}")
}
''', [17, 14], 'exit(0) "25\\n1 y2 true\\n"', False),
    ('born-by-call', '''fn fresh() -> List[str] {
    List[str]()
}

fn main() {
    var out = List[str]()
    region s {
        var xs = fresh()
        region t {
            (mut xs).push(copy "z{3}")
        }
        out = copy xs
    }
    print("{out.len} {out[0]}")
}
''', [10, 13], 'exit(0) "1 z3\\n"', True),
]

BOOK = 'struct Book {\n    lines: List[str],\n}\n\n'
# (name, source, the reference's stdout); every one exits 0.
PLACED = [
    # A container store through `mut`, called at the caller's own depth outside every block: the caller reads its
    # entry ambient through a probe region for the hidden argument, a thousand times.
    ('probe-at-root', BOOK + '''fn add(mut b: Book, i: int) {
    region t {
        (mut b.lines).push(copy "line {i}")
    }
}

fn main() {
    var b = Book { lines: List[str]() }
    let base = live_region_bytes()
    var i = 0
    while i < 1000 {
        add(mut b, i)
        i += 1
    }
    region other {
        let z = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ{i}"
        print("{z.len}")
    }
    print("{b.lines.len} {b.lines[0]} {b.lines[999]} {live_region_bytes() == base}")
}
''', '34\n1000 line 0 line 999 true\n'),
    # Called from inside a block: the hidden argument is the region where `b` was declared, not the block.
    ('called-from-a-block', BOOK + '''fn add(mut b: Book, i: int) {
    (mut b.lines).push(copy "line {i}")
}

fn main() {
    var b = Book { lines: List[str]() }
    var i = 0
    while i < 100 {
        region turn {
            add(mut b, i)
        }
        i += 1
    }
    region other {
        let z = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ{i}"
        print("{z.len}")
    }
    print("{b.lines.len} {b.lines[0]} {b.lines[99]}")
}
''', '33\n100 line 0 line 99\n'),
    # A `mut` parameter passed on: its hidden region passes with it.
    ('passed-on', BOOK + '''fn add(mut b: Book, i: int) {
    region t {
        (mut b.lines).push(copy "line {i}")
    }
}

fn twice(mut b: Book, i: int) {
    add(mut b, i)
    add(mut b, i + 1)
}

fn main() {
    var b = Book { lines: List[str]() }
    region turn {
        twice(mut b, 1)
    }
    region other {
        let z = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
        print("{z.len}")
    }
    print("{b.lines.len} {b.lines[0]} {b.lines[1]}")
}
''', '30\n2 line 1 line 2\n'),
]

REGION = re.compile(r'^region (\d+) (\d+) 1 ([1-7]) (\d+)(?: (\d+))?$')


def probes_freed(fir):
    """Every probe region (made, entered, left at once) is freed by the very next instruction."""
    lines = fir.splitlines()
    probes = freed = 0
    for i, line in enumerate(lines[:-3]):
        ops = [REGION.match(x) for x in lines[i:i + 4]]
        if ops[0] and ops[0][3] == '1' and ops[1] and ops[1][3] == '3' and ops[2] and ops[2][3] == '4':
            probes += 1
            freed += bool(ops[3] and ops[3][3] == '5')
    return probes, freed


def run(argv, cwd):
    return subprocess.run(argv, cwd=cwd, capture_output=True, timeout=300)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('check',))
    p.add_argument('--compiler', required=True, type=Path)
    p.add_argument('--engine', required=True, choices=('interpreter', 'native'))
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    if a.engine == 'native':
        assert sys.platform == 'linux', 'native execution requires Linux, not a skip'
    fenrir = str(a.compiler.resolve())
    out = a.out.resolve()
    failures = 0
    for name, source, site, reference, over in REFUSED:
        work = out / name
        work.mkdir(parents=True, exist_ok=True)
        (work / 'main.lu').write_text(source)
        r = run([fenrir, '--emit=fir', str(work / 'main.lu')], work)
        err = r.stderr.decode(errors='replace')
        where = f'main.lu:{site[0]}:{site[1]}: error[F0001]'
        ok = r.returncode == 4 and where in err and REPAIR in err and not r.stdout
        kind = 'over-refusal' if over else 'refusal'
        print(('PASS' if ok else 'FAIL') + f' outer-write-refuses-{name} {kind} F0001 at {site[0]}:{site[1]}; the reference: {reference}'
              + ('' if ok else f'; fenrir exit {r.returncode}: {err[:240]!r}'), flush=True)
        failures += not ok
    for name, source, want in PLACED:
        work = out / name
        work.mkdir(parents=True, exist_ok=True)
        (work / 'main.lu').write_text(source)
        if a.engine == 'interpreter':
            fir = run([fenrir, '--emit=fir', str(work / 'main.lu')], work)
            if fir.returncode != 0:
                print(f'FAIL outer-write-{name}-{a.engine} fenrir exit {fir.returncode}: {fir.stderr.decode(errors="replace")[:240]!r}', flush=True)
                failures += 1
                continue
            (work / 'main.fir').write_bytes(fir.stdout)
            if name == 'probe-at-root':
                probes, freed = probes_freed(fir.stdout.decode())
                ok = probes > 0 and probes == freed
                print(('PASS' if ok else 'FAIL') + f' outer-write-probe-freed {freed} of {probes} probe regions freed right after they are left', flush=True)
                failures += not ok
            r = run([fenrir, 'interpret', str(work / 'main.fir'), '--steps', '20000000', '--bytes', str(64 << 20),
                     '--report', str(work / 'outcome.txt')], work)
            outcome = (work / 'outcome.txt').read_text() if (work / 'outcome.txt').is_file() else None
        else:
            built = run([fenrir, 'build', str(work / 'main.lu'), '-o', str(work / 'program')], work)
            if built.returncode != 0:
                print(f'FAIL outer-write-{name}-{a.engine} build exit {built.returncode}: {built.stderr.decode(errors="replace")[:240]!r}', flush=True)
                failures += 1
                continue
            r = run([str(work / 'program')], work)
            outcome = f'exit {r.returncode}\n'
        ok = r.returncode == 0 and outcome == 'exit 0\n' and r.stdout.decode(errors='replace') == want
        print(('PASS' if ok else 'FAIL') + f' outer-write-{name}-{a.engine} '
              + ('the reference\'s answer' if ok else f'exit {r.returncode} {outcome!r} {r.stdout[:120]!r} {r.stderr[:160]!r}; wanted {want!r}'), flush=True)
        failures += not ok
    print(f'outer-write: {len(REFUSED)} refusals, {len(PLACED)} placed programs on the {a.engine}, {failures} failed', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
