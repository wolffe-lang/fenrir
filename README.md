# fenrir

A second compiler for [wolf](https://github.com/wolffe-lang/wolf-lang),
written in wolf.

fenrir is built from wolf's specification and checked against the existing
compiler on its corpus: a program fenrir compiles must print, exit and trap
exactly as it does under the reference compiler. Its backend will emit x86-64
assembly for [clef](https://github.com/wolffe-lang/clef) and link with
[ligature](https://github.com/wolffe-lang/ligature), both written in wolf, so a
program built by fenrir needs no Rust, LLVM or binutils on the way. The
runtime library, `libwolf_rt.a`, comes from the wolf release fenrir is pinned
to.

The goal is self-hosting: fenrir built by the reference compiler builds
fenrir, that build builds fenrir again, and the last two are byte-identical.

## Status

Nothing compiles yet. The first milestones, in order:

| | what |
|---|---|
| F0 | the frame: pinned toolchain, continuous integration, the corpus harness and its gates |
| F1 | `hello, wolf`, compiled end to end on Linux x86-64 |
| F2 | the core language: enums, `match`, lists, `Map`, error values, traps |
| F3 | the memory model, lowered as the specification states it |
| F4 | generics, traits, closures, modules; the standard library compiles |
| F5 | the fixpoint: fenrir compiles itself, byte for byte |
| F6 | refusal parity: every program the reference rejects, rejected with its code |
| F7 | full corpus parity, and fenrir running on PAX |

## Build and test

On Linux x86-64 or macOS arm64, install Python 3.11+, curl and a native C
toolchain, then run:

```sh
tools/fetch-toolchain        # downloads and verifies every input digest twice
tools/build                  # pinned wolf 0.2.36 builds target/fenrir
ci/check                     # unit tests, gates and driver integration
tools/build-tools            # optional host-native clef and ligature binaries
```

The frame refuses every invocation with status 2 and does not replace an output
file. The `--emit=tokens|ast`, `asm`, `fir` and `link` commands are stable stubs
for the front-end and backend modules; see [DRIVER](docs/DRIVER.md). macOS is a
development host, not an output target. All inputs and build output stay under
`.wolf-bin/` and `target/`; nothing is installed globally.

The [harness](docs/HARNESS.md) records native wolf and lupin as black boxes
against an immutable specification/corpus pin. Two complete oracle captures are
committed; their disagreements are listed, not counted as compiler coverage.
Refusals fail the differential, and coverage is computed. Run `tools/differ check`
to verify the table's freshness. The [subset inventory](docs/SUBSET.md) prints the gap
between source constructs and the empty implemented compiler subset; the
[diagnostics catalog](docs/DIAGNOSTICS.md) is also empty. CI builds and runs
strict gates on Linux and macOS; branch pushes do not run CI.

## Licence

GPL-3.0-only with the wolf Training Data Permission; see `LICENSE` and
`LICENSE-TRAINING-DATA`.
