export const meta = {
  name: 'draft-tradegen-plans',
  description: 'For each plan: apply round-2 rulings to its contract, draft every task with full code, adversarially review and revise each, then cross-check consistency and fix',
  phases: [
    { title: 'Rulings', detail: 'fold the round-2 rulings into each contract' },
    { title: 'Draft', detail: 'one drafter per task group, chained where code builds on code' },
    { title: 'Review', detail: 'adversarial reviewer per task: scope, contract, runnable code, guards, tests' },
    { title: 'Revise', detail: 'apply review findings to each task file' },
    { title: 'Consistency', detail: 'cross-task names, signatures, edits, fixtures, ordering' },
    { title: 'Fix', detail: 'apply consistency findings' },
  ],
}

const ROOT = 'C:/Users/whydi/OneDrive/Desktop/TRADEGEN'
const PY = ROOT + '/.venv/Scripts/python.exe'
const SCR = 'C:/Users/whydi/AppData/Local/Temp/claude/C--Users-whydi-OneDrive-Desktop-TRADEGEN/b1492ead-23f3-4704-b198-5b5fc445ad00/scratchpad'
const OP = SCR + '/odds_plan'
const CPLAN = ROOT + '/docs/superpowers/plans/2026-10-23-compliance-gate.md'
const PLANS = args

const DRAFT_SCHEMA = { type: 'object', properties: {
  tasks: { type: 'array', items: { type: 'object', properties: {
    n: { type: 'integer' }, path: { type: 'string' }, summary: { type: 'string' },
    produces: { type: 'string' }, open_issues: { type: 'array', items: { type: 'string' } } },
    required: ['n', 'path', 'summary', 'produces', 'open_issues'] } },
}, required: ['tasks'] }
const REVIEW_SCHEMA = { type: 'object', properties: {
  n: { type: 'integer' },
  issues: { type: 'array', items: { type: 'object', properties: {
    severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, location: { type: 'string' },
    problem: { type: 'string' }, fix: { type: 'string' }, evidence: { type: 'string' } }, required: ['severity', 'location', 'problem', 'fix'] } },
  verified: { type: 'array', items: { type: 'string' } },
}, required: ['n', 'issues', 'verified'] }
const CONS_SCHEMA = { type: 'object', properties: { issues: { type: 'array', items: { type: 'object', properties: {
  tasks: { type: 'array', items: { type: 'integer' } }, problem: { type: 'string' }, fix: { type: 'string' } },
  required: ['tasks', 'problem', 'fix'] } } }, required: ['issues'] }

function rules(p) {
  return `HARD RULES FOR YOU:
- Do NOT modify anything under ${ROOT} (no edits, no new files, no git commands that write, no pip). Write ONLY inside ${p.dir}.
- Never touch C:/Users/whydi/OneDrive/Desktop/QUANTGEN, ~/.nextgen or the real ~/.tradegen. Never read the VALUES in ${ROOT}/.env. Never run tests/run_all.py or any repo test suite. No network calls (never call KIS, Upbit, OKX, Binance, Yahoo).
- You may read any repo file, run read-only shell commands, and run Python snippets with ${PY} -I from a scratch directory you create under ${p.dir}/sandbox_<yourname>/ (to ast.parse code, to try a pure function you wrote against small inputs, or to introspect a repo function; cryptography 49.0.0, numpy, scipy are installed in that venv).
- READ FIRST: ${p.dir}/CONTRACT.md (binding), ${p.dir}/TASKS.md (scope), ${p.dir}/header.md, the rulings ${p.rulings.join(', ')} (later files amend earlier ones), the spec(s) ${p.specs.join(', ')}, and the parts of ${OP}/map/DIGEST.md and ${OP}/map/*.md relevant to your task (verified repo facts with file:line evidence). Read the actual repo files you modify or call before writing code that touches them. The finished compliance plan ${CPLAN} is the model for task text quality (read its Task 7 once).
- THIS PLAN EXECUTES LATER THAN IT IS WRITTEN: ${p.order}. Write every Edit of an existing file as an exact old-text/new-text pair quoted from the CURRENT tree, AND name its anchor (function or block) so the executor can apply the DRIFT RULE in the contract's Global Constraints if an earlier plan moved the text.`
}

function format(p) {
  return `TASK TEXT FORMAT (writing-plans skill; follow exactly):
### Task N: <Component Name>

**Files:**
- Create: \`exact/path\` (LF)
- Modify: \`exact/path\` (anchor: <function or block>; LF or CRLF)
- Test: \`tests/<file>.py\`

**Interfaces:**
- Consumes: <exact names/signatures from earlier tasks or the contract>
- Produces: <exact names/signatures later tasks rely on>

**Plan decisions used:** <decision ids from CONTRACT section 1>

- [ ] **Step 1: Write the failing test(s)** — full test code in a python block (append-to-file instructions say exactly where).
- [ ] **Step 2: Run to verify it fails** — the QUANTGEN overlap check, then the exact command (${p.cmd}), and the expected failure text.
- [ ] **Step 3: Implement** — COMPLETE code. A new file: the whole file. An existing file: the exact old text and new text for an Edit-tool replacement (enough surrounding lines to be unique), its anchor, and the line ending to keep.
- [ ] **Step 4: Run to verify it passes** — exact command and expected \`N/N passed, 0 failed, 0 not run\`.
- [ ] **Step 5: Commit** — \`git add <files>\`, then \`git diff --cached --stat\` must equal \`git diff --cached --stat --ignore-cr-at-eol\`, then \`git commit -m "<conventional subject>" -m "<one-line body>" -m "Co-Authored-By: <the model that wrote the commit> <noreply@anthropic.com>"\`.
A task may repeat Steps 1-4 for several cycles before its commit. No placeholders: no TBD/TODO, no "add validation", no "similar to Task N", no ellipses standing for code, no undefined names. Every code block must be complete, syntactically valid Python 3.13 (verify with ast.parse in your sandbox), and where it is pure logic, actually run it on small inputs in your sandbox. Code must pass every guard in CONTRACT section 0 (grep your own text for CANO in upper case (so never CANONICAL), private_key, seed_phrase, order_cash, place_order, submit_order, the KIS order TR ids, "0.4 *", reference_mode, context_log/, and the other banned strings). Match the repo's style (terse docstrings, \`from __future__ import annotations\`, frozen kw_only dataclasses, zero-argument test functions with assert; no pytest).`
}

function draftPrompt(p, tasks, extra) {
  return `${rules(p)}\n\n${format(p)}\n\nYOUR JOB: write the complete plan text for Task(s) ${tasks.join(' and ')} of the ${p.label} implementation plan, as scoped in ${p.dir}/TASKS.md, against ${p.dir}/CONTRACT.md. Write each task to its own file ${p.dir}/tasks/task_NN.md (two digits). ${extra || ''}\nBe exhaustive and exact: the implementer has zero context and copies your code. Cover every bullet of the task's scope with a test that fails before and passes after. Where the contract and the repo disagree about a repo fact, follow the repo and report it in open_issues. Return the files you wrote.`
}

const results = {}
for (const p of PLANS) {
  phase('Rulings')
  await agent(`${rules(p)}\n\nYOUR JOB: the latest rulings file (${p.rulings[p.rulings.length - 1]}) amends earlier decisions. Fold every ruling in it that concerns the ${p.label} plan into ${p.dir}/CONTRACT.md, ${p.dir}/TASKS.md and ${p.dir}/header.md (edit them in place; keep numbering and the coverage tables consistent; add the DRIFT RULE to Global Constraints if it is not there). Append a list of what you changed to ${p.dir}/REVISIONS.md. Return a one-paragraph summary.`, { label: `rulings:${p.key}`, phase: 'Rulings' })

  const drafted = await pipeline(p.groups, async (g) => {
    const first = await agent(draftPrompt(p, g.tasks), { label: `draft:${p.key}:${g.tasks.join('+')}`, phase: 'Draft', schema: DRAFT_SCHEMA })
    if (!g.then) return first ? first.tasks : []
    const second = await agent(draftPrompt(p, g.then, `Task(s) ${g.tasks.join(', ')} are already drafted in ${p.dir}/tasks/: read them first and build exactly on their code (same names, same helpers, same fixtures). Where your task changes a file an earlier task created, quote the earlier task's exact text as the old text.`), { label: `draft:${p.key}:${g.then.join('+')}`, phase: 'Draft', schema: DRAFT_SCHEMA })
    return [...(first ? first.tasks : []), ...(second ? second.tasks : [])]
  }, (tasks) => parallel(tasks.map(t => async () => {
    const review = await agent(`${rules(p)}\n\nYOU ARE AN ADVERSARIAL REVIEWER of ${t.path} (Task ${t.n} of the ${p.label} plan). Assume it is wrong until checked. Report every problem with a concrete fix:\n1. Scope: every bullet for Task ${t.n} in ${p.dir}/TASKS.md and the spec sections and rulings it cites has a test that would fail before and pass after.\n2. Contract: names, signatures, file paths, reason strings, data formats exactly as ${p.dir}/CONTRACT.md (or the repo, where the contract is wrong about the repo).\n3. Runnable code: extract EVERY python code block into ${p.dir}/sandbox_review${t.n}/ and ast.parse it with ${PY} -I; for pure logic, actually execute it in the sandbox against small inputs and report real failures (wrong numbers, exceptions, off-by-one, wrong rounding). Check that every Edit old-text exists verbatim in the current repo file (read it) or in the earlier task's text it builds on, and that line endings are right.\n4. Guards: grep the code destined for core/, execution/ or data/ for every banned string and pattern in CONTRACT section 0 (upper-case CANO including CANONICAL, private_key, seed_phrase, order verbs and KIS order TR ids, .post/.put/.delete/.patch/.request where banned, wall-clock calls outside the allowed main(), imports outside the allowlist, file I/O where banned, "0.4 *").\n5. Test design: tests really exercise the behaviour (no tautologies), save/restore every patched global, never write outside the temp home, never call the network, never need a TTY, and fit the stated time budget.\n6. Placeholders and undefined names.\n7. Commands: exact, with the QUANTGEN overlap check before test runs and qa/acceptance_results.json restored after --suite runs.\nRank blocker > major > minor; list what you verified.`, { label: `review:${p.key}:${t.n}`, phase: 'Review', schema: REVIEW_SCHEMA })
    const issues = review ? review.issues : []
    if (!issues.length) return { ...t, review_count: 0, revised: 'no issues' }
    const revised = await agent(`${rules(p)}\n\n${format(p)}\n\nYOU ARE REVISING ${t.path} (Task ${t.n} of the ${p.label} plan). A reviewer found:\n${JSON.stringify(issues, null, 1)}\n\nFor each issue: verify it yourself (it may be wrong); if right, fix the task file in place (rewrite it with the Write tool); if wrong, leave the text and say why. Re-run ast.parse on every python block, and re-execute the pure logic you changed, in ${p.dir}/sandbox_revise${t.n}/. Return a short summary: fixed, rejected (why).`, { label: `revise:${p.key}:${t.n}`, phase: 'Revise' })
    return { ...t, review_count: issues.length, blockers: issues.filter(i => i.severity === 'blocker').length, revised }
  })))
  const all = drafted.flat().filter(Boolean)
  log(`${p.key}: ${all.length} task drafts reviewed and revised`)

  const cons = await agent(`${rules(p)}\n\nYOU ARE THE CROSS-TASK CONSISTENCY CRITIC for the ${p.label} plan drafts ${p.dir}/tasks/task_*.md (read every one in full, plus CONTRACT.md and TASKS.md). Find every inconsistency: a name, signature, field, constant, reason string, fixture, test module, file path or data format that a later task uses differently from how an earlier task defines it, or that no task defines; an Edit whose old text an earlier task already changed (the later Edit would fail as written); MODULES-list and fixture additions that collide; a test in an earlier task that a later task's change breaks without updating it; ordering problems (a task using something produced later); scope bullets of TASKS.md that no task covers; commit steps that would add files another task owns. For each: the tasks involved and the exact fix. Be exhaustive.`, { label: `consistency:${p.key}`, phase: 'Consistency', schema: CONS_SCHEMA })
  const cIssues = cons ? cons.issues : []
  log(`${p.key}: ${cIssues.length} consistency issues`)
  const byTask = {}
  for (const i of cIssues) for (const n of i.tasks) (byTask[n] = byTask[n] || []).push(i)
  const fixes = await parallel(Object.keys(byTask).map(n => () => agent(`${rules(p)}\n\n${format(p)}\n\nYOU ARE FIXING ${p.dir}/tasks/task_${String(n).padStart(2, '0')}.md for these cross-task consistency findings (other task files are fixed in parallel by other agents for the same findings; fix only YOUR file, choosing the fix described, so all files converge):\n${JSON.stringify(byTask[n], null, 1)}\nVerify each against the other task files (read them), apply the fix, ast.parse every python block in ${p.dir}/sandbox_fix${n}/, and return a summary.`, { label: `fix:${p.key}:${n}`, phase: 'Fix' })))
  results[p.key] = { tasks: all.map(t => ({ n: t.n, path: t.path, review_count: t.review_count, blockers: t.blockers, open_issues: t.open_issues })), consistency: cIssues.length, fixed_files: Object.keys(byTask).length, fix_summaries: fixes.filter(Boolean).map(s => String(s).slice(0, 400)) }
}
return results