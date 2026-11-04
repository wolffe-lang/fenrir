# Assertion message rendering differs for a named message

## Reproducer

Public corpus row: `corpus/faults/assert_msg_name_fails.lu`.

```lu
//! check: run(exit=trap(assert), stdout="before\n")
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
wolf run --no-cache -o target/repro corpus/faults/assert_msg_name_fails.lu
printf 'native process status: %s\n' "$?"
lupin conform-run corpus/faults/assert_msg_name_fails.lu --json
printf 'Lupin tool process status: %s\n' "$?"
```

`conform-run` reports the program outcome in JSON; its own successful process status is not the program's status. Lupin output below is the decoded recorded `stdout_inline`, not the literal JSON command output.

## Observed results

Native `wolf run` process status: **134**; recorded verdict: `trap(assert)`. The native `conform-run --native --json --phase=run` classification also reports `trap(assert)` (tool process status 0).

Native stdout:

```text
before
```

Native stderr:

Relevant exact first line:

```text
wolf-trap: assert
```

The following diagnostic line identifies the assertion site in the corpus row: line 14, column 5.

Lupin `conform-run` tool process status: **0**; record verdict: `trap(assert)`; phase reached: `run`. No numeric program exit status is reported for this trap.

Lupin program stdout:

```text
before
boom
```

Lupin stderr: (empty).

Relevant exact JSON record fields (not the whole record):

```json
{
  "impl": "lupin",
  "impl_version": "0.1.58",
  "phase_reached": "run",
  "verdict": "trap(assert)",
  "stdout_inline": "before\nboom\n",
  "trap_message": "boom",
  "x-trap-clause": "conf.trap.map",
  "x-trap-span": [
    589,
    607
  ]
}
```

## Witness and spec

`main` prints `before` and calls `bail("boom")`. Its body is `assert(false, msg)`. Neither execution reaches the later `print("after")`.

`spec/05-conformance.md`, `[conf.trap.assert]`:

> The two-argument form `assert(cond, msg)`
>   is the intrinsic's own arity: `msg` is a `str` evaluated **only** on
>   the failing path; rendering is one line to stdout before the trap
>   once formatting lands — until then implementations may drop the
>   message.

## Disposition

This is a transitional rendering/corpus-expectation discrepancy, not a proved language violation by either implementation. Native matches the header's stdout and traps; Lupin renders an additional `boom` line and records `trap_message: "boom"` before the same assertion trap. Dropping the rendered message is explicitly allowed until formatting lands. The clause does not decide that either observed rendering choice is wrong. Unlike the effectful twin, this witness alone does not expose a side effect of reading the message, so no claim about skipped evaluation follows from the missing line. Clarify rendering expectations or comparison policy rather than treating the optional line as an established semantic fault.
