// Пример сценария веера для инструмента Workflow в Claude Code (фаза АУДИТ, около 10 агентов).
// Запуск только по прямому слову владельца, цену назвать до запуска.
// args: { dir: "C:/work/audit-2026-10-24", sectors: [{ id: "C1", name: "Сборка и выпуск", hint: "что проверить" }, ...] }
// SCOPE.md и words/OWNER_WORDS.jsonl готовятся до запуска (шаги 0-2 SKILL.md).
export const meta = {
  name: 'audit-lock-audit',
  description: 'Аудит контура: чтецы участков и слов владельца, проверяющий с заверением другой моделью, карта и отчёт',
  phases: [{ title: 'Чтецы' }, { title: 'Проверка' }, { title: 'Сборка' }],
}

const DIR = args.dir
const COMMON = `Прочитай целиком ${DIR}/SCOPE.md: принцип, участки и законы аудита (только чтение, опора путь:строка на каждое утверждение).
Нарушение законов SCOPE = провал. Слова владельца: ${DIR}/words/OWNER_WORDS.jsonl.
Отчёт запиши в указанный файл. Если запись запрещена, верни весь текст в поле fallback_text.`

const FIND = {
  type: 'object',
  properties: {
    file_written: { type: 'string' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['высокая', 'средняя', 'низкая'] },
      title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['id', 'severity', 'title', 'evidence'] } },
    outside_gate: { type: 'array', items: { type: 'object', properties: {
      law: { type: 'string' }, where: { type: 'string' }, why: { type: 'string' } }, required: ['law', 'where'] } },
    fallback_text: { type: 'string' },
  },
  required: ['findings', 'outside_gate'],
}

phase('Чтецы')
const readers = await parallel([
  ...args.sectors.map(s => () => agent(
    `${COMMON}\nТВОЙ УЧАСТОК ${s.id}: ${s.name}. ${s.hint}\nСтруктура: assets/part.template.md скила audit-lock. Отчёт: ${DIR}/parts/${s.id}.md`,
    { label: s.id, phase: 'Чтецы', schema: FIND })),
  () => agent(`${COMMON}\nТЫ ЧТЕЦ СЛОВ ВЛАДЕЛЬЦА: законы и просьбы с датой и цитатой, где держатся (замок / текст / нигде), ` +
    `противоречия, просьбы без исполнения. Отчёт: ${DIR}/parts/W_WORDS.md`, { label: 'W', phase: 'Чтецы', schema: FIND }),
])
const got = readers.filter(Boolean)
log(`чтецов вернулось ${got.length} из ${args.sectors.length + 1}`)

phase('Проверка')
const verify = await agent(`${COMMON}\nТЫ ПРОВЕРЯЮЩИЙ. Каждую высокую и среднюю находку перепроверь с диска своими командами, ` +
  `сначала попытайся опровергнуть; низкие выборочно (не меньше трети); дубли сведи. Список «вне замков» отдай модели другого ` +
  `семейства (scripts/cross_judge.py), ответ дословно в ${DIR}/parts/CROSS_ATTEST.md. Отчёт ${DIR}/parts/VERIFY.md.\n` +
  `НАХОДКИ: ${JSON.stringify(got.map(r => ({ findings: r.findings, outside_gate: r.outside_gate, file: r.file_written })))}`,
  { label: 'V', phase: 'Проверка', schema: { type: 'object', properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' },
      verdict: { type: 'string', enum: ['ПОДТВЕРЖДЕНО', 'ЧАСТИЧНО', 'ОПРОВЕРГНУТО', 'НЕ ПРОВЕРЕНО'] }, note: { type: 'string' } },
      required: ['id', 'verdict'] } } }, required: ['verdicts'] } })

phase('Сборка')
const report = await agent(`${COMMON}\nТЫ СБОРЩИК. Прочитай все ${DIR}/parts/*.md. Запиши ${DIR}/BRANCH_MAP.json по схеме ` +
  `references/audit-method.md раздел 4 и прогони scripts/map_check.py; ${DIR}/AUDIT.md по assets/AUDIT.template.md ` +
  `(в проблемы только ПОДТВЕРЖДЕНО и ЧАСТИЧНО); ${DIR}/SUMMARY.md по assets/SUMMARY.template.md.\n` +
  `ВЕРДИКТЫ: ${JSON.stringify(verify ? verify.verdicts : [])}`,
  { label: 'R', phase: 'Сборка', schema: { type: 'object', properties: { summary_text: { type: 'string' },
    map_check: { type: 'string' } }, required: ['summary_text'] } })

return { readers: got.length, verdicts: verify ? verify.verdicts.length : 0, summary: report ? report.summary_text : null }
