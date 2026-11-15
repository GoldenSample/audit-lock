#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review by a different model: a prompt from a file goes to an OpenAI-compatible endpoint, and the answer is saved verbatim.

  python cross_judge.py PROMPT.md --out ANSWER.md --url https://.../v1/chat/completions --model NAME [--key-env VARIABLE_NAME]
      [--system "you are an audit reviewer..."] [--timeout 900]

The key is taken only from an environment variable (--key-env, JUDGE_API_KEY by default); it is never written to files or argv.
The prompt is read from a file (non-ASCII text in command-line arguments gets mangled on some systems). Temperature and other
parameters are not sent: the model answers on its defaults. The answer file holds the model, the time and the unedited text.
The point: a model finds its own output convincing by construction, so the "outside the locks" list is reviewed by a model
from a different family.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt")
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--key-env", default="JUDGE_API_KEY")
    ap.add_argument("--system", default="You are an independent reviewer of an audit. Argue on the substance, rely only on what "
                                        "is given, and say where the reasoning is weak and what to close first.")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    text = Path(a.prompt).read_text(encoding="utf-8")
    body = {"model": a.model, "messages": [{"role": "system", "content": a.system}, {"role": "user", "content": text}]}
    headers = {"Content-Type": "application/json"}
    key = os.environ.get(a.key_env)
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(a.url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=headers)
    t0 = dt.datetime.now(dt.timezone.utc)
    ok = False
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
        answer = j["choices"][0]["message"]["content"]
        served = j.get("model", a.model)
        status = "answer received"
        ok = True
    except Exception as e:  # noqa: BLE001
        answer, served, status = f"ERROR: {type(e).__name__}: {e}", a.model, "error"
    sec = (dt.datetime.now(dt.timezone.utc) - t0).total_seconds()
    Path(a.out).write_text(f"# Cross-model review: {served}, {t0.isoformat(timespec='seconds')}, {sec:.0f} s, {status}\n\n"
                           f"Prompt: {a.prompt}\n\n{answer}\n", encoding="utf-8")
    print(f"{status}: {a.out} ({len(answer)} characters, {sec:.0f} s, model {served})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
