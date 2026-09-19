"""FCVE Gate 1 (claim extraction, §9) and Gate 2 (assumption extraction, §10).

Extraction itself is a reading task (human or model). This module defines the
schema those outputs must satisfy and validates them, so a malformed or
incomplete extraction is caught before the ledger event is written.
"""
import re

CLAIM_TYPES = {"FORMAL", "EMPIRICAL", "MIXED"}  # §5
CLAIM_ID = re.compile(r"^(CLAIM|LEMMA)-\d{3}$")  # §9 stable IDs
# §9 required per claim. `statement_verbatim` is the theorem statement.
CLAIM_REQUIRED = {
    "claim_id": str, "claim_type": str, "source_location": str, "statement_verbatim": str,
    "explicit_conditions": list, "surrounding_definitions": list, "referenced_lemmas": list,
}
# §10: three categories, each with its own ID prefix.
ASSUMPTION_CATEGORIES = {
    "source_assumptions": "SA",           # SOURCE_ASSUMPTION
    "formalization_assumptions": "FA",    # FORMALIZATION_ASSUMPTION
    "computational_assumptions": "CA",    # COMPUTATIONAL_ASSUMPTION
}


def validate_claims(doc, lenient=()):
    """Return a list of problems (empty = valid).

    `lenient` names required fields to skip for LEMMA-* entries only. It exists
    for legacy runs (VCE-001 kept shared definitions on CLAIM-001); new runs
    should validate strictly.
    """
    probs = []
    claims = doc.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["`claims` must be a non-empty list"]
    ids = [c.get("claim_id") for c in claims]
    for i in {x for x in ids if ids.count(x) > 1}:
        probs.append(f"duplicate claim_id {i}")
    by_id = {c.get("claim_id"): c for c in claims}
    for c in claims:
        cid = c.get("claim_id", "<missing>")
        for k, t in CLAIM_REQUIRED.items():
            if k in lenient and str(cid).startswith("LEMMA-"):
                continue
            if k not in c:
                probs.append(f"{cid}: missing {k}")
            elif not isinstance(c[k], t) or (t is str and not c[k].strip()):
                probs.append(f"{cid}: {k} must be a non-empty {t.__name__}" if t is str
                             else f"{cid}: {k} must be a list")
        if isinstance(c.get("claim_id"), str) and not CLAIM_ID.match(c["claim_id"]):
            probs.append(f"{cid}: id must look like CLAIM-001 / LEMMA-001")
        if c.get("claim_type") not in CLAIM_TYPES:
            probs.append(f"{cid}: claim_type {c.get('claim_type')!r} not in {sorted(CLAIM_TYPES)}")
        if c.get("claim_type") == "MIXED":  # §5: MIXED must be decomposed
            parts = c.get("decomposed_into")
            if not parts:
                probs.append(f"{cid}: MIXED claim must list `decomposed_into` FORMAL/EMPIRICAL ids")
            else:
                for p in parts:
                    if by_id.get(p, {}).get("claim_type") not in {"FORMAL", "EMPIRICAL"}:
                        probs.append(f"{cid}: decomposed_into {p} is not a FORMAL/EMPIRICAL claim in this file")
        for ref in c.get("referenced_lemmas", []) if isinstance(c.get("referenced_lemmas"), list) else []:
            if ref not in by_id:
                probs.append(f"{cid}: referenced lemma {ref} has no entry")
            elif ref == c.get("claim_id"):
                probs.append(f"{cid}: references itself")
    return probs


def validate_assumptions(doc):
    probs, seen = [], set()
    for cat, prefix in ASSUMPTION_CATEGORIES.items():
        if cat not in doc:  # empty category must be stated explicitly, not omitted
            probs.append(f"missing category `{cat}` (use [] if none, so absence is deliberate)")
            continue
        for a in doc[cat]:
            aid = a.get("id", "<missing>")
            if not re.match(rf"^{prefix}-\d{{3}}$", str(aid)):
                probs.append(f"{cat}: id {aid!r} must look like {prefix}-001")
            if aid in seen:
                probs.append(f"duplicate assumption id {aid}")
            seen.add(aid)
            if not str(a.get("statement", "")).strip():
                probs.append(f"{aid}: empty statement")
            if cat == "source_assumptions" and not str(a.get("explicit_or_implicit", "")).startswith(("explicit", "implicit")):
                probs.append(f"{aid}: explicit_or_implicit must start with 'explicit' or 'implicit'")
            if cat == "formalization_assumptions" and not str(a.get("why_introduced", "")).strip():
                probs.append(f"{aid}: formalization assumption needs why_introduced")
    return probs


def scaffold(claim_ids=("CLAIM-001",)):
    return (
        {"claims": [{"claim_id": i, "claim_type": "FORMAL", "theorem_name": "", "source_location": "",
                     "statement_verbatim": "", "explicit_conditions": [], "surrounding_definitions": [],
                     "referenced_lemmas": []} for i in claim_ids]},
        {"source_assumptions": [{"id": "SA-001", "statement": "", "explicit_or_implicit": "explicit"}],
         "formalization_assumptions": [], "computational_assumptions": []},
    )
