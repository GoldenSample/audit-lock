# Privacy

audit-lock is a skill for Claude Code: instructions in `SKILL.md` and Python scripts that run on your machine. Its author, GoldenSample, runs no server for it and receives no data from it. It has no account, no telemetry and no analytics.

## What it reads

- The files of the project you ask it to audit or lock.
- Your Claude Code session logs on this machine (`~/.claude/projects/*/*.jsonl`). `scripts/owner_words.py` reads them in the audit phase and in a release checked with `--owner-quote`. It keeps only the lines you typed yourself and drops the model's text, hook insertions and pasted blocks. With `--keys` it keeps only the lines on the audit topic.

## What it writes

Only files in your folders: the audit folder you name (with the `words/` corpus: the time, a short session id, the project folder name and the text of each line it kept), verdict files next to the files under review, the release journal `releases.jsonl`, and the hook's journal if you set one. In the lock phase, and only on your word, it copies the lock scripts into your project and adds a hook entry to the project's `.claude/settings.json`.

## What can leave your machine

Only the prompt file you send with `scripts/cross_judge.py`. It goes to the endpoint you name, with the API key from the environment variable you name, and that provider's own privacy policy covers it. If you do not run `cross_judge.py`, nothing leaves your machine.

## How long it keeps data

The files stay where they were written until you delete them. To remove them, delete the audit folder, the `*.verdict.json` files and `releases.jsonl`. Uninstalling the plugin does not remove the files it wrote in your projects.

## Children

audit-lock is not intended for people under 18.

## Contact and changes

Questions: [GitHub Issues](https://github.com/GoldenSample/audit-lock/issues). Changes to this file are part of the repository history.
