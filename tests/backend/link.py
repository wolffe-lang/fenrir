#!/usr/bin/env python3
"""The link command has no shell, no fallback and no stale-output success.

The mock tools chatter on standard output, as ligature's `verify` does: a
successful link prints nothing on either stream, and a failing tool's output
reaches fenrir's standard error, never its standard output.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

spec = importlib.util.spec_from_file_location("fir_rows", Path(__file__).with_name("fir.py"))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)

MOCK = '''#!/usr/bin/env python3
import json, os, pathlib, sys
kind = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["CALL_LOG"], "a") as log: log.write(json.dumps([kind, args]) + "\\n")
print(f"{kind} chatter {args[0] if args else ''}", flush=True)
mode = os.environ.get("MOCK_MODE", "")
if mode == kind + "-fail": sys.exit(9)
if args and args[0] == "verify": sys.exit(0)
if mode == kind + "-missing": sys.exit(0)
out = pathlib.Path(args[args.index("-o") + 1])
if kind == "clef": out.write_bytes(b"object")
else:
    header = bytearray(64)
    header[:7] = b"\\x7fELF\\x02\\x01\\x01"
    header[16:20] = b"\\x02\\x00\\x3e\\x00"
    header[24] = 1
    out.write_bytes(header)
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("compiler", type=Path)
    ap.add_argument("--scratch", type=Path, required=True)
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=a.scratch, prefix="link space ") as tmp:
        root = Path(tmp)
        tools = root / "tool chain"
        (tools / "bin").mkdir(parents=True)
        for tool in ("clef", "ligature"):
            p = tools / "bin" / tool
            p.write_text(MOCK)
            p.chmod(0o700)
        src = root / "input ; literal.fir"
        src.write_text(f.module([f.inst("const", 1, data=(0,)), f.inst("return", uses=(0,))]))
        out = root / "output ; literal"
        log = root / "calls.jsonl"
        env = dict(os.environ, FENRIR_TOOLCHAIN=str(tools), CALL_LOG=str(log))
        for mode in ("clef-fail", "clef-missing", "ligature-fail", "ligature-missing", ""):
            out.write_text("sentinel")
            log.write_text("")
            p = subprocess.run([str(a.compiler.resolve()), "link", str(src), "-o", str(out)], capture_output=True, text=True, env=dict(env, MOCK_MODE=mode))
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            assert p.stdout == "", (mode, "a tool's output reached fenrir's stdout", p.stdout)
            if mode:
                assert p.returncode == 2, (mode, p.returncode, p.stderr)
                assert out.read_text() == "sentinel", (mode, "replaced previous output")
                if mode.startswith("clef"):
                    assert [c[0] for c in calls] == ["clef"], calls
                if mode.endswith("-fail"):
                    tool = mode.split("-")[0]
                    assert f"{tool} chatter" in p.stderr, (mode, "the failing tool's output is lost", p.stderr)
            else:
                assert p.returncode == 0, (p.returncode, p.stderr)
                assert p.stderr == "", ("a successful link printed", p.stderr)
                assert out.read_bytes().startswith(b"\x7fELF")
                assert [c[0] for c in calls] == ["clef", "ligature", "ligature"]
                assert calls[0][1][0] == "--64"
                assert str(tools / "musl/libwolf_rt.a") in calls[1][1]
                assert calls[2][1][0] == "verify"
            assert not Path(str(out) + ".fenrir-build").exists(), "scratch was not cleaned"
            print("PASS link-" + (mode or "argv-boundaries"), flush=True)
        # Never remove someone else's pre-existing staging directory.
        stage = Path(str(out) + ".fenrir-build")
        stage.mkdir()
        owned = stage / "not-ours"
        owned.write_text("keep")
        p = subprocess.run([str(a.compiler.resolve()), "link", str(src), "-o", str(out)], capture_output=True, text=True, env=env)
        assert p.returncode == 2 and owned.read_text() == "keep"
        print("PASS link-existing-staging-refusal", flush=True)


if __name__ == "__main__":
    main()
