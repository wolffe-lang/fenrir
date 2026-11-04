#!/usr/bin/env python3
"""Lowering rows: one Wolf program per core construct, trap and order.

Each row is (name, source, expected), where expected is the exact stdout of a
program that exits 0, or "exit:N" after STDOUT for another status, or
"trap:KIND" after STDOUT for a trap. The pinned wolf must agree with every
expectation (the preflight), and on Linux the program fenrir builds must equal
the program the pinned wolf builds from the same file, byte for byte in stdout
and stderr (the trap line and its site) and in its status.
"""

ROWS = []


def row(name, source, stdout="", status=None, trap=None):
    ROWS.append((name, source, stdout, status, trap))


# ---- values and operators -------------------------------------------------
row("hello", 'fn main() { print("hello, wolf") }\n', "hello, wolf\n")
row("literals", '''fn main() {
    let a = 0x7f
    let b: int = 0b1010_1010
    let c: u8 = 0o17
    let d: u64 = 18446744073709551615
    let e = -2147483648
    let f: int = -9223372036854775808
    print("{a} {b} {c} {d} {e} {f} {true} {false}")
}
''', "127 170 15 18446744073709551615 -2147483648 -9223372036854775808 true false\n")
WIDTH = {"int": (64, True), "i32": (32, True), "i64": (64, True), "u8": (8, False), "u64": (64, False), "uint": (64, False)}


def arith(kind, a, b):
    """The expected line, from the checked rules (none of these trap)."""
    bits, signed = WIDTH[kind]
    quotient = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)
    complement = -b - 1 if signed else (1 << bits) - 1 - b
    parts = [a + b, a - b, quotient, a - b * quotient, b * b, a == b, a != b, a < b, a <= b, a > b, a >= b, complement]
    return " ".join(("true" if x else "false") if isinstance(x, bool) else str(x) for x in parts) + "\n"


for kind, a, b in [("int", 9000000000, -7), ("i32", 2000000000, -7), ("i64", -9000000000, 7), ("u8", 200, 7), ("u64", 18000000000000000000, 7), ("uint", 4000000000, 7)]:
    row(f"arith-{kind}", f'''fn main() {{
    let a: {kind} = {a}
    let b: {kind} = {b}
    print("{{a + b}} {{a - b}} {{a / b}} {{a % b}} {{b * b}} {{a == b}} {{a != b}} {{a < b}} {{a <= b}} {{a > b}} {{a >= b}} {{!b}}")
}}
''', arith(kind, a, b))
row("str-ops", '''fn main() {
    let a = "wolf"
    let b = "pack"
    var c = a + " " + b
    c += "!"
    print(c)
    print("{a == b} {a != b} {a < b} {b < a} {a <= a} {a >= b}")
}
''', "wolf pack!\nfalse true false true true true\n")
row("bool-ops", '''fn main() {
    let t = true
    let f = !t
    print("{t == f} {t != f} {!f} {t && f} {t || f}")
}
''', "false true true false true\n")
row("negation", '''fn neg(x: int) -> int { -x }
fn main() {
    let a: i32 = 5
    print("{-a} {neg(7)} {-(-3)}")
}
''', "-5 -7 3\n")

# ---- control --------------------------------------------------------------
row("if-value", '''fn sign(x: int) -> str { if x < 0 { "neg" } else if x == 0 { "zero" } else { "pos" } }
fn main() {
    let v = if 3 > 2 then 10 else 20
    print("{sign(-5)} {sign(0)} {sign(9)} {v}")
}
''', "neg zero pos 10\n")
row("if-statement", '''fn main() {
    var n = 0
    if n == 0 { n += 5 }
    if n > 10 { n = 0 } else { n += 1 }
    print("{n}")
}
''', "6\n")
row("while-break-continue", '''fn main() {
    var i = 0
    var total = 0
    while true {
        i += 1
        if i > 10 { break }
        if i % 2 == 0 { continue }
        total += i
    }
    print("{i} {total}")
}
''', "11 25\n")
row("nested-loops", '''fn main() {
    var i = 0
    var count = 0
    while i < 4 {
        var j = 0
        while j < 4 { if j == i { break }; count += 1; j += 1 }
        i += 1
    }
    print("{count}")
}
''', "6\n")
row("return-early", '''fn first(limit: int) -> int {
    var i = 0
    while i < 100 { if i * i > limit { return i }; i += 1 }
    -1
}
fn main() { print("{first(50)} {first(100000)}") }
''', "8 -1\n")
row("never-branch", '''fn pick(c: bool) -> int { if c { return 1 } else { 2 } }
fn main() { print("{pick(true)} {pick(false)}") }
''', "1 2\n")
row("recursion", '''fn fib(n: int) -> int { if n < 2 { return n }; fib(n - 1) + fib(n - 2) }
fn main() { print("{fib(20)}") }
''', "6765\n")
row("block-value", '''fn main() {
    let x = { let a = 2; let b = 3; a * b }
    print("{x}")
}
''', "6\n")
row("shadowing", '''fn main() {
    let x = 1
    let x = x + 1
    var y = x
    { let y = 100; print("{y}") }
    y += 1
    print("{x} {y}")
}
''', "100\n2 3\n")

# ---- structs and strings ---------------------------------------------------
row("struct-fields", '''struct Point { x: int, y: int }
struct Line { a: Point, b: Point, name: str }
fn length2(l: Line) -> int { let dx = l.b.x - l.a.x; let dy = l.b.y - l.a.y; dx * dx + dy * dy }
fn shift(p: Point, d: int) -> Point { Point { x: p.x + d, y: p.y + d } }
fn main() {
    var l = Line { a: Point { x: 0, y: 0 }, b: Point { x: 3, y: 4 }, name: "diag" }
    print("{length2(l)}")
    l.b.x = 6
    l.a = shift(l.a, 1)
    l.b.y += 4
    l.name = "renamed"
    print("{l}")
    let start = l.a
    print("{start.x} {start}")
}
''', "25\nLine { a: Point { x: 1, y: 1 }, b: Point { x: 6, y: 8 }, name: renamed }\n1 Point { x: 1, y: 1 }\n")
row("struct-shorthand-order", '''struct P { a: int, b: str, c: bool }
fn main() {
    let a = 7
    let b = "s"
    let p = P { c: true, b, a }
    print("{p}")
}
''', "P { a: 7, b: s, c: true }\n")
row("interp-kinds", '''struct Unit {}
struct S { u: u8, w: u64, t: str }
fn nothing() {}
fn main() {
    let s = S { u: 255, w: 18446744073709551615, t: "x" }
    let e = Unit {}
    print("<{nothing()}> {s} {e} {s.t}{s.u}")
}
''', "<()> S { u: 255, w: 18446744073709551615, t: x } Unit { } x255\n")
row("strings", '''fn main() {
    let raw = r"a {b} \\n"
    let multi = """
        two
        lines
        """
    print(raw)
    print(multi)
    print("{{braces}} \\t tab")
}
''', "a {b} \\n\ntwo\nlines\n\n{braces} \t tab\n")

# ---- main's status ---------------------------------------------------------
row("main-int", 'fn main() -> int { print("x"); 300 }\n', "x\n", status=44)
row("main-negative", 'fn main() -> int { -1 }\n', "", status=255)
row("main-result-int", 'fn main() -> !int { 7 }\n', "", status=7)
row("main-result-unit", 'fn main() -> !() { print("u") }\n', "u\n")
row("main-return", 'fn main() -> int { if true { return 3 }; 4 }\n', "", status=3)

# ---- traps at their sites --------------------------------------------------
row("trap-add-tail", 'fn add(a: int, b: int) -> int { a + b }\nfn main() { print("{add(9223372036854775807, 1)}") }\n', trap="overflow")
row("trap-sub-i32", 'fn main() {\n    let a: i32 = -2147483648\n    let b = a - 1\n    print("{b}")\n}\n', trap="overflow")
row("trap-mul-u8", 'fn main() {\n    var x: u8 = 16\n    x *= 16\n    print("{x}")\n}\n', trap="overflow")
row("trap-neg-u8", 'fn neg(x: u8) -> u8 { -x }\nfn main() { print("{neg(1)}") }\n', trap="overflow")
row("trap-neg-min", 'fn neg(x: int) -> int { -x }\nfn main() { print("before"); print("{neg(-9223372036854775807 - 1)}") }\n', "before\n", trap="overflow")
row("trap-in-if-condition", 'fn main() {\n    var x: int = 9223372036854775807\n    if x + 1 > 0 { print("no") }\n}\n', trap="overflow")
row("trap-in-while-header", 'fn main() {\n    var i: u8 = 250\n    while i + 10 > 0 {\n        i += 1\n    }\n}\n', trap="overflow")
row("trap-in-return-operand", 'fn f(x: int) -> int {\n    if x > 0 {\n        return x * 4611686018427387904\n    }\n    0\n}\nfn main() { print("{f(2)}") }\n', trap="overflow")
row("trap-in-argument", 'fn id(x: i32) -> i32 { x }\nfn main() {\n    let a: i32 = 2147483647\n    print("{id(a + 1)}")\n}\n', trap="overflow")
row("trap-in-field-init", 'struct P { a: int }\nfn main() {\n    let m: int = 9223372036854775807\n    let p = P { a: m + 1 }\n    print("{p.a}")\n}\n', trap="overflow")
row("trap-div-zero", 'fn div(a: int, b: int) -> int { a / b }\nfn main() { print("start"); print("{div(1, 0)}") }\n', "start\n", trap="div-zero")
row("trap-rem-zero-u64", 'fn main() {\n    let a: u64 = 5\n    let b: u64 = 0\n    print("{a % b}")\n}\n', trap="div-zero")
row("trap-min-div", 'fn main() {\n    let a: i64 = -9223372036854775808\n    let b: i64 = -1\n    print("{a / b}")\n}\n', trap="overflow")
row("trap-min-rem-i32", 'fn main() {\n    let a: i32 = -2147483648\n    var b: i32 = 0\n    b -= 1\n    print("{a % b}")\n}\n', trap="overflow")
row("trap-assert", 'fn main() {\n    print("one")\n    assert(1 + 1 == 3)\n    print("two")\n}\n', "one\n", trap="assert")
row("trap-assert-message", 'fn check(n: int) {\n    assert(n < 3, "too big: {n}")\n}\nfn main() { check(1); check(5) }\n', trap="assert")

# ---- evaluation order (side effects visible) -------------------------------
SIDE = 'fn side(tag: str, v: int) -> int { print(tag); v }\nfn yes(tag: str) -> bool { print(tag); true }\nfn no(tag: str) -> bool { print(tag); false }\n'
row("order-operands", SIDE + 'fn main() { let r = side("a", 1) + side("b", 2) * side("c", 3); print("{r}") }\n', "a\nb\nc\n7\n")
row("order-arguments", SIDE + 'fn three(a: int, b: int, c: int) -> int { a * 100 + b * 10 + c }\nfn main() { print("{three(side("x", 1), side("y", 2), side("z", 3))}") }\n', "x\ny\nz\n123\n")
row("order-and-short", SIDE + 'fn main() { let r = no("left") && yes("right"); print("{r}") }\n', "left\nfalse\n")
row("order-or-short", SIDE + 'fn main() { let r = yes("left") || no("right"); print("{r}") }\n', "left\ntrue\n")
row("order-and-both", SIDE + 'fn main() { let r = yes("left") && no("right"); print("{r}") }\n', "left\nright\nfalse\n")
row("order-struct-init", SIDE + 'struct P { a: int, b: int, c: int }\nfn main() { let p = P { c: side("c", 3), a: side("a", 1), b: side("b", 2) }; print("{p}") }\n', "c\na\nb\nP { a: 1, b: 2, c: 3 }\n")
row("order-interpolation", SIDE + 'fn main() { print("{side("h1", 1)}-{side("h2", 2)}") }\n', "h1\nh2\n1-2\n")
row("order-assert-message", SIDE + 'fn msg(t: str) -> str { print(t); t }\nfn main() { assert(true, msg("not evaluated")); print("held"); assert(false, msg("evaluated")) }\n', "held\nevaluated\n", trap="assert")
row("order-compound", SIDE + 'fn main() { var x = side("read", 10); x -= side("rhs", 3); print("{x}") }\n', "read\nrhs\n7\n")
row("order-split-operand", SIDE + 'fn main() { let r = side("l", 1) + (if yes("c") { side("t", 10) } else { 0 }) + side("r", 100); print("{r}") }\n', "l\nc\nt\nr\n111\n")
row("order-split-argument", SIDE + 'fn two(a: int, b: bool) -> int { if b { a } else { 0 - a } }\nfn main() { print("{two(side("a", 5), no("p") || yes("q"))}") }\n', "a\np\nq\n5\n")


def rows():
    for name, source, stdout, status, trap in ROWS:
        yield name, source, stdout, status, trap
