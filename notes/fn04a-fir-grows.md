## Prediction

Written before the first change.

- **Types.** FIR grows to version 1: the fixed types become `unit`, `int`,
  `bool`, `str`, `List[int]`, then the sized integers `i32`, `i64`, `u8`,
  `u64` and `uint` at ids 5 to 9, the same ids the typed tree gives them, and
  structs start at 10. Each sized integer is one word in canonical form
  (`i32` sign-extended, `u8` zero-extended). Width, signedness and range come
  from one table in `src/sem/`, which the verifier's constant check and the
  emitter's checks both read. Struct fields may be any earlier non-unit value
  type, `str` and every integer kind included, and a struct may have no fields.
- **Operations.** `add`, `sub`, `mul`, `div` and `rem` take two operands of one
  integer kind and trap exactly as the reference does: `overflow` outside the
  kind's range, `div-zero` on a zero divisor, `overflow` on signed `MIN / -1`
  and `MIN % -1`. Unsigned compares, division and remainder are unsigned. `not`
  on an integer is the bitwise complement within its width and never traps.
  `eq` takes an integer kind, `bool` or `str`; `lt` takes an integer kind or
  `str` (byte order). Negation needs no instruction: `0 - x` already traps
  `overflow` for a nonzero unsigned `x` and for a signed `MIN`.
- **Places.** A function declares typed stack slots; `load` and `store` read and
  write a slot or a field path inside it, so locals and `var` places need no
  cross-block values and lowering stays linear.
- **Text.** `format` renders one or more integer, `bool` and `str` values into a
  fresh `str` through one runtime string buffer: integers in decimal, unsigned
  values never negative, `true`/`false`, a `str` as its bytes. A struct, `()`
  and literal text are rendered by the lowering from those parts.
- **Traps.** The `assert` trap is kind 9, the position `[conf.trap.set]` gives
  it; it may carry its evaluated `str` message, which this backend does not
  print, as the pinned reference does not in an ordinary build.
- **Rows.** Every new form round-trips through the text form; every new
  rejection is refused by name; every emitted fixture assembles with clef to
  GNU as's object and is byte-identical across two emissions. Each new type and
  trap has a Linux program whose stdout, status and complete trap report equal
  the pinned wolf's, byte for byte. Scaling stays linear at N, 10N and 100N.
- **The plant.** A `u64` compare emitted signed is red by name.
