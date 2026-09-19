# Correction Ledger — VCE-002 rev r

## CORRECTION-001 — first attempt superseded
- **original_claim**: the first build of this run (archived at `verification-002r-attempt1-superseded/`) produced a report saying "Promotion is not supported because: G12 (report generation): missing".
- **error**: false. Every gate except the governance decision (G13) was satisfied.
- **detection_method**: reading the rendered PDF after verifying the ledger and gate table; the report's claim disagreed with the §53 table.
- **root_cause**: `permitted_status` counted G12 as a blocker, but a report is built before its own Gate 12 event exists, so G12 was always "missing" at that moment (a circularity in the tool).
- **repair**: G12 is ignored when the report computes what the evidence permits; the report states the assumption that it compiles cleanly. Same-day regression tests added.
- **recheck**: the whole run was rebuilt from the same first ten events (hashes identical) and re-verified: chain intact, canonical order, graph current.
- **result**: RESOLVED. The first attempt is kept, not deleted.
- **date**: 2026-09-19

## CORRECTION-002 — report EVENT-013 superseded by EVENT-014
- **original_claim**: report EVENT-013 was correct.
- **error**: it printed a literal "\S 53" in the permitted-status paragraph (a doubly escaped section sign). Cosmetic; no fact was wrong.
- **detection_method**: reading the rendered PDF text.
- **root_cause**: a `\S` written into text that is then LaTeX-escaped.
- **repair**: the wording now reads "Section 53"; Gate 12 was re-run, appending EVENT-014. EVENT-013 stays in the ledger; EVENT-014 supersedes it.
- **recheck**: the regenerated PDF was read again.
- **result**: RESOLVED.
- **date**: 2026-09-19

## CORRECTION-003 — decision EVENT-015 superseded by EVENT-016 (mistyped input ids)
- **original_claim**: decision EVENT-015 (PROMOTE, recorded on Wilson's instruction) was a valid record.
- **error**: its inputs were `GRAPH-002,REPORT-002`, but this run's nodes are `GRAPH-002r` and `REPORT-002r`. The ids named nothing, so the v3 graph had dangling edges, G11 failed, and the receipt generated from it reported "PROMOTE not supported by §53: G11" — a true statement about a malformed record, not about the evidence. The decision itself (PROMOTE, by Wilson) was unaffected.
- **detection_method**: the receipt's own decision check (`fcve_receipt.check_decision`) on first generation.
- **root_cause**: (1) the assistant typed the wrong input ids; (2) nothing checked input ids at append time; (3) the graph builder kept the edges of superseded events, so a superseding event could not have cleared the dangling edges.
- **repair**: EVENT-016 re-records the same decision with the correct inputs; EVENT-015 stays in the ledger. The graph now drops superseded events; `append` now refuses an input id no earlier event produced (`check_inputs`, on in the CLI and batch). The flawed receipt is archived in `receipt/superseded-EVENT-015/`, not deleted, and the receipt regenerated.
- **recheck**: chain, order, graph and receipt re-verified after the correction.
- **result**: RESOLVED.
- **date**: 2026-09-19

## CORRECTION-004 — report EVENT-014 superseded by EVENT-017; decision EVENT-016 superseded by EVENT-018
- **original_claim**: report EVENT-014 was the final report; its Trust Statement said the remaining limitations were "none recorded".
- **error**: misleading. The report's own Reproducibility section said the repository, commit, project location and checker were NOT RECORDED, so "none" contradicted it and a reader would take it as "no limitations".
- **detection_method**: reading the rendered PDF as a mathematician before issuing it (§61), not from any automated check.
- **root_cause**: the limitations builder only listed unsatisfied gates; a recording gap is not a gate, so it was never listed.
- **repair**: missing reproduction facts and an unidentified checker are now substantive limitations (regression-tested). The report was regenerated (EVENT-017). That replaced the input of decision EVENT-016, so §47 marks it stale (the staleness engine now detects a replaced upstream event, not only a changed file); Wilson re-affirmed PROMOTE as EVENT-018. The old receipt is archived in `receipt/superseded-EVENT-016/`.
- **recheck**: chain, order, graph and receipt re-verified; the regenerated PDF read again.
- **result**: RESOLVED. Nothing was deleted; every superseded event and file is kept.
- **date**: 2026-09-19
- **note**: this entry was written after report EVENT-017 was generated, so it appears in the ledger file but not in that report's Correction Ledger section.
