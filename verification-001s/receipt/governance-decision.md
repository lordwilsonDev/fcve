# Governance Decision — VCE-001 rev s (claim CLAIM-001, Theorem 1.1)

**Decision: PROMOTE.**
**Decided by:** Wilson, in chat, 2026-09-19 ("PROMOTE", chosen from PROMOTE / keep REPAIR / Hold).
**Recorded by:** the assistant (Claude), on Wilson's instruction. The verdict is Wilson's; the assistant did not choose it.
**Recorded after** the final report (EVENT-018), in canonical order.

## Basis (spec §26, §53)
All mandatory gates G0-G12 are satisfied in this run. Gate 9, which had no verdict in the delivered VCE-001 and in the REPAIR run
(`verification-001r`), now records INDEPENDENTLY_CHECKED: nanoda re-checked 17,464 declarations with no errors and its axiom set
(propext, Quot.sound, Classical.choice) equals the fresh Gate 6 footprint. The semantic-bridge verdict is FAITHFUL WITH EXPLICIT
REPRESENTATIONAL DIFFERENCE (set by Wilson). No blockers, no waivers.

## What this decision does NOT claim
- **The independent check ran patched copies of both external tools** (lean4export and nanoda, fast decimal conversion/parse of number
  literals up to 25.6M digits). The patches touch text conversion only, not type-checking, and were validated (identical export prefix,
  five earlier passes reproduce identically, a corrupted literal is rejected). The patched builds exist only on the recording machine; the
  diffs are in `tool-patches/`. Wilson confirmed this limitation (RL-002) before deciding.
- The proof uses Classical.choice; it is a classical proof.
- Computational evidence (Gates 8 and 10) is diagnostic, not proof (§16). No counterexample was sought against the underlying
  nontrivial-cycle claim, because that is infeasible.
- The repository, commit and toolchain facts were captured after the run, not during it.
- 12 of 17 ledger events predate the §25 input/output hash fields.
- Reproducibility level R4 is a ceiling supported by recorded evidence; nothing was re-run to earn it beyond the Gate 9 run recorded here.

## Relation to earlier VCE-001 runs
The delivered VCE-001 recorded REPAIR before its report. `verification-001r` recorded REPAIR (Wilson's, EVENT-018) with Gate 9 open.
This run supersedes the Gate 9 no-verdict (EVENT-011 → EVENT-014) and replaces this decision for the claim. Both earlier runs and their
deliverables are unchanged. This decision applies to `verification-001s`.
