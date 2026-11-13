#!/usr/bin/env python3
"""Source format specs lower once and render identically on both machines."""
import argparse
from pathlib import Path
import subprocess

SUITE = 'format'
PREFIX = ''
CASES = [
    ('sign-zero', 'let n = 42\n let z = 0\n let neg = 0 - 42\n print("[{n:+}][{z:+}][{neg:+}][{n:08}][{neg:06}][{n:+06}]")', '[+42][+0][-42][00000042][-00042][+00042]\n'),
    ('radix', 'let n = 42\n let neg = 0 - 42\n print("[{n:x}][{n:X}][{n:b}][{n:o}][{neg:x}]")', '[2a][2A][101010][52][-2a]\n'),
    ('alignment', 'let n = 42\n let s = "hi"\n print("[{s:8}][{n:8}][{n:*>8}][{s:^5}][{s:0>5}]")', '[hi      ][      42][******42][ hi  ][000hi]\n'),
    ('utf8-precision', 'let s = "é𝄞x"\n print("[{s:.1}][{s:.2}][{s:.5}][{s:*>8.6}]")', '[][é][é][**é𝄞]\n'),
    ('scalar-bool', 'let c = \'é\'\n let b = true\n print("[{c:^5}][{c:.1}][{b:^7}]")', '[ é  ][][ true  ]\n'),
    ('unsigned-edge', 'let n: u64 = 18446744073709551615\n let m: i64 = 0 - 9223372036854775807 - 1\n print("[{n:x}][{n:+}][{m:x}]")', '[ffffffffffffffff][+18446744073709551615][-8000000000000000]\n'),
    ('empty-spec', 'print("[{42:}][{\"wolf\":}]")', '[42][wolf]\n'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compiler', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    failed = False
    for name, body, expected in CASES:
        home = args.out / name; home.mkdir(exist_ok=True)
        source = home / 'row.lu'; source.write_text(PREFIX + 'fn main() -> int {\n ' + body + '\n 0\n}\n')
        fir = home / 'row.fir'; fir.unlink(missing_ok=True)
        lower = subprocess.run([str(args.compiler.resolve()), '--emit=fir', str(source.resolve())], capture_output=True, timeout=30)
        (home / 'lower.stderr').write_bytes(lower.stderr)
        ok = lower.returncode == 0
        if ok:
            fir.write_bytes(lower.stdout)
            report = home / 'outcome'; report.unlink(missing_ok=True)
            run = subprocess.run([str(args.compiler.resolve()), 'interpret', str(fir.resolve()), '--steps', '100000', '--bytes', '4194304', '--report', str(report.resolve())], capture_output=True, timeout=30)
            (home / 'stdout').write_bytes(run.stdout); (home / 'stderr').write_bytes(run.stderr)
            ok = (run.returncode, run.stdout, run.stderr, report.read_text() if report.exists() else '') == (0, expected.encode(), b'', 'exit 0\n')
            if args.native:
                exe = home / 'program'; exe.unlink(missing_ok=True)
                build = subprocess.run([str(args.compiler.resolve()), 'build', str(source.resolve()), '-o', str(exe.resolve())], capture_output=True, timeout=120)
                (home / 'build.stderr').write_bytes(build.stderr)
                ok &= build.returncode == 0
                if build.returncode == 0:
                    native = subprocess.run([str(exe.resolve())], capture_output=True, timeout=30)
                    (home / 'native.stdout').write_bytes(native.stdout); (home / 'native.stderr').write_bytes(native.stderr)
                    ok &= (native.returncode, native.stdout, native.stderr) == (0, expected.encode(), b'')
        print(('PASS' if ok else 'FAIL') + ' ' + SUITE + '-' + name, flush=True)
        failed |= not ok
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
