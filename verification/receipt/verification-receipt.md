# Verification Receipt — VCE-001

| Field | Value |
|---|---|
| THEOREM ID | CLAIM-001 (Eliahou 1993, Theorem 1.1) |
| SOURCE HASH | `077292bebdf53a6e06d92fb475ce395ee1c8af4cc3e9f5c2e4620b2e35134689` (SHA-256, `source/original.pdf`) |
| CLAIM | For a nontrivial cycle Ω of the compressed Collatz map T with min Ω > 2^40: Card Ω = 301994a + 17087915b + 85137581c, a,b,c ≥ 0, b>0, ac=0 |
| NORMALIZED CLAIM | `normalized/normalized-claim.md` — MATCH against source |
| LEAN STATEMENT | `results_eliahou_theorem_1_1` (`Results.lean`) / `eliahou_theorem_1_1` (`Collatz/LinearForm.lean`), repo `tangentstorm/eliahou-collatz-bounds` @ `db804ce6305ea99a817f067869607f8b677d895a` |
| LEAN VERSION | `leanprover/lean4:v4.28.0` |
| MATHLIB VERSION | `v4.28.0` tag (pinned in `lakefile.toml`) |
| BUILD RESULT | PASS — 8033/8033 jobs, exit 0, no `sorry`/`admit` |
| AXIOM FOOTPRINT | `propext`, `Classical.choice`, `Quot.sound` — all MATHLIB_STANDARD. No PROJECT_AXIOM, EXTERNAL, or UNKNOWN. |
| SEMANTIC MATCH | MATCH (Gate 4) + no undisclosed change found on re-audit (Gate 7). Proof *structure* verified isomorphic to the paper's three-case Farey argument, not just the final statement. |
| INDEPENDENT CHECK | **INCOMPLETE for this specific theorem** — `lean4export` stalls on its proof closure (reproducible tool defect, root-caused, not a resource issue). 5/9 supporting paper-facing theorems (including the Real.logb-based sandwich argument) independently PASSED via `nanoda_bin` 0.4.17. |
| COMPUTATIONAL TEST | SUPPORTIVE — convergents p₁₃=301994, p₁₅=17087915, p₁₆=85137581 and both Farey identities independently recomputed in Python (mpmath, 60-digit precision), matching the paper and the Lean proof. One false-mismatch in this process was found, root-caused (float64 precision, not a real defect), and corrected — see `correction-ledger-entry.md`. |
| COUNTEREXAMPLE SEARCH | NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN — boundary inequalities (convergent ordering, strictness of Theorem 2.1's sandwich bound, `hm` actually consumed) checked; no counterexample sought against the Collatz cycle claim itself (computationally infeasible — would require an actual nontrivial cycle, which is open-problem-adjacent) |
| REPRODUCIBILITY LEVEL | **R3** — formal verification is reproducible (exact commit, exact toolchain, build commands given below). Not yet R4 (independent verification isn't reproducible for this specific theorem — it's blocked, not merely unattempted). |
| GRAPH HASH | `0c9330331753c8b8346704adba88b70867e4765f26a93c4b0bb22102031af10f` (15-event ledger, final event `7037245908c7ca08...`) |
| COST | ~12 gates, one 60-line Python script, no paid API calls beyond this session; wall-clock dominated by earlier-session Lean builds (already amortized, not re-run) |
| FINAL DECISION | **REPAIR** (see governance decision below — not PROMOTE, not REJECT) |
| LIMITATIONS | Independent check unavailable for the headline theorem specifically; adversarial search covered numeric/boundary structure, not the underlying Collatz-cycle existence question (infeasible) |

## Reproduction

```bash
git clone https://github.com/tangentstorm/eliahou-collatz-bounds.git
cd eliahou-collatz-bounds
git checkout db804ce6305ea99a817f067869607f8b677d895a
cat lean-toolchain          # leanprover/lean4:v4.28.0
lake exe cache get
lake build                  # expect: Build completed successfully (8033 jobs)
```

To check the axiom footprint of the headline theorem:
```bash
cat > AxiomProbe.lean <<'EOF'
import Results
#print axioms results_eliahou_theorem_1_1
EOF
lake env lean AxiomProbe.lean   # expect: [propext, Classical.choice, Quot.sound]
rm AxiomProbe.lean
```

To independently recompute the convergents and Farey identities:
```bash
python3 verification/computational/tests/verify_convergents.py
```
