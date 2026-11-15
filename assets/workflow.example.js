// An example fan-out script for the Workflow tool in Claude Code (the AUDIT phase, about 10 agents).
// Launch only on the owner's direct word, and name the cost before launch.
// args: { dir: "/work/audit-2026-10-24", sectors: [{ id: "C1", name: "Build and release", hint: "what to check" }, ...] }
// SCOPE.md and words/OWNER_WORDS.jsonl are prepared before launch (steps 0-2 of SKILL.md).
export const meta = {
  name: 'audit-lock-audit',
  description: 'Pipeline audit: readers of sections and of the owner\'s words, a verifier with a cross-model review, the map and the report',
  phases: [{ title: 'Readers' }, { title: 'Verification' }, { title: 'Assembly' }],
}

const DIR = args.dir
const COMMON = `Read ${DIR}/SCOPE.md in full: the principle, the sections and the laws of the audit (read only, support as path:line for every claim).
Breaking the laws of SCOPE means failure. The owner's words: ${DIR}/words/OWNER_WORDS.jsonl.
Write the report to the file named below. If writing is forbidden, return the whole text in the fallback_text field.`

const FIND = {
  type: 'object',
  properties: {
    file_written: { type: 'string' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['id', 'severity', 'title', 'evidence'] } },
    outside_gate: { type: 'array', items: { type: 'object', properties: {
      law: { type: 'string' }, where: { type: 'string' }, why: { type: 'string' } }, required: ['law', 'where'] } },
    fallback_text: { type: 'string' },
  },
  required: ['findings', 'outside_gate'],
}

phase('Readers')
const readers = await parallel([
  ...args.sectors.map(s => () => agent(
    `${COMMON}\nYOUR SECTION ${s.id}: ${s.name}. ${s.hint}\nStructure: assets/part.template.md of the audit-lock skill. Report: ${DIR}/parts/${s.id}.md`,
    { label: s.id, phase: 'Readers', schema: FIND })),
  () => agent(`${COMMON}\nYOU ARE THE READER OF THE OWNER'S WORDS: laws and requests with a date and a quote, where each is held (lock / text / nowhere), ` +
    `contradictions, requests never carried out. Report: ${DIR}/parts/W_WORDS.md`, { label: 'W', phase: 'Readers', schema: FIND }),
])
const got = readers.filter(Boolean)
log(`readers returned: ${got.length} of ${args.sectors.length + 1}`)

phase('Verification')
const verify = await agent(`${COMMON}\nYOU ARE THE VERIFIER. Re-check every high and medium finding from disk with your own commands, ` +
  `and try to refute it first; sample the low ones (at least a third); merge duplicates. Hand the "outside the locks" list to a model ` +
  `from a different family (scripts/cross_judge.py), with the answer verbatim in ${DIR}/parts/CROSS_ATTEST.md. Report: ${DIR}/parts/VERIFY.md.\n` +
  `FINDINGS: ${JSON.stringify(got.map(r => ({ findings: r.findings, outside_gate: r.outside_gate, file: r.file_written })))}`,
  { label: 'V', phase: 'Verification', schema: { type: 'object', properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' },
      verdict: { type: 'string', enum: ['CONFIRMED', 'PARTIAL', 'REFUTED', 'NOT CHECKED'] }, note: { type: 'string' } },
      required: ['id', 'verdict'] } } }, required: ['verdicts'] } })

phase('Assembly')
const report = await agent(`${COMMON}\nYOU ARE THE ASSEMBLER. Read all of ${DIR}/parts/*.md. Write ${DIR}/BRANCH_MAP.json following the schema in ` +
  `references/audit-method.md section 4 and run scripts/map_check.py; ${DIR}/AUDIT.md from assets/AUDIT.template.md ` +
  `(only CONFIRMED and PARTIAL go into the problems); ${DIR}/SUMMARY.md from assets/SUMMARY.template.md.\n` +
  `VERDICTS: ${JSON.stringify(verify ? verify.verdicts : [])}`,
  { label: 'R', phase: 'Assembly', schema: { type: 'object', properties: { summary_text: { type: 'string' },
    map_check: { type: 'string' } }, required: ['summary_text'] } })

return { readers: got.length, verdicts: verify ? verify.verdicts.length : 0, summary: report ? report.summary_text : null }
