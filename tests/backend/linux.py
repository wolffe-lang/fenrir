#!/usr/bin/env python3
"""Linux-only whole-file clef differential, static links and native Wolf oracle."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


rows = module("assembly_rows", Path(__file__).with_name("assembly.py"))


def wolf_source(name):
    if name == "hello": return 'fn main() { print("hello, wolf") }\n'
    if name == "bool": return 'fn main() { print(true); print(!true) }\n'
    if name == "list": return 'fn main() { var xs = List[int](); (mut xs).push(42); print(xs[0]); print(xs.len) }\n'
    if name == "list-bounds": return 'fn main() { let xs = List[int](); print(xs[-1]) }\n'
    if name == "str": return 'fn main() { let a = "hello, wolf"; print(a + a) }\n'
    if name == "while": return 'fn main() { var i: int = 0; while i < 5 { print(i); i += 1 } }\n'
    if name == "parallel-copy": return 'fn main() { var a: int = 1; var b: int = 2; var once = true; while once { let old = a; a = b; b = old; once = false }; print(a); print(b) }\n'
    if name == "struct": return 'struct Pair { a: int, b: int }\nfn main() { let p = Pair { a: 40, b: 2 }; print(p.a + p.b) }\n'
    if name == "struct-call": return 'struct Pair { a: int, b: int }\nfn echo(p: Pair) -> Pair { p }\nfn main() { let p = Pair { a: 40, b: 2 }; let q = echo(p); print(q.a) }\n'
    if name == "call": return 'fn add(a: int, b: int) -> int { a + b }\nfn main() { print(add(20, 22)) }\n'
    operations = {
        "add": ("+", 20, 22), "sub": ("-", 64, 22), "mul": ("*", -6, -7),
        "div": ("/", -85, -2), "rem": ("%", -85, 2),
        "overflow-add": ("+", 9223372036854775807, 1),
        "overflow-sub": ("-", -9223372036854775808, 1),
        "overflow-mul": ("*", 9223372036854775807, 2),
        "zero-div": ("/", 7, 0), "min-div": ("/", -9223372036854775808, -1),
        "min-rem": ("%", -9223372036854775808, -1),
    }
    op, a, b = operations[name]
    return f"fn calculate(a: int, b: int) -> int {{ a {op} b }}\nfn main() {{ print(calculate({a}, {b})) }}\n"


def run(argv, **kw):
    return subprocess.run([str(a) for a in argv], capture_output=True, timeout=180, **kw)


def timed_link(argv, env, prefix):
    started = time.monotonic()
    try:
        result = run(argv, env=env)
    except subprocess.TimeoutExpired as failure:
        seconds = time.monotonic() - started
        prefix.with_suffix(".timing.json").write_text(json.dumps({"outcome": "timeout", "seconds": seconds, "budget_seconds": 180}) + "\n")
        prefix.with_suffix(".stdout").write_bytes(failure.stdout or b"")
        prefix.with_suffix(".stderr").write_bytes(failure.stderr or b"")
        print(f"FAIL link-timeout {prefix.parent.name} seconds={seconds:.3f} budget=180", flush=True)
        raise
    seconds = time.monotonic() - started
    prefix.with_suffix(".timing.json").write_text(json.dumps({"outcome": "completed", "seconds": seconds, "status": result.returncode, "budget_seconds": 180}) + "\n")
    prefix.with_suffix(".stdout").write_bytes(result.stdout)
    prefix.with_suffix(".stderr").write_bytes(result.stderr)
    print(f"LINK {prefix.parent.name} {prefix.name} seconds={seconds:.3f} status={result.returncode}", flush=True)
    return result, seconds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--gas-config", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    assert sys.platform == "linux", "Linux execution required; this is not a skip"
    root = a.root.resolve()
    tools = root / ".wolf-bin"
    a.out.mkdir(parents=True, exist_ok=True)
    elf = module("elf", tools / "clef/tools/elf.py")
    compiler = root / "target/fenrir"
    env = dict(os.environ, FENRIR_TOOLCHAIN=str(tools))
    gas = json.loads(a.gas_config.read_text())
    gas_env = dict(os.environ, LD_LIBRARY_PATH=gas["library_path"])
    version = run([gas["assembler"], "--version"], env=gas_env)
    assert version.returncode == 0 and b"2.42" in version.stdout, version.stderr
    (a.out / "gnu-as-version.txt").write_bytes(version.stdout)
    observations = []
    for name, text, expected in rows.fixtures():
        row = {"name": name}
        folder = (a.out / name).resolve()
        folder.mkdir(exist_ok=True)
        src = folder / "proof.lu"
        src.write_text(wolf_source(name))
        oracle = folder / "oracle"
        built = run([tools / "wolf", "build", src, "-o", oracle])
        (folder / "oracle-build.stderr").write_bytes(built.stderr)
        if built.returncode:
            row.update(verdict="oracle-refuses", status=built.returncode)
            observations.append(row); print("FAIL oracle-" + name, flush=True); continue
        reference = run([oracle])
        (folder / "oracle.stdout").write_bytes(reference.stdout)
        (folder / "oracle.stderr").write_bytes(reference.stderr)
        row["oracle_status"] = reference.returncode
        # These are handwritten FIR rows, not a source-lowering test. Give the
        # FIR instruction the source site's observed coordinates, then require
        # the backend to preserve the complete report byte for byte. Lowering
        # tests must independently derive coordinates from source spans.
        site = re.search(rb"^  at (.*):(\d+):(\d+)$", reference.stderr, re.M)
        if expected.startswith("trap:"):
            assert reference.returncode == 134 and site, (name, reference.returncode, reference.stderr)
            assert reference.stderr.splitlines()[0] == ("wolf-trap: " + expected[5:]).encode(), (name, reference.stderr)
            filename = site[1].hex()
            line, col = int(site[2]), int(site[3])
        else:
            assert reference.returncode == 0 and reference.stdout == expected.encode(), (name, reference.returncode, reference.stdout, reference.stderr)
            filename, line, col = str(src).encode().hex(), 1, 1
        text = text.replace("blob 70726f6f662e6c75", "blob " + filename).replace("site 0 1 1", f"site 0 {line} {col}")
        fir = folder / "proof.fir"
        fir.write_text(text)
        assembly = folder / "proof.s"
        emitted = run([compiler, "asm", fir, "-o", assembly])
        assert emitted.returncode == 0, (name, emitted.stderr)
        candidate_obj, gas_obj = folder / "clef.o", folder / "gas.o"
        assembled = run([tools / "bin/clef", "--64", "-o", candidate_obj, assembly])
        (folder / "clef.stderr").write_bytes(assembled.stderr)
        if assembled.returncode:
            row.update(verdict="clef-refuses", status=assembled.returncode, diagnostic=assembled.stderr.decode())
            observations.append(row); print("FAIL clef-" + name + " " + assembled.stderr.decode().strip(), flush=True); continue
        baseline = run([gas["assembler"], "--64", "-o", gas_obj, assembly], env=gas_env)
        assert baseline.returncode == 0, (name, baseline.stderr)
        delta = elf.differences(elf.ELF(candidate_obj), elf.ELF(gas_obj))
        (folder / "object-differential.json").write_text(json.dumps(delta, indent=2) + "\n")
        if delta:
            row.update(verdict="object-differs", differences=delta)
            observations.append(row); print("FAIL object-" + name, flush=True); continue
        binary = folder / "candidate"
        linked, row["link_seconds"] = timed_link([compiler, "link", fir, "-o", binary], env, folder / "link")
        if linked.returncode:
            row.update(verdict="link-refuses", status=linked.returncode)
            observations.append(row); print("FAIL link-" + name, flush=True); continue
        first = binary.read_bytes()
        again, row["relink_seconds"] = timed_link([compiler, "link", fir, "-o", binary], env, folder / "relink")
        assert again.returncode == 0 and first == binary.read_bytes(), (name, "nondeterministic link", again.stderr)
        actual = run([binary])
        (folder / "candidate.stdout").write_bytes(actual.stdout)
        (folder / "candidate.stderr").write_bytes(actual.stderr)
        same = (actual.returncode, actual.stdout, actual.stderr) == (reference.returncode, reference.stdout, reference.stderr)
        row.update(verdict="same" if same else "differs", candidate_status=actual.returncode)
        observations.append(row)
        print(("PASS " if same else "FAIL ") + "runtime-" + name, flush=True)
    (a.out / "results.json").write_text(json.dumps(observations, indent=2) + "\n")
    return int(any(x["verdict"] != "same" for x in observations))


if __name__ == "__main__":
    raise SystemExit(main())
