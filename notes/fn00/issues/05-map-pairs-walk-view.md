# Map pairs walk has a permitted per-tier allocation difference

## Reproducer

Public corpus row: `corpus/memory/map_pairs_walk_view.lu`.

```lu
//! check: run(exit=0, stdout="64 201600 7 true true\n")
//! phase: run
//! conforms: type.map, mem.region.account.1, mem.region.promote.1
```

Public spec and corpus revision: `5f1f1c949582f53121e4047bc83c86f23ff72240` of `wolffe-lang/wolf-lang`. Observed with the published archives on Linux x86-64; both recorded passes agree:

- `wolf-0.2.36-x86_64-unknown-linux-gnu.tar.gz` — sha256 `d383c74c8cd123b9d9dfaa268271d4f004294f85c2b230237d0ef07027d9500d`.
- `lupin-0.1.58-x86_64-unknown-linux-gnu.tar.gz` — sha256 `34f52792bb59bc7565e0edc1235cd47d9a6ad13d5e6528993627f2e699b62193`.

The command below uses the archives' own layout: keep each release's bundled files beside its executable and put the release commands on `PATH`. The recording's relocation required `WOLF_STD` and `WOLF_RT_LIB` only to locate files kept beside the executable in the unpacked archive; no overrides are needed here.

From the public wolf-lang checkout at that revision, in a shell without `set -e`:

```sh
mkdir -p target
wolf run --no-cache -o target/repro corpus/memory/map_pairs_walk_view.lu
printf 'native process status: %s\n' "$?"
lupin conform-run corpus/memory/map_pairs_walk_view.lu --json
printf 'Lupin tool process status: %s\n' "$?"
```

`conform-run` reports the program outcome in JSON; its own successful process status is not the program's status. Lupin output below is the decoded recorded `stdout_inline`, not the literal JSON command output.

## Observed results

Native `wolf run` process status: **0**; recorded verdict: `exit(0)`. The native `conform-run --native --json --phase=run` classification also reports `exit(0)` (tool process status 0).

Native stdout:

```text
64 201600 7 false false
```

Native stderr:

(empty)

Lupin `conform-run` tool process status: **0**; record verdict: `exit(0)`; phase reached: `run`. Recorded program exit status: **0**.

Lupin program stdout:

```text
64 201600 7 true true
```

Lupin stderr: (empty).

Relevant exact JSON record fields (not the whole record):

```json
{
  "impl": "lupin",
  "impl_version": "0.1.58",
  "phase_reached": "run",
  "verdict": "exit(0)",
  "stdout_inline": "64 201600 7 true true\n"
}
```

## Witness and spec

The row inserts 64 entries, walks `m.pairs()` 100 times, and calls a generic lookup using `m.pairs()` another 100 times. It reports entry count, accumulated values, lookup result, then two same-tier ledger-flatness checks. Both executions agree on `64 201600 7`. Only the allocation-flatness booleans differ.

`spec/02-memory-model.md`, `[mem.region.account.1]`:

>   ledger's *units* — what charges, and by how much — are
>   implementation-measured facts per tier, not comparison surface: the
>   native arena charges alignment-rounded container and region-alloc
>   storage; the checked machine charges its shadow-memory model. The
>   ledger is an accounting surface in the same carve-out class as
>   Tier-3 address inspection, not a `[mem.region.promote.1]`
>   observation: an allocation the implementation promotes or elides may
>   charge nothing, and no program may read placement from the number.

`[mem.region.promote.1]` states:

> - `[mem.region.promote.1]` Stack promotion / escape analysis must not
>   change any program observation: allocation placement is unobservable
>   except through §7-licensed reasoning and address inspection in Tier 3
>   (which carries no placement guarantees — `[mem.ub]` row T2 layout freedom).

## Disposition

No language implementation fault is established. Native's `false false` indicates allocation/accounting work that Lupin's `true true` avoids in this witness. The spec explicitly permits allocation elision and excludes ledger units and allocation charging from cross-tier comparison. The header therefore encodes a specific allocation-flatness/optimization expectation, not a universally required semantic result. This can be tracked as a native performance opportunity or a corpus/comparison-policy clarification; it must not be reported as native semantic nonconformance merely because Lupin matches the header. The semantic count, sum and lookup result agree. The ledger observations alone do not identify a particular internal allocation mechanism.
