# Differential harness

## Commands

`tools/differ oracle --output FILE` records the pinned Rust wolf's native
`wolf run --no-cache -o PRIVATE_OUTPUT FILE` (native by default; `run --native`
is invalid in this release). The flags must precede FILE: otherwise they become
program arguments. The default output is inside the package's `.lu-cache/bin`,
which a read-only input correctly refuses; disabling caches and naming a private
output avoids that write. Lupin uses `conform-run --json`, once per corpus entry.
Exact argv is retained
in native observations. Every non-member also gets a `declared_phase` pair via
`conform-run --phase=PHASE` on both implementations; memory rows use their
explicit `mem` phase, never an inferred typecheck stop. Static rows compare this
pair. Run-header rows compare the raw native result against lupin's dynamic
record, with declared-phase observations retained separately.
The oracle recorder runs only on Linux x86-64 inside an isolated container;
set `FENRIR_ORACLE_SANDBOX=1` there. The environment flag is an assertion by the
container launcher, not a sandbox itself. The launcher must supply the memory
cgroup, CPU allocation and a reaping pid 1, and must not expose host process
namespaces. Each child additionally inherits a 3 GiB address-space limit.
Workers default to three; six is the maximum. A timeout is an explicit oracle
error, never a skip or agreement. Scratch directories belong to the invocation,
under `target/`; each row has a read-only copied package. Every native run,
classification call, declared-phase call and dynamic lupin call gets a separate
private cwd, HOME, TMPDIR and cache directory. No invocation inherits files left
by a previous one. Candidate builds and candidate executions are isolated too.
Before the first call the harness records the package tree's names, modes,
symlink targets and file hashes. It compares that complete listing after every
oracle invocation and aborts on any change; before/after digests and the actual
number of checked calls are retained in each row and checked for freshness.
Timed-out descendants are signalled by individually recorded pid, never a group.

A front-door status can also be a legal program exit. When native `run` returns
2 or 4 without a trap, the harness obtains a native `conform-run --json` record
to disambiguate rejection/refusal from a program that ran. It never borrows
stdout or exit status from that second invocation: contradictory outcomes remain
`tool-error`, with the failed command's raw stderr. It never treats
`wolf run --checked` as the checked machine. The Rust compiler implementation
is not read: only the pinned `spec/` and `corpus/` paths are extracted from its
source archive. The assembler and linker are independent Wolf programs.

`tools/differ check --input FILE` checks oracle-table freshness without rerunning
programs: the exact pin-file identity, reference revision, complete row census,
source byte hashes, parsed header expectations and membership, observation
relations and derived summaries. A limited `--limit N` recording is always
marked incomplete and cannot pass freshness. Run
`tools/differ reconcile --first FIRST.json --second SECOND.json --output tests/oracle.json`
after two independent recordings. It requires equal identities and source rows,
retains both observation sets, and derives a `repeat_changes` list. Freshness
requires two recordings and rechecks their stability flags. Changing rows are
identified instead of silently replacing their expectations. The committed table is evidence, not
fenrir coverage. The oracle's own disagreements are listed by file.

`tools/differ compare --input FILE` compares observations that already include
`fenrir` records. Add `--fenrir PATH` to build and execute every entry live in the
Linux sandbox. It reserves a fresh output for every build; an earlier executable
cannot stand in for a missing new output. `--output FILE` retains the JSON result.
Any verdict other than `same` makes this command fail, including refusals.

## Records

Every `.lu` source is enumerated in sorted order, including module members.
Leading `//!` headers determine `check`, `phase`, `conforms` and membership.
Members are recorded as `module-member` on both sides and are compiled through
their package entry, never independently run or silently skipped. Same-directory
entry candidates are listed; when there is exactly one, its check and phase are
retained as the member's inherited expectation. A malformed implicit member of
a refusing package is never mistaken for a valid standalone program.

Each oracle row contains the file, byte digest, directives, expected header
verdict, phase, membership, and `wolf`/`lupin` observations. Native observations
retain raw stdout as UTF-8 display text and exact base64 bytes plus SHA-256,
process exit, stderr, trap kind and source site when reported. Lupin's full
protocol object is retained, including its stdout digest/inline text, diagnostic
spans and extension fields. A missing source site or trap message is not invented.
An exiting protocol record with null output metadata denotes empty output:
protocol 1 requires the digest whenever an exiting program writes bytes. The
normalized observation uses the empty-byte digest for that case, without
changing the retained protocol object. Trap output metadata remains honest-absent.
Long output unavailable inline is represented
by the protocol's digest, not truncated text passed off as complete stdout.

Oracle relations are `same-observed`, `differs`, `scope-gap`,
`not-dynamically-comparable`, `oracle-error` or `module-member`. These describe
the observations obtainable through native `run`, not a claim of full protocol
span/warning parity: the native front door does not supply a byte-span record
for every successful run. `same-observed` compares exit or trap kind and the
stdout hashes both sides actually supply. Scope gaps and clean static stops
never count as dynamic agreement. Disagreements and tool errors are evidence
about the oracle pair; they are not fenrir successes.

Candidate verdicts are exactly `same`, `differs`, `fenrir-refuses` and
`fenrir-crashes`. Candidate comparison uses native wolf as reference and keeps
lupin's second opinion beside it. It compares stdout bytes/digest, exit or trap
kind, site and message; unavailable trap metadata is retained honestly. Status
2 at build time means `fenrir-refuses`, and 70 means `fenrir-crashes`, with ICE
precedence over any refusal label. Program exit 70 after a successful build is
a program exit, not a compiler error. Other failed builds, signals and timeouts
are crashes. An environment skip is never inferred from 2 or 70.

Coverage is computed as `same` run-header rows divided by all run-header rows;
module members and static refusal rows are separate. Zero run rows gives zero
coverage, never a vacuous 100 percent. F0 accepts no programs and claims no
coverage. Refusal parity and a complete protocol warning/span comparator are
later work, not silently counted as implemented here.

## Tests and cost

`tests/frame.py` plants unknown/stale subset rows, unsupported compiled claims,
a closed bootstrap gap, uncatalogued/unused diagnostics, byte nondeterminism,
a strict-mode skip and a refusal falsely counted as success. `tests/oracle_unit.py`
checks header membership, malformed protocol records, exact trap data, pin
corruption and ICE precedence. `tests/driver.py` invokes the actual stage-0-built
driver through every public seam and checks output preservation.

Enumeration and inventory are linear in source bytes. Linux CI runs the inventory
at N, 10N and 100N, with 100N exceeding ten times the largest real source file,
and rejects superlinear growth with a scheduling allowance. Recording costs the sum
of package-copy bytes plus the black boxes' compile/run times; no compiler pass
or analysis is implemented by this harness. All summaries derive from row data.
