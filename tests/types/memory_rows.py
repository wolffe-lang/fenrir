"""Typed rows for the memory chapter (`mem.*`, docs/MEMORY.md).

The F2 boundary anchors are in scope: each owns a positive row and a negative
row. A negative row is either a refusal fenrir shares with the reference (the
same code at the same line:column, `reference=True`), or a **named
difference**: a program the reference refuses with an E1xxx code and fenrir
accepts, because the static rule is F6's. A named difference pins the
reference's answer (`differs`), carries no parity credit (`candidate_only`),
names the milestone that closes it (`closes`) and is listed in
tests/types/memory-differences.json; tests/types/check.py fails it by name
the day fenrir refuses it. Every other `mem.*` anchor is outside the typed
core until its F3 unit lands: one row refused by name with F0001.
"""

MAIN = 'fn main() -> int {\n'


def program(body, items=''):
    return items + MAIN + body + '    0\n}\n'


POINT = 'struct P { x: int, y: int }\n'
BAG = 'struct Bag { items: List[int], n: int }\n'


def differs(name, anchor, body, code, at, items=''):
    """A named difference: fenrir accepts, the reference refuses with `code` at `at`; closed at F6."""
    return dict(name=name, anchor=anchor, source=program(body, items), exit=0, candidate_only=True,
                differs=f'fail({code}) {code}@{at[0]}:{at[1]}', closes='F6')


def shared(name, anchor, body, code, at, items=''):
    """A refusal fenrir shares with the reference: the same code at the same site."""
    return dict(name=name, anchor=anchor, source=program(body, items), exit=2, code=code, location=at,
                reference=True)


def positive(name, anchor, body, items=''):
    return dict(name=name, anchor=anchor, source=program(body, items), exit=0)


ROWS = [
    # [mem.model], [mem.model.value]: a value moves or copies whole; a moved non-`Copy` value is gone.
    positive('mem-model-value-moves-whole', 'mem.model',
             '    var a = P { x: 1, y: 2 }\n    var b = a\n    b.x = 5\n    print("{b.x} {b.y}")\n', POINT),
    shared('mem-model-let-is-not-assignable', 'mem.model', '    let a = 1\n    a = 2\n', 'E0410', [3, 5]),
    positive('mem-model-value-copy-scalar', 'mem.model.value', '    let a = 3\n    let b = a\n    print("{a} {b}")\n'),
    differs('mem-model-value-read-after-move', 'mem.model.value',
            '    let a = Bag { items: [1], n: 1 }\n    let b = a\n    print("{a.n} {b.n}")\n', 'E1001', [5, 13], BAG),
    # [mem.model.place], [mem.model.path.disjoint], [mem.model.place.elem]: paths name places.
    positive('mem-model-place-field-store', 'mem.model.place',
             '    var a = P { x: 1, y: 2 }\n    a.x = 3\n    print("{a.x}")\n', POINT),
    shared('mem-model-place-field-of-let', 'mem.model.place', '    let a = P { x: 1, y: 2 }\n    a.x = 3\n', 'E0410', [4, 5],
           POINT),
    positive('mem-model-disjoint-fields', 'mem.model.path.disjoint',
             '    var a = P { x: 1, y: 2 }\n    a.x = a.y\n    a.y = 7\n    print("{a.x} {a.y}")\n', POINT),
    differs('mem-model-disjoint-prefix-moved', 'mem.model.path.disjoint',
            '    var b = Bag { items: [1], n: 1 }\n    let xs = b.items\n    print("{b.items.len} {xs.len}")\n',
            'E1001', [5, 13], BAG),
    positive('mem-model-element-store', 'mem.model.place.elem',
             '    var xs = [1, 2, 3]\n    xs[1] = 9\n    print("{xs[1]}")\n'),
    differs('mem-model-element-moved-twice', 'mem.model.place.elem',
            '    let ys = [[1], [2]]\n    let a = ys[0]\n    let b = ys[0]\n    print("{a.len} {b.len}")\n',
            'E1001', [4, 13]),
    # [mem.model.place.rhs]: operands, right-hand side, then the address.
    positive('mem-model-store-rhs-after-index', 'mem.model.place.rhs',
             '    var xs = [0, 0]\n    xs[pick(1)] = pick(7)\n    print("{xs[1]}")\n',
             'fn pick(n: int) -> int {\n    print("{n}")\n    n\n}\n'),
    shared('mem-model-store-wrong-type', 'mem.model.place.rhs', '    var xs = [1]\n    xs[0] = "a"\n', 'E0401', [3, 13]),
    # [mem.model.order]: strict left to right.
    positive('mem-model-order-left-to-right', 'mem.model.order',
             '    print("{pick(1) + pick(2)}")\n', 'fn pick(n: int) -> int {\n    print("{n}")\n    n\n}\n'),
    # [mem.iter], [mem.iter.for], [mem.iter.range]: builtin ranges and lists iterate.
    positive('mem-iter-list', 'mem.iter', '    var t = 0\n    for x in [1, 2, 3] {\n        t += x\n    }\n    print("{t}")\n'),
    shared('mem-iter-element-type', 'mem.iter', '    for x in [1, 2] {\n        let s: str = x\n    }\n', 'E0401', [3, 22]),
    positive('mem-iter-for-range', 'mem.iter.for', '    for i in 0..3 {\n        print("{i}")\n    }\n'),
    shared('mem-iter-for-range-type', 'mem.iter.for', '    for i in 0..3 {\n        let s: str = i\n    }\n', 'E0401', [3, 22]),
    positive('mem-iter-range-inclusive', 'mem.iter.range', '    for i in 1..=3 {\n        print("{i}")\n    }\n'),
    shared('mem-iter-range-bool-end', 'mem.iter.range', '    for i in 0..true {\n        print("{i}")\n    }\n',
           'E0401', [2, 17]),
    # [mem.iter.excl]: the loop's read claim; a write to the walked place is static (E1013, F6).
    positive('mem-iter-excl-read', 'mem.iter.excl',
             '    let xs = [1, 2]\n    var t = 0\n    for x in xs {\n        t += x + xs.len\n    }\n    print("{t}")\n'),
    differs('mem-iter-excl-write', 'mem.iter.excl',
            '    var xs = [1, 2]\n    for x in xs {\n        xs[0] = x\n    }\n', 'E1013', [4, 9]),
    positive('mem-iter-excl-place-lives', 'mem.iter.excl.1',
             '    let xs = [1, 2]\n    for x in xs {\n        print("{x}")\n    }\n    print("{xs.len}")\n'),
    differs('mem-iter-excl-push', 'mem.iter.excl.1',
            '    var xs = [1, 2]\n    for x in xs {\n        xs = [x]\n    }\n', 'E1013', [4, 9]),
    positive('mem-iter-excl-other-place', 'mem.iter.excl.2',
             '    let xs = [1, 2]\n    var ys = [0, 0]\n    for x in xs {\n        ys[0] = x\n    }\n    print("{ys[0]}")\n'),
    differs('mem-iter-excl-element-write', 'mem.iter.excl.2',
            '    var xs = [1, 2]\n    for x in xs {\n        xs[1] = x\n    }\n', 'E1013', [4, 9]),
    # [mem.list.slice], [mem.list.pop], [mem.list.bytes]
    positive('mem-list-slice', 'mem.list.slice', '    let xs = [1, 2, 3]\n    let ys = xs[1..]\n    print("{ys.len}")\n'),
    shared('mem-list-slice-bool', 'mem.list.slice', '    let xs = [1, 2, 3]\n    let ys = xs[true..]\n', 'E0401', [3, 17]),
    positive('mem-list-pop-none', 'mem.list.pop',
             '    var xs: List[int] = [1]\n    let a = (mut xs).pop() else 0\n    let b = (mut xs).pop() else 7\n    print("{a} {b}")\n'),
    shared('mem-list-get-unhandled', 'mem.list.pop', '    let xs = [1]\n    let v: int = xs.get(0)\n', 'E0401', [3, 18]),
    shared('mem-list-bytes-count-int', 'mem.list.bytes', '    let xs = [1, 2]\n    let n = bytes_count(xs, 1)\n',
           'E0401', [3, 25]),
    # [mem.map.absent]: an absent key is `none`; `m[k] op= v` is not a place.
    positive('mem-map-absent-none', 'mem.map.absent',
             '    var m = Map[str, int]()\n    m["a"] = 1\n    let v = m["b"] else 0\n    print("{v}")\n'),
    shared('mem-map-compound-absent', 'mem.map.absent', '    var m = Map[str, int]()\n    m["a"] += 1\n', 'E0417', [3, 5]),
    # [mem.str] and the boundary methods.
    positive('mem-str-concat', 'mem.str', '    let s = "a" + "b"\n    print(s)\n'),
    shared('mem-str-plus-int', 'mem.str', '    let s = "a" + 1\n', 'E0409', [2, 19]),
    positive('mem-str-order', 'mem.str.order', '    print("{"ab" < "b"} {"" < "a"}")\n'),
    shared('mem-str-order-int', 'mem.str.order', '    let b = "a" < 1\n', 'E0401', [2, 19]),
    positive('mem-str-get', 'mem.str.get', '    let s = "abc"\n    let v = s.get(1..2) else "none"\n    print(v)\n'),
    shared('mem-str-get-unhandled', 'mem.str.get', '    let s = "abc"\n    let v: str = s.get(1..2)\n', 'E0401', [3, 18]),
    positive('mem-str-empty-needle', 'mem.str.empty', '    print("{"abc".count("")}")\n'),
    shared('mem-str-count-int', 'mem.str.empty', '    let n = "abc".count(1)\n', 'E0401', [2, 25]),
    positive('mem-str-repeat', 'mem.str.repeat', '    print("ab".repeat(2))\n'),
    shared('mem-str-repeat-str', 'mem.str.repeat', '    let s = "ab".repeat("2")\n', 'E0401', [2, 25]),
    positive('mem-str-ws-trim', 'mem.str.ws', '    print(" a ".trim())\n'),
    shared('mem-str-trim-arity', 'mem.str.ws', '    let s = " a ".trim(1)\n', 'E0402', [2, 13]),
    positive('mem-str-words', 'mem.str.words', '    for w in " a  b ".words() {\n        print(w)\n    }\n'),
    shared('mem-str-words-arity', 'mem.str.words', '    let w = "a b".words(1)\n', 'E0402', [2, 13]),
    positive('mem-str-lines', 'mem.str.lines', '    for l in "a\\r\\nb".lines() {\n        print(l)\n    }\n'),
    shared('mem-str-lines-arity', 'mem.str.lines', '    let w = "a".lines(1)\n', 'E0402', [2, 13]),
    positive('mem-str-split', 'mem.str.split', '    for f in "a,,b".split(",") {\n        print(f)\n    }\n'),
    shared('mem-str-split-int', 'mem.str.split', '    let w = "a,b".split(1)\n', 'E0401', [2, 25]),
    positive('mem-str-view-trim', 'mem.str.view', '    let s = "  ab  "\n    let t = s.trim_start()\n    print(t)\n'),
    shared('mem-str-view-arity', 'mem.str.view', '    let t = "ab".trim_end(1)\n', 'E0402', [2, 13]),
    positive('mem-str-bytes', 'mem.str.view.lend', '    let b = "ab".bytes()\n    print("{b.len}")\n'),
    shared('mem-str-bytes-arity', 'mem.str.view.lend', '    let b = "ab".bytes(1)\n', 'E0402', [2, 13]),
    positive('mem-str-chars', 'mem.str.chars', '    let c = "ab".chars()\n    print("{c.len}")\n'),
    shared('mem-str-chars-arity', 'mem.str.chars', '    let c = "ab".chars(1)\n', 'E0402', [2, 13]),
    positive('mem-str-parse-to-int', 'mem.str.parse', '    let n = "12".to_int() else 0\n    print("{n}")\n'),
    shared('mem-str-parse-unhandled', 'mem.str.parse', '    let n: int = "12".to_int()\n', 'E0401', [2, 18]),
    positive('mem-str-to-int-trimmed', 'mem.str.to_int', '    let n = " -3 ".to_int() else 0\n    print("{n}")\n'),
    shared('mem-str-to-int-arity', 'mem.str.to_int', '    let n = "3".to_int(10) else 0\n', 'E0402', [2, 13]),
    positive('mem-str-imm-rebuild', 'mem.str.imm', '    var s = "ab"\n    s = s + "c"\n    print(s)\n'),
    shared('mem-str-index-not-a-place', 'mem.str.imm', '    var s = "ab"\n    s[0] = 99\n', 'E0416', [3, 5]),
]

# Anchors outside the typed core until their F3 unit (or F4, F7, or none at F3)
# lands: one row each, refused by name with F0001. (anchor, body line, items)
MUT = 'fn bump(mut a: int) {\n    a += 1\n}\n'
TAKE = 'fn eat(take xs: List[int]) -> int {\n    xs.len\n}\n'
OUTSIDE = [
    ('mem.codes', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0.move', 'let xs = [1]\n    let n = eat(take xs)', TAKE),
    ('mem.tier0.move.1', 'let xs = [1]\n    let n = eat(take xs)', TAKE),
    ('mem.tier0.move.2', 'let xs = [1]\n    let ys = move xs', ''),
    ('mem.tier0.move.3', 'let xs = [1]\n    let ys = copy xs', ''),
    ('mem.tier0.move.4', 'var xs = [1]\n    let ys = move xs', ''),
    ('mem.tier0.mode', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0.mode.read', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0.mode.mut', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0.mode.take', 'let xs = [1]\n    let n = eat(take xs)', TAKE),
    ('mem.tier0.excl', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0.excl.1', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0.excl.2', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0.excl.3', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0.excl.4', 'var a = 1\n    bump(mut a)', MUT),
    ('mem.tier0.borrow', 'var a = 1\n    let r = &mut a', ''),
    ('mem.tier0.borrow.1', 'var a = 1\n    let r = &a', ''),
    ('mem.tier0.borrow.2', 'var a = 1\n    let r = &mut a', ''),
    ('mem.model.granule', 'region r {\n        print("r")\n    }', ''),
    ('mem.model.machine', 'region r {\n        print("r")\n    }', ''),
    ('mem.model.alloc', 'region r {\n        let xs = [1]\n    }', ''),
    ('mem.region', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.create', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.create.1', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.create.2', 'let r = region()', ''),
    ('mem.region.create.3', 'let r = region()\n    in r {\n        print("r")\n    }', ''),
    ('mem.region.create.4', 'let r = region()', ''),
    ('mem.region.proc', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.intra', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.intra.1', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.intra.2', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.escape', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.scalar', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.outer-write', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.copyout', 'let n = copy region r {\n        1\n    }', ''),
    ('mem.region.edge', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.edge.iso', 'let r = region()', ''),
    ('mem.region.edge.imm', 'let r = region()', ''),
    ('mem.region.edge.elem', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.edge.raw', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.region.open', 'let r = region()\n    in r {\n        print("r")\n    }', ''),
    ('mem.region.open.1', 'let r = region()\n    in r {\n        print("r")\n    }', ''),
    ('mem.region.open.2', 'let r = region()\n    in r {\n        print("r")\n    }', ''),
    ('mem.region.multiopen', 'let r = region()\n    in r {\n        print("r")\n    }', ''),
    ('mem.region.open.3', 'let r = region()\n    in r {\n        print("r")\n    }', ''),
    ('mem.region.freeze', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.freeze.1', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.freeze.2', 'let r = region()\n    let s = move r', ''),
    ('mem.region.freeze.3', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.freeze.4', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.root', 'let r = region()', ''),
    ('mem.region.imm.ret', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.promote', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.promote.1', 'region r {\n        print("r")\n    }', ''),
    ('mem.region.account', 'region r {\n        print("{region_bytes(r)}")\n    }', ''),
    ('mem.region.account.1', 'region r {\n        print("{region_bytes(r)}")\n    }', ''),
    ('mem.region.account.2', 'print("{live_region_bytes()}")', ''),
    ('mem.region.cap', 'region r(cap: 64) {\n        print("r")\n    }', ''),
    ('mem.region.cap.1', 'region r(cap: 64) {\n        print("r")\n    }', ''),
    ('mem.region.cap.2', 'region r(cap: 64) {\n        print("r")\n    }', ''),
    ('mem.region.cap.3', 'region r(cap: 64) {\n        print("r")\n    }', ''),
    ('mem.shared', 'let c = shared (1)', ''),
    ('mem.shared.rc', 'let c = shared (1)', ''),
    ('mem.shared.rc.1', 'let c = shared (1)', ''),
    ('mem.shared.rc.2', 'let c = shared (1)', ''),
    ('mem.shared.rc.3', 'let c = shared (1)', ''),
    ('mem.shared.rc.4', 'let c = shared (1)', ''),
    ('mem.shared.drop', 'let c = shared (1)', ''),
    ('mem.shared.drop.1', 'let c = shared (1)', ''),
    ('mem.shared.drop.2', 'let c = shared (1)', ''),
    ('mem.shared.drop.3', 'let c = shared (1)', ''),
    ('mem.shared.handle', 'var p = Pool[int]()', ''),
    ('mem.shared.handle.1', 'var p = Pool[int]()', ''),
    ('mem.shared.handle.2', 'var p = Pool[int]()', ''),
    ('mem.shared.handle.3', 'var p = Pool[int]()', ''),
    ('mem.unsafe', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.raw.1', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.raw.2', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.raw.3', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.raw.4', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.raw.5', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.volatile', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.volatile.1', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.volatile.2', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.volatile.3', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.door', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.scope', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.unsafe.sig', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.static', 'print("{K}")', 'const K: int = 3\n'),
    ('mem.static.1', 'print("{K}")', 'const K: int = 3\n'),
    ('mem.static.2', 'print("{K}")', 'const K: int = 3\n'),
    ('mem.static.3', 'print("{K}")', 'const K: int = 3\n'),
    ('mem.static.4', 'print("{K}")', 'const K: int = 3\n'),
    ('mem.prov', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.prov.tag', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.prov.state', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.prov.expose', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.prov.device', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.prov.region', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.ub', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.ub.defined', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.ub.closed', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.boundary', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.boundary.module', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.boundary.doc', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.boundary.trusted', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.boundary.ffi', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.iter.trait', 'let t = 1', 'trait Walk {\n    fn step(self) -> int\n}\n'),
    ('mem.iter.impl', 'let t = 1', 'trait Walk {\n    fn step(self) -> int\n}\n'),
    ('mem.str.impl', 'let t = 1', 'trait Walk {\n    fn step(self) -> int\n}\n'),
    ('mem.dyn.unsize', 'let t = 1', 'trait Walk {\n    fn step(self) -> int\n}\n'),
    ('mem.appendix', 'region r {\n        print("r")\n    }', ''),
]
for anchor, line, items in OUTSIDE:
    ROWS.append(dict(name='outside-' + anchor.replace('.', '-'), anchor=anchor,
                     source=program('    ' + line + '\n', items), exit=4, code='F0001'))
