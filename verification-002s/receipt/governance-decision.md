# Governance Decision — VCE-002 rev s (claim `powers_of_two_reach_one`)

**Decision: PROMOTE.**
**Decided by:** Wilson, in chat, 2026-09-19 ("I affirm PROMOTE for VCE-002"), re-affirming the PROMOTE he recorded on `verification-002r`.
**Recorded by:** the assistant (Claude), on Wilson's instruction. The verdict is Wilson's; the assistant did not choose it.
**Recorded after** the final report (EVENT-015), in canonical order.

## Basis (spec §26, §53)
All mandatory gates G0-G12 are satisfied. The run replays `verification-002r` events 1-11 (hashes identical), including the real Gate 10
(5,001 cases with a control, diagnostic only). The semantic-bridge verdict (FAITHFUL) is confirmed by Wilson. No blockers, no waivers.

## What changed relative to rev r
The report now cites a reproduction snapshot: the project `~/ico-collatz/ico_collatz_verification` at commit `409c4c3b6f01…`, clean, no remote,
Lean 4.34.0. This replaces rev r's statement that repository, commit and toolchain were never recorded.

## What this decision does NOT claim
- The snapshot was captured after the run (the project was committed on 2026-09-19). It identifies the source as it is now; it does not
  prove what the original run built. There is no remote, so the repository URL remains not recorded.
- The checker used for the independent check is not identified in the record; only its result is. The result was recorded in legacy
  wording ("PASS"), not the Section 17 token.
- Computational evidence (Gates 8 and 10) is diagnostic, not proof (Section 16). The Gate 8 search examined only k = 0 to 20 and
  k = 50, 100, 500, 1000 (stated by Wilson); Gate 10 covered every k in [0, 5000].
- 10 of the 13 replayed-and-new ledger events predate the Section 25 hash fields.
- Reproducibility level R4 is a ceiling supported by recorded evidence; nothing was re-run to earn it.

## Relation to earlier VCE-002 runs
The delivered VCE-002 recorded PROMOTE without a Gate 10. `verification-002r` re-ran it with a real Gate 10 and recorded PROMOTE. This run
adds the reproduction snapshot and re-affirms that decision on the new report. All earlier runs and deliverables are unchanged. This
decision applies to `verification-002s`.
