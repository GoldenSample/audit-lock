---
tags: [audit-lock]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

fix it: the firmware must get into dist only through scripts/release.py, and only with a review verdict bound to the file's content, with the reviewer not being the author. hotfix in the Makefile currently puts it there around the check, close that. bypass tests are a must, and show that the lock would have stopped the old case: app.bin was edited after a review with approved true, and it went to dist

Input files: README.md, Makefile, scripts/build.py, scripts/release.py
