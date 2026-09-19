"""FCVE automated LaTeX report (spec §23, §27-34, §51, §57).

Assembles report.tex from the ledger, the receipt facts, claims/assumptions and
the run records, then compiles it and CHECKS the compile (§51). Rules enforced
structurally, not by convention:
  * exactly two diagrams (§23); required sections in §33 order; Trust Statement
    first (§57.4); limitations as a table; exact reproduction commands.
  * the report never prints the governance verdict: it is Gate 12 and must
    precede Gate 13 (§2). The decision lives in the receipt.
  * source prose (normalized claim, comparison notes) is included VERBATIM from
    the run's files; nothing mathematical is invented. Missing input -> an
    explicit "Not recorded" box.
  * unmappable non-ASCII characters are an error, never silently dropped.
  * the compile passes only if the .log has 0 fatal errors, 0 unresolved
    references, 0 missing citations, 0 missing figures, 0 missing characters.
    Exit code 0 is not enough: tectonic exits 0 while dropping glyphs.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess

import fcve_evidence as fe
import fcve_graph as fg
import fcve_receipt as fr
import fcve_semantic as fs
import fcve_limits as fl_
from fcve_lean import _sha

NR = "NOT RECORDED"
SECTIONS = ["Mathematical Statement", "Definitions and Assumptions", "Proof Outline", "Proof Dependency Diagram",
            "Formalization", "Semantic Bridge", "Lean Environment", "Formal Verification", "Axiom Audit",
            "Independent Check", "Computational / Adversarial Tests", "Verification Limitations", "Verification Matrix",
            "Trust / Verification Chain", "Reproducibility Instructions", "Correction Ledger", "Conclusion"]  # §33
FORBIDDEN = ("Fully verified", "THEOREM VERIFIED", "fully verified")  # §27, §54
PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm,mathtools}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,backgrounds}
\usepackage{hyperref}
\usepackage{longtable}
\usepackage{array}
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{corollary}[theorem]{Corollary}
\newtheorem{definition}[theorem]{Definition}
\newtheorem{remark}[theorem]{Remark}
\newenvironment{sourceresult}[1]{\par\medskip\noindent\textbf{#1.}\ \itshape}{\par\medskip}
\sloppy
\emergencystretch=3em
"""

_UNI = {"Ω": r"\Omega", "ω": r"\omega", "θ": r"\theta", "Θ": r"\Theta", "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta",
        "ε": r"\varepsilon", "λ": r"\lambda", "μ": r"\mu", "π": r"\pi", "σ": r"\sigma", "Σ": r"\Sigma", "φ": r"\varphi", "ℕ": r"\mathbb{N}",
        "ℤ": r"\mathbb{Z}", "ℚ": r"\mathbb{Q}", "ℝ": r"\mathbb{R}", "ℂ": r"\mathbb{C}", "≤": r"\leq", "≥": r"\geq", "≠": r"\neq", "≈": r"\approx",
        "→": r"\to", "←": r"\leftarrow", "↔": r"\leftrightarrow", "⇒": r"\Rightarrow", "⟨": r"\langle", "⟩": r"\rangle", "∀": r"\forall",
        "∃": r"\exists", "∈": r"\in", "∉": r"\notin", "⊂": r"\subset", "⊆": r"\subseteq", "∪": r"\cup", "∩": r"\cap", "∧": r"\wedge",
        "∨": r"\vee", "¬": r"\neg", "×": r"\times", "·": r"\cdot", "±": r"\pm", "∞": r"\infty", "√": r"\sqrt{}", "∑": r"\sum", "∏": r"\prod",
        "∘": r"\circ", "↑": r"\uparrow", "∣": r"\mid", "∅": r"\emptyset", "⁻": r"^{-}", "¹": r"^{1}", "₁": r"_{1}", "₂": r"_{2}",
        "ₖ": r"_{k}", "⊢": r"\vdash", "≡": r"\equiv", "∼": r"\sim", "…": r"\ldots", "λ": r"\lambda", "▸": r"\triangleright"}
_TEXT = {"—": "---", "–": "--", "‘": "`", "’": "'", "“": "``", "”": "''", "§": r"\S{}", "\u00a0": "~", "✓": r"\checkmark{}"}
_SPECIAL = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&", "#": r"\#", "_": r"\_", "%": r"\%",
            "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


class ReportError(Exception):
    pass


def esc(text):
    """Escape data for LaTeX text. Unicode math -> math commands. A character with
    no mapping raises: silent glyph loss in a math report is content corruption."""
    out, bad = [], set()
    text = re.sub(r'"([^"\n]*)"', "\u201c\\1\u201d", str(text))  # straight quote pairs -> typographic
    for ch in text:
        if ch in _SPECIAL:
            out.append(_SPECIAL[ch])
        elif ch in _UNI:
            out.append(r"\ensuremath{" + _UNI[ch] + "}")
        elif ch in _TEXT:
            out.append(_TEXT[ch])
        elif ord(ch) < 128 or ch == "\n":
            out.append(ch)
        elif 0xC0 <= ord(ch) <= 0xFF:  # Latin-1 letters render in the default font
            out.append(ch)
        else:
            bad.add(ch)
    if bad:
        raise ReportError(f"no LaTeX mapping for characters {sorted(bad)} (add to _UNI or fix the source text)")
    return "".join(out)


def code(text, size=r"\footnotesize"):
    """Preformatted block that survives unicode AND wraps: each source line is a
    hanging-indent paragraph in \ttfamily, breakable after _ / . , so long Lean
    identifiers do not run off the page."""
    lines = []
    for ln in str(text).rstrip().splitlines():
        ind = len(ln) - len(ln.lstrip(" "))
        body = esc(ln.lstrip(" ")) or "~"
        for a in (r"\_", "/", "."):
            body = body.replace(a, a + r"\allowbreak{}")
        lines.append(r"\hspace*{%.2fem}%s\par" % (ind * 0.55, body))
    return "{" + size + r"\ttfamily\raggedright\hangindent=1.4em\hangafter=1\noindent" + "\n" + "\n".join(lines) + "\n}\n"


_UNSAFE_MATH = re.compile(r"\\(input|include|write|openout|read|catcode|def|edef|gdef|xdef|csname|immediate|usepackage|newcommand|renewcommand|special|jobname|InputIfFileExists|url|href|verb|lstinline)\b")
_MATH_SPAN = re.compile(r"(?<![\\$])\$(?!\$)(.+?)(?<![\\$])\$")


def _math(inner):
    """Raw LaTeX math from the source is passed through only if it is free of
    file/command-definition primitives and balanced. Unicode symbols inside are mapped."""
    if _UNSAFE_MATH.search(inner) or inner.count("{") != inner.count("}"):
        raise ReportError("unsafe or unbalanced math span")
    out = []
    for ch in inner:
        if ch in _UNI:
            out.append(_UNI[ch])
        elif ord(ch) < 128:
            out.append(ch)
        else:
            raise ReportError(f"unmappable character {ch!r} in math")
    return "".join(out)


def _inline(text):
    """Inline markdown: **bold**, `code`, $math$; everything else escaped."""
    pieces, pos = [], 0
    tok = re.compile(r"\*\*(.+?)\*\*|`([^`]+)`|(?<![\\$])\$(?!\$)(.+?)(?<![\\$])\$|(?<![*\w])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![*\w])")
    for m in tok.finditer(text):
        pieces.append(esc(text[pos:m.start()]))
        if m.group(1) is not None:
            pieces.append(r"\textbf{%s}" % _inline(m.group(1)))
        elif m.group(2) is not None:
            pieces.append(r"\texttt{%s}" % esc(m.group(2)))
        elif m.group(4) is not None:
            pieces.append(r"\emph{%s}" % _inline(m.group(4)))
        else:
            try:
                pieces.append("$" + _math(m.group(3)) + "$")
            except ReportError:
                pieces.append(esc(m.group(0)))  # fall back to literal text, never unsafe TeX
        pos = m.end()
    pieces.append(esc(text[pos:]))
    return "".join(pieces)


def _split_cells(row):
    """Split a pipe-table row on '|' that is NOT inside a backtick span."""
    cells, cur, in_code = [], [], False
    for ch in row.strip().strip("|") if not row.strip().startswith("||") else row:
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    cells.append("".join(cur))
    return cells


def md_to_tex(md):
    """Small, deliberate markdown subset: headings, bullets, pipe tables, **bold**,
    `code`, $math$/$$math$$. Anything else is escaped text. Raises ReportError if a
    line cannot be rendered safely; callers fall back to code()."""
    out, lines, i, in_list = [], md.splitlines(), 0, False
    def close():
        nonlocal in_list
        if in_list:
            out.append(r"\end{itemize}"); in_list = False
    while i < len(lines):
        ln = lines[i].rstrip()
        st = ln.strip()
        if not st or re.fullmatch(r"-{3,}", st):
            close(); i += 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)$", st)
        if m:
            close(); n = len(m.group(1))
            out.append((r"\subsection*{%s}", r"\subsubsection*{%s}", r"\paragraph*{%s}", r"\paragraph*{%s}")[n - 1] % _inline(m.group(2)))
            i += 1; continue
        if st.startswith("$$"):
            close(); buf = [st]
            while not (buf[-1].rstrip().endswith("$$") and (len(buf) > 1 or len(st) > 2)) and i + 1 < len(lines):
                i += 1; buf.append(lines[i].strip())
            body = " ".join(buf).strip()[2:-2]
            out.append(r"\[" + _math(body) + r"\]"); i += 1; continue
        if st.startswith("|"):
            close(); block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append([c.strip() for c in _split_cells(lines[i].strip())]); i += 1
            rows = [r for r in block if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            nc = max(len(r) for r in rows); w = 0.92 / nc
            out.append(r"\begin{center}\small\begin{tabular}{%s}\toprule" % "".join(r"p{%.2f\textwidth}" % w for _ in range(nc)))
            for k, r in enumerate(rows):
                out.append(" & ".join(_inline(c) for c in r + [""] * (nc - len(r))) + r" \\" + (r" \midrule" if k == 0 else ""))
            out.append(r"\bottomrule\end{tabular}\end{center}"); continue
        m = re.match(r"^[-*]\s+(.*)$", st)
        if m:
            if not in_list:
                out.append(r"\begin{itemize}"); in_list = True
            out.append(r"\item " + _inline(m.group(1))); i += 1; continue
        close(); out.append(_inline(st) + "\n"); i += 1
    close()
    return "\n".join(out) + "\n"


def prose(md, what):
    """Typeset a run file as mathematics; if it cannot be rendered safely, show it
    verbatim instead of dropping or mangling it."""
    if not md:
        return missing(what)
    try:
        return md_to_tex(md)
    except ReportError:
        return code(md)


def esc_break(text, n=14):
    """esc() with break points inside long unbroken tokens (hashes, paths). Chunks the RAW text
    and escapes each chunk separately, so an escape command is never cut in half."""
    def one(tok):
        return esc(tok) if len(tok) <= n else r"\allowbreak{}".join(esc(tok[k:k + n]) for k in range(0, len(tok), n))
    return "".join(p if p.isspace() else one(p) for p in re.split(r"(\s+)", str(text)))


def missing(what):
    return r"\begin{remark}\textit{Not recorded: %s.} This input was not captured during the run, so nothing is shown in its place.\end{remark}" % esc(what)


def _read(path):
    return open(path, errors="replace").read() if path and os.path.isfile(path) else None


def load(ledger, root=None, lean=(), waivers=None, bridge_record=None, repro_snapshot=None, limitations_record=None):
    events = fe.read_ledger(ledger)
    run_dir = os.path.dirname(os.path.dirname(os.path.abspath(ledger)))
    rcpt = fr.build_receipt(ledger, root=root, waivers=waivers, allow_pending=True)
    def ev_file(action, suffix):
        e = fr._last(events, action)
        f = next((x for x in (e["evidence"] if e else []) if x.endswith(suffix)), None)
        return fr._find(f, ledger, root) if f else None
    cp, ap = ev_file("CLAIM_EXTRACTION", "claims.json"), ev_file("ASSUMPTION_EXTRACTION", "assumptions.json")
    mp = ev_file("SOURCE_INTAKE", "source-metadata.json")
    def md(action, suffix=".md"):
        return _read(ev_file(action, suffix))
    d = {"events": events, "run_dir": run_dir, "receipt": rcpt, "graph": fg.build(events),
         "claims": json.load(open(cp))["claims"] if cp else None, "assumptions": json.load(open(ap)) if ap else None,
         "normalized": md("SEMANTIC_NORMALIZATION"), "gate4": md("LEAN_FORMALIZATION_COMPARISON"), "gate7": md("SEMANTIC_RE_AUDIT"),
         "records": fr._records(run_dir), "lean_statements": [], "source_meta": json.load(open(mp)) if mp else None}
    bpath = bridge_record or glob_first(os.path.join(run_dir, "**", "semantic-gate7*record*.json"))
    d["bridge"], d["bridge_path"] = None, bpath
    if bpath:
        d["bridge"] = json.load(open(bpath))
        probs = fs.validate(d["bridge"])
        if probs:  # fail closed: an invalid verdict is never rendered
            raise ReportError(f"bridge record {bpath} is invalid: " + "; ".join(probs[:4]))
    lpath = limitations_record or glob_first(os.path.join(run_dir, "**", "reviewer-limitations*.json"))
    d["reviewer_limits"] = json.load(open(lpath)) if lpath else None
    if d["reviewer_limits"] is not None:
        lp = fl_.validate(d["reviewer_limits"])
        if lp:  # fail closed, like the bridge record
            raise ReportError(f"reviewer limitations record {lpath} is invalid: " + "; ".join(lp[:4]))
    rpath = repro_snapshot or glob_first(os.path.join(run_dir, "**", "repro-snapshot*.json"))
    d["repro"] = json.load(open(rpath)) if rpath else None
    corr = glob_first(os.path.join(run_dir, "**", "correction-ledger*.md"))
    d["correction_md"] = _read(corr)
    for path, thm in lean:
        d["lean_statements"].append((thm, fs.extract_statement(open(path).read(), thm), fs.lean_signals(fs.extract_statement(open(path).read(), thm))))
    return d


def glob_first(pat):
    import glob
    h = sorted(glob.glob(pat, recursive=True))
    return h[0] if h else None


# ---------------------------------------------------------------- diagrams (exactly two, §23)
def diagram_dependency(claims):
    """Theorem-specific: what depends on what, labelled with the SOURCE's names (§29)."""
    if not claims:
        return missing("claims.json (needed to draw the proof dependency diagram)")
    by = {c["claim_id"]: c for c in claims}
    depth = {}
    def dep(i, seen=()):
        if i in depth:
            return depth[i]
        refs = [r for r in by[i].get("referenced_lemmas", []) if r in by and r not in seen]
        depth[i] = 0 if not refs else 1 + max(dep(r, seen + (i,)) for r in refs)
        return depth[i]
    for i in by:
        dep(i)
    if len(by) == 1:  # no lemma structure recorded: draw the source's own proof steps, if captured
        only = next(iter(by.values()))
        steps = list((only.get("proof_structure") or {}).items())
        if steps:
            t = [r"\begin{center}", r"\begin{tikzpicture}[box/.style={draw,rounded corners,align=center,minimum width=58mm,font=\small}, node distance=8mm, >=Stealth]"]
            prev = None
            for k, (key, val) in enumerate(steps):
                lab = esc(key.replace("_", " ").capitalize() + ": " + (val if len(val) < 46 else val[:43] + "..."))
                t.append(r"\node[box%s] (s%d) {%s};" % ("" if prev is None else f", below=of {prev}", k, lab))
                if prev:
                    t.append(r"\draw[->] (%s) -- (s%d);" % (prev, k))
                prev = f"s{k}"
            t.append(r"\node[box, below=of %s] (goal) {%s};" % (prev, esc(only.get("theorem_name") or only["claim_id"])))
            t += [r"\draw[->] (%s) -- (goal);" % prev, r"\end{tikzpicture}", r"\end{center}"]
            return "\n".join(t)
    rows = {}
    for i, dp in sorted(depth.items(), key=lambda x: (x[1], x[0])):
        rows.setdefault(dp, []).append(i)
    lab = lambda i: esc(by[i].get("theorem_name") or i)
    t = [r"\begin{center}", r"\begin{tikzpicture}[box/.style={draw,rounded corners,align=center,minimum width=34mm,font=\small,fill=white}, >=Stealth]"]
    for dp, ids in sorted(rows.items()):
        for k, i in enumerate(ids):
            t.append(r"\node[box] (%s) at (%.1f,%.1f) {%s};" % (re.sub(r"\W", "", i), (k - (len(ids) - 1) / 2) * 4.2, -dp * 1.7, lab(i)))
    t.append(r"\begin{scope}[on background layer]")
    for i, c in by.items():
        for r in c.get("referenced_lemmas", []):
            if r in by:
                span = depth[i] - depth[r]
                style = "" if span <= 1 else ("bend left=28" if (sum(map(ord, r + i)) % 2) else "bend right=28")
                t.append(r"\draw[->%s] (%s) to (%s);" % ((", " + style) if style else "", re.sub(r"\W", "", r), re.sub(r"\W", "", i)))
    t += [r"\end{scope}", r"\end{tikzpicture}", r"\end{center}"]
    return "\n".join(t)


def diagram_trust(rows):
    """Reusable chain (§23). Each box carries the recorded status of its gate."""
    st = {r["gate"]: r for r in rows}
    def s(g):
        r = st.get(g, {})
        return "not run" if r.get("status", "MISSING") == "MISSING" else ("waived" if r.get("waived") else str(r["status"]).lower().replace("_", " "))
    nodes = [("src", "Source", f"gate 0: {s('G0')}"), ("norm", "Normalized mathematics", f"gate 3: {s('G3')}"),
             ("lean", "Lean formalization", f"gate 4: {s('G4')}"), ("kern", "Lean kernel", f"gate 5: {s('G5')}"),
             ("chk", "Independent checker", f"gate 9: {s('G9')}"), ("comp", "Computational / adversarial tests", f"gates 8, 10: {s('G8')}, {s('G10')}"),
             ("evd", "Evidence graph", f"gate 11: {s('G11')}"), ("ver", "Verdict", "recorded separately (gate 13)")]
    t = [r"\begin{center}", r"\begin{tikzpicture}[node distance=7mm, box/.style={draw,rounded corners,align=center,minimum width=62mm,font=\small}, >=Stealth]"]
    prev = None
    for k, (i, a, b) in enumerate(nodes):
        pos = "" if prev is None else "below=of %s" % prev
        t.append(r"\node[box%s] (%s) {\textbf{%s}\\{\scriptsize %s}};" % ((", " + pos) if pos else "", i, esc(a), esc(b)))
        if prev:
            t.append(r"\draw[->] (%s) -- (%s);" % (prev, i))
        prev = i
    t.append(r"\node[box, right=14mm of kern] (ax) {\textbf{Axiom audit}\\{\scriptsize gate 6: %s}};" % esc(s("G6")))
    t.append(r"\draw[->] (kern) -- (ax);")
    t += [r"\end{tikzpicture}", r"\end{center}"]
    return "\n".join(t).replace("(kern)", "(kern)")


# ---------------------------------------------------------------- sections
_DISC_TITLES = {"informal_meaning": "What the object means informally", "lean_representation": "What Lean's type represents",
                "why_encoding_valid": "Why the encoding is valid", "where_preserved": "Where the property is preserved",
                "literal_or_transported": "Whether the equality is literal or transported through an equivalence",
                "assumptions": "Assumptions that make the translation valid"}


def bridge_state(d):
    """(verdict, state, reviewer). The tool never infers a verdict: no record -> NOT SET."""
    return fs.bridge_info(d.get("bridge"))


def bridge_tex(d):
    """Findings, Justification, the Section 31 disclosure, and the Verdict."""
    rec, R = d.get("bridge"), d["receipt"]
    out = []
    if rec:
        found = [(k, c) for k, c in rec["checks"].items() if c.get("finding") == "FOUND"]
        out += [r"\subsection*{Findings recorded by the reviewer}"]
        out += ([r"\begin{itemize}"] + [r"\item \textbf{%s} (%s): %s" % (esc(k.replace("_", " ")), "disclosed" if c["disclosed"] else "NOT disclosed", _inline(c["detail"])) for k, c in found] + [r"\end{itemize}"]
                if found else [esc("No difference was found by any of the required checks; each check records its basis in the semantic record.")])
        out += [r"\subsection*{Justification}", prose(rec["bridge_justification"], "justification")]
        if rec.get("bridge_verdict") == fs.WITH_DIFF:
            out += [r"\subsection*{Representational difference (Section 31)}", r"\begin{description}"]
            out += [r"\item[%s.] %s" % (esc(_DISC_TITLES[k]), _inline(rec["difference_disclosure"][k])) for k in fs.DISCLOSURE_KEYS] + [r"\end{description}"]
    elif d["gate7"] and d["gate7"] == d["gate4"]:
        out += [r"\subsection*{Justification}", esc("The Gate 7 re-audit recorded no notes of its own: it cites the Gate 4 comparison above as its evidence, so nothing further is shown here.")]
    else:
        out += [r"\subsection*{Justification}", prose(d["gate7"], "Gate 7 re-audit notes")]
    v, state, who = bridge_state(d)
    g = {r["gate"]: r for r in R["gates"]}
    ctx = f"Recorded context: Gate 4 recorded {g.get('G4', {}).get('result') or NR}; Gate 7 recorded {g.get('G7', {}).get('result') or NR}."
    if state == "NOT SET":
        line = r"\noindent\textbf{NOT SET.}\par " + esc("No reviewer-set bridge verdict is recorded for this run. The tool does not infer one. " + ctx)
    elif state == "PROPOSED":
        line = r"\noindent\textbf{%s} (\textbf{PROPOSED, not confirmed})\par " % esc(v) + esc(f"Proposed by {who}. It has not been confirmed by a human reviewer (Section 44: no model certifies its own proposal), so treat it as provisional. " + ctx)
    else:
        line = r"\noindent\textbf{%s}\par " % esc(v) + esc(f"Set by {who}. " + ctx)
    return "\n".join(out + [r"\subsection*{Verdict}", line])


_GATE_WORDS = {"G0": "source intake", "G1": "claim extraction", "G2": "assumption extraction", "G3": "semantic normalization",
               "G4": "formalization comparison", "G5": "Lean build", "G6": "axiom audit", "G7": "semantic re-audit",
               "G8": "adversarial / counterexample search", "G9": "independent check", "G10": "computational check",
               "G11": "evidence graph", "G12": "report", "ORDER": "canonical gate order"}
_STATUS_WORDS = {"MISSING": "was not recorded", "NO_VERDICT": "produced no verdict", "FAIL": "failed", "DISPUTED": "produced a disagreement",
                 "UNCLASSIFIED": "has a result that could not be classified", "PARTIAL": "is only partial", "DIAGNOSTIC": "is diagnostic only"}


def plain_limitations(R, events, brief=False, bridge=None, records=None, repro=None, reviewer=None):
    """(substantive, notes). Substantive = what limits the verification. Notes = record-keeping
    facts, kept out of the Trust Statement. No trailing periods (joinable); wording notes grouped."""
    sub_, notes = [], []
    for r in R["gates"]:
        if r["gate"] == "G13" or r["satisfied"]:
            continue
        w = _GATE_WORDS.get(r["gate"], r["action"].lower())
        base = (f"The {w} (Gate {r['gate'][1:]}) " if r["gate"].startswith("G") else f"The {w} ") + _STATUS_WORDS.get(r["status"], f"has status {r['status'].lower()}")
        if r["gate"] == "G9" and r.get("result") and not brief:
            base += ". Recorded result: " + r["result"].rstrip(".")
        if r["gate"] == "ORDER" and r["note"]:
            base = "The ledger records gates out of the canonical order (" + r["note"] + ")"
        if r.get("waived"):
            base += f". Waived: {r['waived'].rstrip('.')}"
        sub_.append(base)
    if "Classical.choice" in R["fields"]["AXIOM FOOTPRINT"]:
        sub_.append("The proof uses Classical.choice; it is a classical proof")
    rec = records or {}
    if rec.get("build") is None and repro is None:  # only claim a gap if the run has neither a build record nor a snapshot
        sub_.append("The repository, commit and project location were not recorded for this run, so the build cannot be reproduced exactly from this report")
    elif rec.get("build") is None:
        st = repro["state"]
        if st == "DIRTY":
            sub_.append(f"The project directory has {len(repro['git']['dirty_files'])} uncommitted or untracked files, so its commit does not by itself identify the source that was built")
        elif st == "NO_COMMIT":
            nf = len(repro["git"]["dirty_files"])
            sub_.append("The project directory is a git repository with no commit" + (f" and {nf} untracked files" if nf else "") + ", so nothing identifies the source that was built")
        elif st == "NOT_A_REPO":
            sub_.append("The project directory is not a git repository, so no commit identifies the source that was built")
        else:
            note = {True: ", and the commit matches the one named in the run's own notes", False: ", and the commit does NOT match the one named in the run's own notes", None: ""}[repro.get("revision_matches_expected")]
            sub_.append(f"The repository, commit and toolchain were captured after the run (on {repro['captured_utc'][:10]}), not recorded during it; they describe the project as it is now{note}")
        if repro.get("revision_matches_expected") is False and st != "DIRTY":
            sub_.append("The snapshot's commit differs from the commit named in the run's notes, so the run's build cannot be reproduced from it")
    if fr._last(events, "INDEPENDENT_CHECK") and rec.get("independent") is None:
        sub_.append("The checker used for the independent check is not identified in the record; only its result is")
    if bridge == "NOT SET":
        sub_.append("No reviewer-set semantic-bridge verdict is recorded")
    elif bridge == "PROPOSED":
        sub_.append("The semantic-bridge verdict is proposed by an automated assistant and awaits human confirmation")
    for eid, phrase in dangling_refs(events):
        sub_.append(f"The recorded result of {eid} refers to a log or receipt that is not part of this report (\u201c{phrase}\u201d), so that material cannot be inspected here")
    for it in (reviewer or {}).get("limitations", []):   # ADDED after the derived ones; never replaces or softens them
        st = (it.get("short") or it["statement"]).rstrip(".") if brief else it["statement"].rstrip(".")   # Trust Statement: the reviewer's own short form
        state = fl_.info(reviewer)[0]
        sub_.append(st + (" (proposed, not yet confirmed)" if brief and state == "PROPOSED" else "" if brief else f" ({fl_.tag(reviewer)})"))
    n_leg = sum(1 for e in events if not e.get("output_hash"))
    if n_leg:
        notes.append(f"{n_leg} of {len(events)} ledger events predate the input/output hash fields and carry none")
    groups = {}
    for e in events:
        if e["action"] in fe.COMPUTATIONAL_ACTIONS and not e["result"].startswith(fe.COMPUTATIONAL_RESULT_PREFIXES):
            groups.setdefault(e["result"].split()[0], []).append(e["event_id"])
    if groups:
        notes.append("Events " + "; ".join(f"{', '.join(ids)} ({tok})" for tok, ids in groups.items()) +
                     " used wording outside the Section 16 vocabulary; each is read as diagnostic evidence, not proof")
    return sub_, notes


_DANGLING = re.compile(r"\bsee\b[^.;()]{0,40}\b(?:receipt|log|transcript)\b[^.;()]{0,30}", re.I)


def dangling_refs(events):
    """(event id, phrase) for recorded results that point at a receipt/log/transcript. Such a pointer
    is unreadable from this package unless the material is included, so it must be a stated limitation."""
    out = []
    for e in events:
        m = _DANGLING.search(e["result"])
        if m:
            out.append((e["event_id"], m.group(0).strip()))
    return out


def tests_not_established(d):
    """Section 11 subsection answering §61 Q9. Tool-derived facts first (always true), then any reviewer-stated
    test-scope limits. The reviewer's items only add; they cannot remove the tool-derived lines."""
    rec, lr = d["records"], d.get("reviewer_limits")
    items = [esc("They are not proof of the claim (Sections 16 and 18). A search that finds no counterexample is diagnostic evidence only.")]
    if rec["compute"]:
        c = rec["compute"]
        items.append(esc(f"Only the tested domain was examined: {c['tested_domain']} ({c['cases']} cases). Categories not covered: {', '.join(c['categories_not_covered'])}."))
    else:
        items.append(esc("The tested domain is not recorded for these results, so this report cannot say which cases were examined."))
    for it in (lr or {}).get("limitations", []):
        if it["scope"] == "TESTS":
            items.append(_inline(it["statement"]) + " " + esc(f"({fl_.tag(lr)})"))
    return "\n".join([r"\subsection*{What these tests do not establish}", r"\begin{itemize}"] + [r"\item " + x for x in items] + [r"\end{itemize}"])


def status_lines(R):
    """§55-style status, from recorded gate results. The decision line is deliberately absent."""
    def word(g):
        x = next((r for r in R["gates"] if r["gate"] == g), None)
        if x is None or x["status"] == "MISSING":
            return "NOT RUN" + (f" (waived: {x['waived']})" if x and x.get("waived") else "")
        if x["status"] == "DIAGNOSTIC":
            return "NO COUNTEREXAMPLE FOUND IN TESTED DOMAIN (diagnostic, not proof)"
        return x["status"].replace("_", " ") + (" (waived)" if x.get("waived") else "")
    return [("FORMAL PROOF (build)", word("G5")), ("AXIOM AUDIT", word("G6")), ("SEMANTIC MATCH (Gate 4)", word("G4")),
            ("SEMANTIC RE-AUDIT (Gate 7)", word("G7")), ("INDEPENDENT CHECK", word("G9")), ("COUNTEREXAMPLE SEARCH", word("G8")),
            ("COMPUTATIONAL TEST", word("G10")), ("REPRODUCIBILITY", f"R{R['repro_level']} (ceiling supported by recorded evidence)")]


PS_BEGIN, PS_END = "%% PERMITTED-STATUS-BEGIN", "%% PERMITTED-STATUS-END"
VERDICT_WORDS = r"\b(PROMOTE|REPAIR|REJECT|RESEARCH|STOP)\b"


def permitted_block(R):
    """Option 3 (§61 Q12): state what the evidence PERMITS, never the decision. Verdict words
    may appear only between the markers; check_structure enforces that."""
    # G12 is this report: at build time its own ledger event cannot exist yet, so it must not count as a blocker.
    ps = fr.permitted_status(R, ignore={"G12"})
    g12_pending = next((g for g in R["gates"] if g["gate"] == "G12"), {}).get("status") == "MISSING"
    if ps["promote_supported"]:
        core = ("The recorded evidence satisfies the conditions for promotion (Section 53)"
                + (", assuming this report itself compiles cleanly, which is recorded afterwards as Gate 12" if g12_pending else "")
                + ". Whether to promote is the reviewer's decision, recorded after this report.")
    else:
        why = "; ".join(ps["blockers"]) or "a rule of Section 11 applies"
        core = f"Promotion (PROMOTE) is not supported by the recorded evidence, because: {why}."
        if ps["forced_verdict"]:
            core += f" The normalization result requires {ps['forced_verdict']} (Section 11)."
        core += " The reviewer may still record REPAIR, REJECT, RESEARCH or STOP."
    if ps["waived"]:
        core += " Waived explicitly: " + "; ".join(ps["waived"]) + "."
    return "\n".join([PS_BEGIN, r"\begin{quote}\textbf{Status the evidence permits.} " + esc(core) +
                      r" This is not a decision: the governance decision is recorded as a separate step after this report.\end{quote}", PS_END])


def _recorded_build_command(events):
    """The leading `lake ...` command in the LEAN_BUILD event's recorded method (e.g. 'lake exe cache get && lake build,
    Lean v4.28.0, ...'). Returns (command, event id) or (None, None). Taken from the ledger as recorded, not guessed."""
    e = fr._last(events, "LEAN_BUILD")
    m = re.match(r"\s*(lake\b[^,;]*)", e["method"]) if e else None
    return (m.group(1).strip(), e["event_id"]) if m else (None, None)


def repro_block(d):
    """Reproduction facts. Source order: a build record (captured DURING the run), else a reproduction snapshot
    (captured AFTER it, and labelled so), else NOT RECORDED. Clone/checkout commands appear only when the facts
    really identify the source (a clean tree); a dirty tree or a non-repo gets an explicit comment instead."""
    R, F, rec = d["receipt"], d["receipt"]["fields"], d["records"]
    br, ic, snap = rec["build"], rec["independent"], d.get("repro")
    src = br or snap
    git = (src or {}).get("git", {})
    env = (src or {}).get("environment", {})
    state = (snap or {}).get("state") if not br else "CLEAN_AT_COMMIT"
    rev = git.get("revision") or NR
    if snap and not br and state == "NO_COMMIT":
        rev = "none: the repository has no commit"
    elif snap and not br and git.get("is_repo"):
        rev += " (working tree clean)" if state == "CLEAN_AT_COMMIT" else f" (NOT CLEAN: {len(git['dirty_files'])} uncommitted or untracked files)"
    where = "Project directory when run" if br else "Project directory (now)"
    facts = [("Repository URL", git.get("remote_url") or NR), ("Commit", rev), (where, (src or {}).get("cwd") or NR),
             ("Lean toolchain file", env.get("lean_toolchain_file") or NR), ("Lean version", F["LEAN VERSION"]),
             ("Lake version", env.get("lake_version") or NR),
             ("Mathlib revision", F["MATHLIB VERSION"] + (f" (commit {env['mathlib_rev']})" if env.get("mathlib_rev") else "")),
             ("Checker", (f"nanoda {ic['checker'].get('nanoda_commit') or NR}, export format {ic.get('export_meta', {}).get('format', {}).get('version', NR)}" if ic else NR)),
             ("Expected build result", F["BUILD RESULT"])]
    if snap and not br:
        m = snap.get("revision_matches_expected")
        facts += [("How these were obtained", f"Captured {snap['captured_utc'][:10]} from the project as it is now; not recorded during the run"),
                  ("Matches the commit the run's notes name", {True: "yes (" + str(snap.get("expect_commit")) + ")", False: "NO (" + str(snap.get("expect_commit")) + ")", None: "not checked"}[m])]
    T = [r"\begin{tabular}{@{}p{0.27\textwidth}p{0.68\textwidth}@{}}", r"\toprule"]
    T += [r"%s & %s \\" % (esc(k), esc_break(v)) for k, v in facts] + [r"\bottomrule", r"\end{tabular}", ""]
    cmds = []
    if git.get("remote_url") and git.get("revision") and state == "CLEAN_AT_COMMIT" and (snap or {}).get("revision_matches_expected") is not False:
        cmds += [f"git clone {git['remote_url']}", "cd " + re.sub(r"\.git$", "", git["remote_url"].rstrip("/")).rsplit("/", 1)[-1], f"git checkout {git['revision']}"]
    elif snap and not br and state == "CLEAN_AT_COMMIT" and git.get("revision") and (snap.get("revision_matches_expected") is not False):
        cmds.append(f"# the commit is local only (no remote recorded): reproduce from a copy of the project repository, then: git checkout {git['revision']}")
    elif snap and not br and state == "DIRTY":
        cmds.append("# the project directory has uncommitted or untracked files: a commit does not identify the source that was built")
    elif snap and not br and state == "NO_COMMIT":
        cmds.append("# the project directory is a git repository with no commit: nothing identifies the source that was built")
    elif snap and not br and state == "NOT_A_REPO":
        cmds.append("# the project directory is not a git repository: no commit identifies the source that was built")
    elif snap and not br and (snap.get("revision_matches_expected") is False):
        cmds.append("# the snapshot's commit differs from the commit named in the run's notes: do not use it to reproduce this run")
    else:
        cmds.append("# repository location and commit were not recorded for this run (see table above)")
    build_cmd, build_ev = (br["command"], None) if br else _recorded_build_command(d["events"])
    cmds += ["cat lean-toolchain", "lake --version", "lean --version", build_cmd or "lake build"]
    for thm, _, _ in d["lean_statements"]:
        cmds.append(f"# in a Lean file importing the module:  #print axioms {thm}")
    if ic and ic.get("commands"):
        cmds += ["# independent check (paths are those of the recording machine):", ic["commands"]["export"], ic["commands"]["check"]]
    elif not ic:
        cmds.append("# independent-check commands were not recorded for this run")
    T += [code("\n".join(cmds))]
    if not br and not snap:
        T += [esc("This run predates structured build records, so the repository, commit and project location above are NOT RECORDED; "
                  "the commands are the generic sequence, not an exact recipe.")]
    elif not br:
        T += [esc("The repository facts were captured after the run and describe the project as it is now; they do not prove what the original run built."
                  + (f" The build command is the one recorded in {build_ev}." if build_ev else ""))]
    T += [esc(f"Reproducibility level supported by recorded evidence: R{R['repro_level']}. This tool did not re-run the build.")]
    return "\n".join(T)


def build_tex(d, author="Black Swan Labs FCVE", title=None):
    R, F, ev = d["receipt"], d["receipt"]["fields"], d["events"]
    rows = R["gates"]
    c0 = d["claims"][0] if d["claims"] else None
    lemmas = [c for c in (d["claims"] or [])[1:]]
    rec = d["records"]
    name = (c0 or {}).get("theorem_name") or R["claim_id"] or "Unnamed claim"
    date = ev[-1]["timestamp"][:10] if ev else NR
    bstate = bridge_state(d)[1]
    lims_plain, lims_notes = plain_limitations(R, ev, bridge=bstate, records=rec, repro=d.get("repro"), reviewer=d.get("reviewer_limits"))
    lims_brief = plain_limitations(R, ev, brief=True, bridge=bstate, records=rec, repro=d.get("repro"), reviewer=d.get("reviewer_limits"))[0]  # the Trust Statement stays restrained; detail is in Sections 10 and 12
    fp_list = [a.strip() for a in F["AXIOM FOOTPRINT"].split("[")[0].split(",") if a.strip() and a.strip() != NR and a.strip() != "none"]
    trust = fr.trust_statement(F, fp_list, fr._last(ev, "INDEPENDENT_CHECK"), fr._last(ev, "COMPUTATIONAL_CHECK"),
                               fr._last(ev, "ADVERSARIAL_COMPUTATIONAL_TEST", "CORRECTION_AND_RECHECK"), lims_brief, c0).replace("**Trust Statement.**", "").strip()
    fp_reported = F["AXIOM FOOTPRINT"]
    cite = (d.get("source_meta") or {}).get("source_citation")
    T = [PREAMBLE, r"\title{Formal Verification Report: %s%s}" % (esc(title or name), (r"\\[0.5em]{\large Source: " + esc(cite) + "}") if cite else ""),
         r"\author{%s \\ ledger through %s}" % (esc(author), esc(R["covers_through_event"])), r"\date{%s}" % esc(date),
         r"\begin{document}", r"\maketitle", "",
         r"\noindent\textbf{Trust Statement.} " + esc(trust), "",
         r"\begin{abstract}", esc(f"This report documents the formal verification of {name} ({R['claim_id'] or NR}) under the Formal Claim Verification Engine. "
             f"Recorded: build {F['BUILD RESULT']}; axiom footprint {F['AXIOM FOOTPRINT']}; independent check {fr.plain_independent_status(F['INDEPENDENT CHECK'])}. "
             "Computational testing is diagnostic and is not proof. Section 17 states the status the recorded evidence permits; the governance decision is recorded separately, after this report."), r"\end{abstract}", ""]
    S = lambda n: r"\section{%s}" % n
    T += [S("Mathematical Statement")]
    if c0:
        T += [r"\begin{sourceresult}{%s}" % esc(name), esc(c0["statement_verbatim"]), r"\end{sourceresult}", esc((f"Source: {cite}. " if cite else "") + "Source location: " + c0["source_location"] + "."), ""]
        if c0.get("referenced_numeric_facts"):
            T += [r"\noindent Facts the statement relies on:", r"\begin{itemize}"] + [r"\item " + esc(x) for x in c0["referenced_numeric_facts"]] + [r"\end{itemize}"]
    else:
        T += [missing("claims.json")]
    T += [S("Definitions and Assumptions")]
    defs = (c0 or {}).get("surrounding_definitions") or []
    T += ([r"\subsection*{Definitions}", r"\begin{itemize}"] + [r"\item " + esc(x) for x in defs] + [r"\end{itemize}"]) if defs else [missing("surrounding definitions")]
    A = d["assumptions"]
    if A:
        for key, lab in (("source_assumptions", "Source assumptions"), ("formalization_assumptions", "Formalization assumptions"), ("computational_assumptions", "Computational assumptions")):
            items = A.get(key, [])
            T += [r"\subsection*{%s}" % lab] + ([r"\begin{itemize}"] + [r"\item \textbf{%s} %s" % (esc(a.get("id", "")), esc(a.get("statement", ""))) for a in items] + [r"\end{itemize}"] if items else ["None recorded."])
    else:
        T += [missing("assumptions.json")]
    T += [S("Proof Outline")]
    ps = (c0 or {}).get("proof_structure")
    if ps:
        T += [r"\begin{enumerate}"] + [r"\item \textbf{%s.} %s" % (esc(k.replace("_", " ")), esc(v)) for k, v in ps.items()] + [r"\end{enumerate}"]
    else:
        T += [missing("the source's proof structure (claims.json has no proof_structure)")]
    for c in lemmas:
        T += [r"\begin{sourceresult}{%s}" % esc(c.get("theorem_name") or c["claim_id"]), esc(c["statement_verbatim"]), r"\end{sourceresult}"]
    T += [S("Proof Dependency Diagram"), diagram_dependency(d["claims"])]
    T += [S("Formalization"), esc("Lean identifiers below are cross-references; the mathematics is in the sections above (§29).")]
    if d["lean_statements"]:
        for thm, st, sig in d["lean_statements"]:
            T += [r"\subsection*{%s}" % esc(thm), code(st)]
    else:
        T += [missing("the Lean statement (no --lean-file/--theorem supplied)")]
    T += [S("Semantic Bridge")]
    T += [r"\subsection*{Informal Statement}", esc(c0["statement_verbatim"]) if c0 else missing("claim")]
    T += [r"\subsection*{Normalized Statement}", prose(d["normalized"], "normalized claim file")]
    T += [r"\subsection*{Lean Statement}", (code(d["lean_statements"][0][1]) if d["lean_statements"] else missing("Lean statement"))]
    T += [r"\subsection*{Differences}", prose(d["gate4"], "Gate 4 comparison")]
    if d["lean_statements"] and d["lean_statements"][0][2]:
        T += [esc("Syntactic signals in the Lean statement that a reviewer must address: " + ", ".join(f"{k} {v}" for k, v in d["lean_statements"][0][2].items()) + ".")]
    T += [bridge_tex(d)]
    br = rec["build"]
    T += [S("Lean Environment"), r"\begin{tabular}{@{}ll@{}}", r"\toprule"]
    for k in ("LEAN VERSION", "MATHLIB VERSION"):
        T += [r"%s & %s \\" % (esc(k.title()), esc(F[k]))]
    if br:
        T += [r"Toolchain file & %s \\" % esc(br["environment"]["lean_toolchain_file"]), r"Manifest sha256 & \texttt{%s} \\" % esc(br["environment"]["lake_manifest_sha256"][:16] + "..."),
              r"Git revision & \texttt{%s} \\" % esc((br["git"].get("revision") or NR)[:16])]
    T += [r"\bottomrule", r"\end{tabular}"]
    T += [S("Formal Verification"), esc(F["BUILD RESULT"].rstrip(".") + "."), esc(f"Source of this field: {R['sources']['BUILD RESULT']}.")]
    T += [S("Axiom Audit"), esc("Actual axiom footprint: " + F["AXIOM FOOTPRINT"].rstrip(".") + "."), esc(f"Source: {R['sources']['AXIOM FOOTPRINT']}.")]
    if "Classical.choice" in F["AXIOM FOOTPRINT"]:
        T += [esc("Classical.choice is present: the proof is classical, which is reported here and does not by itself fail the audit (§14).")]
    T += [S("Independent Check"), esc(F["INDEPENDENT CHECK"].rstrip(".") + "."), esc("Recording the checker and its version does not by itself establish independence (§17).")]
    T += [S("Computational / Adversarial Tests"), esc("Counterexample search: " + F["COUNTEREXAMPLE SEARCH"]), "", esc("Computational test: " + F["COMPUTATIONAL TEST"]), "",
          esc("Neither result is formal proof (§16, §18).")]
    if rec["compute"]:
        c = rec["compute"]
        T += ["", esc(f"Tested domain: {c['tested_domain']}; cases: {c['cases']}; categories not covered: {', '.join(c['categories_not_covered'])}.")]
    T += [tests_not_established(d)]
    T += [S("Verification Limitations"), r"\begin{longtable}{p{0.16\textwidth}p{0.78\textwidth}}", r"\toprule Item & Limitation \\ \midrule \endhead"]
    for i, l in enumerate(lims_plain or ["None recorded"], 1):
        T += [r"%d & %s. \\" % (i, esc(l))]
    if lims_notes:
        T += [r"\midrule \multicolumn{2}{l}{\textit{Record-keeping notes (these do not change what the verification shows)}} \\ \midrule"]
        for i, l in enumerate(lims_notes, max(len(lims_plain), 1) + 1):
            T += [r"%d & %s. \\" % (i, esc(l))]
    T += [r"\bottomrule", r"\end{longtable}"]
    T += [S("Verification Matrix"), r"\begin{longtable}{lllll}", r"\toprule Gate & Ledger action & Event & Status & Satisfied \\ \midrule \endhead"]
    for r in rows:
        if r["gate"] in ("G13",):
            continue  # the decision is Gate 13, issued after this report
        T += [r"%s & %s & %s & %s & %s \\" % (esc(r["gate"]), esc(r["action"].replace("_", " ").lower()), esc(r["event"] or "-"), esc(r["status"]),
                                              esc("yes" if r["satisfied"] else ("waived: " + r["waived"] if r.get("waived") else "no")))]
    T += [r"\bottomrule", r"\end{longtable}"]
    T += [S("Trust / Verification Chain"), diagram_trust(rows)]
    T += [S("Reproducibility Instructions"), repro_block(d)]
    T += [S("Correction Ledger")]
    bad = [n for n in d["graph"]["nodes"] if n["status"] in ("FAIL", "DISPUTED")]
    no_verdict = [n for n in d["graph"]["nodes"] if n["status"] == "NO_VERDICT"]
    if bad:
        T += [r"\begin{itemize}"] + [r"\item \textbf{%s} (%s): %s" % (esc(n["id"]), esc(n["produced_by_event"]), esc(n["result"])) for n in bad] + [r"\end{itemize}"]
    else:
        T += ["No failed or disputed gate results are recorded in the ledger."]
    if no_verdict:
        T += [esc("Gates that produced no verdict (" + ", ".join(n["id"] for n in no_verdict) + ") are not corrections; they are listed under Verification Limitations.")]
    T += [prose(d["correction_md"], "correction ledger file") if d["correction_md"] else "", ""]
    T += [S("Conclusion"), esc("The recorded evidence is summarized in the Trust Statement and the verification matrix above. Recorded failure is not a passed gate."),
          r"\begin{center}\begin{tabular}{@{}p{0.36\textwidth}p{0.58\textwidth}@{}}"] + [r"%s & %s \\" % (esc(k + ":"), esc(v)) for k, v in status_lines(R)] + [r"\end{tabular}\end{center}", permitted_block(R)]
    T += [r"\appendix", r"\section{Lean Source}", (code("\n\n".join(s for _, s, _ in d["lean_statements"])) if d["lean_statements"] else missing("Lean source"))]
    T += [r"\section{Tests}"]
    ct = [e for e in ev if e["action"] in fe.COMPUTATIONAL_ACTIONS]
    T += ([r"\begin{itemize}"] + [r"\item \textbf{%s} %s: %s" % (esc(e["event_id"]), esc(e["method"]), esc(e["result"])) for e in ct] + [r"\end{itemize}"]) if ct else [missing("computational tests")]
    T += [r"\section{Evidence Receipt}", r"\begin{longtable}{p{0.24\textwidth}p{0.70\textwidth}}", r"\toprule Field & Value \\ \midrule \endhead"]
    for k, v in F.items():
        if k == "FINAL DECISION":
            continue
        T += [r"%s & %s \\" % (esc(k), esc_break(v))]
    T += [r"\bottomrule", r"\end{longtable}", r"\end{document}", ""]
    return "\n".join(T)


def check_structure(tex):
    """Presentation invariants (§23, §33, §57). Returns problems."""
    p = []
    n_tikz = len(re.findall(r"\\begin\{tikzpicture\}", tex))
    if n_tikz != 2:
        p.append(f"exactly two diagrams required (§23); found {n_tikz}")
    if re.search(r"\\includegraphics|\\begin\{figure\}", tex):
        p.append("figure/image found; the report may contain only its two TikZ diagrams (§23)")
    secs = re.findall(r"^\\section\{([^}]*)\}", tex, re.M)
    body = secs[:len(SECTIONS)]
    if body != SECTIONS:
        p.append(f"sections differ from §33 order: {body}")
    if "\\textbf{Trust Statement.}" not in tex or tex.index("\\textbf{Trust Statement.}") > tex.index("\\begin{abstract}") or tex.count("Trust Statement.") != 1:
        p.append("Trust Statement must appear exactly once, before the abstract (§57.4)")
    if "longtable" not in tex or "Limitation" not in tex:
        p.append("limitations table missing (§57.7)")
    if "lake build" not in tex and "lake" not in tex:
        p.append("reproduction commands missing (§34)")
    for f in FORBIDDEN:
        if f in tex:
            p.append(f"forbidden phrase {f!r} (§27/§54)")
    if r"\section{Computational / Adversarial Tests}" in tex and "What these tests do not establish" not in tex.split(r"\section{Computational / Adversarial Tests}")[1].split(r"\section{Verification Limitations}")[0]:
        p.append("Section 11 must state what the tests do not establish (§61 Q9)")
    sb = tex.split(r"\section{Semantic Bridge}")[1].split(r"\section{Lean Environment}")[0] if r"\section{Semantic Bridge}" in tex else ""
    if sb:
        tail = sb.split(r"\subsection*{Verdict}")[-1]
        if not (any(v in tail for v in fs.BRIDGE_VERDICTS) or "NOT SET" in tail):
            p.append("Semantic Bridge verdict must be one of the four Section 30 verdicts, or explicitly NOT SET")
    if PS_BEGIN not in tex or PS_END not in tex or "This is not a decision" not in tex:
        p.append("the 'status the evidence permits' block (marked, and stating it is not a decision) is required (§61 Q12)")
    else:
        # Verdict words are checked in the regions THIS generator writes (front matter, Conclusion) outside the marked
        # block; run files quoted verbatim elsewhere may legitimately contain words like STOP.
        front = tex[:tex.index(r"\end{abstract}")]
        concl = tex.split(r"\section{Conclusion}")[1].split(r"\appendix")[0]
        concl = concl[:concl.index(PS_BEGIN)] + concl[concl.index(PS_END):] if PS_BEGIN in concl else concl
        if re.search(VERDICT_WORDS, front + concl):
            p.append("a governance verdict word appears outside the permitted-status block; the report must not state the decision (Gate 13 follows Gate 12)")
    if re.search(r"(governance|final)\s+decision\s*(is|:)\s*\W*(PROMOTE|REPAIR|REJECT|RESEARCH|STOP)", tex, re.I):
        p.append("the report asserts a governance decision; it may only state what the evidence permits")
    for pkg in ("amsmath", "amssymb", "amsthm", "mathtools", "booktabs", "graphicx", "tikz", "hyperref", "longtable", "array"):
        if pkg not in tex.split(r"\begin{document}")[0]:
            p.append(f"required package {pkg} missing (§32)")
    return p


# ---------------------------------------------------------------- compile (§51)
def _classify(log):
    c = {"fatal": [ln for ln in log.splitlines() if ln.startswith("!") or re.match(r"^error:", ln)],
         "unresolved_references": re.findall(r"Reference `([^']+)' on page \d+ undefined", log),
         "missing_citations": re.findall(r"Citation `([^']+)' on page \d+ undefined", log),
         "missing_figures": re.findall(r"(?:Unable to load picture or PDF file|File `[^']*' not found)[^\n]*", log),
         "missing_characters": re.findall(r"Missing character: [^\n]*", log),
         "layout": re.findall(r"(?:Over|Under)full \\[hv]box[^\n]*", log),
         "other_latex_warnings": [w for w in re.findall(r"LaTeX Warning: [^\n]*", log) if "undefined" not in w and "Rerun" not in w]}
    return c


def compile_report(tex_path, out_dir, only_cached=True):
    """Two passes (§51). Prefers pdflatex if installed; otherwise tectonic, and
    records honestly that the spec-named compiler was not used."""
    out_dir = os.path.abspath(out_dir)  # the compiler runs with cwd=out_dir: a relative path would nest
    os.makedirs(out_dir, exist_ok=True)
    tex_path = os.path.abspath(tex_path)
    if shutil.which("pdflatex"):
        comp, spec = "pdflatex", True
    elif shutil.which("tectonic"):
        comp, spec = "tectonic", False
    else:
        raise ReportError("no LaTeX compiler (pdflatex or tectonic) on PATH")
    ver = subprocess.run([comp, "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    passes, needed_network = [], False
    for n in (1, 2):
        if comp == "tectonic":
            cmd = ["tectonic", "--keep-logs", "-o", out_dir, tex_path] + (["--only-cached"] if only_cached else [])
            pr = subprocess.run(cmd, capture_output=True, text=True, cwd=out_dir)
            if pr.returncode != 0 and only_cached and "cached" in (pr.stderr + pr.stdout).lower():
                needed_network = True
                pr = subprocess.run(["tectonic", "--keep-logs", "-o", out_dir, tex_path], capture_output=True, text=True, cwd=out_dir)
        else:
            pr = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={out_dir}", tex_path], capture_output=True, text=True, cwd=out_dir)
        logf = os.path.join(out_dir, os.path.splitext(os.path.basename(tex_path))[0] + ".log")
        log = (open(logf, errors="replace").read() if os.path.exists(logf) else "") + "\n" + pr.stderr + "\n" + pr.stdout
        cl = _classify(log)
        if pr.returncode != 0 and not cl["fatal"]:
            cl["fatal"].append(f"compiler exit {pr.returncode}")
        passes.append({"pass": n, "exit_code": pr.returncode, **{k: v for k, v in cl.items()}})
    last = passes[-1]
    pdf = os.path.join(out_dir, os.path.splitext(os.path.basename(tex_path))[0] + ".pdf")
    ok = all(p["exit_code"] == 0 for p in passes) and os.path.exists(pdf)
    counts = {k: len(last[k]) for k in ("fatal", "unresolved_references", "missing_citations", "missing_figures", "missing_characters")}
    ok = ok and not any(counts.values())
    rec = {"compiler": comp, "compiler_version": ver, "spec_named_compiler_used": spec, "needed_network": needed_network,
           "passes": passes, "final_counts": counts, "layout_warnings": len(last["layout"]), "other_warnings": last["other_latex_warnings"],
           "pdf_sha256": _sha(pdf) if os.path.exists(pdf) else None, "verdict": "PASS" if ok else "FAIL"}
    return rec


def event_fields(comp, tex_rel, pdf_rel):
    c = comp["final_counts"]
    res = (f"{comp['verdict']} -- {c['fatal']} fatal errors, {c['unresolved_references']} unresolved references, {c['missing_citations']} missing citations, "
           f"{c['missing_figures']} missing figures, {c['missing_characters']} missing characters ({comp['compiler']}, 2 passes"
           + ("" if comp["spec_named_compiler_used"] else "; pdflatex named in §51 was NOT used") + f"; {comp['layout_warnings']} layout warnings)")
    return {"action": "REPORT_GENERATION", "method": f"fcve_report.build_tex + {comp['compiler']} ({comp['compiler_version']})", "result": res,
            "evidence": [tex_rel, pdf_rel]}
