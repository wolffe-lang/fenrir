# x86-64 instruction-form envelope

The table below preserves the initial census against clef `0ef3d84a`.
[clef#20](https://github.com/wolffe-lang/clef/pull/20), now pinned at
`900bdf0a8f8f447bcc1505ecad1f65a367105dcc`, adds those formerly refused forms.
The backend's Linux gate reruns all 640 against pinned GNU as using clef's own
object comparator. The excluded symbolic narrow-relocation form
`testw $sym,sym(%rip)` remains the named `unsupported_narrow_relocation`
refusal, never an accepted form or a skip.

This is the integer backend's planned instruction envelope through F2, not a
claim that F1 already emits every row. F2 adds enums, match, lists, Map, error
values and strings; floating-point/SIMD code generation is outside this envelope.
Every emitted instruction must belong to an observed form below. New forms
require another census row and differential before use.

References are the Intel 64 and IA-32 Architectures Software Developer's Manual,
volume 2, named instruction entries and their opcode tables. Section 2.1–2.2
supply ModRM, SIB, displacement, REX and immediate rules. Volume suffixes follow
the split A/B/D edition used by clef's instruction table; mnemonic and opcode
identify the entry independently of pagination. AT&T source spelling and
relocation policy are tested against GNU as, not inferred from the SDM.

## Probe provenance

- Source pin: clef `0ef3d84a03949a20ba008b35dc1e3bcc156a6112`.
- Probe host: **Darwin arm64**. These are host-native stage-0 Mac probes, not Linux qualification.
- Executable SHA-256: `0854b69b97eb1c9a2ab493300197da7f7009a72bbb91c2b0d6d30cb1b47fe438`.
- 640 one-instruction probes: **238 accepted, 402 refused**.
- Each sample is placed after `.text` and before a local `.Ltarget:` label.
- Status 0 must produce an object; status 1 must refuse without one. Other
  statuses fail the instrument. The exact stderr is retained below, with only
  the unique source pathname normalized to `SOURCE.s`.
- Acceptance here says only that clef assembles the sample. The required
  correctness gate uses a **Linux x86-64 build** and clef's own pinned GNU-as
  differential. Refused rows remain red, never skips or substituted encodings.

## Forms

| ID | Family | One-line sample | Intel SDM reference | Observed result |
|---|---|---|---|---|
| form-0000 | move | `movb %al, %cl` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0001 | move | `movb -16(%rbp), %al` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0002 | move | `movb %al, -16(%rbp)` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0003 | move | `movb $7, %al` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0004 | move | `movb $7, -16(%rbp)` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0005 | integer | `addb %al, %cl` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0006 | integer | `addb -16(%rbp), %al` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0007 | integer | `addb %al, -16(%rbp)` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0008 | integer | `addb $7, %al` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0009 | integer | `addb $7, -16(%rbp)` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0010 | integer | `subb %al, %cl` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0011 | integer | `subb -16(%rbp), %al` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0012 | integer | `subb %al, -16(%rbp)` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0013 | integer | `subb $7, %al` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0014 | integer | `subb $7, -16(%rbp)` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0015 | integer | `andb %al, %cl` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0016 | integer | `andb -16(%rbp), %al` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0017 | integer | `andb %al, -16(%rbp)` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0018 | integer | `andb $7, %al` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0019 | integer | `andb $7, -16(%rbp)` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0020 | integer | `orb %al, %cl` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0021 | integer | `orb -16(%rbp), %al` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0022 | integer | `orb %al, -16(%rbp)` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0023 | integer | `orb $7, %al` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0024 | integer | `orb $7, -16(%rbp)` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0025 | integer | `xorb %al, %cl` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0026 | integer | `xorb -16(%rbp), %al` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0027 | integer | `xorb %al, -16(%rbp)` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0028 | integer | `xorb $7, %al` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0029 | integer | `xorb $7, -16(%rbp)` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0030 | integer | `cmpb %al, %cl` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0031 | integer | `cmpb -16(%rbp), %al` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0032 | integer | `cmpb %al, -16(%rbp)` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0033 | integer | `cmpb $7, %al` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0034 | integer | `cmpb $7, -16(%rbp)` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0035 | test | `testb %al, %cl` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0036 | test | `testb %al, -16(%rbp)` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0037 | test | `testb $7, %al` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0038 | test | `testb $7, -16(%rbp)` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0039 | unary | `negb %al` | 2B NEG: F6/F7 /3 | accepted |
| form-0040 | unary | `negb -16(%rbp)` | 2B NEG: F6/F7 /3 | accepted |
| form-0041 | unary | `notb %al` | 2B NOT: F6/F7 /2 | accepted |
| form-0042 | unary | `notb -16(%rbp)` | 2B NOT: F6/F7 /2 | accepted |
| form-0043 | shift | `shlb $1, %al` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlb: SDM vol.2 instruction set }) |
| form-0044 | shift | `shlb $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlb: SDM vol.2 instruction set }) |
| form-0045 | shift | `shlb $7, %al` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlb: SDM vol.2 instruction set }) |
| form-0046 | shift | `shlb $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlb: SDM vol.2 instruction set }) |
| form-0047 | shift | `shlb %cl, %al` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlb: SDM vol.2 instruction set }) |
| form-0048 | shift | `shlb %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlb: SDM vol.2 instruction set }) |
| form-0049 | shift | `sarb $1, %al` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarb: SDM vol.2 instruction set }) |
| form-0050 | shift | `sarb $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarb: SDM vol.2 instruction set }) |
| form-0051 | shift | `sarb $7, %al` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarb: SDM vol.2 instruction set }) |
| form-0052 | shift | `sarb $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarb: SDM vol.2 instruction set }) |
| form-0053 | shift | `sarb %cl, %al` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarb: SDM vol.2 instruction set }) |
| form-0054 | shift | `sarb %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarb: SDM vol.2 instruction set }) |
| form-0055 | shift | `shrb $1, %al` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrb: SDM vol.2 instruction set }) |
| form-0056 | shift | `shrb $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrb: SDM vol.2 instruction set }) |
| form-0057 | shift | `shrb $7, %al` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrb: SDM vol.2 instruction set }) |
| form-0058 | shift | `shrb $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrb: SDM vol.2 instruction set }) |
| form-0059 | shift | `shrb %cl, %al` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrb: SDM vol.2 instruction set }) |
| form-0060 | shift | `shrb %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrb: SDM vol.2 instruction set }) |
| form-0061 | division | `mulb %cl` | 2B MUL: F6/F7 /4 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic mulb: SDM vol.2 instruction set }) |
| form-0062 | division | `mulb -16(%rbp)` | 2B MUL: F6/F7 /4 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic mulb: SDM vol.2 instruction set }) |
| form-0063 | division | `imulb %cl` | 2A IMUL: F6/F7 /5 (one operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulb: SDM vol.2 instruction set }) |
| form-0064 | division | `imulb -16(%rbp)` | 2A IMUL: F6/F7 /5 (one operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulb: SDM vol.2 instruction set }) |
| form-0065 | division | `divb %cl` | 2A DIV: F6/F7 /6 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic divb: SDM vol.2 instruction set }) |
| form-0066 | division | `divb -16(%rbp)` | 2A DIV: F6/F7 /6 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic divb: SDM vol.2 instruction set }) |
| form-0067 | division | `idivb %cl` | 2A IDIV: F6/F7 /7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic idivb: SDM vol.2 instruction set }) |
| form-0068 | division | `idivb -16(%rbp)` | 2A IDIV: F6/F7 /7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic idivb: SDM vol.2 instruction set }) |
| form-0069 | move | `movw %ax, %cx` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0070 | move | `movw -16(%rbp), %ax` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0071 | move | `movw %ax, -16(%rbp)` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0072 | move | `movw $7, %ax` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0073 | move | `movw $7, -16(%rbp)` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0074 | integer | `addw %ax, %cx` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0075 | integer | `addw -16(%rbp), %ax` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0076 | integer | `addw %ax, -16(%rbp)` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0077 | integer | `addw $7, %ax` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0078 | integer | `addw $7, -16(%rbp)` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0079 | integer | `subw %ax, %cx` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0080 | integer | `subw -16(%rbp), %ax` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0081 | integer | `subw %ax, -16(%rbp)` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0082 | integer | `subw $7, %ax` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0083 | integer | `subw $7, -16(%rbp)` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0084 | integer | `andw %ax, %cx` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0085 | integer | `andw -16(%rbp), %ax` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0086 | integer | `andw %ax, -16(%rbp)` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0087 | integer | `andw $7, %ax` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0088 | integer | `andw $7, -16(%rbp)` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0089 | integer | `orw %ax, %cx` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0090 | integer | `orw -16(%rbp), %ax` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0091 | integer | `orw %ax, -16(%rbp)` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0092 | integer | `orw $7, %ax` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0093 | integer | `orw $7, -16(%rbp)` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0094 | integer | `xorw %ax, %cx` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0095 | integer | `xorw -16(%rbp), %ax` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0096 | integer | `xorw %ax, -16(%rbp)` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0097 | integer | `xorw $7, %ax` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0098 | integer | `xorw $7, -16(%rbp)` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0099 | integer | `cmpw %ax, %cx` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0100 | integer | `cmpw -16(%rbp), %ax` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0101 | integer | `cmpw %ax, -16(%rbp)` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0102 | integer | `cmpw $7, %ax` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0103 | integer | `cmpw $7, -16(%rbp)` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0104 | test | `testw %ax, %cx` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic testw: SDM vol.2 instruction set }) |
| form-0105 | test | `testw %ax, -16(%rbp)` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic testw: SDM vol.2 instruction set }) |
| form-0106 | test | `testw $7, %ax` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic testw: SDM vol.2 instruction set }) |
| form-0107 | test | `testw $7, -16(%rbp)` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic testw: SDM vol.2 instruction set }) |
| form-0108 | unary | `negw %ax` | 2B NEG: F6/F7 /3 | accepted |
| form-0109 | unary | `negw -16(%rbp)` | 2B NEG: F6/F7 /3 | accepted |
| form-0110 | unary | `notw %ax` | 2B NOT: F6/F7 /2 | accepted |
| form-0111 | unary | `notw -16(%rbp)` | 2B NOT: F6/F7 /2 | accepted |
| form-0112 | shift | `shlw $1, %ax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlw: SDM vol.2 instruction set }) |
| form-0113 | shift | `shlw $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlw: SDM vol.2 instruction set }) |
| form-0114 | shift | `shlw $7, %ax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlw: SDM vol.2 instruction set }) |
| form-0115 | shift | `shlw $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlw: SDM vol.2 instruction set }) |
| form-0116 | shift | `shlw %cl, %ax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlw: SDM vol.2 instruction set }) |
| form-0117 | shift | `shlw %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shlw: SDM vol.2 instruction set }) |
| form-0118 | shift | `sarw $1, %ax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarw: SDM vol.2 instruction set }) |
| form-0119 | shift | `sarw $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarw: SDM vol.2 instruction set }) |
| form-0120 | shift | `sarw $7, %ax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarw: SDM vol.2 instruction set }) |
| form-0121 | shift | `sarw $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarw: SDM vol.2 instruction set }) |
| form-0122 | shift | `sarw %cl, %ax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarw: SDM vol.2 instruction set }) |
| form-0123 | shift | `sarw %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarw: SDM vol.2 instruction set }) |
| form-0124 | shift | `shrw $1, %ax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrw: SDM vol.2 instruction set }) |
| form-0125 | shift | `shrw $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrw: SDM vol.2 instruction set }) |
| form-0126 | shift | `shrw $7, %ax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrw: SDM vol.2 instruction set }) |
| form-0127 | shift | `shrw $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrw: SDM vol.2 instruction set }) |
| form-0128 | shift | `shrw %cl, %ax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrw: SDM vol.2 instruction set }) |
| form-0129 | shift | `shrw %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic shrw: SDM vol.2 instruction set }) |
| form-0130 | division | `mulw %cx` | 2B MUL: F6/F7 /4 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic mulw: SDM vol.2 instruction set }) |
| form-0131 | division | `mulw -16(%rbp)` | 2B MUL: F6/F7 /4 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic mulw: SDM vol.2 instruction set }) |
| form-0132 | division | `imulw %cx` | 2A IMUL: F6/F7 /5 (one operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulw: SDM vol.2 instruction set }) |
| form-0133 | division | `imulw -16(%rbp)` | 2A IMUL: F6/F7 /5 (one operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulw: SDM vol.2 instruction set }) |
| form-0134 | division | `divw %cx` | 2A DIV: F6/F7 /6 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic divw: SDM vol.2 instruction set }) |
| form-0135 | division | `divw -16(%rbp)` | 2A DIV: F6/F7 /6 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic divw: SDM vol.2 instruction set }) |
| form-0136 | division | `idivw %cx` | 2A IDIV: F6/F7 /7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic idivw: SDM vol.2 instruction set }) |
| form-0137 | division | `idivw -16(%rbp)` | 2A IDIV: F6/F7 /7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic idivw: SDM vol.2 instruction set }) |
| form-0138 | multiply | `imulw %cx, %ax` | 2A IMUL: 0F AF /r (two operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulw: SDM vol.2 instruction set }) |
| form-0139 | multiply | `imulw $7, %cx, %ax` | 2A IMUL: 6B /r ib (three operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulw: SDM vol.2 instruction set }) |
| form-0140 | multiply | `imulw $1000, %cx, %ax` | 2A IMUL: 69 /r iw/id (three operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulw: SDM vol.2 instruction set }) |
| form-0141 | multiply | `imulw -16(%rbp), %ax` | 2A IMUL: 0F AF /r (two operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulw: SDM vol.2 instruction set }) |
| form-0142 | multiply | `imulw $7, -16(%rbp), %ax` | 2A IMUL: 6B /r ib (three operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulw: SDM vol.2 instruction set }) |
| form-0143 | multiply | `imulw $1000, -16(%rbp), %ax` | 2A IMUL: 69 /r iw/id (three operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imulw: SDM vol.2 instruction set }) |
| form-0144 | move | `movl %eax, %ecx` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0145 | move | `movl -16(%rbp), %eax` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0146 | move | `movl %eax, -16(%rbp)` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0147 | move | `movl $7, %eax` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0148 | move | `movl $7, -16(%rbp)` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0149 | integer | `addl %eax, %ecx` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0150 | integer | `addl -16(%rbp), %eax` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0151 | integer | `addl %eax, -16(%rbp)` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0152 | integer | `addl $7, %eax` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0153 | integer | `addl $7, -16(%rbp)` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0154 | integer | `subl %eax, %ecx` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0155 | integer | `subl -16(%rbp), %eax` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0156 | integer | `subl %eax, -16(%rbp)` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0157 | integer | `subl $7, %eax` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0158 | integer | `subl $7, -16(%rbp)` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0159 | integer | `andl %eax, %ecx` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0160 | integer | `andl -16(%rbp), %eax` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0161 | integer | `andl %eax, -16(%rbp)` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0162 | integer | `andl $7, %eax` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0163 | integer | `andl $7, -16(%rbp)` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0164 | integer | `orl %eax, %ecx` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0165 | integer | `orl -16(%rbp), %eax` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0166 | integer | `orl %eax, -16(%rbp)` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0167 | integer | `orl $7, %eax` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0168 | integer | `orl $7, -16(%rbp)` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0169 | integer | `xorl %eax, %ecx` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0170 | integer | `xorl -16(%rbp), %eax` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0171 | integer | `xorl %eax, -16(%rbp)` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0172 | integer | `xorl $7, %eax` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0173 | integer | `xorl $7, -16(%rbp)` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0174 | integer | `cmpl %eax, %ecx` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0175 | integer | `cmpl -16(%rbp), %eax` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0176 | integer | `cmpl %eax, -16(%rbp)` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0177 | integer | `cmpl $7, %eax` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0178 | integer | `cmpl $7, -16(%rbp)` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0179 | test | `testl %eax, %ecx` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0180 | test | `testl %eax, -16(%rbp)` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0181 | test | `testl $7, %eax` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0182 | test | `testl $7, -16(%rbp)` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0183 | unary | `negl %eax` | 2B NEG: F6/F7 /3 | accepted |
| form-0184 | unary | `negl -16(%rbp)` | 2B NEG: F6/F7 /3 | accepted |
| form-0185 | unary | `notl %eax` | 2B NOT: F6/F7 /2 | accepted |
| form-0186 | unary | `notl -16(%rbp)` | 2B NOT: F6/F7 /2 | accepted |
| form-0187 | shift | `shll $1, %eax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0188 | shift | `shll $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0189 | shift | `shll $7, %eax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0190 | shift | `shll $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0191 | shift | `shll %cl, %eax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0192 | shift | `shll %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0193 | shift | `sarl $1, %eax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarl: SDM vol.2 instruction set }) |
| form-0194 | shift | `sarl $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarl: SDM vol.2 instruction set }) |
| form-0195 | shift | `sarl $7, %eax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarl: SDM vol.2 instruction set }) |
| form-0196 | shift | `sarl $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarl: SDM vol.2 instruction set }) |
| form-0197 | shift | `sarl %cl, %eax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarl: SDM vol.2 instruction set }) |
| form-0198 | shift | `sarl %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarl: SDM vol.2 instruction set }) |
| form-0199 | shift | `shrl $1, %eax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0200 | shift | `shrl $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0201 | shift | `shrl $7, %eax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0202 | shift | `shrl $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0203 | shift | `shrl %cl, %eax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0204 | shift | `shrl %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0205 | division | `mull %ecx` | 2B MUL: F6/F7 /4 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic mull: SDM vol.2 instruction set }) |
| form-0206 | division | `mull -16(%rbp)` | 2B MUL: F6/F7 /4 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic mull: SDM vol.2 instruction set }) |
| form-0207 | division | `imull %ecx` | 2A IMUL: F6/F7 /5 (one operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imull: SDM vol.2 instruction set }) |
| form-0208 | division | `imull -16(%rbp)` | 2A IMUL: F6/F7 /5 (one operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imull: SDM vol.2 instruction set }) |
| form-0209 | division | `divl %ecx` | 2A DIV: F6/F7 /6 | accepted |
| form-0210 | division | `divl -16(%rbp)` | 2A DIV: F6/F7 /6 | accepted |
| form-0211 | division | `idivl %ecx` | 2A IDIV: F6/F7 /7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic idivl: SDM vol.2 instruction set }) |
| form-0212 | division | `idivl -16(%rbp)` | 2A IDIV: F6/F7 /7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic idivl: SDM vol.2 instruction set }) |
| form-0213 | multiply | `imull %ecx, %eax` | 2A IMUL: 0F AF /r (two operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imull: SDM vol.2 instruction set }) |
| form-0214 | multiply | `imull $7, %ecx, %eax` | 2A IMUL: 6B /r ib (three operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imull: SDM vol.2 instruction set }) |
| form-0215 | multiply | `imull $1000, %ecx, %eax` | 2A IMUL: 69 /r iw/id (three operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imull: SDM vol.2 instruction set }) |
| form-0216 | multiply | `imull -16(%rbp), %eax` | 2A IMUL: 0F AF /r (two operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imull: SDM vol.2 instruction set }) |
| form-0217 | multiply | `imull $7, -16(%rbp), %eax` | 2A IMUL: 6B /r ib (three operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imull: SDM vol.2 instruction set }) |
| form-0218 | multiply | `imull $1000, -16(%rbp), %eax` | 2A IMUL: 69 /r iw/id (three operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic imull: SDM vol.2 instruction set }) |
| form-0219 | move | `movq %rax, %rcx` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0220 | move | `movq -16(%rbp), %rax` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0221 | move | `movq %rax, -16(%rbp)` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0222 | move | `movq $7, %rax` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0223 | move | `movq $7, -16(%rbp)` | 2B MOV: 88/89, 8A/8B, B0/B8, C6/C7 | accepted |
| form-0224 | integer | `addq %rax, %rcx` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0225 | integer | `addq -16(%rbp), %rax` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0226 | integer | `addq %rax, -16(%rbp)` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0227 | integer | `addq $7, %rax` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0228 | integer | `addq $7, -16(%rbp)` | 2A ADD: 00-05, 80/81/83 /0 | accepted |
| form-0229 | integer | `subq %rax, %rcx` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0230 | integer | `subq -16(%rbp), %rax` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0231 | integer | `subq %rax, -16(%rbp)` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0232 | integer | `subq $7, %rax` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0233 | integer | `subq $7, -16(%rbp)` | 2B SUB: 28-2D, 80/81/83 /5 | accepted |
| form-0234 | integer | `andq %rax, %rcx` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0235 | integer | `andq -16(%rbp), %rax` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0236 | integer | `andq %rax, -16(%rbp)` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0237 | integer | `andq $7, %rax` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0238 | integer | `andq $7, -16(%rbp)` | 2A AND: 20-25, 80/81/83 /4 | accepted |
| form-0239 | integer | `orq %rax, %rcx` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0240 | integer | `orq -16(%rbp), %rax` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0241 | integer | `orq %rax, -16(%rbp)` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0242 | integer | `orq $7, %rax` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0243 | integer | `orq $7, -16(%rbp)` | 2B OR: 08-0D, 80/81/83 /1 | accepted |
| form-0244 | integer | `xorq %rax, %rcx` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0245 | integer | `xorq -16(%rbp), %rax` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0246 | integer | `xorq %rax, -16(%rbp)` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0247 | integer | `xorq $7, %rax` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0248 | integer | `xorq $7, -16(%rbp)` | 2D XOR: 30-35, 80/81/83 /6 | accepted |
| form-0249 | integer | `cmpq %rax, %rcx` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0250 | integer | `cmpq -16(%rbp), %rax` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0251 | integer | `cmpq %rax, -16(%rbp)` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0252 | integer | `cmpq $7, %rax` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0253 | integer | `cmpq $7, -16(%rbp)` | 2A CMP: 38-3D, 80/81/83 /7 | accepted |
| form-0254 | test | `testq %rax, %rcx` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0255 | test | `testq %rax, -16(%rbp)` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0256 | test | `testq $7, %rax` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0257 | test | `testq $7, -16(%rbp)` | 2B TEST: 84/85, A8/A9, F6/F7 /0 | accepted |
| form-0258 | unary | `negq %rax` | 2B NEG: F6/F7 /3 | accepted |
| form-0259 | unary | `negq -16(%rbp)` | 2B NEG: F6/F7 /3 | accepted |
| form-0260 | unary | `notq %rax` | 2B NOT: F6/F7 /2 | accepted |
| form-0261 | unary | `notq -16(%rbp)` | 2B NOT: F6/F7 /2 | accepted |
| form-0262 | shift | `shlq $1, %rax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0263 | shift | `shlq $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0264 | shift | `shlq $7, %rax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0265 | shift | `shlq $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0266 | shift | `shlq %cl, %rax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0267 | shift | `shlq %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0268 | shift | `sarq $1, %rax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarq: SDM vol.2 instruction set }) |
| form-0269 | shift | `sarq $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarq: SDM vol.2 instruction set }) |
| form-0270 | shift | `sarq $7, %rax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarq: SDM vol.2 instruction set }) |
| form-0271 | shift | `sarq $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarq: SDM vol.2 instruction set }) |
| form-0272 | shift | `sarq %cl, %rax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarq: SDM vol.2 instruction set }) |
| form-0273 | shift | `sarq %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sarq: SDM vol.2 instruction set }) |
| form-0274 | shift | `shrq $1, %rax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0275 | shift | `shrq $1, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0276 | shift | `shrq $7, %rax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0277 | shift | `shrq $7, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0278 | shift | `shrq %cl, %rax` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0279 | shift | `shrq %cl, -16(%rbp)` | 2B SAL/SAR/SHL/SHR: D0/D1, D2/D3, C0/C1 /4,/5,/7 | accepted |
| form-0280 | division | `mulq %rcx` | 2B MUL: F6/F7 /4 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic mulq: SDM vol.2 instruction set }) |
| form-0281 | division | `mulq -16(%rbp)` | 2B MUL: F6/F7 /4 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic mulq: SDM vol.2 instruction set }) |
| form-0282 | division | `imulq %rcx` | 2A IMUL: F6/F7 /5 (one operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: bad_operands: imulq; SDM vol.2 instruction encoding table }) |
| form-0283 | division | `imulq -16(%rbp)` | 2A IMUL: F6/F7 /5 (one operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: bad_operands: imulq; SDM vol.2 instruction encoding table }) |
| form-0284 | division | `divq %rcx` | 2A DIV: F6/F7 /6 | accepted |
| form-0285 | division | `divq -16(%rbp)` | 2A DIV: F6/F7 /6 | accepted |
| form-0286 | division | `idivq %rcx` | 2A IDIV: F6/F7 /7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic idivq: SDM vol.2 instruction set }) |
| form-0287 | division | `idivq -16(%rbp)` | 2A IDIV: F6/F7 /7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic idivq: SDM vol.2 instruction set }) |
| form-0288 | multiply | `imulq %rcx, %rax` | 2A IMUL: 0F AF /r (two operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: bad_operands: imulq; SDM vol.2 instruction encoding table }) |
| form-0289 | multiply | `imulq $7, %rcx, %rax` | 2A IMUL: 6B /r ib (three operand) | accepted |
| form-0290 | multiply | `imulq $1000, %rcx, %rax` | 2A IMUL: 69 /r iw/id (three operand) | accepted |
| form-0291 | multiply | `imulq -16(%rbp), %rax` | 2A IMUL: 0F AF /r (two operand) | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: bad_operands: imulq; SDM vol.2 instruction encoding table }) |
| form-0292 | multiply | `imulq $7, -16(%rbp), %rax` | 2A IMUL: 6B /r ib (three operand) | accepted |
| form-0293 | multiply | `imulq $1000, -16(%rbp), %rax` | 2A IMUL: 69 /r iw/id (three operand) | accepted |
| form-0294 | branch | `ja .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0295 | set-condition | `seta %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic seta: SDM vol.2 instruction set }) |
| form-0296 | set-condition | `seta %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic seta: SDM vol.2 instruction set }) |
| form-0297 | set-condition | `seta -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic seta: SDM vol.2 instruction set }) |
| form-0298 | conditional-move | `cmovaw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovaw: SDM vol.2 instruction set }) |
| form-0299 | conditional-move | `cmovaw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovaw: SDM vol.2 instruction set }) |
| form-0300 | conditional-move | `cmoval %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmoval: SDM vol.2 instruction set }) |
| form-0301 | conditional-move | `cmoval -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmoval: SDM vol.2 instruction set }) |
| form-0302 | conditional-move | `cmovaq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovaq: SDM vol.2 instruction set }) |
| form-0303 | conditional-move | `cmovaq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovaq: SDM vol.2 instruction set }) |
| form-0304 | branch | `jae .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0305 | set-condition | `setae %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setae: SDM vol.2 instruction set }) |
| form-0306 | set-condition | `setae %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setae: SDM vol.2 instruction set }) |
| form-0307 | set-condition | `setae -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setae: SDM vol.2 instruction set }) |
| form-0308 | conditional-move | `cmovaew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovaew: SDM vol.2 instruction set }) |
| form-0309 | conditional-move | `cmovaew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovaew: SDM vol.2 instruction set }) |
| form-0310 | conditional-move | `cmovael %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovael: SDM vol.2 instruction set }) |
| form-0311 | conditional-move | `cmovael -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovael: SDM vol.2 instruction set }) |
| form-0312 | conditional-move | `cmovaeq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovaeq: SDM vol.2 instruction set }) |
| form-0313 | conditional-move | `cmovaeq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovaeq: SDM vol.2 instruction set }) |
| form-0314 | branch | `jb .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0315 | set-condition | `setb %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setb: SDM vol.2 instruction set }) |
| form-0316 | set-condition | `setb %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setb: SDM vol.2 instruction set }) |
| form-0317 | set-condition | `setb -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setb: SDM vol.2 instruction set }) |
| form-0318 | conditional-move | `cmovbw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbw: SDM vol.2 instruction set }) |
| form-0319 | conditional-move | `cmovbw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbw: SDM vol.2 instruction set }) |
| form-0320 | conditional-move | `cmovbl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbl: SDM vol.2 instruction set }) |
| form-0321 | conditional-move | `cmovbl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbl: SDM vol.2 instruction set }) |
| form-0322 | conditional-move | `cmovbq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbq: SDM vol.2 instruction set }) |
| form-0323 | conditional-move | `cmovbq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbq: SDM vol.2 instruction set }) |
| form-0324 | branch | `jbe .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jbe: SDM vol.2 instruction set }) |
| form-0325 | set-condition | `setbe %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setbe: SDM vol.2 instruction set }) |
| form-0326 | set-condition | `setbe %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setbe: SDM vol.2 instruction set }) |
| form-0327 | set-condition | `setbe -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setbe: SDM vol.2 instruction set }) |
| form-0328 | conditional-move | `cmovbew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbew: SDM vol.2 instruction set }) |
| form-0329 | conditional-move | `cmovbew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbew: SDM vol.2 instruction set }) |
| form-0330 | conditional-move | `cmovbel %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbel: SDM vol.2 instruction set }) |
| form-0331 | conditional-move | `cmovbel -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbel: SDM vol.2 instruction set }) |
| form-0332 | conditional-move | `cmovbeq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbeq: SDM vol.2 instruction set }) |
| form-0333 | conditional-move | `cmovbeq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovbeq: SDM vol.2 instruction set }) |
| form-0334 | branch | `jc .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0335 | set-condition | `setc %al` | 2B SETcc: 0F 90+cc /0 | accepted |
| form-0336 | set-condition | `setc %r8b` | 2B SETcc: 0F 90+cc /0 | accepted |
| form-0337 | set-condition | `setc -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | accepted |
| form-0338 | conditional-move | `cmovcw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovcw: SDM vol.2 instruction set }) |
| form-0339 | conditional-move | `cmovcw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovcw: SDM vol.2 instruction set }) |
| form-0340 | conditional-move | `cmovcl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovcl: SDM vol.2 instruction set }) |
| form-0341 | conditional-move | `cmovcl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovcl: SDM vol.2 instruction set }) |
| form-0342 | conditional-move | `cmovcq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovcq: SDM vol.2 instruction set }) |
| form-0343 | conditional-move | `cmovcq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovcq: SDM vol.2 instruction set }) |
| form-0344 | branch | `je .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0345 | set-condition | `sete %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sete: SDM vol.2 instruction set }) |
| form-0346 | set-condition | `sete %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sete: SDM vol.2 instruction set }) |
| form-0347 | set-condition | `sete -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sete: SDM vol.2 instruction set }) |
| form-0348 | conditional-move | `cmovew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovew: SDM vol.2 instruction set }) |
| form-0349 | conditional-move | `cmovew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovew: SDM vol.2 instruction set }) |
| form-0350 | conditional-move | `cmovel %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovel: SDM vol.2 instruction set }) |
| form-0351 | conditional-move | `cmovel -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovel: SDM vol.2 instruction set }) |
| form-0352 | conditional-move | `cmoveq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmoveq: SDM vol.2 instruction set }) |
| form-0353 | conditional-move | `cmoveq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmoveq: SDM vol.2 instruction set }) |
| form-0354 | branch | `jg .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jg: SDM vol.2 instruction set }) |
| form-0355 | set-condition | `setg %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setg: SDM vol.2 instruction set }) |
| form-0356 | set-condition | `setg %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setg: SDM vol.2 instruction set }) |
| form-0357 | set-condition | `setg -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setg: SDM vol.2 instruction set }) |
| form-0358 | conditional-move | `cmovgw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgw: SDM vol.2 instruction set }) |
| form-0359 | conditional-move | `cmovgw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgw: SDM vol.2 instruction set }) |
| form-0360 | conditional-move | `cmovgl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgl: SDM vol.2 instruction set }) |
| form-0361 | conditional-move | `cmovgl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgl: SDM vol.2 instruction set }) |
| form-0362 | conditional-move | `cmovgq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgq: SDM vol.2 instruction set }) |
| form-0363 | conditional-move | `cmovgq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgq: SDM vol.2 instruction set }) |
| form-0364 | branch | `jge .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jge: SDM vol.2 instruction set }) |
| form-0365 | set-condition | `setge %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setge: SDM vol.2 instruction set }) |
| form-0366 | set-condition | `setge %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setge: SDM vol.2 instruction set }) |
| form-0367 | set-condition | `setge -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setge: SDM vol.2 instruction set }) |
| form-0368 | conditional-move | `cmovgew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgew: SDM vol.2 instruction set }) |
| form-0369 | conditional-move | `cmovgew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgew: SDM vol.2 instruction set }) |
| form-0370 | conditional-move | `cmovgel %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgel: SDM vol.2 instruction set }) |
| form-0371 | conditional-move | `cmovgel -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgel: SDM vol.2 instruction set }) |
| form-0372 | conditional-move | `cmovgeq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgeq: SDM vol.2 instruction set }) |
| form-0373 | conditional-move | `cmovgeq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovgeq: SDM vol.2 instruction set }) |
| form-0374 | branch | `jl .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jl: SDM vol.2 instruction set }) |
| form-0375 | set-condition | `setl %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setl: SDM vol.2 instruction set }) |
| form-0376 | set-condition | `setl %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setl: SDM vol.2 instruction set }) |
| form-0377 | set-condition | `setl -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setl: SDM vol.2 instruction set }) |
| form-0378 | conditional-move | `cmovlw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovlw: SDM vol.2 instruction set }) |
| form-0379 | conditional-move | `cmovlw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovlw: SDM vol.2 instruction set }) |
| form-0380 | conditional-move | `cmovll %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovll: SDM vol.2 instruction set }) |
| form-0381 | conditional-move | `cmovll -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovll: SDM vol.2 instruction set }) |
| form-0382 | conditional-move | `cmovlq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovlq: SDM vol.2 instruction set }) |
| form-0383 | conditional-move | `cmovlq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovlq: SDM vol.2 instruction set }) |
| form-0384 | branch | `jle .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0385 | set-condition | `setle %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setle: SDM vol.2 instruction set }) |
| form-0386 | set-condition | `setle %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setle: SDM vol.2 instruction set }) |
| form-0387 | set-condition | `setle -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setle: SDM vol.2 instruction set }) |
| form-0388 | conditional-move | `cmovlew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovlew: SDM vol.2 instruction set }) |
| form-0389 | conditional-move | `cmovlew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovlew: SDM vol.2 instruction set }) |
| form-0390 | conditional-move | `cmovlel %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovlel: SDM vol.2 instruction set }) |
| form-0391 | conditional-move | `cmovlel -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovlel: SDM vol.2 instruction set }) |
| form-0392 | conditional-move | `cmovleq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovleq: SDM vol.2 instruction set }) |
| form-0393 | conditional-move | `cmovleq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovleq: SDM vol.2 instruction set }) |
| form-0394 | branch | `jna .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jna: SDM vol.2 instruction set }) |
| form-0395 | set-condition | `setna %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setna: SDM vol.2 instruction set }) |
| form-0396 | set-condition | `setna %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setna: SDM vol.2 instruction set }) |
| form-0397 | set-condition | `setna -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setna: SDM vol.2 instruction set }) |
| form-0398 | conditional-move | `cmovnaw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnaw: SDM vol.2 instruction set }) |
| form-0399 | conditional-move | `cmovnaw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnaw: SDM vol.2 instruction set }) |
| form-0400 | conditional-move | `cmovnal %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnal: SDM vol.2 instruction set }) |
| form-0401 | conditional-move | `cmovnal -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnal: SDM vol.2 instruction set }) |
| form-0402 | conditional-move | `cmovnaq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnaq: SDM vol.2 instruction set }) |
| form-0403 | conditional-move | `cmovnaq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnaq: SDM vol.2 instruction set }) |
| form-0404 | branch | `jnae .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jnae: SDM vol.2 instruction set }) |
| form-0405 | set-condition | `setnae %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnae: SDM vol.2 instruction set }) |
| form-0406 | set-condition | `setnae %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnae: SDM vol.2 instruction set }) |
| form-0407 | set-condition | `setnae -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnae: SDM vol.2 instruction set }) |
| form-0408 | conditional-move | `cmovnaew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnaew: SDM vol.2 instruction set }) |
| form-0409 | conditional-move | `cmovnaew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnaew: SDM vol.2 instruction set }) |
| form-0410 | conditional-move | `cmovnael %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnael: SDM vol.2 instruction set }) |
| form-0411 | conditional-move | `cmovnael -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnael: SDM vol.2 instruction set }) |
| form-0412 | conditional-move | `cmovnaeq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnaeq: SDM vol.2 instruction set }) |
| form-0413 | conditional-move | `cmovnaeq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnaeq: SDM vol.2 instruction set }) |
| form-0414 | branch | `jnb .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jnb: SDM vol.2 instruction set }) |
| form-0415 | set-condition | `setnb %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnb: SDM vol.2 instruction set }) |
| form-0416 | set-condition | `setnb %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnb: SDM vol.2 instruction set }) |
| form-0417 | set-condition | `setnb -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnb: SDM vol.2 instruction set }) |
| form-0418 | conditional-move | `cmovnbw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbw: SDM vol.2 instruction set }) |
| form-0419 | conditional-move | `cmovnbw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbw: SDM vol.2 instruction set }) |
| form-0420 | conditional-move | `cmovnbl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbl: SDM vol.2 instruction set }) |
| form-0421 | conditional-move | `cmovnbl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbl: SDM vol.2 instruction set }) |
| form-0422 | conditional-move | `cmovnbq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbq: SDM vol.2 instruction set }) |
| form-0423 | conditional-move | `cmovnbq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbq: SDM vol.2 instruction set }) |
| form-0424 | branch | `jnbe .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jnbe: SDM vol.2 instruction set }) |
| form-0425 | set-condition | `setnbe %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnbe: SDM vol.2 instruction set }) |
| form-0426 | set-condition | `setnbe %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnbe: SDM vol.2 instruction set }) |
| form-0427 | set-condition | `setnbe -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnbe: SDM vol.2 instruction set }) |
| form-0428 | conditional-move | `cmovnbew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbew: SDM vol.2 instruction set }) |
| form-0429 | conditional-move | `cmovnbew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbew: SDM vol.2 instruction set }) |
| form-0430 | conditional-move | `cmovnbel %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbel: SDM vol.2 instruction set }) |
| form-0431 | conditional-move | `cmovnbel -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbel: SDM vol.2 instruction set }) |
| form-0432 | conditional-move | `cmovnbeq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbeq: SDM vol.2 instruction set }) |
| form-0433 | conditional-move | `cmovnbeq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnbeq: SDM vol.2 instruction set }) |
| form-0434 | branch | `jnc .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jnc: SDM vol.2 instruction set }) |
| form-0435 | set-condition | `setnc %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnc: SDM vol.2 instruction set }) |
| form-0436 | set-condition | `setnc %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnc: SDM vol.2 instruction set }) |
| form-0437 | set-condition | `setnc -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnc: SDM vol.2 instruction set }) |
| form-0438 | conditional-move | `cmovncw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovncw: SDM vol.2 instruction set }) |
| form-0439 | conditional-move | `cmovncw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovncw: SDM vol.2 instruction set }) |
| form-0440 | conditional-move | `cmovncl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovncl: SDM vol.2 instruction set }) |
| form-0441 | conditional-move | `cmovncl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovncl: SDM vol.2 instruction set }) |
| form-0442 | conditional-move | `cmovncq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovncq: SDM vol.2 instruction set }) |
| form-0443 | conditional-move | `cmovncq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovncq: SDM vol.2 instruction set }) |
| form-0444 | branch | `jne .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0445 | set-condition | `setne %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setne: SDM vol.2 instruction set }) |
| form-0446 | set-condition | `setne %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setne: SDM vol.2 instruction set }) |
| form-0447 | set-condition | `setne -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setne: SDM vol.2 instruction set }) |
| form-0448 | conditional-move | `cmovnew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnew: SDM vol.2 instruction set }) |
| form-0449 | conditional-move | `cmovnew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnew: SDM vol.2 instruction set }) |
| form-0450 | conditional-move | `cmovnel %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnel: SDM vol.2 instruction set }) |
| form-0451 | conditional-move | `cmovnel -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnel: SDM vol.2 instruction set }) |
| form-0452 | conditional-move | `cmovneq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovneq: SDM vol.2 instruction set }) |
| form-0453 | conditional-move | `cmovneq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovneq: SDM vol.2 instruction set }) |
| form-0454 | branch | `jng .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jng: SDM vol.2 instruction set }) |
| form-0455 | set-condition | `setng %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setng: SDM vol.2 instruction set }) |
| form-0456 | set-condition | `setng %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setng: SDM vol.2 instruction set }) |
| form-0457 | set-condition | `setng -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setng: SDM vol.2 instruction set }) |
| form-0458 | conditional-move | `cmovngw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngw: SDM vol.2 instruction set }) |
| form-0459 | conditional-move | `cmovngw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngw: SDM vol.2 instruction set }) |
| form-0460 | conditional-move | `cmovngl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngl: SDM vol.2 instruction set }) |
| form-0461 | conditional-move | `cmovngl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngl: SDM vol.2 instruction set }) |
| form-0462 | conditional-move | `cmovngq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngq: SDM vol.2 instruction set }) |
| form-0463 | conditional-move | `cmovngq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngq: SDM vol.2 instruction set }) |
| form-0464 | branch | `jnge .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jnge: SDM vol.2 instruction set }) |
| form-0465 | set-condition | `setnge %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnge: SDM vol.2 instruction set }) |
| form-0466 | set-condition | `setnge %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnge: SDM vol.2 instruction set }) |
| form-0467 | set-condition | `setnge -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnge: SDM vol.2 instruction set }) |
| form-0468 | conditional-move | `cmovngew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngew: SDM vol.2 instruction set }) |
| form-0469 | conditional-move | `cmovngew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngew: SDM vol.2 instruction set }) |
| form-0470 | conditional-move | `cmovngel %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngel: SDM vol.2 instruction set }) |
| form-0471 | conditional-move | `cmovngel -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngel: SDM vol.2 instruction set }) |
| form-0472 | conditional-move | `cmovngeq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngeq: SDM vol.2 instruction set }) |
| form-0473 | conditional-move | `cmovngeq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovngeq: SDM vol.2 instruction set }) |
| form-0474 | branch | `jnl .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jnl: SDM vol.2 instruction set }) |
| form-0475 | set-condition | `setnl %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnl: SDM vol.2 instruction set }) |
| form-0476 | set-condition | `setnl %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnl: SDM vol.2 instruction set }) |
| form-0477 | set-condition | `setnl -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnl: SDM vol.2 instruction set }) |
| form-0478 | conditional-move | `cmovnlw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnlw: SDM vol.2 instruction set }) |
| form-0479 | conditional-move | `cmovnlw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnlw: SDM vol.2 instruction set }) |
| form-0480 | conditional-move | `cmovnll %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnll: SDM vol.2 instruction set }) |
| form-0481 | conditional-move | `cmovnll -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnll: SDM vol.2 instruction set }) |
| form-0482 | conditional-move | `cmovnlq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnlq: SDM vol.2 instruction set }) |
| form-0483 | conditional-move | `cmovnlq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnlq: SDM vol.2 instruction set }) |
| form-0484 | branch | `jnle .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jnle: SDM vol.2 instruction set }) |
| form-0485 | set-condition | `setnle %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnle: SDM vol.2 instruction set }) |
| form-0486 | set-condition | `setnle %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnle: SDM vol.2 instruction set }) |
| form-0487 | set-condition | `setnle -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnle: SDM vol.2 instruction set }) |
| form-0488 | conditional-move | `cmovnlew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnlew: SDM vol.2 instruction set }) |
| form-0489 | conditional-move | `cmovnlew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnlew: SDM vol.2 instruction set }) |
| form-0490 | conditional-move | `cmovnlel %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnlel: SDM vol.2 instruction set }) |
| form-0491 | conditional-move | `cmovnlel -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnlel: SDM vol.2 instruction set }) |
| form-0492 | conditional-move | `cmovnleq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnleq: SDM vol.2 instruction set }) |
| form-0493 | conditional-move | `cmovnleq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnleq: SDM vol.2 instruction set }) |
| form-0494 | branch | `jno .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jno: SDM vol.2 instruction set }) |
| form-0495 | set-condition | `setno %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setno: SDM vol.2 instruction set }) |
| form-0496 | set-condition | `setno %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setno: SDM vol.2 instruction set }) |
| form-0497 | set-condition | `setno -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setno: SDM vol.2 instruction set }) |
| form-0498 | conditional-move | `cmovnow %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnow: SDM vol.2 instruction set }) |
| form-0499 | conditional-move | `cmovnow -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnow: SDM vol.2 instruction set }) |
| form-0500 | conditional-move | `cmovnol %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnol: SDM vol.2 instruction set }) |
| form-0501 | conditional-move | `cmovnol -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnol: SDM vol.2 instruction set }) |
| form-0502 | conditional-move | `cmovnoq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnoq: SDM vol.2 instruction set }) |
| form-0503 | conditional-move | `cmovnoq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnoq: SDM vol.2 instruction set }) |
| form-0504 | branch | `jnp .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jnp: SDM vol.2 instruction set }) |
| form-0505 | set-condition | `setnp %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnp: SDM vol.2 instruction set }) |
| form-0506 | set-condition | `setnp %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnp: SDM vol.2 instruction set }) |
| form-0507 | set-condition | `setnp -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnp: SDM vol.2 instruction set }) |
| form-0508 | conditional-move | `cmovnpw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnpw: SDM vol.2 instruction set }) |
| form-0509 | conditional-move | `cmovnpw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnpw: SDM vol.2 instruction set }) |
| form-0510 | conditional-move | `cmovnpl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnpl: SDM vol.2 instruction set }) |
| form-0511 | conditional-move | `cmovnpl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnpl: SDM vol.2 instruction set }) |
| form-0512 | conditional-move | `cmovnpq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnpq: SDM vol.2 instruction set }) |
| form-0513 | conditional-move | `cmovnpq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnpq: SDM vol.2 instruction set }) |
| form-0514 | branch | `jns .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0515 | set-condition | `setns %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setns: SDM vol.2 instruction set }) |
| form-0516 | set-condition | `setns %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setns: SDM vol.2 instruction set }) |
| form-0517 | set-condition | `setns -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setns: SDM vol.2 instruction set }) |
| form-0518 | conditional-move | `cmovnsw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnsw: SDM vol.2 instruction set }) |
| form-0519 | conditional-move | `cmovnsw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnsw: SDM vol.2 instruction set }) |
| form-0520 | conditional-move | `cmovnsl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnsl: SDM vol.2 instruction set }) |
| form-0521 | conditional-move | `cmovnsl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnsl: SDM vol.2 instruction set }) |
| form-0522 | conditional-move | `cmovnsq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnsq: SDM vol.2 instruction set }) |
| form-0523 | conditional-move | `cmovnsq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnsq: SDM vol.2 instruction set }) |
| form-0524 | branch | `jnz .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0525 | set-condition | `setnz %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnz: SDM vol.2 instruction set }) |
| form-0526 | set-condition | `setnz %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnz: SDM vol.2 instruction set }) |
| form-0527 | set-condition | `setnz -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setnz: SDM vol.2 instruction set }) |
| form-0528 | conditional-move | `cmovnzw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnzw: SDM vol.2 instruction set }) |
| form-0529 | conditional-move | `cmovnzw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnzw: SDM vol.2 instruction set }) |
| form-0530 | conditional-move | `cmovnzl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnzl: SDM vol.2 instruction set }) |
| form-0531 | conditional-move | `cmovnzl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnzl: SDM vol.2 instruction set }) |
| form-0532 | conditional-move | `cmovnzq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnzq: SDM vol.2 instruction set }) |
| form-0533 | conditional-move | `cmovnzq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovnzq: SDM vol.2 instruction set }) |
| form-0534 | branch | `jo .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jo: SDM vol.2 instruction set }) |
| form-0535 | set-condition | `seto %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic seto: SDM vol.2 instruction set }) |
| form-0536 | set-condition | `seto %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic seto: SDM vol.2 instruction set }) |
| form-0537 | set-condition | `seto -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic seto: SDM vol.2 instruction set }) |
| form-0538 | conditional-move | `cmovow %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovow: SDM vol.2 instruction set }) |
| form-0539 | conditional-move | `cmovow -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovow: SDM vol.2 instruction set }) |
| form-0540 | conditional-move | `cmovol %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovol: SDM vol.2 instruction set }) |
| form-0541 | conditional-move | `cmovol -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovol: SDM vol.2 instruction set }) |
| form-0542 | conditional-move | `cmovoq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovoq: SDM vol.2 instruction set }) |
| form-0543 | conditional-move | `cmovoq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovoq: SDM vol.2 instruction set }) |
| form-0544 | branch | `jp .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jp: SDM vol.2 instruction set }) |
| form-0545 | set-condition | `setp %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setp: SDM vol.2 instruction set }) |
| form-0546 | set-condition | `setp %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setp: SDM vol.2 instruction set }) |
| form-0547 | set-condition | `setp -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setp: SDM vol.2 instruction set }) |
| form-0548 | conditional-move | `cmovpw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpw: SDM vol.2 instruction set }) |
| form-0549 | conditional-move | `cmovpw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpw: SDM vol.2 instruction set }) |
| form-0550 | conditional-move | `cmovpl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpl: SDM vol.2 instruction set }) |
| form-0551 | conditional-move | `cmovpl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpl: SDM vol.2 instruction set }) |
| form-0552 | conditional-move | `cmovpq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpq: SDM vol.2 instruction set }) |
| form-0553 | conditional-move | `cmovpq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpq: SDM vol.2 instruction set }) |
| form-0554 | branch | `jpe .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jpe: SDM vol.2 instruction set }) |
| form-0555 | set-condition | `setpe %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setpe: SDM vol.2 instruction set }) |
| form-0556 | set-condition | `setpe %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setpe: SDM vol.2 instruction set }) |
| form-0557 | set-condition | `setpe -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setpe: SDM vol.2 instruction set }) |
| form-0558 | conditional-move | `cmovpew %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpew: SDM vol.2 instruction set }) |
| form-0559 | conditional-move | `cmovpew -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpew: SDM vol.2 instruction set }) |
| form-0560 | conditional-move | `cmovpel %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpel: SDM vol.2 instruction set }) |
| form-0561 | conditional-move | `cmovpel -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpel: SDM vol.2 instruction set }) |
| form-0562 | conditional-move | `cmovpeq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpeq: SDM vol.2 instruction set }) |
| form-0563 | conditional-move | `cmovpeq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpeq: SDM vol.2 instruction set }) |
| form-0564 | branch | `jpo .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic jpo: SDM vol.2 instruction set }) |
| form-0565 | set-condition | `setpo %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setpo: SDM vol.2 instruction set }) |
| form-0566 | set-condition | `setpo %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setpo: SDM vol.2 instruction set }) |
| form-0567 | set-condition | `setpo -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setpo: SDM vol.2 instruction set }) |
| form-0568 | conditional-move | `cmovpow %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpow: SDM vol.2 instruction set }) |
| form-0569 | conditional-move | `cmovpow -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpow: SDM vol.2 instruction set }) |
| form-0570 | conditional-move | `cmovpol %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpol: SDM vol.2 instruction set }) |
| form-0571 | conditional-move | `cmovpol -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpol: SDM vol.2 instruction set }) |
| form-0572 | conditional-move | `cmovpoq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpoq: SDM vol.2 instruction set }) |
| form-0573 | conditional-move | `cmovpoq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovpoq: SDM vol.2 instruction set }) |
| form-0574 | branch | `js .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0575 | set-condition | `sets %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sets: SDM vol.2 instruction set }) |
| form-0576 | set-condition | `sets %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sets: SDM vol.2 instruction set }) |
| form-0577 | set-condition | `sets -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic sets: SDM vol.2 instruction set }) |
| form-0578 | conditional-move | `cmovsw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovsw: SDM vol.2 instruction set }) |
| form-0579 | conditional-move | `cmovsw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovsw: SDM vol.2 instruction set }) |
| form-0580 | conditional-move | `cmovsl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovsl: SDM vol.2 instruction set }) |
| form-0581 | conditional-move | `cmovsl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovsl: SDM vol.2 instruction set }) |
| form-0582 | conditional-move | `cmovsq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovsq: SDM vol.2 instruction set }) |
| form-0583 | conditional-move | `cmovsq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovsq: SDM vol.2 instruction set }) |
| form-0584 | branch | `jz .Ltarget` | 2A Jcc: 70+cc rel8 / 0F 80+cc rel32 | accepted |
| form-0585 | set-condition | `setz %al` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setz: SDM vol.2 instruction set }) |
| form-0586 | set-condition | `setz %r8b` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setz: SDM vol.2 instruction set }) |
| form-0587 | set-condition | `setz -16(%rbp)` | 2B SETcc: 0F 90+cc /0 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic setz: SDM vol.2 instruction set }) |
| form-0588 | conditional-move | `cmovzw %cx, %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovzw: SDM vol.2 instruction set }) |
| form-0589 | conditional-move | `cmovzw -16(%rbp), %ax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovzw: SDM vol.2 instruction set }) |
| form-0590 | conditional-move | `cmovzl %ecx, %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovzl: SDM vol.2 instruction set }) |
| form-0591 | conditional-move | `cmovzl -16(%rbp), %eax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovzl: SDM vol.2 instruction set }) |
| form-0592 | conditional-move | `cmovzq %rcx, %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovzq: SDM vol.2 instruction set }) |
| form-0593 | conditional-move | `cmovzq -16(%rbp), %rax` | 2A CMOVcc: 0F 40+cc /r | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cmovzq: SDM vol.2 instruction set }) |
| form-0594 | extension | `movsbw %cl, %ax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movsbw: SDM vol.2 instruction set }) |
| form-0595 | extension | `movsbw -16(%rbp), %ax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movsbw: SDM vol.2 instruction set }) |
| form-0596 | extension | `movsbl %cl, %eax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movsbl: SDM vol.2 instruction set }) |
| form-0597 | extension | `movsbl -16(%rbp), %eax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movsbl: SDM vol.2 instruction set }) |
| form-0598 | extension | `movsbq %cl, %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movsbq: SDM vol.2 instruction set }) |
| form-0599 | extension | `movsbq -16(%rbp), %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movsbq: SDM vol.2 instruction set }) |
| form-0600 | extension | `movswl %cx, %eax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movswl: SDM vol.2 instruction set }) |
| form-0601 | extension | `movswl -16(%rbp), %eax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movswl: SDM vol.2 instruction set }) |
| form-0602 | extension | `movswq %cx, %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movswq: SDM vol.2 instruction set }) |
| form-0603 | extension | `movswq -16(%rbp), %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movswq: SDM vol.2 instruction set }) |
| form-0604 | extension | `movslq %ecx, %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | accepted |
| form-0605 | extension | `movslq -16(%rbp), %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | accepted |
| form-0606 | extension | `movzbw %cl, %ax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movzbw: SDM vol.2 instruction set }) |
| form-0607 | extension | `movzbw -16(%rbp), %ax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movzbw: SDM vol.2 instruction set }) |
| form-0608 | extension | `movzbl %cl, %eax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | accepted |
| form-0609 | extension | `movzbl -16(%rbp), %eax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | accepted |
| form-0610 | extension | `movzbq %cl, %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movzbq: SDM vol.2 instruction set }) |
| form-0611 | extension | `movzbq -16(%rbp), %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movzbq: SDM vol.2 instruction set }) |
| form-0612 | extension | `movzwl %cx, %eax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | accepted |
| form-0613 | extension | `movzwl -16(%rbp), %eax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | accepted |
| form-0614 | extension | `movzwq %cx, %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movzwq: SDM vol.2 instruction set }) |
| form-0615 | extension | `movzwq -16(%rbp), %rax` | 2B MOVSX/MOVSXD: 0F BE/BF, 63; MOVZX: 0F B6/B7 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic movzwq: SDM vol.2 instruction set }) |
| form-0616 | sign-extend-accumulator | `cbtw` | 2A CBW/CWDE/CDQE and CWD/CDQ/CQO: 98, 99 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cbtw: SDM vol.2 instruction set }) |
| form-0617 | sign-extend-accumulator | `cwtl` | 2A CBW/CWDE/CDQE and CWD/CDQ/CQO: 98, 99 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cwtl: SDM vol.2 instruction set }) |
| form-0618 | sign-extend-accumulator | `cltq` | 2A CBW/CWDE/CDQE and CWD/CDQ/CQO: 98, 99 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cltq: SDM vol.2 instruction set }) |
| form-0619 | sign-extend-accumulator | `cwtd` | 2A CBW/CWDE/CDQE and CWD/CDQ/CQO: 98, 99 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cwtd: SDM vol.2 instruction set }) |
| form-0620 | sign-extend-accumulator | `cltd` | 2A CBW/CWDE/CDQE and CWD/CDQ/CQO: 98, 99 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cltd: SDM vol.2 instruction set }) |
| form-0621 | sign-extend-accumulator | `cqto` | 2A CBW/CWDE/CDQE and CWD/CDQ/CQO: 98, 99 | refused: clef: Assembly(Failure { origin: Origin { file: SOURCE.s, line: 2, chain:  }, reason: unknown_mnemonic cqto: SDM vol.2 instruction set }) |
| form-0622 | control-address | `movabsq $9223372036854775807, %rax` | 2B MOV: REX.W B8+rd imm64 | accepted |
| form-0623 | control-address | `movabsq $-9223372036854775808, %r10` | 2B MOV: REX.W B8+rd imm64 | accepted |
| form-0624 | control-address | `movq %r8, %r9` | 2B MOV: REX 89 /r | accepted |
| form-0625 | control-address | `movq 16(%rdi,%rsi,8), %rax` | 2B MOV: 8B /r; 2A 2.1 ModRM/SIB | accepted |
| form-0626 | control-address | `movq %rax, 16(%rdi,%rsi,8)` | 2B MOV: 89 /r; 2A 2.1 ModRM/SIB | accepted |
| form-0627 | control-address | `leaq .Ltarget(%rip), %rsi` | 2A LEA: 8D /r; 2A 2.2 RIP-relative | accepted |
| form-0628 | control-address | `leaq -16(%rbp), %rdi` | 2A LEA: 8D /r | accepted |
| form-0629 | control-address | `leaq 16(%rdi,%rsi,8), %rax` | 2A LEA: 8D /r; 2A 2.1 ModRM/SIB | accepted |
| form-0630 | control-address | `pushq %rbp` | 2B PUSH: 50+rd | accepted |
| form-0631 | control-address | `popq %rbp` | 2B POP: 58+rd | accepted |
| form-0632 | control-address | `call external_function` | 2A CALL: E8 rel32 | accepted |
| form-0633 | control-address | `call *%rax` | 2A CALL: FF /2 | accepted |
| form-0634 | control-address | `call *-16(%rbp)` | 2A CALL: FF /2 | accepted |
| form-0635 | control-address | `jmp .Ltarget` | 2A JMP: EB rel8 / E9 rel32 | accepted |
| form-0636 | control-address | `jmp *%rax` | 2A JMP: FF /4 | accepted |
| form-0637 | control-address | `jmp *-16(%rbp)` | 2A JMP: FF /4 | accepted |
| form-0638 | control-address | `ret` | 2B RET: C3 | accepted |
| form-0639 | control-address | `ud2` | 2B UD2: 0F 0B | accepted |

## Assembly directives

The emitter also uses `.text`, `.section .rodata`, `.section
 .note.GNU-stack,"",@progbits`, `.globl`, `.type SYMBOL,@function`, `.size
SYMBOL,.-SYMBOL`, labels and `.byte`. These are object-format/assembler
directives, not SDM instructions. Complete emitted-file differentials cover
their section flags, symbol properties and relocation behavior.

## Width notes

A 32-bit destination register clears its upper half: unsigned 32-to-64 widening
uses `movl`, not a nonexistent `movzlq`. There is no byte `cmov`; bool results
use SETcc plus zero extension. Multiplication has no two-operand byte IMUL.
Shift counts must be checked against Wolf semantics before the ISA masks `%cl`.
Division checks zero and signed MIN/-1 before IDIV. Overflow branches test OF
immediately after checked arithmetic. These checks are semantics, not optional
instruction-selection optimizations.
