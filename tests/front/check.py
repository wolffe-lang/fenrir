#!/usr/bin/env python3
"""Black-box front-end rows and arena invariants; scratch is caller-owned."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def invoke(command, timeout=10):
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start = time.monotonic()
    while True:
        try:
            out, err = child.communicate(timeout=0.1)
            return subprocess.CompletedProcess(command, child.returncode, out, err)
        except subprocess.TimeoutExpired:
            rss = subprocess.run(["ps", "-o", "rss=", "-p", str(child.pid)], capture_output=True, text=True)
            if int(rss.stdout.strip() or "0") > 4 * 1024 * 1024:
                child.kill()
                child.communicate()
                raise AssertionError("child-rss-watchdog")
            if time.monotonic() - start > timeout:
                child.kill()
                child.communicate()
                raise AssertionError("child-timeout")


def arena(output, source):
    data = source.read_bytes()
    positions = {}
    line = col = 1
    offset = 0
    for char in data.decode():
        positions[offset] = (line, col)
        offset += len(char.encode())
        if char == "﻿" and offset == 3:
            continue
        if char == "\n":
            line += 1
            col = 1
        else:
            col += 1
    positions[offset] = (line, col)
    nodes = {}
    token_count = 0
    for row in output.decode().splitlines():
        if row.startswith("token "):
            bits = row.split(" ", 9)
            assert int(bits[1]) == token_count
            token_count += 1
            start, end, ln, cl, eln, ecl = map(int, bits[3:9])
            assert start <= end and positions[start] == (ln, cl) and positions[end] == (eln, ecl), ("token-span", row)
        if row.startswith("node "):
            bits = row.split()
            ident = int(bits[1])
            assert ident == len(nodes)
            token, first, last, nxt, start, end, ln, cl, eln, ecl = map(int, bits[3:])
            assert 0 <= token < token_count
            assert start <= end and positions[start] == (ln, cl) and positions[end] == (eln, ecl), ("node-span", row)
            nodes[ident] = dict(kind=bits[2], first=first, last=last, next=nxt, start=start, end=end)
    assert nodes and nodes[0]["kind"] == "Unit"
    visited = set()
    pending = [0]
    while pending:
        ident = pending.pop()
        assert ident not in visited, ("duplicate-or-cycle", ident)
        visited.add(ident)
        node = nodes[ident]
        child = node["first"]
        siblings = set()
        last = -1
        while child != -1:
            assert child in nodes and child not in siblings
            siblings.add(child)
            sub = nodes[child]
            assert node["start"] <= sub["start"] <= sub["end"] <= node["end"], ("containment", ident, child)
            pending.append(child)
            last = child
            child = sub["next"]
        assert last == node["last"]
    assert visited == set(nodes), ("unreachable", set(nodes) - visited)
    return {n["kind"] for n in nodes.values()}


def main():
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
        source.write_bytes(bytes.fromhex(row["hex"]) if "hex" in row else row["source"].encode())
        try:
            mode = row.get("mode", "ast")
            command = [str(a.binary), "--emit=" + mode, str(source)]
            r = invoke(command)
            ok = r.returncode == row["exit"]
            text = r.stderr.decode("utf-8", errors="replace")
            if "code" in row:
                ok &= row["code"] in text and bool(re.search(re.escape(str(source)) + r":\d+:\d+", text))
            if "location" in row:
                ln, col = row["location"]
                ok &= f"{source}:{ln}:{col}: error[" in text
            if r.returncode == 0:
                again = invoke(command)
                ok &= again.returncode == 0 and again.stdout == r.stdout
                if mode == "ast":
                    kinds = arena(r.stdout, source)
                    ok &= set(row.get("nodes", [])) <= kinds
            print(("PASS " if ok else "FAIL ") + row["name"], flush=True)
            if not ok:
                print(f"  exit={r.returncode}; expected={row['exit']}; {text[:600]}", flush=True)
            failures += not ok
        except (AssertionError, ValueError, KeyError) as exc:
            print("FAIL " + row["name"] + ": " + str(exc), flush=True)
            failures += 1
    print(f"front rows: {failures} failed", flush=True)
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
