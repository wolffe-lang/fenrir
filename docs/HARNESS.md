# Differential harness

## Commands

`tools/differ oracle --output FILE` records the pinned Rust wolf's native
`wolf run --no-cache -o PRIVATE_OUTPUT FILE` (native by default; `run --native`
is invalid in this release). The flags must precede FILE: otherwise they become
program arguments. The default output is inside the package's `.lu-cache/bin`,
which a read-only input correctly refuses; disabling caches and naming a private
output avoids that write. Lupin uses `conform-run --json`, once per corpus entry.
Exact argv is retained
in native observations. Every non-member also gets a `declared_phase` pair via
`conform-run --phase=PHASE` on both implementations; memory rows use their
explicit `mem` phase, never an inferred typecheck stop. Static rows compare this
pair. Run-header rows compare the raw native result against lupin's dynamic
record, with declared-phase observations retained separately.
The oracle recorder runs only on Linux x86-64 inside an isolated container;
set `FENRIR_ORACLE_SANDBOX=1` there. The environment flag is an assertion by the
container launcher, not a sandbox itself. The launcher must supply the memory
cgroup, CPU allocation and a reaping pid 1, and must not expose host process
namespaces. Each child additionally inherits a 3 GiB address-space limit.
Workers default to three; six is the maximum. A timeout is an explicit oracle
error, never a skip or agreement. Scratch directories belong to the invocation,
under `target/`; each row has a read-only copied package. Every native run,
classification call, declared-phase call and dynamic lupin call gets a separate
private cwd, HOME, TMPDIR and cache directory. No invocation inherits files left
by a previous one. Candidate builds and candidate executions are isolated too.
Before the first call the harness records the package tree's names, modes,
symlink targets and file hashes. It compares that complete listing after every
oracle invocation and aborts on any change; before/after digests and the actual
number of checked calls are retained in each row and checked for freshness.
Timed-out descendants are signalled by individually recorded pid, never a group.

A front-door status can also be a legal program exit. When native `run` returns
2 or 4 without a trap, the harness obtains a native `conform-run --json` record
to disambiguate rejection/refusal from a program that ran. Static codes and unsupported verdicts come only from the
protocol, never diagnostic prose: a warning on stderr at process exit 0 is still
`exit(0)`, even if its historical code begins with E. A program may print text
that resembles a compiler error without changing its outcome class. It never borrows
stdout or exit status from that second invocation: contradictory outcomes remain
`tool-error`, with the failed command's raw stderr. It never treats
`wolf run --checked` as the checked machine. The Rust compiler implementation
is not read: only the pinned `spec/` and `corpus/` paths are extracted from its
source archive. The assembler and linker are independent Wolf programs.

`tools/differ check --input FILE` checks oracle-table freshness without rerunning
programs: the exact pin-file identity, reference revision, complete row census,
source byte hashes, parsed header expectations and membership, observation
relations and derived summaries. A limited `--limit N` recording is always
marked incomplete and cannot pass freshness. Run
`tools/differ reconcile --first FIRST.json --second SECOND.json --output tests/oracle.json`
after two independent recordings. It requires equal identities and source rows,
retains both observation sets, and derives a `repeat_changes` list. Freshness
requires two recordings and rechecks their stability flags. Changing rows are
identified instead of silently replacing their expectations. The committed table is evidence, not
fenrir coverage. The oracle's own disagreements are listed by file.

`tools/differ compare --input FILE` compares observations that already include
`fenrir` records. Add `--fenrir PATH` to build and execute every entry live in the
Linux sandbox. It reserves a fresh output for every build; an earlier executable
cannot stand in for a missing new output. `--output FILE` retains the JSON result.
Any verdict other than `same` makes this command fail, including refusals.
`--select FILE` compares only the rows a JSON file names (a list of corpus
files, or an object whose `core` list names them, as the core census does);
every named file must be a non-member row. A candidate build links, and one
link of the musl runtime peaks at about 7.4 GiB of address space, so each build
runs under its own 10 GiB cap and `--build-timeout` (180 s); the program itself
keeps the 3 GiB cap and `--timeout`.

## Records

Every `.lu` source is enumerated in sorted order, including module members.
Leading `//!` headers determine `check`, `phase`, `conforms` and membership.
Members are recorded as `module-member` on both sides and are compiled through
their package entry, never independently run or silently skipped. Same-directory
entry candidates are listed; when there is exactly one, its check and phase are
retained as the member's inherited expectation. A malformed implicit member of
a refusing package is never mistaken for a valid standalone program.

Each oracle row contains the file, byte digest, directives, expected header
verdict, phase, membership, and `wolf`/`lupin` observations. Native observations
retain raw stdout as UTF-8 display text and exact base64 bytes plus SHA-256,
process exit, stderr, trap kind and source site when reported. Lupin's full
protocol object is retained, including its stdout digest/inline text, diagnostic
spans and extension fields. A missing source site or trap message is not invented.
An exiting protocol record with null output metadata denotes empty output:
protocol 1 requires the digest whenever an exiting program writes bytes. The
normalized observation uses the empty-byte digest for that case, without
changing the retained protocol object. Trap output metadata remains honest-absent.
Long output unavailable inline is represented
by the protocol's digest, not truncated text passed off as complete stdout.

Oracle relations are `same-observed`, `differs`, `scope-gap`,
`not-dynamically-comparable`, `oracle-error` or `module-member`. These describe
the observations obtainable through native `run`, not a claim of full protocol
span/warning parity: the native front door does not supply a byte-span record
for every successful run. `same-observed` compares exit or trap kind and the
stdout hashes both sides actually supply. Scope gaps and clean static stops
never count as dynamic agreement. Disagreements and tool errors are evidence
about the oracle pair; they are not fenrir successes.

Candidate verdicts are exactly `same`, `differs`, `fenrir-refuses` and
`fenrir-crashes`. Candidate comparison uses native wolf as reference and keeps
lupin's second opinion beside it. It compares stdout bytes/digest, exit or trap
kind, site and message; unavailable trap metadata is retained honestly. Status
2 (a rejection) or 4 (a refusal, outside fenrir's scope) at build time means
`fenrir-refuses`, and 70 means `fenrir-crashes`, with ICE
precedence over any refusal label. Program exit 70 after a successful build is
a program exit, not a compiler error. Other failed builds, signals and timeouts
are crashes. An environment skip is never inferred from 2, 4 or 70.

Coverage is computed as `same` run-header rows divided by all run-header rows;
module members and static refusal rows are separate. Zero run rows gives zero
coverage, never a vacuous 100 percent. F0 accepts no programs and claims no
coverage. Refusal parity and a complete protocol warning/span comparator are
later work, not silently counted as implemented here.

## Tests and cost

`tests/frame.py` plants unknown/stale subset rows, unsupported compiled claims,
a closed bootstrap gap, uncatalogued/unused diagnostics, byte nondeterminism,
a strict-mode skip and a refusal falsely counted as success. `tests/oracle_unit.py`
checks header membership, malformed protocol records, exact trap data, pin
corruption and ICE precedence. `tests/driver.py` invokes the actual stage-0-built
driver through every public seam and checks output preservation.

Enumeration and inventory are linear in source bytes. Linux CI runs the inventory
at N, 10N and 100N, with 100N exceeding ten times the largest real source file,
and rejects superlinear growth with a scheduling allowance. Recording costs the sum
of package-copy bytes plus the black boxes' compile/run times; no compiler pass
or analysis is implemented by this harness. All summaries derive from row data.

## Recorded oracle disagreements

The committed `tests/oracle.json` contains both complete captures of 1,253 source
rows at public corpus/spec revision `5f1f1c949582f53121e4047bc83c86f23ff72240`,
with wolf 0.2.36 and lupin 0.1.58. Each pass has **827 same-observed, 109 differs,
252 scope gaps, one oracle error and 64 module members**. No fenrir coverage is
claimed. Scope gaps split into **224 Lupin-only, 22 wolf-only and six both**.
These counts are derived from the saved rows, not waivers or expected successes.

The root-domain-death row retains native exit 121 and Lupin exit 1. It compares
as the same nonzero outcome class only when both `conc.proc.root` and the
`run(exit=nonzero)` header are present, as spec/03 requires. Other numeric exits,
traps, build refusals and output differences remain distinct. The saved process
bytes and protocol objects are reparsed by the freshness gate; relations and
summaries are pure derivations of those captures plus the pinned headers.

The oracle identity hashes only the GNU wolf archive (including its runtime and
std), GNU Lupin archive and reference spec/corpus archive. Assembler/linker pin
changes do not stale this table. The original public capture manifest and its
hash are retained, so an offline rederivation can verify that oracle inputs did
not change. Any oracle-input change makes the table stale.

### Causes, not blanket equivalence claims

| Cause | Rows | Example and raw observation excerpts |
|---|---:|---|
| Explicit phase stops | 88 | `comptime/align_of_layout.lu`: wolf `pass` at resolve, no diagnostics; Lupin `fail(E0708)`, span `[510,524]`. |
| UB detector versus unchecked native | 13 | `memory/raw_ub_misaligned_u16_read.lu`: native `exit(0)`; Lupin `ub(mem.ub)`. |
| Static rejection versus execution | 3 | `methods/home_range_str_map.lu`: native `fail(E0403)`, exit 2, stdout empty; Lupin `exit(0)`, stdout `4 2 5 true 1\n`. |
| Assertion rendering | 2 | `faults/assert_msg_effect_fails.lu`: both `trap(assert)`; native stdout `effect\n`, Lupin `effect\nm\n`. |
| Allocation accounting | 2 | `memory/list_reset_reuse_ledger.lu`: native `8 true true\n`, Lupin `8 false true\n`; map-pairs details below. |
| Region lifetime | 1 | `memory/region_outer_write_push_copy_call.lu`: native `exit(0)` with the expected seven values; Lupin `trap(region-fault)`, span `[2009,2023]`. |

The 88 phase-stop rows are explicit-phase observations, not 88 proved language
bugs: fused analyses can discover a later-rung error earlier. Spec/06 compares
pass against fail at an explicit stop, while allowing rung tolerance when both
full-ladder runs reject. Keep these differences visible and resolve the spec's
phase boundary before assigning a universal implementation fix. UB rows also
remain information: unchecked native execution is not a second UB detector,
and invalid accesses can produce changing native results.

The four same-verdict output differences and both originally unequal dynamic
outcome cases have individual public issue/disposition drafts:

- [Native mixed-row ICE](../notes/fn00/issues/01-native-ice-mixed-payload-display.md): the one oracle error, `rows/mixed_payload_display.lu`, native tool failure 2 with `lowered WIR failed verification`; Lupin exits 0 and prints `A(0)\nB(p)\nA(0)\nB(p)\n`. The full exact binary diagnostic is retained.
- [Effectful assertion message](../notes/fn00/issues/02-assert-msg-effect-fails.md) and [named assertion message](../notes/fn00/issues/03-assert-msg-name-fails.md): native omits `m`/`boom`; Lupin renders them. The transitional assertion clause permits omission, so neither side is proved wrong by rendering alone.
- [List reset reuse](../notes/fn00/issues/04-list-reset-reuse-ledger.md): Lupin grows its own ledger while reusing scalar-only slots; the reset/refill contract requires reuse, independently of per-tier byte units.
- [Map pairs allocation](../notes/fn00/issues/05-map-pairs-walk-view.md): native prints `64 201600 7 false false\n`, Lupin `64 201600 7 true true\n`. The semantic values agree; per-tier allocation elision/accounting is explicitly outside the strict comparison surface, so this is not a proved language fault.
- [Outer-region copy through a call](../notes/fn00/issues/06-region-outer-write-push-copy-call.md): the explicit outer-copy rule supports native's retained storage; Lupin's later region-fault is erroneous for this witness.
- [Root-domain status disposition](../notes/fn00/issues/07-proc-link-root-death.md): both implementations are correct; the comparison now applies the specified class rule without altering either raw status.

### Ten hand-checked differing rows

These are exact selected observation/record fields; full raw stdout, stderr,
base64 bytes, hashes and protocol objects remain in the table.

| Row under `corpus/` | Native/declared wolf | Lupin | Reading |
|---|---|---|---|
| `comptime/align_of_layout.lu` | `pass`, diagnostics `[]` at resolve | `fail(E0708)`, span `[510,524]` | Explicit-phase timing. |
| `conc/atomic_order_misuse.lu` | `pass`, diagnostics `[]` at resolve | `fail(E1309)`, span `[792,805]` | Explicit-phase timing. |
| `faults/assert_msg_effect_fails.lu` | `trap(assert)`, stdout `effect\n` | `trap(assert)`, stdout `effect\nm\n` | Optional message rendering, not skipped message evaluation. |
| `generics/explicit_apply_arity.lu` | `pass`, diagnostics `[]` at resolve | `fail(E0812)`, span `[473,483]` | Explicit-phase timing. |
| `grammar/attr_contract_unimplemented.lu` | `pass`, diagnostics `[]` at resolve | `fail(E0817)`, span `[355,362]` | Explicit-phase timing. |
| `membrane/extern_let_not_ptr.lu` | `pass`, diagnostics `[]` at resolve | `fail(E0821)`, span `[345,348]` | Explicit-phase timing. |
| `memory/extern_c_outside_unsafe.lu` | `pass`, diagnostics `[]` at typecheck | `fail(E1301)`, span `[405,415]` | Explicit-phase timing. |
| `methods/home_range_str_map.lu` | `fail(E0403)`, exit 2, stdout empty | `exit(0)`, stdout `4 2 5 true 1\n` | Static capability/typing difference. |
| `rows/else_fallback_range_refused.lu` | `pass`, diagnostics `[]` at resolve | `fail(E0411)`, span `[904,938]` | Explicit-phase timing. |
| `strings/char_index_fail.lu` | `pass`, diagnostics `[]` at resolve | `fail(E0411)`, span `[420,424]` | Explicit-phase timing. |

The separate ten-row transport sampler now agrees on every selected observation,
including `lints/match_str_arm_unreachable.lu`: native process exit 0, stdout
`one\n`, and a warning named `E0802`; Lupin has the identical stdout/hash and
warning severity. A warning's historical code prefix never turns success into
rejection. Sampler agreement is not a precondition: every row must instead be
classified with its raw evidence, and genuine disagreements are listed.

Four rows change between captures: `conc/atomic_race_plain.lu`,
`conc/atomic_ub_uaf.lu`, `memory/unsafe_ub_uaf.lu` and
`memory/volatile_ub_uaf.lu`. They expose race/UB-dependent native observations;
both captures are retained rather than rewriting their expected values.

### Declared-phase clean stop versus rejection (88)

- `corpus/comptime/align_of_layout.lu`: wolf `pass`, Lupin `fail(E0708)`.
- `corpus/comptime/offset_of_layout.lu`: wolf `pass`, Lupin `fail(E0708)`.
- `corpus/comptime/shift_overflow.lu`: wolf `pass`, Lupin `fail(E0706)`.
- `corpus/comptime/size_of_layout.lu`: wolf `pass`, Lupin `fail(E0708)`.
- `corpus/conc/atomic_order_misuse.lu`: wolf `pass`, Lupin `fail(E1309)`.
- `corpus/conc/atomic_outside_unsafe.lu`: wolf `pass`, Lupin `fail(E1301)`.
- `corpus/conc/atomic_pointee.lu`: wolf `pass`, Lupin `fail(E1308)`.
- `corpus/conc/capture_mut_arg.lu`: wolf `pass`, Lupin `fail(E1101)`.
- `corpus/conc/capture_mut_lend.lu`: wolf `pass`, Lupin `fail(E1101)`.
- `corpus/conc/capture_write_assign.lu`: wolf `pass`, Lupin `fail(E1101)`.
- `corpus/conc/chan_unsendable.lu`: wolf `pass`, Lupin `fail(E1102)`.
- `corpus/conc/par_capture_write.lu`: wolf `pass`, Lupin `fail(E1101)`.
- `corpus/conc/store_buffer.lu`: wolf `pass`, Lupin `fail(E1101)`.
- `corpus/conc/when_nested.lu`: wolf `pass`, Lupin `fail(E1103)`.
- `corpus/generics/explicit_apply_arity.lu`: wolf `pass`, Lupin `fail(E0812)`.
- `corpus/grammar/attr_contract_unimplemented.lu`: wolf `pass`, Lupin `fail(E0817)`.
- `corpus/grammar/attr_misplaced.lu`: wolf `pass`, Lupin `fail(E0817)`.
- `corpus/grammar/attr_repr_bogus.lu`: wolf `pass`, Lupin `fail(E0817)`.
- `corpus/grammar/attr_repr_unimplemented.lu`: wolf `pass`, Lupin `fail(E0817)`.
- `corpus/grammar/attr_repr_unlayable.lu`: wolf `pass`, Lupin `fail(E0820)`.
- `corpus/grammar/attr_section.lu`: wolf `pass`, Lupin `fail(E0817)`.
- `corpus/grammar/attr_thread_local.lu`: wolf `pass`, Lupin `fail(E0817)`.
- `corpus/grammar/attr_unknown.lu`: wolf `pass`, Lupin `fail(E0817)`.
- `corpus/grammar/cfg_predicate_unknown.lu`: wolf `pass`, Lupin `fail(E0817)`.
- `corpus/grammar/cfg_target_unknown.lu`: wolf `pass`, Lupin `fail(E0817)`.
- `corpus/grammar/extern_abi_interrupt.lu`: wolf `pass`, Lupin `fail(E0818)`.
- `corpus/grammar/index_origin_bad.lu`: wolf `pass`, Lupin `fail(E0813)`.
- `corpus/grammar/intdot_exponent.lu`: wolf `pass`, Lupin `fail(E0004)`.
- `corpus/grammar/list_lit_mixed.lu`: wolf `pass`, Lupin `fail(E0401)`.
- `corpus/grammar/list_lit_untyped_empty.lu`: wolf `pass`, Lupin `fail(E0419)`.
- `corpus/membrane/extern_let_not_ptr.lu`: wolf `pass`, Lupin `fail(E0821)`.
- `corpus/memory/extern_c_outside_unsafe.lu`: wolf `pass`, Lupin `fail(E1301)`.
- `corpus/memory/mode_missing_mut.lu`: wolf `pass`, Lupin `fail(E1007)`.
- `corpus/memory/nested_fn_mut_omitted.lu`: wolf `pass`, Lupin `fail(E1007)`.
- `corpus/memory/packed_field_lend.lu`: wolf `pass`, Lupin `fail(E0819)`.
- `corpus/memory/push_take_moves.lu`: wolf `pass`, Lupin `fail(E1001)`.
- `corpus/memory/raw_field_store_outside_unsafe.lu`: wolf `pass`, Lupin `fail(E1301)`.
- `corpus/memory/static_init_cycle.lu`: wolf `pass`, Lupin `fail(E0705)`.
- `corpus/memory/static_init_not_comptime.lu`: wolf `pass`, Lupin `fail(E0705)`.
- `corpus/memory/static_qualified_var_outside_unsafe/main.lu`: wolf `pass`, Lupin `fail(E1301)`.
- `corpus/memory/static_var_outside_unsafe.lu`: wolf `pass`, Lupin `fail(E1301)`.
- `corpus/memory/unsafe_raw_outside.lu`: wolf `pass`, Lupin `fail(E1301)`.
- `corpus/memory/unsafe_sig.lu`: wolf `pass`, Lupin `fail(E1302)`.
- `corpus/memory/volatile_outside_unsafe.lu`: wolf `pass`, Lupin `fail(E1301)`.
- `corpus/memory/volatile_pointee_bool.lu`: wolf `pass`, Lupin `fail(E1307)`.
- `corpus/memory/volatile_pointee_int.lu`: wolf `pass`, Lupin `fail(E1307)`.
- `corpus/rows/else_fallback_range_refused.lu`: wolf `pass`, Lupin `fail(E0411)`.
- `corpus/rows/match_range_empty.lu`: wolf `pass`, Lupin `fail(E0815)`.
- `corpus/rows/negative/ctor_arg_unresolved.lu`: wolf `pass`, Lupin `fail(E0301)`.
- `corpus/rows/negative/errdefer_infallible.lu`: wolf `pass`, Lupin `fail(E0607)`.
- `corpus/rows/negative/error_alias_cycle.lu`: wolf `pass`, Lupin `fail(E0610)`.
- `corpus/rows/negative/handler_uncovered.lu`: wolf `pass`, Lupin `fail(E0809)`.
- `corpus/rows/negative/match_row_missing_tag.lu`: wolf `pass`, Lupin `fail(E0801)`.
- `corpus/rows/negative/match_row_missing_value.lu`: wolf `pass`, Lupin `fail(E0801)`.
- `corpus/rows/negative/match_row_tag_variant_collision.lu`: wolf `pass`, Lupin `fail(E0816)`.
- `corpus/rows/negative/row_operand_add.lu`: wolf `pass`, Lupin `fail(E0409)`.
- `corpus/rows/negative/row_operand_compare.lu`: wolf `pass`, Lupin `fail(E0409)`.
- `corpus/rows/negative/row_operand_member.lu`: wolf `pass`, Lupin `fail(E0409)`.
- `corpus/rows/negative/row_operand_method.lu`: wolf `pass`, Lupin `fail(E0409)`.
- `corpus/rows/negative/row_operand_rhs.lu`: wolf `pass`, Lupin `fail(E0409)`.
- `corpus/rows/negative/try_in_defer.lu`: wolf `pass`, Lupin `fail(E0611)`.
- `corpus/rows/negative/try_in_defer_block.lu`: wolf `pass`, Lupin `fail(E0611)`.
- `corpus/rows/negative/try_in_errdefer.lu`: wolf `pass`, Lupin `fail(E0611)`.
- `corpus/strings/char_index_fail.lu`: wolf `pass`, Lupin `fail(E0411)`.
- `corpus/strings/format_spec_malformed.lu`: wolf `pass`, Lupin `fail(E0412)`.
- `corpus/strings/format_spec_mismatch.lu`: wolf `pass`, Lupin `fail(E0413)`.
- `corpus/strings/trim_cutset_refused.lu`: wolf `pass`, Lupin `fail(E0402)`.
- `corpus/traits/dyn_temp_refused.lu`: wolf `pass`, Lupin `fail(E0810)`.
- `corpus/traits/golden_arith.lu`: wolf `pass`, Lupin `fail(E0501)`.
- `corpus/traits/golden_eq.lu`: wolf `pass`, Lupin `fail(E0501)`.
- `corpus/traits/golden_missing_bound.lu`: wolf `pass`, Lupin `fail(E0501)`.
- `corpus/traits/op_eq_no_trait.lu`: wolf `pass`, Lupin `fail(E0301)`.
- `corpus/traits/op_hetero_add.lu`: wolf `pass`, Lupin `fail(E0514)`.
- `corpus/traits/op_missing_impl.lu`: wolf `pass`, Lupin `fail(E0502)`.
- `corpus/typecheck/byte_elem_arith_fail.lu`: wolf `pass`, Lupin `fail(E0401)`.
- `corpus/typecheck/byte_narrow_fail.lu`: wolf `pass`, Lupin `fail(E0401)`.
- `corpus/typecheck/cast_bad.lu`: wolf `pass`, Lupin `fail(E0805)`.
- `corpus/typecheck/fn_never_reaches_end.lu`: wolf `pass`, Lupin `fail(E0401)`.
- `corpus/typecheck/fn_never_return.lu`: wolf `pass`, Lupin `fail(E0401)`.
- `corpus/typecheck/generic_bind_once.lu`: wolf `pass`, Lupin `fail(E0401)`.
- `corpus/typecheck/int_not_float.lu`: wolf `pass`, Lupin `fail(E0409)`.
- `corpus/typecheck/interp_spec_on_union.lu`: wolf `pass`, Lupin `fail(E0413)`.
- `corpus/typecheck/map_compound_absent.lu`: wolf `pass`, Lupin `fail(E0417)`.
- `corpus/typecheck/map_struct_key.lu`: wolf `pass`, Lupin `fail(E0418)`.
- `corpus/typecheck/str_slice_assign.lu`: wolf `pass`, Lupin `fail(E0416)`.
- `corpus/typecheck/tail_declared_str.lu`: wolf `pass`, Lupin `fail(E0401)`.
- `corpus/typecheck/tail_declared_union.lu`: wolf `pass`, Lupin `fail(E0401)`.
- `corpus/typecheck/variant_bare_value.lu`: wolf `pass`, Lupin `fail(E0301)`.

### UB detector versus native outcome (13)

- `corpus/conc/atomic_ub_misaligned.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/conc/atomic_ub_uaf.lu`: wolf `exit(44)`, Lupin `ub(mem.ub)`.
- `corpus/memory/raw_ub_misaligned_repr_c_field.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/memory/raw_ub_misaligned_repr_c_field_store.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/memory/raw_ub_misaligned_u16_read.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/memory/raw_ub_misaligned_u16_write.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/memory/raw_ub_misaligned_u32_read.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/memory/raw_ub_misaligned_u32_write.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/memory/raw_ub_misaligned_u64_read.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/memory/raw_ub_misaligned_u64_write.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/memory/unsafe_ub_uaf.lu`: wolf `exit(6)`, Lupin `ub(mem.ub)`.
- `corpus/memory/volatile_ub_misaligned.lu`: wolf `exit(0)`, Lupin `ub(mem.ub)`.
- `corpus/memory/volatile_ub_uaf.lu`: wolf `exit(62)`, Lupin `ub(mem.ub)`.

### Static rejection versus dynamic outcome (3)

- `corpus/faults/exclusivity_nested_path.lu`: wolf `fail(E1002)`, Lupin `trap(exclusivity)`.
- `corpus/faults/use_after_move_field.lu`: wolf `fail(E1001)`, Lupin `trap(use-after-move)`.
- `corpus/methods/home_range_str_map.lu`: wolf `fail(E0403)`, Lupin `exit(0)`.
