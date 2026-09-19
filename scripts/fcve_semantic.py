"""FCVE semantic comparison -- Gate 3 (§11), Gate 4 (§12), Gate 7 (§15).

Deciding whether a Lean statement means what the source says is a judgment; this
module does not make it. It (1) scans the Lean statement for syntactic signals
that commonly hide a semantic change, (2) defines the comparison record, (3)
rejects a record that skips a required check, leaves a signal unaddressed, or
claims MATCH/CLEAN over an undisclosed finding. Signals are prompts, not
verdicts, and an empty scan does not prove a match.
"""
import re

NORMALIZATION_STATUS = {"MATCH", "PARTIAL", "MISMATCH", "UNCLEAR"}  # §11
NORMALIZATION_ACTION = {"MATCH": "CONTINUE", "PARTIAL": "CONTINUE", "MISMATCH": "STOP", "UNCLEAR": "REPAIR"}
FORMAL_STATUS = {"MATCH", "STRONGER", "WEAKER", "DIFFERENT", "FAILED"}  # §12; only MATCH passes

GATE4_CHECKS = [  # §12 "must detect"
    "stronger_statement", "weaker_statement", "altered_domain", "missing_hypothesis", "extra_hypothesis",
    "changed_quantifier", "changed_equality", "changed_function", "changed_coercion",
    "finite_infinite_mismatch", "exact_approximate_mismatch",
]
GATE7_CHECKS = [  # §15 "must explicitly search for"
    "added_hypotheses", "removed_hypotheses", "strengthened_conclusion", "weakened_conclusion",
    "changed_domains", "coercions", "finite_infinite_substitution", "extensionality_assumptions",
    "injectivity_assumptions", "decidability_assumptions", "classical_assumptions",
]
CHECKS = {"GATE4": GATE4_CHECKS, "GATE7": GATE7_CHECKS}

# Syntactic signals in a Lean theorem statement. name -> (regex, which check it bears on)
SIGNALS = {
    "cast_or_coercion": (r"↑|\(\s*\w+\s*:\s*[ℝℚℤℂ]\s*\)|:\s*[ℝℚℤℂ]\)|Nat\.cast|Int\.cast|Real\.|\bNNReal\b", "coercions"),
    "injectivity": (r"Injective|\.Inj\b|InjOn|Function\.Injective", "injectivity_assumptions"),
    "finite_structure": (r"Finset|Fintype|Set\.Finite|\.card\b|Fin\s", "finite_infinite_substitution"),
    "decidability": (r"Decidable|\bdecide\b|DecidableEq|DecidablePred", "decidability_assumptions"),
    "classical": (r"Classical|\bopen classical\b", "classical_assumptions"),
    "extensionality": (r"funext|propext|\bext\b|Set\.ext", "extensionality_assumptions"),
    "approximation": (r"Real\.logb|Real\.log|Real\.sqrt|Real\.exp|Real\.pi|≈|\bfloor\b|\bceil\b|Nat\.floor|Nat\.ceil", "exact_approximate_mismatch"),
    "strictness": (r"<|≤|>|≥", "changed_equality"),
}


# §30: the four allowed semantic-bridge verdicts. A HUMAN sets one; the tool only validates it.
BRIDGE_VERDICTS = ["FAITHFUL", "FAITHFUL WITH EXPLICIT REPRESENTATIONAL DIFFERENCE", "PARTIAL", "MISMATCH"]
WITH_DIFF = BRIDGE_VERDICTS[1]
# §31: when the encoding differs, the report must state all six of these explicitly.
DISCLOSURE_KEYS = ["informal_meaning", "lean_representation", "why_encoding_valid", "where_preserved",
                   "literal_or_transported", "assumptions"]
_MODEL_RE = re.compile(r"\b(assistant|claude|model|llm|gpt|ai|automated|bot)\b", re.I)


def reviewer_is_model(name):
    """§44: model output is PROPOSED until independently checked; no model certifies its own proposal."""
    return bool(_MODEL_RE.search(str(name or "")))


def bridge_info(rec):
    """(verdict, state, reviewer) where state is CONFIRMED / PROPOSED / NOT SET."""
    if not rec or not rec.get("bridge_verdict"):
        return None, "NOT SET", None
    return rec["bridge_verdict"], ("PROPOSED" if reviewer_is_model(rec.get("reviewer")) else "CONFIRMED"), rec.get("reviewer")


class SemanticError(Exception):
    pass


def extract_statement(lean_source, theorem):
    """Text from `theorem <name>` up to the top-level `:=`. Raises if not found
    or if the declaration is malformed -- never returns a guess."""
    m = re.search(rf"\b(?:theorem|lemma)\s+{re.escape(theorem)}\b", lean_source)
    if not m:
        raise SemanticError(f"theorem {theorem!r} not found in source")
    depth, i, text = 0, m.start(), lean_source
    while i < len(text) - 1:
        c = text[i]
        if c in "([{⟨":
            depth += 1
        elif c in ")]}⟩":
            depth -= 1
        elif depth == 0 and text[i:i + 2] == ":=":
            return text[m.start():i].strip()
        i += 1
    raise SemanticError(f"no `:=` found after theorem {theorem!r}")


def lean_signals(statement):
    """Signals present in the statement: {name: [matched snippets]}."""
    found = {}
    for name, (rx, _) in SIGNALS.items():
        hits = sorted({m.group(0).strip() for m in re.finditer(rx, statement)})
        if hits:
            found[name] = hits
    return found


def validate(rec, signals=None):
    """Problems with a comparison record (empty = acceptable to record).

    rec = {gate, claim_id, status, checks: {item: {finding: NONE|FOUND, detail,
    disclosed}}, signal_dispositions: {signal: {disposition, note}}}
    `signals` (from lean_signals) must each have a written disposition.
    """
    probs = []
    gate = rec.get("gate")
    if gate not in CHECKS:
        return [f"gate must be one of {sorted(CHECKS)}"]
    checks = rec.get("checks", {})
    for item in CHECKS[gate]:
        c = checks.get(item)
        if c is None:
            probs.append(f"check `{item}` not answered (every §{'12' if gate == 'GATE4' else '15'} check must be explicit)")
            continue
        if c.get("finding") not in ("NONE", "FOUND"):
            probs.append(f"{item}: finding must be NONE or FOUND")
        if c.get("finding") == "FOUND":
            if not str(c.get("detail", "")).strip():
                probs.append(f"{item}: FOUND needs a detail")
            if not isinstance(c.get("disclosed"), bool):
                probs.append(f"{item}: FOUND needs disclosed true/false")
        elif not str(c.get("detail", "")).strip():
            probs.append(f"{item}: NONE still needs a one-line basis (what was compared), not a bare tick")
    for extra in set(checks) - set(CHECKS[gate]):
        probs.append(f"unknown check `{extra}`")
    for sig in (signals or {}):
        d = rec.get("signal_dispositions", {}).get(sig)
        if not d or not str(d.get("disposition", "")).strip() or not str(d.get("note", "")).strip():
            probs.append(f"signal `{sig}` {signals[sig]} has no disposition+note")
    probs += _validate_bridge(rec, gate, checks)
    findings = [k for k, v in checks.items() if v.get("finding") == "FOUND"]
    undisclosed = [k for k in findings if checks[k].get("disclosed") is False]
    status = rec.get("status")
    if gate == "GATE4":
        if status not in FORMAL_STATUS:
            probs.append(f"status must be one of {sorted(FORMAL_STATUS)}")
        elif status == "MATCH" and findings:
            probs.append(f"status MATCH contradicts findings: {findings}")
        elif status != "MATCH" and not findings and status != "FAILED":
            probs.append(f"status {status} claims a difference but no check is FOUND")
    else:
        want = "REPAIR" if undisclosed else ("DISCLOSED" if findings else "CLEAN")
        if status != want:
            probs.append(f"Gate 7 status must be {want} (undisclosed change -> REPAIR, §15); got {status!r}")
    return probs


def _validate_bridge(rec, gate, checks):
    """Rules on the human-set bridge verdict. Required on GATE7 (the final semantic judgment, §15);
    optional on GATE4. The tool enforces consistency with the record's own findings, never the choice."""
    probs = []
    v = rec.get("bridge_verdict")
    if v is None or v == "":
        return ["bridge_verdict is required on the Gate 7 record (§30); a person sets it"] if gate == "GATE7" else []
    if v not in BRIDGE_VERDICTS:
        return [f"bridge_verdict {v!r} not one of {BRIDGE_VERDICTS} (§30)"]
    if not str(rec.get("bridge_justification", "")).strip():
        probs.append("bridge_justification is required (why the verdict is what it is; §30 'no silent equivalence claims')")
    if not str(rec.get("reviewer", "")).strip():
        probs.append("reviewer is required (who set the verdict)")
    found = [k for k, c in checks.items() if isinstance(c, dict) and c.get("finding") == "FOUND"]
    if v == "FAITHFUL" and found:
        probs.append(f"FAITHFUL contradicts FOUND checks {found}; use FAITHFUL WITH EXPLICIT REPRESENTATIONAL DIFFERENCE, PARTIAL or MISMATCH")
    if v == WITH_DIFF:
        if not found:
            probs.append("FAITHFUL WITH EXPLICIT REPRESENTATIONAL DIFFERENCE needs at least one FOUND check naming the difference")
        undisclosed = [k for k in found if checks[k].get("disclosed") is False]
        if undisclosed:
            probs.append(f"a difference cannot be 'explicit' while undisclosed: {undisclosed}")
        dd = rec.get("difference_disclosure") or {}
        for k in DISCLOSURE_KEYS:
            if not str(dd.get(k, "")).strip():
                probs.append(f"difference_disclosure.{k} required (§31: state all six of {DISCLOSURE_KEYS})")
    if v == "MISMATCH" and not found:
        probs.append("MISMATCH needs at least one FOUND check")
    return probs


def gate_outcome(rec):
    """Pipeline consequence of a validated record."""
    if rec["gate"] == "GATE4":
        return "PASS" if rec["status"] == "MATCH" else "FAIL"  # §12: only MATCH passes
    return {"CLEAN": "PASS", "DISCLOSED": "PASS", "REPAIR": "REPAIR"}[rec["status"]]


def normalization_outcome(status):
    if status not in NORMALIZATION_STATUS:
        raise SemanticError(f"normalization status must be one of {sorted(NORMALIZATION_STATUS)}")
    return NORMALIZATION_ACTION[status]


def scaffold(gate, claim_id, signals=None):
    extra = {"bridge_verdict": "", "bridge_justification": "", "reviewer": "",
             "difference_disclosure": {k: "" for k in DISCLOSURE_KEYS}} if gate == "GATE7" else {}
    return {**extra, "gate": gate, "claim_id": claim_id, "status": "",
            "checks": {k: {"finding": "", "detail": ""} for k in CHECKS[gate]},
            "signal_dispositions": {s: {"disposition": "", "note": ""} for s in (signals or {})}}
