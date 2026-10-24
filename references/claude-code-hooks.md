# Хуки Claude Code для замков

Короткая шпаргалка под замки. Формат событий и полей со временем меняется: перед постройкой сверь с актуальной документацией Claude Code (раздел hooks) и проверь живым прогоном.

## Регистрация

Проектная (`.claude/settings.json` или `.claude/settings.local.json`) или пользовательская (`~/.claude/settings.json`):

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

- `matcher` = регулярка по имени инструмента. Инструменты MCP называются `mcp__<сервер>__<инструмент>`: их легко забыть, и тогда загрузка через браузер или терминал приложения идёт мимо замка.
- На Windows интерпретатор может называться `python`, `python3` или `py`, а `python` бывает заглушкой магазина, которая ничего не запускает. Надёжная команда перебирает варианты и проверяет, что интерпретатор живой:
  `sh -c 'F="$CLAUDE_PROJECT_DIR/.claude/hooks/guard_hook.py"; for P in python3 python py; do if command -v "$P" >/dev/null 2>&1 && "$P" -c "" >/dev/null 2>&1; then PYTHONIOENCODING=utf-8 exec "$P" "$F"; fi; done; echo "ЗАМОК НЕ РАБОТАЕТ: не найден python"; exit 0'`.
  Если интерпретатора нет, хук говорит об этом вслух, а не молча пропускает производство.
- Вывод хука в UTF-8 (`PYTHONIOENCODING=utf-8` или перенастройка stdout в коде), иначе кириллица в причине отказа превращается в мусор или в пустой ответ.

## Вход (stdin, JSON)

Общие поля: `session_id`, `transcript_path`, `cwd`, `hook_event_name`.
- PreToolUse и PostToolUse: `tool_name`, `tool_input` (для Bash `command`, для Write `file_path` и `content`, для Edit `file_path`, `old_string`, `new_string`), у PostToolUse ещё ответ инструмента.
- UserPromptSubmit: `prompt`.
- SessionStart: `source` (`startup`, `resume`, `clear`, `compact`).
- PreCompact: `trigger` (`manual`, `auto`).

## Выход

- Отказ PreToolUse: код 0 и в stdout
  `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "что запрещено и какой путь разрешён"}}`.
  Причину отказа модель видит и по ней идёт законным путём, поэтому пиши в причину путь, а не только «нельзя».
- Подмешать контекст (UserPromptSubmit, SessionStart): `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}`.
- Не дать закончить ход (Stop): `{"decision": "block", "reason": "чего не хватает в ответе"}`. Пример: в ходе было производство, а в ответе нет строки, какие правила применены.
- Код выхода 2 тоже блокирует (stderr уходит модели), но структурный ответ надёжнее и читается одинаково на всех событиях.

## Приёмы, которые окупились

- **Журнал сессии в файле состояния хука.** PostToolUse на `Read` засчитывает, какие строки файла прочитаны; PreToolUse на производстве сверяет «прочитано целиком в текущей эпохе». SessionStart с `compact` начинает новую эпоху: чтения до сжатия не в счёт.
- **PreCompact пишет состояние задачи** (последние реплики владельца, план, прочитанное, папка работы, незакоммиченное) в файл, SessionStart с `compact` печатает его обратно первым блоком.
- **Гейт фокуса.** UserPromptSubmit подмешивает последние 5 реплик владельца: ни одно требование не теряется молча после длинной работы.
- **Фоновый судья.** Запись файла плана (`WORKFLOW*.md`) запускает судью в фоне, вердикт пишется в файл рядом с планом с полем `plan_sha`. Хук сверяет `plan_sha` с текущим файлом: вердикт по старой версии не открывает замок.
- **Stop-сверка заявлений.** Если ответ называет прочитанные файлы или пройденные станции, хук сверяет названное с журналом и файлами на диске. Назвал, а в журнале нет = блок с перечнем расхождений.
- **Тест харнеса.** Каждый хук гоняется подачей JSON в stdin, как это делает харнес (`scripts/test_hook.py`), включая кодировку и переменные окружения.
