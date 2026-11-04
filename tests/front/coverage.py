#!/usr/bin/env python3
"""Check production/anchor row ownership against both pinned key sets."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

def check(rows, coverage, productions, anchors):
    assert set(coverage["productions"]) == productions, "production key set changed"
    assert set(coverage["anchors"]) == anchors, "anchor key set changed"
    assert set(coverage["scoped"]) == {k for k in anchors if k.startswith(("gram.fmt", "gram.version"))}, "scope changed"
    targets = productions | anchors
    observed = {}
    for row in rows:
        target = row["target"]
        assert target in targets and row["family"] in coverage["families"], "unknown row owner"
        assert row["exit"] in (0, 2) and row["source"], "unexecutable row"
        if row["exit"] == 2:
            assert re.fullmatch(r"E\d{4}", row["code"]), "negative row without code"
        observed.setdefault(target, set()).add(row["exit"])
    assert set(observed) == targets, "missing row owner"
    assert all(verdicts == {0, 2} for verdicts in observed.values()), "missing positive or negative row"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("spec", type=Path)
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    try:
        rows = json.loads((ROOT / "tests/front/grammar.json").read_text())
        coverage = json.loads((ROOT / "tests/front/coverage.json").read_text())
        productions = set(re.findall(r"^(\w+)\s*::=", (a.spec / "grammar.ebnf").read_text(), re.M))
        anchors = {k for k in json.loads((a.spec / "anchors.json").read_text())["anchors"] if k.startswith("gram.")}
        check(rows, coverage, productions, anchors)
        if a.self_test:
            for target in sorted(productions | anchors):
                broken = [r for r in rows if not (r["target"] == target and r["exit"] == 0)]
                try:
                    check(broken, coverage, productions, anchors)
                except AssertionError:
                    print("PASS coverage-rejects-missing-positive " + target)
                else:
                    raise AssertionError("coverage cannot reject missing row: " + target)
            changed = dict(coverage, anchors=coverage["anchors"][:-1])
            try:
                check(rows, changed, productions, anchors)
            except AssertionError:
                print("PASS registry-rejects-dropped-anchor")
            else:
                raise AssertionError("registry gate cannot reject a dropped anchor")
        print(f"coverage: {len(productions)} productions, {len(anchors)} anchors; {len(coverage['scoped'])} scoped acceptance/integrity only; {len(rows)} executable rows")
        return 0
    except (AssertionError, OSError, KeyError, ValueError) as exc:
        print("FAIL grammar-coverage: " + str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
