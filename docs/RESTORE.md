# Restoring from zero (delete everything, redownload, get back to the current state)

**Checked 2026-09-19 before a planned wipe.** Everything committed to the two private repos comes back with `git clone`. This page lists what a clone does *not* carry and how each piece is restored or rebuilt.
Nothing below deletes anything; the destructive step (wiping) is yours.

## 0. Before you wipe: is everything pushed?

```bash
git -C ~/fcve fetch && git -C ~/fcve status -sb && git -C ~/fcve log origin/main..HEAD --oneline   # expect: no unpushed commits, clean tree
git -C ~/ico-collatz/ico_collatz_verification status -sb                                            # same for the VCE-002 project
```
`~/ico-collatz` itself is **not a git repository**. Its small evidence files are archived in `legacy-evidence/` (copies, verified by `MANIFEST.sha256`). Its large contents (exports, the `targets/` clone and builds) are regenerable, not archived.

## 1. What a clone brings back, and what it does not

| Piece | Comes back with `git clone`? | How to restore |
|---|---|---|
| FCVE engine, scripts, tests, skills, docs, manifests, all runs and deliverables, records | yes (`lordwilsonDev/fcve`) | `git clone` |
| Legacy evidence formerly only in `~/ico-collatz` | yes (`legacy-evidence/`) | `cd legacy-evidence && shasum -a 256 -c MANIFEST.sha256` |
| VCE-002 Lean project | yes (`lordwilsonDev/ico-collatz-verification`, commit `409c4c3`) | `git clone` (source only; `.lake` is rebuilt by Lake) |
| Third-party source PDFs (`verification*/source/original.pdf`) | **no** (gitignored: copyright) | `scripts/restore.sh` — finds the file by its recorded sha256 in the pinned upstream repo, refuses any other file |
| Checker tool builds (`.fcve-work/`, ~180 MB) | no | `scripts/setup.sh` (needs ~3.5 GiB free to build from scratch) or `--reuse-from DIR` |
| User-level skill copies (`~/.claude`, `~/.hermes`, `~/.agents`) | no | `scripts/install-agent-skills.sh` |
| Lean toolchains (2.5 GiB each) and Mathlib caches (~10 GiB) | no | `scripts/setup.sh --tag vX --install-toolchain`; `lake exe cache get` in a target |
| The eliahou audit target (`tangentstorm/eliahou-collatz-bounds` @ `db804ce`) | no (someone else's repo) | `git clone`, `git checkout db804ce6305ea99a817f067869607f8b677d895a` |
| Hermes / FreeBuff settings, credentials, trust decisions, Vault notes, memory | no | not in the repo; **`hermes skills trust ~/fcve` is your decision and is never done for you** |
| Upstream PRs (`leanprover/lean4export#52`, `ammkrn/nanoda_lib#36`) | n/a | live on GitHub (your forks) |

## 2. The procedure

```bash
git clone https://github.com/lordwilsonDev/fcve.git && cd fcve
scripts/restore.sh                    # source PDFs, verified by sha256 (clones the pinned upstream repo into .fcve-work/restore-sources/)
scripts/doctor.sh                     # expect FAIL for tools not built yet — that is the correct answer on a fresh clone
scripts/setup.sh                      # tools (add --reuse-from DIR if you kept a copy; --install-toolchain only when you mean to spend 2.5 GiB)
scripts/install-agent-skills.sh       # skills for Claude Code, Hermes, FreeBuff
scripts/doctor.sh && scripts/smoke-test.sh     # READY, then SMOKE TEST PASSED (with the PDFs restored, no engine test is skipped)
scripts/agent-check.sh                # expect 0 FAIL; FreeBuff live = UNRESOLVED until you run the canary check (docs/LOADING-CHECK.md)
```
`scripts/clean-room.sh` rehearses exactly this on a throwaway clone and writes a record under `docs/clean-room-records/`.

## 3. Honest limits

- The legacy-evidence copies were made on 2026-09-19; they cannot prove the originals were unmodified before then.
- A from-scratch tool build has not been rehearsed on this machine (needs ~3.5 GiB free; it had ~2.6). Tool builds were *adopted* in the clean-room runs.
- The wipe itself, and anything outside these repos (the 7.7 GB `targets/`, 1.1 GB `experiments/`), is not covered by any backup.
