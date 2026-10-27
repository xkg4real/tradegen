# E1 plan: interface contract (binding for every task drafter)

Repo: `C:\Users\whydi\OneDrive\Desktop\TRADEGEN`. Written against `main` at `5816d3c`; E1 executes THIRD, after the
compliance follow-up plan and the odds plan have merged (ruling X1), on branch `e1-account-inquiry` cut from the main
of that day.

Binding inputs, in this order of precedence:
1. the controller's round-2 rulings E1R2-1 to E1R2-12 (`E1_RULINGS_ROUND2.md`, 2026-10-25). They amend the rulings
   X1 to X9, rule every open issue of section 20, and in the three items marked "spec rev 2" (E1R2-3, E1R2-4,
   E1R2-9) depart from the approved spec; the plan header lists those three under "For E1 spec rev 2";
2. the APPROVED spec `docs/superpowers/specs/2026-10-24-e1-account-inquiry-design.md` (rev 1, `5816d3c`);
3. the E1 rulings X1 to X9 (restated as E1 to E9 in section 1; they fill the spec's gaps);
4. the main spec `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` (rev 3.2) for the
   gate's rules;
5. the venue research (KIS, Upbit, OKX notes, the skeptic's "Verification" section winning where it says WRONG).

Everything below is fixed. A task that needs a name not listed here defines it as a private helper (leading
underscore) in its own module and says so in its Interfaces block. Never rename anything here. Every repo anchor
quoted below was read in the tree at `5816d3c`; the DRIFT RULE (0.6) says what to do when an earlier plan changed it.

---

## 0. Global rules (every task obeys these; the plan copies them into "Global Constraints")

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

---

## 1. Plan decisions (E1 to E9 restate rulings X1 to X9; E10 on are new; E1R2-n amends them where cited)

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

---

## 2. Files

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

---

## 3. Test harness

### 3.1 `tests/execution_acceptance.py` (Task 1; mirrors tests/compliance_acceptance.py)
```python
TESTS = Path(__file__).resolve().parent
MODULES = ("execution_guards", "execution_keys", "execution_transport", "execution_snapshot", "execution_kis",
           "execution_upbit", "execution_okx", "execution_positions", "execution_evidence", "execution_checks",
           "execution_poll")
_REAL = (Path.home() / ".tradegen" / "execution", Path.home() / ".tradegen" / "compliance",
         Path.home() / ".tradegen" / "kis_token.json")          # fixed at import
def _poller_running() -> bool         # another process holds the real execution/poll.lock (read-only probe)
def _real_listing(paths_only: bool) -> tuple    # see below
def _wrap(fn) -> Callable[[], None]
def tests() -> list[tuple[str, Callable[[], None]]]
def _main(argv: list[str]) -> int
if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
```
- `tests()` as compliance: skip a module file that does not exist, turn a failing import into one `<stem>/import`
  entry that re-raises, collect only `test_*` names defined in the module, modules in MODULES order, names sorted.
  The module imports nothing from `execution` or `tests.execution_fixtures` at module level.
- `_real_listing(paths_only)`: for a folder entry, `(path, size, mtime_ns)` of every folder and file under it (as
  compliance's `os.walk`); for a file entry (`kis_token.json`), its own `(path, size, mtime_ns)` (an `os.walk` of a
  file yields nothing); an absent entry adds nothing. With `paths_only`, the `execution/` entry and `kis_token.json`
  contribute `(path, 0, 0)` rows (the owner's poller appends every few minutes and refreshes the token daily), and a
  file whose name fullmatches `inquiry-\d{8}\.jsonl` is left out (the poller starts one at each Seoul midnight, E30);
  `~/.tradegen/compliance` is always listed in full. `_poller_running()` opens `_REAL[0] / "poll.lock"` (so a test
  that swaps `_REAL` swaps it too) only when it exists, read-only (`"rb"`, never creating it), tries
  `msvcrt.locking(fd, msvcrt.LK_NBRLCK, 1)` (else `fcntl.flock(LOCK_SH | LOCK_NB)`), unlocks at once, and returns True
  when the lock was refused (checked offline: a read-only handle sees another handle's `LK_NBLCK` as a
  `PermissionError`).
- `_wrap(fn)` imports `isolated` from `tests.execution_fixtures` inside its `run()` (lazily, as compliance imports
  `temp_home`), probes `_poller_running()` and lists both forms before, runs `fn()` inside
  `with hermetic(), temp_home() as home, isolated(home):` (hermetic from `tests.macro_acceptance`, temp_home from
  `tests.compliance_fixtures`), probes and lists again, and fails with
  `AssertionError("the test touched the real ~/.tradegen: ...")` if the full listings changed, or only the
  paths-only listings when either probe saw a running poller.
- `_main` runs the entries whose name contains `argv[0]` with `tests.run_all.run`, prints
  `<passed>/<total> passed, <failed> failed, <not run> not run`, exits 0 only with at least one entry and no failure,
  and never writes `qa/acceptance_results.json`.
- `tests/execution_fixtures.py` is not in MODULES.

### 3.2 `tests/execution_fixtures.py`
```python
NOW = datetime(2026, 10, 24, 0, 0, 0, tzinfo=timezone.utc)      # 09:00 KST, a Saturday
DATE_HEADER = "Sat, 24 Oct 2026 00:00:00 GMT"
FAKE_KEYS = {"KIS_APP_KEY": "test-kis-appkey", "KIS_APP_SECRET": "test-kis-appsecret",
             "KIS_ACCOUNT_8": "12345678", "KIS_ACCOUNT_PD": "01",
             "UPBIT_ACCESS_KEY": "test-upbit-access", "UPBIT_SECRET_KEY": "test-upbit-secret",
             "OKX_API_KEY": "test-okx-key", "OKX_API_SECRET": "test-okx-secret", "OKX_API_PASSPHRASE": "test-okx-pass"}
KEY_NAMES = tuple(FAKE_KEYS) + ("KIS_BASE_URL",)

class Refused(RuntimeError): ...        # what the wrapper's stubs raise
TOASTS: list[tuple[str, str]] = []      # (title, body) of every patched alerts._toast call; cleared by isolated()
SLEEPS: list[float] = []                # seconds of every patched transport._sleep call; cleared by isolated()
STRAYS: list[str] = []                  # every refused or unrouted send ("METHOD url-path"); cleared by isolated();
                                        # a test that expects one asserts on it and then clears it
REAL_SEND = None                        # Task 2: the unpatched transport._send while isolated() is active

@contextlib.contextmanager
def isolated(home: Path) -> Iterator[None]          # Task 1 creates it; Task 2 extends it (see below)
@contextlib.contextmanager
def fake_keys(**overrides) -> Iterator[None]        # Task 2: os.environ.update(FAKE_KEYS | overrides); a None
                                                    # override removes that name; restores every name afterwards
@contextlib.contextmanager
def serve(routes: Mapping, *, date: str = DATE_HEADER) -> Iterator[list[dict]]   # Task 3
def kis_routes(**changes) -> dict                   # Task 5: path -> body, the KIS fixtures below
def upbit_routes(**changes) -> dict                 # Task 6
def okx_routes(**changes) -> dict                   # Task 7
def snap(venue: str, **fields) -> "Snapshot"        # Task 4: an ok snapshot stamped NOW, overridable
```
- `isolated(home)` (tests are zero-argument, so they read the module lists `TOASTS`, `SLEEPS` and `STRAYS`); it imports
  `execution.transport` and `execution.keys` inside the context manager, never at module level, so a broken or
  missing module fails only the tests that use it:
  - Task 1: clears `TOASTS` and `STRAYS`; patches `core.compliance.alerts._toast` with a recorder that appends
    `(title, body)` to `TOASTS` and returns True; removes every name in `KEY_NAMES` from `os.environ` (saved and
    restored on exit: a name that was absent at entry is removed again, whatever the test set); after the `yield`, on
    a normal exit only, `assert not STRAYS, STRAYS` (a passing test that made a
    refused or unrouted send fails; the venue snapshots also let `Refused` and `AssertionError` propagate, E38).
  - Task 2 adds: `REAL_SEND` -> the unpatched `transport._send` (reset to None on exit); `execution.transport._send`
    -> a function that appends to `STRAYS` and raises `Refused("E1 transport send inside the execution suite")`;
    `transport._sleep` -> a no-op recorder appending the seconds to `SLEEPS`; `transport._clock` -> `lambda: NOW`;
    `transport._next_issue_at` -> `None`; `transport._okx_offset_s` -> `None`; `transport._bad_tokens` -> `set()`;
    `execution.keys._ENV_FILE` -> `home / "no-such.env"`. Every patch is restored in reverse order in `finally` (save
    `vars(module).get(name, _MISSING)`, as `tests.macro_acceptance.hermetic` does).
- Signed code (E42): KIS tests pass `F.ctx()` (`tests.compliance_fixtures`: sealed, `code_signed=True`) to
  `kis_inquiry.snapshot`, and `F.ctx(code_signed=False)` or an unsealed `dataclasses.replace(F.ctx())` for the
  refusal. A poll test that needs KIS to send builds a signed temp home with `F.pubkey_at(home / "owner_pubkey.pem")`
  and `F.full_home(home)` (the odds plan's public helpers, 0.6; `full_home` signs the code on disk, so
  `load_context` gives `code_signed=True`; NotRun PENDING without cryptography, as in the compliance suite); every
  other poll test runs unsigned, where KIS sends nothing.
- `serve(routes)` (Task 3) replaces `transport._send` (inside `isolated`, which restores the refusing stub) with a
  router:
  - `routes` maps `(method, path)` to a JSON body (a dict, or a list: Upbit answers with lists), to `(status, body)`,
    to `Seq(answer, answer, ...)` (`class Seq(tuple)` in the fixtures: one answer per call, in order), or to a
    callable `call -> (status, headers, body_bytes)`;
  - each call is recorded as `{"method", "url", "path", "query", "headers", "json_body", "params", "timeout"}`;
  - a call with `params is not None` or `timeout != 10.0`, or an unrouted call, appends to `STRAYS` and raises
    `AssertionError(f"unrouted {method} {path}")` (or `"... params/timeout"`);
  - every answer carries header `{"Date": date}` unless the callable gives its own.
- Response fixtures (bodies as the official examples shape them; KIS and OKX send numbers as strings, Upbit exchange
  numbers as decimal strings and Upbit quotation prices as JSON numbers). Field names follow the research tables;
  fields marked `[assumed]` are not in the research tables (accepted, E1R2-5; open issue 5) and the parsers read them
  through `_field()` so a mismatch fails the snapshot closed:
  - KIS `POST /oauth2/tokenP`: `{"access_token": "test-token-1", "token_type": "Bearer", "expires_in": 86400,
    "access_token_token_expired": "2026-10-25 09:00:00"}`.
  - KIS `.../domestic-stock/v1/trading/inquire-balance` (TTTC8434R): `{"rt_cd": "0", "msg_cd": "KIOK0510", "msg1": "",
    "ctx_area_fk100": "", "ctx_area_nk100": "", "output1": [{"pdno": "005930", "prdt_name": "005930",
    "hldg_qty": "1", "ord_psbl_qty": "1", "pchs_avg_pric": "60000.0000", "pchs_amt": "60000", "prpr": "61000",
    "evlu_amt": "61000", "loan_dt": "", "loan_amt": "0"}], "output2": [{"dnca_tot_amt": "21000",
    "nxdy_excc_amt": "20000", "prvs_rcdl_excc_amt": "20000", "tot_evlu_amt": "81000", "nass_amt": "81000",
    "scts_evlu_amt": "61000", "tot_loan_amt": "0"}]}`.
  - KIS `.../inquire-psbl-rvsecncl` (TTTC0084R): `{"rt_cd": "0", "msg_cd": "", "msg1": "", "output": []}`; an open-order
    row: `{"odno": "0000123456", "orgn_odno": "", "pdno": "005930", "ord_qty": "1", "ord_unpr": "60000",
    "tot_ccld_qty": "0", "psbl_qty": "1", "sll_buy_dvsn_cd": "02", "ord_dvsn_cd": "00", "excg_id_dvsn_cd": "KRX"}`.
  - KIS `.../inquire-daily-ccld` (TTTC0081R): `{"rt_cd": "0", "output1": [{"ord_dt": "20261023", "odno": "0000123455",
    "orgn_odno": "", "sll_buy_dvsn_cd": "02", "pdno": "005930", "ord_qty": "1", "ord_unpr": "61000",
    "ord_tmd": "093000", "tot_ccld_qty": "1", "avg_prvs": "61000", "tot_ccld_amt": "61000", "cncl_yn": "N",
    "rmn_qty": "0", "rjct_qty": "0"}], "output2": {}}`.
  - KIS `.../inquire-account-balance` (CTRP6548R): `{"rt_cd": "0", "output1": [], "output2": {"tot_asst_amt": "81000",
    "nass_tot_amt": "81000", "tot_dncl_amt": "21000", "dncl_amt": "21000", "frcr_evlu_tota": "0",
    "ovrs_stck_evlu_amt1": "0", "thdt_rcvb_amt": "0", "crdt_fncg_amt": "0"}}` (`output1`/`output2` containers
    `[assumed]`).
  - KIS `.../intgr-margin` (TTTC0869R): `{"rt_cd": "0", "output": {"acmga_rt": "20", "acmga_pct100_aptm_rson": "",
    "stck_cash_ord_psbl_amt": "20000", "rcvb_amt": "0"}}` (`output` container `[assumed]`).
  - KIS `.../overseas-stock/v1/trading/inquire-balance` (TTTS3012R): `{"rt_cd": "0", "output1": [{"ovrs_pdno": "AAPL",
    "ovrs_cblc_qty": "1", "ord_psbl_qty": "1", "pchs_avg_pric": "200.0000", "frcr_pchs_amt1": "200",
    "ovrs_stck_evlu_amt": "210", "now_pric2": "210.00000000", "frcr_evlu_pfls_amt": "10", "tr_crcy_cd": "USD",
    "ovrs_excg_cd": "NASD"}], "output2": {"tot_evlu_pfls_amt": "10", "frcr_buy_amt_smtl1": "200"}}`.
  - KIS `.../inquire-nccs` (TTTS3018R): `{"rt_cd": "0", "output": []}`; a row: `{"odno": "0000223456", "pdno": "AAPL",
    "ft_ord_qty": "1", "ft_ord_unpr3": "200", "nccs_qty": "1", "sll_buy_dvsn_cd": "02"}` (row fields `[assumed]`).
  - KIS `.../inquire-ccnl` (TTTS3035R): `{"rt_cd": "0", "output": []}`; a row: `{"ord_dt": "20261023",
    "odno": "0000223455", "orgn_odno": "", "pdno": "AAPL", "ft_ord_qty": "1", "ft_ord_unpr3": "200",
    "ft_ccld_qty": "1", "ft_ccld_unpr3": "200", "ft_ccld_amt3": "200", "nccs_qty": "0", "prcs_stat_name": "",
    "rjct_rson": "", "tr_crcy_cd": "USD", "sll_buy_dvsn_cd": "02"}` (`output`, `ord_dt`, `sll_buy_dvsn_cd`
    `[assumed]`).
  - KIS `.../inquire-present-balance` (CTRP6504R): `{"rt_cd": "0", "output1": [], "output2": [{"crcy_cd": "USD",
    "frcr_dncl_amt_2": "5.00", "frcr_drwg_psbl_amt_1": "5.00", "frst_bltn_exrt": "1390.50"}],
    "output3": {"tot_asst_amt": "0", "tot_dncl_amt": "0", "wdrw_psbl_tot_amt": "0", "frcr_use_psbl_amt": "0",
    "frcr_evlu_tota": "0"}}` (`crcy_cd` `[assumed]`).
  - Upbit `/v1/accounts`: `[{"currency": "KRW", "balance": "20000.0", "locked": "0", "avg_buy_price": "0",
    "avg_buy_price_modified": false, "unit_currency": "KRW"}, {"currency": "BTC", "balance": "0.0001",
    "locked": "0", "avg_buy_price": "100000000", "avg_buy_price_modified": false, "unit_currency": "KRW"}]`.
  - Upbit `/v1/orders/open`: `[]`; a row: `{"uuid": "u-open-1", "side": "bid", "ord_type": "limit",
    "price": "90000000", "state": "wait", "market": "KRW-BTC", "created_at": "2026-10-24T08:55:00+09:00",
    "volume": "0.0001", "remaining_volume": "0.0001", "executed_volume": "0", "trades_count": 0}`.
  - Upbit `/v1/orders/closed`: `[{"uuid": "u-done-1", "side": "bid", "ord_type": "limit", "price": "100000000",
    "state": "done", "market": "KRW-BTC", "created_at": "2026-10-23T10:00:00+09:00", "volume": "0.0001",
    "remaining_volume": "0", "executed_volume": "0.0001", "trades_count": 1}]`.
  - Upbit `/v1/withdraws`: `[]`; a row: `{"type": "withdraw", "uuid": "u-wd-1", "currency": "BTC", "net_type": "BTC",
    "txid": "t1", "state": "DONE", "created_at": "2026-10-23T11:00:00+09:00", "done_at": "2026-10-23T11:10:00+09:00",
    "amount": "0.0001", "fee": "0", "transaction_type": "default"}`.
  - Upbit `/v1/withdraws/coin_addresses`: `[{"currency": "BTC", "net_type": "BTC", "network_name": "Bitcoin",
    "withdraw_address": "bc1qfixtureaddress000000000000000000000", "secondary_address": null,
    "beneficiary_name": null, "beneficiary_company_name": null, "beneficiary_type": "individual",
    "exchange_name": "OKX", "wallet_type": null}]`.
  - Upbit `/v1/deposits`: `[{"type": "deposit", "uuid": "u-dep-1", "currency": "KRW", "net_type": null, "txid": "t0",
    "state": "ACCEPTED", "created_at": "2026-10-22T09:00:00+09:00", "done_at": "2026-10-22T09:01:00+09:00",
    "amount": "20000", "fee": "0", "transaction_type": "default"}]`.
  - Upbit `/v1/api_keys`: `[{"access_key": "test-upbit-access", "expire_at": "2027-05-27T15:17:51+09:00"}]`; a
    variant with no offset, `"2027-05-27T15:17:51"`, which the parser reads as Asia/Seoul (the docs give KST).
  - Upbit `/v1/ticker`: `[{"market": "KRW-BTC", "trade_price": 100000000.0}, {"market": "KRW-USDT",
    "trade_price": 1400.0}]` (other ticker fields omitted).
  - Upbit error body: `{"error": {"name": "out_of_scope", "message": "..."}}` with HTTP 401.
  - OKX `/api/v5/public/time`: `{"code": "0", "msg": "", "data": [{"ts": "1792800000000"}]}` (= NOW in ms).
  - OKX `/api/v5/account/config`: `{"code": "0", "msg": "", "data": [{"acctLv": "1", "autoLoan": false,
    "enableSpotBorrow": false, "spotBorrowAutoRepay": false, "perm": "read_only", "ip": "203.0.113.7",
    "label": "tradegen-e1", "uid": "1", "mainUid": "1", "type": "0", "kycLv": "2", "mgnIsoMode": "automatic",
    "ctIsoMode": "automatic", "opAuth": "0"}]}`.
  - OKX `/api/v5/account/balance`: `{"code": "0", "msg": "", "data": [{"totalEq": "14", "uTime": "1792800000000",
    "details": [{"ccy": "USDT", "eq": "10", "cashBal": "10", "availBal": "10", "frozenBal": "0", "ordFrozen": "0",
    "eqUsd": "10", "liab": "", "interest": "", "autoLendStatus": "off", "autoLendMtAmt": "0",
    "uTime": "1792800000000"}]}]}`.
  - OKX `/api/v5/account/positions`: `{"code": "0", "msg": "", "data": []}`; a row: `{"instType": "SWAP",
    "instId": "BTC-USDT-SWAP", "mgnMode": "cross", "posId": "p1", "posSide": "net", "pos": "1", "availPos": "1",
    "avgPx": "70000", "upl": "0", "lever": "3", "liab": "", "liabCcy": "", "cTime": "1", "uTime": "1"}`.
  - OKX `/api/v5/asset/balances`: `{"code": "0", "msg": "", "data": [{"ccy": "BTC", "bal": "0.0001",
    "frozenBal": "0", "availBal": "0.0001"}]}`.
  - OKX `/api/v5/asset/asset-valuation`: `{"code": "0", "msg": "", "data": [{"totalBal": "14", "ts": "1792800000000",
    "details": {"funding": "7", "trading": "7", "classic": "0", "earn": "0"}}]}`.
  - OKX `/api/v5/finance/savings/balance`: `{"code": "0", "msg": "", "data": []}`; a row: `{"ccy": "USDT", "amt": "5",
    "earnings": "0", "rate": "0.01", "loanAmt": "5", "pendingAmt": "0"}`.
  - OKX `/api/v5/finance/flexible-loan/loan-info`: `{"code": "0", "msg": "", "data": [{"loanData": [],
    "collateralData": [], "loanNotionalUsd": "0"}]}` (every field `[assumed]`: the research has no table).
  - OKX `/api/v5/trade/orders-pending` and `/api/v5/trade/orders-algo-pending`: `{"code": "0", "msg": "", "data": []}`;
    a row: `{"ordId": "o1", "instId": "BTC-USDT", "instType": "SPOT", "side": "buy", "px": "60000", "sz": "0.0001",
    "state": "live", "tdMode": "cash", "cTime": "1"}` (an algo row carries `algoId` in place of `ordId`).
  - OKX `/api/v5/trade/fills`: `{"code": "0", "msg": "", "data": [{"tradeId": "f1", "ordId": "o0", "billId": "b1",
    "instId": "BTC-USDT", "instType": "SPOT", "side": "buy", "fillPx": "70000", "fillSz": "0.0001", "execType": "T",
    "fee": "-0.07", "feeCcy": "USDT", "ts": "1792713600000", "fillTime": "1792713600000"}]}`.
  - OKX `/api/v5/asset/deposit-history`: `{"code": "0", "msg": "", "data": [{"ccy": "USDT", "chain": "USDT-TRC20",
    "amt": "10", "from": "", "to": "", "txId": "x1", "ts": "1792627200000", "state": "2", "depId": "d1"}]}`.
  - OKX `/api/v5/asset/withdrawal-history`: `{"code": "0", "msg": "", "data": []}`; a row: `{"ccy": "BTC",
    "chain": "BTC-Bitcoin", "amt": "0.0001", "ts": "1792627200000", "to": "bc1qfixtureaddress000000000000000000000",
    "tag": "", "txId": "x2", "fee": "0.0001", "feeCcy": "BTC", "state": "2", "wdId": "w1"}`.
  - OKX `/api/v5/market/ticker`: `{"code": "0", "msg": "", "data": [{"instId": "BTC-USDT", "last": "70000",
    "ts": "1792800000000"}]}`.
  - OKX error: `{"code": "50120", "msg": "This API key doesn't have permission to use this function", "data": []}`
    with HTTP 200.

### 3.3 Seams (all module-level, looked up at call time)
`execution.transport._send`, `execution.transport._sleep`, `execution.transport._clock`, `execution.keys._ENV_FILE`,
`core.compliance.alerts._toast`, and for the poller's loop test only `execution.poll._sleep`, `execution.poll.poll_once`
and `execution.poll.datetime` (a fake class whose `now()` returns scripted times). Venue modules call `request` and
never `_send` (a guard enforces it, E36); tests never patch `request`. `transport.requests` is swapped only by the
`_send` test of Task 2 (save/restore).

---

## 4. Guard changes

### 4.1 `tests/acceptance.py` (CRLF, Task 1)
Anchor (tests/acceptance.py:48-54):
```python
def runtime_py() -> list[Path]:
    files: list[Path] = []
    for base in (ROOT / "core", ROOT / "data", ROOT / "ui"):
```
Change only the tuple to `(ROOT / "core", ROOT / "data", ROOT / "ui", ROOT / "execution")`.

Anchor (tests/acceptance.py:178-182):
```python
def test_09_no_account_credentials_requested():
    """Order submission needs an account number. Never ask for one."""
    blob = "\n".join(_read(p) for p in runtime_py())
```
Becomes:
```python
def test_09_no_account_credentials_requested():
    """Order submission needs an account number. Never ask for one. E1's balance inquiry,
    execution/kis_inquiry.py, is the one file that names one; tests/execution_guards.py pins its paths and TR ids."""
    blob = "\n".join(_read(p) for p in runtime_py() if p.relative_to(ROOT).as_posix() != "execution/kis_inquiry.py")
```
The loop below it is unchanged.

### 4.2 `tests/macro_m0_harness.py` (LF, Task 1)
Anchor (tests/macro_m0_harness.py:35-36):
```python
FORBIDDEN_TEXT_CS = ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD")           # an account number implies an order path
FORBIDDEN_PATH_RE = re.compile(r"/uapi/[^\s'\"]*/trading/")           # every KIS trading domain
```
Insert after it:
```python
# E1 (execution spec 8; ruling X6): file-exact exceptions to the TEXT checks only. Every other check (imports, calls,
# mutating HTTP) still runs on these files, and tests/execution_guards.py pins what each may hold.
TEXT_EXCEPTIONS = {
    "execution/kis_inquiry.py": frozenset({"KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD", FORBIDDEN_PATH_RE.pattern}),
    "execution/upbit_inquiry.py": frozenset({"/v1/orders", "/v1/withdraws"}),
}
```
Anchor (tests/macro_m0_harness.py:80-82, inside `_offences`):
```python
    hits = [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CI if n in low]
    hits += [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CS if n in code]
    hits += [f"{rel}: {m.group(0)!r}" for m in FORBIDDEN_PATH_RE.finditer(code)]
```
Becomes:
```python
    skip = TEXT_EXCEPTIONS.get(rel, frozenset())
    hits = [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CI if n in low and n not in skip]
    hits += [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CS if n in code and n not in skip]
    if FORBIDDEN_PATH_RE.pattern not in skip:
        hits += [f"{rel}: {m.group(0)!r}" for m in FORBIDDEN_PATH_RE.finditer(code)]
```
`_yaml_offences` is unchanged (the workflow YAML gets no exception).

### 4.3 `core/ficc/context_log.py` (LF, Task 1)
Anchor (core/ficc/context_log.py:71-73):
```python
ACTING_MODULE_PREFIXES = ("core.quant.", "core.engine.", "core.rules.", "core.calendars", "core.markets",
                          "core.ficc.pit", "core.ficc.contracts", "core.ficc.lag_audit",
                          "core.compliance.", "core.odds.")             # spec 4: the gate and the odds engine act
```
Becomes:
```python
ACTING_MODULE_PREFIXES = ("core.quant.", "core.engine.", "core.rules.", "core.calendars", "core.markets",
                          "core.ficc.pit", "core.ficc.contracts", "core.ficc.lag_audit",
                          "core.compliance.", "core.odds.",             # spec 4: the gate and the odds engine act
                          "execution.")                                 # E1 spec 8: account inquiry acts too
```
No wall-clock call is added to this file.

### 4.4 `tests/run_all.py` (CRLF, Task 1)
- Anchor: the last suite import (tests/run_all.py:50 at `5816d3c`:
  `from tests.compliance_acceptance import tests as compliance_tests  # noqa: E402`; the odds plan adds one after it).
  Add after the last one: `from tests.execution_acceptance import tests as execution_tests  # noqa: E402`.
- Anchor: the last term of `tests()` (tests/run_all.py:67 at `5816d3c`:
  `[(f"compliance/{n}", f) for n, f in compliance_tests()])`). Move the closing `)` and append
  `+ [(f"execution/{n}", f) for n, f in execution_tests()]` as the new last term.
- Anchor: the `--suite` help (tests/run_all.py:113 at `5816d3c`: `help="run one suite: cockpit, engine, ui, quant,
  ficc, expansion, macro, paper, grokteam or compliance"`). Add `execution` as the last name, moving the `or`:
  for example `..., grokteam, compliance, odds or execution`.
- ASCII only, no bare `read_text()` (test_17).

### 4.5 `tests/execution_guards.py` (Task 1 creates; Task 2 appends)
```python
ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "execution"
X = "execution/x.py"                       # the name a synthetic offender is checked under
RAW_BANNED = ("private_key", "seed_phrase", "append_system_entry", "system_halt", "system_disarm",
              "x-simulated-trading", "openapivts")          # any case
KIS_ORDER_WORDS = ("order-cash", "order-credit", "order-rvsecncl", "order-resv", "daytime-order", "/trading/order",
                   "/trading/daytime")                       # raw, lower-cased, in kis_inquiry.py
UPBIT_EXACT = frozenset({"/v1/orders/open", "/v1/orders/closed", "/v1/withdraws", "/v1/withdraws/coin_addresses"})
UPBIT_TOKEN = re.compile(r"(?i)/v1/(?:order|withdraw)[A-Za-z0-9_/\-]*")
KIS_TOKEN = re.compile(r"/uapi/[^\s'\"]*")
KIS_GET_PATHS = frozenset({...})           # the nine GET paths of section 7, written out in the test
KIS_TRS = frozenset({...})                 # the nine TR ids of section 7, written out in the test
TR_SHAPE = re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z]{4}[0-9]{4}[A-Z](?![A-Za-z0-9])")
ORDER_TR = re.compile(r"(?i)[A-Z]{4}[0-9]{4}U")
STDLIB = frozenset({"__future__", "argparse", "base64", "collections.abc", "contextlib", "dataclasses", "datetime",
                    "email.utils", "fcntl", "hashlib", "hmac", "json", "math", "msvcrt", "os", "pathlib", "re", "sys",
                    "threading", "time", "traceback", "types", "typing", "uuid", "zoneinfo"})
VERBS = frozenset({"post", "put", "patch", "delete", "request", "send", "urlopen", "getresponse", "connect",
                   "create_connection"})
TRANSPORT_NAMES = frozenset({"request", "require_keys", "Answer", "InquiryRefused", "InquiryError", "AuthError",
                             "KeyMissing"})  # what other modules may import from execution.transport
CREDENTIAL_NAMES = ("KIS_APP_KEY", "KIS_APP_SECRET", "UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY", "OKX_API_KEY",
                    "OKX_API_SECRET", "OKX_API_PASSPHRASE")
SEND_SOURCE = ("def _send(method, url, *, headers, params, json_body, timeout):\n"     # ast.unparse of the whole
               "    with requests.Session() as session:\n"                               # _send of section 6
               "        session.trust_env = False\n"                                     # (E1R2-11; checked with
               "        resp = session.request(method, url, headers=headers, params=params, json=json_body, "
               "timeout=timeout, allow_redirects=False)\n"                               # the venv's ast.unparse)
               "        return (resp.status_code, resp.headers, resp.content)")
CLOCK_MAIN = "execution/poll.py"           # only the body of its main() reads the clock (E11)
TRANSPORT = "execution/transport.py"       # the only user of requests and urllib.parse
def _sources() -> dict[str, str]           # rel -> raw text of every execution/**/*.py (no __pycache__); asserts
                                           # execution/__init__.py is in it
def _test_sources() -> dict[str, str]      # rel -> raw text of every tests/execution_*.py
def _allowlist_hits(rel, src) -> list[str]
def _verb_hits(rel, src) -> list[str]      # VERBS, the os process calls, sys.modules subscripts
def _clock_hits(rel, src) -> list[str]
def _write_hits(rel, src) -> list[str]
def _raw_hits(rel, src) -> list[str]       # RAW_BANNED
def _token_hits(rel, src) -> list[str]     # the Upbit, KIS-path, TR and order-TR rules of 0.5
def _path_hits(rel, src) -> list[str]      # transport is the only way out, and no rebinding from outside (0.5, E36)
def _process_hits(rel, src) -> list[str]   # a test that would start a process or reload a module (0.2)
```
Reuses `tests.compliance_guards` as `CG`: `CG._imports`, `CG._walk`, `CG._def_hits`, `CG._dynamic_hits`,
`CG._main_block_hits`, `CG._init_hits`, `CG._suite_names`, `CG.CLOCKS`. Every test first proves its checker catches a
synthetic offender (positive control), then asserts the shipped files are clean.

Tests (Task 1 unless marked):
- `test_runtime_py_scans_execution`: `runtime_py()` holds `execution/__init__.py`; with `tests.acceptance.ROOT` and
  `tests.macro_m0_harness.ROOT` swapped (save/restore) to a temp root holding `execution/probe.py` with
  `X = "order-cash"`, `tests.acceptance.test_08_no_broker_order_path()` raises `AssertionError` and
  `tests.macro_m0_harness._offences(<probe>)` reports `'order-cash'`.
- `test_kis_and_upbit_exceptions_are_file_exact`: in the same swapped temp root: `execution/kis_inquiry.py` holding
  `CANO = "x"` and `P = "/uapi/domestic-stock/v1/trading/inquire-balance"` passes `_offences` and test_09;
  `execution/other.py` with the same text fails both; `execution/kis_inquiry.py` holding `"order-cash"` fails test_08
  and `_offences`; `execution/kis_inquiry.py` holding `import ccxt` fails `_offences`; `execution/upbit_inquiry.py`
  holding `"/v1/orders/open"` passes `_offences` but with `CANO = 1` fails it and test_09.
- `test_no_raw_banned_words`, `test_no_def_named_transfer_withdraw_or_deposit_address`,
  `test_imports_stay_on_the_allowlist` (positive controls include `import config`, `from data.krx import kis_client`,
  `import data.krx.kis_client`, `from core.engine import orders`, `from core.quant import garch`,
  `import urllib.request`, `import socket`, `import subprocess`, `import ctypes`, `import shutil`, `import requests`
  in `X`; and `import requests`, `from urllib.parse import quote` pass only under `TRANSPORT`; every `STDLIB` module
  passes), `test_no_dynamic_import`, `test_only_transport_send_calls_requests_request` (the name is kept; since
  E1R2-11 the one allowed call is `session.request(...)` inside `_send`; positive controls:
  `requests.post(u)`, `s.request("GET", u)`, `x.delete()`, `requests.Session().send(p)`, `c.getresponse()`,
  `s.connect(a)`, `os.system("curl")`, `os.popen(c)`, `os.startfile(p)`, `os.execv(a, b)`, `os.spawnl(0, a)`,
  `sys.modules["requests"]` in `X`; `session.request(...)` in a function other than `_send` of `TRANSPORT`, and
  `requests.request(...)` inside `_send` of `TRANSPORT`),
  `test_no_wall_clock_outside_poll_main` (positive controls: `datetime.now(timezone.utc)`, `time.time()`,
  `time.monotonic()`, `from time import time`, a `main()` in `X`; a `datetime.now` inside `main` of `CLOCK_MAIN`,
  including a lambda in it, passes; `time.sleep(1)` passes), `test_every_write_goes_through_checked_target`
  (positive controls: `open(p, "ab")`, `open(p, mode="w")`, `p.open("a")`, `os.replace(a, checked_target(b))`,
  `p.mkdir()`, `p.write_bytes(b"")`, `os.remove(p)`, `shutil.copy(a, b)`; `open(checked_target(p, "x"), "ab")` and
  `open(p, "rb")` pass), `test_init_is_empty_and_main_blocks_are_one_line`, `test_acting_prefix_covers_execution`
  (`CL.is_acting_module("execution.poll")` true, `CL.is_acting_module("execution")` false,
  `CL.static_isolation_report() == []`), `test_only_evidence_names_evidence_path` (positive control:
  `owner.evidence_path()` in `X`; the same in `execution/evidence.py` passes).
- `test_tests_start_no_process` over `_test_sources()` (positive controls: `import subprocess`,
  `from subprocess import run`, `import multiprocessing`, `import runpy`, `sys.executable`, `os.system(c)`,
  `os.popen(c)`, `importlib.reload(m)`; the plain strings `"subprocess"` and `"execution.poll"` pass, so
  `tests/execution_guards.py` itself is clean).
- Harness self-tests: `test_suite_runs_hermetic_in_a_temp_home_with_seams` (the guard is armed, TRADEGEN_HOME is a
  temp dir, no E1 key name is in `os.environ`, `alerts._toast` is the recorder, `STRAYS` is empty; from Task 2 also
  `transport._send` raises `Refused` and records a stray, `REAL_SEND` is the unpatched function and
  `keys._ENV_FILE` is inside the temp home), `test_harness_flags_a_change_to_the_real_homes` (swap `_REAL` to
  stand-ins: a changed file under the folder entry and a changed file entry both fail; with a stand-in `poll.lock`
  held by a second in-process handle, an appended stand-in `inquiry-20261024.jsonl` and a new stand-in
  `inquiry-20261025.jsonl` pass, and any other new file under it fails),
  `test_a_stray_send_fails_a_passing_test` (a wrapped function that appends to `STRAYS` and returns normally fails;
  one that clears it passes), `test_aggregator_skips_missing_and_isolates_broken_modules`.
- `test_suite_is_registered_in_run_all_and_readme`: `run_all.select(run_all.tests(), suite="execution")` holds an
  `execution/execution_guards/` entry; `"execution" in CG._suite_names(text)` for the text of tests/run_all.py and of
  README.md (a substring check proves nothing: README.md:12 already says "execution").
- Task 2 appends: `test_allowlists_are_pinned` (section 7: each frozenset equals the literal set written in the test;
  `transport.HOSTS` equals the three hosts; `("POST", "/oauth2/tokenP") in kis_inquiry.ENDPOINTS`; no POST elsewhere;
  every `TR_IDS` path is a GET path of `ENDPOINTS` and every GET `/uapi/` path has exactly one TR id;
  `("GET", "/api/v5/trade/order") not in okx_inquiry.ENDPOINTS`); `test_kis_strings_are_exact`,
  `test_upbit_strings_are_exact` and `test_no_order_tr_anywhere` (the token rules of 0.5 over every execution file;
  positive controls that must fail: `/v1/withdraws/coin`, `/v1/withdraws/krw`, `/v1/withdraws/chance`, `/v1/orders`,
  `/v1/order`, `/v1/orders/uuids`, `/v1/orders/chance`, `/v1/orders/cancel_and_new` in `execution/upbit_inquiry.py`,
  and `/v1/orders/open` in `X`; `/uapi/overseas-stock/v1/trading/order`, the unlisted
  `/uapi/domestic-stock/v1/trading/inquire-psbl-order`, a bare `/uapi/overseas-stock/v1/trading/` and
  `"/uapi/domestic-stock/v1/trading/" + "order-cash"` in `execution/kis_inquiry.py`, with the overseas order path
  failing both in that file and when also added to a patched copy of its `ENDPOINTS`; `TTTC8434R` in `X`;
  `tttc0012u`, `TTTT1002U` and `ttts1002u` in any file; `TTTC0084X` in `execution/kis_inquiry.py`);
  `test_transport_is_the_only_path` (`_path_hits`; positive controls in `X`: `from execution.transport import _send`,
  `from execution import transport`, `import execution.transport`, `transport._send(...)`,
  `request("kis", "POST", p)`, `request("kis", m, p)`, `from execution import keys`, `keys.read(("KIS_APP_KEY",))`,
  `"KIS_APP_SECRET"`, `requests.get(u)`, `x.requests.Session()`, `HOSTS["kis"]`, `kis_inquiry.ENDPOINTS = s`,
  `t._clock = c`, `setattr(t, n, v)`, `getattr(t, n)`, `getattr(request, "__globals__")`, `getattr(t, "_send")`,
  `vars(t)`, `globals()`, `request.__globals__`, `global _send`, `session.trust_env = False`;
  in `execution/kis_inquiry.py` a second `keys.read(...)` call or `keys._parse(...)`; in `execution/poll.py`
  `transport._send = f`, and `transport._clock = c` outside `main`; in `TRANSPORT` `session.trust_env = False` in a
  function other than `_send`; `transport._clock = c` inside `main` of `execution/poll.py`,
  `session.trust_env = False` inside `_send` of `TRANSPORT` and `getattr(x, "name")` pass); `test_send_is_pinned`
  (`ast.unparse` of the `_send` FunctionDef of transport.py equals `SEND_SOURCE`; positive controls that must fail,
  each a copy of `_send` checked by the same comparison: without `session.trust_env = False`, with
  `session.trust_env = True`, with `allow_redirects=True`, with a `verify=False`, `proxies=p`, `auth=a`, `hooks=h`,
  `stream=True` or `cert=c` keyword, with `requests.request(...)` in place of the session; every `requests` name in
  transport.py is its import, the `requests.Session` in `_send` or `requests.exceptions.ConnectionError`).

---

## 5. `execution/keys.py` (Task 2)
```python
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"     # seam: the suite points it at a missing temp file
_NAME = re.compile(r"[A-Z][A-Z0-9_]*")

class KeyMissing(Exception):
    """A named key is not set; the message names it and never holds a value."""
    def __init__(self, name: str): super().__init__(f"{name} is not set in .env or the environment"); self.name = name

def read(names: Sequence[str]) -> tuple[str, ...]
def _parse(text: str) -> dict[str, str]
def _clean(value: str) -> str
```
- `read(names)`: each name must match `_NAME` (else `ValueError("keys: bad name")`). For each, in order: when
  `name in os.environ`, the environment decides alone: `_clean(os.environ[name])` if non-empty, else `KeyMissing`
  (the file is not read for that name, so `KIS_APP_KEY='<unset>'` is missing even when `.env` holds a key); when the
  name is absent from the environment, the file's value if `_clean` leaves it non-empty, else `KeyMissing`. The file
  is read at most once per call, only when a name is absent from the environment, with `encoding="utf-8-sig"`; a
  missing file is an empty file.
- `_parse(text)`: per line, stripped: skip blank lines and lines starting with `#`; drop a leading `export `; split at
  the first `=`; key stripped; value stripped; a value starting with `'` or `"` ends at its matching quote (the quotes
  are removed; anything after is ignored); an unquoted value drops everything from the first whitespace followed by
  `#`. No expansion. A later line wins.
- `_clean(value)`: strip; `<...>` reads as `""`.
- Never logs, prints or stores a value; returns them only to its callers (`transport`, and `kis_inquiry` for the
  account number, E14; a guard pins both, E36).

---

## 6. `execution/transport.py` (Tasks 2, 3)
```python
HOSTS = MappingProxyType({"kis": "https://openapi.koreainvestment.com:9443",
                          "upbit": "https://api.upbit.com",
                          "okx": "https://www.okx.com"})
CREDENTIALS = MappingProxyType({"kis": ("KIS_APP_KEY", "KIS_APP_SECRET"),
                                "upbit": ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"),
                                "okx": ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")})
KIS_TOKEN_PATH = "/oauth2/tokenP"
TIMEOUT_S = 10.0
RETRY_AFTER_S = 2.0
PACE_S = 0.2                          # sleep after every attempt: at most 5 requests a second
OKX_SKEW_LIMIT_S = 25.0
TOKEN_REUSE_MARGIN_S = 120.0
TOKEN_MIN_GAP_S = 70.0
TOKEN_REISSUE_BLOCK_S = 6 * 3600.0    # KIS returned a token it had called bad: issue nothing for 6 hours
KIS_TOKEN_CODES = frozenset({"EGW00121", "EGW00122", "EGW00123"})
AUTH_CODES = MappingProxyType({
    "kis": frozenset({"EGW00103", "EGW00105", "EGW00205", "EGW00206", "EGW00304"}),
    "upbit": frozenset({"invalid_query_payload", "jwt_verification", "expired_access_key", "nonce_used",
                        "no_authorization_ip", "no_authorization_token", "out_of_scope"}),
    "okx": frozenset({"50030", "50035", "50100", "50101", "50103", "50104", "50105", "50106", "50107", "50110",
                      "50111", "50112", "50113", "50114", "50119", "50120", "50121", "50123"})})
_KEY = re.compile(r"[A-Za-z0-9_\[\]]+")

from execution.keys import KeyMissing  # re-exported: venue modules import it from here (E36)

class InquiryRefused(Exception):      # .reason; raised before any key is read
class InquiryError(Exception):        # the venue or the network failed after the checks
class AuthError(InquiryError):        # an authentication or permission answer (KEY_HEALTH)

@dataclass(frozen=True, kw_only=True)
class Answer:
    body: object = field(repr=False)  # the parsed JSON (a token, balances or addresses: never in a repr)
    server_utc: datetime | None       # from the Date header, aware UTC; None when absent or unreadable
    received_utc: datetime            # _clock() right after _send returned (E39)
    sha256: str                       # hex over the raw body bytes

def request(venue: str, method: str, path: str, params: Sequence[tuple[str, str]] | None = None, *,
            tr_id: str | None = None) -> Answer
def require_keys(venue: str) -> None  # KeyMissing (names only) unless every CREDENTIALS[venue] name is set
def _send(method, url, *, headers, params, json_body, timeout) -> tuple[int, Mapping[str, str], bytes]
_sleep = time.sleep
def _clock() -> datetime              # raises until poll.main sets it (E11)
_next_issue_at: float | None = None   # epoch seconds before which this process issues no KIS token
_okx_offset_s: float | None = None    # OKX server time minus the PC clock at the last public/time answer
_bad_tokens: set[str] = set()         # KIS tokens the venue called invalid or expired in this process
def _rules(venue) -> tuple[frozenset, frozenset, frozenset]   # (ENDPOINTS, TR_IDS or frozenset(), PUBLIC)
def _query(venue, path, params) -> str
def _upbit_jwt(access_key: str, secret_key: str, query: str) -> str
def _okx_timestamp(moment: datetime) -> str                   # "%Y-%m-%dT%H:%M:%S.mmmZ"
def _okx_sign(secret: str, timestamp: str, request_path: str) -> str
def _kis_token() -> str
def _read_token(path: Path, now_epoch: float) -> str | None
def _write_token(path: Path, tmp: Path, token: str, expires_at: float) -> None
def _check_answer(venue, path, status, body_bytes) -> object   # E15; returns the parsed body
```
- `_send` is exactly (E1R2-11; `test_send_is_pinned` compares its `ast.unparse` with `SEND_SOURCE`):
  ```python
  def _send(method, url, *, headers, params, json_body, timeout):
      with requests.Session() as session:
          session.trust_env = False                  # no proxy, CA bundle or .netrc from the environment
          resp = session.request(method, url, headers=headers, params=params, json=json_body, timeout=timeout,
                                 allow_redirects=False)
          return resp.status_code, resp.headers, resp.content
  ```
  A new session per call (the body is read before the session closes, since `stream` stays False); no pooling is
  needed at about 40 calls per 5-minute poll.
- `request` order (E13), all before any key is read:
  1. `venue in HOSTS`, else `InquiryRefused(f"unknown venue {venue!r}")`.
  2. `(method, path) in ENDPOINTS`, else `InquiryRefused(f"{venue}: {method} {path} is not on the E1 allowlist")`.
  3. `method == "GET"` or `(venue, method, path) == ("kis", "POST", KIS_TOKEN_PATH)`, else
     `InquiryRefused(f"{venue}: {method} is not GET")`; the KIS POST also needs `params is None`, else
     `InquiryRefused("kis: the token POST takes no parameters")`.
  4. KIS GET: `tr_id` in `{t for p, t in TR_IDS if p == path}` and `tr_id.endswith("R")`, else
     `InquiryRefused(f"kis: {path} needs its pinned TR id ending in R, got {tr_id!r}")`; any other request with a
     `tr_id` -> `InquiryRefused(f"{venue}: a TR id belongs only to a KIS inquiry")`.
  5. `_query`: a key that does not fully match `_KEY`, a non-str value, or (signed Upbit or OKX) a value that
     `quote(v, safe=",")` changes -> `InquiryRefused(f"{venue}: parameter {key!r} is not plain")`.
  6. Signed OKX (path not in PUBLIC): `_okx_offset_s` is not None and `abs(_okx_offset_s) <= OKX_SKEW_LIMIT_S`, else
     `InquiryRefused("okx: the PC clock offset from OKX time is unknown or above 25 s; OKX requests not sent")`.
- Then credentials and headers (Task 3), rebuilt for every attempt; each `keys.read` names `CREDENTIALS[venue]`:
  - KIS GET: `token = _kis_token()`; `app_key, app_secret = keys.read(CREDENTIALS["kis"])`; headers
    `{"content-type": "application/json; charset=utf-8", "authorization": f"Bearer {token}", "appkey": app_key,
    "appsecret": app_secret, "tr_id": tr_id, "custtype": "P"}`.
  - KIS POST (token): `keys.read(CREDENTIALS["kis"])`; headers `{"content-type": "application/json; charset=utf-8"}`;
    `json_body={"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}`.
  - Upbit signed: `keys.read(CREDENTIALS["upbit"])`; headers
    `{"Authorization": f"Bearer {_upbit_jwt(access, secret, query)}", "Accept": "application/json"}`; a fresh
    `str(uuid.uuid4())` nonce per attempt.
  - OKX signed: `keys.read(CREDENTIALS["okx"])`; `ts = _okx_timestamp(_clock())`; headers `{"OK-ACCESS-KEY": key,
    "OK-ACCESS-SIGN": _okx_sign(secret, ts, path_with_query), "OK-ACCESS-TIMESTAMP": ts, "OK-ACCESS-PASSPHRASE":
    passphrase, "Content-Type": "application/json"}`. Never the demo header.
  - Public (Upbit `/v1/ticker`, OKX `public/time`, `market/ticker`): no keys read, headers `{"Accept":
    "application/json"}`.
- `require_keys(venue)`: `keys.read(CREDENTIALS[venue])` and discard the values (it returns None, never a value);
  `KeyMissing` propagates. `okx_inquiry` calls it before `public/time` (E32).
- Send (Task 3): `url = HOSTS[venue] + path + ("?" + query if query else "")`; `_send(method, url, headers=...,
  params=None, json_body=..., timeout=TIMEOUT_S)`; `received_utc = _clock()`; `_sleep(PACE_S)` after every attempt.
  A GET is retried once, after `_sleep(RETRY_AFTER_S)`, on `requests.exceptions.ConnectionError` (its subclass
  `ConnectTimeout` included), HTTP 429 or status >= 500; a POST never; a `ReadTimeout` is not retried (spec 5 names a
  connection error). After the retry decision, a `ValueError` or `OSError` from `_send` becomes
  `InquiryError(f"{venue} {path}: {type(exc).__name__}") from None` (E15); any other exception propagates unchanged
  (the suite's `Refused` and the router's `AssertionError` included).
- `_upbit_jwt`: header `{"alg": "HS512", "typ": "JWT"}`; payload `{"access_key", "nonce"}` plus `"query_hash":
  sha512(query).hexdigest(), "query_hash_alg": "SHA512"` when `query`; both `json.dumps(..., separators=(",", ":"))`,
  base64url without padding; signature `hmac.new(secret.encode(), signing_input, hashlib.sha512)`; no `exp`.
- `_okx_sign`: `base64.b64encode(hmac.new(secret.encode(), (timestamp + "GET" + request_path).encode(),
  hashlib.sha256).digest()).decode("ascii")`, `request_path` = path plus `?query` when there is one.
- After a successful OKX `public/time`: `_okx_offset_s = int(body["data"][0]["ts"]) / 1000 -
  answer.received_utc.timestamp()`.
- Imports: `import requests` (module level; only here), `from urllib.parse import quote`, `from core import isolation`,
  `from core.isolation import checked_target`, `from execution import keys`, `from execution.keys import KeyMissing`;
  `checked_target` and `keys` are module globals looked up at call time (Task 3's test patches
  `transport.checked_target`). `requests` is used only in `_send` (`requests.Session()`) and as
  `requests.exceptions.ConnectionError`.
- Task 2 creates the constants, `KeyMissing`'s re-export, the three errors, `Answer`, `request` with steps 1-6 only
  (after the checks it fails closed with `InquiryError("transport: sending arrives in Task 3")`, as the compliance
  plan's Task 7 left fail-closed helpers for Task 8), `require_keys`, `_send` in its final form, `_sleep`, `_clock`,
  `_next_issue_at`, `_okx_offset_s`, `_bad_tokens`, `_rules` and `_query`. Task 3 adds `_upbit_jwt`,
  `_okx_timestamp`, `_okx_sign`, `_check_answer`, `_kis_token`, `_read_token`, `_write_token` and the sending half of
  `request` (credentials, headers, send, retry, pacing, answers).
- `_kis_token()` (Task 3): `path = isolation.state_root() / "kis_token.json"`; `now = _clock().timestamp()`;
  a cached token (`_read_token`) not in `_bad_tokens` is returned; else, if `_next_issue_at is not None and now <
  _next_issue_at`, `InquiryError("kis: no token may be issued yet; KIS skipped this poll")`; else
  `checked_target(path.parent, ...)`, `checked_target(path, "KIS token cache")` and
  `tmp = checked_target(path.with_name(f".kis_token.{os.urandom(6).hex()}.tmp"), "KIS token temp")` are computed
  BEFORE the POST; `_next_issue_at = now + TOKEN_MIN_GAP_S`; `answer = request("kis", "POST", KIS_TOKEN_PATH)`;
  token = `answer.body["access_token"]`; when token is in `_bad_tokens`, `_next_issue_at = now +
  TOKEN_REISSUE_BLOCK_S` and `AuthError("kis: KIS issued a token it had called invalid; no token for 6 hours")`;
  expiry `now + float(answer.body.get("expires_in") or 86400)`; `_write_token(path, tmp, token, expiry)`; return
  token.
- `_read_token(path, now_epoch)`: `json.loads(path.read_text(encoding="utf-8"))`; returns `access_token` when it is a
  non-empty str and `now_epoch < float(expires_at) - TOKEN_REUSE_MARGIN_S`; None on anything else.
- `_write_token(path, tmp, token, expires_at)`: `checked_target(path.parent).mkdir(parents=True, exist_ok=True)`;
  write `json.dumps({"access_token": token, "expires_at": expires_at})` to the pre-checked `tmp` opened
  `open(checked_target(tmp, "KIS token temp"), "x", encoding="utf-8")`, fsync,
  `os.replace(checked_target(tmp, ...), checked_target(path, ...))`. An `OSError` here propagates: E38 makes it a
  crash (OUTAGE_CRASH), and the next poll finds no cache and may issue again once `_next_issue_at` has passed.
- On a KIS answer with `msg_cd` in `KIS_TOKEN_CODES`: `_bad_tokens.add(token)` and `InquiryError`.
- The token is never logged, never put in an error text and never returned by `request` except as the POST's body to
  `_kis_token`.

---

## 7. The three allowlists, written out in full (Task 2; each module holds them as module-level frozensets)

`execution/kis_inquiry.py`:
```python
ENDPOINTS = frozenset({
    ("POST", "/oauth2/tokenP"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-balance"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-account-balance"),
    ("GET", "/uapi/domestic-stock/v1/trading/intgr-margin"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-balance"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-nccs"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-ccnl"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-present-balance"),
})
TR_IDS = frozenset({
    ("/uapi/domestic-stock/v1/trading/inquire-balance", "TTTC8434R"),
    ("/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl", "TTTC0084R"),
    ("/uapi/domestic-stock/v1/trading/inquire-daily-ccld", "TTTC0081R"),
    ("/uapi/domestic-stock/v1/trading/inquire-account-balance", "CTRP6548R"),
    ("/uapi/domestic-stock/v1/trading/intgr-margin", "TTTC0869R"),
    ("/uapi/overseas-stock/v1/trading/inquire-balance", "TTTS3012R"),
    ("/uapi/overseas-stock/v1/trading/inquire-nccs", "TTTS3018R"),
    ("/uapi/overseas-stock/v1/trading/inquire-ccnl", "TTTS3035R"),
    ("/uapi/overseas-stock/v1/trading/inquire-present-balance", "CTRP6504R"),
})
PUBLIC = frozenset()
ACCOUNT_NAMES = ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")
```
`execution/upbit_inquiry.py`:
```python
ENDPOINTS = frozenset({
    ("GET", "/v1/accounts"), ("GET", "/v1/orders/open"), ("GET", "/v1/orders/closed"), ("GET", "/v1/withdraws"),
    ("GET", "/v1/withdraws/coin_addresses"), ("GET", "/v1/deposits"), ("GET", "/v1/api_keys"),
    ("GET", "/v1/status/wallet"), ("GET", "/v1/ticker"),
})
PUBLIC = frozenset({"/v1/ticker"})
```
`execution/okx_inquiry.py`:
```python
ENDPOINTS = frozenset({
    ("GET", "/api/v5/account/config"), ("GET", "/api/v5/account/balance"), ("GET", "/api/v5/account/positions"),
    ("GET", "/api/v5/asset/balances"), ("GET", "/api/v5/asset/asset-valuation"),
    ("GET", "/api/v5/finance/savings/balance"), ("GET", "/api/v5/finance/flexible-loan/loan-info"),
    ("GET", "/api/v5/trade/orders-pending"), ("GET", "/api/v5/trade/orders-algo-pending"),
    ("GET", "/api/v5/trade/fills"), ("GET", "/api/v5/asset/deposit-history"),
    ("GET", "/api/v5/asset/withdrawal-history"), ("GET", "/api/v5/public/time"), ("GET", "/api/v5/market/ticker"),
})
PUBLIC = frozenset({"/api/v5/public/time", "/api/v5/market/ticker"})
ALGO_TYPES = ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")
```
Hosts (transport): KIS `https://openapi.koreainvestment.com:9443` (never the mock host), Upbit `https://api.upbit.com`,
OKX `https://www.okx.com`.

---

## 8. `execution/snapshot.py` (Task 4)
```python
VENUES = ("kis", "upbit", "okx")
STALE_AFTER = timedelta(minutes=15)
FLAGS = frozenset({"keys_missing", "code_unsigned", "auth_error", "okx_perm", "okx_acct_lv", "okx_spot_borrow",
                   "okx_auto_loan", "okx_no_ip", "EVENTS", "derivative_position"})   # code_unsigned: KIS only, E42

class FieldError(ValueError):
    """A response field is missing or malformed. args[0] is the field's name, a literal of the parser; never its
    value (E37)."""

@dataclass(frozen=True, kw_only=True)
class Holding:
    units: float                          # total held, locked included
    locked: float = 0.0
    avg_cost: float | None = None         # in the venue's quote currency, where the venue gives one

@dataclass(frozen=True, kw_only=True)
class Order:
    id: str; symbol: str; side: str; units: float; price: float | None = None     # side "buy" | "sell"

@dataclass(frozen=True, kw_only=True)
class Move:                               # a fill, a deposit or a withdrawal
    id: str; symbol: str; counter: str = ""; side: str; units: float              # side buy|sell|in|out

@dataclass(frozen=True, kw_only=True)
class Address:
    currency: str; net_type: str; address: str; secondary_address: str = ""

@dataclass(frozen=True, kw_only=True)
class Snapshot:
    venue: str
    utc: str                              # the poll's now, model.iso_utc
    server_utc: str | None = None         # the venue's time (first Date header; OKX public/time), model.iso_utc
    clock_offset_s: float | None = None   # venue time minus the PC clock at receipt of that answer (E39)
    ok: bool
    error: str | None = None              # names, paths and codes only
    holdings: Mapping[str, Holding] = field(default_factory=dict)
    cash: Mapping[str, float] = field(default_factory=dict)          # fiat currency -> settled amount (E16)
    deposit_krw: float | None = None      # KIS dnca_tot_amt (D16 evidence); None elsewhere
    open_orders: tuple[Order, ...] = ()
    fills: tuple[Move, ...] = ()          # the venue's recent window (E16)
    deposits: tuple[Move, ...] = ()
    withdrawals: tuple[Move, ...] = ()
    withdrawal_addresses: tuple[Address, ...] = ()   # Upbit only
    key_expiry: str | None = None         # Upbit: earliest expire_at, model.iso_utc
    loans: Mapping[str, float] = field(default_factory=dict)         # name -> amount (E26)
    earn: Mapping[str, float] = field(default_factory=dict)          # OKX: name -> amount (E26)
    flags: frozenset = frozenset()        # subset of FLAGS
    prices_krw: Mapping[str, float] = field(default_factory=dict)    # symbol or currency -> KRW price used
    response_sha256: Mapping[str, str] = field(default_factory=dict) # path -> sha256 of the body; the OKX algo
                                          # calls use f"{path}?ordType={t}"; never a KIS query (E37)
    snapshot_sha256: str = ""             # __post_init__: sha256_hex(canonical_json(every other field))

def home() -> Path                        # state_root() / "execution"
def inquiry_path(day: date) -> Path       # home() / f"inquiry-{day:%Y%m%d}.jsonl"; day = a Seoul date (E30)
def failed(venue: str, utc: str, error: str, *, flags=frozenset(), server_utc=None, clock_offset_s=None) -> Snapshot
def dump(snap: Snapshot) -> bytes         # (model.canonical_json(snap) + "\n").encode("utf-8")
def load(obj: dict) -> Snapshot           # rebuilds nested records; ValueError unless snapshot_sha256 recomputes
@contextlib.contextmanager
def exclusive(path: Path)                 # threading.Lock + OS byte lock on checked_target(f"{path}.lock")
def write_lines(path: Path, lines: Sequence[bytes], what: str) -> None   # caller holds exclusive(path)
def append_lines(path: Path, lines: Sequence[bytes], what: str) -> None  # exclusive + write_lines
def read_all(path: Path) -> list[dict]
```
- `Snapshot.__post_init__` sets `snapshot_sha256` as `model.Decision.__post_init__` sets `decision_id`
  (`object.__setattr__`), over `{k: v for k, v in model.jsonable(self).items() if k != "snapshot_sha256"}` (no
  `getattr` with a computed name: the guard of 0.5 bans it); floats must be finite (`model.jsonable` raises otherwise).
- Inquiry line format (every `inquiry-YYYYMMDD.jsonl`): `dump(snap)`, the canonical JSON of every field (keys
  sorted). Example keys:
  `cash, clock_offset_s, deposit_krw, deposits, earn, error, fills, flags, holdings, key_expiry, loans, ok,
  open_orders, prices_krw, response_sha256, server_utc, snapshot_sha256, utc, venue, withdrawal_addresses,
  withdrawals`.
- `exclusive(path)`: `checked_target(path.parent, ...).mkdir(parents=True, exist_ok=True)`; open
  `checked_target(str(path) + ".lock", ...)` with `"a+b"`; Windows `msvcrt.locking(fd, msvcrt.LK_LOCK, 1)` after
  `seek(0)` (retries about 10 s), else `fcntl.flock(LOCK_EX)`; unlock in `finally`.
- `write_lines`: opens `open(checked_target(path, what), "ab")`; when the file is non-empty and does not end in
  `b"\n"`, writes `b"\n"` first (a torn last line stays isolated); writes, flushes, fsyncs.
- `read_all(path)`: every parsed row in file order; a line that does not parse as a JSON object is skipped; missing
  file -> []. The poller reads yesterday's and today's inquiry files with it (E30); a daily file is about 1.3 MB.
- `inquiry_path(day)` only computes a path (it creates nothing); the poller appends with
  `exclusive(home() / "inquiry")` (lock file `inquiry.lock`) around `write_lines(inquiry_path(day), ...)`.

---

## 9. `execution/kis_inquiry.py` (Task 5)
```python
def snapshot(now: datetime, ctx: model.Context) -> Snapshot    # contains venue errors only (E38)
```
- First statement (E42, E1R2-9): unless `model.is_sealed(ctx) and ctx.code_signed is True`, return
  `snapshot.failed("kis", utc, "code not signed", flags=frozenset({"code_unsigned"}))`: no `keys.read`, no request,
  no token. `ctx` is the context `poll_once` loaded at the start of this poll (E24); `from core.compliance import
  model`.
- Then reads `keys.read(ACCOUNT_NAMES)` (E14; the module's only use of `keys`) -> `CANO`, `ACNT_PRDT_CD` (8 and 2
  ASCII digits; otherwise it returns `snapshot.failed("kis", utc, "kis: KIS account number is not 8 + 2 digits")` at
  once, before any request). Imports `request`, `KeyMissing`, `AuthError`, `InquiryRefused`, `InquiryError` from
  `execution.transport`.
- Calls, in order (each `request("kis", "GET", path, params, tr_id=TR)`; dates are Seoul dates `YYYYMMDD`):
  1. domestic `inquire-balance` TTTC8434R: `CANO`, `ACNT_PRDT_CD`, `AFHR_FLPR_YN=N`, `OFL_YN=`, `INQR_DVSN=01`,
     `UNPR_DVSN=01`, `FUND_STTL_ICLD_YN=N`, `FNCG_AMT_AUTO_RDPT_YN=N`, `PRCS_DVSN=00`, `CTX_AREA_FK100=`,
     `CTX_AREA_NK100=`.
  2. domestic `inquire-psbl-rvsecncl` TTTC0084R: `CANO`, `ACNT_PRDT_CD`, `CTX_AREA_FK100=`, `CTX_AREA_NK100=`,
     `INQR_DVSN_1=0`, `INQR_DVSN_2=0`.
  3. domestic `inquire-daily-ccld` TTTC0081R: `CANO`, `ACNT_PRDT_CD`, `INQR_STRT_DT=<yesterday>`,
     `INQR_END_DT=<today>`, `SLL_BUY_DVSN_CD=00`, `INQR_DVSN=00`, `PDNO=`, `CCLD_DVSN=01`, `ORD_GNO_BRNO=`, `ODNO=`,
     `INQR_DVSN_3=00`, `INQR_DVSN_1=`, `EXCG_ID_DVSN_CD=ALL`, `CTX_AREA_FK100=`, `CTX_AREA_NK100=`.
  4. domestic `inquire-account-balance` CTRP6548R: `CANO`, `ACNT_PRDT_CD`, `INQR_DVSN_1=`, `BSPR_BF_DT_APLY_YN=`.
  5. domestic `intgr-margin` TTTC0869R: `CANO`, `ACNT_PRDT_CD`, `CMA_EVLU_AMT_ICLD_YN=N`, `WCRC_FRCR_DVSN_CD=01`,
     `FWEX_CTRT_FRCR_DVSN_CD=01`.
  6. overseas `inquire-balance` TTTS3012R: `CANO`, `ACNT_PRDT_CD`, `OVRS_EXCG_CD=NASD`, `TR_CRCY_CD=USD`,
     `CTX_AREA_FK200=`, `CTX_AREA_NK200=`.
  7. overseas `inquire-nccs` TTTS3018R: `CANO`, `ACNT_PRDT_CD`, `OVRS_EXCG_CD=NASD`, `SORT_SQN=DS`,
     `CTX_AREA_FK200=`, `CTX_AREA_NK200=`.
  8. overseas `inquire-ccnl` TTTS3035R: `CANO`, `ACNT_PRDT_CD`, `PDNO=%`, `ORD_STRT_DT=<today - 2 days>`,
     `ORD_END_DT=<today>`, `SLL_BUY_DVSN=00`, `CCLD_NCCS_DVSN=01`, `OVRS_EXCG_CD=NASD`, `SORT_SQN=DS`, `ORD_DT=`,
     `ORD_GNO_BRNO=`, `ODNO=`, `CTX_AREA_NK200=`, `CTX_AREA_FK200=`.
  9. overseas `inquire-present-balance` CTRP6504R: `CANO`, `ACNT_PRDT_CD`, `WCRC_FRCR_DVSN_CD=02`, `NATN_CD=000`,
     `TR_MKET_CD=00`, `INQR_DVSN_CD=00`.
- Parsing (every field is read through `_field(row, name)`, which raises `snapshot.FieldError(name)` when `row` is not a
  dict or lacks `name`; `_num(row, name)`: `""` -> 0.0, else `float(value.replace(",", ""))`, finite, any failure
  `FieldError(name)`; `_one(body, name)`: a dict, or the first element of a non-empty list, else `FieldError(name)`;
  all make the snapshot not ok):
  - holdings: call 1 `output1` rows with `hldg_qty > 0` -> `Holding(units=hldg_qty, locked=hldg_qty - ord_psbl_qty,
    avg_cost=pchs_avg_pric)`, `prices_krw[pdno] = prpr`; call 6 `output1` rows with `ovrs_cblc_qty > 0` ->
    `Holding(units, locked=units - ord_psbl_qty, avg_cost=pchs_avg_pric)`, `prices_krw[ovrs_pdno] = now_pric2 *
    rate[tr_crcy_cd]` (a holding whose currency has no rate gets no price; positions then fail closed).
  - cash: `{"KRW": _one(call1, "output2").prvs_rcdl_excc_amt}` plus `{crcy_cd: frcr_dncl_amt_2}` for every call 9
    `output2` row; `prices_krw[crcy_cd] = frst_bltn_exrt`.
  - `deposit_krw = _one(call1, "output2").dnca_tot_amt`.
  - open orders: call 2 `output` rows with `psbl_qty > 0` -> `Order(id=odno, symbol=pdno, side="sell" if
    sll_buy_dvsn_cd == "01" else "buy", units=psbl_qty, price=ord_unpr)`; every call 7 `output` row -> `Order(id=odno,
    symbol=pdno, side=..., units=nccs_qty or ft_ord_qty, price=ft_ord_unpr3)`.
  - fills: call 3 `output1` rows with `tot_ccld_qty > 0` -> `Move(id=f"{ord_dt}-{odno}", symbol=pdno, counter="KRW",
    side, units=tot_ccld_qty)`; call 8 `output` rows with `ft_ccld_qty > 0` -> `Move(id=f"{ord_dt}-{odno}",
    symbol=pdno, counter=tr_crcy_cd, side, units=ft_ccld_qty)`.
  - loans (E26): `tot_loan_amt`, `loan_amt` (sum over output1), `crdt_fncg_amt`, `thdt_rcvb_amt`, `rcvb_amt`.
  - `server_utc` from the first answer with a Date header, and `clock_offset_s = (answer.server_utc -
    answer.received_utc).total_seconds()` from that answer (E39); `response_sha256[path] = answer.sha256` (the path
    alone: a KIS query holds the account number).
- Failure (E38), always via `snapshot.failed`, with `path` = the allowlisted path being read when it failed:
  `KeyMissing` -> flags `{"keys_missing"}`, error `f"keys missing: {exc.name}"`; `AuthError` -> flags
  `{"auth_error"}`, error `str(exc)`; `InquiryRefused`, `InquiryError` -> error `str(exc)` (built from names, paths,
  TR ids and codes only); `FieldError` -> error `f"kis: {path}: field {exc.args[0]}"`; `LookupError`, other
  `ValueError`, `TypeError`, `AttributeError`, `ArithmeticError` -> error `f"kis: {path}: {type(exc).__name__}"`
  (never `str(exc)`, E37). Every other exception propagates (a `checked_target` refusal is a crash, spec 10).

---

## 10. `execution/upbit_inquiry.py` (Task 6)
```python
def snapshot(now: datetime) -> Snapshot           # contains venue errors only (E38)
```
- Calls (signed unless public): `/v1/accounts` (no params); `/v1/orders/open` `[("states[]", "wait"), ("states[]",
  "watch"), ("limit", "100")]`; `/v1/orders/closed` `[("states[]", "done"), ("states[]", "cancel"), ("limit",
  "1000")]` (no time: the 7 days before the request); `/v1/withdraws` `[("limit", "100")]`;
  `/v1/withdraws/coin_addresses` (no params); `/v1/deposits` `[("limit", "100")]`; `/v1/api_keys` (no params);
  `/v1/ticker` (public) `[("markets", ",".join(sorted({f"KRW-{c}" for c in held} | {"KRW-USDT"})))]` where `held` is
  every non-KRW currency with units > 0.
- Parsing: `/v1/accounts` KRW -> `cash["KRW"] = balance + locked`; others with `balance + locked > 0` ->
  `Holding(units=balance + locked, locked=locked, avg_cost=avg_buy_price if unit_currency == "KRW" else None)`.
  Open orders -> `Order(id=uuid, symbol=market.split("-")[1], side="buy" if side == "bid" else "sell",
  units=remaining_volume, price=price or None)`. Closed rows with `executed_volume > 0` -> `Move(id=uuid,
  symbol=market.split("-")[1], counter=market.split("-")[0], side, units=executed_volume)`. Withdraws -> `Move(id=uuid,
  symbol=currency, side="out", units=amount)`; deposits -> `Move(id=uuid, symbol=currency, side="in", units=amount)`.
  Addresses -> `Address(currency, net_type, address=withdraw_address, secondary_address=secondary_address or "")`.
  `key_expiry` = the earliest `expire_at` (`datetime.fromisoformat`; a value with no offset is Asia/Seoul, as the
  docs give KST; then `model.iso_utc`) (E21). Ticker: `prices_krw[market.split("-")[1]] = trade_price`. `server_utc`
  and `clock_offset_s` from the first answer with a Date header (E39).
- Failure as section 9 (`"upbit: ..."`). An Upbit 401 with `out_of_scope` (a missing permission) is `auth_error`.

---

## 11. `execution/okx_inquiry.py` (Task 7)
```python
SELF_CHECK = ("perm", "acctLv", "enableSpotBorrow", "autoLoan", "ip")
def self_check(config: Mapping) -> frozenset[str]          # pure: the failed flags
def snapshot(now: datetime, usdt_krw: float | None) -> Snapshot    # contains venue errors only (E38)
```
- `self_check(config)` returns the subset of `{"okx_perm" (perm != "read_only", exact; skeptic correction 1),
  "okx_acct_lv" (acctLv != "1"), "okx_spot_borrow" (enableSpotBorrow is not False), "okx_auto_loan" (autoLoan is not
  False), "okx_no_ip" (ip is not a non-empty str)}`. `perm` values `"read_only,trade"`, `"trade"`, `""`, an unknown
  value and a missing key all fail.
- Calls: `require_keys("okx")` first (a `KeyMissing` fails the snapshot with `keys_missing` before any network call,
  E32); `public/time` (sets `server_utc`, `clock_offset_s = ts / 1000 - answer.received_utc.timestamp()` and
  transport's offset); `account/config` (no params) -> any self-check
  failure returns `snapshot.failed("okx", utc, "okx self-check failed: <comma-separated SELF_CHECK names>",
  flags=<the failed flags>)` and stops; then `account/balance`, `asset/balances`, `account/positions`,
  `asset/asset-valuation` `[("ccy", "USDT")]`, `finance/savings/balance`, `finance/flexible-loan/loan-info`,
  `trade/orders-pending`, `trade/orders-algo-pending` once per `ALGO_TYPES` value `[("ordType", t)]`,
  `trade/fills`, `asset/deposit-history`, `asset/withdrawal-history`, `market/ticker` `[("instId", "BTC-USDT")]`.
- Parsing: holdings per ccy = trading `details[].cashBal` + funding `bal`, locked = trading `frozenBal` + funding
  `frozenBal`, units > 0 only; `cash` is empty (coins are holdings, E16). `prices_krw`: when `usdt_krw` is a positive
  number, `{"USDT": usdt_krw, "USDC": usdt_krw, "BTC": last * usdt_krw}`; other coins get none. Open orders from
  `orders-pending` and every algo call -> `Order(id=ordId or algoId, symbol=instId.split("-")[0], side, units=sz,
  price=px or None)`. Fills -> `Move(id=tradeId, symbol=base, counter=quote, side, units=fillSz)`. Deposits ->
  `Move(id=depId, symbol=ccy, side="in", units=amt)`; withdrawals -> `Move(id=wdId, symbol=ccy, side="out",
  units=amt)`. Loans and earn (E26): `loans[f"liab:{ccy}"]`, `loans[f"flexible_loan:{ccy}"]`,
  `loans[f"margin:{instId}"] = abs(pos)`; `earn[f"savings:{ccy}"]`, `earn["asset_valuation"] = details.earn`,
  `earn[f"auto_lend:{ccy}"] = autoLendMtAmt or 1.0` when `autoLendStatus in ("pending", "active")`. Flags (E25):
  `EVENTS`, `derivative_position`. `server_utc` from `public/time` (`ts` ms). `response_sha256` keys are paths, and
  `f"/api/v5/trade/orders-algo-pending?ordType={t}"` for the seven algo calls.
- Failure as section 9 (`"okx: ..."`).

---

## 12. `execution/positions.py` (Task 8)
```python
def venue_value_krw(snap: Snapshot) -> float | None     # cash at prices_krw (KRW at 1.0) + holdings at prices_krw;
                                                       # None when a currency or symbol has no price
def live_positions(snapshots: Mapping[str, Snapshot], now: datetime) -> model.Positions | None
```
- `live_positions` returns None unless each of `snapshot.VENUES` is present, `ok`, stamped with `0 <= now - utc <=
  STALE_AFTER`, and has a value that is not None and >= 0 (E17).
- Otherwise `model.Positions(equity_krw=sum of the three values, holdings={(venue, symbol): units for every holding},
  shorts={}, exposure={venue: model.Exposure(held_krw=value) for each venue})`; `reservations` and
  `promised_sell_units` stay empty (E2 adds them).
- Valuation per spec 6: KIS domestic at `prpr`, KIS overseas at `now_pric2` times the CTRP6504R rate, Upbit at
  `/v1/ticker`, OKX BTC at OKX BTC-USDT times Upbit KRW-USDT, USDT and USDC at Upbit KRW-USDT; OKX `held_krw`
  includes USDT and USDC.

---

## 13. Compliance changes (Task 9; one task, signed with everything else)

### 13.1 `core/compliance/model.py`
Anchor (core/compliance/model.py:177-178, the end of `Context`):
```python
    exposure: Mapping[str, Exposure]
    ctx_hash: str = ""                                # set by seal_context
```
Becomes:
```python
    exposure: Mapping[str, Exposure]
    live_evidence: frozenset = frozenset()            # E1: live D16 requirements in force (owner.evidence_in_force)
    ctx_hash: str = ""                                # set by seal_context
```
Anchor (core/compliance/model.py:229-235, `seal_context`):
```python
    fields.pop("ctx_hash", None)
    ctx = Context(**fields, ctx_hash=sha256_hex(canonical_json(fields)))
```
Becomes (the docstring stays):
```python
    fields.pop("ctx_hash", None)
    draft = Context(**fields)                         # defaults filled in; an unknown field is still a TypeError
    body = {f.name: getattr(draft, f.name) for f in dataclasses.fields(Context) if f.name != "ctx_hash"}
    ctx = Context(**body, ctx_hash=sha256_hex(canonical_json(body)))
```
Reason: today `seal_context` hashes only the fields it is passed. `F.ctx()` never passes `live_evidence`, but
`test_seal_context_registers_and_hand_built_is_refused` rebuilds the fields from `dataclasses.fields(model.Context)`
(now including `live_evidence`) and asserts `again.ctx_hash == sealed.ctx_hash`; with the old body that is False
(checked in a sandbox), so `--suite compliance` would go red. Hashing every field, defaults included, makes ctx_hash
cover every field as the test's comment says; a NaN still raises `ValueError` in `canonical_json`. Every ctx_hash
value changes once; no test or file pins one (grep of tests/ and core/ at `5816d3c`).

### 13.2 `core/compliance/gate.py`
Anchor (core/compliance/gate.py:307-308, in `_row_check`):
```python
    if row.requires_live:                                              # D16: no owner event satisfies these
        out.append(f"needs live broker evidence (execution spec): {row.id}")
```
Becomes:
```python
    missing = sorted(set(row.requires_live) - ctx.live_evidence)       # D16: only live broker evidence lifts these
    if missing:
        out.append(f"needs live broker evidence: {row.id}: {', '.join(missing)}")
```
Every other gate rule is unchanged (D11 exits, D15, the floor, grey rows).

### 13.3 `core/compliance/owner.py`
- Anchor (core/compliance/owner.py:767-773, `code_files`):
  ```python
      """Sorted (relative POSIX path, sha256) of the D14 code closure (P6): core/compliance/*.py and core/odds/*.py,
      ...
      todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]
  ```
  The docstring's first line names `core/compliance/*.py, core/odds/*.py and execution/*.py,` (the docstring is
  rewrapped to 120 columns: the edited first line would be 130) and the seed line becomes
  `todo = [p for base in (root / "core" / "compliance", root / "core" / "odds", root / "execution") for p in sorted(base.glob("*.py"))]`
  (wrapped to 120 columns).
- Anchor (core/compliance/owner.py:1014-1017, the end of `_context`):
  ```python
      return model.seal_context(
          date=day, active=active, snapshot=snapshot, owner=owner, code_hash=current, code_signed=signed,
          session=model.SessionState(session_id=session_id, armed=session_id in owner.armed_sessions),
          equity_krw=equity, holdings=holdings, shorts=shorts, exposure=exposure)
  ```
  The last argument line becomes `equity_krw=equity, holdings=holdings, shorts=shorts, exposure=exposure,
  live_evidence=_live_evidence(day))`. The internal-error fallback in `load_context` keeps the default (empty).
- Append at the end of owner.py (after `_context`; module-level names resolve at call time):
```python
# --------------------------------------------------------------------------- #
# Live D16 evidence (E1 spec 6 and 8): the pure fold of execution/evidence.jsonl
# --------------------------------------------------------------------------- #
from types import MappingProxyType  # noqa: E402

EVIDENCE_THRESHOLDS_KRW = MappingProxyType({"deposit_krw_10m": 10_000_000.0, "deposit_krw_15m": 15_000_000.0,
                                            "deposit_krw_20m": 20_000_000.0, "cash_krw_30m": 30_000_000.0})
EVIDENCE_KEYS = ("seq", "prev_sha256", "utc", "requirement", "met", "value_krw", "snapshot_sha256")
EVIDENCE_MAX_AGE_DAYS = 7

def evidence_path() -> Path                                # state_root() / "execution" / "evidence.jsonl"
def evidence_chain(lines: list[bytes]) -> tuple[list[dict], str]
def evidence_in_force(lines: list[bytes], today: _dt.date) -> frozenset[str]
def _live_evidence(day: _dt.date) -> frozenset[str]
```
- `evidence_chain(lines)`: `([row, ...], "")` when every line is sound, else `([], f"line {n}: <defect>")`. Line `n`
  (from 1) must: be bytes ending in `b"\n"` with no other `\n` and no `\r`; parse as a JSON object with no duplicate
  key (`_no_duplicates`); equal its own canonical JSON; have exactly the keys `EVIDENCE_KEYS + ("row_sha256",)`; have
  `type(seq) is int and seq == n`; `prev_sha256` equal to the previous row's `row_sha256` (`GENESIS_PREV` first);
  `_utc(utc)`; `requirement in EVIDENCE_THRESHOLDS_KRW`; `type(met) is bool`; `_number(value_krw) and value_krw >= 0`;
  `met == (value_krw >= EVIDENCE_THRESHOLDS_KRW[requirement])`; `_hex64(snapshot_sha256)`; `row_sha256 ==
  sha256_hex(canonical_json({k: obj[k] for k in EVIDENCE_KEYS}))`. Never raises.
- `evidence_in_force(lines, today)` (E18): `frozenset()` when the chain is not sound. Otherwise, with `late[i]` = the
  latest `_seoul_date(utc)` among rows `0..i`, a requirement counts when its latest row is `met`, its own Seoul date
  `on` satisfies `on <= today` and `(today - on).days <= EVIDENCE_MAX_AGE_DAYS`, and the first row of the unbroken run
  of `met` rows (of that requirement) ending at the latest has `late[first] < today`. Never raises (any exception ->
  `frozenset()`).
- `_live_evidence(day)`: `frozenset()` when the file is missing, or reading it raises `OSError` or `RuntimeError`
  (an A0 refusal); else `evidence_in_force(path.read_bytes().splitlines(keepends=True), day)`. It creates nothing.

### 13.4 `tools/signer/sign.py` (lockstep; owner act 5)
- Anchor (tools/signer/sign.py:597-598): `# The D14 code hash: a copy of owner.code_files (P6). core/compliance and
  core/odds .py files, every in-repo file` -> name `core/compliance, core/odds and execution .py files` (rewrap the
  comment block to 120 columns).
- Anchor (tools/signer/sign.py:693): the same seed line as owner.py,
  `todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]` -> the same
  three-base seed line.

### 13.5 Compliance tests (all LF)
Each edit is anchored on the quoted old text (line numbers are hints at `5816d3c`; the follow-up and odds plans
change these files, 0.6). Before Task 9's first edit, `grep -rn "needs live broker evidence (execution spec)" tests/
core/` lists every pinned use of the old reason; each one is changed here or is a drift ruling.
- `tests/compliance_gate.py` (hint :579-582, TQQQ and 252670 under `F.ctx()`), anchor
  `"needs live broker evidence (execution spec): KR-KIS-ETP-LEV" in d.reasons, (symbol, d.reasons)`: the expected
  reason becomes `"needs live broker evidence: KR-KIS-ETP-LEV: deposit_krw_10m"`.
- `tests/compliance_gate.py` (hint :919-923, `test_d16_rows_stay_blocked_with_every_owner_flag_signed`), anchor
  `assert d.reasons == (f"needs live broker evidence (execution spec): {row_id}",), (row_id, d.reasons)`: the expected
  single reason per row becomes, from a mapping in the test: `KR-KIS-SHORT` -> `"needs live broker evidence:
  KR-KIS-SHORT: broker_approval, collateral_105pct"`, `KR-KIS-ETP-LEV` -> `"...: KR-KIS-ETP-LEV: deposit_krw_10m"`,
  `KR-KIS-SINGLE-ETP` -> `"...: KR-KIS-SINGLE-ETP: cash_krw_30m"`, `KR-KIS-KRX-DERIV` -> `"...: KR-KIS-KRX-DERIV:
  broker_approval, deposit_krw_10m, deposit_krw_20m"`, `KR-KIS-ELW` -> `"...: KR-KIS-ELW: deposit_krw_15m"`.
- New test after it, `test_d16_rows_lift_only_on_live_deposit_evidence`: the same state and `every` owner, with
  `live_evidence=frozenset(owner.EVIDENCE_THRESHOLDS_KRW)`: ETP-LEV, SINGLE-ETP and ELW are `ALLOW` with no reason;
  KRX-DERIV is BLOCK `"needs live broker evidence: KR-KIS-KRX-DERIV: broker_approval"`; SHORT is BLOCK `"needs live
  broker evidence: KR-KIS-SHORT: broker_approval, collateral_105pct"`; with only `{"deposit_krw_10m"}`, ELW still
  blocks naming `deposit_krw_15m`.
- `tests/compliance_model.py` (hint :91-95, the `changes` dict of
  `test_seal_context_registers_and_hand_built_is_refused`), anchor its last entry
  `"exposure": {"upbit": model.Exposure(held_krw=1.0)}}`: add `"live_evidence": frozenset({"deposit_krw_10m"})`.
  With 13.1's `seal_context`, the test's `again.ctx_hash == sealed.ctx_hash` holds again.
- `tests/compliance_store.py` (hint :130-140, `test_code_files_is_the_import_closure`), anchor the statement
  `expected = {"core/__init__.py", "core/isolation.py"} | {` and its next line
  `f"core/{sub}/{p.name}" for sub in ("compliance", "odds") for p in (ROOT / "core" / sub).glob("*.py")}`: `expected`
  also takes `| {f"execution/{p.name}" for p in (ROOT / "execution").glob("*.py")}`; the docstring names
  `execution/*.py`; add asserts that no name starts with `core/quant/`, `core/calendars/` or `core/engine/`.
- `tests/compliance_signer.py` (hint :637, `test_code_files_match_owner`; the follow-up rewrites the synthetic tree
  further down the same function), anchor
  `assert {f"core/compliance/{p.name}" for p in (ROOT / "core" / "compliance").glob("*.py")} <= paths, paths`:
  insert after it `assert {f"execution/{p.name}" for p in (ROOT / "execution").glob("*.py")} <= paths, paths`.

---

## 14. `execution/evidence.py` (Task 10)
```python
class EvidenceBroken(Exception):                             # the chain does not verify; nothing appended (E33)
def judge(kis: Snapshot) -> list[tuple[str, bool, float]]    # pure: (requirement, met, value_krw) it can judge
def due(rows: list[dict], requirement: str, met: bool, now: datetime) -> bool   # pure: E1R2-3's append rule
def record(kis: Snapshot, now: datetime) -> list[dict]       # appends the due records; returns them
```
- `judge`: `[]` unless `kis.venue == "kis" and kis.ok`. With `deposit = kis.deposit_krw` (skip the deposit items when
  None): `deposit_krw_10m`, `deposit_krw_15m`, `deposit_krw_20m` are `(item, deposit >= threshold, deposit)`;
  `cash_krw_30m` is `(item, value >= 30M, value)` with `value = deposit + sum(amount * kis.prices_krw[c] for c, amount
  in kis.cash.items() if c != "KRW")`, skipped when a rate is missing. `collateral_105pct` and `broker_approval` are
  never written. Thresholds come from `owner.EVIDENCE_THRESHOLDS_KRW`.
- `record`: under `snapshot.exclusive(owner.evidence_path())`: read the lines, `owner.evidence_chain(lines)`; a defect
  raises `EvidenceBroken(f"evidence.jsonl is broken ({why}); nothing appended")` (`why` names a line number and a
  defect, never a value); a `checked_target` refusal is not caught (a crash, E33); then one new line per judged item
  for which `due(rows, requirement, met, now)` holds (E1R2-3, spec rev 2), in the order of
  `owner.EVIDENCE_THRESHOLDS_KRW`; each new line is `{seq, prev_sha256, utc: model.iso_utc(now), requirement, met,
  value_krw, snapshot_sha256: kis.snapshot_sha256}` plus `row_sha256`, as canonical JSON plus `"\n"`, written with
  `snapshot.write_lines` (nothing is written when no item is due).
- `due(rows, requirement, met, now)`: with `last` = the last row of `rows` (the verified chain) naming `requirement`,
  True when there is none, when `last["met"] != met`, or when the Seoul date of `last["utc"]` is before the Seoul date
  of `now` (the daily heartbeat). `value_krw` alone never makes a record due: the fold reads only `met`, the dates
  and the chain.
- Line format (`evidence.jsonl`):
  `{"met":true,"prev_sha256":"<64 hex>","requirement":"deposit_krw_10m","row_sha256":"<64 hex>","seq":1,"snapshot_sha256":"<64 hex>","utc":"2026-10-24T00:00:00Z","value_krw":21000.0}`.
- Only `evidence.py` writes the file, and only inside a poll holding `poll.lock`.

---

## 15. `execution/checks.py` (Task 11; pure: no clock, no file, no network)
```python
KINDS = ("KEY_HEALTH", "FOREIGN_ORDER", "HOLDINGS_CHANGED", "OKX_CAP", "ADDRESS_LIST", "D15_LIVE",
         "HARD_BLOCK_LIVE", "FLOOR", "DAILY_LOSS", "OUTAGE", "CLOCK_SKEW",     # spec 7's eleven checks
         "EVIDENCE", "NOT_SET")                                              # the poller's own (E33, E43)
VENUE_NAMES = MappingProxyType({"kis": "KIS", "upbit": "Upbit", "okx": "OKX", "all": "TRADEGEN"})
KEY_EXPIRY_WARN = timedelta(days=30)
OUTAGE_POLLS = 3
CLOCK_SKEW_S = 60
STAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")            # model.iso_utc's form
INT_SLOTS = frozenset({"n", "k", "added", "removed", "days", "seconds", "fills", "deposits", "withdrawals"})
TIME_SLOTS = frozenset({"expires", "when", "since"})
ITEM_SLOTS = frozenset({"skipped"})     # a "; "-joined str of NOT_SET_ITEMS (E43)
NOT_SET_ITEMS = frozenset(                # every string not_set can return (15.1)
    {f"{VENUE_NAMES[v]}: keys not in .env" for v in snapshot.VENUES} | {"KIS: code not signed"}
    | {f"{c}: {r}" for c in ("FLOOR", "DAILY_LOSS", "OKX_CAP") for r in ("not set", "no live positions")}
    | {"ADDRESS_LIST: owner log not OK"})
TEXT = MappingProxyType({...})          # text_key -> (kind, level, template); 15.3

@dataclass(frozen=True, kw_only=True)
class Alert:
    venue: str                           # "kis" | "upbit" | "okx" | "all"
    kind: str                            # one of KINDS
    level: str                           # "red" | "amber" | "info" (NOT_SET only, E43) | "clear"
    text_key: str
    slots: Mapping[str, int | str] = field(default_factory=dict)   # ints, ISO times and NOT_SET items only

@dataclass(frozen=True, kw_only=True)
class Prior:
    last_ok: Snapshot | None             # the venue's latest ok snapshot before this poll
    fails: int                           # not-ok polls in a row before this one; an ok snapshot or one flagged
                                         # keys_missing or code_unsigned ends the run (not set, not an outage)

@dataclass(frozen=True, kw_only=True)
class Limits:
    total_loss_floor_krw: float | None   # owner limit_set after D12 (None: not set)
    daily_loss_krw: float | None
    okx_equity_share: float | None       # owner cap_set
    day_start_equity_krw: float | None   # E34
    day_start_utc: str | None

def limits_from(owner: model.OwnerState, day_start: tuple[float, str] | None) -> Limits
def priors(rows: list[dict]) -> dict[str, Prior]                       # inquiry rows (E30), file order
def day_start(rows: list[dict], now: datetime) -> tuple[float, str] | None
def run_checks(prev: Mapping[str, Prior], new: Mapping[str, Snapshot], owner: model.OwnerState, limits: Limits,
               now: datetime) -> list[Alert]
def evaluated(prev: Mapping[str, Prior], new: Mapping[str, Snapshot], owner: model.OwnerState, limits: Limits,
              now: datetime) -> frozenset[tuple[str, str]]             # (venue, kind) whose inputs were there (E19)
def not_set(new: Mapping[str, Snapshot], owner: model.OwnerState, limits: Limits,
            live: model.Positions | None) -> tuple[str, ...]
def due(raw: list[Alert], done: frozenset[tuple[str, str]], rows: list[dict], now: datetime
        ) -> tuple[list[Alert], list[Alert]]                           # (fresh, clears)
def render(alert: Alert) -> str          # TEXT[text_key][2].format(venue=VENUE_NAMES[alert.venue], **alert.slots)
def row(alert: Alert, utc: str) -> dict  # the alerts.jsonl row; sent = level in ("clear", "info")
def verify_row(obj: object) -> bool      # the re-check `--pending` applies to a row read back (16.4)
```

### 15.1 The check table (per venue unless "all"; thresholds exact)
| Check | Fires when | text_key, level | Slots |
|---|---|---|---|
| KEY_HEALTH | `keys_missing` in flags (E31, E1R2-8) | KEY_MISSING amber | - |
| KEY_HEALTH (kis) | `code_unsigned` in flags (E42, E1R2-9) | KIS_UNSIGNED amber | - |
| KEY_HEALTH | `auth_error` in flags | KEY_AUTH red | - |
| KEY_HEALTH (okx) | any of `okx_perm`, `okx_acct_lv`, `okx_spot_borrow`, `okx_auto_loan`, `okx_no_ip` | KEY_OKX_SELF_CHECK red | `n` = how many of the 5 |
| KEY_HEALTH (upbit) | ok and `key_expiry - now <= 30 days` | KEY_EXPIRY amber | `days` = max(0, whole days), `expires` |
| FOREIGN_ORDER | ok and any open order | FOREIGN_ORDER red | `n` |
| HOLDINGS_CHANGED | ok, `prev.last_ok` exists, and a symbol's units differ (`abs(a - b) > 1e-12 * max(1, abs(a), abs(b))`, a symbol absent on one side counts as 0) | HOLDINGS_EXPLAINED amber when every changed symbol is the `symbol` or `counter` of a new fill, or the `symbol` of a new deposit or withdrawal (ids not in `prev.last_ok`); else HOLDINGS_UNEXPLAINED red | `n` changed, `k` unexplained; `fills`, `deposits`, `withdrawals` = how many new fills, deposits and withdrawals name a changed symbol (counts only: spec 7's "lists the fills, deposits and withdrawals that explain it" without amounts) |
| ADDRESS_LIST (upbit) | ok, `prev.last_ok` exists, and the `(currency, address, secondary)` set differs | ADDRESS_CHANGED red | `added`, `removed` |
| ADDRESS_LIST (upbit) | ok, `owner.ok`, and a listed `(currency, address, secondary)` is not `(symbol, address, tag)` of any `owner.addresses` entry | ADDRESS_UNSIGNED red | `n` |
| D15_LIVE (okx) | `okx_spot_borrow` or `okx_auto_loan` in flags | D15_BORROW red | - |
| D15_LIVE | ok and any `loans` value > 0 | D15_LOAN red | `n` |
| D15_LIVE (okx) | ok and any `earn` value > 0 | D15_EARN red | `n` |
| HARD_BLOCK_LIVE (okx) | `EVENTS` in flags | HARD_BLOCK_EVENTS red | - |
| HARD_BLOCK_LIVE (okx) | `derivative_position` in flags | HARD_BLOCK_DERIVATIVE red | - |
| FLOOR (all) | live positions and `total_loss_floor_krw` set and `equity_krw <= floor` | FLOOR red | - |
| DAILY_LOSS (all) | live positions, `daily_loss_krw` set, a day start, and `day_start_equity_krw - equity_krw >= daily_loss_krw` | DAILY_LOSS red | `since` |
| OKX_CAP (okx) | live positions, `okx_equity_share` set, and `exposure["okx"].held_krw > share * equity_krw` | OKX_CAP red | - |
| OUTAGE | not ok, neither `keys_missing` nor `code_unsigned` in flags (KEY_MISSING and KIS_UNSIGNED already say why, E31, E42), and `prev.fails + 1 >= 3` | OUTAGE amber | `n` = `prev.fails + 1`, `when` = the snapshot's utc |
| CLOCK_SKEW | `clock_offset_s` set and `abs(clock_offset_s) > 60` (E39) | CLOCK_SKEW amber | `seconds` = `round(abs(clock_offset_s))` |
- `evaluated` (E19): a `(venue, kind)` pair is in it when that check's inputs were there this poll: KEY_HEALTH,
  FOREIGN_ORDER, D15_LIVE, HARD_BLOCK_LIVE and OUTAGE when the venue's snapshot is ok (for KEY_HEALTH that clears
  KEY_MISSING and KIS_UNSIGNED once the keys are back or the code is signed; for OUTAGE it is the recovery, which
  also clears the venue's OUTAGE_CRASH); HOLDINGS_CHANGED when ok and `prev.last_ok` exists;
  ADDRESS_LIST (upbit) when ok, `prev.last_ok` exists and `owner.ok`; FLOOR and DAILY_LOSS ("all") and OKX_CAP
  ("okx") when live positions exist and the limit is set (DAILY_LOSS also needs a day start); CLOCK_SKEW when
  `clock_offset_s` is set. The poller adds `("kis", "EVIDENCE")` when it ran `evidence.record` (16.2). `("all",
  "NOT_SET")` is never in it (E43).
- Live positions = `positions.live_positions(new, now)`. Unset inputs: the check is skipped and `not_set` names it,
  with no alert. `not_set` returns, in this order: for each venue of `snapshot.VENUES`,
  `f"{VENUE_NAMES[v]}: keys not in .env"` when its snapshot has `keys_missing`, or `"KIS: code not signed"` when it
  has `code_unsigned`; then for FLOOR, DAILY_LOSS and OKX_CAP in that order `"<CHECK>: not set"` when the limit or
  cap is unset, else `"<CHECK>: no live positions"` when live positions are None; then
  `"ADDRESS_LIST: owner log not OK"` when `owner.ok` is False. Every string is in `NOT_SET_ITEMS`. The poll's summary
  line prints it (16.3) and the poller records it once a day as the info row of E43 (E1R2-12).
- E1 only alerts: no check halts, disarms, sells or withdraws.
- The poller adds alerts of its own (16.2): EVIDENCE_BROKEN (venue kis, kind EVIDENCE), OUTAGE_CRASH (each venue,
  kind OUTAGE), the info row NOT_SET (venue all, kind NOT_SET, E43) and the toast-only CRASH_UNLOGGED (E40).

### 15.2 The once-a-day rule (`due`, E19, E1R2-2)
- `today` = the Seoul date of `now`; a row counts for today when the Seoul date of its `utc` is today. A row's key is
  `(row["venue"], row["text_key"])` and its group `(row["venue"], TEXT[row["text_key"]][0])`; a row that is not a
  dict or whose `text_key` is not in TEXT is skipped.
- A raw alert is fresh when (a) no row today has its key `(alert.venue, alert.text_key)`, or that key's latest row
  today is a clear; or (b) its level is red and the latest non-clear row today of its group `(alert.venue,
  alert.kind)` is amber (a level rise fires at once). Each text_key dedupes on its own rows, so an amber text_key never
  hides a red one of the same kind (HOLDINGS_EXPLAINED and HOLDINGS_UNEXPLAINED, D15_LOAN and D15_EARN).
- `fresh` is returned in raw order, stably sorted so that amber and info alerts come before red ones: a red that fired
  is its group's latest row of the poll, so (b) does not fire it again on the next poll.
- For each key whose latest row today is not a clear, whose group is in `done`, and which no raw alert raises now:
  one clear `Alert(venue, kind, level="clear", text_key=<that key's text_key>, slots={})`. A key whose group is not in
  `done` (its venue failed, no live positions, the owner log not OK) keeps its last row, so a flaky poll neither
  clears it nor lets it fire again that day. The NOT_SET info row is never cleared (E43), so it is written once a day.
- Row format (`alerts.jsonl`, canonical JSON plus `"\n"`): `{"kind", "level", "sent", "slots", "text_key", "utc",
  "venue"}`; fresh red and amber rows `sent: false`, clear and info rows `sent: true`; `utc` is the poll's
  `model.iso_utc(now)`.
- `verify_row(obj)`: True only when `obj` is a dict with exactly those seven keys; `text_key in TEXT`; `kind ==
  TEXT[text_key][0]`; `level` is `TEXT[text_key][1]` or `"clear"`; `venue in VENUE_NAMES`; `type(sent) is bool`;
  `utc` fullmatches `STAMP`; `slots` is a dict whose keys are exactly the template's fields other than `venue`
  (`re.findall(r"\{(\w+)\}", template)`; none for a clear row), each `INT_SLOTS` value has `type(v) is int`, each
  `TIME_SLOTS` value is a str that fullmatches `STAMP`, and each `ITEM_SLOTS` value is a non-empty str whose
  `split("; ")` items are all in `NOT_SET_ITEMS`.

### 15.3 The sentence catalogue (`TEXT`: text_key -> (kind, level, template))
```python
"KEY_MISSING": ("KEY_HEALTH", "amber", "{venue} keys are not in .env, so E1 did not read {venue}. If you removed "
                "them on purpose, ignore this; it repeats once a day."),
"KIS_UNSIGNED": ("KEY_HEALTH", "amber", "E1 sent nothing to KIS: the KIS key can also trade, and TRADEGEN's code is "
                 "not signed by you. KIS stays unread until you sign the code hash; this repeats once a day."),
"KEY_AUTH": ("KEY_HEALTH", "red", "{venue} refused E1's key with an authentication or permission error. Check the "
             "key, its permissions and its registered IP."),
"KEY_OKX_SELF_CHECK": ("KEY_HEALTH", "red", "OKX key is not read-only, or the OKX account is not spot mode with "
                       "borrowing off, or the key has no bound IP ({n} of 5 checks failed). OKX inquiry stopped "
                       "for this poll."),
"KEY_EXPIRY": ("KEY_HEALTH", "amber", "An Upbit API key of this account expires in {days} days ({expires}). Issue a "
               "new read-only key before then."),
"FOREIGN_ORDER": ("FOREIGN_ORDER", "red", "{venue} shows {n} open order(s). E1 places no orders: check the {venue} "
                  "app now."),
"HOLDINGS_EXPLAINED": ("HOLDINGS_CHANGED", "amber", "{venue} holdings changed in {n} symbol(s); {fills} new "
                       "fill(s), {deposits} deposit(s) and {withdrawals} withdrawal(s) explain them."),
"HOLDINGS_UNEXPLAINED": ("HOLDINGS_CHANGED", "red", "{venue} holdings changed in {n} symbol(s), {k} of them with "
                         "no new fill, deposit or withdrawal to explain it ({fills} new fill(s), {deposits} "
                         "deposit(s) and {withdrawals} withdrawal(s) explain the rest). Check the {venue} app now."),
"ADDRESS_CHANGED": ("ADDRESS_LIST", "red", "Upbit's registered withdrawal addresses changed: {added} added, "
                    "{removed} removed."),
"ADDRESS_UNSIGNED": ("ADDRESS_LIST", "red", "Upbit lists {n} withdrawal address(es) that no signed "
                     "withdrawal_address entry of yours names."),
"D15_BORROW": ("D15_LIVE", "red", "OKX borrowing is switched on (spot borrow or auto-loan). D15 forbids "
               "borrowing."),
"D15_LOAN": ("D15_LIVE", "red", "{venue} shows {n} loan, credit or margin figure(s) above zero. D15 forbids "
             "borrowing."),
"D15_EARN": ("D15_LIVE", "red", "OKX shows {n} Earn or lending figure(s) above zero. D15 forbids lending."),
"HARD_BLOCK_EVENTS": ("HARD_BLOCK_LIVE", "red", "OKX shows an event-contract (EVENTS) instrument. Prediction "
                      "markets are hard-blocked."),
"HARD_BLOCK_DERIVATIVE": ("HARD_BLOCK_LIVE", "red", "OKX shows a derivative position (swap, futures or option). "
                          "Derivatives are hard-blocked."),
"FLOOR": ("FLOOR", "red", "Live total equity is at or below your total-loss floor. E1 only alerts: nothing was "
          "sold, halted or disarmed."),
"DAILY_LOSS": ("DAILY_LOSS", "red", "Live total equity fell by at least your daily loss limit since the first poll "
               "of today ({since}). E1 only alerts."),
"OKX_CAP": ("OKX_CAP", "red", "OKX holds more than your okx_equity_share cap of live total equity (USDT and USDC "
            "included)."),
"OUTAGE": ("OUTAGE", "amber", "{venue} failed {n} polls in a row (the last at {when})."),
"OUTAGE_CRASH": ("OUTAGE", "amber", "An E1 poll crashed at {when}; {venue} counts as failed for it. The next poll "
                 "runs as usual."),
"CRASH_UNLOGGED": ("OUTAGE", "amber", "An E1 poll crashed at {when} and its alert could not be written. Check "
                   "~/.tradegen/execution on the PC."),
"EVIDENCE_BROKEN": ("EVIDENCE", "amber", "E1's evidence log does not verify, so no D16 evidence is recorded or "
                    "counted. Move ~/.tradegen/execution/evidence.jsonl aside to start a new one."),
"CLOCK_SKEW": ("CLOCK_SKEW", "amber", "This PC's clock is {seconds} seconds away from {venue}'s server time. Fix "
               "the Windows clock."),
"NOT_SET": ("NOT_SET", "info", "Checks skipped (not set): {skipped}."),
```
- Slots: `INT_SLOTS` are ints; `TIME_SLOTS` are `model.iso_utc` strings; `ITEM_SLOTS` hold `"; "`-joined
  `NOT_SET_ITEMS`; `venue` is filled from `VENUE_NAMES` and is never a slot key. CRASH_UNLOGGED (venue "all") is only
  toasted, never written (E40). NOT_SET (venue "all") is only written, never toasted or sent (E43).
- The leak test scans every template and every rendered alert of the check tests (fixtures holding balances such as
  `21000`, `0.0001` and the address `bc1qfixtureaddress000000000000000000000`) for
  `(?i)(₩|\$|krw|usd|usdt|usdc|btc|원)\s*[0-9]|[0-9][0-9,.]*\s*(₩|krw|usd|usdt|usdc|btc|원)` and for any run of 25 or
  more letters and digits; it also asserts no fixture balance string or address appears.

---

## 16. `execution/poll.py` (Task 12)
```python
DEFAULT_INTERVAL_MIN = 5
EXIT_OK, EXIT_LOCKED, EXIT_CRASH = 0, 0, 4           # E1R2-1: a second poller exits 0 with a message (spec 4)
PLACEHOLDER = model.Positions(equity_krw=1.0)        # E24: the only positions load_context ever gets from E1
UNVERIFIED = "An E1 alert row did not verify; read ~/.tradegen/execution/alerts.jsonl on the PC."
_sleep = time.sleep                                  # the loop's seam; reads no clock
_unlogged: set = set()                               # Seoul dates on which CRASH_UNLOGGED was toasted (E40)
def alerts_path() -> Path                            # snapshot.home() / "alerts.jsonl"
def lock_path() -> Path                              # snapshot.home() / "poll.lock"
@contextlib.contextmanager
def held_lock()                                      # yields True when poll.lock was taken, False when held elsewhere
def poll_once(now: datetime) -> dict                 # one poll; returns the redacted summary
def pending(rows: list) -> dict                      # pure: the --pending message
def mark_sent(utc: str) -> int                       # rows marked; idempotent
def main(argv: list[str] | None = None) -> int
if __name__ == "__main__":
    raise SystemExit(main())
```

### 16.1 CLI
- `python -m execution.poll [--once] [--interval-min N] [--pending] [--mark-sent UTC]`; at most one of `--once`,
  `--pending`, `--mark-sent`; `--interval-min` an int 1..60 (default 5) with the loop only; `--mark-sent` takes
  `YYYY-MM-DDTHH:MM:SSZ`. Any argument error prints the reason and returns 4 (argparse's `SystemExit` is caught).
- Loop and `--once`: `main` sets `transport._clock = lambda: datetime.now(timezone.utc)`, takes `poll.lock` (held for
  the process's lifetime: `open(checked_target(lock_path(), ...), "a+b")`, `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)`,
  else `fcntl.flock(LOCK_EX | LOCK_NB)`); a held lock prints `another E1 poller holds poll.lock; exiting` and returns
  `EXIT_LOCKED` (0; E1R2-1), having polled nothing. Each poll reads `now = datetime.now(timezone.utc)` in `main`,
  calls `poll_once(now)` and prints the summary as one JSON line. A crash (any exception out of `poll_once`) prints
  one JSON line `{"crash": type(exc).__name__, "at": "<file name>:<line>"}` from the innermost frame of
  `traceback.extract_tb(exc.__traceback__)` (never `str(exc)`, E37) and runs the crash path (16.2). `--once` returns 0,
  or 4 after a crash. The loop never raises out: after each poll it calls `_sleep(max(0, interval * 60 - elapsed))`,
  with `elapsed` = a second `datetime.now(timezone.utc)` minus `now`; a `KeyboardInterrupt` anywhere in the loop (or
  the end of the task) releases the lock and returns 0.
- `--pending`: reads `alerts.jsonl` with `snapshot.read_all` and no lock (a missing file reads as `[]`; nothing is
  created), prints `json.dumps(pending(rows), ensure_ascii=True)`, returns 0 (4 on an error).
- `--mark-sent UTC`: `mark_sent(utc)`, prints `{"marked": n}`, returns 0 (4 on an error).
- `--pending` and `--mark-sent` never take `poll.lock` and never set the clock.

### 16.2 One poll (`poll_once(now)`; spec 4 data flow)
0. `ctx = owner.load_context(now, PLACEHOLDER)` (E24), before any venue is asked; `today` = the Seoul date of `now`,
   `yesterday = today - 1 day`.
1. `upbit = upbit_inquiry.snapshot(now)`; `okx = okx_inquiry.snapshot(now, upbit.prices_krw.get("USDT") if upbit.ok
   else None)`; `kis = kis_inquiry.snapshot(now, ctx)` (sends nothing unless `ctx.code_signed is True`, E42);
   `new = {"kis": kis, "upbit": upbit, "okx": okx}`.
2. `rows = snapshot.read_all(snapshot.inquiry_path(yesterday)) + snapshot.read_all(snapshot.inquiry_path(today))`
   (E30); `prev = checks.priors(rows)`; `start = checks.day_start(rows, now)`.
3. Under `snapshot.exclusive(snapshot.home() / "inquiry")`: `snapshot.write_lines(snapshot.inquiry_path(today),
   [snapshot.dump(new[v]) for v in snapshot.VENUES], "E1 inquiry log")`.
4. When `kis.ok`: `evidence.record(kis, now)` (only the due records, E18); an `evidence.EvidenceBroken` adds
   `Alert("kis", "EVIDENCE", "amber", "EVIDENCE_BROKEN")`; either way `("kis", "EVIDENCE")` joins `done` (E33). Any
   other exception is a crash.
5. `live = positions.live_positions(new, now)`; `start` defaults to `(live.equity_krw, model.iso_utc(now))` when None
   and `live` exists (E34).
6. `limits = checks.limits_from(ctx.owner, start)`; `raw = checks.run_checks(prev, new, ctx.owner, limits, now)`
   (+ step 4's alert); `done = checks.evaluated(prev, new, ctx.owner, limits, now)` (+ step 4's pair);
   `skipped = checks.not_set(new, ctx.owner, limits, live)`; when `skipped`, `raw` also gets the info alert
   `Alert("all", "NOT_SET", "info", "NOT_SET", {"skipped": "; ".join(skipped)})` (E43).
7. Under `snapshot.exclusive(alerts_path())`: `fresh, clears = checks.due(raw, done,
   snapshot.read_all(alerts_path()), now)`; `snapshot.write_lines(alerts_path(), [canonical rows of
   `checks.row(a, model.iso_utc(now))` for `a` in `fresh + clears`], "E1 alerts")` (red and amber rows
   `sent: false`; clear and info rows `sent: true`).
8. For each fresh alert whose level is red or amber: `alerts._toast(f"TRADEGEN E1 {alert.level}",
   checks.render(alert))`. The info row is never toasted.
9. Return the summary (16.3), with `not_set = skipped`.
- The crash path (any exception out of `poll_once`, `checked_target` refusals included): `main` writes
  `Alert(venue, "OUTAGE", "amber", "OUTAGE_CRASH", {"when": iso_utc(now)})` for each venue through `due` (with an
  empty `done`) under the alerts lock and toasts the fresh ones. If that raises too, `main` toasts
  `checks.render(Alert("all", "OUTAGE", "amber", "CRASH_UNLOGGED", {"when": iso_utc(now)}))` unless today's Seoul
  date is in `_unlogged`, adds the date, prints the second failure the same way, and goes on (E40).

### 16.3 The summary (one JSON line per poll, `ensure_ascii=True`; counts only, no balances)
`{"utc": ..., "venues": {"kis": "ok" | "error", ...}, "errors": {"<venue>": "<error text>"},
"counts": {"<venue>": {"holdings": n, "open_orders": n, "fills": n, "deposits": n, "withdrawals": n,
"addresses": n}}, "evidence": n_records | "broken", "alerts": n_fresh, "not_set": [...]}`. Error texts are E37's;
`n_records` counts this poll's due records (often 0, E18); `n_fresh` counts fresh red and amber alerts only.

### 16.4 `--pending` and `--mark-sent`
- `pending(rows)`: the dict rows with `sent is False` and `level` not `"clear"` or `"info"`, in file order (other rows
  are skipped; an info row never leaves the PC, E43).
  None -> `{"send": false}`. Else `{"send": true, "subject": f"TRADEGEN E1: {n} alert(s), {r} red", "body":
  "\n".join(lines), "utcs": sorted distinct utc}`: a row that passes `checks.verify_row` gives the line
  `f"{kst} {level}: {render}"` (`kst` = its utc as `YYYY-MM-DD HH:MM KST`) and counts in `r` when red; every row that
  fails gives the single line `UNVERIFIED` (once in the body, however many rows fail) and never counts in `r`; `n` is
  the number of rows. `utcs` holds the utc of every listed row that fullmatches `checks.STAMP`. No text from a failed
  row reaches the output: the daily task forwards it off the PC and reads it as its own context (E23).
- `mark_sent(utc)`: a missing `alerts.jsonl` returns 0 and creates nothing. Else, under
  `snapshot.exclusive(alerts_path())`, rewrites `alerts.jsonl` with `sent: true` on every dict row whose `utc == utc`
  and other lines byte for byte (a fresh temp `.alerts.jsonl.<hex>.tmp` opened `"xb"` via `checked_target`, fsync,
  `os.replace` of two `checked_target` paths); returns how many rows changed from false to true (0 on a repeat).

---

## 17. README and run_all (Tasks 1 and 13; README is CRLF)
- Task 1, anchor README.md:816 (the Verification block's `--suite` line, ending `... paper, grokteam or
  compliance`; the odds plan may have changed it): add `execution` as the last suite name, as in 4.4.
- Task 13, anchor README.md:8-13 (the status bullet starting `- **Status (2026-10-23): no order path exists.**`):
  add one bullet after it (wrapped at about 80 columns like its neighbours):
  ```text
  - **Read-only account inquiry (E1).** `python -m execution.poll` reads balances, open orders, fills, deposits and
    withdrawals on KIS, Upbit and OKX through one GET-only transport with frozen allowlists, and only alerts. It
    places no order. A KIS key can also trade: only E1's own code keeps it read-only, so E1 sends nothing to KIS
    until you have signed that code. E1 also reads the KIS account
    (balances, orders, fills), so P0's "KIS is used for read-only quotations only" describes the macro package; the
    P0 read-only guards are narrowed, file by file, for `execution/kis_inquiry.py` and `execution/upbit_inquiry.py`.
  ```
  P0 (README.md:399-401) and the UI disclaimer stay as they are: P0 speaks of "the macro package", and E1 adds no
  order path (spec 8); the bullet above says where the quotation-only sentence stops.
- Task 13, anchor README.md:830 (the cockpit row): the words `no account credentials requested` become
  `no account credentials requested outside` followed by `execution/kis_inquiry.py` in backticks.
- Task 13, anchor the compliance row (README.md:839 at `5816d3c`; the follow-up and odds plans change its count): its
  count becomes the full run's compliance count, and `D15 and D16 refusals` becomes `D15 refusals and D16 refusals
  that only live deposit evidence lifts`.
- Task 13: a suite-table row after the last row (compliance or odds), then the **Total** line from the full run:
  ```text
  | execution | `tests/execution_acceptance.py` over `tests/execution_*.py` | E1 read-only account inquiry, offline: the frozen allowlists and refusals before any key is read, Upbit JWT and OKX signing, the shared KIS token cache, KIS read only under signed code, the OKX read-only self-check, snapshots and fail-closed positions, D16 deposit evidence (written on change and daily) with next-Seoul-day lifting and 7-day expiry, every poll check, alert text without balances or addresses, the poller CLI, and the guards (file-exact KIS and Upbit exceptions) | <n> PASS |
  ```

---

## 18. The daily task prompt (owner gate; Task 14)
The scheduled task `tradegen-compliance-daily` changes only with the owner's explicit yes, through the
scheduled-tasks tool (never by editing its files). The new prompt, in full (the current text read on 2026-10-24 from
`~/.claude/scheduled-tasks/tradegen-compliance-daily/SKILL.md`, with the first paragraph's approval clause, step 2's
second bullet, a new step 5 and the last paragraph changed). Task 14 re-reads the live prompt and shows the owner a
computed diff of the live text against this one, never a prose summary:

````text
Daily TRADEGEN compliance alert. Work in Git Bash (the Bash tool) in C:\Users\whydi\OneDrive\Desktop\TRADEGEN. Never arm, trade, sign, install or edit anything. The owner, Geon Koh (sapientia@korea.ac.kr), approved this task on 2026-10-24 as the standing authority for these self-addressed alerts only (spec decision D5), and approved step 5 (E1 account-inquiry alerts) on <the date of the owner's yes>. While the owner has not yet generated their signing key, --check exits 3 every day and an alert is expected; that is the designed safe default, not a fault.

1. Run this as one Bash command:

out=$(.venv/Scripts/python.exe -m core.compliance.rules --check | tail -n 1; exit "${PIPESTATUS[0]}"); code=$?
printf 'code=%s\nsummary=%s\n' "$code" "$out"
.venv/Scripts/python.exe -m core.compliance.alerts --summary "$out" --code $code; echo "alerts exit $?"

This keeps only the exit code and the last line of --check. Never run --check in any other way, and never read, quote or forward its other lines: they quote draft files, so an edit to a draft can put any text there.

2. Take the one JSON line that alerts printed.
- "send": true: the message is its "subject" and "body", exactly as printed. Send it even when alerts exited 1.
- "send": false: send nothing for steps 3 and 4, and go to step 5.
- No such line (an "error" line, or nothing): the message is the subject and body "TRADEGEN compliance: the alert step failed; run the check by hand."

3. Send the message on exactly two channels, push first:
- an iOS push through the Claude app (the PushNotification tool, status "proactive"; load it with ToolSearch if it is deferred);
- an email to sapientia@korea.ac.kr through the connected Gmail tool (its send-message tool; load it with ToolSearch if it is deferred). If the push failed, add the sentence "The iOS push could not be sent." at the end of the email body.
Never send to any other recipient, and never send anything other than that subject and body.

4. Record each channel, ok if it went out and fail if it did not, with one Bash command per channel. Put the code and the summary line printed in step 1 back exactly as printed; the summary goes between the two EOF lines, and each EOF stands alone at the start of its line:

out=$(cat <<'EOF'
<the summary line printed in step 1>
EOF
); .venv/Scripts/python.exe -m core.compliance.alerts --log push ok --summary "$out" --code <the code printed in step 1>

and the same with email in place of push (and fail in place of ok for a channel that failed). If no email tool is available, record email as fail.

5. E1 account-inquiry alerts. Run this as one Bash command:

.venv/Scripts/python.exe -m execution.poll --pending; echo "pending exit $?"

Never run execution.poll in any other way: never --once, never the poller itself.
- "send": false: stop here.
- "send": true: the message is its "subject" and "body", exactly as printed. Send it on the same two channels as step 3, push first, to the same single recipient, with the same rule for a failed push.
- No such line (an "error" line, or nothing): the message is the subject and body "TRADEGEN E1: the pending-alert step failed; run python -m execution.poll --pending by hand." Send it as in step 3 and mark nothing.
- If at least one of the two channels went out, run one Bash command for each value in the printed "utcs" list:

.venv/Scripts/python.exe -m execution.poll --mark-sent <the utc value>

If both channels failed, mark nothing: the same rows are sent again tomorrow.

Files you may change: only ~/.tradegen/compliance/alerts.jsonl (rows that alerts appends), ~/.tradegen/compliance/owner.jsonl.lock (the empty lock file the first logged alert creates), ~/.tradegen/compliance/snapshots (written by --check when the state is valid), ~/.tradegen/execution/alerts.jsonl (rows that --mark-sent marks sent), ~/.tradegen/execution/alerts.jsonl.lock and the temporary ~/.tradegen/execution/.alerts.jsonl.*.tmp file --mark-sent writes and renames. Nothing else.
````

---

## 19. Owner acts and the first live poll (Task 14; spec 12 verbatim)
1. **Upbit key:** issue a key with 자산조회, 주문조회, 출금조회 and 입금조회 only, never 주문하기, 출금하기 or 포켓관리;
   register your PC's public IPv4 address; put `UPBIT_ACCESS_KEY` and `UPBIT_SECRET_KEY` in `.env`; note in the
   owner's own records which permissions you ticked.
2. **OKX key:** create an API key with the Read permission only, bind your IP, and put `OKX_API_KEY`,
   `OKX_API_SECRET` and `OKX_API_PASSPHRASE` in `.env`.
3. **KIS:** nothing new; E1 uses the existing `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_8` and `KIS_ACCOUNT_PD`.
4. **Task Scheduler:** create a task "TRADEGEN E1 poller", trigger "At log on" of your user, action
   `C:\Users\whydi\OneDrive\Desktop\TRADEGEN\.venv\Scripts\python.exe -m execution.poll`, start in
   `C:\Users\whydi\OneDrive\Desktop\TRADEGEN`, "Run only when user is logged on", and on the Settings tab untick
   "Stop the task if it runs longer than 3 days". Stopping it is one click in Task Scheduler.
5. **Signer:** re-verify your signer copy against the repo's after this change (read the diff, re-hash, re-record),
   then sign the code hash as before (owner act 2 of the main spec).
6. **Daily task:** approve the change to `tradegen-compliance-daily`'s prompt so it also sends E1's unsent alerts.

After act 1 or 2, Claude may run a first live read-only poll (`python -m execution.poll --once`) and report what it
saw, as E1-D2 allows: only after the owner says in chat that the keys are in `.env`, only `--once`, never with the
KEYLESS prefix, and reporting only the summary of 16.3 (venues, counts, ok/error; never a balance, address or key).
It writes the real `~/.tradegen/execution` files, may refresh `~/.tradegen/kis_token.json` (KIS then sends its
KakaoTalk issuance notice), and may show Windows toasts. Expected and not a fault: a venue whose keys are not yet in
`.env` reports `keys missing`, is listed under `not_set` and raises one amber KEY_MISSING a day (E31, E1R2-8); and
until the owner has signed the code hash (main-spec owner acts 1 and 2, then E1 owner act 5) KIS reports
`code not signed`, sends nothing and raises one amber KIS_UNSIGNED a day (E42, E1R2-9). In that case the first live
KIS read waits: Claude runs one more `--once` only after the owner says in chat that the code is signed, under the
same rules. Two live answers stop the plan and ask the owner instead of a fix (never a loosening): the OKX
self-check failing on `okx_auto_loan` with `acctLv == "1"` (a spot-mode key; E1R2-6, open issue 6), and the KIS
overseas calls failing because the overseas service is not enabled on the account (E1R2-7, open issue 7). Any other
field mismatch with a live answer, a field marked `[assumed]` included, fails that venue closed; it is recorded in
the ledger and fixed in a follow-up task under the same rules (E1R2-5, open issue 5).

---

## 20. Open issues, all ruled on 2026-10-25 (E1R2-1 to E1R2-12; the header lists the same)
Each item was open after the critic round; the controller ruled every one, and the tasks implement the ruling. The
numbers are kept, so "open issue N" in a task or in section 19 means item N here.
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
