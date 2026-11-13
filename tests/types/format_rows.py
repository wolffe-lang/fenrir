"""Compile-time format grammar and primitive-surface diagnostics."""
from string_rows import row

ROWS = [
    row('format-integer', 'fn main() { print("{42:+08x}") }'),
    row('format-string', 'fn main() { print("{\"éx\":*>5.2}") }'),
    row('format-char', 'fn main() { print("{\'é\':^5.1}") }'),
    row('format-bool', 'fn main() { print("{true:^7}") }'),
    row('format-empty', 'fn main() { print("{42:}") }'),
    row('format-zero-alignment', 'fn main() { print("{42:>08}") }', 'E0412', '1:23'),
    row('format-large-width', 'fn main() { print("{42:65536}") }', 'E0412', '1:23'),
    row('format-large-precision', 'fn main() { print("{\"x\":.65536}") }', 'E0412', '1:24'),
    row('format-int-precision', 'fn main() { print("{42:.2}") }', 'E0413', '1:23'),
    row('format-bool-sign', 'fn main() { print("{true:+}") }', 'E0413', '1:25'),
    row('format-string-radix', 'fn main() { print("{\"x\":x}") }', 'E0413', '1:24'),
]
