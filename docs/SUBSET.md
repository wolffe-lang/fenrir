# Bootstrap subset

The implemented compiler subset is empty. Parser acceptance is never compilation.
The table below is a lexical construct inventory of fenrir's own Wolf source,
not a claim of compiler support. Add a row when source first uses a construct;
update the computed count when source changes. `tools/check-subset --inventory`
prints counts but never rewrites this document. Run the gate after updating it.

close_gap: false

The used-but-not-compiled gap is printed by name and count on every gate run.
It is informational during bootstrap. Closing the language-for-fenrir milestone
requires setting `close_gap: true`; after that any nonempty gap fails. No date
or host switches this rule. A compiled claim replaces `no` with
`F1:tests/subset/ROW.py` (use the actual milestone). The gate executes each
named integration row once in the current checkout and requires exit 0.
The row must compile and run a witness with fenrir, not merely parse it.
Unknown constructs, stale counts and unproved compiled claims always fail.

## Classifier and limitations

The classifier in `tools/constructs.py` scans each source byte a bounded number
of times. It ignores whitespace, line comments and nested block comments.
Each keyword-like spelling in the classifier's conservative list gets its own
`keyword:WORD` row (for example `fn`, `match`, `enum`, `trait`, imports,
parameter modes and control flow). This list also includes contextual names and
is not the grammar's closed reserved-keyword inventory.
Identifiers have their own class, and integers, floats, character, raw,
multiline and ordinary strings have separate literal classes. A quoted string
with an unescaped, undoubled opening brace also counts `string-interpolation`;
its body is conservatively one opaque interpolation construct, not parsed
expressions. Nested quotes in interpolation are not resolved by this gate:
only the front-end parser can disambiguate them.

Each punctuation or operator token belongs to the family in its name below.
Brackets deliberately combine generics, indexing and list syntax; dot combines
member access and methods; `!` combines error types and logical negation;
`?` marks propagation; `|` combines closure bars and bitwise operators;
`*` combines arithmetic and pointer syntax. Arrows combine return and match
arrows. `#`, `@` and `::` combine attributes and qualification. These lexical
unions cannot certify semantic use of one member alone. Unknown punctuation
and unclosed strings/comments get explicit `unknown:` names and fail unless
listed. This gate does not validate syntax or name resolution; stage 0 builds
and the front-end tests do that. Replace unions with parser-derived constructs
when that interface is stable, without weakening the unknown-construct plant.

## Inventory

| Construct | Used (computed token count) | Compiled (milestone:row) | Notes |
|---|---:|---|---|
| `brackets:generic-or-index-or-list` | 2376 | no | List types, range tables, and arena/byte indexing. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `delimiter:braces` | 4580 | no | Function/control bodies and Span, Token, Node, Lexer and Syntax records. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `delimiter:colon` | 1635 | no | Function signatures and record field annotations. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `delimiter:comma` | 8236 | no | Call arguments, record fields, and generated Unicode range lists. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `delimiter:parentheses` | 8544 | no | Calls, conditions, grouping and explicit receiver modes. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `delimiter:semicolon` | 308 | no | Bounded single-line blocks and explicit sequencing. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `identifier` | 21513 | no | Source names, coordinates, state fields and helper names. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:as` | 71 | no | Byte/integer representation casts. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:break` | 25 | no | Exit scanner/parser list and delimiter loops. |
| `keyword:continue` | 18 | no | Advance monotone scanner and trivia loops. |
| `keyword:copy` | 33 | no | Fixed-size token, node and span reads preserve arena ownership. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:defer` | 7 | no | Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:else` | 403 | no | Control-flow alternatives and fallible filesystem/list defaults. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:error` | 29 | no | Contextual identifier spelling in diagnostic state, not an error-alias declaration. |
| `keyword:false` | 115 | no | Boolean state and parser-mode arguments. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:fn` | 388 | no | Named module functions; source uses no closures. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:for` | 74 | no | Linear byte-segment iteration in format validation. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:if` | 1299 | no | Scanner, precedence, diagnostic and rail branches. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:in` | 74 | no | The format-validation for-loop; source uses no in-region blocks. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:let` | 855 | no | Immutable local state and fallible-result bindings. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:match` | 18 | no | Filesystem error-tag dispatch. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:move` | 37 | no | Transfer completed token lists without repeated materialization. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:mut` | 2170 | no | Exclusive parser/scanner parameters and explicit List receivers. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:pub` | 159 | no | Front-end entry points, arena types and consumer-visible fields. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:return` | 697 | no | Early returns and first-error control flow. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:self` | 2 | no | Contextual identifier spelling used to recognize receiver parameters. |
| `keyword:struct` | 40 | no | Span, Token, Lexer, Node and Syntax records. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:true` | 147 | no | Boolean state and parser-mode arguments. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:use` | 34 | no | Driver module imports. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:var` | 361 | no | Mutable cursors, depth counters, arena builders and scanner state. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `keyword:while` | 252 | no | Monotone byte, token and child-chain loops. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `literal:integer` | 5062 | no | Offsets, bounds, byte values, rail constants and generated Unicode ranges. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `literal:raw-string` | 57 | no | Literal brace token spellings without interpolation. |
| `literal:string` | 2717 | no | Token/node kind names, punctuation, messages and emitted text. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `member-or-method` | 2698 | no | Record fields, List mutation and string operations. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `operator:arithmetic-or-pointer` | 578 | no | Offset/range arithmetic; no raw pointer operations in the front end. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `operator:arrow` | 310 | no | Function return annotations and filesystem-error match arms. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `operator:assignment` | 1875 | no | State, arena-field and cursor updates. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `operator:bitwise-or-closure-or-reference` | 136 | no | Filesystem error-handler delimiters; no closure bodies in source. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `operator:comparison` | 2122 | no | Token, byte, boundary and rail comparisons. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `operator:error-or-negation` | 133 | no | Boolean negation; this lexical family also names error-type syntax. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `operator:logical` | 786 | no | Short-circuit validation and parser-mode conditions. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `operator:propagate` | 106 | no | Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `operator:range-or-rest` | 19 | no | Half-open source slices and driver argument slicing. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |
| `string-interpolation` | 312 | no | Stable text dumps and file/line/column diagnostics. Backend bootstrap; see tests/backend/fir.py, assembly.py and link.py. |

## Front-end bootstrap expansion

The front end uses only the constructs named above. Its implementation witnesses
are `tests/front/check.py` with `rows.json` and `grammar.json`, the complete
`tests/front/corpus.py` census including its own source, the Unicode generation
check, and Linux-capped `tests/front/stress.py`. They demonstrate parsing and
native bootstrap execution under the pinned reference compiler, **not** source
compilation by fenrir. No compiled capability is added by this inventory update.

`keyword:error` and `keyword:self` illustrate the classifier's lexical scope:
these counts include contextual identifier spellings in code and field access;
they do not certify an error-alias declaration or a receiver declaration.
Likewise, a literal brace token represented by a raw string is not a block in
fenrir's own implementation. Bracket/operator families remain the unions above.

## Backend bootstrap expansion

The backend adds only the constructs its source uses: typed scalar/struct/List
values, indexed tables, loops and branches, explicit mutable receivers, moves
and copies, error rows with propagation/matching, UTF-8 conversion, byte views,
interpolation, filesystem calls and argv-based subprocesses. These execute
under stage 0; they are not yet compiled from Wolf source by fenrir. FIR
acceptance is a separate backend interface, not evidence that this gap closed.

## Resolution and typing bootstrap expansion

The resolver and checker (`src/resolve/`, `src/types/`, and the literal and
text rules in `src/sem/`) add no construct family: only the counts above moved.
They use records and lists, indexed `while` loops, `for` over lists, `if`/`else`
and the `then` form, explicit mutable receivers and parameters, `copy` and
`move`, error rows with marks and payloads handled by `else` handlers and `?`,
`as` casts between `byte` and `int`, list literals, string interpolation, and
`use` between modules. These execute under stage 0; fenrir does not compile
them yet. The generated prelude table (`src/resolve/prelude.lu`) is string
literals in two list literals.
