# Verification Receipt — CLAIM-002 (generated)

_Generated from the ledger and run records by `fcve.py receipt`. Nothing here is hand-written; every field's source is listed at the end._

> **DECISION CHECK FAILED** — the recorded decision is not supported by the evidence:
> - PROMOTE not supported by §53: G11 (PASS: dangling edge endpoint 'GRAPH-002' (event EVENT-015); dangling edge endpoint 'REPORT-002' (event EVENT-015))

**Trust Statement.** The formal result was checked using Lean 4.34.0 under the pinned project environment (Mathlib master 5ed2965). The theorem CLAIM-002 was kernel-checked with axiom footprint propext, Quot.sound. Independent checking status is INDEPENDENTLY_CHECKED (recorded before the Section 17 vocabulary existed, as PASS). Computational/adversarial testing produced: COMPUTATIONALLY_SUPPORTED; NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN (diagnostic only). The remaining trust limitations are: G11 (EVIDENCE_GRAPH): PASS [dangling edge endpoint 'GRAPH-002' (event EVENT-015); dangling edge endpoint 'REPORT-002' (event EVENT-015)]; 10/15 events lack INPUT/OUTPUT_HASH (§25; legacy events, not backfilled); EVENT-009 uses non-§16 wording (COMPUTATIONALLY_SUPPORTED); read as DIAGNOSTIC. This report does not claim that computational testing constitutes formal proof or that formalization alone establishes the truth of the original informal statement.

| Field | Value |
|---|---|
| THEOREM ID | CLAIM-002 (powers_of_two_reach_one) |
| SOURCE HASH | sha256:97d49fbc3576e79f3901ce85f0fb9dd92d9cbf06d6beb933aada6a2f1a194d60 (../verification-002/source/original.md) |
| CLAIM | Every power of two reaches 1 under the standard Collatz function: for f(n) = n/2 if n even, 3n+1 if n odd, and for every k >= 0, iterating f starting from 2^k eventually reaches 1. |
| NORMALIZED CLAIM | verification-002/normalized/normalized-claim.md -- MATCH |
| LEAN STATEMENT | Gate 4: MATCH |
| LEAN VERSION | 4.34.0 |
| MATHLIB VERSION | master 5ed2965 |
| BUILD RESULT | PASS -- 8924/8924 jobs, exit 0, no sorry/admit |
| AXIOM FOOTPRINT | propext, Quot.sound |
| INDEPENDENT CHECK | PASS -- Checked 1662 declarations with no errors. Axioms confirmed: propext, Quot.sound (matches Gate 6 exactly).  (legacy wording) |
| COMPUTATIONAL TEST | NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN -- 5001 cases over: every integer k in [0,5000]; full trajectory 2^k..1; two independent implementations of f; NOT PROOF [diagnostic, not proof] |
| COUNTEREXAMPLE SEARCH | COMPUTATIONALLY_SUPPORTED -- all cases reach 1 in exactly k steps as predicted; no counterexample in tested domain [diagnostic, not proof] |
| SEMANTIC MATCH | Gate 4: MATCH; Gate 7: PASS -- no undisclosed semantic change; axiom footprint itself serves as independent corroboration of the re-audit's conclusion |
| REPRODUCIBILITY LEVEL | R4 (ceiling supported by recorded evidence; NOT re-run by this tool; R5 needs full-package rebuild, not assessed) |
| GRAPH HASH | v3 cb65d7f643c099f6cac8c3cea5f883c5dbf2889472ed6ab0c2867a8c484c8f62 (covers 15 events through EVENT-015) |
| COST | 15 ledger events; LEAN_BUILD_TIME=NOT RECORDED; COMPUTATIONAL_TEST_TIME=7.19; CHECKER_TIME=NOT RECORDED; HUMAN_TIME, MODEL_CALL_COUNT, MODEL_COST, LATEX_BUILD_TIME=NOT RECORDED (no cost ledger, §43) |
| FINAL DECISION | PROMOTE -- NOT SUPPORTED BY THE EVIDENCE (see check) |
| LIMITATIONS | G11 (EVIDENCE_GRAPH): PASS [dangling edge endpoint 'GRAPH-002' (event EVENT-015); dangling edge endpoint 'REPORT-002' (event EVENT-015)]; 10/15 events lack INPUT/OUTPUT_HASH (§25; legacy events, not backfilled); EVENT-009 uses non-§16 wording (COMPUTATIONALLY_SUPPORTED); read as DIAGNOSTIC |

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
GOVERNANCE DECISION:          PROMOTE  <-- NOT SUPPORTED
```

## §53 gate table

| Gate | Ledger action | Event | Status | Satisfied | Note |
|---|---|---|---|---|---|
| G0 | SOURCE_INTAKE | EVENT-001 | PASS | yes |  |
| G1 | CLAIM_EXTRACTION | EVENT-002 | PASS | yes |  |
| G2 | ASSUMPTION_EXTRACTION | EVENT-003 | PASS | yes |  |
| G3 | SEMANTIC_NORMALIZATION | EVENT-004 | PASS | yes |  |
| G4 | LEAN_FORMALIZATION_COMPARISON | EVENT-005 | PASS | yes |  |
| G5 | LEAN_BUILD | EVENT-006 | PASS | yes |  |
| G6 | AXIOM_AUDIT | EVENT-007 | PASS | yes |  |
| G7 | SEMANTIC_RE_AUDIT | EVENT-008 | PASS | yes |  |
| G8 | ADVERSARIAL_COMPUTATIONAL_TEST | EVENT-009 | DIAGNOSTIC | yes |  |
| G9 | INDEPENDENT_CHECK | EVENT-010 | PASS | yes |  |
| G10 | COMPUTATIONAL_CHECK | EVENT-011 | DIAGNOSTIC | yes |  |
| G11 | EVIDENCE_GRAPH | EVENT-012 | PASS | NO | dangling edge endpoint 'GRAPH-002' (event EVENT-015); dangling edge endpoint 'REPORT-002' (event EVENT-015) |
| G12 | REPORT_GENERATION | EVENT-014 | PASS | yes |  |
| G13 | GOVERNANCE_DECISION | EVENT-015 | DECIDED | yes |  |
| ORDER | canonical chain (§2) | - | PASS | yes |  |

## Limitations table (§28) — headline claim only

| Claim | Formal Proof | Axiom Audit | Independent Check | Computational Test | Semantic Match | Limitation |
|---|---|---|---|---|---|---|
| CLAIM-002 | PASS | PASS | PASS | DIAGNOSTIC (no counterexample in tested domain) | PASS / PASS | G11 (EVIDENCE_GRAPH): PASS [dangling edge endpoint 'GRAPH-002' (event EVENT-015); dangling edge endpoint 'REPORT-002' (event EVENT-015)]; 10/15 events lack INPUT/OUTPUT_HASH (§25; legacy events, not backfilled) |

_Per-lemma rows need per-lemma records; the ledger holds results for the headline theorem only, so none are invented._

## Provenance of each field

- **THEOREM ID** — claims.json
- **SOURCE HASH** — file-hash (computed now from the preserved source)
- **CLAIM** — claims.json
- **NORMALIZED CLAIM** — ledger:EVENT-004
- **LEAN STATEMENT** — ledger:EVENT-005
- **LEAN VERSION** — parsed-legacy-text:EVENT-006
- **MATHLIB VERSION** — parsed-legacy-text:EVENT-006
- **BUILD RESULT** — ledger:EVENT-006
- **AXIOM FOOTPRINT** — parsed-legacy-text:EVENT-007
- **INDEPENDENT CHECK** — ledger:EVENT-010
- **COMPUTATIONAL TEST** — ledger:EVENT-011
- **COUNTEREXAMPLE SEARCH** — ledger:EVENT-009
- **SEMANTIC MATCH** — ledger
- **REPRODUCIBILITY LEVEL** — derived: §35 rules
- **GRAPH HASH** — derived from ledger
- **COST** — records
- **FINAL DECISION** — ledger:GOVERNANCE_DECISION

Covers ledger through `EVENT-015` (`b1ce2829c777780d…`). Run `fcve.py receipt-check` to detect staleness.
