export const meta = {
  name: 'design-e1-contract',
  description: 'Draft the binding contract and task scope for the E1 account-inquiry plan, attack it with lens critics, then revise',
  phases: [
    { title: 'Contract', detail: 'drafter writes CONTRACT.md, TASKS.md and header.md' },
    { title: 'Critique', detail: 'lens critics: order-path safety, repo-fit, spec coverage' },
    { title: 'Revise', detail: 'the drafter applies or rejects every finding' },
  ],
}

const ROOT = 'C:/Users/whydi/OneDrive/Desktop/TRADEGEN'
const PY = ROOT + '/.venv/Scripts/python.exe'
const SCR = 'C:/Users/whydi/AppData/Local/Temp/claude/C--Users-whydi-OneDrive-Desktop-TRADEGEN/b1492ead-23f3-4704-b198-5b5fc445ad00/scratchpad'
const OP = SCR + '/odds_plan'
const DIR = OP + '/e1'
const SPEC = ROOT + '/docs/superpowers/specs/2026-10-24-e1-account-inquiry-design.md'
const MAIN = ROOT + '/docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md'
const CPLAN = ROOT + '/docs/superpowers/plans/2026-10-23-compliance-gate.md'
const LEDGER = ROOT + '/docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md'
const OLD = SCR + '/plan_drafts'

const RULES = `HARD RULES FOR YOU:
- Do NOT modify anything under ${ROOT} (no edits, no new files, no git commands that write, no pip). Write ONLY inside ${DIR}.
- Never touch C:/Users/whydi/OneDrive/Desktop/QUANTGEN, ~/.nextgen or the real ~/.tradegen. Never read the VALUES in ${ROOT}/.env (names only, if needed). Never run tests/run_all.py or any whole suite. No network calls of any kind (never call KIS, Upbit or OKX).
- You may read any repo file, run read-only shell commands, and run small Python snippets with ${PY} -I from ${DIR}/sandbox_<yourname>/.
- BINDING INPUTS: the APPROVED spec ${SPEC} (rev 1), the rulings ${OP}/E1_RULINGS.md (they fill the spec's gaps; if you find hard evidence one is wrong, keep it and report evidence plus a fix in open_issues), the main spec ${MAIN} (rev 3.2) for the gate's rules, the repo facts in ${OP}/map/execution_ctx.md and ${OP}/map/DIGEST.md section 9, the venue research ${OP}/venues/kis.md, upbit.md, okx.md (the skeptic's "Verification" section at the end of each overrides the body where it says WRONG), and the ledger ${LEDGER}.
- FORMAT MODELS: ${OLD}/CONTRACT.md, ${OLD}/TASKS.md, ${OLD}/header.md and the finished compliance plan ${CPLAN} (header, Global Constraints, a full task such as Task 7, Appendix A).`

const SCHEMA = { type: 'object', properties: {
  files: { type: 'array', items: { type: 'string' } }, task_count: { type: 'integer' },
  decisions: { type: 'array', items: { type: 'string' } }, open_issues: { type: 'array', items: { type: 'string' } },
}, required: ['files', 'task_count', 'decisions', 'open_issues'] }
const CRIT = { type: 'object', properties: {
  lens: { type: 'string' },
  issues: { type: 'array', items: { type: 'object', properties: {
    severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, location: { type: 'string' },
    problem: { type: 'string' }, fix: { type: 'string' }, evidence: { type: 'string' } }, required: ['severity', 'location', 'problem', 'fix'] } },
  verified: { type: 'array', items: { type: 'string' } },
}, required: ['lens', 'issues', 'verified'] }

const JOB = `YOUR JOB: write the binding CONTRACT and TASK SCOPE for the TRADEGEN E1 (read-only account inquiry) implementation plan into ${DIR}/:
1. CONTRACT.md: section 0 Global rules (python path, no pytest, the QUANTGEN overlap check in PowerShell and Git Bash forms, qa/acceptance_results.json restore, LF for new files and the exact CRLF list (tests/acceptance.py and tests/run_all.py and README.md are CRLF; verify with git ls-files --eol), Edit-tool only, never sed -i, the diff --stat check, commit trailer naming the model that wrote the commit, branch e1-account-inquiry, the DRIFT RULE of ruling X1, every guard that binds execution/ with exact strings, the never-live rule: no test and no plan step makes a network call except the owner-gated first live --once poll at the very end); section 1 Plan decisions E<n> restating every ruling X1-X9 plus any new decision you must make (each with its source); section 2 Files (create/modify, LF/CRLF, signed or not); then one section per module with EXACT public names, signatures, dataclasses and fields, constants with values, the three allowlists written out in full (venue, method, path, TR id for KIS, host), reason strings, the snapshot/evidence/alert record formats, the sentence catalogue keys and templates, the check table with exact thresholds, the evidence fold rules with the Seoul-date boundary, the gate and owner changes with the anchors to edit (quote them from the current tree), and the test harness (MODULES, _wrap, seams, fixtures with response shapes taken from the research tables).
2. TASKS.md: about 10-14 right-sized tasks in the ${OLD}/TASKS.md format, each with scope bullets, files, the spec sections and rulings it covers, and verify commands. Suggested order: wiring + guards scaffolding + runtime_py widening (with exceptions) first; keys + transport; KIS; Upbit; OKX; snapshot + positions; evidence + the compliance changes (Context.live_evidence, owner fold, gate rule, code_files seeds + signer lockstep + closure tests); checks; poller + alerts CLI; README/full run; the owner-gated final steps (scheduled-task prompt change shown for approval; the first live --once poll only after the owner says keys are in .env). Add a coverage table mapping every spec section 4-12 item and every ruling to a task.
3. header.md: the writing-plans header ("TRADEGEN E1 account inquiry Implementation Plan", the agentic-workers line, Goal, Architecture, Tech Stack, Spec, Global Constraints copied from CONTRACT section 0, the decisions list), the statement that E1 has no order code, the honest KIS point (a KIS key is an order key; only E1's code stands between a TRADEGEN process and an order), the real odds line ("No plan without a real edge that keeps this floor can beat about 1 in 1,000") and "not legal or investment advice; not a licensed advisor".
Verify every repo name, signature, constant and line anchor you use in the current tree. Return the files, task count, decisions, open issues.`

phase('Contract')
const draft = await agent(RULES + '\n\n' + JOB, { label: 'draft:e1-contract', phase: 'Contract', schema: SCHEMA })

const LENSES = [
  { key: 'safety', prompt: `LENS: order-path safety and secrets. Try to find ANY way the contract would let E1 send an order, a cancel, a transfer or a withdrawal, or leak a key: an allowlisted path that also serves a write on some method; a KIS TR that is not an inquiry; an Upbit or OKX endpoint that writes; a transport bypass (another module calling requests, a seam reachable from outside, redirects followed to another host, a params-in-path trick, header injection); the token POST being reusable for other paths; retries replaying a POST; keys reaching logs, exceptions, alert texts, snapshots, test output or the evidence file; guard exceptions that are wider than one file or than the named strings; a test that could make a live call. Check against the venue research files.` },
  { key: 'repo', prompt: `LENS: repo fit. Check every name, signature, path, constant, line anchor and line ending the contract uses against the current tree; the runtime_py widening against every caller of runtime_py and every test that would then scan execution/ (T-RO-01 lists, test_08, test_09, any other scanner of runtime_py or core/); the D14 closure change against owner.code_files, tools/signer/sign.py, tests/compliance_store.py:131-150, tests/compliance_signer.py:630-671; the Context field default against every Context construction (model.seal_context, owner.load_context, compliance_fixtures.ctx); the gate reason-text change against every test that pins the old reason; the token-file compatibility with data/krx/kis_client.py; T-CTX-01 with the new prefix; the harness wiring. Also judge the DRIFT RULE: which anchors will the follow-up and odds plans (scope in ${OP}/RULINGS.md) most likely move, and does the contract quote anchors robust to that?` },
  { key: 'coverage', prompt: `LENS: spec coverage and testability. Map every requirement of the approved E1 spec sections 4-12 (every table row, every check, every evidence rule, every guard change, every error rule, every owner act) and every ruling X1-X9 to the contract and to a task. Report gaps, contradictions with the spec, tasks too big or ordered wrongly, untestable requirements, missing exact values (thresholds, formats, reason strings), and any place the plan asks Claude to do an owner act.` },
]
phase('Critique')
const crits = draft ? (await parallel(LENSES.map(l => () => agent(RULES + `\n\nYOU ARE AN ADVERSARIAL CRITIC of the E1 contract drafts in ${DIR}/ (CONTRACT.md, TASKS.md, header.md). Assume they are wrong until checked. ` + l.prompt + ' Rank issues blocker > major > minor, each with a concrete fix and evidence.', { label: 'critic:e1-' + l.key, phase: 'Critique', schema: CRIT })))).filter(Boolean) : []

phase('Revise')
const rev = (draft && crits.length) ? await agent(RULES + `\n\nYOU ARE REVISING the E1 contract drafts in ${DIR}/. Critics found:\n${JSON.stringify(crits.map(c => ({ lens: c.lens, issues: c.issues })), null, 1)}\n\nFor each issue verify it yourself; fix the files in place if right, leave and explain if wrong. Keep the files consistent (names, numbering, coverage table). Append a table to ${DIR}/REVISIONS.md: issue, verdict, one-line reason. Return files, final task count, decisions, remaining open issues.`, { label: 'revise:e1', phase: 'Revise', schema: SCHEMA }) : null
const count = cs => cs.reduce((a, c) => { for (const i of c.issues) a[i.severity] = (a[i.severity] || 0) + 1; return a }, {})
return { draft, critics: count(crits), revised: rev }