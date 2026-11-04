#!/usr/bin/env python3
"""Typed-tree rows: run --emit=typed, validate its tables against the AST,
and apply each row's checks. Scratch is caller-owned."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rows as data  # noqa: E402

EXPRESSIONS = {'Literal', 'String', 'Group', 'Prefix', 'Binary', 'Call', 'StructLiteral', 'Member', 'If',
               'Block', 'Loop', 'Jump', 'Text', 'Interpolation', 'Binder', 'Assignment', 'Tail', 'Statement'}
NODE = re.compile(r'^node (\d+) (\S+) (-?\d+) (-?\d+) (-?\d+) (\S+)$')
TYPE = re.compile(r'^type (\d+) (\S+) (-?\d+) (-?\d+) (\d+)((?: -?\d+)*)$')
DECL = re.compile(r'^decl (\d+) (\S+) "((?:[^"\\]|\\.)*)" (-?\d+) (-?\d+) (-?\d+) (-?\d+) (\d+)$')
TEXT = re.compile(r'^text (\d+) "((?:[^"\\]|\\.)*)"$')
ESCAPES = {'\\': '\\', '"': '"', 'n': '\n', 'r': '\r', 't': '\t', '0': '\0'}


def unescape(s):
    return re.sub(r'\\(.)', lambda m: ESCAPES[m.group(1)], s)


def run(binary, mode, path, timeout=20):
    return subprocess.run([str(binary), '--emit=' + mode, str(path)], capture_output=True, timeout=timeout)


def ast(output):
    nodes = []
    for line in output.decode().splitlines():
        if line.startswith('node '):
            b = line.split()
            nodes.append(dict(kind=b[2], first=int(b[4]), next=int(b[6]), line=int(b[9]), col=int(b[10]),
                              start=int(b[7]), end=int(b[8])))
    return nodes


def typed(output):
    lines = output.decode().splitlines()
    header = re.fullmatch(r'typed/1 "(.*)" root=(\d+) nodes=(\d+)', lines[0])
    assert header, 'typed-header'
    t = dict(types=[], decls=[], texts=[], nodes=[], count=int(header.group(3)))
    for line in lines[1:]:
        if m := TYPE.fullmatch(line):
            assert int(m.group(1)) == len(t['types']), 'type-ids'
            params = [int(x) for x in m.group(6).split()]
            assert len(params) == int(m.group(5)) or m.group(2) != 'fn', 'fn-params'
            t['types'].append(dict(kind=m.group(2), decl=int(m.group(3)), inner=int(m.group(4)), params=params))
        elif m := DECL.fullmatch(line):
            assert int(m.group(1)) == len(t['decls']), 'decl-ids'
            t['decls'].append(dict(kind=m.group(2), name=unescape(m.group(3)), node=int(m.group(4)), ty=int(m.group(5)),
                                   owner=int(m.group(6)), index=int(m.group(7)), count=int(m.group(8))))
        elif m := TEXT.fullmatch(line):
            assert int(m.group(1)) == len(t['texts']), 'text-ids'
            t['texts'].append(unescape(m.group(2)))
        elif m := NODE.fullmatch(line):
            assert int(m.group(1)) == len(t['nodes']), 'node-ids'
            t['nodes'].append(dict(kind=m.group(2), ty=int(m.group(3)), decl=int(m.group(4)), site=int(m.group(5)),
                                   value=m.group(6)))
        else:
            raise AssertionError('unknown-record: ' + line[:60])
    return t


def type_name(t, ty):
    if ty < 0:
        return '-'
    e = t['types'][ty]
    if e['kind'] == 'struct':
        return t['decls'][e['decl']]['name']
    if e['kind'] == 'result':
        return '!' + type_name(t, e['inner'])
    return e['kind']


def invariants(nodes, t):
    """The facts docs/TYPED.md promises consumers after a successful check."""
    assert t['count'] == len(nodes) == len(t['nodes']), 'node-count'
    ntypes, ndecls = len(t['types']), len(t['decls'])
    fixed = ['unit', 'int', 'bool', 'str', 'never', 'i32', 'i64', 'u8', 'u64', 'uint']
    assert [e['kind'] for e in t['types'][:10]] == fixed, 'fixed-types'
    prelude = ['print', 'assert', 'bool', 'str', 'int', 'uint', 'i32', 'i64', 'u8', 'u64']
    assert [d['name'] for d in t['decls'][:10]] == prelude, 'fixed-decls'
    keys = set()
    for i, e in enumerate(t['types']):
        key = (e['kind'], e['decl'], e['inner'], tuple(e['params']))
        assert key not in keys, 'types-not-interned'
        keys.add(key)
        assert all(0 <= p < ntypes for p in e['params']) and -1 <= e['inner'] < ntypes, 'type-refs'
    starts = []
    for i, d in enumerate(t['decls']):
        assert -1 <= d['ty'] < ntypes and -1 <= d['owner'] < ndecls, 'decl-refs'
        if i >= 10:
            assert d['node'] >= 0 and nodes[d['node']]['kind'] in ('Function', 'Struct', 'Field', 'Parameter', 'Binder'), 'decl-node'
            starts.append(nodes[d['node']]['start'])
            assert d['ty'] >= 0, 'decl-untyped'
        if d['kind'] in ('function', 'struct'):
            want = 'param' if d['kind'] == 'function' else 'field'
            for k in range(d['count']):
                p = t['decls'][i + 1 + k]
                assert p['kind'] == want and p['owner'] == i and p['index'] == k, 'members-contiguous'
    assert starts == sorted(starts), 'decls-in-source-order'
    for i, (a, n) in enumerate(zip(nodes, t['nodes'])):
        assert a['kind'] == n['kind'], 'node-kinds'
        assert -1 <= n['ty'] < ntypes and -1 <= n['decl'] < ndecls, 'node-refs'
        if n['site'] >= 0:
            assert nodes[n['site']]['kind'] in ('Statement', 'Tail'), 'site-kind'
            assert nodes[n['site']]['start'] <= a['start'], 'site-before'
        if a['kind'] in EXPRESSIONS and n['site'] >= 0:
            assert n['ty'] >= 0, f'untyped-expression {i} {a["kind"]}'
        if a['kind'] == 'Name' and n['site'] >= 0:
            assert n['decl'] >= 0, f'unresolved-name {i}'


def find(nodes, kind, line, col):
    # Nested nodes of one kind can share a start (`a < b && c`): the
    # outermost, the longest span, is the one a check names.
    hits = [i for i, n in enumerate(nodes) if n['kind'] == kind and n['line'] == line and n['col'] == col]
    assert hits, f'no {kind} at {line}:{col}'
    return max(hits, key=lambda i: nodes[i]['end'])


def apply(check, nodes, t):
    form = check[0]
    if form == 'text':
        assert check[1] in t['texts'], f'text {check[1]!r} not in {t["texts"]}'
        return
    i = find(nodes, check[1], check[2], check[3])
    n = t['nodes'][i]
    if form == 'type':
        got = type_name(t, n['ty'])
        assert got == check[4], f'type at {check[2]}:{check[3]} is {got}, wanted {check[4]}'
    elif form == 'value':
        assert n['value'] == str(check[4]), f'value at {check[2]}:{check[3]} is {n["value"]}, wanted {check[4]}'
    elif form == 'decl':
        d = t['decls'][n['decl']] if n['decl'] >= 0 else None
        assert d and d['kind'] == check[4], f'decl at {check[2]}:{check[3]} is {d}'
        if d['node'] >= 0:
            where = (nodes[d['node']]['line'], nodes[d['node']]['col'])
            assert where == (check[5], check[6]), f'decl node at {where}, wanted {check[5]}:{check[6]}'
    elif form == 'site':
        s = n['site']
        where = (nodes[s]['line'], nodes[s]['col']) if s >= 0 else None
        assert where == (check[4], check[5]), f'site at {where}, wanted {check[4]}:{check[5]}'
    else:
        raise AssertionError('unknown check form ' + form)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('binary', type=Path)
    p.add_argument('--work', required=True, type=Path)
    p.add_argument('--only')
    a = p.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    failures = 0
    for row in data.ROWS:
        if a.only and row['name'] != a.only:
            continue
        source = a.work / (row['name'] + '.lu')
        source.write_text(row['source'])
        try:
            r = run(a.binary, 'typed', source)
            text = r.stderr.decode('utf-8', errors='replace')
            problems = []
            if r.returncode != row['exit']:
                problems.append(f'exit={r.returncode} wanted {row["exit"]}')
            if 'code' in row and f'error[{row["code"]}]' not in text:
                problems.append(f'code {row["code"]} missing')
            if 'location' in row:
                ln, col = row['location']
                if f'{source}:{ln}:{col}: error[' not in text:
                    problems.append(f'location {ln}:{col} missing')
            if r.returncode == 0 and not problems:
                again = run(a.binary, 'typed', source)
                if again.returncode != 0 or again.stdout != r.stdout:
                    problems.append('typed view not byte-identical across runs')
                nodes = ast(run(a.binary, 'ast', source).stdout)
                t = typed(r.stdout)
                invariants(nodes, t)
                for check in row.get('checks', []):
                    apply(check, nodes, t)
            if problems:
                raise AssertionError('; '.join(problems) + ' | ' + text[:300])
            print('PASS ' + row['name'], flush=True)
        except (AssertionError, ValueError, KeyError, IndexError, subprocess.TimeoutExpired) as exc:
            print('FAIL ' + row['name'] + ' ' + str(exc), flush=True)
            failures += 1
    print(f'typed rows: {len(data.ROWS)} rows, {failures} failed', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
