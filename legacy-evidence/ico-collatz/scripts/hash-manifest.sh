#!/usr/bin/env bash
# Phase 32: hash a set of paths into a SHA-256 manifest.
# Usage: hash-manifest.sh <output-file> <path> [<path> ...]
set -euo pipefail
OUT="${1:?usage: hash-manifest.sh <output-file> <path> [<path> ...]}"
shift

{
  echo "# SHA-256 Manifest"
  echo "generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  for p in "$@"; do
    if [ -f "$p" ]; then
      shasum -a 256 "$p"
    elif [ -d "$p" ]; then
      find "$p" -type f -not -path '*/.lake/*' -not -path '*/.git/*' | sort | xargs shasum -a 256
    fi
  done
} > "$OUT"

echo "Wrote manifest: $OUT ($(wc -l < "$OUT") lines)"
