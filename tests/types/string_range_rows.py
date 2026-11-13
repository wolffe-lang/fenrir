"""String slice endpoints normalize before the UTF-8 domain check."""
from string_rows import row

ROWS = [
    row('str-open', 'fn main() -> int { let s = "éxy"\n if s[2..] == "xy" && s[..2] == "é" { 0 } else { 1 } }'),
    row('str-inclusive', 'fn main() -> int { let s = "éxy"\n if s[0..=1] == "é" && s[..=2] == "éx" { 0 } else { 1 } }'),
    row('str-end-relative', 'fn main() -> int { let s = "éxy"\n if s[^2..^0] == "xy" && s[0..^2] == "é" { 0 } else { 1 } }'),
    row('str-get-extremes', 'fn main() -> int { let s = "éxy"\n let a = s.get(0..=9223372036854775807) else "none"\n let b = s.get(0..^(0 - 9223372036854775807 - 1)) else "none"\n let c = s.get(^5..4) else "none"\n if a == "none" && b == "none" && c == "none" { 0 } else { 1 } }'),
    row('str-get-relative', 'fn main() -> int { let s = "éxy"\n let a = s.get(^2..) else "none"\n let b = s.get(..^2) else "none"\n let c = s.get(..=1) else "none"\n if a == "xy" && b == "é" && c == "é" { 0 } else { 1 } }'),
]
