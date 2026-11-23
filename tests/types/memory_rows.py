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
# The value tier (F3b, docs/MEMORY.md): modes type and lower, so its anchors are in scope. A refusal the modes
# make is shared with the reference (E1007, E1009, E1014); use after a move and exclusivity are static and F6's,
# so each is a named difference with the reference's answer pinned.
RD = 'fn rd(a: int) -> int {\n    a\n}\n'
ADD2 = 'fn add2(mut a: int, mut b: int) {\n    a += 1\n    b += 2\n}\n'
TWO = 'fn two(mut a: int, b: int) -> int {\n    a += b\n    b\n}\n'
POINT2 = 'struct P { x: int, y: int }\n'
ROWS += [
    # [mem.codes], [mem.tier0]: the tier's refusals are static; a mode is spelled at the call.
    positive('mem-codes-mut-call', 'mem.codes', '    var a = 1\n    bump(mut a)\n    print("{a}")\n', MUT),
    shared('mem-codes-mode-unspelled', 'mem.codes', '    var a = 1\n    bump(a)\n', 'E1007', [6, 10], MUT),
    positive('mem-tier0-take-and-copy', 'mem.tier0',
             '    let xs = [1]\n    let ys = copy xs\n    let n = eat(take xs)\n    print("{n} {ys.len}")\n', TAKE),
    shared('mem-tier0-take-unspelled', 'mem.tier0', '    let xs = [1]\n    let n = eat(xs)\n', 'E1007',
           [6, 17], TAKE),
    # [mem.tier0.move] .1 .2 .4: a move leaves no run-time trace; reading the moved place is E1001 (F6).
    positive('mem-tier0-move', 'mem.tier0.move', '    let xs = [1]\n    let ys = move xs\n    print("{ys.len}")\n'),
    differs('mem-tier0-move-read-after', 'mem.tier0.move', '    let xs = [1]\n    let ys = move xs\n    print("{xs.len} {ys.len}")\n',
            'E1001', [4, 13]),
    positive('mem-tier0-move-take', 'mem.tier0.move.1', '    let xs = [1]\n    let n = eat(take xs)\n    print("{n}")\n', TAKE),
    differs('mem-tier0-move-read-after-take', 'mem.tier0.move.1',
            '    let xs = [1]\n    let n = eat(take xs)\n    print("{xs.len} {n}")\n', 'E1001', [7, 13], TAKE),
    positive('mem-tier0-move-no-flag', 'mem.tier0.move.2',
             '    var xs = [1]\n    let ys = xs\n    xs = [2, 3]\n    print("{xs.len} {ys.len}")\n'),
    differs('mem-tier0-move-assignment-moves', 'mem.tier0.move.2',
            '    let xs = [1]\n    let ys = xs\n    print("{xs.len} {ys.len}")\n', 'E1001', [4, 13]),
    positive('mem-tier0-move-store-revives', 'mem.tier0.move.4',
             '    var xs = [1]\n    let ys = move xs\n    xs = [2]\n    print("{xs.len} {ys.len}")\n'),
    differs('mem-tier0-move-read-before-store', 'mem.tier0.move.4',
            '    var xs = [1]\n    let ys = move xs\n    print("{xs.len}")\n    xs = [2]\n', 'E1001', [4, 13]),
    # [mem.tier0.move.3]: `copy` is deep; an adapter of a `Copy` scalar copies on what would move.
    positive('mem-tier0-copy-deep', 'mem.tier0.move.3',
             '    let a = [[1]]\n    var b = copy a\n    (mut b[0]).push(2)\n    print("{a[0].len} {b[0].len}")\n'),
    positive('mem-tier0-adapter-copies', 'mem.tier0.move.3', '    let o = 3 as Off\n    let p = o\n    let q = o\n    print("{p} {q}")\n',
             'type Off = distinct int\n'),
    shared('mem-tier0-adapter-base-only', 'mem.tier0.move.3', '    let c = 7 as Col\n    let n = c as int\n', 'E0805',
           [4, 13], 'type Col = distinct u32\n'),
    # [mem.tier0.mode] .read .mut .take
    positive('mem-tier0-modes', 'mem.tier0.mode',
             '    var a = 1\n    let xs = [1]\n    bump(mut a)\n    let n = eat(take xs)\n    print("{a} {n}")\n', MUT + TAKE),
    shared('mem-tier0-mode-on-read', 'mem.tier0.mode', '    var a = 1\n    let n = rd(mut a)\n', 'E1007', [6, 20], RD),
    positive('mem-tier0-mode-read', 'mem.tier0.mode.read', '    let a = 2\n    print("{rd(a)} {a}")\n', RD),
    shared('mem-tier0-mode-read-lent-mut', 'mem.tier0.mode.read', '    print("{f(1)}")\n', 'E1014', [5, 14],
           MUT + 'fn f(a: int) -> int {\n    bump(mut a)\n    a\n}\n'),
    positive('mem-tier0-mode-mut-every-return', 'mem.tier0.mode.mut',
             '    var a = 1\n    var b = 1\n    let x = early(mut a, true)\n    let y = early(mut b, false)\n    print("{a} {b} {x} {y}")\n',
             'fn early(mut a: int, stop: bool) -> int {\n    a += 1\n    if stop { return a }\n    a += 10\n    a\n}\n'),
    shared('mem-tier0-mode-mut-not-a-place', 'mem.tier0.mode.mut', '    bump(mut 1)\n', 'E1009', [5, 14], MUT),
    positive('mem-tier0-mode-take', 'mem.tier0.mode.take', '    let xs = [1, 2]\n    print("{eat(take xs)}")\n', TAKE),
    shared('mem-tier0-mode-take-lent-mut', 'mem.tier0.mode.take', '    var xs = [1]\n    let n = eat(mut xs)\n', 'E1007',
           [6, 21], TAKE),
    # [mem.tier0.excl] .1 .2 .4: exclusivity is static (E1002, F6); disjoint places are independent.
    positive('mem-tier0-excl-disjoint-elements', 'mem.tier0.excl',
             '    var xs = [1, 2]\n    add2(mut xs[0], mut xs[1])\n    print("{xs[0]} {xs[1]}")\n', ADD2),
    differs('mem-tier0-excl-same-twice', 'mem.tier0.excl', '    var x = 1\n    add2(mut x, mut x)\n', 'E1002', [7, 21], ADD2),
    positive('mem-tier0-excl-other-place', 'mem.tier0.excl.1',
             '    var x = 1\n    let y = 5\n    let n = two(mut x, y)\n    print("{x} {n}")\n', TWO),
    differs('mem-tier0-excl-field-and-whole', 'mem.tier0.excl.1', '    var p = P { x: 1, y: 2 }\n    let n = mix(mut p.x, mut p)\n',
            'E1002', [8, 30], POINT2 + 'fn mix(mut a: int, mut q: P) -> int {\n    a += q.y\n    a\n}\n'),
    positive('mem-tier0-excl-disjoint-fields', 'mem.tier0.excl.2',
             '    var p = P { x: 1, y: 2 }\n    add2(mut p.x, mut p.y)\n    print("{p.x} {p.y}")\n', ADD2 + POINT2),
    differs('mem-tier0-excl-same-field', 'mem.tier0.excl.2', '    var p = P { x: 1, y: 2 }\n    add2(mut p.x, mut p.x)\n',
            'E1002', [8, 23], ADD2 + POINT2),
    positive('mem-tier0-excl-later-read', 'mem.tier0.excl.4', '    var x = 1\n    let n = two(mut x, x + 1)\n    print("{x} {n}")\n', TWO),
    differs('mem-tier0-excl-later-write', 'mem.tier0.excl.4', '    var xs = [1, 2]\n    let n = grow2(mut xs[0], take xs)\n',
            'E1001', [7, 23], 'fn grow2(mut a: int, take ys: List[int]) -> int {\n    a += ys.len\n    a\n}\n'),
]

# The region tier (F3c, docs/MEMORY.md): regions type, lower and run, so its anchors are in scope. A region's
# typing refusals are shared with the reference (E0401, E0402); escape (E1010), an edge between regions (E1004)
# and a region value's use after a move (E1001) are static and F6's, so each is a named difference with the
# reference's answer pinned.
FILL = 'fn fill(r: region) -> int {\n    in r {\n        print("f")\n    }\n    0\n}\n'
EATR = 'fn eatr(take r: region) -> int {\n    in r {\n        print("e")\n    }\n    0\n}\n'
BOX = 'struct Box { xs: List[int] }\n'
MK = 'fn mk() -> List[int] {\n    region r {\n        return [1]\n    }\n    [0]\n}\n'
RING = 'fn ring() -> List[int] {\n    region r {\n        let next = [1, 0]\n        return next\n    }\n    [0]\n}\n'
KEEP = '    var keep = List[List[int]]()\n'
ROWS += [
    # [mem.model.granule], [mem.model.machine], [mem.model.alloc]: an allocation lands in the ambient region.
    positive('mem-model-granule-lists-in-region', 'mem.model.granule',
             '    region r {\n        var outer = List[List[int]]()\n        var xs = [1]\n        (mut outer).push(xs)\n'
             '        print("{outer.len}")\n    }\n'),
    differs('mem-model-granule-list-escapes', 'mem.model.granule',
            KEEP + '    region r {\n        var xs = [1]\n        (mut keep).push(xs)\n    }\n', 'E1010', [5, 25]),
    positive('mem-model-machine-region-forest', 'mem.model.machine',
             '    region a {\n        var xs = [1]\n        region b {\n            var ys = [2, 3]\n'
             '            print("{ys.len} {region_bytes(b) > 0}")\n        }\n        print("{xs.len} {region_bytes(a) > 0}")\n    }\n'),
    differs('mem-model-machine-inner-to-outer', 'mem.model.machine',
            '    region a {\n        var outer = List[List[int]]()\n        region b {\n            var xs = [1]\n'
            '            (mut outer).push(xs)\n        }\n    }\n', 'E1010', [6, 30]),
    positive('mem-model-alloc-ambient', 'mem.model.alloc',
             '    let r = region()\n    in r {\n        var xs = [1, 2]\n        print("{xs.len}")\n    }\n'
             '    print("{region_bytes(r) > 0}")\n'),
    differs('mem-model-alloc-assigned-out', 'mem.model.alloc',
            '    var keep = [0]\n    region r {\n        let xs = [1, 2]\n        keep = xs\n    }\n', 'E1010', [5, 9]),
    # [mem.region], [mem.region.create] .1 .2 .3 .4: sugar blocks and affine values; `in r` enters a value.
    positive('mem-region-sugar', 'mem.region', '    region r {\n        var xs = [1, 2]\n        print("{xs.len}")\n    }\n'),
    differs('mem-region-tail-escapes', 'mem.region', '    let xs = region r {\n        [1, 2]\n    }\n', 'E1010', [3, 9]),
    positive('mem-region-create-both-forms', 'mem.region.create',
             '    region r {\n        let v = region()\n        in v {\n            print("{region_bytes(r)}")\n        }\n    }\n'),
    differs('mem-region-create-value-moved-twice', 'mem.region.create',
            '    let r = region()\n    let a = r\n    let b = r\n', 'E1001', [4, 13]),
    positive('mem-region-create-opens', 'mem.region.create.1',
             '    region r {\n        print("r")\n    }\n    let v = region()\n    in v {\n        print("v")\n    }\n'),
    shared('mem-region-create-cap-not-int', 'mem.region.create.1', '    let r = region(cap: true)\n', 'E0401', [2, 25]),
    positive('mem-region-create-value-moves', 'mem.region.create.2',
             '    let r = region()\n    let s = r\n    in s {\n        print("s")\n    }\n'),
    differs('mem-region-create-enter-after-move', 'mem.region.create.2',
            '    let r = region()\n    let s = r\n    in r {\n        print("r")\n    }\n', 'E1001', [4, 8]),
    positive('mem-region-create-passed-region', 'mem.region.create.3',
             '    let r = region()\n    let a = fill(r)\n    let b = fill(r)\n    print("{a} {b}")\n', FILL),
    shared('mem-region-create-enter-not-region', 'mem.region.create.3', '    in 1 {\n        print("x")\n    }\n',
           'E0401', [2, 8]),
    differs('mem-region-create-enter-after-take', 'mem.region.create.3',
            '    let r = region()\n    let a = eatr(take r)\n    in r {\n        print("r")\n    }\n', 'E1001', [10, 8], EATR),
    positive('mem-region-create-handle-only', 'mem.region.create.4',
             '    let r = region()\n    let n = fill(r)\n    in r {\n        print("{n}")\n    }\n', FILL),
    differs('mem-region-create-query-after-take', 'mem.region.create.4',
            '    let r = region()\n    let a = eatr(take r)\n    let n = region_bytes(r)\n', 'E1001', [10, 26], EATR),
    # [mem.region.intra] .1 .2: references inside a region are free; it is freed whole.
    positive('mem-region-intra-free-edges', 'mem.region.intra',
             '    region r {\n        var a = [1]\n        var b = [2, 3]\n        (mut a).push(b[1])\n        print("{a.len}")\n    }\n'),
    differs('mem-region-intra-escapes', 'mem.region.intra',
            KEEP + '    region r {\n        var a = [1]\n        var b = [2]\n        (mut a).push(b[0])\n        (mut keep).push(a)\n    }\n',
            'E1010', [7, 25]),
    positive('mem-region-intra-cycle', 'mem.region.intra.1',
             '    region r {\n        let next = [1, 0]\n        print("{next[next[0]]}")\n    }\n'),
    differs('mem-region-intra-cycle-returned', 'mem.region.intra.1', '    let xs = ring()\n', 'E1010', [4, 16], RING),
    positive('mem-region-intra-freed-whole', 'mem.region.intra.2',
             '    let before = live_region_bytes()\n    region r {\n        var xs = [1, 2, 3]\n        print("{xs.len}")\n    }\n'
             '    print("{before == live_region_bytes()}")\n'),
    differs('mem-region-intra-returned-out', 'mem.region.intra.2', '    let xs = mk()\n', 'E1010', [3, 16], MK),
    # [mem.region.escape], [mem.region.scalar], [mem.region.outer-write]: a value stays in its region; a scalar
    # names none; a `copy` stored outward is made outside.
    positive('mem-region-escape-copied-out', 'mem.region.escape',
             '    var outer = [[0]]\n    region r {\n        let xs = [1, 2]\n        outer[0] = copy xs\n    }\n'
             '    print("{outer[0].len}")\n'),
    differs('mem-region-escape-made-string', 'mem.region.escape',
            '    var keep = List[str]()\n    region r {\n        let s = "x".repeat(3)\n        (mut keep).push(s)\n    }\n',
            'E1010', [5, 25]),
    positive('mem-region-scalar-out', 'mem.region.scalar',
             '    var n = 0\n    region r {\n        let xs = [1, 2, 3]\n        n = xs.len\n    }\n    print("{n}")\n'),
    differs('mem-region-scalar-string-is-not', 'mem.region.scalar',
            '    var s = ""\n    region r {\n        s = "a{1}"\n    }\n', 'E1010', [4, 9]),
    positive('mem-region-outer-write-copy', 'mem.region.outer-write',
             '    var keep = List[str]()\n    region r {\n        let s = "a{1}"\n        (mut keep).push(copy s)\n    }\n'
             '    print("{keep.len}")\n'),
    differs('mem-region-outer-write-uncopied', 'mem.region.outer-write',
            '    var keep = List[str]()\n    region r {\n        let s = "a{1}"\n        (mut keep).push(s)\n    }\n',
            'E1010', [5, 25]),
    # [mem.region.edge] .elem: edges between regions are static.
    positive('mem-region-edge-field-copy', 'mem.region.edge',
             '    var b = Box { xs: [1] }\n    region r {\n        let ys = [2, 3]\n        b.xs = copy ys\n    }\n'
             '    print("{b.xs.len}")\n', BOX),
    differs('mem-region-edge-field-store', 'mem.region.edge',
            '    var b = Box { xs: [1] }\n    region r {\n        b.xs = [2, 3]\n    }\n', 'E1004', [5, 9], BOX),
    positive('mem-region-edge-elem-push', 'mem.region.edge.elem',
             '    var keep = List[int]()\n    region r {\n        let xs = [4, 5]\n        (mut keep).push(xs[0])\n    }\n'
             '    print("{keep[0]}")\n'),
    differs('mem-region-edge-elem-index-store', 'mem.region.edge.elem',
            '    var outer = [[0]]\n    region r {\n        let xs = [1, 2]\n        outer[0] = xs\n    }\n', 'E1004', [5, 9]),
    # [mem.region.open] .1 .3: re-entry is depth-counted; an outer region is written from an inner one.
    positive('mem-region-open-reenter', 'mem.region.open',
             '    region a {\n        in a {\n            var xs = [1]\n            print("{xs.len}")\n        }\n    }\n'),
    differs('mem-region-open-reentered-escape', 'mem.region.open',
            KEEP + '    region a {\n        in a {\n            var xs = [1]\n            (mut keep).push(xs)\n        }\n    }\n',
            'E1010', [6, 29]),
    positive('mem-region-open-depth', 'mem.region.open.1',
             '    region a {\n        in a {\n            in a {\n                print("{region_bytes(a)}")\n            }\n        }\n    }\n'),
    differs('mem-region-open-nested-reentry-escape', 'mem.region.open.1',
            KEEP + '    region a {\n        region b {\n            in a {\n                var xs = [1]\n'
            '                (mut keep).push(xs)\n            }\n        }\n    }\n', 'E1010', [7, 33]),
    positive('mem-region-open-outer-list-grows', 'mem.region.open.3',
             '    region a {\n        var xs = [1]\n        region b {\n            (mut xs).push(2)\n        }\n'
             '        print("{xs.len}")\n    }\n'),
    differs('mem-region-open-inner-into-outer', 'mem.region.open.3',
            '    region a {\n        var xs = [1]\n        region b {\n            let ys = [2]\n            xs = ys\n        }\n    }\n',
            'E1010', [6, 13]),
    # [mem.region.promote] .1: placement is unobservable.
    positive('mem-region-promote-small', 'mem.region.promote',
             '    region r {\n        let x = [7]\n        print("{x[0]}")\n    }\n'),
    differs('mem-region-promote-string-tail', 'mem.region.promote', '    let s = region r {\n        "a{1}"\n    }\n',
            'E1010', [3, 9]),
    positive('mem-region-promote-copy-out', 'mem.region.promote.1',
             '    var outer = [[0]]\n    region r {\n        let xs = [3]\n        outer[0] = copy xs\n    }\n'
             '    print("{outer[0][0]}")\n'),
    differs('mem-region-promote-struct-tail', 'mem.region.promote.1', '    let b = region r {\n        Box { xs: [1] }\n    }\n',
            'E1010', [4, 9], BOX),
    # [mem.region.account] .1 .2: the byte ledger.
    positive('mem-region-account-monotone', 'mem.region.account',
             '    region r {\n        let a = region_bytes(r)\n        var xs = [1, 2, 3]\n        let b = region_bytes(r)\n'
             '        print("{a} {b >= a} {xs.len}")\n    }\n'),
    differs('mem-region-account-query-after-move', 'mem.region.account',
            '    let r = region()\n    let s = r\n    let n = region_bytes(r)\n', 'E1001', [4, 26]),
    positive('mem-region-account-zero-at-creation', 'mem.region.account.1',
             '    let r = region()\n    let a = region_bytes(r)\n    in r {\n        var xs = [1, 2]\n        print("{xs.len}")\n    }\n'
             '    print("{a == 0} {region_bytes(r) > 0}")\n'),
    shared('mem-region-account-query-not-region', 'mem.region.account.1', '    let n = region_bytes(1)\n', 'E0401', [2, 26]),
    differs('mem-region-account-queried-escape', 'mem.region.account.1',
            KEEP + '    region r {\n        var xs = [1]\n        let n = region_bytes(r)\n        (mut keep).push(xs)\n    }\n',
            'E1010', [6, 25]),
    positive('mem-region-account-live', 'mem.region.account.2',
             '    let before = live_region_bytes()\n    region r {\n        var xs = [1, 2]\n'
             '        print("{live_region_bytes() > before}")\n    }\n'),
    shared('mem-region-account-live-arity', 'mem.region.account.2', '    let n = live_region_bytes(1)\n', 'E0402', [2, 13]),
    differs('mem-region-account-live-escape', 'mem.region.account.2',
            KEEP + '    region r {\n        var xs = [1, 2]\n        (mut keep).push(xs)\n    }\n    print("{live_region_bytes()}")\n',
            'E1010', [5, 25]),
    # [mem.region.cap] .1 .2: creation-time budgets.
    positive('mem-region-cap-under', 'mem.region.cap',
             '    region r(cap: 4096) {\n        var xs = [1, 2]\n        print("{xs.len}")\n    }\n'),
    shared('mem-region-cap-not-int', 'mem.region.cap', '    region r(cap: "x") {\n        print("r")\n    }\n', 'E0401', [2, 19]),
    differs('mem-region-cap-escape', 'mem.region.cap',
            KEEP + '    region r(cap: 64) {\n        var xs = [1]\n        (mut keep).push(xs)\n    }\n', 'E1010', [5, 25]),
    positive('mem-region-cap-value', 'mem.region.cap.1',
             '    let r = region(cap: 4096)\n    in r {\n        var xs = [1]\n        print("{xs.len}")\n    }\n'),
    differs('mem-region-cap-tail-escapes', 'mem.region.cap.1', '    let xs = region r(cap: 4096) {\n        [1, 2]\n    }\n',
            'E1010', [3, 9]),
    positive('mem-region-cap-expression', 'mem.region.cap.2',
             '    var n = 64\n    region r(cap: n * 64) {\n        var xs = [1]\n        print("{xs.len}")\n    }\n'),
    differs('mem-region-cap-value-moved', 'mem.region.cap.2',
            '    let r = region(cap: 64)\n    let s = r\n    in r {\n        print("r")\n    }\n', 'E1001', [4, 8]),
]

OUTSIDE = [
    # A view set (the anchor's own construct, F6): `bump(mut a)` once stood here, but modes are in the core now.
    ('mem.tier0.excl.3', 'var p = P { x: 1, y: 2, z: 3 }\n    let n = (mut p).norm()',
     'struct P { x: int, y: int, z: int }\nimpl P {\n    fn norm(mut self.{x, y}) -> int {\n        self.x\n    }\n}\n'),
    ('mem.tier0.borrow', 'var a = 1\n    let r = &mut a', ''),
    ('mem.tier0.borrow.1', 'var a = 1\n    let r = &a', ''),
    ('mem.tier0.borrow.2', 'var a = 1\n    let r = &mut a', ''),
    ('mem.region.proc', 'let p = spawn proc work(1)', 'fn work(n: int) -> int {\n    n\n}\n'),
    ('mem.region.copyout', 'let n = copy region r {\n        1\n    }', ''),
    ('mem.region.edge.iso', 'let r = region()', 'struct Node {\n    value: int,\n    next: handle Node,\n}\n'),
    ('mem.region.edge.imm', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.edge.raw', 'unsafe {\n        print("u")\n    }', ''),
    ('mem.region.open.2', 'let a = region()\n    let b = region()', 'struct Node {\n    value: int,\n    next: handle Node,\n}\n'),
    ('mem.region.multiopen', 'let a = region()\n    let b = region()', 'struct Node {\n    value: int,\n    next: handle Node,\n}\n'),
    ('mem.region.freeze', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.freeze.1', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.freeze.2', 'let r = region()\n    let s = move r\n    let f = freeze s', ''),
    ('mem.region.freeze.3', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.freeze.4', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.root', 'let r = region()', 'struct Node {\n    value: int,\n    next: handle Node,\n}\n'),
    ('mem.region.imm.ret', 'let r = region()\n    let f = freeze r', ''),
    ('mem.region.cap.3', 'let p = spawn proc work(1)', 'fn work(n: int) -> int {\n    n\n}\n'),
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
    ('mem.appendix', 'let r = region()', 'struct Node {\n    value: int,\n    next: handle Node,\n}\n'),
]
for anchor, line, items in OUTSIDE:
    ROWS.append(dict(name='outside-' + anchor.replace('.', '-'), anchor=anchor,
                     source=program('    ' + line + '\n', items), exit=4, code='F0001'))
