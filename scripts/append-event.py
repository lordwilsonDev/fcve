#!/usr/bin/env python3
"""Append a hash-chained event to the FCVE evidence ledger (spec Section 25).

Usage:
  append-event.py <ledger.jsonl> --action ACTION --reason "..." \
    --input INPUT_ID --output OUTPUT_ID --method "..." --result RESULT \
    [--evidence "path1,path2"] [--actor ACTOR]

Each event's own hash covers the event's own fields plus the previous event's
hash (PARENT_EVENTS), so the ledger is a genuine hash chain: tampering with
any earlier event changes every hash after it.
"""
import argparse, json, hashlib, sys, os
from datetime import datetime, timezone

p = argparse.ArgumentParser()
p.add_argument("ledger")
p.add_argument("--action", required=True)
p.add_argument("--reason", required=True)
p.add_argument("--input", required=True)
p.add_argument("--output", required=True)
p.add_argument("--method", required=True)
p.add_argument("--result", required=True)
p.add_argument("--evidence", default="")
p.add_argument("--actor", default="wilson+claude")
args = p.parse_args()

prior_hash = "GENESIS"
prior_id = None
n = 0
if os.path.exists(args.ledger):
    with open(args.ledger) as f:
        lines = [l for l in f if l.strip()]
        n = len(lines)
        if lines:
            last = json.loads(lines[-1])
            prior_hash = last["event_hash"]
            prior_id = last["event_id"]

event_id = f"EVENT-{n+1:03d}"
event = {
    "event_id": event_id,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "actor": args.actor,
    "action": args.action,
    "reason": args.reason,
    "input": args.input,
    "output": args.output,
    "method": args.method,
    "result": args.result,
    "evidence": [e.strip() for e in args.evidence.split(",") if e.strip()],
    "parent_events": [prior_id] if prior_id else [],
    "parent_hash": prior_hash,
}
canonical = json.dumps(event, sort_keys=True)
event["event_hash"] = hashlib.sha256((prior_hash + canonical).encode()).hexdigest()

with open(args.ledger, "a") as f:
    f.write(json.dumps(event, sort_keys=True) + "\n")

print(f"{event_id} appended, hash={event['event_hash'][:16]}...")
