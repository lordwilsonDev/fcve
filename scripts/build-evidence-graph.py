#!/usr/bin/env python3
"""Derive the typed evidence graph (spec Section 20) from the event ledger.

The ledger (event-ledger.jsonl) is a chronological, hash-chained transaction
log -- one event per gate. The evidence graph is a different view: nodes are
the artifacts (SOURCE-001, CLAIM-001, FORMAL-001, ...) and edges are the
TRANSFORMS/DERIVED_FROM/PRODUCES relationships between them, derived from
each event's (action, input, output) fields.
"""
import json, sys, hashlib

ACTION_TO_NODE_TYPE = {
    "SOURCE_INTAKE": "SOURCE",
    "CLAIM_EXTRACTION": "CLAIM",
    "ASSUMPTION_EXTRACTION": "ASSUMPTION",
    "SEMANTIC_NORMALIZATION": "NORMALIZED_CLAIM",
    "LEAN_FORMALIZATION_COMPARISON": "FORMAL_STATEMENT",
    "LEAN_BUILD": "BUILD",
    "AXIOM_AUDIT": "AXIOM_AUDIT",
    "SEMANTIC_RE_AUDIT": "SEMANTIC_AUDIT",
    "ADVERSARIAL_COMPUTATIONAL_TEST": "ADVERSARIAL_TEST",
    "CORRECTION_AND_RECHECK": "REPAIR",
    "INDEPENDENT_CHECK": "INDEPENDENT_CHECK",
    "COMPUTATIONAL_CHECK": "COMPUTATIONAL_TEST",
}

ledger_path, out_path = sys.argv[1], sys.argv[2]
nodes, edges = {}, []
with open(ledger_path) as f:
    events = [json.loads(l) for l in f if l.strip()]

for ev in events:
    node_type = ACTION_TO_NODE_TYPE.get(ev["action"], "RECEIPT")
    out_id = ev["output"]
    nodes[out_id] = {
        "id": out_id,
        "type": node_type,
        "produced_by_event": ev["event_id"],
        "result": ev["result"],
        "evidence_files": ev["evidence"],
    }
    for inp in ev["input"].split(","):
        inp = inp.strip()
        edges.append({"from": inp, "to": out_id, "edge_type": "TRANSFORMS", "via_event": ev["event_id"]})

graph = {
    "nodes": list(nodes.values()),
    "edges": edges,
    "event_count": len(events),
    "final_event_hash": events[-1]["event_hash"] if events else None,
}
graph_json = json.dumps(graph, indent=2, sort_keys=True)
graph_sha256 = hashlib.sha256(graph_json.encode()).hexdigest()
graph["graph_sha256"] = graph_sha256

with open(out_path, "w") as f:
    json.dump(graph, f, indent=2, sort_keys=True)

print(f"Wrote {len(nodes)} nodes, {len(edges)} edges to {out_path}")
print(f"GRAPH_SHA256: {graph_sha256}")
