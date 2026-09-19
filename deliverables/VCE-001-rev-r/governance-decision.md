# Governance Decision — VCE-001 rev r (claim CLAIM-001, Theorem 1.1)

**Decision: REPAIR.**
**Decided by:** Wilson, in chat, 2026-09-19 ("please repair it", in reply to the question whether to record REPAIR).
**Recorded by:** the assistant (Claude), on Wilson's instruction. The verdict is Wilson's; the assistant did not choose it.
**Recorded after** the final report (EVENT-017), in canonical order (report before decision).

## Basis (spec §26, §53)
The recorded evidence satisfies the gates except Gate 9. The build passed (8033/8033 jobs), the axiom audit passed
(propext, Classical.choice, Quot.sound; no project axiom), the semantic bridge verdict is FAITHFUL WITH EXPLICIT
REPRESENTATIONAL DIFFERENCE (set by Wilson), and computational checks found no counterexample in the tested numeric domain.
**Gate 9 (independent check) has no verdict** for `results_eliahou_theorem_1_1`: lean4export stalls on this proof's large closure.
Promotion is therefore not supported (§53). REPAIR records that the gap is specific, root-caused and fixable.

## What REPAIR means here — and what it does not claim
- It is not a promotion and not a rejection. It does not claim the theorem is independently verified.
- To move toward PROMOTE the Gate 9 gap must be closed: an independent check of this headline theorem must produce a verdict.
  Nothing has been repaired yet; this decision records the intent and the route, not a completed fix.
- Computational evidence is diagnostic only (§16). Reproducibility level R3 is a ceiling supported by recorded evidence; nothing was re-run to earn it.
- The reviewer limitations (Wilson-confirmed): no counterexample was sought against the underlying nontrivial-cycle claim, because that is infeasible.

## Relation to the delivered VCE-001
The delivered VCE-001 run recorded REPAIR before its report (an ordering deviation it discloses itself). This run replays events 1-12
with identical hashes, applies Wilson's confirmed claims clean-up (EVENT-013 supersedes EVENT-002), and records the report before the decision.
The delivered files are unchanged. This decision applies to `verification-001r`.
