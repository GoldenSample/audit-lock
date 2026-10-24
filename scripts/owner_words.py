#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Слова владельца из стенограмм Claude Code: первоисточник аудита и проверка подписи цитатой.

Только процессор, ни одного вызова модели. Берутся реплики человека (origin.kind == human, у старых записей без origin:
без promptSource и не isMeta), реплики, набранные, пока модель работала (вложение queued_command с origin human: обычной
записи user у них нет, без этого теряются отмены и поправки на ходу), и ответы на AskUserQuestion (кроме отказа отвечать);
служебные вставки (<...>, отзывы хуков, тексты скилов, продолжения после сжатия, сообщения других сессий) отброшены;
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


def joined(c) -> str:
    if isinstance(c, list):
        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return str(c or "").strip()


def clean(t: str, kind: str) -> tuple[str, bool, str] | None:
    pasted = "<pasted_content" in t
    own = PASTED.sub(" ", t).strip()
    if not own or own.startswith(META) or "task-notification" in own[:80]:
        return None
    return own, pasted, kind


def human_texts(r: dict) -> list[tuple[str, bool, str]]:
    """[(текст владельца без вставок, была ли вставка, вид)] из записи; пусто, если в ней нет слов человека.

    Вид: prompt = обычная реплика; queued = реплика, набранная, пока модель работала (в стенограмме это вложение
    queued_command, обычной записи user у неё нет); answer = ответ на вопрос AskUserQuestion (выбор или свой текст)."""
    if r.get("isSidechain") or r.get("isMeta"):
        return []
    a = r.get("attachment")
    if r.get("type") == "attachment" and isinstance(a, dict) and a.get("type") == "queued_command":
        origin = a.get("origin")
        if isinstance(origin, dict) and origin.get("kind") != "human":   # peer, task-notification: не владелец
            return []
        if origin is None and a.get("commandMode") != "prompt":
            return []
        hit = clean(joined(a.get("prompt")), "queued")
        return [hit] if hit else []
    if r.get("type") != "user":
        return []
    tr = r.get("toolUseResult")
    if isinstance(tr, dict) and isinstance(tr.get("answers"), dict):
        out = []
        for q, ans in tr["answers"].items():
            ans = str(ans).strip()
            if ans and not ans.startswith("[User dismissed"):
                out.append((ans, False, "answer: " + str(q)[:200]))
        return out
    origin = r.get("origin")
    if isinstance(origin, dict):
        if origin.get("kind") != "human":
            return []
    elif r.get("promptSource") is not None:
        return []
    hit = clean(joined((r.get("message") or {}).get("content")), "prompt")
    return [hit] if hit else []


def records(root: Path):
    for f in sorted(root.glob("*/*.jsonl")):
        try:
            fh = open(f, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"user"' not in line and '"queued_command"' not in line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                for text, pasted, kind in human_texts(r):
                    yield f, r, text, pasted, kind


def epoch(ts) -> float:
    return dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()


def collect(a) -> int:
    root = Path(a.root).expanduser()
    keys = re.compile(a.keys, re.I) if a.keys else None
    since = epoch(a.since + "T00:00:00+00:00") if a.since else None
    seen: dict[str, dict] = {}
    for f, r, text, pasted, kind in records(root):
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
            seen[h] = {"ts": ts, "session": f.stem[:8], "project": f.parent.name, "kind": kind, "text": text[:3000],
                       "pasted": pasted}
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
    kinds = {k: sum(x["kind"].split(":")[0] == k for x in rows) for k in ("prompt", "queued", "answer")}
    print(f"реплик {len(rows)} ({span}; обычных {kinds['prompt']}, набранных во время работы {kinds['queued']}, "
          f"ответов на вопросы {kinds['answer']}), знаков {chars}, со вставками {sum(x['pasted'] for x in rows)}, "
          f"кусков {a.chunks}: {out}")
    return 0


def said(quote: str, root: Path, after=None) -> dict | None:
    q = norm(quote)
    if not q:
        return None
    lo = epoch(after) if after else None
    for f, r, text, _, kind in records(root):
        try:
            if lo is not None and epoch(r.get("timestamp")) < lo:
                continue
        except (TypeError, ValueError):
            continue
        t = norm(text)
        if (len(q) >= MIN_SUB and q in t) or t == q:
            return {"ts": r.get("timestamp"), "session": f.stem[:8], "kind": kind, "text": text}
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
    print(hit["ts"], hit["session"], hit["kind"].split(":")[0], hit["text"][:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
