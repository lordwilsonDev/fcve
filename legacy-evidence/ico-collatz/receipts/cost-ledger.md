# Cost Ledger

Tracks time/resource cost of each phase so scaling to a second target repo has a
real basis for estimation, not a guess.

| Date       | Phase | Item                                   | Cost |
|------------|-------|-----------------------------------------|------|
| 2026-09-18 | 0-2   | Project scaffold + control project build | ~15 min wall clock; 3.9GB partial + 5.2GB resumed Mathlib cache download |
| 2026-09-18 | —     | Disk emergency (Try Omarchy VM removal) | ~10 min; freed 19GB, unrelated to Lean work |
| 2026-09-18 | 6     | Mini proof lab (20 theorems)             | 1 build iteration failed (2 real errors), 1 fix cycle, ~110s per full build (Mathlib import dominates) |
| 2026-09-18 | 9-11,32 | Audit scripts (sorry/axiom/inventory/hash) | 1 bug found + fixed (set -e + pipefail aborting on zero-match grep) before scripts were trusted |

## Notes

- A full `lake build` against Mathlib from this project's `.lake` cache takes
  ~90-115s per invocation even when only one new file changed, because the
  build graph still walks all 8924 jobs. Budget for this when estimating
  iteration speed on the actual target repo.
- Disk headroom should be checked (`df -h /`) before any phase that fetches a
  new Mathlib revision or a second checker toolchain (see correction ledger).
