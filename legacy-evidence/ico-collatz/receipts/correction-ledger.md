# Correction Ledger

Every defect in the project's own process gets an entry here — not defects in the
target proof (those go in `evidence/`), but defects in how we ran the audit.

## Template

```
### <date> — <short title>

Correction:
<what was initially assumed or done>

Observed:
<what was actually found>

Cause:
<why the initial assumption/action was wrong>

Correction:
<what changed as a result>

Result:
<what this means going forward>
```

## Entries

### 2026-09-18 — Our own status file carried a stale self-description

Correction:
While updating the Phase 17/18 rows of `PROJECT_STATUS.md` as the handoff
instructed, left the neighbouring "Open decisions" bullet untouched, on the
assumption that lines nobody asked about were still accurate.

Observed:
That bullet still read "Target repository ... Not yet cloned — proceeding to
Phase 7 now", while the phase table forty lines above it recorded Phase 7 as
DONE. The file was describing a state it had already superseded.

Cause:
Edited only the lines the handoff named (the two phase rows and the frontmatter).
Nothing in this project's process checks a status file against its own phase
table, so a stale line survives until someone happens to edit near it.

Correction:
Rewrote the bullet with the target's actual commit
(`db804ce6305ea99a817f067869607f8b677d895a`) and dated the correction inline,
rather than quietly replacing the text.

Result:
This is the same defect class this audit already caught in the target repo —
`ARISTOTLE_SUMMARY.md` (see `evidence/semantic-audit-eliahou.md`), a document
describing a superseded state, believed because it sounds current. Applying that
doctrine to our own artefacts means `PROJECT_STATUS.md` is itself a claim to be
checked against its own tables, not a file to append to. Any phase that edits it
should re-read the whole file against the phase table.

### 2026-09-18 — Phase 18: blamed memory/disk pressure for an exporter stall it did not cause

Correction:
Treated the aborted Phase 18 export as a resource problem — free the RAM, retry,
and the run should complete — and told the user that freeing ~6 GB of memory was
"very likely what makes the export survive".

Observed:
Freed 5.4 GB of wired memory (7,735 MB → 2,349 MB wired; 163 MB → 5,154 MB
unused; the hog was Ollama's `llama-server`) and re-ran the identical command.
The export behaved exactly as before: 71,147,520 bytes / 1,336,962 lines after
~100 s, then **zero further bytes across 8 min 34 s of accumulated CPU** (RSS
collapsed 9.2 GB → 64 MB, free disk steady at ~5.6 GB, swap flat at 6.8 GB
used). The declaration that was asked for was never reached:
`grep -c results_eliahou_theorem_1_1` on the partial output returned 0.

Cause:
`df -h /` showed swap growth during the original run, and that was taken as the
cause rather than as a co-symptom of it. The swap growth was real but
incidental — the exporter was already making no progress. `sample` on the
stalled process shows 100% CPU inside `dumpConstant` → `dumpDeps` →
`dumpExprAux` (`Export.lean`), i.e. ordinary work, not a deadlock and not GC.
The likely mechanism is that memoization is keyed on structurally-compared
`Expr` values (`getIdx`'s `HashMap Expr Nat`, `Export.lean:82`) while `dumpExpr`
discards the `noMDataExprs` cache on every call (`Export.lean:229`), giving cost
that grows super-linearly in term size. That mechanism is a hypothesis; the
measured behaviour — no output at 100% CPU — is the established part.

Correction:
Stopped treating RAM as the remedy. Freeing the memory was still right on its own
merits (it removed a real disk-exhaustion risk), but "close other applications
and retry" must not be repeated as a fix, because it is not one.

Result:
Phase 18's blocker is a property of the reference exporter on this target's
large proof terms, not of the machine. The earlier entry's option (a) — export a
lighter declaration instead of the full closure — turned out to be the correct
direction, but for the right reason rather than the stated one: it is not "avoid
`Real.logb`/analysis", since `results_eliahou_sandwich` is a `Real.logb` theorem
and exported in 120 s. It is closure *size and term shape* that decides whether
the exporter finishes.

### 2026-09-18 — Phase 18: the disk-floor guard silently stopped guarding

Correction:
Added a free-disk abort guard (kill the export below 1.5 GB free) and treated
"the guard is running" as sufficient protection for a long unattended export.

Observed:
In the retry, the monitor wrote ticks normally through t=521 s, then stopped
writing them while the export kept running for another ~5 minutes. `sample` on
the monitor's bash process showed it still alive inside its `while` loop
(`execute_while_or_until`) — neither exited nor crashed. Nothing surfaced that
the guard had gone quiet.

Cause:
Not established. The loop body used several command substitutions (`df`,
`sysctl`, `pgrep -f`, `stat` inside `$(...)`) and a `pgrep -f` pattern that also
matched the wrapper process; one of those is a likely culprit, but the failure
mode was never pinned down and this entry does not pretend otherwise.

Correction:
Rewrote the runner (`scripts/phase18-independent-check.sh`) so each export is
driven by one monitor that records a tick every 20 s including an explicit
`flat_ticks` counter, and so every export ends by writing an END line and a
`.done` file carrying an exit reason. During the run, tick advancement was
checked on every poll rather than assuming the guard was armed.

Result:
A guard that can stop reporting without stopping the work it guards is not a
guard. Long-running steps in this project must be checked for a *live*
heartbeat, not merely for having one installed. The rewritten runner then
performed correctly: it aborted `results_rational_approx_bound` at `flat_ticks`
15 with `reason=stalled-no-output`, rc=143.

### 2026-09-18 — Phase 18: background export reaped when the launching command returned

Correction:
Launched the long export with `nohup ... &` inside a subshell and assumed it
would outlive the shell that started it.

Observed:
The export and its monitor both vanished within ~2 minutes of the launching
command returning. The monitor log ended after its first tick and no END line was
ever written; the export died at 3.66 GB RSS, mid-load.

Cause:
Long-lived children started from an agent-invoked shell are cleaned up when that
invocation finishes. `nohup` detaches from SIGHUP, not from the process group
being reaped.

Correction:
Relaunched with `subprocess.Popen(..., start_new_session=True,
stdin=DEVNULL)` so the job owns a new session, then verified it survived two
further inspections before trusting it.

Result:
Any export or build expected to outlive a single agent turn in this environment
must be started in its own session. A single tick in a log is not evidence that
the job outlived the call that started it — an ended run must write an END line,
and its absence is itself a signal.

### 2026-09-18 — Phase 18: named the wrong application for the memory hog

Correction:
Described the 6.2 GB process holding the machine's memory as LM Studio's
`llama-server`, and told the user "LM Studio can respawn it later".

Observed:
`ps` shows the process is
`/Applications/Ollama.app/Contents/Resources/llama-server` — Ollama, not LM
Studio. The user's approval to kill it was given partly on that description.

Cause:
Read the process *name* (`llama-server`, shipped by both applications) and
inferred the host product, instead of reading the executable path, which was one
command away.

Correction:
None needed downstream — the process was the intended one either way — but the
record is corrected here.

Result:
When asking the user to approve touching a process they own, name the executable
path rather than an inferred product name.

### 2026-09-18 — Phase 18 independent-checker export aborted under memory/disk pressure

Correction:
Assumed monitoring free disk space alone was sufficient safety margin for
running `lean4export` on the full closure of `results_eliahou_theorem_1_1`
(which pulls in `Real.logb` and a substantial slice of Mathlib's analysis
library).

Observed:
~17 minutes in, the export's own output file was flat at 68MB (not growing),
but free disk kept dropping (4.9GB → 3.8GB) with no growth in any project file.
Cause: system-wide swap usage had climbed to 7GB/8GB (macOS swap files live on
the same APFS volume), driven by combined memory pressure from the export
process's large in-memory environment plus ordinary desktop apps (Chrome,
Claude helpers) already using most of the 16GB of RAM (~380MB free at the
time).

Cause:
Disk headroom checks (`df -h /`) only catch growth in files we control. They
miss OS-level swap growth from memory pressure, which can consume disk just as
fast and isn't visible by watching a specific output file.

Correction:
Killed the export process and removed its partial (68MB) output rather than
let it run indefinitely against an unknown ceiling. Did not attempt to free
RAM by closing the user's other applications (out of scope — those are the
user's active work, not this project's to manage).

Result:
Phase 18 needs either (a) a lighter target theorem with a smaller Mathlib
dependency closure (e.g. one of the purely-ℕ/ℚ Farey-pair lemmas, avoiding
`Real.logb`/analysis machinery) instead of the full headline theorem, or (b)
more free RAM before attempting the full closure again. Documented as an open
gap, not silently retried. See `adversarial/attack-h-kernel-vulnerability.md`
— Phase 18 remains the only way to close T6 for this target, so this gap is
tracked as OPEN, not abandoned.

### 2026-09-18 — Nearly cited a stale self-description as current evidence

Correction:
Almost treated `ARISTOTLE_SUMMARY.md` (the target repo's own prior AI-run
summary) as informative about the current state of the proof.

Observed:
It claims 1 remaining `sorry` (in `eliahou_precise`) and use of `native_decide`
for a key numeric fact. Our own fresh Phase 9-10 audit of the current commit
found 0 sorry, 0 native_decide, 0 admit.

Cause:
`git log --oneline -- ARISTOTLE_SUMMARY.md` shows the file was added in the
very first commit and never updated. Two commits since then changed the actual
math: `fdb0b2e` deleted the old sorry-containing theorem rather than completing
it, and `db804ce` (current HEAD) added a fresh, complete, injectivity-aware
replacement in a new file. The summary describes a since-superseded state.

Correction:
Verified current claims only against a fresh audit of the current commit
(scripts/sorry-audit.sh, scripts/axiom-audit.sh) and `git log`/`git show` on
the specific theorem's history, not against any repo-authored summary or
README, however recent-sounding.

Result:
Documented in `evidence/semantic-audit-eliahou.md` as a standing methodology
note: a target repo's own description of itself (README, AI-run summary,
commit message) is a claim to check, never evidence on its own — check it
against `git log` for staleness and a fresh script run for current truth,
every time, regardless of which direction the staleness would bias the result.

### 2026-09-18 — source-inventory.sh counted vendored Mathlib source, not the target repo

Correction:
Assumed `grep -rhoE '...' --include='*.lean' "$TARGET"` scoped to the target
repo's own files.

Observed:
First run against `targets/eliahou-collatz-bounds` reported 161,075 theorems,
25,505 definitions, 204 axioms, 95 unsafe declarations — for a 7-file repo.
Absurd on its face.

Cause:
`$TARGET` is a directory, and `grep -r` recurses into `.lake/packages/mathlib`,
which is Mathlib's full vendored source tree (thousands of files). The `-h`
flag (used to suppress filenames for clean counting) also silently defeated the
`grep -v '\.lake/'` filter used elsewhere, since with `-h` there's no filename
in the output line left to match against.

Correction:
Replaced the `grep | grep -v` pattern with `grep --exclude-dir=.lake
--exclude-dir=.git`, which filters at the traversal level regardless of `-h`.
Re-ran against both the control project (unchanged: 0 theorems, sane) and the
target repo (61 theorems/lemmas, 7 defs, 0 axioms, 0 unsafe — matches the
repo's own scale).

Result:
Any repo-scoped grep/audit script in this project must use `--exclude-dir`,
not a post-hoc `grep -v`, whenever `-h`/`-o` is also in play. Numbers this
implausible (100x+ the visible file count) are now a trigger to distrust the
tool before distrusting the target.

### 2026-09-18 — Root volume exhaustion during Mathlib cache fetch

Correction:
Assumed there was enough free disk space to run `lake new ... math` (which
auto-fetches the full Mathlib build cache, ~9-10GB) without checking first.

Observed:
The fetch failed at 41% (3,722/8,908 files) with `No space left on device`. The
root volume was at 100% capacity, 109MB free — low enough that Claude Code's own
scratchpad also failed to write, and the `Bash` tool stopped working entirely
(every call failed with `ENOSPC` opening its own output-capture file).

Cause:
An unrelated 19GB "Try Omarchy" QEMU VM (app + VM disk images) had been running
in the background and had grown the Data volume to 100% capacity, unrelated to
this project.

Correction:
1. Switched to `mcp__terminal__run_in_terminal` (writes to the user's terminal
   panel, not the harness's disk-bound output file) to diagnose disk usage when
   `Bash` itself couldn't run.
2. Surfaced the Omarchy VM to the user with exact sizes and an explicit
   confirmation question before deleting anything (destructive, irreversible).
3. Quit the running VM/helper processes, unloaded its LaunchAgent, then removed
   the app, VM data, plist, logs, and sync scripts — recovering 15GB+ free.
4. Resumed `lake exe cache get` from where it left off (already-downloaded files
   were reused) rather than restarting from zero.

Result:
Going forward, any phase that fetches a new large dependency (a different
Mathlib revision for the target repo, a second checker toolchain) checks
`df -h /` first and treats <5GB free as a stop condition, not a "try anyway."
This is now documented in `PROJECT_STATUS.md` under "Disk discipline note."
