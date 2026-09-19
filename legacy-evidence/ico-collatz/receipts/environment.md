# Environment Baseline Receipt

- project_id: ico-collatz
- researcher: Wilson (wilsonlord241@gmail.com)
- date: 2026-09-18
- OS: Darwin 25.6.0 (Darwin Kernel Version 25.6.0, arm64, Apple Silicon)
- git: 2.53.0
- elan: 4.2.4
- lean: 4.34.0 (arm64-apple-darwin24.6.0, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)
- VS Code CLI: /opt/homebrew/bin/code (present)
- VS Code Lean 4 extension: leanprover.lean4 (installed)
- lake: 5.0.0-src+293d5d0 (Lean version 4.34.0)

## Baseline Gate
LEAN_INSTALL = GREEN
LAKE = GREEN
VSCODE_EXTENSION = GREEN

## Control Project (Phase 2)

- path: ~/ico-collatz/ico_collatz_verification
- created via: `lake new ico_collatz_verification math`
- lean-toolchain: leanprover/lean4:v4.34.0
- mathlib commit: 5ed2965256430c3649e86755f9576b54eca72435 (2026-09-15 00:29:41 +0000)
- mathlib cache: 5174/5176 files from cache.mathlib.org (2 files not cached upstream — harmless, rebuilt locally)
- `lake build`: SUCCESS (4 jobs, own project scaffold)
- `EnvironmentCheck.lean` (trivial arithmetic + Mathlib `simp` theorem): SUCCESS, 8924/8924 jobs, kernel-checked against full Mathlib
- disk headroom after full Mathlib build: 15GB free (44% used) — safe margin, no further large downloads needed for this project

## Baseline Gate (Phase 1 complete)
TRIVIAL_PROOF = GREEN
MATHLIB_BUILD = GREEN

