"""FCVE evidence graph, schema v3 (spec §20, §24, §25).

One graph, six filtered views. Built from the hash-chained ledger; the ledger
stays the source of truth. v3 supersedes the Step-2 "v2" shape (never used in a
delivered run). Legacy v1 graphs (VCE-001/002) remain reproducible through
fcve_evidence.build_graph(evidence_class=False).

Differences from v1 that matter:
  * multi-id outputs ("A,B,C") become separate nodes; ranges ("LEMMA-001..005",
    "EVENT-001..EVENT-012") expand; file-like inputs are `external_inputs`, not
    dangling edges. Anything else unresolved is reported by validate().
  * all twelve §20 edge types are available; the choice per action is a judgment
    table (EDGE_FOR_ACTION), overridden to CONTRADICTS/REPAIRS by result status.
  * every node carries `status` (derived from the result text) so a
    diagnostic result can never be listed as a passed check.
"""
import hashlib
import json
import re

from fcve_evidence import ACTIONS, verify_chain

SCHEMA_VERSION = 3
# Events that legitimately follow the graph event (Gate 11): the report (Gate 12) and the decision (Gate 13), and the
# graph event itself. Any other event after the graph is new EVIDENCE, which makes the graph stale.
FOLLOW_ACTIONS = {"EVIDENCE_GRAPH", "REPORT_GENERATION", "GOVERNANCE_DECISION"}
NODE_TYPES = {"SOURCE", "CLAIM", "ASSUMPTION", "DEFINITION", "SYMBOL", "NORMALIZED_CLAIM", "FORMAL_STATEMENT",
              "FORMAL_PROOF", "BUILD", "AXIOM_AUDIT", "COMPUTATIONAL_MODEL", "COMPUTATIONAL_TEST",
              "COUNTEREXAMPLE_SEARCH", "ADVERSARIAL_TEST", "INDEPENDENT_CHECK", "SEMANTIC_AUDIT", "RECEIPT",
              "DECISION", "FAILURE", "REPAIR", "COST"}  # §20
EDGE_TYPES = {"DERIVED_FROM", "TRANSFORMS", "DEPENDS_ON", "JUSTIFIES", "TESTS", "SUPPORTS", "CONTRADICTS",
              "INVALIDATES", "REPAIRS", "PRODUCES", "RECHECKS", "SUPERSEDES"}  # §20
# Judgment table (not spec text): action -> default edge type for input -> output.
EDGE_FOR_ACTION = {
    "SOURCE_INTAKE": "PRODUCES", "CLAIM_EXTRACTION": "DERIVED_FROM", "ASSUMPTION_EXTRACTION": "DERIVED_FROM",
    "SEMANTIC_NORMALIZATION": "TRANSFORMS", "LEAN_FORMALIZATION_COMPARISON": "TRANSFORMS",
    "LEAN_BUILD": "PRODUCES", "AXIOM_AUDIT": "JUSTIFIES", "SEMANTIC_RE_AUDIT": "JUSTIFIES",
    "ADVERSARIAL_COMPUTATIONAL_TEST": "TESTS", "COMPUTATIONAL_CHECK": "TESTS",
    "CORRECTION_AND_RECHECK": "RECHECKS", "INDEPENDENT_CHECK": "JUSTIFIES",
    "EVIDENCE_GRAPH": "DERIVED_FROM", "REPORT_GENERATION": "DERIVED_FROM", "GOVERNANCE_DECISION": "JUSTIFIES",
}
CHECK_ACTIONS = {"AXIOM_AUDIT", "SEMANTIC_RE_AUDIT", "INDEPENDENT_CHECK", "ADVERSARIAL_COMPUTATIONAL_TEST",
                 "COMPUTATIONAL_CHECK", "LEAN_FORMALIZATION_COMPARISON", "LEAN_BUILD"}
NODE_TYPE_OVERRIDE = {"GOVERNANCE_DECISION": "DECISION", "REPORT_GENERATION": "RECEIPT"}

# Result text -> status. Order matters (first match wins). "Supported" wording is
# DIAGNOSTIC on purpose: it must never read as a passed verification (§16).
_STATUS_RULES = [
    ("DISPUTED", r"^(CHECKER_DISAGREEMENT|DISAGREEMENT)"),
    ("NO_VERDICT", r"^(CHECKER_UNAVAILABLE|CHECKER_INCOMPATIBLE|RUN_FAILED|UNCLEAR)"),
    ("DIAGNOSTIC", r"^(NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN|COMPUTATIONALLY_SUPPORTED|COUNTEREXAMPLE_FOUND)"),
    ("NOT_APPLICABLE", r"^NOT_APPLICABLE"),
    ("PARTIAL", r"^PARTIAL"),  # §11: neither a pass nor a stop
    ("FAIL", r"^(FAIL|MISMATCH|STRONGER|WEAKER|DIFFERENT|FAILED|STOP)"),
    ("PASS", r"^(PASS|MATCH|INDEPENDENTLY_CHECKED|CLEAN|DISCLOSED|COMPLETE)"),
]


def classify_result(result):
    for status, rx in _STATUS_RULES:
        if re.match(rx, result.strip()):
            return status
    return "UNCLASSIFIED"  # visible, not silently PASS


_RANGE = re.compile(r"^([A-Z]+)-(\d+)\.\.(?:\1-)?(\d+)$")
_FILELIKE = re.compile(r"(/|\.\w{1,6}(\s|$)|\s\()")


def expand_ids(field):
    """'A-001,B..' -> (ids, external_tokens). Ranges expand: LEMMA-001..005,
    EVENT-001..EVENT-012. File-like tokens are external inputs, not node ids."""
    ids, ext = [], []
    for tok in [t.strip() for t in field.split(",") if t.strip()]:
        m = _RANGE.match(tok)
        if m:
            pre, a, b = m.group(1), int(m.group(2)), int(m.group(3))
            width = len(m.group(2))
            ids += [f"{pre}-{i:0{width}d}" for i in range(a, b + 1)]
        elif _FILELIKE.search(tok):
            ext.append(tok)
        else:
            ids.append(tok)
    return ids, ext


FLOW_EDGES = {"TRANSFORMS", "PRODUCES", "DEPENDS_ON"}  # direction: input -> output
# Every other edge type is relational and points from the derived/checking node to its
# subject: "CLAIM-001 DERIVED_FROM SOURCE-001", "AXIOMS-001 JUSTIFIES BUILD-001",
# "TEST-001 CONTRADICTS NORMALIZED-001", "TEST-001-CORRECTED REPAIRS TEST-001".
_EVENT_REF = re.compile(r"^EVENT-\d+$")
VERDICTS = ("PROMOTE", "REPAIR", "REJECT", "RESEARCH", "STOP")  # §26


def superseded_events(events):
    """Events every one of whose outputs is produced again by a LATER event. They stay in the ledger
    (append-only, §46) but no longer contribute nodes or edges: the newer event replaces them."""
    later = {}
    for i, e in enumerate(events):
        outs = expand_ids(e["output"])[0] or [e["output"].strip()]
        for o in outs:
            later[o] = e["event_id"]      # ends up as the LATEST event producing that id
    out = []
    for e in events:
        outs = expand_ids(e["output"])[0] or [e["output"].strip()]
        if all(later[o] != e["event_id"] for o in outs):
            out.append({"event": e["event_id"], "superseded_by": sorted({later[o] for o in outs})})
    return out


def unresolved_inputs(events, input_field):
    """Bare ids in `input_field` that no earlier event produced (file-like inputs and EVENT-n refs excepted).
    Used to catch a mistyped input id at append time, before it becomes a dangling graph edge."""
    known = set()
    for e in events:
        ids = expand_ids(e["output"])[0] or [e["output"].strip()]
        known.update(ids); known.add(e["event_id"])
    ids, _ = expand_ids(input_field)
    return [i for i in ids if i not in known]


def build(events):
    sup = {s["event"]: s for s in superseded_events(events)}
    nodes, edges, external, event_nodes = {}, [], [], {}
    for ev in events:
        act = ev["action"]
        base_type, eclass = ACTIONS.get(act, ("RECEIPT", None))
        status = classify_result(ev["result"])
        verdict = None
        if act == "GOVERNANCE_DECISION":  # any §26 verdict is a decision, not a pass/fail
            head = ev["result"].strip().split()[0].strip("-:") if ev["result"].strip() else ""
            if head in VERDICTS:
                status, verdict = "DECIDED", head
        ntype = NODE_TYPE_OVERRIDE.get(act, base_type)
        if status in ("FAIL", "DISPUTED") and act in CHECK_ACTIONS and ntype not in ("BUILD",):
            pass  # keep the node's own type; failure is carried by `status` and the Failure view
        outs, _ = expand_ids(ev["output"])
        if not outs:  # output is a file: node id is the file token itself
            outs = [ev["output"].strip()]
        if ev["event_id"] in sup:  # replaced by a later event: keep the event-id -> node mapping, add nothing else
            event_nodes[ev["event_id"]] = outs
            continue
        ins, ext = expand_ids(ev["input"])
        ins = [n for i in ins for n in (event_nodes.get(i, [i]) if _EVENT_REF.match(i) else [i])]
        ins = list(dict.fromkeys(ins))
        for o in outs:
            nodes[o] = {"id": o, "type": ntype, "produced_by_event": ev["event_id"], "action": act,
                        "result": ev["result"], "status": status, "reason": ev.get("reason", ""),
                        "method": ev.get("method", ""), "actor": ev.get("actor", ""),
                        "timestamp": ev.get("timestamp", ""), "evidence_files": ev["evidence"],
                        "evidence_class": eclass.value if eclass else None,
                        "input_hash": ev.get("input_hash"), "output_hash": ev.get("output_hash"),
                        "verdict": verdict}
            event_nodes.setdefault(ev["event_id"], []).append(o)
        for t in ext:
            external.append({"token": t, "event": ev["event_id"]})
        for i in ins:
            for o in outs:
                etype = EDGE_FOR_ACTION.get(act, "TRANSFORMS")
                src = nodes.get(i)
                if act in CHECK_ACTIONS and status in ("FAIL", "DISPUTED"):
                    etype = "CONTRADICTS"
                elif act == "CORRECTION_AND_RECHECK":
                    etype = "REPAIRS" if src and src["status"] in ("FAIL", "DISPUTED", "DIAGNOSTIC") and status != "FAIL" else "RECHECKS"
                a, b = (i, o) if etype in FLOW_EDGES else (o, i)
                edges.append({"from": a, "to": b, "edge_type": etype, "via_event": ev["event_id"]})
    sup_list = sorted(sup.values(), key=lambda s: s["event"])
    graph = {"schema_version": SCHEMA_VERSION, **({"superseded_events": sup_list} if sup_list else {}), "nodes": sorted(nodes.values(), key=lambda n: n["produced_by_event"] + n["id"]),
             "edges": edges, "external_inputs": external, "event_count": len(events),
             "final_event_hash": events[-1]["event_hash"] if events else None}
    graph["graph_sha256"] = hashlib.sha256(json.dumps(graph, indent=2, sort_keys=True).encode()).hexdigest()
    return graph


def validate_legacy(graph, events):
    """v1 graphs (no schema_version): chain intact, not stale, and byte-identical to a
    v1 rebuild. Structural v3 checks do not apply. Known v1 defects are reported by
    validate(build(events)) instead -- v1 cannot be repaired without changing its hash."""
    import fcve_evidence as fe
    probs = [f"ledger: {p}" for p in verify_chain(events)]
    last = events[-1]["event_hash"] if events else None
    if graph.get("final_event_hash") != last or graph.get("event_count") != len(events):
        probs.append(f"STALE: graph covers {graph.get('event_count')} events, ledger has {len(events)}")
    elif fe.build_graph(events)["graph_sha256"] != graph.get("graph_sha256"):
        probs.append("legacy graph does not match a v1 rebuild from the ledger")
    return probs


def validate(graph, events=None):
    """Integrity problems (empty = sound). Checks structure, and -- given the
    ledger -- that the graph is not STALE (built before the ledger's last event)
    and the ledger chain itself is intact (§25)."""
    probs = []
    ids = {n["id"] for n in graph["nodes"]}
    if graph.get("schema_version") != SCHEMA_VERSION:
        return [f"schema_version {graph.get('schema_version')!r} != {SCHEMA_VERSION} (legacy v1 graph? use validate_legacy)"]
    for n in graph["nodes"]:
        if n["type"] not in NODE_TYPES:
            probs.append(f"{n['id']}: node type {n['type']!r} not in §20")
    for e in graph["edges"]:
        if e["edge_type"] not in EDGE_TYPES:
            probs.append(f"edge {e['from']}->{e['to']}: type {e['edge_type']!r} not in §20")
        for end in ("from", "to"):
            if e[end] not in ids:
                probs.append(f"dangling edge endpoint {e[end]!r} (event {e['via_event']})")
    for n in graph["nodes"]:
        if n["status"] == "UNCLASSIFIED":
            probs.append(f"{n['id']}: result not classifiable ({n['result'][:50]!r}); refusing to guess pass/fail")
    body = {k: v for k, v in graph.items() if k != "graph_sha256"}
    if hashlib.sha256(json.dumps(body, indent=2, sort_keys=True).encode()).hexdigest() != graph.get("graph_sha256"):
        probs.append("graph_sha256 does not match graph content")
    if events is not None:
        probs += [f"ledger: {p}" for p in verify_chain(events)]
        n = graph.get("event_count") or 0
        covered_ok = 0 < n <= len(events) and events[n - 1]["event_hash"] == graph.get("final_event_hash")
        later = [e["action"] for e in events[n:]] if covered_ok else []
        evidence_after = [a for a in later if a not in FOLLOW_ACTIONS]
        if not covered_ok or evidence_after:
            last = events[-1]["event_hash"] if events else None
            probs.append(f"STALE: graph covers {n} events ending {str(graph.get('final_event_hash'))[:12]}, ledger has {len(events)} ending {str(last)[:12]}"
                         + (f"; later evidence events: {evidence_after}" if evidence_after else "")
                         + " -- anything citing GRAPH_SHA256 is out of date")
        elif build(events[:n])["graph_sha256"] != graph["graph_sha256"]:
            probs.append("graph does not match a rebuild from the ledger events it covers")
    return probs


def event_integrity(events):
    """§25 required per-event fields. Legacy events lack input/output hashes;
    reported, not invented."""
    need = ["event_id", "timestamp", "actor", "action", "reason", "method", "result", "evidence", "parent_events"]
    out = {"missing_fields": [], "no_input_hash": [], "no_output_hash": []}
    for e in events:
        out["missing_fields"] += [f"{e.get('event_id')}: {k}" for k in need if k not in e]
        if not e.get("input_hash"):
            out["no_input_hash"].append(e["event_id"])
        if not e.get("output_hash"):
            out["no_output_hash"].append(e["event_id"])
    return out


# ---- §24: filtered views of the ONE graph -------------------------------------------------------
def view_chronological(g):
    return [(n["timestamp"], n["produced_by_event"], n["id"], n["action"]) for n in
            sorted(g["nodes"], key=lambda n: (n["produced_by_event"], n["id"]))]


def view_evidence(g):
    """Evidence-class nodes and what they bear on (edges out of, or into, them)."""
    ev = {n["id"]: n for n in g["nodes"] if n["evidence_class"]}
    return [{"node": i, "class": n["evidence_class"], "status": n["status"],
             "bears_on": sorted({e["from"] for e in g["edges"] if e["to"] == i})} for i, n in sorted(ev.items())]


def view_dependency(g):
    """(dependent, dependency) pairs: flow edges are input->output so the output depends
    on the input; DERIVED_FROM/SUPERSEDES already point dependent -> dependency."""
    out = []
    for e in g["edges"]:
        if e["edge_type"] in FLOW_EDGES:
            out.append((e["to"], e["from"]))
        elif e["edge_type"] in ("DERIVED_FROM", "SUPERSEDES"):
            out.append((e["from"], e["to"]))
    return sorted(set(out))


def view_reasoning(g):
    return [(n["produced_by_event"], n["id"], n["reason"]) for n in sorted(g["nodes"], key=lambda n: n["produced_by_event"])]


def view_failure(g):
    """Everything that did not simply pass: FAIL, DISPUTED, NO_VERDICT, plus repairs
    and contradictions, so a failure is never hidden by a later recheck."""
    bad = [n for n in g["nodes"] if n["status"] in ("FAIL", "DISPUTED", "NO_VERDICT", "UNCLASSIFIED")]
    fixes = [e for e in g["edges"] if e["edge_type"] in ("REPAIRS", "CONTRADICTS", "INVALIDATES")]
    return {"nodes": [(n["id"], n["status"], n["result"][:80]) for n in bad],
            "edges": [(e["from"], e["edge_type"], e["to"]) for e in fixes]}


NON_CHECK_CLASSES = {"SOURCE_ASSERTION", "HUMAN_REVIEW"}  # extraction/normalization are not checks


def view_verification(g):
    """Only what actually passed, with its evidence class. Diagnostic (no counterexample
    found, 'supported'), no-verdict and disputed results are excluded by construction."""
    return [(n["id"], n["evidence_class"], n["result"][:80]) for n in g["nodes"]
            if n["status"] == "PASS" and n["evidence_class"] and n["evidence_class"] not in NON_CHECK_CLASSES]


VIEWS = {"chronological": view_chronological, "evidence": view_evidence, "dependency": view_dependency,
         "reasoning": view_reasoning, "failure": view_failure, "verification": view_verification}
