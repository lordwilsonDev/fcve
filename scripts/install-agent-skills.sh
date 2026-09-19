#!/usr/bin/env bash
# install-agent-skills.sh -- make the verification skill available to the agents on this machine as a USER-LEVEL skill.
#
#   scripts/install-agent-skills.sh [--agent claude|hermes|freebuff|all] [--dry-run] [--check]
#
# Targets (each is a copy of skills/verifying-lean-proofs/; the repo copy stays the source of truth):
#   claude   ~/.claude/skills/verifying-lean-proofs     (Claude Code, and FreeBuff also reads ~/.claude/skills)
#   hermes   ~/.hermes/skills/verifying-lean-proofs     (Hermes user skills: not trust-gated like repo-local skills)
#   freebuff ~/.agents/skills/verifying-lean-proofs     (FreeBuff user skills; the shared cross-agent skills dir)
# Behavior: absent -> copy; identical -> "up to date"; differs and the destination is an earlier copy of THIS skill (same `name:`) -> update it;
# differs and it is something else with that directory name -> REFUSE (never overwrite a different skill). Nothing outside those three
# directories is touched. It does not edit any agent's configuration and does not change any trust setting (see docs/AGENT-INTEGRATIONS.md).
# --check reports drift only (exit 1 if a copy differs or is missing); --dry-run prints what would change.
# Exit: 0 ok | 1 drift/missing (with --check) or a refusal | 2 usage
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; SRC="$ROOT/skills/verifying-lean-proofs"; NAME=verifying-lean-proofs
AGENTS=all; DRY=0; CHECK=0
while [ $# -gt 0 ]; do
  case "$1" in --agent) AGENTS="$2"; shift 2 ;; --dry-run) DRY=1; shift ;; --check) CHECK=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;; *) echo "unknown argument: $1" >&2; exit 2 ;; esac
done
[ -f "$SRC/SKILL.md" ] || { echo "source skill missing: $SRC" >&2; exit 2; }
case "$AGENTS" in all) LIST="claude hermes freebuff" ;; claude|hermes|freebuff) LIST="$AGENTS" ;; *) echo "--agent must be claude, hermes, freebuff or all" >&2; exit 2 ;; esac
dest_for() { case "$1" in claude) echo "$HOME/.claude/skills/$NAME" ;; hermes) echo "$HOME/.hermes/skills/$NAME" ;; freebuff) echo "$HOME/.agents/skills/$NAME" ;; esac; }
skill_name() { sed -n 's/^name:[[:space:]]*//p' "$1/SKILL.md" 2>/dev/null | head -1 | tr -d '\r'; }
RC=0
for A in $LIST; do
  D=$(dest_for "$A"); PARENT=$(dirname "$D")
  if [ ! -d "$PARENT" ]; then
    if [ "$A" = hermes ] && ! command -v hermes >/dev/null 2>&1; then echo "[skip   ] $A: Hermes is not installed"; continue; fi
    if [ "$A" = freebuff ] && ! command -v freebuff >/dev/null 2>&1; then echo "[skip   ] $A: FreeBuff is not installed"; continue; fi
  fi
  if [ -d "$D" ] && diff -rq -x .DS_Store "$SRC" "$D" >/dev/null 2>&1; then echo "[current] $A: $D is identical to the repo copy"; continue; fi
  if [ "$CHECK" = 1 ]; then echo "[DRIFT  ] $A: $D $( [ -d "$D" ] && echo 'differs from' || echo 'is missing;' ) the repo copy"; RC=1; continue; fi
  if [ -d "$D" ] && [ "$(skill_name "$D")" != "$(skill_name "$SRC")" ]; then echo "[REFUSED] $A: $D exists and is a different skill (name '$(skill_name "$D")'); not overwriting"; RC=1; continue; fi
  if [ "$DRY" = 1 ]; then echo "[dry-run] $A: would $( [ -d "$D" ] && echo update || echo install ) $D"; continue; fi
  mkdir -p "$D" && rsync -a --delete --exclude=.DS_Store "$SRC/" "$D/" && echo "[ok     ] $A: $( [ -f "$D/SKILL.md" ] && echo installed/updated ) $D" || { echo "[FAILED ] $A: could not write $D"; RC=1; }
done
exit $RC
