# Pin the Unicode release used by identifier properties

At wolf-lang `5f1f1c94`, `spec/grammar.ebnf:5` defines identifiers through
`XID_Start` and `XID_Continue`, but neither that production nor
`spec/01-grammar.md` selects a Unicode release. Using a host's Unicode database
therefore makes acceptance depend on the host's installed database version.

The reference compiler accepts each of these isolated programs through
its native build command, with status 0, using release 0.2.36:

| first XID_Start release | code point | program |
|---|---|---|
| 15.0 | U+1123F | `fn main() -> int { let 𑈿 = 0; 𑈿 }` |
| 15.1 | U+2EBF0 | `fn main() -> int { let 𮯰 = 0; 𮯰 }` |
| 16.0 | U+1C89 | `fn main() -> int { let Ᲊ = 0; Ᲊ }` |
| 17.0 | U+088F | `fn main() -> int { let ࢏ = 0; ࢏ }` |

The probes use standalone entries so directory-module name collisions cannot
be mistaken for lexical rejection. All four published release boundaries are
accepted; no later published release supplies a rejected-release example.
U+0378, an unassigned scalar, supplies a negative identifier example.

Please select a Unicode release explicitly, preferably with a digest-pinned
`DerivedCoreProperties.txt`, and require deterministic generated ranges for
both properties. Unicode 17.0.0's file has SHA-256
`24c7fed1195c482faaefd5c1e7eb821c5ee1fb6de07ecdbaa64b56a99da22c08`.
