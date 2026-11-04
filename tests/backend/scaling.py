#!/usr/bin/env python3
"""Run only under a Linux memory/CPU cap: N, 10N, 100N time/byte rows."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

spec = importlib.util.spec_from_file_location("fir_rows", Path(__file__).with_name("fir.py"))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def source(n):
    code = [f.inst("const", 1, data=(i,)) for i in range(n)]
    code.append(f.inst("return", uses=(n - 1,)))
    return f.module(code)


def measured(argv, errors):
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
    return time.monotonic() - before, usage.ru_maxrss * 1024


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("compiler", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base", type=int, default=1000)
    a = ap.parse_args()
    assert os.uname().sysname == "Linux", "scaling requires a capped Linux job"
    assert a.base >= 100
    a.out.mkdir(parents=True, exist_ok=True)
    report = []
    for n in [a.base, 10 * a.base, 100 * a.base]:
        src = a.out / f"n{n}.fir"
        src.write_text(source(n))
        row = {"n": n, "input_bytes": src.stat().st_size}
        for mode in ["fir", "asm"]:
            elapsed = []
            rss = []
            dest = a.out / f"n{n}.{mode}.out"
            for repetition in range(3):
                seconds, peak = measured([str(a.compiler.resolve()), mode, str(src), "-o", str(dest)], a.out / f"n{n}.{mode}.{repetition}.stderr")
                elapsed.append(seconds)
                rss.append(peak)
            row[mode + "_seconds"] = statistics.median(elapsed)
            row[mode + "_child_peak_bytes"] = max(rss)
            row[mode + "_child_bytes_per_instruction"] = max(rss) / n
            row[mode + "_bytes"] = dest.stat().st_size
        report.append(row)
        print("SCALING " + json.dumps(row, sort_keys=True), flush=True)
    for mode in ["fir", "asm"]:
        for prev, row in zip(report, report[1:]):
            assert row[mode + "_seconds"] <= 18 * prev[mode + "_seconds"], ("superlinear-time", mode, prev, row)
            assert row[mode + "_bytes"] <= 12 * prev[mode + "_bytes"], ("superlinear-output", mode, prev, row)
    (a.out / "scaling.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS scaling-parser-verifier-printer-allocator-emitter", flush=True)


if __name__ == "__main__":
    main()
