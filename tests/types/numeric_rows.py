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
                     source=program(body), exit=0, reference=True))
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
