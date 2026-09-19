# Phase 15: Positive Deviance

## Observation

A naive verification model — "trust the repo's own description of itself" —
predicts this repo has 1 remaining `sorry` and uses `native_decide` for a key
numeric fact (per `ARISTOTLE_SUMMARY.md`). A fresh, independent audit of the
current commit found the opposite: 0 `sorry`, 0 `native_decide`, 0 `admit`,
axiom-clean, and a semantically *more* careful theorem statement than the one
originally attempted (see `evidence/semantic-audit-eliahou.md`).

## Why this is the interesting case

This is not the failure mode the threat model was built to catch (a claim that
oversells completeness). It's the opposite: the repo's own stale
self-description undersold its current state. Both directions are covered by
the same fix — verify against `git log` + a fresh script run, never against a
repo's self-description, regardless of which way the staleness points — but
finding the "undersell" case first is useful evidence that the audit
methodology doesn't just catch the failure mode it was designed for; it also
catches a benign-but-still-wrong deviation nobody predicted in advance.

## Mechanism (Phase 16)

The mechanism is simple and generalizes: any file that describes "what this
proof does" (README, AI-run summary, commit message, docstring) is a snapshot
frozen at whatever commit last touched it. `git log --oneline -- <file>`
against the file's last-touched commit versus the file's actual claims is a
cheap, mechanical check that should run before trusting any such description,
independent of which direction the drift goes.

## Applies to future targets

This becomes a standing step (folded into Phase 12's audit template): for any
claim sourced from a README/summary/docstring rather than a fresh script run,
check `git log --oneline -- <that file>` first and flag drift either way.
