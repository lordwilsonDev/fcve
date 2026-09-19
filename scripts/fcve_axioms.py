"""FCVE Gate 6 -- axiom audit (spec §14).

Runs `#print axioms <name>` for each theorem via a probe file kept OUTSIDE the
project (so the project's git tree stays clean), parses Lean's real output,
classifies every axiom, and applies the MVP rule:

  PROJECT_AXIOM -> FAIL      UNKNOWN -> FAIL      (sorryAx counts as UNKNOWN)
  CLASSICAL / EXTERNAL -> PASS but listed under `reported` (disclosure, not fail)

Classification is by name, against: a fixed core list, axioms declared in the
project's own sources, and an optional caller-supplied external allowlist.
"""
import json
import os
import re
import subprocess
import tempfile

from fcve_lean import strip_lean_comments, _sha

# Lean core axioms. Judgment call (spec §14 lists the classes but not the
# members): propext and Quot.sound are built into Lean's kernel/core;
# Classical.choice is the one that makes a proof classical. Earlier manual runs
# (VCE-001/002) labelled all three MATHLIB_STANDARD -- this module is finer.
KERNEL_STANDARD = {"propext", "Quot.sound"}
CLASSICAL = {"Classical.choice"}
# native_decide: Lean >= 4.2x emits a per-declaration axiom
# `<decl>._native.native_decide.ax_N_M`; older versions used Lean.ofReduceBool.
_TRUSTS_COMPILER = re.compile(r"(^|\.)native_decide\.ax_|^Lean\.(ofReduceBool|trustCompiler)$")
AXIOM_DECL = re.compile(r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+)*axiom\s+([^\s:({\[]+)", re.M)

_DEPENDS = re.compile(r"'([^']+)' depends on axioms: \[([^\]]*)\]", re.S)
_NONE = re.compile(r"'([^']+)' does not depend on any axioms")


def project_axioms(project):
    """Names declared with `axiom` in the project's own Lean sources."""
    found = set()
    for root, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in (".lake", ".git", "build")]
        for fn in files:
            if fn.endswith(".lean"):
                with open(os.path.join(root, fn), errors="replace") as f:
                    found.update(AXIOM_DECL.findall(strip_lean_comments(f.read())))
    return found


def classify(axiom, declared=frozenset(), external=frozenset()):
    if axiom in KERNEL_STANDARD:
        return "KERNEL_STANDARD"
    if axiom in CLASSICAL:
        return "CLASSICAL"
    if _TRUSTS_COMPILER.search(axiom):
        return "EXTERNAL"  # trusts the compiler, not just the kernel
    if axiom in declared or axiom.split(".")[-1] in {d.split(".")[-1] for d in declared}:
        return "PROJECT_AXIOM"
    if axiom in external:
        return "EXTERNAL"
    return "UNKNOWN"  # includes sorryAx, and any axiom nobody vouched for


def parse_print_axioms(text, names):
    """name -> list of axioms, or None if Lean did not answer for that name
    (unknown constant, elaboration error). Never guesses."""
    got = {n: None for n in names}
    for m in _NONE.finditer(text):
        if m.group(1) in got:
            got[m.group(1)] = []
    for m in _DEPENDS.finditer(text):
        if m.group(1) in got:
            got[m.group(1)] = [a.strip() for a in m.group(2).replace("\n", " ").split(",") if a.strip()]
    return got


def probe_source(module, names):
    return f"import {module}\n" + "".join(f"#print axioms {n}\n" for n in names)


def audit(project, module, names, out_dir, external=(), timeout=900):
    """Audit `names` (fully-qualified theorem names) exported by `module`.
    The project must already be built (Gate 5) so the module's oleans exist."""
    os.makedirs(out_dir, exist_ok=True)
    src = probe_source(module, names)
    with tempfile.TemporaryDirectory() as tmp:
        probe = os.path.join(tmp, "AxiomProbe.lean")
        with open(probe, "w") as f:
            f.write(src)
        proc = subprocess.run(["lake", "env", "lean", probe], cwd=project, capture_output=True,
                              text=True, timeout=timeout)
    out = proc.stdout + proc.stderr
    log = os.path.join(out_dir, "axiom-probe.log")
    with open(log, "w") as f:
        f.write(src + "\n--- output ---\n" + out)
    declared = project_axioms(project)
    parsed = parse_print_axioms(out, names)
    theorems, fail, reported = {}, [], {}
    for n in names:
        axs = parsed[n]
        if axs is None:
            theorems[n] = {"axioms": None, "classes": None, "status": "FAIL", "reason": "Lean gave no axiom answer (unknown name or error)"}
            fail.append(f"{n}: no answer from Lean")
            continue
        classes = {a: classify(a, declared, set(external)) for a in axs}
        bad = sorted(a for a, c in classes.items() if c in ("PROJECT_AXIOM", "UNKNOWN"))
        rep = sorted(a for a, c in classes.items() if c in ("CLASSICAL", "EXTERNAL"))
        theorems[n] = {"axioms": axs, "classes": classes, "status": "FAIL" if bad else "PASS",
                       "uses_sorry": "sorryAx" in axs, "trusts_compiler": any(_TRUSTS_COMPILER.search(a) for a in axs)}
        if bad:
            fail.append(f"{n}: {', '.join(bad)}")
        if rep:
            reported[n] = rep
    rec = {
        "gate": "AXIOM_AUDIT", "module": module, "names": list(names), "lean_exit_code": proc.returncode,
        "probe_log": {"path": os.path.basename(log), "sha256": _sha(log)},
        "project_declared_axioms": sorted(declared), "external_allowlist": sorted(external),
        "theorems": theorems, "reported": reported, "failures": fail,
        "verdict": "FAIL" if fail else "PASS",
        "footprint": sorted({a for t in theorems.values() for a in (t["axioms"] or [])}),
    }
    with open(os.path.join(out_dir, "axiom-audit-record.json"), "w") as f:
        json.dump(rec, f, indent=2, sort_keys=True)
    return rec


def event_fields(rec, record_relpath):
    fp = ", ".join(rec["footprint"]) or "none"
    res = (f"PASS -- footprint: {fp}" + (f"; REPORTED: {json.dumps(rec['reported'], sort_keys=True)}" if rec["reported"] else "")
           if rec["verdict"] == "PASS" else f"FAIL -- {'; '.join(rec['failures'])}")
    d = os.path.dirname(record_relpath)
    return {"action": "AXIOM_AUDIT", "method": "#print axioms " + " ".join(rec["names"]), "result": res,
            "evidence": [record_relpath, os.path.join(d, rec["probe_log"]["path"]).lstrip("/")]}
