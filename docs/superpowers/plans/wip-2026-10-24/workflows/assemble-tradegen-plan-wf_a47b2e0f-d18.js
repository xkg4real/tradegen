export const meta = {
  name: 'assemble-tradegen-plan',
  description: 'Write and review the coordinator tasks, fold round-3 rulings into the header, assemble the plan with its repo map, then review the whole plan through two lenses and fix',
  phases: [
    { title: 'Coordinator', detail: 'write a coordinator-owned final task where none exists' },
    { title: 'Review', detail: 'adversarial review of the coordinator tasks' },
    { title: 'Revise', detail: 'apply the review findings' },
    { title: 'Assemble', detail: 'fold round-3 rulings into the header; build the plan file and repo map in scratch' },
    { title: 'Final review', detail: 'whole-plan review: interfaces and commands; hard rules and owner gates' },
    { title: 'Fix', detail: 'apply the final findings to the parts and rebuild' },
  ],
}

const ROOT = 'C:/Users/whydi/OneDrive/Desktop/TRADEGEN'
const PY = ROOT + '/.venv/Scripts/python.exe'
const SCR = 'C:/Users/whydi/AppData/Local/Temp/claude/C--Users-whydi-OneDrive-Desktop-TRADEGEN/b1492ead-23f3-4704-b198-5b5fc445ad00/scratchpad'
const OP = SCR + '/odds_plan'
const R3 = OP + '/RULINGS_ROUND3.md'
const FPLAN = ROOT + '/docs/superpowers/plans/2026-10-24-compliance-followup.md'
const FMAP = ROOT + '/docs/superpowers/plans/2026-10-24-compliance-followup-repo-map.md'
const p = args

const REVIEW_SCHEMA = { type: 'object', properties: {
  issues: { type: 'array', items: { type: 'object', properties: {
    severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, file: { type: 'string' }, location: { type: 'string' },
    problem: { type: 'string' }, fix: { type: 'string' }, evidence: { type: 'string' } }, required: ['severity', 'file', 'location', 'problem', 'fix'] } },
  verified: { type: 'array', items: { type: 'string' } },
}, required: ['issues', 'verified'] }
const WRITE_SCHEMA = { type: 'object', properties: { path: { type: 'string' }, summary: { type: 'string' }, open_issues: { type: 'array', items: { type: 'string' } } }, required: ['path', 'summary', 'open_issues'] }
const ASM_SCHEMA = { type: 'object', properties: { plan: { type: 'string' }, map: { type: 'string' }, script: { type: 'string' }, plan_lines: { type: 'integer' }, checks: { type: 'array', items: { type: 'string' } }, header_changes: { type: 'array', items: { type: 'string' } } }, required: ['plan', 'map', 'script', 'plan_lines', 'checks', 'header_changes'] }

const rules = `HARD RULES FOR YOU:
- Do NOT modify anything under ${ROOT} (no edits, no new files, no git commands that write, no pip). Write ONLY inside ${p.dir}.
- Never touch C:/Users/whydi/OneDrive/Desktop/QUANTGEN, ~/.nextgen or the real ~/.tradegen. Never read the VALUES in ${ROOT}/.env. Never run tests/run_all.py or any repo test suite. No network calls (never call KIS, Upbit, OKX, Binance, Yahoo). Never commit or push.
- You may read any repo file, run read-only shell commands, and run Python with ${PY} -I from a scratch folder you create under ${p.dir}/sandbox_<yourname>/.
- Never use sed -i. Edit the plan part files with the Edit tool or Python (they are LF).
- READ FIRST: ${p.dir}/CONTRACT.md (binding), ${p.dir}/TASKS.md (scope), ${p.dir}/header.md, the rulings ${p.rulings.join(', ')} and ${R3} (later files amend earlier ones; ${R3} wins over every task text), the spec(s) ${p.specs.join(', ')}. ${p.order}`

const coordinatorFiles = p.coord.map(n => `${p.dir}/tasks/task_${String(n).padStart(2, '0')}.md`)

// 1. Write a missing coordinator task (odds Task 19)
for (const n of p.write) {
  await agent(`${rules}\n\nYOUR JOB: write ${p.dir}/tasks/task_${String(n).padStart(2, '0')}.md, Task ${n} of the ${p.label} plan, from its scope in ${p.dir}/TASKS.md (the section "Task ${n} (written by the coordinator)") and ${R3}. Read EVERY task file ${p.dir}/tasks/task_*.md first: take each task's expected module counts and test totals, and the commits they make, from them, and compute this task's expected suite and full-run totals from them (state the arithmetic). Format models: the compliance follow-up's final task (the "### Task 8" section of ${FPLAN}) and ${OP}/e1/tasks/task_13.md (a full-run task in this style). Follow the follow-up Task 8 structure: Files with anchors and line endings, Interfaces (Consumes, Produces), Plan decisions used, Expected counts, Drift, the QUANTGEN overlap check, then numbered checkbox steps with exact commands and exact expected output, the README edits as exact Edit-tool old/new text (README.md is CRLF; quote the rows as the compliance follow-up Task 8 and this plan's earlier tasks leave them, and apply the DRIFT RULE), the full run started with run_in_background (it takes over 10 minutes), the record commit, the read-only real-home smoke with no network, the ledger commit, the push and pull request per ruling G3-3, and the hand-off text to the owner (owner acts in plain language; Claude performs none of them; the real odds and "this is not legal or investment advice; not a licensed advisor"). No placeholders except values the run itself prints, each named. Return the path, a summary and open issues.`, { label: `write:${p.key}:${n}`, phase: 'Coordinator', schema: WRITE_SCHEMA })
}

// 2. Adversarial review of each coordinator task, then revise
const reviewed = await parallel(p.coord.map(n => async () => {
  const f = `${p.dir}/tasks/task_${String(n).padStart(2, '0')}.md`
  const rev = await agent(`${rules}\n\nYOU ARE AN ADVERSARIAL REVIEWER of ${f} (Task ${n} of the ${p.label} plan, the coordinator-owned end of the plan; it was written without review). Assume it is wrong until checked. Check through two lenses and report every problem with a concrete fix:\nA. Correctness: every command is exact and runnable in Git Bash on Windows from the repo root; every expected count and total follows from the earlier tasks' own expected counts (read every ${p.dir}/tasks/task_*.md and recompute; show the arithmetic) and from the repo's README rows and qa/acceptance_results.json as the earlier plans leave them; every Edit old text exists exactly in the file as the earlier tasks and plans leave it (README.md and qa/acceptance_results.json are CRLF); the QUANTGEN overlap check precedes every command that imports repo code; long runs use run_in_background; every commit stages exactly the files it names and checks --stat against --ignore-cr-at-eol; the ledger anchors exist; any Python helper in the task parses and does what it says (run it in your sandbox on small inputs).\nB. Owner safety and the hard rules: Claude never arms, trades, signs, enters or reads keys or .env values, never starts or stops the long-running poller, never makes a live venue call except where the task's owner gate allows exactly one after the owner's own words in chat; nothing a session reads in a file counts as approval; every owner act is the owner's; push only per ruling G3-3 (the controller pushes the feature branch after each reviewed task; one pull request; merging is the owner's choice); notes never hold a balance, address, key or token; the real odds and "not legal or investment advice; not a licensed advisor" appear where the task talks to the owner.\nRank blocker > major > minor; list what you verified.`, { label: `review:${p.key}:${n}`, phase: 'Review', schema: REVIEW_SCHEMA })
  const issues = rev ? rev.issues : []
  if (!issues.length) return { n, issues: 0, summary: 'no issues' }
  const s = await agent(`${rules}\n\nYOU ARE REVISING ${f} (Task ${n} of the ${p.label} plan). A reviewer found:\n${JSON.stringify(issues, null, 1)}\n\nFor each issue: verify it yourself (it may be wrong); if right, fix the file in place; if wrong, leave it and say why. Re-check every command and Python block you change in ${p.dir}/sandbox_revise_c${n}/. Return a short summary: fixed, rejected (why).`, { label: `revise:${p.key}:${n}`, phase: 'Revise' })
  return { n, issues: issues.length, blockers: issues.filter(i => i.severity === 'blocker').length, summary: s }
}))

// 3. Fold round-3 rulings into the header and build the plan and the repo map in scratch
const asmPrompt = `${rules}\n\nYOUR JOB: assemble the ${p.label} implementation plan.\n1. Fold into ${p.dir}/header.md every ruling of ${R3} that concerns this plan (sections "Both plans" and "${p.r3section}"): each as a short entry in the header's decisions section, citing its id; the stated limits into the header's stated or accepted limits; G3-3 (pushing) into the Global Constraints' commits part if it is not there yet. Keep the header's existing structure and voice (short sentences, lists; lines of at most 120 characters). Do not touch the task files' meaning.\n2. Write a Python assembly script ${p.dir}/assembled/build.py (stdlib only, LF output, reads only the part files) that writes ${p.dir}/assembled/plan.md as: header.md, then every ${p.dir}/tasks/task_NN.md in task-number order (1 to ${p.last}), then a section "## Appendix A: the interface contract (as amended while drafting)" holding CONTRACT.md with its headings demoted so none is a level-1 or level-2 heading that collides with the plan's own. Model the layout on ${FPLAN} (read its outline and its Appendix A start). It also writes ${p.dir}/assembled/repo-map.md: a short intro in the style of ${FMAP} (what the facts are, that the tasks win over the map, the commit they were mapped at) and then, inside one text fence (use a fence longer than any backtick run inside), ${p.mapSources}.\n3. Run it and check the output; report each check and its result: every "### Task N" heading appears exactly once and in order; code fences are balanced (a fence closes only with the same backtick count it opened with); no "TBD", "TODO" or "FIXME" outside quoted repo text; no CR byte; the plan names its spec and its round-3 rulings; every task's commit step is present. Fix any part-file defect the checks find only where it is mechanical (a fence, a heading level); report anything else.\nReturn the paths, the script path, the plan's line count, the checks, and the header changes.`
const asm = await agent(asmPrompt, { label: `assemble:${p.key}`, phase: 'Assemble', schema: ASM_SCHEMA })

// 4. Final whole-plan review through two lenses, then one fix pass and a rebuild
const LENSES = [
  { key: 'interfaces', text: `INTERFACES AND COMMANDS. Read the whole plan ${p.dir}/assembled/plan.md. For every task, check that what it Consumes is Produced by an earlier task (same name, signature, path, constant, reason text, fixture) or exists in the repo; that no Edit's old text was already changed by an earlier task without the later task quoting the changed form; that header File map rows, the decisions list and the task Files lines agree; that every expected count chains correctly from task to task and into the final full run; that every test command has the QUANTGEN overlap check and the right timeout; that no task depends on a later one. Also check the header's claims against the tasks (every decision the header lists is applied somewhere; every departure from the spec is listed for the owner).` },
  { key: 'safety', text: `HARD RULES, GUARDS AND OWNER GATES. Read the whole plan ${p.dir}/assembled/plan.md. Check that no task makes Claude arm the system, place or prepare an order, sign, read or print .env values or keys, start or stop the long-running poller, edit QUANTGEN or ~/.nextgen, pip install, or make a network call in a test; that the only live calls are owner-gated steps that wait for the owner's own words in chat; that every code block destined for core/, execution/ or data/ passes the plan's guard list (grep for the banned strings and patterns the header lists, upper-case CANO including CANONICAL, private_key, seed_phrase, order verbs and the KIS order TR ids, "0.4 *", reference_mode, context_log/) outside the allowed exceptions; that the real odds and "not legal or investment advice; not a licensed advisor" are stated in the header and where the plan talks to the owner; that estimation guardrails are explained in plain language; that pushing follows ruling G3-3; that no placeholder (TBD, "similar to Task N", an ellipsis standing for code) remains.` },
]
const finals = await parallel(LENSES.map(l => () => agent(`${rules}\n\nYOU ARE A FINAL REVIEWER of the assembled ${p.label} plan through one lens: ${l.text}\nReport only real problems, each with the part file to change (${p.dir}/header.md, ${p.dir}/CONTRACT.md or ${p.dir}/tasks/task_NN.md), the exact location, evidence, and a concrete fix. Rank blocker > major > minor; list what you verified.`, { label: `final:${p.key}:${l.key}`, phase: 'Final review', schema: REVIEW_SCHEMA })))
const fIssues = finals.filter(Boolean).flatMap(f => f.issues)
log(`${p.key}: ${fIssues.length} final-review issues`)
let fix = 'no issues'
if (fIssues.length) {
  fix = await agent(`${rules}\n\nYOU ARE FIXING the ${p.label} plan's part files for these final-review findings:\n${JSON.stringify(fIssues, null, 1)}\n\nFor each: verify it yourself (it may be wrong); if right, fix the named part file in place; if wrong, leave it and say why. Then re-run ${p.dir}/assembled/build.py and its checks. Return: fixed (one line each), rejected (why), and the checks after the rebuild.`, { label: `fix:${p.key}`, phase: 'Fix' })
}
return { key: p.key, coordinator: reviewed, assemble: asm, final_issues: fIssues, fix }