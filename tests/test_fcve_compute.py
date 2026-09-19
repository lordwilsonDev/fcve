import json, os, sys, tempfile, textwrap, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_compute as fc, fcve_evidence as fe

def write(d, name, body):
    p = os.path.join(d, name)
    with open(p, "w") as f:
        f.write(textwrap.dedent(body))
    return p

def emit(outcome, **kw):
    kw.setdefault("tested_domain", "n in [0,10]"); kw.setdefault("cases", 11)
    return f"print('FCVE_RESULT: ' + {json.dumps(json.dumps({'outcome': outcome, **kw}))})\n"

class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = self.t.name; self.o = os.path.join(self.d, "out")
    def tearDown(self): self.t.cleanup()
    def script(self, name, body): return write(self.d, name, body)

class Parse(unittest.TestCase):
    def test_prose_is_not_a_verdict(self):
        with self.assertRaises(fc.ComputeError): fc.parse_result("OVERALL: ALL CHECKS PASS\n")
    def test_vocabulary_enforced(self):
        with self.assertRaises(fc.ComputeError): fc.parse_result('FCVE_RESULT: {"outcome": "COMPUTATIONALLY_SUPPORTED"}')
    def test_bounded_claim_needs_domain_and_cases(self):
        with self.assertRaises(fc.ComputeError): fc.parse_result('FCVE_RESULT: {"outcome": "NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN", "cases": 3}')
        with self.assertRaises(fc.ComputeError): fc.parse_result('FCVE_RESULT: {"outcome": "NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN", "tested_domain": "x", "cases": 0}')
    def test_unknown_category_rejected(self):
        with self.assertRaises(fc.ComputeError):
            fc.parse_result('FCVE_RESULT: {"outcome": "NOT_APPLICABLE", "categories": ["vibes"]}')

class Run(Base):
    def test_no_counterexample_recorded_as_bounded_not_proof(self):
        r = fc.run_check(self.script("ok.py", emit("NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN", categories=["zero", "boundary"])), self.o)
        self.assertEqual((r["outcome"], r["trust"]), ("NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN", "SINGLE_RUN"))
        self.assertEqual(r["evidence_class"], "COUNTEREXAMPLE_ATTEMPT"); self.assertIn("NOT PROOF", r["text"])
        self.assertIn("empty", r["categories_not_covered"]); self.assertEqual(r["categories_covered"], ["boundary", "zero"])
        self.assertEqual(len(r["run"]["script_sha256"]), 64)

    def test_gate10_class_is_computational_test(self):
        r = fc.run_check(self.script("ok.py", emit("NOT_APPLICABLE")), self.o, gate=10)
        self.assertEqual((r["action"], r["evidence_class"]), ("COMPUTATIONAL_CHECK", "COMPUTATIONAL_TEST"))

    def test_prose_only_script_fails_closed(self):
        r = fc.run_check(self.script("legacy.py", "print('OVERALL: ALL CHECKS PASS')\n"), self.o)
        self.assertEqual(r["outcome"], "RUN_FAILED"); self.assertIn("FCVE_RESULT", r["run"]["error"])

    def test_nonzero_exit_fails_even_with_result_line(self):
        r = fc.run_check(self.script("bad.py", emit("NOT_APPLICABLE") + "raise SystemExit(3)\n"), self.o)
        self.assertEqual(r["outcome"], "RUN_FAILED")

    def test_timeout_recorded(self):
        r = fc.run_check(self.script("slow.py", "import time; time.sleep(30)\n"), self.o, timeout=1)
        self.assertEqual(r["outcome"], "RUN_FAILED"); self.assertIn("TIMEOUT", open(os.path.join(self.o, "slow.stderr.log")).read())

    def test_counterexample_unverified_without_recheck(self):
        r = fc.run_check(self.script("cx.py", emit("COUNTEREXAMPLE_FOUND", details={"n": 7})), self.o)
        self.assertEqual((r["outcome"], r["trust"]), ("COUNTEREXAMPLE_FOUND", "UNVERIFIED"))
        self.assertIn("UNVERIFIED", fc.event_fields(r, "out/x.json")["result"])

    def test_counterexample_confirmed_by_agreeing_recheck(self):
        r = fc.run_check(self.script("cx.py", emit("COUNTEREXAMPLE_FOUND")), self.o,
                         recheck_script=self.script("cx2.py", emit("COUNTEREXAMPLE_FOUND")))
        self.assertEqual(r["trust"], "CONFIRMED_BY_RECHECK")

    def test_counterexample_disputed_when_recheck_disagrees(self):  # the VCE-001 float64 case
        r = fc.run_check(self.script("cx.py", emit("COUNTEREXAMPLE_FOUND")), self.o,
                         recheck_script=self.script("hp.py", emit("NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN")))
        self.assertEqual((r["outcome"], r["trust"]), ("DISAGREEMENT", "DISPUTED"))
        self.assertTrue(fc.event_fields(r, "out/x.json")["result"].startswith("DISAGREEMENT"))

    def test_backend_is_not_python_specific(self):
        sh = fc.CommandBackend("sh", ["sh"], ["sh", "-c", "echo sh-ok"])
        s = self.script("t.sh", """echo 'FCVE_RESULT: {"outcome": "NOT_APPLICABLE"}'\n""")
        r = fc.run_check(s, self.o, backend=sh)
        self.assertEqual((r["outcome"], r["backend"]["name"]), ("NOT_APPLICABLE", "sh"))

    def test_missing_backend_raises_not_guesses(self):
        b = fc.CommandBackend("matlab", ["definitely-not-installed-matlab", "-batch"])
        with self.assertRaises(fc.BackendUnavailable): fc.run_check(self.script("t.m", "x"), self.o, backend=b)

class Ledger(Base):
    def kw(self, result, action="ADVERSARIAL_COMPUTATIONAL_TEST"):
        return dict(action=action, reason="r", input="a", output="b", method="m", result=result)
    def test_supported_wording_refused_and_nothing_written(self):
        led = os.path.join(self.d, "l.jsonl")
        fe.append_event(led, action="SOURCE_INTAKE", reason="r", input="a", output="S", method="m", result="ok")
        for bad in ("COMPUTATIONALLY_SUPPORTED -- all fine", "PROVEN by computation", "PASS"):
            with self.assertRaises(fe.ArtifactError): fe.append_event(led, **self.kw(bad))
        self.assertEqual(len(fe.read_ledger(led)), 1)
        fe.append_event(led, **self.kw("NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN -- 11 cases; NOT PROOF"))
        fe.append_event(led, **self.kw("COUNTEREXAMPLE_FOUND (UNVERIFIED)", "CORRECTION_AND_RECHECK"))
        self.assertEqual(len(fe.read_ledger(led)), 3)
    def test_legacy_flag_allows_old_wording(self):
        led = os.path.join(self.d, "l.jsonl")
        fe.append_event(led, action="SOURCE_INTAKE", reason="r", input="a", output="S", method="m", result="ok")
        fe.append_event(led, legacy_result_wording=True, **self.kw("COMPUTATIONALLY_SUPPORTED"))

if __name__ == "__main__":
    unittest.main()
