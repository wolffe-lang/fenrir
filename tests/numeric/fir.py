#!/usr/bin/env python3
"""Numeric FIR schemas and a finite cross-domain two-engine arithmetic matrix."""
import argparse
import importlib.util
import os
from pathlib import Path
import resource
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
# Every native link path runs its children under the same 2 GiB address space.
LINK_ADDRESS_SPACE = 2 << 30
spec = importlib.util.spec_from_file_location('numeric_oracle', Path(__file__).with_name('semantics.py'))
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def carrier(code):
    if code in (0, 2, 3, 20, 21):
        return 1
    if code == 1:
        return 9
    if code == 4:
        return 5
    if code == 5:
        return 6
    if code == 6:
        return 7
    if code in (7, 8, 9):
        return 8
    return 1 if oracle.KINDS[code % 10][2] else 8


def matrix():
    # One valid edge per operation/domain, and every scalar cast target from
    # a signed and unsigned source. The larger shared-semantics matrix owns
    # every ordered cast pair and trapping edges; corpus traps run separately.
    chosen = {}
    for row in oracle.cases():
        mode, source, target, a, b, value, trap = row
        if trap:
            continue
        if mode == 0:
            if source not in (0, 9):
                continue
            key = (mode, source, target)
        else:
            key = (mode, target)
        old = chosen.get(key)
        if old is None or (a != 0 and old[3] == 0) or (a != value and old[3] == old[5]):
            chosen[key] = row
    return list(chosen.values())


def program(rows):
    blocks = []
    for index, row in enumerate(rows):
        mode, source, target, a, b, value, trap = row
        assert trap == 0
        uses = [0]
        code = [f'const {carrier(source)} 0 1 {a} 0']
        if mode not in (0, 11, 12):
            code.append(f'const {carrier(source)} 0 1 {b} 0')
            uses.append(1)
        result = len(code)
        code.append(f'numeric {carrier(target)} 0 3 {mode} {source} {target} {len(uses)} ' + ' '.join(map(str, uses)))
        expected = len(code)
        code.append(f'const {carrier(target)} 0 1 {value} 0')
        condition = len(code)
        code.append(f'eq 2 0 0 2 {result} {expected}')
        code.append(f'branch 0 0 3 {2 * index + 2} {2 * index + 1} 0 1 {condition}')
        blocks.append('block 0 ' + str(len(code)) + '\n' + '\n'.join(code))
        blocks.append('block 0 1\ntrap 0 0 1 4 0')
    blocks.append('block 0 2\nconst 1 0 1 0 0\nreturn 0 0 0 1 0')
    return ('fir 5\nblobs 1\nblob ' + b'numeric-matrix.lu'.hex() + '\nsites 1\nsite 0 1 1\nshapes 0\nfunctions 1\nfunction 1 0 0 '
            + str(len(blocks)) + '\n' + '\n'.join(blocks) + '\nend\n')


def cap():
    resource.setrlimit(resource.RLIMIT_AS, (LINK_ADDRESS_SPACE, LINK_ADDRESS_SPACE))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args()
    compiler = args.compiler.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = matrix()
    text = program(rows)
    source = args.out / 'matrix.fir'
    source.write_text(text)
    canonical = args.out / 'canonical.fir'
    run = subprocess.run([str(compiler), 'fir', str(source), '-o', str(canonical)], capture_output=True, timeout=30)
    if run.returncode or canonical.read_text() != text:
        print('FAIL numeric-fir-roundtrip ' + repr((run.returncode, run.stderr)), flush=True)
        return 1
    print('PASS numeric-fir-roundtrip', flush=True)
    line = next(line for line in text.splitlines() if line.startswith('numeric '))
    fields = line.split()
    mutations = {
        'mode': (' '.join(fields[:4] + ['13'] + fields[5:]), b'FIR_TYPE'),
        'source-domain': (' '.join(fields[:5] + ['22'] + fields[6:]), b'FIR_TYPE'),
        'target-domain': (' '.join(fields[:6] + ['-1'] + fields[7:]), b'FIR_TYPE'),
        'result-carrier': (' '.join([fields[0], '3'] + fields[2:]), b'FIR_TYPE'),
        'edition': (None, b'FIR_SYNTAX'),
    }
    for name, (replacement, tag) in mutations.items():
        broken = text.replace(line, replacement, 1) if replacement is not None else text.replace('fir 5', 'fir 4', 1)
        path = args.out / (name + '.fir')
        path.write_text(broken)
        canonical.write_text('preserve\n')
        run = subprocess.run([str(compiler), 'fir', str(path), '-o', str(canonical)], capture_output=True, timeout=30)
        if run.returncode != 2 or tag not in run.stderr or canonical.read_text() != 'preserve\n':
            print('FAIL numeric-fir-reject-' + name + ' ' + repr((run.returncode, run.stderr)), flush=True)
            return 1
        print('PASS numeric-fir-reject-' + name, flush=True)
    report = args.out / 'matrix.outcome'
    report.unlink(missing_ok=True)
    run = subprocess.run([str(compiler), 'interpret', str(source), '--steps', '100000', '--bytes', '16777216',
                          '--report', str(report)], capture_output=True, timeout=30)
    if (run.returncode, run.stdout, run.stderr) != (0, b'', b'') or report.read_text() != 'exit 0\n':
        print('FAIL numeric-fir-interpreter ' + repr((run.returncode, run.stdout, run.stderr)), flush=True)
        return 1
    print('PASS numeric-fir-interpreter cases=' + str(len(rows)), flush=True)
    if args.native:
        binary = args.out / 'matrix'
        env = dict(os.environ, FENRIR_TOOLCHAIN=os.environ.get('FENRIR_TOOLCHAIN', str(ROOT / '.wolf-bin')))
        run = subprocess.run([str(compiler), 'link', str(source), '-o', str(binary)], capture_output=True, timeout=120, env=env,
                             preexec_fn=cap if sys.platform == 'linux' else None)
        if run.returncode:
            print('FAIL numeric-fir-native-build ' + repr((run.returncode, run.stderr)), flush=True)
            return 1
        run = subprocess.run([str(binary.resolve())], capture_output=True, timeout=30,
                             preexec_fn=cap if sys.platform == 'linux' else None)
        if (run.returncode, run.stdout, run.stderr) != (0, b'', b''):
            print('FAIL numeric-fir-native ' + repr((run.returncode, run.stdout, run.stderr)), flush=True)
            return 1
        print('PASS numeric-fir-native cases=' + str(len(rows)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
