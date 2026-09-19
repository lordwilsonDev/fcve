# Superseded attempt — do not cite

First build of VCE-002 "rev r". Its report (EVENT-013) said "Promotion is not supported because: G12 (report
generation): missing", because the permitted-status logic counted the report's own not-yet-written Gate 12 event
as a blocker (a circularity in `fcve_receipt.permitted_status`, fixed 2026-09-19). Kept intact for the record; the
corrected run is `../verification-002r/`.
