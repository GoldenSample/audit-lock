"""Выпуск прошивки в dist/ после ревью."""
import json
import shutil
import sys

src = sys.argv[1]
review = json.load(open("build/review.json", encoding="utf-8"))
if not review.get("approved"):
    sys.exit("ревью не пройдено")
shutil.copy(src, "dist/")
print("выпущено", src)
