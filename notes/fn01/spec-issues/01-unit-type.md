# Document the empty tuple spelling for the unit type

At wolf-lang `5f1f1c94`, `spec/grammar.ebnf:201` defines the parenthesized
`type` alternative as `'(' type (',' type)* ','? ')'`. Its first `type` is
mandatory, so it cannot derive `()`.

The corpus uses `()` as a type in `memory/region_unit_tail_call.lu`,
`rows/unit_discard_unit_main.lu`, and `typecheck/main_unit_row.lu`. These rows
reach stages beyond parsing.

Please extend the production to admit the empty parenthesized form, and state
that it is the unit type. Preserve the grouping/one-tuple distinction for the
nonempty forms. A minimal positive example is `fn f() -> () {}`; `(,)` should
remain invalid.
