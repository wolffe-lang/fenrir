#!/usr/bin/env python3
"""Parse every pinned corpus file using the published phase ledger."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument("binary", type=Path)
p.add_argument("corpus", type=Path)
p.add_argument("--report", required=True, type=Path)
p.add_argument("--sources", type=Path)
a = p.parse_args()
paths = sorted(a.corpus.rglob("*.lu"))
if len(paths) != 1253:
    sys.exit(f"FAIL corpus-count: expected 1253, found {len(paths)}")
if a.sources:
    paths += sorted(a.sources.rglob("*.lu"))
failed = 0
with a.report.open("w") as out:
    for i, path in enumerate(paths):
        text = path.read_text()
        phase = re.search(r"^//! phase:\s*(\w+)", text, re.M)
        code = re.search(r"^//! check:\s*fail\((\w+)\)", text, re.M)
        reject = phase is not None and phase[1] in ("none", "lex")
        expected = code[1] if reject and code else None
        # The one broken member inherits the entry's module-load syntax error.
        # Do not infer validity merely from absence of a standalone phase.
        member = bool(re.search(r"^//! member:\s*true", text, re.M))
        if member and phase is None:
            owners = []
            for entry in sorted(path.parent.glob("*.lu")):
                entry_text = entry.read_text()
                error = re.search(r"^//! check:\s*fail\((E02\d\d)\)", entry_text, re.M)
                if error and re.search(r"^//! phase:\s*parse\b", entry_text, re.M):
                    owners.append((entry, error[1]))
            if owners:
                members = [f for f in path.parent.glob("*.lu") if re.search(r"^//! member:\s*true", f.read_text(), re.M)]
                if len(owners) != 1 or len(members) != 1:
                    sys.exit("FAIL ambiguous member syntax expectation: " + str(path.parent))
                reject = True
                expected = owners[0][1]
        child = subprocess.Popen([str(a.binary), "--emit=ast", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        start = time.monotonic()
        watchdog = None
        while child.poll() is None:
            rss = subprocess.run(["ps", "-o", "rss=", "-p", str(child.pid)], capture_output=True, text=True)
            if int(rss.stdout.strip() or "0") > 4 * 1024 * 1024:
                watchdog = "child-rss-watchdog"
            if time.monotonic() - start > 15:
                watchdog = "child-timeout"
            if watchdog:
                child.kill()
                break
            time.sleep(0.01)
        _, err = child.communicate()
        diagnostic = err.decode(errors="replace")
        observed = re.search(r"error\[(\w+)\]", diagnostic)
        ok = watchdog is None and child.returncode == (2 if reject else 0)
        if expected:
            ok &= observed is not None and observed[1] == expected
        row = dict(file=str(path), expected=expected or "accept", exit=child.returncode, code=observed[1] if observed else None, same=bool(ok), diagnostic=diagnostic, watchdog=watchdog)
        out.write(json.dumps(row) + "\n")
        out.flush()
        if not ok:
            print(f"FAIL corpus {path.name}: expected={row['expected']} exit={row['exit']} code={row['code']} {watchdog or ''}", flush=True)
            failed += 1
        if (i + 1) % 100 == 0:
            print(f"corpus: {i + 1}/{len(paths)}; {failed} failures", flush=True)
print(f"corpus: {len(paths)} rows, {failed} failures", flush=True)
sys.exit(bool(failed))
