#!/usr/bin/env bash
# clean-room.sh -- automate docs/CLEAN_ROOM_REPRODUCIBILITY.md steps 1-5 and 9-14 (one or more runs), and write a record per run.
#
#   scripts/clean-room.sh [--runs N] [--source URL_OR_PATH] [--reuse-from DIR] [--records DIR] [--restore-from DIR] [--tags "v4.28.0 v4.34.0"]
#
# For each run it: clones the repository FRESH (default source: this repo's `origin`, i.e. the pushed state, not your working tree) into a
# throwaway directory it creates; runs doctor -> setup -> doctor -> smoke-test -> a representative audit using THE CLONE'S OWN scripts; records
# commit, host, per-step exit codes and timings, and every non-PASS line; then deletes ONLY the throwaway directory it created.
#
# It does NOT start a fresh Claude session (step 6-8 of the procedure): that part needs a person to open Claude in the clone. The record says so.
# It never touches a verification target, your working tree, or anything outside its own mktemp directory and --records.
# --reuse-from DIR adopts existing verified checker builds (saves disk; recorded in the record as "adopted", which is NOT a from-scratch build).
# Without it, setup builds the tools from scratch and will REFUSE (BLOCKED, exit 4) if the disk cannot hold them above the floor.
# Exit: 0 every run passed | 1 a run failed | 3 no failure but a run was BLOCKED (insufficient disk: no verdict) | 2 usage
set -u
# classify_run <doctor-after-log> <setup-exit> -> prints BLOCKED (insufficient disk: no verdict on the repository) or empty.
# A run is BLOCKED when setup refused for disk (exit 4), or when the ONLY doctor FAIL lines are storage lines. Anything else non-zero is a FAIL.
classify_run() {
  local dlog="$1" setup_rc="$2"
  if [ "$setup_rc" = 4 ]; then echo BLOCKED; return; fi
  if [ -f "$dlog" ] && grep -q '^\[FAIL' "$dlog" && ! grep '^\[FAIL' "$dlog" | grep -qv ' storage '; then echo BLOCKED; fi
}
[ "${1:-}" = "--source-only" ] && return 0 2>/dev/null
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNS=1; SOURCE=""; REUSE=""; RESTORE_FROM=""; RECORDS="$HERE/docs/clean-room-records"; TAGS="v4.28.0 v4.34.0"
while [ $# -gt 0 ]; do
  case "$1" in
    --runs) RUNS="$2"; shift 2 ;; --source) SOURCE="$2"; shift 2 ;; --reuse-from) REUSE="$2"; shift 2 ;;
    --records) RECORDS="$2"; shift 2 ;; --restore-from) RESTORE_FROM="$2"; shift 2 ;; --tags) TAGS="$2"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$SOURCE" ] || SOURCE=$(git -C "$HERE" remote get-url origin 2>/dev/null) || { echo "no --source and no origin remote" >&2; exit 2; }
mkdir -p "$RECORDS" || exit 2
BASE=$(mktemp -d "${TMPDIR:-/tmp}/fcve-cleanroom.XXXXXX") || exit 2
case "$BASE" in */fcve-cleanroom.*) ;; *) echo "refusing: unexpected temp dir $BASE" >&2; exit 2 ;; esac
trap 'rm -rf "$BASE"' EXIT      # deletes only the directory created above

TAGARGS=""; for T in $TAGS; do TAGARGS="$TAGARGS --tag $T"; done
ALLPASS=1; DATE=$(date -u +%Y-%m-%d)
for N in $(seq 1 "$RUNS"); do
  CLONE="$BASE/run$N"; REC="$RECORDS/$DATE-run$N-$(date -u +%H%M%S).md"; STEPS=""; RUNPASS=1
  step() { # step <name> <cmd...>  -> appends a table row, runs in the clone
    local name="$1"; shift; local t0 rc; t0=$(date +%s)
    ( cd "$CLONE" && "$@" ) >"$BASE/run$N-$name.log" 2>&1; rc=$?
    local secs=$(( $(date +%s) - t0 ))
    local notes; notes=$(grep -E '^\[ ?(WARN|FAIL|UNRESOLVED)|BLOCKED|SMOKE TEST|SETUP (COMPLETE|INCOMPLETE)|DOCTOR:|REJECTED|Verdict' "$BASE/run$N-$name.log" | head -6 | tr '\n' ';' | sed 's/|/\\|/g' | cut -c1-400)
    STEPS="$STEPS| $name | \`$*\` | $rc | $secs | ${notes:-} |
"
    echo "run $N: $name exit=$rc (${secs}s)"; return $rc
  }
  echo "== clean-room run $N/$RUNS: cloning $SOURCE =="
  rm -rf "$CLONE"; git clone -q "$SOURCE" "$CLONE" || { echo "clone failed"; ALLPASS=0; continue; }
  COMMIT=$(git -C "$CLONE" rev-parse HEAD); HOSTINFO="$(sysctl -n hw.model 2>/dev/null), $(sysctl -n machdep.cpu.brand_string 2>/dev/null), $(python3 -c "print(round($(sysctl -n hw.memsize 2>/dev/null || echo 0)/1073741824))")GB, macOS $(sw_vers -productVersion 2>/dev/null), free disk $(df -h / | tail -1 | awk '{print $4}')"
  step doctor-before   bash scripts/doctor.sh                      # a fresh clone: FAIL for unbuilt tools is the EXPECTED, correct answer
  # restore what git does not carry (gitignored source PDFs), verified by sha256; --restore-from avoids the network
  RESTORE=(bash scripts/restore.sh); [ -n "${RESTORE_FROM:-}" ] && RESTORE=(bash scripts/restore.sh --from "$RESTORE_FROM")
  step restore         "${RESTORE[@]}" || RUNPASS=0
  SETUP=(bash scripts/setup.sh $TAGARGS); [ -n "$REUSE" ] && SETUP=(bash scripts/setup.sh $TAGARGS --reuse-from "$REUSE")
  RESULT=PASS; BLOCKED_RUN=""
  step setup           "${SETUP[@]}"; SETUP_RC=$?; [ "$SETUP_RC" -eq 0 ] || RUNPASS=0
  step doctor-after    bash scripts/doctor.sh; DOC_RC=$?; [ "$DOC_RC" -eq 0 ] || RUNPASS=0
  if [ "$RUNPASS" = 0 ]; then BLOCKED_RUN=$(classify_run "$BASE/run$N-doctor-after.log" "$SETUP_RC"); fi
  if [ -n "$BLOCKED_RUN" ]; then
    # BUG-011: a run stopped by insufficient disk has NO verdict on the repository. Do not run the heavy steps, and do not call it FAIL.
    STEPS="$STEPS| smoke-test | (skipped) | - | - | not run: blocked by insufficient disk |
| audit | (skipped) | - | - | not run: blocked by insufficient disk |
"; RESULT=BLOCKED; echo "run $N: BLOCKED (insufficient disk) -- no verdict on the repository"
  else
    step smoke-test      bash scripts/smoke-test.sh || RUNPASS=0
    step audit           bash scripts/audit.sh tests/fixtures/mini-lean-ok --module Mini --decl mini_add --decl mini_comm --fast-literals no --out "$CLONE/.fcve-work/cleanroom-audit" || RUNPASS=0
    grep -q '^## Verdict: PROVISIONAL' "$CLONE/.fcve-work/cleanroom-audit/AUDIT.md" 2>/dev/null || { echo "run $N: audit verdict is not PROVISIONAL"; RUNPASS=0; }
    grep -q 'SMOKE TEST PASSED' "$BASE/run$N-smoke-test.log" || RUNPASS=0
    [ "$RUNPASS" = 1 ] || RESULT=FAIL
  fi
  case "$RESULT" in PASS) ;; BLOCKED) [ "$ALLPASS" = 1 ] && ALLPASS=2 ;; FAIL) ALLPASS=0 ;; esac
  {
    echo "# Clean-room run $N — $DATE (scripted: scripts/clean-room.sh)"
    echo "- Repository commit under test: \`$COMMIT\`  (cloned fresh from \`$SOURCE\`)"
    echo "- Host: $HOSTINFO"
    echo "- Fresh Claude session reading README/CLAUDE.md (procedure steps 6-8): **NO — not done by this script; requires a person to open Claude in a fresh clone**"
    if [ -n "$REUSE" ]; then echo "- Checker tools: **ADOPTED via --reuse-from \`$REUSE\` (verified by commit + patch equality) — NOT rebuilt from scratch.** A from-scratch tool build was not part of this run."
    else echo "- Checker tools: built from scratch by setup.sh"; fi
    echo "- Manual interventions not written in the repository: none by this script"
    echo; echo "| Step | Command | Exit | Seconds | Notes (WARN / FAIL / UNRESOLVED / verdict lines) |"; echo "|---|---|---|---|---|"; printf '%s' "$STEPS"
    echo; echo "- Engine test suites skipped in the fresh clone (after restore.sh): $(grep -o 'engine test suite: [a-z]* (skipped=[0-9]*' "$BASE/run$N-smoke-test.log" 2>/dev/null | tr '\n' ';' | sed 's/;$//' | grep . || echo none)"
    echo "- Audit verdict line: \`$(grep -m1 '^## Verdict' "$CLONE/.fcve-work/cleanroom-audit/AUDIT.md" 2>/dev/null)\`"
    case "$RESULT" in
      PASS) echo "- **Result: PASS**  (doctor-before is informational: a fresh clone is expected to be NOT READY until setup)" ;;
      BLOCKED) echo "- **Result: BLOCKED (insufficient disk)** — NOT a FAIL of the repository: setup/doctor stopped because free disk was below the in-flight requirement, so no verdict was reached. Re-run with more free space." ;;
      *) echo "- **Result: FAIL**" ;;
    esac
    if [ "$RESULT" = PASS ]; then echo "- Logs: removed with the throwaway clone; the notes column keeps the relevant lines."
    else echo "- Logs kept (BUG-011): \`logs/$(basename "$REC" .md)/\` beside this record."; fi
  } >"$REC"
  if [ "$RESULT" != PASS ]; then mkdir -p "$RECORDS/logs/$(basename "$REC" .md)" && cp "$BASE"/run$N-*.log "$RECORDS/logs/$(basename "$REC" .md)/" 2>/dev/null; fi
  echo "run $N: $RESULT -> $REC"
  rm -rf "$CLONE"          # destroy the environment (step 14): only the throwaway clone
done
case "$ALLPASS" in
  1) echo "CLEAN-ROOM: $RUNS run(s) PASSED"; exit 0 ;;
  2) echo "CLEAN-ROOM: no failures, but at least one run was BLOCKED by insufficient disk (no verdict for those; see records)"; exit 3 ;;
  *) echo "CLEAN-ROOM: at least one run FAILED (see records)"; exit 1 ;;
esac
