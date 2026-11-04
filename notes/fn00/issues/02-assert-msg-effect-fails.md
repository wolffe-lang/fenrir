# Assertion message rendering differs after the message effect runs

## Reproducer

Public corpus row: `corpus/faults/assert_msg_effect_fails.lu`.

```lu
//! check: run(exit=trap(assert), stdout="effect\n")
//! phase: run
//! conforms: conf.trap.assert
```

Public spec and corpus revision: `5f1f1c949582f53121e4047bc83c86f23ff72240` of `wolffe-lang/wolf-lang`. Observed with the published archives on Linux x86-64; both recorded passes agree:

- `wolf-0.2.36-x86_64-unknown-linux-gnu.tar.gz` — sha256 `d383c74c8cd123b9d9dfaa268271d4f004294f85c2b230237d0ef07027d9500d`.
- `lupin-0.1.58-x86_64-unknown-linux-gnu.tar.gz` — sha256 `34f52792bb59bc7565e0edc1235cd47d9a6ad13d5e6528993627f2e699b62193`.

The command below uses the archives' own layout: keep each release's bundled files beside its executable and put the release commands on `PATH`. The recording's relocation required `WOLF_STD` and `WOLF_RT_LIB` only to locate files kept beside the executable in the unpacked archive; no overrides are needed here.

From the public wolf-lang checkout at that revision, in a shell without `set -e`:

```sh
mkdir -p target
wolf run --no-cache -o target/repro corpus/faults/assert_msg_effect_fails.lu
printf 'native process status: %s\n' "$?"
lupin conform-run corpus/faults/assert_msg_effect_fails.lu --json
printf 'Lupin tool process status: %s\n' "$?"
```

`conform-run` reports the program outcome in JSON; its own successful process status is not the program's status. Lupin output below is the decoded recorded `stdout_inline`, not the literal JSON command output.

## Observed results

Native `wolf run` process status: **134**; recorded verdict: `trap(assert)`. The native `conform-run --native --json --phase=run` classification also reports `trap(assert)` (tool process status 0).

Native stdout:

```text
effect
```

Native stderr:

Relevant exact first line:

```text
wolf-trap: assert
```

The following diagnostic line identifies the assertion site in the corpus row: line 19, column 5.

Lupin `conform-run` tool process status: **0**; record verdict: `trap(assert)`; phase reached: `run`. No numeric program exit status is reported for this trap.

Lupin program stdout:

```text
effect
m
```

Lupin stderr: (empty).

Relevant exact JSON record fields (not the whole record):

```json
{
  "impl": "lupin",
  "impl_version": "0.1.58",
  "phase_reached": "run",
  "verdict": "trap(assert)",
  "stdout_inline": "effect\nm\n",
  "trap_message": "m",
  "x-trap-clause": "conf.trap.map",
  "x-trap-span": [
    538,
    565
  ]
}
```

## Witness and spec

The message is `"{noisy()}"`; `noisy()` prints `effect` and returns `"m"`. The loop leaves `c == 1`, so `assert(c == 2, "{noisy()}")` takes the failing path. Both implementations print `effect`, never print `after`, and report `trap(assert)`.

`spec/05-conformance.md`, `[conf.trap.assert]`:

> The two-argument form `assert(cond, msg)`
>   is the intrinsic's own arity: `msg` is a `str` evaluated **only** on
>   the failing path; rendering is one line to stdout before the trap
>   once formatting lands — until then implementations may drop the
>   message.

## Disposition

This is a transitional rendering/corpus-expectation discrepancy, not a proved language violation by either implementation. Native evaluates the message's effect and omits the rendered message; Lupin evaluates it and additionally renders `m` and records `trap_message: "m"`. The clause explicitly permits dropping the message until formatting lands, so it does not require these recorded rendering choices to match. Native matches the header's stdout; Lupin adds the rendered line. Clarify the transitional rendering expectation or the corpus comparison policy before assigning an implementation fault. Do not treat the native absence of `trap_message` as evidence that `noisy()` was skipped.
