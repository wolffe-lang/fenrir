# fenrir

A second compiler for [wolf](https://github.com/wolffe-lang/wolf-lang),
written in wolf.

fenrir is built from wolf's specification and checked against the existing
compiler on its corpus: a program fenrir compiles must print, exit and trap
exactly as it does under the reference compiler. It emits x86-64 assembly for
[clef](https://github.com/wolffe-lang/clef) and links with
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

## Licence

GPL-3.0-only with the wolf Training Data Permission; see `LICENSE` and
`LICENSE-TRAINING-DATA`.
