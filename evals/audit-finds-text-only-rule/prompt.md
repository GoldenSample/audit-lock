---
tags: [audit-lock]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

проведи аудит этого репо: какие правила из README реально держатся кодом, а какие только текстом, и где прошивка может уйти в dist мимо проверки. агентов не запускай, всё сам, код не правь, только отчёт: AUDIT.md и короткая выжимка SUMMARY.md

Input files: README.md, Makefile, scripts/build.py, scripts/release.py
