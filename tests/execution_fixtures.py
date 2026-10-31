"""Fixtures for the execution suite (E1 plan; contract section 3.2). Task 1 adds the constants, the recorders and the
first part of `isolated()`; Task 2 adds the transport seams and `fake_keys()`, Task 3 `serve()`, Task 4 `snap()` and
Tasks 5 to 7 the venue answers. Nothing here imports `execution` at module level, so a broken or missing module fails
only the tests that use it."""
from __future__ import annotations

import contextlib
import json
import os
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit

NOW = datetime(2026, 10, 24, 0, 0, 0, tzinfo=timezone.utc)      # 09:00 KST, a Saturday
DATE_HEADER = "Sat, 24 Oct 2026 00:00:00 GMT"
FAKE_KEYS = {"KIS_APP_KEY": "test-kis-appkey", "KIS_APP_SECRET": "test-kis-appsecret",
             "KIS_ACCOUNT_8": "12345678", "KIS_ACCOUNT_PD": "01",
             "UPBIT_ACCESS_KEY": "test-upbit-access", "UPBIT_SECRET_KEY": "test-upbit-secret",
             "OKX_API_KEY": "test-okx-key", "OKX_API_SECRET": "test-okx-secret", "OKX_API_PASSPHRASE": "test-okx-pass"}
KEY_NAMES = tuple(FAKE_KEYS) + ("KIS_BASE_URL",)
_MISSING = object()


class Refused(RuntimeError):
    """What the suite's stubs raise: an E1 send that no test routed."""


TOASTS: list[tuple[str, str]] = []      # (title, body) of every patched alerts._toast call; cleared by isolated()
SLEEPS: list[float] = []                # seconds of every patched transport._sleep call (Task 2); cleared by isolated()
STRAYS: list[str] = []                  # every refused or unrouted send ("METHOD url-path"); cleared by isolated();
                                        # a test that expects one asserts on it and then clears it
REAL_SEND = None                        # Task 2: the unpatched transport._send while isolated() is active


def _record_toast(title: str, body: str) -> bool:
    """Stands in for core.compliance.alerts._toast: records the toast, shows nothing and reports it shown."""
    TOASTS.append((title, body))
    return True


@contextlib.contextmanager
def isolated(home: Path) -> Iterator[None]:
    """The E1 seams for one test (E28), inside the wrapper's temp home `home`: the recorders are cleared, every name
    of KEY_NAMES leaves os.environ (config's load_dotenv put the real values there), alerts._toast is the recorder,
    and (Task 2) transport._send refuses and records a stray, REAL_SEND holds the unpatched _send (an outer
    isolated()'s, when nested), transport._sleep records into SLEEPS, transport._clock returns NOW, no token gap, OKX
    offset or bad token carries over, and keys._ENV_FILE is a missing file in `home`, so the repo .env is never
    read. On the way out each patch is undone in reverse order and each key name gets its value from before the
    test back (one that was absent is removed again, whatever the test set). A test that returns normally with an
    entry left in STRAYS fails here."""
    from core.compliance import alerts
    from execution import keys, transport
    patches = [(alerts, "_toast", _record_toast),
               (sys.modules[__name__], "REAL_SEND", REAL_SEND or transport._send),
               (transport, "_send", _refuse_send), (transport, "_sleep", SLEEPS.append),
               (transport, "_clock", lambda: NOW), (transport, "_next_issue_at", None),
               (transport, "_okx_offset_s", None), (transport, "_bad_tokens", set()),
               (keys, "_ENV_FILE", home / "no-such.env")]
    TOASTS.clear()
    SLEEPS.clear()
    STRAYS.clear()
    env = {name: os.environ.pop(name, None) for name in KEY_NAMES}
    saved = []
    try:
        for obj, name, value in patches:
            saved.append((obj, name, vars(obj).get(name, _MISSING)))
            setattr(obj, name, value)
        yield
        assert not STRAYS, f"a refused or unrouted E1 send in a test that passed: {STRAYS}"
    finally:
        for obj, name, original in reversed(saved):
            if original is _MISSING:
                delattr(obj, name)
            else:
                setattr(obj, name, original)
        for name, value in env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _refuse_send(method, url, *, headers, params, json_body, timeout):
    """Stands in for execution.transport._send under the suite (Task 2): records "METHOD path" in STRAYS (the
    path only: a KIS query holds the account number) and raises Refused, so no test can reach a venue."""
    STRAYS.append(f"{method} {urlsplit(url).path}")
    raise Refused("E1 transport send inside the execution suite")


@contextlib.contextmanager
def fake_keys(**overrides) -> Iterator[None]:
    """os.environ holds FAKE_KEYS with `overrides` applied (a None override removes that name); every name touched
    is back in its state at entry afterwards."""
    values = FAKE_KEYS | overrides
    saved = {name: os.environ.get(name) for name in values}
    try:
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class Seq(tuple):
    """A serve() route answered one entry per call, in order (`Seq(first, second)` answers the first call with
    `first` and the second with `second`). A call after the last entry is unrouted."""

    def __new__(cls, *answers):
        return super().__new__(cls, answers)


@contextlib.contextmanager
def serve(routes: Mapping, *, date: str = DATE_HEADER) -> Iterator[list[dict]]:
    """transport._send -> a router over `routes` for one block (Task 3; contract 3.2), restored on exit (isolated()
    puts the refusing stub back in any case). A route maps (method, path) to a JSON body (a dict, or a list: Upbit
    answers with lists) sent with HTTP 200, to (status, body), to a Seq of these answers or to a callable
    `call -> (status, headers, body_bytes)`. Every call is recorded, in order, in the list this yields, as a dict of
    method, url, path, query, headers (a copy), json_body, params and timeout. A call with params, a timeout other
    than 10.0 or no answer left appends "METHOD path" to STRAYS and raises AssertionError. Every answer but a
    callable's carries the Date header `date`."""
    from execution import transport
    calls, used = [], {}

    def send(method, url, *, headers, params, json_body, timeout):
        parts = urlsplit(url)
        call = {"method": method, "url": url, "path": parts.path, "query": parts.query, "headers": dict(headers),
                "json_body": json_body, "params": params, "timeout": timeout}
        calls.append(call)
        key = (method, parts.path)
        answer = routes.get(key, _MISSING)
        if isinstance(answer, Seq):
            used[key] = used.get(key, 0) + 1
            answer = answer[used[key] - 1] if used[key] <= len(answer) else _MISSING
        if answer is _MISSING or params is not None or timeout != 10.0:
            STRAYS.append(f"{method} {parts.path}")
            why = "" if answer is _MISSING else ": params/timeout"
            raise AssertionError(f"unrouted {method} {parts.path}{why}")
        if callable(answer):
            return answer(call)
        status, body = answer if isinstance(answer, tuple) else (200, answer)
        return status, {"Date": date}, json.dumps(body).encode("utf-8")

    keep = transport._send
    transport._send = send
    try:
        yield calls
    finally:
        transport._send = keep


# --------------------------------------------------------------------------- #
# Task 4: snapshots (contract 3.2)
# --------------------------------------------------------------------------- #
def snap(venue: str, **fields) -> "Snapshot":
    """An ok `execution.snapshot.Snapshot` of `venue` stamped NOW (venue time NOW, offset 0.0); `fields` override
    any of these or set any other field. execution is imported here, never at module level (contract 3.2)."""
    from core.compliance import model
    from execution.snapshot import Snapshot
    base = {"venue": venue, "utc": model.iso_utc(NOW), "server_utc": model.iso_utc(NOW), "clock_offset_s": 0.0,
            "ok": True}
    return Snapshot(**(base | fields))


import copy

# --------------------------------------------------------------------------- #
# Task 5: the KIS answers (contract 3.2; shaped like the KIS docs' examples, never captured from a live account).
# Not in the research tables, accepted as [assumed] (E1R2-5; a live mismatch fails KIS closed): the output1/output2
# containers of inquire-account-balance, the output container of intgr-margin and inquire-ccnl, the inquire-nccs row
# fields, ord_dt and sll_buy_dvsn_cd of an inquire-ccnl row, and crcy_cd of inquire-present-balance.
# --------------------------------------------------------------------------- #
KIS_ROUTES = {
    "token": ("POST", "/oauth2/tokenP"),
    "balance": ("GET", "/uapi/domestic-stock/v1/trading/inquire-balance"),
    "psbl_rvsecncl": ("GET", "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"),
    "daily_ccld": ("GET", "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"),
    "account_balance": ("GET", "/uapi/domestic-stock/v1/trading/inquire-account-balance"),
    "intgr_margin": ("GET", "/uapi/domestic-stock/v1/trading/intgr-margin"),
    "ovrs_balance": ("GET", "/uapi/overseas-stock/v1/trading/inquire-balance"),
    "nccs": ("GET", "/uapi/overseas-stock/v1/trading/inquire-nccs"),
    "ccnl": ("GET", "/uapi/overseas-stock/v1/trading/inquire-ccnl"),
    "present_balance": ("GET", "/uapi/overseas-stock/v1/trading/inquire-present-balance"),
}
KIS_BODIES = {
    "token": {"access_token": "test-token-1", "token_type": "Bearer", "expires_in": 86400,
              "access_token_token_expired": "2026-10-25 09:00:00"},
    "balance": {"rt_cd": "0", "msg_cd": "KIOK0510", "msg1": "", "ctx_area_fk100": "", "ctx_area_nk100": "",
                "output1": [{"pdno": "005930", "prdt_name": "005930", "hldg_qty": "1", "ord_psbl_qty": "1",
                             "pchs_avg_pric": "60000.0000", "pchs_amt": "60000", "prpr": "61000", "evlu_amt": "61000",
                             "loan_dt": "", "loan_amt": "0"}],
                "output2": [{"dnca_tot_amt": "21000", "nxdy_excc_amt": "20000", "prvs_rcdl_excc_amt": "20000",
                             "tot_evlu_amt": "81000", "nass_amt": "81000", "scts_evlu_amt": "61000",
                             "tot_loan_amt": "0"}]},
    "psbl_rvsecncl": {"rt_cd": "0", "msg_cd": "", "msg1": "", "output": []},
    "daily_ccld": {"rt_cd": "0", "output1": [{"ord_dt": "20261023", "odno": "0000123455", "orgn_odno": "",
                                              "sll_buy_dvsn_cd": "02", "pdno": "005930", "ord_qty": "1",
                                              "ord_unpr": "61000", "ord_tmd": "093000", "tot_ccld_qty": "1",
                                              "avg_prvs": "61000", "tot_ccld_amt": "61000", "cncl_yn": "N",
                                              "rmn_qty": "0", "rjct_qty": "0"}], "output2": {}},
    "account_balance": {"rt_cd": "0", "output1": [],
                        "output2": {"tot_asst_amt": "81000", "nass_tot_amt": "81000", "tot_dncl_amt": "21000",
                                    "dncl_amt": "21000", "frcr_evlu_tota": "0", "ovrs_stck_evlu_amt1": "0",
                                    "thdt_rcvb_amt": "0", "crdt_fncg_amt": "0"}},
    "intgr_margin": {"rt_cd": "0", "output": {"acmga_rt": "20", "acmga_pct100_aptm_rson": "",
                                              "stck_cash_ord_psbl_amt": "20000", "rcvb_amt": "0"}},
    "ovrs_balance": {"rt_cd": "0", "output1": [{"ovrs_pdno": "AAPL", "ovrs_cblc_qty": "1", "ord_psbl_qty": "1",
                                                "pchs_avg_pric": "200.0000", "frcr_pchs_amt1": "200",
                                                "ovrs_stck_evlu_amt": "210", "now_pric2": "210.00000000",
                                                "frcr_evlu_pfls_amt": "10", "tr_crcy_cd": "USD",
                                                "ovrs_excg_cd": "NASD"}],
                     "output2": {"tot_evlu_pfls_amt": "10", "frcr_buy_amt_smtl1": "200"}},
    "nccs": {"rt_cd": "0", "output": []},
    "ccnl": {"rt_cd": "0", "output": []},
    "present_balance": {"rt_cd": "0", "output1": [],
                        "output2": [{"crcy_cd": "USD", "frcr_dncl_amt_2": "5.00", "frcr_drwg_psbl_amt_1": "5.00",
                                     "frst_bltn_exrt": "1390.50"}],
                        "output3": {"tot_asst_amt": "0", "tot_dncl_amt": "0", "wdrw_psbl_tot_amt": "0",
                                    "frcr_use_psbl_amt": "0", "frcr_evlu_tota": "0"}},
}
KIS_ROWS = {   # one row for each list the default answers leave empty
    "psbl_rvsecncl": {"odno": "0000123456", "orgn_odno": "", "pdno": "005930", "ord_qty": "1", "ord_unpr": "60000",
                      "tot_ccld_qty": "0", "psbl_qty": "1", "sll_buy_dvsn_cd": "02", "ord_dvsn_cd": "00",
                      "excg_id_dvsn_cd": "KRX"},
    "nccs": {"odno": "0000223456", "pdno": "AAPL", "ft_ord_qty": "1", "ft_ord_unpr3": "200", "nccs_qty": "1",
             "sll_buy_dvsn_cd": "02"},
    "ccnl": {"ord_dt": "20261023", "odno": "0000223455", "orgn_odno": "", "pdno": "AAPL", "ft_ord_qty": "1",
             "ft_ord_unpr3": "200", "ft_ccld_qty": "1", "ft_ccld_unpr3": "200", "ft_ccld_amt3": "200", "nccs_qty": "0",
             "prcs_stat_name": "", "rjct_rson": "", "tr_crcy_cd": "USD", "sll_buy_dvsn_cd": "02"},
}


def _routes(table: dict, bodies: dict, changes: dict) -> dict:
    """{(method, path): answer} for serve(): a fresh deep copy of every default answer, or the change named after its
    route (any answer form serve() takes, used as given); a None change drops that route. An unknown name is a
    KeyError, so a typo cannot pass silently."""
    unknown = sorted(set(changes) - set(table))
    if unknown:
        raise KeyError(f"no such route: {unknown}")
    out = {}
    for name, route in table.items():
        answer = changes[name] if name in changes else copy.deepcopy(bodies[name])
        if answer is not None:
            out[route] = answer
    return out


def kis_routes(**changes) -> dict:
    """serve() routes for every KIS call, the token POST included, keyed (method, path) as serve() takes them, so the
    three venues' routes merge with `|`. A keyword named after a KIS_ROUTES key replaces that answer."""
    return _routes(KIS_ROUTES, KIS_BODIES, changes)


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
