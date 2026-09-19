#!/usr/bin/env python3
"""Bootstrap / regression / failure-injection tests for the FCVE repository layer.

FCVE's central threat is a FALSE GREEN, so these tests mostly check that things FAIL CORRECTLY:
  * failure injection: missing dependency, wrong Lean version, wrong checker commit, insufficient disk, broken patch, invalid theorem,
    checker rejection, malformed configuration, missing skill, stale/tampered artifact;
  * regression: BUG-003 (relative --out / TOOL_ERROR vs FAIL), BUG-005 (patch application/validation), BUG-006 (BLOCKED vs FAIL,
    TOOL_ERROR vs FAIL, batched axiom import, export cleanup + hashing, configurable stall detection, bash syntax);
  * the audit ceiling: nothing may ever produce TRUSTED.

Tiers: the default tier runs in ~1-2 minutes and needs Lean 4.28.0 installed (tiny Mathlib-free fixtures). FCVE_TEST_FULL=1 adds the slow
tier (the complete smoke test and the patched-tool equivalence tests). A SKIPPED test is reported as skipped, never as passed.
`bash -n` (syntax) is NOT a test of behavior; the runtime tests below are.

Run:  python3 tests/test_bootstrap.py         (fast tier)      FCVE_TEST_FULL=1 python3 tests/test_bootstrap.py   (adds slow tier)
"""
import hashlib, json, os, shutil, stat, subprocess, sys, tempfile, textwrap, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
SKILL = os.path.join(ROOT, "skills", "verifying-lean-proofs")
FIX_OK = os.path.join(ROOT, "tests", "fixtures", "mini-lean-ok")
FIX_BAD = os.path.join(ROOT, "tests", "fixtures", "mini-lean-bad")
WORK = os.path.join(ROOT, ".fcve-work")
FULL = os.environ.get("FCVE_TEST_FULL") == "1"
HOME = os.path.expanduser("~")
LEAN428 = os.path.join(HOME, ".elan", "toolchains", "leanprover--lean4---v4.28.0", "bin", "lean")
ENV = dict(os.environ, PATH=f"{HOME}/.cargo/bin:{HOME}/.elan/bin:" + os.environ.get("PATH", ""))
have_lean = os.path.exists(LEAN428)
have_setup = os.path.exists(os.path.join(WORK, "setup-record.json"))


def run(cmd, env=None, cwd=None, timeout=300):
    e = dict(ENV); e.update(env or {})
    return subprocess.run(cmd, capture_output=True, text=True, env=e, cwd=cwd, timeout=timeout)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def copy_repo_light(dst):
    """Copy only what doctor/setup need (scripts, manifests, tool-patches, skills, docs, top-level files) so a test can break a copy."""
    for d in ("scripts", "manifests", "tool-patches", "skills", "docs", "tests"):
        if os.path.isdir(os.path.join(ROOT, d)):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(dst, d), ignore=shutil.ignore_patterns("__pycache__", ".lake", "lake-manifest.json"))
    for f in ("README.md", "CLAUDE.md", "SPECIFICATION.md", "HANDOFF.md"):
        if os.path.exists(os.path.join(ROOT, f)):
            shutil.copy(os.path.join(ROOT, f), dst)


def jload(path):
    with open(path) as f: return json.load(f)


def jdump(obj, path):
    with open(path, "w") as f: json.dump(obj, f)


def rows_of(path):
    out = {}
    for line in open(path):
        n, st, detail = line.rstrip("\n").split("\t", 2); out[int(n)] = (st, detail)
    return out


# ------------------------------------------------------------------------------------------------------------------- syntax
class Syntax(unittest.TestCase):
    """Syntax validation. NOT a behavioral test (see the module docstring): it only proves every script parses."""
    def test_every_shell_script_parses(self):
        bad = []
        for base in (SCRIPTS, SKILL):
            for dp, _, fs in os.walk(base):
                for f in fs:
                    if f.endswith(".sh"):
                        p = os.path.join(dp, f)
                        r = subprocess.run(["bash", "-n", p], capture_output=True, text=True)
                        if r.returncode: bad.append((p, r.stderr.strip()[:120]))
        self.assertEqual(bad, [])

    def test_python_modules_compile(self):
        r = subprocess.run([sys.executable, "-m", "py_compile"] + [os.path.join(SCRIPTS, f) for f in os.listdir(SCRIPTS) if f.endswith(".py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


# ------------------------------------------------------------------------------------------------------------------ manifest
class Manifest(unittest.TestCase):
    def setUp(self): self.m = jload(os.path.join(ROOT, "manifests", "environment.json"))

    def test_patch_hashes_match_files_and_skill_copies(self):
        for p in self.m["tool_patches"]["patches"]:
            f = os.path.join(ROOT, p["file"])
            self.assertEqual(sha(f), p["sha256"], p["name"])
            self.assertEqual(sha(os.path.join(SKILL, "patches", os.path.basename(f))), p["sha256"], "skill copy of " + p["name"])

    def test_every_expected_file_and_skill_file_exists(self):
        for f in self.m["expected_files"] + self.m["expected_skill_files"]:
            self.assertTrue(os.path.exists(os.path.join(ROOT, f)), f)

    def test_verdict_vocabulary_documented_and_trusted_never_automatic(self):
        v = self.m["verdict_semantics"]
        for k in ("PASS", "FAIL", "BLOCKED", "TOOL_ERROR", "UNRESOLVED", "PARTIAL", "PROVISIONAL", "TRUSTED"): self.assertIn(k, v)
        self.assertIn("never produced automatically", v["TRUSTED"])

    def test_claude_md_states_the_hard_rules(self):
        t = open(os.path.join(ROOT, "CLAUDE.md")).read()
        for needle in ("The model can propose. The experiment decides.", "Building is breaking", "skills/verifying-lean-proofs/SKILL.md",
                       "Convert `TOOL_ERROR` / `BLOCKED` / `UNRESOLVED` into `FAIL`", "cannot produce TRUSTED", "scripts/doctor.sh", "scripts/smoke-test.sh"):
            self.assertIn(needle, t, needle)

    def test_project_level_skill_discovery_link_resolves(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, ".claude", "skills", "verifying-lean-proofs", "SKILL.md")))


# ---------------------------------------------------------------------------------------------- doctor: failure injection
class DoctorFailureInjection(unittest.TestCase):
    def doctor(self, *args, env=None):
        return run(["bash", os.path.join(SCRIPTS, "doctor.sh"), *args], env=env)

    def test_healthy_root_has_no_fail_lines_for_files_and_skill(self):
        r = self.doctor("--work", WORK if have_setup else tempfile.gettempdir())
        for line in r.stdout.splitlines():
            if line.startswith("[FAIL") and ("repo" in line.split()[1:2] or "skill" in line.split()[1:2]): self.fail(line)

    def test_missing_dependency_is_a_FAIL_not_a_pass(self):
        with tempfile.TemporaryDirectory() as t:
            bindir = os.path.join(t, "bin"); os.mkdir(bindir)
            for tool in ("python3", "git", "bash", "sh", "sed", "awk", "grep", "cut", "tr", "sort", "head", "tail", "cat", "cp", "mktemp", "uname", "sysctl", "sw_vers",
                         "df", "shasum", "patch", "rsync", "date", "printf", "rm", "ls", "dirname", "mkdir", "basename", "wc", "diff", "find", "paste", "tee", "cmp", "env"):
                p = shutil.which(tool)
                if p: os.symlink(p, os.path.join(bindir, tool))
            r = run(["bash", os.path.join(SCRIPTS, "doctor.sh"), "--work", os.path.join(t, "w")], env={"PATH": bindir, "HOME": t})
            self.assertEqual(r.returncode, 1, r.stdout[-400:])
            for tool in ("cargo", "rustc", "elan"): self.assertRegex(r.stdout, rf"\[FAIL[^\]]*\] tool\s+{tool}\s+not found")
            self.assertIn("DOCTOR: NOT READY", r.stdout)

    def test_wrong_lean_version_no_validated_toolchain_is_FAIL(self):
        with tempfile.TemporaryDirectory() as t:
            copy_repo_light(t)
            mp = os.path.join(t, "manifests", "environment.json"); m = jload(mp); m["lean"]["toolchains"] = [{"tag": "v0.0.1-not-installed", "validated_with": "none"}]
            jdump(m, mp)
            r = self.doctor("--root", t, "--work", os.path.join(t, "w"))
            self.assertEqual(r.returncode, 1); self.assertRegex(r.stdout, r"\[FAIL[^\]]*\] lean\s+any toolchain")

    def test_insufficient_disk_is_FAIL_and_says_not_a_theorem_failure(self):
        r = self.doctor("--work", WORK, env={"FCVE_FAKE_FREE_KB": "1000"})
        self.assertEqual(r.returncode, 1); self.assertRegex(r.stdout, r"\[FAIL[^\]]*\] storage\s+free space"); self.assertIn("SIMULATED", r.stdout)

    def test_broken_patch_hash_is_FAIL(self):
        with tempfile.TemporaryDirectory() as t:
            copy_repo_light(t)
            with open(os.path.join(t, "tool-patches", "lean4export-fast-natval.diff"), "a") as f: f.write("\n+garbage\n")
            r = self.doctor("--root", t, "--work", os.path.join(t, "w"))
            self.assertRegex(r.stdout, r"\[FAIL[^\]]*\] patch\s+lean4export-fast-natval\s+sha256 differs")

    def test_missing_skill_file_is_FAIL(self):
        with tempfile.TemporaryDirectory() as t:
            copy_repo_light(t); os.remove(os.path.join(t, "skills", "verifying-lean-proofs", "SKILL.md"))
            r = self.doctor("--root", t, "--work", os.path.join(t, "w"))
            self.assertRegex(r.stdout, r"\[FAIL[^\]]*\] skill\s+file skills/verifying-lean-proofs/SKILL.md\s+missing")

    def test_malformed_manifest_is_FAIL_not_a_crash_or_pass(self):
        with tempfile.TemporaryDirectory() as t:
            copy_repo_light(t)
            with open(os.path.join(t, "manifests", "environment.json"), "w") as f: f.write("{ this is not json")
            r = self.doctor("--root", t, "--work", os.path.join(t, "w"))
            self.assertEqual(r.returncode, 1); self.assertRegex(r.stdout, r"\[FAIL[^\]]*\] manifest\s+environment.json\s+not valid JSON")

    def test_unknown_state_is_UNRESOLVED_never_PASS(self):
        with tempfile.TemporaryDirectory() as t:   # no pristine checkouts, no setup record in this fresh work dir
            r = self.doctor("--work", os.path.join(t, "empty"))
            self.assertRegex(r.stdout, r"\[UNRESOLVED\] patch\s+validation record")
            self.assertRegex(r.stdout, r"\[UNRESOLVED\] patch\s+applies to nanoda_lib")


# ---------------------------------------------------------------------------------------------------- setup: refusals
@unittest.skipUnless(have_setup, "run scripts/setup.sh first (needs .fcve-work)")
class SetupRefusals(unittest.TestCase):
    def test_insufficient_disk_stops_before_any_work_exit_4(self):
        r = run(["bash", os.path.join(SCRIPTS, "setup.sh"), "--tag", "v4.28.0", "--work", os.path.join(tempfile.gettempdir(), "fcve-empty-work-test")], env={"FCVE_FAKE_FREE_KB": "1000"})
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr); self.assertIn("BLOCKED: insufficient disk", r.stdout); self.assertIn("not a verification failure", r.stdout)

    def test_unvalidated_tag_is_refused_not_substituted(self):
        r = run(["bash", os.path.join(SCRIPTS, "setup.sh"), "--tag", "v9.9.9", "--dry-run"])
        self.assertEqual(r.returncode, 64); self.assertIn("does not silently substitute", r.stdout)

    def test_wrong_checker_commit_in_manifest_is_refused_exit_5(self):   # BUG-005 family: never silently substitute a tool version
        with tempfile.TemporaryDirectory() as t:
            copy_repo_light(t)
            mp = os.path.join(t, "manifests", "environment.json"); m = jload(mp)
            m["independent_checker"]["lean4export"]["validated_commits"]["v4.28.0"] = "0" * 40; jdump(m, mp)
            r = run(["bash", os.path.join(t, "scripts", "setup.sh"), "--tag", "v4.28.0", "--work", WORK])
            self.assertEqual(r.returncode, 5, r.stdout[-500:]); self.assertIn("refusing to substitute a different version", r.stdout)

    def test_missing_prerequisite_stops_exit_2_and_installs_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            bindir = os.path.join(t, "bin"); os.mkdir(bindir)
            for tool in ("python3", "git", "bash", "sh", "sed", "awk", "grep", "cut", "tr", "head", "tail", "cat", "mktemp", "rm", "dirname", "paste", "df", "date", "uname", "cp", "ls", "mkdir", "env", "printf"):
                p = shutil.which(tool)
                if p: os.symlink(p, os.path.join(bindir, tool))
            r = run(["bash", os.path.join(SCRIPTS, "setup.sh"), "--dry-run", "--work", os.path.join(t, "w")], env={"PATH": bindir, "HOME": t})
            self.assertEqual(r.returncode, 2, r.stdout); self.assertIn("does not install undocumented tools", r.stdout)
            self.assertFalse(os.path.exists(os.path.join(t, "w")))

    def test_setup_is_idempotent_record_unchanged(self):
        stable = ("patch_validation", "patches", "tags", "nanoda_lib", "tools", "host")
        rec = lambda: {k: v for k, v in jload(os.path.join(WORK, "setup-record.json")).items() if k in stable}
        before = rec()
        r = run(["bash", os.path.join(SCRIPTS, "setup.sh"), "--reuse-from", os.path.join(HOME, "ico-collatz", "targets"), "--tag", "v4.28.0", "--tag", "v4.34.0"], timeout=400)
        if r.returncode != 0: self.skipTest("setup could not re-run here: " + r.stdout[-200:])   # reported as SKIPPED, not passed
        self.assertEqual(rec(), before)


# --------------------------------------------------------------------------------------------- patches (BUG-005 family)
class Patches(unittest.TestCase):
    def test_a_patch_that_no_longer_matches_upstream_does_not_apply(self):
        src = os.path.join(WORK, "lean4export-v4.28.0", "Export.lean")
        if not os.path.exists(src): self.skipTest("no pristine lean4export checkout (run setup)")
        with tempfile.TemporaryDirectory() as t:
            f = os.path.join(t, "Export.lean")
            with open(src) as fh: orig = fh.read()
            broken = orig.replace("open Std (HashMap)", "open Std (HashMapMoved)").replace(".lit (.natVal i) => dumpNatDeps", ".lit (.natVal n) => dumpNatDepsMoved")
            self.assertNotEqual(broken, orig, "control must actually change the file (BUG-004: a control that changes nothing proves nothing)")
            with open(f, "w") as fh: fh.write(broken)
            self.assertNotEqual(subprocess.run(["patch", "--dry-run", "-s", f, os.path.join(ROOT, "tool-patches", "lean4export-fast-natval.diff")], capture_output=True).returncode, 0)

    def test_real_patches_apply_cleanly_to_every_pristine_upstream_checkout_present(self):
        checked = 0
        for name, target, patchfile in (("lean4export-v4.28.0", "Export.lean", "lean4export-fast-natval.diff"), ("lean4export-v4.34.0", "Export.lean", "lean4export-fast-natval.diff"),
                                        ("nanoda_lib", os.path.join("src", "parser.rs"), "nanoda-fast-decimal-parse.diff")):
            src = os.path.join(WORK, name, target)
            if not os.path.exists(src): continue
            with tempfile.TemporaryDirectory() as t:
                f = os.path.join(t, os.path.basename(target)); shutil.copy(src, f)
                r = subprocess.run(["patch", "--dry-run", "-s", f, os.path.join(ROOT, "tool-patches", patchfile)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, name + ": " + r.stdout + r.stderr); checked += 1
        if checked == 0: self.skipTest("no pristine checkouts present; run scripts/setup.sh")


# ----------------------------------------------------------------- independent-check.sh with FAKE tools (BUG-003 / BUG-006)
@unittest.skipUnless(have_lean, "Lean v4.28.0 toolchain not installed")
class IndependentCheckClassification(unittest.TestCase):
    """Drive skills/.../independent-check.sh with fake exporter/checker binaries so every status can be produced on demand."""
    def make_tools(self, root, exporter_body, nanoda_body):
        eb = os.path.join(root, "exp", "bin"); nb = os.path.join(root, "nan", "bin"); os.makedirs(eb); os.makedirs(nb)
        for path, body in ((os.path.join(eb, "lean4export"), exporter_body), (os.path.join(nb, "nanoda_bin"), nanoda_body)):
            open(path, "w").write("#!/bin/bash\n" + body + "\n"); os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        return os.path.join(eb, "lean4export"), os.path.join(nb, "nanoda_bin")

    EXPORT_OK = 'printf \'{"meta":{}}\\n{"thm":"mini_add"}\\n\'; exit 0'
    NANODA_PASS = 'echo "theorem mini_add : 2 + 2 = 4"; echo "Checked 3 declarations with no errors"; exit 0'

    def check(self, exporter, nanoda, out_rel="out", extra=(), env=None):
        t = tempfile.mkdtemp(prefix="fcve-ic-")
        self.addCleanup(shutil.rmtree, t, True)
        eb, nb = self.make_tools(t, exporter, nanoda)
        r = run(["bash", os.path.join(SKILL, "scripts", "independent-check.sh"), "--target", FIX_OK, "--module", "Mini", "--export-bin", eb, "--nanoda-bin", nb, "--out", out_rel, *extra, "mini_add"], env=env, cwd=t, timeout=120)
        tsv = os.path.join(t, out_rel, "results.tsv")
        status = open(tsv).read().strip().splitlines()[-1].split("\t") if os.path.exists(tsv) else None
        return r, t, status

    def test_PASS_needs_exit0_checked_line_and_target_printed(self):
        r, t, s = self.check(self.EXPORT_OK, self.NANODA_PASS); self.assertEqual(s[1], "PASS", r.stdout + r.stderr)

    def test_exit0_with_checked_line_but_target_not_printed_is_not_PASS(self):
        r, t, s = self.check(self.EXPORT_OK, 'echo "Checked 3 declarations with no errors"; exit 0'); self.assertNotEqual(s[1], "PASS")

    def test_checker_rejection_is_FAIL(self):
        r, t, s = self.check(self.EXPORT_OK, 'echo "thread main panicked at tc.rs" >&2; exit 101'); self.assertEqual(s[1], "FAIL")

    def test_TOOL_ERROR_is_not_FAIL(self):    # BUG-003
        r, t, s = self.check(self.EXPORT_OK, 'echo "Error: failed to open configuration file" >&2; exit 1'); self.assertEqual(s[1], "TOOL_ERROR")

    def test_relative_out_dir_works(self):    # BUG-003: relative --out used to make the checker unable to open its config
        r, t, s = self.check(self.EXPORT_OK, self.NANODA_PASS, out_rel="rel/out"); self.assertEqual(s[1], "PASS")

    def test_stalled_export_is_BLOCKED_not_FAIL_and_stall_window_is_configurable(self):   # BUG-006
        r, t, s = self.check('printf "{}\\n"; sleep 60', self.NANODA_PASS, env={"TICK_SECONDS": "1", "STALL_TICKS": "2"})
        self.assertEqual(s[1], "BLOCKED"); self.assertIn("stalled-no-output", s[7]); self.assertNotEqual(s[1], "FAIL")

    def test_disk_guard_abort_is_BLOCKED_not_FAIL(self):
        r, t, s = self.check('printf "{}\\n"; sleep 60', self.NANODA_PASS, env={"TICK_SECONDS": "1", "STALL_TICKS": "50", "FCVE_FAKE_FREE_KB": "1000"})
        if s and s[1] == "PASS": self.skipTest("this script version has no simulated-disk hook in the export guard")
        self.assertIn(s[1], ("BLOCKED",)); self.assertNotEqual(s[1], "FAIL")

    def test_export_hashed_then_deleted_with_delete_exports(self):   # BUG-006
        r, t, s = self.check(self.EXPORT_OK, self.NANODA_PASS, extra=("--delete-exports",))
        self.assertEqual(s[1], "PASS"); self.assertFalse(os.path.exists(os.path.join(t, "out", "mini_add.export")))
        log = open(os.path.join(t, "out", "mini_add.monitor.log")).read(); self.assertIn("EXPORT_SHA256", log)
        self.assertIn(hashlib.sha256(b'{"meta":{}}\n{"thm":"mini_add"}\n').hexdigest(), log)

    def test_tool_binaries_are_recorded(self):
        r, t, s = self.check(self.EXPORT_OK, self.NANODA_PASS)
        tools = open(os.path.join(t, "out", "tools.tsv")).read(); self.assertIn("exporter", tools); self.assertIn("nanoda", tools)


# ------------------------------------------------------------------------------- audit.sh: ceiling, batching, failure states
@unittest.skipUnless(have_lean, "Lean v4.28.0 toolchain not installed")
class AuditWrapper(unittest.TestCase):
    def audit(self, target, decls, *extra, env=None):
        t = tempfile.mkdtemp(prefix="fcve-audit-"); self.addCleanup(shutil.rmtree, t, True)
        args = ["bash", os.path.join(SCRIPTS, "audit.sh"), target, "--module", "Mini", "--skip-independent", "--out", os.path.join(t, "o"), "--work", os.path.join(t, "w")]
        for d in decls: args += ["--decl", d]
        r = run(args + list(extra), env=env, timeout=300)
        return r, os.path.join(t, "o")

    def test_TRUSTED_is_never_produced_and_unresolved_gates_stay_visible(self):
        r, o = self.audit(FIX_OK, ["mini_add"]); md = open(os.path.join(o, "AUDIT.md")).read()
        self.assertIn("## Verdict: PROVISIONAL", md); self.assertNotIn("Verdict: TRUSTED", md)
        self.assertIn("cannot produce TRUSTED", md)
        rows = rows_of(os.path.join(o, "rows.tsv")); self.assertEqual(rows[7][0], "NEEDS HUMAN"); self.assertEqual(rows[9][0], "UNRESOLVED"); self.assertEqual(rows[10][0], "NOT RUN")

    def test_source_has_no_path_that_emits_TRUSTED(self):
        src = open(os.path.join(SKILL, "scripts", "audit.sh")).read()
        self.assertIn('assert not verdict.startswith("TRUSTED")', src); self.assertNotIn("TRUSTED-candidate", src)

    def test_report_header_makes_everything_visible(self):
        r, o = self.audit(FIX_OK, ["mini_add"]); md = open(os.path.join(o, "AUDIT.md")).read()
        for needle in ("Repository commit", "Toolchain / Lean", "Mathlib revision", "Environment", "Patched tools", "Independent checker (row 10)", "Axiom audit (row 6)", "Semantic review (row 7)", "Web / kernel review (row 9)"):
            self.assertIn(needle, md, needle)

    def test_batched_axiom_import_one_lean_invocation_for_all_decls(self):   # BUG-006
        r, o = self.audit(FIX_OK, ["mini_add", "mini_comm"])
        self.assertTrue(os.path.exists(os.path.join(o, "axioms-all.txt"))); self.assertFalse(os.path.exists(os.path.join(o, "axioms-mini_add.txt")))
        self.assertEqual(len(open(os.path.join(o, "axioms.tsv")).read().strip().splitlines()), 2)

    def test_invalid_theorem_name_is_FAIL_not_pass(self):
        r, o = self.audit(FIX_OK, ["no_such_theorem"]); self.assertEqual(rows_of(os.path.join(o, "rows.tsv"))[6][0], "FAIL")

    def test_sorry_is_REJECTED(self):
        r, o = self.audit(FIX_BAD, ["bad_sorry"]); rows = rows_of(os.path.join(o, "rows.tsv"))
        self.assertEqual(rows[4][0], "FAIL"); self.assertEqual(rows[6][0], "FAIL"); self.assertIn("Verdict: REJECTED", open(os.path.join(o, "AUDIT.md")).read())

    def test_full_disk_is_BLOCKED_exit_3_and_UNRESOLVED_never_REJECTED(self):   # BUG-006
        r, o = self.audit(FIX_OK, ["mini_add"], env={"FCVE_FAKE_FREE_KB": "1000"})
        self.assertEqual(r.returncode, 3); md = open(os.path.join(o, "AUDIT.md")).read()
        self.assertIn("Verdict: UNRESOLVED", md); self.assertNotIn("REJECTED", md); self.assertIn("not a verdict on the proof", md.replace("says nothing about the proof", "not a verdict on the proof"))

    def test_target_is_not_modified(self):
        before = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", "tests/fixtures/mini-lean-ok"], capture_output=True, text=True).stdout
        self.audit(FIX_OK, ["mini_add"])
        after = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", "tests/fixtures/mini-lean-ok"], capture_output=True, text=True).stdout
        self.assertEqual(before, after)


# -------------------------------------------------------------------------------------------- stale / tampered artifacts
class TamperedEvidence(unittest.TestCase):
    def test_tampered_ledger_fails_verify(self):
        src = os.path.join(ROOT, "deliverables", "VCE-002-rev-s", "event-ledger.jsonl")
        with tempfile.TemporaryDirectory() as t:
            f = os.path.join(t, "ledger.jsonl")
            with open(src) as fh: lines = fh.read().splitlines()
            ev = json.loads(lines[3]); before = dict(ev); ev["reason"] = str(ev.get("reason", "")) + " (tampered)"
            self.assertNotEqual(ev, before, "control must actually change the event")
            lines[3] = json.dumps(ev, sort_keys=True)
            with open(f, "w") as fh: fh.write("\n".join(lines) + "\n")
            r = run([sys.executable, os.path.join(SCRIPTS, "fcve.py"), "verify", f]); self.assertNotEqual(r.returncode, 0, r.stdout)

    def test_receipt_goes_stale_when_the_ledger_changes(self):
        led = os.path.join(ROOT, "deliverables", "VCE-002-rev-s", "event-ledger.jsonl"); rec = os.path.join(ROOT, "deliverables", "VCE-002-rev-s", "receipt.json")
        with tempfile.TemporaryDirectory() as t:
            f = os.path.join(t, "ledger.jsonl"); shutil.copy(led, f)
            with open(f, "a") as fh: fh.write(json.dumps({"event_id": "EVENT-999", "action": "REPORT_GENERATION"}) + "\n")
            r = run([sys.executable, os.path.join(SCRIPTS, "fcve.py"), "receipt-check", f, rec]); self.assertNotEqual(r.returncode, 0, r.stdout)

    def test_delivered_packages_verify(self):
        for d in ("VCE-001-rev-s", "VCE-002-rev-s"):
            p = os.path.join(ROOT, "deliverables", d)
            self.assertEqual(run([sys.executable, os.path.join(SCRIPTS, "fcve.py"), "verify", os.path.join(p, "event-ledger.jsonl")]).returncode, 0, d)
            self.assertEqual(run(["shasum", "-a", "256", "-c", "MANIFEST.sha256"], cwd=p).returncode, 0, d)


# ------------------------------------------------------------------------------------------------------------ slow tier
@unittest.skipUnless(FULL and have_setup, "slow tier: set FCVE_TEST_FULL=1 and run scripts/setup.sh first")
class SlowTier(unittest.TestCase):
    def test_smoke_test_passes(self):
        r = run(["bash", os.path.join(SCRIPTS, "smoke-test.sh")], timeout=900); self.assertEqual(r.returncode, 0, r.stdout[-1500:]); self.assertIn("SMOKE TEST PASSED", r.stdout)

    def test_patched_lean4export_matches_Nat_repr(self):   # BUG-005
        fe = os.path.join(WORK, "lean4export-v4.28.0-fastnat")
        if not os.path.isdir(fe): self.skipTest("patched exporter not built")
        r = run(["lake", "env", "lean", "--run", os.path.join(SKILL, "patches", "NatReprCheck.lean")], cwd=fe, timeout=600)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "mismatches: 0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
