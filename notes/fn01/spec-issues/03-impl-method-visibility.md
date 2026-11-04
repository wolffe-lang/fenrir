# Include method visibility in the impl member grammar

At wolf-lang `5f1f1c94`, `spec/grammar.ebnf:81` defines
`impl_member ::= fn_item | type_item | const_item`. `fn_item` at line 49 begins
with function qualifiers and `fn`, and has no visibility prefix.

`typecheck/variant_value/paint/p.lu` contains `pub fn` methods inside an impl
and is consumed as a module member by an entry that parses successfully.
The extracted production does not derive that spelling.

Please make the visibility prefix explicit in `impl_member`, or route impl
methods through a production that already owns it. State whether the same
prefix applies to associated types and constants and whether trait members
have a different rule. Admitting visibility must not admit ordinary `let`
bindings as impl members.
