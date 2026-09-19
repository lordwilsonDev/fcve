import json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_evidence as fe

LEDGERS = {  # ledger -> (stored legacy graph hash, canonical-order violations expected)
    "verification": ("0c9330331753c8b8346704adba88b70867e4765f26a93c4b0bb22102031af10f",
                     [("REPORT_GENERATION", "GOVERNANCE_DECISION")]),  # known VCE-001 reversal
    "verification-002": ("66705d978fd014309bc8f2cde2af9fd8934a088e0b4650ce9ae2695925c00123", []),
}

def events(v):
    return fe.read_ledger(os.path.join(ROOT, v, "evidence", "event-ledger.jsonl"))

class Regression(unittest.TestCase):
    def test_legacy_hash_reproduced(self):
        for v, (h, _) in LEDGERS.items():
            self.assertEqual(fe.build_graph(events(v), evidence_class=False)["graph_sha256"], h, v)

    def test_chains_intact(self):
        for v in LEDGERS:
            self.assertEqual(fe.verify_chain(events(v)), [], v)

    def test_order_check_flags_only_known_vce001_reversal(self):
        for v, (_, want) in LEDGERS.items():
            self.assertEqual(fe.order_violations([e["action"] for e in events(v)]), want, v)

    def test_v2_shape_is_retired(self):
        with self.assertRaises(ValueError): fe.build_graph(events("verification-002"), evidence_class=True)

class Guards(unittest.TestCase):
    def kw(self, action):
        return dict(action=action, reason="r", input="a", output="b", method="m", result="ok",
                    timestamp="2026-01-01T00:00:00Z")

    def test_strict_refuses_governance_before_report_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            for a in ["SOURCE_INTAKE", "LEAN_BUILD", "EVIDENCE_GRAPH"]:
                fe.append_event(p, **self.kw(a))
            with self.assertRaises(fe.GateOrderError):
                fe.append_event(p, **self.kw("GOVERNANCE_DECISION"))
            self.assertEqual(len(fe.read_ledger(p)), 3)
            fe.append_event(p, **self.kw("REPORT_GENERATION"))
            fe.append_event(p, **self.kw("GOVERNANCE_DECISION"))
            self.assertEqual(fe.verify_chain(fe.read_ledger(p)), [])

    def test_append_matches_legacy_script_hash_scheme(self):
        # rebuild VCE-002 ledger through append_event (non-strict not needed: it is in order)
        src = events("verification-002")
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            for e in src:
                fe.append_event(p, action=e["action"], reason=e["reason"], input=e["input"],
                                output=e["output"], method=e["method"], result=e["result"],
                                evidence=e["evidence"], actor=e["actor"], timestamp=e["timestamp"],
                                root=ROOT, legacy_result_wording=True, hash_artifacts=False)
            self.assertEqual([e["event_hash"] for e in fe.read_ledger(p)],
                             [e["event_hash"] for e in src])

    def test_no_class_promotion(self):
        node = {"id": "COMPTEST-001", "evidence_class": "COMPUTATIONAL_TEST"}
        with self.assertRaises(fe.EvidenceClassError):
            fe.require_class(node, fe.EvidenceClass.FORMAL_PROOF)

class ArtifactGate(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.led = os.path.join(self.d.name, "evidence", "l.jsonl")
        os.makedirs(os.path.dirname(self.led))
        os.makedirs(os.path.join(self.d.name, "claims"))
        self.kw = dict(reason="r", input="SOURCE-1", output="CLAIM-001", method="m", result="ok")
        fe.append_event(self.led, action="SOURCE_INTAKE", **{**self.kw, "output": "SOURCE-1"})

    def tearDown(self):
        self.d.cleanup()

    def write(self, name, doc):
        json.dump(doc, open(os.path.join(self.d.name, "claims", name), "w"))

    def test_invalid_claims_blocks_append(self):
        self.write("claims.json", {"claims": [{"claim_id": "CLAIM-001"}]})
        with self.assertRaises(fe.ArtifactError):
            fe.append_event(self.led, action="CLAIM_EXTRACTION", evidence=["claims/claims.json"], **self.kw)
        self.assertEqual(len(fe.read_ledger(self.led)), 1)

    def test_missing_or_unlisted_artifact_blocks_append(self):
        for ev in ([], ["claims/claims.json"]):
            with self.assertRaises(fe.ArtifactError):
                fe.append_event(self.led, action="CLAIM_EXTRACTION", evidence=ev, **self.kw)
        self.assertEqual(len(fe.read_ledger(self.led)), 1)

    def test_valid_claims_allowed_via_run_dir_path(self):
        cl, asm = fc_scaffold_filled()
        self.write("claims.json", cl)
        fe.append_event(self.led, action="CLAIM_EXTRACTION", evidence=["claims/claims.json"], **self.kw)
        self.assertEqual(len(fe.read_ledger(self.led)), 2)

    def test_no_strict_skips_check(self):
        fe.append_event(self.led, action="CLAIM_EXTRACTION", evidence=[], strict=False, **self.kw)

def fc_scaffold_filled():
    import fcve_claims as fc
    cl, asm = fc.scaffold()
    c = cl["claims"][0]
    c.update(source_location="p.1", statement_verbatim="x")
    return cl, asm

if __name__ == "__main__":
    unittest.main()

