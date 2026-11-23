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
A copy or zero fill of at most 16 words is straight-line moves through `%rax`;
a wider one is a single counted loop, `%rcx` down to zero with indexed moves, so
the text of a copy does not grow with the value's width (`tests/backend/copy_width.py`).
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

## Private scalar leaf

Text operation 14 calls one unexported module-local scalar predicate. This leaf
uses a private SysV-shaped register interface: string pointer in `%rdi`, byte
length in `%rsi`, byte index in `%rdx`, signed width result in `%rax`. Zero means
an invalid index or boundary and the caller reports `bounds` at the instruction's
site; nonzero follows `docs/FIR.md`. It uses only caller-saved registers, touches
no stack storage and calls no runtime entry. The ordinary result-pointer/packed-
arguments Wolf call plan is unchanged. It performs no allocation and checks the
index and scalar extent before any continuation-byte read.

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
__wolf_rt_strbuf_f64(handle, value: f64, spec) -> unit
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
__wolf_rt_str_case(ptr, len, mode, out) -> unit
__wolf_rt_str_from_utf8(handle, out) -> i64
__wolf_rt_write_str(stream, ptr, len, spec) -> unit
__wolf_rt_list_new(elem_size) -> i64
__wolf_rt_list_push(handle, elem_ptr) -> unit
__wolf_rt_list_read(handle, index, out) -> i64
__wolf_rt_list_len(handle) -> i64
__wolf_rt_list_write(handle, index, elem_ptr) -> i64
__wolf_rt_list_pop(handle, out) -> i64
__wolf_rt_list_slice(handle, lo, hi) -> i64
__wolf_rt_list_clear(handle) -> unit
__wolf_rt_list_reserve(handle, capacity) -> unit
__wolf_rt_map_new(key_kind, key_size, value_offset, value_size, entry_size) -> i64
__wolf_rt_map_set(handle, entry) -> unit
__wolf_rt_map_get(handle, entry) -> i64
__wolf_rt_map_remove(handle, entry) -> i64
__wolf_rt_map_pairs(handle) -> i64
__wolf_rt_map_clear(handle) -> unit
__wolf_rt_region_new() -> pointer
__wolf_rt_region_set_cap(region: pointer, cap) -> unit
__wolf_rt_region_ambient_enter(region: pointer) -> pointer
__wolf_rt_region_ambient_leave(previous: pointer) -> unit
__wolf_rt_region_free(region: pointer) -> unit
__wolf_rt_region_bytes(region: pointer) -> i64
__wolf_rt_live_region_bytes() -> i64
```

`strbuf_str` uses `spec=0` for raw bytes. `strbuf_i64` appends an integer in
decimal: `spec=0` reads the word as signed, and `spec=16384` (bit 14, which the
runtime documents as "the value is unsigned") reads it as unsigned, so a `u64`
or `uint` at 2^64 − 1 renders `18446744073709551615`. An `i32` or `u8` passes
its canonical word with either spec by its own signedness. `strbuf_bool`
appends `true` or `false` with `spec=0`. `strbuf_char` takes a scalar widened
to i64 and appends its UTF-8 bytes; its public contract renders an invalid
scalar word as U+FFFD. `strbuf_f64` takes the double in `%xmm0` (SysV: the
handle in `%rdi`, the plan in `%rsi`) and renders it under the plan's float
rules (`docs/FIR.md`, edition 6). The runtime source was not consulted for this
entry: its prototype was settled black-box, by linking a C caller of each
candidate signature against the released runtime archive and comparing 814
value and plan pairs with the released compiler's own output (all 814 equal
under this prototype). `finish` writes 16 bytes containing the
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
empty option with zero padding. End-relative distances and inclusive upper
endpoints are validated and normalized before `str_get`; invalid normalization
uses that same 0/miss path without executing overflowing arithmetic. Byte length reads the str pair's second word;
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
The case and UTF-8 entries are not from runtime documentation: their meanings
were established by C probes linked against the pinned release archive and
observed only through their results. `str_case` writes a fresh str pair
through its 16-byte output: mode 0 lowercases and mode 1 uppercases the whole
string with full mappings (`ß` to `SS`, `İ` to `i` and U+0307). Its return
register carries nothing. Every case pair probed through Unicode 17.0 is
mapped, and the bounded interpreter's host methods are the same runtime's.
`str_from_utf8` reads a runtime list whose element size is one byte. For valid
UTF-8 it returns 0 and writes a fresh str pair that later writes to the list
do not change; for anything else, including any other element size, it
returns 1 and leaves the output alone. fenrir adapts its word list to it
through the public list entries only: a fresh one-byte list from `list_new(1)`,
then `list_read` of each word into scratch and `list_push` of that scratch,
which copies the word's low byte. The result becomes the option's tag.
`write_str` was probed the same way: it writes the bytes to standard error
when `stream` is 2 and to standard output for every other value, through the
same flushed streams `print_str` uses, so writes keep program order. `spec` 0
writes the bytes raw. `print_str` writes the bytes with no newline; `print`
appends one with a second call, `print_raw` does not, `eprint` is
`write_str(2, …)` and then a newline, and `eprint_raw` is the write alone.
The byte scans read each canonical word through `list_read` into scratch and
compare it with the byte; they call no scan entry of the runtime.
A list is constructed with its element's size in bytes, eight per FIR word. Push copies
one element during the call. Read and write copy one element and return 1 on
success, 0 out of bounds; fenrir checks that result and traps `bounds` at the
FIR `get` or `set` instruction, and turns it into the option's tag for
`read`. Pop returns 1 with the last element written, or 0 for an empty list.
A slice's bounds are checked before the call (two unsigned compares, so a
negative bound fails too), and the call returns a fresh list. Clear keeps
the storage, and a list's `reset` is that call. `list_reserve` grows a list's
storage to hold at least `capacity` elements.

A list is an opaque handle: nothing fenrir emits reads its header, assumes its
size or a field's offset, or reads its capacity. A list crosses the boundary
only through the entries above, and an element only by pointer, in fenrir's
own element layout. A runtime that reshapes the header therefore changes no
emitted instruction. One that also renames entries changes only the names in
this table. Every `__wolf_rt_` name in `src/` is listed here, and a frame row
in `tests/frame.py` holds that.

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

A region is the pointer `region_new` returns, one word (FIR's `i64`). A
`region r { }` block calls `region_new`, then `region_set_cap` when it has a
`cap:`, then `region_ambient_enter`, which makes the region ambient and returns
the region it replaces. On every way out of the block, `region_ambient_leave`
restores that previous region and `region_free` frees the block's region. The
ways out are falling through, `return`, `break`, `continue` and `?`, emitted
through the lowering's deferred chain. `in r { }` is the enter and the leave
alone. A region value is `region_new` and its `region_set_cap`. fenrir frees it
at the end of its scope when every use only lends it; the reference never frees
one. `region_bytes` and `live_region_bytes` read the runtime's ledger, in the
runtime's own units. Parity rows compare only its relations (MEMORY.md).

A charge past a region's cap traps `alloc-contract` inside the runtime's
allocator. A negative cap traps the same way at `region_set_cap`. Both report
`wolf-trap: alloc-contract` with no site line, the one trap the runtime
raises itself, so fenrir's interpreter prints no site for it either.
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

Assembly goes only to clef, with `--64 -o OBJECT SOURCE.s`. Blob bytes use
at most 16 comma-separated values per `.byte` directive: only serialization
changes, never blob bytes, labels, lengths or alignment. This avoids giving the
assembler one statement per byte while retaining its existing 2 GiB process cap.
Its own object
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

- **For FIR edition 7's operations `region` and `reserve`:** the region
  entries and `list_reserve`, with their signatures read from the pinned
  0.2.40 release's own calls to them. A list stays an opaque handle. Word
  layouts and the internal call plan are unchanged.

- **For FIR edition 4's operations 15 and 16:** `str_case` and
  `str_from_utf8`, from linked probes. Word layouts and the internal call plan
  are unchanged.
- **For FIR edition 4's operations 17 to 19:** `write_str`, from a linked
  probe, and scans through the public list entries. Word layouts and the
  internal call plan are unchanged.

- **For FIR edition 4's first primitives:** `str_get` supplies checked and
  recoverable zero-copy slices; length and byte reads use the str pair
  directly. All existing word layouts and the internal call plan remain
  unchanged.

- **For wide values:** a copy or zero fill of more than 16 words is one counted
  loop over `%rcx`, in place of a pair of moves per word, whose text grew as
  width times copies past what the assembler could hold under the 2 GiB build
  cap. Word layouts and the internal call plan are unchanged.

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
