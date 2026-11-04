## Prediction

The frame accepts no Wolf programs yet. Every driver seam refuses with status 2, preserves existing output, and keeps compiler errors distinct from environment skips. The oracle table records disagreements rather than manufacturing compiler coverage.

## Forbidden

Reference compiler implementation source was not read. The inputs are the public specification/corpus and black-box binaries. Issue files are drafts only. Plant branches have no PR or CI dispatch.

## Inputs verified

Footprint: cross-cutting

- wolf 0.2.36, lupin 0.1.58; public spec/corpus `5f1f1c949582f53121e4047bc83c86f23ff72240`.
- Generated clef `900bdf0a8f8f447bcc1505ecad1f65a367105dcc`, ligature `c8ca1be4b3ccb7f8c425638e2d1145d21a62ee5a`, licensed link bundle and matching 0.2.36 runtime pins; every digest read twice.
- Stable driver/module interfaces, exact pin staging, bootstrap construct inventory and empty diagnostic catalog.

Commit index:
- `e6c128e` prediction; `d4a8b7b` frame/interfaces; `86dd7b5` construct inventory.
- `475c485` private no-cache outputs and immutable-package checks; `9a3f619` protocol-only native classification.
- `538af69` pure capture rederivation, scoped root-exit equivalence and oracle-only freshness identity.
- `d5ca36f` generated tool pin updates; `40056e3` complete oracle table.
- `af86e83` issue/disposition drafts; `a36098e` grouped evidence and ten hand checks; `dc8a510` README.

## Evidence index

Two complete Linux captures enumerate 1,253 rows: **827 same-observed, 109 differs, 252 scope gaps, one oracle error, 64 module members**, identical bucket counts across passes. Four race/UB rows change and retain both observations. Scope gaps are 224 Lupin-only, 22 wolf-only and six both. This is oracle evidence, not fenrir coverage.

The 109 differences are grouped in [HARNESS](docs/HARNESS.md): 88 explicit-phase stops, 13 UB-vs-native outcomes, three static-vs-dynamic outcomes, four stdout differences, one region-lifetime outcome. The native mixed-row ICE and the output/lifetime cases have seven [issue/disposition drafts](notes/fn00/issues/). Ten cross-directory rows were hand-checked. Root-domain exits 121/1 remain raw; only the explicitly anchored nonzero class compares equal.

Exact-final-head macOS record at `a9f56923f81233a6601d13a72ed9429d0969bdbc`, recorded 2026-11-04 09:07:38–09:07:43Z, is green:

```text
END unit exit=0 secs=1
END oracle-unit exit=0 secs=0
END oracle-readonly exit=0 secs=1
END subset exit=0 secs=0
END diagnostics exit=0 secs=0
END build exit=0 secs=0
END toolchain-tools exit=0 secs=2
END driver exit=0 secs=0
END determinism exit=0 secs=0
END strict-skips exit=0 secs=1
END oracle-freshness exit=0 secs=0
```

The exact-head local Linux record is still queued behind both host locks; it is not claimed green. The completed two-pass Linux oracle capture and earlier Linux integration are separate evidence, not substitutes for that pending final-head record.

Plant `fn00-plant-refusals-pass`, `f99665b24a30189cb387b248ededc2e6cd5a8271`, is one commit, one file, one hunk on the final head. Local record excerpt (trace paths omitted):

```text
PLANT base=a9f56923f81233a6601d13a72ed9429d0969bdbc branch=fn00-plant-refusals-pass
PLANT-ROW refusal-is-not-agreement
START refusal-is-not-agreement
  AssertionError: 0 == 0
FAIL refusal-is-not-agreement refusal was counted as same and compare returned success
END refusal-is-not-agreement exit=1 secs=0
START record-wrapper
END record-wrapper exit=1 secs=0
```

## Done-when

- [x] Two complete black-box oracle captures, pure freshness rederivation and side-specific scope census.
- [x] Gate negative controls, read-only-package integration, diagnostic-like program stderr controls and scoped root-exit regression.
- [x] Local one-hunk refusal plant red by name; no plant PR.
- [x] Exact-final-head macOS build, tool builds, unit/integration tests, determinism, strict gates and table freshness.
- [ ] Exact-final-head Linux gates, scaling and table freshness.
- [x] Linux/macOS PR CI and the single lane audit.

The compiled bootstrap subset remains empty. Its used-but-not-compiled construct gap is printed and becomes mandatory at the explicit subset-close switch. Front-end and backend implementations land separately; their interfaces are documented in `docs/DRIVER.md`.

CI run `41804103517` completed successfully at the head. The single audit independently verified every job and step, the exact-head Mac record and the one-hunk named-red plant. Its final line was `AUDIT CLEAN (footprint: cross-cutting)`. The supplemental exact-head local Linux job is still pending its host locks and remains explicitly unchecked above.

