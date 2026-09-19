# VCE-002 rev r — corrected verification report, issued 2026-09-19

**Claim:** `powers_of_two_reach_one` (CLAIM-002): for every k >= 0, iterating the standard Collatz map from 2^k reaches 1.
**Governance decision (recorded in the receipt, not in the report):** PROMOTE — Wilson's decision, recorded by the assistant on his instruction.

## Files
- `report.pdf` / `report.tex` — the mathematician-facing report (Gate 12). It states what the evidence permits and deliberately does NOT state the decision, which is recorded after it (spec §2).
- `verification-receipt.md` / `receipt.json` — the receipt, generated from the ledger after the decision (§48). Decision check: no problems, no blockers.
- `governance-decision.md` — the decision and its stated limits.
- `correction-ledger.md` — four corrections (§46), including two that happened while producing this deliverable.
- `event-ledger.jsonl` — the full hash-chained ledger (18 events). Superseded events (EVENT-013, -014, -015, -016) are kept, not removed.
- `MANIFEST.sha256` — sha256 of every file here.

## What this supersedes, and how it differs
Supersedes the report `verification-002/report/report.pdf` (sha256 `6695bc8c2c6fc45751ac24e85bdc50f12d0e8cdf148cfb6226959a796069ee57`). That file is unchanged and still exists. Differences:
1. **It has the Semantic Bridge section** (mandatory, §57.2) with the verdict FAITHFUL, set by Wilson, and Appendices A-C (Lean source, tests, evidence receipt). The earlier report had neither.
2. **A real Gate 10** now exists (5,001 cases, full trajectory, two implementations, with a control). §53 requires it; the earlier run had none.
3. **The report no longer announces a decision before it is recorded.** The earlier report printed PROMOTE although its ledger recorded the report before the decision.
4. **It states its limitations plainly.**

## Limitations the report itself states (please read them)
- The repository, commit and project location for the build were never recorded, so the build cannot be reproduced exactly from this report.
- The checker used for the independent check is not identified in the record; only its result is.
- Computational evidence (Gates 8 and 10) is diagnostic; it is not proof.
- 10 of 18 ledger events predate the §25 input/output hash fields.
- Reproducibility level R4 is a ceiling supported by recorded evidence; nothing was re-run to earn it.
- Compiled with tectonic, not the pdflatex that §51 names; the compile record says so.

## Provenance
- Final ledger event: `EVENT-018` (`78773f369808b91dbcc612c53bba55c143b8e77547e7ffec39b52a6f820de5e7`)
- Receipt graph hash (v3): `219f692358beb0510c5bd51935390b2eadde98e838b9408e66802b8a2054bc2a`
- The first attempt and the superseded receipts are kept in `verification-002r-attempt1-superseded/` and `verification-002r/receipt/superseded-*/`.
