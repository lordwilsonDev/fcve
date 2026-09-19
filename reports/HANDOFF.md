# Handoff: FCVE Build-Out (post-VCE-001/VCE-002)

## What this project is

`~/fcve` — the Formal Claim Verification Engine (FCVE). Read
`~/fcve/SPECIFICATION.md` first (62 sections, authored by Wilson) — it's the
governing spec for everything here. Also read the vault note
`~/Documents/Vault/10_Projects/BlackSwanLabz/BlackSwanLabz-FCVE-Spec.md` for
the project history in one place.

The one-sentence version: FCVE turns a mathematical claim into an auditable
evidence package (source integrity → claim extraction → semantic
normalization → Lean formalization → kernel proof → axiom audit → semantic
re-audit → adversarial/computational test → independent (non-kernel) check →
evidence graph → report → governance decision), and never collapses that
into a bare "VERIFIED = TRUE." The governance verdict is always one of
PROMOTE / REPAIR / REJECT / RESEARCH / STOP.

## What's already done — two full manual runs, by hand, per spec §60 step 1

**Do not repeat these.** They're complete, verified, and delivered as PDFs.

- **VCE-001** (`~/fcve/verification/`): audited Eliahou's 1993 Theorem 1.1
  (Collatz cycle-length bound), as formalized in
  `tangentstorm/eliahou-collatz-bounds`. Re-read the entire source paper from
  scratch, independently re-derived its actual three-case Farey-pair proof
  argument, and confirmed the Lean proof's *structure* (not just its final
  statement) is isomorphic to the source. Ran an independent Python
  recomputation of the continued-fraction convergents, which caught a real
  false-mismatch (a float64 precision artifact in the test itself) —
  root-caused and corrected, recorded in the correction ledger rather than
  silently fixed. 15-event hash-chained ledger, final graph hash
  `0c9330331753c8b8346704adba88b70867e4765f26a93c4b0bb22102031af10f`.
  **Verdict: REPAIR** — every layer clean except independent (non-kernel)
  checking, which is blocked for the headline theorem specifically by a
  disclosed, root-caused `lean4export` defect on large proof closures (5/9
  supporting lemmas passed independent check cleanly).
- **VCE-002** (`~/fcve/verification-002/`): a deliberately simple,
  self-authored contrast claim (`powers_of_two_reach_one`). Same pipeline,
  13-event ledger, final graph hash
  `66705d978fd014309bc8f2cde2af9fd8934a088e0b4650ce9ae2695925c00123`.
  **Verdict: PROMOTE** — every layer clean, including independent check
  (1,662 declarations, 0 errors).

Both have compiled PDF reports (`verification*/report/report.pdf`) with a
Trust Statement first, exactly two diagrams, a limitations table, and real
reproduction commands, per the spec's mathematician-facing report rules
(§27-34, §57).

## What this proves and what it doesn't

It proves the *methodology* works by hand, on two different outcomes
(REPAIR and PROMOTE), which is exactly what §60 step 1 requires before any
automation. It does **not** prove any tooling exists yet — every gate so far
was executed manually (a person/agent reading the source, writing the
normalized claim, running scripts, writing the receipt by hand). There is no
CLI, no orchestrator, no reusable "run all gates on a new claim" command.

## What's next, per the spec's own build order (§60)

```
1. VCE-001 manual execution        <- DONE (x2: VCE-001, VCE-002)
2. Evidence schema                 <- START HERE
3. Claim/assumption extraction
4. Lean execution wrapper
5. Axiom audit
6. Semantic comparison
7. Computational backend
8. Independent checker
9. Evidence graph
10. Automated receipt
11. Automated LaTeX report
12. Batch theorem execution
```

**Do not jump ahead to batch execution or full automation.** The spec is
explicit: "The first objective is not scale. It is proving that one complete
verification path works" — that's done; the next objective is making step 2
(evidence schema) solid before automating anything on top of it.

### Step 2: Evidence Schema — concrete starting point

Two scripts already exist and were used for both VCE runs:
- `~/fcve/scripts/append-event.py` — appends one hash-chained event to a
  ledger (`event-ledger.jsonl`)
- `~/fcve/scripts/build-evidence-graph.py` — derives the typed node/edge
  evidence graph (§20) from a ledger

These are the *seed* of the evidence schema, not the finished thing. Look at
both event ledgers (`verification/evidence/event-ledger.jsonl`,
`verification-002/evidence/event-ledger.jsonl`) and the two evidence graphs
to see what fields were actually needed in practice versus what §21/§25
specify, and reconcile any gaps — e.g. the spec wants an explicit
`EVIDENCE_CLASS` field (§21: SOURCE_ASSERTION, FORMAL_PROOF,
COMPUTATIONAL_TEST, etc.) on every node, which the current
`build-evidence-graph.py` does not yet emit (it infers a `type` from the
action name, which is related but not the same field). Fixing that gap is a
reasonable first concrete task.

### Known open items (don't silently resolve, ask or flag)

1. **Gate 12/13 naming ambiguity**: §8 claims "fourteen MVP gates" but only
   Gates 0-11 have explicit `## GATE N` headers in the spec; §53's pass
   condition references G12/G13. Both VCE runs used the resolution
   "Gate 12 = Report Generation, Gate 13 = Governance Decision" consistently,
   and it worked in practice, but Wilson has not explicitly confirmed this in
   the spec document itself. Don't silently change it; if you touch the
   numbering, flag it.
2. **Process-order lesson already learned once**: VCE-001 executed
   Governance Decision (Gate 13) *before* Report Generation (Gate 12),
   reversed from the spec's own canonical chain (§2: ...→ EVIDENCE GRAPH →
   HUMAN-READABLE REPORT → GOVERNANCE DECISION). This was caught, disclosed
   in VCE-001's correction ledger (not silently fixed), and VCE-002 ran the
   two gates in the correct order. Any automation of step 2+ must enforce
   this order structurally, not rely on a human remembering it.
3. **`EVIDENCE_CLASS` vs graph `type`** (see above) — same underlying
   confusion risk: a `COMPUTATIONAL_TEST` node must never be promotable to
   `FORMAL_PROOF` (§21's whole point). If you build tooling that merges or
   summarizes evidence, keep this distinction structurally enforced (e.g. a
   type system or explicit assertion), not just a comment.

## Ground rules carried over from this session's actual incidents (not hypothetical)

- **Check `df -h /` before any large download** (Mathlib olean cache, a new
  Lean toolchain). This machine hit 100% disk capacity once already this
  week from an unrelated cause; don't assume headroom.
- **A found computational "mismatch" needs verification before being trusted,
  exactly as much as a "PASS" does** — VCE-001's correction ledger has a
  concrete example (a false mismatch from float64 precision, caught by
  re-running at higher precision before accepting it).
- **Never trust a repo's own self-description** (README, AI-run summary,
  docstring) without checking `git log --oneline -- <file>` for staleness
  first — this is now baked into `~/.claude/skills/verifying-lean-proofs/`
  as a standing rule, and FCVE inherits it.
- **The event ledger is append-only by design.** Don't rewrite history to
  hide a mistake (a wrong gate order, a bad hash reference) — add a
  correction-ledger entry and move forward. This is a design principle
  (§46), not a suggestion.
- **A hash reference goes stale the moment the thing it points to changes**
  (e.g. rebuilding the evidence graph after adding more events changes its
  hash). Both VCE runs had to fix a receipt/report that cited a hash from
  before the run was actually finished — check this before calling a run
  complete.

## Definition of done for Step 2

A reusable evidence-schema module/library (Python, given the existing
scripts) that: (a) can be imported/called rather than invoked as a
standalone CLI per-event, (b) emits `EVIDENCE_CLASS` per §21 alongside the
existing node `type`, (c) validates gate ordering against the canonical
chain (§2) and refuses/warns on an out-of-order call (closing open item #2
above structurally), and (d) has been exercised against at least one of the
two existing ledgers to confirm it reproduces the same graph hash the manual
script produced (regression check — if it doesn't reproduce the same hash
for the same input, something about the schema changed in a way that needs
explicit acknowledgment, not silent drift).
