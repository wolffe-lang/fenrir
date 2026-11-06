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

   Exact coverage uses an incremental, memoized Boolean decision diagram with
   function-local state and an explicit worklist, not host recursion. Boolean
   products can encode DNF tautology, so the complexity statement is input plus
   explored analysis work, not unconditional input-linear time. The fixed
   per-function caps are 1,000,000 examined/emitted cells and 67,108,864 logical
   bytes. Exceeding either must give F0004/status 4 with the function, cap and
   consumed counters, never E0801 or assumed exhaustiveness. No corpus row
   receives a budget waiver; a native-decided but budget-refused row is a
   separate delta row, not one of the predicted 46.

   Compare a small adversarial input's exact counters on macOS and Linux.
   Drive cap exhaustion twice only on Linux, under a process memory cap.
   macOS never drives that row because its address-space limit is unavailable.
   Report the largest corpus and fixture functions against both caps, identify
   intentional stress rows, and flag ordinary real functions within ten times
   either cap before considering any increase.
6. Recompute the corpus delta against the census prediction, with every moved
   row listed. Stop on any differing observation. Finish with deterministic
   output, the complete local gates, and a one-hunk enum or match plant.

### Coverage kernel checkpoint

The interface preceded consumers at `1350a58`; the standalone API tests at
`d6437cf` failed by name because `coverage` did not exist. The kernel checkpoint
at `6fe2f38` passes the exhaustive Boolean algebra checks, fixed-size record
ownership, limits, witnesses, memo reuse and explicit-worklist rows. These are
bootstrap kernel tests, not yet source-pattern or corpus acceptance evidence.

The eight-pair adversarial DNF's output is byte-identical across macOS and
Linux and across two executions on each: **87,397 cells, 853,376 bytes**
(8.740% and 1.272% of the caps). The Linux-only 24-pair DNF refuses twice with
`Limit("cells", 929854, 6817152)`: 92.985% of the work cap and 10.158% of
storage. The next table growth would exceed the work cap; failed charges do
not advance the consumed counters. F0004 and its function-name boundary remain
producer-integration work, not a completed claim here.

The ordinary conjunction/worklist family at 10, 100, 1,000 and 10,000 variables
uses **840 / 12,161 / 111,607 / 983,100 cells**, and **6,896 / 116,416 / 940,768 /
8,205,344 bytes**. Each tenfold increase passes the 18-times work ceiling. The
10,000-variable stress row is the largest measured kernel fixture at **98.310%
of the work cap and 12.227% of storage**. It is explicitly flagged as near the
limits, not omitted from maxima; no limit was raised. Corpus-function maxima
and source-pattern fixture maxima are still pending producer integration.

### Enum and match typing checkpoint

Typing now implements the enum and match contract in TYPED.md; lowering does
not yet, so `build`, `run` and `--emit=fir|asm` refuse the first enum or
`match` by name (F0001, status 4) rather than reach the lowering as an
internal error. The census gained a `checked` class: rows inside the typed
extension that the lowering differential (which selects `core`) does not run
yet. Its gate requires status 0, as for `core`.

- **The census against the Prediction.** `checked` is exactly the nine rows
  the Prediction named, and `core` is still the same 37. Five oracle-refused
  `match` rows (`rows/match_range_empty`, `typecheck/match_arm_product_nonexhaustive`,
  `match_missing`, `match_str_nonexhaustive`, `pattern_shape`) refuse with the
  oracle's code (E0815, E0801, E0801, E0801, E0808) at the oracle's line and
  column. `memory/match_arm_whole_move` (E1001) and the interpreter-only
  `typecheck/enum_str_bare_choice` are accepted, as the accept-first rule
  expects before memory-model refusals exist.
- **Rows.** `tests/types/pattern_rows.py` holds 62 rows. Every code and
  location (and every E0802 warning's location) comes from a black-box run of
  the reference, and `--reference` re-checks them in `ci/check`. One native
  refusal after type checking (`nested-payload`, "a zero value of this type")
  counts as the reference having typed the row.
- **Deliberate differences** (rows marked `differs`, not compared). Each is a
  reference answer outside the language's rules or outside fenrir's scope, for
  the spec's owners to settle rather than for fenrir to copy. All are filed:
  wolf-lang#1058 (the wrapped literal), #1059 (E0410 through a nullary name),
  #1060 (a duplicated variant), #1061 (binding or-patterns) and #1062 (the
  spec silences: a name bound twice, recursive enums, binding mutability).
  - an or-pattern that binds names: both reference compiler machines refuse
    it after type checking and the reference interpreter runs it; fenrir
    refuses it by name (F0001);
  - one name bound twice in a pattern: the reference accepts it; F0001;
  - an assignment through a nullary pattern name to the outer `let` it did
    not shadow: the reference performs it; fenrir gives E0410;
  - an unused recursive enum: the reference accepts it; F0001 (no recursive
    by-value aggregates);
  - a duplicated variant name: the reference accepts it; E0302;
  - a literal pattern outside its type (`300` against `u8`): the reference
    accepts it, and its tiers disagree (native wraps it, so it matches 44;
    the checked machine and the interpreter never match it); F0001.
- **Binding mutability.** The spec states no rule, and the reference accepts
  assignment to a match binding, so a binding (declaration kind `bind`) is
  assignable. The earlier draft row expecting E0410 was the guess, not the
  reference: it is now `pattern-binding-assignable`.
- **Coverage producer.** Integer tests take every containing range's variable,
  found through a per-path sorted index with a max-high segment tree, so a
  switch's cost stays O((k + 1) log R) per test. Variable ids descend, so an
  arm on a fresh variable joins the earlier arms in constant work, and an arm is
  E0802 exactly when the union does not grow. A first version scanned every
  interval on the path for each test; the growth gate below exists to catch
  that class.
- **Growth and headroom** (`tests/types/analysis.py`, deterministic counters):
  at 40, 400 and 4,000 arms the five families grow 8.8x to 11.4x per tenfold
  (the ceiling is 18x). At 10,000 arms the range and enum families reach the
  cell cap (about 133 to 137 cells per arm), which is why the gate stops at
  4,000. Over 130 sources (every typed corpus row and pattern fixture), the
  largest function uses 534 cells (0.053% of the cap) and 5,546 bytes (0.008%);
  none is within ten times either cap. The source-level F0004 row (32 adversarial
  pairs) runs on Linux only, under a 2 GiB address-space limit.

Footprint: cross-cutting
