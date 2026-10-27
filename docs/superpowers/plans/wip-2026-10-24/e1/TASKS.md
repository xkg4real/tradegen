# E1 plan: task list (scope of each task; the drafter writes the full task text)

Spec = `docs/superpowers/specs/2026-10-24-e1-account-inquiry-design.md` rev 1; "5 KIS" means spec section 5, its KIS
part. E<n> are the plan decisions of CONTRACT section 1 (E1-E9 restate rulings X1-X9; E1-E43 in all). "C<n>" is a
CONTRACT section. E1R2-<n> are the controller's round-2 rulings of 2026-10-25, already folded into the contract; they
rule every open issue of C20, and E1R2-3, E1R2-4 and E1R2-9 are "spec rev 2" items the header lists for the owner.
Every task obeys C0 (Global rules), runs the QUANTGEN overlap check before every test command, uses the KEYLESS
prefix on every `--suite` or full run, restores `qa/acceptance_results.json` after every `--suite` run (Task 13
commits it once), and commits once with the trailer naming the model that wrote the commit. Every edit of an
existing file starts by re-reading it and applying the DRIFT RULE (C0.6): the anchor is the quoted old text, a line
number only a hint. No test starts a process or reloads an execution module (C0.2).

Per-step test commands: `.venv/Scripts/python.exe -m tests.execution_acceptance <module>/<test>` (one test) or
`.venv/Scripts/python.exe -m tests.execution_acceptance <module>/` (one module); one suite:
`<KEYLESS> .venv/Scripts/python.exe tests/run_all.py --suite execution; echo "exit $?"; git checkout -- qa/acceptance_results.json`.

## Task 1: Branch, ledger, package skeleton, execution suite, guard widening (spec 4, 8 "Read-only guards", 9 "Guards"; E1, E2, E6, E8, E28, E29, E35)
- `git switch -c e1-account-inquiry` from an up-to-date, clean main that already holds the compliance follow-up and
  the odds plan (X1). Stop if either has not merged.
- Create the execution ledger `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (LF; a title,
  the branch, the main it was cut from, and empty "Drift rulings", "Deferred minors" and "Runs" sections), so every
  later drift ruling has a place (E35).
- Create `execution/__init__.py`, 0 bytes.
- `tests/acceptance.py` (CRLF, Edit tool): `runtime_py()` adds `ROOT / "execution"`; test_09 skips exactly
  `execution/kis_inquiry.py` (C4.1). Check every caller of `runtime_py` still passes: test_08, test_09, test_16,
  test_18, and T-RO-01 through `_scan_files`.
- `tests/macro_m0_harness.py` (LF): `TEXT_EXCEPTIONS` after `FORBIDDEN_PATH_RE`, and the three `hits` lines of
  `_offences` honour it for the text checks only (C4.2).
- `core/ficc/context_log.py` (LF): `ACTING_MODULE_PREFIXES` gains `"execution."` (C4.3); no clock call added.
- Create `tests/execution_acceptance.py` (C3.1: lazy import of the fixtures inside `_wrap`, `_poller_running`,
  `_real_listing(paths_only)` with the file entry and the running-poller mode) and `tests/execution_fixtures.py` with
  `NOW`, `DATE_HEADER`, `FAKE_KEYS`, `KEY_NAMES`, `Refused`, `TOASTS`, `SLEEPS`, `STRAYS`, `REAL_SEND` and the Task 1
  part of `isolated()` (toast recorder, key names scrubbed from `os.environ`, the stray check on a normal exit; no
  module-level import of `execution`) (C3.2).
- Create `tests/execution_guards.py` with every Task 1 test of C4.5: the `runtime_py` positive control (swapped
  `ROOT`s, a synthetic `execution/probe.py`), the file-exact exception controls, raw bans, def-name ban, the explicit
  stdlib import allowlist (positive controls `import config`, `from data.krx import kis_client`,
  `from core.engine import orders`, `import subprocess`, `import ctypes`, `import requests` outside transport, ...),
  dynamic imports, the widened verb and process-call ban, wall clock outside `poll.main`, writes via `checked_target`,
  0-byte `__init__.py` and one-line `__main__` blocks, the acting prefix (`is_acting_module`,
  `static_isolation_report() == []`), `test_only_evidence_names_evidence_path`, `test_tests_start_no_process` over
  `tests/execution_*.py`, the harness self-tests (hermetic, temp home, scrubbed keys, toast recorder, the real-home
  watch with a file entry and a stand-in running poller, which ignores a new daily `inquiry-<YYYYMMDD>.jsonl` and
  nothing else, `test_a_stray_send_fails_a_passing_test`, the aggregator's skip and isolation), and the registration
  test through `CG._suite_names`. Each guard first catches a synthetic offender.
- `tests/run_all.py` (CRLF): import, `tests()` term and `--suite` help (C4.4). `README.md` (CRLF), anchor the
  Verification block's `--suite` line (hint :816): the suite list gains `execution` (C17). If
  `tests/compliance_guards.py` still pins the literal `"paper, grokteam or compliance"` (the follow-up was to loosen
  it, X1), or has no `_suite_names`, stop and rule. Also check now that `tests/compliance_fixtures.py` exports
  `pubkey_at` and `full_home` (moved public by the odds plan; Tasks 5 and 12 need them, C0.6, C3.2); if not, stop
  and rule.
- Files: create `execution/__init__.py`, `tests/execution_acceptance.py`, `tests/execution_fixtures.py`,
  `tests/execution_guards.py`, the ledger; modify `tests/acceptance.py` (CRLF), `tests/macro_m0_harness.py`,
  `core/ficc/context_log.py`, `tests/run_all.py` (CRLF), `README.md` (CRLF).
- Verify: `-m tests.execution_acceptance execution_guards/` all pass; the T-RO-01 one-liner of C0.3 prints
  `T-RO-01 ok`; `<KEYLESS> --suite cockpit` and `<KEYLESS> --suite compliance` stay green (restore the results file
  after each); `git diff --cached --stat` equals its `--ignore-cr-at-eol` form.

## Task 2: keys.py, the allowlists and the refusal order (spec 5 "The choke point" steps 1-3, the three endpoint tables; E3, E10, E12, E13, E27, E28, E36; E1R2-11)
- `execution/keys.py` complete (C5): a name present in the environment decides alone.
- `execution/transport.py`, the checking half (C6): hosts, `CREDENTIALS`, constants, errors (`KeyMissing`
  re-exported), `Answer`, `_rules`, `_query`, `require_keys`, refusal steps 1-6 of `request` (the KIS POST takes no
  parameters), `_send` in its final pinned form (one `requests.Session()` with `trust_env = False`, one
  `session.request(..., allow_redirects=False)`; E1R2-11), `_sleep`, `_clock`, `_next_issue_at`, `_okx_offset_s`,
  `_bad_tokens`.
  After the checks `request` fails closed with `InquiryError("transport: sending arrives in Task 3")`; the signing
  helpers, `_check_answer` and the token cache come in Task 3.
- `execution/kis_inquiry.py`, `execution/upbit_inquiry.py`, `execution/okx_inquiry.py`: docstring plus the C7
  constants only (`ENDPOINTS`, `TR_IDS`, `PUBLIC`, `ACCOUNT_NAMES`, `ALGO_TYPES`); the docstrings mention no
  `/uapi/` or `/v1/order...` text outside the exact strings (the token rules read docstrings too).
- `tests/execution_fixtures.py`: the Task 2 part of `isolated()` (lazy imports; `REAL_SEND`; refusing `_send` that
  records a stray; `_sleep` recorder; fixed `_clock`; reset `_next_issue_at`, `_okx_offset_s`, `_bad_tokens`;
  `keys._ENV_FILE` in the temp home), `fake_keys()`.
- `tests/execution_keys.py`: an absent name falls back to the file; `export `, quotes, full-line comments, an inline
  ` #` comment on an unquoted value, a BOM, CRLF lines, no expansion; blank and `<placeholder>` values and a missing
  file raise `KeyMissing` whose message names the key and holds no value; env `KIS_APP_KEY='<unset>'` with a temp
  `.env` holding `KIS_APP_KEY=file-value` raises `KeyMissing` (the env decides alone, so KEYLESS is keyless); only the
  requested names come back; a bad name is refused; the suite never reads the repo `.env` (`keys._ENV_FILE` is inside
  the temp home); the default `_ENV_FILE` is `parents[1] / ".env"`, checked from the source text (never by a reload).
- `tests/execution_transport.py`:
  - every refusal of C6 steps 1-6 raises `InquiryRefused` before any key is read (`keys.read` patched to raise
    `AssertionError`), with at least: unknown venue; KIS order path with `TTTC0802U`; KIS POST to an inquiry path;
    the token POST with parameters; `TTTC0802U` and the mock TR `VTTC8434R` on the real balance path; a TR pinned to
    another path; no TR; the mock host written into the path; Upbit `POST /v1/orders`, `DELETE /v1/orders/open`,
    `GET /v1/orders`, `GET /v1/order`, `GET /v1/deposits/generate_coin_address`, a `tr_id` on Upbit; OKX `GET` and
    `POST /api/v5/trade/order`, `GET /api/v5/asset/deposit-address`; a lowercase method; a bad parameter key; a signed
    Upbit value that quoting changes; a signed OKX call with no offset and with a 26 s offset;
  - the not-GET rule on its own: `upbit_inquiry.ENDPOINTS` patched to hold `("DELETE", "/v1/orders/open")` is still
    refused (`"upbit: DELETE is not GET"`);
  - the R rule on its own: `kis_inquiry.TR_IDS` patched to add
    `("/uapi/domestic-stock/v1/trading/inquire-balance", "TTTC8434U")` still refuses `tr_id="TTTC8434U"` with the
    "needs its pinned TR id ending in R" reason, `keys.read` patched to raise;
  - `require_keys`: `KeyMissing` naming the first missing name; with `fake_keys()` it returns None and nothing else;
  - `_send` for real: `REAL_SEND` called with `transport.requests` swapped (save/restore) for
    `types.SimpleNamespace(Session=FakeSession, exceptions=requests.exceptions)`, where `FakeSession` is a context
    manager whose `request` records its arguments and the session's `trust_env` at that moment; exactly one session
    per call, `trust_env is False` when `request` runs, `allow_redirects is False`, `timeout == 10.0`,
    `params is None`, the URL, method, headers and json unchanged, the session closed (`__exit__` ran) when `_send`
    returns, and the returned tuple is `(status_code, headers, content)` of its fake response;
  - `trust_env` off does what E1R2-11 wants, offline: a real `requests.Session()` with `trust_env = False`, with
    `HTTPS_PROXY`, `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` set in `os.environ` (save/restore), gives
    `merge_environment_settings(url, {}, None, None, None)` with no proxies and `verify is True`, while the same call
    with `trust_env = True` picks the proxy up (the control); nothing is sent (checked against requests 2.34.2 in
    `e1/sandbox_round2/send_probe.py`);
  - the probe: under the suite, an unpatched `transport._send` raises `Refused` and records one stray (the test
    asserts it, then clears `STRAYS`).
- `tests/execution_guards.py` appends `test_allowlists_are_pinned`, `test_kis_strings_are_exact`,
  `test_upbit_strings_are_exact`, `test_no_order_tr_anywhere`, `test_transport_is_the_only_path` and
  `test_send_is_pinned` (C4.5, C7), each with the must-fail controls listed there; `test_send_is_pinned` compares the
  whole `_send` with `SEND_SOURCE` (a copy without `trust_env = False`, with `allow_redirects=True` or with any extra
  keyword fails).
- Files: create `execution/keys.py`, `execution/transport.py`, `execution/kis_inquiry.py`,
  `execution/upbit_inquiry.py`, `execution/okx_inquiry.py`, `tests/execution_keys.py`, `tests/execution_transport.py`;
  modify `tests/execution_fixtures.py`, `tests/execution_guards.py`.
- Verify: the three modules (`execution_guards`, `execution_keys`, `execution_transport`) pass; T-RO-01 one-liner;
  `<KEYLESS> --suite cockpit` (test_08, test_09 now see the venue constants).

## Task 3: Signing, sending, answers and the KIS token cache (spec 5 steps 3-5, Upbit and OKX signing, KIS "Token"; ledger "KIS token burnt on refusal"; E3, E11, E12, E15, E39)
- `execution/transport.py`, the sending half (C6): credentials and headers per venue (each `keys.read` names
  `CREDENTIALS[venue]`), `_upbit_jwt`, `_okx_timestamp`, `_okx_sign`, the OKX offset from `public/time` at receipt,
  sending with `received_utc`, retry and pacing (a GET once more on `ConnectionError`, 429 or 5xx; never on a
  `ReadTimeout`; a POST never), the `(ValueError, OSError) -> InquiryError(type name) from None` wrapping,
  `_check_answer`; then `_kis_token`, `_read_token`, `_write_token(path, tmp, ...)`, the `_bad_tokens` rule and the
  6-hour block on a re-issued bad token.
- `tests/execution_fixtures.py`: `serve()` (records `params` and `timeout`; a call with params, a timeout other than
  10.0 or no route records a stray and raises).
- Tests in `tests/execution_transport.py`:
  - Upbit JWT: HS512 over base64url header and payload, verified with the fake secret; `query_hash` is the SHA512 of
    the exact query in the sent URL (`states[]` repeated, brackets unencoded); a fresh nonce per attempt; no `exp`; no
    `query_hash` without parameters;
  - OKX: headers, ISO timestamp with milliseconds and `Z`, signature re-derived in the test over
    `timestamp + "GET" + path?query`; the offset recorded from `public/time` at receipt; no demo header;
  - public endpoints read no key;
  - retry: a GET once more after `_sleep(2.0)` on 503, 429, `requests.exceptions.ConnectionError` and
    `ConnectTimeout`, never on 400 or `ReadTimeout`; `_sleep(0.2)` after every attempt; a `requests` exception and a
    `UnicodeEncodeError` raised by the stub become `InquiryError` whose text is `"<venue> <path>: <TypeName>"` (no URL,
    no exception text); a `Refused` and an `AssertionError` propagate unchanged;
  - answers: HTTP 401 and 403, Upbit `out_of_scope`, OKX `50120` and `50123` on HTTP 200 raise `AuthError`; KIS
    `rt_cd != "0"` and OKX `code != "0"` raise `InquiryError` naming venue, path and code; a 3xx is an error; `Answer`
    carries the parsed body, the Date header as aware UTC, `received_utc` and the body's sha256; `repr(answer)` holds
    no body;
  - the token cache: a cached token is reused while `now < expires_at - 120` (and the token POST is not called); an
    expired or missing cache issues one; the cache file and the temp file pass `checked_target` BEFORE the POST
    (`transport.checked_target` patched to raise: `_send` never called, and the `RuntimeError` propagates); the temp
    path checked before the POST is the one written; a second issue inside 70 s raises `InquiryError` with no POST;
    the token POST is never retried (a `ConnectionError` gives exactly one call); `EGW00123` marks the token bad, the
    next call issues a fresh one only after 70 s; a re-issued token that is already bad raises `AuthError` and no
    further POST happens for 6 hours (clock advanced 6 h - 1 s and 6 h); the write is atomic (no temp file left;
    `os.replace`); the token never appears in an error text or a snapshot;
  - KIS GET headers carry `custtype: P`, the pinned `tr_id`, the bearer token and the app key (moved here from Task 2:
    a KIS GET needs the token cache);
  - the file and format are shared with `data.krx.kis_client` both ways: patch `kis_client._TOKEN_PATH` into the temp
    home (save/restore), then `assert kis_client._TOKEN_PATH.is_relative_to(home)` immediately before
    `object.__new__(KISClient)._store_token(...)` and E1's `_read_token`; E1's `_write_token` then
    `object.__new__(KISClient)._cached_token()`, with an `expires_at` relative to the real clock for kis_client's
    check; never construct `KISClient()` normally and never call `.token()`; E1 never imports kis_client (guard);
  - the probe: a public `request("upbit", "GET", "/v1/ticker", [("markets", "KRW-BTC")])` raises `Refused` under the
    suite (one stray, asserted and cleared).
- Files: modify `execution/transport.py`, `tests/execution_transport.py`, `tests/execution_fixtures.py`.
- Verify: `-m tests.execution_acceptance execution_transport/` and `execution_guards/`.

## Task 4: Snapshot records and JSONL helpers (spec 4 "State files", 6 "Snapshot"; E4, E16, E30, E37; E1R2-4)
- `execution/snapshot.py` complete (C8): the records (`clock_offset_s` included; `FLAGS` with `code_unsigned`),
  `FieldError`, `Snapshot.__post_init__` hash, `home`, `inquiry_path(day)`, `failed`, `dump`, `load`, `exclusive`,
  `write_lines`, `append_lines`, `read_all`. No `read_since`: the daily files of E30 (E1R2-4) replace it.
- `tests/execution_fixtures.py`: `snap(venue, **fields)`.
- `tests/execution_snapshot.py`: `snapshot_sha256` is stable and changes with every field; NaN and inf refused;
  `dump` is canonical JSON plus `\n` with sorted keys; `load(json.loads(dump(s))) == s`; a tampered row is
  `ValueError`; `failed()` gives `ok: false` with names-only error text; `FieldError("x").args[0] == "x"`; `exclusive`
  serialises two threads; `append_lines` isolates a torn last line; `read_all` returns the rows in file order and
  skips an unreadable line; a missing file reads as `[]`; `inquiry_path(date(2026, 10, 24)).name ==
  "inquiry-20261024.jsonl"` under `home()`; two days written under `exclusive(home() / "inquiry")` land in two files
  with one lock file `inquiry.lock`; a hard-linked or junction target is refused by `checked_target` and nothing is
  written; computing a path creates nothing.
- Files: create `execution/snapshot.py`, `tests/execution_snapshot.py`; modify `tests/execution_fixtures.py`.
- Verify: `-m tests.execution_acceptance execution_snapshot/` and `execution_guards/`.

## Task 5: KIS inquiry (spec 5 KIS table and bullets, 6 KIS valuation; E14, E16, E17, E26, E37, E38, E42; E1R2-9)
- `kis_inquiry.snapshot(now, ctx)` (C9), whose first statement is the signed-code gate (E42);
  `tests/execution_fixtures.py`: the KIS response dicts and `kis_routes()` (C3.2).
- `tests/execution_kis.py`, every ok case with `ctx = F.ctx()` (sealed, `code_signed=True`):
  - the gate (E1R2-9): with `F.ctx(code_signed=False)`, an unsealed `dataclasses.replace(F.ctx())`, and `None`, with
    `fake_keys()`, every KIS route served and `keys.read` patched to raise `AssertionError`, the snapshot is
    `ok: false`, error exactly `"code not signed"`, flags `{"code_unsigned"}`, and no call reached the router (the
    token POST included) and no key was read; `F.ctx()` with the same routes sends;
  - the full fixture gives the expected holdings (domestic and overseas), `cash["KRW"]` = the D+2
    `prvs_rcdl_excc_amt`, `cash["USD"]`, `deposit_krw` = `dnca_tot_amt`, `prices_krw` (`prpr`, `now_pric2` times
    `frst_bltn_exrt`, the rate), open orders from both lists, fills from both lists (ids `ord_dt-odno`), the five loan
    figures, `server_utc` and `clock_offset_s`, one `response_sha256` per path with no query in any key; every call is
    a GET with its pinned TR; `INQR_DVSN=01` on every inquire-balance (TTTC8434R) call; `PDNO=%25` on the wire; the
    account comes from `keys.read(ACCOUNT_NAMES)` and a malformed one fails with text that holds no digits of it;
    missing keys give `keys_missing`, an auth code gives `auth_error`, a token-code answer fails the snapshot and
    marks the token bad; a missing field fails closed with `"kis: <path>: field <name>"`; a malformed number such as
    `"1,234,567KRW"` fails closed and the text holds no digit of it; an `rt_cd` error fails closed; a `Refused` send
    and a `checked_target` refusal propagate out of `snapshot` (E38).
- Files: modify `execution/kis_inquiry.py`, `tests/execution_fixtures.py`; create `tests/execution_kis.py`.
- Verify: `execution_kis/`, `execution_guards/` (the token rules now see the full file), the T-RO-01 one-liner,
  `<KEYLESS> --suite cockpit`.

## Task 6: Upbit inquiry (spec 5 Upbit table and bullets, 6 Upbit valuation; E12, E16, E21, E22, E38)
- `upbit_inquiry.snapshot(now)` (C10); the Upbit response dicts and `upbit_routes()`.
- `tests/execution_upbit.py`: every private call carries a JWT whose `query_hash` matches the exact sent query; the
  ticker call carries no `Authorization` header and asks `KRW-USDT` plus every held coin; KRW is cash, coins are
  holdings (`balance + locked`), open orders (wait and watch), closed orders with executed volume as fills,
  withdrawals and deposits as moves, addresses, the earliest `expire_at` as `key_expiry` (an offset-less value read
  as Asia/Seoul), `prices_krw`, `clock_offset_s`; `out_of_scope` (HTTP 401) gives `auth_error`; missing keys give
  `keys_missing`; `/v1/status/wallet` is never called; a malformed field fails closed with names-only text.
- Files: modify `execution/upbit_inquiry.py`, `tests/execution_fixtures.py`; create `tests/execution_upbit.py`.
- Verify: `execution_upbit/`, `execution_guards/` (the Upbit token rule now sees the full file), the T-RO-01
  one-liner.

## Task 7: OKX inquiry and its read-only self-check (spec 5 OKX table and bullets, 6 OKX valuation; E25, E26, E32, E39)
- `okx_inquiry.self_check`, `okx_inquiry.snapshot(now, usdt_krw)` (C11); the OKX response dicts and `okx_routes()`.
- `tests/execution_okx.py`: with no OKX keys the snapshot has `keys_missing` and makes no call at all (not even
  `public/time`); `perm` values `"read_only,trade"`, `"trade"`, `""`, `"read_only,transfer"`, an unknown value and a
  missing key all fail and only exact `"read_only"` passes; `acctLv != "1"`, `enableSpotBorrow` true, `autoLoan` true,
  an empty `ip` each fail; a failed self-check stops after `account/config` (no further call, flags set,
  `ok: false`); `public/time` comes first after the key check and sets the offset and `clock_offset_s`; an offset
  above 25 s refuses every signed call with no key read; one `orders-algo-pending` call per `ALGO_TYPES` value, each
  with its own `response_sha256` key; holdings merge trading and funding; `prices_krw` from `usdt_krw` (none when it
  is None); `EVENTS` from a position, an order or a fill; `derivative_position` from a SWAP row with `pos != "0"` and
  not from `pos == "0"`; MARGIN positions, `liab` and flexible loans as loans; Simple Earn, `asset-valuation` earn
  and auto-lend as earn; `50120` and `50123` give `auth_error`; no demo header on any call.
- Files: modify `execution/okx_inquiry.py`, `tests/execution_fixtures.py`; create `tests/execution_okx.py`.
- Verify: `execution_okx/`, `execution_guards/`.

## Task 8: Live positions (spec 6 "Positions (P19)"; E17)
- `execution/positions.py` (C12).
- `tests/execution_positions.py`: equity is the sum of the three venue values with the spec 6 prices; per-venue
  `held_krw` (OKX USDT and USDC included); holdings keyed `(venue, symbol)`; no reservations or promised units; None
  for a missing venue, a not-ok venue, a snapshot 15 min 1 s old, one stamped after `now`, an unpriced holding or
  currency, and a negative venue value; at exactly 15 min it still counts; the result passes
  `owner._positions_problem(...) == ""`.
- Files: create `execution/positions.py`, `tests/execution_positions.py`.
- Verify: `execution_positions/`.

## Task 9: Compliance changes, signed (spec 6 "How the gate reads it", 8 "Signing" and "Compliance changes"; E4, E5, E18)
- `core/compliance/model.py`: `Context.live_evidence` and the `seal_context` body that hashes every field, defaults
  included (C13.1); without it `test_seal_context_registers_and_hand_built_is_refused` goes red. Before this edit,
  grep `tests/` and `core/` (the odds plan's users of `model.py` included) for a pinned `ctx_hash` value; a hit is a
  drift ruling (C0.6).
- `core/compliance/gate.py`: the D16 rule (C13.2).
- `core/compliance/owner.py`: `code_files` seeds and the rewrapped docstring; `_context` passes `live_evidence`; the
  appended evidence block (`EVIDENCE_THRESHOLDS_KRW`, `EVIDENCE_KEYS`, `EVIDENCE_MAX_AGE_DAYS`, `evidence_path`,
  `evidence_chain`, `evidence_in_force`, `_live_evidence`) (C13.3).
- `tools/signer/sign.py`: the same seeds and the rewrapped comment (C13.4).
- Compliance tests (C13.5, each anchored on its quoted old text): new reason texts in `tests/compliance_gate.py`; the
  new `test_d16_rows_lift_only_on_live_deposit_evidence`; the `changes` case in `tests/compliance_model.py`; the
  closure in `tests/compliance_store.py` and `tests/compliance_signer.py` (execution files in, `config.py`, `data/`,
  `core/quant/`, `core/calendars/`, `core/engine/` out). First `grep -rn "needs live broker evidence (execution spec)"
  tests/ core/`: every hit is changed here or is a drift ruling.
- `tests/execution_evidence.py` (the fold): met and unmet records; a run starting 23:59:59 KST counts at 00:00:00 KST
  the next day while one starting at 00:00:00 KST does not count that day (stamps `2026-10-23T14:59:59Z` and
  `2026-10-23T15:00:00Z`); a later `met: false` removes it at once; a latest record 7 days old counts and 8 days old
  does not; a latest record stamped after today removes it; a back-stamped met line appended after a line stamped
  today is dated today; a broken chain, a torn line, a duplicate key, non-canonical JSON, a `broker_approval` or
  `collateral_105pct` line, and a `met` that disagrees with `value_krw` each give `frozenset()`; an unreadable or
  missing file gives `frozenset()`; `load_context` in a temp home holding only `execution/evidence.jsonl` returns the
  expected `live_evidence` and creates no file; the vocabulary is a subset of `rules.LIVE_REQUIREMENTS`.
- The code hash changes: say so in the commit message (owner act 5 re-verifies the signer; act 2 re-signs).
- Files: modify `core/compliance/model.py`, `gate.py`, `owner.py`, `tools/signer/sign.py`,
  `tests/compliance_gate.py`, `tests/compliance_model.py`, `tests/compliance_store.py`, `tests/compliance_signer.py`;
  create `tests/execution_evidence.py`.
- Verify: `<KEYLESS> --suite compliance` green and `<KEYLESS> --suite odds` green (the odds core screens through
  `Context`, `gate` and `owner`; restore the results file after each); the T-RO-01 one-liner; `execution_evidence/`;
  the grep above finds no old reason text; compliance guards still pass on the new owner.py (no clock, allowlisted
  imports, no `CANO`).

## Task 10: The evidence writer (spec 6 "Evidence (E1-D4)"; E18, E33; E1R2-3)
- `execution/evidence.py` (C14), with `EvidenceBroken` and the pure `due` (E1R2-3, spec rev 2).
- Tests appended to `tests/execution_evidence.py`: `judge` per threshold (just below and at each threshold),
  `cash_krw_30m` adding overseas cash at the KIS rate, skipped when a rate or `deposit_krw` is missing or the snapshot
  is not ok; `record` on an empty file appends one line per judged item, chained; a second poll the same Seoul day
  with the same `met` values appends nothing (a different `value_krw` alone appends nothing either); a flipped `met`
  appends that requirement only; the first poll of the next Seoul day appends a heartbeat for every judged item
  (boundary: a poll at 23:59:59 KST then one at 00:00:00 KST); `due` true and false cases on synthetic rows; the
  lines verify with `owner.evidence_chain` and records written on day D lift on day D+1 through
  `owner.evidence_in_force`; the equivalence test (E1R2-3): over seeded random histories of KIS snapshots (5-minute
  steps, gaps of hours, 2 and 9 days, polls with KIS not ok, a missing `deposit_krw` or rate, 1-second steps across
  Seoul midnight, as `e1/sandbox_round2/fold_probe.py` does), the lines `record` writes and the lines one record per
  judged item per poll would give (the same polls run through `record` into a second file with `evidence.due`
  patched to always return True, save/restore) yield the same
  `owner.evidence_in_force(lines, today)` for every prefix and every `today` from the prefix's last Seoul date to
  9 days after; a broken chain raises `EvidenceBroken` and appends nothing; a hard-linked `evidence.jsonl` raises
  `checked_target`'s `RuntimeError` (not `EvidenceBroken`); `broker_approval` and `collateral_105pct` are never
  written; the write goes through `checked_target`. Keep the equivalence test small (a few hundred comparisons) so the
  suite stays under 60 s.
- Files: create `execution/evidence.py`; modify `tests/execution_evidence.py`.
- Verify: `execution_evidence/`, `execution_guards/` (only evidence.py names `evidence_path`).

## Task 11: The poll checks (spec 7 table and bullets; E7, E19, E20, E21, E31, E34, E39, E42, E43; E1R2-2, E1R2-8, E1R2-9, E1R2-12)
- `execution/checks.py` (C15): constants (`ITEM_SLOTS`, `NOT_SET_ITEMS` included), `TEXT` (with KEY_MISSING,
  KIS_UNSIGNED and NOT_SET), `Alert`, `Prior`, `Limits`, `limits_from`, `priors`, `day_start`, `run_checks`,
  `evaluated`, `not_set`, `due`, `render`, `row`, `verify_row`.
- `tests/execution_checks.py`: each row of C15.1 fires on its trigger and stays silent just inside it (30 days vs 30
  days 1 s for expiry, 2 vs 3 failed polls, an offset of 60 vs 61 s, equity at the floor and 1 KRW above, a loss of
  exactly the daily limit and 1 KRW less, OKX value at the cap and 1 KRW above); CLOCK_SKEW reads `clock_offset_s`, so
  a correct clock with the poll's start a minute before the answer raises nothing; HOLDINGS explained (a fill's
  counter counts) and unexplained, with the `fills`, `deposits` and `withdrawals` counts for a mixed case; ADDRESS
  changed and unsigned, and the unsigned half skipped under a BROKEN owner state;
  - missing keys and unsigned code (E1R2-8, E1R2-9): a `keys_missing` venue raises one amber KEY_MISSING and no
    OUTAGE, however many polls in a row, and is listed by `not_set`; a KIS snapshot with `code_unsigned` raises one
    amber KIS_UNSIGNED and nothing else (no OUTAGE after 3 such polls) and `not_set` lists `"KIS: code not signed"`;
    `priors` ends a fail streak at a `keys_missing` or `code_unsigned` snapshot, so the first real failure after keys
    arrive or the code is signed gives `fails == 0`; KEY_MISSING and KIS_UNSIGNED clear once the venue is ok;
  - unset limits and no live positions are listed by `not_set` with the exact strings of C15.1 and raise nothing;
    every string `not_set` can return is in `NOT_SET_ITEMS`;
  - `due` (E1R2-2): fires once per `(venue, text_key)` per Seoul date; two text_keys of one kind raised together are
    both fresh; a later different text_key of that kind the same day is fresh too (an amber HOLDINGS_EXPLAINED then a
    red HOLDINGS_UNEXPLAINED; D15_LOAN then D15_EARN); a level rise fires at once (KEY_AUTH red fires; next poll
    KEY_MISSING amber fires while KEY_HEALTH is not evaluated, so KEY_AUTH is not cleared; next poll KEY_AUTH is fresh
    again; the poll after, it is not); within one poll `fresh` lists amber and info before red; a clear is written
    only for an evaluated text_key that is no longer raised, and the key fires again when it comes back; FOREIGN_ORDER
    fires, the next poll has Upbit not ok (no clear row), the poll after has the same open order and nothing is
    fresh; the Seoul date boundary of `due` (23:59:59 vs 00:00:00 KST); a NOT_SET info alert is fresh on the first
    poll of each Seoul day only and is never cleared;
  - `row()` gives `sent: true` for clear and info rows and `sent: false` for red and amber; `priors` and `day_start`
    from synthetic rows; `verify_row` true for every row `row()` writes (the NOT_SET row included) and false for a
    wrong key set, an unknown text_key, a kind or level that disagrees, a bool or str in an int slot, an extra slot, a
    time slot that is not a stamp, and a `skipped` value holding an item outside `NOT_SET_ITEMS` or an empty item;
    the leak scan over every template and every rendered alert (C15.3); every text_key's kind is in `KINDS`.
- Files: create `execution/checks.py`, `tests/execution_checks.py`.
- Verify: `execution_checks/`, `execution_guards/` (no clock, no file in checks.py).

## Task 12: The poller and the alert CLI (spec 4 "Data flow per poll", 7 "Alert records and delivery" and "The poller", 10; E7, E11, E23, E24, E30, E33, E37, E40, E42, E43; E1R2-1, E1R2-4, E1R2-9, E1R2-12)
- `execution/poll.py` (C16): `EXIT_LOCKED = 0` (E1R2-1); `poll_once` loads the context first and passes it to KIS
  (E24, E42); the daily inquiry files (E30); the NOT_SET info row (E43).
- `tests/execution_poll.py`, every CLI case through `poll.main(argv)` in-process:
  - in a signed temp home (`F.pubkey_at(home / "owner_pubkey.pem")`, `F.full_home(home)`; C3.2), `poll_once(NOW)`
    with every fixture routed writes three lines to `inquiry-20261024.jsonl`, the first evidence lines, the alert rows
    (sent false) and one toast per fresh red or amber alert, and returns a summary with counts and no balance; a
    second poll a minute later writes no repeated alert and no evidence line; one venue failing leaves the others ok,
    gives no positions and clears nothing of that venue; a broken evidence chain raises EVIDENCE_BROKEN and the poll
    completes;
  - signed code (E1R2-9): in an unsigned temp home (no owner key) with every route served, `poll_once(NOW)` polls
    Upbit and OKX but no KIS path (the router records no KIS call, the token POST included), the KIS snapshot is
    `ok: false`, error `code not signed`, flag `code_unsigned`; one amber KIS_UNSIGNED row and toast, none on later
    polls that day and no OUTAGE for KIS after three; `load_context` runs once per poll and before the first send
    (a recording wrapper around `owner.load_context`, save/restore);
  - daily files (E1R2-4): a poll at 23:59:59 KST and one at 00:00:00 KST write to two files; the second poll's
    priors see the first (it reads yesterday's and today's files only, so a third file two days back is not read);
    nothing is deleted;
  - the info row (E1R2-12): the first poll of a Seoul day with skipped checks writes one NOT_SET row (`level: "info"`,
    `sent: true`, its `skipped` items equal the summary's `not_set`), with no toast; a second poll that day writes
    none; the first poll of the next day writes one; `--pending` never lists it;
  - refused writes: after `snapshot.home()` has run once (so the link scan is remembered clean), a hard-linked
    `inquiry-20261024.jsonl` is a crash and gives OUTAGE_CRASH rows for every venue; a hard-linked `evidence.jsonl` gives
    OUTAGE_CRASH and no EVIDENCE_BROKEN; a hard-linked `kis_token.json` gives a crash; `checked_target` patched to
    refuse `alerts.jsonl` gives exactly one CRASH_UNLOGGED toast per Seoul date, no row, and `main(["--once"])`
    returns 4; a link present before the first scan (so every path computation raises) gives the same single toast;
  - `main(["--once"])` returns 0, 4 after a crash (printing `{"crash": ..., "at": ...}` with no exception text), and
    0 while a second in-process handle holds `poll.lock` (E1R2-1), printing
    `another E1 poller holds poll.lock; exiting` and polling nothing (no inquiry file, no send, `poll_once` not
    called); argument errors (`--interval-min 0`, `61`, `x`, two modes, a bad `--mark-sent` stamp) return 4;
  - the loop: with `poll._sleep`, `poll.poll_once` and `poll.datetime` patched (save/restore),
    `main(["--interval-min", "1"])` where poll 1 crashes, poll 2 succeeds and the second sleep raises
    `KeyboardInterrupt` returns 0, wrote OUTAGE_CRASH rows, slept `60 - elapsed` seconds, and released the lock
    (`held_lock()` yields True afterwards);
  - `--pending` prints one ASCII JSON line with no balance or address and lists the utcs; a forged row (a slot string
    holding text, an unknown text_key, a wrong kind) prints `UNVERIFIED` once and none of its text; in an empty home
    `--pending` prints `{"send": false}` and creates nothing (no `execution/` folder); `--mark-sent` marks only that
    utc, keeps other lines byte for byte, returns the count, a repeat returns 0, and a missing file returns 0 and
    creates nothing; `--pending` and `--mark-sent` work while `poll.lock` is held;
  - KEYLESS proven: with every E1 key name set to `'<unset>'` in `os.environ` (not removed) and `keys._ENV_FILE`
    pointed at a temp `.env` holding fake values, in a signed temp home (so KIS reaches its key read), `poll_once`
    makes no send at all (no stray, no route needed), every venue is `keys_missing`, `not_set` lists the three
    venues, and the only rows are three amber KEY_MISSING rows and one NOT_SET info row (E1R2-8, E1R2-12); the same in
    an unsigned home gives KIS `code_unsigned` instead, with KIS_UNSIGNED in place of the KIS KEY_MISSING;
  - `test_no_secret_reaches_any_output`, in a signed temp home (so the fake KIS keys, account and token are used):
    `poll_once` with every route, then with an auth error, a 500 and a parser `FieldError` per venue, and a crash,
    with stdout captured; no `FAKE_KEYS` value, the token `test-token-1` or the account `12345678` appears in any
    byte under `home / "execution"`, the summaries, `TOASTS`, stdout or the `--pending` output;
  - `main` sets `transport._clock` (save/restore in the test) and is the only clock reader (guard).
- Files: create `execution/poll.py`, `tests/execution_poll.py`.
- Verify: the whole execution suite under 60 s via `<KEYLESS> --suite execution` (restore the results file); the
  T-RO-01 one-liner; `<KEYLESS> --suite cockpit`.

## Task 13: README, the full run and the ledger (spec 8 "README P0", 9; E1)
- `README.md` (CRLF): the read-only inquiry status bullet (with the P0 scope sentence and the narrowed guards), the
  cockpit row wording, the compliance row's count and D16 wording, the execution suite row and the **Total** line
  (C17). P0 and the UI disclaimer stay unchanged.
- The full run with the overlap check and the KEYLESS prefix: `<KEYLESS> .venv/Scripts/python.exe tests/run_all.py`;
  0 failed; the execution suite all PASS; compare the totals with the previous full run and explain any change in
  NOT_RUN (the KEYLESS prefix can turn keyed checks into NOT_RUN).
- Commit `qa/acceptance_results.json` (CRLF) with the README.
- The E1 execution ledger records every drift ruling, every deferred minor, the round-2 rulings E1R2-1 to E1R2-12 as
  applied (C20; no open issue is left open) and the run's totals.
- Files: modify `README.md`, `qa/acceptance_results.json`, the ledger.
- Verify: `git diff --cached --stat` equals `--ignore-cr-at-eol`; `git status` clean after the commit.

## Task 14: Owner-gated final steps (spec 12; E9, E31, E42; X7, X9; E1R2-5, E1R2-6, E1R2-7, E1R2-9)
- Daily task (owner gate): re-read the live prompt, show the owner the exact new prompt of C18 and a computed diff
  against the live one (the first paragraph changes too), then stop. Change `tradegen-compliance-daily` through the
  scheduled-tasks tool only after an explicit yes; never edit its files by hand. Run it by hand only if the owner asks.
- List the six owner acts of spec 12 verbatim (C19). Claude performs none of them.
- The first live poll: only after the owner says in chat that the keys are in `.env`; only
  `.venv/Scripts/python.exe -m execution.poll --once`, without the KEYLESS prefix; report only the C16.3 summary
  (venues, counts, ok/error); say that it wrote the real `~/.tradegen/execution` files, may have refreshed the KIS
  token (KakaoTalk notice) and may have shown toasts. Expected, not faults (C19): a venue without keys shows
  `keys missing` and one amber KEY_MISSING toast (E31, E1R2-8); until the owner has signed the code hash (main-spec
  owner acts 1 and 2, then E1 act 5) KIS shows `code not signed`, sends nothing and gives one amber KIS_UNSIGNED
  toast (E42, E1R2-9), and the first live KIS read waits for one more `--once` that Claude runs only after the owner
  says in chat that the code is signed, under the same rules. If the OKX self-check fails on `okx_auto_loan` with
  `acctLv == "1"` (a spot-mode key; E1R2-6, open issue 6), or the KIS overseas calls fail because the overseas
  service is not enabled (E1R2-7, open issue 7), stop and ask the owner; never loosen a check. Any other field-name
  mismatch with a live answer, a field marked `[assumed]` included, fails that venue closed; record it in the ledger
  and fix it in a follow-up task under the same rules (E1R2-5, open issue 5).
- Memory and hand-over notes: what E1 built, the owner acts still open, the C20 rulings that wait on a live answer
  (5, 6, 7) and the three spec rev 2 items (E1R2-3, E1R2-4, E1R2-9) for the owner's spec revision.
- Files: none in the repo (the ledger only if the live poll needs a ruling).

## Coverage: spec sections 4-12, rulings X1-X9 and round-2 rulings E1R2-1 to E1R2-12

| Item | Task(s) |
|---|---|
| 4 package `execution/`, the eleven files | 1 (`__init__`), 2 (keys, transport checks, venue constants), 3, 4, 5, 6, 7, 8, 10, 11, 12 |
| 4 imports (stdlib, requests, core.isolation, core.compliance.*; never config, data.*, core.quant/calendars/engine/ficc) | 1 (explicit allowlist guard), 2 (transport-only path), every module task |
| 4 data flow per poll, steps 1-6 (with the context loaded first, E24) | 12 |
| 4 state files under `state_root()/execution` (inquiry as daily files, E30), `checked_target` before every write, `poll.lock`, a second poller exits 0 with a message | 4, 10, 12; guard in 1; exit 0 per E1R2-1 |
| 5 choke point steps 1-3, `InquiryRefused` before keys, frozensets pinned | 2 |
| 5 choke point steps 4-5: one send, 10 s timeout, retry rules, parsed JSON and Date header | 2 (`_send` pinned and run), 3 |
| 5 KIS host, headers, the nine TRs, method + path + R-suffixed TR | 2 (refusals, R rule on its own), 3 (headers), 5 |
| 5 KIS token: shared cache, 24 h / 6 h, once a minute, 70 s per process, checked target before the POST | 3 |
| 5 KIS pacing 5/s, account from `KIS_ACCOUNT_8`/`KIS_ACCOUNT_PD` only in kis_inquiry.py, `INQR_DVSN=01` | 3, 5; guard in 2 |
| 5 Upbit host, JWT, nine endpoints, `out_of_scope` by name, no 포켓관리, main pocket | 2, 3, 6 |
| 5 OKX host, signing, 30 s window, fourteen endpoints, exact `perm == "read_only"` self-check, no address list, no `GET /trade/order` | 2, 3, 7 |
| 6 snapshot fields and `snapshot_sha256` | 4, 5, 6, 7 |
| 6 positions: equity, per-venue `held_krw`, valuation per venue, empty reservations, None when stale or failed | 8 |
| 6 evidence vocabulary and thresholds, `collateral_105pct` and `broker_approval` never written | 9, 10 |
| 6 evidence record format, hash chain, writer only evidence.py under `poll.lock`; records on change plus a daily heartbeat (E1R2-3) | 9 (format, fold), 10 (writer, equivalence test), 1 (guard) |
| 6 how the gate reads it: next Seoul day, tighten at once, 7-day expiry, broken chain empty | 9 |
| 6 gate: every live item must be in `ctx.live_evidence`; broker_approval rows stay blocked | 9 |
| 7 KEY_HEALTH, FOREIGN_ORDER, HOLDINGS_CHANGED (with the explaining counts), OKX_CAP, ADDRESS_LIST, D15_LIVE, HARD_BLOCK_LIVE, FLOOR, DAILY_LOSS, OUTAGE, CLOCK_SKEW | 11 |
| 7 unset limits skipped and recorded "not set" (one info row a day, E43), once per venue and text_key per Seoul day with a level rise at once (E19), E1 only alerts | 11, 12 |
| 7 alert records, fixed sentences, no balances or addresses, toast | 11, 12 |
| 7 delivery by the 09:05 task, `--mark-sent`, `core/compliance/alerts.py` unchanged | 12, 14 |
| 7 the poller: interval 5, `--interval-min` 1-60, `--once`, one poller, clock only in `main()`, never raises out of the loop, Ctrl+C | 12 |
| 8 `runtime_py()` adds `execution/**/*.py` with a positive control | 1 |
| 8 KIS exception file-exact; exactness test (paths allowlisted, TRs end in R and pinned, no order words) | 1 (T-RO-01, test_09), 2 (token rules) |
| 8 Upbit exception file-exact; only the four exact paths | 1, 2 |
| 8 test_08 in force; T-RO-02 unchanged; execution never imports kis_client | 1 (guard), 3 (cross-read test without importing it in execution) |
| 8 core-wide bans extended; import allowlist; one token POST; no wall clock outside `poll.main()`; writes via `checked_target` | 1, 2 |
| 8 `ACTING_MODULE_PREFIXES` adds `"execution."` | 1 |
| 8 README P0 and UI disclaimer stay true; README gains one line | 13 |
| 8 signing: `code_files` seeds, signer lockstep, closure tests | 9 |
| 8 compliance changes: Context field, owner fold, gate rule | 9 |
| 9 suite `execution`, MODULES, `_wrap`, run_all and README registration | 1 |
| 9 no live call ever; probe of the unpatched send | 1 (wrapper, no child process), 2 and 3 (probes), 12 (KEYLESS proven) |
| 9 transport refusals before keys; token rate limit and checked target first | 2, 3 |
| 9 OKX self-check values | 7 |
| 9 snapshots and positions | 4, 8 |
| 9 evidence tests, the 23:59:59 / 00:00:00 KST boundary, the gate reading `live_evidence` | 9, 10 |
| 9 checks: every row, once a day, unset limits, no balance or address in text | 11, 12 (the output scan) |
| 9 guards with positive controls; exceptions file-exact | 1, 2 |
| 9 signing: closure includes `execution/*.py`, excludes config.py, data/, core/quant/ | 9 |
| 10 errors contained per venue; no POST retry, token failure skips KIS; skew alerted and OKX not sent; None not partial; refused write stops the poll and alerts | 5, 6, 7, 3, 2, 8, 12 |
| 11 guardrails table (allowlists, KIS checks, OKX self-check, signed code, evidence rules, fail-closed positions, alert text) | 2, 5, 7, 9, 10, 8, 11, 12 |
| 12 owner acts 1-6 and the first live `--once` | 14 |
| X1 order, branch, DRIFT RULE, suite-list literal | 1, every task (C0.6), 13 |
| X2 package, imports, `alerts._toast` through the module, keys.py rules | 1, 2, 12 |
| X3 transport signature, seam, allowlists, retry, pacing, token, Upbit JWT, OKX signing and skew | 2, 3 |
| X4 canonical JSON, sidecar locks, `poll.lock`, evidence format, fold in owner.py, `load_context` reads it | 4, 9, 10, 12 |
| X5 Context field, gate reason, code_files seeds, signer, closure tests | 9 |
| X6 runtime_py, T-RO-01 map, test_09, exactness tests, execution_guards list, context_log prefix | 1, 2 |
| X7 `run_checks`, catalogue and leak test, once-per-day from alerts.jsonl (per `(venue, text_key)` since E1R2-2), poll CLI and exit codes (lock 0 since E1R2-1), the daily prompt gate | 11, 12, 14 |
| X8 suite mirrors compliance, refusing `_send`, toast recorder, probe, fixtures from the docs, under 60 s | 1, 2, 3, 5, 6, 7, 12 |
| X9 owner acts verbatim, first live `--once` only after the owner's word, redacted summary | 14 |
| E1R2-1 `EXIT_LOCKED = 0`, a second poller exits 0 with a message | 12 |
| E1R2-2 dedupe per `(venue, text_key)` per Seoul date; an amber-to-red rise fires at once (E19) | 11 |
| E1R2-3 (spec rev 2) evidence on a `met` change or a daily heartbeat; same `live_evidence` as one record per poll (E18) | 10 |
| E1R2-4 (spec rev 2) daily `inquiry-YYYYMMDD.jsonl`, never deleted; a poll opens yesterday's and today's only (E30) | 4, 12; harness watch in 1 |
| E1R2-5 `[assumed]` fixture fields accepted; a live mismatch fails that venue closed | 5, 6, 7 (fail closed), 14 |
| E1R2-6 OKX `autoLoan` stays strict; Task 14 stops and asks on a spot-mode key with `autoLoan` true | 7, 14 |
| E1R2-7 KIS overseas service not enabled: Task 14 stops and asks | 14 |
| E1R2-8 amber KEY_MISSING once per venue per Seoul day (E31) | 11, 12 |
| E1R2-9 (spec rev 2) KIS sends nothing unless the poll's sealed context has `code_signed is True`; one amber KIS_UNSIGNED a day (E42, E24) | 5, 11, 12, 14 |
| E1R2-10 requests and its dependencies outside the D14 hash, stated as a limit in the header | header (no task) |
| E1R2-11 `_send` through a `requests.Session()` with `trust_env = False` and `allow_redirects=False`, pinned (E12) | 2 |
| E1R2-12 one info row a day in alerts.jsonl naming the skipped checks; never pushed; no new file (E43) | 11, 12 |
