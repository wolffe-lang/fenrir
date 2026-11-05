#!/usr/bin/env python3
"""Run the lowering rows (tests/lower/rows.py) in one of three modes.

--mode preflight  the pinned wolf runs each row and shows its expectation;
--mode emit       fenrir emits FIR and assembly for each row, twice, and the
                  bytes agree; the FIR parses back to the same bytes; the
                  staged clef assembles the assembly;
--mode linux      fenrir builds and links each row; its stdout, stderr (the
                  trap line and site) and status equal the program the pinned
                  wolf builds from the same file. Linux x86-64 only.

Every failing row prints `FAIL NAME ...` and the step fails; nothing skips.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
# One link of the 0.2.36 musl runtime peaks at about 7.4 GiB of address space
# (tests/backend/linux.py); each build runs under its own 10 GiB budget.
LINK_ADDRESS_SPACE = 10 << 30
# `fenrir run` is checked on these rows too: a program's output, a status and
# a trap pass through it unchanged.
RUN_ROWS = {"hello", "main-int", "trap-div-zero"}
# These rows are built twice; the two executables must be byte-identical.
TWICE_ROWS = {"hello", "struct-fields", "order-split-operand"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def budget():
    resource.setrlimit(resource.RLIMIT_AS, (LINK_ADDRESS_SPACE, LINK_ADDRESS_SPACE))


def run(argv, timeout=180, limit=False, **kw):
    if limit:
        kw["preexec_fn"] = budget
    return subprocess.run([str(a) for a in argv], capture_output=True, timeout=timeout, **kw)


def expected_outcome(stdout, status, trap):
    return {"stdout": stdout.encode(), "status": 134 if trap else (status or 0), "trap": trap}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("preflight", "emit", "linux"), required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", action="append", help="run only the named rows")
    a = ap.parse_args()
    root = a.root.resolve()
    tools = root / ".wolf-bin"
    fenrir = root / "target/fenrir"
    rows = load("lower_rows", HERE / "rows.py")
    env = dict(os.environ, WOLF_STD=str(tools / "std"), WOLF_RT_LIB=str(tools / "libwolf_rt.a"), FENRIR_TOOLCHAIN=str(tools))
    if a.mode == "linux":
        assert sys.platform == "linux", "Linux execution required; this is not a skip"
    a.out.mkdir(parents=True, exist_ok=True)
    failed = 0
    count = 0
    for name, source, stdout, status, trap in rows.rows():
        if a.only and name not in a.only:
            continue
        count += 1
        folder = (a.out / name).resolve()
        folder.mkdir(exist_ok=True)
        src = folder / "main.lu"
        src.write_text(source)
        want = expected_outcome(stdout, status, trap)
        try:
            if a.mode == "preflight":
                program = folder / "oracle"
                built = run([tools / "wolf", "build", "--no-cache", src, "-o", program], env=env)
                assert built.returncode == 0, ("oracle build", built.returncode, built.stderr.decode(errors="replace")[:600])
                got = run([program], timeout=60)
                first = got.stderr.splitlines()[:1]
                assert got.returncode == want["status"], ("status", got.returncode, want["status"], got.stderr[:300])
                assert got.stdout == want["stdout"], ("stdout", got.stdout[:400], want["stdout"][:400])
                if trap:
                    assert first == [f"wolf-trap: {trap}".encode()], ("trap line", first)
                    assert got.stderr.splitlines()[1].startswith(b"  at " + str(src).encode() + b":"), ("trap site", got.stderr)
            elif a.mode == "emit":
                for mode in ("fir", "asm"):
                    outputs = []
                    for _ in range(2):
                        p = run([fenrir, f"--emit={mode}", src], env=env)
                        assert p.returncode == 0, (mode, p.returncode, p.stderr.decode(errors="replace")[:600])
                        outputs.append(p.stdout)
                    assert outputs[0] == outputs[1], (mode, "nondeterministic emission")
                    (folder / f"main.{mode if mode == 'fir' else 's'}").write_bytes(outputs[0])
                again = folder / "again.fir"
                p = run([fenrir, "fir", folder / "main.fir", "-o", again], env=env)
                assert p.returncode == 0 and again.read_bytes() == (folder / "main.fir").read_bytes(), ("FIR text is not a fixed point", p.stderr)
                clef = tools / "bin/clef"
                assert clef.is_file(), ("the staged clef is missing; run tools/build-tools first",)
                p = run([clef, "--64", "-o", folder / "main.o", folder / "main.s"], env=env)
                assert p.returncode == 0, ("clef refuses the emitted assembly", p.stderr.decode(errors="replace")[:400])
            else:
                program, oracle = folder / "candidate", folder / "oracle"
                started = time.monotonic()
                built = run([fenrir, "build", src, "-o", program], limit=True, env=env)
                seconds = time.monotonic() - started
                (folder / "build.stderr").write_bytes(built.stderr)
                assert built.returncode == 0 and program.is_file(), ("fenrir build", built.returncode, built.stderr.decode(errors="replace")[:600])
                reference = run([tools / "wolf", "build", "--no-cache", src, "-o", oracle], env=env)
                assert reference.returncode == 0, ("oracle build", reference.returncode, reference.stderr[:400])
                mine, theirs = run([program], timeout=60), run([oracle], timeout=60)
                for label, p in (("candidate", mine), ("oracle", theirs)):
                    (folder / f"{label}.stdout").write_bytes(p.stdout)
                    (folder / f"{label}.stderr").write_bytes(p.stderr)
                assert theirs.returncode == want["status"] and theirs.stdout == want["stdout"], ("oracle disagrees with the row", theirs.returncode, theirs.stdout[:200])
                same = (mine.returncode, mine.stdout, mine.stderr) == (theirs.returncode, theirs.stdout, theirs.stderr)
                assert same, ("differs", mine.returncode, theirs.returncode, mine.stdout[:300], theirs.stdout[:300], mine.stderr[:300], theirs.stderr[:300])
                if name in TWICE_ROWS:
                    first = program.read_bytes()
                    rebuilt = run([fenrir, "build", src, "-o", program], limit=True, env=env)
                    assert rebuilt.returncode == 0 and program.read_bytes() == first, ("two builds differ", rebuilt.returncode)
                if name in RUN_ROWS:
                    ran = run([fenrir, "run", src], limit=True, env=dict(env, TMPDIR=str(folder)))
                    # Each stream on its own, so a failure names the stream: the
                    # program's bytes and nothing of the build's on either.
                    assert ran.stdout == theirs.stdout, ("fenrir run stdout differs", ran.stdout[:300], theirs.stdout[:300])
                    assert ran.stderr == theirs.stderr, ("fenrir run stderr differs", ran.stderr[:300], theirs.stderr[:300])
                    assert ran.returncode == theirs.returncode, ("fenrir run status differs", ran.returncode, theirs.returncode)
                    assert not any(folder.glob("fenrir-run-*")), ("fenrir run left its directory behind",)
                print(f"LINK {name} seconds={seconds:.1f}", flush=True)
        except (AssertionError, subprocess.TimeoutExpired) as failure:
            print(f"FAIL {name} {failure}", flush=True)
            failed += 1
            continue
        print(f"PASS {a.mode}-{name}", flush=True)
    if a.only and count != len(set(a.only)):
        print(f"FAIL lowering-rows unknown row selected: {sorted(set(a.only))}", flush=True)
        return 1
    print(f"lowering rows: {count} run, {failed} failed ({a.mode})", flush=True)
    return 1 if failed or count == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
