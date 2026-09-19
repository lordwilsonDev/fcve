# CLAUDE.md — instructions for a Claude session working in this repository

You have never seen FCVE before. **This repository is the source of truth. Your memory is not.** Do not rely on a previous session,
on anything Wilson said before, or on undocumented machine state. If something you need is not written down here, say so — do not guess.

> **The model can propose. The experiment decides.**
> **Building is breaking:** build → test → inspect → break deliberately → repair → regression test. Capture the lesson, not just the fix.

## Do these, in this order, before any FCVE work

1. Read `README.md`.
2. Read this file completely.
3. Identify the environment: run `scripts/doctor.sh` (it prints hardware, OS, tools, repo state, patches, storage). The **validated**
   environment is a Mac mini (Mac16,10, Apple M4, 16 GB, macOS 26.6.2, arm64) — see `manifests/environment.json`. Anything else is *unvalidated*:
   say so; do not claim it works.
4. Load the verification skill: read `skills/verifying-lean-proofs/SKILL.md` (a project-level symlink at `.claude/skills/verifying-lean-proofs`
   also makes a Claude Code session in this repo discover it). Then its `PROOF-TRUST-MATRIX.md` and `LESSONS.md`.
5. Read the doctor output. Every `FAIL` must be resolved; every `UNRESOLVED` must be resolved or reported. `WARN` = works-but-differs.
6. Determine what is missing. Run `scripts/setup.sh` only where the doctor says something is missing. It is safe to repeat.
   Useful flags: `--reuse-from DIR` (adopt already-built, verified tools), `--tag vX.Y.Z`, `--install-toolchain` (2.5 GB; ask first), `--dry-run`.
7. Run `scripts/smoke-test.sh`.
8. Verify: the output must say `SMOKE TEST PASSED`. If it says anything else, stop and diagnose (see "When something fails").
9. Read `HANDOFF.md` for the current state and open items.
10. Only then do FCVE work.

## What you must NOT do

- Assume a dependency exists, that a cached build is valid, or that a previous session (or its notes) is trustworthy.
- Silently install anything not documented in `manifests/environment.json`. Report a missing prerequisite instead.
- Silently modify a verification **target** repository, or evidence, or a delivered run. Ledgers are append-only; supersede, don't edit; archive, don't delete.
- **Convert `TOOL_ERROR` / `BLOCKED` / `UNRESOLVED` into `FAIL`.** Not-PASS is not FAIL.
- **Convert absence of evidence into `PASS`.** Unknown is never green.
- Declare **TRUSTED** while any human or web gate is unresolved. `scripts/audit.sh` cannot produce TRUSTED and you must not write it.
- Treat your own semantic judgment as independent human review. You may *draft* a semantic comparison; a named human confirms it.
- Claim a patched tool is equivalent to its upstream without the documented validation (below).
- Hide, soften, or "work around" an environmental failure (disk, missing tool, stale cache). Report it as what it is.
- Say "the second checker confirmed everything." Say exactly what it checked (see "Independence").
- Delete user-owned material. Do not delete anything unless the user has asked for that specific thing.

## What you may decide, and what you may not certify

You **may**: inspect, run, reason, propose, write and modify tooling and documentation, diagnose failures, draft semantic comparisons,
run audits, report results.
You **may not**: set a bridge verdict, a governance decision (PROMOTE / REPAIR / RESEARCH / REJECT / STOP), a limitations record, or a
semantic-correspondence verdict as if it were settled. Those are Wilson's (or another named human's). Draft them, label them PROPOSED, ask for a
one-word confirmation with concrete options, and record the confirmation as theirs. Your reasoning does not become independent evidence because you produced it.

## Verdict vocabulary (never collapse these)

| State | Meaning | Example |
|---|---|---|
| `PASS` | the check ran and holds | checker exit 0, "Checked N declarations with no errors", target printed |
| `FAIL` | the check ran and **rejected** the proof/evidence | checker panics on a `def_eq`; `sorryAx` in the axioms |
| `BLOCKED` | the check could not complete; **no verdict on the proof** | disk guard aborted the export; export stalled |
| `TOOL_ERROR` | the tool never ran properly; **no verdict on the proof** | checker could not open its config |
| `UNRESOLVED` | not evaluated / not evaluable; **never a pass** | web unavailable for the kernel-bug review |
| `NEEDS HUMAN` | requires a named human | semantic correspondence (row 7) |
| `PARTIAL` | passes on a stated weaker basis | reused `.lake` cache; patched tools |
| `PROVISIONAL` | no active failure, but rows remain unresolved — **the ceiling of `audit.sh`** | |
| `TRUSTED` | all ten matrix rows pass **including the human and web rows** | never produced automatically |

## Independence has layers

A second checker (nanoda) is independent of *Lean's kernel execution*. It is **not** an independent semantic review, an independent human
review, an independent interpretation, or independent governance. It re-checks the exported proof term against the same statement. Whether the
statement means what the paper says (row 7) is a human question.

## Patched tools (lean4export, nanoda_lib)

Two small patches (`tool-patches/`, hashes in the manifest) make huge decimal number literals tractable. Always distinguish `UPSTREAM` from `PATCHED`.
Any verdict that used them must disclose: the upstream commit, the patch, the patch sha256, the build result, the equivalence-test result, the
negative-control result, export validation, and the relevant output hashes — `scripts/setup.sh` records the first five in
`.fcve-work/setup-record.json`; `audit.sh` records the rest in its output. A patched tool must never masquerade as upstream. Upstream PRs:
`leanprover/lean4export#52`, `ammkrn/nanoda_lib#36` (open, not merged).

## Storage safety

Independent checking can use a lot of disk. Before expensive work: calculate free space, compare it with the floor (measured: hard floor 1.5 GiB
free, 3 GiB recommended, ~2.5 GiB per Lean toolchain, ~10 GiB for a new Mathlib target, 50–200 MB per export — measured on the validated Mac mini,
not universal). Fail *before* starting. Insufficient disk is `BLOCKED`/`UNRESOLVED`, never a theorem failure. Record an export's hash before
deleting it. Never delete a user's target.

## Commands

```bash
scripts/doctor.sh                 # inspect environment; PASS/WARN/FAIL/UNRESOLVED; exit 0 = ready
scripts/setup.sh [--reuse-from D] # build/verify checker tools; idempotent; records .fcve-work/setup-record.json
scripts/smoke-test.sh             # ~1 min end-to-end proof that the machinery works and can fail correctly
scripts/audit.sh <target> --module M --decl D [--decl D2 ...] [--fast-literals auto|yes|no] [--out DIR] [--work DIR] [--rebuild] [--skip-independent]
scripts/run-tests.sh [--full]     # syntax checks, then real tests (fast tier; --full adds the slow end-to-end tier)
scripts/agent-check.sh            # read-only: is this repo usable by Hermes / FreeBuff / Claude Code here? (their own scanners, hooks, discovery)
scripts/install-agent-skills.sh   # install/update the user-level skill copies for claude / hermes / freebuff (idempotent; never overwrites a different skill)
python3 scripts/fcve.py -h        # the FCVE evidence engine (ledger, report, receipt, ...)
```

Read the audit's `AUDIT.md`: it leads with the verdict, what keeps it below TRUSTED, environment, patched tools, and per-row status. Never bury an unresolved gate.

## When something fails

- Read the failing line; it names the fix. Do not retry blindly and do not "adjust" until green.
- A **stall** is a symptom: `sample <pid>`, run `skills/verifying-lean-proofs/scripts/export-literal-scan.py <file.export>`, then decide (`SKILL.md`, "Triage: stalls").
  A stall whose cause was a *guess* has already cost this project a day once (BUG-002).
- Setup order: doctor → setup → doctor → smoke. If a step contradicts this file, trust the experiment and report the discrepancy.
- Known bugs and their regression tests: `skills/verifying-lean-proofs/BUGS.md`, `tests/test_bootstrap.py`. Lessons: `skills/verifying-lean-proofs/LESSONS.md`.

## Where things are

| | |
|---|---|
| `manifests/environment.json` | the validated environment, required tools, patch hashes, measured requirements (machine-readable) |
| `scripts/` | `doctor.sh`, `setup.sh`, `smoke-test.sh`, `audit.sh`, `run-tests.sh`, `fcve.py` + gate modules |
| `skills/verifying-lean-proofs/` | the skill: `SKILL.md`, trust matrix, `audit.sh`, `independent-check.sh`, lessons, bugs, examples, patches |
| `docs/CLEAN_ROOM_REPRODUCIBILITY.md` | how to prove a fresh clone reconstructs the environment (and the record of doing so) |
| `AGENTS.md` | short agent-neutral entry point (Hermes loads ONLY this, not CLAUDE.md; FreeBuff loads both) |
| `docs/AGENT-INTEGRATIONS.md` | how Hermes and FreeBuff load instructions/skills here, what is verified and what is not |
| `docs/blueprints/` | the plan this bootstrap layer implements |
| `tests/` | engine tests, bootstrap/regression/failure-injection tests, tiny Lean fixtures |
| `deliverables/`, `verification*/` | issued packages and runs. Delivered runs are never edited |
| `HANDOFF.md` | current state, decisions made, open items |

Not a product: no SaaS, auth, cloud, or UI. The goal is operational reproducibility of this research/verification infrastructure on the supported Mac mini.
