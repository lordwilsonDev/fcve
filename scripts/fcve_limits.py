"""FCVE reviewer-authored limitations (spec §28, §44, §61 Q9/Q10).

The tool derives limitations from the ledger and the records, but some of the most important ones -- above all
"what the tests did NOT establish" -- are knowledge a reviewer has and no gate records (e.g. "no counterexample was
sought against the underlying conjecture; that is infeasible"). This record lets a person state them.

Rules, chosen to match the bridge-verdict record:
  * A person writes them; the tool only validates and displays.
  * They can only ADD limitations. They never suppress, soften or replace one the tool derived.
  * Each carries a `basis` (where the statement comes from) so it is not free-floating assertion.
  * §44: an entry whose reviewer name reads as a model is shown as PROPOSED, not confirmed.
  * An explicit empty list needs a stated basis ("none" is a claim, not a default).
"""
import re

import fcve_semantic as fs

SCOPES = ["TESTS", "SOURCE", "FORMALIZATION", "INDEPENDENT_CHECK", "REPRODUCTION", "OTHER"]
MAX_STATEMENT = 500          # a limitation is a sentence or two, not an essay
MAX_SHORT = 160              # optional one-line form used in the Trust Statement, which §27 wants concise; never a truncation
_ID = re.compile(r"^RL-\d{3}$")


def validate(rec):
    """Problems with a reviewer-limitations record (empty = valid)."""
    if not isinstance(rec, dict):
        return ["record must be a JSON object"]
    probs = []
    if not str(rec.get("reviewer", "")).strip():
        probs.append("reviewer is required (who is stating these limitations)")
    items = rec.get("limitations")
    if not isinstance(items, list):
        return probs + ["`limitations` must be a list"]
    if not items and not str(rec.get("none_basis", "")).strip():
        probs.append("an empty list needs `none_basis`: saying there are no reviewer limitations is itself a claim")
    seen = set()
    for it in items:
        lid = it.get("id", "<missing>") if isinstance(it, dict) else "<not an object>"
        if not isinstance(it, dict):
            probs.append(f"{lid}: each limitation must be an object"); continue
        if not _ID.match(str(lid)):
            probs.append(f"{lid}: id must look like RL-001")
        if lid in seen:
            probs.append(f"duplicate id {lid}")
        seen.add(lid)
        if it.get("scope") not in SCOPES:
            probs.append(f"{lid}: scope {it.get('scope')!r} not in {SCOPES}")
        st = str(it.get("statement", "")).strip()
        if not st:
            probs.append(f"{lid}: statement is required")
        elif len(st) > MAX_STATEMENT:
            probs.append(f"{lid}: statement is {len(st)} characters; keep it under {MAX_STATEMENT} (a limitation, not an essay)")
        if not str(it.get("basis", "")).strip():
            probs.append(f"{lid}: basis is required (where this statement comes from)")
        sh = it.get("short")
        if sh is not None and (not str(sh).strip() or len(str(sh)) > MAX_SHORT):
            probs.append(f"{lid}: short must be a non-empty line of at most {MAX_SHORT} characters (it is written, not cut from the statement)")
    return probs


def info(rec):
    """(state, reviewer): CONFIRMED / PROPOSED (model-authored, §44) / NOT SET."""
    if not rec:
        return "NOT SET", None
    return ("PROPOSED" if fs.reviewer_is_model(rec.get("reviewer")) else "CONFIRMED"), rec.get("reviewer")


def tag(rec):
    """Short provenance tag appended to a displayed limitation."""
    state, who = info(rec)
    return f"stated by {who}" if state == "CONFIRMED" else f"proposed by {who}; not yet confirmed by a human reviewer"


def scaffold(claim_id):
    return {"claim_id": claim_id, "reviewer": "", "none_basis": "",
            "limitations": [{"id": "RL-001", "scope": "TESTS", "statement": "", "short": "", "basis": ""}]}
