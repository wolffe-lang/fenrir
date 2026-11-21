#!/usr/bin/env python3
"""Float edge cases answered by the released reference, checked on both of fenrir's engines.

The case list is generated here (rendering under every spec shape, arithmetic at rounding ties,
overflow and underflow, signed zeros and NaNs, the six comparisons, conversions both ways with
their traps, literal conversion). The *answers* are never computed here: `capture` runs the
pinned wolf (native tier) and lupin on the generated programs and records what they print, trap
or refuse; the two must agree. `check` builds the same programs with fenrir and compares, case
by case. `table` recomputes the programs from this generator, requires the committed table to
name exactly them, and cross-checks every default rendering independently: it must read back to
the case's double (Python's IEEE binary64) and no shorter decimal may. A failed cross-check is a
question about the reference, never a reason to edit an answer.

  float_cases.py table [--table PATH]
  float_cases.py capture --out PATH                      (Linux x86-64, FENRIR_ORACLE_SANDBOX=1)
  float_cases.py check --compiler F --engine native|interpreter --out DIR [--table PATH]

Cost: linear in the cases; each program is built and run once per engine.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
TABLE = ROOT / 'tests/numeric/float-cases.json'
CHUNK = 60


def bits(v):
    return struct.unpack('<Q', struct.pack('<d', v))[0]


def from_bits(b):
    return struct.unpack('<d', struct.pack('<Q', b))[0]


NEG_NAN = from_bits(0xFFF8000000000000)   # x86's default NaN, what 0/0 gives there
POS_NAN = from_bits(0x7FF8000000000000)


def expr(v):
    """A wolf f64 expression with exactly v's value (specials from the bindings `one` and `zero`)."""
    if math.isnan(v):
        return 'zero / zero' if bits(v) >> 63 else '-(zero / zero)'
    if math.isinf(v):
        return 'one / zero' if v > 0 else '-one / zero'
    if v == 0:
        return '-zero' if bits(v) >> 63 else 'zero'
    text = repr(abs(v)).replace('e+', 'e')
    return ('-' if v < 0 else '') + text


RENDER = [0.0, -0.0, 1.0, -1.0, 0.1, 0.2, 0.3, 0.1 + 0.2, 1 / 3, 2 / 3, 0.5, 1.5, 2.5, -0.5, 3.14159, 2.675,
          4.35, 0.15, 100.0, 123456789.125, 1.2345678901234567, 1e5, 1e6, 1e15, 1e16, 1e17, 1e18, 1e20, 1e21,
          1e22, 1e23, 9.999999999999999e22, 0.001, 1e-4, 1e-5, 1.5e-5, 5e-5, 1e-6, 1e-7, -1e-7, 1.23e-18,
          5e-324, 1e-323, 2.2250738585072009e-308, 2.2250738585072014e-308, 1.7976931348623157e308, -1e300,
          9.87654321e100, float(2 ** 53), float(2 ** 53 + 2), float(2 ** 63), float(2 ** 64),
          math.inf, -math.inf, NEG_NAN, POS_NAN]
FIXED = [('.0f', [0.5, 1.5, 2.5, 3.5, -0.5, -1.5, 0.49999999999999994, 1e22, 1e23, -0.0]),
         ('.1f', [0.05, 0.15, 0.25, 0.35, 0.95, -0.05]),
         ('.2f', [0.125, 0.375, 2.675, 1.005, -0.001, 99.995, 5e-324]),
         ('.3f', [1.0005, 2.0625, 1e-4]),
         ('.20f', [0.1, 1 / 3]), ('.25f', [1e-20]), ('.5', [1 / 3, 2.5, -2.5]), ('.0', [2.5, 0.5]),
         ('f', [0.1, 1e20, 5e-7]), ('.2f', [math.inf, -math.inf, NEG_NAN])]
EXP = [('e', [0.0, -0.0, 1.0, 0.1, 123456.0, 1e-300, 5e-324, 1.7976931348623157e308, math.inf, NEG_NAN]),
       ('.0e', [2.5, 3.5, 1.5e10, 9.5]), ('.2e', [1.125, 1.135, 9.995, 0.0]), ('.3E', [1234.5, 1e-10]),
       ('.15e', [1 / 3]), ('E', [6.02214076e23])]
SHAPE = [('>10', [1.5, -1.5, math.inf]), ('<10', [1.5, NEG_NAN]), ('^10', [1.5]), ('^11', [-1.5]),
         ('*>10', [3.25]), ('_<12.3', [3.14159]), ('+', [0.0, -0.0, 1.5, math.inf, NEG_NAN, POS_NAN]),
         ('+.1f', [-0.0, 0.04, -0.04]), ('010.2f', [-1.5, 3.14159]), ('+010.2f', [1.5]),
         ('08', [math.inf, -math.inf, NEG_NAN, 1.5]), ('+e', [1.5]), ('012.3e', [-1.5]), ('>3', [123456.0]),
         ('^9.1', [-0.0]), ('08.2f', [-1.5])]
ARITH = [('+', 0.1, 0.2), ('+', 1e16, 1.0), ('+', float(2 ** 53), 1.0), ('+', float(2 ** 53), 3.0),
         ('+', -0.0, 0.0), ('+', -0.0, -0.0), ('+', math.inf, -math.inf), ('+', 1.7976931348623157e308, 1e292),
         ('-', 1.0, 1e-16), ('-', 1.0000000000000002, 1.0), ('-', -0.0, 0.0), ('-', 0.0, 0.0), ('-', 0.0, 1.5),
         ('-', math.inf, math.inf), ('*', 3.0, 0.1), ('*', 1e308, 10.0), ('*', -1e308, 10.0), ('*', 0.0, -1.0),
         ('*', math.inf, 0.0), ('*', 5e-324, 0.5), ('*', 1e-300, 1e-300), ('*', 1.1, 1.1),
         ('*', 2.2250738585072014e-308, 0.5), ('/', 1.0, 3.0), ('/', 1.0, 0.0), ('/', -1.0, 0.0),
         ('/', 0.0, 0.0), ('/', 5e-324, 2.0), ('/', 7.5, 2.5), ('/', 1.0, -math.inf), ('/', 2.0, 3.0),
         ('/', 1e300, 1e-300), ('/', math.inf, math.inf)]
NEGATE = [0.0, -0.0, 1.5, math.inf, NEG_NAN, POS_NAN, 5e-324]
COMPARE_PAIRS = [(NEG_NAN, NEG_NAN), (NEG_NAN, 1.0), (1.0, NEG_NAN), (-0.0, 0.0), (math.inf, math.inf),
                 (-math.inf, math.inf), (5e-324, 0.0), (1.0, 2.0), (2.0, 1.0), (1.0, 1.0)]
OPS = ['==', '!=', '<', '<=', '>', '>=']
TO_FLOAT = [('i64', '0'), ('i64', '1'), ('i64', '-1'), ('i64', '9007199254740993'), ('i64', '9223372036854775807'),
            ('i64', '-9223372036854775807 - 1'), ('i64', '123456789012345678'), ('int', '-9007199254740995'),
            ('u64', '9223372036854775808'), ('u64', '18446744073709551615'), ('u64', '9007199254740993'),
            ('u64', '18446744073709550592'), ('u64', '18446744073709550593'), ('uint', '18446744073709551615'),
            ('i32', '-2147483648'), ('i32', '2147483647'), ('u8', '255'), ('i8', '-128'), ('i16', '-32768'),
            ('u16', '65535'), ('u32', '4294967295')]
TO_INT = [('int', 3.7), ('int', -3.7), ('int', -0.5), ('int', -0.0), ('int', 0.9999999999999999),
          ('int', 9.223372036854775e18), ('int', -9.223372036854775808e18), ('i64', 1e18), ('u64', 1e19),
          ('u64', 1.844674407370955e19), ('u64', -0.9), ('uint', 1e19), ('i32', 2147483647.9),
          ('i32', -2147483648.9), ('u8', 255.9), ('u8', -0.99), ('i8', -128.9), ('i16', 32767.5),
          ('u16', 65535.99), ('u32', 4294967295.5)]
TRAPS = [('int', NEG_NAN), ('int', math.inf), ('int', -math.inf), ('int', float(2 ** 63)),
         ('int', -9.223372036854777e18), ('int', 1e300), ('u64', -1.0), ('u64', float(2 ** 64)), ('u64', NEG_NAN),
         ('uint', -1.0), ('i32', 2147483648.0), ('i32', -2147483649.0), ('u8', 256.0), ('u8', -1.0),
         ('i8', 128.0), ('u32', 4294967296.0)]
LITERALS = ['0.1', '1e300', '1e-320', '2.2250738585072011e-308', '2.47032822920623272e-324',
            '2.4703282292062328e-324', '7.2057594037927933e16', '9007199254740993.0', '9007199254740995.0',
            '0.1000000000000000055511151231257827021181583404541015625',
            '3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798',
            '1.7976931348623158e308', '123456789012345678901234567890.0', '1_000.5']
ADOPT = ['9007199254740993', '18446744073709551615', '0', '123']
ALONE = ['1e400', '1e-400', '1.7976931348623159e308']


def cases():
    """Every case, in order: dict(id, category, lines, hole, value) or a standalone program."""
    out = []

    def add(category, lines, hole, value=None, standalone=None):
        out.append(dict(id=f'c{len(out):04d}', category=category, lines=lines, hole=hole,
                        value=None if value is None else f'{bits(value):016x}', standalone=standalone))

    for v in RENDER:
        add('render', [f'let aNNNN: f64 = {expr(v)}'], 'aNNNN', v)
    for spec, values in FIXED + EXP + SHAPE:
        for v in values:
            add('spec', [f'let aNNNN: f64 = {expr(v)}'], f'aNNNN:{spec}', v)
    for op, a, b in ARITH:
        add('arith', [f'let aNNNN: f64 = {expr(a)}', f'let bNNNN: f64 = {expr(b)}'], f'aNNNN {op} bNNNN')
    for v in NEGATE:
        add('negate', [f'let aNNNN: f64 = {expr(v)}'], '-aNNNN')
    for a, b in COMPARE_PAIRS:
        for op in OPS:
            add('compare', [f'let aNNNN: f64 = {expr(a)}', f'let bNNNN: f64 = {expr(b)}'], f'aNNNN {op} bNNNN')
    for kind, text in TO_FLOAT:
        add('int-to-float', [f'let nNNNN: {kind} = {text}'], 'nNNNN as f64')
    for kind, v in TO_INT:
        add('float-to-int', [f'let aNNNN: f64 = {expr(v)}'], f'aNNNN as {kind}', v)
    for kind, v in TRAPS:
        add('trap', [f'let aNNNN: f64 = {expr(v)}'], None, v, standalone=f'aNNNN as {kind}')
    # A literal the reference might refuse would sink a whole chunk, so each is its own program.
    for category, texts in (('literal', LITERALS + ALONE), ('adopt', ADOPT)):
        for text in texts:
            add(category, [f'let aNNNN: f64 = {text}'], 'aNNNN', standalone='print')
    for case in out:
        n = case['id'][1:]
        case['lines'] = [line.replace('NNNN', n) for line in case['lines']]
        if case['hole'] is not None:
            case['hole'] = case['hole'].replace('NNNN', n)
        if case['standalone'] not in (None, 'print'):
            case['standalone'] = case['standalone'].replace('NNNN', n)
    return out


HEADER = ['// Generated by tests/numeric/float_cases.py: float edge cases, one line each.',
          'fn main() -> !int {', '    let one: f64 = 1.0', '    let zero: f64 = 0.0']


def programs():
    """(name, source, case ids) in order: chunks of printed cases, then one program per standalone case."""
    all_cases = cases()
    printed = [c for c in all_cases if c['standalone'] is None]
    result = []
    for start in range(0, len(printed), CHUNK):
        chunk = printed[start:start + CHUNK]
        body = []
        for c in chunk:
            body += ['    ' + line for line in c['lines']]
            body.append(f'    print("{c["id"]} {{{c["hole"]}}}")')
        result.append((f'chunk-{start // CHUNK:02d}', '\n'.join(HEADER + body + ['    0', '}']) + '\n', [c['id'] for c in chunk]))
    for c in all_cases:
        if c['standalone'] is None:
            continue
        body = ['    ' + line for line in c['lines']]
        if c['standalone'] == 'print':
            body.append(f'    print("{c["id"]} {{{c["hole"]}}}")')
        else:
            body += [f'    let r = {c["standalone"]}', f'    print("{c["id"]} {{r}}")']
        result.append((c['id'], '\n'.join(HEADER + body + ['    0', '}']) + '\n', [c['id']]))
    return result


# Cases the pinned lupin answers differently from the native reference, each with its reason,
# keyed by (value bits, the conversion). The table keeps both answers; `check` compares with the
# native one, which is the specification's (`[type.numlit.cast.trunc]`: out of range traps).
LUPIN_DIFFERS = {
    ('43e0000000000000', 'as int'): 'lupin prints 2^63 for 2^63 as int; the native reference traps overflow',
    ('43f0000000000000', 'as u64'): 'lupin prints 2^64 for 2^64 as u64; the native reference traps overflow',
}


def lupin_differs(case):
    standalone = case.get('standalone') or ''
    return LUPIN_DIFFERS.get((case['value'], standalone.split(' ', 1)[1] if ' ' in standalone else ''))


def generator_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def outcome(observed, ids):
    """The comparable part of one program's observation: its verdict, trap kind and line,
    refusal code and line, and each case's printed text."""
    lines = (observed.get('stdout') or '').split('\n')
    printed = {}
    for line in lines:
        head, _, rest = line.partition(' ')
        if head in ids and head not in printed:
            printed[head] = rest
    # The native record names the trap's line and column; lupin's names a byte span, which the
    # agreement check does not compare (the table's answer is the native one).
    site = observed.get('trap_site')
    site = site if isinstance(site, dict) else {}
    return dict(verdict=observed.get('verdict'), trap_kind=observed.get('trap_kind'),
                trap_line=site.get('line'), trap_column=site.get('column'),
                refusal=observed.get('refusal_code') or observed.get('code'),
                printed={i: printed.get(i) for i in ids})


def capture(args):
    from frame import STAGE, oracle_identity, pins
    from differlib import execute, isolated_context, lupin_observation, observe_native
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise SystemExit('capture requires Linux x86-64 (not a skip)')
    if not os.environ.get('FENRIR_ORACLE_SANDBOX'):
        raise SystemExit('capture requires an isolated container; set FENRIR_ORACLE_SANDBOX=1 inside it')
    progs = programs()
    by_case = {c['id']: c for c in cases()}
    rows, disagreements = [], []
    (ROOT / 'target').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='float-cases-', dir=ROOT / 'target') as temp:
        for index, (name, source_text, ids) in enumerate(progs):
            scratch = Path(temp) / str(index)
            source = scratch / 'src' / f'{name}.lu'
            source.parent.mkdir(parents=True)
            source.write_text(source_text)
            env = dict(os.environ, WOLF_STD=str(STAGE / 'std'), WOLF_RT_LIB=str(STAGE / 'libwolf_rt.a'))
            roots = [(scratch, '<scratch>'), (STAGE, '<toolchain>')]
            cwd, nenv = isolated_context(scratch, 'native-run', env)
            native = observe_native(STAGE / 'wolf', source, cwd, nenv, args.timeout, roots,
                                    classification_context=isolated_context(scratch, 'native-classification', env))
            cwd, lenv = isolated_context(scratch, 'lupin', env)
            lupin = lupin_observation(execute([STAGE / 'lupin', 'conform-run', source, '--json'], cwd, lenv, args.timeout), source, roots)
            n, l = outcome(native, ids), outcome(lupin, ids)
            agree = n['printed'] == l['printed'] and n['trap_kind'] == l['trap_kind'] and \
                (n['verdict'] == l['verdict'] or n['trap_kind'] is not None)
            named = [lupin_differs(by_case[cid]) for cid in ids if lupin_differs(by_case[cid])]
            if not agree and not named:
                disagreements.append(name)
            elif agree and named:
                disagreements.append(name + ' (a named lupin difference no longer differs)')
            print(f'{"PASS" if agree or named else "FAIL"} float-capture-{name} native {n["verdict"]} lupin {l["verdict"]}'
                  + (f' (named: {named[0]})' if named and not agree else ''), flush=True)
            rows.append(dict(program=name, ids=ids, source_sha256=hashlib.sha256(source_text.encode()).hexdigest(),
                             native=n, lupin=l, native_stderr=native.get('stderr'), agree=agree))
    table = dict(format=1, generator_sha256=generator_digest(), identity=oracle_identity(pins()),
                 cases=[{k: c[k] for k in ('id', 'category', 'lines', 'hole', 'value', 'standalone')} for c in cases()],
                 programs=rows, disagreements=disagreements)
    Path(args.out).write_text(json.dumps(table, indent=1, sort_keys=True) + '\n')
    print(f'{"PASS" if not disagreements else "FAIL"} float-capture {len(rows)} programs, {len(table["cases"])} cases; '
          f'native and lupin disagree on {len(disagreements)}', flush=True)
    return int(bool(disagreements))


def shortest_ok(text, value):
    """`text` reads back to `value` and no decimal with fewer significant digits does."""
    try:
        parsed = float(text)
    except ValueError:
        return False
    if bits(parsed) != bits(value):
        return False
    digits = len(re.sub(r'^0+', '', re.sub(r'[eE].*$', '', text.lstrip('-')).replace('.', '')).rstrip('0') or '0')
    return all(bits(float(f'{value:.{d - 1}e}')) != bits(value) for d in range(1, digits))


def table_check(args):
    table = json.loads(Path(args.table).read_text())
    problems = []
    if table.get('generator_sha256') != generator_digest():
        problems.append('generator changed since the capture (recapture)')
    want = [{k: c[k] for k in ('id', 'category', 'lines', 'hole', 'value', 'standalone')} for c in cases()]
    if table.get('cases') != want:
        problems.append('the table does not name exactly the generated cases')
    progs = programs()
    if [(r['program'], r['ids'], r['source_sha256']) for r in table.get('programs', [])] != \
            [(n, ids, hashlib.sha256(s.encode()).hexdigest()) for n, s, ids in progs]:
        problems.append('the table does not hold exactly the generated programs')
    if table.get('disagreements'):
        problems.append('native and lupin disagree on ' + ', '.join(table['disagreements']))
    by_case = {c['id']: c for c in cases()}
    named = 0
    for row in table.get('programs', []):
        if any(lupin_differs(by_case[cid]) for cid in row['ids']):
            named += 1
            if row.get('agree'):
                problems.append(f'{row["program"]}: a named lupin difference no longer differs')
    crossed = 0
    for row in table.get('programs', []):
        for cid, text in row['native']['printed'].items():
            c = by_case[cid]
            if c['category'] == 'render' and c['value'] and text is not None:
                v = from_bits(int(c['value'], 16))
                if math.isfinite(v):
                    crossed += 1
                    if not shortest_ok(text, v):
                        problems.append(f'{cid} renders {text!r}, not the shortest round trip of {v!r}')
    for p in problems:
        print(f'FAIL float-cases-table {p}', flush=True)
    if not problems:
        print(f'PASS float-cases-table {len(want)} cases in {len(progs)} programs; {crossed} default renderings '
              f'read back to their double and are shortest; {named} named lupin differences', flush=True)
    return int(bool(problems))


def check(args):
    from frame import STAGE
    from differlib import execute, interpreted_observation, isolated_context, native_observation
    table = json.loads(Path(args.table).read_text())
    expected = {r['program']: r for r in table['programs']}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failed = total = 0
    for name, source_text, ids in programs():
        work = out / name
        work.mkdir(exist_ok=True)
        source = work / f'{name}.lu'
        source.write_text(source_text)
        env = dict(os.environ, WOLF_STD=str(STAGE / 'std'))
        roots = [(work, '<scratch>'), (STAGE, '<toolchain>')]
        fenrir = str(Path(args.compiler).resolve())
        if args.engine == 'native':
            built = execute([fenrir, 'build', source, '-o', work / 'program'], work, env, args.timeout)
            observed = native_observation(execute([work / 'program'], work, env, args.timeout), source, roots) \
                if built[0] == 0 else dict(verdict='refused', stdout='', stderr=built[2].decode(errors='replace'))
        else:
            built = execute([fenrir, '--emit=fir', source], work, env, args.timeout)
            if built[0] == 0:
                (work / 'program.fir').write_bytes(built[1])
                report = work / 'outcome.txt'
                result = execute([fenrir, 'interpret', work / 'program.fir', '--steps', '4000000', '--bytes', '67108864',
                                  '--report', report], work, env, args.timeout)
                observed = interpreted_observation(result, report.read_text() if report.is_file() else None, source, roots)
            else:
                observed = dict(verdict='refused', stdout='', stderr=built[2].decode(errors='replace'))
        got, want = outcome(observed, ids), expected[name]['native']
        refusal = re.search(r'error\[([A-Z]\d{4})\]', observed.get('stderr') or '')
        for cid in ids:
            total += 1
            fields = [('printed', got['printed'][cid], want['printed'][cid])]
            if want['trap_kind'] or got['trap_kind']:
                fields += [('trap', (got['trap_kind'], got['trap_line'], got['trap_column']),
                            (want['trap_kind'], want['trap_line'], want['trap_column']))]
            bad = [(k, g, w) for k, g, w in fields if g != w]
            if got['verdict'] == 'refused' and want['verdict'] != 'refused':
                bad.append(('verdict', 'refused ' + (refusal.group(1) if refusal else '?'), want['verdict']))
            if bad:
                failed += 1
                k, g, w = bad[0]
                print(f'FAIL float-case-{args.engine} {cid} {k} expected {w!r} observed {g!r}', flush=True)
    print(f'{"PASS" if not failed else "FAIL"} float-cases-{args.engine} {total - failed}/{total} cases equal the reference', flush=True)
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
    w = sub.add_parser('write-programs')
    w.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.mode == 'write-programs':
        a.out.mkdir(parents=True, exist_ok=True)
        for name, source, ids in programs():
            (a.out / name).mkdir(exist_ok=True)   # one package per program: a directory holds one
            (a.out / name / f'{name}.lu').write_text(source)
        print(f'{len(programs())} programs, {len(cases())} cases', flush=True)
        return 0
    return {'table': table_check, 'capture': capture, 'check': check}[a.mode](a)


if __name__ == '__main__':
    sys.exit(main())
