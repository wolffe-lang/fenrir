#!/usr/bin/env python3
"""Census of the integer x86-64 encoding envelope planned through F2."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess


def forms():
    rows = []
    def add(group, sample, reference):
        rows.append({"id": f"form-{len(rows):04d}", "group": group, "sample": sample, "sdm": reference})
    widths = [("b", "%al", "%cl"), ("w", "%ax", "%cx"), ("l", "%eax", "%ecx"), ("q", "%rax", "%rcx")]
    for suffix, a, b in widths:
        for ops in [f"{a}, {b}", f"-16(%rbp), {a}", f"{a}, -16(%rbp)", f"$7, {a}", "$7, -16(%rbp)"]:
            add("move", f"mov{suffix} {ops}", "2B MOV: 88/89, 8A/8B, B0/B8, C6/C7")
        for op, ref in [("add", "2A ADD: 00-05, 80/81/83 /0"), ("sub", "2B SUB: 28-2D, 80/81/83 /5"), ("and", "2A AND: 20-25, 80/81/83 /4"), ("or", "2B OR: 08-0D, 80/81/83 /1"), ("xor", "2D XOR: 30-35, 80/81/83 /6"), ("cmp", "2A CMP: 38-3D, 80/81/83 /7")]:
            for ops in [f"{a}, {b}", f"-16(%rbp), {a}", f"{a}, -16(%rbp)", f"$7, {a}", "$7, -16(%rbp)"]:
                add("integer", f"{op}{suffix} {ops}", ref)
        for ops in [f"{a}, {b}", f"{a}, -16(%rbp)", f"$7, {a}", "$7, -16(%rbp)"]:
            add("test", f"test{suffix} {ops}", "2B TEST: 84/85, A8/A9, F6/F7 /0")
        for op, ref in [("neg", "2B NEG: F6/F7 /3"), ("not", "2B NOT: F6/F7 /2")]:
            for dst in [a, "-16(%rbp)"]:
                add("unary", f"{op}{suffix} {dst}", ref)
        for op in ["shl", "sar", "shr"]:
            for count in ["$1", "$7", "%cl"]:
                for dst in [a, "-16(%rbp)"]:
                    add("shift", f"{op}{suffix} {count}, {dst}", "2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7")
        for op, ref in [("mul", "2B MUL: F6/F7 /4"), ("imul", "2A IMUL: F6/F7 /5 (one operand)"), ("div", "2A DIV: F6/F7 /6"), ("idiv", "2A IDIV: F6/F7 /7")]:
            for src in [b, "-16(%rbp)"]:
                add("division", f"{op}{suffix} {src}", ref)
        if suffix != "b":
            for src in [b, "-16(%rbp)"]:
                add("multiply", f"imul{suffix} {src}, {a}", "2A IMUL: 0F AF /r (two operand)")
                add("multiply", f"imul{suffix} $7, {src}, {a}", "2A IMUL: 6B /r ib (three operand)")
                add("multiply", f"imul{suffix} $1000, {src}, {a}", "2A IMUL: 69 /r iw/id (three operand)")
    # Include canonical conditions and documented aliases: same encoding, distinct spellings.
    conditions = "a ae b be c e g ge l le na nae nb nbe nc ne ng nge nl nle no np ns nz o p pe po s z".split()
    for cc in conditions:
        add("branch", f"j{cc} .Ltarget", "2A Jcc: 70+cc rel8 / 0F 80+cc rel32")
        for dst in ["%al", "%r8b", "-16(%rbp)"]:
            add("set-condition", f"set{cc} {dst}", "2B SETcc: 0F 90+cc /0")
        for suffix, a, b in widths[1:]:
            for src in [b, "-16(%rbp)"]:
                add("conditional-move", f"cmov{cc}{suffix} {src}, {a}", "2A CMOVcc: 0F 40+cc /r")
    for op, source, dest in [("movsbw", "%cl", "%ax"), ("movsbl", "%cl", "%eax"), ("movsbq", "%cl", "%rax"), ("movswl", "%cx", "%eax"), ("movswq", "%cx", "%rax"), ("movslq", "%ecx", "%rax"), ("movzbw", "%cl", "%ax"), ("movzbl", "%cl", "%eax"), ("movzbq", "%cl", "%rax"), ("movzwl", "%cx", "%eax"), ("movzwq", "%cx", "%rax")]:
        for src in [source, "-16(%rbp)"]:
            add("extension", f"{op} {src}, {dest}", "2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7")
    for op in ["cbtw", "cwtl", "cltq", "cwtd", "cltd", "cqto"]:
        add("sign-extend-accumulator", op, "2A CBW/CWDE/CDQE and CWD/CDQ/CQO: 98, 99")
    for sample, ref in [
        ("movabsq $9223372036854775807, %rax", "2B MOV: REX.W B8+rd imm64"),
        ("movabsq $-9223372036854775808, %r10", "2B MOV: REX.W B8+rd imm64"),
        ("movq %r8, %r9", "2B MOV: REX 89 /r"),
        ("movq 16(%rdi,%rsi,8), %rax", "2B MOV: 8B /r; 2A 2.1 ModRM/SIB"),
        ("movq %rax, 16(%rdi,%rsi,8)", "2B MOV: 89 /r; 2A 2.1 ModRM/SIB"),
        ("leaq .Ltarget(%rip), %rsi", "2A LEA: 8D /r; 2A 2.2 RIP-relative"),
        ("leaq -16(%rbp), %rdi", "2A LEA: 8D /r"),
        ("leaq 16(%rdi,%rsi,8), %rax", "2A LEA: 8D /r; 2A 2.1 ModRM/SIB"),
        ("pushq %rbp", "2B PUSH: 50+rd"),
        ("popq %rbp", "2B POP: 58+rd"),
        ("call external_function", "2A CALL: E8 rel32"),
        ("call *%rax", "2A CALL: FF /2"),
        ("call *-16(%rbp)", "2A CALL: FF /2"),
        ("jmp .Ltarget", "2A JMP: EB rel8 / E9 rel32"),
        ("jmp *%rax", "2A JMP: FF /4"),
        ("jmp *-16(%rbp)", "2A JMP: FF /4"),
        ("ret", "2B RET: C3"),
        ("ud2", "2B UD2: 0F 0B"),
    ]:
        add("control-address", sample, ref)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clef", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--doc", type=Path, required=True)
    ap.add_argument("--pin", required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    rows = forms()
    for row in rows:
        src = a.out / (row["id"] + ".s")
        obj = a.out / (row["id"] + ".o")
        src.write_text(".text\n" + row["sample"] + "\n.Ltarget:\n")
        p = subprocess.run([str(a.clef.resolve()), "--64", "-o", str(obj), str(src)], capture_output=True, text=True, timeout=30)
        if p.returncode not in (0, 1):
            raise AssertionError((row, "unexpected probe status", p.returncode, p.stderr))
        row["status"] = p.returncode
        row["diagnostic"] = p.stderr.strip().replace(str(src), "SOURCE.s")
        row["object"] = obj.is_file()
        assert row["object"] == (p.returncode == 0), row
        print(row["id"], "accepted" if p.returncode == 0 else row["diagnostic"], flush=True)
    host = platform.system() + " " + platform.machine()
    sha = hashlib.sha256(a.clef.read_bytes()).hexdigest()
    result = {"host": host, "clef_pin": a.pin, "clef_binary_sha256": sha, "rows": rows}
    (a.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    yes = sum(r["status"] == 0 for r in rows)
    lines = ["# x86-64 instruction-form envelope", "", "This is the integer backend's planned instruction envelope through F2, not a", "claim that F1 already emits every row. F2 adds enums, match, lists, Map, error", "values and strings; floating-point/SIMD code generation is outside this envelope.", "Every emitted instruction must belong to an observed form below. New forms", "require another census row and differential before use.", "", "References are the Intel 64 and IA-32 Architectures Software Developer's Manual,", "volume 2, named instruction entries and their opcode tables. Section 2.1–2.2", "supply ModRM, SIB, displacement, REX and immediate rules. Volume suffixes follow", "the split A/B/D edition used by clef's instruction table; mnemonic and opcode", "identify the entry independently of pagination. AT&T source spelling and", "relocation policy are tested against GNU as, not inferred from the SDM.", "", "## Probe provenance", "", f"- Source pin: clef `{a.pin}`.", f"- Probe host: **{host}**. These are host-native stage-0 Mac probes, not Linux qualification." if platform.system() == "Darwin" else f"- Probe host: **{host}**.", f"- Executable SHA-256: `{sha}`.", f"- {len(rows)} one-instruction probes: **{yes} accepted, {len(rows)-yes} refused**.", "- Each sample is placed after `.text` and before a local `.Ltarget:` label.", "- Status 0 must produce an object; status 1 must refuse without one. Other", "  statuses fail the instrument. The exact stderr is retained below, with only", "  the unique source pathname normalized to `SOURCE.s`.", "- Acceptance here says only that clef assembles the sample. The required", "  correctness gate uses a **Linux x86-64 build** and clef's own pinned GNU-as", "  differential. Refused rows remain red, never skips or substituted encodings.", "", "## Forms", "", "| ID | Family | One-line sample | Intel SDM reference | Observed result |", "|---|---|---|---|---|"]
    for r in rows:
        verdict = "accepted" if r["status"] == 0 else "refused: " + r["diagnostic"].replace("\n", " / ")
        lines.append(f"| {r['id']} | {r['group']} | `{r['sample']}` | {r['sdm']} | {verdict.replace('|', '&#124;')} |")
    lines += ["", "## Assembly directives", "", "The emitter also uses `.text`, `.section .rodata`, `.section", " .note.GNU-stack,\"\",@progbits`, `.globl`, `.type SYMBOL,@function`, `.size", "SYMBOL,.-SYMBOL`, labels and `.byte`. These are object-format/assembler", "directives, not SDM instructions. Complete emitted-file differentials cover", "their section flags, symbol properties and relocation behavior.", "", "## Width notes", "", "A 32-bit destination register clears its upper half: unsigned 32-to-64 widening", "uses `movl`, not a nonexistent `movzlq`. There is no byte `cmov`; bool results", "use SETcc plus zero extension. Multiplication has no two-operand byte IMUL.", "Shift counts must be checked against Wolf semantics before the ISA masks `%cl`.", "Division checks zero and signed MIN/-1 before IDIV. Overflow branches test OF", "immediately after checked arithmetic. These checks are semantics, not optional", "instruction-selection optimizations."]
    a.doc.write_text("\n".join(lines) + "\n")
    refused = sorted({r["sample"].split()[0] for r in rows if r["status"]})
    print("REFUSED MNEMONICS:", ", ".join(refused))


if __name__ == "__main__":
    main()
