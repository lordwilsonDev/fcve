# VCE-001 rev s — corrected verification report, assembled 2026-09-19

**Claim:** Theorem 1.1 (CLAIM-001, Eliahou): for a nontrivial cycle Ω of the compressed Collatz map T with min Ω > 2^40, Card Ω = 301994a + 17087915b + 85137581c with b>0 and ac=0.
**Governance decision (recorded in the receipt, not in the report):** PROMOTE — Wilson's decision, recorded by the assistant on his instruction.

## Files
- `report.pdf` / `report.tex` — the mathematician-facing report (Gate 12). States what the evidence permits; does not state the decision.
- `verification-receipt.md` / `receipt.json` — generated from the ledger after the decision (§48). Decision check: no problems, no blockers; R4.
- `governance-decision.md` — the decision, its basis, and what it does not claim.
- `correction-ledger.md` — two corrections (§46), including the wrong recorded root cause of the Gate 9 stall.
- `independent-check-record.json` — the Gate 9 record (export sha256, checker output, axiom comparison).
- `tool-patches/` — the two diffs (lean4export, nanoda) the independent check depends on.
- `event-ledger.jsonl` — the full hash-chained ledger (19 events). Superseded events (EVENT-002, -011, -015, -016, -017) are kept.
- `MANIFEST.sha256` — sha256 of every file here.

## What this supersedes, and how it differs
Supersedes `deliverables/VCE-001-rev-r/` (REPAIR, Gate 9 open) and the delivered `verification/report/report.pdf`. Both are unchanged. Differences from rev r:
1. **Gate 9 is closed**: INDEPENDENTLY_CHECKED — nanoda re-checked 17,464 declarations, no errors, axioms {propext, Quot.sound, Classical.choice} equal the Gate 6 footprint. Rev r had no verdict, hence REPAIR.
2. The earlier explanation for the Gate 9 stall ("memoization cache") was wrong. The real cause was quadratic decimal conversion of number literals of up to 25.6M digits in both the exporter and the checker; see CORRECTION-002.
3. A fresh machine-produced Gate 6 axiom audit (the earlier one was parsed from legacy text).
4. Reproducibility R4.

## Limitations the report itself states (please read them)
- **The independent check ran patched copies of lean4export and nanoda** (limitation RL-002, stated by Wilson). The patches change only decimal text conversion, not type-checking, and were validated: identical export prefix, five earlier passes reproduce, a corrupted literal is rejected. The patched builds exist only on the recording machine; a third party needs `tool-patches/` to reproduce the check.
- The proof uses Classical.choice.
- Repository, commit and toolchain were captured after the run, not during it.
- No counterexample was sought against the underlying nontrivial-cycle claim (infeasible); computational evidence is diagnostic, not proof.
- 12 of 17 ledger events (12 of 19 counting the report/decision events) predate the §25 hash fields. Compiled with tectonic, not the pdflatex §51 names.

## Provenance
- Final ledger event: `EVENT-019` (`423ea56b7b674777…`; full hash in `receipt.json`)
- Receipt graph hash (v3): `470709ae57ec6c1e0258c4b41064b2ff7f9c9d4766a6b676729de42ca5dc2120`
- First attempts and superseded reports are kept in `verification-001r/`, `verification-001r-attempt1-superseded/` and `verification-001s/report-superseded-*/`.
