import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_claims as fc

def load(v, n):
    return json.load(open(os.path.join(ROOT, v, "claims", n)))

class Existing(unittest.TestCase):
    def test_vce002_strictly_valid(self):
        self.assertEqual(fc.validate_claims(load("verification-002", "claims.json")), [])
        self.assertEqual(fc.validate_assumptions(load("verification-002", "assumptions.json")), [])

    def test_vce001_strict_flags_exactly_lemma_definitions(self):
        p = fc.validate_claims(load("verification", "claims.json"))
        self.assertEqual(sorted(p), [f"LEMMA-00{i}: missing surrounding_definitions" for i in range(1, 6)])

    def test_vce001_valid_with_legacy_flag(self):
        self.assertEqual(fc.validate_claims(load("verification", "claims.json"),
                                            lenient=("surrounding_definitions",)), [])
        self.assertEqual(fc.validate_assumptions(load("verification", "assumptions.json")), [])

class Rules(unittest.TestCase):
    def claim(self, **kw):
        c = {"claim_id": "CLAIM-001", "claim_type": "FORMAL", "source_location": "s", "statement_verbatim": "x",
             "explicit_conditions": [], "surrounding_definitions": [], "referenced_lemmas": []}
        c.update(kw); return c

    def test_mixed_needs_decomposition(self):
        self.assertTrue(fc.validate_claims({"claims": [self.claim(claim_type="MIXED")]}))
        ok = {"claims": [self.claim(claim_type="MIXED", decomposed_into=["CLAIM-002", "CLAIM-003"]),
                         self.claim(claim_id="CLAIM-002"), self.claim(claim_id="CLAIM-003", claim_type="EMPIRICAL")]}
        self.assertEqual(fc.validate_claims(ok), [])

    def test_dangling_lemma_and_duplicate_id(self):
        p = fc.validate_claims({"claims": [self.claim(referenced_lemmas=["LEMMA-009"]), self.claim()]})
        self.assertTrue(any("LEMMA-009" in x for x in p) and any("duplicate" in x for x in p))

    def test_omitted_assumption_category_is_a_defect(self):
        p = fc.validate_assumptions({"source_assumptions": []})
        self.assertEqual(len(p), 2)

    def test_scaffold_is_not_valid_until_filled(self):
        cl, asm = fc.scaffold()
        self.assertTrue(fc.validate_claims(cl)); self.assertTrue(fc.validate_assumptions(asm))

if __name__ == "__main__":
    unittest.main()
