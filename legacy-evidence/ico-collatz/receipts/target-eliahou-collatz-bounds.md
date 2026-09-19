# Target Repository Intake (Phase 7)

- repo: https://github.com/tangentstorm/eliahou-collatz-bounds
- cloned to: ~/ico-collatz/targets/eliahou-collatz-bounds
- commit: db804ce6305ea99a817f067869607f8b677d895a
- commit date: 2026-09-17 05:30:16 +0000
- branch: main
- commit subject: "Pre-audit fixes: full Thm 1.1 linear form, glue, norm_num powers"

## Stated environment (as pinned by the repo — NOT yet matched to our control project)

- lean-toolchain: `leanprover/lean4:v4.28.0`
- Mathlib: pinned via lakefile to `rev = "v4.28.0"` (a tagged release, not `master`)

**This differs from our control project baseline** (Lean 4.34.0, Mathlib master
commit `5ed2965`, dated 2026-09-15). Per Phase 7 rule, this drift is treated as
an experimental variable, not silently normalized to our current environment.
Building this repo will require installing Lean 4.28.0 via elan (separate
toolchain, does not replace 4.34.0) and fetching a second, older Mathlib olean
cache (~9-10GB, similar in size to the one already fetched for the control
project).

## Scope (from README, as claimed by the repo — not yet verified)

Formalizes Eliahou's Theorem 1.1 (Eliahou 1993, *The 3x+1 problem: new lower
bounds on nontrivial cycle lengths*, Discrete Mathematics 118) in full linear
form:

> For an exact (injective) compressed Collatz cycle Ω with min Ω > 2^40,
> Card Ω = 301994·a + 17087915·b + 85137581·c for some a,b,c ≥ 0 with b > 0
> and a·c = 0.

Claimed corollary: every such cycle has length ≥ 17,087,915. README explicitly
states "no `native_decide` remains in the Lean sources" (self-reported — to be
verified independently in Phase 10, not taken at face value).

## Threat classification (Phase 14, preliminary — this is a BOUNDED RESULT about
cycle length lower bounds, not a GLOBAL RESULT and not the Collatz conjecture
itself. Do not let this become "Collatz was proved.")

## Files present

- `Main.lean`, `Results.lean` (paper-facing statements, per README)
- `Collatz/` (main formalization, incl. `Collatz/LinearForm.lean`, `Collatz/README.md`)
- `scripts/`
- `eliahou-collatz.pdf` (638KB — likely the source paper or a write-up; not yet read)
- `ARISTOTLE_SUMMARY.md` (not yet read — name suggests possible prior AI-assisted
  summary; treat as a claim to verify, not evidence)
- `lake-manifest.json`, `lakefile.toml`, `lean-toolchain`

## Not yet done (Phase 8+)

- Reproduce build exactly as supplied (needs Lean 4.28.0 toolchain + its own
  Mathlib cache — a second large download; see disk discipline note in
  PROJECT_STATUS.md before proceeding)
- Source inventory, sorry audit, axiom audit (scripts are ready in `scripts/`)
- Read `ARISTOTLE_SUMMARY.md` and `eliahou-collatz.pdf` for the semantic
  correspondence audit (Phase 12)
