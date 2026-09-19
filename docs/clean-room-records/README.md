# Clean-room records

One file per reconstruction run, `YYYY-MM-DD-runN.md`, using the template in [`../CLEAN_ROOM_REPRODUCIBILITY.md`](../CLEAN_ROOM_REPRODUCIBILITY.md).

**Status: three consecutive scripted PASS (commit `5c825cf`) but NOT a complete validation:** tools were adopted rather than built from scratch, and no fresh Claude session has been used. A complete validation needs three consecutive PASS on one commit with a from-scratch tool build and a fresh Claude session, with no manual intervention that is not written in the repository. Partial runs are recorded too, and labelled as partial.

## Records so far

- `2026-09-19-run1..3-*.md` — **FAIL, all three, same cause**: the engine's `receipt` test suite depends on a gitignored third-party PDF absent from a fresh clone (BUG-008). The clean room did its job: it found machine-specific state the author could not see.
  Checker tools were **adopted** (`--reuse-from`), not built from scratch. No fresh Claude session was used. Fix pushed after these runs; passing runs (if any) are recorded below by later files.
- `2026-09-19-run1..3-171339/171544/171856.md` — **PASS ×3** on commit `5c825cf` (after the fix). Same caveats: adopted tools, scripted, no fresh Claude session.
