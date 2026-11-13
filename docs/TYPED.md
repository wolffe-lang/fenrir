# Typed tree interface

The `types` module owns this interface. `types.check(syntax: front.Syntax) -> Typed`
resolves every name and types every expression of one parsed translation unit.
It reads the syntax arena and never mutates it. Callers must inspect
`Typed.code` before consuming the tables: an empty code means success; a
nonempty code is the first diagnostic, and the tables are then partial and must
not be consumed. `syntax.code` must be empty on entry.

**Every driver command enters through `types.load(path: str) -> Source`.** It
reads the file, parses it, refuses a program of several files (F0001, below),
then checks it, so `build`, `run` and every `--emit` view share the typed view's
refusals and statuses. `Source` holds `syntax: front.Syntax`, `typed: Typed` and
`status: int`: 0 when `typed` is a successful check; otherwise the diagnostic
is already on stderr, `typed.code` names it, the tables are empty or partial
and must not be consumed, and `status` is the command's exit (2, 4 or 70, as
below). A caller that already holds a parsed `Syntax` may call `check` itself,
but then it owns the module-shape refusal.

The typed tree is a set of **side tables keyed by the AST's node ids**
(`docs/AST.md`). It adds no nodes and reorders nothing. Every source span comes
from the arena: a typed fact about node `n` has the span `syntax.nodes[n].span`,
and a declaration's span is its declaring node's span. The consumer keeps the
`Syntax` and the `Typed` side by side.

## The F1 core

`check` succeeds only on programs inside the F1 core, and the core is **one
file**. By `[conf.directive.standalone]` a directory is a module and every `.lu`
file in it joins unless it is a standalone entry, so `fenrir --emit=typed FILE`
refuses FILE with F0001 ("a module of several files") when a sibling `.lu` file
is a member; a named file whose siblings are all standalone entries is a
one-file program. Inside that one file:

- **items:** functions with typed, mode-free parameters and an optional result;
  structs with typed fields; `pub` is accepted and has no effect in one file;
- **types:** `()`, `bool`, `str`, `int`, the sized integers `i32`, `i64`, `u8`,
  `u64` and `uint`, a struct, and `!T` (with `T` from this list) only as a
  function's declared result;
- **statements:** `let` and `var` with one name (or `_`) per binder, an optional
  annotation and an initializer, in comma groups; `=` and `+=`, `-=`, `*=`, `/=`,
  `%=` to a `var` local or a field path rooted at one; expression statements;
- **expressions:** names; integer literals (decimal, `0x`, `0o`, `0b`, `_`
  separators), `true`, `false`; plain, multiline and raw strings with
  interpolation holes that carry no format spec; parentheses; prefix `-` and
  `!`; binary `+ - * / %`, `== != < <= > >=`, `&&`, `||`; calls of a function
  or of a core prelude entry by name; struct literals, including field
  shorthand; field reads; `if`/`else` (block or `then` form) as statement and
  expression; blocks; `while`; `break` and `continue` without a value;
  `return` with or without a value.

Three extensions widen this core: enums and `match`, then lists,
`Map`, tuples and error rows, then primitive strings, chars and bytes (below).
Everything else (generics, traits, impls and methods other than the supported
collection/string methods, closures and fn values, `loop`, casts,
an empty list literal, regions, modules and `use`, attributes, constants,
module-level bindings, nested items, float literals,
bitwise and shift operators, parameter and argument modes other than a `mut`
receiver, other prelude entries, recursive structs) is refused by name with
**F0001** (`not yet in fenrir: CONSTRUCT`) at the construct's span. That
refusal is fenrir's scope, never a verdict about the program.

## Representation

Primitive interpolation specs are parsed and checked once during typing.
An interpolation node with a `Format` child carries the packed plan in
`node_value`; an absent child means bare rendering. The plan's bit contract is
`docs/FIR.md` operation 4. Malformed shapes, conflicting zero/alignment flags and
width or precision above 65535 are E0412; fields outside the primitive type's
surface are E0413, at the format token. `char` uses the str surface and `byte`
the integer surface. All holes still evaluate before rendering starts.

String subscripts and `get` admit open, inclusive and end-relative ranges.
Endpoints are int byte offsets, evaluated once from left to right after the
receiver. Missing endpoints mean the corresponding edge; `^n` means length
minus n. Normalization belongs to the checked/recoverable domain question, not
to checked integer arithmetic, so even extreme invalid offsets answer `none`
from `get`. List slices still require two plain endpoints; other uses of open
or end-relative ranges remain named refusals.

```text
pub struct Typed {
    pub code: str             // "" on success, else the first diagnostic's code
    pub message: str
    pub error: front.Span     // the diagnostic's span
    pub types: List[Type]     // the type table; ids are indices
    pub type_params: List[int]// fn types' parameter type ids, contiguous
    pub decls: List[resolve.Decl] // the declaration table; ids are indices
    pub texts: List[str]      // decoded string segments; ids are indices
    pub node_type: List[int]  // per AST node: type id, or -1
    pub node_decl: List[int]  // per AST node: declaration id, or -1
    pub node_site: List[int]  // per AST node: its trap-site node, or -1
    pub node_value: List[int] // per AST node: literal bits or text id, else 0
    pub functions: List[int]  // function declaration ids, in source order
    pub structs: List[int]    // struct declaration ids, in source order
    pub main: int             // the declaration id of `main`, or -1
}

pub struct Type {
    pub kind: str   // unit int bool str never i32 i64 u8 u64 uint struct fn result
    pub decl: int   // struct: its declaration id; otherwise -1
    pub inner: int  // fn: result type; result: ok type; otherwise -1
    pub first: int  // fn: index of its first parameter in type_params; otherwise -1
    pub count: int  // fn: parameter count; otherwise 0
}

pub struct Decl {  // in the `resolve` module, which types re-uses
    pub kind: str   // prelude-fn prelude-type function struct field param let var
    pub name: str
    pub node: int   // the declaring node (below); -1 for prelude entries
    pub ty: int     // the declared or inferred type id (below)
    pub owner: int  // param, let, var: the function; field: the struct; otherwise -1
    pub index: int  // param: position; field: position; otherwise -1
    pub count: int  // function: parameter count; struct: field count; otherwise 0
}
```

All five `node_*` columns have exactly `syntax.nodes.len` entries.

### Types

Types are **interned**: two type ids are equal exactly when the types are
equal, so a consumer compares ids, never structure. The fixed ids are

| id | kind | meaning |
|---:|---|---|
| 0 | `unit` | `()` |
| 1 | `int` | signed 64-bit |
| 2 | `bool` | `true`/`false` |
| 3 | `str` | immutable UTF-8 bytes |
| 4 | `never` | no value: `return`, `break`, `continue` and what they end |
| 5 | `i32` | signed 32-bit |
| 6 | `i64` | signed 64-bit, distinct from `int` |
| 7 | `u8` | unsigned 8-bit |
| 8 | `u64` | unsigned 64-bit |
| 9 | `uint` | unsigned 64-bit, distinct from `u64` |
| 10 | `char` | a Unicode scalar, distinct from integers |
| 11 | `byte` | an octet, distinct from integers |

Ids 0–3 coincide with FIR's first types. Struct types follow, one per struct
declaration in source order. Function and result types follow, interned in the
order the checker first builds them: the core prelude's signatures, then each
function's signature in source order. A `fn` type's parameters are
`type_params[first .. first + count]`. A `result` type is `!T` with ok type
`inner`. The width, signedness and range of every integer kind come from
`src/sem/`, never from a second table.

`never` is the type of `return`, `break` and `continue`, of a block whose last
statement or tail is one of them, and of an `if` whose branches are all
`never`. It joins any other type: `if c { return 1 } else { 2 }` is `int`.

### Declarations

Declaration ids are deterministic. The **core prelude** comes first, in this
fixed order, which is the pinned prelude's order:

| id | kind | name | type |
|---:|---|---|---|
| 0 | `prelude-fn` | `print` | `fn(str) -> ()`: writes the bytes and a newline to stdout |
| 1 | `prelude-fn` | `assert` | `-1`: an intrinsic with two forms, below |
| 2 | `prelude-type` | `bool` | 2 |
| 3 | `prelude-type` | `str` | 3 |
| 4 | `prelude-type` | `int` | 1 |
| 5 | `prelude-type` | `uint` | 9 |
| 6 | `prelude-type` | `i32` | 5 |
| 7 | `prelude-type` | `i64` | 6 |
| 8 | `prelude-type` | `u8` | 7 |
| 9 | `prelude-type` | `u64` | 8 |
| 10 | `prelude-type` | `char` | 10 |
| 11 | `prelude-type` | `byte` | 11 |

`assert(cond: bool)` and `assert(cond: bool, msg: str)` both have type `()`.
The condition is evaluated first; when it holds, nothing else happens and `msg`
is not evaluated. When it fails, the program traps `assert` at the call's site.
The message, when present, is evaluated only on that failing path.

Source declarations follow, **numbered in source order of their declaring
node**, over the whole file at once: a function, then its parameters, then the
locals of its body in order; a struct, then its fields. So a function's
parameters are the `count` declarations after it, and a struct's fields are the
`count` declarations after it, in declaration order.

| kind | declaring node | type |
|---|---|---|
| `function` | the `Function` node | its `fn` type; the result is `()` when omitted |
| `struct` | the `Struct` node | its struct type |
| `field` | the `Field` node | the field's type |
| `param` | the `Parameter` node | the parameter's type |
| `let`, `var` | the `Binder` node | the binding's inferred or annotated type |

A `_` binder declares nothing.

## Annotations

### `node_decl`

| node | declaration |
|---|---|
| `Function`, `Struct`, `Field`, `Parameter`, `Binder` | the declaration it introduces |
| the `Name` child of each of those (for a `Binder`, the pattern's `Name`) | the same declaration |
| `Name` in value position | the `param`, `let` or `var` it reads |
| `Name` receiver of a `Call` | the callee: a `function` or `prelude-fn`; this name has no type (-1) |
| `Call` | the callee, as above |
| `Name` in a type's `Path` | the `struct` or `prelude-type` it names |
| `NamedType` | the same |
| `StructLiteral` and its head `Name` | the `struct` |
| `FieldInitializer` | the `field` it initializes |
| `Name` of a longhand `FieldInitializer` (`x: e`) | the `field` |
| `Name` of a shorthand `FieldInitializer` (`x`) | the local it reads; the initializer node names the field |
| `Member` and its `MemberName` | the `field` read or written |
| `Assignment` | the root local of its place (`v` in `v.a.b = e`) |
| `Jump` `break`/`continue` | -1; it binds to the innermost enclosing `while` |

Everything else is -1. Name uses are resolved before any type is used, so a
consumer never resolves a name by its spelling.

### `node_type`

Every expression node inside a body has a type id ≥ 0 after a successful check
(a call's callee name is not an expression), and **no
inference variable survives**: every integer literal has a concrete integer
type, defaulted to `i32` where nothing decided it.

| node | type |
|---|---|
| `Name`, `Literal`, `String`, `Group`, `Prefix`, `Binary`, `Call`, `StructLiteral`, `Member`, `If`, `Block`, `Loop`, `Jump` | the expression's type |
| `Text`, `Interpolation` | `str` |
| `Binder` | the binding's type; its initializer has the same type |
| `Assignment` | `()`; its place and right-hand side carry their own types |
| `Tail` | its expression's type |
| `Statement` | `()` |
| `Parameter`, `Field` | the declared type |
| `NamedType`, `TupleType`, `PrefixType` in a written type | the type written |
| `ReturnType` | the function's result type |

A `Block`'s type is its tail's type, `()` when it has no tail, and `never` when
its last statement is a `never` expression statement. A block in a **unit
context** (`[type.unit.context]`: a function body with result `()`, a `while`
body, the then-block of an `if` with no `else`) has type `()`; the checker
requires its tail to be `()` or `never`, as the reference does.

### `node_value`

| node | value |
|---|---|
| integer `Literal` | its value's 64-bit two's-complement bit pattern in its type (`18446744073709551615` at `u64` is -1) |
| negative literal | a `Prefix` `-` whose operand is an integer `Literal`: the negated constant's bit pattern, on both nodes |
| `true` / `false` `Literal` | 1 / 0 |
| `Text` | the id of its decoded text in `texts` |
| raw-string `Literal` | the id of its content in `texts` |

Every other node is 0. Texts are decoded: escapes, doubled braces and the
multiline dedent are applied, so a consumer never reinterprets source spelling.
A `String`'s value is its children in order: each `Text` is its text, and each
`Interpolation` is the rendering of its value expression.

### `node_site`

`node_site[n]` is the id of the innermost `Statement` or `Tail` that contains
`n`, or -1 outside any body. **The trap site of an operation is the start of
`syntax.nodes[node_site[n]].span`**: the reference reports a trap at the start
of the statement or tail whose check fired, wherever in it the operation sits
(an overflow in an `if` condition traps at the `if`; one in a `return` operand
inside a block traps at that `return`).

## Semantics the checker guarantees

These are the facts the lowering may rely on after a successful check.

1. **Calls.** Every `Call`'s callee is a source `function` or the prelude's
   `print` or `assert`, called by name. The argument count equals the
   parameter count, and each argument's type id equals its parameter's. There
   are no implicit conversions anywhere in the core: a literal's adoption is
   already its type. Arguments are evaluated left to right, before the call.
   Recursion and forward references are ordinary calls.
2. **Arithmetic.** `+ - * / %` have two operands of one integer type, which is
   the result's; each is checked in that type, as `src/sem/` defines it: a
   result outside the type traps `overflow`, a zero divisor traps `div-zero`,
   and `MIN / -1` and `MIN % -1` trap `overflow` on a signed type. `+` on two
   `str`s is concatenation and never traps. Compound assignment `x op= e` is
   `x = x op e` with the same rules. The left operand is evaluated first.
3. **Prefix.** `-x` on a signed integer is `0 - x` in its type (so `-MIN`
   traps); on an unsigned type it is `0` for `0` and traps `overflow` otherwise.
   `!x` is logical not on `bool` and the bitwise complement on an integer type,
   which never traps.
4. **Comparison.** `==` and `!=` take two operands of one type: an integer type
   (by value, unsigned types unsigned), `bool`, or `str` (bytewise). `<`, `<=`,
   `>`, `>=` take an integer type or `str` (byte order). Each yields `bool`.
   Comparison of structs is not in the core (the reference refuses it).
5. **Logic.** `&&` and `||` take and yield `bool`, and short-circuit: the right
   operand runs only when the left does not decide.
6. **Control.** An `if` condition and a `while` header are `bool`. An `if` with
   an `else` used as a value has both branches of the `if`'s type (or `never`).
   An `if` without `else` has type `()`. `break` and `continue` occur only
   inside a `while` and bind to the innermost one. A `return` operand has the
   function's ok type; a bare `return` occurs only in a function whose ok type
   is `()`.
7. **Results.** A function's body has its declared result type, or for `!T`
   its ok type `T`. **The core raises nothing**: no error tag, `?` or fallible
   call is in it, so a `!T` result always holds its ok value, and a `!T`
   function is called by no core program (only `main` may be one in practice).
   `main`, when present, has no parameters and returns `()`, `int`, `!()` or
   `!int` (anything else is E0414); its process status is its `int` value, or 0.
   A file with no `main` still checks.
8. **Bindings and places.** A `let` binding and its fields are never assigned
   (E0410), and neither is a parameter (E1014). An assignment's place is a `var`
   local or a field path rooted at one; it holds the right-hand side's type. A
   local's scope runs from the end of its binder to the end of its block; a
   later binder of the same name shadows it; a binder's own initializer sees
   the previous binding. Comma groups bind left to right.
9. **Structs.** Field order is declaration order. A struct literal initializes
   every field exactly once (E0408 otherwise; an unknown field is E0403); its
   initializers run in source order and the value is assembled in field order.
   Struct values are copied whole on binding, passing, returning and field
   read; struct types form no cycle.
10. **Literals.** Every integer literal fits its type. A **negative literal**
    (a `Prefix` `-` directly over an integer `Literal`) is one constant: its
    negated value is what fits, so `-2147483648` is an `i32` and
    `-9223372036854775808` an `int`. Both nodes have the constant's type and
    value; the lowering materializes the `Prefix` and never negates at run
    time. A literal whose only
    context is an unannotated binding (directly, or through a term made only of
    literals) also fits `i32` (E0415), as `[type.numlit.value]` requires, even
    when a later use gives the binding a wider type.
11. **Interpolation.** A hole renders its value by type: an integer in decimal
    with `-` only on a negative value (unsigned values are never negative);
    `true`/`false`; a `str` as its bytes; `()` as `()`; a struct as
    `Name { f: v, g: w }` with each field rendered by its own rule and a
    zero-field struct as `Name { }`.

## Diagnostics and status

`types.check` runs its checks in a fixed order (the core scope check, then
resolution, then typing one function at a time in source order) and stops at the
first diagnostic, so the report is deterministic. A message of code `internal`
is a compiler invariant failure, reported with status 70. Reports use the
front end's source form, `FILE:LINE:COL: error[CODE]: MESSAGE (bytes
START..END)`. Codes the reference reports for the same program use its numbers
(`docs/DIAGNOSTICS.md` lists each). `fenrir --emit=typed FILE` returns 0 on
success, 2 for a source rejection or an I/O failure, 4 for an F0001 or F0002 refusal
(`[conf.exit.refused]`), and 70 for an internal error.

## Stable text form

`fenrir --emit=typed FILE` prints fenrir's own deterministic format, not a copy
of anything the reference prints:

```text
typed/1 "FILE" root=ROOT nodes=N
type ID KIND DECL INNER COUNT PARAM...
tag ID "NAME" COUNT PAYLOAD...
decl ID KIND "NAME" NODE TYPE OWNER INDEX COUNT
text ID "TEXT"
node ID KIND TYPE DECL SITE VALUE
```

Each table is printed in id order, and there is one `node` line for every AST
node. Strings use the AST form's escapes. Missing ids are -1. Two runs over the
same input are byte-identical.

## Complexity

The core scope check, declaration, resolution and typing each visit every node
a bounded number of times. Scopes are fenrir's own hashed tables with an undo
log per block (never the runtime `Map`, never a linear scan), and integer-kind
inference is union-find with path compression, so the whole check is
O(nodes · α(nodes)) time and O(nodes + tokens) space. A scaling row measures it
at N, 10N and 100N.

## Enum and match extension contract

This section was specified before its consumers changed. Typing implements
it (`tests/types/pattern_rows.py`), and the lowering emits it (LOWERING.md),
except that interpolating an enum value into a string is refused by name
(F0001) at `build`, `run` and `--emit=fir|asm`. The extension adds non-generic enums (including enum-form type aliases),
qualified constructors and `match`. It adds no tuples, lists, error rows,
parameter modes, methods or destructuring `let`/`var` bindings.

### Nominal enums and patterns

`Typed` gains `enums: List[int]` in source order, `warnings: List[Warning]`, and
`analysis: List[Analysis]`. The additional records are:

```text
Warning { code: str, message: str, node: int }
Analysis { function: int, name: str, cells: int, bytes: int, cap: str }
```

A type with `kind = "enum"` uses `decl` for its nominal declaration, with
`inner = first = -1` and `count = 0`, just like a struct. Struct and enum
nominal types are allocated together in declaration order after fixed id 11.
An enum declaration has kind `enum` and `count` variants; its next `count`
declarations have kind `variant`, `owner` the enum, and `index` the zero-based
source-order tag. A variant's `ty` is an interned `fn` signature whose result
is the owning enum and whose parameter types are the payload types; its
`count` is the payload arity. Unit payloads count at this interface even though
the lowering erases their storage. Recursive by-value aggregate layouts remain
outside the core, including cycles crossing enums and structs.

A constructor expression is qualified (`E.V` or `E.V(args)`), resolves to the
variant declaration and has the enum type. Arguments are typed and evaluated
left to right. Bare payload-carrying constructor values follow the pinned
language's default-payload behavior, independently of a bare constructor
*pattern*, which must have arity zero (E0808 otherwise).

Accepted match patterns are wildcard, binder, literal, integer range,
constructor, struct, tuple, `@` and or-patterns over the extended core's types.
An or-pattern's alternatives bind the same names at the same types. A name
missing from an alternative is E0828 at that alternative; a later binding at a
different type is E0401 at that binding. The checker uses sparse binding undo
logs, not a copy of every declaration per alternative. Constructor tests bind
nothing and may share a spelling with a real binding elsewhere in a product.
Each name is published once for the guard/body after the alternatives agree.
The native reference still has named execution refusals for binding joins;
those are labelled separately, never counted as output parity. A name bound
twice in one accepted pattern or parameter
list is E0827 at the second binding, with the first identified. Each D63 comma
group entry is a separate pattern, so ordinary shadowing remains legal. Literal
patterns outside their type still have a named refusal pending the complete
ruled literal-range check. A binding is a local of declaration kind `bind` and
is immutable for its guard/body, including field and index writes (E0410).
A `var x = x` shadow is a new mutable local, not a write to the matched value.
Bindings are scoped to that arm's guard and body, and shadow outer names only when
they actually bind. A bare pattern name is resolved against
its expected enum before it is treated as a binder. In particular a nullary
constructor pattern introduces no local and does not hide an outer binding.
Temporary resolver candidates do not survive in the successful typed tables;
final declaration ids remain dense and in source order.

The existing columns carry the additional facts:

- `node_decl`: enum/variant declarations and their names name themselves;
  qualified constructors and constructor calls/patterns name the variant;
  binder and `@` patterns name their local; struct patterns name the struct;
  field patterns name the field, with a shorthand's `Name` naming its local.
- `node_type`: patterns have the scrutinee/subfield type; guards are bool;
  `Match` and `Arm` have their joined result type. Never-valued bodies join as
  in `if`. In a unit context an arm body must be unit or never.
- `node_value`: literal patterns contain their scalar bits or decoded complete
  string's `texts` id. Range endpoints retain their checked literal values;
  the syntax's range operator distinguishes inclusive and exclusive bounds.
- `node_site`: the existing innermost Statement/Tail rule is unchanged. Guards
  and arm bodies keep their source sites, and the scrutinee is evaluated once.

### Coverage, warnings and refusal

Each function has a fresh bounded coverage state, shared by its matches, with
incremental arm coverage and memoized symbolic operations as COVERAGE.md
specifies. Pattern tests describe sets; they never execute user expressions.
Guards are checked and executed normally but never contribute exhaustiveness,
including a guard spelled `true`. Unguarded arms extend coverage in source
order. E0801 rejects missing cases; E0802 is an unreachable-arm warning and
never by itself changes successful status 0.

Integer columns follow `[gram.pat.range]`, not finite-machine-domain inference:
a wildcard or binder is required even for a bounded integer type. Empty ranges
are E0815. Range usefulness warnings follow the spec's conservative
single-earlier-arm subsumption rule: coverage only by a union of prior ranges
is not reported as E0802. The generic kernel does not decide this policy.
Rows must hold both the wildcard requirement and the conservative warning.

The producer charges pattern visits and its own paths, predicates, warnings
and witnesses before allocating them. Cap failure alone maps to F0004/status 4,
with function name, exhausted cap and both consumed counters. Internal kernel
failure maps to status 70. Neither becomes E0801, assumed coverage, or a program
trap. No executable output is published from partial typed tables.

Analysis records are the exception to the partial-table restriction: they are
self-contained snapshots, including a function that refused or failed during
coverage. `cap` is empty unless that function exhausted `cells` or `storage`.
Functions not reached after an earlier failure have no record, not fabricated
zero usage. A function with no `match` records its empty state: 0 cells and
512 bytes. `fenrir --emit=analysis FILE` follows the shared source load path,
emits these records even when checking refuses, and returns the same status:

```text
analysis/1 "FILE"
function DECL "NAME" CELLS BYTES "CAP"
```

Records follow source function order. Strings use the typed form's escapes.
This output is deliberately separate from executable/typed output and does not
permit consuming other partial tables. The ordinary `typed/1` table columns
remain unchanged; the new declaration/type kinds extend their vocabulary.

## Lists, maps, tuples and error rows extension

This extension adds `List[T]`, `Map[K, V]`, tuples, indexing, `for` over a
list or an integer range, the list and map methods, and error rows: `T ! {…}`
results, tags, raising, `?`, `else` with or without a handler, `match` over
a result or a caught row, error aliases and the inferred rows of `!T`. Typing
implements it (`tests/types/collection_rows.py` holds each refusal against
the reference's code and place), and the lowering emits it (LOWERING.md).
Interpolating a map, or a list, tuple or row that holds an enum, is refused by
name (F0001) at `build`, `run` and `--emit=fir|asm`.

### Types

The type table gains five kinds. Each is interned by its components, so equal
types are equal ids, and none survives with an unsolved integer variable.

| kind | `inner` | `first .. first + count` |
|---|---|---|
| `list` | the element type | none (`count` 0) |
| `map` | -1 | `type_params`: the key, then the value |
| `tuple` | -1 | `type_params`: the items in order |
| `result` | the ok type | `row_tags`: the row's tag ids |
| `row` | -1 | `row_tags`: a caught row's tag ids |

`Typed` gains `tags: List[Tag]` and `row_tags: List[int]`. A tag is
`Tag { name: str, first: int, count: int }`, its payload types being
`type_params[first .. first + count]`. Tags are structural: two rows that
name `Bad(int)` share one tag id. A row's tags are sorted by name, so equal
rows are equal ids. `!T` is a result whose row is inferred (below); a written
`T ! {…}` or `T ! Alias` names its row.

A map key is `str`, `bool`, `int` or `char` (another source integer kind is
E0418). An index is `int` (E0401 otherwise); a list literal's
elements share one type (E0401). A row spells each tag once among its own
entries (E0601, at the later entry) and names an alias with no payload
(E0601). Each alias a row names is one more layer, as a nested row is: a tag
two layers share merges when its payloads agree and is E0609 otherwise.
Aliases close no loop (E0610), whether or not a row names them.

### Declarations and annotations

An error alias (`error Name = {…}`) is a declaration of kind `alias` whose
`ty` is the row of its tags. A `for` binder is a `let`; each name of a
tuple pattern in a binding is a `let` or `var` as the binding is; a handler
(`else |e| …`) is one arm over the caught row, so its binder is a `bind`.

- `node_type`: a list literal, `Index`, `Tuple`, `Range` and `Propagate` have
  their value's type: an index read of a list is the element, of a map the
  value's result `V ! {none}`; `?` is its operand's ok type. A `Handler` has
  its body's type, and the `else` it belongs to the join of that and the ok
  type. A tag pattern in a `match` over a result or row has the scrutinee's
  type.
- `node_decl`: a raise of a tag (`return Bad(4)`, or a bare `Bad(4)` tail),
  a tag pattern's name, and the `List` or `Map` head of a written type or a
  constructor have -1: a tag, `List` and `Map` are not declarations. A
  method call's callee `Member` has no type, as a call's callee name has
  none.
- `node_value`: a raise has its tag id; a tag pattern has its tag id; a
  tuple member `.0` has its item index; a method `Call` has its method code:
  1 `push`, 2 `pop`, 3 `get`, 4 `first`, 5 `last`, 6 `is_empty`, 7 `len()`
  or `count`, 8 `clear`, 10 `pairs`, 11 `remove`. `push`, `pop`, `clear` and
  `remove` need a `(mut …)` receiver (E0804 otherwise).

### Rows and their handling

1. **Inferred rows.** A `!T` function's row is the tags its body can raise:
   every capitalized bare tag it raises, the row of every call it propagates
   with `?`, and `none` for every `?` on an index or a method that can miss.
   The checker reaches the rows by a fixpoint over the functions before it
   types any body, so a call's row never depends on source order. A
   lowercase bare tag must be declared in a written row (E0301 otherwise).
   A row that ends in `..` is open: it also takes what its body raises,
   and a call of its function that leaves another function, by `?` or as
   the returned value, needs that function's row open too (E0602 at the
   call; an inferred `!T` row is not open). An exported function writes its
   row out: `pub fn … -> !T` is E0605 at the function's name.
2. **Accepting a value.** Where a result is expected, an ok value is wrapped
   into it, and a result whose row is narrower converts to the wider one. A
   tag that escapes into a row that lacks it is E0602; a tag whose payload
   differs from the row's is E0606.
3. **Propagation.** `e?` needs a fallible `e` (E0603) inside a fallible
   function (E0604); it yields the ok value and returns the error otherwise.
4. **Defaults and handlers.** `e else d` evaluates `d` only on an error;
   `e else |x| body` binds the caught row to `x`. `else` on a value that
   cannot fail is E0608. A handler's payload pattern that leaves tags
   unhandled is E0809; a bare name in a handler always binds.
5. **Matching a result or a row.** The arms test tags by name, bind the ok
   value with a binder pattern, and must cover every tag and the ok value
   (E0801). A row tag that is also a variant of the ok enum is E0816.
6. **Discarding.** A `!T` value in a unit context, as a statement or a unit
   block's tail, is discarded (`[type.unit.discard]`).
7. **The entry.** An unhandled error from `main` prints `error: TAG`, the
   tag's name without its payload, on stdout and exits 1.

Index stores on a `var` list or map are places (`xs[i] = v`, `m[k] = v`); a
compound assignment through a map index is E0417 at the place, since the
entry may be absent. A list index read or store outside the list traps
`bounds` at the statement's site; a map read never traps, its miss is the
`none` row.

## String primitives extension

The first string primitives add `.len`, `len()`, checked half-open slices and
`get(a..b)` to the existing literal, concatenation and comparison core. Offsets
are `int` bytes, not Unicode scalar indices. A checked slice has type `str`;
`get` has type `str ! {none}`. Endpoints evaluate once, left to right, after
the receiver. Invalid offsets, reversed bounds and UTF-8 splits trap `bounds`
for a checked slice and return `none` for `get`.

A plain `s[i]` is E0411 at the index expression; a store through a string
index or slice is E0416 at the place. A string never becomes mutable through
an index. These numbers and spans are checked against the pinned reference.
Inclusive, open and end-relative string ranges are normalized as described
above; the recoverable normalization is total even at extreme signed offsets.

A string method `Call`'s `node_value` uses these stable codes: 100 `len`,
101 `get`, 102 `to_int`, 103 `find`, 104 `rfind`, 105 `starts_with`,
106 `ends_with`, 107 `contains`, 108 `count`, 109 `repeat`, 110 `replace`,
111 `split`, 112 `words`, 113 `lines`, 114 `trim`, 115 `trim_start`,
116 `trim_end`, 117 `is_empty`, 118 `bytes`, 119 `chars`. The last two
answer `List[byte]` and `List[char]`. On-the-spot byte consumers retain the
str pair in lowering; bindings, returns and unclassified arguments use the
materialized list fallback. String search answers `int ! {none}`;
parsing answers `int ! {parse}`; the split family answers `List[str]`.
The parse tag is included in inferred function rows when propagated with `?`.
A range argument's `node_type` is `str`, and its endpoint nodes are `int`.
Fixed type and declaration ids are unchanged by these primitives.

## Character and byte primitive contract

The next string increment adds source types `char` and `byte`, at fixed ids
10 and 11. Their prelude declarations are appended at ids 10 and 11 too;
all existing fixed ids and the first ten prelude declarations stay unchanged.
Nominal source types now follow fixed id 11. This does not renumber FIR:
the lowering erases a character or byte to a canonical int word and retains
its source type for operator checking and rendering.

A character literal records its decoded Unicode scalar in `node_value`.
Character equality and ordering compare scalar values; concatenation accepts
`str + char`, `char + str` and `str += char`. A character's interpolation is
its UTF-8 encoding, never its scalar number. Character literal patterns use
the integer-column discipline: a wildcard/binder is still needed, and escape
spellings of one scalar test the same value. `Map` also accepts character
keys. A byte remains distinct from the integer source types; its list element
word representation is not permission to perform source integer arithmetic.
String byte/scalar materialization methods remain subsequent work.

## Interface change record

- The character and byte primitive contract: source fixed ids and prelude
  declarations 10/11, nominal source types after 11, and int-word erasure in
  FIR with source-directed character rendering.

- The string primitives extension: byte length, half-open checked and
  recoverable slices, E0411/E0416, and string method codes 100/101.

- The enum and match extension above: `Typed.enums`, `warnings` and
  `analysis`; the `enum` type kind; the `enum`, `variant` and `bind`
  declaration kinds; struct and enum nominal types in one declaration-order
  sequence; and `--emit=analysis`.
- The lists, maps, tuples and error rows extension above: the `list`, `map`,
  `tuple`, `result` (with a row) and `row` type kinds; `Typed.tags` and
  `Typed.row_tags`; the `alias` declaration kind; method codes, raise and
  tag-pattern values in `node_value`; and two more text-form lines, `tag ID
  "NAME" COUNT PAYLOAD...`, with a result or row type's `PARAM...` naming its
  tag ids.

Version 1 introduces this interface. After integration, any change to a table,
a column's meaning, the core's extent, a fixed id or the text form adds an entry
here before its consumers are updated.

Changes since the first draft, before integration:

- `Decl.type` is `Decl.ty`, because `type` is a keyword, and `Decl` lives in the
  `resolve` module (`Typed.decls: List[resolve.Decl]`).
- A negative literal is one constant on both of its nodes (`node_value`, and
  semantics item 10).
- A call's callee `Name` carries no type; its declaration is the callee.
- Diagnostics come from checks in a fixed order, not by source position across
  checks; `internal` names an invariant failure (status 70).
- The core is one file: a file with member siblings is refused before the check.
- `types.load(path) -> Source` is the shared entry (read, parse, module shape,
  check); `fenrir --emit=typed` is `load` then the text form.
