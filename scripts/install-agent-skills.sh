#!/usr/bin/env bash
# install-agent-skills.sh -- make this repository's skills (skills/*/) available to the agents on this machine as USER-LEVEL skills.
#
#   scripts/install-agent-skills.sh [--agent claude|hermes|freebuff|all] [--skill NAME] [--dry-run] [--check]
#
# Skills: every directory under skills/ that has a SKILL.md (today: verifying-lean-proofs, new-run), or just --skill NAME.
# Targets (each is a copy of skills/<name>/; the repo copy stays the source of truth):
#   claude   ~/.claude/skills/<name>     (Claude Code, and FreeBuff also reads ~/.claude/skills)
#   hermes   ~/.hermes/skills/<name>     (Hermes user skills: not trust-gated like repo-local skills)
#   freebuff ~/.agents/skills/<name>     (FreeBuff user skills; the shared cross-agent skills dir)
# Behavior: absent -> copy; identical -> "up to date"; differs and the destination is an earlier copy of THIS skill (same `name:`) -> update it;
# differs and it is something else with that directory name -> REFUSE (never overwrite a different skill). Nothing outside those three
# directories is touched. It does not edit any agent's configuration and does not change any trust setting (see docs/AGENT-INTEGRATIONS.md).
# --check reports drift only (exit 1 if a copy differs or is missing); --dry-run prints what would change.
# Exit: 0 ok | 1 drift/missing (with --check) or a refusal | 2 usage
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; AGENTS=all; DRY=0; CHECK=0; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in --agent) AGENTS="$2"; shift 2 ;; --skill) ONLY="$2"; shift 2 ;; --dry-run) DRY=1; shift ;; --check) CHECK=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;; *) echo "unknown argument: $1" >&2; exit 2 ;; esac
done
SKILLS=""; for d in "$ROOT"/skills/*/; do [ -f "$d/SKILL.md" ] && SKILLS="$SKILLS $(basename "$d")"; done
[ -n "$ONLY" ] && { case " $SKILLS " in *" $ONLY "*) SKILLS=" $ONLY" ;; *) echo "no such skill: $ONLY (have:$SKILLS)" >&2; exit 2 ;; esac; }
[ -n "$SKILLS" ] || { echo "no skills found under $ROOT/skills" >&2; exit 2; }
case "$AGENTS" in all) LIST="claude hermes freebuff" ;; claude|hermes|freebuff) LIST="$AGENTS" ;; *) echo "--agent must be claude, hermes, freebuff or all" >&2; exit 2 ;; esac
dest_for() { case "$1" in claude) echo "$HOME/.claude/skills/$2" ;; hermes) echo "$HOME/.hermes/skills/$2" ;; freebuff) echo "$HOME/.agents/skills/$2" ;; esac; }
skill_name() { sed -n 's/^name:[[:space:]]*//p' "$1/SKILL.md" 2>/dev/null | head -1 | tr -d '\r'; }
RC=0
for NAME in $SKILLS; do SRC="$ROOT/skills/$NAME"
for A in $LIST; do
  D=$(dest_for "$A" "$NAME"); PARENT=$(dirname "$D")
  if [ ! -d "$PARENT" ]; then
    if [ "$A" = hermes ] && ! command -v hermes >/dev/null 2>&1; then echo "[skip   ] $A/$NAME: Hermes is not installed"; continue; fi
    if [ "$A" = freebuff ] && ! command -v freebuff >/dev/null 2>&1; then echo "[skip   ] $A/$NAME: FreeBuff is not installed"; continue; fi
  fi
  if [ -d "$D" ] && diff -rq -x .DS_Store "$SRC" "$D" >/dev/null 2>&1; then echo "[current] $A/$NAME: $D is identical to the repo copy"; continue; fi
  if [ "$CHECK" = 1 ]; then echo "[DRIFT  ] $A/$NAME: $D $( [ -d "$D" ] && echo 'differs from' || echo 'is missing;' ) the repo copy"; RC=1; continue; fi
  if [ -d "$D" ] && [ "$(skill_name "$D")" != "$(skill_name "$SRC")" ]; then echo "[REFUSED] $A/$NAME: $D exists and is a different skill (name '$(skill_name "$D")'); not overwriting"; RC=1; continue; fi
  if [ "$DRY" = 1 ]; then echo "[dry-run] $A/$NAME: would $( [ -d "$D" ] && echo update || echo install ) $D"; continue; fi
  mkdir -p "$D" && rsync -a --delete --exclude=.DS_Store "$SRC/" "$D/" && echo "[ok     ] $A/$NAME: $( [ -f "$D/SKILL.md" ] && echo installed/updated ) $D" || { echo "[FAILED ] $A/$NAME: could not write $D"; RC=1; }
done
done
exit $RC
