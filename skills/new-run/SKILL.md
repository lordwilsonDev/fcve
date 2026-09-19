---
name: new-run
description: Use at the start of a new or resumed session on the FCVE repository (when the user says "new run", "resume", "continue", "handoff", or opens a fresh clone), and again at the end of a session to write the handoff. Loads context from the repository instead of memory, verifies the environment, checks the handoff's claims against reality, and reports the real state before touching anything. Works in Claude Code, Hermes and FreeBuff.
---

# new-run — start, resume, and close an FCVE session

**A handoff is a set of claims, not facts.** Your job at the start of a run is to rebuild context from the repository and *check* what the last session said, not to trust it.
The model can propose; the experiment decides.

## Starting or resuming a run (do these in order; stop and report if one fails)

1. **Read the repo's own instructions.** `AGENTS.md`, then `CLAUDE.md` completely, then `README.md`. (Hermes only auto-loads `AGENTS.md`; read the rest yourself.)
2. **Read the current state.** Open `HANDOFF.md` and read only the block at the top, "CURRENT STATE". Everything under "History" may be stale.
3. **Look at reality.** `git log --oneline | head`, `git status --short`. Note anything uncommitted: it is someone's unfinished work, not yours to discard.
4. **Check the environment.** `scripts/doctor.sh`. Resolve or report every `FAIL` and `UNRESOLVED`. If tools are not built, `scripts/setup.sh` (safe to repeat; `--dry-run` first if disk is tight).
5. **Prove the machinery works.** `scripts/smoke-test.sh` must end with `SMOKE TEST PASSED`. If unsure the agent wiring is intact, `scripts/agent-check.sh` (read-only).
6. **Check the handoff's claims that matter to what you are about to do**, each with a command, not by inference:
   `python3 scripts/fcve.py verify deliverables/<pkg>/event-ledger.jsonl` (chain intact), `receipt-check` (receipt current), `shasum -a 256 -c MANIFEST.sha256` (inside a package),
   `ls docs/clean-room-records`, `git log` for the commits it names. Where the handoff and the repo disagree, **the repo wins**; say so.
7. **Load the audit skill** when the task involves Lean proofs: `skills/verifying-lean-proofs/SKILL.md`, then its `PROOF-TRUST-MATRIX.md` and `LESSONS.md`.
8. **Report before acting**, in a few lines: what is done, what is open, what changed since the handoff, anything that contradicted it, and what needs a human decision.
   Offer options with a recommendation. Do not push urgency and do not start work the user has not asked for.

## Hard rules (the short list — the full one is in `CLAUDE.md`)

- Ledgers are append-only: supersede, never edit; archive, don't delete. Never modify a delivered run or a verification target.
- Verdicts, bridge verdicts, limitations and governance decisions belong to a named human. Draft them as PROPOSED; ask with concrete options; record the answer as theirs.
- Never turn `BLOCKED` / `TOOL_ERROR` / `UNRESOLVED` into `FAIL`, or missing evidence into `PASS`. `scripts/audit.sh` cannot produce `TRUSTED`.
- Do not change security settings (for example a trust list), send anything outward, or delete anything unless asked for that specific thing.
- Tell the user when something does not add up, even if it is inconvenient.

## Closing a run — writing the handoff (do this before the session ends)

1. **Verify what you are about to claim.** Re-run the check for every "done" you will write (tests, doctor, smoke, verify). Note what you did **not** verify, in plain words.
2. **Update `HANDOFF.md`'s CURRENT STATE block** in place (facts, results, open items in the order you'd look at them, decisions that are the user's). Keep old material under History; do not delete it. Mark stale text as stale.
3. **Update the mirrors:** the running note in `~/Documents/Vault/40_Memory/` (Edit/Write tools, not a shell heredoc) and the project memory entry. Tell the user what you saved and where.
4. **Commit and push** with an absolute-path `cd` (the commit hook needs it), only if the user has asked you to commit. Say plainly what is uncommitted if not.
5. **Write down honestly** what is unverified, what needs the user, and what you would do next — as options, without urgency.

## When something is unclear

Ask one short question with concrete options. Do not guess a verdict, a name, or a destination for outward-facing actions (publishing, pushing, trusting, deleting).
