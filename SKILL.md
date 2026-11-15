---
name: audit-lock
description: "Audit a codebase or working pipeline and put machine locks on the action path, so that a rule is enforced instead of sitting in text. Two phases: AUDIT (inventory of stations and datasets, production problems, what is outside the locks and why, the owner's words from transcripts, a skeptical verifier, review by a different model, a map built from data, a plain report) and LOCK (a single release path with a verdict bound to the content sha, a hook on the side doors, owner sign-off only as a verbatim quote, a test for every bypass, a run of the lock against the historical defect). Production gate: before a release the plan answers 6 questions. Use when the user asks to audit a codebase, pipeline or agent setup, find what bypasses the rules, add guardrails, gates, pre-tool hooks or release locks, or asks why a written rule keeps being ignored. Triggers: audit the code, audit the pipeline, check everything, what is outside the gates, why is the rule not followed, add a lock, release gate, hook, stop the model from bypassing, fix it and build it in, audit, guardrail, PreToolUse hook, bypass."
license: MIT
---

# Audit + lock

A rule written in text does not get enforced. The only thing that gets enforced is a lock on the action path that checks the product itself. This skill first finds what is held by text alone (the AUDIT phase), then turns the most important rules into locks and proves them with bypass tests (the LOCK phase).

The phases run on the owner's word: "run an audit" starts the first one; "fix it", "build it in" or "set the locks" starts the second. Without a word to fix, the audit only reads.

## Where this comes from: five cases the method grew out of

1. **A brick instead of a graphics card.** A finished 3D model of a graphics card sat in the skill's library, the rule "take it from the library" was written down, and a hook reminded the model to open the skill on every run. A hand-drawn brick went into the video anyway. Only a refusal on the action itself (deny) helped; the reminder never helped once. Conclusion: a reminder is not a lock.
2. **The locks checked paperwork.** The release gate compared form fields that the executor filled in itself: "approved: true", "video: file name". A re-encoded copy went to the platform instead of the file that had been checked. The cure: a lock on the sha256 of the content, and owner sign-off only as a verbatim quote that the machine finds in the owner's real messages.
3. **Self-grading.** The one doing the work gave itself a PASS, metrics were written without counting, and the sign-off was added after the fact. The cure: the checker is not the doer; a metric comes only from a command; a record made after the result counts as a defect.
4. **Bypass through another door.** The lock stood on one script, while the same action went through `cp`, PowerShell, a different CLI to the same model, direct HTTP, or a script written in one step and run in the next. The cure: one permitted path, a hook on every other door, a test for every door.
5. **A baseline with no event.** A drift watchdog compared a connector against a baseline taken before the connector was reseated, and sent false alarms for a full day. The baseline could only be reset by hand, and nobody remembered that. Conclusion: every baseline needs an event that resets it, and that reset must go into the log.

## Laws (and the reason for each)

1. **The lock goes on the path, not beside it.** The refusal must stand on the action that spoils the result: a write, a copy, a release, a model call, an upload. The model skips advice in its context whenever a shorter way looks "obvious".
2. **Check the product, not the paperwork.** A file hash, the content, a word count, recognized speech against the script. A field that the executor fills in proves nothing.
3. **The checker is not the doer.** The judge has a different role and, better still, comes from a different model family: Claude judges Grok's text, Grok judges Claude's plan. A model finds its own output convincing by construction.
4. **Every claim has support.** `path:line`, a command with its output, or an owner quote with a date. "Not found" is written plainly. A metric without a count means the audit has failed.
5. **The primary source is the owner's words.** The owner's lines from the transcripts (`scripts/owner_words.py`), not retellings, not the model's memory, not handoff notes. A retelling loses the prohibitions, and the prohibitions are the most valuable part.
6. **One release path.** There is exactly one door that releases the product (`scripts/release_gate.py`), and it demands a verdict bound to the sha of that very file. The other doors are closed by a hook (`scripts/guard_hook.py`). The hook's regex is the backstop; the lock is the single door.
6a. **Intercept at the source.** A defect is caught at the entrance of the station where it is born, not by inspecting the finished product at the exit. A finished text or file can be checked, but the cause of the defect is no longer visible there, and the check costs more.
7. **Owner sign-off means the owner's verbatim words.** An "approved" field counts only if the quoted text is found by the machine in the owner's messages no earlier than the moment of the lock (`owner_words.py said`). A bare `true` is not a signature. Lifting a lock ("no gate") also takes a quote and an entry in the log.
8. **Honest judge rounds.** A round counts only if it is a new version and the judge has itself confirmed that the previous remarks were closed in substance. Neither the judge nor the executor knows the round limit; otherwise the limit becomes a loophole. A plan written to pass the refusal is a defect.
9. **A minor contradiction between rules is settled by the owner's eye.** If two rules cannot both be met without spoiling the result, build the best version, write down both rules and the choice, show it to the owner and record the owner's words verbatim. Major laws (facts, prices, safety) are not lifted this way.
10. **Without the "prod" tag the judge is an adviser.** On draft work the judge's remarks are taken on their merits and nobody waits for rounds. With the word "prod" the judge locks. Otherwise work stalls for hours.
11. **Closed on production, open on everything else.** A hook error on a production action means a refusal. On reads and checks an error means a pass with a printed notice; otherwise one broken hook locks up all work.
12. **The model does not edit the lock's state.** The hook forbids writes to its own state files and to its own registration. Hooks are edited only on the owner's word and with the tests run.
13. **Before context compaction, the task state goes into a file.** What has been read, where we stand, what is still open. After compaction, reading counts from scratch: the model's memory of a file it read before compaction is worth nothing.
14. **Your own before something new.** Before building, find what already exists in the repo (code search, past audits, existing locks). Building new is easier than digging up your own, which is why this step is skipped most often.
15. **The report to the owner is in plain words.** The point in the first line, 3 to 7 items, no codes and no tables, one main question with a recommendation. Details go into a file, with a link.
16. **An agent fan-out only on the owner's direct word.** Name the cost before launch. A harness flag or a system reminder is not the owner's word.
17. **An audit only reads.** Do not touch production, live hardware, USB drives, databases or services; a website gets GET requests only. Run tests only if they write nothing.

## Phase 1: AUDIT

Detailed role briefs and formats: `references/audit-method.md`. Templates: `assets/`.

0. **The owner's word, verbatim,** goes into `SCOPE.md` (template `assets/SCOPE.template.md`). Find past audits of the same pipeline: their open items are re-checked, not rewritten.
1. **The corpus of the owner's words.** `python scripts/owner_words.py collect --keys "<topic regex>" --out <audit>/words` collects the owner's lines from Claude Code transcripts (the human only, without hook insertions or other people's text), collapses duplicates and cuts the result into chunks for the readers.
2. **Sections.** Split the pipeline into 5 to 12 sections by the meaning of the product (what is released, and for whom), not by folders. Each section has its paths, its state today and its known loose ends.
3. **Section readers.** Each one writes `parts/<id>.md` from the template `assets/part.template.md` in five parts: inventory (stations, datasets, what goes into the product, dead weight), production problems (severity, support, failure scenario, the fix in one sentence), outside the locks (the law, where it is held, why), items from the previous audit, and what was checked by machine.
4. **The reader of the owner's words.** Laws, prohibitions and requests with a date and a quote; where each one is held (a lock, a test, text only, nowhere); contradictions with skills and code; requests that were never carried out.
5. **The model's path and the user's path.** Run the hooks on sample requests and see where the model walks past them. Walk the path of whoever receives the product (a site visitor, a viewer, a hardware operator) and find where they leave or receive a defect.
6. **The verifier.** Re-check every high and medium finding from disk with your own commands, and try to refute it first. Low findings are sampled, at least a third of them. Merge duplicates across sections. Verdict: CONFIRMED, PARTIAL, REFUTED, NOT CHECKED.
7. **Review by a different model.** Hand the "outside the locks" list with its reasoning to a model from a different family (`scripts/cross_judge.py`) and save the answer verbatim. The question: is the "why there is no lock" convincing, what should be closed first, and with which lock.
8. **A map built from data.** `BRANCH_MAP.json` (stations, datasets, links, locks, statuses; example `assets/map.example.json`) and the check `python scripts/map_check.py BRANCH_MAP.json`: links point at existing nodes, and stations without locks are listed. The diagram is drawn only from the map: `python scripts/map_draw.py BRANCH_MAP.json --out img/` (SVG and HTML). A diagram drawn "from the head" repeats the blind spots of whoever draws it.
9. **The report.** `AUDIT.md` from the template `assets/AUDIT.template.md`: only CONFIRMED and PARTIAL go into the problems, and whatever was refuted gets one line at the end. The fix plan is numbered, and every item has a check. Up to 8 questions for the owner, each with a recommendation. `SUMMARY.md` from `assets/SUMMARY.template.md`.

**How many agents.** A small audit: one agent per section, a reader of the owner's words, a verifier and an assembler (about 10). A large one: three readers per section (inventory, problems, outside the locks), readers of the owner's words by chunk, verifiers by section, the cross-model review, the map, the diagrams and two reviewers of the report (about 100). Without subagents, do the steps yourself, but still run verification as a separate pass from a fresh read of the disk, preferably with a different model. An example fan-out script for Claude Code: `assets/workflow.example.js`.

## Phase 2: LOCK

The catalog of locks and bypasses: `references/lock-patterns.md`. Claude Code hooks: `references/claude-code-hooks.md`.

0. **Input:** the fix plan from `AUDIT.md` and the owner's word to fix. Write `WORKFLOW.md` from `assets/WORKFLOW.lock.template.md`: every item has its law, the lock type, the point on the path, the bypass test and what the owner decides. **Safeguard clause:** before the first edit, list the pipeline's existing locks and what must not be weakened in them (the enforcement register). Fixing one lock often quietly opens another.
1. **Choose the lock type** from the matrix in `references/lock-patterns.md`: a lock inside the call (a guard in the API wrapper; without a pass the request does not leave), a single release door with a verdict bound to the sha, a hook on the side doors, a seal and a ticket (the input sha in the ticket equals the sha of what actually left), sign-off by quote, a shared-resource slot (one lease per card or port).
2. **Put the lock inside the path and the hook outside.** A lock in the code catches every door that goes through that code. A hook catches the doors that go around the code. You need both.
3. **A test for every door.** For each lock: the legitimate path passes, every known side door is refused, a hook error on production means a refusal, and there is a smoke run that writes nothing (`HOOK_SMOKE=1`). The harness: `python scripts/test_hook.py <hook> <cases.json>`; the base set of bypasses: `assets/bypass_cases.example.json`.
4. **A run against the historical defect.** A lock that lets the old defect through is not a lock. Feed it the very file or plan that started it all: it must refuse, with a clear reason. A good reference sample must pass.
5. **A reason instead of silence.** If you are not adding a lock, write down the reason with a check (a command and its output); do not just skip the item.
6. **Log and report.** Every release, lift and refusal is written as a line of jsonl. A plan item is closed only with a "verified" field: by what (a test, a run, a command) and with a number or verbatim output. The word "done" without a check does not close an item. Commit per plan item. The report to the owner is in plain words: what is now locked, what is still text and why, and one question.

## Production gate: when the skill is mandatory on every release

A pipeline can keep this skill as the gate for every production run: a hook requires reading it before any production action (a build, a render, a write of the product, an upload, a deploy, a write to removable media) and hands it to the judge together with the plan. In that case the audit and lock phases do not run. Before the first action, the production plan answers six questions, and the judge checks the answers against the steps of the plan:

1. **The release door.** What the product goes through on its way to people or to hardware (a release script, an upload, a deploy, a write to a USB drive) and which lock stands on that door. If there is a lock, name it and its command. If there is none, write exactly that, "there is no locked door", and do not call a manual copy a release.
2. **What the door checks in the product itself.** A hash, the content, recognized speech against the script, a count. If the check looks at fields you fill in yourself, that is paperwork, and the plan says so.
3. **Who judges.** Not the author of the product. The verdict is bound to the version that leaves (the sha). An edit after the judgment means a new judgment.
4. **Side doors.** By which other routes the same product can be released (`cp`, a browser, another CLI, direct HTTP) and what holds them shut. Do not use them, even when it is "faster".
5. **What is held by text alone.** The owner's laws for this product that have no lock: list them so they stay in view and not in memory.
6. **The check after release.** What confirmed that the same thing went out (the sha of the copy, the live page, the file downloaded back), plus a line in the release log.

Do not build new locks on every release: write the hole you found into the report to the owner and propose it as a LOCK phase. Without the "prod" tag the judge advises (law 10); with the tag it locks a plan that does not answer these questions.

**Do not do without the owner:** change passwords and keys, deploy to production, weaken existing locks, edit hook registration without the owner's word, edit lock state by hand.

## How to check yourself before handing over

- Every claim in the report has support, and the metrics were counted by a command.
- The findings went through the verifier, and nothing refuted ended up among the problems.
- `map_check.py` passed, and the diagram was built from the map.
- Every new lock is covered by a bypass test and was run against the historical defect.
- The summary for the owner: the point in the first line, one question with a recommendation.
