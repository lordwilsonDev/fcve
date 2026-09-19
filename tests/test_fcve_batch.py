import json, os, shutil, stat, sys, tempfile, textwrap, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "tests"))
import fcve_batch as fb, fcve_evidence as fe, fcve_claims as fc
from test_fcve_lean import make_project, HAVE
HAVE_TEC = bool(shutil.which("tectonic") or shutil.which("pdflatex"))
META = '{"meta":{"exporter":{"name":"lean4export","version":"3.1.0"},"format":{"version":"3.1.0"},"lean":{"githash":"x","version":"4.34.0"}}}'

def exe(d, name, body):
    p = os.path.join(d, name)
    with open(p, "w") as f: f.write("#!/bin/sh\n" + textwrap.dedent(body))
    os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR); return p

def py(d, name, outcome, dom="n in [0,9]", cases=10):
    p = os.path.join(d, name)
    with open(p, "w") as f: f.write("import json\nprint('FCVE_RESULT: ' + json.dumps(%r))\n" % {"outcome": outcome, "tested_domain": dom, "cases": cases})
    return p

class Fx:
    """A batch workspace: real tiny Lean projects, human gates seeded like a person would."""
    def __init__(self, tc):
        self.t = tempfile.TemporaryDirectory(); tc.addCleanup(self.t.cleanup); self.d = self.t.name
        self.exp = exe(self.d, "exp.sh", f"printf '%s\\n' '{META}'\nprintf '{{\"in\":1}}\\n'\n")
        self.nan = exe(self.d, "nan.sh", "cat <<'EOF'\ntheorem t : True\nChecked 5 declarations with no errors\nEOF\n")
        self.ok8, self.ok10 = py(self.d, "g8.py", "NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN"), py(self.d, "g10.py", "NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN")

    def theorem(self, tid, body="theorem t : 1 + 1 = 2 := rfl\n", upto="G4", g7=True, full=True):
        proj, run = os.path.join(self.d, f"proj-{tid}"), os.path.join(self.d, f"run-{tid}")
        make_project(proj, body)
        for sub in ("source", "claims", "normalized", "lean", "evidence"): os.makedirs(os.path.join(run, sub))
        w = lambda rel, txt: open(os.path.join(run, rel), "w").write(txt)
        w("source/original.md", f"Claim {tid}: 1+1=2."); w("normalized/n.md", "# Normalized\n\n$1+1=2$, **MATCH**.\n"); w("lean/g4.md", "# Gate 4\n\nMATCH\n")
        cl, asm = fc.scaffold(("CLAIM-001",)); cl["claims"][0].update(theorem_name="t", source_location="s", statement_verbatim="1 + 1 = 2",
                                                                          proof_structure={"method": "by computation"})
        json.dump(cl, open(os.path.join(run, "claims/claims.json"), "w")); asm["source_assumptions"][0]["statement"] = "none"
        json.dump(asm, open(os.path.join(run, "claims/assumptions.json"), "w"))
        L = os.path.join(run, "evidence", "event-ledger.jsonl")
        def add(action, i, o, res, ev): fe.append_event(L, action=action, reason="seeded as a person would", input=i, output=o, method="manual", result=res, evidence=ev, root=run)
        seq = [("SOURCE_INTAKE", "source/original.md", f"SOURCE-{tid}", "PASS", ["source/original.md"]),
               ("CLAIM_EXTRACTION", f"SOURCE-{tid}", f"CLAIM-{tid}", "PASS", ["claims/claims.json"]),
               ("ASSUMPTION_EXTRACTION", f"CLAIM-{tid}", f"ASSUME-{tid}", "PASS", ["claims/assumptions.json"]),
               ("SEMANTIC_NORMALIZATION", f"CLAIM-{tid}", f"NORMALIZED-{tid}", "MATCH", ["normalized/n.md"]),
               ("LEAN_FORMALIZATION_COMPARISON", f"NORMALIZED-{tid}", f"FORMAL-{tid}", "MATCH", ["lean/g4.md"])]
        for a in seq[:[g for g in ("G0", "G1", "G2", "G3", "G4")].index(upto) + 1]: add(*a)
        t = {"id": tid, "run_dir": run, "ledger": L, "root": run,
             "lean": {"project": proj, "module": "Mini", "theorems": ["t"], "lean_files": [[os.path.join(proj, "Mini.lean"), "t"]]},
             "compute": {"gate8": self.ok8, "gate10": self.ok10},
             "checkers": {"export_bin": self.exp, "nanoda_bin": self.nan, "export_cmd": [self.exp], "nanoda_cmd": [self.nan]}}
        if not full: t.pop("checkers"); t["compute"].pop("gate10")
        t["_add"] = add; return t

    def manifest(self, *ts, floor=0.1):
        return {"min_free_gb": floor, "out_dir": self.d, "theorems": list(ts)}

@unittest.skipUnless(HAVE, "needs lake + Lean v4.34.0")
class Run(unittest.TestCase):
    def setUp(self): self.fx = Fx(self)

    def test_runs_mechanical_gates_and_stops_at_g7_never_fabricating_it(self):
        t = self.fx.theorem("A"); m = self.fx.manifest(t)
        s = fb.run_batch(m, log=lambda *_: None); r = s["theorems"][0]
        self.assertEqual(r["state"], "AWAITING_REVIEW:G7"); self.assertEqual(r["done"], ["G0", "G1", "G2", "G3", "G4", "G5", "G6"])
        acts = [e["action"] for e in fe.read_ledger(t["ledger"])]
        self.assertNotIn("SEMANTIC_RE_AUDIT", acts); self.assertNotIn("GOVERNANCE_DECISION", acts)
        self.assertIn("fcve.py scaffold-semantic GATE7", r["detail"])

    @unittest.skipUnless(HAVE_TEC, "needs tectonic or pdflatex")
    def test_full_path_to_g13_then_receipt_after_the_human_decision(self):
        t = self.fx.theorem("A"); m = self.fx.manifest(t); q = lambda *_: None
        fb.run_batch(m, log=q)
        t["_add"]("SEMANTIC_RE_AUDIT", f"FORMAL-A,AXIOMS-A", "REAUDIT-A", "PASS -- no undisclosed semantic change", ["lean/g4.md"])
        s = fb.run_batch(m, log=q); r = s["theorems"][0]
        self.assertEqual(r["state"], "AWAITING_REVIEW:G13", r)
        ev = fe.read_ledger(t["ledger"]); acts = [e["action"] for e in ev]
        self.assertEqual(acts[5:], ["LEAN_BUILD", "AXIOM_AUDIT", "SEMANTIC_RE_AUDIT", "ADVERSARIAL_COMPUTATIONAL_TEST", "INDEPENDENT_CHECK",
                                    "COMPUTATIONAL_CHECK", "EVIDENCE_GRAPH", "REPORT_GENERATION"])
        self.assertEqual(fe.verify_chain(ev), []); self.assertEqual(fe.order_violations(acts), [])
        res = {e["action"]: e["result"] for e in ev}
        self.assertTrue(res["LEAN_BUILD"].startswith("PASS")); self.assertTrue(res["INDEPENDENT_CHECK"].startswith("INDEPENDENTLY_CHECKED"))
        self.assertTrue(res["REPORT_GENERATION"].startswith("PASS")); self.assertTrue(res["ADVERSARIAL_COMPUTATIONAL_TEST"].startswith("NO_COUNTEREXAMPLE"))
        self.assertTrue(os.path.exists(os.path.join(t["run_dir"], "report", "report.pdf")))
        self.assertTrue(all(e.get("output_hash") for e in ev if e["actor"] == "fcve-batch"))
        t["_add"]("GOVERNANCE_DECISION", f"GRAPH-A,REPORT-A", "DECISION-A", "PROMOTE -- all gates satisfied", ["receipt/verification-receipt.md"])
        s = fb.run_batch(m, log=q); self.assertEqual(s["theorems"][0]["state"], "COMPLETE")
        rc = json.load(open(os.path.join(t["run_dir"], "receipt", "receipt.json"))); self.assertEqual(rc["decision"], "PROMOTE")
        cost = fb.cost_summary(os.path.join(self.fx.d, "batch-cost-ledger.jsonl"))
        self.assertGreater(cost["LEAN_BUILD_TIME"], 0); self.assertEqual(cost["HUMAN_TIME"], fb.NR); self.assertEqual(cost["TOTAL_COST"], fb.NR)

    def test_one_failing_theorem_never_stops_the_others(self):
        good, bad, waiting = self.fx.theorem("A"), self.fx.theorem("B", "theorem t : 1 + 1 = 3 := rfl\n"), self.fx.theorem("C", upto="G3")
        s = fb.run_batch(self.fx.manifest(bad, good, waiting), log=lambda *_: None)
        st = {r["id"]: r["state"] for r in s["theorems"]}
        self.assertEqual(st, {"B": "BLOCKED_FAILED:G5", "A": "AWAITING_REVIEW:G7", "C": "AWAITING_REVIEW:G4"})
        acts_b = [e["action"] for e in fe.read_ledger(bad["ledger"])]
        self.assertEqual(acts_b[-1], "LEAN_BUILD"); self.assertNotIn("AXIOM_AUDIT", acts_b)   # failure recorded, nothing downstream ran
        self.assertTrue(fe.read_ledger(bad["ledger"])[-1]["result"].startswith("FAIL"))
        self.assertEqual(len(fe.read_ledger(waiting["ledger"])), 4)                            # C untouched: never fabricated G4
        self.assertEqual(s["counts"], {"BLOCKED_FAILED": 1, "AWAITING_REVIEW": 2}); self.assertIn("No theorem is called 'verified'", s["note"])

    def test_resume_is_idempotent(self):
        t = self.fx.theorem("A"); m = self.fx.manifest(t)
        fb.run_batch(m, log=lambda *_: None); n = len(fe.read_ledger(t["ledger"]))
        fb.run_batch(m, log=lambda *_: None); self.assertEqual(len(fe.read_ledger(t["ledger"])), n)

    def test_theorems_have_isolated_ledgers(self):
        a, b = self.fx.theorem("A"), self.fx.theorem("B"); fb.run_batch(self.fx.manifest(a, b), log=lambda *_: None)
        for t in (a, b):
            self.assertTrue(all(e["output"].endswith(t["id"]) or e["output"].endswith("original.md") or t["id"] in e["output"] for e in fe.read_ledger(t["ledger"])))
        self.assertNotEqual(a["ledger"], b["ledger"])

    def test_low_disk_halts_the_batch_and_writes_nothing(self):
        a, b = self.fx.theorem("A"), self.fx.theorem("B"); n = len(fe.read_ledger(a["ledger"]))
        s = fb.run_batch(self.fx.manifest(a, b, floor=10**9), log=lambda *_: None)
        self.assertEqual({r["state"] for r in s["theorems"]}, {"HALTED_DISK"}); self.assertEqual(len(fe.read_ledger(a["ledger"])), n)

    def test_live_lock_skips_and_stale_lock_is_cleared(self):
        t = self.fx.theorem("A"); lock = os.path.join(t["run_dir"], ".fcve-batch.lock")
        open(lock, "w").write(str(os.getpid()))
        self.assertEqual(fb.run_batch(self.fx.manifest(t), log=lambda *_: None)["theorems"][0]["state"], "LOCKED")
        open(lock, "w").write("999999")
        self.assertEqual(fb.run_batch(self.fx.manifest(t), log=lambda *_: None)["theorems"][0]["state"], "AWAITING_REVIEW:G7")
        self.assertFalse(os.path.exists(lock))

    def test_unconfigured_gates_are_listed_not_silently_skipped(self):
        t = self.fx.theorem("A", full=False); p = fb.plan(t)
        self.assertEqual(sorted(p["not_configured"]), ["G10", "G9"])

class Stale(unittest.TestCase):
    def setUp(self): self.fx = Fx(self)

    def test_changed_upstream_artifact_marks_everything_downstream_stale(self):
        t = self.fx.theorem("A", upto="G4"); m = self.fx.manifest(t)
        fb.run_batch(m, log=lambda *_: None)
        self.assertEqual(fb.stale_report(t["ledger"], t["root"])["stale_events"], [])
        open(os.path.join(t["run_dir"], "claims", "claims.json"), "a").write(" ")            # the claim file changes
        s = fb.stale_report(t["ledger"], t["root"])
        self.assertEqual(list(s["changed_events"]), ["EVENT-002"])
        for node in ("CLAIM-A", "NORMALIZED-A", "FORMAL-A", "BUILD-A", "AXIOMS-A"): self.assertIn(node, s["stale_nodes"])
        p = fb.plan(t)
        self.assertEqual(p["state"], "AWAITING_REVIEW:G1"); self.assertIn("STALE", p["detail"])   # a human gate goes back to a human

    def test_stale_automatic_gate_is_rerun_not_trusted(self):
        t = self.fx.theorem("A"); fb.run_batch(self.fx.manifest(t), log=lambda *_: None)
        with open(os.path.join(t["run_dir"], "lean", "build-incremental-record.json"), "a") as f: f.write(" ")
        p = fb.plan(t); self.assertEqual((p["state"], p["next"]), ("READY", "G5")); self.assertIn("STALE", p["detail"])

    def test_a_replaced_upstream_event_makes_the_earlier_decision_stale_even_though_no_file_changed(self):
        t = self.fx.theorem("A", upto="G4"); L = t["ledger"]; add = t["_add"]
        add("SEMANTIC_RE_AUDIT", "FORMAL-A", "REAUDIT-A", "PASS -- no undisclosed change", ["lean/g4.md"])                 # G7, so the plan can reach G13
        add("EVIDENCE_GRAPH", "EVENT-001..EVENT-006", "GRAPH-A", "PASS", []); add("REPORT_GENERATION", "GRAPH-A", "REPORT-A", "PASS -- v1", [])
        add("GOVERNANCE_DECISION", "GRAPH-A,REPORT-A", "DECISION-A", "PROMOTE -- x", [])
        bare = {**t, "compute": {}, "checkers": None, "lean": None}                                                       # only the human/graph/report gates apply
        self.assertEqual(fb.stale_report(L, t["root"])["stale_events"], [])
        self.assertNotEqual(fb.plan(bare)["state"].split(":")[0], "AWAITING_REVIEW")                                      # decided and fresh: nothing awaits review
        add("REPORT_GENERATION", "GRAPH-A", "REPORT-A", "PASS -- v2", [])                                                 # the report is re-issued AFTER the decision
        s = fb.stale_report(L, t["root"])
        self.assertEqual(list(s["changed_events"]), ["EVENT-009"]); self.assertIn("replaced it", s["changed_events"]["EVENT-009"])   # the decision event
        self.assertIn("DECISION-A", s["stale_nodes"]); self.assertNotIn("REPORT-A", s["stale_nodes"])                    # the new report is fresh
        p = fb.plan(bare); self.assertEqual(p["state"], "AWAITING_REVIEW:G13"); self.assertIn("STALE", p["detail"])       # a human gate goes back to a human

    def test_legacy_events_without_hashes_are_unverifiable_never_assumed_fresh(self):
        led = os.path.join(ROOT, "verification-002", "evidence", "event-ledger.jsonl"); s = fb.stale_report(led, ROOT)
        self.assertEqual(s["changed_events"], {}); self.assertEqual(len(s["unverifiable_events"]), 13)

class Protects(unittest.TestCase):
    def test_existing_hand_written_receipt_is_never_overwritten(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        run = os.path.join(d, "verification-002"); shutil.copytree(os.path.join(ROOT, "verification-002"), run)
        hand = open(os.path.join(run, "receipt", "verification-receipt.md")).read()
        t = {"id": "V2", "run_dir": run, "ledger": os.path.join(run, "evidence", "event-ledger.jsonl"), "root": d}
        self.assertEqual(fb.plan(t)["state"], "COMPLETE")
        with self.assertRaises(fb.BatchError): fb.write_receipt(t)
        self.assertEqual(open(os.path.join(run, "receipt", "verification-receipt.md")).read(), hand)

    def test_plan_is_read_only_on_real_delivered_runs(self):
        for v, root in (("verification", None), ("verification-002", ROOT)):
            led = os.path.join(ROOT, v, "evidence", "event-ledger.jsonl"); before = open(led).read()
            p = fb.plan({"id": v, "run_dir": os.path.join(ROOT, v), "ledger": led, "root": root})
            self.assertEqual(p["state"], "COMPLETE"); self.assertEqual(p["unverifiable_events"].__len__(), p["events"])
            self.assertEqual(open(led).read(), before)

class Manifest(unittest.TestCase):
    def write(self, obj):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True); p = os.path.join(d, "m.json"); json.dump(obj, open(p, "w")); return p
    def test_rejects_duplicates_overlaps_and_missing_files(self):
        for bad, frag in ((dict(theorems=[dict(id="a", run_dir="r"), dict(id="a", run_dir="s")]), "duplicate"),
                          (dict(theorems=[dict(id="a", run_dir="r"), dict(id="b", run_dir="r/inner")]), "overlaps"),
                          (dict(theorems=[dict(id="a", run_dir="r", compute=dict(gate8="/nope.py"))]), "not found"),
                          (dict(theorems=[dict(id="a", run_dir="r", lean=dict(project="/nope"))]), "lean.module"),
                          (dict(theorems=[]), "no theorems")):
            with self.assertRaises(fb.BatchError) as c: fb.load_manifest(self.write(bad))
            self.assertIn(frag, str(c.exception))
    def test_valid_manifest_loads_with_defaults(self):
        m = fb.load_manifest(self.write(dict(theorems=[dict(id="a", run_dir="r")])))
        self.assertEqual(m["min_free_gb"], fb.DEFAULT_MIN_FREE_GB); self.assertTrue(m["theorems"][0]["ledger"].endswith("evidence/event-ledger.jsonl"))

if __name__ == "__main__":
    unittest.main()
