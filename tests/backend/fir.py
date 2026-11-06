#!/usr/bin/env python3
"""Black-box FIR contracts; no reference-compiler implementation is read."""
import argparse
import pathlib
import subprocess
import tempfile


def inst(op, ty=0, site=0, data=(), uses=()):
    return f"{op} {ty} {site} {len(data)}" + "".join(f" {x}" for x in data) + f" {len(uses)}" + "".join(f" {x}" for x in uses)


# FIR 1's fixed types; structs start at STRUCT.
UNIT, INT, BOOL, STR, LIST, I32, I64, U8, U64, UINT, STRUCT = range(11)


def function(result, params, blocks, slots=()):
    head = f"function {result} {len(params)}" + "".join(f" {x}" for x in params)
    return head + f" {len(slots)}" + "".join(f" {x}" for x in slots) + f" {len(blocks)}"


def module(body, *, blocks=None, result=1, params=(), structs=(), slots=(), shapes=None):
    if blocks is None:
        blocks = [(params, body)]
    lines = ["fir 1", "blobs 2", "blob 70726f6f662e6c75", "blob 68656c6c6f2c20776f6c66", "sites 1", "site 0 1 1", f"structs {len(structs)}"]
    records = [("struct", fields) for fields in structs]
    if shapes is not None:
        lines[0], lines[-1] = "fir 2", f"shapes {len(shapes)}"
        records = shapes
    for kind, fields in records:
        lines.append(f"{kind} {len(fields)}" + "".join(f" {x}" for x in fields))
    lines += ["functions 1", function(result, params, blocks, slots)]
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
    yield "reject-recursive-type", module([c, r], structs=[(STRUCT,)]), "FIR_TYPE"
    yield "reject-unit-use", module([c, inst("print", uses=(0,)), inst("add", 1, uses=(1, 0)), inst("return", uses=(2,))]), "FIR_TYPE"
    yield "reject-negative-use", module([inst("add", 1, uses=(-1, -1)), r]), "FIR_DOMINANCE"
    yield "reject-branch-condition", module([c, inst("branch", data=(0, 0, 0), uses=(0,))]), "FIR_TYPE"
    yield "reject-call-arity", module([c, inst("call", 1, data=(0,), uses=(0,)), inst("return", uses=(1,))]), "FIR_CALL"
    yield "reject-call-result", module([inst("call", 2, data=(0,)), c, inst("return", uses=(1,))]), "FIR_TYPE"
    yield "reject-unknown-blob", module([inst("string", 3, data=(999,)), c, inst("return", uses=(1,))]), "FIR_LITERAL"
    yield "reject-unknown-field", module([c, inst("struct", STRUCT, uses=(0,)), inst("field", 1, data=(9,), uses=(1,)), inst("return", uses=(2,))], structs=[(1,)]), "FIR_TYPE"
    yield "reject-site-file", module([c, r]).replace("site 0 1 1", "site 999 1 1"), "FIR_SITE"
    shapes = [(1,)] + [(STRUCT + i - 1, STRUCT + i - 1) for i in range(1, 21)]
    huge = module([c, r], structs=shapes).replace("functions 1", "functions 2")
    params = " ".join([str(STRUCT + 20)] * 129)
    callee = f"function 0 129 {params} 0 1\nblock 129 {params} 1\n" + inst("return") + "\n"
    yield "reject-frame-displacement", huge.replace("end\n", callee + "end\n"), "FIR_LAYOUT"
    yield from grown()


def grown():
    """FIR 1: sized integers, slots, rendering and the assert trap."""
    c = inst("const", 1, data=(0,))
    r = inst("return", uses=(0,))
    kinds = [(INT, -9223372036854775808, 9223372036854775807), (I32, -2147483648, 2147483647),
             (I64, -9223372036854775808, 9223372036854775807), (U8, 0, 255), (U64, 0, -1), (UINT, 0, -1)]
    body = [c]
    for ty, low, high in kinds:
        a = len(body)
        body += [inst("const", ty, data=(low,)), inst("const", ty, data=(high,))]
        for op in ("add", "sub", "mul", "div", "rem"):
            body.append(inst(op, ty, uses=(a, a + 1)))
        body += [inst("eq", BOOL, uses=(a, a + 1)), inst("lt", BOOL, uses=(a, a + 1)), inst("not", ty, uses=(a,))]
    body.append(r)
    yield "roundtrip-sized-integers", module(body), None
    yield "roundtrip-slots", module([c, inst("store", data=(0, 1, 0), uses=(0,)), inst("load", INT, data=(0, 1, 0)), inst("load", STRUCT + 1, data=(0,)), inst("store", data=(1,), uses=(3,)), inst("return", uses=(2,))], structs=[(INT, STR), (BOOL, STRUCT, U8)], slots=(STRUCT + 1, STRUCT + 1)), None
    yield "roundtrip-format", module([c, inst("const", U64, data=(-1,)), inst("const", BOOL, data=(1,)), inst("string", STR, data=(1,)), inst("format", STR, uses=(0, 1, 2, 3)), inst("print", uses=(4,)), inst("return", uses=(0,))]), None
    yield "roundtrip-assert", module([inst("string", STR, data=(1,)), inst("trap", data=(4,), uses=(0,))]), None
    yield "roundtrip-assert-bare", module([inst("trap", data=(4,))]), None
    yield "roundtrip-empty-struct", module([inst("struct", STRUCT), inst("struct", STRUCT + 1, uses=(0,)), c, inst("return", uses=(2,))], structs=[(), (STRUCT,)]), None
    yield "roundtrip-str-eq-lt", module([inst("string", STR, data=(1,)), inst("eq", BOOL, uses=(0, 0)), inst("lt", BOOL, uses=(0, 0)), inst("eq", BOOL, uses=(1, 2)), c, inst("return", uses=(4,))]), None
    yield "reject-fir-0", module([c, r]).replace("fir 1", "fir 0"), "FIR_SYNTAX"
    yield "reject-u8-literal", module([inst("const", U8, data=(256,)), c, inst("return", uses=(1,))]), "FIR_LITERAL"
    yield "reject-u8-negative-literal", module([inst("const", U8, data=(-1,)), c, inst("return", uses=(1,))]), "FIR_LITERAL"
    yield "reject-i32-literal", module([inst("const", I32, data=(2147483648,)), c, inst("return", uses=(1,))]), "FIR_LITERAL"
    yield "reject-mixed-kinds", module([inst("const", I32, data=(1,)), c, inst("add", I32, uses=(0, 1)), inst("return", uses=(1,))]), "FIR_TYPE"
    yield "reject-arith-result", module([inst("const", U64, data=(1,)), inst("add", UINT, uses=(0, 0)), c, inst("return", uses=(2,))]), "FIR_TYPE"
    yield "reject-lt-bool", module([inst("const", BOOL, data=(1,)), inst("lt", BOOL, uses=(0, 0)), c, inst("return", uses=(2,))]), "FIR_TYPE"
    yield "reject-eq-mixed", module([inst("string", STR, data=(1,)), c, inst("eq", BOOL, uses=(0, 1)), inst("return", uses=(1,))]), "FIR_TYPE"
    yield "reject-not-str", module([inst("string", STR, data=(1,)), inst("not", STR, uses=(0,)), c, inst("return", uses=(2,))]), "FIR_TYPE"
    yield "reject-not-result", module([inst("const", U8, data=(1,)), inst("not", INT, uses=(0,)), inst("return", uses=(1,))]), "FIR_TYPE"
    yield "reject-format-empty", module([inst("format", STR), c, inst("return", uses=(1,))]), "FIR_ARITY"
    yield "reject-format-struct", module([c, inst("struct", STRUCT, uses=(0,)), inst("format", STR, uses=(1,)), inst("return", uses=(0,))], structs=[(INT,)]), "FIR_TYPE"
    yield "reject-unknown-slot", module([inst("load", INT, data=(1,)), inst("return", uses=(0,))], slots=(INT,)), "FIR_SLOT"
    yield "reject-slot-path", module([inst("load", INT, data=(0, 0)), inst("return", uses=(0,))], slots=(INT,)), "FIR_TYPE"
    yield "reject-slot-field", module([inst("load", INT, data=(0, 2)), inst("return", uses=(0,))], structs=[(INT, BOOL)], slots=(STRUCT,)), "FIR_TYPE"
    yield "reject-load-result", module([inst("load", BOOL, data=(0,)), c, inst("return", uses=(1,))], slots=(INT,)), "FIR_TYPE"
    yield "reject-store-type", module([inst("const", BOOL, data=(1,)), inst("store", data=(0,), uses=(0,)), c, inst("return", uses=(2,))], slots=(INT,)), "FIR_TYPE"
    yield "reject-store-arity", module([c, inst("store", data=(0,)), inst("return", uses=(0,))], slots=(INT,)), "FIR_ARITY"
    yield "reject-unit-slot", module([c, r], slots=(UNIT,)), "FIR_TYPE"
    yield "reject-trap-message-kind", module([inst("string", STR, data=(1,)), inst("trap", data=(1,), uses=(0,))]), "FIR_TRAP"
    yield "reject-assert-message-type", module([c, inst("trap", data=(4,), uses=(0,))]), "FIR_TYPE"
    yield "reject-trap-kind-5", module([inst("trap", data=(5,))]), "FIR_TRAP"
    yield "reject-assert-kind-9", module([inst("string", STR, data=(1,)), inst("trap", data=(9,), uses=(0,))]), "FIR_TRAP"
    yield "reject-list-field", module([c, r], structs=[(LIST,)]), "FIR_TYPE"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("compiler", type=pathlib.Path)
    ap.add_argument("--scratch", type=pathlib.Path, required=True)
    ap.add_argument("--keep-going", action="store_true", help="name every failing row, then fail")
    a = ap.parse_args()
    failed = []
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
                if not a.keep_going:
                    raise
                failed.append(name)
                continue
            print(f"PASS {name}", flush=True)
    if failed:
        raise SystemExit(f"{len(failed)} FIR rows failed")


if __name__ == "__main__":
    main()
