# Did the agent actually load FCVE? (Hermes, FreeBuff, Claude Code)

**Files existing is not the same as the agent loading them.** This page gives a check per agent that does not depend on a model's self-report being right — free models are
the weak link (a Hermes one-shot on the default free model answered correctly once and "I don't have the repository's instructions" once, with identical loading).

## Quick start for someone using the free tools

```bash
git clone https://github.com/lordwilsonDev/fcve.git && cd fcve         # public repo
scripts/doctor.sh                       # environment: PASS / WARN / FAIL / UNRESOLVED
scripts/setup.sh                        # only if the doctor says tools are missing (add --reuse-from DIR to adopt existing builds)
scripts/smoke-test.sh                   # must end with: SMOKE TEST PASSED
scripts/install-agent-skills.sh         # user-level skill copies for Claude Code, Hermes, FreeBuff (idempotent)
scripts/agent-check.sh                  # is it wired for the agents installed here? (read-only)
```
Then open your agent **inside the repo directory** and say: **`new run`** (the `new-run` skill starts or resumes a session and reports state before doing anything).

## How to run a canary test so that a pass means something

A canary only proves *loading* if the agent could not have obtained it any other way. An agent with file tools can pass by reading the file (that is a **lookup**, not a load; one agent reported exactly this
on 2026-09-19: it answered correctly, then said it had grepped the repo from a different working directory). So run **both** halves, as the **first** message of a **fresh** session:

1. **Positive (start the agent in the repo root** — Hermes: `cd <repo> && hermes`; FreeBuff: `cd <repo> && freebuff` or `freebuff --cwd <repo>`). First message, verbatim:
   > *Do not use any tools and do not read any files. Answer only from the instructions you were given at startup. What is the FCVE load canary for AGENTS-MD? If it is not in your startup context, say "not in my context".*
   Expected: `harbor-lantern-7`. If it says "not in my context", the file did not load.
2. **Control (start the same agent in a different directory, e.g. `/tmp`), same message.** Expected: **"not in my context".** If it still answers, it looked the answer up (or the canary leaked from somewhere else), and the positive result proves nothing.
3. **Decoy (either place):** ask for the canary for `NO-SUCH-FILE`. Expected: "not in my context". An invented word means the model guesses; discount every answer it gives.

A pass = positive answers correctly **and** control does not. Anything else is inconclusive, not a pass. A model that answers correctly *after using a tool* has shown retrieval, not loading. Free models are weak: repeat once before concluding.

## The load canaries

Each instruction file and skill carries a unique phrase (`manifests/load-canaries.json`). Ask the agent the question **using the protocol above** (a correct answer only proves loading if no tool could have supplied it). They are not secrets.

| File | Ask | Expected |
|---|---|---|
| `AGENTS.md` | "What is the FCVE load canary for AGENTS-MD?" | `harbor-lantern-7` |
| `CLAUDE.md` | "What is the FCVE load canary for CLAUDE-MD?" | `slate-orchard-9` |
| skill `verifying-lean-proofs` | "What is the FCVE load canary for AUDIT-SKILL?" (load the skill first) | `copper-meridian-4` |
| skill `new-run` | "What is the FCVE load canary for NEW-RUN-SKILL?" (load the skill first) | `willow-compass-2` |

## Per agent

**Hermes** — fully checkable by script, no model needed: `scripts/agent-check.sh` runs Hermes's *own* loaders and reports (a) `AGENTS.md`'s canary is in the context Hermes would inject, (b) Hermes serves both skills with the current canary
(not a stale copy), (c) Hermes's injection scanner and `skills_guard` accept our files, (d) `hermes prompt-size` shows project context only inside the repo, (e) the trusted-repo path works — tested in a **throwaway profile**, so your real config is never touched.
Expected: **`CLAUDE.md`'s canary is absent for Hermes**: it loads only one project context file and `AGENTS.md` wins. By hand: `cd <repo> && hermes`, then ask the `AGENTS-MD` question.
Repo-local skills (`.agents/skills`) additionally need `hermes skills trust <repo>` (your decision — it is a security setting); the user-level copies work without it.

**FreeBuff** — has no non-interactive mode, so no script can prove it; the check is by hand: `cd <repo> && freebuff` (add `--trust-agents` to skip the trust prompt for the repo's `.agents` files), then ask the `AGENTS-MD` and `CLAUDE-MD` questions (FreeBuff reads both) and ask it to list its skills.
`scripts/agent-check.sh` reports this as **UNRESOLVED** — never as PASS — until a person confirms. A FreeBuff session was seen running the `new-run` protocol from this repo and writing a correct handoff (2026-09-19), which is evidence it loads the skill, but it is not a canary test.

**Claude Code** — `CLAUDE.md` loads automatically; ask the `CLAUDE-MD` question. Skills load from `.claude/skills/` (symlinks) or `~/.claude/skills/`.

## If a check fails

| Symptom | Likely cause | Fix |
|---|---|---|
| a canary answer is wrong or "I don't have that" | a weak model, or the file did not load | ask again once; then use the deterministic check (Hermes) or confirm the working directory is the repo root |
| Hermes: "skill content … WITHOUT the current canary" | stale user-level copy | `scripts/install-agent-skills.sh` |
| Hermes: `skills_guard … dangerous` | a scanner false positive in the skill (BUG-010) | do not install; read the finding; see `BUGS.md` |
| Hermes: repo skills do not load | repo not trusted | `hermes skills trust <repo>` (your decision) |
| FreeBuff does not know the skill | project not trusted / not started in the repo | start in the repo; `--trust-agents`; or install user-level copies |
| `agent-check` FAIL on a canary | the file no longer contains its canary | restore it; the canaries are asserted by `tests/test_bootstrap.py` |
