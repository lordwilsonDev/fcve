# Capability Metric Contract

## Capability under test

Evidence-gated formal-verification pipeline capable of independently auditing
Lean mathematical results.

## Baseline (before this project)

Undocumented / ad hoc: "does it compile" was the de facto trust signal for any
Lean formalization referenced informally.

## Post-intervention (this pipeline)

A target formalization is only claimed TRUSTED/PROVISIONAL/UNRESOLVED/REJECTED
after passing through the full Proof Trust Matrix (Phase 19): source available,
commit pinned, Lean/Mathlib versions pinned, clean rebuild, no `sorry`, axiom
audit, dependency audit, semantic correspondence, kernel verification,
independent checker, reproducibility, adversarial review.

## Success threshold

All mandatory verification gates (source, build, sorry, axiom, semantic
correspondence) produce reproducible, re-runnable evidence — i.e., a second
person following `receipts/` and `scripts/` gets the same answers without
re-deriving anything from scratch.

## Failure threshold

Any critical trust gate (no clean rebuild, undisclosed axiom, semantic mismatch
between the Lean statement and the paper's claim) cannot be reproduced or
independently evaluated.

## Observation window

The duration of the complete Phase 7–34 audit of the first target repository
(`tangentstorm/eliahou-collatz-bounds`).

## Rollback

If the pipeline itself proves unreliable (e.g. Phase 15's meta-validation
experiment — deliberately injecting a defect — goes undetected), return to the
last known-reproducible environment (this receipt + `environment.md`) and do
not scale the pipeline to a second target until the miss is understood and
fixed.
