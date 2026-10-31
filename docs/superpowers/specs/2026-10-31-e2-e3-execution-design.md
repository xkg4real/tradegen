# E2 execution control and E3 venue adapters

Date: 2026-10-31 (Asia/Seoul).
Status: implementation contract for the owner's instruction to build E1 through E3. Development is authorized;
real account setup, signatures, session arming and live operation are separate owner actions. This document is not
evidence that its implementation or venue validation has passed. The execution ledger records actual completion.

Inputs: [main compliance design](2026-10-23-compliance-gate-and-odds-engine-design.md),
[E1 plan](../plans/2026-10-24-e1-account-inquiry.md), and
[equity-policy candidate](2026-10-30-equity-policy-and-strategy-design.md). Owner financial parameters remain private.
This is software design, not legal, tax or investment advice. Neither the software nor its author is a licensed advisor.

## 1. Boundaries and sequence

E1 remains a read-only inquiry package. E2 adds control and a simulated adapter; E3 then adds venue codecs and one
authenticated transport, in the order Upbit, KIS, OKX. Each stage is reviewed and tested before dependent work is
reported complete. Development can continue on reviewed feature commits; an intermediate PR merge is not a new
development prerequisite. PR merges still need the owner's explicit approval.

The first supported execution subset is cash-funded, long-only, single-leg limit orders on approved instruments:
Upbit KRW spot, KIS KRX and US shares/plain 1x ETFs, and OKX spot. Unsupported order types, venues, products,
financing, routes and extra payload fields are refused. No withdrawal, transfer, credit, loan, derivative, batch,
algorithmic or cancel-and-replace route is added. A cancellation never implies that the order stopped filling.

The implementation must distinguish: code complete; mock protocol tests passed; owner configured; signed/armed;
and actually exercised against a venue. None of these states implies the next one. No live API call is made while
developing or running acceptance tests.

## 2. Modules and trust boundary

| Package | Responsibilities |
|---|---|
| `execution/` | Existing E1 inquiry, immutable snapshots, live positions and evidence; its transport stays read-only |
| `execution_control/model.py` | Frozen order and instrument-rule value types; exact validation and canonical digests |
| `execution_control/store.py` | One exclusive control lock, append-only journal, replay validation and durable reservations |
| `execution_control/risk.py` | Pure Decimal policy evaluation and fill accounting; no I/O or clock |
| `execution_control/session.py` | Fresh-seed plan confirmation and binding to a signed owner session |
| `execution_control/controller.py` | Reservation, fresh-context gate checks, dispatch, reconciliation and kill handling |
| `execution_control/dry_run.py` | Deterministic simulated adapter; it never imports the live transport |
| `execution_orders/model.py` | Frozen prepared-request/result types and strict request integrity checks |
| `execution_orders/upbit.py`, `kis.py`, `okx.py` | Pure strict payload generation and response interpretation |
| `execution_orders/transport.py` | Typed credential-provider boundary, sole execution HTTP path, authentication and bounded single sends |

Module names are the integration contract; a reviewed implementation may split helpers without creating an alternate
send path. Runtime scans and D14 owner/signer seed lists include both new packages recursively. Keep E1's complete
read-only scan. Extend the repo's existing broad read-only checks only with exact reviewed E3 file/token exceptions;
retain negative tests proving those tokens fail everywhere else. Add an E2/E3 guard suite for import restrictions,
send-path uniqueness, credential access, forbidden transfers, checked writes and signature coverage. Do not skip the
new packages or delete the old tests to make orders possible.

The control layer imports only standard-library code, `core.isolation`, compliance, odds, and the documented E1
snapshot/positions helpers. Pure risk and codec modules import neither keys nor HTTP clients. Only the execution
transport imports `requests`. A separate typed credential provider supplies trading credentials at dispatch time;
it is never E1's read-only credential reader. The shipped unconfigured provider refuses. Its objects suppress secret
values in repr/str, and credentials never enter requests' public diagnostics, journals or exception messages.

This is an application discipline inside signed Python code, not a sandbox against a malicious process with the
same user's filesystem and interpreter access. Hash chains detect alteration; they do not authenticate an attacker
who can replace the full writable history.

## 3. Frozen integration interfaces

All public data objects are frozen, keyword-only dataclasses. Numeric business inputs are finite `Decimal` values
or canonical decimal strings, never floats or booleans. The implementation exports these roles:

| Name | Required contract |
|---|---|
| `Order` | `client_id`, opaque `account_scope`, `venue`, `market`, `symbol`, `side` (`buy`/`sell`), `quantity`, `limit_price`, `quote_krw`, `time_in_force` (`gtc` for Upbit/OKX, explicitly `day` for KIS); all wire-affecting fields belong to its digest |
| `InstrumentRules` | Approved venue/instrument identity, lot and tick increments, minimum quantity/notional, supported quote currency, fee reserve, provenance and as-of instant |
| `Fill` | Stable venue/account/order/fill identity, execution UTC, side, quantity, price, quote-to-KRW rate and explicit fee amount/currency; no inferred zero fees |
| `RiskPolicy` | Versioned private principal/peak/daily rules, valuation convention and explicit first/zero-day allowance or unresolved status |
| `RiskObservation` | Reconciled marked equity, high-water mark, day-opening equity, prior/current realized net results, externally selected daily-loss measure, effective floor, data/flow completeness and as-of instant |
| `RiskResult` | Entry eligibility, reasons, requested/effective floor, deferred relaxation, budget/target diagnostics and whether protective action is needed; never an execution permit |
| `PreparedRequest` | Venue, operation, fixed method/path, exact ordered query/body fields, expected response identity and order digest; no credentials |
| `AdapterResult` | `accepted`, `rejected`, `unknown` or reconciled terminal state, sanitized code, venue order ID and matched client identity; acknowledgment is not a fill |

The callable boundary is `prepare(order, rules) -> PreparedRequest`, `parse(response, request) -> AdapterResult`,
and a controller-owned adapter `dispatch(request, capability, *, now) -> AdapterResult`. Credentials are resolved only
after request/capability validation. The controller creates the one-use, process-local capability after its durable
pre-send transition. A caller-supplied boolean or hand-built object is not a capability. Mutating an order, permit,
request or nested value after creation is detected by recomputing canonical digests immediately before dispatch.

Each control operation takes an explicit aware `now`; no risk or codec function reads a clock. The runtime runner
owns clock sampling. Unknown fields and malformed persisted values fail closed. Adapter implementations must not
round a quantity or price silently: either the controller selects a valid smaller lot under the approved policy and
re-authorizes that exact order, or the request is refused.

## 4. Session preparation and arming

### Integration signature freeze (v1)

The builders share the following names. Private helpers may vary; changing a signature requires one recorded
integration decision. `Mapping` inputs are copied/frozen before hashing, never retained as mutable caller state.

```python
# execution_control/model.py (store/model builder owns)
@dataclass(frozen=True, kw_only=True)
class Order:
    client_id: str
    account_scope: str
    venue: str
    market: str
    symbol: str
    side: str
    quantity: Decimal
    limit_price: Decimal
    quote_krw: Decimal
    time_in_force: str = "gtc"

@dataclass(frozen=True, kw_only=True)
class InstrumentRules:
    venue: str
    market: str
    symbol: str
    lot_size: Decimal
    tick_size: Decimal
    min_quantity: Decimal
    min_notional_krw: Decimal
    fee_fraction: Decimal
    asof: datetime
    source_digest: str

def order_digest(order: Order) -> str: ...
def rules_digest(rules: InstrumentRules) -> str: ...
def validate_order(order: Order, rules: InstrumentRules) -> None: ...
# Validation raises a sanitized ValueError; it never adjusts an order.

# execution_control/store.py (store/model builder owns)
class Journal:
    def __init__(self, root: Path | None = None): ...
    def transaction(self) -> ContextManager[Transaction]: ...

class Transaction:
    @property
    def events(self) -> tuple[dict, ...]: ...  # detached canonical row copies
    def append(self, kind: str, data: Mapping, *, now: datetime) -> dict: ...

# execution_control/risk.py (risk/controller builder owns all risk dataclasses)
def evaluate(policy: RiskPolicy, observation: RiskObservation) -> RiskResult: ...
def account_fills(fills: tuple[Fill, ...]) -> AccountingResult: ...

# execution_control/session.py
def prepare_session(*, journal, session_id, selected_plan, inputs, positions,
                    policy, instrument_rules: InstrumentRules, now: datetime,
                    selection_seed_hex, account_scope, market, quote_currency,
                    expires_at: datetime | None = None) -> PreparedSession: ...
def verify_session(prepared, *, session_id, policy, instrument_rules: InstrumentRules,
                   ctx, now: datetime, order, events) -> None: ...

# execution_orders/model.py (venue builder owns)
@dataclass(frozen=True, kw_only=True)
class PreparedRequest:
    venue: str
    account_scope: str
    operation: str                # "create", "cancel", "status"
    method: str
    path: str
    params: tuple[tuple[str, str], ...]
    body: tuple[tuple[str, str], ...]
    order_digest: str
    client_id: str
    headers: tuple[tuple[str, str], ...] = ()  # nonsecret allowlist, e.g. KIS tr_id
    expected: tuple[tuple[str, str], ...] = ()  # canonical bound business fields
    metadata: tuple[tuple[str, str], ...] = ()  # validated broker/date/cancel context

@dataclass(frozen=True, kw_only=True)
class AdapterResult:
    status: str                  # accepted/rejected/unknown/open/partial/filled/canceled
    code: str
    venue_order_id: str = ""
    client_id: str = ""
    metadata: tuple[tuple[str, str], ...] = ()
    filled_quantity: Decimal | None = None
    average_price: Decimal | None = None
    fee: Decimal | None = None
    fee_currency: str = ""

# Each execution_orders/{upbit,kis,okx}.py exports:
def prepare(order: Order, rules: InstrumentRules) -> PreparedRequest: ...
def prepare_cancel(order: Order, venue_order_id: str, *, broker_org_id: str = "", remaining_quantity: Decimal | None = None) -> PreparedRequest: ...
def prepare_status(order: Order, venue_order_id: str, *, order_date: str = "", broker_org_id: str = "") -> PreparedRequest: ...
def parse(response: Mapping, request: PreparedRequest) -> AdapterResult: ...

# execution_orders/transport.py
# Provider is a callable (venue, account_scope) -> repr-safe credential object. The transport
# never imports execution.keys, and no provider is invoked during pure prepare.
def dispatch(request: PreparedRequest, capability, *, credentials, now: datetime) -> AdapterResult: ...

# execution_control/controller.py (risk/controller builder owns)
class Controller:
    def __init__(self, *, journal, account_provider, policy, adapters, session_provider): ...
    def reserve(self, order: Order, rules: InstrumentRules, *, session_id: str, now: datetime): ...
    def dispatch(self, client_id: str, *, now: datetime): ...
    def cancel(self, client_id: str, *, now: datetime): ...
    def reconcile(self, client_id: str, *, now: datetime): ...
    def kill(self, session_id: str, *, reason: str, now: datetime): ...
    def observe(self, *, now: datetime): ...
    def approve_floor_relaxation(self, *, floor: Decimal, now: datetime, session_id: str): ...
    def halt(self, *, floor: Decimal, now: datetime): ...
```

The controller constructor takes a Journal, account-observation provider, risk policy, adapter map and session
confirmation provider explicitly; none has a live default. Account observations contain sealed-context inputs,
exact available settled cash, risk observations, no-credit status and a fresh timestamp. The implementation must
document the final constructor before integration tests. Adapter `dispatch` accepts only a capability validated
by the process-local registry and bound to the exact request digest. The controller alone imports the issuance
helper; the transport imports only the consuming helper from `execution_control.capability`, avoiding a controller
or transport import cycle.

`AccountObservation.held_exposure_krw[(venue, account_scope)]` supplies exact independently reconciled Decimal
exposure. Admission compares the venue's held exposure, every active buy reservation and the proposed buy,
including their fee reserves, with the prepared plan's capital. A session's capital cannot be reused by multiple
simultaneous orders. The exact grey-cap check also runs before the legacy float gate. Exact holdings and exposure
must agree with the legacy gate inputs. Entry refuses nonempty external `Positions.exposure.reservations`, and
reducing exits refuse external `promised_sell_units`; these unsupported promises require manual reconciliation.
Admitted promises are owned by the execution journal; crypto sell promises share the normalized base asset across
quote pairs.

The opaque account scope binds observation, session, order, reservation and credential provider. The provider must
match that binding before dispatch; changing credentials cannot silently select a different account. This binding
contains no raw account number in the audit record. KIS `tr_id` is a nonsecret prepared header and is included in the
request digest because it encodes the side; the transport rejects every unapproved prepared header. Authorization
headers and account fields are added only from the matching credential provider, never caller-supplied overrides.

Market tokens are frozen as `spot` for Upbit/OKX, with full-pair `symbol` values such as `KRW-BTC` and `BTC-USDT`;
KIS uses lowercase `krx`, `nasd`, `nyse`, `amex`. The controller derives the matching approved compliance instrument
and quote; it must not confuse wire pairs with base-asset holdings keys. KIS broker organization ID comes from the
stored matched venue answer. Status `order_date` comes from explicit reconciled venue trade dates (`YYYYMMDD`), not
an assumed Seoul date for US trading. Missing necessary metadata refuses that route. These are explicit interface
rulings agreed with the builders, superseding earlier proposed uppercase-market/base-symbol conventions.
KIS cash limit orders require explicit `time_in_force="day"`; the model's default `gtc` is not a claim that the KIS
wire supports good-till-canceled orders. Upbit and OKX support the `gtc` limit subset here. This is the root's
protocol-alignment ruling, not a silent coercion of the requested time in force.

Journal event kinds are `session_prepared`, `reserved`, `dispatching`, `acknowledged`, `rejected`, `unknown`,
`expired`, `cancelled_local`, `cancel_requested`, `reconciled`, `fill`, `risk_snapshot`, `kill` and `halt`.
Every order event carries `client_id` and the immutable order digest; only `reserved` introduces an order body.
The lifecycle fold rejects an event inappropriate for the prior state, contradictory terminal outcomes, a fill
without the known venue order identity, and an attempt to reuse an ID. The journal helper validates structural
integrity; the controller's fold validates lifecycle semantics before any transaction performs an effect.

Cancellation has its own one-use capability and operation binding; it does not reuse a create permit or fabricate
a `cancel` compliance Intent. The controller derives the cancellation from a known stored order and matched venue
ID, permits it only to reduce outstanding exposure, and journals it before sending. It requires no new-entry
arming approval, but cannot target an arbitrary externally supplied venue ID. Its acknowledgment retains the
original order reservation until status/fills prove the remaining quantity terminal. No quantity/price amendment
is represented as a cancellation.

`AdapterResult.status` alone cannot release a reservation. The final adapter result may carry immutable normalized
broker metadata and cumulative fill/fee quantities; the controller requires authoritative accounting reconciliation
for all executed quantities before release. Missing or contradictory fill/fee information remains unresolved even
when a status response calls the order filled or canceled. KIS uses the full remaining-cancel route; partial-size
amendment is outside this interface. Its explicit cancellable quantity must be authoritative and matched to a
successful reconciliation within five seconds. A cancel acknowledgment or unknown result keeps cancellation
pending; it never permits a repeated cancel POST without authoritative reconciliation.

When status supplies a cumulative average price, reconciliation also requires
`sum(fill.quantity * fill.price) == cumulative_quantity * average_price`. A conflicting or unsupported rounded
average retains the reservation; no broker rounding tolerance is invented. An omitted average can be reconciled
from the complete authoritative ledger's explicit prices and fees.

`prepare_session` accepts the selected odds plan and complete explicit odds inputs, generates a new comparison ID,
and actually invokes the odds engine. Its market seed must differ from the selection run's seed. Retain the result's
plan/input/code/state digests, seed and timestamp in the preparation record. A caller-provided `passed=True`, a copy
of the selection report, or a hand-authored probability is insufficient. A refusal, critical model diagnostic,
stale data, invalid calendar or mismatched plan blocks preparation. The comparison result does not promise profit.

Preparation writes no signed owner entry and does not arm anything. An entry session must then be present in the
verified owner's `session_armed` set, have a nonempty matching session ID, current code approval, required warning
acknowledgments, and configured limits. E2's local binding ties that session ID to the exact preparation and policy
version. Session expiry/day rollover, kill, code changes, broken evidence and preparation mismatch block new entries.
Do not reuse an old owner's session acknowledgment for another session or another warning hash.

The `session_id` input to `prepare_session` is a validated label of at most 32 characters. The returned
`PreparedSession.session_id` is that label plus the full 64-hex digest of all immutable preparation fields except
the ID and record digest. The owner signs the returned content-derived ID, not the input label. Verification
recomputes that ID and compares the original immutable registry digest, so changing policy, plan, account, seed,
expiry or other preparation evidence cannot retain an old owner acknowledgment.
The supplied `InstrumentRules` digest is part of that signed preparation identity. Changing fee reserves, lots,
ticks, minimums or rules provenance requires a fresh preparation and owner acknowledgment; entry verification
compares the exact rules before authorizing the order.

The controller always calls `owner.load_context`; it never hand-seals a production Context. The gate currently does
not itself enforce an armed session or consume a permit. E2 must enforce both independently. Tests may use the
existing temporary signed-home fixtures and fake keys; they never sign real owner data.

## 5. Durable state, reservation and dispatch

State belongs under `state_root()/execution-control/`, with checked targets for the directory, journal, lock,
checkpoint and every temporary file. Reuse a reviewed cross-platform exclusive lock. Journal rows have schema
version, monotonically increasing sequence, previous hash, event kind, UTC and canonical payload. Write, flush and
fsync before advancing. Replay verifies both chain and legal state transitions, not just valid JSON.

The reservation lifecycle is:

`RESERVED -> DISPATCHING -> ACKNOWLEDGED | REJECTED | UNKNOWN -> reconciled terminal state`.

Before dispatch, `RESERVED` may become `EXPIRED` or `CANCELLED_LOCAL`. A `DISPATCHING` row found after restart is
`UNKNOWN`, not an unsent request. One client ID always denotes one immutable order, including after expiry or
completion. Duplicate creation with the same digest returns its existing state; a different digest is refused.

Under the same control lock, reservation reads the latest valid E1 positions, incorporates all outstanding buy
notional/fee reservations and sell-unit promises, evaluates policy, loads a fresh Context, and calls `gate.permit`.
It stores the full immutable order digest and permit fields/digest. A persisted permit is not reconstructed into an
issued gate permit after restart: stale reservations must be reauthorized before their first send or abandoned.

At send time, under the lock, rebuild exposure and reload Context. Exclude only this reservation's own amounts as
the gate contract requires; never exclude another reservation sharing a symbol. Verify order and permit integrity,
session/date/deadline, fresh prices/balances, exact free cash/units, live fee reserve, policy and `gate.verify_permit`.
Then durably mark `DISPATCHING`, consume the capability and perform at most one bounded transport attempt. Holding
the lock through that bounded attempt is acceptable for this single-account implementation; its timeout bounds how
long another control operation waits. An out-of-process kill cannot reverse an already delivered venue request.

Timeout, disconnect, malformed success, mismatched identity, ambiguous venue error or failure to persist the result
leaves `UNKNOWN`. Retain its cash/unit capacity until authoritative reconciliation proves what happened. Never retry
an order POST because the reply was lost. A cancellation acknowledgment does not release capacity until the final
order/fill state is reconciled; partial fills update inventory and remaining reservation exactly once. Broker IDs
are venue-scoped and may not be attached to a different local client ID.

Before any new entry after restart, reconcile all nonterminal orders. A torn tail, missing checkpoint anchor,
truncated history, duplicate contradictory fill or impossible state blocks new entries and raises a sanitized
diagnostic. Preserve the damaged evidence; do not repair a broken owner or control log by deleting its tail.

## 6. Risk, accounting, exits and kill

Implement the parameterized formulas from the equity-policy design without copying private values. Positive
prior-day realized net profit yields its configured fraction as the next daily budget. A prior loss blocks new
entries; verified zero profit and absent history remain distinct. The first-session exception is one-time persisted
state, not a restart flag. Unspecified first/zero-day budgets remain unresolved, not zero or unlimited.

Use a persistent lifetime equity peak. Below activation protect that peak; after activation compute the configured
drawdown floor with the principal lower bound. A calculated lower floor never lowers the effective floor without
the approved D12 transition. Per the owner's latest correction, the new E2 monitor breaches only strictly below
the effective floor: equality alone neither prohibits entry nor causes a halt. Keep the signed numerical floor
and daily cap in force; the old odds `floor_safe` cash-reserve invariant is unchanged. A separately identified
policy conflict may block entry, but equality alone is not evidence of such a conflict. A reviewed, explicitly
approved D12 loosening applies only on the next eligible Seoul day, disarmed and without a recorded halt; it is
never inferred solely from crossing the peak-activation threshold. Persist both daily-stop and lifetime-halt state.

Targets use realized net profit over day-opening equity. Missing a target never enlarges a budget, increases order
size or overrides a stop. Account marking and realized P&L are separate. Implement deterministic FIFO acquisition
cost allocation as the initial accounting convention, including entry/exit fees and partial fills; record that
convention, not a claim about tax treatment. Duplicate identical fills are idempotent; contradictory duplicates,
missing fees/FX, unaccounted transfers and incomplete history require reconciliation. External flows do not count
as trading profit or silently move the high-water mark.

`Fill.order_date: str = ""` is authoritative venue-local `YYYYMMDD` for KIS. Never derive it from UTC execution
time. `Fill.broker_org_id: str = ""` is 1–20 digits for KRX and may be empty for US markets only on authoritative
absence. KIS order identity is `(venue, account_scope, market, order_date, broker_org_id, order_id)`; its duplicate
fill identity adds `fill_id`. Crypto requires both date and organization fields empty and retains
`(venue, account_scope, order_id)` plus `fill_id`. `AccountingResult.order_quantities` rows are
`(venue, account_scope, market, order_date, broker_org_id, order_id, filled_quantity)` so a reused KIS order number
on another branch, market or trading date cannot collide with old fills. Cumulative reconciliation must preserve
already-recorded fill identities and their exact values before releasing any reservation.

Entry risk checks also reserve settled cash including costs. KIS's cash endpoint is not proof that no margin will
be used: require verified no-credit account settings and sufficient reconciled cash, even when the broker would
accept a larger order. Exact Decimal checks precede the legacy gate's finite float interface. A rounded cap breach
is still a refusal; reduce and reauthorize a valid lot, never soften the gate comparison.

A kill request first persists a local no-entry latch, then records `system_disarm` when the owner log is writable.
A genuine hard-floor halt records `system_halt` and survives restart. If that append fails, keep the local latch
and report the failure. H2: compare the writer's timestamp with recent server time and the journal's monotone
history, including Seoul-date boundaries. Clock ambiguity blocks entries and preserves a local halt; do not append
a far-future owner event to make a broken clock look valid. Resolving the clock must never clear a halt.

Permitted reducing exits and known-order cancellations remain available under daily stops, disarm and kill, subject
to conduct checks, verified holdings, exact outstanding sell promises and `gate`'s approved-snapshot recovery rule.
Corrupt execution reservations cannot be guessed away to auto-sell; if free units cannot be established, report the
need for manual venue handling. Neither a stop nor a cancellation guarantees that equity remains above a threshold.

## 7. E3 protocol requirements

All hosts are fixed HTTPS production hosts; caller-supplied URLs, redirects, proxies, arbitrary methods/paths and
extra fields are refused before keys are fetched. The send seam creates a `requests.Session` with `trust_env=False`,
uses a bounded timeout and `allow_redirects=False`. No request carrying order/cancel effects is automatically retried.
GET reconciliation may retry only under an explicitly bounded read policy. Every error uses allowlisted codes and
field names, never raw response text, headers, account identifiers, query strings or credential values.

| Venue | Initial wire contract and evidence |
|---|---|
| Upbit | `POST /v1/orders`, JSON limit request: market, bid/ask, volume, price, ord_type=limit, stable identifier. Authenticate HS512 JWT with a fresh nonce and SHA512 of the exact decoded query representation. Identifier is unique across account history and at most 64 characters. [Official order reference](https://docs.upbit.com/kr/reference/new-order), [authentication](https://docs.upbit.com/kr/reference/auth). |
| KIS KRX | `POST /uapi/domestic-stock/v1/trading/order-cash`; buy `TTTC0012U`, sell `TTTC0011U`; `ORD_DVSN=00`, string quantity/price, `EXCG_ID_DVSN_CD=KRX`, ordinary sale type. [Official sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/order_cash/order_cash.py), blob `f422cf4ebb3029f580eb10294883a82fded610f6`, checked 2026-10-31. |
| KIS US | `POST /uapi/overseas-stock/v1/trading/order`; buy `TTTT1002U`, sell `TTTT1006U`; NASD/NYSE/AMEX, `ORD_DVSN=00`, `ORD_SVR_DVSN_CD=0`. [Official sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/order/order.py), blob `c26154439193fa93cd3ceac88732ae94d4aab48d`, checked 2026-10-31. |
| OKX | `POST /api/v5/trade/order`, cash spot only; explicit instId, tdMode=cash, side, ordType=limit, sz, px and clOrdId. Authenticate the exact timestamp + method + request path/query + body bytes using HMAC-SHA256/base64. Check both top-level code and row-level sCode. [Official trade/auth reference](https://www.okx.com/docs-v5/en/). |

KIS has no assumed request-id deduplication guarantee. Keep uncertain outcomes reserved and reconcile; do not invent
an idempotency header. OKX's open-order client-ID uniqueness also is not an eternal deduplication guarantee; the
local journal never reuses an ID. KIS tokens are supplied through the reviewed trading credential provider, not by
borrowing E1's inquiry transport for POST. Separate credentials do not imply separate brokerage rate limits.

Verified follow-up routes (2026-10-31) are:

- Upbit `GET /v1/order` and `DELETE /v1/order`, identified by UUID or client identifier; use the known ID and verify
  returned identity. [Lookup](https://docs.upbit.com/kr/reference/get-order),
  [cancellation](https://docs.upbit.com/kr/reference/cancel-order).
- KIS KRX cancellation: `POST /uapi/domestic-stock/v1/trading/order-rvsecncl`, `TTTC0013U`, cancellation code `02`;
  preserve original broker organization/order IDs and query cancelable quantity. Status uses the E1 daily-fill
  route `TTTC0081R` with all continuation pages. [Cancel sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/order_rvsecncl/order_rvsecncl.py),
  [status sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/inquire_daily_ccld/inquire_daily_ccld.py).
- KIS US cancellation: the overseas `order-rvsecncl` route, `TTTT1004U`, code `02`, cancellation price `0`; status
  uses `TTTS3035R` with complete continuation. [Cancel sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/order_rvsecncl/order_rvsecncl.py),
  [status sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_ccnl/inquire_ccnl.py).
- OKX `POST /api/v5/trade/cancel-order` and `GET /api/v5/trade/order` require the instrument plus order/client ID.
  Cancellation acceptance is not terminal cancellation; `50004` is an unknown outcome.
  [Official trade reference](https://www.okx.com/docs-v5/en/).

The current [KIS authentication helper](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/kis_auth.py#L268)
documents the hashkey as optional. Do not add an invented HMAC requirement. If hashkey is deliberately used, it
covers the exact body. Current tick/lot/minimum rules, recognized response-state fields and OKX regional host
applicability are supplied as verified configuration/evidence; unknown response shapes fail closed. KIS's first
status page cannot prove an order absent when continuation exists. Live configuration additionally requires the
owner's correct venue/account, trading scope, IP setup, funding/no-credit state and approvals. Static source
research cannot prove those account-specific facts.

## 8. Verification and completion

Tests must exercise the controller and the actual codec/authentication path with captured in-memory fake HTTP
responses, not only compare helpers with themselves. Test reservations racing for the same cash/units; duplicate
IDs; changed price/body/permit/session; midnight and clock rollback; signature/code changes; unknown POST outcomes;
crash windows; reconciliation; partial fills and fees; no-credit cash refusal; loss/peak policy boundaries; exits
after kill; corrupt logs; linked paths; malformed/nonfinite values; and authentication byte-for-byte fixtures.

An end-to-end dry-run scenario starts with a temporary signed owner state, prepares a real fresh-seed odds result,
observes the owner's test-only arming record, admits one order, dispatches once, books partial/final fills, prevents
a duplicate, trips a loss control and still permits a qualified exit. Repeat codec/transport integration for each
venue with fake HTTP only. Demonstrate zero real send calls and unchanged real homes.

Run serial E1, compliance, odds and execution-control/order regression checks, then the full suite. Preserve existing
NOT_RUN explanations; do not relabel unexercised live behavior as PASS. The final ledger identifies all owner-only
setup that remains and any unsupported protocol route. No statistical strategy verdict or profit guarantee is
earned by these software tests.
