"""Specification-first list, map, tuple and error-row typing cases.

`code` and `at` are the first error (line:column) as the pinned reference
reports it; the reference mode re-checks them. Accepted rows type with no
error on both. Codes the specification does not name (E0603, E0604, E0608,
E0804 and others) are the reference's, read black-box.
"""

# Locations recorded from the reference by `patterns.py --rows collection_rows --probe`.
AT = {
    'list-mixed': '2:18',
    'list-index-str': '3:21',
    'list-index-i32': '4:8',
    'list-push-no-mut': '3:5',
    'map-i32-key': '2:17',
    'map-struct-key': '3:17',
    'map-compound-absent': '3:5',
    'map-read-is-a-row': '3:5',
    'inferred-row-lowercase': '2:24',
    'try-not-fallible': '2:13',
    'try-in-infallible': '3:13',
    'try-escapes': '3:13',
    'try-payload-clash': '3:5',
    'else-not-fallible': '2:13',
    'tag-twice': '1:27',
    'nested-layer-clash': '1:37',
    'alias-loop': '2:12',
    'tag-variant-collision': '4:5',
    'row-operand': '2:24',
    'row-member': '2:20',
    'row-match-missing-tag': '3:5',
    'row-match-missing-value': '3:5',
    'tag-undeclared': '1:30',
    'handler-payload-partial': '5:31',
}


def row(name, source, code='', differs=''):
    at = AT.get(name)
    return dict(name=name, source=source + '\n', code=code, warnings=[], at=at, warn_at=[], differs=differs)


ROWS = [
    # Lists.
    row('list-literal-index-len', 'fn main() -> int {\n    let xs = [1, 2, 3]\n    let n: int = xs[1]\n    n + xs.len\n}'),
    row('list-adopts-later-use', 'fn use_int(v: int) -> int { v }\nfn main() -> int {\n    let ys = [5, 6]\n    use_int(ys[0])\n}'),
    row('list-constructor-push', 'fn main() -> int {\n    var xs = List[str]()\n    (mut xs).push("a")\n    xs.len\n}'),
    row('list-of-structs', 'struct P { a: int, b: str }\nfn main() -> int {\n    var xs = List[P]()\n    (mut xs).push(P { a: 1, b: "x" })\n    xs[0].a\n}'),
    row('list-nested', 'fn main() -> int {\n    var outer = List[List[int]]()\n    (mut outer).push([1, 2])\n    outer[0][1]\n}'),
    row('list-methods', 'fn main() -> int {\n    var xs = [4, 5]\n    let a = (mut xs).pop() else 0\n    let b = xs.get(0) else 0\n    let c = xs.first() else 0\n    let d = xs.last() else 0\n    if xs.is_empty() { return 9 }\n    (mut xs).clear()\n    a + b + c + d + xs.count() + xs.len()\n}'),
    row('list-slice', 'fn main() -> int {\n    let xs = [1, 2, 3, 4]\n    let ys = xs[1..3]\n    let zs = xs[0..=1]\n    ys.len + zs.len\n}'),
    row('list-store', 'fn main() -> int {\n    var xs = [1, 2]\n    xs[0] = 7\n    xs[1] += 3\n    xs[0] + xs[1]\n}'),
    row('list-mixed', 'fn main() -> int {\n    let xs = [1, "a"]\n    0\n}', 'E0401'),
    row('list-index-str', 'fn main() -> int {\n    let xs = [1, 2]\n    let n: int = xs["a"]\n    n\n}', 'E0401'),
    row('list-index-i32', 'fn main() -> int {\n    let xs = [1, 2]\n    let i: i32 = 1\n    xs[i]\n}', 'E0401'),
    row('list-push-no-mut', 'fn main() -> int {\n    var xs = List[int]()\n    xs.push(1)\n    xs.len\n}', 'E0804'),
    # for, tuples.
    row('for-range', 'fn main() -> int {\n    var t: int = 0\n    for i in 0..3 { t = t + i }\n    for j in 1..=2 { t = t + j }\n    t\n}'),
    row('for-list-break-continue', 'fn main() -> int {\n    var t = 0\n    for x in [1, 2, 3, 4] {\n        if x == 2 { continue }\n        if x == 4 { break }\n        t += x\n    }\n    t\n}'),
    row('tuple-values', 'fn pair() -> (int, str) { (34, "wolf") }\nfn main() -> int {\n    let (x, y) = pair()\n    let t = (5, (6, 7))\n    let (a, (b, c)) = t\n    x + t.0 + a + b + c\n}'),
    row('for-pairs', 'fn main() -> int {\n    var m = Map[str, int]()\n    m["a"] = 1\n    var t = 0\n    for p in m.pairs() { t += p.1 }\n    for (k, v) in m.pairs() { t += v }\n    t\n}'),
    # Maps.
    row('map-keys', 'fn main() -> int {\n    var a = Map[str, int]()\n    var b = Map[int, str]()\n    var c = Map[bool, List[int]]()\n    a["x"] = 1\n    b[2] = "y"\n    c[true] = [3]\n    let n = a["x"] else 0\n    let removed = (mut a).remove("x") else 0\n    if a.is_empty() { (mut b).clear() }\n    n + removed + a.len + b.count()\n}'),
    row('map-i32-key', 'fn main() -> int {\n    var m = Map[i32, int]()\n    m.len\n}', 'E0418'),
    row('map-struct-key', 'struct P { a: int }\nfn main() -> int {\n    var m = Map[P, int]()\n    m.len\n}', 'E0418'),
    row('map-compound-absent', 'fn main() -> int {\n    var m = Map[str, int]()\n    m["a"] += 1\n    0\n}', 'E0417'),
    row('map-read-is-a-row', 'fn main() -> int {\n    var m = Map[str, int]()\n    m["a"] + 1\n}', 'E0409'),
    # Rows.
    row('raise-propagate-else', 'fn f(n: int) -> int ! {none, Bad(int)} {\n    if n == 0 { return none }\n    if n == 1 { return Bad(n) }\n    n\n}\nfn g(n: int) -> int ! {none, Bad(int), other} {\n    let v = f(n)?\n    v + 1\n}\nfn main() -> int { g(3) else 0 }'),
    row('handler-binder-and-match', 'fn f(n: int) -> int ! {none, Bad(int)} {\n    if n == 0 { return none }\n    Bad(n)\n}\nfn main() -> int {\n    let a = f(1) else |e| match e {\n        none => 0,\n        Bad(k) => k,\n    }\n    let b = f(0) else |_| 4\n    a + b\n}'),
    row('match-over-result', 'enum Shape { Dot, Line(int) }\nfn pick(n: int) -> Shape ! {none} {\n    if n < 0 { return none }\n    Shape.Line(n)\n}\nfn main() -> int {\n    match pick(1) {\n        none => 0,\n        Dot => 1,\n        Line(k) => k,\n    }\n}'),
    row('inferred-row-capitalized', 'fn main() -> !int {\n    if 1 == 2 { return Boom }\n    0\n}'),
    row('inferred-row-lowercase', 'fn main() -> !int {\n    if 1 == 2 { return boom }\n    0\n}', 'E0301'),
    row('ok-into-row-parameter', 'fn or(v: int ! {none}) -> int { v else 0 }\nfn main() -> int { or(5) + or(none) }'),
    row('alias-and-nested', 'error E = {none, parse}\nfn f() -> int ! E { 1 }\nfn g() -> int ! {Bad(int)} ! {Bad(int), none} { 2 }\nfn main() -> int { (f() else 0) + (g() else 0) }'),
    row('open-row', 'fn probe(n: int) -> int ! {Io(int), ..} {\n    if n < 0 { return Weird }\n    if n == 0 { return Io(4) }\n    n\n}\nfn main() -> int { probe(1) else 0 }'),
    row('unit-discard', 'fn boom() -> () ! {bad} { return bad }\nfn f() { boom() }\nfn main() -> int {\n    f()\n    0\n}'),
    row('try-not-fallible', 'fn f() -> int ! {a} {\n    let x = 5?\n    x\n}\nfn main() -> int { f() else 0 }', 'E0603'),
    row('try-in-infallible', 'fn f() -> int ! {a} { return a }\nfn main() -> int {\n    let x = f()?\n    x\n}', 'E0604'),
    row('try-escapes', 'fn f() -> int ! {a} { return a }\nfn g() -> int ! {b} {\n    let x = f()?\n    x\n}\nfn main() -> int { g() else 0 }', 'E0602'),
    row('try-payload-clash', 'fn f() -> int ! {N(int)} { N(4) }\nfn g() -> int ! {N(str)} {\n    f()?\n}\nfn main() -> int { g() else 0 }', 'E0606'),
    row('else-not-fallible', 'fn main() -> int {\n    let x = 5 else 0\n    x\n}', 'E0608'),
    row('tag-twice', 'fn f() -> int ! {Io(str), Io} { 7 }\nfn main() -> int { f() else 0 }', 'E0601'),
    row('nested-layer-clash', 'fn f(n: int) -> int ! {Bad(int)} ! {Bad(str)} { n }\nfn main() -> int { f(3) else 0 }', 'E0609'),
    row('alias-loop', 'error A = {B, io}\nerror B = {A, parse}\nfn f() -> int ! A { 0 }\nfn main() -> int { f() else 0 }', 'E0610'),
    row('handler-name-binds', 'fn f() -> int ! {a, b} { return a }\nfn main() -> int { f() else |a| 1 }'),
    row('handler-payload-partial', 'fn f(n: int) -> int ! {Io(int), timeout} {\n    if n == 0 { return Io(9) }\n    n\n}\nfn main() -> int { f(2) else |Io(e)| e }', 'E0809'),
    row('tag-variant-collision', 'enum Shape { Dot, Line(int) }\nfn pick(n: int) -> Shape ! {Line(int)} { Shape.Dot }\nfn main() -> int {\n    match pick(1) {\n        Line(k) => k,\n        Dot => 0,\n    }\n}', 'E0816'),
    row('row-operand', 'fn f() -> int ! {a} { 1 }\nfn main() -> int { 1 + f() }', 'E0409'),
    row('row-member', 'fn f() -> (int, int) ! {a} { (1, 2) }\nfn main() -> int { f().0 }', 'E0409'),
    row('row-match-missing-tag', 'fn f() -> int ! {a, b} { 1 }\nfn main() -> int {\n    match f() {\n        a => 0,\n        v => v,\n    }\n}', 'E0801'),
    row('row-match-missing-value', 'fn f() -> int ! {a} { 1 }\nfn main() -> int {\n    match f() {\n        a => 0,\n    }\n}', 'E0801'),
    row('tag-undeclared', 'fn f() -> int ! {a} { return b }\nfn main() -> int { f() else 0 }', 'E0301'),
]
