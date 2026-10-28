### Task 7: OKX inquiry and its read-only self-check (`execution/okx_inquiry.py`)

**Files:**
- Modify: `execution/okx_inquiry.py` (anchors: the module docstring and the `from __future__ import annotations`
  line above `ENDPOINTS = frozenset({`, and the last constant line
  `ALGO_TYPES = ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")`; LF)
- Modify: `tests/execution_fixtures.py` (anchor: the file's last line, the end of Task 6's `upbit_routes()`; LF)
- Create: `tests/execution_okx.py` (LF, UTF-8, no BOM)
- Modify, only when this task records a drift ruling (Step 1 or Edit 3a):
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (anchor: the `## Deferred minors`
  heading; one line above it, in the `## Drift rulings` section; LF)
- Test: `tests/execution_okx.py`

`tests/execution_acceptance.py` (Task 1) already lists `"execution_okx"` in MODULES and skips the module until this
task creates it. The guards of `tests/execution_guards.py` read the full `execution/okx_inquiry.py` from this task
on: no `/api/v5/trade/order` constant, no demo header or mock host text, no TR-shaped token, and from transport only
the TRANSPORT_NAMES `request` (always with the literal `"GET"`), `require_keys` and the four error classes
`AuthError`, `InquiryError`, `InquiryRefused` and `KeyMissing`. No CRLF file and no file outside the three above
changes (the execution ledger aside, when Step 1 or Edit 3a records a drift ruling).

**Interfaces:**
- Consumes:
  - Task 2 (`execution/okx_inquiry.py`, contract 7): `ENDPOINTS` (fourteen `("GET", path)` pairs),
    `PUBLIC = frozenset({"/api/v5/public/time", "/api/v5/market/ticker"})`,
    `ALGO_TYPES = ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")`.
  - Tasks 2 and 3 (`execution.transport`, contract 6): `require_keys(venue) -> None` (reads
    `CREDENTIALS["okx"]` with `keys.read` and discards them; `KeyMissing` names the first missing key);
    `request(venue, method, path, params=None, *, tr_id=None) -> Answer`; `AuthError`, `InquiryError`,
    `InquiryRefused`, `KeyMissing`. After a successful `public/time` transport sets
    `_okx_offset_s = int(ts) / 1000 - answer.received_utc.timestamp()` itself, and while that offset is unknown or
    above 25 s it refuses every signed OKX request, before any key is read, with the reason
    `"okx: the PC clock offset from OKX time is unknown or above 25 s; OKX requests not sent"` (E13 step 6). It
    signs with `OK-ACCESS-KEY`, `OK-ACCESS-SIGN` (Base64 HMAC-SHA256 of timestamp + `GET` + path with query),
    `OK-ACCESS-TIMESTAMP` (`_okx_timestamp(_clock())`, milliseconds and `Z`) and `OK-ACCESS-PASSPHRASE`, never a demo
    header, and raises `AuthError` for an OKX code in `AUTH_CODES["okx"]` (50120 and 50123 included) on HTTP 200
    and `InquiryError` for any other code that is not `"0"`, its text naming venue, path, HTTP status and the code
    only (E15). The `AuthError` text is not pinned (E15 pins only `InquiryError`'s), so the tests ask only that it
    is non-empty and holds no venue message. Tests only: `transport._okx_offset_s`.
  - Task 2 (`execution.keys.read`, tests only: wrapped to record which names are read).
  - Task 4 (`execution.snapshot`): `FieldError`, `Holding`, `Move`, `Order`, `Snapshot`, `failed`; its `FLAGS`
    hold `keys_missing`, `auth_error`, `okx_perm`, `okx_acct_lv`, `okx_spot_borrow`, `okx_auto_loan`, `okx_no_ip`,
    `EVENTS` and `derivative_position`.
  - `core.compliance.model` (repo): `iso_utc(moment)`.
  - Tests: the Tasks 1 to 4 fixtures as in Task 5 (`FAKE_KEYS` holds `OKX_API_KEY` `"test-okx-key"`,
    `OKX_API_SECRET` `"test-okx-secret"`, `OKX_API_PASSPHRASE` `"test-okx-pass"`); Task 5's `_routes`.
- Produces:
  - `execution/okx_inquiry.py`:
    - `SELF_CHECK = ("perm", "acctLv", "enableSpotBorrow", "autoLoan", "ip")` (contract 11).
    - `self_check(config: Mapping) -> frozenset[str]`, pure: the subset of `okx_perm` (`perm` is not exactly the
      string `"read_only"`), `okx_acct_lv` (`acctLv` is not the string `"1"`), `okx_spot_borrow`
      (`enableSpotBorrow is not False`), `okx_auto_loan` (`autoLoan is not False`) and `okx_no_ip` (`ip` is not a
      non-empty string); a missing key fails its check.
    - `snapshot(now: datetime, usdt_krw: float | None) -> Snapshot`: `require_keys("okx")` first (a missing key
      gives `keys missing: <name>` with flag `keys_missing` and no call at all), then the public `public/time`
      (`server_utc` from its `ts`, `clock_offset_s = ts / 1000 - received_utc`), then `account/config`, whose failed
      self-check returns `failed("okx", utc, "okx self-check failed: <the failed SELF_CHECK names, in SELF_CHECK
      order, joined by ", ">", flags=<the failed flags>)` with the venue time and sends nothing more; then
      `account/balance`, `asset/balances`, `account/positions`, `asset/asset-valuation` (`ccy=USDT`),
      `finance/savings/balance`, `finance/flexible-loan/loan-info`, `trade/orders-pending`, one
      `trade/orders-algo-pending` per `ALGO_TYPES` value (`ordType=<t>`), `trade/fills`, `asset/deposit-history`,
      `asset/withdrawal-history` and the public `market/ticker` (`instId=BTC-USDT`). The ok snapshot holds
      `holdings` (per currency: trading `cashBal` plus funding `bal`, locked = the two `frozenBal`, units > 0 only),
      no `cash` (coins are holdings, E16), `prices_krw` (`{"USDT": u, "USDC": u, "BTC": last * u}` when `usdt_krw`
      is a positive finite number, else empty), `open_orders` (`orders-pending` rows with `ordId`, then the algo rows
      with `algoId`, in `ALGO_TYPES` order: `Order(id, symbol=<base of instId>, side, units=sz, price=px or None)`),
      `fills` (`Move(id=tradeId, symbol=<base>, counter=<quote>, side, units=fillSz)`), `deposits` (`depId`,
      `side="in"`), `withdrawals` (`wdId`, `side="out"`), `loans` (`liab:<ccy>` for every trading row,
      `flexible_loan:<ccy>`, `margin:<instId>` = `abs(pos)` of a MARGIN position), `earn` (`asset_valuation`,
      `savings:<ccy>`, `auto_lend:<ccy>` = `autoLendMtAmt or 1.0` while `autoLendStatus` is `pending` or `active`),
      `flags` (`EVENTS` for any EVENTS position, order or fill; `derivative_position` for any other non-MARGIN
      position with `pos` not 0; a non-EVENTS position whose `pos` is `""` fails OKX with
      `okx: /api/v5/account/positions: field pos`) and `response_sha256` keyed by path, with
      `/api/v5/trade/orders-algo-pending?ordType=<t>` for the seven algo calls. Venue errors fail the snapshot as in
      Task 5 (`okx: <path>: field <name>`, `okx: <path>: <TypeName>`), keeping `server_utc` and `clock_offset_s`
      once `public/time` has answered; anything else propagates (E38).
  - Private to `execution/okx_inquiry.py`: `_FLAGS` (one flag per `SELF_CHECK` name), `_EPOCH`, the path constants
    `_TIME`, `_CONFIG`, `_BALANCE`, `_FUNDING`, `_POSITIONS`, `_VALUATION`, `_SAVINGS`, `_LOANS`, `_PENDING`, `_ALGO`,
    `_FILLS`, `_DEPOSITS`, `_WITHDRAWALS`, `_TICKER`; `_BEFORE_ALGO`, `_AFTER_ALGO`, `_CONTAINED`; `_failed`, `_add`,
    `_pair(row) -> (base, quote)` (else `FieldError("instId")`), `_field`, `_num` (a string only; `""` is 0),
    `_one`, `_list`.
  - `tests/execution_fixtures.py`: `NOW_MS = 1792800000000` (NOW in epoch milliseconds), `OKX_ROUTES`,
    `OKX_BODIES`, `OKX_ROWS` (a SWAP position, a savings row, an open order, an algo order, a withdrawal and the
    50120 error body) and `okx_routes(**changes) -> dict` (contract 3.2: `(method, path)` -> answer for serve(); a
    keyword named after an OKX_ROUTES key replaces that answer (None drops it)); one route answers all seven algo
    calls (a callable can answer one `ordType` differently).
  - Later users: Task 8 (`holdings`, `prices_krw`; OKX USDT and USDC in `held_krw`), Task 11 (the self-check flags,
    `auth_error`, `keys_missing`, `EVENTS`, `derivative_position`, `loans`, `earn`, `open_orders`, `fills`,
    `clock_offset_s`), Task 12 (`poll_once` asks OKX second with `usdt_krw` = the ok Upbit snapshot's
    `prices_krw.get("USDT")`, else None, E32; a test that polls at a time other than NOW passes its own
    `okx_routes(time=<its own answer>)`, since the default `ts` is NOW).

**Plan decisions used:** E32 (keys first, then `public/time`, then the self-check, which stops OKX for the poll),
E25 (one algo call per `ordType`; MARGIN is a loan; EVENTS and derivative flags), E26 (OKX loans and earn), E39 (the
offset from `public/time` at receipt), E13 step 6 (the 25 s rule, in transport), E16 (coins are holdings), E17 (no
Upbit USDT price, no OKX prices: positions fail closed), E37, E38, E10 and E36, E2, E1R2-5, E1R2-6 (`autoLoan` stays
strict).

Design notes (read before Step 3):
- `perm` must equal `"read_only"` exactly: OKX added Transfer, Loan and Earn permissions in 2026 and may report
  values its docs do not list, so a "contains read_only" test would pass a trade-capable key (okx.md skeptic
  correction 1). `acctLv`, `enableSpotBorrow` and `autoLoan` are compared by type too (`"1"`, `False`): a string
  `"false"` fails closed.
- Three readings of E25 are stricter than its words, all fail closed: an EVENTS position sets `EVENTS` even with
  `pos` 0 (okx.md correction 8: flag any EVENTS row), and any position type other than MARGIN and EVENTS with a
  non-zero `pos` sets `derivative_position` (SWAP, FUTURES and OPTION today, and any type OKX adds later). A zero
  MARGIN, SWAP, FUTURES or OPTION row is ignored (okx.md correction 7). Third, a non-EVENTS position whose `pos`
  is `""` fails OKX closed with `field pos`. OKX sends `""` for a field that does not apply and a position always has
  a size, so the row is malformed; E25 ignores only `pos == "0"`, and `_num` alone would read `""` as 0 and drop the
  row with no flag and no loan.
- The venue time is `_EPOCH + timedelta(seconds=ts)`, never `datetime.fromtimestamp`: on Windows an absurd `ts`
  makes `fromtimestamp` raise `OSError`, which E38 does not contain, so a garbage answer would crash the poll
  instead of failing OKX; the epoch sum raises `OverflowError`, which it does.
- Every algo row is read with `px` as contract 11 says (`price=px or None`). OKX documents trigger and order prices
  of some algo types under other names; an algo row without `px` fails OKX closed until a follow-up reads those
  fields (E1R2-5).

- [ ] **Step 1: Write the failing test(s)**

  First confirm the inputs. Overlap check with the PowerShell tool (it must print nothing; otherwise wait and run it
  again):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
test ! -e tests/execution_okx.py && grep -c '"execution_okx"' tests/execution_acceptance.py
git ls-files --eol execution/okx_inquiry.py tests/execution_fixtures.py
grep -c '^ALGO_TYPES = ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")$' execution/okx_inquiry.py
grep -n '^from __future__ import annotations$\|^ENDPOINTS = frozenset({$' execution/okx_inquiry.py
tail -n 1 tests/execution_fixtures.py
.venv/Scripts/python.exe -c "from execution import keys as K, okx_inquiry as O, snapshot as S, transport as T; from tests import execution_fixtures as EF; print(sorted(n for n in vars(O) if n.isupper()), hasattr(O, 'snapshot'), O.ALGO_TYPES, sorted(O.PUBLIC))"
.venv/Scripts/python.exe -c "from execution import keys as K, okx_inquiry as O, snapshot as S, transport as T; from tests import execution_fixtures as EF; print(all(callable(getattr(EF, n, None)) for n in ('_routes', 'serve', 'fake_keys', 'isolated', 'upbit_routes', 'Refused')), isinstance(EF.STRAYS, list), EF.DATE_HEADER, EF.FAKE_KEYS['OKX_API_KEY'], all(callable(getattr(T, n, None)) for n in ('request', 'require_keys', 'AuthError', 'InquiryError', 'InquiryRefused', 'KeyMissing')), callable(K.read), {'keys_missing', 'auth_error', 'okx_perm', 'okx_acct_lv', 'okx_spot_borrow', 'okx_auto_loan', 'okx_no_ip', 'EVENTS', 'derivative_position'} <= S.FLAGS, {'50120', '50123'} <= T.AUTH_CODES['okx'], '_okx_offset_s' in vars(T), T._okx_offset_s)"
```

  Expected, line by line: `1`; `i/lf    w/lf` for both files; `1`; `<n>:from __future__ import annotations` and
  `<n+2>:ENDPOINTS = frozenset({`; `    return _routes(UPBIT_ROUTES, UPBIT_BODIES, changes)`; then
  `['ALGO_TYPES', 'ENDPOINTS', 'PUBLIC'] False ('conditional', 'oco', 'trigger', 'move_order_stop', 'iceberg',
  'twap', 'chase') ['/api/v5/market/ticker', '/api/v5/public/time']` (one line); then
  `True True Sat, 24 Oct 2026 00:00:00 GMT test-okx-key True True True True True None` (one line). Apply the DRIFT
  RULE (contract 0.6) to any other answer: a different last line of `tests/execution_fixtures.py` means use it as
  Edit 1a's old_string and record a one-line ruling in the execution ledger
  (`docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`); anything else above `ENDPOINTS`, a
  `False` in the last line, a missing name or a `snapshot` that already exists means stop and rule.

  Edit 1a, `tests/execution_fixtures.py`, anchor: the end of the file, the last line of Task 6's `upbit_routes()`
  (LF). old_string is that line, with no newline after it:

```text
    return _routes(UPBIT_ROUTES, UPBIT_BODIES, changes)
```

  new_string = that line, then `\n\n\n` (one newline ending the old last line, then two empty lines), then the block
  below from its first `#` up to and including its last line, `    return _routes(OKX_ROUTES, OKX_BODIES, changes)`,
  with NO newline after it. The file's existing final newline, which old_string left outside the match, then closes
  the block, so the file still ends in exactly one newline. The block (the OKX answers; top-level code, so it starts
  in column 0 on the third line after the `return`):

```python
# --------------------------------------------------------------------------- #
# Task 7: the OKX answers (contract 3.2; OKX sends numbers as strings and its errors on HTTP 200; never captured
# from a live account). [assumed], since the research has no table for them (E1R2-5; Task 14's first live poll
# shows them): every flexible-loan field; every algo-row field (px above all: an algo order without px fails OKX
# closed); instType of orders-pending and fills rows; instId of positions rows; the public/time and market/ticker
# bodies.
# --------------------------------------------------------------------------- #
NOW_MS = 1792800000000                                  # NOW in epoch milliseconds (public/time's ts)
OKX_ROUTES = {
    "time": ("GET", "/api/v5/public/time"),
    "config": ("GET", "/api/v5/account/config"),
    "balance": ("GET", "/api/v5/account/balance"),
    "asset_balances": ("GET", "/api/v5/asset/balances"),
    "positions": ("GET", "/api/v5/account/positions"),
    "asset_valuation": ("GET", "/api/v5/asset/asset-valuation"),
    "savings": ("GET", "/api/v5/finance/savings/balance"),
    "flexible_loan": ("GET", "/api/v5/finance/flexible-loan/loan-info"),
    "orders_pending": ("GET", "/api/v5/trade/orders-pending"),
    "orders_algo_pending": ("GET", "/api/v5/trade/orders-algo-pending"),   # one route answers all seven ordTypes
    "fills": ("GET", "/api/v5/trade/fills"),
    "deposit_history": ("GET", "/api/v5/asset/deposit-history"),
    "withdrawal_history": ("GET", "/api/v5/asset/withdrawal-history"),
    "ticker": ("GET", "/api/v5/market/ticker"),
}
OKX_BODIES = {
    "time": {"code": "0", "msg": "", "data": [{"ts": str(NOW_MS)}]},
    "config": {"code": "0", "msg": "", "data": [{"acctLv": "1", "autoLoan": False, "enableSpotBorrow": False,
                                                 "spotBorrowAutoRepay": False, "perm": "read_only",
                                                 "ip": "203.0.113.7", "label": "tradegen-e1", "uid": "1",
                                                 "mainUid": "1", "type": "0", "kycLv": "2",
                                                 "mgnIsoMode": "automatic", "ctIsoMode": "automatic",
                                                 "opAuth": "0"}]},
    "balance": {"code": "0", "msg": "", "data": [{"totalEq": "14", "uTime": "1792800000000", "details": [
        {"ccy": "USDT", "eq": "10", "cashBal": "10", "availBal": "10", "frozenBal": "0", "ordFrozen": "0",
         "eqUsd": "10", "liab": "", "interest": "", "autoLendStatus": "off", "autoLendMtAmt": "0",
         "uTime": "1792800000000"}]}]},
    "asset_balances": {"code": "0", "msg": "", "data": [{"ccy": "BTC", "bal": "0.0001", "frozenBal": "0",
                                                         "availBal": "0.0001"}]},
    "positions": {"code": "0", "msg": "", "data": []},
    "asset_valuation": {"code": "0", "msg": "", "data": [{"totalBal": "14", "ts": "1792800000000",
                                                          "details": {"funding": "7", "trading": "7",
                                                                      "classic": "0", "earn": "0"}}]},
    "savings": {"code": "0", "msg": "", "data": []},
    "flexible_loan": {"code": "0", "msg": "", "data": [{"loanData": [], "collateralData": [],
                                                        "loanNotionalUsd": "0"}]},
    "orders_pending": {"code": "0", "msg": "", "data": []},
    "orders_algo_pending": {"code": "0", "msg": "", "data": []},
    "fills": {"code": "0", "msg": "", "data": [{"tradeId": "f1", "ordId": "o0", "billId": "b1", "instId": "BTC-USDT",
                                                "instType": "SPOT", "side": "buy", "fillPx": "70000",
                                                "fillSz": "0.0001", "execType": "T", "fee": "-0.07",
                                                "feeCcy": "USDT", "ts": "1792713600000",
                                                "fillTime": "1792713600000"}]},
    "deposit_history": {"code": "0", "msg": "", "data": [{"ccy": "USDT", "chain": "USDT-TRC20", "amt": "10",
                                                          "from": "", "to": "", "txId": "x1", "ts": "1792627200000",
                                                          "state": "2", "depId": "d1"}]},
    "withdrawal_history": {"code": "0", "msg": "", "data": []},
    "ticker": {"code": "0", "msg": "", "data": [{"instId": "BTC-USDT", "last": "70000", "ts": "1792800000000"}]},
}
OKX_ROWS = {   # rows for the lists the defaults leave empty, and the permission error
    "positions": {"instType": "SWAP", "instId": "BTC-USDT-SWAP", "mgnMode": "cross", "posId": "p1", "posSide": "net",
                  "pos": "1", "availPos": "1", "avgPx": "70000", "upl": "0", "lever": "3", "liab": "",
                  "liabCcy": "", "cTime": "1", "uTime": "1"},
    "savings": {"ccy": "USDT", "amt": "5", "earnings": "0", "rate": "0.01", "loanAmt": "5", "pendingAmt": "0"},
    "orders_pending": {"ordId": "o1", "instId": "BTC-USDT", "instType": "SPOT", "side": "buy", "px": "60000",
                       "sz": "0.0001", "state": "live", "tdMode": "cash", "cTime": "1"},
    "orders_algo_pending": {"algoId": "a1", "instId": "BTC-USDT", "instType": "SPOT", "side": "buy",
                            "px": "60000", "sz": "0.0001", "state": "live", "tdMode": "cash", "cTime": "1"},
    "withdrawal_history": {"ccy": "BTC", "chain": "BTC-Bitcoin", "amt": "0.0001", "ts": "1792627200000",
                           "to": "bc1qfixtureaddress000000000000000000000", "tag": "", "txId": "x2", "fee": "0.0001",
                           "feeCcy": "BTC", "state": "2", "wdId": "w1"},
    "no_permission": {"code": "50120", "msg": "This API key doesn't have permission to use this function",
                      "data": []},
}


def okx_routes(**changes) -> dict:
    """serve() routes for every OKX call, keyed (method, path); a keyword named after an OKX_ROUTES key replaces
    that answer (None drops it; a callable for orders_algo_pending can answer one ordType differently)."""
    return _routes(OKX_ROUTES, OKX_BODIES, changes)
```

  Check the end of the file from the repo root; it must print `True False False` (the block ends the file, no blank
  line after it, no CR anywhere):

```bash
.venv/Scripts/python.exe -c "import pathlib; b = pathlib.Path('tests/execution_fixtures.py').read_bytes(); print(b.endswith(b'    return _routes(OKX_ROUTES, OKX_BODIES, changes)\n'), b.endswith(b'\n\n'), b'\r' in b)"
```

  Any other output means the append went wrong: redo Edit 1a from the file as it now stands before going on.

  Edit 1b: create `tests/execution_okx.py` with exactly this content:

```python
"""OKX inquiry and its read-only self-check (E1 Task 7; contract C11; spec 5 OKX, 6; E25, E26, E32, E37, E38, E39).

Every send goes to `EF.serve` (the OKX answers of contract 3.2, never a live one); the suite's wrapper refuses any
other send. OKX answers its errors on HTTP 200 with a code; transport turns 50120 and 50123 into AuthError.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from urllib.parse import parse_qsl, urlsplit

from execution import keys, okx_inquiry, transport
from execution.snapshot import Holding, Move, Order
from tests import execution_fixtures as EF

PATH = {name: route[1] for name, route in EF.OKX_ROUTES.items()}
SIGNED_BEFORE_ALGO = ("balance", "asset_balances", "positions", "asset_valuation", "savings", "flexible_loan",
                      "orders_pending")
AFTER_ALGO = ("fills", "deposit_history", "withdrawal_history", "ticker")
OKX_KEYS = ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")
GOOD = EF.OKX_BODIES["config"]["data"][0]
ALGO = "/api/v5/trade/orders-algo-pending"


def _path(call: dict) -> str:
    return urlsplit(call["url"]).path


def _query(call: dict) -> str:
    return urlsplit(call["url"]).query


def _run(routes: dict, usdt_krw: float | None = 1400.0, **key_changes):
    """One snapshot at EF.NOW under the fake keys (a keyword changes one; None removes it); (snapshot, calls)."""
    with EF.fake_keys(**key_changes), EF.serve(routes) as calls:
        snap = okx_inquiry.snapshot(EF.NOW, usdt_krw)
    return snap, calls


def _time(offset_ms: int) -> dict:
    return {"code": "0", "msg": "", "data": [{"ts": str(EF.NOW_MS + offset_ms)}]}


def _config(**changes) -> dict:
    return {"code": "0", "msg": "", "data": [dict(GOOD, **changes)]}


def _algo(answers: dict):
    """An orders-algo-pending route that answers each ordType from `answers` (default: no rows)."""
    def answer(call):
        kind = dict(parse_qsl(_query(call)))["ordType"]
        body = answers.get(kind, {"code": "0", "msg": "", "data": []})
        return 200, {"Date": EF.DATE_HEADER}, json.dumps(body).encode("utf-8")
    return answer


def _rows(name: str, *rows) -> dict:
    return {"code": "0", "msg": "", "data": list(rows) if rows else [dict(EF.OKX_ROWS[name])]}


def test_self_check_passes_only_exact_read_only_spot_without_borrow_and_with_an_ip():
    assert okx_inquiry.SELF_CHECK == ("perm", "acctLv", "enableSpotBorrow", "autoLoan", "ip")
    assert okx_inquiry.self_check(GOOD) == frozenset()
    for perm in ("read_only,trade", "trade", "", "read_only,transfer", "read_only,withdraw", "Read_only", "readonly",
                 " read_only", None, ["read_only"]):
        assert okx_inquiry.self_check(dict(GOOD, perm=perm)) == frozenset({"okx_perm"}), perm
    missing = dict(GOOD)
    del missing["perm"]
    assert okx_inquiry.self_check(missing) == frozenset({"okx_perm"})
    for value in ("2", "3", "4", 1, ""):
        assert okx_inquiry.self_check(dict(GOOD, acctLv=value)) == frozenset({"okx_acct_lv"}), value
    for value in (True, "false", 0, None):
        assert okx_inquiry.self_check(dict(GOOD, enableSpotBorrow=value)) == frozenset({"okx_spot_borrow"}), value
        assert okx_inquiry.self_check(dict(GOOD, autoLoan=value)) == frozenset({"okx_auto_loan"}), value
    for value in ("", None, ["203.0.113.7"]):
        assert okx_inquiry.self_check(dict(GOOD, ip=value)) == frozenset({"okx_no_ip"}), value
    assert okx_inquiry.self_check({}) == frozenset({"okx_perm", "okx_acct_lv", "okx_spot_borrow", "okx_auto_loan",
                                                    "okx_no_ip"})


def test_no_keys_means_no_call_at_all():
    for name in OKX_KEYS:
        snap, calls = _run(EF.okx_routes(), **{name: None})
        assert calls == [], [_path(c) for c in calls]           # not even the public time (E32)
        assert not snap.ok and snap.flags == frozenset({"keys_missing"}) and snap.error == f"keys missing: {name}"
        assert transport._okx_offset_s is None


def test_a_failed_self_check_stops_after_account_config():
    for changes, flags, names in (({"perm": "read_only,trade"}, {"okx_perm"}, "perm"),
                                  ({"acctLv": "2", "autoLoan": True}, {"okx_acct_lv", "okx_auto_loan"},
                                   "acctLv, autoLoan"),
                                  ({"perm": "trade", "acctLv": "2"}, {"okx_perm", "okx_acct_lv"},
                                   "perm, acctLv"),                    # SELF_CHECK order, not sorted
                                  ({"enableSpotBorrow": True, "ip": ""}, {"okx_spot_borrow", "okx_no_ip"},
                                   "enableSpotBorrow, ip")):
        snap, calls = _run(EF.okx_routes(config=_config(**changes)))
        assert [_path(c) for c in calls] == [PATH["time"], PATH["config"]]     # nothing after the self-check
        assert not snap.ok and snap.flags == frozenset(flags), snap.flags
        assert snap.error == f"okx self-check failed: {names}", snap.error
        assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0
        assert snap.holdings == {} and snap.response_sha256 == {}


def test_public_time_comes_first_and_sets_the_offset():
    snap, calls = _run(EF.okx_routes(time=_time(3000)))
    assert snap.ok, snap.error
    assert [_path(c) for c in calls[:2]] == [PATH["time"], PATH["config"]]
    assert snap.server_utc == "2026-10-24T00:00:03Z" and snap.clock_offset_s == 3.0
    assert transport._okx_offset_s == 3.0                        # transport's own copy gates every signed call


def test_an_offset_above_25_s_refuses_every_signed_call_with_no_key_read():
    reads, saved = [], keys.read

    def recording(names):
        reads.append(tuple(names))
        return saved(names)
    for offset_ms in (25001, -25001, 120000, -120000):
        reads.clear()
        keys.read = recording
        try:
            snap, calls = _run(EF.okx_routes(time=_time(offset_ms)))
        finally:
            keys.read = saved
        assert [_path(c) for c in calls] == [PATH["time"]], [_path(c) for c in calls]   # no signed call sent
        assert reads == [OKX_KEYS], reads                        # require_keys only: no key read after the time
        assert not snap.ok and snap.flags == frozenset() and "above 25 s; OKX requests not sent" in snap.error
        assert round(snap.clock_offset_s, 3) == offset_ms / 1000   # kept, so CLOCK_SKEW sees it (E39)
    for offset_ms in (25000, -25000):                             # exactly 25 s either way is still within the limit
        snap, _calls = _run(EF.okx_routes(time=_time(offset_ms)))
        assert snap.ok, (offset_ms, snap.error)


def test_an_absurd_server_time_fails_okx_closed():
    snap, calls = _run(EF.okx_routes(time={"code": "0", "msg": "", "data": [{"ts": "1000000000000000"}]}))
    assert [_path(c) for c in calls] == [PATH["time"]]           # year 33658: no signed call follows
    assert not snap.ok and snap.error == "okx: /api/v5/public/time: OverflowError", snap.error   # contained


def test_the_call_order_and_one_algo_call_per_ordtype():
    snap, calls = _run(EF.okx_routes())
    assert snap.ok, snap.error
    algo = [(PATH["orders_algo_pending"], f"ordType={t}") for t in okx_inquiry.ALGO_TYPES]
    assert [(_path(c), _query(c)) for c in calls] == (
        [(PATH["time"], ""), (PATH["config"], "")]
        + [(PATH[n], "ccy=USDT" if n == "asset_valuation" else "") for n in SIGNED_BEFORE_ALGO] + algo
        + [(PATH[n], "instId=BTC-USDT" if n == "ticker" else "") for n in AFTER_ALGO])
    assert len(okx_inquiry.ALGO_TYPES) == 7
    assert all("," not in _query(c) for c in calls if _path(c) == ALGO)   # never a comma list (E25)
    keyed = {f"{ALGO}?ordType={t}" for t in okx_inquiry.ALGO_TYPES}
    plain = {PATH[n] for n in ("time", "config") + SIGNED_BEFORE_ALGO + AFTER_ALGO}
    assert set(snap.response_sha256) == keyed | plain, sorted(snap.response_sha256)   # each algo call its own key
    raw = {f"{ALGO}?ordType=oco": b'{"code": "0", "msg": "", "data": []} '}

    def answer(call):
        key = f"{_path(call)}?{_query(call)}"
        return 200, {"Date": EF.DATE_HEADER}, raw.get(key, b'{"code": "0", "msg": "", "data": []}')
    snap, _calls = _run(EF.okx_routes(orders_algo_pending=answer))
    hashes = snap.response_sha256
    assert hashes[f"{ALGO}?ordType=oco"] == hashlib.sha256(raw[f"{ALGO}?ordType=oco"]).hexdigest()
    assert hashes[f"{ALGO}?ordType=oco"] != hashes[f"{ALGO}?ordType=twap"]


def test_signed_calls_carry_the_okx_headers_and_no_demo_header():
    snap, calls = _run(EF.okx_routes())
    assert snap.ok, snap.error
    public = {PATH["time"], PATH["ticker"]}
    for call in calls:
        names = {k.lower() for k in call["headers"]}
        assert not any("simulated" in n for n in names), names   # never the demo header, on any call
        if _path(call) in public:
            assert not any(n.startswith("ok-access") for n in names), names
            continue
        head = call["headers"]
        assert head["OK-ACCESS-KEY"] == EF.FAKE_KEYS["OKX_API_KEY"]
        assert head["OK-ACCESS-PASSPHRASE"] == EF.FAKE_KEYS["OKX_API_PASSPHRASE"]
        assert head["OK-ACCESS-TIMESTAMP"] == "2026-10-24T00:00:00.000Z"
        target = _path(call) + (f"?{_query(call)}" if _query(call) else "")
        want = base64.b64encode(hmac.new(EF.FAKE_KEYS["OKX_API_SECRET"].encode(),
                                         f"2026-10-24T00:00:00.000ZGET{target}".encode(), hashlib.sha256).digest())
        assert head["OK-ACCESS-SIGN"] == want.decode("ascii"), target


def test_the_full_fixture_gives_every_field():
    fill, algo = EF.OKX_BODIES["fills"]["data"][0], EF.OKX_ROWS["orders_algo_pending"]
    snap, _calls = _run(EF.okx_routes(
        withdrawal_history=_rows("withdrawal_history", dict(EF.OKX_ROWS["withdrawal_history"], fee="0.00002")),
        orders_pending=_rows("orders_pending", dict(EF.OKX_ROWS["orders_pending"], side="sell")),
        orders_algo_pending=_algo({"conditional": _rows("orders_algo_pending"),
                                   "trigger": _rows("orders_algo_pending", dict(algo, algoId="a2", px=""))}),
        fills=_rows("fills", fill, dict(fill, tradeId="f2", side="sell", fillSz="0.00005"))))
    assert snap.ok and snap.error is None and snap.flags == frozenset(), snap.error
    assert snap.venue == "okx" and snap.utc == "2026-10-24T00:00:00Z"
    assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0
    assert dict(snap.holdings) == {"USDT": Holding(units=10.0, locked=0.0), "BTC": Holding(units=0.0001, locked=0.0)}
    assert dict(snap.cash) == {} and snap.deposit_krw is None    # coins, USDT included, are holdings (E16)
    assert dict(snap.prices_krw) == {"USDT": 1400.0, "USDC": 1400.0, "BTC": 70000.0 * 1400.0}
    assert snap.open_orders == (Order(id="o1", symbol="BTC", side="sell", units=0.0001, price=60000.0),
                                Order(id="a1", symbol="BTC", side="buy", units=0.0001, price=60000.0),
                                Order(id="a2", symbol="BTC", side="buy", units=0.0001, price=None))   # px "": None
    assert snap.fills == (Move(id="f1", symbol="BTC", counter="USDT", side="buy", units=0.0001),
                          Move(id="f2", symbol="BTC", counter="USDT", side="sell", units=0.00005))
    assert snap.deposits == (Move(id="d1", symbol="USDT", side="in", units=10.0),)
    assert snap.withdrawals == (Move(id="w1", symbol="BTC", side="out", units=0.0001),)   # amt, never the fee
    assert dict(snap.loans) == {"liab:USDT": 0.0} and dict(snap.earn) == {"asset_valuation": 0.0}
    assert snap.withdrawal_addresses == () and snap.key_expiry is None   # OKX lists no address book


def test_holdings_merge_trading_and_funding():
    routes = EF.okx_routes()
    routes[EF.OKX_ROUTES["balance"]]["data"][0]["details"][0] |= {"cashBal": "10", "frozenBal": "4"}
    routes[EF.OKX_ROUTES["asset_balances"]]["data"] += [
        {"ccy": "USDT", "bal": "2.5", "frozenBal": "0.5", "availBal": "2"},
        {"ccy": "ETH", "bal": "0", "frozenBal": "0", "availBal": "0"}]
    snap, _calls = _run(routes)
    assert snap.ok, snap.error
    assert dict(snap.holdings) == {"USDT": Holding(units=12.5, locked=4.5), "BTC": Holding(units=0.0001, locked=0.0)}


def test_prices_come_from_the_upbit_usdt_price():
    for usdt_krw in (None, 0.0, -1.0, float("nan"), float("inf")):
        snap, _calls = _run(EF.okx_routes(), usdt_krw=usdt_krw)
        assert snap.ok and dict(snap.prices_krw) == {}, (usdt_krw, snap.prices_krw)   # positions then fail closed
    routes = EF.okx_routes()
    routes[EF.OKX_ROUTES["ticker"]]["data"][0]["last"] = "65000.5"
    snap, _calls = _run(routes, usdt_krw=1350.0)
    assert dict(snap.prices_krw) == {"USDT": 1350.0, "USDC": 1350.0, "BTC": 65000.5 * 1350.0}


def test_events_from_a_position_an_order_or_a_fill():
    events = {"instType": "EVENTS", "instId": "EV-1"}
    cases = (EF.okx_routes(positions=_rows("positions", dict(EF.OKX_ROWS["positions"], **events, pos="0"))),
             EF.okx_routes(orders_pending=_rows("orders_pending", dict(EF.OKX_ROWS["orders_pending"], **events))),
             EF.okx_routes(orders_algo_pending=_algo({"trigger": _rows(
                 "orders_algo_pending", dict(EF.OKX_ROWS["orders_algo_pending"], **events))})),
             EF.okx_routes(fills=_rows("fills", dict(EF.OKX_BODIES["fills"]["data"][0], **events))))
    for routes in cases:
        snap, _calls = _run(routes)
        assert snap.ok and snap.flags == frozenset({"EVENTS"}), (snap.error, snap.flags)


def test_derivative_position_only_from_a_nonzero_position():
    swap = dict(EF.OKX_ROWS["positions"])
    for row, flags in ((swap, {"derivative_position"}),
                       (dict(swap, pos="-2"), {"derivative_position"}),
                       (dict(swap, instType="FUTURES", instId="BTC-USD-261225"), {"derivative_position"}),
                       (dict(swap, instType="OPTION", instId="BTC-USD-261225-70000-C"), {"derivative_position"}),
                       (dict(swap, pos="0"), set())):
        snap, _calls = _run(EF.okx_routes(positions=_rows("positions", row)))
        assert snap.ok and snap.flags == frozenset(flags), (row["instType"], row["pos"], snap.flags)
        assert dict(snap.loans) == {"liab:USDT": 0.0}            # a derivative is no loan
    for kind in ("SWAP", "MARGIN"):                              # a size OKX left blank fails closed (E25)
        snap, _calls = _run(EF.okx_routes(positions=_rows("positions", dict(swap, instType=kind, pos=""))))
        assert not snap.ok and snap.error == f"okx: {PATH['positions']}: field pos", (kind, snap.error)


def test_loans_and_earn():
    routes = EF.okx_routes(
        positions=_rows("positions", dict(EF.OKX_ROWS["positions"], instType="MARGIN", instId="BTC-USDT",
                                          pos="-0.5"), dict(EF.OKX_ROWS["positions"], instType="MARGIN",
                                                            instId="ETH-USDT", pos="0")),
        savings=_rows("savings"),
        flexible_loan={"code": "0", "msg": "", "data": [{"loanData": [{"ccy": "USDT", "amt": "3"}],
                                                         "collateralData": [], "loanNotionalUsd": "3"}]})
    details = routes[EF.OKX_ROUTES["balance"]]["data"][0]["details"]
    details[0] |= {"liab": "1.5", "autoLendStatus": "active", "autoLendMtAmt": "2"}
    details.append(dict(details[0], ccy="USDC", cashBal="1", liab="", autoLendStatus="pending", autoLendMtAmt="0"))
    routes[EF.OKX_ROUTES["asset_valuation"]]["data"][0]["details"]["earn"] = "6"
    snap, _calls = _run(routes)
    assert snap.ok and snap.flags == frozenset(), (snap.error, snap.flags)   # MARGIN is a loan, not a derivative
    assert dict(snap.loans) == {"liab:USDT": 1.5, "liab:USDC": 0.0, "margin:BTC-USDT": 0.5,
                                "flexible_loan:USDT": 3.0}, snap.loans
    assert dict(snap.earn) == {"auto_lend:USDT": 2.0, "auto_lend:USDC": 1.0, "asset_valuation": 6.0,
                               "savings:USDT": 5.0}, snap.earn   # pending auto-lend with no matched amount: 1.0


def test_permission_codes_give_auth_error():
    for code in ("50120", "50123"):
        for name in ("config", "balance", "withdrawal_history"):
            body = dict(EF.OKX_ROWS["no_permission"], code=code)
            snap, calls = _run(EF.okx_routes(**{name: body}))
            assert not snap.ok and snap.flags == frozenset({"auth_error"}) and snap.error, (code, name, snap)
            assert _path(calls[-1]) == PATH[name]                # it stopped at the refused call
            assert "permission to use" not in snap.error         # the venue's message text never travels


def test_another_okx_code_fails_closed_without_auth_error():
    for name in ("config", "balance", "ticker"):
        snap, calls = _run(EF.okx_routes(**{name: {"code": "50011", "msg": "fixture text", "data": []}}))
        assert not snap.ok and snap.flags == frozenset() and "50011" in snap.error, (name, snap.error)   # E15
        assert _path(calls[-1]) == PATH[name] and "fixture text" not in snap.error


def test_a_malformed_field_fails_closed_with_names_only():
    cases = (("balance", {"code": "0", "msg": "", "data": [{"details": [{"ccy": "USDT", "cashBal": "1e999",
                                                                          "frozenBal": "0", "liab": "",
                                                                          "autoLendStatus": "off",
                                                                          "autoLendMtAmt": "0"}]}]},
              PATH["balance"], "field cashBal"),
             ("asset_balances", {"code": "0", "msg": "", "data": [{"ccy": "BTC", "bal": 0.0001, "frozenBal": "0"}]},
              PATH["asset_balances"], "field bal"),
             ("fills", _rows("fills", dict(EF.OKX_BODIES["fills"]["data"][0], instId="BTCUSDT")), PATH["fills"],
              "field instId"),
             ("asset_valuation", {"code": "0", "msg": "", "data": [{"details": {"funding": "7"}}]},
              PATH["asset_valuation"], "field earn"),
             ("flexible_loan", {"code": "0", "msg": "", "data": [{"loanData": "none"}]}, PATH["flexible_loan"],
              "field loanData"),
             ("ticker", {"code": "0", "msg": "", "data": []}, PATH["ticker"], "field data"))
    for name, body, path, tail in cases:
        snap, _calls = _run(EF.okx_routes(**{name: body}))
        assert not snap.ok and snap.flags == frozenset(), name
        assert snap.error == f"okx: {path}: {tail}", snap.error
        assert "1e999" not in snap.error and "0.0001" not in snap.error


def test_a_refused_send_propagates():
    with EF.fake_keys():
        try:
            okx_inquiry.snapshot(EF.NOW, 1400.0)                 # no serve(): the suite's refusing stub answers
        except EF.Refused:
            pass
        else:
            raise AssertionError("a refused send became a snapshot")
    assert len(EF.STRAYS) == 1 and EF.STRAYS[0].endswith(PATH["time"]), EF.STRAYS   # the public time, refused
    EF.STRAYS.clear()
```

- [ ] **Step 2: Run to verify it fails**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_okx/
```

  Expected: 18 `FAIL` lines, each after its traceback on stderr, exit code 1:
  `FAIL execution_okx/test_self_check_passes_only_exact_read_only_spot_without_borrow_and_with_an_ip
  AttributeError: module 'execution.okx_inquiry' has no attribute 'SELF_CHECK'`, and for each of the other 17 tests
  `FAIL execution_okx/<test> AttributeError: module 'execution.okx_inquiry' has no attribute 'snapshot'`; the last
  line is `0/18 passed, 18 failed, 0 not run`. Any other failure (`execution_okx/import`, `KeyError: no such route`)
  means Step 1 went wrong: fix it before Step 3.

- [ ] **Step 3: Implement**

  Re-read `execution/okx_inquiry.py` first. Two Edit-tool replacements; the file stays LF and Task 2's constants
  (`ENDPOINTS`, `PUBLIC`, `ALGO_TYPES`) stay byte for byte.

  Edit 3a, anchor: the module docstring and the future import above `ENDPOINTS = frozenset({`. old_string (Task 2's
  text, the first five lines of the file):

```python
"""OKX read-only inquiry (E1 spec 5, the OKX table; contract section 7; E10, E25): the endpoint allowlist, its two
public paths and the algo order types, read one per call. transport.request reads ENDPOINTS and PUBLIC at call time.
The single-order trade path is not listed: the same path also serves the order POST. Task 7 adds the
self-check and the snapshot."""
from __future__ import annotations
```

  If the docstring in the file differs (DRIFT RULE, contract 0.6), use the file's own docstring and future import
  as old_string and record a one-line ruling in the execution ledger. new_string:

```python
"""OKX read-only inquiry (E1 spec 5 and 6; plan C7, C11): the frozen allowlist, the read-only self-check and the OKX
snapshot of one poll. Nothing is sent while the OKX keys are missing; public/time comes first, since its offset
gates every signed call (E32); a failed self-check stops OKX for that poll. OKX lists no withdrawal address book,
so OKX addresses are not checked."""
from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

from core.compliance import model
from execution.snapshot import FieldError, Holding, Move, Order, Snapshot, failed
from execution.transport import AuthError, InquiryError, InquiryRefused, KeyMissing, request, require_keys
```

  Edit 3b, anchor: the last constant line. old_string:

```python
ALGO_TYPES = ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")
```

  new_string (that line, one blank line, then the self-check, the snapshot and their helpers):

```python
ALGO_TYPES = ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")

SELF_CHECK = ("perm", "acctLv", "enableSpotBorrow", "autoLoan", "ip")

_FLAGS = ("okx_perm", "okx_acct_lv", "okx_spot_borrow", "okx_auto_loan", "okx_no_ip")   # one per SELF_CHECK name
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)   # epoch + timedelta: an absurd ts is OverflowError, never the
                                                    # OSError that datetime.fromtimestamp raises on Windows
_TIME = "/api/v5/public/time"
_CONFIG = "/api/v5/account/config"
_BALANCE = "/api/v5/account/balance"
_FUNDING = "/api/v5/asset/balances"
_POSITIONS = "/api/v5/account/positions"
_VALUATION = "/api/v5/asset/asset-valuation"
_SAVINGS = "/api/v5/finance/savings/balance"
_LOANS = "/api/v5/finance/flexible-loan/loan-info"
_PENDING = "/api/v5/trade/orders-pending"
_ALGO = "/api/v5/trade/orders-algo-pending"
_FILLS = "/api/v5/trade/fills"
_DEPOSITS = "/api/v5/asset/deposit-history"
_WITHDRAWALS = "/api/v5/asset/withdrawal-history"
_TICKER = "/api/v5/market/ticker"
_BEFORE_ALGO = ((_BALANCE, None), (_FUNDING, None), (_POSITIONS, None), (_VALUATION, [("ccy", "USDT")]),
                (_SAVINGS, None), (_LOANS, None), (_PENDING, None))
_AFTER_ALGO = ((_FILLS, None), (_DEPOSITS, None), (_WITHDRAWALS, None), (_TICKER, [("instId", "BTC-USDT")]))
_CONTAINED = (KeyMissing, InquiryRefused, InquiryError, LookupError, ValueError, TypeError, AttributeError,
              ArithmeticError)                      # E38: the venue's own errors (AuthError and FieldError included)


def self_check(config: Mapping) -> frozenset[str]:
    """The failed flags of the key and account self-check (spec 5): `perm` exactly "read_only" (OKX may report
    permissions its docs do not list), spot mode, spot borrow and auto-loan off, and a bound IP. Pure."""
    ip = config.get("ip")
    passed = (config.get("perm") == "read_only", config.get("acctLv") == "1",
              config.get("enableSpotBorrow") is False, config.get("autoLoan") is False,
              isinstance(ip, str) and ip != "")
    return frozenset(flag for flag, ok in zip(_FLAGS, passed) if not ok)


def snapshot(now: datetime, usdt_krw: float | None) -> Snapshot:
    """The OKX snapshot of the poll at `now` (C11); `usdt_krw` is Upbit's KRW-USDT price of this poll, or None. A
    venue error gives a failed snapshot whose text holds names, paths and codes only (E37, E38); a refused write, the
    suite's refusing stub and a programming error propagate."""
    utc, path, answers, server_utc, offset = model.iso_utc(now), _TIME, {}, None, None
    try:
        require_keys("okx")                                 # no call at all while the keys are missing (E32)
        answers[path] = request("okx", "GET", path)
        ts = _num(_one(answers[path].body, "data"), "ts") / 1000
        server_utc = model.iso_utc(_EPOCH + timedelta(seconds=ts))
        offset = ts - answers[path].received_utc.timestamp()      # transport keeps the same offset for its check
        path = _CONFIG
        answers[path] = request("okx", "GET", path)
        bad = self_check(_one(answers[path].body, "data"))
        if bad:
            names = ", ".join(name for name, flag in zip(SELF_CHECK, _FLAGS) if flag in bad)
            return failed("okx", utc, f"okx self-check failed: {names}", flags=bad, server_utc=server_utc,
                          clock_offset_s=offset)
        for path, params in _BEFORE_ALGO:
            answers[path] = request("okx", "GET", path, params)
        path = _ALGO
        for kind in ALGO_TYPES:                             # one call per ordType, never a comma list (E25)
            answers[f"{_ALGO}?ordType={kind}"] = request("okx", "GET", path, [("ordType", kind)])
        for path, params in _AFTER_ALGO:
            answers[path] = request("okx", "GET", path, params)
        flags, units, locked, loans, earn = set(), {}, {}, {}, {}
        path = _BALANCE
        for row in _list(_one(answers[path].body, "data"), "details"):
            ccy = _field(row, "ccy")
            _add(units, ccy, _num(row, "cashBal"))
            _add(locked, ccy, _num(row, "frozenBal"))
            _add(loans, f"liab:{ccy}", _num(row, "liab"))
            if _field(row, "autoLendStatus") in ("pending", "active"):
                _add(earn, f"auto_lend:{ccy}", _num(row, "autoLendMtAmt") or 1.0)
        path = _FUNDING
        for row in _list(answers[path].body, "data"):
            ccy = _field(row, "ccy")
            _add(units, ccy, _num(row, "bal"))
            _add(locked, ccy, _num(row, "frozenBal"))
        path = _POSITIONS
        for row in _list(answers[path].body, "data"):
            kind = _field(row, "instType")
            if kind == "EVENTS":
                flags.add("EVENTS")                         # any EVENTS row, even one of size 0 (okx.md correction 8)
                continue
            if _field(row, "pos") == "":
                raise FieldError("pos")                     # a position always has a size: "" fails closed (E25)
            size = _num(row, "pos")
            if size == 0:
                continue                                    # a zero row is no exposure (okx.md correction 7)
            if kind == "MARGIN":
                _add(loans, f"margin:{_field(row, 'instId')}", abs(size))
            else:                                           # SWAP, FUTURES, OPTION, and any type OKX adds later
                flags.add("derivative_position")
        path = _VALUATION
        earn["asset_valuation"] = _num(_field(_one(answers[path].body, "data"), "details"), "earn")
        path = _SAVINGS
        for row in _list(answers[path].body, "data"):
            _add(earn, f"savings:{_field(row, 'ccy')}", _num(row, "amt"))
        path = _LOANS
        for info in _list(answers[path].body, "data"):
            for row in _list(info, "loanData"):
                _add(loans, f"flexible_loan:{_field(row, 'ccy')}", _num(row, "amt"))
        orders, fills = [], []
        for key in (_PENDING,) + tuple(f"{_ALGO}?ordType={kind}" for kind in ALGO_TYPES):
            path = key.partition("?")[0]
            for row in _list(answers[key].body, "data"):
                if _field(row, "instType") == "EVENTS":
                    flags.add("EVENTS")
                order_id = _field(row, "ordId" if path == _PENDING else "algoId")
                orders.append(Order(id=order_id, symbol=_pair(row)[0], side=_field(row, "side"),
                                    units=_num(row, "sz"), price=_num(row, "px") or None))
        path = _FILLS
        for row in _list(answers[path].body, "data"):
            if _field(row, "instType") == "EVENTS":
                flags.add("EVENTS")
            base, quote = _pair(row)
            fills.append(Move(id=_field(row, "tradeId"), symbol=base, counter=quote, side=_field(row, "side"),
                              units=_num(row, "fillSz")))
        path = _DEPOSITS
        deposits = tuple(Move(id=_field(r, "depId"), symbol=_field(r, "ccy"), side="in", units=_num(r, "amt"))
                         for r in _list(answers[path].body, "data"))
        path = _WITHDRAWALS
        withdrawals = tuple(Move(id=_field(r, "wdId"), symbol=_field(r, "ccy"), side="out", units=_num(r, "amt"))
                            for r in _list(answers[path].body, "data"))
        path = _TICKER
        last, prices = _num(_one(answers[path].body, "data"), "last"), {}
        if usdt_krw is not None and math.isfinite(usdt_krw) and usdt_krw > 0:   # other coins stay unpriced (E17)
            prices = {"USDT": usdt_krw, "USDC": usdt_krw, "BTC": last * usdt_krw}
        return Snapshot(venue="okx", utc=utc, server_utc=server_utc, clock_offset_s=offset, ok=True,
                        holdings={c: Holding(units=u, locked=locked[c]) for c, u in units.items() if u > 0},
                        open_orders=tuple(orders), fills=tuple(fills), deposits=deposits, withdrawals=withdrawals,
                        loans=loans, earn=earn, flags=frozenset(flags), prices_krw=prices,
                        response_sha256={k: a.sha256 for k, a in answers.items()})
    except _CONTAINED as exc:
        return _failed(utc, path, exc, server_utc, offset)


def _failed(utc: str, path: str, exc: Exception, server_utc: str | None, offset: float | None) -> Snapshot:
    """A contained venue error as a failed snapshot (E38); the text is built from names only, never str() of a
    parse or network error (E37). It keeps the clock offset, so CLOCK_SKEW still sees a refused poll (E39)."""
    if isinstance(exc, KeyMissing):
        error, flags = f"keys missing: {exc.name}", frozenset({"keys_missing"})
    elif isinstance(exc, AuthError):
        error, flags = str(exc), frozenset({"auth_error"})
    elif isinstance(exc, (InquiryRefused, InquiryError)):
        error, flags = str(exc), frozenset()
    elif isinstance(exc, FieldError):
        error, flags = f"okx: {path}: field {exc.args[0]}", frozenset()
    else:
        error, flags = f"okx: {path}: {type(exc).__name__}", frozenset()
    return failed("okx", utc, error, flags=flags, server_utc=server_utc, clock_offset_s=offset)


def _add(totals: dict, key: str, amount: float) -> None:
    totals[key] = totals.get(key, 0.0) + amount


def _pair(row) -> tuple[str, str]:
    """(base, quote) of an instId such as BTC-USDT or BTC-USDT-SWAP."""
    inst = _field(row, "instId")
    base, _, rest = inst.partition("-") if isinstance(inst, str) else ("", "", "")
    if not base or not rest:
        raise FieldError("instId")
    return base, rest.partition("-")[0]


def _field(row, name: str):
    """row[name]; FieldError(name) when row is not a dict or lacks it (E37)."""
    if not isinstance(row, dict) or name not in row:
        raise FieldError(name)
    return row[name]


def _num(row, name: str) -> float:
    """A finite number from an OKX string ("" means not applicable, so 0); otherwise FieldError(name), never the
    value."""
    value = _field(row, name)
    if not isinstance(value, str):
        raise FieldError(name)
    try:
        number = 0.0 if value == "" else float(value)
    except ValueError:
        raise FieldError(name) from None
    if not math.isfinite(number):
        raise FieldError(name)
    return number


def _one(body, name: str) -> dict:
    """body[name] as one dict: the dict itself, or the first row of a non-empty list."""
    value = _field(body, name)
    if isinstance(value, list) and value:
        value = value[0]
    if not isinstance(value, dict):
        raise FieldError(name)
    return value


def _list(body, name: str) -> list:
    """body[name], which must be a list."""
    rows = _field(body, name)
    if not isinstance(rows, list):
        raise FieldError(name)
    return rows
```

  Do not name the OKX demo header, the single-order path or any Upbit or KIS path in a comment or docstring (the
  guards read them).

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check before EACH command below (the Git Bash prefix does it). All from the repo root.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_okx/
```

  Expected: 18 lines `PASS execution_okx/test_<name>`, then `18/18 passed, 0 failed, 0 not run` (exit code 0).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/
```

  Expected: only `PASS execution_guards/<name>` lines, then `G/G passed, 0 failed, 0 not run` with the same G as at
  the end of Task 6 (this task adds no guard test).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance
```

  Expected (no argument: every entry so far, in process, no results file): only `PASS` lines, the last one
  `N/N passed, 0 failed, 0 not run`, where N is G plus the tests of the keys, transport and snapshot modules (Tasks 2
  to 4) plus 48 for the three venue modules (19 + 11 + 18); Tasks 5 and 6 stay green after this task's fixture
  append.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; t(); u(); print('T-RO-01 ok')"
```

  Expected: `T-RO-01 ok`.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.acceptance import test_08_no_broker_order_path as a, test_09_no_account_credentials_requested as b, test_16_every_source_file_is_utf8_readable as c, test_18_eodhd_is_gone_from_the_runtime as d; a(); b(); c(); d(); print('cockpit scans ok')"
```

  Expected: `cockpit scans ok`.

```bash
git status --short
```

  Expected: exactly ` M execution/okx_inquiry.py`, ` M tests/execution_fixtures.py` and `?? tests/execution_okx.py`,
  plus ` M docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` when Step 1 or Edit 3a recorded
  a drift ruling.

- [ ] **Step 5: Commit**

```bash
git add execution/okx_inquiry.py tests/execution_fixtures.py tests/execution_okx.py
```

  When Step 1 or Edit 3a recorded a drift ruling, also run
  `git add docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`. Then:

```bash
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (every staged file is LF). Then commit. In the trailer, replace
  `<the committing model>` with the name of the model that writes this commit, for example `Claude Sonnet 5.5` or
  `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "feat(execution): OKX read-only self-check and inquiry snapshot" -m "Task 7: okx_inquiry.self_check (perm exactly read_only, spot mode, no borrow, no auto-loan, a bound IP) and snapshot (keys first, then public/time and the self-check; balances, earn, loans, orders, seven algo calls, fills, moves; EVENTS and derivative flags), the OKX answers and tests/execution_okx.py." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
```
