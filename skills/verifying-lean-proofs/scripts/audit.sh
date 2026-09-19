#!/usr/bin/env bash
# audit.sh -- run the Proof Trust Matrix end to end and write a filled-in AUDIT.md.
#
# Usage:
#   audit.sh <target-dir> --module MODULE --decl DECL [--decl DECL ...] \
#            [--out DIR] [--work DIR] [--fast-literals auto|yes|no] [--rebuild] [--skip-independent] [--axioms a,b,c]
#
# What it automates: rows 1-6, 8, 10 (source pin, toolchain, build, sorry/admit/native_decide, axioms,
# stale self-descriptions, independent check). What it CANNOT do, and says so in the output:
#   row 7 (semantic correspondence) -- a human reads the claim against the Lean statement;
#   row 9 (kernel-vulnerability exposure) -- needs live web access.
# So the best verdict this script can reach is PROVISIONAL, never TRUSTED: TRUSTED is not produced by any code path here.
# It never fixes the target. --skip-independent leaves row 10 as NOT RUN (counted as unresolved), for fast checks of rows 1-9.
#
# --fast-literals auto (default): try the pristine lean4export/nanoda first; if the export stalls or is BLOCKED,
#   build the patched fast-literal tools (patches/) and retry, and DISCLOSE that in AUDIT.md.
# --rebuild: run `lake exe cache get` first. The build check itself reuses an existing .lake (weaker than a
#   from-empty clone; AUDIT.md says which). Nothing is ever deleted from the target.
#
# Long steps (export/check) can outlive one agent turn: run this whole script detached, e.g.
#   python3 -c 'import subprocess;subprocess.Popen(["bash","audit.sh",...],start_new_session=True)'
# Every step's wall-clock time is recorded in AUDIT.md (## Timing).
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="" MODULE="" OUT="" WORK="${LEAN_AUDIT_WORK:-$HOME/.lean-proof-audit}" FAST=auto REBUILD=0 SKIP_INDEP=0
AXIOMS="propext,Classical.choice,Quot.sound"
DECLS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --module) MODULE="$2"; shift 2 ;;
    --decl) DECLS+=("$2"); shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --work) WORK="$2"; shift 2 ;;
    --fast-literals) FAST="$2"; shift 2 ;;
    --rebuild) REBUILD=1; shift ;;
    --skip-independent) SKIP_INDEP=1; shift ;;
    --axioms) AXIOMS="$2"; shift 2 ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) TARGET="$1"; shift ;;
  esac
done
[ -n "$TARGET" ] && [ -n "$MODULE" ] && [ "${#DECLS[@]}" -gt 0 ] || {
  echo "usage: audit.sh <target-dir> --module MODULE --decl DECL [--decl DECL ...] [--out DIR] [--work DIR] [--fast-literals auto|yes|no] [--rebuild]" >&2; exit 2; }
case "$FAST" in auto|yes|no) ;; *) echo "--fast-literals must be auto, yes or no" >&2; exit 2 ;; esac
TARGET=$(cd "$TARGET" && pwd) || { echo "target not found" >&2; exit 2; }
[ -n "$OUT" ] || OUT="./audit-$(basename "$TARGET")-$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "$OUT" "$WORK" && OUT=$(cd "$OUT" && pwd) && WORK=$(cd "$WORK" && pwd)
LOG="$OUT/audit.log"; TIMES="$OUT/timing.tsv"; : >"$LOG"; : >"$TIMES"
ROWS="$OUT/rows.tsv"; : >"$ROWS"   # n <TAB> status <TAB> detail

now() { date +%s; }
say() { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*" | tee -a "$LOG" >&2; }
row() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" >>"$ROWS"; say "row $1: $2 -- $3"; }
timed() { local name="$1" t0; shift; t0=$(now); "$@"; local rc=$?; printf '%s\t%s\n' "$name" "$(( $(now) - t0 ))" >>"$TIMES"; return $rc; }

FACTS="$OUT/facts.tsv"; : >"$FACTS"
fact() { printf '%s\t%s\n' "$1" "$2" >>"$FACTS"; }

# ---- preflight -----------------------------------------------------------------------------------------------
# FCVE_FAKE_FREE_KB is a TEST HOOK (simulates a full disk for failure-injection tests); never set in normal use.
FREE_KB="${FCVE_FAKE_FREE_KB:-$(df -k "$OUT" | tail -1 | awk '{print $4}')}"
HARD_KB=$(( ${AUDIT_HARD_FLOOR_KB:-1572864} ))   # 1.5 GiB: the export guard's floor (measured, not universal)
fact host "$(uname -s) $(uname -m) $(sw_vers -productVersion 2>/dev/null) model=$(sysctl -n hw.model 2>/dev/null) ram_gib=$(python3 -c "print(round($(sysctl -n hw.memsize 2>/dev/null || echo 0)/1073741824,1))" 2>/dev/null)"
fact free_disk_kb "$FREE_KB"
if [ "$FREE_KB" -lt "$HARD_KB" ]; then
  say "BLOCKED: insufficient disk ($FREE_KB KiB free, floor $HARD_KB KiB). No expensive work was started. This is not a verdict on the proof."
  printf '# Proof audit: %s\n\n## Verdict: UNRESOLVED -- BLOCKED before any check ran\n\nInsufficient disk: %s KiB free, hard floor %s KiB (measured on the validated Mac mini; approximate). This says nothing about the proof.\nFree space (nothing is deleted for you) and re-run.\n' "$(basename "$TARGET")" "$FREE_KB" "$HARD_KB" >"$OUT/AUDIT.md"
  echo UNRESOLVED
  exit 3
fi
say "target=$TARGET module=$MODULE decls=${DECLS[*]} free_disk_kb=$FREE_KB"
if [ "$FREE_KB" -lt $((3 * 1024 * 1024)) ]; then
  say "WARNING: under 3 GB free. Exports are 50-200 MB each and a fresh toolchain is ~2.5 GB; the export guard aborts at 1.5 GB."
fi
command -v lake >/dev/null || { say "FATAL: lake not on PATH (install Lean via elan)"; exit 2; }

# ---- rows 1-2: source + toolchain pinned -----------------------------------------------------------------------
r12() {
  if git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1; then
    REV=$(git -C "$TARGET" rev-parse HEAD 2>/dev/null); REMOTE=$(git -C "$TARGET" remote get-url origin 2>/dev/null || echo "none"); fact commit "${REV:-none}"; fact remote "$REMOTE"
    DIRTY=$(git -C "$TARGET" status --porcelain | wc -l | tr -d ' ')
    if [ -z "$REV" ]; then row 1 UNRESOLVED "git repo with no commit: nothing identifies the source"
    elif [ "$DIRTY" -gt 0 ]; then row 1 PARTIAL "commit $REV, remote $REMOTE, BUT $DIRTY uncommitted/untracked files: the commit does not identify what was audited"
    else row 1 PASS "commit $REV, remote $REMOTE, working tree clean"; fi
  else row 1 UNRESOLVED "not a git repository: no commit to pin"; fi
  TC=$(cat "$TARGET/lean-toolchain" 2>/dev/null | tr -d '\n')
  MREV=$(python3 - "$TARGET/lake-manifest.json" <<'PY' 2>/dev/null
import json,sys
m=json.load(open(sys.argv[1]))
for p in m.get("packages",[]):
    if p.get("name")=="mathlib": print(p.get("rev","")); break
PY
)
  fact toolchain "${TC:-none}"; fact mathlib "${MREV:-none}"
  fact lean_version "$( (cd "$TARGET" && lake env lean --version 2>/dev/null | head -1) || true)"
  fact tools "elan=$(elan --version 2>/dev/null | awk '{print $2}') rustc=$(rustc --version 2>/dev/null | awk '{print $2}') cargo=$(cargo --version 2>/dev/null | awk '{print $2}') git=$(git --version | awk '{print $3}')"
  if [ -n "$TC" ]; then row 2 PASS "lean-toolchain=$TC; mathlib rev=${MREV:-none (no mathlib dependency)}; drift vs your control environment NOT compared (do that by hand)"
  else row 2 UNRESOLVED "no lean-toolchain file"; fi
}
timed rows1-2 r12
TAG=$(printf '%s' "${TC:-}" | sed -n 's#^leanprover/lean4:\(v[0-9][^ ]*\)$#\1#p')

# ---- row 3: build ----------------------------------------------------------------------------------------------
r3() {
  ( cd "$TARGET" && { if [ "$REBUILD" = 1 ]; then lake exe cache get >>"$OUT/build.log" 2>&1; fi; lake build >>"$OUT/build.log" 2>&1; } ); local rc=$?
  if [ "$rc" -eq 0 ]; then
    if [ -d "$TARGET/.lake" ]; then row 3 PARTIAL "lake build succeeded, but against an existing .lake cache (not from-empty): reproducibility from a clean clone NOT shown$([ "$REBUILD" = 1 ] && echo "; cache get was run (--rebuild)")"
    else row 3 PASS "lake build succeeded on a tree with no prior .lake"; fi
  else row 3 FAIL "lake build exit $rc -- see $OUT/build.log (not fixing the target)"; fi
}
timed row3-build r3

# ---- rows 4-5: sorry / admit / native_decide --------------------------------------------------------------------
r45() {
  bash "$HERE/sorry-audit.sh" "$TARGET" >"$OUT/sorry-audit.txt" 2>&1
  S=$(grep '^SORRY_COUNT=' "$OUT/sorry-audit.txt" | cut -d= -f2); A=$(grep '^ADMITTED_COUNT=' "$OUT/sorry-audit.txt" | cut -d= -f2); N=$(grep '^NATIVE_DECIDE_COUNT=' "$OUT/sorry-audit.txt" | cut -d= -f2)
  if [ "${S:-x}" = 0 ] && [ "${A:-x}" = 0 ]; then row 4 PASS "0 sorry, 0 admit (text scan; row 6 is the authoritative check)"; else row 4 FAIL "sorry=${S:-?} admit=${A:-?} -- see sorry-audit.txt"; fi
  if [ "${N:-x}" = 0 ]; then row 5 PASS "0 native_decide"; else row 5 PARTIAL "${N:-?} native_decide use(s): decide whether acceptable for this claim -- see sorry-audit.txt"; fi
}
timed rows4-5 r45

# ---- row 6: axiom footprint per declaration ---------------------------------------------------------------------
r6() {
  # ONE `lake env lean` for all declarations: importing Mathlib costs ~2 min each time (measured), so never once per decl.
  local bad=0 flag=0 D SCR AX
  : >"$OUT/axioms.tsv"
  SCR=$(mktemp "${TMPDIR:-/tmp}/axiom-check-XXXXXX") && mv "$SCR" "$SCR.lean" && SCR="$SCR.lean"
  { printf 'import %s\n' "$MODULE"; for D in "${DECLS[@]}"; do printf '#print axioms %s\n' "$D"; done; } >"$SCR"
  ( cd "$TARGET" && lake env lean "$SCR" ) >"$OUT/axioms-all.txt" 2>&1; rm -f "$SCR"
  python3 - "$OUT/axioms-all.txt" "$OUT/axioms.tsv" "${DECLS[@]}" <<'PY'
import re,sys
t=open(sys.argv[1]).read(); out=open(sys.argv[2],"w"); decls=sys.argv[3:]
found={}
for m in re.finditer(r"'([^']+)' (depends on axioms: \[(.*?)\]|does not depend on any axioms)",t,re.S):
    found[m.group(1)]=("NONE" if m.group(3) is None else ",".join(a.strip() for a in m.group(3).replace("\n"," ").split(",") if a.strip()))
for d in decls: out.write(f"{d}\t{found.get(d,'UNPARSED')}\n")
PY
  while IFS=$'\t' read -r D AX; do
    case ",$AX," in *,sorryAx,*|*,UNPARSED,*) bad=1 ;; esac
    for a in $(echo "$AX" | tr ',' ' '); do case ",$AXIOMS,NONE," in *,"$a",*) ;; *) flag=1 ;; esac; done
  done <"$OUT/axioms.tsv"
  if [ "$bad" = 1 ]; then row 6 FAIL "sorryAx present or output unparsed -- see axioms-all.txt / axioms.tsv"
  elif [ "$flag" = 1 ]; then row 6 PARTIAL "axioms outside {$AXIOMS}: classify each (KERNEL_STANDARD/MATHLIB_STANDARD/CLASSICAL/PROJECT/EXTERNAL) -- axioms.tsv"
  else row 6 PASS "every declaration's axioms within {$AXIOMS} (axioms.tsv). Classical.choice, if listed, means the proof is classical"; fi
}
timed row6-axioms r6

# ---- row 7: human -----------------------------------------------------------------------------------------------
row 7 "NEEDS HUMAN" "read the source claim (paper/spec) against each Lean statement side by side; write the comparison. Print statements: 'lake env lean' with #check / delaborated statements. MATCH/PARTIAL/MISMATCH/UNCLEAR is a human verdict (a model may draft, not certify)."

# ---- row 8: stale self-descriptions -----------------------------------------------------------------------------
r8() {
  local f n stale=""
  if ! git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1; then row 8 UNRESOLVED "not a git repo: cannot date self-descriptions"; return; fi
  for f in $(cd "$TARGET" && ls *.md 2>/dev/null); do
    n=$(git -C "$TARGET" rev-list --count "$(git -C "$TARGET" log -1 --format=%H -- "$f" 2>/dev/null)..HEAD" 2>/dev/null)
    [ -n "$n" ] && [ "$n" -gt 0 ] && stale="$stale $f(${n} commits behind)"
  done
  if [ -n "$stale" ]; then row 8 PARTIAL "descriptive files older than HEAD:${stale}. Do NOT cite them as evidence of the current state; verify claims fresh."
  else row 8 PASS "no root-level .md file is older than HEAD (still: cite only what this audit re-checked)"; fi
}
timed row8-stale r8

# ---- row 9: web ---------------------------------------------------------------------------------------------------
row 9 UNRESOLVED "needs live web access: compare ${TC:-the pinned Lean version} against release notes for kernel soundness fixes. Starting list: LESSONS.md D22 (lean4lean bugs-found). Marked UNRESOLVED, not skipped."

# ---- row 10: independent checker --------------------------------------------------------------------------------
r10() {
  if [ "$SKIP_INDEP" = 1 ]; then row 10 "NOT RUN" "--skip-independent: the independent check was not attempted. This is unresolved, not a pass."; fact independent "NOT RUN (--skip-independent)"; fact patched_tools "not used (independent check not run)"; return; fi
  [ -n "$TAG" ] || { row 10 UNRESOLVED "cannot read a v-tag from lean-toolchain ('${TC:-}'): lean4export needs the exact tag"; return; }
  command -v cargo >/dev/null || { row 10 UNRESOLVED "cargo not found: nanoda cannot be built"; return; }
  if [ "$(df -k "$OUT" | tail -1 | awk '{print $4}')" -lt $((2 * 1024 * 1024)) ]; then say "WARNING: under 2 GB free before the independent check; exports are 50-200 MB and the tool builds ~0.3-0.6 GB. The export guard will abort at 1.5 GB (reported as UNRESOLVED, not a failure)."; fi
  local EXP="$WORK/lean4export-$TAG" NAN="$WORK/nanoda_lib/target/release/nanoda_bin" USED="upstream (unpatched)" RD="$OUT/independent-check"
  if [ "$FAST" != yes ]; then
    timed setup-pristine bash "$HERE/setup-independent-checker.sh" "$TAG" "$WORK" >"$OUT/setup.log" 2>&1 \
      || { row 10 UNRESOLVED "setup failed -- see setup.log"; return; }
    STALL_TICKS=$([ "$FAST" = auto ] && echo 6 || echo 15) timed independent-check-pristine bash "$HERE/independent-check.sh" --delete-exports --target "$TARGET" --module "$MODULE" --export-bin "$EXP/.lake/build/bin/lean4export" \
      --nanoda-bin "$NAN" --axioms "$AXIOMS" --out "$RD" "${DECLS[@]}" >"$OUT/independent-check.log" 2>&1
  fi
  need_fast=0; [ "$FAST" = yes ] && need_fast=1
  if [ "$FAST" = auto ] && grep -qE 'BLOCKED|TOOL_ERROR' "$RD/results.tsv" 2>/dev/null; then need_fast=1; say "pristine tools BLOCKED on at least one declaration: retrying with the fast-literal tools"; fi
  if [ "$need_fast" = 1 ]; then
    FAST_LITERALS=1 timed setup-fast bash "$HERE/setup-independent-checker.sh" "$TAG" "$WORK" >"$OUT/setup-fast.log" 2>&1 \
      || { row 10 UNRESOLVED "pristine tools blocked and the fast-literal setup failed -- see setup-fast.log"; return; }
    USED="PATCHED (fast decimal literals: patches/*.diff) -- DISCLOSE"
    rm -rf "$RD-fast"
    timed independent-check-fast bash "$HERE/independent-check.sh" --delete-exports --target "$TARGET" --module "$MODULE" --export-bin "$WORK/lean4export-$TAG-fastnat/.lake/build/bin/lean4export" \
      --nanoda-bin "$WORK/nanoda_lib-fastparse/target/release/nanoda_bin" --axioms "$AXIOMS" --out "$RD-fast" "${DECLS[@]}" >"$OUT/independent-check-fast.log" 2>&1
    RD="$RD-fast"
  fi
  [ -f "$RD/results.tsv" ] || { row 10 UNRESOLVED "no results.tsv -- see independent-check*.log"; return; }
  local total pass
  total=$(tail -n +2 "$RD/results.tsv" | wc -l | tr -d ' '); pass=$(tail -n +2 "$RD/results.tsv" | awk -F'\t' '$2=="PASS"' | wc -l | tr -d ' ')
  fact independent "$USED; $pass/$total declarations PASS"
  if [ "$need_fast" = 1 ]; then fact patched_tools "YES -- PATCHED (patch sha256: lean4export-fast-natval $(shasum -a 256 "$HERE/../patches/lean4export-fast-natval.diff" | cut -c1-12)..., nanoda-fast-decimal-parse $(shasum -a 256 "$HERE/../patches/nanoda-fast-decimal-parse.diff" | cut -c1-12)...); validation is recorded by scripts/setup.sh (setup-record.json)"
  else fact patched_tools "no -- upstream tools only"; fi
  cp "$RD/results.tsv" "$OUT/row10-results.tsv"; cp "$RD/tools.tsv" "$OUT/row10-tools.tsv" 2>/dev/null
  if [ "$pass" = "$total" ] && [ "$total" -gt 0 ]; then
    if [ "$need_fast" = 1 ]; then row 10 PARTIAL "PASS $pass/$total with $USED. A verdict from patched tools must be disclosed and validated (SKILL.md 'Patched tools'); results in row10-results.tsv"
    else row 10 PASS "PASS $pass/$total with $USED; raw checker output in independent-check*/; still compare its axiom set with row 6"; fi
  else
    local rejected blocked
    rejected=$(tail -n +2 "$RD/results.tsv" | awk -F'\t' '$2=="FAIL"' | wc -l | tr -d ' '); blocked=$((total - pass - rejected))
    if [ "$rejected" -gt 0 ]; then row 10 FAIL "$rejected declaration(s) REJECTED by the independent checker -- row10-results.tsv"
    else row 10 UNRESOLVED "no verdict for $blocked of $total (BLOCKED = export stalled/aborted, TOOL_ERROR = checker did not run); $pass PASS. This is NOT a rejection. Reasons in row10-results.tsv (e.g. disk-floor, stalled-no-output: triage per SKILL.md before calling it a tool limitation)."; fi
  fi
}
timed row10-independent r10

# ---- write AUDIT.md ----------------------------------------------------------------------------------------------
python3 - "$OUT" "$TARGET" "$MODULE" "${DECLS[*]}" <<'PY'
import sys,os
out,target,module,decls=sys.argv[1:5]
NAMES={1:"Source pinned",2:"Toolchain pinned",3:"Clean rebuild",4:"No sorry/admit",5:"No native_decide",6:"Axiom footprint",7:"Semantic correspondence",8:"Self-description not stale",9:"Kernel vulnerability exposure",10:"Independent check"}
rows={}
for l in open(os.path.join(out,"rows.tsv")):
    n,st,d=l.rstrip("\n").split("\t",2); rows[int(n)]=(st,d)
facts={}
for l in open(os.path.join(out,"facts.tsv")):
    k,_,v=l.rstrip("\n").partition("\t"); facts[k]=v
sts=[rows.get(n,("NOT RUN",))[0] for n in range(1,11)]
# --- verdict. CEILING: PROVISIONAL. There is deliberately no code path that yields TRUSTED: rows 7 (human) and 9 (web) are
# --- never automated, and "no active failure" is not "trusted".
if "FAIL" in sts:
    verdict="REJECTED (at least one row actively fails)"; why=[n for n in range(1,11) if sts[n-1]=="FAIL"]
elif not any(s=="PASS" for s in sts[:6]):
    verdict="UNRESOLVED (no automated row could be evaluated)"; why=[n for n in range(1,11) if sts[n-1]!="PASS"]
else:
    verdict="PROVISIONAL (no active failure among the automated rows; unresolved rows keep it below TRUSTED)"; why=[n for n in range(1,11) if sts[n-1]!="PASS"]
assert not verdict.startswith("TRUSTED"), "audit.sh must never emit TRUSTED"
counts={}
for s_ in sts: counts[s_]=counts.get(s_,0)+1
t=[l.rstrip("\n").split("\t") for l in open(os.path.join(out,"timing.tsv"))]
tot=sum(int(b) for a,b in t)
def status_of(n): return rows.get(n,("NOT RUN",""))[0]
with open(os.path.join(out,"AUDIT.md"),"w") as f:
    f.write(f"# Proof audit: {os.path.basename(target)}\n\n")
    f.write(f"## Verdict: {verdict}\n\n")
    f.write("**This automated audit cannot produce TRUSTED.** Row 7 (semantic correspondence) needs a named human; row 9 (kernel-vulnerability review) needs the web. "
            "Rows keeping the verdict below TRUSTED: " + (", ".join(map(str,why)) or "none") + ".\n\n")
    f.write("### At a glance\n\n| | |\n|---|---|\n")
    def line(k,v): f.write(f"| {k} | {v} |\n")
    line("Target",f"`{target}`"); line("Module / declarations",f"`{module}` / {decls}")
    line("Repository commit",f"`{facts.get('commit','?')}` (remote: {facts.get('remote','?')})")
    line("Toolchain / Lean",f"{facts.get('toolchain','?')} / {facts.get('lean_version','?')}")
    line("Mathlib revision",facts.get("mathlib","?"))
    line("Environment",facts.get("host","?")+"; "+facts.get("tools","?"))
    line("Row results",", ".join(f"{k}: {v}" for k,v in sorted(counts.items())))
    line("Patched tools",facts.get("patched_tools","unknown -- independent check did not complete"))
    line("Independent checker (row 10)",f"**{status_of(10)}** -- {facts.get('independent','not completed')}")
    line("Axiom audit (row 6)",f"**{status_of(6)}** -- see axioms.tsv")
    line("Semantic review (row 7)",f"**{status_of(7)}** -- not done by this script; a named human must do it")
    line("Web / kernel review (row 9)",f"**{status_of(9)}** -- not done by this script; needs live web access")
    line("Free disk at start",f"{int(facts.get('free_disk_kb','0'))/1048576:.2f} GiB")
    f.write("\n### Rows\n\n| # | Gate | Status | Evidence / note |\n|---|---|---|---|\n")
    for n in range(1,11):
        st,d=rows.get(n,("NOT RUN","")); f.write(f"| {n} | {NAMES[n]} | **{st}** | {d} |\n")
    f.write("\n### Status meanings\n\nPASS = check ran and holds. FAIL = check ran and rejected the proof/evidence. BLOCKED / TOOL_ERROR = the check could not complete or the tool never ran properly: **no verdict on the proof, not a rejection**. "
            "UNRESOLVED / NEEDS HUMAN / NOT RUN = not established, **never a pass**. PARTIAL = passes on a stated weaker basis.\n\n")
    f.write("## Timing (wall clock, seconds)\n\n| step | s |\n|---|---|\n")
    for a,b in t: f.write(f"| {a} | {b} |\n")
    f.write(f"| **total** | **{tot}** |\n\n")
    f.write("## Files\n`rows.tsv`, `facts.tsv`, `audit.log`, `build.log`, `sorry-audit.txt`, `axioms.tsv`, `axioms-all.txt`, `independent-check*/`, `row10-results.tsv`, `row10-tools.tsv`, `setup*.log`.\n\n")
    f.write("Provenance: automated pass. Never write \"proved\" as a bare verdict; state the verdict above and list what keeps it from TRUSTED. The model can propose; the experiment decides.\n")
print(verdict.split(" ")[0])
PY
say "wrote $OUT/AUDIT.md"
