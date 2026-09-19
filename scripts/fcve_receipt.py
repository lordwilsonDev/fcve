"""FCVE automated receipt (spec §26, §27, §28, §35, §43, §48, §53, §55).

Derives verification-receipt.md from the hash-chained ledger and, where present,
the structured records written by Steps 4-8. It does not write the verdict: the
governance decision is a recorded event. It CHECKS that decision against the
evidence ("recorded failure != passed gate", §26): PROMOTE is refused unless the
§53 pass condition holds or each gap is explicitly waived and shown.

Every field says where it came from. Anything not recorded reads NOT RECORDED --
never a plausible-looking default.
"""
import glob
import hashlib
import json
import os
import re

import fcve_evidence as fe
import fcve_graph as fg
from fcve_lean import _sha

NR = "NOT RECORDED"
VERDICTS = ("PROMOTE", "REPAIR", "REJECT", "RESEARCH", "STOP")
# §53 gates -> the ledger action that satisfies each
GATES = [("G0", "SOURCE_INTAKE"), ("G1", "CLAIM_EXTRACTION"), ("G2", "ASSUMPTION_EXTRACTION"),
         ("G3", "SEMANTIC_NORMALIZATION"), ("G4", "LEAN_FORMALIZATION_COMPARISON"), ("G5", "LEAN_BUILD"),
         ("G6", "AXIOM_AUDIT"), ("G7", "SEMANTIC_RE_AUDIT"), ("G8", "ADVERSARIAL_COMPUTATIONAL_TEST"),
         ("G9", "INDEPENDENT_CHECK"), ("G10", "COMPUTATIONAL_CHECK"), ("G11", "EVIDENCE_GRAPH"),
         ("G12", "REPORT_GENERATION"), ("G13", "GOVERNANCE_DECISION")]
WAIVABLE = {"G10", "ORDER"}  # G0-G7 can never be waived; G9 has its own N/A-with-reason path (§53)
KNOWN_AXIOMS = ["propext", "Classical.choice", "Quot.sound", "sorryAx", "Lean.ofReduceBool"]


def _last(events, *actions):
    hit = [e for e in events if e["action"] in actions]
    return hit[-1] if hit else None


def _base_dirs(ledger, root):
    return [root or os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(ledger)))]


def _find(rel, ledger, root):
    for b in _base_dirs(ledger, root):
        p = os.path.join(b, os.path.expanduser(rel))
        if os.path.isfile(p):
            return p
    return None


def _records(run_dir):
    def one(pat):
        hits = sorted(glob.glob(os.path.join(run_dir, "**", pat), recursive=True))
        return json.load(open(hits[-1])) if hits else None
    return {"build": one("build-*-record.json"), "axiom": one("axiom-audit-record.json"),
            "independent": one("independent-check-record.json"), "compute": one("*-compute-record.json")}


def gate_table(events, waivers=None):
    """§53 pass condition, gate by gate. Returns rows and PROMOTE blockers."""
    waivers = waivers or {}
    for g in waivers:
        if g not in WAIVABLE:
            raise ValueError(f"{g} cannot be waived (only {sorted(WAIVABLE)}); G0-G7 are mandatory (§53)")
    rows = []
    for gate, action in GATES:
        acts = ("ADVERSARIAL_COMPUTATIONAL_TEST", "CORRECTION_AND_RECHECK") if gate == "G8" else (action,)
        ev = _last(events, *acts)
        row = {"gate": gate, "action": action, "event": ev["event_id"] if ev else None, "result": ev["result"] if ev else None,
               "status": fg.classify_result(ev["result"]) if ev else "MISSING", "satisfied": False, "note": ""}
        st = row["status"]
        tok = (ev["result"].strip().split() or [""])[0] if ev else ""
        if ev is None:
            row["note"] = "no ledger event"
        elif gate in ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G12"):
            row["satisfied"] = st == "PASS"
        elif gate == "G8":  # COMPLETED: ran to a §16 outcome and no unresolved counterexample
            row["satisfied"] = st in ("PASS", "DIAGNOSTIC") and not tok.startswith("COUNTEREXAMPLE_FOUND")
            first = _last([e for e in events if e["action"] == "ADVERSARIAL_COMPUTATIONAL_TEST"], "ADVERSARIAL_COMPUTATIONAL_TEST")
            if first and first is not ev and fg.classify_result(first["result"]) in ("FAIL", "DISPUTED"):
                row["note"] = f"earlier {first['event_id']} recorded a failure; superseded by {ev['event_id']} (kept in Failure view)"
        elif gate == "G9":
            if tok == "NOT_APPLICABLE":
                row["satisfied"] = "--" in ev["result"] and bool(ev["result"].split("--", 1)[1].strip())
                row["note"] = "N/A" + ("" if row["satisfied"] else " WITHOUT a stated reason (§53 requires one)")
            else:
                row["satisfied"] = st == "PASS"
        elif gate == "G10":
            row["satisfied"] = st in ("PASS", "DIAGNOSTIC") and not tok.startswith("COUNTEREXAMPLE_FOUND")
        elif gate == "G11":
            problems = fg.validate(fg.build(events), events)
            row["satisfied"] = not problems
            row["note"] = "; ".join(problems[:2])
        elif gate == "G13":
            row["satisfied"] = True
            if tok.strip("-:") in VERDICTS:
                row["status"] = "DECIDED"
        if gate in waivers and not row["satisfied"]:
            row["waived"] = waivers[gate]
        rows.append(row)
    viol = fe.order_violations([e["action"] for e in events])
    rows.append({"gate": "ORDER", "action": "canonical chain (§2)", "event": None, "result": None,
                 "status": "PASS" if not viol else "FAIL", "satisfied": not viol,
                 "note": ", ".join(f"{a} must precede {b}" for a, b in viol),
                 **({"waived": waivers["ORDER"]} if viol and "ORDER" in waivers else {})})
    blockers = [r for r in rows if not r["satisfied"] and not r.get("waived") and r["gate"] != "G13"]
    return rows, blockers


def check_decision(events, rows, blockers, allow_pending=False):
    """Problems with the recorded governance decision, given the evidence."""
    dec = _last(events, "GOVERNANCE_DECISION")
    if dec is None:
        # A report (Gate 12) legitimately precedes the decision (Gate 13, §2).
        return ([], "PENDING") if allow_pending else (["no GOVERNANCE_DECISION event (Gate 13)"], None)
    verdict = (dec["result"].strip().split() or [""])[0].strip("-:")
    probs = []
    if verdict not in VERDICTS:
        probs.append(f"decision {verdict!r} is not one of {VERDICTS} (§26)")
    if verdict == "PROMOTE" and blockers:
        probs.append("PROMOTE not supported by §53: " + "; ".join(f"{b['gate']} ({b['status']}{': ' + b['note'] if b['note'] else ''})" for b in blockers))
    norm = _last(events, "SEMANTIC_NORMALIZATION")
    if norm:
        t = norm["result"].strip().split()[0]
        if t == "MISMATCH" and verdict != "STOP":
            probs.append("normalization MISMATCH requires STOP (§11)")
        if t == "UNCLEAR" and verdict != "REPAIR":
            probs.append("normalization UNCLEAR requires REPAIR (§11)")
    return probs, verdict


def _legacy_footprint(text):
    """Footprint from a legacy result line. Only the list stated before the word
    'only' counts: 'propext, Quot.sound only. NO Classical.choice' must NOT yield
    Classical.choice (a negated mention is not a dependency). No 'only' -> None,
    reported as NOT RECORDED rather than guessed."""
    m = re.search(r"^(?:\w+\s*--\s*)?(.*?)\s+only\b", text.strip(), re.S)
    return [a for a in KNOWN_AXIOMS if a in m.group(1)] if m else None


def _axioms(ev, rec):
    if rec:
        return sorted(rec["footprint"]), sorted({a for v in rec["reported"].values() for a in v}), f"record:axiom-audit-record.json"
    if ev:
        return _legacy_footprint(ev["result"]), [], f"parsed-legacy-text:{ev['event_id']}"
    return None, [], NR


def build_receipt(ledger, root=None, waivers=None, run_dir=None, allow_pending=False, limitations_record=None):
    events = fe.read_ledger(ledger)
    run_dir = run_dir or os.path.dirname(os.path.dirname(os.path.abspath(ledger)))
    rec = _records(run_dir)
    rows, blockers = gate_table(events, waivers)
    probs, verdict = check_decision(events, rows, blockers, allow_pending)
    graph = fg.build(events)
    F, src = {}, {}

    def put(k, v, s):
        F[k], src[k] = v, s

    intake = _last(events, "SOURCE_INTAKE"); p = None
    if intake:
        f = next((e for e in intake["evidence"] if not e.endswith("metadata.json")), None)
        p = _find(f, ledger, root) if f else None
    put("SOURCE HASH", f"sha256:{_sha(p)} ({os.path.relpath(p, run_dir) if p else ''})" if p else NR,
        "file-hash (computed now from the preserved source)" if p else NR)
    claims_path = _find(next((e for e in (_last(events, "CLAIM_EXTRACTION") or {"evidence": []})["evidence"] if e.endswith("claims.json")), ""), ledger, root) if _last(events, "CLAIM_EXTRACTION") else None
    claim0 = json.load(open(claims_path))["claims"][0] if claims_path else None
    put("THEOREM ID", f"{claim0['claim_id']} ({claim0.get('theorem_name', '')})" if claim0 else NR, "claims.json" if claim0 else NR)
    put("CLAIM", claim0["statement_verbatim"] if claim0 else NR, "claims.json" if claim0 else NR)
    nm = _last(events, "SEMANTIC_NORMALIZATION")
    put("NORMALIZED CLAIM", f"{(nm['evidence'] or ['?'])[0]} -- {nm['result'].split()[0]}" if nm else NR, f"ledger:{nm['event_id']}" if nm else NR)
    g4 = _last(events, "LEAN_FORMALIZATION_COMPARISON")
    theorems = rec["axiom"]["names"] if rec["axiom"] else []
    put("LEAN STATEMENT", (", ".join(theorems) + " -- " if theorems else "") + (f"Gate 4: {g4['result'].split()[0]}" if g4 else NR), "record:axiom-audit + ledger" if theorems else (f"ledger:{g4['event_id']}" if g4 else NR))
    b = _last(events, "LEAN_BUILD"); br = rec["build"]
    if br:
        put("LEAN VERSION", br["environment"]["lean_version_actual"], "record:build-record.json")
        put("MATHLIB VERSION", br["environment"].get("mathlib_rev") or NR, "record:build-record.json")
        put("BUILD RESULT", f"{br['verdict']} -- exit {br['exit_code']}, {br['kind']}, sorry-scan text-only" + (f", git {br['git']['revision'][:12]}" if br["git"].get("revision") else ""), "record:build-record.json")
    elif b:
        lv = re.search(r"Lean v?(\d+\.\d+\.\d+)", b["method"]); mv = re.search(r"Mathlib ([^,;)]+)", b["method"])
        put("LEAN VERSION", lv.group(1) if lv else NR, f"parsed-legacy-text:{b['event_id']}")
        put("MATHLIB VERSION", mv.group(1).strip() if mv else NR, f"parsed-legacy-text:{b['event_id']}")
        put("BUILD RESULT", b["result"], f"ledger:{b['event_id']}")
    else:
        for k in ("LEAN VERSION", "MATHLIB VERSION", "BUILD RESULT"):
            put(k, NR, NR)
    fp, reported, asrc = _axioms(_last(events, "AXIOM_AUDIT"), rec["axiom"])
    put("AXIOM FOOTPRINT", NR if fp is None else (", ".join(fp) or "none") + (f"  [reported: {', '.join(reported)}]" if reported else ""),
        asrc if fp is not None else f"{asrc} (footprint not stated in a parseable form; see the event text)")
    ic = _last(events, "INDEPENDENT_CHECK")
    if rec["independent"]:
        put("INDEPENDENT CHECK", f"{rec['independent']['result']} -- {rec['independent']['reason']}", "record:independent-check-record.json")
    elif ic:
        put("INDEPENDENT CHECK", ic["result"] + ("  (legacy wording)" if not ic["result"].startswith(fe.INDEPENDENT_RESULT_PREFIXES) else ""), f"ledger:{ic['event_id']}")
    else:
        put("INDEPENDENT CHECK", NR, NR)
    cc, g8 = _last(events, "COMPUTATIONAL_CHECK"), _last(events, "ADVERSARIAL_COMPUTATIONAL_TEST", "CORRECTION_AND_RECHECK")
    put("COMPUTATIONAL TEST", (cc["result"] + " [diagnostic, not proof]") if cc else "NOT RUN (no Gate 10 event)", f"ledger:{cc['event_id']}" if cc else "ledger: absent")
    put("COUNTEREXAMPLE SEARCH", (g8["result"] + " [diagnostic, not proof]") if g8 else "NOT RUN (no Gate 8 event)", f"ledger:{g8['event_id']}" if g8 else "ledger: absent")
    g7 = _last(events, "SEMANTIC_RE_AUDIT")
    put("SEMANTIC MATCH", f"Gate 4: {g4['result'].split()[0] if g4 else NR}; Gate 7: {g7['result'] if g7 else NR}", "ledger")
    # §35: level supported BY RECORDED EVIDENCE; this tool does not re-run anything.
    sat = {r["gate"]: r["satisfied"] for r in rows}
    lvl = 0
    if p:
        lvl = 1
        if sat["G5"] and (br or (b and re.search(r"Lean v?\d", b["method"]))):
            lvl = 2
            if sat["G6"]:
                lvl = 3
                if ic and (rec["independent"] and rec["independent"]["result"] == "INDEPENDENTLY_CHECKED" or (not rec["independent"] and sat["G9"] and ic["result"].split()[0] != "NOT_APPLICABLE")):
                    lvl = 4
    put("REPRODUCIBILITY LEVEL", f"R{lvl} (ceiling supported by recorded evidence; NOT re-run by this tool; R5 needs full-package rebuild, not assessed)", "derived: §35 rules")
    put("GRAPH HASH", f"v3 {graph['graph_sha256']} (covers {graph['event_count']} events through {events[-1]['event_id']})", "derived from ledger")
    dur = {"LEAN_BUILD_TIME": br["duration_s"] if br else None,
           "COMPUTATIONAL_TEST_TIME": rec["compute"]["run"]["duration_s"] if rec["compute"] else None,
           "CHECKER_TIME": rec["independent"]["export"]["seconds"] if rec["independent"] else None}
    put("COST", f"{len(events)} ledger events; " + "; ".join(f"{k}={v if v is not None else NR}" for k, v in dur.items()) + f"; HUMAN_TIME, MODEL_CALL_COUNT, MODEL_COST, LATEX_BUILD_TIME={NR} (no cost ledger, §43)", "records" if any(v is not None for v in dur.values()) else "ledger only")
    put("FINAL DECISION", f"{verdict}" + (" -- NOT SUPPORTED BY THE EVIDENCE (see check)" if probs else ""), "ledger:GOVERNANCE_DECISION")

    lim = []
    lrec = None
    if limitations_record:
        import fcve_limits  # local: keeps the receipt usable without it
        lrec = json.load(open(limitations_record))
        probs_l = fcve_limits.validate(lrec)
        if probs_l:
            raise ValueError("reviewer limitations record invalid: " + "; ".join(probs_l[:3]))
    for r in rows:
        if r["gate"] != "G13" and not r["satisfied"]:
            lim.append(f"{r['gate']} ({r['action']}): {r['status']}" + (f" -- WAIVED: {r['waived']}" if r.get("waived") else "") + (f" [{r['note']}]" if r["note"] else ""))
        elif r["note"]:
            lim.append(f"{r['gate']}: {r['note']}")
    if reported:
        lim.append(f"classical/external axioms in footprint: {', '.join(reported)}")
    if br:
        lim.append("build sorry-scan is text-only; real check is the axiom audit's sorryAx (§38)")
    if F["COMPUTATIONAL TEST"].startswith("NOT RUN") or F["COUNTEREXAMPLE SEARCH"].startswith("NOT RUN"):
        lim.append("computational evidence is diagnostic only and is never formal proof (§16, §18)")
    ei = fg.event_integrity(events)
    if ei["no_output_hash"]:
        lim.append(f"{len(ei['no_output_hash'])}/{len(events)} events lack INPUT/OUTPUT_HASH (§25; legacy events, not backfilled)")
    for e in events:
        if e["action"] in fe.COMPUTATIONAL_ACTIONS and not e["result"].startswith(fe.COMPUTATIONAL_RESULT_PREFIXES):
            lim.append(f"{e['event_id']} uses non-§16 wording ({e['result'].split()[0]}); read as DIAGNOSTIC")
    if lrec:  # reviewer-stated limitations are ADDED, never substituted for the derived ones
        lim += [f"{it['statement'].rstrip('.')} ({fcve_limits.tag(lrec)})" for it in lrec["limitations"]]
    dec = _last(events, "GOVERNANCE_DECISION")
    return {"receipt_version": 1, "ledger": os.path.abspath(ledger), "covers_through_event": events[-1]["event_id"],
            "covers_through_hash": events[-1]["event_hash"], "graph_sha256_v3": graph["graph_sha256"],
            "fields": F, "sources": src, "gates": rows, "blockers": [b["gate"] for b in blockers],
            "waivers": waivers or {}, "decision": verdict, "decision_problems": probs, "limitations": lim,
            "repro_level": lvl, "claim_id": claim0["claim_id"] if claim0 else None,
            "trust": trust_statement(F, fp, ic, cc, g8, lim, claim0), "decision_event": dec["event_id"] if dec else None}


def _lead(text):
    """The outcome token/phrase before the explanation: 'X -- why' or 'X (why)' -> 'X'. Never cuts mid-sentence."""
    return re.split(r"\s+--\s+|\s+\(", text.strip(), maxsplit=1)[0].strip()


_IC_GLOSS = {
    "CHECKER_INCOMPATIBLE": "no verdict: the external checker could not process this proof's export",
    "CHECKER_UNAVAILABLE": "no verdict: no external checker was available or the run was cut off before it finished",
    "CHECKER_DISAGREEMENT": "the external checker disagreed with the Lean kernel; this needs investigation",
    "NOT_APPLICABLE": "not applicable to this claim",
}


def plain_independent_status(field_text):
    """The recorded independent-check status with a plain-language gloss for the §17 tokens a
    non-specialist would not know. Text before ' -- ' / ' (' is kept as recorded."""
    lead = _lead(field_text.replace("  (legacy wording)", ""))
    if lead == "PASS":
        return "INDEPENDENTLY_CHECKED (recorded before the Section 17 vocabulary existed, as PASS)"
    for tok, gloss in _IC_GLOSS.items():
        if lead.startswith(tok):
            return f"{lead} ({gloss})"
    return lead


def trust_statement(F, fp, ic, cc, g8, lim, claim0):
    """§27 template, filled from recorded facts only. Full explanations live in the sections it
    points to; the statement itself carries outcomes, not truncated prose."""
    outs = []
    for e in (g8, cc):
        if e and _lead(e["result"]) not in outs:
            outs.append(_lead(e["result"]))
    comp = "; ".join(outs) or "no computational test recorded"
    icw = plain_independent_status(F["INDEPENDENT CHECK"])
    return (f"**Trust Statement.** The formal result was checked using Lean {F['LEAN VERSION']} under the pinned project environment "
            f"(Mathlib {F['MATHLIB VERSION']}). The theorem {claim0['claim_id'] if claim0 else NR} was kernel-checked with axiom footprint "
            f"{(', '.join(fp) or 'none') if fp is not None else NR}. Independent checking status is {icw}. Computational/adversarial testing produced: {comp} (diagnostic only). "
            f"The remaining trust limitations are: {'; '.join(l.rstrip('.') for l in lim) or 'none recorded'}. This report does not claim that computational testing "
            f"constitutes formal proof or that formalization alone establishes the truth of the original informal statement.")


def render(r):
    F = r["fields"]
    order = ["THEOREM ID", "SOURCE HASH", "CLAIM", "NORMALIZED CLAIM", "LEAN STATEMENT", "LEAN VERSION", "MATHLIB VERSION", "BUILD RESULT",
             "AXIOM FOOTPRINT", "INDEPENDENT CHECK", "COMPUTATIONAL TEST", "COUNTEREXAMPLE SEARCH", "SEMANTIC MATCH",
             "REPRODUCIBILITY LEVEL", "GRAPH HASH", "COST", "FINAL DECISION"]
    L = [f"# Verification Receipt — {r['claim_id'] or NR} (generated)", "",
         "_Generated from the ledger and run records by `fcve.py receipt`. Nothing here is hand-written; every field's source is listed at the end._", ""]
    if r["decision_problems"]:
        L += ["> **DECISION CHECK FAILED** — the recorded decision is not supported by the evidence:"] + [f"> - {p}" for p in r["decision_problems"]] + [""]
    L += [r["trust"], "", "| Field | Value |", "|---|---|"]
    L += [f"| {k} | {F[k].replace('|', '/')} |" for k in order]
    L += [f"| LIMITATIONS | {'; '.join(r['limitations']).replace('|', '/') or 'none recorded'} |", "", "## Status (§55)", "", "```"]
    def gs(g): return next((x for x in r["gates"] if x["gate"] == g), {"status": "MISSING", "satisfied": False})
    def show(g):
        x = gs(g)
        if x.get("waived"):
            return f"{x['status']} -- WAIVED ({x['waived']})"
        return ("PASS" if x["satisfied"] and x["status"] in ("PASS", "DECIDED") else "DIAGNOSTIC (no counterexample in tested domain)" if x["satisfied"] and x["status"] == "DIAGNOSTIC"
                           else "NOT RUN" if x["status"] == "MISSING" else f"{x['status']}" + (" (waived)" if x.get("waived") else ""))
    for lab, g in (("FORMAL PROOF (build)", "G5"), ("AXIOM AUDIT", "G6"), ("SEMANTIC MATCH (Gate 4)", "G4"), ("SEMANTIC RE-AUDIT (Gate 7)", "G7"),
                   ("INDEPENDENT CHECK", "G9"), ("COUNTEREXAMPLE SEARCH", "G8"), ("COMPUTATIONAL TEST", "G10")):
        L.append(f"{lab + ':':<30}{show(g)}")
    L += [f"{'REPRODUCIBILITY:':<30}R{r['repro_level']} (evidence-supported ceiling)", f"{'GOVERNANCE DECISION:':<30}{r['decision']}" + ("  <-- NOT SUPPORTED" if r["decision_problems"] else ""), "```", "",
          "## §53 gate table", "", "| Gate | Ledger action | Event | Status | Satisfied | Note |", "|---|---|---|---|---|---|"]
    for x in r["gates"]:
        L.append(f"| {x['gate']} | {x['action']} | {x['event'] or '-'} | {x['status']} | {'yes' if x['satisfied'] else ('WAIVED: ' + x['waived'] if x.get('waived') else 'NO')} | {x['note'].replace('|', '/')} |")
    L += ["", "## Limitations table (§28) — headline claim only", "",
          "| Claim | Formal Proof | Axiom Audit | Independent Check | Computational Test | Semantic Match | Limitation |", "|---|---|---|---|---|---|---|",
          f"| {r['claim_id'] or NR} | {show('G5')} | {show('G6')} | {show('G9')} | {show('G10')} | {show('G4')} / {show('G7')} | {'; '.join(r['limitations'][:2]).replace('|', '/') or 'None recorded'} |",
          "", "_Per-lemma rows need per-lemma records; the ledger holds results for the headline theorem only, so none are invented._", "",
          "## Provenance of each field", ""] + [f"- **{k}** — {r['sources'].get(k, NR)}" for k in order]
    L += ["", f"Covers ledger through `{r['covers_through_event']}` (`{r['covers_through_hash'][:16]}…`). Run `fcve.py receipt-check` to detect staleness."]
    return "\n".join(L) + "\n"


def permitted_status(R, ignore=()):
    """What the recorded evidence PERMITS (§26, §53, §11) -- explicitly not the decision.
    Lets the report (Gate 12) answer 'what is the status?' without asserting a verdict that
    is only recorded later at Gate 13."""
    blockers = [r for r in R["gates"] if r["gate"] in R["blockers"] and r["gate"] not in ignore]
    waived = [r for r in R["gates"] if r.get("waived") and not r["satisfied"]]
    reasons = [f"{b['gate']} ({b['action'].lower().replace('_', ' ')}): {b['status'].lower().replace('_', ' ')}" + (f" -- {b['note']}" if b["note"] else "") for b in blockers]
    forced = None
    norm = next((r for r in R["gates"] if r["gate"] == "G3"), None)
    if norm and norm.get("result"):
        t = norm["result"].split()[0]
        forced = "STOP" if t == "MISMATCH" else "REPAIR" if t == "UNCLEAR" else None
    return {"promote_supported": not blockers and forced is None, "blockers": reasons, "waived": [f"{w['gate']}: {w['waived']}" for w in waived],
            "forced_verdict": forced}


def check_receipt(receipt, ledger):
    """Is the receipt still true of the ledger? (the stale-hash lesson, §25)"""
    events = fe.read_ledger(ledger)
    probs = [f"ledger: {p}" for p in fe.verify_chain(events)]
    ids = [e["event_id"] for e in events]
    if receipt["covers_through_event"] not in ids:
        return probs + [f"covers {receipt['covers_through_event']} which is not in the ledger"]
    n = ids.index(receipt["covers_through_event"]) + 1
    if events[n - 1]["event_hash"] != receipt["covers_through_hash"]:
        probs.append("ledger history differs from the receipt's (event hash mismatch)")
    if fg.build(events[:n])["graph_sha256"] != receipt["graph_sha256_v3"]:
        probs.append("receipt's graph hash does not match a rebuild of the events it covers")
    if n < len(events):
        probs.append(f"STALE: ledger has {len(events) - n} event(s) after {receipt['covers_through_event']}; the receipt's graph hash/decision may be out of date")
    return probs
