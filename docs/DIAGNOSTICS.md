# Diagnostics

The front end stops at the first source-ordered diagnostic. Lex and parse form
one rung: the earliest starting byte wins, with lex before parse at a tie.
Unclosed delimiter diagnostics point at their opener. A malformed character
escape is diagnosed before a secondary character-width consequence.

Add a code here when its first emitter is added, and remove it with its last
emitter. `tools/check-diagnostics` checks both directions, including the backend's
stable symbolic tags. Its lexical approximation scans source string literals
and ignores comments; computed or assembled code strings are forbidden.

Every report has the form:

```text
FILE:LINE:COL: error[CODE]: MESSAGE (bytes START..END)
```

Lines and scalar columns are one-based. Byte intervals are half-open. A source
refusal and an I/O failure return 2; internal failures use the driver's distinct
status 70. There is no "unsupported means success" outcome.

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
| E0201 | other expected-token or grammar-shape failure | grammar |
| E0202 | unclosed delimiter or inline C body | grammar and corpus |
| E0206 | a type position does not begin with a type | grammar |
| E0207 | missing or invalid pattern, including a binding-mode keyword in pattern position | corpus |
| E0209 | expression/statement/type/pattern recursion exceeds 256 | front-end nesting code |
| E0210 | parenthesized moded receiver not followed by a member | grammar |
| E0211 | file-wide attribute after the initial attribute prefix | grammar |
| E0412 | malformed format-spec shape or non-byte fill | interpolation specification |
| E0822 | variadic marker does not end a fixed parameter list | C membrane specification |

Retired grammar numbers are not reused. Resolution, typing, ownership, attribute
applicability and runtime checks are outside this catalog until implemented.
`tools/check-diagnostics` checks emitted string codes against this table in both
directions; no computed or assembled diagnostic codes are permitted.

## Backend tags

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
| `FIR_BRANCH` | Invalid branch destination or argument signature |
| `FIR_CALL` | Invalid function entry or call signature |
| `FIR_TERMINATOR` | Empty block, missing or misplaced terminator |
| `FIR_TRAP` | Unknown explicit trap kind |
| `FIR_LAYOUT` | Frame exceeds the supported displacement range |
| `FIR_LINK` | Link arguments, selected tools, output or staging failed |
