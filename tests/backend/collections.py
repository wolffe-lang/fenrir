#!/usr/bin/env python3
"""Edition-3 contracts: lists of every value type, maps and their reads.

Prediction: before edition 3 exists, the first list round trip is refused
(`FIR_SYNTAX unknown edition 3`). After it, every round trip prints edition 3
back byte for byte, every malformed module is refused by name, each finite
fixture prints and exits (or traps `bounds` at its site) identically through
the bounded interpreter and, on Linux, natively through clef and ligature.
Recoverable reads answer a two-variant enum: the element, or the empty variant.
"""
import argparse
import os
from pathlib import Path
import resource
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def inst(op, ty=0, site=0, data=(), uses=()):
    return f"{op} {ty} {site} {len(data)}" + "".join(f" {x}" for x in data) + f" {len(uses)}" + "".join(f" {x}" for x in uses)


I = inst
BLOBS = ['proof.lu', 'hello, wolf', 'none', 'hello, ', 'wolf', 'some']
NONE, HELLO_, WOLF, SOME = 2, 3, 4, 5


def hexed(text):
    return text.encode().hex() or '-'


def module(blocks, shapes, slots=(), edition=3, functions=()):
    """One FIR module: function 0 is `blocks`; `functions` adds (result, params, slots, blocks)."""
    lines = [f"fir {edition}", f"blobs {len(BLOBS)}", *[f"blob {hexed(b)}" for b in BLOBS],
             "sites 2", "site 0 1 1", "site 0 7 3", f"shapes {len(shapes)}"]
    for kind, fields in shapes:
        lines.append(f"{kind} {len(fields)}" + "".join(f" {x}" for x in fields))
    every = [(1, (), slots, blocks), *functions]
    lines.append(f"functions {len(every)}")
    for result, params, fslots, fblocks in every:
        lines.append(f"function {result} {len(params)}" + "".join(f" {x}" for x in params)
                     + f" {len(fslots)}" + "".join(f" {x}" for x in fslots) + f" {len(fblocks)}")
        for ps, code in fblocks:
            lines += [f"block {len(ps)}" + "".join(f" {x}" for x in ps) + f" {len(code)}", *code]
    return "\n".join([*lines, "end", ""])


def straight(code, shapes, slots=()):
    return module([((), code)], shapes, slots)


NEW_OPS = {'set', 'pop', 'read', 'clear', 'slice', 'map', 'lookup', 'insert', 'remove', 'pairs'}


def canonical(text):
    """The printed form: the lowest edition that carries the module."""
    lines = text.split('\n')
    head = next(i for i, l in enumerate(lines) if l.startswith('shapes '))
    tail = next(i for i, l in enumerate(lines) if l.startswith('functions '))
    kinds = {l.split(' ')[0] for l in lines[head + 1:tail]}
    ops = {l.split(' ')[0] for l in lines[tail + 1:]}
    if kinds & {'list', 'map'} or ops & NEW_OPS:
        return text
    if 'enum' in kinds:
        return text.replace('fir 3\n', 'fir 2\n', 1)
    return text.replace('fir 3\n', 'fir 1\n', 1).replace('\nshapes ', '\nstructs ', 1)


C0 = I('const', 1, data=(0,))
# Shapes shared by the option fixtures: an int option at 12, a str option at 15.
OPT_INT = [('struct', (1,)), ('struct', ()), ('enum', (10, 11))]


def fixtures():
    """(name, text, stdout, outcome): outcome is `exit 0` or `trap bounds`."""
    # A list of str: push, len, get.
    yield 'list-str', straight([
        I('list', 10), I('string', 3, data=(1,)), I('push', uses=(0, 1)), I('push', uses=(0, 1)),
        I('len', 1, uses=(0,)), I('print', uses=(4,)), I('const', 1, data=(1,)), I('get', 3, uses=(0, 6)),
        I('print', uses=(7,)), C0, I('return', uses=(9,))], [('list', (3,))]), '2\nhello, wolf\n', 'exit 0'
    # A list of structs: set replaces an element whole.
    yield 'list-struct-set', straight([
        I('list', 11), I('const', 1, data=(7,)), I('string', 3, data=(1,)), I('struct', 10, uses=(1, 2)),
        I('push', uses=(0, 3)), I('const', 1, data=(9,)), I('struct', 10, uses=(5, 2)), C0,
        I('set', uses=(0, 7, 6)), I('get', 10, uses=(0, 7)), I('field', 1, data=(0,), uses=(9,)),
        I('print', uses=(10,)), I('field', 3, data=(1,), uses=(9,)), I('print', uses=(12,)),
        I('len', 1, uses=(0,)), I('print', uses=(14,)), I('return', uses=(7,))],
        [('struct', (1, 3)), ('list', (10,))]), '9\nhello, wolf\n1\n', 'exit 0'
    # Element reads and writes outside the list trap `bounds` at their site.
    for name, code in [
            ('list-get-bounds', [I('list', 4), I('const', 1, data=(0,)), I('get', 1, site=1, uses=(0, 1)), I('return', uses=(2,))]),
            ('list-get-negative', [I('list', 4), I('const', 1, data=(5,)), I('push', uses=(0, 1)), I('const', 1, data=(-1,)),
                                   I('get', 1, site=1, uses=(0, 3)), I('return', uses=(4,))]),
            ('list-set-bounds', [I('list', 4), I('const', 1, data=(1,)), I('set', site=1, uses=(0, 1, 1)), I('return', uses=(1,))])]:
        yield name, straight(code, []), '', 'trap bounds'
    # pop answers the last element, then the empty variant once the list is empty.
    blocks = [((), [I('list', 4), I('const', 1, data=(5,)), I('push', uses=(0, 1)), I('pop', 12, uses=(0,)),
                    I('case', data=(0, 1, 3, 1), uses=(3, 0))]),
              ((10, 4), [I('field', 1, data=(0,), uses=(0,)), I('print', uses=(2,)), I('pop', 12, uses=(1,)),
                         I('case', data=(1, 2, 3, 0), uses=(4,))]),
              ((11,), [I('string', 3, data=(NONE,)), I('print', uses=(1,)), C0, I('return', uses=(3,))]),
              ((), [I('trap', data=(4,))])]
    yield 'list-pop', module(blocks, OPT_INT), '5\nnone\n', 'exit 0'
    # read answers an element in range and the empty variant outside it.
    blocks = [((), [I('list', 4), I('const', 1, data=(8,)), I('push', uses=(0, 1)), C0, I('read', 12, uses=(0, 3)),
                    I('case', data=(0, 1, 4, 1), uses=(4, 0))]),
              ((10, 4), [I('field', 1, data=(0,), uses=(0,)), I('print', uses=(2,)), I('const', 1, data=(-1,)),
                         I('read', 12, uses=(1, 4)), I('case', data=(1, 2, 4, 1), uses=(5, 1))]),
              ((11, 4), [I('const', 1, data=(1,)), I('read', 12, uses=(1, 2)), I('case', data=(1, 3, 4, 0), uses=(3,))]),
              ((11,), [I('string', 3, data=(NONE,)), I('print', uses=(1,)), C0, I('return', uses=(3,))]),
              ((), [I('trap', data=(4,))])]
    yield 'list-read', module(blocks, OPT_INT), '8\nnone\n', 'exit 0'
    yield 'list-clear', straight([
        I('list', 4), I('const', 1, data=(3,)), I('push', uses=(0, 1)), I('push', uses=(0, 1)), I('clear', uses=(0,)),
        I('len', 1, uses=(0,)), I('print', uses=(5,)), I('push', uses=(0, 1)), I('len', 1, uses=(0,)),
        I('print', uses=(8,)), C0, I('return', uses=(10,))], []), '0\n1\n', 'exit 0'
    pushes = [I('list', 4)]
    for k in range(4):
        pushes += [I('const', 1, data=(k + 1,)), I('push', uses=(0, len(pushes)))]
    base = len(pushes)
    yield 'list-slice', straight(pushes + [
        I('const', 1, data=(1,)), I('const', 1, data=(3,)), I('slice', 4, uses=(0, base, base + 1)),
        I('len', 1, uses=(base + 2,)), I('print', uses=(base + 3,)), C0, I('get', 1, uses=(base + 2, base + 5)),
        I('print', uses=(base + 6,)), I('const', 1, data=(9,)), I('push', uses=(base + 2, base + 8)),
        I('len', 1, uses=(0,)), I('print', uses=(base + 10,)), I('return', uses=(base + 5,))], []), '2\n2\n4\n', 'exit 0'
    for name, lo, hi in [('list-slice-reversed', 3, 1), ('list-slice-past-end', 0, 5), ('list-slice-negative', -1, 2)]:
        yield name, straight(pushes + [I('const', 1, data=(lo,)), I('const', 1, data=(hi,)),
                                       I('slice', 4, site=1, uses=(0, base, base + 1)), I('return', uses=(base,))], []), '', 'trap bounds'
    # A list of lists: the inner handle is an element like any other.
    yield 'list-nested', straight([
        I('list', 10), I('list', 4), I('const', 1, data=(7,)), I('push', uses=(1, 2)), I('push', uses=(0, 1)),
        C0, I('get', 4, uses=(0, 5)), I('get', 1, uses=(6, 5)), I('print', uses=(7,)), I('len', 1, uses=(0,)),
        I('print', uses=(9,)), I('return', uses=(5,))], [('list', (4,))]), '7\n1\n', 'exit 0'
    # A list survives a call and a slot round trip as its handle.
    callee = (1, (10,), (), [((10,), [I('len', 1, uses=(0,)), I('return', uses=(1,))])])
    yield 'list-call-slot', module([((), [
        I('list', 10), I('string', 3, data=(1,)), I('push', uses=(0, 1)), I('store', data=(0,), uses=(0,)),
        I('load', 10, data=(0,)), I('call', 1, data=(1,), uses=(4,)), I('print', uses=(5,)), C0, I('return', uses=(7,))])],
        [('list', (3,))], slots=(10,), functions=[callee]), '1\n', 'exit 0'
    # Map[int, str]: insert, replace, len, lookup hit and miss, remove, clear.
    shapes = [('map', (1, 3)), ('struct', (3,)), ('struct', ()), ('enum', (11, 12))]
    blocks = [((), [I('map', 10), I('const', 1, data=(1,)), I('const', 1, data=(2,)), I('string', 3, data=(SOME,)),
                    I('string', 3, data=(1,)), I('insert', uses=(0, 1, 3)), I('insert', uses=(0, 2, 3)),
                    I('insert', uses=(0, 1, 4)), I('len', 1, uses=(0,)), I('print', uses=(8,)),
                    I('lookup', 13, uses=(0, 1)), I('case', data=(0, 1, 5, 1), uses=(10, 0))]),
              ((11, 10), [I('field', 3, data=(0,), uses=(0,)), I('print', uses=(2,)), I('const', 1, data=(3,)),
                          I('lookup', 13, uses=(1, 4)), I('case', data=(1, 2, 5, 1), uses=(5, 1))]),
              ((12, 10), [I('const', 1, data=(1,)), I('remove', 13, uses=(1, 2)), I('case', data=(0, 3, 5, 1), uses=(3, 1))]),
              ((11, 10), [I('field', 3, data=(0,), uses=(0,)), I('print', uses=(2,)), I('len', 1, uses=(1,)),
                          I('print', uses=(4,)), I('const', 1, data=(1,)), I('remove', 13, uses=(1, 6)),
                          I('case', data=(1, 4, 5, 1), uses=(7, 1))]),
              ((12, 10), [I('clear', uses=(1,)), I('len', 1, uses=(1,)), I('print', uses=(3,)), C0, I('return', uses=(5,))]),
              ((), [I('trap', data=(4,))])]
    yield 'map-int', module(blocks, shapes), '2\nhello, wolf\nhello, wolf\n1\n0\n', 'exit 0'
    # Map[str, int]: a key built at run time finds the literal key's entry by
    # its bytes; pairs() reports insertion order as (key, value) records.
    shapes = [('map', (3, 1)), ('struct', (1,)), ('struct', ()), ('enum', (11, 12)), ('struct', (3, 1)), ('list', (14,))]
    blocks = [((), [I('map', 10), I('string', 3, data=(1,)), I('const', 1, data=(42,)), I('insert', uses=(0, 1, 2)),
                    I('string', 3, data=(WOLF,)), I('const', 1, data=(7,)), I('insert', uses=(0, 4, 5)),
                    I('string', 3, data=(HELLO_,)), I('concat', 3, uses=(7, 4)), I('lookup', 13, uses=(0, 8)),
                    I('case', data=(0, 1, 2, 1), uses=(9, 0))]),
              ((11, 10), [I('field', 1, data=(0,), uses=(0,)), I('print', uses=(2,)), I('pairs', 15, uses=(1,)),
                          I('len', 1, uses=(4,)), I('print', uses=(5,)), C0, I('get', 14, uses=(4, 7)),
                          I('field', 3, data=(0,), uses=(8,)), I('print', uses=(9,)), I('const', 1, data=(1,)),
                          I('get', 14, uses=(4, 11)), I('field', 3, data=(0,), uses=(12,)), I('print', uses=(13,)),
                          I('field', 1, data=(1,), uses=(12,)), I('print', uses=(15,)), I('return', uses=(7,))]),
              ((), [I('trap', data=(4,))])]
    yield 'map-str', module(blocks, shapes), '42\n2\nhello, wolf\nwolf\n7\n', 'exit 0'
    # A map whose values are lists: the value is the list's handle.
    shapes = [('map', (2, 4)), ('struct', (4,)), ('struct', ()), ('enum', (11, 12))]
    blocks = [((), [I('map', 10), I('const', 2, data=(1,)), I('list', 4), I('const', 1, data=(6,)),
                    I('push', uses=(2, 3)), I('insert', uses=(0, 1, 2)), I('lookup', 13, uses=(0, 1)),
                    I('case', data=(0, 1, 2, 0), uses=(6,))]),
              ((11,), [I('field', 4, data=(0,), uses=(0,)), C0, I('get', 1, uses=(1, 2)), I('print', uses=(3,)), I('return', uses=(2,))]),
              ((), [I('trap', data=(4,))])]
    yield 'map-bool-list', module(blocks, shapes), '6\n', 'exit 0'


def rejections():
    base = fixtures()
    text = dict((name, t) for name, t, _, _ in base)
    lstr = text['list-str']
    mint = text['map-int']
    for name, source, old, new, error in [
            ('list-of-int-shape', lstr, 'list 1 3', 'list 1 1', 'FIR_TYPE'),
            ('list-of-unit', lstr, 'list 1 3', 'list 1 0', 'FIR_TYPE'),
            ('list-forward', lstr, 'list 1 3', 'list 1 10', 'FIR_TYPE'),
            ('list-arity', lstr, 'list 1 3', 'list 2 3 3', 'FIR_TYPE'),
            ('push-element', lstr, I('push', uses=(0, 1)), I('push', uses=(0, 0)), 'FIR_TYPE'),
            ('get-result', lstr, I('get', 3, uses=(0, 6)), I('get', 1, uses=(0, 6)), 'FIR_TYPE'),
            ('get-index', lstr, I('get', 3, uses=(0, 6)), I('get', 3, uses=(0, 1)), 'FIR_TYPE'),
            ('len-scalar', lstr, I('len', 1, uses=(0,)), I('len', 1, uses=(1,)), 'FIR_TYPE'),
            ('list-result', lstr, I('list', 10), I('list', 3), 'FIR_TYPE'),
            ('map-struct-key', mint, 'map 2 1 3', 'map 2 11 3', 'FIR_TYPE'),
            ('map-forward-value', mint, 'map 2 1 3', 'map 2 1 13', 'FIR_TYPE'),
            ('map-arity', mint, 'map 2 1 3', 'map 1 1', 'FIR_TYPE'),
            ('insert-value', mint, I('insert', uses=(0, 1, 3)), I('insert', uses=(0, 1, 2)), 'FIR_TYPE'),
            ('insert-arity', mint, I('insert', uses=(0, 1, 3)), I('insert', uses=(0, 1)), 'FIR_ARITY'),
            ('lookup-key', mint, I('lookup', 13, uses=(0, 1)), I('lookup', 13, uses=(0, 3)), 'FIR_TYPE'),
            ('lookup-option', mint, I('lookup', 13, uses=(0, 1)), I('lookup', 11, uses=(0, 1)), 'FIR_TYPE'),
            ('edition-2-list-shape', lstr, 'fir 3', 'fir 2', 'FIR_SYNTAX'),
            ('edition-5', lstr, 'fir 3', 'fir 5', 'FIR_SYNTAX'),
    ]:
        assert old in source, name
        yield 'reject-' + name, source.replace(old, new, 1), error
    pop = text['list-pop']
    for name, old, new, error in [
            ('pop-option-shape', 'enum 2 10 11', 'enum 2 11 10', 'FIR_TYPE'),
            ('pop-option-payload', 'struct 1 1', 'struct 1 2', 'FIR_TYPE'),
            ('pop-arity', I('pop', 12, uses=(0,)), I('pop', 12, uses=(0, 0)), 'FIR_ARITY')]:
        assert old in pop, name
        yield 'reject-' + name, pop.replace(old, new, 1), error
    mstr = text['map-str']
    old = I('pairs', 15, uses=(1,))
    yield 'reject-pairs-record', mstr.replace('struct 2 3 1', 'struct 2 1 3', 1), 'FIR_TYPE'
    yield 'reject-pairs-result', mstr.replace(old, I('pairs', 10, uses=(1,)), 1), 'FIR_TYPE'
    # New instructions need edition 3 even without a list or map shape.
    yield 'reject-edition-2-set', straight([I('list', 4), C0, I('set', uses=(0, 1, 1)), I('return', uses=(1,))], []).replace('fir 3', 'fir 2'), 'FIR_SYNTAX'
    slices = text['list-slice']
    yield 'reject-slice-result', slices.replace(I('slice', 4, uses=(0, 9, 10)), I('slice', 1, uses=(0, 9, 10)), 1), 'FIR_TYPE'


# Aggregates count against the interpreter's memory budget. Each program fills
# one container with N elements of W words in a loop; the least budget that
# lets it exit is found by bisection, and the growth over the one-element run
# is the storage the ledger charged for N - 1 more elements.
BUDGET_POINTS = (1, 1000, 10000, 100000)


def filling(kind, n):
    """(text, words per element): a loop of `n` pushes or inserts, then exit 0."""
    if kind == 'list-int':
        shapes, ty, words, body = [], 4, 1, [I('push', uses=(0, 1))]
    elif kind == 'list-record':
        shapes, ty, words = [('struct', (1, 1, 1)), ('list', (10,))], 11, 3
        body = [I('struct', 10, uses=(1, 1, 1)), I('push', uses=(0, 2))]
    else:
        shapes, ty, words, body = [('map', (1, 1))], 10, 2, [I('insert', uses=(0, 1, 1))]
    step = len(body) + 2
    blocks = [((), [I('list' if kind != 'map-int' else 'map', ty), C0, I('jump', data=(1,), uses=(0, 1))]),
              ((ty, 1), [I('const', 1, data=(n,)), I('lt', 2, uses=(1, 2)), I('branch', data=(2, 3, 2), uses=(3, 0, 1))]),
              ((ty, 1), [*body, I('const', 1, data=(1,)), I('add', 1, uses=(1, step)), I('jump', data=(1,), uses=(0, step + 1))]),
              ((), [C0, I('return', uses=(0,))])]
    return module(blocks, shapes), words


def least_budget(compiler, src, report):
    """The least --bytes that lets `src` exit; every smaller budget is refused by name."""
    def outcome(budget):
        p = run([compiler, 'interpret', src, '--steps', '100000000', '--bytes', str(budget), '--report', report],
                memory=1 << 30, cpu=60, timeout=120)
        text = report.read_text() if report.exists() else ''
        if text == 'exit 0\n' and p.returncode == 0:
            return True
        assert text == 'refused FIR_MEMORY_BUDGET\n' and p.returncode == 4 and b'FIR_MEMORY_BUDGET' in p.stderr, (budget, p.returncode, text, p.stderr[:200])
        return False
    low, high = 0, 1 << 16
    while not outcome(high):
        low, high = high, high * 2
        assert high <= 1 << 32, 'no budget lets the program exit'
    while high - low > 1:
        middle = (low + high) // 2
        if outcome(middle):
            high = middle
        else:
            low = middle
    return high


def budget_rows(compiler, out):
    """Yield (name, ok, line): per-element charges must fall in [8 W, 64 W] bytes."""
    for kind in ('list-int', 'list-record', 'map-int'):
        least = {}
        for n in BUDGET_POINTS:
            text, words = filling(kind, n)
            src = out / f'budget-{kind}-{n}.fir'
            src.write_text(text)
            least[n] = least_budget(compiler, src, out / f'budget-{kind}-{n}.outcome')
        for n in BUDGET_POINTS[1:]:
            per = (least[n] - least[1]) / ((n - 1) * words)
            ok = 8 <= per <= 64
            yield f'budget-{kind}-{n}', ok, f'least={least[n]} one={least[1]} words={words} bytes-per-word={per:.2f}'


def limits(memory=512 << 20, cpu=30):
    def apply():
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    return apply


def run(argv, memory=512 << 20, cpu=30, timeout=60, **kw):
    opts = {'preexec_fn': limits(memory, cpu)} if sys.platform == 'linux' else {}
    return subprocess.run([str(x) for x in argv], capture_output=True, timeout=timeout, **opts, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('compiler', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--native', action='store_true')
    a = ap.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    compiler = a.compiler.resolve()
    env = dict(os.environ, FENRIR_TOOLCHAIN=str(ROOT / '.wolf-bin'))
    failed = 0
    for name, text, error in [(n, t, None) for n, t, _, _ in fixtures()] + list(rejections()):
        src, out = a.out / (name + '.fir'), a.out / (name + '.canonical')
        src.write_text(text)
        out.write_text('sentinel')
        p = run([compiler, 'fir', src, '-o', out])
        try:
            if error:
                assert p.returncode == 2 and error.encode() in p.stderr and out.read_text() == 'sentinel', (p.returncode, p.stderr)
            else:
                assert p.returncode == 0, (p.returncode, p.stderr)
                assert out.read_text() == canonical(text), 'not canonical: the printed module differs from its source'
                again = a.out / 'again.fir'
                q = run([compiler, 'fir', out, '-o', again])
                assert q.returncode == 0 and again.read_bytes() == out.read_bytes()
        except AssertionError as failure:
            print(f'FAIL {name} {failure}', flush=True)
            failed += 1
            continue
        print('PASS ' + name, flush=True)
    for name, text, expected, outcome in fixtures():
        src, report = a.out / (name + '.fir'), a.out / (name + '.outcome')
        status = 0 if outcome == 'exit 0' else 134
        p = run([compiler, 'interpret', src, '--steps', '10000', '--bytes', str(1 << 20), '--report', report])
        got = (p.returncode, p.stdout, report.read_text() if report.exists() else '')
        if got != (status, expected.encode(), outcome + '\n') or (status == 134 and not p.stderr.startswith(b'wolf-trap: bounds\n  at proof.lu:7:3')):
            print(f'FAIL interpret-{name} {got} {p.stderr[:200]}', flush=True)
            failed += 1
            continue
        print('PASS interpret-' + name, flush=True)
        assembly = a.out / (name + '.s')
        q = run([compiler, 'asm', src, '-o', assembly])
        first = assembly.read_bytes() if q.returncode == 0 else b''
        q2 = run([compiler, 'asm', src, '-o', assembly])
        if q.returncode or q2.returncode or assembly.read_bytes() != first:
            print(f'FAIL asm-{name} {q.returncode} {q.stderr[:300]}', flush=True)
            failed += 1
            continue
        if a.native:
            assert sys.platform == 'linux', 'native proof requires Linux; this is not a skip'
            binary = a.out / (name + '.exe')
            q = run([compiler, 'link', src, '-o', binary], memory=2 << 30, cpu=180, timeout=240, env=env)
            if q.returncode:
                print(f'FAIL link-{name} {q.stderr[:300]}', flush=True)
                failed += 1
                continue
            q = run([binary])
            (a.out / (name + '.native.stdout')).write_bytes(q.stdout)
            (a.out / (name + '.native.stderr')).write_bytes(q.stderr)
            if (p.returncode, p.stdout, p.stderr) != (q.returncode, q.stdout, q.stderr):
                print(f'FAIL collections-differential-{name} differs STOP {q.returncode} {q.stdout[:200]} {q.stderr[:200]}', flush=True)
                failed += 1
                continue
            print('PASS native-' + name, flush=True)
    for name, ok, line in budget_rows(compiler, a.out):
        print(f"{'PASS' if ok else 'FAIL'} {name} {line}", flush=True)
        failed += 0 if ok else 1
    print(f'collections: {failed} failed', flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
