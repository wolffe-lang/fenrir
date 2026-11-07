## Prediction

Written before the first change; base `1b24f2f` (fenrir trunk, 46 `same`
core rows of the corpus's 780 run rows).

### The census

`tools/census needs` reads every run row's AST and records each construct the
row needs beyond the trunk compiler, by family, instead of stopping at the
first one as the core census does ([the frozen table](../tests/types/fn06-needs.json)).
A receiver's family (`xs.len`, `xs[i]`, `for x in xs`) comes from a small local
type environment; a receiver it cannot read is labelled `unknown` and keeps
its row out of every prediction. The walk agrees with the core census on all
780 run rows (an empty needs set is exactly the `core` class), and two runs
are byte-identical. Only rows whose native oracle runs or traps count; a
native refusal is never predicted coverage.

Each family brings its own helpers: lists bring `for` over ranges (one clause,
`[mem.iter.for]`), and `Map` brings the tuples `pairs()` yields
(`[type.map.key]`). Rows brought into scope, beyond the 46:

| families | rows |
|---|---:|
| lists alone | 29 |
| `Map` alone | 2 |
| error values alone | 28 |
| lists and `Map` | 32 |
| lists and error values | 67 |
| `Map` and error values | 41 |
| **all three** | **86** |

`Map` alone reaches almost nothing because a map read is a row
(`[mem.map.absent]`: `m[k]` is `V ! {none}`), so a map program handles
an error value. The three together reach more than any pair, so the lane
keeps the contract's split: lists, `Map` and error values, in that order
(lists first because the most rows need them, and every `Map` row needs
error values).

**Also needing strings: 20 rows**, fn07's: `str` methods (`bytes`,
`chars`, `lines`, `to_int`, `find`, `split`, `starts_with`), `str` slices
and `.len`, `char` and format specs.

**Also needing parameter and argument modes: 56 rows**, nearly all
`corpus/memory/*` claim, exclusivity and lend rows. Modes are lends
(`[mem.tier0.mode]`), which the campaign puts in F3, so this lane does not
take them.

### The predicted rows

The prediction is **86 new `same` rows, taking the core from 46 to 132**
(16.9% of the 780 run rows), natively and through the bounded interpreter,
with no `differs`. They are:

- `corpus/faults/assert_msg_effect_fails.lu`
- `corpus/faults/assert_msg_holds.lu`
- `corpus/faults/assert_msg_name.lu`
- `corpus/faults/assert_msg_try.lu`
- `corpus/faults/overflow_elem_read.lu`
- `corpus/faults/overflow_elem_write.lu`
- `corpus/faults/overflow_list_pop_i32.lu`
- `corpus/faults/overflow_list_pop_i64.lu`
- `corpus/lints/discarded_result.lu`
- `corpus/lints/else_comparison.lu`
- `corpus/lints/tag_case_payload.lu`
- `corpus/memory/ctl_index_else_once.lu`
- `corpus/memory/ctl_index_return_break_once.lu`
- `corpus/memory/ctl_index_try_once.lu`
- `corpus/memory/ctl_nested_index_try_once.lu`
- `corpus/memory/ctl_slice_endpoints.lu`
- `corpus/memory/ctl_slice_endpoints_call.lu`
- `corpus/memory/ctl_slice_endpoints_indexed_base.lu`
- `corpus/memory/ctl_slice_endpoints_nested.lu`
- `corpus/memory/ctl_slice_try_once.lu`
- `corpus/memory/ctl_store_order.lu`
- `corpus/memory/ctl_store_order_compound.lu`
- `corpus/memory/ctl_store_order_nested_index.lu`
- `corpus/memory/destructure_bind.lu`
- `corpus/memory/destructure_partial_live.lu`
- `corpus/memory/elem_const_iter_mut.lu`
- `corpus/memory/elem_key_move_map.lu`
- `corpus/memory/field_shorthand_mixed_runs.lu`
- `corpus/memory/field_shorthand_nested_runs.lu`
- `corpus/memory/index_store_copies_list.lu`
- `corpus/memory/index_store_copies_map.lu`
- `corpus/memory/index_store_copy_elem.lu`
- `corpus/memory/list_elem_copy_loop.lu`
- `corpus/memory/list_mixed_width_struct.lu`
- `corpus/memory/list_pop_empty.lu`
- `corpus/memory/list_slice_inline_owned.lu`
- `corpus/memory/list_slice_owned_call.lu`
- `corpus/memory/map_absent_else.lu`
- `corpus/memory/map_int_keys.lu`
- `corpus/memory/map_pairs_walk_snapshot.lu`
- `corpus/memory/oob_bounds.lu`
- `corpus/memory/prov_two_phase.lu`
- `corpus/memory/push_grow_guarded_index.lu`
- `corpus/memory/push_grow_nested_guarded_index.lu`
- `corpus/rows/else_own_failure.lu`
- `corpus/rows/else_return_tag.lu`
- `corpus/rows/else_try_call_arg.lu`
- `corpus/rows/else_try_handler.lu`
- `corpus/rows/else_try_index.lu`
- `corpus/rows/else_try_nested_else.lu`
- `corpus/rows/error_alias_row.lu`
- `corpus/rows/error_alias_transparent.lu`
- `corpus/rows/error_alias_union.lu`
- `corpus/rows/eu_bind_empty_row.lu`
- `corpus/rows/eu_bind_empty_row_handled.lu`
- `corpus/rows/eu_bind_empty_row_unit.lu`
- `corpus/rows/eu_main_err_exit.lu`
- `corpus/rows/first_list_literal_sum.lu`
- `corpus/rows/handler_match_tags.lu`
- `corpus/rows/iter_diverging_else_bound.lu`
- `corpus/rows/match_row_bare_tag.lu`
- `corpus/rows/match_row_else_control.lu`
- `corpus/rows/match_row_nested.lu`
- `corpus/rows/match_row_try_scrutinee.lu`
- `corpus/rows/match_row_wild_each_half.lu`
- `corpus/rows/nested_row_merge_payload.lu`
- `corpus/rows/nested_row_param.lu`
- `corpus/rows/nested_row_return.lu`
- `corpus/rows/open_row_growth.lu`
- `corpus/rows/tag_arg_position.lu`
- `corpus/rows/tag_let_position.lu`
- `corpus/rows/tag_shadow_local.lu`
- `corpus/rows/unit_discard_fallible_body_stmt.lu`
- `corpus/rows/unit_discard_if_value.lu`
- `corpus/rows/unit_discard_return_operand.lu`
- `corpus/rows/unit_discard_tail_if_chain.lu`
- `corpus/rows/unit_discard_tail_if_leaves.lu`
- `corpus/rows/unit_discard_tail_if_value_row.lu`
- `corpus/rows/unit_discard_try_leaves.lu`
- `corpus/rows/unit_discard_unit_main.lu`
- `corpus/typecheck/list_lit_elem_i32.lu`
- `corpus/typecheck/list_tuple_elem.lu`
- `corpus/typecheck/match_exhaustive.lu`
- `corpus/typecheck/match_narrow_scrutinee.lu`
- `corpus/typecheck/numlit_binding_value_later_use.lu`
- `corpus/typecheck/numlit_list_element_width.lu`

`corpus/faults/assert_msg_effect_fails.lu` is one of the oracle's own
recorded disagreements (the native tier prints no assertion message);
fenrir is compared with native, as every row is.

### The design

1. **Lists.** `List[T]` for every type in scope (integers, `bool`, `str`,
   structs, enums, lists, maps, tuples). FIR grows a list type per element
   type in its shapes table, and the list instructions take it: a fresh list,
   `push`, an element read and write that trap `bounds` at their site, `len`,
   `pop` and the recoverable reads (`get`, `first`, `last`, which answer
   `none`), `clear`, and a slice that traps `bounds` outside
   `lo <= hi <= len` (`[mem.list.slice]`). The literal is a fresh list with
   its elements evaluated left to right (`[type.list.lit.value]`); its element
   type unifies left to right, `[]` takes it from the context or is E0419
   (`[type.list.lit]`). `push` and an index store copy a list or map element
   deep, as `[type.comb.set]` states; a `str` shares its bytes. The backend
   calls the runtime's list entries with the element's byte size.
2. **Iteration.** `for x in xs` over a list and `for i in a..b` /
   `a..=b` over a range (`[mem.iter.range]`: endpoints evaluated once, left
   to right, ascending, checked arithmetic). `break` and `continue` work as
   in `while`.
3. **Tuples,** as far as `pairs()` and the corpus rows need them: tuple
   types, values, `.0` reads and `let (a, b) = …` destructuring.
4. **`Map[K, V]`** with `str`, `int` and `bool` keys (`char` waits for
   strings; any other key is E0418, `[type.map.key]`). `m[k]` is
   `V ! {none}`, `m[k] = v` inserts or replaces, `m[k] op= v` is E0417
   (`[mem.map.absent]`); `len`, `count()`, `is_empty()`, `clear()`,
   `remove(k)` (`V ! {none}`) and `pairs()` (a fresh `List[(K, V)]`). The
   order is the spec's: unspecified but consistent, and the runtime reports
   insertion order, which fenrir keeps (the interpreter does too). The
   runtime has entries for construction, get, set, remove, pairs, copy and
   clear but none for the length, so a fenrir map value carries its own
   count beside the runtime handle, kept by `set` (after a get tells an
   insert from a replace), `remove` and `clear`. No length is computed by
   materializing `pairs()`.
5. **Error values.** `T ! {row}`, `!T` with its inferred private row
   (`[gram.item.fn]`), open rows (`..`), nested rows flattened
   (`[gram.type.row.flatten]`) and error-set aliases (`[type.err.alias]`).
   A row value is a FIR enum: the ok payload, then one variant per tag in a
   fixed order. Raising a tag (`[gram.expr.tagident]`'s checked positions),
   `?` (propagation, converting the callee's row into the caller's), `else`
   with a fallback and `else |p|` with a handler (`[type.row.else]`: only the
   scrutinee's own row is handled; a `?` inside it propagates past), `match`
   over a row (`[type.row.match]`), and rendering a row in an interpolation
   hole. An operator applied to a row is E0409 (`[type.row.operand]`).
   `main` returning an error prints `error: TAG` on stdout and exits 1, as
   the runtime's `main_err` entry documents.
6. **Every layer.** Types and resolution, the lowering, FIR (a new edition,
   through its change record), the verifier, the text form, the bounded
   interpreter and x86-64. Every new refusal code goes into
   `docs/DIAGNOSTICS.md` and the catalog gate, with rows from black-box
   reference runs. The interpreter charges list and map storage to its
   memory budget, measured; exhaustion stays `FIR_MEMORY_BUDGET`.
7. **Rows, red first,** from the predicted corpus rows where possible and
   fixtures where not: each list, map and row operation and trap at its
   site, evaluation order, and determinism. No optimizer: nothing is folded
   and no transform moves a trap.

Any `differs` in the corpus delta is a stop and a ruling, never a ledger line.

### Amendments to the design

Three points of the design changed during the work, each for a reason found
in the work itself:

- **A map's length.** The design had a fenrir map carry its own count, since
  the runtime has no length entry. The runtime's map documentation says a
  map's header begins with a list header, so that lowering reads the entry
  count through the list header's length. `len` on a map is the list length
  entry on the map's handle, and no count is carried.
- **The empty list literal.** The design had `[]` take its type from the
  context, or be E0419. No predicted row needs it, so the scope check refuses
  `[]` by name (F0001) and leaves it to a later lane.
- **The needs walker.** After the Prediction was frozen, the walker learnt
  that `len()` is a list and map method (it had only `.len`), and it now
  labels an empty list literal, `defer` and `errdefer` as outside the families.
  The census then reached one row the Prediction did not name,
  `corpus/memory/elem_header_methods_after_move_map.lu`, which calls
  `xs.len()`. The frozen counts in `tests/types/fn06-needs.json` are the
  Prediction's and stay as they were.

### FIR edition 3

The verifier, the text form, the bounded interpreter and the x86-64 backend
carry list and map shapes and the ten new instructions (FIR.md). The fixture
rows came first (`tests/backend/collections.py`): against the base compiler
the first list round trip is refused with `FIR_SYNTAX unknown edition 3`.
Seventeen finite fixtures print, exit and trap identically through the
interpreter and natively on Linux; 25 malformed modules are
refused by name; an edition-1 or edition-2 module still prints its old bytes.

Aggregates count against the interpreter's memory budget. The rows fill a
list of one-word elements, a list of three-word records and a map of `int`
to `int` with N entries, and bisect the least budget that lets each run. Over
the one-entry run, each word of storage is charged:

| container | N = 1,000 | 10,000 | 100,000 |
|---|---:|---:|---:|
| list, 1 word | 16.34 | 26.21 | 20.97 |
| list, 3 words | 16.34 | 26.21 | 20.97 |
| map, 2 words | 32.67 | 52.42 | 41.94 |

bytes per word. The figures are the ledger's own counts, so they are the
same on every host. A list's geometric capacity accounts for the swing
between 16 and 32; a map adds its index, at eight bytes a slot. The rows
hold every figure between 8 and 64, so a container that stopped being
charged, or began to be charged quadratically, fails by name.

### Typing and the refusal codes

`tests/types/collection_rows.py` holds 54 refusal and acceptance rows for
lists, maps, tuples and rows, each against fenrir and against the reference
with the same code at the same place. Against the base compiler all 54 fail
by name. The typed rows (`tests/types/rows.py`)
moved every anchor that entered the core from an F0001 row to a positive row
and a refusal row, and the typed invariants learnt the new kinds: `List`,
`Map` and tag names name no declaration, a method's callee `Member` is
untyped, and the final type table holds no type with an unsolved integer
variable (a list literal `[1, n]` used to leave one behind).

The reference checks an error alias only where a row names it, and treats
the alias as a layer only when the row's own spelling of a tag comes first.
The clauses say otherwise, and fenrir follows them: an alias that names
itself is E0610 even when nothing uses it (`[type.err.alias.cycle]`), and a
tag that the row and an alias it names share merges whichever comes first
(`[type.err.alias.union]`). The three rows that show it are marked `differs`,
and the reference must keep giving the answer each row records for it.

Two more rules came from the corpus's own refusal rows, which the census
showed fenrir accepting once lists and rows were in scope:
`corpus/rows/negative/open_into_closed.lu` (E0602) and
`corpus/rows/negative/pub_inferred.lu` (E0605). Black-box runs gave the
reference's rule for each. A call of a function whose row ends in `..` may
leave another function, by `?` or as the returned value, only if that
function's row is open too; an inferred `!T` row is not open. An exported
function may not infer its row, so `pub fn … -> !T` is E0605 at its name,
`main` included. Both rules are in `tests/types/collection_rows.py`; against
the build before them, the five refusal rows failed by name.

Seventeen other oracle-refused rows are accepted now, besides the three the
base already had, and all are the memory model's: use after a move (E1001),
writes through a read parameter (E1002, E1014) and a list changed while it
is iterated (E1013). They are F3's, and the census counts them apart from
the core. One more, `corpus/rows/mixed_payload_display.lu`, is no refusal:
the pinned native compiler stops on it with an internal verification error,
while the reference interpreter prints the row's expected output. It is not
a native `same` either way.

### Lowering rows

Fourteen lowering rows came first: list literals, methods, slices and
nested lists, a list of records, maps of `str` and `int` keys with removal
and iteration order, a map of lists, raising and handling, propagation with
its evaluation order, and `main` returning an error and a value. Against
the base compiler each of the fourteen is refused by name (F0001). Three of
them trap `bounds`: an index read, an index store whose index and value both
run before the trap, and a reversed slice. On Linux each is built by fenrir
and by the pinned compiler, and the two programs agree byte for byte in
stdout, stderr (the trap line and its site) and status. The pinned compiler
refused two rows as first written, for reading a value out of a list or map
and then using the container (E1001), and printed `error: TooBig` where a
row expected the payload too. The rows were corrected to the reference's
answers, and the typed interface says so: the entry prints the tag's name
alone.

### The corpus delta

The core differential over the census's 133 core rows, natively (built by
clef and ligature, run on Linux x86-64) and through the bounded interpreter,
gives 133 `same` each: no `differs`, `fenrir-refuses` or `fenrir-crashes`.
The two verdict tables are byte-identical. The Prediction was 46 to 132, and
the rows that moved are the 86 it named and one more,
`corpus/memory/elem_header_methods_after_move_map.lu`, which the needs
walker counted out until it knew `len()` (above). No row was lost. That is
133 of the corpus's 780 run rows (17.1%, from 5.90%). F2's 50% belongs to
fn07 now, with strings and traps.
