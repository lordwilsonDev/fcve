# Mathematical Semantics Audit (Phase 12): eliahou-collatz-bounds

- date: 2026-09-18
- commit: db804ce6305ea99a817f067869607f8b677d895a
- sources compared: `eliahou-collatz.pdf` (Eliahou, S. (1993), *Discrete Mathematics*
  118(1-3), 45-56 — read directly, pages 1-3), `Collatz/README.md`,
  `Collatz/Defs.lean`, `Collatz/LinearForm.lean` (via `Results.lean`)

## Map definition

| | Statement |
|---|---|
| Paper (p.45) | `T(n) = n/2` if n even, `T(n) = (3n+1)/2` if n odd |
| Lean (`Defs.lean`) | `collatzComp n = if n % 2 = 0 then n / 2 else (3 * n + 1) / 2` |

**MATCH.**

## "Cycle" and the Card Ω correspondence

The paper defines a cycle of length k directly as a set Ω with `T^(k)(x) = x`
for all `x ∈ Ω`, **where `k = Card Ω` by definition** — i.e. the paper's own
notion of "cycle of length k" already presupposes k distinct elements per
period.

Lean's `CollatzCycle L` instead indexes by `Fin L → ℕ` with a step relation
(`T(seq i) = seq(i.succMod hL)`), which does *not* by itself force injectivity
— `L` could overcount if the sequence repeats within one period. The repo
handles this explicitly and correctly:

- `ExactCollatzCycle` extends `CollatzCycle` with an explicit
  `injective : Function.Injective seq` field.
- `ExactCollatzCycle.card_eq_length` / `CollatzCycle.card_eq_of_injective`
  prove `(Finset.univ.image c.seq).card = L` *given* injectivity — this is the
  precise bridge lemma that makes `L` and `Card Ω` interchangeable, and it is
  proved, not assumed.
- The headline theorem `results_eliahou_theorem_1_1` (in `Results.lean`) takes
  `hinj : Function.Injective c.seq` as an explicit hypothesis and states its
  conclusion in terms of `(Finset.univ.image c.seq).card` — the actual
  Eliahou "Card Ω" — not `L` directly.

**MATCH**, and notably a *more careful* formalization than a naive direct
restatement would be: it does not silently identify "cycle length" with
"count of distinct elements" without proof.

## Numeric coefficients

| | Statement |
|---|---|
| Paper Theorem 1.1 | `Card Ω = 301994a + 17087915b + 85137581c`, `a,b,c ≥ 0`, `b>0`, `ac=0`, given `min Ω > 2^40` |
| Lean `results_eliahou_theorem_1_1` | `∃ a b cCoeff, 0 < b ∧ a * cCoeff = 0 ∧ (Finset.univ.image c.seq).card = 301994*a + 17087915*b + 85137581*cCoeff`, given `hinj` and `hmin : 2^40 < c.minElem` |

**MATCH** — coefficients, constraint structure (`b>0`, `ac=0`), and threshold
(`2^40`) are identical.

## Nontriviality

Paper: theorem applies to *nontrivial* cycles, but the hypothesis given is
`min Ω > 2^40`, which already excludes the only trivial cycle `{1,2}` (min=1).
Lean: same — `hmin : 2^40 < c.minElem` is used directly as the hypothesis;
`CollatzCycle.isNontrivial` (`2 < c.minElem`) exists as a separate, weaker
definition but is not what does the work here. No gap.

## Verdict: MATCH

The Lean formalization's headline theorem corresponds to the paper's Theorem
1.1, including the subtle Card Ω ↔ L bridge that a careless formalization
could have gotten wrong (or silently assumed away) in either direction. This
does not itself verify the *proof* is correct beyond what Phases 9-11 already
checked (sorry-free, axiom-clean); it verifies the theorem *statement* being
proved is the right one — closing the T2 (formalization mismatch) and T9
(semantic ambiguity) threats from the threat model for this specific theorem.

## Important side-finding: `ARISTOTLE_SUMMARY.md` is stale, not evidence

`ARISTOTLE_SUMMARY.md` was added in the very first commit (`e7663e1 initial
import from aristotle`) and has never been touched since (`git log --oneline
-- ARISTOTLE_SUMMARY.md` shows exactly one commit). It claims:

> "The only remaining sorry is `eliahou_precise` ... (1 sorry remaining)"
> "3^10781274 < 2^17087915 (via `native_decide`)"

Both claims are **false for the current commit** (Phase 9-10: 0 sorry, 0
native_decide) but were presumably true for the very first import. The
intervening history shows why:

- `fdb0b2e "removed unused/unproven 'precise' reformulation"` — the old
  sorry-containing `eliahou_precise` (which stated the claim directly about
  `L`, without an injectivity hypothesis or the Card Ω bridge) was **deleted**,
  not completed.
- `db804ce` (current HEAD, "Pre-audit fixes: full Thm 1.1 linear form...")
  introduced `Collatz/LinearForm.lean` fresh, containing a different,
  complete, injectivity-aware proof (`eliahou_theorem_1_1`) — this is a
  rewrite, not a patch of the old sorry.

**Lesson applied**: do not cite a repo's own self-description
(`ARISTOTLE_SUMMARY.md`, or any README) as evidence of current state without
checking it against `git log` and a fresh audit run. This is exactly the T8/T9
failure mode this project's methodology exists to catch — in this case the
stale doc undersold the current state (made it look less complete than it is),
but the same blind trust could just as easily overlook a doc that oversells.
