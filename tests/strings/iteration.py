#!/usr/bin/env python3
"""Direct text-field iteration preserves views, order and loop control."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('text_iteration_runner', Path(__file__).with_name('format.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.__doc__ = __doc__
runner.SUITE = 'iteration'
runner.PREFIX = '''fn source() -> str { print("receiver")\n "a,,b," }
fn separator() -> str { print("separator")\n "," }
'''
runner.CASES = [
    ('split-empty-fields', 'for field in "a,,b,".split(",") { print("[{field}]") }', '[a]\n[]\n[b]\n[]\n'),
    ('split-empty-separator', 'for field in "éx".split("") { print("[{field}]") }', '[éx]\n'),
    ('words-unicode', r'for word in " \u{85}a\u{2003}é\u{3000}𝄞".words() { print("[{word}]") }', '[a]\n[é]\n[𝄞]\n'),
    ('words-non-whitespace', r'for word in "a\u{180e}\u{200b}b".words() { print("[{word}]") }', '[a᠎​b]\n'),
    ('lines', r'for line in "a\r\n\nb\n".lines() { print("[{line}]") }', '[a]\n[]\n[b]\n'),
    ('control-order', 'for field in source().split(separator()) {\n if field == "" { continue }\n print(field)\n if field == "b" { break }\n}', 'receiver\nseparator\na\nb\n'),
    ('nested-control', r'''for line in "a\nb".lines() {
 for word in " x y ".words() {
  if word == "x" { continue }
  print("{line}:{word}")
 }
}''', 'a:y\nb:y\n'),
    ('words-whitespace-only', r'for word in "\t\n\u{b}\u{c}\r \u{85}\u{a0}\u{1680}\u{2000}\u{2001}\u{2002}\u{2003}\u{2004}\u{2005}\u{2006}\u{2007}\u{2008}\u{2009}\u{200a}\u{2028}\u{2029}\u{202f}\u{205f}\u{3000}".words() { print(word) }', ''),
    ('lines-empty', r'''for line in "".lines() { print("wrong") }
 for line in "\n".lines() { print("[{line}]") }''', '[]\n'),
]

if __name__ == '__main__':
    raise SystemExit(runner.main())
