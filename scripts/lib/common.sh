#!/usr/bin/env bash
# Shared helpers for scripts/setup.sh, doctor.sh, smoke-test.sh. Source it; do not execute it.
# Bash 3.2-compatible on purpose (macOS ships 3.2 as /bin/bash), no associative arrays.

FCVE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$FCVE_ROOT/manifests/environment.json"
FCVE_WORK_DEFAULT="$FCVE_ROOT/.fcve-work"

# Put the Lean/Rust install locations FIRST on PATH (moving them to the front if already present). Order matters: the validated
# checker builds used rustup's toolchain (~/.cargo/bin), and a Homebrew rustc earlier in PATH is a different version.
# This only chooses which installed tool is found; it never installs anything.
for _d in "$HOME/.cargo/bin" "$HOME/.elan/bin"; do
  if [ -d "$_d" ]; then PATH="$_d:$(printf '%s' "$PATH" | tr ':' '\n' | grep -vxF "$_d" | paste -sd: -)"; fi
done
export PATH

# Status accounting: each check calls `record LEVEL category name detail`.
# LEVEL is one of PASS WARN FAIL UNRESOLVED (never anything that means "unknown is fine").
N_PASS=0; N_WARN=0; N_FAIL=0; N_UNRESOLVED=0
RESULTS_FILE="$(mktemp "${TMPDIR:-/tmp}/fcve-results.XXXXXX")"
trap 'rm -f "$RESULTS_FILE"' EXIT

record() {
  local level="$1" cat="$2" name="$3" detail="$4"
  case "$level" in
    PASS) N_PASS=$((N_PASS+1)) ;; WARN) N_WARN=$((N_WARN+1)) ;;
    FAIL) N_FAIL=$((N_FAIL+1)) ;; UNRESOLVED) N_UNRESOLVED=$((N_UNRESOLVED+1)) ;;
    *) echo "internal error: bad level '$level'" >&2; exit 70 ;;
  esac
  printf '%s\t%s\t%s\t%s\n' "$level" "$cat" "$name" "$detail" >>"$RESULTS_FILE"
  printf '[%-10s] %-9s %-28s %s\n' "$level" "$cat" "$name" "$detail"
}

have() { command -v "$1" >/dev/null 2>&1; }

# Manifest lookup with python (standard library only). Usage: mf 'd["validated_environment"]["macos"]'
mf() {
  python3 - "$MANIFEST" "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
v = eval(sys.argv[2])
print(v if not isinstance(v, (list, dict)) else json.dumps(v))
PY
}

# Free disk in KiB for the directory holding $1. FCVE_FAKE_FREE_KB is a TEST HOOK (used by the failure-injection
# tests to simulate a full disk); it is never set in normal use and is reported when set.
free_kb() {
  if [ -n "${FCVE_FAKE_FREE_KB:-}" ]; then echo "$FCVE_FAKE_FREE_KB"; return; fi
  df -k "$1" 2>/dev/null | tail -1 | awk '{print $4}'
}

kb_to_gib() { python3 -c "print(round($1/1048576, 2))" 2>/dev/null || echo "?"; }

sha256_of() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }

tool_version() { # best-effort one-line version, empty if the tool is absent
  case "$1" in
    git) git --version 2>/dev/null | awk '{print $3}' ;;
    bash) echo "${BASH_VERSION%%(*}" ;;
    python3) python3 --version 2>/dev/null | awk '{print $2}' ;;
    elan) elan --version 2>/dev/null | awk '{print $2}' ;;
    lake) lake --version 2>/dev/null | sed -n 's/.*Lake version \([0-9.]*\).*/\1/p' ;;
    rustc) rustc --version 2>/dev/null | awk '{print $2}' ;;
    cargo) cargo --version 2>/dev/null | awk '{print $2}' ;;
    tectonic) tectonic --version 2>/dev/null | head -1 | awk '{print $2}' ;;
    *) have "$1" && echo present ;;
  esac
}
