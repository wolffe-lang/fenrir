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
| `brackets:generic-or-index-or-list` | 240 | no | List types, range tables, and arena/byte indexing. |
| `delimiter:braces` | 1266 | no | Function/control bodies and Span, Token, Node, Lexer and Syntax records. |
| `delimiter:colon` | 284 | no | Function signatures and record field annotations. |
| `delimiter:comma` | 4465 | no | Call arguments, record fields, and generated Unicode range lists. |
| `delimiter:parentheses` | 3238 | no | Calls, conditions, grouping and explicit receiver modes. |
| `delimiter:semicolon` | 121 | no | Bounded single-line blocks and explicit sequencing. |
| `identifier` | 5884 | no | Source names, coordinates, state fields and helper names. |
| `keyword:as` | 12 | no | Byte/integer representation casts. |
| `keyword:break` | 23 | no | Exit scanner/parser list and delimiter loops. |
| `keyword:continue` | 10 | no | Advance monotone scanner and trivia loops. |
| `keyword:copy` | 11 | no | Fixed-size token, node and span reads preserve arena ownership. |
| `keyword:else` | 119 | no | Control-flow alternatives and fallible filesystem/list defaults. |
| `keyword:error` | 20 | no | Contextual identifier spelling in diagnostic state, not an error-alias declaration. |
| `keyword:false` | 35 | no | Boolean state and parser-mode arguments. |
| `keyword:fn` | 107 | no | Named module functions; source uses no closures. |
| `keyword:for` | 1 | no | Linear byte-segment iteration in format validation. |
| `keyword:if` | 427 | no | Scanner, precedence, diagnostic and rail branches. |
| `keyword:in` | 1 | no | The format-validation for-loop; source uses no in-region blocks. |
| `keyword:let` | 173 | no | Immutable local state and fallible-result bindings. |
| `keyword:match` | 1 | no | Filesystem error-tag dispatch. |
| `keyword:move` | 2 | no | Transfer completed token lists without repeated materialization. |
| `keyword:mut` | 1094 | no | Exclusive parser/scanner parameters and explicit List receivers. |
| `keyword:pub` | 32 | no | Front-end entry points, arena types and consumer-visible fields. |
| `keyword:return` | 139 | no | Early returns and first-error control flow. |
| `keyword:self` | 2 | no | Contextual identifier spelling used to recognize receiver parameters. |
| `keyword:struct` | 5 | no | Span, Token, Lexer, Node and Syntax records. |
| `keyword:true` | 91 | no | Boolean state and parser-mode arguments. |
| `keyword:use` | 2 | no | Driver module imports. |
| `keyword:var` | 57 | no | Mutable cursors, depth counters, arena builders and scanner state. |
| `keyword:while` | 83 | no | Monotone byte, token and child-chain loops. |
| `literal:integer` | 3562 | no | Offsets, bounds, byte values, rail constants and generated Unicode ranges. |
| `literal:raw-string` | 55 | no | Literal brace token spellings without interpolation. |
| `literal:string` | 990 | no | Token/node kind names, punctuation, messages and emitted text. |
| `member-or-method` | 485 | no | Record fields, List mutation and string operations. |
| `operator:arithmetic-or-pointer` | 93 | no | Offset/range arithmetic; no raw pointer operations in the front end. |
| `operator:arrow` | 85 | no | Function return annotations and filesystem-error match arms. |
| `operator:assignment` | 370 | no | State, arena-field and cursor updates. |
| `operator:bitwise-or-closure-or-reference` | 2 | no | Filesystem error-handler delimiters; no closure bodies in source. |
| `operator:comparison` | 829 | no | Token, byte, boundary and rail comparisons. |
| `operator:error-or-negation` | 42 | no | Boolean negation; this lexical family also names error-type syntax. |
| `operator:logical` | 458 | no | Short-circuit validation and parser-mode conditions. |
| `operator:range-or-rest` | 10 | no | Half-open source slices and driver argument slicing. |
| `string-interpolation` | 40 | no | Stable text dumps and file/line/column diagnostics. |

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
