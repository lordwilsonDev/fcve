#!/usr/bin/env bash
# Phase 18 — independent checker driver.
#
# For each declaration: export its dependency closure from the (read-only) target
# repo with lean4export, then independently type-check the export with nanoda_bin
# (a Rust external checker — not Lean's own kernel).
#
# Usage (must run detached from the agent's shell; see Phase 18 notes):
#   bash scripts/phase18-independent-check.sh <decl> [<decl>...]
#
# Guards per export (both abort the export, and neither is a substitute for
# checking the monitor log afterwards — see receipts/correction-ledger.md):
#   * free disk on / below FREE_KB_FLOOR   -> abort, reason=disk-floor
#   * export output flat for STALL_TICKS   -> abort, reason=stalled-no-output
#   * wall clock above MAX_SECONDS         -> abort, reason=time-cap
set -u

TARGET="$HOME/ico-collatz/targets/eliahou-collatz-bounds"
EXPORT_BIN="$HOME/ico-collatz/targets/lean4export/.lake/build/bin/lean4export"
NANODA_DIR="$HOME/ico-collatz/experiments/independent-checker/nanoda_lib"
NANODA_BIN="$NANODA_DIR/target/release/nanoda_bin"
OUT_DIR="$HOME/ico-collatz/experiments/independent-checker"
SUMMARY="$OUT_DIR/phase18-results.tsv"
MODULE="Results"

TICK_SECONDS=20
STALL_TICKS=15               # 300 s of zero output growth => pathological
MAX_SECONDS=900
FREE_KB_FLOOR=$((1500 * 1024))

[ -x "$EXPORT_BIN" ] || { echo "missing exporter: $EXPORT_BIN" >&2; exit 1; }
[ -x "$NANODA_BIN" ] || { echo "missing checker:  $NANODA_BIN" >&2; exit 1; }

[ -f "$SUMMARY" ] || printf 'decl\tstatus\tcloser\tseconds\texport_bytes\tnanoda_exit\tnanoda_decls\treason\n' >"$SUMMARY"

run_export() { # $1 = decl, $2 = out path, $3 = err path, $4 = mon path
  local decl="$1" out="$2" err="$3" mon="$4"
  local free sz last_sz flat_ticks start_epoch reason="" killed=0
  : >"$mon"
  {
    printf '%s START decl=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$decl"
    printf '%s START cmd: cd %s && lake env %s %s -- %s > %s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$TARGET" "$EXPORT_BIN" "$MODULE" "$decl" "$out"
    printf '%s START disk: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(df -k / | tail -1)"
  } >>"$mon"

  ( cd "$TARGET" && exec lake env "$EXPORT_BIN" "$MODULE" -- "$decl" ) >"$out" 2>"$err" &
  local pid=$!
  start_epoch=$(date +%s)
  last_sz=-1
  flat_ticks=0

  while kill -0 "$pid" 2>/dev/null; do
    sleep "$TICK_SECONDS"
    kill -0 "$pid" 2>/dev/null || break
    free=$(df -k / | tail -1 | awk '{print $4}')
    [ -n "$free" ] || free=0
    sz=$(stat -f%z "$out" 2>/dev/null)
    [ -n "$sz" ] || sz=0
    if [ "$sz" -eq "$last_sz" ]; then
      flat_ticks=$((flat_ticks + 1))
    else
      flat_ticks=0
      last_sz=$sz
    fi
    printf '%s tick t=%ss free_kb=%s out_bytes=%s flat_ticks=%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(( $(date +%s) - start_epoch ))" \
      "$free" "$sz" "$flat_ticks" >>"$mon"

    if [ "$free" -lt "$FREE_KB_FLOOR" ]; then
      reason="disk-floor"; killed=1
    elif [ "$(date +%s)" -ge "$((start_epoch + MAX_SECONDS))" ]; then
      reason="time-cap"; killed=1
    elif [ "$sz" -gt 0 ] && [ "$flat_ticks" -ge "$STALL_TICKS" ]; then
      # Only a stream that has already started emitting can be "stalled".
      # Before the first byte the process is legitimately inside the environment
      # load, which can take minutes under memory pressure; that case is bounded
      # by MAX_SECONDS instead, so that a guard-induced abort can never be
      # mistaken for evidence that the export stalled.
      reason="stalled-no-output"; killed=1
    fi

    if [ "$killed" -eq 1 ]; then
      printf '%s ABORT reason=%s (free_kb=%s out_bytes=%s)\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$reason" "$free" "$sz" >>"$mon"
      pkill -f 'lean4export' 2>/dev/null
      kill "$pid" 2>/dev/null
      break
    fi
  done

  wait "$pid"
  local rc=$?
  local secs=$(( $(date +%s) - start_epoch ))
  sz=$(stat -f%z "$out" 2>/dev/null); [ -n "$sz" ] || sz=0
  # A complete export ends on a newline-terminated JSON object.
  local tail_ch
  tail_ch=$(tail -c1 "$out" 2>/dev/null | od -An -c | tr -d ' ')
  printf '%s END rc=%s killed=%s reason=%s secs=%s out_bytes=%s last_byte=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$rc" "$killed" "${reason:-none}" "$secs" "$sz" "$tail_ch" >>"$mon"
  EXPORT_RC=$rc
  EXPORT_SECS=$secs
  EXPORT_BYTES=$sz
  EXPORT_REASON="${reason:-none}"
  EXPORT_COMPLETE=0
  [ "$rc" -eq 0 ] && [ "$tail_ch" = '\n' ] && EXPORT_COMPLETE=1
}

for DECL in "$@"; do
  OUT="$OUT_DIR/$DECL.export"
  ERR="$OUT_DIR/$DECL.stderr.log"
  MON="$OUT_DIR/$DECL.monitor.log"
  CFG="$OUT_DIR/nanoda-config-$DECL.json"
  NSTDOUT="$OUT_DIR/$DECL.nanoda.stdout.txt"
  NSTDERR="$OUT_DIR/$DECL.nanoda.stderr.txt"

  rm -f "$OUT" "$ERR" "$MON" "$CFG" "$NSTDOUT" "$NSTDERR"
  run_export "$DECL" "$OUT" "$ERR" "$MON"

  if [ "$EXPORT_COMPLETE" -ne 1 ]; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$DECL" BLOCKED export \
      "$EXPORT_SECS" "$EXPORT_BYTES" - - "$EXPORT_REASON/rc=$EXPORT_RC" >>"$SUMMARY"
    continue
  fi

  # The requested declaration must actually be present before we claim a check.
  if ! grep -qF "$DECL" "$OUT"; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$DECL" BLOCKED export \
      "$EXPORT_SECS" "$EXPORT_BYTES" - - decl-not-in-export >>"$SUMMARY"
    continue
  fi

  python3 - "$CFG" "$OUT" "$DECL" <<'PY'
import json, sys
cfg, export, decl = sys.argv[1], sys.argv[2], sys.argv[3]
json.dump({
    "export_file_path": export,
    "use_stdin": False,
    "permitted_axioms": ["propext", "Classical.choice", "Quot.sound"],
    "unpermitted_axiom_hard_error": False,
    "nat_extension": True,
    "string_extension": True,
    "print_success_message": True,
    "print_axioms": True,
    "pp_declars": [decl],
    "pp_to_stdout": True,
}, open(cfg, "w"), indent=2)
PY

  ( cd "$NANODA_DIR" && exec "$NANODA_BIN" "$CFG" ) >"$NSTDOUT" 2>"$NSTDERR"
  NRC=$?
  CHECKED=$(grep -o 'Checked [0-9]* declarations' "$NSTDOUT" | grep -o '[0-9]*' | head -1)
  [ -n "$CHECKED" ] || CHECKED="-"
  if [ "$NRC" -eq 0 ] && grep -q 'Checked [0-9]* declarations with no errors' "$NSTDOUT"; then
    STATUS=PASS
  else
    STATUS=FAIL
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$DECL" "$STATUS" nanoda \
    "$EXPORT_SECS" "$EXPORT_BYTES" "$NRC" "$CHECKED" - >>"$SUMMARY"
done

echo "--- phase18 results ---"
cat "$SUMMARY"
