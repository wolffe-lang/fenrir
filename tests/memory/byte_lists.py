#!/usr/bin/env -S python3 -I
"""Frozen packed-byte list rows. Run both engines; refusals are failures, never skips.

The edition-7 rejection must name edition 8, and an edition-8 old-only
module must print its minimal edition. Source value rows can already pass
before storage is repaired; their separate shape checks and ledger rows
expose the missing packed representation without inventing a wrong value.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LEDGER = 'payload 65536 | holds_payload true | growth_bound true | width_retired true | small true | monotone true\n'
PUSH = '''    var xs = List[byte]()
    (mut xs).push(0 as byte)
    (mut xs).push(127 as byte)
    (mut xs).push(128 as byte)
    (mut xs).push(255 as byte)
'''
SOURCES = [
    ('values', 'fn main() {\n' + PUSH + '''    print("{xs[0] as int} {xs[1] as int} {xs[2] as int} {xs[3] as int}")
}
''', '0 127 128 255\n'),
    ('copy-slice', 'fn main() {\n' + PUSH + '''    var ys = copy xs
    ys[0] = 255 as byte
    var zs = xs[1..4]
    zs[0] = 0 as byte
    print("{xs[0] as int} {xs[1] as int} {ys[0] as int} {zs[0] as int}")
}
''', '0 127 255 0\n'),
    ('options-reset', 'fn main() {\n' + PUSH + '''    let read = xs.get(2) else 0 as byte
    let last = (mut xs).pop() else 0 as byte
    (mut xs).reserve(32)
    (mut xs).reset()
    let empty = (mut xs).pop() else 17 as byte
    (mut xs).push(128 as byte)
    print("{read as int} {last as int} {empty as int} {xs[0] as int}")
}
''', '128 255 17 128\n'),
    ('materialized-text', '''fn main() {
    var xs = "AZ".bytes()
    let s = str_from_utf8(xs) else "bad"
    xs[0] = 90 as byte
    let where = bytes_find(xs, 90 as byte, 0) else -1
    let count = bytes_count(xs, 90 as byte)
    print("{s} {xs[0] as int} {where} {count}")
}
''', 'AZ 90 0 2\n'),
    ('outer-copy-width', '''fn main() {
    region dest {
        var keep = List[byte]()
        let header = region_bytes(dest)
        region source {
            var xs = List[byte]()
            for i in 0..1024 { (mut xs).push((i % 256) as byte) }
            keep = copy xs
        }
        let used = region_bytes(dest) - header
        print("{keep[0] as int} {keep[127] as int} {keep[128] as int} {keep[255] as int} {used <= 2176}")
    }
}
''', '0 127 128 255 true\n'),
]


def module(edition, shapes, code):
    return (f'fir {edition}\nblobs 1\nblob ' + b'byte-list.lu'.hex() + '\nsites 1\nsite 0 1 1\n'
            + f'shapes {len(shapes)}\n' + ''.join(x + '\n' for x in shapes)
            + 'functions 1\nfunction 1 0 0 1\nblock 0 ' + str(len(code)) + '\n'
            + ''.join(x + '\n' for x in code) + 'end\n')


def minimal(edition):
    text = module(edition, [], ['const 1 0 1 0 0', 'return 0 0 0 1 0'])
    return text.replace('shapes 0\n', 'structs 0\n') if edition == 1 else text


def packed_values():
    code = ['list 10 0 0 0']
    values = [0, 127, 128, 255, -1, 256, 511]
    next_value = 1
    for value in values:
        code += [f'const 1 0 1 {value} 0', f'push 0 0 0 2 0 {next_value}']
        next_value += 2
    for index in range(len(values)):
        code += [f'const 1 0 1 {index} 0', f'get 1 0 0 2 0 {next_value}',
                 f'print 0 0 0 1 {next_value + 1}']
        next_value += 3
    code += ['const 1 0 1 0 0', f'return 0 0 0 1 {next_value}']
    return module(8, ['bytes 1 1'], code), '0\n127\n128\n255\n255\n0\n255\n'


def run(argv, work, timeout=300):
    home = work / 'home'
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HOME=str(home), SHELL='/bin/sh')
    return subprocess.run(list(map(str, argv)), cwd=work, env=env, capture_output=True, timeout=timeout)


def fact(ok, name, detail=''):
    print(('PASS ' if ok else 'FAIL ') + name + (' ' + detail if detail else ''), flush=True)
    return int(not ok)


def execute_fir(compiler, engine, source, work):
    if engine == 'interpreter':
        report = work / 'outcome'
        if report.exists():
            report.unlink()
        p = run([compiler, 'interpret', source, '--steps', '20000000', '--bytes', str(64 << 20), '--report', report], work)
        outcome = report.read_text() if report.is_file() else None
    else:
        program = work / 'program'
        p = run([compiler, 'link', source, '-o', program], work)
        if p.returncode:
            return p, None
        p = run([program], work)
        outcome = 'exit ' + str(p.returncode) + '\n'
    return p, outcome


def format_rows(compiler, out):
    failed = 0
    work = out / 'format'
    work.mkdir(parents=True, exist_ok=True)
    old = work / 'edition7-bytes.fir'
    old.write_text(module(7, ['bytes 1 1'], ['const 1 0 1 0 0', 'return 0 0 0 1 0']))
    dest = work / 'preserved.fir'
    dest.write_text('preserve me\n')
    p = run([compiler, 'fir', old, '-o', dest], work)
    ok = p.returncode == 2 and b'FIR_SYNTAX a bytes shape needs edition 8' in p.stderr \
        and dest.read_text() == 'preserve me\n'
    failed += fact(ok, 'byte-edition7-bytes-shape', 'exit=' + str(p.returncode))
    plain = work / 'edition8-no-bytes.fir'
    plain.write_text(minimal(8))
    p = run([compiler, 'fir', plain, '-o', dest], work)
    failed += fact(p.returncode == 0 and dest.read_text() == minimal(1),
                   'byte-edition8-no-bytes-minimal', 'exit=' + str(p.returncode))
    packed = work / 'edition8-values.fir'
    text, _ = packed_values()
    packed.write_text(text)
    p = run([compiler, 'fir', packed, '-o', dest], work)
    canonical = dest.read_text() if p.returncode == 0 else ''
    if p.returncode == 0:
        again = work / 'again.fir'
        q = run([compiler, 'fir', dest, '-o', again], work)
        ok = q.returncode == 0 and again.read_text() == canonical and canonical.startswith('fir 8\n')
    else:
        ok = False
    failed += fact(ok, 'byte-edition8-fixed-point', 'exit=' + str(p.returncode))
    return failed


def reference_cases(out):
    failures = 0
    for name, text, expected in source_cases():
        work = out / 'reference' / name
        work.mkdir(parents=True, exist_ok=True)
        source = work / 'main.lu'
        source.write_text(text)
        native = run([ROOT / '.wolf-bin/wolf', 'run', '--no-cache', source], work)
        lupin = run([ROOT / '.wolf-bin/lupin', 'conform-run', '--json', source], work)
        try:
            record = json.loads(lupin.stdout)
        except ValueError:
            record = {}
        ok = native.returncode == 0 and native.stdout.decode(errors='replace') == expected \
            and lupin.returncode == 0 and record.get('verdict') == 'exit(0)' \
            and record.get('stdout_inline') == expected
        failures += fact(ok, 'byte-reference-' + name,
                         'both oracles execute' if ok else 'native=' + str(native.returncode)
                         + ' lupin=' + str(lupin.returncode) + ' stderr=' + repr(native.stderr[:240])
                         + ' record=' + repr(record))
    return failures


def source_cases():
    return SOURCES + [('ledger', (ROOT / '.wolf-bin/reference/corpus/memory/byte_list_ledger.lu').read_text(), LEDGER)]


def check(compiler, engine, out, smoke=False):
    failures = format_rows(compiler, out)
    work = out / 'fir-values'
    work.mkdir(parents=True, exist_ok=True)
    source = work / 'main.fir'
    text, expected = packed_values()
    source.write_text(text)
    p, outcome = execute_fir(compiler, engine, source, work)
    failures += fact(p.returncode == 0 and outcome == 'exit 0\n' and p.stdout.decode(errors='replace') == expected,
                     'byte-fir-zero-extension-' + engine, 'exit=' + str(p.returncode) + ' outcome=' + repr(outcome))
    for name, text, expected in source_cases():
        if smoke and name not in ('values', 'outer-copy-width'):
            continue
        work = out / name
        work.mkdir(parents=True, exist_ok=True)
        source = work / 'main.lu'
        source.write_text(text)
        emitted = run([compiler, '--emit=fir', source], work)
        packed = emitted.returncode == 0 and b'\nbytes 1 1\n' in emitted.stdout
        failures += fact(packed, 'byte-source-shape-' + name + '-' + engine,
                         'emit=' + str(emitted.returncode))
        if emitted.returncode:
            failures += fact(False, 'byte-source-' + name + '-' + engine,
                             'emit refused: ' + repr(emitted.stderr[:240]))
            continue
        fir = work / 'main.fir'
        fir.write_bytes(emitted.stdout)
        p, outcome = execute_fir(compiler, engine, fir, work)
        ok = p.returncode == 0 and outcome == 'exit 0\n' and p.stdout.decode(errors='replace') == expected
        failures += fact(ok, 'byte-source-' + name + '-' + engine,
                         'exit=' + str(p.returncode) + ' outcome=' + repr(outcome)
                         + ('' if ok else ' stdout=' + repr(p.stdout[:240]) + ' stderr=' + repr(p.stderr[:160])))
    return failures


def selftest():
    text, expected = packed_values()
    lines = text.splitlines()
    block = next(x for x in lines if x.startswith('block '))
    assert int(block.split()[2]) == len(lines) - lines.index(block) - 2
    assert expected == '0\n127\n128\n255\n255\n0\n255\n'
    assert minimal(1).startswith('fir 1\n') and 'structs 0\n' in minimal(1)
    assert minimal(8).startswith('fir 8\n') and 'shapes 0\n' in minimal(8)
    assert len({name for name, _, _ in SOURCES}) == len(SOURCES)
    print('PASS byte-list-fixture-selftest', flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['selftest', 'reference', 'check'])
    parser.add_argument('--compiler', type=Path)
    parser.add_argument('--engine', choices=['interpreter', 'native'])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--smoke', action='store_true')
    a = parser.parse_args()
    if a.mode == 'selftest':
        return selftest()
    if not a.out:
        parser.error('--out required')
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if a.mode == 'reference':
        failed = reference_cases(out)
    else:
        if not a.compiler or not a.engine:
            parser.error('check requires --compiler and --engine')
        if a.engine == 'native' and sys.platform != 'linux':
            parser.error('native execution requires Linux; not a skip')
        failed = check(a.compiler.resolve(), a.engine, out, a.smoke)
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
