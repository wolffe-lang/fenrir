#!/usr/bin/env python3
"""Byte consumption is a view; bound bytes and scalar lists materialize."""
import argparse
from pathlib import Path
import subprocess

CASES = [
    ('byte-view-length', 'fn main() -> int { "éx".bytes().len }', False),
    ('byte-view-index', 'fn main() { print("{"éx".bytes()[1]}") }', False),
    ('byte-view-for', 'fn main() -> int { var n = 0\n for b in "éx".bytes() { n += 1 }\n n }', False),
    ('byte-binding-materializes', 'fn main() -> int { let b = "éx".bytes()\n b.len }', True),
    ('scalar-list-materializes', 'fn main() -> int { "éx".chars().len }', True),
    ('split-view-for', 'fn main() -> int { var n = 0\n for field in "a,b".split(",") { n += 1 }\n n }', False),
    ('words-view-for', 'fn main() -> int { var n = 0\n for word in " a é ".words() { n += 1 }\n n }', False),
    ('lines-view-for', 'fn main() -> int { var n = 0\n for line in "a\\r\\n\\nb\\n".lines() { n += 1 }\n n }', False),
    ('split-binding-materializes', 'fn main() -> int { let fields = "a,b".split(",")\n fields.len }', True),
    ('words-binding-materializes', 'fn main() -> int { let words = " a b ".words()\n words.len }', True),
    ('lines-binding-materializes', 'fn main() -> int { let lines = "a\\nb".lines()\n lines.len }', True),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compiler', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    failed = False
    for name, text, material in CASES:
        home = args.out / name; home.mkdir(exist_ok=True)
        source = home / 'row.lu'; source.write_text(text + '\n')
        run = subprocess.run([str(args.compiler.resolve()), '--emit=fir', str(source.resolve())], capture_output=True, timeout=30)
        (home / 'fir.txt').write_bytes(run.stdout); (home / 'stderr.txt').write_bytes(run.stderr)
        allocations = [line for line in run.stdout.decode().splitlines()
                       if line.startswith('list ') or (line.startswith('text ') and line.split()[4] in ('10', '13'))]
        ok = run.returncode == 0 and bool(allocations) == material
        print(('PASS' if ok else 'FAIL') + ' ' + name, flush=True)
        failed |= not ok
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
