# Specify dynamic format width expressions in the grammar

At wolf-lang `5f1f1c94`, `spec/grammar.ebnf:18` gives `FORMAT_SPEC` a
`DIGIT*` width and an optional `'.' DIGIT+` precision. Neither part admits an
expression between braces.

`grammar/interp_fmtcolon.lu` contains `"{m["k"] else 8:>{w}}"` and reaches
`mem`. Its comment explicitly says that the width is interpolated. The
production cannot derive this accepted corpus spelling.

Please describe the dynamic width form explicitly, including its expression
extent, delimiter balancing, and permitted width/precision positions. State
whether precision admits the same form. Keep the first top-level colon rule
unchanged: nested indexing and nested strings in the value expression do not
start the format specification. `"{x:>{w}}"` should be a positive row and
`"{x:>{}}"` a negative one.
