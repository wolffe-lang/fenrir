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
A field written through an index (`xs[i].f = v`, `xs[i].f += v`) evaluates the
container and the index once, then the right-hand side, then reads the element
again, changes the field and sets the element back
(`[mem.model.place.elem]`); a tuple position (`t.0`) is a field path too.
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

`loop` jumps back to its body's header after every turn; only a `break`
reaches its exit, so a `loop` with none has no exit block and nothing after it
is lowered.

`assert(cond)` and `assert(cond, msg)` branch on the condition; the failing
block evaluates the message, if any, and traps `assert`, carrying the message.
The literal `assert(false)` is bottom: it evaluates the message and traps with
no branch and no block after it. A call to a `-> never` function is followed
by the same `assert` trap, so a callee that did return would stop the program
there, and no block follows it either ([type.fn.never]).

`min(a, b)` evaluates both operands once, left to right, then one `lt` of
`b` against `a` and one branch to a join that receives `b` when it is smaller
and `a` otherwise, so equal operands answer `a`. `print_raw`, `eprint` and
`eprint_raw` are text operation 17; `bytes_find` and `bytes_count` are text
operations 18 and 19 over the byte list's words (docs/FIR.md).

**Deferred statements.** `defer e` and `errdefer e` emit nothing where they
stand: the block records them in order ([mem.model.order]). When a block that
recorded any is left, the exit forms its value first (the block's own value,
a return value kept in the function's return slot, or nothing for `break` and
`continue`), stores its kind and whether it is on the error path in the
block's two slots, and jumps into the block's cleanup chain at the newest
deferred statement it reached. The chain has one block per deferred
statement, each running its expression (an `errdefer` only when the error slot
is set) and falling to the next older one, and then one dispatch block, which
sends each kind of exit on: the block's own end continues after the block, a
return enters the next enclosing chain or returns, and a `break` or `continue`
enters the next chain inside the loop or jumps to the loop's target. The error
path is a `?` that fails, a return whose value is an error, and a block whose
own value is an error; a trap runs no deferred statement. Each deferred
expression is lowered once, so a block costs its statements plus one jump per
exit, never a copy of the chain per exit. A block that records none lowers
exactly as before.

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
  continues. Each successful edge stores that alternative's bound values into
  common slots keyed by declaration id, so name order and extraction paths may
  differ without exposing uninitialized alternatives. The joined values enter
  the guard/body once; an unselected alternative reads no payload.

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
adds one, checked. An open side is 0 or the list's `len`, read after the
spelled endpoints; `^n` is `len` minus n, and an inclusive `^n` then adds one,
both in `wrapping[int]`, so every distance outside the list, the most negative
int included, reaches the slice's own `bounds` check rather than `overflow`.
A byte view's window (`s.bytes()[a..b]`) takes the same endpoint surface.

**Subscript origin.** Inside an `index(1)` scope (`[gram.expr.index.origin]`)
each spelled subscript position lowers to one checked `sub` of one, right
after the index or start endpoint is evaluated, so the most negative int traps
`overflow` before any bounds question: a list read, store and compound store,
a byte view read, and the plain start of a list, byte view or string slice. A
plain end is already the 0-based exclusive bound, so `..=` adds nothing to it;
`^n` endpoints, open sides, map keys and every method argument (`.get`) are
origin-free. The origin is lexical and computed once per unit from the syntax
(`resolve.origins`). `m[k]` is `lookup`, whose option is the `V ! {none}`
result. `xs[i] = v` runs the index, then the value, then `set`, so a bounds
trap comes after both; `xs[i] op= v` reads the old element between them.
`m[k] = v` is `insert`. The methods map to single instructions: `push`,
`pop`, `get` (`read`), `first` (`read` at 0), `last` (`read` at the length
less one, so an empty list answers the empty variant), `is_empty`, `len` or
`count`, `clear`, `pairs` and `remove`.

**Copies.** A value that owns a list or map, directly or inside a struct,
tuple, enum, result or caught row, is copied deep where it is stored: pushed,
written to an element or a map entry, placed in a list literal, assigned to a
local or field, or passed as an argument. A binding takes the value as it is. A list whose elements
own no container copies with one whole-list `slice`, one instruction whose
cost is the words it copies; a list of lists, maps or values holding them
copies element by element through its helper. The reference's move
rules make a moved-from place unusable (E1001); this compiler does not check
them yet, so it keeps the value semantics only for programs the reference
accepts.

A tagged copy selects the active variant with `case`, copies only that
payload's fields and rebuilds the tag, zeroing inactive padding. The same
helper handles a result's ok record, error payloads and a caught row. Ordinary
copies share strings; outward materialization re-makes every reached string.
A reverse-edge worklist computes container/storage effects once per typed
module in O(types + edges), including recursive handle graphs. Dense indexes
reserve each type's copy/materialization/rendering helper once. The existing
placement planner retains its narrower predicate, so this repair does not
widen or narrow its named refusals.

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
Rendering a map, including a nested map, remains a named F0001 refusal at the
outer interpolation value, directing the program to `pairs()`. The pinned native
reference refuses a direct Map at resolve and nested Maps at mem, at the same
outer expression site. Neither is output to count as `same`. The direct and
struct/list/tuple cases pin every tier's exact observed answer under
[wolf-lang#1110](https://github.com/wolffe-lang/wolf-lang/issues/1110): checked
wolf refuses the direct hole but renders `<value>` in the nested cases, while
lupin renders the Map in all four. This disagreement does not select a Map
rendering for fenrir or turn its named refusal into parity credit.

## Modes and value-result (F3b)

A function with `mut` parameters returns one FIR struct: its result first
(when it has one), then each `mut` parameter's final value, in parameter order
(`value_result_shape`, made for every function before any body is lowered, so
a call knows its callee's shape). Every way out of the body goes through
`emit_return`: the tail, an early `return`, `?` propagating an error and an
error `return` each load the `mut` parameters' slots and pack them with the
result. A call evaluates its arguments left to right; a `mut` argument's place
is evaluated once (`mut_place`: a local's field path, or a list element at a
key held in a slot, with a field path inside the element) and its current
value is passed (a list or map passes its handle). After the call each
returned value is written back to its place in parameter order (`write_back`;
an element is read again and set back with only the lent path changed), and
when the callee has a result the call's value is the struct's field 0. `take`
passes the value, `move x` is `x`'s value and `copy x` is the deep copy by
type the stores already use. No FIR edition changes: FIR already returns
structs.

An adapter (`type X = distinct T`) has its base's FIR type (`place` maps it to
the base), so a cast between an adapter and its base emits nothing, and an
adapter renders as its base value. A nested `fn` item is lowered as a function
of its own (the statement that declares it emits nothing). `[]` as a
`List`-typed field is an empty `list` of the field's type.
`#[consttime(public(…))]` naming every parameter changes nothing in FIR: every
fenrir function is already a call boundary.

## Regions (F3c)

A `region r(cap: e) { … }` block lowers to FIR edition 7's `region`
operations (docs/FIR.md): new, then cap with `e`'s value when the block has a
budget, then enter. The block's name is a slot holding the handle, so
`region_bytes(r)` inside the block reads it. The region and the ambient region
that enter replaced each get a slot of their own. The block's exit is its
first deferred entry, so it runs after the block's own `defer`s, on every way
out: the block's end, `return`, `?`, an error `return`, `break` and
`continue`. The exit runs leave with the replaced region, then free. It uses
the cleanup chain above, so each exit costs one jump, never a copy of the
leave and the free. `in r { … }` is the same block with enter and leave only:
it never frees `r`.

A region value, `region(cap: e)`, is new and an optional cap. The reference
never frees a region value (wolf-lang#1092). fenrir frees one bound by `let`
at the end of its binding's block when every use of the binding only lends it:
the value of an `in` block, or a plain argument such as `region_bytes(r)`.
This is a named difference closing at F6, which has the liveness to free it
at its last use instead (docs/MEMORY.md). No row can observe the difference.
A region value used any other way is never freed.

**A write into an outer value** (`[mem.region.outer-write]`,
src/lower/outer.lu). Inside a `region` or `in` block, an outer value is a
binding declared before the block opened, or a place reached through a `mut`
parameter, whose storage is the caller's. There, a store of `copy e` is the
materializing copy: every `str` it reaches is re-made by a one-part `format`,
every list and map gets a fresh buffer, and structs and tuples are rebuilt
around their parts. The copy is made with the outer value's region ambient,
entered just before the copy and left just after it, and the store copies no
more.

For a container store (a push, an index or `Map` store, the key included, or
a `List` or `Map` field or binding replaced), the region is the container's
own. For a local, that is the region ambient where it was declared: the saved
previous ambient of the outermost block that encloses the store but not the
declaration. For a `mut` parameter, it is the hidden region its caller passes
(docs/ABI.md). For any other store it is the ambient where the outer binding
was declared, and a parameter's is the function's entry ambient. A `copy`
anywhere else shares its strings, as before.

fenrir names a local's region statically, so before lowering it refuses by
name (F0001) two cases:
- a container store's copy into a local whose containers were not made where
  it is declared;
- such a local passed `mut` to a function that stores copies into it.

Made there means the initializer and every whole or field store into the local
at its own depth is a literal, a constructor, a struct literal of such parts,
or a `copy`. A container reached through an index is refused the same way. A
refused store is never placed in a region that may not hold its container.
`tests/memory/outer_write.py` has a row for each refused shape. `born-by-call`
is a named over-refusal: a local made by a call that happens to make its list
in the same region is refused, because fenrir cannot see that it does.

`region_bytes(r)` and `live_region_bytes()` are the bytes and live
operations. `reserve(n)` is FIR's `reserve`, and `reset()` is `clear`, which
keeps the storage. A region is never read through: the native runtime owns
the ledger (docs/ABI.md), and the interpreter keeps its own (docs/FIR.md).

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
time and in the size of the module it emits; deferred statements add one
chain block each and one jump per exit. A scaling row measures `--emit=fir`
at N, 10N and 100N, in the child's CPU time, the minimum of five interleaved
rounds.
