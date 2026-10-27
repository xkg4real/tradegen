# Compliance follow-up plan: task list (scope of each task; the drafter writes the full task text)

"C<n>" means CONTRACT.md section n; "R<n>" a contract decision; "R2-<n>" a round-2 ruling (RULINGS_ROUND2.md). Spec
section numbers refer to rev 3.2. Line numbers are those of `995534b` (equal to `5816d3c` outside docs/). Every Edit
in the task text is an exact old/new pair quoted from that tree and names its anchor (function, constant, test, YAML
row or table row), and every task applies the DRIFT RULE of C0 (R2-13) before each Edit. Every task is
TDD: write or change the test, run it and see it fail for the stated reason, make the change, run it green, run the
compliance suite, restore `qa/acceptance_results.json`, commit. Run the QUANTGEN overlap check (C0) before every test
command. Module runs: `.venv/Scripts/python.exe -m tests.compliance_acceptance <module>/`. Suite runs:
`.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json`.

## Task 1: Branch and guards: xml.dom, string-exec modules, bare compile, the suite-list check (spec 4 "Guards"; R1, R7, R9; C3)
- Branch from main's HEAD at execution time, no pinned hash (R13, R2-11): on `main`, `git status --short` and
  `git diff --stat 995534b HEAD -- . ':!docs'` must both print nothing (today: one new docs file since `995534b`, and
  the plans' own docs commits join it); if either prints anything, stop and report. Then
  `git switch -c compliance-followup`.
- `tests/compliance_guards.py` (LF) only; no product file, no code-hash change:
  - `import re` (C3.1);
  - `NETWORK_MODULES` 22 -> 26 entries (C3.2): `xml.dom` replaces `xml.dom.pulldom`, `xml.dom.expatbuilder`; append
    `antigravity`, `ctypes`, `_ctypes`, `_ssl`, `_overlapped`;
  - the dynamic comment and constants (C3.3, old text quoted there): `DYNAMIC_MODULES` 9 -> 29 entries (`importlib`
    replaces `importlib.util`, `importlib.machinery`; add `profile, pdb, bdb, trace, doctest, unittest,
    logging.config, pickle, _pickle, shelve, marshal, site, ensurepip, venv, tkinter, _tkinter, turtle, turtledemo,
    idlelib`, then `pstats, tracemalloc` by R2-10), new `DYNAMIC_BARE = frozenset({"compile"})` and
    `DYNAMIC_EXEMPT = "importlib.metadata"`; the comment says why pstats and tracemalloc are banned (they load files
    with marshal and pickle) and why faulthandler stays allowed (it runs no string and opens nothing);
  - new `_dynamic_module(target)` and the new `_dynamic_hits` (C3.4): `from X import a` judged by `X.a` (R9), bare
    `compile` matched on `ast.Name` only, and an attribute of the name `importlib` other than `metadata` is a hit;
  - the `test_no_http_verb_calls` docstring rewritten (C3.5);
  - `test_no_forbidden_module_import`: the motivating positives, `import pstats`, `from pstats import Stats`,
    `import tracemalloc` and `from tracemalloc import Snapshot` among them, and a second negative control
    (traceback, faulthandler, logging, `re.compile`; no pstats or tracemalloc, R2-10) (C3.6);
  - `test_imports_stay_on_the_allowlist`: the xml.dom, antigravity, ctypes, _ssl, _overlapped positives;
    `from xml.dom import minidom` leaves the negative control (C3.7);
  - new `test_bare_compile_and_importlib_submodules_are_dynamic` (C3.8);
  - R7: `_suite_names(text)` and the rewritten `test_suite_is_registered_in_run_all_and_readme` (C3.9).
- Failing first: the new positives (`import xml.dom`, `from xml.dom import minidom`, `import pdb`, `import pstats`,
  `import tracemalloc`, `x = compile(...)`, `import importlib.resources`, `import importlib.metadata` then
  `importlib.util....`, ...) are not caught today (followup.md probe: all four checkers print no hit; pstats and
  tracemalloc are on no list today), so the extended tests and the new test fail before the lists change. R7 is a
  test refactor: its positive controls (a list without "compliance" is caught) prove the parser.
- Verify: `compliance_guards/` -> `16/16 passed, 0 failed, 0 not run`; `--suite compliance` -> 0 failed (318 rows,
  316 PASS, 2 NOT_RUN). The shipped-file asserts stay green (checked in-process 2026-10-24: no hit in
  core/compliance; core/odds has no .py file).
- Commit: `test(guards): ban xml.dom, string-exec modules and bare compile; read the suite lists`.

## Task 2: Loader: D15 and D16 by content, D15 rows blocking, review_by/max_leverage/{cap} bounds, exact row pins (spec 5.2 "Loading"; R2, R10; C4)
- `core/compliance/rules.py` (LF, closure file): the six constants after :405-406 (C4.1) and the five checks at their
  R10 places in `_row` (C4.2; check 4 reads a row with no class axis on an ETP asset as matching `etp_leveraged` and
  `etp_single_stock`), with the exact reason strings of C4.3.
- `tests/compliance_cli.py` (LF): the third deliberate rewrite, lines 576-577 of `test_render_has_no_rule_free_text`
  append `{cap}` to the grey row's warning only (C4.4). It passes before and after R2; without it R2 makes the test's
  mutated table Invalid at KR-KIS-US-OPTION (gated, per_session).
- `tests/compliance_tables.py` (LF):
  - the two deliberate flips first: tables:295 (`D160` gated etp_leveraged without live: now `_bad` with the
    D16-content reason, plus an `etp_1x` line keeping the "D160 is not D16" intent) and tables:316 (`{cap}` leaves the
    allow-row loop); `test_max_leverage` gains the bound cases;
  - new after tables:300: `test_d15_rows_never_let_credit_margin_lending_or_borrowing_through`,
    `test_a_d15_row_is_blocking`, `test_d16_by_content_needs_requires_live`,
    `test_review_by_is_not_before_the_latest_review`, `test_only_a_grey_row_states_a_cap` (C4.4);
  - new in the Task 5 block after tables:981: `_T5_PINNED` (C4.5, the 15 rows) and
    `test_shipped_rows_that_can_let_through_are_pinned_exactly`.
- The shipped table is not edited and stays VALID and byte-identical (sha `127a3c91...551bd3b79`). State in the task
  that R2 tightens the loader that re-parses every stored approval at every load_context (owner.py:960-961,
  rules.py:766-767): an approved table that broke R2 would turn INVALID. No approval exists today.
- Verify: `compliance_tables/` -> `64/65 passed, 0 failed, 1 not run` (REFDATA symlink); `compliance_cli/` ->
  `35/35 passed, 0 failed, 0 not run`; `compliance_gate/` and `compliance_store/` green (they parse the shipped
  table); `--suite compliance` -> 0 failed (324 rows). The C4 dry run on a sandbox copy matched this (shipped table
  VALID; the cli mutation Invalid as written, VALID as rewritten).
- Commit: `fix(compliance): loader refuses D15/D16 content, bounds review_by, max_leverage and {cap}; pin rows`.

## Task 3: The KR-KIS-KRX-DERIV reason names broker approval (ledger:118; R3; C5)
- `core/compliance/kr_rules.yaml:204` (LF): the one reason line of C5, nothing else.
- `tests/compliance_tables.py`: `test_shipped_d16_rows_need_live_evidence` gains the "broker approval" assertion
  after :959 (fails first).
- State: the table sha becomes `74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd`; the owner's
  first rules approval (owner act 3) is of these bytes; nothing pins the old sha. Do not touch the 2027-01-01
  affected_by item, any deposit network or the old plan document.
- Verify: `compliance_tables/` -> `64/65 passed, 0 failed, 1 not run`; `--suite compliance` -> 0 failed (324 rows).
- Commit: `fix(tables): KR-KIS-KRX-DERIV reason names broker approval`.

## Task 4: The D14 closure scan trusts a guard only while its name is unbound and unmutated (ledger:208; spec 6.4 "The code hash"; R4; C6)
- `core/compliance/owner.py` (LF, closure file) and `tools/signer/sign.py` (LF, off the closure), identical text:
  new `_guards(tree)` after `_typing_flag` (C6.1: the binding counts, and no guard at all in a module with an
  attribute store of TYPE_CHECKING or `__name__` or a setattr/delattr/globals/vars/locals/modules/`__dict__`/builtins
  route), `_skipped(node, guards)` (C6.2), `_import_nodes` takes `guards`, and `_repo_imports` passes `_guards(tree)`
  (C6.3; owner.py:755, sign.py:678).
- Tests (failing first): `tests/compliance_store.py` :153-194 and `tests/compliance_signer.py` :630-677 gain the ten
  synthetic files h.py to q.py and their ten targets (C6.4; today's owner.py hides all ten); new
  `test_closure_scan_helpers_are_identical_in_owner_and_signer` in tests/compliance_signer.py (fails first with
  AttributeError: no `_guards`).
- State: the real closure (10 entries) is unchanged and no closure file uses a mutation route (checked in-process
  2026-10-24); owner.py moves the code hash (no `code_approved` exists yet); sign.py changes need the owner act of C7
  (copy, re-hash, re-record). State the limit, which the controller accepts as stated (R2-12): the route list is a
  denylist, so another module changing `typing.TYPE_CHECKING` first, or a name built at run time, is not seen; the
  owner's diff review of the hashed files covers it.
- Verify: `compliance_store/` -> `29/29 passed`; `compliance_signer/` -> `38/38 passed, 0 failed, 0 not run`;
  `--suite compliance` -> 0 failed (325 rows).
- Commit: `fix(compliance): closure scan skips a guard only while its name is unbound and unmutated`.

## Task 5: The signer's ancestor walk fails closed (ledger:229, :233; spec 6.4 "Where it runs"; R5, R11; C7)
- `tools/signer/sign.py` (LF), repo copy only: `_SESSION_ROOTS` and the new `_has_claude_ancestor` (C7.1, replaces
  sign.py:758-767: the walk never stops at a session process; a break refuses unless one was passed); the refusal
  text at sign.py:810-811, one help bullet and the module docstring's sign.py:3 (C7.2). `_claude_ancestor` is
  unchanged.
- `tests/compliance_signer.py`: `test_claude_ancestor_walk` rewritten (two flips: the cycle and the empty table now
  refuse; the owner's Windows Terminal chain passes; an exited parent, the 256-step cap, an upper-case CLAUDE.EXE and a
  claude.exe above a process named winlogon.exe refuse); `test_claude_ancestor_check_fails_closed` gains the
  exited-parent case;
  `test_main_refuses_claude_parent_and_non_tty_stdin` asserts "has exited" in the refusal (C7.3).
- State the evidence for R11 in the task (the live chains of 2026-10-24), that every chain refused today stays
  refused, and the honest limits (COM activation and the desktop shell drop the claude.exe ancestor, so the passphrase
  and the typed code remain the barrier; a reused pid above a session process that now runs claude.exe refuses).
- Hand-off text for the owner (in the plan's owner-act list): owner act 1 is not done, so copy the merged sign.py
  then; if a copy already exists, read the diff of tools/signer/sign.py, re-hash it with certutil, re-record the hash
  on paper.
- Verify: `compliance_signer/` -> `38/38 passed, 0 failed, 0 not run`; `--suite compliance` -> 0 failed (325 rows).
- Commit: `fix(signer): the ancestor walk refuses when the chain breaks before a session process`.

## Task 6: alerts.jsonl records a fingerprint only from codes 0 to 2 (ledger:219; spec 6.4 "Public key and fingerprint"; P20; R6; C8)
- `core/compliance/alerts.py` (LF, closure file): `log()` blanks `row["fingerprint"]` when `summary["code"] > 2`,
  before the `_in_log` check; the docstring sentence of C8.
- `tests/compliance_cli.py`: new `test_log_records_a_fingerprint_only_from_codes_0_to_2` after :592-623 (fails first:
  the code-3 row records `SHA256:000...`).
- Verify: `compliance_cli/` -> `36/36 passed, 0 failed, 0 not run`; `--suite compliance` -> 0 failed (326 rows).
- Commit: `fix(alerts): record a key fingerprint only from a check that verified the log`.

## Task 7: Data-layer A0 minors: the KIS token target is checked before the POST; the ficc memory cache after the check (ledger:81, :82; spec 4 "Isolation residual"; R8, R12; C9)
- `data/krx/kis_client.py` (LF): one `checked_target(_TOKEN_PATH, "KIS token cache")` line in `token()` after the
  cache miss (:174-175) and before :176; `_store_token` keeps its own check.
- `core/ficc/data.py` (LF): `_cache_put` checks the target before `_MEM[key] = (now, rows)` (swap :273 and :274).
- `tests/compliance_isolation.py`: new `test_kis_token_is_refused_before_the_token_request` after :247-258 (no
  credential read, no POST, victim bytes unchanged; fails first with "token request failed"); the ficc test at
  :295-306 asserts the refused key is not in `D._MEM` (fails first).
- Both files are outside the D14 closure. State that R8 takes "KIS token burnt on refusal" off the execution carry list
  (ledger:239).
- Verify: `compliance_isolation/` -> `16/17 passed, 0 failed, 1 not run`; `--suite compliance` -> 0 failed (327 rows);
  then `--suite engine`, `--suite macro`, `--suite expansion`, `--suite ficc`, `--suite quant`, each 0 failed, restoring
  `qa/acceptance_results.json` after each.
- Commit: `fix(isolation): check the KIS token and ficc cache targets before side effects`.

## Task 8 (written by the coordinator, not a drafter): Full run, README, hand-off
- Full suite with the overlap check: `.venv/Scripts/python.exe tests/run_all.py; echo "exit $?"` -> 0 failed.
  Expected: compliance 327 rows (325 PASS / 2 NOT_RUN); full 1176 rows (1053 PASS / 123 NOT_RUN). The run's numbers
  win.
- `README.md` (CRLF, Edit tool): the compliance row's count (README.md:839) and the Total row (README.md:840), today's
  date; `git diff --stat` equals `--ignore-cr-at-eol`.
- Real-home `--check`: list `~/.tradegen/compliance`, run `.venv/Scripts/python.exe -m core.compliance.rules --check`,
  expect exit 3 and an unchanged listing.
- Commit `README.md` and `qa/acceptance_results.json`: `test: full run after the compliance follow-up`.
- The execution ledger `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` is the executor's,
  written during and after execution; the plan does not write it.
- Hand-off: the owner acts of this plan (copy the updated signer at owner act 1, or re-hash an existing copy; sign the
  code hash once at owner act 2, after the odds plan lands; approve the edited rules table at owner act 3); then merge
  per superpowers:finishing-a-development-branch and start the odds plan from the merged main.

## Coverage

F1 to F8 as amended by RULINGS_ROUND2 (R2-10 to R2-13); R2-1 to R2-9 concern the odds plan only.

| Ruling | Task(s) | Files | Proof |
|---|---|---|---|
| F1 guards (xml.dom; DYNAMIC additions incl. pstats and tracemalloc by R2-10; NETWORK additions; importlib except metadata; bare compile; controls, faulthandler negative; docstring) | 1 | tests/compliance_guards.py | extended `test_no_forbidden_module_import` (pstats and tracemalloc positives), `test_imports_stay_on_the_allowlist`; new `test_bare_compile_and_importlib_submodules_are_dynamic` |
| R2-11 branch base checked, not pinned | 1 | none (git only) | on `main`: `git status --short` and `git diff --stat 995534b HEAD -- . ':!docs'` print nothing before `git switch -c` |
| R2-12 R4 denylist limit accepted as stated | 4 | core/compliance/owner.py (docstring of `_guards`) | the stated limit in the task text and the `_guards` docstring |
| R2-13 DRIFT RULE | every task | every edited file | each Edit an exact old/new pair with its anchor; a one-line ledger ruling per drift |
| F2 loader (D15 content, D15 label, D16 content incl. ETP assets with no class axis, review_by, max_leverage, {cap}, 15 exact pins) | 2 | core/compliance/rules.py, tests/compliance_tables.py, tests/compliance_cli.py | five new loader tests, `test_shipped_rows_that_can_let_through_are_pinned_exactly`, three rewritten assertions (tables:295, :316; cli:576-577), extended `test_max_leverage` |
| F3 KRX-DERIV reason | 3 | core/compliance/kr_rules.yaml, tests/compliance_tables.py | extended `test_shipped_d16_rows_need_live_evidence` |
| F4 closure scan (owner.py + sign.py identical; binding and mutation routes) | 4 | core/compliance/owner.py, tools/signer/sign.py, tests/compliance_store.py, tests/compliance_signer.py | extended synthetic trees in both files; new `test_closure_scan_helpers_are_identical_in_owner_and_signer` |
| F5 ancestor walk fails closed (repo copy; owner act for the owner's copy) | 5 (owner act in 8) | tools/signer/sign.py, tests/compliance_signer.py | rewritten `test_claude_ancestor_walk`, extended `test_claude_ancestor_check_fails_closed`, refusal text |
| F6 fingerprint only from codes 0-2 | 6 | core/compliance/alerts.py, tests/compliance_cli.py | new `test_log_records_a_fingerprint_only_from_codes_0_to_2` |
| F7 suite-list check | 1 | tests/compliance_guards.py | rewritten `test_suite_is_registered_in_run_all_and_readme` with `_suite_names` controls |
| F8 KIS token before POST; ficc `_MEM` after the check | 7 | data/krx/kis_client.py, core/ficc/data.py, tests/compliance_isolation.py | new `test_kis_token_is_refused_before_the_token_request`; extended `test_ficc_cache_writer_refuses_a_hard_linked_target` |
| Final: full run, README row (CRLF), ledger by the executor | 8 | README.md, qa/acceptance_results.json | full run 0 failed; real-home `--check` exit 3, nothing written |

Not in scope (C11; the plan lists each with its reason): H2 (to E2, the execution halt writer with a trusted clock;
ledger:188, :239); T2 (a documented limit: the owner's key plus a backdated clock; ledger:189); the snapshot
cross-check (within spec 6.4's limits; ledger:204); every other item on the execution carry list (ledger:239 except
the KIS token item F8 takes, ledger:244, ledger:155); the deferred minors not ruled in (ledger:64, :70, :83, :86, :93,
:95, :96, :104, :107, :114, :123, :126, :158, :159, :169, :178-:180, :202, :203, :209, :216, :218, :220, :230, :231, and
the pem and keygen-text parts of :233); the ACCEPT items (DIGEST 8.5, and map/followup.md section 8: ledger:84, :102,
:116, :124, :125, :132, :136, :138, :161, :172, :196, :205); the execution-side :144, :150, :157; the odds-side
prerequisites (RULINGS O3) and notes (ledger:68, :101); the documented limits of DIGEST 8.2 and 8.4 (non-recursive D14
seeds, the core/calendars `__getattr__` re-export, `screen` and `effective_from`); the owner acts (OKX stablecoin
networks, ledger:112, :120; signing). Cited as already closed (C11): ledger:74, :80, :133, :145 (final wave, :238) and
:75, :242 (R1). Every other line of map/followup.md section 8 keeps its class there.
