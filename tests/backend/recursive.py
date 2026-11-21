#!/usr/bin/env python3
"""Recursive types through storage handles, and recursion without one refused by name.

Prediction: before edition 6 admits a later list or map component, `--emit=fir` of a type that
recurses through `List` or `Map` does not terminate (placement recursed through the handle) and
the process traps. Afterwards each source row lowers to edition 6, whose list or map shape names a
later shape; the FIR prints back byte for byte, runs in the bounded interpreter to the stdout of
the reference's checked machine (`wolf conform-run --checked`) and, with --native, natively on
Linux. The released native backend overflows its own stack rendering a recursive enum and refuses
deep copies of recursive structs, so the checked machine is the oracle here.

A type that recurses with no handle in between has no finite size: the type checker refuses it
(E0404, at the reference's byte span) before lowering, and the FIR verifier refuses a struct field
or enum payload that names a later shape at every edition. Editions 5 and below refuse a later
list or map component by name.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

TREE = '''enum Tree {
    Leaf(int),
    Node(List[Tree]),
}

fn sum(t: Tree) -> int {
    match t {
        Leaf(n) => n,
        Node(kids) => {
            var s = 0
            for k in kids { s = s + sum(k) }
            s
        },
    }
}
'''

# (name, source, stdout of the checked machine)
SOURCES = [
    ('enum-through-list', TREE + '''
fn main() {
    var inner = List[Tree]()
    (mut inner).push(Tree.Leaf(2))
    (mut inner).push(Tree.Leaf(3))
    var top = List[Tree]()
    (mut top).push(Tree.Leaf(1))
    (mut top).push(Tree.Node(inner))
    let t = Tree.Node(top)
    print("{sum(t)}")
    print("{t}")
}
''', '6\nTree.Node([Tree.Leaf(1), Tree.Node([Tree.Leaf(2), Tree.Leaf(3)])])\n'),
    # The render helper is one function per type; its calls follow the value, so a value nested
    # 64 deep renders through 64 nested calls of the same helper.
    ('enum-through-list-deep', TREE + '''
fn main() {
    var t = Tree.Leaf(1)
    var i = 0
    while i < 64 {
        var kids = List[Tree]()
        (mut kids).push(t)
        t = Tree.Node(kids)
        i += 1
    }
    let text = "{t}"
    print("{sum(t)} {text.len}")
}
''', '1 844\n'),
    ('enum-through-map', '''enum Json {
    Num(int),
    Obj(Map[str, Json]),
}

fn depth(j: Json) -> int {
    match j {
        Num(_) => 0,
        Obj(m) => {
            var d = 0
            for (_, v) in m.pairs() {
                let e = depth(v)
                if e > d { d = e }
            }
            d + 1
        },
    }
}

fn main() {
    var leaf = Map[str, Json]()
    leaf["a"] = Json.Num(1)
    var outer = Map[str, Json]()
    outer["k"] = Json.Obj(leaf)
    outer["n"] = Json.Num(2)
    print("{depth(Json.Obj(outer))}")
}
''', '2\n'),
    ('struct-through-list', '''struct Node {
    v: int,
    kids: List[Node],
}

fn total(n: Node) -> int {
    var s = n.v
    for k in n.kids { s = s + total(k) }
    s
}

fn main() {
    var leaves = List[Node]()
    (mut leaves).push(Node { v: 2, kids: List[Node]() })
    (mut leaves).push(Node { v: 3, kids: List[Node]() })
    let root = Node { v: 1, kids: leaves }
    print("{total(root)}")
    print("{root}")
}
''', '6\nNode { v: 1, kids: [Node { v: 2, kids: [] }, Node { v: 3, kids: [] }] }\n'),
    # A struct reached by value from an enum that the struct holds through a list.
    ('mutual-through-list', '''struct Bag {
    items: List[Item],
}

enum Item {
    Atom(int),
    Nested(Bag),
}

fn weight(i: Item) -> int {
    match i {
        Atom(n) => n,
        Nested(b) => count(b),
    }
}

fn count(b: Bag) -> int {
    var n = 0
    for i in b.items { n = n + weight(i) }
    n
}

fn main() {
    var inner = List[Item]()
    (mut inner).push(Item.Atom(4))
    var items = List[Item]()
    (mut items).push(Item.Atom(1))
    (mut items).push(Item.Nested(Bag { items: inner }))
    let b = Bag { items: items }
    print("{count(b)}")
    print("{b}")
}
''', '5\nBag { items: [Item.Atom(1), Item.Nested(Bag { items: [Item.Atom(4)] })] }\n'),
    # The list element is a tuple holding the struct by value.
    ('tuple-element-through-list', '''struct Pairs {
    tag: str,
    rest: List[(int, Pairs)],
}

fn size(p: Pairs) -> int {
    var n = 1
    for e in p.rest { n = n + e.0 + size(e.1) }
    n
}

fn main() {
    var rest = List[(int, Pairs)]()
    (mut rest).push((10, Pairs { tag: "b", rest: List[(int, Pairs)]() }))
    let p = Pairs { tag: "a", rest: rest }
    print("{size(p)}")
    print("{p}")
}
''', '12\nPairs { tag: a, rest: [(10, Pairs { tag: b, rest: [] })] }\n'),
]

# Recursion with no handle in between: (name, source, byte span of the reference's E0404).
BY_VALUE = [
    ('by-value-enum', 'enum E {\n    Leaf,\n    Node(E),\n}\n\nfn main() {\n    let e = E.Leaf\n}\n', (23, 27)),
    ('by-value-tuple', 'struct P {\n    t: (int, P),\n}\n\nfn main() {\n    print("x")\n}\n', (15, 16)),
    ('by-value-mutual', 'struct A {\n    b: B,\n}\n\nstruct B {\n    a: A,\n}\n\nfn main() {\n    print("x")\n}\n', (15, 16)),
    ('by-value-struct-enum', 'struct S {\n    e: E,\n}\n\nenum E {\n    Hold(S),\n    Empty,\n}\n\nfn main() {\n    print("x")\n}\n', (15, 16)),
]


def module(shapes, edition=6):
    """A module whose `main` returns 0 and whose shapes are (kind, fields)."""
    lines = [f'fir {edition}', 'blobs 1', f'blob {"proof.lu".encode().hex()}', 'sites 1', 'site 0 1 1',
             f'shapes {len(shapes)}']
    lines += [f'{kind} {len(fields)}' + ''.join(f' {x}' for x in fields) for kind, fields in shapes]
    lines += ['functions 1', 'function 1 0 0 1', 'block 0 2', 'const 1 0 1 0 0', 'return 0 0 0 1 0', 'end', '']
    return '\n'.join(lines)


# Shape ids start at 10. (name, shapes, refusal or None at edition 6, refusal at editions 3-5)
LATER = 'FIR_TYPE a later list or map component needs edition 6'
SHAPES = [
    ('list-names-later-struct', [('list', (11,)), ('struct', (1, 10))], None, LATER),
    ('map-names-later-struct', [('map', (3, 11)), ('struct', (1, 10))], None, LATER),
    ('list-names-later-enum', [('list', (13,)), ('struct', (1,)), ('struct', (10,)), ('enum', (11, 12))], None, LATER),
    ('list-names-itself', [('list', (10,))], None, LATER),
    ('struct-field-names-later-struct', [('struct', (1, 11)), ('struct', (1,))], 'FIR_TYPE invalid struct field', None),
    ('struct-field-names-itself', [('struct', (1, 10))], 'FIR_TYPE invalid struct field', None),
    ('enum-payload-names-later-struct', [('enum', (11,)), ('struct', (1,))], 'FIR_TYPE enum payload is not an earlier struct', None),
    ('list-names-missing-shape', [('list', (12,)), ('struct', (1, 10))], 'FIR_TYPE invalid list element type', None),
]


def limits(memory=1 << 30, cpu=60):
    def apply():
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    return apply


def run(argv, memory=1 << 30, cpu=60, timeout=120, **kw):
    opts = {'preexec_fn': limits(memory, cpu)} if sys.platform == 'linux' else {}
    return subprocess.run([str(x) for x in argv], capture_output=True, timeout=timeout, **opts, **kw)


def checked(home, source):
    """The reference's checked machine on one row: (verdict, stdout, first diagnostic)."""
    env = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'), WOLF_RT_LIB=str(ROOT / '.wolf-bin/libwolf_rt.a'))
    r = run([ROOT / '.wolf-bin/wolf', 'conform-run', source.name, '--json', '--checked'], cwd=home, env=env)
    (home / 'reference.json').write_bytes(r.stdout)
    (home / 'reference.stderr').write_bytes(r.stderr)
    record = json.loads(r.stdout)
    first = record['diagnostics'][0] if record['diagnostics'] else {}
    return record['verdict'], record.get('stdout_inline'), (first.get('code'), tuple(first.get('span') or ()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('compiler', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--native', action='store_true')
    ap.add_argument('--reference', action='store_true', help="also run the reference's checked machine on every source row")
    a = ap.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    compiler = a.compiler.resolve()
    env = dict(os.environ, FENRIR_TOOLCHAIN=str(ROOT / '.wolf-bin'))
    failed = 0

    def report(ok, name, detail=''):
        nonlocal failed
        failed += 0 if ok else 1
        print(('PASS ' if ok else 'FAIL ') + name + (' ' + detail if detail and not ok else ''), flush=True)

    for name, source, expected in SOURCES:
        home = a.out / name
        home.mkdir(exist_ok=True)
        src = home / 'row.lu'
        src.write_text(source)
        if a.reference:
            verdict, stdout, _ = checked(home, src)
            report((verdict, stdout) == ('exit(0)', expected), 'reference-' + name, f'{verdict} {stdout!r}')
        lower = run([compiler, '--emit=fir', src])
        fir = home / 'row.fir'
        fir.write_bytes(lower.stdout)
        if lower.returncode != 0 or not lower.stdout.startswith(b'fir 6\n'):
            report(False, 'lower-' + name, f'exit={lower.returncode} {lower.stdout[:8]!r} {lower.stderr[:200]!r}')
            continue
        again = home / 'again.fir'
        p = run([compiler, 'fir', fir, '-o', again])
        report(p.returncode == 0 and again.read_bytes() == lower.stdout, 'roundtrip-' + name, p.stderr[:200].decode(errors='replace'))
        outcome = home / 'outcome'
        p = run([compiler, 'interpret', fir, '--steps', '20000000', '--bytes', str(1 << 26), '--report', outcome])
        (home / 'interpreter.stdout').write_bytes(p.stdout)
        got = (p.returncode, outcome.read_text() if outcome.exists() else '')
        ok = got == (0, 'exit 0\n') and p.stdout.decode(errors='replace') == expected
        report(ok, 'interpret-' + name, f'{got} {p.stdout[:300]!r} {p.stderr[:200]!r}')
        # The x86-64 assembly of the later list or map shapes, twice, byte for byte.
        assembly = home / 'row.s'
        q1 = run([compiler, '--emit=asm', src])
        q2 = run([compiler, '--emit=asm', src])
        assembly.write_bytes(q1.stdout)
        report(q1.returncode == 0 and q2.returncode == 0 and q1.stdout == q2.stdout and bool(q1.stdout), 'asm-' + name,
               q1.stderr[:200].decode(errors='replace'))
        if a.native:
            assert sys.platform == 'linux', 'native proof requires Linux; this is not a skip'
            exe = home / 'program'
            b = run([compiler, 'build', src, '-o', exe], memory=2 << 30, cpu=180, timeout=240, env=env)
            if b.returncode:
                report(False, 'native-' + name, b.stderr[:300].decode(errors='replace'))
                continue
            q = run([exe])
            (home / 'native.stdout').write_bytes(q.stdout)
            report((q.returncode, q.stdout, q.stderr) == (0, p.stdout, b''), 'native-' + name,
                   f'{q.returncode} {q.stdout[:200]!r} {q.stderr[:200]!r}')

    for name, source, span in BY_VALUE:
        home = a.out / name
        home.mkdir(exist_ok=True)
        src = home / 'row.lu'
        src.write_text(source)
        p = run([compiler, '--emit=fir', src])
        line = p.stderr.decode(errors='replace').splitlines()[0] if p.stderr else ''
        ok = p.returncode == 2 and not p.stdout and 'error[E0404]' in line and f'(bytes {span[0]}..{span[1]})' in line
        report(ok, 'refused-' + name, f'exit={p.returncode} {line[:200]}')
        if a.reference:
            verdict, _, first = checked(home, src)
            report((verdict, first) == ('fail(E0404)', ('E0404', span)), 'reference-' + name, f'{verdict} {first}')

    for name, shapes, refusal, older in SHAPES:
        for edition in (6, 5, 3):
            label = f'shapes-{name}-edition-{edition}'
            text = module(shapes, edition)
            src = a.out / (label + '.fir')
            src.write_text(text)
            out = a.out / (label + '.canonical')
            out.write_text('sentinel')
            p = run([compiler, 'fir', src, '-o', out])
            want = refusal or (older if edition < 6 else None)
            if want:
                ok = p.returncode == 2 and want.encode() in p.stderr and out.read_text() == 'sentinel'
                report(ok, label, f'exit={p.returncode} {p.stderr[:200]!r}')
                continue
            outcome = a.out / (label + '.outcome')
            q = run([compiler, 'interpret', src, '--steps', '1000', '--bytes', str(1 << 20), '--report', outcome])
            ok = p.returncode == 0 and out.read_text() == text and q.returncode == 0 and outcome.read_text() == 'exit 0\n'
            report(ok, label, f'exit={p.returncode} {p.stderr[:200]!r} interpret={q.returncode}')

    print(f'recursive: {failed} failed', flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
