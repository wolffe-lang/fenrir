#!/usr/bin/env python3
"""[mem.region.outer-write]: where fenrir makes a `copy` stored into an outer value, and what it refuses.

A `copy` written at a store into an outer value is made in the outer value's region (docs/LOWERING.md). fenrir
names that region statically, so a store it cannot place is refused by name (F0001) before lowering, never placed
in the wrong region. Each refused shape is a row; `born-by-call` is a named over-refusal: fenrir's stand-in would
place it right, but fenrir cannot prove it. Each placed program runs on the given engine and must print the
reference's answer, recorded here from the pinned release. NATIVE_DEFECTS explicitly names the native
copy refusals; those expectations come from the specification and lupin 0.1.62, not a refused native run.
One placed program reads its caller's entry ambient through a probe region: its FIR frees that region in the same
block that made it, right after it is left, so no path leaves it live.

  outer_write.py check --compiler FENRIR --engine interpreter|native --out DIR

Prediction for the aggregate-copy repair: enum-copy-fixed prints `1 2`, not
`2 2`; enum-outer prints `x7` after the source region is freed, without a
region-fault. Both released oracles agree. No syntax, FIR edition, ABI or
corpus membership changes. Inactive variant storage must never be read.

Cost: four refusals and ten small programs. Result ok/error and caught-row copies
must also be independent; outward result payloads must survive the source region.
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
    # [mem.tier0.move.3]: changing a copied active enum payload must not change its source.
    ('enum-copy-fixed', '''enum E { A(List[int]), B }
fn size(e: E) -> int { match e { A(xs) => xs.len, B => 0 } }
fn grow(mut e: E) {
    match e {
        A(xs) => {
            var ys = move xs
            (mut ys).push(2)
            e = E.A(move ys)
        },
        B => { e = E.B }
    }
}
fn main() {
    let a = E.A([1])
    var b = copy a
    grow(mut b)
    print("{size(a)} {size(b)}")
}
''', '1 2\n'),
    # [mem.region.outer-write]: an enum's active str payload must be materialized too.
    ('enum-outer', '''enum E { A(str), B }
fn text(e: E) -> str { match e { A(s) => s, B => "" } }
fn main() {
    var keep = E.B
    region r { keep = copy E.A("x{7}") }
    print("{text(keep)}")
}
''', 'x7\n'),
    ('result-ok-copy', '''fn make() -> List[int] ! {Bad(List[int])} { [1] }
fn main() {
    let a = make()
    let b = copy a
    var c = b else |e| match e { Bad(xs) => xs }
    (mut c).push(2)
    let d = a else |e| match e { Bad(xs) => xs }
    print("{d.len} {c.len}")
}
''', '1 2\n'),
    ('result-error-copy', '''fn make() -> List[int] ! {Bad(List[int])} { Bad([1]) }
fn main() {
    let a = make()
    let b = copy a
    var c = b else |e| match e { Bad(xs) => xs }
    (mut c).push(2)
    let d = a else |e| match e { Bad(xs) => xs }
    print("{d.len} {c.len}")
}
''', '1 2\n'),
    # Empty active variants must not interpret pointer-shaped inactive payload padding.
    ('enum-empty-copy', '''enum E { Empty, Data(List[str], str) }
fn main() {
    let a = E.Empty
    let b = copy a
    var keep = E.Empty
    region r { keep = copy b }
    print("{a} {keep}")
}
''', 'E.Empty E.Empty\n'),
    ('result-outer', '''fn make() -> str ! {Bad(str)} { Bad("x{7}") }
fn main() {
    var keep: str ! {Bad(str)} = ""
    region r { keep = copy make() }
    let s = keep else |e| match e { Bad(s) => s }
    print(s)
}
''', 'x7\n'),
    ('caught-row-copy', '''fn make() -> int ! {Bad(List[int])} { Bad([1]) }
fn main() {
    let n = make() else |e| {
        let f = copy e
        var xs = match f { Bad(xs) => xs }
        (mut xs).push(2)
        let ys = match e { Bad(ys) => ys }
        print("{ys.len} {xs.len}")
        0
    }
    print("{n}")
}
''', '1 2\n0\n'),
]

# These accepted shapes expose the released native compiler's documented copy gap.
# Their answers come from the specification and lupin, never parity credit for a refusal.
NATIVE_DEFECTS = {
    'result-ok-copy': 'wolf-lang#404',
    'result-error-copy': 'wolf-lang#404',
    'result-outer': 'wolf-lang#404',
    'caught-row-copy': 'wolf-lang#404',
}

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


def reference_cases(out):
    """Recheck both released binaries; a listed native defect must remain a refusal, not a pass."""
    root = Path(__file__).resolve().parents[2]
    failures = 0
    for name, source, want in PLACED:
        work = out / 'reference' / name
        work.mkdir(parents=True, exist_ok=True)
        src = work / 'main.lu'
        src.write_text(source)
        native = run([str(root / '.wolf-bin/wolf'), 'run', '--no-cache', str(src)], work)
        interp = run([str(root / '.wolf-bin/lupin'), 'conform-run', '--json', str(src)], work)
        try:
            observed = json.loads(interp.stdout)
        except (ValueError, TypeError):
            observed = {}
        known = name in NATIVE_DEFECTS
        native_ok = native.returncode == 4 and b'cannot compile this yet' in native.stderr and b'copy' in native.stderr \
            if known else native.returncode == 0 and native.stdout.decode(errors='replace') == want
        lupin_ok = interp.returncode == 0 and observed.get('verdict') == 'exit(0)' \
            and (observed.get('stdout_inline') or '') == want
        ok = native_ok and lupin_ok
        detail = f'native refusal listed as {NATIVE_DEFECTS[name]}; no native parity credit' if known else 'both oracles run'
        print(('PASS' if ok else 'FAIL') + f' outer-write-reference-{name} {detail}'
              + ('' if ok else f'; native {native.returncode} {native.stdout[:100]!r} {native.stderr[:180]!r}; lupin {observed!r}'), flush=True)
        failures += not ok
    return failures


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('check',))
    p.add_argument('--compiler', required=True, type=Path)
    p.add_argument('--engine', required=True, choices=('interpreter', 'native'))
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--reference', action='store_true')
    a = p.parse_args()
    if a.engine == 'native':
        assert sys.platform == 'linux', 'native execution requires Linux, not a skip'
    fenrir = str(a.compiler.resolve())
    out = a.out.resolve()
    failures = reference_cases(out) if a.reference else 0
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
              + ((f'the specification and lupin answer; native defect {NATIVE_DEFECTS[name]}' if name in NATIVE_DEFECTS
                  else 'the reference\'s answer') if ok else f'exit {r.returncode} {outcome!r} {r.stdout[:120]!r} {r.stderr[:160]!r}; wanted {want!r}'), flush=True)
        failures += not ok
    print(f'outer-write: {len(REFUSED)} refusals, {len(PLACED)} placed programs on the {a.engine}, {failures} failed', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
