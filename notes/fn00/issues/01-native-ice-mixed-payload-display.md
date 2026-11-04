# Native ICE while displaying mixed row payloads

## Reproducer

Public corpus row: `corpus/rows/mixed_payload_display.lu`.

```lu
//! check: run(exit=0, stdout="A(0)\nB(p)\nA(0)\nB(p)\n")
//! phase: run
//! conforms: err.rows, type.interp.row
```

Public spec and corpus revision: `5f1f1c949582f53121e4047bc83c86f23ff72240` of `wolffe-lang/wolf-lang`. Observed with the published archives on Linux x86-64; both recorded passes agree:

- `wolf-0.2.36-x86_64-unknown-linux-gnu.tar.gz` — sha256 `d383c74c8cd123b9d9dfaa268271d4f004294f85c2b230237d0ef07027d9500d`.
- `lupin-0.1.58-x86_64-unknown-linux-gnu.tar.gz` — sha256 `34f52792bb59bc7565e0edc1235cd47d9a6ad13d5e6528993627f2e699b62193`.

The command below uses the archives' own layout: keep each release's bundled files beside its executable and put the release commands on `PATH`. The recording's relocation required `WOLF_STD` and `WOLF_RT_LIB` only to locate files kept beside the executable in the unpacked archive; no overrides are needed here.

From the public wolf-lang checkout at that revision, in a shell without `set -e`:

```sh
mkdir -p target
wolf run --no-cache -o target/repro corpus/rows/mixed_payload_display.lu
printf 'native process status: %s\n' "$?"
lupin conform-run corpus/rows/mixed_payload_display.lu --json
printf 'Lupin tool process status: %s\n' "$?"
```

`conform-run` reports the program outcome in JSON; its own successful process status is not the program's status. Lupin output below is the decoded recorded `stdout_inline`, not the literal JSON command output.

## Observed results

Native `wolf run` process status: **2**; recorded verdict: `tool-error`. Compilation fails before the program runs; no native conformance record was produced.

Native stdout:

(empty)

Native stderr (complete and exact recorded output; compiler binary output, not implementation source):

```text
wolf build: ICE: lowered WIR failed verification
wir verify error [type] in @show: b2: `%13 = sext.i64 %6`: integer conversion needs integer types
--- offending function ---
fn @show(i64) {
  fact deref %37 16 : op
  fact region %37 r0 : op
b0(%0: i64):
  %1: mem.r2 = region.foreign 1
  %2: mem.r1 = region.foreign 0
  %3 = call @f(%0)
  %4: bool = eu.is_err %3
  br %4, b1, b24
b1:
  %5: i64 = eu.err %3
  %6: union{i64, {ptr, i64}} = eu.err %3, 0
  call @__wolf_rt_print_begin()
  %7 = call @wolf.tag_name(%5)
  %8 = agg.get %7, 0
  %9 = agg.get %7, 1
  call @__wolf_rt_print_str(%8, %9)
  %10 = iconst.i64 1
  %11 = icmp.eq %5, %10
  br %11, b2, b3
b2:
  %12 = data.addr @str.1
  call @__wolf_rt_print_str(%12, %10)
  %13 = sext.i64 %6
  call @__wolf_rt_print_i64(%13)
  %14 = data.addr @str.2
  call @__wolf_rt_print_str(%14, %10)
  jmp b6
b3:
  %15 = iconst.i64 2
  %16 = icmp.eq %5, %15
  br %16, b4, b5
b4:
  %17 = data.addr @str.1
  call @__wolf_rt_print_str(%17, %10)
  %18 = agg.get %6, 0
  %19 = agg.get %6, 1
  call @__wolf_rt_print_str(%18, %19)
  %20 = data.addr @str.2
  call @__wolf_rt_print_str(%20, %10)
  jmp b6
b5:
  jmp b6
b6:
  %21 = data.addr @str.3
  call @__wolf_rt_print_str(%21, %10)
  call @__wolf_rt_print_end(%10)
  %22 = call @__wolf_rt_strbuf_new()
  %23 = call @wolf.tag_name(%5)
  %24 = agg.get %23, 0
  %25 = agg.get %23, 1
  %26 = iconst.i64 0
  call @__wolf_rt_strbuf_str(%22, %24, %25, %26)
  br %11, b7, b8
b7:
  %27 = data.addr @str.1
  call @__wolf_rt_strbuf_str(%22, %27, %10, %26)
  %28 = sext.i64 %6
  call @__wolf_rt_strbuf_i64(%22, %28, %26)
  %29 = data.addr @str.2
  call @__wolf_rt_strbuf_str(%22, %29, %10, %26)
  jmp b11
b8:
  %30 = iconst.i64 2
  %31 = icmp.eq %5, %30
  br %31, b9, b10
b9:
  %32 = data.addr @str.1
  call @__wolf_rt_strbuf_str(%22, %32, %10, %26)
  %33 = agg.get %6, 0
  %34 = agg.get %6, 1
  call @__wolf_rt_strbuf_str(%22, %33, %34, %26)
  %35 = data.addr @str.2
  call @__wolf_rt_strbuf_str(%22, %35, %10, %26)
  jmp b11
b10:
  jmp b11
b11:
  %36 = iconst.i64 16
  %37: ptr, %38: mem.r0 = stack.alloc %36
  %39 = call @__wolf_rt_strbuf_finish(%22, %37, %38)
  %40 = load.ptr %37, %39
  %41 = iconst.i64 8
  %42 = ptr.off %37, %41, 1
  %43 = load.i64 %42, %39
  %44 = icmp.eq %0, %26
  br %44, b12, b13
b12:
  %45 = data.addr @str.4
  %46 = iconst.i64 4
  %47 = agg.make %45, %46
  jmp b14(%47)
b13:
  %48 = data.addr @str.5
  %49 = iconst.i64 4
  %50 = agg.make %48, %49
  jmp b14(%50)
b14(%51: {ptr, i64}):
  %52 = agg.get %51, 0
  %53 = agg.get %51, 1
  %54 = icmp.eq %43, %53
  %55 = bconst true
  %56 = bconst false
  br %54, b15, b21(%56)
b15:
  %57 = iconst.i64 64
  %58 = icmp.sgt %53, %57
  br %58, b16, b17
b16:
  %59 = call @__wolf_rt_str_eq(%40, %43, %52, %53)
  %60 = icmp.ne %59, %26
  br %60, b21(%55), b21(%56)
b17:
  jmp b18(%26)
b18(%61: i64):
  %62 = icmp.slt %61, %53
  br %62, b19, b21(%55)
b19:
  %63 = ptr.off %40, %61, 1
  %64 = load.i8 %63, %1
  %65 = zext.i64 %64
  %66 = ptr.off %52, %61, 1
  %67 = load.i8 %66, %1
  %68 = zext.i64 %67
  %69 = icmp.eq %65, %68
  br %69, b20, b21(%56)
b20:
  %70 = iadd.wrap %61, %10
  jmp b18(%70)
b21(%71: bool):
  br %71, b22, b23
b22:
  ret
b23:
  trap
b24:
  %72: i64 = eu.ok %3
  %73 = iconst.i64 2
  %74 = icmp.eq %72, %73
  br %74, b25, b26
b25:
  ret
b26:
  trap
}

```

Lupin `conform-run` tool process status: **0**; record verdict: `exit(0)`; phase reached: `run`. Recorded program exit status: **0**.

Lupin program stdout:

```text
A(0)
B(p)
A(0)
B(p)
```

Lupin stderr: (empty).

Relevant exact JSON record fields (not the whole record):

```json
{
  "impl": "lupin",
  "impl_version": "0.1.58",
  "phase_reached": "run",
  "verdict": "exit(0)",
  "stdout_inline": "A(0)\nB(p)\nA(0)\nB(p)\n"
}
```

## Spec and disposition

`spec/10-types.md`, `[type.interp.row]`:

> - `[type.interp.row]` A caught row value (`else |err|`, a `match`
>   binding) renders as **the tag's name**, then `(p1, p2)` when the
>   tag carries a payload, each payload rendered by its own rule:
>   `too_short`, `BadDigit(q, 1)`, `closed`.

The row constructs `A(int)` and `B(str)`, catches the error, prints it, and builds an interpolated string from it. The header requires four lines, exactly as Lupin produces. The native compiler is wrong here: it reports an internal verification failure instead of compiling this specified row rendering. The recorded failure is an ICE, not an assertion trap or an unsupported result. The complete diagnostic above is evidence only; no implementation source was consulted and no internal repair is inferred.
