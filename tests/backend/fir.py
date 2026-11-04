#!/usr/bin/env python3
"""Black-box FIR contracts; no reference-compiler implementation is read."""
import argparse
import pathlib
import subprocess
import tempfile


def inst(op, ty=0, site=0, data=(), uses=()):
    return f"{op} {ty} {site} {len(data)}" + "".join(f" {x}" for x in data) + f" {len(uses)}" + "".join(f" {x}" for x in uses)


def module(body, *, blocks=None, result=1, params=(), structs=()):
    if blocks is None:
        blocks = [(params, body)]
    lines = ["fir 0", "blobs 2", "blob 70726f6f662e6c75", "blob 68656c6c6f2c20776f6c66", "sites 1", "site 0 1 1", f"structs {len(structs)}"]
    for fields in structs:
        lines.append(f"struct {len(fields)}" + "".join(f" {x}" for x in fields))
    lines += ["functions 1", f"function {result} {len(params)}" + "".join(f" {x}" for x in params) + f" {len(blocks)}"]
    for ps, ins in blocks:
        lines += [f"block {len(ps)}" + "".join(f" {x}" for x in ps) + f" {len(ins)}", *ins]
    return "\n".join([*lines, "end", ""])


def cases():
    c = inst("const", 1, data=(0,))
    r = inst("return", uses=(0,))
    yield "roundtrip-int", module([c, r]), None
    yield "roundtrip-string", module([inst("string", 3, data=(1,)), inst("print", uses=(0,)), c, inst("return", uses=(2,))]), None
    yield "reject-opcode", module([inst("mystery"), c, inst("return", uses=(1,))]), "FIR_OPCODE"
    yield "reject-site", module([inst("const", 1, site=99, data=(0,)), r]), "FIR_SITE"
    yield "reject-type", module([inst("const", 99, data=(0,)), r]), "FIR_TYPE"
    yield "reject-operand-type", module([inst("const", 2, data=(1,)), inst("add", 1, uses=(0, 0)), inst("return", uses=(1,))]), "FIR_TYPE"
    yield "reject-forward-use", module([inst("add", 1, uses=(1, 1)), c, r]), "FIR_DOMINANCE"
    yield "reject-self-use", module([inst("add", 1, uses=(0, 0)), r]), "FIR_DOMINANCE"
    yield "reject-cross-block-use", module([], blocks=[([], [c, inst("jump", data=(1,))]), ([], [r])]), "FIR_DOMINANCE"
    yield "reject-after-trap", module([inst("trap", data=(1,)), r]), "FIR_TERMINATOR"
    yield "reject-missing-terminator", module([c]), "FIR_TERMINATOR"
    yield "reject-after-terminator", module([c, r, c]), "FIR_TERMINATOR"
    yield "reject-branch-target", module([inst("jump", data=(9,))]), "FIR_BRANCH"
    yield "reject-branch-arity", module([], blocks=[([], [inst("jump", data=(1,))]), ([1], [r])]), "FIR_BRANCH"
    yield "reject-call-target", module([inst("call", 1, data=(9,)), r]), "FIR_CALL"
    yield "reject-return-type", module([inst("const", 2, data=(1,)), r]), "FIR_TYPE"
    yield "reject-bool-range", module([inst("const", 2, data=(2,)), c, inst("return", uses=(1,))]), "FIR_LITERAL"
    yield "reject-trap-kind", module([inst("trap", data=(99,))]), "FIR_TRAP"
    yield "reject-trailing-tokens", module([c, r]) + "garbage\n", "FIR_SYNTAX"
    yield "reject-negative-count", module([c, r]).replace("blobs 2", "blobs -1"), "FIR_SYNTAX"
    yield "reject-invalid-utf8", module([c, r]).replace("blob 68656c6c6f2c20776f6c66", "blob ff"), "FIR_SYNTAX"
    yield "reject-empty-site", module([c, r]).replace("blob 70726f6f662e6c75", "blob -"), "FIR_SITE"
    yield "reject-zero-line", module([c, r]).replace("site 0 1 1", "site 0 0 1"), "FIR_SITE"
    yield "reject-recursive-type", module([c, r], structs=[(5,)]), "FIR_TYPE"
    yield "reject-unit-use", module([c, inst("print", uses=(0,)), inst("add", 1, uses=(1, 0)), inst("return", uses=(2,))]), "FIR_TYPE"
    yield "reject-negative-use", module([inst("add", 1, uses=(-1, -1)), r]), "FIR_DOMINANCE"
    yield "reject-branch-condition", module([c, inst("branch", data=(0, 0, 0), uses=(0,))]), "FIR_TYPE"
    yield "reject-call-arity", module([c, inst("call", 1, data=(0,), uses=(0,)), inst("return", uses=(1,))]), "FIR_CALL"
    yield "reject-call-result", module([inst("call", 2, data=(0,)), c, inst("return", uses=(1,))]), "FIR_TYPE"
    yield "reject-unknown-blob", module([inst("string", 3, data=(999,)), c, inst("return", uses=(1,))]), "FIR_LITERAL"
    yield "reject-unknown-field", module([c, inst("struct", 5, uses=(0,)), inst("field", 1, data=(9,), uses=(1,)), inst("return", uses=(2,))], structs=[(1,)]), "FIR_TYPE"
    yield "reject-site-file", module([c, r]).replace("site 0 1 1", "site 999 1 1"), "FIR_SITE"
    shapes = [(1,)] + [(i + 4, i + 4) for i in range(1, 21)]
    huge = module([c, r], structs=shapes).replace("functions 1", "functions 2")
    params = " ".join(["25"] * 129)
    callee = f"function 0 129 {params} 1\nblock 129 {params} 1\n" + inst("return") + "\n"
    yield "reject-frame-displacement", huge.replace("end\n", callee + "end\n"), "FIR_LAYOUT"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("compiler", type=pathlib.Path)
    ap.add_argument("--scratch", type=pathlib.Path, required=True)
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fir-", dir=a.scratch) as root:
        root = pathlib.Path(root)
        for name, text, error in cases():
            src, out = root / f"{name}.fir", root / f"{name}.out"
            src.write_text(text)
            out.write_text("sentinel")
            p = subprocess.run([str(a.compiler.resolve()), "fir", str(src), "-o", str(out)], capture_output=True, text=True)
            try:
                if error:
                    assert p.returncode == 2 and error in p.stderr, (name, p.returncode, p.stdout, p.stderr)
                    assert out.read_text() == "sentinel", (name, "replaced output on refusal")
                else:
                    assert p.returncode == 0, (name, p.returncode, p.stderr)
                    second = root / "again.fir"
                    q = subprocess.run([str(a.compiler.resolve()), "fir", str(out), "-o", str(second)], capture_output=True, text=True)
                    assert q.returncode == 0 and out.read_bytes() == second.read_bytes(), (name, q.stderr)
            except AssertionError:
                print(f"FAIL {name} expected {error or 'round trip'} status={p.returncode}", flush=True)
                raise
            print(f"PASS {name}", flush=True)


if __name__ == "__main__":
    main()
