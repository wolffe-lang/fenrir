## Prediction

A small typed FIR with block parameters and block-local SSA can be verified in
linear time with no dominator pass. Printing, parsing and printing again is a
byte fixed point. A stack-everything allocator assigns each value once, so
N/10N/100N rows grow linearly in work and output. Every emitted `.s` assembles
with clef to the same object GNU as produces. Checked arithmetic, branches, calls,
structs, `str` and `List[int]` programs written by hand in FIR print, exit and
trap (kind and site) exactly as the same programs do under the pinned wolf. The
predictions were committed first in `ddbd507` (`tests/backend/predictions.txt`).

Footprint: cross-cutting

## Forbidden

No reference-compiler source was read: no compiler crate, and no binutils, LLVM
or GCC source. The references are the wolf specification at `5f1f1c94`, the
runtime's public `extern "C"` signatures and their doc comments, the Intel SDM and
the System V AMD64 psABI. clef and ligature are invoked as tools. GNU as 2.42 is
used only as a binary oracle through clef's own comparator. No fallback assembler
or linker exists, and no refusal or skip counts as a pass. Wolf source does not
compile yet: this PR is the backend only, fed by hand-written FIR. The plant
branch has no PR, and branch pushes do not run CI.

## Inputs verified

- Rebased onto trunk `8cdf680`, which holds the frame and the front end.
- Pinned wolf 0.2.36 and its musl `libwolf_rt.a`; clef `900bdf0a`; ligature
  `c8ca1be4` with the licensed musl link bundle; specification `5f1f1c94`.
- The initial instruction-form census used clef `0ef3d84a` and is kept distinct
  from the current pin (`314c217`).
- Where the specification and the runtime disagree: `[type.char]`/`[type.byte]`
  say every sub-word scalar crosses the runtime seam widened to `i64`, but the
  public bool hooks take `i8`. fenrir follows each hook's prototype; see R-fn02-2
  and wolf-lang#1036.
- The rebase met the front end in four documents and nowhere in code. Both sides
  are kept whole: `docs/DIAGNOSTICS.md` (front-end codes, then a backend tag
  section), `docs/DRIVER.md`, `README.md`, and `docs/SUBSET.md`, whose inventory
  counts were recomputed over the combined source by `tools/check-subset
  --inventory`, never by hand. The front end's own gate, `ci/check`, is green over
  the backend on both platforms (records below), including its driver row, which
  expects the backend commands to refuse a `.lu` input with status 2, a `fenrir:`
  report and the existing output untouched.

Commits:
- `ddbd507`, `60bb04a`: predictions, then the FIR and ABI contracts with refusal-first rows.
- `094ad1b`, `be863b4`, `ab86d40`: typed FIR parser, printer and mandatory verifier; the `fenrir fir` command; public API.
- `a4e61ab`, `305c03c`, `956c36b`, `cb54c5b`: checked x86-64 emission with stack value slots, linear and clef-supported forms only.
- `394d46c`, `ab49fe5`, `314c217`, `a2e7de5`: the instruction-form census and its Linux GNU-as parity.
- `d7ceb09`, `56ef099`: link argument isolation and output preservation, then `fenrir link` through staged clef and ligature.
- `61dbd4e`, `e6c0cab`, `ac02373`, `77f3cb8`: scaling at three sizes, frame and resource bounds, parallel copies, child memory caps.
- `e6d6a53`, `fc2cfcc`, `64cce7e`: the Linux qualification batch, separate core and native-proof CI jobs, a bounded batch budget.
- `b9aea6d`, `6321a43`: subset inventory and README.
- `bcf5b5a`, `f1c332c`, `8aab61b`: bool runtime hooks, structured step records, the spec-wording issue draft.
- `1fdfdd1`, `31d0969`: the comparator honours clef's mapping contract (`{}` is equal); planted text-byte and equal-object controls, both red under the old classifier.
- `f06494e`: the frame's `fenrir:` prefix kept on backend tags; integrated driver row.
- `35e3cba`, `c42fdb0`: the oracle twins print through string interpolation (the pinned `print` takes only `str`), and list-bounds indexes at run time (a negative literal subscript is a compile error, E0209).
- `10bb454`: a failed verifier row prints `FAIL <row>` before its traceback.
- `49515d9`: the backend tag report form, `fenrir: TAG MESSAGE`, stated beside the front end's source report form.
- `8d7cd66`: each link runs under its own measured address-space budget, with a starved-budget control.
- `9036f02`: the native proof keeps its 6 GiB soft cap; only the hard limit rises, for links.

## Evidence index

Final head: `9036f023e9922a548aa1e337e0522d92bef5811c`.

- [x] Verifier: 33 rows. 31 broken-FIR kinds are refused by name with exit 2 and the
  output untouched: `FIR_SYNTAX`, `FIR_OPCODE`, `FIR_TYPE`, `FIR_DOMINANCE`,
  `FIR_TERMINATOR`, `FIR_BRANCH`, `FIR_CALL`, `FIR_LITERAL`, `FIR_TRAP`, `FIR_SITE`
  and `FIR_LAYOUT`.
- [x] Text form: the two round-trip rows print, parse and print to the same bytes.
- [x] Assembly: 21 fixtures, each emitted twice and byte-identical.
- [x] clef gate (Linux): every fixture's `.s` assembles with clef, and clef's object
  differential against GNU as 2.42 is empty. All 640 census forms agree with GNU as
  (640/640); the named narrow-relocation form stays refused.
- [x] Link: `fenrir link` through clef, ligature, the musl runtime and the licensed
  sysroot; each fixture is linked and relinked, and relinking is byte-identical;
  argument isolation, refusal and output preservation rows.
- [x] Link memory: each link runs under its own 10 GiB address-space budget, set with
  `setrlimit` in the link's child and inherited by clef and ligature. The reason is
  wolffe-lang/ligature#32: one static link of the 46 MB musl runtime needs more than 6 GiB.
  - Measured on Linux x86-64, nine successful links of hello and `str`: ligature peaks at
    7.18 to 7.36 GiB of address space (7.07 to 7.26 GiB resident, one thread).
    `ligature verify` peaks at 4.7 to 4.9 GiB, and fenrir and clef stay under 7 MB.
  - Under 6 GiB the link itself aborts, and `verify` never starts.
  - The budget is the 7.36 GiB peak plus 36% headroom, rounded up to 10 GiB. Linked under
    8 GiB twice and under 10 GiB: 29.0, 29.4 and 29.5 s.
  - CI keeps every other process at the 6 GiB soft limit. The hard limit is the link
    budget: `prlimit --as=6442450944:10737418240`. The Linux record below ran under exactly
    that (`inherited_soft=6442450944 inherited_hard=10737418240`).
  - A starved control links hello under 16 MiB and must fail by status, with no output and
    fenrir's `FIR_LINK` report. Measured, a starved link aborts promptly at every cap
    tried: 0.2 s at 16 MiB, 0.4 s at 64 MiB, 1.5 s at 256 MiB, 17.3 s at 1 GiB and 27.8 s at
    2 GiB, each with status 2. In the record: `PASS link-starved-budget status=2`, 0.155 s.
  - The 180 s timeout per link still ends a hang. In this record the 42 links (each fixture
    linked and relinked) took 42.2 to 50.4 s each.
- [x] F1 proof (Linux x86-64): hello, bool, add/sub/mul/div/rem, overflow on
  add/sub/mul, div-zero, MIN/-1 for div and rem, list push/index/len, list bounds,
  `str` concatenation, struct, struct passed and returned, `while`, a parallel-copy
  swap, calls with arguments. stdout, exit status and the complete trap report
  (`wolf-trap: KIND` and `  at FILE:LINE:COL`) equal the pinned wolf's, byte for byte.
- [x] Scaling: `fir` and `asm` at N/10N/100N (N = 1000), median of three runs, with
  time, output bytes and child peak memory; each tenfold step stays within 18x time
  and 12x bytes. Linux only: here inside the 12 GiB container, in CI under a 6 GiB
  address-space soft cap. Measured: `asm` output 42,538, 438,293 and 4,575,798 bytes; 0.013,
  0.022 and 0.173 s; child peak 14.6, 16.6 and 153.1 MB.
- [x] Oracle preflight (macOS arm64): all 21 wolf twins build (exit 0) and match
  their expected output or trap before any Linux take.
- [x] The front end's gate (`ci/check`) over the backend: macOS and Linux.
- [x] Strict skip checks on every step: zero skips.
- [x] Seen red first: CI run 41832511040 at `49515d9` linked under the old whole-job
  6 GiB limit, and all 21 links aborted with `memory allocation of 65536 bytes failed`
  (SIGABRT). A link of hello under a 6 GiB `setrlimit` aborts the same way on a local
  Linux host.
- [ ] PAX under QEMU: not run (R-fn02-3).

Test targets at the final head:
- [x] macOS arm64: `bash ci/backend-core`, 12 steps, `worst=0`.
- [x] macOS arm64: `bash ci/check`, the front end's gate over the backend, 17 steps, `worst=0`.
- [x] macOS arm64: all 21 wolf twins build (exit 0) and match before any Linux take.
- [x] Linux x86-64: `prlimit --as=6442450944:10737418240 bash tests/backend/run-linux`, 13 steps, `worst=0`.
- [x] Linux x86-64: `bash ci/check --oracle`, 20 steps, `worst=0`.
- [x] The plant `fn02-plant-site-unchecked`, red by name (`reject-site`).
- [ ] CI on this head: `backend` (core on ubuntu-24.04 and macos-15, then linux-proof) and `ci`.

Rulings, all seven accepted:
- **R-fn02-1, FIR interpreter: recommend one in F2, as a test-only second oracle.**
  The options were (a) a small interpreter behind the same verifier, (b) the native
  differential alone, or (c) deferring the choice. Every native row costs an
  assemble, a link (about 29 s here) and a run on Linux, and a lowering bug and a backend
  bug look the same there. An interpreter over FIR's 23 ops runs anywhere, in
  milliseconds, and splits them. It must render traps exactly as the runtime does
  and is never a fallback. Not built here; the item is optional for F1.
- **R-fn02-2, bool at the runtime seam: follow each hook's `i8` prototype.** The
  emitter passes canonical 0/1 with zero upper bits, which satisfies both readings.
  The spec wording is tracked in wolf-lang#1036, drafted in
  `notes/fn02/spec-issues/01-bool-runtime-widening.md`.
- **R-fn02-3, PAX: defer to the milestone that links for PAX.** `fenrir link` targets
  the musl Linux runtime and static ELF. PAX links with its own runtime and linker
  script, a profile this backend does not emit. F1 is proven on Linux x86-64 only.
- **R-fn02-4, allocator: stack-everything for F1, named as such.** Each value gets
  its words once, linear in values and aggregate words (`docs/ABI.md`). Register
  allocation is a later lane's.
- **R-fn02-5, report forms: scope each section to its own form.** The front end's
  catalog states one form for every report, `FILE:LINE:COL: error[CODE]: …`; FIR
  text has no source span, so backend reports are `fenrir: TAG MESSAGE`. The backend
  section states its own form (`49515d9`); the front end's sentence is scoped to
  source diagnostics in a later front-end change.
- **R-fn02-6, diagnostic numbering: follow the reference.** The pinned wolf reports a
  negative literal subscript as E0209, and the front end uses E0209 for nesting
  past 256. Refusal parity needs the reference's numbering, so the front end's
  nesting-depth code moves in a front-end follow-on. Nothing is renumbered here.
- **R-fn02-7, README: a one-commit follow-up at the merge.** The status line about
  the executable proof not being qualified is updated then, so this head and its
  records stay as they are.

Linux final record END lines (x86-64, 12 GiB container on six CPUs, under the workflow's
`prlimit --as=6442450944:10737418240`):
```text
END fetch exit=0 secs=29
END comparator exit=0 secs=1
END build exit=0 secs=1
END driver exit=0 secs=0
END build-tools exit=0 secs=3
END fir exit=0 secs=0
END assembly exit=0 secs=0
END link-boundary exit=0 secs=0
END scaling exit=0 secs=2
END fetch-gas exit=0 secs=3
END before-form-census exit=0 secs=2
END form-differential exit=0 secs=6
END linux-proof exit=0 secs=1925
RECORD-END worst=0 steps=13 end=2026-11-04T17:11:05Z
```

Linux record of the front end's gate over the backend (`ci/check --oracle`):
```text
END unit exit=0 secs=2
END oracle-unit exit=0 secs=0
END oracle-readonly exit=0 secs=0
END inventory-scaling exit=0 secs=5
END subset exit=0 secs=0
END diagnostics exit=0 secs=0
END build exit=0 secs=1
END toolchain-tools exit=0 secs=3
END driver exit=0 secs=0
END front-unit exit=0 secs=0
END front-grammar exit=0 secs=2
END front-coverage exit=0 secs=0
END front-unicode exit=0 secs=0
END front-record-output exit=0 secs=1
END front-api exit=0 secs=0
END front-corpus exit=0 secs=20
END front-capped-stress exit=0 secs=11
END determinism exit=0 secs=2
END strict-skips exit=0 secs=0
END oracle-freshness exit=0 secs=0
RECORD-END worst=0 steps=20 end=2026-11-04T17:11:52Z
```

macOS arm64 final record END lines (`ci/backend-core`):
```text
END comparator exit=0 secs=0
END frame-unit exit=0 secs=1
END oracle-unit exit=0 secs=0
END build exit=0 secs=1
END build-tools exit=0 secs=1
END driver exit=0 secs=0
END fir exit=0 secs=0
END assembly exit=0 secs=1
END link-boundary exit=0 secs=0
END subset exit=0 secs=0
END diagnostics exit=0 secs=0
END determinism exit=0 secs=1
RECORD-END worst=0 steps=12 end=2026-11-04T15:21:22Z
```

macOS arm64 record of the front end's gate over the backend (`ci/check`):
```text
END unit exit=0 secs=1
END oracle-unit exit=0 secs=0
END oracle-readonly exit=0 secs=0
END subset exit=0 secs=0
END diagnostics exit=0 secs=0
END build exit=0 secs=1
END toolchain-tools exit=0 secs=1
END driver exit=0 secs=0
END front-unit exit=0 secs=1
END front-grammar exit=0 secs=1
END front-coverage exit=0 secs=0
END front-unicode exit=0 secs=0
END front-record-output exit=0 secs=0
END front-api exit=0 secs=1
END front-corpus exit=0 secs=23
END determinism exit=0 secs=1
END strict-skips exit=0 secs=0
RECORD-END worst=0 steps=17 end=2026-11-04T15:21:52Z
```

Plant: `fn02-plant-site-unchecked` at
`e50a548e762eade3ecad330a0969996040726f51`, one commit, one file, one hunk on the
final head. It drops the verifier's upper bound on an instruction's site index, so
an instruction with no site in the table is accepted. Red by name:
```text
PLANT base=9036f023e9922a548aa1e337e0522d92bef5811c branch=fn02-plant-site-unchecked
PLANT-ROW reject-site
END build exit=0 secs=1
FAIL reject-site expected FIR_SITE status=0
END verifier exit=1 secs=0
END record-wrapper exit=1 secs=0
RECORD-END worst=1 steps=3 end=2026-11-04T15:26:51Z
```

## Done-when

FIR, its text form and its always-on verifier; the ABI and runtime boundary; the
x86-64 backend with its clef gate; the link; and the F1 proof programs are
implemented and green at the head, locally on Linux x86-64 and macOS arm64, with
the plant red by name. CI runs the core gate on both platforms and the native proof
on Linux. The audit and CI are the merge checks. Nothing is merged, labelled,
tagged or closed here.

