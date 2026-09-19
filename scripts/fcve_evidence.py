"""FCVE evidence schema (spec §2, §20, §21, §25, §46, §60 step 2).

Importable replacement for the per-event CLI pair (append-event.py,
build-evidence-graph.py). The old scripts stay as the reference
implementation: with `evidence_class=False` this module must reproduce their
graph hashes byte-for-byte (see tests/test_fcve_evidence.py).
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from enum import Enum


class EvidenceClass(str, Enum):  # spec §21
    SOURCE_ASSERTION = "SOURCE_ASSERTION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    FORMAL_PROOF = "FORMAL_PROOF"
    FORMAL_AXIOM_AUDIT = "FORMAL_AXIOM_AUDIT"
    SEMANTIC_COMPARISON = "SEMANTIC_COMPARISON"
    COMPUTATIONAL_TEST = "COMPUTATIONAL_TEST"
    COUNTEREXAMPLE_ATTEMPT = "COUNTEREXAMPLE_ATTEMPT"
    INDEPENDENT_REPLICATION = "INDEPENDENT_REPLICATION"
    REPRODUCIBILITY_CHECK = "REPRODUCIBILITY_CHECK"


EC = EvidenceClass

# action -> (node type, evidence class). Node types are unchanged from
# build-evidence-graph.py. Evidence class None = the node is bookkeeping, not
# evidence (§21: "every evidence-producing node"). The action->class mapping is
# a judgment call, not spec text -- review before relying on it.
ACTIONS = {
    "SOURCE_INTAKE": ("SOURCE", EC.SOURCE_ASSERTION),
    "CLAIM_EXTRACTION": ("CLAIM", EC.SOURCE_ASSERTION),
    "ASSUMPTION_EXTRACTION": ("ASSUMPTION", EC.SOURCE_ASSERTION),
    "SEMANTIC_NORMALIZATION": ("NORMALIZED_CLAIM", EC.HUMAN_REVIEW),
    "LEAN_FORMALIZATION_COMPARISON": ("FORMAL_STATEMENT", EC.SEMANTIC_COMPARISON),
    "LEAN_BUILD": ("BUILD", EC.FORMAL_PROOF),
    "AXIOM_AUDIT": ("AXIOM_AUDIT", EC.FORMAL_AXIOM_AUDIT),
    "SEMANTIC_RE_AUDIT": ("SEMANTIC_AUDIT", EC.SEMANTIC_COMPARISON),
    "ADVERSARIAL_COMPUTATIONAL_TEST": ("ADVERSARIAL_TEST", EC.COUNTEREXAMPLE_ATTEMPT),
    "CORRECTION_AND_RECHECK": ("REPAIR", EC.COMPUTATIONAL_TEST),
    "INDEPENDENT_CHECK": ("INDEPENDENT_CHECK", EC.INDEPENDENT_REPLICATION),
    "COMPUTATIONAL_CHECK": ("COMPUTATIONAL_TEST", EC.COMPUTATIONAL_TEST),
    "EVIDENCE_GRAPH": ("RECEIPT", None),
    "REPORT_GENERATION": ("RECEIPT", None),
    "GOVERNANCE_DECISION": ("RECEIPT", None),
}

# Canonical chain (§2): ... -> EVIDENCE GRAPH -> REPORT -> GOVERNANCE DECISION.
# Enforced as precedence pairs (a must appear before b if both present), not a
# total order, because the two runs legitimately differ in which optional
# checks ran and in where independent/computational checks fall.
_EVIDENCE_ACTIONS = [a for a, (_, c) in ACTIONS.items() if c is not None]
PRECEDENCE = (
    [("SOURCE_INTAKE", a) for a in ACTIONS if a != "SOURCE_INTAKE"]
    + [(a, "EVIDENCE_GRAPH") for a in _EVIDENCE_ACTIONS]
    + [("EVIDENCE_GRAPH", "REPORT_GENERATION"), ("REPORT_GENERATION", "GOVERNANCE_DECISION")]
)
# Links that must already exist (not merely be ordered if present) before the
# later action may be appended live. Optional checks (correction, computational)
# stay optional, so they are not listed here.
REQUIRED = [("SOURCE_INTAKE", a) for a in ACTIONS if a != "SOURCE_INTAKE"] + [
    ("EVIDENCE_GRAPH", "REPORT_GENERATION"), ("REPORT_GENERATION", "GOVERNANCE_DECISION")]


# Computational events must lead with a §16 outcome (or RUN_FAILED) so a run can
# never be recorded as "supported"/"proven" (§16, §21). Legacy VCE runs used
# COMPUTATIONALLY_SUPPORTED; they need legacy_result_wording=True (also covers VCE-002's 'PASS -- ...' Gate 9 wording).
COMPUTATIONAL_ACTIONS = {"ADVERSARIAL_COMPUTATIONAL_TEST", "COMPUTATIONAL_CHECK", "CORRECTION_AND_RECHECK"}
COMPUTATIONAL_RESULT_PREFIXES = ("COUNTEREXAMPLE_FOUND", "NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN",
                                 "NOT_APPLICABLE", "RUN_FAILED", "DISAGREEMENT")


# Gate 9 results must lead with a §17 result token, same reasoning: "uses nanoda"
# or "PASS" must never stand in for "independent verification completed".
INDEPENDENT_RESULT_PREFIXES = ("INDEPENDENTLY_CHECKED", "CHECKER_UNAVAILABLE", "CHECKER_INCOMPATIBLE",
                               "CHECKER_DISAGREEMENT", "NOT_APPLICABLE")


class GateOrderError(Exception):
    pass


class ArtifactError(Exception):
    """A gate's artifact is missing or fails its schema; nothing is appended."""


class EvidenceClassError(Exception):
    pass


def order_violations(actions):
    """Precedence violations for a sequence of action names, as (a, b) pairs
    meaning "a was required before b but appeared after it"."""
    seen = set()
    bad = []
    for act in actions:
        for a, b in PRECEDENCE:
            if b == act and a not in seen and a in actions:
                bad.append((a, b))
        seen.add(act)
    return bad


# action -> (evidence file basename, validator name in fcve_claims)
ARTIFACT_CHECKS = {
    "CLAIM_EXTRACTION": ("claims.json", "validate_claims"),
    "ASSUMPTION_EXTRACTION": ("assumptions.json", "validate_assumptions"),
}


def check_artifacts(action, evidence, ledger, root=None, legacy_lemma_defs=False):
    """Validate the gate artifact named in `evidence`, if this action has a
    schema. Paths are tried against `root` (default cwd), then the ledger's run
    directory (ledger lives at <run>/evidence/), since older runs recorded
    paths relative to one or the other. Raises ArtifactError on any problem."""
    if action not in ARTIFACT_CHECKS:
        return
    import fcve_claims  # local import: keeps this module usable without it
    base, fn = ARTIFACT_CHECKS[action]
    files = [e for e in evidence if os.path.basename(e) == base]
    if not files:
        raise ArtifactError(f"{action}: evidence must include a {base}")
    bases = [root or os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(ledger)))]
    for rel in files:
        path = next((os.path.join(b, rel) for b in bases if os.path.exists(os.path.join(b, rel))), None)
        if path is None:
            raise ArtifactError(f"{action}: {rel} not found under {bases}")
        with open(path) as f:
            doc = json.load(f)
        kw = {"lenient": ("surrounding_definitions",)} if legacy_lemma_defs and fn == "validate_claims" else {}
        probs = getattr(fcve_claims, fn)(doc, **kw)
        if probs:
            raise ArtifactError(f"{action}: {rel} invalid:\n  " + "\n  ".join(probs))


def _resolve(rel, ledger, root):
    bases = [root or os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(ledger)))]
    return next((os.path.join(b, rel) for b in bases if os.path.isfile(os.path.join(b, rel))), None)


def evidence_file_hashes(evidence, ledger, root=None):
    """path -> sha256, or null if the file could not be found when recorded. Stored on new
    events so staleness (§47) compares only files that WERE hashed: a file that did not exist
    at record time (e.g. a receipt written after the decision that cites it) cannot go stale."""
    from fcve_lean import _sha
    return {rel: (lambda p: _sha(p) if p else None)(_resolve(rel, ledger, root)) for rel in evidence}


def artifact_hashes(events, input_field, evidence, ledger, root=None):
    """§25 INPUT_HASH / OUTPUT_HASH. output_hash covers the evidence files (path ->
    sha256, null when a listed file cannot be found, so absence is visible);
    input_hash covers the output_hash of the event that produced each input id."""
    from fcve_lean import _sha
    out = sorted([rel, (lambda p: _sha(p) if p else None)(_resolve(rel, ledger, root))] for rel in evidence)
    produced = {}
    for e in events:
        for tok in e["output"].split(","):
            produced[tok.strip()] = e.get("output_hash")
    inp = sorted([tok.strip(), produced.get(tok.strip())] for tok in input_field.split(",") if tok.strip())
    h = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()
    return h(inp), h(out)


def read_ledger(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def verify_chain(events):
    """Recompute every event hash; return list of problems (empty = intact)."""
    problems, prior = [], "GENESIS"
    for ev in events:
        body = {k: v for k, v in ev.items() if k != "event_hash"}
        want = hashlib.sha256((prior + json.dumps(body, sort_keys=True)).encode()).hexdigest()
        if body.get("parent_hash") != prior:
            problems.append(f"{ev['event_id']}: parent_hash mismatch")
        if ev["event_hash"] != want:
            problems.append(f"{ev['event_id']}: event_hash mismatch")
        prior = ev["event_hash"]
    return problems


def append_event(ledger, *, action, reason, input, output, method, result,
                 evidence=(), actor="wilson+claude", strict=True, timestamp=None,
                 root=None, legacy_lemma_defs=False, legacy_result_wording=False,
                 hash_artifacts=True, check_inputs=False):
    """Append one hash-chained event (same hash scheme as append-event.py).

    strict=True refuses an event that would put the ledger out of canonical
    gate order (closes handoff open item #2). The ledger is append-only, so a
    refused call writes nothing; record the mistake in a correction ledger
    instead of reordering history (§46).
    """
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}; register it in ACTIONS")
    events = read_ledger(ledger)
    if strict:
        prior = [e["action"] for e in events]
        bad = [v for v in order_violations(prior + [action]) if v[1] == action]
        bad += [v for v in REQUIRED if v[1] == action and v[0] not in prior and v not in bad]
        if bad:
            raise GateOrderError(
                f"{action} out of canonical order; missing/late prerequisites: "
                + ", ".join(a for a, _ in bad))
        check_artifacts(action, list(evidence), ledger, root, legacy_lemma_defs)
        if (action in COMPUTATIONAL_ACTIONS and not legacy_result_wording
                and not result.startswith(COMPUTATIONAL_RESULT_PREFIXES)):
            raise ArtifactError(f"{action}: result must start with one of {COMPUTATIONAL_RESULT_PREFIXES} (§16); got {result[:60]!r}")
        if (action == "INDEPENDENT_CHECK" and not legacy_result_wording
                and not result.startswith(INDEPENDENT_RESULT_PREFIXES)):
            raise ArtifactError(f"{action}: result must start with one of {INDEPENDENT_RESULT_PREFIXES} (§17); got {result[:60]!r}")
    if check_inputs:
        import fcve_graph  # lazy: fcve_graph imports this module
        bad = fcve_graph.unresolved_inputs(events, input)
        if bad:
            raise ArtifactError(f"{action}: input id(s) {bad} not produced by any earlier event (typo? the graph would get a dangling edge)")
    prior_hash = events[-1]["event_hash"] if events else "GENESIS"
    prior_id = events[-1]["event_id"] if events else None
    event = {
        "event_id": f"EVENT-{len(events) + 1:03d}",
        "timestamp": timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor": actor,
        "action": action,
        "reason": reason,
        "input": input,
        "output": output,
        "method": method,
        "result": result,
        "evidence": list(evidence),
        "parent_events": [prior_id] if prior_id else [],
        "parent_hash": prior_hash,
    }
    if hash_artifacts:  # off only to rebuild legacy ledgers byte-for-byte
        event["input_hash"], event["output_hash"] = artifact_hashes(events, input, list(evidence), ledger, root)
        event["evidence_hashes"] = evidence_file_hashes(list(evidence), ledger, root)
    event["event_hash"] = hashlib.sha256(
        (prior_hash + json.dumps(event, sort_keys=True)).encode()).hexdigest()
    with open(ledger, "a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def build_graph(events, evidence_class=False):
    """Legacy v1 graph (VCE-001/002 shape). Kept ONLY so their cited hashes
    reproduce. The current graph is fcve_graph.build (schema v3); the short-lived
    Step-2 'v2' shape was retired before any delivered run used it."""
    if evidence_class:
        raise ValueError("evidence_class graphs are schema v3 now: use fcve_graph.build(events)")
    nodes, edges = {}, []
    for ev in events:
        ntype = ACTIONS.get(ev["action"], ("RECEIPT", None))[0]
        nodes[ev["output"]] = {"id": ev["output"], "type": ntype, "produced_by_event": ev["event_id"],
                               "result": ev["result"], "evidence_files": ev["evidence"]}
        for inp in ev["input"].split(","):
            edges.append({"from": inp.strip(), "to": ev["output"], "edge_type": "TRANSFORMS", "via_event": ev["event_id"]})
    graph = {"nodes": list(nodes.values()), "edges": edges, "event_count": len(events),
             "final_event_hash": events[-1]["event_hash"] if events else None}
    graph["graph_sha256"] = hashlib.sha256(json.dumps(graph, indent=2, sort_keys=True).encode()).hexdigest()
    return graph


def require_class(node, *allowed):
    """Structural guard for anything that merges/summarizes evidence: refuse a
    node whose class isn't in `allowed`. There is deliberately no function
    that converts one class into another (§21)."""
    got = node.get("evidence_class")
    if got not in {c.value for c in allowed}:
        raise EvidenceClassError(
            f"{node.get('id')}: evidence_class {got!r} not in "
            f"{[c.value for c in allowed]}")
    return node
