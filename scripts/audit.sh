#!/usr/bin/env bash
# scripts/audit.sh -- one-command audit of a Lean project (the documented entry point).
#
#   scripts/audit.sh <target-dir> --module <Module> --decl <theorem> [--decl <theorem2> ...] \
#       [--fast-literals auto|yes|no] [--out <dir>] [--work <dir>] [--rebuild] [--skip-independent]
#
# Thin wrapper over skills/verifying-lean-proofs/scripts/audit.sh: it defaults --work to <repo>/.fcve-work (where
# scripts/setup.sh put the checker tools) and reminds you if setup has not been run. Everything else is passed through.
# It never modifies the target, and its best verdict is PROVISIONAL -- never TRUSTED (rows 7 and 9 need a human and the web).
# Exit codes are the skill script's: 0 finished (read AUDIT.md for the verdict), 2 usage, 3 BLOCKED before any work (e.g. disk).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case " $* " in *" --work "*) ;; *) set -- "$@" --work "$ROOT/.fcve-work" ;; esac
if [ ! -f "$ROOT/.fcve-work/setup-record.json" ] && case " $* " in *" --skip-independent "*) false ;; *) true ;; esac; then
  echo "note: $ROOT/.fcve-work/setup-record.json not found -- the independent check needs the checker tools. Run scripts/setup.sh first (or pass --skip-independent for rows 1-9 only)." >&2
fi
exec bash "$ROOT/skills/verifying-lean-proofs/scripts/audit.sh" "$@"
