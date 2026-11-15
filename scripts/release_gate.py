#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The single release door: the product reaches the consumer only with a verdict bound to the sha256 of this file.

The verdict sits next to the product: <file>.verdict.json. It is written by the judge (or its wrapper) with the stamp command, not by the executor.
  python release_gate.py stamp   FILE --verdict PASS --judge NAME --maker NAME [--report REPORT] [--judge-error TEXT] [--open "item" ...]
  python release_gate.py check   FILE [--allow PASS] [--max-age-h 72] [--owner-quote]     dry check, exit code 0 = the release will pass
  python release_gate.py release FILE --dest FOLDER [--allow PASS] [--max-age-h 72] [--owner-quote] [--journal releases.jsonl]
  python release_gate.py find    SHA256 [--journal releases.jsonl]                          which release carries this content

Release checks: the verdict exists; the verdict's sha256 = the file's sha256 now (the file did not change after the judgment);
the judge really ran (no judge_error); the judge is not the one who did the work; the verdict is from the permitted set;
the verdict is no older than --max-age-h; with --owner-quote the owner_quote field must contain a quotation ("...", “...” or «...»)
that owner_words.py said finds in the owner's messages no earlier than the time of the verdict. The copy is written under a
temporary name, compared by sha256 and only then given its real name. Every release and every refusal is written as a line in the log.
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
QUOTE = re.compile(r"«([^«»]{2,})»|“([^“”]{2,})”|\"([^\"]{2,})\"")


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
    print(f"verdict {a.verdict} for {p.name} ({v['sha256'][:12]}) written: {vpath(p)}")
    return 0


def problems(p: Path, a) -> tuple[list[str], dict]:
    errs: list[str] = []
    if not p.is_file():
        return [f"no such file {p}"], {}
    vp = vpath(p)
    if not vp.is_file():
        return [f"no verdict {vp.name}: the judgment comes first (the judge writes the verdict with the stamp command)"], {}
    try:
        v = json.loads(vp.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"the verdict cannot be read: {e}"], {}
    cur = sha256(p)
    if v.get("sha256") != cur:
        errs.append("the verdict belongs to different content: the file changed after the judgment, a new judgment is needed")
    if v.get("judge_error"):
        errs.append(f"the judge did not run ({v['judge_error']}): release only after a full judgment")
    if not v.get("judge"):
        errs.append("the verdict does not name a judge")
    elif v.get("maker") and v["judge"].strip().lower() == v["maker"].strip().lower():
        errs.append("the judge and the executor are the same: the doer does not grade itself")
    allow = {x.strip() for x in a.allow.split(",") if x.strip()}
    if v.get("verdict") not in allow:
        opened = v.get("open") or []
        errs.append(f"the verdict \"{v.get('verdict')}\" is not among the permitted {sorted(allow)}" +
                    (": open items " + "; ".join(map(str, opened[:10])) if opened else ""))
    try:
        age_h = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(v["ts"])).total_seconds() / 3600
        if a.max_age_h and age_h > a.max_age_h:
            errs.append(f"the verdict is older than {a.max_age_h} h ({age_h:.0f} h): judge again")
    except (KeyError, ValueError, TypeError):
        errs.append("the verdict has no judgment time")
    if a.owner_quote:
        qs = [x or y or z for x, y, z in QUOTE.findall(str(v.get("owner_quote") or ""))]
        if not qs:
            errs.append("no owner sign-off as a quotation in quote marks (the owner_quote field); a bare yes or true is not a signature")
        else:
            sys.path.insert(0, str(HERE))
            import owner_words  # noqa: E402
            root = Path(a.root).expanduser()
            for q in qs:
                if not owner_words.said(q, root, v.get("ts")):
                    errs.append(f"the owner did not say \"{q[:80]}\" after the judgment (owner_words.py said)")
    return errs, v


def check(a) -> int:
    errs, v = problems(Path(a.file), a)
    if errs:
        print("STOP:\n  " + "\n  ".join(errs))
        return 1
    print(f"the release will pass: {a.file}, verdict {v['verdict']}, judge {v['judge']}")
    return 0


def release(a) -> int:
    p = Path(a.file)
    jr = Path(a.journal) if a.journal else HERE / "releases.jsonl"
    errs, v = problems(p, a)
    if errs:
        journal(jr, {"ts": now(), "file": str(p), "result": "refused", "why": errs})
        print("STOP:\n  " + "\n  ".join(errs))
        return 1
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    final = dest / p.name
    tmp = dest / (p.name + ".partial")
    shutil.copy2(p, tmp)
    same = sha256(tmp) == v["sha256"]
    if not same:
        tmp.unlink(missing_ok=True)
        journal(jr, {"ts": now(), "file": str(p), "dest": str(final), "result": "refused", "why": ["the copy did not match by sha256"]})
        print("STOP: the copy did not match by sha256, the release is cancelled")
        return 1
    os.replace(tmp, final)
    journal(jr, {"ts": now(), "file": str(p), "dest": str(final), "sha256": v["sha256"], "verdict": v["verdict"],
                 "judge": v["judge"], "report": v.get("report", ""), "result": "released", "verified": True})
    print(f"released: {final} ({v['verdict']}), the copy was verified by sha256")
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
        print("no releases with this content")
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
    s.add_argument("--owner-quote", help="the owner's sign-off, with the quotation in quote marks")
    for name in ("check", "release"):
        x = sub.add_parser(name)
        x.add_argument("file")
        x.add_argument("--allow", default="PASS")
        x.add_argument("--max-age-h", type=float, default=0)
        x.add_argument("--owner-quote", action="store_true", help="require the owner's sign-off as a quotation")
        x.add_argument("--root", default="~/.claude/projects", help="transcripts used to verify the quotation")
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
