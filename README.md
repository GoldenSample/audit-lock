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

1. Put the `audit-lock` folder into your skills folder (`~/.claude/skills/` or the project's `.claude/skills/`). The easiest way is a clone:
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

## Where it comes from

The skill was assembled from live practice: audits of pipelines for videos, a news channel, fiction and hardware overclocking, where the model bypassed written rules again and again. Every law in `SKILL.md` appeared after a specific failure, and the reason for it is written next to it.
