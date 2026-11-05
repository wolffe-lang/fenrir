## Prediction

Implementation plan, before the first change; base `bfb12e0`.

1. Move only the ligature pin to `6cec81a` using the pin generator. A direct
   child measurement of the hello link under a 2 GiB address-space cap should
   fail at the old `c8ca1be4` pin and succeed at the new pin. Measure the linker's
   own peak resident and virtual memory, not the Python runner's memory. Keep
   the 16 MiB starvation control. Lower the backend link budget to 2 GiB after
   committing and running the new regression row.
2. Preserve the diagnostic fixes already in this base rather than repeat them.
   `89132914636bd70d246343aa81d77955fede90dd` moved expression-depth errors
   from E0209 to E0201; `tests/front/rows.json` has
   `nesting-parentheses-256`, `nesting-parentheses-2000` and
   `nesting-prefix-256`, with accepted-boundary and syntax-rail companions.
   `9332e72451b4867d70ddabc661f560655572b71e` scoped the diagnostic format to
   source diagnostics in AST.md and DIAGNOSTICS.md. Re-run the existing driver
   and front rows. The negative literal subscript's E0209 remains a black-box
   reference check, not a claim that the F1 checker supports indexing.
3. Before interpreter or enum implementation, extend the census to count
   exactly which run rows need only the core plus enums and `match`; record
   the numeric prediction before changing those compiler stages.
4. Implement a step- and byte-bounded FIR interpreter before extending
   lowering. Exhaustion is a named refusal, never a trap. Compare every
   existing FIR fixture and core corpus row against native execution.
5. Extend resolution, typing and exhaustiveness, lowering, interpretation and
   x86-64 execution for enums and `match`, with failing rows committed first.
   Preserve evaluation order and trap sites; add no optimizer.
6. Recompute the corpus delta against the census prediction, with every moved
   row listed. Stop on any differing observation. Finish with deterministic
   output, the complete local gates, and a one-hunk enum or match plant.

Footprint: cross-cutting
