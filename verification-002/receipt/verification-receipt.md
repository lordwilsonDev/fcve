# Verification Receipt — VCE-002

| Field | Value |
|---|---|
| THEOREM ID | CLAIM-002 (`powers_of_two_reach_one`, self-authored demonstration claim) |
| SOURCE HASH | `97d49fbc3576e79f3901ce85f0fb9dd92d9cbf06d6beb933aada6a2f1a194d60` (SHA-256, `source/original.md`) |
| CLAIM | For $f(n)=n/2$ (even) or $3n+1$ (odd), every $k\ge0$: $\exists m,\ f^{(m)}(2^k)=1$ |
| NORMALIZED CLAIM | `normalized/normalized-claim.md` — MATCH |
| LEAN STATEMENT | `powers_of_two_reach_one` in `IcoCollatzVerification/PowersOfTwoReachOne.lean` (our own control project, `~/ico-collatz/ico_collatz_verification`) |
| LEAN VERSION | Lean 4.34.0 |
| MATHLIB VERSION | master commit `5ed2965256430c3649e86755f9576b54eca72435` |
| BUILD RESULT | PASS — 8924/8924 jobs, exit 0, no `sorry`/`admit` |
| AXIOM FOOTPRINT | `propext`, `Quot.sound` only — **no `Classical.choice`**, fully constructive |
| SEMANTIC MATCH | MATCH (Gate 4) and no undisclosed change on re-audit (Gate 7) |
| INDEPENDENT CHECK | **PASS** — `nanoda_bin` 0.4.17 checked 1,662 declarations, 0 errors, axioms match exactly |
| COMPUTATIONAL TEST | SUPPORTIVE — independent Python brute-force check across k=0 (minimal case) through k=1000 (large parameter), all reaching 1 in exactly k steps as predicted |
| COUNTEREXAMPLE SEARCH | NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN |
| REPRODUCIBILITY LEVEL | **R4** — independent verification is itself reproducible (unlike VCE-001), since both the Lean build and the independent check complete cleanly from the stated commands |
| GRAPH HASH | `66705d978fd014309bc8f2cde2af9fd8934a088e0b4650ce9ae2695925c00123` (final, 13-event ledger) |
| COST | 11 events, one ~25-line Python script, all builds reused already-warm caches from earlier this session |
| FINAL DECISION | **PROMOTE** (see governance decision) |
| LIMITATIONS | None material. This is a deliberately elementary claim; the absence of limitations reflects the claim's simplicity, not a general property of the pipeline (contrast VCE-001). |

## Reproduction

```bash
cd ~/ico-collatz/ico_collatz_verification
lake build IcoCollatzVerification.PowersOfTwoReachOne
# expect: Build completed successfully (8924 jobs)
```

```bash
~/.claude/skills/verifying-lean-proofs/scripts/independent-check.sh \
  --target ~/ico-collatz/ico_collatz_verification \
  --module IcoCollatzVerification.PowersOfTwoReachOne \
  --export-bin ~/ico-collatz/targets/lean4export-v4.34.0/.lake/build/bin/lean4export \
  --nanoda-bin ~/ico-collatz/targets/nanoda_lib/target/release/nanoda_bin \
  --out /tmp/vce002-check \
  powers_of_two_reach_one
# expect: PASS, nanoda_decls=1662
```
