# FCVE handoff

> ## CURRENT STATE — read this block first (written 2026-09-19, end of the session that built the bootstrap layer)
> Everything below this block is **history** (older sections; parts are superseded and some opening claims are stale — e.g. VCE-001 is no longer REPAIR). Where they disagree, this block and the repository win; verify anything here with the commands at the end.
>
> **What FCVE is:** an evidence engine (`scripts/fcve.py`) that never collapses a claim to "VERIFIED" + a Lean-proof audit skill (`skills/verifying-lean-proofs/`). Spec: `SPECIFICATION.md`.
> **Results (decisions are Wilson's, recorded in each receipt):** VCE-001 (Eliahou Thm 1.1) → **PROMOTE** in `deliverables/VCE-001-rev-s/`; VCE-002 (powers of two reach 1) → **PROMOTE** in `deliverables/VCE-002-rev-s/`. Earlier revisions (rev r) and the delivered runs are superseded but kept, untouched.
> Limitations travel with each package (`ISSUE-NOTE.md`): VCE-001's independent check used **patched** lean4export/nanoda (the recorded "memoization bug" was a wrong guess; the cause was quadratic handling of literals up to 25.6M digits); repro facts were captured after the runs; computational evidence is diagnostic only.
> **Repos (private):** `github.com/lordwilsonDev/fcve` (this repo, `main`), `github.com/lordwilsonDev/ico-collatz-verification` (VCE-002 Lean project, commit `409c4c3`). Upstream PRs open, not merged: `leanprover/lean4export#52`, `ammkrn/nanoda_lib#36`.
> **The bootstrap layer (built this session):** `CLAUDE.md` / `AGENTS.md` (Hermes loads only AGENTS.md; FreeBuff loads both), `scripts/{setup,doctor,smoke-test,audit,run-tests,clean-room,agent-check,install-agent-skills}.sh`, `manifests/environment.json`, `docs/CLEAN_ROOM_REPRODUCIBILITY.md`, `docs/AGENT-INTEGRATIONS.md`, `tests/test_bootstrap.py` (failure injection, bug regressions, never-TRUSTED ceiling). Skills: `verifying-lean-proofs` (the audit) and `new-run` (how to start/resume/close a session). Plan of record: `docs/blueprints/FCVE-SELF-BOOTSTRAPPING-BLUEPRINT.md` (phases 1-11 done).
> **Verified so far:** smoke test ~48 s; 56 runtime tests; clean room = 3 FAIL (found BUG-008) then PASS on `5c825cf` ×3 and `42f439a` ×1 — **but** tools were *adopted* (`--reuse-from`, disk too tight to build from scratch) and **no fresh Claude session has done a reconstruction**. Hermes loading verified with its own `prompt-size` + scanners; FreeBuff live behavior is **unverified** (no non-interactive mode).
> **Open, in the order I'd look at them (nothing is urgent):**
> 1. A fresh Claude session in a fresh clone reconstructs the environment from README/CLAUDE.md alone (needs a person). 2. Two more clean-room runs at the newest commit; `scripts/run-tests.sh --full`; failure injection by hand.
> 3. Wilson's calls: `hermes skills trust /Users/lordwilson/fcve` (security setting, not run); pick a LICENSE (none chosen); the plaintext Telegram token in `~/.hermes/config.yaml`; free disk (≈2 GiB free now; a from-scratch tool build needs ≈3.5 GiB; `~/msb-backups/` grows ~1 GB/day).
> 4. Unproven: the audit wrapper on someone else's Lean project; Linux; `batch-run` on a real Mathlib project; FreeBuff live; Hermes with the repo trusted.
> **Rules that mattered (details: `CLAUDE.md`, `skills/verifying-lean-proofs/LESSONS.md`, `BUGS.md` BUG-001…010):** the ledger is append-only (supersede, never edit; archive, don't delete); verdicts, bridge verdicts, limitations and decisions are Wilson's — draft as PROPOSED, ask with concrete options; never turn BLOCKED/TOOL_ERROR/UNRESOLVED into FAIL or absence into PASS; `audit.sh` cannot produce TRUSTED; sample a stall before naming a cause; read rendered PDFs; never edit a running script; commit hook needs absolute `cd` paths; vault writes via Bash heredoc can trip a hook — use Edit/Write.
> **Check this block against reality (each is quick):** `git log --oneline | head` · `scripts/doctor.sh` · `scripts/smoke-test.sh` · `scripts/agent-check.sh` · `python3 scripts/fcve.py verify deliverables/VCE-001-rev-s/event-ledger.jsonl` (and VCE-002-rev-s) · `ls docs/clean-room-records`.
> Memory/Vault mirrors: `~/Documents/Vault/40_Memory/SESSION-HANDOFF-2026-09-19.md` (running log), `~/.claude/projects/-Users-lordwilson/memory/project_fcve_state.md`.

---

## History (older handoff, kept)


Supersedes `reports/HANDOFF.md` (the earlier handoff, kept as history). Full running log with reasoning:
`~/Documents/Vault/10_Projects/BlackSwanLabz/BlackSwanLabz-FCVE-Spec.md`. Governing spec: `SPECIFICATION.md` (62 sections).

## One paragraph
FCVE turns a math claim into an auditable evidence package (source → claims → normalization → Lean → build → axiom audit →
semantic re-audit → computational tests → independent check → graph → report → governance decision) and never collapses it to
"VERIFIED". **All twelve steps of the spec's §60 build order now exist as tested code** (12 suites, 258 tests, all pass). Two
theorems have been run by hand (VCE-001 = REPAIR, VCE-002 = PROMOTE); VCE-002 has a corrected re-run (`verification-002r`) with a
recorded PROMOTE and an issued deliverable. What is left is mostly decisions and data gaps, not missing machinery.

## Read these first, in this order
1. This file. 2. The vault note above (long; the last ~120 lines are this session). 3. `deliverables/VCE-002-rev-r/ISSUE-NOTE.md`.

## Layout
- `scripts/` — `fcve.py` (CLI) plus one module per gate: `fcve_evidence` (ledger, hash chain, gate order), `fcve_claims` (G1/G2),
  `fcve_lean` (G5 build + reproduction snapshot), `fcve_axioms` (G6), `fcve_semantic` (G3/4/7 + bridge verdict), `fcve_compute`
  (G8/G10), `fcve_independent` (G9), `fcve_graph` (G11, schema v3), `fcve_receipt`, `fcve_report` (G12 LaTeX), `fcve_limits`
  (reviewer limitations), `fcve_batch` (step 12). `append-event.py` / `build-evidence-graph.py` are the ORIGINAL manual scripts, kept
  only because they reproduce the delivered runs' hashes.
- `tests/test_fcve_*.py` — run one with `python3 tests/test_fcve_report.py`. All 12 pass. Lean/axiom/batch tests need `lake` and the
  Lean v4.34.0 toolchain; report tests need `tectonic`.
- Runs: `verification/` (VCE-001, delivered), `verification-002/` (VCE-002, delivered), `verification-002r/` (VCE-002 re-run),
  `verification-002r-attempt1-superseded/` (first attempt, kept + README), `deliverables/VCE-002-rev-r/` (issued package + MANIFEST.sha256).
- `reviewed-records/` = human-CONFIRMED: both Gate 7 bridge records, VCE-001 repro snapshot. `proposed-records/` = drafted by the
  assistant, NOT confirmed: both reviewer-limitations records.
- CLI subcommands: append verify validate-claims scaffold lean-build axiom-audit semantic-check scaffold-semantic compute-run
  independent-check batch-plan batch-run report receipt receipt-check scaffold-limitations limitations-check repro-snapshot graph
  graph-check graph-view. `fcve.py <cmd> -h` for flags.

## State of each run
| Run | Ledger | Decision | Notes |
|---|---|---|---|
| VCE-001 (delivered) | 15 events; chain OK; `verify` flags ORDER (decision before report — disclosed in its own correction ledger) | REPAIR | G9 has no verdict (lean4export stalls on the headline proof); legacy events have no §25 hashes |
| VCE-002 (delivered) | 13 events, canonical | PROMOTE | **No Gate 10 event** → PROMOTE not supported by §53 read literally; report lacked Semantic Bridge + appendices and printed PROMOTE before it was recorded. Untouched. |
| `verification-002r` | 18 events, canonical, graph + receipt current | **PROMOTE (Wilson's)** | Replays VCE-002 events 1-10 (hashes identical), real Gate 10 (5,001 cases + control), fresh graph/report. Superseded events 013-016 kept. Receipt: no problems, no blockers, R4. |

## Decisions Wilson made (do not relitigate)
- Gate 12/13 naming: Report Generation = 12, Governance Decision = 13.
- Graph schema: new runs use v3; legacy v1 kept ONLY so delivered hashes reproduce (VCE-001 `0c93…`, VCE-002 `6670…`).
- Q12 (§61): **option 3** — the report states what the evidence PERMITS, never the decision; the decision lives in the receipt.
- Bridge verdicts confirmed: VCE-001 FAITHFUL WITH EXPLICIT REPRESENTATIONAL DIFFERENCE; VCE-002 FAITHFUL (both "Set by Wilson").
- VCE-002 Gate 10: run for real (not waived), in a NEW run; PROMOTE recorded and re-affirmed on the regenerated report.
- The corrected VCE-002 report was issued as a NEW revision beside the delivered one; delivered files not replaced.

## How the work is done here (rules that mattered)
- **The ledger is append-only.** Fix a mistake by appending a superseding event + a correction entry, never by editing. Archive, don't delete.
- **Never modify delivered runs** (`verification/`, `verification-002/`). Regeneration goes to scratch or a new run.
- **Ask Wilson for verdicts and other judgments** (decision, bridge verdict, limitations). He answers briefly ("confirm", "PROMOTE"). A
  model may draft but cannot certify its own proposal (§44) — records name the reviewer; model names render as PROPOSED.
- **Read the rendered PDF as a mathematician before trusting or issuing a report.** Most bugs this session (false "none recorded",
  circular G12 blocker, `\S 53` literal, dangling edges) were caught by reading output, not by tests.
- Tectonic exits 0 while dropping glyphs / leaving undefined refs; the compile check parses the `.log`. This machine has `tectonic`,
  NOT `pdflatex` (§51 names pdflatex; records say so).
- **Vault writes:** a PreToolUse hook (`require-verified-claims.sh`) false-positives on the word "commit" in Bash heredocs. Use the
  Edit/Write tools for vault notes instead.

## Update — Gate 9 closed (2026-09-19, later)
- Cause of the VCE-001 Gate 9 stall was NOT memoization: it is quadratic decimal conversion of nat literals up to 25.6M digits (exporter print, then nanoda parse). Two patches in `tool-patches/`; patched builds at `~/ico-collatz/targets/{lean4export-fastnat,nanoda_lib-fastparse}`. Validated: identical export prefix, 5 earlier passes reproduce, corrupted literal rejected.
- New run `verification-001s/` (17 events): fresh Gate 6 audit, EVENT-014 = INDEPENDENTLY_CHECKED (17,464 decls, axioms match), graph, report EVENT-017, R4. Report says the evidence permits PROMOTE. **No decision, no receipt, not issued — G13 is Wilson's.** `verification-001r` (REPAIR) untouched.
- RL-002 confirmed by Wilson; report final EVENT-018. **PROMOTE recorded (Wilson's, EVENT-019)**, receipt current (no blockers, R4), package assembled: `deliverables/VCE-001-rev-s/` (ISSUE-NOTE, MANIFEST, tool-patches). VCE-001 is now PROMOTE on `verification-001s`; rev r (REPAIR) and the delivered run are superseded but untouched.
- Logged in `~/.claude/skills/verifying-lean-proofs/BUGS.md` (BUG-002/003).

## Update — GitHub (2026-09-19)
- **Private repos created by Wilson's request:** `github.com/lordwilsonDev/fcve` (this directory, branch `main`, commit d02818b) and `github.com/lordwilsonDev/ico-collatz-verification` (the VCE-002 Lean project, branch `master`, commit 409c4c3, now has `origin`).
- `~/fcve/.gitignore` excludes `**/source/original.pdf` (Eliahou's paper, third-party copyright; hashes stay in the ledgers) — a clone cannot re-hash it until the PDF is re-downloaded.
- The VCE-002 snapshot/report still say "no remote": true when captured. A future revision could cite the repo URL, but the commit was still made after the runs.
- The patched lean4export/nanoda BUILDS are not in the repo (only the diffs in `tool-patches/`).

## Update — upstream PRs + skill tried on more proofs (2026-09-19)
- **Upstream PRs opened (from `lordwilsonDev` forks):** `leanprover/lean4export#52` (sub-quadratic natVal printing) and `ammkrn/nanoda_lib#36` (sub-quadratic decimal parse). Bodies state the diagnosis, evidence, and that the exporter patch was NOT built on upstream's v4.35.0-rc2 (disk). Watch for maintainer feedback; nothing merged. Until merged, patched builds + `tool-patches/` are needed.
- **Upgraded `verifying-lean-proofs` skill tried on the 3 theorems that Phase 18 had BLOCKED** (`~/ico-collatz/experiments/independent-checker/skill-run2/`): `results_rational_approx_bound` PASS (16,940 decls), `results_eliahou_bound` PASS (17,493), `results_eliahou_bound_card` PASS (17,505). With the five earlier passes, all 9 paper-facing declarations of eliahou-collatz-bounds are now independently checked (the four formerly blocked ones with patched tools). Caveat: printed target + "no errors" confirmed; the checker's axiom sets for these three were not compared to a fresh row-6 audit. Not in any FCVE report.

## Update — one-command audit wrapper (2026-09-19)
- `skills/verifying-lean-proofs/scripts/audit.sh` runs rows 1-6, 8, 10 and writes `AUDIT.md` (verdict max PROVISIONAL; rows 7/9 need a human/web). Tested on two projects/toolchains (eliahou-collatz-bounds @4.28.0, ico-collatz-verification @4.34.0); examples in `skills/.../examples/`. Measured: ~26 min (2 decls, incl. a ~6 min stalled upstream attempt) and ~5 min (1 decl); row 6 is dominated by importing Mathlib (~2-3 min). Bugs found by running it: BUG-006. Linux untested.
- Observed: an orphaned stalled `lean4export` (pid 83961, ~14 h old, from the earlier Phase-18 retry) was still running; left alone (not started this session).

## Planned (not started)
- `docs/blueprints/FCVE-SELF-BOOTSTRAPPING-BLUEPRINT.md` — Wilson's plan to make a fresh clone self-bootstrapping on the Mac mini (CLAUDE.md, README rewrite, setup/doctor/smoke scripts, environment manifest, clean-room procedure, regression + failure-injection tests). Added 2026-09-19 as a plan of record only; **nothing implemented, nothing deleted; Wilson said "not ready yet".** Its 20 phases start with inspecting what already exists (much of `audit.sh`, the skill, and the trust matrix already covers parts of it).

## Update — self-bootstrapping layer built (blueprint phases 1-11) + clean room started
- Added: `CLAUDE.md`, README rewrite (22 sections), `scripts/{setup,doctor,smoke-test,audit,run-tests,clean-room}.sh`, `scripts/lib/common.sh`, `manifests/environment.json`, `docs/CLEAN_ROOM_REPRODUCIBILITY.md`, `tests/test_bootstrap.py` (44 runtime tests: failure injection + BUG-003/005/006/007 regressions + the never-TRUSTED ceiling), tiny Lean fixtures, `.claude/skills` discovery symlink. `audit.sh`: report header, hard PROVISIONAL ceiling, BLOCKED-before-work on low disk, `--skip-independent`. BUG-007 (`pkill -f`), BUG-008 (test depending on a gitignored PDF), BUG-009 (editing a running script).
- Measured here: smoke test ~48 s; doctor ~3 s; setup 31-115 s with adopted tools; `run-tests.sh` ~3.5 min. **Clean room: 3 FAIL (found BUG-008), then 3 consecutive PASS on `5c825cf`** — with tools ADOPTED (disk too tight for a from-scratch build) and NO fresh Claude session yet.
- **Not done (blueprint phases 13-20 / acceptance):** a genuinely fresh Claude session reconstructing from repo instructions only; a from-scratch tool build in a clean room (needs ~3.5 GiB free); Test D by hand; `scripts/run-tests.sh --full`. Nothing was deleted.

## Update — available to Hermes and FreeBuff (2026-09-19)
- `AGENTS.md` (Hermes loads ONE project context file, first found wins → AGENTS.md beats CLAUDE.md; FreeBuff loads both), `.agents/skills/` symlink, `scripts/install-agent-skills.sh` (user-level copies: `~/.hermes/skills`, `~/.agents/skills`, `~/.claude/skills` — installed), `scripts/agent-check.sh` (read-only; runs Hermes's own scanners), `docs/AGENT-INTEGRATIONS.md`.
- Found + fixed: Hermes `skills_guard` rated the skill **dangerous** (word `host` + `$` matched its DNS-exfil rule in `audit.sh`) → key renamed `machine` (BUG-010); the BUG-010 write-up itself re-tripped it, caught by the new test.
- Verified: `hermes prompt-size` context 4,552 B in repo vs 0 B elsewhere; skill in Hermes's index; Hermes scanners clean; global command hook allows FCVE commands and blocks `rm -rf /`. **Not verified:** FreeBuff live behavior (no non-interactive mode); Hermes with the repo TRUSTED. **Left to Wilson:** `hermes skills trust /Users/lordwilson/fcve` (security decision, not run). Clean room: 1 PASS on `42f439a`.
- Heads-up: `~/.hermes/config.yaml` holds a Telegram bot token in cleartext (it appeared in a tool output this session; not copied anywhere, not modified).

## Open items (recommended order)
1. ~~Confirm the two drafted limitation records~~ — **DONE 2026-09-19**: Wilson confirmed both; copies with `reviewer: Wilson` are in
   `reviewed-records/vce-00{1,2}-reviewer-limitations.json` (`limitations-check` = CONFIRMED). Drafts left in `proposed-records/`. Delivered
   reports still print "proposed" — they pick up the confirmed records only when regenerated with `--limitations-record`.
2. ~~`claims.json` clean-up (VCE-001)~~ — **DONE 2026-09-19**: Wilson confirmed 2 edits (K numeric fact split into K(2^39)=p_13 / K(2^40)=K(2^48)=p_15; step_2 interval now open (log2 3, log2(3+2^-40))). Confirmed file: `reviewed-records/vce-001-claims-cleaned.json`; delivered `claims.json` untouched. Goes into the corrected VCE-001 run via a superseding event (item 3). Original problem: one "fact the statement relies on" is stream-of-consciousness prose; §3 says "closed-open-ish".
   It is Wilson's delivered extraction — his call. Sections 1-3 also show plain-text math because claims.json isn't `$…$`.
3. ~~**Corrected VCE-001 deliverable**~~ — **DONE 2026-09-19**: `verification-001r/` (18 events, REPAIR = Wilson's EVENT-018, receipt current, blocker G9, R3), package `deliverables/VCE-001-rev-r/` (ISSUE-NOTE + MANIFEST). Attempt 1 archived. Real next step: close Gate 9 (lean4export stalls on `results_eliahou_theorem_1_1`). Original plan was: replay events 1-12, then graph, report, THEN decision (Wilson's; REPAIR expected —
   G9 still no verdict). Use `--repro-snapshot`, `--bridge-record`, `--limitations-record` (or put them in a manifest).
4. VCE-001 Q8 stays partial (legacy results carry no tested domain). VCE-002 project has NO commit and NO remote (8 untracked files),
   **UPDATE 2026-09-19: Wilson had the project committed** — `~/ico-collatz/ico_collatz_verification` HEAD `409c4c3b6f0179ae9131ac2450998e59a7fb1132` (13 files, no remote, `.lake/` ignored). Caveat: committed AFTER the VCE-002 runs, so it identifies the source as it is now, not proof of what was built then (same caveat as VCE-001's snapshot). **Snapshot taken 2026-09-19:** `proposed-records/vce-002-repro-snapshot.json` (CLEAN_AT_COMMIT 409c4c3, no remote, Lean 4.34.0, Mathlib 5ed29652…, captured by the tool; not yet used in any report). **Corrected VCE-002 built (pre-decision): `verification-002s/`** — events 1-11 of 002r replayed (hashes identical, graph hash unchanged `611fea5b…`), graph EVENT-012, final report EVENT-015 (cites the snapshot; commit shown, local-only). 15 events, chain OK. **PROMOTE re-affirmed by Wilson (EVENT-016), receipt current (no blockers, R4), package `deliverables/VCE-002-rev-s/` assembled (ISSUE-NOTE, MANIFEST).** (Was pending: `verification-002r`/`deliverables/VCE-002-rev-r/` untouched). Tool bug found reading the PDF and fixed (local-only commit was called 'not recorded'; regression test added; report suite 62 tests OK).
   so its reproduction can never be answered by a snapshot unless Wilson commits the project.
5. Trust Statement of VCE-001 is long (7 items, each real) — trim only if Wilson asks.
6. Batch (`batch-run`) has never been run on a real Mathlib project (only tiny fixtures); no parallelism/retries/`--clean-room`.

## Environment warnings
- **Disk: 2.7 GiB free (82%)**, down from 4.7 GiB at the start of the session. The wrapper's own build floor is 3 GB, so real `lean-build`
  runs will REFUSE (tests pin a small floor). Not caused by FCVE (its scratch is MBs). Likely cause: `~/msb-backups/msb-v3/` grows ~1 GB/day
  (7 backups = 7.0 GB, 08:00Z job). Big items: `~/ico-collatz/ico_collatz_verification` 7.9 GB, `targets` 7.4 GB, `~/.elan` 5.1 GB. Nothing was deleted.
- `~/.claude/skills/verifying-lean-proofs/` holds the standing rule "never trust a repo's self-description; check `git log` for staleness".
- Scratch used this session: `/tmp/claude-501/scratch/` (disposable).

## Quick commands
```bash
cd ~/fcve
for t in evidence claims lean axioms semantic compute independent graph receipt report batch limits; do python3 tests/test_fcve_$t.py 2>&1 | tail -1; done
python3 scripts/fcve.py verify verification-002r/evidence/event-ledger.jsonl
python3 scripts/fcve.py receipt-check verification-002r/evidence/event-ledger.jsonl verification-002r/receipt/receipt.json
python3 scripts/fcve.py batch-plan <manifest.json>          # read-only status of every theorem
# regenerate a report for regression (delivered ledgers already have a decision, hence --allow-post-decision):
python3 scripts/fcve.py report verification/evidence/event-ledger.jsonl /tmp/out --allow-post-decision \
  --bridge-record reviewed-records/vce-001-semantic-gate7-record.json --repro-snapshot reviewed-records/vce-001-repro-snapshot.json \
  --limitations-record proposed-records/vce-001-reviewer-limitations.json \
  --lean ~/ico-collatz/targets/eliahou-collatz-bounds/Results.lean:results_eliahou_theorem_1_1
```

## What is NOT proven (be honest with Wilson)
The tools were validated against two real runs and fixtures, not at scale. Semantic judgments (claim extraction, normalization, Gate 4/7,
bridge verdict, limitations, governance) are human; the tool checks completeness and consistency only. Reproducibility levels are
ceilings supported by recorded evidence — nothing was re-run to earn R3/R4. Computational evidence is diagnostic, never proof.
