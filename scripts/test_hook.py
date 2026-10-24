#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Харнес тестов хука: подаёт вызовы инструментов в stdin так же, как это делает Claude Code, и сверяет решение.

  python test_hook.py ХУК.py КЕЙСЫ.json [--env GUARD_CONFIG=путь] [--python python3]

КЕЙСЫ.json = список {"name": "...", "tool_name": "Bash", "tool_input": {...}, "cwd": "...", "expect": "deny" | "allow"}
(базовый набор обходов: assets/bypass_cases.example.json). Хук зовётся с PYTHONIOENCODING=utf-8 и HOOK_SMOKE=1, как в бою
без записи. Проверяется и сам закон хука: код выхода 0, ответ пустой или JSON. Итог: прошло N из M, код 0 = всё прошло.
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
            reason = "ответ не JSON: " + out[:120]
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
        mark = "ок " if good else "БРАК"
        extra = "" if code == 0 else f" (код выхода {code}: закон хука = всегда 0)"
        print(f"{mark} {c['name']}: ждали {c['expect']}, вышло {dec}{extra}" + (f" | {why[:110]}" if why and not good else ""))
    print(f"ИТОГ: прошло {ok} из {len(cases)}")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
