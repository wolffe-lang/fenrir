#!/usr/bin/env python3
"""Oracle preflight: every FIR fixture's Wolf twin runs under the pinned wolf
on this host and shows the fixture's expected stdout or trap kind.

It runs before any Linux take, on macOS and Linux alike, so a wrong expected
value or a twin the reference refuses is found where it is cheap. The Linux
differential then compares the linked FIR program with the twin byte for byte.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    root = a.root.resolve()
    tools = root / ".wolf-bin"
    here = Path(__file__).resolve().parent
    rows = load("assembly_rows", here / "assembly.py")
    linux = load("linux_rows", here / "linux.py")
    env = dict(os.environ, WOLF_STD=str(tools / "std"), WOLF_RT_LIB=str(tools / "libwolf_rt.a"))
    a.out.mkdir(parents=True, exist_ok=True)
    failed = 0
    for name, _, expected in rows.fixtures():
        folder = (a.out / name).resolve()
        folder.mkdir(exist_ok=True)
        src = folder / "proof.lu"
        src.write_text(linux.wolf_source(name))
        program = folder / "oracle"
        built = subprocess.run([str(tools / "wolf"), "build", "--no-cache", str(src), "-o", str(program)], capture_output=True, env=env, timeout=180)
        if built.returncode:
            print(f"FAIL preflight-{name} oracle build status={built.returncode} {built.stderr.decode(errors='replace').strip()[:400]}", flush=True)
            failed += 1
            continue
        ran = subprocess.run([str(program)], capture_output=True, timeout=60)
        if expected.startswith("trap:"):
            first = ran.stderr.splitlines()[:1]
            good = ran.returncode == 134 and first == [("wolf-trap: " + expected[5:]).encode()]
        else:
            good = ran.returncode == 0 and ran.stdout == expected.encode()
        if good:
            print(f"PASS preflight-{name}", flush=True)
        else:
            print(f"FAIL preflight-{name} status={ran.returncode} stdout={ran.stdout[:300]!r} stderr={ran.stderr[:300]!r} expected={expected[:300]!r}", flush=True)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
