#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка карты контура BRANCH_MAP.json (схема: references/audit-method.md, раздел 4).

  python map_check.py BRANCH_MAP.json [--strict]

Печатает: сколько станций, массивов и связей; станции вне замков (locks пуст); станции broken и dead; массивы, которые никто
не читает или которые не идут в продукт; ошибки: повтор id, связь на несуществующий узел, неизвестный статус, станция без опоры.
Код 0 = ошибок нет (станции вне замков не ошибка, это находка аудита); с --strict станция вне замков тоже ошибка.
"""
from __future__ import annotations

import json
import sys
from collections import Counter

STATUS = {"ok", "weak", "broken", "dead"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    if not args:
        print(__doc__)
        return 2
    with open(args[0], encoding="utf-8") as f:
        d = json.load(f)
    st, ar, fl = d.get("stations") or [], d.get("arrays") or [], d.get("flows") or []
    errs: list[str] = []
    ids = Counter([s.get("id") for s in st] + [a.get("id") for a in ar])
    for i, n in ids.items():
        if not i:
            errs.append("узел без id")
        elif n > 1:
            errs.append(f"id «{i}» повторяется {n} раз")
    known = set(ids)
    for k, x in enumerate(fl):
        for end in ("from", "to"):
            if x.get(end) not in known:
                errs.append(f"связь {k} ({x.get('from')} -> {x.get('to')}): узла «{x.get(end)}» нет в stations или arrays")
    outside, bad = [], []
    for s in st:
        if s.get("status") not in STATUS:
            errs.append(f"станция «{s.get('id')}»: статус «{s.get('status')}» не из {sorted(STATUS)}")
        if not s.get("external") and not s.get("evidence"):
            errs.append(f"станция «{s.get('id')}» без опоры (evidence путь:строка)")
        if not s.get("external") and not s.get("locks"):
            outside.append(s)
        if s.get("status") in ("broken", "dead"):
            bad.append(s)
    readers = {r for a in ar for r in (a.get("readers") or [])}
    unread = [a for a in ar if not a.get("readers")]
    not_in_product = [a for a in ar if a.get("in_product") is False]
    used = {x.get("from") for x in fl} | {x.get("to") for x in fl} | readers
    lonely = [s for s in st if s.get("id") not in used]
    paths = Counter(x.get("path") or "main" for x in fl)
    print(f"карта «{d.get('name', '?')}»: станций {len(st)}, массивов {len(ar)}, связей {len(fl)}, путей {len(paths)} "
          f"({', '.join(f'{k} {v}' for k, v in paths.items())})")
    print(f"вне замков {len(outside)}: " + (", ".join(f"{s['id']} ({s.get('status')})" for s in outside) or "нет"))
    print(f"сломано или мертво {len(bad)}: " + (", ".join(f"{s['id']} {s['status']}" for s in bad) or "нет"))
    if unread:
        print("массивы, которые никто не читает: " + ", ".join(a["id"] for a in unread))
    if not_in_product:
        print("массивы мимо продукта: " + ", ".join(a["id"] for a in not_in_product))
    if lonely:
        print("станции без связей: " + ", ".join(s["id"] for s in lonely))
    if strict and outside:
        errs.append(f"строгий режим: {len(outside)} станций вне замков")
    if errs:
        print(f"ОШИБКИ {len(errs)}:\n  " + "\n  ".join(errs))
        return 1
    print("ошибок нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
