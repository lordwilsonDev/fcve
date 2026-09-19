import copy, json, os, re, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_evidence as fe, fcve_receipt as fr

def led(v): return os.path.join(ROOT, v, "evidence", "event-ledger.jsonl")
def hand(v): return open(os.path.join(ROOT, v, "receipt", "verification-receipt.md")).read()
R1 = fr.build_receipt(led("verification")); R2 = fr.build_receipt(led("verification-002"))

# The delivered VCE-001 run hashes verification/source/original.pdf (Eliahou's paper). That third-party PDF is deliberately NOT in the repository
# (.gitignore, copyright), so on a fresh clone these tests cannot run: they SKIP with this reason, visibly, instead of failing or (worse) passing.
_PDF = os.path.join(ROOT, "verification", "source", "original.pdf")
needs_source_pdf = unittest.skipUnless(os.path.exists(_PDF), "third-party source PDF verification/source/original.pdf is not in the repository (gitignored, copyright); place it there to run this test")

class AgainstHandWrittenReceipts(unittest.TestCase):
    @needs_source_pdf
    def test_source_hashes_match_the_hand_receipts(self):
        for v, R in (("verification", R1), ("verification-002", R2)):
            h = re.search(r"sha256:([0-9a-f]{64})", R["fields"]["SOURCE HASH"]).group(1)
            self.assertIn(h, hand(v), v)

    def test_decisions_match(self):
        self.assertEqual((R1["decision"], R2["decision"]), ("REPAIR", "PROMOTE"))

    @needs_source_pdf
    def test_repro_levels_match_hand_receipts(self):
        self.assertEqual((R1["repro_level"], R2["repro_level"]), (3, 4))

    def test_axiom_footprints_match_and_negated_mention_is_not_a_dependency(self):
        self.assertEqual(R2["fields"]["AXIOM FOOTPRINT"], "propext, Quot.sound")   # bug: once read as incl. Classical.choice
        self.assertEqual(R1["fields"]["AXIOM FOOTPRINT"], "propext, Classical.choice, Quot.sound")

    def test_independent_check_status(self):
        self.assertTrue(R2["fields"]["INDEPENDENT CHECK"].startswith("PASS -- Checked 1662"))
        self.assertIn("legacy wording", R2["fields"]["INDEPENDENT CHECK"])
        self.assertTrue(R1["fields"]["INDEPENDENT CHECK"].startswith("CHECKER_INCOMPATIBLE"))

    def test_versions(self):
        self.assertEqual((R1["fields"]["LEAN VERSION"], R2["fields"]["LEAN VERSION"]), ("4.28.0", "4.34.0"))

    def test_every_field_states_its_source(self):
        for R in (R1, R2):
            for k in R["fields"]: self.assertIn(k, R["sources"])

    def test_unrecorded_costs_are_not_invented(self):
        self.assertIn("NOT RECORDED", R2["fields"]["COST"]); self.assertNotIn("no paid API", R2["fields"]["COST"])

class DecisionCheck(unittest.TestCase):
    def test_vce001_repair_is_supported_and_blockers_are_disclosed(self):
        self.assertEqual(R1["decision_problems"], []); self.assertEqual(R1["blockers"], ["G9", "ORDER"])
        self.assertTrue(any("G9" in l for l in R1["limitations"])); self.assertTrue(any("ORDER" in l for l in R1["limitations"]))

    def test_vce002_promote_flagged_for_missing_gate10_as_per_literal_53(self):
        self.assertEqual(R2["blockers"], ["G10"]); self.assertTrue(any("G10" in p for p in R2["decision_problems"]))
        self.assertIn("DECISION CHECK FAILED", fr.render(R2)); self.assertIn("NOT SUPPORTED", R2["fields"]["FINAL DECISION"])

    def test_explicit_waiver_is_shown_not_silent(self):
        R = fr.build_receipt(led("verification-002"), waivers={"G10": "Gate 8 script also served as the computational check"})
        self.assertEqual(R["decision_problems"], []); md = fr.render(R)
        self.assertIn("WAIVED: Gate 8 script also served", md)
        status = md.split("## Status")[1].split("## §53")[0]
        self.assertIn("COMPUTATIONAL TEST:", status); self.assertIn("MISSING -- WAIVED (Gate 8 script", status)

    def test_mandatory_gates_cannot_be_waived(self):
        for g in ("G0", "G5", "G6", "G7", "G9"):
            with self.assertRaises(ValueError): fr.gate_table(fe.read_ledger(led("verification-002")), {g: "x"})

class Rules(unittest.TestCase):
    def ev(self, action, result, method="m"):
        return {"event_id": "E", "action": action, "result": result, "method": method, "evidence": [], "input": "a", "output": "b", "event_hash": "h"}

    def test_normalization_mismatch_forces_stop_unclear_forces_repair(self):
        rows, bl = fr.gate_table([self.ev("SEMANTIC_NORMALIZATION", "MISMATCH")])
        self.assertTrue(any("STOP" in p for p in fr.check_decision([self.ev("SEMANTIC_NORMALIZATION", "MISMATCH"), self.ev("GOVERNANCE_DECISION", "REPAIR -- x")], rows, bl)[0]))
        self.assertTrue(any("REPAIR" in p for p in fr.check_decision([self.ev("SEMANTIC_NORMALIZATION", "UNCLEAR"), self.ev("GOVERNANCE_DECISION", "PROMOTE")], rows, bl)[0]))

    def test_non_verdict_rejected(self):
        self.assertTrue(fr.check_decision([self.ev("GOVERNANCE_DECISION", "VERIFIED!")], [], [])[0])

    def test_na_independent_check_needs_a_reason(self):
        no = fr.gate_table([self.ev("INDEPENDENT_CHECK", "NOT_APPLICABLE")])[0]
        yes = fr.gate_table([self.ev("INDEPENDENT_CHECK", "NOT_APPLICABLE -- empirical claim, no Lean artifact")])[0]
        g9 = lambda rows: next(r for r in rows if r["gate"] == "G9")
        self.assertFalse(g9(no)["satisfied"]); self.assertTrue(g9(yes)["satisfied"])

    def test_unresolved_counterexample_blocks(self):
        g8 = next(r for r in fr.gate_table([self.ev("ADVERSARIAL_COMPUTATIONAL_TEST", "COUNTEREXAMPLE_FOUND (UNVERIFIED)")])[0] if r["gate"] == "G8")
        self.assertFalse(g8["satisfied"])

class NoTruncation(unittest.TestCase):
    def test_fields_carry_the_full_recorded_result(self):
        ev = fe.read_ledger(led("verification")); full = next(e["result"] for e in ev if e["action"] == "INDEPENDENT_CHECK")
        self.assertGreater(len(full), 130); self.assertIn(full, R1["fields"]["INDEPENDENT CHECK"])
        self.assertEqual(next(g for g in R1["gates"] if g["gate"] == "G9")["result"], full)

    def test_trust_statement_uses_outcomes_not_cut_prose(self):
        self.assertNotRegex(R1["trust"], r"p16\),\s*;"); self.assertIn("CHECKER_INCOMPATIBLE for results_eliahou_theorem_1_1 specifically", R1["trust"])
        self.assertIn("INDEPENDENTLY_CHECKED (recorded before", R2["trust"]); self.assertNotRegex(R2["trust"], r"\.;|\.\.")

class PlainIndependentStatus(unittest.TestCase):
    def test_glosses_each_section_17_token_and_keeps_the_recorded_lead(self):
        f = fr.plain_independent_status
        self.assertIn("could not process this proof's export", f("CHECKER_INCOMPATIBLE for x specifically -- stalls"))
        self.assertTrue(f("CHECKER_INCOMPATIBLE for x specifically -- stalls").startswith("CHECKER_INCOMPATIBLE for x specifically ("))
        self.assertIn("no external checker was available", f("CHECKER_UNAVAILABLE -- no binary"))
        self.assertIn("disagreed with the Lean kernel", f("CHECKER_DISAGREEMENT -- x")); self.assertIn("not applicable", f("NOT_APPLICABLE -- empirical"))
        self.assertEqual(f("INDEPENDENTLY_CHECKED -- 1662 declarations"), "INDEPENDENTLY_CHECKED")
        self.assertIn("recorded before the Section 17 vocabulary existed", f("PASS -- Checked 1662  (legacy wording)"))
    def test_receipt_trust_statement_carries_the_gloss(self):
        self.assertIn("could not process this proof's export", R1["trust"]); self.assertNotIn("could not process", R2["trust"])

class PermittedStatusFn(unittest.TestCase):
    def test_promote_supported_only_without_blockers(self):
        self.assertFalse(fr.permitted_status(R2)["promote_supported"]); self.assertTrue(any("G10" in b for b in fr.permitted_status(R2)["blockers"]))
        W = fr.build_receipt(led("verification-002"), waivers={"G10": "reason"}); ps = fr.permitted_status(W)
        self.assertTrue(ps["promote_supported"]); self.assertEqual(ps["waived"], ["G10: reason"])

class PermittedIgnoresTheReportItself(unittest.TestCase):
    def test_g12_missing_only_because_the_report_is_being_built_is_not_a_blocker(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(f"{d}/evidence"); p = f"{d}/evidence/l.jsonl"
            for e in fe.read_ledger(led("verification-002"))[:11]:                       # through the graph, before the report
                open(p, "a").write(json.dumps(e, sort_keys=True) + "\n")
            R = fr.build_receipt(p, root=ROOT, waivers={"G10": "reason"}, allow_pending=True)
            self.assertIn("G12", R["blockers"])                                            # the receipt's own table still shows it
            ps = fr.permitted_status(R, ignore={"G12"}); self.assertTrue(ps["promote_supported"]); self.assertEqual(ps["blockers"], [])
            self.assertFalse(fr.permitted_status(R)["promote_supported"])

class Staleness(unittest.TestCase):
    def test_current_receipt_checks_clean_and_later_events_make_it_stale(self):
        self.assertEqual(fr.check_receipt(R2, led("verification-002")), [])
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(f"{d}/evidence"); p = f"{d}/evidence/l.jsonl"
            for e in fe.read_ledger(led("verification-002")): open(p, "a").write(json.dumps(e, sort_keys=True) + "\n")
            fe.append_event(p, action="REPORT_GENERATION", reason="r", method="m", result="PASS", input="x.md", output="R2", strict=False)
            self.assertTrue(any("STALE" in x for x in fr.check_receipt(R2, p)))

    def test_forged_history_detected(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(f"{d}/evidence"); p = f"{d}/evidence/l.jsonl"
            for e in fe.read_ledger(led("verification-002")):
                if e["event_id"] == "EVENT-004": e = dict(e, result="MATCH -- forged")
                open(p, "a").write(json.dumps(e, sort_keys=True) + "\n")
            self.assertTrue(fr.check_receipt(R2, p))

class Render(unittest.TestCase):
    def test_all_18_spec_fields_present(self):
        md = fr.render(R1)
        for f in ("THEOREM ID", "SOURCE HASH", "CLAIM", "NORMALIZED CLAIM", "LEAN STATEMENT", "LEAN VERSION", "MATHLIB VERSION", "BUILD RESULT",
                  "AXIOM FOOTPRINT", "INDEPENDENT CHECK", "COMPUTATIONAL TEST", "COUNTEREXAMPLE SEARCH", "SEMANTIC MATCH",
                  "REPRODUCIBILITY LEVEL", "GRAPH HASH", "COST", "FINAL DECISION", "LIMITATIONS"):
            self.assertIn(f"| {f} |", md)
        self.assertIn("**Trust Statement.**", md); self.assertNotIn("Fully verified", md)

if __name__ == "__main__":
    unittest.main()
