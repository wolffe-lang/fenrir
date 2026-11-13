#!/usr/bin/env python3
"""Assembly fixtures and deterministic output checks (runtime checks are separate)."""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess

spec = importlib.util.spec_from_file_location("fir_rows", Path(__file__).with_name("fir.py"))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
I = f.inst
spec = importlib.util.spec_from_file_location("grown_rows", Path(__file__).with_name("grown.py"))
grown = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grown)


def fixtures():
    c = I("const", 1, data=(0,))
    yield "hello", f.module([I("string", 3, data=(1,)), I("print", uses=(0,)), c, I("return", uses=(2,))]), "hello, wolf\n"
    payload = 'A' * 33 + '\0é𝄞'
    data = f.module([I('string', 3, data=(1,)), I('print', uses=(0,)), c, I('return', uses=(2,))])
    yield 'blob-boundaries', data.replace('blob 68656c6c6f2c20776f6c66', 'blob ' + payload.encode().hex()), payload + '\n'
    yield "bool", f.module([I("const", 2, data=(1,)), I("print", uses=(0,)), I("not", 2, uses=(0,)), I("print", uses=(2,)), c, I("return", uses=(4,))]), "true\nfalse\n"
    for op, a, b, answer in [("add", 20, 22, 42), ("sub", 64, 22, 42), ("mul", -6, -7, 42), ("div", -85, -2, 42), ("rem", -85, 2, -1)]:
        yield op, f.module([I("const", 1, data=(a,)), I("const", 1, data=(b,)), I(op, 1, uses=(0, 1)), I("print", uses=(2,)), c, I("return", uses=(4,))]), f"{answer}\n"
    for name, op, a, b, kind in [("overflow-add", "add", 9223372036854775807, 1, "overflow"), ("overflow-sub", "sub", -9223372036854775808, 1, "overflow"), ("overflow-mul", "mul", 9223372036854775807, 2, "overflow"), ("zero-div", "div", 7, 0, "div-zero"), ("min-div", "div", -9223372036854775808, -1, "overflow"), ("min-rem", "rem", -9223372036854775808, -1, "overflow")]:
        yield name, f.module([I("const", 1, data=(a,)), I("const", 1, data=(b,)), I(op, 1, uses=(0, 1)), I("return", uses=(2,))]), "trap:" + kind
    yield "list", f.module([I("list", 4), I("const", 1, data=(42,)), I("push", uses=(0, 1)), c, I("get", 1, uses=(0, 3)), I("print", uses=(4,)), I("len", 1, uses=(0,)), I("print", uses=(6,)), I("return", uses=(3,))]), "42\n1\n"
    yield "list-bounds", f.module([I("list", 4), I("const", 1, data=(-1,)), I("get", 1, uses=(0, 1)), I("return", uses=(2,))]), "trap:bounds"
    yield "str", f.module([I("string", 3, data=(1,)), I("concat", 3, uses=(0, 0)), I("print", uses=(1,)), c, I("return", uses=(3,))]), "hello, wolfhello, wolf\n"
    yield "struct", f.module([I("const", 1, data=(40,)), I("const", 1, data=(2,)), I("struct", f.STRUCT, uses=(0, 1)), I("field", 1, data=(0,), uses=(2,)), I("field", 1, data=(1,), uses=(2,)), I("add", 1, uses=(3, 4)), I("print", uses=(5,)), c, I("return", uses=(7,))], structs=[(1, 1)]), "42\n"
    loop = f.module([], blocks=[([], [c, I("jump", data=(1,), uses=(0,))]), ([1], [I("const", 1, data=(5,)), I("lt", 2, uses=(0, 1)), I("branch", data=(2, 3, 1), uses=(2, 0, 0))]), ([1], [I("print", uses=(0,)), I("const", 1, data=(1,)), I("add", 1, uses=(0, 2)), I("jump", data=(1,), uses=(3,))]), ([1], [c, I("return", uses=(1,))])])
    yield "while", loop, "0\n1\n2\n3\n4\n"
    swap = f.module([], blocks=[([], [I("const", 1, data=(1,)), I("const", 1, data=(2,)), I("const", 2, data=(1,)), I("jump", data=(1,), uses=(0, 1, 2))]), ([1, 1, 2], [I("const", 2, data=(0,)), I("branch", data=(1, 2, 3), uses=(2, 1, 0, 3, 0, 1))]), ([1, 1], [I("print", uses=(0,)), I("print", uses=(1,)), c, I("return", uses=(4,))])])
    yield "parallel-copy", swap, "2\n1\n"
    # Function 1 adds two arguments, including a value carried across its call.
    main = f.module([I("const", 1, data=(20,)), I("const", 1, data=(22,)), I("call", 1, data=(1,), uses=(0, 1)), I("print", uses=(2,)), c, I("return", uses=(4,))])
    callee = f.function(1, (1, 1), [0]) + "\nblock 2 1 1 2\n" + I("add", 1, uses=(0, 1)) + "\n" + I("return", uses=(2,)) + "\n"
    yield "call", main.replace("functions 1", "functions 2").replace("end\n", callee + "end\n"), "42\n"
    main = f.module([I("const", 1, data=(40,)), I("const", 1, data=(2,)), I("struct", f.STRUCT, uses=(0, 1)), I("call", f.STRUCT, data=(1,), uses=(2,)), I("field", 1, data=(0,), uses=(3,)), I("print", uses=(4,)), c, I("return", uses=(6,))], structs=[(1, 1)])
    callee = f.function(f.STRUCT, (f.STRUCT,), [0]) + f"\nblock 1 {f.STRUCT} 1\n" + I("return", uses=(0,)) + "\n"
    yield "struct-call", main.replace("functions 1", "functions 2").replace("end\n", callee + "end\n"), "40\n"
    # FIR 1: sized integers, slots, rendering and the assert trap.
    for name, text, expected, _ in grown.fixtures():
        yield name, text, expected


def blob_encoding(text, assembly):
    expected = [bytes.fromhex(line[5:]) if line[5:] != '-' else b''
                for line in text.splitlines() if line.startswith('blob ')]
    actual, chunks = {}, {}
    current = None
    for line in assembly.decode().splitlines():
        match = re.fullmatch(r'\.Lblob(\d+):', line)
        if match:
            current = int(match[1]); actual[current] = bytearray(); chunks[current] = []
        elif current is not None and line.startswith('.byte '):
            values = [int(value.strip()) for value in line[6:].split(',')]
            actual[current].extend(values); chunks[current].append(len(values))
    if set(actual) != set(range(len(expected))):
        return False
    for index, payload in enumerate(expected):
        sizes = [16] * (len(payload) // 16) + ([len(payload) % 16] if len(payload) % 16 else [])
        if bytes(actual[index]) != payload or chunks[index] != sizes:
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("compiler", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, text, expected in fixtures():
        src = a.out / (name + ".fir")
        src.write_text(text)
        (a.out / (name + ".expected")).write_text(expected)
        outputs = []
        for n in range(2):
            out = a.out / (name + f".{n}.s")
            p = subprocess.run([str(a.compiler.resolve()), "asm", str(src), "-o", str(out)], capture_output=True, text=True)
            assert p.returncode == 0, (name, p.returncode, p.stdout, p.stderr)
            outputs.append(out.read_bytes())
        assert outputs[0] == outputs[1], (name, "nondeterministic assembly")
        assert b"call __wolf_rt_main_start" in outputs[0]
        if not blob_encoding(text, outputs[0]):
            print(f'FAIL assembly-{name} blob bytes or bounded directive chunks', flush=True)
            failures += 1
            continue
        # Block jumps are direct: the pinned clef's layout converges for
        # mutually dependent short and long jumps (tests/backend/nested-loops.s).
        if b"jmp *%rax" in outputs[0]:
            print(f"FAIL assembly-{name} a block jump goes through %rax instead of a direct jmp", flush=True)
            failures += 1
            continue
        print(f"PASS assembly-{name}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
