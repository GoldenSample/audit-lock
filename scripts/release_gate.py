#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Единственная дверь выпуска: продукт уходит к потребителю только с вердиктом, привязанным к sha256 этого файла.

Вердикт лежит рядом с продуктом: <файл>.verdict.json. Пишет его судья (или его обёртка) командой stamp, не исполнитель.
  python release_gate.py stamp   ФАЙЛ --verdict PASS --judge ИМЯ --maker ИМЯ [--report ОТЧЁТ] [--judge-error ТЕКСТ] [--open "пункт" ...]
  python release_gate.py check   ФАЙЛ [--allow PASS] [--max-age-h 72] [--owner-quote]     сухая проверка, код 0 = выпуск пройдёт
  python release_gate.py release ФАЙЛ --dest ПАПКА [--allow PASS] [--max-age-h 72] [--owner-quote] [--journal releases.jsonl]
  python release_gate.py find    SHA256 [--journal releases.jsonl]                          какой выпуск у этого содержимого

Проверки выпуска: вердикт есть; sha256 вердикта = sha256 файла сейчас (файл не менялся после суда); судья отработал
(нет judge_error); судья не тот, кто делал; вердикт из разрешённого набора; вердикт не старше --max-age-h;
с --owner-quote поле owner_quote должно содержать цитату в «», которую owner_words.py said находит в репликах владельца
не раньше времени вердикта. Копия пишется во временное имя, сверяется по sha256 и только потом получает своё имя.
Каждый выпуск и каждый отказ пишется строкой в журнал.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUOTE = re.compile(r"«([^«»]{2,})»|“([^“”]{2,})”")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def vpath(p: Path) -> Path:
    return p.with_name(p.name + ".verdict.json")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def journal(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def stamp(a) -> int:
    p = Path(a.file)
    v = {"file": p.name, "sha256": sha256(p), "verdict": a.verdict, "judge": a.judge, "maker": a.maker, "ts": now(),
         "report": a.report or "", "judge_error": a.judge_error or "", "open": a.open or [], "owner_quote": a.owner_quote or ""}
    vpath(p).write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"вердикт {a.verdict} для {p.name} ({v['sha256'][:12]}) записан: {vpath(p)}")
    return 0


def problems(p: Path, a) -> tuple[list[str], dict]:
    errs: list[str] = []
    if not p.is_file():
        return [f"нет файла {p}"], {}
    vp = vpath(p)
    if not vp.is_file():
        return [f"нет вердикта {vp.name}: сначала суд (судья пишет вердикт командой stamp)"], {}
    try:
        v = json.loads(vp.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"вердикт не читается: {e}"], {}
    cur = sha256(p)
    if v.get("sha256") != cur:
        errs.append("вердикт относится к другому содержимому: файл менялся после суда, нужен новый суд")
    if v.get("judge_error"):
        errs.append(f"судья не отработал ({v['judge_error']}): выпуск только после полного суда")
    if not v.get("judge"):
        errs.append("в вердикте не указан судья")
    elif v.get("maker") and v["judge"].strip().lower() == v["maker"].strip().lower():
        errs.append("судья и исполнитель одно лицо: делающий себя не оценивает")
    allow = {x.strip() for x in a.allow.split(",") if x.strip()}
    if v.get("verdict") not in allow:
        opened = v.get("open") or []
        errs.append(f"вердикт «{v.get('verdict')}» не из разрешённых {sorted(allow)}" +
                    (": открыто " + "; ".join(map(str, opened[:10])) if opened else ""))
    try:
        age_h = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(v["ts"])).total_seconds() / 3600
        if a.max_age_h and age_h > a.max_age_h:
            errs.append(f"вердикт старше {a.max_age_h} ч ({age_h:.0f} ч): суд заново")
    except (KeyError, ValueError, TypeError):
        errs.append("в вердикте нет времени суда")
    if a.owner_quote:
        qs = [x or y for x, y in QUOTE.findall(str(v.get("owner_quote") or ""))]
        if not qs:
            errs.append("нет подписи владельца цитатой в «» (поле owner_quote); голое да или true не подпись")
        else:
            sys.path.insert(0, str(HERE))
            import owner_words  # noqa: E402
            root = Path(a.root).expanduser()
            for q in qs:
                if not owner_words.said(q, root, v.get("ts")):
                    errs.append(f"владелец не говорил «{q[:80]}» после суда (owner_words.py said)")
    return errs, v


def check(a) -> int:
    errs, v = problems(Path(a.file), a)
    if errs:
        print("СТОП:\n  " + "\n  ".join(errs))
        return 1
    print(f"выпуск пройдёт: {a.file}, вердикт {v['verdict']}, судья {v['judge']}")
    return 0


def release(a) -> int:
    p = Path(a.file)
    jr = Path(a.journal) if a.journal else HERE / "releases.jsonl"
    errs, v = problems(p, a)
    if errs:
        journal(jr, {"ts": now(), "file": str(p), "result": "отказ", "why": errs})
        print("СТОП:\n  " + "\n  ".join(errs))
        return 1
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    final = dest / p.name
    tmp = dest / (p.name + ".partial")
    shutil.copy2(p, tmp)
    same = sha256(tmp) == v["sha256"]
    if not same:
        tmp.unlink(missing_ok=True)
        journal(jr, {"ts": now(), "file": str(p), "dest": str(final), "result": "отказ", "why": ["копия не совпала по sha256"]})
        print("СТОП: копия не совпала по sha256, выпуск отменён")
        return 1
    os.replace(tmp, final)
    journal(jr, {"ts": now(), "file": str(p), "dest": str(final), "sha256": v["sha256"], "verdict": v["verdict"],
                 "judge": v["judge"], "report": v.get("report", ""), "result": "выпущено", "verified": True})
    print(f"выпущено: {final} ({v['verdict']}), копия сверена по sha256")
    return 0


def find(a) -> int:
    jr = Path(a.journal) if a.journal else HERE / "releases.jsonl"
    hits = []
    if jr.is_file():
        for line in jr.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("sha256", "").startswith(a.sha.lower()):
                hits.append(r)
    for r in hits:
        print(r["ts"], r["result"], r.get("dest"), r.get("verdict"))
    if not hits:
        print("выпусков с этим содержимым нет")
    return 0 if hits else 1


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stamp")
    s.add_argument("file")
    s.add_argument("--verdict", required=True)
    s.add_argument("--judge", required=True)
    s.add_argument("--maker", required=True)
    s.add_argument("--report")
    s.add_argument("--judge-error")
    s.add_argument("--open", nargs="*")
    s.add_argument("--owner-quote", help="подпись владельца с цитатой в «»")
    for name in ("check", "release"):
        x = sub.add_parser(name)
        x.add_argument("file")
        x.add_argument("--allow", default="PASS")
        x.add_argument("--max-age-h", type=float, default=0)
        x.add_argument("--owner-quote", action="store_true", help="требовать подпись владельца цитатой")
        x.add_argument("--root", default="~/.claude/projects", help="стенограммы для проверки цитаты")
        if name == "release":
            x.add_argument("--dest", required=True)
            x.add_argument("--journal")
    f = sub.add_parser("find")
    f.add_argument("sha")
    f.add_argument("--journal")
    a = ap.parse_args()
    return {"stamp": stamp, "check": check, "release": release, "find": find}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
