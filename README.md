# FCVE — Formal Claim Verification Engine

FCVE turns a mathematical claim into an **auditable evidence package** instead of a one-word "verified". It walks a claim
through a fixed chain of gates and records what each one actually showed:

```
source → claims → normalization → Lean formalization → build → axiom audit → semantic re-audit
       → computational tests → independent check → evidence graph → report → governance decision
```

It never collapses that chain to "VERIFIED". The report states what the recorded evidence *permits*; the decision
(PROMOTE / REPAIR / RESEARCH / …) is made afterwards, by a named human, and lives in the receipt. Spec: [`SPECIFICATION.md`](SPECIFICATION.md).

## Status — read this first

- All twelve steps of the spec's build order (§60) exist as code, with 12 test suites in [`tests/`](tests/).
- It has been run on **two real theorems and some fixtures**, by one person. It has not been used at scale, on a real
  Mathlib project through `batch-run`, or by anyone else.
- The tool checks **completeness and consistency**. Semantic judgments (claim extraction, whether the Lean statement means what the paper says,
  bridge verdicts, limitations, the final decision) are human. A model may draft them; it must not certify its own draft.
- The ledger is **tamper-evident, not tamper-proof**: hash-chained and append-only, but stored locally and unsigned.
- Reproducibility levels are ceilings supported by *recorded* evidence. Nothing is re-run to earn a level.

## What has been run

| Claim | Delivered | Corrected revisions | Decision |
|---|---|---|---|
| **VCE-001** — Eliahou, Theorem 1.1 (a bound on the length of a nontrivial Collatz cycle; it does **not** resolve the conjecture) | [`verification/`](verification/) | [rev r](deliverables/VCE-001-rev-r/) (REPAIR), [rev s](deliverables/VCE-001-rev-s/) | **PROMOTE** (rev s) |
| **VCE-002** — every power of two reaches 1 under the Collatz map | [`verification-002/`](verification-002/) | [rev r](deliverables/VCE-002-rev-r/), [rev s](deliverables/VCE-002-rev-s/) | **PROMOTE** (rev s) |

Delivered runs are never edited. Corrections are new runs beside them, with the earlier runs, attempts and superseded reports kept.
Each issued package in [`deliverables/`](deliverables/) has an `ISSUE-NOTE.md` (what it supersedes and its stated limitations) and a `MANIFEST.sha256`.
The limitations are part of the result — read them before relying on a package.

## Quick start

Requires Python 3, `git`; Lean/`lake` (via `elan`) for the Lean gates; `tectonic` for reports; `cargo` for the independent checker.

```bash
python3 scripts/fcve.py -h                       # all subcommands
python3 scripts/fcve.py verify  <run>/evidence/event-ledger.jsonl        # hash chain + gate order
python3 scripts/fcve.py receipt-check <ledger> <receipt.json>            # is the receipt current with the ledger?
python3 scripts/fcve.py batch-plan <manifest.json>                       # read-only status of every theorem

for t in evidence claims lean axioms semantic compute independent graph receipt report batch limits; do
  python3 tests/test_fcve_$t.py 2>&1 | tail -1; done                    # Lean/batch tests need lake + the pinned toolchain
```

Subcommands: `append verify validate-claims scaffold lean-build axiom-audit semantic-check scaffold-semantic compute-run independent-check
batch-plan batch-run report receipt receipt-check scaffold-limitations limitations-check repro-snapshot graph graph-check graph-view`.

## Layout

| Path | What |
|---|---|
| `scripts/` | `fcve.py` (CLI) plus one module per gate. `append-event.py` / `build-evidence-graph.py` are the original manual scripts, kept only so the delivered runs' hashes reproduce. |
| `tests/` | one suite per module |
| `verification*/` | runs: delivered (`verification`, `verification-002`), corrected (`-001r`, `-001s`, `-002r`, `-002s`), and superseded first attempts |
| `deliverables/` | issued packages: report (PDF + tex), receipt, decision note, correction ledger, full ledger, manifest |
| `reviewed-records/` | human-confirmed records: bridge verdicts, reviewer limitations, VCE-001 claims clean-up and repro snapshot |
| `proposed-records/` | drafted, **not** confirmed (e.g. the VCE-002 reproduction snapshot) |
| `tool-patches/` | the two patches behind VCE-001's independent check (below) |
| `skills/verifying-lean-proofs/` | snapshot of the Lean-proof audit skill: trust matrix, `audit.sh` one-command audit, lessons, bug log, worked examples |
| `independent-checks/` | raw results of extra independent-check runs |
| `HANDOFF.md` | current state, decisions made, open items — start here when resuming |

## The independent-check finding

VCE-001's headline proof was recorded as "independent checker incompatible: `lean4export` stalls (memoization bug)". That was a hypothesis
repeated as fact. Sampling the stalled process showed the real cause: **quadratic decimal conversion of natural-number literals of up to
25.6 million digits** — in the exporter (printing) and then in the checker (nanoda, parsing). Two small patches
([`tool-patches/`](tool-patches/)) fix it; the theorem then checks (17,464 declarations, axioms matching the Lean audit), a corrupted literal is
still rejected, and earlier passes reproduce. Upstream PRs:
[`leanprover/lean4export#52`](https://github.com/leanprover/lean4export/pull/52),
[`ammkrn/nanoda_lib#36`](https://github.com/ammkrn/nanoda_lib/pull/36) — open, not merged. **A verdict from patched tools is disclosed as a
limitation in the VCE-001 rev s report.** The patched builds exist only on the recording machine; the diffs are what a third party needs.

## Known limits

- Disk: real Lean builds need ~3 GB free (the wrapper refuses below it) plus ~2.5 GB per Lean toolchain and ~9–10 GB for a Mathlib cache.
- Repository/commit facts for these runs were **captured after the runs**; they identify the source as it is now, not proof of what was built then.
  Source PDFs of third-party papers are not in this repo (`.gitignore`); their hashes are recorded in each ledger.
- Written and tested on macOS (Apple silicon). Linux is untested.
- Compiled with `tectonic`, not the `pdflatex` the spec names; each compile record says so.
- No license has been chosen yet.

## Rules of the house

1. The ledger is append-only. Fix a mistake by appending a superseding event and a correction entry — never by editing. Archive, don't delete.
2. Never modify a delivered run. Regeneration goes to a new run.
3. Order: evidence graph → report → *then* the decision.
4. A named human sets verdicts and limitations; models render as PROPOSED.
5. Read the rendered PDF before trusting or issuing a report — most real bugs here were found that way, not by tests.

More detail on these and on what went wrong along the way: [`HANDOFF.md`](HANDOFF.md) and [`skills/verifying-lean-proofs/LESSONS.md`](skills/verifying-lean-proofs/LESSONS.md).
