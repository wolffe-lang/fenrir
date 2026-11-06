#!/usr/bin/env python3
"""Edition-2 contracts, bounded execution and sequential native parity.

Prediction: edition 1 rejects the first enum roundtrip. After implementation,
all roundtrips/refusals and the in-memory consumer pass; each finite fixture
has identical interpreter/native output. No inactive payload is projected.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('fir_rows', Path(__file__).with_name('fir.py'))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
I = f.inst
C = I('const', 1, data=(0,))
S = [('struct', (1,)), ('struct', (3,)), ('enum', (10, 11))]


def done(params=0):
    return [C, I('return', uses=(params,))]


def fixtures():
    # Int bits 42 must never be interpreted as an inactive string handle.
    for tag, scalar, payload, other in [(0, I('const', 1, data=(42,)), 10, 11),
                                       (1, I('string', 3, data=(1,)), 11, 10)]:
        ty = 1 if tag == 0 else 3
        other_ty = 3 if tag == 0 else 1
        blocks = [([], [scalar, I('struct', payload, uses=(0,)), I('enum', 12, data=(tag,), uses=(1,)),
                       I('case', data=(1-tag, 1, 2, 0), uses=(2, 2))]),
                  ([other], [I('field', other_ty, data=(0,), uses=(0,)), I('print', uses=(1,)), *done(3)]),
                  ([12], [I('case', data=(tag, 3, 4, 0), uses=(0,))]),
                  ([payload], [I('field', ty, data=(0,), uses=(0,)), I('print', uses=(1,)), *done(3)]),
                  ([], [I('trap', data=(4,))])]
        yield f'enum-inactive-{tag}', f.module([], blocks=blocks, shapes=S), '42\n' if tag == 0 else 'hello, wolf\n'
    shapes = [('struct', ()), ('struct', (3,)), ('enum', (10, 11))]
    blocks = [([], [I('struct', 10), I('enum', 12, data=(0,), uses=(0,)), I('const', 1, data=(42,)),
                    I('case', data=(0, 1, 2, 1), uses=(1, 2))]),
              ([10, 1], [I('print', uses=(1,)), *done(3)]), ([], [I('trap', data=(4,))])]
    yield 'enum-empty-payload', f.module([], blocks=blocks, shapes=shapes), '42\n'
    nested = S + [('struct', (12,)), ('enum', (13,)), ('struct', (14,))]
    blocks = [([], [I('string', 3, data=(1,)), I('struct', 11, uses=(0,)), I('enum', 12, data=(1,), uses=(1,)),
                    I('struct', 13, uses=(2,)), I('enum', 14, data=(0,), uses=(3,)), I('struct', 15, uses=(4,)),
                    I('store', data=(0,), uses=(5,)), I('load', 14, data=(0, 0)), I('case', data=(0, 1, 3, 0), uses=(7,))]),
              ([13], [I('field', 12, data=(0,), uses=(0,)), I('case', data=(1, 2, 3, 0), uses=(1,))]),
              ([11], [I('field', 3, data=(0,), uses=(0,)), I('print', uses=(1,)), *done(3)]),
              ([], [I('trap', data=(4,))])]
    yield 'enum-nested-slot', f.module([], blocks=blocks, shapes=nested, slots=(15,)), 'hello, wolf\n'
    blocks = [([], [I('const', 1, data=(42,)), I('struct', 10, uses=(0,)), I('enum', 12, data=(0,), uses=(1,)),
                    I('call', 12, data=(1,), uses=(2,)), I('store', data=(0,), uses=(3,)), I('load', 12, data=(0,)),
                    I('case', data=(0, 1, 2, 0), uses=(5,))]),
              ([10], [I('field', 1, data=(0,), uses=(0,)), I('print', uses=(1,)), *done(3)]),
              ([], [I('trap', data=(4,))])]
    text = f.module([], blocks=blocks, shapes=S, slots=(12,))
    callee = f.function(12, (12,), [0], (12,)) + '\nblock 1 12 3\n' + '\n'.join([
        I('store', data=(0,), uses=(0,)), I('load', 12, data=(0,)), I('return', uses=(2,))]) + '\n'
    yield 'enum-call-slot-result', text.replace('functions 1', 'functions 2').replace('end\n', callee+'end\n'), '42\n'
    # A taken self-edge swaps explicit operands before re-entering. The second
    # case takes the no edge; both edges must stage copies before writes.
    shapes = [('struct', (1,)), ('enum', (10, 10))]
    blocks = [([], [I('const', 1, data=(1,)), I('const', 1, data=(2,)), I('struct', 10, uses=(0,)),
                    I('enum', 11, data=(0,), uses=(2,)), I('jump', data=(1,), uses=(2, 3, 0, 1))]),
              ([10, 11, 1, 1], [I('enum', 11, data=(1,), uses=(0,)),
                                I('case', data=(0, 1, 2, 3), uses=(1, 4, 3, 2, 2, 3))]),
              ([1, 1], [I('print', uses=(0,)), I('print', uses=(1,)), *done(4)])]
    yield 'enum-parallel-copy', f.module([], blocks=blocks, shapes=shapes), '2\n1\n'


def cases():
    for name, text, _ in fixtures():
        yield name, text, None
    base = next(fixtures())[1]
    construct = I('enum', 12, data=(0,), uses=(1,))
    case = I('case', data=(1, 1, 2, 0), uses=(2, 2))
    for name, old, new, error in [
        ('payload-scalar', 'enum 2 10 11', 'enum 2 1 11', 'FIR_TYPE'),
        ('payload-enum', 'enum 2 10 11', 'enum 2 12 11', 'FIR_TYPE'),
        ('empty-enum', 'enum 2 10 11', 'enum 0', 'FIR_TYPE'),
        ('unknown-kind', 'enum 2 10 11', 'union 2 10 11', 'FIR_TYPE'),
        ('negative-tag', construct, I('enum', 12, data=(-1,), uses=(1,)), 'FIR_TYPE'),
        ('high-tag', construct, I('enum', 12, data=(2,), uses=(1,)), 'FIR_TYPE'),
        ('wrong-payload', construct, I('enum', 12, data=(1,), uses=(1,)), 'FIR_TYPE'),
        ('enum-on-struct', construct, I('enum', 10, data=(0,), uses=(1,)), 'FIR_TYPE'),
        ('struct-on-enum', construct, I('struct', 12, uses=(1,)), 'FIR_TYPE'),
        ('enum-arity', construct, I('enum', 12, data=(0,), uses=()), 'FIR_ARITY'),
        ('case-negative-tag', case, I('case', data=(-1, 1, 2, 0), uses=(2, 2)), 'FIR_TYPE'),
        ('case-high-tag', case, I('case', data=(2, 1, 2, 0), uses=(2, 2)), 'FIR_TYPE'),
        ('case-target', case, I('case', data=(1, 99, 2, 0), uses=(2, 2)), 'FIR_BRANCH'),
        ('case-no-target', case, I('case', data=(1, 1, 99, 0), uses=(2, 2)), 'FIR_BRANCH'),
        ('case-partition', case, I('case', data=(1, 1, 2, 3), uses=(2, 2)), 'FIR_BRANCH'),
        ('case-negative-partition', case, I('case', data=(1, 1, 2, -1), uses=(2, 2)), 'FIR_BRANCH'),
        ('case-arity', case, I('case', data=(1, 1, 2), uses=(2, 2)), 'FIR_BRANCH'),
        ('case-missing-scrutinee', case, I('case', data=(1, 1, 2, 0)), 'FIR_BRANCH'),
        ('case-scalar', case, I('case', data=(1, 1, 2, 0), uses=(0, 2)), 'FIR_TYPE'),
        ('case-wrong-implicit', 'block 1 11 4', 'block 1 10 4', 'FIR_BRANCH'),
        ('case-missing-implicit', 'block 1 11 4', 'block 0 4', 'FIR_BRANCH'),
        ('case-no-args', case, I('case', data=(1, 1, 2, 0), uses=(2,)), 'FIR_BRANCH'),
        ('case-no-type', case, I('case', data=(1, 1, 2, 0), uses=(2, 0)), 'FIR_BRANCH'),
        ('case-dominance', case, I('case', data=(1, 1, 2, 0), uses=(2, 9)), 'FIR_DOMINANCE'),
    ]:
        assert old in base, name
        yield 'reject-enum-'+name, base.replace(old, new, 1), error
    yield 'reject-enum-field', f.module([I('load', 12, data=(0,)), I('field', 10, data=(0,), uses=(0,)), *done(2)], shapes=S, slots=(12,)), 'FIR_TYPE'
    for op in ('load', 'store'):
        body = [I('const', 1, data=(1,)), I('struct', 10, uses=(0,))]
        body += [I(op, 10 if op == 'load' else 0, data=(0, 0), uses=() if op == 'load' else (1,)), *done(3)]
        yield 'reject-enum-path-'+op, f.module(body, shapes=S, slots=(12,)), 'FIR_TYPE'
    old = f.module([C, I('case', data=(0, 0, 0, 0), uses=(0,))])
    yield 'reject-case-edition1', old, 'FIR_SYNTAX'
    yield 'reject-enum-edition1', f.module([I('enum', 10, data=(0,), uses=(0,)), *done(1)], structs=[()]), 'FIR_SYNTAX'
    # An enum-free edition 2 canonicalizes back to the old bytes.
    yield 'enum-free-edition2', f.module(done(), shapes=[]), None


def limits(memory=512 << 20, cpu=30):
    def apply():
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    return apply


def run(argv, memory=512 << 20, cpu=30, timeout=60, **kw):
    opts = {'preexec_fn': limits(memory, cpu)} if sys.platform == 'linux' else {}
    return subprocess.run([str(x) for x in argv], capture_output=True, timeout=timeout, **opts, **kw)


def build(work, name):
    source = work / name
    source.mkdir(parents=True, exist_ok=True)
    for module in ('fir', 'sem', 'interp', 'x86'):
        shutil.copytree(ROOT/'src'/module, source/module, dirs_exist_ok=True)
    shutil.copyfile(ROOT/'tests/backend'/f'{name}.lu', source/'main.lu')
    binary = source/'consumer'
    env = dict(os.environ, WOLF_STD=str(ROOT/'.wolf-bin/std'), WOLF_RT_LIB=str(ROOT/'.wolf-bin/libwolf_rt.a'))
    p = run([ROOT/'.wolf-bin/wolf', 'build', '--no-cache', '--deny-warnings', source/'main.lu', '-o', binary], memory=6 << 30, cpu=180, timeout=240, env=env)
    if p.returncode:
        print(f'FAIL {name}-build status={p.returncode}\n{p.stderr.decode(errors="replace")}', flush=True)
        raise SystemExit(1)
    return binary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--compiler', type=Path)
    ap.add_argument('--api-only', action='store_true')
    ap.add_argument('--native', action='store_true')
    a = ap.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.api_only:
        binary = build(a.out, 'enum_api')
        p = run([binary])
        assert (p.returncode, p.stdout, p.stderr) == (0, b'enum api: ok\n', b''), (p.returncode, p.stdout, p.stderr)
        print('PASS enum-api-verifier-budgets')
        return
    compiler = a.compiler.resolve() if a.compiler else build(a.out, 'enum_driver')
    env = dict(os.environ, FENRIR_TOOLCHAIN=str(ROOT/'.wolf-bin'))
    for name, text, error in cases():
        src, out = a.out/(name+'.fir'), a.out/(name+'.canonical')
        src.write_text(text)
        out.write_text('sentinel')
        p = run([compiler, 'fir', src, '-o', out])
        try:
            if error:
                assert p.returncode == 2 and error.encode() in p.stderr and out.read_text() == 'sentinel', (p.returncode, p.stderr)
            else:
                assert p.returncode == 0, (p.returncode, p.stderr)
                again = a.out/'again.fir'
                q = run([compiler, 'fir', out, '-o', again])
                assert q.returncode == 0 and again.read_bytes() == out.read_bytes()
                assert out.read_text().startswith('fir 1\n' if name == 'enum-free-edition2' else 'fir 2\n')
        except AssertionError:
            print('FAIL '+name, flush=True)
            raise
        print('PASS '+name, flush=True)
    for name, text, expected in fixtures():
        src, report = a.out/(name+'.fir'), a.out/(name+'.outcome')
        p = run([compiler, 'interpret', src, '--steps', '1000', '--bytes', str(1 << 20), '--report', report])
        assert (p.returncode, p.stdout, p.stderr, report.read_text()) == (0, expected.encode(), b'', 'exit 0\n'), (name, p.returncode, p.stdout, p.stderr)
        print('PASS interpret-'+name, flush=True)
        assembly = a.out/(name+'.s')
        q = run([compiler, 'asm', src, '-o', assembly])
        assert q.returncode == 0, (name, q.stderr)
        first = assembly.read_bytes()
        q = run([compiler, 'asm', src, '-o', assembly])
        assert q.returncode == 0 and assembly.read_bytes() == first
        if a.native:
            assert sys.platform == 'linux', 'native proof requires Linux'
            binary = a.out/(name+'.exe')
            q = run([compiler, 'link', src, '-o', binary], memory=2 << 30, cpu=180, timeout=240, env=env)
            assert q.returncode == 0, (name, q.stderr)
            q = run([binary])
            (a.out/(name+'.native.stdout')).write_bytes(q.stdout)
            (a.out/(name+'.native.stderr')).write_bytes(q.stderr)
            if (p.returncode, p.stdout, p.stderr) != (q.returncode, q.stdout, q.stderr):
                print('FAIL enum-differential-'+name+' differs STOP', flush=True)
                raise SystemExit(1)
            print('PASS native-'+name, flush=True)


if __name__ == '__main__':
    main()
