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
3. The predictive census at `3107fe9`, before interpreter or enum code,
   predicts **9 new native `same` run rows**, taking the existing 37 to **46**.
   `tools/census predict` reads every pinned corpus AST and extends the existing
   independent F1 scope classifier only with non-generic enums and `match`
   patterns over F1 values. Two complete runs produced byte-identical tables;
   [the frozen prediction](../tests/types/fn05-prediction.json) records all
   1,253 files, their source digests, blockers and oracle outcomes. Predicted
   gains are:
   - `corpus/lints/binder_capitalized.lu`
   - `corpus/lints/match_str_arm_unreachable.lu`
   - `corpus/strings/match_str_const_scrutinee.lu`
   - `corpus/strings/match_str_dispatch.lu`
   - `corpus/typecheck/match_arm_product_unreachable.lu`
   - `corpus/typecheck/match_chain_reuse.lu`
   - `corpus/typecheck/match_guard_const.lu`
   - `corpus/typecheck/match_unreachable.lu`
   - `corpus/typecheck/numlit_radix.lu`

   The interpreter parity set is the same **46** rows: 37 already lowering
   today and these 9 after the extension. An interpreter does not remove a
   source-language blocker, so it adds **0 further native-comparable rows**.
   There is **1 additional reference-interpreter-only run row** inside the
   proposed source scope: `corpus/typecheck/enum_str_bare_choice.lu`. The pinned
   native oracle refuses its unused string payload's zero value; lupin runs it.
   Check it separately against lupin, never count it as native `same` and never
   silently replace its native oracle. No corpus execution is claimed by this
   prediction.

   The split stays unchanged. The small immediate delta is explained by real
   prerequisites: the grammar directory's module-member siblings put its match
   rows outside the one-file core; other enum rows also need lists, modes,
   error rows or floats. Those blockers remain explicit rather than broadening
   this lane. Enum and union-payload coverage therefore also needs fixtures,
   including nested enum/struct patterns and a str/int payload union. A reliable
   fn06-alone or combined unlock count is not cheap from this classifier: it
   stops at the next blocker and does not model list/Map methods or error-row
   scope, so no comparative reach claim is made.
4. Implement a step- and byte-bounded FIR interpreter before extending
   lowering. Exhaustion is a named refusal, never a trap. Compare every
   existing FIR fixture and core corpus row against native execution.

   The interpreter's CPU gate grows input, not just a loop's step budget:
   one dependent arithmetic chain and a chain through distinct functions, at
   N=1,000, 10N and 100N. Each must print N, exit 0, and refuse if given one
   instruction fewer than its exact execution count. Five interleaved rounds
   use the direct child's user+system CPU time, the minimum per point, a
   0.005-second timer floor, and an 18x ceiling for each tenfold input increase.
   The largest input must exceed ten times the largest real source or executable
   FIR fixture. Independent 2 GiB address-space, 30-second CPU and 90-second
   wall limits keep a broken measurement bounded. The expected green is linear
   growth in parsing, verification, layout and execution. The off-line plant
   redundantly scans every 128th instruction site on every step: unchanged
   answers, but quadratic work, which the same gate must reject by name.
   The first 50 ms floor caught the call-shaped plant but masked the arithmetic
   chain's roughly 16 ms to 780 ms increase. A regression row now rejects that
   case; the floor is 5 ms, with the input sizes, five-round minimum and 18x
   ceiling unchanged. Both planted shapes must fail under the tighter floor.
5. Extend resolution, typing and exhaustiveness, lowering, interpretation and
   x86-64 execution for enums and `match`, with failing rows committed first.
   Preserve evaluation order and trap sites; add no optimizer.
6. Recompute the corpus delta against the census prediction, with every moved
   row listed. Stop on any differing observation. Finish with deterministic
   output, the complete local gates, and a one-hunk enum or match plant.

Footprint: cross-cutting
