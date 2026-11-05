"""Specification-first enum/match integration cases, separate from F1 rows."""

def row(name, source, code='', warnings=()):
    return dict(name=name, source=source + '\n', code=code, warnings=list(warnings))


ROWS = [
    row('enum-constructor', 'enum E { A, B(int), C(str) }\nfn f(v: E) -> int { match v { A => 0, B(x) => x, C(s) => { print(s)\n 4 } } }\nfn main() -> int { f(E.B(3)) }'),
    row('enum-alias', 'type E = enum { A, B(int) }\nfn main() -> int { match E.B(3) { A => 0, B(x) => x } }'),
    row('bool-product', 'struct P { a: bool, b: bool }\nfn f(p: P) -> int { match p { P { a: true, b } => if b then 1 else 2, P { a: false, b: true } => 3, P { a: false, b: false } => 4 } }\nfn main() -> int { f(P { a: true, b: false }) }'),
    row('or-payload-bindings', 'enum E { A(int), B(int) }\nfn f(v: E) -> int { match v { A(x) | B(x) => x } }\nfn main() -> int { f(E.A(3)) }'),
    row('at-guard', 'fn f(v: int) -> int { match v { n @ 1..=9 if n > 3 => n, _ => 0 } }\nfn main() -> int { f(5) }'),
    row('string-dispatch', 'fn f(v: str) -> int { match v { "a" => 1, r"b" => 2, other => { print(other)\n 3 } } }\nfn main() -> int { f("b") }'),
    row('nullary-does-not-shadow', 'enum E { Done, Other }\nfn main() -> int { var Done: int = 8\n match E.Done { Done => { Done = 9 }, Other => { } }\n Done }'),
    row('nested-payload', 'enum Inner { A, B(str) }\nstruct P { flag: bool }\nenum Outer { Pair(Inner, P), Empty }\nfn f(v: Outer) -> int { match v { Pair(B(s), P { flag: true }) => { print(s)\n 1 }, Pair(_, _) => 2, Empty => 3 } }\nfn main() -> int { f(Outer.Pair(Inner.A, P { flag: false })) }'),
    row('bool-missing', 'fn f(v: bool) -> int { match v { true => 1 } }', 'E0801'),
    row('guard-does-not-cover', 'fn f(v: bool) -> int { match v { true if true => 1, false => 2 } }', 'E0801'),
    row('enum-missing', 'enum E { A, B(int) }\nfn f(v: E) -> int { match v { A => 0 } }', 'E0801'),
    row('bare-payload-pattern', 'enum E { A(int) }\nfn f(v: E) -> int { match v { A => 1 } }', 'E0808'),
    row('constructor-arity', 'enum E { A(int) }\nfn main() -> int { let v = E.A(1, 2)\n 0 }', 'E0402'),
    row('range-empty', 'fn f(v: int) -> int { match v { 5..5 => 1, _ => 0 } }', 'E0815'),
    row('range-bounded-needs-rest', 'fn f(v: u8) -> int { match v { 0..=255 => 1 } }', 'E0801'),
    row('range-single-subsumption', 'fn f(v: int) -> int { match v { 0..10 => 1, 2..5 => 2, _ => 0 } }\nfn main() -> int { f(3) }', warnings=('E0802',)),
    row('range-union-stays-silent', 'fn f(v: int) -> int { match v { 0..5 => 1, 5..10 => 2, 0..10 => 3, _ => 0 } }\nfn main() -> int { f(3) }'),
    row('literal-unreachable', 'fn f(v: str) -> int { match v { "a" => 1, "a" => 2, _ => 0 } }\nfn main() -> int { f("a") }', warnings=('E0802',)),
    row('struct-pattern-missing', 'struct P { a: bool, b: int }\nfn f(v: P) -> int { match v { P { a } => 1 } }', 'E0408'),
    row('pattern-binding-immutable', 'enum E { A(int) }\nfn f(v: E) -> int { match v { A(x) => { x = 1\n x } } }', 'E0410'),
    row('pattern-binding-does-not-leak', 'enum E { A(int) }\nfn f(v: E) -> int { match v { A(x) => { } }\n x }', 'E0301'),
]
