#!/usr/bin/env python3
"""Run only under a Linux memory/CPU cap: N, 10N, 100N time/byte rows.

Time is the child's own CPU time (user plus system, from its rusage), not wall
time, so neither the wait loop's poll nor time spent waiting for a core counts.
Every point runs ROUNDS times, the sizes interleaved round by round so a slow
spell of the host falls on all of them, and the minimum stands. Each tenfold
step may take at most 18 times the smaller point, and a smaller point under
FLOOR seconds counts as FLOOR: below it a point is process start and timer
grain, not the code's growth.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

ROUNDS = 5
FLOOR = 0.05

spec = importlib.util.spec_from_file_location("fir_rows", Path(__file__).with_name("fir.py"))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def source(n):
    code = [f.inst("const", 1, data=(i,)) for i in range(n)]
    code.append(f.inst("return", uses=(n - 1,)))
    return f.module(code)


def grown(n):
    """FIR 1 forms at scale: u64 arithmetic, a slot path store/load, format."""
    code = [f.inst("const", f.U64, data=(1,))]
    for i in range(n // 4):
        at = len(code)
        code += [f.inst("add", f.U64, uses=(at - 1, 0)), f.inst("store", data=(0, 1), uses=(at,)),
                 f.inst("load", f.U64, data=(0, 1)), f.inst("format", f.STR, uses=(at + 2, at + 2))]
        code.append(f.inst("load", f.U64, data=(0, 1)))
    code += [f.inst("const", 1, data=(0,)), f.inst("return", uses=(len(code),))]
    return f.module(code, structs=[(f.BOOL, f.U64)], slots=(f.STRUCT,))


def measured(argv, errors):
    """One run: the child's CPU seconds and its peak resident bytes."""
    before = time.monotonic()
    with errors.open("wb") as stderr:
        child = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=stderr)
        while True:
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                child.returncode = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - before > 180:
                child.kill()  # this child PID only, never a process group
                _, status, usage = os.wait4(child.pid, 0)
                child.returncode = os.waitstatus_to_exitcode(status)
                raise AssertionError("scaling child exceeded 180 seconds")
            time.sleep(0.01)
    assert child.returncode == 0, (child.returncode, errors.read_text())
    return usage.ru_utime + usage.ru_stime, usage.ru_maxrss * 1024


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("compiler", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base", type=int, default=10000)
    a = ap.parse_args()
    assert os.uname().sysname == "Linux", "scaling requires a capped Linux job"
    assert a.base >= 100
    a.out.mkdir(parents=True, exist_ok=True)
    points = [(scale * a.base, kind) for kind in ("const", "grown") for scale in (1, 10, 100)]
    seconds, rss = {}, {}
    for n, kind in points:
        (a.out / f"{kind}-n{n}.fir").write_text(source(n) if kind == "const" else grown(n))
    for repetition in range(ROUNDS):
        for n, kind in points:
            for mode in ["fir", "asm"]:
                src, dest = a.out / f"{kind}-n{n}.fir", a.out / f"{kind}-n{n}.{mode}.out"
                cpu, peak = measured([str(a.compiler.resolve()), mode, str(src), "-o", str(dest)], a.out / f"{kind}-n{n}.{mode}.{repetition}.stderr")
                seconds.setdefault((kind, n, mode), []).append(cpu)
                rss.setdefault((kind, n, mode), []).append(peak)
    report = []
    for n, kind in points:
        row = {"n": n, "kind": kind, "input_bytes": (a.out / f"{kind}-n{n}.fir").stat().st_size}
        for mode in ["fir", "asm"]:
            row[mode + "_seconds"] = min(seconds[kind, n, mode])
            row[mode + "_seconds_runs"] = seconds[kind, n, mode]
            row[mode + "_child_peak_bytes"] = max(rss[kind, n, mode])
            row[mode + "_child_bytes_per_instruction"] = max(rss[kind, n, mode]) / n
            row[mode + "_bytes"] = (a.out / f"{kind}-n{n}.{mode}.out").stat().st_size
        report.append(row)
        print("SCALING " + json.dumps(row, sort_keys=True), flush=True)
    for mode in ["fir", "asm"]:
        for prev, row in zip(report, report[1:]):
            if prev["kind"] != row["kind"]:
                continue
            allowed = 18 * max(prev[mode + "_seconds"], FLOOR)
            assert row[mode + "_seconds"] <= allowed, ("superlinear-time", mode, row["kind"], prev["n"], row["n"], prev[mode + "_seconds"], row[mode + "_seconds"], allowed)
            assert row[mode + "_bytes"] <= 12 * prev[mode + "_bytes"], ("superlinear-output", mode, prev, row)
    (a.out / "scaling.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS scaling-parser-verifier-printer-allocator-emitter", flush=True)


if __name__ == "__main__":
    main()
