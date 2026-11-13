#!/usr/bin/env python3
"""Edition-4 string instructions: schema, text round trips and both machines."""
import argparse
import os
from pathlib import Path
import resource
import subprocess


def instruction(op, ty=0, data=(), uses=(), site=0):
    return f'{op} {ty} {site} {len(data)}' + ''.join(f' {v}' for v in data) + f' {len(uses)}' + ''.join(f' {v}' for v in uses)


class Program:
    def __init__(self, shapes=()):
        self.blobs = ['proof.lu']
        self.code = []
        self.shapes = list(shapes)

    def emit(self, op, ty=0, data=(), uses=(), site=0):
        value = len(self.code)
        self.code.append(instruction(op, ty, data, uses, site))
        return value

    def string(self, text):
        index = len(self.blobs)
        self.blobs.append(text)
        return self.emit('string', 3, (index,))

    def integer(self, value):
        return self.emit('const', 1, (value,))

    def text(self, code, ty, *uses, mode=0, flavor=None):
        data = (code, mode) if flavor is None else (code, mode, flavor)
        return self.emit('text', ty, data, uses, site=1)

    def finish(self, blocks=None):
        if blocks is None:
            zero = self.integer(0)
            self.emit('return', uses=(zero,))
            blocks = [((), self.code)]
        lines = ['fir 4', f'blobs {len(self.blobs)}',
                 *['blob ' + (s.encode().hex() or '-') for s in self.blobs],
                 'sites 2', 'site 0 1 1', 'site 0 7 3', f'shapes {len(self.shapes)}']
        lines += [kind + f' {len(fields)}' + ''.join(f' {t}' for t in fields) for kind, fields in self.shapes]
        lines += ['functions 1', f'function 1 0 0 {len(blocks)}']
        for params, code in blocks:
            lines += [f'block {len(params)}' + ''.join(f' {t}' for t in params) + f' {len(code)}', *code]
        return '\n'.join([*lines, 'end', ''])


def fixtures():
    p = Program(); s = p.string('éx'); n = p.text(0, 1, s); p.emit('print', uses=(n,))
    yield 'text-byte-length', p.finish(), '3\n', 'exit 0'
    p = Program(); s = p.string('éx'); lo = p.integer(0); hi = p.integer(2)
    value = p.text(1, 3, s, lo, hi); p.emit('print', uses=(value,))
    yield 'text-slice', p.finish(), 'é\n', 'exit 0'
    for name, lo, hi in [('negative', -1, 2), ('split-codepoint', 1, 2), ('reversed', 2, 0), ('past-end', 0, 4)]:
        p = Program(); s = p.string('éx'); a = p.integer(lo); b = p.integer(hi); p.text(1, 3, s, a, b)
        yield 'text-slice-' + name, p.finish(), '', 'trap bounds'
    p = Program(); s = p.string('éx'); i = p.integer(1); value = p.text(3, 1, s, i); p.emit('print', uses=(value,))
    yield 'text-byte', p.finish(), '169\n', 'exit 0'
    p = Program(); s = p.string('a'); i = p.integer(1); p.text(3, 1, s, i)
    yield 'text-byte-bounds', p.finish(), '', 'trap bounds'
    for flavor, value, expected in [(1, -42, '-42\n'), (2, -1, '18446744073709551615\n'), (4, 0x1d11e, '\U0001d11e\n')]:
        p = Program(); v = p.integer(value); text = p.text(4, 3, v, flavor=flavor); p.emit('print', uses=(text,))
        yield 'text-render-' + str(flavor), p.finish(), expected, 'exit 0'
    p = Program(); s = p.string('alphabet'); needle = p.string('alpha'); yes = p.text(6, 2, s, needle); p.emit('print', uses=(yes,))
    yield 'text-prefix', p.finish(), 'true\n', 'exit 0'
    p = Program(); s = p.string('aaaaa'); needle = p.string('aa'); count = p.text(7, 1, s, needle); p.emit('print', uses=(count,))
    yield 'text-count', p.finish(), '2\n', 'exit 0'
    for count, expected, outcome in [(3, 'ababab\n', 'exit 0'), (-1, '', 'trap assert')]:
        p = Program(); s = p.string('ab'); n = p.integer(count); value = p.text(8, 3, s, n); p.emit('print', uses=(value,))
        yield 'text-repeat-' + str(count), p.finish(), expected, outcome
    p = Program(); s = p.string('a,b,a'); old = p.string('a'); new = p.string('xy'); value = p.text(9, 3, s, old, new); p.emit('print', uses=(value,))
    yield 'text-replace', p.finish(), 'xy,b,xy\n', 'exit 0'
    for mode, text, sep, expected in [(0, 'a,,b,', ',', '4\na\n'), (1, ' a b ', '', '2\na\n'), (2, 'a\r\n\nb\n', '', '3\na\n')]:
        p = Program([('list', (3,))]); s = p.string(text); needle = p.string(sep); xs = p.text(10, 10, s, needle, mode=mode)
        n = p.emit('len', 1, uses=(xs,)); p.emit('print', uses=(n,)); zero = p.integer(0); first = p.emit('get', 3, uses=(xs, zero)); p.emit('print', uses=(first,))
        yield 'text-split-' + str(mode), p.finish(), expected, 'exit 0'
    for code, source, expected in [(2, 'éx', 'é\n'), (5, 'abcabc', '0\n'), (11, '  +42  ', '42\n'), (11, '0x10', 'none\n')]:
        inner = 3 if code == 2 else 1
        p = Program([('struct', (inner,)), ('struct', ()), ('enum', (10, 11))]); s = p.string(source)
        if code == 2:
            lo = p.integer(0); hi = p.integer(2); option = p.text(2, 12, s, lo, hi)
        elif code == 5:
            needle = p.string('abc'); option = p.text(5, 12, s, needle)
        else:
            option = p.text(11, 12, s)
        p.emit('case', data=(0, 1, 2, 0), uses=(option,))
        yes = [instruction('field', inner, data=(0,), uses=(0,)), instruction('print', uses=(1,)),
               instruction('const', 1, data=(0,)), instruction('return', uses=(3,))]
        blob = len(p.blobs); p.blobs.append('none')
        no = [instruction('string', 3, data=(blob,)), instruction('print', uses=(0,)),
              instruction('const', 1, data=(0,)), instruction('return', uses=(2,))]
        yield f'text-option-{code}-{source == "0x10"}', p.finish([((), p.code), ((10,), yes), ((), no)]), expected, 'exit 0'
    p = Program(); s = p.string('  x \u0085'); value = p.text(12, 3, s); p.emit('print', uses=(value,))
    yield 'text-trim', p.finish(), 'x\n', 'exit 0'
    for name, mode, text, lo, hi, expected in [
            ('bytes', 0, 'éx', 0, 3, '3\n169\n'),
            ('byte-fragment', 0, 'éx', 1, 2, '1\n169\n'),
            ('scalars', 1, 'é\U0001d11e', 0, 6, '2\n119070\n')]:
        p = Program(); s = p.string(text); a = p.integer(lo); b = p.integer(hi)
        xs = p.text(13, 4, s, a, b, mode=mode); length = p.emit('len', 1, uses=(xs,)); p.emit('print', uses=(length,))
        i = p.integer(0 if name == 'byte-fragment' else 1); element = p.emit('get', 1, uses=(xs, i)); p.emit('print', uses=(element,))
        yield 'text-materialize-' + name, p.finish(), expected, 'exit 0'
    p = Program(); s = p.string('éx'); a = p.integer(1); b = p.integer(2); p.text(13, 4, s, a, b, mode=1)
    yield 'text-materialize-scalar-boundary', p.finish(), '', 'trap bounds'


def cap():
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compiler', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    compiler = str(args.compiler.resolve()); bad = False
    def run(command):
        return subprocess.run(command, capture_output=True, timeout=180,
                              preexec_fn=cap if sys_platform_linux else None)
    for name, text, expected, outcome in fixtures():
        src = args.out / (name + '.fir'); src.write_text(text)
        canonical = args.out / (name + '.canonical'); canonical.unlink(missing_ok=True)
        result = run([compiler, 'fir', str(src), '-o', str(canonical)])
        ok = result.returncode == 0 and canonical.read_text() == text if canonical.exists() else False
        report = args.out / (name + '.outcome'); report.unlink(missing_ok=True)
        result = run([compiler, 'interpret', str(src), '--steps', '10000', '--bytes', '1048576', '--report', str(report)])
        status = 134 if outcome.startswith('trap ') else 0
        ok = ok and result.returncode == status and result.stdout == expected.encode() and report.exists() and report.read_text() == outcome + '\n'
        trap = outcome.removeprefix('trap ')
        stderr = f'wolf-trap: {trap}\n  at proof.lu:7:3\n'.encode() if outcome.startswith('trap ') else b''
        ok = ok and result.stderr == stderr
        if args.native:
            exe = args.out / (name + '.exe'); exe.unlink(missing_ok=True)
            built = run([compiler, 'link', str(src), '-o', str(exe)])
            if built.returncode == 0 and exe.exists():
                native = run([str(exe.resolve())]); ok = ok and native.returncode == status and native.stdout == expected.encode() and native.stderr == stderr
            else:
                ok = False
        print(('PASS' if ok else 'FAIL') + ' ' + name, flush=True); bad |= not ok
    first = next(fixtures())[1]
    for name, text, tag in [
        ('text-old-edition', first.replace('fir 4\n', 'fir 3\n', 1), 'FIR_SYNTAX'),
        ('text-unknown-code', first.replace('text 1 1 2 0 0 ', 'text 1 1 2 99 0 ', 1), 'FIR_OPCODE'),
        ('text-wrong-result', first.replace('text 1 1 2 0 0 ', 'text 3 1 2 0 0 ', 1), 'FIR_TYPE'),
        ('text-wrong-mode', first.replace('text 1 1 2 0 0 ', 'text 1 1 2 0 1 ', 1), 'FIR_LITERAL')]:
        src = args.out / (name + '.fir'); src.write_text(text)
        result = run([compiler, 'fir', str(src), '-o', str(args.out / (name + '.out'))])
        ok = result.returncode == 2 and tag.encode() in result.stderr
        print(('PASS' if ok else 'FAIL') + ' ' + name, flush=True); bad |= not ok
    return int(bad)


sys_platform_linux = os.uname().sysname == 'Linux'
if __name__ == '__main__':
    raise SystemExit(main())
