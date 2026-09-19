#!/usr/bin/env bash
# Phase 11: axiom audit for one theorem in a built Lean project.
# Usage: axiom-audit.sh <project-dir> <Fully.Qualified.theoremName>
set -euo pipefail
PROJECT="${1:?usage: axiom-audit.sh <project-dir> <theorem-name>}"
THEOREM="${2:?usage: axiom-audit.sh <project-dir> <theorem-name>}"

cd "$PROJECT"
echo "# Axiom Audit: $THEOREM"
echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "project: $PROJECT"
echo

TMP=$(mktemp /tmp/axiom-check-XXXX.lean)
echo "#print axioms $THEOREM" > "$TMP"
# Requires the theorem's module to already be imported by the caller's own
# probe file; this script prints the command to run manually inside the
# project's REPL / a scratch file that imports the relevant module, since
# `#print axioms` needs the declaration in scope.
echo "Run inside a .lean file (in this project, importing the module that"
echo "declares $THEOREM):"
echo
echo "  #print axioms $THEOREM"
echo
echo "Classify each reported axiom as one of:"
echo "  KERNEL_STANDARD | MATHLIB_STANDARD | CLASSICAL | PROJECT_AXIOM | EXTERNAL_AXIOM | UNKNOWN"
rm -f "$TMP"
