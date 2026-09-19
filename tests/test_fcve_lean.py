import json, os, shutil, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_lean as fl

TOOLCHAIN = "leanprover/lean4:v4.34.0"  # installed locally (elan)
HAVE = shutil.which("lake") and os.path.isdir(os.path.expanduser("~/.elan/toolchains/leanprover--lean4---v4.34.0"))

def make_project(d, body="theorem t : 1 + 1 = 2 := rfl\n", git=True):
    os.makedirs(d)
    files = {"lean-toolchain": TOOLCHAIN + "\n",
             "lakefile.toml": 'name = "mini"\ndefaultTargets = ["Mini"]\n\n[[lean_lib]]\nname = "Mini"\n',
             "lake-manifest.json": json.dumps({"version": "1.1.0", "packagesDir": ".lake/packages", "packages": [], "name": "mini", "lakeDir": ".lake"}),
             "Mini.lean": body, ".gitignore": ".lake/\n"}
    for name, text in files.items():
        with open(f"{d}/{name}", "w") as f:
            f.write(text)
    if git:
        for c in (["init", "-q"], ["add", "-A"], ["-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "i"]):
            subprocess.run(["git"] + c, cwd=d, check=True)

@unittest.skipUnless(HAVE, "needs lake + Lean v4.34.0 toolchain")
class Build(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.p = os.path.join(self.t.name, "p"); self.o = os.path.join(self.t.name, "out")
    def tearDown(self): self.t.cleanup()

    def test_clean_project_passes_with_full_record(self):
        make_project(self.p)
        r = fl.run_build(self.p, self.o, min_free_gb=0.05)
        self.assertEqual(r["verdict"], "PASS", r["failed_conditions"])
        self.assertEqual(r["exit_code"], 0)
        self.assertTrue(os.path.exists(os.path.join(self.o, "build-incremental-record.json")))
        self.assertIn("4.34.0", r["environment"]["lean_version_actual"])
        self.assertEqual(len(r["git"]["revision"]), 40)
        self.assertEqual(len(r["logs"]["stdout"]["sha256"]), 64)

    def test_sorry_fails_via_text_scan_and_log_warning(self):
        make_project(self.p, "theorem t : 1 + 1 = 2 := by sorry\n")
        r = fl.run_build(self.p, self.o, min_free_gb=0.05)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("no_sorry_admit_in_source", r["failed_conditions"])
        self.assertIn("no_sorry_warnings_in_log", r["failed_conditions"])

    def test_comment_mentioning_sorry_is_not_a_hit(self):
        make_project(self.p, "-- no sorry here\n/- admit nothing -/\ntheorem t : 1 + 1 = 2 := rfl\n")
        self.assertEqual(fl.scan_sorry(self.p), [])

    def test_broken_build_fails_exit_code(self):
        make_project(self.p, "theorem t : 1 + 1 = 3 := rfl\n")
        r = fl.run_build(self.p, self.o, min_free_gb=0.05)
        self.assertEqual(r["verdict"], "FAIL"); self.assertIn("exit_code_zero", r["failed_conditions"])

    def test_dirty_tree_fails_hidden_modifications(self):
        make_project(self.p)
        with open(f"{self.p}/Mini.lean", "a") as f:
            f.write("-- edit\n")
        r = fl.run_build(self.p, self.o, min_free_gb=0.05)
        self.assertIn("no_hidden_local_modifications", r["failed_conditions"])

    def test_record_captures_remote_url_and_lake_version_for_reproduction(self):
        make_project(self.p)
        subprocess.run(["git", "remote", "add", "origin", "https://example.org/x/mini.git"], cwd=self.p, check=True)
        r = fl.run_build(self.p, self.o, min_free_gb=0.05)
        self.assertEqual(r["git"]["remote_url"], "https://example.org/x/mini.git"); self.assertIn("Lake", r["environment"]["lake_version"])

    def test_no_remote_is_recorded_as_none_not_invented(self):
        make_project(self.p); self.assertIsNone(fl.run_build(self.p, self.o, min_free_gb=0.05)["git"]["remote_url"])

    def test_not_a_git_repo_fails_closed(self):
        make_project(self.p, git=False)
        self.assertIn("no_hidden_local_modifications", fl.run_build(self.p, self.o, min_free_gb=0.05)["failed_conditions"])

@unittest.skipUnless(HAVE, "needs lake + Lean v4.34.0 toolchain")
class Snapshot(unittest.TestCase):
    def setUp(self): self.t = tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup); self.p = os.path.join(self.t.name, "p"); self.o = os.path.join(self.t.name, "o")

    def test_clean_checkout_at_a_commit_matching_expectation(self):
        make_project(self.p); subprocess.run(["git", "remote", "add", "origin", "https://example.org/x/mini.git"], cwd=self.p, check=True)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.p, capture_output=True, text=True).stdout.strip()
        r = fl.snapshot(self.p, self.o, expect_commit=head[:8])
        self.assertEqual((r["state"], r["revision_matches_expected"], r["git"]["revision"], r["git"]["remote_url"]), ("CLEAN_AT_COMMIT", True, head, "https://example.org/x/mini.git"))
        self.assertIn("after the run", r["caveat"]); self.assertTrue(os.path.exists(os.path.join(self.o, "repro-snapshot.json")))

    def test_a_commit_that_differs_from_the_one_the_notes_name_is_reported(self):
        make_project(self.p); self.assertFalse(fl.snapshot(self.p, self.o, expect_commit="deadbeef")["revision_matches_expected"])

    def test_dirty_tree_means_the_commit_does_not_identify_the_source(self):
        make_project(self.p)
        with open(os.path.join(self.p, "Mini.lean"), "a") as f: f.write("-- edit\n")
        r = fl.snapshot(self.p, self.o); self.assertEqual(r["state"], "DIRTY"); self.assertEqual(len(r["git"]["dirty_files"]), 1)

    def test_a_repository_with_no_commit_is_NO_COMMIT_never_the_word_HEAD(self):   # the bug: rev-parse printed "HEAD" on an empty repo
        make_project(self.p, git=False); subprocess.run(["git", "init", "-q"], cwd=self.p, check=True)
        r = fl.snapshot(self.p, self.o); self.assertEqual(r["state"], "NO_COMMIT"); self.assertIsNone(r["git"]["revision"])
        self.assertIsNone(fl.git_state(self.p)["revision"])

    def test_not_a_repo_and_not_a_lean_project(self):
        make_project(self.p, git=False); self.assertEqual(fl.snapshot(self.p, self.o)["state"], "NOT_A_REPO")
        with self.assertRaises(fl.PreflightError): fl.snapshot(self.t.name, self.o)

    def test_capture_is_read_only(self):
        make_project(self.p); before = fl.git_state(self.p); fl.snapshot(self.p, self.o); self.assertEqual(fl.git_state(self.p), before)

class Preflight(unittest.TestCase):
    def test_disk_floor_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            make_project(os.path.join(d, "p"), git=False)
            with self.assertRaises(fl.PreflightError):
                fl.preflight(os.path.join(d, "p"), min_free_gb=10**6)

    def test_missing_toolchain_file_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(fl.PreflightError):
                fl.preflight(d)

if __name__ == "__main__":
    unittest.main()
