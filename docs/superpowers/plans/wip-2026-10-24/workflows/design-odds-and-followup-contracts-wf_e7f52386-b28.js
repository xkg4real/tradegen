export const meta = {
  name: 'design-odds-and-followup-contracts',
  description: 'Draft the binding contract and task scope for the odds plan and the compliance follow-up plan, attack them with lens critics, then revise',
  phases: [
    { title: 'Contract', detail: 'one drafter per plan writes CONTRACT.md, TASKS.md and header.md' },
    { title: 'Critique', detail: 'lens critics: math/stats, repo-fit, spec+rulings coverage (odds); one critic (follow-up)' },
    { title: 'Revise', detail: 'each drafter applies or rejects every finding' },
  ],
}

const ROOT = 'C:/Users/whydi/OneDrive/Desktop/TRADEGEN'
const PY = ROOT + '/.venv/Scripts/python.exe'
const SCR = 'C:/Users/whydi/AppData/Local/Temp/claude/C--Users-whydi-OneDrive-Desktop-TRADEGEN/b1492ead-23f3-4704-b198-5b5fc445ad00/scratchpad'
const OP = SCR + '/odds_plan'
const SPEC = ROOT + '/docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md'
const CPLAN = ROOT + '/docs/superpowers/plans/2026-10-23-compliance-gate.md'
const LEDGER = ROOT + '/docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md'
const OLD = SCR + '/plan_drafts'

const RULES = `HARD RULES FOR YOU:
- Do NOT modify anything under ${ROOT} (no edits, no new files, no git commands that write, no pip). Write ONLY inside ${OP}.
- Never touch C:/Users/whydi/OneDrive/Desktop/QUANTGEN, ~/.nextgen or the real ~/.tradegen. Never run tests/run_all.py or any whole suite. No network calls.
- You may read any repo file, run read-only shell commands, and run Python snippets with ${PY} -I (cwd ${ROOT} for repo imports; introspection and small pure computations only; never call a network function) from a scratch dir under ${OP}/sandbox_<yourname>/.
- BINDING INPUTS: ${OP}/RULINGS.md (owner and controller rulings; follow them; if you find hard evidence one is wrong or impossible, keep it, and report the evidence and a proposed fix in open_issues), the spec ${SPEC} (rev 3.2; the rulings override it where they say so), the verified repo facts in ${OP}/map/DIGEST.md (and the per-area files in ${OP}/map/), and the execution ledger ${LEDGER}.
- FORMAT MODELS: the compliance plan's contract and scope files ${OLD}/CONTRACT.md, ${OLD}/TASKS.md, ${OLD}/header.md, and the finished plan ${CPLAN} (its header with Global Constraints and plan decisions P1-P39, one full task such as Task 7, and Appendix A). Mirror their structure, density and exactness.`

const DRAFT_SCHEMA = { type: 'object', properties: {
  files: { type: 'array', items: { type: 'string' } },
  task_count: { type: 'integer' },
  decisions: { type: 'array', items: { type: 'string' }, description: 'each plan decision as "Q<n>: one line" (odds) or "F<n>-P<n>: one line" (follow-up)' },
  open_issues: { type: 'array', items: { type: 'string' } },
}, required: ['files', 'task_count', 'decisions', 'open_issues'] }

const CRIT_SCHEMA = { type: 'object', properties: {
  lens: { type: 'string' },
  issues: { type: 'array', items: { type: 'object', properties: {
    severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, location: { type: 'string' },
    problem: { type: 'string' }, fix: { type: 'string' }, evidence: { type: 'string' } },
    required: ['severity', 'location', 'problem', 'fix'] } },
  verified: { type: 'array', items: { type: 'string' } },
}, required: ['lens', 'issues', 'verified'] }

const ODDS_DIR = OP + '/odds'
const FU_DIR = OP + '/followup'

const ODDS_JOB = `YOUR JOB: write the binding CONTRACT and the TASK SCOPE for the TRADEGEN ODDS implementation plan (the second of the spec's two plans), into ${ODDS_DIR}/:
1. ${ODDS_DIR}/CONTRACT.md: section 0 Global rules (copy the still-valid A.0 rules of the compliance plan: python path, no pytest, the QUANTGEN overlap check in both PowerShell and Git Bash forms, qa/acceptance_results.json restore, LF for new files and the CRLF list, Edit-tool only, never sed -i, diff --stat check, commit trailer "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" naming the model that wrote the commit, branch odds-engine, every guard that binds core/odds and core/oddsdata with its exact forbidden strings, the O1 import allowlist); section 1 Plan decisions Q1..Qn (every RULINGS item O1-O15 restated as a numbered decision with its source: OWNER, CONTROLLER, or a new decision you must make where spec + rulings are still silent; list every remaining DIGEST design question DQ1-DQ32 and say which decision answers it); section 2 Files (every file created or modified, LF/CRLF, signed or unsigned); then one section per module with EXACT public names, signatures, dataclass fields, constants with values, reason strings, flag names, data formats (bars input arrays, the injected inputs object, the replay output, the OddsReport fields, the sentence catalogue keys and their slots), and the test harness (tests/odds_acceptance.py MODULES, _wrap, seams patched, fixtures, CHUNK swapping). Decide everything an implementer would otherwise guess: the simulator's state machine per path (cash, units, entry, bracket levels, lock state, daily-loss stop, re-entry at the next check point, AT_FLOOR absorption, REACHED stop on moonshot), the cost ledger per fill, the affordability rules per scenario (base and 2x stress, carry), bold() stake formula with lot rounding, the two-point kernel with bands and ticks and limit-down locks, the GARCH-t path, edge tilt by bisection, delisting stress columns, the outcome ladder (D4: P(+10%), P(+25%), P(2x), P(10x), P(target), median, 5th percentile, P(floor)), HIDDEN_EDGE and CEILING_BREACH computations, Clopper-Pearson, model spread members, the seed derivation byte layout, provenance fields. Use real repo names and signatures only (verify each in the repo; the DIGEST gives file:line evidence).
2. ${ODDS_DIR}/TASKS.md: the task list in the format of ${OLD}/TASKS.md: each task's scope bullets, files, the spec 8 "odds" items 1-9 and the RULINGS items it covers, and its verify commands. Right-size tasks (each independently testable and reviewable; about 12-18 tasks; the compliance-side prerequisites of O3 come first; the wiring and guards task first of all; the D13 replay, bars and the CLI in the unsigned package; the final task is a full-suite run, README rows (CRLF) and the hand-off to execution E1). Every spec 8 odds item and every RULINGS item must map to at least one task: add a coverage table at the end.
3. ${ODDS_DIR}/header.md: the plan header in the writing-plans format (title "TRADEGEN odds engine Implementation Plan", the agentic-workers line, Goal, Architecture, Tech Stack, Spec, Global Constraints copied from CONTRACT section 0, the plan decisions list), plus the real-odds and not-advice statements the project requires ("No plan without a real edge that keeps this floor can beat 1 in N"; "not legal or investment advice; not a licensed advisor").
Verify every numeric claim you can with ${PY} -I in your sandbox (bold_even values, the 2,005-KRW floor, Clopper-Pearson k=0 at n=1e6, the KRX session counts, the S_C3 replay digests if cheap). Return the files, the task count, the decision list and open issues.`

const FU_JOB = `YOUR JOB: write the binding CONTRACT and TASK SCOPE for the TRADEGEN COMPLIANCE FOLLOW-UP (hardening) implementation plan into ${FU_DIR}/: CONTRACT.md (section 0 Global rules as for the compliance plan but branch compliance-followup; section 1 decisions R1..Rn restating RULINGS F1-F8 with exact before/after values; section 2 Files; one section per change with the exact old text locations (path:line, verified in the current tree) and the exact new rule text, reason strings and test names), TASKS.md (about 5-8 tasks in the ${OLD}/TASKS.md format, each with scope bullets, files and verify commands, plus a coverage table mapping F1-F8 and the "not in scope" items), and header.md (title "TRADEGEN compliance follow-up Implementation Plan", writing-plans header, Goal, Architecture, Tech Stack, Spec, Global Constraints, the decisions list, and the statement that no owner signature exists yet so nothing needs re-signing now, while after owner act 2 every closure change needs a fresh code_approved). The source facts are ${OP}/map/followup.md (read it in full) and the DIGEST section 8. Verify every line reference in the current tree. Return the files, the task count, the decision list and open issues.`

phase('Contract')
const [odds, fu] = await parallel([
  () => agent(RULES + '\n\n' + ODDS_JOB, { label: 'draft:odds-contract', phase: 'Contract', schema: DRAFT_SCHEMA }),
  () => agent(RULES + '\n\n' + FU_JOB, { label: 'draft:followup-contract', phase: 'Contract', schema: DRAFT_SCHEMA }),
])
log(`odds: ${odds ? odds.task_count : 'FAILED'} tasks; follow-up: ${fu ? fu.task_count : 'FAILED'} tasks`)

const LENSES = [
  { key: 'math', prompt: `LENS: mathematics and statistics. Check the contract's simulator, kernel, bands, locks, cost ledger, affordability, bold() and Kelly formulas, the no-edge law (E[next|p]=p exactly, including tick-clamped edges), the tilt, HIDDEN_EDGE (range R, empirical Bernstein with delta 1e-4, resolution wording), CEILING_BREACH (one-sided Clopper-Pearson at 95% and at 1-0.001/m with m defined), the ceiling (W0-L_min)/(T-L_min) with L_min per sizing, structural_max with the half-open session count, the outcome ladder, the precision wording, the model spread, and the seeds/streams against spec sections 3, 7 and 8 "odds". Recompute numbers yourself with ${PY} -I. Find every formula that is wrong, ambiguous, or would let a no-edge plan look better than the ceiling allows.` },
  { key: 'repo', prompt: `LENS: repo fit. Check every name, signature, path, constant and line reference the contract uses against the current tree (read the files; run introspection). Check the O1 layout against owner.code_files (the D14 closure) and tests/compliance_store.py:137-150 and tests/compliance_signer.py:638; every guard that binds core/odds and core/oddsdata (tests/compliance_guards.py, tests/macro_m0_harness.py T-RO-01, test_08/test_09, T-CTX-01, T-TF-GOV-06 "0.4 *", the CANO substring, reference_mode, context_log/); the venues.yaml parser change against rules.py and every byte/shape pin in tests/compliance_tables.py and tests/compliance_gate.py; the harness wiring (tests/run_all.py CRLF, compliance_acceptance.py pattern, hermetic(), seams); line endings; the copied code's equality tests (do the originals have the claimed signatures and constants?). Report everything that would fail to run or break an existing test.` },
  { key: 'coverage', prompt: `LENS: spec, rulings and task coverage. Map every spec section 7 requirement, every spec 8 "odds" test item 1-9, every spec 9 odds error rule, every spec 10 guardrail row that the odds engine shows, and every RULINGS item O1-O15 to the contract and to a task in TASKS.md. Report gaps, contradictions between contract and rulings, tasks that are too big or depend on later tasks, missing refusal reasons or flags, missing report wording (the exact sentences of spec 7.5 and 7.4, the base rates of spec 3 with their dates, the "not in these numbers" list, the footer, the language guard words), and any place the plan would print a probability from a refused run. Also check the plan states the real odds and the not-advice line.` },
]

phase('Critique')
const oddsCrit = odds ? (await parallel(LENSES.map(l => () => agent(RULES + `\n\nYOU ARE AN ADVERSARIAL CRITIC of the odds plan contract drafts in ${ODDS_DIR}/ (CONTRACT.md, TASKS.md, header.md). Assume they are wrong until checked. ` + l.prompt + ' Rank issues blocker > major > minor, each with a concrete fix and evidence.', { label: 'critic:odds-' + l.key, phase: 'Critique', schema: CRIT_SCHEMA })))).filter(Boolean) : []
const fuCrit = fu ? await agent(RULES + `\n\nYOU ARE AN ADVERSARIAL CRITIC of the compliance follow-up contract drafts in ${FU_DIR}/. Check every line reference and old-text location against the current tree, that every new ban/rule leaves core/compliance and the shipped tables VALID and the existing tests green except the ones the plan deliberately rewrites (name them), that nothing loosens spec 5.2/6.4/D11/D12, that F1-F8 are all covered, that the guard additions bind core/odds correctly (DYNAMIC_* scans core/odds too: would any odds-plan module need a newly banned module? the odds core imports only stdlib, numpy, scipy, core.isolation, core.compliance), and that the "not in scope" list is complete. Rank issues blocker > major > minor with fixes and evidence.`, { label: 'critic:followup', phase: 'Critique', schema: CRIT_SCHEMA }) : null

phase('Revise')
const REV = (dir, crits, what) => agent(RULES + `\n\nYOU ARE REVISING the ${what} drafts in ${dir}/ (CONTRACT.md, TASKS.md, header.md). Critics found these issues:\n${JSON.stringify(crits, null, 1)}\n\nFor each issue: verify it yourself against the repo, spec and RULINGS (it may be wrong). If right, fix the files in place. If wrong, leave the text and say why. Keep the files internally consistent after your edits (names, numbering, coverage table). Then append to ${dir}/REVISIONS.md a table: issue, verdict (fixed / rejected / partly), one-line reason. Return the files, final task count, decisions and remaining open issues.`, { label: 'revise:' + what, phase: 'Revise', schema: DRAFT_SCHEMA })
const [oddsRev, fuRev] = await parallel([
  () => (odds && oddsCrit.length) ? REV(ODDS_DIR, oddsCrit.map(c => ({ lens: c.lens, issues: c.issues })), 'odds') : Promise.resolve(null),
  () => (fu && fuCrit) ? REV(FU_DIR, [{ lens: fuCrit.lens, issues: fuCrit.issues }], 'follow-up') : Promise.resolve(null),
])
const count = cs => cs.reduce((a, c) => { for (const i of c.issues) a[i.severity] = (a[i.severity] || 0) + 1; return a }, {})
return {
  odds: { draft: odds, critics: count(oddsCrit), revised: oddsRev },
  followup: { draft: fu, critics: fuCrit ? count([fuCrit]) : null, revised: fuRev },
}