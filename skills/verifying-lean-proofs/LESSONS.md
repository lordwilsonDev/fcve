# Lessons from real audits

Audit-method lessons, each from something that actually went wrong, with where the full record lives. (Bugs in *this
skill's own scripts* are in `BUGS.md`; this file is what the audits taught about how to run them.) Sources:
`~/ico-collatz/receipts/correction-ledger.md` (Phase 18, 2026-09-18) and the FCVE correction ledgers in `~/fcve/`
(VCE-001 / VCE-002 runs, 2026-09-19).

## A. Diagnosing tool stalls and failures

1. **A stall is a symptom, not a diagnosis. `sample <pid>` before you name a cause.** The VCE-001 Gate 9 stall was recorded as
   a "memoization cache reset" bug for a day; one stack sample would have shown `Nat.reprFast → toDigitsCore → gmpn_divrem_1`
   — quadratic decimal conversion of nat literals up to 25.6M digits. The hypothesis was labelled a hypothesis in one file and
   became "root-caused" in three others. *A hypothesis that gets copied without its label becomes a fact.* (BUG-002)
2. **Fixing one end can move the stall to the other.** The exporter *prints* the literal quadratically; the checker *parses* it
   quadratically. After the exporter was fixed, nanoda stalled next (`BigUint::from_str_radix` at 100% CPU). Re-sample after each fix.
3. **Don't blame the machine by reflex.** Freeing 5.4 GB of RAM did nothing (Phase 18): 100% CPU with zero output growth is no
   progress whatever the free memory. Swap growth was a co-symptom. Disk-only guards miss OS swap growth.
4. **A guard that is installed is not a guard that is working.** A monitor loop went silent while its process stayed alive.
   Check the tick counter advancing on every poll; make every run write an END line (its absence is a signal).
5. **Detach long jobs properly.** `nohup cmd &` from an agent shell still gets reaped. Use `Popen(start_new_session=True)`
   (macOS has no `setsid`) and confirm it survives a second, later check.
6. **Zero output is not a stall** (loading Mathlib takes minutes); only flat *non-zero* output is. Gate the zero phase with a wall clock.
7. **A tooling error is not a verdict.** A relative `--out` made nanoda fail to open its config; the script recorded `FAIL`. That
   says nothing about the proof. The script now reports `TOOL_ERROR` vs `FAIL` (proof rejected) vs `BLOCKED` (no verdict). (BUG-003)
8. **Name the executable path, not the product, when asking to touch a process.** The memory hog was Ollama's `llama-server`,
   not LM Studio's, inferred from the process name.

## B. Trusting your own patches and checks

9. **A negative control must be proven to perturb something.** The first corrupted-literal test changed 0 lines and "passed"
   (the unmodified file checked fine). Assert `modified_count > 0` before believing a control, then confirm it is *rejected*.
10. **When you patch a checker, validate the patch three ways:** (a) output identical to the original wherever the original got
    to (byte-prefix compare); (b) regression — everything that passed before still passes with identical counts; (c) a negative
    control that is rejected. Keep the diffs and record tool hashes. A verdict from patched tools must be disclosed.
11. **"Checked N declarations with no errors" needs company:** exit 0, N > 0, the target declaration actually printed, and the
    axiom set equal to your own `#print axioms` result. The script/exit code alone is not evidence.
12. **Numeric spot-checks need arbitrary precision.** A float64 compare of `p16/q16 < log2 3` (they agree to ~16 digits — that is
    what makes it a convergent) produced a false MISMATCH. Verify a *found* discrepancy as hard as a clean pass; use mpmath.
13. **Numbers 100x off the visible scale are a trigger to distrust the tool** (161,075 "theorems" in a 7-file repo = grep
    recursed into vendored Mathlib). Use `--exclude-dir`, never a post-hoc `grep -v` when `-h`/`-o` is on.

## C. Records, provenance, and self-description

14. **Any repo/AI summary is a claim, not evidence.** `ARISTOTLE_SUMMARY.md` described a superseded state; `git log -- <file>`
    before citing. This applies to your own status files too — re-read `PROJECT_STATUS.md` against its own phase table.
15. **Capturing repo/commit/toolchain after the run does not prove what the run built.** Say "captured after the run" in the
    report. A project with no commit or only local commits cannot be reproduced from a report; commit and push *before* auditing.
16. **Never edit a delivered record; supersede it.** Append a superseding event and a correction entry; archive, don't delete.
    Order matters: evidence graph → report → *then* decision. VCE-001's decision was logged before its report; that is disclosed, not hidden.
17. **A replayed run must be self-contained.** Replaying events whose evidence paths were relative to another run dir made the
    report print "Not recorded" and drop reproducibility to R0. Copy the referenced evidence into the new run (delivered files stay untouched).
18. **Read the rendered PDF.** Most FCVE bugs (false "none recorded", circular G12 blocker, literal `\S 53`, dangling graph edges,
    "commit not recorded" beside a listed commit) were found by reading output, not by tests. Tectonic exits 0 while dropping glyphs.
19. **Typed ids need checking at write time.** A decision event with mistyped input ids named nothing and silently produced dangling
    graph edges. `append` now refuses an input id no earlier event produced.
20. **Extraction notes are data.** Working prose left in a claims file ("closed-open-ish", a K(2^39)/K(2^40) mix-up) shipped in a
    delivered extraction. Clean extractions against the source before Gate 1 is recorded.

## D. Environment

21. **Check `df -h /` before a large fetch; under 5 GB free is a stop condition.** A Mathlib cache fetch exhausted the volume at
    41%, and the agent's own Bash tool stopped (ENOSPC). Use the terminal tool to diagnose; ask before deleting anything large.
22. **Kernel-bug exposure (row 9) has a starting list.** Bugs found in the Lean kernel through formalization (lean4lean):
    the `hasLooseBVars` soundness discussion on Zulip (channel 270676-lean4), `leanprover/lean4#10475`, `#10511`.
    Check the target's pinned version against these and the release notes; mark UNRESOLVED if you can't.
23. **Independence has layers.** A second *checker* is independent of Lean's kernel; it is not an independent *reviewer*. Semantic
    judgments (bridge verdict, limitations, decision) stay with a named human; a model may draft, never certify its own draft.
