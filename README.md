# FCVE — Formal Claim Verification Engine

FCVE turns a mathematical claim into an **auditable evidence package** instead of a one-word "verified", and includes a one-command audit
for Lean 4 / Mathlib proofs. This repository is meant to be **self-bootstrapping**: a fresh clone contains the instructions, skill, scripts,
manifest and tests needed to reconstruct the working environment on the supported Mac mini without relying on anyone's memory.

> **Start here:** if you are Claude, read [`CLAUDE.md`](CLAUDE.md) next. If you are a person: [Installation](#7-installation) → [Environment Doctor](#9-environment-doctor) → [Smoke Test](#10-smoke-test).

## 1. What FCVE Is

- An evidence engine (`scripts/fcve.py` + one module per gate) that walks a claim through a fixed chain — source → claims → normalization → Lean
  formalization → build → axiom audit → semantic re-audit → computational tests → independent check → evidence graph → report → governance decision —
  and records what each gate actually showed in an **append-only, hash-chained ledger**. Spec: [`SPECIFICATION.md`](SPECIFICATION.md).
- A Lean-proof audit skill ([`skills/verifying-lean-proofs/`](skills/verifying-lean-proofs/SKILL.md)) with a ten-row trust matrix and a one-command audit (`scripts/audit.sh`).
- Two theorems run through it by hand so far (see [Research / Engineering Notes](#22-research--engineering-notes)).

## 2. What FCVE Is Not

- **Not a universal verifier.** It has been run on two real theorems and some fixtures, by one person.
- Not a substitute for human judgment: it checks completeness and consistency; claim extraction, whether a Lean statement means what a paper says,
  bridge verdicts, limitations and the final decision are **human**. A model may draft them; it must not certify its own draft.
- Not a product: no SaaS, auth, billing, cloud, multi-tenant or web UI. The aim is operational reproducibility of a research/verification tool.
- Not proof of a theorem's truth: a passed audit says what was checked, and only that.

## 3. Architecture

```
claim ──► [gates 0-4: source, claims, assumptions, normalization, Lean comparison]  (mostly human judgment, recorded)
      ──► [gate 5-6: Lean build, axiom audit]                                        (Lean kernel)
      ──► [gate 7: semantic re-audit, bridge verdict]                                (human)
      ──► [gates 8,10: computational tests]                                          (diagnostic only, never proof)
      ──► [gate 9: independent check]      lean4export → nanoda_lib                  (a second, differently-implemented checker)
      ──► [gate 11-12: evidence graph, report]  ──► [gate 13: governance decision]   (a named human)
                        all of it: append-only hash-chained ledger + receipt
```

The audit skill implements a related ten-row **Proof Trust Matrix** (source pinned, toolchain pinned, rebuild, sorry/admit, native_decide,
axioms, semantic correspondence, stale self-description, kernel-bug exposure, independent check). `scripts/audit.sh` automates rows 1–6, 8 and 10.

## 4. Verification Philosophy

- **The model can propose. The experiment decides.** Reasoning is not evidence.
- **Never collapse the states** (below). *Not PASS is not FAIL.* Unknown is never green.
- Recorded failure is not a passed gate. Corrections supersede; they never overwrite. Archive, don't delete.
- **Building is breaking:** build → test → inspect → break deliberately → repair → regression test. Every bug found became a lesson
  ([`skills/verifying-lean-proofs/LESSONS.md`](skills/verifying-lean-proofs/LESSONS.md)) and, where practical, a test.
- The central threat is **false confidence** — a false green — so the test suite mostly checks that things fail correctly.

## 5. Supported Environment

**Validated** on exactly this environment ([`manifests/environment.json`](manifests/environment.json)):

| | |
|---|---|
| Device | Mac mini, model `Mac16,10`, Apple M4 (10 cores), 16 GB RAM, ~228 GB disk |
| OS | macOS 26.6.2, arm64 |
| Tools | git 2.53.0, bash 5.3.9, Python 3.12.9, elan 4.2.4, Lake 5.0.0, rustc/cargo 1.92.0 (rustup), Tectonic 0.17.0 |
| Lean toolchains | v4.28.0 (with Mathlib 8f9d9cff…), v4.34.0 (with Mathlib 5ed29652…) |
| Checkers | `lean4export` @ d065b00 (v4.28.0) / 076e8e5 (v4.34.0); `nanoda_lib` @ 4c544ed |

Anything else — other Macs, other macOS versions, Linux — is **unvalidated**. The doctor reports a difference as `WARN`; it does not claim compatibility.

## 6. Prerequisites

You install these; setup will not install undocumented tools for you. Required: `git`, `bash`, `python3`, `patch`, `shasum`, **elan** (Lean), **rustup/cargo** (to build `nanoda_lib`).
Optional: `tectonic` (only to compile FCVE reports), `rsync`, `sample` (macOS; stack samples of a stalled export).
Disk: measured on the validated Mac mini — hard floor **1.5 GiB free**, **3 GiB recommended**, ~2.5 GiB per Lean toolchain, ~10 GiB for a new Mathlib target,
0.05–0.2 GiB per export (approximate, not universal). Time: a clean tool setup took 23 s (upstream) / 39 s (patched) here.

## 7. Installation

```bash
git clone https://github.com/lordwilsonDev/fcve.git && cd fcve     # private repo
scripts/doctor.sh                       # what is missing? (a fresh clone will show FAIL for tools not built yet)
scripts/setup.sh                        # builds/verifies the checker tools under .fcve-work/ ; safe to repeat
#   scripts/setup.sh --reuse-from ~/ico-collatz/targets      # adopt already-built, VERIFIED tools instead of rebuilding (saves ~0.5 GB)
#   scripts/setup.sh --tag v4.34.0 --install-toolchain       # also fetch a Lean toolchain (2.5 GB; only when you mean to)
scripts/doctor.sh && scripts/smoke-test.sh
```

`setup.sh` never touches a verification target, never substitutes a different tool version, checks disk **before** expensive work (exit 4 =
`BLOCKED: insufficient disk`, not a proof failure), and records what it did in `.fcve-work/setup-record.json`.

## 8. Claude Setup

Open Claude Code in the repository. `CLAUDE.md` is the entry point; it tells Claude to read this README, run the doctor, load the skill, run setup only where
needed, run the smoke test, and only then work. The skill is discoverable at `skills/verifying-lean-proofs/SKILL.md` and, via a project-level symlink,
at `.claude/skills/verifying-lean-proofs`. **Hermes and FreeBuff** are supported too: `AGENTS.md` is their entry point, the skill is discoverable at `.agents/skills/` and via user-level copies (`scripts/install-agent-skills.sh`), and `scripts/agent-check.sh` verifies it with each agent's own scanners — see [`docs/AGENT-INTEGRATIONS.md`](docs/AGENT-INTEGRATIONS.md) (including what is *not* verified, and the one security decision left to you: trusting the repo in Hermes). A previous Claude session is not needed and not trusted: [`docs/CLEAN_ROOM_REPRODUCIBILITY.md`](docs/CLEAN_ROOM_REPRODUCIBILITY.md)
is the procedure for proving that.

## 9. Environment Doctor

`scripts/doctor.sh` inspects hardware, OS, tools + versions, Lean toolchains, repository state (commit, branch, dirty), expected files and skill files, the tool
patches (present, hash = manifest, apply cleanly to the pristine upstream, built, validated), the checker builds, and free disk versus what is needed.
Each item is `PASS`, `WARN` (works but differs from validated), `FAIL` (fix printed) or `UNRESOLVED` (could not be determined). Exit 0 = ready, 1 = a FAIL,
3 = only UNRESOLVED. It changes nothing and never installs anything.

## 10. Smoke Test

`scripts/smoke-test.sh` (about a minute here) runs, for real: the doctor, syntax checks, the engine's fast test suites, integrity checks on the delivered packages, and
an end-to-end audit of a tiny Mathlib-free Lean fixture **including the independent checker** — plus two negative checks: a fixture with `sorry` must be REJECTED, and a
simulated full disk must be BLOCKED/UNRESOLVED (not REJECTED). It prints `SMOKE TEST PASSED` only if every required condition holds — and that statement is about the
environment, not about any theorem.

## 11. Running an Audit

```bash
scripts/audit.sh <target-dir> --module <Module> --decl <theorem> [--decl <theorem2> ...] \
    [--fast-literals auto|yes|no] [--out <dir>] [--work <dir>] [--rebuild] [--skip-independent]
```

It runs rows 1–6, 8, 10 and writes `AUDIT.md`: verdict, what keeps it below TRUSTED, environment, tool versions, patched tools, per-row status, timings. It never edits the
target. Long audits should run detached. Measured on the validated Mac mini (single runs, not benchmarks): 1 declaration on Lean 4.34.0 ≈ 5 min; 2 declarations on Lean 4.28.0 with a
stalled-then-patched independent check ≈ 26 min; row 6 is dominated by importing Mathlib (2–3 min).

## 12. Understanding Audit Results

| State | Meaning |
|---|---|
| `PASS` | the check ran and holds |
| `FAIL` | the check ran and **rejected** the proof or evidence |
| `BLOCKED` | the check could not complete (stall, disk guard): **no verdict on the proof** |
| `TOOL_ERROR` | the tool never ran properly: **no verdict on the proof** |
| `UNRESOLVED` / `NEEDS HUMAN` / `NOT RUN` | not established; **never a pass** |
| `PARTIAL` | passes on a stated weaker basis (reused build cache; patched tools) |
| `PROVISIONAL` | no active failure, rows unresolved — **the ceiling of `audit.sh`** |
| `TRUSTED` | all ten rows pass **including human and web rows** — never produced automatically |

Rules: checker rejects → `FAIL`; disk guard prevents the check → `BLOCKED`/`UNRESOLVED`; checker crashes → `TOOL_ERROR`; web unavailable → `UNRESOLVED`; human review not done → `NEEDS HUMAN`.

## 13. Evidence Model

Each run keeps `evidence/event-ledger.jsonl`: one JSON event per gate, each hashed with its parent (a tamper-evident chain), plus a receipt generated from the ledger after the
decision, an evidence graph, a LaTeX report, and a correction ledger. Delivered runs are never edited; a correction is a new run beside them, with superseded events and
reports kept. See [`HANDOFF.md`](HANDOFF.md). The chain is tamper-**evident**, not tamper-proof (local, unsigned).

## 14. TRUSTED vs PROVISIONAL

`scripts/audit.sh` can reach **PROVISIONAL** at most. `TRUSTED` needs row 7 (a named human confirms the Lean statement means what the source claims) and row 9 (kernel-vulnerability
review of the pinned Lean version, which needs live web access). Neither is automated, so no code path emits `TRUSTED`, and the test suite asserts that. This rule is repeated in
`CLAUDE.md`, `SKILL.md`, `manifests/environment.json` and in every `AUDIT.md`.

## 15. Independent Checker

Row 10 / Gate 9: `lean4export` serializes the proof's dependency closure and `nanoda_lib` (a separate Rust implementation, not Lean's kernel) re-checks it. PASS requires a complete export,
exit 0, "Checked N declarations with no errors" with N > 0, the target declaration printed, and the checker's axiom set equal to the Lean-side audit. **Independence has layers:**
a second checker is independent of Lean's kernel execution. It is not an independent semantic review, an independent human review, or independent governance — never write "the second
checker confirmed everything".

## 16. Patched Tool Policy

Two small patches ([`tool-patches/`](tool-patches/), sha256 in the manifest) make huge decimal literals tractable (up to 25.6 M digits in one proof; upstream is quadratic in both printing and
parsing). They are **optional and always disclosed**: every verdict that used them says `PATCHED`, names the upstream commit, patch hash, build result, equivalence-test result,
negative-control result, export validation and output hashes. `setup.sh` builds them beside the pristine tools and runs the equivalence tests; `audit.sh --fast-literals auto` tries upstream first
and falls back. Upstream PRs (open, not merged): `leanprover/lean4export#52`, `ammkrn/nanoda_lib#36`. The patched builds are machine-local; the diffs are what a third party needs.

## 17. Reproducibility

The repository is the source of truth. [`manifests/environment.json`](manifests/environment.json) records the validated environment; [`docs/CLEAN_ROOM_REPRODUCIBILITY.md`](docs/CLEAN_ROOM_REPRODUCIBILITY.md) is the
procedure (fresh clone → fresh Claude session → setup → doctor → smoke → audit → destroy → repeat ×3, plus failure injection). Three consecutive scripted clean-room runs pass on commit `5c825cf` (after the first three found and fixed a real bug), **but** the checker tools were adopted rather than built from scratch and no fresh Claude session has yet done the reconstruction — so it is **not** fully validated; see
`docs/clean-room-records/`. Reproducibility levels in reports are ceilings supported by *recorded* evidence; nothing is re-run to earn one.

## 18. Troubleshooting

| Symptom | Meaning / fix |
|---|---|
| `doctor`: `FAIL tool cargo/elan …` | install it (setup will not); re-run the doctor |
| `doctor`/`setup`: insufficient disk (exit 4, `BLOCKED`) | not a proof failure. Free space (nothing is deleted for you) or `setup.sh --reuse-from DIR` |
| `setup`: "refusing to substitute a different version" | the checkout is not at the manifest's validated commit; don't work around it |
| `UNRESOLVED patch … no pristine checkout` | run `scripts/setup.sh` |
| an export stalls (`BLOCKED … stalled-no-output`) | sample it and run `skills/verifying-lean-proofs/scripts/export-literal-scan.py`; huge literals → `--fast-literals yes` (disclosed) |
| `TOOL_ERROR` | the tool did not run (config path, missing binary) — not a verdict on the proof |
| `smoke-test` says `NOT RUN` | setup has not been run |
| a `pkill`/stale `lean4export` process | check with `pgrep -fl lean4export` before assuming it is yours |

## 19. Repository Structure

| Path | What |
|---|---|
| `CLAUDE.md` | Claude's entry point: ordered bootstrap, hard rules, vocabulary |
| `manifests/environment.json` | machine-readable validated environment + requirements |
| `scripts/` | `setup.sh`, `doctor.sh`, `smoke-test.sh`, `audit.sh`, `run-tests.sh`, `lib/common.sh`, `fcve.py` + gate modules |
| `skills/verifying-lean-proofs/` | the skill: `SKILL.md`, trust matrix, audit scripts, lessons, bug log, examples, patches |
| `.claude/skills/` | symlink so a Claude Code session here discovers the skill |
| `tool-patches/` | the two tool patches |
| `docs/` | clean-room procedure and records, blueprints |
| `tests/` | engine tests, `test_bootstrap.py` (failure injection, regressions, ceiling), tiny Lean fixtures |
| `verification*/`, `deliverables/`, `*-records/` | runs, issued packages, reviewed/proposed records |
| `HANDOFF.md`, `SPECIFICATION.md` | current state; the specification |

## 20. Version / Release Information

No tagged release. The repository is identified by commit (`git rev-parse HEAD`; the doctor prints it and `setup-record.json` stores it). The environment manifest is schema 1, validated 2026-09-19.

## 21. Known Limitations

- Validated on one machine type; Linux and other macOS versions untested. Two theorems and fixtures so far; no scale testing; `batch-run` never run on a real Mathlib project.
- One human in the loop: "independent" means an independent *checker*, not an independent reviewer.
- The ledger is tamper-evident, not tamper-proof. Repository/commit facts for the two delivered runs were captured after the runs.
- The patched tools are unreviewed by their upstream maintainers (PRs open); the exporter patch was not built on upstream's current toolchain (v4.35.0-rc2).
- Real Lean builds need ~3 GB free; a disk below the floor blocks audits (reported as UNRESOLVED). A from-scratch rebuild of the checker tools does not fit on a nearly full disk.
- Compiled reports use `tectonic`, not the `pdflatex` the spec names. No license has been chosen.

## 22. Research / Engineering Notes

| Claim | Delivered run | Corrected revisions | Decision |
|---|---|---|---|
| **VCE-001** — Eliahou, Theorem 1.1 (a bound on the length of a nontrivial Collatz cycle; it does **not** resolve the conjecture) | [`verification/`](verification/) | [rev r](deliverables/VCE-001-rev-r/) (REPAIR), [rev s](deliverables/VCE-001-rev-s/) | **PROMOTE** (rev s) |
| **VCE-002** — every power of two reaches 1 under the Collatz map | [`verification-002/`](verification-002/) | [rev r](deliverables/VCE-002-rev-r/), [rev s](deliverables/VCE-002-rev-s/) | **PROMOTE** (rev s) |

Each issued package has an `ISSUE-NOTE.md` (what it supersedes, stated limitations) and a `MANIFEST.sha256`; read the limitations before relying on one.

**The independent-check finding.** VCE-001's headline proof was first recorded as "checker incompatible: `lean4export` stalls (memoization bug)" — a hypothesis repeated as fact. Sampling the stalled
process showed the real cause: quadratic decimal conversion of natural-number literals up to 25.6 M digits, in the exporter and then in the checker. The patches fix it; the theorem then checks
(17,464 declarations, axioms matching the Lean audit), a corrupted literal is still rejected, and earlier passes reproduce. That episode, and the other bugs found along the way, are in
[`skills/verifying-lean-proofs/LESSONS.md`](skills/verifying-lean-proofs/LESSONS.md) and [`BUGS.md`](skills/verifying-lean-proofs/BUGS.md).

Plan of record for this bootstrap layer: [`docs/blueprints/FCVE-SELF-BOOTSTRAPPING-BLUEPRINT.md`](docs/blueprints/FCVE-SELF-BOOTSTRAPPING-BLUEPRINT.md). Current state and open items: [`HANDOFF.md`](HANDOFF.md).
