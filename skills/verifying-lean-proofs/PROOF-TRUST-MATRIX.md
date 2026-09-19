# Proof Trust Matrix (template)

Copy this table into the audit output and fill in every row. No row may be
left blank or marked green without a specific artifact (file, log, command
output) backing it. "Compiles" answers none of these rows by itself.

| # | Gate | PASS criteria | Evidence file |
|---|---|---|---|
| 1 | Source pinned | exact commit hash recorded | — |
| 2 | Toolchain pinned | `lean-toolchain` + Mathlib rev recorded, compared against your own control environment for drift | — |
| 3 | Clean rebuild | `lake exe cache get && lake build` succeeds, unmodified. State whether this was from a from-empty clone (stronger) or an existing `.lake` cache (weaker — disclose it) | build log |
| 4 | No `sorry`/`admit` | `scripts/sorry-audit.sh <target>` reports 0 for both | sorry-audit output |
| 5 | No `native_decide` (or disclosed if present) | same script; if present, decide whether it's acceptable for this claim | sorry-audit output |
| 6 | Axiom footprint | `#print axioms <theorem>` on every headline theorem; classify each axiom KERNEL_STANDARD / MATHLIB_STANDARD / CLASSICAL / PROJECT_AXIOM / EXTERNAL_AXIOM | axiom-audit output |
| 7 | Semantic correspondence | the Lean statement is read against the actual claim (paper, spec, issue) line by line — MATCH / PARTIAL MATCH / MISMATCH / UNCLEAR | written comparison, not a summary |
| 8 | Self-description checked for staleness | any README/AI-summary/docstring describing "what this proves" is checked against `git log --oneline -- <file>` before being cited | git log output |
| 9 | Kernel vulnerability exposure | is the pinned Lean version affected by any known kernel soundness issue? Check release notes between the pinned version and current (needs web access — mark UNRESOLVED, not silently skipped, if unavailable) | version comparison + release-notes citation |
| 10 | Independent check | a second, differently-implemented checker (not the same Lean kernel) verifies the headline theorem's exported closure. PASS needs **all** of: complete export; checker exit 0; "Checked N declarations with no errors" with N > 0; the target declaration printed by the checker; the checker's axiom set equal to row 6. Tool errors are not FAIL; a stall is not "incompatible" until it has a stack-level diagnosis (see SKILL.md, Triage). If patched tools were used, that is disclosed and validated (SKILL.md, Patched tools) | independent-check.sh results.tsv + tools.tsv + raw nanoda/checker stdout |

## Verdict (pick exactly one, state why)

- **TRUSTED** — all 10 rows pass with evidence.
- **PROVISIONAL** — rows 1-8 pass; row 9 or 10 has a disclosed, bounded gap
  (e.g. old kernel version but no plausible attack vector; independent checker
  blocked by a known tool limitation, not skipped).
- **UNRESOLVED** — a row could not be evaluated (e.g. couldn't rebuild, couldn't
  reach the paper). Say which row and why, don't guess.
- **REJECTED** — any row actively fails (sorry present and undisclosed, axiom
  smuggled in, statement doesn't match the claim, rebuild fails).

Never write "proved" as a bare verdict. Write which of the four states, and
list the specific row(s) that keep it out of TRUSTED.

**Provenance of your verdict is part of the verdict.** Record which tool builds produced rows 6 and 10 (`tools.tsv`), whether any were patched, and which rows were captured after the run rather than during it. Lessons behind these rules: `LESSONS.md`.
