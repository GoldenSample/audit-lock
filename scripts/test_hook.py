#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hook test harness: feeds tool calls to stdin the same way Claude Code does and compares the decision.

  python test_hook.py HOOK.py CASES.json [--env GUARD_CONFIG=path] [--python python3]

CASES.json = a list of {"name": "...", "tool_name": "Bash", "tool_input": {...}, "cwd": "...", "expect": "deny" | "allow"}
(the base set of bypasses: assets/bypass_cases.example.json). The hook is called with PYTHONIOENCODING=utf-8 and HOOK_SMOKE=1,
as in the field but without writes. The hook's own law is checked too: exit code 0, and the answer is empty or JSON.
Result: N of M passed; exit code 0 = everything passed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys


def run(hook: str, case: dict, env: dict, py: str) -> tuple[str, str, int]:
    payload = {"session_id": "test", "transcript_path": "", "cwd": case.get("cwd", os.getcwd()),
               "hook_event_name": "PreToolUse", "tool_name": case["tool_name"], "tool_input": case.get("tool_input", {})}
    p = subprocess.run([py, hook], input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60)
    out = p.stdout.decode("utf-8", "replace").strip()
    decision = "allow"
    reason = ""
    if out:
        try:
            j = json.loads(out)
            h = j.get("hookSpecificOutput") or {}
            if h.get("permissionDecision") == "deny" or j.get("decision") == "block":
                decision = "deny"
                reason = h.get("permissionDecisionReason") or j.get("reason") or ""
        except ValueError:
            decision = "broken"
            reason = "the answer is not JSON: " + out[:120]
    return decision, reason, p.returncode


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        return 2
    hook, cases_path = a[0], a[1]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", HOOK_SMOKE="1")
    py = sys.executable
    for i, x in enumerate(a):
        if x == "--env" and i + 1 < len(a):
            k, v = a[i + 1].split("=", 1)
            env[k] = v
        if x == "--python" and i + 1 < len(a):
            py = a[i + 1]
    with open(cases_path, encoding="utf-8") as f:
        cases = json.load(f)
    ok = 0
    for c in cases:
        dec, why, code = run(hook, c, env, py)
        good = dec == c["expect"] and code == 0
        ok += good
        mark = "ok  " if good else "FAIL"
        extra = "" if code == 0 else f" (exit code {code}: the hook's law is always 0)"
        print(f"{mark} {c['name']}: expected {c['expect']}, got {dec}{extra}" + (f" | {why[:110]}" if why and not good else ""))
    print(f"TOTAL: {ok} of {len(cases)} passed")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
