# VCE-002 rev s — corrected verification report, assembled 2026-09-19

**Claim:** `powers_of_two_reach_one` (CLAIM-002): for every k >= 0, iterating the standard Collatz map from 2^k reaches 1.
**Governance decision (recorded in the receipt, not in the report):** PROMOTE — Wilson's decision (re-affirming the rev-r PROMOTE), recorded by the assistant on his instruction.

## Files
- `report.pdf` / `report.tex` — the mathematician-facing report (Gate 12). States what the evidence permits; does not state the decision.
- `verification-receipt.md` / `receipt.json` — generated from the ledger after the decision (§48). Decision check: no problems, no blockers; R4.
- `governance-decision.md` — the decision, its basis, and what it does not claim.
- `correction-ledger.md` — one correction (§46) and a note on what changed from rev r.
- `vce-002-repro-snapshot.json` — the reproduction snapshot the report cites.
- `event-ledger.jsonl` — the full hash-chained ledger (16 events). Superseded events (EVENT-013, -014) are kept.
- `MANIFEST.sha256` — sha256 of every file here.

## What this supersedes, and how it differs
Supersedes `deliverables/VCE-002-rev-r/` (report sha256 `25aaed88…`) and the delivered `verification-002/report/report.pdf` (`6695bc8c…`). Both are unchanged. Difference from rev r:
1. **Reproduction:** rev r said the repository, commit and toolchain were never recorded. This revision cites a snapshot of the project at commit `409c4c3b6f0179ae9131ac2450998e59a7fb1132` (clean, no remote, Lean 4.34.0, Mathlib `5ed29652…`).
2. Fixed a report wording bug found while building it (a clean local-only commit was described as "not recorded"); see CORRECTION-001.

Everything else — the real Gate 10 (5,001 cases with a control), the Semantic Bridge (FAITHFUL, set by Wilson), the stated limitations — is carried over from rev r; events 1-11 replay with identical hashes.

## Limitations the report itself states (please read them)
- The snapshot was captured **after** the run (the project was committed on 2026-09-19). It identifies the source as it is now; it does not prove what the original run built. There is no remote, so the repository URL is not recorded.
- The checker used for the independent check is not identified in the record; only its result is.
- Computational evidence (Gates 8 and 10) is diagnostic, not proof. Gate 8 examined only k = 0 to 20 and k = 50, 100, 500, 1000 (stated by Wilson).
- 10 of the ledger events predate the §25 hash fields. Compiled with tectonic, not the pdflatex §51 names.

## Provenance
- Final ledger event: `EVENT-016` (`ced80197668d664a…`; full hash in `receipt.json`)
- Receipt graph hash (v3): `b6fd7481e3a1a68789bef42f24c444491b0ed171591d7f19d5507d9a890f4149`
- Superseded reports are kept in `verification-002s/report-superseded-*/`.
