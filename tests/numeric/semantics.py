#!/usr/bin/env python3
"""Independent integer-domain oracle for the shared semantics, not a compiler tier."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
KINDS = [('int', 64, True), ('uint', 64, False), ('i8', 8, True), ('i16', 16, True),
         ('i32', 32, True), ('i64', 64, True), ('u8', 8, False), ('u16', 16, False),
         ('u32', 32, False), ('u64', 64, False)]


def word(value):
    value %= 1 << 64
    return value - (1 << 64) if value >= 1 << 63 else value


def limits(code):
    _, width, signed = KINDS[code % 10]
    return (-(1 << (width - 1)), (1 << (width - 1)) - 1) if signed else (0, (1 << width) - 1)


def normalize(code, value):
    _, width, signed = KINDS[code % 10]
    value %= 1 << width
    if signed and value >= 1 << (width - 1):
        value -= 1 << width
    return value


def expected(mode, code, a, b):
    _, width, signed = KINDS[code % 10]
    low, high = limits(code)
    wrapping = code >= 10
    if mode == 12:
        return normalize(code, ~a), 0
    if mode in (6, 7, 8):
        return (a & b if mode == 6 else a | b if mode == 7 else a ^ b), 0
    if mode in (9, 10):
        if wrapping:
            b %= width
        elif b < 0:
            return 0, 1
        elif b >= width:
            return ((-1 if a < 0 else 0), 0) if mode == 10 else ((0, 0) if a == 0 else (0, 1))
        value = a << b if mode == 9 else a >> b
    elif mode in (4, 5):
        if b == 0:
            return 0, 2
        quotient = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            quotient = -quotient
        value = quotient if mode == 4 else a - quotient * b
        # Plain signed MIN % -1 shares the checked division overflow.
        if not wrapping and a == low and signed and b == -1:
            return 0, 1
    else:
        value = {1: lambda: a + b, 2: lambda: a - b, 3: lambda: a * b, 11: lambda: -a}[mode]()
    if wrapping:
        return normalize(code, value), 0
    return (value, 0) if low <= value <= high else (0, 1)


def cases():
    rows = []
    for code in range(20):
        low, high = limits(code)
        _, width, signed = KINDS[code % 10]
        pairs = {(0, 0), (1, 1), (high, 1), (low, 1), (high, high), (0, high)}
        if signed:
            pairs |= {(low, -1), (-7, 2), (7, -2), (-1, width - 1), (low, 0)}
        for mode in range(1, 13):
            use_pairs = pairs
            if mode in (9, 10):
                use_pairs = {(a, b) for a in (low, high, 0, 1, -1 if signed else 1)
                             for b in (0, 1, width - 1, width, width + 1, high, -1 if signed else 1)}
            for a, b in sorted(use_pairs):
                value, trap = expected(mode, code, a, b)
                rows.append([mode, code, code, word(a), word(b), word(value), trap])
    for source in range(20):
        low, high = limits(source)
        for target in range(20):
            tlo, thi = limits(target)
            for value in sorted({low, high, 0, 1, max(low, min(high, tlo)), max(low, min(high, thi))}):
                out = normalize(target, value) if target >= 10 else value
                trap = int(target < 10 and not tlo <= value <= thi)
                rows.append([0, source, target, word(value), 0, 0 if trap else word(out), trap])
    for value in (-1, 0, 255, 256, 300, 55295, 55296, 57343, 57344, 1114111, 1114112):
        trap = int(value < 0 or value > 1114111 or 55296 <= value <= 57343)
        rows.append([0, 0, 20, value, 0, 0 if trap else value, trap])
        rows.append([0, 0, 21, value, 0, value % 256, 0])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    source = args.out / 'source'
    source.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'src/sem', source / 'sem', dirs_exist_ok=True)
    rows = cases()
    (args.out / 'cases.json').write_text(json.dumps(rows) + '\n')
    data = ',\n'.join('Case { mode: %d, source: %d, target: %d, a: %d, b: %d, value: %d, trap: %d }' % tuple(r) for r in rows)
    program = '''use sem
struct Case { mode: int, source: int, target: int, a: int, b: int, value: int, trap: int }
fn main() -> int {
    let cases = [\n''' + data + '''\n]
    var i = 0
    for c in cases {
        let got = sem.numeric(c.mode, sem.numeric_kind(c.source), sem.numeric_kind(c.target), c.a, c.b)
        if got.value != c.value || got.trap != c.trap {
            print("FAIL numeric-domain-{i} mode={c.mode} source={c.source} target={c.target} a={c.a} b={c.b} expected={c.value}/{c.trap} actual={got.value}/{got.trap}")
            return 1
        }
        i += 1
    }
    print("PASS numeric-domains {i}")
    0
}
'''
    (source / 'main.lu').write_text(program)
    binary = args.out / 'consumer'
    env = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'), WOLF_RT_LIB=str(ROOT / '.wolf-bin/libwolf_rt.a'))
    result = subprocess.run([str(ROOT / '.wolf-bin/wolf'), 'build', '--no-cache', '--deny-warnings',
                             str(source / 'main.lu'), '-o', str(binary)], env=env, capture_output=True, timeout=120)
    if result.returncode:
        print('FAIL numeric-domains-build exit=' + str(result.returncode) + ' ' + result.stderr.decode(errors='replace'), flush=True)
        return 1
    result = subprocess.run([str(binary.resolve())], capture_output=True, timeout=30)
    print(result.stdout.decode(errors='replace'), end='', flush=True)
    if result.returncode or result.stderr or result.stdout != f'PASS numeric-domains {len(rows)}\n'.encode():
        print('FAIL numeric-domains-outcome exit=' + str(result.returncode) + ' stderr=' + repr(result.stderr), flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
