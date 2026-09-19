# Governance Decision — VCE-002 rev r (claim `powers_of_two_reach_one`)

**Decision: PROMOTE.**
**Decided by:** Wilson, in chat, 2026-09-19 (chose PROMOTE from the options PROMOTE / REPAIR / RESEARCH / Hold).
**Recorded by:** the assistant (Claude), on Wilson's instruction. The verdict is Wilson's; the assistant did not choose it.
**Re-affirmed:** 2026-09-19, after the report was regenerated (EVENT-017). The first decision (EVENT-016) was on the previous report and became stale under §47; Wilson re-affirmed PROMOTE on the new one (EVENT-018).

## Basis (spec §26, §53)
Promotion requires every mandatory gate to pass. At the time of decision, the §53 gate table for this run showed:
G0-G8, G10, G11 and G12 satisfied; G9 satisfied (independent check passed, recorded in the pre-§17 wording "PASS");
canonical gate order satisfied. No blockers, no waivers. The semantic-bridge verdict (FAITHFUL) is confirmed by Wilson.

## What this decision does NOT claim
- The computational evidence (Gates 8 and 10) is diagnostic: no counterexample found in the tested domain
  (every k in [0,5000]); it is not proof (§16).
- The formal claim rests on the Lean kernel check (axioms: propext, Quot.sound only) and the independent check
  (nanoda, 1662 declarations, 0 errors), both from the original VCE-002 run and replayed here unchanged
  (events 1-10, hashes identical).
- The independent check's result was recorded in legacy wording ("PASS"), not the §17 token INDEPENDENTLY_CHECKED.
- 10 of the 13 ledger events predate the §25 input/output hash fields.
- Reproducibility level R4 is a ceiling supported by recorded evidence; nothing was re-run to earn it.

## Limitations the corrected report now states that the first one hid
- The repository, commit and project location were never recorded for this run, so the build cannot be reproduced exactly from the report.
- The checker used for the independent check is not identified in the record; only its result is.
Wilson re-affirmed PROMOTE with these stated.

## Relation to the delivered VCE-002
The delivered VCE-002 run recorded PROMOTE without a Gate 10 event, which §53 read literally does not support.
This run adds a real Gate 10 and regenerates the graph and report in canonical order, so that PROMOTE is supported.
The delivered files are unchanged. This decision applies to `verification-002r`.
