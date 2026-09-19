#!/usr/bin/env bash
# run-tests.sh -- two tiers, kept distinct on purpose:
#   1. SYNTAX validation:  `bash -n` on every shell script + py_compile on every Python module.  This is NOT a test of behavior.
#   2. RUNTIME tests:      tests/test_bootstrap.py (failure injection, regression tests, audit ceiling) and the fast FCVE engine suites.
# Default is the fast tier (~1-2 min, needs Lean v4.28.0 and scripts/setup.sh to have run for some tests; a test that cannot run is
# reported SKIPPED, never passed). --full adds the slow tier (the full smoke test, patched-tool equivalence).
# Exit: 0 all ran and passed | 1 a syntax or runtime failure
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT" || exit 1
FULL=0; [ "${1:-}" = "--full" ] && FULL=1
RC=0
echo "== 1. syntax validation (bash -n / py_compile) -- parses only; proves nothing about behavior =="
while IFS= read -r f; do bash -n "$f" || { echo "SYNTAX ERROR: $f"; RC=1; }; done < <(find scripts skills -name '*.sh' | sort)
python3 -m py_compile scripts/*.py || RC=1
[ "$RC" = 0 ] && echo "syntax OK ($(find scripts skills -name '*.sh' | wc -l | tr -d ' ') shell scripts, $(ls scripts/*.py | wc -l | tr -d ' ') python modules)"
echo
echo "== 2. runtime tests =="
if [ "$FULL" = 1 ]; then export FCVE_TEST_FULL=1; fi
python3 tests/test_bootstrap.py || RC=1
for t in evidence claims graph receipt limits; do printf 'engine suite %-9s ' "$t"; python3 "tests/test_fcve_$t.py" 2>&1 | tail -1; [ "${PIPESTATUS[0]}" = 0 ] || RC=1; done
echo
[ "$RC" = 0 ] && echo "RUN-TESTS: all executed tests passed (skipped tests are listed above as skipped, not passed)" || echo "RUN-TESTS: FAILURES (see above)"
exit $RC
