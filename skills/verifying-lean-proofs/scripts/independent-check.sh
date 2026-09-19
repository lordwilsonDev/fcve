#!/usr/bin/env bash
# Independent-checker driver, generalized from the eliahou-collatz-bounds audit.
#
# For each declaration: export its dependency closure from a Lean project with
# lean4export, then independently type-check the export with nanoda_bin (a
# separate Rust implementation — not Lean's own kernel). This is what upgrades
# "the Lean kernel accepted it" to "a second, differently-implemented checker
# also accepted it" — the only way to address a known Lean-kernel-version
# vulnerability class (see SKILL.md's threat model section) without bumping
# the target's own pinned toolchain.
#
# Usage:
#   independent-check.sh --target DIR --module MODULE \
#     --export-bin PATH --nanoda-bin PATH [--out DIR] [--axioms a,b,c] \
#     DECL [DECL...]
#
# MUST be run in a way that survives this shell exiting if it will outlive a
# single agent turn — e.g. `setsid bash independent-check.sh ... &` or a
# Python subprocess.Popen(..., start_new_session=True). A plain `nohup ... &`
# from an agent-invoked shell gets reaped when that invocation returns (see
# SKILL.md's "Mistakes already made" table) — this is not hypothetical, it
# was observed directly while building this script.
#
# Guards per export (all abort just that export, not the whole run):
#   * free disk at/below FREE_KB_FLOOR   -> abort, reason=disk-floor
#   * export output flat for STALL_TICKS -> abort, reason=stalled-no-output
#   * wall clock above MAX_SECONDS       -> abort, reason=time-cap
# A flat *zero* output is NOT treated as stalled — environment loading can
# legitimately take minutes before the first byte. Only a stream that has
# already started emitting and then stops is "stalled".
set -u
# GNU stat first: on Linux `stat -f` means filesystem status, not size. (Linux path untested here.)
fsize() { stat -c%s "$1" 2>/dev/null || stat -f%z "$1" 2>/dev/null; }

TARGET="" MODULE="" EXPORT_BIN="" NANODA_BIN="" OUT_DIR="./independent-check-out"
AXIOMS="propext,Classical.choice,Quot.sound"
TICK_SECONDS=20
STALL_TICKS=${STALL_TICKS:-15}   # x TICK_SECONDS of flat NON-ZERO output = stalled (override via env)
DELETE_EXPORTS=0
MAX_SECONDS=900
FREE_KB_FLOOR=$((1500 * 1024))

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --module) MODULE="$2"; shift 2 ;;
    --export-bin) EXPORT_BIN="$2"; shift 2 ;;
    --nanoda-bin) NANODA_BIN="$2"; shift 2 ;;
    --out) OUT_DIR="$2"; shift 2 ;;
    --axioms) AXIOMS="$2"; shift 2 ;;
    --delete-exports) DELETE_EXPORTS=1; shift ;;
    --) shift; break ;;
    -*) echo "unknown flag: $1" >&2; exit 1 ;;
    *) break ;;
  esac
done

[ -n "$TARGET" ] && [ -n "$MODULE" ] && [ -n "$EXPORT_BIN" ] && [ -n "$NANODA_BIN" ] && [ $# -gt 0 ] || {
  echo "usage: independent-check.sh --target DIR --module MODULE --export-bin PATH --nanoda-bin PATH [--out DIR] [--axioms a,b,c] DECL [DECL...]" >&2
  exit 1
}
[ -x "$EXPORT_BIN" ] || { echo "missing exporter: $EXPORT_BIN (run setup-independent-checker.sh first)" >&2; exit 1; }
[ -x "$NANODA_BIN" ] || { echo "missing checker:  $NANODA_BIN (run setup-independent-checker.sh first)" >&2; exit 1; }
NANODA_DIR=$(dirname "$(dirname "$NANODA_BIN")")

mkdir -p "$OUT_DIR"
# Absolute path: the checker is launched after a `cd` (below); a relative --out made its config path
# unresolvable ("failed to open configuration file") -- BUG-003 in BUGS.md.
OUT_DIR=$(cd "$OUT_DIR" && pwd)
SUMMARY="$OUT_DIR/results.tsv"
[ -f "$SUMMARY" ] || printf 'decl\tstatus\tcloser\tseconds\texport_bytes\tnanoda_exit\tnanoda_decls\treason\n' >"$SUMMARY"

IFS=',' read -r -a AXIOM_ARR <<< "$AXIOMS"

# Record exactly which tool binaries produced these verdicts (patched builds must be identifiable).
{ printf 'exporter\t%s\t%s\n' "$EXPORT_BIN" "$(shasum -a 256 "$EXPORT_BIN" | cut -d' ' -f1)"
  printf 'nanoda\t%s\t%s\n' "$NANODA_BIN" "$(shasum -a 256 "$NANODA_BIN" | cut -d' ' -f1)"
  for b in "$EXPORT_BIN" "$NANODA_BIN"; do
    d=$(git -C "$(dirname "$b")" rev-parse --show-toplevel 2>/dev/null) || continue
    printf 'git\t%s\t%s\tdirty_files=%s\n' "$d" "$(git -C "$d" rev-parse HEAD)" "$(git -C "$d" status --short | wc -l | tr -d ' ')"; done
} >"$OUT_DIR/tools.tsv" 2>/dev/null

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
    free=$(df -k / | tail -1 | awk '{print $4}'); [ -n "$free" ] || free=0
    sz=$(fsize "$out"); [ -n "$sz" ] || sz=0
    if [ "$sz" -eq "$last_sz" ]; then flat_ticks=$((flat_ticks + 1)); else flat_ticks=0; last_sz=$sz; fi
    printf '%s tick t=%ss free_kb=%s out_bytes=%s flat_ticks=%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(( $(date +%s) - start_epoch ))" "$free" "$sz" "$flat_ticks" >>"$mon"

    if [ "$free" -lt "$FREE_KB_FLOOR" ]; then reason="disk-floor"; killed=1
    elif [ "$(date +%s)" -ge "$((start_epoch + MAX_SECONDS))" ]; then reason="time-cap"; killed=1
    elif [ "$sz" -gt 0 ] && [ "$flat_ticks" -ge "$STALL_TICKS" ]; then reason="stalled-no-output"; killed=1
    fi
    if [ "$killed" -eq 1 ]; then
      printf '%s ABORT reason=%s (free_kb=%s out_bytes=%s)\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$reason" "$free" "$sz" >>"$mon"
      # A stall is a SYMPTOM, not a diagnosis. Sample the stuck process before killing it so the cause can be read,
      # not guessed (BUG-002: a "memoization" guess stood for a week; the real cause was visible in one sample).
      if [ "$reason" = "stalled-no-output" ] && command -v sample >/dev/null 2>&1; then
        sample "$(pgrep -n -f "$(basename "$EXPORT_BIN")")" 3 -file "${out%.export}.stall-sample.txt" >/dev/null 2>&1 \
          && printf '%s SAMPLE saved: %s (read the top of stack; huge nat literals show Nat.repr/toDigits + gmpn_divrem)\n' \
               "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${out%.export}.stall-sample.txt" >>"$mon"
      fi
      pkill -f "$(basename "$EXPORT_BIN")" 2>/dev/null
      kill "$pid" 2>/dev/null
      break
    fi
  done

  wait "$pid"; local rc=$?
  local secs=$(( $(date +%s) - start_epoch ))
  sz=$(fsize "$out"); [ -n "$sz" ] || sz=0
  local tail_ch; tail_ch=$(tail -c1 "$out" 2>/dev/null | od -An -c | tr -d ' ')
  printf '%s END rc=%s killed=%s reason=%s secs=%s out_bytes=%s last_byte=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$rc" "$killed" "${reason:-none}" "$secs" "$sz" "$tail_ch" >>"$mon"
  EXPORT_RC=$rc; EXPORT_SECS=$secs; EXPORT_BYTES=$sz; EXPORT_REASON="${reason:-none}"
  EXPORT_COMPLETE=0; [ "$rc" -eq 0 ] && [ "$tail_ch" = '\n' ] && EXPORT_COMPLETE=1
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
    [ "$DELETE_EXPORTS" = 1 ] && rm -f "$OUT"
    continue
  fi
  if ! grep -qF "$DECL" "$OUT"; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$DECL" BLOCKED export \
      "$EXPORT_SECS" "$EXPORT_BYTES" - - decl-not-in-export >>"$SUMMARY"
    continue
  fi

  python3 - "$CFG" "$OUT" "$DECL" "$AXIOMS" <<'PY'
import json, sys
cfg, export, decl, axioms = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
json.dump({
    "export_file_path": export, "use_stdin": False,
    "permitted_axioms": axioms, "unpermitted_axiom_hard_error": False,
    "nat_extension": True, "string_extension": True,
    "print_success_message": True, "print_axioms": True,
    "pp_declars": [decl], "pp_to_stdout": True,
}, open(cfg, "w"), indent=2)
PY

  # Huge decimal nat literals make BOTH lean4export (printing) and nanoda (parsing) quadratic unless patched.
  MAXLIT=$(python3 "$(dirname "$0")/export-literal-scan.py" "$OUT" 2>/dev/null | head -1)
  printf '%s LITERALS %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${MAXLIT:-scan-failed}" >>"$MON"

  ( cd "$NANODA_DIR" && exec "$NANODA_BIN" "$CFG" ) >"$NSTDOUT" 2>"$NSTDERR"
  NRC=$?
  CHECKED=$(grep -o 'Checked [0-9]* declarations' "$NSTDOUT" | grep -o '[0-9]*' | head -1)
  [ -n "$CHECKED" ] || CHECKED="-"
  # PASS needs exit 0 AND "Checked N declarations with no errors" AND the target printed AND its axioms listed.
  # FAIL = the checker ran and rejected the proof (panic / def_eq failure). TOOL_ERROR = the checker never ran properly
  # (bad config path, unreadable export): NOT evidence about the proof -- never report it as a failed proof.
  STATUS=FAIL
  if [ "$NRC" -ne 0 ] && grep -q '^Error:' "$NSTDERR" 2>/dev/null; then STATUS=TOOL_ERROR
  elif [ "$NRC" -eq 0 ] && grep -q 'Checked [0-9]* declarations with no errors' "$NSTDOUT" && grep -qF "$DECL" "$NSTDOUT"; then STATUS=PASS
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$DECL" "$STATUS" nanoda \
    "$EXPORT_SECS" "$EXPORT_BYTES" "$NRC" "$CHECKED" - >>"$SUMMARY"
  if [ "$DELETE_EXPORTS" = 1 ] && [ -f "$OUT" ]; then
    printf '%s EXPORT_SHA256 %s bytes=%s (file deleted after check: --delete-exports)\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(shasum -a 256 "$OUT" | cut -d' ' -f1)" "$(fsize "$OUT")" >>"$MON"
    rm -f "$OUT"
  fi
done

echo "--- results ---"
cat "$SUMMARY"
