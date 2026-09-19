# Correction Ledger — VCE-002 rev s

## CORRECTION-001 — report EVENT-014 superseded: local-only commit described as "not recorded"
- **original_claim**: the Reproducibility Instructions of the first rev-s report were accurate.
- **error**: with a clean project at a commit but no remote, the report listed the commit in its table and then printed the comment "repository location and commit were not recorded for this run (see table above)", which contradicts the table.
- **detection_method**: reading the rendered PDF.
- **root_cause**: the reproduction-instructions builder had no branch for CLEAN_AT_COMMIT without a remote and fell through to the "nothing recorded" default.
- **repair**: a branch now says the commit is local only and gives the `git checkout` target without a clone command; regression test added (`test_clean_local_only_commit_is_not_called_unrecorded_and_gets_no_clone_command`). The report was regenerated; EVENT-014 stays in the ledger, superseded; its files are kept in `report-superseded-EVENT-014/`.
- **recheck**: `tests/test_fcve_report.py` passes; the regenerated PDF was read again.
- **result**: RESOLVED. Nothing was deleted. The facts (commit `409c4c3b6f01…`, clean, no remote) were correct throughout; only the comment was wrong.
- **date**: 2026-09-19

## Note — what rev s changes relative to rev r (not a correction)
Rev r said the repository, commit and toolchain "were never recorded". Rev s cites a reproduction snapshot of the project at commit `409c4c3b…`, taken after the runs (the project was committed on 2026-09-19). It identifies the source as it is now; it does not prove what the original 2026-09 runs built. The checker is still not identified in the record.
