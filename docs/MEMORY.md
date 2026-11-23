# The memory model, lowered

This document is the F3 design: what each clause of the memory chapter means
when fenrir runs a program, on both execution engines (native x86-64 through
clef and ligature, and the bounded FIR interpreter), and which piece of F3
lowers it. It is written before any F3 lowering and is the reference the F3
units implement and the coverage rows check.

Sources: Wolf `spec/02-memory-model.md` and `spec/anchors.json` at reference
revision `b333b9da` (the pinned specification interface), `spec/04-abi.md`
for the C membrane, `spec/09-constant-time.md` for the one attribute named
below, and the pinned corpus. Runtime entry points are named from the symbol
index of the pinned musl `libwolf_rt.a` (297 `__wolf_rt_` names) and are
settled by linked probes against the released archives, never by reading
runtime source or its documentation. The released `wolf` and `lupin` are
black boxes. No compiler, runtime or interpreter source was consulted.

## What F3 is, and what it is not

F3 builds the run-time meaning of the memory chapter. The static rules of the
chapter (the E1xxx refusals: use after move, exclusivity, escape, edges,
freezing, raw-tier rings) are F6's: an F3 unit lowers the programs those
rules accept, and writes each clause's negative row now, with the reference's
code and site, so F6 inherits it. Until F6 fenrir accepts what those rows
refuse; every such row is a **named difference** (below), counted, and a row
fails when its difference closes.

Not lowered at F3: `shared T`, `weak T` and user destructors
(`[mem.shared.rc]`, `[mem.shared.drop]`). No native-comparable corpus run row
needs them, and a destructor is a trait impl (F4). They stay named F0001
refusals. A proc's own region (`[mem.region.proc]`) and a cap breach inside a
proc (`[mem.region.cap.3]`) need the scheduler and are F7's. The trait and
`dyn` clauses (`[mem.iter.trait]`, `[mem.iter.impl]`, `[mem.str.impl]`,
`[mem.dyn.unsize]`) are F4's.

## Design choices every unit implements

1. **`mut` is value-result.** A `mut` argument names a place. The caller
   evaluates the place's operands once, left to right, before the call
   (`[mem.model.order]`, `[mem.tier0.excl.4]`), and passes the place's
   current value; a list or map passes its handle, never a copy. A callee
   with `mut` parameters returns a FIR struct of its result (when it has
   one) and each `mut` parameter's final value, on **every** return path:
   the tail, an early `return`, `?` and an error return
   (`[mem.tier0.mode.mut]`). The caller writes each value back to its place
   in parameter order, re-walking the already-evaluated path, then takes the
   result. Under `[mem.tier0.excl.1]` nothing else can observe the place
   during the call, so this is observably the same as passing by reference.
   It keeps `[mem.model.place.rhs]` and fenrir's opaque list and map
   handles, and it lives in `src/lower`, so both engines run the same
   convention (no FIR edition). A `mut` receiver of a list or map method
   (`(mut xs).push(v)`) changes the storage its handle names. This replaces
   the first plan, a caller temporary passed by address: the two are
   observably the same under `[mem.tier0.excl.1]`, and returning the values
   needs no new FIR.
2. **`take` moves, `read` lends.** A `take` argument passes the value and the
   caller's place becomes uninitialized (`[mem.tier0.move.1]`); a plain
   argument passes the value read-only. Neither needs a run-time flag: a
   moved place has **no run-time representation** of being moved. Its reads
   are E1001 (static, F6) on the reference; fenrir does not track them.
3. **`copy` is deep, by type** (`[mem.tier0.move.3]`). A `List` copies its
   elements, a `Map` its entries, a struct, tuple or enum its fields and
   payloads, each by the same rule; a `str` shares its immutable bytes; a
   scalar is its own copy. Copies allocate in the ambient region. fenrir
   emits the copy by type. The runtime's `__wolf_rt_list_copy` and
   `__wolf_rt_map_copy` are used only where a probe shows the depth they copy
   to; otherwise fenrir walks the value itself.
4. **A region is the runtime's region handle and nothing more.** Region
   identity is static (`[mem.region.create.4]`). On the native engine a region
   value is the handle `__wolf_rt_region_new` returns; allocations land in the
   ambient region, which only `__wolf_rt_region_ambient_enter` and `_leave`
   move (lists the runtime allocates go there, so a fenrir-emitted arena is no
   substitute). The interpreter models the same handle as an index into a
   table of regions, each with its ledger, its cap and whether it is freed.
   The open, suspended and frozen states come with the units that check them.
5. **A region dies as a unit.** A sugar block's region is freed at its exit,
   on every path out (`return`, `break`, `?`). The clause frees a first-class
   region value at its last use (`[mem.region.intra.2]`). fenrir has no
   liveness before F6, so it frees a `let`-bound value at the end of its
   binding's block, and only when every use of the binding lends it (an `in`
   block, a plain argument). Any other region value is never freed. This is a
   named difference closing at F6. No row can see it, since nothing reads a
   region after its block. The released native compiler never frees
   first-class regions (wolf-lang#1092). A `copy` stored from inside a block
   into an outer value is made in the outer value's region
   (`[mem.region.outer-write]`; docs/LOWERING.md). fenrir names that region
   statically and refuses by name a store whose container it cannot name, so
   nothing is placed in a region that dies first. The interpreter poisons a
   freed region's storage and traps `region-fault` on a read of it, so a
   placement fault shows on the Mac as it would natively.
6. **The ledger is relational.** `region_bytes` and `live_region_bytes` are
   accounting surfaces whose units are each engine's own
   (`[mem.region.account.1]`). The interpreter keeps a ledger whose charging
   rule mirrors the runtime's as observed (element bytes by FIR type, growth
   history kept; docs/FIR.md), so every relational fact the corpus prints
   (grew, stable, reclaimed, at the cap) holds on both engines. Raw ledger
   numbers are never comparison surface. One relation does not hold yet: a
   `List[byte]` is stored, and charged, in 8-byte words on both engines, so its
   ledger cannot show the byte width (`corpus/memory/byte_list_ledger.lu`, a
   named difference until one width-1 layout lands).
7. **Memory class is measured, not assumed.** "Identical in RSS class" means:
   the child's peak RSS at N, 10N and 100N, measured by `wait4` from a small
   parent with the floor (an empty program's peak) stated; the class
   (constant or linear, by the 10N to 100N ratio) equal to the reference's on
   the same source; fenrir's 100N peak within twice the reference's. Where the
   reference is defective (wolf-lang#1092) fenrir is held to the clause's class
   and the row is listed.
8. **Tier 3 is ordinary memory.** A raw pointer is an address word; a raw
   access is one load or store at the pointee's natural alignment, a packed
   field at the alignment its offset guarantees (`[mem.unsafe.raw.4]`); a
   volatile access is exactly one access of its width
   (`[mem.unsafe.volatile.2]`). A `var` is writable data and a `const` its
   value (`[mem.static]`). C calls go to the licensed musl bundle through
   ligature. The interpreter models each raw allocation as a byte array with
   a provenance id inside its byte budget; a UB row may trap `ub` there and
   carries no parity credit either way.

## Reference defects F3 meets

A case the reference cannot build (a panic, a by-name "cannot compile this
yet", or a by-name refusal of a program the specification accepts) is a named
defect. Its answer comes from lupin, the released macOS compiler where it
builds there, and the clause, all agreeing; otherwise the work stops with an
issue draft. fenrir's observation is gated against that answer on both
engines, but the case never counts as `same` and never earns parity, and it is
re-measured at every re-pin.

| defect | where F3 meets it |
|---|---|
| wolf-lang#1160: `f64` to `u8`, `i8`, `i16`, `u16` panics the Linux compiler | generated case tables over every value kind (at most one such case a program) |
| wolf-lang#404: native `copy` refuses by name a `Map` whose values reach the heap, a heap-carrying enum or row payload, a `Pool`, a `shared` cell | copy-depth and copy-out tables |
| native "cannot compile this yet" on `memory/region_iso_edge_ok`, `region_value_container`, `region_value_elem` | outside parity |
| wolf-lang#927: `copy` of a `List[byte]` parameter refused natively when the caller passed `.bytes()` | copy-depth tables |
| wolf-lang#1092: a first-class region is never freed natively | `rss-region-value-loop`; any `live_region_bytes` read after a value's last use |
| wolf-lang#644: region exit frees to malloc; the reference links glibc, fenrir musl | RSS rows compare class, not bytes |

## The anchors

Each `mem.*` anchor of the pinned registry (145) has one row here. **Scope**
names where the anchor's run-time meaning is lowered: `F2` (already lowered;
in scope from F3a), an F3 unit (`F3b` modes and moves, `F3c` regions, `F3d`
copy-out, freeze, transfer, pools and handles, `F3e-1` tier 3 without atomics,
`F3e-2` atomics), `F4`, `F6` (a construct no F3 row uses: view sets and local
borrows, which come with their static rules), `F7`, or `none` (not lowered at
F3). Until its unit lands an anchor is outside the typed coverage with one F0001
row; when it lands, the unit adds its positive row and its negative row. **Negative** names
the negative row's kind: a refusal fenrir shares with the reference (same code
and site), or the reference's E1xxx as a named difference closed at F6.
Documentary anchors (a chapter heading, the code table, the appendix) take the
scope of the construct their text illustrates.

| anchor | scope | run-time meaning at F3 | negative |
|---|---|---|---|
| `mem.model` | F2 | values, places and the evaluation order below | shared refusal |
| `mem.model.value` | F2 | assignment and argument passing transfer or copy the whole value | named difference (E1001, F6) |
| `mem.model.place` | F2 | a path of field and index steps names one storage location | shared refusal |
| `mem.model.place.elem` | F2 | an index step names one element; stores through it as `xs[i] = v` | named difference (E1001, F6) |
| `mem.model.path.disjoint` | F2 | disjoint field paths are independent stores | named difference (E1001, F6) |
| `mem.model.place.rhs` | F2 | a store runs its place's operands, then the right-hand side, then mints the address | shared refusal |
| `mem.model.order` | F2 | strict left-to-right evaluation; `defer`/`errdefer` at scope exit | shared refusal |
| `mem.model.granule` | F3c | documentary: value, region and cell granules | named difference (E1010, F6) |
| `mem.model.machine` | F3c | documentary: allocations, provenance, region forest, scope stack | named difference (E1010, F6) |
| `mem.model.alloc` | F3c | allocation sites land in the ambient region | named difference (E1010, F6) |
| `mem.codes` | F3b | documentary: the E1xxx family is static, traps are run time | shared refusal (E1007) |
| `mem.tier0` | F3b | the value tier: modes, moves, copies, borrows | shared refusal (E1007) |
| `mem.tier0.move` | F3b | moves transfer the value | named difference (E1001, F6) |
| `mem.tier0.move.1` | F3b | assignment, `take` arguments and `return` move non-`Copy` values | named difference (E1001, F6) |
| `mem.tier0.move.2` | F3b | a moved place has no run-time representation; its read is static | named difference (E1001, F6) |
| `mem.tier0.move.3` | F3b | `copy x` is a deep independent value; adapters of `Copy` scalars copy | shared refusal (E0805) |
| `mem.tier0.move.4` | F3b | storing to a moved place makes it live again | named difference (E1001, F6) |
| `mem.tier0.mode` | F3b | parameter modes `read`, `mut`, `take` | shared refusal (E1007) |
| `mem.tier0.mode.read` | F3b | a plain parameter is read-only for the call; a move out of it is a lend | shared refusal (E1014) |
| `mem.tier0.mode.mut` | F3b | value-result: the callee returns each `mut` parameter's final value on every return; the caller writes it back | shared refusal (E1009) |
| `mem.tier0.mode.take` | F3b | the argument moves into the callee | shared refusal (E1007) |
| `mem.tier0.excl` | F3b | exclusivity is static; accepted programs need no run-time check | named difference (E1002, F6) |
| `mem.tier0.excl.1` | F3b | no other live path to a `mut` place during its claim | named difference (E1002, F6) |
| `mem.tier0.excl.2` | F3b | disjoint `mut` arguments are independent temporaries | named difference (E1002, F6) |
| `mem.tier0.excl.3` | F6 | a view set passes only the named fields; no F3 row uses a view set | F6 |
| `mem.tier0.excl.4` | F3b | arguments are evaluated left to right; a `mut` claim starts at call entry, so earlier reads see the old value | named difference (E1001, F6) |
| `mem.tier0.borrow` | F6 | local borrows `&p`, `&mut p` are the place itself within the body; no F3 row uses a borrow | F6 |
| `mem.tier0.borrow.1` | F6 | a borrow never outlives its activation | F6 |
| `mem.tier0.borrow.2` | F6 | an `&mut` borrow holds its path exclusively until its last use | F6 |
| `mem.iter` | F2 | `for` over ranges, lists and pieces | shared refusal |
| `mem.iter.excl` | F2 | the loop holds a read claim on its operand | named difference (E1013, F6) |
| `mem.iter.excl.1` | F2 | a `Copy` operand is copied at loop entry; a place stays live behind the walk | named difference (E1013, F6) |
| `mem.iter.excl.2` | F2 | a write to the claimed place inside the loop is static | named difference (E1013, F6) |
| `mem.iter.for` | F2 | builtin ranges iterate directly; other iterables by the drive loop | shared refusal |
| `mem.iter.range` | F2 | `a..b` and `a..=b` ascend by checked `+1`, endpoints evaluated once | shared refusal |
| `mem.iter.trait` | F4 | `Iter[T]` and `next(mut self) -> T ! {done}` | F4 |
| `mem.iter.impl` | F4 | `List` and `Pool` adopt `Iter`; user types by name | F4 |
| `mem.list.slice` | F2 | `cs[a..b]` is a fresh list in the ambient region; outside the domain traps `bounds` | shared refusal |
| `mem.list.pop` | F2 | `pop`, `get`, `first`, `last` answer `none`; the subscript traps `bounds` | shared refusal |
| `mem.list.bytes` | F2 | `bytes_find` and `bytes_count` over a `List[byte]` | shared refusal |
| `mem.map.absent` | F2 | `m[k]` is `V ! {none}`; `m[k] = v` inserts or replaces | shared refusal |
| `mem.region` | F3c | the region tier | named difference (E1010, F6) |
| `mem.region.create` | F3c | sugar blocks and first-class values | named difference (E1001, F6) |
| `mem.region.create.1` | F3c | `region name { }` creates and opens; `region(…)` creates a value (`__wolf_rt_region_new`) | shared refusal |
| `mem.region.create.2` | F3c | a region value is affine: it moves, never copies | named difference (E1001, F6) |
| `mem.region.create.3` | F3c | every function runs with a current region, by default its caller's; `in r { }` enters `r` (`__wolf_rt_region_ambient_enter`, `_leave`) | named difference (E1001, F6) |
| `mem.region.create.4` | F3c | region identity has no run-time representation beyond the handle | named difference (E1001, F6) |
| `mem.region.proc` | F7 | a proc entry's ambient region is the proc's own | F7 |
| `mem.region.intra` | F3c | references inside one region are unrestricted | named difference (E1010, F6) |
| `mem.region.intra.1` | F3c | cycles and back edges inside a region are safe | named difference (E1010, F6) |
| `mem.region.intra.2` | F3c | a region is freed wholesale at block exit or the value's last use (`__wolf_rt_region_free`) | named difference (E1010, F6) |
| `mem.region.escape` | F3c | nothing at run time on the native engine; the interpreter traps `region-fault` on a read of a freed region (a fenrir-internal check, never parity) | named difference (E1010, F6) |
| `mem.region.scalar` | F3c | a value that reaches no storage names no region | named difference (E1010, F6) |
| `mem.region.outer-write` | F3c | a `copy` stored into an outer value is made in the outer value's region | named difference (E1010, F6) |
| `mem.region.copyout` | F3d | `copy region { }` deep-copies the block's value into the entry's ambient region before the free; `return`, `break`, `?` hand out nothing | named difference (E1010, F6) |
| `mem.region.edge` | F3c | edges between regions are static | named difference (E1004, F6) |
| `mem.region.edge.iso` | F3d | a region has at most one owning edge | named difference (F6) |
| `mem.region.edge.imm` | F3d | frozen data is referable from anywhere | named difference (F6) |
| `mem.region.edge.elem` | F3c | a store through a container index lends the value; `push` copies the element in | named difference (E1004, F6) |
| `mem.region.edge.raw` | F3e-1 | raw cross-region edges carry tier-3 obligations only | named difference (F6) |
| `mem.region.open` | F3c | open and suspended states | named difference (E1010, F6) |
| `mem.region.open.1` | F3c | re-entering an open region is depth-counted | named difference (E1010, F6) |
| `mem.region.open.2` | F3d | disjoint regions may be open together | named difference (F6) |
| `mem.region.multiopen` | F3d | several region values open at once, swapped | named difference (F6) |
| `mem.region.open.3` | F3c | a suspended region is unwritable | named difference (E1010, F6) |
| `mem.region.freeze` | F3d | freeze and transfer | named difference (E1005, F6) |
| `mem.region.freeze.1` | F3d | `freeze r` consumes the value and makes its contents immutable in place (`__wolf_rt_region_freeze`) | named difference (E1012, F6) |
| `mem.region.freeze.2` | F3d | `move r` transfers the value (`__wolf_rt_region_transfer`, `_adopt`) | named difference (E1001, F6) |
| `mem.region.freeze.3` | F3d | freezing a region with an open child is static | named difference (E1005, F6) |
| `mem.region.freeze.4` | F3d | reads through frozen data are ordinary reads; an unmodified receiver written back is not a write | named difference (E1012, F6) |
| `mem.region.root` | F3d | a region carries no root; a handle travels beside it | named difference (F6) |
| `mem.region.imm.ret` | F3d | `imm` is not a type qualifier | shared refusal |
| `mem.region.promote` | F3c | placement is unobservable | named difference (E1010, F6) |
| `mem.region.promote.1` | F3c | stack promotion changes no observation | named difference (E1010, F6) |
| `mem.region.account` | F3c | the byte ledger | named difference (E1001, F6) |
| `mem.region.account.1` | F3c | `region_bytes(r)`: zero at creation, monotone, stable between allocations (`__wolf_rt_region_bytes`) | named difference (E1010, F6) |
| `mem.region.account.2` | F3c | `live_region_bytes()`: rises while a region holds storage, drops wholesale at its free (`__wolf_rt_live_region_bytes`) | named difference (E1010, F6) |
| `mem.region.cap` | F3c | creation-time byte budgets | named difference (E1010, F6) |
| `mem.region.cap.1` | F3c | a charge past the cap traps `alloc-contract` at the allocating site; exactly at the cap is legal (`__wolf_rt_region_set_cap`) | named difference (E1010, F6) |
| `mem.region.cap.2` | F3c | `cap:` is evaluated once; a negative cap traps `alloc-contract` at the creating site | named difference (E1001, F6) |
| `mem.region.cap.3` | F7 | a breach inside a proc is contained at the proc boundary | F7 |
| `mem.shared` | none | the cell tier: `shared`, `weak`, `handle` | none |
| `mem.shared.rc` | none | reference-counted cells; not lowered at F3 | none |
| `mem.shared.rc.1` | none | a cell drops at its last strong reference; not lowered at F3 | none |
| `mem.shared.rc.2` | none | strong cycles are static (E1006); not lowered at F3 | none |
| `mem.shared.rc.3` | none | `weak` upgrades to an option-shaped result; not lowered at F3 | none |
| `mem.shared.rc.4` | none | count operations are unobservable; not lowered at F3 | none |
| `mem.shared.drop` | F4 | destructor timing; destructors are trait impls | F4 |
| `mem.shared.drop.1` | F4 | a destructor runs at scope exit, LIFO with `defer` | F4 |
| `mem.shared.drop.2` | F4 | destructor-free values may be reclaimed after last use | F4 |
| `mem.shared.drop.3` | none | a cell's payload destructor runs at the last release; not lowered at F3 | none |
| `mem.shared.handle` | F3d | `handle T` is a generational index into a pool region | named difference (F6) |
| `mem.shared.handle.1` | F3d | `reserve()` yields a handle, `init(h, v)` fills it (`__wolf_rt_pool_reserve`, `_write`) | named difference (F6) |
| `mem.shared.handle.2` | F3d | a freed or re-generationed slot traps `stale-handle` at the access (`__wolf_rt_pool_alive`, `_read`) | named difference (F6) |
| `mem.shared.handle.3` | F3d | `pool[h]` and `pool[mut h]` are places based at the pool | named difference (E1002, F6) |
| `mem.unsafe` | F3e-1 | the raw tier | named difference (E1301, F6) |
| `mem.unsafe.raw.1` | F3e-1 | raw pointers are address words with no aliasing assumptions | named difference (E1301, F6) |
| `mem.unsafe.raw.2` | F3e-1 | `assume noalias` is an assertion; nothing at run time | named difference (F6) |
| `mem.unsafe.raw.3` | F3e-1 | volatile accesses are the two methods of `*T` | named difference (F6) |
| `mem.unsafe.raw.4` | F3e-1 | an ordinary raw access is one access at the pointee's alignment; a packed field at its offset's alignment | named difference (F6) |
| `mem.unsafe.raw.5` | F3e-1 | a field of a raw element is one access at the field's layout offset | named difference (E1301, F6) |
| `mem.unsafe.volatile` | F3e-1 | `read_volatile` and `write_volatile` | named difference (E1301, F6) |
| `mem.unsafe.volatile.1` | F3e-1 | the pointee is a fixed-width integer or `byte` | named difference (E1307, F6) |
| `mem.unsafe.volatile.2` | F3e-1 | exactly one aligned access of the width per call, never merged or elided | named difference (F6) |
| `mem.unsafe.volatile.3` | F3e-1 | on an allocation, an ordinary access of the width | named difference (F6) |
| `mem.unsafe.door` | F3e-1 | `borrow r from p` and the checked handle re-enter the safe tier | named difference (F6) |
| `mem.unsafe.scope` | F3e-1 | `unsafe { }` blocks inside safe signatures | named difference (E1301, F6) |
| `mem.unsafe.sig` | F3e-1 | a `*T` in a private or C-membrane signature; passed by value it is a copy of the word | named difference (E1302, F6) |
| `mem.static` | F3e-1 | module `const`, `let`, `var` | named difference (F6) |
| `mem.static.1` | F3e-1 | a `const` is its value; a `let` is read-only data | shared refusal |
| `mem.static.2` | F3e-1 | a `var` is writable data; every access is raw tier; a call may write it | named difference (E1301, F6) |
| `mem.static.3` | F3e-1 | initializers are compile-time values; the image holds them | shared refusal |
| `mem.static.4` | F3e-1 | a `pub` item read through its module's name | named difference (E1301, F6) |
| `mem.prov` | F3e-1 | pointer provenance | named difference (F6) |
| `mem.prov.tag` | F3e-1 | tags are the interpreter's; native carries none | named difference (F6) |
| `mem.prov.state` | F3e-1 | tag states are the interpreter's UB model | named difference (F6) |
| `mem.prov.expose` | F3e-1 | `addr`, `with_addr`, `expose`, `with_exposed`, `is_null`, casts; identity on 64-bit words | named difference (E0409, F6) |
| `mem.prov.device` | F3e-1 | an address no allocation owns is UB on a hosted target | named difference (F6) |
| `mem.prov.region` | F3e-1 | freeing a region disables its tags; tags never alias across regions | named difference (F6) |
| `mem.ub` | F3e-1 | the closed UB table; UB rows carry no parity credit | named difference (F6) |
| `mem.ub.defined` | F3e-1 | overflow, division by zero, bounds and stale handles trap | named difference (F6) |
| `mem.ub.closed` | F3e-1 | documentary: the table is closed | named difference (F6) |
| `mem.boundary` | F3e-1 | the module is the audit granule | named difference (F6) |
| `mem.boundary.module` | F3e-1 | an unsafe block relies only on its module's invariants; nothing at run time | named difference (F6) |
| `mem.boundary.doc` | F3e-1 | every unsafe block states its invariant; nothing at run time | named difference (F6) |
| `mem.boundary.trusted` | F7 | `#[trusted]` modules are a package-manifest surface | F7 |
| `mem.boundary.ffi` | F3e-1 | a C call borrows an implicit region for its extent | named difference (F6) |
| `mem.str` | F2 | `str` ordering and the boundary methods | shared refusal |
| `mem.str.order` | F2 | byte-lexicographic order | shared refusal |
| `mem.str.impl` | F4 | `impl Ord for str` | F4 |
| `mem.str.get` | F2 | `s.get(a..b)` answers `none` exactly where `s[a..b]` traps | shared refusal |
| `mem.str.empty` | F2 | an empty needle matches nothing | shared refusal |
| `mem.str.repeat` | F2 | a negative count traps `assert` | shared refusal |
| `mem.str.ws` | F2 | the separator set is Unicode `White_Space` | shared refusal |
| `mem.str.words` | F2 | maximal non-empty runs of non-separators | shared refusal |
| `mem.str.lines` | F2 | splits on LF, absorbing one CR before it | shared refusal |
| `mem.str.split` | F2 | every field between leftmost non-overlapping separators | shared refusal |
| `mem.str.view` | F2 | views allocate nothing and share the receiver's bytes | shared refusal |
| `mem.str.view.lend` | F2 | `bytes()` materializes a `List[byte]` | shared refusal |
| `mem.str.chars` | F2 | the scalar values, materialized | shared refusal |
| `mem.str.parse` | F2 | the parse family is `to_int` | shared refusal |
| `mem.str.to_int` | F2 | optional sign and ASCII digits inside the whitespace run | shared refusal |
| `mem.str.imm` | F2 | a `str` never changes; its index is not a place | shared refusal |
| `mem.dyn.unsize` | F4 | trait objects by explicit cast | F4 |
| `mem.appendix` | F3d | documentary: `corpus/regions.lu` clause by clause | named difference (F6) |

The negative kinds above are the plan. A unit that brings an anchor in scope
writes the negative row the table names, or changes the table in the same
commit with the reason.

## Named differences

A named difference is a negative row the reference refuses with an E1xxx code
and fenrir accepts, because the static rule is F6's. Each is listed in
`tests/types/memory-differences.json` with the anchor, the reference's code
and site, and the milestone that closes it; the list's count is committed and
checked in both directions against the rows, so it cannot grow or shrink
quietly. A row whose difference closes (fenrir starts refusing) fails by name
until it is removed from the list.

A run row can differ too. `tests/types/core-differences.json` lists each
corpus row that fenrir types but that differs from the reference on an
engine, until a named step lands. The census classes a listed row
`named-difference`, outside the core and outside every corpus run. The census
gate fails a listed row that stops typing or that the census puts anywhere
else. The list's count is held, so adding an entry is a visible change. Its
one entry is `memory/byte_list_ledger`. It needs one width-1 layout for
`List[byte]` across the list literal, the constructor, `bytes()`, `copy` and
slicing, with native reads that zero-extend.

## F3's membership

`tests/types/f3-membership.json` freezes F3's rows: 204 native-comparable run
rows, placed by unit at the last unit among each row's blockers. The census
(`tools/census`) records every blocker a row meets in the census's scope model
(`blockers`), and the membership gate checks the frozen lists against it in
both directions on every run. Eight members need a construct outside the units'
own language, each named in the file under `owed` with the unit that owes it:

| member | construct | owed by |
|---|---|---|
| `memory/read_lend_frame`, `memory/read_lend_value_semantics` | `#[consttime(public(…))]` naming every parameter (`[ct.attr]`; nothing secret, so nothing to verify) | F3b |
| `memory/elem_const_swap_heap`, `memory/mut_place_nested` | an empty list literal typed from its context | F3b |
| `memory/nested_fn_mut_param` | a nested `fn` item | F3b |
| `membrane/extern_let_image` | `#[cfg(target = …)]` on items | F3e-1 |
| `memory/packed_fields_at_offset_of` | a nested `const` with `size_of` and `offset_of` | F3e-1 |
| `memory/static_var_call_deep` | a top-level function used as a value and called | F3e-1 |

F3b brings in the constructs it owes only in the forms these members use; the
lowering of each is in [LOWERING](LOWERING.md).

The scope model and fenrir's checker do not always name a row's first refusal
alike; `tests/types/scope-model-gap.json` lists every out-of-core row where
they differ, by name or by site, and the census checks it is current.
