import json, os, re, shutil, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fcve_report as rp, fcve_evidence as fe, fcve_semantic as fs_

H = os.path.expanduser("~/ico-collatz")
LEAN = {"verification-002": [(f"{H}/ico_collatz_verification/IcoCollatzVerification/PowersOfTwoReachOne.lean", "powers_of_two_reach_one")],
        "verification": [(f"{H}/targets/eliahou-collatz-bounds/Results.lean", "results_eliahou_theorem_1_1")]}
HAVE_LEAN = all(os.path.exists(p) for v in LEAN.values() for p, _ in v)
HAVE_TEC = bool(shutil.which("tectonic") or shutil.which("pdflatex"))

def tex_for(v, lean=True):
    return rp.build_tex(rp.load(os.path.join(ROOT, v, "evidence", "event-ledger.jsonl"), lean=LEAN[v] if lean and HAVE_LEAN else ()))

class Escape(unittest.TestCase):
    def test_specials_and_unicode_math(self):
        self.assertEqual(rp.esc("a_b & 50% #1 {x}"), r"a\_b \& 50\% \#1 \{x\}")
        self.assertIn(r"\ensuremath{\mathbb{N}}", rp.esc("ℕ")); self.assertIn(r"\leq", rp.esc("≤"))
    def test_unmapped_character_raises_not_dropped(self):
        with self.assertRaises(rp.ReportError): rp.esc("a ⚛ b")
    def test_quote_pairs(self):
        self.assertEqual(rp.esc('the "compressed" map'), "the ``compressed'' map")

class Markdown(unittest.TestCase):
    def test_math_bold_italic_headings_lists(self):
        t = rp.md_to_tex("# Title\n\n- $f : \\mathbb{N} \\to \\mathbb{N}$ is **standard**, a *set*\n")
        self.assertIn(r"\subsection*{Title}", t); self.assertIn(r"$f : \mathbb{N} \to \mathbb{N}$", t)
        self.assertIn(r"\textbf{standard}", t); self.assertIn(r"\emph{set}", t); self.assertIn(r"\begin{itemize}", t)
    def test_unsafe_math_never_reaches_tex(self):
        t = rp.md_to_tex(r"see $\input{/etc/passwd}$ and $\write18{x}$")
        self.assertNotIn(r"\input{", t.replace(r"\textbackslash{}input", "")); self.assertIn("textbackslash", t)
    def test_table_pipe_inside_backticks_is_one_cell(self):
        self.assertEqual(len(rp._split_cells("| a | `x | y` | b |")), 3)
    def test_display_math(self):
        self.assertIn(r"\[", rp.md_to_tex("$$\nx^2 + 1\n$$\n"))
    def test_unmappable_character_fails_closed_even_through_the_verbatim_fallback(self):
        with self.assertRaises(rp.ReportError): rp.prose("plain ⚛ text", "x")  # never silently dropped
    def test_missing_input_is_explicit(self):
        self.assertIn("Not recorded", rp.prose(None, "a file"))

class Structure(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.tex = tex_for("verification-002", lean=False)
    def test_clean(self): self.assertEqual(rp.check_structure(self.tex), [])
    def test_third_diagram_rejected(self):
        self.assertTrue(any("two diagrams" in p for p in rp.check_structure(self.tex.replace(r"\end{document}", r"\begin{tikzpicture}\end{tikzpicture}\end{document}"))))
    def test_image_rejected(self):
        self.assertTrue(rp.check_structure(self.tex.replace(r"\end{document}", r"\includegraphics{x.png}\end{document}")))
    def test_section_order_enforced(self):
        self.assertTrue(rp.check_structure(self.tex.replace(r"\section{Axiom Audit}", r"\section{Something Else}")))
    def test_trust_statement_must_come_first(self):
        t = self.tex.replace(r"\begin{abstract}", r"\noindent\textbf{Trust Statement.} dup" + "\n" + r"\begin{abstract}")
        self.assertTrue(rp.check_structure(t))
    def test_verdict_and_hype_rejected(self):
        self.assertTrue(rp.check_structure(self.tex.replace(r"\end{abstract}", " PROMOTE " + r"\end{abstract}")))
        self.assertTrue(rp.check_structure(self.tex.replace("Trust Statement.", "Fully verified. Trust Statement.", 1)))

@unittest.skipUnless(HAVE_LEAN, "needs ~/ico-collatz sources")
class AgainstDeliveredReports(unittest.TestCase):
    APPX = ["Lean Source", "Tests", "Evidence Receipt"]

    def secs(self, tex): return re.findall(r"^\\section\{([^}]*)\}", tex, re.M)

    def test_generated_reports_have_all_17_sections_plus_appendices_and_two_diagrams(self):
        for v in ("verification", "verification-002"):
            gen = tex_for(v)
            self.assertEqual(self.secs(gen), rp.SECTIONS + self.APPX, v); self.assertEqual(gen.count(r"\begin{tikzpicture}"), 2)

    def test_delivered_vce001_matches_the_required_structure(self):
        d = open(os.path.join(ROOT, "verification", "report", "report.tex")).read()
        self.assertEqual(self.secs(d), rp.SECTIONS + self.APPX); self.assertEqual(d.count(r"\begin{tikzpicture}"), 2)

    def test_KNOWN_DEFECT_delivered_vce002_lacks_semantic_bridge_and_appendices(self):
        # spec §57.2 (bridge mandatory) and §33 (appendices). Pinned so the finding stays visible;
        # when a corrected VCE-002 report is issued this test should be inverted.
        d = open(os.path.join(ROOT, "verification-002", "report", "report.tex")).read()
        self.assertNotIn("Semantic Bridge", self.secs(d))
        self.assertEqual(sorted(set(rp.SECTIONS + self.APPX) - set(self.secs(d))), sorted(["Semantic Bridge"] + self.APPX))
        self.assertEqual(d.count(r"\begin{tikzpicture}"), 2)

    def test_source_names_used_not_lean_identifiers_for_lemmas(self):
        gen = tex_for("verification")
        for name in ("Lemma 2.2", "Theorem 2.1", "Lemma 3.1", "Corollary 2.3", "Theorem 3.2"): self.assertIn(name, gen)

    def test_verdict_words_appear_only_inside_the_permitted_status_block(self):
        for v in ("verification", "verification-002"):
            tex = tex_for(v); self.assertEqual(rp.check_structure(tex), [], v)
            front = tex[:tex.index(r"\end{abstract}")]; concl = tex.split(r"\section{Conclusion}")[1].split(r"\appendix")[0]
            concl = concl[:concl.index(rp.PS_BEGIN)] + concl[concl.index(rp.PS_END):]
            self.assertNotRegex(front + concl, rp.VERDICT_WORDS); self.assertIn("This is not a decision", tex)

    def test_lean_statement_and_signals_present(self):
        g = tex_for("verification"); self.assertIn("Function.Injective", g); self.assertIn("injectivity", g)

def rdata(v):
    return rp.load(os.path.join(ROOT, v, "evidence", "event-ledger.jsonl"))

class FixedToolBugs(unittest.TestCase):
    def test_esc_break_never_cuts_an_escape_command(self):
        out = rp.esc_break("2^k " + "x" * 40 + " a_b")
        self.assertIn(r"\textasciicircum{}", out); self.assertNotRegex(out, r"\\[a-z]*\\allowbreak\{\}[a-z]")
        self.assertEqual(rp.esc_break("plain words"), "plain words")

    def test_results_are_shown_in_full_not_cut_mid_sentence(self):
        d = rdata("verification"); tex = rp.build_tex(d)
        full = next(e["result"] for e in d["events"] if e["action"] == "INDEPENDENT_CHECK")
        self.assertGreater(len(full), 130)
        self.assertIn(rp.esc(full).split(" -- ")[1][:60], tex.replace("\n", " "))            # the WHY survives
        self.assertNotIn("(rep.", tex)

    def test_no_placeholder_when_the_run_recorded_no_location(self):
        for v in ("verification", "verification-002"):
            tex = rp.build_tex(rdata(v)); self.assertNotIn("<project directory>", tex)
            self.assertIn("NOT RECORDED", tex.split(r"\section{Reproducibility Instructions}")[1].split(r"\section{Correction")[0])
            self.assertIn("were not recorded", tex)

    def test_repro_block_uses_recorded_facts_when_a_build_record_exists(self):
        d = rdata("verification-002")
        d["records"]["build"] = {"cwd": "/w/proj", "command": "lake build Mod", "git": {"remote_url": "https://example.org/a/proj.git", "revision": "a" * 40},
                                 "environment": {"lean_toolchain_file": "leanprover/lean4:v4.34.0", "lake_version": "Lake version 5.0.0"}}
        b = rp.repro_block(d)
        for want in ("git clone https://example.org/a/proj.git", "git checkout " + "a" * 40, "lake build Mod", "Lake version 5.0.0", "/w/proj"):
            self.assertIn(want.replace("_", r"\_") if "_" in want else want, b.replace(r"\allowbreak{}", ""))
        self.assertNotIn("repository location and commit were not recorded", b)
        self.assertIn("independent-check commands were not recorded", b)      # a different, true note: this fixture has no Gate 9 record

    def test_trust_statement_has_no_garbled_joins_or_bookkeeping(self):
        for v in ("verification", "verification-002"):
            tex = rp.build_tex(rdata(v)); ts = tex.split(r"\begin{abstract}")[0].split("Trust Statement.")[1]
            self.assertNotRegex(ts, r"\.;|\.\."); self.assertNotIn("ledger events predate", ts); self.assertNotIn("wording outside", ts)

    def test_trust_statement_stays_brief_detail_lives_in_the_sections(self):
        tex = rp.build_tex(rdata("verification")); ts = tex.split(r"\begin{abstract}")[0].split("Trust Statement.")[1]
        sec10 = tex.split(r"\section{Independent Check}")[1].split(r"\section{Computational")[0]
        self.assertNotIn("memoization", ts); self.assertIn("no verdict", ts)               # brief in the statement
        self.assertIn("memoization", sec10); self.assertNotIn("..", sec10.replace("...", ""))   # full in Section 10, no doubled period

    def test_missing_reproduction_facts_are_a_stated_limitation_not_none(self):
        for v in ("verification", "verification-002"):
            tex = rp.build_tex(rdata(v)); ts = tex.split(r"\begin{abstract}")[0]
            self.assertIn("cannot be reproduced exactly from this report", ts); self.assertNotIn("none recorded", ts)
            self.assertIn("checker used for the independent check is not identified", tex.split(r"\section{Verification Limitations}")[1])
        d = rdata("verification-002"); d["records"]["build"] = {"cwd": "/w", "command": "lake build", "git": {"remote_url": "https://e/x.git", "revision": "a" * 40}, "environment": {"lean_toolchain_file": "t", "lake_version": "L"}}
        d["records"]["independent"] = {"checker": {"nanoda_commit": "c"}, "commands": {"export": "e", "check": "c"}, "result": "INDEPENDENTLY_CHECKED"}
        subs, _ = rp.plain_limitations(d["receipt"], d["events"], records=d["records"]); self.assertFalse([x for x in subs if "not recorded for this run" in x or "not identified" in x])

    def test_limitations_are_deduplicated_and_notes_are_separated(self):
        for v in ("verification", "verification-002"):
            d = rdata(v); subs, notes = rp.plain_limitations(d["receipt"], d["events"])
            self.assertEqual(len(subs), len(set(subs)))
            self.assertEqual(sum("wording outside" in n for n in notes), 1)             # grouped, not one line per event
            self.assertTrue(all("Gate 10" not in x for x in subs if "not recorded" in x and subs.count(x) > 1))
        d = rdata("verification-002"); subs, _ = rp.plain_limitations(d["receipt"], d["events"])
        self.assertEqual(sum("Gate 10" in x for x in subs), 1)                          # was stated twice

PR = os.path.join(ROOT, "reviewed-records")

def with_bridge(v, **over):
    src = json.load(open(os.path.join(PR, ("vce-001" if v == "verification" else "vce-002") + "-semantic-gate7-record.json")))
    src.update(over); d = tempfile.mkdtemp(); p = os.path.join(d, "r.json"); json.dump(src, open(p, "w"))
    try:
        return rp.load(os.path.join(ROOT, v, "evidence", "event-ledger.jsonl"), bridge_record=p), rp
    finally: shutil.rmtree(d, True)

class BridgeVerdictInReport(unittest.TestCase):
    def verdict_part(self, tex): return tex.split(r"\subsection*{Verdict}")[1].split(r"\section{Lean Environment}")[0]

    def test_without_a_record_the_verdict_is_NOT_SET_never_inferred(self):
        for v in ("verification", "verification-002"):
            d = rdata(v); tex = rp.build_tex(d)
            self.assertEqual(rp.bridge_state(d)[1], "NOT SET"); self.assertIn("NOT SET", self.verdict_part(tex))
            self.assertNotIn("FAITHFUL", self.verdict_part(tex)); self.assertIn("No reviewer-set semantic-bridge verdict", tex)

    def test_vce001_now_states_the_third_verdict_with_all_six_31_parts(self):
        d, _ = with_bridge("verification", reviewer="assistant (Claude)"); tex = rp.build_tex(d)
        self.assertIn("FAITHFUL WITH EXPLICIT REPRESENTATIONAL DIFFERENCE", self.verdict_part(tex)); self.assertIn("PROPOSED", self.verdict_part(tex))
        for title in rp._DISC_TITLES.values(): self.assertIn(rp.esc(title), tex)
        self.assertIn("Function.Injective", tex); self.assertEqual(rp.check_structure(tex), [])

    def test_the_shipped_records_are_confirmed_by_a_human_reviewer(self):
        for v, want in (("verification", fs_.WITH_DIFF), ("verification-002", "FAITHFUL")):
            d, _ = with_bridge(v); verdict, state, who = rp.bridge_state(d)
            self.assertEqual((verdict, state, who), (want, "CONFIRMED", "Wilson")); tex = rp.build_tex(d)
            self.assertNotIn("PROPOSED", self.verdict_part(tex)); self.assertNotIn("awaits human confirmation", tex); self.assertIn("Set by Wilson", tex)
        self.assertEqual(rp.check_structure(rp.build_tex(with_bridge("verification")[0])), [])

    def test_vce002_is_faithful_and_has_no_representational_section(self):
        d, _ = with_bridge("verification-002"); tex = rp.build_tex(d)
        self.assertIn("FAITHFUL", self.verdict_part(tex)); self.assertNotIn("Representational difference (Section 31)", tex)

    def test_a_proposed_verdict_is_flagged_as_a_limitation_and_a_human_one_is_not(self):
        d, _ = with_bridge("verification-002", reviewer="assistant (Claude)"); self.assertIn("awaits human confirmation", rp.build_tex(d))
        d, _ = with_bridge("verification-002", reviewer="Wilson Lord"); tex = rp.build_tex(d)
        self.assertNotIn("awaits human confirmation", tex); self.assertNotIn("PROPOSED", self.verdict_part(tex)); self.assertIn("Set by Wilson Lord", tex)
        self.assertEqual(rp.bridge_state(d)[1], "CONFIRMED")

    def test_an_invalid_record_fails_closed(self):
        with self.assertRaises(rp.ReportError): with_bridge("verification", bridge_verdict="FAITHFUL")      # contradicts its own FOUND checks
        with self.assertRaises(rp.ReportError): with_bridge("verification", difference_disclosure={"informal_meaning": "x"})

class VceReadThroughFixes(unittest.TestCase):
    """The four tool fixes from the VCE-001 mathematician read-through."""
    def test_source_citation_from_the_runs_own_metadata_is_in_the_title_and_section_1(self):
        d = rdata("verification"); tex = rp.build_tex(d)
        self.assertIn("Eliahou, S. (1993)", d["source_meta"]["source_citation"])
        title = tex.split(r"\title{")[1].split(r"\author")[0]
        self.assertIn("Source: Eliahou, S. (1993)", title); self.assertIn("Discrete Mathematics", title)
        self.assertIn("Source: Eliahou, S. (1993)", tex.split(r"\section{Mathematical Statement}")[1].split(r"\section{Definitions")[0])

    def test_no_citation_means_no_subtitle_and_nothing_invented(self):
        d = rdata("verification"); d["source_meta"] = None; tex = rp.build_tex(d)
        self.assertNotIn("Source: ", tex.split(r"\title{")[1].split(r"\author")[0])

    def test_a_pointer_to_material_outside_the_package_is_a_stated_limitation(self):
        self.assertEqual(rp.dangling_refs(rdata("verification")["events"]), [("EVENT-006", "see prior receipt for full log")])
        self.assertEqual(rp.dangling_refs(rdata("verification-002")["events"]), [])          # 'see EVENT-010' style refs are not flagged
        tex = rp.build_tex(rdata("verification")); ts = tex.split(r"\begin{abstract}")[0]
        self.assertIn("EVENT-006 refers to a log or receipt that is not part of this report", ts)
        self.assertNotIn("refers to a log or receipt", rp.build_tex(rdata("verification-002")))
        self.assertEqual(rp.dangling_refs([{"event_id": "E", "result": "PASS -- see EVENT-004 and the notes"}]), [])
        self.assertEqual(len(rp.dangling_refs([{"event_id": "E", "result": "PASS; see the transcript"}])), 1)

    def test_correction_ledger_lists_failures_not_missing_verdicts(self):
        tex = rp.build_tex(rdata("verification")); cl = tex.split(r"\section{Correction Ledger}")[1].split(r"\section{Conclusion}")[0]
        self.assertIn("TEST-001", cl)                                                          # a real FAIL that was corrected
        self.assertNotIn("lean4export stalls", cl); self.assertNotIn("memoization", cl)        # the long no-verdict text is not repeated here
        self.assertIn("INDEPCHECK-001", cl); self.assertIn("are not corrections", cl)          # named once, as a pointer to the limitations
        self.assertIn("No failed or disputed gate results", rp.build_tex(rdata("verification-002")).split(r"\section{Correction Ledger}")[1])

    def test_independent_check_status_is_glossed_in_the_trust_statement_and_abstract(self):
        tex = rp.build_tex(rdata("verification")); front = tex.split(r"\end{abstract}")[0]
        self.assertGreaterEqual(front.count("no verdict: the external checker could not process this proof"), 2)     # trust statement + abstract
        t2 = rp.build_tex(rdata("verification-002")).split(r"\end{abstract}")[0]
        self.assertNotIn("could not process", t2)

SNAP = os.path.join(ROOT, "reviewed-records", "vce-001-repro-snapshot.json")

def with_snap(v="verification", **over):
    snap = json.load(open(SNAP)); snap.update(over)
    if "git_over" in over: snap["git"] = {**snap["git"], **snap.pop("git_over")}
    d = rdata(v); d["repro"] = snap; return d

class ReproSnapshotInTheReport(unittest.TestCase):
    def sect(self, tex): return tex.split(r"\section{Reproducibility Instructions}")[1].split(r"\section{Correction")[0].replace(r"\allowbreak{}", "").replace(r"\&", "&")
    def flat(self, tex): return tex.replace(r"\allowbreak{}", "").replace("\n", " ")

    def test_vce001_now_answers_q11_with_a_labelled_after_the_fact_snapshot(self):
        tex = rp.build_tex(rp.load(os.path.join(ROOT, "verification", "evidence", "event-ledger.jsonl"), repro_snapshot=SNAP)); s = self.sect(tex)
        for want in ("https://github.com/tangentstorm/eliahou-collatz-bounds.git", "db804ce6305ea99a817f067869607f8b677d895a", "working tree clean", "Lake version 5.0.0",
                     "git clone https://github.com/tangentstorm/eliahou-collatz-bounds.git", "git checkout db804ce6305ea99a817f067869607f8b677d895a",
                     "lake exe cache get && lake build", "Captured 2026", "yes (db804ce6)"):
            self.assertIn(want, s, want)
        self.assertNotIn("NOT RECORDED", s.split("Checker")[0].split("Repository URL")[1])         # repo, commit, toolchain, Lake are all filled in
        self.assertIn("do not prove what the original run built", self.flat(tex))

    def test_the_limitation_changes_from_not_recorded_to_captured_after_the_run(self):
        tex = rp.build_tex(rp.load(os.path.join(ROOT, "verification", "evidence", "event-ledger.jsonl"), repro_snapshot=SNAP)); ts = self.flat(tex.split(r"\begin{abstract}")[0])
        self.assertNotIn("were not recorded for this run", ts); self.assertIn("were captured after the run", ts); self.assertIn("the commit matches the one named in the run's own notes", ts)

    def test_the_build_command_is_the_recorded_one_not_a_guess(self):
        self.assertEqual(rp._recorded_build_command(rdata("verification")["events"]), ("lake exe cache get && lake build", "EVENT-006"))
        self.assertEqual(rp._recorded_build_command(rdata("verification-002")["events"])[0], "lake build IcoCollatzVerification.PowersOfTwoReachOne")
        self.assertEqual(rp._recorded_build_command([]), (None, None))

    def test_dirty_no_commit_and_mismatch_never_get_clone_commands(self):
        for over, needle in (({"state": "DIRTY", "git_over": {"dirty": True, "dirty_files": ["?? a", "?? b"]}}, "2 uncommitted or untracked files"),
                             ({"state": "NO_COMMIT", "git_over": {"revision": None, "dirty_files": ["?? a"]}}, "no commit"),
                             ({"revision_matches_expected": False}, "does NOT match")):
            tex = rp.build_tex(with_snap(**over)); s = self.sect(tex)
            self.assertNotIn("git clone", s, over); self.assertNotIn("git checkout", s, over); self.assertIn(needle, self.flat(tex), over)

    def test_clean_local_only_commit_is_not_called_unrecorded_and_gets_no_clone_command(self):
        tex = rp.build_tex(with_snap(git_over={"remote_url": None, "revision": "b" * 40, "dirty": False, "dirty_files": []})); s = self.sect(tex)
        self.assertNotIn("git clone", s); self.assertNotIn("were not recorded for this run (see table above)", self.flat(tex))
        self.assertIn("commit is local only", self.flat(tex)); self.assertIn("b" * 40, self.flat(tex))

    def test_without_a_snapshot_or_build_record_it_is_still_not_recorded(self):
        tex = rp.build_tex(rdata("verification")); self.assertIn("were not recorded for this run", tex.split(r"\begin{abstract}")[0]); self.assertNotIn("git clone", self.sect(tex))

    def test_a_build_record_beats_a_snapshot(self):
        d = with_snap(); d["records"]["build"] = {"cwd": "/w", "command": "lake build Mod", "git": {"remote_url": "https://e/x.git", "revision": "a" * 40},
                                                  "environment": {"lean_toolchain_file": "t", "lake_version": "L", "lake_manifest_sha256": "0" * 64}}
        s = self.sect(rp.build_tex(d)); self.assertIn("Project directory when run", s); self.assertNotIn("Captured 2026", s)

class PermittedStatus(unittest.TestCase):
    def block(self, v, **kw):
        d = rp.load(os.path.join(ROOT, v, "evidence", "event-ledger.jsonl"), **kw); t = rp.build_tex(d)
        return t[t.index(rp.PS_BEGIN):t.index(rp.PS_END)]

    def test_vce002_promote_not_supported_because_gate10(self):
        b = self.block("verification-002"); self.assertIn("not supported", b); self.assertIn("Gate 10", b.replace("G10", "Gate 10") if "G10" in b else b)
        self.assertIn("This is not a decision", b)

    def test_vce002_with_explicit_waiver_says_so_and_supports_promotion(self):
        b = self.block("verification-002", waivers={"G10": "Gate 8 script also served as the computational check"})
        self.assertIn("satisfies the conditions", b); self.assertIn("Waived explicitly", b)

    def test_pre_report_ledger_does_not_call_its_own_report_a_blocker(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(f"{d}/evidence"); p = f"{d}/evidence/l.jsonl"
            for e in fe.read_ledger(os.path.join(ROOT, "verification-002", "evidence", "event-ledger.jsonl"))[:11]:
                open(p, "a").write(json.dumps(e, sort_keys=True) + "\n")
            t = rp.build_tex(rp.load(p, root=ROOT, waivers={"G10": "Gate 8 script also served as the computational check"}))
        b = t[t.index(rp.PS_BEGIN):t.index(rp.PS_END)]
        self.assertNotIn("G12", b); self.assertIn("satisfies the conditions", b); self.assertIn("assuming this report itself compiles cleanly", b)
        self.assertIn("Waived explicitly", b); self.assertNotIn("textbackslash", b); self.assertNotIn("\\S 53", b)   # once printed a literal "\S 53"

    def test_vce001_lists_independent_check_and_order_as_reasons(self):
        b = self.block("verification"); self.assertIn("not supported", b); self.assertIn("G9", b); self.assertIn("ORDER", b)

    def test_conclusion_carries_the_55_status_lines_but_no_decision_line(self):
        tex = rp.build_tex(rdata("verification-002")); concl = tex.split(r"\section{Conclusion}")[1].split(r"\appendix")[0]
        for lab in ("FORMAL PROOF", "AXIOM AUDIT", "INDEPENDENT CHECK", "COUNTEREXAMPLE SEARCH", "COMPUTATIONAL TEST", "REPRODUCIBILITY"): self.assertIn(lab, concl)
        self.assertNotIn("GOVERNANCE DECISION", concl)

    def test_asserting_the_decision_anywhere_is_rejected(self):
        tex = tex_for("verification-002", lean=False).replace(r"\section{Conclusion}", r"\section{Conclusion} The final decision is PROMOTE.")
        self.assertTrue(rp.check_structure(tex))
    def test_missing_block_is_rejected(self):
        tex = tex_for("verification-002", lean=False).replace(rp.PS_BEGIN, "")
        self.assertTrue(any("permits" in x for x in rp.check_structure(tex)))

@unittest.skipUnless(HAVE_TEC, "needs tectonic or pdflatex")
class Compile(unittest.TestCase):
    def build(self, body, extra=""):
        d = tempfile.mkdtemp(); p = os.path.join(d, "t.tex")
        with open(p, "w") as f: f.write("\\documentclass{article}\n" + extra + "\\begin{document}\n" + body + "\n\\end{document}\n")
        self.addCleanup(shutil.rmtree, d, True); return rp.compile_report(p, d, only_cached=False)

    def test_clean_document_passes(self): self.assertEqual(self.build("Hello $x^2$.")["verdict"], "PASS")
    def test_undefined_reference_fails_even_though_exit_code_is_zero(self):
        r = self.build(r"See \ref{nope}."); self.assertEqual(r["verdict"], "FAIL"); self.assertEqual(r["final_counts"]["unresolved_references"], 1)
    def test_undefined_citation_fails(self): self.assertEqual(self.build(r"See \cite{gone}.")["final_counts"]["missing_citations"], 1)
    def test_missing_glyph_fails(self):
        r = self.build("θ ≤ 1"); self.assertEqual(r["verdict"], "FAIL"); self.assertGreater(r["final_counts"]["missing_characters"], 0)
    def test_missing_figure_fails(self): self.assertEqual(self.build(r"\includegraphics{nothere.png}", r"\usepackage{graphicx}")["verdict"], "FAIL")
    def test_relative_output_dir_works(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True); cwd = os.getcwd(); os.chdir(d)
        try:
            with open("t.tex", "w") as f: f.write("\\documentclass{article}\\begin{document}x\\end{document}\n")
            r = rp.compile_report("t.tex", "sub/out", only_cached=False)
        finally: os.chdir(cwd)
        self.assertEqual(r["verdict"], "PASS"); self.assertTrue(os.path.exists(os.path.join(d, "sub", "out", "t.pdf")))

    def test_records_compiler_honestly(self):
        r = self.build("x"); self.assertIn(r["compiler"], ("pdflatex", "tectonic")); self.assertEqual(r["spec_named_compiler_used"], r["compiler"] == "pdflatex")
        self.assertIn("pdflatex named in §51 was NOT used" if r["compiler"] == "tectonic" else "2 passes", rp.event_fields(r, "a", "b")["result"])

    @unittest.skipUnless(HAVE_LEAN, "needs ~/ico-collatz sources")
    def test_both_real_reports_compile_clean(self):
        for v in ("verification", "verification-002"):
            d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
            with open(os.path.join(d, "report.tex"), "w") as f: f.write(tex_for(v))
            r = rp.compile_report(os.path.join(d, "report.tex"), d, only_cached=False)
            self.assertEqual(r["verdict"], "PASS", (v, r["final_counts"])); self.assertEqual(len(r["pdf_sha256"]), 64)

if __name__ == "__main__":
    unittest.main()
