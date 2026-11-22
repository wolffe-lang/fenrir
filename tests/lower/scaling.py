#!/usr/bin/env python3
"""Run only under a Linux memory/CPU cap: the lowering at N, 10N and 100N.

Six inputs grow: many small functions, one function with many statements
(splits, slots and loops are function-local, so either shape must stay linear),
one function whose deferred statements each precede an early return: every
return leaves through all the defers before it, so lowering that copied the
deferred statements to each exit would grow with their product; and the two
value-result shapes ([mem.tier0.mode.mut]): many `mut` calls in one function
(each call's write-backs are its own, so a call costs the same however many
precede it), and many functions with `mut` parameters and early returns (each
return path packs the parameters' final values once); and a struct of n/60 words passed `mut`
n/60 times (tests/backend/copy_width.py), whose x86-64 text is measured too: a copy that wrote one
pair of moves per word grew as width times copies, and the assembler could not hold the result.
Time is the child's own CPU time (user plus system, from its rusage). Every
size runs ROUNDS times, the sizes interleaved round by round, and the minimum
stands; a tenfold step may take at most 18 times the smaller size, whose time
counts as at least FLOOR seconds, and emit at most 12 times its bytes.
"""
import argparse
import json
import os
from pathlib import Path
import importlib.util
import subprocess
import time

ROUNDS = 5
FLOOR = 0.05

STATEMENTS = '''    var a{i}: int = {i}
    a{i} += side(a{i}) * 2
    if a{i} > 3 && a{i} < 1000000 {{ a{i} -= 1 }} else {{ a{i} += 1 }}
    while a{i} % 7 != 0 {{ a{i} += 1 }}
    let p{i} = P {{ x: a{i}, s: "v{i}" }}
    total += p{i}.x
'''


def many_functions(n):
    out = ["struct P { x: int, s: str }", "fn side(x: int) -> int { x + 1 }"]
    for i in range(n // 6):
        out.append(f"fn f{i}(seed: int) -> int {{\n    var total: int = seed\n" + STATEMENTS.format(i=0) + "    total\n}")
    calls = " + ".join(f"f{i}({i})" for i in range(min(n // 6, 50)))
    out.append(f'fn main() {{ print("{{{calls}}}") }}')
    return "\n".join(out) + "\n"


def one_function(n):
    body = "".join(STATEMENTS.format(i=i) for i in range(n // 6))
    return ("struct P { x: int, s: str }\nfn side(x: int) -> int { x + 1 }\n"
            f"fn main() {{\n    var total: int = 0\n{body}    print(\"{{total}}\")\n}}\n")


DEFERRED = '''    defer print_raw("d{i} ")
    if side(total) == {i} {{ return }}
    total += 1
'''


def deferred_returns(n):
    body = "".join(DEFERRED.format(i=i) for i in range(n // 6))
    return ("fn side(x: int) -> int { x - 1 }\n"
            f"fn main() {{\n    var total: int = 0\n{body}    print(\"{{total}}\")\n}}\n")


MUT_CALLS = '''    var c{i} = C {{ n: {i}, vs: [{i}] }}
    bump(mut c{i}.n, {i})
    bump(mut xs[{k}], 1)
    total += swap(mut c{i}, mut d)
    total += c{i}.n + xs[{k}]
'''


def mut_calls(n):
    body = "".join(MUT_CALLS.format(i=i, k=i % 3) for i in range(n // 6))
    return ("struct C { n: int, vs: List[int] }\nfn bump(mut a: int, by: int) { a += by }\n"
            "fn swap(mut a: C, mut b: C) -> int {\n    let t = a.n\n    a.n = b.n\n    b.n = t\n    t\n}\n"
            "fn main() {\n    var total: int = 0\n    var xs = [0, 0, 0]\n    var d = C { n: 0, vs: [0] }\n"
            f"{body}    print(\"{{total}}\")\n}}\n")


def mut_functions(n):
    out = []
    for i in range(n // 6):
        out.append(f"fn m{i}(mut a: int, mut b: List[int], k: int) -> int {{\n    if k == {i} {{ return a }}\n"
                   f"    a += k\n    (mut b).push(k)\n    if a > 1000000 {{ return 0 }}\n    a\n}}")
    calls = "\n".join(f"    total += m{i}(mut a, mut b, {i + 1})" for i in range(min(n // 6, 50)))
    out.append(f"fn main() {{\n    var total: int = 0\n    var a: int = 1\n    var b = [0]\n{calls}\n"
               "    print(\"{total} {a} {b.len}\")\n}")
    return "\n".join(out) + "\n"


def wide(n):
    spec = importlib.util.spec_from_file_location("copy_width", Path(__file__).resolve().parents[1] / "backend" / "copy_width.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.wide_copies(max(1, n // 60))


# Shapes whose assembly is measured as well as their FIR.
ASSEMBLY = ("wide-copies",)


def measured(argv, out_path):
    before = time.monotonic()
    with out_path.open("wb") as stdout:
        child = subprocess.Popen(argv, stdout=stdout, stderr=subprocess.PIPE)
        while True:
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                code = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - before > 180:
                child.kill()  # this child PID only, never a process group
                os.wait4(child.pid, 0)
                raise AssertionError("scaling child exceeded 180 seconds")
            time.sleep(0.01)
    err = child.stderr.read()
    assert code == 0, (code, err[:400])
    return usage.ru_utime + usage.ru_stime, usage.ru_maxrss * 1024


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("compiler", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base", type=int, default=600)
    a = ap.parse_args()
    assert os.uname().sysname == "Linux", "scaling requires a capped Linux job"
    a.out.mkdir(parents=True, exist_ok=True)
    points = [(shape, make, n) for shape, make in (("functions", many_functions), ("statements", one_function),
                                                   ("defers", deferred_returns), ("mut-calls", mut_calls),
                                                   ("mut-functions", mut_functions), ("wide-copies", wide))
              for n in (a.base, 10 * a.base, 100 * a.base)]
    for shape, make, n in points:
        # Every `.lu` file in a directory joins its module, so each program
        # gets a directory of its own and stays a one-file program.
        folder = a.out / f"{shape}-n{n}"
        folder.mkdir(exist_ok=True)
        (folder / "main.lu").write_text(make(n))
    seconds, peaks = {}, {}
    for _ in range(ROUNDS):
        for shape, _, n in points:
            folder = a.out / f"{shape}-n{n}"
            cpu, peak = measured([str(a.compiler.resolve()), "--emit=fir", str(folder / "main.lu")], folder / "main.fir")
            seconds.setdefault((shape, n), []).append(cpu)
            peaks.setdefault((shape, n), []).append(peak)
            if shape in ASSEMBLY:
                cpu, peak = measured([str(a.compiler.resolve()), "--emit=asm", str(folder / "main.lu")], folder / "main.s")
                seconds.setdefault((shape, n, "asm"), []).append(cpu)
                peaks.setdefault((shape, n, "asm"), []).append(peak)
    report = []
    for shape, _, n in points:
        folder = a.out / f"{shape}-n{n}"
        row = {"shape": shape, "n": n, "source_bytes": (folder / "main.lu").stat().st_size, "fir_bytes": (folder / "main.fir").stat().st_size,
               "seconds": min(seconds[shape, n]), "seconds_runs": seconds[shape, n], "child_peak_bytes": max(peaks[shape, n])}
        if shape in ASSEMBLY:
            row.update(asm_bytes=(folder / "main.s").stat().st_size, asm_seconds=min(seconds[shape, n, "asm"]),
                       asm_seconds_runs=seconds[shape, n, "asm"], asm_child_peak_bytes=max(peaks[shape, n, "asm"]))
        report.append(row)
        print("SCALING " + json.dumps(row, sort_keys=True), flush=True)
    for prev, row in zip(report, report[1:]):
        if prev["shape"] != row["shape"]:
            continue
        allowed = 18 * max(prev["seconds"], FLOOR)
        assert row["seconds"] <= allowed, ("superlinear-time", row["shape"], prev["n"], row["n"], prev["seconds"], row["seconds"], allowed)
        assert row["fir_bytes"] <= 12 * prev["fir_bytes"], ("superlinear-output", prev, row)
        if row["shape"] in ASSEMBLY:
            allowed = 18 * max(prev["asm_seconds"], FLOOR)
            assert row["asm_seconds"] <= allowed, ("superlinear-assembly-time", row["shape"], prev["n"], row["n"], prev["asm_seconds"], row["asm_seconds"], allowed)
            assert row["asm_bytes"] <= 12 * prev["asm_bytes"], ("superlinear-assembly", prev, row)
    (a.out / "scaling.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS scaling-lowering", flush=True)


if __name__ == "__main__":
    main()
