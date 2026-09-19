---
project_id: ico-collatz
question_id: ico-collatz-q1
researcher: Wilson (wilsonlord241@gmail.com)
repository: ~/ico-collatz
commit: (not yet a git repo)
lean_version: 4.34.0
mathlib_version: 5ed2965256430c3649e86755f9576b54eca72435
os: Darwin 25.6.0 arm64
created: 2026-09-18
updated: 2026-09-18
status: PHASE_18_PARTIAL_5_OF_9_INDEPENDENTLY_CHECKED_HEADLINE_BLOCKED
---

# Project Status

## Phase gate table

| Phase | Name                              | Status |
|------:|------------------------------------|--------|
| 0     | Project initialization             | DONE |
| 1     | Environment baseline               | DONE (GREEN) |
| 2     | Control project                    | DONE (GREEN) |
| 3     | Toolchain trust baseline           | DONE |
| 4     | Threat model                       | DONE |
| 5     | Learning baseline                  | SCAFFOLDED |
| 6     | Mini proof lab                     | IN PROGRESS |
| 7     | Target repository intake           | DONE — see receipts/target-eliahou-collatz-bounds.md |
| 8     | Reproduce before modifying         | DONE (GREEN) — see receipts/phase8-reproduction.md |
| 9     | Source inventory                   | DONE — evidence/source-inventory-eliahou.md (7 files, 61 theorems/lemmas, 7 defs, 0 axioms, 0 unsafe) |
| 10    | `sorry` audit                      | DONE — evidence/sorry-audit-eliahou.md (0 sorry, 0 admit, 0 native_decide — corroborates README's self-reported claim) |
| 11    | Axiom audit                        | DONE — evidence/axiom-audit-eliahou.md. All 3 headline theorems depend only on `propext`, `Classical.choice`, `Quot.sound` (MATHLIB_STANDARD). No PROJECT_AXIOM/EXTERNAL_AXIOM. |
| 12    | Mathematical semantics audit       | DONE — evidence/semantic-audit-eliahou.md. MATCH on map, coefficients, nontriviality, and the Card Ω / L injectivity bridge. |
| 13    | Collatz formalization map          | DONE (folded into Phase 12 — `collatzComp` confirmed identical to paper's T(n)) |
| 14    | Target theorem classification      | DONE — BOUNDED RESULT (cycle-length lower bound), NOT the Collatz conjecture itself. See receipts/target-eliahou-collatz-bounds.md. |
| 15    | Positive-deviance search           | DONE — see below |
| 16    | Mechanism generation               | PENDING |
| 17    | Adversarial verification           | PARTIAL — Attack H (kernel vulnerability) run and documented as OPEN; A/D/E/F folded into Phases 8/11/10/12. T6 remains open for the headline theorem — Phase 18 did not cover it. |
| 18    | Independent checker                | PARTIAL — 5 of 9 `Results`-level paper-facing theorems independently **PASS** under `nanoda_bin` 0.4.17 (Rust external checker, not Lean's kernel) over their entire exported dependency closures, with the MATHLIB_STANDARD axiom set. The other 4 — including the requested `results_eliahou_theorem_1_1` — are BLOCKED by a reproducible `lean4export` stall on this target's largest proof terms, measured after freeing 5.4 GB specifically to rule resources out. See evidence/independent-checker-eliahou.md |
| 19    | Proof trust matrix                 | TEMPLATED |
| 20    | Discriminating predictions         | PENDING |
| 21    | Bounded intervention               | PENDING |
| 22    | Measurement plan                   | DEFINED |
| 23    | Capability metric contract         | TEMPLATED |
| 24    | Governance decision                | PENDING |
| 25    | Correction ledger                  | TEMPLATED |
| 26    | Reproducibility package            | PENDING |
| 27    | Evidence chain                     | TEMPLATED |
| 28    | LaTeX report                       | SKELETON CREATED |
| 29    | LaTeX figures                      | PENDING |
| 30    | LaTeX compilation                  | PENDING |
| 31    | Receipts                           | TEMPLATED |
| 32    | Hashing                            | SCRIPTED, NOT RUN |
| 33    | Final package                      | PENDING |
| 34    | Final green gate                   | PENDING |
| 35    | Final claim discipline             | PENDING (doctrine only) |

## Environment

See [receipts/environment.md](receipts/environment.md) — Lean/Lake/Mathlib pinned,
control project builds clean, trivial + Mathlib-backed theorem kernel-checked
(8924/8924 jobs).

## Disk discipline note

2026-09-18: root volume hit 100% capacity (109MB free) mid-Mathlib-cache-fetch due to
an unrelated 19GB "Try Omarchy" VM. Removed (app, VM data, LaunchAgent, sync scripts).
Recovered to 15GB free. Any future large dependency fetch (new Mathlib revision for the
target repo, a second checker toolchain) should re-check `df -h /` first and stop if
free space drops below ~5GB.

2026-09-18 (Phase 18): started the heavy exports at only 3.9GB free. Recovered to 5.2GB by
deleting the orphaned `~/try-omarchy` leftovers (~1.3GB) from the already-removed Omarchy
VM, and armed a 1.5GB free-disk abort floor on every export. Free disk never went below
~5.2GB during any Phase 18 run.

## Open decisions

- Target repository: `tangentstorm/eliahou-collatz-bounds` (per blueprint). Cloned at
  `db804ce6305ea99a817f067869607f8b677d895a` (Lean `v4.28.0`, Mathlib `v4.28.0`); Phases 7-15
  are complete against that exact commit. (This bullet previously still read "not yet
  cloned — proceeding to Phase 7 now" after Phase 7 was done; corrected 2026-09-18.)
- Independent checker (Phase 18): `nanoda` settled — `nanoda_lib` `4c544ed4`,
  `nanoda_bin` 0.4.17, driven by `lean4export` v4.28.0 (format 3.1.0). Five of the nine
  `Results`-level theorems now have an independent PASS. The requested headline theorem
  does not, and `lean4lean` is not a viable substitute on this target (no revision is
  pinned to Lean v4.28.0, and it reads oleans through Lean's own importer).
- Remaining blocker is now tool-side, not resource-side: the reference exporter stops
  emitting on the headline theorem's closure (~71MB, then 0 bytes at 100% CPU, declaration
  never reached). Fixing or replacing the exporter for large terms is the open question.

## Next step

Phase 18 is now PARTIAL, and the open question has changed shape. The export→
independent-check pipeline is proven to work on this target (five paper-facing
theorems, including the `Real.logb` sandwich argument, each re-checked across
12,012-17,320 declarations by a Rust checker with the expected axiom set). What
fails is the exporter, on the closure of `rational_approx_bound` and everything
depending on it — which includes the requested `results_eliahou_theorem_1_1`.

The earlier diagnosis in this file ("more free RAM is the more likely fix") was
wrong and has been struck: 5.4GB was freed, and the export stalled identically,
with RSS *falling* to 64MB and no swap or disk growth. `sample` shows 100% CPU
inside `dumpConstant`/`dumpExprAux`, i.e. work that is not making progress.

Concrete options, in order of expected value:
1. **Avoid the exporter's DAG walk for the large closure.** The suspected cause is
   memoisation keyed on structurally-compared `Expr` values plus a per-call cache
   reset (`Export.lean:82`, `Export.lean:229`). A patched or replacement exporter
   that only changes *speed* would unblock the headline theorem; any such patch
   must be disclosed in the evidence chain, since the export it produces is then
   not from the unmodified reference tool.
2. **Check the target under a Lean version that has both an exporter and a second
   checker.** The target's own `v4.28.0` pin is what makes this hard: the exporter
   must match it, and no `lean4lean` revision does. This needs a compatible
   Mathlib olean set (~9-10GB), which disk does not currently allow.
3. **Document and stop.** Accept an audit whose T6 remains open for the headline
   theorem, with the blocker precisely characterised as above.

Until the headline theorem has an independent verdict, the honest governance
state (Phase 24) is RESEARCH, not PROMOTE — everything else (Phases 7-15) is
clean, and five of nine paper-facing theorems now carry independent checks, but
the specific theorem this audit exists to establish is explicitly open, not
silently passed.
