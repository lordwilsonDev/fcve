# Governance Decision — VCE-001 (CLAIM-001, Eliahou Theorem 1.1)

## Layer-by-layer status (spec Section 4)

| Layer | Status |
|---|---|
| L1 Source Integrity | PASS — SHA-256 preserved, byte-identical copy |
| L2 Source-Mathematical Integrity | PASS — source read in full, argument coherent, no circularity, no missing hypothesis found |
| L3 Formal Integrity | PASS — Lean kernel accepts the proof under the pinned v4.28.0 toolchain |
| L4 Computational Integrity | SUPPORTIVE — independent Python recomputation of every numeric fact the proof relies on |
| L5 Reproducibility/Independence | **INCOMPLETE** — independent (non-Lean-kernel) check succeeded for 5/9 supporting theorems but could not complete for the headline theorem itself, due to a disclosed, root-caused exporter defect |

Per Section 4's explicit rule, L5's incompleteness is **not** absorbed by L1-L4 passing — each layer stands on its own evidence.

## Why not PROMOTE

PROMOTE requires all mandatory gates to pass (Section 26). L5/Gate 9 does not
pass for this specific theorem — not because the theorem is suspect, but
because the tool meant to provide that layer of trust has a known limitation.
Note: Section 53's MVP *acceptance test* (validating the FCVE pipeline itself,
not this specific claim) explicitly allows "G9 COMPLETED OR N/A WITH REASON" —
that bar is met. But the governance decision for the *claim* is a stricter,
separate question, and Section 4 is explicit that layers don't inherit
passes from each other.

## Why not REJECT

Nothing in Gates 0-8, 10 found any actual defect in the theorem, the proof,
or its formalization. The source-mathematical review, the formal proof, the
axiom audit, the semantic re-audit, and the independent computational
recomputation are all clean. Rejecting would misrepresent strong positive
evidence as a negative finding.

## Why not RESEARCH

RESEARCH is for questions that "cannot currently be resolved." That's not
the situation here — the blocker (Gate 9's exporter defect) is fully
diagnosed, with concrete, known repair paths (patch the exporter's
memoization; or obtain a compatible independent checker under a newer,
compatible toolchain). This is a defect with a defined fix, not an open
question.

## Why not STOP

Nothing here makes further work unsafe or non-reproducible. The correction
ledger entry (a false-mismatch caught and fixed) is itself evidence the
process is working as designed, not evidence it's broken.

## Decision: REPAIR

**Known defect: `lean4export`'s reference implementation cannot complete on
this theorem's proof closure. Repair path: (a) patch or replace the exporter
for large closures, or (b) obtain an independent checker compatible with a
newer Lean/Mathlib pin the target could be bumped to. Until either lands,
CLAIM-001 carries a disclosed, bounded trust gap at Layer 5 only — every
other layer is clean.**

This is a materially different, more precise finding than a plain "not yet
verified": four of five trust layers are fully satisfied, with concrete
evidence for each, and the fifth has a scoped, understood, fixable gap
rather than being simply unattempted.
