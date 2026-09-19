# Gate 7: Semantic Re-Audit

A second, independent pass over Gate 4's comparison, specifically hunting for
the failure modes Gate 4 could plausibly have missed: silently flipped
inequality directions, a hypothesis used in the statement but not actually
consumed in the proof (or vice versa), and dropped nonemptiness conditions.

## Inequality direction check (high-risk spot for silent errors)

Paper (p.48, the "simplified" inequality actually used): $\log_2 3 < \dfrac{\mathrm{Card}\,\Omega}{\mathrm{Card}\,\Omega_1} \le \log_2(3+m^{-1})$ — **strict** on the left, **non-strict** on the right.

Lean (`rational_linear_form`'s hypotheses): `hlower : Real.logb 2 3 < (L:ℝ)/k₁` (strict `<`), `hupper : (L:ℝ)/k₁ ≤ Real.logb 2 (3+1/(m:ℝ))` (non-strict `≤`).

**Exact match, including strictness on each side.** This is the single easiest place to introduce an off-by-a-boundary-case error (e.g. an equality case silently included or excluded), and it's correct.

## Hypothesis-actually-used check

`hm : 2^40 < m` is not just present in the signature — it is explicitly threaded into `logb_three_plus_lt_conv13 m hm`, which is exactly the step that needs "$m$ large enough" to guarantee $\log_2(3+1/m) < p_{13}/q_{13}$. Confirmed by reading the call site, not just the type signature — a hypothesis appearing in a signature but never used in the proof body is possible in Lean (unused-variable warning aside) and would be a real defect if it happened here. It doesn't.

## Nonemptiness / division-by-zero check

The ratio $\mathrm{Card}\,\Omega/\mathrm{Card}\,\Omega_1$ requires $\mathrm{Card}\,\Omega_1 > 0$ (the paper tacitly assumes this — a cycle's ratio of total-to-odd elements is meaningless if there are no odd elements). Lean does not assume this: `cyc.numOdd_pos` is a **proved** theorem (`Collatz/Defs.lean`, via a minimal-element argument: if every element were even, the minimum element's image would be a strictly smaller cycle element, contradiction) supplied at the call site (`rational_linear_form cyc.numOdd_pos hmin ...`). This is Lean being *more* rigorous than the paper's tacit assumption, not a gap — worth stating as a positive finding, not filed as a difference requiring REPAIR.

## Decidability / classical reasoning

The axiom footprint (`AXIOMS-001`) already discloses `Classical.choice`. Nothing found in this pass suggests it's used beyond ordinary real-number order decidability (`Real.logb`, `lt_trichotomy`), consistent with any Mathlib-based real-analysis argument.

## Result

No undisclosed semantic change found. Combined with Gate 4, both the final
statement and the detailed inequality/hypothesis mechanics match the source.

**Status: no REPAIR triggered.**
