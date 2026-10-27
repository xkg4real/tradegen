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
