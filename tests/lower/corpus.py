#!/usr/bin/env python3
"""The census-driven corpus differential, Linux x86-64 in an isolated job.

Runs the harness (`tools/differ compare --fenrir`) over exactly the rows the
core census names, prints one line per row, and writes the compact verdict
table. With `--expect`, the table must equal the committed one. Any verdict
other than `same` fails: `differs`, `fenrir-crashes` and `fenrir-refuses` alike.

With `--shard K/N` it compares only the K-th of N shards of the selection (the
rows in file order, every N-th from the K-th), so hosted CI can run the native
differential as parallel jobs. Each row is in exactly one shard; with `--expect`
the shard's rows and identity must equal the committed table's, row by row. The
whole-table counts and coverage stay checked by the unsharded interpreter run.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def parse_shard(text):
    """`K/N` with 1 <= K <= N, as the pair (K, N)."""
    try:
        k, n = (int(part) for part in text.split("/"))
    except ValueError:
        raise ValueError(f"shard {text!r} is not K/N") from None
    if not 1 <= k <= n:
        raise ValueError(f"shard {text!r} names no shard")
    return k, n


def shard_rows(select, k, n):
    """The selection's rows in file order, every n-th from the k-th (1-based)."""
    chosen = json.loads(Path(select).read_text())
    if isinstance(chosen, dict) and "rows" in chosen:
        chosen = [row["file"] for row in chosen["rows"] if row.get("cls") == "core"]
    elif isinstance(chosen, dict):
        chosen = chosen["core"]
    return sorted(chosen)[k - 1::n]


def shard_problems(table, expected, names):
    """A shard's table against the committed one: its identity, and exactly the
    shard's rows, each equal to the committed row. Each problem is one line."""
    problems = []
    if table.get("identity") != expected.get("identity"):
        problems.append("identity differs from the committed table")
    wanted = {row["file"]: row for row in expected["rows"]}
    found = {row["file"]: row for row in table["rows"]}
    inside = set(names)
    for name in names:
        if name not in wanted:
            problems.append(f"{name} is not in the committed table")
        elif name not in found:
            problems.append(f"{name} missing from the shard table")
        elif found[name] != wanted[name]:
            problems.append(f"{name} differs from the committed row")
    problems += [f"{row['file']} is outside the shard" for row in table["rows"] if row["file"] not in inside]
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fenrir", type=Path, required=True)
    ap.add_argument("--select", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--expect", type=Path, help="the committed verdict table this run must reproduce")
    ap.add_argument("--interpreter", action="store_true", help="compare bounded FIR execution instead of linking")
    ap.add_argument("--shard", metavar="K/N", help="compare only the K-th of N shards of the selection")
    a = ap.parse_args()
    assert sys.platform == "linux", "Linux execution required; this is not a skip"
    a.out.mkdir(parents=True, exist_ok=True)
    select, names = a.select, None
    if a.shard:
        k, n = parse_shard(a.shard)
        names = shard_rows(a.select, k, n)
        if not names:
            print(f"FAIL corpus-shard {a.shard} holds no row", flush=True)
            return 1
        select = a.out / "selection.json"
        select.write_text(json.dumps(names, indent=1) + "\n")
        print(f"corpus-shard {a.shard}: {len(names)} rows", flush=True)
    table = a.out / "verdicts.json"
    full = a.out / "comparison.json"
    # Each build runs in its own private cwd, so the toolchain path is absolute.
    env = dict(os.environ, FENRIR_ORACLE_SANDBOX="1", FENRIR_TOOLCHAIN=os.environ.get("FENRIR_TOOLCHAIN", str(ROOT / ".wolf-bin")))
    command = [str(ROOT / "tools/differ"), "compare", "--fenrir", str(a.fenrir.resolve()), "--select", str(select),
               "--output", str(full), "--table", str(table)]
    if a.interpreter:
        command.append("--interpreter")
    with (a.out / "compare.stdout").open("wb") as stdout:
        p = subprocess.run(command, stdout=stdout, stderr=subprocess.PIPE, env=env, cwd=ROOT)
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
    if a.expect and names is not None:
        problems = shard_problems(data, json.loads(a.expect.read_text()), names)
        for problem in problems:
            print(f"FAIL corpus-table shard {a.shard}: {problem}", flush=True)
        if problems:
            status = status or 1
        else:
            print(f"PASS corpus-table shard {a.shard}: {len(names)} rows equal {a.expect}'s", flush=True)
    elif a.expect:
        if json.loads(a.expect.read_text()) != data:
            print(f"FAIL corpus-table the computed verdict table differs from {a.expect}", flush=True)
            status = status or 1
        else:
            print(f"PASS corpus-table equals {a.expect}", flush=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
