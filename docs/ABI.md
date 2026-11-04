# x86-64 ABI

Sources: Wolf `spec/04-abi.md` at `5f1f1c94`, especially §1 and
`[abi.target.main]`; the public `extern "C"` signatures and documentation in
that revision's `wolf_rt`; System V AMD64 psABI §3.2; Intel SDM instruction
semantics. No compiler implementation is an ABI reference for this backend.

## Internal calls

`[abi.native.layout]` leaves native field order unspecified;
`[abi.native.call]` permits small aggregates in registers and multiple returns
and requires each backend to publish its target contract.
`[abi.native.unstable]` makes the native ABI versioned and unstable. Together
these clauses leave internal layouts and calling plans to the implementation. It does **not** specify register-by-register interoperability
between separately compiled native functions from different compilers. Fenrir
therefore defines its own internal plan, `fenrir-fir-0`, within those freedoms.
Only the documented C runtime boundary is shared with the reference compiler.
Mixing another compiler's native Wolf functions into these calls is unsupported.

A function receives two pointers: `%rdi` addresses its caller-owned result slot;
`%rsi` addresses the packed argument words, in declaration order. Unit results
occupy zero words. The callee copies arguments to its own frame before executing
its first block; a returned value is copied into the result slot before return.
Scalar structs are copied whole, never returned as addresses of callee locals.
The result and argument pointers are saved in frame slots before any call.

The F1 allocator is **stack-everything**, not a register allocator with liveness
analysis. Each value receives consecutive 8-byte words once, with a per-block
index. `%rax`, `%rcx`, `%rdx`, `%r10` and `%r11` are scratch, and runtime argument
registers are caller-saved. `%rbp` is saved/restored. No other callee-saved
register is modified. Frames round up to 16 bytes; after `pushq %rbp`, subtracting
that multiple preserves 16-byte stack alignment at every call. There is no red
zone, unwind table, landing pad or implicit exception path. Allocation is linear
in value count and aggregate word count. Branch argument copies use a separate
staging area, so backedges and parameter permutations cannot overwrite sources.

## Value layouts

All scalar words and pointers are little-endian and 8-byte aligned. `int` is
signed 64-bit; bool is a word containing 0 or 1. A str is `{pointer, byte_length}`
(two words) naming immutable, valid UTF-8. It is not NUL-terminated. A `List[int]`
is one opaque handle; fenrir never inspects its runtime header. Scalar structs
use declaration-order whole-word fields, recursively, without inter-field
padding. This internal bool layout is not a C bool layout or a promise about
Wolf's general `#[repr(c)]` layout. No aggregates cross the runtime C boundary by
value. General narrow integer, floating, enum, Map and C membrane layouts are
not implemented by this FIR edition.

## Runtime C boundary

All calls use SysV AMD64: INTEGER arguments in `%rdi`, `%rsi`, `%rdx`, `%rcx`,
`%r8`, `%r9`, scalar return in `%rax`; stack aligned to 16 before `call`.
The current runtime calls never exceed six arguments. An `i32` uses the low
32 bits and an `i8` the low byte. Runtime `i64` handles and pointers both occupy
one register but retain their documented meaning. Output pointers refer to
sufficient, aligned caller-frame storage, live for the complete call.

The emitted C `main(argc: i32, argv: pointer, envp: pointer) -> i32` calls
`__wolf_rt_main_start` first with those exact arguments, then invokes FIR
function 0. Its integer return supplies the process status.

These are the public interfaces used by the first backend; `pointer` below is
a machine pointer, and every unlabeled integer parameter is `i64`.

```text
__wolf_rt_main_start(argc: i32, argv: pointer, envp: pointer) -> unit
__wolf_rt_trap_at(kind: i32, file: pointer, file_len, line, col) -> never
__wolf_rt_print_str(ptr: pointer, len) -> unit
__wolf_rt_print_i64(value) -> unit
__wolf_rt_print_bool(value: i8) -> unit
__wolf_rt_strbuf_new() -> i64
__wolf_rt_strbuf_str(handle, ptr, len, spec) -> unit
__wolf_rt_strbuf_finish(handle, out) -> unit
__wolf_rt_list_new(elem_size) -> i64
__wolf_rt_list_push(handle, elem_ptr) -> unit
__wolf_rt_list_read(handle, index, out) -> i64
__wolf_rt_list_len(handle) -> i64
```

`strbuf_str` uses `spec=0` for raw bytes. `finish` writes 16 bytes containing the
str pair and consumes the builder handle. A list is constructed with element
size 8. Push copies eight bytes during the call. Read writes eight bytes and
returns 1 on success, 0 on out-of-bounds; fenrir checks that result and traps
`bounds` at the FIR get instruction. Runtime allocation owns the ambient region.
Print emits its value and a newline through the flushed public print routines.
This single-threaded FIR edition does not promise cross-thread print atomicity;
concurrency requires extending that boundary, not guessing a stream identifier.

A trap passes its kind and immutable file bytes with positive line/column, then
emits `ud2` in case a broken runtime returns. Checked add/subtract/multiply test
OF. Division checks zero and signed MIN/-1 before `idivq`; no hardware SIGFPE
substitutes for the runtime report. The runtime reports `wolf-trap: KIND`, then
`  at FILE:LINE:COL`, and terminates with 134 on the native Linux runtime.

## Link boundary

Assembly goes only to clef, with `--64 -o OBJECT SOURCE.s`. Its own object
comparator checks section bytes, relocation tuples and structural symbols
against pinned GNU as; symbol/string-table serialization order need not match.
This is not a claim that the entire object files have identical serialization.

Ligature receives `-o OUTPUT OBJECT libwolf_rt.a -lpthread -ldl -lm
-Wl,--gc-sections`, with `LIGATURE_SYSROOT` naming the licensed musl bundle.
The runtime must be the matching release's **musl** archive, not its GNU/Linux
archive. Ligature supplies musl CRT/libc from that sysroot and produces static
non-PIE ELF64 x86-64. No external assembler or linker fallback is permitted.
Toolchain digests and licensed input provenance belong to the repository pins.

`fenrir link FILE.fir -o OUTPUT` compiles FIR in an exclusively created
`OUTPUT.fenrir-build` directory, assembles, links and verifies the candidate, then
renames it into place. Failure preserves an existing OUTPUT. Only the three
known staging files are removed; a pre-existing staging directory is refused.
`FENRIR_TOOLCHAIN` selects the staged root (default `.wolf-bin`); the tools are
`bin/clef` and `bin/ligature`, runtime `musl/libwolf_rt.a`, and sysroot
`bundle/sysroot`. Arguments are separate argv entries, never shell text.
