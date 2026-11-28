#!/usr/bin/env -S python3 -I
"""Compile the owned C caller to assembly, assemble with clef and link pinned musl.

No system assembler/linker fallback, host-libc linkage, header inspection or new
runtime entry is involved. Only GCC's non-executable .file metadata is removed:
the original and edited assembly are retained and their exact diff is recorded.
This is a runtime-boundary witness, not a compiler performance measurement or
a source-language parity row.
"""
import argparse
import difflib
import hashlib
import os
from pathlib import Path
import re
import resource
import shlex
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
         '-fno-tree-vectorize', '-fno-merge-constants', '-fno-ident', str(ROOT / 'tests/memory/byte_runtime.c'), '-o', str(asm)],
        [str(stage / 'bin/clef'), '--64', '-o', str(obj), str(asm)],
        [str(stage / 'bin/ligature'), '-o', str(exe), str(obj), str(stage / 'musl/libwolf_rt.a'),
         '-lpthread', '-ldl', '-lm', '-Wl,--gc-sections'],
        [str(stage / 'bin/ligature'), 'verify', str(exe)],
    ]
    version = subprocess.run(['cc', '--version'], cwd=out, env=env, capture_output=True, timeout=30)
    if version.returncode:
        print('FAIL byte-runtime-compiler-version exit=' + str(version.returncode), flush=True)
        return 1
    print('PROBE_COMPILER_VERSION ' + version.stdout.decode(errors='replace').splitlines()[0], flush=True)
    print('PROBE_COMPILER_COMMAND ' + shlex.join(commands[0]), flush=True)
    for index, command in enumerate(commands):
        p = subprocess.run(command, cwd=out, env=env, capture_output=True, timeout=120, preexec_fn=capped)
        if p.returncode:
            print(f'FAIL byte-runtime-boundary-stage-{index} exit={p.returncode} stderr={p.stderr[:400]!r}', flush=True)
            if index == 1:
                directives = sorted(set(re.findall(r'(?m)^\s*(\.[A-Za-z][A-Za-z0-9_.]*)(?:\s|$)', asm.read_text())))
                print('OBSERVATION remaining-probe-directives ' + ','.join(directives), flush=True)
            return 1
        if index == 0:
            original = asm.read_bytes()
            raw = out / 'probe.gcc.s'
            assert not raw.exists(), 'original probe assembly already exists; use fresh --out'
            raw.write_bytes(original)
            lines = original.decode().splitlines(keepends=True)
            edited = [line for line in lines if not re.match(r'^\s*\.file(?:\s|$)', line)]
            removed = len(lines) - len(edited)
            assert removed > 0, 'expected GCC source-file metadata'
            after = ''.join(edited).encode()
            asm.write_bytes(after)
            assert asm.read_bytes() == b''.join(line.encode() for line in lines
                                                if not re.match(r'^\s*\.file(?:\s|$)', line))
            print(f'PROBE_ASSEMBLY_EDIT only=.file removed_lines={removed} '
                  + 'original_sha256=' + hashlib.sha256(original).hexdigest()
                  + ' edited_sha256=' + hashlib.sha256(after).hexdigest(), flush=True)
            print(''.join(difflib.unified_diff(lines, edited, fromfile='probe.gcc.s', tofile='probe.s')), end='', flush=True)
            directives = sorted(set(re.findall(r'(?m)^\s*(\.[A-Za-z][A-Za-z0-9_.]*)(?:\s|$)', after.decode())))
            print('PROBE_DIRECTIVES ' + ','.join(directives), flush=True)
    p = subprocess.run([str(exe)], cwd=out, env=env, capture_output=True, timeout=30, preexec_fn=capped)
    ok = p.returncode == 0 and p.stdout == b'byte-runtime-ok\n' and p.stderr == b''
    print(('PASS' if ok else 'FAIL') + f' byte-runtime-boundary exit={p.returncode} stdout={p.stdout!r} stderr={p.stderr[:240]!r}', flush=True)
    return int(not ok)


if __name__ == '__main__':
    raise SystemExit(main())
