"""Declared error rows reach returned branch/block expressions and nested tests."""
from pathlib import Path
from string_rows import row

ROOT=Path(__file__).resolve().parents[2]
ROWS=[row('returned-if-tag', '''fn pick(ok: bool) -> int ! {gone} { if ok { 5 } else { gone } }
fn main() -> int { (pick(false) else 7) - 7 }'''),
      row('returned-nested-tag', '''enum Kind { A, B }
fn pick(n: int) -> int ! {Bad(Kind)} { if n > 0 { n } else if n == 0 { Bad(Kind.A) } else { Bad(Kind.B) } }
fn main() -> int { pick(0) else 0 }'''),
      row('annotated-if-row', '''fn main() -> int { let result: int ! {gone} = if false then 1 else { gone }
 (result else 7) - 7 }''')]
for name,path in [('handler-binder-name','lints/binder_variant_else.lu'),
                  ('nested-row-variant','rows/match_row_nested_bare_variant.lu')]:
    ROWS.append(row(name,(ROOT/'.wolf-bin/reference/corpus'/path).read_text().rstrip('\n')))
