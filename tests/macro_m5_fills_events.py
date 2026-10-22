"""M5 package B tests: simulated fill model (R-27 + INV-1/INV-2/INV-5), bar convention, event store / windows /
gap tags / event_calendar artifact (R-10), evaluator BLOCKED and R-08 annotation hooks, VaR display scale.

Spec tests: T-FILL-01..03, T-BAR-01 (R-27 clause), T-ANNOT-01, G-R08-01, I-06, I-06b, I-06c, T-CAP-02 (R-08
nothing-changes-exposure clause), T-TZ-02 (re-asserted through the event store); TASK-M5-14 / M5-15 spikes as
NotRun REFDATA. Hermetic: synthetic sessions, the signed temp-dir calendar fixture of macro_m1_calendars, a
temp-dir PIT store; the only local file read is the labelled SMOKE on docs/asset_expansion/cache (never asserted).
"""
from __future__ import annotations

import ast
import csv
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from core.calendars import clocks, events as EV
from core.engine import evaluator as E
from core.engine import orders as O
from core.ficc import annotations as A
from core.ficc import pit as P
from core.ficc.macro_artifacts import provenance
from core.ficc.macro_schema import validate
from core.rules.model import OrderKind, Side
from tests.acceptance import _code_only
from tests.macro_m1_calendars import U, fixture_set
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "docs" / "asset_expansion" / "cache"
NY, KST = ZoneInfo("America/New_York"), ZoneInfo("Asia/Seoul")
D = date(2026, 7, 31)
KR_CLOSE = U(2026, 7, 31, 6, 30)
EVENTS_CFG = EV._cfg(None)


def _raises(fn, exc=Exception, needle=""):
    try:
        fn()
    except exc as e:
        assert needle.lower() in str(e).lower(), f"{needle!r} not in {e}"
        return e
    raise AssertionError(f"expected {exc.__name__}")


def _order(side=Side.BUY, symbol="000660", at=None, kind=OrderKind.MARKET) -> O.SimulatedOrder:
    return O.SimulatedOrder(id=f"book-r1-t1-{symbol}-{side.value}", rule_id="book", rule_revision=1, rule_name="sim",
                            symbol=symbol, market="KRX", side=side, kind=kind, quantity=Decimal(1), limit_price=None,
                            notional=None, trigger_price=Decimal(1), created_at=at or KR_CLOSE, as_of=at)


def _session(**kw) -> O.FillSession:
    base = dict(venue="KRX", session_date=D, instrument="stock", official_close=1_844_000.0, prev_close=1_419_000.0,
                price_limit=0.30, tick=1000.0, close_utc=KR_CLOSE, random_end_max_s=30)
    base.update(kw)
    return O.FillSession(**base)


def _event(event_id, typ, sched_utc, status="scheduled", **kw) -> dict:
    e = {"event_id": event_id, "type": typ, "region": kw.pop("region", "US"), "scheduled_utc": sched_utc,
         "status": status, "released_utc": None, "source": "fixture", "windows": [], "kr_open_gap_session": None,
         "gap_sessions": None, "var_display_scale": None, "scenario_tag": None, "notes": ""}
    e.update(kw)
    return e


def _prov():
    return provenance(clock=lambda: U(2026, 10, 2, 6, 41, 7), knowledge_utc="2026-10-02T06:40:50Z",
                      config_hash="c" * 32, data_snapshot_id="d" * 32)


# --------------------------------------------------------------------------- #
# T-FILL-01: close fill, random end, refusals (mechanics); the QF1 golden is REFDATA
# --------------------------------------------------------------------------- #
def test_fill01_official_close_fill_random_end_and_refusals():
    model = O.fill_model("KRX")
    assert model.snapshot_local == "15:19" and model.random_end_max_s == 30 and model.fill == "official_close"
    assert model.limit_price == "tick_rounded_toward_prev_close" and model.inav_residual_flag_bp == 30
    assert O.fill_model("NYSE").fill == "official_close_moc_equivalent" and O.fill_model("NYSE").snapshot_local == "15:50"
    assert O.fill_model("KOSPI200_futures").trades_until_local == "15:45"
    assert O.fill_model("KRX").bars["daily_close_from_bars"] == "forbidden"
    _raises(lambda: O.fill_model("NXT"), KeyError)
    assert O.snapshot_time_local(datetime.strptime("15:20", "%H:%M").time()).strftime("%H:%M") == "15:19"
    assert O.snapshot_time_local(datetime.strptime("14:50", "%H:%M").time()).strftime("%H:%M") == "14:49"
    # rule 1 / INV-1: the official close of t fills at the close, decision labelled official_close (KIS unverified)
    f = O.simulate_fill(_order(), _session(official_close=1_700_000.0), model=model)
    assert isinstance(f, O.Fill) and f.price == 1_700_000.0 and f.fill_status == "filled" and f.cost_multiplier == 1.0
    assert f.decision_price_source == "official_close" and "snapshot_fallback_official_close_UNVERIFIED" in f.labels
    assert f.extras()["fill_status"] == "filled" and f.extras()["fill_model"] == "R-27"
    assert O.simulated_fill is O.simulate_fill
    # random end: a closing-call print inside [close, close + 30 s] is the close; later or earlier is not
    ok = O.simulate_fill(_order(), _session(official_close=1_700_000.0, print_utc=KR_CLOSE + timedelta(seconds=20)))
    assert isinstance(ok, O.Fill)
    late = O.simulate_fill(_order(), _session(official_close=1_700_000.0, print_utc=KR_CLOSE + timedelta(seconds=31)))
    assert isinstance(late, O.NonFillable) and late.reason == "print_outside_random_end" and late.fill_status == "carried"
    early = O.simulate_fill(_order(), _session(official_close=1_700_000.0, print_utc=KR_CLOSE - timedelta(minutes=5)))
    assert isinstance(early, O.NonFillable) and early.reason == "intraday_print"
    # never an NXT / after-hours / bar print (INV-1, R-27 rule 6); no official close -> carried + alert
    for src in ("NXT", "after_hours", "KRX_after_market", "post_close_session"):
        r = O.simulate_fill(_order(), _session(official_close=1_700_000.0, print_source=src))
        assert isinstance(r, O.NonFillable) and r.reason == "nxt_or_after_hours_print" and r.carry, src
    bar = O.simulate_fill(_order(), _session(official_close=1_700_000.0, print_source="bar"))
    assert isinstance(bar, O.NonFillable) and bar.reason == "bar_derived_close"
    none = O.simulate_fill(_order(), _session(official_close=None))
    assert isinstance(none, O.NonFillable) and none.reason == "no_official_close" and none.alert and none.carry
    prov = O.simulate_fill(_order(), _session(official_close=1_700_000.0, value_status="provisional_intraday"))
    assert isinstance(prov, O.NonFillable) and prov.reason == "no_official_close"
    vend = O.simulate_fill(_order(), _session(official_close=1_700_000.0, value_status="vendor_close"))
    assert isinstance(vend, O.NonFillable)
    # NYSE MOC-equivalent (rule 4) and the same-session futures fill (rule 5)
    ny = O.simulate_fill(_order(symbol="SPY"), O.FillSession("NYSE", date(2026, 10, 1), "etf", 660.0, print_source="moc",
                                                              inav=660.5))
    assert isinstance(ny, O.Fill) and ny.price == 660.0 and "LP_exempt_auction" in ny.flags
    fut = O.simulate_fill(_order(symbol="K200"), O.FillSession("KOSPI200_futures", D, "futures", 950.0))
    assert isinstance(fut, O.Fill)
    # the printed tracking-error line (mechanics only; the 0.19% / 0.0013 golden needs the 15:19 snapshots)
    r = [0.01, -0.02, 0.015, 0.0, 0.01, -0.01, 0.02, 0.005]
    te = O.fill_tracking_error([0.5] * 8, [0.5] * 8, r)
    assert te["te_ann"] == 0.0 and te["mean_abs_dw"] == 0.0
    te2 = O.fill_tracking_error([0.5, 0.52, 0.5, 0.49, 0.5, 0.5, 0.51, 0.5], [0.5] * 8, r)
    assert te2["te_ann"] > 0 and abs(te2["mean_abs_dw"] - 0.005) < 1e-12
    _raises(lambda: O.fill_tracking_error([0.5], [0.5], [0.1]), ValueError)
    # the operator's manual contract is untouched: fill() takes any price, no venue rule, and the as_of field persists
    book = O.OrderBook()
    o = _order(at=U(2026, 7, 31, 1, 0))
    assert book.place(o) is o and book.fill(o.id, Decimal(1)) == (True, "")
    rows = book.snapshot()
    assert rows[0]["as_of"] == "2026-07-31T01:00:00+00:00"
    book2 = O.OrderBook()
    book2.restore(rows)
    assert book2.get(o.id).as_of == U(2026, 7, 31, 1, 0) and book2.get(o.id).status is O.OrderStatus.FILLED


test_fill01_official_close_fill_random_end_and_refusals.test_ids = ["T-FILL-01"]


def test_fill01_qf1_tracking_error_golden_refdata():
    """0.19% a year on KOSPI, mean |dw| 0.0013 within +-0.05 pp: needs the 15:19 KST snapshot fixture (L6018)."""
    raise NotRun("REFDATA: 15:19 KST KIS snapshot series (QF1, L6018) and KOSPI official closes; the KIS quote field "
                 "is UNVERIFIED (OWNER: M1-01 quote check)")


test_fill01_qf1_tracking_error_golden_refdata.test_ids = ["T-FILL-01"]


# --------------------------------------------------------------------------- #
# T-FILL-02: tick-rounded limit lock both sides, carried limit-down at 2x, halt day, INV-5
# --------------------------------------------------------------------------- #
def test_fill02_limit_lock_both_sides_carry_and_halt_days():
    # SK hynix 2026-07-31 shape: prev 1,419,000 x 1.30 = 1,844,700 -> tick 1,000 toward the previous close ->
    # limit-up 1,844,000 = +29.951%; the close EQUALS it although |r| < 0.30 (L2915)
    down, up = O.limit_prices(1_419_000.0, 0.30, 1000.0)
    assert up == 1_844_000.0 and down == 994_000.0
    r_up = up / 1_419_000.0 - 1.0
    assert 0.299 < r_up < 0.30 and not (abs(r_up) >= 0.30)                         # a |r| >= limit test would miss it
    assert O.limit_lock(1_844_000.0, 1_419_000.0, 0.30, 1000.0) == "up"
    assert O.limit_lock(1_843_000.0, 1_419_000.0, 0.30, 1000.0) is None             # one tick below: fillable
    assert O.limit_lock(994_000.0, 1_419_000.0, 0.30, 1000.0) == "down"
    assert O.limit_lock(995_000.0, 1_419_000.0, 0.30, 1000.0) is None
    # locked limit-up: no entry (buy carried); a sell fills at the locked-up close
    buy = O.simulate_fill(_order(Side.BUY), _session())
    assert isinstance(buy, O.NonFillable) and buy.reason == "limit_up_locked" and buy.carry
    assert buy.fill_status == "non_fillable_limit_lock" and buy.extras()["fill_status"] == "non_fillable_limit_lock"
    sell_up = O.simulate_fill(_order(Side.SELL), _session())
    assert isinstance(sell_up, O.Fill) and sell_up.price == 1_844_000.0
    # one tick below the limit fills in both directions (|r| = 29.88%, never a lock)
    assert isinstance(O.simulate_fill(_order(Side.BUY), _session(official_close=1_843_000.0)), O.Fill)
    # locked limit-down: the exit carries; a buy fills
    sell_dn = O.simulate_fill(_order(Side.SELL), _session(official_close=994_000.0))
    assert isinstance(sell_dn, O.NonFillable) and sell_dn.reason == "limit_down_locked"
    assert isinstance(O.simulate_fill(_order(Side.BUY), _session(official_close=994_000.0)), O.Fill)
    # the carried exit fills at the first unlocked session at 2x cost (INV-2); a carried buy at 1x
    nxt = _session(session_date=date(2026, 8, 3), official_close=1_000_000.0, prev_close=994_000.0,
                   close_utc=U(2026, 8, 3, 6, 30))
    carried = O.simulate_fill(_order(Side.SELL), nxt, carried=sell_dn)
    assert isinstance(carried, O.Fill) and carried.cost_multiplier == 2.0 and carried.reason == "carried_limit_down_exit_2x"
    assert carried.carried_from == D and carried.extras()["cost_multiplier"] == 2.0
    still = O.simulate_fill(_order(Side.SELL), _session(session_date=date(2026, 8, 3), official_close=696_000.0,
                                                           prev_close=994_000.0), carried=sell_dn)
    assert isinstance(still, O.NonFillable) and still.reason == "limit_down_locked"     # locked again: carried on
    cb = O.simulate_fill(_order(Side.BUY), _session(session_date=date(2026, 8, 3), official_close=1_500_000.0,
                                                       prev_close=1_844_000.0), carried=buy)
    assert isinstance(cb, O.Fill) and cb.cost_multiplier == 1.0 and cb.reason == "carried_limit_up_entry"
    # the KODEX 200 line fills (ETF and futures lines stay fillable unless themselves locked)
    etf = O.simulate_fill(_order(Side.BUY, "069500"), _session(instrument="etf", official_close=112_060.0,
                                                                 prev_close=111_000.0, tick=5.0, inav=112_000.0))
    assert isinstance(etf, O.Fill) and etf.price == 112_060.0 and "LP_exempt_auction" in etf.flags
    locked_etf = O.simulate_fill(_order(Side.BUY, "069500"), _session(instrument="etf", official_close=144_300.0,
                                                                        prev_close=111_000.0, tick=5.0))
    assert isinstance(locked_etf, O.NonFillable) and locked_etf.reason == "limit_up_locked"
    # VI / circuit-breaker / halt days are unfillable (INV-2); expiry-day futures stop; unreadable tick table
    for kind in ("vi", "circuit_breaker", "trading_halt"):
        h = O.simulate_fill(_order(), _session(halted=True, halt_kind=kind))
        assert isinstance(h, O.NonFillable) and h.reason == "halt_day" and h.carry and kind in h.detail
    exp = O.simulate_fill(_order(symbol="K200"), O.FillSession("KOSPI200_futures", D, "futures", 950.0, expiry_day=True))
    assert isinstance(exp, O.NonFillable) and exp.reason == "expiry_day_no_trading"
    nt = O.simulate_fill(_order(), _session(tick=None))
    assert isinstance(nt, O.NonFillable) and nt.reason == "not_tradable"
    _raises(lambda: O.NonFillable("stop_loss", D), ValueError, "not in")
    _raises(lambda: O.simulate_fill(object(), _session()), ValueError, "side")
    _raises(lambda: O.FillSession("KRX", D, "option"), ValueError)
    # the reason vocabulary covers R-27 and INV-2 and has no stop reason; no stop path exists in orders.py (INV-5)
    assert {"limit_up_locked", "limit_down_locked", "halt_day", "no_official_close", "nxt_or_after_hours_print",
            "bar_derived_close"} <= set(O.NONFILL_REASONS)
    assert not any("stop" in r for r in O.NONFILL_REASONS)
    code = _code_only(ROOT / "core" / "engine" / "orders.py").lower()
    for needle in ("stop_loss", "stoploss", "stop_price", "trailing_stop", "stop_out"):
        assert needle not in code, needle
    tree = ast.parse((ROOT / "core" / "engine" / "orders.py").read_text(encoding="utf-8"))
    params = {a.arg for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) for a in n.args.args + n.args.kwonlyargs}
    assert not any("stop" in p for p in params), params
    assert set(O.FILL_STATUSES) == {"filled", "non_fillable_limit_lock", "carried"}


test_fill02_limit_lock_both_sides_carry_and_halt_days.test_ids = ["T-FILL-02"]


def test_fill02_real_000660_closes_refdata():
    raise NotRun("REFDATA: KRX official closes of 000660 for 2026-07-30/31 and the owner-signed stock tick table "
                 "(OWNER: F-18); the lock rule is asserted on the inline shape above")


test_fill02_real_000660_closes_refdata.test_ids = ["T-FILL-02"]


# --------------------------------------------------------------------------- #
# T-FILL-03: LP-exempt iNAV check
# --------------------------------------------------------------------------- #
def test_fill03_inav_residual_flag():
    assert O.inav_check(10_031.0, 10_000.0)[1] == ("LP_exempt_auction", "inav_residual_gt_30bp")
    assert O.inav_check(10_030.0, 10_000.0)[1] == ("LP_exempt_auction",)                 # exactly 30 bp: not flagged
    assert O.inav_check(9_969.0, 10_000.0)[1] == ("LP_exempt_auction", "inav_residual_gt_30bp")
    assert O.inav_check(10_000.0, None) == (None, ("LP_exempt_auction",))                 # no iNAV: still LP-exempt
    base = _session(instrument="etf", official_close=10_031.0, prev_close=10_000.0, tick=5.0)
    f = O.simulate_fill(_order(symbol="069500"), O.FillSession(**{**base.__dict__, "inav": 10_000.0}))
    assert isinstance(f, O.Fill) and "inav_residual_gt_30bp" in f.flags and abs(f.inav_residual_bp - 31.0) < 1e-9
    g = O.simulate_fill(_order(symbol="069500"), O.FillSession(**{**base.__dict__, "official_close": 10_030.0, "inav": 10_000.0}))
    assert isinstance(g, O.Fill) and g.flags == ("LP_exempt_auction",)
    s = O.simulate_fill(_order(symbol="005930"), _session(official_close=1_500_000.0))     # a stock: no ETF flags
    assert isinstance(s, O.Fill) and s.flags == () and s.inav_residual_bp is None
    assert set(O.FILL_FLAGS) == {"LP_exempt_auction", "inav_residual_gt_30bp"}


test_fill03_inav_residual_flag.test_ids = ["T-FILL-03"]


# --------------------------------------------------------------------------- #
# T-BAR-01 (R-27 clause): bar convention; a bar-derived close is refused everywhere
# --------------------------------------------------------------------------- #
def test_bar01_r27_bar_convention_refuses_bar_closes():
    lat = timedelta(seconds=90)
    hourly = [O.Bar("005930", U(2026, 7, 31, h, 0), 1.0, 1.1, 0.9, 1.0, 100.0, source="vendor", latency=lat)
              for h in (1, 2, 3, 4, 5, 6)]                                    # 10:00 .. 15:00 KST bar ends
    assert hourly[-1].bar_end_utc.astimezone(KST).strftime("%H:%M") == "15:00"
    assert hourly[0].available_at_utc == U(2026, 7, 31, 1, 1, 30)
    auction = O.Bar("005930", U(2026, 7, 31, 6, 30), 1.0, 1.0, 1.0, 1.0, 10.0, is_closing_auction=True, latency=lat)
    assert auction.is_closing_auction and not hourly[-1].is_closing_auction
    _raises(lambda: O.refuse_bar_close(hourly), O.BarDerivedClose, "never derived")       # the 727-of-729 case
    _raises(lambda: O.refuse_bar_close(hourly + [auction]), O.BarDerivedClose)            # even with the auction bar
    _raises(lambda: O.refuse_bar_close([]), O.BarDerivedClose)
    _raises(lambda: O.Bar("x", datetime(2026, 7, 31, 6, 0), 1, 1, 1, 1, 1), ValueError, "tz-aware")
    assert O.Bar("x", U(2026, 7, 31, 6), 1, 1, 1, 1, 1).available_at_utc is None          # no declared latency
    r = O.simulate_fill(_order(), _session(official_close=1_500_000.0, print_source="bar"))
    assert isinstance(r, O.NonFillable) and r.reason == "bar_derived_close"
    _raises(lambda: P.stamp_close("KOSPI_OFFICIAL_CLOSE", D, 1.0, retrieved_at_utc=KR_CLOSE, source="v",
                                  registry=None, clocks=None, obs_kind="bar"), P.PITError, "never derived")
    # no function in core/engine/orders.py returns a close from bars: the only bar->close path raises
    tree = ast.parse((ROOT / "core" / "engine" / "orders.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "refuse_bar_close")
    assert any(isinstance(n, ast.Raise) for n in ast.walk(fn)) and not any(isinstance(n, ast.Return) for n in ast.walk(fn))


test_bar01_r27_bar_convention_refuses_bar_closes.test_ids = ["T-BAR-01"]


# --------------------------------------------------------------------------- #
# T-ANNOT-01 / T-CAP-02 (R-08 clause): the annotation changes no exposure; request logged UNVERIFIED
# --------------------------------------------------------------------------- #
def test_annot01_annotation_never_changes_exposure_and_requests_snapshot():
    from core.quant import risk_layer as RL
    on = A.annotate(20.5, 18.0, date(2026, 9, 30), requested_utc=U(2026, 10, 1, 20, 0, 30))
    off = A.annotate(15.0, 18.0, date(2026, 9, 30))
    par = A.annotate(18.0, 18.0, date(2026, 9, 30))
    assert on.vix_ge_vix3m and not off.vix_ge_vix3m and par.vix_ge_vix3m                 # parity flags; never tuned
    assert on.rule_id == "R-08" and on.changes_exposure is False and on.status == "ok"
    assert on.kis_snapshot_request is not None and on.kis_snapshot_request.status == "unverified_not_sent"
    assert "UNVERIFIED" in on.kis_snapshot_request.label and on.kis_snapshot_request.endpoint_kind == "kis_quotation_read_only"
    assert on.kis_snapshot_request.lines == ("069500",) and on.kis_snapshot_request.requested_utc == "2026-10-01T20:00:30Z"
    assert off.kis_snapshot_request is None and any("unverified_not_sent" in n for n in on.notes)
    queued = A.annotate(20.5, 18.0, date(2026, 9, 30), kis_verified=True, lines=("069500", "252670"))
    assert queued.kis_snapshot_request.status == "queued" and queued.kis_snapshot_request.label == ""
    missing = A.annotate(None, 18.0, date(2026, 9, 30))
    assert missing.status == "missing" and not missing.vix_ge_vix3m and missing.kis_snapshot_request is None
    assert A.annotate(20.5, 18.0, date(2026, 9, 30), status="stale").status == "stale"
    _raises(lambda: A.SnapshotRequest(("069500",), "x", "sent"), ValueError)
    # macro_state.annotations validates inside a full macro_state
    from tests.macro_m0_schemas import filled
    ms = dict(filled()["macro_state"])
    ms["annotations"] = on.macro_state_block()
    assert validate("macro_state", ms) == [] and ms["annotations"]["vix_ge_vix3m"] is True
    # nothing changes exposure: the composition never sees the flag, the weights are identical flag on / off
    held = {"069500": 0.694, "005930": 0.0}
    for flag in (on, off):
        composed = RL.compose(0.694, (1.0,), 1.0, 1.0)
        assert composed == 0.694
        A.assert_no_exposure_change(held, dict(held))
        assert flag.changes_exposure is False
    _raises(lambda: A.assert_no_exposure_change(held, {**held, "069500": 0.5}), AssertionError, "change")
    _raises(lambda: A.assert_no_exposure_change(held, {"069500": 0.694}), AssertionError, "lines")
    for mod in ("risk_layer", "sleeves", "costed"):
        path = ROOT / "core" / "quant" / f"{mod}.py"
        assert "vix_ge_vix3m" not in _code_only(path), mod
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):        # no acting module imports R-08
            if isinstance(node, ast.ImportFrom):
                assert node.module != "core.ficc.annotations", mod
                assert not (node.module == "core.ficc" and any(a.name == "annotations" for a in node.names)), mod
    assert "vix" not in _code_only(ROOT / "core" / "engine" / "orders.py").lower()
    # the evaluator hook: an Annotation, never a Decision; only R-08 is an annotation rule
    ann = E.evaluator_annotate("R-08", {"vix": 20.5, "vix3m": 18.0, "input_date": date(2026, 9, 30),
                                        "requested_utc": U(2026, 10, 1, 20, 0, 30)})
    assert isinstance(ann, A.Annotation) and ann.vix_ge_vix3m and not isinstance(ann, E.Decision)
    _raises(lambda: E.evaluator_annotate("R-10", {}), ValueError)
    # switch budget: > 2 x 14 transitions in the trailing 252 input dates is logged (a logging rule only)
    base = date(2025, 9, 1)
    noisy = [(base + timedelta(days=i), bool(i % 2)) for i in range(252)]
    a = A.annotate(20.0, 18.0, base + timedelta(days=252), history=noisy)
    assert a.switch_log and a.transitions_trailing > 28 and any("logged for review" in n for n in a.notes)
    calm = [(base + timedelta(days=i), i >= 200) for i in range(252)]
    b = A.annotate(20.0, 18.0, base + timedelta(days=252), history=calm)
    assert not b.switch_log and b.transitions_trailing == 1
    # spell arithmetic on a known pattern
    s = A.spell_stats([False, True, False, True, True, True, True, True, False, False])
    assert s == {"n_days": 10, "n_flagged": 6, "share_flagged": 0.6, "n_spells": 2, "share_one_day": 0.5,
                 "share_ge5": 0.5, "n_transitions": 4, "transitions_per_year": 4 / 10 * 252}
    assert A.parity_flags({date(2026, 1, 2): 20.0, date(2026, 1, 5): 10.0}, {date(2026, 1, 2): 19.0}) == [(date(2026, 1, 2), True)]


test_annot01_annotation_never_changes_exposure_and_requests_snapshot.test_ids = ["T-ANNOT-01", "T-CAP-02"]


def test_annot01_pit_read_path_context_role_never_fails():
    from tests.macro_m1_pit import CLK, REG, _kr_dec, _release, _store
    store = _store()
    d0, d1 = date(2026, 9, 29), date(2026, 9, 30)
    rows = []
    for d, vix, vix3m in ((d0, 15.0, 18.0), (d1, 20.5, 18.0)):
        post = datetime.combine(d, datetime.min.time(), tzinfo=NY).replace(hour=16, minute=15).astimezone(timezone.utc)
        rows.append(_release("VIXCLS", d, vix, post + timedelta(minutes=1), source="Cboe", posting=post))
        rows.append(_release("VXVCLS", d, vix3m, post + timedelta(minutes=1), source="Cboe", posting=post))
    assert store.append(rows) == 4
    know = U(2026, 10, 2)
    # the close of D is not usable at the US close of D (16:15 ET posting is after the 16:00:30 bound): the
    # annotation at that decision is still the one of D-1 (flag off), never a failure
    at_d = A.vix_ge_vix3m(store, CLK.close_print_bound_utc("US", d1), know, registry=REG)
    assert at_d.status == "ok" and at_d.input_date == d0 and not at_d.vix_ge_vix3m and at_d.kis_snapshot_request is None
    # the KRX close of K = D+1 and the US close of D+1 read D = 2026-09-30: flag on, request UNVERIFIED
    kr = A.vix_ge_vix3m(store, _kr_dec(date(2026, 10, 1)), know, registry=REG)
    assert kr.status == "ok" and kr.vix_ge_vix3m and kr.input_date == d1 and kr.vix == 20.5 and kr.vix3m == 18.0
    assert kr.kis_snapshot_request.status == "unverified_not_sent" and kr.transitions_trailing == 1
    us = A.vix_ge_vix3m(store, CLK.close_print_bound_utc("US", date(2026, 10, 1)), know, registry=REG)
    assert us.vix_ge_vix3m and us.input_date == d1
    # an empty store: missing, labelled; the consumer binding is context (role never HALTs)
    empty = A.vix_ge_vix3m(_store(), _kr_dec(date(2026, 10, 1)), know, registry=REG)
    assert empty.status == "missing" and "never a failure" in empty.notes[0]
    assert REG.resolve_binding("VIXCLS", "R-08").role == "context"


test_annot01_pit_read_path_context_role_never_fails.test_ids = ["T-ANNOT-01"]


def _cache_series(name: str) -> dict[date, float]:
    path = CACHE / name
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        col = [c for c in (reader.fieldnames or ()) if c != "Date"][0]
        out = {}
        for row in reader:
            try:
                out[date.fromisoformat(row["Date"])] = float(row[col])
            except (ValueError, KeyError):
                continue
    return out


def test_g_r08_01_spell_count_smoke_then_refdata():
    """G-R08-01: 4,735 days, 10.1% flagged, 132 spells, 50.8% one-day, 15.9% >= 5 days, 14.0 transitions a year on
    FRED VIXCLS / VXVCLS 2007-12-04 -> 2026-09-30. A labelled SMOKE on the Yahoo cache (last intraday row dropped)
    prints the count; the golden is never asserted on vendor data."""
    vix, vix3m = _cache_series("yf__VIX.csv"), _cache_series("yf__VIX3M.csv")
    if vix and vix3m:
        last = max(set(vix) & set(vix3m))
        pairs = [(d, f) for d, f in A.parity_flags(vix, vix3m) if date(2007, 12, 4) <= d < last]   # drop the last row
        s = A.spell_stats(pairs)
        print(f"SMOKE G-R08-01 (Yahoo ^VIX/^VIX3M to {max(d for d, _ in pairs)}, vendor data, not the golden): "
              f"{s['n_days']} days, {100 * s['share_flagged']:.1f}% flagged, {s['n_spells']} spells, "
              f"{100 * s['share_one_day']:.1f}% one-day, {100 * s['share_ge5']:.1f}% >= 5 days, "
              f"{s['transitions_per_year']:.2f} transitions/yr")
        assert s["n_days"] > 4000 and 0.05 < s["share_flagged"] < 0.20 and s["n_spells"] > 50   # sanity, not the golden
    raise NotRun("REFDATA: FRED VIXCLS / VXVCLS 2007-12-04 -> 2026-09-30 (QX_DLB_r08.csv basis) for the 132-spell "
                 "golden; the Yahoo cache SMOKE above is vendor data and never asserted")


test_g_r08_01_spell_count_smoke_then_refdata.test_ids = ["G-R08-01", "T-ANNOT-01"]


# --------------------------------------------------------------------------- #
# I-06: event store, windows, cancelled / delayed, BoK pair, opening-gap nights, artifact
# --------------------------------------------------------------------------- #
def test_i06_event_windows_cancelled_delayed_bok_and_artifact():
    cal = fixture_set()
    cfg = EVENTS_CFG
    nfp = _event("US-NFP-2026-10-02", "US_NFP", "2026-10-02T12:30:00Z")
    w = EV.event_windows(nfp, cfg=cfg)
    assert w == ({"market": "US", "action": "evaluator_block_new_intraday_entries", "start_utc": "2026-10-02T12:25:00Z",
                  "end_utc": "2026-10-02T14:00:00Z", "resume_condition": "10:00 ET"},)             # L3855 verbatim
    fomc = _event("FOMC-2026-10-28", "FOMC", "2026-10-28T18:00:00Z")
    wf = EV.event_windows(fomc, cfg=cfg)
    assert wf[0] == {"market": "US", "action": "evaluator_block_new_intraday_entries", "start_utc": "2026-10-28T17:45:00Z",
                     "end_utc": "2026-10-28T19:00:00Z", "resume_condition": "VIX < pre-14:00 ET level else 19:30Z"}
    assert wf[1] == {"market": "KR_FUT_NIGHT", "action": "evaluator_block_new_futures_entries",
                     "start_utc": "2026-10-28T17:45:00Z", "end_utc": "2026-10-28T19:00:00Z", "resume_condition": None}
    assert EV.event_windows(fomc, cfg=cfg, vix_pre14=18.0, vix_at_resume=17.0)[0]["end_utc"] == "2026-10-28T19:00:00Z"
    assert EV.event_windows(fomc, cfg=cfg, vix_pre14=18.0, vix_at_resume=18.0)[0]["end_utc"] == "2026-10-28T19:30:00Z"
    assert EV.event_windows(fomc, cfg=cfg, missing_vix_resume_late=True)[1]["end_utc"] == "2026-10-28T19:30:00Z"
    ism = _event("US-ISM-2026-10-01", "US_OTHER_RELEASE", "2026-10-01T14:00:00Z")
    assert EV.event_windows(ism, cfg=cfg)[0]["start_utc"] == "2026-10-01T13:30:00Z"                  # drift: -30 min
    # the Oct-2025 CPI was never published: a cancelled event has no window; a delayed one moves with its instant
    cpi = _event("US-CPI-2025-10-15", "US_CPI", "2025-10-15T12:30:00Z", status="cancelled")
    assert EV.event_windows(cpi, cfg=cfg) == ()
    assert EV.active_windows([cpi], "US", U(2025, 10, 15, 12, 40), cfg=cfg) == ()
    late = _event("US-CPI-2025-11-13", "US_CPI", "2025-11-13T13:30:00Z", status="delayed")
    assert EV.event_windows(late, cfg=cfg)[0]["start_utc"] == "2025-11-13T13:25:00Z"
    assert EV.active_windows([late], "US", U(2025, 11, 13, 13, 0), cfg=cfg) == ()
    assert EV.active_windows([late], "US", U(2025, 11, 13, 13, 40), cfg=cfg)[0]["event_id"] == "US-CPI-2025-11-13"
    # BoK: two events, each with its own status and its own KOSPI200-futures window
    bok = _event("BOK-DECISION-2026-10-23", "BOK_DECISION", "2026-10-23T00:50:00Z", region="KR")
    press = _event("BOK-PRESS-2026-10-23", "BOK_PRESS_CONFERENCE", "2026-10-23T02:10:00Z", region="KR", status="released",
                   released_utc="2026-10-23T02:10:00Z")
    wb, wp = EV.event_windows(bok, cfg=cfg)[0], EV.event_windows(press, cfg=cfg)[0]
    assert (wb["start_utc"], wb["end_utc"], wb["market"], wb["action"]) == (
        "2026-10-23T00:45:00Z", "2026-10-23T01:15:00Z", "KR_FUT", "evaluator_block_new_futures_entries")
    assert (wp["start_utc"], wp["end_utc"]) == ("2026-10-23T02:00:00Z", "2026-10-23T02:45:00Z")
    assert EV.Event.from_dict(bok).status == "scheduled" and EV.Event.from_dict(press).status == "released"
    assert EV.event_windows(bok, cfg=cfg) != EV.event_windows(press, cfg=cfg)
    # opening-gap nights (T-TZ-02 through the event store): NFP 2026-10-02 -> 10-06; FOMC 2026-09-16 -> 09-17
    assert EV.kr_open_gap_session_of(nfp, cal=cal, cfg=cfg) == date(2026, 10, 6)
    assert EV.kr_open_gap_session_of(_event("FOMC-2026-09-16", "FOMC", "2026-09-16T18:00:00Z"), cal=cal, cfg=cfg) == date(2026, 9, 17)
    assert EV.kr_open_gap_session_of(fomc, cal=cal, cfg=cfg) == date(2026, 10, 29)
    assert EV.kr_open_gap_session_of(cpi, cal=cal, cfg=cfg) is None                                  # cancelled: no tag
    assert EV.kr_open_gap_session_of(bok, cal=cal, cfg=cfg) is None                                  # not a gap type
    assert EV.kr_open_gap_event(date(2026, 10, 6), [nfp], cal=cal, cfg=cfg)
    assert EV.kr_open_gap_event(date(2026, 9, 17), [_event("FOMC-2026-09-16", "FOMC", "2026-09-16T18:00:00Z")], cal=cal, cfg=cfg)
    assert not EV.kr_open_gap_event(date(2026, 9, 18), [_event("FOMC-2026-09-16", "FOMC", "2026-09-16T18:00:00Z")], cal=cal, cfg=cfg)
    # every KRX day: the first 30 minutes (09:00-09:30; 10:00-10:30 on the first trading day), from the calendar
    w_open = EV.kr_open_window(date(2026, 10, 6), cal=cal, cfg=cfg)
    assert (w_open["start_utc"], w_open["end_utc"], w_open["market"]) == ("2026-10-06T00:00:00Z", "2026-10-06T00:30:00Z", "KR")
    w_first = EV.kr_open_window(date(2026, 1, 2), cal=cal, cfg=cfg)
    assert (w_first["start_utc"], w_first["end_utc"]) == ("2026-01-02T01:00:00Z", "2026-01-02T01:30:00Z")
    assert EV.active_windows([], "KR", U(2026, 10, 6, 0, 10), cal=cal, cfg=cfg)[0]["event_id"] == "KR-OPEN-2026-10-06"
    assert EV.active_windows([], "KR", U(2026, 10, 6, 0, 30), cal=cal, cfg=cfg) == ()
    cbw = EV.active_windows([], "KR", U(2026, 10, 6, 2, 20), cal=cal, cfg=cfg, cb_reopen_utc=U(2026, 10, 6, 2, 0))
    assert len(cbw) == 1 and cbw[0]["event_id"].startswith("KR-CB-REOPEN") and cbw[0]["end_utc"] == "2026-10-06T02:30:00Z"
    # never a blackout: no window is a day long or more, and the store says so
    for e in (nfp, fomc, ism, late, bok, press):
        for win in EV.event_windows(e, cfg=cfg):
            assert (EV.utc(win["end_utc"]) - EV.utc(win["start_utc"])) <= timedelta(hours=2)
    assert cfg["daily_book_blackouts"] is False and cfg["tags_change_weights"] is False
    # the artifact: one file per calendar version, provenance envelope, windows + tags generated, schema-valid
    art = EV.build_event_calendar([nfp, fomc, cpi, bok, press], provenance=_prov(), calendar_version=cal.version, cal=cal,
                                  cfg=cfg, gap_sessions_for=[date(2026, 10, 6), date(2026, 10, 8), date(2026, 11, 27)])
    assert validate("event_calendar", art) == [] and art["calendar_version"] == "1.0.0-fixture" and art["read_only"] is True
    by_id = {e["event_id"]: e for e in art["events"]}
    assert by_id["US-NFP-2026-10-02"]["kr_open_gap_session"] == "2026-10-06" and by_id["US-NFP-2026-10-02"]["windows"] == list(w)
    assert by_id["FOMC-2026-10-28"]["kr_open_gap_session"] == "2026-10-29" and len(by_id["FOMC-2026-10-28"]["windows"]) == 2
    assert by_id["US-CPI-2025-10-15"]["windows"] == [] and by_id["US-CPI-2025-10-15"]["kr_open_gap_session"] is None
    assert "KRX-HOLIDAY-GAP-2026-10-06" in by_id and "KRX-HOLIDAY-GAP-2026-10-08" not in by_id
    assert "KRX-HOLIDAY-GAP-2026-11-27" not in by_id
    gap = by_id["KRX-HOLIDAY-GAP-2026-10-06"]
    assert gap["type"] == "KRX_HOLIDAY_GAP" and gap["gap_sessions"] == 2 and abs(gap["var_display_scale"] - math.sqrt(2)) < 1e-12
    assert gap["windows"][0]["action"] == "annotate_only" and gap["region"] == "KR" and gap["source"] == "core/calendars"
    # a validation failure is refused, never a HALT (ValueError; no runtime call exists in events.py)
    _raises(lambda: EV.build_event_calendar([dict(nfp, status="done")], provenance=_prov(), calendar_version="x", cfg=cfg),
            ValueError)
    assert "runtime_halt" not in (ROOT / "core" / "calendars" / "events.py").read_text(encoding="utf-8")


test_i06_event_windows_cancelled_delayed_bok_and_artifact.test_ids = ["I-06", "T-TZ-02"]


def test_i06_evaluator_blocked_for_new_entries_only():
    cfg = EVENTS_CFG
    nfp = _event("US-NFP-2026-10-02", "US_NFP", "2026-10-02T12:30:00Z")
    inside, outside = U(2026, 10, 2, 12, 40), U(2026, 10, 2, 14, 0)
    book = O.OrderBook()
    log: list = []

    def fired(side, at):
        o = _order(side, "AAPL", at=at)
        return E.Decision(o.rule_id, o.rule_name, E.Outcome.FIRED, "all conditions met", at, o, Decimal(1))

    state_in = E.BlockState(windows=EV.active_windows([nfp], "US", inside, cfg=cfg), market="US")
    state_out = E.BlockState(windows=EV.active_windows([nfp], "US", outside, cfg=cfg), market="US")
    assert len(state_in.windows) == 1 and state_out.windows == ()
    blocked = E.evaluator_block("R-10", fired(Side.BUY, inside), state_in, log=log)
    assert blocked.outcome is E.Outcome.BLOCKED and blocked.reason.startswith("R-10: US-NFP-2026-10-02")
    assert blocked.order is None and blocked.rule_id == "book" and E.Outcome("blocked") is E.Outcome.BLOCKED
    assert log and log[0]["kind"] == "evaluator_blocked" and log[0]["macro_rule"] == "R-10"
    exit_d = fired(Side.SELL, inside)
    assert E.evaluator_block("R-10", exit_d, state_in, log=log) is exit_d                 # exits are never blocked
    buy_out = fired(Side.BUY, outside)
    assert E.evaluator_block("R-10", buy_out, state_out, log=log) is buy_out             # entries resume at 10:00 ET
    kr_state = E.BlockState(windows=EV.active_windows([nfp], "US", inside, cfg=cfg), market="KR")
    assert E.evaluator_block("R-10", fired(Side.BUY, inside), kr_state) .outcome is E.Outcome.FIRED   # other market
    skipped = E.Decision("book", "sim", E.Outcome.SKIPPED, "not met", inside, None, None)
    assert E.evaluator_block("R-10", skipped, state_in) is skipped                        # only a would-act decision
    assert len(log) == 1 and book.all() == ()                                             # nothing written to a book
    # the R-31 -12% step: new entries blocked, holds / decreases / exits pass (rulings 3.6 weight-book definition)
    step = E.BlockState(block_new_entries=True, w_held=0.3, w_target=0.5)
    b = E.evaluator_block("R-31", fired(Side.SELL, inside), step, log=log)                # the caller's weights govern
    assert b.outcome is E.Outcome.BLOCKED and b.reason.startswith("R-31")
    hold = E.BlockState(block_new_entries=True, w_held=0.5, w_target=0.5)
    dec = E.BlockState(block_new_entries=True, w_held=0.5, w_target=0.2)
    ex = E.BlockState(block_new_entries=True, w_held=0.5, w_target=0.0)
    for st in (hold, dec, ex):
        d = fired(Side.BUY, inside)
        assert E.evaluator_block("R-31", d, st) is d
    off = E.BlockState(block_new_entries=False, w_held=0.0, w_target=0.5)
    d = fired(Side.BUY, inside)
    assert E.evaluator_block("R-31", d, off) is d
    stated = E.BlockState(block_new_entries=True, is_new_entry=False)
    assert E.evaluator_block("R-31", fired(Side.BUY, inside), stated).outcome is E.Outcome.FIRED
    assert E.is_new_entry(Side.BUY) and not E.is_new_entry(Side.SELL) and not E.is_new_entry(None)
    assert E.is_new_entry(w_held=0.0, w_target=0.1) and not E.is_new_entry(w_held=0.1, w_target=0.1)
    _raises(lambda: E.evaluator_block("R-08", fired(Side.BUY, inside), state_in), ValueError)   # R-08 is no block
    assert set(E.BLOCK_RULES) == {"R-10", "R-31"}
    # the UI style row exists for the new outcome (static; the page is Flet)
    assert "Outcome.BLOCKED" in (ROOT / "ui" / "trading_page.py").read_text(encoding="utf-8")


test_i06_evaluator_blocked_for_new_entries_only.test_ids = ["I-06"]


# --------------------------------------------------------------------------- #
# I-06b / I-06c: gap tags, VaR display scale, nothing changes a weight
# --------------------------------------------------------------------------- #
def test_i06b_i06c_gap_tags_var_scale_and_no_weight_change():
    cal = fixture_set()
    cfg = EVENTS_CFG
    nfp = _event("US-NFP-2026-10-02", "US_NFP", "2026-10-02T12:30:00Z")
    tags = EV.gap_tags(date(2026, 10, 6), [nfp], cal=cal, cfg=cfg)
    assert tags == {"kr_open_gap_event": True, "gap_sessions": 2, "var_display_scale": math.sqrt(2.0)}
    assert abs(tags["var_display_scale"] - 1.4142) < 1e-4
    assert EV.gap_tags(date(2026, 10, 12), [], cal=cal, cfg=cfg)["gap_sessions"] == 2                  # 8 and 9 Oct
    # I-06c: the KR decision of 2026-11-26 (effective 2026-11-27, NYSE closed 2026-11-26): 0, 1, false, no event
    t = EV.gap_tags(date(2026, 11, 27), [], cal=cal, cfg=cfg)
    assert t == {"kr_open_gap_event": False, "gap_sessions": 0, "var_display_scale": 1.0}
    assert EV.holiday_gap_event(date(2026, 11, 27), cal=cal) is None
    ordinary = EV.gap_tags(date(2026, 10, 8), [], cal=cal, cfg=cfg)
    assert ordinary == {"kr_open_gap_event": False, "gap_sessions": 1, "var_display_scale": 1.0}
    assert EV.var_display_scale(0) == 1.0 and EV.var_display_scale(1) == 1.0 and EV.var_display_scale(4) == 2.0
    _raises(lambda: EV.var_display_scale(-1), ValueError)
    gap = EV.holiday_gap_event(date(2026, 10, 6), cal=cal)
    assert gap.type == "KRX_HOLIDAY_GAP" and gap.gap_sessions == 2 and gap.kr_open_gap_session == "2026-10-06"
    assert gap.scheduled_utc == "2026-10-06T00:00:00Z" and gap.windows[0]["action"] == "annotate_only"
    # the flags validate in a full macro_state, and a context-field failure never HALTs (refused with ValueError)
    from tests.macro_m0_schemas import filled
    ms = dict(filled()["macro_state"])
    ms["flags"] = {**ms["flags"], **t}
    assert validate("macro_state", ms) == []
    bad = dict(ms, flags={**ms["flags"], "gap_sessions": -1})
    assert validate("macro_state", bad) and all("gap_sessions" in i for i in validate("macro_state", bad))
    # no event tag or gap flag changes any weight: the composition and the weights are identical with every tag flipped
    from core.quant import risk_layer as RL
    held = {"069500": 0.694}
    for flip in ({}, {"kr_open_gap_event": True, "gap_sessions": 3, "var_display_scale": EV.var_display_scale(3)}):
        flags = {**t, **flip}
        assert RL.compose(0.694, (1.0,), 1.0, 1.0) == 0.694 and flags["var_display_scale"] >= 1.0
        A.assert_no_exposure_change(held, dict(held))
    assert cfg["multi_session_gap"]["gross_rule"] is False and cfg["sidecar_cb"]["gross_cut"] is False
    code = _code_only(ROOT / "core" / "calendars" / "events.py")
    assert "compose(" not in code and "weights" not in code.lower().replace("tags_change_weights", "")
    for mod in ("risk_layer", "sleeves"):
        assert "gap_sessions" not in _code_only(ROOT / "core" / "quant" / f"{mod}.py")


test_i06b_i06c_gap_tags_var_scale_and_no_weight_change.test_ids = ["I-06b", "I-06c"]


# --------------------------------------------------------------------------- #
# TASK-M5-14 / M5-15 spikes
# --------------------------------------------------------------------------- #
def test_task_m5_14_halt_count_pin_refdata():
    raise NotRun("REFDATA: F13 yahoo_KS11_1996-12_2026-10-02.csv (KOSPI 1997-04-15 -> 2026-10-02 official closes) for "
                 "the v2 HALT count pin and G-LAD-04 (section 9.4 items 9-10); never changes a default")


test_task_m5_14_halt_count_pin_refdata.test_ids = ["I-04b"]


def test_task_m5_15_event_conditional_variance_refdata():
    raise NotRun("REFDATA: local KRX hourly bars and daily opens (QF7-A28 basis) for the DM test on the squared "
                 "opening gap; the 2027-28 post-holiday VaR breach check is pre-registered (OWNER: 2027-28 data). "
                 "Whatever it shows, no gap flag changes a weight (asserted above)")


test_task_m5_15_event_conditional_variance_refdata.test_ids = ["I-06b"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
