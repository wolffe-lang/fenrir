#!/usr/bin/env python3
"""The census-driven corpus differential, Linux x86-64 in an isolated job.

Runs the harness (`tools/differ compare --fenrir`) over exactly the rows the
core census names, prints one line per row, and writes the compact verdict
table. With `--expect`, the table must equal the committed one. Any verdict
other than `same` fails: `differs`, `fenrir-crashes` and `fenrir-refuses` alike.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fenrir", type=Path, required=True)
    ap.add_argument("--select", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--expect", type=Path, help="the committed verdict table this run must reproduce")
    a = ap.parse_args()
    assert sys.platform == "linux", "Linux execution required; this is not a skip"
    a.out.mkdir(parents=True, exist_ok=True)
    table = a.out / "verdicts.json"
    full = a.out / "comparison.json"
    # Each build runs in its own private cwd, so the toolchain path is absolute.
    env = dict(os.environ, FENRIR_ORACLE_SANDBOX="1", FENRIR_TOOLCHAIN=os.environ.get("FENRIR_TOOLCHAIN", str(ROOT / ".wolf-bin")))
    with (a.out / "compare.stdout").open("wb") as stdout:
        p = subprocess.run([str(ROOT / "tools/differ"), "compare", "--fenrir", str(a.fenrir.resolve()), "--select", str(a.select),
                            "--output", str(full), "--table", str(table)], stdout=stdout, stderr=subprocess.PIPE, env=env, cwd=ROOT)
    sys.stdout.write(p.stderr.decode(errors="replace"))
    if not table.is_file():
        print(f"FAIL corpus-differential harness wrote no table, status {p.returncode}", flush=True)
        return 1
    data = json.loads(table.read_text())
    for row in data["rows"]:
        tag = "PASS" if row["verdict"] == "same" else "FAIL"
        print(f"{tag} corpus-{row['file']} {row['verdict']}", flush=True)
    print("VERDICTS " + json.dumps({"counts": data["counts"], "coverage": data["coverage"]}, sort_keys=True), flush=True)
    status = p.returncode
    if a.expect:
        if json.loads(a.expect.read_text()) != data:
            print(f"FAIL corpus-table the computed verdict table differs from {a.expect}", flush=True)
            status = status or 1
        else:
            print(f"PASS corpus-table equals {a.expect}", flush=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
