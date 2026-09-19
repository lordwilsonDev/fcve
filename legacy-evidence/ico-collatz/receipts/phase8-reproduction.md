# Phase 8: Reproduce Before Modifying

- target: ~/ico-collatz/targets/eliahou-collatz-bounds
- commit: db804ce6305ea99a817f067869607f8b677d895a
- toolchain installed: leanprover/lean4:v4.28.0 (via elan, alongside 4.34.0 — no
  replacement of the control project's toolchain)
- `lake exe cache get`: 8010/8010 files downloaded and decompressed cleanly (Azure-hosted
  mathlib4 cache), ~26s decompression
- `lake build`: SUCCESS, 8033/8033 jobs, 7m38s wall clock (27.5s user / 46.2s system —
  mostly I/O and process overhead across many small Lean processes)
- No source modifications made before this build.

## Disk cost of this phase (important for future planning)

| Item | Size |
|---|---|
| `~/.cache/mathlib` (shared elan/lake olean cache, both versions) | 1.1G |
| `targets/eliahou-collatz-bounds/.lake` (v4.28.0 build) | 7.0G |
| `ico_collatz_verification/.lake` (v4.34.0/master build, control project) | 7.9G |
| **Free space after this build** | **5.0GB (71% used)** |

This is now at the 5GB stop-line documented in `PROJECT_STATUS.md` / the
correction ledger. Any further large fetch (an independent checker toolchain
like `nanoda`, a third Mathlib revision, a second target repo) should wait for
either (a) more free space, or (b) deleting one of the two `.lake` build
directories once its audit phase is done with it.

This dual-cache cost (~15GB for two Lean/Mathlib version pairs to coexist) is
itself a piece of evidence for T5/T8 (dependency contamination / build
contamination threats) — version drift between a target repo and a control
environment is not free, even before any correctness question is asked.

## Baseline Gate (Phase 8 complete)
CLEAN_REBUILD = GREEN (as-supplied, no source modification, exact pinned versions)
