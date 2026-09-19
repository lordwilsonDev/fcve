# Using FCVE from Hermes and FreeBuff

Both agents are installed on the validated Mac mini. This file records **how each one actually loads instructions and skills** — read from the agents' own code on this
machine, not assumed — what is wired up, what you still have to decide yourself, and what could not be verified. Re-verify with `scripts/agent-check.sh` (read-only).

| | Claude Code | Hermes (v0.21.2) | FreeBuff (0.0.180, a Codebuff rebrand) |
|---|---|---|---|
| Auto-loaded instructions | `CLAUDE.md` | **one** project context file, first found wins: `.hermes.md`/`HERMES.md` → **`AGENTS.md`** (git root → cwd) → `CLAUDE.md` (cwd only) → `.cursorrules` | knowledge files in a directory: `knowledge.md`, `AGENTS.md`, `CLAUDE.md` |
| What it therefore gets here | `CLAUDE.md` (full) | `AGENTS.md` (short, self-contained; **not** `CLAUDE.md` — it only loads one) | both |
| Repo skill discovery | `.claude/skills/<name>/SKILL.md` | `.hermes/skills/` and `.agents/skills/` — **only if the repo is trusted** | `.agents/skills/` and `.claude/skills/` (project), then `~/.agents/skills`, `~/.claude/skills` |
| User-level skill | `~/.claude/skills/<name>` | `~/.hermes/skills/<name>` (no trust step) | `~/.agents/skills/<name>`, `~/.claude/skills/<name>` |
| Safety hooks on shell commands | `~/.claude/settings.json` | `~/.hermes/config.yaml` → `~/.agents/hooks/deny-dangerous.sh hermes` | none found |

## What is wired up (all by files in this repository or `scripts/install-agent-skills.sh`)

- `AGENTS.md` (root): the short, agent-neutral entry point. It carries the hard rules itself because Hermes will not also load `CLAUDE.md`; it tells the agent to read `CLAUDE.md` for the rest.
- `.agents/skills/verifying-lean-proofs` and `.claude/skills/verifying-lean-proofs`: symlinks to `skills/verifying-lean-proofs/` (one source of truth). Hermes and FreeBuff resolve symlinks
  (Hermes `Path.is_dir()`; FreeBuff `fs.statSync().isDirectory()`).
- User-level copies, installed by `scripts/install-agent-skills.sh` (idempotent; refuses to overwrite a *different* skill; touches nothing else; changes no agent configuration):
  `~/.hermes/skills/verifying-lean-proofs`, `~/.agents/skills/verifying-lean-proofs`, `~/.claude/skills/verifying-lean-proofs`. `scripts/install-agent-skills.sh --check` reports drift; the repo copy is the source of truth.

## What compatibility work was needed

- **Hermes runs its own injection scanner on context files and `skills_guard` on repo skills.** `CLAUDE.md`, `AGENTS.md` and `README.md` are not blocked. The skill was first rated **"dangerous"** (which would quarantine it in a
  trusted repo) because `audit.sh` had a local variable literally named `host` followed by `$(...)`, which matched Hermes's DNS-exfiltration rule (`host <space> ... $`). It only recorded hardware facts to a local file; the key
  was renamed `machine`, and the verdict is now **safe** (remaining findings are medium/low and accurate: e.g. the setup script runs `git clone`). `scripts/agent-check.sh` re-runs Hermes's scanners so a regression is caught.
- **The global command guard** (`~/.agents/hooks/deny-dangerous.sh`, Hermes mode) allows every documented FCVE command and still blocks `rm -rf /` (the control that shows the check is not vacuous).

## What you have to decide (not done for you)

- **Trust this repo in Hermes** so its repo-local `.agents/skills` loads: `hermes skills trust /path/to/fcve`. Trust is a prompt-injection defense and a security decision, so nothing here runs it. Until you do, Hermes still has the skill through the
  user-level copy, and still reads `AGENTS.md`. (Hermes rescans every project `SKILL.md` with `skills_guard` and quarantines a `dangerous` one even in a trusted repo, so a later change to the skill can un-load it.)
- **FreeBuff's trust prompt** for project `.agents` files: answer it, or pass `--trust-agents` (documented as "for CI"). FreeBuff's own memory vault (`~/FREEBUFF_PZS`) is untouched.

## Verified, and how

| Claim | Evidence |
|---|---|
| Hermes loads project context here and not elsewhere | `hermes prompt-size` (offline): context block **4,552 B** in the repo, **0 B** from `/tmp` (it includes Hermes's own `SOUL.md`; `AGENTS.md` is 2,586 B) |
| Hermes has the skill in its index | `prompt-size --json` → `skills_breakdown` lists `verifying-lean-proofs` with path `~/.hermes/skills/...`; `hermes skills list` shows it (local, enabled) |
| Hermes scanners are satisfied | `scripts/agent-check.sh` runs `_scan_context_content` and `skills_guard.scan_skill` from Hermes's own Python |
| FreeBuff's discovery paths and limits | read from the FreeBuff binary: search list `[.agents/skills, .claude/skills, ~/.agents/skills, ~/.claude/skills]`, name slug `^[a-z0-9]+(-[a-z0-9]+)*$` ≤64, description ≤1024 |

## Not verified — be honest

- **FreeBuff live behavior.** FreeBuff has no non-interactive mode, so no script can show it loaded the skill or the instructions in a session. To confirm by hand: `cd <repo> && freebuff`, then ask it to list its skills and read back the first three steps in `AGENTS.md`.
- **Model behavior.** Two one-shot Hermes questions (`hermes -z`, default free model `solar-pro4:free`) gave one correct answer and one "I don't have the repository's instructions" — the model, not the loading, is the weak link there. Trust `prompt-size`, not the model's self-report.
- Hermes with the repo **trusted** (repo-local skills path) was not exercised, because trust was not granted.
- Nothing here was tried through Hermes's Telegram gateway or FreeBuff Desktop.
