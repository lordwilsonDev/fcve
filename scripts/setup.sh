#!/usr/bin/env bash
# setup.sh -- build the independent-checker tools FCVE needs, from the manifest, and record what was done.
#
# Safe to run repeatedly (setup, setup again, setup again converge). It:
#   * never touches a verification target, evidence, or anything outside <repo>/.fcve-work (unless --work says otherwise)
#   * never installs an undocumented dependency: a missing prerequisite is reported and setup stops (exit 2)
#   * never substitutes a different tool version: lean4export / nanoda_lib must be at the commits in manifests/environment.json
#   * checks free disk BEFORE expensive work and stops with "BLOCKED: insufficient disk" (exit 4) -- that is not a proof failure
#   * only installs a Lean toolchain if you pass --install-toolchain (it is ~2.5 GB)
#
# Usage: scripts/setup.sh [--tag vX.Y.Z]... [--install-toolchain] [--skip-patched] [--reuse-from DIR] [--work DIR] [--dry-run]
#   --tag            Lean toolchain tag(s) to prepare. Default: every manifest tag whose toolchain is already installed.
#   --skip-patched   build only the upstream tools (no fast-literal patched copies)
#   --reuse-from DIR adopt existing builds instead of rebuilding (saves ~0.5 GB): DIR/lean4export[-TAG], DIR/nanoda_lib, and the patched
#                    copies DIR/lean4export-fastnat, DIR/nanoda_lib-fastparse. Each is VERIFIED (commit; patched copy == pristine+patch)
#                    before it is linked; anything that does not verify is ignored and built fresh.
#   --dry-run        print the plan and the disk arithmetic; change nothing
# Exit codes: 0 complete | 2 prerequisite missing | 4 insufficient disk | 5 a step failed | 64 usage
set -u
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

WORK="${FCVE_WORK:-$FCVE_WORK_DEFAULT}"; TAGS_REQ=(); INSTALL_TC=0; PATCHED=1; REUSE=""; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --tag) TAGS_REQ+=("$2"); shift 2 ;;
    --install-toolchain) INSTALL_TC=1; shift ;;
    --skip-patched) PATCHED=0; shift ;;
    --reuse-from) REUSE="$2"; shift 2 ;;
    --work) WORK="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done
say() { printf '%s\n' "$*"; }
die() { say "SETUP INCOMPLETE: $2"; exit "$1"; }

say "FCVE setup -- $(date -u +%Y-%m-%dT%H:%M:%SZ) -- repo $FCVE_ROOT -- work $WORK$([ "$DRY" = 1 ] && echo ' -- DRY RUN')"

# ---- prerequisites (report all, then stop) ---------------------------------------------------------------------------
have python3 || die 2 "python3 is required (cannot read the manifest). Install Python 3 and re-run."
[ -f "$MANIFEST" ] || die 2 "missing $MANIFEST"
MISSING=""
for T in git patch shasum elan cargo rustc; do have "$T" || MISSING="$MISSING $T"; done
[ -z "$MISSING" ] || die 2 "missing prerequisite(s):$MISSING. Setup does not install undocumented tools. Install them (elan: https://github.com/leanprover/elan; Rust via rustup) and re-run scripts/doctor.sh."
say "prerequisites present: git patch shasum elan cargo rustc"

# ---- which tags -------------------------------------------------------------------------------------------------------
ALL_TAGS=$(python3 -c "import json;print(' '.join(t['tag'] for t in json.load(open('$MANIFEST'))['lean']['toolchains']))")
TAGS=()
if [ "${#TAGS_REQ[@]}" -gt 0 ]; then
  for T in "${TAGS_REQ[@]}"; do case " $ALL_TAGS " in *" $T "*) TAGS+=("$T") ;; *) die 64 "tag $T is not a validated toolchain (manifest: $ALL_TAGS). FCVE does not silently substitute untested versions; add it to the manifest after validating it." ;; esac; done
else
  for T in $ALL_TAGS; do [ -x "$HOME/.elan/toolchains/leanprover--lean4---$T/bin/lean" ] && TAGS+=("$T"); done
  [ "${#TAGS[@]}" -gt 0 ] || { [ "$INSTALL_TC" = 1 ] && TAGS=($ALL_TAGS) || die 2 "no validated Lean toolchain is installed ($ALL_TAGS). Re-run with --tag <vX> --install-toolchain (about 2.5 GB each)."; }
fi
say "tags: ${TAGS[*]}"

NAN_COMMIT=$(mf 'd["independent_checker"]["nanoda_lib"]["validated_commit"]')
exp_commit() { mf "d['independent_checker']['lean4export']['validated_commits']['$1']"; }

# ---- disk arithmetic (before anything expensive) ---------------------------------------------------------------------
HARD=$(mf 'd["measured_requirements"]["disk_gib"]["hard_floor_free"]')
DG() { mf "d['measured_requirements']['disk_gib']['$1']"; }
NEED=0
for T in "${TAGS[@]}"; do
  [ -x "$HOME/.elan/toolchains/leanprover--lean4---$T/bin/lean" ] || NEED=$(python3 -c "print(round($NEED+$(DG per_lean_toolchain),2))")
  [ -e "$WORK/lean4export-$T/.lake/build/bin/lean4export" ] || NEED=$(python3 -c "print(round($NEED+$(DG lean4export_build_per_tag)+$PATCHED*$(DG patched_copies_extra),2))")
done
[ -e "$WORK/nanoda_lib/target/release/nanoda_bin" ] || NEED=$(python3 -c "print(round($NEED+$(DG nanoda_build)+$PATCHED*$(DG patched_copies_extra),2))")
NEED_FULL=$NEED
[ -n "$REUSE" ] && say "(--reuse-from given: the estimate below assumes nothing verifies; adopted builds cost ~0 GiB)"
FREE=$(free_kb "$(dirname "$WORK")"); FREE_G=$(kb_to_gib "${FREE:-0}")
say "disk: ~$NEED_FULL GiB needed for what is missing, $FREE_G GiB free, hard floor $HARD GiB (measured on the validated Mac mini; approximate)"
if [ -z "$REUSE" ] && ! python3 -c "import sys; sys.exit(0 if ${FREE:-0}/1048576 - $NEED_FULL >= $HARD else 1)"; then
  die 4 "BLOCKED: insufficient disk (needs ~$NEED_FULL GiB, $FREE_G GiB free, floor $HARD GiB). This is not a verification failure. Free space, or use --reuse-from DIR to adopt existing builds. Nothing was changed."
fi
[ "$DRY" = 1 ] && { say "dry run: would prepare tags ${TAGS[*]} in $WORK; nothing changed."; exit 0; }
mkdir -p "$WORK" || die 5 "cannot create $WORK"
case "$WORK" in "$FCVE_ROOT"/.fcve-work*) ;; *) say "note: --work is outside the repo's .fcve-work" ;; esac

# ---- toolchains -------------------------------------------------------------------------------------------------------
for T in "${TAGS[@]}"; do
  if [ ! -x "$HOME/.elan/toolchains/leanprover--lean4---$T/bin/lean" ]; then
    [ "$INSTALL_TC" = 1 ] || die 2 "Lean toolchain $T is not installed. Run: scripts/setup.sh --tag $T --install-toolchain (about $(DG per_lean_toolchain) GiB)"
    say "installing Lean toolchain $T ..."
    elan toolchain install "leanprover/lean4:$T" || die 5 "elan could not install $T"
  fi
done

# ---- adopt existing builds (verified, never trusted blindly) ----------------------------------------------------------
adopt() { # adopt <src> <dst> : symlink if dst absent
  [ -e "$2" ] || [ -L "$2" ] || { ln -s "$1" "$2" && say "  adopted $2 -> $1"; }
}
if [ -n "$REUSE" ]; then
  say "adopting verified builds from $REUSE"
  for T in "${TAGS[@]}"; do
    for C in "$REUSE/lean4export-$T" "$REUSE/lean4export"; do
      [ -x "$C/.lake/build/bin/lean4export" ] || continue
      [ "$(tr -d '\n' <"$C/lean-toolchain")" = "leanprover/lean4:$T" ] || continue
      [ "$(git -C "$C" rev-parse HEAD 2>/dev/null)" = "$(exp_commit "$T")" ] || { say "  skip $C: commit is not the validated $(exp_commit "$T" | cut -c1-12)"; continue; }
      [ -z "$(git -C "$C" status --porcelain)" ] || { say "  skip $C: working tree is not clean"; continue; }
      adopt "$C" "$WORK/lean4export-$T"; break
    done
    for C in "$REUSE/lean4export-fastnat" "$REUSE/lean4export-$T-fastnat"; do
      [ "$PATCHED" = 1 ] && [ -x "$C/.lake/build/bin/lean4export" ] && [ -d "$WORK/lean4export-$T" ] || continue
      [ "$(tr -d '\n' <"$C/lean-toolchain")" = "leanprover/lean4:$T" ] || continue
      TMPF=$(mktemp); cp "$WORK/lean4export-$T/Export.lean" "$TMPF"; patch -s "$TMPF" <"$FCVE_ROOT/tool-patches/lean4export-fast-natval.diff" 2>/dev/null
      if cmp -s "$TMPF" "$C/Export.lean"; then adopt "$C" "$WORK/lean4export-$T-fastnat"; else say "  skip $C: Export.lean is not pristine+patch"; fi; rm -f "$TMPF"
    done
  done
  C="$REUSE/nanoda_lib"
  if [ -x "$C/target/release/nanoda_bin" ] && [ "$(git -C "$C" rev-parse HEAD 2>/dev/null)" = "$NAN_COMMIT" ] && [ -z "$(git -C "$C" status --porcelain)" ]; then adopt "$C" "$WORK/nanoda_lib"; else [ -e "$C" ] && say "  skip $C: not built, not the validated commit, or not clean"; fi
  C="$REUSE/nanoda_lib-fastparse"
  if [ "$PATCHED" = 1 ] && [ -x "$C/target/release/nanoda_bin" ] && [ -d "$WORK/nanoda_lib" ]; then
    TMPF=$(mktemp); cp "$WORK/nanoda_lib/src/parser.rs" "$TMPF"; patch -s "$TMPF" <"$FCVE_ROOT/tool-patches/nanoda-fast-decimal-parse.diff" 2>/dev/null
    if cmp -s "$TMPF" "$C/src/parser.rs"; then adopt "$C" "$WORK/nanoda_lib-fastparse"; else say "  skip $C: parser.rs is not pristine+patch"; fi; rm -f "$TMPF"
  fi
fi

# ---- pin nanoda_lib to the validated commit BEFORE the skill's setup script builds it ---------------------------------
if [ ! -x "$WORK/nanoda_lib/target/release/nanoda_bin" ] && [ ! -d "$WORK/nanoda_lib" ]; then
  say "cloning nanoda_lib @ ${NAN_COMMIT:0:12}"
  git clone -q https://github.com/ammkrn/nanoda_lib.git "$WORK/nanoda_lib" && git -C "$WORK/nanoda_lib" checkout -q "$NAN_COMMIT" || die 5 "could not clone/checkout nanoda_lib at the validated commit"
fi

# ---- build via the skill's setup script (idempotent: it skips what already exists) -------------------------------------
PATCH_TEST_OK=1
for T in "${TAGS[@]}"; do
  say "== preparing checker tools for $T =="
  if [ "$PATCHED" = 1 ]; then FAST_LITERALS=1 bash "$FCVE_ROOT/skills/verifying-lean-proofs/scripts/setup-independent-checker.sh" "$T" "$WORK" || die 5 "tool setup failed for $T (see the output above)"
  else bash "$FCVE_ROOT/skills/verifying-lean-proofs/scripts/setup-independent-checker.sh" "$T" "$WORK" || die 5 "tool setup failed for $T"; fi
  [ "$(git -C "$WORK/lean4export-$T" rev-parse HEAD 2>/dev/null)" = "$(exp_commit "$T")" ] || die 5 "lean4export for $T is at $(git -C "$WORK/lean4export-$T" rev-parse --short HEAD 2>/dev/null), not the validated $(exp_commit "$T" | cut -c1-12): refusing to substitute a different version"
done
[ "$(git -C "$WORK/nanoda_lib" rev-parse HEAD 2>/dev/null)" = "$NAN_COMMIT" ] || die 5 "nanoda_lib is not at the validated commit ${NAN_COMMIT:0:12}: refusing to substitute a different version"

# ---- validate the patched builds (equivalence + parse tests), including adopted ones ------------------------------------
PATCH_VALIDATION="NOT_APPLICABLE"
if [ "$PATCHED" = 1 ]; then
  PATCH_VALIDATION=PASS
  for T in "${TAGS[@]}"; do
    FE="$WORK/lean4export-$T-fastnat"
    if [ -x "$FE/.lake/build/bin/lean4export" ]; then
      R=$(cd "$FE" && lake env lean --run "$FCVE_ROOT/skills/verifying-lean-proofs/patches/NatReprCheck.lean" 2>&1 | tail -1)
      [ "$R" = "mismatches: 0" ] && say "patched lean4export $T: equivalence test PASS ($R)" || { say "patched lean4export $T: equivalence test FAILED ($R)"; PATCH_VALIDATION=FAIL; }
    else say "patched lean4export $T: not built"; PATCH_VALIDATION=UNRESOLVED; fi
  done
  if [ -x "$WORK/nanoda_lib-fastparse/target/release/nanoda_bin" ]; then
    if (cd "$WORK/nanoda_lib-fastparse" && cargo test --release parse_decimal >/dev/null 2>&1); then say "patched nanoda_lib: parse-equivalence test PASS"; else say "patched nanoda_lib: parse-equivalence test FAILED"; PATCH_VALIDATION=FAIL; fi
  else say "patched nanoda_lib: not built"; PATCH_VALIDATION=UNRESOLVED; fi
fi

# ---- record what exists ----------------------------------------------------------------------------------------------
python3 - "$WORK" "$FCVE_ROOT" "$PATCH_VALIDATION" "${TAGS[*]}" <<'PY'
import hashlib, json, os, subprocess, sys, datetime
work, root, pv, tags = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split()
def sh(cmd, cwd=None):
    try: return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception: return ""
def sha(p):
    try: return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception: return None
rec = {"generated_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
       "fcve_commit": sh("git rev-parse HEAD", root), "fcve_tree_modified_tracked_files": len([l for l in sh("git status --porcelain", root).splitlines() if not l.startswith("??")]),
       "host": {"model": sh("sysctl -n hw.model"), "chip": sh("sysctl -n machdep.cpu.brand_string"), "arch": sh("uname -m"), "macos": sh("sw_vers -productVersion"), "ram_bytes": sh("sysctl -n hw.memsize")},
       "tools": {"git": sh("git --version"), "python3": sh("python3 --version"), "elan": sh("elan --version"), "rustc": sh("rustc --version"), "cargo": sh("cargo --version"), "tectonic": sh("tectonic --version | head -1")},
       "patch_validation": pv, "patches": {}, "tags": {}, "nanoda_lib": {}}
for name in ("lean4export-fast-natval.diff", "nanoda-fast-decimal-parse.diff"):
    rec["patches"][name] = sha(os.path.join(root, "tool-patches", name))
for t in tags:
    d = os.path.join(work, f"lean4export-{t}"); f = d + "-fastnat"
    rec["tags"][t] = {"lean_toolchain": open(os.path.join(d, "lean-toolchain")).read().strip() if os.path.exists(os.path.join(d, "lean-toolchain")) else None,
        "upstream_commit": sh("git rev-parse HEAD", d), "upstream_binary_sha256": sha(os.path.join(d, ".lake/build/bin/lean4export")),
        "patched_binary_sha256": sha(os.path.join(f, ".lake/build/bin/lean4export")), "adopted_by_symlink": os.path.islink(d)}
n = os.path.join(work, "nanoda_lib"); nf = os.path.join(work, "nanoda_lib-fastparse")
rec["nanoda_lib"] = {"upstream_commit": sh("git rev-parse HEAD", n), "upstream_binary_sha256": sha(os.path.join(n, "target/release/nanoda_bin")),
    "patched_binary_sha256": sha(os.path.join(nf, "target/release/nanoda_bin")), "adopted_by_symlink": os.path.islink(n)}
json.dump(rec, open(os.path.join(work, "setup-record.json"), "w"), indent=2)
PY
say "recorded: $WORK/setup-record.json (patch_validation=$PATCH_VALIDATION)"

if [ "$PATCH_VALIDATION" = FAIL ]; then die 5 "a patched tool failed its validation test; do not use the patched tools. Upstream tools are usable (--fast-literals no)."; fi
say
say "SETUP COMPLETE. Next: scripts/doctor.sh, then scripts/smoke-test.sh"
