#!/usr/bin/env python3
"""Check the real clef comparator with equal ELF objects and a changed text byte."""
import argparse
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fixture():
    # ELF gABI ch.4: ELF64-LE ET_REL, .text plus its section-name string table.
    text = b"\x88\xc1"  # MOV r/m8,r8: movb %al,%cl (Intel SDM MOV 88 /r).
    strings = b"\0.text\0.shstrtab\0"
    shoff = (64 + len(text) + len(strings) + 7) & ~7
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    header = struct.pack("<16sHHIQQQIHHHHHH", ident, 1, 62, 1, 0, 0, shoff, 0, 64, 0, 0, 64, 3, 2)
    body = header + text + strings
    body += bytes(shoff - len(body))
    body += bytes(64)
    body += struct.pack("<IIQQQQIIQQ", 1, 1, 6, 0, 64, len(text), 0, 0, 1, 0)
    body += struct.pack("<IIQQQQIIQQ", 7, 3, 0, 0, 64 + len(text), len(strings), 0, 0, 1, 0)
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--scratch", type=Path, required=True)
    a = ap.parse_args()
    harness = load("form_harness", a.root / "tests/backend/forms-linux.py")
    elf = load("elf", a.root / ".wolf-bin/clef/tools/elf.py")
    a.scratch.mkdir(parents=True, exist_ok=True)
    failures = 0

    def check(name, condition):
        nonlocal failures
        print(("PASS " if condition else "FAIL ") + name, flush=True)
        failures += int(not condition)

    with tempfile.TemporaryDirectory(prefix="elf-contract-", dir=a.scratch) as directory:
        directory = Path(directory)
        baseline, equal, changed = [directory / name for name in ("baseline.o", "equal.o", "changed.o")]
        original = fixture()
        baseline.write_bytes(original)
        equal.write_bytes(original)
        planted = bytearray(original)
        planted[64] ^= 1  # Change exactly one payload byte; do not damage ELF tables.
        changed.write_bytes(planted)
        mismatch = elf.differences(elf.ELF(baseline), elf.ELF(changed))
        check("comparator-planted-text-byte", isinstance(mismatch, dict) and "sections" in mismatch and not harness.same_object(mismatch))
        matching = elf.differences(elf.ELF(baseline), elf.ELF(equal))
        check("comparator-equal-dict", matching == {} and harness.same_object(matching))
        check("comparator-missing-result", not harness.same_object(None))
        check("comparator-wrong-result-shape", not harness.same_object([]))
    return int(failures != 0)


if __name__ == "__main__":
    raise SystemExit(main())
