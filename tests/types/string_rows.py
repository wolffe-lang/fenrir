"""String typing: codes and spans are checked against the pinned binary."""

def row(name, source, code='', at=None):
    return dict(name=name, source=source + '\n', code=code, warnings=[], at=at, warn_at=[], differs='')


ROWS = [
    row('str-length', 'fn main() -> int { "éx".len }'),
    row('str-slice', 'fn main() -> int { let s = "éx"\n s[0..2].len }'),
    row('str-get', 'fn main() -> int { let s = "éx"\n (s.get(0..2) else "").len }'),
    row('str-index-refused', 'fn main() -> int {\n    let s = "wolf"\n    let c = s[2]\n    0\n}', 'E0411', '3:13'),
    row('str-store-refused', 'fn main() {\n    var s = "wolf"\n    s[0..1] = "a"\n}', 'E0416', '3:5'),
]
