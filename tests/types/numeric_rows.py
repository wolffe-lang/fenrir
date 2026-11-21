"""Integer typing anchors, including scalar bridges and homogeneous shifts."""


def program(body):
    return 'fn main() -> int {\n' + body + '    0\n}\n'


CORE = [
    ('type.byte', '    let b: byte = 65 as byte\n'),
    ('type.byte.cast', '    let n = 3 as byte as int\n'),
    ('type.byte.interp', '    let b = 7 as byte\n    print("{b}")\n'),
    ('type.byte.op', '    let b = 1 as byte\n    let n: int = b + b\n'),
    ('type.char.cast', '    let n = 97 as char as int\n'),
    ('type.int.shift', '    let n: int = 1 << 3\n'),
    ('type.numlit.cast', '    let f = 1 as int\n'),
    ('type.numlit.cast.narrow', '    let b = 300 as u8\n'),
    ('type.numlit.cast.wrap', '    let w = 1 as wrapping[u8]\n'),
    ('type.wrap.div', '    let w = 7 as wrapping[i8]\n    let q = w / 2\n'),
]

ROWS = []
for anchor, body in CORE:
    ROWS.append(dict(name='integer-' + anchor.replace('.', '-'), anchor=anchor,
                     source=program(body), exit=0))
    if anchor in ('type.byte', 'type.byte.interp', 'type.byte.op'):
        bad = '    let b: byte = 65\n'
        code, location = 'E0401', [2, 19]
    elif anchor == 'type.int.shift':
        bad = '    let a: u8 = 1\n    let n: int = 1\n    let r = a << n\n'
        code, location = 'E0401', [4, 18]
    elif anchor == 'type.wrap.div':
        bad = '    let a = 7 as wrapping[i8]\n    let b = 2 as wrapping[u8]\n    let r = a / b\n'
        code, location = 'E0401', [4, 17]
    else:
        target = {'type.byte.cast': 'byte', 'type.char.cast': 'char',
                  'type.numlit.cast': 'int', 'type.numlit.cast.narrow': 'u8',
                  'type.numlit.cast.wrap': 'wrapping[u8]'}[anchor]
        bad = '    let b = true\n    let n = b as ' + target + '\n'
        code, location = 'E0805', [3, 13]
    ROWS.append(dict(name='integer-' + anchor.replace('.', '-') + '-refused', anchor=anchor,
                     source=program(bad), exit=2, code=code, location=location, reference=True))

# These observations are not refusal/execution parity. The released compiler
# treats bare wrapping differently from lupin, and loses nominal identity in
# the explicit shadowing annotation. Keep the original sources and answers.
ROWS.append(dict(name='integer-unapplied-wrapping-refused', anchor='type.numlit.cast.wrap',
                 source=program('    let x: wrapping = 1\n'), exit=4, code='F0001', location=[2, 12],
                 candidate_only=True, differs='fail(E0401) E0401@2:23'))
ROWS.append(dict(name='integer-unapplied-wrapping-argument-refused', anchor='type.numlit.cast.wrap',
                 source=program('    let xs = List[wrapping]()\n'), exit=4, code='F0001', location=[2, 19],
                 candidate_only=True, differs='unsupported'))
# wolf-lang#1112 confirms that this annotation resolves to the user's type.
# Fenrir's acceptance is intended. Keep the released-compiler disagreement
# pinned and uncredited until a release carries the correction.
ROWS.append(dict(name='integer-wrapping-name-shadowed', anchor='type.numlit.cast.wrap',
                 source='struct wrapping { n: int }\n' + program('    let x: wrapping = wrapping { n: 1 }\n'),
                 exit=0, candidate_only=True, differs='fail(E0401) E0401@3:23'))
ROWS.append(dict(name='integer-wrapping-constructor-shadowed', anchor='type.numlit.cast.wrap',
                 source='struct wrapping { n: int }\n' + program('    let x = wrapping { n: 1 }\n    print("{x.n}")\n'), exit=0))

# Float typing ([type.numlit]): a `{float}` literal takes only a float type; an `{integer}`
# literal adopts one; a mixed term needs a float type to reach it; a value never adopts.
# Values are binary64 words, so `200` adopting `f64` is the word of 200.0.
FLOAT = [
    dict(name='float-numlit-kind', anchor='type.numlit.kind', source=program('    let f = 1.5\n'),
         exit=0, checks=[['type', 'Binder', 2, 9, 'f64'], ['value', 'Literal', 2, 13, 4609434218613702656]]),
    dict(name='float-numlit-kind-refused', anchor='type.numlit.kind', source=program('    let n: int = 0.0\n'),
         exit=2, code='E0401', location=[2, 18], reference=True),
    dict(name='float-numlit-adopt', anchor='type.numlit.adopt', source=program('    let x: f64 = 200\n'),
         exit=0, checks=[['type', 'Literal', 2, 18, 'f64'], ['value', 'Literal', 2, 18, 4641240890982006784]]),
    dict(name='float-numlit-adopt-refused', anchor='type.numlit.adopt', source=program('    let x: u8 = 1.5\n'),
         exit=2, code='E0401', location=[2, 17], reference=True),
    dict(name='float-numlit-propagate', anchor='type.numlit.propagate',
         source=program('    let c: f64 = 100.0\n    let f = c * 1.8 + 32\n'),
         exit=0, checks=[['type', 'Binder', 3, 9, 'f64'], ['type', 'Literal', 3, 23, 'f64'],
                         ['value', 'Literal', 3, 23, 4629700416936869888]]),
    dict(name='float-numlit-propagate-division', anchor='type.numlit.propagate', source=program('    let x: f64 = 1 / 2\n'),
         exit=0, checks=[['type', 'Literal', 2, 18, 'f64'], ['type', 'Literal', 2, 22, 'f64']]),
    dict(name='float-numlit-default', anchor='type.numlit.default', source=program('    print("{0.5}")\n'),
         exit=0, checks=[['type', 'Literal', 2, 13, 'f64'], ['value', 'Literal', 2, 13, 4602678819172646912]]),
    dict(name='float-numlit-ambig', anchor='type.numlit.ambig', source=program('    let x = 1 + 2.0\n'),
         exit=2, code='E0401', location=[2, 17], reference=True),
    # Joining the kinds is the conflict, so a float type reaching the term later does not decide it.
    dict(name='float-numlit-ambig-annotated', anchor='type.numlit.ambig', source=program('    let x: f64 = 2.5 * (1 + 2)\n'),
         exit=2, code='E0401', location=[2, 24], reference=True),
    dict(name='float-numlit-value', anchor='type.numlit.value', source=program('    let x = 2.5\n    let y: f64 = x\n'),
         exit=0, checks=[['type', 'Binder', 3, 9, 'f64']]),
    dict(name='float-numlit-value-refused', anchor='type.numlit.value', source=program('    let n = 0\n    let x: f64 = n\n'),
         exit=2, code='E0401', location=[3, 18], reference=True),
    dict(name='float-numlit-cast-widen', anchor='type.numlit.cast.widen', source=program('    let f = 3 as f64\n'),
         exit=0, checks=[['type', 'Binder', 2, 9, 'f64']]),
    dict(name='float-numlit-cast-widen-refused', anchor='type.numlit.cast.widen',
         source=program('    let b = true\n    let f = b as f64\n'), exit=2, code='E0805', location=[3, 13], reference=True),
    dict(name='float-numlit-cast-trunc', anchor='type.numlit.cast.trunc', source=program('    let n = 3.7 as int\n'),
         exit=0, checks=[['type', 'Binder', 2, 9, 'int']]),
    dict(name='float-numlit-cast-trunc-refused', anchor='type.numlit.cast.trunc',
         source=program('    let f = 3.7\n    let c = f as char\n'), exit=2, code='E0805', location=[3, 13], reference=True),
    dict(name='float-not-refused', anchor='type.numlit.kind', source=program('    let f = 1.5\n    let g = !f\n'),
         exit=2, code='E0409', location=[3, 14], reference=True),
    dict(name='float-radix-spec-refused', anchor='type.numlit.kind', source=program('    let f = 1.5\n    print("{f:x}")\n'),
         exit=2, code='E0413', location=[3, 14], reference=True),
    dict(name='float-f32-refused', anchor='type.numlit.cast.widen', source=program('    let c = 97 as f32\n'),
         exit=4, code='F0001', location=[2, 19]),
]
ROWS.extend(FLOAT)
