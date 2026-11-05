#!/usr/bin/env python3
"""Input-size CPU scaling: dependent instructions and distinct function calls.

Linux only. Five interleaved rounds use the direct child's user+system CPU
(rusage), never polling wall time. Each tenfold increase gets 18x the smaller
point or a 0.05-second floor. A one-instruction-short control proves the work
was dispatched. Every child has independent AS, CPU and wall caps.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ROUNDS = 5
FLOOR = 0.05
RATIO = 18
SHAPES = ('instructions', 'functions')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


f = load('scaling_fir', HERE / 'fir.py')
measurement = load('scaling_child', HERE / 'link_budget.py')
fixtures = load('scaling_fixtures', HERE / 'assembly.py')


def program(shape, n):
    if n <= 0 or shape not in SHAPES:
        raise ValueError('positive N and a known shape required')
    body = [f.inst('const', 1, data=(0,))]
    previous = 0
    if shape == 'instructions':
        body.append(f.inst('const', 1, data=(1,)))
        for _ in range(n):
            body.append(f.inst('add', 1, uses=(previous, 1)))
            previous = len(body) - 1
    else:
        for i in range(n):
            body.append(f.inst('call', 1, data=(i + 1,), uses=(previous,)))
            previous = len(body) - 1
    body.append(f.inst('print', uses=(previous,)))
    zero = len(body)
    body += [f.inst('const', 1, data=(0,)), f.inst('return', uses=(zero,))]
    text = f.module(body)
    steps = len(body)
    if shape == 'functions':
        callee = (f.function(1, (1,), [0]) + '\nblock 1 1 3\n' +
                  f.inst('const', 1, data=(1,)) + '\n' +
                  f.inst('add', 1, uses=(0, 1)) + '\n' +
                  f.inst('return', uses=(2,)) + '\n')
        text = text.replace('functions 1\n', f'functions {n + 1}\n').replace('end\n', callee * n + 'end\n')
        steps += 3 * n
    return text, steps


def problems(points):
    failures = []
    if {p['shape'] for p in points} != set(SHAPES):
        failures.append('missing or unknown shape')
    for shape in SHAPES:
        group = sorted((p for p in points if p['shape'] == shape), key=lambda p: p['n'])
        if len(group) != 3 or group[0]['n'] <= 0 or [p['n'] for p in group] != [group[0]['n'] * k for k in (1, 10, 100)]:
            failures.append(f'{shape}: incomplete N/10N/100N points')
            continue
        valid = all(len(p['cpu_samples']) == ROUNDS and
                    all(math.isfinite(v) and v >= 0 for v in p['cpu_samples']) for p in group)
        if not valid:
            failures.append(f'{shape}: invalid or incomplete CPU samples')
            continue
        for previous, current in zip(group, group[1:]):
            before, after = min(previous['cpu_samples']), min(current['cpu_samples'])
            allowed = RATIO * max(before, FLOOR)
            if after > allowed:
                failures.append(f'{shape}: superlinear CPU N={previous["n"]}->{current["n"]} '
                                f'cpu={before:.6f}->{after:.6f} allowed={allowed:.6f}')
    return failures


def execute(binary, point, round_number, steps):
    folder = Path(point['directory'])
    prefix = folder / f'round-{round_number}'
    outcome = prefix.with_suffix('.outcome')
    argv = [str(binary), 'interpret', str(folder / 'program.fir'), '--steps', str(steps),
            '--bytes', str(128 << 20), '--report', str(outcome)]
    result = measurement.measured(argv, dict(os.environ), prefix, limit=2 << 30, timeout=90, cpu=30)
    stdout = prefix.with_suffix('.stdout').read_bytes()
    stderr = prefix.with_suffix('.stderr').read_bytes()
    report = outcome.read_text() if outcome.is_file() else None
    return result, stdout, stderr, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--base', type=int, default=1000)
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('Linux hard caps and rusage required; not a skip')
    if args.base <= 0:
        parser.error('--base must be positive')
    binary = args.binary.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    take = Path(tempfile.mkdtemp(prefix='take-', dir=args.out.resolve()))
    sources = list((ROOT / 'src').rglob('*.lu')) + list((ROOT / '.wolf-bin/reference/corpus').rglob('*.lu'))
    largest = max([p.stat().st_size for p in sources] + [len(text.encode()) for _, text, _ in fixtures.fixtures()])
    points = []
    for shape in SHAPES:
        for n in (args.base, args.base * 10, args.base * 100):
            folder = take / f'{shape}-{n}'
            folder.mkdir()
            text, steps = program(shape, n)
            (folder / 'program.fir').write_text(text)
            points.append(dict(shape=shape, n=n, input_bytes=len(text.encode()), steps=steps,
                               directory=str(folder), cpu_samples=[], child_peak_bytes=[]))
    report = dict(compiler_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), floor=FLOOR,
                  ratio=RATIO, rounds=ROUNDS, largest_real_bytes=largest, points=points, failures=[])
    try:
        for shape in SHAPES:
            largest_point = next(p for p in points if p['shape'] == shape and p['n'] == args.base * 100)
            if largest_point['input_bytes'] < 10 * largest:
                raise ValueError(f'{shape}: 100N is below ten times the largest real input')
        for round_number in range(ROUNDS):
            # Rotate the order, retaining one sample at every size in each round.
            order = points[round_number % len(points):] + points[:round_number % len(points)]
            for point in order:
                result, out, err, outcome = execute(binary, point, round_number, point['steps'])
                if result['timeout'] or result['exit'] != 0 or out != f'{point["n"]}\n'.encode() or err or outcome != 'exit 0\n':
                    raise ValueError(f'{point["shape"]} N={point["n"]}: execution failed: {result}, outcome={outcome!r}, stderr={err[:200]!r}')
                point['cpu_samples'].append(result['child_cpu_seconds'])
                point['child_peak_bytes'].append(result['child_peak_rss_bytes'])
                print(f'SAMPLE {point["shape"]} N={point["n"]} round={round_number} cpu={result["child_cpu_seconds"]:.6f}', flush=True)
        report['failures'] = problems(points)
        if not report['failures']:
            for point in points:
                if point['n'] != args.base * 100:
                    continue
                result, out, err, outcome = execute(binary, point, 'short', point['steps'] - 1)
                if (result['timeout'] or result['exit'] != 4 or out != f'{point["n"]}\n'.encode() or
                        b'FIR_STEP_BUDGET' not in err or outcome != 'refused FIR_STEP_BUDGET\n'):
                    raise ValueError(f'{point["shape"]}: one-instruction-short control did not refuse')
                print('PASS interpreter-scaling-step-control ' + point['shape'], flush=True)
    except (OSError, ValueError) as error:
        report['failures'].append(str(error))
    for point in points:
        if point['cpu_samples']:
            point['minimum_cpu'] = min(point['cpu_samples'])
        print('SCALING ' + json.dumps(point, sort_keys=True), flush=True)
    (take / 'scaling.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    for failure in report['failures']:
        print('FAIL interpreter-scaling ' + failure, flush=True)
    if not report['failures']:
        print('PASS interpreter-scaling', flush=True)
    return int(bool(report['failures']))


if __name__ == '__main__':
    raise SystemExit(main())
