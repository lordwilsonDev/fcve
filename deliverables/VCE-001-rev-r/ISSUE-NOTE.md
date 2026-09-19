# VCE-001 rev r — corrected verification report, assembled 2026-09-19

**Claim:** Theorem 1.1 (CLAIM-001, Eliahou): for a nontrivial cycle Ω of the compressed Collatz map T with min Ω > 2^40, Card Ω = 301994a + 17087915b + 85137581c with b>0 and ac=0.
**Governance decision (recorded in the receipt, not in the report):** REPAIR — Wilson's decision, recorded by the assistant on his instruction. Not a promotion: Gate 9 (independent check) has no verdict for the headline theorem.

## Files
- `report.pdf` / `report.tex` — the mathematician-facing report (Gate 12). States what the evidence permits; does NOT state the decision.
- `verification-receipt.md` / `receipt.json` — generated from the ledger after the decision (§48). Decision check: no problems; blocker: G9.
- `governance-decision.md` — the decision, its basis, and what it does not claim.
- `correction-ledger.md` — two corrections (§46).
- `event-ledger.jsonl` — the full hash-chained ledger (18 events). Superseded events (EVENT-002, -015, -016) are kept.
- `MANIFEST.sha256` — sha256 of every file here.

## What this supersedes, and how it differs
Supersedes the report `verification/report/report.pdf` (sha256 `820ef6a37dcf37e413dfdc1f62a44331be6e9b1818bc2e222d0fd3b5ddf29d26`). That file is unchanged and still exists. Differences:
1. **Canonical order:** the report is recorded before the decision. The delivered run recorded REPAIR before its report (disclosed in its own ledger).
2. **Claims clean-up:** Wilson's two confirmed edits to the extraction (K(2^39) vs K(2^40) fact; step 2's interval is the open interval (log2 3, log2(3+2^-40))). EVENT-013 supersedes EVENT-002; the delivered `claims.json` is unchanged.
3. **Semantic Bridge** with Wilson's verdict (FAITHFUL WITH EXPLICIT REPRESENTATIONAL DIFFERENCE) and the §31 disclosure; **reviewer limitations** stated by Wilson; **reproduction snapshot** (clean checkout at `db804ce6…`).
4. Reproducibility level R3.

## Limitations the report itself states (please read them)
- **Gate 9 has no verdict** for `results_eliahou_theorem_1_1`: lean4export stalls on its large proof closure. This is why the decision is REPAIR, not PROMOTE.
- The proof uses Classical.choice.
- Repository, commit and toolchain were captured after the run, not during it; the checker used for the independent check is not identified.
- No counterexample was sought against the underlying nontrivial-cycle claim (infeasible).
- Computational evidence is diagnostic, not proof. 12 of 18 ledger events predate the §25 hash fields. Compiled with tectonic, not the pdflatex §51 names.
- REPAIR records intent and route only; nothing has been repaired yet.

## Provenance
- Final ledger event: `EVENT-018` (`0e21d873fb6ba0504f10cead26c2f558336de543fb88411cc50c38f2615cb077`)
- Receipt graph hash (v3): `8cf85ca1ee638a781015223e8c9c0b56cc11f9f88fceb2dde1a249599a7fb835`
- The first attempt and superseded reports are kept in `verification-001r-attempt1-superseded/` and `verification-001r/report-superseded-*/`.
