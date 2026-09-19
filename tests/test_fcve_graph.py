import copy, json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_evidence as fe, fcve_graph as fg

def ev(v): return fe.read_ledger(os.path.join(ROOT, v, "evidence", "event-ledger.jsonl"))

class Expand(unittest.TestCase):
    def test_ranges_lists_files(self):
        self.assertEqual(fg.expand_ids("LEMMA-001..005")[0], [f"LEMMA-00{i}" for i in range(1, 6)])
        self.assertEqual(fg.expand_ids("EVENT-001..EVENT-003")[0], ["EVENT-001", "EVENT-002", "EVENT-003"])
        ids, ext = fg.expand_ids("CLAIM-001,assumptions.json,source/original.md,eliahou.pdf (from x @ y)")
        self.assertEqual(ids, ["CLAIM-001"]); self.assertEqual(len(ext), 3)

class Status(unittest.TestCase):
    def test_supported_and_diagnostic_are_never_pass(self):
        for r in ("COMPUTATIONALLY_SUPPORTED -- x", "NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN -- 5 cases", "COUNTEREXAMPLE_FOUND (UNVERIFIED)"):
            self.assertEqual(fg.classify_result(r), "DIAGNOSTIC")
    def test_others(self):
        c = fg.classify_result
        self.assertEqual((c("PASS -- ok"), c("MATCH"), c("INDEPENDENTLY_CHECKED -- n"), c("FAIL -- x"), c("MISMATCH_FOUND (..)")), ("PASS", "PASS", "PASS", "FAIL", "FAIL"))
        self.assertEqual((c("CHECKER_INCOMPATIBLE"), c("CHECKER_UNAVAILABLE"), c("CHECKER_DISAGREEMENT"), c("DISAGREEMENT")), ("NO_VERDICT", "NO_VERDICT", "DISPUTED", "DISPUTED"))
    def test_unknown_is_visible_not_pass(self):
        self.assertEqual(fg.classify_result("looks good to me"), "UNCLASSIFIED")

class RealLedgers(unittest.TestCase):
    def test_both_validate_clean_and_match_delivered_verdicts(self):
        for v, verdict in (("verification", "REPAIR"), ("verification-002", "PROMOTE")):
            e = ev(v); g = fg.build(e)
            self.assertEqual(fg.validate(g, e), [], v)
            self.assertEqual([n["verdict"] for n in g["nodes"] if n["type"] == "DECISION"], [verdict])

    def test_vce002_independent_check_is_in_verification_view_vce001s_is_not(self):
        v2 = [x[0] for x in fg.view_verification(fg.build(ev("verification-002")))]
        v1 = [x[0] for x in fg.view_verification(fg.build(ev("verification")))]
        self.assertIn("INDEPCHECK-002", v2); self.assertNotIn("INDEPCHECK-001", v1)

    def test_diagnostic_computational_never_in_verification_view(self):
        for v in ("verification", "verification-002"):
            names = [x[0] for x in fg.view_verification(fg.build(ev(v)))]
            self.assertFalse({"TEST-001", "TEST-001-CORRECTED", "COMPTEST-001", "TEST-002"} & set(names))

    def test_failure_view_keeps_false_mismatch_and_its_repair(self):
        f = fg.view_failure(fg.build(ev("verification")))
        self.assertIn("TEST-001", [n[0] for n in f["nodes"]])
        self.assertIn(("TEST-001-CORRECTED", "REPAIRS", "TEST-001"), f["edges"])
        self.assertIn(("TEST-001", "CONTRADICTS", "FORMAL-001"), f["edges"])

    def test_edge_direction_convention(self):
        g = fg.build(ev("verification-002")); E = {(e["from"], e["edge_type"], e["to"]) for e in g["edges"]}
        self.assertIn(("CLAIM-002", "DERIVED_FROM", "SOURCE-002"), E)
        self.assertIn(("AXIOMS-002", "JUSTIFIES", "BUILD-002"), E)
        self.assertIn(("FORMAL-002", "PRODUCES", "BUILD-002"), E)

    def test_event_range_resolves_to_nodes_not_dangling(self):
        g = fg.build(ev("verification-002"))
        self.assertFalse([e for e in g["edges"] if e["from"].startswith("EVENT-") or e["to"].startswith("EVENT-")])

    def test_dependency_view_pairs(self):
        d = fg.view_dependency(fg.build(ev("verification-002")))
        self.assertIn(("CLAIM-002", "SOURCE-002"), d)

    def test_six_views_one_graph(self):
        g = fg.build(ev("verification-002"))
        self.assertEqual(set(fg.VIEWS), {"chronological", "evidence", "dependency", "reasoning", "failure", "verification"})
        for f in fg.VIEWS.values(): f(g)
        self.assertTrue(all(n["reason"] for n in g["nodes"]))

    def test_legacy_v1_still_reproduces_delivered_hashes(self):
        self.assertEqual(fe.build_graph(ev("verification"))["graph_sha256"], "0c9330331753c8b8346704adba88b70867e4765f26a93c4b0bb22102031af10f")

    def test_legacy_events_report_missing_25_hashes_not_invented(self):
        r = fg.event_integrity(ev("verification-002")); self.assertEqual(len(r["no_input_hash"]), 13); self.assertEqual(r["missing_fields"], [])

class Superseded(unittest.TestCase):
    """A later event re-producing an output replaces the earlier one in the GRAPH; the ledger keeps both (§46)."""
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup); self.d = self.t.name
        os.makedirs(f"{self.d}/evidence"); self.L = f"{self.d}/evidence/l.jsonl"
    def add(self, action, i, o, res="PASS", **kw): return fe.append_event(self.L, action=action, reason="r", input=i, output=o, method="m", result=res, strict=False, hash_artifacts=False, **kw)

    def test_mistyped_input_is_a_dangling_edge_until_a_superseding_event_replaces_it(self):
        self.add("SOURCE_INTAKE", "source/a.md", "SOURCE-1"); self.add("EVIDENCE_GRAPH", "EVENT-001", "GRAPH-1"); self.add("REPORT_GENERATION", "GRAPH-1", "REPORT-1")
        self.add("GOVERNANCE_DECISION", "GRAPH,REPORT", "DECISION-1", "PROMOTE -- x")                 # typo: ids do not exist
        e = fe.read_ledger(self.L); self.assertTrue(any("dangling" in p for p in fg.validate(fg.build(e), e)))
        self.add("GOVERNANCE_DECISION", "GRAPH-1,REPORT-1", "DECISION-1", "PROMOTE -- x")            # supersedes it
        e = fe.read_ledger(self.L); g = fg.build(e)
        self.assertEqual(fg.validate(g, e), []); self.assertEqual(g["superseded_events"], [{"event": "EVENT-004", "superseded_by": ["EVENT-005"]}])
        self.assertEqual(len(e), 5)                                                                     # the ledger still has both
        self.assertEqual([n["produced_by_event"] for n in g["nodes"] if n["id"] == "DECISION-1"], ["EVENT-005"])

    def test_event_refs_to_a_superseded_event_still_resolve(self):
        self.add("SOURCE_INTAKE", "source/a.md", "SOURCE-1"); self.add("REPORT_GENERATION", "SOURCE-1", "REPORT-1"); self.add("REPORT_GENERATION", "SOURCE-1", "REPORT-1")
        self.add("EVIDENCE_GRAPH", "EVENT-001..EVENT-003", "GRAPH-1")
        e = fe.read_ledger(self.L); self.assertEqual(fg.validate(fg.build(e), e), [])

    def test_no_supersession_no_extra_key_so_existing_hashes_are_unchanged(self):
        self.assertNotIn("superseded_events", fg.build(ev("verification-002"))); self.assertNotIn("superseded_events", fg.build(ev("verification")))

class InputCheck(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup); os.makedirs(f"{self.t.name}/evidence"); self.L = f"{self.t.name}/evidence/l.jsonl"
        fe.append_event(self.L, action="SOURCE_INTAKE", reason="r", input="source/a.md", output="SOURCE-1", method="m", result="PASS", hash_artifacts=False)
    def add(self, i, **kw): return fe.append_event(self.L, action="LEAN_BUILD", reason="r", input=i, output="BUILD-1", method="m", result="PASS", hash_artifacts=False, **kw)

    def test_mistyped_input_refused_and_nothing_written(self):
        with self.assertRaises(fe.ArtifactError) as c: self.add("SOURCE", check_inputs=True)
        self.assertIn("SOURCE", str(c.exception)); self.assertEqual(len(fe.read_ledger(self.L)), 1)
    def test_valid_inputs_pass_including_files_and_event_ranges(self):
        self.add("SOURCE-1,notes/x.md,EVENT-001", check_inputs=True); self.assertEqual(len(fe.read_ledger(self.L)), 2)
    def test_off_by_default_so_free_form_ids_keep_working(self):
        self.add("anything-goes"); self.assertEqual(len(fe.read_ledger(self.L)), 2)
    def test_both_delivered_ledgers_replay_cleanly_under_the_check(self):
        for v in ("verification", "verification-002"):
            e = ev(v)
            for i, x in enumerate(e): self.assertEqual(fg.unresolved_inputs(e[:i], x["input"]), [] if i else fg.unresolved_inputs(e[:0], x["input"]), (v, x["event_id"]))

class Legacy(unittest.TestCase):
    def test_stored_delivered_graphs_are_current_and_unforged(self):
        for v in ("verification", "verification-002"):
            g = json.load(open(os.path.join(ROOT, v, "evidence", "evidence-graph.json")))
            self.assertEqual(fg.validate_legacy(g, ev(v)), [], v)

    def test_legacy_stale_detected(self):
        g = json.load(open(os.path.join(ROOT, "verification-002", "evidence", "evidence-graph.json")))
        self.assertTrue(any("STALE" in p for p in fg.validate_legacy(g, ev("verification-002")[:-1] + [dict(ev("verification-002")[-1], event_hash="x")])))

    def test_v3_validator_refuses_legacy_shape_cleanly(self):
        g = json.load(open(os.path.join(ROOT, "verification-002", "evidence", "evidence-graph.json")))
        self.assertEqual(len(fg.validate(g, ev("verification-002"))), 1)

class Integrity(unittest.TestCase):
    def test_stale_graph_detected(self):
        e = ev("verification-002"); g = fg.build(e[:8])                    # built before events 9-13 (evidence + graph + report + decision)
        self.assertTrue(any("STALE" in p for p in fg.validate(g, e)))
    def test_report_and_decision_after_the_graph_do_not_make_it_stale(self):
        e = ev("verification-002"); g = fg.build(e[:10])                  # EVENT-011 graph, 012 report, 013 decision follow
        self.assertEqual(fg.validate(g, e), [])
    def test_new_evidence_after_the_graph_does_make_it_stale(self):
        e = copy.deepcopy(ev("verification-002")); g = fg.build(e[:9])    # events 10 (independent check) came after
        p = fg.validate(g, e); self.assertTrue(any("STALE" in x and "INDEPENDENT_CHECK" in x for x in p))
    def test_tampered_graph_detected(self):
        e = ev("verification-002"); g = fg.build(e); g["nodes"][0]["result"] = "PASS -- forged"
        self.assertTrue(any("graph_sha256" in p for p in fg.validate(g, e)))
    def test_tampered_ledger_detected(self):
        e = copy.deepcopy(ev("verification-002")); e[3]["result"] = "PASS -- forged"; g = fg.build(e)
        self.assertTrue(any("ledger:" in p for p in fg.validate(g, e)))
    def test_dangling_and_bad_type_detected(self):
        e = ev("verification-002"); g = fg.build(e); g["edges"].append({"from": "NOPE", "to": "SOURCE-002", "edge_type": "MADE_UP", "via_event": "EVENT-001"})
        p = fg.validate(g, e); self.assertTrue(any("dangling" in x for x in p) and any("MADE_UP" in x for x in p))

class EventHashes(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = self.t.name; os.makedirs(f"{self.d}/evidence"); os.makedirs(f"{self.d}/claims")
        self.led = f"{self.d}/evidence/l.jsonl"
    def tearDown(self): self.t.cleanup()
    def add(self, **kw):
        base = dict(reason="r", method="m", result="PASS -- ok"); base.update(kw)
        return fe.append_event(self.led, **base)

    def test_new_events_carry_hashes_that_track_file_content(self):
        with open(f"{self.d}/claims/a.txt", "w") as f: f.write("v1")
        e1 = self.add(action="SOURCE_INTAKE", input="s", output="SOURCE-1", evidence=["claims/a.txt"])
        with open(f"{self.d}/claims/a.txt", "w") as f: f.write("v2")
        e2 = self.add(action="LEAN_BUILD", input="SOURCE-1", output="BUILD-1", evidence=["claims/a.txt"])
        self.assertNotEqual(e1["output_hash"], e2["output_hash"])
        self.assertTrue(e1["input_hash"] and e2["input_hash"] and e1["input_hash"] != e2["input_hash"])

    def test_missing_evidence_file_is_null_not_skipped(self):
        e = self.add(action="SOURCE_INTAKE", input="s", output="S", evidence=["nope.txt"])
        e_ok = self.add(action="LEAN_BUILD", input="S", output="B", evidence=[])
        self.assertNotEqual(e["output_hash"], e_ok["output_hash"])  # a listed-but-missing file is recorded, not ignored

    def test_input_hash_changes_when_upstream_evidence_changes(self):
        with open(f"{self.d}/claims/a.txt", "w") as f: f.write("A")
        self.add(action="SOURCE_INTAKE", input="s", output="S", evidence=["claims/a.txt"])
        x = self.add(action="LEAN_BUILD", input="S", output="B", evidence=[])
        led2 = f"{self.d}/evidence/l2.jsonl"
        with open(f"{self.d}/claims/a.txt", "w") as f: f.write("B")
        fe.append_event(led2, action="SOURCE_INTAKE", reason="r", method="m", result="PASS", input="s", output="S", evidence=["claims/a.txt"])
        y = fe.append_event(led2, action="LEAN_BUILD", reason="r", method="m", result="PASS", input="S", output="B", evidence=[])
        self.assertNotEqual(x["input_hash"], y["input_hash"])

    def test_graph_of_new_ledger_validates_and_carries_hashes(self):
        self.add(action="SOURCE_INTAKE", input="source/original.md", output="SOURCE-1", evidence=[])
        e = fe.read_ledger(self.led); g = fg.build(e)
        self.assertEqual(fg.validate(g, e), []); self.assertTrue(g["nodes"][0]["output_hash"])
        self.assertEqual(fg.event_integrity(e)["no_input_hash"], [])

if __name__ == "__main__":
    unittest.main()
