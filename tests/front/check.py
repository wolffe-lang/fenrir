#!/usr/bin/env python3
"""Black-box front-end rows. All generated files stay in caller-owned scratch."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument("binary", type=Path)
p.add_argument("--work", required=True, type=Path)
p.add_argument("--rows", type=Path, default=Path(__file__).with_name("rows.json"))
a = p.parse_args()
a.work.mkdir(parents=True, exist_ok=True)
if not a.binary.is_file():
    sys.exit("FAIL front-executable: build the front end first")
failures = 0
for row in json.loads(a.rows.read_text()):
    source = a.work / (row["name"] + ".lu")
    source.write_text(row["source"])
    try:
        r = subprocess.run([str(a.binary), "--emit=ast", str(source)], capture_output=True, timeout=10)
        ok = r.returncode == row["exit"]
        text = r.stderr.decode("utf-8", errors="replace")
        if "code" in row:
            ok &= row["code"] in text and bool(re.search(re.escape(str(source)) + r":\d+:\d+", text))
        if r.returncode == 0:
            again = subprocess.run([str(a.binary), "--emit=ast", str(source)], capture_output=True, timeout=10)
            ok &= again.returncode == 0 and again.stdout == r.stdout
        print(("PASS " if ok else "FAIL ") + row["name"], flush=True)
        if not ok:
            print(f"  exit={r.returncode}; expected={row['exit']}; {text[:600]}", flush=True)
        failures += not ok
    except subprocess.TimeoutExpired:
        print("FAIL " + row["name"] + ": timeout", flush=True)
        failures += 1
print(f"front rows: {failures} failed", flush=True)
sys.exit(bool(failures))
