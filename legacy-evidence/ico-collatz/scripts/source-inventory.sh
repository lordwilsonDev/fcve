#!/usr/bin/env bash
# Phase 9: source inventory for a Lean project.
# Usage: source-inventory.sh <path-to-lean-project>
set -euo pipefail
TARGET="${1:?usage: source-inventory.sh <path-to-lean-project>}"

echo "# Source Inventory: $TARGET"
echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

echo "## Files"
find "$TARGET" -name '*.lean' -not -path '*/.lake/*' | sort

echo
echo "## Counts"
GREP_OPTS=(--include='*.lean' --exclude-dir=.lake --exclude-dir=.git)

FILES=$(find "$TARGET" -name '*.lean' -not -path '*/.lake/*' | wc -l | tr -d ' ')
THEOREMS=$({ grep -rhoE "${GREP_OPTS[@]}" '^\s*(theorem|lemma)\s+\S+' "$TARGET" 2>/dev/null | wc -l; } || true); THEOREMS=$(echo "$THEOREMS" | tr -d ' ')
DEFS=$({ grep -rhoE "${GREP_OPTS[@]}" '^\s*def\s+\S+' "$TARGET" 2>/dev/null | wc -l; } || true); DEFS=$(echo "$DEFS" | tr -d ' ')
AXIOMS_DECLARED=$({ grep -rhoE "${GREP_OPTS[@]}" '^\s*axiom\s+\S+' "$TARGET" 2>/dev/null | wc -l; } || true); AXIOMS_DECLARED=$(echo "$AXIOMS_DECLARED" | tr -d ' ')
UNSAFE=$({ grep -rn "${GREP_OPTS[@]}" -E '^\s*unsafe\b' "$TARGET" 2>/dev/null | wc -l; } || true); UNSAFE=$(echo "$UNSAFE" | tr -d ' ')

echo "lean_files=$FILES"
echo "theorems_and_lemmas=$THEOREMS"
echo "definitions=$DEFS"
echo "project_declared_axioms=$AXIOMS_DECLARED"
echo "unsafe_declarations=$UNSAFE"

echo
echo "## Imports (unique, top-level)"
{ grep -rhoE "${GREP_OPTS[@]}" '^import\s+\S+' "$TARGET" 2>/dev/null | sort -u; } || true
