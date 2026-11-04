# Lupin loses outer container storage copied through a mut call

## Reproducer

Public corpus row: `corpus/memory/region_outer_write_push_copy_call.lu`.

```lu
//! check: run(exit=0, stdout="4 100000 101 64 4 0 2000\n")
//! phase: run
//! conforms: mem.region.outer-write, mem.region.edge.elem, mem.region.create.3
```

Public spec and corpus revision: `5f1f1c949582f53121e4047bc83c86f23ff72240` of `wolffe-lang/wolf-lang`. Observed with the published archives on Linux x86-64; both recorded passes agree:

- `wolf-0.2.36-x86_64-unknown-linux-gnu.tar.gz` — sha256 `d383c74c8cd123b9d9dfaa268271d4f004294f85c2b230237d0ef07027d9500d`.
- `lupin-0.1.58-x86_64-unknown-linux-gnu.tar.gz` — sha256 `34f52792bb59bc7565e0edc1235cd47d9a6ad13d5e6528993627f2e699b62193`.

The command below uses the archives' own layout: keep each release's bundled files beside its executable and put the release commands on `PATH`. The recording's relocation required `WOLF_STD` and `WOLF_RT_LIB` only to locate files kept beside the executable in the unpacked archive; no overrides are needed here.

From the public wolf-lang checkout at that revision, in a shell without `set -e`:

```sh
mkdir -p target
wolf run --no-cache -o target/repro corpus/memory/region_outer_write_push_copy_call.lu
printf 'native process status: %s\n' "$?"
lupin conform-run corpus/memory/region_outer_write_push_copy_call.lu --json
printf 'Lupin tool process status: %s\n' "$?"
```

`conform-run` reports the program outcome in JSON; its own successful process status is not the program's status. Lupin output below is the decoded recorded `stdout_inline`, not the literal JSON command output.

## Observed results

Native `wolf run` process status: **0**; recorded verdict: `exit(0)`. The native `conform-run --native --json --phase=run` classification also reports `exit(0)` (tool process status 0).

Native stdout:

```text
4 100000 101 64 4 0 2000
```

Native stderr:

(empty)

Lupin `conform-run` tool process status: **0**; record verdict: `trap(region-fault)`; phase reached: `run`. No numeric program exit status is reported for this trap.

Lupin program stdout:

No stdout is supplied (`stdout_inline: null`, `stdout_sha256: null`); this does not assert that an independently captured stream was empty.

Lupin stderr: (empty).

Relevant exact JSON record fields (not the whole record):

```json
{
  "impl": "lupin",
  "impl_version": "0.1.58",
  "phase_reached": "run",
  "verdict": "trap(region-fault)",
  "stdout_inline": null,
  "x-trap-clause": "mem.region.intra.2",
  "x-trap-span": [
    2009,
    2023
  ]
}
```

## Witness

`h` is declared before both region blocks. `alloc(mut h, ...)` is called inside `region scratch`; its new slots are created at these stores:

```lu
fn alloc(mut h: Heap, t: int) -> int {
    let at = h.used * 2 + h.half
    if at >= h.slots.len {
        (mut h.slots).push(copy empty())
        (mut h.slots).push(copy empty())
    }
    h.slots[at].t = t
    h.used += 1
    at
}
```

The block fills an outer slot with 100,000 bytes and another with 64 scalar-only `Val` elements. A second region churns temporary storage. After both blocks close, `collect(mut h)` reads and copies the outer slots. Lupin's reported UTF-8 byte span `[2009, 2023]` identifies `h.slots[src].t` in `collect` (line 61), with `x-trap-clause: "mem.region.intra.2"`. Native reads the retained data and prints the header's exact result.

## Spec

`spec/02-memory-model.md`, `[mem.region.create.3]` supplies the default:

> - `[mem.region.create.3]` **Ambient allocation**: every function executes
>   with a *current region*; heap allocations land there.

The clause also makes the caller's current region the function body's default; `in r { … }` sets it to `r` for the block.

`[mem.region.outer-write]` explicitly covers stores through `mut` parameters and `copy` at the store:

>   a write into an OUTER value — a field store or whole assignment to a
>   binding declared before the block opened, a store through a `mut`
>   parameter (always outer: its storage is the caller's), a `push`, an
>   index store or a `Map` store into such a container — is admitted
>   when the stored value **names no region** (`[mem.region.scalar]`; a
>   literal's bytes are static and name none either) or is written
>   **`copy e` at the store**.

It specifies the destination of that materializing copy (excerpt):

> made in
>   the **outer value's region**, never the block's:

For a container store, the same clause specifies:

> the container's OWN region, the one its header remembers

For calls inside a block, it gives the ambient-clean exception (excerpts):

> **unless the callee's parameter is
>   ambient-clean** — proven by the callee's own lowering, over its whole
>   body: the parameter's root never holds or shares an allocation
>   outside its own region (the generalized region its storage arrived
>   in, where its containers grow and the copies aimed at it land) other
>   than its own entry storage and the static region's.

The permitted operations include:

> Under this clause that is exactly: scalar stores; container
>   stores of
>   scalars or of `copy`s (the container's own region); containers
>   replaced by `copy` (the old header's region); calls handing the
>   parameter, or a place in it, to an ambient-clean parameter; and the
>   mutators that store nothing (`pop`, `clear`, `reset`, `reserve`).

`[mem.region.intra.2]` states:

> - `[mem.region.intra.2]` A region dies as a unit: when a region is freed
>   (sugar-block exit, or last use of the region value), every allocation in
>   it is freed **wholesale**. Per-allocation frees do not exist in safe
>   code.

## Disposition

Lupin is wrong on this witness. The two `push(copy empty())` stores into `h.slots` materialize into the container's own region, not the caller's scratch region. `alloc` otherwise stores scalars; it meets the clause's ambient-clean case, so calling it inside the block must not retain scratch-region storage in `h`. The direct byte pushes and scalar-only `Val` pushes likewise name no region. Freeing scratch and the later temporary region therefore must not invalidate the outer slots; `[mem.region.intra.2]` does not license this trap. Native's successful retained-data output is consistent with the specified behavior. The black-box record establishes an erroneous Lupin region-fault, not its internal cause or a specific repair.
