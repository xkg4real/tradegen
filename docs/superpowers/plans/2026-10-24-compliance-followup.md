# TRADEGEN compliance follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the merged compliance gate before the owner's first signature. It covers:
- the static guards: the whole `xml.dom` package, the modules that run code from strings or data, every `importlib`
  import but `importlib.metadata`, the bare `compile()`, and a suite-list check that survives new suites (F1, F7);
- the rules loader: D15 and D16 enforced by row content, D15 rows always blocking, bounds on `review_by`,
  `max_leverage` and the `{cap}` slot, and exact pins of the 15 shipped rows that can let an intent through (F2);
- one table sentence: the KR-KIS-KRX-DERIV reason names broker approval (F3);
- the D14 closure scan and its signer copy: a guard counts only while its name is unbound (F4);
- the signer's Claude-ancestor walk: it fails closed when the parent chain breaks before a Windows session process,
  and still refuses on a claude.exe anywhere in the chain (F5);
- the alerts log: a key fingerprint is recorded only from a check that verified the log (F6);
- two A0 data-layer minors: the KIS token target is checked before the token POST, and the ficc memory cache is set
  only after its target check (F8).

Every change only adds refusals. No order is placed, no money moves, and nothing is signed.

**Architecture:** No new module and no new file outside the tests. Each fix sits at the narrowest place every caller
already passes through: the guard tuples and `_dynamic_hits` in `tests/compliance_guards.py`; `_row` in
`core/compliance/rules.py`; `_skipped` and a new `_guards` helper in `core/compliance/owner.py`, copied character for
character into `tools/signer/sign.py`; `_has_claude_ancestor` in the signer; `log()` in `core/compliance/alerts.py`;
`KISClient.token()` and `_cache_put`. Three closure files change (`rules.py`, `owner.py`, `alerts.py`), so the D14 code
hash moves; one table changes (`kr_rules.yaml`), so its sha moves. The odds plan runs after this one, from the merged
main, so the owner signs the code hash once, after both.

**Tech Stack:**
- Python 3.13.14 in `.venv`; PyYAML 6.0.3; `cryptography` 49.0.0 (already installed; this plan installs nothing);
- the repo's own runner `tests/run_all.py`. There is no pytest.

**Spec:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` (rev 3.2, `b5603f5`), with
the controller's follow-up rulings F1 to F8 of 2026-10-24 (restated below as R1 to R8) and their round-2 amendments
R2-10 to R2-13 (pstats and tracemalloc banned too; the branch base checked, not pinned; the R4 limit accepted as
stated; the drift rule). These depart from rev 3.2 in stricter directions and are listed for spec rev 3.3:
- 4 "Guards": the network and dynamic import bans named in R1, and the bare `compile`;
- 5.2 "Loading": D15 by content and by label, D16 by content (beside "Every row citing D16 must carry requires.live";
  a row with no class axis on an ETP asset counts as matching the leveraged and single-stock classes), `review_by`
  not before the latest review, `max_leverage <= 10`, `{cap}` only in grey warnings;
- 5.3: the KR-KIS-KRX-DERIV reason text;
- 6.4 "The code hash": an `if TYPE_CHECKING:`, `if typing.TYPE_CHECKING:` or `__name__ == "__main__"` guard is
  skipped only while the module neither rebinds its name nor uses a route that changes it without a binding (an
  attribute store, setattr, globals, sys.modules, a frame's f_globals or f_locals and the like). Stated limit:
  another module changing `typing.TYPE_CHECKING` before this one is imported, or a route through `getattr`
  (`getattr(sys, "modules")["typing"] = ...`), is not seen; the owner's review of each hashed diff covers it;
- 6.4 "Where it runs": the signer also refuses when its parent chain breaks before a Windows session process (a
  claude.exe anywhere in the chain still refuses, even above one);
- 6.4 "Public key and fingerprint": `alerts.jsonl` records a fingerprint only from a check with exit 0, 1 or 2;
- 4 "Isolation residual": the KIS token and ficc cache targets are checked before their side effects;
- stated limits the controller accepted at this plan's final review (none loosens a rule):
  - 6.4 "Public key and fingerprint" (Task 6): between owner act 1 and the first check that exits 0, 1 or 2, no
    fingerprint is recorded, and the paper fingerprint from owner act 1 is the only reference; new exposure stays
    blocked throughout, since every check exits 3 until owner acts 2 and 3 (an exit-0 check writes no alerts row,
    so the first recorded fingerprint comes with the first alert of an exit 1 or 2 check; Task 6 gives the timing);
  - 4 "Isolation residual" (Task 7): kis_client's token read path is left as is (`_cached_token()` reads the token
    file before any check; a read, not a write, so outside A0 and R8);
  - 6.4 "Where it runs" (Task 5): the fail-closed ancestor walk refuses VS Code integrated terminals (their chain
    stops at a launcher that has exited), so the owner signs from Windows Terminal opened from the Start menu;
  - R4 (Task 4): the frame route is closed (`f_globals`, `f_locals` are route names); `getattr` cannot be listed
    (gate.py, model.py, rules.py, alerts.py and `owner._binds` call it), so `getattr(sys, "modules")["typing"]`
    stays a stated limit.
GPT's final check runs after 2026-10-30 14:40. This plan does not wait for it: a valid finding that touches built code
becomes a new task with its own failing test.

> This is research and software design, not legal, tax or investment advice. Neither TRADEGEN nor its author is a
> licensed advisor.

## Global Constraints

Every task's requirements include this section. Values are copied from the spec, the rulings and the verified repo map.

**Hard rules from the owner's brief**
- Never arm the system, place a live order, or enter credentials or keys.
- Never edit anything under `C:\Users\whydi\OneDrive\Desktop\QUANTGEN`. Never write under `~/.nextgen`. Never run
  anything while QUANTGEN's test suite runs.
- Never delete `grokteam/PREREG_book.json` or `grokteam/out/frozen_book/`.

**Signing, the owner log and the signer**
- Claude never runs `tools/signer/sign.py` with a real key. Claude never asks for or handles the owner's passphrase.
- Claude never writes to the real `~/.tradegen/compliance/owner.jsonl`.
- Tests load the signer with `importlib.util.spec_from_file_location`, build owner logs only inside a temporary
  `TRADEGEN_HOME`, and sign them with the fixed test key.
- The repo signer is a proposal (spec 6.4). Updating the owner's copy is an owner act: read the diff, re-hash,
  re-record.

**No owner signature exists yet.** `core/compliance/owner_pubkey.pem` is absent (owner act 1 is not done), so no
`code_approved` and no table approval is in force, and `--check` exits 3 in the real home. Nothing this plan changes
needs re-signing now. Once the owner signs `code_approved` (owner act 2), every later change to a file of the D14
closure (`core/__init__.py`, `core/isolation.py`, `core/compliance/*.py`, `core/odds/*.py` and their in-repo imports)
needs a fresh `code_approved`; once the owner approves a table (owner act 3), every byte change to it needs a fresh
`approved {kind}`, and a tightened loader can turn an approved table INVALID.

**Python and test runs**
- Interpreter: `.venv/Scripts/python.exe`, which is Python 3.13.14. Never `pip install` anything.
- A test is a zero-argument `test_*` function that raises on failure. There is no pytest.
- Overlap check: run it before every test command. It must print nothing; otherwise wait. QUANTGEN's Store Python
  runs as `python3.13.exe` with no `python.exe` beside it, so only a `python*` name filter sees it.
  - PowerShell tool:
    `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`
  - Git Bash prefix. The PowerShell script is in single quotes, so Bash leaves `$_` alone:
    `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`
- One test or module: `.venv/Scripts/python.exe -m tests.compliance_acceptance <module>/<test>`. This does not write
  `qa/acceptance_results.json`.
- One suite: `.venv/Scripts/python.exe tests/run_all.py --suite <name>`. This rewrites the tracked
  `qa/acceptance_results.json`. Restore it with `git checkout -- qa/acceptance_results.json` afterwards. Only Task 8
  commits that file.

**Files, line endings and commits**
- Every file this plan edits is LF, except `README.md` (CRLF, Task 8 only). `tests/run_all.py` (CRLF) is not edited.
- Edit existing files only with the Edit tool, never `sed -i`. Git Bash hides the CR of a CRLF file from `grep` and
  `sed`, so check line endings with `git ls-files --eol <path>` or Python bytes.
- Before every commit, `git diff --cached --stat` must equal `git diff --cached --stat --ignore-cr-at-eol`.
- Work on branch `compliance-followup`, which Task 1 creates from main's HEAD at execution time, not from a pinned
  hash. First, on `main`, `git status --short` and `git diff --stat 995534b HEAD -- . ':!docs'` must both print
  nothing (only docs changed since the compliance merge `995534b`); if either prints anything, stop and report.
  Commit once per task (Task 8: the full-run record, the ledger, and a repeat record after a review fix wave). End
  each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Pushing (round-3 ruling G3-3, 2026-10-28; the repo is public by the owner's choice): after each task's review
  passes, the controller pushes the branch (`git push -u origin compliance-followup` the first time, `git push` after
  that). No subagent pushes. The plan ends in one pull request; Task 8's merge step becomes "open the pull request",
  and merging it stays the owner's choice.

**Drift rule.** This plan was written against main `5816d3c`, which equals `995534b` outside docs/. It executes first,
after this plan, the odds plan and the E1 plan are committed to main as docs.
- Every Edit in a task quotes its old text exactly from that tree and names its anchor: the function, constant, test,
  YAML row or table row it sits in. A cited line number is that of `995534b` and only helps find the anchor.
- Line numbers move as earlier tasks of this plan land (Task 2 before Tasks 3 and 6, Task 4 before Task 5). The anchor
  wins.
- Re-read the file before each Edit. If the quoted old text differs only because an earlier plan changed it, apply the
  same change to the current text, keep the earlier behaviour, and record a one-line ruling in the execution ledger
  (`docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`). If the change no longer makes sense,
  stop and rule.
- Task 1's check proves that no earlier plan has changed a file outside docs/. The odds and E1 plans carry the same
  rule for the files this plan changes.

**Guards on `core/**/*.py`.** They scan raw text, so docstrings and comments count.
- Never write upper-case `CANO` (so never `CANONICAL`), `KIS_ACCOUNT` or `ACNT_PRDT_CD`.
- Never write `order_cash`, `order-cash`, `place_order`, `submit_order`, `TTTC0802U`, `TTTC0801U` or `VTTC0802U`.
- Never write `private_key` or `seed_phrase` in any form.
- Never call, and never define, a function named `transfer`, `withdraw` or `deposit_address`.
- Never use `.post`, `.put`, `.delete`, `.patch` or `.request` in `core/compliance`.
- `core/compliance/*.py` may import only the stdlib, `yaml`, `cryptography` (lazily, inside functions),
  `core.isolation` and `core.compliance.*`. After Task 1 the stdlib excludes the 26 network modules and the 29 dynamic
  modules of R1 (`importlib.metadata` stays allowed), and no file in `core/compliance` or `core/odds` may use the bare
  name `compile` or an attribute of the name `importlib` other than `metadata`.
- No wall-clock call anywhere in `core/compliance/`, except in the CLI `main()` of `rules.py` and `alerts.py`.

**Writes and encodings**
- Every file the code writes goes through `core.isolation.checked_target()` before anything else happens for it.
- Every text open passes `encoding="utf-8"`.

**Values fixed by the rulings and the verified tree**
- Shipped rules table: 47 rows, 15 of them allow, gated or grey; sha `127a3c91...551bd3b79` before Task 3 and
  `74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd` after it.
- Loader bounds: `max_leverage <= 10`; `review_by >=` the latest review date; `{cap}` only in a grey warning.
- Signer session roots: `explorer.exe`, `services.exe`, `wininit.exe`, `winlogon.exe` (case-insensitive); a session
  process never ends the walk; a break (an exited parent, a cycle, 256 steps) refuses unless one came first.
- Compliance suite at the start: 317 rows, 315 PASS / 2 NOT_RUN (README.md:839); full run 1043/1166, 123 NOT_RUN
  (README.md:840). Expected at the end: compliance 327 rows (325 PASS / 2 NOT_RUN), full 1176 (1053 PASS / 123
  NOT_RUN).

## Decisions this plan makes

The tasks cite these as R1 to R13. R1 to R8 restate the controller's rulings F1 to F8, as amended by the round-2
rulings R2-10 to R2-13; R9 to R13 are readings this plan adds where a ruling is silent. None of them loosens
anything. GPT's 2026-10-30 check should read this list together with the spec. Appendix A (the interface contract)
gives each one's exact old and new text.

The ruling ids cited in the tasks and in Appendix A:
- F1 to F8: the controller's follow-up rulings of 2026-10-24 on the parked and deferred items of the compliance
  plan's execution ledger; R1 to R8 below restate them, one for one.
- R2-10: pstats and tracemalloc join the dynamic-module ban (stricter than F1). R2-11: the branch starts from main's
  HEAD at execution time, checked, not pinned. R2-12: R4's denylist limit is accepted as stated. R2-13: the drift
  rule of Global Constraints. (Round-2 rulings R2-1 to R2-9 concern the odds plan only.)
- O1, O2, O3, O5: rulings of the odds plan, cited where this plan touches it. O1: the signed odds core
  (`core/odds/`) and its import allowlist ("everything injected"; `core/oddsdata/` is outside it). O2: the odds
  plan's own guards, which import this plan's guard lists instead of copying them. O3: the compliance-side
  prerequisites the odds plan's first tasks do (the venues parser keys, `calendar_in_force`, `grey_rows`, the move
  of the signed-home fixtures). O5: `review_by` and rule dates inside a simulated horizon.
- P<n> are the compliance plan's own decisions (its header), D<n> the spec's decisions.

The decisions:

- R1 (F1, amended by R2-10) `tests/compliance_guards.py` only. `NETWORK_MODULES` goes from 22 to 26 entries:
  `xml.dom` replaces `xml.dom.pulldom` and `xml.dom.expatbuilder`, and `antigravity`, `ctypes`, `_ctypes`, `_ssl`,
  `_overlapped` join. `DYNAMIC_MODULES` goes from 9 to 29: `importlib` replaces `importlib.util` and
  `importlib.machinery`, and `profile`, `pdb`, `bdb`, `trace`, `doctest`, `unittest`, `logging.config`, `pickle`,
  `_pickle`, `shelve`, `marshal`, `site`, `ensurepip`, `venv`, `tkinter`, `_tkinter`, `turtle`, `turtledemo`,
  `idlelib`, `pstats`, `tracemalloc` join; `DYNAMIC_EXEMPT = "importlib.metadata"`. The bare name `compile` is banned
  (`DYNAMIC_BARE`), never the attribute, so `re.compile` stays legal. `from xml.dom import minidom` moves from the
  negative control to the positives; logging, xml.etree, importlib.metadata and subprocess stay negative controls, and
  faulthandler joins them: it stays unbanned because it runs no string and opens nothing, and the comment says so.
  pstats and tracemalloc are banned by round-2 ruling R2-10, which is stricter than F1 (F1 had them unbanned): their
  own APIs load files, `pstats.Stats` with marshal and `tracemalloc.Snapshot.load` with pickle. Every new entry has a
  positive control.
- R2 (F2) `core/compliance/rules.py` `_row`. An allow, gated or grey row may not match financing `credit` or `margin`,
  nor action `lend` or `borrow` (D15 by content); a row citing D15 is `hard_block` or `out_of_scope`; a non-blocking
  row that matches `sell_short`, the class `etp_leveraged`, `etp_single_stock`, `krx_derivative` or `elw`, or the
  asset `krx_derivative` or `elw` needs `requires.live` (D16 by content; a row with no class axis that names the asset
  `krx_etp` or `us_etp` matches every ETP class, so it counts as matching `etp_leveraged` and `etp_single_stock`; the
  D16 label rule stays); `review_by` is not
  before the latest review; `max_leverage <= 10`; `{cap}` appears only in a grey warning. The 15 shipped non-blocking
  rows are pinned exactly as (match, requires_owner, requires_live, treatment). The shipped table stays VALID and
  byte-identical.
- R3 (F3) `core/compliance/kr_rules.yaml:204`: the KR-KIS-KRX-DERIV reason starts "KOSPI200 futures and options need
  broker approval, ...". It changes the table sha; no approval exists yet.
- R4 (F4) `owner._skipped` and the signer copy: `if typing.TYPE_CHECKING:` is skipped only when `typing` is bound
  exactly once in the module, by a plain `import typing`; `if __name__ == "__main__":` only when `__name__` is bound
  nowhere. A binding is not the only way to change these names, so no guard counts at all in a module that stores to
  an attribute `TYPE_CHECKING` or `__name__` or uses `setattr`, `delattr`, `globals`, `vars`, `locals`, `modules`,
  `__dict__`, `builtins`, `__builtins__`, `f_globals` or `f_locals` (none of the 8 closure files does; the two frame
  names close the frame route, by the controller's ruling at the final review). Both files stay character-identical
  in the closure helpers, and a test compares their source. Stated limit, accepted as stated by round-2 ruling
  R2-12: the route list is a denylist, so another module changing `typing.TYPE_CHECKING` before this one is
  imported, or a name built at run time, is not seen (`getattr` cannot be listed, so `getattr(sys,
  "modules")["typing"]` is one); the owner's review of each hashed diff covers it.
- R5 (F5) `sign._has_claude_ancestor`, repo copy only: a parent missing from the process table, a pid-reuse cycle or
  more than 256 steps now refuse (True), where they returned False, unless the walk has already passed a Windows
  session process (R11). The walk still reaches every process the old one did, so a claude.exe anywhere in the chain
  refuses as before. The refusal text names the cause. The owner's copy changes only by the owner act above.
- R6 (F6) `alerts.log()`: a row records the summary's fingerprint only when its code is 0, 1 or 2; a code 3 or 4 row
  records "". The first recorded fingerprint, which the key is held to (P20), therefore always comes from a check
  that verified the log.
- R7 (F7) The registration test reads the "one suite: ... or ..." lists of `tests/run_all.py` and `README.md` and
  asserts that `compliance` is one of their names, instead of the literal "paper, grokteam or compliance".
- R8 (F8) `KISClient.token()` checks `_TOKEN_PATH` with `checked_target` before reading credentials and before the
  token POST, so a refused target burns no issuance; this takes "KIS token burnt on refusal" off the execution carry
  list. `ficc _cache_put` checks its target before it sets `_MEM`, so a refused key is never served from memory.
- R9 (reading of R1) The bare `import importlib` is a dynamic import too (its own API is `import_module`, `reload` and
  `__import__`). In the dynamic scan, `from X import a` is judged by `X.a`, so `from importlib import metadata` stays
  legal. `import importlib.metadata` binds the name `importlib`, so any attribute of it but `metadata`
  (`importlib.util`, `importlib._bootstrap`) is a hit too. `importlib.metadata`'s `EntryPoint.load` string import and
  an alias of the name stay documented limits: the lists are a denylist, not a proof.
- R10 (reading of R2) The new loader checks sit after `_match` and the axis check, the D16 label check and the
  warning-slot checks, so every existing reason keeps its text. Three existing assertions flip on purpose and are
  rewritten: tables:295 (a gated etp_leveraged row citing D160 without live evidence), tables:316 (`{cap}` in an
  allow row's warning) and tests/compliance_cli.py:576-577 (the free-text test appends `{cap}` to every shipped
  warning, the gated KR-KIS-US-OPTION one included; it now appends it to the grey row only).
- R11 (reading of R5) The root of the ancestor walk is pid 0, or a break after the walk has passed a Windows session
  process (`explorer.exe`, `services.exe`, `wininit.exe`, `winlogon.exe`). Evidence, from the live process table on
  2026-10-24: every chain on this PC ends at a parent that has exited, and the owner's Windows Terminal chain is
  `powershell.exe -> WindowsTerminal.exe -> svchost.exe -> services.exe -> wininit.exe -> (exited)`, so pid 0 alone
  would refuse the terminal spec 6.4 names. A session process never ends the walk, because a process name is only a
  file name: a copy of cmd.exe saved as winlogon.exe under Claude is still refused, as today. An editor terminal whose
  launcher has exited is refused, and the refusal says to open Windows Terminal from the Start menu. Honest limits: a
  process started through COM activation or the desktop shell has no claude.exe ancestor, so this check stays defence
  in depth behind the passphrase and the typed code; a reused pid above a session process that now runs claude.exe
  refuses, as today, until Claude is closed.
- R12 (reading of R8) `_store_token` keeps its own `checked_target`; the new one in `token()` is one line.
- R13 (amended by R2-11 and R2-13) This plan runs first, on `compliance-followup` from main's HEAD at execution time,
  after Task 1 checks that nothing outside docs/ changed since `995534b`; the odds plan runs second and E1 third, each
  from main after the one before merges, each under the drift rule above. None waits for GPT's check.

Not in scope, with the reason recorded in Appendix A section 11: H2 (moves to the execution spec's halt writer, which
has a trusted clock), T2 (a documented limit: it needs the owner's own key and a backdated clock), the snapshot
cross-check (within spec 6.4's stated limits), every other item on the execution carry list (ledger:239, :244, :155),
the deferred minors the rulings did not take in (each ledger line named there; every other line keeps the class the
repo map gives it), and three documented limits from the repo map: the non-recursive D14 seeds, the package
`__getattr__` re-export of core/calendars, and `screen` not flagging `effective_from`.

Companion documents:
- **Appendix A** below is the interface contract the tasks were drafted against. Where a task's text and Appendix A
  differ, the task wins.
- **The repo facts** this plan rests on are the `followup` area of the 2026-10-24 repo map (each with file:line
  evidence), re-checked against the tree at `995534b` while the contract was drafted. It is committed beside this
  plan as `docs/superpowers/plans/2026-10-24-compliance-followup-repo-map.md`; where it and the tasks disagree, the
  tasks win.

## File map

| Path | Status | Task(s) | Responsibility |
|---|---|---|---|
| `tests/compliance_guards.py` | modify | 1 | R1 import bans, `_dynamic_module`, bare `compile`; R7 suite-list check |
| `core/compliance/rules.py` | modify (closure) | 2 | R2 loader rules in `_row` |
| `tests/compliance_tables.py` | modify | 2, 3 | R2 tests, two rewritten assertions, 15 exact row pins; R3 assertion |
| `core/compliance/kr_rules.yaml` | modify (table) | 3 | R3 reason text, line 204 only |
| `core/compliance/owner.py` | modify (closure) | 4 | R4 `_guards`, `_skipped`, `_import_nodes`, `_repo_imports` |
| `tools/signer/sign.py` | modify (off the closure; owner copy is an owner act) | 4, 5 | R4 identical copy; R5 ancestor walk, refusal text, help bullet |
| `tests/compliance_store.py` | modify | 4 | R4 synthetic closure tree |
| `tests/compliance_signer.py` | modify | 4, 5 | R4 synthetic tree and source-equality test; R5 walk tests |
| `core/compliance/alerts.py` | modify (closure) | 6 | R6 fingerprint only from codes 0-2 |
| `tests/compliance_cli.py` | modify | 2, 6 | R10 third rewrite (`{cap}` on the grey warning only, :576-577); R6 test |
| `data/krx/kis_client.py` | modify (off the closure) | 7 | R8 target check before the token POST |
| `core/ficc/data.py` | modify (off the closure) | 7 | R8 target check before the memory cache |
| `tests/compliance_isolation.py` | modify | 7 | R8 tests |
| `README.md` (CRLF), `qa/acceptance_results.json` (CRLF) | modify | 8 | the compliance count row and Total row; the full run |
| `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` | commit only (Task 8 Step 8); the executor writes it | 8 | the executor's record of every task, review, fix and drift ruling |
| `core/compliance/owner_pubkey.pem` | NOT created | - | appears only after owner act 1 (P24) |

## Owner gates during execution

None: this plan downloads nothing, schedules nothing and sends nothing.

After this plan (owner acts, done by the owner, never by Claude; Task 8 Step 9 gives the full text). The E1 plan
changes `tools/signer/sign.py` and the code hash again (its Task 9), so acts 1 and 2 done before E1 lands are redone
after it.
1. **The signer copy.** Owner act 1 is not done, so copy the merged `tools/signer/sign.py` when you do it. If you
   already copied an earlier version: read the diff of `tools/signer/sign.py`, run
   `certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256` in Windows Terminal (PowerShell), and
   write the new hash on paper. Sign from Windows Terminal opened from the Start menu: the fail-closed ancestor walk
   (Task 5) refuses a VS Code integrated terminal, whose parent chain stops at a launcher that has exited.
2. **One code signature, after the odds plan lands.** Owner act 2 signs the code hash once, covering this plan's and
   the odds plan's closure changes. Read the hashed files first, in full for the first signature: R4's stated limit
   relies on that review.
3. **The three tables, with act 2.** Owner act 3 approves `kr_rules.yaml` as Task 3 leaves it, `instruments.yaml`,
   and `core/odds/venues.yaml` as the odds plan leaves it.

Until then the shipped system stays in its safe default: every new-exposure intent is BLOCK and `--check` exits 3.

---

### Task 1: Branch and guards: xml.dom, string-exec modules, bare compile, the suite-list check

**Files:**
- Modify: `tests/compliance_guards.py` (LF; anchors: the module's import block; the constant `NETWORK_MODULES`; the
  dynamic-import comment and constants between `FORBIDDEN_MODULES` and `# base name -> attributes that read the
  clock`; the checker `_dynamic_hits`; the tests `test_no_http_verb_calls`, `test_no_forbidden_module_import`,
  `test_imports_stay_on_the_allowlist` and `test_suite_is_registered_in_run_all_and_readme`)
- Test: `tests/compliance_guards.py` (the guards are their own tests; 15 tests become 16)

No product file and no table changes. `tests/` is outside the D14 closure, so the code hash does not move.

**Interfaces:**
- Consumes (existing names in `tests/compliance_guards.py`, unchanged): `ROOT`, `X`, `COMPLIANCE`, `ODDS`,
  `_scope(*bases)`, `_walk(node)`, `_imports(rel, tree)` (yields `(node, absolute module, imported names, enclosing
  functions)`), `_forbidden_hits`, `_allowlist_hits(rel, src)` (keeps its own `[module] + [module.n]` targets),
  `DYNAMIC_NAMES` (unchanged); `tests.run_all.select(entries, suite="compliance")` and `tests.run_all.tests()`.
- Produces (Appendix A section 3.10; the odds guards import these and never copy them):
  - `NETWORK_MODULES`: 26 entries; `DYNAMIC_MODULES`: 29 entries; `DYNAMIC_NAMES`: unchanged;
    `DYNAMIC_BARE = frozenset({"compile"})`; `DYNAMIC_EXEMPT = "importlib.metadata"`.
  - `_dynamic_module(target: str) -> bool`: True for a dotted import target equal to or below a `DYNAMIC_MODULES`
    entry, False for `importlib.metadata` and everything below it. An import target is tested with this function,
    never with a raw prefix match over `DYNAMIC_MODULES` (`importlib` is an entry, so a raw match would drop
    `importlib.metadata`).
  - `_dynamic_hits(rel: str, src: str) -> list[str]`: signature unchanged. New hit texts:
    `"<rel>:<line>: importlib.<attr>"` and `"<rel>:<line>: compile"`.
  - `_suite_names(text: str) -> list[str]` (Appendix A sections 3.9 and 3.10). The odds guards do not import it, but
    the E1 plan's `tests/execution_guards.py` does, as `CG._suite_names`, in its registration test (the E1 plan's
    Appendix A sections 0.6 and 4.5), so its name and signature are fixed like the names of Appendix A section 3.10.
    The odds plan adds `odds` to the two suite lists without touching a compliance test.
  - New test `test_bare_compile_and_importlib_submodules_are_dynamic`. No name is renamed or removed.

**Plan decisions used:** R1 (as amended by round-2 ruling R2-10), R7, R9, R13 (as amended by R2-11); the drift rule
(R2-13) of Global Constraints.

Notes (read before Step 1):
- What the new bans close (repo map `followup` section 1; each was checked in the venv's own stdlib sources):
  - `xml.dom` as one package: `xml.dom.xmlbuilder`'s `DOMBuilder.parseURI` opens a URL with `urllib.request`, and
    both `minidom` and the bare `xml.dom.getDOMImplementation()` hand that builder out. So
    `from xml.dom import minidom` leaves the negative control and becomes a positive one.
  - `antigravity` opens a URL at import; `ctypes` and `_ctypes` call any DLL; `_ssl` and `_overlapped` are the C
    halves of `ssl` and asyncio's Windows transport.
  - The dynamic modules run code named in a string or read from data. `profile`, `pdb`, `bdb`, `trace` and
    `doctest` exec a string. `unittest` imports by string (mock.patch targets, the loader). `logging.config` builds
    classes from strings and runs a TCP listener. `pickle`, `_pickle`, `shelve` and `marshal` load objects and code
    from bytes. `site` execs `.pth` lines. `ensurepip` and `venv` run pip through runpy. `tkinter`, `_tkinter`,
    `turtle`, `turtledemo` and `idlelib` embed a Tcl interpreter with sockets (idlelib also execs). `pstats` and
    `tracemalloc` (R2-10) load files with marshal and pickle (`pstats.Stats`, `tracemalloc.Snapshot.load`).
  - `importlib` as a whole except `importlib.metadata` (R9): the bare `import importlib` is dynamic, and so are
    `importlib.resources`, `importlib.abc` and `importlib._bootstrap`. `import importlib.metadata` binds the name
    `importlib`, so any attribute of that name except `metadata` is a hit too (`importlib.util.spec_from_file_location`
    would otherwise load a file with no banned import). In the dynamic scan only, `from X import a` is judged by `X.a`,
    so `from importlib import metadata` stays legal; every other entry is still caught in every import form.
  - The bare builtin `compile` is banned as an `ast.Name` only (a call, a reference or a rebinding), so every
    `re.compile` in core/compliance (rules.py:155, :190, :383-386, owner.py:75-78, alerts.py:25-28) stays legal.
- What stays open, named as left to review (the counts of R1 are binding; banning more needs a controller ruling):
  `codeop` and `dis` compile a string (`codeop.compile_command`, `dis.Bytecode(src).codeobj`) that
  `types.FunctionType` runs; `_frozen_importlib` and `_frozen_importlib_external` are `importlib._bootstrap` and
  `importlib._bootstrap_external` under their sys.modules names (`SourceFileLoader(name, path).get_code(name)` loads a
  file), and `_imp.create_dynamic` loads an extension module; `_interpreters.run_string` runs a string. All six are in
  `sys.stdlib_module_names`, so the allowlist passes them; no file under core/, tools/ or tests/ imports one. The
  Edit 8 comment names them. Likewise `sqlite3`'s `Connection.load_extension` loads any DLL by path, as ctypes does;
  the Edit 10 docstring names it under "Not covered".
- Wording that differs from Appendix A (the task wins): Edit 8's comment reads "(importlib.util,
  importlib._bootstrap)" with no trailing ellipsis and adds the left-to-review sentence above; Edit 10's docstring
  adds the sqlite3 clause and ends "All three are left to review"; Edit 6's `_suite_names` docstring says
  "a, b or c" where Appendix A section 3.9 has a longer example. Behaviour is the same.
- What stays allowed, as negative controls: `import logging`, `from logging import getLogger`, `xml.etree`,
  `subprocess` (the P26 toast), `importlib.metadata` (owner.py reads the RECORD files with it), `faulthandler` (it
  runs no string and opens nothing), `traceback` (the `trace` ban must not catch a longer name) and `re.compile`.
- Scope is unchanged: `NETWORK_MODULES` binds core/compliance only (`test_imports_stay_on_the_allowlist`);
  `DYNAMIC_*` binds core/compliance and core/odds (`test_no_forbidden_module_import`). Checked in-process on
  2026-10-24 with exactly the code below: the six core/compliance files give no hit, and neither does Task 2's
  rules.py; core/odds holds no .py file yet.
- R7 is a test refactor: the new registration test passes before and after the list changes. Its own positive
  controls (a list without `compliance`, a text with no list) prove the parser. It needs `import re`, so the import
  goes in Step 1.
- Every Edit below is an exact old/new pair quoted from the tree at `5816d3c` (equal to `995534b` outside docs/) with
  its anchor. Before each Edit, re-read the file; if the old text is not found exactly once, apply the drift rule of
  Global Constraints. This plan runs first, so outside docs/ no earlier plan has changed this file (Step 1a checks it).

- [ ] **Step 1: Check the base, create the branch, then write the failing tests**

  **1a. The base (R13, R2-11).** From the repo root in Git Bash:

```bash
git branch --show-current
git status --short
git diff --stat 995534b HEAD -- . ':!docs'
```

  Expected: `main`, then nothing, then nothing. Since `995534b` only docs commits have landed on main: the E1 spec
  (`5816d3c`) and the docs commits of this plan, the odds plan and the E1 plan. If the first command prints another
  branch, run `git switch main` and repeat. The one `git status --short` line allowed is
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` (the executor's untracked ledger, if
  already started). If either of the other two commands prints anything else, stop and report to the controller:
  every line number and count in this plan rests on that tree. Then:

```bash
git switch -c compliance-followup
git ls-files --eol tests/compliance_guards.py
```

  Expected: `Switched to a new branch 'compliance-followup'`, then a line starting `i/lf    w/lf    attr/-text`. If
  `git switch -c` reports that `compliance-followup` already exists, stop and report; never `git switch -C`, and never
  delete the branch.

  **1b. The tests.** Six Edit-tool replacements in `tests/compliance_guards.py` (LF, kept). They add the positive
  and negative controls, the new test, the R7 helper and `import re`. The lists themselves change in Step 3.

  Edit 1. Anchor: the module's import block (guards:12-18). Old text:

```python
import io
import os
import sys
```

  New text:

```python
import io
import os
import re
import sys
```

  Edit 2. Anchor: test_no_forbidden_module_import, its docstring (guards:273-276). Only the docstring's last two lines
  change ("or bare compile()"). Old text:

```python
def test_no_forbidden_module_import():
    """core.engine.orders in every form (T-RO-01 misses `from core.engine import orders`), the forward simulator,
    the refusal legs and the protected context modules, at module or function level; and no star or dynamic import,
    which would hide one from this scan and load code the D14 closure never signed (P6)."""
```

  New text:

```python
def test_no_forbidden_module_import():
    """core.engine.orders in every form (T-RO-01 misses `from core.engine import orders`), the forward simulator,
    the refusal legs and the protected context modules, at module or function level; and no star or dynamic import
    or bare compile(), which would hide one from this scan and load code the D14 closure never signed (P6)."""
```

  Edit 3. Anchor: test_no_forbidden_module_import, the explicit dynamic positives, the module loop and the negative
  control (guards:284-297). The explicit list gains the motivating positives of every new entry (`import pstats`,
  `from pstats import Stats`, `import tracemalloc` and `from tracemalloc import Snapshot` among them, R2-10; the old
  `import importlib.util` and `from importlib import util` stay). The module loop is unchanged and covers every tuple
  entry in three import forms. A second negative control follows the first: traceback, faulthandler, logging and
  `re.compile` are not banned, and pstats and tracemalloc are not in it. Old text:

```python
    for src in ("from core.engine import *\n", "from core.compliance.model import *\n",
                "import importlib\nm = importlib.import_module('numpy')\n", "m = __import__('numpy')\n",
                "from importlib import import_module as im\n", "import importlib.util\n",
                "from importlib import util\n", "import runpy\n", "import pkgutil\n", "exec(src)\n", "eval(src)\n",
                "spec.loader.exec_module(m)\n", "import pydoc\n", "from pydoc import locate\n",
                "from timeit import timeit\n", "import timeit\n", "import code\n", "from code import interact\n",
                "import cProfile\n", "from cProfile import run\n"):
        assert _dynamic_hits(X, src), src
    for module in DYNAMIC_MODULES:                      # every banned module, in each import form
        for src in (f"import {module}\n", f"import {module}.x\n", f"from {module} import x\n"):
            assert _dynamic_hits(X, src), src
    assert not _dynamic_hits(X, "import importlib.metadata\nfrom importlib import metadata\n"
                                "v = importlib.metadata.distribution('PyYAML')\nimport json\nimport codecs\n"
                                "import profile_notes\nfrom core.compliance import code_files\n")
```

  New text:

```python
    for src in ("from core.engine import *\n", "from core.compliance.model import *\n",
                "import importlib\nm = importlib.import_module('numpy')\n", "m = __import__('numpy')\n",
                "from importlib import import_module as im\n", "import importlib.util\n",
                "from importlib import util\n", "import runpy\n", "import pkgutil\n", "exec(src)\n", "eval(src)\n",
                "spec.loader.exec_module(m)\n", "import pydoc\n", "from pydoc import locate\n",
                "from timeit import timeit\n", "import timeit\n", "import code\n", "from code import interact\n",
                "import cProfile\n", "from cProfile import run\n", "import importlib\n",
                "import importlib.resources\n", "from importlib import resources\n", "import profile\n",
                "import pdb\n", "from bdb import Bdb\n", "import trace\n", "import doctest\n", "import unittest.mock\n",
                "from unittest import mock\n", "from logging import config\n", "import logging.config\n",
                "from logging.config import dictConfig\n", "import pickle\n", "import _pickle\n", "import shelve\n",
                "import marshal\n", "import site\n", "import ensurepip\n", "import venv\n", "import tkinter\n",
                "from tkinter import Tcl\n", "import _tkinter\n", "import turtle\n", "import turtledemo\n",
                "import idlelib.run\n", 'x = compile(s, "x", "exec")\n', "import pstats\n",
                "from pstats import Stats\n", "import tracemalloc\n", "from tracemalloc import Snapshot\n"):
        assert _dynamic_hits(X, src), src
    for module in DYNAMIC_MODULES:                      # every banned module, in each import form
        for src in (f"import {module}\n", f"import {module}.x\n", f"from {module} import x\n"):
            assert _dynamic_hits(X, src), src
    assert not _dynamic_hits(X, "import importlib.metadata\nfrom importlib import metadata\n"
                                "v = importlib.metadata.distribution('PyYAML')\nimport json\nimport codecs\n"
                                "import profile_notes\nfrom core.compliance import code_files\n")
    assert not _dynamic_hits(X, "from importlib.metadata import distribution, PackageNotFoundError\nimport traceback\n"
                                "import faulthandler\nimport logging\nfrom logging import getLogger\n"
                                "_P = re.compile(r'x')\n")    # not banned (R1); pstats and tracemalloc are (R2-10)
```

  Edit 4. Anchor: the def line and docstring of test_imports_stay_on_the_allowlist (guards:305-309); the new test goes
  right above it. Old text:

```python
def test_imports_stay_on_the_allowlist():
    """stdlib, yaml, cryptography (inside a function only), core.isolation and core.compliance.* (contract
    section 0), so the D14 signed closure stays core/__init__.py, core/isolation.py and core/compliance (P6). The
    stdlib modules in NETWORK_MODULES are not allowed even though they are stdlib: core/compliance never needs the
    network (the alert email is sent by the scheduled Claude task, the toast is a subprocess)."""
```

  New text:

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


def test_imports_stay_on_the_allowlist():
    """stdlib, yaml, cryptography (inside a function only), core.isolation and core.compliance.* (contract
    section 0), so the D14 signed closure stays core/__init__.py, core/isolation.py and core/compliance (P6). The
    stdlib modules in NETWORK_MODULES are not allowed even though they are stdlib: core/compliance never needs the
    network (the alert email is sent by the scheduled Claude task, the toast is a subprocess)."""
```

  Edit 5. Anchor: test_imports_stay_on_the_allowlist, the "modules a plain socket/urllib list misses" loop and the
  sub-module negative control (guards:323-333). The list gains the xml.dom, antigravity, ctypes, _ctypes, _ssl and
  _overlapped positives (the three old xml.dom cases stay), and `from xml.dom import minidom` leaves the negative
  control. Old text:

```python
    # the modules a plain socket/urllib list misses: each can open a connection or fetch a URL on its own
    for src in ("import multiprocessing.connection\n", "from multiprocessing import connection\n",
                "import logging.handlers\n", "from logging import handlers\n",
                "from logging.handlers import HTTPHandler\n", "import _socket\n", "import socketserver\n",
                "import selectors\n", "from wsgiref import simple_server\n", "import xml.sax\n",
                "from xml import sax\n", "from xml.dom import pulldom\n", "from xml.dom import expatbuilder\n",
                "import xml.dom.expatbuilder\n"):
        assert _allowlist_hits(X, src), src
    # a banned SUB-module does not ban its parent package or its harmless siblings
    assert not _allowlist_hits(X, "import logging\nfrom logging import getLogger\nimport xml.etree.ElementTree\n"
                                  "from xml.etree import ElementTree\nfrom xml.dom import minidom\n")
```

  New text:

```python
    # the modules a plain socket/urllib list misses: each can open a connection or fetch a URL on its own
    for src in ("import multiprocessing.connection\n", "from multiprocessing import connection\n",
                "import logging.handlers\n", "from logging import handlers\n",
                "from logging.handlers import HTTPHandler\n", "import _socket\n", "import socketserver\n",
                "import selectors\n", "from wsgiref import simple_server\n", "import xml.sax\n",
                "from xml import sax\n", "from xml.dom import pulldom\n", "from xml.dom import expatbuilder\n",
                "import xml.dom.expatbuilder\n", "import xml.dom\n", "from xml.dom import minidom\n",
                "import xml.dom.minidom\n", "import xml.dom.xmlbuilder\n", "from xml import dom\n",
                "from xml.dom.minidom import parseString\n", "import antigravity\n", "import ctypes\n",
                "from ctypes import wintypes\n", "import _ctypes\n", "import _ssl\n", "import _overlapped\n"):
        assert _allowlist_hits(X, src), src
    # a banned SUB-module does not ban its parent package or its harmless siblings
    assert not _allowlist_hits(X, "import logging\nfrom logging import getLogger\nimport xml.etree.ElementTree\n"
                                  "from xml.etree import ElementTree\n")
```

  Edit 6. Anchor: test_suite_is_registered_in_run_all_and_readme, the whole function (guards:483-489). Old text:

```python
def test_suite_is_registered_in_run_all_and_readme():
    """`tests/run_all.py --suite compliance` selects this suite, and both hand-written suite lists name it."""
    from tests import run_all
    names = [n for n, _f in run_all.select(run_all.tests(), suite="compliance")]
    assert any(n.startswith("compliance/compliance_guards/") for n in names), names
    assert "paper, grokteam or compliance" in (ROOT / "tests" / "run_all.py").read_text(encoding="utf-8")
    assert "paper, grokteam or compliance" in (ROOT / "README.md").read_text(encoding="utf-8")
```

  New text (`read_text` uses universal newlines, so the CRLF files split cleanly; tests/run_all.py:113 and
  README.md:816 hold the only "one suite: " lines today):

```python
def _suite_names(text: str) -> list[str]:
    """The names of the first hand-written "one suite: a, b or c" list in `text` ([] when there is none)."""
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

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/; echo "exit $?"
```

  Expected: three tracebacks, and these three FAIL lines among 13 PASS lines (the runner sorts by test name):

```
FAIL compliance_guards/test_bare_compile_and_importlib_submodules_are_dynamic AssertionError: x = compile(s, "x", "exec")
FAIL compliance_guards/test_imports_stay_on_the_allowlist AssertionError: import xml.dom
FAIL compliance_guards/test_no_forbidden_module_import AssertionError: import importlib
```

  then `13/16 passed, 3 failed, 0 not run` and `exit 1`. Each first failing case is a route the lists miss today:
  the bare compile, the whole xml.dom package and the bare importlib. The PASS line of
  `test_suite_is_registered_in_run_all_and_readme` shows the R7 refactor is green already. Any other FAIL means an
  Edit of Step 1 went wrong: fix the Edit, never the expectation.

- [ ] **Step 3: Implement**

  Four Edit-tool replacements in `tests/compliance_guards.py` (LF, kept). Line numbers below are those of the tree
  before Step 1; after Edit 1 they are one higher, and each Edit below shifts the ones after it, so find each Edit by
  its anchor.

  Edit 7. Anchor: the constant NETWORK_MODULES (guards:39-41). The two `xml.dom.*` entries become one `xml.dom` (in
  place), and five entries are appended: 22 entries become 26. The comment above the constant stays. Old text:

```python
NETWORK_MODULES = ("urllib", "http", "socket", "_socket", "socketserver", "selectors", "ssl", "smtplib", "ftplib",
                   "imaplib", "poplib", "nntplib", "telnetlib", "xmlrpc", "asyncio", "webbrowser", "multiprocessing",
                   "wsgiref", "xml.sax", "xml.dom.pulldom", "xml.dom.expatbuilder", "logging.handlers")
```

  New text:

```python
NETWORK_MODULES = ("urllib", "http", "socket", "_socket", "socketserver", "selectors", "ssl", "smtplib", "ftplib",
                   "imaplib", "poplib", "nntplib", "telnetlib", "xmlrpc", "asyncio", "webbrowser", "multiprocessing",
                   "wsgiref", "xml.sax", "xml.dom", "logging.handlers", "antigravity", "ctypes", "_ctypes", "_ssl",
                   "_overlapped")
```

  Edit 8. Anchor: the comment block "# Star and dynamic imports hide" through the end of DYNAMIC_MODULES, between
  FORBIDDEN_MODULES and "# base name -> attributes that read the clock" (guards:45-51). `importlib` replaces
  `importlib.util` and `importlib.machinery` (first), the seven old entries follow, then the 19 of F1 and `pstats`,
  `tracemalloc` (R2-10): 9 entries become 29. `DYNAMIC_NAMES` is unchanged. Old text:

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
# name importlib, so any other attribute of it (importlib.util, importlib._bootstrap) is a hit too; its
# EntryPoint.load imports by string through an attribute, which this scan does not see. faulthandler stays allowed
# (R1): it runs no string and opens nothing. A denylist, not a proof: codeop and dis (they compile a string, which
# types.FunctionType runs), _frozen_importlib, _frozen_importlib_external and _imp (importlib's bootstrap under other
# names) and _interpreters (run_string) are not on it and are left to review. core/ probes for cryptography with a
# lazy `import` inside try/except ImportError; importlib.util.find_spec is for tests only.
DYNAMIC_NAMES = frozenset({"__import__", "import_module", "exec_module", "load_module", "exec", "eval"})
DYNAMIC_BARE = frozenset({"compile"})               # an ast.Name only: re.compile is an attribute
DYNAMIC_MODULES = ("importlib", "runpy", "pkgutil", "zipimport", "pydoc", "timeit", "code", "cProfile", "profile",
                   "pdb", "bdb", "trace", "doctest", "unittest", "logging.config", "pickle", "_pickle", "shelve",
                   "marshal", "site", "ensurepip", "venv", "tkinter", "_tkinter", "turtle", "turtledemo", "idlelib",
                   "pstats", "tracemalloc")
DYNAMIC_EXEMPT = "importlib.metadata"               # and everything below it (R9)
```

  Edit 9. Anchor: the checker _dynamic_hits, the whole function (guards:146-157). Old text:

```python
def _dynamic_hits(rel: str, src: str) -> list[str]:
    tree, hits = ast.parse(src), []
    for node, module, names, _f in _imports(rel, tree):
        targets = [module] + [f"{module}.{n}" for n in names]
        if ("*" in names or DYNAMIC_NAMES.intersection(names)
                or any(t == m or t.startswith(m + ".") for t in targets for m in DYNAMIC_MODULES)):
            hits.append(f"{rel}:{node.lineno}: star or dynamic import from {module}")
    for node, _f in _walk(tree):
        name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
        if name in DYNAMIC_NAMES:
            hits.append(f"{rel}:{node.lineno}: {name}")
    return hits
```

  New text (one new helper above the checker):

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

  Edit 10. Anchor: test_no_http_verb_calls, its def line and docstring (guards:248-262; the body below it stays). The
  docstring names the new network bans, drops the minidom and ctypes routes from "not covered" and adds sqlite3's
  load_extension there. Old text:

```python
def test_no_http_verb_calls():
    """core/compliance never calls .post/.put/.delete/.patch/.request on anything (contract section 0), a dict-like
    `.put` included, nor urlopen, urlretrieve or create_connection (bare or as an attribute). This is the second
    line. The first is test_imports_stay_on_the_allowlist, which bans every import form of the stdlib modules that
    open a connection or fetch a URL (NETWORK_MODULES: urllib, http, socket, ssl, the mail, ftp and telnet clients,
    xmlrpc, asyncio, selectors, socketserver, wsgiref, multiprocessing, webbrowser, logging.handlers, xml.sax, which
    opens a URL given as a system id, and two xml.dom modules that are not fetchers themselves: pulldom, built on
    xml.sax, and expatbuilder, which imports xml.dom.xmlbuilder). Together they catch a stdlib network call written
    in the ordinary ways; they do not prove that core/compliance cannot reach the network. Not covered: a
    `subprocess` call (the P26 alert toast is one; os.system, os.popen and os.startfile launch processes the same
    way), `ctypes`, and reaching a network API through an allowed module, by attribute or by `getattr(module,
    "name")`. That needs no banned import and no banned name: the allowed xml.dom.minidom hands out an
    xml.dom.xmlbuilder DOMBuilder whose parseURI opens a URL with urllib.request
    (`minidom.getDOMImplementation().createDOMBuilder(1, None).parseURI(url)`), and an allowed module that imports
    a banned one carries it as an attribute. All three are left to review."""
```

  New text:

```python
def test_no_http_verb_calls():
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
    _winapi launch processes the same way), sqlite3's Connection.load_extension, which loads any DLL as ctypes does,
    and reaching a network API through an allowed module, by attribute or by `getattr(module, "name")`: an allowed
    module that imports a banned one carries it as an attribute (mailbox carries socket, concurrent.futures.process
    carries multiprocessing.connection). All three are left to review."""
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/; echo "exit $?"
```

  Expected: 16 PASS lines, then `16/16 passed, 0 failed, 0 not run`, then `exit 0`. A
  FAIL of `test_no_forbidden_module_import` or `test_imports_stay_on_the_allowlist` on a shipped file names the file
  and line: report it to the controller, never shorten a list to make it pass.

  Overlap check, then the compliance suite (it rewrites the tracked `qa/acceptance_results.json`, which is restored
  at once). Every `--suite` run first imports all ten suites (tests/run_all.py:41-50), against the Bash tool's 120 s
  default, so give this line `timeout: 300000`; never start a second run meanwhile:

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected last lines: `316/318 passed, 0 failed, 2 not run; ` followed by the path of `qa\acceptance_results.json`,
  then `exit 0`. The two NOT_RUN rows are the REFDATA symlink tests
  (`compliance_isolation/test_symlinks_are_refused`, `compliance_tables/test_calendar_sha256_refuses_a_file_symlink`);
  with Windows Developer Mode on they pass instead and the line reads `318/318 passed, 0 failed, 0 not run`. Then:

```bash
git status --short
```

  Expected: exactly ` M tests/compliance_guards.py`, plus, if the executor keeps its ledger in the repo and has not
  committed it, `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add tests/compliance_guards.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (the file is LF): `tests/compliance_guards.py | 127` followed by its bar,
  and `1 file changed, 98 insertions(+), 29 deletions(-)`. If they differ, an edit converted line endings: run
  `git restore --staged tests/compliance_guards.py`, `git checkout -- tests/compliance_guards.py` and redo the
  Edits with the Edit tool. Then:

```bash
git commit -m "test(guards): ban xml.dom, string-exec modules and bare compile; read the suite lists" -m "Task 1 (R1 with R2-10, R7, R9): NETWORK_MODULES 22 -> 26, DYNAMIC_MODULES 9 -> 29 with DYNAMIC_BARE and DYNAMIC_EXEMPT, and the registration test reads the one-suite lists." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: Loader: D15 and D16 by content, D15 rows blocking, review_by/max_leverage/{cap} bounds, exact row pins

**Files:**
- Modify: `core/compliance/rules.py` (LF; a D14 closure file; anchors: the constants `_BLOCKING` and
  `_MAX_REVIEW_DAYS` above `_match`; in `_row`: the axis-check block `if treatment not in _BLOCKING:`, the grey
  `{cap}` check with the `leverage =` line, the block from `policy_ref = item.get("policy_ref")` through the
  gated-row raise, and the `review_by` checks after `latest = max(r.date for r in reviews)`)
- Modify: `tests/compliance_tables.py` (LF; anchors: `test_d16_rows_need_requires_live`, `test_warning_slots`,
  `test_max_leverage`; new tests right above `test_requires_items_in_vocabulary` and right above
  `test_shipped_okx_warning_has_only_the_cap_slot`)
- Modify: `tests/compliance_cli.py` (LF; anchor: `test_render_has_no_rule_free_text`)
- Test: `tests/compliance_tables.py` (59 tests become 65), `tests/compliance_cli.py` (35 tests, one rewritten line)
- Not touched: `core/compliance/kr_rules.yaml`. It stays byte-identical and VALID, sha256
  `127a3c913fdc7c0e07a19f8daae2c0548c782770c74b5b6a6578ec9551bd3b79` (59,408 bytes) until Task 3.

**Interfaces:**
- Consumes:
  - `core.compliance.rules`, unchanged: `Invalid(reason)` (`.reason == str(exc)`), `ETP_ASSETS`
    (`{"krx_etp", "us_etp"}`), `_BLOCKING`, the result of `_match` (a read-only `Mapping[str, frozenset]`; on a
    non-blocking row the axis check guarantees `action`, `financing` and a `class` or `asset` key, and `any` is
    already refused),
    `_warning`, `_positive`, `parse_rules(raw: bytes) -> RulesTable`, and the `Row` fields `.match`,
    `.requires_owner`, `.requires_live`, `.treatment`, `.max_leverage`, `.warning`, `.review_by`, `.policy_ref`.
  - `tests/compliance_tables.py`, unchanged helpers: `_row(**over)` (a valid allow row `T-ALLOW` on upbit coin
    buy/sell for cash, covering all 38 matrix rows; review 2026-10-23, review_by 2026-11-23), `_grey(**over)` (a
    valid grey row `T-GREY` shaped like KR-OKX-SPOT), `_parse(*rows)`, `_bad(*rows_and_has) -> str` (asserts Invalid
    with every needle and returns the reason), `_refused(call, *has)`, `date`; in the compliance plan's Task 5 block
    (the `_t5_` helpers) `_t5_raw(kind)`, `_t5_shipped()` and `_t5_rules`.
  - Task 1: the widened guard lists. The new rules.py text was scanned with Task 1's checkers on 2026-10-24: no
    raw-text, def, verb, dynamic, allowlist, clock, seal or `__main__` hit.
- Produces:
  - In `core/compliance/rules.py`: the private constants `_MAX_LEVERAGE = 10.0`, `_D15_FINANCING`, `_D15_ACTIONS`,
    `_D16_ACTIONS`, `_D16_CLASSES`, `_D16_ASSETS`, and the seven reason strings of the table below. The signatures of
    `_row` and `parse_rules` are unchanged; every existing reason keeps its exact text (R10).
  - In `tests/compliance_tables.py`: the tests `test_d15_rows_never_let_credit_margin_lending_or_borrowing_through`,
    `test_a_d15_row_is_blocking`, `test_d16_by_content_needs_requires_live`,
    `test_review_by_is_not_before_the_latest_review`, `test_only_a_grey_row_states_a_cap` and
    `test_shipped_rows_that_can_let_through_are_pinned_exactly`; the constant `_T5_PINNED`
    (`{row id: (match as {key: set}, requires_owner, requires_live, treatment)}`, 15 rows in table order); and the
    private helper `_t5_pin_misses(table) -> list[str]`, which this task defines (it is not in Appendix A).
  - For later work: Task 3 edits only the KR-KIS-KRX-DERIV reason, so `_T5_PINNED` holds unchanged after it. Any
    later change to a shipped allow, gated or grey row (the odds plan included) updates its `_T5_PINNED` entry in
    the same commit.

**Plan decisions used:** R2 (F2), R10 (the check order and the three deliberate rewrites), R13 with the drift rule
(R2-13) of Global Constraints.

Notes (read before Step 1):
- The rules (R2). For a row whose treatment is allow, gated or grey:
  - D15 by content: it never matches financing `credit` or `margin`, nor action `lend` or `borrow`; margin is D15
    by the compliance plan's Task 7 ruling (ledger:131). `sell_short` is D16 (spec:70), never D15.
  - D16 by content: if its action includes `sell_short`, or its class includes `etp_leveraged`,
    `etp_single_stock`, `krx_derivative` or `elw`, or its asset includes `krx_derivative` or `elw`, it needs a
    non-empty `requires.live`, whatever its policy_ref says. A row with no `class` key that names the asset
    `krx_etp` or `us_etp` matches every class those assets derive to (gate.py:385-401 checks only the keys a row
    has; rules.py:213-224), so it counts as matching `etp_leveraged` and `etp_single_stock`. The D16 label rule
    (rules.py:491-492) stays.
  - The other three rules apply to every row:
    - D15 by label: a row whose policy_ref names D15 is `hard_block` or `out_of_scope`.
    - Bounds: `review_by` is not before the row's latest review date, and `max_leverage <= 10` (10 itself is legal).
    - Only a grey row's warning may hold the `{cap}` slot (ledger:146), so the cap text an owner acks always
      belongs to a grey row's signed cap.
- Check order inside `_row` (R10), so every existing reason keeps its text:
  1. `_match` (it refuses `any`), then the axis check, then D15 content (new, in the same block);
  2. the conduct-ETP check, `requires`, then the ack and grey checks;
  3. the warning slots, with `{cap}` only in grey (new);
  4. `max_leverage`, with the bound (new);
  5. the policy_ref format, the D16 label, then the D15 label (new);
  6. D16 content (new), then the gated-row requirement and the rest of `_row`;
  7. the `review_by` lower bound (new), before the 31-day check.
  So an existing fixture that broke two rules still fails on its old reason: the `any` test's credit row fails on
  `any`, and the "D15, D16" row of `test_d16_rows_need_requires_live` fails on the D16 label.
- Three existing assertions flip on purpose and are rewritten in Step 1 (R10):
  - tables:295, a gated etp_leveraged row citing D160 with no live evidence. It is VALID today and Invalid by D16
    content, so it becomes a `_bad` with that reason, plus an etp_1x line that keeps the "D160 is not D16" intent.
  - tables:316, `{cap}` in an allow row's warning, leaves the allow-row loop.
  - cli:576-577. `test_render_has_no_rule_free_text` appends " {cap}" to every shipped warning, so R2 would make its
    mutated table Invalid at the gated per_session row KR-KIS-US-OPTION ("rules: row KR-KIS-US-OPTION: warning: only
    a grey row states a {cap}", dry run 2026-10-24). The rewrite appends it to the grey row only. The table stays
    VALID and the test still proves that no rule free text renders. It passes before and after R2.
- The shipped table. Read-only probe of 2026-10-24: 47 rows. The 15 allow, gated and grey rows are all
  `financing: [cash]` and none has lend or borrow. The five rows matching sell_short or a D16 class all carry live
  evidence, and no row names an ETP asset without a class axis. The two D15 rows (KR-KIS-CREDIT,
  KR-DOMESTIC-LENDING) are out_of_scope. No review_by is before its review, max_leverage peaks at 3.0, and only
  KR-OKX-SPOT has `{cap}`. So the table parses VALID under R2 with no byte changed.
- Approved tables. R2 tightens the loader that re-parses every stored approval at every `load_context`
  (owner.py:960-961 calls `rules.approved_state`; rules.py:766-767 turns an `Invalid` into an invalid state). An
  approved table that broke R2 would therefore turn INVALID: new exposure blocked, and exits through the snapshot
  invalid too. No owner signature or table approval exists today (no `owner_pubkey.pem`; real-home `--check` exits
  3), so nothing changes in force now. Owner act 3 approves the table as Task 3 leaves it.
- The code hash. `core/compliance/rules.py` is in the D14 closure, so its hash moves. No `code_approved` exists yet,
  so there is nothing to re-sign. After owner act 2, every later change to it needs a fresh `code_approved`.
- Reason strings (exact; the row id follows `rules: row `):

| Rule | Reason |
|---|---|
| D15 content, financing | `rules: row <id>: match.financing: an allow, gated or grey row never matches ['credit'] (D15: no credit buying)` (the sorted hit list) |
| D15 content, action | `rules: row <id>: match.action: an allow, gated or grey row never matches ['borrow', 'lend'] (D15: no coin lending or borrowing)` |
| D15 label | `rules: row <id>: treatment: a D15 row is hard_block or out_of_scope (D15 only keeps credit and lending out)` |
| D16 content | `rules: row <id>: requires.live: a row matching ['etp_leveraged'] needs live broker evidence (D16)` (an ETP asset with no class axis lists `['etp_leveraged', 'etp_single_stock']`) |
| review_by | `rules: row <id>: review_by: 2026-10-22 is before the review of 2026-10-23` |
| max_leverage | `rules: row <id>: max_leverage: at most 10, got 10.5` |
| {cap} | `rules: row <id>: warning: only a grey row states a {cap}` |

- Fixture rule of the new tests: a row other than `_row()` itself gets its own id and `matrix_rows: []` and is
  passed after `_row()`, which covers the 38 matrix rows. A single `_row(**over)` override keeps id T-ALLOW and the
  full matrix.
- Every Edit below is an exact old/new pair quoted from the tree at `5816d3c` (equal to `995534b` outside docs/) with
  its anchor; the line numbers are those of that tree and only help find the anchor. Task 1 did not touch these
  three files. Before each Edit, re-read the file; if the old text is not found exactly once, apply the drift rule
  of Global Constraints.

- [ ] **Step 1: Write the failing tests**

  Six Edit-tool replacements: five in `tests/compliance_tables.py` and one in `tests/compliance_cli.py` (both LF,
  kept).

  Edit 1, `tests/compliance_tables.py`. Anchor: test_d16_rows_need_requires_live, the `"policy_ref": "D160"` line
  (tables:295). The first deliberate flip (R10): a gated etp_leveraged row citing D160 with no live evidence is D16 by
  content. Old text:

```python
    _parse(_row(), _row(**{**lev, "policy_ref": "D160"}, requires={"owner": ["kofia_leveraged_1h"]}))   # not D16
```

  New text:

```python
    _bad(_row(), _row(**{**lev, "policy_ref": "D160"}, requires={"owner": ["kofia_leveraged_1h"]}),
         "row T-LEV: requires.live: a row matching ['etp_leveraged']")         # not D16 by label, D16 by content
    one_x = {**lev["match"], "class": ["etp_1x"]}                               # D160 is not D16, nor is etp_1x
    _parse(_row(), _row(**{**lev, "policy_ref": "D160", "match": one_x}, requires={"owner": ["kofia_leveraged_1h"]}))
```

  Edit 2, `tests/compliance_tables.py`. Anchor: the def line and first statement of test_requires_items_in_vocabulary
  (tables:302-303); the five new tests go right above it. Old text:

```python
def test_requires_items_in_vocabulary():
    _bad(_row(requires={"owner": ["age_19"]}), "row T-ALLOW: requires.owner", "'age_19' is outside")
```

  New text (the five loader tests, then the unchanged head of `test_requires_items_in_vocabulary`):

```python
def test_d15_rows_never_let_credit_margin_lending_or_borrowing_through():
    """D15 by content (R2, ledger:243): an allow, gated or grey row never matches financing credit or margin, nor
    action lend or borrow, whatever its policy_ref says. Blocking rows may (KR-KIS-CREDIT, KR-DOMESTIC-LENDING), and
    sell_short is D16 (spec:70), never D15."""
    coin = {"venue": ["upbit"], "class": ["coin"], "action": ["buy", "sell"], "financing": ["cash"]}
    for make in (lambda m: _row(match=m),
                 lambda m: _row(match=m, treatment="gated", requires={"owner": ["age_of_majority"]})):
        for financing in (["cash", "margin"], ["credit"], ["margin"]):
            _bad(make({**coin, "financing": financing}),
                 "row T-ALLOW: match.financing: an allow, gated or grey row never matches")
        for action in (["buy", "lend"], ["borrow"]):
            _bad(make({**coin, "action": action}),
                 "row T-ALLOW: match.action: an allow, gated or grey row never matches")
    assert _bad(_row(match={**coin, "financing": ["credit"]})) == (
        "rules: row T-ALLOW: match.financing: an allow, gated or grey row never matches ['credit'] (D15: no credit "
        "buying)")
    assert _bad(_row(match={**coin, "action": ["buy", "lend", "borrow"]})) == (
        "rules: row T-ALLOW: match.action: an allow, gated or grey row never matches ['borrow', 'lend'] (D15: no coin "
        "lending or borrowing)")
    okx = {"venue": ["okx"], "class": ["coin"], "action": ["buy", "sell"], "financing": ["cash", "margin"]}
    _bad(_row(), _grey(match=okx), "row T-GREY: match.financing", "['margin'] (D15")
    _bad(_row(), _grey(match={**okx, "financing": ["cash"], "action": ["buy", "borrow"]}), "row T-GREY: match.action",
         "['borrow'] (D15")
    wide = {**coin, "action": ["buy", "lend", "borrow"], "financing": ["credit", "margin"]}
    for treatment in ("hard_block", "out_of_scope"):
        row = _parse(_row(), _row(id="T-D15", treatment=treatment, match=wide, matrix_rows=[])).rows[1]
        assert row.match["financing"] == {"credit", "margin"} and row.match["action"] == {"buy", "lend", "borrow"}
    short = {"venue": ["kis"], "asset": ["krx_share"], "action": ["buy", "sell_short"], "financing": ["cash"]}
    row = _parse(_row(), _row(id="T-SHORT", treatment="gated", match=short, requires={"live": ["broker_approval"]},
                              matrix_rows=[])).rows[1]
    assert row.match["action"] == {"buy", "sell_short"} and row.requires_live == ("broker_approval",)


def test_a_d15_row_is_blocking():
    """D15 by label (R2): a row citing D15 is hard_block or out_of_scope, as a row citing D16 needs requires.live."""
    d15 = {"id": "T-D15", "policy_ref": "D15", "basis": ["policy"], "matrix_rows": []}
    for row in (_row(**d15), _row(**d15, treatment="gated", requires={"owner": ["age_of_majority"]}), _grey(**d15)):
        _bad(_row(), row, "row T-D15: treatment: a D15 row is hard_block or out_of_scope")
    assert _bad(_row(), _row(**d15)) == ("rules: row T-D15: treatment: a D15 row is hard_block or out_of_scope (D15 "
                                         "only keeps credit and lending out)")
    for ref in ("D15", "D10, D15"):
        for treatment in ("hard_block", "out_of_scope"):
            row = _parse(_row(), _row(**{**d15, "policy_ref": ref}, treatment=treatment)).rows[1]
            assert (row.policy_ref, row.treatment) == (ref, treatment)


def test_d16_by_content_needs_requires_live():
    """D16 by content (R2): a row that can let an intent through and matches sell_short, a leveraged or single-stock
    ETP, a KRX derivative or an ELW needs requires.live, whatever its policy_ref says. A row with no class axis that
    names an ETP asset matches every class that asset derives to, the leveraged and single-stock ones included."""
    kis = {"venue": ["kis"], "action": ["buy"], "financing": ["cash"]}
    matches = ({**kis, "asset": ["krx_share"], "action": ["sell_short"]}, {**kis, "class": ["etp_1x", "etp_leveraged"]},
               {**kis, "class": ["etp_single_stock"]}, {**kis, "class": ["krx_derivative"]},
               {**kis, "asset": ["krx_derivative"]}, {**kis, "class": ["elw"]}, {**kis, "asset": ["elw"]},
               {**kis, "asset": ["krx_etp"]}, {**kis, "asset": ["us_etp"]})
    live = {"owner": ["age_of_majority"], "live": ["broker_approval"]}
    for m in matches:
        d16 = {"id": "T-D16", "match": m, "matrix_rows": []}
        _bad(_row(), _row(**d16, treatment="gated", requires={"owner": ["age_of_majority"]}),
             "row T-D16: requires.live: a row matching")
        _bad(_row(), _row(**d16), "row T-D16: requires.live: a row matching")
        gated = _parse(_row(), _row(**d16, treatment="gated", requires=live)).rows[1]
        assert gated.requires_live == ("broker_approval",), m
        assert _parse(_row(), _row(**d16, treatment="out_of_scope")).rows[1].treatment == "out_of_scope"
    assert _bad(_row(), _row(id="T-D16", match=matches[1], matrix_rows=[])) == (
        "rules: row T-D16: requires.live: a row matching ['etp_leveraged'] needs live broker evidence (D16)")
    assert _bad(_row(), _row(id="T-D16", match=matches[7], matrix_rows=[])) == (
        "rules: row T-D16: requires.live: a row matching ['etp_leveraged', 'etp_single_stock'] needs live broker "
        "evidence (D16)")
    one_x = _row(id="T-1X", match={**kis, "asset": ["krx_etp"], "class": ["etp_1x"]}, matrix_rows=[])
    assert _parse(_row(), one_x).rows[1].match["class"] == {"etp_1x"}          # a class axis decides
    sell_short = {"venue": ["okx"], "class": ["coin"], "action": ["buy", "sell_short"], "financing": ["cash"]}
    _bad(_row(), _grey(match=sell_short), "row T-GREY: requires.live: a row matching ['sell_short']")


def test_review_by_is_not_before_the_latest_review():
    """R2 (ledger:103): review_by is never before the row's latest review, the earliest legal value being the review
    day itself; an earlier date is a typo, never a schedule."""
    assert _parse(_row(review_by="2026-10-23")).rows[0].review_by == date(2026, 10, 23)
    assert _bad(_row(review_by="2026-10-22")) == (
        "rules: row T-ALLOW: review_by: 2026-10-22 is before the review of 2026-10-23")
    two = [{"date": "2026-09-01", "by": "a", "checked": "x"}, {"date": "2026-10-23", "by": "b", "checked": "y"}]
    _bad(_row(reviews=two, review_by="2026-10-01"),
         "row T-ALLOW: review_by: 2026-10-01 is before the review of 2026-10-23")      # the latest review counts


def test_only_a_grey_row_states_a_cap():
    """R2 (ledger:146): only a grey row's warning has the {cap} slot, so the cap text an owner acks in a per_session
    warning is always a grey row's signed cap."""
    _bad(_row(warning="OKX is capped at {cap} of your equity."), "row T-ALLOW: warning: only a grey row states a {cap}")
    gated = _row(id="T-GATED", treatment="gated", ack="per_session", requires={"owner": ["age_of_majority"]},
                 warning="at most {cap} of your equity", matrix_rows=[])
    _bad(_row(), gated, "row T-GATED: warning: only a grey row states a {cap}")
    _bad(_row(), _row(id="T-OOS", treatment="out_of_scope", warning="{cap}", matrix_rows=[]),
         "row T-OOS: warning: only a grey row states a {cap}")
    assert _parse(_row(warning="literal {{cap}} braces")).rows[0].warning == "literal {{cap}} braces"
    assert "{cap}" in _parse(_row(), _grey()).rows[1].warning


def test_requires_items_in_vocabulary():
    _bad(_row(requires={"owner": ["age_19"]}), "row T-ALLOW: requires.owner", "'age_19' is outside")
```

  Edit 3, `tests/compliance_tables.py`. Anchor: test_warning_slots, its first loop (tables:316-317). The second
  deliberate flip (R10): `{cap}` leaves the allow-row loop. The `_bad` cases below the loop stay: `{cap!r}` and
  `{cap:>5}` still fail first in `_warning`. Old text:

```python
    for text in ("OKX is capped at {cap} of your equity.", "no slot at all", "literal {{cap}} braces", ""):
        assert _parse(_row(warning=text)).rows[0].warning == text
```

  New text:

```python
    for text in ("no slot at all", "literal {{cap}} braces", ""):    # {cap}: test_only_a_grey_row_states_a_cap
        assert _parse(_row(warning=text)).rows[0].warning == text
```

  Edit 4, `tests/compliance_tables.py`. Anchor: test_max_leverage, its last line (tables:413). `test_max_leverage`
  gains the bound cases. `1e6` is dumped as `1000000.0`, a decimal float the strict loader reads. Old text:

```python
    _bad(_row(max_leverage=10 ** 400), "rules: line ", "has more than 18 digits")      # Invalid, never OverflowError
```

  New text:

```python
    _bad(_row(max_leverage=10 ** 400), "rules: line ", "has more than 18 digits")      # Invalid, never OverflowError
    assert _parse(_row(max_leverage=10)).rows[0].max_leverage == 10.0                 # R2: 10 itself is legal
    for bad in (10.5, 11, 1e6):
        _bad(_row(max_leverage=bad), "row T-ALLOW: max_leverage: at most 10")
    assert _bad(_row(max_leverage=10.5)) == "rules: row T-ALLOW: max_leverage: at most 10, got 10.5"
```

  Edit 5, `tests/compliance_tables.py`. Anchor: the def line and first statement of
  test_shipped_okx_warning_has_only_the_cap_slot (tables:984-985); the pins and their test go right above it.
  `_T5_PINNED` was generated from the shipped table on 2026-10-24 and equals it, in table order. Its tuples keep the
  YAML order of `requires`. Of the two widenings ledger:113 names, the loader now refuses one (sell_short on
  KR-KIS-US-SHARE, D16 by content), and the pin catches the other (p2p_buy on KR-DOMESTIC-SPOT, which stays VALID
  under R2). Four pin controls follow: p2p_buy added (KR-DOMESTIC-SPOT), an owner requirement dropped
  (KR-KIS-US-OPTION), a row leaving the set (KR-KIS-ETP-1X turned hard_block) and a blocking row entering it
  (KR-KIS-CRYPTO-SPOT-ETP turned allow for cash, VALID under today's loader and under R2), so neither half of the
  symmetric difference in `_t5_pin_misses` goes unchecked. Each replaced byte string is checked to occur exactly once
  in the shipped bytes. Old text:

```python
def test_shipped_okx_warning_has_only_the_cap_slot():
    table, _, _ = _t5_shipped()
```

  New text:

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


def _t5_pin_misses(table) -> list[str]:
    """The ids where the allow, gated and grey rows of `table` and _T5_PINNED differ: an id in only one of the two,
    or a row whose (match, requires_owner, requires_live, treatment) is not its pin."""
    rows = {r.id: r for r in table.rows if r.treatment in ("allow", "gated", "grey")}
    misses = sorted(set(rows) ^ set(_T5_PINNED))
    for rid in sorted(set(rows) & set(_T5_PINNED)):
        r = rows[rid]
        if ({k: set(v) for k, v in r.match.items()}, r.requires_owner, r.requires_live, r.treatment) != _T5_PINNED[rid]:
            misses.append(rid)
    return misses


def test_shipped_rows_that_can_let_through_are_pinned_exactly():
    """The 15 shipped rows that can let an intent through, pinned exactly (R2). ledger:113: widening an allow row
    (sell_short on KR-KIS-US-SHARE, p2p_buy on KR-DOMESTIC-SPOT) passed every test of the compliance plan's Task 5.
    Now the loader refuses the first (D16 by content) and the pin catches the second, a dropped owner requirement,
    and a row leaving or entering the set; a deliberate change to one of these rows edits its pin in the same commit."""
    raw = _t5_raw("rules")
    spot = b"match: {venue: [upbit, bithumb, coinone, korbit], class: [coin], action: [buy, sell], financing: [cash]}"
    us = b"match: {venue: [kis], asset: [us_share], action: [buy, sell], financing: [cash]}"
    option = b"requires: {owner: [us_option_course_1h, us_option_mock_3h, broker_eligibility], live: []}"
    one_x = b"match: {venue: [kis], class: [etp_1x], action: [buy, sell], financing: [cash]}\n    treatment: allow\n"
    etp = b"match: {venue: [kis], class: [etp_crypto_spot], action: [buy]}\n    treatment: hard_block\n"
    opened = etp.replace(b"[buy]}", b"[buy], financing: [cash]}").replace(b"hard_block", b"allow")
    assert all(raw.count(old) == 1 for old in (spot, us, option, one_x, etp))
    for old, new, missed in ((spot, spot.replace(b"[buy, sell]", b"[buy, sell, p2p_buy]"), ["KR-DOMESTIC-SPOT"]),
                             (option, option.replace(b", broker_eligibility", b""), ["KR-KIS-US-OPTION"]),
                             (one_x, one_x.replace(b"allow", b"hard_block"), ["KR-KIS-ETP-1X"]),   # a row leaves
                             (etp, opened, ["KR-KIS-CRYPTO-SPOT-ETP"])):           # a blocking row turns allow
        assert _t5_pin_misses(_t5_rules.parse_rules(raw.replace(old, new))) == missed, missed
    _refused(lambda: _t5_rules.parse_rules(raw.replace(us, us.replace(b"[buy, sell]", b"[buy, sell, sell_short]"))),
             "row KR-KIS-US-SHARE: requires.live: a row matching ['sell_short']")
    table, _, _ = _t5_shipped()
    assert len(_T5_PINNED) == 15 and _t5_pin_misses(table) == [], _t5_pin_misses(table)


def test_shipped_okx_warning_has_only_the_cap_slot():
    table, _, _ = _t5_shipped()
```

  Edit 6, `tests/compliance_cli.py`. Anchor: test_render_has_no_rule_free_text, the loop that rewrites every shipped
  row (cli:574-577). The third deliberate rewrite (R10). It passes under today's loader and keeps passing under R2.
  Old text:

```python
        if row.get("warning"):
            row["warning"] = UNIQUE + " {cap}"
```

  New text:

```python
        if row.get("warning"):
            row["warning"] = UNIQUE + (" {cap}" if row["treatment"] == "grey" else "")   # R2: {cap} is grey-only
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected: eight tracebacks and these eight FAIL lines (the runner sorts by test name). Each is a case today's
  loader accepts:

```
FAIL compliance_tables/test_a_d15_row_is_blocking AssertionError: accepted; expected Invalid containing ('row T-D15: treatment: a D15 row is hard_block or out_of_scope',)
FAIL compliance_tables/test_d15_rows_never_let_credit_margin_lending_or_borrowing_through AssertionError: accepted; expected Invalid containing ('row T-ALLOW: match.financing: an allow, gated or grey row never matches',)
FAIL compliance_tables/test_d16_by_content_needs_requires_live AssertionError: accepted; expected Invalid containing ('row T-D16: requires.live: a row matching',)
FAIL compliance_tables/test_d16_rows_need_requires_live AssertionError: accepted; expected Invalid containing ("row T-LEV: requires.live: a row matching ['etp_leveraged']",)
FAIL compliance_tables/test_max_leverage AssertionError: accepted; expected Invalid containing ('row T-ALLOW: max_leverage: at most 10',)
FAIL compliance_tables/test_only_a_grey_row_states_a_cap AssertionError: accepted; expected Invalid containing ('row T-ALLOW: warning: only a grey row states a {cap}',)
FAIL compliance_tables/test_review_by_is_not_before_the_latest_review AssertionError: accepted; expected Invalid containing ()
FAIL compliance_tables/test_shipped_rows_that_can_let_through_are_pinned_exactly AssertionError: accepted; expected Invalid containing ("row KR-KIS-US-SHARE: requires.live: a row matching ['sell_short']",)
```

  The rest are 56 PASS lines (`test_warning_slots` among them) and
  `NOT_RUN compliance_tables/test_calendar_sha256_refuses_a_file_symlink` with its REFDATA reason. Then
  `56/65 passed, 8 failed, 1 not run` and exit code 1. With Windows Developer Mode on, the symlink test passes and
  the line reads `57/65 passed, 8 failed, 0 not run`. Before the pin test reaches its sell_short control, its four
  pin controls already pass, so the pins match the shipped table.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected, ending: `35/35 passed, 0 failed, 0 not run` (exit code 0). The rewritten free-text test passes under
  today's loader.

- [ ] **Step 3: Implement**

  Five Edit-tool replacements in `core/compliance/rules.py` (LF, kept). Together they add 31 lines, none longer
  than 120 characters, and no banned word (the raw-text guard scans comments too).

  Edit 7. Anchor: the constants _BLOCKING and _MAX_REVIEW_DAYS above _match (rules.py:405-406). Old text:

```python
_BLOCKING = frozenset({"hard_block", "out_of_scope"})      # conduct rows are hard_block, so `any` is legal there
_MAX_REVIEW_DAYS = 31
```

  New text:

```python
_BLOCKING = frozenset({"hard_block", "out_of_scope"})      # conduct rows are hard_block, so `any` is legal there
_MAX_REVIEW_DAYS = 31
_MAX_LEVERAGE = 10.0                                       # R2: a typo cannot sign 1e6x
_D15_FINANCING = frozenset({"credit", "margin"})           # D15: no credit buying (margin included, ledger:131)
_D15_ACTIONS = frozenset({"lend", "borrow"})               # D15: no coin lending or borrowing
_D16_ACTIONS = frozenset({"sell_short"})                   # D16 by content (spec:70), whatever policy_ref says
_D16_CLASSES = frozenset({"etp_leveraged", "etp_single_stock", "krx_derivative", "elw"})
_D16_ASSETS = frozenset({"krx_derivative", "elw"})
```

  Edit 8. Anchor: _row, the axis check block `if treatment not in _BLOCKING:` (rules.py:454-459). D15 content goes
  right after the `missing` raise, inside the block that guarantees `match["financing"]` and `match["action"]` exist.
  Old text:

```python
    if treatment not in _BLOCKING:              # a missing key matches everything, so a row that can let an intent
        missing = sorted({"action", "financing"} - set(match)) + ([] if {"class", "asset"} & set(match)
                                                                  else ["class or asset"])   # through names each axis
        if missing:
            raise Invalid(f"{where}: match: an allow, gated or grey row names action, financing and a class or an "
                          f"asset; missing {missing}")
```

  New text:

```python
    if treatment not in _BLOCKING:              # a missing key matches everything, so a row that can let an intent
        missing = sorted({"action", "financing"} - set(match)) + ([] if {"class", "asset"} & set(match)
                                                                  else ["class or asset"])   # through names each axis
        if missing:
            raise Invalid(f"{where}: match: an allow, gated or grey row names action, financing and a class or an "
                          f"asset; missing {missing}")
        credit = sorted(match["financing"] & _D15_FINANCING)
        if credit:
            raise Invalid(f"{where}: match.financing: an allow, gated or grey row never matches {credit} (D15: no "
                          "credit buying)")
        lending = sorted(match["action"] & _D15_ACTIONS)
        if lending:
            raise Invalid(f"{where}: match.action: an allow, gated or grey row never matches {lending} (D15: no coin "
                          "lending or borrowing)")
```

  Edit 9. Anchor: _row, the grey {cap} check and the `leverage =` line (rules.py:484-486). The slot set is computed
  once, `{cap}` outside grey is refused, and the `max_leverage` bound follows `_positive` (which already refuses 0,
  negatives, bools, NaN and inf). The bound's reason prints the value with `!r`, as `_positive`'s own reason does, so
  10.0000001 reads `got 10.0000001` (`:g` would print `got 10`), 11 reads `got 11.0` and 10.5 `got 10.5` (Appendix
  A section 4.2 check 3, amended 2026-10-25). Old text:

```python
    if treatment == "grey" and "cap" not in {slot for _, slot, _, _ in string.Formatter().parse(warning)}:
        raise Invalid(f"{where}: warning: a grey row states its {{cap}}")
    leverage = 1.0 if item.get("max_leverage") is None else _positive(item["max_leverage"], f"{where}: max_leverage")
```

  New text:

```python
    slots = {slot for _, slot, _, _ in string.Formatter().parse(warning)}
    if treatment == "grey" and "cap" not in slots:
        raise Invalid(f"{where}: warning: a grey row states its {{cap}}")
    if treatment != "grey" and "cap" in slots:                               # the cap is a grey row's (ledger:146)
        raise Invalid(f"{where}: warning: only a grey row states a {{cap}}")
    leverage = 1.0 if item.get("max_leverage") is None else _positive(item["max_leverage"], f"{where}: max_leverage")
    if leverage > _MAX_LEVERAGE:
        raise Invalid(f"{where}: max_leverage: at most {_MAX_LEVERAGE:g}, got {leverage!r}")
```

  Edit 10. Anchor: _row, from `policy_ref = item.get("policy_ref")` through the gated-row raise (rules.py:487-494).
  The D15 label check follows the D16 label check inside the `policy_ref` block; D16 content follows the block and
  precedes the gated-row requirement. Old text:

```python
    policy_ref = item.get("policy_ref")
    if policy_ref is not None:
        if not isinstance(policy_ref, str) or not _POLICY.fullmatch(policy_ref):
            raise Invalid(f"{where}: policy_ref: expected 'D<n>' or 'D<n>, D<n>, ...', got {policy_ref!r}")
        if "D16" in policy_ref.split(", ") and not live:
            raise Invalid(f"{where}: requires.live: a D16 row needs live broker evidence (requires.live)")
    if treatment == "gated" and not (owner or live):                         # else it would act as an allow row
        raise Invalid(f"{where}: requires: a gated row requires owner or live evidence")
```

  New text:

```python
    policy_ref = item.get("policy_ref")
    if policy_ref is not None:
        if not isinstance(policy_ref, str) or not _POLICY.fullmatch(policy_ref):
            raise Invalid(f"{where}: policy_ref: expected 'D<n>' or 'D<n>, D<n>, ...', got {policy_ref!r}")
        if "D16" in policy_ref.split(", ") and not live:
            raise Invalid(f"{where}: requires.live: a D16 row needs live broker evidence (requires.live)")
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
    if treatment == "gated" and not (owner or live):                         # else it would act as an allow row
        raise Invalid(f"{where}: requires: a gated row requires owner or live evidence")
```

  Edit 11. Anchor: _row, `latest = max(r.date for r in reviews)` and the 31-day check (rules.py:523-525). Old text:

```python
    latest = max(r.date for r in reviews)
    if (review_by - latest).days > _MAX_REVIEW_DAYS:                         # P15: monthly
        raise Invalid(f"{where}: review_by: {review_by} is more than 31 days after the review of {latest}")
```

  New text:

```python
    latest = max(r.date for r in reviews)
    if review_by < latest:                                                   # a typo, never a schedule (ledger:103)
        raise Invalid(f"{where}: review_by: {review_by} is before the review of {latest}")
    if (review_by - latest).days > _MAX_REVIEW_DAYS:                         # P15: monthly
        raise Invalid(f"{where}: review_by: {review_by} is more than 31 days after the review of {latest}")
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before each test command below (the
  module runs, the static-guard `-c` run and the suite run). All run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected, ending: `64/65 passed, 0 failed, 1 not run` (exit code 0; the NOT_RUN is the REFDATA symlink test, and
  with Developer Mode on the line is `65/65 passed, 0 failed, 0 not run`).

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected, ending: `35/35 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then the gate and the store, which parse the shipped table through the fixtures and signed homes:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_gate/
```

  Expected, ending: `49/49 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected, ending: `29/29 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then the static guards, whose scans include the new rules.py text (comments too):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Expected, ending: `16/16 passed, 0 failed, 0 not run` (exit code 0). A failure names the offending file and text:
  fix `rules.py`, never the guard.

  Overlap check, then the repo-wide read-only guards over `core/` (T-RO-01, test_08, test_09). This calls the three
  test functions directly, does not start `tests/run_all.py`, and writes nothing:

```bash
.venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as ro; from tests.acceptance import test_08_no_broker_order_path as t8, test_09_no_account_credentials_requested as t9; ro(); t8(); t9(); print('guards ok')"
```

  Expected: `guards ok` (exit code 0).

  The shipped table is unchanged (a hash, not a test command, so no overlap check):

```bash
.venv/Scripts/python.exe -c "import hashlib; print(hashlib.sha256(open('core/compliance/kr_rules.yaml', 'rb').read()).hexdigest())"
```

  Expected: `127a3c913fdc7c0e07a19f8daae2c0548c782770c74b5b6a6578ec9551bd3b79`.

  Overlap check, then the compliance suite (it rewrites the tracked `qa/acceptance_results.json`, which is restored
  at once). Every `--suite` run first imports all ten suites (run_all.py:41-50), and the compliance tests alone took
  64 s in the 2026-10-24 record, against the Bash tool's 120 s default: give this line `timeout: 300000`; never
  start a second run meanwhile.

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected last lines: `322/324 passed, 0 failed, 2 not run; ` followed by the path of `qa\acceptance_results.json`,
  then `exit 0` (with Developer Mode on: `324/324 passed, 0 failed, 0 not run`). Then:

```bash
git status --short
```

  Expected: exactly ` M core/compliance/rules.py`, ` M tests/compliance_cli.py` and ` M tests/compliance_tables.py`,
  plus, if the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add core/compliance/rules.py tests/compliance_tables.py tests/compliance_cli.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (all three files are LF): `core/compliance/rules.py | 33`,
  `tests/compliance_cli.py | 2`, `tests/compliance_tables.py | 181`, each followed by its bar, and
  `3 files changed, 212 insertions(+), 4 deletions(-)`. If they differ, an edit converted line endings: run
  `git restore --staged <file>` then `git checkout -- <file>`, redo every Edit of that file with the Edit tool
  (Edits 1-5 for `tests/compliance_tables.py`, Edit 6 for `tests/compliance_cli.py`, Edits 7-11 for
  `core/compliance/rules.py`), then repeat Step 4 and this step. Then:

```bash
git commit -m "fix(compliance): loader refuses D15/D16 content, bounds review_by, max_leverage and {cap}; pin rows" -m "Task 2 (R2, R10): five checks in rules._row, three deliberate test rewrites (tables:295, :316, cli:576-577), five loader tests and the 15 exact row pins; kr_rules.yaml unchanged and VALID." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: The KR-KIS-KRX-DERIV reason names broker approval (`core/compliance/kr_rules.yaml`)

**Files:**
- Modify: `core/compliance/kr_rules.yaml` (anchor: the `reason:` key of the row `- id: KR-KIS-KRX-DERIV`, line 204
  today, the row starts at :199; LF; a shipped table, outside the D14 code closure)
- Modify: `tests/compliance_tables.py` (anchor: `test_shipped_d16_rows_need_live_evidence`, :951-965 today, in the
  `_t5_` block (the compliance plan's Task 5); LF)
- Test: `tests/compliance_tables.py`

**Interfaces:**
- Consumes: the existing helpers of the `_t5_` block (the compliance plan's Task 5) of `tests/compliance_tables.py`:
  `_t5_shipped()` (:854, returns `(table, imap, venues)` parsed from the shipped files) and `_t5_row(table, row_id)`
  (:861); `rules.Row.reason` (`str`), `rules.Row.requires_live` (`tuple[str, ...]`). Task 2's loader (R2) must accept
  the edited table; it does (dry run below).
- Produces: no new name. The shipped rules table's bytes change on one line: 59,408 -> 59,425 bytes, sha256
  `127a3c913fdc7c0e07a19f8daae2c0548c782770c74b5b6a6578ec9551bd3b79` ->
  `74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd`.

**Plan decisions used:** R3; R13 and the drift rule (Global Constraints).

What this task does and why:
- The ledger (ledger:118, "KR-KIS-KRX-DERIV reason text does not mention broker approval (cosmetic)") recorded that
  the row's `requires.live` (:203) lists `broker_approval` while its reason (:204) names only deposits, courses and
  mock trading. R3 makes the reason start "KOSPI200 futures and options need broker approval, a broker deposit of
  KRW 10M (stage 1) ...". Only this line changes; the row's match, requires, treatment, sources and dates stay.
- The table sha changes. No approval exists yet (`core/compliance/owner_pubkey.pem` is absent, owner act 1 is not
  done), so nothing is re-signed; the owner's first rules approval (owner act 3) is of these edited bytes. Nothing in
  the repo pins the old sha or the old reason text (2026-10-24, `git grep -I -n <term> -- . ':!docs'`: `127a3c91`
  finds nothing; `KOSPI200 futures and options need` and `broker deposit of KRW` each find only kr_rules.yaml:204
  itself; the bare term `KOSPI200 futures` also hits about 27 files of prose, research notes and data, none of which
  quotes the reason); every test that reads the shipped table hashes it at run time.
- Not touched here (each is out of scope, Appendix A section 11): the 2027-01-01 `affected_by` item (ledger:114), any
  deposit network (the OKX USDT/USDC networks stay an owner act, ledger:112, :120), and the compliance plan's embedded
  copy of the old row (docs/superpowers/plans/2026-10-23-compliance-gate.md:5109, a historical record).
- Dry run (2026-10-24, a sandbox copy of the table and of the test file): exactly line 204 differs; the edited table
  parses VALID with 47 rows under today's `rules.parse_rules` and under the Task 2 (R2) sandbox copy of rules.py; the
  new assertion fails on today's table with the old reason as its message and passes on the edited one; the file
  stays LF, UTF-8 and under 256 KB (`test_shipped_files_are_utf8_lf_and_small`, tables:897-902).
- Drift: Task 2 edits `tests/compliance_tables.py` before this task (new tests after :300 and the `_T5_PINNED` block
  after :981), so the line numbers of `test_shipped_d16_rows_need_live_evidence` move down; find it by name. Neither
  Task 2 nor any earlier plan changes kr_rules.yaml. Re-read each file before its Edit; if the quoted old text differs
  only because an earlier plan changed it, apply the same change to the current text and write one ledger line.

- [ ] **Step 1: Write the failing test**

  In `tests/compliance_tables.py`, function `test_shipped_d16_rows_need_live_evidence`, add one assertion right after
  the `krx_deriv` lines (Edit tool; the file is LF).

  Old text (exact, two lines):

```python
    krx_deriv = _t5_row(table, "KR-KIS-KRX-DERIV")          # D16: broker eligibility is live evidence, not an owner snapshot
    assert "broker_approval" in krx_deriv.requires_live and "broker_eligibility" not in krx_deriv.requires_owner
```

  New text:

```python
    krx_deriv = _t5_row(table, "KR-KIS-KRX-DERIV")          # D16: broker eligibility is live evidence, not an owner snapshot
    assert "broker_approval" in krx_deriv.requires_live and "broker_eligibility" not in krx_deriv.requires_owner
    assert "broker approval" in krx_deriv.reason, krx_deriv.reason   # the reason names what requires.live asks (ledger:118)
```

  (The new line is Appendix A section 5's line exactly, 124 characters; the first old line is 125 characters today and
  stays as it is. The assertion checks presence only; the Step 3 size and sha check pins the exact new reason.)

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected: a traceback, the line

```
FAIL compliance_tables/test_shipped_d16_rows_need_live_evidence AssertionError: KOSPI200 futures and options need a broker deposit of KRW 10M (stage 1) or KRW 20M (stage 2: option writing, VKOSPI futures), at least 1h of course and 3h of mock trading; this row asks for the stage-2 deposit for every intent; refused until live broker evidence exists (D16)
```

  and, ending, `63/65 passed, 1 failed, 1 not run` (exit code 1). The not-run test is the REFDATA symlink test; with
  Windows Developer Mode on it passes and the line reads `64/65 passed, 1 failed, 0 not run`. Any other failure means
  Task 2 did not land as written: stop and rule.

- [ ] **Step 3: Implement**

  In `core/compliance/kr_rules.yaml`, row `- id: KR-KIS-KRX-DERIV`, replace its `reason:` line (Edit tool; the file
  is LF; the line is one physical line, do not wrap it).

  Old text (exact, one line):

```
    reason: "KOSPI200 futures and options need a broker deposit of KRW 10M (stage 1) or KRW 20M (stage 2: option writing, VKOSPI futures), at least 1h of course and 3h of mock trading; this row asks for the stage-2 deposit for every intent; refused until live broker evidence exists (D16)"
```

  New text (exact, one line):

```
    reason: "KOSPI200 futures and options need broker approval, a broker deposit of KRW 10M (stage 1) or KRW 20M (stage 2: option writing, VKOSPI futures), at least 1h of course and 3h of mock trading; this row asks for the stage-2 deposit for every intent; refused until live broker evidence exists (D16)"
```

  Then check the bytes (read-only, from the repo root in Git Bash; no overlap check needed, it runs no test):

```bash
git diff --stat -- core/compliance/kr_rules.yaml
git diff --stat --ignore-cr-at-eol -- core/compliance/kr_rules.yaml
git ls-files --eol core/compliance/kr_rules.yaml
.venv/Scripts/python.exe -I -c "import hashlib, pathlib; b = pathlib.Path('core/compliance/kr_rules.yaml').read_bytes(); print(len(b), hashlib.sha256(b).hexdigest(), b.count(b'\r'))"
```

  Expected: each of the two `git diff --stat` commands prints exactly (git's leading space included)

```
 core/compliance/kr_rules.yaml | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

  then `i/lf    w/lf    attr/-text            	core/compliance/kr_rules.yaml`; and
  `59425 74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd 0`. Another size or sha means the line
  was mistyped (or an earlier plan changed the table): fix the line, or stop and rule under the drift rule.

- [ ] **Step 4: Run to verify it passes**

  Overlap check (PowerShell tool, as in Step 2; it must print nothing), then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected, ending: `64/65 passed, 0 failed, 1 not run` (exit code 0; `65/65 passed, 0 failed, 0 not run` with
  Developer Mode on).

  Overlap check again, then the compliance suite (it parses the shipped table in compliance_gate, compliance_store,
  compliance_cli and compliance_signer too), then restore the results file (give this line `timeout: 300000`; never
  start a second run meanwhile):

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected, ending:

```
322/324 passed, 0 failed, 2 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json
exit 0
```

  (324 rows, as after Task 2; the two not-run rows are the REFDATA symlink tests). Then
  `git status --short` lists only ` M core/compliance/kr_rules.yaml` and ` M tests/compliance_tables.py`, plus, if
  the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add core/compliance/kr_rules.yaml tests/compliance_tables.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are LF), each exactly (git's column padding included):

```
 core/compliance/kr_rules.yaml | 2 +-
 tests/compliance_tables.py    | 1 +
 2 files changed, 2 insertions(+), 1 deletion(-)
```

  Then:

```bash
git commit -m "fix(tables): KR-KIS-KRX-DERIV reason names broker approval" -m "R3 (ledger:118): the reason now names the broker approval its requires.live lists; table sha 74894f05..., no approval exists yet, owner act 3 approves these bytes." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: Closure scan: a guard counts only while its name is unbound and unmutated (`owner.py`, `sign.py`)

**Files:**
- Modify: `core/compliance/owner.py` (anchors: `_skipped` (:708-724 today; `_guards` is inserted right before it,
  after `_typing_flag`), `_import_nodes` (:727-736), the `_import_nodes(...)` loop line of `_repo_imports` (:755); LF;
  a D14 closure file)
- Modify: `tools/signer/sign.py` (anchors: the same three, `_skipped` :631-647, `_import_nodes` :650-659,
  `_repo_imports` :678; LF; off the closure, the owner keeps a copy)
- Modify: `tests/compliance_store.py` (anchors: the module's import block, `import contextlib` :7; and
  `test_code_files_counts_lazy_imports_and_skips_main_and_type_checking`, :153-194; LF)
- Modify: `tests/compliance_signer.py` (anchors: `test_code_files_match_owner`, :630-677, and the start of
  `test_store_layout_matches_owner_store_put`, :680, before which the new test goes; LF)
- Test: `tests/compliance_store.py`, `tests/compliance_signer.py`

**Interfaces:**
- Consumes (unchanged, identical in owner.py and sign.py): `_binds(tree: ast.AST, name: str) -> int` (owner.py:683,
  sign.py:606: bindings of `name` at any depth, imports, assignments, defs, parameters, except-as, match captures);
  `_typing_flag(tree: ast.AST) -> bool` (owner.py:699, sign.py:622); `_module_file(root, dotted)`;
  `code_files(repo_root) -> list[tuple[str, str]]` and `code_hash(repo_root) -> str` (their bodies do not change).
  Test fixtures: `F.temp_home()` (tests/compliance_store.py, from tests.compliance_fixtures); in
  tests/compliance_signer.py the module-level `signer` (loaded by path as `tradegen_signer_under_test`), `owner`,
  `ROOT` and `_home()` (:120, the test's temp TRADEGEN_HOME).
- Produces, character-identical in `core/compliance/owner.py` and `tools/signer/sign.py`:
  - `_guards(tree: ast.AST) -> tuple[bool, bool, bool]`: (bare `TYPE_CHECKING` trusted, `typing.TYPE_CHECKING`
    trusted, `__name__ == "__main__"` trusted) for one module;
  - `_skipped(node: ast.AST, guards: tuple[bool, bool, bool]) -> bool` (was `bare_flag: bool`);
  - `_import_nodes(node: ast.AST, guards: tuple[bool, bool, bool])` (was `bare_flag: bool`);
  - `_repo_imports(root, path)` keeps its signature and passes `_guards(tree)`.
  - New test `test_closure_scan_helpers_are_identical_in_owner_and_signer` in tests/compliance_signer.py. Task 5 edits
    sign.py after this task (other functions only); nothing here is renamed.

**Plan decisions used:** R4 (with its stated limit, accepted by R2-12); R13 and the drift rule (Global Constraints).

What this task does and why:
- Today `if typing.TYPE_CHECKING:` is skipped whatever `typing` is bound to (owner.py:718-719), and
  `if __name__ == "__main__":` is skipped even when the module rebinds `__name__` (owner.py:720-723). So
  `typing = SimpleNamespace(TYPE_CHECKING=True)` or `__name__ = "__main__"` hides an import that does run from the
  D14 closure (ledger:208), and so do `typing.TYPE_CHECKING = True`, `setattr(typing, ...)`,
  `globals()["__name__"] = ...`, `sys.modules["typing"] = ...` and `sys._getframe().f_globals["__name__"] = ...`,
  which change the names without binding them.
- After: `typing.TYPE_CHECKING` counts only when `typing` is bound exactly once in the module, by a plain
  `import typing`; the `__main__` test counts only when `__name__` is bound nowhere in the module; the bare
  `TYPE_CHECKING` keeps today's `_typing_flag` rule. A module that stores to an attribute `TYPE_CHECKING` or
  `__name__`, or uses any Name or attribute `setattr`, `delattr`, `globals`, `vars`, `locals`, `modules`, `__dict__`,
  `builtins`, `__builtins__`, `f_globals` or `f_locals`, trusts no guard at all, the bare one included. Every change
  only scans more. `f_globals` and `f_locals` (a frame's namespaces) are route names by a controller ruling at the
  plan's final review, so the frame route is closed too.
- The signer's copy (sign.py:597-718, "a copy of owner.code_files (P6)") gets the identical text, and a new test
  compares the source of the seven closure-scan helpers in the two files, so a hardening in one cannot be forgotten in
  the other; `test_code_files_match_owner` keeps comparing their outputs on the real and the synthetic tree.
- State after this task, checked in a sandbox on 2026-10-24 with exactly the text below: the real closure is unchanged
  (10 entries: `core/__init__.py`, `core/isolation.py`, `core/compliance/__init__.py`, `alerts.py`, `gate.py`,
  `model.py`, `owner.py`, `rules.py`, and the PyYAML and cryptography RECORD rows), and no closure file uses any of the
  route names, so `rules.py` and `model.py` keep their bare `TYPE_CHECKING` skip and `rules.py` and `alerts.py` their
  `__main__` skip. Of the twelve synthetic modules below, today's helpers hide all twelve targets and the new ones
  hide none; the eight route cases asserted directly on `_guards` each void all three guards. Re-checked on a scratch
  copy at the plan's final assembly with the two frame routes added: no closure file names `f_globals` or
  `f_locals`, the real closure files keep the guards named above, and the frame modules r.py and s.py hide their
  targets today and not after this task. For the odds plan: a core/odds module that uses any route name anywhere (a
  `vars()` call, a name `modules`, `.__dict__`) trusts no guard, so its `if TYPE_CHECKING:` and `__main__` imports count in the D14 closure (and `test_code_files_is_the_import_closure`
  turns red if one names a repo file outside its expected set: core/__init__.py, core/isolation.py,
  core/compliance/*.py, core/odds/*.py). The same holds for E1's execution/*.py once its Task 9 adds them to the
  closure: keep TYPE_CHECKING-only imports out of a closure module that uses a route name.
- Code hash: owner.py is a closure file, so the D14 code hash moves. No `code_approved` exists yet (owner act 2 is not
  done), so nothing is re-signed now. sign.py is off the closure, but the owner runs a copy of it: owner act 1 is not
  done, so the owner copies the merged file then; if a copy already exists, the owner reads the diff of
  `tools/signer/sign.py`, re-hashes it in Windows Terminal (PowerShell) with the certutil line of Task 8 Step 9,
  `certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256`, and re-records the hash on paper (Task 5
  changes sign.py again; one owner act after the merge covers both).
- Stated limit (spec rev 3.3; accepted as stated, round-2 ruling R2-12): the route list is a denylist. Another module
  changing `typing.TYPE_CHECKING` before this one is imported, or a name built at run time, is not seen; the owner's
  review of each hashed file's diff is the barrier there. The `_guards` docstring names the first of these (its text
  is fixed by Appendix A section 6.1).
  - The frame route is closed: by the controller's ruling at the final review, `f_globals` and `f_locals` are route
    names, so a module that touches a frame's namespaces (`sys._getframe().f_globals["__name__"] = "__main__"`,
    `sys._getframe().f_locals["TYPE_CHECKING"] = True`) trusts no guard (the synthetic modules r.py and s.py).
  - In-module routes the list still misses, each confirmed on a scratch copy (2026-10-24) to still hide an import that
    runs: an attribute fetched by string (`getattr(sys, "modules")["typing"] = ...`), a dunder call
    (`typing.__setattr__("TYPE_CHECKING", True)`, `object.__setattr__(typing, "TYPE_CHECKING", True)`) and a
    from-import alias of a route name (`from sys import modules as m`, `from builtins import setattr as s`,
    `from builtins import globals as g`). No Task 1 guard sees them either (sys and builtins are on no list). Each is
    plain to read in a hashed diff.
  - `getattr` cannot be listed: gate.py (:111-112, :127, :398, :623-625), model.py (:37, :198), rules.py (:813, :867),
    alerts.py (:223) and `owner._binds` itself (owner.py:694) call it, so listing it would void the guards of every
    closure file that calls it; `__setattr__` likewise (model.py:199). Today's closure would stay the same, because
    the guarded bodies import only closure files (model.py:17-18, rules.py:24-25) or nothing (rules.py:970,
    alerts.py:353), but Appendix A section 6.1 fixes the route list, so this task leaves those names and alias names
    out. `getattr(sys, "modules")["typing"]` stays a stated limit.
- Departures from Appendix A (the task wins): Appendix A section 6.4 lists only the twelve synthetic files for
  tests/compliance_store.py. This task also adds `import ast` there (Edit T0) and, after the expected set (Edit T3),
  one assert that `owner._guards` trusts all three guards of a plain module plus eight direct `owner._guards` route
  asserts (delattr, vars, locals, `__dict__`, builtins, `__builtins__`, a `__name__` attribute store, a `del` of
  `TYPE_CHECKING`), each voiding all three guards. owner.py and sign.py get exactly Appendix A sections 6.1-6.3.
- Drift: no earlier task of this plan touches these four files (Task 2 changes rules.py, not owner.py), so the quoted
  text is that of `5816d3c`. Re-read each file before its Edit; if the quoted old text differs only because an earlier
  plan changed it, apply the same change to the current text, keep the earlier behaviour and write one ledger line;
  if the change no longer makes sense, stop and rule. Edits O1-O3 are applied to owner.py and then, unchanged, to
  sign.py: the old texts are character-identical in the two files today.

- [ ] **Step 1: Write the failing tests**

  All Edits with the Edit tool; both files are LF.

  **Edit T0**, `tests/compliance_store.py`, the module's import block (`ast` is new there; the route asserts of
  Edit T3 parse source text). Old text (exact):

```python
import contextlib
import datetime as _dt
```

  New text:

```python
import ast
import contextlib
import datetime as _dt
```

  **Edit T1**, `tests/compliance_store.py`, `test_code_files_counts_lazy_imports_and_skips_main_and_type_checking`,
  the last docstring line. Old text (exact):

```python
    at import: an `!=` test, a bare TYPE_CHECKING that is a local (or rebound) name, and `not TYPE_CHECKING`."""
```

  New text:

```python
    at import: an `!=` test, a bare TYPE_CHECKING that is a local (or rebound) name, and `not TYPE_CHECKING`; and a
    guard whose name the module rebinds or never imports plainly (typing rebound, `import os as typing`, no `import
    typing`, `__name__` assigned or a parameter), or that the module can change without a binding (an attribute store,
    setattr, globals(), sys.modules, a frame's f_globals or f_locals), is scanned too (R4)."""
```

  **Edit T2**, same function, the `sources` dict: twelve synthetic modules after `f.py` (h.py to q.py, then the frame
  routes r.py and s.py) and their twelve empty targets after `core/rev_cli.py`. Old text (exact):

```python
        "core/compliance/f.py": "if \"__main__\" == __name__:\n    import core.rev_cli\n",
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
```

  New text:

```python
        "core/compliance/f.py": "if \"__main__\" == __name__:\n    import core.rev_cli\n",
        "core/compliance/h.py": ("import types\nimport typing\ntyping = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.rebound_typing\n"),
        "core/compliance/i.py": "__name__ = \"__main__\"\nif __name__ == \"__main__\":\n    import core.rebound_main\n",
        "core/compliance/j.py": "import os as typing\nif typing.TYPE_CHECKING:\n    import core.alias_typing\n",
        "core/compliance/k.py": "if typing.TYPE_CHECKING:\n    import core.unbound_typing\n",
        "core/compliance/l.py": ("def main(__name__=None):\n    return __name__\n"
                                 "if __name__ == \"__main__\":\n    import core.param_main\n"),
        "core/compliance/m.py": ("import typing\ntyping.TYPE_CHECKING = True\n"
                                 "if typing.TYPE_CHECKING:\n    import core.stored_typing\n"),
        "core/compliance/n.py": ("import typing\nsetattr(typing, \"TYPE_CHECKING\", True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.setattr_typing\n"),
        "core/compliance/o.py": ("globals()[\"__name__\"] = \"__main__\"\n"
                                 "if __name__ == \"__main__\":\n    import core.globals_main\n"),
        "core/compliance/p.py": ("import sys\nimport types\n"
                                 "sys.modules[\"typing\"] = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "import typing\nif typing.TYPE_CHECKING:\n    import core.modules_typing\n"),
        "core/compliance/q.py": ("import typing\ntyping.TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\n"
                                 "if TYPE_CHECKING:\n    import core.stored_bare\n"),
        "core/compliance/r.py": ("import sys\nsys._getframe().f_globals[\"__name__\"] = \"__main__\"\n"
                                 "if __name__ == \"__main__\":\n    import core.frame_main\n"),
        "core/compliance/s.py": ("import sys\nfrom typing import TYPE_CHECKING\n"
                                 "sys._getframe().f_locals[\"TYPE_CHECKING\"] = True\n"
                                 "if TYPE_CHECKING:\n    import core.frame_bare\n"),
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
        "core/rebound_typing.py": "", "core/rebound_main.py": "", "core/alias_typing.py": "",
        "core/unbound_typing.py": "", "core/param_main.py": "", "core/stored_typing.py": "",
        "core/setattr_typing.py": "", "core/globals_main.py": "", "core/modules_typing.py": "",
        "core/stored_bare.py": "", "core/frame_main.py": "", "core/frame_bare.py": "",
```

  **Edit T3**, same function, the expected set, then direct asserts on `owner._guards` for the routes the synthetic
  modules do not exercise (delattr, vars, locals, `__dict__`, builtins, `__builtins__`, an attribute store of
  `__name__`, a `del` of `TYPE_CHECKING`), so dropping one from `routes` turns this test red. Old text (exact):

```python
                    "core/compliance/f.py",
                    "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, sorted(repo)
```

  New text:

```python
                    "core/compliance/f.py",
                    "core/compliance/h.py", "core/compliance/i.py", "core/compliance/j.py", "core/compliance/k.py",
                    "core/compliance/l.py", "core/compliance/m.py", "core/compliance/n.py", "core/compliance/o.py",
                    "core/compliance/p.py", "core/compliance/q.py", "core/compliance/r.py", "core/compliance/s.py",
                    "core/rebound_typing.py", "core/rebound_main.py", "core/alias_typing.py",
                    "core/unbound_typing.py", "core/param_main.py", "core/stored_typing.py",
                    "core/setattr_typing.py", "core/globals_main.py", "core/modules_typing.py",
                    "core/stored_bare.py", "core/frame_main.py", "core/frame_bare.py",
                    "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, sorted(repo)
    trusted = "import typing\nfrom typing import TYPE_CHECKING\n"
    assert owner._guards(ast.parse(trusted)) == (True, True, True)
    for route in ("delattr(typing, 'x')", "vars(typing)", "locals()", "typing.__dict__", "import builtins\nbuiltins",
                  "__builtins__", "typing.__name__ = 'x'", "del typing.TYPE_CHECKING"):
        assert owner._guards(ast.parse(trusted + route + "\n")) == (False, False, False), route
```

  **Edit T4**, `tests/compliance_signer.py`, `test_code_files_match_owner`, the `sources` dict (its tree also holds
  `core/compliance/g.py`, which stays). Old text (exact):

```python
        "core/compliance/g.py": "def main():\n    from core.compliance import g\n    return g\n",   # rules.main's shape
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
```

  New text:

```python
        "core/compliance/g.py": "def main():\n    from core.compliance import g\n    return g\n",   # rules.main's shape
        "core/compliance/h.py": ("import types\nimport typing\ntyping = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.rebound_typing\n"),
        "core/compliance/i.py": "__name__ = \"__main__\"\nif __name__ == \"__main__\":\n    import core.rebound_main\n",
        "core/compliance/j.py": "import os as typing\nif typing.TYPE_CHECKING:\n    import core.alias_typing\n",
        "core/compliance/k.py": "if typing.TYPE_CHECKING:\n    import core.unbound_typing\n",
        "core/compliance/l.py": ("def main(__name__=None):\n    return __name__\n"
                                 "if __name__ == \"__main__\":\n    import core.param_main\n"),
        "core/compliance/m.py": ("import typing\ntyping.TYPE_CHECKING = True\n"
                                 "if typing.TYPE_CHECKING:\n    import core.stored_typing\n"),
        "core/compliance/n.py": ("import typing\nsetattr(typing, \"TYPE_CHECKING\", True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.setattr_typing\n"),
        "core/compliance/o.py": ("globals()[\"__name__\"] = \"__main__\"\n"
                                 "if __name__ == \"__main__\":\n    import core.globals_main\n"),
        "core/compliance/p.py": ("import sys\nimport types\n"
                                 "sys.modules[\"typing\"] = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "import typing\nif typing.TYPE_CHECKING:\n    import core.modules_typing\n"),
        "core/compliance/q.py": ("import typing\ntyping.TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\n"
                                 "if TYPE_CHECKING:\n    import core.stored_bare\n"),
        "core/compliance/r.py": ("import sys\nsys._getframe().f_globals[\"__name__\"] = \"__main__\"\n"
                                 "if __name__ == \"__main__\":\n    import core.frame_main\n"),
        "core/compliance/s.py": ("import sys\nfrom typing import TYPE_CHECKING\n"
                                 "sys._getframe().f_locals[\"TYPE_CHECKING\"] = True\n"
                                 "if TYPE_CHECKING:\n    import core.frame_bare\n"),
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
        "core/rebound_typing.py": "", "core/rebound_main.py": "", "core/alias_typing.py": "",
        "core/unbound_typing.py": "", "core/param_main.py": "", "core/stored_typing.py": "",
        "core/setattr_typing.py": "", "core/globals_main.py": "", "core/modules_typing.py": "",
        "core/stored_bare.py": "", "core/frame_main.py": "", "core/frame_bare.py": "",
```

  **Edit T5**, `tests/compliance_signer.py`, the end of `test_code_files_match_owner` (its expected set) and the
  new test between it and `test_store_layout_matches_owner_store_put`. Old text (exact):

```python
        "core/compliance/f.py", "core/compliance/g.py",
        "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, mine


def test_store_layout_matches_owner_store_put():
```

  New text:

```python
        "core/compliance/f.py", "core/compliance/g.py",
        "core/compliance/h.py", "core/compliance/i.py", "core/compliance/j.py", "core/compliance/k.py",
        "core/compliance/l.py", "core/compliance/m.py", "core/compliance/n.py", "core/compliance/o.py",
        "core/compliance/p.py", "core/compliance/q.py", "core/compliance/r.py", "core/compliance/s.py",
        "core/rebound_typing.py", "core/rebound_main.py", "core/alias_typing.py", "core/unbound_typing.py",
        "core/param_main.py", "core/stored_typing.py", "core/setattr_typing.py", "core/globals_main.py",
        "core/modules_typing.py", "core/stored_bare.py", "core/frame_main.py", "core/frame_bare.py",
        "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, mine


def test_closure_scan_helpers_are_identical_in_owner_and_signer():
    """R4: the signer's copy of the D14 closure scan is owner.py's, character for character, so a hardening in one
    file cannot be forgotten in the other (test_code_files_match_owner compares outputs on chosen trees only)."""
    import inspect
    for name in ("_binds", "_typing_flag", "_guards", "_skipped", "_import_nodes", "_module_file", "_repo_imports"):
        assert inspect.getsource(getattr(signer, name)) == inspect.getsource(getattr(owner, name)), name


def test_store_layout_matches_owner_store_put():
```

  (`code_files` and `code_hash` are not compared: the signer's copies differ on purpose, in their docstrings (its
  `code_hash` has none) and in calling its own `sha256_hex`/`canonical_json` and a function-level
  `from importlib import metadata`, since it may not import the repo. The other six helpers are character-identical
  today, checked 2026-10-24.)

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: a traceback, then the line
  `FAIL compliance_store/test_code_files_counts_lazy_imports_and_skips_main_and_type_checking AssertionError: [...]`,
  whose list (the closure today's helpers build) names `core/compliance/h.py` to `core/compliance/s.py` but none of
  the twelve targets `core/alias_typing.py`, `core/frame_bare.py`, `core/frame_main.py`, `core/globals_main.py`,
  `core/modules_typing.py`, `core/param_main.py`, `core/rebound_main.py`, `core/rebound_typing.py`,
  `core/setattr_typing.py`, `core/stored_bare.py`, `core/stored_typing.py`, `core/unbound_typing.py` (the
  expected-set assert fails before the `owner._guards` asserts run, so there is no AttributeError); and, ending,
  `28/29 passed, 1 failed, 0 not run` (exit code 1).

  Overlap check again, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected, two FAIL lines (each after its traceback):

```
FAIL compliance_signer/test_closure_scan_helpers_are_identical_in_owner_and_signer AttributeError: module 'tradegen_signer_under_test' has no attribute '_guards'
```

  and `FAIL compliance_signer/test_code_files_match_owner AssertionError: [('config.py', ...), ...]` (the signer's
  closure of the synthetic tree, with the same twelve targets missing; the signer and owner.py still agree with each
  other, so it is the expected-set assertion that fails); ending `36/38 passed, 2 failed, 0 not run` (exit code 1).
  Any other failure: stop and rule.

- [ ] **Step 3: Implement**

  Apply Edits O1, O2 and O3 to `core/compliance/owner.py`, then the same three Edits, unchanged, to
  `tools/signer/sign.py` (Edit tool; both LF). Each old text occurs exactly once in each file.

  **Edit O1**, anchor `_skipped` (owner.py:708-724, sign.py:631-647): `_guards` goes right after `_typing_flag`, and
  `_skipped` takes the guards tuple. Old text (exact):

```python
def _skipped(node: ast.AST, bare_flag: bool) -> bool:
    """Whether `node` is an `if` whose body never runs at import and so is outside the code closure (P6):
    `if typing.TYPE_CHECKING:`, `if TYPE_CHECKING:` when `bare_flag` (see _typing_flag), and a single `==`
    comparison of `__name__` with "__main__" in either order. Every other test (`!=`, `not TYPE_CHECKING`, a local
    TYPE_CHECKING) is scanned, since its body can run at import."""
    if not isinstance(node, ast.If):
        return False
    t = node.test
    if isinstance(t, ast.Name):
        return t.id == "TYPE_CHECKING" and bare_flag
    if isinstance(t, ast.Attribute):
        return t.attr == "TYPE_CHECKING" and isinstance(t.value, ast.Name) and t.value.id == "typing"
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
        sides = [t.left, *t.comparators]
        return (any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides)
                and any(isinstance(s, ast.Constant) and s.value == "__main__" for s in sides))
    return False
```

  New text:

```python
def _guards(tree: ast.AST) -> tuple[bool, bool, bool]:
    """Which `if` guards of `tree` may skip their body (P6, R4): (bare TYPE_CHECKING, typing.TYPE_CHECKING,
    __name__ == "__main__"). The bare name needs _typing_flag; `typing.` needs `typing` bound exactly once, by a
    plain `import typing`; the `__main__` test needs `__name__` bound nowhere in the module. A rebound name
    (typing = SimpleNamespace(TYPE_CHECKING=True), __name__ = "__main__") loses its guard, and a module that can
    change these names without binding them (an attribute store of TYPE_CHECKING or __name__, or any setattr,
    delattr, globals, vars, locals, modules, __dict__, builtins, __builtins__, f_globals or f_locals) trusts no
    guard: the guarded body is scanned. Not seen: another module changing typing.TYPE_CHECKING first (the review of
    each hashed diff)."""
    plain = any(isinstance(n, ast.Import) and any(a.name == "typing" and a.asname is None for a in n.names)
                for n in ast.walk(tree))
    routes = {"setattr", "delattr", "globals", "vars", "locals", "modules", "__dict__", "builtins", "__builtins__",
              "f_globals", "f_locals"}
    if any((isinstance(n, ast.Name) and n.id in routes) or (isinstance(n, ast.Attribute) and (n.attr in routes or (
            n.attr in ("TYPE_CHECKING", "__name__") and not isinstance(n.ctx, ast.Load)))) for n in ast.walk(tree)):
        return False, False, False
    return _typing_flag(tree), plain and _binds(tree, "typing") == 1, _binds(tree, "__name__") == 0


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

  **Edit O2**, anchor `_import_nodes` (owner.py:727-736, sign.py:650-659): the parameter becomes the guards tuple;
  the docstring stays. Old text (exact):

```python
def _import_nodes(node: ast.AST, bare_flag: bool):
    """Every import statement at any depth, function bodies included; a skipped `if` keeps its `else`."""
    if _skipped(node, bare_flag):
        for child in node.orelse:
            yield from _import_nodes(child, bare_flag)
        return
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        yield node
    for child in ast.iter_child_nodes(node):
        yield from _import_nodes(child, bare_flag)
```

  New text:

```python
def _import_nodes(node: ast.AST, guards: tuple[bool, bool, bool]):
    """Every import statement at any depth, function bodies included; a skipped `if` keeps its `else`."""
    if _skipped(node, guards):
        for child in node.orelse:
            yield from _import_nodes(child, guards)
        return
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        yield node
    for child in ast.iter_child_nodes(node):
        yield from _import_nodes(child, guards)
```

  **Edit O3**, anchor `_repo_imports` (owner.py:754-755, sign.py:677-678). Old text (exact):

```python
    tree = ast.parse(path.read_bytes())
    for node in _import_nodes(tree, _typing_flag(tree)):
```

  New text:

```python
    tree = ast.parse(path.read_bytes())
    for node in _import_nodes(tree, _guards(tree)):
```

  No other line changes: `_binds`, `_typing_flag`, `_module_file`, `code_files`, `code_hash`, `_RECORD_DISTS` and
  sign.py's section comment (sign.py:597-602, "An `if` body that never runs at import is skipped (see _skipped);
  every other body is scanned.", still true) are untouched. Then check (read-only, Git Bash, no overlap check
  needed):

```bash
git diff --stat
git diff --stat --ignore-cr-at-eol
git grep -n -E "bare_flag|_import_nodes\(tree, _typing_flag" -- core/compliance/owner.py tools/signer/sign.py
```

  Expected: the two stat outputs identical, with the per-file counts `core/compliance/owner.py | 44`,
  `tests/compliance_signer.py | 41`, `tests/compliance_store.py | 45`, `tools/signer/sign.py | 44` (each followed by
  its `+`/`-` bar) and `4 files changed, 149 insertions(+), 25 deletions(-)` (owner.py and sign.py 32 insertions and
  12 deletions each; the signer test 41 insertions; the store test 44 insertions and 1 deletion; `git diff
  --no-index --numstat` on scratch copies of the four files with Edits T0-T5 and O1-O3 applied, at the plan's final
  assembly); the `git grep` prints nothing (exit code 1).

- [ ] **Step 4: Run to verify it passes**

  Overlap check (PowerShell tool, as in Step 2; it must print nothing), then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected, ending: `29/29 passed, 0 failed, 0 not run` (exit code 0; `test_code_files_is_the_import_closure` still
  passes, so the real closure is the same 10 entries, and the eight route asserts on `owner._guards` pass).

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected, ending: `38/38 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then the compliance suite (its guards scan the new owner.py text: raw words, imports, dynamic names,
  HTTP verbs, clock calls), then restore the results file. Every `--suite` run first imports all ten suites
  (run_all.py:41-50) and the compliance tests alone took 64 s on 2026-10-24, so give this line `timeout: 300000`;
  never start a second run meanwhile:

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected, ending:

```
323/325 passed, 0 failed, 2 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json
exit 0
```

  (325 rows: 324 after Task 3 plus the new signer test; the two not-run rows are the REFDATA symlink
  tests). A guard failure names the file and text: fix owner.py, never the guard. Then `git status --short` lists
  exactly the four files of this task, plus, if the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add core/compliance/owner.py tools/signer/sign.py tests/compliance_store.py tests/compliance_signer.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (all four files are LF; the counts of Step 3). Then:

```bash
git commit -m "fix(compliance): closure scan skips a guard only while its name is unbound and unmutated" -m "R4 (ledger:208): owner._guards and its character-identical signer copy; a rebound typing or __name__, or an attribute store, setattr, globals, sys.modules or frame f_globals/f_locals route, voids the guard; source-equality test added." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: The signer's ancestor walk fails closed (`tools/signer/sign.py`)

**Files:**
- Modify: `tools/signer/sign.py` (anchors: the module docstring's first paragraph and its "Every time, before you type
  the passphrase" list; `_has_claude_ancestor`; the `_claude_ancestor()` branch of `_refusal`; LF). Repo copy only:
  the owner's own copy changes only by the owner act at the end of this task.
- Test: `tests/compliance_signer.py` (anchors: `test_main_refuses_claude_parent_and_non_tty_stdin`,
  `test_claude_ancestor_walk`, `test_claude_ancestor_check_fails_closed`, `test_help_names_owner_acts_1_and_2`; LF)

**Interfaces:**
- Consumes:
  - `tools/signer/sign.py` as Task 4 leaves it: `_process_table() -> dict[int, tuple[int, str]]` (pid -> (parent pid,
    exe name), unchanged), `_claude_ancestor() -> bool` (unchanged: True on a failed snapshot or a table without our
    own pid, else `_has_claude_ancestor(os.getpid(), table)`), `_refusal() -> str`, `main(argv=None) -> int`,
    `_parser() -> argparse.ArgumentParser` (its description is the module docstring).
  - `tests/compliance_signer.py` as Task 4 leaves it (38 tests): `signer` (the module loaded by
    `spec_from_file_location`), `_patched(obj, name, value)`, `_quiet(fn, *args)`, `_env_without_claude()`, `_Tty`,
    `_never`, `_home()`.
- Produces (`tools/signer/sign.py`):
  - `_SESSION_ROOTS = frozenset({"explorer.exe", "services.exe", "wininit.exe", "winlogon.exe"})`;
  - `_has_claude_ancestor(pid: int, table: dict[int, tuple[int, str]]) -> bool`, same signature, new rule: True on a
    claude.exe anywhere in the chain (any case), True on a break (a pid missing from `table`, a pid-reuse cycle, 256
    steps) unless a session process was passed first, False only at pid 0 or at such a break after a session process;
  - the `_refusal()` text for that branch, which contains "claude.exe" and "has exited".
  No later task calls these; Task 8 carries the owner act below into the plan's hand-off.

**Plan decisions used:** R5, R11 (and R13 for the drift rule).

Design notes (read before Step 1):
- What changes. Today `_has_claude_ancestor` (sign.py:758-767) ends with `return False` whenever its loop stops, so a
  parent that has exited, a pid-reuse cycle or the 256-step cap all read as "no Claude ancestor": a refusal check
  that fails open (ledger:229 rules that a refusal check fails closed; ledger:233 names this walk). After this task
  the walk goes on until pid 0 or a break, and a break refuses unless the walk has already passed a Windows session
  process (`_SESSION_ROOTS`): a user's chain normally passes one of them before its top parent, which has exited.
- Why the root is not pid 0 alone (R11). Read-only probes of the live process table on 2026-10-24 (the probe behind
  R11 in Appendix A section 1, and this task's re-run through the repo signer's own `_process_table`, 721
  processes): pid 0 is `[System Process]` and no user chain reaches it; every chain ends at a parent that has
  exited. The owner's Windows Terminal chain is `powershell.exe -> WindowsTerminal.exe -> svchost.exe ->
  services.exe -> wininit.exe -> (exited)`, `explorer.exe`'s, `wininit.exe`'s and `winlogon.exe`'s own parents
  have exited (`services.exe`'s parent is the live `wininit.exe`), and 298 processes end at `wininit.exe ->
  (exited)`. A pid-0-only root would refuse the very terminal spec 6.4 says the signer runs in. With this walk that
  chain still passes (it passes `services.exe` and `wininit.exe` before the break), and so does a terminal started
  from `explorer.exe`.
- A session process never stops the walk. A process name is only a file name: a copy of cmd.exe saved as
  winlogon.exe and run under Claude must not end the search before the claude.exe above it (today's walk refuses
  that chain because it walks on; so does this one, test case `renamed`).
- Every chain refused today stays refused. The old walk returned True only on reaching a claude.exe. The new walk
  takes the same steps (same table lookups, same cycle test, same 256-pid cap), so it reaches the same claude.exe;
  the only step it no longer takes is through pid 0, which on Windows is `[System Process]`, its own parent, never
  claude.exe. The re-run above agrees: over the 721 live processes, (old, new) verdicts were (True, True) 169,
  (False, False) 324, (False, True) 228, and never (True, False). The 228 that now refuse are chains that end at a
  launcher that has exited without a session process on the way: VS Code terminals (`powershell.exe -> Code.exe ->
  Code.exe -> (exited)`), a tray app's or a browser's children, a console whose parent exited.
- The refusal text names the new cause and the fix: open Windows Terminal from the Start menu. The help gains the
  same first bullet, and the docstring's refusal sentence names the new rule.
- For the controller, not for this task: sign.py's existing help (sign.py:5-31) gives its commands in Command Prompt
  syntax (`%USERPROFILE%` in the certutil, keygen and code-approve lines; test_help_names_owner_acts_1_and_2 pins the
  certutil one), while the new bullet sends the owner to Windows Terminal, which opens PowerShell (R11's chain), where
  `%USERPROFILE%` is not expanded. This plan does not edit the existing help without a ruling: either the help says
  "Command Prompt", or rewriting it for PowerShell is ruled as a later task. The owner act at the end of this task
  uses PowerShell syntax, as Task 8 Step 9 does.
- Departures from Appendix A (the task wins): Edit 2 adds the `shell` and `service` cases, the `roots` pin of
  `_SESSION_ROOTS`, a docstring and assertion messages to Appendix A section 7.3's test; Edit 3 adds a docstring
  change and an assertion message; Edit 4 adds two needles to test_help_names_owner_acts_1_and_2, which section 7.3
  does not list (that test already pins help needles, as section 7.2 says, and Edit 4 adds the two new ones); Edit
  7's comment and docstring differ (Step 3 notes); the owner act uses PowerShell syntax where section 7.3's uses
  Command Prompt syntax.
- Honest limits (R11, spec 6.4): a process started through COM activation or the desktop shell has no claude.exe
  ancestor, so this check stays defence in depth; the passphrase and the typed code are the barrier. A session
  process is recognised by its file name only, so a chain that passes a process carrying one of those names and
  then breaks, with no claude.exe on the way, passes (today any break passed). A reused pid above a session
  process is walked too, so if it now runs claude.exe the signer refuses, as today, until Claude is closed.
- Drift rule (Global Constraints; Appendix A section 0). Task 4 lands first and inserts `_guards` above `_skipped`
  in sign.py, so the sign.py lines cited here below :631 (`_has_claude_ancestor`, `_refusal`) sit 20 lines lower;
  it adds tests to `test_code_files_match_owner` and a new test after it, so `test_help_names_owner_acts_1_and_2`
  (tests/compliance_signer.py:1094) sits lower too. Neither changes any text quoted below. Before each Edit, re-read
  the file and find the anchor; if the quoted old text differs only because an earlier plan changed it, apply the
  same change to the current text, keep that earlier behaviour, and add one line to
  `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`.

- [ ] **Step 1: Write the failing tests**

  Four Edit-tool replacements in `tests/compliance_signer.py` (LF; keep LF).

**Edit 1 of 8** — `tests/compliance_signer.py`, anchor: `test_main_refuses_claude_parent_and_non_tty_stdin` (the
first `with` block and its assertion; tests/compliance_signer.py:222-224). The refusal must name the new cause.

Old text (exact):
```python
        with _patched(signer, "_claude_ancestor", lambda: True), _patched(sys, "stdin", _Tty()):
            code, _, err = _quiet(signer.main, ["keygen"])
        assert code == 2 and "claude.exe" in err, (code, err)
```

New text:
```python
        with _patched(signer, "_claude_ancestor", lambda: True), _patched(sys, "stdin", _Tty()):
            code, _, err = _quiet(signer.main, ["keygen"])
        assert code == 2 and "claude.exe" in err and "has exited" in err, (code, err)
```

**Edit 2 of 8** — `tests/compliance_signer.py`, anchor: `test_claude_ancestor_walk` (the whole function;
tests/compliance_signer.py:285-293). Two assertions flip on purpose: the pid-reuse cycle and the empty table now
refuse.

Old text (exact):
```python
def test_claude_ancestor_walk():
    table = {10: (9, "python.exe"), 9: (8, "cmd.exe"), 8: (7, "Claude.exe"), 7: (0, "explorer.exe")}
    assert signer._has_claude_ancestor(10, table) is True
    assert signer._has_claude_ancestor(9, {**table, 8: (7, "WindowsTerminal.exe")}) is False
    assert signer._has_claude_ancestor(1, {1: (2, "a.exe"), 2: (1, "b.exe")}) is False      # pid-reuse cycle ends
    assert signer._has_claude_ancestor(5, {}) is False
    if os.name == "nt":
        live = signer._process_table()
        assert live[os.getpid()][0] == os.getppid(), live.get(os.getpid())
```

New text:
```python
def test_claude_ancestor_walk():
    """R5, R11: a claude.exe anywhere in the chain refuses, even above a session process, and so does a walk that
    breaks (an exited parent, a pid-reuse cycle, more than 256 steps) before it has passed a session process."""
    table = {10: (9, "python.exe"), 9: (8, "cmd.exe"), 8: (7, "Claude.exe"), 7: (0, "explorer.exe")}
    assert signer._has_claude_ancestor(10, table) is True
    assert signer._has_claude_ancestor(9, {**table, 8: (7, "WindowsTerminal.exe")}) is False
    terminal = {20: (21, "python.exe"), 21: (22, "powershell.exe"), 22: (23, "WindowsTerminal.exe"),
                23: (24, "svchost.exe"), 24: (25, "services.exe"), 25: (99, "wininit.exe")}      # 99 has exited
    assert signer._has_claude_ancestor(20, terminal) is False, "the owner's Windows Terminal chain (R11)"
    shell = {50: (51, "python.exe"), 51: (52, "cmd.exe"), 52: (53, "Explorer.EXE")}             # 53 has exited
    assert signer._has_claude_ancestor(50, shell) is False, "a console started from explorer.exe, any case (R11)"
    renamed = {1: (2, "python.exe"), 2: (3, "winlogon.exe"), 3: (4, "bash.exe"), 4: (5, "claude.exe"),
               5: (0, "explorer.exe")}                       # cmd.exe saved as winlogon.exe, run under Claude
    assert signer._has_claude_ancestor(1, renamed) is True, "a session process name never ends the walk"
    assert signer._has_claude_ancestor(1, {1: (2, "a.exe"), 2: (1, "b.exe")}) is True, "a pid-reuse cycle refuses"
    assert signer._has_claude_ancestor(5, {}) is True, "an empty table refuses"
    exited = {30: (31, "python.exe"), 31: (32, "Code.exe")}                                    # 32 has exited
    assert signer._has_claude_ancestor(30, exited) is True, "an editor terminal whose launcher has exited"
    assert signer._has_claude_ancestor(40, {40: (41, "python.exe"), 41: (0, "CLAUDE.EXE")}) is True, "any case"
    deep = {**{n: (n + 1, "python.exe") for n in range(1, 300)}, 300: (0, "wininit.exe")}
    assert signer._has_claude_ancestor(1, deep) is True, "the 256-step cap refuses"
    service = {60: (61, "python.exe"), 61: (62, "svchost.exe")}                                # 62 has exited
    assert signer._has_claude_ancestor(60, service) is True, "svchost.exe is no session process"
    roots = frozenset({"explorer.exe", "services.exe", "wininit.exe", "winlogon.exe"})
    assert signer._SESSION_ROOTS == roots, "exactly the four session processes: one more makes the walk looser (R11)"
    if os.name == "nt":
        live = signer._process_table()
        assert live[os.getpid()][0] == os.getppid(), live.get(os.getpid())
```

**Edit 3 of 8** — `tests/compliance_signer.py`, anchor: `test_claude_ancestor_check_fails_closed` (the whole
function; tests/compliance_signer.py:296-311). It gains the exited-parent case; `{me: (0, "python.exe")}` stays
False.

Old text (exact):
```python
def test_claude_ancestor_check_fails_closed():
    """Claude is ruled out only from a process table that holds this very process: a failed snapshot, an empty
    table or a table without our pid all read as "cannot rule it out"."""
    me = os.getpid()

    def broken():
        raise OSError("Process32FirstW failed")

    for table in (lambda: {}, lambda: {me + 1: (0, "python.exe")}, broken,
                  lambda: (_ for _ in ()).throw(TypeError("ctypes")), lambda: (_ for _ in ()).throw(ImportError("x"))):
        with _patched(signer, "_process_table", table):
            assert signer._claude_ancestor() is True, table
    with _patched(signer, "_process_table", lambda: {me: (0, "python.exe")}):
        assert signer._claude_ancestor() is False
    with _patched(signer, "_process_table", lambda: {me: (7, "python.exe"), 7: (0, "Claude.exe")}):
        assert signer._claude_ancestor() is True
```

New text:
```python
def test_claude_ancestor_check_fails_closed():
    """Claude is ruled out only from a process table that holds this very process and whose parent chain reaches
    pid 0 or passes a Windows session process: a failed snapshot, an empty table, a table without our pid or a
    parent that has exited all read as "cannot rule it out" (R5)."""
    me = os.getpid()

    def broken():
        raise OSError("Process32FirstW failed")

    for table in (lambda: {}, lambda: {me + 1: (0, "python.exe")}, broken,
                  lambda: (_ for _ in ()).throw(TypeError("ctypes")), lambda: (_ for _ in ()).throw(ImportError("x"))):
        with _patched(signer, "_process_table", table):
            assert signer._claude_ancestor() is True, table
    with _patched(signer, "_process_table", lambda: {me: (0, "python.exe")}):
        assert signer._claude_ancestor() is False
    with _patched(signer, "_process_table", lambda: {me: (me + 1, "python.exe")}):
        assert signer._claude_ancestor() is True, "a parent that has exited refuses (R5)"
    with _patched(signer, "_process_table", lambda: {me: (7, "python.exe"), 7: (0, "Claude.exe")}):
        assert signer._claude_ancestor() is True
```

**Edit 4 of 8** — `tests/compliance_signer.py`, anchor: `test_help_names_owner_acts_1_and_2` (its `for needle in`
loop; tests/compliance_signer.py:1096-1103 before Task 4). The help (the module docstring) must carry the new
bullet and the new refusal sentence. The other needles stay.

Old text (exact):
```python
    for needle in ("certutil -hashfile %USERPROFILE%\\tradegen-signer\\sign.py SHA256", "away from the PC",
                   "keygen", "code-approve", "owner_pubkey.pem", "at least 20 characters",
                   "at least 5 different words", "python.exe -I", "site-packages\\*.pth",
                   "Claude never runs this file", "from the next Asia/Seoul date", "blanks do not count",
                   "Key rotation", "keygen --key NEW\\owner_key.enc", "event key_rotated", "copy NEW\\owner_key.pem",
                   "owner_pubkey.pem", "pass --key NEW\\owner_key.enc to every command",
                   "reads BROKEN between steps 3 and 4", "write the new fingerprint on paper"):
        assert needle in " ".join(text.split()), needle
```

New text:
```python
    for needle in ("certutil -hashfile %USERPROFILE%\\tradegen-signer\\sign.py SHA256", "away from the PC",
                   "keygen", "code-approve", "owner_pubkey.pem", "at least 20 characters",
                   "at least 5 different words", "python.exe -I", "site-packages\\*.pth",
                   "Claude never runs this file", "from the next Asia/Seoul date", "blanks do not count",
                   "Key rotation", "keygen --key NEW\\owner_key.enc", "event key_rotated", "copy NEW\\owner_key.pem",
                   "owner_pubkey.pem", "pass --key NEW\\owner_key.enc to every command",
                   "reads BROKEN between steps 3 and 4", "write the new fingerprint on paper",
                   "open Windows Terminal yourself from the Start menu",               # R5, R11
                   "when its parent chain stops before a Windows session process"):
        assert needle in " ".join(text.split()), needle
```

- [ ] **Step 2: Run to verify it fails**

  Run from the repo root in Git Bash (the Bash tool), behind the QUANTGEN overlap check. The prefix prints nothing
  and runs the command only when no python `run_all` is running; if the line exits 1 with no output, a run is in
  progress: wait, then run it again.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected: four FAIL lines on stdout (their tracebacks go to stderr, in any interleaving), in this order, and the
  count. The other 34 pass, Task 4's included.

```text
FAIL compliance_signer/test_claude_ancestor_check_fails_closed AssertionError: a parent that has exited refuses (R5)
FAIL compliance_signer/test_claude_ancestor_walk AssertionError: a pid-reuse cycle refuses
FAIL compliance_signer/test_help_names_owner_acts_1_and_2 AssertionError: open Windows Terminal yourself from the Start menu
FAIL compliance_signer/test_main_refuses_claude_parent_and_non_tty_stdin AssertionError: (2, 'sign.py refused: a parent process is claude.exe: run me in your own terminal, never under Claude\n')

34/38 passed, 4 failed, 0 not run
```

  (In the last line `\n` is the two characters of the repr, not a line break.) A `NOT_RUN ... PENDING:
  cryptography not installed` line means the venv lost `cryptography`; stop and report.

- [ ] **Step 3: Implement**

  Four Edit-tool replacements in `tools/signer/sign.py` (LF; keep LF: the owner certutil-hashes these exact bytes).
  Edits 5 and 6 change the module docstring, which is also the `--help` text; they are shown as text, not code.

**Edit 5 of 8** — `tools/signer/sign.py`, anchor: the module docstring's first paragraph (sign.py:2-3, the sentence
"and refuses to run under Claude ..."). Line 3 becomes two lines.

Old text (exact):
```text
Windows Terminal. It uses the standard library and `cryptography`, never imports the TRADEGEN repo, and refuses to
run under Claude, under a claude.exe parent process, without a terminal on stdin, or without python.exe -I.
```

New text:
```text
Windows Terminal. It uses the standard library and `cryptography`, never imports the TRADEGEN repo, and refuses to
run under Claude, under a claude.exe parent process, when its parent chain stops before a Windows session process,
without a terminal on stdin, or without python.exe -I.
```

**Edit 6 of 8** — `tools/signer/sign.py`, anchor: the module docstring's list "Every time, before you type the
passphrase" (sign.py:22-23). A new first bullet.

Old text (exact):
```text
Every time, before you type the passphrase
  - start it with python.exe -I, as above. -I keeps the folder of sign.py, the current folder and PYTHON*
```

New text:
```text
Every time, before you type the passphrase
  - open Windows Terminal yourself from the Start menu (an editor's terminal can be refused: its parent chain may
    stop at a launcher that has exited);
  - start it with python.exe -I, as above. -I keeps the folder of sign.py, the current folder and PYTHON*
```

**Edit 7 of 8** — `tools/signer/sign.py`, anchor: `_has_claude_ancestor` (the whole function, sign.py:758-767,
between `_process_table` and `_claude_ancestor`). The new constant and its comment go right above it.
`_claude_ancestor` below it is unchanged.

Old text (exact):
```python
def _has_claude_ancestor(pid: int, table: dict[int, tuple[int, str]]) -> bool:
    """True when `pid` or any ancestor in `table` runs claude.exe (any version, any case); pid reuse cycles end."""
    seen = set()
    while pid in table and pid not in seen and len(seen) < 256:
        seen.add(pid)
        parent, exe = table[pid]
        if exe.lower() == "claude.exe":
            return True
        pid = parent
    return False
```

New text:
```python
# Windows session processes: a user's chain normally passes one of these before its top parent exits (R11).
_SESSION_ROOTS = frozenset({"explorer.exe", "services.exe", "wininit.exe", "winlogon.exe"})


def _has_claude_ancestor(pid: int, table: dict[int, tuple[int, str]]) -> bool:
    """True when `pid` or any ancestor in `table` runs claude.exe (any version, any case), even above a Windows
    session process (a process name is only a file name). The walk goes on to pid 0 or until it breaks: at a pid
    missing from the table (a parent that has exited), a pid-reuse cycle or 256 steps. A break returns True (Claude
    cannot be ruled out) unless the walk has passed a session process (_SESSION_ROOTS): a user chain's top parent
    has normally exited (explorer.exe's, wininit.exe's), and Windows Terminal runs under svchost.exe, services.exe
    and wininit.exe (R11)."""
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

**Edit 8 of 8** — `tools/signer/sign.py`, anchor: `_refusal`, its `if _claude_ancestor():` branch (sign.py:810-811).
The other refusals and their order stay.

Old text (exact):
```python
    if _claude_ancestor():
        return "a parent process is claude.exe: run me in your own terminal, never under Claude"
```

New text:
```python
    if _claude_ancestor():
        return ("a parent process is claude.exe, or the parent chain stops at a process that has exited: open Windows "
                "Terminal yourself from the Start menu and run me there, never under Claude")
```

  Notes:
  - Nothing else in sign.py changes: `_process_table`, `_claude_ancestor` (it already fails closed on a failed
    snapshot or a table without our own pid), `_isolated`, `_stdin_is_terminal`, the Task 4 closure helpers,
    `code_files` and `code_hash` keep their text. sign.py is off the D14 closure (it is not under `core/`), so the
    code hash does not move in this task; the owner's copy is what the owner act below updates.
  - The longest new line is 119 characters (`return ("a parent process ...`); every new line in this task's
    edits is within 120 columns.
  - Dry run (2026-10-24, sandbox copies of both files with Edits 1-8 applied to the tree at `5816d3c`): each quoted
    old text occurs exactly once; the four tests fail before Edits 5-8 with exactly the Step 2 lines and pass after
    them; over 200,000 random process tables (pid 0 never claude.exe, as on Windows, where it is `[System Process]`)
    the old walk's True is always the new walk's True, and every new False reached pid 0 or broke after a session
    process with no claude.exe on the way.
  - Edit 7 differs from Appendix A section 7.1 in its comment and docstring only, and the task wins (header): 7.1
    says the session processes' parents exit, but `services.exe`'s parent is the live `wininit.exe` (read-only
    probe, 2026-10-24). The code and its behaviour are 7.1's. The test's `roots` pin is new too: adding a name to
    `_SESSION_ROOTS` makes the walk looser, and without the pin a mutant adding `svchost.exe` passed every test.

- [ ] **Step 4: Run to verify it passes**

  Each command behind the overlap check, from the repo root in Git Bash:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected last line: `38/38 passed, 0 failed, 0 not run`.

  Then the compliance suite. Every `--suite` run first imports all ten suites, and the compliance tests alone took
  64 s in the 2026-10-24 record, so give this line `timeout: 300000`; never start a second run meanwhile. If it
  prints only `exit 1` and no test lines, the overlap check found a run_all in progress (the checkout was a harmless
  no-op): wait, then run the line again.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: `323/325 passed, 0 failed, 2 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json`
  then `exit 0`. The two NOT_RUN lines are the `REFDATA: symlink creation needs Developer Mode` tests
  (`compliance_isolation/test_symlinks_are_refused`, `compliance_tables/test_calendar_sha256_refuses_a_file_symlink`);
  with Developer Mode on it ends `325/325 passed, 0 failed, 0 not run`. The run's numbers win over these if an earlier
  task's count differed; what must hold is `0 failed`. Then confirm the results file is restored and only the two
  files are pending:

```bash
git status --short
```

  Expected: these two lines,

```text
 M tests/compliance_signer.py
 M tools/signer/sign.py
```

  plus, if the executor keeps its ledger in the repo,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` (untracked until Task 8 Step 8
  commits it). Anything else, `qa/acceptance_results.json` included, is restored or removed before the commit.

- [ ] **Step 5: Commit**

  Both files must stay LF (the owner hashes the exact bytes of sign.py). This prints `[0, 0]`:

```bash
.venv/Scripts/python.exe -I -c "print([open(p, 'rb').read().count(b'\r\n') for p in ('tools/signer/sign.py', 'tests/compliance_signer.py')])"
```

  Then:

```bash
git add tools/signer/sign.py tests/compliance_signer.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -m "fix(signer): the ancestor walk refuses when the chain breaks before a session process" -m "An exited parent, a pid-reuse cycle or 256 steps now refuse unless the walk passed explorer, services, wininit or winlogon; a claude.exe anywhere still refuses (R5, R11; ledger:229, :233)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  The two `--stat` outputs must be identical (2 files changed).

**Owner act (for the plan's hand-off list; Claude never does it).** `tools/signer/sign.py` changed in Tasks 4 and 5.
Every command below is for Windows Terminal (PowerShell), as in Task 8 Step 9.
- Owner act 1 (spec 11) is not done yet, so when you do it, copy the merged `tools/signer/sign.py` (from `main` after
  this plan merges) to your folder `$env:USERPROFILE\tradegen-signer\`, read all of it, and in Windows Terminal
  (PowerShell) hash that copy with `certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256`, then
  finish act 1 as spec section 11 lists it.
- If you already copied an earlier version to `$env:USERPROFILE\tradegen-signer\sign.py`: in Windows Terminal
  (PowerShell) compare it with the repo file while `main` is checked out after this plan merges (`git switch main`
  first; another branch may hold unreviewed, unmerged changes to sign.py):
  `fc.exe /n "$env:USERPROFILE\tradegen-signer\sign.py" "C:\Users\whydi\OneDrive\Desktop\TRADEGEN\tools\signer\sign.py"`
  (`fc.exe`, because in PowerShell `fc` is Format-Custom). Read every changed line, copy the repo file over your
  copy, run `certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256`, and write the new hash on the
  paper, crossing out the old one.
- From then on, open Windows Terminal from the Start menu to sign: a terminal inside an editor (VS Code) can be
  refused, because its parent chain may stop at a launcher that has exited.

### Task 6: alerts.jsonl records a fingerprint only from codes 0 to 2 (`core/compliance/alerts.py`)

**Files:**
- Modify: `core/compliance/alerts.py` (anchor: `log()`, its docstring and the lines from the row build to the
  `_in_log` check; LF). A D14 closure file: the code hash moves (no `code_approved` exists yet, so nothing is
  re-signed now).
- Test: `tests/compliance_cli.py` (anchor: a new test inserted right above `test_log_refuses_bad_input_and_writes_nothing`,
  that is after `test_log_rows_carry_anchor_and_fingerprint` and its helper `_canonical_line`; LF)

**Interfaces:**
- Consumes:
  - `core.compliance.alerts`: `log(channel: str, result: str, summary: dict, now: datetime) -> None` (raises
    ValueError before writing for a bad channel, result, summary, naive `now` or head), `_first(history) -> dict |
    None`, `_history() -> list[dict]`, `due(summary, history, today) -> list[dict]`; `rules._SUMMARY_KEYS` (`code,
    due, overdue, head_seq, head_sha256, fingerprint`); `owner._first_recorded() -> tuple[str, str] | None`
    (owner.py:913-918, the first alerts.jsonl row with a non-empty fingerprint, P20).
  - `tests/compliance_cli.py`: `_sample(**over)` (code 0, nothing due, head (0, ""), fingerprint `FP`),
    `_alerts_lines() -> list[dict]`, `FP = "SHA256:" + "f" * 64`, and the module imports `date`, `datetime`,
    `timezone`, `alerts`, `owner`, `rules`.
- Produces: `log()` writes `row["fingerprint"] == ""` whenever `summary["code"] > 2` (codes 3 and 4); codes 0, 1 and
  2 keep the summary's fingerprint; every row keeps all nine keys. New test
  `test_log_records_a_fingerprint_only_from_codes_0_to_2`. No later task calls anything new.

**Plan decisions used:** R6; the DRIFT RULE (Global Constraints).

Design notes (read before Step 1):
- Why. The key is held to the first fingerprint alerts.jsonl records (P20; `owner._first_recorded`, owner.py:913-918,
  and `alerts._first`, alerts.py:97-100). Today `log()` copies the summary's `fingerprint` into every row
  (alerts.py:253-254), whatever the code, so the first recorded one can come from a code 3 summary (a broken log,
  KEY CHANGED, unsigned code, an unapproved table; ledger:219). R6 blanks code 4 too: rules.main and `_MISSING`
  already write `""` there (rules.py:962, alerts.py:24), so only a hand-written `--summary` could give a code 4 row a
  fingerprint. A code 3 summary carries the fingerprint of whatever `owner_pubkey.pem` holds even when the log does
  not verify against it (owner.py `_owner_now` passes `fingerprint_now` into the BROKEN state; a swapped key file
  reads as a broken log). Recorded first, that fingerprint becomes the P20 reference: `owner_state` then reads the owner's real key as KEY CHANGED
  from then on (owner.py:470-474), and `due()` raises no KEY CHANGED headline for a later check with the unverified
  key (alerts.py:128-131; the last assertion of the new test). After this task a code 3 or 4 row records `""`, which
  both readers already skip, so the first recorded fingerprint always comes from a check that verified the log
  (exit 0, 1 or 2).
- Where. One `if` in `log()` after the row is built and before the `_in_log` check, so every caller (the toast row of
  `main()`, `--log CHANNEL RESULT`, the daily task) goes through it. `_valid_summary`, `due()`, `render()` and
  `_footer` are unchanged: the footer still prints the summary's current fingerprint as "Key now ...", and `due()`
  still compares a code 3 summary's fingerprint with the first recorded one. `_MISSING` (code 4) already carries
  `""`.
- What stays green. `test_log_rows_carry_anchor_and_fingerprint` logs code 1 rows and still reads `FP` back;
  `test_check_code_3_key_changed` logs a code 0 summary; `test_alerts_main_send_toasts_once_and_logs` logs a code 3
  toast row after a code 1 row and asserts only its channel and result, and its footer reads the code 1 row; the
  hand-built histories of `test_due_key_changed` and `test_render_fixed_template_and_sanitises` never pass through
  `log()`.
- Departures from Appendix A (the task wins). Appendix A section 8's test logs codes 3, 4 and 0 and checks the two
  blank fingerprints and the first recorded one. This task's test also logs a code 2 row (an overdue date, the other
  fingerprint) and checks that it keeps that fingerprint, checks every row's code and fingerprint and its nine keys,
  and calls `due()` to show that a later code 3 check with the unverified key still owes KEY CHANGED; its docstring
  says so. `log()` and its docstring are as in section 8.
- A consequence the owner should know (it follows from R6, not a new rule). Between owner act 1 and the first alert
  sent from a check that exits 1 or 2 (a row date within 14 days, or overdue), alerts.jsonl records no fingerprint.
  An exit-0 check owes no alert and writes no row (`due()` returns `[]` for code 0 and `main()` returns before
  `log()`, alerts.py:329-331; the daily prompt stops on `"send": false`, compliance plan :16676). Every check exits 3
  until owner acts 2 and 3 (unsigned code, an unapproved table). After them, a `review_by` is at most 31 days after
  its review (rules.py:524), so the first 14-day alert comes at most about 17 days after the reviewed table is
  approved, and sooner when a date is closer. Until then the alert footer reads "first recorded none yet", and the
  fingerprint written on paper at owner act 1 is the only reference, including against a swap of key and log
  together. Throughout, a check exits 0 to 2 only when the owner log verifies against the key file; what the window
  lacks is the alerts.jsonl reference for the key itself. The controller accepts this window as a stated limit (the
  plan header's "Spec" list): new exposure stays blocked until a check exits 0, 1 or 2.
- Drift rule. Task 2 lands first and rewrites tests/compliance_cli.py:576-577 inside `test_render_has_no_rule_free_text`
  (above this task's anchor), two lines for two, so the tests/compliance_cli.py line numbers cited here do not move;
  no earlier task of this plan touches alerts.py. Before each Edit, re-read the file
  and find the anchor; if the quoted old text differs only because an earlier plan changed it, apply the same change
  to the current text, keep that earlier behaviour, and add one line to
  `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`.

- [ ] **Step 1: Write the failing test**

**Edit 1 of 2** — `tests/compliance_cli.py`, anchor: `test_log_refuses_bad_input_and_writes_nothing` (its first two
lines, tests/compliance_cli.py:631-632). The new test goes right above it, after `_canonical_line`.

Old text (exact):
```python
def test_log_refuses_bad_input_and_writes_nothing():
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
```

New text:
```python
def test_log_records_a_fingerprint_only_from_codes_0_to_2():
    """R6 (ledger:219): the key is held to the first fingerprint alerts.jsonl records (P20), so a code 3 or 4
    summary, which can come from a key the log does not verify, records "" and never becomes that first one, and a
    later check with that key still owes KEY CHANGED. Codes 0 and 2 keep theirs here (code 1 in
    test_log_rows_carry_anchor_and_fingerprint)."""
    now = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)
    other = "SHA256:" + "0" * 64
    late = [{"row": "KR-X", "field": "review_by", "date": "2026-11-22", "days_late": 1}]
    alerts.log("email", "ok", _sample(code=3, fingerprint=other), now)
    alerts.log("push", "ok", _sample(code=4, fingerprint=other), now)
    fingerprints = [r["fingerprint"] for r in _alerts_lines()]
    assert fingerprints == ["", ""], fingerprints
    assert owner._first_recorded() is None and alerts._first(alerts._history()) is None
    alerts.log("email", "ok", _sample(code=0), now)
    alerts.log("push", "ok", _sample(code=2, overdue=late, fingerprint=other), now)
    rows = _alerts_lines()
    assert [(r["code"], r["fingerprint"]) for r in rows] == [(3, ""), (4, ""), (0, FP), (2, other)], rows
    assert all(set(r) == {"utc", "channel", "result", *rules._SUMMARY_KEYS} for r in rows), rows
    assert owner._first_recorded() == (FP, "2026-10-23T00:00:00Z"), owner._first_recorded()
    owed = alerts.due(_sample(code=3, fingerprint=other), rows, date(2026, 10, 24))
    assert owed == [{"kind": "key_changed", "since": "2026-10-23"}, {"kind": "state"}], owed


def test_log_refuses_bad_input_and_writes_nothing():
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
```

- [ ] **Step 2: Run to verify it fails**

  Run from the repo root in Git Bash (the Bash tool), behind the QUANTGEN overlap check. The prefix prints nothing
  and runs the command only when no python `run_all` is running; if the line exits 1 with no output, a run is in
  progress: wait, then run it again.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected: one FAIL line (its traceback printed above it, on stderr) and the count; the other 35 pass, Task 2's
  rewritten `test_render_has_no_rule_free_text` included. The FAIL line and the last line (35 PASS lines are printed
  too):

```text
FAIL compliance_cli/test_log_records_a_fingerprint_only_from_codes_0_to_2 AssertionError: ['SHA256:0000000000000000000000000000000000000000000000000000000000000000', 'SHA256:0000000000000000000000000000000000000000000000000000000000000000']

35/36 passed, 1 failed, 0 not run
```

  A `NOT_RUN ... PENDING: cryptography not installed` line means the venv lost `cryptography`; stop and report.

- [ ] **Step 3: Implement**

**Edit 2 of 2** — `core/compliance/alerts.py`, anchor: `log()` (from its `def` line to the `_in_log` check and its
raise, alerts.py:242-256). The docstring gains the R6 sentence; two lines go between the row build and the `_in_log`
check. The lock, the `checked_target` open and the write below stay as they are.

Old text (exact):
```python
def log(channel: str, result: str, summary: dict, now: datetime) -> None:
    """Append one alerts.jsonl row, canonical JSON {utc, channel, result, code, due, overdue, head_seq,
    head_sha256, fingerprint}. Its head is an owner-log anchor (spec 6.4) and the first fingerprint recorded is the
    one the key is held to (P20). ValueError before anything is written for an unknown channel or result, a
    malformed summary, a naive `now`, or a head that is not that line of owner.jsonl (append-only, so the check
    holds under the lock too). The append takes the owner-log sidecar lock: a torn line would be BROKEN for good."""
    from core.compliance import owner
    if channel not in _CHANNELS or result not in _RESULTS:
        raise ValueError(f"log: channel must be one of {_CHANNELS} and result one of {_RESULTS}")
    if not _valid_summary(summary):
        raise ValueError("log: not a --check summary")
    row = {"utc": model.iso_utc(now), "channel": channel, "result": result,
           **{k: summary[k] for k in rules._SUMMARY_KEYS}}
    if not _in_log(summary["head_seq"], summary["head_sha256"]):
        raise ValueError(f"log: owner log entry #{summary['head_seq']} does not have that row_sha256")
```

New text:
```python
def log(channel: str, result: str, summary: dict, now: datetime) -> None:
    """Append one alerts.jsonl row, canonical JSON {utc, channel, result, code, due, overdue, head_seq,
    head_sha256, fingerprint}. Its head is an owner-log anchor (spec 6.4) and the first fingerprint recorded is the
    one the key is held to (P20), so a row keeps the summary's fingerprint only when its code is 0, 1 or 2; a code 3
    or 4 summary (a broken log, KEY CHANGED, a failed check) can come from a key the log does not verify, and its
    row records an empty fingerprint. ValueError before anything is written for an unknown channel or result, a
    malformed summary, a naive `now`, or a head that is not that line of owner.jsonl (append-only, so the check
    holds under the lock too). The append takes the owner-log sidecar lock: a torn line would be BROKEN for good."""
    from core.compliance import owner
    if channel not in _CHANNELS or result not in _RESULTS:
        raise ValueError(f"log: channel must be one of {_CHANNELS} and result one of {_RESULTS}")
    if not _valid_summary(summary):
        raise ValueError("log: not a --check summary")
    row = {"utc": model.iso_utc(now), "channel": channel, "result": result,
           **{k: summary[k] for k in rules._SUMMARY_KEYS}}
    if summary["code"] > 2:                     # R6: a code 3 or 4 summary may name a key the log does not verify
        row["fingerprint"] = ""
    if not _in_log(summary["head_seq"], summary["head_sha256"]):
        raise ValueError(f"log: owner log entry #{summary['head_seq']} does not have that row_sha256")
```

  Notes:
  - `summary["code"]` is an int from 0 to 4 here: `_valid_summary` has already accepted the summary (alerts.py:88).
  - The new lines pass every guard of the compliance plan: no wall-clock call, no network or dynamic import, no
    `.post/.put/.delete/.patch/.request`, none of the banned strings; the longest new line is 116 characters.
  - Dry run (2026-10-24, sandbox copies of both files with Edits 1-2 applied to the tree at `5816d3c`, each test in
    a temp TRADEGEN_HOME): each quoted old text occurs exactly once; the new test fails before Edit 2 with exactly
    the Step 2 line and passes after it; with the new `log()` the eight other compliance_cli tests that reach
    `alerts.log` or `alerts.main` without a signed home pass (`test_log_rows_carry_anchor_and_fingerprint`,
    `test_log_refuses_bad_input_and_writes_nothing`, the six `test_alerts_main_*`/`test_alerts_runs_as_main_module`
    tests). The three that build a signed home (`test_check_code_0_and_alert_rows_are_accepted`,
    `test_check_code_3_key_changed`, `test_render_has_no_rule_free_text`) log only code 0 or 1 summaries, which R6
    leaves as they are; Step 4's module run covers them.

- [ ] **Step 4: Run to verify it passes**

  Each command behind the overlap check, from the repo root in Git Bash:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected last line: `36/36 passed, 0 failed, 0 not run`.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Expected last line: `16/16 passed, 0 failed, 0 not run` (alerts.py is scanned by the import, clock, verb and
  banned-string guards).

  The suite line: every `--suite` run first imports all ten suites (run_all.py:41-50), and the compliance tests alone
  took 64 s in the 2026-10-24 record, so give this line `timeout: 300000`; never start a second run meanwhile.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: `324/326 passed, 0 failed, 2 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json`
  then `exit 0`. If it prints only `exit 1` and no test lines, the overlap check found a run_all in progress (the
  checkout was a harmless no-op): wait, then run the line again. The two NOT_RUN lines are the `REFDATA: symlink creation needs Developer Mode` tests
  (`compliance_isolation/test_symlinks_are_refused`, `compliance_tables/test_calendar_sha256_refuses_a_file_symlink`);
  with Developer Mode on it ends `326/326 passed, 0 failed, 0 not run`. The run's numbers win over these if an earlier
  task's count differed; what must hold is `0 failed`. Then:

```bash
git status --short
```

  Expected exactly:

```text
 M core/compliance/alerts.py
 M tests/compliance_cli.py
```

  plus, if the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

  Both files must stay LF. This prints `[0, 0]`:

```bash
.venv/Scripts/python.exe -I -c "print([open(p, 'rb').read().count(b'\r\n') for p in ('core/compliance/alerts.py', 'tests/compliance_cli.py')])"
```

  Then:

```bash
git add core/compliance/alerts.py tests/compliance_cli.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -m "fix(alerts): record a key fingerprint only from a check that verified the log" -m "log() writes an empty fingerprint for a code 3 or 4 summary, so the first recorded fingerprint the key is held to comes from exit 0, 1 or 2 (R6, P20; ledger:219)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  The two `--stat` outputs must be identical (2 files changed). alerts.py is a D14 closure file, so the code hash on
  disk moves; no `code_approved` exists yet (owner act 2 signs once, after the odds plan lands).

### Task 7: Data-layer A0 minors: the KIS token target is checked before the POST, the ficc memory cache after the check

**Files:**
- Modify: `data/krx/kis_client.py` (anchor: `KISClient.token`, the cache-miss branch inside `with _TOKEN_LOCK:`,
  kis_client.py:172-176; LF)
- Modify: `core/ficc/data.py` (anchor: `_cache_put`, data.py:269-279; LF)
- Modify: `tests/compliance_isolation.py` (anchors: the end of `test_kis_token_writer_refuses_a_hard_linked_target`,
  :247-258, where the new test goes in before `test_opendart_cache_writer_refuses_a_hard_linked_target`; and the
  `try` block of `test_ficc_cache_writer_refuses_a_hard_linked_target`, :295-306; LF)
- Test: `tests/compliance_isolation.py`

**Interfaces:**
- Consumes:
  - `core.isolation.checked_target(path, what: str = "path", *, within=None) -> Path`. It raises `RuntimeError`
    (`"<what> <path> is a hard link; writing it would change another file (A0)"` for a second name) and creates
    nothing (core/isolation.py:40-56).
  - `data.krx.kis_client`:
    - the module globals `_TOKEN_PATH` (kis_client.py:53), `_once` (the one-attempt `requests` module, :39) and
      `_TOKEN_LOCK` (:54);
    - `KISError(RuntimeError)` (:45);
    - `KISClient.token() -> str` (:169-196), `KISClient._cached_token()` (:146-155) and
      `KISClient._store_token(token, expires_in)` (:157-167, keeps its own `checked_target` at :158).
  - `config.kis_credentials() -> tuple[str, str]` (config.py:180). kis_client calls it through the module attribute,
    so patching `config.kis_credentials` reaches it: the T-RO-02 recorder of tests/macro_m1_pit.py:1067-1072.
  - `core.ficc.data._MEM: dict[str, tuple[float, Rows]]` (data.py:217) and `core.ficc.data._cache_put(key, rows)`
    (:269-279).
  - In `tests/compliance_isolation.py`: `VICTIM` (:23), `_fake_quantgen()` (:26-39), `_hard_linked(state, link)`
    (:58-64), `_refused(call, needle)` (:67-74) and `import config` (:18).
- Produces:
  - one new test, `tests/compliance_isolation.py::test_kis_token_is_refused_before_the_token_request`;
  - no new product name. `KISClient.token()` now raises the `checked_target` refusal on a cache miss before it reads
    a credential or builds the token request. Its one production caller, `_get`, still reads the credentials at
    kis_client.py:207 before it calls `token()` at :209; that read sends nothing, so no issuance is burnt.
    `_cache_put` now raises that refusal before it sets `_MEM[key]`.

**Plan decisions used:** R8, R12; R13 and the DRIFT RULE (Global Constraints).

What this task changes, and what it leaves alone:
- **The D14 closure.** Neither product file is in the closure: `core/__init__.py`, `core/isolation.py`,
  `core/compliance/*.py`, `core/odds/*.py` and their in-repo imports (owner.py:773). So the code hash does not move
  and no table changes.
- **The execution carry list.** R8 takes "KIS token burnt on refusal" off it (ledger:239). The executor writes that
  in the execution ledger when this task lands.
- **R12.** `_store_token` keeps its own `checked_target` (kis_client.py:158), which still guards a direct call. The
  existing `test_kis_token_writer_refuses_a_hard_linked_target` keeps proving it. The new check in `token()` is one
  line.
- **The tests' controls.** Each new refusal assertion has a positive control in the same test, so it cannot pass
  vacuously after the fix. The KIS test then points `_TOKEN_PATH` at a clean target and wants the recorder to see
  the credential read and the POST. The ficc test then puts a clean key and wants it in `_MEM`.
- **Other suites.** No test outside this file calls the real `KISClient.token()` except cockpit/test_21
  (tests/acceptance.py:318). It reaches `token()` through `KRXGateway.daily` -> `KISClient.daily` -> `_get`
  (data/krx/gateway.py:90-98, kis_client.py:209), and only when KIS keys are set.
  - There, a clean target passes the new check. A refusal is the same `RuntimeError` that `_store_token` raised
    before, and the gateway's `except Exception` (gateway.py:97) still turns it into a failed answer.
  - The cockpit's read-only scans (test_08, test_09) run directly in Step 4. Step 4 does not add `--suite cockpit`:
    with KIS keys set, test_21 sends real KIS requests, the token POST to `/oauth2/tokenP` on a cache miss
    (kis_client.py:181) and the read-only daily-chart quotation GET (`KISClient.daily`, kis_client.py:273-281).
    The rest of the cockpit suite, test_21 included, runs once, in Task 8 Step 2's full run. There, when KIS keys
    are set, test_21 makes that read-only KIS quotation call, as every earlier full run did; the controller accepts
    this, and no key check is added. This task makes no KIS call.
  - engine test_89 replaces `client.token` (tests/engine_acceptance.py:1376).
  - T-RO-02 refuses in `_get` before any token (tests/macro_m1_pit.py:1073).
  - `_cache_put` changes only when `checked_target` refuses, and then it raises as before.
  - The engine, macro, expansion, ficc and quant suites still run in Step 4, because they load these modules.
- **Left as it is.**
  - `_cached_token()` still reads the token file before the check. A0 checks writes ("every writer ... checks its
    final target", spec 4 "Isolation residual"). A link present at the process's first `state_root()` scan of that
    root is refused by the link scan (kis_client.py:53 calls `config.state_root()` at import; the scan is memoised
    per root, refusals included, `scan_links` at core/isolation.py:99-102). A link created after that scan is read
    by `_cached_token()` unchecked, and a valid token in it is used. That is a read and no write, so it is outside
    A0 and R8. The controller rules that this token read path is left as is (a stated limit in the plan header's
    "Spec" list).
  - The `core/ficc/data.py` module docstring ("Cache failures are ignored, never raised") predates A0. It is not
    rewritten here.
- **Drift.** No earlier task of this plan touches these three files. Under the DRIFT RULE, re-read each file before
  its Edit anyway.

- [ ] **Step 1: Write the failing tests**

  Re-read `tests/compliance_isolation.py`. Then make two Edit-tool replacements. Keep LF.

  Edit 1. The anchor is the end of `test_kis_token_writer_refuses_a_hard_linked_target` and the `def` line of
  `test_opendart_cache_writer_refuses_a_hard_linked_target` (tests/compliance_isolation.py:255-261). The new test
  goes in between them. Old text (exact):

```python
            _refused(lambda: object.__new__(kis_client.KISClient)._store_token("t", 60.0), "hard link")
        finally:
            kis_client._TOKEN_PATH = keep
        assert victim.read_bytes() == VICTIM


def test_opendart_cache_writer_refuses_a_hard_linked_target():
```

  New text:

```python
            _refused(lambda: object.__new__(kis_client.KISClient)._store_token("t", 60.0), "hard link")
        finally:
            kis_client._TOKEN_PATH = keep
        assert victim.read_bytes() == VICTIM


def test_kis_token_is_refused_before_the_token_request():
    """R8 (ledger:81): on a cache miss token() checks the cache target before it reads a credential or sends the
    token request, so a refused target burns no token issuance (KIS rate-limits issuance hard). _store_token keeps
    its own check for a direct call (R12, the test above)."""
    from data.krx import kis_client
    calls = []

    class _Once:                                        # stands in for requests: records the POST, then fails
        @staticmethod
        def post(url, **_kw):
            calls.append(f"POST {url}")
            raise ConnectionError("the token request was sent")

    with _fake_quantgen() as (state, _repo, scratch):
        target = scratch / "kis_token.json"
        victim = _hard_linked(state, target)            # VICTIM is not a token, so the cache misses
        keep = (kis_client._TOKEN_PATH, kis_client._once, config.kis_credentials)
        try:
            kis_client._TOKEN_PATH, kis_client._once = target, _Once
            config.kis_credentials = lambda: calls.append("credentials") or ("k", "s")   # the T-RO-02 recorder
            client = object.__new__(kis_client.KISClient)
            client.ready, client.base_url, client.timeout_s = True, "https://example.invalid", 1.0
            _refused(client.token, "hard link")
            assert calls == [], calls                   # no credential read, no token request
            kis_client._TOKEN_PATH = scratch / "clean" / "kis_token.json"   # control: a clean target reaches the POST
            _refused(client.token, "token request failed: ConnectionError")
            assert calls == ["credentials", "POST https://example.invalid/oauth2/tokenP"], calls
        finally:
            kis_client._TOKEN_PATH, kis_client._once, config.kis_credentials = keep
        assert victim.read_bytes() == VICTIM


def test_opendart_cache_writer_refuses_a_hard_linked_target():
```

  The control's `KISError` is a `RuntimeError`, so `_refused` catches it. The clean target's directory does not
  exist, so `_cached_token()` misses and `checked_target` passes it without creating anything.

  Edit 2. The anchor is the `try` block of `test_ficc_cache_writer_refuses_a_hard_linked_target`
  (tests/compliance_isolation.py:302-305). The `finally` that pops the key stays, and pops the control key too. The
  control writes `A0_PROBE_2.json` into the fake scratch directory, which `_fake_quantgen()` removes. Old text
  (exact):

```python
            _refused(lambda: D._cache_put("A0_PROBE_1", [("2026-10-22", 1.0)]), "hard link")
        finally:
            config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir = keep
            D._MEM.pop("A0_PROBE_1", None)
```

  New text:

```python
            _refused(lambda: D._cache_put("A0_PROBE_1", [("2026-10-22", 1.0)]), "hard link")
            assert "A0_PROBE_1" not in D._MEM, "a refused key was cached in memory"
            D._cache_put("A0_PROBE_2", [("2026-10-22", 1.0)])                # control: a clean key is cached
            assert "A0_PROBE_2" in D._MEM, "a clean key was not cached in memory"
        finally:
            config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir = keep
            D._MEM.pop("A0_PROBE_1", None)
            D._MEM.pop("A0_PROBE_2", None)
```

- [ ] **Step 2: Run to verify it fails**

  First run the overlap check with the PowerShell tool. It must print nothing; if it prints a process, wait and run
  it again.

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_isolation/
```

  Expected: two tracebacks, these three lines among the 17 result lines, and then the summary. Exit code 1.

```text
FAIL compliance_isolation/test_ficc_cache_writer_refuses_a_hard_linked_target AssertionError: a refused key was cached in memory
FAIL compliance_isolation/test_kis_token_is_refused_before_the_token_request AssertionError: token request failed: ConnectionError
NOT_RUN compliance_isolation/test_symlinks_are_refused REFDATA: symlink creation needs Developer Mode

14/17 passed, 2 failed, 1 not run
```

  Why each one fails today:
  - **The KIS token test.** `token()` reads the credentials and calls `_once.post` before any check. The recorder
    raises, and `token()` turns that into `KISError("token request failed: ConnectionError")` (kis_client.py:187-188).
    The first `_refused` wants "hard link", so it raises an AssertionError with that message. The control is not
    reached.
  - **The ficc test.** `_cache_put` sets `_MEM["A0_PROBE_1"]` at data.py:273, before the refusal at :274. The control
    is not reached.

  If the KIS line instead names `HermeticViolation`, the `_once` patch did not take effect: re-check Edit 1.

- [ ] **Step 3: Implement**

  Edit 3: `data/krx/kis_client.py` (LF). Re-read the file. The anchor is the cache-miss branch inside
  `with _TOKEN_LOCK:` in `KISClient.token` (kis_client.py:172-176). The new line goes after `return cached` and
  before `config.kis_credentials()`. The same `app_key, app_secret = config.kis_credentials()` line also occurs in
  `_get` (:207), so the old text includes the lines above it to stay unique. `_store_token` is not touched. Old text
  (exact):

```python
        with _TOKEN_LOCK:
            cached = self._cached_token()
            if cached:
                return cached
            app_key, app_secret = config.kis_credentials()
```

  New text:

```python
        with _TOKEN_LOCK:
            cached = self._cached_token()
            if cached:
                return cached
            checked_target(_TOKEN_PATH, "KIS token cache")      # A0: refuse before the POST burns an issuance (R8)
            app_key, app_secret = config.kis_credentials()
```

  `checked_target` is already imported (kis_client.py:36).

  Edit 4: `core/ficc/data.py` (LF). Re-read the file. The anchor is the body of `_cache_put` (data.py:272-274).
  `_MEM[key] = (now, rows)` and the `checked_target` line swap places, and the moved line gets the R8 comment.
  `_cache_get`'s own `_MEM[key] = (ts, rows)` (:264) is not touched. Old text (exact):

```python
    now = time.time()
    _MEM[key] = (now, rows)
    target = checked_target(config.ficc_cache_dir() / f"{key}.json", "FICC cache")   # A0: a refusal propagates
```

  New text:

```python
    now = time.time()
    target = checked_target(config.ficc_cache_dir() / f"{key}.json", "FICC cache")   # A0: a refusal propagates
    _MEM[key] = (now, rows)   # after the check: a refused key is never served from memory (R8)
```

  Then check the line endings. Expected: each line reads `i/lf    w/lf    attr/-text`.

```bash
git ls-files --eol data/krx/kis_client.py core/ficc/data.py tests/compliance_isolation.py
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 before EACH command below that starts Python. All run from the repo root in Git
  Bash. In Git Bash the overlap check can also be a prefix. The PowerShell script is in single quotes, so Bash leaves
  `$_` alone:
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`.

  Overlap check, then the module:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_isolation/
```

  Expected:
  - 16 `PASS compliance_isolation/test_...` lines;
  - `NOT_RUN compliance_isolation/test_symlinks_are_refused REFDATA: symlink creation needs Developer Mode`;
  - then `16/17 passed, 0 failed, 1 not run`, and exit code 0.
  - With Developer Mode on, `17/17 passed, 0 failed, 0 not run`.

  Overlap check, then the repo-wide read-only guards: T-RO-01 on code with docstrings and comments stripped
  (`_code_only`, tests/macro_m0_harness.py:78), and cockpit test_08 and test_09 on raw text. `runtime_py()` scans
  core, data, ui, main.py and config.py. This calls the three test functions directly, does not start
  `tests/run_all.py`, and writes nothing. The raw-text checks over every file of `core/` (tests/compliance_guards.py)
  run in the compliance suite below.

```bash
.venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as ro; from tests.acceptance import test_08_no_broker_order_path as t8, test_09_no_account_credentials_requested as t9; ro(); t8(); t9(); print('guards ok')"
```

  Expected: `guards ok` (exit code 0).

  Then the compliance suite, and the five suites below that load these modules, one at a time. The cockpit suite also
  loads kis_client; it is left to Task 8 Step 2's full run, because its test_21 calls KIS when keys are set ("Other
  suites" above). Before each line, run the overlap check.
  Each line restores the tracked, CRLF `qa/acceptance_results.json` after its run.
  - Engine: test_89 stubs `client.token`; test_81 checks `kis._once`.
  - Macro: T-RO-02 re-runs kis_client from its source, and macro_m0_rules reads its state paths.
  - Expansion: fake KIS transports.
  - Ficc and quant: the FICC cache.

  If a line prints `exit 1` and no test lines, the prefixed overlap check found a running `run_all.py`: wait, then
  run that line again.

  Timeouts. Every `--suite` run imports all ten suites before it runs its own. In the 2026-10-24 record the tests
  took 64 s for compliance, 56 s for expansion, 56 s for quant and 416 s (about 7 minutes) for macro, against the
  Bash tool's 120 s default. So give each `--suite` line `timeout: 300000`, and the macro line `timeout: 600000` or
  start it with `run_in_background` and wait for its notification. Never start a second run in the meantime.

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite engine; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite macro; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite expansion; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite ficc; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite quant; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: every run reports `0 failed` and prints `exit 0`. Each summary line ends with
  `; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json`. The counts come from Tasks 1-7 for
  compliance and from README.md:831-836 for the other suites; when `0 failed` holds, the run's own numbers win:
  - compliance: `325/327 passed, 0 failed, 2 not run`. The 2 not run are the two REFDATA symlink tests,
    `compliance_isolation/test_symlinks_are_refused` and `compliance_tables/test_calendar_sha256_refuses_a_file_symlink`.
  - engine: `92/92 passed, 0 failed, 0 not run`
  - macro: `419/540 passed, 0 failed, 121 not run`
  - expansion: `19/19 passed, 0 failed, 0 not run`
  - ficc: `56/56 passed, 0 failed, 0 not run`
  - quant: `53/53 passed, 0 failed, 0 not run`

  After the last line:

```bash
git status --short
```

  Expected exactly:

```text
 M core/ficc/data.py
 M data/krx/kis_client.py
 M tests/compliance_isolation.py
```

  plus, if the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add data/krx/kis_client.py core/ficc/data.py tests/compliance_isolation.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical. All three files are LF. Expected:

```text
 core/ficc/data.py             |  2 +-
 data/krx/kis_client.py        |  1 +
 tests/compliance_isolation.py | 36 ++++++++++++++++++++++++++++++++++++
 3 files changed, 38 insertions(+), 1 deletion(-)
```

  Then:

```bash
git commit -m "fix(isolation): check the KIS token and ficc cache targets before side effects" -m "Task 7 (R8, R12): token() refuses a bad cache target before it reads a credential or sends the token POST; _cache_put sets _MEM only after checked_target." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Then add a line to the execution ledger (`docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`,
  which the executor keeps): "KIS token burnt on refusal" (ledger:239) is closed by Task 7 (R8) and leaves the
  execution carry list.

### Task 8: Full run, README counts, the real-home check, the final review and the hand-off

**Files:**
- Modify: `README.md`. Anchors: the last cell of the `| compliance |` row of the suite table (README.md:839) and the
  last cell of the `| **Total** |` row (README.md:840); a contingency names the other nine rows (Step 4). The file is
  CRLF; use the Edit tool only.
- Modify: `qa/acceptance_results.json` (CRLF). The full run of Step 2 writes it, and only this task commits it: once
  in Step 5, and once more if the final review leads to fixes (Step 7).
- Commit: `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` (LF). The executor writes it
  during and after execution; this plan never writes its content. Step 8 commits it before the merge.
- Test: no new test. The full run is the check.

**Interfaces:**
- Consumes:
  - Tasks 1 to 7, each committed on `compliance-followup`.
  - `tests/run_all.py`. With no argument it runs every suite, writes `qa/acceptance_results.json` (rows of
    `{"test": "<group>/...", "status": "PASS" | "FAIL" | "NOT_RUN", ...}`) even when a test fails, and ends with
    `<passed>/<total> passed, <failed> failed, <not run> not run; <path of qa/acceptance_results.json>`
    (tests/run_all.py:92-123).
  - `tests.compliance_acceptance._real_listing() -> tuple`: the (relative path, size, mtime_ns) rows of the real
    `~/.tradegen/compliance`, and `()` when it does not exist (tests/compliance_acceptance.py:31-40). It always reads
    `Path.home() / ".tradegen" / "compliance"` (tests/compliance_acceptance.py:28), whatever `TRADEGEN_HOME` says.
  - `python -m core.compliance.rules --check` (rules.py:931-967). It uses `TRADEGEN_HOME` when that is set, else
    `~/.tradegen` (core/isolation.py:108). While `core/compliance/owner_pubkey.pem` is absent (owner.py:24), the owner
    log is BROKEN "no owner key yet: owner act 1" (owner.py:929), so the check exits 3 and writes nothing.
  - `load_context` needs an approval of all three tables, rules, instruments and venues (owner.py:602 `_TABLES`,
    owner.py:947-961 `_approved_now`).
- Produces:
  - the README compliance and Total counts;
  - the committed full-run record (`test: full run after the compliance follow-up`, and after a fix wave
    `test: full run after the final review wave`);
  - the committed execution ledger (`docs(plan): execution ledger of the compliance follow-up`);
  - the merge, after which the odds plan starts from the merged main (R13);
  - the owner-act hand-off.

**Plan decisions used:**
- R13 (the order of the plans) and the DRIFT RULE;
- R3 (the table sha the owner approves at owner act 3);
- R2, R4 and R6 (the closure changes the owner signs at owner act 2, after the odds plan), and R4's stated limit
  (R2-12), which rests on the owner's review of the hashed files;
- R4, R5 and R11 (the signer copy, owner act 1, and the owner's Windows Terminal, which runs PowerShell).

**Expected counts.**
- Compliance: 327 rows, 325 PASS / 2 NOT_RUN. That is 317 + 10 new tests:
  - Task 1: 1 (guards);
  - Task 2: 6 (5 loader tests and the pin test);
  - Task 4: 1 (source equality);
  - Task 6: 1 (fingerprint);
  - Task 7: 1 (KIS token).
- Full run: 1176 rows, 1053 PASS / 123 NOT_RUN, against 1043/1166 at README.md:840.
- Every other group keeps its README.md:830-838 count.
- A review fix inside a task, or a fix task after the final review, adds its own tests on top. The numbers the run
  prints win over these as long as nothing fails.

**Drift.** No earlier task of this plan edits README.md, and the odds and E1 plans are docs-only commits on main
until this plan merges. Re-read README.md before each Edit anyway (DRIFT RULE).

**The QUANTGEN overlap check.** Run it before every test command and every command that imports repo code: Steps 1,
2 and 6 put it in front. It must print nothing; otherwise wait. The stdlib-only one-liners of Steps 1, 2 and 4 read
a pipe or a file and import no repo code, so they need no check.
- PowerShell tool:
  `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`
- Git Bash prefix (the PowerShell script is in single quotes, so Bash leaves `$_` alone):
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`

- [ ] **Step 1: Check the branch, the commits and the compliance suite**

  From the repo root in Git Bash:

```bash
git branch --show-current
git status --short
git log --format=%s --reverse main..compliance-followup | .venv/Scripts/python.exe -I -c "
import sys
for stream in (sys.stdin, sys.stdout):
    stream.reconfigure(encoding='utf-8', errors='replace')
want = [
    'test(guards): ban xml.dom, string-exec modules and bare compile; read the suite lists',
    'fix(compliance): loader refuses D15/D16 content, bounds review_by, max_leverage and {cap}; pin rows',
    'fix(tables): KR-KIS-KRX-DERIV reason names broker approval',
    'fix(compliance): closure scan skips a guard only while its name is unbound and unmutated',
    'fix(signer): the ancestor walk refuses when the chain breaks before a session process',
    'fix(alerts): record a key fingerprint only from a check that verified the log',
    'fix(isolation): check the KIS token and ficc cache targets before side effects',
]
done = 0
for subject in sys.stdin.read().splitlines():
    if done < len(want) and subject == want[done]:
        done += 1
        print('task', done, subject)
    else:
        print('other after task', done, subject)
print('missing:', want[done] if done < len(want) else 'none')
"
```

  Expected:
  - `git branch --show-current` prints `compliance-followup`. If it prints anything else, run
    `git switch compliance-followup` and start this step again.
  - `git status --short` prints nothing. The one exception is the executor's ledger while it is not committed yet:
    `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`.
  - The log check prints the seven task subjects in task order, as `task 1 ...` to `task 7 ...`, and ends with
    `missing: none`.
  - Other commits are allowed, each printed as `other after task <n> <subject>`:
    - a review fix of task `<n>`, made during subagent-driven execution;
    - on a repeat of this step (Step 7), after task 7: the Step 5 record commit
      `test: full run after the compliance follow-up` and the fix commits of the final review.

    Each must have a ledger line that names it. If one has none, write that line from the commit itself
    (`git show --stat <hash>`).

  Stop and report when:
  - `missing:` names a subject: that task is not committed, so finish it first;
  - the tree is dirty beyond the ledger line;
  - a line reads `other after task 0`;
  - an `other` commit is none of the kinds above.

  Then run the compliance suite with the overlap check in front, with the Bash tool's `timeout: 600000`; never start
  a second run meanwhile. The suite's tests took 63.6 s in the 2026-10-24 record, and the guards' registration test
  (`test_suite_is_registered_in_run_all_and_readme`, tests/compliance_guards.py:485) imports `tests.run_all`, which
  imports every suite (tests/run_all.py:41-50). This command's entry point `_main` imports it too, before any test
  runs (tests/compliance_acceptance.py:79).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance; echo "exit $?"
```

  Expected:
  - every test line is `PASS`, except these two NOT_RUN lines:

```text
NOT_RUN compliance_isolation/test_symlinks_are_refused REFDATA: symlink creation needs Developer Mode
NOT_RUN compliance_tables/test_calendar_sha256_refuses_a_file_symlink REFDATA: symlink creation needs Developer Mode
```

  - then these two lines:

```text
325/327 passed, 0 failed, 2 not run
exit 0
```

  - With Developer Mode on, `327/327 passed, 0 failed, 0 not run` and `exit 0`.
  - On a repeat after a fix wave, the totals grow by the fix tasks' tests, and each of those tests has a ledger line.

  If the output is `exit 1` alone, the overlap check found another `run_all.py`: wait and run the line again. A
  `NOT_RUN ... PENDING` line means a dependency is missing; stop and report it. For a FAIL that names the real
  `~/.tradegen/compliance`, see the ledger:67 bullet in Step 2.

- [ ] **Step 2: Run the full suite with the overlap guard**

  The full run takes about 11 minutes: its tests took 609 s in the 2026-10-24 record. That is longer than the Bash
  tool's 10-minute limit, so start this command with `run_in_background` and wait for its notification. Do not poll
  it, and do not start any other run meanwhile.

  The run includes cockpit test_21 (tests/acceptance.py:318). When KIS keys are set, it makes the quote-only calls
  that every earlier full run made: through `KRXGateway().daily` a KIS token request on a cache miss (cached in
  TRADEGEN's own `~/.tradegen/kis_token.json`, kis_client.py:53) and a daily-price GET, and through `.filings` an
  OpenDART GET when that key is set. They are read-only quotation calls: none places an order or reads an account.
  The controller accepts them here, once per full run, and no key check is added; Task 7 keeps them out of its
  per-suite runs.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe tests/run_all.py; echo "exit $?"; date +%F
```

  Expected, at the end of the output:

```text
1053/1176 passed, 0 failed, 123 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json
exit 0
```

  A third line follows: the date of the run as `date +%F` prints it. Step 4 writes that date into the Total row.

  If the line reads `exit 1` with no test output, the overlap check found another `run_all.py`: wait and start the
  line again.

  If any test fails, or the run is cut short, stop. `tests/run_all.py` writes the record even when tests fail
  (tests/run_all.py:118), so restore it before anything else:

```bash
git checkout -- qa/acceptance_results.json
```

  Then find the task whose change broke the test and fix it there with its own failing test; never edit a guard to
  make it pass. The likely suspects:
  - **Guards and isolation.** compliance_guards (Task 1's lists over core/compliance), T-CTX-01's isolation report,
    cockpit test_08 and test_09, and T-RO-01.
  - **The kis_client source.** T-RO-02, which re-runs kis_client from its source (Task 7).
  - **The suite lists.** The R7 check (Task 1) reads the `one suite:` lists at tests/run_all.py:113 and
    README.md:816. This plan edits neither list; the odds plan adds `odds` to both.
  - **Not a task bug: ledger:67.** Suppose a compliance FAIL's detail reads
    `the test touched the real ~/.tradegen/compliance: [('alerts.jsonl', ...` and the run spanned 09:00 KST. Then
    the daily alert job `tradegen-compliance-daily` appended a row during the run: ledger:67, a deferred minor.
    Restore the record, write one ledger line, and run Step 2 again outside that time.

  When the run is green, count each group's statuses in the record (read-only):

```bash
.venv/Scripts/python.exe -c "import json, collections; rows = json.load(open('qa/acceptance_results.json', encoding='utf-8')); print(*sorted(collections.Counter((r['test'].split('/', 1)[0], r['status']) for r in rows).items()), sep='\n'); print(len(rows))"
```

  Expected (no `FAIL` entry):

```text
(('cockpit', 'PASS'), 47)
(('compliance', 'NOT_RUN'), 2)
(('compliance', 'PASS'), 325)
(('engine', 'PASS'), 92)
(('expansion', 'PASS'), 19)
(('ficc', 'PASS'), 56)
(('grokteam', 'PASS'), 17)
(('macro', 'NOT_RUN'), 121)
(('macro', 'PASS'), 419)
(('paper', 'PASS'), 21)
(('quant', 'PASS'), 53)
(('ui', 'PASS'), 4)
1176
```

  Only the compliance row changes from the 2026-10-24 record (315 to 325 PASS). If another group's counts differ
  from its README.md:830-838 row, the run wins:
  - give that row's last cell the run's counts in Step 4 (its old text is listed there);
  - write one ledger line naming the group and the reason (for example, a REFDATA test that now runs).

- [ ] **Step 3: Confirm that only the record changed**

```bash
git status --short
git diff --stat
git diff --stat --ignore-cr-at-eol
git ls-files --eol qa/acceptance_results.json
```

  Expected:
  - the only line of `git status --short` is ` M qa/acceptance_results.json`, apart from the untracked ledger line
    allowed in Step 1;
  - the two `--stat` outputs are identical;
  - the eol line reads `i/crlf  w/crlf  attr/-text`, because the run rewrites the file in text mode and keeps CRLF.

  If another tracked file changed, or an untracked file appeared, stop: a test wrote into the repo.

- [ ] **Step 4: Update the README counts (CRLF, Edit tool)**

  Re-read `README.md` (DRIFT RULE), then make the Edit-tool replacements below. Each old text lies inside one line and
  stops before the line end, so every CRLF ending stays as it is.

  Edit 1. The anchor is the last cell of the `| compliance |` row (README.md:839). Old text (exact, it occurs once):

```text
final-target checks) | 315 PASS / 2 NOT_RUN |
```

  New text, with the compliance counts of Step 2 (expected 325 PASS / 2 NOT_RUN):

```text
final-target checks) | 325 PASS / 2 NOT_RUN |
```

  Edit 2. The anchor is the `| **Total** |` row (README.md:840). Old text (exact, it occurs once):

```text
| **Total** | `tests/run_all.py` | | 1043/1166 passed, 0 failed, 123 not run (2026-10-24, TRADEGEN `.venv`) |
```

  New text. Fill the slots from Step 2: the counts from its summary line and the date that `date +%F` printed:

```text
| **Total** | `tests/run_all.py` | | <passed>/<total> passed, 0 failed, <not run> not run (<date from Step 2>, TRADEGEN `.venv`) |
```

  The expected result is
  `| **Total** | `tests/run_all.py` | | 1053/1176 passed, 0 failed, 123 not run (<date from Step 2>, TRADEGEN `.venv`) |`.
  If the date is still 2026-10-24, the date stays as it is.

  Contingency, only for a group whose Step 2 counts differ from its row. The anchor is that group's row, named by its
  first cell. The old text is its last cell, exact, and each one occurs once in README.md:
  - the `| cockpit |` row (README.md:830): `| 47 PASS |`
  - the `| engine |` row (README.md:831): `| 92 PASS |`
  - the `| ui |` row (README.md:832): `| 4 PASS |`
  - the `| quant |` row (README.md:833): `| 53 PASS |`
  - the `| ficc |` row (README.md:834): `| 56 PASS |`
  - the `| expansion |` row (README.md:835): `| 19 PASS |`
  - the `| macro |` row (README.md:836): `| 419 PASS / 121 NOT_RUN |`
  - the `| paper |` row (README.md:837): `| 21 PASS |`
  - the `| grokteam |` row (README.md:838): `| 17 PASS |`

  The new text is the run's counts in the same form: `| N PASS |`, or `| N PASS / M NOT_RUN |` when the group has
  NOT_RUN rows.

  On a repeat after a fix wave (Step 7), the old texts of Edits 1 and 2 are the two cells exactly as the first pass
  left them, re-read from README.md, and the new texts carry the repeat run's counts and date.

  Then check the endings and the diff:

```bash
.venv/Scripts/python.exe -c "b = open('README.md', 'rb').read(); print(b.count(b'\n'), b.count(b'\r\n'))"
git ls-files --eol README.md
git diff --stat README.md
git diff --stat --ignore-cr-at-eol README.md
```

  Expected:
  - `891 891`: every line still ends in CRLF;
  - `i/crlf  w/crlf  attr/-text`;
  - two identical stat outputs, ` README.md | 4 ++--` and `1 file changed, 2 insertions(+), 2 deletions(-)`;
  - two more changed lines for each contingency row.

- [ ] **Step 5: Commit the full-run record and the README**

```bash
git add README.md qa/acceptance_results.json
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical, and the ledger stays out of this commit. Then, with the numbers of Step 2
  in the body:

```bash
git commit -m "test: full run after the compliance follow-up" -m "Task 8: full run 1053/1176 passed, 0 failed, 123 not run (compliance 325 PASS / 2 NOT_RUN); README compliance and Total rows." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: The read-only check against the real home**

  This step never writes. With no owner key, `--check` writes nothing. With a key, `load_context` would write a
  snapshot under `~/.tradegen/compliance/snapshots`, so the step skips in that case. It also stops when
  `TRADEGEN_HOME` is set, because then `--check` reads another home than `_real_listing()` lists, and an unchanged
  listing would prove nothing. And it waits while a `run_all.py` runs (the overlap check). Otherwise it lists the
  real compliance home before and after.

```bash
if test -e core/compliance/owner_pubkey.pem; then echo "skip: the owner key exists"
elif test -n "${TRADEGEN_HOME:-}"; then echo "stop: TRADEGEN_HOME is set to $TRADEGEN_HOME"
elif test -n "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')"; then echo "wait: a run_all.py is running"
else
  before=$(.venv/Scripts/python.exe -c "from tests.compliance_acceptance import _real_listing; print(_real_listing())")
  .venv/Scripts/python.exe -m core.compliance.rules --check; echo "exit $?"
  after=$(.venv/Scripts/python.exe -c "from tests.compliance_acceptance import _real_listing; print(_real_listing())")
  test "$before" = "$after" && echo "real ~/.tradegen/compliance unchanged: $before"
fi
```

  If it prints `wait: a run_all.py is running`, wait and run the block again. If it prints
  `stop: TRADEGEN_HOME is set to ...`, stop and report: the shell's profile points the state somewhere else, and only
  the owner can say which home is real.

  Expected when the check ran, among the human lines:
  - `owner log: BROKEN: no owner key yet: owner act 1`
  - `owner log head: entry #0; key fingerprint none`
  - `rules: the draft 74894f05e0b7f1af is not the version in force (none); it counts only once signed`. This is
    Task 3's table: sha `74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd`.
  - `instruments: the draft 50fa819f62707eb5 is not the version in force (none); it counts only once signed`
  - `venues: the draft 603e264080f4c69b is not the version in force (none); it counts only once signed`
  - a line starting `exit 3: new exposure is blocked`

  Then exactly these three lines:

```text
{"code": 3, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": ""}
exit 3
real ~/.tradegen/compliance unchanged: ()
```

  `()` means the folder does not exist. If it exists, the tuple lists its entries, and it must print the same before
  and after. If the last line is missing, the check changed the real home: stop and report. If a fix wave (Step 7)
  changed a table, the draft lines of its repeat run win, and Step 9 hands over their shas.

  Write the result in the ledger: `ran` (with exit 3 and the listing) or `skipped: the owner key exists`. Step 9's
  owner texts depend on it.

- [ ] **Step 7: The final review, and the repeat run after a fix**

  1. Request the final review of `main..compliance-followup` (superpowers:requesting-code-review).
  2. Fix each finding the controller takes in a new task with its own failing test, under the rules of Tasks 1 to 7:
     - the DRIFT RULE;
     - the overlap check before each test command;
     - the record restored after each `--suite` run;
     - one commit per fix;
     - one ledger line per finding and per ruling.

     Then request a re-review of the fix commits, and repeat until it finds nothing to fix.
  3. If no fix commit was made, go to Step 8.
  4. After any fix commit, the record and the README rows of Step 5 are stale. Repeat Steps 1 to 6:
     - Step 1's log check also lists the Step 5 record commit and the fix commits as `other after task 7`;
     - the run's numbers win;
     - Step 4 edits the cells as the first pass left them;
     - Step 5 runs as written, but its commit uses this subject and the repeat run's numbers in the body.

     The repeat's Step 5 commit:

```bash
git commit -m "test: full run after the final review wave" -m "Task 8, after the final review: full run <passed>/<total> passed, 0 failed, <not run> not run (compliance <n> PASS / <m> NOT_RUN); README compliance and Total rows." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

     Fill the five slots from the repeat run's Step 2. If README.md did not change, `git add` only
     `qa/acceptance_results.json`, and drop "README compliance and Total rows." from the body. After the repeat's
     Step 6, go to Step 8.

- [ ] **Step 8: Commit the execution ledger**

  `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` is the executor's record. If you kept it
  outside the repo, copy it to that path first. Before the commit, check that it holds:
  - one line per task, with its commit and module counts, and one line per review fix;
  - every DRIFT RULE ruling;
  - "KIS token burnt on refusal" (ledger:239) closed by Task 7;
  - the full-run line of Step 2, and of its repeat if Step 7 made one;
  - the real-home result of Step 6;
  - the final review, each finding and ruling, and the re-review.

```bash
git add docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md
git status --short
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  Expected:
  - `git status --short` prints only
    `A  docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`;
  - the two stat outputs are identical: `1 file changed, <n> insertions(+)`.

  No test reads a `.md` file under `docs/superpowers`, so this commit leaves the record of Step 5 (or Step 7) current.

```bash
git commit -m "docs(plan): execution ledger of the compliance follow-up" -m "Every task review, fix round, DRIFT RULE ruling, the final review and the full runs of the follow-up execution, kept for the owner's audit and GPT's 2026-10-30 check." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 9: Merge, then hand off**

  1. **Merge** per superpowers:finishing-a-development-branch.
  2. **The odds plan.** Start it from the merged main (R13), under its DRIFT RULE for the files this plan changed.
     The E1 plan follows after the odds plan merges.
  3. **The owner acts.** Tell the owner these in chat. Claude does none of them, and never runs the signer with a
     real key. Pick each text by Step 6's result.

     The order of the plans matters to acts 1 and 2. The E1 plan changes `tools/signer/sign.py` and the D14 code hash
     again (its Task 9, which adds `execution/*.py` to the closure). If you do acts 1 and 2 before E1 lands, you
     re-copy the signer and sign again after it.

     - **Owner act 1, the signer copy.**
       - If Step 6 ran (no owner key), act 1 is not done. When you do it:
         - copy the merged `tools/signer/sign.py` to your folder `$env:USERPROFILE\tradegen-signer\`;
         - read it in full;
         - in Windows Terminal (PowerShell), run
           `certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256`, and write the hash on paper;
         - then finish act 1 as spec section 11 lists it.

         Tasks 4 and 5 changed the file: the closure scan, and the ancestor walk that refuses when the parent chain
         breaks before a Windows session process.
       - If Step 6 printed `skip: the owner key exists`, act 1 is done, and your copy is older than the merged file.
         Re-verify it:
         - read the diff of your copy against the merged file, in Windows Terminal (PowerShell):
           `fc.exe /n "$env:USERPROFILE\tradegen-signer\sign.py" "C:\Users\whydi\OneDrive\Desktop\TRADEGEN\tools\signer\sign.py"`;
         - copy the merged file;
         - run the same `certutil` line;
         - write the new hash on paper.
       - Either way, run the signer from Windows Terminal opened from the Start menu. The fail-closed ancestor walk
         of Task 5 refuses a VS Code integrated terminal (its parent chain stops at a launcher that has exited); the
         controller accepts this as a stated limit.
     - **Owner act 2, one code signature, after the odds plan lands.** It covers this plan's closure changes
       (`core/compliance/rules.py`, `owner.py`, `alerts.py`) and the odds plan's together.
       - Before signing, read the hashed files: every file the signing prompt lists. Today these are
         `core/__init__.py`, `core/isolation.py`, `core/compliance/*.py` and `core/odds/*.py`; E1 adds
         `execution/*.py`.
       - If no `code_approved` exists yet, this is your first signature, so read them in full; otherwise read each
         diff since the signed version.
       - R4's stated limit relies on that review: the closure scan cannot see a module that changes
         `typing.TYPE_CHECKING` for another one, or a name built at run time.
     - **Owner act 3, the three tables, after the odds plan lands and together with act 2.** `load_context` needs an
       approval of all three. Approve:
       - `core/compliance/kr_rules.yaml` as Task 3 left it, sha
         `74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd`;
       - `core/compliance/instruments.yaml`, sha
         `50fa819f62707eb58e09135355b4f84160611ef4a8ad1af7345bb119b6f1431a`, unless a later plan changes it;
       - `core/odds/venues.yaml` as the odds plan leaves it, with the fixed charges and lots its owner gate asks you
         to add. Its sha changes from today's `603e264080f4c69b...`.

       `--check`'s draft lines print the first 16 hex digits of each sha to compare.
     - **What to expect until then.**
       - If Step 6 ran: every new-exposure intent is BLOCK, and `--check` exits 3. That is the designed safe
         default, not a fault.
       - If Step 6 skipped: Claude did not run `--check` against your home, because with your key it would write a
         snapshot there. Run it yourself to see the current state.
       - From owner act 1 until a check exits 0, 1 or 2, alerts.jsonl records no key fingerprint (Task 6), and new
         exposure stays blocked throughout: the fingerprint you write on paper at act 1 is the only reference for
         your key, so keep that paper. The first fingerprint is recorded with the first alert of a check that exits
         1 or 2 (an exit-0 check sends no alert).

---

## Appendix A: the interface contract (as amended while drafting)

Repo: `C:\Users\whydi\OneDrive\Desktop\TRADEGEN` (git, tree clean, no other branch). Written against `main` at
`5816d3c`, which differs from `995534b` (the compliance merge) only by one new docs file
(`git diff --stat 995534b 5816d3c -- . ':!docs'` prints nothing, 2026-10-24). The plan executes first, from main's
HEAD after this plan, the odds plan and the E1 plan are committed there (docs only; Task 1 checks it, R13).
Spec: `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` rev 3.2. The owner approved it.
Rulings: the controller's follow-up rulings F1 to F8 (on the parked and deferred items), amended by the round-2
rulings R2-10 to R2-13 (where they differ, round 2 wins); the plan header defines each, and the odds rulings O1, O2,
O3 and O5 cited below. They are restated below as R1 to R8 with exact before and after values; R9 to R13 are the
readings this contract adds where a ruling is silent. Where a ruling and the spec differ, the ruling wins and is
listed for spec rev 3.3 (header, "Spec").
Repo facts: the repo map `docs/superpowers/plans/2026-10-24-compliance-followup-repo-map.md` (sections 0-8) and
section 8 of the 2026-10-24 map digest (not committed; each item it adds is cited here by its ledger line). Every
path:line below was re-read in the tree at `995534b` on 2026-10-24; outside docs/ that tree is the tree at
`5816d3c`, and the docs files cited here (the spec, the ledger, the compliance plan) are unchanged since `995534b`.
Ledger: `docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md` (245 lines), cited as `ledger:<n>`.

The tasks were drafted against this contract. Names a task added are private helpers listed in its Interfaces
block. Where a task's text and this appendix differ, the task wins.

### A.0 Global rules (every task obeys these; the plan copies them into "Global Constraints")

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
- Work on branch `compliance-followup`, which Task 1 creates from main's HEAD at execution time (R13, round-2 ruling
  R2-11), never from a pinned hash. Before it branches, Task 1 checks on `main` that `git status --short` and
  `git diff --stat 995534b HEAD -- . ':!docs'` both print nothing (only docs changed since the compliance merge); if
  either prints anything, stop and report: every line number and count in this plan rests on that tree. Commit once
  per task (Task 8: the full-run record, the ledger, and a repeat record after a review fix wave) with the
  repo-local identity (already set) and end each message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- DRIFT RULE (round-2 ruling R2-13). Every Edit in a task is an exact old-text/new-text pair quoted from the tree at
  `5816d3c` and names its anchor: the function, constant, test, YAML row or table row it sits in. A cited line number
  is that of `995534b` (the same as `5816d3c` outside docs/) and only helps find the anchor; line numbers also shift
  as earlier tasks of this plan land (Task 2 before Tasks 3 and 6, Task 4 before Task 5), and then the anchor wins.
  Before each Edit, re-read the file. If the quoted old text differs only because an earlier plan changed it, apply
  the same change to the current text, keep the earlier behaviour, and record a one-line ruling in the execution
  ledger (`docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`); if the change no longer makes
  sense, stop and rule. This plan runs first, so outside docs/ no earlier plan has changed its files (Task 1's check);
  the odds and E1 plans carry the same rule for the files this plan changes (section 12).
- Guards that scan `core/**/*.py` stay exactly as in the compliance plan (its Appendix A.0; raw text includes docstrings
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

### A.1 Decisions (R1-R8 restate F1-F8 as amended by R2-10 to R2-13; R9-R13 are this contract's readings)

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
    turtle, turtledemo, idlelib`, then `pstats, tracemalloc` (round-2 ruling R2-10: their own APIs load files,
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
  attribute `setattr`, `delattr`, `globals`, `vars`, `locals`, `modules`, `__dict__`, `builtins`, `__builtins__`,
  `f_globals` or `f_locals` (`typing.TYPE_CHECKING = True`, `setattr(typing, ...)`, `globals()["__name__"] = ...`,
  `sys.modules["typing"] = ...`, `sys._getframe().f_globals["__name__"] = ...` each hide an import today; the two
  frame names were added by the controller's ruling at the plan's final review). The two files stay
  character-identical in these helpers (a new source-equality test, section 6.4); `test_code_files_match_owner`
  (tests/compliance_signer.py:630-677) keeps their outputs in step. Checked in-process on 2026-10-24, and again with
  the frame names at the final assembly: the real closure (10 entries) is unchanged, and no closure file uses any of
  those names. Stated limit (spec rev 3.3; the controller accepts it as stated, round-2 ruling R2-12): the route list
  is a denylist, so another module changing `typing.TYPE_CHECKING` before this one is imported, or a name built at
  run time, is not seen; the owner's review of each hashed file's diff is the barrier there. `getattr` stays off the
  list, so `getattr(sys, "modules")["typing"] = ...` is a stated limit too: gate.py, model.py, rules.py, alerts.py and
  `owner._binds` call `getattr`, and listing it would void their guards.
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
- **R13 (order and signatures, the controller's ruling on the order of the plans, amended by R2-11 and R2-13).**
  This plan runs first, on `compliance-followup` from main's HEAD at execution time (no pinned hash: by then main holds this plan, the odds
  plan and the E1 plan as docs commits after `995534b`, and Task 1 checks that nothing outside docs/ changed); the
  odds plan runs second and E1 third, each from main after the one before merges, each under the DRIFT RULE (section
  0). GPT's check after 2026-10-30 14:40 is not waited for: a valid finding that touches built code becomes a new task
  with its own failing test.

### A.2 Files

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

### A.3 Guards: `tests/compliance_guards.py` (Task 1; R1, R7, R9)

#### A.3.1 Imports (guards:12-18)
Add `import re` between `import os` (:15) and `import sys` (:16).

#### A.3.2 `NETWORK_MODULES` (guards:39-41), new text
```python
NETWORK_MODULES = ("urllib", "http", "socket", "_socket", "socketserver", "selectors", "ssl", "smtplib", "ftplib",
                   "imaplib", "poplib", "nntplib", "telnetlib", "xmlrpc", "asyncio", "webbrowser", "multiprocessing",
                   "wsgiref", "xml.sax", "xml.dom", "logging.handlers", "antigravity", "ctypes", "_ctypes", "_ssl",
                   "_overlapped")
```
The comment above it (guards:34-38) stays.

#### A.3.3 Dynamic constants (guards:45-51)
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
Dry run (2026-10-24, on a scratch copy of the guards file with this block and section 3.4): 29 distinct entries;
every entry in each import form, `import pstats`, `from pstats import Stats`, `import tracemalloc` and
`from tracemalloc import Snapshot` are hits; the section 3.6 negative controls are not; no hit in core/compliance,
core/odds or the R2/R4 scratch copies of rules.py and owner.py; longest line 120 characters.

#### A.3.4 `_dynamic_hits` (guards:146-157), new text with one new helper above it
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

#### A.3.5 `test_no_http_verb_calls` docstring (guards:249-262), new text (the body :263-270 stays)
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

#### A.3.6 `test_no_forbidden_module_import` (guards:273-302)
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

#### A.3.7 `test_imports_stay_on_the_allowlist` (guards:305-341)
- The "modules a plain socket/urllib list misses" list (:324-329) gains `"import xml.dom\n"`,
  `"from xml.dom import minidom\n"`, `"import xml.dom.minidom\n"`, `"import xml.dom.xmlbuilder\n"`,
  `"from xml import dom\n"`, `"from xml.dom.minidom import parseString\n"`, `"import antigravity\n"`,
  `"import ctypes\n"`, `"from ctypes import wintypes\n"`, `"import _ctypes\n"`, `"import _ssl\n"`,
  `"import _overlapped\n"`. The three old xml.dom cases stay.
- The negative control (:332-333) becomes
  `assert not _allowlist_hits(X, "import logging\nfrom logging import getLogger\nimport xml.etree.ElementTree\n"
  "from xml.etree import ElementTree\n")` (the `from xml.dom import minidom\n` line is dropped). :334-335 stays.

#### A.3.8 New test, placed right after `test_no_forbidden_module_import`
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

#### A.3.9 R7: the registration test (guards:483-489), new text with one helper above it
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

#### A.3.10 Interfaces this produces for the odds plan
`NETWORK_MODULES`, `DYNAMIC_MODULES`, `DYNAMIC_NAMES`, `DYNAMIC_BARE`, `DYNAMIC_EXEMPT`, `_dynamic_module`,
`_dynamic_hits`, `CLOCKS` in `tests/compliance_guards.py`. The odds guards (odds ruling O2) import them; they do not
copy. They test an import target with `_dynamic_module` (which honours DYNAMIC_EXEMPT), never with a raw prefix match
over DYNAMIC_MODULES: since `importlib` is a DYNAMIC_MODULES entry, a raw match would also drop `importlib.metadata`.
- `_suite_names(text)` (used by the E1 plan's registration test; name and signature fixed).

Expected after Task 1: `-m tests.compliance_acceptance compliance_guards/` prints `16/16 passed, 0 failed, 0 not run`.

### A.4 Loader: `core/compliance/rules.py` and `tests/compliance_tables.py` (Task 2; R2, R10)

#### A.4.1 Constants (after rules.py:405-406 `_BLOCKING`, `_MAX_REVIEW_DAYS`)
```python
_MAX_LEVERAGE = 10.0                                       # R2: a typo cannot sign 1e6x
_D15_FINANCING = frozenset({"credit", "margin"})           # D15: no credit buying (margin included, ledger:131)
_D15_ACTIONS = frozenset({"lend", "borrow"})               # D15: no coin lending or borrowing
_D16_ACTIONS = frozenset({"sell_short"})                   # D16 by content (spec:70), whatever policy_ref says
_D16_CLASSES = frozenset({"etp_leveraged", "etp_single_stock", "krx_derivative", "elw"})
_D16_ASSETS = frozenset({"krx_derivative", "elw"})
```

#### A.4.2 The five checks, at their R10 places in `_row`
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

#### A.4.3 Reason strings (exact; `<id>` is the row id)
| Rule | Reason |
|---|---|
| D15 content, financing | `rules: row <id>: match.financing: an allow, gated or grey row never matches ['credit'] (D15: no credit buying)` (the sorted hit list) |
| D15 content, action | `rules: row <id>: match.action: an allow, gated or grey row never matches ['borrow', 'lend'] (D15: no coin lending or borrowing)` |
| D15 label | `rules: row <id>: treatment: a D15 row is hard_block or out_of_scope (D15 only keeps credit and lending out)` |
| D16 content | `rules: row <id>: requires.live: a row matching ['etp_leveraged'] needs live broker evidence (D16)` (an ETP asset with no class axis lists `['etp_leveraged', 'etp_single_stock']`) |
| review_by | `rules: row <id>: review_by: 2026-10-22 is before the review of 2026-10-23` |
| max_leverage | `rules: row <id>: max_leverage: at most 10, got 10.5` |
| {cap} | `rules: row <id>: warning: only a grey row states a {cap}` |

#### A.4.4 Tests in `tests/compliance_tables.py` (and two lines of `tests/compliance_cli.py`)
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
New, in the compliance plan's Task 5 block after `test_shipped_okx_spot_is_the_d6_grey_row` (tables:968-981):
- `test_shipped_rows_that_can_let_through_are_pinned_exactly` with module constant `_T5_PINNED` (section 4.5): the set
  of shipped ids whose treatment is allow, gated or grey equals `set(_T5_PINNED)`, and for each id
  `({k: set(v) for k, v in r.match.items()}, r.requires_owner, r.requires_live, r.treatment) == _T5_PINNED[id]`.
  Docstring names ledger:113 (widening an allow row passed all 18 tests).

#### A.4.5 `_T5_PINNED` (generated from the shipped table on 2026-10-24; tuples keep the YAML order)
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

### A.5 Table text: `core/compliance/kr_rules.yaml:204` (Task 3; R3)

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

### A.6 Closure scan: `core/compliance/owner.py` and `tools/signer/sign.py` (Task 4; R4)

#### A.6.1 New helper, placed right after `_typing_flag` (owner.py:699-705; sign.py:622-628), identical in both files
```python
def _guards(tree: ast.AST) -> tuple[bool, bool, bool]:
    """Which `if` guards of `tree` may skip their body (P6, R4): (bare TYPE_CHECKING, typing.TYPE_CHECKING,
    __name__ == "__main__"). The bare name needs _typing_flag; `typing.` needs `typing` bound exactly once, by a
    plain `import typing`; the `__main__` test needs `__name__` bound nowhere in the module. A rebound name
    (typing = SimpleNamespace(TYPE_CHECKING=True), __name__ = "__main__") loses its guard, and a module that can
    change these names without binding them (an attribute store of TYPE_CHECKING or __name__, or any setattr,
    delattr, globals, vars, locals, modules, __dict__, builtins, __builtins__, f_globals or f_locals) trusts no
    guard: the guarded body is scanned. Not seen: another module changing typing.TYPE_CHECKING first (the review of
    each hashed diff)."""
    plain = any(isinstance(n, ast.Import) and any(a.name == "typing" and a.asname is None for a in n.names)
                for n in ast.walk(tree))
    routes = {"setattr", "delattr", "globals", "vars", "locals", "modules", "__dict__", "builtins", "__builtins__",
              "f_globals", "f_locals"}
    if any((isinstance(n, ast.Name) and n.id in routes) or (isinstance(n, ast.Attribute) and (n.attr in routes or (
            n.attr in ("TYPE_CHECKING", "__name__") and not isinstance(n.ctx, ast.Load)))) for n in ast.walk(tree)):
        return False, False, False
    return _typing_flag(tree), plain and _binds(tree, "typing") == 1, _binds(tree, "__name__") == 0
```
Dry run (2026-10-24, sandbox copies of owner.py and sign.py with sections 6.1-6.3): the real closure is the same 10
entries; the seven helpers are source-identical; the synthetic tree of section 6.4 hides none of its targets
(today's owner.py hides all of them); rules.py and model.py keep the bare TYPE_CHECKING skip and rules.py and
alerts.py the `__main__` skip; every new line is within 120 characters. `f_globals` and `f_locals` joined the route
list by the controller's ruling at the plan's final review (a frame's namespaces change `__name__` or
`TYPE_CHECKING` with no binding: `sys._getframe().f_globals["__name__"] = "__main__"`); re-checked then on scratch
copies: no closure file names either, the same guards hold, and the two frame modules r.py and s.py of section 6.4
hide their targets today and not after. `getattr` is not listed (gate.py, model.py, rules.py, alerts.py and
`owner._binds` call it), so `getattr(sys, "modules")["typing"] = ...` stays a stated limit (R4).

#### A.6.2 `_skipped` (owner.py:708-724; sign.py:631-647), new text, identical in both files
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

#### A.6.3 Callers (both files)
- `_import_nodes` (owner.py:727-736; sign.py:650-659): the parameter `bare_flag: bool` becomes
  `guards: tuple[bool, bool, bool]` in the signature and in its three uses; the docstring stays.
- `_repo_imports` (owner.py:755; sign.py:678): `for node in _import_nodes(tree, _typing_flag(tree)):` becomes
  `for node in _import_nodes(tree, _guards(tree)):`.
- sign.py's section comment (sign.py:597-601) stays true; no other line changes. `code_files`, `code_hash` and
  `_RECORD_DISTS` are untouched.

#### A.6.4 Tests
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
  `"core/compliance/r.py": "import sys\nsys._getframe().f_globals[\"__name__\"] = \"__main__\"\nif __name__ == \"__main__\":\n    import core.frame_main\n"`,
  `"core/compliance/s.py": "import sys\nfrom typing import TYPE_CHECKING\nsys._getframe().f_locals[\"TYPE_CHECKING\"] = True\nif TYPE_CHECKING:\n    import core.frame_bare\n"`,
  and the twelve empty targets `core/rebound_typing.py`, `core/rebound_main.py`, `core/alias_typing.py`,
  `core/unbound_typing.py`, `core/param_main.py`, `core/stored_typing.py`, `core/setattr_typing.py`,
  `core/globals_main.py`, `core/modules_typing.py`, `core/stored_bare.py`, `core/frame_main.py`, `core/frame_bare.py`.
  The expected set gains `core/compliance/h.py` .. `s.py` and the twelve targets. The docstring gains: "and a guard
  whose name the module rebinds or never imports plainly (typing rebound, `import os as typing`, no `import typing`,
  `__name__` assigned or a parameter), or that the module can change without a binding (an attribute store, setattr,
  globals(), sys.modules, a frame's f_globals or f_locals), is scanned too (R4)". (r.py and s.py, the frame routes,
  were added by the controller's ruling at the plan's final review.)
- `tests/compliance_signer.py` `test_code_files_match_owner` (:630-677): the same twelve sources, twelve targets and
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

### A.7 Signer ancestor walk: `tools/signer/sign.py` (Task 5; R5, R11)

#### A.7.1 New constant and function (sign.py:758-767 replaced)
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

#### A.7.2 Refusal text (sign.py:810-811), new
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
/ `without a terminal on stdin, or without python.exe -I.` test_help_names_owner_acts_1_and_2 pins help needles;
Task 5 adds the two new ones.

#### A.7.3 Tests (`tests/compliance_signer.py`)
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

### A.8 Alerts: `core/compliance/alerts.py` `log()` (Task 6; R6)

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

### A.9 Data layer (Task 7; R8, R12)

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

### A.10 Final task (Task 8)

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

### A.11 Not in scope (documented so a reviewer does not re-raise them)

- **H2** (ledger:188, and the carry item at ledger:239): moves to the execution spec (E2, the halt writer), which has a
  trusted clock. No production caller of `append_system_entry` exists (owner.py:400 is its only occurrence outside
  tests), so H2 is latent. tests/compliance_owner.py:958-960 keeps pinning today's behaviour.
- **T2** (ledger:189): a documented limit; it needs the owner's own key and a backdated signer clock, and the signer
  shows the stamp (sign.py `_confirm`). The only outside time source (alerts.jsonl rows) would change owner_state's pure
  signature (the compliance plan's Appendix A.8.3).
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
  ACCEPT items of the map digest's section 8.5 (ledger:65-67, :71, :92, :94, :105, :147, :148, :186, :115, :134) stay
  accepted, and so do the ACCEPT lines of the repo map's section 8: ledger:84, :102, :116, :124, :125, :132, :136,
  :138, :161, :172, :196, :205. Every line of the repo map's section 8 not named in this plan keeps its class there.
- **Already closed, so not re-raised:** ledger:74, :80, :133, :145 by the final fix wave (ledger:238); :75 and :242 by
  R1; :103, :113, :146, :243 by R2; :118 by R3; :208 by R4; the walk part of :233 by R5, in line with the :229 ruling
  that a refusal check fails closed (its rotation-help part was fixed at :238); :219 by R6; :69 by R7; :81, :82 by R8.
- **Execution-side items:** ledger:144 (a derived destination buy keeps the source's asset and multiple; no shipped
  path), :150 (a transfer's reservation_id carried into the destination buy) and :157 (a permit issued with session_id
  None), the same family as the carried session and reservation items.
- **Odds-side items:** the venues parser keys, `calendar_in_force`, `grey_rows`, the fixtures move (odds ruling O3), the
  zero stake (ledger:244), the yfinance cache, KONEX structural_max; ledger:68 (the guards' clean asserts over core/odds
  become non-vacuous once it holds .py files) and :101 (never `asdict` or `deepcopy` a Row: `match` is a
  MappingProxyType). The odds plan owns them.
- **Documented limits from the map digest (its sections 8.2 and 8.4):** the D14 seeds are non-recursive
  (owner.py:773 `.glob`) while the guards scan with rglob (guards:69), so a .py file in a core/compliance subfolder is scanned but is in the
  closure only once a closure file imports it (none exists today; the odds guards refuse a core/odds subfolder); a
  package `__getattr__` re-export (core/calendars/__init__.py:224-229) escapes D14, and neither allowlist lets
  core/compliance or core/odds import that package; `screen` ignores `effective_from` (gate.py:645-648), so a row that
  starts mid-horizon is not flagged (nothing is lost today; the odds plan reads the screening flags, odds ruling O5).
- **Owner acts:** OKX USDT/USDC deposit networks (ledger:112, :120); copying the updated signer (section 7); signing.

### A.12 Effects on the odds and E1 plans (they run second and third)

- Line numbers the odds rulings cite move once this merges: rules.py (`_VENUE_OPTIONAL` at :636-642 moves down by
  31 lines, section 4), tests/compliance_tables.py (`minimum_krw` at :633 moves to about :739; the new tests sit
  after :300), tests/compliance_store.py (the signed-home helpers at :242-299 move down by 43 lines, for example
  `_pubkey_at` 247 -> 290: Task 4's `import ast`, the twelve synthetic files of section 6.4 and its route asserts),
  and tests/compliance_guards.py:488-489 is gone (R7). The byte pins in tests/compliance_gate.py do not move (that
  file is not edited).
- `_T5_PINNED` (Task 2) pins the 15 shipped non-blocking rows; a change to one updates its pin in the same commit.
- R4: a closure module using a route name trusts no guard; keep TYPE_CHECKING-only imports out of such modules
  (core/odds now, execution/ for E1).
- The odds plan is written against main `5816d3c`, before this plan's code exists, and E1 likewise; both carry the
  DRIFT RULE (R2-13, section 0) for the files this plan changes (core/compliance/rules.py, owner.py, alerts.py,
  kr_rules.yaml, tests/compliance_guards.py, tests/compliance_tables.py, tests/compliance_store.py,
  tests/compliance_signer.py, tests/compliance_cli.py, tests/compliance_isolation.py, tools/signer/sign.py,
  data/krx/kis_client.py, core/ficc/data.py): they find their quoted anchor in the merged tree and make their change
  there, keeping this plan's behaviour. This plan renames no function, constant or test it touches (it only adds
  names and changes bodies), so every name they anchor on still exists after it merges.
- New `core/odds/*.py` files must pass the widened DYNAMIC_* lists (no pickle, marshal, unittest, logging.config,
  pstats, tracemalloc, importlib other than metadata, no attribute of the name `importlib` but `metadata`, bare
  compile). `core/oddsdata/` is outside both guard scopes (odds rulings O1, O2). The odds guards read the lists from
  `tests/compliance_guards.py` at test time and pin no entry count, so R2-10 binds core/odds with no odds code
  change; only the odds plan's prose list of the F1 additions (its Appendix A, the "no import of
  `importlib.util`, ..." bullet) lacked `pstats` and `tracemalloc` when this contract was drafted (raised for the
  odds drafts, not edited here).
- The odds guards' allowlist ("the stdlib minus NETWORK_MODULES and DYNAMIC_MODULES") tests each import target with
  `compliance_guards._dynamic_module`, never a raw prefix match over DYNAMIC_MODULES, so `importlib.metadata` stays
  allowed as the odds plan's Appendix A says (section 3.10).
- The odds suite registers `odds` in tests/run_all.py:113 and README.md:816 with no compliance test change (R7).
