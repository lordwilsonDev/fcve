# Test fixtures

Tiny Lean projects (no Mathlib, Lean v4.28.0) used by `scripts/smoke-test.sh` and `tests/test_bootstrap.py`.

- `mini-lean-ok/` — two axiom-free theorems. A correct audit gives rows 4-6 PASS and, with the independent checker, row 10 PASS.
- `mini-lean-bad/` — contains `sorry`. A correct audit must report row 4 FAIL and row 6 FAIL (`sorryAx`), and the verdict REJECTED.
  This fixture exists to prove FCVE can fail: its central threat is a false green.

They live inside this repository, so audit row 1 pins the *FCVE* commit, not a separate one.
