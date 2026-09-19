# Proof audit: ico_collatz_verification

- target: `/Users/lordwilson/ico-collatz/ico_collatz_verification`
- module: `IcoCollatzVerification.PowersOfTwoReachOne`
- declarations: powers_of_two_reach_one

## Verdict: PROVISIONAL (automated rows have no active failure; rows below keep it out of TRUSTED)

Rows keeping it out of TRUSTED: 3, 7, 9. This script cannot reach TRUSTED: rows 7 and 9 need a human and the web.

| # | Gate | Status | Evidence / note |
|---|---|---|---|
| 1 | Source pinned | **PASS** | commit 409c4c3b6f0179ae9131ac2450998e59a7fb1132, remote https://github.com/lordwilsonDev/ico-collatz-verification.git, working tree clean |
| 2 | Toolchain pinned | **PASS** | lean-toolchain=leanprover/lean4:v4.34.0; mathlib rev=5ed2965256430c3649e86755f9576b54eca72435; drift vs your control environment NOT compared (do that by hand) |
| 3 | Clean rebuild | **PARTIAL** | lake build succeeded, but against an existing .lake cache (not from-empty): reproducibility from a clean clone NOT shown |
| 4 | No sorry/admit | **PASS** | 0 sorry, 0 admit (text scan; row 6 is the authoritative check) |
| 5 | No native_decide | **PASS** | 0 native_decide |
| 6 | Axiom footprint | **PASS** | every declaration's axioms within {propext,Classical.choice,Quot.sound} (axioms.tsv). Classical.choice, if listed, means the proof is classical |
| 7 | Semantic correspondence | **NEEDS HUMAN** | read the source claim (paper/spec) against each Lean statement side by side; write the comparison. Print statements: 'lake env lean' with #check / delaborated statements. MATCH/PARTIAL/MISMATCH/UNCLEAR is a human verdict (a model may draft, not certify). |
| 8 | Self-description not stale | **PASS** | no root-level .md file is older than HEAD (still: cite only what this audit re-checked) |
| 9 | Kernel vulnerability exposure | **UNRESOLVED** | needs live web access: compare leanprover/lean4:v4.34.0 against release notes for kernel soundness fixes. Starting list: LESSONS.md D22 (lean4lean bugs-found). Marked UNRESOLVED, not skipped. |
| 10 | Independent check | **PASS** | PASS 1/1 with upstream (unpatched); raw checker output in independent-check*/; still compare its axiom set with row 6 |

## Timing (wall clock, seconds)

| step | s |
|---|---|
| rows1-2 | 0 |
| row3-build | 9 |
| rows4-5 | 0 |
| row6-axioms | 197 |
| row8-stale | 1 |
| setup-pristine | 0 |
| independent-check-pristine | 40 |
| row10-independent | 40 |
| **total** | **287** |

## Files
`rows.tsv`, `audit.log`, `build.log`, `sorry-audit.txt`, `axioms.tsv`, `axioms-all.txt`, `independent-check*/`, `row10-results.tsv`, `row10-tools.tsv`, `setup*.log`.

Provenance: this is an automated pass. Never write "proved" as a bare verdict; state the verdict above and list what keeps it from TRUSTED.
