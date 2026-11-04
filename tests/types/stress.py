#!/usr/bin/env python3
"""Linux-only, capped: the checker's N/10N/100N scaling rows and its fuzz rows.

Scaling grows two shapes (many items; one long body) to 100N above ten times
the largest real input and fails on superlinear growth in time. Fuzz mutates
the core corpus rows and the typed rows by fixed seeds, and generates random
well-formed core programs; neither may crash the checker (statuses 0, 2, 4)."""
import argparse
import json
import os
from pathlib import Path
import random
import resource
import statistics
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rows as data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CAP = 1024 * 1024 * 1024


def cap():
    resource.setrlimit(resource.RLIMIT_AS, (CAP, CAP))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))


def run(binary, source):
    """Run one child; return its status, wall time and its own peak RSS (KiB)."""
    start = time.perf_counter()
    err_path = source.with_suffix('.err')
    with err_path.open('wb') as err:
        child = subprocess.Popen([str(binary), '--emit=typed', str(source)], stdout=subprocess.DEVNULL,
                                 stderr=err, preexec_fn=cap)
        while True:
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                break
            if time.perf_counter() - start > 25:
                child.kill()
                os.wait4(child.pid, 0)
                raise AssertionError(('checker-timeout', source.name))
            time.sleep(0.001)
    elapsed = time.perf_counter() - start
    code = os.waitstatus_to_exitcode(status)
    text = err_path.read_bytes()
    assert code in (0, 2, 4), ('checker-crash', source.name, code, text[:400])
    if code:
        assert b'error[' in text and str(source).encode() in text, ('unnamed-refusal', source.name, text[:300])
    return code, elapsed, usage.ru_maxrss


def items(n):
    unit = []
    for i in range(n):
        unit.append(f'struct P{i} {{\n    x: int\n    s: str\n}}\n'
                    f'fn f{i}(a: int, b: str) -> int {{\n    var t = a\n    let p = P{i} {{ x: t, s: b + "x" }}\n'
                    f'    if p.x > 3 {{ t += 1 }} else {{ t -= 1 }}\n    while t < 10 {{ t += 1 }}\n    t\n}}\n')
    return ''.join(unit) + 'fn main() -> int {\n    print("{f0(1, "a")}")\n    0\n}\n'


def body(n):
    lines = ['fn main() -> int {\n', '    var t = 0\n']
    for i in range(n):
        lines.append(f'    let v{i} = t + {i % 7}\n    t = v{i} * 1 - 0\n')
    lines.append('    print("{t}")\n    0\n}\n')
    return ''.join(lines)


def scaling(binary, work, largest):
    results = {}
    for name, shape in (('items', items), ('body', body)):
        base = 64
        while len(shape(base * 100)) <= largest * 10:
            base *= 2
        times = []
        for scale in (1, 10, 100):
            source = work / f'scale-{name}-{scale}' / 'row.lu'
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(shape(base * scale))
            samples, peaks = [], []
            for _ in range(3):
                code, elapsed, peak = run(binary, source)
                assert code == 0, ('scaling-refusal', name, scale)
                samples.append(elapsed)
                peaks.append(peak)
            times.append(statistics.median(samples))
            print(f'PASS scaling shape={name} N={base * scale} bytes={source.stat().st_size} median={times[-1]:.4f}s '
                  f'child-peak-rss={max(peaks)}KiB cap={CAP}', flush=True)
        for i in (0, 1):
            assert times[i + 1] <= max(times[i], 0.002) * 16, ('superlinear-scaling', name, times)
        results[name] = dict(base=base, seconds=times)
    return results


MUTATIONS = ('drop-line', 'duplicate-line', 'swap-lines', 'literal-kind', 'rename', 'drop-char', 'unbalance')


def mutate(text, rng):
    lines = text.split('\n')
    kind = rng.choice(MUTATIONS)
    i = rng.randrange(len(lines))
    if kind == 'drop-line':
        del lines[i]
    elif kind == 'duplicate-line':
        lines.insert(i, lines[i])
    elif kind == 'swap-lines':
        j = rng.randrange(len(lines))
        lines[i], lines[j] = lines[j], lines[i]
    elif kind == 'literal-kind':
        lines[i] = lines[i].replace('0', rng.choice(['true', '"s"', '9223372036854775808', '-1', 'x']), 1)
    elif kind == 'rename':
        lines[i] = lines[i].replace('let ', 'var ', 1).replace('x', 'zz', 1)
    elif kind == 'drop-char' and lines[i]:
        k = rng.randrange(len(lines[i]))
        lines[i] = lines[i][:k] + lines[i][k + 1:]
    else:
        lines[i] = lines[i] + rng.choice(['(', '}', '{', ' +', ' else'])
    return '\n'.join(lines), kind


TYPES = ['int', 'i32', 'u8', 'u64', 'bool', 'str']


def expression(rng, depth, scope):
    if depth == 0 or rng.random() < 0.3:
        choice = rng.random()
        if scope and choice < 0.5:
            return rng.choice(scope)
        return rng.choice(['0', '1', '255', 'true', 'false', '"w"', '-5', '4294967296'])
    a = expression(rng, depth - 1, scope)
    b = expression(rng, depth - 1, scope)
    form = rng.randrange(6)
    if form == 0:
        return f'({a} {rng.choice(["+", "-", "*", "/", "%"])} {b})'
    if form == 1:
        return f'({a} {rng.choice(["==", "!=", "<", ">="])} {b})'
    if form == 2:
        return f'({a} {rng.choice(["&&", "||"])} {b})'
    if form == 3:
        return f'(if {a} {{ {b} }} else {{ {a} }})'
    if form == 4:
        return f'"{{{a}}}"'
    return f'{rng.choice(["-", "!"])}{a}'


def generated(rng):
    lines = ['fn main() -> int {']
    scope = []
    for i in range(rng.randrange(1, 12)):
        annotation = f': {rng.choice(TYPES)}' if rng.random() < 0.4 else ''
        lines.append(f'    {rng.choice(["let", "var"])} v{i}{annotation} = {expression(rng, 3, scope)}')
        scope.append(f'v{i}')
        if rng.random() < 0.3:
            lines.append(f'    v{rng.randrange(i + 1)} {rng.choice(["=", "+="])} {expression(rng, 2, scope)}')
        if rng.random() < 0.2:
            lines.append(f'    while {expression(rng, 2, scope)} {{ break }}')
    lines.append('    0\n}\n')
    return '\n'.join(lines)


def fuzz(binary, work, census):
    sources = [r['source'] for r in data.ROWS]
    table = json.loads(census.read_text())
    corpus = ROOT / '.wolf-bin/reference'
    sources += [(corpus / r['file']).read_text() for r in table['rows'] if r['cls'] in ('core', 'oracle-refused')]
    statuses = {0: 0, 2: 0, 4: 0}
    for seed in (7, 41, 2026):
        rng = random.Random(seed)
        for index in range(200):
            if index % 4 == 3:
                text, kind = generated(rng), 'generated'
            else:
                text, kind = mutate(rng.choice(sources), rng)
            source = work / f'fuzz-{seed}-{index}' / 'row.lu'
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(text)
            code, _, _ = run(binary, source)
            statuses[code] += 1
        print(f'PASS fuzz seed={seed} rows=200 cap={CAP}', flush=True)
    return statuses


def main():
    p = argparse.ArgumentParser()
    p.add_argument('binary', type=Path)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--census', type=Path, default=ROOT / 'tests/types/census.json')
    a = p.parse_args()
    assert sys.platform.startswith('linux'), 'growing inputs and fuzz require Linux hard caps'
    a.work.mkdir(parents=True, exist_ok=True)
    inputs = list((ROOT / 'src').rglob('*.lu')) + list((ROOT / '.wolf-bin/reference/corpus').rglob('*.lu'))
    largest = max(path.stat().st_size for path in inputs)
    statuses = fuzz(a.binary, a.work, a.census)
    print('PASS fuzz-never-crashes statuses=' + json.dumps(statuses), flush=True)
    results = scaling(a.binary, a.work, largest)
    (a.work / 'measurements.json').write_text(json.dumps(dict(cap=CAP, largest=largest, scaling=results,
                                                              fuzz=statuses), indent=2) + '\n')
    print('PASS typed-linear-scaling', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, subprocess.TimeoutExpired) as exc:
        print('FAIL typed-stress: ' + str(exc), flush=True)
        sys.exit(1)
