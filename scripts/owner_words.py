#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The owner's words from Claude Code transcripts: the audit's primary source and the check for sign-off by quote.

CPU only, not a single model call. It takes the human's messages (origin.kind == human; for old records without origin:
no promptSource and not isMeta), messages typed while the model was working (a queued_command attachment with a human origin:
these have no ordinary user record, and without them cancellations and corrections made on the fly are lost), and answers to
AskUserQuestion (except a refusal to answer); service insertions (<...>, hook feedback, skill texts, continuations after
compaction, messages from other sessions) are dropped; <pasted_content> blocks are cut out of the owner's text and flagged in
the pasted field (a pasted log or someone else's post is not the owner's words).

  python owner_words.py collect --out DIR [--keys REGEX] [--since 2026-01-01] [--chunks 4] [--root ~/.claude/projects]
      DIR/OWNER_WORDS.jsonl (ts, session, project, text, pasted) + chunks OWNER_WORDS_01..N.jsonl for the readers.
      Duplicates (session forks, repeats) are collapsed by text; the earliest date is kept.
  python owner_words.py said "quote" [--after 2026-10-24T10:00:00] [--root ...]
      exit code 0 = the owner said this (prints the date and the message), 1 = did not. A quote of 12 characters or more is
      matched as a substring after normalization (case, punctuation); a shorter one ("yes", "ok") counts only if it is the
      whole message.
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
# the app glues a service block onto the owner's message (a fork summary, a list of linked sessions): the block is cut out,
# its text is not the owner's words, and the message after it stays (before this fix, fresh messages were lost entirely)
REMIND = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
MIN_SUB = 12


def norm(s: str) -> str:
    # lower case, punctuation and symbols collapsed to spaces; letters of any alphabet are kept
    s = str(s).lower().replace("ё", "е")
    return " ".join(re.sub(r"[\W_]+", " ", s).split())


def joined(c) -> str:
    if isinstance(c, list):
        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return str(c or "").strip()


def clean(t: str, kind: str) -> tuple[str, bool, str] | None:
    pasted = "<pasted_content" in t
    own = PASTED.sub(" ", REMIND.sub(" ", t)).strip()
    if not own or own.startswith(META) or "task-notification" in own[:80]:
        return None
    return own, pasted, kind


def human_texts(r: dict) -> list[tuple[str, bool, str]]:
    """[(the owner's text without pasted blocks, whether there was a paste, kind)] from a record; empty if it holds no human words.

    Kind: prompt = an ordinary message; queued = a message typed while the model was working (in the transcript this is a
    queued_command attachment with no ordinary user record); answer = an answer to an AskUserQuestion (a choice or free text)."""
    if r.get("isSidechain") or r.get("isMeta"):
        return []
    a = r.get("attachment")
    if r.get("type") == "attachment" and isinstance(a, dict) and a.get("type") == "queued_command":
        origin = a.get("origin")
        if isinstance(origin, dict) and origin.get("kind") != "human":   # peer, task-notification: not the owner
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
    print(f"messages {len(rows)} ({span}; ordinary {kinds['prompt']}, typed while the model was working {kinds['queued']}, "
          f"answers to questions {kinds['answer']}), characters {chars}, with pasted blocks {sum(x['pasted'] for x in rows)}, "
          f"chunks {a.chunks}: {out}")
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
    c.add_argument("--keys", help="topic regex (without it, all messages are taken)")
    c.add_argument("--since", help="YYYY-MM-DD")
    c.add_argument("--chunks", type=int, default=4)
    c.add_argument("--root", default="~/.claude/projects")
    s = sub.add_parser("said")
    s.add_argument("quote")
    s.add_argument("--after", help="ISO time: the message is no earlier than this (the moment the lock was sealed)")
    s.add_argument("--root", default="~/.claude/projects")
    a = ap.parse_args()
    if a.cmd == "collect":
        return collect(a)
    hit = said(a.quote, Path(a.root).expanduser(), a.after)
    if not hit:
        print("not found: the owner did not say this" + (f" after {a.after}" if a.after else ""))
        return 1
    print(hit["ts"], hit["session"], hit["kind"].split(":")[0], hit["text"][:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
