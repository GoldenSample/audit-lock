# WORKFLOW: locks from the audit of <pipeline> (<date>)

The owner's word, <date>: "<verbatim: fix it, build it in, set the locks>". Input: `AUDIT.md` section 9 (the fix plan).

## Step 0, before any edits
- Find what already exists: this pipeline's existing locks, hooks and tests (`<search commands and their output>`). Fix your own; do not build a second one next to it.
- Write the state to `STATE.md` (in case of context compaction).

## Items
| # | law (verbatim or file) | lock type | point on the path | bypass test | historical defect for the run | owner decides |
|---|---|---|---|---|---|---|
| 1 | <...> | single door + verdict bound to the sha | `<file:function>` | `<test_*.py, cases>` | `<the file that got through before>` | no |

## Reasons against (items where no lock is added)
- <item>: <why it is not needed>, check: `<command>` -> `<output>`.

## What I do not do without the owner
Passwords and keys, deploying to production, weakening existing locks, hook registration, editing lock state.

## Done when
- Every lock: the legitimate path passes, every door from the catalog is refused, an error on production means a refusal.
- Every lock was run against the historical defect: a refusal with a clear reason; the reference sample passes.
- All hook tests of the pipeline are green, with the number of checks.
- The report to the owner: what is locked, what is still text and why, one question.
