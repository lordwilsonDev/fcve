#!/usr/bin/env bash
# restore.sh -- after a fresh clone, put back the things git deliberately does not carry, verified by hash. Idempotent; never deletes; never overwrites.
#
#   scripts/restore.sh [--from DIR] [--dry-run]
#
# What git cannot carry: the third-party source PDFs (gitignored: copyright). Each run's tracked `source/source-metadata.json` records the PDF's sha256.
# For every such PDF that is missing, this finds a file with EXACTLY that sha256 (in --from DIR, or in a fresh clone of the upstream repo at the pinned
# commit in manifests/environment.json) and copies it into place. A file whose hash does not match is never used (UNRESOLVED, exit 3).
# It does not build tools (scripts/setup.sh) or install skills (scripts/install-agent-skills.sh); it prints what else a wipe would have removed.
# Exit: 0 everything present/restored | 3 something could not be restored (hash not found) | 2 usage/prerequisite
set -u
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"
FROM=""; DRY=0
while [ $# -gt 0 ]; do case "$1" in --from) FROM="$2"; shift 2 ;; --dry-run) DRY=1; shift ;; -h|--help) sed -n '2,13p' "$0"; exit 0 ;; *) echo "unknown argument: $1" >&2; exit 2 ;; esac; done
have python3 || { echo "python3 required" >&2; exit 2; }
cd "$FCVE_ROOT" || exit 2

NEEDED=$(python3 - <<'PY'
import glob, json, os
for meta in sorted(glob.glob("*/source/source-metadata.json") + glob.glob("*/*/source/source-metadata.json")):
    if meta.startswith(".fcve-work"): continue
    d = json.load(open(meta)); rel = d.get("source_original", "")
    if not rel.lower().endswith(".pdf") or not d.get("source_sha256"): continue
    target = os.path.join(os.path.dirname(os.path.dirname(meta)), rel)
    print(f"{target}\t{d['source_sha256']}\t{'present' if os.path.exists(target) else 'missing'}")
PY
)
[ -n "$NEEDED" ] || { echo "no runs with a recorded PDF source: nothing to restore"; exit 0; }
MISSING=$(printf '%s\n' "$NEEDED" | awk -F'\t' '$3=="missing"' | wc -l | tr -d ' ')
echo "source PDFs recorded: $(printf '%s\n' "$NEEDED" | wc -l | tr -d ' '); missing: $MISSING"
# present ones must match their recorded hash too (a wrong file is worse than a missing one)
RC=0
printf '%s\n' "$NEEDED" | awk -F'\t' '$3=="present"' | while IFS=$'\t' read -r T H S; do
  [ "$(sha256_of "$T")" = "$H" ] && echo "  [ok       ] $T (sha256 matches the recorded value)" || { echo "  [MISMATCH ] $T does not match its recorded sha256 ${H:0:12}…: NOT touched; investigate"; echo x >>"$RESULTS_FILE.unresolved"; }
done
if [ "$MISSING" = 0 ]; then
  if [ -s "$RESULTS_FILE.unresolved" ]; then rm -f "$RESULTS_FILE.unresolved"; echo "RESTORE: a present file does not match its recorded hash"; exit 3; fi
  rm -f "$RESULTS_FILE.unresolved"; echo "nothing missing"; exit 0
fi
[ "$DRY" = 1 ] && { printf '%s\n' "$NEEDED" | awk -F'\t' '$3=="missing"{print "  would restore " $1}'; exit 0; }

if [ -z "$FROM" ]; then
  REPO=$(mf 'd["restore"]["source_pdf"]["repo"]'); COMMIT=$(mf 'd["restore"]["source_pdf"]["commit"]')
  FROM="$FCVE_WORK_DEFAULT/restore-sources/$(basename "$REPO" .git)"; mkdir -p "$(dirname "$FROM")"
  if [ ! -d "$FROM/.git" ]; then have git || { echo "git required" >&2; exit 2; }
    echo "cloning $REPO @ ${COMMIT:0:12} into $FROM"; git clone -q "$REPO" "$FROM" && git -C "$FROM" checkout -q "$COMMIT" || { echo "could not clone/checkout the source repository"; exit 3; }
  fi
fi
[ -d "$FROM" ] || { echo "--from $FROM is not a directory" >&2; exit 2; }
CANDS=$(find "$FROM" -name '.git' -prune -o -type f \( -iname '*.pdf' \) -print 2>/dev/null)
printf '%s\n' "$NEEDED" | awk -F'\t' '$3=="missing"' | while IFS=$'\t' read -r T H S; do
  FOUND=""; for C in $CANDS; do [ "$(sha256_of "$C")" = "$H" ] && { FOUND="$C"; break; }; done
  if [ -z "$FOUND" ]; then echo "  [UNRESOLVED] $T: no PDF under $FROM has sha256 ${H:0:12}…"; echo x >>"$RESULTS_FILE.unresolved"; continue; fi
  mkdir -p "$(dirname "$T")"; cp -n "$FOUND" "$T" && [ "$(sha256_of "$T")" = "$H" ] && echo "  [restored ] $T <- ${FOUND#$FROM/} (sha256 verified)" || { echo "  [FAILED   ] $T"; echo x >>"$RESULTS_FILE.unresolved"; }
done
if [ -s "$RESULTS_FILE.unresolved" ]; then rm -f "$RESULTS_FILE.unresolved"; echo "RESTORE: incomplete (see UNRESOLVED lines): unknown is not restored"; exit 3; fi
rm -f "$RESULTS_FILE.unresolved"
echo; echo "Also removed by a wipe (not handled here): checker tool builds -> scripts/setup.sh [--reuse-from DIR]; user-level skill copies -> scripts/install-agent-skills.sh;"
echo "the VCE-002 Lean project -> git clone https://github.com/lordwilsonDev/ico-collatz-verification; the eliahou audit target -> clone tangentstorm/eliahou-collatz-bounds @ db804ce (+ ~10 GB Mathlib cache). See docs/RESTORE.md."
echo "RESTORE: complete"
