# Locks: types, bypasses, building rules

Contents: 1. The matrix: which lock for which law. 2. Eight types of locks. 3. The catalog of bypasses (what to test). 4. Building rules. 5. How to tell that a lock checks paperwork.

## 1. The matrix

| The law sounds like this | The lock | Why this one |
|---|---|---|
| "release only what has been checked" (to a USB drive, a platform, a channel, production) | a single release door + a verdict bound to the sha + a hook on the other doors | the check is tied to the content, and the copy is compared after the write |
| "do not call the model/API without X" (without a manifest, a limit, a ticket) | a lock inside the call wrapper (a guard before HTTP) + a hook on direct calls | any script that goes through the wrapper is locked, with no exceptions |
| "read the skill/dataset first, then act" | a hook: a production action is forbidden until the session log shows a full read; after context compaction the count starts over | a reminder does not work; only a refusal on the action does |
| "the plan before the result", "the map before the render" | a seal: the plan writes its sha and time into a log, and the release refuses if the seal is younger than the result or the sha does not match | a retroactive signature is caught by time and hash |
| "approved by the owner" | sign-off is a quoted text that the machine finds in the owner's messages after the seal | a field filled in by the executor is worth nothing |
| "one model per card", "do not touch someone else's process" | a slot: a lease file with O_EXCL, holder = name + pid, a lease term, a hook on direct ports | races and silent takeovers show up by the holder's name |
| "do not kill services", "do not change limits" | a hook: commands against a list of protected names, one permitted tool | the action is irreversible, and a refusal is cheaper than the post-mortem |
| "the comparison baseline must be fresh" | the baseline reset event is written to the log; the watchdog itself proposes a reset after a power break or a reseat | otherwise false alarms teach people to ignore them |

## 2. Eight types of locks

**2.1 A lock inside the call.** A wrapper that the call (to a model, an API, a device write) has to go through. The check comes before the action: no condition met means an exception, and the request does not leave. Example: `guard()` before HTTP with a cost estimate, `check(profile, sheet)` inside `save()`. Strength: it catches every door that goes through the code. Weakness: it does not see the paths around the code; the hook closes those.

**2.2 A single release door.** One tool copies the product to the place where it is consumed, and it does so only with a verdict whose `sha256` matches the file, where the judge really ran (not "no judge"), the verdict is from the permitted set, and the judge is not the one who did the work. After the copy, the hash of the copy is compared and a line is written to the release log. Starter: `scripts/release_gate.py`.

**2.3 A hook on the side doors.** PreToolUse in the agent harness: a command or a write that puts the product into a protected place by any other means gets a refusal with the text "there is one path: <tool>". Parsing is per segment (`;`, `&&`, `|`, newline); a read is not production; a `cd` inside the command changes the folder for the segments that follow. Starter: `scripts/guard_hook.py`. A regex catches the known doors, so the hook is the backstop and the lock is 2.2.

**2.4 A seal and a ticket.** The step after which the input must not change writes a ticket: the sha of the input, the sha of the manifest, the time with microseconds. The next step sends exactly the text whose sha is in the ticket and refuses on a mismatch. This makes "checked one thing, sent another" impossible.

**2.5 Sign-off by quote.** The fields "approved", "lifted by the owner" and "owner's verdict" accept only text that carries a quotation. The machine looks for the quote in the owner's messages from the transcripts (human lines only, without pasted text, hook feedback or skill text), no earlier than the time of the seal. A short "yes" or "ok" counts only if it is the whole message. Starter: `scripts/owner_words.py said`.

**2.6 Lifting a lock by word.** The owner can lift a lock ("no gate"): the lift is valid for a limited time or for one task, is verified by a quote and is written to the lift log. An environment variable such as `GATE=off` sets the mark "lock disabled" and writes to the log, but does not open the release.

**2.7 A shared-resource slot.** One lease file outside virtualized folders (application sandboxes can be invisible to services), acquisition with `O_EXCL` and a nonce check, holder = name + pid, nested entry through an environment variable, a lease term. A hook forbids direct access to the resource's port while someone else holds the slot.

**2.8 A watchdog with a baseline event.** If a watchdog compares against a baseline (current shares across wires, model speed, dump size), the baseline has a date and an event that resets it. A gap in the log longer than N hours or an explicit reseat means the watchdog writes "the baseline is stale, reset it?" instead of raising alarms against the old baseline. A reset is written as a log line with its reason.

## 3. The catalog of bypasses: what to test

Each line is a test case for `scripts/test_hook.py` (the base set is in `assets/bypass_cases.example.json`). The expectation for each: the legitimate path passes, and the bypass is refused or is caught by lock 2.2 at the exit.

Shell commands:
- `cp`, `mv`, `copy`, `move`, `xcopy`, `robocopy`, `rsync`, `scp`, PowerShell `Copy-Item`, `Move-Item`, `Set-Content`, `Out-File`.
- Redirection with `>` and `>>`, `tee`, a heredoc `cat > file <<EOF`.
- Inline code: `python -c "open(...,'w')"`, `shutil.copy`, `write_bytes`, `node -e "fs.writeFileSync(...)"`.
- Paths: a relative path after `cd`, different letter case, backslashes and forward slashes, `\\?\` long paths, a variable `$d`, a drive letter through `subst`, a symlink or junction to the protected folder.
- Splitting: the protected path in quotes, string concatenation, an encoded command (the PowerShell switch for an encoded command, or a base64 payload that is decoded and piped into a shell).
- Two steps: write a script to a harmless place, then run `python script.py` in a second call. A hook on the command sees only the launch. Only a lock at the exit (2.2) or a content check on the consumer's side catches this.
- Deferred launch: the task scheduler, cron, `at`, a service. The hook lets it through now, and the action happens without the agent.

Agent tools other than the shell:
- A file write by a tool (`Write`, `Edit`, `MultiEdit`, `NotebookEdit`) straight into the protected folder.
- The browser and computer control: a file upload through `file_upload`, a batch of browser actions, screen control, an application's built-in terminal.
- A different CLI to the same model or API, direct HTTP (`curl`, `Invoke-WebRequest`, `urllib`).
- Subagents: their calls must go through the hook too; check that the registration covers this.
- Editing the hook itself, its registration or its state files.

Forged paperwork:
- An `approved: true` field, a verdict filled in by hand, a verdict from a different file with the same name.
- The checked file swapped after the check (TOCTOU): caught by comparing the sha at the moment of release and after the copy.
- A re-encoded or renamed copy of the checked file.
- A plan seal applied after the result.

## 4. Building rules

1. A refusal always explains the path: what is forbidden, which path is permitted, what to read, who can lift it.
2. A hook always exits with code 0 and returns the refusal as a structure (`permissionDecision: deny`), not by crashing. In some harnesses a crashed hook is a silent pass.
3. On a production action a parse error means a refusal. On everything else it means a pass with a line in the log.
4. `HOOK_SMOKE=1` (or an equivalent) means the hook writes nothing; this is for tests and CI.
5. A hook does not call a model synchronously on every call. The judge works in the background, its verdict arrives in the context, and the hook only compares a ready verdict.
6. The hook's state lives in a separate folder, and the hook itself forbids the agent's tools from writing there.
7. Hook tests run under the same conditions as in the harness (the same output encoding, the same interpreter). A hook that writes in a different encoding under test "works" in the test and stays silent in the field.
8. After editing hooks, run all hook tests, not only your own.
9. Every lock faces the historical defect: the old bad file is refused, and the reference sample passes.
10. An item where no lock is added gets a reason with a check: a command and its output showing why it is not needed here.

## 5. How to tell that a lock checks paperwork

Ask three questions about every lock:
1. Who writes what the lock reads? If it is the executor, the lock checks paperwork.
2. Is the check tied to the content (a sha, recognized text, a count) or to a name and a field?
3. Is there a way to deliver the product to the consumer without passing this lock? List the doors from section 3 and find a test for each.

If even one answer is bad, the lock is converted to type 2.2 or 2.4, and the executor's field becomes a sign-off by quote.
