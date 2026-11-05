#!/usr/bin/env python3
"""Executable FIR parity and bounded-interpreter refusals, red before execution.

smoke runs only finite, small fixtures (also on macOS). linux adds deliberately
unbounded programs under independent address-space and CPU hard limits. The
outcome file distinguishes a program returning 4 from a tool refusing with 4.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


HERE = Path(__file__).resolve().parent
assembly = load('interpreter_assembly_rows', HERE / 'assembly.py')
f = load('interpreter_fir_rows', HERE / 'fir.py')
I = f.inst
measurement = load('interpreter_child_measurement', HERE / 'link_budget.py')


def cases(mode):
    for name, text, expected in assembly.fixtures():
        trap = expected.removeprefix('trap:') if expected.startswith('trap:') else None
        if trap:
            yield name, text, 100000, 64 << 20, 134, b'', f'wolf-trap: {trap}\n  at proof.lu:1:1\n'.encode(), f'trap {trap}\n'
        else:
            yield name, text, 100000, 64 << 20, 0, expected.encode(), b'', 'exit 0\n'
    returning_four = f.module([I('const', 1, data=(4,)), I('return', uses=(0,))])
    yield 'program-exit-four', returning_four, 2, 1 << 20, 4, b'', b'', 'exit 4\n'
    yield 'negative-budget', returning_four, -1, 1 << 20, 2, b'', b'FIR_LIMIT', None
    yield 'missing-input', None, 10, 1 << 20, 2, b'', b'FIR_IO', None
    uninitialized = f.module([I('load', 1, data=(0,)), I('return', uses=(0,))], slots=(1,))
    yield 'uninitialized-slot', uninitialized, 10, 1 << 20, 2, b'', b'FIR_STATE', None
    printed = f.module([I('string', 3, data=(1,)), I('print', uses=(0,)),
                        I('const', 1, data=(0,)), I('return', uses=(2,))])
    yield 'output-before-refusal', printed, 2, 1 << 20, 4, b'hello, wolf\n', b'FIR_STEP_BUDGET', 'refused FIR_STEP_BUDGET\n'
    yield 'step-limit', returning_four, 1, 1 << 20, 4, b'', b'FIR_STEP_BUDGET', 'refused FIR_STEP_BUDGET\n'
    yield 'memory-limit', returning_four, 10, 0, 4, b'', b'FIR_MEMORY_BUDGET', 'refused FIR_MEMORY_BUDGET\n'
    trap = f.module([I('trap', data=(1,))])
    yield 'trap-before-budget', trap, 1, 1 << 20, 134, b'', b'wolf-trap: overflow\n  at proof.lu:1:1\n', 'trap overflow\n'
    yield 'budget-before-trap', trap, 0, 1 << 20, 4, b'', b'FIR_STEP_BUDGET', 'refused FIR_STEP_BUDGET\n'
    for name, text, tag in f.cases():
        if tag:
            yield name, text, 100000, 64 << 20, 2, b'', tag.encode(), None
    if mode == 'linux':
        yield 'bounded-stream-input', 'x' * 1025, 10, 1024, 4, b'', b'FIR_MEMORY_BUDGET', 'refused FIR_MEMORY_BUDGET\n'
        spin = f.module([], blocks=[
            ([], [I('string', 3, data=(1,)), I('print', uses=(0,)), I('jump', data=(1,))]),
            ([], [I('jump', data=(1,))])])
        yield 'bounded-spin', spin, 100, 1 << 20, 4, b'hello, wolf\n', b'FIR_STEP_BUDGET', 'refused FIR_STEP_BUDGET\n'
        recur = f.module([I('string', 3, data=(1,)), I('print', uses=(0,)), I('call', 1, data=(1,)), I('return', uses=(2,))])
        callee = f.function(1, (), [0]) + '\nblock 0 2\n' + I('call', 1, data=(1,)) + '\n' + I('return', uses=(0,)) + '\n'
        recur = recur.replace('functions 1', 'functions 2').replace('end\n', callee + 'end\n')
        yield 'bounded-recursion', recur, 100000, 8192, 4, b'hello, wolf\n', b'FIR_MEMORY_BUDGET', 'refused FIR_MEMORY_BUDGET\n'
        growing = f.module([], slots=(3,), blocks=[
            ([], [I('string', 3, data=(1,)), I('print', uses=(0,)), I('store', data=(0,), uses=(0,)), I('jump', data=(1,))]),
            ([], [I('load', 3, data=(0,)), I('concat', 3, uses=(0, 0)),
                  I('store', data=(0,), uses=(1,)), I('jump', data=(1,))])])
        yield 'bounded-string-growth', growing, 100000, 8192, 4, b'hello, wolf\n', b'FIR_MEMORY_BUDGET', 'refused FIR_MEMORY_BUDGET\n'
        flat = f.module([], blocks=[
            ([], [I('string', 3, data=(1,)), I('jump', data=(1,), uses=(0,))]),
            ([3], [I('eq', 2, uses=(0, 0)), I('jump', data=(1,), uses=(0,))])])
        flat = flat.replace('blob 68656c6c6f2c20776f6c66', 'blob ' + (b'x' * 32768).hex())
        for steps in (1000, 10000, 100000):
            yield f'nonallocating-string-loop-{steps}', flat, steps, 256 << 10, 4, b'', b'FIR_STEP_BUDGET', 'refused FIR_STEP_BUDGET\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mode', choices=('smoke', 'linux'), default='smoke')
    a = p.parse_args()
    if a.mode == 'linux' and sys.platform != 'linux':
        raise SystemExit('Linux hard caps required for resource-growth rows; not a skip')
    a.out.mkdir(parents=True, exist_ok=True)
    take = Path(tempfile.mkdtemp(prefix='take-', dir=a.out.resolve()))
    observations = []
    for name, text, steps, memory, status, stdout, stderr, report in cases(a.mode):
        folder = take / name
        folder.mkdir()
        source, outcome = folder / 'program.fir', folder / 'outcome.txt'
        writer = None
        if name == 'bounded-stream-input':
            os.mkfifo(source)
            writer = subprocess.Popen([sys.executable, '-I', '-c',
                'import sys; f=open(sys.argv[1], "wb"); f.write(sys.argv[2].encode()); f.close()',
                str(source), text], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif text is not None:
            source.write_text(text)
        # Rejection must preserve an existing report, never fabricate completion.
        if report is None:
            outcome.write_text('preserve\n')
        argv = [str(a.binary.resolve()), 'interpret', str(source), '--steps', str(steps),
                '--bytes', str(memory), '--report', str(outcome)]
        try:
            metrics = None
            if sys.platform == 'linux':
                metrics = measurement.measured(argv, dict(os.environ), folder / 'process',
                                               limit=512 << 20, timeout=15, cpu=10)
                if metrics['timeout']:
                    raise subprocess.TimeoutExpired(argv, 15)
                result = subprocess.CompletedProcess(argv, metrics['exit'],
                    (folder / 'process.stdout').read_bytes(), (folder / 'process.stderr').read_bytes())
            else:
                result = subprocess.run(argv, capture_output=True, timeout=15)
            (folder / 'stdout').write_bytes(result.stdout)
            (folder / 'stderr').write_bytes(result.stderr)
            actual_report = outcome.read_text() if outcome.is_file() else None
            same = result.returncode == status and result.stdout == stdout
            if report and report.startswith('refused '):
                same &= stderr in result.stderr and b'wolf-trap:' not in result.stderr
            elif report is None:
                same &= stderr in result.stderr
            else:
                same &= result.stderr == stderr
            same &= actual_report == (report if report is not None else 'preserve\n')
            if name.startswith('nonallocating-string-loop-'):
                # A generous fixed allowance covers the runtime and fixed input;
                # retaining a 32 KiB copy per step must fail well before 100N.
                same &= metrics['child_peak_rss_bytes'] < 64 << 20
            row = dict(name=name, passed=bool(same), exit=result.returncode, report=actual_report)
            if metrics is not None:
                row.update(child_peak_rss_bytes=metrics['child_peak_rss_bytes'],
                           child_cpu_seconds=metrics['child_cpu_seconds'])
        except subprocess.TimeoutExpired:
            row = dict(name=name, passed=False, timeout=True)
        finally:
            if writer is not None:
                try:
                    writer.communicate(timeout=3)
                    if writer.returncode:
                        row = dict(name=name, passed=False, writer_exit=writer.returncode)
                except subprocess.TimeoutExpired:
                    writer.kill()  # Only this row's writer, reaped immediately.
                    writer.communicate()
                    row = dict(name=name, passed=False, writer_timeout=True)
                source.unlink(missing_ok=True)
                (folder / 'stream.input').write_text(text)
        observations.append(row)
        print(('PASS ' if row['passed'] else 'FAIL ') + 'interpreter-' + name + ' ' + json.dumps(row), flush=True)
    (take / 'results.json').write_text(json.dumps(observations, indent=2) + '\n')
    return int(any(not row['passed'] for row in observations))


if __name__ == '__main__':
    raise SystemExit(main())
