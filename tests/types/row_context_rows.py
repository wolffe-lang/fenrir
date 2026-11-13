"""Declared error rows reach returned branch/block expressions and nested tests."""
from pathlib import Path
from string_rows import row

ROOT=Path(__file__).resolve().parents[2]
ROWS=[row('returned-if-tag', '''fn pick(ok: bool) -> int ! {gone} { if ok { 5 } else { gone } }
fn main() -> int { (pick(false) else 7) - 7 }'''),
      row('returned-nested-tag', '''enum Kind { A, B }
fn pick(n: int) -> int ! {Bad(Kind)} { if n > 0 { n } else if n == 0 { Bad(Kind.A) } else { Bad(Kind.B) } }
fn main() -> int { pick(0) else 0 }'''),
      row('annotated-if-row', '''fn main() -> int { let result: int ! {gone} = if false { 1 } else { gone }
 (result else 7) - 7 }''')]
for name,path in [('handler-binder-name','lints/binder_variant_else.lu'),
                  ('nested-row-variant','rows/match_row_nested_bare_variant.lu')]:
    ROWS.append(row(name,(ROOT/'.wolf-bin/reference/corpus'/path).read_text().rstrip('\n')))

ROWS.append(row('known-tag-cannot-fail',
    (ROOT/'.wolf-bin/reference/corpus/typecheck/tag_known_cannot_fail.lu').read_text().rstrip('\n'),
    'E0604', '20:16'))

PREFIX='fn g() -> int ! {bad} { bad }\n'
ANNOTATED='fn main() -> int { let r: int ! {bad} = g()\n let n = r else 0\n'
ROWS += [
    row('known-tag-return', PREFIX+ANNOTATED+' return bad }', 'E0604', '4:9'),
    row('known-tag-tail', PREFIX+ANNOTATED+' bad }', 'E0604', '4:2'),
    row('known-tag-value', PREFIX+ANNOTATED+' let x = bad\n x }', 'E0604', '4:10'),
    row('known-tag-later-annotation', PREFIX+'fn main() -> int { return bad\n let r: int ! {bad} = g()\n 0 }', 'E0604', '2:27'),
    row('known-tag-local-shadows', PREFIX+ANNOTATED+' let bad = 4\n return bad }'),
    row('tag-in-another-function-is-not-known', PREFIX+'fn main() -> int { return bad }', 'E0301', '2:27'),
    row('callee-row-does-not-declare-a-tag', PREFIX+'fn main() -> int { let r = g()\n let n = r else 0\n return bad }', 'E0301', '4:9'),
    row('unknown-tag-cannot-fail', 'fn main() -> int { return bad }', 'E0301', '1:27'),
    row('known-payload-tag-cannot-fail', 'fn g() -> int ! {Bad(int)} { Bad(1) }\nfn main() -> int { let r: int ! {Bad(int)} = g()\n let n = r else 0\n return Bad(3) }', 'E0604', '4:9'),
    row('loop-pattern-binding-immutable', '''enum Step { Inc(int), Dec(int), Stop }
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
fn main() {}''', 'E0410', '6:13'),
]

