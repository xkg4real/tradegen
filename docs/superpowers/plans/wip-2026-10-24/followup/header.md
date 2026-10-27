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
