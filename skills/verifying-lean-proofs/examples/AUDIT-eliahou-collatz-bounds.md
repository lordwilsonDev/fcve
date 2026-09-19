# Proof audit: eliahou-collatz-bounds

- target: `/Users/lordwilson/ico-collatz/targets/eliahou-collatz-bounds`
- module: `Results`
- declarations: results_farey_pair_bound results_eliahou_theorem_1_1

## Verdict: PROVISIONAL (automated rows have no active failure; rows below keep it out of TRUSTED)

Rows keeping it out of TRUSTED: 3, 7, 8, 9, 10. This script cannot reach TRUSTED: rows 7 and 9 need a human and the web.

| # | Gate | Status | Evidence / note |
|---|---|---|---|
| 1 | Source pinned | **PASS** | commit db804ce6305ea99a817f067869607f8b677d895a, remote https://github.com/tangentstorm/eliahou-collatz-bounds.git, working tree clean |
| 2 | Toolchain pinned | **PASS** | lean-toolchain=leanprover/lean4:v4.28.0; mathlib rev=8f9d9cff6bd728b17a24e163c9402775d9e6a365; drift vs your control environment NOT compared (do that by hand) |
| 3 | Clean rebuild | **PARTIAL** | lake build succeeded, but against an existing .lake cache (not from-empty): reproducibility from a clean clone NOT shown |
| 4 | No sorry/admit | **PASS** | 0 sorry, 0 admit (text scan; row 6 is the authoritative check) |
| 5 | No native_decide | **PASS** | 0 native_decide |
| 6 | Axiom footprint | **PASS** | every declaration's axioms within {propext,Classical.choice,Quot.sound} (axioms.tsv). Classical.choice, if listed, means the proof is classical |
| 7 | Semantic correspondence | **NEEDS HUMAN** | read the source claim (paper/spec) against each Lean statement side by side; write the comparison. Print statements: 'lake env lean' with #check / delaborated statements. MATCH/PARTIAL/MISMATCH/UNCLEAR is a human verdict (a model may draft, not certify). |
| 8 | Self-description not stale | **PARTIAL** | descriptive files older than HEAD: ARISTOTLE_SUMMARY.md(7 commits behind). Do NOT cite them as evidence of the current state; verify claims fresh. |
| 9 | Kernel vulnerability exposure | **UNRESOLVED** | needs live web access: compare leanprover/lean4:v4.28.0 against release notes for kernel soundness fixes. Starting list: LESSONS.md D22 (lean4lean bugs-found). Marked UNRESOLVED, not skipped. |
| 10 | Independent check | **PARTIAL** | PASS 2/2 with PATCHED (fast decimal literals: patches/*.diff) -- DISCLOSE. A verdict from patched tools must be disclosed and validated (SKILL.md 'Patched tools'); results in row10-results.tsv |

## Timing (wall clock, seconds)

| step | s |
|---|---|
| rows1-2 | 0 |
| row3-build | 7 |
| rows4-5 | 0 |
| row6-axioms | 151 |
| row8-stale | 1 |
| setup-pristine | 0 |
| independent-check-pristine | 346 |
| setup-fast | 0 |
| independent-check-fast | 350 |
| row10-independent | 697 |
| **total** | **1552** |

## Files
`rows.tsv`, `audit.log`, `build.log`, `sorry-audit.txt`, `axioms.tsv`, `axioms-all.txt`, `independent-check*/`, `row10-results.tsv`, `row10-tools.tsv`, `setup*.log`.

Provenance: this is an automated pass. Never write "proved" as a bare verdict; state the verdict above and list what keeps it from TRUSTED.
