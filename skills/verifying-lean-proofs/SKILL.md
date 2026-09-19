---
name: verifying-lean-proofs
description: Use when someone brings a Lean 4/Mathlib proof, repo, or theorem claim and asks whether it's actually verified or trustworthy, not just whether it compiles — including auditing an AI-generated, third-party, or "fully proved" Lean formalization before citing or relying on it.
---

# Verifying Lean Proofs

## Overview

"Compiles with no errors" and "trustworthy" are different claims. A Lean
proof can compile cleanly and still be wrong in ways compiling doesn't catch:
a hidden `sorry`, an undisclosed axiom, a theorem statement that doesn't
actually say what the paper/spec claims, or — the one most people never
check — a Lean kernel version with a known soundness bug. This skill runs the
proof through a fixed checklist (`PROOF-TRUST-MATRIX.md`) using the scripts
in `scripts/`, ending in one of four verdicts: TRUSTED, PROVISIONAL,
UNRESOLVED, REJECTED. Never "proved" as a bare word.

This is two separable things, as the name implies: (1) the checklist/scripts
here, which don't change per proof, and (2) the specific proof someone hands
you, which gets run through them. Don't skip straight to reading the Lean
source and eyeballing it — that's exactly the failure mode this exists to
catch.

## When to use

- Someone says "verify this proof" / "is this Lean formalization actually
  correct" / "audit this before we cite it"
- An AI coding/proof agent (or anyone) claims a Lean theorem is "fully proved"
  and you need to check that claim rather than take it at face value
- Reviewing a third-party Lean repo before depending on its results

**Not for**: writing new proofs from scratch (that's ordinary Lean/Mathlib
work), or trivial one-line sanity checks where a `#print axioms` by hand is
obviously enough — this is for when the claim matters enough to check
properly.

## Workflow

1. Copy `PROOF-TRUST-MATRIX.md` into your output. Fill rows 1-2 by reading
   the repo (commit, `lean-toolchain`, Mathlib rev) — do not proceed on
   assumption.
2. Rows 3-6 are scripted:
   ```bash
   scripts/source-inventory.sh <target-dir>   # file/theorem/def/axiom counts
   scripts/sorry-audit.sh <target-dir>        # sorry/admit/native_decide — rows 4-5
   ```
   Both use `--exclude-dir=.lake --exclude-dir=.git` internally — if you copy
   this pattern elsewhere, keep that exclusion or you'll count vendored
   Mathlib source as the target's own code (see Common Mistakes).
   For row 6, put `#print axioms <theorem>` in a scratch `.lean` file that
   imports the module declaring it, `lake env lean scratch.lean`, then
   **delete the scratch file** — never commit it to the audited repo.
   `scripts/axiom-audit.sh` explains this since `#print axioms` needs a real
   Lean file, not a CLI flag. **This command can run long on a Mathlib-heavy
   import** (same silent-backgrounding risk as step 7's exports) — don't
   assume a default tool-call timeout is enough; run it the same
   detached/backgrounded way if it doesn't return quickly.
3. Row 3 (clean rebuild): `lake exe cache get && lake build` from the
   unmodified clone. If it fails, that's the finding — don't "fix" the
   target's build to make it pass. If a `.lake` build cache already exists
   from earlier work, reusing it is fine for iteration, but **disclose it as
   a caveat** rather than reporting an unqualified PASS — the evidence file
   should say whether this was validated against a from-empty clone or an
   existing cache, since only the former also confirms reproducibility.
4. Row 7 (semantic correspondence): read the actual source of the claim (the
   paper, spec, or linked issue) and the Lean statement side by side. Write
   the comparison down — map, don't summarize. A theorem whose Lean statement
   silently conflates two mathematically different things (e.g. a sequence's
   length vs. its distinct-element count) is a MISMATCH even if the proof
   itself is sorry-free.
5. Row 8: `git log --oneline -- <any README/summary/docstring you're about to
   cite>`. If it predates the commit you're auditing, it's not evidence of
   the current state — verify current claims fresh, regardless of whether the
   stale doc oversells or undersells.
6. Row 9: check the pinned Lean version's release notes / changelog (e.g.
   `lean-lang.org/doc/reference/latest/releases/`) between that version and
   current for any kernel soundness fix, and search for the version string
   plus "kernel" / "soundness" / "CVE". This needs live web access — if
   that's unavailable in your environment, mark row 9 UNRESOLVED rather than
   silently skipping it or assuming no vulnerability exists. A version
   predating a fix is a real, disclosable exposure even if exploiting it
   needs deliberate malicious intent — say so plainly, don't downgrade it to
   a footnote. Also worth a quick grep of the target's own source for
   metaprogramming that could plausibly reach the vulnerable path (e.g.
   `elab`/`macro`/direct `Lean.Meta`/`Lean.Elab` API use, unsafe casts) —
   absence of that narrows the exposure without closing it.
7. Row 10 (independent checker) — the only gate that closes row 9's gap
   without bumping the target's own toolchain:
   ```bash
   scripts/setup-independent-checker.sh <lean-toolchain-tag> <work-dir>   # once per Lean version
   scripts/independent-check.sh --target <dir> --module <Module> \
     --export-bin <work-dir>/lean4export-<tag>/.lake/build/bin/lean4export \
     --nanoda-bin <work-dir>/nanoda_lib/target/release/nanoda_bin \
     --out <ABSOLUTE out-dir> <decl> [<decl>...]
   ```
   Run this **detached from your own shell** if it might outlive the current
   turn (`Popen(..., start_new_session=True)`; macOS has no `setsid`) — see
   Common Mistakes. `results.tsv` statuses: **PASS** (exit 0 + "Checked N
   declarations with no errors" + the target printed), **FAIL** (the checker ran
   and rejected the proof), **TOOL_ERROR** (the checker never ran properly —
   *not* evidence about the proof), **BLOCKED** (no verdict: export incomplete
   or stalled). A PASS row without the raw checker output quoted is a claim
   about evidence, not evidence; also compare the checker's printed axiom set
   with your own row-6 result. `<out-dir>/tools.tsv` records the exact
   exporter/checker binaries (sha256, git rev, dirty count) behind the verdicts.
   If a declaration is BLOCKED, do **not** call it a tool limitation yet —
   go to *Triage: stalls* below.
8. Fill in the verdict per `PROOF-TRUST-MATRIX.md`'s rules. State exactly
   which rows are incomplete if not TRUSTED.

## Triage: when an export or check stalls

A stall (`reason=stalled-no-output`, or nanoda at 100% CPU with no result) is a
**symptom**. Diagnose before you classify — twice we recorded a guess as a
root cause (BUG-002).

1. `sample <pid> 3 -file stall.txt` (the script saves one automatically on an
   export stall: `<decl>.stall-sample.txt`). Read the top of stack.
2. `scripts/export-literal-scan.py <file.export>` — the longest nat literal.
   Literals with >100k digits (from `decide`/`norm_num` over huge exponents)
   make lean4export's *printing* and nanoda's *parsing* quadratic. Stack shows
   `Nat.repr`/`toDigitsCore`/`gmpn_divrem_1` (exporter) or
   `BigUint::from_str_radix` (checker). If that's it → use the fast-literal builds below.
3. Anything else (deep recursion, real memoization cost, memory): read the stack,
   form a hypothesis, **label it a hypothesis** wherever you write it, and test it.
   Only after a stack-level cause is established is "UNRESOLVED — disclosed tool
   limitation" honest. Adding RAM or retrying is not a fix.
4. Re-sample after each fix: the stall can move from the exporter to the checker.

## Patched tools (fast literals)

`FAST_LITERALS=1 scripts/setup-independent-checker.sh <tag> <work-dir>` builds
patched copies beside the pristine ones (`lean4export-<tag>-fastnat`,
`nanoda_lib-fastparse`) from `patches/`, refusing to force a patch that doesn't
apply, and running the patches' own equivalence tests. Patches touch decimal
text conversion only, not type-checking. Applies cleanly and passes
`NatReprCheck.lean` on Lean v4.28.0 and v4.34.0; the nanoda patch is verified on
nanoda_lib @ 4c544ed. Rules when a verdict comes from patched tools:

- **Disclose it in the report and the trust statement** (a reviewer limitation, stated by a named human), with the two diffs beside the evidence.
- **Validate before trusting** (all three, not one): export byte-identical to the pristine exporter over the prefix it reached;
  every declaration the pristine checker passed still passes with identical counts; a negative control that *demonstrably
  modified something* (assert the count) is rejected by the patched checker.
- Keep `tools.tsv` (binary hashes). Patched builds are machine-local; a third party needs the diffs to reproduce.
- Upstream the fixes if you can (`leanprover/lean4export`, `ammkrn/nanoda_lib`); until then the verdict rests on your patches.

## Running under FCVE (`~/fcve`)

If the audit feeds an FCVE evidence package, use `fcve.py independent-check`
(it enforces the same PASS conditions and records the export sha256 and
axiom comparison) and follow its rules: ledger append-only; delivered runs
never edited; report *before* decision; a named human sets verdicts and
limitations; read the rendered PDF; make replayed runs self-contained. The
reasons are in `LESSONS.md` sections B–C.

## Quick reference

| Script | Answers |
|---|---|
| `source-inventory.sh <dir>` | file/theorem/def/axiom/unsafe counts (row 1 sanity, row 6 setup) |
| `sorry-audit.sh <dir>` | sorry/admit/native_decide counts + locations (rows 4-5) |
| `axiom-audit.sh <dir> <theorem>` | prints the `#print axioms` command to run (row 6) |
| `hash-manifest.sh <out> <paths...>` | SHA-256 manifest for the final evidence package |
| `setup-independent-checker.sh <tag> <dir>` | one-time: builds lean4export @ tag + nanoda_lib |
| `independent-check.sh ...` | export + independently check specific declarations (row 10); writes `results.tsv`, `tools.tsv`, stall samples |
| `export-literal-scan.py <file>` | longest nat literal in an export — the first thing to read on a stall |
| `patches/*.diff` + `NatReprCheck.lean` | fast-literal patches for lean4export and nanoda (opt-in via `FAST_LITERALS=1`) |

## Common mistakes (all observed directly, not hypothetical)

| Mistake | Why it happens | Fix |
|---|---|---|
| Counting vendored Mathlib source as the target's own | `grep -r` with `-h`/`-o` recurses into `.lake/packages/` and `-h` silently defeats a `grep -v` path filter | Use `--exclude-dir` at the traversal level, not a post-hoc `grep -v` |
| Trusting a README/AI-summary as current state | It's a snapshot frozen at whatever commit last touched it | `git log --oneline -- <file>` before citing it, every time, either direction of staleness |
| Blaming disk/memory pressure for an exporter stall | Swap growth is a real, measurable *co-symptom*, but a process at 100% CPU with zero output growth for minutes is making no progress regardless of free RAM | Profile it (`sample <pid>`) before assuming "more resources" fixes it |
| A background export dying silently within ~2 minutes | `nohup cmd &` from an agent-invoked shell only detaches from SIGHUP — the process group still gets reaped when that shell invocation returns | Launch with `setsid` or `Popen(start_new_session=True)`, then verify it's still alive on a second, later check |
| A disk/stall guard that "should" be running but silently stopped ticking | A watcher loop can survive while its ticks stop advancing, and "the guard is running" gets mistaken for "the guard is working" | Check the guard's own heartbeat (a live-updating tick counter) on every poll, not just that its process exists |
| Treating a zero-byte export as "stalled" | Loading a full Mathlib-based environment can legitimately take minutes before the first byte | Only count flat *nonzero* output as a stall; gate the zero-output phase with a wall-clock cap instead |
| Recording a stall's cause as fact when it was a guess | A hypothesis loses its label when copied ("likely memoization" → "root-caused") | `sample` first; write "hypothesis" next to any unverified cause; re-check inherited root causes before repeating them |
| A negative control that changed nothing | The tamper script matched no lines and the untouched file "passed" | Assert the modified-count > 0, *then* confirm rejection |
| Treating a tool error as a failed proof | A relative `--out` made the checker unable to open its config; result logged as FAIL | Distinguish FAIL / TOOL_ERROR / BLOCKED; use absolute paths |
| Reporting patched-tool results as if from upstream tools | The verdict looks identical | Disclose patches, keep diffs + tool hashes, validate (see *Patched tools*) |
| Reusing another run's evidence paths in a replay | Paths were relative to the old run dir; the report said "Not recorded" | Make each run self-contained; never modify the delivered run |
| Starting a large fetch without checking disk | Mathlib cache is ~9-10 GB; the volume filled and the agent's own tools failed | `df -h /` first; <5 GB free = stop and ask |

## Independent checker notes

`nanoda_lib` (github.com/ammkrn/nanoda_lib) checks Lean's `.export` text
format, produced by `lean4export` (github.com/leanprover/lean4export).
`lean4export` must be built at the **exact tag matching the target's
`lean-toolchain`** (it reads that Lean version's `.olean` binary format);
`nanoda_lib` itself is not toolchain-specific and only needs building once,
shared across every target you audit. Large exports can stall. The one diagnosed cause so far is **huge nat literals**
(tens of millions of digits in `decide`/`norm_num`-style proofs): quadratic
decimal printing in `lean4export` and quadratic parsing in `nanoda_lib` — see
*Triage: stalls* and *Patched tools*. An earlier note here blamed "a
memoization cache that's reset every call"; that was a hypothesis that turned
out not to be the cause (BUG-002). Export size alone (~70MB+) is not the trigger:
the VCE-001 headline export completes in about a minute once the literals are handled.
Another declaration may stall for a different reason — sample it; only a
stack-level diagnosis justifies "UNRESOLVED — tool limitation".

For the row-9 kernel-bug search, a starting list of Lean kernel bugs found via
formalization is in `LESSONS.md` (D22). Audit-method lessons from every run so
far are in `LESSONS.md`.
