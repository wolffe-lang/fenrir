# Lowering: the typed tree to FIR

The `lower` module owns this pass. `lower.lower(syntax: front.Syntax, typed:
types.Typed) -> fir.Module ! {Bad(str)}` turns one checked translation unit
(`docs/TYPED.md`) into a verified FIR module (`docs/FIR.md`). It reads the
syntax arena and the typed tables and mutates neither. `Bad` is an internal
error: the typed tree broke an invariant the lowering relies on, or the module
it built does not verify. The driver reports it with status 70. The verifier
runs on every module the lowering returns, always.

## Module shape

- **Blob 0** is the file's path as the driver was given it; every site names
  it. Each string literal and each literal piece of an interpolation is its own
  blob, in emission order.
- **Types.** The typed tree's ids 0–3 and 5–9 are FIR's own ids; `never` lowers
  to no value; a list, map, tuple, result or caught row lowers as the last
  section below says. Each struct gets a FIR id after every struct its fields name,
  so FIR's earlier-type rule holds whatever the source order. A field of type
  `()` occupies no FIR field: it is evaluated where written and rendered as
  `()`.
- **Functions.** FIR function 0 is the entry: it calls `main` and returns its
  `int`, or 0 for `()` and `!()`, as the process status (TYPED item 7). When
  `main` is fallible and answers an error, the entry prints `error: TAG` and
  returns 1. Source function `k`, in the typed tree's source order, is FIR
  function `k + 1`; the generated helpers (below) follow the source functions.
  A parameter of type `()` is not passed; its argument is still evaluated.

## Values and places

Every parameter, `let` and `var` lives in a stack slot of its function, created
when its binder is lowered; a read is a `load`, a write a `store`, and a field
path rooted at a local (`v.a.b`, read or assigned) is one `load` or `store`
through that path. Parameters are stored to their slots in the entry block.
Literals use `node_value`'s bits; a negative literal is one constant (TYPED
item 10). A struct literal runs its initializers in source order and assembles
the value in field order; struct values are copied whole (TYPED item 9).

Values are block-local in FIR, so an expression whose later operand can leave
the current block (an `if`, `&&`, `||`, a loop, `assert`, a jump) first stores
each earlier operand it still needs to a fresh slot and loads it back where the
operation runs. Whether a node can leave its block is computed once per node.

## Evaluation order and control

Operands, call arguments, struct initializers and interpolation holes run left
to right, then the operation (TYPED items 1–5). `&&` and `||` branch on the
left operand and pass the deciding value to their join block; the right operand
runs only on the undecided edge. `x op= e` loads `x`, runs `e`, then stores.
Comparisons are `eq` and `lt` with their operands swapped or negated, which
moves no evaluation. `-x` is `0 - x` in the kind. `if` creates its join block
only when a branch reaches it, so an `if` whose branches all end in `never` has
no join and nothing after it is lowered. `while` re-evaluates its header in a
header block; `break` and `continue` jump to the innermost loop's exit and
header. Code after a `never` expression is unreachable and is not lowered.

`assert(cond)` and `assert(cond, msg)` branch on the condition; the failing
block evaluates the message, if any, and traps `assert`, carrying the message.

## Enums and match

Each enum gets a FIR enum shape (FIR edition 2) after the aggregates its
payloads hold. Each variant first gets its own payload struct, with fields of
type `()` erased as a struct's are. `E.V(a, b)` runs its arguments left to
right, assembles the payload struct, then tags it with `enum`; a bare `E.V`
tags an empty payload struct.

A `match` evaluates its scrutinee once and stores it to a fresh slot, then
tries the arms in source order. Each arm's tests branch to the next arm on
failure, and the last arm's failure reaches a `trap` that coverage proves
unreachable.

- A literal is `eq` against a constant of the scrutinee's type (a `str`
  literal compares by its decoded bytes).
- A range is two comparisons on the scrutinee, signed or unsigned by its type
  (`[gram.pat.range]`).
- A struct pattern tests its fields through field paths into the same slot.
- A constructor pattern is a `case` on the tag. Only the matched edge receives
  the payload record, which is stored to its own slot for the sub-patterns;
  no inactive payload is read.
- An or-pattern tries its alternatives in order, and the first that matches
  continues. No alternative binds a name.

When every test has passed, each binding is copied to a slot of its own, the
guard (if any) runs and branches to the body or the next arm, and the body's
value joins the others as an `if` branch's does. Only the selected guards and
body execute, and no pattern test runs user code. `match` can leave its block,
so earlier operands around it are held in slots as for `if`.

## Lists, maps, tuples and error rows

**Shapes.** A list or map is one FIR handle: `List[int]` is FIR type 4 and
every other list or map gets an edition-3 `list` or `map` shape after the
types it holds. A tuple is a FIR struct of its items. A result `T ! R` is a
FIR enum whose variant 0 carries the ok record and whose next variants carry
the payload records of `R`'s tags, in the row's order; a caught row is the
enum of its tags' records alone. Records are shared: one ok record per FIR ok
type (one field, or none for `()`) and one payload record per tag. So the
option a FIR read answers is the very enum of `V ! {none}`, and converting a
result between rows moves records without copying their fields.

**Lists and maps.** A list literal runs its elements left to right, then
makes the list and pushes each. `xs[i]` is `get`, which traps `bounds` at
the statement's site; `xs[a..b]` is `slice` after both endpoints, and `..=`
adds one, checked. `m[k]` is `lookup`, whose option is the `V ! {none}`
result. `xs[i] = v` runs the index, then the value, then `set`, so a bounds
trap comes after both; `xs[i] op= v` reads the old element between them.
`m[k] = v` is `insert`. The methods map to single instructions: `push`,
`pop`, `get` (`read`), `first` (`read` at 0), `last` (`read` at the length
less one, so an empty list answers the empty variant), `is_empty`, `len` or
`count`, `clear`, `pairs` and `remove`.

**Copies.** A value that owns a list or map, directly or inside a struct or
tuple, is copied deep where it is stored: pushed, written to an element or a
map entry, placed in a list literal, assigned to a local or field, or passed
as an argument. A binding takes the value as it is. The reference's move
rules make a moved-from place unusable (E1001); this compiler does not check
them yet, so it keeps the value semantics only for programs the reference
accepts.

**`for`.** `for p in a..b` evaluates both endpoints once, left to right,
then counts up by checked steps of one; `a..=b` checks `b + 1` where the loop
starts. `for p in xs` reads each element by index while the index is below
the list's length, read again on every pass. A tuple pattern binds each item
through the tuple's fields.

Direct `for` consumption of `str.split`, `words` and `lines` is a zero-copy
field view, not a materialized list. The receiver and separator run once,
left to right. A private fixed-signature FIR helper returns five words:
`(lo, hi, next, present, last)`. Bounds name a valid UTF-8 view of the cached
receiver. Split preserves empty fields and treats an empty separator as the
whole string; lines uses LF and absorbs one preceding CR without an extra
trailing field; words walks valid scalars using the frozen 25-scalar
White_Space set. The helper stores nothing per scanned scalar and allocates
no runtime container. The cursor and final-field flag are saved before the
body: `continue` advances, and `break` does not scan another field. Helpers use
only verified FIR instructions, including the bounded scalar-space primitive,
and the published internal call ABI. Word scanning retains nothing per scalar;
the native predicate is one shared nonallocating leaf, not an expanded decoder
per cursor helper. No runtime C ABI is introduced. Bound or otherwise unclassified
split/words/lines results still materialize their `List[str]` values.

**Rows.** A raise evaluates its payload left to right, builds the tag's
record and tags it as its variant of the expected result. An ok value where a
result is expected is wrapped as variant 0. A result of a narrower row
converts by one `case` per variant, each moving its record to the matching
variant of the wider type. `e?` cases on the ok variant: the ok record's
value continues, and every other variant converts to the function's result
and returns. `e else f` evaluates `f` only on the error edge; a handler binds
its pattern over the caught row first. A `match` over a result or row tests
a tag arm by its variant and a value arm on the ok variant, then the value;
`_` and a row binder take everything. A fallible value in a unit context is
evaluated and dropped.

**Helpers.** A deep copy of a list or map, and the rendering of a list,
enum, result or row, need a loop or a branch. Each is a helper function,
generated once per type after the source functions, so a rendering inside
an expression stays one call. A list renders as `[a, b]`, a tuple as
`(a, b)`, a tag as its name with `(p1, p2)` when it carries a payload, and a
result as its ok value or its tag. A nominal enum renders as `Enum.Variant`,
with `(p1, p2)` for a payload. Its helper selects the active payload with
`case` before reading any field; erased unit fields still render as `()`.
These rules compose recursively through structs, lists, tuples and rows.
Rendering a map, including a nested map, remains a named F0001 refusal while
its reference contract is measured; no map spelling is guessed.

## Sites

Every instruction's site is the start of the innermost `Statement` or `Tail`
containing the node it lowers (`node_site`, TYPED's site rule), so a trap
reports where the reference reports it. One FIR site is made per such node.
The entry block's parameter stores and function 0 use the function's own
declaration start.

## Interpolation

A string with no holes is one `string` constant. Otherwise every hole is
evaluated first, in order, and then rendered (`[type.interp]`): an integer,
`bool` or `str` value is a `format` part; `()` is the text `()`; a struct is
its name, ` {`, each field as ` name: value` with `,` between, then ` }`
(`Name { }` with no fields), each field rendered by its own rule through
`field` copies. Adjacent literal text is merged into one `string` part.

## Complexity

Each AST node is lowered once and its split flag computed once; each table is a
dense array indexed by node or declaration id, allocated once per module, never
the runtime `Map` and never a scan. A struct hole costs its rendered fields and
a struct literal its fields. A row conversion costs one `case` per variant of
the narrower type, and a helper is generated once per type it serves. The pass is O(nodes + rendered struct fields) in
time and in the size of the module it emits. A scaling row measures `--emit=fir`
at N, 10N and 100N, in the child's CPU time, the minimum of five interleaved
rounds.
