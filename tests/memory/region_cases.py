#!/usr/bin/env python3
"""Regions: what a program sees of its regions, answered by the released reference.

Each program here prints one line per case, `ID text`, and every case prints a relation or a value,
never a raw ledger number: `region_bytes` and `live_region_bytes` count in each engine's own units
(`[mem.region.account.1]`, docs/MEMORY.md), so only what the clauses guarantee on every tier is
compared (zero at creation, growth, stability, attribution to the birth region, reclamation, the cap).
Each program's outcome (its exit or trap kind) is a case too, `PROGRAM-outcome`.

The answers are never computed here: `capture` runs the pinned wolf (native tier) and lupin on each
program and records what they print, trap or refuse; `check` builds the same programs with fenrir, on
either engine, and compares case by case with the committed table; `table` requires the committed table
to name exactly these programs, by digest. As in tests/memory/mode_cases.py, a case where the
specification settles the meaning against the native compiler is a listed `KNOWN_COMPILER_DIFFERENCES`
entry answered by lupin, and a program the released Linux compiler cannot build is a listed
`NATIVE_DEFECTS` entry answered by lupin; the capture fails on any other disagreement.

The programs cover both creation forms, `in r`, nesting and re-entry (`[mem.region.open.1]`), every
way out of a sugar block (a `return`, a `break`, `?` propagating, an error return, falling through:
`[mem.region.intra.2]`), the ledger's relations (`[mem.region.account.1]`, `.2`), attribution to the
birth region (`[mem.region.create.3]`), the cap at, under and past its budget and its single evaluation
(`[mem.region.cap.1]`, `.2`), a region value passed to a call and returned from one, strings charged
where they are made and copied out to an outer list (`[mem.region.outer-write]`), and `List.reserve` and
`List.reset` in a region (`[type.list.reserve]`, `[type.list.reset]`).

  region_cases.py table [--table PATH]
  region_cases.py capture --out PATH [--only NAME]   (Linux x86-64; FENRIR_ORACLE_SANDBOX=1 in the container;
                                         --only captures one program end to end, never a table to commit)
  region_cases.py check --compiler F --engine native|interpreter --out DIR [--table PATH]
  region_cases.py write-programs --out DIR
  region_cases.py paths                    (any OS: every file a child is given is named from its own folder)

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
TABLE = ROOT / 'tests/memory/region-cases.json'

# Case id -> the issue that settles it against the native compiler; the answer is lupin's.
KNOWN_COMPILER_DIFFERENCES = {}
# Program -> the issue for a program the released Linux compiler cannot build; the answer is lupin's.
NATIVE_DEFECTS = {}

PROGRAMS = {
    # [mem.region.account.1], [mem.region.account.2]: zero at creation, growth, stability, monotone,
    # the live total up while the region holds storage and back at its free.
    'ledger': '''fn main() -> int {
    let base = live_region_bytes()
    var reclaimed = false
    region r {
        let c0 = region_bytes(r)
        let zero = c0 == 0
        print("ledger-zero {zero}")
        var xs = List[int]()
        for i in 0..300 { (mut xs).push(i) }
        let c1 = region_bytes(r)
        let c2 = region_bytes(r)
        let grew = c1 > c0
        let stable = c1 == c2
        print("ledger-grew {grew}")
        print("ledger-stable {stable}")
        for i in 0..300 { (mut xs).push(i) }
        let c3 = region_bytes(r)
        let monotone = c3 >= c1
        print("ledger-monotone {monotone}")
        let up = live_region_bytes() > base
        print("ledger-live-up {up}")
        print("ledger-values {xs.len} {xs[599]}")
    }
    reclaimed = live_region_bytes() == base
    print("ledger-reclaimed {reclaimed}")
    0
}
''',
    # [mem.region.create.1], [mem.region.create.3]: a region value, entered with `in r`; a container
    # charges the region ambient where it was born, so a root-born list growing later moves nothing.
    'value': '''fn main() -> int {
    let r = region()
    let c0 = region_bytes(r)
    var outer = List[int]()
    in r {
        var ys = List[int]()
        for i in 0..200 { (mut ys).push(i) }
        print("value-inner {ys.len} {ys[199]}")
    }
    let c1 = region_bytes(r)
    (mut outer).push(1)
    (mut outer).push(2)
    let c2 = region_bytes(r)
    let zero = c0 == 0
    let charged = c1 > c0
    let birth = c2 == c1
    print("value-zero {zero}")
    print("value-charged {charged}")
    print("value-birth {birth}")
    print("value-outer {outer.len}")
    0
}
''',
    # [mem.region.create.3], [mem.region.open.1]: an inner region takes the allocations made inside
    # it, the outer one is left alone; re-entering an open region is depth-counted, not an error.
    'nesting': '''fn main() -> int {
    region a {
        let a0 = region_bytes(a)
        region b {
            var xs = List[int]()
            for i in 0..100 { (mut xs).push(i) }
            let inner = region_bytes(b) > 0
            let still = region_bytes(a) == a0
            print("nesting-inner-charged {inner}")
            print("nesting-outer-still {still}")
        }
        in a {
            var zs = List[int]()
            for i in 0..100 { (mut zs).push(i) }
            print("nesting-reenter {zs.len} {zs[99]}")
        }
        let grew = region_bytes(a) > a0
        print("nesting-reenter-charged {grew}")
    }
    0
}
''',
    # [mem.region.intra.2]: a sugar block's region is freed on every way out of it.
    'exits': '''fn by_return(n: int) -> int {
    region r {
        var xs = List[int]()
        for i in 0..n { (mut xs).push(i) }
        if n > 0 { return xs.len }
    }
    0
}
fn by_fall(n: int) -> int {
    var total = 0
    region r {
        var xs = List[int]()
        for i in 0..n { (mut xs).push(i) }
        total = xs.len
    }
    total
}
fn by_break(n: int) -> int {
    var total = 0
    for k in 0..3 {
        region r {
            var xs = List[int]()
            for i in 0..n { (mut xs).push(i) }
            total += xs.len
            if k == 1 { break }
        }
    }
    total
}
fn by_error(n: int, bad: bool) -> int ! {nope} {
    region r {
        var xs = List[int]()
        for i in 0..n { (mut xs).push(i) }
        if bad { return nope }
    }
    n
}
fn by_prop(n: int, bad: bool) -> int ! {nope} {
    var held = 0
    region r {
        var xs = List[int]()
        for i in 0..n { (mut xs).push(i) }
        let v = by_error(n, bad)?
        held = v + xs.len
    }
    held
}
fn main() -> int {
    let base = live_region_bytes()
    let a = by_return(50)
    let fa = live_region_bytes() == base
    print("exits-return {a} {fa}")
    let b = by_fall(60)
    let fb = live_region_bytes() == base
    print("exits-fall-through {b} {fb}")
    let c = by_break(70)
    let fc = live_region_bytes() == base
    print("exits-break {c} {fc}")
    let d = by_error(80, true) else -1
    let fd = live_region_bytes() == base
    print("exits-error {d} {fd}")
    let e = by_prop(90, true) else -1
    let fe = live_region_bytes() == base
    print("exits-propagated {e} {fe}")
    let f = by_prop(90, false) else -1
    let ff = live_region_bytes() == base
    print("exits-propagated-ok {f} {ff}")
    0
}
''',
    # [mem.region.cap.1], [mem.region.cap.2]: exactly at the cap is legal, a zero cap is legal for a
    # region that never charges, the queries answer as on an uncapped region, and `cap:` runs once.
    'cap': '''fn budget(mut calls: int, n: int) -> int {
    calls += 1
    n
}
fn main() -> int {
    let probe = region()
    var measured = 0
    in probe {
        var xs = List[int]()
        for i in 0..150 { (mut xs).push(i) }
        measured = region_bytes(probe)
    }
    let positive = measured > 0
    print("cap-measured {positive}")
    let capped = region(cap: measured)
    var at_cap = false
    var held = 0
    in capped {
        var ys = List[int]()
        for i in 0..150 { (mut ys).push(i) }
        at_cap = region_bytes(capped) == measured
        held = ys.len + ys[149]
    }
    print("cap-at-cap-values {held}")
    print("cap-at-cap {at_cap}")
    var zero = false
    region idle(cap: 0) {
        zero = region_bytes(idle) == 0
    }
    print("cap-zero {zero}")
    var calls = 0
    region once(cap: budget(mut calls, 1000000)) {
        var zs = List[int]()
        for i in 0..10 { (mut zs).push(i) }
    }
    print("cap-evaluated-once {calls}")
    0
}
''',
    # [mem.region.cap.1]: the charge that would pass the budget traps `alloc-contract` at its site.
    'cap-breach': '''fn main() -> int {
    let probe = region()
    var measured = 0
    in probe {
        var xs = List[int]()
        for i in 0..200 { (mut xs).push(i) }
        measured = region_bytes(probe)
    }
    let positive = measured > 0
    print("cap-breach-measured {positive}")
    region tight(cap: measured - 1) {
        var ys = List[int]()
        for i in 0..200 { (mut ys).push(i) }
        print("cap-breach-unreached {ys.len}")
    }
    0
}
''',
    # A region value crossing calls: passed in and opened by the callee twice, and made by one call and
    # returned to its caller.
    'pass-return': '''fn fill(r: region, n: int) -> int {
    var total = 0
    in r {
        var xs = List[int]()
        for i in 0..n { (mut xs).push(i) }
        for v in xs { total += v }
    }
    total
}
fn make() -> region {
    let r = region()
    r
}
fn main() -> int {
    let r = region()
    let a = fill(r, 10)
    let b = fill(r, 20)
    let charged = region_bytes(r) > 0
    print("pass-return-fill {a} {b}")
    print("pass-return-charged {charged}")
    let m = make()
    let fresh = region_bytes(m) == 0
    var t = 0
    in m {
        var ys = List[int]()
        (mut ys).push(41)
        t = ys[0] + 1
    }
    let used = region_bytes(m) > 0
    print("pass-return-made {t} {fresh} {used}")
    0
}
''',
    # [mem.region.outer-write]: a string made in a region charges it; `copy` into an outer list makes
    # the copy in the outer list's region, so it is there after the region is gone.
    'strings': '''fn main() -> int {
    let base = live_region_bytes()
    var keep = List[str]()
    region r {
        let c0 = region_bytes(r)
        for i in 0..10 {
            let s = "item-{i}"
            (mut keep).push(copy s)
        }
        let made = "{keep.len}-made"
        let charged = region_bytes(r) > c0
        print("strings-charged {charged} {made}")
    }
    let reclaimed = live_region_bytes() == base
    print("strings-kept {keep.len} {keep[0]} {keep[9]}")
    print("strings-reclaimed {reclaimed}")
    0
}
''',
    # [type.list.reserve], [type.list.reset] in a region: reserve leaves length and elements alone and
    # charges where the list lives; reset empties a list, keeps its buffer and charges nothing.
    'reserve-reset': '''fn main() -> int {
    var xs = List[int]()
    (mut xs).reserve(100)
    let len0 = xs.len
    for i in 0..100 { (mut xs).push(i) }
    print("reserve-reset-reserve {len0} {xs.len} {xs[0]} {xs[99]}")
    var ys = List[int]()
    (mut ys).push(7)
    (mut ys).push(8)
    (mut ys).reserve(1)
    (mut ys).reserve(0)
    print("reserve-reset-noop {ys.len} {ys[0]} {ys[1]}")
    var rising = false
    var flat = false
    region r {
        var zs = List[int]()
        let a = region_bytes(r)
        (mut zs).reserve(64)
        let b = region_bytes(r)
        rising = b >= a
        for i in 0..50 { (mut zs).push(i) }
        let c = region_bytes(r)
        (mut zs).reset()
        let d = region_bytes(r)
        for i in 0..50 { (mut zs).push(i + 1) }
        let e = region_bytes(r)
        flat = d == c && e == c
        print("reserve-reset-reset {zs.len} {zs[0]} {zs[49]}")
    }
    print("reserve-reset-rising {rising}")
    print("reserve-reset-flat {flat}")
    0
}
''',
}


def programs():
    """(name, source, ids) for every program, in a fixed order."""
    return [(name, source, ids_of(source)) for name, source in PROGRAMS.items()]


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
    with tempfile.TemporaryDirectory(prefix='region-cases-', dir=ROOT / 'target') as temp:
        for index, (name, source_text, ids) in enumerate(programs()):
            if args.only and name != args.only:
                continue
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
            if (n['verdict'], n['trap_kind']) != (l['verdict'], l['trap_kind']):
                differing.append(f'{name}-outcome')
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
                    problems.append(f'{i}: native {n["printed"].get(i, n["verdict"])!r}, '
                                    f'lupin {l["printed"].get(i, l["verdict"])!r}, and no entry names it')
            answer = l if name in NATIVE_DEFECTS else n
            silent = [i for i, v in answer['printed'].items() if v is None]
            if answer['verdict'] == 'exit(0)' and silent:
                problems.append(f'{name}: cases printed nothing: {", ".join(silent)}')
            ok = not [p for p in problems if p.startswith((name + ':', name + '-outcome:') + tuple(i + ':' for i in ids))]
            print(f'{"PASS" if ok else "FAIL"} region-capture-{name} native {n["verdict"]} lupin {l["verdict"]}', flush=True)
            rows.append(dict(program=name, ids=ids, source_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
                             native=n, lupin=l, native_stderr=native.get('stderr'), differing=differing))
    if args.only and not rows:
        problems.append(f'--only {args.only}: no such program')
    table = dict(format=1, generator_sha256=generator_digest(), identity=oracle_identity(pins()),
                 host='-'.join(host).lower(), known_compiler_differences=KNOWN_COMPILER_DIFFERENCES,
                 native_defects=NATIVE_DEFECTS, programs=rows, problems=problems, only=args.only)
    Path(args.out).write_text(json.dumps(table, indent=1, sort_keys=True) + '\n')
    for p in problems:
        print('FAIL region-capture ' + p, flush=True)
    print(f'{"PASS" if not problems else "FAIL"} region-capture {len(rows)} programs, '
          f'{sum(len(r["ids"]) + 1 for r in rows)} cases; {len(KNOWN_COMPILER_DIFFERENCES)} known compiler '
          f'differences, {len(NATIVE_DEFECTS)} native defects', flush=True)
    return int(bool(problems))


def answer_of(row, cid):
    """The observation a case is held to: lupin's for a listed difference or defect, else the native one."""
    return row['lupin' if cid in KNOWN_COMPILER_DIFFERENCES or row['program'] in NATIVE_DEFECTS else 'native']


def table_check(args):
    if not Path(args.table).is_file():
        print(f'FAIL region-cases-table no committed answers: {args.table}', flush=True)
        return 1
    table = json.loads(Path(args.table).read_text())
    progs = {name: (source, ids) for name, source, ids in programs()}
    have = {r['program']: r for r in table['programs']}
    problems = list(table.get('problems', []))
    if table.get('only'):
        problems.append(f'the table is a one-program probe (--only {table["only"]}), not a capture')
    if sorted(have) != sorted(progs):
        problems.append('the table names other programs than the generator: ' + ', '.join(sorted(set(have) ^ set(progs))))
    for name, (source, ids) in progs.items():
        row = have.get(name)
        if row and row['source_sha256'] != hashlib.sha256(source.encode()).hexdigest():
            problems.append(f'{name}: the program changed since the capture')
    if table.get('known_compiler_differences') != KNOWN_COMPILER_DIFFERENCES or table.get('native_defects') != NATIVE_DEFECTS:
        problems.append('the listed differences or defects changed since the capture')
    for p in problems:
        print('FAIL region-cases-table ' + p, flush=True)
    cases = sum(len(ids) + 1 for _, ids in progs.values())
    print(f'{"PASS" if not problems else "FAIL"} region-cases-table {len(progs)} programs, {cases} cases; '
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
    return Path(out).resolve()


def places(out, name):
    """A program's folder and its source, as handed to a child that runs in that folder."""
    work = out / name
    return work, work / f'{name}.lu'


def paths_self_test():
    """A relative --out (as the Linux gate passes it) must still name every file absolutely."""
    bad = []
    for name, _, _ in programs():
        work, source = places(output_root('target/backend-linux/region-cases'), name)
        bad += [(name, p) for p in (work, source, work / 'program', work / 'program.fir') if not p.is_absolute()]
    for name, p in bad:
        print(f'FAIL region-cases-paths {name} names {p} from the caller\'s folder, not the child\'s', flush=True)
    if not bad:
        print(f'PASS region-cases-paths {len(programs())} programs name their files absolutely', flush=True)
    return 1 if bad else 0


def check(args):
    from frame import STAGE
    from differlib import execute, interpreted_observation, native_observation
    execute = execute if platform.system() == 'Linux' else plain
    if args.engine == 'native' and platform.system() != 'Linux':
        raise SystemExit('the native engine requires Linux x86-64 (not a skip)')
    if not Path(args.table).is_file():
        print(f'FAIL region-cases-{args.engine} no committed answers: {args.table}', flush=True)
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
        for cid in ids + [f'{name}-outcome']:
            total += 1
            want_row = answer_of(table[name], cid)
            if got['verdict'] == 'refused':
                failed += 1
                print(f'FAIL region-case-{args.engine} {cid} refused {refusal.group(1) if refusal else "?"}', flush=True)
            elif cid == f'{name}-outcome':
                want = (want_row['verdict'], want_row['trap_kind'])
                if (got['verdict'], got['trap_kind']) != want:
                    failed += 1
                    print(f'FAIL region-case-{args.engine} {cid} expected {want!r} observed '
                          f'{(got["verdict"], got["trap_kind"])!r}', flush=True)
            elif got['printed'][cid] != want_row['printed'][cid]:
                failed += 1
                print(f'FAIL region-case-{args.engine} {cid} expected {want_row["printed"][cid]!r} '
                      f'observed {got["printed"][cid]!r}', flush=True)
    print(f'{"PASS" if not failed else "FAIL"} region-cases-{args.engine} {total - failed}/{total} cases equal the reference',
          flush=True)
    return int(bool(failed))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='mode', required=True)
    t = sub.add_parser('table')
    t.add_argument('--table', type=Path, default=TABLE)
    c = sub.add_parser('capture')
    c.add_argument('--out', type=Path, required=True)
    c.add_argument('--timeout', type=int, default=120)
    c.add_argument('--only')
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
        print(f'{len(programs())} programs, {sum(len(p[2]) + 1 for p in programs())} cases', flush=True)
        return 0
    if a.mode == 'paths':
        return paths_self_test()
    return {'table': table_check, 'capture': capture, 'check': check}[a.mode](a)


if __name__ == '__main__':
    sys.exit(main())
