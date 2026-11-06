#!/usr/bin/env python3
"""Execute the unchanged F2 form envelope through both pinned Linux assemblers."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def same_object(differences):
    # clef's comparator returns a mapping of changed semantic categories.
    # None means an assembler failed; an unexpected result shape is not equality.
    return isinstance(differences, dict) and not differences


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--gas-config", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    assert sys.platform == "linux", "Linux-built clef is required"
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    forms = load("form_envelope", Path(__file__).with_name("x86_forms.py"))
    elf = load("elf", root / ".wolf-bin/clef/tools/elf.py")
    gas = json.loads(a.gas_config.read_text())
    gas_env = dict(os.environ, LD_LIBRARY_PATH=gas["library_path"])
    clef = root / ".wolf-bin/bin/clef"
    results = []
    for row in forms.forms():
        src = a.out / (row["id"] + ".s")
        candidate = a.out / (row["id"] + ".clef.o")
        baseline = a.out / (row["id"] + ".gas.o")
        src.write_text(".text\n" + row["sample"] + "\n.Ltarget:\n")
        c = subprocess.run([str(clef), "--64", "-o", str(candidate), str(src)], capture_output=True, timeout=30)
        g = subprocess.run([gas["assembler"], "--64", "-o", str(baseline), str(src)], env=gas_env, capture_output=True, timeout=30)
        row["clef_status"], row["gas_status"] = c.returncode, g.returncode
        row["clef_stderr"], row["gas_stderr"] = c.stderr.decode(), g.stderr.decode()
        row["differences"] = elf.differences(elf.ELF(candidate), elf.ELF(baseline)) if c.returncode == 0 and g.returncode == 0 else None
        row["same"] = same_object(row["differences"])
        results.append(row)
        if not row["same"]:
            print("FAIL " + row["id"] + " " + json.dumps({key: row[key] for key in ("sample", "clef_status", "gas_status", "clef_stderr", "gas_stderr", "differences")}, sort_keys=True), flush=True)
        elif len(results) % 64 == 0:
            print(f"PASS form-differential-progress {len(results)}/640", flush=True)
    # An explicitly excluded narrow symbolic relocation remains a named refusal.
    src = a.out / "narrow-symbolic.s"
    src.write_text(".text\ntestw $sym,sym(%rip)\n")
    c = subprocess.run([str(clef), "--64", "-o", str(a.out / "narrow.clef.o"), str(src)], capture_output=True, timeout=30)
    g = subprocess.run([gas["assembler"], "--64", "-o", str(a.out / "narrow.gas.o"), str(src)], env=gas_env, capture_output=True, timeout=30)
    deviation = {"sample": "testw $sym,sym(%rip)", "clef_status": c.returncode, "gas_status": g.returncode, "diagnostic": c.stderr.decode()}
    assert c.returncode == 1 and g.returncode == 0 and b"unsupported_narrow_relocation" in c.stderr, deviation
    # Two nested `while` loops whose direct jumps' short and long forms depend
    # on each other: the layout must reach GNU as's fixed point. The emitter's
    # block jumps go through %rax; this witness keeps the direct-jump shape.
    witness = Path(__file__).with_name("nested-loops.s")
    c = subprocess.run([str(clef), "--64", "-o", str(a.out / "nested-loops.clef.o"), str(witness)], capture_output=True, timeout=30)
    g = subprocess.run([gas["assembler"], "--64", "-o", str(a.out / "nested-loops.gas.o"), str(witness)], env=gas_env, capture_output=True, timeout=30)
    nested = {"clef_status": c.returncode, "gas_status": g.returncode, "clef_stderr": c.stderr.decode(), "gas_stderr": g.stderr.decode()}
    nested["differences"] = elf.differences(elf.ELF(a.out / "nested-loops.clef.o"), elf.ELF(a.out / "nested-loops.gas.o")) if c.returncode == 0 and g.returncode == 0 else None
    nested["same"] = same_object(nested["differences"])
    print(("PASS" if nested["same"] else "FAIL") + " nested-loop-layout " + json.dumps(nested, sort_keys=True)[:600], flush=True)
    pins = tomllib.loads((root / "wolf-toolchain.toml").read_text())
    pin = next(x["rev"] for x in pins["artifact"] if x["name"] == "clef")
    report = {"clef_pin": pin, "clef_binary_sha256": hashlib.sha256(clef.read_bytes()).hexdigest(), "host": os.uname().machine, "cpus": sorted(os.sched_getaffinity(0)), "rows": results, "named_deviation": deviation, "nested_loops": nested}
    (a.out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    good = sum(x["same"] for x in results)
    print(f"{'PASS' if good == len(results) else 'FAIL'} form-differential {good}/{len(results)}; named narrow relocation remains refused", flush=True)
    return int(good != len(results) or not nested["same"])


if __name__ == "__main__":
    raise SystemExit(main())
