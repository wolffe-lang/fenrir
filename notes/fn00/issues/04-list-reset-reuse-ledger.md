# Lupin charges reused list storage after reset

## Reproducer

Public corpus row: `corpus/memory/list_reset_reuse_ledger.lu`.

```lu
//! check: run(exit=0, stdout="8 true true\n")
//! phase: run
//! conforms: type.list.reset, type.list.reserve, mem.region.account.1
```

Public spec and corpus revision: `5f1f1c949582f53121e4047bc83c86f23ff72240` of `wolffe-lang/wolf-lang`. Observed with the published archives on Linux x86-64; both recorded passes agree:

- `wolf-0.2.36-x86_64-unknown-linux-gnu.tar.gz` — sha256 `d383c74c8cd123b9d9dfaa268271d4f004294f85c2b230237d0ef07027d9500d`.
- `lupin-0.1.58-x86_64-unknown-linux-gnu.tar.gz` — sha256 `34f52792bb59bc7565e0edc1235cd47d9a6ad13d5e6528993627f2e699b62193`.

The command below uses the archives' own layout: keep each release's bundled files beside its executable and put the release commands on `PATH`. The recording's relocation required `WOLF_STD` and `WOLF_RT_LIB` only to locate files kept beside the executable in the unpacked archive; no overrides are needed here.

From the public wolf-lang checkout at that revision, in a shell without `set -e`:

```sh
mkdir -p target
wolf run --no-cache -o target/repro corpus/memory/list_reset_reuse_ledger.lu
printf 'native process status: %s\n' "$?"
lupin conform-run corpus/memory/list_reset_reuse_ledger.lu --json
printf 'Lupin tool process status: %s\n' "$?"
```

`conform-run` reports the program outcome in JSON; its own successful process status is not the program's status. Lupin output below is the decoded recorded `stdout_inline`, not the literal JSON command output.

## Observed results

Native `wolf run` process status: **0**; recorded verdict: `exit(0)`. The native `conform-run --native --json --phase=run` classification also reports `exit(0)` (tool process status 0).

Native stdout:

```text
8 true true
```

Native stderr:

(empty)

Lupin `conform-run` tool process status: **0**; record verdict: `exit(0)`; phase reached: `run`. Recorded program exit status: **0**.

Lupin program stdout:

```text
8 false true
```

Lupin stderr: (empty).

Relevant exact JSON record fields (not the whole record):

```json
{
  "impl": "lupin",
  "impl_version": "0.1.58",
  "phase_reached": "run",
  "verdict": "exit(0)",
  "stdout_inline": "8 false true\n"
}
```

## Witness and spec

The row reserves eight `V` elements, fills the list, and reads `before = region_bytes(r)`. `V` contains only `int`, `int`, and `f64` fields. It resets and refills those same eight slots 100 times, reads `after`, then pushes eight additional elements. The output is `n`, `after == before`, and whether the final pushes increased the ledger.

`spec/10-types.md`, `[type.list.reset]`:

> - `[type.list.reset]` **`xs.reset()`** (`mut` receiver, unit-valued)
>   empties the list and **keeps its buffer**: the length goes to 0, the
>   capacity and the storage stay, the next pushes reuse it in the
>   list's own region, and the reset itself allocates nothing and
>   charges nothing on any machine.

The same clause makes the rebuild guarantee explicit:

> The rule the two names state: **a `List`
>   field replaced by assignment holds its old storage until its region
>   ends**, so a rebuild that must not grow the region resets and
>   refills.

`[type.list.reserve]` explicitly distinguishes reservation accounting from slot accounting:

>   (`[mem.region.account.1]`): the native arena charges the buffer at
>   the reservation, the checked machine charges what is stored (a push
>   charges its slot) and nothing at the reservation.

`spec/02-memory-model.md`, `[mem.region.account.1]`:

>   ledger's *units* — what charges, and by how much — are
>   implementation-measured facts per tier, not comparison surface: the
>   native arena charges alignment-rounded container and region-alloc
>   storage; the checked machine charges its shadow-memory model. The
>   ledger is an accounting surface in the same carve-out class as
>   Tier-3 address inspection, not a `[mem.region.promote.1]`
>   observation: an allocation the implementation promotes or elides may
>   charge nothing, and no program may read placement from the number.

## Disposition

Lupin is wrong about the reset/refill reuse contract: the middle `false` means its ledger grows while refilling already-held storage with scalar-only elements. This is not a comparison of native and interpreter byte totals. It is a same-tier before/after equality test across operations that reuse existing storage, as `[type.list.reset]` expressly promises. Native's `8 true true` matches the contract and header. Lupin's `8 false true` preserves the length and charges additional high-water storage, but does not keep the repeated refill flat. Fix and test Lupin's reuse accounting without imposing identical byte units across tiers.
