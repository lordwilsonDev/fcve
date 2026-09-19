# Clean-room reproducibility

**Question this answers:** does a fresh clone of this repository, read by a Claude session that has never seen FCVE, contain enough to
reconstruct the working environment? "It works on Wilson's Mac" is not the standard. A clean reconstruction that works, repeatedly, is.

**What it detects:** undocumented dependencies, hidden caches, machine-specific state, stale files, missing skills or scripts, implicit human
intervention, setup-order bugs, path assumptions, environment assumptions.

The same reconstruction is also what a new operator does. `scripts/setup.sh`, `scripts/doctor.sh` and `scripts/smoke-test.sh` are its steps.

## Procedure (one run)

Do this on the validated machine (see `manifests/environment.json`). Do **not** delete anything you have not decided to delete: steps 3-4 are for
the *throwaway* clone and the *generated* state inside it, never for a target project or evidence.

```text
 1. Record the repository commit under test:                git -C <repo> rev-parse HEAD
 2. Record the host specification:                          scripts/doctor.sh (hardware + OS + tools sections), plus `df -h /`
 3. Delete the previous throwaway clone (only that directory).
 4. Delete generated state you are testing from zero: the clone's .fcve-work/ (checker builds, setup record). Leave user-owned target repos alone.
    NOTE: rebuilding the checker tools from scratch needs ~0.5-1 GB free above the 1.5 GiB floor; on a tighter disk `setup.sh` REFUSES
    (BLOCKED) instead of trying. Adopting existing verified builds (--reuse-from) is a documented, recorded shortcut, not the same test.
 5. Fresh clone:                                            git clone <remote> <fresh-dir>
 6. Start a fresh Claude session in <fresh-dir> (no prior conversation, no memory of FCVE).
 7. Claude reads README.md and CLAUDE.md, in that order.
 8. Claude discovers the required skill from the repository: skills/verifying-lean-proofs/SKILL.md
    (also via the project-level symlink .claude/skills/verifying-lean-proofs).
 9. scripts/setup.sh            (add --install-toolchain only with the operator's OK; add --reuse-from only if you mean to test that path)
10. scripts/doctor.sh           expect exit 0 (READY), or a clearly explained WARN set
11. scripts/smoke-test.sh       expect "SMOKE TEST PASSED"
12. A representative audit:     scripts/audit.sh tests/fixtures/mini-lean-ok --module Mini --decl mini_add --decl mini_comm --fast-literals no
                                (and, when time/disk allow, a real target such as the VCE-002 project)
13. Record the results (template below): commit, host, per-step exit status, timings, every WARN/FAIL/UNRESOLVED, anything the operator had to do by hand.
14. Destroy the environment (the throwaway clone).
15. Repeat from step 1.
```

**Target:** Run 1 → PASS, Run 2 → PASS, Run 3 → PASS, on the same commit. Then failure injection (below).
A run that needed any human intervention *not written in the repository* is a **FAIL** of the repository, even if the machine ended up working:
fix the documentation or scripts, and start the count again.

## Failure injection (Test D)

Break one thing on purpose and confirm the *correct* failure state is reported. These are automated in `tests/test_bootstrap.py`
(`python3 tests/test_bootstrap.py`); do at least one by hand in a clean room too:

| Break | Expected |
|---|---|
| remove `cargo` from `PATH` | doctor `FAIL`, setup exit 2 (missing prerequisite), nothing installed |
| ask for a Lean tag not in the manifest | setup exit 64, no silent substitution |
| set `FCVE_FAKE_FREE_KB=1000` | doctor `FAIL` (storage); setup exit 4 `BLOCKED: insufficient disk`; audit exit 3 `UNRESOLVED` — never `REJECTED` |
| change a patch byte | doctor `FAIL` (sha256 differs); a patch that no longer applies is detected |
| point the manifest at a different `lean4export` commit | setup exit 5, "refusing to substitute a different version" |
| audit a fixture containing `sorry` | rows 4 and 6 `FAIL`, verdict `REJECTED` |
| a fake checker that rejects / errors / stalls | `FAIL` / `TOOL_ERROR` / `BLOCKED` respectively — three different states |
| tamper with a ledger line | `fcve.py verify` fails |
| delete `skills/verifying-lean-proofs/SKILL.md` | doctor `FAIL` |

## Evidence integrity (Test E)

Confirm: audit output is reproducible (same inputs → same rows, same verdict); hashes are recorded (`facts.tsv`, `row10-tools.tsv`, `setup-record.json`);
patched tools are disclosed in the output; unresolved gates stay unresolved; `TRUSTED` cannot appear (`audit.sh` has no code path for it; the
test suite asserts it).

## Record template

Copy to `docs/clean-room-records/YYYY-MM-DD-runN.md`.

```markdown
# Clean-room run N — <date>
- Repository commit: <sha>            - Clone location: <path>          - Fresh Claude session: yes/no (how started)
- Host: <model, chip, RAM, macOS, free disk at start>
- Tools rebuilt from scratch: yes / no (adopted via --reuse-from: <what>)
| Step | Command | Exit | Seconds | Notes (every WARN / FAIL / UNRESOLVED; every manual action) |
|---|---|---|---|---|
| setup | scripts/setup.sh ... | | | |
| doctor | scripts/doctor.sh | | | |
| smoke | scripts/smoke-test.sh | | | |
| audit | scripts/audit.sh ... | | | |
- Manual interventions not written in the repo: none / <list>   (any entry here is a repository bug)
- Result: PASS / FAIL          - Discrepancies to fix: <list>
```

## Measured record

Records live in [`clean-room-records/`](clean-room-records/). Status as of 2026-09-19 (commit `5c825cf`):

- **Scripted runs (`scripts/clean-room.sh`): 3 consecutive PASS** — fresh clone from the remote → doctor → setup → doctor → smoke test → audit, no manual steps.
  The first three runs (earlier commit) **FAILED** and found a real bug: tests that depended on a gitignored third-party PDF (BUG-008). Fixed; the next three runs passed.
- **Not yet done, so this procedure is NOT fully validated:**
  1. The checker tools were **adopted** (`--reuse-from`, verified by commit and patch equality), not built from scratch — the disk here (~2 GiB free) cannot hold a from-scratch build above the 1.5 GiB floor, and setup correctly refuses. Free ≥ ~3.5 GiB and run without `--reuse-from` to test it.
     (Separately, a from-scratch tool build was measured earlier at 23 s upstream / 39 s patched.)
  2. No **fresh Claude session** has yet read the repository and reconstructed the environment from `README.md` / `CLAUDE.md` alone (procedure steps 6-8). That needs a person to open Claude in a fresh clone.
  3. Failure injection (Test D) is automated in `tests/test_bootstrap.py`; it has not been repeated by hand inside a clean room.
