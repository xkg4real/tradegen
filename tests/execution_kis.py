"""KIS inquiry (E1 Task 5; contract C9; spec 5 KIS, 6; E14, E16, E17, E26, E37, E38, E39, E42).

Every send goes to `EF.serve` (the KIS answers of contract 3.2, never a live one); the suite's wrapper refuses any
other send. Every ok case passes `F.ctx()` (sealed, `code_signed=True`): KIS sends nothing under unsigned code.
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from core.compliance import model
from execution import keys, kis_inquiry, transport
from execution.snapshot import Holding, Move, Order
from tests import compliance_fixtures as F
from tests import execution_fixtures as EF

ROOT = Path(__file__).resolve().parents[1]
PATH = {name: route[1] for name, route in EF.KIS_ROUTES.items()}
GETS = ("balance", "psbl_rvsecncl", "daily_ccld", "account_balance", "intgr_margin", "ovrs_balance", "nccs", "ccnl",
        "present_balance")                          # the order of contract C9
ACCOUNT_ERROR = "kis: KIS account number is not 8 + 2 digits"


def _path(call: dict) -> str:
    return urlsplit(call["url"]).path


def _pairs(call: dict) -> list[tuple[str, str]]:
    """The sent query as (key, value) pairs, exactly as on the wire (not unquoted)."""
    return [tuple(p.split("=", 1)) for p in urlsplit(call["url"]).query.split("&")]


def _only(calls: list, name: str) -> dict:
    found = [c for c in calls if _path(c) == PATH[name]]
    assert len(found) == 1, (name, len(found))
    return found[0]


def _full() -> dict:
    """kis_routes() with one row in each list the defaults leave empty."""
    routes = EF.kis_routes()
    for name in ("psbl_rvsecncl", "nccs", "ccnl"):
        routes[EF.KIS_ROUTES[name]]["output"] = [dict(EF.KIS_ROWS[name])]
    return routes


def _run(routes: dict, ctx=None, **key_changes):
    """One snapshot at EF.NOW under the fake keys (a keyword changes one; None removes it); (snapshot, calls)."""
    with EF.fake_keys(**key_changes), EF.serve(routes) as calls:
        snap = kis_inquiry.snapshot(EF.NOW, F.ctx() if ctx is None else ctx)
    return snap, calls


def _no_key_read(names):
    raise AssertionError(f"keys.read({tuple(names)}) under unsigned code")


def _names_only(error: str) -> bool:
    """True when a failure text holds neither the fake account number nor the account field (E37)."""
    return EF.FAKE_KEYS["KIS_ACCOUNT_8"] not in error and "CANO" not in error


def test_the_signed_code_gate_is_the_first_statement():
    tree = ast.parse((ROOT / "execution" / "kis_inquiry.py").read_text(encoding="utf-8"))
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "snapshot"), None)
    assert fn is not None, "kis_inquiry.snapshot is not defined"
    body = fn.body[1:] if ast.get_docstring(fn) else fn.body
    gate = body[0]
    assert isinstance(gate, ast.If) and not gate.orelse, ast.unparse(gate)
    assert ast.unparse(gate.test) == "not (model.is_sealed(ctx) and ctx.code_signed is True)", ast.unparse(gate.test)
    assert [ast.unparse(s) for s in gate.body] == [
        "return failed('kis', model.iso_utc(now), 'code not signed', flags=frozenset({'code_unsigned'}))"]


def test_kis_sends_nothing_and_reads_no_key_unless_the_code_is_signed():
    unsealed = dataclasses.replace(F.ctx())
    assert not model.is_sealed(unsealed)
    for ctx in (F.ctx(code_signed=False), F.ctx(code_signed=1), unsealed, None):
        saved = keys.read
        keys.read = _no_key_read
        try:
            with EF.fake_keys(), EF.serve(_full()) as calls:
                snap = kis_inquiry.snapshot(EF.NOW, ctx)
        finally:
            keys.read = saved
        assert calls == [], [_path(c) for c in calls]                # not even the token POST
        assert not snap.ok and snap.error == "code not signed", snap.error
        assert snap.flags == frozenset({"code_unsigned"}) and snap.utc == "2026-10-24T00:00:00Z"
        assert snap.holdings == {} and snap.response_sha256 == {} and snap.server_utc is None
    snap, calls = _run(_full())
    assert snap.ok and snap.error is None and len(calls) == 10, snap.error   # signed: the token POST and nine GETs


def test_the_full_fixture_gives_every_field():
    snap, _calls = _run(_full())
    assert snap.ok and snap.error is None and snap.flags == frozenset(), snap.error
    assert snap.venue == "kis" and snap.utc == "2026-10-24T00:00:00Z"
    assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0
    assert dict(snap.holdings) == {"005930": Holding(units=1.0, locked=0.0, avg_cost=60000.0),
                                   "AAPL": Holding(units=1.0, locked=0.0, avg_cost=200.0)}
    assert dict(snap.cash) == {"KRW": 20000.0, "USD": 5.0}       # KRW: the D+2 prvs_rcdl_excc_amt, not dnca_tot_amt
    assert snap.deposit_krw == 21000.0                           # dnca_tot_amt (D16 evidence)
    assert dict(snap.prices_krw) == {"005930": 61000.0, "AAPL": 210.0 * 1390.5, "USD": 1390.5}
    assert snap.open_orders == (Order(id="0000123456", symbol="005930", side="buy", units=1.0, price=60000.0),
                                Order(id="0000223456", symbol="AAPL", side="buy", units=1.0, price=200.0))
    assert snap.fills == (Move(id="20261023-0000123455", symbol="005930", counter="KRW", side="buy", units=1.0),
                          Move(id="20261023-0000223455", symbol="AAPL", counter="USD", side="buy", units=1.0))
    assert dict(snap.loans) == {"tot_loan_amt": 0.0, "loan_amt": 0.0, "crdt_fncg_amt": 0.0, "thdt_rcvb_amt": 0.0,
                                "rcvb_amt": 0.0}
    assert snap.deposits == () and snap.withdrawals == () and snap.withdrawal_addresses == ()
    assert snap.key_expiry is None and dict(snap.earn) == {}
    assert set(snap.response_sha256) == {PATH[n] for n in GETS}  # one per path, no query (it holds the account)
    assert all("?" not in k for k in snap.response_sha256)
    assert all(re.fullmatch(r"[0-9a-f]{64}", v) for v in snap.response_sha256.values())


def test_every_call_is_a_get_with_its_pinned_tr_and_the_account_from_keys():
    reads, saved = [], keys.read

    def recording(names):
        reads.append(tuple(names))
        return saved(names)
    keys.read = recording
    try:
        snap, calls = _run(EF.kis_routes(), KIS_ACCOUNT_8="97654310", KIS_ACCOUNT_PD="37")
    finally:
        keys.read = saved
    assert snap.ok, snap.error
    assert reads[0] == ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD") == kis_inquiry.ACCOUNT_NAMES      # before any request
    assert reads.count(kis_inquiry.ACCOUNT_NAMES) == 1
    assert [(c["method"], _path(c)) for c in calls] == [("POST", "/oauth2/tokenP")] + [("GET", PATH[n]) for n in GETS]
    pinned = dict(kis_inquiry.TR_IDS)
    for call in calls[1:]:
        assert call["headers"]["tr_id"] == pinned[_path(call)] and call["headers"]["tr_id"].endswith("R")
        assert _pairs(call)[:2] == [("CANO", "97654310"), ("ACNT_PRDT_CD", "37")], _pairs(call)[:2]
    balance = _pairs(_only(calls, "balance"))
    assert ("INQR_DVSN", "01") in balance and [k for k, _v in balance].count("INQR_DVSN") == 1
    ccnl = _pairs(_only(calls, "ccnl"))
    assert ("PDNO", "%25") in ccnl                               # "%" goes out as %25
    assert ("OVRS_EXCG_CD", "NASD") in ccnl and ("TR_CRCY_CD", "USD") in _pairs(_only(calls, "ovrs_balance"))


def test_the_dates_are_seoul_dates():
    for now, d0, d1, d2 in ((datetime(2026, 10, 23, 14, 59, 59, tzinfo=timezone.utc), "20261023", "20261022",
                             "20261021"),
                            (datetime(2026, 10, 23, 15, 0, 0, tzinfo=timezone.utc), "20261024", "20261023",
                             "20261022")):
        with EF.fake_keys(), EF.serve(EF.kis_routes()) as calls:
            snap = kis_inquiry.snapshot(now, F.ctx())
        assert snap.ok and snap.utc == model.iso_utc(now), snap.error
        daily, ccnl = _pairs(_only(calls, "daily_ccld")), _pairs(_only(calls, "ccnl"))
        assert ("INQR_STRT_DT", d1) in daily and ("INQR_END_DT", d0) in daily, daily
        assert ("ORD_STRT_DT", d2) in ccnl and ("ORD_END_DT", d0) in ccnl, ccnl


def test_server_time_and_offset_come_from_the_first_answer_with_a_date_header():
    no_date = json.dumps(EF.KIS_BODIES["balance"]).encode("utf-8")
    later = json.dumps(EF.KIS_BODIES["present_balance"]).encode("utf-8")
    routes = EF.kis_routes(balance=lambda call: (200, {}, no_date),
                           present_balance=lambda call: (200, {"Date": "Sat, 24 Oct 2026 00:00:45 GMT"}, later))
    with EF.fake_keys(), EF.serve(routes, date="Sat, 24 Oct 2026 00:00:30 GMT"):
        snap = kis_inquiry.snapshot(EF.NOW, F.ctx())
    # the first dated answer (+30 s), not the last one (+45 s)
    assert snap.ok and snap.server_utc == "2026-10-24T00:00:30Z" and snap.clock_offset_s == 30.0, snap


def test_response_sha256_is_per_path_over_the_raw_body():
    raw = json.dumps(EF.KIS_BODIES["present_balance"]).encode("utf-8") + b" "
    snap, _calls = _run(EF.kis_routes(present_balance=lambda call: (200, {"Date": EF.DATE_HEADER}, raw)))
    assert snap.ok and snap.response_sha256[PATH["present_balance"]] == hashlib.sha256(raw).hexdigest()


def test_quantities_sides_and_commas():
    routes = _full()
    balance = routes[EF.KIS_ROUTES["balance"]]
    balance["output1"][0] |= {"hldg_qty": "3", "ord_psbl_qty": "1"}
    balance["output1"].append(dict(balance["output1"][0], pdno="000660", hldg_qty="0", ord_psbl_qty="0"))
    balance["output2"][0]["dnca_tot_amt"] = "1,234,567"
    ovrs = routes[EF.KIS_ROUTES["ovrs_balance"]]["output1"]
    ovrs.append(dict(ovrs[0], ovrs_pdno="MSFT", ovrs_cblc_qty="0"))
    routes[EF.KIS_ROUTES["psbl_rvsecncl"]]["output"] = [dict(EF.KIS_ROWS["psbl_rvsecncl"], sll_buy_dvsn_cd="01"),
                                                        dict(EF.KIS_ROWS["psbl_rvsecncl"], odno="0000123457",
                                                             psbl_qty="0")]
    routes[EF.KIS_ROUTES["nccs"]]["output"] = [dict(EF.KIS_ROWS["nccs"], nccs_qty="", ft_ord_qty="2")]
    fills = routes[EF.KIS_ROUTES["daily_ccld"]]["output1"]
    fills[0]["ord_qty"] = "2"                                    # ordered 2, filled 1: units are the filled ones
    fills.append(dict(fills[0], odno="0000123454", tot_ccld_qty="0"))
    routes[EF.KIS_ROUTES["ccnl"]]["output"] = [dict(EF.KIS_ROWS["ccnl"], sll_buy_dvsn_cd="01"),
                                               dict(EF.KIS_ROWS["ccnl"], odno="0000223454", ft_ccld_qty="0")]
    snap, _calls = _run(routes)
    assert snap.ok, snap.error
    assert dict(snap.holdings) == {"005930": Holding(units=3.0, locked=2.0, avg_cost=60000.0),
                                   "AAPL": Holding(units=1.0, locked=0.0, avg_cost=200.0)}   # zero rows skipped
    assert snap.deposit_krw == 1234567.0                         # KIS may group digits: commas are dropped
    assert snap.open_orders == (Order(id="0000123456", symbol="005930", side="sell", units=1.0, price=60000.0),
                                Order(id="0000223456", symbol="AAPL", side="buy", units=2.0, price=200.0))
    assert snap.fills == (Move(id="20261023-0000123455", symbol="005930", counter="KRW", side="buy", units=1.0),
                          Move(id="20261023-0000223455", symbol="AAPL", counter="USD", side="sell", units=1.0))


def test_the_five_loan_figures():
    routes = EF.kis_routes()
    balance = routes[EF.KIS_ROUTES["balance"]]
    balance["output2"][0]["tot_loan_amt"] = "100"
    balance["output1"].append(dict(balance["output1"][0], pdno="000660", hldg_qty="0", loan_amt="50"))
    balance["output1"][0]["loan_amt"] = "25"
    routes[EF.KIS_ROUTES["account_balance"]]["output2"] |= {"crdt_fncg_amt": "7", "thdt_rcvb_amt": "8"}
    routes[EF.KIS_ROUTES["intgr_margin"]]["output"]["rcvb_amt"] = "9"
    snap, _calls = _run(routes)
    assert snap.ok and dict(snap.loans) == {"tot_loan_amt": 100.0, "loan_amt": 75.0, "crdt_fncg_amt": 7.0,
                                            "thdt_rcvb_amt": 8.0, "rcvb_amt": 9.0}, snap.loans


def test_a_holding_without_a_rate_has_no_price():
    routes = EF.kis_routes()
    routes[EF.KIS_ROUTES["present_balance"]]["output2"] = []
    snap, _calls = _run(routes)
    assert snap.ok and "AAPL" in snap.holdings and "AAPL" not in snap.prices_krw and "USD" not in snap.cash


def test_a_malformed_account_number_fails_before_any_request():
    for acct8, pd in (("9999999", "01"), ("999999999", "01"), ("9999999x", "01"), ("９" * 8, "01"),
                      ("99999999", "1"), ("99999999", "0a"), ("99999999", "013")):
        snap, calls = _run(EF.kis_routes(), KIS_ACCOUNT_8=acct8, KIS_ACCOUNT_PD=pd)
        assert calls == [] and not snap.ok and snap.flags == frozenset(), (acct8, pd)
        assert snap.error == ACCOUNT_ERROR, snap.error
        assert acct8 not in snap.error and pd not in snap.error, snap.error            # names only, never the value


def test_missing_keys_give_keys_missing():
    for name in ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD", "KIS_APP_KEY"):   # the app key last: its attempt starts the 70 s
        snap, calls = _run(EF.kis_routes(), **{name: None})
        assert calls == [] and not snap.ok, name
        assert snap.flags == frozenset({"keys_missing"}) and snap.error == f"keys missing: {name}", snap.error


def test_auth_answers_give_auth_error():
    for answer in ((401, {"rt_cd": "1", "msg_cd": "EGW00205", "msg1": ""}),
                   {"rt_cd": "1", "msg_cd": "EGW00103", "msg1": ""}):
        snap, calls = _run(EF.kis_routes(balance=answer))
        assert not snap.ok and snap.flags == frozenset({"auth_error"}) and snap.error, snap
        assert _path(calls[-1]) == PATH["balance"]               # it stopped at the first GET
        assert "test-token-1" not in snap.error and "test-kis-app" not in snap.error and _names_only(snap.error)


def test_a_token_code_fails_the_snapshot_and_marks_the_token_bad():
    snap, calls = _run(EF.kis_routes(balance={"rt_cd": "1", "msg_cd": "EGW00123", "msg1": ""}))
    assert not snap.ok and snap.flags == frozenset() and snap.error, snap
    assert _path(calls[-1]) == PATH["balance"]
    assert "test-token-1" in transport._bad_tokens and "test-token-1" not in snap.error and _names_only(snap.error)


def test_a_missing_or_malformed_field_fails_closed_with_its_name():
    cases = (("balance", lambda b: b["output2"][0].pop("prvs_rcdl_excc_amt"), "prvs_rcdl_excc_amt"),
             ("present_balance", lambda b: b["output2"][0].pop("crcy_cd"), "crcy_cd"),
             ("intgr_margin", lambda b: b.pop("output"), "output"),
             ("daily_ccld", lambda b: b["output1"][0].pop("ord_dt"), "ord_dt"),
             ("ovrs_balance", lambda b: b.update(output1={}), "output1"),
             ("account_balance", lambda b: b.update(output2=[]), "output2"),
             # the field each value comes from, where the fixture gives a sibling field the same value
             ("present_balance", lambda b: b["output2"][0].pop("frcr_dncl_amt_2"), "frcr_dncl_amt_2"),
             ("ovrs_balance", lambda b: b["output1"][0].pop("now_pric2"), "now_pric2"),
             ("ovrs_balance", lambda b: b["output1"][0].pop("pchs_avg_pric"), "pchs_avg_pric"),
             ("nccs", lambda b: b["output"][0].pop("nccs_qty"), "nccs_qty"),
             ("ccnl", lambda b: b["output"][0].pop("tr_crcy_cd"), "tr_crcy_cd"),
             # a live mismatch fails closed (E1R2-5): more free than held, less than none, an id that is not text
             ("balance", lambda b: b["output1"][0].update(ord_psbl_qty="2"), "ord_psbl_qty"),
             ("ovrs_balance", lambda b: b["output1"][0].update(ord_psbl_qty="-1"), "ord_psbl_qty"),
             ("balance", lambda b: b["output1"][0].update(pdno=""), "pdno"),
             ("ccnl", lambda b: b["output"][0].update(odno=223455), "odno"))
    for name, change, field in cases:
        routes = _full()
        change(routes[EF.KIS_ROUTES[name]])
        snap, _calls = _run(routes)
        assert not snap.ok and snap.flags == frozenset(), (name, field)
        assert snap.error == f"kis: {PATH[name]}: field {field}", snap.error


def test_a_malformed_number_fails_closed_without_its_value():
    for value in ("1,234,567KRW", "9,876,543KRW", "nan", "inf", 21000, None, True):
        routes = EF.kis_routes()
        routes[EF.KIS_ROUTES["balance"]]["output2"][0]["dnca_tot_amt"] = value
        snap, _calls = _run(routes)
        assert not snap.ok and snap.error == f"kis: {PATH['balance']}: field dnca_tot_amt", snap.error
        assert str(value) not in snap.error and "KRW" not in snap.error          # names only, never the value


def test_an_rt_cd_error_fails_closed():
    snap, _calls = _run(EF.kis_routes(intgr_margin={"rt_cd": "1", "msg_cd": "APBK0013", "msg1": "fixture text"}))
    assert not snap.ok and snap.flags == frozenset() and "APBK0013" in snap.error, snap.error
    assert "fixture text" not in snap.error and _names_only(snap.error)
    assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0   # the venue time read so far


def test_a_refused_send_propagates():
    with EF.fake_keys():
        try:
            kis_inquiry.snapshot(EF.NOW, F.ctx())                # no serve(): the suite's refusing stub answers
        except EF.Refused:
            pass
        else:
            raise AssertionError("a refused send became a snapshot")
    assert len(EF.STRAYS) == 1, EF.STRAYS                         # the token POST, refused
    EF.STRAYS.clear()


def test_a_refused_write_propagates():
    def refuse(path, what="path", **kw):
        raise RuntimeError(f"{what} refused (test)")
    saved = transport.checked_target
    transport.checked_target = refuse
    try:
        with EF.fake_keys(), EF.serve(EF.kis_routes()) as calls:
            kis_inquiry.snapshot(EF.NOW, F.ctx())
    except RuntimeError as exc:
        assert "refused (test)" in str(exc) and calls == [], calls   # refused before the token POST, not contained
    else:
        raise AssertionError("a refused write became a snapshot")
    finally:
        transport.checked_target = saved
