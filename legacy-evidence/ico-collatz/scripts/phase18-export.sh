#!/usr/bin/env bash
# Phase 18 — export the dependency closure of one or more declarations from the
# (read-only) target repo, while monitoring free disk.
#
# Usage: bash scripts/phase18-export.sh <decl> [<decl>...] [--module <Name>]
#
# Background: the first attempt at the headline theorem
# (`results_eliahou_theorem_1_1`) was aborted twice — once by the previous
# session under memory/disk pressure, once by this session after measuring that
# the exporter stops emitting output entirely:
#   ~100 s   -> 71,147,520 bytes / 1,336,962 lines / 1.2 M expression nodes
#   +8 min   -> 0 further bytes at 100% CPU, RSS collapsed to ~64 MB
# and the requested declaration's name never appears in the output at all.
# That abort is recorded in receipts/correction-ledger.md. This script keeps a
# free-disk floor so a long run cannot repeat the earlier disk exhaustion.
set -u

TARGET="$HOME/ico-collatz/targets/eliahou-collatz-bounds"
EXPORT_BIN="$HOME/ico-collatz/targets/lean4export/.lake/build/bin/lean4export"
OUT_DIR="$HOME/ico-collatz/experiments/independent-checker"
MODULE="Results"

TICK_SECONDS=20
FREE_KB_FLOOR=$((1500 * 1024)) # ground rule: stop below ~1.5GB free on /

# --- args: declarations to export, optional --module override -----------------
DECLARS=()
while [ $# -gt 0 ]; do
  case "$1" in
  --module)
    MODULE="${2:?--module needs a value}"
    shift 2
    ;;
  *)
    DECLARS+=("$1")
    shift
    ;;
  esac
done
if [ "${#DECLARS[@]}" -eq 0 ]; then
  echo "usage: $0 <decl> [<decl>...] [--module <Name>]" >&2
  exit 2
fi

# Slug: first declaration, plus _and_N more when several are requested.
SLUG="${DECLARS[0]}"
[ "${#DECLARS[@]}" -gt 1 ] && SLUG="${SLUG}_and_$(( ${#DECLARS[@]} - 1 ))_more"

OUT="$OUT_DIR/$SLUG.export"
STDERR_LOG="$OUT_DIR/$SLUG.stderr.log"
MON_LOG="$OUT_DIR/$SLUG.monitor.log"
DONE="$OUT_DIR/$SLUG.done"

rm -f "$OUT" "$STDERR_LOG" "$MON_LOG" "$DONE"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$MON_LOG"; }
disk_line() { df -k / | tail -1; }

log "START module=$MODULE declars=${DECLARS[*]}"
log "START cmd: cd $TARGET && lake env $EXPORT_BIN $MODULE -- ${DECLARS[*]} > $OUT"
log "START disk: $(disk_line)"
log "START swap: $(sysctl -n vm.swapusage)"

cd "$TARGET" || {
  log "ABORT could not cd $TARGET"
  printf 'rc=1\nkilled=0\nreason=no-target-dir\n' >"$DONE"
  exit 1
}

lake env "$EXPORT_BIN" "$MODULE" -- "${DECLARS[@]}" >"$OUT" 2>"$STDERR_LOG" &
WRAPPER=$!

KILLED=0
START_EPOCH=$(date +%s)
while kill -0 "$WRAPPER" 2>/dev/null; do
  sleep "$TICK_SECONDS"
  kill -0 "$WRAPPER" 2>/dev/null || break
  FREE=$(df -k / | tail -1 | awk '{print $4}')
  [ -n "$FREE" ] || FREE=0
  SZ=$(stat -f%z "$OUT" 2>/dev/null)
  [ -n "$SZ" ] || SZ=0
  SB=$(ps -o rss= -p "$WRAPPER" 2>/dev/null | tr -d ' ')
  [ -n "$SB" ] || SB=0
  log "tick elapsed=$(( $(date +%s) - START_EPOCH ))s free_kb=$FREE out_bytes=$SZ lake_rss_kb=$SB"
  if [ "$FREE" -lt "$FREE_KB_FLOOR" ]; then
    log "ABORT free_kb=$FREE below floor=$FREE_KB_FLOOR — killing export"
    pkill -f 'lean4export' 2>/dev/null
    kill "$WRAPPER" 2>/dev/null
    KILLED=1
    break
  fi
done

wait "$WRAPPER"
RC=$?
ELAPSED=$(( $(date +%s) - START_EPOCH ))
SZ=$(stat -f%z "$OUT" 2>/dev/null)
[ -n "$SZ" ] || SZ=0
log "END rc=$RC killed=$KILLED elapsed=${ELAPSED}s out_bytes=$SZ"
log "END disk: $(disk_line)"
log "END swap: $(sysctl -n vm.swapusage)"
log "END stderr_tail: $(tail -c 400 "$STDERR_LOG" 2>/dev/null | tr '\n' ' ')"
printf 'rc=%s\nkilled=%s\nelapsed_s=%s\nout_bytes=%s\n' "$RC" "$KILLED" "$ELAPSED" "$SZ" >"$DONE"
