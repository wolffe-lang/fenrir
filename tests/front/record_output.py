#!/usr/bin/env python3
"""Indent bounded step output and replay only its literal FAIL row markers.

The canonical record format needs column-zero named plant evidence. This adaptor
never invents a row or infers a verdict from text; the child status is retained.
"""
import argparse
import re
import subprocess
import sys

MARKER = re.compile(r'^FAIL [A-Za-z0-9_.:/-]+(?:\s.*)?$')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', nargs=argparse.REMAINDER)
    args = p.parse_args().command
    if args[:1] == ['--']:
        args = args[1:]
    if not args:
        p.error('a child command is required')
    child = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace')
    markers = []
    for line in child.stdout.splitlines():
        print('  ' + line)
        literal = line.lstrip()
        if MARKER.fullmatch(literal):
            markers.append(literal)
    for literal in markers:
        print(literal)
    # A signalled child has the same numeric wait status a shell exposes.
    return child.returncode if child.returncode >= 0 else 128 - child.returncode


if __name__ == '__main__':
    sys.exit(main())
