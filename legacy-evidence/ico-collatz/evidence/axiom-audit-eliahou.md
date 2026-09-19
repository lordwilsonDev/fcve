# Axiom Audit (Phase 11): eliahou-collatz-bounds

- date: 2026-09-18
- commit: db804ce6305ea99a817f067869607f8b677d895a
- method: scratch probe file `AxiomProbe.lean` (`import Results; #print axioms <name>`),
  run via `lake env lean AxiomProbe.lean`, then deleted (not committed to the target
  repo — `git status --short` confirmed clean afterward)

## Theorems checked

The three paper-facing "headline" theorems from `Results.lean`:

| Theorem | Axioms | Classification |
|---|---|---|
| `results_eliahou_theorem_1_1` (full linear form, the paper's Theorem 1.1) | `propext`, `Classical.choice`, `Quot.sound` | MATHLIB_STANDARD (all three) |
| `results_eliahou_bound_card` | `propext`, `Classical.choice`, `Quot.sound` | MATHLIB_STANDARD |
| `results_eliahou_bound` | `propext`, `Classical.choice`, `Quot.sound` | MATHLIB_STANDARD |

## Interpretation

`propext`, `Classical.choice`, and `Quot.sound` are the three axioms nearly all of
Mathlib depends on (propositional extensionality, choice, and quotient soundness).
Their presence is expected and is not evidence of anything unusual — a Mathlib-based
proof with *zero* axioms would be the surprising result. Critically, **no
PROJECT_AXIOM or EXTERNAL_AXIOM appears** — the headline theorem does not smuggle in
an undisclosed assumption beyond ordinary classical mathematics as Mathlib defines it.

Combined with Phase 9/10 (0 `sorry`, 0 `admit`, 0 `native_decide`, 0 project-declared
`axiom` statements anywhere in the 7 source files), this specific gate (T3: hidden
axiom, T4: `sorry`) is clean for this repository as of this commit.

## What this does NOT establish

This says nothing about T2 (formalization mismatch) or T9 (semantic ambiguity) —
whether `results_eliahou_theorem_1_1`'s Lean statement actually captures Eliahou's
1993 paper claim is a separate audit (Phase 12, not yet done) that requires reading
`eliahou-collatz.pdf` and `Collatz/README.md` against the Lean statement line by line.
An axiom-clean, sorry-free proof of the *wrong statement* is still a failed audit.
