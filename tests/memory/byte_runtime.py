#!/usr/bin/env -S python3 -I
"""Compile the owned C caller to assembly, assemble with clef and link pinned musl.

No system assembler/linker fallback, host-libc linkage, header inspection or new
runtime entry is involved. This is a runtime-boundary witness, not a compiler
performance measurement or a source-language parity row.
"""
import argparse
import os
from pathlib import Path
import resource
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def capped():
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    a = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('linked musl witness requires Linux, not a skip')
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    home = out / 'home'
    home.mkdir(exist_ok=True)
    stage = ROOT / '.wolf-bin'
    env = dict(os.environ, HOME=str(home), SHELL='/bin/sh',
               LIGATURE_SYSROOT=str(stage / 'bundle/sysroot'))
    asm, obj, exe = (out / name for name in ('probe.s', 'probe.o', 'probe'))
    commands = [
        ['cc', '-S', '-m64', '-std=c11', '-O2', '-ffreestanding', '-fno-stack-protector',
         '-fno-pie', '-fno-pic', '-fno-asynchronous-unwind-tables', '-fno-unwind-tables',
         '-fno-tree-vectorize', '-fno-ident', str(ROOT / 'tests/memory/byte_runtime.c'), '-o', str(asm)],
        [str(stage / 'bin/clef'), '--64', '-o', str(obj), str(asm)],
        [str(stage / 'bin/ligature'), '-o', str(exe), str(obj), str(stage / 'musl/libwolf_rt.a'),
         '-lpthread', '-ldl', '-lm', '-Wl,--gc-sections'],
        [str(stage / 'bin/ligature'), 'verify', str(exe)],
    ]
    for index, command in enumerate(commands):
        p = subprocess.run(command, cwd=out, env=env, capture_output=True, timeout=120, preexec_fn=capped)
        if p.returncode:
            print(f'FAIL byte-runtime-boundary-stage-{index} exit={p.returncode} stderr={p.stderr[:400]!r}', flush=True)
            return 1
    p = subprocess.run([str(exe)], cwd=out, env=env, capture_output=True, timeout=30, preexec_fn=capped)
    ok = p.returncode == 0 and p.stdout == b'byte-runtime-ok\n' and p.stderr == b''
    print(('PASS' if ok else 'FAIL') + f' byte-runtime-boundary exit={p.returncode} stdout={p.stdout!r} stderr={p.stderr[:240]!r}', flush=True)
    return int(not ok)


if __name__ == '__main__':
    raise SystemExit(main())
