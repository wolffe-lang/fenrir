"""String typing: codes and spans are checked against the pinned binary."""

def row(name, source, code='', at=None):
    return dict(name=name, source=source + '\n', code=code, warnings=[], at=at, warn_at=[], differs='')


ROWS = [
    row('str-length', 'fn main() -> int { "éx".len }'),
    row('str-slice', 'fn main() -> int { let s = "éx"\n s[0..2].len }'),
    row('str-get', 'fn main() -> int { let s = "éx"\n (s.get(0..2) else "").len }'),
    row('char-pattern-order', r"""fn class(c: char) -> int { match c { 'a' | 'b' => 1, '\n' => 2, _ => 0 } }
fn main() -> int { if 'z' < 'é' && '\u{61}' == 'a' { class('b') } else { 0 } }"""),
    row('char-concatenation', """fn main() -> int { var s = "x"
 s += 'é'
 if 'a' + s == "axé" { 0 } else { 1 } }"""),
    row('char-map-key', r"""fn main() -> int { var m = Map[char, bool]()
 m['é'] = true
 if m['\u{e9}'] else false { 0 } else { 1 } }"""),
    row('string-search-parse', 'fn main() -> int { let n = "42".to_int() else 0\n let i = "aba".find("b") else 0\n if "aba".starts_with("a") { n + i + "aba".count("a") } else { 0 } }'),
    row('string-repeat-replace', 'fn main() -> int { "ab".repeat(2).replace("a", "x").len }'),
    row('string-trim-split', 'fn main() -> int { " a b ".trim().split(" ").len }'),
    row('byte-list-type', 'fn main() -> int { let b = List[byte]()\n b.len }'),
    row('str-index-refused', 'fn main() -> int {\n    let s = "wolf"\n    let c = s[2]\n    0\n}', 'E0411', '3:13'),
    row('str-store-refused', 'fn main() {\n    var s = "wolf"\n    s[0..1] = "a"\n}', 'E0416', '3:5'),
]
