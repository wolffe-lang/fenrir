#!/usr/bin/env python3
"""Run only under a Linux memory/CPU cap: a region's memory class at N, 10N and 100N, natively (MEMORY.md 7).

[mem.region.intra.2]: a region is freed whole at its block's exit, so a loop that opens a region each turn
and allocates inside it holds no more at 100N turns than at 10N: its class is constant. One region that
holds N allocations grows with them: its class is linear. Each program prints a total that only its
allocations make, so a run that skipped them is a wrong answer, not a small one. The control holds the
same turns' allocations in one region instead, so it must read linear: a measurement that reads every
program as constant fails there. The probe program calls a function whose `mut` parameter receives a container
store's copy N times from outside every block, so each call reads its entry ambient through a probe region
(docs/LOWERING.md): a probe left live would grow with the calls.

Both fenrir's native program (`fenrir build`) and the reference's (`wolf build`) run the same source. The
peak is the child's own `ru_maxrss`, read by `wait4` from a small parent, tests/memory/maxrss.c, built here with
`cc`: `ru_maxrss` survives exec, so a child forked from this Python process would report at least Python's resident
set. The floor is an empty program's peak, built by the same compiler, and it must be under FLOOR_MAX: a larger
floor means the parent is not small, and every smaller peak would read as the floor. Every size runs ROUNDS times, the sizes interleaved round by round, and the
largest peak stands. The class comes from the growth above the floor from 10N to 100N: at most twice is
constant, five to twenty times is linear, and anything else is unclassified, which fails. fenrir's class
must be the reference's, and fenrir's 100N peak at most twice the reference's. RSS rows compare classes,
never bytes: the reference links glibc and fenrir musl.

The interpreter is not measured here. Its storage is its own, not the runtime's, and the ledger's relations
on it are tests/memory/region_cases.py's.

  region_scaling.py COMPILER --out DIR [--reference WOLF]
  region_scaling.py --self-test    (any OS: the plan names every child's file absolutely; the classes)
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROUNDS = 3
SLACK = 256 << 10
FLOOR_MAX = 8 << 20
LAUNCHER = Path(__file__).resolve().parent / 'maxrss.c'
TURN_ITEMS = 64
BASES = {'turns': 2000, 'held': 500, 'fill': 4000, 'probe': 20000}
WANT = {'turns': 'constant', 'held': 'linear', 'fill': 'linear', 'probe': 'constant'}

TURNS = '''fn main() {{
    var total = 0
    var i = 0
    while i < {n} {{
        region turn {{
            var xs = List[int]()
            var j = 0
            while j < {items} {{
                (mut xs).push(i + j)
                j += 1
            }}
            let s = "turn {{i}} {{xs.len}}"
            total += xs[{last}] - i + s.len
        }}
        i += 1
    }}
    print("{{total}}")
}}
'''

HELD = '''fn main() {{
    var total = 0
    region all {{
        var i = 0
        while i < {n} {{
            var xs = List[int]()
            var j = 0
            while j < {items} {{
                (mut xs).push(i + j)
                j += 1
            }}
            let s = "turn {{i}} {{xs.len}}"
            total += xs[{last}] - i + s.len
            i += 1
        }}
    }}
    print("{{total}}")
}}
'''

FILL = '''fn main() {{
    region r {{
        var keep = List[List[int]]()
        var i = 0
        while i < {n} {{
            var xs = List[int]()
            (mut xs).push(i)
            (mut keep).push(xs)
            i += 1
        }}
        var total = 0
        var k = 0
        while k < keep.len {{
            total += keep[k][0]
            k += 1
        }}
        print("{{keep.len}} {{total}}")
    }}
}}
'''

PROBE = '''struct Book {{
    lines: List[str],
}}

fn touch(mut b: Book, i: int) -> int {{
    if i < 0 {{
        region t {{
            (mut b.lines).push(copy "never")
        }}
    }}
    i % 7
}}

fn main() {{
    var b = Book {{ lines: List[str]() }}
    var total = 0
    var i = 0
    while i < {n} {{
        total += touch(mut b, i)
        i += 1
    }}
    print("{{total}} {{b.lines.len}}")
}}
'''

EMPTY = 'fn main() {\n}\n'


def program(shape, n):
    if shape in ('turns', 'held'):
        return (TURNS if shape == 'turns' else HELD).format(n=n, items=TURN_ITEMS, last=TURN_ITEMS - 1)
    if shape == 'probe':
        return PROBE.format(n=n)
    return FILL.format(n=n)


def expected(shape, n):
    if shape == 'probe':
        return f'{sum(i % 7 for i in range(n))} 0\n'
    if shape in ('turns', 'held'):
        return f'{sum(TURN_ITEMS - 1 + len(f"turn {i} {TURN_ITEMS}") for i in range(n))}\n'
    return f'{n} {n * (n - 1) // 2}\n'


def klass(floor, peak10, peak100):
    """The memory class from the growth above the floor between 10N and 100N."""
    ratio = max(peak100 - floor, 0) / max(peak10 - floor, SLACK)
    if ratio <= 2:
        return 'constant', ratio
    if 5 <= ratio <= 20:
        return 'linear', ratio
    return 'unclassified', ratio


def measured(launcher, argv, out_path, cwd):
    """The child's own peak in bytes: `launcher` (maxrss.c) runs it and reports its ru_maxrss in KiB."""
    before = time.monotonic()
    report = out_path.with_suffix('.maxrss')
    report.unlink(missing_ok=True)
    with out_path.open('wb') as stdout:
        child = subprocess.Popen([launcher, str(report)] + argv, stdout=stdout, stderr=subprocess.PIPE, cwd=cwd)
        while True:
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                code = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - before > 180:
                child.kill()  # this child PID only, never a process group
                os.wait4(child.pid, 0)
                raise AssertionError('region scaling child exceeded 180 seconds')
            time.sleep(0.01)
    err = child.stderr.read()
    assert code == 0, (argv[0], code, err[:400])
    return int(report.read_text()) * 1024


def small_parent(out):
    """Build tests/memory/maxrss.c into OUT, as every measurement here runs, and return its path."""
    launcher = Path(out).resolve() / 'maxrss'
    built = subprocess.run(['cc', '-O2', '-o', str(launcher), str(LAUNCHER)], capture_output=True, timeout=120)
    assert built.returncode == 0, ('cc maxrss.c', built.stderr[:400])
    return str(launcher)


def plan(out):
    """Each program's folder and each built child's path, by (shape, n) and compiler. A child runs in its
    folder, so every file named here is named absolutely."""
    out = Path(out).resolve()
    folders = {('empty', 0): out / 'empty'}
    for shape, base in BASES.items():
        for n in (base, 10 * base, 100 * base):
            folders[shape, n] = out / f'{shape}-n{n}'
    return {key: {name: folder / name for name in ('fenrir.out', 'reference.out')} | {'folder': folder}
            for key, folder in folders.items()}


def self_test():
    failures = 0
    runs = plan(Path('target/region-scaling'))
    for key, files in runs.items():
        for name, path in files.items():
            if not Path(path).is_absolute():
                print(f'FAIL region-scaling-self-test {key} names {name} from the caller\'s directory', flush=True)
                failures += 1
    mib = 1 << 20
    for floor, p10, p100, want in ((2 * mib, 3 * mib, 3 * mib + 100, 'constant'), (2 * mib, 2 * mib, 2 * mib, 'constant'),
                                   (2 * mib, 6 * mib, 42 * mib, 'linear'), (2 * mib, 4 * mib, 9 * mib, 'unclassified'),
                                   (2 * mib, 3 * mib, 80 * mib, 'unclassified')):
        got = klass(floor, p10, p100)[0]
        if got != want:
            print(f'FAIL region-scaling-self-test class of {p10}, {p100} over {floor} is {got}, wanted {want}', flush=True)
            failures += 1
    for shape in BASES:
        for n in (1, 3):
            if expected(shape, n) == expected(shape, n + 1):
                print(f'FAIL region-scaling-self-test {shape} prints the same total at {n} and {n + 1}', flush=True)
                failures += 1
    # The small parent builds by the measurement's own path into an --out that does not exist yet (a take's
    # checkout has none), passes its child's output and status through, and reports a peak.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        try:
            launcher, built = small_parent(Path(tmp) / 'fresh' / 'region-scaling'), 0
        except AssertionError as e:
            launcher, built = None, e.args[0]
        run = subprocess.run([launcher, str(Path(tmp) / 'report'), '/bin/sh', '-c', 'echo hi; exit 3'],
                             capture_output=True, timeout=60) if launcher else None
        reported = (Path(tmp) / 'report').read_text().strip() if (Path(tmp) / 'report').is_file() else ''
        if run is None or run.returncode != 3 or run.stdout != b'hi\n' or not reported.isdigit() or int(reported) <= 0:
            print(f'FAIL region-scaling-self-test the small parent into a new --out: built {built!r}, '
                  f'{run.returncode if run else None} {run.stdout if run else None!r}, reported {reported!r}', flush=True)
            failures += 1
    if not failures:
        print(f'PASS region-scaling-self-test {len(runs)} folders named absolutely; five classes; totals differ by n; '
              f'the small parent builds into a new --out, passes status and output through and reports a peak', flush=True)
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('compiler', type=Path, nargs='?')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--reference', type=Path, default=Path(__file__).resolve().parents[2] / '.wolf-bin/wolf')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    assert a.compiler and a.out, 'COMPILER and --out are required'
    assert os.uname().sysname == 'Linux', 'region scaling requires a capped Linux job'
    compilers = {'fenrir': str(a.compiler.resolve()), 'reference': str(a.reference.resolve())}
    runs = plan(a.out)
    launcher = small_parent(a.out)
    for key, files in runs.items():
        files['folder'].mkdir(parents=True, exist_ok=True)
        (files['folder'] / 'main.lu').write_text(EMPTY if key[0] == 'empty' else program(*key))
        for name, compiler in compilers.items():
            built = subprocess.run([compiler, 'build', 'main.lu', '-o', name], cwd=files['folder'],
                                   capture_output=True, timeout=600)
            assert built.returncode == 0, ('build', name, key, built.stderr[:400])
    peaks = {}
    for _ in range(ROUNDS):
        for key, files in runs.items():
            for name in compilers:
                out = files[f'{name}.out']
                peak = measured(launcher, [str(files['folder'] / name)], out, files['folder'])
                if key[0] != 'empty':
                    assert out.read_text() == expected(*key), ('wrong total', name, key, out.read_text()[:80])
                peaks[name, key] = max(peaks.get((name, key), 0), peak)
    report, failures = [], 0
    for name in compilers:
        floor = peaks[name, ('empty', 0)]
        if floor > FLOOR_MAX:
            print(f'FAIL region-scaling-floor {name}\'s empty program peaks at {floor} bytes, over {FLOOR_MAX}: the '
                  f'measuring parent is not small', flush=True)
            failures += 1
        else:
            print(f'PASS region-scaling-floor {name}\'s empty program peaks at {floor} bytes', flush=True)
    for shape, base in BASES.items():
        classes, mine = {}, 0
        for name in compilers:
            floor = peaks[name, ('empty', 0)]
            sizes = [peaks[name, (shape, n)] for n in (base, 10 * base, 100 * base)]
            got, ratio = klass(floor, sizes[1], sizes[2])
            classes[name] = got
            row = dict(shape=shape, compiler=name, n=base, floor_bytes=floor, peak_bytes=sizes, growth_ratio=round(ratio, 3),
                       memory_class=got)
            report.append(row)
            print('REGION-SCALING ' + json.dumps(row, sort_keys=True), flush=True)
        fenrir_100, reference_100 = peaks['fenrir', (shape, 100 * base)], peaks['reference', (shape, 100 * base)]
        for problem in ([f'fenrir is {classes["fenrir"]}, wanted {WANT[shape]}'] if classes['fenrir'] != WANT[shape] else []) + \
                       ([f'the reference is {classes["reference"]}, wanted {WANT[shape]}'] if classes['reference'] != WANT[shape] else []) + \
                       ([f'fenrir\'s 100N peak {fenrir_100} is more than twice the reference\'s {reference_100}']
                        if fenrir_100 > 2 * reference_100 else []):
            print(f'FAIL region-scaling-{shape} {problem}', flush=True)
            mine += 1
        failures += mine
        if not mine:
            print(f'PASS region-scaling-{shape} {WANT[shape]} on both compilers', flush=True)
    (Path(a.out) / 'scaling.json').write_text(json.dumps(report, indent=2) + '\n')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
