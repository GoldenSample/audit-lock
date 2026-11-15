"""Releases the firmware to dist/ after a review."""
import json
import shutil
import sys

src = sys.argv[1]
review = json.load(open("build/review.json", encoding="utf-8"))
if not review.get("approved"):
    sys.exit("the review has not passed")
shutil.copy(src, "dist/")
print("released", src)
