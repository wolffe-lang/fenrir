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
Each reserved keyword spelling gets its own `keyword:WORD` row (for example
`fn`, `match`, `enum`, `trait`, imports, parameter modes and control flow).
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
| `attribute-or-qualified-name` | 1 | no | Bootstrap use only. |
| `brackets:generic-or-index-or-list` | 30 | no | Bootstrap use only. |
| `delimiter:braces` | 22 | no | Bootstrap use only. |
| `delimiter:colon` | 7 | no | Bootstrap use only. |
| `delimiter:comma` | 7 | no | Bootstrap use only. |
| `delimiter:parentheses` | 34 | no | Bootstrap use only. |
| `identifier` | 67 | no | Bootstrap use only. |
| `keyword:fn` | 5 | no | Bootstrap use only. |
| `keyword:if` | 6 | no | Bootstrap use only. |
| `keyword:let` | 1 | no | Bootstrap use only. |
| `keyword:pub` | 4 | no | Bootstrap use only. |
| `keyword:return` | 5 | no | Bootstrap use only. |
| `keyword:use` | 2 | no | Bootstrap use only. |
| `literal:integer` | 22 | no | Bootstrap use only. |
| `literal:string` | 13 | no | Bootstrap use only. |
| `member-or-method` | 9 | no | Bootstrap use only. |
| `operator:arrow` | 5 | no | Bootstrap use only. |
| `operator:assignment` | 1 | no | Bootstrap use only. |
| `operator:comparison` | 10 | no | Bootstrap use only. |
| `operator:logical` | 4 | no | Bootstrap use only. |
| `operator:range-or-rest` | 1 | no | Bootstrap use only. |
| `string-interpolation` | 7 | no | Bootstrap use only. |
