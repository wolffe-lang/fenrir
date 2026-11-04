# Abstract syntax interface

The `front` module owns this interface. `front.parse(file: str, text: str) -> Syntax`
parses one translation unit. Callers must inspect `Syntax.code` before consuming
its tree: an empty code means success; a nonempty code means the first diagnostic
and a partial, non-consumable arena. `front.emit(path: str, mode: str) -> int`
implements the CLI's token and AST views. It returns 0 on success, 2 on a source
or I/O error. Internal failures belong to the driver's separate status 70, never
to a syntax refusal or an environment skip.

## Representation and ownership

`Syntax` owns `file`, UTF-8 `text`, `tokens: List[Token]`, and
`nodes: List[Node]`. `root` is the Unit's integer node id. Its remaining fields
(`pos`, `depth`, `string_depth`, `code`, `message`, `error`) are parser state and
the first diagnostic; consumers do not mutate them. Ids are indices, not pointers.
The parser appends to the token and node arenas and does not intern names in a
linear-scan map. Name resolution is a later phase.

Every `Token` has `kind: str` and `span: Span`. Every `Node` has:

| field | invariant |
|---|---|
| `kind: str` | one kind from the tables below |
| `span: Span` | the full construct, including its delimiters |
| `token: int` | index of the construct's first token; leaves obtain their spelling here |
| `first: int` | first child id, or -1 |
| `last: int` | last child id, or -1 exactly when first is -1 |
| `next: int` | next sibling id, or -1 |

A successful tree is connected and acyclic, each non-root node has exactly one
parent, every child span is inside its parent's, and `last.next == -1`. Children
are linked in **source order**, not allocation order. In particular, an infix
wrapper can be allocated after its left operand. Traverse `first`, then `next`;
never assume that a subtree occupies a contiguous arena slice. No mutable arena
reference may be kept across an append. Consumers may retain integer ids.

`Span` fields are `file: str`, `start: int`, `end: int`, `line: int`, `col: int`,
`end_line: int`, `end_col: int`. Byte intervals are zero-based, half-open, on the
original source, including an initial BOM if present. Lines and columns are
one-based; a column counts Unicode scalars, not bytes or display cells. A tab
counts one. An initial BOM consumes bytes but not a source column. Endpoints
are UTF-8 boundaries. EOF and inserted EOF terminators can have empty spans.

The arena retains syntax, not type judgments. An index may be generic application;
a NamePattern may bind a name or name a nullary constructor; a name in a checked
position may be an error tag. Resolution decides. Literal and string spellings
are losslessly available through token spans. They are not decoded into runtime
values by the parser. The next phase decodes escapes, applies multiline dedent,
and resolves names and types; it must not reinterpret string text as source.

## Units and declarations

`?` denotes an optional child and `*` a sequence. The spelling of a leaf is the
source slice of its `token`. Metadata leaves below are real spanned nodes.

| kind | ordered children and meaning |
|---|---|
| Unit | InnerAttribute*, Item*; the only root |
| Item | Attribute*, Visibility?, one declaration below |
| Visibility | optional Name `pkg`; token is `pub` |
| Function | Qualifier/ABI literal sequence, Name, Generics?, Parameters, ReturnType?, Block?; absent block is a bodyless signature |
| Qualifier | leaf `comptime`, `extern`, or `export`; an extern ABI literal follows it in the function's children |
| Generics | GenericParameter+ |
| GenericParameter | Name, optional Bound or BuiltinType `type` |
| Bound | Path+; the separators are `+` |
| Parameters | Parameter* and optional final Variadic |
| Parameter | Mode?, Name, ViewSet? or a type?; `self` may omit a type; closure parameters may also omit it |
| ViewSet | Name+; the field-granular `self.{x,y}` suffix |
| Variadic | leaf `...`; only final, after a fixed parameter |
| ReturnType | exactly one type; token is `->` |
| Bindings | BindingKind, Binder+; one `let` or `var` comma group |
| BindingKind | leaf `let`, `var`, or `const` |
| Binder | pattern, optional type, initializer expression |
| Constant | Name, optional type, initializer expression |
| ExternBinding | extern Qualifier and ABI literal, BindingKind, Name, type, optional initializer; the checker refuses forbidden modes/initializers |
| TypeAlias | Name, Generics?, type or Fields or Variants |
| Struct | Name, Generics?, Fields |
| Fields | Field* |
| Field | Attribute*, Visibility?, Name, type |
| Enum | Name, Generics?, Variants |
| Variants | Variant+ |
| Variant | Name, payload types* |
| Trait | Name, Generics?, Bound for an alias, otherwise Item* members |
| Impl | Generics?, subject type, optional `for` type, Item* members |
| ErrorAlias | Name, closed ErrorRow |
| Use | Path, selected Name*, optional final alias Name; source punctuation distinguishes selection and `as` |
| ImportC | contextual Name `c`, header String |
| Attribute / InnerAttribute | AttributeEntry+ |
| AttributeEntry | Path, optional literal or nested AttributeEntry/literal argument sequence; source `(` versus `=` retains the input form |

A function with an explicit unit return has a ReturnType child; a function with
no return annotation does not. Trait and impl members are functions, types, or
constants, never ordinary bindings. `pub` is accepted on impl methods as described
below. Attributes are parsed structurally; whether an attribute is implemented,
in the right position, or conditionally removes a node belongs to a later phase.
A late file-wide attribute is already a syntax error (E0211).

## Types

| kind | ordered children and meaning |
|---|---|
| NamedType | Path, TypeArguments? |
| Path | Name+; dots are retained in the token stream |
| PrefixType | one type, or Path for `dyn`; first token says `!`, `*`, `shared`, `handle`, `weak`, `distinct`, or `dyn` |
| BuiltinType | leaf `type` or `region` |
| TupleType | types*; no children is `()`; for one child, retain the comma/grouping distinction in its tokens |
| FunctionType | TypeParameters, ReturnType? |
| TypeParameters | types*; the function type's parenthesized input list |
| TypeArguments | type-or-expression nodes+; ambiguous const/type heads remain expressions for resolution |
| ErrorType | underlying type, ErrorRow or Path naming a row alias |
| ErrorRow | RowEntry*, optional OpenRow; an empty row is supported below |
| RowEntry | Path, payload types* |
| OpenRow | leaf `..`; absent from a closed alias row |

Postfix rows are retained as nested ErrorType nodes, not flattened by the parser.
Flattening, alias expansion, payload agreement and row closure are later checks.

## Expressions and statements

| kind | ordered children and meaning |
|---|---|
| Name | leaf identifier, including contextual names |
| Literal | leaf integer, float, char, bool, raw or generalized literal; Token.kind distinguishes them |
| String | Text or Interpolation children*; opening token distinguishes plain/multiline |
| Text | leaf raw source string segment, including its escapes and doubled braces |
| Interpolation | value expression, then Format / FormatArgument children* |
| Format | leaf raw format-spec text chunk; the first chunk includes `:` |
| FormatArgument | one dynamic width/precision expression between braces |
| Group | one parenthesized expression; unlike Tuple, no comma |
| Tuple | expression+; a comma, including a trailing one, selects this kind |
| List | expression* |
| StructLiteral | name/member path expression, FieldInitializer* |
| FieldInitializer | Name, expression?; missing expression means shorthand, not an absent value |
| Prefix | Operator, Mode? (`& mut` only), operand |
| FromEnd | Operator `^`, operand; retained for subscript/range interpretation |
| Binary | left expression, Operator, right expression |
| Cast | expression, Operator `as`, type |
| Range | optional start expression, Operator, optional end expression; at least one endpoint exists |
| Default | left expression, Operator `else`, fallback expression or Handler |
| Handler | closed pattern, fallback expression/block |
| Call / Index | receiver expression, CallArguments / IndexArguments |
| CallArguments / IndexArguments | Argument* |
| Argument | Mode?, type-or-expression; type-only prefixes and bare `region` are accepted in index arguments |
| Receiver | Mode, expression; its closing `)` must be followed immediately by a member suffix |
| Mode | leaf `mut` or `take` |
| Member | receiver expression, MemberName |
| MemberName | leaf identifier, integer tuple index or reserved keyword |
| Propagate | one expression; postfix `?` |
| If | condition, then expression/block, else expression/block?; a nested If retains an `else if` chain |
| Match | scrutinee, Arm* |
| Select | Arm+ |
| Arm | Match: pattern, Guard?, body; Select: pattern then source expression then body, or Timeout then timeout expression then body |
| Guard | one expression; token is `if` |
| Timeout | leaf contextual `timeout` |
| Loop | LoopKind, pattern only for `for`, header expression for `for`/`while`, Block |
| LoopKind | leaf `for`, `while` or `loop` |
| Jump | JumpKind, operand? (`return`/`break` only) |
| JumpKind | leaf `return`, `break` or `continue` |
| Closure | Parameters, body expression or Block |
| Region | optional Name, RegionCapacity?, RegionStrategy?, Block |
| RegionValue | RegionStrategy?, RegionCapacity?; the value spelling `region(...)` |
| InRegion | region expression, Block |
| RegionStrategy | Name `rc` or `pool`, optional pool element type |
| RegionCapacity | one expression; token is contextual `cap` |
| Scope | Name?, Block |
| Spawn | Path, CallArguments; `spawn proc` |
| When | expression+, Block; at least two acquisition expressions |
| Unsafe | Block |
| InlineC | Captures?, CBody |
| Captures | Name+ |
| CBody | leaf opaque brace-balanced C body, including braces; quotes and C comments do not affect balancing |
| Asm | template String, AsmOperand* |
| AsmOperand | optional bound Name, AsmDirection, constraint Name, expression |
| AsmDirection | leaf `in`, `out`, `inout` or `lateout` |
| Borrow | borrowed expression, source expression |
| Block | Statement* and optional final Tail |
| Statement | Attribute*, one Item, expression, Assignment, Defer, or Assume |
| Tail | Attribute*, one final expression; includes an implicit newline terminator when present, but not an explicit `;` |
| Assignment | place expression, Operator, Mode? (`take` on plain indexed stores only), right expression |
| Defer | DeferKind, expression |
| DeferKind | leaf `defer` or `errdefer` |
| Assume | expression+; at least two, after `assume noalias` |
| Operator | leaf operator token; its exact spelling is authoritative |

Expression precedence follows the published table. Comparisons and ranges do not
chain. Defaulting associates right. A braced closure body ends at its closing
brace; an expression body extends maximally. Conditions and loop/match headers
use no-struct-literal mode, restored inside parentheses. Bare `if` branches stop
at their own `else`; a parenthesized default can still occur inside one.

## Patterns

| kind | ordered children and meaning |
|---|---|
| WildcardPattern | leaf `_` |
| NamePattern | Path; binding versus nullary constructor is unresolved |
| LiteralPattern | one literal |
| RangePattern | lower literal, RangeOperator, upper literal; no open ends |
| RangeOperator | leaf `..` or `..=` |
| TuplePattern | pattern+; commas are required |
| ConstructorPattern | Path, payload pattern+ |
| StructPattern | Path, FieldPattern+, RestPattern? |
| FieldPattern | Name, pattern?; omitted pattern binds the field's name |
| RestPattern | leaf `..`, after a separating comma |
| AtPattern | binding Path, closed pattern |
| OrPattern | closed pattern+ |

The parser does not check constructor arity, irrefutability, field uniqueness,
range endpoint types, or exhaustiveness. Those facts require resolution/types.

## Stable text forms

These are fenrir's own formats, not copies of the reference compiler's output.
The first line is `tokens/1 "FILE"` or `ast/1 "FILE" root=ID`.
The AST form then contains the token table followed by the node table.

```text
token ID KIND START END LINE COL END_LINE END_COL "SPELLING"
node ID KIND TOKEN FIRST LAST NEXT START END LINE COL END_LINE END_COL
```

Ids are decimal integers, contiguous from zero, in allocation order. `-1` is the
only missing id. Paths and spellings escape backslash, double quote, LF, CR, tab,
and NUL with `\\`, `\"`, `\n`, `\r`, `\t`, `\0`. Other valid Unicode scalars
are preserved. This is a text protocol, not JSON. A token spelling is the exact
source slice; an inserted `term` spans its newline (or is empty at EOF), while
`;` stays a distinct explicit token. Comments and the initial shebang are trivia;
line/column information and source byte gaps retain their locations.

The string token sequence is `string-open` or `multi-open`, then `text` and
`interp-open`/expression/optional format/`interp-end`, then `string-end`.
Dynamic format expressions use `format-open` and `interp-end`. Raw, generalized,
and character literals are single tokens. The stream ends in `eof`.

## Beyond the EBNF

The pinned corpus is also a normative input to this implementation. These
additive spellings are accepted explicitly, not silently called EBNF derivations.

| spelling | corpus examples | production extended | positive / negative front-end rows |
|---|---|---|---|
| unit type `()` | `memory/region_unit_tail_call.lu`, `rows/unit_discard_unit_main.lu` | `type` | `unit-type-positive`, `unit-type-negative` |
| empty row `{}` | `rows/eu_bind_empty_row_unit.lu`, `typecheck/main_unit_row.lu` | `error_row` | `empty-error-row-positive`, `empty-error-row-negative` |
| `pub` impl methods | `typecheck/variant_value/paint/p.lu` | `impl_member` | `pub-impl-positive`, `pub-impl-negative` |
| dynamic width `{w}` | `grammar/interp_fmtcolon.lu` | `FORMAT_SPEC` | `dynamic-width-positive`, `dynamic-width-negative` |

## Coverage and complexity

Recursive descent handles declarations, types, patterns and control flow;
precedence climbing handles expressions. Both make context and ambiguity rules
visible without speculative reparsing. Lexing, termination, delimiter checking,
parsing and emission are O(source bytes + tokens + nodes). Identifier property
lookups are binary searches in fixed, generated Unicode range tables. Lists are
append-only/amortised O(1); no runtime Map backs a compiler index. Storage is
O(source bytes + tokens + nodes), with bounded parser and string recursion.

`tests/front/coverage.json` and `grammar.json` pair a positive and negative
executable row with each of the 144 EBNF productions and 82 `gram.*` anchors.
Rows share explicit fixture families; this is production/anchor coverage, not a
claim that every possible derivation or every semantic clause is implemented.
The coverage gate compares both pinned key sets in both directions and proves
that deleting each positive row is rejected. Positive rows validate tree
connectivity, sibling order, source containment, UTF-8 endpoints and coordinates,
and repeat emission byte-for-byte. The corpus census parses every file, including
module members and this compiler's source. Growing inputs and token fuzz run only
on Linux under hard child address-space and container memory limits.

**fenrir has no formatter.** The following 20 anchors have only parser-acceptance
and metadata-integrity coverage; their negative rows test syntax/registry errors,
never reject valid noncanonical layout. This scope is separate from syntax
implementation coverage:

- `gram.fmt`, `gram.fmt.brace`, `gram.fmt.break`, `gram.fmt.canon`
- `gram.fmt.commas`, `gram.fmt.continuation`, `gram.fmt.if`, `gram.fmt.imports`
- `gram.fmt.indent`, `gram.fmt.inline`, `gram.fmt.list`, `gram.fmt.paren`
- `gram.fmt.region`, `gram.fmt.strings`
- `gram.version`, `gram.version.1`, `gram.version.anchor`, `gram.version.enforce`

## Interface change record

Version 1 introduces this arena and the text forms above. After integration,
any node, child-order, span or text-form change must add an entry here before its
consumers are updated. Do not silently repurpose a kind or child position.
