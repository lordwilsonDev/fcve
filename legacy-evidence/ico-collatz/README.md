# ICO–Collatz Formal Verification Project

BlackSwanLabz Research Lab — Inversion-Oriented Cybernetic Orchestration (ICO)

## Thesis

This project does not begin by trying to prove the Collatz conjecture. It begins by
testing whether an evidence-gated, independently checked Lean workflow can reliably
distinguish a **formally trustworthy** result from a **merely compiling** one.

Layer A (mathematical target): formalizations concerning the Collatz conjecture.
Layer B (verification target, primary experiment): source inspection, version pinning,
clean reconstruction, `sorry` audit, axiom audit, dependency audit, kernel verification,
independent checker verification, adversarial proof-path analysis, and semantic
correspondence between the Lean statement and the mathematical claim.

## Central research question

> Can an ICO-governed verification pipeline distinguish a formally compiled Lean result
> from a sufficiently independently verified mathematical result?

## Status

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for current phase and gate states.

## Structure

- `lean/` — learning exercises, mini proof lab
- `ico_collatz_verification/` — control project (Phase 2 baseline, clean of target contamination)
- `targets/` — cloned target repositories under audit
- `experiments/` — baseline / fixed-toolchain / independent-checker / adversarial runs
- `evidence/` — raw audit outputs (sorry audit, axiom audit, dependency audit, semantic audit)
- `adversarial/` — attack logs (toolchain, dependency, semantic, axiom, build, checker)
- `receipts/` — environment, evidence-chain, correction-ledger, cost-ledger, capability-metric-contract
- `reports/` — human-readable phase reports
- `latex/` — compiled ICO cycle report
- `references/` — source papers, links
- `scripts/` — audit automation (sorry-audit.sh, axiom-audit.sh, etc.)
- `logs/` — build logs
- `hashes/` — SHA-256 manifests
- `archive/` — superseded artifacts

## Governance states

`PROMOTE | REPAIR | REJECT | RESEARCH | STOP`

The compiled PDF is the terminal representation of the evidence chain, not a substitute
for it. The proof is not the deliverable — the evidence chain around the proof is.
