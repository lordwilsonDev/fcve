"""FCVE Gate 5 -- Lean build wrapper (spec §13, §37, §38).

Runs `lake build` in a project, captures what §13 requires (command, exit code,
stdout, stderr, duration, environment, git state) into a build record plus raw
logs, and evaluates the required pass conditions. Stdlib only.

Not covered here: axiom audit (Gate 6) -- the text scan below is explicitly
insufficient on its own (§38); real unresolved-obligation detection is the
`sorryAx` check in the axiom audit.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone

DEFAULT_MIN_FREE_GB = 3.0  # handoff ground rule: never assume disk headroom
SORRY_RE = re.compile(r"\b(sorry|admit)\b")


class PreflightError(Exception):
    pass


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _run(cmd, cwd, timeout=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def preflight(project, min_free_gb=DEFAULT_MIN_FREE_GB):
    if not os.path.isdir(project):
        raise PreflightError(f"{project} is not a directory")
    for f in ("lean-toolchain", "lake-manifest.json"):
        if not os.path.exists(os.path.join(project, f)):
            raise PreflightError(f"{project}: missing {f} (§13 requires the project's own toolchain files)")
    if not (os.path.exists(os.path.join(project, "lakefile.lean")) or os.path.exists(os.path.join(project, "lakefile.toml"))):
        raise PreflightError(f"{project}: missing lakefile.*")
    free = shutil.disk_usage(project).free / 1e9
    if free < min_free_gb:
        raise PreflightError(f"only {free:.1f} GB free (< {min_free_gb} GB); refusing to build")
    if not shutil.which("lake"):
        raise PreflightError("lake not on PATH")
    return free


def strip_lean_comments(text):
    text = re.sub(r"/-.*?-/", "", text, flags=re.S)  # block comments (non-nested; good enough for a text scan)
    return re.sub(r"--[^\n]*", "", text)


def scan_sorry(project):
    """Text scan of project Lean sources (skips .lake/). Comments are stripped
    first so prose like 'no sorry' does not trip it. A clean scan is NOT proof
    (§38)."""
    hits = []
    for root, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in (".lake", ".git", "build")]
        for fn in files:
            if fn.endswith(".lean"):
                p = os.path.join(root, fn)
                with open(p, errors="replace") as f:
                    src = f.read()
                for i, line in enumerate(strip_lean_comments(src).splitlines(), 1):
                    if SORRY_RE.search(line):
                        hits.append({"file": os.path.relpath(p, project), "line": i, "text": line.strip()[:120]})
    return hits


def git_state(project):
    top = _run(["git", "rev-parse", "--show-toplevel"], project)
    if top.returncode != 0:
        return {"is_repo": False}
    head = _run(["git", "rev-parse", "--verify", "-q", "HEAD"], project)
    rev = head.stdout.strip() if head.returncode == 0 and head.stdout.strip() else None   # an empty repo has no commit; never report the word "HEAD"
    remote = _run(["git", "remote", "get-url", "origin"], project)
    remote_url = remote.stdout.strip() if remote.returncode == 0 and remote.stdout.strip() else None
    dirty = [l for l in _run(["git", "status", "--porcelain"], project).stdout.splitlines() if l.strip()]
    return {"is_repo": True, "revision": rev, "remote_url": remote_url, "dirty": bool(dirty), "dirty_files": dirty[:50]}


def environment(project):
    with open(os.path.join(project, "lean-toolchain")) as f:
        toolchain = f.read().strip()
    manifest_path = os.path.join(project, "lake-manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    pkgs = {p.get("name"): {"rev": p.get("rev"), "url": p.get("url")} for p in manifest.get("packages", [])}
    lean = _run(["lake", "env", "lean", "--version"], project)
    return {
        "lean_toolchain_file": toolchain,
        "lean_version_actual": (lean.stdout or lean.stderr).strip(),
        "lake_version": (_run(["lake", "--version"], project).stdout or "").strip() or None,
        "lake_manifest_sha256": _sha(manifest_path),
        "packages": pkgs,
        "mathlib_rev": pkgs.get("mathlib", {}).get("rev"),
    }


def run_build(project, out_dir, target=None, clean_room=False, timeout=7200,
              min_free_gb=DEFAULT_MIN_FREE_GB):
    """Run the build and write <out_dir>/build-record.json + raw logs.

    clean_room=True runs `lake clean` first (§37) -- this deletes the project's
    build artifacts, which for Mathlib-based projects means an expensive
    rebuild, so it is opt-in and recorded as its own build (`kind`).
    """
    free = preflight(project, min_free_gb)
    os.makedirs(out_dir, exist_ok=True)
    env = environment(project)
    git = git_state(project)
    scan = scan_sorry(project)
    if clean_room:
        clean = _run(["lake", "clean"], project, timeout=600)
        if clean.returncode != 0:
            raise PreflightError(f"lake clean failed: {clean.stderr.strip()[:200]}")
    cmd = ["lake", "build"] + ([target] if target else [])
    kind = "clean_room" if clean_room else "incremental"
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.monotonic()
    try:
        proc = _run(cmd, project, timeout=timeout)
        code, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        code, out, err = -1, (e.stdout or ""), (e.stderr or "") + f"\nTIMEOUT after {timeout}s"
    dur = round(time.monotonic() - t0, 2)
    stem = f"build-{kind}"
    logs = {}
    for name, text in (("stdout", out), ("stderr", err)):
        path = os.path.join(out_dir, f"{stem}.{name}.log")
        with open(path, "w") as f:
            f.write(text)
        logs[name] = {"path": os.path.basename(path), "sha256": _sha(path)}
    combined = out + "\n" + err
    sorry_warnings = len(re.findall(r"declaration uses [`'\"]?sorry", combined))
    conditions = {  # §13 "Required conditions"
        "exit_code_zero": code == 0,
        "no_sorry_admit_in_source": not scan,
        "no_sorry_warnings_in_log": sorry_warnings == 0,
        "no_hidden_local_modifications": git.get("is_repo", False) and not git.get("dirty", True),
    }
    rec = {
        "kind": kind, "command": " ".join(cmd), "cwd": os.path.abspath(project), "started_utc": started,
        "duration_s": dur, "exit_code": code, "free_disk_gb_before": round(free, 1),
        "logs": logs, "environment": env, "git": git,
        "sorry_text_hits": scan, "sorry_warning_count": sorry_warnings,
        "conditions": conditions,
        "text_scan_only": True,  # §38: real unresolved-obligation check lives in the axiom audit
        "verdict": "PASS" if all(conditions.values()) else "FAIL",
        "failed_conditions": [k for k, v in conditions.items() if not v],
    }
    with open(os.path.join(out_dir, f"{stem}-record.json"), "w") as f:
        json.dump(rec, f, indent=2, sort_keys=True)
    return rec


def snapshot(project, out_dir, expect_commit=None, name="repro-snapshot.json"):
    """Read-only capture of what is needed to reproduce a build: repository URL, commit, whether the working
    tree is clean, toolchain, Lake and manifest. It describes the project AS IT IS NOW, not as it was during the
    original run, and says so. expect_commit (a full hash or a prefix) is the commit the run's own notes name;
    the snapshot reports whether HEAD matches it. A dirty tree means the commit alone does not identify the source."""
    for f in ("lean-toolchain", "lake-manifest.json"):
        if not os.path.exists(os.path.join(project, f)):
            raise PreflightError(f"{project}: missing {f}; not a Lean/Lake project")
    git, env = git_state(project), environment(project)
    if not git.get("is_repo"):
        state = "NOT_A_REPO"
    elif not git.get("revision"):
        state = "NO_COMMIT"          # a repository with no commit identifies nothing, clean or not
    else:
        state = "DIRTY" if git["dirty"] else "CLEAN_AT_COMMIT"
    rec = {"kind": "repro_snapshot", "captured_utc": _now_iso(), "cwd": os.path.abspath(project), "state": state,
           "caveat": "Captured after the run, not during it. It describes the project as it is now; it does not prove what the original run built.",
           "git": git, "environment": env, "expect_commit": expect_commit,
           "revision_matches_expected": ((git.get("revision") or "").startswith(expect_commit) if expect_commit and git.get("is_repo") else None)}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name), "w") as f:
        json.dump(rec, f, indent=2, sort_keys=True)
    return rec


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def event_fields(rec, record_relpath):
    """kwargs for fcve_evidence.append_event(action='LEAN_BUILD', ...)."""
    res = (f"PASS -- exit {rec['exit_code']}, {rec['kind']}, {rec['duration_s']}s, {(rec['git'].get('revision') or 'no-commit')[:12]}"
           if rec["verdict"] == "PASS" else f"FAIL -- {', '.join(rec['failed_conditions'])}")
    return {"action": "LEAN_BUILD", "method": f"{rec['command']} ({rec['environment']['lean_version_actual']})",
            "result": res, "evidence": [record_relpath] + [f"{os.path.dirname(record_relpath)}/{v['path']}".lstrip("/")
                                                            for v in rec["logs"].values()]}
