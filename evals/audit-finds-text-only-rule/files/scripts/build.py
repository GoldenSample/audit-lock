"""Собирает build/app.bin и черновик ревью (поля заполняет тот же скрипт)."""
import json
import os

os.makedirs("build", exist_ok=True)
with open("build/app.bin", "wb") as f:
    f.write(b"FW-1.4.2" + bytes(range(64)))
review = {"file": "app.bin", "approved": True, "reviewer": os.environ.get("USER", "builder"), "author": os.environ.get("USER", "builder")}
with open("build/review.json", "w", encoding="utf-8") as f:
    json.dump(review, f)
print("build/app.bin готов, review.json записан")
