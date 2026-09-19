#!/usr/bin/env bash
# agent-check.sh -- is this repository actually usable by Hermes and FreeBuff (and Claude Code) on this machine?
#
# Read-only. It changes nothing: no agent configuration, no trust setting, no files. Same vocabulary as doctor.sh:
#   PASS / WARN (works but not fully wired) / FAIL (broken: fix printed) / UNRESOLVED (cannot be determined here -- never shown as PASS)
# Exit: 0 no FAIL and no UNRESOLVED | 1 a FAIL | 3 only UNRESOLVED
#
# What it checks, per agent: the instruction files it auto-loads; the skill discovery paths it uses; user-level copies (drift); and,
# for Hermes, its OWN injection scanner on our context files and its skills_guard verdict on our skill, its safety hooks, and whether this
# repo is trusted for repo-local skills. FreeBuff has no non-interactive mode, so whether it loaded the skill in a live session is UNRESOLVED
# unless a person confirms it (docs/AGENT-INTEGRATIONS.md says how).
set -u
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"
SKILLS=""; for d in "$FCVE_ROOT"/skills/*/; do [ -f "$d/SKILL.md" ] && SKILLS="$SKILLS $(basename "$d")"; done
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"; HERMES_SRC="$HOME/.hermes/hermes-agent"
echo "FCVE agent check -- $(date -u +%Y-%m-%dT%H:%M:%SZ) -- repo $FCVE_ROOT"; echo

# ---- repository side (agent-neutral) ----------------------------------------------------------------------------------
for F in AGENTS.md CLAUDE.md; do [ -f "$FCVE_ROOT/$F" ] && record PASS repo "$F" "present" || record FAIL repo "$F" "missing: agents that auto-load it will get no instructions"; done
for NAME in $SKILLS; do
  for P in .claude/skills .agents/skills; do
    [ -f "$FCVE_ROOT/$P/$NAME/SKILL.md" ] && record PASS repo "$P/$NAME" "resolves to SKILL.md ($( [ -L "$FCVE_ROOT/$P/$NAME" ] && echo symlink || echo directory ))" \
      || record FAIL repo "$P/$NAME" "missing or a broken symlink: agents that scan $P will not find the skill"
  done
  python3 - "$FCVE_ROOT/skills/$NAME" "$NAME" <<'PY' && record PASS skill "frontmatter $NAME" "name matches its directory, valid slug (<=64), description <=1024 chars (FreeBuff's limits, read from its binary)" || record FAIL skill "frontmatter $NAME" "SKILL.md frontmatter would be rejected (see message above)"
import re, sys
d, name = sys.argv[1], sys.argv[2]
t = open(d + "/SKILL.md").read(); m = re.match(r"---\n(.*?)\n---", t, re.S)
if not m: sys.exit(print("no frontmatter"))
fm = m.group(1); n = re.search(r"^name:\s*(.+)$", fm, re.M); ds = re.search(r"^description:\s*(.+)$", fm, re.M)
ok = bool(n and ds) and n.group(1).strip() == name and len(name) <= 64 and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(ds.group(1).strip()) <= 1024
if not ok: print("name=%r description_len=%s" % (n and n.group(1), ds and len(ds.group(1)))); sys.exit(1)
PY
done
MISSING=""; for PH in "TRUSTED" "BLOCKED" "TOOL_ERROR" "propose" "SKILL.md" "doctor.sh" "smoke-test.sh"; do grep -q "$PH" "$FCVE_ROOT/AGENTS.md" || MISSING="$MISSING $PH"; grep -q "$PH" "$FCVE_ROOT/CLAUDE.md" || MISSING="$MISSING CLAUDE:$PH"; done
[ -z "$MISSING" ] && record PASS repo "AGENTS.md / CLAUDE.md agree" "both carry the hard rules (TRUSTED ceiling, BLOCKED/TOOL_ERROR, propose/decide, skill, doctor, smoke test)" || record FAIL repo "AGENTS.md / CLAUDE.md agree" "missing key phrases:$MISSING"

drift() { diff -rq -x .DS_Store "$FCVE_ROOT/skills/$NAME" "$1" >/dev/null 2>&1; }   # uses $NAME (set by the caller loop)

# ---- Hermes -------------------------------------------------------------------------------------------------------------
echo
if have hermes; then
  record PASS hermes install "$(hermes --version 2>/dev/null | head -1)"
  PSR=$(cd "$FCVE_ROOT" && hermes prompt-size --json 2>/dev/null); PSN=$(cd /tmp && hermes prompt-size --json 2>/dev/null); SKL=$(hermes skills list 2>/dev/null)
  for NAME in $SKILLS; do
    D="$HOME/.hermes/skills/$NAME"
    if [ -d "$D" ]; then drift "$D" && record PASS hermes "user-level skill $NAME" "identical to the repo copy (loads without a trust step)" || record WARN hermes "user-level skill $NAME" "$D differs from the repo copy: scripts/install-agent-skills.sh --agent hermes"
    else record WARN hermes "user-level skill $NAME" "not installed: scripts/install-agent-skills.sh --agent hermes (or trust this repo so its .agents/skills loads)"; fi
    echo "$SKL" | grep -qi "$(echo "$NAME" | cut -c1-14)" && record PASS hermes "skill listed $NAME" "\`hermes skills list\` shows it" || record WARN hermes "skill listed $NAME" "\`hermes skills list\` does not show it"
    echo "$PSR" | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if any((x.get('name') if isinstance(x,dict) else x[0])=='$NAME' for x in d['skills_breakdown']) else 1)" 2>/dev/null \
      && record PASS hermes "skill in prompt index $NAME" "prompt-size skills_breakdown includes it" || record WARN hermes "skill in prompt index $NAME" "not in Hermes's skills index (install the user-level copy or trust the repo)"
  done
  # Deterministic proof of what Hermes loads (offline, no model): project-context bytes in the repo vs a neutral directory.
  CTXR=$(echo "$PSR" | python3 -c "import sys,json;d=json.load(sys.stdin);print([s[2] for s in d['sections'] if s[0].startswith('context')][0])" 2>/dev/null)
  CTXN=$(echo "$PSN" | python3 -c "import sys,json;d=json.load(sys.stdin);print([s[2] for s in d['sections'] if s[0].startswith('context')][0])" 2>/dev/null)
  if [ -n "$CTXR" ] && [ -n "$CTXN" ] && [ "$CTXR" -gt "$CTXN" ]; then record PASS hermes "loads repo context" "prompt-size: project context $CTXR B here vs $CTXN B elsewhere (Hermes loads ONE context type: AGENTS.md wins over CLAUDE.md)"
  else record FAIL hermes "loads repo context" "prompt-size shows no extra project context in the repo (here=${CTXR:-?} B, elsewhere=${CTXN:-?} B): Hermes is not loading AGENTS.md"; fi
  if [ -x "$HERMES_PY" ]; then
    RES=$(cd "$HERMES_SRC" && "$HERMES_PY" - "$FCVE_ROOT" <<'PY' 2>&1
import sys, pathlib
sys.path.insert(0, ".")
root = pathlib.Path(sys.argv[1])
from agent.prompt_builder import _scan_context_content
for f in ("AGENTS.md", "CLAUDE.md"):
    out = _scan_context_content((root / f).read_text(), f)
    print("CONTEXT", f, "BLOCKED" if out.startswith("[BLOCKED") else "clean")
from tools import skills_guard as sg
for d in sorted((root / "skills").iterdir()):
    if (d / "SKILL.md").is_file():
        r = sg.scan_skill(d, source="local"); print("SKILL", d.name, r.verdict, len(r.findings))
PY
)
    for F in AGENTS.md CLAUDE.md; do echo "$RES" | grep -q "^CONTEXT $F clean" && record PASS hermes "context scan $F" "Hermes's own injection scanner does not block it" || record FAIL hermes "context scan $F" "Hermes would BLOCK this file (its scanner flagged it): $(echo "$RES" | tail -2 | tr '\n' ' ' | cut -c1-160)"; done
    for NAME in $SKILLS; do
      V=$(echo "$RES" | sed -n "s/^SKILL $NAME \([a-z]*\).*/\1/p")
      case "$V" in safe) record PASS hermes "skills_guard $NAME" "safe (a 'dangerous' verdict would quarantine it in a trusted project)" ;;
        caution) record WARN hermes "skills_guard $NAME" "caution: loads, but review the findings" ;;
        dangerous) record FAIL hermes "skills_guard $NAME" "dangerous: Hermes would quarantine the skill in a trusted project" ;;
        *) record UNRESOLVED hermes "skills_guard $NAME" "could not run Hermes's scanner: $(echo "$RES" | tail -1 | cut -c1-120)" ;; esac
    done
    TR=$("$HERMES_PY" - "$FCVE_ROOT" <<'PY' 2>/dev/null
import sys, os
try:
    import yaml
    cfg = yaml.safe_load(open(os.path.expanduser("~/.hermes/config.yaml"))) or {}
    dirs = [os.path.realpath(os.path.expanduser(str(d))) for d in ((cfg.get("skills") or {}).get("trusted_project_dirs") or [])]
    print("TRUSTED" if os.path.realpath(sys.argv[1]) in dirs else "NOT_TRUSTED")
except Exception as e:
    print("UNKNOWN")
PY
)
    case "$TR" in TRUSTED) record PASS hermes "repo trusted" "repo-local skills (.agents/skills) load in a session opened here" ;;
      NOT_TRUSTED) record WARN hermes "repo trusted" "not trusted: repo-local skills will NOT load (the user-level copy still does). Trusting is your security decision: hermes skills trust $FCVE_ROOT" ;;
      *) record UNRESOLVED hermes "repo trusted" "could not read Hermes's trusted_project_dirs" ;; esac
  else record UNRESOLVED hermes "scanners" "Hermes's Python ($HERMES_PY) not found: cannot run its injection scanner or skills_guard"; fi
  H="$HOME/.agents/hooks/deny-dangerous.sh"
  if [ -x "$H" ] && have jq; then
    BLK=""; for C in "scripts/doctor.sh" "scripts/setup.sh --reuse-from ~/ico-collatz/targets" "scripts/smoke-test.sh" "scripts/audit.sh tests/fixtures/mini-lean-ok --module Mini --decl mini_add" "scripts/clean-room.sh --runs 1"; do
      O=$(printf '{"tool_name":"terminal","tool_input":{"command":"%s"}}' "$C" | bash "$H" hermes 2>&1); [ -z "$O" ] || BLK="$BLK [$C]"; done
    CTRL=$(printf '{"tool_name":"terminal","tool_input":{"command":"rm -rf /"}}' | bash "$H" hermes 2>&1)
    [ -z "$BLK" ] && record PASS hermes "safety hook allows FCVE" "deny-dangerous.sh (hermes mode) allows the documented commands" || record FAIL hermes "safety hook allows FCVE" "the global guard would block:$BLK"
    [ -n "$CTRL" ] && record PASS hermes "safety hook control" "the same hook DOES block \`rm -rf /\` (so the check above is not vacuous)" || record UNRESOLVED hermes "safety hook control" "the hook did not block a known-dangerous command: the allow result above proves nothing"
  else record UNRESOLVED hermes "safety hook" "$H or jq not available: cannot test the global command guard"; fi
else record WARN hermes install "Hermes is not installed here; nothing to check (skip if you do not use it)"; fi

# ---- FreeBuff -----------------------------------------------------------------------------------------------------------
echo
if have freebuff; then
  record PASS freebuff install "freebuff $(freebuff --version 2>/dev/null | head -1)"
  for NAME in $SKILLS; do
    for UD in "$HOME/.agents/skills/$NAME" "$HOME/.claude/skills/$NAME"; do
      if [ -d "$UD" ]; then drift "$UD" && record PASS freebuff "user-level $NAME in $(dirname "$UD" | sed "s#$HOME#~#")" "identical to the repo copy" || record WARN freebuff "user-level $NAME in $(dirname "$UD" | sed "s#$HOME#~#")" "differs from the repo copy: scripts/install-agent-skills.sh"
      else record WARN freebuff "user-level $NAME in $(dirname "$UD" | sed "s#$HOME#~#")" "not installed: scripts/install-agent-skills.sh"; fi
    done
  done
  record PASS freebuff "instruction files" "auto-reads knowledge.md / AGENTS.md / CLAUDE.md in a directory (read from its binary): both of ours are found"
  record PASS freebuff "project skills" "searches <project>/.agents/skills and <project>/.claude/skills (both present here; it follows symlinks: statSync().isDirectory())"
  record UNRESOLVED freebuff "loaded in a live session" "FreeBuff has no non-interactive mode, so this cannot be shown by a script. Confirm by hand: cd $FCVE_ROOT && freebuff (add --trust-agents to skip the trust prompt), then ask it to list its skills"
else record WARN freebuff install "FreeBuff is not installed here; nothing to check (skip if you do not use it)"; fi

echo; echo "summary: $N_PASS PASS, $N_WARN WARN, $N_FAIL FAIL, $N_UNRESOLVED UNRESOLVED"
if [ "$N_FAIL" -gt 0 ]; then echo "AGENT-CHECK: NOT READY ($N_FAIL FAIL)"; exit 1
elif [ "$N_UNRESOLVED" -gt 0 ]; then echo "AGENT-CHECK: OK BUT NOT FULLY RESOLVED ($N_UNRESOLVED UNRESOLVED): unknown is not PASS"; exit 3
else echo "AGENT-CHECK: READY ($N_WARN WARN)"; exit 0; fi
