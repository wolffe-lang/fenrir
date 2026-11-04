# Clarify sub-word widening statements for bool runtime hooks

The runtime-widening parentheticals in `[type.char]` and `[type.byte]` are too
broad. At wolf-lang `5f1f1c94`, `spec/10-types.md` says:

- `[type.char]`: “the value crosses the runtime's C seam widened to `i64` like
  every sub-word scalar”.
- `[type.byte]`: “the value crosses the runtime's C seam zero-extended to `i64`
  like every sub-word scalar”.

The public bool hooks instead declare one-byte parameters:

```rust
pub extern "C" fn __wolf_rt_print_bool(v: i8);
pub unsafe extern "C" fn __wolf_rt_strbuf_bool(handle: i64, v: i8, spec: i64);
```

The public documentation for `__wolf_rt_print_bool` in
`crates/wolf_rt/src/native.rs` is explicit:

> Write `true`/`false` to stdout, flushed. The parameter is `i8` —
> WIR bools cross the call boundary as one byte (only the low byte of
> the register is defined under SysV).

The public documentation for `__wolf_rt_strbuf_bool` in
`crates/wolf_rt/src/str.rs` agrees:

> Append a `true`/`false` hole. `i8` — WIR bools cross the call
> boundary as one byte, exactly as in the s38 write shims.

## Requested clarification

Keep the char and byte hooks' specified widening, but remove the generalization
“like every sub-word scalar”, or qualify it to exclude bool hooks. State that a
runtime call follows its individual public prototype; storage width does not
imply a universal runtime-hook parameter type.

This is a documentation correction, not a request to change the runtime ABI.
Passing canonical bool values 0 and 1 with zero upper register bits satisfies
the one-byte prototypes. Declaring every sub-word hook to take `i64` would be
the wrong resolution even where the resulting register bits happened to agree.
