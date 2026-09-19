#!/usr/bin/env bash
# Phase 10: sorry audit. Usage: sorry-audit.sh <path-to-lean-project>
set -euo pipefail
TARGET="${1:?usage: sorry-audit.sh <path-to-lean-project>}"

echo "# Sorry Audit: $TARGET"
echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

GREP_OPTS=(--include='*.lean' --exclude-dir=.lake --exclude-dir=.git)

SORRY_COUNT=$({ grep -rn "${GREP_OPTS[@]}" -E '\bsorry\b' "$TARGET" 2>/dev/null | wc -l; } || true)
SORRY_COUNT=$(echo "$SORRY_COUNT" | tr -d ' ')
ADMIT_COUNT=$({ grep -rn "${GREP_OPTS[@]}" -E '\badmit\b' "$TARGET" 2>/dev/null | wc -l; } || true)
ADMIT_COUNT=$(echo "$ADMIT_COUNT" | tr -d ' ')
NATIVE_DECIDE_COUNT=$({ grep -rn "${GREP_OPTS[@]}" -E 'native_decide' "$TARGET" 2>/dev/null | wc -l; } || true)
NATIVE_DECIDE_COUNT=$(echo "$NATIVE_DECIDE_COUNT" | tr -d ' ')

echo "SORRY_COUNT=$SORRY_COUNT"
echo "ADMITTED_COUNT=$ADMIT_COUNT"
echo "NATIVE_DECIDE_COUNT=$NATIVE_DECIDE_COUNT"
echo

if [ "$SORRY_COUNT" -gt 0 ]; then
  echo "## sorry occurrences"
  grep -rn "${GREP_OPTS[@]}" -E '\bsorry\b' "$TARGET"
fi

if [ "$NATIVE_DECIDE_COUNT" -gt 0 ]; then
  echo "## native_decide occurrences (bypasses kernel type-checking of the decision procedure)"
  grep -rn "${GREP_OPTS[@]}" -E 'native_decide' "$TARGET"
fi
