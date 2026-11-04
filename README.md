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

No source program compiles to machine code yet. The lexer and parser provide
stable token and AST views, with source spans and named syntax refusals.
The backend accepts typed, hand-written
[FIR](docs/FIR.md), verifies it unconditionally, prints a round-tripping text
form and emits deterministic x86-64 assembly. Its first allocator keeps every
value on the stack. [ABI](docs/ABI.md) specifies its calling and runtime boundary.

The link command invokes only staged clef and ligature. The executable proof
is qualified on Linux x86-64: each of 21 hand-written FIR programs is assembled
by clef, linked by ligature and run, and its output and exit status match the
same program in wolf source built by the pinned reference compiler. Each link
gets a 10 GiB address-space budget, because one static link of the runtime
currently peaks near 7.4 GiB in ligature
([ligature#32](https://github.com/wolffe-lang/ligature/issues/32)). The pinned assembler now includes the direct
arithmetic and comparison forms required by this backend. [X86-FORMS](docs/X86-FORMS.md) records the
measured instruction envelope; a refusal is a failing gate, never a fallback to
another assembler. The first milestones, in order:

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

## Build and backend commands

On Linux x86-64 or macOS arm64, use Python 3.11+, curl and a native C toolchain.

```sh
tools/fetch-toolchain
tools/build-tools
tools/build
target/fenrir fir examples/hello.fir -o target/hello.fir
target/fenrir asm examples/hello.fir -o target/hello.s
target/fenrir link examples/hello.fir -o target/hello
```

The front-end views below parse source.
The tools run natively on the development host; linked output is static Linux
x86-64 ELF, not a macOS executable. The staged runtime is the matching musl
release, not the development host's runtime. See [DRIVER](docs/DRIVER.md) for
staging and exit statuses. `FENRIR_TOOLCHAIN` can name a different staged root.
Toolchain inputs and build output stay under `.wolf-bin/` and `target/`; nothing
is installed globally.

`tests/backend/fir.py` checks round-trips and named verifier rejections;
`assembly.py` checks deterministic emission; `link.py` checks process arguments,
failures and output preservation. `bash tests/backend/run-linux` also builds
Linux-native tools, measures N/10N/100N scaling and compares complete objects
with clef's GNU-as differential, then linked programs with pinned Wolf. It
stops on a failed step and prints its exit status. The full executable proof
is a separate Linux job; it is not implied by a passing Mac core gate.

The [harness](docs/HARNESS.md) records native Wolf and lupin as black boxes
against an immutable specification/corpus pin. Two complete oracle captures are
committed; their disagreements are listed, not counted as compiler coverage.
Refusals fail the differential, and coverage is computed. Run `tools/differ check`
to verify the table's freshness. The [subset inventory](docs/SUBSET.md) prints the gap
between source constructs and the empty implemented compiler subset; the
[diagnostics catalog](docs/DIAGNOSTICS.md) names the front end's syntax refusals and the backend's FIR tags.
CI builds and runs strict gates on Linux and macOS; branch pushes do not run CI.

## Front-end views

After building the driver with the pinned bootstrap toolchain:

```sh
target/fenrir --emit=tokens program.lu
target/fenrir --emit=ast program.lu
```

Both views are deterministic text. The AST is an append-only arena with a span
on every node; [the interface](docs/AST.md) documents its fields, child order,
format, coverage scope, and the corpus spellings beyond the extracted grammar.
Parsing does not imply resolution, type checking, ownership checking, or code
generation. Syntax and I/O errors return 2, never an environment skip.

## Licence

GPL-3.0-only with the wolf Training Data Permission; see `LICENSE` and
`LICENSE-TRAINING-DATA`.
