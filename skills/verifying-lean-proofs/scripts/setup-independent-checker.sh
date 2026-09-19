#!/usr/bin/env bash
# One-time bootstrap for the independent-checker leg of the proof trust matrix.
#
# Usage: setup-independent-checker.sh <lean-toolchain-tag> <work-dir>
#   e.g. setup-independent-checker.sh v4.28.0 ~/ico-collatz/targets
#
# Produces, under <work-dir>:
#   lean4export/                 built at the exact toolchain tag (must match
#                                 the TARGET proof's own lean-toolchain, since
#                                 it reads that Lean version's .olean format)
#   nanoda_lib/                  built once (not toolchain-specific — it checks
#                                 the .export text format, not olean binaries)
#
# Optional: FAST_LITERALS=1 also builds PATCHED copies (lean4export-$TAG-fastnat, nanoda_lib-fastparse) from
# ../patches/ for proofs containing huge nat literals (millions of digits), where the upstream tools are
# quadratic and stall. The pristine builds are always kept; a verdict from patched tools MUST be disclosed
# (see SKILL.md, "Patched tools"). Patches are refused, not forced, if they do not apply cleanly.
#
# Requires: elan (for the matching Lean toolchain), cargo/rustc (for nanoda).
set -euo pipefail
TAG="${1:?usage: setup-independent-checker.sh <lean-toolchain-tag e.g. v4.28.0> <work-dir>}"
WORK="${2:?usage: setup-independent-checker.sh <lean-toolchain-tag> <work-dir>}"
mkdir -p "$WORK"

command -v elan >/dev/null || { echo "elan not found — install Lean via elan first" >&2; exit 1; }
command -v cargo >/dev/null || { echo "cargo not found — install Rust first" >&2; exit 1; }

FREE_KB=$(df -k / | tail -1 | awk '{print $4}')
if [ "$FREE_KB" -lt $((3 * 1024 * 1024)) ]; then
  echo "WARNING: less than 3GB free disk. lean4export's own build is cheap (~100MB)" >&2
  echo "but pulling a Mathlib olean cache for a NEW toolchain tag is not (~9-10GB)." >&2
  echo "Check df -h / before building the TARGET proof itself, not just this tool." >&2
fi

# Namespaced per tag: a lean4export binary built for one Lean version reads a
# DIFFERENT .olean binary format than another, so a stale reused binary at a
# fixed path would silently check the wrong thing rather than fail loudly.
# (Caught by hand while dogfooding this script: calling it a second time with
# a different tag against the same work-dir reused the first tag's binary.)
EXPORT_DIR="$WORK/lean4export-$TAG"
if [ ! -x "$EXPORT_DIR/.lake/build/bin/lean4export" ]; then
  echo "== cloning lean4export @ $TAG =="
  [ -d "$EXPORT_DIR" ] || git clone --branch "$TAG" https://github.com/leanprover/lean4export.git "$EXPORT_DIR"
  ( cd "$EXPORT_DIR" && lake build )
else
  echo "== lean4export @ $TAG already built at $EXPORT_DIR =="
fi

# Verify unconditionally (fresh clone AND reused directory) — the namespaced
# path makes a mismatch unlikely, not impossible (a manually renamed dir, a
# copy-pasted work-dir, a typo'd tag would still collide otherwise). This is
# a hard failure, not a warning: an unverified exporter silently checks the
# wrong .olean format instead of erroring, which is worse than not checking
# at all — see BUGS.md in this skill's directory for why.
TOOLCHAIN=$(cat "$EXPORT_DIR/lean-toolchain" 2>/dev/null || echo "")
if [ "$TOOLCHAIN" != "leanprover/lean4:$TAG" ]; then
  echo "FATAL: $EXPORT_DIR is built for '$TOOLCHAIN', not 'leanprover/lean4:$TAG'." >&2
  echo "Refusing to hand back a mismatched exporter. Delete $EXPORT_DIR and re-run," >&2
  echo "or check https://github.com/leanprover/lean4export/tags for the right tag." >&2
  exit 1
fi

if [ ! -x "$WORK/nanoda_lib/target/release/nanoda_bin" ]; then
  echo "== cloning + building nanoda_lib (shared across all Lean versions) =="
  [ -d "$WORK/nanoda_lib" ] || git clone https://github.com/ammkrn/nanoda_lib.git "$WORK/nanoda_lib"
  ( cd "$WORK/nanoda_lib" && cargo build --release )
else
  echo "== nanoda_lib already built at $WORK/nanoda_lib =="
fi

if [ "${FAST_LITERALS:-0}" = "1" ]; then
  PATCHES="$(cd "$(dirname "$0")/.." && pwd)/patches"
  FAST_EXPORT="$WORK/lean4export-$TAG-fastnat"
  if [ ! -x "$FAST_EXPORT/.lake/build/bin/lean4export" ]; then
    rm -rf "$FAST_EXPORT"; cp -RL "$EXPORT_DIR" "$FAST_EXPORT"
    ( cd "$FAST_EXPORT" && patch --dry-run -s Export.lean < "$PATCHES/lean4export-fast-natval.diff" >/dev/null \
        || { echo "FATAL: exporter patch does not apply cleanly to $TAG; not forcing it" >&2; exit 1; }
      patch -s Export.lean < "$PATCHES/lean4export-fast-natval.diff" && cp "$PATCHES/NatReprCheck.lean" . && lake build \
        && [ "$(lake env lean --run NatReprCheck.lean | tail -1)" = "mismatches: 0" ] ) \
      || { echo "FATAL: patched exporter failed to build or failed its Nat.repr equivalence check" >&2; exit 1; }
  fi
  FAST_NANODA="$WORK/nanoda_lib-fastparse"
  if [ ! -x "$FAST_NANODA/target/release/nanoda_bin" ]; then
    rm -rf "$FAST_NANODA"; cp -RL "$WORK/nanoda_lib" "$FAST_NANODA"
    ( cd "$FAST_NANODA" && patch --dry-run -s src/parser.rs < "$PATCHES/nanoda-fast-decimal-parse.diff" >/dev/null \
        || { echo "FATAL: nanoda patch does not apply cleanly; not forcing it" >&2; exit 1; }
      patch -s src/parser.rs < "$PATCHES/nanoda-fast-decimal-parse.diff" \
        && cargo test --release parse_decimal >/dev/null && cargo build --release ) \
      || { echo "FATAL: patched nanoda failed to build or failed its parse-equivalence test" >&2; exit 1; }
  fi
  echo
  echo "PATCHED builds ready (disclose them; keep patches/*.diff with the evidence):"
  echo "  --export-bin $FAST_EXPORT/.lake/build/bin/lean4export"
  echo "  --nanoda-bin $FAST_NANODA/target/release/nanoda_bin"
fi

echo
echo "Ready. Pass these to independent-check.sh:"
echo "  --export-bin $EXPORT_DIR/.lake/build/bin/lean4export"
echo "  --nanoda-bin $WORK/nanoda_lib/target/release/nanoda_bin"
