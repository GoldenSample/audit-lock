#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Заверение другой моделью: промпт из файла уходит в OpenAI-совместимый эндпоинт, ответ сохраняется дословно.

  python cross_judge.py ПРОМПТ.md --out ОТВЕТ.md --url https://.../v1/chat/completions --model ИМЯ [--key-env ИМЯ_ПЕРЕМЕННОЙ]
      [--system "ты заверитель аудита..."] [--timeout 900]

Ключ берётся только из переменной окружения (--key-env, по умолчанию JUDGE_API_KEY), в файлы и argv не пишется.
Промпт читается из файла (кириллица в аргументах командной строки на некоторых системах бьётся). Температура и прочие
параметры не передаются: модель отвечает на своих умолчаниях. В файл ответа идут модель, время и текст без правок.
Смысл: свой вывод модель находит убедительным по построению, поэтому список «вне замков» заверяет модель другого семейства.
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
    ap.add_argument("--system", default="Ты независимый заверитель аудита. Спорь по существу, опирайся только на то, что дано, "
                                        "пиши, где довод слабый и что закрыть первым.")
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
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
        answer = j["choices"][0]["message"]["content"]
        served = j.get("model", a.model)
        status = "ответ получен"
    except Exception as e:  # noqa: BLE001
        answer, served, status = f"ОШИБКА: {type(e).__name__}: {e}", a.model, "ошибка"
    sec = (dt.datetime.now(dt.timezone.utc) - t0).total_seconds()
    Path(a.out).write_text(f"# Заверение: {served}, {t0.isoformat(timespec='seconds')}, {sec:.0f} с, {status}\n\n"
                           f"Промпт: {a.prompt}\n\n{answer}\n", encoding="utf-8")
    print(f"{status}: {a.out} ({len(answer)} знаков, {sec:.0f} с, модель {served})")
    return 0 if status == "ответ получен" else 1


if __name__ == "__main__":
    sys.exit(main())
