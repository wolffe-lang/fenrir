# Front-end implementation plan

The source of truth is wolf-lang's published grammar and corpus at the pinned specification revision. The reference compiler is a black-box build tool, not an implementation reference.

## Predictions and order

1. Commit executable positive and negative lexical and grammar rows before implementing their features. Initially the runner must fail because the front-end executable is absent.
2. Implement a single-pass byte lexer with explicit UTF-8 scalar validation, source coordinates, string/interpolation nesting, and delimiter-sensitive newline termination. Malformed escapes must name their specification codes at the offending escape.
3. Implement recursive descent for declarations, types, patterns and control flow, with precedence climbing for expressions. Every recursive grammar entry checks a nesting rail. First-error refusal has status 2; internal failures use status 70.
4. Store syntax in an append-only arena with linked child edges. Indexing and linking are amortised constant time; neither parsing nor emission reconstructs an entire subtree per token. Text emission follows source/arena order, never hash iteration.
5. Compare the entire pinned corpus against its syntax-phase expectations, parse the front end itself, check byte-identical emission twice, exercise bounded random token streams, and measure N/10N/100N scaling. Unimplemented or discrepant rows are failures, not skips.
6. Document the AST contract, source subset, diagnostics, and any specification disagreements. Integrate with the common driver after the repository frame lands.

The expected lexer/parser time is O(source bytes + nodes), excluding bounded nesting and fixed Unicode-range table lookups. Storage is O(source bytes + tokens + nodes). Tests must expose accidental repeated string materialization and list copying.
