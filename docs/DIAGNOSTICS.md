# Diagnostics

The front end stops at the first source-ordered diagnostic. Lex and parse form
one rung: the earliest starting byte wins, with lex before parse at a tie.
Unclosed delimiter diagnostics point at their opener. A malformed character
escape is diagnosed before a secondary character-width consequence.

Add a code here when its first emitter is added, and remove it with its last
emitter. `tools/check-diagnostics` checks both directions, including the backend's
stable symbolic tags. Its lexical approximation scans source string literals
and ignores comments; computed or assembled code strings are forbidden.

Every source diagnostic has the form below. A tool's own refusal (a missing
input file, a bad flag) has no source position and is not in this form.

```text
FILE:LINE:COL: error[CODE]: MESSAGE (bytes START..END)
```

Lines and scalar columns are one-based. Byte intervals are half-open. A source
rejection and an I/O failure return 2, an F0001 refusal returns 4, and internal
failures use the driver's distinct status 70. There is no "unsupported means
success" outcome.

| code | condition | ownership |
|---|---|---|
| E0001 | leading-operator continuation begins a new statement | grammar |
| E0002 | empty explicit statement | grammar |
| E0003 | comparison operators chained without a logical connective | grammar |
| E0006 | unparenthesized struct literal in a condition | grammar |
| E0007 | friendly string/interpolation nesting limit of eight | grammar |
| E0008 | reserved keyword used as an identifier | grammar |
| E0101 | unknown or malformed escape, including Unicode escapes outside one to six hex digits | grammar |
| E0102 | unterminated string, raw/generalized string, interpolation or format | grammar |
| E0103 | multiline delimiter shares its content line | grammar |
| E0104 | multiline content is left of the closing margin | grammar |
| E0105 | multiline indentation differs byte-for-byte from the closing margin | grammar |
| E0106 | missing base-prefixed digit or exponent digit | front-end lexical shape code |
| E0107 | stray source character, unmatched literal closing brace, or invalid UTF-8 | grammar |
| E0108 | lexer string/format mode safety limit of 32 | grammar |
| E0110 | malformed character shape or non-scalar character value | grammar |
| E0200 | source I/O failure, changed source, or invalid emission mode | front-end input code |
| E0201 | other expected-token or grammar-shape failure, including an expression nested deeper than 256 levels (reported at the first token of the 257th, as the reference does) | grammar |
| E0202 | unclosed delimiter or inline C body | grammar and corpus |
| E0206 | a type position does not begin with a type | grammar |
| E0207 | missing or invalid pattern, including a binding-mode keyword in pattern position | corpus |
| E0210 | parenthesized moded receiver not followed by a member | grammar |
| E0211 | file-wide attribute after the initial attribute prefix | grammar |
| E0412 | malformed format-spec shape or non-byte fill | interpolation specification |
| E0822 | variadic marker does not end a fixed parameter list | C membrane specification |
| F0002 | syntax of any kind nests deeper than fenrir's recursion limit of 2048; status 4, a refusal | fenrir scope |

Retired grammar numbers are not reused. The nesting rail's former number is the
reference's code for a negative literal subscript, so the front end gave it up. Ownership, attribute applicability and
runtime checks are outside this catalog until implemented.
`tools/check-diagnostics` checks emitted string codes against this table in both
directions; no computed or assembled diagnostic codes are permitted.

## Resolution and typing

The checker (`docs/TYPED.md`) runs after a successful parse and reports in the
same source form. It runs its checks in a fixed order (the core scope check,
then resolution, then typing, one function at a time in source order) and stops
at the first diagnostic. Where the reference compiler reports the same program,
the code and location are the reference's; `tests/types/reference.py` runs the
reference over the typed rows and compares them.

| code | condition | ownership |
|---|---|---|
| E0301 | nothing in scope declares a name, a type or a struct-literal head; `==` or an ordering on a struct, which has no `Eq` or `Ord` in the core | resolution |
| E0302 | two module items, functions or structs, share a name | resolution |
| E0401 | a type mismatch: an argument, annotation, assignment, condition, branch or result against what its position expects, or a non-`()` tail in a unit context | typing |
| E0402 | a call's argument count differs from the callee's parameter count | typing |
| E0403 | a struct literal or field read names a field the struct does not declare | resolution and typing |
| E0408 | a struct literal misses a field or initializes one twice | resolution |
| E0409 | an operator applied to a type it is not defined on, including `str` joined with a non-`str` by `+` or `+=` | typing |
| E0410 | an assignment to a `let` binding or to a field of one | resolution |
| E0414 | `main` returns something other than `()`, `int`, `!()` or `!int`, or takes parameters | typing |
| E0415 | an integer literal outside its type, or outside `i32` when an unannotated binding is its only context | typing |
| E0801 | a `match` that some value of its scrutinee's type reaches with no unguarded arm; integer and `str` columns need a `_` or binder arm | coverage |
| E0802 | a warning, not an error: an arm whose every value the arms before it already match | coverage |
| E0808 | a pattern of the wrong shape: a variant that carries values written bare, a constructor pattern's payload count, a constructor pattern against a value that is no enum, or a range endpoint that is not an integer literal | typing |
| E0814 | a struct pattern that names a field twice, or misses a field without ending in `..` | typing |
| E0815 | an empty range pattern, such as `5..5` or `9..=3` | coverage |
| E1014 | an assignment to a parameter, which is `read` for the whole call | resolution |
| F0001 | not yet in fenrir: the named construct is outside the F1 core | fenrir scope |
| F0003 | not yet in fenrir: a build or run of a program with no `main` function | driver |
| F0004 | a function's pattern analysis exhausted its budget of 1,000,000 cells or 64 MiB of analysis storage | coverage |

### Lists, maps and error rows

These codes and their locations are the reference's, read from black-box runs
where the specification names no code (`tests/types/collection_rows.py`
re-checks them against the reference).

| code | condition | ownership |
|---|---|---|
| E0417 | a compound assignment through a map index, `m[k] op= v`: the entry may be absent (`[mem.map.absent]`); reported at the place | typing |
| E0418 | a `Map` key type other than `str`, `int` or `bool` (`char` waits for strings), at the key's spelling (`[type.map.key]`) | typing |
| E0601 | one row spells a tag twice | typing |
| E0602 | a `?` or a returned result can fail with a tag the function's row does not include | typing |
| E0603 | `?` on a value that cannot fail | typing |
| E0604 | `?` in a function whose result has no error row | typing |
| E0606 | a tag reaches a row whose tag of that name carries another payload | typing |
| E0608 | `else` on a value that cannot fail | typing |
| E0609 | a nested row's later layer spells an earlier tag with another payload (`[gram.type.row.flatten]`) | typing |
| E0610 | error-set aliases that name one another in a loop, at the entry of the alias that closes it (`[type.err.alias.cycle]`) | typing |
| E0804 | a list or map method that mutates its receiver (`push`, `pop`, `clear`, `remove`) called without `(mut …)` | typing |
| E0809 | an `else` handler whose pattern handles only some of its operand's tags | typing |
| E0816 | a `match` over a result whose row has a tag that is also a variant of the ok type (`[type.row.match]`) | typing |

The checker also uses existing codes for these constructs, as the reference
does: E0301 for a bare name no expected row declares as a tag, E0401 for a list
element or index of the wrong type, E0402 for a method's or a raise's argument
count, E0409 for an operator or member on a result (`[type.row.operand]`),
and E0801 for a `match` over a result that misses a tag or the value half.

F0001 is fenrir's own refusal, not a verdict about the program: the program is
outside what this compiler implements, so `--emit=typed` returns status 4
(`[conf.exit.refused]`), never 2. The message names the construct and the report
points at it.

E0802 is the one warning. It is reported in the same source form with
`warning` in place of `error`, only by a check that succeeds, and it never
changes the status by itself:

```text
FILE:LINE:COL: warning[E0802]: MESSAGE (bytes START..END)
```

F0004 is fenrir's refusal by budget, not a verdict about the program
(docs/COVERAGE.md): the status is 4, the message names the function, the
exhausted limit and both counters, and it points at the `match` where the
budget ran out. A budget refusal is never reported as E0801.

F0003 is the same kind of refusal from `build`, `run` and `--emit=fir|asm`: a
file with no `main` checks, but there is no executable to build around it, and
the reference refuses the same build with status 4. Its report points at the
file's first byte.

## Backend tags

FIR text carries no source span, so a backend report is not in the source form
above: it is one stderr line, `fenrir: TAG MESSAGE`, with the driver's prefix.
FIR input diagnostics return status 2. The same verifier's failure after an
internal transform or during emission returns 70: that is a compiler invariant
failure, not a source refusal. The backend has no verifier-disable switch.

| Tag | Meaning |
|---|---|
| `FIR_SYNTAX` | Invalid FIR tokens, encoding, counts or trailing input |
| `FIR_TYPE` | Invalid type, operand/result mismatch or inconsistent layout |
| `FIR_SITE` | Missing or invalid source coordinates |
| `FIR_LITERAL` | Invalid constant value or unknown literal blob |
| `FIR_ARITY` | Wrong instruction data/operand count |
| `FIR_OPCODE` | Unknown instruction |
| `FIR_DOMINANCE` | Use is not an earlier definition in this block |
| `FIR_SLOT` | Load or store names no stack slot of its function |
| `FIR_BRANCH` | Invalid branch destination or argument signature |
| `FIR_CALL` | Invalid function entry or call signature |
| `FIR_TERMINATOR` | Empty block, missing or misplaced terminator |
| `FIR_TRAP` | Unknown explicit trap kind |
| `FIR_LAYOUT` | Frame exceeds the supported displacement range |
| `FIR_LINK` | Link arguments, selected tools, output or staging failed |
| `FIR_LIMIT` | Invalid interpreter arguments or negative resource budget; status 2 |
| `FIR_IO` | Interpreter input or outcome-file I/O failure; status 2 |
| `FIR_STATE` | Invalid execution state, including a slot read before its first store |
| `FIR_INTERNAL` | Interpreter invariant failure after verification; status 70, never a refusal |
| `FIR_STEP_BUDGET` | Interpreter instruction budget exhausted; status 4, never a program trap |
| `FIR_MEMORY_BUDGET` | Interpreter byte budget exhausted; status 4, never a program trap |
