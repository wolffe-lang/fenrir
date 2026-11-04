# Root-domain death: no implementation issue; harness classification corrected

## Reproducer

Public corpus row: `corpus/conc/proc_link_root_death.lu`.

```lu
//! check: run(exit=nonzero)
//! phase: run
//! conforms: conc.proc.root, conc.proc.link.pair, conf.directive.check
```

Public spec and corpus revision: `5f1f1c949582f53121e4047bc83c86f23ff72240` of `wolffe-lang/wolf-lang`. Observed with the published archives on Linux x86-64; both recorded passes agree:

- `wolf-0.2.36-x86_64-unknown-linux-gnu.tar.gz` — sha256 `d383c74c8cd123b9d9dfaa268271d4f004294f85c2b230237d0ef07027d9500d`.
- `lupin-0.1.58-x86_64-unknown-linux-gnu.tar.gz` — sha256 `34f52792bb59bc7565e0edc1235cd47d9a6ad13d5e6528993627f2e699b62193`.

The command below uses the archives' own layout: keep each release's bundled files beside its executable and put the release commands on `PATH`. The recording's relocation required `WOLF_STD` and `WOLF_RT_LIB` only to locate files kept beside the executable in the unpacked archive; no overrides are needed here.

From the public wolf-lang checkout at that revision, in a shell without `set -e`:

```sh
mkdir -p target
wolf run --no-cache -o target/repro corpus/conc/proc_link_root_death.lu
printf 'native process status: %s\n' "$?"
lupin conform-run corpus/conc/proc_link_root_death.lu --json
printf 'Lupin tool process status: %s\n' "$?"
```

`conform-run` reports the program outcome in JSON; its own successful process status is not the program's status. Lupin output below is the decoded recorded `stdout_inline`, not the literal JSON command output.

## Observed results

Native `wolf run` process status: **121**; recorded verdict: `exit(121)`. The native `conform-run --native --json --phase=run` classification also reports `exit(121)` (tool process status 0).

Native stdout:

(empty)

Native stderr:

```text
wolf-proc: root supervisor domain died (error): killing live procs
```

Lupin `conform-run` tool process status: **0**; record verdict: `exit(1)`; phase reached: `run`. Recorded program exit status: **1**.

Lupin program stdout:

(empty; `stdout_inline` is null in the record)

Lupin stderr: (empty).

Relevant exact JSON record fields (not the whole record):

```json
{
  "impl": "lupin",
  "impl_version": "0.1.58",
  "phase_reached": "run",
  "verdict": "exit(1)",
  "stdout_inline": null
}
```

## Spec

The witness links `shard` to `main`'s root domain; `shard` returns `Corrupt`. Neither execution prints from the blocked receive's handler or the later serving path.

`spec/03-concurrency.md`, `[conc.proc.root]`:

> - `[conc.proc.root]` The **root supervisor's domain is the process**:
>   `main`'s task tree runs in it, and `w.link()` called from `main`
>   couples `w` to it. The root domain's abnormal death — a linked
>   partner's abnormal exit, or a fault escaping `main` — runs the
>   killed-proc sequence (`[conc.proc.kill]`) for every live proc and
>   terminates the process with a nonzero, implementation-specified
>   status (`[conf.trap.exit]` discipline: conforming tools compare the
>   outcome class, never the number). A corpus witness spells that
>   class `run(exit=nonzero)` (`[conf.directive.check]`; witness
>   `conc/proc_link_root_death.lu`, where wolf's native tier exits 121
>   and lupin 0.1.36 exits 1).

`spec/05-conformance.md`, `[conf.directive.check]`:

>   `exit=nonzero` matches an `exit(N)` verdict whose N is not 0 and
>   nothing else: not a trap (a trap is its own outcome class, spelled
>   `exit=trap`), and never a program that did not compile — a
>   `fail(CODE)` verdict under `exit=nonzero` is an error by name,
>   because a build failure also ends `wolf run` nonzero and the weak
>   claim must not score it.

## Disposition

**No implementation issue; harness classification corrected.** Native status 121 and Lupin record `exit(1)` are both correct nonzero process-termination outcomes under this clause. The recorded differential result compared the numbers and called them different; that is a harness classification error, not a compiler or interpreter bug. Native's explanatory stderr and Lupin's empty stderr do not change the specified outcome class.

The corrected comparison uses the nonzero-exit class only when both the `conc.proc.root` conformance anchor and the `run(exit=nonzero)` header are present. It does not equate arbitrary exit statuses, convert traps to exits, accept a build failure as a runtime outcome, or apply this relaxation to rows lacking either condition. Retain both raw statuses and verdicts as evidence. This draft is a disposition record, not a request to change either implementation.
