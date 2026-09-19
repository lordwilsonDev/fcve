# Gate 4: Lean Formalization Comparison

Comparing `NORMALIZED-001` (independently derived from the source PDF) against
`Collatz/LinearForm.lean`'s `eliahou_theorem_1_1` (and `Results.lean`'s
`results_eliahou_theorem_1_1` wrapper), in the target repo
`tangentstorm/eliahou-collatz-bounds` @ `db804ce6`.

## Side-by-side

| Human mathematics (normalized) | Lean |
|---|---|
| $\Omega$ nontrivial cycle, $\min\Omega > 2^{40}$ | `(cyc : CollatzCycle L) (hinj : Function.Injective cyc.seq) (hmin : 2^40 < cyc.minElem)` |
| $\mathrm{Card}\,\Omega$ | `(Finset.univ.image cyc.seq).card` |
| $\exists\, a,b,c\ge 0,\ b>0,\ ac=0:\ \mathrm{Card}\,\Omega = 301994a+17087915b+85137581c$ | `∃ a b cCoeff : ℕ, 0 < b ∧ a * cCoeff = 0 ∧ (Finset.univ.image cyc.seq).card = 301994*a + 17087915*b + 85137581*cCoeff` |

## Proof-structure comparison (not just the final statement)

| Paper (p.55-56) | Lean (`Collatz/LinearForm.lean`) |
|---|---|
| Lemma 3.1 (Farey intermediate fraction) | `farey_intermediate_coeffs` — same hypotheses (Farey pair, strict betweenness), same conclusion form |
| $p_{16}/q_{16} < \log_2 3 < p_{15}/q_{15} < \log_2(3+2^{-40}) < p_{13}/q_{13}$ | `conv16_lt_logb_three`, `farey_15_16`, `farey_13_15`, `logb_three_plus_lt_conv13` — same chain of inequalities, same specific convergents |
| Three-way case split on where $k/l$ falls | `rcases lt_trichotomy ((L:ℚ)/k₁) (17087915/10781274)` — same trichotomy, same pivot fraction ($p_{15}/q_{15}$) |
| Case (i): $k/l\in(p_{16}/q_{16},p_{15}/q_{15}) \Rightarrow k=p_{15}b+p_{16}c$ | `hlt` branch: `farey_intermediate_coeffs` with `farey_15_16`, returns `⟨0, bCoeff, cCoeff, ...⟩` |
| Case (ii): $k/l=p_{15}/q_{15} \Rightarrow k=p_{15}b$ | `heq` branch: divisibility argument via coprimality, returns `⟨0, b, 0, ...⟩` |
| Case (iii): $k/l\in(p_{15}/q_{15},p_{13}/q_{13}) \Rightarrow k=p_{13}a+p_{15}b$ | `hgt` branch: `farey_intermediate_coeffs` with `farey_13_15`, returns `⟨bF, aF, 0, ...⟩` |

**The Lean proof is not merely a different route to the same numbers — it implements the same three-case Farey-pair argument, pivoting on the same convergent, using the same Farey identity, in the same order.**

## Detected semantic differences (per Gate 4's required checklist)

| Check | Finding |
|---|---|
| Stronger/weaker statement | Neither — see injectivity note below |
| Altered domain | No |
| Missing hypothesis | No — `hinj` is *additional*, not missing; see below |
| Extra hypothesis | `hinj : Function.Injective cyc.seq` — see justification |
| Changed quantifier | No |
| Changed equality | No |
| Changed function | No |
| Changed coercion | `ℝ`/`ℚ` intermediate steps (`rat_of_real_div_lt`) not present in the paper's argument, which works in $\mathbb{R}$ throughout — a formalization convenience (rational arithmetic is decidable/computable where real arithmetic isn't), not a semantic change: the paper's own convergents are already rational by construction |
| Finite/infinite mismatch | No |
| Exact/approximate mismatch | No |

## The one real structural difference: injectivity

The paper's own definition (p.45) makes "cycle of length $k$" mean $k=\mathrm{Card}\,\Omega$ **by definition** — a paper "cycle" is inherently what Lean calls an `ExactCollatzCycle` (injective indexing). Lean's base `CollatzCycle L` structure is strictly more general (it permits repeated elements within one period), so `eliahou_theorem_1_1` adds `hinj` as an explicit hypothesis to recover exactly the paper's object of study.

This is **not** a weakening (the theorem isn't proved for a smaller class of paper-cycles) and **not** a strengthening (it isn't proved for objects the paper didn't consider) — the injectivity hypothesis exactly closes the gap between Lean's more general indexed structure and the paper's implicit assumption. Confirmed independently in this session's prior audit (`evidence/semantic-audit-eliahou.md`) via the proved bridge lemma `ExactCollatzCycle.card_eq_length`.

## Semantic status

**MATCH.**
