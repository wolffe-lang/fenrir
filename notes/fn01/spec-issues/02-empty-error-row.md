# Admit empty error rows in the extracted grammar

At wolf-lang `5f1f1c94`, `spec/grammar.ebnf:208` defines `error_row` with a
mandatory initial `row_entry`. The production cannot derive `{}`.

`rows/eu_bind_empty_row_unit.lu` and `typecheck/main_unit_row.lu` use empty
rows and reach stages beyond parsing. An empty declared row is useful in its
own right: it states that a return type has no error alternatives.

Please admit an empty row body explicitly and describe its meaning. Keep the
rules for the open marker separate, so admitting `{}` does not accidentally
admit arbitrary comma-only rows. A minimal positive example is
`fn f() -> () ! {} {}`; `! {,}` should remain invalid.
