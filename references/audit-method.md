# The audit method: roles, briefs, formats

Contents: 1. The audit folder. 2. Inventory of sections. 3. Role briefs (section reader, reader of the owner's words, the model's path, the user's path, verifier, cross-model review, assembler, reviewers). 4. The map schema. 5. Cost and launching a fan-out. 6. Typical audit failures.

## 1. The audit folder

```
<audit>/
  SCOPE.md            the owner's word verbatim, the principle, the sections, the laws of the audit
  STATE.md            where we stand (in case of context compaction): launch, run id, what has been collected
  words/              the corpus of the owner's words (owner_words.py collect)
  parts/              role reports: <section>.md, W_WORDS.md, MODEL_PATH.md, USER_PATH.md, VERIFY.md, CROSS_ATTEST.md
  BRANCH_MAP.json     the pipeline map
  img/                diagrams drawn from the map (map_draw.py)
  AUDIT.md            the consolidated report
  SUMMARY.md          the summary for the owner
```

Write `STATE.md` right after launching the fan-out and update it at every stage. If the context gets compacted or the fan-out dies on a usage limit, work resumes from that file and not from zero.

## 2. Inventory of sections

A section is a piece of the pipeline that has its own product and its own consumer. Examples: "building a profile and releasing it to a USB drive", "website: selection logic", "website: pages and deployment", "hardware watchdogs", "knowledge bases". Folders and languages are no reason to cut sections: one section can live in three folders.

For each section, `SCOPE.md` holds: the paths (code, data, logs, skills, documents), the state today according to memory and handoff notes (verify against the disk), and the known loose ends of past audits.

The laws of the audit are written in `SCOPE.md` once and apply to every role:
1. Read only; the only thing a role may write is its own file in `parts/`.
2. What must not be physically touched: production, deployment, USB drives and removable disks, services, logs opened for writing (open sqlite as `file:...?mode=ro`), the graphics card, generations, paid calls, except those assigned to the role.
3. Support for every claim; "not found" stated plainly.
4. The reading barrier: what the agents must not read (personal material, secrets, the judges' prompts and scores when the writer and the judge have to stay separated).
5. Do not copy out passwords and keys, only the fact: "a key sits in the code, path:line".
6. The language and style of the reports.

## 3. Role briefs

A brief starts with a pointer to `SCOPE.md`: "read it in full; breaking the laws means failure". The rest is below. Do not put the auditor's hypothesis into the brief; put paths and questions. An agent that is handed a conclusion returns it confirmed.

### Section reader

```
YOUR SECTION <id>: <name>. Paths are in SCOPE.md, line <id>.
Check: <5-10 concrete questions about the section: where a formula may lie, where the release path is, which doors exist, which old items remain>.
Report: <audit>/parts/<id>.md, sections:
## Inventory: stations (scripts, steps) and datasets (databases, tables, logs); what really goes into the product, what is dead weight or a duplicate
## Production problems: id, severity (high / medium / low), what is broken or will break, support as path:line or a command with its output, the failure scenario for the consumer, the fix in one sentence
## Outside the locks: the owner's law or request (date) -> where it is held (a lock on the path, a check in the code, a test / text only / nowhere) -> why, and what it threatens
## Items from the previous audit: status now, with support
## What was checked by machine: commands and results
Also return a structured list of findings (id, severity, title, support, fix) and the "outside the locks" list.
```

The section's questions are written by the auditor, who has already looked at the inventory. A good question names a mechanism: "is the verdict bound to the file's sha or to its name", "what happens if the field's type is a number and not a list", "does the decision sheet cover every field the builder writes". A bad question: "check the code quality".

### Reader of the owner's words

Reads the whole corpus (in chunks, taking notes). Output `parts/W_WORDS.md`:
- "Laws and requests": date, a quote of up to 25 words, what it demands.
- "Outside the locks": for each law, where it is held now (the `path:line` of the lock, or "text only: the skill or memory file", or "nowhere").
- "Contradictions": where the owner's words disagree with the code, a skill or memory. Separately, cancelled decisions that the code still lives by.
- "Requests never carried out": asked for, but not in the code.

Other people's text pasted into the owner's messages (logs, someone else's posts, bot replies) is not the owner's words: `owner_words.py` cuts out `<pasted_content>` blocks and marks such lines.

### The model's path

How the executor gets through the pipeline's hooks. The method: collect 10 to 30 sample tool calls (JSON `tool_name`, `tool_input`), including the legitimate path and the bypasses, run each hook through `scripts/test_hook.py`, and record where the hook stays silent on a dangerous action and where it locks a harmless one. Plus a review of the registration: which events and tools the hook is attached to (`settings.json`), and which tools are not covered at all (MCP, the browser, the terminal, subagents).

### The user's path

Walk the path of the product's consumer from entry to result: a site visitor (home page, wizard, selection, checkout, links), a viewer (the first seconds, the loop, the call to action, the links), a hardware operator (profile, release, boot, test, snapshot). Where they leave, where they receive a defect, where the product differs from what was checked. Live services are read only.

### Verifier

```
Below is a digest of all the readers' findings (JSON) and the paths to their reports.
1) Re-check every finding of high and medium severity yourself, from disk, with your own commands, from a skeptic's position: try to refute it first.
   Verdict CONFIRMED / PARTIAL / REFUTED / NOT CHECKED, with your own support. Low findings are sampled, at least a third. Merge duplicates.
2) Put the "outside the locks" list into a prompt file and hand it to a model from a different family (cross_judge.py). The answer goes verbatim into parts/CROSS_ATTEST.md.
3) Report parts/VERIFY.md: one line per finding with the verdict and the support; the duplicates; where the cross-model reviewer disagrees.
```

On a large audit there are several verifiers, one per section, plus three skeptics on every high finding (refuted by a majority means dropped).

### Review by a different model

The prompt for the reviewer: the context of the pipeline in one paragraph; the list of "law, where it is held, why there is no lock"; the questions: (a) is the reasoning convincing for each item; (b) which five items should be closed first, and with which lock (inside the call, single door, hook, seal, sign-off, slot); (c) what is missing from the list. The answer is stored verbatim, and the assembler argues with it on the substance and does not retell it.

### Assembler

Reads `SCOPE.md`, everything in `parts/`, the verifier's verdicts and the cross-model review. Writes:
1. `BRANCH_MAP.json` following the schema in section 4, runs `map_check.py` and puts the output into the report.
2. `AUDIT.md` from `assets/AUDIT.template.md`.
3. `SUMMARY.md` from `assets/SUMMARY.template.md`.

Only CONFIRMED and PARTIAL go into the production problems. NOT CHECKED is a separate list, and REFUTED is one line at the end.

### Reviewers (large audit)

Two independent reviewers read the finished `AUDIT.md` against `parts/` and the disk: what in the report has no support, what from `parts/` got lost, where the fix plan cannot be verified. The assembler revises according to the remarks, and the second edition goes to the owner.

## 4. The schema of the map `BRANCH_MAP.json`

```json
{
  "name": "pipeline X",
  "date": "2026-10-24",
  "stations": [
    {"id": "build", "name": "Profile build", "files": ["cmo/build.py"], "inputs": ["snap"], "arrays": ["decisions"],
     "outputs": ["profile"], "locks": ["guard.check inside save()"], "status": "ok",
     "evidence": "cmo/build.py:120", "problems": ["C1-P2"]}
  ],
  "arrays": [
    {"id": "decisions", "path": "cpu_spec/decisions.json", "what": "decision sheet by field", "writers": ["make_sheet.py"],
     "readers": ["build"], "in_product": true}
  ],
  "flows": [
    {"from": "snap", "to": "build", "what": "timings and resistances", "path": "profile"}
  ]
}
```

- `status`: `ok`, `weak` (works, but is held by text or has a hole), `broken`, `dead` (unused).
- `locks`: an empty list means the station is outside the locks. A lock is named so that it can be found: a file and a function, or a hook and an event.
- `flows[].path`: the name of a path (for example "profile", "model", "visitor"); `map_draw.py` draws a separate lane for each.
- The nodes in `flows` must exist in `stations` or `arrays`. Model the outside world (the user, the hardware, the platform) as a station with status `ok` and the mark `"external": true`.

## 5. Cost and launching a fan-out

- Tell the owner the number of agents and the approximate share of the usage limit before launch. Without the owner's direct word the fan-out does not start.
- Readers and verifiers can run on a simpler model; the assembler and the verifier of high findings run on a strong one.
- A barrier between the readers and the verifier is justified (verification needs all the findings in order to merge duplicates). Between a reader and its own verification no barrier is needed; on a large audit run them as a pipeline.
- If the fan-out died on a usage limit, the harvest is not lost: the results of the finished agents are in the run log, so continue from the cache and not from scratch.
- A subagent may be forbidden to write files. In that case let it return the report text in its answer, and the orchestrator writes the file.

## 6. Typical audit failures

- **The inventory is a file list.** An inventory answers what goes into the product and what does not. A list of folders does not say that.
- **"Tests are green" with no number.** Write "47 checks, 47 passed, the command was such-and-such".
- **A finding without a scenario.** "There is no type check" is not a finding. "On 1R the field is a number, on 2R it is a list, `checks` crashes on the very first 1R snapshot, `snapshot.py:212`" is a finding.
- **The verifier was handed a conclusion.** It is given a claim and the task to refute it, not "confirm that X".
- **A diagram from the head.** It is drawn only from the map; otherwise the diagram repeats its author's blind spots.
- **A corpus without lines said "on the fly".** The owner often cancels or corrects a law while the model is working, and such a line sits in the transcript as a queue attachment, not as an ordinary entry. A collector that takes only ordinary entries loses exactly the cancellations: in a live audit the lifted law "no higher than 1.30 V" passed the cross-model review as still in force, because the cancellation had been typed in the middle of a turn. `owner_words.py` takes such lines too, as well as answers to questions; check this first in your own collector.
- **A report in jargon.** An owner who did not understand the report stops arguing, and the pipeline starts living a life of its own. Section and finding codes belong only in `AUDIT.md`; the summary uses human words.
