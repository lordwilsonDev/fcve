#!/usr/bin/env bash
# smoke-test.sh -- prove the reconstructed environment can execute the core FCVE workflow, fast.
#
#   repository -> skill -> dependencies -> Lean -> build infrastructure -> verification scripts -> audit machinery
#
# It runs a REAL end-to-end audit of a tiny Mathlib-free Lean fixture (with the independent checker), checks that a fixture with `sorry`
# is REJECTED, and checks that a full disk is reported as BLOCKED/UNRESOLVED rather than a proof failure. Typically a couple of minutes.
#
# It prints "SMOKE TEST PASSED" only if EVERY required condition passes. That is a statement about the environment, not about any theorem:
# a passed smoke test verifies nothing about your proof.
# Exit: 0 passed | 1 at least one required condition failed | 2 setup has not been run (run scripts/setup.sh first)
#
# Usage: scripts/smoke-test.sh [--work DIR] [--out DIR] [--skip-audit]
set -u
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"
WORK="${FCVE_WORK:-$FCVE_WORK_DEFAULT}"; OUT=""; SKIP_AUDIT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --work) WORK="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --skip-audit) SKIP_AUDIT=1; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done
[ -n "$OUT" ] || OUT="$WORK/smoke"; mkdir -p "$OUT" || exit 1
NFAIL=0; T0=$(date +%s)
step_ok()   { printf '[ OK   ] %s\n' "$1"; }
step_fail() { printf '[ FAIL ] %s -- %s\n' "$1" "$2"; NFAIL=$((NFAIL+1)); }
row_status() { awk -F'\t' -v n="$2" '$1==n {print $2}' "$1" 2>/dev/null; }   # row_status <rows.tsv> <n>
need() { if eval "$2"; then step_ok "$1"; else step_fail "$1" "${3:-condition not met}"; fi; }

echo "FCVE smoke test -- $(date -u +%Y-%m-%dT%H:%M:%SZ) -- repo $FCVE_ROOT"
[ -f "$WORK/setup-record.json" ] || { echo "setup has not been run (no $WORK/setup-record.json). Run scripts/setup.sh, then retry."; echo "SMOKE TEST NOT RUN"; exit 2; }

# 1. repository + skill + dependencies + tool patches (the doctor is the single source for these)
bash "$FCVE_ROOT/scripts/doctor.sh" --work "$WORK" --json "$OUT/doctor.json" >"$OUT/doctor.txt" 2>&1; DRC=$?
need "doctor: environment READY (no FAIL, no UNRESOLVED; see $OUT/doctor.txt)" "[ $DRC -eq 0 ]" "doctor exit $DRC: $(grep -E '^\[(FAIL|UNRESOLVED)' "$OUT/doctor.txt" | head -3 | tr '\n' ';' | cut -c1-200)"

# 2. every shell script parses (syntax only -- `bash -n` is NOT a test; the runtime steps below are)
SYN=0; while IFS= read -r f; do bash -n "$f" 2>"$OUT/syntax.err" || { SYN=1; echo "   syntax error in $f: $(head -1 "$OUT/syntax.err")"; }; done < <(cd "$FCVE_ROOT" && find scripts skills -name '*.sh' -print | sed "s#^#$FCVE_ROOT/#")
need "bash -n: every scripts/ and skills/ shell script parses" "[ $SYN -eq 0 ]"

# 3. the verification skill is discoverable from the repository
need "skill: skills/verifying-lean-proofs/SKILL.md present" "[ -f '$FCVE_ROOT/skills/verifying-lean-proofs/SKILL.md' ]"
need "skill: CLAUDE.md tells Claude to read it" "grep -q 'skills/verifying-lean-proofs/SKILL.md' '$FCVE_ROOT/CLAUDE.md'" "CLAUDE.md missing or does not name the skill"

# 4. the engine's own fast tests (pure Python; no Lean needed)
for t in evidence claims graph receipt limits; do
  ( cd "$FCVE_ROOT" && python3 "tests/test_fcve_$t.py" >"$OUT/test_$t.log" 2>&1 ); need "engine test suite: $t" "[ $? -eq 0 ]" "see $OUT/test_$t.log"
done

# 5. evidence integrity of the delivered packages: hash chain, order, receipt currency, manifest checksums
for D in VCE-001-rev-s VCE-002-rev-s; do
  P="$FCVE_ROOT/deliverables/$D"
  need "deliverable $D: ledger chain intact + canonical order" "python3 '$FCVE_ROOT/scripts/fcve.py' verify '$P/event-ledger.jsonl' >'$OUT/verify-$D.log' 2>&1" "see $OUT/verify-$D.log"
  need "deliverable $D: receipt current with the ledger" "python3 '$FCVE_ROOT/scripts/fcve.py' receipt-check '$P/event-ledger.jsonl' '$P/receipt.json' >'$OUT/receipt-$D.log' 2>&1" "see $OUT/receipt-$D.log"
  need "deliverable $D: MANIFEST.sha256 verifies" "(cd '$P' && shasum -a 256 -c MANIFEST.sha256 >'$OUT/manifest-$D.log' 2>&1)" "see $OUT/manifest-$D.log"
done

# 6-8. the audit machinery, for real, on the tiny fixtures
if [ "$SKIP_AUDIT" = 1 ]; then echo "[ SKIP ] audit machinery (--skip-audit): a passed smoke test WITHOUT this step is not a passed smoke test"; NFAIL=$((NFAIL+1))
else
  OKD="$FCVE_ROOT/tests/fixtures/mini-lean-ok"; BADD="$FCVE_ROOT/tests/fixtures/mini-lean-bad"
  rm -rf "$OUT/audit-ok" "$OUT/audit-bad" "$OUT/audit-disk"
  bash "$FCVE_ROOT/scripts/audit.sh" "$OKD" --module Mini --decl mini_add --decl mini_comm --fast-literals no --out "$OUT/audit-ok" --work "$WORK" >"$OUT/audit-ok.stdout" 2>&1; ARC=$?
  A="$OUT/audit-ok/AUDIT.md"
  need "audit (good fixture): finished and wrote AUDIT.md" "[ $ARC -eq 0 ] && [ -f '$A' ]" "exit $ARC; see $OUT/audit-ok.stdout"
  RT="$OUT/audit-ok/rows.tsv"
  need "audit (good fixture): rows 1,2 PASS/PARTIAL and rows 4,5,6 PASS" '[ "$(row_status "$RT" 1)" != FAIL ] && [ "$(row_status "$RT" 2)" = PASS ] && [ "$(row_status "$RT" 4)" = PASS ] && [ "$(row_status "$RT" 5)" = PASS ] && [ "$(row_status "$RT" 6)" = PASS ]' "see $RT"
  need "audit (good fixture): independent check (row 10) PASS with upstream tools" '[ "$(row_status "$RT" 10)" = PASS ]' "row 10 = $(row_status "$RT" 10); see $OUT/audit-ok/independent-check.log"
  need "audit (good fixture): verdict is PROVISIONAL, never TRUSTED" "grep -q '^## Verdict: PROVISIONAL' '$A' && ! grep -q '^## Verdict: TRUSTED' '$A'"
  need "audit (good fixture): unresolved gates stay visible (rows 7 and 9)" "grep -q '| 7 | Semantic correspondence | \*\*NEEDS HUMAN\*\*' '$A' && grep -q '| 9 | Kernel vulnerability exposure | \*\*UNRESOLVED\*\*' '$A'"
  # it must be able to FAIL: a proof containing sorry is rejected
  bash "$FCVE_ROOT/scripts/audit.sh" "$BADD" --module Mini --decl bad_sorry --skip-independent --out "$OUT/audit-bad" --work "$WORK" >"$OUT/audit-bad.stdout" 2>&1
  RB="$OUT/audit-bad/rows.tsv"
  need "audit (sorry fixture): REJECTED, rows 4 and 6 FAIL" 'grep -q "^## Verdict: REJECTED" "$OUT/audit-bad/AUDIT.md" && [ "$(row_status "$RB" 4)" = FAIL ] && [ "$(row_status "$RB" 6)" = FAIL ]' "the audit did not reject a proof containing sorry (see $OUT/audit-bad.stdout)"
  # a full disk is BLOCKED/UNRESOLVED, not a rejection
  FCVE_FAKE_FREE_KB=1000 bash "$FCVE_ROOT/scripts/audit.sh" "$OKD" --module Mini --decl mini_add --skip-independent --out "$OUT/audit-disk" --work "$WORK" >"$OUT/audit-disk.stdout" 2>&1; DKRC=$?
  need "audit (simulated full disk): BLOCKED/UNRESOLVED (exit 3), not REJECTED" "[ $DKRC -eq 3 ] && grep -q 'Verdict: UNRESOLVED' '$OUT/audit-disk/AUDIT.md' && ! grep -q 'REJECTED' '$OUT/audit-disk/AUDIT.md'" "exit $DKRC"
fi

ELAPSED=$(( $(date +%s) - T0 ))
echo
echo "smoke test took ${ELAPSED}s; details in $OUT"
echo "NOTE: this checks the ENVIRONMENT and the audit machinery. It verifies nothing about any theorem you care about."
if [ "$NFAIL" -eq 0 ]; then echo "SMOKE TEST PASSED"; exit 0; else echo "SMOKE TEST FAILED ($NFAIL required condition(s) did not hold)"; exit 1; fi
