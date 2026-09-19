# Correction Ledger — VCE-001 rev r

## CORRECTION-001 — claims extraction EVENT-002 superseded by EVENT-013
- **original_claim**: the delivered VCE-001 `claims.json` (EVENT-002) stated the extraction of Theorem 1.1 accurately.
- **error**: two passages were wrong or unclear. (1) A "fact the statement relies on" mixed up K(2^39) = p_13 with K(2^40) = p_15 in one stream-of-consciousness sentence. (2) Proof step 2 called the interval for k/l "closed-open-ish"; Theorem 2.1 gives log2(3+M^-1) < k/l <= log2(3+m^-1) and M >= m > 2^40, so k/l lies in the open interval (log2(3), log2(3+2^-40)).
- **detection_method**: reading the delivered extraction against the source (p.55, Theorem 2.1) while preparing this revision.
- **root_cause**: hand-written working notes were kept in the extraction as written.
- **repair**: Wilson confirmed two edits (2026-09-19). The cleaned file is `claims-v2/claims.json`; EVENT-013 supersedes EVENT-002. The delivered `verification/claims/claims.json` is unchanged and still hash-matches EVENT-002.
- **recheck**: `validate-claims` passes; the rendered report was read.
- **result**: RESOLVED. Nothing in the proof or the conclusion changed; only the wording of one fact and one interval.
- **date**: 2026-09-19

## CORRECTION-002 — first attempt superseded; report built in passes
- **original_claim**: the first build of this run (archived at `verification-001r-attempt1-superseded/`) was a valid revision.
- **error**: its replayed events kept evidence paths relative to `verification/`, so assumptions, the normalized claim and the Gate 4 comparison printed as "Not recorded" and reproducibility fell to R0.
- **detection_method**: reading the rendered PDF.
- **root_cause**: the run dir did not contain the evidence files its events point to.
- **repair**: the referenced evidence files were copied into this run (delivered files untouched) and the run rebuilt from the same first twelve events (hashes identical). Because a report is built before its own G12 event exists, the report was produced again once that event existed; earlier report events are superseded, and their files are kept in `report-superseded-EVENT-015/`.
- **recheck**: chain, order and graph re-verified; the regenerated PDF read again.
- **result**: RESOLVED. Nothing was deleted.
- **date**: 2026-09-19
