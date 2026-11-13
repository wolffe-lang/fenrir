"""Binding or-patterns, source order, joins, guards and constructor tests."""
from string_rows import row

PROGRAMS = {
    'or-simple': ('enum E { A(int), B(int) }\nfn f(v: E) -> int { match v { A(x) | B(x) => x } }\n', 'f(E.B(3))', 3),
    'or-name-order': ('enum E { A(int, int), B(int, int) }\nfn f(v: E) -> int { match v { A(x, y) | B(y, x) => x * 10 + y } }\n', 'f(E.A(1, 2)) + f(E.B(3, 4))', 55),
    'or-first-match': ('enum E { A(int, int) }\nfn f(v: E) -> int { match v { A(x, _) | A(_, x) => x } }\n', 'f(E.A(1, 2))', 1),
    'or-nested': ('enum Inner { A(int), B(int) }\nenum Outer { W(Inner) }\nfn f(v: Outer) -> int { match v { W((A(x) | B(x))) if x >= 0 => x, _ => 0 } }\n', 'f(Outer.W(Inner.B(7)))', 7),
    'or-guard': ('enum E { A(int), B(int) }\nfn f(v: E) -> int { match v { A(x) | B(x) if x > 5 => x, _ => 0 } }\n', 'f(E.B(3)) + f(E.A(7))', 7),
    'or-at': ('fn f(v: int) -> int { match v { n @ 1..=9 | n @ 20..=29 => n, _ => 0 } }\n', 'f(27)', 27),
    'bind-then-case-test': ('enum E { red, blue }\nstruct P { a: int, b: E }\nfn f(v: P) -> int { match v { P { a: red, b: red } => red, _ => 0 } }\n', 'f(P { a: 7, b: E.red })', 7),
    'case-test-then-bind': ('enum E { red, blue }\nstruct P { a: int, b: E }\nfn f(v: P) -> int { match v { P { b: red, a: red } => red, _ => 0 } }\n', 'f(P { a: 7, b: E.red })', 7),
}
ROWS = [row(name, prefix + 'fn main() -> int { ' + call + ' }')
        for name, (prefix, call, _) in PROGRAMS.items()]
missing = 'enum E { A(int), B(int) }\nfn f(v: E) -> int { match v { A(_) | B(x) => x } }\nfn main() -> int { f(E.A(1)) }'
ROWS.append(row('or-missing-first', missing, 'E0828', '2:' + str(missing.splitlines()[1].index('A(_)') + 1)))
