#!/usr/bin/env python3
"""Parameter modes, moves and copies: what the caller sees, answered by the released reference.

Each program here prints one line per case, `ID text`. The answers are never computed here:
`capture` runs the pinned wolf (native tier) and lupin on each program and records what they
print, trap or refuse; `check` builds the same programs with fenrir, on either engine, and
compares case by case with the committed table. `table` requires the committed table to name
exactly these programs, by digest.

The answer is the native compiler's, with two exceptions, each listed and counted:
- `KNOWN_COMPILER_DIFFERENCES`: a case where the specification settles the meaning against the
  native compiler (a store through a `for` binding holds the binding's own value, wolf-lang#1169).
  Its answer is lupin's, and the capture fails if the compiler stops differing. F3b has none:
  fenrir keeps every store through a `for` binding refused (E0410), so no case here makes one.
- `NATIVE_DEFECTS`: a program the released Linux compiler cannot build (its `copy` refusals,
  wolf-lang#404). Its answer is lupin's, and the capture fails if the compiler builds it.

The rows cover every value kind under `read`, `mut`, `take`, `move` and `copy`, and copy depth.
They also cover the places where returning `mut` values (fenrir's copy-in, copy-out through
caller temporaries, docs/MEMORY.md) could differ from passing a place:
- every return path (a plain return, an early `return`, `?` propagating, falling off the end);
- a `mut` parameter passed on one and two levels, and twice in sequence;
- several `mut` arguments in one call;
- element and field arguments whose index the callee changes through another `mut` parameter.

A trap inside the callee ends the process, so nothing afterwards can tell the two apart; no row
pretends to. A program the reference refuses for exclusivity is a typed row with a named
difference (tests/types/memory_rows.py), never a case here.

  mode_cases.py table [--table PATH]
  mode_cases.py capture --out PATH       (Linux x86-64; FENRIR_ORACLE_SANDBOX=1 inside the container)
  mode_cases.py check --compiler F --engine native|interpreter --out DIR [--table PATH]
  mode_cases.py write-programs --out DIR
  mode_cases.py paths                    (any OS: every file a child is given is named from its own folder)

Cost: linear in the programs; each is built and run once per engine.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
TABLE = ROOT / 'tests/memory/mode-cases.json'

# Case id -> the issue that settles it against the native compiler; the answer is lupin's.
KNOWN_COMPILER_DIFFERENCES = {}
# Program -> the issue for a program the released Linux compiler cannot build; the answer is lupin's.
NATIVE_DEFECTS = {}

# One program per value kind: `read` leaves the caller's value alone, `mut` writes it back, `take`
# consumes it, `move` transfers it, and `copy` gives an independent value the caller can change.
KINDS = [
    # (name, items, type, initial value, a write through a `mut` place `x`, a rendering of `x`)
    ('int', '', 'int', '41', 'x += 1', '{x}'),
    ('i32', '', 'i32', '7', 'x = x * 3', '{x}'),
    ('u8', '', 'u8', '250', 'x += 5', '{x}'),
    ('bool', '', 'bool', 'false', 'x = !x', '{x}'),
    ('char', '', 'char', "'a'", "x = 'z'", '{x}'),
    ('byte', '', 'byte', '65 as byte', 'x = 66 as byte', '{x}'),
    ('str', '', 'str', '"wolf"', 'x += "!"', '{x}'),
    ('f64', '', 'f64', '1.5', 'x = x * 2.0', '{x}'),
    ('struct', 'struct P { a: int, b: int }\n', 'P', 'P { a: 1, b: 2 }', 'x.a += 10', '{x.a} {x.b}'),
    ('enum', 'enum E { A, B(int) }\n', 'E', 'E.A', 'x = E.B(5)', '{x}'),
    ('tuple', '', '(int, bool)', '(3, true)', 'x = (x.0 + 1, !x.1)', '{x.0} {x.1}'),
    ('list', '', 'List[int]', '[1, 2]', '(mut x).push(9)', '{x}'),
    ('map', '', 'Map[str, int]', 'Map[str, int]()', 'x["k"] = 2', '{x.len} {x["k"] else 0}'),
    ('nested', 'struct H { tag: int, items: List[int] }\n', 'H', 'H { tag: 1, items: [5] }',
     '(mut x.items).push(6)', '{x.tag} {x.items}'),
    ('list-of-lists', '', 'List[List[int]]', '[[1], [2, 3]]', '(mut x[0]).push(7)', '{x}'),
]


def kind_program(name, items, ty, init, write, render):
    k = name
    show = lambda var: render.replace('x', var)
    return f'''{items}fn rd(x: {ty}) -> str {{ "{render}" }}
fn mu(mut x: {ty}) {{ {write} }}
fn tk(take x: {ty}) -> str {{ "{render}" }}
fn main() -> int {{
    var r: {ty} = {init}
    print("{k}-read {{rd(r)}} {show('r')}")
    var m: {ty} = {init}
    mu(mut m)
    print("{k}-mut {show('m')}")
    var t: {ty} = {init}
    print("{k}-take {{tk(take t)}}")
    var v: {ty} = {init}
    let w = move v
    print("{k}-move {show('w')}")
    var o: {ty} = {init}
    var c = copy o
    mu(mut c)
    print("{k}-copy {show('o')} / {show('c')}")
    0
}}
'''


DESIGN = {
    # Every return path writes back: a plain return, an early return, `?` propagating, falling off the end.
    'return-paths': '''fn plain(mut a: int, mut xs: List[int]) -> int {
    a += 1
    (mut xs).push(1)
    return a
}
fn early(mut a: int, mut xs: List[int], stop: bool) -> int {
    a += 10
    (mut xs).push(2)
    if stop { return a }
    a += 100
    a
}
fn fails(mut a: int, mut xs: List[int], bad: bool) -> int ! {nope} {
    a += 1000
    (mut xs).push(3)
    if bad { return nope }
    a
}
fn prop(mut a: int, mut xs: List[int], bad: bool) -> int ! {nope} {
    a += 5
    let v = fails(mut a, mut xs, bad)?
    v + 1
}
fn tail(mut a: int, mut xs: List[int]) {
    a += 7
    (mut xs).push(4)
}
fn main() -> int {
    var a = 0
    var xs = List[int]()
    let p = plain(mut a, mut xs)
    print("ret-plain {p} {a} {xs}")
    let e = early(mut a, mut xs, true)
    print("ret-early {e} {a} {xs}")
    let f = early(mut a, mut xs, false)
    print("ret-late {f} {a} {xs}")
    let g = prop(mut a, mut xs, true) else -1
    print("ret-propagated {g} {a} {xs}")
    let h = prop(mut a, mut xs, false) else -1
    print("ret-propagated-ok {h} {a} {xs}")
    tail(mut a, mut xs)
    print("ret-fall-through {a} {xs}")
    0
}
''',
    # A `mut` parameter passed on as `mut`: one level, two levels, and twice in sequence.
    'pass-on': '''fn leaf(mut a: int, mut xs: List[int]) {
    a = a * 2
    (mut xs).push(a)
}
fn one(mut a: int, mut xs: List[int]) {
    a += 1
    leaf(mut a, mut xs)
}
fn two(mut a: int, mut xs: List[int]) {
    a += 1
    one(mut a, mut xs)
    a += 1
}
fn twice(mut a: int, mut xs: List[int]) {
    leaf(mut a, mut xs)
    leaf(mut a, mut xs)
}
fn main() -> int {
    var a = 1
    var xs = List[int]()
    one(mut a, mut xs)
    print("pass-one {a} {xs}")
    two(mut a, mut xs)
    print("pass-two {a} {xs}")
    twice(mut a, mut xs)
    print("pass-twice {a} {xs}")
    0
}
''',
    # Several `mut` arguments in one call, and element and field places whose index the callee changes.
    'places': '''struct P { a: int, b: int }
struct R { a: int, v: List[int] }
fn three(mut x: int, mut y: int, mut z: int) {
    x += 1
    y += 10
    z += 100
}
fn bump_at(mut e: int, mut i: int) {
    e += 50
    i += 1
}
fn grow(mut e: int, mut n: int) {
    e = n
    n += 1
}
fn swap(mut a: int, mut b: int) {
    let t = a
    a = b
    b = t
}
fn main() -> int {
    var x = 0
    var y = 0
    var z = 0
    three(mut x, mut y, mut z)
    print("args-three {x} {y} {z}")
    var p = P { a: 1, b: 2 }
    swap(mut p.a, mut p.b)
    print("args-fields {p.a} {p.b}")
    var xs = [10, 20, 30]
    var i = 0
    bump_at(mut xs[i], mut i)
    print("place-index-once {xs} {i}")
    var rs = [P { a: 1, b: 2 }, P { a: 3, b: 4 }]
    var j = 1
    grow(mut rs[j].a, mut j)
    print("place-element-field {rs[0].a} {rs[1].a} {j}")
    var r = R { a: 0, v: [7, 8] }
    swap(mut r.a, mut r.v[1])
    print("place-field-element {r.a} {r.v}")
    0
}
''',
    # `copy` is deep: change the copy's inner list, the original's stays.
    'copy-depth': '''struct H { tag: int, items: List[int] }
fn main() -> int {
    var g = [[1, 2], [3]]
    var c = copy g
    (mut c[0]).push(9)
    print("copy-nested-lists {g} {c}")
    var h = H { tag: 1, items: [5] }
    var d = copy h
    (mut d.items).push(6)
    print("copy-struct-list {h.items} {d.items}")
    var m = Map[str, List[int]]()
    m["k"] = [1]
    var n = copy m
    n["k"] = [2]
    print("copy-map {m["k"] else List[int]()} {n["k"] else List[int]()}")
    var hs = [H { tag: 1, items: [1] }]
    var e = copy hs
    (mut e[0].items).push(2)
    print("copy-list-of-structs {hs[0].items} {e[0].items}")
    0
}
''',
}


def programs():
    """(name, source, ids) for every program, in a fixed order."""
    out = []
    for kind in KINDS:
        source = kind_program(*kind)
        out.append(('kind-' + kind[0], source, ids_of(source)))
    for name, source in DESIGN.items():
        out.append((name, source, ids_of(source)))
    return out


def ids_of(source):
    return re.findall(r'print\("([a-z0-9-]+) ', source)


def generator_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def outcome(observed, ids):
    """One program's comparable observation: its verdict, trap kind and site, and each case's text."""
    printed = {}
    for line in (observed.get('stdout') or '').split('\n'):
        head, _, rest = line.partition(' ')
        if head in ids and head not in printed:
            printed[head] = rest
    site = observed.get('trap_site')
    site = site if isinstance(site, dict) else {}
    return dict(verdict=observed.get('verdict'), trap_kind=observed.get('trap_kind'),
                trap_line=site.get('line'), trap_column=site.get('column'),
                printed={i: printed.get(i) for i in ids})


def capture(args):
    from frame import STAGE, oracle_identity, pins
    from differlib import execute, isolated_context, lupin_observation, observe_native
    host = (platform.system(), platform.machine())
    if host != ('Linux', 'x86_64'):
        raise SystemExit('capture requires Linux x86-64 (not a skip)')
    if not os.environ.get('FENRIR_ORACLE_SANDBOX'):
        raise SystemExit('capture requires an isolated container; set FENRIR_ORACLE_SANDBOX=1 inside it')
    rows, problems = [], []
    (ROOT / 'target').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mode-cases-', dir=ROOT / 'target') as temp:
        for index, (name, source_text, ids) in enumerate(programs()):
            scratch = Path(temp) / str(index)
            source = scratch / 'src' / f'{name}.lu'
            source.parent.mkdir(parents=True)
            source.write_text(source_text)
            env = dict(os.environ, WOLF_STD=str(STAGE / 'std'), WOLF_RT_LIB=str(STAGE / 'libwolf_rt.a'))
            roots = [(scratch, '<scratch>'), (STAGE, '<toolchain>')]
            cwd, nenv = isolated_context(scratch, 'native-run', env)
            native = observe_native(STAGE / 'wolf', source, cwd, nenv, args.timeout, roots, runner=execute,
                                    classification_context=isolated_context(scratch, 'native-classification', env))
            cwd, lenv = isolated_context(scratch, 'lupin', env)
            lupin = lupin_observation(execute([STAGE / 'lupin', 'conform-run', source, '--json'], cwd, lenv, args.timeout),
                                      source, roots)
            n, l = outcome(native, ids), outcome(lupin, ids)
            differing = sorted(i for i in ids if n['printed'][i] != l['printed'][i])
            known = sorted(i for i in ids if i in KNOWN_COMPILER_DIFFERENCES)
            built = n['verdict'] not in (None, 'refused', 'unsupported') and not str(n['verdict']).startswith('fail')
            if name in NATIVE_DEFECTS and built:
                problems.append(f'{name}: named as a native defect, but the compiler builds it')
            if name not in NATIVE_DEFECTS and not built:
                problems.append(f'{name}: the native compiler gives {n["verdict"]} and no defect names it')
            for i in known:
                if i not in differing:
                    problems.append(f'{i}: a known compiler difference no longer differs')
            for i in differing:
                if i not in known and name not in NATIVE_DEFECTS:
                    problems.append(f'{i}: native {n["printed"][i]!r}, lupin {l["printed"][i]!r}, and no entry names it')
            if any(v is None for v in (l if name in NATIVE_DEFECTS else n)['printed'].values()):
                problems.append(f'{name}: a case printed nothing')
            ok = not [p for p in problems if p.startswith((name + ':',) + tuple(i + ':' for i in ids))]
            print(f'{"PASS" if ok else "FAIL"} mode-capture-{name} native {n["verdict"]} lupin {l["verdict"]}', flush=True)
            rows.append(dict(program=name, ids=ids, source_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
                             native=n, lupin=l, native_stderr=native.get('stderr'), differing=differing))
    table = dict(format=1, generator_sha256=generator_digest(), identity=oracle_identity(pins()),
                 host='-'.join(host).lower(), known_compiler_differences=KNOWN_COMPILER_DIFFERENCES,
                 native_defects=NATIVE_DEFECTS, programs=rows, problems=problems)
    Path(args.out).write_text(json.dumps(table, indent=1, sort_keys=True) + '\n')
    for p in problems:
        print('FAIL mode-capture ' + p, flush=True)
    print(f'{"PASS" if not problems else "FAIL"} mode-capture {len(rows)} programs, '
          f'{sum(len(r["ids"]) for r in rows)} cases; {len(KNOWN_COMPILER_DIFFERENCES)} known compiler differences, '
          f'{len(NATIVE_DEFECTS)} native defects', flush=True)
    return int(bool(problems))


def expected(row, cid):
    """The answer a case is held to: lupin's for a listed difference or defect, else the native one."""
    source = 'lupin' if cid in KNOWN_COMPILER_DIFFERENCES or row['program'] in NATIVE_DEFECTS else 'native'
    return row[source]['printed'][cid]


def table_check(args):
    if not Path(args.table).is_file():
        print(f'FAIL mode-cases-table no committed answers: {args.table}', flush=True)
        return 1
    table = json.loads(Path(args.table).read_text())
    progs = {name: (source, ids) for name, source, ids in programs()}
    have = {r['program']: r for r in table['programs']}
    problems = list(table.get('problems', []))
    if sorted(have) != sorted(progs):
        problems.append('the table names other programs than the generator: ' + ', '.join(sorted(set(have) ^ set(progs))))
    for name, (source, ids) in progs.items():
        row = have.get(name)
        if row and row['source_sha256'] != hashlib.sha256(source.encode()).hexdigest():
            problems.append(f'{name}: the program changed since the capture')
    if table.get('known_compiler_differences') != KNOWN_COMPILER_DIFFERENCES or table.get('native_defects') != NATIVE_DEFECTS:
        problems.append('the listed differences or defects changed since the capture')
    for p in problems:
        print('FAIL mode-cases-table ' + p, flush=True)
    cases = sum(len(ids) for _, ids in progs.values())
    print(f'{"PASS" if not problems else "FAIL"} mode-cases-table {len(progs)} programs, {cases} cases; '
          f'{len(KNOWN_COMPILER_DIFFERENCES)} known compiler differences, {len(NATIVE_DEFECTS)} native defects', flush=True)
    return int(bool(problems))


def plain(args, cwd, env, timeout, address_space=None):
    """A child run off Linux, which has no prlimit: the timeout is its only bound."""
    import subprocess
    try:
        p = subprocess.run([str(a) for a in args], cwd=cwd, env=env, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr, False
    except subprocess.TimeoutExpired as e:
        return None, e.stdout or b'', e.stderr or b'', True


def output_root(out):
    """The folder every program's own folder sits in. Each child runs in its program's folder."""
    return Path(out)


def places(out, name):
    """A program's folder and its source, as handed to a child that runs in that folder."""
    work = out / name
    return work, work / f'{name}.lu'


def paths_self_test():
    """A relative --out (as the Linux gate passes it) must still name every file absolutely."""
    bad = []
    for name, _, _ in programs():
        work, source = places(output_root('target/backend-linux/mode-cases'), name)
        bad += [(name, p) for p in (work, source, work / 'program', work / 'program.fir') if not p.is_absolute()]
    for name, p in bad:
        print(f'FAIL mode-cases-paths {name} names {p} from the caller\'s folder, not the child\'s', flush=True)
    if not bad:
        print(f'PASS mode-cases-paths {len(programs())} programs name their files absolutely', flush=True)
    return 1 if bad else 0


def check(args):
    from frame import STAGE
    from differlib import execute, interpreted_observation, native_observation
    execute = execute if platform.system() == 'Linux' else plain
    if args.engine == 'native' and platform.system() != 'Linux':
        raise SystemExit('the native engine requires Linux x86-64 (not a skip)')
    if not Path(args.table).is_file():
        print(f'FAIL mode-cases-{args.engine} no committed answers: {args.table}', flush=True)
        return 1
    table = {r['program']: r for r in json.loads(Path(args.table).read_text())['programs']}
    out = output_root(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failed = total = 0
    fenrir = str(Path(args.compiler).resolve())
    for name, source_text, ids in programs():
        work, source = places(out, name)
        work.mkdir(exist_ok=True)
        source.write_text(source_text)
        env = dict(os.environ, WOLF_STD=str(STAGE / 'std'))
        roots = [(work, '<scratch>'), (STAGE, '<toolchain>')]
        if args.engine == 'native':
            built = execute([fenrir, 'build', source, '-o', work / 'program'], work, env, args.timeout)
            observed = native_observation(execute([work / 'program'], work, env, args.timeout), source, roots) \
                if built[0] == 0 else dict(verdict='refused', stdout='', stderr=built[2].decode(errors='replace'))
        else:
            built = execute([fenrir, '--emit=fir', source], work, env, args.timeout)
            if built[0] == 0:
                (work / 'program.fir').write_bytes(built[1])
                report = work / 'outcome.txt'
                result = execute([fenrir, 'interpret', work / 'program.fir', '--steps', '20000000', '--bytes', '67108864',
                                  '--report', report], work, env, args.timeout)
                observed = interpreted_observation(result, report.read_text() if report.is_file() else None, source, roots)
            else:
                observed = dict(verdict='refused', stdout='', stderr=built[2].decode(errors='replace'))
        got = outcome(observed, ids)
        refusal = re.search(r'error\[([A-Z]\d{4})\]', observed.get('stderr') or '')
        for cid in ids:
            total += 1
            want = expected(table[name], cid)
            if got['verdict'] == 'refused':
                failed += 1
                print(f'FAIL mode-case-{args.engine} {cid} refused {refusal.group(1) if refusal else "?"}', flush=True)
            elif got['printed'][cid] != want:
                failed += 1
                print(f'FAIL mode-case-{args.engine} {cid} expected {want!r} observed {got["printed"][cid]!r}', flush=True)
    print(f'{"PASS" if not failed else "FAIL"} mode-cases-{args.engine} {total - failed}/{total} cases equal the reference', flush=True)
    return int(bool(failed))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='mode', required=True)
    t = sub.add_parser('table')
    t.add_argument('--table', type=Path, default=TABLE)
    c = sub.add_parser('capture')
    c.add_argument('--out', type=Path, required=True)
    c.add_argument('--timeout', type=int, default=120)
    k = sub.add_parser('check')
    k.add_argument('--compiler', type=Path, required=True)
    k.add_argument('--engine', choices=('native', 'interpreter'), required=True)
    k.add_argument('--out', type=Path, required=True)
    k.add_argument('--table', type=Path, default=TABLE)
    k.add_argument('--timeout', type=int, default=120)
    sub.add_parser('paths')
    w = sub.add_parser('write-programs')
    w.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.mode == 'write-programs':
        a.out.mkdir(parents=True, exist_ok=True)
        for name, source, ids in programs():
            (a.out / name).mkdir(exist_ok=True)   # one package per program: a directory holds one module
            (a.out / name / 'main.lu').write_text(source)
        print(f'{len(programs())} programs, {sum(len(p[2]) for p in programs())} cases', flush=True)
        return 0
    if a.mode == 'paths':
        return paths_self_test()
    return {'table': table_check, 'capture': capture, 'check': check}[a.mode](a)


if __name__ == '__main__':
    sys.exit(main())
