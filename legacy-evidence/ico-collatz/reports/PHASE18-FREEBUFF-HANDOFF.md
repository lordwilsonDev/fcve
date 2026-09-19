# Handoff: Phase 18 Independent Checker (ICO-Collatz project)

## What this project is

`~/ico-collatz` — an audit of the Lean 4 formalization
`~/ico-collatz/targets/eliahou-collatz-bounds` (Eliahou's 1993 Collatz
cycle-length bound, cloned from
https://github.com/tangentstorm/eliahou-collatz-bounds, commit
`db804ce6305ea99a817f067869607f8b677d895a`). Read `~/ico-collatz/README.md`
and `~/ico-collatz/PROJECT_STATUS.md` first — they explain the full
methodology and current phase gates. Everything below is Phase 18 only; do
not touch other phases' files.

## The one job

Get an **independent checker** (a second, differently-implemented type
checker, not the Lean kernel itself) to verify
`results_eliahou_theorem_1_1` in
`~/ico-collatz/targets/eliahou-collatz-bounds/Results.lean`, and report
PASS/FAIL with the checker's own output as evidence.

## Why this specific theorem, why now

Phases 7-15 of this audit are all clean (source inventory, sorry audit, axiom
audit, semantic correspondence against the actual 1993 paper — see
`~/ico-collatz/evidence/` and `~/ico-collatz/reports/`). But Phase 17's Attack
H (`~/ico-collatz/adversarial/attack-h-kernel-vulnerability.md`) found
something real: the target repo is pinned to Lean `v4.28.0`, which **predates**
the Lean 4.32.2 release that fixed a kernel soundness bug (nested inductive
types with phantom type parameters could make the kernel accept a proof of
`False`). Exploiting it needs a deliberately malicious metaprogram — nothing
suggests this repo is malicious — but "the same kernel that has a known bug
class accepted it" is a weaker trust claim than "an independently implemented
checker also accepted it." Phase 18 exists specifically to upgrade that claim.
Without it, this audit's honest governance state is RESEARCH, not PROMOTE.

## What was already tried and why it failed (don't repeat this)

Candidate: `nanoda_lib` (https://github.com/ammkrn/nanoda_lib), which checks
Lean's `.export` format (via
https://github.com/leanprover/lean4export — cloned at the matching `v4.28.0`
tag into `~/ico-collatz/targets/lean4export`, already built successfully,
binary at `~/ico-collatz/targets/lean4export/.lake/build/bin/lean4export`).

Command tried (from inside the target repo, so `lake env` resolves its
compiled `.olean`s):
```bash
cd ~/ico-collatz/targets/eliahou-collatz-bounds
lake env ../lean4export/.lake/build/bin/lean4export Results -- results_eliahou_theorem_1_1 > out.export
```

This ran for 17 minutes at 100% CPU. Its own output file was small and
harmless (68MB, stopped growing early). But **system swap climbed to 7GB/8GB**
during the run (macOS swap files live on the main disk), and free disk quietly
dropped from ~4.9GB to ~3.8GB with nothing in the project growing — this
machine had a full-disk incident earlier today (unrelated 19GB VM, since
removed) and I killed this process rather than risk repeating that with a
harder-to-diagnose cause. **The memory pressure looks like it comes from
loading the whole Mathlib-based environment, not from the size of the
requested theorem's closure** — so picking a "smaller" theorem to export
probably won't fix it. More free RAM (close other heavy apps first) is the
more likely fix. Current machine state at handoff time: **3.9GB disk free,
~1.2GB swap free (7GB/8GB swap in use), ~130MB RAM free** — do not start
another heavy process without checking `df -h /` and
`sysctl vm.swapusage` first, and stop if free disk drops below ~1.5GB.

## What "done" looks like

One of:

1. `nanoda_lib` successfully checks the export and reports which axioms it
   used / that the proof term type-checks — write the result to
   `~/ico-collatz/evidence/independent-checker-eliahou.md` (this exact
   filename, referenced from `PROJECT_STATUS.md`'s Phase 18 row) including:
   the exact commands run, the checker's version/commit, and its full output.
2. A different, working independent-checker approach entirely (e.g.
   `lean4lean` — https://github.com/digama0/lean4lean, an independent Lean 4
   kernel written in Lean 4 itself — may be much easier to set up since it's
   an ordinary Lake project rather than requiring the export+Rust+JSON-config
   pipeline). If you take this path, note in the writeup that it doesn't fully
   escape T7 (independent-checker vulnerability) in the same way a
   differently-implemented-language checker would, since it's still a Lean
   host — say so explicitly, don't oversell it.
3. If genuinely blocked again (resource or otherwise), update
   `~/ico-collatz/receipts/correction-ledger.md` with a new dated entry
   (follow the existing entries' format exactly) explaining what was tried and
   why it didn't work — do not silently give up or fake a result.

## Ground rules (carried over from this project's own incidents today)

- Check `df -h /` before anything that fetches a new toolchain/Mathlib
  revision or runs a heavy Lean process. Stop below ~1.5GB free.
- Never trust a repo's own self-description (README, AI-run summary, commit
  message) as evidence — this project already caught
  `ARISTOTLE_SUMMARY.md` being stale (see
  `~/ico-collatz/evidence/semantic-audit-eliahou.md`). Verify claims with a
  fresh command, every time.
- Log every defect in your own process (not just the target's) to
  `~/ico-collatz/receipts/correction-ledger.md`, following its existing entry
  format (Correction / Observed / Cause / Correction / Result).
- Do not modify anything under `~/ico-collatz/targets/eliahou-collatz-bounds`
  — it's a read-only audit subject. Scratch files (like the old
  `AxiomProbe.lean` probe) get deleted after use; `git status --short` should
  come back clean when you're done touching it.
- Once Phase 18 has a real result, update the Phase 17/18 rows in
  `~/ico-collatz/PROJECT_STATUS.md` and the `status:` frontmatter field.
