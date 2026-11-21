#!/usr/bin/env python3
"""FIR edition 6's float domain: schema rows and a bit-exact two-engine matrix.

The matrix's expected bits come from Python's IEEE binary64 arithmetic (round to nearest,
ties to even), an independent computation, never fenrir's. A NaN result follows the rule
the SDM gives the scalar SSE instructions, written here as data: an invalid operation
yields 0xFFF8000000000000, and a NaN operand comes back quieted, the first operand's
before the second's. Rendering is not checked here; the reference-answered float table
(tests/numeric/float_cases.py) owns it.

  float_fir.py --compiler target/fenrir --out DIR [--native]
"""
import argparse
import math
import os
from pathlib import Path
import resource
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LINK_ADDRESS_SPACE = 2 << 30
DEFAULT_NAN = 0xFFF8000000000000
KINDS = {0: ('int', True, 64), 1: ('uint', False, 64), 2: ('i8', True, 8), 4: ('i32', True, 32),
         5: ('i64', True, 64), 6: ('u8', False, 8), 8: ('u32', False, 32), 9: ('u64', False, 64)}


def bits(v):
    return struct.unpack('<Q', struct.pack('<d', v))[0]


def word(b):
    return b - (1 << 64) if b >= 1 << 63 else b


def carrier(code):
    return {0: 1, 1: 9, 2: 1, 4: 5, 5: 6, 6: 7, 8: 8, 9: 8, 22: 8}[code]


def nan_bits(x):
    return math.isnan(x)


def arith(mode, a, b):
    """Expected result bits of FIR mode 1-4 on doubles a, b (given as bit patterns)."""
    x, y = struct.unpack('<d', struct.pack('<Q', a))[0], struct.unpack('<d', struct.pack('<Q', b))[0]
    if math.isnan(x):
        return a | (1 << 51)
    if math.isnan(y):
        return b | (1 << 51)
    try:
        if mode == 1:
            r = x + y
        elif mode == 2:
            r = x - y
        elif mode == 3:
            r = x * y
        else:
            if y == 0:
                if x == 0:
                    return DEFAULT_NAN
                return bits(math.copysign(math.inf, x) * math.copysign(1, y))
            r = x / y
    except OverflowError:
        return bits(math.copysign(math.inf, x) * (math.copysign(1, y) if mode in (3, 4) else 1))
    return DEFAULT_NAN if math.isnan(r) else bits(r)


VALUES = [0.0, -0.0, 1.0, -1.5, 0.1, 0.2, 3.0, 1e16, 2.0 ** 53, 1e308, -1e308, 5e-324, 2.2250738585072014e-308,
          1.7976931348623157e308, math.inf, -math.inf]
NANS = [DEFAULT_NAN, 0x7FF8000000000001, 0x7FF0000000000001]   # default, quiet with payload, signaling
PAIRS = [(0.1, 0.2), (1e16, 1.0), (2.0 ** 53, 1.0), (2.0 ** 53, 3.0), (-0.0, 0.0), (-0.0, -0.0), (math.inf, -math.inf),
         (1e308, 10.0), (5e-324, 0.5), (1e-300, 1e-300), (1.1, 1.1), (2.2250738585072014e-308, 0.5), (1.0, 3.0),
         (1.0, 0.0), (-1.0, 0.0), (0.0, 0.0), (5e-324, 2.0), (math.inf, 0.0), (math.inf, math.inf), (1.0, -math.inf),
         (1.0000000000000002, 1.0), (3.0, 0.1), (7.5, 2.5), (1.7976931348623157e308, 1e292)]


def cases():
    """(kind, mode, source, target, a, b, expected) in FIR words; kind 'word' or 'bool'."""
    rows = []
    for x, y in PAIRS:
        for mode in (1, 2, 3, 4):
            rows.append(('word', mode, 22, 22, bits(x), bits(y), arith(mode, bits(x), bits(y))))
    for n in NANS:
        rows.append(('word', 1, 22, 22, n, bits(1.0), n | (1 << 51)))
        rows.append(('word', 2, 22, 22, bits(1.0), n, n | (1 << 51)))
        rows.append(('word', 3, 22, 22, n, NANS[1], n | (1 << 51)))
    for v in VALUES + [struct.unpack('<d', struct.pack('<Q', n))[0] for n in NANS[:1]]:
        b = bits(v) if not math.isnan(v) else DEFAULT_NAN
        rows.append(('word', 11, 22, 22, b, 0, b ^ (1 << 63)))
    ordered = [-math.inf, -1.5, -0.0, 0.0, 5e-324, 1.0, math.inf]
    for x in ordered + [math.nan]:
        for y in ordered + [math.nan]:
            for mode, test in ((13, lambda p, q: p == q), (14, lambda p, q: p != q), (15, lambda p, q: p < q),
                               (16, lambda p, q: p <= q), (17, lambda p, q: p > q), (18, lambda p, q: p >= q)):
                a = DEFAULT_NAN if math.isnan(x) else bits(x)
                b = DEFAULT_NAN if math.isnan(y) else bits(y)
                rows.append(('bool', mode, 22, 22, a, b, int(test(x, y))))
    for code, value in [(0, 0), (0, -1), (0, 9007199254740993), (0, 2 ** 63 - 1), (0, -2 ** 63), (5, 123456789012345678),
                        (9, 2 ** 63), (9, 2 ** 64 - 1), (9, 9007199254740993), (1, 2 ** 64 - 1), (4, -2147483648),
                        (6, 255), (8, 4294967295), (2, -128)]:
        rows.append(('word', 0, code, 22, value, 0, bits(float(value))))
    for code, v in [(0, 3.7), (0, -3.7), (0, -0.5), (0, -0.0), (0, 9.223372036854775e18), (0, -9.223372036854775808e18),
                    (9, 1e19), (9, 1.844674407370955e19), (9, -0.9), (9, 9.223372036854775808e18), (1, 1e19),
                    (4, 2147483647.9), (4, -2147483648.9), (6, 255.9), (6, -0.99), (8, 4294967295.5), (2, -128.9)]:
        rows.append(('word', 0, 22, code, bits(v), 0, int(v)))
    return rows


def program(rows):
    blocks = []
    for index, (kind, mode, source, target, a, b, expected) in enumerate(rows):
        code = [f'const {carrier(source)} 0 1 {word(a) if source == 22 else value_word(source, a)} 0']
        uses = [0]
        if mode not in (0, 11):
            code.append(f'const 8 0 1 {word(b)} 0')
            uses.append(1)
        result = len(code)
        rtype = 2 if kind == 'bool' else carrier(target)
        code.append(f'numeric {rtype} 0 3 {mode} {source} {target} {len(uses)} ' + ' '.join(map(str, uses)))
        want = len(code)
        if kind == 'bool':
            code.append(f'const 2 0 1 {expected} 0')
        else:
            code.append(f'const {rtype} 0 1 {word(expected) if target == 22 else value_word(target, expected)} 0')
        condition = len(code)
        code.append(f'eq 2 0 0 2 {result} {want}')
        code.append(f'branch 0 0 3 {2 * index + 2} {2 * index + 1} 0 1 {condition}')
        blocks.append('block 0 ' + str(len(code)) + '\n' + '\n'.join(code))
        blocks.append('block 0 1\ntrap 0 0 1 4 0')
    blocks.append('block 0 2\nconst 1 0 1 0 0\nreturn 0 0 0 1 0')
    return ('fir 6\nblobs 1\nblob ' + b'float-matrix.lu'.hex() + '\nsites 1\nsite 0 1 1\nshapes 0\nfunctions 1\nfunction 1 0 0 '
            + str(len(blocks)) + '\n' + '\n'.join(blocks) + '\nend\n')


def value_word(code, value):
    """An integer domain's canonical word: signed words as themselves, 64-bit unsigned as bits."""
    return word(value % (1 << 64)) if not KINDS[code][1] and KINDS[code][2] == 64 else value


def cap():
    resource.setrlimit(resource.RLIMIT_AS, (LINK_ADDRESS_SPACE, LINK_ADDRESS_SPACE))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(args):
    return subprocess.run(args, capture_output=True, timeout=120)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--compiler', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--native', action='store_true')
    a = ap.parse_args()
    fenrir = str(a.compiler.resolve())
    a.out.mkdir(parents=True, exist_ok=True)
    rows = cases()
    text = program(rows)
    source = a.out / 'float-matrix.fir'
    source.write_text(text)
    canonical = a.out / 'canonical.fir'
    r = run([fenrir, 'fir', str(source), '-o', str(canonical)])
    ok = r.returncode == 0 and canonical.is_file() and canonical.read_text() == text
    print(('PASS' if ok else 'FAIL') + f' float-fir-roundtrip status={r.returncode} {r.stderr.decode(errors="replace")[:200]}', flush=True)
    status = int(not ok)
    lines = text.splitlines()
    first = next(i for i, line in enumerate(lines) if line.startswith('numeric '))
    f = lines[first].split()
    compare = next(i for i, line in enumerate(lines) if line.startswith('numeric 2 '))
    g = lines[compare].split()
    text_part = ('fir 6\nblobs 1\nblob ' + b'x.lu'.hex() + '\nsites 1\nsite 0 1 1\nshapes 0\nfunctions 1\nfunction 1 0 0 1\n'
                 'block 0 4\nconst 8 0 1 0 0\ntext 3 0 3 4 0 5 1 0\nconst 1 0 1 0 0\nreturn 0 0 0 1 2\nend\n')
    rejects = {
        # In an edition-5 module the float domain, its comparisons and its rendering do not exist.
        'float-domain-in-edition-5': (text.replace('fir 6', 'fir 5', 1), b'FIR_TYPE'),
        'float-rendering-in-edition-5': (text_part.replace('fir 6', 'fir 5', 1), b'FIR_LITERAL'),
        'remainder-on-float': (text.replace(lines[first], ' '.join(f[:4] + ['5'] + f[5:]), 1), b'FIR_TYPE'),
        'comparison-on-integer': (text.replace(lines[compare], ' '.join(g[:4] + [g[4], '0', '0'] + g[7:]), 1), b'FIR_TYPE'),
        'comparison-result-not-bool': (text.replace(lines[compare], ' '.join([g[0], '8'] + g[2:]), 1), b'FIR_TYPE'),
        'float-to-char': (text.replace(lines[first], ' '.join(f[:4] + ['0', '22', '20', '1', f[-2]]), 1), b'FIR_TYPE'),
        'float-to-wrapping': (text.replace(lines[first], ' '.join(f[:4] + ['0', '22', '10', '1', f[-2]]), 1), b'FIR_TYPE'),
        'unknown-domain': (text.replace(lines[first], ' '.join(f[:5] + ['23', '23'] + f[7:]), 1), b'FIR_TYPE'),
        'float-rendering-radix': (text_part.replace('text 3 0 3 4 0 5', 'text 3 0 3 4 844424930131968 5', 1), b'FIR_LITERAL'),
        'edition-7': (text.replace('fir 6', 'fir 7', 1), b'FIR_SYNTAX'),
    }
    good = a.out / 'text-part.fir'
    good.write_text(text_part)
    r = run([fenrir, 'fir', str(good), '-o', str(canonical)])
    ok = r.returncode == 0 and canonical.read_text() == text_part
    print(('PASS' if ok else 'FAIL') + f' float-fir-rendering-part status={r.returncode} {r.stderr.decode(errors="replace")[:200]}', flush=True)
    status |= int(not ok)
    for name, (broken, tag) in rejects.items():
        path = a.out / (name + '.fir')
        path.write_text(broken)
        canonical.write_text('preserve\n')
        r = run([fenrir, 'fir', str(path), '-o', str(canonical)])
        ok = r.returncode == 2 and tag in r.stderr and canonical.read_text() == 'preserve\n'
        print(('PASS' if ok else 'FAIL') + f' float-fir-reject-{name} status={r.returncode} {r.stderr.decode(errors="replace")[:160]}', flush=True)
        status |= int(not ok)
    report = a.out / 'matrix.outcome'
    report.unlink(missing_ok=True)
    r = run([fenrir, 'interpret', str(source), '--steps', '1000000', '--bytes', '16777216', '--report', str(report)])
    outcome = report.read_text() if report.is_file() else None
    ok = (r.returncode, outcome) == (0, 'exit 0\n')
    failed = None
    if not ok and outcome and outcome.startswith('trap assert'):
        failed = 'a case returned a different word'
    print(('PASS' if ok else 'FAIL') + f' float-fir-interpreter cases={len(rows)} status={r.returncode} outcome={outcome!r} {failed or ""}', flush=True)
    status |= int(not ok)
    if a.native:
        binary = a.out / 'float-matrix'
        env = dict(os.environ, FENRIR_TOOLCHAIN=os.environ.get('FENRIR_TOOLCHAIN', str(ROOT / '.wolf-bin')))
        r = subprocess.run([fenrir, 'link', str(source), '-o', str(binary)], capture_output=True, timeout=120, env=env,
                           preexec_fn=cap if sys.platform == 'linux' else None)
        if r.returncode:
            print('FAIL float-fir-native-build ' + repr((r.returncode, r.stderr[:300])), flush=True)
            return 1
        r = subprocess.run([str(binary.resolve())], capture_output=True, timeout=30, preexec_fn=cap if sys.platform == 'linux' else None)
        ok = (r.returncode, r.stdout) == (0, b'')
        print(('PASS' if ok else 'FAIL') + f' float-fir-native cases={len(rows)} status={r.returncode} {r.stderr[:200]!r}', flush=True)
        status |= int(not ok)
    return status


if __name__ == '__main__':
    raise SystemExit(main())
