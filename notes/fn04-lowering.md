## Prediction

Written before the lowering's first commit.

- **The lowering.** One function at a time, every AST node lowered once, with
  dense per-node and per-declaration tables allocated once per module, turns
  the typed tree into FIR 1 in time linear in nodes plus the words of the struct
  values it renders. Locals, `var` places and parameters live in stack slots;
  a value an expression still needs across a split (an `if`, `&&`, `||`, a
  loop or `assert` inside a later operand) is spilled to a slot, so no value
  crosses a block except through a branch argument. The FIR verifier runs on
  every module the lowering returns.
- **Semantics.** Operands, arguments, struct initializers and interpolation
  holes run left to right; `&&` and `||` short-circuit; an assertion's message
  runs only on its failing path. Each trap reports its kind and the start of
  the innermost statement or tail containing the operation, as the reference
  does. `main` hands its `int` (or 0) to the process.
- **The driver.** `fenrir build FILE.lu -o OUT` links a static Linux x86-64
  executable through clef and ligature; `fenrir run` runs it with the program's
  own status; `--emit=fir` and `--emit=asm` print stable text. Statuses are 0,
  2 for a rejection, 4 for a refusal (F0001, and F0002 for a program with no
  `main`), 70 for an internal error.
- **Rows.** Every core construct, every trap kind at its site and every
  evaluation-order row equals the pinned wolf byte for byte on Linux; emission
  is byte-identical across two runs; the lowering scales linearly at N, 10N and
  100N.
- **F1.** `fenrir build hello.lu` prints `hello, wolf`, and every row of the
  computed core census is `same` against the pinned oracle: no `differs`, no
  `fenrir-crashes`, no `fenrir-refuses`. The PAX row of F1 belongs to a later
  PAX lane.
- **The plant.** `&&` evaluating its right operand when the left is false is red
  by name.
