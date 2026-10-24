# TRADEGEN E1: read-only account inquiry

Date: 2026-10-24.

Status:
- **Revision 1.** Designed with the owner in chat on 2026-10-24, section by section (structure, poll checks, guards
  and evidence, testing and setup); each section was approved before this file was written.
- Next: the owner's review of this file, then an implementation plan with writing-plans.

Inputs:
- the compliance gate and odds engine spec, rev 3.2 (`docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md`),
  whose section 13 lists execution and calls account inquiry "its own small reviewed design";
- the built compliance gate (main `995534b`) and its ledger (`docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md`);
- official-docs research of 2026-10-24 on the KIS, Upbit and OKX inquiry APIs, each claim re-checked by an independent
  skeptic (kept with the session's notes; the facts this spec relies on are cited inline);
- `research_notes/QUANTGEN asset coverage expansion/kis_api_audit.md` and `crypto_wallets_connectivity.md`.

> This is software design, not legal, tax or investment advice. Neither TRADEGEN nor its author is a licensed advisor.
> E1 places no order and moves no money. The real odds are unchanged by it: no plan without a real edge that keeps the
> floor can beat about 1 in 1,000 (1 in 2,000 with the floor at half the stake), and the research estimates the
> practical chance of 1,000x in a month at 0.01% or less.

---

## 1. Purpose and scope

Execution is split into three sub-projects, built in numerical order, each with its own spec and plan:
- **E1 (this spec): account inquiry.** Read live balances, open orders, recent fills, deposits, withdrawals and
  withdrawal-address lists on KIS, Upbit and OKX. Turn them into the gate's live `Positions` (P19), into live D16
  evidence, and into alerts. **E1 contains no order code and cannot place, change or cancel an order.**
- **E2: execution core.** Arming per session, single-use permits, atomic reservations, the audit log, the kill switch,
  the daily and total loss limits, writing `system_halt` and `system_disarm`, H2. It runs against a dry-run adapter.
- **E3: live order adapters,** one venue at a time: Upbit, then KIS, then OKX (grey; auto-off 2026-12-03).

E1 builds on `owner.load_context()`, `model.Positions`, `alerts._toast` and the owner log. It changes the compliance
package only where section 8 says so.

## 2. Owner decisions (fixed inputs, 2026-10-24)

| # | Decision |
|---|---|
| E1-D1 | Execution is E1, E2, E3, in that order, each with its own spec and plan |
| E1-D2 | All three venues may be queried by TRADEGEN processes that Claude starts, KIS included, although a KIS key can also trade |
| E1-D3 | Keys come from the shared `.env` (QUANTGEN's copy); the shared KIS token and rate limits are accepted |
| E1-D4 | A live broker answer lifts its D16 refusal automatically, unsigned, from the next Asia/Seoul day |
| E1-D5 | E1 polls while the PC is on; a Windows Task Scheduler logon task the owner creates starts it |
| E1-D6 | A mismatch shows a Windows notification at once and is written down; the 09:05 KST Claude task sends push and email for anything not yet sent |
| E1-D7 | The code lives in a new top-level package `execution/`, which the read-only guards scan and the signed D14 code hash covers |

## 3. The honest points, up front

- **A KIS key is an order key.** KIS has no inquiry-only key or scope for individuals: one token from the app key and
  secret calls every API, orders included ("해당 토큰을 활용하여 조회 및 매수/매도 등 모든 API를 호출할 수 있습니다", KIS
  Developers community notice). Individuals get no IP binding either. Under E1-D2 only E1's own code (section 5)
  stands between a TRADEGEN process and a KIS order. The design makes that code small, frozen and signed, but it is
  software, not a server-side refusal.
- **The keys are outside every signature.** `.env` is outside the D14 code hash (spec 6.4). Anyone who can edit it can
  swap keys. E1 never logs a key, never writes one, and never sends one anywhere but its venue.
- **E1-D4 adds the first unsigned entry that loosens the gate.** Today the only unsigned owner-log kinds,
  `system_halt` and `system_disarm`, can only tighten. Any process that can write `~/.tradegen` could forge an
  evidence record. The hash chain detects edits of existing lines, not well-formed forgeries.
- **What evidence can lift is narrow.** KIS exposes no inquiry API for account eligibility: not for the leveraged-ETP
  education or deposit rules, short selling, ELW or derivatives (KIS portal lists and notices; the overseas
  leveraged-ETP rule of 2026-05-22 surfaces only as the order rejection `APBK1681`). E1 can therefore prove only the
  **deposit-type** live requirements from balances. `broker_approval` stays blocked until E3 sees an order-time answer.
  Short selling can never lift: it needs borrowed stock, and D15 forbids borrowing.
- **The 10M-won deposit requirements are far above this account's stake** (about KRW 42,000), so in practice D16
  rows stay blocked. E1 records the evidence honestly either way.

## 4. Architecture

```
execution/                 top-level package; scanned by the guards; inside the D14 code hash
  __init__.py              0 bytes
  keys.py                  reads named variables from .env (stdlib parser); values never logged
  transport.py             the ONLY network path: allowlist check, then credentials, then one GET (or the KIS token POST)
  kis_inquiry.py           KIS domestic + overseas balances, open orders, fills (the only file with KIS account fields)
  upbit_inquiry.py         Upbit accounts, orders open/closed, withdrawals, deposits, withdrawal addresses, key expiry
  okx_inquiry.py           OKX key self-check, balances, positions, earn/loan, orders, fills, deposits, withdrawals
  snapshot.py              one normalised, hashed record per venue per poll; inquiry.jsonl
  positions.py             latest snapshots -> model.Positions with live KRW values
  evidence.py              D16 deposit-type evidence -> evidence.jsonl (hash-chained)
  checks.py                the poll checks of section 7 (pure)
  poll.py                  the poller CLI: python -m execution.poll [--once] [--interval-min N]
```

**Imports.** `execution/` imports only the standard library, `requests` (third party, not hashed), `core.isolation`
and `core.compliance.*`. It never imports `config`, `data.*`, `core.quant.*`, `core.calendars.*`, `core.engine.*` or
`core.ficc.*`, so its signed closure stays small (the D14 closure follows in-repo imports at any depth, owner.py:727-736).
It never imports `core.engine.orders` in any form.

**Data flow per poll.**
1. `poll.py` reads the wall clock once (`now`, aware UTC) and asks each venue module for a snapshot.
2. Each venue module asks `transport` for each allowlisted endpoint; `transport` checks the request, then reads the
   keys, then sends.
3. `snapshot.py` normalises and hashes the answers and appends one line per venue to `inquiry.jsonl`.
4. `evidence.py` derives deposit-type evidence from the KIS snapshot and appends to `evidence.jsonl`.
5. `checks.py` compares the new snapshots with the previous ones, the owner state (`load_context`) and the limits, and
   returns alerts.
6. `poll.py` shows a toast for each new alert, appends it to `execution/alerts.jsonl`, and sleeps until the next poll.

**State files** (all under `core.isolation.state_root()/execution/`, every write through `checked_target` immediately
before opening, temp files included): `inquiry.jsonl`, `evidence.jsonl`, `alerts.jsonl`, `poll.lock` (one poller at a
time; a second exits 0 with a message).

## 5. Transport and allowlists

**The choke point.** `transport.request(venue, method, path, params)` is the only function in `execution/` that sends
anything. In order, it:
1. refuses unless `(venue, method, path)` is in the frozen allowlist below, and for KIS unless the TR id is in the
   frozen TR list for that path and ends in `R`;
2. refuses any method other than GET, except exactly `("kis", "POST", "/oauth2/tokenP")`;
3. only then reads the keys it needs from `keys.py`;
4. sends one request through the module-level seam `transport._send` with a 10-second timeout, never retrying a POST;
   a GET is retried at most once, after 2 seconds, on a connection error or HTTP 429/5xx;
5. returns the parsed JSON and the response's `Date` header (used for the clock-skew check).

A refusal raises `InquiryRefused(reason)` before any key is read. The allowlists are module-level `frozenset`s; a test
pins each one exactly.

**KIS** (real host `https://openapi.koreainvestment.com:9443`; mock hosts are refused, because E1 reads a real account).
Headers: `authorization: Bearer <token>`, `appkey`, `appsecret`, `tr_id`, `custtype: P`.

| Endpoint | Path | TR |
|---|---|---|
| token (cached) | `/oauth2/tokenP` (POST) | none |
| domestic holdings + cash | `/uapi/domestic-stock/v1/trading/inquire-balance` | TTTC8434R |
| domestic open orders | `/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl` | TTTC0084R |
| domestic orders and fills (3 months) | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` | TTTC0081R |
| domestic asset summary | `/uapi/domestic-stock/v1/trading/inquire-account-balance` | CTRP6548R |
| integrated margin status | `/uapi/domestic-stock/v1/trading/intgr-margin` | TTTC0869R |
| overseas holdings | `/uapi/overseas-stock/v1/trading/inquire-balance` | TTTS3012R |
| overseas open orders | `/uapi/overseas-stock/v1/trading/inquire-nccs` | TTTS3018R |
| overseas orders and fills | `/uapi/overseas-stock/v1/trading/inquire-ccnl` | TTTS3035R |
| overseas holdings + cash by currency | `/uapi/overseas-stock/v1/trading/inquire-present-balance` | CTRP6504R |

- Inquiry and order endpoints share the `/trading/` paths, and the method and TR id are what separate them (KIS FAQ:
  orders and the token are POST, every inquiry is GET; every inquiry TR in the official lists ends in R, every order TR
  in U). E1 therefore checks all three: the exact path, GET, and a pinned R-suffixed TR.
- **Token.** E1 reads and writes the same token cache file the quote client uses (`state_root()/kis_token.json`), so
  the two never mint competing tokens. A token is valid 24 hours; a request within 6 hours returns the same token;
  issuance is limited to once a minute (`EGW00133`). E1 issues at most one token per 70 seconds per process and
  computes the cache's checked target before the POST (the ledger's "token burnt on refusal" item).
- **Pacing.** At most 5 KIS requests a second from E1 (KIS allows 18 a second per account on the real server).
- Account number: `KIS_ACCOUNT_8` and `KIS_ACCOUNT_PD` from `.env`, read only inside `kis_inquiry.py`.
- The `inquire-balance` parameter `INQR_DVSN` is always `01`.

**Upbit** (`https://api.upbit.com`; HS512 JWT with `access_key`, a fresh UUID `nonce` per request, and `query_hash`
SHA512 over the unencoded query string when there is one; the JWT has no expiry claim).

| Endpoint | Path | Permission |
|---|---|---|
| balances | `/v1/accounts` | 자산조회 |
| open orders | `/v1/orders/open` | 주문조회 |
| closed orders (at most 7 days per call) | `/v1/orders/closed` | 주문조회 |
| withdrawals | `/v1/withdraws` | 출금조회 |
| registered withdrawal addresses | `/v1/withdraws/coin_addresses` | 출금조회 |
| deposits | `/v1/deposits` | 입금조회 |
| key expiry | `/v1/api_keys` | none |
| wallet status | `/v1/status/wallet` | none |
| KRW prices (public) | `/v1/ticker` | public |

- Upbit refuses order endpoints for a key without 주문하기 with `out_of_scope` (HTTP 401 or 403; match on the error
  name). That is documented, not observed; E1 never probes it.
- 포켓관리 (pocket management) also allows transfers, so it must stay off the key, which means E1 cannot read the
  key's own permissions. The owner states them in the setup act (section 12).
- `/v1/accounts` returns the issuing pocket's assets. E1 assumes the owner's main pocket.

**OKX** (`https://www.okx.com`; headers `OK-ACCESS-KEY`, `OK-ACCESS-SIGN` = Base64 HMAC-SHA256 of timestamp + method +
requestPath (with query) + body, `OK-ACCESS-TIMESTAMP` (ISO, milliseconds, within 30 seconds of OKX time),
`OK-ACCESS-PASSPHRASE`; never the demo header).

| Endpoint | Path |
|---|---|
| key and account self-check | `/api/v5/account/config` |
| trading balances | `/api/v5/account/balance` |
| positions | `/api/v5/account/positions` |
| funding balances | `/api/v5/asset/balances` |
| total valuation (cross-check) | `/api/v5/asset/asset-valuation` |
| earn balances | `/api/v5/finance/savings/balance` |
| loans | `/api/v5/finance/flexible-loan/loan-info` |
| open orders | `/api/v5/trade/orders-pending` |
| open algo orders | `/api/v5/trade/orders-algo-pending` |
| fills (last 3 days) | `/api/v5/trade/fills` |
| deposits | `/api/v5/asset/deposit-history` |
| withdrawals | `/api/v5/asset/withdrawal-history` |
| server time (public) | `/api/v5/public/time` |
| BTC-USDT price (public) | `/api/v5/market/ticker` |

- **Self-check first, every poll.** `account/config` must show `perm` **exactly** equal to `"read_only"` (OKX added
  Transfer, Loan and Earn permissions in 2026 and may report values the docs do not list, so "contains read_only" is
  not enough), `acctLv == "1"` (spot mode), `enableSpotBorrow` false and `autoLoan` false, and a non-empty `ip`.
  Anything else stops OKX inquiry for that poll and raises an alert.
- No OKX endpoint lists the verified withdrawal-address whitelist, so OKX addresses are not checked.
- `GET /api/v5/trade/order` is not on the list: its path also serves the order POST.

## 6. Snapshots, positions and evidence

**Snapshot** (one per venue per poll, frozen dataclass, serialised as canonical JSON, `snapshot_sha256` over its
canonical bytes): `venue`, `utc` (poll time), `server_utc` (from the venue), `ok` (bool) and `error` (text or null),
`holdings` (symbol -> units, locked units, average cost where given), `cash` (currency -> amount), `open_orders`
(list of {id, symbol, side, units, price}), `fills_since_last` (list), `deposits_since_last`, `withdrawals_since_last`,
`withdrawal_addresses` (Upbit only: list of {currency, net_type, address, secondary_address}), `key_expiry` (Upbit),
`loans` (KIS `loan_amt`/`tot_loan_amt`, OKX loan and borrow figures), `earn` (OKX), `flags` (for example `EVENTS`,
`derivative_position`), `prices_krw` (symbol -> KRW price used), `response_sha256` (per endpoint, over the raw body).

**Positions (P19).** `positions.live_positions(snapshots)` builds a `model.Positions`:
- `equity_krw` = the sum over venues of cash plus holdings at `prices_krw` (KIS domestic at the balance's `prpr`; KIS
  overseas at `now_pric2` times the KRW rate in `inquire-present-balance`; Upbit at `/v1/ticker`; OKX coins at OKX
  BTC-USDT times Upbit KRW-USDT, USDT and USDC at Upbit KRW-USDT);
- per venue, `Exposure.held_krw` = everything held there, settlement assets included (USDT and USDC on OKX count);
- `reservations` and `promised_sell_units` empty (E2 adds them).
- A venue whose latest snapshot is older than 15 minutes, or not `ok`, makes `live_positions` return `None` for the
  whole set (fail closed: the caller then has no live positions, never partial ones).

**Evidence (E1-D4).** `evidence.py` maps the KIS snapshot to the live requirement vocabulary
(`core/compliance/rules.py` `LIVE_REQUIREMENTS`):
- `deposit_krw_10m`, `deposit_krw_15m`, `deposit_krw_20m`: domestic cash `dnca_tot_amt` at least 10, 15 or 20
  million won;
- `cash_krw_30m`: domestic plus overseas cash in KRW at least 30 million won;
- `collateral_105pct`: not derivable from the E1 endpoints; never written;
- `broker_approval`: never written by E1.

Each poll appends one record per requirement it can judge, met or not: `{seq, prev_sha256, utc, requirement, met,
value_krw, snapshot_sha256}`, hash-chained like the owner log (`row_sha256` over canonical JSON). Writer: only
`evidence.py`, under `poll.lock`.

**How the gate reads it** (a compliance change, section 8). `load_context` reads `evidence.jsonl` into a new Context
field `live_evidence: frozenset[str]` of requirements that count today:
- a requirement counts when its most recent record is `met` AND an unbroken run of `met` records for it starts on an
  Asia/Seoul date before today (it lifts from the next Seoul day, D12-style);
- a `met: false` record removes it at once (tighten now);
- the most recent record older than 7 days removes it (a stopped poller fails closed);
- a broken chain, a bad line or an unreadable file means `live_evidence = frozenset()`.

`gate.py` treats a row's `requires.live` as satisfied only if every item in it is in `ctx.live_evidence`. Rows whose
live items include `broker_approval` therefore stay blocked in E1.

## 7. The poll checks (`checks.py`, pure)

Every poll, per venue (the owner approved this list in section 2 of the design chat):

| Check | Alert when | Level |
|---|---|---|
| KEY_HEALTH | OKX self-check fails; Upbit `expire_at` within 30 days; a venue answers with an auth error | red (OKX, auth), amber (expiry) |
| FOREIGN_ORDER | any open order on any venue (E1 sends none) | red |
| HOLDINGS_CHANGED | holdings differ from the previous snapshot; the alert lists the fills, deposits and withdrawals that explain it | amber if explained, red if not |
| OKX_CAP | OKX held value (USDT and USDC included) above `okx_equity_share` x live total equity | red |
| ADDRESS_LIST | Upbit's registered withdrawal addresses changed, or differ from the owner's signed `withdrawal_address` entries | red |
| D15_LIVE | OKX borrowing enabled, any OKX loan or earn balance, or any KIS loan amount | red |
| HARD_BLOCK_LIVE | an OKX `EVENTS` instrument or any derivative position | red |
| FLOOR | live total equity at or below `total_loss_floor_krw` | red |
| DAILY_LOSS | live total equity fell by at least `daily_loss_krw` since the first poll of the Asia/Seoul day | red |
| OUTAGE | a venue fails 3 polls in a row | amber; a recovery is logged, not alerted |
| CLOCK_SKEW | the PC clock differs from a venue's server time by more than 60 seconds | amber |

- Unset limits or caps: the check is skipped and the poll records "not set" (no alert).
- Each alert kind fires at most once per venue per Asia/Seoul day, unless it clears and comes back.
- E1 only alerts. It never halts, disarms, sells or withdraws; those are E2's.

**Alert records and delivery.** `execution/alerts.jsonl` rows: `{utc, venue, kind, level, text_key, slots, sent}`.
`text_key` picks a fixed sentence from a catalogue in `checks.py`; slots carry counts, venues and times, **never
balances or addresses** (push and email go off the PC). The toast shows the same sentence. The 09:05 Claude task
(updated with the owner's approval, section 12) sends every row with `sent: false` by push and email to
`sapientia@korea.ac.kr`, then marks it sent through a small CLI (`python -m execution.poll --mark-sent <utc>`).
`core/compliance/alerts.py` is not changed; its `alerts.jsonl` stays check-only.

**The poller.** `python -m execution.poll`: interval 5 minutes by default, `--interval-min` 1 to 60, `--once` for one
poll. One poller at a time (`poll.lock`). It reads the wall clock only in `main()`. It never raises out of the loop:
a crashed poll is logged and alerted (OUTAGE for every venue) and the next poll runs. Ctrl+C or ending the task stops
it cleanly.

## 8. Guards, signing and compliance changes

**Read-only guards: narrowed for named files, never removed.**
- `tests/acceptance.py` `runtime_py()` (used by T-RO-01, test_08, test_09) adds `execution/**/*.py`, with a positive
  control that an order string placed in a synthetic `execution/` file is caught.
- **KIS exception.** Only `execution/kis_inquiry.py` may contain `CANO`, `ACNT_PRDT_CD`, `KIS_ACCOUNT` and paths
  matching T-RO-01's `/uapi/.../trading/` pattern. A new test reads that file and requires that every `/trading/`
  path string in it is in `transport`'s KIS allowlist, that every TR id string in it ends in `R` and is pinned, and
  that none of `order-cash`, `order-credit`, `order-rvsecncl`, `order-resv`, `daytime-order` appears.
- **Upbit exception.** Only `execution/upbit_inquiry.py` may contain the T-RO-01 strings `/v1/orders` and
  `/v1/withdraws`, and only inside the exact paths `/v1/orders/open`, `/v1/orders/closed`, `/v1/withdraws` and
  `/v1/withdraws/coin_addresses`; a test pins that. (This second exception was found while writing this spec: Upbit's
  inquiry paths share their prefix with the banned order and withdrawal paths.)
- test_08 (order verbs and TR ids) stays in force everywhere, `execution/` included. T-RO-02 is unchanged:
  `KISClient._get` stays quotation-only, and a test proves `execution/` never imports `data.krx.kis_client`.
- The compliance guards' core-wide bans (`private_key`, `seed_phrase`; no function named `transfer`, `withdraw` or
  `deposit_address`) extend to `execution/`. A new `tests/execution_guards.py` adds: the import allowlist of section
  4; no `.post/.put/.patch/.delete` call anywhere in `execution/` except the one token POST inside `transport.py`; no
  wall-clock call outside `poll.main()`; every file write preceded by `checked_target`.
- `core/ficc/context_log.py` `ACTING_MODULE_PREFIXES` adds `"execution."`.
- README P0 and the UI disclaimer stay true (no order path). README gains one line on read-only inquiry.

**Signing.** `owner.code_files` (and its copy in `tools/signer/sign.py`, kept in step by
`test_code_files_match_owner`) seeds `execution/*.py` beside `core/compliance` and `core/odds`. The closure tests
(`tests/compliance_store.py:137-150`) gain the `execution/` files and still exclude `config.py` and `data/`.
Because the signer changes, the owner re-verifies their own signer copy (an owner act).

**Compliance changes** (one task, signed with everything else):
- `model.Context` gains `live_evidence: frozenset[str] = frozenset()`.
- `owner.load_context` reads `state_root()/execution/evidence.jsonl` as section 6 says (pure fold, tested like the
  owner-state fold).
- `gate.py`: a `requires.live` row passes its live check only when every live item is in `ctx.live_evidence`; the
  reason text for a block names the missing items. Every other gate rule is unchanged (D11 exits, D15, the floor).

## 9. Testing

A new suite `execution` (`tests/execution_acceptance.py`, mirroring the compliance suite: a MODULES tuple, `_wrap`
with `hermetic()` and `temp_home()`), registered in `tests/run_all.py` (CRLF) and README.
- **No live call ever.** `transport._send` is patched with synthetic responses shaped like the official docs; a probe
  test proves an unpatched send is refused under the suite.
- **Transport:** every request outside the allowlist, a non-GET method, a KIS TR not ending in R, a mock host and an
  unpinned TR are refused **before** any key is read (the keys reader is patched to fail the test if called); the
  token POST is rate-limited and computes its checked target first.
- **OKX self-check:** `perm` values `read_only,trade`, `trade`, `""` and an unknown value are refused; spot mode,
  borrow and auto-loan are checked.
- **Snapshots and positions:** canonical hashing, KRW valuation per venue, stale or failed venues give `None`.
- **Evidence:** met and unmet records, next-Seoul-day lifting at the boundary 23:59:59 / 00:00:00 KST, tighten at
  once, the 7-day expiry, a broken chain, and the gate reading `live_evidence` (a D16 row with only deposit items
  lifts; one with `broker_approval` never does; a short never does).
- **Checks:** every row of section 7, the once-a-day rule, unset limits, and that no alert text carries a balance or
  an address.
- **Guards:** every new guard with a positive control; the exceptions are file-exact.
- **Signing:** the closure includes `execution/*.py` and excludes `config.py`, `data/`, `core/quant/`.

## 10. Error handling

- Any venue error is contained to that venue's snapshot (`ok: false`); the other venues still poll.
- `transport` never retries a POST; a token failure means KIS is skipped for that poll.
- Clock skew above 60 seconds is alerted; OKX requests are not sent when the skew would break its 30-second window.
- `live_positions` returns `None` rather than partial positions.
- Every file write goes through `checked_target`; a refused write stops that poll and is alerted.

## 11. The guardrails, in plain language

| Guardrail | What it protects you from | What you see |
|---|---|---|
| One transport, frozen allowlists, GET only | A bug or an edit turning an inquiry into an order | Nothing; a refusal names the path |
| KIS checks (path, GET, R-suffixed TR) | KIS keys being order keys | Nothing; the test suite fails on any widening |
| OKX self-check | A key with trade, transfer or withdraw rights | "OKX key is not read-only" and OKX stops |
| Signed code | Someone editing E1 without your signature | New exposure blocked until you sign (the gate's rule) |
| Evidence next-day rule, expiry and re-block | A balance blip lifting a refusal, or a stopped poller keeping one lifted | Rows lift a day later, re-block at once, expire after 7 days |
| Fail-closed positions | Trading on stale or partial balances later (E2) | "No live positions" |
| Alert text without balances | Your balances leaving the PC | Venue, kind and time only |

## 12. Owner acts (Claude performs none of them)

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
saw, as E1-D2 allows.

## 13. Risks

- **The shared KIS key.** QUANTGEN's processes hold the same trade-capable key and account number. E1 cannot protect
  against code outside TRADEGEN. Mitigation: none in E1; separate TRADEGEN keys remain an open owner choice.
- **A forged evidence record** lifts a deposit-type D16 row. Mitigation: the next-day rule, the 7-day expiry, the
  narrow vocabulary, and that the deposit levels are far above this account's size.
- **Undocumented venue changes** (new OKX permissions, Upbit pocket rules, KIS TR renames). Mitigation: exact
  allowlists, the OKX exact-match self-check, OUTAGE and KEY_HEALTH alerts.
- **The PC is off.** Then nothing polls; positions go stale after 15 minutes and evidence expires after 7 days, both
  fail closed.

## 14. Out of scope

- Everything that sends an order, cancels one or moves money: E2 and E3.
- H2 (halt dating) and every other item the compliance ledger carries to execution: E2.
- OKX withdrawal-address checks (no OKX endpoint exists).
- KIS WebSocket fill notices (E2 or E3 may add them; E1 polls).
- Separate TRADEGEN keys: the owner chose the shared `.env` (E1-D3); revisit before E3.
