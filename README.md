# fenrir

A second compiler for [wolf](https://github.com/wolffe-lang/wolf-lang),
written in wolf.

fenrir is built from wolf's specification and checked against the existing
compiler on its corpus: a program fenrir compiles must print, exit and trap
exactly as it does under the reference compiler. Its backend emits x86-64
assembly for [clef](https://github.com/wolffe-lang/clef) and links with
[ligature](https://github.com/wolffe-lang/ligature), both written in wolf, so a
program built by fenrir needs no Rust, LLVM or binutils on the way. The
runtime library, `libwolf_rt.a`, comes from the wolf release fenrir is pinned
to.

The goal is self-hosting: fenrir built by the reference compiler builds
fenrir, that build builds fenrir again, and the last two are byte-identical.

## Status

`fenrir build FILE.lu -o OUT` compiles a program in the core to a static
Linux x86-64 executable: lex, parse, check, lower to FIR, verify, emit, then clef
and ligature ([LOWERING](docs/LOWERING.md)); `fenrir run FILE.lu` builds and runs
it. The lexer and parser provide stable token and AST views, with source spans
and named syntax refusals. Name resolution and the type checker cover the
core (integers, `f64`, `bool`, `str`, `char`, `byte`, functions, `if`/`while`/`loop`,
structs and their destructuring, enums and `match`, lists, `Map`, tuples, `for`,
error rows, `defer`/`errdefer`, `never` and the `index` and `allow` attributes,
the parameter modes `mut` and `take` with `move` and `copy`, adapter types over a
`Copy` scalar, nested `fn` items that name only their own scope, and
`#[consttime(public(…))]` naming every parameter)
and print a typed view; a program outside the core is refused by name. All ten integer kinds,
checked integer casts, byte/character bridges, wrapping arithmetic, bitwise
operators and homogeneous shifts share explicit numeric-domain semantics; `f64`
arithmetic, comparison, casts to and from the integer kinds and rendering are
IEEE 754 binary64, computed in `src/sem/float.lu` with integer arithmetic only.
A type may recurse through a list or a map.
Strings include checked
byte-offset views, scalar/byte materialization, checked construction from
bytes, case conversion, formatting and direct split/words/lines iteration;
lists and byte views take open and from-end slices. Composite rendering and binding alternatives
have dedicated execution checks. Map-containing interpolation is a named
refusal, matching the native reference rather than inventing Map output.
The [live census](tests/types/census.json) identifies 423 core run rows; all
423 measure `same` natively and through the bounded interpreter, with zero
differences, crashes or refusals ([verdicts](tests/lower/core-verdicts.json)).
That is **51.97% of the released corpus's 814 run rows** (wolf 0.2.40), not whole-corpus parity.
The [latest delta](tests/types/f3c-language-delta.json) names the 46 rows the
memory model's region tier added, frozen in advance, and every changed
typing/classification observation (150); all 377 previously passing rows remain
passing. The [value-tier delta](tests/types/f3b-language-delta.json) before it
names the 87 rows `mut`, `take`, `move` and `copy` added. The [float delta](tests/types/fn09b-language-delta.json) before it names
the 15 rows the float tranche added, and the
[delta before that](tests/types/fn09-language-delta.json) names the 33 rows the
text (6), aggregate (4), attributes (7) and control (16) tranches added.
The [integer delta](tests/types/fn08-language-delta.json) before it names the
60 integer gains and two text rows that came with them.
The backend accepts typed, hand-written
[FIR](docs/FIR.md), verifies it unconditionally, prints a round-tripping text
form and emits deterministic x86-64 assembly. Its first allocator keeps every
value on the stack. [ABI](docs/ABI.md) specifies its calling and runtime boundary.
A bounded FIR interpreter executes the same instruction set, with explicit step
and byte budgets. Exhaustion is a named tool refusal, never a program trap; a
separate outcome record distinguishes refusal from a program returning 4.
This execution path does not broaden the source-language subset.

The link command invokes only staged clef and ligature. The executable proof
is qualified on Linux x86-64: each of 45 hand-written FIR programs is assembled
by clef, linked by ligature and run, and its output and exit status match the
same program in wolf source built by the pinned reference compiler. Each link
gets a 2 GiB address-space budget. The pinned linker's hello link measured
0.654 GiB sampled peak virtual memory and 0.621 GiB exact child peak RSS;
`tests/backend/link_budget.py` enforces the cap and records the linker's own
memory. The pinned assembler includes the direct
arithmetic and comparison forms required by this backend. [X86-FORMS](docs/X86-FORMS.md) records the
measured instruction envelope; a refusal is a failing gate, never a fallback to
another assembler. Numeric checks add 4,390 independently computed scalar
edge cases and a 282-case cross-domain FIR matrix on both execution engines.
Float checks add a 537-case binary64 FIR matrix and 326 float edge cases whose
answers come from the reference, both on both engines; for eight narrow-integer
casts the released Linux compiler cannot build
([wolf-lang#1160](https://github.com/wolffe-lang/wolf-lang/issues/1160)) the answer
is the one lupin, the released macOS compiler and the specification agree on.
FIR edition 5 records numeric source and target domains explicitly, and edition 6
adds the `f64` domain and list and map components that name a later shape, each
preserving every earlier type id and opcode meaning; the value tier needs no new edition. The first milestones,
in order:

| | what |
|---|---|
| F0 | the frame: pinned toolchain, continuous integration, the corpus harness and its gates |
| F1 | `hello, wolf`, compiled end to end on Linux x86-64 |
| F2 | the core language: enums, `match`, lists, `Map`, error values, strings, rendering and traps |
| F3 | the memory model, lowered as the specification states it |
| F4 | generics, traits, closures, modules; the standard library compiles |
| F5 | the fixpoint: fenrir compiles itself, byte for byte |
| F6 | refusal parity: every program the reference rejects, rejected with its code |
| F7 | full corpus parity, and fenrir running on PAX |

F2 is met: the [frozen membership](tests/types/fn08-membership.json)
and [resolved placements](tests/types/fn08-membership-placements.json) identify
290 native-comparable rows inside its language, and the census's 290 core rows
are exactly those, each `same` natively and through the bounded interpreter,
with the required string, rendering, trap and pattern checks green. The earlier
403 was an optimistic upper bound, not membership: it granted unknowns and
several later surfaces for free.
A percentage cannot pull memory-model, generic/module, foreign, comptime or
host-surface features into F2; the former half-corpus target belongs later.

F3's first piece, F3b, the value tier, is met: `mut` is value-result (a callee
hands back each `mut` parameter's final value with its result, on every return
path, and the caller writes it back to the place it lent), `take` and `move`
pass the value, and `copy` is deep by type. Its second, F3c, the region tier,
is met:
- a `region r { }` block makes its region ambient and frees it on every way out;
- a region value is entered with `in r { }`;
- a `cap:` budget traps `alloc-contract` past it;
- `region_bytes` and `live_region_bytes` read the ledger;
- a list's `reserve` and `reset` grow or keep its storage;
- a `copy` stored from inside a block into an outer value is made in that
  value's region.

Where fenrir cannot name that region it refuses the store by name rather than
place it wrong. Tagged copies select only the active enum, result or row
payload: ordinary copies keep nested containers independent, and an outward
copy re-makes reached strings before the source region is freed. The
[copy rows](tests/memory/outer_write.py) check both engines, erased unit fields
and emission growth; named native-reference copy gaps use the specification
and lupin's answer without earning native parity credit.
The bounded interpreter traps `region-fault` on a read of a
freed region's storage, a check of fenrir's own.

The two tiers' 87 and 46 frozen rows are in the core, each `same` on both
engines. The region tier's 47th row, `memory/byte_list_ledger`, is a
[named difference](tests/types/core-differences.json): fenrir stores a
`List[byte]` in 8-byte words on both engines, so its ledger cannot show the byte
width yet. [MEMORY](docs/MEMORY.md) gives each of the memory chapter's 145
clauses its run-time meaning on both engines and the piece of F3 that lowers it.
F3's [frozen membership](tests/types/f3-membership.json) places 204
native-comparable run rows by piece (87, 46, 16, 50 and 5), checked against
every blocker the census records for each row; 14 of them expect undefined
behavior and earn no parity credit, so F3 would end at 480 of 814.
The typed coverage holds every memory clause: the 75 the core now runs have
positive and negative rows, and each negative the reference refuses with a
memory-tier code fenrir does not check yet is a
[named difference](tests/types/memory-differences.json), counted and closed at F6.
The 423 do not mean fenrir refuses what the reference refuses: fenrir accepts 127
corpus programs the reference refuses.
- 43 of them came with the region tier. 41 break a region rule that fenrir
  does not check until F6 (E1010 36, E1004 3, E1011 1, E1005 1). Two are rows
  the pinned release cannot build (a region held in a container), with no code.
- 76 break a move, exclusivity or read-mode rule, also F6's (E1002 37, E1001 34,
  E1014 4, E1004 1).
- Two mutate a list while a `for` loop walks it (E1013, also checked at F6).
- Two spell one tag twice in an error row (E0601).
- Four are rows the pinned release refuses without a code although their own
  headers expect them to pass or run (a test-tier file and three or-pattern
  bindings).

The census counts each with the reference's code (`oracle-refused-fenrir-accepts`).

## Build and backend commands

On Linux x86-64 or macOS arm64, use Python 3.11+, curl and a native C toolchain.

```sh
tools/fetch-toolchain
tools/build-tools
tools/build
target/fenrir fir examples/hello.fir -o target/hello.fir
target/fenrir asm examples/hello.fir -o target/hello.s
target/fenrir link examples/hello.fir -o target/hello
target/fenrir build examples/hello.lu -o target/hello
target/fenrir interpret examples/hello.fir --steps 1000 --bytes 1048576 --report target/hello.outcome
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
stops on a failed step and prints its exit status. `run-linux proof`,
`run-linux lower`, `run-linux tranches` and `run-linux corpus-1` to
`corpus-3` run the shared builds and then one part each; the three corpus
parts are shards of the census core's native differential, each row in exactly
one. CI runs every part as its own parallel Linux job, the proof as its two
halves `run-linux proof-1` and `proof-2`, and `ci/check` fails when a step runs
in no job or in two, or when a job runs the whole proof. Every part first checks
all handcrafted oracle sources at the released typecheck phase and lowers
all expected-success lowering fixtures to verified FIR, then links one smoke
case and runs the region-scaling measurement's own path small (its small parent
and one row from each compiler, both floors printed), so a broken measurement
refuses in the first minute rather than at the proof's end. `run-linux preflight`
runs only this short readiness gate after the shared
builds; use it before a full take. It catches missing source twins and stale
successful fixtures without spending a native batch. The full executable
proof is not implied by a passing Mac core gate.

The [harness](docs/HARNESS.md) records native Wolf and lupin as black boxes
against an immutable specification/corpus pin. Two complete oracle captures are
committed; their disagreements are listed, not counted as compiler coverage.
Refusals fail the differential, and coverage is computed. Run `tools/differ check`
to verify the table's freshness. The [subset inventory](docs/SUBSET.md) prints the gap
between source constructs and demonstrated self-compilation capabilities; the
[diagnostics catalog](docs/DIAGNOSTICS.md) names the front end's syntax refusals, the checker's codes and the backend's FIR tags.
CI builds and runs strict gates on Linux and macOS; branch pushes do not run CI.

## Front-end views

After building the driver with the pinned bootstrap toolchain:

```sh
target/fenrir --emit=tokens program.lu
target/fenrir --emit=ast program.lu
target/fenrir --emit=typed program.lu
```

All three views are deterministic text. The AST is an append-only arena with a span
on every node; [the interface](docs/AST.md) documents its fields, child order,
format, coverage scope, and the corpus spellings beyond the extracted grammar.
Parsing does not imply resolution or type checking. The typed view
([its interface](docs/TYPED.md)) resolves every name to a numbered declaration
and types every expression of the core; it does not check ownership or
generate code. Syntax, type and I/O errors return 2, a program outside the
core returns 4, and neither is an environment skip. `tools/census check`
recomputes the corpus census and its gate, records every construct outside
the core that each row meets, holds F3's frozen membership to those blockers
in both directions, and keeps current the
[list of rows](tests/types/scope-model-gap.json) where the census's scope model
and the checker name a row's first refusal differently.

## Licence

GPL-3.0-only with the wolf Training Data Permission; see `LICENSE` and
`LICENSE-TRAINING-DATA`.
