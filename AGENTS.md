# AGENTS.md — FCVE (Formal Claim Verification Engine)

Instructions for any AI coding agent working here (Claude Code, Hermes, FreeBuff, others). **The full instructions are in [`CLAUDE.md`](CLAUDE.md) — read it completely
before doing anything.** This file exists so agents that look for `AGENTS.md` (Hermes walks up from the working directory; FreeBuff reads it as a knowledge file) find the essentials
from any subdirectory. If this file and `CLAUDE.md` ever disagree, `CLAUDE.md` wins, and you should report the discrepancy.

**The repository is the source of truth; your memory is not. The model can propose. The experiment decides. Building is breaking.**

## Do, in order
1. Read `README.md`, then `CLAUDE.md` completely.
2. Run `scripts/doctor.sh` (identifies the environment; the validated one is a Mac mini, Apple M4, 16 GB, macOS 26.6.2 — anything else is *unvalidated*).
3. Load the verification skill: read `skills/verifying-lean-proofs/SKILL.md` (also discoverable at `.agents/skills/` and `.claude/skills/`).
4. Fix every doctor `FAIL`; resolve or report every `UNRESOLVED`. Run `scripts/setup.sh` only where something is missing (safe to repeat).
5. Run `scripts/smoke-test.sh`; it must say `SMOKE TEST PASSED`. Only then do FCVE work. Read `HANDOFF.md` for current state.

## Never
- Assume dependencies, cached builds, or earlier sessions are valid; silently install undocumented tools; silently modify a verification target, evidence, or a delivered run (ledgers are append-only).
- Turn `BLOCKED`, `TOOL_ERROR` or `UNRESOLVED` into `FAIL`, or missing evidence into `PASS`. Not-PASS is not FAIL. Unknown is never green.
- Write **TRUSTED**. `scripts/audit.sh` cannot produce it (ceiling: `PROVISIONAL`); rows 7 (a named human's semantic review) and 9 (web kernel-bug review) are not automated.
- Treat your own judgment as independent review. You may draft a semantic comparison, bridge verdict or decision as PROPOSED; a named human confirms. A second checker (nanoda) is independent of Lean's kernel, not of the statement's meaning.
- Claim patched tools (`tool-patches/`) equal upstream, or hide that a verdict used them. Delete anything the user did not ask you to delete.

## Commands
`scripts/doctor.sh` · `scripts/setup.sh [--reuse-from DIR]` · `scripts/smoke-test.sh` · `scripts/audit.sh <target> --module M --decl D [...]` · `scripts/run-tests.sh [--full]` · `scripts/agent-check.sh` · `python3 scripts/fcve.py -h`

Agent-specific notes (Hermes trust, FreeBuff skill discovery, hooks): [`docs/AGENT-INTEGRATIONS.md`](docs/AGENT-INTEGRATIONS.md).
