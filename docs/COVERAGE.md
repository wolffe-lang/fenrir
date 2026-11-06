# Pattern coverage kernel

The `coverage` module is a symbolic Boolean decision-diagram kernel for the
type checker's exhaustiveness and usefulness analysis. It never evaluates a
program, reads an enum payload, or rewrites executable FIR. The producer maps
typed patterns and their valid value domain to predicates; usefulness is
`pattern AND NOT covered`, and an unguarded arm extends `covered` by union.
Guards do not extend coverage.

## Interface

Roots are dense integer ids. Root 0 is false (empty), root 1 is true. Other
roots are reduced, ordered binary decision nodes with a nonnegative integer
variable id and low/high roots. Variables are ordered by id. The producer
assigns ids deterministically from semantic field paths, with enum tags before
payload paths. The kernel knows Boolean variables, not language type names.

```text
pub error Failure = {Limit(str, int, int), Internal(str)}
coverage.create() -> State
coverage.create_limited(cells: int, bytes: int) -> State ! Failure
coverage.charge(mut state: State, cells: int, bytes: int) -> () ! Failure
coverage.literal(mut state: State, variable: int, value: bool) -> int ! Failure
coverage.equal_bits(mut state: State, first: int, width: int, value: u64) -> int ! Failure
coverage.less_bits(mut state: State, first: int, width: int, value: u64) -> int ! Failure
coverage.both(mut state: State, a: int, b: int) -> int ! Failure
coverage.either(mut state: State, a: int, b: int) -> int ! Failure
coverage.invert(mut state: State, root: int) -> int ! Failure
coverage.difference(mut state: State, a: int, b: int) -> int ! Failure
coverage.witness(mut state: State, root: int, variables: int) -> List[int] ! Failure
```

`State` exposes `cells` and `bytes`, the consumed accounting totals. Its other
fields are implementation-owned. `create` uses the fixed limits below;
`create_limited` exists for tests and may only lower them. Invalid arguments or
an invalid root are `Internal`, never a coverage result.

Bit-vector variables are `first .. first + width`, most significant bit first;
width is 0 through 64. `equal_bits` compares to the supplied unsigned value;
a value outside a shorter width is false. `less_bits` means unsigned `< value`;
a bound at or above the domain's size is true. The producer handles a bound
above u64's maximum before calling it. A zero-bit vector has only value 0.
`witness` requires a nonempty root and returns one entry per variable: -1 for
unconstrained, otherwise 0 or 1. It takes the low edge whenever that edge is
nonempty, so the result is deterministic. Its allocation and visits are charged.

## Limits and failure

Each function starts a fresh state with **1,000,000 examined/emitted pattern
cells** and **64 MiB (67,108,864 bytes) of logical analysis storage**. The
producer charges its pattern visits and analysis-owned paths, predicates,
warnings and witnesses through `charge`; the kernel charges decision nodes,
unique-table and memo entries/probes, and worklist storage. Already-held syntax
and ordinary typed input tables are not analysis storage.

Accounting uses fixed logical sizes, not host allocator sizes: an integer word
is eight bytes. Array capacity and metadata are charged before allocation.
Storage accounting is monotone, including replacement capacity; no refund can
make behavior depend on host collection. The empty state costs 512 logical
bytes. Exact node/table/work-frame costs are documented beside their definitions.
Cell checks precede storage checks. On a charge that would exceed a limit,
consumed totals do not advance and the state remains failed. `Limit` carries
which cap (`cells` or `storage`) and both consumed totals, including constructor
failure. No operation may return an ordinary root after failure.

The type checker converts `Limit` to **F0004, status 4**, naming the function,
which cap ran out and the counters. It must never convert exhaustion to E0801,
an empty predicate, or assumed exhaustiveness. `Internal` is status 70.

## Algorithm and cost

Hash-cons nodes and memoize Boolean operations using owned, open-addressed
integer-keyed tables, never the runtime Map or a linear-scan stand-in. Use an
explicit reusable worklist, not host recursion, for Boolean operations and
witness extraction. Equal branches reduce to one root. No whole-function
coverage recomputation occurs per arm; the producer extends its current root.

Complexity is input plus the analysis work actually explored. General products
and alternatives can encode Boolean DNF tautology, so input-linear worst-case
analysis is not promised. Deterministic work/storage limits bound that case.
Ordinary linear-family scaling and adversarial refusal/determinism rows are
both required. The largest observed corpus and fixture function counters are
reported against both limits; intentional budget fixtures are identified,
not silently excluded from the maximum.

## Kernel tests

`python3 -I tests/types/coverage_api.py` compiles an external consumer and runs
finite algebra/limit checks plus an eight-pair Boolean-product DNF. It enumerates
all two-variable truth functions and every pair of those functions, checks
unsigned predicates through 64 bits, and checks deterministic witnesses.
Each execution runs twice and its complete output must agree.

`--bounded` additionally runs the 10/100/1,000/10,000-variable worklist family
and a 24-pair DNF prefix that exhausts a cap before its final wildcard. The
work-family gate allows at most 18 times the examined cells per tenfold input
increase and separately checks reuse of a memoized deep complement. These
rows run only on Linux, with 2 GiB address-space, 30-second CPU and 60-second
wall limits on each child. macOS never drives a cap-exhausting or large-memory
row: its address-space resource limit is unavailable. Cross-platform evidence
instead compares the exact counters of the small eight-pair DNF, which uses
less than 1 MiB of logical storage. This separates deterministic counting from
safely forcing deterministic refusal.

The kernel's `Limit` is not itself a source diagnostic. Producer integration
must still supply the function name and F0004/status 4 boundary, and rerun the
same principles through real source patterns. Kernel greens alone do not
claim source-language acceptance or corpus headroom.

## The producer

The type checker (`src/types/exhaust.lu`) runs one state per function, after
the function's types and literal values are solved, over its matches in
source order. It maps each arm to a predicate over variables it assigns from
value paths (the scrutinee, a struct field by index, a variant's payload by
position). Ids descend from 2^40 in first-encounter order, so a test on a
fresh path sits above every earlier variable and joins the arms before it in
constant work:

- an enum tag is a bit vector of the smallest width holding its variants, held
  below the variant count by a domain predicate conjoined into `valid`;
- a `bool` is one variable;
- each distinct `str` literal on a path is one variable, and each distinct
  integer interval (a literal is the interval of one value) is one variable.
  These columns are infinite: their predicates are positive, so no set of
  them completes a column without a `_` or binder arm (`[gram.pat.range]`).

An integer test is the conjunction of its own variable and the variable of
every range on the same path that contains it, which reports an arm inside one
earlier literal or range (E0802) and stays silent for an arm covered only by a
union of several. Ranges of more than one value are indexed per path after a
first pass: sorted by low bound, with a segment tree of the maximal high bound,
so finding a test's k containing ranges among R costs O((k + 1) log R). Equal
literal and one-value range tests share one variable.

Each arm's predicate is conjoined with `valid`. An arm whose union with the
covered set is unchanged (diagrams are canonical, so that is root equality)
is E0802; only unguarded arms extend the covered set; `valid` minus the covered
set, if nonempty, is E0801 at the `match`. The producer charges a cell per
pattern visit and per index comparison, and its keys, intervals and warnings
by size. At 4,000 arms the measured cost is about 52 cells per arm for `str`
or integer literals, 56 for struct fields, and 133 to 137 for disjoint ranges
and enum variants, so a single match of roughly 7,000 (ranges, variants) to
19,000 (literals) arms reaches the cell cap. `tests/types/analysis.py`
holds five families to the 18-times ceiling at 40, 400 and 4,000 arms, drives
F0004 from source on Linux, and reports every typed corpus row's and pattern
fixture's counters against both caps.

## Initial change record

This interface precedes its implementation and type-checker consumers. It adds
no source-language acceptance by itself and changes no FIR instruction.
