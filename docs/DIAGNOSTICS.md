# Diagnostics

The catalog is empty: there are no numbered diagnostics yet. The initial
frame reports an unnumbered refusal, not a syntax or type error.

Add a code here when source first emits it, and remove it when its last emitter
is removed. `tools/check-diagnostics` checks both directions. Its temporary
lexical approximation scans diagnostic-looking codes in source string literals
and ignores comments; computed or assembled code strings are forbidden until
an explicit emission API and AST-based gate replace it. A string containing a
code is conservatively treated as an emitter, even in unreachable code.

See [the driver contract](DRIVER.md) for status codes.
