# Compliance follow-up plan: interface contract (binding for every task drafter)

Repo: `C:\Users\whydi\OneDrive\Desktop\TRADEGEN` (git, tree clean, no other branch). Written against `main` at
`5816d3c`, which differs from `995534b` (the compliance merge) only by one new docs file
(`git diff --stat 995534b 5816d3c -- . ':!docs'` prints nothing, 2026-10-24). The plan executes first, from main's
HEAD after this plan, the odds plan and the E1 plan are committed there (docs only; Task 1 checks it, R13).
Spec: `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` rev 3.2. The owner approved it.
Rulings: `scratchpad/odds_plan/RULINGS.md` section "Compliance follow-up plan" (F1 to F8, controller rulings on the
parked and deferred items), amended by `scratchpad/odds_plan/RULINGS_ROUND2.md` R2-10 to R2-13 (where they differ,
round 2 wins). They are restated below as R1 to R8 with exact before and after values; R9 to R13 are the
readings this contract adds where a ruling is silent. Where a ruling and the spec differ, the ruling wins and is
listed for spec rev 3.3 (header, "Spec").
Repo facts: `scratchpad/odds_plan/map/followup.md` (sections 0-8) and `map/DIGEST.md` section 8. Every path:line
below was re-read in the tree at `995534b` on 2026-10-24; outside docs/ that tree is the tree at `5816d3c`, and the
docs files cited here (the spec, the ledger, the compliance plan) are unchanged since `995534b`.
Ledger: `docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md` (245 lines), cited as `ledger:<n>`.

Everything below is fixed. If a task needs a name that is not here, it defines it inside its own module as a private
helper (leading underscore) and says so in its Interfaces block. Never rename anything here.

## 0. Global rules (every task obeys these; the plan copies them into "Global Constraints")

- Python is `C:/Users/whydi/OneDrive/Desktop/TRADEGEN/.venv/Scripts/python.exe` (3.13.14). Never `pip install`
  anything: this plan adds no dependency. No pytest: a test is a zero-argument `test_*` function that raises on failure.
- One test or one module: `.venv/Scripts/python.exe -m tests.compliance_acceptance <module>/<test>` or
  `.venv/Scripts/python.exe -m tests.compliance_acceptance <module>/`. It prints
  `<passed>/<total> passed, <failed> failed, <not run> not run` and never writes `qa/acceptance_results.json`.
- One suite: `.venv/Scripts/python.exe tests/run_all.py --suite <name>; echo "exit $?"; git checkout -- qa/acceptance_results.json`
  from the repo root. A suite run rewrites the TRACKED, CRLF file `qa/acceptance_results.json`; restore it after every
  `--suite` run. Only the final full run (Task 8) commits it.
- Before every test command, check that no other python `run_all.py` is running (QUANTGEN shares the machine, and its
  Store Python runs as `python3.13.exe` with no `python.exe` beside it, so only a `python*` name filter sees it). It
  must print nothing; if it prints a process, wait; never run concurrently. PowerShell tool:
  `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`.
  Git Bash prefix (the PowerShell script in single quotes, so Bash does not expand `$_`):
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`.
- Line endings (`.gitattributes:2` is `* -text`). Every file this plan edits is LF (`git ls-files --eol`: `i/lf w/lf`)
  except `README.md`, which is CRLF and is edited only in Task 8. `tests/run_all.py` (CRLF) is NOT edited. Edit
  existing files only with the Edit tool, never `sed -i`. Git Bash `grep`/`sed` strip the CR on display (a CRLF
  README shows `grep -c $'\r'` = 0), so check endings with `git ls-files --eol <path>` or Python bytes, never grep.
  Before each commit: `git diff --cached --stat` must equal `git diff --cached --stat --ignore-cr-at-eol`.
- Work on branch `compliance-followup`, which Task 1 creates from main's HEAD at execution time (R13, RULINGS_ROUND2
  R2-11), never from a pinned hash. Before it branches, Task 1 checks on `main` that `git status --short` and
  `git diff --stat 995534b HEAD -- . ':!docs'` both print nothing (only docs changed since the compliance merge); if
  either prints anything, stop and report: every line number and count in this plan rests on that tree. Commit once
  per task with the repo-local identity (already set) and end each message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- DRIFT RULE (RULINGS_ROUND2 R2-13). Every Edit in a task is an exact old-text/new-text pair quoted from the tree at
  `5816d3c` and names its anchor: the function, constant, test, YAML row or table row it sits in. A cited line number
  is that of `995534b` (the same as `5816d3c` outside docs/) and only helps find the anchor; line numbers also shift
  as earlier tasks of this plan land (Task 2 before Tasks 3 and 6, Task 4 before Task 5), and then the anchor wins.
  Before each Edit, re-read the file. If the quoted old text differs only because an earlier plan changed it, apply
  the same change to the current text, keep the earlier behaviour, and record a one-line ruling in the execution
  ledger (`docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`); if the change no longer makes
  sense, stop and rule. This plan runs first, so outside docs/ no earlier plan has changed its files (Task 1's check);
  the odds and E1 plans carry the same rule for the files this plan changes (section 12).
- Guards that scan `core/**/*.py` stay exactly as in the compliance plan (Appendix A.0; raw text includes docstrings
  and comments): no upper-case `CANO` (so never `CANONICAL`), `KIS_ACCOUNT`, `ACNT_PRDT_CD`; no `order_cash`,
  `order-cash`, `place_order`, `submit_order`, `TTTC0802U`, `TTTC0801U`, `VTTC0802U`; no `private_key` or
  `seed_phrase` in any form; no def or call named `transfer`, `withdraw`, `deposit_address`; no `.post/.put/.delete/
  .patch/.request` in core/compliance; no wall-clock call in core/compliance outside the CLI `main()` of `rules.py`
  and `alerts.py`; the import allowlist for `core/compliance/*.py` (stdlib minus the network and dynamic modules,
  `yaml`, `cryptography` lazily inside functions, `core.isolation`, `core.compliance.*`). Task 1 widens two of these
  lists (R1); every later task's code must pass the widened lists.
- Every file the compliance code writes goes through `core.isolation.checked_target()` immediately before it is opened.
  Every text open passes `encoding="utf-8"`.
- Claude never runs `tools/signer/sign.py` with a real key, never asks for a passphrase, never writes to the real
  `~/.tradegen/compliance/owner.jsonl`. Tests load the signer with `importlib.util.spec_from_file_location` and sign
  only inside a temp `TRADEGEN_HOME` with the fixed test key. Never touch QUANTGEN or `~/.nextgen`.
- Code-hash bookkeeping. The D14 closure is `core/__init__.py`, `core/isolation.py`, `core/compliance/*.py`,
  `core/odds/*.py` (owner.py:773; tests/compliance_store.py:130-150). This plan changes three closure files
  (`core/compliance/rules.py` R2, `owner.py` R4, `alerts.py` R6), one table (`core/compliance/kr_rules.yaml` R3), the
  off-closure signer (`tools/signer/sign.py` R4, R5) and two off-closure loaders (`data/krx/kis_client.py`,
  `core/ficc/data.py` R8). No owner signature exists today (owner.py:24, no `owner_pubkey.pem`; ledger:240
  "real-home --check exit 3"), so none of this costs a re-sign now. After owner act 2 (the first `code_approved`), every
  later change to a closure file needs a fresh `code_approved`, and after owner act 3 every table byte change needs a
  fresh `approved {kind}`.

## 1. Decisions (R1-R8 restate F1-F8 as amended by R2-10 to R2-13; R9-R13 are this contract's readings)

Each task that implements one cites it as "Plan decision R<n>". None of them loosens anything.

- **R1 (F1, amended by R2-10) Guards, `tests/compliance_guards.py` only.** No product file, no code-hash change.
  - `NETWORK_MODULES` (guards:39-41). Before, 22 entries: `urllib, http, socket, _socket, socketserver, selectors, ssl,
    smtplib, ftplib, imaplib, poplib, nntplib, telnetlib, xmlrpc, asyncio, webbrowser, multiprocessing, wsgiref,
    xml.sax, xml.dom.pulldom, xml.dom.expatbuilder, logging.handlers`. After, 26 entries: the two `xml.dom.*` entries
    become one `xml.dom` (in place), and `antigravity, ctypes, _ctypes, _ssl, _overlapped` are appended.
  - `DYNAMIC_MODULES` (guards:50-51). Before, 9 entries: `importlib.util, importlib.machinery, runpy, pkgutil,
    zipimport, pydoc, timeit, code, cProfile`. After, 29 entries: the two `importlib.*` entries become one `importlib`
    (first), then `runpy, pkgutil, zipimport, pydoc, timeit, code, cProfile` as before, then `profile, pdb, bdb, trace,
    doctest, unittest, logging.config, pickle, _pickle, shelve, marshal, site, ensurepip, venv, tkinter, _tkinter,
    turtle, turtledemo, idlelib`, then `pstats, tracemalloc` (RULINGS_ROUND2 R2-10: their own APIs load files,
    `pstats.Stats` with marshal and `tracemalloc.Snapshot.load` with pickle; stricter than F1, which listed them as
    needing no ban). New constant `DYNAMIC_EXEMPT = "importlib.metadata"` (with everything below it).
  - The bare builtin `compile`: new constant `DYNAMIC_BARE = frozenset({"compile"})`, matched on `ast.Name` only, so
    `re.compile` (rules.py:383-386, owner.py:75-78, alerts.py:25-28) stays legal. `DYNAMIC_NAMES` (guards:49) is
    unchanged.
  - The negative control `from xml.dom import minidom` (guards:333) moves to the positive cases; the negative controls
    `import logging`, `from logging import getLogger`, `import xml.etree.ElementTree`, `from xml.etree import
    ElementTree`, `import subprocess`, `import importlib.metadata`, `from importlib import metadata` stay;
    `faulthandler` (and `traceback`, which the `trace` ban must not catch) join the negative controls, and the comment
    says why faulthandler stays allowed: it runs no string and opens nothing. `pstats` and `tracemalloc` are banned
    (R2-10, the controller's answer to round 1's open issue), so they are positive controls, never negative ones.
    Every new entry gets a positive control (the two loops at guards:292-294 and :319-322 cover each tuple entry in
    every import form; the motivating routes, `import pstats` and `import tracemalloc` among them, are listed
    explicitly too). The `test_no_http_verb_calls` docstring (guards:248-262) is rewritten (section 3.5).
  - Scope stays: NETWORK_MODULES binds core/compliance only (guards:340), DYNAMIC_* binds core/compliance and core/odds
    (guards:300-301). Checked on 2026-10-24 with the new lists run in-process: core/compliance (6 files) gives no hit,
    also with the importlib attribute rule of R9 and with the R2 and R4 versions of rules.py and owner.py;
    re-run with the 29-entry list of R2-10, still no hit (no repo file under core/, tools/ or tests/compliance_*
    imports pstats, tracemalloc or faulthandler); core/odds holds no .py file yet.
- **R2 (F2) Loader, `core/compliance/rules.py` `_row` (rules.py:440-538) and `tests/compliance_tables.py`.** Code-hash
  change. Before: a non-blocking (allow, gated or grey) row loads VALID with `financing: [cash, margin]`, `[credit]`,
  `action: [.., lend]` or `[borrow]`; a row citing D15 may be allow, gated or grey; a non-blocking row that matches
  `sell_short` or the class `etp_leveraged`, `etp_single_stock`, `krx_derivative`, `elw` (or the asset
  `krx_derivative`, `elw`) loads VALID without `requires.live` unless its policy_ref names D16 (rules.py:491,
  tables:295); `review_by` has no lower bound; `max_leverage` is any finite number > 0 (rules.py:486); `{cap}` is legal
  in every warning (rules.py:76, :484-485). After, each of these is Invalid with the reason of section 4.3:
  - D15 by content: a non-blocking row may not match financing `credit` or `margin`, nor action `lend` or `borrow`.
    `sell_short` is D16 (spec:70), never D15.
  - D15 by label: a row whose policy_ref names D15 is `hard_block` or `out_of_scope`.
  - D16 by content: a non-blocking row whose action includes `sell_short`, or whose class includes `etp_leveraged`,
    `etp_single_stock`, `krx_derivative` or `elw`, or whose asset includes `krx_derivative` or `elw`, needs a non-empty
    `requires.live`. A row with no `class` key that names the asset `krx_etp` or `us_etp` matches every class those
    assets derive to (gate.py:385-401 checks only the keys present; rules.py:213-224), so it counts as matching
    `etp_leveraged` and `etp_single_stock`. The label rule (rules.py:491-492, spec:299) stays.
  - Bounds: `review_by` is not before the row's latest review date; `max_leverage <= 10`; a `{cap}` slot appears only
    in a grey row's warning.
  - Exact pins of `(match, requires_owner, requires_live, treatment)` for all 15 shipped non-blocking rows
    (section 4.5), and the pinned id set equals the shipped non-blocking id set.
  - The shipped table stays VALID and byte-identical under R2 (read-only probe 2026-10-24: 47 rows; the 15 non-blocking
    rows are all `financing: [cash]`, none has lend or borrow; the 5 rows matching sell_short or a D16 class all carry
    live; no row names an ETP asset without a class axis; the D15 rows KR-KIS-CREDIT and KR-DOMESTIC-LENDING are
    out_of_scope; no review_by is before its review; max_leverage peaks at 3.0; only KR-OKX-SPOT has `{cap}`). Its
    sha stays
    `127a3c913fdc7c0e07a19f8daae2c0548c782770c74b5b6a6578ec9551bd3b79` until R3.
- **R3 (F3) `core/compliance/kr_rules.yaml:204`, the KR-KIS-KRX-DERIV reason.** Before: "KOSPI200 futures and options
  need a broker deposit of KRW 10M (stage 1) ..." (no "broker approval", ledger:118) while :203 `requires.live` lists
  `broker_approval`. After: the reason starts "KOSPI200 futures and options need broker approval, a broker deposit of
  KRW 10M (stage 1) ..." (exact line in section 5). One line changes; the table sha changes (no approval exists, so no
  re-sign; owner act 3 approves the edited bytes). No test pins the old sha or the old text (grep, 2026-10-24).
- **R4 (F4) D14 closure scan, `core/compliance/owner.py` `_skipped` (owner.py:708-724) and its copy in
  `tools/signer/sign.py` (sign.py:631-647).** Code-hash change (owner.py). Before: `if typing.TYPE_CHECKING:` is skipped
  whatever `typing` is bound to (owner.py:718-719), and `if __name__ == "__main__":` is skipped even when the module
  rebinds `__name__` (owner.py:720-723), so `typing = SimpleNamespace(TYPE_CHECKING=True)` or `__name__ = "__main__"`
  hides an import from the closure (ledger:208). After: `typing.TYPE_CHECKING` counts as a skip only when `typing` is
  bound exactly once in the module, by a plain `import typing`; the `__main__` test counts only when `__name__` is bound
  nowhere in the module (`owner._binds(tree, "__name__") == 0`). `_typing_flag` (owner.py:699-705) is unchanged. A
  binding is not the only way to change these names, so (a stricter reading of F4) no guard counts at all, the bare
  `TYPE_CHECKING` included, in a module that stores to an attribute `TYPE_CHECKING` or `__name__` or uses any Name or
  attribute `setattr`, `delattr`, `globals`, `vars`, `locals`, `modules`, `__dict__`, `builtins` or `__builtins__`
  (`typing.TYPE_CHECKING = True`, `setattr(typing, ...)`, `globals()["__name__"] = ...`, `sys.modules["typing"] =
  ...` each hide an import today). The two files stay character-identical in these helpers (a new source-equality
  test, section 6.4); `test_code_files_match_owner` (tests/compliance_signer.py:630-677) keeps their outputs in step.
  Checked in-process on 2026-10-24: the real closure (10 entries) is unchanged, and no closure file uses any of those
  names. Stated limit (spec rev 3.3; the controller accepts it as stated, RULINGS_ROUND2 R2-12): the route list is a
  denylist, so another module changing `typing.TYPE_CHECKING` before this one is imported, or a name built at run
  time, is not seen; the owner's review of each hashed file's diff is the barrier there.
- **R5 (F5) Signer ancestor walk, `tools/signer/sign.py` `_has_claude_ancestor` (sign.py:758-767), repo copy only.**
  Before: the walk returns False (no Claude ancestor, so signing may go on) when it reaches a pid missing from the
  table, a cycle or 256 steps (ledger:233). After: it returns True (Claude cannot be ruled out, refuse) in each of these
  cases unless the walk has already passed a Windows session process (R11), and it still walks the whole chain, so a
  claude.exe anywhere in it returns True as today, even above a session process. It returns False only at pid 0 or at
  such a break after a session process. Every chain refused today is still refused. The refusal text
  (sign.py:810-811) names the new cause. Updating
  the owner's own copy is an owner act (spec:598-599): read the diff, re-hash with certutil, re-record on paper.
- **R6 (F6) `core/compliance/alerts.py` `log()` (alerts.py:242-262).** Code-hash change. Before: every row copies the
  summary's `fingerprint` (alerts.py:253-254), so the first recorded fingerprint, which the key is held to (P20;
  owner.py:913-918 `_first_recorded`; alerts.py:97-100 `_first`), can come from a code-3 summary of a key the log does
  not verify (ledger:219). After: a row records the summary's fingerprint only when its `code` is 0, 1 or 2; a code 3
  or 4 row records `""`. The row keeps all nine keys.
- **R7 (F7) `tests/compliance_guards.py:483-489`.** Before: the test asserts the literal `"paper, grokteam or
  compliance"` in `tests/run_all.py` (:113) and `README.md` (:816), which breaks when any suite is added (ledger:69).
  After: it asserts that `compliance` is one of the names of the "one suite: a, b, ... or z" list in each file
  (section 3.9), so the odds plan adds `odds` to both lists without touching a compliance test.
- **R8 (F8) Data-layer minors from A0.** Both files are outside the D14 closure (P6).
  - `data/krx/kis_client.py`: before, `token()` POSTs to `/oauth2/tokenP` (kis_client.py:181) and only then
    `_store_token` runs `checked_target` (kis_client.py:158 via :195), so a refused target burns a token issuance
    (ledger:81; also on the execution carry list, ledger:239 "KIS token burnt on refusal", which this plan takes off
    it). After: `token()` calls `checked_target(_TOKEN_PATH, "KIS token cache")` after the cache miss and before
    `config.kis_credentials()` (kis_client.py:176), so a refusal raises before any credential is read or request built.
  - `core/ficc/data.py` `_cache_put` (data.py:269-279): before, `_MEM[key] = (now, rows)` (:273) precedes
    `checked_target` (:274), so a refused key is later served from memory (ledger:82). After: the check comes first.
- **R9 (reading of R1) importlib.** "Every importlib submodule except importlib.metadata" is implemented as
  `importlib` in DYNAMIC_MODULES plus DYNAMIC_EXEMPT, so the bare `import importlib` is dynamic too (its own API is
  `import_module`, `reload` and `__import__`; nothing in core/compliance imports it bare, checked 2026-10-24). In the
  dynamic scan only, a `from X import a, b` statement is judged by `X.a` and `X.b`, never by `X` alone, so `from
  importlib import metadata` stays legal; every other DYNAMIC entry is still caught in every form (a `from` of a banned
  module names a target below it). `_allowlist_hits` keeps its own `[module] + [module.n]` targets. In the name walk,
  an attribute of the bare name `importlib` other than `metadata` is a hit too: `import importlib.metadata` binds the
  name `importlib`, so `importlib.util.spec_from_file_location` or `importlib._bootstrap._load` would otherwise load a
  file with no banned import (owner.py uses only `importlib.metadata.*`, so no shipped hit).
  `importlib.metadata`'s `EntryPoint.load` string import (through an attribute) and an alias (`m = importlib`) stay
  documented limits; the lists are a denylist, not a proof.
- **R10 (reading of R2) check order inside `_row`, so every existing reason keeps its text.** `_match` (rules.py:451,
  refuses `any`) -> the axis check (:454-459) -> D15 content (new, same block) -> conduct-ETP check (:460-462) ->
  requires (:464-467) -> ack and grey (:468-480) -> warning slots (:481-485, `{cap}`-only-in-grey added) ->
  `max_leverage` with the bound (:486) -> policy_ref format, D16 label, then D15 label (:487-492) -> D16 content (new)
  -> the gated requirement (:493-494) -> ... -> `review_by` lower bound (new, before the 31-day check at :524). Three
  existing assertions flip on purpose and are rewritten in Task 2: tables:295 (a gated etp_leveraged row citing D160
  without live, VALID today, Invalid by D16 content), tables:316 (`{cap}` in an allow row's warning, VALID today) and
  tests/compliance_cli.py:576-577 (`test_render_has_no_rule_free_text` appends " {cap}" to every shipped warning, so
  the gated per_session row KR-KIS-US-OPTION turns Invalid; the rewrite appends it to the grey row only).
- **R11 (reading of R5) "the root" of the ancestor walk.** On this PC every chain ends at a parent that has exited
  (read-only probe of the live process table, 2026-10-24): the owner's Windows Terminal chain is `powershell.exe ->
  WindowsTerminal.exe -> svchost.exe -> services.exe -> wininit.exe -> (exited)`, `explorer.exe`'s parent has exited,
  and 299 service processes end at `wininit.exe -> (exited)`. So "the root" cannot be pid 0 alone (that would refuse
  the owner's own terminal, where spec:600 says the signer runs). The root is pid 0, or the break of a chain that has
  passed a Windows session process: `_SESSION_ROOTS = frozenset({"explorer.exe", "services.exe", "wininit.exe",
  "winlogon.exe"})` (case-insensitive), whose own parent normally exits. A session process never stops the walk: a
  process name is only a file name, so a copy of cmd.exe saved as winlogon.exe under Claude must not end the search
  (today's walk refuses that chain, and so does this one). So the walk goes on to pid 0 or a break; a claude.exe
  anywhere returns True; a break (a missing pid, a cycle, 256 steps) returns False only when a session process was
  passed on the way, else True. An editor terminal whose host's launcher exited (for example `Code.exe -> (exited)`)
  is refused; the refusal tells the owner to open Windows Terminal from the Start menu. Stated limits: a process
  started through COM activation or the desktop shell has no claude.exe ancestor, so this check stays defence in
  depth, and the passphrase and the typed code are the barrier (spec 6.4); a reused pid above a session process is
  walked too, so if it now runs claude.exe the signer refuses (as today) until Claude is closed.
- **R12 (reading of R8) the KIS check stays twice.** `_store_token` keeps its own `checked_target` (kis_client.py:158),
  which still guards a direct call (tests/compliance_isolation.py:247-258); the new call in `token()` is one line.
- **R13 (order and signatures, RULINGS "Order of the plans", amended by R2-11 and R2-13).** This plan runs first, on
  `compliance-followup` from main's HEAD at execution time (no pinned hash: by then main holds this plan, the odds
  plan and the E1 plan as docs commits after `995534b`, and Task 1 checks that nothing outside docs/ changed); the
  odds plan runs second and E1 third, each from main after the one before merges, each under the DRIFT RULE (section
  0). GPT's check after 2026-10-30 14:40 is not waited for: a valid finding that touches built code becomes a new task
  with its own failing test.

## 2. Files

```
tests/compliance_guards.py        (modify; Task 1)   R1 lists, _dynamic_module, _dynamic_hits, docstrings; R7 _suite_names
core/compliance/rules.py          (modify; Task 2)   R2: constants after :405-406, five checks in _row
tests/compliance_tables.py        (modify; Tasks 2, 3) R2 tests and two rewritten assertions; R3 assertion
core/compliance/kr_rules.yaml     (modify; Task 3)   R3: line 204 only
core/compliance/owner.py          (modify; Task 4)   R4: _guards (new), _skipped, _import_nodes, _repo_imports
tools/signer/sign.py              (modify; Tasks 4, 5) R4 identical copy; R5 _SESSION_ROOTS, _has_claude_ancestor,
                                                     _refusal text, one help bullet
tests/compliance_store.py         (modify; Task 4)   R4 synthetic tree
tests/compliance_signer.py        (modify; Tasks 4, 5) R4 synthetic tree + source-equality test; R5 walk tests
core/compliance/alerts.py         (modify; Task 6)   R6: log() row and docstring
tests/compliance_cli.py           (modify; Tasks 2, 6) R10 third rewrite (:576-577); R6 test
data/krx/kis_client.py            (modify; Task 7)   R8: one line in token()
core/ficc/data.py                 (modify; Task 7)   R8: two lines swapped in _cache_put
tests/compliance_isolation.py     (modify; Task 7)   R8 tests
README.md                         (modify; Task 8, CRLF) compliance row count and Total line
qa/acceptance_results.json        (commit; Task 8, CRLF) the full run
```
Not touched: `tests/run_all.py`, `tests/compliance_acceptance.py` (no new module), `core/odds/`, `core/isolation.py`,
`config.py`, every other table, `core/compliance/__init__.py` (stays 0 bytes), `owner_pubkey.pem` (still absent).

## 3. Guards: `tests/compliance_guards.py` (Task 1; R1, R7, R9)

### 3.1 Imports (guards:12-18)
Add `import re` between `import os` (:15) and `import sys` (:16).

### 3.2 `NETWORK_MODULES` (guards:39-41), new text
```python
NETWORK_MODULES = ("urllib", "http", "socket", "_socket", "socketserver", "selectors", "ssl", "smtplib", "ftplib",
                   "imaplib", "poplib", "nntplib", "telnetlib", "xmlrpc", "asyncio", "webbrowser", "multiprocessing",
                   "wsgiref", "xml.sax", "xml.dom", "logging.handlers", "antigravity", "ctypes", "_ctypes", "_ssl",
                   "_overlapped")
```
The comment above it (guards:34-38) stays.

### 3.3 Dynamic constants (guards:45-51)
Anchor: the comment block from `# Star and dynamic imports hide` through the end of `DYNAMIC_MODULES`, between
`FORBIDDEN_MODULES` and `# base name -> attributes that read the clock`. Old text (exact):
```python
# Star and dynamic imports hide what a file loads from these guards and from the D14 closure (P6). pydoc (locate),
# timeit, code and cProfile import or run code named in a string, so they count as dynamic imports too.
# importlib.metadata stays allowed: owner.py reads the RECORD files with it. core/ probes for cryptography with a
# lazy `import` inside try/except ImportError; importlib.util.find_spec is for tests only.
DYNAMIC_NAMES = frozenset({"__import__", "import_module", "exec_module", "load_module", "exec", "eval"})
DYNAMIC_MODULES = ("importlib.util", "importlib.machinery", "runpy", "pkgutil", "zipimport", "pydoc", "timeit",
                   "code", "cProfile")
```
New text:
```python
# Star and dynamic imports hide what a file loads from these guards and from the D14 closure (P6). Each module below
# imports or runs code named in a string or read from data: importlib (every submodule but metadata), runpy, pkgutil,
# zipimport, pydoc (locate), timeit, code, cProfile, profile, pdb, bdb, trace and doctest (exec of a string), unittest
# (mock.patch targets, the loader's __import__), logging.config (class strings, and a TCP listener), pickle, _pickle,
# shelve and marshal (objects and code from bytes), site (.pth lines are exec'd), ensurepip and venv (pip through
# runpy), tkinter, _tkinter, turtle, turtledemo and idlelib (a Tcl interpreter with sockets; idlelib exec), pstats
# and tracemalloc (they load files with marshal and pickle: pstats.Stats, tracemalloc.Snapshot.load). The builtin
# compile() is banned as a bare name only, so re.compile stays legal (builtins.compile is left to review).
# importlib.metadata stays allowed: owner.py reads the RECORD files with it. `import importlib.metadata` binds the
# name importlib, so any other attribute of it (importlib.util, importlib._bootstrap, ...) is a hit too; its
# EntryPoint.load imports by string through an attribute, which this scan does not see. faulthandler stays allowed
# (R1): it runs no string and opens nothing. A denylist, not a proof. core/ probes for cryptography with a lazy
# `import` inside try/except ImportError; importlib.util.find_spec is for tests only.
DYNAMIC_NAMES = frozenset({"__import__", "import_module", "exec_module", "load_module", "exec", "eval"})
DYNAMIC_BARE = frozenset({"compile"})               # an ast.Name only: re.compile is an attribute
DYNAMIC_MODULES = ("importlib", "runpy", "pkgutil", "zipimport", "pydoc", "timeit", "code", "cProfile", "profile",
                   "pdb", "bdb", "trace", "doctest", "unittest", "logging.config", "pickle", "_pickle", "shelve",
                   "marshal", "site", "ensurepip", "venv", "tkinter", "_tkinter", "turtle", "turtledemo", "idlelib",
                   "pstats", "tracemalloc")
DYNAMIC_EXEMPT = "importlib.metadata"               # and everything below it (R9)
```
Dry run (2026-10-24, `followup/sandbox_round2/make_and_probe.py`, a sandbox copy of the guards file with this block
and section 3.4): 29 distinct entries; every entry in each import form, `import pstats`, `from pstats import Stats`,
`import tracemalloc` and `from tracemalloc import Snapshot` are hits; the section 3.6 negative controls are not; no hit
in core/compliance, core/odds or the R2/R4 sandbox copies of rules.py and owner.py; longest line 120 characters.

### 3.4 `_dynamic_hits` (guards:146-157), new text with one new helper above it
```python
def _dynamic_module(target: str) -> bool:
    """A dotted import target in DYNAMIC_MODULES (or below one), unless it is DYNAMIC_EXEMPT or below it (R9)."""
    if target == DYNAMIC_EXEMPT or target.startswith(DYNAMIC_EXEMPT + "."):
        return False
    return any(target == m or target.startswith(m + ".") for m in DYNAMIC_MODULES)


def _dynamic_hits(rel: str, src: str) -> list[str]:
    tree, hits = ast.parse(src), []
    for node, module, names, _f in _imports(rel, tree):
        targets = [f"{module}.{n}" for n in names] or [module]     # `from importlib import metadata` is that module
        if "*" in names or DYNAMIC_NAMES.intersection(names) or any(_dynamic_module(t) for t in targets):
            hits.append(f"{rel}:{node.lineno}: star or dynamic import from {module}")
    for node, _f in _walk(tree):
        name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
        via = isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "importlib"
        if via and name != "metadata":                  # `import importlib.metadata` binds the name importlib (R9)
            hits.append(f"{rel}:{node.lineno}: importlib.{name}")
        elif name in DYNAMIC_NAMES or (isinstance(node, ast.Name) and node.id in DYNAMIC_BARE):
            hits.append(f"{rel}:{node.lineno}: {name}")
    return hits
```

### 3.5 `test_no_http_verb_calls` docstring (guards:249-262), new text (the body :263-270 stays)
```
    """core/compliance never calls .post/.put/.delete/.patch/.request on anything (contract section 0), a dict-like
    `.put` included, nor urlopen, urlretrieve or create_connection (bare or as an attribute). This is the second
    line. The first is test_imports_stay_on_the_allowlist, which bans every import form of the stdlib modules that
    open a connection or fetch a URL (NETWORK_MODULES: urllib, http, socket, ssl and _ssl, the mail, ftp and telnet
    clients, xmlrpc, asyncio and _overlapped, selectors, socketserver, wsgiref, multiprocessing, webbrowser and
    antigravity, which opens a URL at import, logging.handlers, xml.sax, which opens a URL given as a system id, the
    whole xml.dom package, whose xmlbuilder DOMBuilder.parseURI opens a URL with urllib.request and which minidom and
    xml.dom.getDOMImplementation() both hand out, and ctypes and _ctypes, which call any DLL). Together they catch a
    stdlib network call written in the ordinary ways; they do not prove that core/compliance cannot reach the
    network. Not covered: a `subprocess` call (the P26 alert toast is one; os.system, os.popen, os.startfile and
    _winapi launch processes the same way), and reaching a network API through an allowed module, by attribute or by
    `getattr(module, "name")`: an allowed module that imports a banned one carries it as an attribute (mailbox
    carries socket, concurrent.futures.process carries multiprocessing.connection). Both are left to review."""
```

### 3.6 `test_no_forbidden_module_import` (guards:273-302)
- Docstring (:274-276): "and no star or dynamic import," becomes "and no star or dynamic import or bare compile(),"
  (rewrap the docstring within 120 columns; :275 is 115 characters today).
- The explicit positive list (:284-290) gains, after `"from cProfile import run\n"`: `"import importlib\n"`,
  `"import importlib.resources\n"`, `"from importlib import resources\n"`, `"import profile\n"`, `"import pdb\n"`,
  `"from bdb import Bdb\n"`, `"import trace\n"`, `"import doctest\n"`, `"import unittest.mock\n"`,
  `"from unittest import mock\n"`, `"from logging import config\n"`, `"import logging.config\n"`,
  `"from logging.config import dictConfig\n"`, `"import pickle\n"`, `"import _pickle\n"`, `"import shelve\n"`,
  `"import marshal\n"`, `"import site\n"`, `"import ensurepip\n"`, `"import venv\n"`, `"import tkinter\n"`,
  `"from tkinter import Tcl\n"`, `"import _tkinter\n"`, `"import turtle\n"`, `"import turtledemo\n"`,
  `"import idlelib.run\n"`, `'x = compile(s, "x", "exec")\n'`, `"import pstats\n"`, `"from pstats import Stats\n"`,
  `"import tracemalloc\n"`, `"from tracemalloc import Snapshot\n"` (R2-10). The old `"import importlib.util\n"` and
  `"from importlib import util\n"` stay.
- The negative control (:295-297) stays (`import profile_notes` in it proves the `profile` ban does not catch a
  longer name), and a second one follows it:
```python
    assert not _dynamic_hits(X, "from importlib.metadata import distribution, PackageNotFoundError\nimport traceback\n"
                                "import faulthandler\nimport logging\nfrom logging import getLogger\n"
                                "_P = re.compile(r'x')\n")    # not banned (R1); pstats and tracemalloc are (R2-10)
```

### 3.7 `test_imports_stay_on_the_allowlist` (guards:305-341)
- The "modules a plain socket/urllib list misses" list (:324-329) gains `"import xml.dom\n"`,
  `"from xml.dom import minidom\n"`, `"import xml.dom.minidom\n"`, `"import xml.dom.xmlbuilder\n"`,
  `"from xml import dom\n"`, `"from xml.dom.minidom import parseString\n"`, `"import antigravity\n"`,
  `"import ctypes\n"`, `"from ctypes import wintypes\n"`, `"import _ctypes\n"`, `"import _ssl\n"`,
  `"import _overlapped\n"`. The three old xml.dom cases stay.
- The negative control (:332-333) becomes
  `assert not _allowlist_hits(X, "import logging\nfrom logging import getLogger\nimport xml.etree.ElementTree\n"
  "from xml.etree import ElementTree\n")` (the `from xml.dom import minidom\n` line is dropped). :334-335 stays.

### 3.8 New test, placed right after `test_no_forbidden_module_import`
```python
def test_bare_compile_and_importlib_submodules_are_dynamic():
    """The builtin compile() turns a string into code (types.FunctionType can then run it with no exec or eval), so the
    bare name is banned; re.compile is an attribute and stays legal. Every importlib import but importlib.metadata is
    dynamic (importlib.resources imports a package named by a string), and so is every attribute of the name
    importlib but metadata, which `import importlib.metadata` binds (R9)."""
    for src in ('x = compile(s, "x", "exec")\n', "f = compile\n", "compile = None\n", "import importlib\n",
                "import importlib.resources\n", "from importlib import resources\n", "import importlib.abc\n",
                "import importlib._bootstrap\n", "from importlib import metadata, util\n",
                "import importlib.metadata\nm = importlib.util.spec_from_file_location('m', p)\n",
                "import importlib.metadata\nimportlib._bootstrap._load(s)\n",
                "import importlib.metadata\nimportlib.reload(m)\n"):
        assert _dynamic_hits(X, src), src
    assert _dynamic_module("importlib.util") and not _dynamic_module("importlib.metadata.x")
    assert not _dynamic_hits(X, "_P = re.compile(r'x')\nself.compile()\nm.compile\n")
    assert not _dynamic_hits(X, "import importlib.metadata\nfrom importlib import metadata\n"
                                "from importlib.metadata import distribution, PackageNotFoundError\n"
                                "import importlib.metadata as md\nv = importlib.metadata.version('PyYAML')\n")
```

### 3.9 R7: the registration test (guards:483-489), new text with one helper above it
```python
def _suite_names(text: str) -> list[str]:
    """The names of the first hand-written "one suite: a, b, ... or z" list in `text` ([] when there is none)."""
    line = next((s for s in text.splitlines() if "one suite: " in s), "")
    listed = line.split("one suite: ", 1)[1].rstrip('")').strip() if line else ""
    return [n for n in re.split(r", | or ", listed) if n]


def test_suite_is_registered_in_run_all_and_readme():
    """`tests/run_all.py --suite compliance` selects this suite, and both hand-written suite lists name it; the check
    reads the list, so adding a suite to either list breaks nothing (R7)."""
    from tests import run_all
    names = [n for n, _f in run_all.select(run_all.tests(), suite="compliance")]
    assert any(n.startswith("compliance/compliance_guards/") for n in names), names
    assert _suite_names('help="run one suite: cockpit, compliance or odds")') == ["cockpit", "compliance", "odds"]
    assert "compliance" not in _suite_names("x  # one suite: cockpit or paper\n") and _suite_names("none\n") == []
    for path in (ROOT / "tests" / "run_all.py", ROOT / "README.md"):
        assert "compliance" in _suite_names(path.read_text(encoding="utf-8")), path.name
```
(`read_text` uses universal newlines, so the CRLF files split cleanly; tests/run_all.py:113 and README.md:816 hold the
only "one suite: " lines today.)

### 3.10 Interfaces this produces for the odds plan
`NETWORK_MODULES`, `DYNAMIC_MODULES`, `DYNAMIC_NAMES`, `DYNAMIC_BARE`, `DYNAMIC_EXEMPT`, `_dynamic_module`,
`_dynamic_hits`, `CLOCKS` in `tests/compliance_guards.py`. The odds guards (RULINGS O2) import them; they do not copy.
They test an import target with `_dynamic_module` (which honours DYNAMIC_EXEMPT), never with a raw prefix match over
DYNAMIC_MODULES: since `importlib` is a DYNAMIC_MODULES entry, a raw match would also drop `importlib.metadata`.

Expected after Task 1: `-m tests.compliance_acceptance compliance_guards/` prints `16/16 passed, 0 failed, 0 not run`.

## 4. Loader: `core/compliance/rules.py` and `tests/compliance_tables.py` (Task 2; R2, R10)

### 4.1 Constants (after rules.py:405-406 `_BLOCKING`, `_MAX_REVIEW_DAYS`)
```python
_MAX_LEVERAGE = 10.0                                       # R2: a typo cannot sign 1e6x
_D15_FINANCING = frozenset({"credit", "margin"})           # D15: no credit buying (margin included, ledger:131)
_D15_ACTIONS = frozenset({"lend", "borrow"})               # D15: no coin lending or borrowing
_D16_ACTIONS = frozenset({"sell_short"})                   # D16 by content (spec:70), whatever policy_ref says
_D16_CLASSES = frozenset({"etp_leveraged", "etp_single_stock", "krx_derivative", "elw"})
_D16_ASSETS = frozenset({"krx_derivative", "elw"})
```

### 4.2 The five checks, at their R10 places in `_row`
1. D15 content, inside `if treatment not in _BLOCKING:` right after the `missing` raise (rules.py:457-459):
```python
        credit = sorted(match["financing"] & _D15_FINANCING)
        if credit:
            raise Invalid(f"{where}: match.financing: an allow, gated or grey row never matches {credit} (D15: no "
                          "credit buying)")
        lending = sorted(match["action"] & _D15_ACTIONS)
        if lending:
            raise Invalid(f"{where}: match.action: an allow, gated or grey row never matches {lending} (D15: no coin "
                          "lending or borrowing)")
```
2. `{cap}` only in grey: rules.py:484-485 become
```python
    slots = {slot for _, slot, _, _ in string.Formatter().parse(warning)}
    if treatment == "grey" and "cap" not in slots:
        raise Invalid(f"{where}: warning: a grey row states its {{cap}}")
    if treatment != "grey" and "cap" in slots:                               # the cap is a grey row's (ledger:146)
        raise Invalid(f"{where}: warning: only a grey row states a {{cap}}")
```
3. `max_leverage` bound, right after rules.py:486:
```python
    if leverage > _MAX_LEVERAGE:
        raise Invalid(f"{where}: max_leverage: at most {_MAX_LEVERAGE:g}, got {leverage!r}")
```
   (Amended 2026-10-25, Task 2 review: `!r` as in `_positive`'s reason, so 10.0000001 never reads `got 10`.)
4. D15 label, inside `if policy_ref is not None:` after the D16 label raise (rules.py:491-492), then D16 content after
   that block and before the gated check (rules.py:493):
```python
        if "D15" in policy_ref.split(", ") and treatment not in _BLOCKING:
            raise Invalid(f"{where}: treatment: a D15 row is hard_block or out_of_scope (D15 only keeps credit and "
                          "lending out)")
    classes = match.get("class", frozenset())
    if "class" not in match and match.get("asset", frozenset()) & ETP_ASSETS:   # no class axis: it matches every
        classes = frozenset({"etp_leveraged", "etp_single_stock"})               # class an ETP derives to
    d16 = sorted((match.get("action", frozenset()) & _D16_ACTIONS) | (classes & _D16_CLASSES)
                 | (match.get("asset", frozenset()) & _D16_ASSETS))
    if treatment not in _BLOCKING and d16 and not live:
        raise Invalid(f"{where}: requires.live: a row matching {d16} needs live broker evidence (D16)")
```
5. `review_by` lower bound, right after rules.py:523 `latest = max(r.date for r in reviews)`:
```python
    if review_by < latest:                                                   # a typo, never a schedule (ledger:103)
        raise Invalid(f"{where}: review_by: {review_by} is before the review of {latest}")
```

### 4.3 Reason strings (exact; `<id>` is the row id)
| Rule | Reason |
|---|---|
| D15 content, financing | `rules: row <id>: match.financing: an allow, gated or grey row never matches ['credit'] (D15: no credit buying)` (the sorted hit list) |
| D15 content, action | `rules: row <id>: match.action: an allow, gated or grey row never matches ['borrow', 'lend'] (D15: no coin lending or borrowing)` |
| D15 label | `rules: row <id>: treatment: a D15 row is hard_block or out_of_scope (D15 only keeps credit and lending out)` |
| D16 content | `rules: row <id>: requires.live: a row matching ['etp_leveraged'] needs live broker evidence (D16)` (an ETP asset with no class axis lists `['etp_leveraged', 'etp_single_stock']`) |
| review_by | `rules: row <id>: review_by: 2026-10-22 is before the review of 2026-10-23` |
| max_leverage | `rules: row <id>: max_leverage: at most 10, got 10.5` |
| {cap} | `rules: row <id>: warning: only a grey row states a {cap}` |

### 4.4 Tests in `tests/compliance_tables.py` (and two lines of `tests/compliance_cli.py`)
Fixture rule: a test row other than `_row()` itself gets its own id and `matrix_rows: []` and is passed after `_row()`,
which covers the 38 matrix rows (tables:50-59); a single `_row(...)` override keeps id T-ALLOW and the full matrix.
Changed (the three R10 rewrites, written first; the new `_bad` at tables:295 fails first, the other two pass before
and after R2 and keep their tests green under it):
- `test_d16_rows_need_requires_live` (tables:285-299): line 295 becomes two lines:
  `_bad(_row(), _row(**{**lev, "policy_ref": "D160"}, requires={"owner": ["kofia_leveraged_1h"]}),
  "row T-LEV: requires.live: a row matching ['etp_leveraged']")   # not D16 by label, D16 by content` and
  `_parse(_row(), _row(**{**lev, "policy_ref": "D160", "match": {**lev["match"], "class": ["etp_1x"]}},
  requires={"owner": ["kofia_leveraged_1h"]}))   # D160 is not D16, and etp_1x is not D16 by content`.
  Lines 289-291 and 296-299 stay (their reasons are unchanged under R10).
- `test_warning_slots` (tables:315-322): the tuple at :316 drops `"OKX is capped at {cap} of your equity."`; :318-322
  stay (`{cap!r}` and `{cap:>5}` still fail first in `_warning`).
- `test_max_leverage` (tables:408-413) gains `assert _parse(_row(max_leverage=10)).rows[0].max_leverage == 10.0` and
  `for bad in (10.5, 11, 1e6): _bad(_row(max_leverage=bad), "row T-ALLOW: max_leverage: at most 10")`.
- In `tests/compliance_cli.py` `test_render_has_no_rule_free_text` (:564-590), lines 576-577
  `if row.get("warning"):` / `row["warning"] = UNIQUE + " {cap}"` become
  `if row.get("warning"):` / `row["warning"] = UNIQUE + (" {cap}" if row["treatment"] == "grey" else "")`. The
  grey row KR-OKX-SPOT keeps its slot and KR-KIS-US-OPTION (gated, per_session) a plain warning, so the table stays
  VALID and the test still proves that no rule free text renders. It passes before and after R2; without it R2 turns
  this test red (`rules: row KR-KIS-US-OPTION: warning: only a grey row states a {cap}`, dry run 2026-10-24).
New, placed after `test_d16_rows_need_requires_live` (tables:300), names fixed:
- `test_d15_rows_never_let_credit_margin_lending_or_borrowing_through`: for an allow row and a gated row (`requires:
  {owner: [age_of_majority]}`) on `{venue: [upbit], class: [coin], ...}`: financing `[cash, margin]`, `[credit]`,
  `[margin]` each `_bad(..., "row T-ALLOW: match.financing: an allow, gated or grey row never matches")`; action
  `[buy, lend]`, `[borrow]` each `_bad(..., "match.action: an allow, gated or grey row never matches")`; a grey row
  (`_grey(match={venue: [okx], class: [coin], action: [buy, sell], financing: [cash, margin]})`) gives
  `"row T-GREY: match.financing"` and `"['margin'] (D15"`; a `hard_block` and an `out_of_scope` row matching action
  `[buy, lend, borrow]` and financing `[credit, margin]` parse; a gated row with action `[buy, sell_short]` and
  `requires: {live: [broker_approval]}` parses (sell_short is D16, not D15).
- `test_a_d15_row_is_blocking`: a row with `policy_ref: D15`, `basis: [policy]`, `matrix_rows: []` is
  `_bad(_row(), row, "row T-D15: treatment: a D15 row is hard_block or out_of_scope")` as allow, as gated (owner
  requirement) and as grey (`_grey(id="T-D15", policy_ref="D15", basis=["policy"], matrix_rows=[])`); with policy_ref
  `"D15"` and `"D10, D15"` it parses as hard_block and as out_of_scope.
- `test_d16_by_content_needs_requires_live`: nine matches on venue kis with financing cash: asset `[krx_share]` +
  action `[sell_short]`; class `[etp_1x, etp_leveraged]`; class `[etp_single_stock]`; class `[krx_derivative]`; asset
  `[krx_derivative]`; class `[elw]`; asset `[elw]`; asset `[krx_etp]` and asset `[us_etp]` with no class key (action
  `[buy]` unless named). Each is `_bad(..., "row T-D16: requires.live: a row matching")` as a gated row with only an
  owner requirement and as an allow row; each parses as a gated row with `requires: {owner: [age_of_majority], live:
  [broker_approval]}` (`requires_live == ("broker_approval",)`) and as an out_of_scope row; an allow row with asset
  `[krx_etp]` and class `[etp_1x]` parses (the class axis decides); a grey row with action `[buy, sell_short]` gives
  `"row T-GREY: requires.live: a row matching ['sell_short']"`.
- `test_review_by_is_not_before_the_latest_review`: `review_by: "2026-10-23"` (the review day) parses;
  `"2026-10-22"` gives `"row T-ALLOW: review_by: 2026-10-22 is before the review of 2026-10-23"`; with reviews
  2026-09-01 and 2026-10-23, `"2026-10-01"` gives `"is before the review of 2026-10-23"` (the latest review counts).
- `test_only_a_grey_row_states_a_cap`: `_bad(_row(warning="OKX is capped at {cap} of your equity."),
  "row T-ALLOW: warning: only a grey row states a {cap}")`; a gated row with `ack: per_session`, an owner requirement
  and `warning: "at most {cap} of your equity"` gives `"row T-GATED: warning: only a grey row"` (the ledger:146 case);
  `"literal {{cap}} braces"` still parses on an allow row; `"{cap}" in _parse(_row(), _grey()).rows[1].warning`.
New, in the Task 5 block after `test_shipped_okx_spot_is_the_d6_grey_row` (tables:968-981):
- `test_shipped_rows_that_can_let_through_are_pinned_exactly` with module constant `_T5_PINNED` (section 4.5): the set
  of shipped ids whose treatment is allow, gated or grey equals `set(_T5_PINNED)`, and for each id
  `({k: set(v) for k, v in r.match.items()}, r.requires_owner, r.requires_live, r.treatment) == _T5_PINNED[id]`.
  Docstring names ledger:113 (widening an allow row passed all 18 tests).

### 4.5 `_T5_PINNED` (generated from the shipped table on 2026-10-24; tuples keep the YAML order)
```python
_T5_PINNED = {                                   # (match, requires_owner, requires_live, treatment), ledger:113
    "KR-KIS-KRX-SHARE": ({"venue": {"kis"}, "asset": {"krx_share"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                         (), (), "allow"),
    "KR-KIS-KONEX": ({"venue": {"kis"}, "class": {"konex_share"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                     (), (), "allow"),
    "KR-KIS-ETP-1X": ({"venue": {"kis"}, "class": {"etp_1x"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                      (), (), "allow"),
    "KR-KIS-ETP-INVERSE": ({"venue": {"kis"}, "class": {"etp_index_inverse"}, "action": {"buy", "sell"},
                            "financing": {"cash"}}, (), (), "allow"),
    "KR-KIS-ETP-LEV": ({"venue": {"kis"}, "class": {"etp_leveraged"}, "action": {"buy"}, "financing": {"cash"}},
                       ("kofia_leveraged_1h",), ("deposit_krw_10m",), "gated"),
    "KR-KIS-SINGLE-ETP": ({"venue": {"kis"}, "class": {"etp_single_stock"}, "action": {"buy"}, "financing": {"cash"}},
                          ("kofia_single_stock_3h", "krx_mock_5h_5days"), ("cash_krw_30m",), "gated"),
    "KR-KIS-CRYPTO-FUT-ETF": ({"venue": {"kis"}, "class": {"etp_crypto_futures_1x"}, "action": {"buy", "sell"},
                               "financing": {"cash"}}, (), (), "allow"),
    "KR-KIS-KRX-DERIV": ({"venue": {"kis"}, "class": {"krx_derivative"}, "action": {"buy", "sell_short", "write"},
                          "financing": {"cash"}}, ("kofia_derivatives_1h", "krx_derivatives_mock_3h"),
                         ("broker_approval", "deposit_krw_10m", "deposit_krw_20m"), "gated"),
    "KR-KIS-ELW": ({"venue": {"kis"}, "class": {"elw"}, "action": {"buy"}, "financing": {"cash"}},
                   ("elw_course",), ("deposit_krw_15m",), "gated"),
    "KR-KIS-SHORT": ({"venue": {"kis"}, "asset": {"krx_share"}, "action": {"sell_short"}, "financing": {"cash"}},
                     ("short_course_30m", "short_mock_1h"), ("broker_approval", "collateral_105pct"), "gated"),
    "KR-KIS-US-SHARE": ({"venue": {"kis"}, "asset": {"us_share"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                        (), (), "allow"),
    "KR-KIS-US-OPTION": ({"venue": {"kis"}, "class": {"option"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                         ("us_option_course_1h", "us_option_mock_3h", "broker_eligibility"), (), "gated"),
    "KR-DOMESTIC-SPOT": ({"venue": {"bithumb", "coinone", "korbit", "upbit"}, "class": {"coin"},
                          "action": {"buy", "sell"}, "financing": {"cash"}}, (), (), "allow"),
    "KR-TRANSFER-OUT": ({"venue": {"bithumb", "coinone", "korbit", "upbit"}, "class": {"coin"},
                         "action": {"transfer_out"}, "financing": {"cash"}}, (), (), "allow"),
    "KR-OKX-SPOT": ({"venue": {"okx"}, "class": {"coin"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                    ("age_of_majority",), (), "grey"),
}
```

Dry run on a sandbox copy of rules.py with exactly the section 4.1-4.2 text (2026-10-24, re-run after the
no-class-axis lines of check 4): rules.py grows by 31 lines (longest line 120 characters); the shipped table parses
VALID (47 rows); of the 59 existing table tests, 56 pass, the REFDATA symlink test is NOT_RUN, and exactly the two
tables flips fail (tables:295 with the D16-content reason, tables:316 with the `{cap}` reason); the mutated table of
tests/compliance_cli.py:573-578 is Invalid as written and VALID with the rewritten line; every case of section 4.4
passes.
Expected after Task 2: `-m tests.compliance_acceptance compliance_tables/` prints `64/65 passed, 0 failed, 1 not run`
(the REFDATA symlink test, unless Developer Mode is on); `compliance_cli/` prints `35/35 passed, 0 failed, 0 not run`;
`--suite compliance` 0 failed.

## 5. Table text: `core/compliance/kr_rules.yaml:204` (Task 3; R3)

Anchor: the `reason:` key of the row `- id: KR-KIS-KRX-DERIV` (:199). Old line 204 (exact):
```
    reason: "KOSPI200 futures and options need a broker deposit of KRW 10M (stage 1) or KRW 20M (stage 2: option writing, VKOSPI futures), at least 1h of course and 3h of mock trading; this row asks for the stage-2 deposit for every intent; refused until live broker evidence exists (D16)"
```
New line 204 (exact):
```
    reason: "KOSPI200 futures and options need broker approval, a broker deposit of KRW 10M (stage 1) or KRW 20M (stage 2: option writing, VKOSPI futures), at least 1h of course and 3h of mock trading; this row asks for the stage-2 deposit for every intent; refused until live broker evidence exists (D16)"
```
Only this line changes: the file grows from 59,408 to 59,425 bytes and its sha256 goes from `127a3c91...551bd3b79`
to `74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd` (computed on a copy, 2026-10-24; the edited
table parses VALID under R2).
Test: `test_shipped_d16_rows_need_live_evidence` (tables:951-965) gains, after :959,
`assert "broker approval" in krx_deriv.reason, krx_deriv.reason   # the reason names what requires.live asks (ledger:118)`.
The file stays LF, UTF-8, under 256 KB (`test_shipped_files_are_utf8_lf_and_small`, tables:897-902). Not in scope
here: the 2027-01-01 `affected_by` item (ledger:114), any deposit network (OKX USDT/USDC stays an owner act,
ledger:120), and the plan document's embedded copy of the old row (docs/superpowers/plans/2026-10-23-compliance-gate.md
:5109, a historical record).

## 6. Closure scan: `core/compliance/owner.py` and `tools/signer/sign.py` (Task 4; R4)

### 6.1 New helper, placed right after `_typing_flag` (owner.py:699-705; sign.py:622-628), identical in both files
```python
def _guards(tree: ast.AST) -> tuple[bool, bool, bool]:
    """Which `if` guards of `tree` may skip their body (P6, R4): (bare TYPE_CHECKING, typing.TYPE_CHECKING,
    __name__ == "__main__"). The bare name needs _typing_flag; `typing.` needs `typing` bound exactly once, by a
    plain `import typing`; the `__main__` test needs `__name__` bound nowhere in the module. A rebound name
    (typing = SimpleNamespace(TYPE_CHECKING=True), __name__ = "__main__") loses its guard, and a module that can
    change these names without binding them (an attribute store of TYPE_CHECKING or __name__, or any setattr,
    delattr, globals, vars, locals, modules, __dict__, builtins or __builtins__) trusts no guard: the guarded body
    is scanned. Not seen: another module changing typing.TYPE_CHECKING first (the review of each hashed diff)."""
    plain = any(isinstance(n, ast.Import) and any(a.name == "typing" and a.asname is None for a in n.names)
                for n in ast.walk(tree))
    routes = {"setattr", "delattr", "globals", "vars", "locals", "modules", "__dict__", "builtins", "__builtins__"}
    if any((isinstance(n, ast.Name) and n.id in routes) or (isinstance(n, ast.Attribute) and (n.attr in routes or (
            n.attr in ("TYPE_CHECKING", "__name__") and not isinstance(n.ctx, ast.Load)))) for n in ast.walk(tree)):
        return False, False, False
    return _typing_flag(tree), plain and _binds(tree, "typing") == 1, _binds(tree, "__name__") == 0
```
Dry run (2026-10-24, sandbox copies of owner.py and sign.py with sections 6.1-6.3): the real closure is the same 10
entries; the seven helpers are source-identical; the synthetic tree of section 6.4 hides none of its ten targets
(today's owner.py hides all ten); rules.py and model.py keep the bare TYPE_CHECKING skip and rules.py and alerts.py
the `__main__` skip; every new line is within 120 characters.

### 6.2 `_skipped` (owner.py:708-724; sign.py:631-647), new text, identical in both files
```python
def _skipped(node: ast.AST, guards: tuple[bool, bool, bool]) -> bool:
    """Whether `node` is an `if` whose body never runs at import and so is outside the code closure (P6):
    `if TYPE_CHECKING:`, `if typing.TYPE_CHECKING:` and a single `==` comparison of `__name__` with "__main__" in
    either order, each only while `guards` (see _guards) trusts its name. Every other test (`!=`, `not
    TYPE_CHECKING`, a local or rebound name) is scanned, since its body can run at import."""
    if not isinstance(node, ast.If):
        return False
    bare, dotted, main = guards
    t = node.test
    if isinstance(t, ast.Name):
        return t.id == "TYPE_CHECKING" and bare
    if isinstance(t, ast.Attribute):
        return dotted and t.attr == "TYPE_CHECKING" and isinstance(t.value, ast.Name) and t.value.id == "typing"
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
        sides = [t.left, *t.comparators]
        return (main and any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides)
                and any(isinstance(s, ast.Constant) and s.value == "__main__" for s in sides))
    return False
```

### 6.3 Callers (both files)
- `_import_nodes` (owner.py:727-736; sign.py:650-659): the parameter `bare_flag: bool` becomes
  `guards: tuple[bool, bool, bool]` in the signature and in its three uses; the docstring stays.
- `_repo_imports` (owner.py:755; sign.py:678): `for node in _import_nodes(tree, _typing_flag(tree)):` becomes
  `for node in _import_nodes(tree, _guards(tree)):`.
- sign.py's section comment (sign.py:597-601) stays true; no other line changes. `code_files`, `code_hash` and
  `_RECORD_DISTS` are untouched.

### 6.4 Tests
- `tests/compliance_store.py` `test_code_files_counts_lazy_imports_and_skips_main_and_type_checking` (:153-194):
  `sources` gains (after `"core/compliance/f.py"`):
  `"core/compliance/h.py": "import types\nimport typing\ntyping = types.SimpleNamespace(TYPE_CHECKING=True)\nif typing.TYPE_CHECKING:\n    import core.rebound_typing\n"`,
  `"core/compliance/i.py": "__name__ = \"__main__\"\nif __name__ == \"__main__\":\n    import core.rebound_main\n"`,
  `"core/compliance/j.py": "import os as typing\nif typing.TYPE_CHECKING:\n    import core.alias_typing\n"`,
  `"core/compliance/k.py": "if typing.TYPE_CHECKING:\n    import core.unbound_typing\n"`,
  `"core/compliance/l.py": "def main(__name__=None):\n    return __name__\nif __name__ == \"__main__\":\n    import core.param_main\n"`,
  `"core/compliance/m.py": "import typing\ntyping.TYPE_CHECKING = True\nif typing.TYPE_CHECKING:\n    import core.stored_typing\n"`,
  `"core/compliance/n.py": "import typing\nsetattr(typing, \"TYPE_CHECKING\", True)\nif typing.TYPE_CHECKING:\n    import core.setattr_typing\n"`,
  `"core/compliance/o.py": "globals()[\"__name__\"] = \"__main__\"\nif __name__ == \"__main__\":\n    import core.globals_main\n"`,
  `"core/compliance/p.py": "import sys\nimport types\nsys.modules[\"typing\"] = types.SimpleNamespace(TYPE_CHECKING=True)\nimport typing\nif typing.TYPE_CHECKING:\n    import core.modules_typing\n"`,
  `"core/compliance/q.py": "import typing\ntyping.TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import core.stored_bare\n"`,
  and the ten empty targets `core/rebound_typing.py`, `core/rebound_main.py`, `core/alias_typing.py`,
  `core/unbound_typing.py`, `core/param_main.py`, `core/stored_typing.py`, `core/setattr_typing.py`,
  `core/globals_main.py`, `core/modules_typing.py`, `core/stored_bare.py`. The expected set gains `core/compliance/h.py`
  .. `q.py` and the ten targets. The docstring gains: "and a guard whose name the module rebinds or never imports
  plainly (typing rebound, `import os as typing`, no `import typing`, `__name__` assigned or a parameter), or that the
  module can change without a binding (an attribute store, setattr, globals(), sys.modules), is scanned too (R4)".
- `tests/compliance_signer.py` `test_code_files_match_owner` (:630-677): the same ten sources, ten targets and
  expected-set entries (its synthetic tree also holds `core/compliance/g.py`, which stays).
- New `tests/compliance_signer.py` test, placed after `test_code_files_match_owner`:
```python
def test_closure_scan_helpers_are_identical_in_owner_and_signer():
    """R4: the signer's copy of the D14 closure scan is owner.py's, character for character, so a hardening in one
    file cannot be forgotten in the other (test_code_files_match_owner compares outputs on chosen trees only)."""
    import inspect
    for name in ("_binds", "_typing_flag", "_guards", "_skipped", "_import_nodes", "_module_file", "_repo_imports"):
        assert inspect.getsource(getattr(signer, name)) == inspect.getsource(getattr(owner, name)), name
```
(The six existing helpers are byte-identical today, checked 2026-10-24; `code_files` and `code_hash` differ in their
docstrings and are not compared.)

Expected after Task 4: `compliance_store/` `29/29 passed`; `compliance_signer/` `38/38 passed, 0 failed, 0 not run`.

## 7. Signer ancestor walk: `tools/signer/sign.py` (Task 5; R5, R11)

### 7.1 New constant and function (sign.py:758-767 replaced)
```python
_SESSION_ROOTS = frozenset({"explorer.exe", "services.exe", "wininit.exe", "winlogon.exe"})   # their parents exit


def _has_claude_ancestor(pid: int, table: dict[int, tuple[int, str]]) -> bool:
    """True when `pid` or any ancestor in `table` runs claude.exe (any version, any case), even above a Windows
    session process (a process name is only a file name). The walk goes on to pid 0 or until it breaks: at a pid
    missing from the table (a parent that has exited), a pid-reuse cycle or 256 steps. A break returns True (Claude
    cannot be ruled out) unless the walk has passed a session process (_SESSION_ROOTS), whose own parent has normally
    exited: Windows Terminal runs under svchost.exe, services.exe and wininit.exe (R11)."""
    seen, rooted = set(), False
    while pid != 0:
        if pid not in table or pid in seen or len(seen) >= 256:
            return not rooted
        seen.add(pid)
        parent, exe = table[pid]
        if exe.lower() == "claude.exe":
            return True
        rooted = rooted or exe.lower() in _SESSION_ROOTS
        pid = parent
    return False
```
Every table the old walk answers True for is still True (it returned True only on a claude.exe, and this walk still
reaches every process the old one reached); the old False cases at a break flip to True unless a session process came
first. Dry run 2026-10-24 (sandbox copy): every case of section 7.3 holds.
`_claude_ancestor` (sign.py:770-779) is unchanged (it already fails closed on a failed snapshot or a missing own pid).

### 7.2 Refusal text (sign.py:810-811), new
```python
    if _claude_ancestor():
        return ("a parent process is claude.exe, or the parent chain stops at a process that has exited: open Windows "
                "Terminal yourself from the Start menu and run me there, never under Claude")
```
Help text: the "Every time, before you type the passphrase" list (sign.py:22-31) gains a first bullet
`  - open Windows Terminal yourself from the Start menu (an editor's terminal can be refused: its parent chain may
    stop at a launcher that has exited);`. The module docstring's sign.py:3 `run under Claude, under a claude.exe
parent process, without a terminal on stdin, or without python.exe -I.` becomes two lines:
`run under Claude, under a claude.exe parent process, when its parent chain stops before a Windows session process,`
/ `without a terminal on stdin, or without python.exe -I.` No test pins the help text or the docstring (grep,
2026-10-24).

### 7.3 Tests (`tests/compliance_signer.py`)
- `test_claude_ancestor_walk` (:285-293), rewritten (two flips: :289 cycle and :290 empty table now True):
```python
def test_claude_ancestor_walk():
    """R5, R11: a claude.exe anywhere in the chain refuses, even above a session process, and so does a walk that
    breaks (an exited parent, a pid-reuse cycle, more than 256 steps) before it has passed a session process."""
    table = {10: (9, "python.exe"), 9: (8, "cmd.exe"), 8: (7, "Claude.exe"), 7: (0, "explorer.exe")}
    assert signer._has_claude_ancestor(10, table) is True
    assert signer._has_claude_ancestor(9, {**table, 8: (7, "WindowsTerminal.exe")}) is False
    terminal = {20: (21, "python.exe"), 21: (22, "powershell.exe"), 22: (23, "WindowsTerminal.exe"),
                23: (24, "svchost.exe"), 24: (25, "services.exe"), 25: (99, "wininit.exe")}      # 99 has exited
    assert signer._has_claude_ancestor(20, terminal) is False
    renamed = {1: (2, "python.exe"), 2: (3, "winlogon.exe"), 3: (4, "bash.exe"), 4: (5, "claude.exe"),
               5: (0, "explorer.exe")}                       # cmd.exe saved as winlogon.exe, run under Claude
    assert signer._has_claude_ancestor(1, renamed) is True
    assert signer._has_claude_ancestor(1, {1: (2, "a.exe"), 2: (1, "b.exe")}) is True           # pid-reuse cycle
    assert signer._has_claude_ancestor(5, {}) is True
    assert signer._has_claude_ancestor(30, {30: (31, "python.exe"), 31: (32, "Code.exe")}) is True   # 32 exited
    assert signer._has_claude_ancestor(40, {40: (41, "python.exe"), 41: (0, "CLAUDE.EXE")}) is True
    deep = {**{n: (n + 1, "python.exe") for n in range(1, 300)}, 300: (0, "wininit.exe")}
    assert signer._has_claude_ancestor(1, deep) is True                                          # the 256-step cap
    if os.name == "nt":
        live = signer._process_table()
        assert live[os.getpid()][0] == os.getppid(), live.get(os.getpid())
```
- `test_claude_ancestor_check_fails_closed` (:296-311) gains
  `with _patched(signer, "_process_table", lambda: {me: (me + 1, "python.exe")}): assert signer._claude_ancestor() is True`
  (a parent that has exited); `{me: (0, "python.exe")}` stays False.
- `test_main_refuses_claude_parent_and_non_tty_stdin` (:219-231): the first assertion becomes
  `assert code == 2 and "claude.exe" in err and "has exited" in err, (code, err)`.

Expected after Task 5: `compliance_signer/` `38/38 passed, 0 failed, 0 not run`.
Owner act (in the plan's hand-off, not done by Claude): sign.py changed in Tasks 4 and 5. Owner act 1 (spec 11) is not
done yet, so the owner copies the merged `tools/signer/sign.py` then. If the owner already copied an earlier version:
read the diff, run `certutil -hashfile %USERPROFILE%\tradegen-signer\sign.py SHA256`, and write the new hash on paper.

## 8. Alerts: `core/compliance/alerts.py` `log()` (Task 6; R6)

- Row (alerts.py:253-254) stays, followed by
```python
    if summary["code"] > 2:                     # R6: a code 3 or 4 summary may name a key the log does not verify
        row["fingerprint"] = ""
```
  placed before the `_in_log` check (alerts.py:255).
- Docstring (alerts.py:243-247): "the first fingerprint recorded is the one the key is held to (P20)" becomes "the first
  fingerprint recorded is the one the key is held to (P20), so a row keeps the summary's fingerprint only when its code
  is 0, 1 or 2; a code 3 or 4 summary (a broken log, KEY CHANGED, a failed check) can come from a key the log does not
  verify, and its row records an empty fingerprint".
- Test, new in `tests/compliance_cli.py` after `test_log_rows_carry_anchor_and_fingerprint` (:592-623):
```python
def test_log_records_a_fingerprint_only_from_codes_0_to_2():
    """R6 (ledger:219): the key is held to the first fingerprint alerts.jsonl records (P20), so a code 3 or 4
    summary, which can come from a key the log does not verify, records "" and never becomes that first one."""
    now = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)
    other = "SHA256:" + "0" * 64
    alerts.log("email", "ok", _sample(code=3, fingerprint=other), now)
    alerts.log("push", "ok", _sample(code=4, fingerprint=other), now)
    assert [r["fingerprint"] for r in _alerts_lines()] == ["", ""], _alerts_lines()
    assert owner._first_recorded() is None and alerts._first(alerts._history()) is None
    alerts.log("email", "ok", _sample(code=0), now)
    assert owner._first_recorded() == (FP, "2026-10-23T00:00:00Z")
```
  (`_sample`, `_alerts_lines`, `FP` exist at tests/compliance_cli.py:164-180, :30.) `test_log_rows_carry_anchor_and_
  fingerprint` (code 1) and the hand-built histories of :517-545 are unaffected.

Expected after Task 6: `compliance_cli/` `36/36 passed, 0 failed, 0 not run`.

## 9. Data layer (Task 7; R8, R12)

- `data/krx/kis_client.py` `token()` (kis_client.py:169-196): after :174-175 `if cached:` / `return cached`, insert
  `            checked_target(_TOKEN_PATH, "KIS token cache")      # A0: refuse before the POST burns an issuance (R8)`
  so it precedes :176 `app_key, app_secret = config.kis_credentials()`. `_store_token` (:157-167) is unchanged.
- `core/ficc/data.py` `_cache_put` (data.py:269-279): :273 `_MEM[key] = (now, rows)` and :274 `target = checked_target(...)`
  swap, and :273's new place carries the comment `# after the check: a refused key is never served from memory (R8)`.
- Tests in `tests/compliance_isolation.py`:
  - New, after `test_kis_token_writer_refuses_a_hard_linked_target` (:247-258):
    `test_kis_token_is_refused_before_the_token_request`: inside `_fake_quantgen()`, a hard-linked `scratch /
    "kis_token.json"` as `kis_client._TOKEN_PATH`; `client = object.__new__(kis_client.KISClient)` with `client.ready
    = True`, `client.base_url = "https://example.invalid"`, `client.timeout_s = 1.0`; `config.kis_credentials` patched
    to a recorder (`lambda: calls.append("credentials") or ("k", "s")`, the T-RO-02 pattern of
    tests/macro_m1_pit.py:1072) and `kis_client._once` patched to an object whose `.post` records and raises, each
    saved and restored in `finally`; `_refused(client.token, "hard link")`; then `calls == []`, no POST recorded, and
    the victim's bytes unchanged. Before R8 it fails: `token()` reads the credentials and posts first.
  - `test_ficc_cache_writer_refuses_a_hard_linked_target` (:295-306) gains, right after the `_refused(...)` line,
    `assert "A0_PROBE_1" not in D._MEM, "a refused key was cached in memory"`. Its `finally` pop stays.
- Other suites that load these modules: engine (test_89 stubs `client.token`), macro (T-RO-02 re-execs kis_client,
  macro_m0_rules state paths), expansion (fake KIS transports), ficc and quant (the FICC cache). Run `--suite engine`,
  `--suite macro`, `--suite expansion`, `--suite ficc`, `--suite quant` after Task 7, restoring the results file after
  each.

Expected after Task 7: `compliance_isolation/` `16/17 passed, 0 failed, 1 not run` (REFDATA symlink).

## 10. Final task (Task 8)

- Full suite with the overlap check: `.venv/Scripts/python.exe tests/run_all.py; echo "exit $?"`. Expected 0 failed.
  Expected counts from the tasks above: compliance 327 rows (325 PASS / 2 NOT_RUN, was 315/2 at README.md:839); full
  1176 rows (1053 PASS / 123 NOT_RUN, was 1043/1166 at README.md:840) when no other suite's REFDATA changed. The numbers
  the run prints win over these.
- `README.md` (CRLF, Edit tool): the compliance row's last cell (README.md:839, `| 315 PASS / 2 NOT_RUN |`) and the
  Total row's last cell (README.md:840, today "1043/1166 passed, 0 failed, 123 not run (2026-10-24, TRADEGEN
  .venv)" with `.venv` in backticks) get the run's counts and date. Check `git diff --stat` equals
  `git diff --stat --ignore-cr-at-eol`.
- Real-home check, read-only: list `~/.tradegen/compliance` (relative path, size, mtime_ns), run
  `.venv/Scripts/python.exe -m core.compliance.rules --check`, expect exit 3 ("no owner key yet: owner act 1"), list
  again, expect no change.
- Commit `README.md` and `qa/acceptance_results.json` together.
- The execution ledger `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` is written by the
  executor during and after execution, not by the plan. Merge per superpowers:finishing-a-development-branch after the
  final review; the odds plan then branches from the merged main.

## 11. Not in scope (documented so a reviewer does not re-raise them)

- **H2** (ledger:188, and the carry item at ledger:239): moves to the execution spec (E2, the halt writer), which has a
  trusted clock. No production caller of `append_system_entry` exists (owner.py:400 is its only occurrence outside
  tests), so H2 is latent. tests/compliance_owner.py:958-960 keeps pinning today's behaviour.
- **T2** (ledger:189): a documented limit; it needs the owner's own key and a backdated signer clock, and the signer
  shows the stamp (sign.py `_confirm`). The only outside time source (alerts.jsonl rows) would change owner_state's pure
  signature (A.8.3).
- **Snapshot cross-check** (ledger:204): within spec 6.4's stated limits (exits only, under a broken log).
- **Every other item on the execution carry list** (ledger:239 except "KIS token burnt on refusal", which R8 takes;
  ledger:244; ledger:155).
- **Deferred minors not ruled in** (each fails closed or is test-only today): clock_gettime and alias routes (ledger:64);
  reversed `"__main__" == __name__` in `_main_block_hits` (ledger:70); an untested refusal from
  `config.ficc_cache_dir()` (ledger:83); unbounded reason length (ledger:93); bytearray in load_strict (ledger:95);
  dict-equality scalar tests (ledger:96); non-str venue items (ledger:104); "D0016" untested (ledger:107); the
  2027-01-01 affected_by row (ledger:114, a table change); jsonable key stringification (ledger:123, :126); malformed
  plans (ledger:158); purity-scan hardening (ledger:159); nested duplicate keys and BROKEN-path tests (ledger:169,
  :180); owner_state date/now and ArithmeticError (ledger:178, :179); huge ints and double reads of positions
  (ledger:202, :203); store_get framing (ledger:209); alerts row and stdout edge cases (ledger:216, :218, :220); signer
  state_root and keygen edge cases (ledger:230, :231); the signer's pem-beside-the-key and keygen-text items, the rest
  of ledger:233 after R5 and the final wave; ancestor junctions of the state root (ledger:86, a design question). The
  ACCEPT items of DIGEST 8.5 (ledger:65-67, :71, :92, :94, :105, :147, :148, :186, :115, :134) stay accepted, and so do
  the ACCEPT lines of map/followup.md section 8: ledger:84, :102, :116, :124, :125, :132, :136, :138, :161, :172, :196,
  :205. Every line of map/followup.md section 8 not named in this plan keeps its class there.
- **Already closed, so not re-raised:** ledger:74, :80, :133, :145 by the final fix wave (ledger:238); :75 and :242 by
  R1; :103, :113, :146, :243 by R2; :118 by R3; :208 by R4; the walk part of :233 by R5, in line with the :229 ruling
  that a refusal check fails closed (its rotation-help part was fixed at :238); :219 by R6; :69 by R7; :81, :82 by R8.
- **Execution-side items:** ledger:144 (a derived destination buy keeps the source's asset and multiple; no shipped
  path), :150 (a transfer's reservation_id carried into the destination buy) and :157 (a permit issued with session_id
  None), the same family as the carried session and reservation items.
- **Odds-side items:** the venues parser keys, `calendar_in_force`, `grey_rows`, the fixtures move (RULINGS O3), the
  zero stake (ledger:244), the yfinance cache, KONEX structural_max; ledger:68 (the guards' clean asserts over core/odds
  become non-vacuous once it holds .py files) and :101 (never `asdict` or `deepcopy` a Row: `match` is a
  MappingProxyType). The odds plan owns them.
- **Documented limits from the repo map (DIGEST 8.2, 8.4):** the D14 seeds are non-recursive (owner.py:773 `.glob`)
  while the guards scan with rglob (guards:69), so a .py file in a core/compliance subfolder is scanned but is in the
  closure only once a closure file imports it (none exists today; the odds guards refuse a core/odds subfolder); a
  package `__getattr__` re-export (core/calendars/__init__.py:224-229) escapes D14, and neither allowlist lets
  core/compliance or core/odds import that package; `screen` ignores `effective_from` (gate.py:645-648), so a row that
  starts mid-horizon is not flagged (nothing is lost today; the odds plan reads the screening flags, RULINGS O5).
- **Owner acts:** OKX USDT/USDC deposit networks (ledger:112, :120); copying the updated signer (section 7); signing.

## 12. Effects on the odds plan (it runs second)

- Line numbers the odds rulings cite move once this merges: rules.py (`_VENUE_OPTIONAL` at :636-642 moves down by
  31 lines, section 4), tests/compliance_tables.py (`minimum_krw` at :633 moves down by several dozen lines, the
  new tests sit after :300), tests/compliance_store.py (the signed-home helpers at :242-299 move down by about 20 to
  30 lines, the ten synthetic files of section 6.4), and tests/compliance_guards.py:488-489 is gone (R7). The byte pins
  in tests/compliance_gate.py do not move (that file is not edited).
- The odds plan is written against main `5816d3c`, before this plan's code exists, and E1 likewise; both carry the
  DRIFT RULE (R2-13, section 0) for the files this plan changes (core/compliance/rules.py, owner.py, alerts.py,
  kr_rules.yaml, tests/compliance_guards.py, tests/compliance_tables.py, tests/compliance_store.py,
  tests/compliance_signer.py, tests/compliance_cli.py, tests/compliance_isolation.py, tools/signer/sign.py,
  data/krx/kis_client.py, core/ficc/data.py): they find their quoted anchor in the merged tree and make their change
  there, keeping this plan's behaviour. This plan renames no function, constant or test it touches (it only adds
  names and changes bodies), so every name they anchor on still exists after it merges.
- New `core/odds/*.py` files must pass the widened DYNAMIC_* lists (no pickle, marshal, unittest, logging.config,
  pstats, tracemalloc, importlib other than metadata, no attribute of the name `importlib` but `metadata`, bare
  compile). `core/oddsdata/` is outside both guard scopes (RULINGS O1, O2). The odds guards read the lists from
  `tests/compliance_guards.py` at test time and pin no entry count, so R2-10 binds core/odds with no odds code
  change; only the odds contract's prose list of the F1 additions (odds/CONTRACT.md, the "no import of
  `importlib.util`, ..." bullet) lacks `pstats` and `tracemalloc` (raised for the odds drafts, not edited here).
- The odds guards' allowlist ("the stdlib minus NETWORK_MODULES and DYNAMIC_MODULES") tests each import target with
  `compliance_guards._dynamic_module`, never a raw prefix match over DYNAMIC_MODULES, so `importlib.metadata` stays
  allowed as the odds contract says (section 3.10).
- The odds suite registers `odds` in tests/run_all.py:113 and README.md:816 with no compliance test change (R7).
