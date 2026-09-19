import json, os, stat, sys, tempfile, textwrap, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_independent as fi, fcve_evidence as fe

META = '{"meta":{"exporter":{"name":"lean4export","version":"3.1.0"},"format":{"version":"%s"},"lean":{"githash":"x","version":"%s"}}}'
FP = ["propext", "Quot.sound"]

class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = self.t.name; self.o = os.path.join(self.d, "out"); os.makedirs(self.o)
        self.proj = os.path.join(self.d, "proj"); os.makedirs(self.proj)
    def tearDown(self): self.t.cleanup()

    def exe(self, name, body):
        p = os.path.join(self.d, name)
        with open(p, "w") as f: f.write("#!/bin/sh\n" + textwrap.dedent(body))
        os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)
        return p

    def exporter(self, fmt="3.1.0", lean="4.34.0", tail="\\n", body="", code=0, sleep=""):
        return self.exe("exp.sh", f"printf '%s\\n' '{META % (fmt, lean)}'\n{body}\n{sleep}\nprintf '{{\"in\":1}}{tail}'\nexit {code}\n")

    def nanoda(self, decl="foo", n=10, axioms=("propext", "Quot.sound"), code=0, printed=True, checked=True):
        lines = ""
        if printed: lines += f"theorem {decl} : True\n"
        for a in axioms: lines += f"axiom {a} {{a : Prop}} : a\n"
        if checked: lines += f"Checked {n} declarations with no errors\n"
        return self.exe("nan.sh", f"cat <<'EOF'\n{lines}EOF\nexit {code}\n")

    def go(self, exp, nan, permitted=FP, decl="foo", **kw):
        kw.setdefault("tick_s", 0.05); kw.setdefault("expected_lean_version", "4.34.0")
        return fi.check(self.proj, "M", decl, self.o, exp, nan, permitted, export_cmd=[exp], **kw)

class Outcomes(Base):
    def test_full_pass(self):
        r = self.go(self.exporter(), self.nanoda())
        self.assertEqual(r["result"], "INDEPENDENTLY_CHECKED"); self.assertEqual(r["declarations_checked"], 10)
        self.assertEqual(len(r["export"]["sha256"]), 64); self.assertTrue(r["export"]["deleted_after_check"])
        self.assertFalse(os.path.exists(os.path.join(self.o, "foo.export")))
        self.assertIn("independence", r["note"])

    def test_record_carries_the_exact_commands_run(self):
        r = self.go(self.exporter(), self.nanoda())
        self.assertIn("foo.export", r["commands"]["export"]); self.assertIn("foo.nanoda-config.json", r["commands"]["check"])

    def test_keep_export(self):
        self.go(self.exporter(), self.nanoda(), keep_export=True)
        self.assertTrue(os.path.exists(os.path.join(self.o, "foo.export")))

    def test_missing_binary_is_unavailable(self):
        r = fi.check(self.proj, "M", "foo", self.o, "/no/such/exp", "/no/such/nan", FP)
        self.assertEqual(r["result"], "CHECKER_UNAVAILABLE")

    def test_exporter_failure_is_incompatible(self):
        self.assertEqual(self.go(self.exporter(code=2), self.nanoda())["result"], "CHECKER_INCOMPATIBLE")

    def test_truncated_export_is_incompatible(self):
        r = self.go(self.exporter(tail=""), self.nanoda()); self.assertEqual(r["result"], "CHECKER_INCOMPATIBLE"); self.assertIn("incomplete", r["reason"])

    def test_stall_after_first_byte_is_incompatible(self):
        r = self.go(self.exporter(sleep="sleep 5"), self.nanoda(), stall_ticks=3)
        self.assertEqual((r["result"], r["export"]["abort_reason"]), ("CHECKER_INCOMPATIBLE", "stalled-no-output"))

    def test_slow_start_hits_time_cap_not_stall_and_is_unavailable(self):
        # no bytes at all for a while: must NOT be read as an exporter defect
        slow = self.exe("slow.sh", "sleep 5\n")
        r = self.go(slow, self.nanoda(), stall_ticks=2, max_s=0.5)
        self.assertEqual((r["result"], r["export"]["abort_reason"]), ("CHECKER_UNAVAILABLE", "time-cap"))

    def test_disk_floor_is_unavailable(self):
        r = self.go(self.exporter(sleep="sleep 5"), self.nanoda(), min_free_gb=10**9)
        self.assertEqual((r["result"], r["export"]["abort_reason"]), ("CHECKER_UNAVAILABLE", "disk-floor"))

    def test_version_mismatch_is_incompatible(self):
        self.assertEqual(self.go(self.exporter(lean="4.28.0"), self.nanoda())["result"], "CHECKER_INCOMPATIBLE")
        self.assertEqual(self.go(self.exporter(fmt="3.2.0"), self.nanoda())["result"], "CHECKER_INCOMPATIBLE")

    def test_checker_rejection_is_disagreement_not_pass(self):
        self.assertEqual(self.go(self.exporter(), self.nanoda(code=1, checked=False))["result"], "CHECKER_DISAGREEMENT")

    def test_axiom_footprint_mismatch_is_disagreement(self):
        r = self.go(self.exporter(), self.nanoda(axioms=("propext", "Quot.sound", "Classical.choice")))
        self.assertEqual(r["result"], "CHECKER_DISAGREEMENT"); self.assertIn("Gate 6", r["reason"])

    def test_zero_declarations_is_not_a_pass(self):
        self.assertEqual(self.go(self.exporter(), self.nanoda(n=0))["result"], "CHECKER_DISAGREEMENT")

    def test_target_not_printed_is_incompatible(self):
        self.assertEqual(self.go(self.exporter(), self.nanoda(printed=False))["result"], "CHECKER_INCOMPATIBLE")

    def test_config_makes_extra_axioms_hard_error_with_gate6_list(self):
        self.go(self.exporter(), self.nanoda())
        cfg = json.load(open(os.path.join(self.o, "foo.nanoda-config.json")))
        self.assertEqual(sorted(cfg["permitted_axioms"]), sorted(FP)); self.assertTrue(cfg["unpermitted_axiom_hard_error"])

    def test_not_applicable_record(self):
        self.assertEqual(fi.not_applicable("EMPIRICAL claim; no Lean artifact", self.o)["result"], "NOT_APPLICABLE")

class Parse(unittest.TestCase):
    def test_parse_nanoda_strips_universe_params(self):
        n, ax = fi.parse_nanoda("axiom Quot.sound.{u} {a : Prop} : a\naxiom propext {a : Prop} : a\nChecked 1662 declarations with no errors\n")
        self.assertEqual((n, ax), (1662, ["Quot.sound", "propext"]))
    def test_no_summary_line_is_none(self):
        self.assertIsNone(fi.parse_nanoda("theorem x\n")[0])

class Ledger(Base):
    def test_wording_guard(self):
        led = os.path.join(self.d, "l.jsonl")
        fe.append_event(led, action="SOURCE_INTAKE", reason="r", input="a", output="S", method="m", result="ok")
        kw = dict(action="INDEPENDENT_CHECK", reason="r", input="a", output="b", method="m")
        for bad in ("PASS -- Checked 1662", "nanoda verified it"):
            with self.assertRaises(fe.ArtifactError): fe.append_event(led, result=bad, **kw)
        fe.append_event(led, result="CHECKER_INCOMPATIBLE -- exporter stalled", **kw)
        fe.append_event(led, result="PASS -- old wording", legacy_result_wording=True, **kw)
        self.assertEqual(len(fe.read_ledger(led)), 3)

if __name__ == "__main__":
    unittest.main()
