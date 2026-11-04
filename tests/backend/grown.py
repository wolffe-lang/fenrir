#!/usr/bin/env python3
"""FIR 1 fixtures: hand-written FIR beside an equivalent Wolf program.

Each fixture is (name, FIR text, expected stdout or "trap:KIND", Wolf twin).
The expected values are computed here from the integer rules as the
specification states them; the Linux differential also checks every one
against the pinned wolf, so this table is never the only witness.
"""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("fir_rows", Path(__file__).with_name("fir.py"))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
I = f.inst

KINDS = {f.INT: ("int", 64, True), f.I32: ("i32", 32, True), f.I64: ("i64", 64, True),
         f.U8: ("u8", 8, False), f.U64: ("u64", 64, False), f.UINT: ("uint", 64, False)}


def bounds(ty):
    _, bits, signed = KINDS[ty]
    return (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed else (0, (1 << bits) - 1)


def pattern(ty, value):
    """The FIR literal: the value's 64-bit two's-complement pattern."""
    low, high = bounds(ty)
    assert low <= value <= high, (ty, value)
    return value - (1 << 64) if value >= 1 << 63 else value


def apply(ty, op, a, b):
    """The checked result, or the trap kind it raises."""
    low, high = bounds(ty)
    if op in ("div", "rem"):
        if b == 0:
            return "div-zero"
        quotient = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)
        exact = quotient if op == "div" else a - b * quotient
        if not low <= quotient <= high:
            return "overflow"
        return exact
    if op == "not":
        return -a - 1 if KINDS[ty][2] else high - a
    if op in ("eq", "lt"):
        return (a == b) if op == "eq" else (a < b)
    exact = {"add": a + b, "sub": a - b, "mul": a * b}[op]
    return exact if low <= exact <= high else "overflow"


SPELLING = {"add": "+", "sub": "-", "mul": "*", "div": "/", "rem": "%", "eq": "==", "lt": "<"}


def render(value):
    return ("true" if value else "false") if isinstance(value, bool) else str(value)


def module(body, blobs=(), structs=(), slots=(), blocks=None, functions=()):
    """fir.module with extra blobs (ids 2 and up) and extra functions."""
    text = f.module(body, structs=structs, slots=slots, blocks=blocks)
    if blobs:
        extra = "".join(f"blob {b.encode().hex() if b else '-'}\n" for b in blobs)
        text = text.replace("blobs 2\n", f"blobs {2 + len(blobs)}\n").replace("sites 1\n", extra + "sites 1\n")
    if functions:
        text = text.replace("functions 1\n", f"functions {1 + len(functions)}\n").replace("end\n", "".join(functions) + "end\n")
    return text


def values():
    """Every non-trapping operation at each kind's edges, one line each."""
    cases = []
    for ty in KINDS:
        low, high = bounds(ty)
        mid = 7
        rows = [("sub", high, mid), ("add", low, mid), ("mul", mid, 3), ("div", high, mid), ("rem", high, mid),
                ("eq", high, low), ("lt", low, high), ("lt", high, low), ("not", low, 0), ("not", mid, 0)]
        if KINDS[ty][2]:
            rows += [("mul", mid, -3), ("div", low, -mid), ("rem", low, mid), ("rem", -mid, 2), ("div", low + 1, -1)]
        else:
            rows += [("div", high, 1), ("rem", mid, high), ("sub", high, high)]
        cases += [(ty, op, a, b) for op, a, b in rows]
    body, lines, wolf = [], [], ["fn main() {"]
    for i, (ty, op, a, b) in enumerate(cases):
        result = apply(ty, op, a, b)
        assert not isinstance(result, str) or isinstance(result, bool), (ty, op, a, b, result)
        at = len(body)
        body += [I("const", ty, data=(pattern(ty, a),)), I("const", ty, data=(pattern(ty, b),))]
        rty = f.BOOL if op in ("eq", "lt") else ty
        body.append(I(op, rty, uses=(at,)) if op == "not" else I(op, rty, uses=(at, at + 1)))
        body += [I("format", f.STR, uses=(at + 2,)), I("print", uses=(at + 3,))]
        lines.append(render(result))
        name = KINDS[ty][0]
        wolf += [f"    let a{i}: {name} = {a}", f"    let b{i}: {name} = {b}"]
        expression = f"!a{i}" if op == "not" else f"a{i} {SPELLING[op]} b{i}"
        wolf.append(f'    print("{{{expression}}}")')
    body += [I("const", 1, data=(0,)), I("return", uses=(len(body),))]
    return module(body), "".join(line + "\n" for line in lines), "\n".join(wolf + ["}", ""])


def trap_case(ty, op, a, b):
    result = apply(ty, op, a, b)
    assert result in ("overflow", "div-zero"), (ty, op, a, b, result)
    name = KINDS[ty][0]
    body = [I("const", ty, data=(pattern(ty, a),)), I("const", ty, data=(pattern(ty, b),)), I(op, ty, uses=(0, 1)),
            I("const", 1, data=(0,)), I("return", uses=(3,))]
    wolf = f'fn calculate(a: {name}, b: {name}) -> {name} {{ a {SPELLING[op]} b }}\nfn main() {{ print("{{calculate({a}, {b})}}") }}\n'
    return module(body), "trap:" + result, wolf


def negate(ty, a):
    """Negation is `0 - a` in the kind: a signed MIN and any nonzero unsigned trap."""
    name = KINDS[ty][0]
    body = [I("const", ty, data=(0,)), I("const", ty, data=(pattern(ty, a),)), I("sub", ty, uses=(0, 1)),
            I("const", 1, data=(0,)), I("return", uses=(3,))]
    wolf = f'fn negate(a: {name}) -> {name} {{ -a }}\nfn main() {{ print("{{negate({a})}}") }}\n'
    return module(body), "trap:" + apply(ty, "sub", 0, a), wolf


def fixtures():
    yield ("values", *values())
    for ty, op, a, b in [(f.I32, "add", 2147483647, 1), (f.I32, "mul", -2147483648, 2), (f.I32, "div", -2147483648, -1),
                         (f.I32, "rem", -2147483648, -1), (f.I64, "rem", -9223372036854775808, -1),
                         (f.U8, "add", 255, 1), (f.U8, "sub", 0, 1), (f.U8, "mul", 16, 16), (f.U8, "div", 7, 0),
                         (f.U64, "add", (1 << 64) - 1, 1), (f.U64, "sub", 1, 2), (f.U64, "mul", 1 << 32, 1 << 32),
                         (f.U64, "rem", 9, 0), (f.UINT, "sub", 0, 1)]:
        yield (f"trap-{op}-{KINDS[ty][0]}", *trap_case(ty, op, a, b))
    yield ("negate-u8", *negate(f.U8, 3))
    yield ("negate-i32-min", *negate(f.I32, -2147483648))
    # assert traps kind 9; the evaluated message is carried, not printed, as the
    # pinned reference prints none in an ordinary build.
    yield ("assert", module([I("trap", data=(9,))]), "trap:assert",
           'fn check(c: bool) { assert(c) }\nfn main() { check(false) }\n')
    yield ("assert-message", module([I("string", 3, data=(1,)), I("trap", data=(9,), uses=(0,))]), "trap:assert",
           'fn check(c: bool, m: str) { assert(c, m) }\nfn main() { check(false, "hello, wolf") }\n')
    # One buffer renders a signed, an unsigned, a bool and a str part in order.
    yield ("format", module([I("const", f.INT, data=(-5,)), I("const", f.U64, data=(-1,)), I("const", f.BOOL, data=(1,)),
                             I("string", 3, data=(1,)), I("format", 3, uses=(0, 1, 2, 3)), I("print", uses=(4,)),
                             I("const", 1, data=(0,)), I("return", uses=(6,))]),
           "-518446744073709551615truehello, wolf\n",
           'fn main() {\n    let a: int = -5\n    let b: u64 = 18446744073709551615\n    let c = true\n    let d = "hello, wolf"\n    print("{a}{b}{c}{d}")\n}\n')
    # A struct with str, u8 and bool fields, rendered from its parts as a hole renders it.
    pieces = ["P { n: ", ", s: ", ", u: ", ", b: ", " }", "hi"]
    shape = (f.INT, f.STR, f.U8, f.BOOL)
    body = [I("const", f.INT, data=(-1,)), I("string", 3, data=(7,)), I("const", f.U8, data=(200,)), I("const", f.BOOL, data=(1,)),
            I("struct", f.STRUCT, uses=(0, 1, 2, 3))]
    body += [I("field", ty, data=(k,), uses=(4,)) for k, ty in enumerate(shape)]
    body += [I("string", 3, data=(2 + k,)) for k in range(5)]
    body += [I("format", 3, uses=(9, 5, 10, 6, 11, 7, 12, 8, 13)), I("print", uses=(14,)), I("const", 1, data=(0,)), I("return", uses=(16,))]
    yield ("struct-render", module(body, blobs=pieces, structs=[shape]), "P { n: -1, s: hi, u: 200, b: true }\n",
           'struct P { n: int, s: str, u: u8, b: bool }\nfn main() {\n    let p = P { n: -1, s: "hi", u: 200, b: true }\n    print("{p}")\n}\n')
    # A counter kept in a stack slot instead of block parameters, and an empty
    # struct value. The reference refuses an empty struct as a parameter or a
    # field (unit-typed there), so this fixture only builds one.
    loop = [([], [I("const", 1, data=(0,)), I("store", data=(0,), uses=(0,)), I("jump", data=(1,))]),
            ([], [I("load", 1, data=(0,)), I("const", 1, data=(5,)), I("lt", 2, uses=(0, 1)), I("branch", data=(2, 3, 0), uses=(2,))]),
            ([], [I("load", 1, data=(0,)), I("print", uses=(0,)), I("const", 1, data=(1,)), I("add", 1, uses=(0, 2)),
                  I("store", data=(0,), uses=(3,)), I("jump", data=(1,))]),
            ([], [I("struct", f.STRUCT), I("const", 1, data=(0,)), I("return", uses=(1,))])]
    yield ("slots", module([], blocks=loop, slots=(f.INT,), structs=[()]), "0\n1\n2\n3\n4\n",
           'struct E {}\nfn main() {\n    var i: int = 0\n    while i < 5 { print("{i}"); i += 1 }\n    let e = E {}\n}\n')
    # str equality is bytewise and order is byte order.
    words = ["abc", "abd", "b", "abc"]
    body = [I("string", 3, data=(2 + k,)) for k in range(4)]
    tests = [("eq", 0, 3), ("eq", 0, 1), ("lt", 0, 1), ("lt", 2, 0), ("lt", 1, 0), ("lt", 0, 3)]
    for op, x, y in tests:
        at = len(body)
        body += [I(op, 2, uses=(x, y)), I("format", 3, uses=(at,)), I("print", uses=(at + 1,))]
    body += [I("const", 1, data=(0,)), I("return", uses=(len(body),))]
    twin = ["fn main() {"] + [f'    let w{k} = "{w}"' for k, w in enumerate(words)]
    twin += [f'    print("{{w{x} {SPELLING[op]} w{y}}}")' for op, x, y in tests] + ["}", ""]
    expected = "".join(render((words[x] == words[y]) if op == "eq" else (words[x].encode() < words[y].encode())) + "\n" for op, x, y in tests)
    yield ("str-compare", module(body, blobs=words), expected, "\n".join(twin))


if __name__ == "__main__":
    for name, text, expected, wolf in fixtures():
        print(f"== {name}: {expected!r}\n{wolf}")
