#!/usr/bin/env python3
"""Run only under a Linux memory/CPU cap: `copy` is linear in what it reaches, at N, 10N and 100N.

[mem.tier0.move.3]: `copy x` is deep, so its cost is the storage it reaches. Each program builds a
`List[List[int]]` of N integers in rows of eight, copies it ten times and prints a total that only
the copies' lengths make, so a copy that did not run is a wrong answer, not a fast one. Both
engines run the same FIR: the interpreter (`fenrir interpret`) and the native program
(`fenrir build`). Time is the child's own CPU time (user plus system, from its rusage); every size
runs ROUNDS times, the sizes interleaved round by round, and the minimum stands. A tenfold step may
take at most 18 times the smaller size, whose time counts as at least FLOOR seconds.

  copy_scaling.py COMPILER --out DIR [--base N]
  copy_scaling.py --self-test    (any OS: every file a measured child is given is named from its own directory)
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROUNDS = 5
FLOOR = 0.05
COPIES = 10
ROW = 8

PROGRAM = '''fn build(n: int) -> List[List[int]] {{
    var outer = List[List[int]]()
    var i = 0
    while i < n / {row} {{
        var inner = List[int]()
        var j = 0
        while j < {row} {{
            (mut inner).push(i + j)
            j += 1
        }}
        (mut outer).push(inner)
        i += 1
    }}
    outer
}}

fn main() {{
    let xs = build({n})
    var total = 0
    var k = 0
    while k < {copies} {{
        let ys = copy xs
        total += ys.len + ys[ys.len - 1].len
        k += 1
    }}
    print("{{total}}")
}}
'''


def program(n):
    return PROGRAM.format(n=n, row=ROW, copies=COPIES)


def expected(n):
    return f'{COPIES * (n // ROW + ROW)}\n'


def measured(argv, out_path, cwd):
    before = time.monotonic()
    with out_path.open('wb') as stdout:
        child = subprocess.Popen(argv, stdout=stdout, stderr=subprocess.PIPE, cwd=cwd)
        while True:
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                code = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - before > 180:
                child.kill()  # this child PID only, never a process group
                os.wait4(child.pid, 0)
                raise AssertionError('scaling child exceeded 180 seconds')
            time.sleep(0.01)
    err = child.stderr.read()
    assert code == 0, (argv[0], code, err[:400])
    return usage.ru_utime + usage.ru_stime, usage.ru_maxrss * 1024


def plan(compiler, out, sizes):
    """Each measured child's argv, by (engine, n). A child runs in its program's own folder, so every file
    named here must be named from there."""
    runs = {}
    for n in sizes:
        # Every `.lu` file in a directory joins its module: one directory per program.
        folder = out / f'copy-n{n}'
        runs['interpreter', n] = [compiler, 'interpret', str(folder / 'main.fir'), '--steps', '4000000000',
                                  '--bytes', str(1 << 30), '--report', str(folder / 'outcome.txt')]
        runs['native', n] = [str(folder / 'program')]
    return runs


def self_test():
    """A relative --out (as run-linux passes it) must still name each file from the child's folder."""
    runs = plan('fenrir', Path('target/copy-scaling'), (1, 10))
    bad = [(key, arg) for key, argv in runs.items() for arg in argv[1:] + argv[:1]
           if arg.endswith(('.fir', '.txt', 'program')) and not Path(arg).is_absolute()]
    for key, arg in bad:
        print(f'FAIL copy-scaling-self-test {key[0]} n={key[1]} names {arg} from the caller\'s directory, not the child\'s', flush=True)
    if not bad:
        print(f'PASS copy-scaling-self-test {len(runs)} children name their files absolutely', flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('compiler', type=Path, nargs='?')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--base', type=int, default=4000)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    assert a.compiler and a.out, 'COMPILER and --out are required'
    assert os.uname().sysname == 'Linux', 'scaling requires a capped Linux job'
    compiler = str(a.compiler.resolve())
    a.out.mkdir(parents=True, exist_ok=True)
    sizes = (a.base, 10 * a.base, 100 * a.base)
    runs = plan(compiler, a.out, sizes)
    for n in sizes:
        folder = a.out / f'copy-n{n}'
        folder.mkdir(exist_ok=True)
        (folder / 'main.lu').write_text(program(n))
        fir = subprocess.run([compiler, '--emit=fir', 'main.lu'], cwd=folder, capture_output=True, timeout=180)
        assert fir.returncode == 0, ('fir', n, fir.stderr[:400])
        (folder / 'main.fir').write_bytes(fir.stdout)
        built = subprocess.run([compiler, 'build', 'main.lu', '-o', 'program'], cwd=folder, capture_output=True, timeout=600)
        assert built.returncode == 0, ('build', n, built.stderr[:400])
    seconds, peaks = {}, {}
    for _ in range(ROUNDS):
        for engine in ('interpreter', 'native'):
            for n in sizes:
                folder = a.out / f'copy-n{n}'
                out = folder / f'{engine}.out'
                cpu, peak = measured(runs[engine, n], out, folder)
                assert out.read_text() == expected(n), ('wrong total', engine, n, out.read_text()[:80])
                seconds.setdefault((engine, n), []).append(cpu)
                peaks.setdefault((engine, n), []).append(peak)
    report = []
    for engine in ('interpreter', 'native'):
        for n in sizes:
            row = {'engine': engine, 'n': n, 'reached': COPIES * n, 'seconds': min(seconds[engine, n]),
                   'seconds_runs': seconds[engine, n], 'child_peak_bytes': max(peaks[engine, n])}
            report.append(row)
            print('SCALING ' + json.dumps(row, sort_keys=True), flush=True)
    for prev, row in zip(report, report[1:]):
        if prev['engine'] != row['engine']:
            continue
        allowed = 18 * max(prev['seconds'], FLOOR)
        assert row['seconds'] <= allowed, ('superlinear-copy', row['engine'], prev['n'], row['n'], prev['seconds'], row['seconds'], allowed)
    (a.out / 'scaling.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS copy-scaling', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
