# Evidence Chain

Each completed audit must be reconstructable along this chain, with every arrow
backed by a specific file under `evidence/`, `receipts/`, or `experiments/`.

```
FINAL CLAIM
  ↑ receipts/governance-decision.md (not yet created — Phase 24)
GOVERNANCE DECISION
  ↑ receipts/capability-metric-contract.md
FINDING
  ↑ evidence/ (semantic-audit.md, axiom-audit.md, sorry-audit.md, dependency-audit.md)
EXPERIMENT
  ↑ experiments/{baseline,fixed-toolchain,independent-checker,adversarial}/
PREDICTION
  ↑ reports/threat-model.md (T1-T10) + per-threat prediction (Phase 20, not yet written)
MECHANISM
  ↑ (Phase 16, written once a positive deviance is found)
POSITIVE DEVIANCE
  ↑ (Phase 15, written once the target repo is audited)
INVERSION
  ↑ "compiles ≠ trustworthy" (see README.md thesis)
QUESTION
  ↑ research-question.md
OPERATIONAL TRUTH
  ↑ receipts/environment.md (Lean 4.34.0 / Mathlib 5ed2965, control project green)
```

## Status as of 2026-09-18

Populated: OPERATIONAL TRUTH, QUESTION, INVERSION.
Not yet populated: everything from POSITIVE DEVIANCE upward — these depend on
Phase 7 (clone target repo) and Phase 8 (reproduce its build), which are the
next actions.
