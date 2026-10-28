# E1 account inquiry plan: repo map (2026-10-24)

These are the verified facts the E1 account inquiry plan rests on. Parts 1 to 3 are repo facts: sections 0
and 9 of the 2026-10-24 map digest and the whole `execution_ctx` area map, mapped read-only with file:line
evidence at `main` `995534b`, which equals `5816d3c` (the commit the plan is written against) outside docs/.
In the digest, (C) marks a fact the critic re-checked against the tree, and CORRECTED marks a reader's claim
the critic corrected. Parts 4 to 6 are the venue research notes of 2026-10-24 (documentation only: no key used, no
account endpoint called); in each, the skeptic's Verification section wins where it says WRONG. Where the
plan's tasks and this map disagree, the tasks win. Line numbers are as of commit `995534b`.

```text
# Part 1 of 6. Map digest, section 0: repo state and process rules

## 0. Repo state and process rules

* [state] HEAD is 995534b on `main`, the only branch. The compliance branch is merged. core/odds holds only
  venues.yaml. (C)
     EVIDENCE: `git log --oneline -1` `995534b test: full run after the final review wave`; `ls core/odds` -> `venues.yaml`
     IMPACT: Both new plans branch from main. The odds plan creates every core/odds .py file.
* [no owner key yet] core/compliance/owner_pubkey.pem does not exist, so load_context returns BROKEN "no owner key yet:
  owner act 1", and every screen() result is BLOCK in the real home. (C)
     EVIDENCE: core/compliance/owner.py:24 `PUBKEY_PATH = Path(__file__).with_name("owner_pubkey.pem")   # the trust anchor; absent until owner act 1 (P24)`; :929 `return model.OwnerState.broken("no owner key yet: owner act 1"), None`
     IMPACT: No real-home odds run can produce a probability before owner acts 1-5. Manual checks expect the
     refusal. Tests use a temp home and the test key. Nothing is signed yet, so code edits cost no re-signing today.
* [no pytest] A test is a zero-argument `test_*` function that raises. No pytest is installed or used.
     EVIDENCE: plan:61 `- A test is a zero-argument `test_*` function that raises on failure. There is no pytest.`
     IMPACT: No fixtures, parametrize or monkeypatch. Use loops, helpers and save/restore in try/finally.
* [commands] One module or one test: `.venv/Scripts/python.exe -m tests.<suite>_acceptance <module>/[<test>]`. It never
  writes the results file and imports every suite (~7 s, reader-measured). One suite:
  `.venv/Scripts/python.exe tests/run_all.py --suite <name>; echo "exit $?"; git checkout -- qa/acceptance_results.json`.
  Run from the repo root.
     EVIDENCE: tests/compliance_acceptance.py:8-11 `.venv/Scripts/python.exe -m tests.compliance_acceptance [substring]` ... `It never writes` / `qa/acceptance_results.json.`; plan:70-73 `- One suite: `.venv/Scripts/python.exe tests/run_all.py --suite <name>`. This rewrites the tracked` / `qa/acceptance_results.json`. Restore it with `git checkout -- qa/acceptance_results.json` afterwards.`
     IMPACT: Copy both forms into each plan, with the suite name substituted.
* [CORRECTED by harness, vs the earlier repo map: results file is TRACKED] qa/acceptance_results.json is tracked
  (committed in 995534b, 355f978 and d47cea9) and CRLF. Every `run_all` run overwrites it, `--suite` runs included. It
  holds 1166 rows: 1043 PASS and 123 NOT_RUN, 608.6 s. (C)
     EVIDENCE: tests/run_all.py:54 `OUT = ROOT / "qa" / "acceptance_results.json"`; `git ls-files --eol qa/acceptance_results.json` -> `i/crlf  w/crlf`; results summary `1166 ... {'PASS': 1043, 'NOT_RUN': 123}`
     IMPACT: Restore the file after every suite run. Only the final full-run task commits it.
* [overlap check] QUANTGEN shares the machine. Before every test command, run a check that prints nothing.
     EVIDENCE: plan:62-67 `- Overlap check: run it before every test command. It must print nothing; otherwise wait.` ... `Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" }`
     IMPACT: Carry the rule into both plans. The odds Monte Carlo is CPU-heavy: never run two suites at once.
* [line endings] `.gitattributes` is `* -text` ("Byte-exact"). CRLF: README.md, config.py, tests/run_all.py,
  core/quant/history.py, grokteam/book.py, qa/acceptance_results.json and the docs/asset_expansion/cache CSVs. LF:
  every core/compliance file, core/odds/venues.yaml, data/krx/kis_client.py, data/crypto/crypto_client.py,
  core/ficc/data.py, core/isolation.py, tools/signer/sign.py, and tests/compliance_*.py, macro_acceptance.py,
  macro_m0_rules.py and macro_m1_calendars.py. (C)
     EVIDENCE: `git ls-files --eol` (e.g. `i/crlf  w/crlf  attr/-text  tests/run_all.py`, `i/lf    w/lf    attr/-text  core/compliance/rules.py`); plan:75-76 `- New files are UTF-8 with no BOM and LF endings.`
     IMPACT: Edit CRLF files with the Edit tool only, never `sed -i`. New files are LF. Before each commit,
     `git diff --stat` must equal `git diff --stat --ignore-cr-at-eol`.
* [interpreter and pins] Python 3.13.14. Pinned: numpy 2.3.5, scipy 1.18.0, pandas 2.3.3, statsmodels 0.14.6,
  yfinance 1.4.1, curl_cffi 0.15.0, tzdata 2026.2, cryptography 49.0.0, PyYAML 6.0.3. requirements.txt and
  pyproject already declare numpy, scipy and yfinance (as >=), so no new dependency is needed. `arch` is not
  installed. (C)
     EVIDENCE: constraints.txt:1 `# TRADEGEN .venv as of 2026-10-23 (Python 3.13.14)...`; :55 `numpy==2.3.5`; :87 `scipy==1.18.0`; :106 `yfinance==1.4.1`; pyproject.toml `"numpy>=1.26", "pandas>=2.1", "scipy>=1.11", ...` `"yfinance>=0.2", ...` `"cryptography==49.0.0",`
     IMPACT: Record numpy.__version__ and the cryptography version (via importlib.metadata) in provenance. Never
     change the pins: the replay golden depends on them.

# Part 2 of 6. Map digest, section 9: execution design context

## 9. Execution design context (spec section 13)

* [scope] Execution owns adapters, arming and sessions, atomic reservations, single-use permits, the audit log,
  writing system_halt and system_disarm, live balances and broker answers (lifting D16 row by row), and the narrow
  retirement of the read-only guards. An account-inquiry-only first step is its own small reviewed design.
     EVIDENCE: spec:1160-1163
     IMPACT: Split out account inquiry first.
* [what it builds on] The gate is pure. permit() issues only for ALLOW or ALLOW_EXIT and registers the permit in a
  process-local WeakValueDictionary (it does not survive a restart). verify_permit re-checks the intent hash, the
  decision, the session, the date and the state, but NOT single use. Permit fields: decision_id, intent_hash,
  state_hash, state_seq, session_id, reservation_id, date. Reservations live in caller-supplied Positions. (C)
     EVIDENCE: core/compliance/gate.py:566 `_ISSUED: weakref.WeakValueDictionary = weakref.WeakValueDictionary()`; :586-605; core/compliance/model.py:202-210; :96-109 `class Exposure:` / `class Positions:` / `"""Caller-supplied until the execution spec adds live reads (P19)."""`
     IMPACT: Execution adds single use, a durable atomic reservation store, an audit row per verify, and re-permits
     after a restart.
* [gate gaps execution must own] The gate never reads ctx.session.armed, halted_floors or the loss limits. A session
  ack with session None is accepted. D16 rows always block, and no Context field carries live evidence. Two permits
  can share a reservation_id. A permit edited in place still verifies.
     EVIDENCE: core/compliance/gate.py:423-426; :318 `if (ctx.session.session_id, row.id, sha) in ctx.owner.session_acks:`; :307-308; ledger:143, :155, :156, :239
     IMPACT: The design decides the armed check, the D3 floor halt and the daily loss: in execution, or as a signed
     gate change.
* [owner log for sessions and halts] The system kinds are only system_halt {floor_krw} and system_disarm {session_id,
  reason}, written by `append_system_entry(kind, data, now)` under an OS lock. It raises ValueError, RuntimeError,
  TypeError and OSError, with no production caller yet. Arming is an owner-signed session_armed. "Halts for good" is
  only half-encoded: limits cannot loosen, but re-arming is not forbidden. (C)
     EVIDENCE: core/compliance/owner.py:26-28 `SYSTEM_KINDS = frozenset({"system_halt", "system_disarm"})`; :151-160 (schemas); :400 `def append_system_entry(kind: str, data: dict, now: datetime) -> tuple[int, str]:`; :514-522 (armed_sessions)
     IMPACT: The kill switch needs a local fail-safe that does not depend on the append, and a trusted `now`
     (H2). Rule whether any halt forbids arming.
* [simulated engine, frozen files] core/engine is a simulation with no broker. state.py, runtime.py, feed.py and
  `__init__.py` must stay byte-identical to the backup zip, and orders.py, evaluator.py and ui/trading_page.py are
  add-only. EngineState semantics (disarmed start, never-raising halt, manual ack) are the pattern. Daily counters use
  UTC dates. orders.py names a nonexistent guards.py. (C)
     EVIDENCE: tests/macro_m5_integration.py:54-58 `UNTOUCHED = ("core/engine/state.py", "core/engine/runtime.py", "core/engine/feed.py", "core/engine/__init__.py")`; core/engine/orders.py:3-4, :126-133 `def notional_today(self, *, now: Optional[datetime] = None) -> Decimal:`; core/engine/state.py:6-8, :141-142
     IMPACT: A live engine is a sibling package. Daily loss uses the Asia/Seoul date (model.KST).
* [read-only guards to retire narrowly]
  - KIS account inquiry needs /trading/ paths with CANO and ACNT_PRDT_CD. That trips T-RO-01 (text and path),
    test_09 and T-RO-02's refusal of `/trading/inquire-balance`.
  - Orders add test_08, the T-RO-01 verbs, calls and mutating HTTP, the crypto-client raw test, the UI disclaimer
    and its test, and README P0.
  - T-RO-01 scans only core, data, ui, main.py, config.py and docs/*.py, so a new top-level package escapes it.
  - `KISClient._get` checks the quotation path before credentials (the pattern to copy).
     EVIDENCE: tests/macro_m0_harness.py:28-60, :63-64; tests/acceptance.py:169-182; tests/macro_m1_pit.py:1054-1057; data/krx/kis_client.py:206 `check_quotation_path(path)                  # T-RO-02: before credentials, before any request`; tests/expansion_acceptance.py:154-156; tests/macro_ui_components.py:16-17; README.md:8-13, :399-401
     IMPACT: First widen runtime_py() (or the scope), then retire each guard as an allowlist of named files and
     endpoints, with positive controls.
* [venue clients] `UpbitAccount.balances()` (GET /v1/accounts, HS512 JWT, 자산조회 scope) already passes every guard.
  The keys are absent from .env. There is no OKX client and no Binance account code, and the `okx` package import is
  banned. data.net.session retries GETs only, but still retries an unsent connection for any method.
     EVIDENCE: data/crypto/crypto_client.py:308-319 `class UpbitAccount:` / `"""Balances only. There is no order path in this class or this module."""`; data/net.py:17-20, :43-50; tests/macro_m0_harness.py:40
     IMPACT: Account inquiry can start Upbit-only with no guard retirement. An order POST must not use the shared
     session.
* [keys and research] .env (QUANTGEN's copy) sets KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_8 and KIS_ACCOUNT_PD
  (names only), with no UPBIT or OKX lines. .env and the venv are outside the code hash. Whether the KIS key can trade
  is "unknown". Upbit keys are IP-bound for order scope and last 1 year. OKX private-API facts are unresearched. KIS
  tokens: 24 h, at most one issue per minute, and a KakaoTalk notice on each issue.
     EVIDENCE: names-only .env scan (execution_ctx); spec:626 `- **edit the venv or `.env`.** Both are outside the code hash;`; tests/macro_m1_pit.py:1090-1091; research_notes/QUANTGEN asset coverage expansion/crypto_wallets_connectivity.md:28-30, :98; kis_api_audit.md:185, :190
     IMPACT: Require TRADEGEN-own and inquiry-vs-trading keys before arming. Research OKX before designing it.
* [alerts] Push and email come only from the daily 09:00 KST task, and only to OWNER_ALERT_EMAIL. The toast is a
  patched seam. alerts.jsonl accepts only --check summaries.
     EVIDENCE: core/compliance/alerts.py:1-5, :18-21, :216-221, :242-252
     IMPACT: Execution needs an immediate channel and its own audit log file.
* [live calls in a test] cockpit test_21 calls `KRXGateway().daily("005930")`, the real KIS client when keys exist. A
  kis_token.json exists in the real ~/.tradegen (listed once by the execution_ctx reader).
     EVIDENCE: tests/acceptance.py:318-322; data/krx/gateway.py:90-92
     IMPACT: Make test_21 hermetic before any trade-capable key exists.

# Part 3 of 6. Execution context map (area key execution_ctx), in full

# Map: execution context (area key `execution_ctx`)

Repo: `C:/Users/whydi/OneDrive/Desktop/TRADEGEN`, main at `995534b`, tree clean. Read only. No test suite run, no
network call. `.env` was read for variable NAMES only (a script printed `name set|blank`); no value was read.
Every path below is repo-relative unless it says otherwise.

## 1. What the spec already fixes for execution

* [spec scope] Neither shipped package may place an order; execution is its own spec built on four interfaces.
   EVIDENCE: docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:42 `**Neither package can place an order.** Execution, strategy research and the UI each get their own spec.`
   IMPACT: The execution design consumes `owner.load_context()`, `decide()`, `permit()`/`verify_permit()` and `OddsReport`. It must not widen `core/compliance` or `core/odds` into order code.
* [spec 13] The execution spec's own list: adapters, arming and sessions, atomic reservations, single-use permits, the audit log, writing `system_halt`/`system_disarm`, live balances and broker answers (which lift D16 row by row), and retiring the read-only guards narrowly. An account-inquiry-only early step is "its own small reviewed design".
   EVIDENCE: docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:1160 `- **Execution:** adapters, arming and sessions, atomic reservations, single-use permits, the audit log, writing`
   IMPACT: Use this as the checklist of the execution design. Split out "account inquiry only" as a first, smaller design.
* [D3] Ruin is the total-loss floor L. Execution halts for good there, and the odds engine and the kill switch read one shared setting.
   EVIDENCE: spec:57 `| D3 | Ruin = equity reaching the owner's hard total-loss floor L. Execution halts for good there, and the odds engine and the kill switch read one shared setting |`
   IMPACT: The one setting is `limit_set.total_loss_floor_krw` in the owner log (see section 6). The kill switch must read `OwnerState.limits`, never a second copy.
* [D8] Disarmed by default, armed per session by the owner only, hard daily and total loss limits, a kill switch, an audit log; the owner adds trading-scope keys.
   EVIDENCE: spec:62 `| D8 | Execution is disarmed by default and armed per session by the owner only. It has hard daily and total loss limits, a kill switch and an audit log. The owner adds trading-scope keys |`
   IMPACT: Claude never adds or enters keys. The design describes where the owner puts them and how they are checked.
* [D11] Exits stay open; under corrupt owner state, automated closing orders use the last approved snapshot and withdrawals are manual.
   EVIDENCE: spec:65 `| D11 | **Exits stay open.** Stale rows, auto-off, unmet gates, caps and out-of-scope or hard-block venue rows block **new exposure only**.`
   IMPACT: The adapters need a sell/close path that works even when new exposure is blocked, and must never automate a withdrawal under a BROKEN log.
* [D12] Limits and caps tighten at once and loosen only from the next Asia/Seoul date, never inside an armed session, never after a recorded halt.
   EVIDENCE: spec:66 `| D12 | Limits and caps **tighten at once and loosen slowly**: only from the next Asia/Seoul date, never inside an armed session, and never after a recorded halt |`
   IMPACT: Already folded by `owner._owner_fold` (section 6). Execution must read limits only through `load_context`, never cache them across a session boundary.
* [D14] Owner-only writes are signed; Claude never runs the signer or writes owner entries.
   EVIDENCE: spec:615 `- **Claude** never runs the signer, never asks for the passphrase, and never writes owner entries.`
   IMPACT: Arming (`session_armed`) is an owner-signed entry, so arming happens in the owner's terminal. Execution code writes only the two unsigned system kinds.
* [D14 limits] `.env` and the venv are outside the code hash.
   EVIDENCE: spec:626 `- **edit the venv or `.env`.** Both are outside the code hash;`
   IMPACT: Trading-scope keys in `.env` are not covered by any signature. The design must say so, or move key custody elsewhere (open question).
* [D16] Short selling, leveraged/single-stock ETPs, KRX derivatives and ELW stay refused until live broker evidence exists, which the execution spec adds.
   EVIDENCE: spec:70 `| D16 | Short selling, leveraged and single-stock ETPs, KRX derivatives and ELW are **refused until live broker evidence exists**, which the execution spec adds.`
   IMPACT: Today no Context field can carry live evidence (section 5). Lifting D16 needs a signed change to `model.py`/`gate.py`.
* [spec 6.3/6.4] Atomic reservation, single use and the audit log belong to execution; every caller goes through `load_context`; unset limits mean execution refuses to arm.
   EVIDENCE: spec:534 `Atomic reservation, single use and the audit log belong to the execution spec.`; spec:582 `The execution spec must route every caller through it. No caller may build a `Context` by hand.`; spec:575 `**Unset limits.** The odds engine refuses with `LIMITS_UNSET`, and execution will refuse to arm.`
   IMPACT: Arming precondition = `ctx.owner.limits` holds both `total_loss_floor_krw` and `daily_loss_krw`.
* [spec 6.4] `system_halt {floor_krw}` and `system_disarm {session_id, reason}` are the only unsigned kinds, can only tighten, and "the execution spec writes halts here".
   EVIDENCE: spec:548 `the only unsigned kinds, and they can only tighten.`; spec:567 `- system (unsigned): `system_halt`, `system_disarm`. The execution spec writes halts here.`
   IMPACT: The kill switch and the loss-floor halt write through `owner.append_system_entry` (section 6).

## 2. `core/engine/`: a simulated operator engine, no broker

* [engine package] The package is a simulated engine: state machine, guards, order book, journal.
   EVIDENCE: core/engine/__init__.py:1 `"""Simulated execution engine: state machine, guards, order book, journal."""`
   IMPACT: Nothing here talks to a venue. Execution adapters are new code.
* [orders.py] Everything in orders.py is a simulation; no broker client, no path to a real venue.
   EVIDENCE: core/engine/orders.py:3-4 `Everything here is a simulation. There is no broker client in this package and` / `no code path that reaches a real venue`
   IMPACT: Do not grow orders.py into a live book (it is ADD_ONLY anyway, section 3).
* [orders.py contents] Two halves: (a) `OrderStatus`, `SimulatedOrder`, `order_id`, the in-memory thread-safe `OrderBook` (place/fill/cancel/reject/discard_rejected/cancel_all_open/reset/snapshot/restore); (b) the pure R-27 fill model (`FillModel`, `FillSession`, `Fill`, `NonFillable`, `limit_prices`, `limit_lock`, `inav_check`, `simulate_fill`, `fill_tracking_error`, `Bar`, `refuse_bar_close`).
   EVIDENCE: core/engine/orders.py:90-91 `class OrderBook:` / `"""In-memory book of simulated orders. Thread-safe."""`; :252-254 `# R-27 simulated fill model (M5; TASK-M5-10, M5-11) ... Everything below is pure: `simulate_fill` computes a `Fill` or a `NonFillable` from PIT inputs`
   IMPACT: `simulate_fill` is a close-price model for backtests. A live adapter must record broker fills, not call it.
* [manual fills] A simulated order never fills itself; only an operator fill does.
   EVIDENCE: core/engine/orders.py:169-171 `def fill(self, oid: str, price: Decimal) -> tuple[bool, str]:` / `"""Operator-initiated fill (§3). Never happens on its own."""`
   IMPACT: The "practice" workflow (operator sees an open order and settles it) is a UX precedent for a live confirm step, not live code.
* [deterministic ids] Order ids are deterministic per (rule, revision, trigger sequence), so a restart cannot submit the same trigger twice; `place()` refuses a duplicate id inside the lock.
   EVIDENCE: core/engine/orders.py:85-87 `def order_id(rule_id: str, revision: int, sequence: int) -> str:` / `"""Deterministic, so the same logical trigger cannot be submitted twice."""`; :148-152 `if order.id in self._orders:` / `return None`
   IMPACT: Reusable idea for live client order ids (idempotency keys) and for single-use permits.
* [stale docstring] orders.py names a `guards.py` that does not exist in core/engine (files: __init__, books, evaluator, feed, orders, runtime, state).
   EVIDENCE: core/engine/orders.py:21 `idempotency guard in `guards.py` can recognise a duplicate submission of the`
   IMPACT: Do not plan against a `core/engine/guards.py`; the duplicate guard lives in `OrderBook.place`.
* [LIMIT_DOWN_CARRY_COST_MULTIPLIER] It is 2.0 and documented as an assumption, not a measurement.
   EVIDENCE: core/engine/orders.py:275 `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0        # INV-2: "an assumption, not measured" (R3:802)`
   IMPACT: The odds plan declares it locally and a test compares (spec:160). Execution should not treat it as a real cost.
* [daily counters use UTC] `counts_today` and `notional_today` count by the UTC date of `created_at`.
   EVIDENCE: core/engine/orders.py:126-133 `def notional_today(self, *, now: Optional[datetime] = None) -> Decimal:` ... `today = now.date()` with `now = now or datetime.now(timezone.utc)`
   IMPACT: D12 and the daily loss limit are on Asia/Seoul dates (`model.KST`). A live daily-loss counter must use the Seoul date, not this helper.
* [state machine] `EngineState`: DISARMED on construction, no constructor or persisted field restores ARMED, `halt()` callable from any state and never raises, a halt needs a manual acknowledge before arming.
   EVIDENCE: core/engine/state.py:6-8 `A fresh` / ``EngineState` is DISARMED. There is no constructor argument that starts it` / `armed and no persisted field that restores ARMED.`; :141-142 `def halt(self, reason: HaltReason = HaltReason.OPERATOR, detail: str = "") -> None:` / `"""Emergency stop. Callable from any state, idempotent, never raises."""`; :118-124 `"""Explicit operator action. Refused while a halt is unacknowledged."""`
   IMPACT: These are exactly D8's semantics, so reuse the pattern. But arming here is an unsigned UI click; D8/D14 need a signed `session_armed` (section 6). The live arm must require both.
* [runtime] `EngineRuntime` runs its loop only while armed, persists engine state to `config.trading_dir()/engine.json` on every transition, and owns the simulated `OrderBook`.
   EVIDENCE: core/engine/runtime.py:9-11 `* **The loop runs only while armed.** A disarmed engine makes no network` / `request.`; :78-79 `self.state_path = Path(state_path) if state_path else (` / `config.trading_dir() / "engine.json")`; :86-87 `self.state = EngineState(on_change=lambda _t: self._persist())` / `self.book = OrderBook()`
   IMPACT: The UI wires it as `EngineRuntime(rule_store, QuoteFeed(gateway))` (main.py:113). A live engine is a sibling, not a mode of this one.
* [evaluator caps] The evaluator's caps are per-rule notional caps (max triggers, max order amount, max daily amount), not loss limits.
   EVIDENCE: core/rules/model.py:105-109 `class Limits:` / `"""§5 safety caps. Every field is operator-supplied; none has a default."""` / `max_triggers` / `max_order_amount` / `max_daily_amount`; core/engine/evaluator.py:331-336 `if limits.max_daily_amount is not None:` / `already = self.book.notional_today(now=now)`
   IMPACT: D8's daily and total loss limits (realised and marked P&L against equity) do not exist anywhere in the engine. They are new.
* [books.py] `core/engine/books.py` is the v2 per-book runtime, "additive beside `EngineState`", with HALT scoped to one book id, no wall clock, and governance events.
   EVIDENCE: core/engine/books.py:5-7 `Additive beside `EngineState`: the operator engine's global state machine, manual acknowledge and `engine.json` are` / `untouched.`; :9 `Every function takes `decision_utc` explicitly; nothing here reads a wall clock.`
   IMPACT: Precedent for adding new runtime modules next to the frozen ones instead of editing them.

## 3. test_s4: the engine files are frozen or add-only

* [test_s4 lists] `state.py`, `runtime.py`, `feed.py`, `__init__.py` must stay byte-identical to the backup zip; `orders.py`, `evaluator.py`, `ui/trading_page.py` may only gain lines; eight S4 modules may add no wall-clock call.
   EVIDENCE: tests/macro_m5_integration.py:54-58 `BACKUP = ROOT / "_backup" / "QUANTGEN_pre_v2_2026-10-05.zip"` / `S4_MODULES = ("core/engine/books.py", "core/engine/orders.py", "core/engine/evaluator.py", ...` / `UNTOUCHED = ("core/engine/state.py", "core/engine/runtime.py", "core/engine/feed.py", "core/engine/__init__.py")` / `ADD_ONLY = ("core/engine/orders.py", "core/engine/evaluator.py", "ui/trading_page.py")`
   IMPACT: Execution cannot edit these files. New modules (for example a new package) avoid the test; retiring it is TRADEGEN's own explicit decision, never a silent edit.
* [test_s4 still bites] The backup zip exists and the four UNTOUCHED files are byte-identical to it today; orders.py differs (it gained lines).
   EVIDENCE: `_backup/QUANTGEN_pre_v2_2026-10-05.zip` present; a `.venv` `-I` zip comparison printed `core/engine/state.py True`, `core/engine/runtime.py True`, `core/engine/feed.py True`, `core/engine/__init__.py True`, `core/engine/orders.py False`; tests/macro_m5_integration.py:344-345 `for rel in UNTOUCHED:` / `assert z.read(find(rel)) == (ROOT / rel).read_bytes(), f"{rel} differs from the pre-v2 backup"`
   IMPACT: The diff clause is live, not skipped (it returns early only when the zip is absent, :342-343).
* [split map] The split map records the same rule and says retiring it is TRADEGEN's choice.
   EVIDENCE: research_notes/QUANTGEN TRADEGEN split map/split_map.md:282 `- TRADEGEN inherits the same test, the backup zip and the rule. If TRADEGEN later wants to rework its engine, that test is TRADEGEN's to retire.`
   IMPACT: If the execution design wants to reuse `EngineRuntime`, the plan must include an explicit, reviewed retirement of test_s4's clauses.

## 4. The read-only guards (what blocks real orders and account access)

* [T-RO-01 forbidden text] Case-insensitive substrings banned in code (docstrings and comments stripped): KIS order verbs and TR ids, Upbit `/v1/orders`, `/v1/withdraws`, `/v1/deposits/generate_coin_address`, Binance `/api/v3/order`, `/sapi/v1/capital/withdraw`, `/sapi/v1/capital/deposit`, `private_key`, `seed_phrase`. Case-sensitive: `KIS_ACCOUNT`, `CANO`, `ACNT_PRDT_CD`. Path regex: any `/uapi/.../trading/`.
   EVIDENCE: tests/macro_m0_harness.py:28-36 `FORBIDDEN_TEXT_CI = (` ... `"/v1/orders", "/v1/withdraws", "/v1/deposits/generate_coin_address",   # Upbit` ... `FORBIDDEN_TEXT_CS = ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD")           # an account number implies an order path` / `FORBIDDEN_PATH_RE = re.compile(r"/uapi/[^\s'\"]*/trading/")           # every KIS trading domain`
   IMPACT: Every KIS account endpoint (balance inquiry included) is a `/trading/` path that sends `CANO` and `ACNT_PRDT_CD`. Even read-only KIS account inquiry trips three T-RO-01 checks.
* [T-RO-01 imports and calls] Any import of 21 order-client packages (ccxt, web3, pyupbit, binance, okx, bybit, pykis, mojito, ...) fails; calls named place_order, create_order, cancel_order, withdraw, transfer, deposit_address, sign_transaction and others fail; `.post/.put/.delete/.patch` on a URL string containing order, withdraw, transfer or deposit fails.
   EVIDENCE: tests/macro_m0_harness.py:38-52 `FORBIDDEN_IMPORTS = frozenset({` / `"ccxt", "web3", "pyupbit", "binance", ...` / `"mojito", "pykis", "kiwoom", "okx", "bybit", ...` / `FORBIDDEN_CALLS = frozenset({` / `"place_order", "submit_order", "create_order", "send_order", ...` / `MUTATING_HTTP = frozenset({"post", "put", "delete", "patch"})` / `MUTATING_URL_WORDS = ("order", "withdraw", "transfer", "deposit")`
   IMPACT: An order adapter written with stdlib/requests and neutral names would pass a naive reading but violates the intent. The narrow retirement must replace these with an allowlist: specific adapter files, specific endpoints.
* [T-RO-01 orders import allowlist] Only `core/engine/`, `core/skills/macro_daily.py` and `core/skills/pipeline.py` may import `core.engine.orders`; the check misses `from core.engine import orders`.
   EVIDENCE: tests/macro_m0_harness.py:58-59 `ORDERS_IMPORTERS_ALLOWED = ("core/engine/", "core/skills/macro_daily.py", "core/skills/pipeline.py")` / `ORDERS_NAMES = {"OrderBook", "SimulatedOrder", "OrderStatus", "order_id"}`
   IMPACT: A live module outside core/engine may not import the simulated book. compliance_guards closes the `from core.engine import orders` gap for core/compliance and core/odds only.
* [T-RO-01 scope] T-RO-01 scans `runtime_py()` (core/, data/, ui/, main.py, config.py) plus top-level `docs/*.py`, and only the macro workflow YAML.
   EVIDENCE: tests/macro_m0_harness.py:63-65 `def _scan_files() -> list[Path]:` / `files = runtime_py() + sorted(p for p in (ROOT / "docs").glob("*.py"))`; tests/acceptance.py:48-54 `for base in (ROOT / "core", ROOT / "data", ROOT / "ui"):` ... `files.extend([ROOT / "main.py", ROOT / "config.py"])`
   IMPACT: `paper_live/`, `grokteam/`, `tools/` and any new top-level package are never scanned. An execution package outside core/data/ui escapes every guard, so the design must either live under a scanned root or extend `runtime_py()`.
* [test_08] Raw text (docstrings and comments included), case-insensitive: order_cash, order-cash, place_order, submit_order, TTTC0802U, TTTC0801U, VTTC0802U.
   EVIDENCE: tests/acceptance.py:169-175 `def test_08_no_broker_order_path():` / `"""KIS is a brokerage API; this build implements quotations only."""` / `needles = ["order_cash", "order-cash", "place_order", "submit_order",` / `"TTTC0802U", "TTTC0801U", "VTTC0802U"]`
   IMPACT: KIS's own order endpoint is `/trading/order-cash` with TR ids TTTC0802U/0801U; any KIS order adapter needs test_08 retired for named files.
* [test_09] Raw text, case-sensitive: `KIS_ACCOUNT`, `CANO`, `ACNT_PRDT_CD` anywhere in runtime_py.
   EVIDENCE: tests/acceptance.py:178-182 `def test_09_no_account_credentials_requested():` / `"""Order submission needs an account number. Never ask for one."""` / `for name in ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD"):`
   IMPACT: KIS balance inquiry needs CANO/ACNT_PRDT_CD as request fields, so account inquiry alone already needs test_09 retired for one file. Note: upper-case `CANO` also matches `CANONICAL`.
* [T-RO-02 allowlist] The KIS allowlist is a frozen set of exactly 25 `/uapi/.../quotations/` paths in config.py; tests assert it is a frozenset of 25, equals the set of paths used in three files, and holds no `/trading/`, `/oauth2/` or "account" path.
   EVIDENCE: config.py:186-190 `# Read-only guard (v2 M1, TASK-M1-02; spec P0, T-RO-02): the frozen allowlist of KIS quotation endpoints.` ... `KIS_QUOTATION_ALLOWLIST = frozenset({`; tests/macro_m1_pit.py:1046-1051 `assert len(allow) == 25 and all("/quotations/" in p and p.startswith("/uapi/") for p in allow)` ... `assert used == allow`; tests/macro_m1_integration.py:233 `assert not any(("/trading/" in p) or ("/oauth2/" in p) or ("account" in p) for p in allow)`
   IMPACT: Do not add account paths to this allowlist. A KIS account adapter needs its own separate, equally frozen allowlist and its own choke point.
* [T-RO-02 choke point] `KISClient._get` calls `check_quotation_path` as its first statement, before credentials are read; the test refuses `/trading/inquire-balance` by name and asserts credentials are not read first.
   EVIDENCE: data/krx/kis_client.py:206 `check_quotation_path(path)                  # T-RO-02: before credentials, before any request`; tests/macro_m1_pit.py:1054-1057 `trading = "/uapi/domestic-stock/v1/" + "trading/" + "order-" + "cash"` / `for bad in (trading, "/uapi/domestic-stock/v1/" + "trading/inquire-balance", "/oauth2/tokenP", "", None,`; :1077 `assert calls == [], "credentials were read before the path check"`
   IMPACT: Copy this pattern (path check before credentials) for every new adapter. Leave `KISClient._get` as the quotation-only choke point; a balance call must not go through it.
* [T-RO-02 attestation] Whether the KIS app key can trade is an owner attestation, default "unknown", never probed through a trading path.
   EVIDENCE: tests/macro_m1_pit.py:1090-1091 `raise NotRun("OWNER: KIS credentials and the 20-session quote-field check (M1-01); whether the app key can trade is "` / `"recorded as an owner attestation (default 'unknown'), never probed through a trading path (F-3)")`; docs/kis_quote_check.py:54 `def not_run_record(session: date, *, app_key_can_trade: str = "unknown") -> dict:`
   IMPACT: The same KIS app key (in `.env`) may already be trade-capable. The design must assume it is.
* [compliance guards, core-wide] In every file of core/: no raw `private_key`/`seed_phrase` (comments included) and no function named transfer, withdraw or deposit_address.
   EVIDENCE: tests/compliance_guards.py:31-32 `CORE_RAW_CI = ("private_key", "seed_phrase")            # these two hold for every file in core/ (contract section 0)` / `DEF_NAMES = frozenset({"transfer", "withdraw", "deposit_address"})`; :244 `hits = [h for rel, src in _scope(CORE).items() for h in _def_hits(rel, src)]`
   IMPACT: An exchange adapter under core/ cannot define `withdraw()`. D11 withdrawals are manual today anyway; keep it that way unless a separate decision says otherwise.
* [compliance guards, compliance+odds only] The full raw-text list, the forbidden-module ban (core.engine.orders in every form, forward_sim, refusal, context modules) and the dynamic-import ban cover core/compliance and core/odds; the HTTP-verb ban, the network-module ban and the import allowlist cover core/compliance only.
   EVIDENCE: tests/compliance_guards.py:233 `hits = [h for rel, src in _scope(COMPLIANCE, ODDS).items() for h in _raw_hits(rel, src)]`; :269 `hits = [h for rel, src in _scope(COMPLIANCE).items() for h in _http_hits(rel, src)]`; :300-301 `hits = [h for rel, src in _scope(COMPLIANCE, ODDS).items()` / `for h in _forbidden_hits(rel, src) + _dynamic_hits(rel, src)]`; :340 `hits = [h for rel, src in _scope(COMPLIANCE).items() for h in _allowlist_hits(rel, src)]`
   IMPACT: The gate stays network-free. Adapters must live outside core/compliance and core/odds and call into them.
* [crypto client raw guard] A separate expansion test bans `/v1/orders`, `/v1/withdraws`, `/api/v3/order`, `private_key`, `seed_phrase`, `import ccxt`, `import web3` in the raw source of data/crypto/crypto_client.py.
   EVIDENCE: tests/expansion_acceptance.py:154-156 `src = (ROOT / "data" / "crypto" / "crypto_client.py").read_text(encoding="utf-8")` / `for forbidden in ("/v1/orders", "/v1/withdraws", "/api/v3/order", "private_key", "seed_phrase", "import ccxt", "import web3"):`
   IMPACT: An Upbit order path must not be added to crypto_client.py. Put it in a new module, and list this test among the guards to retire narrowly.
* [disclaimer pinned] The UI disclaimer "read-only research desk with no order path" is pinned by a test.
   EVIDENCE: tests/macro_ui_components.py:16-17 `DISCLAIMERS = (... "Not investment advice: QUANTGEN is a read-only research desk with no order path.")`; ui/research_view.py:33 the same string
   IMPACT: Once a live path exists, this text becomes false. The execution plan must change the text and its test together.
* [README P0 / status] The README says no order path exists and the guards are retired only through TRADEGEN's safety design (gate, per-session arming, loss limits, kill switch, order audit log).
   EVIDENCE: README.md:8-13 `- **Status (2026-10-23): no order path exists.** ... Those guards are` / `retired only through TRADEGEN's own safety design: a Korean compliance gate,` / `execution the owner arms per session, hard loss limits, a kill switch and an` / `order audit log.`; README.md:399-401 `**P0. Read-only by construction.** ... KIS is used for read-only quotations only.`
   IMPACT: The execution plan updates README P0 and the status line in the same change that retires each guard.
* [split map on guards] The split map says any TRADEGEN execution path must retire these guards explicitly, and that the scans never see paper_live/ or grokteam/.
   EVIDENCE: research_notes/QUANTGEN TRADEGEN split map/split_map.md:541-543 `- The order-path scans `test_08`/`test_09` read only `runtime_py()` ...` / `- Why: section 4.3 notes only test_s4 as TRADEGEN's to retire. Any TRADEGEN execution path, and its Korean-law review, must retire these guards explicitly, not by a silent edit. Extending `runtime_py()` to every package is a cheap first step in both programs.`
   IMPACT: First step of the execution plan: widen `runtime_py()` (or the guard scope) before any adapter lands, so the retirement is an allowlist of named files.

## 5. The compliance gate as execution will use it

* [gate is pure] `gate.py` reads only the intent and a sealed Context: no clock, no file, no network.
   EVIDENCE: core/compliance/gate.py:3-4 `Pure: no clock, no file, no network, no time zone. It reads only the intent and a Context that model.is_sealed` / `accepts (P5). decide() never raises`
   IMPACT: Execution supplies time, positions and session; the gate only judges.
* [permit] `permit(intent, ctx)` returns a Permit only for ALLOW/ALLOW_EXIT, registered in a process-local WeakValueDictionary.
   EVIDENCE: core/compliance/gate.py:566 `_ISSUED: weakref.WeakValueDictionary = weakref.WeakValueDictionary()     # id(permit) -> permit, as model._SEALED`; :569-581 `def permit(intent, ctx) -> model.Permit | None:` ... `_ISSUED[id(issued)] = issued`
   IMPACT: Permits do not survive a restart or serialisation; the execution layer must re-permit after a restart (the plan's contract says so too, docs/superpowers/plans/2026-10-23-compliance-gate.md:17322 `the execution spec re-permits after a restart.`).
* [verify_permit] It re-checks: issued here, same intent hash (covers reservation_id), decision now ALLOW/ALLOW_EXIT, same session id, same Asia/Seoul date, and state hash equal or a higher seq. Single use is NOT checked.
   EVIDENCE: core/compliance/gate.py:593-605 `if type(p) is not model.Permit or _ISSUED.get(id(p)) is not p:` ... `for what, same in (("session", ctx_now.session.session_id == p.session_id),` / `("date", ctx_now.date == p.date),` / `("state", d.state_hash == p.state_hash or state.seq > p.state_seq)):`
   IMPACT: Execution must add single use (consume on send) and an audit row per verify, with a fresh `load_context` for `ctx_now`.
* [Permit fields] Permit = decision_id, intent_hash, state_hash, state_seq, session_id, reservation_id, date.
   EVIDENCE: core/compliance/model.py:202-210 `class Permit:` / `decision_id: str` / `intent_hash: str` / `state_hash: str` / `state_seq: int` / `session_id: str | None` / `reservation_id: str | None` / `date: date`
   IMPACT: The audit log can key on decision_id and intent_hash; it carries no venue order id, so execution adds that.
* [reservations are caller-supplied] Reservations live in `Exposure.reservations` inside caller-supplied `Positions`; nothing in core/compliance stores them.
   EVIDENCE: core/compliance/model.py:96-109 `class Exposure:` / `held_krw: float  # everything held there, settlement included` / `reservations: Mapping[str, float] = field(default_factory=dict)        # reservation_id -> notional_krw` / `promised_sell_units: ...` / `class Positions:` / `"""Caller-supplied until the execution spec adds live reads (P19)."""`
   IMPACT: Execution owns a durable reservation store (atomic, under a lock) and builds `Positions` from live balances plus that store.
* [grey cap math] The OKX cap counts held value plus every other reservation plus this notional against cap times equity.
   EVIDENCE: core/compliance/gate.py:334-339 `held = exposure.held_krw if exposure is not None else 0.0` / `own = intent.reservation_id` / `others = (sum(v for k, v in exposure.reservations.items() if own is None or k != own)` / `if held + others + intent.notional_krw > cap * ctx.equity_krw:`
   IMPACT: `held_krw` must include USDT/USDC on OKX at a live KRW price; stale prices understate it.
* [promised sell units] A sell is valid only up to holdings minus units promised to unexpired sell permits.
   EVIDENCE: core/compliance/gate.py:475-479 `def _within_free(intent, ctx) -> bool:` / `"""quantity <= holdings minus the units already promised to unexpired sell permits."""`
   IMPACT: Execution tracks promised units per open sell permit and expires them.
* [gate never reads armed or halts] decide() checks only owner-log validity, active state and code_signed for new exposure; it never reads `ctx.session.armed`, `halted_floors` or the loss limits.
   EVIDENCE: core/compliance/gate.py:423-426 `def _preconditions(ctx, state) -> list[str]:` / `out = [] if ctx.owner.ok and _usable(ctx.active) and state is ctx.active else [_why_no_active(ctx)]` / `return out + ([] if ctx.code_signed is True else ["unsigned code"])`; grep of gate.py for `armed` and `halted` finds nothing; docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:239 `carried to the execution spec: ack accepted with session None and gate never reads ctx.session.armed`
   IMPACT: The kill switch, the armed check, the D3 floor halt and the daily loss limit are execution's job, or a signed gate change. Decide which explicitly.
* [ack keyed on session] Per-session acks match `(ctx.session.session_id, row.id, warning_sha256)`; a None session id is accepted.
   EVIDENCE: core/compliance/gate.py:318 `if (ctx.session.session_id, row.id, sha) in ctx.owner.session_acks:`; docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:143 `Task 8: minor (deferred): per-session ack accepted with session_id None`
   IMPACT: Execution must always pass a non-empty `session_id` to `load_context` when armed.
* [D16 block is unconditional] A row with `requires.live` always blocks with "needs live broker evidence (execution spec)"; the live vocabulary exists but no Context field carries live evidence.
   EVIDENCE: core/compliance/gate.py:307-308 `if row.requires_live:                                              # D16: no owner event satisfies these` / `out.append(f"needs live broker evidence (execution spec): {row.id}")`; core/compliance/rules.py:67-68 `LIVE_REQUIREMENTS = frozenset({"deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m", "cash_krw_30m",` / `"broker_approval", "collateral_105pct"})`
   IMPACT: Lifting D16 row by row needs a new Context field for live evidence plus a gate change, both inside the signed code hash.
* [shared reservation id] Two permits sharing one reservation_id both verify.
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:155 `Task 9: minor (deferred): two permits sharing one reservation_id both verify (120k vs a 100k cap); add "a reservation id names exactly one intent, reserved at its notional" to P36 / A.5.2 for the execution spec`
   IMPACT: The reservation store enforces one reservation id per intent at its notional.
* [permit edited in place] A registered permit changed with `object.__setattr__` still verifies.
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:156 `Task 9: minor (deferred): a registered permit edited in place (object.__setattr__) still verifies (P5 discipline; digest-at-issue hardening possible)`
   IMPACT: Candidate hardening for the compliance follow-up, or the execution layer stores a digest at issue.
* [positions must be live] Notional and held_krw must come from live prices.
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:244 `Final: carried — odds plan must not send a zero stake to screen() (it now reports malformed: notional_krw); execution spec must derive notional and held_krw from live prices (P19)`
   IMPACT: The account-inquiry step is a prerequisite for live permits.

## 6. Owner log, sessions, halts and limits

* [kinds] Owner (signed) kinds include `session_armed`, `session_ack`, `limit_set`, `cap_set`, `withdrawal_address`; system (unsigned) kinds are only `system_halt` and `system_disarm`.
   EVIDENCE: core/compliance/owner.py:26-28 `OWNER_KINDS = frozenset({"approved", "code_approved", "course_completed", "broker_approval", "age_of_majority",` / `"cap_set", "limit_set", "withdrawal_address", "session_armed", "session_ack", "transfer_ack", "key_rotated"})` / `SYSTEM_KINDS = frozenset({"system_halt", "system_disarm"})`
   IMPACT: Arming a session needs the owner's signer. Execution writes halts and disarms itself.
* [schemas] `session_armed {session_id}`, `limit_set {total_loss_floor_krw >= 0, daily_loss_krw > 0}`, `system_halt {floor_krw >= 0}`, `system_disarm {session_id, reason}`.
   EVIDENCE: core/compliance/owner.py:151-160 `"limit_set": {"total_loss_floor_krw": lambda v: _number(v) and v >= 0,` / `"daily_loss_krw": lambda v: _number(v) and v > 0},` ... `"session_armed": {"session_id": _text},` ... `"system_halt": {"floor_krw": lambda v: _number(v) and v >= 0},` / `"system_disarm": {"session_id": _text, "reason": _text},`
   IMPACT: `system_halt` carries only a floor, no reason, venue or session; a daily-loss stop or operator kill may need `system_disarm` instead. Any new system kind changes owner.py, the signer and the code hash.
* [append_system_entry] Appends one unsigned line under a sidecar OS lock, re-checks the chain first, fsyncs; ValueError on an owner kind or bad data, RuntimeError on a broken chain.
   EVIDENCE: core/compliance/owner.py:400-414 `def append_system_entry(kind: str, data: dict, now: datetime) -> tuple[int, str]:` ... `if kind not in SYSTEM_KINDS:` / `raise ValueError(f"{kind!r} is not a system kind: owner entries come only from the owner's signer")` ... `raise RuntimeError(f"owner log is broken ({why}); nothing appended")`
   IMPACT: Under a BROKEN log a halt cannot be recorded in the log, so the kill switch also needs a local fail-safe (in-memory and the engine state file) that does not depend on the append.
* [append errors carried] Unhandled TypeError/OSError and torn last lines are open.
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:239 `append_system_entry TypeError/OSError; torn alerts.jsonl / owner.jsonl last line repair`
   IMPACT: The kill-switch caller wraps the append and treats any failure as "halt locally and alert".
* [halts tighten floors] A loosening never applies after the first halt, and a set floor is never below the highest halted floor.
   EVIDENCE: core/compliance/owner.py:525-528 `def loosening_counts(e, on) -> bool:` / `return (e.utc <= now_utc and on < day` / `and (first_halt is None or (e.seq < first_halt and on < halt_day))`; :557-558 `if halt_floor is not None and "total_loss_floor_krw" in values:     # never below a halted floor, for good (D12)`
   IMPACT: "Halts for good" (D3) is only half-encoded: limits cannot loosen, but nothing forbids re-arming. The execution design must say whether any `system_halt` forbids arming forever.
* [armed sessions] `armed_sessions` holds session ids with a `session_armed` stamped by now and no later `system_disarm`; `load_context` sets `session.armed`.
   EVIDENCE: core/compliance/owner.py:514-522 `if e.kind == "session_armed":` ... `if e.utc <= now_utc:` / `armed.add(sid)` / `elif e.kind == "system_disarm":` / `armed.discard(e.data["session_id"])`; :1016 `session=model.SessionState(session_id=session_id, armed=session_id in owner.armed_sessions),`
   IMPACT: Disarm = `system_disarm {session_id}`. Arm = an owner-signed `session_armed`. A session id is never reusable after a disarm unless re-signed.
* [halt dating parked] A halt stamped ahead under a past-midnight clock skew can let a same-day loosening through.
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:188 `Task 12: parked — a halt stamped ahead (system clock past Seoul midnight) with no later line stamped on/before the loosening's date lets a same-date loosening through after the halt (H2)`
   IMPACT: Execution writes system entries with a trustworthy `now`; it should guard against clock skew before writing `system_halt`.
* [load_context] `load_context(now, positions, *, session_id=None)` is the only Context producer; ValueError only for a naive `now`; anything else fails closed.
   EVIDENCE: core/compliance/owner.py:964-969 `def load_context(now: _dt.datetime, positions: model.Positions, *, session_id: str | None = None) -> model.Context:` / `"""The only producer of Context (spec 6.4). Hashes the code on disk, verifies the owner log ...`
   IMPACT: Each call hashes the code closure and verifies the whole log. Call it per decision and per send, and budget its cost (not measured here).
* [code hash closure] The signed code closure is core/compliance and core/odds plus their in-repo import closure and two RECORD files; nothing else.
   EVIDENCE: core/compliance/owner.py:768-773 `"""Sorted (relative POSIX path, sha256) of the D14 code closure (P6): core/compliance/*.py and core/odds/*.py,` ... `todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]`
   IMPACT: Execution adapters are not in the signed code hash unless the design adds their directory here, which is itself a signed change.
* [acting modules] T-CTX-01 treats `core.compliance.` and `core.odds.` as acting modules, alongside core.engine., core.quant., core.rules.
   EVIDENCE: core/ficc/context_log.py:71-73 `ACTING_MODULE_PREFIXES = ("core.quant.", "core.engine.", "core.rules.", "core.calendars", "core.markets",` ... `"core.compliance.", "core.odds.")             # spec 4: the gate and the odds engine act`
   IMPACT: A new execution package under core/ should be added to this tuple.

## 7. KIS client and keys

* [KIS endpoints] The KIS client is quotation-only. Its docstring says four endpoints, but the allowlist holds 25 quotation paths used by kis_client.py, data/kis_markets.py and docs/kis_quote_check.py.
   EVIDENCE: data/krx/kis_client.py:7-8 `file, or anywhere in this repository.** This client exposes exactly four` / `read-only quotation endpoints:`; config.py:188-189 `The 24 paths in use (kis_client.py, data/kis_markets.py) plus the asking-price path` / `# of the owner-run quote-field check (docs/kis_quote_check.py). Never a /trading/, /oauth2/ or account path.`
   IMPACT: The docstring is stale. There is no balance, order, cancel or account endpoint anywhere.
* [KIS token] One bearer token is cached at `config.state_root()/kis_token.json`, computed at import; issuance is a one-attempt POST to `/oauth2/tokenP`; the cache holds the token, never the key.
   EVIDENCE: data/krx/kis_client.py:53 `_TOKEN_PATH = config.state_root() / "kis_token.json"     # never QUANTGEN's ~/.nextgen token: a refresh would clobber it`; :181-186 `resp = _once.post(` / `f"{self.base_url}/oauth2/tokenP",` / `json={"grant_type": "client_credentials",` / `"appkey": app_key, "appsecret": app_secret},`; :24 `cache file holds a token, never the appkey/appsecret.`
   IMPACT: A trading adapter can share the token (same app key) or get its own. The token endpoint is not behind `check_quotation_path`.
* [KIS token burn] The token is issued before the final-target check can refuse its write.
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:81 `Task 2: minor (deferred): KIS token is issued before the final-target check refuses, burning an issuance per call when the target is bad`; data/krx/kis_client.py:158 `target = checked_target(_TOKEN_PATH, "KIS token cache")      # A0: outside the try, so a refusal propagates`
   IMPACT: Issuance is limited to once a minute (section 9). An adapter must not mint a token per call.
* [KIS env vars] Credentials come from `KIS_APP_KEY`/`KIS_APP_SECRET` via `config.kis_credentials()`; base URL defaults to the real host; `.env` is loaded by `load_dotenv()` at config import.
   EVIDENCE: config.py:176-184 `def kis_ready() -> bool:` / `return _present("KIS_APP_KEY") and _present("KIS_APP_SECRET")` ... `KIS_BASE_URL = _clean("KIS_BASE_URL") or "https://openapi.koreainvestment.com:9443"`; config.py:26-28 `from dotenv import load_dotenv` / `load_dotenv()`
   IMPACT: The default is the real (not mock) server. A trading adapter should name its base URL explicitly and refuse the mock/real mix-up.
* [KIS pacing] All KIS calls in the process share one pacer at about 8 requests a second; EGW00201 is retried once.
   EVIDENCE: data/krx/kis_client.py:82-83 `_RATE_LIMITED = "EGW00201"` / `_MIN_GAP_S = 0.12                       # about 8 requests a second`
   IMPACT: Order and quote calls should share this budget, or the adapter takes its own lock with the same gap.
* [.env keys] `.env` (QUANTGEN's copy) sets KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_8 and KIS_ACCOUNT_PD; it has no UPBIT_* and no OKX lines. Values were not read.
   EVIDENCE: names-only scan of `.env`: line 28 `KIS_APP_KEY set`, 29 `KIS_APP_SECRET set`, 30 `KIS_ACCOUNT_8 set`, 31 `KIS_ACCOUNT_PD set`; `.env.example`:34-35 `UPBIT_ACCESS_KEY blank`, `UPBIT_SECRET_KEY blank`; `.gitignore`:1 `.env`
   IMPACT: An account number is already on disk, and the KIS app key is shared with QUANTGEN (token, rate limit). The "shared .env keys pending" owner action is still open. The design should require TRADEGEN-own keys before arming.
* [shared keys, documented] The split map records that the copied `.env` shares KIS, FMP and Anthropic keys with QUANTGEN and holds KIS_ACCOUNT_PD.
   EVIDENCE: research_notes/QUANTGEN TRADEGEN split map/split_map.md:517-518 `It holds ... `KIS_ACCOUNT_PD` (L31) ... Values were not read.` / `TRADEGEN gets the same KIS, FMP and Anthropic keys, so the two share rate limits, token and quota. ... TRADEGEN's `.env` should get the state-dir overrides and, where possible, its own API keys.`
   IMPACT: Same as above.
* [live calls in cockpit suite] cockpit test_21 calls `KRXGateway().daily("005930")`, which uses the real KIS client when keys are present.
   EVIDENCE: tests/acceptance.py:318-322 `def test_21_krx_gateway_degrades_with_a_reason():` ... `gateway = KRXGateway()` / `for answer in (gateway.daily("005930"), gateway.filings("005930")):`; data/krx/gateway.py:90-92 `if self.kis.ready:` / `try:` / `rows = self.kis.daily(ticker, start=start, end=end)`
   IMPACT: Once the KIS key can trade, a test suite run holds a trade-capable credential on the network. Execution tests must be hermetic; consider making test_21 hermetic first.
* [HTTP session] The shared `data.net.session` retries only GETs on 502/503/504 and never replays a POST after a response.
   EVIDENCE: data/net.py:17-18 `* **POSTs are never replayed on a response or a read error.** The KIS token` / `endpoint is itself rate-limited, and issuing a token twice is not harmless.`; :43-50 `RETRY = Retry(` / `total=2,` ... `allowed_methods=("GET",),`
   IMPACT: Its docstring also says "A connection that never reached the server is still retried, for any method" (data/net.py:19-20). An order POST must not use this session; send once and reconcile by client order id.

## 8. Crypto clients (Upbit, Binance, OKX)

* [Upbit balance exists] `UpbitAccount.balances()` already calls authenticated `GET /v1/accounts` with a stdlib HS512 JWT, keys from `UPBIT_ACCESS_KEY`/`UPBIT_SECRET_KEY`, documented as 자산조회 scope only.
   EVIDENCE: data/crypto/crypto_client.py:13-16 `* **Upbit account, 자산조회 (balance) scope only** — `GET /v1/accounts` with a` / `stdlib HS512 JWT when UPBIT_ACCESS_KEY / UPBIT_SECRET_KEY are set.`; :308-319 `class UpbitAccount:` / `"""Balances only. There is no order path in this class or this module."""` ... `page = _get(f"{UPBIT}/accounts", headers={"Authorization": f"Bearer {token}"}, label="Upbit accounts")`
   IMPACT: Upbit account inquiry needs no guard retirement: it already passes every scan. It is the natural first live read for `Positions` (holdings, `locked`, `avg_buy_price`). The keys are absent from `.env`.
* [Upbit JWT] `upbit_jwt` supports the query_hash needed by parameterised private calls.
   EVIDENCE: data/crypto/crypto_client.py:295-302 `def upbit_jwt(access_key: str, secret_key: str, query: str = "") -> str:` ... `payload["query_hash"] = hashlib.sha512(query.encode()).hexdigest()`
   IMPACT: Reusable for order calls, but an order call must live in a new module (crypto_client.py is guarded, section 4).
* [Upbit GET helper] The crypto `_get` is GET-only, one attempt through the shared session, raises on 429 and non-200.
   EVIDENCE: data/crypto/crypto_client.py:112-124 `def _get(url: str, params: dict | None = None, headers: dict | None = None, *, label: str) -> Any:` ... `resp = _requests.get(url, ...` ... `if resp.status_code == 429:` / `raise CryptoError(f"{label}: rate limited (HTTP 429); slow down")`
   IMPACT: It also goes through `data.net.session`, which retries GETs; fine for reads, not for writes.
* [Upbit balance caller] Only the crypto UI page (and one test) calls `UpbitAccount().balances()`.
   EVIDENCE: ui/crypto_page.py:90-93 `if config.upbit_ready() and source == "live":` ... `bal = UpbitAccount().balances()`; tests/expansion_acceptance.py:181 `bal = cc.UpbitAccount().balances()`
   IMPACT: No engine path reads live balances today.
* [no OKX or Binance private client] There is no OKX client at all and no Binance account code; Binance is public data only. OKX appears only in the rules table, the gate floor, owner caps, venues.yaml and the signer.
   EVIDENCE: data/crypto/crypto_client.py:24-25 `* No transaction is ever signed. No account on an unregistered foreign` / `exchange is assumed: Binance is data only.`; grep `(?i)okx` over core, data, ui, tools finds only core/compliance/gate.py, kr_rules.yaml, owner.py, rules.py, core/odds/venues.yaml, tools/signer/sign.py; tests/macro_m0_harness.py:40 `"mojito", "pykis", "kiwoom", "okx", "bybit", ...`
   IMPACT: An OKX adapter (public or private) is entirely new, and the `okx` package name is import-banned, so it must be stdlib/requests. Grep for `OK-ACCESS` found nothing.
* [OKX venue facts] venues.yaml lists OKX markets BTC/USDT and BTC/USDC and one unverified BTC deposit network; Upbit only BTC/KRW and USDT/KRW.
   EVIDENCE: core/odds/venues.yaml:42-48 `okx:` / `settlement: [USDT, USDC]` / `markets: [[BTC, USDT], [BTC, USDC]]` ... `- {symbol: BTC, network: bitcoin, tag_required: false}` / `source: "UNVERIFIED: owner to confirm before approval"`
   IMPACT: An adapter's tradable set equals the approved venue facts. The odds plan's venues.yaml edits change the approved sha and need a new owner approval.

## 9. Venue facts from the research notes (API scopes, IP lists, limits)

* [Upbit scopes and IPs] Upbit private calls use an HS512 JWT; up to 10 IPs per key; balance needs the 자산조회 scope; IP registration is mandatory for keys with 주문하기 (order) or 출금하기 (withdraw) scope.
   EVIDENCE: research_notes/QUANTGEN asset coverage expansion/crypto_wallets_connectivity.md:28-29 `"API Key per maximum 10 IPs can be registered"; secret shown only at issuance` / `- IP registration is mandatory when a key is issued with 주문하기 (order) or 출금하기 (withdraw) scope`
   IMPACT: A trading key is IP-bound to the owner's PC. The design keeps order and withdraw scopes on separate keys and never requests 출금하기.
* [Upbit rate limits] Quotation 10 req/s per IP per group; exchange `default` group 30 req/s; `order` group 12 req/s; `Remaining-Req` header.
   EVIDENCE: crypto_wallets_connectivity.md:27 `- Rate limits: all quotation (public) endpoints 10 req/s per IP in five groups ... exchange (private) `default` group 30 req/s per pocket (covers balance), `order` 12/s; header `Remaining-Req: group=default; min=1800; sec=29``
   IMPACT: Pace order calls under 12/s and read `Remaining-Req`.
* [Upbit key expiry] Upbit keys last one year and cannot be extended.
   EVIDENCE: crypto_wallets_connectivity.md:30 `- Key validity: "Open API Key 토큰의 유효 기간은 1년이며 연장은 불가합니다"`
   IMPACT: Arming should refuse a key past its owner-recorded expiry.
* [key scope risk] A key issued with 주문하기 scope is a live order credential on disk.
   EVIDENCE: crypto_wallets_connectivity.md:296 `a key accidentally issued with 주문하기 scope would be a live order credential on disk — Settings must tell the operator to issue 자산조회-only`
   IMPACT: Use two Upbit keys: an inquiry key (자산조회) for balances and a trading key (주문하기, never 출금하기) used only while armed.
* [own-name wallet rule and Travel Rule] Exchange-to-personal-wallet transfers only to an own-name verified wallet (FIU notice 2026-08-20); Travel Rule data on VASP transfers of KRW 1,000,000 or more.
   EVIDENCE: crypto_wallets_connectivity.md:22 `transfers from an exchange to a personal wallet only to a "본인명의 확인 지갑" (own-name verified wallet)`; :20 `- Travel Rule: from 2022-03-25 a VASP transferring ≥ ₩1,000,000 of virtual assets to another VASP must send sender/recipient names and addresses`
   IMPACT: Withdrawals stay manual in the exchange app (D11 recovery and the core-wide `withdraw` def ban); the design need not automate them.
* [OKX public data] OKX public candles `/api/v5/market/candles`, 20 req per 2 s; the base host is unverified. Nothing in the repo covers OKX private-API auth, scopes, passphrase or IP lists.
   EVIDENCE: crypto_wallets_connectivity.md:98 `- OKX `GET /api/v5/market/candles?instId=&bar=&after=&before=&limit=<≤300>` ... 20 req / 2 s; no auth for public data ... which is current: UNVERIFIED.`
   IMPACT: An OKX trading adapter needs new, source-checked research (API key permissions, passphrase, IP binding, withdrawal whitelist) before design.
* [research refusals] The connectivity note's design refuses every order, withdrawal and transfer endpoint on any key, and never asks for a Binance/Bybit/OKX key.
   EVIDENCE: crypto_wallets_connectivity.md:382 `- **No order submission, cancellation, withdrawal, deposit-address or transfer endpoint** on any exchange ... none of them, on any key, ever.`; :385 `the app never asks for a Binance/Bybit/OKX API key.`
   IMPACT: That was QUANTGEN's stance. The execution design must state where TRADEGEN departs from it and why (D2, D6, D8).
* [KIS account fields] In KIS's own samples, only `/trading/` paths send CANO; every quotation path sends none.
   EVIDENCE: research_notes/QUANTGEN asset coverage expansion/kis_api_audit.md:28 `- Paths under `/quotations/`, `/ranking/`, `/finance/`, `/ksdinfo/` are read-only by construction; only `/trading/` paths carry `CANO`.`
   IMPACT: Confirms KIS account inquiry requires retiring the `/trading/` and CANO guards for one adapter file.
* [KIS token and rate rules] Tokens last 24 h; reissue at most once a minute (EGW00133); about 20 req/s on real accounts (secondary sources), lower on mock; each issuance sends a KakaoTalk notice.
   EVIDENCE: kis_api_audit.md:185 `Tokens come from POST `/oauth2/tokenP` (client_credentials + appkey + appsecret), live 24 hours, and KIS throttles issuance to once per minute (error EGW00133 on a repeat)`; :190 `"토큰 유효시간 1일, 6시간 이내 발급신청시는 기존 토큰값과 동일, 발급시 알림톡 발송"`
   IMPACT: One cached token per app key. Two programs sharing the key share the throttle.
* [KIS mock server] The mock REST host is `openapivts.koreainvestment.com:29443`, and mock tr_ids swap a leading T/J/C for V.
   EVIDENCE: kis_api_audit.md:98 `REST real `https://openapi.koreainvestment.com:9443`, mock `https://openapivts.koreainvestment.com:29443``; :23 `the common helper rewrites a leading `T`/`J`/`C` to `V` for mock`
   IMPACT: A mock-first rollout is possible. The guard needles include `VTTC0802U` (the mock order TR id), so mock orders also trip test_08.

## 10. paper_live: "live" means live data, simulated money

* [paper engine] paper_live's engine trades simulated accounts on live 1-minute closes; the same code runs live and in replay.
   EVIDENCE: paper_live/engine.py:1-4 `"""Live paper-trading engine: data, probability model, simulated accounts, two rule sets.` / `The engine is clock-driven: `Engine.step(now, closes)` sees only 1-minute closes stamped` / `at or before `now` (the caller truncates), so the same code runs live and in replay.`; paper_live/config.py:16 `START_EQUITY = 500.0`
   IMPACT: "Live" is a data mode, not real money. Nothing in paper_live sends an order.
* [paper run] `run_live` loops until the window end and flattens every simulated account; `--dry` does one tick.
   EVIDENCE: paper_live/run_live.py:1-4 `"""Run the live paper session until WINDOW_END_UTC, then flatten every account.` / `python -m paper_live.run_live            # live loop (resumes from out/live/state.json)`
   IMPACT: Its state lives in `paper_live/out*/` inside the repo, not under `~/.tradegen` (paper_live/engine.py:31 `OUT = Path(__file__).resolve().parent / ("out" if C.PROFILE == "base" else f"out_{C.PROFILE}")`).
* [paper accounts] A paper `Account` holds cash, peak, halted flag and positions in USD.
   EVIDENCE: paper_live/engine.py:384-397 `class Account:` / `name: str` ... `cash: float = C.START_EQUITY        # start equity + realised net P&L (costs included)` / `peak: float = C.START_EQUITY` / `halted: bool = False`
   IMPACT: A source of shadow-mode ideas only; paper_live is unscanned by the guards and frozen for QUANTGEN's H2 study, so do not build on it.
* [paper tests] tests/paper_live_acceptance.py checks costs, the cost gate, state resume and snapshots offline; it has no order or account test.
   EVIDENCE: tests/paper_live_acceptance.py:1-7 `"""Acceptance checks for the paper_live harness fixes of 2026-10-18 (after live paper Runs 1 and 2).` / `No network: every check builds synthetic 1-minute closes in memory and an Engine on a temp` / `directory.`
   IMPACT: Nothing to reuse for execution tests beyond the offline style.
* [engine tests] tests/engine_acceptance.py defends the operator engine's contract clauses: starts disarmed, manual ack after a halt, restart never restores armed, halt from any state, duplicate triggers refused, caps reject with a reason.
   EVIDENCE: tests/engine_acceptance.py:51 `def test_01_engine_starts_disarmed():`; :55 `def test_02_halt_requires_manual_acknowledgement_before_arming():`; :68 `def test_03_restart_never_restores_armed():`; :89 `def test_05_emergency_stop_works_from_any_state_and_never_raises():`; :125 `def test_09_duplicate_trigger_is_not_placed_twice():`
   IMPACT: Good templates for the live engine's acceptance tests (same clauses, plus signed arming and loss limits).

## 11. Alerts

* [alert channels] Channels are toast, push and email. The toast is a PowerShell subprocess; push and email are sent by the daily Claude task, only to OWNER_ALERT_EMAIL.
   EVIDENCE: core/compliance/alerts.py:1-5 `... `_toast()` shows a Windows notification; `log()` appends the` / `alerts.jsonl row ... The iOS` / `push and the email are sent by the daily Claude task, and only to OWNER_ALERT_EMAIL."""`; :18-21 `OWNER_ALERT_EMAIL = "sapientia@korea.ac.kr"` / `_CHANNELS = ("toast", "push", "email")`
   IMPACT: There is no event-driven alert path. A halt, a disarm or a refused send at 14:00 is only seen when the daily task runs. Execution needs its own immediate channel (at least the toast), and a design for push/email that respects "core/compliance never needs the network".
* [alerts.jsonl is check-only] `alerts.log()` accepts only a valid `--check` summary and anchors the owner log head.
   EVIDENCE: core/compliance/alerts.py:242-252 `def log(channel: str, result: str, summary: dict, now: datetime) -> None:` ... `if not _valid_summary(summary):` / `raise ValueError("log: not a --check summary")`
   IMPACT: The execution audit log is a separate file; do not write execution events into alerts.jsonl.
* [toast seam] `_toast` passes text through environment variables and tests patch it.
   EVIDENCE: core/compliance/alerts.py:216-221 `def _toast(title: str, body: str) -> bool:` / `"""P26 seam: one Windows toast through powershell.exe ... The` / `text travels in environment variables, never inside the script. Tests patch this and never run PowerShell."""`
   IMPACT: Reusable for an immediate halt alert.

## 12. Test harness facts an execution suite must respect

* [hermetic touchpoints] The macro hermetic guard patches a fixed list of network seams (crypto `_get`, KIS `_get`/`requests`/`_once`, `net.session.request`, socket connect, and more).
   EVIDENCE: tests/macro_acceptance.py:51-67 `def _touchpoints() -> list[tuple[object, str, object]]:` ... `(kis_client, "requests", _Refuse()), (kis_client, "_once", _Refuse()), (kis_client.KISClient, "_get", _boom),` ... `(socket.socket, "connect", _refuse_connect), (socket.socket, "connect_ex", _refuse_connect),`
   IMPACT: Every adapter's transport must be a module-level seam added to this list, so no suite can reach a venue.
* [suite list pinned] A compliance guard asserts the exact suite-list text in run_all.py and README.
   EVIDENCE: tests/compliance_guards.py:488-489 `assert "paper, grokteam or compliance" in (ROOT / "tests" / "run_all.py").read_text(encoding="utf-8")` / `assert "paper, grokteam or compliance" in (ROOT / "README.md").read_text(encoding="utf-8")`; tests/run_all.py:113 `help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam or compliance")`
   IMPACT: Adding an "odds" suite (the odds plan) or an "execution" suite breaks this test unless it is updated in the same change.

## 13. What execution builds on, and what it must retire narrowly

* [builds on] Reusable today without retiring anything: `load_context`/`decide`/`permit`/`verify_permit`; `append_system_entry` for halts and disarms; `UpbitAccount.balances()` for Upbit holdings; the `EngineState` semantics (disarmed start, manual re-arm, never-raising halt) as a pattern; `OrderBook.place`'s atomic duplicate guard as the idempotency pattern; the `check_quotation_path` "check before credentials" pattern; `alerts._toast`.
   EVIDENCE: core/compliance/owner.py:400; core/compliance/gate.py:569, 586; data/crypto/crypto_client.py:308-319; core/engine/state.py:141-142; core/engine/orders.py:140-152; data/krx/kis_client.py:62-76
   IMPACT: An account-inquiry first step can be Upbit-only with no guard retirement. KIS inquiry cannot.
* [retire narrowly] For KIS account inquiry: T-RO-01 FORBIDDEN_TEXT_CS (CANO, ACNT_PRDT_CD) and FORBIDDEN_PATH_RE (`/trading/`), test_09, and the T-RO-02 tests that refuse `/trading/inquire-balance`. For orders, additionally: T-RO-01 FORBIDDEN_TEXT_CI order verbs and TR ids, FORBIDDEN_CALLS, MUTATING_HTTP on order URLs, test_08, the crypto-client raw test (if Upbit orders), the UI disclaimer text and its test, README P0. test_s4 only if the frozen engine files are touched.
   EVIDENCE: tests/macro_m0_harness.py:28-52; tests/acceptance.py:169-182; tests/macro_m1_pit.py:1054-1057; tests/macro_m1_integration.py:233; tests/expansion_acceptance.py:155; tests/macro_ui_components.py:16-17; README.md:399-401; tests/macro_m5_integration.py:55-58
   IMPACT: Each retirement should be an allowlist of named adapter files and named endpoints, with a positive control showing every other file is still scanned.

## Open questions

* Where do execution adapters live? Under core/ (scanned by T-RO-01/test_08/09 and the core-wide compliance guards, and a candidate acting-module prefix) or a new top-level package (unscanned today unless `runtime_py()` is widened)?
* Do the adapters join the D14 signed code closure (`owner.code_files` covers only core/compliance and core/odds)? If not, an agent can edit the order path without the owner signing.
* Should the armed check, the D3 floor halt and the daily-loss limit be enforced inside `decide()` (a signed gate change) or only in execution? Today the gate reads none of them.
* Does "halts for good" (D3) mean no `session_armed` counts after any `system_halt`, or only that the floor cannot loosen (what owner.py encodes now)?
* Is `system_halt {floor_krw}` enough for the kill switch and the daily-loss stop, or does execution need a new system kind (for example a daily stop with a Seoul date)? A new kind changes owner.py, the signer and the code hash.
* Where do trading-scope keys live? `.env` is outside the code hash and today is QUANTGEN's shared copy (with KIS_ACCOUNT_8/KIS_ACCOUNT_PD set). Does the owner want separate TRADEGEN keys, and separate inquiry and trading keys per venue?
* Is the KIS app key in `.env` already trade-capable (the attestation is "unknown")? Does the owner want a mock-server (openapivts) phase first?
* OKX private API: key permissions, API passphrase, IP binding, withdrawal whitelist and rate limits are not researched anywhere in the repo. A source-checked note is needed before an OKX adapter is designed. Should the OKX adapter wait, given auto-off on 2026-12-03?
* How are immediate alerts (halt, disarm, refused send) delivered? Today push and email come only from the daily 09:00 KST Claude task; is the toast alone acceptable during an armed session?
* Daily-loss accounting: realised only, or marked to market? On which price source and which Seoul-date boundary for 24/7 crypto?
* Does the account-inquiry-only step start with Upbit (already built, no guard retirement, keys absent from `.env`) or KIS (needs three guard retirements)?
* Process note: while checking scope I listed the top-level names under the real `~/.tradegen` once (read only; it shows `kis_token.json`, so KIS tokens have been issued under TRADEGEN, probably by cockpit test_21). Nothing there was opened or changed.

# Part 4 of 6. Venue research: KIS, with its Verification section

# KIS (Korea Investment & Securities) Open API: account inquiry (E1) research

Researched 2026-10-24. Documentation only. No key was used, no account or trading endpoint was called, and nothing was submitted. The only things fetched were public documentation: the portal's API-guide JSON, public forum posts, the error-code page, and files on the official GitHub.

## Source legend and versions

- **[OFF-PORTAL]**: the official KIS Developers API guide. The human page is `https://apiportal.koreainvestment.com/apiservice-apiservice?<path>`. The portal's own page script loads the same data as JSON from `https://apiportal.koreainvestment.com/api/apis/public/detail?accessUrl=<path>` (per API) and `.../api/apis/public/api-list/<collectionId>` (per category). "doc mod" is the `lastModifiedDate` the portal returns for that API entry.
- **[OFF-NOTICE] / [OFF-FAQ]**: official portal posts. Notice board: `https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000001/post/<id>`. FAQ board: `https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/<id>`. The post date is given with each one.
- **[OFF-ERR]**: the official error-code page `https://apiportal.koreainvestment.com/faq-error-code` (content lastModified 2025-04-25).
- **[OFF-GH]**: the official GitHub `https://github.com/koreainvestment/open-trading-api`, main branch at commit cd63caee6a (2026-10-23). `examples_user/kis_auth.py` last changed 2026-03-09. `examples_user/domestic_stock/domestic_stock_functions.py` last changed 2025-08-21.
- **[3P]**: a third party (not official).

Sections are numbered in the order the task listed them. Endpoints in section 5 are sorted by KIS's official API number.

---

## 0. Short answers to the key questions

| Question | Answer | Basis |
|---|---|---|
| Can an app key be inquiry-only? | **No such option is documented.** One token calls every API, including orders. Individuals have no scope parameter. The only inquiry-only case is an account *type*: IRP (29). | FAQ 58eeac3f, FAQ 0b29069f, tokenP doc |
| How is a key tied to an account? | Keys are issued per 8-digit 종합계좌번호. Every product account under that number (01, 03, 08, 22, 29) uses the same key. Each request carries CANO (8) + ACNT_PRDT_CD (2). Keys are bound to the HTS ID and the account password. | FAQ 34b89bae, FAQ 2b6c34cb, Notice bff7ecdb, FAQ f7f6c853 |
| Access token | `POST /oauth2/tokenP`. Valid 24 h. Calling again within 6 h returns the same token; after 6 h a new token is issued. Issuing is limited to 1 call per minute (EGW00133). Each issuance sends a KakaoTalk alert. Whether a new token revokes the old one is **not documented**. Explicit revoke is `POST /oauth2/revokeP`. | tokenP doc, Notices b9136772 and 7e0da1f9 |
| Two programs on one key | They share one per-key REST budget and one WebSocket session (a second session fails with OPSP8996). Within the 6 h window both receive the same token. If both try to issue, they hit the 1/min limit together. What happens to program A's token when B triggers a fresh issue after 6 h is **not documented**. | Notice d0d1a83f, OFF-ERR, [3P] AlgoLab |
| Real-account rate limit | **18 REST calls/s per account (app key)** as of 2026-04-20 (was 20). New registrations get 3/s for their first 3 days. Stock balance (TTTC8434R) also has a 120 TPS cap across all customers (EGW00215). | Notices d0d1a83f and c1113824, inquire-balance doc |
| Do inquiry endpoints live under `/trading/`? | **Yes, all of them.** Domestic and overseas balance, fills, open orders, buying power, asset summary, margin, and pension all sit under `/uapi/domestic-stock/v1/trading/...` or `/uapi/overseas-stock/v1/trading/...`, the same prefix as `order-cash` and `order`. A guard that bans the `/uapi/.../trading/` string bans all of E1. Only product info (`/quotations/`) and WebSocket fill notices are outside it. | OFF-PORTAL lists, OFF-GH |
| Is there a product-eligibility API? | **No account-level eligibility API is documented** for leveraged/inverse ETP pre-education or 기본예탁금, short selling, derivatives account, or ELW. What exists: order-time rejections (APBK1681: overseas leveraged-ETP 기본예탁금; APBK1943: best-execution disclosure) and product-level flags (`sgle_item_lvrg_etp_yn`, `etp_chas_erng_rt_dbnb`, `etf_chas_erng_rt_dbnb`). | Notices 15abe578 and 0778faf1, product-info docs |
| Mock environment | Yes. Separate domain, app key and mock account. TR ids start with V. **Many account inquiries are "모의투자 미지원"** (not supported in mock). | OFF-PORTAL, FAQ 5c706351 |
| WebSocket fill notices | H0STCNI0 (domestic) and H0GSCNI0 (overseas); mock versions H0STCNI9 / H0GSCNI9. Keyed by **HTS ID**, so notices cover every account under that ID. AES256-encrypted. The client only subscribes and unsubscribes. | OFF-PORTAL, Notice d0d1a83f |
| Deposit/withdrawal address lists | Not applicable: this is a broker, not a crypto venue. No transfer or withdrawal API appears in the documented account lists. | OFF-PORTAL lists |

---

## 1. Authentication and key scopes

1. **One token unlocks everything.** "해당 토큰을 활용하여 조회 및 매수/매도 등 모든 API를 호출할 수 있습니다." [OFF-FAQ 58eeac3f, 2026-04-07] `.../000000000002/post/58eeac3f-f5b5-4f22-a48d-ffd668fac8b4`
2. **Individuals have no scope parameter.** The tokenP request body is only `grant_type`, `appkey` and `appsecret`; grant_type is "client_credentials". [OFF-PORTAL tokenP, doc mod 2025-04-28] `https://apiportal.koreainvestment.com/apiservice-apiservice?/oauth2/tokenP`. The error list does include EGW00109 "scope는 필수입니다." and EGW00110 "유효하지 않은 scope 입니다." [OFF-ERR], but the same doc says partner corporations use the "Authorization Code Grant 절차를 준용" (a different flow). **Whether scopes apply to individual keys is not documented.**
3. **Inquiry-only exists only as an account type.** "IRP(29): 주문은 불가하며, 계좌조회/시세조회만 이용 가능합니다." DC accounts (55) cannot use Open API at all. [OFF-FAQ 0b29069f, 2026-03-26] `.../000000000002/post/0b29069f-812b-4a70-94db-63d07d5ad54c`
4. **Key-to-account binding.** "종합계좌번호(8자리) 단위로 Open API 서비스 신청 및 앱 발급이 되므로". Product accounts under the same 8 digits, such as -01 and -22, use the same key. [OFF-FAQ 34b89bae, 2025-08-11] `.../000000000002/post/34b89bae-7d22-45b4-a8cc-2781fbbcd7aa`
   - CANO and ACNT_PRDT_CD: "CANO에 종합계좌번호 8자리, ACNT_PRDT_CD에 계좌상품코드 2자리". The product code is 01 for stocks (domestic and overseas), 03 for domestic futures/options, 08 for overseas futures/options. [OFF-FAQ 2b6c34cb, 2023-05-10] `.../000000000002/post/2b6c34cb-8067-4efa-a0f2-043644c922ab`
   - The official config file also lists 22 (pension savings) and 29 (retirement pension): `my_prod: "01" # 종합계좌`. [OFF-GH kis_devlp.yaml] `https://github.com/koreainvestment/open-trading-api/blob/main/kis_devlp.yaml`
   - Limits: "실전투자계좌의 경우 최대 89개, 모의투자계좌의 경우 최대 2개까지". [OFF-NOTICE 0d5bc017, 2022-10-27] `.../000000000001/post/0d5bc017-eb8b-431a-98da-a2854f17f110`
   - Only your own accounts: "현재 본인계좌 이외에는 매매가 불가능합니다." [OFF-FAQ 4cd60e0e, 2022-08-05]
5. **Key lifetime.** "유효기간은 1년이며 만료 30일 전부터 앱키를 갱신하실 수 있습니다." and "갱신시 APP Key, APP Secret는 새로 발급됩니다." [OFF-NOTICE 0d5bc017]. A renewal first sends a "해지" (cancelled) notice, then a new-registration notice. [OFF-FAQ 544bdacd, 2025-08-11]
6. **Events that invalidate the key.**
   - Changing the account password: "계좌비밀번호를 변경하신 경우는 기존 앱키, 앱시크리트 사용이 불가합니다." [OFF-FAQ f7f6c853, 2023-08-04]
   - Changing the HTS ID: "기존에 발급받은 API Key는 더 이상 사용하실 수 없으며". From 2026-08-17 this is enforced on overseas balance (TTTS3012R) and overseas open orders (TTTS3018R). [OFF-NOTICE bff7ecdb, 2026-08-03] `.../000000000001/post/bff7ecdb-f13c-40d3-a5e6-403a5a9e0a6b`
   - Manual cancellation at any time: "해지 완료 시 발급되었던 APP Key, APP Secret는 사용이 불가능합니다." [OFF-FAQ 6a66821c, 2023-09-06]
7. **The secret goes on every call.** Every REST request header carries `authorization` (Bearer), `appkey` **and** `appsecret`, plus `tr_id` and `custtype` ("P : 개인"). So any process that reads the account must hold the app secret. The doc's own note on the secret field: "(절대 노출되지 않도록 주의해주세요.)" [OFF-PORTAL inquire-balance, doc mod 2026-07-06] `https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/trading/inquire-balance`
8. **HTS ID.** It is needed for WebSocket fill notices (`my_htsid`) [OFF-GH README]. The pension docs state API keys are issued only when "HTS ID에 반드시 연결되어있어야만". [OFF-GH domestic_stock_functions.py, pension section]
9. **Terms of use.** "자신의 보안코드(앱키, 시크릿키)가 유출 및 도용되지 않도록 관리해야". Market data may be used for personal investment only. [OFF-FAQ 1f422ddb, 2026-10-06]

## 2. Token and signature rules and lifetimes

1. **Endpoint.** `POST /oauth2/tokenP` with body `{"grant_type":"client_credentials","appkey":...,"appsecret":...}`. The response carries `access_token`, `token_type` "Bearer", `expires_in` (the example shows 86400) and `access_token_token_expired` ("YYYY-MM-DD HH:MM:SS"). [OFF-PORTAL tokenP, doc mod 2025-04-28]
2. **Lifetime and reissue.** "접근토큰(access_token)의 유효기간은 24시간 이며(1일 1회발급 원칙)" and "갱신발급주기는 6시간 입니다.(6시간 이내는 기존 발급키로 응답)" [OFF-PORTAL tokenP]
   - After 6 h: "6시간 이후에 발급 요청시 토큰값 신규생성 및 결과 값 리턴". [OFF-NOTICE 7e0da1f9, 2023-07-10] `.../000000000001/post/7e0da1f9-9540-4530-8ca9-cb1da1cc68ed`
3. **Issue-rate limit (EGW00133).** "1분당 1회 호출가능, 2회 이상 호출시 오류 리턴", effective 2023-10-27 17:00, `msg_cd: EGW00133`. [OFF-NOTICE b9136772, 2023-10-17 "[수정]"] `.../000000000001/post/b9136772-4f5b-4e72-92c5-bf9429b392fd`
   - Confirmed by [OFF-FAQ a046c19e, 2025-08-11]: "1분 내 2회 이상 호출 시 오류가 반환됩니다." and by the [OFF-GH README]: "토큰 재발급 - 1분당 1회 발급됩니다."
   - **Older or conflicting official statements:**
     - FAQ 0ad7f35e (2023-07-18) says "5분당 1회 (2023.10.27일부터 적용)". This predates the "[수정]" (revised) notice, which says the limit was changed to 1 minute after customer feedback.
     - The rate-limit notice d0d1a83f says "접근토큰발급(/oauth2/tokenP)의 경우 1초당 1건".
     - Treat 1/min as binding, because it is the strictest current statement and matches the EGW00133 message text.
4. **Alert on issuance.** "접근토큰발급 사실을 카톡 등을 통하여 안내드리고 있사오니" (b9136772). The official sample says "Token 발급, 유효기간 1일, 6시간 이내 발급시 기존 token값 유지, 발급시 알림톡 무조건 발송". [OFF-GH examples_user/kis_auth.py, line 192] `https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/kis_auth.py`
5. **Does a new token revoke the old one? Not documented.** The docs only say the same token is returned within 6 h. Whether a token issued after the 6 h mark invalidates an earlier token that still has hours left is not stated anywhere official. [3P AlgoLab, 2026-08-09, `https://algolab.co.kr/blog/kis-api-access-token-expiry-refresh-2026`] does not say either; it recommends a single shared token file because "각자 발급을 시도하면 분당 제한에 함께 걸립니다".
6. **Explicit revoke.** `POST /oauth2/revokeP` with body `appkey`, `appsecret`, `token`. Purpose: "부여받은 접큰토큰을 더 이상 활용하지 않을 때 사용합니다." [OFF-PORTAL revokeP, doc mod 2022-04-24]
7. **WebSocket approval key.** `POST /oauth2/Approval` with body `grant_type`, `appkey`, `secretkey`. The doc notes "appsecret와 secretkey는 동일하오니". The key is used once at connect: "접속키는 세션 연결 시 초기 1회만 사용하기 때문에", and the session can then stay up indefinitely. Issuance is limited to 1/s. [OFF-PORTAL Approval, doc mod 2023-06-27; OFF-NOTICE d0d1a83f]
8. **Signature.** Requests are not HMAC-signed; auth is bearer token plus appkey/appsecret headers.
   - The legacy sample had a `/uapi/hashkey` call for POST bodies, but in the current sample the call is commented out: `# if (hashFlag): set_order_hash_key(headers, params)` [OFF-GH kis_auth.py].
   - `/uapi/hashkey` has no entry in the current portal (the portal JSON returned nothing for it). The error list keeps EGW00131 "유효하지 않은 hashkey입니다."
   - Hashkey is for order POSTs only, so it does not matter for E1.
9. **Transport.** TLS 1.2 or higher is mandatory since 2025-12-12: "TLS 1.0, 1.1로 호출 시 서비스 이용이 불가". [OFF-NOTICE 1510666f, 2025-11-25]. The WebSocket is plain `ws://`: "ws 프로토콜만 제공하며, wss(SSL 암호화) 접속은 지원하지 않습니다." [OFF-FAQ efa49825, 2025-08-11]

## 3. IP binding

1. **None for individuals.** "별도의 IP 화이트리스트 운영 없이 전체 허용 정책입니다." [OFF-FAQ 691e2917, 2025-08-11] `.../000000000002/post/691e2917-3eb9-486b-b94c-9630a5c186c6`
2. **No fixed IP needed.** "접속 IP와 무관하게 인증이 이루어지기 때문에 고정 IP가 필요하지 않습니다." [OFF-FAQ c5c4f097, 2025-07-28]. KIS will not whitelist a specific IP on request either. [OFF-FAQ ff32a7fd, 2025-08-11]
3. **Corporate only.** The `ip_addr` header is "[법인 필수] 사용자(회원)의 IP Address" [OFF-PORTAL, every account API], and EGW00303 reads "법인고객에게 허용되지 않은 IP접근입니다." [OFF-ERR]
4. **Abuse blocking.** Clients that reconnect the WebSocket in a loop may be blocked: "고객님의 IP 및 앱키가 일시 차단 될 수". [OFF-NOTICE 4f34b068, 2026-02-24]

## 4. Rate limits

1. **REST (current).** "(실전투자) 1초당 18건 (기존 20건)", "(모의투자) 1초당 1건 (기존 2건)". Limits apply per account: "계좌 단위로 유량 제한". [OFF-NOTICE d0d1a83f, title says "2026.04.20 기준"] `.../000000000001/post/d0d1a83f-6f8d-4437-9700-6d26702fd989`
   - Spacing advice: "동시 호출의 경우, 100ms ~ 150ms 텀을 두고".
   - When some calls fail under load-balancing, the advice is an immediate retry: "즉시 재호출 수행 부탁드립니다".
   - A per-account key is the same thing as a per-app-key limit: "1개의 앱키당" [OFF-FAQ bcfb94ee, 2022-11-13, older figures of 20/2].
2. **New registrations.** "신청 시점으로부터 3일 동안 초당 3건으로 제한". A cancel-and-re-register counts as new: "서비스 해지 후 등록 시에는 신규 등록으로 간주". This applies since 2026-04-03 17:00 and not to mock accounts. [OFF-NOTICE c1113824, 2026-03-20] `.../000000000001/post/c1113824-17c7-47a7-b7b8-8880506a847c`
3. **Stock-balance cap across all customers.** "개인 고객 유량 무관하게 초당 120 TPS로 제한되어 있습니다." It returns "EGW00215 원장에서 허용 가능한 초당 거래건수를 초과하였습니다." and the advice is to retry. [OFF-PORTAL inquire-balance, doc mod 2026-07-06; also OFF-NOTICE 050d6619, 2026-02-09]
4. **Token and approval key.** tokenP: 1/min (section 2.3). Approval key: "초당 1건으로 발급 제한". [OFF-NOTICE d0d1a83f]
5. **WebSocket.** "WEBSOCKET : 1세션" per app key. The subscription limit is "실시간 데이터 합산 41건까지 등록 가능", summed across all products. One PC may open sessions for several keys. [OFF-NOTICE d0d1a83f]
   - Over the limit: OPSP0008 "MAX SUBSCRIBE OVER" [OFF-ERR].
   - A second session on the same key: OPSP8996 "ALREADY IN USE appkey" [OFF-ERR].
   - "한 사용자가 2개의 소켓을 열 수 없습니다." [OFF-FAQ 434b97f1]
6. **Optional higher tier.** Accounts with at least KRW 7.5 bn of monthly Open API volume get 50/s REST and 201 WS subscriptions. Not relevant at this account size. [OFF-NOTICE eb3e2dcb, 2025-11-03]
7. **Stale figures elsewhere.**
   - The official sample still sleeps `_smartSleep = 0.05` (real) and `0.5` (mock), which matches the old 20/s and 2/s. [OFF-GH kis_auth.py lines 146 and 151]
   - The 2022 FAQ 8548106c says "1초당 10건". Superseded.
   - [3P AlgoLab `https://algolab.co.kr/platforms/kis`] quotes 20/s and 2/s. Stale against the official 18/1.
8. **Page sizes per call (official).**
   - Domestic balance: 50 per call (real), 20 (mock).
   - Daily fills: 100 (real), 15 (mock).
   - Cancellable orders: 50.
   - Overseas balance: 100 (real).
   - Overseas fills: 20 (real), 15 (mock).
   - Overseas open orders: 40.
   - Paging uses the `tr_cont` header (response "F or M : 다음 데이터 있음"; next request "N") plus the `CTX_AREA_FK100/NK100` keys (FK200/NK200 for overseas).

## 5. Read-only endpoints

**Headers common to every REST call** [OFF-PORTAL]: `content-type: application/json; charset=utf-8`, `authorization: Bearer <token>`, `appkey`, `appsecret`, `tr_id`, `custtype: P`, optional `tr_cont`. The response body has `rt_cd` ("0 : 성공  0 이외의 값 : 실패"), `msg_cd` and `msg1`. Every endpoint below is `GET` with query parameters. Real host: `https://openapi.koreainvestment.com:9443`. Mock host: `https://openapivts.koreainvestment.com:29443`.

### 5.1 Domestic stock (all under `/uapi/domestic-stock/v1/trading/`)

| Official id | Name | Path | Real TR | Mock TR | doc mod |
|---|---|---|---|---|---|
| v1_국내주식-004 | 주식정정취소가능주문조회 (open / cancellable orders) | `.../trading/inquire-psbl-rvsecncl` | TTTC0084R (old TTTC8036R) | 모의투자 미지원 | 2025-04-30 |
| v1_국내주식-005 | 주식일별주문체결조회 (orders & fills) | `.../trading/inquire-daily-ccld` | ≤3 mo TTTC0081R; >3 mo CTSC9215R | VTTC0081R / VTSC9215R | 2026-06-08 |
| v1_국내주식-006 | 주식잔고조회 (holdings + cash) | `.../trading/inquire-balance` | TTTC8434R | VTTC8434R | 2026-07-06 |
| v1_국내주식-007 | 매수가능조회 (buying power) | `.../trading/inquire-psbl-order` | TTTC8908R | VTTC8908R | 2025-04-30 |
| v1_국내주식-020 | 주식예약주문조회 (reserved orders) | `.../trading/order-resv-ccnl` | CTSC0004R | 미지원 | 2026-02-02 |
| v1_국내주식-032..036 | 퇴직연금 잔고/미체결/매수가능/예수금 (IRP) | `.../trading/pension/...` | TTTC2202R, TTTC2201R / TTTC2210R, TTTC0503R, TTTC0506R, TTTC2208R | 미지원 | 2025-04-30 to 2026-03-20 |
| v1_국내주식-041 | 주식잔고조회_실현손익 | `.../trading/inquire-balance-rlz-pl` | TTTC8494R | 미지원 | 2025-04-30 |
| v1_국내주식-042 | 신용매수가능조회 (credit buying power) | `.../trading/inquire-credit-psamount` | TTTC8909R | 미지원 | 2025-04-30 |
| v1_국내주식-048 | 투자계좌자산현황조회 (asset summary) | `.../trading/inquire-account-balance` | CTRP6548R | 미지원 | 2025-04-30 |
| v1_국내주식-052 | 기간별손익일별합산조회 | `.../trading/inquire-period-profit` | TTTC8708R | 미지원 | 2025-04-30 |
| v1_국내주식-060 | 기간별매매손익현황조회 | `.../trading/inquire-period-trade-profit` | TTTC8715R | 미지원 | 2025-04-30 |
| 국내주식-165 | 매도가능수량조회 (sellable qty) | `.../trading/inquire-psbl-sell` | TTTC8408R | 미지원 | 2025-04-30 |
| 국내주식-191 | 주식통합증거금 현황 (integrated margin) | `.../trading/intgr-margin` | TTTC0869R | 미지원 | 2025-04-30 |
| 국내주식-211 | 기간별계좌권리현황조회 (corporate-action rights) | `.../trading/period-rights` | CTRGA011R | 미지원 | 2025-04-30 |

Source for the whole table: the [OFF-PORTAL] list for category "[국내주식] 주문/계좌" (`.../api/apis/public/api-list/b0a44bfd-dfd5-47f1-9b06-758383e595db`), cross-checked against [OFF-GH] `examples_user/domestic_stock/domestic_stock_functions.py` (for example `api_url = "/uapi/domestic-stock/v1/trading/inquire-balance"`, line 3730).

**Details of the key endpoints:**

- **-006 inquire-balance (TTTC8434R).**
  - Required params: `CANO`, `ACNT_PRDT_CD`, `AFHR_FLPR_YN`, `INQR_DVSN`, `UNPR_DVSN`, `FUND_STTL_ICLD_YN`, `FNCG_AMT_AUTO_RDPT_YN`, `PRCS_DVSN`, plus `OFL_YN` (blank) and `CTX_AREA_FK100/NK100`.
  - Since 2026-09-14, AFHR_FLPR_YN means: N = KRX regular close, X = NXT, Y = KRX+NXT combined. [OFF-NOTICE 26dfe350, 2026-09-09]
  - `INQR_DVSN=02` is now rejected ("INPUT INVALID_CHECK_INQR_DVSN"), so use `01`. [OFF-NOTICE 050d6619, 2026-02-09]
  - output1 (per holding): `pdno`, `prdt_name`, `hldg_qty`, `ord_psbl_qty`, `pchs_avg_pric`, `pchs_amt`, `prpr`, `evlu_amt`, `evlu_pfls_amt`, `evlu_pfls_rt`, `thdt_buyqty`, `thdt_sll_qty`, `loan_dt`, `loan_amt`, `item_mgna_rt_name`.
  - output2 (cash): `dnca_tot_amt` (예수금총금액, "예수금"), `nxdy_excc_amt` ("D+1 예수금"), `prvs_rcdl_excc_amt` ("D+2 예수금"), `tot_evlu_amt` ("유가증권 평가금액 합계금액 + D+2 예수금"), `nass_amt`, `scts_evlu_amt`, `pchs_amt_smtl_amt`, `evlu_pfls_smtl_amt`, `tot_loan_amt`.
  - Caveats:
    - Holdings sold out today still appear at quantity 0 and disappear after D-2.
    - The doc warns it is "조회속도가 느린 API" and recommends the buying-power and sellable-quantity TRs before placing orders.
- **-007 inquire-psbl-order (TTTC8908R).**
  - Params: `CANO`, `ACNT_PRDT_CD`, `PDNO`, `ORD_UNPR`, `ORD_DVSN`, `CMA_EVLU_AMT_ICLD_YN`, `OVRS_ICLD_YN`. Per the doc, if PDNO and ORD_UNPR are blank, only the amount is returned (no quantity).
  - Output: `ord_psbl_cash` ("예수금으로 계산된 주문가능금액"), `ruse_psbl_amt`, `nrcvb_buy_amt`/`nrcvb_buy_qty` (no margin debt), `max_buy_amt`/`max_buy_qty` (with margin debt), `ord_psbl_frcr_amt_wcrc`.
  - Use `ORD_DVSN=01` so the stock's margin rate is applied.
- **-005 inquire-daily-ccld.**
  - Params: `CANO`, `ACNT_PRDT_CD`, `INQR_STRT_DT`, `INQR_END_DT`, `SLL_BUY_DVSN_CD`, `PDNO`, `ORD_GNO_BRNO`, `ODNO`, `CCLD_DVSN` (00 all / 01 filled / 02 unfilled), `INQR_DVSN`, `INQR_DVSN_1`, `INQR_DVSN_3`, `EXCG_ID_DVSN_CD` (KRX/NXT/SOR/ALL; "모의투자는 KRX만 제공"), `CTX_AREA_*`.
  - Old TR ids: "(구)TTTC8001R → (신)TTTC0081R" and CTSC9115R → CTSC9215R. The doc warns "구TR은 사전고지 없이 막힐 수 있으므로". Calls on old ids are still auto-mapped (Notice 7c894616), but do not use them.
  - output1: `ord_dt`, `odno`, `orgn_odno`, `sll_buy_dvsn_cd`, `pdno`, `ord_qty`, `ord_unpr`, `ord_tmd`, `tot_ccld_qty`, `avg_prvs`, `tot_ccld_amt`, `cncl_yn`, `rmn_qty`, `rjct_qty`, `excg_id_dvsn_Cd`.
  - Doc defect: the output2 labels are shifted (`tot_ccld_amt` is labelled 매입평균가격).
  - Sample gap: the official sample's params dict omits `EXCG_ID_DVSN_CD` (domestic_stock_functions.py lines ~4250-4265), although the portal marks it required.
- **-004 inquire-psbl-rvsecncl (TTTC0084R)** is the "open orders" view. Params: `INQR_DVSN_1` (0 by order / 1 by stock), `INQR_DVSN_2` (0 all / 1 sell / 2 buy), `CTX_AREA_*`. Output: `odno`, `orgn_odno`, `pdno`, `ord_qty`, `ord_unpr`, `tot_ccld_qty`, `psbl_qty`, `sll_buy_dvsn_cd`, `ord_dvsn_cd`, `excg_id_dvsn_cd`. Real accounts only.
- **-048 inquire-account-balance (CTRP6548R)**, the asset summary.
  - Params: `CANO`, `ACNT_PRDT_CD`, `INQR_DVSN_1` (blank), `BSPR_BF_DT_APLY_YN` (blank).
  - Output includes `tot_asst_amt`, `nass_tot_amt`, `tot_dncl_amt` (총예수금액), `dncl_amt` (예수금액), `frcr_evlu_tota`, `ovrs_stck_evlu_amt1`, `thdt_rcvb_amt` (당일미수금액), `crdt_fncg_amt`. (Field names are from [OFF-GH] `examples_llm/domestic_stock/inquire_account_balance/chk_inquire_account_balance.py`.)
- **국내주식-191 intgr-margin (TTTC0869R).** Params: `CMA_EVLU_AMT_ICLD_YN`=N, `WCRC_FRCR_DVSN_CD`, `FWEX_CTRT_FRCR_DVSN_CD`. Output includes `acmga_rt` (계좌증거금율), `acmga_pct100_aptm_rson` (reason the account is set to 100% margin), `stck_cash_ord_psbl_amt`, `rcvb_amt` (미수금액). This is the closest thing to an "account trading-terms" answer (margin rate and 100%-margin flag).
- **Ledger lag.** "체결통보 수신 ≠ 당사 원장 반영 완료". Before acting, re-confirm with the buying-power (-007) and sellable-quantity (-165) inquiries. [OFF-NOTICE 227ac529, 2025-05-20]

### 5.2 Overseas stock (all under `/uapi/overseas-stock/v1/trading/`)

| Official id | Name | Path | Real TR | Mock TR | doc mod |
|---|---|---|---|---|---|
| v1_해외주식-005 | 미체결내역 (open orders) | `.../trading/inquire-nccs` | TTTS3018R | 미지원 | 2025-04-30 |
| v1_해외주식-006 | 해외주식 잔고 (holdings) | `.../trading/inquire-balance` | TTTS3012R | VTTS3012R | 2025-04-30 |
| v1_해외주식-007 | 주문체결내역 (orders & fills) | `.../trading/inquire-ccnl` | TTTS3035R | VTTS3035R | 2026-06-11 |
| v1_해외주식-008 | 체결기준현재잔고 (holdings + cash by currency) | `.../trading/inquire-present-balance` | CTRP6504R | VTRP6504R | 2025-04-30 |
| v1_해외주식-013 | 예약주문조회 | `.../trading/order-resv-list` | TTTT3039R (US) / TTTS3014R (Asia) | 미지원 | 2025-05-23 |
| v1_해외주식-014 | 매수가능금액조회 (buying power) | `.../trading/inquire-psamount` | TTTS3007R | VTTS3007R | 2025-04-30 |
| v1_해외주식-032 | 기간손익 | `.../trading/inquire-period-profit` | TTTS3039R | 미지원 | 2025-04-30 |
| 해외주식-035 | 해외증거금 통화별조회 (margin by currency) | `.../trading/foreign-margin` | TTTC2101R | 미지원 | 2025-04-30 |
| 해외주식-063 | 일별거래내역 | `.../trading/inquire-period-trans` | CTOS4001R | 미지원 | 2025-04-30 |
| 해외주식-064 | 결제기준잔고 | `.../trading/inquire-paymt-stdr-balance` | CTRP6010R | 미지원 | 2025-04-30 |
| 해외주식-070 / 071 | TWAP/VWAP fills / order numbers | `.../trading/inquire-algo-ccnl`, `.../trading/algo-ordno` | TTTS6059R / TTTS6058R | 미지원 | 2025-05-23 |

Source: the [OFF-PORTAL] list for "[해외주식] 주문/계좌" (`.../api-list/fae9f1bb-0de9-4523-ab91-6c534e212700`) and [OFF-GH] `examples_user/overseas_stock/overseas_stock_functions.py`.

- **Common precondition.** "해외주식 서비스 신청 후 이용 가능합니다." This appears on the balance, fills, open-orders and buying-power docs.
- **-006 inquire-balance (TTTS3012R).**
  - Params: `CANO`, `ACNT_PRDT_CD`, `OVRS_EXCG_CD` (real: NASD = all US; also NAS/NYSE/AMEX/SEHK/SHAA/SZAA/TKSE/HASE/VNSE), `TR_CRCY_CD` (USD/HKD/CNY/JPY/VND), `CTX_AREA_FK200/NK200`.
  - Output: `ovrs_pdno`, `ovrs_cblc_qty`, `ord_psbl_qty`, `pchs_avg_pric`, `frcr_pchs_amt1`, `ovrs_stck_evlu_amt`, `now_pric2`, `frcr_evlu_pfls_amt`, `tr_crcy_cd`, `ovrs_excg_cd`, plus totals (`tot_evlu_pfls_amt`, `frcr_buy_amt_smtl1`).
  - Mini-stock holdings are not included ("미니스탁 잔고는 해당 API로 확인이 불가").
  - In the US daytime session, valuation follows night prices.
- **-008 inquire-present-balance (CTRP6504R).**
  - Params: `WCRC_FRCR_DVSN_CD` (01 KRW / 02 foreign), `NATN_CD` (000 all, 840 US, ...), `TR_MKET_CD`, `INQR_DVSN_CD`.
  - output2 (per currency): `frcr_dncl_amt_2` (외화예수금액2), `frcr_drwg_psbl_amt_1` ("출금가능한 외화금액"), `frst_bltn_exrt`.
  - output3: `tot_asst_amt`, `tot_dncl_amt`, `wdrw_psbl_tot_amt`, `frcr_use_psbl_amt`, `frcr_evlu_tota`.
  - In mock only output3 is valid.
  - It is not real-time at night: "야간에 실시간 잔고 반영이 안 됩니다". [OFF-FAQ 1f4b60d6, 2022-08-10]. That FAQ also mentions a day/night ledger API (`dayornight`, JTTT3012R) that **does not appear in the current portal list**, so treat it as possibly stale.
  - US trades after about 18:10 are not reflected in real time.
- **-007 inquire-ccnl (TTTS3035R).**
  - Params: `PDNO` ("%" = all), `ORD_STRT_DT`/`ORD_END_DT` (local date), `SLL_BUY_DVSN`, `CCLD_NCCS_DVSN`, `OVRS_EXCG_CD`, `SORT_SQN`, `ORD_DT`/`ORD_GNO_BRNO`/`ODNO` (blank; "주문번호로 검색 불가능합니다").
  - Output: `odno`, `orgn_odno`, `pdno`, `ft_ord_qty`, `ft_ord_unpr3`, `ft_ccld_qty`, `ft_ccld_unpr3`, `ft_ccld_amt3`, `nccs_qty`, `prcs_stat_name`, `rjct_rson`, `tr_crcy_cd`.
  - Fractional-share trades are not shown.
- **-005 inquire-nccs (TTTS3018R).** Params: `OVRS_EXCG_CD` (required for paging; NASD = all US), `SORT_SQN`, `CTX_AREA_*`. In mock, use -007's `nccs_qty` instead.
- **-014 inquire-psamount (TTTS3007R).** Params: `OVRS_EXCG_CD`, `OVRS_ORD_UNPR`, `ITEM_CD`. Output: `ord_psbl_frcr_amt`, `ovrs_ord_psbl_amt`, `max_ord_psbl_qty`, `echm_af_ord_psbl_amt`, `exrt`.
- **-035 foreign-margin (TTTC2101R).** Params: `CANO`, `ACNT_PRDT_CD`. Output: `natn_name`, `frcr_dncl_amt1`, `ustl_buy_amt`, `ustl_sll_amt`, `frcr_rcvb_amt`, `frcr_ord_psbl_amt1`, `itgr_ord_psbl_amt`, `bass_exrt`.

### 5.3 Product information (eligibility-adjacent, outside `/trading/`)

| Name | Path | TR | What it answers | doc mod |
|---|---|---|---|---|
| 상품기본조회 v1_국내주식-029 | `/uapi/domestic-stock/v1/quotations/search-info` | CTPF1604R | `prdt_risk_grad_cd` (product risk grade), `ivst_prdt_type_cd` | 2025-05-14 |
| 주식기본조회 v1_국내주식-067 | `/uapi/domestic-stock/v1/quotations/search-stock-info` | CTPF1002R | `scty_grp_id_cd` (EF ETF / EN ETN / EW ELW), `etf_chas_erng_rt_dbnb` (ETF tracking multiple), `etf_etn_ivst_heed_item_yn`, `tr_stop_yn`, `admn_item_yn`, `cptt_trad_tr_psbl_yn` (NXT tradable) | 2025-05-14 |
| 해외주식 상품기본정보 v1_해외주식-034 | `/uapi/overseas-price/v1/quotations/search-info` | CTPF1702R | `sgle_item_lvrg_etp_yn` (single-stock leveraged ETP), `etp_chas_erng_rt_dbnb` (ETP multiple), `ovrs_stck_etf_risk_drtp_cd`, ETP underlying class codes | 2026-08-11 |
| 당사 신용가능종목 국내주식-111 | `/uapi/domestic-stock/v1/quotations/credit-by-company` | FHPST04770000 | which stocks the broker allows on credit (product level) | 2026-04-10 |
| 당사 대주가능 종목 국내주식-195 | `/uapi/domestic-stock/v1/quotations/lendable-by-company` | CTSC2702R | which stocks can be borrowed (대주) (product level) | 2026-04-10 |

Notes on these:
- Overseas product info is blocked from 08:59 to 09:31 KST with "[EGW00317] 09:00 ~ 09:30 시간 동안에는 조회하실 수 없습니다." [OFF-NOTICE 365bc02b, 2026-07-24]
- The ETP class fields were added 2026-08-14. [OFF-NOTICE bb8d1be5]
- All of these are **product** attributes. None of them says whether **this account** may trade the product.

### 5.4 Eligibility: what is and is not documented

- **Overseas leveraged ETP 기본예탁금 and single-stock leveraged ETP 심화 사전교육**, effective 2026-05-22.
  - The target is the order API only: "대상 API : [해외주식] 주문/계좌 > 해외주식 주문".
  - A failing account gets `rt_cd "7"`, `msg_cd "APBK1681"`, "해당종목은 기본예탁금 충족한 계좌만 매수주문가능합니다".
  - Source: [OFF-NOTICE 15abe578, 2026-05-20] `.../000000000001/post/15abe578-7871-4f6d-80e7-ee1e40ffc0f3`
  - **No inquiry API reports whether the account meets the requirement; it surfaces only as an order rejection.**
- **Best-execution disclosure (최선집행의무 설명서).** Without registration, domestic stock orders fail with `APBK1943` "최선집행기준 설명서 미교부 고객은 주문이 불가합니다." [OFF-NOTICE 0778faf1, 2025-02-13]. No inquiry API exposes this status.
- **Domestic leveraged/inverse ETP pre-education and 기본예탁금** (the domestic rule): **not documented** anywhere in the KIS API docs, notices or FAQ that were checked. No rejection code is documented for it either.
- **Short selling eligibility: not documented.** Only the product-level lendable list (CTSC2702R) exists.
- **Derivatives account.** It needs a product-03 account registered under the key [OFF-FAQ 0b29069f]. Futures/options inquiries exist (`/uapi/domestic-futureoption/v1/trading/inquire-balance` CTFO6118R, `/trading/inquire-deposit` CTRP6550R). No eligibility API.
- **ELW.** Ordered through the ordinary cash-order API: "PDNO(상품코드)에 ELW 종목코드를 입력" [OFF-FAQ 842f4450, 2025-07-28]. ELW pre-education and deposit status: **not documented**.
- **Overseas trading enabled (해외주식 서비스 신청).** The error text "해외투자가 불가능한 계좌입니다. 확인하세요." is the title of [OFF-FAQ 704eedbe]. Which endpoint returns it, and whether a read-only inquiry such as inquire-psamount returns it on an account that has not applied, is **not documented** (it would be an inference).
- **Margin / credit status.** Account-level signals from read-only calls:
  - `acmga_rt` and `acmga_pct100_aptm_rson` from intgr-margin (TTTC0869R).
  - Credit buying power from inquire-credit-psamount (TTTC8909R).
  - Their exact semantics are not documented beyond the field names.

### 5.5 WebSocket fill notices (receive-only)

- **Connection.** Real: `ws://ops.koreainvestment.com:21000`. Mock: `ws://ops.koreainvestment.com:31000`. [OFF-GH kis_devlp.yaml]. The header carries `approval_key`, `custtype`, `tr_type` (1 subscribe / 2 unsubscribe), `content-type`. The body carries `tr_id` and `tr_key`.
- **Domestic H0STCNI0 (mock H0STCNI9)** [OFF-PORTAL `/tryitout/H0STCNI0`, doc mod 2025-04-30]
  - `tr_key` = **HTS ID**.
  - Two message types: "14번째 값(CNTG_YN;체결여부)가 2이면 체결통보" (fill); value 1 = order/modify/cancel/reject acknowledgement.
  - The payload is encrypted: "체결 통보 응답 결과는 암호화되어 출력됩니다." It is decrypted with the AES256 key and IV returned at subscribe.
  - Fields: `CUST_ID`, `ACNT_NO`, `ODER_NO`, `OODER_NO`, `SELN_BYOV_CLS`, `RCTF_CLS`, `ODER_KIND`, `STCK_SHRN_ISCD`, `CNTG_QTY`, `CNTG_UNPR`, `STCK_CNTG_HOUR`, `RFUS_YN`, `CNTG_YN`, `ACPT_YN`, `ODER_QTY`, `ORD_EXG_GB`, `CRDT_CLS`, `ODER_PRC`.
  - The field set changed on 2025-03-04 (ATS): `CNTG_ISNM` removed; `ORD_COND_PRC`, `ORD_EXG_GB`, `POPUP_YN`, `FILLER` added. [OFF-FAQ 26ee44dd; OFF-NOTICE cad37f81]
- **Overseas H0GSCNI0 (mock H0GSCNI9)** [OFF-PORTAL `/tryitout/H0GSCNI0`, doc mod 2025-05-23]
  - Same structure, `tr_key` = HTSID.
  - `CNTG_UNPR12` was added 2025-12-20 [OFF-NOTICE 3c75de0f].
  - Notes from the doc: "특정 거래소의 체결시간 데이터는 수신되지 않습니다." Also, `CNTG_QTY` carries the order quantity on order acknowledgements.
- **Scope of notices.** "체결통보의 경우 HTS ID 단위로 등록하여, ID에 연결된 모든 계좌의 체결 통보 수신" [OFF-NOTICE d0d1a83f]. So one subscription delivers fills for **every account under that HTS ID**, not only the CANO configured in E1.
- **Final-fill detection.** There is no "fully filled" flag: "최종 체결 여부를 직접 알려주는 별도 정보가 제공되지 않습니다". Sum `CNTG_QTY`, or compare `ord_qty` with `tot_ccld_qty` from -005. [OFF-FAQ 4f86cd4d, 2025-08-11]
- **Keep-alive.** The server closes the session after 100 s with no data; answer PINGPONG with a pong. [OFF-FAQ 07f312e5, 2023-11-22]. Do not reconnect in tight loops: IP and key blocking (section 3.4).
- **Is it read-only?** The documented WebSocket TRs are all real-time data and notices, and the client only sends subscribe/unsubscribe frames. An explicit statement that orders cannot be sent over the socket is **not documented**.

### 5.6 Deposit/withdrawal address lists

Not applicable to a securities broker. Neither the "[국내주식] 주문/계좌" nor the "[해외주식] 주문/계좌" list contains any transfer, withdrawal or bank-account endpoint (checked against the portal JSON lists). The withdrawable amounts that are visible come from read-only fields: `frcr_drwg_psbl_amt_1` and `wdrw_psbl_tot_amt` (overseas -008), and `prvs_rcdl_excc_amt` (D+2, domestic -006).

## 6. What distinguishes read-only from trading at the protocol level

1. **HTTP method.** "접근토큰발급과 주문은 POST 방식, 그 외 조회는 GET 방식으로 호출해야". [OFF-FAQ 695cfecd, 2025-08-19] Every account inquiry in section 5 is GET; every order (`order-cash`, `order-credit`, `order-rvsecncl`, `order-resv*`, overseas `order*`, `daytime-order*`) is POST.
2. **TR id.** "API 호출 시 TR ID 첫 글자는 해당 서버(원장)를 지정합니다." (T stock, S night F&O, O overseas F&O, C other, V mock). [OFF-FAQ 587c7efd, 2025-08-11]
   - *Observation, not a documented rule:* in the official tables every inquiry TR ends in `R` and every order TR ends in `U` (TTTC0011U/0012U/0013U, TTTT1002U/1006U/1004U, CTSC0008U/0009U/0013U).
   - The routing is by TR: "TR 기준으로 원장에 호출을 하기 때문에 TR이 보다 정확한 구분값". [OFF-FAQ 5c706351, 2023-05-10]
3. **Path is not a separator.** Inquiries and orders share `/uapi/domestic-stock/v1/trading/` and `/uapi/overseas-stock/v1/trading/`. Examples: `.../trading/inquire-balance` versus `.../trading/order-cash`, and overseas `.../trading/inquire-balance` versus `.../trading/order`.
4. **Domain is not a separator either.** The FAQ warns that with a switched domain, calls may still go through by TR: "도메인을 변경해서 사용하시면 TR 기준으로 API 호출되어서 거래가 되는 경우가". [OFF-FAQ 5c706351]
5. **Credentials are identical.** The same token, appkey and appsecret serve both (section 1.1). There is no per-call secret, PIN or account password on orders. Hashkey is not required in the current sample (section 2.8).
6. **The official sample silently rewrites TR ids for mock.** It turns a leading T/J/C into V: `if ptr_id[0] in ("T", "J", "C"): ... tr_id = "V" + ptr_id[1:]`. [OFF-GH kis_auth.py, lines 422-424]

## 7. Sandbox / paper environment (모의투자)

- **Hosts.** REST `https://openapivts.koreainvestment.com:29443` (portal `virtualDomain`). WebSocket `ws://ops.koreainvestment.com:31000`. [OFF-PORTAL tokenP JSON; OFF-GH kis_devlp.yaml]
- **Separate credentials.** It needs its own mock app key and secret (`paper_app` / `paper_sec`) and a mock account number. "TR_ID: V로 시작, ex) VTTT1234U", "앱정보: 모의계좌번호, 모의계좌의 appkey, appsecret". [OFF-FAQ 5c706351]
  - Mock account numbers: "모의투자 계좌는 5로 시작할 경우 주식," (6 = futures/options). [OFF-NOTICE 747384fe, 2026-08-25]
  - Corporations cannot use mock (EGW00210).
- **Inquiry coverage in mock.** Supported: domestic -005 (VTTC0081R / VTSC9215R), -006 (VTTC8434R), -007 (VTTC8908R); overseas -006 (VTTS3012R), -007 (VTTS3035R), -008 (VTRP6504R, output3 only), -014 (VTTS3007R); WebSocket H0STCNI9 / H0GSCNI9. **Everything else in sections 5.1 and 5.2 is "모의투자 미지원"**: cancellable orders, asset summary, margin, sellable quantity, overseas open orders, foreign margin, and the rest.
- **Limits and behaviour.**
  - 1 REST call/s (Notice d0d1a83f).
  - Mock runs on a separate operator: "모의투자는 별도 운영사(연합인포맥스)에서 시스템을 관리". [OFF-NOTICE 9858397d, 2024-03-27]
  - KRX only, no NXT. [OFF-NOTICE dd2e7e20]
  - Fills happen only when the real market trades at that price. [OFF-FAQ ca2cc700]
  - An expired mock account fails with "40910000 모의투자 주문이 불가한 계좌입니다." [OFF-NOTICE 747384fe]
- **Other test tools.** The official GitHub includes a backtester and strategy builder, and KIS recommends mock before going live. [OFF-FAQ 6005110f, 2026-04-07]

## 8. Error codes for auth and rate limits

Source is [OFF-ERR] unless noted.

| Code | Text (official) | Meaning for E1 |
|---|---|---|
| EGW00103 / EGW00105 | 유효하지 않은 AppKey입니다. / 유효하지 않은 AppSecret입니다. | Bad, cancelled or renewed key |
| EGW00121 | 유효하지 않은 token 입니다. | Token invalid; reissue, respecting 1/min |
| EGW00122 | token을 찾을 수 없습니다. | Token unknown |
| EGW00123 | 기간이 만료된 token 입니다. | Token expired (24 h) |
| EGW00133 | 접근토큰발급 잠시후 다시 시도하세요(1분당 1회) | tokenP called twice in one minute [OFF-NOTICE b9136772; not on the error page] |
| EGW00201 | 초당 거래건수를 초과하였습니다. | Per-key rate limit (18/s real, 1/s mock) |
| EGW00215 | 원장에서 허용 가능한 초당 거래건수를 초과하였습니다. | Cross-customer 120 TPS cap on TTTC8434R; retry [OFF-PORTAL inquire-balance] |
| EGW00205 | credentials_type이 유효하지 않습니다.(Bearer) | Missing "Bearer " prefix |
| EGW00206 | API 사용 권한이 없습니다. | Permission denied (when it triggers is not documented) |
| EGW00207 | IP 주소가 없거나 유효하지 않습니다. | Corporate IP header |
| EGW00213 | 모의투자 tr이 아닙니다. | Real TR sent to the mock host |
| EGW00304 | 고객식별키(법인 personalSeckey, 개인 appSecret)가 유효하지 않습니다. | Bad appsecret header |
| EGW00356 | 타겟 서버가 올바르지 않습니다 | Wrong TR first letter [OFF-FAQ 587c7efd] |
| EGW00317 | 09:00 ~ 09:30 시간 동안에는 조회하실 수 없습니다. | Overseas product-info time block [OFF-NOTICE 365bc02b] |
| EGW00301 / EGW00302 | 연결 시간이 초과되었습니다. / 거래시간이 초과되었습니다. (직전 거래를 반드시 확인하세요) | Timeouts |
| OPSP0002 / OPSP0008 / OPSP8996 / OPSP0011 | ALREADY IN SUBSCRIBE / MAX SUBSCRIBE OVER / ALREADY IN USE appkey / invalid approval(appkey) : NOT FOUND | WebSocket: duplicate subscription / over 41 / second session / bad approval key |
| (msg) | 처리계좌의 ID와 사용자정보가 상이하여 주문처리 불가능합니다. | HTS ID changed after key issue; enforced on TTTS3012R and TTTS3018R from 2026-08-17 [OFF-NOTICE bff7ecdb] |
| 90070000 / 40910000 | 모의투자 처리계좌의 ID와 사용자정보가 상이 / 모의투자 주문이 불가한 계좌 | Mock account mismatch / mock account expired [OFF-NOTICE 747384fe] |
| HTTP 403 | (FAQ) | Wrong host or wrong method (GET vs POST) [OFF-FAQ 695cfecd] |
| (msg) | 비밀번호 [5회] 오류입니다. | Account password changed after key issue; re-register [OFF-FAQ 765ed450] |

`rt_cd` is "0" on success. Order rejections use `rt_cd "7"` (APBK codes), but those are not part of E1.

## 9. Open questions (not documented; would need KIS VOC or a live test with the owner's approval)

1. **Inquiry-only key.** Is there any way to issue an app key or token that cannot place orders? The docs say the token calls "모든 API". The EGW00109/EGW00110 scope errors appear to belong to the partner Authorization-Code flow. This is the central risk for E1.
2. **Repo guard conflict.** Every E1 REST endpoint path contains `/uapi/domestic-stock/v1/trading/` or `/uapi/overseas-stock/v1/trading/`. A guard that bans that string blocks E1 entirely. The owner must decide how to tell inquiry from order (for example GET plus an allowlist of R-suffix TR ids). The path cannot be the discriminator.
3. **Revocation on reissue.** After the 6 h window, does a newly issued token invalidate an older one that is still within its 24 h? This matters if TRADEGEN and any other tool share a key.
4. **tokenP limit wording.** Official sources give 1/min (Notice 2023-10-17, FAQ 2025-08-11, README), 1/s (rate notice), and 5 min (FAQ 2023-07-18). Treat 1/min as binding; KIS has not reconciled these.
5. **What counts toward the 18/s.** Do tokenP, Approval and WebSocket traffic count toward the per-key REST limit? Not documented. Also not documented: whether the 3/s new-registration limit applies again after the yearly renewal (the notice says renewal goes straight to the base limit, but re-registration after cancellation counts as new).
6. **Eligibility.** There is no inquiry API for domestic leveraged/inverse ETP pre-education and 기본예탁금, overseas leveraged-ETP 기본예탁금 (APBK1681 appears only on orders), short selling, ELW, or derivatives-account status. The only read-only proxies are product-level flags plus the margin fields `acmga_rt` and `acmga_pct100_aptm_rson`. No rejection code is documented for the domestic leveraged-ETP rule.
7. **Overseas service not enabled.** On an account that has not applied, does a read-only inquiry (inquire-psamount, inquire-balance) fail with "해외투자가 불가능한 계좌입니다", which would make it a usable eligibility probe? Not documented.
8. **HTS-ID-wide fill notices.** H0STCNI0 and H0GSCNI0 deliver fills for every account under the HTS ID, so E1 must filter on `ACNT_NO`. The format of `ACNT_NO` in the notice (8 or 10 digits) is not documented.
9. **Missing required parameter in the sample.** inquire-daily-ccld: the official sample omits `EXCG_ID_DVSN_CD`, which the portal marks required. Which is correct is unverified.
10. **Overseas day/night ledger.** The 2022 FAQ references a `dayornight` API and the JTTT3012R TR, which are absent from the current portal list. Current behaviour of the overseas balance during the US daytime session is documented only as "valuation differs from HTS".
11. **KakaoTalk alert on token issuance.** Can E1 rely on it as an out-of-band intrusion signal (does it fire for the same-token return within 6 h)? Not documented.
12. **Mock coverage gap.** Most E1 endpoints are not supported in mock, so tests of -004, -048, -165, -191, overseas -005 and -035 can only use recorded fixtures, never a sandbox call.

---

## Verification (skeptic)

Checked 2026-10-24 by an independent pass. Documentation only: no key was used and no account or trading endpoint was called.

**Method.** I re-fetched every cited official source myself:
- the portal's per-API JSON (`https://apiportal.koreainvestment.com/api/apis/public/detail?accessUrl=<path>`);
- both account-category lists (`https://apiportal.koreainvestment.com/api/apis/public/api-list/b0a44bfd-dfd5-47f1-9b06-758383e595db` and `.../api-list/fae9f1bb-0de9-4523-ab91-6c534e212700`);
- all 119 notices and 173 FAQ posts, through the portal's own forum JSON (`https://apiportal.koreainvestment.com/api/forums/<forumId>/posts`);
- the error-code content JSON (`https://apiportal.koreainvestment.com/api/contents/kind?title=ERRORCODE&kind=CONTENTS`, lastModified 2025-04-25), which is what `https://apiportal.koreainvestment.com/faq-error-code` renders;
- the GitHub files at main `cd63caee6a` (2026-10-23).

Every cited post id resolved to an existing official post. Quotes below are verbatim from those fetches. [3P] claims were not re-checked; none is load-bearing.

**URL shorthand used below** (each expands to a full official URL):
- `N:<id>` = `https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000001/post/<id>` (notices)
- `F:<id>` = `https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/<id>` (FAQ)
- `P:<path>` = `https://apiportal.koreainvestment.com/apiservice-apiservice?<path>` (API guide)
- `ERR` = `https://apiportal.koreainvestment.com/faq-error-code`
- `GH:<file>` = `https://github.com/koreainvestment/open-trading-api/blob/main/<file>`

**Bottom line.** The note holds up. Four claims are **WRONG** (5.1 INQR_DVSN, 5.1 sample gap, 5.4 domestic ETP rule, 6.1 `order-resv*` wording) and two have **omissions** (2.7 approval-key expiry, 4.6 tier is time-limited). The central risk is unchanged and now confirmed: **no read-only key or scope exists for individuals**, so order blocking must be enforced on the client.

Claims are listed in the note's numerical order.

### 0. Short answers

- **0.1 Inquiry-only key.** CONFIRMED that none exists. F:58eeac3f-f5b5-4f22-a48d-ffd668fac8b4: "해당 토큰을 활용하여 조회 및 매수/매도 등 모든 API를 호출할 수 있습니다." Whether a read-only key would be refused for orders server-side is **UNVERIFIED and moot**: no such key type is documented. The only official order block is the IRP (29) account type (1.3), and no error code for an IRP order attempt is documented.
- **0.2 Key-to-account binding.** CONFIRMED (see 1.4 and 1.6).
- **0.3 Access token.** CONFIRMED (2.1 to 2.6). Revoke-on-reissue is UNVERIFIED (2.5).
- **0.4 Two programs on one key.** CONFIRMED (4.1, 4.5). What happens to program A's token is UNVERIFIED (2.5).
- **0.5 Real-account rate limit.** CONFIRMED (4.1 to 4.3).
- **0.6 Inquiries under `/trading/`.** CONFIRMED. All 41 entries in the two lists (30 GET, 11 POST) sit under `/trading/`. The names also mislead (see 6.1).
- **0.7 Eligibility API.** CONFIRMED that none is documented, with one correction (5.4: notice 15abe578 does mention the domestic single-stock leveraged/inverse ETP training).
- **0.8 Mock environment.** CONFIRMED (section 7).
- **0.9 WebSocket fill notices.** CONFIRMED (5.5).
- **0.10 No transfer API.** CONFIRMED. Neither list contains a transfer, withdrawal or bank-account endpoint.

### 1. Authentication and key scopes

- **1.1 One token for everything.** CONFIRMED (same quote as 0.1).
- **1.2 No scope parameter for individuals.** CONFIRMED. P:/oauth2/tokenP (doc mod 2025-04-28) has exactly three body properties: `grant_type`, `appkey`, `appsecret`. Individuals follow "OAuth 2.0의 Client Credentials Grant 절차를 준용"; partners follow "Authorization Code Grant 절차를 준용".
  - EGW00109 and EGW00110 are on ERR: CONFIRMED ("scope는 필수입니다.").
  - Whether scopes apply to individual keys: UNVERIFIED.
- **1.3 IRP is inquiry-only; DC cannot use the API.** CONFIRMED. F:0b29069f-812b-4a70-94db-63d07d5ad54c: "IRP(29): 주문은 불가하며, 계좌조회/시세조회만 이용 가능합니다." Also F:34b89bae-7d22-45b4-a8cc-2781fbbcd7aa: "IRP(29)계좌는 매매 기능이 제공되지 않고 조회 기능만 지원". The error code an IRP order would return is UNVERIFIED.
- **1.4 Key-to-account binding.**
  - Per 8-digit number: CONFIRMED. F:34b89bae-7d22-45b4-a8cc-2781fbbcd7aa: "종합계좌번호(8자리) 단위로 Open API 서비스 신청 및 앱 발급이 되므로".
  - CANO and ACNT_PRDT_CD: CONFIRMED. F:2b6c34cb-8067-4efa-a0f2-043644c922ab: "CANO에 종합계좌번호 8자리, ACNT_PRDT_CD에 계좌상품코드 2자리".
  - Codes 22 and 29: CONFIRMED. GH:kis_devlp.yaml: `# my_prod: "22" # 개인연금` and `# my_prod: "29" # 퇴직연금`.
  - Account limits: CONFIRMED. N:0d5bc017-eb8b-431a-98da-a2854f17f110: "실전투자계좌의 경우 최대 89개, 모의투자계좌의 경우 최대 2개까지".
  - Own accounts only: CONFIRMED. F:4cd60e0e-1c8a-4243-b0d6-23c55526de19: "현재 본인계좌 이외에는 매매가 불가능합니다."
- **1.5 Key lifetime.** CONFIRMED. N:0d5bc017-eb8b-431a-98da-a2854f17f110: "유효기간은 1년이며 만료 30일 전부터 앱키를 갱신하실 수 있습니다." and "갱신시 APP Key, APP Secret는 새로 발급됩니다." A renewal sends the cancellation notice first: F:544bdacd-16f1-47a1-9fa5-5a8f508981be, "갱신 시 ‘해지’ 알림이 먼저 발송되지만".
- **1.6 Events that invalidate the key.**
  - Password change: CONFIRMED. F:f7f6c853-fa53-4fed-84bd-f66e8b3c3929: "계좌비밀번호를 변경하신 경우는 기존 앱키, 앱시크리트 사용이 불가합니다."
  - HTS ID change: CONFIRMED. N:bff7ecdb-f13c-40d3-a5e6-403a5a9e0a6b: "기존에 발급받은 API Key는 더 이상 사용하실 수 없으며", effective 2026.08.17. Nit: the notice prints the TR ids as "TTS3012R / TTS3018R" (one T missing). The portal's real ids are TTTS3012R and TTTS3018R, so the note reads them correctly.
  - Manual cancellation: CONFIRMED. F:6a66821c-f902-466e-b9a1-76b80cd32985: "해지 완료 시 발급되었던 APP Key, APP Secret는 사용이 불가능합니다."
- **1.7 The secret goes on every call.** CONFIRMED. P:/uapi/domestic-stock/v1/trading/inquire-balance lists header `appsecret` as req=Y, with the note "(절대 노출되지 않도록 주의해주세요.)". Nit: `custtype` is req=N on inquire-balance but req=Y on order-cash, so send it always.
- **1.8 HTS ID.** CONFIRMED.
  - GH:README.md line 252: "체결통보, 나의 조건 목록 확인 등에 사용됩니다."
  - GH:examples_user/domestic_stock/domestic_stock_functions.py line 11347: "HTS ID에 반드시 연결되어있어야만 API 신청 및 앱정보 발급이 가능".
- **1.9 Terms of use.** CONFIRMED. F:1f422ddb-7a9c-4279-9ecb-21eb750a4b7a: "자신의 보안코드(앱키, 시크릿키)가 유출 및 도용되지 않도록 관리해야".

### 2. Token and signature rules and lifetimes

- **2.1 tokenP response.** CONFIRMED. The P:/oauth2/tokenP response example has `access_token_token_expired`, `token_type` "Bearer" and `expires_in` 86400. (The field's own description example, 7776000 s, is the 90-day partner value.)
- **2.2 Lifetime and reissue.** CONFIRMED.
  - P:/oauth2/tokenP: "갱신발급주기는 6시간 입니다.(6시간 이내는 기존 발급키로 응답)".
  - N:7e0da1f9-9540-4530-8ca9-cb1da1cc68ed: "6시간 이후에 발급 요청시 토큰값 신규생성 및 결과 값 리턴".
- **2.3 Issue-rate limit, EGW00133 at 1 per minute.** CONFIRMED.
  - N:b9136772-4f5b-4e72-92c5-bf9429b392fd: "1분당 1회 호출가능, 2회 이상 호출시 오류 리턴".
  - F:a046c19e-d638-4eda-bd1a-264934fdfd5e: "1분 내 2회 이상 호출 시 오류가 반환됩니다."
  - GH:README.md line 390: "토큰 재발급 - 1분당 1회 발급됩니다."
  - The conflicts are real:
    - F:0ad7f35e-8ada-4c37-ae11-c9ee293f3720 says "5분당 1회 (2023.10.27일부터 적용)".
    - N:d0d1a83f-6f8d-4437-9700-6d26702fd989 says "접근토큰발급(/oauth2/tokenP)의 경우 1초당 1건(23.10.27 시행)".
  - EGW00133 is absent from ERR: CONFIRMED.
- **2.4 KakaoTalk alert on issuance.** CONFIRMED.
  - N:b9136772-4f5b-4e72-92c5-bf9429b392fd: "접근토큰발급 사실을 카톡 등을 통하여 안내드리고".
  - GH:examples_user/kis_auth.py line 192: "발급시 알림톡 무조건 발송".
- **2.5 Does a new token revoke the old one?** UNVERIFIED. It is not stated in the tokenP doc, in N:7e0da1f9, or in the other tokenP FAQ, F:f2b74a2b-c63e-496a-81fc-fece1b38a825 (2023-06-07).
- **2.6 Explicit revoke.** CONFIRMED. P:/oauth2/revokeP (doc mod 2022-04-24) has body `appkey`, `appsecret` and `token`, all req=Y. Purpose: "부여받은 접큰토큰을 더 이상 활용하지 않을 때 사용합니다."
- **2.7 WebSocket approval key.** CONFIRMED. P:/oauth2/Approval (doc mod 2023-06-27) has body `grant_type`, `appkey`, `secretkey`, and says "접속키는 세션 연결 시 초기 1회만 사용하기 때문에".
  - **Omission:** the same doc says "접속키의 유효기간은 24시간이지만". The key itself expires after 24 h; only a session that is already open keeps running.
  - Issue limit of 1 per second: CONFIRMED. N:d0d1a83f: "접속키 발급의 경우, 초당 1건으로 발급 제한".
- **2.8 No HMAC signature; hashkey is optional.** CONFIRMED.
  - The portal JSON for `/uapi/hashkey` returns "API 정보가 존재하지 않습니다."
  - The inquire-balance and order-cash header lists contain no signature field.
  - GH:examples_user/kis_auth.py line 442: `# if (hashFlag): set_order_hash_key(headers, params)`. Line 270: "현재는 hash key 필수 사항아님".
  - A stronger source the note missed: N:21106822-e6da-4fb8-a718-7bb22159923b (2022-08-25), "hashkey값을 넣어도, 넣지 않아도 정상 호출됩니다."
  - EGW00131 is on ERR: CONFIRMED.
- **2.9 Transport.** CONFIRMED.
  - N:1510666f-5770-4de4-b0ff-2497ca98c616: "12.12(금) 이후부터는 TLS 1.0, 1.1로 호출 시 서비스 이용이 불가".
  - F:efa49825-6875-4f57-bf5f-c7094016d4fb: "wss(SSL 암호화) 접속은 지원하지 않습니다".

### 3. IP binding

- **3.1 None for individuals.** CONFIRMED. F:691e2917-3eb9-486b-b94c-9630a5c186c6: "별도의 IP 화이트리스트 운영 없이 전체 허용 정책입니다."
- **3.2 No fixed IP needed.** CONFIRMED.
  - F:c5c4f097-0f6d-46b9-aa0c-26e80519b9a8: "접속 IP와 무관하게 인증이 이루어지기 때문에 고정 IP가 필요하지 않습니다."
  - F:ff32a7fd-f6fc-4cb9-bfac-cb094eff4b62: "IP 허용 요청은 별도로 처리되지 않으며".
- **3.3 Corporate only.** CONFIRMED. The `ip_addr` header on P inquire-balance and order-cash reads "[법인 필수] 사용자(회원)의 IP Address". ERR lists EGW00303 "법인고객에게 허용되지 않은 IP접근입니다."
- **3.4 Abuse blocking.** CONFIRMED. N:4f34b068-3203-40fb-8936-c3bad5f154c0: "고객님의 IP 및 앱키가 일시 차단 될 수".
- **Consequence.** A leaked appkey plus appsecret works from any IP. Individuals have no IP-binding defence.

### 4. Rate limits

- **4.1 REST limits.** CONFIRMED. N:d0d1a83f-6f8d-4437-9700-6d26702fd989:
  - "(실전투자) 1초당 18건 (기존 20건)" and "(모의투자) 1초당 1건 (기존 2건)";
  - "1계좌당 1초당 18건";
  - spacing: "100ms ~ 150ms 텀을 두고";
  - retry: "즉시 재호출 수행 부탁드립니다".
  - Account, app key and 8-digit number are the same unit: CONFIRMED. N:eb3e2dcb-3d52-4ff1-9eb2-c09b1c880fb2: "계좌(appkey) 단위로 적용됩니다. (=종합계좌번호 8자리 단위)". F:bcfb94ee-5aa3-4915-bca6-d63378c620c2 gives the old figure, "1개의 앱키당 실전투자 1초당 20건". Nit: that FAQ is dated 2022-11-14 in KST; the note's 11-13 is the UTC date.
- **4.2 New registrations.** CONFIRMED. N:c1113824-17c7-47a7-b7b8-8880506a847c:
  - "신청 시점으로부터 3일 동안 초당 3건으로 제한";
  - "서비스 해지 후 등록 시에는 신규 등록으로 간주";
  - "모의투자 계좌는 해당되지 않습니다";
  - renewal: "갱신 시에는 기본 유량으로 자동 상향 처리".
- **4.3 Stock-balance cap across all customers.** CONFIRMED.
  - P inquire-balance: "개인 고객 유량 무관하게 초당 120 TPS로 제한".
  - N:050d6619-c967-46c2-840c-7e8f1c18ebc4: "초당 120 건으로 총량 제한".
- **4.4 Token and approval key limits.** CONFIRMED (see 2.3 and 2.7).
- **4.5 WebSocket.** CONFIRMED.
  - N:d0d1a83f: "실시간 데이터 합산 41건까지 등록 가능" and "1개의 PC에서 여러 개의 계좌(앱키)로 세션 연결 가능".
  - ERR: OPSP0008 "MAX SUBSCRIBE OVER" and OPSP8996 "ALREADY IN USE appkey".
  - F:434b97f1-c130-470e-b682-f184f00f1b50: "한 사용자가 2개의 소켓을 열 수 없습니다."
- **4.6 Optional higher tier.** **Omission**, current status UNVERIFIED. N:eb3e2dcb confirms 50/s REST and 201 WS subscriptions for accounts with at least KRW 7.5 bn of Open API volume, but only as a one-month programme: "12월 한 달간(12.1~12.31) 아래와 같이 유량을 확대 적용". That was December 2025, judged on volume from 11.3 to 11.27. No official source says whether it still runs in October 2026. It is irrelevant at KRW 42k.
- **4.7 Stale figures elsewhere.** CONFIRMED.
  - GH:examples_user/kis_auth.py line 146 `_smartSleep = 0.05` and line 151 `_smartSleep = 0.5`.
  - F:8548106c-c7a8-4126-abb7-b8ec46a8cb5c: "1초당 10건".
  - [3P] AlgoLab was not re-checked.
- **4.8 Page sizes.** CONFIRMED in each P doc:
  - inquire-balance: "최대 50건" (real) / "최대 20건" (mock);
  - inquire-daily-ccld: 100 / 15;
  - inquire-psbl-rvsecncl: 50;
  - overseas inquire-balance: 100;
  - inquire-ccnl: 20 / 15;
  - inquire-nccs: 40.
  - `tr_cont` "F or M : 다음 데이터 있음": CONFIRMED.

### 5. Read-only endpoints

- **5.0 Common headers, hosts, GET.** CONFIRMED.
  - Every inquiry in both lists has httpMethod GET.
  - The tokenP JSON gives realDomain `https://openapi.koreainvestment.com:9443` and virtualDomain `https://openapivts.koreainvestment.com:29443`.
  - `rt_cd`: "0 : 성공 / 0 이외의 값 : 실패".
- **5.1 Domestic table.** CONFIRMED. All 14 rows match the domestic list JSON on path, real TR, mock TR and doc mod.
  - -004 old TR, from its own doc: "(구)TTTC8036R → (신)TTTC0084R".
  - Pension -033: "TTTC2201R(기존 KRX만 가능), TTTC2210R (KRX,NXT/SOR)".
  - **-006 params:** CONFIRMED. AFHR_FLPR_YN N/X/Y is in the P doc, and N:26dfe350-eb72-48e5-8175-34eb27970f3e gives the date "2026년 9월 14일(월)".
  - **-006 INQR_DVSN=02: WRONG in detail.** N:050d6619 says 02 returns the error message but is then "01 (대출일별) 조회값으로 자동 분기 처리 됨". So 02 is auto-routed to 01, not hard-rejected. The advice to send 01 still stands. Nit: the notice is dated 2026-02-10 in KST.
  - **-006 caveats:** CONFIRMED. P inquire-balance: "최종 D-2일 이후에는 잔고에서 사라집니다." and "조회속도가 느린 API".
  - **-007:** CONFIRMED.
    - P inquire-psbl-order: "PDNO, ORD_UNPR 공란 입력 시, 매수수량 없이 매수금액만 조회됨".
    - ORD_DVSN advice: "반드시" ORD_DVSN:01(시장가)로 지정.
  - **-005:** CONFIRMED.
    - EXCG_ID_DVSN_CD is req=Y, with "※ 모의투자는 KRX만 제공".
    - Old-TR warning: "구TR은 사전고지 없이 막힐 수 있으므로".
    - Auto-mapping: N:7c894616-def7-425a-b62c-210e1a640f20, "기존-신규 TR 자동 매핑 지원".
    - output2 label shift: `tot_ccld_amt` is labelled 매입평균가격 and `pchs_avg_pric` is labelled 추정제비용합계.
  - **-005 sample gap: WRONG.** GH:examples_user/domestic_stock/domestic_stock_functions.py adds the field right after the dict, at lines 4269-4270: `if excg_id_dvsn_cd is not None: params["EXCG_ID_DVSN_CD"] = excg_id_dvsn_cd`. The docstring (line 4173) types it Optional. The sample omits it only when the caller passes None, so E1 must always pass it (the portal marks it req=Y).
  - **-004, -048, -191 fields:** CONFIRMED in the P docs: `psbl_qty`; `tot_asst_amt`, `dncl_amt`, `thdt_rcvb_amt`; `acmga_rt`, `acmga_pct100_aptm_rson`, `rcvb_amt`.
  - **Ledger lag:** CONFIRMED. N:227ac529-ad68-4007-9dd6-320f1d455a26: "체결통보 수신 ≠ 당사 원장 반영 완료".
- **5.2 Overseas table.** CONFIRMED. All 11 rows match the overseas list JSON. The -070 and -071 summaries do mention TWAP/VWAP.
  - Precondition, on the balance, nccs and psamount docs: "해외주식 서비스 신청 후 이용 가능합니다".
  - Mini-stock: "미니스탁 잔고는 해당 API로 확인이 불가".
  - -008 fields: `frcr_drwg_psbl_amt_1` ("출금가능한 외화금액") and `wdrw_psbl_tot_amt`.
  - F:1f4b60d6-017d-4b85-8ce3-d92efd8fc39a: "야간에 실시간 잔고 반영이 안 됩니다". It names JTTT3012R and `dayornight`, and neither is in the current list.
  - -007: "주문번호로 검색 불가능합니다".
- **5.3 Product information.** CONFIRMED. All 5 rows match on path, TR and doc mod; credit-by-company is FHPST04770000 and lendable-by-company is CTSC2702R, both 2026-04-10. The fields are present.
  - N:365bc02b-2b6e-4b3d-98b9-a9f1700a3e84: "거래제어시간 : 08:59 ~ 09:31".
  - N:bb8d1be5-ea48-4f0e-9b13-1b816b5342fd: "변경 시점 : 08.14 (금) 17:00~".
- **5.4 Eligibility.**
  - **APBK1681:** CONFIRMED. N:15abe578-7871-4f6d-80e7-ee1e40ffc0f3: "대상 API : [해외주식] 주문/계좌 > 해외주식 주문" and "해당종목은 기본예탁금 충족한 계좌만 매수주문가능합니다".
  - **APBK1943:** CONFIRMED. N:0778faf1-bf9c-4921-92ef-dc930b8d62af: "최선집행기준 설명서 미교부 고객은 주문이 불가합니다."
  - **Domestic leveraged/inverse ETP rule "not documented anywhere": WRONG in part.** N:15abe578 states that the 1-hour 심화 사전교육 also covers "국내/해외 단일종목 레버리지•인버스ETP" from 2026-05-22. Still undocumented:
    - any API that reports it;
    - any rejection code for a domestic order;
    - the older general domestic leveraged-ETP 사전교육 and 기본예탁금 rule.
  - **Short selling and ELW pre-education:** UNVERIFIED. No official source covers them. This matches my keyword sweep of all notices and FAQs, which found only 15abe578, 842f4450, and FAQ 13719c77 (the 신용/대주 product lists).
  - **Derivatives inquiries:** CONFIRMED in P: `/uapi/domestic-futureoption/v1/trading/inquire-balance` CTFO6118R (mock VTFO6118R) and `/trading/inquire-deposit` CTRP6550R.
  - **ELW orders:** CONFIRMED. F:842f4450-0ff9-4761-9b6a-42843f5611e5: "PDNO(상품코드)에 ELW 종목코드를 입력".
  - **Overseas service not enabled:** the title of F:704eedbe-ed92-4905-a725-d7359768536c is CONFIRMED. Which endpoint returns that error is UNVERIFIED.
  - **Margin field semantics:** UNVERIFIED.
- **5.5 WebSocket fill notices.** CONFIRMED.
  - GH:kis_devlp.yaml: `ops: "ws://ops.koreainvestment.com:21000"` and `vops: "ws://ops.koreainvestment.com:31000"`.
  - P:/tryitout/H0STCNI0 (doc mod 2025-04-30): "체결 통보 응답 결과는 암호화되어 출력됩니다", mock H0STCNI9.
  - P:/tryitout/H0GSCNI0 (doc mod 2025-05-23): mock H0GSCNI9, and "특정 거래소의 체결시간 데이터는 수신되지 않습니다".
  - Scope: N:d0d1a83f, "ID에 연결된 모든 계좌의 체결 통보 수신".
  - Field changes: N:cad37f81-475d-468c-884b-534bc7f29cb6 (CNTG_ISNM, ORD_COND_PRC) and N:3c75de0f-b92f-431c-9f7d-5cb92a7a7721 (CNTG_UNPR12).
  - Final fill: F:4f86cd4d-d3aa-43e5-ad18-027eb3ca6e27, "최종 체결 여부를 직접 알려주는 별도 정보가 제공되지 않습니다".
  - Keep-alive: F:07f312e5-0bf3-4bbe-8179-1ffd7246b392 (100초, PINGPONG).
  - Whether orders can be sent over the socket: UNVERIFIED.
- **5.6 No deposit/withdrawal endpoints.** CONFIRMED. Neither list has a transfer endpoint.

### 6. What distinguishes read-only from trading

- **6.1 HTTP method.** CONFIRMED. F:695cfecd-4379-4ea3-bd24-d23f9400985a: "접근토큰발급과 주문은 POST 방식, 그 외 조회는 GET 방식으로 호출해야". The two lists have 30 GET and 11 POST entries, with no exception.
  - **Wording WRONG:** the note counts `order-resv*` among the POST orders, but some of those paths are GET inquiries:
    - domestic `/trading/order-resv-ccnl` (CTSC0004R) is a GET inquiry;
    - overseas `/trading/order-resv-list` (TTTT3039R / TTTS3014R) is a GET inquiry;
    - overseas `/trading/order-resv-ccnl` (TTTT3017U) is a POST cancel.
  - The same path ending is an inquiry in domestic and an order in overseas, so a path prefix cannot classify either one. Use method plus TR id.
- **6.2 TR id.** CONFIRMED. F:587c7efd-2b76-4f82-9a84-0f924e03459b: "API 호출 시 TR ID 첫 글자는 해당 서버(원장)를 지정합니다."
  - The R/U pattern holds across both lists: every GET real TR ends in R and every POST real TR ends in U. It is still an observation, not a documented rule.
  - F:5c706351-631c-4276-b190-f2b52830a296: "TR 기준으로 원장에 호출을 하기 때문에".
- **6.3 Path is not a separator.** CONFIRMED (from the lists).
- **6.4 Domain is not a separator.** CONFIRMED. F:5c706351: "도메인을 변경해서 사용하시면 TR 기준으로 API 호출되어서 거래가 되는 경우가".
- **6.5 Credentials are identical.** CONFIRMED. P:/uapi/domestic-stock/v1/trading/order-cash uses the same token, appkey and appsecret headers. Its body (CANO, ACNT_PRDT_CD, PDNO, ORD_DVSN, ORD_QTY, ORD_UNPR and others) has no password or PIN field.
- **6.6 The sample rewrites TR ids for mock.** CONFIRMED. GH:examples_user/kis_auth.py lines 422-424.

### 7. Sandbox / paper environment

- **Hosts:** CONFIRMED.
- **Separate credentials:** CONFIRMED. F:5c706351: "앱정보: 모의계좌번호, 모의계좌의 appkey, appsecret".
- **Mock account numbers start with 5:** CONFIRMED (N:747384fe-f047-495c-8548-769c8e6f4c15).
- **EGW00210:** CONFIRMED. ERR: "법인고객의 경우 모의투자를 이용할 수 없습니다."
- **Inquiry coverage in mock:** CONFIRMED (the mock-TR column of both lists).
- **1 REST call/s:** CONFIRMED (see 4.1).
- **Separate operator:** CONFIRMED. N:9858397d-351b-4eda-b6b5-c5ccbcaa64ce: "별도 운영사(연합인포맥스)".
- **KRX only:** CONFIRMED. The title of N:dd2e7e20-51e8-45fd-b65a-24a128f6af34 includes "넥스트레이드 미지원".
- **40910000:** CONFIRMED (N:747384fe).
- **F:ca2cc700 and F:6005110f:** the posts exist, but I did not re-read their wording, so the note's paraphrase is UNVERIFIED.

### 8. Error codes

- **Verbatim match on ERR:** CONFIRMED for EGW00103, EGW00105, EGW00109, EGW00110, EGW00121, EGW00122, EGW00123, EGW00131, EGW00201, EGW00205, EGW00206, EGW00207, EGW00210, EGW00213, EGW00301, EGW00302, EGW00303, EGW00304, OPSP0002, OPSP0008, OPSP8996 and OPSP0011.
- **Not on ERR but CONFIRMED elsewhere:**
  - EGW00133 (N:b9136772);
  - EGW00215 (P inquire-balance);
  - EGW00356 (F:587c7efd);
  - EGW00317 (N:365bc02b);
  - 90070000 and 40910000 (N:747384fe);
  - HTTP 403 (F:695cfecd).
- **Nit:** ERR assigns EGW00213 twice, to "제휴사명(corpname)은 필수 입니다." and to "모의투자 tr이 아닙니다.", so do not key logic on that code alone.
- **F:765ed450-e3a4-4d67-b0f2-16d7d8a52ddc** ("비밀번호 [5회] 오류") exists. Linking it to a password change after key issue is the note's own reading: UNVERIFIED.

### 9. Open questions: status after this pass

1. Inquiry-only key: UNVERIFIED. It remains the central risk, and the guard has to be on the client.
2. Repo guard conflict: CONFIRMED (0.6, 6.1). Add the `order-resv-ccnl` trap: GET in domestic, POST in overseas.
3. Revocation on reissue: UNVERIFIED.
4. tokenP limit wording: CONFIRMED that the official sources conflict (1/min, 1/s and 5 min).
5. What counts toward the 18/s: UNVERIFIED for tokenP and WebSocket traffic. Renewal going straight to the base limit is CONFIRMED (N:c1113824).
6. Eligibility: UNVERIFIED, with the 15abe578 correction from 5.4.
7. Overseas service not enabled: UNVERIFIED.
8. `ACNT_NO` format in fill notices: UNVERIFIED.
9. Missing parameter in the sample: reword it. The sample sends the parameter whenever the caller passes it (5.1).
10. Overseas day/night ledger: UNVERIFIED.
11. KakaoTalk alert as an intrusion signal: UNVERIFIED.
12. Mock coverage gap: CONFIRMED (mock-TR column).

### Corrections to apply to the body above

1. **5.1 / -006:** INQR_DVSN=02 returns an error message and is then auto-routed to 01; it is not rejected (N:050d6619).
2. **5.1 / -005 and open question 9:** the official sample includes EXCG_ID_DVSN_CD conditionally (`domestic_stock_functions.py` lines 4269-4270). It is not omitted.
3. **5.4 and open question 6:** N:15abe578 announces the domestic single-stock leveraged/inverse ETP 심화교육 from 2026-05-22. No domestic API or rejection code is documented for it.
4. **6.1:** `order-resv*` is not all POST. Domestic `order-resv-ccnl` and overseas `order-resv-list` are GET inquiries.
5. **2.7:** add that the approval key is valid for 24 h.
6. **4.6:** the 50/s tier was a one-month programme in December 2025; whether it still runs is unverified.

# Part 5 of 6. Venue research: Upbit, with its Verification section

# Upbit Open API: read-only account inquiry (for E1)

Researched 2026-10-24. This is documentation research only: no key was used and no request was sent to api.upbit.com.
Sources are the official Korean reference at docs.upbit.com/kr (each page carries an `updatedAt` stamp, given as "upd") unless a line is marked **[3rd party]**.
Quotes are short and verbatim (Korean). Field names in backticks are literal schema tokens.
The docs index is at https://docs.upbit.com/llms.txt.

Base: `https://api.upbit.com/v1`. TLS 1.2 or higher. JSON only (https://docs.upbit.com/kr/reference/rest-api-guide, upd 2026-10-06).

---

## 0. Big change since older Upbit docs: "pockets" (포켓)

- An account has one **main pocket** plus user-created **sub pockets**. Each API key is issued **per pocket**, and Exchange rate limits are counted **per pocket**.
  - Source: https://docs.upbit.com/kr/reference/pocket-overview (upd 2026-10-20).
  - Quote: "외부 입출금은 제한됩니다" (sub pockets).
- Pocket count: "최대 5개까지 만들 수 있습니다". The docs do not make clear whether this means 5 sub pockets or 5 pockets in total (same page).
- A sub pocket cannot be renamed or deleted after creation (same page).
- `GET /v1/accounts` returns "포켓이 보유하고 있는 자산 목록과 잔고" (https://docs.upbit.com/kr/reference/get-balance, upd 2026-10-07).
  - The request takes no pocket parameter. I infer, without a doc statement, that the pocket is the one the key was issued from.
- **E1 implication:** if the owner has only a main pocket, a main-pocket key is the only key needed. Sub-pocket balances need a main-pocket key with `포켓관리` (see 4.10).

---

## 1. Authentication and key scopes

### Permission checkboxes (current names)
- Source: https://docs.upbit.com/kr/docs/api-setup (upd 2026-07-07) and pocket-overview (upd 2026-10-20).

| UI name | Machine enum (`permissions`) | Pocket | Read or write |
|---|---|---|---|
| 자산조회 | `view_account` | main + sub | read |
| 주문조회 | `view_orders` | main + sub | read |
| 주문하기 | `make_orders` | main + sub | **write** (orders, cancels, test order) |
| 출금조회 | `view_withdrawals` | main only | read |
| 출금하기 | `withdraw` | main only | **write** |
| 입금조회 | `view_deposits` | main only | read |
| 입금하기 | `deposit` | main only | **write** (KRW deposit, address generation, travel-rule verify) |
| 자산이전 | `transfer` | sub only | **write** |
| 포켓관리 | `manage_pockets` | main only | read **and write** in one scope (lists pockets and also executes transfers) |

- Enum source: https://docs.upbit.com/kr/reference/list-pocket-api-keys (upd 2026-10-07). It lists `view_account`, `view_orders`, `make_orders`, `view_withdrawals`, `withdraw`, `view_deposits`, `deposit`, `transfer`, `manage_pockets`.
- `포켓관리` covers both viewing all pockets' assets and executing transfers (pocket-overview). **Do not grant it to an E1 read-only key.** That leaves sub-pocket balances out of E1 unless the owner accepts this risk.
- At least one permission is mandatory: "최소 하나 이상의 기능을 선택한 후" (https://docs.upbit.com/kr/docs/api-key, upd 2026-07-07).
- Keys are issued on the PC web only, under 마이페이지 > Open API 관리. KYC and 2FA must already be complete (api-key page).
- Max keys: "메인포켓에서 발급가능한 API Key 개수는 최대 10개입니다". Each sub pocket allows 5 (api-key page).
- The secret is shown once: "Secret key는 최초 발급 화면에서만 확인 가능하므로" (api-key page).

### Is an inquiry-only key rejected at the server for order endpoints?
- **Documented as yes.** Every order-write page says "[주문하기] 권한이 설정된 API Key를 사용해야 합니다". Sources:
  - https://docs.upbit.com/kr/reference/new-order (upd 2026-10-07)
  - https://docs.upbit.com/kr/reference/cancel-order
  - https://docs.upbit.com/kr/reference/batch-cancel-orders
- The error is `out_of_scope`: "요청에 필요한 API Key 권한이 없습니다." (rest-api-guide).
- HTTP status varies: "`401 Unauthorized` 또는 `403 Forbidden`으로 다를 수 있습니다" (rest-api-guide). E1 must match on `error.name`, not on the status.
- api-setup says the response is 401 (out_of_scope) when a key lacks a required permission (api-setup page).
- Not empirically verified. The first E1 smoke test could confirm it with `POST /v1/orders/test` using a read-only key, which should fail with `out_of_scope`. That needs the owner's go-ahead (see 9).

### Withdrawal safety lock (출금 안심차단)
- Since 2026-07-09, keys that hold `출금하기` get the lock automatically: "출금 권한이 있으면 자동으로 적용됩니다" (https://docs.upbit.com/kr/changelog/withdrawal-safety-lock).
- The lock can only be removed in the mobile app. The API cannot remove it (same notice).
- The error is `open_api_withdraw_locked`: "Open API 출금이 잠금 상태입니다." (rest-api-guide).
- This is irrelevant to E1 because E1 must not hold `출금하기`.

---

## 2. Token and signature rules, and lifetimes

Source: https://docs.upbit.com/kr/reference/auth (upd 2026-09-22).

### JWT claims
- `access_key`: required.
- `nonce`: required, a new UUID each time. Quote: "매 요청마다 새로운 값을 입력해야 합니다."
- `query_hash`: required when there is a query string or a body.
- `query_hash_alg`: defaults to SHA512. Quote: "기본값은 `SHA512`로".

### Signing
- HMAC over header.payload with the Secret Key used raw. Quote: "Secret Key는 Base64 인코딩 되어있지 않습니다."
- Recommended algorithm: "HS512(HMAC with SHA-512) 사용을 권장합니다." Some WebSocket examples on the same page use HS256, so they are inconsistent with this.

### query_hash
- SHA512 of the query string exactly as sent: same order as sent, no re-sorting.
  - Array parameters repeat the key: `states[]=wait&states[]=watch`.
  - Non-array lists are comma-joined: `pairs=KRW-BTC,KRW-ETH`.
- The auth page says to hash *before* URL encoding. The Java examples on the same page URL-encode first. This is a doc inconsistency. Use the Python SDK's behaviour as the reference (open question).
- The rest-api-guide requires URL-encoding of query params on the wire, except for `[]` in names.

### Header and lifetime
- Header: `Authorization: Bearer <jwt>`.
- **Lifetime:** no `exp` claim and no TTL are documented. Each request needs a fresh token because the nonce is single-use: `nonce_used` "이미 사용된 `nonce` 값입니다." (rest-api-guide). The size or length of the nonce-replay window is not documented.

### Duplicate headers
- From 2026-07-31, a duplicated `Content-Type` "400 오류가 반환될 수 있습니다" (https://docs.upbit.com/kr/changelog/prevent-duplicate-request-headers). Send each header once.

### Key expiry
- `GET /v1/api_keys` returns `expire_at` for each key: "계정의 모든 API Key 목록과 각 Key의 만료일자를 조회합니다." (https://docs.upbit.com/kr/reference/list-api-keys, upd 2026-10-07).
- **A fixed validity period (e.g. one year) is not documented** in any official page I found.
- The only hint is an example in list-pocket-api-keys: `created_at` 2026-05-28T15:17:51+09:00 and `expired_at` 2027-05-27T15:17:51+09:00. That is an implied 1-year period (inference from an example, not a rule).
- An expired key returns `expired_access_key` "API Key가 만료되었습니다." (rest-api-guide).
- **E1 should read `expire_at` itself and alert ahead of expiry.**

---

## 3. IP binding

Source: https://docs.upbit.com/kr/docs/api-key (upd 2026-07-07).

- **Mandatory for every key, including inquiry-only keys:** "'IP 주소 등록'창에 하나 이상의 IP를 입력".
- Public IP only: "사설 IP는 외부 접근이 불가능하므로 등록할 수 없습니다".
- IPv4 only: "IPv4형식의 IP 주소만 지원합니다."
- A static IP is recommended over a dynamic one. The allowed list can be changed later with [변경].
- A wrong IP returns `no_authorization_ip` "API Key에 등록되지 않은 IP에서 요청했습니다." (rest-api-guide). The get-balance example message is "This is not a verified IP."
- `GET /v1/pockets/api_keys` returns `allowed_ips` for each key (list-pocket-api-keys).
- **[3rd party]** fnnews, 2026-10-08, reporting Dunamu: a call from an unregistered IP triggers a KakaoTalk alert to the owner. https://www.fnnews.com/news/202610080852170334
- **E1 risk:** a Korean residential connection usually has a dynamic IP. If the IP changes, every call fails closed with `no_authorization_ip` until the owner updates the allowlist on the PC web.

---

## 4. Read-only endpoints (REST)

Common to all of section 4:
- Rate limit group `default`: "초당 최대 30회 호출할 수 있습니다". Counted per pocket.
- Pages are dated upd 2026-10-07 unless noted.
- All money and quantity values are **decimal strings**.

### 4.1 Balances: `GET /v1/accounts` (자산조회)
- Doc: https://docs.upbit.com/kr/reference/get-balance. Quote: "[자산조회] 권한이 설정된 API Key가 필요합니다."
- Params: none.
- Response: array of:
  - `currency`
  - `balance`: orderable amount
  - `locked`: amount locked for orders or withdrawals
  - `avg_buy_price`
  - `avg_buy_price_modified` (bool)
  - `unit_currency`: the unit of `avg_buy_price` (KRW, BTC or USDT)
- Total holding = `balance` + `locked`.

### 4.2 Market eligibility and fees: `GET /v1/orders/chance` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/available-order-information.
- Required param: `market` (e.g. `KRW-BTC`).
- Fees: `bid_fee`, `ask_fee`, `maker_bid_fee`, `maker_ask_fee`.
- `market` object:
  - `id`, `name`
  - `order_sides`
  - `bid_types`, `ask_types` (`order_types` is deprecated: "지원이 종료될 예정입니다")
  - `bid.min_total`, `ask.min_total`
  - `max_total`
  - `state` (only `active` is documented)
- `bid_account` and `ask_account`: same fields as accounts.
- There is no warnings field. Market warnings come from the public `GET /v1/market/all?is_details=true`, which returns `market_event.warning` and `market_event.caution{PRICE_FLUCTUATIONS, TRADING_VOLUME_SOARING, DEPOSIT_AMOUNT_SOARING, GLOBAL_PRICE_DIFFERENCES, CONCENTRATION_OF_SMALL_ACCOUNTS}`. That endpoint is IP-limited at 10/s (https://docs.upbit.com/kr/reference/list-trading-pairs, upd 2026-07-29).
- Errors: 400 `invalid_parameter`, `notfoundmarket`.

### 4.3 Single order with fills: `GET /v1/order` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/get-order.
- Params: `uuid` or `identifier`. Quote: "uuid 또는 identifier 중 하나는 반드시 포함해야 합니다." If both are sent, uuid wins.
- Fields:
  - `uuid`, `market`, `side`, `ord_type`, `price`
  - `state` (`wait`/`watch`/`done`/`cancel`), `created_at`
  - `volume`, `remaining_volume`, `executed_volume`
  - `reserved_fee`, `remaining_fee`, `paid_fee`
  - `locked`, `trades_count`, `time_in_force`, `identifier`
  - `smp_type`, `prevented_volume`, `prevented_locked`
- **Fills:** `trades[]` with `market`, `uuid`, `price`, `volume`, `funds`, `trend`, `created_at`, `side`.
- `trades[]` appears **only on this single-order call**: "체결 목록 (개별 주문 조회 시 반환)" (list-open-orders schema).
- Error: 404 `order_not_found`.
- **There is no account-wide "my trades" REST endpoint** in the index. Fills come from `GET /v1/order` per order, or from WebSocket `myOrder` (section 5).

### 4.4 Open orders: `GET /v1/orders/open` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/list-open-orders (upd 2026-10-07).
- Params:
  - `market`
  - `state` or `states[]` (`wait`, `watch`; default `wait`). Quote: "state와 states[]는 동시에 사용할 수 없습니다."
  - `page` (default 1)
  - `limit` (default 100, max 100)
  - `order_by` (default `desc`)
- Order fields as in 4.3, but with no `trades[]`.
- **DANGER:** `DELETE /v1/orders/open` on the same path is **cancel-all** (주문하기, group `order-cancel-all`) (https://docs.upbit.com/kr/reference/batch-cancel-orders).

### 4.5 Closed orders: `GET /v1/orders/closed` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/list-closed-orders.
- Params:
  - `market`
  - `state` or `states[]` (`done`, `cancel`)
  - `start_time`, `end_time` (ISO 8601 or ms)
  - `limit` (default 100, max 1000)
  - `order_by`
- The window is at most 7 days. With no times given, it is the 7 days before the request.
- How far back history goes overall is not documented.

### 4.6 Orders by id: `GET /v1/orders/uuids` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/list-orders-by-ids (upd 2026-10-07).
- Params: `uuids[]` or `identifiers[]`, max 100 each, not both. Quote: "두 파라미터를 동시에 사용할 수 없습니다." Optional `market`, `order_by`.
- The callout on the same page spells the parameter `identifier[]`. This is a doc typo.
- **DANGER:** `DELETE /v1/orders/uuids` is cancel-by-ids (https://docs.upbit.com/kr/reference/cancel-orders-by-ids).

### 4.7 Deprecated list endpoint: `GET /v1/orders`
- Deprecated since 2024-06. Quote: "정확한 지원종료 예정일은 추후 공지사항을 통해 다시 안내드리겠습니다" (https://docs.upbit.com/kr/v1.5.9/reference/주문-리스트-조회, older versioned docs).
- **Do not use it in E1.**

### 4.8 Withdrawals (출금조회; main pocket only)
- **`GET /v1/withdraws`** (https://docs.upbit.com/kr/reference/list-withdrawals)
  - Params:
    - `currency`, `state`
    - `uuids[]` or `txids[]` (max 100)
    - `limit` (max 100), `page`, `order_by`
    - cursors `from` / `to` (a uuid)
  - States: `WAITING`, `PROCESSING`, `DONE`, `FAILED`, `CANCELLED`, `REJECTED`.
  - Fields:
    - `type`, `uuid`, `currency`, `net_type`, `txid`, `state`
    - `created_at`, `done_at`
    - `amount`, `fee`
    - `transaction_type` (`default` / `internal`), `is_cancelable`
- **`GET /v1/withdraw`** (https://docs.upbit.com/kr/reference/get-withdrawal)
  - Params: `uuid` / `txid` / `currency`.
  - With no id it returns the latest: "uuid와 txid를 모두 입력하지 않는 경우 최신 출금 정보가 반환됩니다."
  - Error: 404 `withdraw_not_found`.
- **`GET /v1/withdraws/chance`** (https://docs.upbit.com/kr/reference/available-withdrawal-information, upd 2026-10-07)
  - Required params: `currency` and `net_type`.
  - `member_level`:
    - `security_level`, `fee_level`
    - `email_verified`, `identity_auth_verified`, `bank_account_verified`, `two_factor_auth_verified`
    - `locked`, `wallet_locked`
  - `currency`:
    - `code`, `withdraw_fee`, `is_coin`
    - `wallet_state`, `wallet_support` (a list: `deposit` and/or `withdraw`)
  - `account`: same fields as accounts.
  - `withdraw_limit`:
    - `minimum`, `fixed`, `fiat_currency`
    - `remaining_daily_fiat`, `withdraw_delayed_fiat`, `can_withdraw`
    - deprecated: `onetime`, `daily`, `remaining_daily`, `remaining_daily_krw`
- **`GET /v1/withdraws/coin_addresses`**: the registered withdrawal **allowlist** (https://docs.upbit.com/kr/reference/list-withdrawal-addresses, upd 2026-10-07)
  - Params: none.
  - Fields:
    - `currency`
    - `net_type` (must be used in the withdrawal), `network_name` (display only)
    - `withdraw_address`, `secondary_address` (tag/memo, nullable)
    - `beneficiary_name`, `beneficiary_company_name`, `beneficiary_type` (`individual`/`corporate`)
    - `exchange_name` (exchange wallet), `wallet_type` (personal wallet, e.g. 메타마스크)
  - Registration happens on the PC web only (마이페이지 > Open API 관리 > 디지털 자산 출금주소 관리). No registration API is documented.
  - Travel-rule address verification with the counterparty exchange happens at registration. If it fails, withdrawals to that address may be restricted.
  - The doc is inconsistent about whether `beneficiary_name` is null for personal wallets.

### 4.9 Deposits (입금조회; main pocket only)
- **`GET /v1/deposits`** (https://docs.upbit.com/kr/reference/list-deposits, upd 2026-10-07)
  - Params: the same set as withdraws.
  - States:
    - `PROCESSING`, `ACCEPTED`, `CANCELLED`, `REJECTED`
    - `TRAVEL_RULE_SUSPECTED`, `REFUNDING`, `REFUNDED`
  - Fields:
    - `type`, `uuid`, `currency`
    - `net_type` (null for KRW), `txid`, `state`
    - `created_at`, `done_at` (KST)
    - `amount`, `fee`, `transaction_type`
- **`GET /v1/deposit`** (https://docs.upbit.com/kr/reference/get-deposit)
  - Params: `uuid` / `txid` / `currency`. With none, it returns the latest.
  - Error: 404 `deposit_not_found`.
- **`GET /v1/deposits/coin_addresses`** (https://docs.upbit.com/kr/reference/list-deposit-addresses)
  - Params: none.
  - Fields: `currency`, `net_type`, `deposit_address`, `secondary_address`.
- **`GET /v1/deposits/coin_address`** (https://docs.upbit.com/kr/reference/get-deposit-address)
  - Required params: `currency` and `net_type`.
  - `deposit_address` may be null right after generation: "deposit_address 필드가 null로 반환될 수 있습니다."
- **`GET /v1/deposits/chance/coin`** (https://docs.upbit.com/kr/reference/available-deposit-information)
  - Required params: `currency` and `net_type`.
  - Fields:
    - `is_deposit_possible`, `deposit_impossible_reason`
    - `minimum_deposit_amount`, `minimum_deposit_confirmations`, `decimal_precision`
  - Not real time: "서비스 상태를 실시간으로 반영하지 않으며".
- **DANGER:** `POST /v1/deposits/generate_coin_address` is a write call under 입금하기 (https://docs.upbit.com/kr/reference/create-deposit-address). E1 must never call it.

### 4.10 Pockets (포켓관리; main-pocket key only; this scope also allows transfers)
- `GET /v1/pockets`: `uuid`, `name`, `type` (`main` / `user_spot_trading`) (https://docs.upbit.com/kr/reference/list-pockets, upd 2026-10-07).
- `GET /v1/pockets/assets?uuid=`: sub-pocket balances, with the same fields as accounts. Errors: 404 `pocket_not_found` (https://docs.upbit.com/kr/reference/get-sub-pocket-balance).
- `GET /v1/pockets/api_keys` (`uuids[]`, `include_expired`): each key's `access_key`, `permissions`, `allowed_ips`, `created_at`, `expired_at` (https://docs.upbit.com/kr/reference/list-pocket-api-keys).
  - This is the only documented way for a program to read its own key's scopes.
- `GET /v1/pockets/universal_transfers`: transfer history, with a 7-day window (https://docs.upbit.com/kr/reference/list-universal-transfers).

### 4.11 Keys and wallet status (auth, no extra permission)
- **`GET /v1/api_keys`**: "별도 권한은 필요하지 않습니다".
  - Fields: `access_key`, `expire_at` (KST).
  - It does **not** return scopes (https://docs.upbit.com/kr/reference/list-api-keys).
- **`GET /v1/status/wallet`**: "인증이 필요한 API입니다. 별도 권한은 필요하지 않습니다." (https://docs.upbit.com/kr/reference/get-service-status, upd 2026-10-07).
  - Fields:
    - `currency`
    - `wallet_state` (`working`/`withdraw_only`/`deposit_only`/`paused`/`unsupported`)
    - `block_state` (`normal`/`delayed`/`inactive`), `block_height`, `block_updated_at`, `block_elapsed_minutes`
    - `net_type`, `network_name`
  - Not real time: "실시간 상태 조회를 보장하지 않습니다."

### 4.12 Travel rule
- **`GET /v1/travel_rule/vasps`** (입금조회): `vasp_name`, `vasp_uuid`, `depositable`, `withdrawable` (https://docs.upbit.com/kr/reference/list-travelrule-vasps).
- Verification is **not read-only**:
  - `POST /v1/travel_rule/deposit/uuid` takes `deposit_uuid` and `vasp_uuid`. It requires 입금하기, and a deposit can be verified "10분당 최대 1회" (https://docs.upbit.com/kr/reference/verify-travelrule-by-uuid).
  - `POST /v1/travel_rule/deposit/txid` takes `vasp_uuid`, `txid`, `currency`, `net_type`. Same scope and same limit (https://docs.upbit.com/kr/reference/verify-travelrule-by-txid).
  - A successful verification releases a `TRAVEL_RULE_SUSPECTED` deposit (https://docs.upbit.com/kr/reference/travelrule-guide, upd 2026-07-28).
- **E1 can only *see* a `TRAVEL_RULE_SUSPECTED` deposit.** Releasing it is a manual or write step.
- Travel-rule verification for withdrawal addresses happens at address registration on the web (4.8). No API for it is documented.

### 4.13 Withdrawal hold after a KRW deposit
- **Visible through the API only as an amount:** `withdraw_limit.withdraw_delayed_fiat` "출금 지연 제도로 인해 출금이 제한된 금액" (withdraws/chance). The API reports no trigger time or release time.
- Policy, official changelog (https://docs.upbit.com/kr/changelog/안내-24시간-디지털-자산-출금-지연제-도입-안내):
  - Effective 2020-11-28 15:00.
  - Quote: "해당 입금액 가치의 디지털 자산은 24시간 경과 후 출금 가능합니다."
- Upbit support center says the **first** KRW deposit triggers a 72-hour digital-asset withdrawal hold, and later deposits trigger 24 hours each. The page returned HTTP 403 to my fetch, so this comes from a search-result summary only and needs verification: https://support.upbit.com/hc/ko/articles/900005806486

---

## 5. Read-only WebSocket (optional for E1)

Endpoint: `wss://api.upbit.com/websocket/v1/private`, with the JWT in the Authorization header (https://docs.upbit.com/kr/reference/websocket-guide, upd 2026-09-23).

- **`myOrder`** (https://docs.upbit.com/kr/reference/websocket-myorder, upd 2026-10-13)
  - Fills arrive with `state=trade`.
  - Fill fields: `trade_uuid`, `price`, `volume`, `trade_fee`, `is_maker`, `trade_timestamp`.
  - Running totals: `avg_price`, `executed_volume`, `executed_funds`, `paid_fee`.
  - Nothing is sent without activity: "주문 또는 체결이 없으면 데이터가 전송되지 않습니다."
- **`myAsset`** (https://docs.upbit.com/kr/reference/websocket-myasset, upd 2026-09-22)
  - Fields: `assets[{currency, balance, locked}]`, `asset_timestamp`.
  - Pushes only when holdings change.
  - The first push can be delayed by minutes.
- The required permission for either stream is **not documented**.
- The auth error is `INVALID_AUTH`.
- **E1 should poll REST as the source of truth.** WebSocket is at most a hint.

---

## 6. Rate limits

Source: https://docs.upbit.com/kr/reference/rate-limits (upd 2026-10-07).

### Groups

| Group | Limit | Counted per |
|---|---|---|
| Quotation (`market`, `candle`, `trade`, `ticker`, `orderbook`) | 10/s each | IP |
| Exchange `default` (all of section 4) | 30/s | pocket |
| `order` | 12/s (raised from 8/s on 2026-08-21: https://docs.upbit.com/kr/changelog/order-rate-limit-update) | pocket |
| `order-test` | 8/s | pocket |
| `order-cancel-all` | 1 per 2 s | pocket |
| `websocket-connect` | 5/s | IP without auth, pocket with auth |
| `websocket-message` | 5/s and 100/min | connection |

- Quotation or WebSocket requests that carry an `Origin` header are limited to 1 per 10 s.
- The per-minute REST limit no longer applies (order-rate-limit-update notice).

### Remaining-Req header
- Example: `Remaining-Req: group=default; min=1800; sec=29`.
- `min` is deprecated. Use `sec`.

### 429 and 418
- **429**: "API 호출 한도를 초과했습니다." Wait until the next second, then retry.
- **418**: "과도한 요청으로 인해 요청 제한이 적용되었습니다."
  - It is a block per IP, pocket or connection.
  - The response carries the block time.
  - Repeat offences lengthen the block.
- The best-practice page says to stop all calls in the group on a 429 (https://docs.upbit.com/kr/docs/rest-api-best-practice, upd 2026-05-04).

---

## 7. What separates read-only from trading at the protocol level

1. **Permission scope on the key, enforced at the server** (documented). An E1 key should hold only `view_account`, `view_orders`, `view_withdrawals`, `view_deposits`. Order writes need `make_orders` and return `out_of_scope` without it.
2. **HTTP method.** Every E1 call is `GET`. Two pairs share a path with a destructive verb:
   - `GET/DELETE /v1/order`
   - `GET/DELETE /v1/orders/open` (DELETE is cancel-all)
   - `GET /v1/orders/uuids` vs `DELETE` on the same path (cancel-by-ids)

   **The E1 client should hard-code `GET` and refuse any other verb.**
3. `POST` is used only by write endpoints:
   - orders and the test order
   - deposits/krw and generate_coin_address
   - withdraws and withdraws/krw
   - travel_rule verify
   - pocket transfers
4. Rate-limit groups also differ: `default` vs `order*`.
5. Scopes that are not purely read:
   - `포켓관리` mixes read and transfer.
   - Travel-rule verify sits under `입금하기`.

   Keep both off an E1 key.
6. A read-only key **cannot** use `POST /v1/orders/test`, because it needs 주문하기 (https://docs.upbit.com/kr/reference/order-test). So E1 has no dry-run order check.

---

## 8. Sandbox or paper environment

- **None documented.** The llms.txt index has no sandbox page.
- The only test facility is `POST /v1/orders/test`:
  - Quote: "실제 주문을 생성하지 않고 주문 요청 형식과 주문 가능 여부를 검증합니다."
  - It needs `주문하기` and uses the `order-test` group (8/s).
  - It returns 403 `market_offline` for a pair that cannot be traded yet.
  - UUIDs it returns cannot be looked up.
- All read-only calls hit production. With a GET-only client and a view-only key, this is low-risk.

---

## 9. Error codes (auth, permissions, rate limits)

Source: https://docs.upbit.com/kr/reference/rest-api-guide (upd 2026-10-06).

| HTTP | `error.name` | Meaning (quote) |
|---|---|---|
| 401 | `invalid_query_payload` | "JWT 페이로드가 올바르지 않습니다." |
| 401 | `jwt_verification` | "JWT 검증에 실패했습니다." |
| 401 | `expired_access_key` | "API Key가 만료되었습니다." |
| 401 | `nonce_used` | "이미 사용된 `nonce` 값입니다." |
| 401 | `no_authorization_ip` | "API Key에 등록되지 않은 IP에서 요청했습니다." |
| 401 | `no_authorization_token` | No Bearer token |
| 401/403 | `out_of_scope` | "요청에 필요한 API Key 권한이 없습니다." |
| 403 | `open_api_withdraw_locked` | "Open API 출금이 잠금 상태입니다." |
| 404 | `pocket_not_found`, `currency_not_found`, `order_not_found`, `withdraw_not_found`, `deposit_not_found` | Not found |
| 418 | (no name) | Temporary block |
| 429 | (no name) | Rate limit exceeded |
| WS | `INVALID_AUTH`, `TOO_MANY_REQUEST` | WebSocket |

- Error body: `{"error":{"name","message"}}`.
- In the Exchange API `name` is a string. In the Quotation API it is an integer.
- `invalid_access_key` (from older client libraries) is **not** in the current guide.

---

## 10. Open questions

1. Is a one-year key lifetime official policy? It is not documented. The only evidence is an example in list-pocket-api-keys. E1 should read `GET /v1/api_keys` `expire_at`.
2. Does `GET /v1/accounts` on a main-pocket key include sub-pocket assets? The docs only say it returns "포켓이 보유하고 있는 자산".
3. Does the query_hash use URL-encoded or unencoded values? The auth page says "before encoding" and its Java examples encode first. Check against the official Python SDK at https://github.com/upbit-official.
4. Is the HTTP status of `out_of_scope` on order endpoints 401 or 403? Both are documented. Match on `error.name`.
5. Which permissions do WebSocket `myOrder` and `myAsset` need? Not documented.
6. The withdrawal-delay rule (72 h after the first KRW deposit, 24 h after each later one) comes from the support center, which my fetch could not open. The API shows only `withdraw_delayed_fiat` and gives no release time.
7. How far back do `/v1/orders/closed` and `/v1/deposits` / `/v1/withdraws` history go? Not documented beyond the 7-day window per request and the 100-per-page limit.
8. "최대 5개": is the cap 5 sub pockets or 5 pockets in total?
9. How long is the nonce-replay window, and is there a clock-skew rule? Not documented. Since there is no `exp` claim, clock skew probably does not matter, but this is not confirmed.
10. Dynamic residential IP: the docs give no fallback. The owner must re-register the IP on the PC web.
11. Which IP and machine will hold the read-only key? This is an owner decision, and per the hard rules the agent never enters keys.

---

## Verification (skeptic)

Re-checked 2026-10-24 against docs.upbit.com/kr (WebFetch of each page, no API call). Items follow the note's own numerical order (section 0 to 10). Quotes are verbatim and under 15 words. Default is UNVERIFIED when no official sentence was found.

Tally: 4 WRONG (V18, V89, V91, V97), 7 UNVERIFIED (V28, V31, V41, V50, V74, V75, V99), 1 partly UNVERIFIED (V90), the rest CONFIRMED.

### Header
- V0. Base `https://api.upbit.com/v1`, TLS 1.2+. **CONFIRMED** (rest-api-guide): "TLS 1.2 이상 버전만 지원합니다"

### Section 0. Pockets
- V1. Sub pockets: external deposits and withdrawals restricted. **CONFIRMED.** https://docs.upbit.com/kr/reference/pocket-overview: "외부 입출금은 제한됩니다"
- V2. Exchange rate limits are counted per pocket. **CONFIRMED.** pocket-overview: "Rate Limit은 포켓(Pocket) 단위로 적용됩니다"
- V3. Keys are issued per pocket. **CONFIRMED.** https://docs.upbit.com/kr/docs/api-key gives separate caps per pocket, and pocket-overview links "포켓 별 API Key 발급 받으러 가기".
- V4. "최대 5개" is ambiguous. **CONFIRMED as ambiguous.** Full sentence: "메인포켓은 1개, 서브포켓은 필요에 따라 직접 추가할 수 있으며 최대 5개까지 만들 수 있습니다." The most natural reading is 5 sub pockets, but the page does not say so.
- V5. Sub pocket cannot be renamed or deleted. **CONFIRMED.** pocket-overview: "서브포켓 명칭 변경 및 삭제가 불가능하므로"
- V6. `GET /v1/accounts` returns the pocket's assets, with no pocket parameter. **CONFIRMED.** https://docs.upbit.com/kr/reference/get-balance: "포켓이 보유하고 있는 자산 목록과 잔고를 조회합니다." The page lists no parameters. Which pocket is meant is still UNVERIFIED (see V75).

### Section 1. Authentication and key scopes
- V7. The nine UI names and their pocket applicability (자산조회/주문조회/주문하기 main+sub; 입출금 main only; 자산이전 sub; 포켓관리 main). **CONFIRMED.** https://docs.upbit.com/kr/docs/api-setup (upd 2026-07-07) has the table.
- V8. Permissions enum (`view_account` … `manage_pockets`, 9 values). **CONFIRMED.** https://docs.upbit.com/kr/reference/list-pocket-api-keys (upd 2026-10-07) lists all nine.
- V9. 포켓관리 = view all pockets + execute transfers. **CONFIRMED.** pocket-overview: "모든 포켓의 자산 조회, 자산 이전 실행 및 내역 조회"
- V10. At least one permission required. **CONFIRMED.** api-key: "최소 하나 이상의 기능을 선택한 후"
- V11. PC web only, KYC + 2FA first. **CONFIRMED.** api-key: "업비트 API Key 발급은 PC 웹 환경에서만 가능합니다." It also requires 고객 확인 and 2채널 인증(2FA).
- V12. Max 10 keys on main, 5 per sub pocket. **CONFIRMED.** api-key: "서브포켓 당 발급 가능한 API Key 개수는 최대 5개입니다."
- V13. Secret shown once. **CONFIRMED.** api-key: "Secret key는 최초 발급 화면에서만 확인 가능하므로"
- V14. Order writes require 주문하기. **CONFIRMED** on all three pages: https://docs.upbit.com/kr/reference/new-order (`POST /v1/orders`), https://docs.upbit.com/kr/reference/cancel-order (`DELETE /v1/order`) and https://docs.upbit.com/kr/reference/batch-cancel-orders (`DELETE /v1/orders/open`). Each says "[주문하기] 권한이 설정된 API Key를 사용해야 합니다."
- V15. Error `out_of_scope`. **CONFIRMED.** https://docs.upbit.com/kr/reference/rest-api-guide: "요청에 필요한 API Key 권한이 없습니다."
- V16. Status can be 401 or 403. **CONFIRMED.** rest-api-guide: "`401 Unauthorized` 또는 `403 Forbidden`으로 다를 수 있습니다". The guide files it under 403. api-setup lists "401 Unauthorized(out_of_scope)".
- V17. The server refuses read-only keys for orders. **CONFIRMED as documented only.** No official source shows an observed response, so the empirical check is still pending (owner go-ahead).
- V18. Withdrawal safety lock is applied automatically to every key holding 출금하기 since 2026-07-09. **WRONG (overbroad).** https://docs.upbit.com/kr/changelog/withdrawal-safety-lock says it applies to keys **issued** from 2026-07-09 15:00. Older keys keep their current behaviour and can opt in. "출금 권한이 있으면 자동으로 적용됩니다" is still accurate for new keys. No E1 impact.
- V19. The lock cannot be removed through the API. **CONFIRMED.** Same notice: "API를 활용해 출금 안심 차단 해제는 불가능합니다." It is removed in the mobile app under 인증/보안 > Open API 관리.
- V20. Error `open_api_withdraw_locked`. **CONFIRMED.** rest-api-guide: "Open API 출금이 잠금 상태입니다." The changelog itself names no error code.

### Section 2. Token and signature
- V21. Claims `access_key`, `nonce` (fresh each request), `query_hash` (when there is a query or body), `query_hash_alg` default SHA512. **CONFIRMED.** https://docs.upbit.com/kr/reference/auth (upd 2026-09-22): "매 요청마다 새로운 값을 입력해야 합니다."
- V22. Secret not Base64; HS512 recommended. **CONFIRMED.** auth: "Secret Key는 Base64 인코딩 되어있지 않습니다."
- V23. Some WebSocket examples use HS256. **CONFIRMED.** The auth page's Java WebSocket example uses `Algorithm.HMAC256`.
- V24. Hash before URL encoding, and the Java examples encode first. **CONFIRMED, with an addition.** auth: "URL 인코딩되지 않은 쿼리 문자열을 기준으로 Hash 값을 생성해야 합니다." The Python example matches the rule (`unquote(urlencode(params, doseq=True))`). **The Node examples also hash an encoded string**, so it is not only Java. The two forms differ only when values hold reserved characters or spaces. The Python example on the auth page is the safe reference.
- V25. Wire encoding: URL-encode all params except `[]` in names. **CONFIRMED.** rest-api-guide (GET/DELETE query params; brackets of array names left unencoded).
- V26. Header `Authorization: Bearer <jwt>`. **CONFIRMED.** auth.
- V27. No `exp`/TTL documented; nonce single-use. **CONFIRMED (absence).** The auth payload table lists only the 4 claims, and no example sets `exp`. rest-api-guide: "이미 사용된 `nonce` 값입니다."
- V28. Nonce replay window and clock-skew rule. **UNVERIFIED.** Neither is documented (auth, rest-api-guide).
- V29. Duplicate `Content-Type` may cause 400, from 2026-07-31. **CONFIRMED.** https://docs.upbit.com/kr/changelog/prevent-duplicate-request-headers: "400 오류가 반환될 수 있습니다"
- V30. `GET /v1/api_keys` returns `expire_at`, needs no extra permission. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-api-keys: "계정의 모든 API Key 목록과 각 Key의 만료일자를 조회합니다." Note: the schema describes `expire_at` as "해당 Access Key의 Deprecated일시 (KST)". Treat it as the expiry time.
- V31. A fixed 1-year validity. **UNVERIFIED.** No policy sentence was found on api-key, api-setup or auth. The only evidence is the list-pocket-api-keys example (`created_at` 2026-05-28T15:17:51+09:00, `expired_at` 2027-05-27T15:17:51+09:00), which matches the note.
- V32. `expired_access_key`. **CONFIRMED.** rest-api-guide: "API Key가 만료되었습니다."

### Section 3. IP binding
- V33. At least one IP is mandatory for every key. **CONFIRMED.** api-key FAQ: "'IP 주소 등록'창에 하나 이상의 IP를 입력". No exemption exists for inquiry-only keys.
- V34. Public IPv4 only, no private IP. **CONFIRMED.** api-key: "IPv4형식의 IP 주소만 지원합니다."
- V35. Static IP recommended; list editable with [변경]. **CONFIRMED.** api-key: "업비트 API는 유동 IP 환경에서의 이용을 권장하지 않습니다."
- V36. `no_authorization_ip`, and the get-balance example "This is not a verified IP." **CONFIRMED** on rest-api-guide and get-balance.
- V37. `allowed_ips` in `GET /v1/pockets/api_keys`. **CONFIRMED.** list-pocket-api-keys: "API 요청이 허용된 IP 주소 목록"
- V38. KakaoTalk alert on unregistered IP. **CONFIRMED as a third-party report only** (fnnews 2026-10-08): "등록하지 않은 IP에서 API 호출 시도가 발생하면 카카오톡 알림톡". No official doc page found.

### Section 4. Read-only REST endpoints
- V39. `default` group 30/s, per pocket. **CONFIRMED.** https://docs.upbit.com/kr/reference/rate-limits (upd 2026-10-07) and each endpoint page: "초당 최대 30회 호출할 수 있습니다"
- V40. 4.1 `GET /v1/accounts`, 자산조회, fields `currency, balance, locked, avg_buy_price, avg_buy_price_modified, unit_currency`. **CONFIRMED.** get-balance: "[자산조회] 권한이 설정된 API Key가 필요합니다."
- V41. 4.1 "Total = balance + locked". **UNVERIFIED (inference).** It is consistent with the field definitions ("주문 가능 수량 또는 금액", "출금이나 주문 등에 잠겨 있는 잔액"), but no doc sentence states the sum.
- V42. 4.2 `GET /v1/orders/chance`, required `market`, 주문조회, the fee and market fields, `state` enum `active` only, 400 `invalid_parameter`/`notfoundmarket`. **CONFIRMED.** https://docs.upbit.com/kr/reference/available-order-information: "[주문조회] 권한이 설정된 API Key를 사용해야 합니다." `order_types` is marked deprecated ("지원 종료 이후 응답에서 해당 필드가 제거될 예정").
- V43. 4.2 No warnings field; `GET /v1/market/all?is_details=true` gives `market_event.warning` + 5 caution keys, at 10/s per IP. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-trading-pairs (upd 2026-07-29): "초당 최대 10회 호출할 수 있습니다"
- V44. 4.3 `GET /v1/order`, uuid or identifier with uuid winning, fields incl. `smp_type`/`prevented_*`, `trades[]` subfields, 404 `order_not_found`. **CONFIRMED.** https://docs.upbit.com/kr/reference/get-order: "uuid 또는 identifier 중 하나는 반드시 포함해야 합니다."
- V45. 4.3 `trades` only on single-order lookup. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-open-orders schema: "체결 목록 (개별 주문 조회 시 반환)"
- V46. 4.3 No account-wide "my trades" REST endpoint. **CONFIRMED (absence).** The Order section of https://docs.upbit.com/llms.txt lists only order create/test/get/list/cancel pages. The only fills listings are public pair trades and WebSocket MyOrder.
- V47. 4.4 `GET /v1/orders/open`: `state`/`states[]` exclusive, default `wait`, limit 100/100, `order_by` default `desc`. **CONFIRMED.** list-open-orders: "state와 states[]는 동시에 사용할 수 없습니다."
- V48. 4.4 `DELETE /v1/orders/open` = cancel-all, 주문하기, group `order-cancel-all`. **CONFIRMED** (batch-cancel-orders).
- V49. 4.5 `GET /v1/orders/closed`: limit max 1000, 7-day max window, default = previous 7 days. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-closed-orders: "최대 조회 범위는 7일입니다." Also documented: only `start_time` set gives the next 7 days, and only `end_time` set gives the previous 7 days.
- V50. 4.5 Overall history depth. **UNVERIFIED** (not documented).
- V51. 4.6 `GET /v1/orders/uuids`: max 100, not both, and the callout typo `identifier[]`. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-orders-by-ids: "두 파라미터를 동시에 사용할 수 없습니다." Callout: "uuid[] 또는 identifier[]를 반드시 포함해야 합니다". Both `uuid[]` and `identifier[]` are typos there.
- V52. 4.6 `DELETE /v1/orders/uuids` = cancel-by-ids. **CONFIRMED** (https://docs.upbit.com/kr/reference/cancel-orders-by-ids, 주문하기).
- V53. 4.7 `GET /v1/orders` deprecated since 2024-06, no end date. **CONFIRMED.** https://docs.upbit.com/kr/v1.5.9/reference/주문-리스트-조회: header "Deprecated (2024.06~)". Also: "정확한 지원종료 예정일은 추후 공지사항을 통해 다시 안내드리겠습니다".
- V54. 4.8 `GET /v1/withdraws`: params, state enum, fields, `transaction_type` default/internal. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-withdrawals: "uuids와 txids 파라미터는 동시에 사용할 수 없습니다."
- V55. 4.8 Withdrawal and deposit inquiry are main pocket only. **CONFIRMED via api-setup** (입출금 permissions are main pocket only). The endpoint pages themselves do not say so.
- V56. 4.8 `GET /v1/withdraw` returns the latest when there is no id; 404 `withdraw_not_found`. **CONFIRMED.** https://docs.upbit.com/kr/reference/get-withdrawal: "uuid와 txid를 모두 입력하지 않는 경우 최신 출금 정보가 반환됩니다."
- V57. 4.8 `GET /v1/withdraws/chance`: required `currency`+`net_type`, `member_level`/`currency`/`account`/`withdraw_limit` fields, deprecated four. **CONFIRMED** (https://docs.upbit.com/kr/reference/available-withdrawal-information). Small correction: `net_type` is described as required for digital assets.
- V58. 4.8 `GET /v1/withdraws/coin_addresses`: fields, PC-web registration, travel-rule check at registration, `beneficiary_name` inconsistency. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-withdrawal-addresses: "해당 주소를 발급한 상대 거래소로 주소 검증을 요청합니다." On the inconsistency: the field text says null for personal wallets, while the callout and example ("John" on MetaMask) say the member's name.
- V59. 4.9 `GET /v1/deposits` state enum and fields; `net_type` null for KRW. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-deposits: "원화(KRW) 입금의 경우 null로 반환됩니다."
- V60. 4.9 `GET /v1/deposit` returns the latest when there is no id; 404 `deposit_not_found`. **CONFIRMED** (https://docs.upbit.com/kr/reference/get-deposit).
- V61. 4.9 `GET /v1/deposits/coin_addresses` with no params and 4 fields; `GET /v1/deposits/coin_address` with `deposit_address` possibly null. **CONFIRMED** (list-deposit-addresses, get-deposit-address): "응답의 deposit_address 필드가 null로 반환될 수 있습니다."
- V62. 4.9 `GET /v1/deposits/chance/coin`: fields, not real time. **CONFIRMED** (https://docs.upbit.com/kr/reference/available-deposit-information): "서비스 상태를 실시간으로 반영하지 않으며"
- V63. 4.9 `POST /v1/deposits/generate_coin_address` needs 입금하기. **CONFIRMED** (https://docs.upbit.com/kr/reference/create-deposit-address).
- V64. 4.10 `GET /v1/pockets`, main-pocket key only, type `main`/`user_spot_trading`. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-pockets: "메인포켓에서 발급한 API Key만 사용할 수 있으며"
- V65. 4.10 `GET /v1/pockets/assets?uuid=`, 404 `pocket_not_found`. **CONFIRMED, with a doc inconsistency.** The OpenAPI path is `/v1/pockets/assets`, but the flow diagram on https://docs.upbit.com/kr/reference/get-sub-pocket-balance shows `/v1/pockets/asset`. Use the OpenAPI path.
- V66. 4.10 `GET /v1/pockets/api_keys` (`uuids[]`, `include_expired`) needs 포켓관리 on a main-pocket key, and is the only way to read scopes. **CONFIRMED** (list-pocket-api-keys; `GET /v1/api_keys` has no scopes).
- V67. 4.10 `GET /v1/pockets/universal_transfers` has a 7-day window. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-universal-transfers: "전체 기간은 최대 7일을 초과할 수 없습니다." Default limit is 20, max 100.
- V68. 4.11 `GET /v1/status/wallet`: auth needed, no permission, enums, not real time. **CONFIRMED.** https://docs.upbit.com/kr/reference/get-service-status: "인증이 필요한 API입니다. 별도 권한은 필요하지 않습니다."
- V69. 4.12 `GET /v1/travel_rule/vasps` (입금조회) fields. **CONFIRMED** (https://docs.upbit.com/kr/reference/list-travelrule-vasps).
- V70. 4.12 Both verify calls are POST, need 입금하기, and are limited to 1 per 10 min per deposit. **CONFIRMED** (verify-travelrule-by-uuid, verify-travelrule-by-txid): "동일 입금건에 대해서는 10분당 최대 1회 호출할 수 있습니다."
- V71. 4.12 Successful verification releases a `TRAVEL_RULE_SUSPECTED` deposit. **CONFIRMED (paraphrase).** https://docs.upbit.com/kr/reference/travelrule-guide: "입금 반영을 재개할 수 있습니다"
- V72. 4.13 `withdraw_delayed_fiat` is an amount only. **CONFIRMED.** withdraws/chance: "출금 지연 제도로 인해 출금이 제한된 금액"
- V73. 4.13 24 h rule effective 2020-11-28 15:00. **CONFIRMED.** https://docs.upbit.com/kr/changelog/안내-24시간-디지털-자산-출금-지연제-도입-안내: "해당 입금액 가치의 디지털 자산은 24시간 경과 후 출금 가능합니다."
- V74. 4.13 72 h hold after the **first** KRW deposit. **UNVERIFIED.** The support page https://support.upbit.com/hc/ko/articles/900005806486 again returned 403. The official changelog mentions only 24 h. Only third-party blogs mention 72 h, and they disagree with each other.
- V75. Section 0 inference that `GET /v1/accounts` returns the key's own pocket. **UNVERIFIED.** pocket-overview says 자산조회 covers "해당 포켓의 보유자산 및 잔고 조회", which supports the inference but does not name the endpoint.

### Section 5. WebSocket
- V76. Endpoint `wss://api.upbit.com/websocket/v1/private` with JWT in the Authorization header. **CONFIRMED.** https://docs.upbit.com/kr/reference/websocket-guide (upd 2026-09-23).
- V77. `myOrder`: `state=trade`, fill fields, running totals, silent with no activity. **CONFIRMED.** https://docs.upbit.com/kr/reference/websocket-myorder: "주문 또는 체결이 없으면 데이터가 전송되지 않습니다." It also has a `prevented` state that the note omits.
- V78. `myAsset`: push on change only, first push delayed by minutes. **CONFIRMED.** https://docs.upbit.com/kr/reference/websocket-myasset: "초기 수분 동안 데이터 수신이 지연될 수 있습니다"
- V79. Required permission for the private streams not documented. **CONFIRMED (absence)** on all three pages.
- V80. Auth error `INVALID_AUTH`. **CONFIRMED** (websocket-guide).

### Section 6. Rate limits
- V81. Group table (quotation 10/s per IP; default 30, order 12, order-test 8, cancel-all 1 per 2 s per pocket; ws-connect 5/s IP or pocket; ws-message 5/s + 100/min per connection). **CONFIRMED** (rate-limits): "분당 최대 100회"
- V82. order 8 to 12/s from 2026-08-21, and per-minute REST limit gone. **CONFIRMED.** https://docs.upbit.com/kr/changelog/order-rate-limit-update: "분 단위 요청 제한은 더 이상 적용되지 않으며". The precise time is 21:00.
- V83. Origin header gives 1 per 10 s. **CONFIRMED** (rate-limits): "10초당 1회만 허용됩니다"
- V84. `Remaining-Req` example; `min` deprecated. **CONFIRMED** (rate-limits).
- V85. 429 and 418 messages. **CONFIRMED** (rest-api-guide): "API 호출 한도를 초과했습니다." and "과도한 요청으로 인해 요청 제한이 적용되었습니다."
- V86. 418 is per IP/pocket/connection, the response carries the block time, and repeat offences lengthen the block. **CONFIRMED on rate-limits, not on rest-api-guide**: "429 누적으로 일시 차단 (동일 IP·포켓·커넥션 단위)".
- V87. Stop the group's calls on 429. **CONFIRMED.** https://docs.upbit.com/kr/docs/rest-api-best-practice: "즉시 해당 그룹에 속한 API 호출을 중단하고"

### Section 7. Read-only vs trading
- V88. 7.1 Scope enforced at the server. **CONFIRMED as documented** (see V14 to V17). Not observed.
- V89. 7.2 "**Two** pairs share a path with a destructive verb." **WRONG (count).** The note then lists three, and all three are real: `GET`/`DELETE /v1/order` (cancel-order), `GET`/`DELETE /v1/orders/open` (batch-cancel-orders) and `GET`/`DELETE /v1/orders/uuids` (cancel-orders-by-ids). The GET-only rule stands.
- V90. 7.3 POST is used only by writes. **Partly CONFIRMED:** `POST /v1/orders`, `/v1/orders/test`, `/v1/deposits/generate_coin_address` and `/v1/travel_rule/deposit/{uuid,txid}` were checked. **UNVERIFIED:** the exact methods and paths for deposits/krw, withdraws, withdraws/krw and pocket transfers were not re-fetched.
- V91. 7.4 "Rate-limit groups also differ: `default` vs `order*`." **WRONG as a read/write separator.** Single and by-id cancels are trading writes but sit in **`default`**. cancel-order and cancel-orders-by-ids: "[default 그룹] 내에서 요청 가능 횟수를 공유합니다". Only new order, test order and cancel-all are in `order*`. Do not use the group name to classify a call as read-only.
- V92. 7.6 Read-only key cannot use `POST /v1/orders/test`. **CONFIRMED.** https://docs.upbit.com/kr/reference/order-test: "[주문하기] 권한이 설정된 API Key를 사용해야 합니다."

### Section 8. Sandbox
- V93. No sandbox documented. **CONFIRMED (absence)** in llms.txt.
- V94. `/v1/orders/test`: no real order, 8/s, 403 `market_offline`, returned UUID not usable. **CONFIRMED** (order-test): "실제 주문을 생성하지 않고 주문 요청 형식과 주문 가능 여부를 검증합니다." Also: "주문 조회나 취소 요청에 사용할 수 없습니다."

### Section 9. Error codes
- V95. 401 rows: `invalid_query_payload`, `jwt_verification`, `expired_access_key`, `nonce_used`, `no_authorization_ip`, `no_authorization_token`. **CONFIRMED** (rest-api-guide). The `no_authorization_token` text is "인증 토큰이 요청에 포함되지 않았습니다."
- V96. 404 row cited to rest-api-guide. **CONFIRMED, wrong attribution in part.** rest-api-guide lists only `pocket_not_found` and `currency_not_found`. `order_not_found`, `withdraw_not_found` and `deposit_not_found` come from get-order, get-withdrawal and get-deposit.
- V97. WS row lists `TOO_MANY_REQUEST`. **WRONG per current docs.** It is not in rest-api-guide, websocket-guide or rate-limits. The websocket-guide error list is `INVALID_AUTH`, `WRONG_FORMAT`, `NO_TICKET`, `NO_TYPE`, `NO_CODES`, `INVALID_PARAM`. WS rate-limit errors are deferred to rate-limits (418/429).
- V98. Error body; `name` is a string in Exchange and an integer in Quotation; `invalid_access_key` absent. **CONFIRMED** (rest-api-guide): "문자열 형식의 `name` 값을 반환합니다."

### Section 10. Open questions after verification
- V99. Q3 (query_hash encoding): partly resolved. The doc rule and the Python example both use the **unencoded** string, while the Java and Node examples are the outliers. The official SDK repo https://github.com/upbit-official/upbit-sdk-python exists, but its signing code was not read. Status: UNVERIFIED against the SDK.
- V100. Q1, Q2, Q5, Q6, Q7, Q8, Q9: still open (see V31, V75, V79, V74, V50, V4, V28).

# Part 6 of 6. Venue research: OKX, with its Verification section

# OKX API v5: read-only account inquiry (for TRADEGEN E1)

This is documentation research only. No key was created or used, and no request was signed.

## Sources and versions

| Source | What it is | Date / version seen |
|---|---|---|
| https://www.okx.com/docs-v5/en/ | Official API v5 guide. It is one long page; links below use its section anchors. | Fetched 2026-10-24. The page shows no version number. The newest changelog entry is 2026-09-30. |
| https://www.okx.com/docs-v5/log_en/ | Official changelog | Newest dated entry 2026-09-30. The "Upcoming Changes" items were last updated 2026-10-16. |
| https://www.okx.com/help/terms-of-service | Official Terms of Service | "Last Updated: 22 October 2026" |
| https://www.okx.com/help/risk-compliance-disclosure | Official Risk and Compliance Disclosure (Section 3 is the list of restricted jurisdictions) | "Last Updated: 8 July 2026" |
| Third-party news (labelled where cited) | Korean regulatory context | Dated where cited |

How the docs were read: WebFetch cuts the docs page off at about 400k of its 2.1M characters. So the raw HTML (5.3 MB) was saved to the scratchpad and parsed locally with a stdlib HTML parser. Every endpoint fact below comes from that copy of the official page, fetched 2026-10-24.

---

## 1. Authentication and key scopes

- **Three secrets per key.** The secrets are the API key, the secret key and the passphrase. "We cannot recover the Passphrase if you have lost it." ([#overview-api-key-creation-generating-an-api-key](https://www.okx.com/docs-v5/en/#overview-api-key-creation-generating-an-api-key))
- **Three permissions, combinable:** "One or more permission can be assigned to any key." ([#overview-api-key-creation-api-key-permissions](https://www.okx.com/docs-v5/en/#overview-api-key-creation-api-key-permissions))
  - Read: "Can request and view account info such as bills and order history"
  - Trade: "Can place and cancel orders, funding transfer, make settings"
  - Withdraw: "Can make withdrawals"
  - Note that funds transfer and account settings (for example, account mode or auto-loan) come under **Trade**, not Read. So a Read-only key cannot change the account mode or turn borrowing on.
- **Keys are created in the website UI only**, through "Please refer to my api page" (link `/account/my-api`). The docs describe no REST endpoint that creates a key for the master account. Sub-account key endpoints exist under Sub-account (`#sub-account-rest-api-create-an-api-key-for-a-sub-account`). Their `perm` values include "read_only: Read only".
- **Self-introspection of the key in use.** `GET /api/v5/account/config` returns:
  - `perm`: "The permission of the current requesting API key or Access token". Values are `read_only`, `trade`, `withdraw`, comma-separated, for example `"read_only,withdraw,trade"`.
  - `ip`: "It is an empty string "" if there is no IP bonded."
  - `label`: the API key note.
  ([#trading-account-rest-api-get-account-configuration](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-account-configuration))
  - **Use for E1:** a startup self-check can refuse to run unless `perm == "read_only"` and `ip` is non-empty.
- **Is a Read-only key rejected by the server on trade endpoints?**
  - The docs **do not state this explicitly** for each endpoint.
  - Per-endpoint "Permission:" lines appear only on 4 newer endpoints (the GLP v2 endpoints and Flexible Loan e-mode info, all "Permission: Read"). The classic endpoints have no such line.
  - The server-side refusal is implied by error code **50120**: "This API key doesn't have permission to use this function" (HTTP 200). Also 50030: "You don't have permission to use this API endpoint". ([#error-code-rest-api-public](https://www.okx.com/docs-v5/en/#error-code-rest-api-public))
  - Status: implied, not documented as a rule. See the open questions.

## 2. Signature rules and lifetimes

- **Required headers on every private REST call:** `OK-ACCESS-KEY`, `OK-ACCESS-SIGN`, `OK-ACCESS-TIMESTAMP`, `OK-ACCESS-PASSPHRASE`. ([#overview-rest-authentication-making-requests](https://www.okx.com/docs-v5/en/#overview-rest-authentication-making-requests))
- **Timestamp:** "ISO 8601 UTC format with millisecond precision, e.g. 2020-12-08T09:08:57.715Z".
- **Timestamp window: 30 seconds.** "differs from server time by more than 30 seconds (error 50102)". The docs advise syncing with `GET /api/v5/public/time`, and say "Always use UTC".
- **Signature:** "Create a pre-hash string of timestamp + method + requestPath + body". The pre-hash is signed with HMAC SHA256 using the SecretKey, then Base64-encoded. ([#overview-rest-authentication-signature](https://www.okx.com/docs-v5/en/#overview-rest-authentication-signature))
  - Method must be uppercase.
  - "`GET` request parameters are counted as requestpath, not body". The query string is part of what gets signed, for example `/api/v5/account/balance?ccy=BTC`.
  - Body is empty for GET.
- **Lifetimes:** there are no session tokens and no refresh. Each request is signed on its own and is valid only inside the 30-second window. The key itself does not expire, except under the inactivity rule in section 3.
- **WebSocket login** (`op: login`) ([#overview-websocket-login](https://www.okx.com/docs-v5/en/#overview-websocket-login)):
  - The timestamp is in **seconds**: "Unix Epoch time, the unit is seconds".
  - Pre-hash is `timestamp + 'GET' + '/users/self/verify'`.
  - "The request will expire 30 seconds after the timestamp."
  - Login failure is code 60009, "Login failed."
- **Optional `expTime` header** (request deadline in milliseconds). It applies only to place and amend order endpoints, so E1 does not need it. ([#overview-transaction-timeouts-rest-api](https://www.okx.com/docs-v5/en/#overview-transaction-timeouts-rest-api))

## 3. IP binding

([#overview-api-key-creation-api-key-security](https://www.okx.com/docs-v5/en/#overview-api-key-creation-api-key-security))

- "we strongly recommend clients linked the API key to IP addresses". It is recommended, not required, in general.
- "Each API key can bind up to 20 IP addresses". Formats are IPv4, IPv6 and network segments.
- **Inactivity expiry:**
  - Applies to keys "not linked to an IP address and have `trade` or `withdraw` permissions".
  - Such keys "will expire after 14 days of inactivity."
  - "The API key of demo trading will not expire".
- **A Read-only key without IP binding is not covered by the 14-day rule**, as the sentence is written. The docs say nothing more about Read-only keys without IP.
- **What counts as "used":**
  - Only calling "an API that requires API key authentication".
  - On WebSocket, "only operation of logging in" counts.
- Usage records for unbound trade/withdraw keys are visible in the Security Center (web).
- **Related errors:**
  - 50110 (HTTP 401): "Your IP {param0} is not included in your API key's IP whitelist."
  - 50035 (HTTP 403): "This endpoint requires that APIKey must be bound to IP".
  - 50121: "You can't access our services through the IP address ({param0})".
  - Which endpoints raise 50035 is **not documented**.

## 4. Rate limits

General rules ([#overview-rate-limits](https://www.okx.com/docs-v5/en/#overview-rate-limits)):

- "Private REST rate limits are based on User ID (sub-accounts have individual User IDs)."
- "Public unauthenticated REST rate limits are based on IP address."
- WebSocket login and subscribe limits are per connection.
- Rejection is error **50011**: "Rate limit reached...". The error table lists 50011 twice: HTTP 200 "Rate limit reached" and HTTP 429 "Too Many Requests".
- 50013 (HTTP 429): "Systems are busy. Please try again later."
- 50061 is the per-sub-account order-rate cap (1000 order requests per 2 s). It applies to placing and amending orders only, so it does not affect E1.

Per-endpoint limits, quoted from each endpoint's "Rate Limit" and "Rate limit rule" headings:

| Endpoint | Limit | Rule |
|---|---|---|
| GET /api/v5/account/balance | 10 requests per 2 seconds | User ID |
| GET /api/v5/account/positions | 10 requests per 2 seconds | User ID |
| GET /api/v5/account/config | 5 requests per 2 seconds | User ID |
| GET /api/v5/account/instruments | 20 requests per 2 seconds | User ID + Instrument Type |
| GET /api/v5/account/bills | 5 requests per second | User ID |
| GET /api/v5/trade/orders-pending | 60 requests per 2 seconds | User ID |
| GET /api/v5/trade/orders-history (7 days) | 40 requests per 2 seconds | User ID |
| GET /api/v5/trade/orders-history-archive (3 months) | 20 requests per 2 seconds | User ID |
| GET /api/v5/trade/fills (3 days) | 60 requests per 2 seconds | User ID |
| GET /api/v5/trade/fills-history (3 months) | 10 requests per 2 seconds | User ID |
| GET /api/v5/asset/currencies | 6 requests per second | User ID |
| GET /api/v5/asset/balances | 6 requests per second | User ID |
| GET /api/v5/asset/non-tradable-assets | 6 requests per second | User ID |
| GET /api/v5/asset/asset-valuation | 1 request per second | User ID |
| GET /api/v5/asset/deposit-address | 6 requests per second | User ID |
| GET /api/v5/asset/deposit-history | 6 requests per second | User ID |
| GET /api/v5/asset/withdrawal-history | 6 requests per second | User ID |
| GET /api/v5/asset/deposit-withdraw-status | 1 request per 2 seconds | User ID |
| GET /api/v5/finance/savings/balance (Simple Earn) | 6 requests per second | User ID |
| GET /api/v5/system/status | 1 request per 5 seconds | rule not stated |

WebSocket limits ([#overview-websocket-connect](https://www.okx.com/docs-v5/en/#overview-websocket-connect), [#overview-websocket-connection-count-limit](https://www.okx.com/docs-v5/en/#overview-websocket-connection-count-limit)):

- "Connection limit: 3 requests per second (based on IP)".
- Subscribe, unsubscribe and login requests are limited to "480 times per hour" per connection.
- 30 connections per private channel per sub-account. This covers the orders, account and positions channels, among others.
- The connection drops after 30 s without data, so the client should send `ping` and expect `pong`.

## 5. Read-only endpoints for E1

All endpoints below are private (signed) GETs on `https://openapi.okx.com`.

- That is the production REST base URL in the docs ([#overview-production-trading-services](https://www.okx.com/docs-v5/en/#overview-production-trading-services)).
- The 2026-05-20 changelog says `www.okx.com` "will continue to work and will not be deprecated".
- Regional domains: US/AU users use `us.okx.com` and EU users use `eea.okx.com`. The docs say "Using openapi.okx.com will not work for the regions below." A Korean account would be on the global entity, but that is **not documented** for Korea specifically.
- All numbers are returned as strings.

### 5.1 Trading account balance: GET /api/v5/account/balance
([#trading-account-rest-api-get-balance](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance))

- **Params:**
  - `ccy` (optional). Up to 20 currencies, comma-separated.
- **Account-level fields:**
  - `totalEq` ("Total account assets denominated in USD")
  - `uTime`
  - `adjEq`, `imr`, `mmr`, `mgnRatio`, `borrowFroz`, `notionalUsd`, `notionalUsdForBorrow`, `upl` (margin modes only; "" when not applicable)
- **Per currency (`details[]`):**
  - Holdings: `ccy`, `eq`, `cashBal`, `availBal`, `frozenBal`, `ordFrozen`, `eqUsd`, `uTime`
  - Spot cost basis: `spotBal`, `openAvgPx`, `accAvgPx`, `spotUpl`, `totalPnl`
  - **Borrowing and lending indicators:**
    - `liab` ("Liabilities of currency"; Spot mode, Multi-currency and PM)
    - `crossLiab`, `interest` ("Accrued interest of currency"), `maxLoan`, `twap` (forced-repayment risk 0–5), `frpType`
    - `autoLendStatus` (`unsupported`, `off`, `pending`, `active`) and `autoLendMtAmt` (the auto-lend matched amount)
- **Notes:**
  - "The currency details will not be returned when cashBal and eq is both 0."
  - "" is returned for fields that do not apply to the current account level.

### 5.2 Positions: GET /api/v5/account/positions
([#trading-account-rest-api-get-positions](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-positions))

- **Params:** all optional.
  - `instType`: MARGIN, SWAP, FUTURES, OPTION or EVENTS. SPOT is not a position type.
  - `instId`: up to 10.
  - `posId`: up to 20.
- **Fields:** `instType`, `mgnMode` (cross/isolated), `posId`, `posSide`, `pos`, `availPos`, `avgPx`, `upl`, `lever`, `liqPx`, `liab` ("only applicable to MARGIN"), `liabCcy`, `interest`, `cTime`, `uTime`.
- **Use for E1:** with spot-only holdings this should return an empty list. Any row means margin or derivatives exposure.

### 5.3 Account configuration: GET /api/v5/account/config
([#trading-account-rest-api-get-account-configuration](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-account-configuration))

- **Params:** none.
- **Fields relevant to "no margin, no lending":**
  - `acctLv`: "1: Spot mode / 2: Futures mode / 3: Multi-currency margin / 4: Portfolio margin".
  - `enableSpotBorrow`: "Whether borrow is allowed or not in Spot mode" (true/false).
  - `autoLoan`: "Whether to borrow coins automatically".
  - `spotBorrowAutoRepay`.
  - `mgnIsoMode` and `ctIsoMode` (isolated margin settings).
  - `opAuth`: "Whether the optional trading was activated" (options).
- **Key and identity fields:**
  - `perm`, `ip`, `label` (see sections 1 and 3).
  - `kycLv`: "0: No verification … 3: level 3 completed".
  - `uid` and `mainUid` (whether this is the main account or a sub-account).
  - `type` (0 is the main account).
- **Answer to the brief:**
  - Yes, this endpoint can show whether margin or borrowing is possible.
  - A spot-only, no-borrow account should read `acctLv == "1"` and `enableSpotBorrow == false`. `autoLoan` should be false.
  - The docs do not say whether `autoLoan` applies in Spot mode or only in the margin modes.
  - Spot mode can still borrow when `enableSpotBorrow` is true. The docs use the phrase "Spot mode (enabled borrow)" in several places.
- **Changing the account mode:**
  - Done with `POST /api/v5/account/set-account-level`, which is a write action and so needs a Trade key.
  - Overview: "You need to set on the Web/App for the first set of every account mode." ([#overview-account-mode](https://www.okx.com/docs-v5/en/#overview-account-mode))

### 5.4 Account-level eligibility: GET /api/v5/account/instruments
([#trading-account-rest-api-get-instruments](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-instruments))

- "Retrieve available instruments info of current account."
- **Params:**
  - `instType` (required): SPOT, MARGIN, SWAP, FUTURES, OPTION or EVENTS.
  - `instFamily` (conditional).
  - `instId` (optional).
- **Fields:** `instId`, `baseCcy`, `quoteCcy`, `state` (live, suspend, …), `minSz`, `lotSz`, `tickSz`, `maxMktAmt`, `lever`, and so on.
- **Use for eligibility:** this is the closest thing OKX documents to a "product eligibility answer". Calling it per `instType` shows what the account may trade.
- What a Korea-resident account gets back for SWAP, FUTURES or MARGIN (an empty list or an error) is **not documented**.

### 5.5 Open orders: GET /api/v5/trade/orders-pending
([#order-book-trading-trade-get-order-list](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-list))

- "Retrieve all incomplete orders under the current account."
- **Params:** all optional.
  - `instType`, `instFamily`, `instId`, `ordType`, `state` (live, partially_filled).
  - `after` and `before` (ordId cursors).
  - `limit`: max 100, default 100.
- **Fields:** `ordId`, `clOrdId`, `instId`, `side`, `ordType`, `px`, `sz`, `accFillSz`, `avgPx`, `state`, `fee`, `feeCcy`, `cTime`, `uTime`.
  - `tdMode` ("Trade mode"). The value `cash` means non-margin spot; `cross` and `isolated` are margin. Use it to check that no order uses margin.
- This endpoint lists order-book orders only. Algo orders are a separate list: `GET /api/v5/trade/orders-algo-pending` (`#order-book-trading-algo-trading-get-algo-order-list`).

### 5.6 Order history: GET /api/v5/trade/orders-history (7 d) and /orders-history-archive (3 months)
([#order-book-trading-trade-get-order-history-last-7-days](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-history-last-7-days), [#order-book-trading-trade-get-order-history-last-3-months](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-history-last-3-months))

- **Params:**
  - `instType` is **required** ("yes").
  - Optional: `instId`, `ordType`, `state` (canceled, filled, mmp_canceled).
  - Cursors: `after` and `before`. Time filters on cTime: `begin` and `end` (ms).
  - `limit` up to 100.
- **Caveat:** "The incomplete orders that have been canceled are only reserved for 2 hours."
- **Fields:** the same order fields as 5.5.

### 5.7 Fills: GET /api/v5/trade/fills (3 d) and /fills-history (3 months)
([#order-book-trading-trade-get-transaction-details-last-3-days](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-transaction-details-last-3-days), [#order-book-trading-trade-get-transaction-details-last-3-months](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-transaction-details-last-3-months))

- **Params:**
  - `instType` is optional for `/fills` and **required** for `/fills-history`.
  - Optional: `instId`, `ordId`, `subType`.
  - Cursors: `after` and `before` are **billId** cursors. `begin` and `end` filter on ts.
  - `limit` up to 100.
- **Fields:** `tradeId`, `ordId`, `clOrdId`, `billId`, `instId`, `side`, `fillPx`, `fillSz`, `execType` (T/M), `fee` (negative means a fee was charged), `feeCcy`, `feeRate` (SPOT/MARGIN only), `ts`, `fillTime`.
- Longer ledger: `GET /api/v5/account/bills` covers 7 d and `/bills-archive` covers 3 months. Fields include `balChg`, `bal`, `type`, `subType`, `mgnMode` (`cash` for non-margin), `interest`. Bills also record transfers and interest.

### 5.8 Funding account balance: GET /api/v5/asset/balances
([#funding-account-rest-api-get-balance](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-balance))

- **Params:** `ccy` (optional, up to 20).
- **Fields:** `ccy`, `bal`, `frozenBal`, `availBal`.
- The funding account is separate from the trading account. E1 must sum both.
- `GET /api/v5/asset/asset-valuation` gives totals for each account: `funding`, `trading`, `earn`, `totalBal`. Its `ccy` parameter accepts **KRW** as the valuation unit.

### 5.9 Lending check (Simple Earn): GET /api/v5/finance/savings/balance
([#financial-product-simple-earn-flexible-get-saving-balance](https://www.okx.com/docs-v5/en/#financial-product-simple-earn-flexible-get-saving-balance))

- **Fields:** `ccy`, `amt`, `earnings`, `rate` ("Minimum annual lending rate"), `loanAmt` ("Lending amount"), `pendingAmt`.
- **Use for E1:** this is the read-only way to confirm that no assets are lent out. Use it together with `autoLendStatus` from 5.1.

### 5.10 Currencies, chains and withdrawal minimums: GET /api/v5/asset/currencies
([#funding-account-rest-api-get-currencies](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-currencies))

- "Retrieve a list of all currencies available which are related to the current account's KYC entity". This makes it an account-specific eligibility signal.
- **Params:** `ccy` (optional).
- **Fields:**
  - `chain` ("Chain name, e.g. USDT-ERC20, USDT-TRC20")
  - `canDep`, `canWd`, `canInternal`
  - `minDep`, `minWd` ("minimum on-chain withdrawal amount"), `maxWd`, `wdTickSz`
  - `fee` ("The fixed withdrawal fee"). `minFee`/`maxFee` are deprecated.
  - `wdQuota` and `usedWdQuota` (24-hour withdrawal limit and amount used, in USD)
  - `needTag`, `mainNet`, `ctAddr`, `minDepArrivalConfirm`, `minWdUnlockConfirm`, `depQuotaFixed`

### 5.11 Deposit address: GET /api/v5/asset/deposit-address
([#funding-account-rest-api-get-deposit-address](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-deposit-address))

- "Retrieve the deposit addresses of currencies, including previously-used addresses."
- **Params:** `ccy` (**required**).
- **Fields:**
  - `addr`, `tag`, `memo`, `pmtId`, `addrEx`, `ccy`
  - `chain` (for example USDT-TRC20)
  - `to` ("6: Funding account 18: Trading account")
  - `selected`, `ctAddr`, `verifiedName`

### 5.12 Deposit history: GET /api/v5/asset/deposit-history
([#funding-account-rest-api-get-deposit-history](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-deposit-history))

- **Params:** all optional.
  - `ccy`, `depId`, `fromWdId`, `txId`.
  - `type`: 3 is internal transfer, 4 is on-chain.
  - `state`: 0 waiting, 1 credited, 2 successful, 8 pending, and others.
  - `after` and `before` are **ts** cursors in ms.
  - `limit` up to 100. "The 100 most recent records are returned by default."
- **Fields:** `ccy`, `chain`, `amt`, `from`, `to`, `txId`, `ts`, `state`, `depId`, `actualDepBlkConfirm`.

### 5.13 Withdrawal history: GET /api/v5/asset/withdrawal-history
([#funding-account-rest-api-get-withdrawal-history](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-withdrawal-history))

- **Params:** all optional.
  - `ccy`, `wdId`, `clientId`, `txId`, `type` (3 or 4), `state`.
  - `after` and `before` (ts cursors), `limit` up to 100.
- **Fields:** `ccy`, `chain`, `amt`, `ts`, `to` ("Receiving address"), `toAddrType`, `tag`, `memo`, `txId`, `fee`, `feeCcy`, `state`, `wdId`, `nonTradableAsset`, `note`.
- Per-transaction status: `GET /api/v5/asset/deposit-withdraw-status` (1 request per 2 s). Pass `wdId`, or pass `txId` with `ccy`, `to` and `chain`. It returns `estCompleteTime` and `state`.

### 5.14 Withdrawal address book / whitelist: **no list endpoint documented**

- The withdrawal endpoint says: "The API can only make withdrawal to verified addresses/account". It adds: "verified addresses can be set by WEB/APP." ([#funding-account-rest-api-withdrawal](https://www.okx.com/docs-v5/en/#funding-account-rest-api-withdrawal))
- The related error codes are 58207 ("Withdrawal address isn't on the verified address list.") and 58203 ("Please add a withdrawal address.").
- A search of the full page for "address book", "whitelist", "verified address" and "allowlist" found no endpoint that reads the list of verified addresses.
- **What E1 can show instead:** past destinations, from the `to` field of withdrawal history.

### 5.15 System status (public): GET /api/v5/system/status
([#status-get-status](https://www.okx.com/docs-v5/en/#status-get-status))

- Returns maintenance events (`state`, `begin`, `end`, `serviceType`).
- `env` says which environment an event affects: "1: Production Trading / 2: Demo Trading".
- Useful for E1 to tell an outage apart from an auth failure.

### 5.16 WebSocket alternatives (read-only push)

- Private channels: account, positions, balance-and-position, orders, plus deposit-info and withdrawal-info on the business URL.
- They need `login` first. Login counts as "using" the key.
- Whether a Read-only key may log in and subscribe is **not documented explicitly**. It is presumably allowed, since these channels only read data.

## 6. Read-only vs trading at the protocol level

- **The same signing scheme, headers, host and base path apply to read and write calls.** There is no separate read-only host, token type or header. Read calls are GETs and writes are mostly POSTs, but the protocol does not enforce read-only behaviour.
- **The only difference is the key's permission set**, enforced on the server:
  - Read covers "view account info"; Trade covers orders, "funding transfer, make settings"; Withdraw covers withdrawals.
  - A missing permission produces 50120 ("doesn't have permission to use this function"). The docs do not show a per-endpoint mapping.
- **Client-side guards E1 can add:**
  - Startup: check `GET /account/config.perm == "read_only"`, and refuse to start otherwise.
  - Code: allow only GET in the client and keep a path allow-list.
  - Note that `GET /api/v5/account/balance` and `POST /api/v5/trade/order` look the same apart from method and path.
- **IP binding is optional for a Read-only key.** The 14-day inactivity expiry covers only keys with trade or withdraw permission and no IP. So a Read-only key without IP stays valid. That is convenient, but a leaked key is then usable from anywhere, though only to read.

## 7. Sandbox / demo environment

([#overview-demo-trading-services](https://www.okx.com/docs-v5/en/#overview-demo-trading-services))

- **Demo REST base URL:** `https://openapi.okx.com`, the same host as production. Demo WebSocket hosts are `wss://wspap.okx.com/ws/v5/{public,private,business}`.
- **Header:** "`x-simulated-trading: 1` needs to be added to the header of the Demo Trading request."
- **Demo keys:**
  - Demo keys are separate. They are created via "Trade —> Demo Trading —> Personal Center —> Demo Trading API".
  - Error 50101 is "APIKey does not match current environment." That is what happens when a key is used against the wrong environment (demo vs live).
  - "The API key of demo trading will not expire".
- **Limits:**
  - "some functions are not supported, such as withdraw,deposit,purchase/redemption".
  - Error 50038 is "This feature is unavailable in demo trading". So deposit-address and deposit or withdrawal history may not work on demo. Exactly which endpoints fail is **not documented**.
- **Official Python SDK** (linked from the docs as "Python SDK"): the samples use `flag = "1" # Production trading:0 , demo trading:1`.
- **WebSocket port 8443** (changelog "Upcoming Changes", updated 2026-10-16): public-internet connections on `:8443` stop on 2026-10-31. Use URLs without the port.

## 8. Error codes for auth and rate limits

([#error-code-rest-api-public](https://www.okx.com/docs-v5/en/#error-code-rest-api-public))

| Code | HTTP | Message (abridged) |
|---|---|---|
| 50011 | 200 / 429 | Rate limit reached / Too Many Requests |
| 50013 | 429 | Systems are busy. Please try again later. |
| 50030 | 200 | You don't have permission to use this API endpoint |
| 50035 | 403 | This endpoint requires that APIKey must be bound to IP |
| 50038 | 200 | This feature is unavailable in demo trading |
| 50051 | 200 | Due to compliance restrictions in your country or region… |
| 50100 | 400 | API frozen, please contact customer service. |
| 50101 | 401 | APIKey does not match current environment. |
| 50102 | 401 | Timestamp request expired. |
| 50103 / 50104 / 50106 / 50107 | 401 | Header OK-ACCESS-KEY / PASSPHRASE / SIGN / TIMESTAMP cannot be empty |
| 50105 | 401 | Request header "OK-ACCESS-PASSPHRASE" incorrect. |
| 50110 | 401 | Your IP … is not included in your API key's IP whitelist. |
| 50111 | 401 | Invalid OK-ACCESS-KEY. |
| 50112 | 401 | Invalid OK-ACCESS-TIMESTAMP. |
| 50113 | 401 | Invalid signature. |
| 50114 | 401 | Invalid authorization. |
| 50119 | 200 | API key doesn't exist |
| 50120 | 200 | This API key doesn't have permission to use this function |
| 50121 | 200 | You can't access our services through the IP address (…) |
| 51024 | 200 | Several variants, e.g. "trading is not available in your verified country" |
| 60009 (WS) | – | Login failed. |

- Many business errors return **HTTP 200** with a non-zero `code`. A client must check `code`, not just the HTTP status.
- "code and msg represent the request result … when the return data has code". Batch endpoints use `sCode`/`sMsg` instead. ([#overview-general-info](https://www.okx.com/docs-v5/en/#overview-general-info))

## 9. Korea-specific status (as of 2026-10-24)

**Official OKX sources:**

- **The Risk and Compliance Disclosure** (last updated 8 July 2026) lists South Korea among the jurisdictions where OKX "may restrict services". The restriction is "specifically regarding our derivatives-related and P2P services". ([risk-compliance-disclosure, Section 3](https://www.okx.com/help/risk-compliance-disclosure))
  - South Korea is **not** on the full "Restricted Locations" list there. Only North Korea is.
  - So, officially, spot, deposits and withdrawals are not listed as restricted for South Korea, while derivatives and P2P are.
- **The Terms of Service** (last updated 22 October 2026), clause 2.2: "We may not make all of the Services available in all markets". The complete list is deferred to the disclosure above. ([terms-of-service](https://www.okx.com/help/terms-of-service))
- **The API docs** have no Korea-specific text. The compliance hooks relevant to Korea are:
  - `GET /asset/currencies` is scoped to the "current account's KYC entity".
  - `GET /account/instruments` returns the "available instruments info of current account".
  - Error 51024 has a variant "This product isn't available in your country or region…".
  - Error 50051: "Due to compliance restrictions in your country or region, you cannot use this feature."
  - The account-mode precheck can return `compliance_restriction`: "margin trading services are unavailable".
  - What a Korean account actually gets back from these is **not documented**.
- **The API docs say nothing about restricting API access** (as opposed to products) for Korean residents.

**Third-party reports (not OKX, not regulators):**

- **Cryptonomist, 2026-07-28** ([link](https://en.cryptonomist.ch/2026/07/28/south-korea-crypto-app-ban-okx-return/)):
  - The OKX Android app was missing from the Korean Google Play Store from about 24 July and back by 28 July 2026. The reported cause was unregistered-VASP status under Google's own policy.
  - The article says web access was not affected.
- **Blockmedia** ([link](https://www.blockmedia.co.kr/archives/1032177)) reported that Google Play would restrict apps of overseas exchanges not reported to the FIU from 28 January 2026. It said OKX is not on the FIU-registered list. Third party, and written as a forecast.
- **Asiae, 2026-09-23** ([link](https://core.asiae.co.kr/article/2026092214243195647)) reported that KoFIU and the media-communications review commission agreed to block unregistered overseas exchange sites that serve Korean residents. OKX is not named. Third party.
- **SBS Biz** ([link](https://biz.sbs.co.kr/amp/article/20000339576)) reported an earlier block of 27 unregistered VASP sites, including KuCoin and MEXC. OKX was not listed. Third party; the article's date was not confirmed.
- **The Block** ([link](https://www.theblock.co/post/276404/okx-south-korea-probe)) reported a 2024 complaint about OKX operating in Korea without registration. Third party, older background.

**Bottom line for TRADEGEN:**

- OKX is **not a Korean-registered VASP**. Officially, derivatives and P2P may be restricted for Korea.
- A future Korean site block could cut off web and API access with no API-level notice. Treat this as a live venue risk and show it to the owner.
- The legality of using OKX is a question for the project's legal note, not this doc.

## 10. Open questions (verify before relying on them)

1. **Read-only enforcement:** does a Read-only key calling `POST /api/v5/trade/order` get 50120, 50030 or something else? The docs do not map this per endpoint. It could be verified on **demo** with a demo Read-only key, without real money, but only if the owner allows that. No key has been used.
2. **Read-only key on WebSocket:** can it `login` and subscribe to the account, orders and positions channels? Not documented.
3. **Demo coverage:** do `deposit-address`, `deposit-history`, `withdrawal-history` and `asset/currencies` work on demo, or return 50038? Not documented.
4. **Korean account behaviour:** for a Korea-KYC account, what do `GET /account/instruments?instType=SWAP|FUTURES|MARGIN` and `GET /asset/currencies` return: an empty list, error 51024, or error 50051? Not documented.
5. **`autoLoan` in Spot mode:** does it have any effect when `acctLv == 1`, or does only `enableSpotBorrow` matter? The docs do not say. A conservative check requires both to be false.
6. **Which endpoints need IP binding (50035)?** Not documented. Read endpoints are presumably exempt.
7. **No API to list the verified withdrawal-address whitelist.** E1 can only show past destinations from withdrawal history. Confirm there is no hidden or undocumented endpoint (none found in the 2026-10-24 docs).
8. **Regional domain for Korean users:** the docs list special domains only for US/AU (`us.okx.com`) and EU (`eea.okx.com`). The assumption is that a Korean resident is on the global entity and uses `openapi.okx.com` or `www.okx.com`. Not stated for Korea.
9. **The OKX API Agreement** applies ("continued use constitutes acceptance"). Its terms were not reviewed here.

## Verification (skeptic)

An independent pass ran on 2026-10-24. Fresh copies of five official pages were downloaded and searched locally: the API docs page (5.28 MB HTML), the changelog, the ToS, the Risk and Compliance Disclosure, and the help-center API FAQ. No key was created and no request was signed. Every quote is under 15 words. "docs" means https://www.okx.com/docs-v5/en/ plus the anchor given. "FAQ" means https://www.okx.com/help/api-faq (shown as "Updated on Sep 28, 2026").

### Corrections that change E1 (read these first)

1. **WRONG (outdated): "three permissions".** The FAQ now lists three more permissions: Transfer, Loan and Earn. It says "Transfer: Allows the key to transfer funds between your accounts", and also "If your API Key previously had Trade permissions enabled, all three permissions" are switched on automatically. The API docs still list only Read, Trade and Withdraw, and the `perm` values in `account/config` are still documented as `read_only`, `trade` and `withdraw`.
   - **E1 impact:** `perm` may carry values that are not documented. The startup check must be the exact test `perm == "read_only"`, which fails closed on any extra value. It must never be a "contains read_only" test.
   - Whether a Read-only key can carry Transfer is **UNVERIFIED**. The FAQ says Transfer is "Available to all accounts".
2. **Read-only keys are refused for orders: now CONFIRMED (FAQ).** The FAQ says such a key "can retrieve account data but cannot place orders."
   - **The error code is UNVERIFIED, and probably not 50120.** The FAQ links missing Trade permission to **50123**, whose docs text is "This API Key does not have trading permission for the Crypto." (#error-code-rest-api-public). The FAQ gives this in a demo-trading context.
   - E1 should treat 50030, 50120 and 50123 all as permission refusals.
   - Supporting evidence that OKX assigns a permission to each endpoint, from the changelog for 2023-07-05: "Changed the request permission of Position builder from "Trade" to "Read"".
3. **UNVERIFIED (sources conflict): "A Read-only key without an IP is not covered by the 14-day rule".**
   - The docs sentence supports the claim.
   - The FAQ says "Only read-only API keys bound to an IP or specific permissions will not expire." That can be read as saying a Read-only key also needs an IP to avoid expiry.
   - The FAQ also says unbound trade or withdraw keys are "automatically deleted", not merely expired.
   - **Safer choice:** bind an IP to the E1 key anyway.
4. **Partly WRONG: "the docs do not say whether `autoLoan` applies in Spot mode"** (open question 5). The "Set auto loan" endpoint is "Only applicable to Multi-currency margin and Portfolio margin" (#trading-account-rest-api-set-auto-loan). It also says "The default is true".
   - **E1 impact:** in Spot mode, `enableSpotBorrow` is the setting that matters. Still require both to be false.
5. **Overclaim: Simple Earn is "the read-only way to confirm that no assets are lent out", and `account/config` shows "no borrowing".** The docs have other ways to lend, lock or borrow assets:
   - Flexible Loan, which is borrowing against collateral: `GET /api/v5/finance/flexible-loan/loan-info`. The docs call it a loan "without selling off their crypto".
   - On-chain earn: `/finance/staking-defi/orders-active`.
   - ETH and SOL staking: `/finance/staking-defi/{eth,sol}/balance`.
   - Dual investment: `/finance/sfp/dcd/order-status`.
   - OKUSD (`/finance/okusd/account`) and stable rewards (`/finance/stable-rewards/balance`).
   - The `earn` total in `asset/asset-valuation` is the aggregate cross-check. `account/config` does not cover Flexible Loan.
6. **Incomplete: `tdMode` values.** There is also `spot_isolated`, "only applicable to SPOT lead trading". E1 should accept `cash` only and reject every other value. It should not reject only `cross` and `isolated`.
7. **Nuance: "positions should return an empty list".** The docs say a row with zero size can appear: "a position with a position of 0 will be generated" (manual-transfer isolated mode). Treat a row with `pos == "0"` as a separate warning, not as live exposure.
8. **Missing: the `EVENTS` instType is "Event Contracts".** It appears in the positions, instruments and orders endpoints. `account/instruments` also has a `seriesId` parameter, which is required for EVENTS. Because the legal note hard-blocks prediction markets, E1 should flag any EVENTS row.
9. **Correction: `deposit-withdraw-status` with `txId` returns deposit status, not withdrawal status.** The docs say "Hash record of the deposit, use to retrieve deposit status". Withdrawal status needs `wdId`.
10. **Missing: a third regional domain.** The 2026-05-20 changelog entry also lists `tr.okx.com`. The FAQ says error 50119 often means the account's region and the domain don't match.
11. **Nuance (Korea):** the Disclosure's list of partly restricted places is introduced with "including but not limited to". So spot being absent from the list is not a guarantee.

### Claim-by-claim

| # | Claim in these notes | Verdict | Source and quote (under 15 words) |
|---|---|---|---|
| 1.1 | Three secrets per key; a lost passphrase cannot be recovered | CONFIRMED | docs #overview-api-key-creation-generating-an-api-key: "We cannot recover the Passphrase if you have lost it." |
| 1.2 | Read, Trade and Withdraw are the permissions, and they combine | CONFIRMED in the docs, but WRONG as a complete list | docs #overview-api-key-creation-api-key-permissions: "One or more permission can be assigned to any key." The FAQ adds Transfer, Loan and Earn (correction 1). |
| 1.3 | Trade covers orders, funds transfer and settings | CONFIRMED in the docs, superseded for transfer | docs: "Can place and cancel orders, funding transfer, make settings". The FAQ now makes Transfer its own permission. |
| 1.4 | Keys are made in the web UI; there is no REST endpoint for master-account keys | CONFIRMED | docs: "Create an API key on the website before signing any requests." A scan of every `GET /api/v5/users/*` endpoint found key endpoints only under `subaccount/apikey`. |
| 1.5 | Sub-account keys have the `perm` value `read_only` | CONFIRMED | docs #sub-account-rest-api-create-an-api-key-for-a-sub-account: "read_only: Read only" |
| 1.6 | `account/config` returns `perm`, `ip` and `label` | CONFIRMED | docs #trading-account-rest-api-get-account-configuration: "It is an empty string "" if there is no IP bonded." The `perm` description also says "or Access token" (OAuth tokens exist for broker apps), so "no tokens" is true only for self-signed keys. |
| 1.7 | Only 4 endpoints carry a "Permission:" line | CONFIRMED | There are exactly 4: GLP v2 overview, GLP v2 assessment details, GLP v2 performance history, and Flexible Loan e-mode info. |
| 1.8 | 50120 and 50030 are the permission errors | CONFIRMED, but incomplete | docs #error-code-rest-api-public: "This API key doesn't have permission to use this function". 50123 is missing (correction 2). |
| 1.9 | Server-side refusal is only implied | Now CONFIRMED by the FAQ; the error code is UNVERIFIED | FAQ: "can retrieve account data but cannot place orders." |
| 2.1 | The four OK-ACCESS-* headers | CONFIRMED | docs #overview-rest-authentication-making-requests: "All private REST requests must contain the following headers" |
| 2.2 | ISO ms UTC timestamp, 30 s window, error 50102 | CONFIRMED | docs: "differs from server time by more than 30 seconds (error 50102)" |
| 2.3 | Pre-hash, HMAC SHA256, Base64; uppercase method; query string is part of requestPath | CONFIRMED | docs #overview-rest-authentication-signature: "`GET` request parameters are counted as requestpath, not body" |
| 2.4 | No session tokens or refresh; each request is signed | CONFIRMED for API-key auth | The docs describe only per-request signing. See 1.6 for the OAuth caveat. |
| 2.5 | WS login uses seconds, `/users/self/verify` and a 30 s expiry; failure is 60009 | CONFIRMED | docs #overview-websocket-login: "The request will expire 30 seconds after the timestamp." |
| 2.6 | `expTime` applies only to place and amend | CONFIRMED | docs #overview-transaction-timeouts-rest-api covers place and amend (single and batch), plus "Place sub order under signal bot trading". |
| 3.1 | IP binding is recommended, not required | CONFIRMED | docs #overview-api-key-creation-api-key-security: "we strongly recommend clients linked the API key to IP addresses" |
| 3.2 | Up to 20 IPs per key, in IPv4, IPv6 or segment format | CONFIRMED | docs: "Each API key can bind up to 20 IP addresses" |
| 3.3 | 14-day expiry for unbound trade or withdraw keys; demo keys never expire | CONFIRMED | docs: "will expire after 14 days of inactivity." |
| 3.4 | A Read-only key without an IP is exempt | UNVERIFIED (conflict) | See correction 3. |
| 3.5 | Only authenticated calls count as use; on WS, only login counts | CONFIRMED | docs: "only operation of logging in will be considered to have used the API key" |
| 3.6 | Usage records are in the Security Center | CONFIRMED | docs: "get the usage records of the API key ... though Security Center." |
| 3.7 | 50110 (401), 50035 (403), 50121 | CONFIRMED | docs: "This endpoint requires that APIKey must be bound to IP" |
| 3.8 | Which endpoints raise 50035 is not documented | CONFIRMED that it is absent | The changelog does say IP linking is required for sub-account keys with trade or withdraw. That is one likely source of 50035. |
| 4.1 | Private limits are per User ID, public per IP, WS per connection | CONFIRMED | docs #overview-rate-limits: "Private REST rate limits are based on User ID" |
| 4.2 | 50011 appears twice (200 and 429); 50013 is 429 | CONFIRMED | docs #error-code-rest-api-public. Both 50011 rows are present. |
| 4.3 | 50061 is the sub-account order cap of 1000 per 2 s | CONFIRMED | docs #overview-rate-limits-sub-account-rate-limit: "a maximum of 1000 order requests per 2 seconds" |
| 4.4 | All 20 rows of the per-endpoint rate table | CONFIRMED | A script read each endpoint's "Rate Limit:" and "Rate limit rule:" headings. All 20 rows match. `bills-archive` (not in the table) is 5 requests per 2 s. |
| 4.5 | system/status is 1 request per 5 s, with no rule stated | CONFIRMED | docs #status-get-status: "Rate Limit: 1 request per 5 seconds" |
| 4.6 | WS limits: 3 connections per second per IP, 480 requests per hour, 30 connections per channel, 30 s idle timeout | CONFIRMED | docs #overview-websocket-connect: "limited to 480 times per hour." and #overview-websocket-connection-count-limit: "30 WebSocket connections per specific WebSocket channel per sub-account" |
| 5.0a | Production REST host is `openapi.okx.com`; `www.okx.com` is not deprecated | CONFIRMED | docs #overview-production-trading-services: "REST: https://openapi.okx.com". Changelog 2026-05-20: "will continue to work and will not be deprecated" |
| 5.0b | Regional domains are us and eea; nothing for Korea | CONFIRMED, but incomplete | docs: "Using openapi.okx.com will not work for the regions below." `tr.okx.com` is missing (correction 10). |
| 5.0c | All numbers are returned as strings | UNVERIFIED as a general rule | It matches the field tables (typed String), but no sentence in the docs states it. |
| 5.1 | Balance: `ccy` takes up to 20; the field set; `liab`, `twap` and `autoLendStatus`; the two notes | CONFIRMED | docs #trading-account-rest-api-get-balance: "not be returned when cashBal and eq is both 0." Also: "Applicable to Spot mode/Multi-currency margin/Portfolio margin" (`liab`). |
| 5.2 | Positions: parameters and limits; SPOT is not a position type; `liab` is MARGIN only | CONFIRMED | docs #trading-account-rest-api-get-positions: "Liabilities, only applicable to MARGIN." |
| 5.2b | With spot only, the result should be an empty list | Partly WRONG | See correction 7. |
| 5.3 | Config fields `acctLv`, `enableSpotBorrow`, `autoLoan`, `kycLv`, `uid`/`mainUid`, `type` | CONFIRMED | docs: "Whether borrow is allowed or not in Spot mode". `type` 0 is "Main account". |
| 5.3b | `autoLoan` in Spot mode is not documented | Partly WRONG | See correction 4. |
| 5.3c | "Spot mode (enabled borrow)" appears in several places | CONFIRMED (2 occurrences) | docs (borrow and interest sections) |
| 5.3d | Changing mode is `POST set-account-level`; the first switch must be done on Web/App | CONFIRMED | docs #overview-account-mode: "You need to set on the Web/App for the first set" |
| 5.4 | `account/instruments` lists what the account may trade; parameters | CONFIRMED, but incomplete | docs: "Retrieve available instruments info of current account." `seriesId` is missing; `state` also has the values rebase, post_only, preopen and test. |
| 5.4b | What a Korea account gets back | UNVERIFIED | Not in any official source. |
| 5.5 | `orders-pending`: parameters, limit of 100, `tdMode`; algo orders are listed separately | CONFIRMED, but `tdMode` is incomplete | docs: "Retrieve all incomplete orders under the current account." See correction 6. |
| 5.6 | Order history: `instType` is required; canceled orders are kept 2 hours | CONFIRMED | docs: "The incomplete orders that have been canceled are only reserved for 2 hours." |
| 5.7 | Fills: `billId` cursors; fee sign; `feeRate` only for SPOT/MARGIN; `execType` T/M; bills `mgnMode` is `cash` for non-margin | CONFIRMED | docs: "The trading fee deduction is negative". Also: "This field is returned for SPOT and MARGIN only" |
| 5.8 | Funding balance fields; `asset-valuation` accepts KRW and returns funding, trading, earn and totalBal | CONFIRMED | docs #funding-account-rest-api-get-account-asset-valuation lists "USD, CNY, JP, KRW, RUB, EUR". There is also a deprecated `classic` field. |
| 5.9 | Simple Earn balance fields | CONFIRMED | docs: `rate` is "Minimum annual lending rate configured by users" |
| 5.9b | This is "the read-only way" to confirm nothing is lent | Overclaim | See correction 5. |
| 5.10 | `asset/currencies` is scoped to the account's KYC entity; its fields | CONFIRMED | docs: "related to the current account's KYC entity." Also: `fee` is "The fixed withdrawal fee" |
| 5.11 | `deposit-address`: `ccy` is required; `to` is 6 or 18 | CONFIRMED | docs: "6: Funding account 18: Trading account" |
| 5.12 | Deposit history: parameters, ts cursors, 100 by default | CONFIRMED | docs: "The 100 most recent records are returned by default." |
| 5.13 | Withdrawal history fields; `to` is the receiving address | CONFIRMED | docs: "Receiving address" |
| 5.13b | The status endpoint takes `wdId`, or `txId` plus `ccy`, `to` and `chain` | CONFIRMED with a correction | See correction 9. |
| 5.14 | No endpoint lists the verified withdrawal addresses | CONFIRMED | docs #funding-account-rest-api-withdrawal: "verified addresses can be set by WEB/APP." A scan of every `GET /api/v5/asset/*` endpoint found no address list. 58203 and 58207 confirmed. |
| 5.15 | system/status: `env` 1 is production, 2 is demo | CONFIRMED | docs: "1: Production Trading" and "2: Demo Trading" |
| 5.16 | Private WS channels; deposit-info and withdrawal-info are on the business URL | CONFIRMED | docs #funding-account-websocket-deposit-info-channel: "/ws/v5/business (required login)" |
| 5.16b | A Read-only key may log in and subscribe on WS | UNVERIFIED | No official statement found. |
| 6 | Read and write calls use the same host, headers and signing; only the permission differs | CONFIRMED | Same sections as 2.1 to 2.3, and the FAQ statement in 1.9. |
| 7.1 | Demo uses the same REST host, `wspap` for WS, the `x-simulated-trading: 1` header, and separate keys | CONFIRMED | docs #overview-demo-trading-services: "`x-simulated-trading: 1` needs to be added to the header" |
| 7.2 | 50101 is a key used in the wrong environment; demo does not support withdraw or deposit; 50038 | CONFIRMED | docs: "some functions are not supported, such as withdraw,deposit,purchase/redemption" |
| 7.3 | The SDK flag is 0 for production, 1 for demo | CONFIRMED | This is in the docs' own code samples. The "Python SDK" link goes to pypi.org/project/python-okx. |
| 7.4 | Public-internet WS on port 8443 stops on 2026-10-31 | CONFIRMED | changelog #upcoming-changes: "Public internet: October 31, 2026" (last update October 16, 2026) |
| 8 | All 22 error rows: codes, HTTP status and text | CONFIRMED | docs #error-code-rest-api-public. Missing from the table: 50123 (permission) and 50115 (405, "Invalid request method."). |
| 8b | Batch endpoints use `sCode`/`sMsg` | CONFIRMED | docs #overview-general-info: "It is sCode and sMsg that represent the request result" |
| 9.1 | Disclosure (last updated 8 July 2026): South Korea is limited for derivatives and P2P only; North Korea is fully restricted | CONFIRMED, with a nuance | risk-compliance-disclosure: "South Korea (specifically regarding our derivatives-related and P2P services)". See correction 11. |
| 9.2 | ToS (last updated 22 October 2026), clause 2.2 | CONFIRMED | terms-of-service: "We may not make all of the Services available in all markets" |
| 9.3 | `compliance_restriction`, the 51024 country variant, and 50051 | CONFIRMED | docs: "due to compliance restrictions, margin trading services are unavailable" |
| 9.4 | Cryptonomist (2026-07-28): the app was off Korean Google Play from 24 to 28 July; web was unaffected | CONFIRMED (third party) | It is stated in the article. |
| 9.5 | Blockmedia: the Google Play restriction from 28 Jan, written as a forecast; OKX is not FIU-registered | CONFIRMED (third party) | Dated 2026-01-14. OKX is named among the unreported exchanges. |
| 9.6 | Asiae (2026-09-23): KoFIU and the review commission agreed to block | CONFIRMED with a nuance (third party) | The article says "corrective orders", with standards still to be finalized. OKX is not named. |
| 9.7 | SBS Biz and The Block items | UNVERIFIED | Not re-checked in this pass. |

### Status of the open questions after this pass

- **Q1:** partly answered. The refusal itself is confirmed by the FAQ. The exact code (50123 vs 50120 vs 50030) is still unverified.
- **Q5:** partly answered. Set-auto-loan applies only to MCM and PM.
- **Q2, Q3, Q4, Q6, Q8, Q9:** still open.
- **Q7:** confirmed that no list endpoint exists in the 2026-10-24 docs.
- **New questions:**
  - (a) How do the FAQ's Transfer, Loan and Earn permissions show up in `perm`? Can a Read-only key carry Transfer?
  - (b) Does an unbound Read-only key expire? The FAQ and the docs disagree.
```
