---
tags: [audit-lock]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

чини: прошивка должна попадать в dist только через scripts/release.py, и только с вердиктом ревью, привязанным к содержимому файла, ревьюер не автор. hotfix в Makefile сейчас кладёт мимо, закрой. тесты на обходы обязательно и покажи, что замок остановил бы старый случай: app.bin поправили после ревью approved true, и он ушёл в dist

Input files: README.md, Makefile, scripts/build.py, scripts/release.py
