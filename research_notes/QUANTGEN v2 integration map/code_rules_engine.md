# code_rules_engine — map of `core/rules/*` and `core/engine/*` for the v2.0 build

Scope read completely: `core/rules/{__init__,model,store,validation}.py` (683 lines), `core/engine/{__init__,state,orders,evaluator,feed,runtime}.py` (1,465 lines), `tests/engine_acceptance.py` (1,398 lines), `tests/run_all.py`, `tests/flet_api_guard.py`; collaborators read for interfaces: `core/markets.py`, `core/calendars.py`, `config.py`, `main.py`, `ui/trading_page.py`, `ui/rules_page.py` (call sites).
Spec lines cited as `SPEC:n` = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md`; `R3:n` = `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/research_notes/R3_TF_neural_link.md`; `TASK-…` = `QUANTGEN_V2_TASKS.json`.
Environment verified 2026-10-05: Python 3.13.14, Flet 0.85.2, `python tests/run_all.py` last result file `qa/acceptance_results.json` = 266/266 PASS (engine 89, ficc 56, quant 53, cockpit 47, expansion 17, ui 4).

Three facts the build coordinator must hold before anything else:

1. **What exists is an operator price-trigger engine, not a portfolio engine.** One global state machine, one global in-memory order book of share-quantity orders, live intraday quotes on a 5 s loop. There is **no position ledger, no P&L, no NAV, no weights, no costs, no book id** anywhere in `core/rules` or `core/engine`. Every v2 item that reads "whole-book NAV" (hard stop, ladder, R-25) needs a ledger that does not exist.
2. **`Rule` (existing) ≠ "rule object" (SPEC §7.1).** Existing `Rule` = "when last price ≤ 68000, place a simulated BUY of 10 shares". v2 rule object = `{rule_id: "R-06", kind, output_range, exposure_basis, …}`. Same words (`Rule`, `rule_id`, `validate`, "rules store", "edit history"), disjoint semantics.
3. **Existing safety contract contradicts v2 per-book semantics on purpose-built, tested points** (manual acknowledge before any re-arm; mode never persisted; orders never fill themselves). v2 must be **additive beside** the existing classes, not a change to them, or tests `engine/test_02,03,04,18,78,84` fail.

---

## A. File by file

### A.1 `core/rules/__init__.py` (11 lines)
Re-exports (`__all__`): `CancelCondition, Comparator, EVALUABLE, Limits, OrderKind, PriceCondition, Rule, RuleStatus, Side, SizeMode` (from `model`), `Issue, Report, Severity, can_confirm, validate` (from `validation`). `RuleStore`, `to_dict`, `from_dict`, `HISTORY_LIMIT` are **not** re-exported: import from `core.rules.store`.

### A.2 `core/rules/model.py` (241 lines) — the operator-authored rule
Purpose: immutable, declarative rule; **no default with financial meaning**; editing yields a new revision (docstring 1–21).

Enums (all `class X(str, Enum)`, value == name):

| Enum | Members (verbatim) | Lines |
|---|---|---|
| `Side` | `BUY`, `SELL` | 32–34 |
| `Comparator` | `AT_OR_BELOW`, `AT_OR_ABOVE`, `CROSSES_DOWN` (previous > level and current <= level), `CROSSES_UP` (previous < level and current >= level) | 37–42 |
| `SizeMode` | `QUANTITY` (share count), `NOTIONAL` (cash amount, converted at trigger time) | 45–47 |
| `OrderKind` | `MARKET`, `LIMIT` | 50–52 |
| `RuleStatus` | `DRAFT`, `CONFIRMED`, `ACTIVE`, `PAUSED`, `EXHAUSTED`, `EXPIRED`, `CANCELLED` | 55–62 |

Constant: `EVALUABLE = frozenset({RuleStatus.ACTIVE})` (66).

Frozen dataclasses (`@dataclass(frozen=True)`):

```python
PriceCondition(comparator: Comparator, level: Decimal)            # .describe() -> "last price is at or below 68,000"
CancelCondition(after_seconds: Optional[int] = None,
                if_price_beyond: Optional[PriceCondition] = None)  # .empty: bool ; .describe() -> "... or ..." | "never"
Limits(max_triggers: Optional[int] = None,          # lifetime firings for this rule
       max_order_amount: Optional[Decimal] = None,  # per-order notional ceiling
       max_daily_amount: Optional[Decimal] = None)  # per-day notional ceiling ; .empty: bool
Rule(
  id: str = uuid4().hex[:12], revision: int = 1, name: str = "",
  symbol: str = "", market: str = "",               # market = a core.markets venue code (KRX | US | TSE | …)
  side: Optional[Side] = None, size_mode: Optional[SizeMode] = None, size_value: Optional[Decimal] = None,
  order_kind: Optional[OrderKind] = None, limit_price: Optional[Decimal] = None,
  conditions: tuple[PriceCondition, ...] = (), require_all_conditions: bool = True,   # AND when true, OR when false
  valid_from: Optional[datetime] = None, valid_to: Optional[datetime] = None,
  limits: Limits = Limits(), cancel: CancelCondition = CancelCondition(),
  status: RuleStatus = RuleStatus.DRAFT, trigger_count: int = 0,
  created_at: datetime = now(UTC), updated_at: datetime = now(UTC),
  confirmed_at: Optional[datetime] = None, notes: str = "")
```

`Rule` methods (all return a **new** `Rule` via `dataclasses.replace`; none validates a state transition):

| Method | Effect | Lines |
|---|---|---|
| `edit(**changes) -> Rule` | `revision += 1`, `updated_at = now`. If any key in `decision_fields` changed value → `status = DRAFT`, `confirmed_at = None`. `decision_fields = {"symbol","market","side","size_mode","size_value","order_kind","limit_price","conditions","require_all_conditions","valid_from","valid_to","limits","cancel"}`. `name`, `notes` do not revoke confirmation. Unknown key → `TypeError` from `replace`. | 153–176 |
| `confirm()` | `status = CONFIRMED`, `confirmed_at = updated_at = now`. Revision unchanged. | 178–181 |
| `activate()` | `status = ACTIVE`. **Unused** by any caller (UI uses `with_status(RuleStatus.ACTIVE)`). | 183–185 |
| `with_status(status)` | sets status, `updated_at`. No guard: DRAFT→ACTIVE is accepted. | 187–188 |
| `record_trigger()` | `trigger_count += 1`; `status = EXHAUSTED` when `limits.max_triggers is not None and count >= max_triggers`. Revision unchanged. | 190–198 |
| `summary() -> str` | `"On {symbol}: when {condition}, place {kind} to {side} {size}."`; unset parts render as `(no instrument)`, `(no condition set)`, `(direction not set)`, `(size not set)`, `(order type not set)`, `a limit order at (no limit price)`. | 201–236 |
| `is_confirmed` (property) | `status in (CONFIRMED, ACTIVE, PAUSED)` | 238–241 |

Conventions: money and prices are `Decimal`; timestamps tz-aware UTC; `id` is 12 hex chars. Nothing ever sets `RuleStatus.EXPIRED` or `CANCELLED` in engine code (window closed = a SKIPPED decision only).

### A.3 `core/rules/validation.py` (191 lines) — field-level validation of the operator `Rule`
```python
class Severity(str, Enum): ERROR = "error"; WARNING = "warning"
@dataclass(frozen=True) class Issue:  field: str; message: str; severity: Severity = Severity.ERROR ; .blocking -> bool
@dataclass(frozen=True) class Report: issues: tuple[Issue, ...] = ()
    .errors -> tuple[Issue,...] ; .warnings -> tuple[Issue,...] ; .ok -> bool (no errors)
    .for_field(name) -> tuple[Issue,...] ; __bool__ == .ok
_MAX_CONDITIONS = 8
def validate(rule: Rule, *, now: datetime | None = None) -> Report      # returns ALL issues at once, never raises
def can_confirm(rule: Rule) -> Report    # validate() + Issue("status", "A {cancelled|expired} rule cannot be confirmed.")
```
`Issue.field` strings in use (the UI matches on `==`, `startswith(f"{name}[")`, `startswith(f"{name}.")`, `ui/rules_page.py:307–309`): `name`, `symbol`, `market`, `side`, `size_mode`, `size_value`, `order_kind`, `limit_price`, `conditions`, `conditions[{i}]`, `valid_to`, `valid_from`, `limits`, `limits.max_triggers`, `limits.max_order_amount`, `limits.max_daily_amount`, `cancel.after_seconds`, `status`.

Checks (72–158): blank name/symbol/market → error; `side`/`size_mode`/`size_value`/`order_kind` None → error; `size_value <= 0` → error; QUANTITY not integral → error; LIMIT without `limit_price` or `<= 0` → error; MARKET with a `limit_price` → warning; no conditions or `> 8` → error; any `level <= 0` → error; AND-contradiction (`min(ceilings) < max(floors)`, ceilings = AT_OR_BELOW/CROSSES_DOWN, floors = AT_OR_ABOVE/CROSSES_UP; 161–181) → error; `valid_from >= valid_to` → error; `valid_to <= now` → warning; no window → warning; each limit `<= 0` → error; `max_order_amount > max_daily_amount` → error; `limits.empty` → warning; NOTIONAL `size_value > max_order_amount` → error; `cancel.after_seconds <= 0` → error.
Tested constraint (`engine/test_24`): no message may contain `"try "`, `"we recommend"`, `"suggested"`, `"typically"`, `"usually"`, `"e.g."`, `"for example"`.
`can_confirm` is exported and **never called** (UI calls `validate` then `.confirm()`).

### A.4 `core/rules/store.py` (240 lines) — one JSON file with per-rule history
```python
HISTORY_LIMIT = 50
def to_dict(rule: Rule) -> dict        # Decimal -> str, datetime -> isoformat, enums -> .value, nested "limits"/"cancel" dicts
def from_dict(raw: dict) -> Rule       # raises KeyError/ValueError on a bad row (caller catches)
class RuleStore:                       # threading.RLock; "the engine loop reads it while the UI writes to it"
    def __init__(self, path: Optional[Path] = None)   # default config.trading_dir() / "rules.json"; calls load()
    def all(self) -> tuple[Rule, ...]                 # sorted by updated_at desc
    def get(self, rule_id: str) -> Optional[Rule]
    def active(self) -> tuple[Rule, ...]              # status is ACTIVE
    def by_id(self) -> dict[str, Rule]
    def history(self, rule_id: str) -> tuple[dict, ...]   # prior revisions as to_dict() rows, oldest first
    def symbols(self) -> tuple[tuple[str, str], ...]  # sorted (symbol, market) of active rules
    def save(self, rule: Rule) -> Rule                # see below
    def delete(self, rule_id: str) -> bool            # also deletes that rule's history
    def clear(self) -> None                           # wipes rules AND history ("whole-reset action in §7")
    def load(self) -> None
    def export_to(self, destination: Path) -> Path    # {"version": 1, "rules": [...]} ; no history
```
On-disk shape (`_flush`, 216–231): `{"version": 1, "saved_at": "<iso, seconds>", "rules": [to_dict…], "history": {rule_id: [to_dict(previous)…]}}`, UTF-8, `indent=2, ensure_ascii=False`, atomic (`tempfile.mkstemp(dir=parent, suffix=".tmp")` → `os.replace`).

`save()` semantics (168–177): the **previous** stored revision is appended to `history[rule.id]` **only when `previous.revision != rule.revision`**; then trimmed with `del bucket[:-HISTORY_LIMIT]`. Consequence: `confirm()`, `with_status()`, `record_trigger()`, `activate()` (no revision bump) leave **no** history entry. History holds rule snapshots only: no actor, no reason, no timestamp of the edit other than the snapshot's own `updated_at`, no refusal records.

Error handling / degradation (all silent):
- `load()`: unreadable/corrupt JSON → empty store, no error (203–204); a row that fails `from_dict` is skipped (208–209); `history` kept only if a dict of lists.
- `_flush()`: **any** exception is swallowed (`except Exception: pass`, 230–231).
- `_undt()` returns `None` for an unparsable timestamp; naive → assumed UTC. `created_at`/`updated_at` missing → `now`.
- `from_dict` drops conditions whose `level is None` (104); `limits.max_triggers` / `cancel.after_seconds` are loaded uncast.

### A.5 `core/engine/__init__.py` (11 lines)
`__all__`: `Decision, Evaluator, Outcome, Quote, conditions_met` (evaluator); `OrderBook, OrderStatus, SimulatedOrder, order_id` (orders); `EngineMode, EngineState, HaltReason, Transition` (state). `EngineRuntime` and `QuoteFeed` are imported from their submodules (`core.engine.runtime`, `core.engine.feed`).

### A.6 `core/engine/state.py` (186 lines) — the single global state machine
```python
class EngineMode(str, Enum): DISARMED = "DISARMED"; ARMED = "ARMED"; HALTED = "HALTED"
class HaltReason(str, Enum):
    OPERATOR = "operator"; STALE_DATA = "stale_data"; NO_DATA = "no_data"
    PROVIDER_ERROR = "provider_error"; LIMIT_BREACH = "limit_breach"; UNKNOWN_STATE = "unknown_state"
@dataclass(frozen=True) class Transition: at: datetime; frm: EngineMode; to: EngineMode; reason: str = ""; detail: str = ""
class EngineState:                                     # threading.RLock
    def __init__(self, *, on_change: Optional[Callable[[Transition], None]] = None)   # always starts DISARMED
    mode -> EngineMode ; is_armed -> bool ; halt_reason -> Optional[HaltReason] ; halt_detail -> str
    requires_manual_rearm -> bool ; history -> tuple[Transition, ...]   (in-memory, last 500, not persisted)
    def describe(self) -> str            # "HALTED ({reason}) — manual re-arm required" | mode.value
    def arm(self) -> tuple[bool, str]    # (False, "Acknowledge the halt ({why}) before arming. This program never re-arms itself.")
                                         # | (True, "Already armed.") | (True, "Armed.")
    def disarm(self, detail: str = "") -> None
    def halt(self, reason: HaltReason = HaltReason.OPERATOR, detail: str = "") -> None   # any state, idempotent, never raises
    def acknowledge(self) -> None        # clears the flag, -> DISARMED, does NOT arm
    def snapshot(self) -> dict           # {"halt_reason": str|None, "halt_detail": str, "requires_manual_rearm": bool} — mode deliberately absent
    def restore(self, snapshot: dict) -> None   # unknown reason string -> HaltReason.UNKNOWN_STATE; mode forced DISARMED
```
Transition reasons written (strings): `"operator armed"`, `"operator disarmed"`, `reason.value` on halt, `"halt acknowledged"`. `on_change` exceptions are swallowed (111–115).
Never raised anywhere in engine code: `HaltReason.PROVIDER_ERROR`, `HaltReason.LIMIT_BREACH` (only used by `engine/test_04`). Raised: `OPERATOR` (UI/emergency stop), `NO_DATA`, `STALE_DATA` (evaluator), `UNKNOWN_STATE` (runtime loop exception; unknown persisted reason).

### A.7 `core/engine/orders.py` (234 lines) — simulated order lifecycle
```python
class OrderStatus(str, Enum): OPEN = "OPEN"; FILLED = "FILLED"; CANCELLED = "CANCELLED"; REJECTED = "REJECTED" ; .terminal -> bool
@dataclass(frozen=True) class SimulatedOrder:
    id: str; rule_id: str; rule_revision: int; rule_name: str; symbol: str; market: str
    side: Side; kind: OrderKind; quantity: Decimal; limit_price: Optional[Decimal]; notional: Optional[Decimal]
    trigger_price: Decimal; status: OrderStatus = OPEN; created_at: datetime = now(UTC)
    settled_at: Optional[datetime] = None; fill_price: Optional[Decimal] = None; reason: str = ""
    .open -> bool ; .age_seconds -> float (uses wall clock when unsettled) ; .describe() -> str
def order_id(rule_id: str, revision: int, sequence: int) -> str      # f"{rule_id}-r{revision}-t{sequence}"
class OrderBook:                                    # in-memory dict, threading.RLock, unbounded
    get(oid) -> Optional[SimulatedOrder] ; all() -> tuple (created_at desc) ; open_orders() ; for_rule(rule_id) ; exists(oid) -> bool
    counts_today(*, now=None) -> dict[str, int]     # keys = OrderStatus values; "today" = UTC date of created_at
    notional_today(*, now=None) -> Decimal          # sum of notional of ALL non-REJECTED orders created today (UTC), all rules, all currencies
    place(order) -> Optional[SimulatedOrder]        # None when the id already exists (atomic duplicate guard)
    fill(oid, price: Decimal) -> tuple[bool, str]   # operator-initiated; (False, "No such order.") | (False, "Order is already {status}.") | (True, "")
    cancel(oid, reason="cancelled by operator") -> tuple[bool, str]
    reject(order, reason) -> SimulatedOrder         # writes a REJECTED copy under order.id (overwrites any existing id)
    cancel_all_open(reason) -> int                  # no caller
    reset() -> None                                 # "연습 시나리오 초기화"
    snapshot() -> list[dict] ; restore(rows: list[dict]) -> None   # explicit field list both ways; bad row skipped
```
No fill model, no auto-fill, no cost, no partial fill, no position. `fill()` accepts any price the caller passes (`ui/trading_page.py:262–263` passes `limit_price` else `trigger_price`).

### A.8 `core/engine/evaluator.py` (334 lines) — guard chain
```python
class Outcome(str, Enum): FIRED = "fired"; SKIPPED = "skipped"; REJECTED = "rejected"; HALTED = "halted"
@dataclass(frozen=True) class Quote: symbol: str; price: Decimal; previous: Optional[Decimal]; as_of: datetime; source: str
    def age_seconds(self, *, now=None) -> float
@dataclass(frozen=True) class Decision: rule_id: str; rule_name: str; outcome: Outcome; reason: str; at: datetime
    order: Optional[SimulatedOrder] = None; quote_price: Optional[Decimal] = None ; .fired -> bool
def conditions_met(rule: Rule, quote: Quote) -> tuple[bool, str]
class Evaluator:
    def __init__(self, state: EngineState, book: OrderBook, *, max_quote_age_s: float = 120.0)
    def evaluate(self, rule: Rule, quote: Optional[Quote], *, now: Optional[datetime] = None,
                 quote_error: str = "", quote_grace: str = "") -> Decision
    def sweep_cancellations(self, rules: dict[str, Rule], quotes: dict[str, Quote], *, now=None) -> list[Decision]
```
Guard order in `evaluate` (142–231), with exact outcomes:

| # | Guard | Outcome · reason template |
|---|---|---|
| 1 | `not state.is_armed` | SKIPPED · `engine is {mode}, not ARMED` |
| 2 | `rule.status not in EVALUABLE` | SKIPPED · `rule is {status}` |
| 3 | `now < valid_from` / `now > valid_to` | SKIPPED · `window opens at {iso}` / `validity window has closed` |
| 4 | `markets.get(rule.market)` has a session and `trading_state(now)[0] != "open"` | SKIPPED · `{market} is {state}: {why}` |
| 5a | `quote is None` and `quote_grace` | SKIPPED · `no quote for {symbol}[: {quote_error}] — miss {quote_grace}, not evaluated; the engine halts if this continues` |
| 5b | `quote is None`, no grace | `state.halt(NO_DATA, detail)` → HALTED |
| 5c | `_freshness` (233–287): no session → `age > max_quote_age_s` → HALTED `… quote is {age}s old (limit {n}s)`; `age > session.max_age_hard_s` → HALTED; `quote.as_of < market.session_start(now)` → SKIPPED `… No trade has printed this session.`; `age > session.max_age_open_s` → HALTED | `state.halt(STALE_DATA, detail)` on HALTED |
| 6 | `conditions_met` false | SKIPPED · explanation |
| 7 | `book.exists(oid)` where `oid = order_id(rule.id, rule.revision, rule.trigger_count + 1)` | SKIPPED · `trigger {n} already placed as {oid}` |
| 8 | `_cap_refusal` (289–309): quantity ≤ 0; `trigger_count >= max_triggers`; `notional > max_order_amount`; `book.notional_today + notional > max_daily_amount` | REJECTED · reason, and `book.reject(candidate, reason)` is written |
| 9 | `book.place(candidate)`; `None` → SKIPPED (duplicate) | FIRED · explanation |

Sizing (`_order_notional`, 115–130): reference = `limit_price` for LIMIT else `quote.price`; QUANTITY → `(q, q × ref)`; NOTIONAL → `q = floor(size_value / ref)`. Cancel sweep emits `Decision(…, Outcome.SKIPPED, "cancelled — {reason}", …)`.
A halt is **global** (one `EngineState`); the docstring (15–25) states freshness is a halt, not a skip; a closed venue or a not-yet-printed session is a skip.

### A.9 `core/engine/feed.py` (285 lines) — provider rows → `Quote`
```python
class QuoteFeed:
    def __init__(self, krx_gateway=None, fmp_client=None)       # FMP client built lazily on first use
    fmp (property) ; provider_status() -> list[dict]
    last_error(symbol) -> str ; previous(symbol) -> Optional[Decimal] ; misses(symbol) -> int
    is_permanent(symbol) -> bool ; degraded() -> list[tuple[str, int, str]] ; clear_misses() ; reset()
    fetch(symbol, market) -> Optional[Quote]
    fetch_many(pairs: Iterable[tuple[str, str]]) -> dict[str, Optional[Quote]]     # keyed by SYMBOL only
```
Routing by `markets.provider_for(market)` (`"krx"` → `krx_gateway.quote(symbol)` per symbol; `"fmp"` → one `client.quotes([...])` call with `markets.provider_symbol` suffixing). Miss accounting: `+1` per failed fetch, `max(0, held − 1)` per good quote (187–195). Permanent failures (no grace): unknown venue, missing KRX gateway, FMP not ready, FMP plan block (HTTP 402). `_record` refuses `price <= 0` (`"provider returned no usable price"`) and a missing timestamp (`"provider returned no timestamp"`): **a timestamp is never invented**. `previous` = price at the previous successful fetch of that symbol (not previous close).

### A.10 `core/engine/runtime.py` (415 lines) — owns state, book, evaluator, feed; background thread
```python
DECISION_RING = 400
class EngineRuntime:
    def __init__(self, store: RuleStore, feed: QuoteFeed, *, tick_seconds: Optional[float] = None,
                 max_quote_age_s: Optional[float] = None, no_data_grace: Optional[int] = None,
                 state_path: Optional[Path] = None, on_update: Optional[Callable[[], None]] = None,
                 clock: Optional[Callable[[], datetime]] = None)
    # attributes: store, feed, tick_seconds, no_data_grace (clamped to 0..10), state_path, on_update,
    #             state: EngineState, book: OrderBook, evaluator: Evaluator
    arm() -> tuple[bool, str] ; disarm() ; halt(reason=HaltReason.OPERATOR, detail="") ; acknowledge()
    mode (property) ; decisions(limit=50) -> tuple[Decision, ...] (newest first) ; last_tick (property)
    dashboard() -> dict ; stop() ; tick() -> list[Decision] (non-reentrant; [] if a pass is running)
    reset_practice() -> None
```
`dashboard()` keys (158–187): `venues` (list of `{code, open: True|False|None, why, describe, rules}`), `degraded` (list of `(symbol, misses, last_error)`), `calendar_stale`, `mode`, `describe`, `halt_reason`, `halt_detail`, `needs_ack`, `active_rules`, `total_rules`, `fired_today`, `rejected_today`, `orders_today`, `open_orders`, `notional_today`, `last_tick`.
Loop: daemon thread `"nextgen-engine"` started on the first successful `arm()`; `tick()` only while armed; an exception in a tick → `state.halt(HaltReason.UNKNOWN_STATE, "{Type}: {exc}")`. Per pass (`_tick_locked`, 272–341): fetch only venues with `markets.is_open(...) is not False`; **re-read the clock after the fetch**; evaluate each active rule; on FIRED `store.save(rule.record_trigger())` immediately; cancel sweep; log a decision only when `(outcome, reason)` changed for that rule (grace episodes collapse to one line); `_persist()`; `_notify()`.
Persistence (`_persist`/`_restore`, 364–407): `{"version": 1, "saved_at", "state": EngineState.snapshot(), "orders": OrderBook.snapshot(), "decisions": [{rule_id, rule_name, outcome, reason, at, quote_price}]}` to `state_path`, atomic, all exceptions swallowed. Written on every state transition (`on_change`), every tick that had at least one active rule (a pass with no active rules returns before `_persist`, 275–278), and `reset_practice`. Restored decisions lose their `order` link.

---

## B. Cross-file flows

Import direction (no cycles; keep it): `core.rules.model` ← `core.rules.{validation,store}`; `core.engine.orders` ← `core.rules.model`; `core.engine.evaluator` ← `core.markets`, `core.engine.{orders,state}`, `core.rules.model`; `core.engine.feed` ← `core.markets`, `core.engine.evaluator` (`Quote`), `data.fmp` (lazy); `core.engine.runtime` ← `core.calendars`, `core.markets`, all engine modules, `core.rules.{model,store}`, `config` (lazy, inside `__init__`). `core.rules` never imports `core.engine`. `config` is imported lazily in `RuleStore.__init__` and `EngineRuntime.__init__`.

Wiring (`main.py:107–113`): `gateway = KRXGateway()` → `rule_store = RuleStore()` → `engine = EngineRuntime(rule_store, QuoteFeed(gateway))`, constructed once in `main(page)` so they outlive navigation. `build_trading_page(page, engine, …)` and `build_rules_page(page, rule_store, on_changed=lambda: cache.pop("trading", None))`. The `trading` view is rebuilt on every navigation (`main.py:164`).

Callers:
- `ui/rules_page.py`: `store.all()`, `store.save(rule.with_status(s))`, `store.save(rule.confirm())`, `store.delete(id)`, `validate(rule)` on every keystroke via `dataclasses.replace(base, **changes)`, `store.save(draft.edit(**12 fields))`, `.edit(...).confirm()` (lines 133, 140, 148, 167, 301, 305, 457, 475–480).
- `ui/trading_page.py`: `runtime.arm/disarm/halt/acknowledge/tick`, `runtime.dashboard()`, `runtime.decisions(limit=40)`, `runtime.book.fill(oid, price)`, `runtime.book.cancel(oid)`, **`runtime._persist()` (private, lines 110, 118)**, assigns `runtime.on_update = refresh`, reads `runtime.tick_seconds`, `runtime.no_data_grace`; indexes `MODE_STYLE[mode]` (KeyError on a new `EngineMode` member) and `OUTCOME_STYLE.get(outcome, …)` (safe for a new `Outcome`).

Disk (default root `Path.home()/".nextgen"`; this machine: `C:/Users/whydi/.nextgen`):

| File | Writer | Content |
|---|---|---|
| `trading/rules.json` | `RuleStore._flush` | rules + history (currently 1 rule, 1 history key, `version: 1`) |
| `trading/engine.json` | `EngineRuntime._persist` | halt snapshot, orders, decision ring |
| `trading/practice_checklist.json`, `trading/safety.json`, `policy_events.jsonl`, `prefs.json` | **no writer in the current code** (NEXTGEN leftovers) | do not reuse these names |

Env vars read by this subsystem (module-level constants in `config.py`, evaluated at import; `.env` loaded by `python-dotenv`):

| Var | Default | Used by |
|---|---|---|
| `NEXTGEN_TRADING_DIR` | `~/.nextgen/trading` | `config.trading_dir()` → `rules.json`, `engine.json` |
| `NEXTGEN_QUOTE_MAX_AGE` | `120` s | `Evaluator.max_quote_age_s` (only for a venue without a session) |
| `NEXTGEN_ENGINE_TICK` | `5` s | `EngineRuntime.tick_seconds` |
| `NEXTGEN_NO_DATA_GRACE` | `3` passes (runtime clamps 0..10) | `EngineRuntime.no_data_grace` |
| `NEXTGEN_MAX_AGE_<MARKET>` | per venue: KRX `120`, FMP venues `180` | `core/markets._with_overrides` → `Session.max_age_open_s` |
| `NEXTGEN_FMP_MIN_INTERVAL` | `20` s (must stay `< QUOTE_MAX_AGE`; `engine/test_50`) | `data.fmp` throttle |
| `FMP_API_KEY`, `KIS_APP_KEY`, `KIS_APP_SECRET` | — | quote providers |

Collaborator interfaces the engine depends on: `markets.get(code) -> Optional[Market]`, `Market.trading_state(now) -> (state, why)` with state ∈ `"open" | "closed" | "unknown"`, `Market.session_start(now)`, `Session.max_age_open_s`, `Session.max_age_hard_s` (`DEFAULT_HARD_AGE_S = 5*24*3600`), `markets.is_open(code, now) -> Optional[bool]`, `markets.provider_for`, `markets.provider_symbol`, `calendars.stale_markets()`. Venue codes are `KRX, US, LSE, XETRA, EURONEXT_PA, EURONEXT_AS, BIT, BME, SIX, OMX_ST, OSE, TSE, HKEX, SSE, SZSE, TWSE, SGX, NSE, ASX, TSX, B3, BMV` (`core/markets.py:247–320`).

---

## C. Existing tests

Runner: `python tests/run_all.py` (no pytest). `run_all.py:30–44` imports each suite's `tests()` and prefixes names: `cockpit/`, `engine/`, `ui/`, `quant/`, `ficc/`, `expansion/`. Each test is a zero-argument function; PASS unless it raises. Results → `qa/acceptance_results.json` (`[{test, status, seconds, detail}]`); exit code 1 on any failure. stdout/stderr are reconfigured to UTF-8 (cp949 fix, `run_all.py:24–28`).

**Registering new tests:** (a) add a module-level `def test_NN_name():` to `tests/engine_acceptance.py` — its `tests()` (1396–1398) auto-collects every `test_*` callable, sorted by name; or (b) create a new suite file exposing `def tests() -> list[tuple[str, Callable]]`, then add one import and one line to `tests()` in `tests/run_all.py`. The 266 count is the baseline; a v2 suite adds to it.

`tests/engine_acceptance.py` — 89 tests, `test_01 … test_91` (numbers 63, 64 absent). Fixtures: `NOW = 2026-08-18T06:00Z`; `TRADING_NOW = 2026-08-19T02:00Z` (11:00 KST Wed); `_rule(**over)` (ACTIVE KRX 005930 BUY 10 MARKET, AT_OR_BELOW 70000, `Limits(max_triggers=3, max_order_amount=10_000_000)`); `_quote`; `_armed()`; `_runtime(tmp, price)` (fake gateway, `tick_seconds=999`, `state_path=tmp/engine.json`, pinned `clock`); `_flaky_runtime(tmp, outcomes, grace)`; `_FakeFMP`; `_tmpdir()` (`tempfile.mkdtemp`, never removed). No test touches `~/.nextgen`.

| Tests | Asserted contract (v2 code must not break it) |
|---|---|
| 01–05 | `EngineState()` starts DISARMED; HALTED refuses `arm()` until `acknowledge()` and acknowledging does not arm; `"mode" not in snapshot()`; an unacknowledged halt survives `restore()`; `halt()` works from any state, twice |
| 06–17 | disarmed never fires; stale quote → HALTED + `STALE_DATA`; missing quote → HALTED + `NO_DATA`; duplicate trigger SKIPPED `"already placed"`; `max_triggers` → REJECTED `"already fired"` with a REJECTED order in the book; per-order cap `"exceeds this rule's maximum"`; daily cap `"daily maximum"`; rejected orders do not consume `notional_today`; skip reason contains `"not met"` and `"60,000"`; `"validity window has closed"`; crossing needs `previous`; notional below one share → REJECTED `"smaller than one share"` |
| 18–21 | placed orders stay OPEN (**never self-fill**); manual `fill` then `cancel` → `"already filled"`; `book.reset()`; cancel sweep (pokes `book._orders` directly) |
| 22–29 | `Rule()` has None for `side,size_mode,size_value,order_kind,limit_price`, `conditions == ()`, `limits.empty`; `validate(Rule())` reports `{name,symbol,side,size_value,order_kind,conditions}` at once; no value hints; contradictory AND conditions; decision edit → DRAFT + `revision+1`; rename keeps confirmation; EXHAUSTED at `max_triggers`; `summary()` content |
| 30–34 | runtime increments `trigger_count` once; 8 concurrent ticks place 1 order; `place()` refuses a duplicate id; restart reloads the book but mode is DISARMED; disarmed runtime fires nothing |
| 35–37, 42–46, 86 | feed: no invented timestamp; `previous` tracked; unknown venue = missing data, not a crash; provider-symbol round trip; one FMP call per pass; 402 reported verbatim; one miss per symbol per pass |
| 38–39 | `RuleStore` round-trips `Decimal("68000.55")`; saving a new revision keeps the previous one (`history[0]["size_value"] == "10"`) |
| 40–41, 47–50 | market registry routes every code to `krx`/`fmp`; suffix idempotent; FMP key redaction, throttle, plan-block not retried; `FMP_MIN_INTERVAL_SECONDS < QUOTE_MAX_AGE_SECONDS` |
| 51–62, 65–66, 76 | per-venue sessions: overnight US quote SKIPPED not HALTED; fresh in-session fires; 20-min-old in-session HALTED; no print this session SKIPPED (`"before today"`); 9-day-old HALTED; lunch break SKIPPED; weekend closed; every market has a session with `max_age_open_s < max_age_hard_s`; real tz with DST; no-session venue uses the global bound (`"limit 60s"`); closed venue with no quote SKIPPED; missing data while open HALTED naming the cause; closed venues not fetched; unchanged verdict logged once |
| 67–75 | holiday by name; KRX Seollal; half-day close 13:00 ET; uncovered date → `is_trading_day is None`; every market has calendar data; coverage not expired; provenance `library == "exchange_calendars"`; 20k lookups < 1 s |
| 77–80, 83–85, 87–88, 90–91 | grace: `"miss 1 of 3"`, recovery pays one miss back; outlasting grace → HALTED, `arm()` still needs `"Acknowledge"`; grace 0 halts at once; plan refusal halts at once; one log line per grace episode; arming starts a fresh window, re-arming an armed engine does not; fetch time counts against freshness; dashboard `degraded` rows; grace capped at 10; venue opening mid-pass does not halt |
| 81–82, 89 | HTTP retry session policy (**`test_82` starts a real `HTTPServer` on 127.0.0.1**), KIS pacing and `EGW00201` handling |

`tests/flet_api_guard.py` (4 tests, `ui/` prefix) statically scans `ui/*.py` only: every `page.<method>()` exists on `ft.Page`; every keyword of a checked `ft.<Control>(...)` exists in its `__init__`; attribute assignments on singly-assigned controls exist; every `pal.<token>` is in `core.theme.token_names()`. Any v2 UI (book states, governance alerts) passes through this guard.

No existing test covers: `can_confirm`, `export_to`, `RuleStore.delete/clear`, `HISTORY_LIMIT` trimming, `cancel_all_open`, `reset_practice`, a corrupt `rules.json`, `EngineState.disarm()` while HALTED.

---

## D. Extension points for v2

Rule for every item below: **add beside, do not alter** `Rule`, `validate`, `EngineState`, `OrderBook.fill`'s manual contract, or the `engine.json` / `rules.json` shapes. Section E lists why.

### D.0 Reuse, do not duplicate

| Need | Reuse | Where |
|---|---|---|
| All-at-once, field-bound refusals | `Issue(field, message, severity)`, `Report`, `Severity` | `core/rules/validation.py:30–66` |
| Atomic JSON write | `tempfile.mkstemp(dir=parent, suffix=".tmp")` + `os.fdopen(..., "w", encoding="utf-8")` + `os.replace` | `store.py:224–229`, `runtime.py:378–384` (same code twice; a third copy should call one helper) |
| Decimal / datetime (de)serialisation | `_dec`, `_undec`, `_dt`, `_undt` | `store.py:36–55` |
| Storage root + env override for hermetic tests | `config.trading_dir()` / `NEXTGEN_TRADING_DIR`; constructor `path=` injection as in `RuleStore(path)`, `EngineRuntime(state_path=…)` | `config.py:236–238` |
| Injectable clock | `EngineRuntime(clock=…)`, `evaluate(now=…)`, `validate(now=…)` | never call `datetime.now()` in new acting code (also SPEC:1105) |
| Deterministic ids / atomic duplicate guard | `order_id(rule_id, revision, sequence)`, `OrderBook.place()` returning `None` | `orders.py:83–85, 138–150` |
| Immutable revisioned object pattern | `@dataclass(frozen=True)` + `replace` + `edit()` bumping `revision` | `model.py:153–176` |
| Venue session, holiday, half-day | `markets.get(code).trading_state(now)`, `.windows_for`, `.session_start`, `calendars.is_trading_day` (`None` = unknown, never "open") | `core/markets.py`, `core/calendars.py` |
| Thread-safety idiom | one `threading.RLock` per store; non-reentrant `tick` via `Lock.acquire(blocking=False)` | `runtime.py:94–97, 265` |

### D.1 Rule-object schema, bounds validation, DO-NOT-BUILD refusals (TASK-M0-04, -05, -14; SPEC:4687–4705, 6229–6252, 4620–4679; tests T-CAP-01, T-BASIS-01, T-DNB-01)

What exists: nothing. `Rule` has none of the §7.1 fields.

Attach:
- **New frozen dataclass** (proposed `core/rules/objects.py`, class `RuleObject`) with the §7.1 fields verbatim: `rule_id`, `kind` ∈ `{INVARIANT, CONVENTION, CARD-O, CARD-P, CONTEXT, GOVERNANCE}`, `output_range` `[lo, hi]`, `exposure_basis` ∈ `{active, total}`, `applies_to` ∈ `{momentum, reversal, flow, quality, ts_trend, market_gross}`, `composition` (`min`), `books[]` ∈ `{recommended, specification, forward_sim, refusal}`, `inputs[]` of `{series_id, role, books, timing, source_kind}` with `source_kind` ∈ `{market_price, published_series, derived, implied_vol, regime_model, ml_classifier}`, `estimator` `{name, kind}` with `kind` ∈ `{sma, ewma, garch, har, comb, ml}`, `label_layer` ∈ `{none, conformal}`, `instrument_book`, `market`, `card_id`, `tier`, `header_md5`, `results_md5`, `n_rule` (SPEC:4693–4704). No field default with financial meaning (same rule as `Rule`; SPEC:4127). Hyphenated enum values (`CARD-O`, `CARD-P`) need explicit `Enum("…")` values, not member names.
- **Validation in `core/rules/validation.py`** (the spec names this module as the enforcer, SPEC:6231): new `validate_rule_object(obj, *, store_ctx) -> Report` returning `Issue`s. Each §10.3 shape = one predicate `(obj, ctx) -> Optional[Issue]`; `Issue.field` = the §7.1 field, `Issue.message` must name the §10 item number and its label (`harm`/`null`/`inconclusive`, SPEC:4621–4661, 6231; TASK-M0-14). The 17 `refused_shapes` keys and item numbers are SPEC:4662–4679 verbatim. Bounds (T-CAP-01, SPEC:5626): overlay outside `[0.5, 1.0]` refused; `vt`/`vs` outside `[0, 1.0]` refused; `output_range.hi > 1.0` refused (items 2, 8); `composition != "min"` refused (item 31); `exposure_basis` missing on an acting rule refused; a vt (R-06) rule on anything but `market_gross` refused; any multiplier on `ts_trend` refused (SPEC:4696).
- **Existing `validate(rule: Rule)` keeps its name and signature** (UI calls it per keystroke; `engine/test_23,24,25`). `validate_card_header` (TASK-M0-09, -13: "`core/rules.validate_card_header`") lands in the same module.
- **Store hook.** `RuleStore.save()` performs **no validation today** (anything is written). For rule objects the spec requires "The refusal names the item and its label. It is logged in the store's edit history, and nothing is written" (SPEC:6231). Attach as a validating `save()` on the **new** rule-object store (D.1a), which on `not report.ok` appends a refusal record and returns/raises without touching the object map. Do not add v2 validation to the operator `RuleStore.save()` (the UI deliberately saves invalid DRAFT rules: `rules_page.py:455–465`).

D.1a — the v2 store itself (TASK-M0-05). `rules.json` is a flat list of operator `Rule`s with `"version": 1`; the §7 document is a nested config (`version: "2.0.0"`, `as_of`, `read_only: true`, `owner_decisions`, `time`, `calendars`, `data_contracts`, `vol_target`, `fill_model`, `instruments`, `cards`, `monitoring`, `gate.*`, `do_not_build`, `reproducibility`; SPEC:4134–4685). It cannot be a `Rule` row and `from_dict` would raise `KeyError: 'id'` and silently drop it (see E-2). Attach as a **second document with its own file and class** (proposed class `MacroRuleStore` in `core/rules/store.py` or a sibling module; file name distinct from `rules.json`), reusing the atomic-write and RLock idioms, with:
- an **append-only** revision log (who/when/what/reason/refused-or-applied) — the existing `history` map cannot serve: it is capped at `HISTORY_LIMIT = 50`, deleted by `delete()`/`clear()`, records no refusals, and skips same-revision saves (A.4). R-25 reads this log as the card revision log in M8 (TASK-M0-04 last sentence).
- `read_only: true` asserted at load (SPEC:4137).
- constructor `path=` so tests use a temp copy (T-HERM-02: store byte-identical before and after `tests/run_all.py`).

### D.2 Owner-decision registry with `{ref}` resolution (TASK-M0-06; SPEC:4130, 4138–4152, 5444–5446, 5672; test T-OWNER-01)

What exists: nothing.

Binding shape (SPEC:4130, 4140–4152): `owner_decisions.D<n> = {key, value, default, options, status, effective_from, rationale, refs}`, `status` ∈ `default | owner_set | pending`.

| D | `key` (canonical, dotted) | default `value` | `options` | `status` | `refs` |
|---|---|---|---|---|---|
| D1 | `risk_layer.korea_caps.template` | `msci_25_50` | `[domestic_max10_or_weight, msci_25_50, pair_35]` | default | `[]` |
| D2 | `risk_layer.drawdown.hard_stop.level` | `-0.15` | `[-0.15, "-1.5*sigma_book"]` | default | `[cards.R-31_step_down.hard_stop_level]` |
| D3 | `families.reversal.calm_state_downweight` | `not_adopted` | `[not_adopted, reopen_after_krx_net_test]` | default | `[]` |
| D4 | `monitoring.false_demotion_budget_per_year` | `0.10` | `[tighten_only_le_0p10]` | default | `[]` |
| D5 | `sleeves.US.line` | `none` | `[CME_micro_ES, KRX_listed_SP500_ETF, none]` | **pending** | `[instruments.us_line_choice, cards.R-28_trend_axis.us_sleeve, cards.R-29_US_FUT.us_sleeve_and_line]` |
| D6 | `gate.acceptance_test.cdar_guard.calibration` | `lowest_placebo_false_pass_rule` | 4 options (SPEC:4151) | default | `[]` |

Attach (new module in `core/rules`, e.g. `core/rules/registry.py`; pure functions over the loaded document, no engine import):
```python
def resolve_refs(doc: dict) -> dict            # at load: replace every {"ref": "<dotted key>"} by the value at that path
def check_owner_decisions(doc: dict) -> Report # T-OWNER-01 predicates below
def rule(doc, decision: str, value, *, actor="owner", rationale, effective_from) -> dict   # owner ruling
```
Load-time predicates (T-OWNER-01, SPEC:5672; TASK-M0-06): (1) each D1–D6 canonical key exists and holds a **plain scalar equal to `owner_decisions.D<n>.value`** (the scalar lives twice by design: registry `value` and the key itself, e.g. SPEC:4486 `false_demotion_budget_per_year: 0.10`); (2) every `{ref: …}` resolves; (3) a `{ref}` object with any other key is refused; (4) a **literal** at a path listed in some `D<n>.refs` (or at the canonical key) that differs from the key's value is refused at load. A ruling: sets `value`, flips `status` to `owner_set`, re-resolves every reference, appends one `owner_ruling` governance event (D.3). It is never an acting-parameter edit (never demotes) and never a gate-package change (SPEC:5445–5446). A card header records the values at commit and is checked only at commit; a D2 ruling gives R-31 a counted revision before its next run (SPEC:5446, 5672).
`{ref}` targets seen in the spec that are **not** owner decisions: `sleeves.US.notional_nav`, `sleeves.KR.notional_nav` (SPEC:3028, 3109, 4288, 4429, 4438) — the resolver must be a general dotted-path resolver, not a D-key lookup.

### D.3 Append-only hash-chained governance log (TASK-M0-07; SPEC:4094–4119, 1248–1250, 5681; tests T-OWNER-01, T-SCHEMA-01, T-OBS-05)

What exists: nothing hash-chained. `EngineState._history` (in-memory, 500 `Transition`s, not persisted) and the decision ring (400, deduplicated, rewritten whole each tick) are **not** append-only logs and must not be presented as one.

Attach: "`core/rules` (M0) owns the appender" (SPEC:4096) → new module `core/rules/governance.py`:
```python
def append_event(path: Path, *, kind, book_id, rule_id, key, actor, reason, refs, old=…, new=…) -> dict
def verify_chain(path: Path) -> Report        # T-OBS-05; a hand-edited row -> GOVERNANCE_LOG_BROKEN (page severity)
```
Record (schema `$id: quantgen/governance_event.v2.0`, SPEC:4099–4110): required `["schema","schema_version","event_id","utc","kind","book_id","rule_id","key","actor","reason","refs","prev_row_md5"]`; `schema` const `quantgen.governance_event`; `schema_version` const `"2.0"`; `kind` ∈ `halt, rearm, book_state, demotion, package_freeze, package_redesign, header_commit, owner_ruling, calendar_change, notional_change, admissibility_reweight, binding_share_recompute, binding_change, record_reset, verdict_integrity`; `actor` ∈ `owner, operator, runtime, harness, council`; `book_id`/`rule_id`/`key` string-or-null; `old`/`new` any JSON; `prev_row_md5` = md5 of the previous line, `null` only on the first line. File name `governance_events.jsonl`, one JSON object per line. Example line: SPEC:4116–4118 (must validate, T-SCHEMA-01).
Callers: the registry (D.2: `owner_ruling`), the per-book runtime (D.4: `halt`, `rearm`, `book_state`), later `core/calendars` (`calendar_change`), the gate harness, R-25. `core/engine` importing `core.rules.governance` respects the existing import direction.
Implementation constraints from this codebase: (a) open in **binary append** (or `newline="\n"`, `encoding="utf-8"`): Windows text mode writes `\r\n` and the default codec is cp949, either of which changes the hashed bytes; (b) **do not copy the `except Exception: pass` idiom** of `_flush`/`_persist` — a failed append must raise (fail closed), otherwise the chain silently loses events; (c) never rewrite the file (no `os.replace` here); (d) hash the exact bytes of the previous line; canonical JSON form is given at SPEC:4683 (`canonical_json: sorted_keys_repr_floats_no_whitespace`); (e) path via a `config` function with an env override so `tests/run_all.py` never writes the real log; (f) the verifier ships in M0 and is wired into app start in M8 (TASK-M0-07) — natural call site `main.py` before `EngineRuntime(...)` construction (`main.py:112`).

### D.4 Per-book runtime states (TASK-M1-20, M1-17, M5-03, M5-04, M5-12; SPEC:1178–1180, 1187; tests T-ROLE-01, T-HALT-01, T-SCOPE-01, T-OBS-01)

What exists: one `EngineState` per process, global halt, manual acknowledge, mode never persisted, `HaltReason` flat enum. `EngineRuntime` owns exactly one `state`, one `book`, one `evaluator`.

What v2 specifies (verbatim terms): book ids `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on|off|S>` (SPEC:1180). States `DISARMED` (initial; also a retired book) → `ARMED` (automatic, from never-armed only, when every acting input bound to the book is fresh and past warm-up, calendars cover ≥ 60 sessions ahead, and for card books the header is committed) → `HALTED` → `ARMED` (re-arm rules) ; `ARMED|HALTED → DISARMED` owner action only, never re-arms. Halt block: `halt.class` ∈ `RISK | OPS`, `halt.reason_code`, `halt.causes[]` of `{class, reason_code, since_utc, rearm_mode, rearm_not_before, cleared_utc}`, top-level `class`/`reason_code`/`since_utc` restate `causes[0]`, top-level `rearm_mode` = `operator` while any uncleared cause needs the operator else `auto` (SPEC:1179). Hooks (SPEC:1081–1086):
```python
def runtime_halt(book_id: str, cls: Literal["RISK", "OPS"], reason: str) -> None    # that book only; idempotent per cause;
        # a new cause joins halt.causes[]; never extends rearm_not_before, never resets a reference; governance event
def runtime_rearm(book_id: str, mode: Literal["auto", "operator"], operator: str | None = None) -> None
```
Re-arm rules to encode (SPEC:1179): RISK — exposure 0 on sessions t+1…t+10 of the book's primary-market calendar, automatic re-arm at the decision at the close of t+10; after a hard-stop cause both references reset to NAV at re-arm; `post_rearm_cap = 0.5` joins `min()` for the re-arm decision and the 9 after it; a risk-limit-breach cause re-arms only at the first decision ≥ t+10 at which the post-action target meets the limit, no reference reset. OPS — re-arm at the first decision at which the cause has cleared; no refusal window, no reference reset, no cap; **operator re-arm required** after a lag-audit violation or an acting-artifact schema failure. Operator kill = `runtime_halt(book_id, "OPS", "operator_kill")` (SPEC:1186). A card's `on/off/S` books are killed and retired together (SPEC:1180).

Attach:
- **State class** in `core/engine/state.py` beside `EngineState` (spec: "`core/engine/state` persists … each book's runtime state and consecutive-failure counters", SPEC:1187). Reuse `EngineMode` for the three state names (values already `"DISARMED"`, `"ARMED"`, `"HALTED"` = the `macro_state` `engine_state` strings, SPEC:4117). Do **not** subclass or reuse `EngineState`: its `arm()` refuses without acknowledgement, its `snapshot()` omits the mode, its `halt()` takes a `HaltReason` and keeps one reason (no `causes[]`).
- **Do not extend `HaltReason`** for v2 codes: carry `class` + free `reason_code` strings on the new class. (Adding members is harmless to `restore()` — unknown strings map to `UNKNOWN_STATE` — but mixing the vocabularies invites a book-scoped cause halting the global engine.)
- **Registry + hooks** in `core/engine/runtime.py` as module-level `runtime_halt` / `runtime_rearm` over a registry object keyed by book id (constructor-injected path and clock, as `EngineRuntime`). The hooks take explicit `decision_utc`; they are stepped **per decision** (one per market per close) by the macro workflow, not by the 5 s `_loop`.
- **Persistence**: a separate file from `engine.json`. `_persist()` writes a fixed key set and `_restore()` reads only `state`, `orders`, `decisions`; adding a `books` key there would be dropped/overwritten by every tick of the operator engine. Unlike `EngineState`, book state **must persist the state itself** plus `hwm_hard`, `ref_step`, `dwell_left`, `rearm_not_before`, `post_rearm_left`, per-(book, series) and per-book failure counters, switch counts, forward alarms (SPEC:1187, 3271).
- Every HALT, re-arm and state change appends a governance event (D.3) **and** fills the book's `macro_state.runtime[]` entry (T-OBS-01).
- Scope rule to enforce in the registry API (SPEC:1178 "Scope (binding)"): a trigger HALTs only the books whose own NAV breached, whose own artifact failed acting-field validation, or that read the failed input through an `acting_exposure` binding; a global failure HALTs every reading book, "never 'the engine' as such". ⇒ the per-book hooks must **never call `EngineState.halt()`**, and the operator engine's own `NO_DATA`/`STALE_DATA` global halts stay as they are (they concern operator rules only).

### D.5 Drawdown-ladder and hard-stop hooks (TASK-M5-03, M5-05; SPEC:1055–1058, 1182, 1586–1587, 3271–3302; tests I-04, I-04b, T-HALT-01, T-STEP-01…05)

What exists: nothing; and no NAV to evaluate them on (fact 1).

The functions live in `core/quant/risk` (`drawdown_ladder(nav_path, decision_utc) -> LadderState`, `compose(vt, overlays, ladder, post_rearm_cap)`), **not** in this subsystem. This subsystem supplies three attachments:
1. **State carrier** — `LadderState{hwm_hard, ref_step, step_mult in {1.0, 0.5}, dwell_left, block_new_entries, halted, rearm_not_before, post_rearm_left, binding_share}` (names binding, SPEC:1056–1057, 3271) is persisted per book in `core/engine/state` (D.4).
2. **Hard stop → halt hook** — when `dd_hard <= hard_stop_level` (`<=`, exactly −15.00% triggers, T-HALT-01; level read through `{ref: risk_layer.drawdown.hard_stop.level}`, never a literal, SPEC:3327) the risk function calls `runtime_halt(book_id, "RISK", <hard-stop code>)`; `halt()` idempotent; steps cleared; ladder **not evaluated while HALTED**, references frozen until re-arm (SPEC:3285–3288). An exception inside an acting risk-layer function (`market_vol_target`, `concentration_bound`, `drawdown_ladder`, `compose`) → `runtime_halt(book, "OPS", …)` (SPEC:1178). Whole-book NAV unavailable → step state held + alert; `> 2` consecutive decisions → OPS HALT (SPEC:1178, 3337).
3. **−12% step → evaluator block** — `block_new_entries` feeds `evaluator_block` (D.7). Steps: `−0.08 → 0.5`, `−0.12 → 0.5 + evaluator_block_new_entries`, `dwell_sessions: 21` including the first, totals never cumulative, `composition: min`, `binding_share_threshold: 0.10` (> 0.10 → specification book only until the R-31 CARD-P passes; KOSPI VT20 ≈ 19%) (SPEC:3316–3328).

Prerequisite this subsystem cannot satisfy today: a per-book NAV series valued at each decision from official closes (SPEC:1181, binding `NAV_LINE_CLOSES`, `nav_fx`). `OrderBook` holds orders, not holdings. A book ledger (weights/positions, cost-charged fills, NAV) must be built (TASK-M5-12 places the simulated books in `core/engine/orders` and their state in `core/engine/state`).

### D.6 Simulated close-auction fill model, reached only through the simulated order book (TASK-M5-10, M0-01; SPEC:1087, 1177, 2893–2946; tests T-FILL-01/02/03, T-RO-01)

What exists: `OrderBook.fill(oid, price)` (manual, any price), `OrderStatus` `OPEN|FILLED|CANCELLED|REJECTED`. No venue fill rule, no cost.

Spec API (R-27 text binds over §3.5, SPEC:963): in `core/engine/orders` — `fill_model(venue) -> FillModel` and `simulate_fill(order, session) -> Fill | NonFillable(reason)` (SPEC:2893). Config block `fill_model` verbatim at SPEC:2930–2936 (`KRX: {snapshot: closing_call_start_minus_1min, snapshot_kst_since_2016-08-01: "15:19", fill: official_close, random_end_max_s: 30, fallback: post_close_session_UNVERIFIED, limit_price: tick_rounded_toward_prev_close, etf: {flag: LP_exempt_auction, inav_residual_flag_bp: 30}, limit_lock: non_fillable_at_close}`, `NYSE: {snapshot_et: "15:50", fill: official_close_moc_equivalent}`, `KOSPI200_futures: {trades_until_kst: "15:45", expiry_day_stop_kst: "15:20"}`, `bars: {…, daily_close_from_bars: forbidden}`). Outputs: `decision_price_source ∈ {snapshot_1519, official_close}`, `fill_status ∈ {filled, non_fillable_limit_lock, carried}`, `flags[]` ∈ `{LP_exempt_auction, inav_residual_gt_30bp}` (SPEC:2940).

Attach:
- **Pure function + result types in `core/engine/orders.py`**: `simulate_fill` computes a result from PIT inputs (official close with `value_status = official_close`, previous close, `price_limit` regime tag, tick table, iNAV); it does **not** mutate a book. The book runner then applies a `Fill` through the existing mutation API `OrderBook.fill(oid, fill.price)`, and leaves a `NonFillable`/carried order `OPEN` (carried to the next session, logged). This keeps one mutation path, which is what T-RO-01 checks ("`core/engine/orders` is reached only through the simulated order book API", SPEC:5605) and what TASK-M0-01 scans for.
- **One `OrderBook` instance per book id** (the class is plain and instantiable; `EngineRuntime.book` stays the operator's practice book). Operator-rule orders keep the manual-fill contract (`engine/test_18`); only macro-book orders pass through `simulate_fill`.
- **Limit-lock predicate** (SPEC:2913–2917): non-fillable when the official close **equals** the session limit price = previous close × (1 ± `price_limit`) rounded to the tick **toward the previous close**; limit-up blocks buys, limit-down blocks sells; never a `|r| ≥ limit` test (SK hynix 2026-07-31 closed at +29.95%). ETF and futures lines stay fillable unless themselves locked.
- **Fail-closed** (SPEC:2944–2946): no official close for the session → no fill, order carried, alert; a bar-derived close is refused; an unverified KIS quote field cannot drive a snapshot → fall back to the official-close decision, labelled.
- `SimulatedOrder` reuse: it is share-quantity and operator-rule shaped (`rule_id`, `rule_revision`, `rule_name`, `trigger_price` required). New optional fields (book id, session date, cost, fill status) can be appended with defaults (frozen dataclass, keyword construction everywhere) **but** `OrderBook.snapshot()` (194–210) and `restore()` (212–234) enumerate fields explicitly — a field not added to both is silently lost on restart. `order_id(book_or_rule_id, revision, sequence)` gives the deterministic id per (book, revision, session ordinal).
- Costs: "Every simulated fill is charged the pre-registered cost, with the tick floor applied (P10)" (SPEC:1177). No cost concept exists in `orders.py`; the cost table itself lives with the gate (`core/quant/backtest.cost_per_side`, TASK-M0-12), so the fill result carries the charged cost and the ledger applies it.
- `core/markets.Session` has no closing-call, random-end or LP-duty metadata (TASK-M5-10 assigns these to `core/markets`); `Market`/`Session` are frozen dataclasses with positional construction in `_MARKETS` — add keyword fields with defaults at the end.
- Tech-fund invariants landing on the same function: INV-1 (decide at close t, fill at the KRX official close of t; never NXT or after-hours prints; R3:132–137) and INV-2 (no entry at a locked limit-up close; an exit at a locked limit-down close carries to the first unlocked session **at 2× cost**; VI, circuit-breaker and halt days unfillable; R3:139–144) extend the `NonFillable.reason` vocabulary beyond R-27's `non_fillable_limit_lock` — keep `reason` an open string/enum that can take both sets.

### D.7 Evaluator hooks: BLOCKED decisions and the R-08 annotation (TASK-M5-06, M5-07; SPEC:1079–1080, 1183; tests I-04, I-06, T-ANNOT-01)

What exists: `Outcome` has no `BLOCKED`. `Evaluator.evaluate` has no injection point between "conditions met" and "place".
```python
def evaluator_block(rule_id: str, decision: Decision, state: MacroState) -> Decision    # -> BLOCKED(reason), new entries only
def evaluator_annotate(rule_id: str, state: MacroState) -> Annotation                    # R-08: annotation + KIS snapshot request
```
Attach in `core/engine/evaluator.py`: add `Outcome.BLOCKED = "blocked"` (safe: `runtime._restore` wraps `Outcome(raw["outcome"])` in try/except; `ui/trading_page.OUTCOME_STYLE.get(...)` has a fallback; add a style row for it anyway). `evaluator_block` as a module-level pure function mapping a would-act `Decision` to `Decision(outcome=BLOCKED, reason=…)` while an R-10 event window or the −12% step is active; holds and exits are never blocked; nothing is written to the book for a block (it is not a cap refusal). `Decision` is frozen with explicit persistence in `runtime._persist` (371–374) — any new field (e.g. an annotation) must be added there and in `_restore` or it is not journalled. R-08 is an annotation only: "no book's exposure changes" (SPEC:1183).

### D.8 Naming collisions and identifier maps

| Existing | v2 term | Resolution |
|---|---|---|
| `core.rules.Rule`, `Decision.rule_id` (12-hex operator id) | §7.1 rule object, `rule_id` like `R-06` | separate class (`RuleObject`); never store `R-xx` objects in `rules.json` |
| `validate(rule)` | rules-store validation of rule objects / card headers | new function names; keep `validate` |
| `RuleStore` / `rules.json` `"version": 1` | "rules store" `version: "2.0.0"` | second store/file |
| `RuleStore.history` ("edit history") | "the store's edit history is the revision log" (SPEC:4128) | new append-only log |
| `EngineMode` (global) | per-book `engine_state` | reuse enum, new per-book class |
| `HaltReason` | `halt.class` (`RISK`/`OPS`) + `reason_code` | separate fields |
| `EngineState.acknowledge()` (required) | "operator's acknowledgement is logged but never required" (SPEC:1179) | different objects; do not merge |
| `Outcome.REJECTED` (cap refusal) / `OrderStatus.REJECTED` | gate verdict `REJECT`; DNB "refused" | do not reuse `REJECTED` for validation refusals |
| `Outcome.HALTED` (global engine halted during this evaluation) | book `HALTED` | distinct |
| venue codes `KRX`, `US`, `TSE`, … (`Rule.market`, `core.markets`) | market ids `KR`, `US`, `JP`, …, `CRYPTO`, `FX` (SPEC:1036: "venue codes … used only inside core/markets") | explicit map needed; `US` is both a venue code and a market id; `NYSE` in `fill_model` is neither an existing code (`US`) |
| `SimulatedOrder`, `OrderBook.fill` | `SimOrder`, `SimFill` (SPEC:1087) vs `Fill`, `NonFillable` (SPEC:2893) | see Ambiguities A-4 |
| `Limits.max_triggers`, `Rule.trigger_count` (persisted in `rules.json`) | "`core/engine/state` persists trigger counts" (SPEC:1187) | spec sentence is not how the code works today; card switch counts are new state |
| DNB item ids `1…37` (ints, SPEC:4623–4661) | `DNB-TF-01…17` (R3:1307, XS-19) | make the item key a string |

### D.9 Constraints checklist for implementers
- Frozen dataclasses throughout (`Rule`, `Limits`, `PriceCondition`, `CancelCondition`, `Issue`, `Report`, `Transition`, `SimulatedOrder`, `Quote`, `Decision`, `Session`, `Market`): mutate only via `dataclasses.replace`.
- No financial default on any new model field; no message that suggests a value.
- All timestamps tz-aware UTC; every new function takes `now`/`decision_utc` explicitly.
- Every `open()`/`read_text()`/`write_text()` passes `encoding="utf-8"`; JSON dumps `ensure_ascii=False`.
- Flet 0.85.2 guard applies to any new control in `ui/*.py` (`page.show_dialog`/`pop_dialog`, `ft.Dropdown(on_select=…)`, `page.on_resize`); palette tokens must exist in `core.theme`.
- No order, cancel, withdrawal, deposit-address or transfer path and no broker adapter, "even behind a flag" (TASK-M0-01; SPEC:1257). §3.10 is a constraint list, not a design.
- The T-RO-01 static scan must allow the simulated book's own method names (`OrderBook.place/fill/cancel/reject/cancel_all_open`, `ui/trading_page.fill_order/cancel_order`, `Evaluator.sweep_cancellations`): a naive token scan for "order"/"cancel" flags `core/engine` itself.

### Ambiguities (source silent or contradictory; conservative reading stated)

| # | Issue | Lines | Conservative reading |
|---|---|---|---|
| A-1 | Existing engine contract "never re-arms itself; acknowledge required; mode not restored" vs v2 automatic DISARMED→ARMED and automatic RISK/OPS re-arm, with book state persisted | `state.py:1–21`, `engine/test_02–04,78`; SPEC:1179–1180, 1187 | v2 semantics apply to the **new per-book runtime only**. `EngineState` and the operator engine are unchanged. No operator rule is ever armed automatically. |
| A-2 | "A global failure (… the `core/engine` QuoteFeed) HALTs every book that reads it; it never HALTs 'the engine' as such" vs the evaluator halting the global `EngineState` on stale/missing quotes | SPEC:1178; `evaluator.py:186–191` | Leave the operator engine's global data halts in place (they stop only operator rules; no exposure). Per-book hooks never touch `EngineState`. |
| A-3 | Where the v2 rules document and `governance_events.jsonl` live: SPEC says "`core/rules` JSON store", "the trading directory for the rules JSON" and "macro artifact directory (**proposed**)"; `config_hash`/`definitions_md5` imply a repo-committed file | SPEC:4126, 4096, 4681 | Ship the canonical v2.0.0 document as a read-only data file in the repo (hashable); keep mutable state (owner rulings, revision log, governance log, book states) under a `config` path with an env override; tests always pass explicit temp paths. Never write to `~/.nextgen/trading/rules.json`. |
| A-4 | Fill API named two ways: `simulated_fill(order: SimOrder, venue: str, session_date: date) -> SimFill` vs `fill_model(venue) -> FillModel`, `simulate_fill(order, session) -> Fill | NonFillable(reason)` | SPEC:1087 vs 2893 | R-27's names bind ("the rule texts bind any detail not shown here", SPEC:963); export one alias for the §3.5 name. |
| A-5 | `prev_row_md5` = "md5 of the previous line": newline included or not, and whether the hash is of raw bytes or canonical JSON | SPEC:4096, 4110 | md5 of the previous line's exact UTF-8 bytes **without** the trailing `\n`; lines written in canonical form (SPEC:4683) with `\n` only; the verifier re-hashes raw bytes (so any hand edit breaks the chain). |
| A-6 | "Literal copy that differs from its key is refused": the spec does not say how a literal is recognised as a copy | SPEC:4130, 5672 | Check exactly the canonical key and every path in `owner_decisions.D<n>.refs`; anything else is not a copy. |
| A-7 | D4 `options: [tighten_only_le_0p10]` is a constraint token, not a value list (default `0.10` is not a member); D2 option `"-1.5*sigma_book"` is a string formula | SPEC:4142, 4146 | Do not enforce `value ∈ options` generically. D4: accept only `value <= 0.10`. D2 formula option: refuse to evaluate until its `σ_book` definition is implemented (SPEC:1586); default −0.15 stays. |
| A-8 | `evaluator_block` on "new-entry decisions; holds and exits never blocked": the operator engine has no positions, so entry vs exit is undecidable for an operator `Rule` | SPEC:1183, 5691; I-06 | Apply BLOCKED to macro-book new-entry decisions where the caller states `is_new_entry`. Do not change operator-rule firing without an owner instruction (simulated practice orders carry no exposure). |
| A-9 | Heartbeat trigger "feed heartbeat loss > 60 s during a session … re-arms once restored for 5 minutes": `QuoteFeed` records no success timestamp and is polled only while the operator engine is ARMED with active rules | SPEC:1178; `feed.py`, `runtime.py:240–252` | Heartbeat is undefined when nothing polls; treat as "not measured" (no HALT, labelled), and apply the trigger only to books with intraday simulated entries once a poller exists. Needs an owner/council reading before M5-04. |
| A-10 | "Refusal … is logged in the store's edit history, and nothing is written": the history is itself a write | SPEC:6231 | The refusal record goes to the append-only revision log; the object map and its file are not modified. |
| A-11 | XS-19 cites "Section 10 DO-NOT-BUILD (items 1-26)" and overlaps with items 14, 26, 11, 13; v2.0 has items 1–37 with 1–26 keeping v1.2 numbers | R3:1307; SPEC:6044–6045 | Add `DNB-TF-01…17` as separate string-keyed items; do not renumber; verify each claimed overlap against SPEC §10.2 text before merging any. Proposal status only (owner confirms). |
| A-12 | XS-08 ladder proposal (re-arm at 0.5, reference peak reset, total book NAV, non-cumulative) vs SPEC R-07/R-31 | R3:1296; SPEC:1586–1587 | Consistent with v2 as written; no code difference. v2 text governs the numbers (10-session refusal, 0.5 cap for 10 decisions). |
| A-13 | D1/D2 ruling timing while a book is HALTED or near its stop is an open owner question | SPEC:5462 | A ruling is recorded with `effective_from`; do not apply it to a HALTED book's references until the owner answers. |

---

## E. Gotchas (verified in code; items marked ▶ were reproduced in memory on 2026-10-05)

1. ▶ **A rule rejected once is stuck until its revision changes.** A cap REJECTED order is written under the trigger's deterministic id; `trigger_count` does not advance; the next pass hits guard 7 (`book.exists(oid)`) and returns SKIPPED `trigger 1 already placed as …` forever, even when the cap would now pass (e.g. the next day's daily cap). Only an `edit()` (new revision) or `reset_practice()` frees it. No test covers the third evaluation.
2. **Silent data loss on load.** A row that fails `from_dict` is skipped; the next `save()` rewrites the file from memory, permanently erasing it. A corrupt `rules.json` loads as empty and is overwritten by the next save. Writing any non-`Rule` object into `rules.json` therefore destroys it.
3. **Silent write failure.** `RuleStore._flush` and `EngineRuntime._persist` swallow every exception; a locked or read-only target (antivirus, sync client) yields no error and leaves an orphan `*.tmp` beside the file. Unacceptable for the governance log and book state.
4. **History is not an audit trail.** Capped at 50 per rule; removed by `delete()` and `clear()`; status changes, confirmations and trigger counts leave no entry.
5. ▶ **`EngineState.disarm()` while HALTED clears the halt** (`requires_manual_rearm = False`) without `acknowledge()`; `arm()` then succeeds. The UI hides Disarm while `needs_ack`, but `EngineRuntime.disarm()` is public. ▶ `acknowledge()` while ARMED silently disarms. ▶ After a restart with an unacknowledged halt: `mode == DISARMED`, `describe() == "DISARMED"`, `requires_manual_rearm == True` — the banner shows no halt reason (it prints one only when `mode is HALTED`).
6. **`max_daily_amount` is not per rule.** `_cap_refusal` compares this rule's cap with `book.notional_today()`, the sum over **all rules and all currencies** (KRW and USD notionals added unconverted), by **UTC date**.
7. **Mixed clocks.** `dashboard()` counts "today" with `datetime.now()`, `SimulatedOrder.age_seconds` and `OrderBook.counts_today/notional_today` default to the wall clock, while `_venue_status`, `_degraded` and `tick` use the injected clock. Pinned-clock tests of new code must pass `now=` everywhere.
8. **Quotes are keyed by symbol only.** `fetch_many` returns `dict[symbol]`; two rules with the same symbol on different venues share one quote, one miss count and one `previous` (`engine/test_86` pins the miss behaviour).
9. ▶ **An ACTIVE rule with `side=None` fires** (nothing validates on `save` or `with_status`), and `OrderBook.snapshot()` then raises `AttributeError` inside `_persist` — outside its `try` — which surfaces as an `UNKNOWN_STATE` halt from the loop, or as an exception in a UI handler.
10. `_persist` builds its payload (iterating the decision deque and the book) outside the `try` and without the runtime lock; `ui/trading_page.py` calls the private `runtime._persist()` from the UI thread.
11. `orders.py` docstring (line 21) cites `guards.py`; no such module exists (the guards are in `evaluator.py`). `trading_page.py:383` and `core/calendars.py:4` cite `pkg_tools/generate_calendars.py`; no `pkg_tools/` directory exists in the repository.
12. `EngineRuntime` docstring says "the loop runs only while armed": the daemon thread keeps waking every `tick_seconds` after a disarm (it makes no request); `stop()` only sets a flag. Each test constructing a runtime must call `runtime.stop()` (they do, in `finally`).
13. `runtime.on_update` is a single slot overwritten on each rebuild of the trading page (rebuilt on every navigation); a second listener (e.g. a Macro-page book panel) would silently replace the first.
14. `HaltReason.LIMIT_BREACH` and `PROVIDER_ERROR`, `RuleStatus.EXPIRED`/`CANCELLED`, `Rule.activate`, `can_confirm`, `OrderBook.cancel_all_open` are defined but never produced or called by application code.
15. `core.markets` trading windows are regular hours only; no closing-call window exists (KRX `09:00–15:30` as one window), and calendar coverage is finite (`is_trading_day` returns `None` beyond it; `trading_state` then falls back to the weekly pattern with the note `outside calendar coverage; using regular weekly hours`).
16. **README is stale on test counts** (`README.md:347` "229 checks", `:379` "245 checks"; actual 266) and describes the engine surfaces as "unchanged" NEXTGEN (`:327–330`) — consistent with the code. Service-contract section marks (`§2`, `§3`, `§5`, `§7`) in docstrings refer to the NEXTGEN client contract, not to the v2 spec's sections.
17. Windows/cp949: the default text codec on this machine is cp949; em dashes and Hangul appear in decision reasons, provider labels and `describe()` strings. `run_all.py` reconfigures stdout; any new CLI entry point or file write must do the same / pass `encoding="utf-8"`. Text-mode writes translate `\n` to `\r\n` (breaks byte hashes). The repository sits under OneDrive; mutable state belongs under `~/.nextgen` (not synced), as today.
18. `tests/engine_acceptance.py::test_82` opens a real loopback HTTP server; a T-HERM-01 style "all sockets raise" guard applied suite-wide would fail it. `test_21` reaches into `book._orders`.
19. `config` constants are read at import; setting `NEXTGEN_*` after `import config` has no effect — tests inject via constructor arguments, never via env.
20. The spec's description of `core/rules` ("immutable model, no financial defaults, validation, one JSON store with edit history", SPEC:916) is accurate for the operator `Rule`; its statement that the store's edit history "is the revision log" (SPEC:4128) is aspirational (gotcha 4).
