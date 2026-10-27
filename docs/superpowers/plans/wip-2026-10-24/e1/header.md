# TRADEGEN E1 account inquiry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build E1, the read-only account inquiry of the approved E1 spec. It covers:
- one GET-only transport with frozen allowlists, the only network path in `execution/`;
- read-only inquiry of KIS (domestic and US balances, open orders, fills), Upbit (balances, open and closed orders,
  deposits, withdrawals, registered withdrawal addresses, key expiry) and OKX (key self-check, balances, positions,
  earn and loans, orders, fills, deposits, withdrawals);
- one hashed snapshot per venue per poll, and the gate's live `Positions` (P19) built from them, fail closed;
- live D16 deposit-type evidence, hash-chained, which the gate reads from the next Asia/Seoul day;
- the poll checks of spec 7 and their alerts (a Windows toast at once; push and email by the daily task);
- the narrow, file-exact widening of the read-only guards, and the signed code hash over `execution/`.

**E1 contains no order code. It cannot place, change or cancel an order, and it moves no money.** It never halts,
disarms, sells or withdraws either: those belong to E2 and E3.

**Architecture:** A new top-level package `execution/` (inside the guards' scan and the D14 code hash). The poller
`python -m execution.poll` reads the wall clock once per poll and asks `kis_inquiry`, `upbit_inquiry` and
`okx_inquiry` for a snapshot. Each venue module calls `transport.request`, which checks the request against the
venue's frozen allowlist (and, for KIS, a pinned TR id ending in R) before it reads any key, then sends one GET (or the
KIS token POST); `kis_inquiry` sends nothing unless the poll's context, loaded first, says the code is signed.
`snapshot.py` appends one canonical, hashed line per venue to that Seoul day's `inquiry-YYYYMMDD.jsonl`;
`evidence.py` appends deposit-type evidence to `evidence.jsonl` when it changes and once a day; `positions.py` builds
`model.Positions`; the pure `checks.py` compares the new snapshots with the previous ones, the owner state from
`owner.load_context()` and the limits, and returns alerts, which `poll.py` toasts and writes to `alerts.jsonl`. The
compliance package changes only where spec 8 says: `Context.live_evidence`, the evidence fold in `owner.py`, and the
gate's D16 rule.

**Tech Stack:**
- Python 3.13.14 in `.venv`; the standard library (`hmac`, `hashlib`, `base64`, `json`, `uuid`, `zoneinfo`,
  `msvcrt`/`fcntl`, `urllib.parse.quote`, `email.utils`);
- `requests` 2.34.2 (already installed and pinned; transport only; never `data.net.session`);
- `core.isolation` and `core.compliance.*` (`model.canonical_json`, `owner.load_context`, `alerts._toast`);
- the repo's own runner `tests/run_all.py`. There is no pytest. No new dependency.

**Spec:** `docs/superpowers/specs/2026-10-24-e1-account-inquiry-design.md` (rev 1, `5816d3c`), approved by the owner
on 2026-10-24. The gate's rules come from `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md`
(rev 3.2). The E1 rulings X1 to X9 fill the spec's gaps and are restated below as E1 to E9. The controller's
round-2 rulings E1R2-1 to E1R2-12 (2026-10-25) amend them and rule every open issue (listed at the end). The plan is
written against `main` at `5816d3c` and executes third, after the compliance follow-up and the odds plan (X1).

**For E1 spec rev 2.** Three round-2 rulings depart from the approved spec rev 1. The plan builds them as ruled;
the spec's next revision should take them in:
- **E1R2-3, evidence written on change (spec 6).** `evidence.jsonl` gets a record for a requirement only when its
  `met` value changes, or when its last record is dated on an earlier Asia/Seoul date (a daily heartbeat on the first
  poll of each Seoul day), instead of one record per requirement per poll: about four lines a day instead of about
  1,150. The lifting, re-blocking and 7-day expiry rules of spec 6 are unchanged, and a test proves the fold gives the
  same `live_evidence` as one record per poll would on the same history (E18, Task 10).
- **E1R2-4, daily inquiry files (spec 4 "State files").** Inquiry records go to `execution/inquiry-YYYYMMDD.jsonl`,
  one file per Asia/Seoul date of the poll, in place of the single `inquiry.jsonl`; nothing is ever deleted, and each
  poll opens only yesterday's and today's files (E30, Tasks 4 and 12).
- **E1R2-9, KIS only under signed code (spec 4 data flow, 5, 10; stricter).** The KIS inquiry sends nothing unless
  that poll's context says `code_signed is True`: the KIS key can trade, so only owner-signed code may hold it on the
  network. Upbit and OKX (read-only keys) poll regardless. Until you have generated your signing key and signed the
  code hash (main-spec owner acts 1 and 2), the KIS snapshot is `ok: false` with error "code not signed", with no
  alert beyond one amber KIS_UNSIGNED a day (E42, Tasks 5 and 12).

**The honest points:**
- **A KIS key is an order key.** KIS has no inquiry-only key or scope for individuals: one token from the app key and
  secret calls every API, orders included, and individual keys have no IP binding. Under E1-D2 only E1's own code
  (its frozen allowlists, the GET-only rule and the pinned R-suffixed TR ids) stands between a TRADEGEN process and a
  KIS order. That code is small, frozen and signed, but it is software, not a server-side refusal. QUANTGEN's
  processes hold the same key, and E1 cannot protect against code outside TRADEGEN.
- **Signing now gates E1's KIS requests, not its Upbit and OKX ones.** The poller sends nothing to KIS unless the
  poll's sealed context says the code on disk is the code you signed (E42, E1R2-9). Upbit and OKX keys are read-only,
  so an unsigned edit of `execution/*.py` can still read those two venues. The check stops unsigned code that keeps
  it; an edit that removes the check fails the test suite, and nothing in E1 stops an edit that removes both the
  check and those tests.
- **The keys, and the HTTP library, are outside every signature: a limit of this plan.** `.env` is outside the D14
  code hash, and so are `requests`, `urllib3`, `certifi`, `idna` and `charset_normalizer`, like the rest of the venv,
  as spec 6.4 accepts (E1R2-10): a venv change can alter what transport sends without a re-sign. The environment no
  longer can: `_send` ignores proxy, CA-bundle and `.netrc` settings (E1R2-11). E1 never logs, writes or sends a key
  anywhere but its venue.
- **E1-D4 adds the first unsigned entry that loosens the gate.** A process that can write `~/.tradegen` could forge an
  evidence record. The next-day rule, the 7-day expiry and the narrow vocabulary limit that, and the KRW 10M to 30M
  deposit levels are far above this account's stake (about KRW 42,000), so in practice the D16 rows stay blocked.
- **The real odds are unchanged by E1.** No plan without a real edge that keeps this floor can beat about 1 in 1,000
  (1 in 2,000 with the floor at half the stake), and the research puts the practical chance of 1,000x in a month at
  0.01% or less.

> This is software design, not legal, tax or investment advice. Neither TRADEGEN nor its author is a licensed
> advisor.

## Global Constraints

Every task's requirements include this section. It is section 0 of the E1 interface contract, copied verbatim.

### 0.1 Hard rules from the owner's brief
- Never arm the system, place an order, move money, or enter credentials or keys. Claude never adds a key to `.env`,
  never opens `.env`, never prints a value read from it, and never asks for one. Only `execution/keys.py` reads `.env`,
  inside the E1 process.
- Never edit anything under `C:\Users\whydi\OneDrive\Desktop\QUANTGEN`. Never write under `~/.nextgen`. Never run
  anything while QUANTGEN's test suite runs (0.3).
- Never delete `grokteam/PREREG_book.json` or `grokteam/out/frozen_book/`.
- Claude never runs `tools/signer/sign.py` with a real key, never asks for or handles the owner's passphrase, and never
  writes to the real `~/.tradegen/compliance/owner.jsonl`.
- Claude never creates the Windows Task Scheduler task and never starts the long-running poller. Both are owner acts
  (spec 12).

### 0.2 The never-live rule
- No test and no plan step makes a network call to any venue, with one exception: the owner-gated first live
  `python -m execution.poll --once` at the very end of the plan (Task 14), run only after the owner says in chat that
  the keys are in `.env`.
- Every E1 test runs with `execution.transport._send` replaced by a refusing stub (section 3); a probe test proves an
  unpatched send is refused under the suite.
- No test starts a process that imports `execution` (`subprocess`, `os.system`, `os.popen`, `multiprocessing`,
  `runpy`, `sys.executable`): a child has none of the wrapper's patches, and OKX `public/time` needs no key. CLI tests
  call `poll.main(argv)` in-process; the lock-held case uses a second in-process handle on `poll.lock`.
  `tests/execution_guards.py` checks every `tests/execution_*.py` for this (4.5).
- No test runs `importlib.reload` on an execution module (a reload points `keys._ENV_FILE` back at the real `.env`
  mid-test); the default `_ENV_FILE` is checked from the source text.
- Every suite or full-run command in this plan runs with the KEYLESS prefix, so no keyed client of the inherited
  suites (cockpit `test_21` calls `KRXGateway().daily("005930")`, which uses the real KIS client when keys are set;
  tests/acceptance.py:318-322) can reach KIS, Upbit or OKX. `config._clean` (config.py:33-41) reads `<...>` as unset
  and `load_dotenv()` (config.py:28) never overrides a variable that is already set; `keys.py` lets a variable that is
  present in the environment decide alone, so a `<...>` or blank value is missing and the `.env` file is not read for
  that name (section 5):
  - Git Bash prefix:
    `KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>'`
  - PowerShell (setting `''` would delete the variable, so the placeholder is required; run it and the command in
    the same tool call, since each call is a fresh process):
    `foreach ($n in 'KIS_APP_KEY','KIS_APP_SECRET','KIS_ACCOUNT_8','KIS_ACCOUNT_PD','UPBIT_ACCESS_KEY','UPBIT_SECRET_KEY','OKX_API_KEY','OKX_API_SECRET','OKX_API_PASSPHRASE','OPENDART_API_KEY','KRX_API_KEY','FMP_API_KEY') { Set-Item -Path "env:$n" -Value '<unset>' }; <command>`

### 0.3 Python and test runs
- Interpreter: `C:/Users/whydi/OneDrive/Desktop/TRADEGEN/.venv/Scripts/python.exe` (Python 3.13.14), run from the
  repo root. Never `pip install` anything; E1 adds no dependency (`requests==2.34.2` is already pinned,
  constraints.txt:85; `requests>=2.31` in requirements.txt:3 and pyproject.toml:13).
- No pytest. A test is a zero-argument `test_*` function that raises on failure. Use loops, helpers and
  save/restore in `try`/`finally`; never `monkeypatch` or fixtures.
- QUANTGEN overlap check before every test command. It must print nothing; if it prints a process, wait. QUANTGEN's
  Store Python runs as `python3.13.exe` with no `python.exe` beside it, so only a `python*` name filter sees it.
  - PowerShell tool:
    `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`
  - Git Bash prefix (the PowerShell script in single quotes, so Bash leaves `$_` alone):
    `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`
- One test or module: `.venv/Scripts/python.exe -m tests.execution_acceptance <module>/<test>` (or `<module>/`). It
  never writes `qa/acceptance_results.json`. Expected PASS output ends `N/N passed, 0 failed, 0 not run`.
- One suite: `<KEYLESS> .venv/Scripts/python.exe tests/run_all.py --suite <name>; echo "exit $?"; git checkout -- qa/acceptance_results.json`.
  A suite run rewrites the tracked CRLF `qa/acceptance_results.json`; restore it after every `--suite` run. Only
  Task 13's full run commits it.
- The inherited T-RO-01 check alone (no results file):
  `.venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; t(); u(); print('T-RO-01 ok')"`.
  Never run `python -m tests.macro_acceptance` (its `__main__` resyncs the registry).
- Never run two suites at once. The E1 suite stays under 60 s (X8).

### 0.4 Files, line endings and commits
- New files are UTF-8, no BOM, LF endings.
- These files E1 edits are CRLF and stay CRLF (verified with `git ls-files --eol`): `tests/acceptance.py`,
  `tests/run_all.py`, `README.md`; and `qa/acceptance_results.json` (Task 13 only). Every other file E1 edits is LF:
  `tests/macro_m0_harness.py`, `core/ficc/context_log.py`, `core/compliance/model.py`, `core/compliance/owner.py`,
  `core/compliance/gate.py`, `tools/signer/sign.py`, `tests/compliance_gate.py`, `tests/compliance_model.py`,
  `tests/compliance_store.py`, `tests/compliance_signer.py`. Re-run `git ls-files --eol <file>` before the first edit
  of each file; a different answer is a drift ruling (0.6).
- Edit existing files only with the Edit tool. Never `sed -i` (it strips CRLF). No E1 file is mixed-ending, so no
  Python bytes I/O edit is needed.
- Before every commit: `git diff --cached --stat` must equal `git diff --cached --stat --ignore-cr-at-eol`.
- Commit once per task with the repo-local identity. End each message with a trailer naming the model that wrote
  the commit, for example `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` or
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Work on branch `e1-account-inquiry`; Task 1 creates it with `git switch -c e1-account-inquiry` from an up-to-date,
  clean `main`.

### 0.5 Guards that bind every file under `execution/` (exact strings)
Raw text means docstrings and comments included.
- test_08 (tests/acceptance.py:169-175; raw, case-insensitive): never write `order_cash`, `order-cash`,
  `place_order`, `submit_order`, `TTTC0802U`, `TTTC0801U`, `VTTC0802U`.
- test_09 (tests/acceptance.py:178-182; raw, case-sensitive): never write `KIS_ACCOUNT`, `CANO` or `ACNT_PRDT_CD`,
  except in `execution/kis_inquiry.py` (E6). Upper-case `CANO` also matches `CANONICAL`: write `canonical` lower-case.
- T-RO-01 (tests/macro_m0_harness.py:28-60; code only, docstrings and comments stripped):
  - text, case-insensitive: `order_cash`, `order-cash`, `place_order`, `submit_order`, `tttc0802u`, `tttc0801u`,
    `vttc0802u`, `/v1/orders`, `/v1/withdraws`, `/v1/deposits/generate_coin_address`, `/api/v3/order`,
    `/sapi/v1/capital/withdraw`, `/sapi/v1/capital/deposit`, `private_key`, `seed_phrase`;
  - text, case-sensitive: `KIS_ACCOUNT`, `CANO`, `ACNT_PRDT_CD`;
  - the path regex `/uapi/[^\s'\"]*/trading/`;
  - file-exact exceptions (E6): `execution/kis_inquiry.py` may hold `KIS_ACCOUNT`, `CANO`, `ACNT_PRDT_CD` and the path
    regex; `execution/upbit_inquiry.py` may hold `/v1/orders` and `/v1/withdraws`; the exceptions cover the text
    checks only;
  - imports of `ccxt`, `web3`, `pyupbit`, `binance`, `python_binance`, `ib_insync`, `alpaca`, `alpaca_trade_api`,
    `mojito`, `pykis`, `kiwoom`, `okx`, `bybit`, `kucoin`, `coinbase`, `cbpro`, `MetaTrader5`, `oandapyV20`,
    `eth_account`, `bitcoinlib`, `bitcoin` (the top-level name `okx` is banned; `execution.okx_inquiry` is fine);
  - calls named `place_order`, `submit_order`, `create_order`, `send_order`, `new_order`, `order_cash`,
    `cancel_order`, `create_market_order`, `create_limit_order`, `buy_market_order`, `sell_market_order`,
    `buy_limit_order`, `sell_limit_order`, `withdraw`, `withdraw_coin`, `withdraw_krw`, `create_withdrawal`,
    `transfer`, `transfer_funds`, `deposit_address`, `get_deposit_address`, `create_deposit_address`,
    `fetch_deposit_address`, `generate_coin_address`, `sign_transaction`, `send_transaction`,
    `send_raw_transaction`;
  - `.post`, `.put`, `.delete`, `.patch` on a URL string containing `order`, `withdraw`, `transfer` or `deposit`;
  - never import `core.engine.orders` in any form.
- test_16 / test_18: every file is UTF-8; no `eodhd` or `quartr` in code.
- `tests/execution_guards.py` (section 4.5), over every `execution/**/*.py`:
  - raw, any case: no `private_key`, no `seed_phrase`; no `append_system_entry`, `system_halt`, `system_disarm`
    (E1 only alerts); no `x-simulated-trading`, no `openapivts` (no demo header, no mock host);
  - no `def`/`async def` named `transfer`, `withdraw` or `deposit_address`;
  - Upbit token rule (raw): every match of `(?i)/v1/(?:order|withdraw)[A-Za-z0-9_/\-]*` is in
    `execution/upbit_inquiry.py` and equals one of `/v1/orders/open`, `/v1/orders/closed`, `/v1/withdraws`,
    `/v1/withdraws/coin_addresses` (so `/v1/order`, `/v1/orders`, `/v1/orders/uuids`, `/v1/orders/chance`,
    `/v1/orders/cancel_and_new`, `/v1/withdraws/coin`, `/v1/withdraws/krw` and `/v1/withdraws/chance` all fail);
  - KIS token rule (raw): every match of `/uapi/[^\s'\"]*` is in `execution/kis_inquiry.py` and equals one of the
    nine GET paths of section 7, written as a literal set in the test (never read from `kis_inquiry.ENDPOINTS`);
    none of `order-cash`, `order-credit`, `order-rvsecncl`, `order-resv`, `daytime-order`, `/trading/order`,
    `/trading/daytime` (raw, lower-cased) in that file;
  - TR rule (raw): every match of `(?i)(?<![A-Za-z0-9])[A-Z]{4}[0-9]{4}[A-Z](?![A-Za-z0-9])` is in
    `execution/kis_inquiry.py` and equals one of the nine pinned TR ids of section 7 (upper-case, ending in `R`); no
    match of `(?i)[A-Z]{4}[0-9]{4}U` in any execution file (every KIS order TR ends in U: TTTC0011U, TTTC0012U,
    TTTC0013U, TTTT1002U, TTTT1006U, ...);
  - no string constant equal to `/api/v5/trade/order` anywhere;
  - import allowlist (E2): exactly these stdlib modules: `__future__`, `argparse`, `base64`, `collections.abc`,
    `contextlib`, `dataclasses`, `datetime`, `email.utils`, `fcntl`, `hashlib`, `hmac`, `json`, `math`, `msvcrt`, `os`,
    `pathlib`, `re`, `sys`, `threading`, `time`, `traceback`, `types`, `typing`, `uuid`, `zoneinfo`; `requests` and
    `urllib.parse` only in `execution/transport.py`; `core.isolation`; `core.compliance` and `core.compliance.*`;
    `execution` and `execution.*` (4.5 narrows these). Nothing else: never `subprocess`, `ctypes`, `socket`, `config`,
    `data.*` (so never `data.krx.kis_client`), `core.engine.*`, `core.quant.*`, `core.calendars.*`, `core.ficc.*`,
    `core.rules.*`. A module a task needs beyond this list is a ruling (stop and rule);
  - no star or dynamic import (`tests.compliance_guards._dynamic_hits`);
  - no attribute call named `post`, `put`, `patch`, `delete`, `request`, `send`, `urlopen`, `getresponse`,
    `connect` or `create_connection`, except the single `session.request(...)` inside the function `_send` of
    `execution/transport.py`; no `os.system`, `os.popen`, `os.startfile`, `os.fork*`, `os.exec*`, `os.spawn*`,
    `os.posix_spawn*` call; no subscript of `sys.modules`;
  - transport is the only way out (E36): `_send` is exactly the function of section 6 (`ast.unparse` equality with
    `SEND_SOURCE`, 4.5: one `requests.Session()` with `trust_env = False`, then one `session.request(method, url,
    headers=headers, params=params, json=json_body, timeout=timeout, allow_redirects=False)`; E1R2-11); the name
    `requests` appears only in `execution/transport.py` (its import, the `requests.Session()` in `_send` and
    `requests.exceptions.ConnectionError`); outside transport.py, transport is reached only as
    `from execution.transport import <name>` with `<name>` one of `request`, `require_keys`, `Answer`, `InquiryRefused`, `InquiryError`, `AuthError`, `KeyMissing`, except
    `from execution import transport` in `execution/poll.py`, whose only use is `transport._clock = ...` inside
    `main`; every `request(...)` call outside transport.py passes the string constant `"GET"` as its second
    positional argument; `execution.keys` is imported only by transport.py and kis_inquiry.py, and kis_inquiry.py
    uses it only in the one call `keys.read(ACCOUNT_NAMES)`; the credential names `KIS_APP_KEY`, `KIS_APP_SECRET`,
    `UPBIT_ACCESS_KEY`, `UPBIT_SECRET_KEY`, `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE` appear (raw) only in
    transport.py;
  - no rebinding from outside: no `global` statement outside transport.py (there only `_next_issue_at` and
    `_okx_offset_s`); no assignment, augmented or annotated assignment or `del` whose target is an attribute, except
    `transport._clock = ...` inside `poll.main` and `session.trust_env = False` inside `transport._send`; no call of
    `setattr`, `delattr`, `vars` or `globals`; `getattr` only with a string-constant second argument that does not start with `_`; no attribute `__globals__`, `__dict__`,
    `__builtins__`, `__code__`, `__closure__`, `__subclasses__`; `object.__setattr__(self, ...)` only inside a
    `__post_init__`;
  - only `execution/evidence.py` names `evidence_path` (the one writer of `evidence.jsonl`, spec 6);
  - no wall-clock read (`tests.compliance_guards.CLOCKS`: `datetime.now/utcnow/today`, `date.today`, `time.time`,
    `time.monotonic`, `time.perf_counter`, `time.localtime`, `time.gmtime`, and the rest of that table, plus any
    `from time import ...`) outside the body of the function `main` in `execution/poll.py` (E11);
  - every write goes through `core.isolation.checked_target` immediately before it opens: every `open()` with a mode
    holding `w`, `a`, `x` or `+` has a `checked_target(...)` call as its first argument, and a `.open(...)` method call
    with such a mode is banned (`p.open("w")` names no checked target); both arguments of every
    `os.replace` are `checked_target(...)` calls; the receiver of every `.mkdir(` is a `checked_target(...)` call;
    `write_text`, `write_bytes`, `touch`, `unlink`, `rename`, `rmdir`, `os.remove`, `os.unlink`, `os.rename` and any
    `shutil` use are banned outright;
  - `execution/__init__.py` exists and is 0 bytes; a `__main__` block is exactly `raise SystemExit(main())`.
- `tests/execution_guards.py` also checks every `tests/execution_*.py`: no import of `subprocess`, `multiprocessing`,
  `runpy`; no `sys.executable`; no `os.system`, `os.popen`, `os.startfile`, `os.spawn*` or `os.exec*` call; no
  `importlib.reload` (0.2).
- Every text open passes `encoding="utf-8"` (`keys.py` reads `.env` with `encoding="utf-8-sig"`, E27). JSON printed by
  the CLI uses `json.dumps(..., ensure_ascii=True)`.
- Error and alert text never carries a key, a token, an account number, a URL with its query, a balance or an address
  (E37): it is built from venue names, allowlisted paths, exception type names, response field names and venue codes
  only, never from `str(exc)` of a parse or network exception.

### 0.6 The DRIFT RULE (ruling X1)
The plan is written against main `5816d3c`. The compliance follow-up plan changes `core/compliance/rules.py`,
`owner.py`, `alerts.py`, `tests/compliance_guards.py` (adds `_suite_names`), `tools/signer/sign.py`,
`data/krx/kis_client.py` (one line in `token()`; `_TOKEN_PATH`, `_store_token` and `KISClient._cached_token` stay, its
R12), `tests/compliance_store.py` (synthetic tree), `tests/compliance_signer.py` (rewrites the synthetic tree inside
`test_code_files_match_owner` and adds a test after it) and `README.md` (compliance row and Total); the odds plan
changes `rules.py`, `owner.py` (`calendar_in_force`), `gate.py` (`grey_rows`), `tests/compliance_fixtures.py`,
`tests/compliance_store.py` (moves its lines 242-299), `tests/compliance_gate.py` (appends tests), `tests/run_all.py`
and `README.md`, and it adds users of `core/compliance/model.py` (`OF.odds_ctx` builds on `F.ctx`, and the odds core
reads `Context`). Every E1 edit of a file is written as "find this anchor (function, block or line, quoted) and make
this change"; a line number is a hint at `5816d3c`, never the anchor. Before each Edit, re-read the file.
- If the quoted old text differs only because an earlier plan changed it, apply the same change to the current text,
  keep every earlier plan's behaviour, and record a one-line ruling in the E1 execution ledger
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`.
- If the change no longer makes sense, stop and rule before editing.
- The same applies to the `tests.compliance_guards` helpers E1 reuses (`_imports`, `_walk`, `_raw_hits`, `_def_hits`,
  `_dynamic_hits`, `_main_block_hits`, `_init_hits`, `_suite_names`, `CLOCKS`, `CORE_RAW_CI`, `DEF_NAMES`), the
  `tests.compliance_fixtures` helpers E1's tests use (`temp_home`, `ctx`, and the public `pubkey_at` and `full_home`
  that the odds plan's Task 4 moves there from `tests/compliance_store.py`, odds CONTRACT 3.3) and the
  `data.krx.kis_client` names Task 3 reads (`_TOKEN_PATH`, `KISClient._store_token`, `KISClient._cached_token`): if an
  earlier plan renamed one, use the new name and record it; if `pubkey_at` or `full_home` is not public, stop and rule.
- Model users: before Task 9's `seal_context` edit (13.1), grep `tests/` and `core/` (odds included) again for a
  pinned `ctx_hash` value; a hit is a drift ruling, never a silent update.

## Decisions this plan makes where the spec is silent or would break a guard

The tasks cite these as E1 to E43. E1 to E9 restate the rulings X1 to X9; E10 on are this plan's own; E1R2-n
marks where a round-2 ruling amended one. None of them loosens anything. The full interface contract (module names,
signatures, record formats, the catalogue, the anchors) is the E1 CONTRACT the tasks were drafted against; where a
task's text and the contract differ, the task wins.

- **E1 (X1) Order and drift.** E1 runs third, after the compliance follow-up and the odds plan have merged; branch
  `e1-account-inquiry` from that day's main. The DRIFT RULE of 0.6 binds every edit. The suite-list literal guard
  (tests/compliance_guards.py:483-489) is loosened by the follow-up, so E1 only adds `execution` to the `--suite` help
  and the README list. Source: X1.
- **E2 (X2) Package and imports.** `execution/__init__.py` is 0 bytes; the files are exactly spec 4's list; tests are
  `tests/execution_*.py`. Imports: the stdlib, `requests`, `core.isolation`, `core.compliance.*` only (plus
  `execution.*`). `alerts._toast` is reached through the module (`from core.compliance import alerts`, then
  `alerts._toast(title, body)`) so tests patch one seam; a documented cross-package use of a private seam.
  `keys.py` is a stdlib reader of the repo-root `.env` (`Path(__file__).resolve().parents[1] / ".env"`): lines
  `KEY=VALUE`, optional `export `, surrounding single or double quotes stripped, `#` full-line comments, no variable
  expansion; it returns only the requested names; a missing or blank value raises `KeyMissing(name)` (names only in
  the message); an environment variable of the same name wins over the file, and decides alone: a blank or `<...>`
  value in the environment is missing, so the KEYLESS prefix really keeps E1 keyless; it never logs or returns a value
  to anything but transport (and, for the account number, `kis_inquiry.py`: E14). Source: X2, spec 4.
- **E3 (X3) Transport.** One public `request(venue, method, path, params=None, *, tr_id=None) -> Answer` (Answer:
  frozen dataclass `body`, `server_utc`, `sha256`). The seam is
  `transport._send(method, url, *, headers, params, json_body, timeout) -> (status, headers, body_bytes)` using
  `requests` (X3 named `requests.request`; since E1R2-11 one `requests.Session()` with `trust_env = False`, E12;
  never `data.net.session`). Allowlists: three frozensets of `(method, path)`, one frozenset of
  `(path, tr_id)` for KIS, and the host per venue; exactly spec 5's tables; the KIS token POST is the only non-GET
  entry. Retry: a GET at most once more after 2 s on a connection error (`requests.exceptions.ConnectionError`,
  `ConnectTimeout` included; a `ReadTimeout` is not retried), HTTP 429 or 5xx; never a POST. Pacing: KIS,
  Upbit and OKX at most 5 requests a second. KIS token: the SAME file and format as `data/krx/kis_client.py`
  (`state_root()/kis_token.json`, `{"access_token": ..., "expires_at": <epoch seconds>}`, reused when
  `now < expires_at - 120`), `checked_target` BEFORE the POST, written atomically (tmp + `os.replace`, both checked),
  at most one issue per 70 s per process; E1 never imports kis_client; a test proves both read each other's file.
  Upbit JWT: HS512 with stdlib `hmac`/`hashlib`/`base64`/`json`, payload `{"access_key", "nonce": str(uuid4())}` plus
  `query_hash` (SHA512 hex of the UNENCODED query string) and `query_hash_alg: "SHA512"` when there are parameters;
  the string is built once as `"&".join(f"{k}={v}" for k, v in params)` over ordered pairs (array parameters as
  repeated `key[]=value`) and sent exactly; nothing reused from `data/crypto`. OKX: Base64(HMAC-SHA256(secret,
  timestamp + "GET" + requestPath-with-query + "")), timestamp ISO-8601 UTC with milliseconds and "Z"; refuse to send
  when |PC clock - OKX server time| > 25 s (from the last `public/time`). Source: X3, spec 5.
- **E4 (X4) Snapshots, positions, evidence records.** Canonical JSON is `core.compliance.model.canonical_json`; hashes
  are sha256 hex. The inquiry records (daily files under one `inquiry.lock` since E1R2-4, E30), `evidence.jsonl` and
  `alerts.jsonl` are appended under an OS sidecar lock (a copy of `owner._exclusive`, which is private) with fsync; `poll.lock` is a separate exclusive lock held for the poller's
  lifetime. `evidence.jsonl` lines: `{seq, prev_sha256, utc, requirement, met, value_krw, snapshot_sha256}` plus
  `row_sha256` over the canonical JSON of the other fields; seq from 1; the first `prev_sha256` is 64 zeros. The fold
  is the pure `core.compliance.owner.evidence_in_force(lines, today) -> frozenset[str]` (today = the Asia/Seoul date of
  `load_context`'s `now`); `load_context` reads `core.isolation.state_root()/"execution"/"evidence.jsonl"`; a missing
  file is `frozenset()`; a refused or unreadable one too. Source: X4, spec 6.
- **E5 (X5) Compliance changes.** `model.Context` gains `live_evidence: frozenset = frozenset()`. In `gate.py` the D16
  block becomes: block unless `set(row.requires_live) <= ctx.live_evidence`, reason
  `f"needs live broker evidence: {row.id}: {', '.join(missing)}"` with `missing` sorted; the exact-reason tests are
  updated. `owner.code_files` seeds add `execution/*.py` (non-recursive); `tools/signer/sign.py` changes in lockstep;
  `tests/compliance_store.py` (closure test) and `tests/compliance_signer.py` (`test_code_files_match_owner`) add the
  execution files and still exclude `config.py`, `data/`, `core/quant/`, `core/calendars/`, `core/engine/`.
  Source: X5, spec 8.
- **E6 (X6) Guards.** `tests/acceptance.py` (CRLF) `runtime_py()` adds `execution/**/*.py`; every caller (test_08,
  test_09, test_16, test_18, T-RO-01 via `_scan_files`) still passes; a positive control proves an order string in a
  synthetic `execution/` file is caught. T-RO-01 (`tests/macro_m0_harness.py`, LF) gets a per-file exception map
  `{"execution/kis_inquiry.py": {"CANO", "ACNT_PRDT_CD", "KIS_ACCOUNT", <the /trading/ path regex>},
  "execution/upbit_inquiry.py": {"/v1/orders", "/v1/withdraws"}}` applied ONLY to the text checks; every other check
  still runs on those files. test_09 gets the same KIS exception for that one file. The exactness tests (every
  `/trading/` path in kis_inquiry.py allowlisted, every TR string ends in R and is pinned, no order path words; Upbit
  strings only inside the four exact paths) live in `tests/execution_guards.py`, which also holds the import
  allowlist, the HTTP-verb rule, the wall-clock rule, the checked_target rule, the private_key/seed_phrase ban, the
  def-name ban, the 0-byte `__init__.py` and the `data.*`/`config`/`core.engine.*` import ban.
  `core/ficc/context_log.py` `ACTING_MODULE_PREFIXES` adds `"execution."`; T-CTX-01 still passes. Source: X6, spec 8.
- **E7 (X7) Checks, alerts, poller.** `checks.py` is pure: `run_checks(prev, new, owner_state_view, limits, now) ->
  list[Alert]`; the catalogue is `TEXT[text_key] -> str.format template` whose slots are ints, venue names, kinds and
  ISO times only; a test scans every template and every produced slot for digits-with-currency and address-like
  strings. Once-per-day state comes from `alerts.jsonl` itself, per `(venue, text_key)`, and an amber-to-red rise of
  the same venue and check fires at once (E19; E1R2-2 replaces X7's per-`(venue, kind)` rule). `poll.py`:
  `main(argv)`, `--once`, `--interval-min` (int 1..60, default 5), `--mark-sent <utc>` (marks rows with that exact utc
  sent; idempotent); exit codes 0 ok, 0 another poller holds the lock (it prints a message and exits; E1R2-1: spec 4
  wins over X7's 2, so a duplicate at-logon start is not a failed run), 4 crash in `--once`; the loop catches every
  exception per poll. The 09:05 daily task prompt change is the LAST task's owner gate: the plan prints the exact new
  prompt (section 18) and stops for the owner's approval. Source: X7, spec 7, E1R2-1, E1R2-2.
- **E8 (X8) Tests.** Suite `execution` mirrors `tests/compliance_acceptance.py`; `_wrap` adds a nested patch of
  `execution.transport._send` with a refusing stub and of `core.compliance.alerts._toast` with a recorder; a probe
  test proves an unpatched send is refused. Synthetic venue responses are Python dicts in
  `tests/execution_fixtures.py`, shaped like the official docs' examples (field names exactly as in the research
  tables), never captured from a live account. The suite stays under 60 s. Source: X8, spec 9.
- **E9 (X9) Owner acts and the first live poll.** The final task lists the six owner acts of spec 12 verbatim, and says
  the first live poll (`--once`) is run by Claude only after the owner says the keys are in `.env`, and only as
  `--once`, printing a redacted summary (venues, counts, ok/error, no balances). Source: X9, spec 12.
- **E10 The allowlists live in the venue modules.** `kis_inquiry.ENDPOINTS` and `kis_inquiry.TR_IDS`,
  `upbit_inquiry.ENDPOINTS` and `upbit_inquiry.PUBLIC`, `okx_inquiry.ENDPOINTS` and `okx_inquiry.PUBLIC` are
  module-level frozensets; `transport.request` reads them at call time through `transport._rules(venue)` (an import
  inside the function, since the venue modules import transport). Reason: E6 lets the KIS `/trading/` paths and the
  Upbit `/v1/orders`, `/v1/withdraws` strings appear only in those two files, so a copy inside `transport.py` would
  fail T-RO-01. The hosts, the one POST exception and every check stay in transport. Task 2 creates the three venue
  modules with these constants only. Source: spec 5 ("module-level frozensets; a test pins each one exactly") read
  with X6.
- **E11 One wall-clock reader.** `poll.main()` reads the clock once per poll (`now`, aware UTC) and passes it down, and
  sets `transport._clock = lambda: datetime.now(timezone.utc)` for the three send-time needs: the OKX timestamp
  header, the OKX clock offset at each `public/time` answer, and the KIS token's age and 70 s rate limit. Pacing and
  retry use `transport._sleep` (a seam bound to `time.sleep`), which reads no clock. The default `transport._clock`
  raises `RuntimeError("transport: no clock; poll.main sets one")`. Source: spec 7 "reads the wall clock only in
  main()" and spec 8 guard, which a sending transport cannot otherwise meet.
- **E12 The query is built once and sent as built.** `transport._query(venue, path, params)` joins ordered pairs as
  `f"{k}={quote(v, safe=',')}"` (`urllib.parse.quote`); every key must match `[A-Za-z0-9_\[\]]+`; every value must be
  `str`. For a signed Upbit or OKX request, a value that quoting would change is refused, so the hashed or signed
  string is byte-identical to the sent one; the KIS value `PDNO=%` goes out as `%25`. The query rides in the URL and
  transport always passes `params=None` to `_send` (the X3 seam keeps the argument). `_send` opens one
  `requests.Session()`, sets `session.trust_env = False` and makes one `session.request(method, url,
  headers=headers, params=params, json=json_body, timeout=timeout, allow_redirects=False)` (E1R2-11): with
  `trust_env` off, `HTTPS_PROXY`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` and `~/.netrc` no longer apply (checked
  offline against requests 2.34.2: `merge_environment_settings` then gives no proxies and `verify=True`, and
  `prepare_request` reads `.netrc` only when `trust_env`). The whole function is pinned by a guard (`SEND_SOURCE`)
  and run for real by a test with `transport.requests` swapped for a recorder: `requests` follows redirects by
  default and, on a host change, drops only `Authorization`, keeping the `appkey`, `appsecret` and `OK-ACCESS-*`
  headers (and, on 307 or 308, the tokenP body). A 3xx is an error. OKX algo orders are read once per `ordType`,
  never as a comma list (E25). Source: X3 plus the Upbit and OKX signing rules (research: upbit.md section 2, okx.md
  section 2), E1R2-11.
- **E13 Refusal order.** `request` checks, in order: the venue is one of `kis`, `upbit`, `okx`; `(method, path)` is in
  the venue's `ENDPOINTS`; the method is `GET`, or exactly `("kis", "POST", "/oauth2/tokenP")`; for KIS GET a `tr_id`
  with `(path, tr_id)` in `TR_IDS` and `tr_id.endswith("R")`, for the KIS POST and every Upbit or OKX request
  `tr_id is None`; the parameters (E12; the KIS token POST takes none: `params is None`); for a signed OKX request a
  recorded OKX offset within 25 s. Every refusal is
  `InquiryRefused(reason)` before `keys.read` is called. Source: spec 5 steps 1-3, spec 9.
- **E14 KIS account numbers.** `kis_inquiry.snapshot()` reads `KIS_ACCOUNT_8` and `KIS_ACCOUNT_PD` with `keys.read`
  before its first transport call (they are request fields, not credentials) and checks them as 8 and 2 ASCII digits
  (error text "KIS account number is not 8 + 2 digits", never the value). Every credential (app key and secret, Upbit
  keys, OKX key, secret and passphrase) is read only inside transport, after the checks. Source: spec 5 "read only
  inside kis_inquiry.py", spec 8 KIS exception.
- **E15 Answer validation lives in transport.** Success is HTTP 200 plus the venue's success marker: KIS `rt_cd == "0"`
  (the token answer: a non-empty `access_token`), OKX `code == "0"`, Upbit no `error` key. A 401 or 403, or a code in
  `transport.AUTH_CODES[venue]`, raises `AuthError`; anything else raises `InquiryError` naming venue, path, HTTP status
  and the venue's code only. KIS `EGW00121`, `EGW00122`, `EGW00123` (token invalid, unknown, expired) mark that token
  bad for this process (`transport._bad_tokens`) and raise `InquiryError`, so the next poll issues a fresh token within
  the 70 s rule; a newly issued token that is already bad raises `AuthError` and blocks issuing for 6 hours (KIS
  returns the same token within 6 hours, and every issue sends the owner a KakaoTalk notice). Every `ValueError` or
  `OSError` out of `_send` (each `requests` exception is an `OSError`; http.client's latin-1 `UnicodeEncodeError` on a
  header value is a `ValueError` whose text quotes the secret's characters) becomes
  `InquiryError(f"{venue} {path}: {type(exc).__name__}") from None` (never the URL, which holds the account number in
  its query, and never the exception's text); anything else propagates (the suite's `Refused` and `AssertionError`
  included). Source: research error tables (kis.md 8, upbit.md 9, okx.md 8 with skeptic correction 2: 50123).
- **E16 Snapshot fields refined.** `fills`, `deposits`, `withdrawals` hold each venue's recent window (KIS: yesterday
  and today in Seoul, overseas from two days back; Upbit: the default 7-day closed-order window and the latest 100
  deposits and withdrawals; OKX: the default 3-day fills and the latest 100 deposits and withdrawals), not "since the
  last poll"; `checks` diffs ids between consecutive ok snapshots, which needs no clock. `cash` is fiat only and is
  the settled amount: KIS domestic KRW is the D+2 deposit `prvs_rcdl_excc_amt` (so a buy that has not settled is not
  counted twice: once in holdings, once in cash), KIS foreign cash is `frcr_dncl_amt_2` per currency, Upbit KRW is
  `balance + locked`. Coins, OKX USDT and USDC included, are holdings (the gate needs them in `Positions.holdings`).
  A new field `deposit_krw` carries KIS `dnca_tot_amt` for D16 evidence (spec 6 names that field). Source: spec 6,
  research kis.md 5.1 (`tot_evlu_amt` = securities + D+2 deposit).
- **E17 Positions fail closed.** `live_positions(snapshots, now)` (the 15-minute rule needs `now`) returns `None` when
  any of the three venues is missing, not ok, stamped more than 15 minutes before `now` or after it, holds a symbol or
  cash currency without a KRW price, or has a negative value. KIS overseas covers the US only (`OVRS_EXCG_CD=NASD`,
  `TR_CRCY_CD=USD`), matching the instrument map; each KIS list is read on its first page only
  (`# ponytail: first page only; a 51st holding or 101st fill is missed; add tr_cont paging when the account grows`).
  Source: spec 6, research kis.md 4.8.
- **E18 Evidence, exactly.** The vocabulary is the four E1 items with their thresholds, owned by owner.py:
  `deposit_krw_10m` 10,000,000, `deposit_krw_15m` 15,000,000, `deposit_krw_20m` 20,000,000, `cash_krw_30m`
  30,000,000. A line naming any other requirement (`broker_approval`, `collateral_105pct`), or whose `met` disagrees
  with `value_krw >= threshold`, breaks the chain, so `live_evidence = frozenset()`. Each poll with an ok KIS
  snapshot judges every requirement it can and appends a record for a requirement only when that requirement has no
  record yet, when its `met` differs from the requirement's last record, or when that last record's own `utc` falls
  on an earlier Seoul date than the poll's `now` (a daily heartbeat on the first such poll of each Seoul day). This is
  E1R2-3 (spec rev 2), replacing spec 6's one record per requirement per poll (about 1,150 lines a day at 5-minute
  polls, each re-verified by every `load_context`); it writes about four lines a day plus one per change. The fold
  below is unchanged and gives the same `live_evidence` as one record per poll would on the same history: the latest
  record has the same `met` and the same Seoul date (the heartbeat dates it on the last polled day), and the met run
  starts at the same poll (checked offline on 9,780 comparisons over random histories with gaps, skipped items and
  1-second steps across midnight, `e1/sandbox_round2/fold_probe.py`; Task 10 proves it in the suite). A record is
  dated as late as the log allows (the latest Seoul date among the lines up to and including it, as
  `owner._owner_fold` dates a loosening). A requirement counts when its latest record is met, stamped on or before
  today and at most 7 days before today, and the unbroken run of met records ending there starts on a Seoul date
  before today. Source: spec 6, D12, X4, E1R2-3.
- **E19 Alert identity.** Dedupe is per `(venue, text_key)` per Seoul date (E1R2-2, replacing X7's per-`(venue,
  kind)` rule): each text_key has one fixed level and dedupes on its own rows, so an amber HOLDINGS_EXPLAINED never
  hides a red HOLDINGS_UNEXPLAINED, nor D15_LOAN a D15_EARN. A level rise fires at once: a red alert is also fresh
  when the latest non-clear row today of its `(venue, kind)` is amber (for example KEY_AUTH red, then KEY_MISSING
  amber while KEY_HEALTH could not be evaluated, then KEY_AUTH again); within one poll the fresh rows are written
  amber and info first, red last, so a red that fired is its group's latest row and does not fire again. A text_key
  that was raised today, whose kind was evaluated this poll (`checks.evaluated`: its inputs were there, for example
  the venue was ok) and that is not raised now writes one row with `level: "clear"` and `sent: true` (never toasted
  or sent); the next occurrence that day fires again. A poll that could not evaluate a check (the venue failed, no
  live positions, the owner log not OK) clears nothing, so a flaky poll cannot re-fire a red alert. Source: spec 7
  "at most once per venue per Asia/Seoul day, unless it clears and comes back", "a recovery is logged, not alerted",
  X7, E1R2-2.
- **E20 ADDRESS_LIST compares `(currency, address, secondary_address or "")`.** Upbit's `net_type` and the owner's
  `withdrawal_address.network` use different vocabularies (`BTC` vs `bitcoin`), and the owner entry's `venue` is the
  destination, so only currency, address and tag can be matched. Red when the set changed since the last ok Upbit
  snapshot, and red when Upbit lists an address no signed entry names; the second half is skipped ("not set") while
  the owner log is not OK. Source: spec 7, core/compliance/owner.py:153-154 and gate.py:367-372.
- **E21 Upbit key expiry** is the earliest `expire_at` among all keys `/v1/api_keys` lists: E1 cannot tell which row is
  its own key without reading the key value outside transport. Source: X2 "never returns a value to anything but
  transport", research upbit.md 4.11.
- **E22 Allowlisted but unused.** `/v1/status/wallet` stays on the Upbit allowlist (spec 5) but nothing calls it in
  E1: no spec 7 check reads it. OKX `asset-valuation` is called for its aggregate `earn` figure (D15; skeptic
  correction 5). Source: spec 5, okx.md verification 5.
- **E23 Alert CLI.** `--pending` prints one JSON line for the daily task (section 16.4), reading `alerts.jsonl`
  without a lock and creating nothing (a missing file prints `{"send": false}`); it re-verifies every row before it
  renders it, since the daily task forwards the text off the PC. `--mark-sent` takes the `alerts.jsonl` sidecar lock,
  and only when the file exists. Neither takes `poll.lock`. An argument error exits 4 (argparse's own `SystemExit(2)`
  is caught; 4 stays the not-ok code after E1R2-1 made the lock exit 0). `--pending` never lists an info row (E43).
  Source: spec 7 delivery, X7, E1R2-1.
- **E24 Owner state per poll.** Each poll calls `owner.load_context(now, PLACEHOLDER)` once, first, before any venue is
  asked (E42 needs `code_signed` before KIS sends), with `PLACEHOLDER = model.Positions(equity_krw=1.0)`, and reads
  only `ctx.owner` (limits, caps, addresses, `ok`) and `ctx.code_signed`. The placeholder only keeps `load_context`'s
  positions check satisfied; neither the owner state nor `code_signed` depends on positions (owner.py `_context`:
  `signed = owner.ok and bool(current) and code_approval(check) == current`, computed before `_positions_problem`), so
  live positions are never passed in. Source: spec 4 step 5 "the owner state (load_context)", spec 6.4 "every caller
  goes through load_context", E1R2-9.
- **E25 OKX classification.** Algo orders: one `orders-algo-pending` call per `ordType` in `("conditional", "oco",
  "trigger", "move_order_stop", "iceberg", "twap", "chase")`. A `MARGIN` position counts as a loan (D15); a `SWAP`,
  `FUTURES` or `OPTION` position with `pos != "0"` sets flag `derivative_position`; `instType == "EVENTS"` in any
  position, open order or fill sets flag `EVENTS`; a `pos == "0"` row is ignored. Source: okx.md 5.2, 5.5, skeptic
  corrections 6-8.
- **E26 Loans and earn.** KIS loans: `tot_loan_amt` (inquire-balance output2), the sum of `loan_amt` (output1),
  `crdt_fncg_amt` and `thdt_rcvb_amt` (asset summary), `rcvb_amt` (integrated margin). OKX loans: each
  `details[].liab`, each flexible-loan `loanData[].amt`, each MARGIN position. OKX earn: each Simple Earn `amt`, the
  `asset-valuation` `details.earn`, and each `details[].autoLendStatus` in `pending`/`active`. Any figure above 0 is
  D15_LIVE. Source: spec 6 `loans`/`earn`, spec 7 D15_LIVE, research kis.md 5.1, okx.md 5.1, 5.9 and correction 5.
- **E27 `.env` details.** An unquoted value drops a trailing whitespace-then-`#` comment (python-dotenv's rule, which
  `config.py` applies to the same file); a `<placeholder>` reads as missing; the file is read with
  `encoding="utf-8-sig"` (a Notepad BOM). Source: X2, config.py:26-41.
- **E28 The test wrapper also isolates keys.** It removes every E1 key name and `KIS_BASE_URL` from `os.environ`
  (config's `load_dotenv()` put the real values there), points `keys._ENV_FILE` at a missing file in the temp home,
  patches `transport._sleep`, `transport._clock`, `transport._next_issue_at`, `transport._okx_offset_s`,
  `transport._bad_tokens`, records every refused or unrouted send in `STRAYS` and fails a passing test that left one,
  and watches the real `~/.tradegen/execution`, `~/.tradegen/compliance` and `~/.tradegen/kis_token.json` (only the
  set of paths under `execution/` while another process holds the real `poll.lock`, leaving out the daily
  `inquiry-<YYYYMMDD>.jsonl` files the poller starts at each Seoul midnight, so the owner's running poller does not
  fail a suite). The harness imports `execution` lazily, so a half-built module is one `<stem>/import` entry, not a
  broken `tests/run_all.py`. Source: X8, the never-live rule.
- **E29 T-CTX-01.** Only the prefix is added. The static scan's `repo_modules` (core/ficc/context_log.py:166-180) keeps
  scanning `core/` and `data/`; E1's import allowlist already bans every `core.ficc` import, and the runtime guard
  `assert_not_acting_caller` now refuses an `execution.*` frame. Source: X6, context_log.py.
- **E30 Daily inquiry files (E1R2-4; spec rev 2).** Inquiry records go to `execution/inquiry-YYYYMMDD.jsonl`, one file
  per Asia/Seoul date of the poll's `now` (`snapshot.inquiry_path(day)`), all appended under the one sidecar lock
  `execution/inquiry.lock` (`snapshot.exclusive(snapshot.home() / "inquiry")`, so no lock file per day). Nothing is
  ever deleted (about 1.3 MB a day; the owner may archive old files by hand). Each poll opens only yesterday's and
  today's files (`snapshot.read_all` of each; a missing one reads as `[]`), which hold exactly the rows since 00:00 of
  yesterday: the previous ok snapshot per venue, the fail streak and today's first poll. A venue whose last ok
  snapshot is older is compared again from its next ok snapshot (`# ponytail:` comment). This replaces spec 4's single
  `inquiry.jsonl` and this plan's backward chunk reader (`read_since` is gone). Source: E1R2-4.
- **E31 Missing keys.** A venue whose keys are not in `.env` gives a not-ok snapshot with flag `keys_missing`. It
  raises the amber KEY_MISSING (kind KEY_HEALTH) once per venue per Seoul day, so a key deleted from `.env` shows
  (E1R2-8, replacing this plan's earlier "no alert"); the owner accepts one amber a day for a venue never keyed (OKX
  may stay unkeyed until its 2026-12-03 auto-off). The poll also lists `"<Venue>: keys not in .env"` in `not_set`;
  OUTAGE and the fail streak (`checks.priors`) skip the venue, since KEY_MISSING already says why. Source: E1R2-8,
  spec 7 KEY_HEALTH, spec 10.
- **E32 Poll order.** The poll's context first (E24), then Upbit, then OKX (it values USDT and USDC at Upbit's
  `KRW-USDT`), then KIS (which sends only under signed code, E42). `okx_inquiry` first calls `require_keys("okx")`
  (no network call while its keys are missing), then `public/time` (its offset gates every signed OKX request), then
  the self-check; a failed self-check stops OKX for that poll. Source: spec 5 OKX, spec 6 positions, E1R2-9.
- **E33 Evidence writer failures.** A broken `evidence.jsonl` chain does not crash the poll: `evidence.record` raises
  `evidence.EvidenceBroken` (chain defects only), `poll_once` catches only that and raises the amber `EVIDENCE_BROKEN`
  alert (kind `EVIDENCE`); `live_evidence` is then empty (fail closed). A refused write (`checked_target`'s
  `RuntimeError`) anywhere, `evidence.jsonl` and `kis_token.json` included, is not a venue error: it propagates out of
  the venue snapshot and `poll_once`, stops that poll and is alerted as a crash (OUTAGE_CRASH, or E40's direct toast
  when the alert rows cannot be written either). Source: spec 10.
- **E34 Daily-loss baseline.** The day's start is the first poll of the current Seoul date whose three snapshots give
  live positions, read back from today's daily inquiry file (E30); when none exists yet, the current poll is the start
  (no loss). Source: spec 7 DAILY_LOSS.
- **E35 Plan files.** The plan is `docs/superpowers/plans/2026-10-24-e1-account-inquiry.md`; its execution ledger is
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (LF), created and committed by Task 1.
- **E36 Transport is the only way out.** The guard bullet "transport is the only way out" of 0.5 makes spec 11's
  "the test suite fails on any widening" hold for the paths around transport, not only through it: no execution
  module but transport can reach `requests`, `_send`, the signing helpers, the hosts or a credential name, and the
  stdlib allowlist leaves out `subprocess`, `ctypes` and `socket` (the toast reaches `subprocess` through
  `alerts._toast`, outside `execution/`). Without it, a module could read the trade-capable KIS key and call `_send`
  with an order path while every other guard stayed green. Source: spec 5 "the only function in execution/ that sends
  anything", spec 11, critic finding.
- **E37 Error text from names only.** Venue parsers read fields through `_field`, `_num` and `_one`, which raise
  `snapshot.FieldError(name)` (the field's name, a literal of the parser); a failed snapshot's error is
  `f"{venue}: {path}: field {name}"` for a `FieldError` and `f"{venue}: {path}: {type(exc).__name__}"` for any other
  contained exception (E38), where `path` is the allowlisted path being read; transport's `InquiryRefused` and
  `InquiryError` texts are built from names, paths, TR ids and venue codes. `str(exc)` of a parse or network error is
  never used: `float("1,234,567KRW")` quotes the value, and a header encoding error quotes the secret. `Answer.body`
  is `field(repr=False)`. `response_sha256` keys are paths, `f"{path}?ordType={t}"` only for the OKX algo calls, never a
  KIS query (it holds the account number). A test scans every byte E1 writes, prints or toasts for the fake keys, the
  fake token and the fake account. Source: 0.5, spec 7 "never balances or addresses".
- **E38 Venue errors are contained, nothing else.** `snapshot(now)` turns into a failed snapshot exactly the venue's
  errors: `KeyMissing`, `AuthError`, `InquiryRefused`, `InquiryError`, `LookupError`, `ValueError` (`FieldError`
  included), `TypeError`, `AttributeError`, `ArithmeticError`. Anything else propagates: `checked_target`'s
  `RuntimeError` (a refused write is a crash, spec 10), the suite's `Refused` and the router's `AssertionError` (so a
  test sees a stray send instead of an `ok: false`), and programming errors. Source: spec 10, critic findings.
- **E39 Clock offset at receipt.** `Answer.received_utc` is `transport._clock()` read right after `_send` returns;
  each snapshot keeps `clock_offset_s` = the venue's time minus `received_utc` from its first answer with a `Date`
  header (OKX: `public/time`'s `ts`). CLOCK_SKEW compares that offset, not the poll's start time, with 60 s: KIS is read
  last, after about 20 paced OKX calls and possible 10 s timeouts. Source: spec 7 CLOCK_SKEW.
- **E40 An alert that cannot be written still shows.** When a poll crashes and writing its OUTAGE_CRASH rows fails too
  (a junction on `~/.tradegen/execution`, a link present before the first `state_root()` scan), `main` toasts the
  fixed sentence `CRASH_UNLOGGED` directly, at most once per process per Seoul date (an in-memory set), and prints the
  crash. Source: spec 10 "a refused write stops that poll and is alerted", E1-D6.
- **E41 Where E1 runs, and what it does not touch.** E1 runs only from the repo root (`python -m execution.poll`; the
  owner's Task Scheduler task starts in the repo). TRADEGEN is not pip-installed, so `pyproject.toml`'s
  `packages.find` (pyproject.toml:23-25, no `execution*`) is left alone. `tests/macro_acceptance._touchpoints` gains
  no `execution` entry: no other suite imports `execution`, the E1 suite patches `_send` itself, and `hermetic()`
  still refuses every `socket.connect` (a DNS lookup through `getaddrinfo` is the remaining residual, as for every
  suite). Source: critic findings, ruled here.
- **E42 KIS sends only under signed code (E1R2-9; spec rev 2, stricter).** The KIS key can trade, so only owner-signed
  code may hold it on the network. `poll_once` loads the poll's context first (E24) and passes it to
  `kis_inquiry.snapshot(now, ctx)`, whose first statement returns
  `snapshot.failed("kis", utc, "code not signed", flags=frozenset({"code_unsigned"}))` unless
  `model.is_sealed(ctx) and ctx.code_signed is True`: no key, account number or token is read and nothing is sent,
  the token POST included. Upbit and OKX keys are read-only, so they poll regardless. Until main-spec owner acts 1
  and 2 (the signing key, then the signed code hash; after this plan, E1 owner act 5), every poll gives that KIS
  snapshot and one amber KIS_UNSIGNED (kind KEY_HEALTH) a day and nothing more: OUTAGE and the fail streak skip
  `code_unsigned`, `not_set` lists `"KIS: code not signed"`, and with KIS not ok there are no live positions and no
  D16 evidence (fail closed). The check stops unsigned code that keeps it; an edit that drops the check fails Task
  5's tests, and nothing in E1 stops an edit that drops both (the header says so). Source: E1R2-9.
- **E43 The not-set record (E1R2-12).** When `checks.not_set(...)` is non-empty, the poll adds
  `Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET", slots={"skipped": "; ".join(items)})` to its
  raw alerts. `due` writes it at most once per Seoul day (its kind is never evaluated, so it never clears), as a row
  with `level: "info"` and `sent: true`; it is never toasted and `--pending` never lists it, so it never leaves the
  PC. Each item is one of `checks.NOT_SET_ITEMS`, which `verify_row` checks. No new file: spec 4's state files stay
  as listed, with E30's daily inquiry files. Source: E1R2-12.

## File map

| Path | Status | Task | Endings | In the D14 code hash (signed) | Responsibility |
|---|---|---|---|---|---|
| `execution/__init__.py` | create, 0 bytes | 1 | none | yes (from Task 9) | package marker |
| `execution/keys.py` | create | 2 | LF | yes | `.env` reader, `KeyMissing` |
| `execution/transport.py` | create | 2 (checks, `_send`), 3 | LF | yes | the only network path: checks, credentials, signing, one GET (or the token POST), the KIS token cache |
| `execution/kis_inquiry.py` | create | 2 (constants), 5 | LF | yes | KIS allowlist and TR ids, the KIS snapshot (sent only under signed code, E42); the only file with KIS account fields |
| `execution/upbit_inquiry.py` | create | 2 (constants), 6 | LF | yes | Upbit allowlist, the Upbit snapshot |
| `execution/okx_inquiry.py` | create | 2 (constants), 7 | LF | yes | OKX allowlist, self-check, the OKX snapshot |
| `execution/snapshot.py` | create | 4 | LF | yes | snapshot records, hashing, the daily inquiry files, the sidecar lock and JSONL helpers |
| `execution/positions.py` | create | 8 | LF | yes | snapshots -> `model.Positions` |
| `execution/evidence.py` | create | 10 | LF | yes | D16 deposit-type evidence -> `evidence.jsonl` |
| `execution/checks.py` | create | 11 | LF | yes | the poll checks, the sentence catalogue, the once-a-day rule (pure) |
| `execution/poll.py` | create | 12 | LF | yes | the poller CLI, `alerts.jsonl`, `--pending`, `--mark-sent` |
| `core/compliance/model.py` | modify | 9 | LF | yes | `Context.live_evidence`; `seal_context` hashes every field, defaults included |
| `core/compliance/owner.py` | modify | 9 | LF | yes | evidence fold, `load_context` reads it, `code_files` seeds |
| `core/compliance/gate.py` | modify | 9 | LF | yes | the D16 rule reads `ctx.live_evidence` |
| `tools/signer/sign.py` | modify | 9 | LF | no (owner-kept copy; owner act 5) | `code_files` seeds in lockstep |
| `core/ficc/context_log.py` | modify | 1 | LF | no | `ACTING_MODULE_PREFIXES += "execution."` |
| `tests/acceptance.py` | modify | 1 | CRLF | no | `runtime_py()` widened; test_09 KIS exception |
| `tests/macro_m0_harness.py` | modify | 1 | LF | no | T-RO-01 per-file text exceptions |
| `tests/run_all.py` | modify | 1 | CRLF | no | register the `execution` suite |
| `README.md` | modify | 1, 13 | CRLF | no | suite list (Task 1); status bullet, cockpit row, compliance row count, execution row, Total (Task 13) |
| `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` | create | 1, 13, 14 | LF | no | drift rulings, deferred minors, the full run's totals |
| `tests/compliance_gate.py` | modify | 9 | LF | no | new D16 reason texts, the lift test |
| `tests/compliance_model.py` | modify | 9 | LF | no | the Context-field case list |
| `tests/compliance_store.py` | modify | 9 | LF | no | closure test adds `execution/*.py` |
| `tests/compliance_signer.py` | modify | 9 | LF | no | lockstep test adds `execution/*.py` |
| `tests/execution_acceptance.py` | create | 1 | LF | no | suite aggregator, `_wrap`, `-m` runner |
| `tests/execution_fixtures.py` | create | 1-7 | LF | no | `isolated()`, `STRAYS`, `REAL_SEND`, `fake_keys()`, `serve()`, response dicts, `snap()` |
| `tests/execution_guards.py` | create | 1, 2 | LF | no | static guards, exactness tests, transport-only path, harness self-tests, registration |
| `tests/execution_keys.py` | create | 2 | LF | no | keys.py |
| `tests/execution_transport.py` | create | 2, 3 | LF | no | transport and token |
| `tests/execution_snapshot.py` | create | 4 | LF | no | records and JSONL helpers |
| `tests/execution_kis.py` | create | 5 | LF | no | KIS |
| `tests/execution_upbit.py` | create | 6 | LF | no | Upbit |
| `tests/execution_okx.py` | create | 7 | LF | no | OKX |
| `tests/execution_positions.py` | create | 8 | LF | no | positions |
| `tests/execution_evidence.py` | create | 9, 10 | LF | no | the fold, `load_context`, the gate lift, the writer |
| `tests/execution_checks.py` | create | 11 | LF | no | every check row, the catalogue scan, the once-a-day rule |
| `tests/execution_poll.py` | create | 12 | LF | no | the poller end to end, CLI exits, pending, mark-sent |
| `qa/acceptance_results.json` | modify | 13 | CRLF | no | the full run (committed once) |

Every `execution/*.py` joins the D14 code hash in Task 9 (the `code_files` seeds); before that it is outside it.
Nothing is signed yet (no owner key), so the change blocks nothing today; after main-spec owner act 1 (the signing
key), any later edit of these files blocks new exposure in the gate until the owner signs again. The poller also
sends no KIS request unless that poll's sealed context says `code_signed` (E42, E1R2-9); Upbit and OKX, whose keys
are read-only, poll regardless. `pyproject.toml` is not changed (E41).

Outside the repo, Task 14 only: the scheduled task `tradegen-compliance-daily` (its prompt, owner gate) and memory or
hand-over notes.

State files, all under `core.isolation.state_root()/"execution"` (never created by a computation of the path):
`inquiry-YYYYMMDD.jsonl`, one per Seoul date and never deleted (E30), all under one `inquiry.lock`;
`evidence.jsonl` (+ `.lock`), `alerts.jsonl` (+ `.lock`, + `.alerts.jsonl.<hex>.tmp` during `--mark-sent`; it also
holds the daily info row of E43), `poll.lock`. Plus `state_root()/"kis_token.json"` (shared with kis_client) and its
temp file `.kis_token.<hex>.tmp`.

## Owner gates during execution

1. **Before Task 1.** The compliance follow-up plan and the odds plan have merged to main (X1). If not, stop.
2. **Task 9.** The D14 code hash changes (the closure now covers `execution/*.py`, and `tools/signer/sign.py`
   changes in lockstep). Nothing is signed yet, so nothing breaks today; once the owner has a signing key (main-spec
   owner act 1), the owner re-verifies the signer copy and signs the new code hash (E1 owner act 5).
3. **Task 14.** Approve the new prompt of `tradegen-compliance-daily` (CONTRACT section 18; shown as a computed diff
   against the live prompt). It may send E1's alerts only to you: the same iOS push and the same email to
   `sapientia@korea.ac.kr`. Claude changes the task only after your explicit yes.
4. **Task 14.** The first live `python -m execution.poll --once`, run by Claude only after you say in chat that the
   keys are in `.env`, reporting venues, counts and ok/error only. Until you have signed the code hash, KIS reads
   nothing and reports `code not signed`; the first live KIS read is one more `--once`, run only after you say the
   code is signed. If the OKX self-check fails on auto-loan with a spot-mode key (E1R2-6) or the KIS overseas
   service is not enabled (E1R2-7), the plan stops and asks you; no check is loosened.
5. **After this plan: the six owner acts of spec 12** (CONTRACT section 19): the Upbit read-only key, the OKX
   Read-only key, nothing new for KIS, the Task Scheduler logon task, re-verifying and re-signing, and approving the
   daily task change. Until you do them, every venue without keys reports `keys missing` (listed as not set, with
   one amber KEY_MISSING a day, E1R2-8), KIS reads nothing until the code is signed (one amber KIS_UNSIGNED a day,
   E1R2-9), the poller does not run, and the gate's D16 rows stay blocked.

## Open issues, all ruled

The controller ruled every open issue on 2026-10-25 (E1R2-1 to E1R2-12); the tasks implement the rulings. The
numbers are kept, so "open issue N" in a task means item N here. The contract's section 20 holds the same list.

1. **Lock exit code.** Ruled E1R2-1 (spec 4 wins over X7): `EXIT_LOCKED = 0`; a second poller prints
   `another E1 poller holds poll.lock; exiting` and exits 0, so a duplicate at-logon start is not a failed run in
   Task Scheduler. Argument errors stay 4. (E7, E23, C16; Task 12.)
2. **evidence.jsonl growth.** Ruled E1R2-3 (spec rev 2): a record for a requirement only when its `met` changes, or
   when its last record is dated on an earlier Seoul date (a daily heartbeat on the first poll of each Seoul day),
   about four lines a day instead of about 1,150. Lifting, re-blocking and the 7-day expiry are unchanged, and a test
   proves the fold gives the same `live_evidence` as one record per poll. (E18, C14; Task 10.)
3. **inquiry.jsonl growth.** Ruled E1R2-4 (spec rev 2): daily files `execution/inquiry-YYYYMMDD.jsonl` (the Seoul
   date of the poll), never deleted; each poll opens only yesterday's and today's. (E30, C8, C16.2; Tasks 4, 12.)
4. **Dedupe per kind.** Ruled E1R2-2: dedupe per `(venue, text_key)` per Seoul date, and an amber-to-red rise for the
   same venue and check fires at once; an amber HOLDINGS_EXPLAINED never hides a red HOLDINGS_UNEXPLAINED, nor
   D15_LOAN a D15_EARN. (E19, C15.2; Task 11.)
5. **Fixture fields marked `[assumed]`** (3.2). Ruled E1R2-5: accepted. The owner-gated first live poll of Task 14 is
   where a mismatch shows; it fails that venue closed (`FieldError`), Task 14 records it in the ledger and a
   follow-up task fixes it under the same rules.
6. **OKX `autoLoan`.** The OKX docs say auto-loan is set only in the margin modes and "The default is true" (okx.md
   skeptic correction 4). Ruled E1R2-6: the check stays strict (spec 5). If the first live poll shows `autoLoan`
   true on a spot-mode key (`acctLv == "1"`), Task 14 stops and asks the owner; the check is never loosened.
7. **KIS overseas service.** The overseas inquiries need the overseas service enabled ("해외주식 서비스 신청 후 이용
   가능합니다", kis.md 5.2); without it the whole KIS snapshot fails every poll. Ruled E1R2-7: if the first live KIS
   poll shows it, Task 14 stops and asks the owner.
8. **Missing keys.** Ruled E1R2-8: an amber KEY_MISSING once per venue per Seoul day, so a key deleted from `.env`
   shows; OUTAGE skips the venue. (E31, C15.1; Task 11.)
9. **The poller and the code signature.** Ruled E1R2-9 (spec rev 2, stricter): KIS inquiry sends nothing unless
   `ctx.code_signed is True` in that poll's context, since the KIS key can trade; Upbit and OKX (read-only keys) poll
   regardless. Until main-spec owner acts 1 and 2 the KIS snapshot is `ok: false` with error `code not signed`, and
   the only alert is one amber KIS_UNSIGNED a day. (E42, E24, C9, C16.2; Tasks 5, 11, 12.)
10. **requests outside the signed hash.** Ruled E1R2-10: `requests`, `urllib3`, `certifi`, `idna` and
    `charset_normalizer` stay outside the D14 hash, as spec 6.4 accepts for the venv; the plan header states it as a
    limit, and `owner._RECORD_DISTS` is not changed.
11. **requests reads the environment.** Ruled E1R2-11: `_send` uses a `requests.Session()` with `trust_env = False`
    (no proxies, no `REQUESTS_CA_BUNDLE`, no `.netrc`) and `allow_redirects=False`, and the guard pins that exact
    function. (E12, C0.5, C4.5, C6; Task 2.)
12. **not_set persistence.** Ruled E1R2-12: one info-level row per Seoul day in `alerts.jsonl` (`level: "info"`,
    `sent: true`, never pushed) naming the skipped checks; no new file. (E43, C15, C16.2; Tasks 11, 12.)

---
