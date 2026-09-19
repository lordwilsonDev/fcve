#!/usr/bin/env python3
"""FCVE CLI over fcve_evidence.

  fcve.py append LEDGER --action A --reason R --input I --output O --method M --result X
                        [--evidence a,b] [--actor NAME] [--no-strict]
  fcve.py verify LEDGER            # hash chain + gate order
  fcve.py graph  LEDGER OUT.json [--legacy]   # --legacy = v1 shape (no evidence_class)
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fcve_evidence as fe
import fcve_claims as fc
import fcve_lean as fl
import fcve_axioms as fx
import fcve_semantic as fsem
import fcve_compute as fcomp
import fcve_independent as fi
import fcve_graph as fgr
import fcve_receipt as frc
import fcve_semantic as fs
import fcve_report as frp
import fcve_limits as flim
import fcve_batch as fbt

p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd", required=True)
a = sub.add_parser("append"); a.add_argument("ledger")
for k in ("action", "reason", "input", "output", "method", "result"):
    a.add_argument(f"--{k}", required=True)
a.add_argument("--evidence", default=""); a.add_argument("--actor", default="wilson+claude")
a.add_argument("--no-strict", action="store_true")
a.add_argument("--no-check-inputs", action="store_true", help="skip the check that every input id was produced by an earlier event")
a.add_argument("--root", default=None, help="dir evidence paths are relative to (default: cwd, then run dir)")
a.add_argument("--legacy-lemma-defs", action="store_true")
a.add_argument("--legacy-result-wording", action="store_true")
v = sub.add_parser("verify"); v.add_argument("ledger")
vc = sub.add_parser("validate-claims"); vc.add_argument("claims"); vc.add_argument("assumptions")
vc.add_argument("--legacy-lemma-defs", action="store_true", help="VCE-001 only: lemmas may omit surrounding_definitions")
sc = sub.add_parser("scaffold"); sc.add_argument("outdir"); sc.add_argument("--ids", default="CLAIM-001")
lb = sub.add_parser("lean-build"); lb.add_argument("project"); lb.add_argument("outdir")
lb.add_argument("--target"); lb.add_argument("--clean-room", action="store_true")
lb.add_argument("--min-free-gb", type=float, default=fl.DEFAULT_MIN_FREE_GB)
lb.add_argument("--ledger"); lb.add_argument("--input"); lb.add_argument("--output"); lb.add_argument("--reason", default="Build the formalization with the project's own toolchain (Gate 5)")
ax = sub.add_parser("axiom-audit"); ax.add_argument("project"); ax.add_argument("module"); ax.add_argument("outdir")
ax.add_argument("names", nargs="+"); ax.add_argument("--external", default="", help="comma list of vouched-for external axioms")
ax.add_argument("--ledger"); ax.add_argument("--input"); ax.add_argument("--output")
ax.add_argument("--reason", default="Record the axiom footprint of the headline theorem(s) (Gate 6)")
sm = sub.add_parser("semantic-check", help="validate a Gate 4/7 comparison record; optionally append the event")
sm.add_argument("record"); sm.add_argument("--lean-file"); sm.add_argument("--theorem")
sm.add_argument("--ledger"); sm.add_argument("--input"); sm.add_argument("--output"); sm.add_argument("--reason")
ss = sub.add_parser("scaffold-semantic"); ss.add_argument("gate", choices=["GATE4", "GATE7"]); ss.add_argument("claim_id")
ss.add_argument("--lean-file"); ss.add_argument("--theorem"); ss.add_argument("out")
cr = sub.add_parser("compute-run", help="run a test script (must emit an FCVE_RESULT line); optionally append the event")
cr.add_argument("script"); cr.add_argument("outdir"); cr.add_argument("--gate", type=int, choices=[8, 10], default=8)
cr.add_argument("--recheck-script"); cr.add_argument("--timeout", type=int, default=600)
cr.add_argument("--ledger"); cr.add_argument("--input"); cr.add_argument("--output"); cr.add_argument("--reason")
ic = sub.add_parser("independent-check", help="Gate 9: export + external re-check of one declaration")
ic.add_argument("project"); ic.add_argument("module"); ic.add_argument("decl"); ic.add_argument("outdir")
ic.add_argument("--export-bin", required=True); ic.add_argument("--nanoda-bin", required=True)
ic.add_argument("--audit-record", required=True, help="Gate 6 axiom-audit-record.json; its footprint for DECL is the permitted axiom set")
ic.add_argument("--keep-export", action="store_true"); ic.add_argument("--not-applicable", metavar="REASON")
ic.add_argument("--max-seconds", type=int, default=900); ic.add_argument("--stall-seconds", type=int, default=300)
ic.add_argument("--min-free-gb", type=float, default=1.5)
ic.add_argument("--ledger"); ic.add_argument("--input"); ic.add_argument("--output"); ic.add_argument("--reason")
bp = sub.add_parser("batch-plan", help="read-only: where every theorem in a manifest stands and what happens next")
bp.add_argument("manifest"); bp.add_argument("--only", action="append", default=[])
br = sub.add_parser("batch-run", help="advance every theorem as far as the mechanical gates allow; stops each at the next human gate")
br.add_argument("manifest"); br.add_argument("--only", action="append", default=[])
rp_ = sub.add_parser("report", help="assemble report.tex from the ledger and run files, structure-check it, compile it twice and check the logs (§51)")
rp_.add_argument("ledger"); rp_.add_argument("outdir"); rp_.add_argument("--lean", action="append", default=[], metavar="FILE:THEOREM")
rp_.add_argument("--root", help="dir the ledger's evidence paths are relative to (default: cwd, then the run dir)")
rp_.add_argument("--waive", action="append", default=[], metavar="GATE=REASON", help="explicit waiver of G10/ORDER; shown in the report")
rp_.add_argument("--bridge-record", help="Gate 7 semantic record with the reviewer-set bridge_verdict (auto-discovered if named semantic-gate7*record*.json in the run dir)")
rp_.add_argument("--repro-snapshot", help="reproduction snapshot (fcve.py repro-snapshot); used when the run has no build record")
rp_.add_argument("--limitations-record", help="reviewer-authored limitations (fcve.py scaffold-limitations); auto-found as reviewer-limitations*.json in the run dir")
rp_.add_argument("--author", default="Black Swan Labs FCVE"); rp_.add_argument("--no-compile", action="store_true")
rp_.add_argument("--allow-post-decision", action="store_true", help="regression only: build from a ledger that already has a GOVERNANCE_DECISION")
rp_.add_argument("--allow-network", action="store_true", help="let the compiler fetch uncached packages (recorded in the result)")
rp_.add_argument("--append", action="store_true"); rp_.add_argument("--input"); rp_.add_argument("--output"); rp_.add_argument("--reason")
rc = sub.add_parser("receipt", help="generate verification-receipt.md + receipt.json from the ledger and run records (§48)")
rc.add_argument("ledger"); rc.add_argument("outdir"); rc.add_argument("--root"); rc.add_argument("--limitations-record")
sl = sub.add_parser("scaffold-limitations", help="blank reviewer-limitations record"); sl.add_argument("claim_id"); sl.add_argument("out")
lc = sub.add_parser("limitations-check", help="validate a reviewer-limitations record"); lc.add_argument("record")
rc.add_argument("--waive", action="append", default=[], metavar="GATE=REASON", help="explicitly waive a waivable gate (G10, ORDER); shown in the receipt")
rcc = sub.add_parser("receipt-check", help="is a receipt.json still true of its ledger? (staleness, forgery, decision vs evidence)")
rcc.add_argument("ledger"); rcc.add_argument("receipt")
rs = sub.add_parser("repro-snapshot", help="read-only capture of repo URL/commit/clean-tree/toolchain for reproduction (labelled: captured after the run)")
rs.add_argument("project"); rs.add_argument("outdir"); rs.add_argument("--expect-commit", help="commit (or prefix) the run's own notes name; the snapshot reports whether HEAD matches")
rs.add_argument("--name", default="repro-snapshot.json")
g = sub.add_parser("graph", help="write the evidence graph (schema v3; --legacy = the v1 shape VCE-001/002 cite)")
g.add_argument("ledger"); g.add_argument("out"); g.add_argument("--legacy", action="store_true")
gc = sub.add_parser("graph-check", help="integrity + staleness of a graph file against its ledger (§25)")
gc.add_argument("ledger"); gc.add_argument("graph")
gv = sub.add_parser("graph-view", help="print one of the six §24 views")
gv.add_argument("ledger"); gv.add_argument("view", choices=sorted(fgr.VIEWS))
args = p.parse_args()

if args.cmd == "append":
    try:
        ev = fe.append_event(args.ledger, action=args.action, reason=args.reason, input=args.input,
                             output=args.output, method=args.method, result=args.result,
                             evidence=[e.strip() for e in args.evidence.split(",") if e.strip()],
                             actor=args.actor, strict=not args.no_strict,
                             root=args.root, legacy_lemma_defs=args.legacy_lemma_defs, check_inputs=not args.no_check_inputs,
                             legacy_result_wording=args.legacy_result_wording)
    except (fe.GateOrderError, fe.ArtifactError, ValueError) as e:
        sys.exit(f"REFUSED: {e}")
    print(f"{ev['event_id']} appended, hash={ev['event_hash'][:16]}...")
elif args.cmd == "verify":
    events = fe.read_ledger(args.ledger)
    probs = fe.verify_chain(events)
    probs += [f"order: {a} must precede {b}" for a, b in fe.order_violations([e["action"] for e in events])]
    print("\n".join(probs) if probs else f"OK: {len(events)} events, chain intact, order canonical")
    sys.exit(1 if probs else 0)
elif args.cmd == "validate-claims":
    probs = fc.validate_claims(json.load(open(args.claims)),
                               lenient=("surrounding_definitions",) if args.legacy_lemma_defs else ())
    probs += fc.validate_assumptions(json.load(open(args.assumptions)))
    print("\n".join(probs) if probs else "OK: claims and assumptions valid")
    sys.exit(1 if probs else 0)
elif args.cmd == "lean-build":
    try:
        rec = fl.run_build(args.project, args.outdir, target=args.target, clean_room=args.clean_room,
                           min_free_gb=args.min_free_gb)
    except fl.PreflightError as e:
        sys.exit(f"REFUSED: {e}")
    print(f"{rec['verdict']}: exit {rec['exit_code']} in {rec['duration_s']}s ({rec['kind']})"
          + (f"; failed: {', '.join(rec['failed_conditions'])}" if rec["failed_conditions"] else ""))
    if args.ledger:
        if not (args.input and args.output):
            sys.exit("--ledger needs --input and --output")
        rel = os.path.join(args.outdir, f"build-{rec['kind']}-record.json")
        ev = fe.append_event(args.ledger, reason=args.reason, input=args.input, output=args.output,
                             **fl.event_fields(rec, rel))
        print(f"{ev['event_id']} appended, hash={ev['event_hash'][:16]}...")
    sys.exit(0 if rec["verdict"] == "PASS" else 1)
elif args.cmd == "axiom-audit":
    rec = fx.audit(args.project, args.module, args.names, args.outdir,
                   external=[e for e in args.external.split(",") if e])
    print(f"{rec['verdict']}: footprint {rec['footprint'] or 'none'}"
          + (f"; reported {rec['reported']}" if rec["reported"] else "")
          + (f"; failures {rec['failures']}" if rec["failures"] else ""))
    if args.ledger:
        if not (args.input and args.output):
            sys.exit("--ledger needs --input and --output")
        ev = fe.append_event(args.ledger, reason=args.reason, input=args.input, output=args.output,
                             **fx.event_fields(rec, os.path.join(args.outdir, "axiom-audit-record.json")))
        print(f"{ev['event_id']} appended, hash={ev['event_hash'][:16]}...")
    sys.exit(0 if rec["verdict"] == "PASS" else 1)
elif args.cmd in ("semantic-check", "scaffold-semantic"):
    sigs = None
    if args.lean_file:
        if not args.theorem:
            sys.exit("--lean-file needs --theorem")
        try:
            sigs = fsem.lean_signals(fsem.extract_statement(open(args.lean_file).read(), args.theorem))
        except fsem.SemanticError as e:
            sys.exit(f"REFUSED: {e}")
    if args.cmd == "scaffold-semantic":
        if os.path.exists(args.out):
            sys.exit(f"REFUSED: {args.out} exists")
        json.dump(fsem.scaffold(args.gate, args.claim_id, sigs), open(args.out, "w"), indent=2)
        print(f"Scaffolded {args.out}; signals to address: {sigs or 'none found (not proof of a match)'}")
        sys.exit(0)
    rec = json.load(open(args.record))
    probs = fsem.validate(rec, sigs)
    if probs:
        print("INVALID:\n  " + "\n  ".join(probs)); sys.exit(1)
    outcome = fsem.gate_outcome(rec)
    print(f"OK: {rec['gate']} {rec['status']} -> {outcome}")
    if args.ledger:
        if not (args.input and args.output):
            sys.exit("--ledger needs --input and --output")
        action = "LEAN_FORMALIZATION_COMPARISON" if rec["gate"] == "GATE4" else "SEMANTIC_RE_AUDIT"
        ev = fe.append_event(args.ledger, action=action, method="semantic comparison (fcve_semantic checklist)",
                             result=f"{rec['status']} -> {outcome}", evidence=[args.record],
                             reason=args.reason or f"{rec['gate']} semantic comparison of source, normalized claim and Lean statement",
                             input=args.input, output=args.output)
        print(f"{ev['event_id']} appended, hash={ev['event_hash'][:16]}...")
    sys.exit(0 if outcome == "PASS" else 1)
elif args.cmd == "compute-run":
    try:
        rec = fcomp.run_check(args.script, args.outdir, gate=args.gate, recheck_script=args.recheck_script, timeout=args.timeout)
    except fcomp.BackendUnavailable as e:
        sys.exit(f"REFUSED: {e}")
    print(f"{rec['outcome']} (trust: {rec['trust']}); {rec['cases']} cases; domain: {rec['tested_domain'] or '-'}")
    print(f"categories not covered: {', '.join(rec['categories_not_covered'])}")
    if rec["trust"] == "UNVERIFIED":
        print("WARNING: counterexample is unverified; rerun independently (--recheck-script) before trusting it")
    if args.ledger:
        if not (args.input and args.output):
            sys.exit("--ledger needs --input and --output")
        ev = fe.append_event(args.ledger, reason=args.reason or "Computational test of the claim; evidence is not proof (§16)",
                             input=args.input, output=args.output,
                             **fcomp.event_fields(rec, os.path.join(args.outdir, os.path.splitext(os.path.basename(args.script))[0] + "-compute-record.json")))
        print(f"{ev['event_id']} appended, hash={ev['event_hash'][:16]}...")
    sys.exit(0 if rec["outcome"] not in ("RUN_FAILED", "DISAGREEMENT") else 1)
elif args.cmd == "independent-check":
    if args.not_applicable:
        rec = fi.not_applicable(args.not_applicable, args.outdir)
    else:
        th = json.load(open(args.audit_record)).get("theorems", {}).get(args.decl)
        if not th or th.get("axioms") is None:
            sys.exit(f"REFUSED: {args.decl} has no Gate 6 footprint in {args.audit_record}; run axiom-audit first")
        tick = 20
        rec = fi.check(args.project, args.module, args.decl, args.outdir, args.export_bin, args.nanoda_bin,
                       th["axioms"], keep_export=args.keep_export, tick_s=tick, stall_ticks=max(1, args.stall_seconds // tick),
                       max_s=args.max_seconds, min_free_gb=args.min_free_gb)
    print(f"{rec['result']}: {rec['reason']}")
    if args.ledger:
        if not (args.input and args.output):
            sys.exit("--ledger needs --input and --output")
        ev = fe.append_event(args.ledger, reason=args.reason or "Second verification route outside the Lean kernel (Gate 9)",
                             input=args.input, output=args.output,
                             **fi.event_fields(rec, os.path.join(args.outdir, "independent-check-record.json")))
        print(f"{ev['event_id']} appended, hash={ev['event_hash'][:16]}...")
    sys.exit(0 if rec["result"] == "INDEPENDENTLY_CHECKED" else 1)
elif args.cmd == "scaffold":
    cl, asm = fc.scaffold(tuple(args.ids.split(",")))
    os.makedirs(args.outdir, exist_ok=True)
    for name, d in (("claims.json", cl), ("assumptions.json", asm)):
        path = os.path.join(args.outdir, name)
        if os.path.exists(path):
            sys.exit(f"REFUSED: {path} exists")
        json.dump(d, open(path, "w"), indent=2)
    print(f"Scaffolded {args.outdir}/claims.json and assumptions.json")
elif args.cmd in ("batch-plan", "batch-run"):
    try:
        man = fbt.load_manifest(args.manifest)
    except fbt.BatchError as e:
        sys.exit(f"REFUSED: {e}")
    out_dir = man.get("out_dir") or os.path.dirname(os.path.abspath(args.manifest))
    man["out_dir"] = out_dir
    if args.cmd == "batch-plan":
        res = [fbt.plan(t, man["min_free_gb"]) for t in man["theorems"] if not args.only or t["id"] in args.only]
        summ = fbt.summarize(res)
    else:
        summ = fbt.run_batch(man, only=set(args.only) or None, log=lambda m: print(m, flush=True))
        os.makedirs(out_dir, exist_ok=True)
        cost = fbt.cost_summary(os.path.join(out_dir, "batch-cost-ledger.jsonl"))
        json.dump({**summ, "cost": cost}, open(os.path.join(out_dir, "batch-summary.json"), "w"), indent=2, sort_keys=True)
        open(os.path.join(out_dir, "batch-summary.md"), "w").write(fbt.render_summary(summ, cost))
    print(fbt.render_summary(summ))
    bad = [r for r in summ["theorems"] if r["state"].split(":")[0] in ("BLOCKED_FAILED", "ERROR", "HALTED_DISK", "LOCKED")]
    sys.exit(1 if bad else 0)
elif args.cmd == "repro-snapshot":
    try:
        rec = fl.snapshot(args.project, args.outdir, expect_commit=args.expect_commit, name=args.name)
    except fl.PreflightError as e:
        sys.exit(f"REFUSED: {e}")
    g_ = rec["git"]
    print(f"{rec['state']}: {g_.get('remote_url') or 'no remote'} @ {(g_.get('revision') or 'no commit')[:12]}; lean {rec['environment']['lean_toolchain_file']}; "
          f"matches expected commit: {rec['revision_matches_expected']}" + (f"; DIRTY files: {len(g_['dirty_files'])}" if g_.get("dirty") else ""))
    sys.exit(0 if rec["state"] == "CLEAN_AT_COMMIT" and rec["revision_matches_expected"] in (True, None) else 1)
elif args.cmd == "scaffold-limitations":
    if os.path.exists(args.out):
        sys.exit(f"REFUSED: {args.out} exists")
    json.dump(flim.scaffold(args.claim_id), open(args.out, "w"), indent=2); print(f"Scaffolded {args.out}; fill reviewer, statement and basis for each limitation")
elif args.cmd == "limitations-check":
    rec = json.load(open(args.record)); probs = flim.validate(rec)
    print("\n".join(probs) if probs else f"OK: {len(rec['limitations'])} limitation(s), {flim.info(rec)[0]} ({flim.info(rec)[1]})")
    sys.exit(1 if probs else 0)
elif args.cmd == "report":
    events = fe.read_ledger(args.ledger)
    acts = [e["action"] for e in events]
    if "EVIDENCE_GRAPH" not in acts:
        sys.exit("REFUSED: no EVIDENCE_GRAPH event yet; the report (Gate 12) follows the graph (Gate 11) (§2)")
    if "GOVERNANCE_DECISION" in acts and not args.allow_post_decision:
        sys.exit("REFUSED: ledger already has a GOVERNANCE_DECISION; the report (Gate 12) must precede it (Gate 13) (§2)")
    try:
        d = frp.load(args.ledger, root=args.root, lean=[tuple(x.rsplit(":", 1)) for x in args.lean], waivers=dict(w.split("=", 1) for w in args.waive), bridge_record=args.bridge_record, repro_snapshot=args.repro_snapshot, limitations_record=args.limitations_record)
        if d["claims"] is None:
            sys.exit("REFUSED: claims.json named in the ledger could not be found; the proof dependency diagram (§23) needs it. "
                     "Run from the project root or pass --root DIR (paths in this ledger are relative to it).")
        tex = frp.build_tex(d, author=args.author)
    except (frp.ReportError, fs.SemanticError) as e:
        sys.exit(f"REFUSED: {e}")
    probs = frp.check_structure(tex)
    if probs:
        sys.exit("REFUSED: structure check failed:\n  " + "\n  ".join(probs))
    os.makedirs(args.outdir, exist_ok=True)
    tex_path = os.path.join(args.outdir, "report.tex")
    if os.path.exists(tex_path):
        sys.exit(f"REFUSED: {tex_path} exists (reports are not overwritten)")
    open(tex_path, "w").write(tex)
    print(f"Wrote {tex_path}; structure OK (2 diagrams, 17 sections in §33 order, trust statement first)")
    if args.no_compile:
        sys.exit(0)
    comp = frp.compile_report(tex_path, args.outdir, only_cached=not args.allow_network)
    json.dump(comp, open(os.path.join(args.outdir, "compile-record.json"), "w"), indent=2, sort_keys=True)
    c = comp["final_counts"]
    print(f"{comp['verdict']}: {c} layout warnings={comp['layout_warnings']} compiler={comp['compiler']} (spec-named pdflatex used: {comp['spec_named_compiler_used']}; needed network: {comp['needed_network']})")
    if args.append:
        if not (args.input and args.output):
            sys.exit("--append needs --input and --output")
        ev = fe.append_event(args.ledger, reason=args.reason or "Assemble and compile the mathematician-facing report (Gate 12)", input=args.input, output=args.output,
                             **frp.event_fields(comp, os.path.join(args.outdir, "report.tex"), os.path.join(args.outdir, "report.pdf")))
        print(f"{ev['event_id']} appended, hash={ev['event_hash'][:16]}...")
    sys.exit(0 if comp["verdict"] == "PASS" else 1)
elif args.cmd == "receipt":
    try:
        waivers = dict(w.split("=", 1) for w in args.waive)
        rcpt = frc.build_receipt(args.ledger, root=args.root, waivers=waivers, limitations_record=args.limitations_record)
    except ValueError as e:
        sys.exit(f"REFUSED: {e}")
    md, js = os.path.join(args.outdir, "verification-receipt.md"), os.path.join(args.outdir, "receipt.json")
    for path in (md, js):
        if os.path.exists(path):
            sys.exit(f"REFUSED: {path} exists (receipts are not overwritten)")
    os.makedirs(args.outdir, exist_ok=True)
    open(md, "w").write(frc.render(rcpt)); json.dump(rcpt, open(js, "w"), indent=2, sort_keys=True)
    print(f"Wrote {md} and {js}; decision {rcpt['decision']}, blockers {rcpt['blockers'] or 'none'}")
    for p_ in rcpt["decision_problems"]:
        print(f"DECISION CHECK FAILED: {p_}")
    sys.exit(1 if rcpt["decision_problems"] else 0)
elif args.cmd == "receipt-check":
    probs = frc.check_receipt(json.load(open(args.receipt)), args.ledger)
    print("\n".join(probs) if probs else "OK: receipt is current with the ledger")
    sys.exit(1 if probs else 0)
elif args.cmd == "graph-check":
    events, gr = fe.read_ledger(args.ledger), json.load(open(args.graph))
    legacy = "schema_version" not in gr
    probs = fgr.validate_legacy(gr, events) if legacy else fgr.validate(gr, events)
    ei = fgr.event_integrity(events)
    print("\n".join(probs) if probs else
          f"OK: legacy v1 graph matches ledger, not stale ({len(events)} events; v1 structural defects are not checked -- see graph-check on a v3 rebuild)"
          if legacy else f"OK: graph v{gr['schema_version']} sound, current with ledger ({len(events)} events)")
    if ei["no_input_hash"] or ei["no_output_hash"]:
        print(f"note: {len(ei['no_output_hash'])} events have no INPUT/OUTPUT_HASH (legacy events; §25 fields not backfilled)")
    sys.exit(1 if probs else 0)
elif args.cmd == "graph-view":
    print(json.dumps(fgr.VIEWS[args.view](fgr.build(fe.read_ledger(args.ledger))), indent=1))
else:
    events = fe.read_ledger(args.ledger)
    gr = fe.build_graph(events) if args.legacy else fgr.build(events)
    json.dump(gr, open(args.out, "w"), indent=2, sort_keys=True)
    print(f"Wrote {len(gr['nodes'])} nodes, {len(gr['edges'])} edges to {args.out}\nGRAPH_SHA256: {gr['graph_sha256']}")
