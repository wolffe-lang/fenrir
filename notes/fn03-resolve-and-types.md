## Prediction

Written before the first change.

- **Resolution.** Declaring every binding in one source-order walk, then
  resolving every use in a second walk with hashed scope tables and an undo log
  per block, resolves each name in the F1 core to exactly one declaration in
  O(nodes). Unresolved names are E0301 and duplicate module items E0302, as the
  reference reports them; a later `let` shadows, an inner block's binding ends
  with its block, and a module item hides the prelude entry of the same name.
- **Types.** Union-find inference over integer-kind variables, defaulted to
  `i32` once at the end of each function body, types the core in
  O(nodes · α(nodes)): checked arithmetic on `int` and `i32` (and the five
  other sized types the core rows name), `bool`, comparison, the logical
  operators, `str` concatenation and interpolation, unit, functions,
  recursion, `let`/`var`/assignment, `if`/`else`, `while` and structs by value.
  Mismatches use the reference's codes (E0401, E0402, E0403, E0408, E0409,
  E0410, E0414, E0415).
- **Outside the core** every construct is refused by name with one fenrir code
  and the specification's refusal status 4, never a crash and never an accept.
- **Census.** Of the 1,253 corpus files, 55 to 75 are core once module members
  and multi-file modules are counted out; every core row the oracle accepts
  types with no refusal, and the oracle's refusals inside the core are mostly
  refused with the same code. No row crashes.
- **Scale and determinism.** N/10N/100N inputs grow linearly (each tenfold step
  within 12x time); two `--emit=typed` runs are byte-identical.
- **Nesting follow-on.** The reference reports nesting past 256 as E0201 at the
  257th opener, so the front end's E0209 moves to E0201 there, red first.
- **The plant.** A checker that accepts `int + str` is red by name.
