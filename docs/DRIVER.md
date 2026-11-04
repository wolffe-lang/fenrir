# Driver interfaces

`src/main.lu` owns command-line dispatch. Front-end token/AST views accept valid
source and return 2 for syntax or I/O errors. Backend module entries remain
refusal-only stubs until implemented.

| Invocation | Module entry |
|---|---|
| `fenrir --emit=tokens FILE.lu` | `front.emit(path: str, mode: str) -> int`, mode `tokens` |
| `fenrir --emit=ast FILE.lu` | `front.emit(path: str, mode: str) -> int`, mode `ast` |
| `fenrir asm FILE.fir -o OUT.s` | `x86.assemble(path: str, output: str) -> int` |
| `fenrir fir FILE.fir -o OUT.fir` | `x86.canonical(path: str, output: str) -> int` |
| `fenrir link ARGS...` | `x86.link(args: List[str]) -> int` |

Replace the implementation of a module entry without changing main's dispatch.
`src/front/` owns lexing, parsing and AST text. `src/fir/` owns FIR and its
always-on verifier; `src/x86/` owns assembly emission and backend driver entries.
`src/sem/` is reserved for the shared semantics table. No optimizer is enabled.
Future `build FILE.lu -o OUTPUT` and `run FILE.lu` are reserved and refuse today.
AST, FIR and ABI details belong in their respective interface documents.

| Status | Meaning |
|---|---|
| 0 | Success |
| 2 | Refusal, including syntax, type, I/O and not-built-yet diagnostics |
| 70 | Internal compiler error |
| 77 | Test environment cannot run a row; never a compiler refusal |

The differential harness treats 70 and signals as `fenrir-crashes`, 2 as
`fenrir-refuses`. Strict mode prints every skip to stdout and fails on it;
neither 2 nor 70 can be skipped.

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
