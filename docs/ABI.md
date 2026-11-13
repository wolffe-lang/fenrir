# x86-64 ABI

Sources: Wolf `spec/04-abi.md` at `3fc86f77`, especially §1 and
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
A jump to a block is a direct `jmp` to the block's label. Its short and long
forms may depend on one another's lengths; the pinned clef's layout reaches GNU
as's fixed point for them (`tests/backend/nested-loops.s`).

## Value layouts

All scalar words and pointers are little-endian and 8-byte aligned. `int` and
`i64` are signed 64-bit, and `u64` and `uint` unsigned 64-bit. Each narrower
integer kind fills a whole word in canonical form: an `i32` sign-extended and a
`u8` zero-extended, so a 64-bit compare orders and equates them correctly. bool
is a word containing 0 or 1. A str is `{pointer, byte_length}` (two words)
naming immutable, valid UTF-8. It is not NUL-terminated. A list or map is one
opaque handle; fenrir never inspects its runtime header. A list's elements
are their FIR words, flat, so a `List[str]` element is the str's two words.
A map entry is its key's words, then its value's. Structs use
declaration-order whole-word fields, recursively, without inter-field padding;
a struct with no fields occupies no words. A stack slot holds its type's words
in the function's frame, after every block's values. This internal layout is
not a C layout or a promise about Wolf's general `#[repr(c)]` layout. No
aggregates cross the runtime C boundary by value: elements and entries pass
through caller-frame storage. An enum is its tag word, then its widest
payload's words. Floating and C membrane layouts are not implemented by this
FIR edition.

## Runtime C boundary

All calls use SysV AMD64: INTEGER arguments in `%rdi`, `%rsi`, `%rdx`, `%rcx`,
`%r8`, `%r9`, scalar return in `%rax`; stack aligned to 16 before `call`.
The string replacement entry additionally uses a seventh argument in the
caller's stack area: the caller reserves 16 bytes, writes the output pointer
at `0(%rsp)`, calls, then restores `%rsp`. Stack alignment remains 16 bytes.
An `i32` uses the low
32 bits and an `i8` the low byte. Runtime `i64` handles and pointers both occupy
one register but retain their documented meaning. Output pointers refer to
sufficient, aligned caller-frame storage, live for the complete call.

The broad sub-word widening parentheticals in the char/byte specification do
not override individual bool-hook prototypes;
[wolf-lang#1036](https://github.com/wolffe-lang/wolf-lang/issues/1036) tracks that
wording clarification. Bool calls use the documented `i8` prototype and canonical
0/1 values with zero upper register bits.

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
__wolf_rt_strbuf_i64(handle, value, spec) -> unit
__wolf_rt_strbuf_bool(handle, value: i8, spec) -> unit
__wolf_rt_strbuf_char(handle, value, spec) -> unit
__wolf_rt_strbuf_finish(handle, out) -> unit
__wolf_rt_str_eq(a_ptr, a_len, b_ptr, b_len) -> i64
__wolf_rt_str_cmp(a_ptr, a_len, b_ptr, b_len) -> i64
__wolf_rt_str_get(ptr, len, lo, hi, out) -> i64
__wolf_rt_str_find(ptr, len, needle_ptr, needle_len, reverse) -> i64
__wolf_rt_str_probe(ptr, len, needle_ptr, needle_len, mode) -> i64
__wolf_rt_str_count(ptr, len, needle_ptr, needle_len) -> i64
__wolf_rt_str_to_int(ptr, len, out) -> i64
__wolf_rt_str_trim(ptr, len, mode, out) -> unit
__wolf_rt_str_repeat(ptr, len, count, out) -> unit
__wolf_rt_str_replace(ptr, len, old_ptr, old_len, new_ptr, new_len, out) -> unit
__wolf_rt_str_split(ptr, len, separator_ptr, separator_len, mode) -> i64
__wolf_rt_str_chars(ptr, len) -> i64
__wolf_rt_list_new(elem_size) -> i64
__wolf_rt_list_push(handle, elem_ptr) -> unit
__wolf_rt_list_read(handle, index, out) -> i64
__wolf_rt_list_len(handle) -> i64
__wolf_rt_list_write(handle, index, elem_ptr) -> i64
__wolf_rt_list_pop(handle, out) -> i64
__wolf_rt_list_slice(handle, lo, hi) -> i64
__wolf_rt_list_clear(handle) -> unit
__wolf_rt_map_new(key_kind, key_size, value_offset, value_size, entry_size) -> i64
__wolf_rt_map_set(handle, entry) -> unit
__wolf_rt_map_get(handle, entry) -> i64
__wolf_rt_map_remove(handle, entry) -> i64
__wolf_rt_map_pairs(handle) -> i64
__wolf_rt_map_clear(handle) -> unit
```

`strbuf_str` uses `spec=0` for raw bytes. `strbuf_i64` appends an integer in
decimal: `spec=0` reads the word as signed, and `spec=16384` (bit 14, which the
runtime documents as "the value is unsigned") reads it as unsigned, so a `u64`
or `uint` at 2^64 − 1 renders `18446744073709551615`. An `i32` or `u8` passes
its canonical word with either spec by its own signedness. `strbuf_bool`
appends `true` or `false` with `spec=0`. `strbuf_char` takes a scalar widened
to i64 and appends its UTF-8 bytes; its public contract renders an invalid
scalar word as U+FFFD. `finish` writes 16 bytes containing the
str pair and consumes the builder handle. The parsed primitive format plan is
passed as an immediate to the same four `strbuf_` append entries; its bit fields
are documented in `docs/FIR.md`. Flavor 2 additionally sets bit 14. Strings pass
the plan as argument four, scalar values as argument three. A `format` instruction makes one
buffer, appends every part in order, and finishes it. `str_eq` returns 1 when
the byte sequences are equal; `str_cmp` returns -1, 0 or 1 in byte order
(`[mem.str.order]`); fenrir turns each into a canonical bool.
`str_get` writes a zero-copy str pair through its 16-byte output and returns
1 on a hit, or 0 for out-of-bounds, reversed or non-boundary endpoints. A
checked slice traps at its FIR site on 0; a recoverable slice constructs the
empty option with zero padding. Byte length reads the str pair's second word;
a byte read bounds-checks first, then loads and zero-extends one byte. Neither
operation materializes the string's byte list. These are the public 0.2.39
entry's documented meanings, not inferred runtime header layouts.
`str_find` returns a byte offset or -1; reverse is 0 for find and 1 for
reverse find. Probe modes are 0 starts-with, 1 ends-with, 2 contains; the
result is 1 or 0. Count is non-overlapping and empty-needle count is zero.
`str_to_int` writes one int and returns 0 on success, 1 for `parse`, unlike
`str_get`'s success convention. Trim modes are 0 both ends, 1 start, 2 end,
and the returned pair is a view. Repeat is called only after a negative
count has trapped `assert` at its FIR site. Replace takes its seventh output
pointer on the stack. Split returns a runtime `List[str]`, whose element
stride is the same 16-byte pair as FIR str; modes are 0 split, 1 words,
2 lines, with view elements and allocation only for the list. `str_chars`
returns a native char list with four-byte cells. Scalar materialization reads
each cell through `list_read` into a zeroed eight-byte scratch word, then pushes
that word into a FIR list. Byte materialization reads the string's bytes directly
into eight-byte FIR words. Neither adapter inspects a runtime list header.
A list is constructed with its element's size in bytes, eight per FIR word. Push copies
one element during the call. Read and write copy one element and return 1 on
success, 0 out of bounds; fenrir checks that result and traps `bounds` at the
FIR `get` or `set` instruction, and turns it into the option's tag for
`read`. Pop returns 1 with the last element written, or 0 for an empty list.
A slice's bounds are checked before the call (two unsigned compares, so a
negative bound fails too), and the call returns a fresh list. Clear keeps
the storage.

A map is made with `key_kind` 1 for `str` keys (compared as strings) and 0
for the others (compared by their bytes), the key's size, the value's offset
and size inside an entry, and the entry stride, here the key's words then
the value's. Each map call takes one entry staged in the frame's scratch
area: `set` reads the key and value; `get` and `remove` read the key and, on
a hit, return 1 with the bound value written into the entry's value bytes,
or return 0 when the key is absent. `pairs` returns a fresh list whose
elements are entries, each one a key-and-value record. A map's length is
`list_len` of its handle: the runtime documents that a map's header begins
with a list header. Runtime allocation owns the ambient region.
Print emits its value and a newline through the flushed public print routines.
This single-threaded FIR edition does not promise cross-thread print atomicity;
concurrency requires extending that boundary, not guessing a stream identifier.

A trap passes its kind and immutable file bytes with positive line/column, then
emits `ud2` in case a broken runtime returns. The kind numbers are the runtime's
own, read from the pinned runtime's trap entry by calling it with each number:
0 `unknown`, 1 `overflow`, 2 `div-zero`, 3 `bounds`, 4 `assert`, 5
`use-after-move`, 6 `exclusivity`, 7 `region-fault`, 8 `stale-handle`, 9
`alloc-contract`, 10 `race`, 11 `ub`, 12 `deadlock`, 13 `stack-overflow`, 14
`argument-utf8`, and `unknown` from 15. That is not `[conf.trap.set]`'s order,
which puts `assert` ninth; `[abi.target.none.hooks]` says only that overflow,
div-zero and bounds are 1, 2 and 3. fenrir emits 1, 2, 3 and 4. The Linux
differential observes each against the pinned runtime's report, `wolf-trap:
assert` included. An assertion's message is evaluated before the trap but not
passed: the ordinary build's only entry is the trap, and the reference prints
no message there either.

Checked arithmetic follows the operand kind (`src/sem/`). A signed
64-bit add, subtract or multiply tests OF; an `i32` one uses the 32-bit form,
tests OF and sign-extends the result back to its word. An unsigned 64-bit add or
subtract tests CF, and a multiply uses the one-operand `mulq`, whose OF/CF report
a nonzero high half; a `u8` one uses the byte form, tests CF (OF for `mulb`) and
zero-extends. Division checks zero, then for a signed kind its own MIN / -1,
before `idivq` on the sign-extended words; an unsigned kind clears `%rdx` and
uses `divq`. No hardware SIGFPE substitutes for the runtime report. Unsigned
comparison uses `setb`. The runtime reports `wolf-trap: KIND`, then
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
renames it into place. Failure preserves an existing OUTPUT. Each tool's
standard output goes to the staging file `tool.out` and is copied to fenrir's
standard error only when that tool fails, so a successful link prints nothing.
Only the four known staging files are removed; a pre-existing staging directory
is refused.
`FENRIR_TOOLCHAIN` selects the staged root (default `.wolf-bin`); the tools are
`bin/clef` and `bin/ligature`, runtime `musl/libwolf_rt.a`, and sysroot
`bundle/sysroot`. Arguments are separate argv entries, never shell text.

## Interface change record

- **For FIR edition 4's first primitives:** `str_get` supplies checked and
  recoverable zero-copy slices; length and byte reads use the str pair
  directly. All existing word layouts and the internal call plan remain
  unchanged.

- **`fenrir-fir-0`** introduced the internal plan above for `int`, `bool`,
  `str`, `List[int]` and scalar structs, and the runtime entries for start-up,
  the sited trap, printing, string buffers of str segments, and integer lists.
- **For FIR edition 1:** the integer kinds' canonical words; structs with `str`
  and integer fields, and with no fields; stack slots in the frame;
  `strbuf_i64` with its unsigned spec bit, `strbuf_bool`, `str_eq` and
  `str_cmp`; the `assert` trap kind 4; width-aware checked arithmetic and
  unsigned division and comparison. The internal call plan is unchanged.
- **For the lowering:** a block jump is `leaq` of its label, then `jmp *%rax`,
  in place of a direct `jmp`, whose short and long forms could keep clef's
  layout from converging (`nested-loops` in `tests/lower/rows.py`). The
  internal call plan is unchanged.
- **For the lowering's driver:** a tool's standard output is staged in
  `tool.out` and shown on fenrir's standard error only when the tool fails;
  the link boundary is otherwise unchanged.
- **For direct block jumps:** a block jump is a direct `jmp` again, since the
  pinned clef converges on mutually dependent short and long jumps. A row in
  `tests/backend/assembly.py` refuses an indirect block jump by name.
- **For FIR edition 3:** lists of every element type, flat in their words;
  maps; the enum layout; the runtime entries `list_write`, `list_pop`,
  `list_slice`, `list_clear` and the `map_` entries, with an entry staged in
  the frame's scratch area. The internal call plan is unchanged.
