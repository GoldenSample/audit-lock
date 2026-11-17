# audit-lock: audit + lock

Russian version: [README.ru.md](README.ru.md) and [SKILL.ru.md](SKILL.ru.md). The last full Russian edition (references, templates, scripts) is kept at the tag [`v1-ru`](https://github.com/GoldenSample/audit-lock/tree/v1-ru).

A skill for people who have grown a large prompt machine around a model: dozens of skills, long instructions, memory, hooks, agents, their own pipelines. It does two things. First it shows honestly which of the machine's rules are really enforced and which are only written down. Then it turns the most important rules into locks that the model cannot bypass, and proves it with tests.

## Why you need it

The larger the prompt machine, the worse each individual rule is followed. This is not malice on the model's part, it is its nature: it takes the path of least resistance. A rule from a long instruction loses to an "obviously shorter" solution. After context compaction the model forgets what it read. It finds its own work convincing, and checking itself turns into a "PASS" stamp. The rules start contradicting each other, and the judge goes in circles.

Meanwhile the owner sees smooth reports and does not know that half of the laws have long been held only on paper. This usually comes out once the defect has already reached people: a hand-drawn brick in the video instead of the finished model, a fabrication posted to the channel, the wrong profile written to the USB drive.

The skill answers three questions that sooner or later face any large machine:
1. **What actually works here?** An inventory of stations and data: what goes into the product, what sits as dead weight, where the product differs from what was checked.
2. **Which of my rules are held by text alone?** Every law of the owner is taken from the owner's own words in the transcripts, not from retellings. For each one you can see where it stands: as a lock on the path, as a test, or only as a line in a skill.
3. **How do I make a rule get enforced?** A lock goes on the action itself (a write, a release, a model call, an upload) and checks the content, not fields filled in by the executor. Every known loophole is covered by a test. The lock is run against the old defect and has to stop it.

## What is inside

- **The audit method.** Readers per section, a reader of the owner's words, a skeptical verifier who first tries to refute each finding, a review by a different model, a map of the pipeline built from data and a diagram drawn from the map, a report in plain words with one main question.
- **A catalog of locks:** a single release door with a verdict bound to the file's sha, a lock inside the call, a hook on the side doors, a "plan before the result" seal, owner sign-off only as a verbatim quote, a shared-resource slot, a watchdog with a baseline event.
- **A catalog of bypasses worth testing:** another tool, redirection, `python -c`, `cd`, letter case, quotes, an encoded command, an upload through the browser, a two-step script, swapping the file after the check.
- **Scripts with no dependencies (Python 3.8+):**
  - `owner_words.py`: collects the owner's words from the transcripts and checks whether the owner said a given quote;
  - `release_gate.py`: the release door;
  - `guard_hook.py`: a configurable hook on the side doors;
  - `test_hook.py`: a hook test harness;
  - `map_check.py` and `map_draw.py`: the map check and the diagram;
  - `cross_judge.py`: a review by a model from a different family through any OpenAI-compatible endpoint.

## Getting started

1. Install it as a Claude Code plugin. Inside Claude Code:
   ```
   /plugin marketplace add GoldenSample/audit-lock
   /plugin install audit-lock@goldensample
   ```
   Or in one command from a terminal (Claude Code 2.1.292 or later; checked on 2.1.325):
   ```
   claude plugin install audit-lock --marketplace GoldenSample/audit-lock
   ```
   Without the plugin system, put the `audit-lock` folder into your skills folder (`~/.claude/skills/` or the project's `.claude/skills/`), for example with a clone:
   ```
   git clone https://github.com/GoldenSample/audit-lock ~/.claude/skills/audit-lock
   ```
2. Tell the model: "run an audit of my pipeline with audit-lock" and say what to check. It will launch an agent fan-out only if you ask for it directly, and it will name the cost in advance.
3. Read the summary and answer the main question.
4. Say "set the locks": the model takes the plan from the report, adds the locks, and shows the tests and the run against the old defect.

A quick check that the hook works on your machine:
```
python scripts/test_hook.py scripts/guard_hook.py assets/bypass_cases.example.json --env GUARD_CONFIG=assets/guard_config.example.json
```

## Try it

The skill is made and tested in Claude Code, and the lock phase uses Claude Code hooks. These three prompts show its core. The first two have a small sample project in this repo: copy the files from `evals/<case>/files/` into an empty folder (or run `evals/<case>/place-files.sh` there), open Claude Code in that folder and give the prompt.

1. Audit, sample `evals/audit-finds-text-only-rule/files/`:
   > audit this repo: which rules from the README are really held by code and which only by text, and where the firmware can get into dist around the check. don't launch agents, do it all yourself, don't edit the code, just the report: AUDIT.md and a short summary SUMMARY.md
2. Lock, sample `evals/lock-release-door/files/`:
   > fix it: the firmware must get into dist only through scripts/release.py, and only with a review verdict bound to the file's content, with the reviewer not being the author. hotfix in the Makefile currently puts it there around the check, close that. bypass tests are a must, and show that the lock would have stopped the old case: app.bin was edited after a review with approved true, and it went to dist
3. Hook check, no sample needed:
   > check that the side-door hook from audit-lock holds on this machine: run its bypass tests

The graders in `evals/<case>/graders/` describe a good result for the first two.

## What it reads, runs, sends and changes

audit-lock has no server, no account and no telemetry, and its author receives nothing from it. The scripts run on your machine with Python 3.8+ and its standard library.

- **Reads.** The files of the project you audit. In the audit phase, and in a release checked with `--owner-quote`, `scripts/owner_words.py` reads your Claude Code session logs on this machine (`~/.claude/projects/*/*.jsonl`). It keeps only the lines you typed yourself: no model text, no hook insertions, and pasted blocks are cut out and flagged. With `--keys` it keeps only the lines on the audit topic.
- **Writes, in your folders only.** The audit files in the folder you name: `SCOPE.md`, `AUDIT.md`, `SUMMARY.md`, `parts/`, `BRANCH_MAP.json`, `img/`, and the `words/` corpus with the time, a short session id, the project folder name and the text of each line it kept. A verdict file next to the file under review (`<file>.verdict.json`). The release journal `releases.jsonl`, and the hook's journal if you set one in its config.
- **Changes Claude Code settings, only on your word in the lock phase.** It copies the lock scripts into your project and adds a `PreToolUse` hook entry to the project's `.claude/settings.json`. The hook refuses only the side doors you agreed to close. The lock phase adds hooks, not permission rules, and it touches user-level settings only if you ask.
- **Sends, only when you run it.** `scripts/cross_judge.py` sends the prompt file you pass to the OpenAI-compatible endpoint you name with `--url`, with the API key from the environment variable you name (`JUDGE_API_KEY` by default). The script keeps the key out of files and out of the command line. It saves the answer to a file as a second opinion for the report, and the skill does not follow that answer as instructions. Without this step, nothing leaves your machine.
- **Runs.** The Python scripts in `scripts/`. `scripts/test_hook.py` runs a hook as a child process with a reduced environment. A fan-out of subagents runs only if you ask for it directly, and the skill names the cost first.

## Privacy, support and security

- Privacy: [PRIVACY.md](PRIVACY.md).
- Questions and bug reports: [GitHub Issues](https://github.com/GoldenSample/audit-lock/issues).
- Security problems: [SECURITY.md](SECURITY.md).

## Troubleshooting

- **"LOCK NOT WORKING: python not found".** The hook command found no working Python. Install Python 3.8 or later and put it on `PATH`. On Windows, `python` can be a Store stub that runs nothing; the command in `references/claude-code-hooks.md` tries `python3`, `python` and `py` in turn.
- **The hook refuses a legitimate command or lets a side door through.** Add the command as a case to your copy of `assets/bypass_cases.example.json`, run `python scripts/test_hook.py <hook> <cases.json>`, fix `allowed` or `protected` in the hook config, and run the tests again.
- **The release journal is gone after a plugin update.** `release_gate.py` writes `releases.jsonl` next to itself unless you pass `--journal`. Keep the lock scripts in your project, not in the plugin folder: the plugin folder changes with every update.
- **The skill does not show up after the install.** Start a new session or run `/reload-plugins`. Then check that `audit-lock` is listed and enabled in `claude plugin list`, and read the Errors tab of `/plugin`.

## Where it comes from

The skill was assembled from live practice: audits of pipelines for videos, a news channel, fiction and hardware overclocking, where the model bypassed written rules again and again. Every law in `SKILL.md` appeared after a specific failure, and the reason for it is written next to it.
