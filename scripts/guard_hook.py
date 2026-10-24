#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Хук PreToolUse на боковые двери: продукт попадает в защищённое место только законным путём (например release_gate.py).

Настройка: JSON рядом с хуком (guard_config.json) или путь в переменной GUARD_CONFIG. Поля (пример assets/guard_config.example.json):
  name           имя замка в тексте отказа
  protected      защищённые места: префиксы путей (U:/, dist/, /mnt/flash/) или регулярки с префиксом re:
  protected_ext  если задано, замок только для этих расширений (.cmo, .mp4); пусто = любые файлы
  allowed        регулярки законного пути (сегмент команды, где он стоит, не проверяется)
  deny_tools     регулярки имён инструментов, запрещённых всегда (загрузка через браузер, терминал приложения)
  state_dirs     папки состояния замков: запись туда инструментами агента запрещена всегда
  help           что делать вместо: путь один, что прочитать, кто снимает
  fail_closed    true = ошибка разбора на записи = отказ (по умолчанию true)

Законы хука: всегда код 0, отказ = JSON permissionDecision deny; чтение (cat, grep, ls, Get-Content) не производство;
команда режется на сегменты по ; && || | и переводу строки, cd внутри команды меняет папку для следующих сегментов;
закодированные команды (-EncodedCommand, base64 | sh) с защищённым местом в контексте запрещены: их нельзя разобрать.
HOOK_SMOKE=1: ничего не пишет в журнал. Регулярка хука = страховка; замок = единственная дверь выпуска.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

WRITE_VERB = re.compile(
    r"(^|[\s;&|(])(cp|mv|install|rsync|scp|dd|tee|copy|move|xcopy|robocopy|ren|rename|mklink|"
    r"copy-item|move-item|rename-item|set-content|add-content|out-file|new-item|tar|7z|zip|unzip|expand-archive)\b"
    r"|\bshutil\.(copy\w*|move)|\bwrite_(bytes|text)\(|\bopen\([^)]*['\"][wax]b?\+?['\"]|\.save\(|"
    r"\bwritefile(sync)?\(|\bcopyfile(sync)?\(|\bfs\.(write|copy|rename)|\bos\.(replace|rename)\(|\[io\.file\]::(write|copy)",
    re.I)
READ_ONLY = re.compile(r"^\s*(cat|type|less|more|head|tail|grep|rg|findstr|ls|dir|get-childitem|get-content|test-path|"
                       r"sha256sum|certutil|get-filehash|stat|file|wc|diff|fc)\b", re.I)
ENCODED = re.compile(r"-e(nc(odedcommand)?)?\s+[a-z0-9+/=]{16,}|base64\s+(-d|--decode)[^|]*\|\s*(sh|bash|python|iex)|"
                     r"frombase64string", re.I)
REDIRECT = re.compile(r"(?<![0-9&])>>?\s*[\"']?([^\s\"';|&>]+)")
SEG = re.compile(r"&&|\|\||[;\n|]")
CD = re.compile(r"^\s*(cd|set-location|pushd)\s+[\"']?([^\"']+?)[\"']?\s*$", re.I)
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}


def norm(s: str) -> str:
    s = str(s).replace("\\\\?\\", "").replace("\\", "/").lower()
    return re.sub(r"/{2,}", "/", s)


def load_cfg() -> dict:
    p = os.environ.get("GUARD_CONFIG") or str(Path(__file__).with_name("guard_config.json"))
    with open(p, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("name", "ЗАМОК")
    cfg.setdefault("fail_closed", True)
    return cfg


def place_hits(text: str, cfg: dict) -> bool:
    t = norm(text)
    for p in cfg.get("protected", []):
        if p.startswith("re:"):
            if re.search(p[3:], t, re.I):
                return True
        elif norm(p) in t:
            return True
    return False


def ext_ok(text: str, cfg: dict) -> bool:
    exts = [e.lower() for e in cfg.get("protected_ext", [])]
    if not exts:
        return True
    t = norm(text)
    return any(e in t for e in exts) or bool(re.search(r"(^|\s)(-r|-a|/e|/s|-recurse)\b|\*", t))  # папкой или маской


def in_state(text: str, cfg: dict) -> bool:
    t = norm(text)
    return any(norm(d) in t for d in cfg.get("state_dirs", []))


def deny(cfg: dict, why: str) -> None:
    msg = f"{cfg['name']}: {why}. {cfg.get('help', '')}".strip()
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": msg}}, ensure_ascii=False))
    jr = cfg.get("journal")
    if jr and not os.environ.get("HOOK_SMOKE"):
        try:
            with open(jr, "a", encoding="utf-8") as f:
                f.write(json.dumps({"why": why}, ensure_ascii=False) + "\n")
        except OSError:
            pass


def check_shell(cmd: str, cwd: str, cfg: dict) -> str | None:
    allowed = [re.compile(x, re.I) for x in cfg.get("allowed", [])]
    if ENCODED.search(cmd) and cfg.get("protected"):
        return "закодированную команду нельзя разобрать, а замок стоит на защищённых местах"
    here = cwd
    for seg in SEG.split(cmd):
        s = seg.strip()
        if not s:
            continue
        m = CD.match(s)
        if m:
            here = m.group(2)
            continue
        if any(rx.search(s) for rx in allowed):
            continue
        targets = REDIRECT.findall(s)
        rel = lambda t: not re.match(r"^([a-z]:|/|~|\\\\)", t, re.I)  # noqa: E731
        if any(in_state(t, cfg) for t in targets) or (in_state(s, cfg) and WRITE_VERB.search(s)):
            return "запись в состояние замка запрещена"
        redir_bad = any((place_hits(t, cfg) or (rel(t) and place_hits(here.rstrip('/\\') + '/', cfg))) and ext_ok(t, cfg) for t in targets)
        if READ_ONLY.match(s) or not WRITE_VERB.search(s):
            if redir_bad:                     # читать можно, перенаправить вывод в защищённое место нельзя
                return "вывод команды пишется в защищённое место: " + s[:160]
            continue
        if (place_hits(s, cfg) or place_hits(here.rstrip('/\\') + '/', cfg) or redir_bad) and ext_ok(s, cfg):
            return "запись или копия в защищённое место мимо законного пути: " + s[:160]
    return None


def main() -> None:
    cfg = None
    data = {}
    try:
        cfg = load_cfg()
        data = json.load(sys.stdin)
        tool = str(data.get("tool_name") or "")
        ti = data.get("tool_input") or {}
        for rx in cfg.get("deny_tools", []):
            if re.fullmatch(rx, tool):
                deny(cfg, f"инструмент {tool} закрыт этим замком")
                return
        if tool in WRITE_TOOLS:
            fp = str(ti.get("file_path") or ti.get("notebook_path") or "")
            if in_state(fp, cfg):
                deny(cfg, "запись в состояние замка запрещена")
            elif place_hits(fp, cfg) and ext_ok(fp, cfg):
                deny(cfg, f"запись файла в защищённое место мимо законного пути: {fp}")
            return
        if tool in SHELL_TOOLS:
            why = check_shell(str(ti.get("command") or ""), str(data.get("cwd") or ""), cfg)
            if why:
                deny(cfg, why)
    except Exception as e:  # noqa: BLE001
        tool = str((data or {}).get("tool_name") or "")
        if cfg and cfg.get("fail_closed") and (tool in WRITE_TOOLS or tool in SHELL_TOOLS):
            deny(cfg, f"ошибка замка ({type(e).__name__}): на записи ошибка = отказ")


if __name__ == "__main__":
    try:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
        main()
    finally:
        sys.exit(0)
