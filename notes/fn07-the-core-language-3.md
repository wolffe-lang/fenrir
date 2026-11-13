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

### Measured pin-only result

The unchanged base reproduces **133 `same` of 780 run rows**, natively and
through the bounded interpreter. The wolf 0.2.39 source pin is
`3fc86f77795afbbd6fbe483fef76c08e7f13a840`; its corpus has 1,353 files and
**813 run rows**. Two complete oracle captures reconcile and pass freshness.
At the new pin the unchanged compiler gives **142 `same`, four refusals,
zero differences and zero crashes** among 146 selected core candidates. All
133 previous passing rows remain passing. The new-pin interpreter take did
not run after the native red; no interpreter parity is claimed at that pin.

[The pin-only ledger](../tests/types/fn07-pin-delta.json) names all 100 added
sources, every changed census class, all 22 changed pre-existing native
observations, the nine additional passing rows and the four refusals. The
changes are explained by the intervening release notes; the four already
unstable race/UB rows are not attributed to the pin. The four refusals expose
row-tag resolution, tuple match patterns and enum rendering, rather than a
regression in a previously passing row. The 14 census gate failures remain
failures, including the newly specified diagnostic numbers.

### Frozen language Prediction

[The per-row projection](../tests/types/fn07-needs.json), committed before any
compiler change, records every source hash and the oracle, census, native
verdict and parser-observation input digests. Its 142-row baseline comes from
execution, not from the classifier's optimistic 146-row core. The small local
type model retains its raw inventory on measured rows. On unmeasured rows,
unknown receivers and unmodelled constructs remain blockers. Two complete
projection runs are byte-identical. These are predicted gains, not measured
coverage.

| Added capability | Additional `same` predicted | Total predicted |
|---|---:|---:|
| strings alone | 32 | 174 |
| enum/map rendering alone | 1 | 143 |
| traps alone | 0 | 142 |
| strings and rendering | 33 | 175 |
| strings and traps | 32 | 174 |
| rendering and traps | 1 | 143 |
| all three | 33 | **175** |

The 32 strings rows are:

- `corpus/faults/bounds_slice.lu`
- `corpus/faults/byte_view_slice_reversed.lu`
- `corpus/faults/list_slice_oob.lu`
- `corpus/faults/list_slice_reversed.lu`
- `corpus/faults/repeat_negative.lu`
- `corpus/lints/else_arithmetic.lu`
- `corpus/memory/ctl_slice_endpoints_str.lu`
- `corpus/memory/map_char_bool_keys.lu`
- `corpus/memory/map_count.lu`
- `corpus/memory/map_remove.lu`
- `corpus/projects/wordtree.lu`
- `corpus/rows/else_fallback_bound_slice.lu`
- `corpus/rows/else_fallback_paren_slice.lu`
- `corpus/rows/else_tag_payload.lu`
- `corpus/rows/match_row_payload_tag.lu`
- `corpus/rows/row_member_handled.lu`
- `corpus/rows/row_union_payloads.lu`
- `corpus/rows/to_int_parse.lu`
- `corpus/strings/char_order.lu`
- `corpus/strings/concat_mix_char.lu`
- `corpus/strings/concat_plus.lu`
- `corpus/strings/empty_needle.lu`
- `corpus/strings/equality_lanes.lu`
- `corpus/strings/format_spec_full.lu`
- `corpus/strings/format_spec_width.lu`
- `corpus/strings/slice_oob_trap.lu`
- `corpus/strings/split_clause.lu`
- `corpus/strings/str_uni_leading_zeros.lu`
- `corpus/strings/to_int.lu`
- `corpus/typecheck/enum_union_three.lu`
- `corpus/typecheck/straight_line_str_eq.lu`
- `corpus/typecheck/straight_line_str_order.lu`

The rendering gain is `corpus/typecheck/enum_str_bare_choice.lu`. No separate
native map-rendering row is unlocked by rendering alone; fixture coverage is
still required for maps and nested values. Zero independent trap gains does
not waive the trap catalogue, report-stream, status or source-site checks.
The string gains themselves include bounds and negative-repeat traps.

Among these 32 rows, length occurs in 11, slices in eight, `to_int` in four,
and `chars`, character literals, format specs and `lines` in three each.
`bytes`, `repeat`, `words`, `find`, `starts_with`, `count` and `split` occur in
two each; `replace` occurs in one. Implement most-used operations first.
Literal decoding, concatenation, equality and ordering already have baseline
coverage and must not regress.

The byte/scalar distinction is the specification's, not a choice here:
`[mem.str.get]` defines slices over "every pair of `int` byte offsets" and
returns `none` for an offset that "splits a UTF-8 code point";
`[mem.str.chars]` states that `s.chars().len` is the code-point count and
"`s.len` the byte count". Checked slices retain the corresponding `bounds`
trap. Rendering uses `[type.interp.value]` and `[type.interp.agg]`: strings in
composites are unquoted, and an enum variant is qualified by its enum name.

### The remainder and the existing completion bar

Half of 813 run rows is **407**. The three planned capability groups predict
175, **232 short**. The frozen table lists every remaining row and every
missing feature, ranked largest first. The leading blocker occurrences are
not independent gains, since one row may need several:

| Missing feature | Remaining native-executable rows |
|---|---:|
| unresolved rendering type | 140 |
| casts | 127 |
| mutable argument modes | 85 |
| mutable parameter modes | 85 |
| unresolved name/type model | 73 |
| unresolved index receiver | 71 |
| regions | 67 |
| unsafe expressions | 56 |
| a module of several files | 56 |
| C imports | 46 |
| unresolved `free` receiver | 46 |
| unresolved length receiver | 40 |
| generic application | 39 |
| unresolved `calloc` receiver | 39 |
| closures | 36 |
| explicit `copy` | 36 |
| module imports | 33 |
| impls | 32 |

There is also a deliberately optimistic upper bound. Of the 813 run rows,
794 have a native reference execution. Among those, 176 explicitly require
memory-model constructs assigned to F3, 170 explicitly require modules,
generics, traits, impls or closures assigned to F4, and 67 explicitly call
`fs_*`, `os_*` or `env_*` host entries assigned to F7. These sets overlap;
their union is **391 rows**. The table names each row and its barrier.

Even granting every other feature for free, and resolving every unknown or
ambiguous construct in F2's favor, the native-comparable F2 ceiling is
**794 - 391 = 403**, below 407. The bound deliberately does not exclude casts,
unknowns, arbitrary generic applications or unsafe expressions merely by
analogy. These measurements preceded language implementation.

The milestone is measured by parity over its own language: its language must
be built, and every run row the census places inside that language must be
`same`, with the string, rendering, trap and specified-pattern obligations
met. The 50% target carries forward to a milestone whose features can reach
it; no memory-model, generic/module or host-surface feature is brought into
this work to satisfy the old percentage. The measured ceiling remains 403 of
813 rows against the former target of 407.

### Text implementation checkpoints

At `1c78cb9`, a limited Linux checkpoint passes the 32 FIR string checks on
both machines, five byte-view structural checks, 15 source typing/reference
rows and 13 source executions on both machines. Direct byte length, indexing
and iteration keep the string view; binding bytes and obtaining scalar lists
materialize canonical word elements. Native scalar-list adaptation uses the
public four-byte char cells through `list_read`, never a private header.

At `f0404bb`, the development checkpoint additionally passes 11 primitive-format
typing/reference rows, seven interpreter formatting programs, five extended
string-range typing/reference rows and their source executions. The format
plan is parsed once, and integer output preserves signedness at both 64-bit
extremes. Open, inclusive and end-relative string slices normalize without
arithmetic overflow; recoverable `get` returns `none` for invalid extreme
offsets. All 32 frozen string Prediction sources now emit verified FIR.
These are lowering and fixture results, not 32 measured coverage gains.
At `022eb89`, the Linux take also passes all 32 FIR checks on both machines,
19 positive source executions on both machines, and all seven format programs
natively and in the interpreter. Its catalogue gate exposed the missing E0413
entry, and its two Prediction steps stopped before executing rows because of
missing isolated-job setup. Both issues have red-first corrections. The
32-row native/interpreter Prediction retake at `acf7c3e` passes: **32 `same`,
zero refusals, zero differences and zero crashes on each machine**. Its bounded
interpreter record contains 32 fresh successful lowerings and 32 outcome records
(25 exit 0, one exit 1, five bounds traps and one assert trap). The previously
measured 142-row baseline still needs an exact-head regression retake, so no
new whole-corpus coverage total is asserted here. The final corpus tables and
exact-head full gates have not yet been refreshed.

### Views, rendering and trap checkpoints

The Linux checkpoint at `b95dba6` passes all 32 frozen string Prediction rows
natively and in the bounded interpreter, including the split row that had
exceeded the assembler's unchanged 2 GiB address-space cap. One shared,
nonallocating scalar-space leaf and compact byte directives replace the
expanded decoder and one-directive-per-byte output. No link budget changed.
Nine direct split/words/lines execution cases preserve empty fields, all 25
frozen whitespace scalars, UTF-8 widths, receiver/separator evaluation order,
`break` and `continue`, without materializing a runtime list.

The same checkpoint passes 26 finite source trap/control cases against native
wolf: exact stdout, stderr, status and statement site, plus matching bounded
FIR outcomes. The controls prove that absent Map keys, empty-list `pop` and
invalid recoverable string `get` yield rows rather than traps. The catalogue
names all 14 released trap kinds; nine require later language features.
`stack-overflow` is a separate host-resource case: native exhaustion is a
runtime trap with a best-effort site, while bounded interpretation exhausts a
tool budget. An explicit recursive source witness is retained for that
separate check. Native wolf on macOS reports `stack-overflow`, status 134,
on stderr after the preceding stdout; bounded FIR answers the distinct
`FIR_STEP_BUDGET` refusal. The Linux x86-64 result is still pending.

Ordinary enum variants, nested aggregates and error values match native output.
A unit-typed enum payload is deliberately separate: native wolf refuses it,
while checked wolf, lupin and fenrir run it. It is candidate-only coverage,
not `same`; the reference issue is titled “native tier refuses a unit-typed
enum payload that checked and lupin run”. Direct and struct/list/tuple Map
interpolations retain named refusals at the outer value, with `pairs()` advice.
Their verdict is `fenrir-refuses`, never fabricated rendering parity.

### Pattern and declared-row checkpoint

The committed `66d18ad` Mac checkpoint passes all 30 released-rule typing
rows, nine binding-alternative typing rows, the inherited pattern regressions,
and 15 declared-row context cases against native wolf. The last group includes
`tag_known_cannot_fail.lu`'s E0604 at 20:16 and controls for late annotations,
local shadowing, payload tags and tags mentioned only in another function.
All eight binding-alternative programs execute correctly in the bounded
interpreter. Six native reference refusals are matched by exact construct
name and labelled candidate-only; the two mixed binder/constructor-test rows
execute under the native reference as well.

The generated prelude now matches the released `prelude.json`; two complete
released oracle captures are reconciled, retaining their four changing rows.
The live classifier is separate from the frozen prediction model: its 39 unit
tests and the complete 1,353-file typing census gate pass, with **180 core run
rows**. Unknown receivers remain blockers. This is a typing extent, not 180
measured successes. The refreshed native/interpreter corpus tables and full
exact-head gates remain pending.

The rendering plant `aa390a3` removes enum qualification in one file and one
hunk, on its separate plant branch. The committed Mac check fails by name at
`render-enum-variants`, `render-nested-enums` and `render-enum-result-row`;
the unmodified `17c6be8` check passes these same rows. The plant branch was
pushed without a pull request, and the immediate CI listing contained no run.

The complete Mac `ci/check --oracle` checkpoint at `aebebcc` is green:
[all 60 END lines](fn07/evidence/mac-aebebcc.log) have exit 0, with the
[head, command and digest](fn07/evidence/mac-aebebcc.json) recorded alongside.
It includes 1,353 corpus files and 67 compiler-source parser cases, 468 grammar
ownership rows, 215 typed rows and their reference checks, 90 grammar anchors,
104 typed anchors, all new source suites, determinism and oracle freshness.
This is a complete Mac checkpoint, not the pending Linux native-output proof.

### Released-tier questions and the original core retake

At `ab4f364`, all **146 original core rows are `same` on both engines**, with
zero refusals, differences or crashes: [native](fn07/evidence/core-ab4f364-native.json)
and [bounded interpreter](fn07/evidence/core-ab4f364-interpreter.json). This
restores all four pin-only refusals. The [13-step development record summary](fn07/evidence/rules-ab4f364.json)
retains its one red step instead of hiding it: the Map harness incorrectly
required every tier to refuse every case at resolve. Its header also names a
bundle origin, so this is development evidence, not the final audit record.

[wolf-lang#1110](https://github.com/wolffe-lang/wolf-lang/issues/1110) tracks
the four Map cases. Native refuses the direct hole at resolve and nested
struct/list/tuple holes at mem, all at the outer expression. Checked wolf
refuses the direct hole but prints `<value>` inside the three composites;
lupin renders each Map. The corrected harness pins all twelve tier-specific
observations, including exact output bytes and hashes or refusal phase,
construct, span and site. Mutation tests reject drift. The candidate still
answers its named refusal and is never credited as `same` for these rows.

[wolf-lang#1109](https://github.com/wolffe-lang/wolf-lang/issues/1109) remains
parked: the specification illustrates `W((A(x) | B(x)))`, native and checked
report E0801 then E0808, lupin refuses because no arm applies, and fenrir keeps
E0401 at 3:37. The [named open row and recorded answers](../tests/types/parenthesized-or-open.json)
have zero parity credit. No grouping rule, parser behavior or diagnostic
precedence has been changed; the unparenthesized joined-binding fixture remains
separately proven. The final 180-row retake and qualified full Linux gate are
still pending.
