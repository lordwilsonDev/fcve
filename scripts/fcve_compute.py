"""FCVE computational backend (spec §16 Gate 8, §18 Gate 10, §19 abstraction).

A test script reports its outcome as ONE machine-readable line on stdout:

    FCVE_RESULT: {"outcome": "...", "tested_domain": "...", "cases": N, ...}

The verdict comes from that line plus the exit code, never from prose. Outcomes
use §16's vocabulary only. NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN is
diagnostic evidence, not proof, and must state the domain it covered.

Backends are interchangeable (§19): PythonBackend, or CommandBackend for any
interpreter (matlab -batch, octave, julia, ...). Only Python is exercised here.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

from fcve_lean import _sha

OUTCOMES = {"COUNTEREXAMPLE_FOUND", "NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN", "NOT_APPLICABLE"}  # §16
CATEGORIES = ["minimal", "boundary", "degenerate", "zero", "empty", "singleton", "equality",
              "extremal_parameters", "domain_transition", "pathological"]  # §16 list of 10
FORBIDDEN_WORDING = re.compile(r"PROVEN|PROVED|VERIFIED|SUPPORTED_AS_TRUE|COMPUTATIONALLY_SUPPORTED|\bTRUE\b", re.I)
RESULT_LINE = re.compile(r"^FCVE_RESULT:\s*(\{.*\})\s*$", re.M)


class BackendUnavailable(Exception):
    pass


class ComputeError(Exception):
    pass


def report(outcome, tested_domain="", cases=0, categories=(), details=None, seed=None):
    """Called by a test script to emit its result line."""
    print("FCVE_RESULT: " + json.dumps({"outcome": outcome, "tested_domain": tested_domain, "cases": cases,
                                        "categories": list(categories), "details": details or {}, "seed": seed}, sort_keys=True))


class CommandBackend:
    """Run a script with an interpreter command, e.g. ["python3"], ["octave", "--no-gui"],
    ["matlab", "-batch"] (the last two are untested here -- not installed)."""

    def __init__(self, name, argv, version_argv=None):
        self.name, self.argv, self.version_argv = name, list(argv), version_argv

    def available(self):
        return shutil.which(self.argv[0]) is not None

    def version(self):
        if not self.available():
            raise BackendUnavailable(f"{self.argv[0]} not on PATH")
        argv = self.version_argv or [self.argv[0], "--version"]
        p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        return (p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr).strip() else "unknown"

    def run(self, script, timeout):
        if not self.available():
            raise BackendUnavailable(f"{self.argv[0]} not on PATH")
        return subprocess.run(self.argv + [script], capture_output=True, text=True, timeout=timeout)


class PythonBackend(CommandBackend):
    def __init__(self):
        super().__init__("python", [sys.executable], [sys.executable, "--version"])

    def libs(self):
        out = {}
        for m in ("mpmath", "sympy", "numpy"):
            p = subprocess.run([sys.executable, "-c", f"import {m};print({m}.__version__)"], capture_output=True, text=True)
            if p.returncode == 0:
                out[m] = p.stdout.strip()
        return out


def parse_result(stdout):
    """Last FCVE_RESULT line -> dict, or raise ComputeError (fail closed)."""
    hits = RESULT_LINE.findall(stdout)
    if not hits:
        raise ComputeError("no FCVE_RESULT line in stdout (prose output is not accepted as a verdict)")
    try:
        r = json.loads(hits[-1])
    except json.JSONDecodeError as e:
        raise ComputeError(f"FCVE_RESULT is not valid JSON: {e}")
    if r.get("outcome") not in OUTCOMES:
        raise ComputeError(f"outcome {r.get('outcome')!r} not in §16 vocabulary {sorted(OUTCOMES)}")
    if r["outcome"] == "NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN":
        if not str(r.get("tested_domain", "")).strip():
            raise ComputeError("NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN must state tested_domain (a bounded claim)")
        if not isinstance(r.get("cases"), int) or r["cases"] <= 0:
            raise ComputeError("NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN needs cases > 0")
    bad = [c for c in r.get("categories", []) if c not in CATEGORIES]
    if bad:
        raise ComputeError(f"unknown categories {bad}; allowed: {CATEGORIES}")
    return r


def _one(script, backend, timeout, out_dir, label):
    t0 = time.monotonic()
    try:
        p = backend.run(script, timeout)
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        code, out, err = -1, (e.stdout or ""), (e.stderr or "") + f"\nTIMEOUT after {timeout}s"
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
    dur = round(time.monotonic() - t0, 2)
    logs = {}
    for n, text in (("stdout", out), ("stderr", err)):
        path = os.path.join(out_dir, f"{label}.{n}.log")
        with open(path, "w") as f:
            f.write(text)
        logs[n] = {"path": os.path.basename(path), "sha256": _sha(path)}
    result, error = None, None
    if code != 0:
        error = f"script exit code {code}"
    else:
        try:
            result = parse_result(out)
        except ComputeError as e:
            error = str(e)
    return {"script": os.path.basename(script), "script_sha256": _sha(script), "exit_code": code,
            "duration_s": dur, "logs": logs, "result": result, "error": error}


def run_check(script, out_dir, backend=None, gate=8, recheck_script=None, recheck_backend=None, timeout=600):
    """Run a test script; if it reports COUNTEREXAMPLE_FOUND, that is UNVERIFIED
    until an independent recheck agrees (§45; VCE-001's float64 false mismatch).
    Returns the record. Never raises on a script failure -- it records it."""
    if gate not in (8, 10):
        raise ValueError("gate must be 8 (adversarial) or 10 (computational check)")
    backend = backend or PythonBackend()
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(script))[0]
    main = _one(script, backend, timeout, out_dir, stem)
    rec = {"gate": gate, "action": "ADVERSARIAL_COMPUTATIONAL_TEST" if gate == 8 else "COMPUTATIONAL_CHECK",
           "evidence_class": "COUNTEREXAMPLE_ATTEMPT" if gate == 8 else "COMPUTATIONAL_TEST",
           "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "backend": {"name": backend.name, "version": backend.version(),
                       **({"libs": backend.libs()} if hasattr(backend, "libs") else {})},
           "run": main, "recheck": None, "text": "NOT PROOF: computational evidence only (§16)"}
    if main["error"]:
        rec["outcome"], rec["trust"] = "RUN_FAILED", "NONE"
    elif main["result"]["outcome"] == "COUNTEREXAMPLE_FOUND":
        if recheck_script:
            rb = recheck_backend or backend
            rc = _one(recheck_script, rb, timeout, out_dir, os.path.splitext(os.path.basename(recheck_script))[0] + ".recheck")
            rc["backend"] = {"name": rb.name, "version": rb.version()}
            rec["recheck"] = rc
            agree = rc["result"] is not None and rc["result"]["outcome"] == "COUNTEREXAMPLE_FOUND"
            rec["outcome"] = "COUNTEREXAMPLE_FOUND" if agree else "DISAGREEMENT"
            rec["trust"] = "CONFIRMED_BY_RECHECK" if agree else "DISPUTED"
        else:
            rec["outcome"], rec["trust"] = "COUNTEREXAMPLE_FOUND", "UNVERIFIED"
    else:
        rec["outcome"], rec["trust"] = main["result"]["outcome"], "SINGLE_RUN"
    res = main["result"] or {}
    rec["tested_domain"] = res.get("tested_domain", "")
    rec["cases"] = res.get("cases", 0)
    rec["categories_covered"] = sorted(res.get("categories", []))
    rec["categories_not_covered"] = [c for c in CATEGORIES if c not in res.get("categories", [])]
    with open(os.path.join(out_dir, f"{stem}-compute-record.json"), "w") as f:
        json.dump(rec, f, indent=2, sort_keys=True)
    return rec


def event_fields(rec, record_relpath):
    if rec["outcome"] == "RUN_FAILED":
        res = f"RUN_FAILED -- {rec['run']['error']}"
    else:
        res = rec["outcome"]
        if rec["outcome"] == "NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN":
            res += f" -- {rec['cases']} cases over: {rec['tested_domain']}; NOT PROOF"
        elif rec["trust"] == "UNVERIFIED":
            res += " (UNVERIFIED -- rerun independently before trusting; may be a test artifact)"
        elif rec["trust"] == "DISPUTED":
            res += " -- recheck did not reproduce; disagreement, see record (§45)"
    d = os.path.dirname(record_relpath)
    files = [record_relpath] + [os.path.join(d, v["path"]) for v in rec["run"]["logs"].values()]
    if rec["recheck"]:
        files += [os.path.join(d, v["path"]) for v in rec["recheck"]["logs"].values()]
    return {"action": rec["action"], "method": f"{rec['backend']['name']} {rec['backend']['version']}: {rec['run']['script']}",
            "result": res, "evidence": [f.lstrip("/") for f in files]}
