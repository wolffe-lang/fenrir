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

## Initial change record

This interface precedes its implementation and type-checker consumers. It adds
no source-language acceptance by itself and changes no FIR instruction.
