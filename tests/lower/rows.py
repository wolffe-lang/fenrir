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


# ---- enums and match --------------------------------------------------------
row("match-enum-payloads", """enum Shape { Dot, Square(int), Rect(int, int), Named(str) }
fn area(s: Shape) -> int {
    match s {
        Dot => 0,
        Square(n) => n * n,
        Rect(w, h) => w * h,
        Named(_) => -1,
    }
}
fn main() {
    print("{area(Shape.Dot)} {area(Shape.Square(4))} {area(Shape.Rect(2, 5))} {area(Shape.Named("x"))}")
}
""", "0 16 10 -1\n")
row("match-int-guards-ranges", """fn class(n: int) -> str {
    match n {
        0 => "zero",
        x if x < 0 => "negative",
        1..=9 => "digit",
        10..100 => "small",
        _ => "large",
    }
}
fn main() { print("{class(0)} {class(-5)} {class(7)} {class(42)} {class(100)}") }
""", "zero negative digit small large\n")
row("match-struct-fields", """struct P { on: bool, n: int }
fn f(p: P) -> int {
    match p {
        P { on: true, n: 0 } => 1,
        P { on: true, n } => n + 10,
        P { on: false, .. } => 2,
    }
}
fn main() { print("{f(P { on: true, n: 0 })} {f(P { on: true, n: 5 })} {f(P { on: false, n: 9 })}") }
""", "1 15 2\n")
row("match-str-alternatives", """fn op(t: str) -> int {
    match t {
        "+" | "plus" => 1,
        "-" => 2,
        _ => 9,
    }
}
fn main() { print("{op("+")} {op("plus")} {op("-")} {op("x")}") }
""", "1 1 2 9\n")
row("match-nested-enums", """enum Inner { A, B(int) }
enum Outer { Wrap(Inner), Pair(Inner, Inner), Empty }
fn f(v: Outer) -> int {
    match v {
        Wrap(B(n)) => n,
        Wrap(A) => 100,
        Pair(B(x), B(y)) => x + y,
        Pair(_, _) => 200,
        Empty => -1,
    }
}
fn main() {
    print("{f(Outer.Wrap(Inner.B(7)))} {f(Outer.Wrap(Inner.A))} {f(Outer.Pair(Inner.B(1), Inner.B(2)))} {f(Outer.Pair(Inner.A, Inner.B(2)))} {f(Outer.Empty)}")
}
""", "7 100 3 200 -1\n")
row("match-loop-statement", """enum Step { Inc(int), Dec(int), Stop }
fn apply(n: int, s: Step) -> int {
    match s {
        Inc(k) => n + k,
        Dec(k) => {
            k = k * 2
            n - k
        },
        Stop => n,
    }
}
fn main() {
    var n = 0
    var i = 0
    while i < 5 {
        let s = if i == 4 then Step.Stop else if i % 2 == 0 then Step.Inc(i + 1) else Step.Dec(i)
        n = apply(n, s)
        match s {
            Stop => print("stop at {n}"),
            _ => {},
        }
        i += 1
    }
    print("{n}")
}
""", "stop at -4\n-4\n")
row("match-trap-in-arm", 'fn f(n: int) -> int { match n { 0 => 10 / n, _ => n } }\nfn main() { print("{f(3)}"); print("{f(0)}") }\n', "3\n", trap="div-zero")
row("order-match", SIDE + """enum E { A(int, int), B }
fn main() {
    let v = E.A(side("x", 1), side("y", 2))
    let r = match side("scrutinee", 5) {
        n if yes("guard1") && n > 9 => 0,
        n if yes("guard2") => n,
        _ => -1,
    }
    match v { A(a, b) => print("{a + b + r}"), B => print("b") }
}
""", "x\ny\nscrutinee\nguard1\nguard2\n8\n")



# ---- lists, maps and error rows ---------------------------------------------
row("list-basics", """fn main() {
    var xs = [3, 1, 4]
    (mut xs).push(1)
    xs[1] = 5
    var total = 0
    for x in xs { total += x }
    let last = (mut xs).pop() else -1
    print("{xs} {xs.len} {total} {last} {xs.is_empty()}")
}
""", "[3, 5, 4] 3 13 1 false\n")
row("list-strs-structs", """struct P { x: int, y: int }
fn main() {
    var ps = [P { x: 1, y: 2 }]
    (mut ps).push(P { x: 3, y: 4 })
    let names = ["wolf", "pack"]
    print("{ps} {names} {names[1]} {ps[1].x + ps[1].y} {ps.len}")
}
""", '[P { x: 1, y: 2 }, P { x: 3, y: 4 }] ["wolf", "pack"] pack 7 2\n')
row("list-nested-copy", """fn main() {
    var grid = [[1, 2], [3]]
    var inner = [5]
    (mut grid).push(inner)
    (mut inner).push(6)
    print("{grid} {inner} {grid[2].len}")
}
""", "[[1, 2], [3], [5]] [5, 6] 1\n")
row("list-slice-methods", """fn main() {
    var xs = [10, 20, 30, 40]
    let ys = xs[1..3]
    let first = xs.first() else 0
    let final = xs.last() else 0
    let got = xs.get(9) else -1
    (mut xs).clear()
    print("{ys} {first} {final} {got} {xs.len} {xs.is_empty()}")
}
""", "[20, 30] 10 40 -1 0 true\n")
row("list-index-trap", """fn main() {
    let xs = [1, 2, 3]
    var i = 0
    while i < 4 {
        print("{xs[i]}")
        i += 1
    }
}
""", "1\n2\n3\n", trap="bounds")
row("list-store-trap", SIDE + """fn main() {
    var xs = [1, 2, 3]
    xs[side("index", 1)] = side("value", 7)
    print("{xs}")
    xs[side("index", 3)] = side("value", 8)
    print("unreached")
}
""", "index\nvalue\n[1, 7, 3]\nindex\nvalue\n", trap="bounds")
row("list-slice-trap", """fn cut(xs: List[int], lo: int, hi: int) -> List[int] { xs[lo..hi] }
fn main() {
    let xs = [1, 2, 3]
    print("{cut(xs, 0, 3)}")
    print("{cut(xs, 2, 1)}")
}
""", "[1, 2, 3]\n", trap="bounds")
row("map-basics", """fn main() {
    var m = Map[str, int]()
    m["b"] = 2
    m["a"] = 1
    m["b"] = 20
    let hit = m["b"] else 0
    let miss = m["z"] else -1
    for (k, v) in m.pairs() { print("{k}={v}") }
    print("{hit} {miss} {m.len} [{m["z"]}]")
}
""", "b=20\na=1\n20 -1 2 [none]\n")
row("map-int-keys-remove", """fn main() {
    var m = Map[int, str]()
    m[3] = "c"
    m[1] = "a"
    m[2] = "b"
    let gone = (mut m).remove(1) else "?"
    let again = (mut m).remove(1) else "?"
    print("{gone} {again} {m.len}")
    for (k, v) in m.pairs() { print("{k} {v}") }
    (mut m).clear()
    print("{m.len} {m.is_empty()}")
}
""", "a ? 2\n3 c\n2 b\n0 true\n")
row("map-list-values", """fn main() {
    var m = Map[str, List[int]]()
    m["a"] = [1]
    m["b"] = [2, 3]
    var a = m["a"] else List[int]()
    (mut a).push(4)
    let b = m["b"] else List[int]()
    m["a"] = [7]
    let a2 = m["a"] else List[int]()
    print("{a} {b.len} {a2} {m.len}")
}
""", "[1, 4] 2 [7] 2\n")
row("err-raise-handle", """fn digit(c: int) -> int ! {Bad(int), empty} {
    if c < 0 { return empty }
    if c > 9 { return Bad(c) }
    c
}
fn main() {
    let a = digit(4) else -1
    let b = digit(12) else |e| {
        match e {
            Bad(n) => n * 10,
            empty => -2,
        }
    }
    let c = digit(-1) else |e| match e { Bad(n) => n, empty => -2 }
    print("{a} {b} {c}")
}
""", "4 120 -2\n")
row("err-propagate-render", SIDE + """fn digit(c: int) -> int ! {Bad(int)} {
    if c > 9 { return Bad(c) }
    c
}
fn sum(a: int, b: int) -> int ! {Bad(int)} { digit(side("left", a))? + digit(side("right", b))? }
fn main() {
    print("{sum(1, 2)}")
    print("{sum(10, 2)}")
}
""", "left\nright\n3\nleft\nBad(10)\n")
row("err-main-unhandled", """fn check(n: int) -> int ! {TooBig(int)} {
    if n > 5 { return TooBig(n) }
    n
}
fn main() -> !int {
    print("start")
    let a = check(2)?
    let b = check(9)?
    print("unreached {a} {b}")
    0
}
""", "start\nerror: TooBig\n", status=1)
row("err-main-ok-status", """fn check(n: int) -> int ! {too_big} {
    if n > 5 { return too_big }
    n
}
fn main() -> !int { check(3)? }
""", "", status=3)

def rows():
    for name, source, stdout, status, trap in ROWS:
        yield name, source, stdout, status, trap
