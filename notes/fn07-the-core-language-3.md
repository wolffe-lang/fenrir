## Prediction

Start from trunk `20ba4b8a26c2f221ca34a8de0e2dece7ee8ee2e7`.
The preceding change records 133 `same` core rows of 780 run rows.
Remeasure that exact base, natively and with the bounded FIR interpreter,
before changing an input.

### Reference update

Generate a targeted update to wolf 0.2.39, lupin 0.1.61 and the specification
and corpus at the wolf release's immutable source commit. Update the musl
runtime with wolf. Preserve the assembler, linker and licensed link bundle
pins. Check every downloaded archive twice, against the release digest where
one is published. Test the generator with sealed, mocked inputs before
implementing the new targeted operation.

The prediction for the existing 133 core rows is no loss and no differing
answer. Additional source rows and changed oracle outcomes are recorded
separately; none is counted as new compiler capability. Capture the new
oracles twice, recompute the census, then compare the unchanged compiler
against the new native reference, natively and through the interpreter.
List every row whose membership, classification or answer moves. Stop on an
unexplained regression instead of updating a golden to conceal it.

### Language work after the reference update

Before changing the compiler, commit the new corpus's per-row feature census
and an exact Prediction for strings, enum rendering and traps, independently
and together. Rank the remaining blockers to half of the run rows. The old
needs walker describes an earlier core; update its scope model and test it
against the current census before trusting its reach counts. Unknown receiver
types remain blockers, never optimistic predictions.

Implement the chosen rows through typing, lowering, verified FIR, bounded
interpretation and x86-64, with failing rows committed before their fixes.
Retain source sites and evaluation order, add no optimizer, and leave memory
ownership and generics to their respective milestones. Check the new pattern
and error-alias clauses with their own rows; a fixed reference divergence is
not a reason to discard its regression test.
