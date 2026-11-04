## Prediction

A spec-first lexer/parser should accept every syntactically valid pinned corpus
file, refuse syntax errors by code and file:line:column, and emit deterministic
tokens and a fully spanned AST. Recursive descent plus precedence climbing and
append-only arenas should scale linearly.

Footprint: cross-cutting

## Forbidden

No reference compiler implementation source was read. No optimizer, resolver,
type checker, ownership checker or code generator is claimed. Parser acceptance
is not compilation: the compiled bootstrap subset remains empty, with 43 used
construct families explicitly inventoried. No unsupported result or skip counts
as success. The plant has no PR and branch pushes do not trigger CI.

## Inputs verified

- Rebased onto the frame's `a9f56923f81233a6601d13a72ed9429d0969bdbc`.
- Pinned wolf 0.2.36; sealed specification/corpus at `5f1f1c94` (1,253 files).
- Generated Unicode 17.0.0 XID tables from a digest-pinned data file. Reference
  builds accept the 15.0/15.1/16.0/17.0 release-boundary identifiers. All four
  have positive rows; an unassigned scalar supplies the negative.
- The corpus adds unit `()`, empty error rows, public impl methods and dynamic
  format width beyond the EBNF. `docs/AST.md` documents them and their paired
  rows. Five specification issue drafts are under `notes/fn01/spec-issues/`.

Commit references:
- `b01b576`: lexer/parser and source/syntax arenas.
- `cfaf462`: corpus grammar edges and source-ordered diagnostics.
- `0958636`: public arena fields and grammar-boundary refinements.
- `910b37f`: front-end checks in CI, Linux-only capped fuzz/scaling.
- `7d37c1a`: captured-output adaptor and independent tests.
- `9955a74`, `189e9d9`: exact-location regression then BOM column fix.

## Evidence index

Final head: `189e9d9438aee06b9e861d4bcbb2553afdd4eec6`.

- [x] 63 targeted rows, including exact invalid-UTF-8/BOM coordinates.
- [x] 144 EBNF productions and 82 grammar anchors, 452 positive/negative rows.
  Eighteen formatter/version anchors are explicitly scoped to parser acceptance
  and metadata integrity; fenrir has no formatter. Shared fixture families are
  not a claim of exhaustive derivation or semantic coverage.
- [x] 1,253 corpus files plus 11 own sources: 1,264 accepted/refused as specified.
  The deliberately broken module member inherits its entry's syntax expectation.
- [x] AST connectivity, sibling links, containment, UTF-8 endpoints and coordinates;
  deterministic text/binary emission; separately compiled public-arena consumer.
- [x] Three seeds, 600 random token streams; parentheses/else-if/prefix/type/pattern
  recursion rails; N/10N/100N token/AST scaling under a 1 GiB child address-space cap.
- [x] Linux: a local Linux host, one CPU slot, 12 GiB container, sensor log.
  macOS: bounded build/unit/corpus with memory/disk gates, child timeouts and
  4 GiB RSS watchdog. Fuzz and growing inputs never ran on the Mac.
- [x] Strict skip checks: zero skips. Source refusals are 2, internal errors 70.

Output adaptor: `tests/front/record_output.py`. Its row,
`tests/front/record_output_test.py`, proves that a nonzero command without a FAIL
line produces no named marker and canonical plant verification rejects it;
one indented literal FAIL is re-emitted exactly once at column zero with the
original status. The canonical integration cases also pass in the Mac record.
The adaptor never invents a row or derives a verdict from its text.

Linux final record END lines:
```text
END unit exit=0 secs=0
END oracle-unit exit=0 secs=0
END oracle-readonly exit=0 secs=1
END inventory-scaling exit=0 secs=4
END subset exit=0 secs=1
END diagnostics exit=0 secs=0
END build exit=0 secs=0
END toolchain-tools exit=0 secs=2
END driver exit=0 secs=0
END front-unit exit=0 secs=0
END front-grammar exit=0 secs=1
END front-coverage exit=0 secs=0
END front-unicode exit=0 secs=0
END front-record-output exit=0 secs=0
END front-api exit=0 secs=1
END front-corpus exit=0 secs=15
END front-capped-stress exit=0 secs=6
END determinism exit=0 secs=2
END strict-skips exit=0 secs=0
END oracle-freshness exit=0 secs=0
RECORD-END worst=0 steps=20 end=2026-11-04T09:42:06Z
```

Mac final record END lines:
```text
END build exit=0 secs=0
END driver exit=0 secs=1
END subset exit=0 secs=0
END diagnostics exit=0 secs=0
END front-unit exit=0 secs=0
END front-grammar exit=0 secs=2
END front-coverage exit=0 secs=0
END front-unicode exit=0 secs=0
END record-output exit=0 secs=0
END front-api exit=0 secs=1
END front-corpus exit=0 secs=22
END determinism exit=0 secs=2
END strict-skips exit=0 secs=0
RECORD-END worst=0 steps=13 end=2026-11-04T09:42:09Z
```

Plant: `fn01-plant-unicode-seven` at
`f26cafa0555ad2feb20c41ba15567c0221aeffc6`, one commit/file/hunk on the final
head. Changing the Unicode digit bound from six to seven is red by name:
```text
PLANT base=189e9d9438aee06b9e861d4bcbb2553afdd4eec6 branch=fn01-plant-unicode-seven
PLANT-ROW unicode-seven-digits
END build exit=0 secs=1
FAIL unicode-seven-digits
END front-unit exit=1 secs=0
END record-wrapper exit=1 secs=0
RECORD-END worst=1 steps=3 end=2026-11-04T09:44:57Z
```

## Done-when

The lexer, parser, AST interface, token/AST driver views, corpus/own-source census,
coverage rows, fuzz/scaling, construct inventory, README and diagnostics catalog
are implemented and locally green at the head. Both CI platforms run the new
checks; only Linux runs capped fuzz/scaling. Job caps remain 60 minutes, well
above twice the measured local run. The PR audit and GitHub CI remain the merge
checks; no merge, label, tag or issue filing is performed here.

