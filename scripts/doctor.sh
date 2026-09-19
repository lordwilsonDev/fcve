#!/usr/bin/env bash
# doctor.sh -- inspect the machine and the repository and say, per item, PASS / WARN / FAIL / UNRESOLVED.
#
#   PASS        the item was checked and matches what FCVE needs
#   WARN        it works or may work, but differs from the validated environment (e.g. a different macOS)
#   FAIL        a requirement is missing or wrong; the fix is printed
#   UNRESOLVED  it could not be determined. Unknown is never reported as PASS.
#
# Exit code: 0 = no FAIL and no UNRESOLVED; 1 = at least one FAIL; 3 = no FAIL but at least one UNRESOLVED.
# It changes nothing on the machine and never installs anything.
#
# Usage: scripts/doctor.sh [--work DIR] [--json FILE] [--root DIR]
#   --work  where setup.sh builds the checker tools (default: <repo>/.fcve-work)
#   --json  also write the results as JSON
#   --root  (tests) treat DIR as the repository root, to inject a missing file/skill
set -u
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

WORK="${FCVE_WORK:-$FCVE_WORK_DEFAULT}"; JSON_OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --work) WORK="$2"; shift 2 ;;
    --json) JSON_OUT="$2"; shift 2 ;;
    --root) FCVE_ROOT="$(cd "$2" && pwd)"; MANIFEST="$FCVE_ROOT/manifests/environment.json"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

echo "FCVE doctor -- $(date -u +%Y-%m-%dT%H:%M:%SZ) -- repo $FCVE_ROOT"
echo

# ---- 0. python + manifest (everything else reads the manifest) ------------------------------------------------------
if ! have python3; then
  record FAIL manifest python3 "python3 not found: install Python 3 (needed to read the manifest and run FCVE)"
  echo; echo "DOCTOR: NOT READY (cannot read the manifest without python3)"; exit 1
fi
if [ ! -f "$MANIFEST" ]; then
  record FAIL manifest environment.json "missing $MANIFEST"
  echo; echo "DOCTOR: NOT READY"; exit 1
fi
if ! python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$MANIFEST" 2>/dev/null; then
  record FAIL manifest environment.json "not valid JSON: $MANIFEST"
  echo; echo "DOCTOR: NOT READY"; exit 1
fi
record PASS manifest environment.json "readable ($(mf 'd["validated_on"]'))"

# ---- 1. hardware / OS ------------------------------------------------------------------------------------------------
V_MODEL=$(mf 'd["validated_environment"]["model_identifier"]'); V_ARCH=$(mf 'd["validated_environment"]["architecture"]')
V_RAM=$(mf 'd["validated_environment"]["ram_gib"]'); V_OS=$(mf 'd["validated_environment"]["macos"]'); V_CHIP=$(mf 'd["validated_environment"]["chip"]')
OS_NAME=$(uname -s)
if [ "$OS_NAME" = Darwin ]; then
  MODEL=$(sysctl -n hw.model 2>/dev/null); CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
  RAM_GIB=$(python3 -c "print(round($(sysctl -n hw.memsize 2>/dev/null || echo 0)/1073741824,1))"); OSV=$(sw_vers -productVersion 2>/dev/null)
  if [ "$MODEL" = "$V_MODEL" ]; then record PASS hardware model "$MODEL (Mac mini) = validated"
  elif [ -n "$MODEL" ]; then record WARN hardware model "$MODEL differs from validated $V_MODEL (Mac mini): unvalidated hardware"
  else record UNRESOLVED hardware model "could not read hw.model"; fi
  [ "$CHIP" = "$V_CHIP" ] && record PASS hardware chip "$CHIP" || record WARN hardware chip "${CHIP:-unknown} differs from validated $V_CHIP"
  if python3 -c "import sys; sys.exit(0 if float('$RAM_GIB') >= float('$V_RAM') else 1)"; then record PASS hardware ram "$RAM_GIB GiB (validated $V_RAM GiB)"
  else record WARN hardware ram "$RAM_GIB GiB is below the validated $V_RAM GiB; large exports may swap"; fi
  [ "$OSV" = "$V_OS" ] && record PASS os macos "$OSV = validated" || record WARN os macos "${OSV:-unknown} differs from validated $V_OS: unvalidated"
else
  record WARN os platform "$OS_NAME is not macOS: FCVE is validated on macOS only (some scripts use macOS tools)"
fi
ARCH=$(uname -m); [ "$ARCH" = "$V_ARCH" ] && record PASS os architecture "$ARCH" || record WARN os architecture "$ARCH differs from validated $V_ARCH"
record PASS os shell "bash ${BASH_VERSION%%(*}; login shell ${SHELL:-unknown}"

# ---- 2. dependencies -------------------------------------------------------------------------------------------------
for T in $(python3 -c "import json;print(' '.join(json.load(open('$MANIFEST'))['required_tools']))"); do
  REQ=$(mf "d['required_tools']['$T']['required']"); VAL=$(mf "d['required_tools']['$T']['validated']"); ROLE=$(mf "d['required_tools']['$T']['role']")
  if have "$T"; then
    V=$(tool_version "$T")
    if [ "$VAL" = system ] || [ "$V" = "$VAL" ] || [ "$V" = present ]; then record PASS tool "$T" "${V:-present} ($ROLE)"
    else record WARN tool "$T" "$V differs from validated $VAL ($ROLE)"; fi
  elif [ "$REQ" = True ]; then record FAIL tool "$T" "not found -- required for: $ROLE"
  else record WARN tool "$T" "not found -- optional, needed for: $ROLE"; fi
done
# Lean toolchains (never run `elan run`: it would try to download a missing toolchain)
TOOLCHAINS_OK=0; TAGS=$(python3 -c "import json;print(' '.join(t['tag'] for t in json.load(open('$MANIFEST'))['lean']['toolchains']))")
MISSING_TC=0
for TAG in $TAGS; do
  TCDIR="$HOME/.elan/toolchains/leanprover--lean4---$TAG"
  if [ -x "$TCDIR/bin/lean" ]; then TOOLCHAINS_OK=$((TOOLCHAINS_OK+1)); record PASS lean "toolchain $TAG" "$("$TCDIR/bin/lean" --version 2>/dev/null | cut -c1-70)"
  else MISSING_TC=$((MISSING_TC+1)); record WARN lean "toolchain $TAG" "not installed -- needed only for targets pinned to $TAG (install: scripts/setup.sh --tag $TAG --install-toolchain)"; fi
done
[ "$TOOLCHAINS_OK" -eq 0 ] && record FAIL lean "any toolchain" "none of the validated Lean toolchains ($TAGS) is installed; run scripts/setup.sh --install-toolchain"

# ---- 3. repository ---------------------------------------------------------------------------------------------------
if git -C "$FCVE_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  REV=$(git -C "$FCVE_ROOT" rev-parse HEAD 2>/dev/null); BR=$(git -C "$FCVE_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)
  TAGN=$(git -C "$FCVE_ROOT" describe --tags --exact-match 2>/dev/null || echo none); DIRTY=$(git -C "$FCVE_ROOT" status --porcelain 2>/dev/null | grep -v '^?? ' | wc -l | tr -d ' ')
  if [ -z "$REV" ]; then record UNRESOLVED repo commit "git repository has no commit"; else record PASS repo commit "${REV:0:12} on $BR (tag: $TAGN)"; fi
  [ "$DIRTY" = 0 ] && record PASS repo tree "no modified tracked files" || record WARN repo tree "$DIRTY modified tracked files: results from this tree are not identified by the commit alone"
else record UNRESOLVED repo commit "not a git checkout: no commit identifies this copy"; fi
MISS=0; for F in $(python3 -c "import json;print(' '.join(json.load(open('$MANIFEST'))['expected_files']))"); do [ -e "$FCVE_ROOT/$F" ] || { record FAIL repo "file $F" "missing"; MISS=1; }; done
[ "$MISS" = 0 ] && record PASS repo "expected files" "all present"
MISS=0; for F in $(python3 -c "import json;print(' '.join(json.load(open('$MANIFEST'))['expected_skill_files']))"); do [ -e "$FCVE_ROOT/$F" ] || { record FAIL skill "file $F" "missing: the verification skill is incomplete"; MISS=1; }; done
[ "$MISS" = 0 ] && record PASS skill "expected skill files" "all present (skills/verifying-lean-proofs)"
if [ -e "$FCVE_ROOT/.claude/skills/verifying-lean-proofs/SKILL.md" ]; then record PASS skill "project discovery" ".claude/skills/verifying-lean-proofs resolves to SKILL.md (a Claude Code session opened in this repo finds it)"
else record WARN skill "project discovery" ".claude/skills/verifying-lean-proofs missing or broken: Claude must be told to read skills/verifying-lean-proofs/SKILL.md (see CLAUDE.md)"; fi
if [ -d "$HOME/.claude/skills/verifying-lean-proofs" ]; then
  if diff -rq "$FCVE_ROOT/skills/verifying-lean-proofs" "$HOME/.claude/skills/verifying-lean-proofs" >/dev/null 2>&1; then record PASS skill "user-level copy" "~/.claude/skills copy is identical to the repo copy"
  else record WARN skill "user-level copy" "~/.claude/skills/verifying-lean-proofs differs from the repo copy; the repo copy is the source of truth"; fi
else record PASS skill "user-level copy" "none installed (the repo copy is used)"; fi

# ---- 4. tool patches -------------------------------------------------------------------------------------------------
for I in 0 1; do
  PF=$(mf "d['tool_patches']['patches'][$I]['file']"); PH=$(mf "d['tool_patches']['patches'][$I]['sha256']"); PN=$(mf "d['tool_patches']['patches'][$I]['name']")
  if [ ! -f "$FCVE_ROOT/$PF" ]; then record FAIL patch "$PN" "patch file missing: $PF"
  elif [ "$(sha256_of "$FCVE_ROOT/$PF")" = "$PH" ]; then record PASS patch "$PN" "present, sha256 ${PH:0:12}… = manifest"
  else record FAIL patch "$PN" "sha256 differs from the manifest: the patch was changed; do not use it as validated"; fi
  SK="$FCVE_ROOT/skills/verifying-lean-proofs/patches/$(basename "$PF")"
  if [ -f "$SK" ] && [ "$(sha256_of "$SK")" != "$PH" ]; then record FAIL patch "$PN (skill copy)" "the skill's copy differs from tool-patches/"; fi
done
for TAG in $TAGS; do
  [ -x "$HOME/.elan/toolchains/leanprover--lean4---$TAG/bin/lean" ] || continue
  P="$WORK/lean4export-$TAG"; PP="$WORK/lean4export-$TAG-fastnat"
  if [ -d "$P" ] && [ -f "$P/Export.lean" ]; then
    T=$(mktemp "${TMPDIR:-/tmp}/exp.XXXXXX"); cp "$P/Export.lean" "$T"
    if patch --dry-run -s "$T" <"$FCVE_ROOT/tool-patches/lean4export-fast-natval.diff" >/dev/null 2>&1; then record PASS patch "applies to lean4export $TAG" "dry-run against the pristine checkout: clean"
    else record FAIL patch "applies to lean4export $TAG" "patch does NOT apply to the pristine $TAG checkout"; fi; rm -f "$T"
  else record UNRESOLVED patch "applies to lean4export $TAG" "no pristine checkout in $WORK to test against; run scripts/setup.sh --tag $TAG"; fi
  [ -x "$PP/.lake/build/bin/lean4export" ] && record PASS patch "patched lean4export $TAG" "built" || record WARN patch "patched lean4export $TAG" "not built (optional; only needed for huge-literal proofs): scripts/setup.sh --tag $TAG"
done
if [ -d "$WORK/nanoda_lib" ] && [ -f "$WORK/nanoda_lib/src/parser.rs" ]; then
  T=$(mktemp "${TMPDIR:-/tmp}/parser.XXXXXX"); cp "$WORK/nanoda_lib/src/parser.rs" "$T"
  if patch --dry-run -s "$T" <"$FCVE_ROOT/tool-patches/nanoda-fast-decimal-parse.diff" >/dev/null 2>&1; then record PASS patch "applies to nanoda_lib" "dry-run against the pristine checkout: clean"
  else record FAIL patch "applies to nanoda_lib" "patch does NOT apply to the pristine checkout"; fi; rm -f "$T"
else record UNRESOLVED patch "applies to nanoda_lib" "no pristine checkout in $WORK; run scripts/setup.sh"; fi
[ -x "$WORK/nanoda_lib-fastparse/target/release/nanoda_bin" ] && record PASS patch "patched nanoda_lib" "built" || record WARN patch "patched nanoda_lib" "not built (optional): scripts/setup.sh"
SR="$WORK/setup-record.json"
if [ -f "$SR" ]; then
  PV=$(python3 -c "import json;print(json.load(open('$SR')).get('patch_validation','UNKNOWN'))" 2>/dev/null || echo UNKNOWN)
  [ "$PV" = PASS ] && record PASS patch "validation record" "setup-record.json: equivalence tests passed when the patched tools were built" \
    || record UNRESOLVED patch "validation record" "setup-record.json says patch_validation=$PV"
else record UNRESOLVED patch "validation record" "no setup-record.json: patched-tool validation has not been recorded on this machine"; fi

# ---- 5. checker builds -----------------------------------------------------------------------------------------------
for TAG in $TAGS; do
  [ -x "$HOME/.elan/toolchains/leanprover--lean4---$TAG/bin/lean" ] || continue
  [ -x "$WORK/lean4export-$TAG/.lake/build/bin/lean4export" ] && record PASS checker "lean4export $TAG" "built ($(git -C "$WORK/lean4export-$TAG" rev-parse --short HEAD 2>/dev/null))" \
    || record FAIL checker "lean4export $TAG" "not built: run scripts/setup.sh --tag $TAG"
done
[ -x "$WORK/nanoda_lib/target/release/nanoda_bin" ] && record PASS checker "nanoda_lib" "built ($(git -C "$WORK/nanoda_lib" rev-parse --short HEAD 2>/dev/null))" \
  || record FAIL checker "nanoda_lib" "not built: run scripts/setup.sh"

# ---- 6. storage ------------------------------------------------------------------------------------------------------
mkdir -p "$WORK" 2>/dev/null; FREE=$(free_kb "${WORK}"); [ -n "$FREE" ] || FREE=$(free_kb "$FCVE_ROOT")
HARD=$(mf 'd["measured_requirements"]["disk_gib"]["hard_floor_free"]'); REC=$(mf 'd["measured_requirements"]["disk_gib"]["recommended_free"]')
if [ -z "${FREE:-}" ]; then record UNRESOLVED storage "free space" "could not read free disk"
else
  FREE_G=$(kb_to_gib "$FREE"); [ -n "${FCVE_FAKE_FREE_KB:-}" ] && FREE_G="$FREE_G (SIMULATED via FCVE_FAKE_FREE_KB)"
  NEED=$(python3 - "$MANIFEST" "$MISSING_TC" "$WORK" "$TAGS" <<'PY'
import json,os,sys
d=json.load(open(sys.argv[1]))["measured_requirements"]["disk_gib"]; miss=int(sys.argv[2]); work=sys.argv[3]; tags=sys.argv[4].split()
need = miss*d["per_lean_toolchain"] if False else 0.0   # missing toolchains are only installed on request, counted separately
for t in tags:
    if not os.path.exists(f"{work}/lean4export-{t}/.lake/build/bin/lean4export"): need += d["lean4export_build_per_tag"] + d["patched_copies_extra"]
if not os.path.exists(f"{work}/nanoda_lib/target/release/nanoda_bin"): need += d["nanoda_build"] + d["patched_copies_extra"]
need += d["one_export_max"]
print(round(need,2))
PY
)
  if python3 -c "import sys; sys.exit(0 if $FREE/1048576 >= $HARD else 1)"; then
    if python3 -c "import sys; sys.exit(0 if $FREE/1048576 >= $REC else 1)"; then record PASS storage "free space" "$FREE_G GiB free (recommended >= $REC, hard floor $HARD; measured, not universal)"
    else record WARN storage "free space" "$FREE_G GiB free: above the hard floor ($HARD) but below the recommended $REC GiB; large exports may be aborted (reported as UNRESOLVED, not a failed proof)"; fi
    if python3 -c "import sys; sys.exit(0 if $FREE/1048576 - $NEED >= $HARD else 1)"; then record PASS storage "room to finish setup" "needs ~$NEED GiB for checker builds + one export; stays above the $HARD GiB floor"
    else record FAIL storage "room to finish setup" "needs ~$NEED GiB for checker builds + one export but only $FREE_G GiB is free above a $HARD GiB floor: free disk first (nothing is deleted for you)"; fi
  else record FAIL storage "free space" "$FREE_G GiB free is BELOW the hard floor of $HARD GiB: audits will be blocked (UNRESOLVED), not judged"; fi
  record PASS storage "measured needs" "per Lean toolchain ~$(mf 'd["measured_requirements"]["disk_gib"]["per_lean_toolchain"]') GiB; a new Mathlib target ~$(mf 'd["measured_requirements"]["disk_gib"]["mathlib_cache_new_target"]') GiB; one export $(mf 'd["measured_requirements"]["disk_gib"]["one_export_min"]')-$(mf 'd["measured_requirements"]["disk_gib"]["one_export_max"]') GiB (measured on the validated Mac mini)"
fi

# ---- summary ---------------------------------------------------------------------------------------------------------
echo
echo "summary: $N_PASS PASS, $N_WARN WARN, $N_FAIL FAIL, $N_UNRESOLVED UNRESOLVED"
if [ -n "$JSON_OUT" ]; then
  python3 - "$RESULTS_FILE" "$JSON_OUT" "$FCVE_ROOT" <<'PY'
import json,sys,datetime
rows=[dict(zip(("level","category","name","detail"),l.rstrip("\n").split("\t",3))) for l in open(sys.argv[1])]
json.dump({"generated_utc":datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),"repo":sys.argv[3],"results":rows},open(sys.argv[2],"w"),indent=2)
PY
  echo "wrote $JSON_OUT"
fi
if [ "$N_FAIL" -gt 0 ]; then echo "DOCTOR: NOT READY ($N_FAIL FAIL, $N_UNRESOLVED UNRESOLVED) -- fix the FAIL lines above, then run scripts/setup.sh if they name it"; exit 1
elif [ "$N_UNRESOLVED" -gt 0 ]; then echo "DOCTOR: NOT FULLY RESOLVED ($N_UNRESOLVED UNRESOLVED): unknown is not PASS -- see the UNRESOLVED lines"; exit 3
else echo "DOCTOR: READY ($N_WARN WARN)"; exit 0; fi
