# Bug Reports

Bugs found in this skill's own tooling (not in any audited proof). Keep every
entry even after it's fixed — the point is a record of what broke and why the
fix actually closes it, in the same spirit as row 8 of the Proof Trust Matrix
(don't trust a description of current state without checking it).

---

## BUG-001: `setup-independent-checker.sh` silently reused the wrong Lean version's exporter

**Status:** Fixed 2026-09-18. **Severity:** High — would have produced a false
PASS/FAIL from a tool checking the wrong thing, with no error to signal it.

### What happened

`setup-independent-checker.sh` was called twice in the same work directory,
once with tag `v4.28.0` (auditing `eliahou-collatz-bounds`) and later with tag
`v4.34.0` (checking a new theorem in a different Lean project). The second
call printed:

```
== lean4export already built at ~/ico-collatz/targets/lean4export ==
```

and handed back the *same* binary path both times. That binary was built for
Lean `v4.28.0` — the first call's version, not the second's.

### Why it happened

The script's existence check was:

```bash
if [ ! -x "$WORK/lean4export/.lake/build/bin/lean4export" ]; then
  # ...clone + build...
else
  echo "== lean4export already built at $WORK/lean4export =="
fi
```

This asks "does *a* binary exist at this fixed path," not "does a binary
*for the requested tag* exist here." `lean4export` binaries are not
interchangeable across Lean versions — the tool reads a specific version's
`.olean` binary format directly, so a `v4.28.0` build handed a `v4.34.0`
project's `.olean` files doesn't fail loudly; it either errors deep inside in
a confusing way or, worse, produces output that looks structurally fine but
was built against assumptions that don't hold. The bug is a classic
path-based cache invalidation miss: the cache key (a fixed directory path)
didn't include the thing that actually determines validity (the toolchain
tag).

### How it was caught

Not by inspection — by dogfooding. The skill was used a second time, for a
second Lean version, in the same session that built it. The reused-path
symptom (`lean4export already built`, printed for a *different* tag than the
one just requested) was suspicious enough on sight to check
`cat lean-toolchain` before trusting the result, which confirmed the mismatch
immediately. This is the exact discipline row 8 of the skill's own checklist
asks for ("verify before citing") applied to the skill's own tooling instead
of a target proof — the skill caught a bug in itself by the same standard it
holds other things to.

### The fix

Two layers, not one:

1. **Structural**: namespace the build directory by tag
   (`$WORK/lean4export-$TAG` instead of `$WORK/lean4export`). Two different
   tags can no longer physically collide on the same path — there is no cache
   key to get wrong because there's no shared cache slot.
2. **Verification, unconditional**: after the namespaced path is resolved
   (whether freshly cloned or reused), read `lean-toolchain` from it and
   compare against the requested tag. **Hard-fail (`exit 1`) on mismatch**,
   not a warning — a warning that's easy to scroll past defeats the point.
   This layer exists specifically for the cases namespacing alone doesn't
   cover: a manually renamed directory, a copied work-dir from another
   project, a typo in the tag argument that happens to match an unrelated
   existing directory name.

### Why it can't happen again

- **It's not "we remembered to add a check" — it's structural.** The fix
  doesn't rely on remembering the toolchain string format correctly forever;
  a mismatched directory is now a *hard error with a message telling you
  exactly what's wrong and how to fix it*, not a silent wrong answer. Even if
  someone deletes the verification block later, the namespacing alone
  prevents the original collision.
- **Verified by reproduction, not just by re-reading the diff.** Before
  calling this fixed, a synthetic mismatched directory was constructed by
  hand (`lean-toolchain` file claiming `v4.28.0` inside a directory named for
  `v9.9.9`) and the script was run against it. It exited 1 with the expected
  message. A fix that was only read, not exercised against the failure it
  claims to prevent, is a guess — this one was tested against the actual
  failure shape.
- **The two copies (`~/.claude/skills/...` and `~/Desktop/verifying-lean-proofs/...`)
  are kept in sync by direct `cp`, checked with `diff` after every sync** —
  a skill fix that lands in one copy and not the other reintroduces exactly
  this class of bug at the deployment level instead of the code level.

---

## BUG-002: the "memoization cache reset" root cause for lean4export stalls was a hypothesis repeated as fact

**Status:** Corrected 2026-09-19. **Severity:** High — it turned a fixable tooling gap into a "disclosed tool limitation" on a headline theorem (FCVE VCE-001, Gate 9 CHECKER_INCOMPATIBLE).

**What happened:** SKILL.md and the Phase 18 correction ledger attribute `reason=stalled-no-output` on large exports to "a memoization cache that's reset every call". The Phase 18 ledger itself called this a hypothesis. It is not the cause of the `results_eliahou_theorem_1_1` stall.

**Actual cause:** `sample` of the stalled exporter shows `Nat.reprFast → toDigitsCore → __gmpn_divrem_1`: quadratic decimal conversion of a huge `natVal` literal (this proof has literals up to 25.6M digits). After fixing the exporter the stall moved to nanoda, whose `BigUint::from_str` is quadratic too. Patched copies of both (diffs in `~/fcve/tool-patches/`) checked the theorem: 17,464 declarations, axioms match Gate 6; negative control (one corrupted digit) is rejected; five earlier passes reproduce.

**How to check next time:** before calling a stall a tool limitation, `sample <pid>` and read the top of stack. Huge-literal proofs (decide/norm_num over exponents in the millions) hit this; other stalls may not.

**Also (BUG-003):** `independent-check.sh` `cd`s to the nanoda dir before using the config path, so a relative `--out` gives "failed to open configuration file". Use an absolute `--out`.

---

## BUG-003 (detail): `independent-check.sh` failed on a relative `--out`, and recorded the tooling error as FAIL

**Status:** Fixed 2026-09-19. **Severity:** Medium — a false "FAIL" on a real proof.

**What happened:** the script `cd`s into the nanoda directory before launching the checker, but passed a config path relative to
the original directory. nanoda printed `failed to open configuration file` and exited 1; the script's status logic saw "not PASS" and wrote **FAIL**.

**Fix:** (1) `OUT_DIR` is resolved to an absolute path right after `mkdir -p`. (2) Status is now PASS / FAIL / TOOL_ERROR / BLOCKED: `TOOL_ERROR` when nonzero exit and stderr starts with `Error:` (the checker never ran properly); PASS also requires the target declaration in the checker's output. (3) `tools.tsv` records the exporter/checker binary sha256 and git state; `export-literal-scan.py` logs the longest nat literal; an export stall now saves `sample` output before the process is killed.
**Verified:** a relative `--out` run passed on `results_farey_pair_bound` (12012 declarations); a fake checker that prints `Error: ...` and exits 1 was classified `TOOL_ERROR`.

---

## BUG-004: a negative control that modified nothing (my own error, caught by reading the count)

**Status:** Caught in the act, 2026-09-19. **Severity:** High if uncaught — a "rejects bad input" claim resting on a control that never fed the checker bad input.

**What happened:** to prove the patched checker still rejects corrupted proofs, I tampered with the big literal by matching `"ie":1224981}` on the same line. The real line format is `{"ie":1224624,"natVal":"…"}`; the match found 0 lines. The unmodified file was checked, passed, and I nearly took it as "control passed". The script printed `tampered lines: 0`.
**Fix / rule:** every control asserts its own perturbation happened (`modified > 0`) before running; then it must be *rejected* (panic on failed `def_eq`, exit 101, no "no errors" line). See LESSONS.md B9–B10.

---

## BUG-005: setup script gave no way to build the fast-literal tools

**Status:** Fixed 2026-09-19. `FAST_LITERALS=1 setup-independent-checker.sh` builds patched copies from `patches/` beside the pristine ones, refuses patches that don't apply, and runs their equivalence tests (`NatReprCheck.lean`, `cargo test parse_decimal`). Verified from a clean clone: lean4export v4.28.0 @ d065b00, nanoda_lib @ 4c544ed, then the headline theorem re-checked end to end (17,464 declarations) with the skill's own script.

---

## BUG-006: `audit.sh` first drafts (all found by running them, none by reading them)

**Status:** Fixed 2026-09-19.
1. **Syntax error only surfaced mid-run.** A missing `}` in the row-3 function; bash parses function bodies lazily, so rows 1-2 ran and *then* the script died. Always `bash -n` AND do a real run before trusting a script.
2. **A blocked export was reported as REJECTED.** The disk guard aborted an export (free space < 1.5 GB), the wrapper counted "not PASS" as FAIL and produced a REJECTED verdict. BLOCKED/TOOL_ERROR now give row 10 = UNRESOLVED ("this is NOT a rejection"); only a checker-reported FAIL is FAIL.
3. **Row 6 re-imported Mathlib once per declaration** (~2 min each, measured). Now one `lake env lean` file with all `#print axioms` (270 s -> 151 s for two declarations).
4. **Exports were kept after checking**, eating 50-200 MB each and tripping the disk guard on a 2 GB-free machine. `independent-check.sh --delete-exports` (used by audit.sh) records the export's sha256 in the monitor log and removes the file.
5. **The stall wait was 5 minutes** even for the disposable upstream attempt in `auto` mode; `STALL_TICKS` is now overridable and `auto` uses 6 (2 min of flat non-zero output).
Verified: two full audits (different projects, Lean 4.28.0 and 4.34.0) reach PROVISIONAL with the expected rows; see `examples/`.
