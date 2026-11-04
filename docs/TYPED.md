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

Everything else (enums, `match`, generics, traits, impls and methods, closures
and fn values, lists, `Map`, tuples, indexing, ranges, `for` and `loop`, casts,
error rows and tags, `?`, `else` handlers, calls of fallible functions, regions,
modules and `use`, attributes, constants, module-level bindings, nested items,
format specs, char and float literals, bitwise and shift operators, parameter
and argument modes, other prelude entries, recursive structs) is refused by name
with **F0001** (`not yet in fenrir: CONSTRUCT`) at the construct's span. That
refusal is fenrir's scope, never a verdict about the program.

## Representation

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

## Interface change record

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
