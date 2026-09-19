import os, shutil, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "tests"))
import fcve_axioms as fa, fcve_lean as fl
from test_fcve_lean import make_project, HAVE

BODY = """axiom myAx : 1 = 2
theorem t0 : 1 + 1 = 2 := rfl
theorem t1 (p : Prop) : p \\/ \\u00acp := Classical.em p
theorem t2 : True = (1 = 1) := propext \\u27e8fun _ => rfl, fun _ => trivial\\u27e9
theorem t3 : 1 = 2 := myAx
theorem t4 : 1 = 2 := by sorry
theorem t5 : 2^10 = 1024 := by native_decide
""".encode().decode("unicode_escape")

class Parse(unittest.TestCase):
    def test_parser_on_real_formats(self):
        txt = ("'a' does not depend on any axioms\n'b' depends on axioms: [propext, Classical.choice,\n Quot.sound]\n"
               "x.lean:1:1: error: Unknown constant `c`\n")
        self.assertEqual(fa.parse_print_axioms(txt, ["a", "b", "c"]),
                         {"a": [], "b": ["propext", "Classical.choice", "Quot.sound"], "c": None})

    def test_classify(self):
        c = fa.classify
        self.assertEqual(c("propext"), "KERNEL_STANDARD"); self.assertEqual(c("Classical.choice"), "CLASSICAL")
        self.assertEqual(c("sorryAx"), "UNKNOWN"); self.assertEqual(c("Foo.myAx", {"myAx"}), "PROJECT_AXIOM")
        self.assertEqual(c("t5._native.native_decide.ax_1_1"), "EXTERNAL")
        self.assertEqual(c("Lean.ofReduceBool"), "EXTERNAL")
        self.assertEqual(c("Dep.axiom1", external={"Dep.axiom1"}), "EXTERNAL")
        self.assertEqual(c("Dep.axiom1"), "UNKNOWN")

@unittest.skipUnless(HAVE, "needs lake + Lean v4.34.0")
class Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = tempfile.TemporaryDirectory(); cls.p = os.path.join(cls.t.name, "p"); cls.o = os.path.join(cls.t.name, "o")
        make_project(cls.p, BODY)
        fl.run_build(cls.p, cls.o + "b", min_free_gb=0.05)  # sorry in t4 => build FAIL verdict, but oleans still produced
    @classmethod
    def tearDownClass(cls): cls.t.cleanup()

    def run_audit(self, names, **kw): return fa.audit(self.p, "Mini", names, self.o, **kw)

    def test_clean_theorem_passes_empty_footprint(self):
        r = self.run_audit(["t0"]); self.assertEqual(r["verdict"], "PASS"); self.assertEqual(r["footprint"], [])

    def test_classical_passes_but_is_reported(self):
        r = self.run_audit(["t1"]); self.assertEqual(r["verdict"], "PASS"); self.assertEqual(r["reported"], {"t1": ["Classical.choice"]})

    def test_propext_is_kernel_standard_no_report(self):
        r = self.run_audit(["t2"]); self.assertEqual((r["verdict"], r["reported"]), ("PASS", {}))

    def test_project_axiom_fails(self):
        r = self.run_audit(["t3"]); self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["theorems"]["t3"]["classes"], {"myAx": "PROJECT_AXIOM"})

    def test_sorry_fails_as_unknown(self):
        r = self.run_audit(["t4"]); self.assertEqual(r["verdict"], "FAIL"); self.assertTrue(r["theorems"]["t4"]["uses_sorry"])

    def test_native_decide_reported_not_failed(self):
        r = self.run_audit(["t5"]); self.assertEqual(r["verdict"], "PASS"); self.assertTrue(r["theorems"]["t5"]["trusts_compiler"])
        self.assertIn("t5", r["reported"])

    def test_unknown_name_fails_closed(self):
        r = self.run_audit(["t0", "nope"]); self.assertEqual(r["verdict"], "FAIL"); self.assertIsNone(r["theorems"]["nope"]["axioms"])

    def test_probe_does_not_dirty_project(self):
        self.run_audit(["t0"]); self.assertFalse(fl.git_state(self.p)["dirty"])

if __name__ == "__main__":
    unittest.main()
