# Differential harness

The black boxes are wolf 0.2.36's native `run` and lupin 0.1.58's
`conform-run --json`. Inputs are only the pinned specification and corpus.
No reference compiler implementation is read. The committed oracle table
will record both observations per entry, module membership, header expectations,
and the oracles' own disagreements. It is evidence, not fenrir coverage.

The frame compiles nothing; `fenrir-refuses` is a failing verdict and never
counts as `same`. Coverage is computed from run rows, not hand-maintained.
Status 70 is a crash, never an environmental skip. See DRIVER.md.

The command and record schemas will be completed alongside the harness.
