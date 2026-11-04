# FIR 0

FIR is a typed, deterministic, block-argument intermediate representation. It
is independent of any other compiler IR. Its authority is the Wolf specification
at `5f1f1c94`, especially `[mem.model.order]`, `[abi.native]` and `[conf.trap]`.
The first backend implements signed 64-bit integers, booleans, strings, integer
lists and scalar aggregates. It is not yet the full Wolf language.

## Representation

Module tables are ordered and indexed by dense zero-based integers. Types 0–4
are `unit`, `int`, `bool`, `str`, and `List[int]`. Later types are structs whose
fields name only earlier non-unit types. Structs may contain only `int`, `bool`
or another scalar struct in this first edition. Fields occupy whole 8-byte
words; a bool word is exactly 0 or 1. A str is two words, pointer then byte length;
a list is one opaque runtime handle. A struct's width is the sum of its fields.

A module holds UTF-8 blobs, source sites, struct types and functions. A site
names a nonempty file blob and positive, one-based line and column. Function 0
is the entry, takes no parameters and returns int (the process status).
Functions have declared parameter and result types, and ordered blocks. Block
0's parameters exactly match the function's parameters.

**Values are block-local SSA.** Parameters are numbered first, then every
instruction receives the next value number, including unit instructions (which
cannot be used). An operand must name an earlier non-unit value in this same
block. Every cross-block value travels through explicit branch operands and
becomes a parameter at the destination. This is an intentionally stricter,
sealed-block dominance discipline, not a claim to accept arbitrary global SSA.
It makes dominance verification linear without a dominator fixed-point pass.
Loops carry values through their header's parameters. All branches perform
parallel copies: sources are staged before any destination parameter is written.

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
again is a byte fixed point.

```text
fir 0
blobs COUNT
blob HEX
... COUNT records
sites COUNT
site FILE_BLOB LINE COLUMN
... COUNT records
structs COUNT
struct FIELD_COUNT TYPE...
... COUNT records (type IDs start at 5)
functions COUNT
function RESULT_TYPE PARAM_COUNT TYPE... BLOCK_COUNT
block PARAM_COUNT TYPE... INSTRUCTION_COUNT
OP RESULT_TYPE SITE DATA_COUNT INTEGER... USE_COUNT VALUE...
... records according to counts
end
```

Every instruction carries a valid site, including constants and terminators.
`DATA` holds immediate integers, never SSA uses. Every `USE` is a block-local
value reference. The op table defines the exact data and use arities.

| Op | Result | Data | Uses | Effect / trap |
|---|---|---|---|---|
| `const` | int or bool | one literal | none | bool literal must be 0 or 1 |
| `string` | str | blob index | none | immutable static UTF-8 view |
| `add`, `sub`, `mul` | int | none | int, int | checked; overflow |
| `div`, `rem` | int | none | int, int | div-zero; overflow for MIN / -1, including remainder |
| `eq`, `lt` | bool | none | int, int | signed comparison |
| `not` | bool | none | bool | logical negation |
| `struct` | struct type | none | one value per field | whole-value construction |
| `field` | field type | field index | struct | whole-field copy |
| `call` | callee result | function index | declared arguments | ordered call; callee retains its sites |
| `concat` | str | none | str, str | runtime string buffer, ambient allocation |
| `list` | List[int] | none | none | fresh ambient runtime list |
| `push` | unit | none | List[int], int | append through runtime; no retained element pointer |
| `get` | int | none | List[int], int | bounds at this instruction's site |
| `len` | int | none | List[int] | runtime length |
| `print` | unit | none | int, bool or str | one line on stdout |
| `jump` | unit | target block | target's arguments | terminator |
| `branch` | unit | true block, false block, true argument count | bool, true arguments, false arguments | terminator |
| `return` | unit | none | result, or none for unit | terminator |
| `trap` | unit | trap kind number | none | terminator; source site required |

Trap numbers exposed here are 1 overflow, 2 div-zero and 3 bounds. Other kinds
are rejected until a backend implementation and runtime-interface evidence are
added. Arithmetic has no unchecked/profile-dependent variant. Runtime allocation
failure is runtime-owned; FIR does not invent an allocation-site report that the
runtime API does not expose. List push is an explicit mutable effect on its
handle; earlier lowering must enforce Wolf ownership and exclusivity. FIR does
not claim to implement the memory checker or deep copying of owning values.

## Verifier and complexity

`fir.verify` validates table references and sizes, instruction schemas, value
types, block-local dominance, branch signatures, call signatures, terminators
and sites. Parsing calls it before returning; formatting and assembly generation
call it again before producing output. There is no disable switch. A future
transform must call it before returning its module. The first edition has no
optimizer or transforms.

The parser and printer are O(input/output bytes). Verification is O(types +
fields + sites + blocks + instructions + operands), using dense indexed tables,
never the runtime Map. Layout and stack assignment are O(values + aggregate
words). Emission is O(emitted bytes + copied words). Aggregate word count is
included in the size metric; a nested type that doubles its width is not a
constant-size backend input. Scaling tests must report both work and bytes at
N, 10N and 100N. There is no whole-function search per use or instruction.
