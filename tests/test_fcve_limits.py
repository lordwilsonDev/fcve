import copy, json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_limits as fl, fcve_report as rp, fcve_receipt as fr

def rec(**kw):
    r = {"claim_id": "CLAIM-001", "reviewer": "Wilson", "none_basis": "",
         "limitations": [{"id": "RL-001", "scope": "TESTS", "statement": "No counterexample was sought against the underlying conjecture.", "basis": "hand receipt"}]}
    r.update(kw); return r

class Validate(unittest.TestCase):
    def test_valid(self): self.assertEqual(fl.validate(rec()), [])
    def test_reviewer_required(self): self.assertTrue(any("reviewer" in p for p in fl.validate(rec(reviewer=" "))))
    def test_each_limitation_needs_scope_statement_basis_and_a_valid_id(self):
        bad = rec(limitations=[{"id": "X1", "scope": "NOPE", "statement": "", "basis": ""}])
        p = " | ".join(fl.validate(bad)); [self.assertIn(w, p) for w in ("id must look like", "scope", "statement is required", "basis is required")]
    def test_duplicate_ids_rejected(self):
        it = rec()["limitations"][0]; self.assertTrue(any("duplicate" in p for p in fl.validate(rec(limitations=[it, dict(it)]))))
    def test_an_essay_is_rejected_a_limitation_is_a_sentence_or_two(self):
        it = dict(rec()["limitations"][0], statement="x" * 501); self.assertTrue(any("keep it under" in p for p in fl.validate(rec(limitations=[it]))))
    def test_saying_there_are_none_is_itself_a_claim_and_needs_a_basis(self):
        self.assertTrue(any("none_basis" in p for p in fl.validate(rec(limitations=[]))))
        self.assertEqual(fl.validate(rec(limitations=[], none_basis="Reviewed the tests and the source; nothing further to add.")), [])
    def test_a_model_authored_record_is_proposed_not_confirmed(self):
        for who in ("assistant (Claude)", "an automated model"): self.assertEqual(fl.info(rec(reviewer=who))[0], "PROPOSED", who)
        self.assertEqual(fl.info(rec())[0], "CONFIRMED"); self.assertEqual(fl.info(None)[0], "NOT SET")
        self.assertIn("not yet confirmed", fl.tag(rec(reviewer="assistant (Claude)"))); self.assertEqual(fl.tag(rec()), "stated by Wilson")
    def test_scaffold_is_invalid_until_filled(self): self.assertTrue(fl.validate(fl.scaffold("CLAIM-001")))

def led(v): return os.path.join(ROOT, v, "evidence", "event-ledger.jsonl")
def loaded(v, r):
    d = rp.load(led(v)); d["reviewer_limits"] = r; return d

class ShortForm(unittest.TestCase):
    def test_short_is_optional_bounded_and_never_a_truncation(self):
        it = dict(rec()["limitations"][0])
        self.assertEqual(fl.validate(rec(limitations=[dict(it, short="One line for the Trust Statement")])), [])
        self.assertTrue(any("short must be" in p for p in fl.validate(rec(limitations=[dict(it, short="x" * 161)]))))
        self.assertTrue(any("short must be" in p for p in fl.validate(rec(limitations=[dict(it, short=" ")]))))

    def test_trust_statement_uses_the_short_form_while_the_table_and_section_11_keep_the_full_statement(self):
        it = dict(rec()["limitations"][0], statement="The long, careful, complete statement of the limitation.", short="A short form")
        d = loaded("verification", rec(limitations=[it])); tex = rp.build_tex(d); ts = tex.split(r"\begin{abstract}")[0]
        self.assertIn("A short form", ts); self.assertNotIn("long, careful, complete", ts)
        self.assertIn("long, careful, complete", tex.split(r"\section{Verification Limitations}")[1]); self.assertIn("long, careful, complete", tex.split(r"\section{Computational")[1])

    def test_without_short_the_full_statement_is_used_whole(self):
        ts = rp.build_tex(loaded("verification", rec())).split(r"\begin{abstract}")[0]
        self.assertIn("No counterexample was sought against the underlying conjecture", ts)

class InTheReport(unittest.TestCase):
    def sect11(self, tex): return tex.split(r"\section{Computational / Adversarial Tests}")[1].split(r"\section{Verification Limitations}")[0]

    def test_section_11_always_says_what_the_tests_do_not_establish_even_without_a_record(self):
        for v in ("verification", "verification-002"):
            s = self.sect11(rp.build_tex(rp.load(led(v)))); self.assertIn("What these tests do not establish", s)
            self.assertIn("not proof of the claim", s); self.assertIn("The tested domain is not recorded", s)         # honest about the legacy gap

    def test_reviewer_test_limits_appear_in_section_11_and_the_table_and_the_trust_statement(self):
        tex = rp.build_tex(loaded("verification", rec())); flat = tex.replace("\\n", " ")
        self.assertIn("No counterexample was sought against the underlying conjecture", self.sect11(tex)); self.assertIn("stated by Wilson", self.sect11(tex))
        self.assertIn("underlying conjecture", tex.split(r"\section{Verification Limitations}")[1].split(r"\section{Verification Matrix}")[0])
        self.assertIn("underlying conjecture", tex.split(r"\begin{abstract}")[0])

    def test_only_TESTS_scope_goes_into_section_11_others_go_to_the_table_only(self):
        r = rec(limitations=[dict(rec()["limitations"][0], scope="SOURCE", statement="The source paper was read in full by one reviewer.")])
        tex = rp.build_tex(loaded("verification", r)); self.assertNotIn("read in full by one reviewer", self.sect11(tex))
        self.assertIn("read in full by one reviewer", tex.split(r"\section{Verification Limitations}")[1])

    def test_reviewer_items_only_ADD_they_never_replace_a_derived_limitation(self):
        base = rp.plain_limitations(loaded("verification", None)["receipt"], loaded("verification", None)["events"], records=loaded("verification", None)["records"])[0]
        d = loaded("verification", rec()); added = rp.plain_limitations(d["receipt"], d["events"], records=d["records"], reviewer=rec())[0]
        self.assertEqual(added[:len(base)], base); self.assertEqual(len(added), len(base) + 1)

    def test_a_proposed_record_is_shown_as_unconfirmed(self):
        tex = rp.build_tex(loaded("verification", rec(reviewer="assistant (Claude)")))
        self.assertIn("proposed by assistant (Claude); not yet confirmed by a human reviewer", tex); self.assertIn("(proposed, not yet confirmed)", tex.split(r"\begin{abstract}")[0])

    def test_an_invalid_record_makes_the_report_refuse(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "l.json"); json.dump(rec(reviewer=""), open(p, "w"))
        with self.assertRaises(rp.ReportError): rp.load(led("verification"), limitations_record=p)

    def test_removing_the_tests_subsection_fails_the_structure_check(self):
        tex = rp.build_tex(rp.load(led("verification-002"))); self.assertEqual(rp.check_structure(tex), [])
        self.assertTrue(any("what the tests do not establish" in p for p in rp.check_structure(tex.replace("What these tests do not establish", "Notes"))))

    def test_a_record_with_compute_data_states_the_tested_domain_instead_of_the_gap(self):
        d = rp.load(led("verification-002")); d["records"]["compute"] = {"tested_domain": "k in [0,5000]", "cases": 5001, "categories_not_covered": ["empty"]}
        s = self.sect11(rp.build_tex(d)); self.assertIn("k in [0,5000]", s); self.assertNotIn("is not recorded for these results", s)

class InTheReceipt(unittest.TestCase):
    def test_receipt_limitations_include_reviewer_statements_added_last(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "l.json"); json.dump(rec(), open(p, "w"))
        base = fr.build_receipt(led("verification"))["limitations"]; withl = fr.build_receipt(led("verification"), limitations_record=p)["limitations"]
        self.assertEqual(withl[:len(base)], base); self.assertEqual(len(withl), len(base) + 1); self.assertIn("stated by Wilson", withl[-1])
    def test_invalid_record_refused_by_the_receipt_too(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "l.json"); json.dump(rec(reviewer=""), open(p, "w"))
        with self.assertRaises(ValueError): fr.build_receipt(led("verification"), limitations_record=p)

if __name__ == "__main__":
    unittest.main()
