#!/usr/bin/env python3
"""Extract only clef-pinned GNU-as binary packages into isolated directories."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clef-source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    lock = json.loads((a.clef_source / "ci/oracle-lock.json").read_text())
    wanted = {"binutils-x86-64-linux-gnu", "libbinutils", "libsframe1", "libctf0", "libctf-nobfd0"}
    packages = [p for p in lock["packages"] if p["name"] in wanted]
    assert {p["name"] for p in packages} == wanted
    a.out.mkdir(parents=True, exist_ok=False)
    libraries = []
    assembler = None
    for p in packages:
        item = a.out / p["name"]
        item.mkdir()
        archive = item / "input.deb"
        subprocess.run(["curl", "-fsSL", "--retry", "3", p["url"], "-o", str(archive)], check=True)
        for _ in range(2):
            assert hashlib.sha256(archive.read_bytes()).hexdigest() == p["sha256"], p["name"]
        extracted = item / "extracted"
        extracted.mkdir()
        subprocess.run(["dpkg-deb", "-x", str(archive), str(extracted)], check=True)
        libraries.append(str((extracted / "usr/lib/x86_64-linux-gnu").resolve()))
        if p["name"] == "binutils-x86-64-linux-gnu":
            assembler = (extracted / "usr/bin/x86_64-linux-gnu-as").resolve()
        print("PINNED GNU-AS PACKAGE " + p["name"] + " " + p["sha256"], flush=True)
    assert assembler and assembler.is_file()
    config = {"assembler": str(assembler), "library_path": ":".join(libraries), "packages": packages}
    (a.out / "gas.json").write_text(json.dumps(config, indent=2) + "\n")


if __name__ == "__main__":
    main()
