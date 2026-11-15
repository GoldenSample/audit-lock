---
tags: [audit-lock]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

audit this repo: which rules from the README are really held by code and which only by text, and where the firmware can get into dist around the check. don't launch agents, do it all yourself, don't edit the code, just the report: AUDIT.md and a short summary SUMMARY.md

Input files: README.md, Makefile, scripts/build.py, scripts/release.py
