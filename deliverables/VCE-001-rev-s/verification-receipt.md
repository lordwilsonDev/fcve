# Verification Receipt — CLAIM-001 (generated)

_Generated from the ledger and run records by `fcve.py receipt`. Nothing here is hand-written; every field's source is listed at the end._

**Trust Statement.** The formal result was checked using Lean 4.28.0 under the pinned project environment (Mathlib v4.28.0 pin). The theorem CLAIM-001 was kernel-checked with axiom footprint Classical.choice, Quot.sound, propext. Independent checking status is INDEPENDENTLY_CHECKED. Computational/adversarial testing produced: COMPUTATIONALLY_SUPPORTED (diagnostic only). The remaining trust limitations are: G8: earlier EVENT-009 recorded a failure; superseded by EVENT-010 (kept in Failure view); classical/external axioms in footprint: Classical.choice; 12/19 events lack INPUT/OUTPUT_HASH (§25; legacy events, not backfilled); EVENT-009 uses non-§16 wording (MISMATCH_FOUND); read as DIAGNOSTIC; EVENT-010 uses non-§16 wording (COMPUTATIONALLY_SUPPORTED); read as DIAGNOSTIC; EVENT-012 uses non-§16 wording (COMPUTATIONALLY_SUPPORTED); read as DIAGNOSTIC; No counterexample was sought against the underlying claim about nontrivial Collatz cycles: doing so would require exhibiting an actual nontrivial cycle, which is computationally infeasible and open-problem-adjacent. The computational checks covered numeric and boundary structure only: the convergents p13, p15 and p16, both Farey identities, and the three boundary inequalities (stated by Wilson); The independent check (Gate 9) ran patched copies of both external tools: lean4export and nanoda with a faster decimal conversion/parse of large number literals, because this proof contains literals of up to 25.6 million digits. The patches touch text conversion only, not type-checking, and were tested (identical export prefix, five earlier passes reproduce, a corrupted literal is rejected). The patched builds exist only on the recording machine; the two diffs are published beside the run (stated by Wilson). This report does not claim that computational testing constitutes formal proof or that formalization alone establishes the truth of the original informal statement.

| Field | Value |
|---|---|
| THEOREM ID | CLAIM-001 (Theorem 1.1) |
| SOURCE HASH | sha256:077292bebdf53a6e06d92fb475ce395ee1c8af4cc3e9f5c2e4620b2e35134689 (source/original.pdf) |
| CLAIM | Let Ω be a nontrivial cycle of T. Provided min Ω > 2^40, we have Card Ω = 301994a + 17087915b + 85137581c, where a,b,c are nonnegative integers, b>0, and ac=0. In particular, the smallest admissible values for Card Ω are 17087915, 17389909, 17691903, and so on. |
| NORMALIZED CLAIM | normalized/normalized-claim.md -- MATCH |
| LEAN STATEMENT | results_eliahou_theorem_1_1 -- Gate 4: MATCH |
| LEAN VERSION | 4.28.0 |
| MATHLIB VERSION | v4.28.0 pin |
| BUILD RESULT | PASS (8033/8033 jobs; see prior receipt for full log) |
| AXIOM FOOTPRINT | Classical.choice, Quot.sound, propext  [reported: Classical.choice] |
| INDEPENDENT CHECK | INDEPENDENTLY_CHECKED -- 17464 declarations re-checked, axioms match Gate 6 |
| COMPUTATIONAL TEST | COMPUTATIONALLY_SUPPORTED -- see EVENT-010 [diagnostic, not proof] |
| COUNTEREXAMPLE SEARCH | COMPUTATIONALLY_SUPPORTED -- all convergents (p13,p15,p16), both Farey identities, and all three boundary inequalities confirmed. Original MISMATCH was a float64 precision artifact in the test script, not a defect in the claim. [diagnostic, not proof] |
| SEMANTIC MATCH | Gate 4: MATCH; Gate 7: PASS -- no undisclosed semantic change; Lean proves numOdd_pos rather than assuming it (stricter than paper) |
| REPRODUCIBILITY LEVEL | R4 (ceiling supported by recorded evidence; NOT re-run by this tool; R5 needs full-package rebuild, not assessed) |
| GRAPH HASH | v3 470709ae57ec6c1e0258c4b41064b2ff7f9c9d4766a6b676729de42ca5dc2120 (covers 19 events through EVENT-019) |
| COST | 19 ledger events; LEAN_BUILD_TIME=NOT RECORDED; COMPUTATIONAL_TEST_TIME=NOT RECORDED; CHECKER_TIME=60.0; HUMAN_TIME, MODEL_CALL_COUNT, MODEL_COST, LATEX_BUILD_TIME=NOT RECORDED (no cost ledger, §43) |
| FINAL DECISION | PROMOTE |
| LIMITATIONS | G8: earlier EVENT-009 recorded a failure; superseded by EVENT-010 (kept in Failure view); classical/external axioms in footprint: Classical.choice; 12/19 events lack INPUT/OUTPUT_HASH (§25; legacy events, not backfilled); EVENT-009 uses non-§16 wording (MISMATCH_FOUND); read as DIAGNOSTIC; EVENT-010 uses non-§16 wording (COMPUTATIONALLY_SUPPORTED); read as DIAGNOSTIC; EVENT-012 uses non-§16 wording (COMPUTATIONALLY_SUPPORTED); read as DIAGNOSTIC; No counterexample was sought against the underlying claim about nontrivial Collatz cycles: doing so would require exhibiting an actual nontrivial cycle, which is computationally infeasible and open-problem-adjacent. The computational checks covered numeric and boundary structure only: the convergents p13, p15 and p16, both Farey identities, and the three boundary inequalities (stated by Wilson); The independent check (Gate 9) ran patched copies of both external tools: lean4export and nanoda with a faster decimal conversion/parse of large number literals, because this proof contains literals of up to 25.6 million digits. The patches touch text conversion only, not type-checking, and were tested (identical export prefix, five earlier passes reproduce, a corrupted literal is rejected). The patched builds exist only on the recording machine; the two diffs are published beside the run (stated by Wilson) |

## Status (§55)

```
FORMAL PROOF (build):         PASS
AXIOM AUDIT:                  PASS
SEMANTIC MATCH (Gate 4):      PASS
SEMANTIC RE-AUDIT (Gate 7):   PASS
INDEPENDENT CHECK:            PASS
COUNTEREXAMPLE SEARCH:        DIAGNOSTIC (no counterexample in tested domain)
COMPUTATIONAL TEST:           DIAGNOSTIC (no counterexample in tested domain)
REPRODUCIBILITY:              R4 (evidence-supported ceiling)
GOVERNANCE DECISION:          PROMOTE
```

## §53 gate table

| Gate | Ledger action | Event | Status | Satisfied | Note |
|---|---|---|---|---|---|
| G0 | SOURCE_INTAKE | EVENT-001 | PASS | yes |  |
| G1 | CLAIM_EXTRACTION | EVENT-013 | PASS | yes |  |
| G2 | ASSUMPTION_EXTRACTION | EVENT-003 | PASS | yes |  |
| G3 | SEMANTIC_NORMALIZATION | EVENT-004 | PASS | yes |  |
| G4 | LEAN_FORMALIZATION_COMPARISON | EVENT-005 | PASS | yes |  |
| G5 | LEAN_BUILD | EVENT-006 | PASS | yes |  |
| G6 | AXIOM_AUDIT | EVENT-007 | PASS | yes |  |
| G7 | SEMANTIC_RE_AUDIT | EVENT-008 | PASS | yes |  |
| G8 | ADVERSARIAL_COMPUTATIONAL_TEST | EVENT-010 | DIAGNOSTIC | yes | earlier EVENT-009 recorded a failure; superseded by EVENT-010 (kept in Failure view) |
| G9 | INDEPENDENT_CHECK | EVENT-014 | PASS | yes |  |
| G10 | COMPUTATIONAL_CHECK | EVENT-012 | DIAGNOSTIC | yes |  |
| G11 | EVIDENCE_GRAPH | EVENT-015 | PASS | yes |  |
| G12 | REPORT_GENERATION | EVENT-018 | PASS | yes |  |
| G13 | GOVERNANCE_DECISION | EVENT-019 | DECIDED | yes |  |
| ORDER | canonical chain (§2) | - | PASS | yes |  |

## Limitations table (§28) — headline claim only

| Claim | Formal Proof | Axiom Audit | Independent Check | Computational Test | Semantic Match | Limitation |
|---|---|---|---|---|---|---|
| CLAIM-001 | PASS | PASS | PASS | DIAGNOSTIC (no counterexample in tested domain) | PASS / PASS | G8: earlier EVENT-009 recorded a failure; superseded by EVENT-010 (kept in Failure view); classical/external axioms in footprint: Classical.choice |

_Per-lemma rows need per-lemma records; the ledger holds results for the headline theorem only, so none are invented._

## Provenance of each field

- **THEOREM ID** — claims.json
- **SOURCE HASH** — file-hash (computed now from the preserved source)
- **CLAIM** — claims.json
- **NORMALIZED CLAIM** — ledger:EVENT-004
- **LEAN STATEMENT** — record:axiom-audit + ledger
- **LEAN VERSION** — parsed-legacy-text:EVENT-006
- **MATHLIB VERSION** — parsed-legacy-text:EVENT-006
- **BUILD RESULT** — ledger:EVENT-006
- **AXIOM FOOTPRINT** — record:axiom-audit-record.json
- **INDEPENDENT CHECK** — record:independent-check-record.json
- **COMPUTATIONAL TEST** — ledger:EVENT-012
- **COUNTEREXAMPLE SEARCH** — ledger:EVENT-010
- **SEMANTIC MATCH** — ledger
- **REPRODUCIBILITY LEVEL** — derived: §35 rules
- **GRAPH HASH** — derived from ledger
- **COST** — records
- **FINAL DECISION** — ledger:GOVERNANCE_DECISION

Covers ledger through `EVENT-019` (`423ea56b7b674777…`). Run `fcve.py receipt-check` to detect staleness.
