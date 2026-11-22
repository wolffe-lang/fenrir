#!/usr/bin/env python3
"""Wide values: the x86-64 text of a copy must not grow with the value's width.

A value of more than 16 words (the emitter's straight-line limit) is copied by a counted loop;
16 words and fewer stay straight-line moves. The assembler meets the emitted text, and its peak
memory grows with that text: copying every word of a 401-word struct as its own pair of moves,
at each of fifty copies, gave a megabyte of assembly that the assembler could not hold in the
2 GiB build cap (corpus/memory/read_lend_frame.lu).

  copy_width.py size COMPILER --out DIR
      the assembly of corpus/memory/read_lend_frame.lu stays under SIZE_LIMIT bytes.
  copy_width.py curve COMPILER --out DIR
      a struct of n words copied through n `mut` calls, at n = 10, 40, 160: each fourfold step
      may emit at most CURVE_LIMIT times the assembly (straight-line copies grow sixteenfold).
  copy_width.py cases COMPILER --out DIR [--reference] [--native]
      every copy path at widths 14 to 17 and 400, so each path's width (the struct, the struct
      plus a tag, the struct plus two fields) is seen at 16 words and at 17. The answers are the
      reference's: --reference runs its checked machine on each program and requires the stdout
      written here. The interpreter runs on every OS; --native builds under the differ's 2 GiB
      build cap and runs on Linux.

The curve and the size are deterministic byte counts, so they run on any OS. tests/lower/scaling.py
measures the same wide shape's emission time and memory under the Linux cap.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
THRESHOLD = 16
WIDTHS = (14, 15, 16, 17, 400)
SIZE_ROW = ROOT / '.wolf-bin/reference/corpus/memory/read_lend_frame.lu'
# Straight-line text for the row's 401-field literal and its field reads stays; each of its
# fifty wide copies becomes a loop of a few lines: about 90 KB, against 1,017,139 bytes before.
SIZE_LIMIT = 128 * 1024
CURVE = (10, 40, 160)
CURVE_LIMIT = 6
BUILD_ADDRESS_SPACE = 2 << 30


def limits(memory, cpu):
    def apply():
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    return apply


def run(argv, memory=1 << 30, cpu=120, timeout=240, **kw):
    opts = {'preexec_fn': limits(memory, cpu)} if sys.platform == 'linux' else {}
    return subprocess.run([str(x) for x in argv], capture_output=True, timeout=timeout, **opts, **kw)


def declare(w):
    return 'struct S {\n' + ''.join(f'    f{i}: int,\n' for i in range(w)) + '}\n'


def wide_copies(w):
    """A struct of w words, then w `mut` calls on one value: each call copies it in and out."""
    literal = ', '.join(f'f{i}: {i}' for i in range(w))
    calls = ''.join(f'    total += bump(mut s, {i})\n' for i in range(w))
    return (declare(w) + 'fn bump(mut s: S, by: int) -> int {\n    s.f0 += by\n    s.f0\n}\n'
            f'fn main() {{\n    var s = S {{ {literal} }}\n    var total = 0\n{calls}'
            '    print("{total} {s.f0}")\n}\n')


def program(w):
    last = w - 1
    literal = ', '.join(f'f{i}: seed + {i}' for i in range(w))
    weighted = ' + '.join(f's.f{i} * {i + 1}' for i in range(w))
    return declare(w) + f'''struct O {{ head: int, s: S, tail: int }}
enum E {{ Has(S), Empty }}

fn mk(seed: int) -> S {{ S {{ {literal} }} }}
fn sig(s: S) -> int {{ {weighted} }}
fn bump(mut s: S, by: int) {{
    s.f0 += by
    s.f{last} += by
}}
fn pick(c: bool, a: int, b: int) -> S {{
    if c {{ mk(a) }} else {{ mk(b) }}
}}
fn wrap(c: bool, seed: int) -> E {{
    if c {{ E.Has(mk(seed)) }} else {{ E.Empty }}
}}
fn main() {{
    let a = mk(100)
    print("w{w}-return {{sig(a)}} {{a.f0}} {{a.f{last}}}")
    var m = mk(200)
    bump(mut m, 5)
    bump(mut m, 7)
    print("w{w}-mut {{sig(m)}} {{m.f0}} {{m.f{last}}}")
    let p = pick(true, 300, 400)
    let q = pick(false, 300, 400)
    print("w{w}-edge {{sig(p)}} {{sig(q)}}")
    let o = O {{ head: 1, s: mk(500), tail: 2 }}
    print("w{w}-field {{o.head}} {{sig(o.s)}} {{o.tail}}")
    let e1 = wrap(true, 600)
    let v1 = match e1 {{
        Has(s) => sig(s),
        Empty => 0 - 1,
    }}
    let e2 = wrap(false, 600)
    let v2 = match e2 {{
        Has(s) => sig(s),
        Empty => 0 - 1,
    }}
    print("w{w}-enum {{v1}} {{v2}}")
    var xs = List[S]()
    (mut xs).push(mk(700))
    (mut xs).push(mk(800))
    let got = xs.get(1) else mk(0)
    let missing = xs.get(5) else mk(900)
    print("w{w}-list {{sig(xs[0])}} {{sig(got)}} {{sig(missing)}}")
    let popped = (mut xs).pop() else mk(0)
    print("w{w}-pop {{sig(popped)}} {{xs.len}}")
    var table = Map[int, S]()
    table[1] = mk(1000)
    let hit = table[1] else mk(0)
    let miss = table[2] else mk(1100)
    print("w{w}-map {{sig(hit)}} {{sig(miss)}}")
    var cur = mk(1200)
    var i = 0
    while i < 3 {{
        cur = mk(cur.f{last} + 1)
        i += 1
    }}
    print("w{w}-loop {{sig(cur)}} {{cur.f0}}")
}}
'''


def expected(w):
    last = w - 1
    def sig(seed, bumped=0):
        return sum((i + 1) * (seed + i) for i in range(w)) + bumped * (1 + w)
    seed = 1200 + 3 * (last + 1)
    return ''.join(line + '\n' for line in [
        f'w{w}-return {sig(100)} 100 {100 + last}',
        f'w{w}-mut {sig(200, 12)} 212 {200 + last + 12}',
        f'w{w}-edge {sig(300)} {sig(400)}',
        f'w{w}-field 1 {sig(500)} 2',
        f'w{w}-enum {sig(600)} -1',
        f'w{w}-list {sig(700)} {sig(800)} {sig(900)}',
        f'w{w}-pop {sig(800)} 1',
        f'w{w}-map {sig(1000)} {sig(1100)}',
        f'w{w}-loop {sig(seed)} {seed}',
    ])


def assembly(compiler, home, source):
    home.mkdir(parents=True, exist_ok=True)
    (home / 'main.lu').write_text(source)
    p = run([compiler, '--emit=asm', 'main.lu'], cwd=home)
    assert p.returncode == 0, (home.name, p.returncode, p.stderr[:400])
    (home / 'main.s').write_bytes(p.stdout)
    return len(p.stdout)


def size(a):
    got = assembly(a.compiler, a.out / 'read-lend-frame', SIZE_ROW.read_text())
    ok = got <= SIZE_LIMIT
    print(f'{"PASS" if ok else "FAIL"} copy-width-size read_lend_frame emits {got} bytes of assembly, limit {SIZE_LIMIT}', flush=True)
    return 0 if ok else 1


def curve(a):
    sizes = [assembly(a.compiler, a.out / f'wide-{n}', wide_copies(n)) for n in CURVE]
    print('CURVE ' + json.dumps(dict(zip(map(str, CURVE), sizes))), flush=True)
    failed = 0
    for (n, small), (m, big) in zip(zip(CURVE, sizes), zip(CURVE[1:], sizes[1:])):
        ok = big <= CURVE_LIMIT * small
        failed += not ok
        print(f'{"PASS" if ok else "FAIL"} copy-width-curve n={n}->{m}: {small} -> {big} bytes, x{big / small:.1f}, limit x{CURVE_LIMIT}', flush=True)
    return 1 if failed else 0


def checked(home):
    env = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'), WOLF_RT_LIB=str(ROOT / '.wolf-bin/libwolf_rt.a'))
    r = run([ROOT / '.wolf-bin/wolf', 'conform-run', 'main.lu', '--json', '--checked'], cwd=home, env=env)
    (home / 'reference.json').write_bytes(r.stdout)
    (home / 'reference.stderr').write_bytes(r.stderr)
    record = json.loads(r.stdout)
    return record['verdict'], record.get('stdout_inline')


def cases(a):
    failed = seen = 0
    def report(ok, name, detail=''):
        nonlocal failed, seen
        failed += not ok
        seen += 1
        print(('PASS ' if ok else 'FAIL ') + name + (' ' + detail if detail and not ok else ''), flush=True)
    env = dict(os.environ, FENRIR_TOOLCHAIN=str(ROOT / '.wolf-bin'))
    for w in WIDTHS:
        name = f'w{w}'
        home = a.out / name
        home.mkdir(parents=True, exist_ok=True)
        (home / 'main.lu').write_text(program(w))
        want = expected(w)
        if a.reference:
            verdict, stdout = checked(home)
            report((verdict, stdout) == ('exit(0)', want), f'copy-width-reference-{name}', f'{verdict} {stdout!r:.300}')
        lower = run([a.compiler, '--emit=fir', 'main.lu'], cwd=home)
        (home / 'main.fir').write_bytes(lower.stdout)
        if lower.returncode:
            report(False, f'copy-width-lower-{name}', lower.stderr[:300].decode(errors='replace'))
            continue
        p = run([a.compiler, 'interpret', home / 'main.fir', '--steps', '50000000', '--bytes', str(1 << 28),
                 '--report', home / 'outcome.txt'], cwd=home)
        (home / 'interpreter.stdout').write_bytes(p.stdout)
        report((p.returncode, p.stdout.decode(errors='replace')) == (0, want), f'copy-width-interpret-{name}',
               f'{p.returncode} {p.stdout[:300]!r} {p.stderr[:200]!r}')
        if a.native:
            assert sys.platform == 'linux', 'native proof requires Linux; this is not a skip'
            b = run([a.compiler, 'build', 'main.lu', '-o', home / 'program'], memory=BUILD_ADDRESS_SPACE, cpu=300,
                    timeout=600, cwd=home, env=env)
            if b.returncode:
                report(False, f'copy-width-native-{name}', f'build {b.returncode} {b.stderr[-300:]!r}')
                continue
            q = run([home / 'program'], cwd=home)
            (home / 'native.stdout').write_bytes(q.stdout)
            report((q.returncode, q.stdout.decode(errors='replace'), q.stderr) == (0, want, b''), f'copy-width-native-{name}',
                   f'{q.returncode} {q.stdout[:300]!r} {q.stderr[:200]!r}')
    print(f'{"PASS" if not failed else "FAIL"} copy-width-cases {seen - failed}/{seen}', flush=True)
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('size', 'curve', 'cases'))
    ap.add_argument('compiler', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--reference', action='store_true')
    ap.add_argument('--native', action='store_true')
    a = ap.parse_args()
    a.compiler = a.compiler.resolve()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    return dict(size=size, curve=curve, cases=cases)[a.mode](a)


if __name__ == '__main__':
    raise SystemExit(main())
