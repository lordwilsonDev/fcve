"""FCVE Gate 9 -- independent check (spec §17).

Export a declaration's dependency closure with lean4export, then re-check it
with an external type checker (nanoda) that is not Lean's kernel. §17: "uses
nanoda" is NOT "independent verification completed". INDEPENDENTLY_CHECKED needs
ALL of: complete export, export/toolchain versions consistent, checker exit 0,
"Checked N declarations with no errors" with N>0, the target declaration
actually pretty-printed by the checker, and the checker's axiom set equal to the
Gate 6 footprint. Anything else is one of the other §17 results.

Guard aborts (time cap, disk floor) are NOT evidence about the proof: they map to
CHECKER_UNAVAILABLE ("no verdict"), never CHECKER_INCOMPATIBLE. A stall counts
only after the exporter has started emitting (before that it is loading Mathlib).
"""
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone

from fcve_lean import _sha

RESULTS = {"INDEPENDENTLY_CHECKED", "CHECKER_UNAVAILABLE", "CHECKER_INCOMPATIBLE",
           "CHECKER_DISAGREEMENT", "NOT_APPLICABLE"}  # §17
NANODA_EXPORT_RANGE = ((3, 1, 0), (3, 2, 0))  # supported >= 3.1.0, < 3.2.0 (per Phase 18 notes)
_CHECKED = re.compile(r"Checked (\d+) declarations with no errors")
_AXIOM = re.compile(r"^axiom\s+(\S+)", re.M)


def _ver(s):
    return tuple(int(x) for x in s.split(".")[:3])


def read_export_meta(path):
    with open(path) as f:
        first = f.readline()
    try:
        return json.loads(first)["meta"]
    except (json.JSONDecodeError, KeyError):
        return None


def parse_nanoda(stdout):
    """(declarations_checked or None, sorted axiom names, error_seen)"""
    m = _CHECKED.search(stdout)
    axioms = sorted({re.sub(r"\.\{.*$", "", a) for a in _AXIOM.findall(stdout)})
    return (int(m.group(1)) if m else None), axioms


def _free_gb(path):
    return shutil.disk_usage(path).free / 1e9


def run_export(cmd, cwd, out_path, err_path, tick_s=20, stall_ticks=15, max_s=900, min_free_gb=1.5):
    """Run the exporter under guards. Returns dict incl. abort_reason in
    {None, 'stalled-no-output', 'time-cap', 'disk-floor'}."""
    t0 = time.monotonic()
    abort, last, flat = None, -1, 0
    with open(out_path, "wb") as out, open(err_path, "wb") as err:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=out, stderr=err)
        while proc.poll() is None:
            time.sleep(tick_s)
            if proc.poll() is not None:
                break
            sz = os.path.getsize(out_path)
            flat = flat + 1 if sz == last else 0
            last = sz
            if _free_gb(os.path.dirname(out_path) or ".") < min_free_gb:
                abort = "disk-floor"
            elif time.monotonic() - t0 >= max_s:
                abort = "time-cap"
            elif sz > 0 and flat >= stall_ticks:  # only an emitting stream can stall
                abort = "stalled-no-output"
            if abort:
                proc.kill()
                break
        proc.wait()
    size = os.path.getsize(out_path)
    with open(out_path, "rb") as f:
        f.seek(max(size - 1, 0))
        last_byte = f.read(1) if size else b""
    return {"exit_code": proc.returncode, "seconds": round(time.monotonic() - t0, 1), "bytes": size,
            "complete": proc.returncode == 0 and abort is None and last_byte == b"\n" and size > 0,
            "abort_reason": abort}


def _result(outcome, reason, **extra):
    assert outcome in RESULTS
    return {"gate": "INDEPENDENT_CHECK", "result": outcome, "reason": reason,
            "note": "Recording the checker and version does not by itself establish independence (§17)", **extra}


def not_applicable(reason, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rec = _result("NOT_APPLICABLE", reason, started_utc=_now())
    _write(rec, out_dir)
    return rec


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(rec, out_dir):
    with open(os.path.join(out_dir, "independent-check-record.json"), "w") as f:
        json.dump(rec, f, indent=2, sort_keys=True)


def check(project, module, decl, out_dir, export_bin, nanoda_bin, permitted_axioms, *,
          export_cmd=None, nanoda_cmd=None, expected_lean_version=None, keep_export=False,
          tick_s=20, stall_ticks=15, max_s=900, min_free_gb=1.5, checker_timeout=3600):
    """Run Gate 9 for one declaration. `permitted_axioms` MUST be the Gate 6
    footprint for `decl`; nanoda is told any other axiom is a hard error, and the
    axiom set it reports must equal it exactly."""
    os.makedirs(out_dir, exist_ok=True)
    rec = {"started_utc": _now(), "project": os.path.abspath(project), "module": module, "declaration": decl,
           "gate6_footprint": sorted(permitted_axioms)}
    rec["checker"] = {"export_bin": export_bin, "nanoda_bin": nanoda_bin, "nanoda_commit": None}
    for b in (export_bin, nanoda_bin):
        if not (os.path.isfile(b) and os.access(b, os.X_OK)):
            r = _result("CHECKER_UNAVAILABLE", f"not executable: {b}", **{k: v for k, v in rec.items()})
            _write(r, out_dir)
            return r
    ndir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(nanoda_bin))))
    g = subprocess.run(["git", "-C", ndir, "rev-parse", "HEAD"], capture_output=True, text=True)
    rec["checker"]["nanoda_commit"] = g.stdout.strip() if g.returncode == 0 else None
    if expected_lean_version is None:
        tc = os.path.join(project, "lean-toolchain")
        if os.path.exists(tc):
            m = re.search(r"v?(\d+\.\d+\.\d+)", open(tc).read())
            expected_lean_version = m.group(1) if m else None
    rec["expected_lean_version"] = expected_lean_version
    ecmd = export_cmd or ["lake", "env", export_bin, module, "--", decl]
    rec["commands"] = {"export": f"cd {os.path.abspath(project)} && " + " ".join(ecmd) + f" > {decl}.export",
                       "check": " ".join(nanoda_cmd or [nanoda_bin]) + f" {decl}.nanoda-config.json"}

    export = os.path.join(out_dir, f"{decl}.export")
    exp = run_export(export_cmd or ["lake", "env", export_bin, module, "--", decl], project, export,
                     os.path.join(out_dir, f"{decl}.export.stderr.log"), tick_s, stall_ticks, max_s, min_free_gb)
    rec["export"] = exp
    try:
        if exp["abort_reason"] in ("time-cap", "disk-floor"):
            r = _result("CHECKER_UNAVAILABLE", f"export aborted by guard ({exp['abort_reason']}): no verdict on the proof", **rec)
        elif exp["abort_reason"] == "stalled-no-output":
            r = _result("CHECKER_INCOMPATIBLE", "exporter stalled after it began emitting (measured property of the exporter on this closure)", **rec)
        elif not exp["complete"]:
            r = _result("CHECKER_INCOMPATIBLE", f"export incomplete (exit {exp['exit_code']}, {exp['bytes']} bytes)", **rec)
        else:
            r = _verify(rec, export, out_dir, decl, nanoda_bin, nanoda_cmd, permitted_axioms, expected_lean_version, checker_timeout)
    finally:
        if os.path.exists(export):
            if os.path.getsize(export) > 0:
                rec["export"]["sha256"] = _sha(export)
            if not keep_export:
                os.remove(export)
                rec["export"]["deleted_after_check"] = True
    r["export"] = rec["export"]
    _write(r, out_dir)
    return r


def _verify(rec, export, out_dir, decl, nanoda_bin, nanoda_cmd, permitted, expected_lean, timeout):
    meta = read_export_meta(export)
    rec["export_meta"] = meta
    if meta is None:
        return _result("CHECKER_INCOMPATIBLE", "export has no readable meta line", **rec)
    fmt = meta.get("format", {}).get("version", "")
    lean_v = meta.get("lean", {}).get("version", "")
    lo, hi = NANODA_EXPORT_RANGE
    try:
        in_range = lo <= _ver(fmt) < hi
    except ValueError:
        in_range = False
    if not in_range:
        return _result("CHECKER_INCOMPATIBLE", f"export format {fmt!r} outside checker's supported range", **rec)
    if expected_lean and lean_v != expected_lean:
        return _result("CHECKER_INCOMPATIBLE", f"exporter's Lean {lean_v} != project toolchain {expected_lean}", **rec)
    cfg = {"export_file_path": os.path.abspath(export), "use_stdin": False, "permitted_axioms": sorted(permitted),
           "unpermitted_axiom_hard_error": True, "nat_extension": True, "string_extension": True,
           "print_success_message": True, "print_axioms": True, "pp_declars": [decl], "pp_to_stdout": True}
    cfg_path = os.path.join(out_dir, f"{decl}.nanoda-config.json")
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
    logs = {}
    try:
        p = subprocess.run((nanoda_cmd or [nanoda_bin]) + [cfg_path], capture_output=True, text=True, timeout=timeout)
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return _result("CHECKER_UNAVAILABLE", f"checker exceeded {timeout}s: no verdict", **rec)
    for n, t in (("stdout", out), ("stderr", err)):
        path = os.path.join(out_dir, f"{decl}.nanoda.{n}.log")
        with open(path, "w") as f:
            f.write(t)
        logs[n] = {"path": os.path.basename(path), "sha256": _sha(path)}
    n, axioms = parse_nanoda(out)
    rec.update(checker_exit_code=code, declarations_checked=n, checker_axioms=axioms, checker_logs=logs)
    if code != 0 or n is None:
        # kernel accepted this at Gate 5; an external checker rejecting it is a disagreement to investigate (§45),
        # not proof of a bad proof (the checker can have bugs -- §17)
        return _result("CHECKER_DISAGREEMENT", f"checker exit {code}, no clean 'Checked N declarations' line", **rec)
    if n <= 0:
        return _result("CHECKER_DISAGREEMENT", "checker reported zero declarations checked", **rec)
    if not re.search(rf"^(theorem|def|lemma|abbrev|instance)\s+{re.escape(decl)}\b", out, re.M):
        return _result("CHECKER_INCOMPATIBLE", "target declaration was not printed by the checker (export may not contain it)", **rec)
    if set(axioms) != set(permitted):
        return _result("CHECKER_DISAGREEMENT", f"checker axioms {axioms} != Gate 6 footprint {sorted(permitted)}", **rec)
    return _result("INDEPENDENTLY_CHECKED", f"{n} declarations re-checked, axioms match Gate 6", **rec)


def event_fields(rec, record_relpath):
    res = f"{rec['result']} -- {rec['reason']}"
    d = os.path.dirname(record_relpath)
    files = [record_relpath] + [os.path.join(d, v["path"]) for v in rec.get("checker_logs", {}).values()]
    c = rec.get("checker", {})
    method = (f"lean4export + nanoda {(c.get('nanoda_commit') or 'commit-unknown')[:12]} "
              f"(export format {rec.get('export_meta', {}).get('format', {}).get('version', 'n/a')})" if c else "n/a")
    return {"action": "INDEPENDENT_CHECK", "method": method, "result": res, "evidence": [f.lstrip("/") for f in files]}
