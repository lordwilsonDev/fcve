"""FCVE batch execution (spec §43, §44, §47, §60 step 12).

Runs the MECHANICAL gates for many theorems and stops each theorem at the next
gate that needs a person. Nothing judgmental is automated or invented:

  human:  G0 source intake, G1 claims, G2 assumptions, G3 normalization,
          G4 formalization comparison, G7 semantic re-audit, G13 governance decision
  auto:   G5 build, G6 axiom audit, G8 counterexample search, G9 independent
          check, G10 computational check, G11 evidence graph, G12 report, receipt

State is derived from each theorem's own ledger (the source of truth), so a run
is resumable and idempotent. One theorem failing never aborts the batch; a
failed build (G5) or axiom audit (G6) blocks THAT theorem. Low disk halts the
whole batch (not safe to continue). Theorems run sequentially: Lean/Mathlib
memory makes parallelism a hazard on this machine, and it is a solo setup.

Staleness (§47): if an artifact a recorded event depended on changed on disk,
that event and everything downstream is STALE and is re-run (auto) or sent back
for review (human). No downstream PASS survives an invalidated dependency.
"""
import json
import os
import shutil
import time
from datetime import datetime, timezone

import fcve_axioms as fx
import fcve_compute as fcomp
import fcve_evidence as fe
import fcve_graph as fg
import fcve_independent as fi
import fcve_lean as fl
import fcve_receipt as fr
import fcve_report as frp

NR = "NOT RECORDED"
DEFAULT_MIN_FREE_GB = 3.0
# (gate, ledger action, kind, needs-config-key)
SEQUENCE = [("G0", "SOURCE_INTAKE", "human", None), ("G1", "CLAIM_EXTRACTION", "human", None),
            ("G2", "ASSUMPTION_EXTRACTION", "human", None), ("G3", "SEMANTIC_NORMALIZATION", "human", None),
            ("G4", "LEAN_FORMALIZATION_COMPARISON", "human", None), ("G5", "LEAN_BUILD", "auto", "lean"),
            ("G6", "AXIOM_AUDIT", "auto", "lean"), ("G7", "SEMANTIC_RE_AUDIT", "human", None),
            ("G8", "ADVERSARIAL_COMPUTATIONAL_TEST", "auto", "gate8"), ("G9", "INDEPENDENT_CHECK", "auto", "checkers"),
            ("G10", "COMPUTATIONAL_CHECK", "auto", "gate10"), ("G11", "EVIDENCE_GRAPH", "auto", None),
            ("G12", "REPORT_GENERATION", "auto", None), ("G13", "GOVERNANCE_DECISION", "human", None)]
HARD_STOP_GATES = {"G5", "G6"}  # a FAIL here blocks the theorem; evidence gaps elsewhere do not
HUMAN_HELP = {
    "G0": "record the source: fcve.py append LEDGER --action SOURCE_INTAKE --evidence source/<file>,source/source-metadata.json ...",
    "G1": "write claims/claims.json, run fcve.py validate-claims, then append CLAIM_EXTRACTION (validated on append)",
    "G2": "write claims/assumptions.json, then append ASSUMPTION_EXTRACTION (validated on append)",
    "G3": "write the normalized claim and decide MATCH/PARTIAL/MISMATCH/UNCLEAR (§11), then append SEMANTIC_NORMALIZATION",
    "G4": "compare the Lean statement to the normalized claim: fcve.py scaffold-semantic GATE4 ..., fill it, semantic-check --ledger ...",
    "G7": "semantic re-audit: fcve.py scaffold-semantic GATE7 ..., fill it, semantic-check --ledger ...",
    "G13": "record the governance decision (PROMOTE/REPAIR/REJECT/RESEARCH/STOP) with its reason; it must not exceed what the receipt allows",
}


class BatchError(Exception):
    pass


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ manifest
def load_manifest(path):
    m = json.load(open(path))
    base = os.path.dirname(os.path.abspath(path))
    ids, runs, probs = set(), set(), []
    for t in m.get("theorems", []):
        tid = t.get("id")
        if not tid or not str(tid).replace("-", "").replace("_", "").isalnum():
            probs.append(f"theorem id {tid!r} must be alphanumeric"); continue
        if tid in ids:
            probs.append(f"duplicate theorem id {tid}")
        ids.add(tid)
        t["run_dir"] = os.path.abspath(os.path.join(base, t["run_dir"])) if "run_dir" in t else None
        if not t["run_dir"]:
            probs.append(f"{tid}: run_dir required"); continue
        if any(t["run_dir"] == r or t["run_dir"].startswith(r + os.sep) or r.startswith(t["run_dir"] + os.sep) for r in runs):
            probs.append(f"{tid}: run_dir overlaps another theorem's (runs must be isolated)")
        runs.add(t["run_dir"])
        t.setdefault("ledger", os.path.join(t["run_dir"], "evidence", "event-ledger.jsonl"))
        if not os.path.isabs(t["ledger"]):
            t["ledger"] = os.path.join(base, t["ledger"])
        t.setdefault("root", None)
        if t.get("lean"):
            for k in ("project", "module", "theorems"):
                if k not in t["lean"]:
                    probs.append(f"{tid}: lean.{k} required")
            if "project" in t["lean"] and not os.path.isdir(t["lean"]["project"]):
                probs.append(f"{tid}: lean.project {t['lean']['project']} not found")
        for k in ("gate8", "gate10"):
            sp = (t.get("compute") or {}).get(k)
            if sp and not os.path.isfile(sp):
                probs.append(f"{tid}: compute.{k} script {sp} not found")
    if not m.get("theorems"):
        probs.append("manifest has no theorems")
    if probs:
        raise BatchError("manifest invalid:\n  " + "\n  ".join(probs))
    m.setdefault("min_free_gb", DEFAULT_MIN_FREE_GB)
    return m


# ------------------------------------------------------------------ staleness (§47)
def stale_report(ledger, root=None):
    """Which recorded events' evidence changed on disk, and what is downstream.
    Events without a recorded output_hash cannot be checked: reported UNVERIFIABLE,
    never assumed fresh."""
    events = fe.read_ledger(ledger)
    latest = {}
    for i, e in enumerate(events):  # latest event per output id wins
        for o in e["output"].split(","):
            latest[o.strip()] = i
    changed, unverifiable = {}, []
    for i, e in enumerate(events):
        if i not in latest.values():
            continue
        if not e.get("output_hash"):
            unverifiable.append(e["event_id"]); continue
        if "evidence_hashes" in e:  # per-file: only files that were hashed when recorded can go stale
            now = fe.evidence_file_hashes(list(e["evidence_hashes"]), ledger, root)
            bad = [p for p, h in e["evidence_hashes"].items() if h is not None and now[p] != h]
            if bad:
                changed[e["event_id"]] = "evidence changed or went missing since recorded: " + ", ".join(bad[:3])
        else:
            _, now = fe.artifact_hashes(events[:i], e["input"], e["evidence"], ledger, root)
            if now != e["output_hash"]:
                changed[e["event_id"]] = "evidence file changed or went missing since it was recorded"
    # replaced-input staleness: event j used id X, and a LATER event re-produced X after j ran -> j is stale
    producers = {}
    for i, e in enumerate(events):
        for o in (fg.expand_ids(e["output"])[0] or [e["output"].strip()]):
            producers.setdefault(o, []).append(i)
    for j, e in enumerate(events):
        for x in fg.expand_ids(e["input"])[0]:
            later = [p for p in producers.get(x, []) if p > j]
            if later and any(p < j for p in producers.get(x, [])):
                changed.setdefault(e["event_id"], f"was computed from {x} as produced before {events[later[0]]['event_id']} replaced it")
    g = fg.build(events)
    ev_of = {n["id"]: n["produced_by_event"] for n in g["nodes"]}
    deps = {}  # node -> nodes that depend on it
    for ed in g["edges"]:
        # flow edges run input -> output (output depends on input); relational edges run derived -> subject
        # (derived depends on subject). Either way: a = the dependency, b = what depends on it.
        a, b = (ed["from"], ed["to"]) if ed["edge_type"] in fg.FLOW_EDGES else (ed["to"], ed["from"])
        deps.setdefault(a, set()).add(b)
    seed = [n for n, ev in ev_of.items() if ev in changed]
    stale, todo = set(seed), list(seed)
    while todo:
        for d in deps.get(todo.pop(), ()):
            if d not in stale:
                stale.add(d); todo.append(d)
    return {"changed_events": changed, "stale_nodes": sorted(stale), "stale_events": sorted({ev_of[n] for n in stale if n in ev_of}),
            "unverifiable_events": unverifiable}


# ------------------------------------------------------------------ state
def _latest(events, action):
    hit = [e for e in events if e["action"] == action]
    return hit[-1] if hit else None


def plan(t, min_free_gb=DEFAULT_MIN_FREE_GB):
    """Where a theorem stands and what happens next. Pure: executes nothing."""
    events = fe.read_ledger(t["ledger"]) if os.path.exists(t["ledger"]) else []
    stale = stale_report(t["ledger"], t["root"]) if events else {"stale_events": [], "changed_events": {}, "unverifiable_events": [], "stale_nodes": []}
    out = {"id": t["id"], "events": len(events), "stale_events": stale["stale_events"], "unverifiable_events": stale["unverifiable_events"],
           "changed_events": stale["changed_events"], "not_configured": [], "done": []}
    have_event = {g for g, a, _, _ in SEQUENCE if _latest(events, a)}
    out["not_configured"] = [g for g, _, _, need in SEQUENCE if need and g not in have_event and not _configured(t, need, g)]
    for gate, action, kind, need in SEQUENCE:
        ev = _latest(events, action)
        if gate in out["not_configured"]:
            continue
        is_stale = ev is not None and ev["event_id"] in stale["stale_events"]
        if ev is not None and not is_stale:
            if gate in HARD_STOP_GATES and fg.classify_result(ev["result"]) == "FAIL":
                out.update(state=f"BLOCKED_FAILED:{gate}", next=None, detail=f"{gate} recorded {ev['result'][:80]}; downstream gates do not run for this theorem")
                return out
            out["done"].append(gate); continue
        if kind == "human":
            out.update(state=f"AWAITING_REVIEW:{gate}", next=gate, detail=HUMAN_HELP[gate] + (" (STALE: an upstream artifact changed; re-review required)" if is_stale else ""))
            return out
        out.update(state="READY", next=gate, detail=f"run {action}" + (" (re-run: previous result is STALE)" if is_stale else ""))
        return out
    rdir = os.path.join(t["run_dir"], "receipt")
    have = [f for f in ("receipt.json", "verification-receipt.md") if os.path.exists(os.path.join(rdir, f))]
    if not have:
        out.update(state="READY", next="RECEIPT", detail="generate the receipt")
    else:  # an existing receipt (machine- or hand-written) is never overwritten
        note = (f"; CAUTION: {len(out['unverifiable_events'])}/{len(events)} events carry no evidence hashes, so staleness cannot be checked"
                if out["unverifiable_events"] else "")
        out.update(state="COMPLETE", next=None, detail="receipt exists: " + ", ".join(have) + note)
    return out


def _configured(t, need, gate):
    if need == "lean":
        return bool(t.get("lean"))
    if need == "gate8":
        return bool((t.get("compute") or {}).get("gate8"))
    if need == "gate10":
        return bool((t.get("compute") or {}).get("gate10"))
    if need == "checkers":
        c = t.get("checkers") or {}
        return bool(c.get("independent_na") or (c.get("export_bin") and c.get("nanoda_bin")))
    return True


# ------------------------------------------------------------------ steps
def _rel(t, path):
    return os.path.relpath(path, t["run_dir"])


def _ids(events, action):
    e = _latest(events, action)
    return e["output"] if e else None


def _timed(t, step, fn, cost_log):
    t0, start = time.monotonic(), _now()
    try:
        return fn()
    finally:
        with open(cost_log, "a") as f:
            f.write(json.dumps({"theorem": t["id"], "step": step, "started_utc": start, "seconds": round(time.monotonic() - t0, 2)}) + "\n")


def run_step(t, gate, min_free_gb, cost_log):
    """Execute one automatic gate and append its ledger event (failures too)."""
    events = fe.read_ledger(t["ledger"])
    L, root, tid = t["ledger"], t["root"], t["id"]
    lean, run = t.get("lean") or {}, t["run_dir"]
    def add(ev_kwargs, input_, output):
        return fe.append_event(L, reason=ev_kwargs.pop("reason", f"Automated {gate} (batch)"), input=input_, output=output, actor="fcve-batch", root=root, check_inputs=True, **ev_kwargs)
    if gate == "G5":
        out = os.path.join(run, "lean")
        rec = _timed(t, gate, lambda: fl.run_build(lean["project"], out, target=lean.get("target"), min_free_gb=min_free_gb), cost_log)
        return add(fl.event_fields(rec, _rel(t, os.path.join(out, f"build-{rec['kind']}-record.json"))), _ids(events, "LEAN_FORMALIZATION_COMPARISON"), f"BUILD-{tid}")
    if gate == "G6":
        out = os.path.join(run, "axiom")
        rec = _timed(t, gate, lambda: fx.audit(lean["project"], lean["module"], lean["theorems"], out, external=lean.get("external_axioms", ())), cost_log)
        return add(fx.event_fields(rec, _rel(t, os.path.join(out, "axiom-audit-record.json"))), f"BUILD-{tid}", f"AXIOMS-{tid}")
    if gate in ("G8", "G10"):
        cfg, key = t["compute"], "gate8" if gate == "G8" else "gate10"
        out = os.path.join(run, "computational", "results")
        rec = _timed(t, gate, lambda: fcomp.run_check(cfg[key], out, gate=8 if gate == "G8" else 10, recheck_script=cfg.get(key + "_recheck")), cost_log)
        rel = _rel(t, os.path.join(out, os.path.splitext(os.path.basename(cfg[key]))[0] + "-compute-record.json"))
        inp = ",".join(x for x in (_ids(events, "SEMANTIC_NORMALIZATION"), _ids(events, "LEAN_FORMALIZATION_COMPARISON")) if x) if gate == "G8" else f"TEST-{tid}"
        return add(fcomp.event_fields(rec, rel), inp, f"TEST-{tid}" if gate == "G8" else f"COMPTEST-{tid}")
    if gate == "G9":
        c, out = t["checkers"], os.path.join(run, "independent")
        if c.get("independent_na"):
            rec = _timed(t, gate, lambda: fi.not_applicable(c["independent_na"], out), cost_log)
        else:
            ax = _latest(events, "AXIOM_AUDIT")
            audit = json.load(open(os.path.join(run, "axiom", "axiom-audit-record.json"))) if os.path.exists(os.path.join(run, "axiom", "axiom-audit-record.json")) else None
            decl = lean["theorems"][0]
            if not audit or audit["theorems"].get(decl, {}).get("axioms") is None:
                raise BatchError(f"{tid}: G9 needs a Gate 6 record with a footprint for {decl}")
            rec = _timed(t, gate, lambda: fi.check(lean["project"], lean["module"], decl, out, c["export_bin"], c["nanoda_bin"], audit["theorems"][decl]["axioms"],
                                                 export_cmd=c.get("export_cmd"), nanoda_cmd=c.get("nanoda_cmd"), max_s=c.get("max_seconds", 900),
                                                 min_free_gb=min(1.5, min_free_gb)), cost_log)
        return add(fi.event_fields(rec, _rel(t, os.path.join(out, "independent-check-record.json"))), f"AXIOMS-{tid}", f"INDEPCHECK-{tid}")
    if gate == "G11":
        g = fg.build(events)
        probs = fg.validate(g, events)
        path = os.path.join(run, "evidence", f"evidence-graph-v3-{len(events)}events.json")
        json.dump(g, open(path, "w"), indent=2, sort_keys=True)
        res = (f"PASS -- {len(g['nodes'])} nodes, {len(g['edges'])} edges, GRAPH_SHA256={g['graph_sha256']}" if not probs
               else f"FAIL -- graph invalid: {'; '.join(probs[:3])}")
        return add({"action": "EVIDENCE_GRAPH", "method": "fcve_graph.build (schema v3)", "result": res, "evidence": [_rel(t, path)]},
                   f"EVENT-001..EVENT-{len(events):03d}", f"GRAPH-{tid}")
    if gate == "G12":
        out = os.path.join(run, "report")
        def go():
            d = frp.load(L, root=root, lean=[tuple(x) for x in lean.get("lean_files", [])], waivers=t.get("waivers") or None, bridge_record=t.get("bridge_record"), repro_snapshot=t.get("repro_snapshot"), limitations_record=t.get("limitations_record"))
            if d["claims"] is None:
                raise BatchError(f"{tid}: claims.json not found; cannot draw the proof dependency diagram (§23)")
            tex = frp.build_tex(d)
            p = frp.check_structure(tex)
            if p:
                raise BatchError(f"{tid}: report structure check failed: {p}")
            os.makedirs(out, exist_ok=True)
            tp = os.path.join(out, "report.tex")
            open(tp, "w").write(tex)
            return frp.compile_report(tp, out, only_cached=False)
        comp = _timed(t, gate, go, cost_log)
        json.dump(comp, open(os.path.join(out, "compile-record.json"), "w"), indent=2, sort_keys=True)
        return add(frp.event_fields(comp, _rel(t, os.path.join(out, "report.tex")), _rel(t, os.path.join(out, "report.pdf"))), f"GRAPH-{tid}", f"REPORT-{tid}")
    raise BatchError(f"no automatic step for {gate}")


def write_receipt(t):
    d = os.path.join(t["run_dir"], "receipt")
    clash = [f for f in ("receipt.json", "verification-receipt.md") if os.path.exists(os.path.join(d, f))]
    if clash:
        raise BatchError(f"{t['id']}: refusing to overwrite existing {', '.join(clash)}")
    r = fr.build_receipt(t["ledger"], root=t["root"], waivers=t.get("waivers") or {}, limitations_record=t.get("limitations_record"))
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "verification-receipt.md"), "w").write(fr.render(r))
    json.dump(r, open(os.path.join(d, "receipt.json"), "w"), indent=2, sort_keys=True)
    return r


def _lock(t):
    p = os.path.join(t["run_dir"], ".fcve-batch.lock")
    os.makedirs(t["run_dir"], exist_ok=True)
    if os.path.exists(p):
        try:
            pid = int(open(p).read().strip())
            os.kill(pid, 0)
            return None  # a live process holds it
        except (ValueError, ProcessLookupError, PermissionError):
            pass  # stale lock
    open(p, "w").write(str(os.getpid()))
    return p


def run_batch(manifest, only=None, max_steps_per_theorem=40, log=print):
    """Advance every theorem as far as it can go without a human. Returns the summary."""
    floor = manifest["min_free_gb"]
    results, halted = [], None
    cost_log = os.path.join(manifest.get("out_dir", os.path.dirname(manifest["theorems"][0]["run_dir"])), "batch-cost-ledger.jsonl")
    for t in manifest["theorems"]:
        if only and t["id"] not in only:
            continue
        if halted:
            p = plan(t, floor); p.update(state="HALTED_DISK", detail=halted); results.append(p); continue
        lock = _lock(t)
        if lock is None:
            p = plan(t, floor); p.update(state="LOCKED", detail="another batch process holds this run"); results.append(p); continue
        try:
            steps = 0
            while True:
                p = plan(t, floor)
                if p["state"] != "READY" or steps >= max_steps_per_theorem:
                    break
                free = shutil.disk_usage(t["run_dir"]).free / 1e9
                if free < floor:
                    halted = f"only {free:.1f} GB free (< {floor}); halting the batch, remaining work stays pending"
                    p.update(state="HALTED_DISK", detail=halted); break
                log(f"[{t['id']}] {p['next']}: {p['detail']}")
                try:
                    if p["next"] == "RECEIPT":
                        write_receipt(t)
                    else:
                        run_step(t, p["next"], floor, cost_log)
                except (BatchError, fe.GateOrderError, fe.ArtifactError, fl.PreflightError, ValueError, frp.ReportError, fcomp.BackendUnavailable) as e:
                    p.update(state=f"ERROR:{p['next']}", detail=f"{type(e).__name__}: {e}"); break  # this theorem stops; the batch goes on
                steps += 1
            results.append(p)
        finally:
            if os.path.exists(lock):
                os.remove(lock)
    return summarize(results)


def summarize(results):
    counts = {}
    for r in results:
        k = r["state"].split(":")[0]
        counts[k] = counts.get(k, 0) + 1
    return {"generated_utc": _now(), "counts": counts, "theorems": results,
            "note": "COMPLETE means the mechanical gates ran and a receipt exists; it says nothing about the governance decision or correctness. No theorem is called 'verified' here."}


def cost_summary(cost_log):
    """§43 fields from the batch's own step timings; everything not measured is NOT RECORDED."""
    rows = [json.loads(l) for l in open(cost_log) if l.strip()] if os.path.exists(cost_log) else []
    by = lambda gates: round(sum(r["seconds"] for r in rows if r["step"] in gates), 1)
    return {"LEAN_BUILD_TIME": by({"G5"}), "COMPUTATIONAL_TEST_TIME": by({"G8", "G10"}), "CHECKER_TIME": by({"G9"}),
            "LATEX_BUILD_TIME": by({"G12"}), "MACHINE_TIME": by({r["step"] for r in rows}), "steps_recorded": len(rows),
            "HUMAN_TIME": NR, "MODEL_CALL_COUNT": NR, "MODEL_COST": NR, "TOTAL_COST": NR}


def render_summary(s, cost=None):
    L = [f"# Batch summary ({s['generated_utc']})", "", f"States: {s['counts']}", "", "_" + s["note"] + "_", "",
         "| Theorem | State | Next / detail | Done gates | Stale | Not configured |", "|---|---|---|---|---|---|"]
    for r in s["theorems"]:
        L.append(f"| {r['id']} | {r['state']} | {str(r.get('detail', ''))[:170].replace('|', '/')} | {','.join(r['done']) or '-'} | {','.join(r['stale_events']) or '-'} | {','.join(r['not_configured']) or '-'} |")
    if cost:
        L += ["", "## Cost ledger (§43)", ""] + [f"- {k}: {v}" for k, v in cost.items()]
    return "\n".join(L) + "\n"
