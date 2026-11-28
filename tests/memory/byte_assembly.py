#!/usr/bin/env -S python3 -I
"""Capture the complete old-core assembly set before packed-byte implementation.

Allowed changes are identified per source row from actual typed byte-list
uses/declarations or explicit byte-list annotations. View-only uses may remain
unchanged; every row outside the frozen set must keep identical assembly.
No machine name, absolute source path or captured program output is serialized.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TYPE = re.compile(r'^type (\d+) (\S+) (-?\d+) (-?\d+) (\d+)((?: -?\d+)*)$')
NODE = re.compile(r'^node \d+ \S+ (-?\d+) (-?\d+) (-?\d+) \S+$')
DECL = re.compile(r'^decl \d+ \S+ "(?:[^"\\]|\\.)*" (-?\d+) (-?\d+) -?\d+ -?\d+ \d+$')
GAIN = 'corpus/memory/byte_list_ledger.lu'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def byte_reasons(typed, source):
    types, used = {}, set()
    for line in typed.splitlines():
        if m := TYPE.fullmatch(line):
            types[int(m[1])] = (m[2], int(m[4]))
        elif m := NODE.fullmatch(line):
            used.add(int(m[1]))
        elif m := DECL.fullmatch(line):
            if int(m[1]) >= 0:
                used.add(int(m[2]))

    def byte(ty):
        seen = set()
        while ty in types and ty not in seen:
            seen.add(ty)
            kind, inner = types[ty]
            if kind == 'byte':
                return True
            if kind != 'adapter':
                return False
            ty = inner
        return False

    lists = {ty for ty, (kind, inner) in types.items() if kind == 'list' and byte(inner)}
    reasons = []
    if lists & used:
        reasons.append('typed-source-byte-list-use-or-declaration')
    if re.search(r'\bList\s*\[\s*byte\s*\]', source):
        reasons.append('explicit-byte-list-annotation')
    return reasons


def invoke(compiler, mode, source, home):
    env = dict(os.environ, HOME=str(home), SHELL='/bin/sh')
    p = subprocess.run([str(compiler), '--emit=' + mode, str(source)], cwd=ROOT,
                       env=env, capture_output=True, timeout=120)
    if p.returncode:
        raise RuntimeError('emission failed: ' + str(source) + ' mode=' + mode + ' exit=' + str(p.returncode))
    return p.stdout


def selection():
    table = json.loads((ROOT / 'tests/lower/core-verdicts.json').read_text())
    names = [r['file'] for r in table['rows']]
    assert len(names) == len(set(names)) and all(n.startswith('corpus/') and '..' not in Path(n).parts for n in names)
    return sorted(names)


def capture(compiler, out):
    names = selection()
    assert len(names) == 423 and GAIN not in names
    destination = out / 'baseline.json'
    assert not destination.exists(), 'never overwrite a frozen capture'
    home = out / 'home'
    home.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in names:
        source = Path('.wolf-bin/reference') / name
        data = (ROOT / source).read_bytes()
        typed = invoke(compiler, 'typed', source, home).decode()
        asm = invoke(compiler, 'asm', source, home)
        repeated = invoke(compiler, 'asm', source, home)
        assert asm == repeated, 'nondeterministic baseline assembly: ' + name
        reasons = byte_reasons(typed, data.decode())
        rows.append(dict(file=name, source_sha256=digest(data), asm_sha256=digest(asm), asm_bytes=len(asm),
                         allowed_change=bool(reasons), reasons=reasons))
        print('PASS byte-assembly-baseline ' + name + ' allowed=' + str(bool(reasons)).lower(), flush=True)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    result = dict(format=1, baseline_head=head, selection_count=423,
                  scope='old core; byte-list representation changes only; no observed post-change result',
                  source_argument_prefix='.wolf-bin/reference/',
                  toolchain_sha256=digest((ROOT / 'wolf-toolchain.toml').read_bytes()), rows=rows)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS byte-assembly-capture rows=423 allowed=' + str(sum(r['allowed_change'] for r in rows)), flush=True)


def compare(compiler, out, baseline):
    sealed = json.loads(baseline.read_text())
    old = {r['file']: r for r in sealed['rows']}
    assert len(old) == sealed['selection_count'] == 423
    current = set(selection())
    assert set(old) <= current and current - set(old) <= {GAIN}, 'old row lost or unlisted gain'
    assert digest((ROOT / 'wolf-toolchain.toml').read_bytes()) == sealed['toolchain_sha256']
    home = out / 'home'
    home.mkdir(parents=True, exist_ok=True)
    changed, unchanged, failed = [], [], []
    for name, row in sorted(old.items()):
        source = Path('.wolf-bin/reference') / name
        assert digest((ROOT / source).read_bytes()) == row['source_sha256'], 'stale source capture: ' + name
        asm = invoke(compiler, 'asm', source, home)
        assert asm == invoke(compiler, 'asm', source, home), 'nondeterministic assembly: ' + name
        same = digest(asm) == row['asm_sha256']
        (unchanged if same else changed).append(name)
        ok = same or row['allowed_change']
        if not ok:
            failed.append(name)
        print(('PASS' if ok else 'FAIL') + ' byte-assembly-unchanged-set ' + name + ' unchanged=' + str(same).lower(), flush=True)
    (out / 'comparison.json').write_text(json.dumps(dict(changed=changed, unchanged=unchanged, unexpected=failed), indent=2) + '\n')
    print(('PASS' if not failed else 'FAIL') + f' byte-assembly-compare rows=423 changed={len(changed)} unexpected={len(failed)}', flush=True)
    return int(bool(failed))


def selftest():
    types = 'type 11 byte -1 -1 0\ntype 16 list -1 11 0\n'
    assert byte_reasons(types, '') == [], 'unused prelude type cannot allow every row'
    assert byte_reasons(types + 'node 0 Call 16 -1 0 0\n', '') == ['typed-source-byte-list-use-or-declaration']
    assert byte_reasons(types + 'decl 0 param "x" 1 16 0 0 0\n', '') == ['typed-source-byte-list-use-or-declaration']
    assert byte_reasons('type 1 int -1 -1 0\ntype 16 list -1 1 0\nnode 0 Call 16 -1 0 0\n', '') == []
    assert byte_reasons('', 'List[byte]') == ['explicit-byte-list-annotation']
    print('PASS byte-assembly-prediction-selftest', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['selftest', 'capture', 'compare'])
    parser.add_argument('--compiler', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--baseline', type=Path, default=ROOT / 'tests/memory/byte-assembly-baseline.json')
    a = parser.parse_args()
    if a.mode == 'selftest':
        selftest()
        return 0
    if not a.compiler or not a.out:
        parser.error('--compiler and --out required')
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if a.mode == 'capture':
        capture(a.compiler.resolve(), out)
        return 0
    return compare(a.compiler.resolve(), out, a.baseline.resolve())


if __name__ == '__main__':
    raise SystemExit(main())
