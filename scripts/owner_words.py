#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Слова владельца из стенограмм Claude Code: первоисточник аудита и проверка подписи цитатой.

Только процессор, ни одного вызова модели. Берутся реплики человека (origin.kind == human, у старых записей без origin:
без promptSource и не isMeta); служебные вставки (<...>, отзывы хуков, тексты скилов, продолжения после сжатия) отброшены;
блоки <pasted_content> вырезаются из текста владельца и помечаются полем pasted (вставленный лог или чужой пост не его слова).

  python owner_words.py collect --out DIR [--keys REGEX] [--since 2026-01-01] [--chunks 4] [--root ~/.claude/projects]
      DIR/OWNER_WORDS.jsonl (ts, session, project, text, pasted) + куски OWNER_WORDS_01..N.jsonl для чтецов.
      Дубли (форки сессий, повторы) схлопываются по тексту, остаётся самая ранняя дата.
  python owner_words.py said "цитата" [--after 2026-10-24T10:00:00] [--root ...]
      код 0 = владелец это сказал (печатает дату и реплику), 1 = не говорил. Цитата от 12 знаков ищется подстрокой
      после чистки (регистр, ё, знаки); короче («да», «ок») засчитывается, только если это вся реплика.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

META = ("<", "This session is being continued", "Continue from where you left off", "[Image", "Another Claude session",
        "[Cross-session", "Caveat:", "[SYSTEM NOTIFICATION", "[Request interrupted", "Stop hook feedback",
        "Base directory for this skill", "Commit the working tree", "Run the \"", "Your response above")
PASTED = re.compile(r"<pasted_content.*?</pasted_content[^>]*>", re.S)
MIN_SUB = 12


def norm(s: str) -> str:
    s = str(s).lower().replace("ё", "е")
    return " ".join(re.sub(r"[^0-9a-zа-я]+", " ", s).split())


def human_text(r: dict) -> tuple[str, bool] | None:
    """(текст владельца без вставок, была ли вставка) или None, если запись не реплика человека."""
    if r.get("type") != "user" or r.get("isSidechain") or r.get("isMeta"):
        return None
    origin = r.get("origin")
    if isinstance(origin, dict):
        if origin.get("kind") != "human":
            return None
    elif r.get("promptSource") is not None:
        return None
    c = (r.get("message") or {}).get("content")
    if isinstance(c, list):
        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    t = str(c or "").strip()
    if not t:
        return None
    pasted = "<pasted_content" in t
    own = PASTED.sub(" ", t).strip()
    if not own or own.startswith(META) or "task-notification" in own[:80]:
        return None
    return own, pasted


def records(root: Path):
    for f in sorted(root.glob("*/*.jsonl")):
        try:
            fh = open(f, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"user"' not in line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                ht = human_text(r)
                if ht:
                    yield f, r, ht[0], ht[1]


def epoch(ts) -> float:
    return dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()


def collect(a) -> int:
    root = Path(a.root).expanduser()
    keys = re.compile(a.keys, re.I) if a.keys else None
    since = epoch(a.since + "T00:00:00+00:00") if a.since else None
    seen: dict[str, dict] = {}
    for f, r, text, pasted in records(root):
        ts = r.get("timestamp") or ""
        try:
            if since is not None and epoch(ts) < since:
                continue
        except ValueError:
            continue
        if keys and not keys.search(text):
            continue
        h = hashlib.sha1(norm(text).encode("utf-8")).hexdigest()
        if h not in seen or ts < seen[h]["ts"]:
            seen[h] = {"ts": ts, "session": f.stem[:8], "project": f.parent.name, "text": text[:3000], "pasted": pasted}
    rows = sorted(seen.values(), key=lambda x: x["ts"])
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "OWNER_WORDS.jsonl", "w", encoding="utf-8") as fo:
        for x in rows:
            fo.write(json.dumps(x, ensure_ascii=False) + "\n")
    size = max(1, -(-len(rows) // a.chunks))
    for i in range(a.chunks):
        part = rows[i * size:(i + 1) * size]
        if part:
            with open(out / f"OWNER_WORDS_{i + 1:02d}.jsonl", "w", encoding="utf-8") as fo:
                for x in part:
                    fo.write(json.dumps(x, ensure_ascii=False) + "\n")
    span = f"{rows[0]['ts'][:10]} .. {rows[-1]['ts'][:10]}" if rows else "-"
    chars = sum(len(x["text"]) for x in rows)
    print(f"реплик {len(rows)} ({span}), знаков {chars}, со вставками {sum(x['pasted'] for x in rows)}, кусков {a.chunks}: {out}")
    return 0


def said(quote: str, root: Path, after=None) -> dict | None:
    q = norm(quote)
    if not q:
        return None
    lo = epoch(after) if after else None
    for f, r, text, _ in records(root):
        try:
            if lo is not None and epoch(r.get("timestamp")) < lo:
                continue
        except (TypeError, ValueError):
            continue
        t = norm(text)
        if (len(q) >= MIN_SUB and q in t) or t == q:
            return {"ts": r.get("timestamp"), "session": f.stem[:8], "text": text}
    return None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--out", required=True)
    c.add_argument("--keys", help="регулярка темы (без неё берутся все реплики)")
    c.add_argument("--since", help="YYYY-MM-DD")
    c.add_argument("--chunks", type=int, default=4)
    c.add_argument("--root", default="~/.claude/projects")
    s = sub.add_parser("said")
    s.add_argument("quote")
    s.add_argument("--after", help="ISO-время: реплика не раньше (момент печати замка)")
    s.add_argument("--root", default="~/.claude/projects")
    a = ap.parse_args()
    if a.cmd == "collect":
        return collect(a)
    hit = said(a.quote, Path(a.root).expanduser(), a.after)
    if not hit:
        print("не найдено: владелец так не говорил" + (f" после {a.after}" if a.after else ""))
        return 1
    print(hit["ts"], hit["session"], hit["text"][:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
