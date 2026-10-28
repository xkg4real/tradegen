### Task 6: Upbit inquiry (`execution/upbit_inquiry.py`)

**Files:**
- Modify: `execution/upbit_inquiry.py` (anchors: the module docstring and the `from __future__ import annotations`
  line above `ENDPOINTS = frozenset({`, and the last constant line `PUBLIC = frozenset({"/v1/ticker"})`; LF)
- Modify: `tests/execution_fixtures.py` (anchor: the file's last line, the end of Task 5's `kis_routes()`; LF)
- Create: `tests/execution_upbit.py` (LF, UTF-8, no BOM)
- Modify, only when this task records a drift ruling (Step 1 or Edit 3a):
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (anchor: the `## Deferred minors`
  heading; one line above it, in the `## Drift rulings` section; LF)
- Test: `tests/execution_upbit.py`

`tests/execution_acceptance.py` (Task 1) already lists `"execution_upbit"` in MODULES and skips the module until
this task creates it. From this task on the Upbit token rule of `tests/execution_guards.py` (Task 2) sees the full
`execution/upbit_inquiry.py`: every string in it that starts `/v1/order` or `/v1/withdraw` must be one of
`/v1/orders/open`, `/v1/orders/closed`, `/v1/withdraws` and `/v1/withdraws/coin_addresses`, comments and docstrings
included, so the code names those four paths only as the exact constants below. No CRLF file changes, and no file
outside the three above changes, except the ledger line of a drift ruling.

**Interfaces:**
- Consumes:
  - Task 2 (`execution/upbit_inquiry.py`, contract 7): `ENDPOINTS` (nine `("GET", path)` pairs, `/v1/status/wallet`
    included), `PUBLIC = frozenset({"/v1/ticker"})`.
  - Tasks 2 and 3 (`execution.transport`, contract 6): `request(venue, method, path, params=None, *, tr_id=None) ->
    Answer` (`.body`, `.server_utc`, `.received_utc`, `.sha256`); `AuthError`, `InquiryError`, `InquiryRefused`,
    `KeyMissing`. Transport signs every Upbit path but `/v1/ticker` with an HS512 JWT
    (`Authorization: Bearer <jwt>`, payload `access_key`, a fresh `nonce`, and `query_hash` = SHA512 hex of the
    exact query on the wire plus `query_hash_alg: "SHA512"` when there is one; no `exp`), reads the Upbit keys only
    for a signed call (a missing one raises `KeyMissing` before anything is sent), refuses a signed value that
    quoting would change, raises `AuthError` on HTTP 401/403 or an error name in `AUTH_CODES["upbit"]`
    (`out_of_scope` included), raises `InquiryError` naming venue, path, HTTP status and code (never the venue's
    message) on any other error answer (E15), and lets the router's `AssertionError` through unchanged.
  - Task 4 (`execution.snapshot`): `Address(currency, net_type, address, secondary_address="")`, `FieldError`,
    `Holding`, `Move`, `Order`, `Snapshot`, `failed`.
  - `core.compliance.model` (repo): `iso_utc(moment)`, `KST`.
  - Tests: Tasks 1 to 4 fixtures as in Task 5 (`NOW`, `DATE_HEADER`, `FAKE_KEYS` with `UPBIT_ACCESS_KEY`
    `"test-upbit-access"` and `UPBIT_SECRET_KEY` `"test-upbit-secret"`, `Refused`, `STRAYS` (`"METHOD url-path"`
    rows), `fake_keys`, `serve` (an unrouted call appends to `STRAYS` and raises `AssertionError`)); Task 5's
    `_routes(table, bodies, changes)` (a None change drops that route).
- Produces:
  - `execution/upbit_inquiry.py`: `snapshot(now: datetime) -> Snapshot`. It sends, in this order, the signed GETs
    `/v1/accounts`, `/v1/orders/open` (`states[]=wait&states[]=watch&limit=100`), `/v1/orders/closed`
    (`states[]=done&states[]=cancel&limit=1000`, no time: Upbit's default 7 days), `/v1/withdraws` (`limit=100`),
    `/v1/withdraws/coin_addresses`, `/v1/deposits` (`limit=100`), `/v1/api_keys`, then the public `/v1/ticker`
    with `markets` = the sorted `KRW-<coin>` of every held coin plus `KRW-USDT`. It never calls `/v1/status/wallet`
    (E22). The ok snapshot holds `cash = {"KRW": balance + locked}`, `holdings` (every other currency with
    `balance + locked > 0`: `Holding(units=balance + locked, locked=locked, avg_cost=avg_buy_price if unit_currency
    == "KRW" else None)`), `open_orders` (`Order(id=uuid, symbol=<base>, side="buy" for bid else "sell",
    units=remaining_volume, price=price or None)`), `fills` (closed rows with `executed_volume > 0`:
    `Move(id=uuid, symbol=<base>, counter=<quote>, side, units=executed_volume)`), `withdrawals` (`side="out"`),
    `deposits` (`side="in"`), `withdrawal_addresses` (`Address(currency, net_type, address=withdraw_address,
    secondary_address=secondary_address or "")`), `key_expiry` (the earliest `expire_at` of every listed key, an
    offset-less value read as Asia/Seoul, then `model.iso_utc`; None when none is listed; E21), `prices_krw`
    (`<base> -> trade_price` of each `KRW-<base>` ticker row, `USDT` included: Task 12 passes it to OKX; a row
    quoted in anything but KRW is `FieldError("market")`), `server_utc` and `clock_offset_s` from the first answer
    with a Date header, and `response_sha256` keyed by the eight paths. Venue errors fail the snapshot as in Task 5
    (`upbit: <path>: field <name>`, `upbit: <path>: <TypeName>`, `keys missing: <name>` with `keys_missing`,
    `str(exc)` with `auth_error` for an `AuthError`, `str(exc)` with no flag for any other `InquiryError` or an
    `InquiryRefused`), and a failed snapshot keeps the venue time read before the failure (E39); anything else
    propagates, the router's `AssertionError` and the suite's `Refused` included (E38).
  - Private to `execution/upbit_inquiry.py`: the path constants `_ACCOUNTS`, `_OPEN`, `_CLOSED`, `_WITHDRAWS`,
    `_ADDRESSES`, `_DEPOSITS`, `_KEYS`, `_TICKER`; `_SIGNED` (the seven signed calls and their parameters);
    `_CONTAINED`; `_failed`, `_clock_of`, `_rows(body)` (an Upbit list answer, else `FieldError("body")`),
    `_field`, `_num` (a decimal string or a JSON number, never a bool, nan, inf or a number too large for a float),
    `_price`, `_market(row) -> (quote, base)` (else `FieldError("market")`), `_side`, `_when(row, name) -> datetime`.
  - `tests/execution_fixtures.py`: `UPBIT_ROUTES`, `UPBIT_BODIES`, `UPBIT_ROWS` (an open order, a withdrawal, the
    offset-less key `api_keys_naive`, the `out_of_scope` error body) and `upbit_routes(**changes) -> dict`:
    `(method, path) -> answer` for `serve()`, as `kis_routes()`; a keyword named after an `UPBIT_ROUTES` key replaces
    that answer (None drops it); the routes include `/v1/status/wallet` so a test can show it is never asked.
  - Later users: Task 8 (`cash`, `holdings`, `prices_krw`), Task 11 (`key_expiry`, `withdrawal_addresses`,
    `open_orders`, `fills`, `deposits`, `withdrawals`, `clock_offset_s`, `auth_error`, `keys_missing`), Task 12
    (`poll_once` asks Upbit first and passes `prices_krw.get("USDT")` of an ok Upbit snapshot to OKX, E32).

**Plan decisions used:** E12 (the query built once and hashed as sent), E16 (KRW is settled cash, coins are
holdings, the 7-day and latest-100 windows), E21 (key expiry is the earliest of all listed keys), E22 (the wallet
status is allowlisted and never called), E37, E38, E39, E10 and E36 (every `request` call passes the literal
`"GET"`; the four exact Upbit paths only here), E2, E1R2-5.

Design notes (read before Step 3):
- Upbit answers lists; exchange numbers are decimal strings and quotation prices JSON numbers (contract 3.2), so
  this module's `_num` takes both and refuses a bool, `nan`, `inf`, a number too large for a float and any other
  type; an answer that is not a list is `FieldError("body")`.
- `/v1/api_keys` lists every key of the account and E1 never sees its own key's value outside transport, so
  `key_expiry` is the earliest `expire_at` of all of them (E21).
- The ticker is asked last, after the balances: its `markets` come from the held coins. `KRW-USDT` is always asked,
  since OKX values USDT, USDC and BTC with it (E32). Only KRW markets are asked, so a ticker row in any other quote
  is a venue anomaly and fails the snapshot (`prices_krw` must hold KRW prices only).

- [ ] **Step 1: Write the failing test(s)**

  First confirm the inputs. Overlap check with the PowerShell tool (it must print nothing; otherwise wait and run it
  again):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
test ! -e tests/execution_upbit.py && grep -c '"execution_upbit"' tests/execution_acceptance.py
git ls-files --eol execution/upbit_inquiry.py tests/execution_fixtures.py
grep -c '^PUBLIC = frozenset({"/v1/ticker"})$' execution/upbit_inquiry.py
head -n 5 execution/upbit_inquiry.py
grep -n '^from __future__ import annotations$\|^ENDPOINTS = frozenset({$' execution/upbit_inquiry.py
tail -n 1 tests/execution_fixtures.py
.venv/Scripts/python.exe -c "from execution import upbit_inquiry as U; from tests import execution_fixtures as EF; print(sorted(n for n in vars(U) if n.isupper()), hasattr(U, 'snapshot'), sorted(U.PUBLIC), len(U.ENDPOINTS), callable(getattr(EF, 'kis_routes', None)), callable(getattr(EF, '_routes', None)))"
```

  Expected, line by line: `1`; `i/lf    w/lf` for both files; `1`; the five lines quoted below as Edit 3a's
  old_string; `5:from __future__ import annotations` and `7:ENDPOINTS = frozenset({`;
  `    return _routes(KIS_ROUTES, KIS_BODIES, changes)`; then
  `['ENDPOINTS', 'PUBLIC'] False ['/v1/ticker'] 9 True True`. Apply the DRIFT RULE (contract 0.6) to any other
  answer: a different last line of `tests/execution_fixtures.py` means use it as Edit 1a's old_string; a different
  module docstring means Edit 3a's fallback; either way record a one-line ruling in
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`, as the last line of its
  `## Drift rulings` section (just above the `## Deferred minors` heading). Any other line above `ENDPOINTS` (an
  import, a constant), or a `snapshot` that already exists, means stop and rule.

  Edit 1a, `tests/execution_fixtures.py`, anchor: the end of the file, the last line of Task 5's `kis_routes()`
  (LF). old_string is that line, with no newline after it:

```text
    return _routes(KIS_ROUTES, KIS_BODIES, changes)
```

  new_string is that line, then `\n\n\n` (one newline ending the old last line, then two empty lines), then the
  block below from its first `#` up to and including `    return _routes(UPBIT_ROUTES, UPBIT_BODIES, changes)`, with
  NO newline after it. The file's existing final newline, which old_string left outside the match, then closes the
  block, so the file still ends in exactly one newline. The block (the Upbit answers; top-level code, so it starts in
  column 0 on the third line after the `return`):

```python
# --------------------------------------------------------------------------- #
# Task 6: the Upbit answers (contract 3.2; exchange numbers are decimal strings and quotation prices JSON numbers,
# as the Upbit docs give them; never captured from a live account)
# --------------------------------------------------------------------------- #
UPBIT_ROUTES = {
    "accounts": ("GET", "/v1/accounts"),
    "orders_open": ("GET", "/v1/orders/open"),
    "orders_closed": ("GET", "/v1/orders/closed"),
    "withdraws": ("GET", "/v1/withdraws"),
    "coin_addresses": ("GET", "/v1/withdraws/coin_addresses"),
    "deposits": ("GET", "/v1/deposits"),
    "api_keys": ("GET", "/v1/api_keys"),
    "status_wallet": ("GET", "/v1/status/wallet"),          # allowlisted, never called (E22): routed so a test sees it
    "ticker": ("GET", "/v1/ticker"),
}
UPBIT_BODIES = {
    "accounts": [{"currency": "KRW", "balance": "20000.0", "locked": "0", "avg_buy_price": "0",
                  "avg_buy_price_modified": False, "unit_currency": "KRW"},
                 {"currency": "BTC", "balance": "0.0001", "locked": "0", "avg_buy_price": "100000000",
                  "avg_buy_price_modified": False, "unit_currency": "KRW"}],
    "orders_open": [],
    "orders_closed": [{"uuid": "u-done-1", "side": "bid", "ord_type": "limit", "price": "100000000", "state": "done",
                       "market": "KRW-BTC", "created_at": "2026-10-23T10:00:00+09:00", "volume": "0.0001",
                       "remaining_volume": "0", "executed_volume": "0.0001", "trades_count": 1}],
    "withdraws": [],
    "coin_addresses": [{"currency": "BTC", "net_type": "BTC", "network_name": "Bitcoin",
                        "withdraw_address": "bc1qfixtureaddress000000000000000000000", "secondary_address": None,
                        "beneficiary_name": None, "beneficiary_company_name": None, "beneficiary_type": "individual",
                        "exchange_name": "OKX", "wallet_type": None}],
    "deposits": [{"type": "deposit", "uuid": "u-dep-1", "currency": "KRW", "net_type": None, "txid": "t0",
                  "state": "ACCEPTED", "created_at": "2026-10-22T09:00:00+09:00",
                  "done_at": "2026-10-22T09:01:00+09:00", "amount": "20000", "fee": "0",
                  "transaction_type": "default"}],
    "api_keys": [{"access_key": "test-upbit-access", "expire_at": "2027-05-27T15:17:51+09:00"}],
    "status_wallet": [],
    "ticker": [{"market": "KRW-BTC", "trade_price": 100000000.0}, {"market": "KRW-USDT", "trade_price": 1400.0}],
}
UPBIT_ROWS = {   # rows for the lists the defaults leave empty, the offset-less key variant and the error body
    "orders_open": {"uuid": "u-open-1", "side": "bid", "ord_type": "limit", "price": "90000000", "state": "wait",
                    "market": "KRW-BTC", "created_at": "2026-10-24T08:55:00+09:00", "volume": "0.0001",
                    "remaining_volume": "0.0001", "executed_volume": "0", "trades_count": 0},
    "withdraws": {"type": "withdraw", "uuid": "u-wd-1", "currency": "BTC", "net_type": "BTC", "txid": "t1",
                  "state": "DONE", "created_at": "2026-10-23T11:00:00+09:00", "done_at": "2026-10-23T11:10:00+09:00",
                  "amount": "0.0001", "fee": "0", "transaction_type": "default"},
    "api_keys_naive": {"access_key": "test-upbit-access", "expire_at": "2027-05-27T15:17:51"},   # read as KST
    "out_of_scope": {"error": {"name": "out_of_scope", "message": "fixture: the key lacks this permission"}},
}


def upbit_routes(**changes) -> dict:
    """serve() routes for every Upbit call (the never-called /v1/status/wallet included), keyed (method, path); a
    keyword named after an UPBIT_ROUTES key replaces that answer (None drops it)."""
    return _routes(UPBIT_ROUTES, UPBIT_BODIES, changes)
```

  Check the end of the file from the repo root; it must print `True False False` (the block ends the file, no blank
  line after it, no CR anywhere):

```bash
.venv/Scripts/python.exe -c "import pathlib; b = pathlib.Path('tests/execution_fixtures.py').read_bytes(); print(b.endswith(b'    return _routes(UPBIT_ROUTES, UPBIT_BODIES, changes)\n'), b.endswith(b'\n\n'), b'\r' in b)"
```

  Edit 1b: create `tests/execution_upbit.py` with exactly this content:

```python
"""Upbit inquiry (E1 Task 6; contract C10; spec 5 Upbit, 6; E12, E15, E16, E21, E22, E37, E38, E39).

Every send goes to `EF.serve` (the Upbit answers of contract 3.2, never a live one); the suite's wrapper refuses any
other send. The JWT is checked here against the exact query on the wire, with the fake secret.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from urllib.parse import urlsplit

from execution import upbit_inquiry
from execution.snapshot import Address, Holding, Move, Order
from tests import execution_fixtures as EF

PATH = {name: route[1] for name, route in EF.UPBIT_ROUTES.items()}
SIGNED = ("accounts", "orders_open", "orders_closed", "withdraws", "coin_addresses", "deposits", "api_keys")
ADDRESS = "bc1qfixtureaddress000000000000000000000"


def _path(call: dict) -> str:
    return urlsplit(call["url"]).path


def _query(call: dict) -> str:
    return urlsplit(call["url"]).query


def _headers(call: dict) -> dict:
    return {k.lower(): v for k, v in call["headers"].items()}


def _run(routes: dict, **key_changes):
    """One snapshot at EF.NOW under the fake keys (a keyword changes one; None removes it); (snapshot, calls)."""
    with EF.fake_keys(**key_changes), EF.serve(routes) as calls:
        snap = upbit_inquiry.snapshot(EF.NOW)
    return snap, calls


def _b64(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _jwt(call: dict) -> dict:
    """The payload of the call's Bearer JWT, after checking its HS512 signature with the fake secret."""
    scheme, _, token = _headers(call)["authorization"].partition(" ")
    assert scheme == "Bearer", scheme
    head, payload, sig = token.split(".")
    want = hmac.new(EF.FAKE_KEYS["UPBIT_SECRET_KEY"].encode(), f"{head}.{payload}".encode(), hashlib.sha512).digest()
    assert hmac.compare_digest(_b64(sig), want), "the JWT is not signed with the Upbit secret"
    assert json.loads(_b64(head)) == {"alg": "HS512", "typ": "JWT"}
    return json.loads(_b64(payload))


def _dated(name: str, date: str | None):
    """A serve() callable answering the default body of `name` with its own Date header (none for None)."""
    body = json.dumps(EF.UPBIT_BODIES[name]).encode("utf-8")
    return lambda call: (200, {} if date is None else {"Date": date}, body)


def test_every_private_call_carries_a_jwt_over_the_exact_query():
    snap, calls = _run(EF.upbit_routes())
    assert snap.ok, snap.error
    assert [_path(c) for c in calls] == [PATH[n] for n in SIGNED] + [PATH["ticker"]]   # contract C10's order
    assert all(c["method"] == "GET" for c in calls)
    nonces = []
    for call in calls[:-1]:
        claims = _jwt(call)
        nonces.append(claims["nonce"])
        assert claims["access_key"] == EF.FAKE_KEYS["UPBIT_ACCESS_KEY"] and "exp" not in claims, claims
        query = _query(call)
        if query:
            assert claims["query_hash"] == hashlib.sha512(query.encode()).hexdigest(), (_path(call), claims)
            assert claims["query_hash_alg"] == "SHA512"
            assert set(claims) == {"access_key", "nonce", "query_hash", "query_hash_alg"}, claims
        else:
            assert set(claims) == {"access_key", "nonce"}, claims
    assert len(set(nonces)) == len(nonces) == 7                  # a fresh nonce per call
    queries = {_path(c): _query(c) for c in calls}
    assert queries[PATH["orders_open"]] == "states[]=wait&states[]=watch&limit=100"      # brackets unencoded
    assert queries[PATH["orders_closed"]] == "states[]=done&states[]=cancel&limit=1000"  # no time: the last 7 days
    assert queries[PATH["withdraws"]] == queries[PATH["deposits"]] == "limit=100"
    assert queries[PATH["accounts"]] == queries[PATH["coin_addresses"]] == queries[PATH["api_keys"]] == ""


def test_the_ticker_is_public_and_asks_usdt_and_every_held_coin():
    routes = EF.upbit_routes()
    routes[EF.UPBIT_ROUTES["accounts"]] += [
        {"currency": "XRP", "balance": "0", "locked": "3", "avg_buy_price": "700", "avg_buy_price_modified": False,
         "unit_currency": "KRW"},
        {"currency": "ETH", "balance": "0.5", "locked": "0", "avg_buy_price": "0", "avg_buy_price_modified": False,
         "unit_currency": "KRW"},
        {"currency": "DOGE", "balance": "0", "locked": "0", "avg_buy_price": "0", "avg_buy_price_modified": False,
         "unit_currency": "KRW"}]
    snap, calls = _run(routes)
    assert snap.ok, snap.error
    ticker = calls[-1]
    assert _path(ticker) == PATH["ticker"] and "authorization" not in _headers(ticker), _headers(ticker)
    assert _query(ticker) == "markets=KRW-BTC,KRW-ETH,KRW-USDT,KRW-XRP"     # held coins and USDT; DOGE is not held


def test_the_full_fixture_gives_every_field():
    routes = EF.upbit_routes(orders_open=[dict(EF.UPBIT_ROWS["orders_open"])],
                             withdraws=[dict(EF.UPBIT_ROWS["withdraws"])])
    snap, calls = _run(routes)
    assert snap.ok and snap.error is None and snap.flags == frozenset(), snap.error
    assert snap.venue == "upbit" and snap.utc == "2026-10-24T00:00:00Z"
    assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0
    assert dict(snap.cash) == {"KRW": 20000.0}                   # KRW is cash, never a holding
    assert dict(snap.holdings) == {"BTC": Holding(units=0.0001, locked=0.0, avg_cost=100000000.0)}
    assert snap.open_orders == (Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90000000.0),)
    assert snap.fills == (Move(id="u-done-1", symbol="BTC", counter="KRW", side="buy", units=0.0001),)
    assert snap.withdrawals == (Move(id="u-wd-1", symbol="BTC", side="out", units=0.0001),)
    assert snap.deposits == (Move(id="u-dep-1", symbol="KRW", side="in", units=20000.0),)
    assert snap.withdrawal_addresses == (Address(currency="BTC", net_type="BTC", address=ADDRESS),)
    assert snap.key_expiry == "2027-05-27T06:17:51Z"             # 15:17:51 KST
    assert dict(snap.prices_krw) == {"BTC": 100000000.0, "USDT": 1400.0}
    assert snap.deposit_krw is None and dict(snap.loans) == {} and dict(snap.earn) == {}
    assert set(snap.response_sha256) == {PATH[n] for n in SIGNED + ("ticker",)}
    assert all(re.fullmatch(r"[0-9a-f]{64}", v) for v in snap.response_sha256.values())
    assert PATH["status_wallet"] not in {_path(c) for c in calls}    # allowlisted, routed, never asked (E22)


def test_balances_count_locked_units_and_orders_map_sides():
    routes = EF.upbit_routes()
    routes[EF.UPBIT_ROUTES["accounts"]][0] |= {"balance": "15000", "locked": "5000"}
    routes[EF.UPBIT_ROUTES["accounts"]][1] |= {"balance": "0.5", "locked": "0.25"}
    routes[EF.UPBIT_ROUTES["accounts"]].append({"currency": "ETH", "balance": "1", "locked": "0",
                                                "avg_buy_price": "0.05", "avg_buy_price_modified": False,
                                                "unit_currency": "BTC"})
    routes[EF.UPBIT_ROUTES["ticker"]].append({"market": "KRW-ETH", "trade_price": 5000000})
    routes[EF.UPBIT_ROUTES["orders_open"]] = [
        dict(EF.UPBIT_ROWS["orders_open"]),
        dict(EF.UPBIT_ROWS["orders_open"], uuid="u-open-2", side="ask", state="watch", price=None,
             remaining_volume="0.00005"),
        dict(EF.UPBIT_ROWS["orders_open"], uuid="u-open-3", price="0")]        # a zero price: no limit price
    routes[EF.UPBIT_ROUTES["orders_closed"]] += [
        dict(EF.UPBIT_BODIES["orders_closed"][0], uuid="u-done-2", side="ask",
             executed_volume="0.00002"),
        dict(EF.UPBIT_BODIES["orders_closed"][0], uuid="u-cancel-1", state="cancel", executed_volume="0")]
    snap, _calls = _run(routes)
    assert snap.ok, snap.error
    assert dict(snap.cash) == {"KRW": 20000.0}                   # balance + locked
    assert snap.holdings["BTC"] == Holding(units=0.75, locked=0.25, avg_cost=100000000.0)
    assert snap.holdings["ETH"] == Holding(units=1.0, locked=0.0, avg_cost=None)   # bought for BTC: no KRW cost
    assert snap.prices_krw["ETH"] == 5000000.0
    assert snap.open_orders == (Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90000000.0),
                                Order(id="u-open-2", symbol="BTC", side="sell", units=0.00005, price=None),
                                Order(id="u-open-3", symbol="BTC", side="buy", units=0.0001, price=None))
    assert snap.fills == (Move(id="u-done-1", symbol="BTC", counter="KRW", side="buy", units=0.0001),
                          Move(id="u-done-2", symbol="BTC", counter="KRW", side="sell", units=0.00002))


def test_server_time_and_offset_come_from_the_first_answer_with_a_date_header():
    routes = EF.upbit_routes(accounts=_dated("accounts", None),
                             orders_open=_dated("orders_open", "Fri, 23 Oct 2026 23:59:15 GMT"))
    snap, _calls = _run(routes)                                  # every later answer carries DATE_HEADER (offset 0)
    assert snap.ok and snap.server_utc == "2026-10-23T23:59:15Z" and snap.clock_offset_s == -45.0, snap


def test_key_expiry_is_the_earliest_and_an_offset_less_value_is_seoul():
    later = {"access_key": "other", "expire_at": "2027-09-01T00:00:00+09:00"}
    snap, _calls = _run(EF.upbit_routes(api_keys=[later, dict(EF.UPBIT_ROWS["api_keys_naive"])]))
    assert snap.ok and snap.key_expiry == "2027-05-27T06:17:51Z", snap.key_expiry   # naive 15:17:51 read as KST
    snap, _calls = _run(EF.upbit_routes(api_keys=[later, {"access_key": "x", "expire_at": "2027-01-01T00:00:00Z"}]))
    assert snap.ok and snap.key_expiry == "2027-01-01T00:00:00Z", snap.key_expiry
    snap, _calls = _run(EF.upbit_routes(api_keys=[]))
    assert snap.ok and snap.key_expiry is None


def test_out_of_scope_gives_auth_error():
    for name, status in (("accounts", 401), ("orders_closed", 401), ("coin_addresses", 403)):   # Upbit sends either
        snap, calls = _run(EF.upbit_routes(**{name: (status, dict(EF.UPBIT_ROWS["out_of_scope"]))}))
        assert not snap.ok and snap.flags == frozenset({"auth_error"}) and snap.error, (name, snap)
        assert _path(calls[-1]) == PATH[name]                    # it stopped at the refused call
        assert "fixture:" not in snap.error and EF.FAKE_KEYS["UPBIT_ACCESS_KEY"] not in snap.error
        clock = (None, None) if name == "accounts" else ("2026-10-24T00:00:00Z", 0.0)   # the time read so far (E39)
        assert (snap.server_utc, snap.clock_offset_s) == clock, (name, snap.server_utc, snap.clock_offset_s)


def test_missing_keys_give_keys_missing():
    for name in ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"):
        snap, calls = _run(EF.upbit_routes(), **{name: None})
        assert calls == [] and not snap.ok, name
        assert snap.flags == frozenset({"keys_missing"}) and snap.error == f"keys missing: {name}", snap.error


def test_a_malformed_field_fails_closed_with_names_only():
    cases = (("accounts", lambda b: b[1].pop("locked"), "field locked"),
             ("accounts", lambda b: b[1].update(balance="0.0001BTC"), "field balance"),
             ("accounts", lambda b: b[1].update(balance=10 ** 400), "field balance"),     # too large for a float
             ("orders_closed", lambda b: b[0].update(market="KRWBTC"), "field market"),
             ("orders_closed", lambda b: b[0].update(executed_volume=None), "field executed_volume"),
             ("coin_addresses", lambda b: b[0].pop("withdraw_address"), "field withdraw_address"),
             ("api_keys", lambda b: b[0].update(expire_at="27 May 2027"), "field expire_at"),
             ("ticker", lambda b: b[0].update(trade_price="nan"), "field trade_price"),
             ("ticker", lambda b: b[0].update(trade_price=True), "field trade_price"),
             ("ticker", lambda b: b[0].update(market="BTC-ETH"), "field market"),         # not a KRW price
             ("deposits", lambda b: b.insert(0, "not a row"), "field uuid"))
    for name, change, tail in cases:
        routes = EF.upbit_routes()
        change(routes[EF.UPBIT_ROUTES[name]])
        snap, _calls = _run(routes)
        assert not snap.ok and snap.flags == frozenset(), name
        assert snap.error == f"upbit: {PATH[name]}: {tail}", snap.error
        assert ADDRESS not in snap.error and "0.0001" not in snap.error and "2027" not in snap.error
    snap, _calls = _run(EF.upbit_routes(withdraws={"not": "a list"}))
    assert not snap.ok and snap.error == f"upbit: {PATH['withdraws']}: field body", snap.error


def test_other_venue_errors_fail_closed_and_an_unrouted_send_propagates():
    bad = {"error": {"name": "validation_error", "message": "fixture: bad"}}
    snap, calls = _run(EF.upbit_routes(deposits=(400, bad)))    # an InquiryError, not an auth answer
    assert not snap.ok and snap.flags == frozenset() and PATH["deposits"] in snap.error, snap.error
    assert "fixture:" not in snap.error and _path(calls[-1]) == PATH["deposits"], snap.error
    routes = EF.upbit_routes()
    routes[EF.UPBIT_ROUTES["accounts"]][1]["currency"] = ["BTC"]        # unhashable: a TypeError, never its text
    snap, _calls = _run(routes)
    assert not snap.ok and snap.flags == frozenset(), snap.error
    assert snap.error == f"upbit: {PATH['accounts']}: TypeError", snap.error
    with EF.fake_keys(), EF.serve(EF.upbit_routes(api_keys=None)):
        try:
            upbit_inquiry.snapshot(EF.NOW)                       # the router refuses the unrouted call (E38)
        except AssertionError:
            pass
        else:
            raise AssertionError("an unrouted send became a snapshot")
    assert len(EF.STRAYS) == 1 and EF.STRAYS[0].endswith(PATH["api_keys"]), EF.STRAYS
    EF.STRAYS.clear()


def test_a_refused_send_propagates():
    with EF.fake_keys():
        try:
            upbit_inquiry.snapshot(EF.NOW)                       # no serve(): the suite's refusing stub answers
        except EF.Refused:
            pass
        else:
            raise AssertionError("a refused send became a snapshot")
    assert len(EF.STRAYS) == 1 and EF.STRAYS[0].endswith(PATH["accounts"]), EF.STRAYS   # the first signed call
    EF.STRAYS.clear()
```

- [ ] **Step 2: Run to verify it fails**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_upbit/
```

  Expected: 11 lines `FAIL execution_upbit/<test> AttributeError: module 'execution.upbit_inquiry' has no
  attribute 'snapshot'` (each preceded by its traceback), then `0/11 passed, 11 failed, 0 not run` (exit code 1). Any
  other failure (`execution_upbit/import`, `KeyError: no such route`) means Step 1 went wrong: fix it before Step 3.

- [ ] **Step 3: Implement**

  Re-read `execution/upbit_inquiry.py` first. Two Edit-tool replacements; the file stays LF and Task 2's constants
  (`ENDPOINTS`, `PUBLIC`) stay byte for byte.

  Edit 3a, anchor: the module docstring and the future import above `ENDPOINTS = frozenset({` (LF). old_string, the
  first five lines of the file as Task 2 wrote them:

```python
"""Upbit read-only inquiry (E1 spec 5, the Upbit table; contract section 7; E10, E22): the endpoint allowlist and its
one public path. transport.request reads ENDPOINTS and PUBLIC at call time. This is the only file in execution/ that
may name the Upbit order and withdrawal inquiry paths, and tests/execution_guards.py holds each of them to the four
exact paths listed here. Task 6 adds the snapshot."""
from __future__ import annotations
```

  If the Edit finds no match because Task 2 as executed wrote another docstring (Step 1's `head -n 5` showed it),
  use the file's text from its first character through the end of the line `from __future__ import annotations` as
  old_string instead, and record the drift ruling as Step 1 says. new_string:

```python
"""Upbit read-only inquiry (E1 spec 5 and 6; plan C7, C10): the frozen allowlist and the Upbit snapshot of one poll,
for the owner's main pocket. Transport signs every call but the public ticker with an HS512 JWT whose query hash
covers the exact query sent. The wallet status stays on the allowlist but nothing reads it (E22)."""
from __future__ import annotations

import math
from datetime import datetime

from core.compliance import model
from execution.snapshot import Address, FieldError, Holding, Move, Order, Snapshot, failed
from execution.transport import AuthError, InquiryError, InquiryRefused, KeyMissing, request
```

  Edit 3b, anchor: the last constant line (LF). old_string:

```python
PUBLIC = frozenset({"/v1/ticker"})
```

  new_string (that line, one blank line, then the snapshot and its helpers):

```python
PUBLIC = frozenset({"/v1/ticker"})

_ACCOUNTS = "/v1/accounts"
_OPEN = "/v1/orders/open"
_CLOSED = "/v1/orders/closed"
_WITHDRAWS = "/v1/withdraws"
_ADDRESSES = "/v1/withdraws/coin_addresses"
_DEPOSITS = "/v1/deposits"
_KEYS = "/v1/api_keys"
_TICKER = "/v1/ticker"
_SIGNED = ((_ACCOUNTS, None), (_OPEN, [("states[]", "wait"), ("states[]", "watch"), ("limit", "100")]),
           (_CLOSED, [("states[]", "done"), ("states[]", "cancel"), ("limit", "1000")]),   # no time: the last 7 days
           (_WITHDRAWS, [("limit", "100")]), (_ADDRESSES, None), (_DEPOSITS, [("limit", "100")]), (_KEYS, None))
_CONTAINED = (KeyMissing, InquiryRefused, InquiryError, LookupError, ValueError, TypeError, AttributeError,
              ArithmeticError)                      # E38: the venue's own errors (AuthError and FieldError included)


def snapshot(now: datetime) -> Snapshot:
    """The Upbit snapshot of the poll at `now` (C10). A venue error gives a failed snapshot whose text holds names,
    paths and codes only (E37, E38); a refused write, the suite's refusing stub and a programming error propagate."""
    utc, path, answers = model.iso_utc(now), _ACCOUNTS, {}
    try:
        for path, params in _SIGNED:
            answers[path] = request("upbit", "GET", path, params)
        path, cash, holdings = _ACCOUNTS, {}, {}
        for row in _rows(answers[path].body):
            currency, locked = _field(row, "currency"), _num(row, "locked")
            units = _num(row, "balance") + locked
            if currency == "KRW":
                cash["KRW"] = units
            elif units > 0:
                cost = _num(row, "avg_buy_price") if _field(row, "unit_currency") == "KRW" else None
                holdings[currency] = Holding(units=units, locked=locked, avg_cost=cost)
        path = _OPEN
        orders = tuple(Order(id=_field(r, "uuid"), symbol=_market(r)[1], side=_side(r),
                             units=_num(r, "remaining_volume"), price=_price(r)) for r in _rows(answers[path].body))
        path, fills = _CLOSED, []
        for row in _rows(answers[path].body):
            units = _num(row, "executed_volume")
            if units > 0:                                   # a cancelled order with nothing executed is no fill
                quote, base = _market(row)
                fills.append(Move(id=_field(row, "uuid"), symbol=base, counter=quote, side=_side(row), units=units))
        path = _WITHDRAWS
        withdrawals = tuple(Move(id=_field(r, "uuid"), symbol=_field(r, "currency"), side="out",
                                 units=_num(r, "amount")) for r in _rows(answers[path].body))
        path = _DEPOSITS
        deposits = tuple(Move(id=_field(r, "uuid"), symbol=_field(r, "currency"), side="in",
                              units=_num(r, "amount")) for r in _rows(answers[path].body))
        path = _ADDRESSES
        addresses = tuple(Address(currency=_field(r, "currency"), net_type=_field(r, "net_type"),
                                  address=_field(r, "withdraw_address"),
                                  secondary_address=_field(r, "secondary_address") or "")
                          for r in _rows(answers[path].body))
        path = _KEYS                                        # every key of the account: E1 never sees its own (E21)
        expiries = [_when(r, "expire_at") for r in _rows(answers[path].body)]
        path = _TICKER
        markets = sorted({f"KRW-{c}" for c in holdings} | {"KRW-USDT"})     # KRW-USDT values OKX too (E32)
        answers[path] = request("upbit", "GET", path, [("markets", ",".join(markets))])
        prices = {}
        for row in _rows(answers[path].body):
            quote, base = _market(row)
            if quote != "KRW":                              # only KRW markets were asked: prices_krw is KRW only
                raise FieldError("market")
            prices[base] = _num(row, "trade_price")
        server_utc, offset = _clock_of(answers)
        return Snapshot(venue="upbit", utc=utc, server_utc=server_utc, clock_offset_s=offset, ok=True,
                        holdings=holdings, cash=cash, open_orders=orders, fills=tuple(fills), deposits=deposits,
                        withdrawals=withdrawals, withdrawal_addresses=addresses,
                        key_expiry=model.iso_utc(min(expiries)) if expiries else None, prices_krw=prices,
                        response_sha256={p: a.sha256 for p, a in answers.items()})
    except _CONTAINED as exc:
        return _failed(utc, path, exc, answers)


def _failed(utc: str, path: str, exc: Exception, answers: dict) -> Snapshot:
    """A contained venue error as a failed snapshot (E38), keeping the venue time read so far (E39); the text is
    built from names only, never str() of a parse or network error (E37). An out_of_scope answer (a permission the
    key lacks) reaches here as an AuthError, so auth_error (spec 5)."""
    if isinstance(exc, KeyMissing):
        error, flags = f"keys missing: {exc.name}", frozenset({"keys_missing"})
    elif isinstance(exc, AuthError):
        error, flags = str(exc), frozenset({"auth_error"})
    elif isinstance(exc, (InquiryRefused, InquiryError)):
        error, flags = str(exc), frozenset()
    elif isinstance(exc, FieldError):
        error, flags = f"upbit: {path}: field {exc.args[0]}", frozenset()
    else:
        error, flags = f"upbit: {path}: {type(exc).__name__}", frozenset()
    server_utc, offset = _clock_of(answers)
    return failed("upbit", utc, error, flags=flags, server_utc=server_utc, clock_offset_s=offset)


def _clock_of(answers: dict) -> tuple[str | None, float | None]:
    """server_utc and clock_offset_s from the first answer with a Date header (E39)."""
    for answer in answers.values():
        if answer.server_utc is not None:
            return model.iso_utc(answer.server_utc), (answer.server_utc - answer.received_utc).total_seconds()
    return None, None


def _rows(body) -> list:
    """An Upbit list answer."""
    if not isinstance(body, list):
        raise FieldError("body")
    return body


def _field(row, name: str):
    """row[name]; FieldError(name) when row is not a dict or lacks it (E37)."""
    if not isinstance(row, dict) or name not in row:
        raise FieldError(name)
    return row[name]


def _num(row, name: str) -> float:
    """A finite number from a decimal string (exchange answers) or a JSON number (quotation prices); otherwise
    FieldError(name), never the value."""
    value = _field(row, name)
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise FieldError(name)
    try:
        number = float(value)
    except (ValueError, OverflowError):                 # OverflowError: an integer too large for a float
        raise FieldError(name) from None
    if not math.isfinite(number):
        raise FieldError(name)
    return number


def _price(row) -> float | None:
    """An order's price; None for a null or zero price (a market order)."""
    return None if _field(row, "price") is None else _num(row, "price") or None


def _market(row) -> tuple[str, str]:
    """(quote, base) of a market such as KRW-BTC."""
    market = _field(row, "market")
    quote, _, base = market.partition("-") if isinstance(market, str) else ("", "", "")
    if not quote or not base or "-" in base:
        raise FieldError("market")
    return quote, base


def _side(row) -> str:
    return "buy" if _field(row, "side") == "bid" else "sell"


def _when(row, name: str) -> datetime:
    """An ISO time; one with no offset is Asia/Seoul, as the Upbit docs give KST (E21)."""
    value = _field(row, name)
    if not isinstance(value, str):
        raise FieldError(name)
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        raise FieldError(name) from None
    return moment if moment.utcoffset() is not None else moment.replace(tzinfo=model.KST)
```

  Do not mention any other Upbit order or withdrawal path in a comment or docstring (the Upbit token rule reads them)
  and write `canonical` in lower case if you touch a docstring (test_09 and T-RO-01 match the KIS account-field
  text case-sensitively in this file).

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check before EACH command below (the Git Bash prefix does it). All from the repo root.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_upbit/
```

  Expected: 11 lines `PASS execution_upbit/test_<name>`, then `11/11 passed, 0 failed, 0 not run` (exit code 0).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_kis/
```

  Expected: the same `N/N passed, 0 failed, 0 not run` as at the end of Task 5 (Task 5 still green: this task only
  appended to the fixtures).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/
```

  Expected: only `PASS execution_guards/<name>` lines, then `G/G passed, 0 failed, 0 not run` with the same G as at
  the end of Task 5 (this task adds no guard test). The Upbit token rule now reads the whole of
  `execution/upbit_inquiry.py`.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; t(); u(); print('T-RO-01 ok')"
```

  Expected: `T-RO-01 ok` (`/v1/orders` and `/v1/withdraws` are accepted in `execution/upbit_inquiry.py` only, by the
  file-exact text exception of Task 1).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.acceptance import test_08_no_broker_order_path as a, test_09_no_account_credentials_requested as b, test_16_every_source_file_is_utf8_readable as c, test_18_eodhd_is_gone_from_the_runtime as d; a(); b(); c(); d(); print('cockpit scans ok')"
```

  Expected: `cockpit scans ok` (the four text scans of `runtime_py()` over the real tree; no results file is
  written).

```bash
git status --short
```

  Expected: exactly ` M execution/upbit_inquiry.py`, ` M tests/execution_fixtures.py` and
  `?? tests/execution_upbit.py`, plus ` M docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`
  when this task recorded a drift ruling.

- [ ] **Step 5: Commit**

```bash
git add execution/upbit_inquiry.py tests/execution_fixtures.py tests/execution_upbit.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  If this task recorded a drift ruling, also
  `git add docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` before the two stat commands.
  The two stat outputs must be identical (every staged file is LF). Then commit. In the trailer, replace
  `<the committing model>` with the name of the model that writes this commit, for example `Claude Sonnet 5.5` or
  `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "feat(execution): Upbit read-only inquiry snapshot" -m "Task 6: upbit_inquiry.snapshot (seven JWT-signed GETs and the public ticker; KRW cash, coin holdings, orders, fills, moves, addresses, the earliest key expiry in UTC (an offset-less value read as KST)), the Upbit answers and tests/execution_upbit.py." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
```
