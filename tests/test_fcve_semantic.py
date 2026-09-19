import copy, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_semantic as fs

H = os.path.expanduser("~/ico-collatz")
P2 = f"{H}/ico_collatz_verification/IcoCollatzVerification/PowersOfTwoReachOne.lean"
RES = f"{H}/targets/eliahou-collatz-bounds/Results.lean"

def filled(gate, status):
    r = fs.scaffold(gate, "CLAIM-001")
    for c in r["checks"].values():
        c.update(finding="NONE", detail="compared normalized text to Lean statement")
    r["status"] = status
    if gate == "GATE7":
        r.update(bridge_verdict="FAITHFUL", bridge_justification="statement and Lean match term for term", reviewer="R. Reviewer")
    return r

class Rules(unittest.TestCase):
    def test_scaffold_invalid_until_filled(self):
        self.assertTrue(fs.validate(fs.scaffold("GATE4", "C")))

    def test_clean_records_valid(self):
        self.assertEqual(fs.validate(filled("GATE4", "MATCH")), [])
        self.assertEqual(fs.validate(filled("GATE7", "CLEAN")), [])

    def test_skipped_check_rejected(self):
        r = filled("GATE7", "CLEAN"); del r["checks"]["injectivity_assumptions"]
        self.assertTrue(any("injectivity_assumptions" in p for p in fs.validate(r)))

    def test_bare_tick_rejected(self):
        r = filled("GATE4", "MATCH"); r["checks"]["altered_domain"]["detail"] = ""
        self.assertTrue(fs.validate(r))

    def test_match_over_a_finding_rejected(self):
        r = filled("GATE4", "MATCH"); r["checks"]["changed_coercion"] = {"finding": "FOUND", "detail": "N->R", "disclosed": True}
        self.assertTrue(any("contradicts" in p for p in fs.validate(r)))

    def test_gate7_undisclosed_forces_repair(self):
        r = filled("GATE7", "CLEAN"); r["checks"]["injectivity_assumptions"] = {"finding": "FOUND", "detail": "hinj", "disclosed": False}
        r["bridge_verdict"] = "PARTIAL"                                  # a found difference can no longer be plain FAITHFUL
        self.assertTrue(fs.validate(r))                                  # status CLEAN over an undisclosed change
        r["status"] = "REPAIR"; self.assertEqual(fs.validate(r), []); self.assertEqual(fs.gate_outcome(r), "REPAIR")

    def test_gate7_disclosed_finding_passes(self):
        r = filled("GATE7", "DISCLOSED"); r["checks"]["injectivity_assumptions"] = {"finding": "FOUND", "detail": "hinj", "disclosed": True}
        r["bridge_verdict"] = fs.WITH_DIFF; r["difference_disclosure"] = {k: "stated" for k in fs.DISCLOSURE_KEYS}
        self.assertEqual(fs.validate(r), []); self.assertEqual(fs.gate_outcome(r), "PASS")

    def test_only_match_passes_gate4(self):
        r = filled("GATE4", "MATCH"); self.assertEqual(fs.gate_outcome(r), "PASS")
        r["status"] = "WEAKER"; r["checks"]["weaker_statement"] = {"finding": "FOUND", "detail": "d", "disclosed": True}
        self.assertEqual(fs.validate(r), []); self.assertEqual(fs.gate_outcome(r), "FAIL")

    def test_unaddressed_signal_rejected(self):
        r = filled("GATE7", "CLEAN")
        self.assertTrue(any("injectivity" in p for p in fs.validate(r, {"injectivity": ["Function.Injective"]})))
        r["signal_dispositions"] = {"injectivity": {"disposition": "DISCLOSED", "note": "hinj is a hypothesis of the theorem"}}
        self.assertEqual(fs.validate(r, {"injectivity": ["Function.Injective"]}), [])

    def test_normalization_outcomes(self):
        self.assertEqual([fs.normalization_outcome(s) for s in ("MATCH", "PARTIAL", "MISMATCH", "UNCLEAR")],
                         ["CONTINUE", "CONTINUE", "STOP", "REPAIR"])
        with self.assertRaises(fs.SemanticError): fs.normalization_outcome("MAYBE")

    def test_extract_statement_errors(self):
        with self.assertRaises(fs.SemanticError): fs.extract_statement("theorem a : True := trivial", "b")

@unittest.skipUnless(os.path.exists(P2) and os.path.exists(RES), "needs ~/ico-collatz sources")
class RealSources(unittest.TestCase):
    def sig(self, path, name): return fs.lean_signals(fs.extract_statement(open(path).read(), name))

    def test_vce002_statement_has_no_signals(self):
        self.assertEqual(self.sig(P2, "powers_of_two_reach_one"), {})

    def test_vce001_signals_match_what_manual_audit_hunted(self):
        s = self.sig(RES, "results_eliahou_theorem_1_1")
        self.assertIn("injectivity", s); self.assertIn("finite_structure", s)
        s = self.sig(RES, "results_rational_linear_form")
        self.assertIn("cast_or_coercion", s); self.assertIn("approximation", s)

class BridgeVerdict(unittest.TestCase):
    def rec(self, verdict, findings=(), **kw):
        r = filled("GATE7", "DISCLOSED" if findings else "CLEAN"); r["bridge_verdict"] = verdict
        for k in findings: r["checks"][k] = {"finding": "FOUND", "detail": "d", "disclosed": True}
        r.update(kw); return r

    def test_required_on_gate7_optional_on_gate4(self):
        r = filled("GATE7", "CLEAN"); del r["bridge_verdict"]
        self.assertTrue(any("bridge_verdict is required" in p for p in fs.validate(r)))
        self.assertEqual(fs.validate(filled("GATE4", "MATCH")), [])

    def test_only_the_four_section_30_verdicts(self):
        self.assertEqual(fs.BRIDGE_VERDICTS, ["FAITHFUL", "FAITHFUL WITH EXPLICIT REPRESENTATIONAL DIFFERENCE", "PARTIAL", "MISMATCH"])
        self.assertTrue(any("not one of" in p for p in fs.validate(self.rec("LOOKS GOOD"))))

    def test_justification_and_reviewer_required(self):
        p = fs.validate(self.rec("FAITHFUL", bridge_justification="", reviewer=""))
        self.assertTrue(any("bridge_justification" in x for x in p) and any("reviewer" in x for x in p))

    def test_faithful_cannot_coexist_with_a_found_difference(self):
        self.assertTrue(any("contradicts" in p for p in fs.validate(self.rec("FAITHFUL", ["injectivity_assumptions"]))))

    def test_with_difference_needs_a_finding_disclosure_and_all_six_parts(self):
        self.assertTrue(any("at least one FOUND" in p for p in fs.validate(self.rec(fs.WITH_DIFF))))
        r = self.rec(fs.WITH_DIFF, ["injectivity_assumptions"])
        self.assertEqual(sum("difference_disclosure." in p for p in fs.validate(r)), 6)
        r["difference_disclosure"] = {k: "x" for k in fs.DISCLOSURE_KEYS}; self.assertEqual(fs.validate(r), [])
        r["difference_disclosure"]["assumptions"] = " "; self.assertEqual(sum("difference_disclosure." in p for p in fs.validate(r)), 1)

    def test_an_undisclosed_difference_cannot_be_called_explicit(self):
        r = self.rec(fs.WITH_DIFF, ["injectivity_assumptions"], difference_disclosure={k: "x" for k in fs.DISCLOSURE_KEYS})
        r["checks"]["injectivity_assumptions"]["disclosed"] = False; r["status"] = "REPAIR"
        self.assertTrue(any("undisclosed" in p for p in fs.validate(r)))

    def test_mismatch_needs_a_finding(self):
        self.assertTrue(any("MISMATCH needs" in p for p in fs.validate(self.rec("MISMATCH"))))
        self.assertEqual(fs.validate(self.rec("MISMATCH", ["changed_domains"], status="DISCLOSED")), [])

    def test_a_model_cannot_certify_its_own_proposal(self):
        for who in ("assistant", "Claude", "an automated model", "GPT"):
            self.assertEqual(fs.bridge_info(self.rec("FAITHFUL", reviewer=who))[1], "PROPOSED", who)
        self.assertEqual(fs.bridge_info(self.rec("FAITHFUL", reviewer="Wilson Lord"))[1], "CONFIRMED")
        self.assertEqual(fs.bridge_info({})[1], "NOT SET")

    def test_scaffold_has_the_new_fields_and_is_invalid_until_filled(self):
        sc = fs.scaffold("GATE7", "C"); self.assertEqual(set(sc["difference_disclosure"]), set(fs.DISCLOSURE_KEYS)); self.assertTrue(fs.validate(sc))
        self.assertNotIn("bridge_verdict", fs.scaffold("GATE4", "C"))

if __name__ == "__main__":
    unittest.main()
