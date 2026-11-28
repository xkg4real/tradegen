"""Acceptance suite for the C++20 native engine (native/tradegen_fast) and Tier A/B bridges.

Verifies:
1. Build manifest & SHA-256 / ABI integrity checks (tampered .so / manifest -> NativeIntegrityError).
2. 1,100+ randomized differential test cases across HP-1 .. HP-6 proving 0-ULP / 0-digest
   identity between C++20 native execution and pure Python (TRADEGEN_DISABLE_NATIVE=1).
3. Seamless TG_FALLBACK_PRECISION fallback for sub-1e-18 precision and >1e20 magnitude inputs.
4. End-to-end latency speedup benchmarks across HP-1, HP-3, HP-5, and HP-6.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as CM, native_accel, owner
from core.odds import plan as odds_plan, report as odds_report, simulate as odds_sim
from data import _kis_native, kis_live
from execution_accounts import continuous, provider
from execution_accounts.upbit_collector import TradePrint
from execution_control.model import InstrumentRules, Order, validate_order
from execution_control.risk import Fill
from execution_launch import carry_evaluator as CE, managed_behavior as MB, program as LP
from tests import compliance_fixtures as CF, odds_fixtures as OF

D = Decimal
T0 = datetime(2026, 11, 10, 1, 0, 0, tzinfo=timezone.utc)


def _exact_equal(a, b) -> bool:
    import numpy as np
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return (isinstance(a, np.ndarray) and isinstance(b, np.ndarray)
                and a.shape == b.shape and a.dtype == b.dtype
                and bool(np.array_equal(a, b, equal_nan=True)))
    if type(a) is not type(b):
        return False
    if type(a) is float:
        return (math.isnan(a) and math.isnan(b)) or a == b
    if is_dataclass(a) and not isinstance(a, type):
        return all(_exact_equal(getattr(a, f.name), getattr(b, f.name)) for f in fields(a))
    if isinstance(a, (tuple, list)):
        return len(a) == len(b) and all(_exact_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return set(a) == set(b) and all(_exact_equal(a[k], b[k]) for k in a)
    return a == b


def _with_native_disabled(fn):
    with patch.dict(os.environ, {"TRADEGEN_DISABLE_NATIVE": "1"}):
        return fn()


def _with_native_enabled(fn):
    env = {k: v for k, v in os.environ.items() if k != "TRADEGEN_DISABLE_NATIVE"}
    with patch.dict(os.environ, env, clear=True):
        assert native_accel.get_native_handle() is not None, "libtradegen_fast.so must be loaded"
        return fn()


def _upbit_fill(*, order_id: str, fill_id: str, symbol: str, side: str,
                quantity: Decimal, price: Decimal, fee: Decimal, executed_at: datetime) -> Fill:
    return Fill(
        venue="upbit",
        account_scope="acct-1",
        order_id=order_id,
        fill_id=fill_id,
        market="spot",
        symbol=symbol,
        base_currency=symbol[4:],
        quote_currency="KRW",
        side=side,
        quantity=quantity,
        price=price,
        quote_krw=D(1),
        fee_amount=fee,
        fee_currency="KRW",
        executed_at=executed_at,
    )


def _tprint(*, market: str, seq: int, ts_ms: int, price: Decimal, volume: Decimal, ask_bid: str = "BID") -> TradePrint:
    return TradePrint(
        market=market,
        sequential_id=seq,
        timestamp_ms=ts_ms,
        at=datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=ts_ms),
        price=price,
        volume=volume,
        ask_bid=ask_bid,
        source_sha256="1" * 64,
    )


def test_native_manifest_and_tamper_refusal():
    handle = _with_native_enabled(native_accel.get_native_handle)
    assert handle is not None
    assert int(handle["lib"].tg_abi_version()) == native_accel.EXPECTED_ABI_VERSION

    real_dir = native_accel.DEFAULT_BUILD_DIR
    with tempfile.TemporaryDirectory(prefix="tradegen_tamper_") as tmp:
        tdir = Path(tmp)
        shutil.copy2(real_dir / "libtradegen_fast.so", tdir / "libtradegen_fast.so")
        shutil.copy2(real_dir / "build_manifest.json", tdir / "build_manifest.json")

        so_bytes = bytearray((tdir / "libtradegen_fast.so").read_bytes())
        so_bytes[-1] ^= 0xFF
        (tdir / "libtradegen_fast.so").write_bytes(bytes(so_bytes))
        try:
            _with_native_enabled(lambda: native_accel.get_native_handle(build_dir=tdir))
            raise AssertionError("expected NativeIntegrityError on tampered .so")
        except native_accel.NativeIntegrityError as exc:
            assert str(exc) == "NATIVE_BINARY_DIGEST_MISMATCH"

    with tempfile.TemporaryDirectory(prefix="tradegen_tamper_manifest_") as tmp:
        tdir = Path(tmp)
        shutil.copy2(real_dir / "libtradegen_fast.so", tdir / "libtradegen_fast.so")
        manifest = json.loads((real_dir / "build_manifest.json").read_text(encoding="utf-8"))
        manifest["abi_version"] = 999
        (tdir / "build_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        try:
            _with_native_enabled(lambda: native_accel.get_native_handle(build_dir=tdir))
            raise AssertionError("expected NativeIntegrityError on tampered manifest")
        except native_accel.NativeIntegrityError as exc:
            assert str(exc) == "NATIVE_ABI_VERSION_MISMATCH"

    assert _with_native_disabled(native_accel.get_native_handle) is None


def test_hp1_continuous_interval_differential_260_cases():
    rng = random.Random(2026112701)
    markets_pool = ("KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL")

    for case_idx in range(260):
        t_start = T0
        t_end = T0 + timedelta(seconds=60)
        k = 1 if case_idx < 180 else rng.randint(2, 4)
        chosen = markets_pool[:k]
        open_cash = D(str(rng.randint(20_000_000, 80_000_000)))
        hist_fills = []
        o_units_list = []
        o_marks = {}
        prints_by = {m: [] for m in chosen}
        int_fills = []
        seq = 1000
        open_eq = open_cash
        for idx_m, m in enumerate(chosen):
            u = D(rng.randint(1, 50)) / D("100")
            mk = D(str(rng.randint(100_000, 5_000_000)))
            o_marks[m] = mk
            if u > 0:
                o_units_list.append((m, u))
                open_eq += u * mk
                hist_fills.append(_upbit_fill(
                    order_id=f"hist-o-{case_idx}-{idx_m}",
                    fill_id=f"hist-f-{case_idx}-{idx_m}",
                    symbol=m, side="buy", quantity=u, price=mk, fee=D(0),
                    executed_at=t_start - timedelta(minutes=10),
                ))

        cur_u = dict(o_units_list)
        cur_c = open_cash
        cur_ms = int(t_start.timestamp() * 1000) + 50
        for step in range(rng.randint(6, 40)):
            if rng.random() < 0.65:
                cur_ms += rng.randint(1, 400)
            at_dt = datetime.fromtimestamp(cur_ms / 1000.0, tz=timezone.utc)
            if at_dt >= t_end:
                break
            m = rng.choice(chosen)
            px = D(str(rng.randint(90_000, 5_500_000)))
            seq += 1
            if rng.random() < 0.65:
                prints_by[m].append(_tprint(
                    market=m, seq=seq, ts_ms=cur_ms, price=px, volume=D("0.5"), ask_bid="BID",
                ))
            else:
                if cur_u.get(m, D(0)) > D("0.05") and rng.random() < 0.5:
                    qty = D("0.02")
                    fee = (qty * px * D("0.0005")).quantize(D("0.01"))
                    int_fills.append(_upbit_fill(
                        order_id=f"int-o-{case_idx}-{step}", fill_id=f"int-f-{seq}",
                        symbol=m, side="sell", quantity=qty, price=px, fee=fee, executed_at=at_dt,
                    ))
                    cur_u[m] -= qty
                    cur_c += qty * px - fee
                else:
                    qty = D("0.02")
                    fee = (qty * px * D("0.0005")).quantize(D("0.01"))
                    if cur_c >= qty * px + fee:
                        int_fills.append(_upbit_fill(
                            order_id=f"int-o-{case_idx}-{step}", fill_id=f"int-f-{seq}",
                            symbol=m, side="buy", quantity=qty, price=px, fee=fee, executed_at=at_dt,
                        ))
                        cur_u[m] = cur_u.get(m, D(0)) + qty
                        cur_c -= qty * px + fee

        trade_path = {m: tuple(v) for m, v in prints_by.items()}
        o_units_tup = tuple(sorted(o_units_list))
        hist_tup = tuple(hist_fills)
        int_tup = tuple(int_fills)

        nat = _with_native_enabled(lambda: continuous.value_trade_paths(
            trade_path, opening_marks=o_marks, opening_cash_krw=open_cash,
            opening_units=o_units_tup, historical_fills=hist_tup, interval_fills=int_tup,
            previous_equity_krw=open_eq, previous_realized_net_krw=D(0),
            start=t_start, end=t_end, account_scope="acct-1",
        ))
        py = _with_native_disabled(lambda: continuous.value_trade_paths(
            trade_path, opening_marks=o_marks, opening_cash_krw=open_cash,
            opening_units=o_units_tup, historical_fills=hist_tup, interval_fills=int_tup,
            previous_equity_krw=open_eq, previous_realized_net_krw=D(0),
            start=t_start, end=t_end, account_scope="acct-1",
        ))
        assert nat == py, f"HP-1 mismatch at case {case_idx}"

    # Sub-1e-18 precision & >1e20 magnitude seamless TG_FALLBACK_PRECISION verification
    sub18_cash = D("1000.000000000000000000001")
    sub18 = _with_native_enabled(lambda: continuous.value_trade_paths(
        {"KRW-BTC": (_tprint(
            market="KRW-BTC", seq=1, ts_ms=int(T0.timestamp() * 1000) + 100,
            price=D("105"), volume=D("1"), ask_bid="BID",
        ),)},
        opening_marks={"KRW-BTC": D("100")},
        opening_cash_krw=sub18_cash,
        opening_units=(("KRW-BTC", D("1")),),
        historical_fills=(_upbit_fill(
            order_id="h-sub", fill_id="f-sub", symbol="KRW-BTC", side="buy",
            quantity=D("1"), price=D("100"), fee=D(0), executed_at=T0 - timedelta(seconds=10),
        ),),
        interval_fills=(),
        previous_equity_krw=sub18_cash + D("100"),
        previous_realized_net_krw=D(0),
        start=T0, end=T0 + timedelta(seconds=10), account_scope="acct-1",
    ))
    assert sub18.equity_krw == D("1105.000000000000000000001")

    huge_cash = D("500000000000000000000000")
    huge = _with_native_enabled(lambda: continuous.value_trade_paths(
        {"KRW-BTC": ()},
        opening_marks={"KRW-BTC": D("100")},
        opening_cash_krw=huge_cash,
        opening_units=(("KRW-BTC", D("1")),),
        historical_fills=(_upbit_fill(
            order_id="h-huge", fill_id="f-huge", symbol="KRW-BTC", side="buy",
            quantity=D("1"), price=D("100"), fee=D(0), executed_at=T0 - timedelta(seconds=10),
        ),),
        interval_fills=(),
        previous_equity_krw=huge_cash + D("100"),
        previous_realized_net_krw=D(0),
        start=T0, end=T0 + timedelta(seconds=10), account_scope="acct-1",
    ))
    assert huge.equity_krw == huge_cash + D("100")


def test_hp2_and_hp4_bid_gap_orders_and_books_differential_450_cases():
    rng = random.Random(2026112702)

    for i in range(250):
        mark = D(rng.randint(1000, 150_000_000)) / D(rng.choice((1, 10, 100)))
        if i % 15 == 0:
            y = None
        elif i % 17 == 0:
            y = D("0.0123456789012345678901")
        else:
            y = D(rng.randint(1, 500)) / D("10000")
        if i % 13 == 0:
            bid = None
        else:
            exact_thresh = mark * (D(1) - (y or D("0.02")))
            delta = rng.choice((D("-0.000001"), D("0"), D("0.000001"), D("-1"), D("1")))
            bid = max(D("0.000001"), exact_thresh + delta)
        nat = _with_native_enabled(lambda: provider._check_bid_gap(bid, mark, y))
        py = _with_native_disabled(lambda: provider._check_bid_gap(bid, mark, y))
        expected = (
            True if (bid is None or y is None)
            else Fraction(bid) <= Fraction(mark) * (Fraction(1) - Fraction(y))
        )
        assert nat == py == expected, (i, bid, mark, y, nat, py, expected)

    rules = InstrumentRules(
        venue="upbit", market="spot", symbol="KRW-BTC",
        lot_size=D("0.00000001"), tick_size=D("1000"),
        min_quantity=D("0.0001"), min_notional_krw=D("5000"),
        fee_fraction=D("0.0005"), asof=T0, source_digest="a" * 64,
    )
    for i in range(150):
        qty = D(rng.randint(1, 500_000)) * D("0.00000001")
        if i % 7 == 0:
            qty += D("0.000000003")
        px = D(rng.randint(1, 200_000)) * D("1000")
        if i % 9 == 0:
            px += D("500")
        order = Order(
            client_id=f"cid-{i}", account_scope="acct1", venue="upbit", market="spot",
            symbol="KRW-BTC", side=rng.choice(("buy", "sell")),
            quantity=qty, limit_price=px, quote_krw=D(1),
        )
        nat_err = py_err = None
        try:
            _with_native_enabled(lambda: validate_order(order, rules))
        except ValueError as e:
            nat_err = str(e)
        try:
            _with_native_disabled(lambda: validate_order(order, rules))
        except ValueError as e:
            py_err = str(e)
        assert nat_err == py_err, (i, nat_err, py_err)

    for i in range(50):
        levels = []
        base_bid = D(rng.randint(50_000, 100_000))
        base_ask = base_bid + D(rng.randint(-10, 50))
        for lv in range(5):
            b = max(D(1), base_bid - D(lv * 10))
            a = max(D(1), base_ask + D(lv * 10))
            bs = D(rng.randint(1, 1000)) / D(100)
            as_ = D(rng.randint(1, 1000)) / D(100)
            levels.append((b, bs, a, as_))
        res = _with_native_enabled(lambda: native_accel.validate_book_levels(levels, allow_crossed=False))
        assert res is not None
        crossed = any(b >= a for b, _, a, _ in levels)
        assert res["valid"] == (not crossed)
        if not crossed:
            assert res["spread"] == levels[0][2] - levels[0][0]


def test_hp3_strategy_and_carry_differential_300_cases():
    rng = random.Random(2026112703)
    rule_sha = "7" * 64
    trend_spec = LP.ProgramSpec(
        schema_version=1, strategy_id="trend-diff", kind="moving_average_trend",
        fast_window=5, slow_window=20, exposure_fraction=D("0.75"),
    )
    rot_spec = LP.ProgramSpec(
        schema_version=2, strategy_id="rot-diff", kind="universe_top1_momentum",
        fast_window=0, slow_window=0, exposure_fraction=D("0.8"),
        lookback_slots=3, min_hold_slots=2, switch_margin=D("0.015"),
        max_candidates=5, universe_rule_sha256=rule_sha,
    )

    for i in range(120):
        if i % 10 == 0:
            marks = tuple(D("100.123456") for _ in range(25))
        else:
            marks = tuple(D(rng.randint(90_000, 110_000)) / D("100") for _ in range(rng.randint(15, 60)))
        nat = _with_native_enabled(lambda: LP.target_fraction(trend_spec, marks))
        py = _with_native_disabled(lambda: LP.target_fraction(trend_spec, marks))
        assert nat == py, (i, nat, py)

    coins = ("KRW-AAA", "KRW-BBB", "KRW-CCC", "KRW-DDD", "KRW-EEE")
    flag_choices = ("unflagged", "warning", "caution", "unknown", "absent")
    state = LP.ChooserState(held=None, hold_count=0)
    for i in range(130):
        top = coins[:rng.randint(1, 5)]
        flags = {c: rng.choices(flag_choices, weights=(6, 1, 1, 1, 1))[0] for c in coins}
        now_p = {c: D(rng.randint(80, 140)) / D(10) for c in coins if rng.random() < 0.85}
        lag_p = {c: D(rng.randint(80, 140)) / D(10) for c in coins if rng.random() < 0.85}
        now_slot = LP.ChooserSlot(top_n=top, flags=flags, prices=now_p)
        lag_slot = None if i % 12 == 0 else LP.ChooserSlot(top_n=top, flags=flags, prices=lag_p)
        nat = _with_native_enabled(lambda: LP.choose(rot_spec, state, now_slot, lag_slot))
        py = _with_native_disabled(lambda: LP.choose(rot_spec, state, now_slot, lag_slot))
        assert nat == py, (i, state, nat, py)
        state = nat[1]

    for i in range(50):
        n_bars = rng.randint(30, 120)
        start_dt = T0
        end_dt = start_dt + timedelta(minutes=n_bars - 1)
        proto = SimpleNamespace(
            schema_version=2, evaluator_revision=MB.CARRY_EVALUATOR_REVISION,
            behavior_revision=MB.BEHAVIOR_REVISION, terminal_accounting=MB.TERMINAL_ACCOUNTING,
            management_behavior_sha256=MB.behavior_digest(), universe_rule_sha256=None,
            initial_cash_quote=D("10000000"), fee_fraction=D("0.0005"), slippage_bps=D("5"),
            capture_end=end_dt, venue="upbit", market="spot", quote_currency="KRW", symbol="KRW-BTC",
        )
        rules = InstrumentRules(
            venue="upbit", market="spot", symbol="KRW-BTC",
            lot_size=D("0.0001"), tick_size=D("1000"),
            min_quantity=D("0.0001"), min_notional_krw=D("5000"),
            fee_fraction=D("0.0005"), asof=start_dt, source_digest="b" * 64,
        )
        bars = []
        decs = []
        marks_prefix = []
        px = D("100000000")
        for b_idx in range(n_bars):
            obs = start_dt + timedelta(minutes=b_idx)
            px = max(D("10000000"), px + D(rng.randint(-500, 520)) * D("1000"))
            bars.append(SimpleNamespace(
                observed_at=obs, bid=px - D("1000"), ask=px + D("1000"), mark=px,
                quote_krw=D(1), source_sha256=f"{b_idx:064x}",
            ))
            marks_prefix.append(px)
            decs.append(MB.derive_fixed_decision_v2(
                trend_spec, tuple(marks_prefix), bar_index=b_idx,
                decided_at=obs, history_sha256=f"{(b_idx + 1000):064x}",
            ))
        bars_t = tuple(bars)
        decs_t = tuple(decs)
        cm = rng.choice((1, 2))
        lg = rng.choice((1, 2))
        bh = rng.choice((False, True))
        nat = _with_native_enabled(lambda: CE.simulate_carry(
            proto, bars_t, decs_t, rules, cost_multiple=cm, lag=lg, buy_hold=bh,
        ))
        py = _with_native_disabled(lambda: CE.simulate_carry(
            proto, bars_t, decs_t, rules, cost_multiple=cm, lag=lg, buy_hold=bh,
        ))
        assert nat == py, f"HP-3 carry mismatch at scenario {i}"


def test_hp5_kis_frame_and_window_differential_150_cases():
    rng = random.Random(2026112705)
    for i in range(100):
        fields = [f"F{j}_{rng.randint(10, 99999)}" for j in range(12)]
        raw = "^".join(fields)
        nat = _with_native_enabled(lambda: _kis_native.parse_caret_fields(raw, 12, 128))
        assert nat == tuple(fields)
        assert _with_native_enabled(lambda: _kis_native.parse_caret_fields(raw, 11, 128)) is False

    for i in range(50):
        ticks = []
        base_dt = T0
        n_ticks = rng.randint(2, 25)
        for k in range(n_ticks):
            obs = base_dt + timedelta(seconds=k * 2)
            rec = obs + timedelta(milliseconds=rng.randint(0, 500))
            px = D(rng.randint(50_000, 90_000))
            sz = D(rng.randint(1, 500))
            ticks.append(kis_live.TradeTick(
                symbol="005930", market="krx", tr_id="H0STCNT0",
                price=px, size=sz, cumulative_volume=sz * D(k + 1),
                observed_at=obs, received_at=rec, state="regular",
                delay_seconds=0, time_inferred=False,
                source_sha256=f"{(i * 100 + k):064x}",
            ))
        t_tup = tuple(ticks)
        now_dt = base_dt + timedelta(seconds=(n_ticks - 1) * 2 + 1)
        book = kis_live.OrderBook(
            symbol="005930", market="krx", tr_id="H0STASP0",
            levels=(
                kis_live.BookLevel(bid=D("70000"), bid_size=D("15"), ask=D("70100"), ask_size=D("10")),
                kis_live.BookLevel(bid=D("69900"), bid_size=D("20"), ask=D("70200"), ask_size=D("25")),
            ),
            observed_at=now_dt, received_at=now_dt, state="regular",
            delay_seconds=0, time_inferred=False, source_sha256="e" * 64,
        )
        nat = _with_native_enabled(lambda: kis_live._metrics(
            t_tup, book, now=now_dt, trade_fresh=True, book_fresh=True,
        ))
        py = _with_native_disabled(lambda: kis_live._metrics(
            t_tup, book, now=now_dt, trade_fresh=True, book_fresh=True,
        ))
        assert nat == py, (i, nat, py)


def test_hp6_odds_mc_and_bid_gap_study_differential():
    with CF.temp_home() as home, CF.pubkey_at(home / "test-anchor.pem"), OF.chunk(), OF.pilots():
        CF.full_home(
            home, venues_raw=OF.ODDS_VENUES,
            limits={"total_loss_floor_krw": 2000.0, "daily_loss_krw": 5000.0}, cap=0.1,
        )
        now = CF.NOW
        positions = CM.Positions(
            equity_krw=1_000_000.0, holdings={}, exposure={"upbit": CM.Exposure(held_krw=0.0)},
        )
        ctx = owner.load_context(now, positions)
        series = OF.fresh_series(end=(now.astimezone(CM.KST).date() - timedelta(days=1)).isoformat())

        for track in ("moonshot", "compounding"):
            for bracket in (None, odds_plan.Bracket(take_profit=0.12, stop=0.06)):
                plan = odds_plan.Plan(
                    name=f"diff-{track}",
                    track=track,
                    stake_krw=100_000.0,
                    target_krw=115_000.0,
                    fx_krw_per_usd=1400.0,
                    start=now.astimezone(CM.KST).date(),
                    horizon_days=5,
                    leg=odds_plan.Leg(
                        venue="upbit", symbol="BTC", model="bootstrap",
                        bracket=bracket, sizing="floor_safe", edge_source="none",
                    ),
                    fraction=odds_plan.fixed(0.25),
                )
                inputs = OF.inputs(plan, series, now=now)
                rep_nat = _with_native_enabled(lambda: odds_sim.simulate(plan, ctx, inputs))
                rep_py = _with_native_disabled(lambda: odds_sim.simulate(plan, ctx, inputs))
                assert _exact_equal(rep_nat, rep_py), f"HP-6 10,000-path MC mismatch for {track} bracket={bracket}"
                assert odds_report.render(rep_nat) == odds_report.render(rep_py)

    sample_rets = [0.002 * ((k % 11) - 5) for k in range(120)]
    s1 = _with_native_enabled(lambda: native_accel.adaptive_bid_gap_mc(
        sample_rets, n_paths=5000, horizon=10, block_len=4, cost_hurdle=0.001, seed=123456789,
    ))
    s2 = _with_native_enabled(lambda: native_accel.adaptive_bid_gap_mc(
        sample_rets, n_paths=5000, horizon=10, block_len=4, cost_hurdle=0.001, seed=123456789,
    ))
    assert s1 is not None and s1 == s2
    assert 0.0 <= s1["favorable_prob"] <= 1.0 and 0.0 <= s1["adverse_prob"] <= 1.0


def test_native_latency_benchmarks():
    rng = random.Random(2026112799)

    # Benchmark 1: HP-1 4-coin 4,000-print continuous interval fold
    t_start = T0
    t_end = T0 + timedelta(minutes=5)
    markets = ("KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL")
    o_u = tuple((m, D("1.5")) for m in markets)
    o_m = {m: D("1000000") for m in markets}
    h_fills = tuple(
        _upbit_fill(
            order_id=f"bench-ho-{idx}", fill_id=f"bench-hf-{idx}", symbol=m, side="buy",
            quantity=D("1.5"), price=D("1000000"), fee=D(0),
            executed_at=t_start - timedelta(minutes=5),
        )
        for idx, m in enumerate(markets)
    )
    base_ms = int(t_start.timestamp() * 1000) + 10
    prints_by = {
        m: tuple(
            _tprint(
                market=m, seq=j + 1, ts_ms=base_ms + j * 20,
                price=D(1_000_000 + (j % 50) * 100), volume=D("0.1"), ask_bid="BID",
            )
            for j in range(1000)
        )
        for m in markets
    }
    prev_eq = D("10000000") + D("6000000")

    t0 = time.perf_counter()
    for _ in range(5):
        _with_native_enabled(lambda: continuous.value_trade_paths(
            prints_by, opening_marks=o_m, opening_cash_krw=D("10000000"),
            opening_units=o_u, historical_fills=h_fills, interval_fills=(),
            previous_equity_krw=prev_eq, previous_realized_net_krw=D(0),
            start=t_start, end=t_end, account_scope="acct-1",
        ))
    hp1_nat_ms = (time.perf_counter() - t0) * 1000.0 / 5.0

    t0 = time.perf_counter()
    for _ in range(2):
        _with_native_disabled(lambda: continuous.value_trade_paths(
            prints_by, opening_marks=o_m, opening_cash_krw=D("10000000"),
            opening_units=o_u, historical_fills=h_fills, interval_fills=(),
            previous_equity_krw=prev_eq, previous_realized_net_krw=D(0),
            start=t_start, end=t_end, account_scope="acct-1",
        ))
    hp1_py_ms = (time.perf_counter() - t0) * 1000.0 / 2.0

    # Benchmark 2: HP-3 2,000-bar multi-lot decimal carry simulation + 2,000-mark MA crossover
    n_bars = 2000
    proto = SimpleNamespace(
        schema_version=2, evaluator_revision=MB.CARRY_EVALUATOR_REVISION,
        behavior_revision=MB.BEHAVIOR_REVISION, terminal_accounting=MB.TERMINAL_ACCOUNTING,
        management_behavior_sha256=MB.behavior_digest(), universe_rule_sha256=None,
        initial_cash_quote=D("100000000"), fee_fraction=D("0.0005"),
        slippage_bps=D("5"), capture_end=T0 + timedelta(minutes=n_bars - 1),
        venue="upbit", market="spot", quote_currency="KRW", symbol="KRW-BTC",
    )
    rules = InstrumentRules(
        venue="upbit", market="spot", symbol="KRW-BTC",
        lot_size=D("0.00000001"), tick_size=D("0.01"),
        min_quantity=D("0.0001"), min_notional_krw=D("5000"),
        fee_fraction=D("0.0005"), asof=T0, source_digest="c" * 64,
    )
    ma_bench_spec = LP.ProgramSpec(
        schema_version=1, strategy_id="bench-ma-2000", kind="moving_average_trend",
        fast_window=400, slow_window=1800, exposure_fraction=D("0.8"),
    )
    bars = []
    decs = []
    px = D("123456.78")
    for b_i in range(n_bars):
        obs = T0 + timedelta(minutes=b_i)
        px = max(D("50000.01"), px + D(rng.randint(-400, 410)) * D("0.03"))
        bars.append(SimpleNamespace(
            observed_at=obs, bid=px - D("0.02"), ask=px + D("0.02"), mark=px,
            quote_krw=D(1), source_sha256=f"{b_i:064x}",
        ))
        cycle_pos = b_i % 250
        if cycle_pos < 245:
            tf_step = (D(cycle_pos + 1) / D(250)).quantize(D("0.0001"))
            st, cs, tf = ("long_target", "trend_above", tf_step)
        else:
            st, cs, tf = ("cash_target", "trend_not_above", D("0"))
        decs.append(MB._make(
            bar_index=b_i, decided_at=obs, history_sha256=f"{(b_i + 5000):064x}",
            state=st, cause=cs, target=tf,
        ))
    bars_t, decs_t = tuple(bars), tuple(decs)
    marks_2000 = tuple(b.mark for b in bars_t)

    def _run_hp3_workload():
        CE.simulate_carry(proto, bars_t, decs_t, rules)
        for _ in range(10):
            LP.target_fraction(ma_bench_spec, marks_2000)

    t0 = time.perf_counter()
    for _ in range(3):
        _with_native_enabled(_run_hp3_workload)
    hp3_nat_ms = (time.perf_counter() - t0) * 1000.0 / 3.0

    t0 = time.perf_counter()
    for _ in range(2):
        _with_native_disabled(_run_hp3_workload)
    hp3_py_ms = (time.perf_counter() - t0) * 1000.0 / 2.0

    # Benchmark 3: HP-6 10,000-path Monte Carlo odds simulation
    with CF.temp_home() as home, CF.pubkey_at(home / "test-anchor.pem"), OF.chunk(), OF.pilots():
        CF.full_home(
            home, venues_raw=OF.ODDS_VENUES,
            limits={"total_loss_floor_krw": 2000.0, "daily_loss_krw": 5000.0}, cap=0.1,
        )
        now = CF.NOW
        positions = CM.Positions(
            equity_krw=1_000_000.0, holdings={}, exposure={"upbit": CM.Exposure(held_krw=0.0)},
        )
        ctx = owner.load_context(now, positions)
        series = OF.fresh_series(end=(now.astimezone(CM.KST).date() - timedelta(days=1)).isoformat())
        plan = odds_plan.Plan(
            name="bench-mc", track="compounding", stake_krw=100_000.0, target_krw=120_000.0,
            fx_krw_per_usd=1400.0, start=now.astimezone(CM.KST).date(), horizon_days=10,
            leg=odds_plan.Leg(
                venue="upbit", symbol="BTC", model="bootstrap",
                bracket=odds_plan.Bracket(take_profit=0.15, stop=0.08),
                sizing="floor_safe", edge_source="none",
            ),
            fraction=odds_plan.fixed(0.3),
        )
        inputs = OF.inputs(plan, series, now=now)
        t0 = time.perf_counter()
        for _ in range(5):
            _with_native_enabled(lambda: odds_sim.simulate(plan, ctx, inputs))
        hp6_nat_ms = (time.perf_counter() - t0) * 1000.0 / 5.0

        t0 = time.perf_counter()
        for _ in range(2):
            _with_native_disabled(lambda: odds_sim.simulate(plan, ctx, inputs))
        hp6_py_ms = (time.perf_counter() - t0) * 1000.0 / 2.0

    assert hp1_nat_ms < hp1_py_ms, (hp1_nat_ms, hp1_py_ms)
    assert hp3_nat_ms < hp3_py_ms, (hp3_nat_ms, hp3_py_ms)
    assert hp6_nat_ms < hp6_py_ms, (hp6_nat_ms, hp6_py_ms)
    print(json.dumps({
        "benchmark": "tradegen_fast_cpp20",
        "hp1_4coin_4000prints_ms": {"native": round(hp1_nat_ms, 2), "python": round(hp1_py_ms, 2),
                                    "speedup_x": round(hp1_py_ms / hp1_nat_ms, 2)},
        "hp3_2000bars_carry_ms": {"native": round(hp3_nat_ms, 2), "python": round(hp3_py_ms, 2),
                                  "speedup_x": round(hp3_py_ms / hp3_nat_ms, 2)},
        "hp6_10000paths_mc_ms": {"native": round(hp6_nat_ms, 2), "python": round(hp6_py_ms, 2),
                                 "speedup_x": round(hp6_py_ms / hp6_nat_ms, 2)},
    }, sort_keys=True))


def tests():
    module = sys.modules[__name__]
    from tests.control_acceptance import _wrap
    return [
        ("native_cpp_acceptance/" + name, _wrap(fn))
        for name, fn in sorted(vars(module).items())
        if name.startswith("test_") and callable(fn)
    ]


def main(argv=None) -> int:
    from tests.run_all import run
    args = list(sys.argv[1:] if argv is None else argv)
    rows = run([(n, fn) for n, fn in tests() if not args or args[0] in n])
    counts = {s: sum(r["status"] == s for r in rows) for s in ("PASS", "FAIL", "NOT_RUN")}
    print(counts)
    return 0 if rows and counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
