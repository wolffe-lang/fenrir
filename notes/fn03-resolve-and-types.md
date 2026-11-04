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

Footprint: cross-cutting

## Forbidden

No reference compiler source was read. The specification and corpus come from a
sparse checkout of the pinned revision that holds only `spec/` and `corpus/`,
so no compiler crate was ever on disk. Stage 0 (wolf 0.2.36) and lupin are
used as black boxes: probes run under them and their codes and positions are
read from their records. No other compiler's type checker was consulted. There
is no lowering here (that is the lowering lane's), no optimizer, and no skip or
refusal counted as a pass. The plant branch has no PR, and branch pushes do not
run CI.

## Inputs verified

- Trunk `ce496a8`; pinned wolf 0.2.36 and lupin 0.1.58; specification and
  corpus at `5f1f1c94` (1,253 corpus files); `spec/prelude.json` by digest.
- Stage 0 probes, read as black boxes, fixed the facts the checker follows:
  - `{integer}` defaults to `i32`, with real `i32` overflow at run time; a
    literal-only initializer is fit-checked at `i32` (E0415) but typed by the
    binding's later use; `-2147483648` is one `i32` constant.
  - `print` takes exactly one `str`; a struct renders as `P { x: -1, s: hi }`.
  - The trap site is the start of the innermost enclosing statement or tail.
  - The codes: E0301 unresolved (and `==` on a struct, which needs `Eq`), E0302
    duplicate item, E0401, E0402, E0403, E0408 (missing or repeated field),
    E0409 (including `1 && true` and mixed `str +`), E0410, E0414, E0415, and
    E1014 for an assignment to a parameter.
  - Expressions nest 255 levels; the 256th is E0201 at the first token of the
    257th level. Else-if chains, types and patterns have no limit to 2,000.
- `docs/TYPED.md` was written first and pushed alone (`ab44f23`); every later
  change to it is listed in its change record and in "Interface changes" below.

Commits:
- `5503d5d`, `ab44f23`: the prediction, then the typed-tree interface.
- `c97ba21`: typed-tree rows, their runner and the reference check, red before the checker (169 of 169 failed on trunk).
- `a5d2f4e`, `d048ac8`: `src/sem/` integer kinds, literal magnitudes, fit and bit patterns; string escapes, multiline dedent, raw content.
- `9a5d943`, `7160d52`, `ed09939`, `a64fef5`: the generated prelude table, the hashed interner, the core scope check, declarations and resolution.
- `5a47911`, `2d86e21`, `64a929d`: interned types, integer inference and the checks; `--emit=typed`; the catalog.
- `e4f66be`, `b9f586e`, `990dfc5`: TYPED corrections from the implementation.
- `5a89568`, `1c3c38d`, `bcc1e23`: build status 4 is `fenrir-refuses`, red first, then the harness and the docs.
- `3539f37`, `87489db`: module-formation rows, red first, then the refusal of a program of several files.
- `de8feef`, `31ac7d1`, `804f4d6`: the census tool, its table, and its gate's failure rows.
- `b8e220c`, `bb027a0`: rows for every remaining anchor; the coverage gate.
- `910f5ea`, `8913291`, `d36ea4b`, `8c0e85c`, `9332e72`, `36d8e0b`: the nesting follow-on, red first at E0209.
- `3fc61da`, `feaa0b6`, `f409eb5`, `4477819`, `de5e5f3`: SUBSET counts, stress and determinism rows, the CI steps, the README.

Interface changes after `ab44f23`, for the lowering:
- `e4f66be`: `Decl.type` is `Decl.ty` (`type` is a keyword) and `Decl` lives in
  `resolve`; a negative literal is one constant on both its nodes; a callee's
  `Name` has no type; diagnostics come from checks in a fixed order.
- `b9f586e`: the core is one file; a file with member siblings is refused.
- `990dfc5`: the nesting rail's F0002 is status 4 in the typed view too.

## Evidence index

The gauntlet records, with every `END` line, and the plant record are in the
PR body; they were made at the final head, which this note is part of.

- [x] Typed rows (`tests/types/rows.py`): 178 rows, each run twice and
  byte-identical, each typed table checked against the AST (ids, interning,
  source-order declarations, contiguous members, every body expression typed,
  every name resolved, sites). 30 anchors in scope own a positive and a refusal
  row; 70 outside the core own an F0001 row. The coverage gate compares both
  key sets with the pinned registry and rejects the deletion of any positive.
- [x] The reference over the rows (`tests/types/reference.py`): stage 0 reports
  every reference-pinned row's code at its line and column, and accepts every
  positive row.
- [x] The census (`tests/types/census.json`, `tools/census check`): 37 core,
  17 oracle-refused, 1,160 out-of-core, 39 syntax-refused of 1,253. Every core
  row types; 16 of the 17 oracle-refused rows are refused with the oracle's code
  at its location, and one (`test/assert_test.lu`, which the reference cannot
  build) is the F6 count of accepting what the oracle refuses. 1,139 out-of-core
  rows are F0001; module members alone in a subdirectory type as one-file
  programs, as the named-entry rule makes them. The independent classifier
  and the checker name the same construct at the same place on 1,014 of the
  1,017 rows both classify by node. No row crashes.
- [x] Determinism: all 1,253 corpus files typed twice, byte-identical.
- [x] Scaling and fuzz (`tests/types/stress.py`, Linux, 1 GiB address-space
  cap): N/10N/100N over many items and one long body, 100N above ten times the
  largest real input, each tenfold step within 16x; 600 mutated and generated
  programs never crash. A development smoke on the Mac (small sizes, no cap)
  measured 10x items at 6.4x time and 180 cases with no crash; the recorded run
  is CI's Linux job.
- [x] The nesting follow-on: 10 front rows red at E0209 first (`910f5ea`), then
  green at the reference's limits; the Linux stress rails updated to match.
- [x] Harness: build status 4 is `fenrir-refuses`, red first (`5a89568`).
- [x] Gates seen red: the typed rows on trunk (169 of 169), the module rows
  (`module-member-sibling`), the nesting rows (10), the status-4 row, the
  census gate's eight failure conditions, and the coverage gate's deletions.
- [x] Strict skips: zero.
- [ ] CI on this head (ci on ubuntu-24.04 and macos-15, backend).

Test targets:
- [x] macOS arm64: `bash ci/check --oracle` under the gauntlet record, every step `exit=0`.
- [x] The plant `fn03-plant-int-plus-str`, red by name.
- [ ] Linux x86-64: CI's `ci/check --oracle`, including `types-capped-stress` and `front-capped-stress`.

## Done-when

Name resolution and the type checker for the F1 core, `docs/TYPED.md` (written
first), `--emit=typed`, the F0001 refusal outside the core, the computed census
with its committed table, freshness check and gate, the type errors inside the
core with the reference's codes, the E0201 nesting follow-on and the scoped
report-form sentence are implemented and green at the head on macOS arm64, with
the plant red by name. CI on Linux and macOS is the merge check for this
cross-cutting change. Nothing is merged, labelled, tagged or closed here.

Rulings, all four accepted:
- **R-fn03-1, sized integers:** the checker types `i32`, `i64`, `u8`, `u64` and
  `uint`, the five a core row names (`i32` is also the literal default); their
  lowering and FIR's growth for them are the lowering lane's.
- **R-fn03-2, the refusal status:** F0001 returns 4, as `[conf.exit.refused]`
  says; the harness reads a build status of 4 as `fenrir-refuses`.
- **R-fn03-3, census classes:** syntax-refused, then out-of-core (modules
  included), then oracle-refused, then core; the core class is "the core corpus
  rows", and the oracle-refused class carries the F6 count.
- **R-fn03-4, the core prelude:** `print` and `assert`.
