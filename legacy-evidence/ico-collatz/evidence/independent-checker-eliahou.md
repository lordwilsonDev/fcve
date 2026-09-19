# Phase 18 — Independent checker (nanoda) against `tangentstorm/eliahou-collatz-bounds`

Date: 2026-09-18
Target: `~/ico-collatz/targets/eliahou-collatz-bounds` @ `db804ce6305ea99a817f067869607f8b677d895a`
(Lean `v4.28.0`, Mathlib `v4.28.0`) — read-only throughout; `git status --short` clean at
start and end of this phase.

## Bottom line

An independent checker has now verified part of this target, and the rest is
blocked for a reason that is precisely characterised below.

| | |
|---|---|
| Paper-facing theorems independently checked and **PASS** | 5 of 9 |
| Requested headline theorem `results_eliahou_theorem_1_1` | **NOT independently checked — still BLOCKED** |
| T6 (kernel vulnerability) status | **still OPEN for the headline theorem** |
| Governance implication | unchanged: `RESEARCH`, not `PROMOTE` |

The headline theorem specifically — the one Phase 18 exists to discharge — did
**not** get an independent verdict. Nothing in this document should be read as
closing T6. What is new is that the remaining blocker is no longer "we ran out
of memory": it is a measured property of the reference exporter on this target's
largest proof terms, with a reproduction and a boundary.

## What was actually checked

Independent checker: **`nanoda_lib`** — an external type checker for Lean 4
written in Rust, i.e. a type checker that is *not* Lean's own kernel, reaching
the proof terms through Lean 4's NDJSON `.export` format.

| Component | Pinned at |
|---|---|
| `ammkrn/nanoda_lib` | commit `4c544ed4099c8227f07d5de77ad1e69fb0740a27` (2026-09-09), `nanoda_bin` 0.4.17 |
| Rust / cargo | `cargo 1.93.1 (Homebrew)` |
| `leanprover/lean4export` | tag `v4.28.0` (`d065b00`) — matches the target's toolchain |
| export format | `3.1.0` (nanoda supports `>= 3.1.0, < 3.2.0`) |
| export `meta` line | `{"exporter":{"name":"lean4export","version":"3.1.0"},"format":{"version":"3.1.0"},"lean":{"githash":"7e01a1bf5c70fc6167d49c345d3bf80596e9a79b","version":"4.28.0"}}` |

Method, per declaration, driven by `scripts/phase18-independent-check.sh`:

```bash
# 1. export that declaration's dependency closure from the read-only target repo
cd ~/ico-collatz/targets/eliahou-collatz-bounds
lake env ../lean4export/.lake/build/bin/lean4export Results -- <decl> > <decl>.export

# 2. independently type-check the whole exported closure
cd ~/ico-collatz/experiments/independent-checker/nanoda_lib
./target/release/nanoda_bin ../../../experiments/independent-checker/nanoda-config-<decl>.json
```

Each run is monitored for a free-disk floor and for output that has stopped
advancing; see "Blocked declarations" for what those guards caught.

## Results

| Declaration | Verdict | Checker | Export size | Declarations re-checked by nanoda | nanoda exit |
|---|---|---:|---:|---:|---:|
| `results_eliahou_product_formula` | **PASS** | nanoda_bin 0.4.17 | 50,667,171 B | 12,809 | 0 |
| `results_farey_pair_bound` | **PASS** | nanoda_bin 0.4.17 | 46,792,968 B | 12,012 | 0 |
| `results_eliahou_product_formula_real` | **PASS** | nanoda_bin 0.4.17 | 53,870,161 B | 13,639 | 0 |
| `results_eliahou_sandwich` | **PASS** | nanoda_bin 0.4.17 | 74,005,619 B | 17,320 | 0 |
| `results_log2_three_lt_ratio` | **PASS** | nanoda_bin 0.4.17 | 73,780,867 B | 17,301 | 0 |
| `results_rational_approx_bound` | BLOCKED | — | 70,582,272 B (incomplete) | — | — |
| `results_eliahou_bound` | BLOCKED | — | 70,807,552 B (incomplete) | — | — |
| `results_eliahou_bound_card` | BLOCKED | — | 70,840,320 B (incomplete) | — | — |
| `results_eliahou_theorem_1_1` | BLOCKED | — | 71,147,520 B (incomplete) | — | — |

Machine-readable equivalent: `experiments/independent-checker/phase18-results.tsv`.

### Verbatim checker output (all five PASSes)

For each passing declaration, nanoda's stdout ends with the same three admitted
axioms and the same success line. `results_eliahou_product_formula`, in full:

```
theorem results_eliahou_product_formula :
  forall {L : Nat} (c : CollatzCycle L),
  Eq
    (Finset.prod (CollatzCycle.oddIndices c)
      (fun (i : Fin L) => HAdd.hAdd (HMul.hMul (OfNat.ofNat 3) (CollatzCycle.seq c i)) (OfNat.ofNat 1)))
    (HMul.hMul (HPow.hPow (OfNat.ofNat 2) L)
      (Finset.prod (CollatzCycle.oddIndices c) (fun (i : Fin L) => CollatzCycle.seq c i))) :=
  _

axiom propext {a b : Prop} : Iff a b → Eq a b

axiom Quot.sound.{u} {α : Sort u} {r : α → α → Prop} {a b : α} : r a b → Eq (Quot.mk r a) (Quot.mk r b)

axiom Classical.choice.{u} {α : Sort u} : Nonempty α → α

Checked 12809 declarations with no errors
```

The other four print the same axiom set and their own success line:

```
results_farey_pair_bound:            Checked 12012 declarations with no errors
results_eliahou_product_formula_real: Checked 13639 declarations with no errors
results_eliahou_sandwich:            Checked 17320 declarations with no errors
results_log2_three_lt_ratio:         Checked 17301 declarations with no errors
```

Full transcripts: `experiments/independent-checker/<decl>.nanoda.stdout.txt`
(stderr holds `/usr/bin/time -l` resource figures; peak footprint was on the
order of 100 MB, so the checker itself is cheap — the exporter is the cost).

Two things this output establishes, beyond "it type-checked":

1. **The re-check covers the whole closure, not one theorem.** nanoda re-checked
   12,012–17,320 declarations per export — every constant in that closure, with
   nanoda's own checker, not just the named top-level theorem.
2. **The axiom set is independently corroborated.** nanoda's own list of admitted
   axioms is exactly `propext`, `Quot.sound`, `Classical.choice` — the same
   MATHLIB_STANDARD triple Phase 11 (`evidence/axiom-audit-eliahou.md`) reported
   from `#print axioms`. That is a second, differently-implemented route to the
   same claim, and it agrees.

Checker settings, disclosed because they bound the claim:
`nat_extension` and `string_extension` were **enabled** (Mathlib relies on Lean's
`Nat`/`String` kernel extensions); `permitted_axioms` was `["propext",
"Classical.choice", "Quot.sound"]`; `unpermitted_axiom_hard_error` was `false`,
so an unpermitted axiom would be skipped rather than abort the run, but *using*
one would still be a hard error — and no such error occurred. Per-declaration
configs are checked in as
`experiments/independent-checker/nanoda-config-<decl>.json`.

## Blocked declarations, and why

Four of the nine `Results`-level theorems could not be independently checked,
because their export never completed. The blocker is in the **reference
exporter**, not in the target, the checker, or the machine's resources.

Measured on `results_eliahou_theorem_1_1` (the requested headline theorem),
after freeing 5.4 GB of RAM specifically to rule resource pressure out:

* ~100 s in: 71,147,520 bytes / 1,336,962 lines / ~1.22 M expression nodes exported;
  11,020 theorems, 3,995 definitions, 533 inductives already emitted.
* then **zero further bytes across 8 min 34 s of accumulated CPU**, at 100% CPU.
* the process's RSS *fell* from 9.2 GB to 64 MB over that period, free disk held
  steady at ~5.6 GB, and swap did not grow. So memory and disk were not binding.
* the file ends mid-JSON-object (its last flushed byte is not a newline), and the
  declaration that was asked for is **absent from the output**:
  `grep -c results_eliahou_theorem_1_1` returns `0`. The exporter never reached it.

This is **reproducible, not incidental**: the scripted re-run of the same
command stopped at the byte-identical output size, 71,147,520 bytes, and was
aborted by the stall guard after 603 s (`rc=143`,
`reason=stalled-no-output`). Two independent runs, same command, same flat
offset — the export always reaches exactly this point and never moves past it.

`sample <pid>` puts the spinning process inside
`dumpConstant` → `dumpConstant_dumpDeps` → `dumpExprAux` (`Export.lean`) — that is
ordinary work, not a deadlock and not GC, which is consistent with the memory
profile above and inconsistent with "waiting on I/O or thrashing".

Working hypothesis for the mechanism (stated as a hypothesis, not a finding):
`getIdx` memoises into a `HashMap Expr Nat` keyed on structurally-compared `Expr`
values (`Export.lean:82`), while `dumpExpr` throws away the `noMDataExprs` cache
on every call (`Export.lean:229`). Cost then grows super-linearly in term size,
which is exactly what the flat-output-at-100%-CPU-with-flat-memory profile looks
like. The target's own `Collatz/LinearForm.lean` compiles to an 85 MB `.olean`
(against ~100 KB–1 MB for a typical Mathlib file), i.e. this repo does contain
unusually large proof terms — consistent with commit `db804ce`'s own note about
"`norm_num` powers".

**The boundary is closure shape, not a specific tactic.** `Real.logb` is present
in two theorems that passed (`results_eliahou_sandwich` in 120 s,
`results_log2_three_lt_ratio` in 181 s), so the earlier guess that analysis
machinery / `Real.logb` was the problem is wrong. What the four blocked theorems
share is a dependency on `rational_approx_bound` — the declaration carrying the
large numeric reasoning (`2^40`, `17,087,915`, `85,137,581`) — and each of the
three attempted aborts died in the same way as the headline one.

Reproduce any blocked row with:

```bash
bash scripts/phase18-independent-check.sh results_rational_approx_bound
# monitor log: experiments/independent-checker/results_rational_approx_bound.monitor.log
```

### A guard artefact that must not be read as evidence

The first `results_eliahou_bound_card` row in `phase18-results.tsv` shows
`out_bytes=0`. That abort was produced by the stall guard firing during the
*environment load*, before a single byte had been emitted, so **that row is not
evidence that the export stalled** — it may simply have been slow to start under
memory pressure. The guard was fixed to count stall only after the first byte
(`scripts/phase18-independent-check.sh`), and the row was re-run. The corrected
run emitted 70,840,320 bytes before going flat and aborting at 685 s, which is
a genuine mid-stream stall.

The superseded row was left in the TSV rather than edited out, because
`phase18-results.tsv` is an append-only log of what the driver actually
recorded, so the row for this declaration appears twice: the superseded
`out_bytes=0` abort first (322 s), then the corrected run (685 s / 70,840,320 B)
immediately below it. Only the second is a finding. This is called out rather
than smoothed over because a guard artefact that looks like a finding is worse
than no finding.

## What this does and does not establish

Does establish:

* Five of the nine paper-facing `Results`-level theorems — including
  `results_eliahou_sandwich`, the Theorem 1.1 sandwich argument itself — have been
  re-type-checked by a checker that is not Lean's kernel, over their entire
  exported dependency closures, with no errors, and with the expected axiom set.
* The reference export→independent-check pipeline works end to end on this
  target: `lean4export` at the target's own `v4.28.0`, format `3.1.0`, checked by
  `nanoda_bin` 0.4.17.
* The remaining blocker is localised and reproducible, with a measured signature.

Does **not** establish:

* **Any independent verdict on `results_eliahou_theorem_1_1`.** This is the
  theorem Phase 18 exists for. It remains unverified by any second checker, so
  T6 remains open for it, and the audit's honest governance state stays
  `RESEARCH`.
* Independence from Lean's *parser*. nanoda checks the proof terms, but it
  receives them through Lean's own `.olean` reader and `lean4export`, so a shared
  parsing/elaboration defect is not excluded by this evidence. The independence
  here is at the type-checking/kernel layer, which is the layer T6 concerns.
* Anything about the target's *mathematics*. Whether the Lean statement says what
  Eliahou's paper says is Phase 12's job (`evidence/semantic-audit-eliahou.md`);
  an independent checker has no opinion on it.
* That `nanoda` is itself correct. T7 (independent-checker vulnerability) is not
  discharged by using a second checker — nanoda is a different implementation in
  a different language, so it does not inherit Lean's nested-inductive kernel bug
  by construction, but it carries no proof of its own correctness. This is a
  strictly different failure mode, not the absence of one.

## The `lean4lean` route was examined and declined

The handoff offered `digama0/lean4lean` (an independent Lean 4 kernel written in
Lean 4) as option 2. It was not taken, because it cannot reach this target's
oleans at the version they were built with:

* No `lean4lean` revision exists pinned to Lean **`v4.28.0`**. Its `lean-toolchain`
  history steps `v4.26.0` → `v4.29.0` → `v4.30.0` → `v4.31.0` → `v4.32.2` →
  `v4.33.0-rc2`; `main` pins `v4.33.0-rc2` and requires `batteries v4.33.0-rc2`.
* `lean4lean` loads oleans through Lean's own importer
  (`Lean4Lean/Replay.lean:298`, `importModulesCore`), so it can only check a
  project compiled by a Lean it was built against — which rules out pointing a
  newer build at this target's `v4.28.0` oleans.

Had it been used, the write-up would have had to say plainly that lean4lean is
"derived directly from the C++ kernel implementation" and therefore "likely
shares some implementation bugs with it" — its own README's words — which is a
weaker independence claim than the Rust checker that was used instead.

## Preconditions and side effects of this run

* Free disk before the heavy steps: 3.9 GB (below this project's own 5 GB rule).
  Recovered to 5.2 GB by deleting the orphaned `~/try-omarchy` leftovers (1.3 GB)
  from the already-removed Omarchy VM. Every export ran with a 1.5 GB free-disk
  abort floor armed.
* RAM: Ollama's `llama-server` was holding 6.2 GB (7,735 MB wired on a 16 GB
  machine, 163 MB unused). It was stopped with the user's approval, freeing
  5.4 GB. As recorded in `receipts/correction-ledger.md`, this did **not** fix
  the export and was not the cause — the stall is unrelated to RAM. The memory
  was still worth freeing, because it removed a genuine disk-exhaustion risk
  from swap growth.
* The aborted 68 MiB partial export is retained as
  `results_eliahou_theorem_1_1.export`, which is clearly not a valid input: it is
  incomplete, ends mid-JSON-object, and does not contain the declaration it was
  asked for. No incomplete export was ever fed to the checker — the driver
  requires a newline-terminated file containing the requested declaration's name
  before it will invoke nanoda.
* Nothing under `targets/eliahou-collatz-bounds` was modified.

## Artifacts

| Path | Contents |
|---|---|
| `scripts/phase18-independent-check.sh` | export + independent-check driver for one or more declarations |
| `scripts/phase18-export.sh` | export-only runner (kept for the single-declaration attempt) |
| `experiments/independent-checker/phase18-results.tsv` | machine-readable verdict matrix |
| `experiments/independent-checker/<decl>.export` | completion-checked export fed to nanoda |
| `experiments/independent-checker/nanoda-config-<decl>.json` | checker config used, per declaration |
| `experiments/independent-checker/<decl>.nanoda.stdout.txt` | full checker output |
| `experiments/independent-checker/<decl>.monitor.log` | per-tick disk / output-growth trace |
| `experiments/independent-checker/results_eliahou_theorem_1_1.export` | the aborted headline export — incomplete, ends mid-JSON, target declaration absent |
| `experiments/independent-checker/sample-5442.txt` | stack sample of the stalled exporter |
| `experiments/independent-checker/nanoda_lib/` | checker at commit `4c544ed4` |

## Re-run (guard fixed)

Two declarations were re-run after the stall guard was corrected to count stall
only after the first byte of output:

| Declaration | Verdict | Seconds | Bytes emitted before flat | Abort reason |
|---|---:|---:|---:|---|
| `results_eliahou_bound_card` | BLOCKED | 685 | 70,840,320 | `stalled-no-output` (rc=143) |
| `results_eliahou_theorem_1_1` | BLOCKED | 603 | 71,147,520 | `stalled-no-output` (rc=143) |

Both are genuine mid-stream stalls: each emitted tens of megabytes, then produced
nothing for fifteen consecutive 20-second ticks while the process stayed alive,
which is what the guard keys on. Neither reached the declaration it was asked
for.

The headline re-run is the important one. It reproduced the earlier manual
attempt's output size **exactly** — 71,147,520 bytes — and its trapped offset is
raw evidence rather than a summary: the aborted export ends mid-JSON-object, and
`grep -c results_eliahou_theorem_1_1` on it returns `0`.

Per-declaration abort traces:
`experiments/independent-checker/results_eliahou_bound_card.monitor.log`,
`experiments/independent-checker/results_eliahou_theorem_1_1.monitor.log`.

### Aftermath

The blocked runs leave an incomplete `.export` per declaration. None of them was
fed to nanoda — an incomplete export cannot produce a verdict, and it is
`scripts/phase18-independent-check.sh` that enforces this by requiring the file to
end on a newline and to contain the requested declaration's name before it will
invoke the checker at all. The freed disk after the full matrix was ~4.8 GB free.

## Governance reading

`RESEARCH`, unchanged. Five of nine paper-facing theorems now carry an
independently-checked PASS, which is a real strengthening of Phases 7-15. The
theorem that Phase 18 was commissioned to establish — `results_eliahou_theorem_1_1`
— is not among them, and T6 therefore stays open for it. The audit does not get to
convert "the adjacent theorems check out" into "the headline theorem checks out";
those are different claims, and only the first is evidenced here.
