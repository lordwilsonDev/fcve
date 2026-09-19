# Correction Ledger — VCE-001

## CORRECTION-001

- **original_claim**: The independent computational adversarial check (Gate 8) reported `p16/q16 < log2(3)` as `False`, triggering "MISMATCH FOUND -- STOP".
- **error**: A false mismatch — not a real defect in the theorem, the Lean proof, or the paper.
- **detection_method**: Before accepting a STOP verdict, per Gate 8's own rule ("a failed counterexample search is diagnostic evidence only" — the symmetric discipline applies to a *found* discrepancy too: verify it before trusting it), the comparison was re-run using `mpmath`'s 60-digit precision instead of native Python `float` (float64, ~15-17 significant digits) for both sides of the inequality.
- **root_cause**: `p16/q16` and `log2(3)` agree to approximately 16 significant digits — that closeness is *exactly what makes p16/q16 a good continued-fraction convergent* in the first place. Comparing two float64 values that agree to 16 digits is comparing them past the precision float64 can reliably represent, so the comparison's result was noise, not signal.
- **repair**: Rewrote the boundary-check section of `verify_convergents.py` to use `mpmath.mpf` at 60 decimal digits for both `theta` and the rational convergent ratios, rather than casting either to native `float`.
- **recheck**: Re-ran the full script. All boundary inequalities (`p16/q16 < log2(3) < p15/q15 < p13/q13`) now report `True`, consistent with the paper (p.55) and the Lean proof.
- **result**: RESOLVED — false mismatch, root cause understood, fix verified by re-running (not just reasoned about).
- **date**: 2026-09-19
- **hash**: see `verification/evidence/event-ledger.jsonl` EVENT-009/EVENT-010 for the hash-chained record of both the original run and the corrected re-run.

## CORRECTION-002

- **original_claim**: (implicit) that this run followed the spec's canonical chain order (Section 2: ... → EVIDENCE GRAPH → HUMAN-READABLE REPORT → GOVERNANCE DECISION).
- **error**: Gate 13 (Governance Decision, EVENT-014) was logged *before* Gate 12 (Report Generation, EVENT-015) — the reverse of the canonical order.
- **detection_method**: Noticed while updating the report's graph-hash reference after rebuilding the evidence graph a second time (once at 12 events, again at 15) — the discrepancy between "the report cites a graph hash" and "the graph didn't include the report yet when the decision was made" surfaced the ordering issue.
- **root_cause**: The governance decision was drafted immediately after Gate 11 (evidence graph) because all the evidence needed to decide (L1-L5 status) already existed at that point; report-writing was treated as a documentation step and deferred, without checking it against the spec's stated canonical order first.
- **repair**: None applied to the ledger itself — it is append-only and hash-chained by design specifically so that the actual order of operations is preserved, not rewritten after the fact. The correct repair is disclosure, which is this entry.
- **result**: The decision's *content* is unaffected — the report doesn't introduce new evidence, it packages existing evidence, so reordering it after the decision changes nothing material. But the process deviation is real and is recorded rather than hidden, consistent with Section 46's rule that corrections "remain in history" and are "never silently overwritten."
- **date**: 2026-09-19

## Why this entry matters beyond this one theorem

This is the exact failure mode Gate 8 exists to catch in *either* direction:
a computational test can produce a false negative (says PASS when the claim
is actually false) or a false positive failure (says MISMATCH when the claim
is actually true, because the *test* was imprecise). Both directions must be
verified before being trusted, not just the direction that would embarrass
the target. This entry is kept rather than deleted precisely because the
correction ledger's job is to show the discipline was applied, not to
present a record that looks clean because the mistake was erased.
