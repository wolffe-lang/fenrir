#!/usr/bin/env python3
"""Nominal enums and recursively nested values obey the aggregate text contract."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('source_render_runner', Path(__file__).with_name('format.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.__doc__ = __doc__
runner.SUITE = 'render'
runner.CASES = [
    ('enum-variants', 'print("{Message.Quiet}|{Message.Text(\"raw\")}|{Message.Count(0 - 2)}")', 'Message.Quiet|Message.Text(raw)|Message.Count(-2)\n'),
    ('nested-enums', 'let values = [Message.Text("raw"), Message.Quiet]\n let box = Box { values: values, pair: (Message.Quiet, \'é\') }\n print("{box}")', 'Box { values: [Message.Text(raw), Message.Quiet], pair: (Message.Quiet, é) }\n'),
    ('enum-result-row', 'let a = good()\n let b = bad()\n print("{a}|{b}")', 'Message.Count(7)|Oops(Message.Quiet)\n'),
    ('enum-erased-unit', 'print("{make()}")', 'E.V(())\n'),
]
runner.PREFIX = '''enum Message { Quiet, Text(str), Count(int) }
struct Box { values: List[Message], pair: (Message, char) }
fn good() -> Message ! {Oops(Message)} { Message.Count(7) }
fn bad() -> Message ! {Oops(Message)} { Oops(Message.Quiet) }
'''

runner.PREFIXES = {'enum-erased-unit': '''enum E { V(()) }
fn make() -> E { E.V({}) }
'''}
runner.REFERENCE_REFUSALS = {'enum-erased-unit': 'unit-typed enum payloads'}

if __name__ == '__main__':
    raise SystemExit(runner.main())
