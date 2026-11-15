# AUDIT: <pipeline> (<date>)

The owner's word, <date>: "<verbatim>".

## Principle
<whose method we repeat: past audits, what we take from them; what is new in this one>

## State today (from memory and handoff notes; verify against the disk)
- <what is installed, which versions, what changed recently>

## Primary source
- The owner's words: `words/OWNER_WORDS.jsonl` (<N> messages, <dates>, `owner_words.py collect --keys "<regex>"`).
- Past audits: <paths, open items>.

## Sections
| id | section | where |
|---|---|---|
| C1 | <product and consumer> | <paths to code, data, logs, skills> |

Plus: W (reader of the owner's words), V (verifier + cross-model review), R (map, report, summary).

## Laws of the audit (for every agent)
1. Read only. The only thing you may write is your own file in `<audit>/parts/`.
2. Do not physically touch: <production, deployment, USB drives, services, logs opened for writing, the graphics card, paid calls>.
3. Support for every claim: `path:line`, a command with its output, or an owner quote with a date. Not found means you write exactly that.
4. Reading barrier: <what not to read>.
5. Do not copy out passwords and keys.
6. Style: <language; no jargon in the conclusions meant for the owner>.
