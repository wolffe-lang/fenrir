"""Specification-first enum/match integration cases, separate from F1 rows.

`code` and `at` are the first error (line:column), `warnings` and `warn_at`
the E0802 warnings, all as the pinned reference reports them; the reference
mode re-checks them. A row whose `differs` names a reason is one where fenrir
deliberately answers otherwise (a refusal fenrir owns, or a reference answer
the language rules contradict), and is not compared with the reference.
"""

# Locations recorded from the reference by `patterns.py --probe` (fenrir's own for `differs` rows).
AT = {
    'or-payload-bindings': ('2:33', []),
    'bool-missing': ('1:24', []),
    'guard-does-not-cover': ('1:24', []),
    'enum-missing': ('2:21', []),
    'bare-payload-pattern': ('2:31', []),
    'constructor-arity': ('2:28', []),
    'range-empty': ('1:33', []),
    'range-bounded-needs-rest': ('1:22', []),
    'range-single-subsumption': (None, ['1:45']),
    'literal-unreachable': (None, ['1:43']),
    'struct-pattern-missing': ('2:31', []),
    'pattern-binding-does-not-leak': ('3:2', []),
    'ctor-arity-pattern': ('2:39', []),
    'ctor-unknown-bare': ('2:39', []),
    'ctor-unknown-qualified': ('2:33', []),
    'ctor-other-enum': ('3:33', []),
    'ctor-on-int': ('2:12', []),
    'struct-unknown-field': ('2:31', []),
    'struct-dup-field': ('2:38', []),
    'literal-type-mismatch': ('1:33', []),
    'arm-type-mismatch': ('1:54', []),
    'guard-not-bool': ('1:38', []),
    'after-wildcard': (None, ['1:42']),
    'enum-after-all': (None, ['2:64']),
    'guarded-after-wildcard': (None, ['1:42']),
    'bool-exhaustive-then-rest': (None, ['2:35']),
    'range-str': ('1:33', []),
    'range-mixed': ('1:36', []),
    'range-reversed': ('1:33', []),
    'statement-match-joins': ('3:28', []),
    'bare-payload-value': ('3:24', []),
    'missing-product': ('2:21', []),
    'missing-int': ('1:23', []),
    'match-no-arms': ('2:21', []),
    'enum-equality': ('2:23', []),
    'enum-struct-same-name': ('2:8', []),
    'negative-literal-pattern': ('1:33', []),
    'capitalized-binder': (None, ['2:41']),
    'binding-twice': ('2:44', []),
    'constructor-name-assigns-let': ('3:27', []),
    'recursive-enum': ('1:1', []),
    'variant-twice': ('1:13', []),
    'literal-outside-type': ('1:32', []),
}


def row(name, source, code='', warnings=(), differs=''):
    at, warn_at = AT.get(name, (None, []))
    return dict(name=name, source=source + '\n', code=code, warnings=list(warnings), at=at,
                warn_at=list(warn_at), differs=differs)


E3 = 'enum E { A, B(int), C(int, bool) }\n'
P2 = 'struct P { a: bool, b: int }\n'

ROWS = [
    row('enum-constructor', 'enum E { A, B(int), C(str) }\nfn f(v: E) -> int { match v { A => 0, B(x) => x, C(s) => { print(s)\n 4 } } }\nfn main() -> int { f(E.B(3)) }'),
    row('enum-alias', 'type E = enum { A, B(int) }\nfn main() -> int { match E.B(3) { A => 0, B(x) => x } }'),
    row('bool-product', 'struct P { a: bool, b: bool }\nfn f(p: P) -> int { match p { P { a: true, b } => if b then 1 else 2, P { a: false, b: true } => 3, P { a: false, b: false } => 4 } }\nfn main() -> int { f(P { a: true, b: false }) }'),
    row('or-payload-bindings', 'enum E { A(int), B(int) }\nfn f(v: E) -> int { match v { A(x) | B(x) => x } }\nfn main() -> int { f(E.A(3)) }',
        'F0001', differs='both compiler machines refuse an or-pattern that binds (lupin runs it); fenrir refuses it by name (wolf-lang#1061)'),
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
    row('struct-pattern-missing', 'struct P { a: bool, b: int }\nfn f(v: P) -> int { match v { P { a } => 1 } }', 'E0814'),
    # The spec states no rule on assigning a match binding (wolf-lang#1062).
    row('pattern-binding-assignable', 'enum E { A(int) }\nfn f(v: E) -> int { match v { A(x) => { x = 1\n x } } }\nfn main() -> int { f(E.A(3)) }'),
    row('pattern-binding-does-not-leak', 'enum E { A(int) }\nfn f(v: E) -> int { match v { A(x) => { } }\n x }', 'E0301'),
    # Black-box probes of the reference, 2026-11-06.
    row('ctor-arity-pattern', E3 + 'fn f(v: E) -> int { match v { A => 0, B(x, y) => 1, C(x, y) => 2 } }\nfn main() -> int { f(E.A) }', 'E0808'),
    row('ctor-unknown-bare', E3 + 'fn f(v: E) -> int { match v { A => 0, Zed(x) => 1, _ => 2 } }\nfn main() -> int { f(E.A) }', 'E0403'),
    row('ctor-unknown-qualified', E3 + 'fn f(v: E) -> int { match v { E.Zed => 0, _ => 2 } }\nfn main() -> int { f(E.A) }', 'E0403'),
    row('ctor-other-enum', E3 + 'enum F { A, Q }\nfn f(v: E) -> int { match v { F.Q => 0, _ => 2 } }\nfn main() -> int { f(E.A) }', 'E0403'),
    row('ctor-on-int', 'fn main() -> int { let n = 3\n match n { Io(x) => x, _ => 0 } }', 'E0808'),
    row('struct-unknown-field', P2 + 'fn f(v: P) -> int { match v { P { a, zz } => 1 } }\nfn main() -> int { f(P { a: true, b: 1 }) }', 'E0814'),
    row('struct-dup-field', P2 + 'fn f(v: P) -> int { match v { P { a, a, b } => 1 } }\nfn main() -> int { f(P { a: true, b: 1 }) }', 'E0814'),
    row('struct-rest', P2 + 'fn f(v: P) -> int { match v { P { a: true, .. } => 1, P { b, .. } => b } }\nfn main() -> int { f(P { a: false, b: 7 }) }'),
    row('or-nullary', E3 + 'fn f(v: E) -> int { match v { A | B(_) => 0, C(_, _) => 2 } }\nfn main() -> int { f(E.A) }'),
    row('literal-type-mismatch', 'fn f(v: str) -> int { match v { 1 => 0, _ => 2 } }\nfn main() -> int { f("a") }', 'E0401'),
    row('arm-type-mismatch', 'fn f(v: bool) -> int { match v { true => 0, false => "x" } }\nfn main() -> int { f(true) }', 'E0401'),
    row('guard-not-bool', 'fn f(v: int) -> int { match v { x if x => 0, _ => 2 } }\nfn main() -> int { f(1) }', 'E0401'),
    row('after-wildcard', 'fn f(v: bool) -> int { match v { _ => 0, true => 2 } }\nfn main() -> int { f(true) }', warnings=('E0802',)),
    row('enum-after-all', E3 + 'fn f(v: E) -> int { match v { A => 0, B(_) => 1, C(_, _) => 2, _ => 3 } }\nfn main() -> int { f(E.A) }', warnings=('E0802',)),
    row('guarded-after-wildcard', 'fn f(v: bool) -> int { match v { _ => 0, true if v => 2 } }\nfn main() -> int { f(true) }', warnings=('E0802',)),
    row('bool-exhaustive-then-rest', 'fn main() -> int { let b = true\n match b { true => 0, false => 1, _ => 2 } }', warnings=('E0802',)),
    row('range-str', 'fn f(v: str) -> int { match v { "a".."c" => 0, _ => 2 } }\nfn main() -> int { f("a") }', 'E0808'),
    row('range-mixed', 'fn f(v: int) -> int { match v { 0..true => 0, _ => 2 } }\nfn main() -> int { f(1) }', 'E0808'),
    row('range-reversed', 'fn f(v: int) -> int { match v { 9..=3 => 1, _ => 0 } }\nfn main() -> int { f(1) }', 'E0815'),
    row('range-u8-literals', 'fn f(v: u8) -> int { match v { 255 => 1, 0..10 => 2, _ => 0 } }\nfn main() -> int { f(255) }'),
    row('statement-match-joins', E3 + 'fn main() -> int { let v = E.A\n match v { A => 1, B(_) => "s", C(_, _) => true }\n 0 }', 'E0401'),
    row('statement-match-unit', E3 + 'fn main() -> int { let v = E.A\n match v { A => print("a"), B(_) => print("b"), C(_, _) => {} }\n 0 }'),
    row('bare-payload-value', 'enum E { A, B(int) }\nfn f(v: E) -> int { match v { A => 0, B(x) => x + 5 } }\nfn main() -> int { f(E.B) }', 'E0402'),
    row('binder-covers', E3 + 'fn f(v: E) -> int { match v { x => 1 } }\nfn main() -> int { f(E.A) }'),
    row('missing-product', E3 + 'fn f(v: E) -> int { match v { A => 0, C(_, true) => 1, B(_) => 3 } }\nfn main() -> int { f(E.A) }', 'E0801'),
    row('missing-int', 'fn f(v: int) -> int { match v { 0..10 => 1, 11 => 2 } }\nfn main() -> int { f(1) }', 'E0801'),
    row('match-no-arms', 'enum E { A }\nfn f(v: E) -> int { match v { } }\nfn main() -> int { 0 }', 'E0801'),
    row('qualified-patterns', E3 + 'fn f(v: E) -> int { match v { E.A => 0, E.B(x) => x, E.C(n, _) => n } }\nfn main() -> int { f(E.B(4)) }'),
    row('enum-equality', 'enum E { A, B }\nfn main() -> int { if E.A == E.B then 1 else 0 }', 'E0301'),
    row('enum-in-struct', 'enum E { A, B(int) }\nstruct S { e: E, n: int }\nfn main() -> int { let s = S { e: E.B(2), n: 1 }\n match s.e { A => s.n, B(k) => k + s.n } }'),
    row('at-on-enum', E3 + 'fn f(v: E) -> int { match v { w @ B(n) => n, _ => 0 } }\nfn main() -> int { f(E.B(6)) }'),
    row('binding-shadows', 'fn main() -> int { let x = 4\n match 9 { x => x } }'),
    row('enum-struct-same-name', 'enum E { A }\nstruct E { a: int }\nfn main() -> int { 0 }', 'E0302'),
    row('negative-literal-pattern', 'fn f(v: int) -> int { match v { -1 => 7, -5..=-2 => 8, _ => 2 } }\nfn main() -> int { f(-3) }', 'E0207'),
    row('capitalized-binder', E3 + 'fn f(v: int) -> int { match v { A => 0, _ => 1 } }\nfn main() -> int { f(1) }', warnings=('E0802',)),
    # Deliberate differences, each a reference answer outside fenrir's rules.
    row('binding-twice', P2 + 'fn f(v: P) -> int { match v { P { a: x, b: x } => 1 } }\nfn main() -> int { f(P { a: true, b: 1 }) }',
        'F0001', differs='the reference accepts one name bound twice in a pattern; fenrir refuses it by name (wolf-lang#1062)'),
    row('constructor-name-assigns-let', 'enum E { Done, Other }\nfn main() -> int { let Done: int = 8\n match E.Done { Done => { Done = 9 }, Other => { } }\n Done }',
        'E0410', differs='the reference assigns the outer `let` the nullary pattern did not shadow (wolf-lang#1059)'),
    row('recursive-enum', 'enum L { Nil, Cons(int, L) }\nfn main() -> int { 0 }',
        'F0001', differs='a recursive by-value aggregate is outside fenrir; the reference accepts an unused one (wolf-lang#1062)'),
    row('variant-twice', 'enum E { A, A }\nfn main() -> int { 0 }',
        'E0302', differs='the reference accepts a duplicated variant name (wolf-lang#1060)'),
    row('literal-outside-type', 'fn f(v: u8) -> int { match v { 300 => 0, _ => 2 } }\nfn main() -> int { f(1) }',
        'F0001', differs='the reference accepts it: native wraps 300 to match 44, checked and lupin never match (wolf-lang#1058)'),
]
