# FIR 1

FIR is a typed, deterministic, block-argument intermediate representation. It
is independent of any other compiler IR. Its authority is the Wolf specification
at `5f1f1c94`, especially `[mem.model.order]`, `[abi.native]`, `[conf.trap]`,
`[type.numlit.cast]`, `[type.wrap.div]` and `[type.interp]`. The backend
implements the integer kinds, booleans, strings, integer lists, aggregates of
those, typed stack slots and string rendering. It is not yet the full Wolf
language. The change record at the end lists what each edition added.

## Representation

Module tables are ordered and indexed by dense zero-based integers. The fixed
types are:

| id | type | words | canonical word |
|---:|---|---:|---|
| 0 | `unit` | 0 | none; a unit value cannot be used |
| 1 | `int` | 1 | signed 64-bit |
| 2 | `bool` | 1 | exactly 0 or 1 |
| 3 | `str` | 2 | pointer, then byte length |
| 4 | `List[int]` | 1 | an opaque runtime handle |
| 5 | `i32` | 1 | signed 32-bit, sign-extended |
| 6 | `i64` | 1 | signed 64-bit, distinct from `int` |
| 7 | `u8` | 1 | unsigned 8-bit, zero-extended |
| 8 | `u64` | 1 | unsigned 64-bit |
| 9 | `uint` | 1 | unsigned 64-bit, distinct from `u64` |

Ids 1 and 5–9 are the **integer kinds**; they are the same ids the typed tree
gives them (`docs/TYPED.md`). Their width, signedness and range are defined once,
in `src/sem/`, keyed by the kind's name (`fir.kind` maps an id to it); the
verifier's constant check, the emitter's checks and the typed tree's checker
read that table and no other. Types from 10 on are structs, one per `struct`
record in order. A struct's fields name earlier types: an integer kind, `bool`,
`str` or an earlier struct, never `unit` or the list handle. A struct may have
no fields; its width is then zero words, and its values may still be used.
Fields occupy whole words in declaration order without padding; a struct's
width is the sum of its fields'.

A module holds UTF-8 blobs, source sites, struct types and functions. A site
names a nonempty file blob and positive, one-based line and column. Function 0
is the entry, takes no parameters and returns int (the process status).
Functions have declared parameter and result types, typed stack slots and
ordered blocks. Block 0's parameters exactly match the function's parameters.

**Values are block-local SSA.** Parameters are numbered first, then every
instruction receives the next value number, including unit instructions (which
cannot be used). An operand must name an earlier non-unit value in this same
block. Every cross-block value travels through explicit branch operands and
becomes a parameter at the destination. This is an intentionally stricter,
sealed-block dominance discipline, not a claim to accept arbitrary global SSA.
It makes dominance verification linear without a dominator fixed-point pass.
Loops carry values through their header's parameters. All branches perform
parallel copies: sources are staged before any destination parameter is written.

**Stack slots are function-wide places.** A slot has a non-unit type and is
named by its index. `load` copies a slot, or a field path inside it, into a new
value; `store` copies a value into a slot or a field path. Slots carry locals
and `var` places across blocks, so a lowering need not thread every local
through block parameters. Loads and stores run in instruction order. The
verifier checks every slot index and path statically; reading a slot before
any store is the producer's error, not a verifier rule.

Every block ends in exactly one terminator. No instruction follows it. There
are no implicit fallthroughs. Calls may have arbitrary arity; they name a
function index, with arguments and result checked against its declaration.

## Text grammar

ASCII whitespace separates tokens. Decimal integers are signed 64-bit values;
counts and references must be nonnegative and fit the corresponding table.
Blobs use lowercase hexadecimal UTF-8 bytes (`-` means empty). There are no
comments, quoted strings, implicit names, escapes or discarded trailing tokens.
The printer emits one record per line and a final newline. Noncanonical decimal
spellings are accepted but normalize on printing. Printing, parsing and printing
again is a byte fixed point. Only edition 1 is read: a `fir 0` module is refused
by name rather than having its struct ids silently reinterpreted.

```text
fir 1
blobs COUNT
blob HEX
... COUNT records
sites COUNT
site FILE_BLOB LINE COLUMN
... COUNT records
structs COUNT
struct FIELD_COUNT TYPE...
... COUNT records (type IDs start at 10)
functions COUNT
function RESULT_TYPE PARAM_COUNT TYPE... SLOT_COUNT TYPE... BLOCK_COUNT
block PARAM_COUNT TYPE... INSTRUCTION_COUNT
OP RESULT_TYPE SITE DATA_COUNT INTEGER... USE_COUNT VALUE...
... records according to counts
end
```

Every instruction carries a valid site, including constants and terminators.
`DATA` holds immediate integers, never SSA uses. Every `USE` is a block-local
value reference. The op table defines the exact data and use arities. `K`
below is one integer kind, the same kind for every operand and the result.

| Op | Result | Data | Uses | Effect / trap |
|---|---|---|---|---|
| `const` | an integer kind or bool | one literal | none | the literal's 64-bit pattern must be a canonical value of its kind (`u64` 2^64 − 1 is −1); a bool is 0 or 1 |
| `string` | str | blob index | none | immutable static UTF-8 view |
| `add`, `sub`, `mul` | K | none | K, K | checked in K: a result outside K traps overflow |
| `div`, `rem` | K | none | K, K | zero divisor traps div-zero; signed MIN / −1 and MIN % −1 trap overflow; unsigned kinds divide unsigned, truncating |
| `eq` | bool | none | two of one type: K, bool or str | value equality; str bytewise |
| `lt` | bool | none | two of one type: K or str | signed or unsigned by K; str byte order |
| `not` | bool or K | none | the same type | logical negation on bool; bitwise complement within K's width, never a trap |
| `struct` | struct type | none | one value per field | whole-value construction |
| `field` | field type | field index | struct | whole-field copy |
| `load` | the place's type | slot, field index... | none | whole-value copy out of the slot or field path |
| `store` | unit | slot, field index... | the place's type | whole-value copy into the slot or field path |
| `call` | callee result | function index | declared arguments | ordered call; callee retains its sites |
| `concat` | str | none | str, str | runtime string buffer, ambient allocation |
| `format` | str | none | one or more of K, bool, str | one runtime string buffer renders each part in order: an integer in decimal, with `-` only on a negative value (unsigned kinds never negative); `true`/`false`; a str as its bytes |
| `list` | List[int] | none | none | fresh ambient runtime list |
| `push` | unit | none | List[int], int | append through runtime; no retained element pointer |
| `get` | int | none | List[int], int | bounds at this instruction's site |
| `len` | int | none | List[int] | runtime length |
| `print` | unit | none | int, bool or str | one line on stdout |
| `jump` | unit | target block | target's arguments | terminator |
| `branch` | unit | true block, false block, true argument count | bool, true arguments, false arguments | terminator |
| `return` | unit | none | result, or none for unit | terminator |
| `trap` | unit | trap kind number | none; for assert, optionally its str message | terminator; source site required |

Negation has no instruction: `-x` in a kind is `sub` from a `const 0` of that
kind, which traps overflow exactly where `[type.wrap.div]` and the typed tree
say it does (a signed MIN, any nonzero unsigned value). A struct hole, `()` and
literal text are rendered by the producer as `format` parts and `string`
constants, so the backend renders only scalars.

Trap numbers exposed here are 1 overflow, 2 div-zero, 3 bounds and 4 assert,
the numbers the runtime's trap entry reads (`docs/ABI.md`). Other kinds are rejected until a backend
implementation and runtime-interface evidence are added. An `assert` trap may
carry its message, already evaluated on the failing path as `[conf.trap.assert]`
requires; only `assert` may carry one. The pinned runtime's ordinary build prints
no assertion message, and neither does this backend, so the trap report equals
the reference's; the message stays in the FIR for a later rendering.
Arithmetic has no unchecked/profile-dependent variant. Runtime allocation
failure is runtime-owned; FIR does not invent an allocation-site report that the
runtime API does not expose. List push is an explicit mutable effect on its
handle; earlier lowering must enforce Wolf ownership and exclusivity. FIR does
not claim to implement the memory checker or deep copying of owning values.

## Verifier and complexity

`fir.verify` validates table references and sizes, instruction schemas, value
types, constant ranges, slot indices and field paths, block-local dominance,
branch signatures, call signatures, terminators and sites. Parsing calls it
before returning; formatting and assembly generation call it again before
producing output. There is no disable switch. Every transform, the lowering
included, must call it before returning its module.

The parser and printer are O(input/output bytes). Verification is O(types +
fields + sites + slots + blocks + instructions + operands + path lengths),
using dense indexed tables, never the runtime Map. Layout and stack assignment
are O(values + slots + aggregate words). Emission is O(emitted bytes + copied
words). Aggregate word count is included in the size metric; a nested type that
doubles its width is not a constant-size backend input. Scaling tests must
report both work and bytes at N, 10N and 100N. There is no whole-function
search per use or instruction.

## Module interfaces

```text
fir.parse(source: str) -> Module ! {Bad(str)}
fir.verify(module: Module) -> () ! {Bad(str)}
fir.format(module: Module) -> str ! {Bad(str)}
x86.emit(module: fir.Module) -> str ! {Bad(str)}
x86.assemble(path: str, output: str) -> int
x86.canonical(path: str, output: str) -> int
x86.link(args: List[str]) -> int
```

`parse` verifies before returning. `format` and `emit` verify their inputs again.
The driver treats parse failures as input refusals (2), and subsequent invariant
failures as internal errors (70). It writes no assembly for an invalid module.
`fenrir fir INPUT -o OUTPUT` is the canonical text command; `asm` emits assembly.
The parser limits a struct to 1,048,576 words, rejecting larger structs by name
rather than overflowing layout arithmetic. Cached field offsets and widths are
verified, not trusted, and rebuilt by the text parser.

## Bounded interpreter

The interpreter executes FIR 1 without changing its text or instruction
semantics. Interpreting FIR does not broaden source-language acceptance.

```text
interp.run(module: fir.Module, max_steps: int, max_bytes: int) -> Outcome ! Failure
fenrir interpret INPUT.fir --steps N --bytes N --report OUTCOME
```

`Outcome` exposes `kind`, `status` and `code`: `kind` is `exit`, `trap` or
`refused`; `status` is the process status, and `code` is empty except for a
budget refusal. The in-memory entry verifies the module, writes only executed
program output, and returns its outcome without printing tool diagnostics.
The CLI parses FIR text and invokes the same entry. Invalid input remains a
named FIR rejection (2), not a program trap, and preserves an existing outcome
file. `Failure` names `Bad(str)` for invalid input and `Internal(str)` for an
interpreter invariant failure; the latter returns 70 and publishes no outcome.
Budgets are explicit nonnegative integers, not host-dependent defaults. The
text reader stops at the byte ceiling even if the file grows after its size
check. `Outcome` also exposes the consumed `steps` and logical `bytes`, and a
trap's kind number and site index.

Plans are built once per run, in O(module size plus operands). Execution costs
its instructions plus the words copied and bytes rendered or compared. Frames
reuse a geometrically grown high-water stack; literal strings are views, not
copies. The monotone ledger charges layout tables, 16 logical bytes per new
stack-capacity word, list capacity in 8-byte elements, container metadata and
string-building storage. These are accounting bytes, not an RSS claim; the
fixed input representation and allocator overhead remain separate. Linux rows
measure the direct child's RSS at N, 10N and 100N nonallocating loop steps.

One step is charged before executing each FIR instruction, including a
terminator. Exhaustion returns 4 with `FIR_STEP_BUDGET`, without executing the
next instruction. The memory ledger counts bytes of retained execution
storage, including its tables, frames, values, lists and constructed strings,
before growth occurs. Its charge is monotone; storage reuse creates no new
allocation. Exhaustion returns 4 with `FIR_MEMORY_BUDGET`, never `alloc-contract`
or a native allocation failure. Input/module storage is fixed in input size;
execution must retain nothing per step outside the charged storage. Calls use
an explicit bounded frame stack rather than relying on host stack overflow.

A program's output before refusal or a trap is preserved. Traps use the native
backend's kind, source site, report bytes and status 134. There is no folding,
reordering or alternate arithmetic profile. Resource refusals print their named
tag on stderr, never a `wolf-trap:` line.

The outcome file is a separate, closed one-line protocol: `exit N`, `trap KIND`,
or `refused CODE`, followed by a newline. A normal program returning 4 writes
`exit 4`; budget exhaustion writes `refused FIR_STEP_BUDGET` or
`refused FIR_MEMORY_BUDGET`. Harnesses read this record rather than guessing
from a colliding status or from program output.

`tests/backend/interpreter.py --mode smoke` uses only finite, small executable
FIR fixtures, verifier rejection rows and boundary budgets. Its `linux` mode
adds endless control flow, recursion and allocating loops under independent
hard process limits. `tests/backend/interpreter_api.py` compiles a consumer
that constructs FIR in memory and distinguishes exit 4 from both refusals.
The native differential and the core corpus comparison remain required proof;
fixture expectations alone are not equivalence evidence.

## Enum extension contract (edition 2)

This interface precedes its implementation and lowering consumers. Existing
edition-1 behavior remains the implemented baseline until its new rows pass.
The fixed ids and all existing instruction meanings remain unchanged.

`Shape` gains `kind: str`, exactly `struct` or `enum`. All aggregates continue
in the single ordered `Module.shapes` table at ids 10 and above. For a struct,
`fields`, `offsets` and `words` retain their current meanings, and a field may
also name an earlier enum. For an enum, `fields` is its nonempty source-order
list of **earlier struct types**, one payload-record type per variant.
`offsets` has one entry per variant, each exactly 1. `words` is one tag word
plus the maximum payload-record width, checked against the existing 1,048,576
word ceiling. A nullary variant uses a zero-field, zero-word payload struct.
The producer erases unit payload fields but preserves their source positions
in its typed-to-FIR mapping. There is no recursively sized aggregate layout.

An enum value contains its zero-based tag followed by the active payload's
words. Its unused tail words are canonical zero padding, not typed values.
Whole enum copies may copy those raw words; they never interpret padding as a
string, list, nested enum or other inactive payload. Enum fields cannot be
read with `field` or by a slot path: the only payload elimination is the
checked `case` terminator below. Whole enum slot loads/stores remain legal.

| Op | Result | Data | Uses | Effect |
|---|---|---|---|---|
| `enum` | enum type | variant index | one value of that variant's payload-record type | write tag and active payload; zero unused padding |
| `case` | unit | variant index, yes block, no block, explicit yes-argument count | enum value, explicit yes arguments, no arguments | compare tag; only on equality extract the matching payload and enter yes, otherwise enter no |

`case` is a terminator. The yes destination's **first parameter** must have
that variant's payload-record type, even when its width is zero. Its remaining
parameters match the explicit yes arguments. The no destination has only its
explicit arguments. Both targets, the variant, every use and every parameter
type are verified. Copies are parallel as for `branch`. Crucially, the tag
comparison precedes every active-payload load or copy: the interpreter and
native backend may not prepare the yes payload unconditionally before the
branch. There is no unchecked payload-projection instruction.

A `case` costs one interpreter step, just like `branch`; its copy/layout space
uses the same existing memory ledger. It introduces no new program trap and
changes no source evaluation order. The lowering evaluates the scrutinee once,
tries patterns and guards in arm order, and uses nested `case` operations for
nested enum patterns and enum rendering. Only the selected guard/body executes.

Edition 2 changes the aggregate-table grammar to:

```text
fir 2
... blobs and sites as in edition 1 ...
shapes COUNT
struct FIELD_COUNT TYPE...
enum VARIANT_COUNT PAYLOAD_STRUCT_TYPE...
... COUNT mixed records, ids starting at 10 ...
... functions and instructions as in edition 1 ...
```

The reader accepts editions 1 and 2, still never edition 0. Edition 1's
`structs` records create `kind = "struct"`; enums and `case` cannot be smuggled
into that edition. The canonical printer uses edition 1 for enum-free modules
and edition 2 when an enum is present, preserving existing fixture bytes while
making every new capability explicit. Printing reaches a byte fixed point.
The in-memory verifier checks kinds and cached widths/offsets independently of
text parsing. Unknown kinds, invalid payload types/tags and unguarded field
paths through enums are named FIR rejections, not compiler crashes.

## Interface change record

- **Edition 0** introduced the representation: `unit`, `int`, `bool`, `str`
  and `List[int]`, scalar structs of `int`, `bool` and earlier structs, the
  three trap kinds overflow, div-zero and bounds, and the text form `fir 0`.
- **Edition 1** (the F1 core's lowering needs these):
  - the sized integer kinds `i32`, `i64`, `u8`, `u64` and `uint` at ids 5–9, so
    struct ids now start at 10; `const`, the arithmetic, `eq`, `lt` and `not`
    take every integer kind, with width-aware checks from `src/sem/`;
  - `not` on an integer kind is the bitwise complement;
  - `eq` on bool and str, and `lt` on str;
  - struct fields of `str` and every integer kind, and structs with no fields;
  - typed stack slots on each function, read and written by `load` and `store`
    through field paths; the function record gains `SLOT_COUNT TYPE...`;
  - `format`, rendering scalar parts into one fresh str;
  - the `assert` trap, kind 4, with an optional str message;
  - the text form's header is `fir 1`, and `fir 0` is refused.
