# Driver interfaces

`src/main.lu` owns command-line dispatch. Front-end token/AST views accept valid
source and return 2 for syntax or I/O errors. The typed view returns 2 for a
syntax, resolution or type rejection and 4 for a program outside the F1 core.
Every command that compiles source enters through `types.load`, which reads,
parses, refuses a program of several files and checks, and returns the status
those refusals carry. The backend implements `fir`, `asm` and `link FILE.fir -o
OUTPUT`. A source file inside the F1 core is compiled by `build`, `run` and
`--emit=fir|asm`: `types.load`, then lower, verify, emit, and for `build` and
`run` clef and ligature (`docs/LOWERING.md`). A command reports a refusal rather
than silently selecting another compiler.

| Invocation | Module entry |
|---|---|
| `fenrir --emit=tokens FILE.lu` | `front.emit(path: str, mode: str) -> int`, mode `tokens` |
| `fenrir --emit=ast FILE.lu` | `front.emit(path: str, mode: str) -> int`, mode `ast` |
| `fenrir --emit=typed FILE.lu` | `types.emit(path: str) -> int`, over `types.load(path: str) -> Source` |
| `fenrir asm FILE.fir -o OUT.s` | `x86.assemble(path: str, output: str) -> int` |
| `fenrir fir FILE.fir -o OUT.fir` | `x86.canonical(path: str, output: str) -> int` |
| `fenrir link ARGS...` | `x86.link(args: List[str]) -> int` |
| `fenrir build FILE.lu -o OUT` | `lower.build(path: str, output: str) -> int` |
| `fenrir run FILE.lu` | `lower.run(path: str) -> int` |
| `fenrir --emit=fir FILE.lu` | `lower.emit(path: str, mode: str) -> int`, mode `fir` |
| `fenrir --emit=asm FILE.lu` | `lower.emit(path: str, mode: str) -> int`, mode `asm` |

Replace the implementation of a module entry without changing main's dispatch.
`src/front/` owns lexing, parsing and AST text. `src/resolve/` owns the F1
core's scope check, declarations and name resolution, and `src/types/` the type
checker and the typed text form (`docs/TYPED.md`). `src/fir/` owns FIR and its
always-on verifier; `src/x86/` owns assembly emission and backend driver entries.
`src/lower/` owns the lowering and the source commands. `src/sem/` defines the
shared integer kinds (width, signedness, range), literal rules, string decoding
and integer-operation classification. No optimizer is enabled. `build` writes a
static Linux x86-64 executable and preserves an existing output on any failure;
`run` builds into a private directory under `TMPDIR`, runs the program with
fenrir's stdout and stderr, removes the directory, and exits with the program's
status (128 + N for a signal N). A successful build prints nothing, so under
`run` both streams carry only the program's bytes. `--emit=fir` and `--emit=asm` print the
verified FIR text and the assembly, each byte-identical across runs. AST, FIR
and ABI details belong in their respective interface documents.

| Status | Meaning |
|---|---|
| 0 | Success |
| 2 | Rejection: a syntax, resolution, type or I/O diagnostic (`[conf.exit.static]`), or a tool that could not do the job (a link failure) |
| 4 | Refusal: the program is outside what fenrir implements, F0001, F0002, or F0003 for a build with no `main` (`[conf.exit.refused]`) |
| 70 | Internal compiler error |
| 77 | Test environment cannot run a row; never a compiler refusal |

The differential harness treats 70 and signals as `fenrir-crashes`, 2 and 4 as
`fenrir-refuses`. Strict mode prints every skip to stdout and fails on it;
none of 2, 4 or 70 can be skipped.

## Build and staging

Python 3.11+, curl and a native C toolchain are needed. `tools/fetch-toolchain`
stages immutable, twice-digest-checked inputs under `.wolf-bin/`: `wolf`,
`lupin`, `std`, `reference/{spec,corpus}`, `clef/`, `ligature/`, `bundle/`
and `musl/libwolf_rt.a`. The assembler and linker paths contain pinned source;
`tools/build-tools` compiles their executables as `.wolf-bin/bin/{clef,ligature}`
on the development host (Linux x86-64 or macOS arm64). Runtime bytes are from the matching 0.2.36 musl release.
`tools/build [-o OUTPUT]` uses only `.wolf-bin/wolf` and the bundled std;
the default output is `target/fenrir`. It does not accept a PATH compiler.
Nothing is installed globally. macOS builds the front end with stage 0; fenrir's
output target is Linux x86-64 and PAX, not Mach-O.
