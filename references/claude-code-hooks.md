# Claude Code hooks for locks

A short cheat sheet for building locks. The format of events and fields changes over time: before building, compare with the current Claude Code documentation (the hooks section) and verify with a live run.

## Registration

Per project (`.claude/settings.json` or `.claude/settings.local.json`) or per user (`~/.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit",
       "hooks": [{"type": "command", "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard_hook.py\"", "timeout": 60}]},
      {"matcher": "mcp__.*__file_upload|mcp__.*browser.*|mcp__computer-use__.*",
       "hooks": [{"type": "command", "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/upload_gate.py\""}]}
    ],
    "SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": [{"type": "command", "command": "..."}]}],
    "PreCompact": [{"hooks": [{"type": "command", "command": "..."}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "..."}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "..."}]}]
  }
}
```

- `matcher` is a regex over the tool name. MCP tools are named `mcp__<server>__<tool>`: they are easy to forget, and then an upload through the browser or an application's terminal goes around the lock.
- On Windows the interpreter may be called `python`, `python3` or `py`, and `python` can be a Store stub that runs nothing. A reliable command tries the variants and checks that the interpreter is alive:
  `sh -c 'F="$CLAUDE_PROJECT_DIR/.claude/hooks/guard_hook.py"; for P in python3 python py; do if command -v "$P" >/dev/null 2>&1 && "$P" -c "" >/dev/null 2>&1; then PYTHONIOENCODING=utf-8 exec "$P" "$F"; fi; done; echo "LOCK NOT WORKING: python not found"; exit 0'`.
  If there is no interpreter, the hook says so out loud and does not silently let production through.
- The hook's output is UTF-8 (`PYTHONIOENCODING=utf-8` or reconfiguring stdout in the code); otherwise non-ASCII text in the refusal reason turns into garbage or an empty answer.

## Input (stdin, JSON)

Common fields: `session_id`, `transcript_path`, `cwd`, `hook_event_name`.
- PreToolUse and PostToolUse: `tool_name`, `tool_input` (for Bash `command`; for Write `file_path` and `content`; for Edit `file_path`, `old_string`, `new_string`); PostToolUse also has the tool's response.
- UserPromptSubmit: `prompt`.
- SessionStart: `source` (`startup`, `resume`, `clear`, `compact`).
- PreCompact: `trigger` (`manual`, `auto`).

## Output

- A PreToolUse refusal: exit code 0 and, on stdout,
  `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "what is forbidden and which path is permitted"}}`.
  The model sees the refusal reason and follows it onto the legitimate path, so put the path into the reason, not just "not allowed".
- Adding context (UserPromptSubmit, SessionStart): `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}`.
- Keeping the turn from ending (Stop): `{"decision": "block", "reason": "what is missing from the answer"}`. Example: the turn included production, but the answer has no line saying which rules were applied.
- Exit code 2 also blocks (stderr goes to the model), but a structured answer is more reliable and reads the same on every event.

## Techniques that paid off

- **A session log in the hook's state file.** PostToolUse on `Read` records which lines of a file were read; PreToolUse on production checks "read in full in the current epoch". SessionStart with `compact` starts a new epoch: reads from before compaction do not count.
- **PreCompact writes the task state** (the owner's latest messages, the plan, what was read, the working folder, uncommitted changes) to a file, and SessionStart with `compact` prints it back as the first block.
- **The focus gate.** UserPromptSubmit adds the owner's last 5 messages: no requirement gets silently lost after a long stretch of work.
- **A background judge.** Writing a plan file (`WORKFLOW*.md`) starts the judge in the background, and the verdict is written to a file next to the plan with a `plan_sha` field. The hook compares `plan_sha` with the current file: a verdict on an old version does not open the lock.
- **A Stop check of claims.** If the answer names files that were read or stations that were passed, the hook compares what was named with the log and the files on disk. Named but not in the log means a block with the list of discrepancies.
- **A harness test.** Every hook is run by feeding JSON to stdin the way the harness does (`scripts/test_hook.py`), including the encoding and the environment variables.
