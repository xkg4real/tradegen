"""Plan types, injected inputs and the product, state and data checks (odds Task 5; spec 7.1, 7.2 "Data rules";
contract 5; Q4, Q7, Q8, Q23, Q24, Q25, Q39). Helpers are prefixed `_t5_` so later tasks cannot shadow them."""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
import types

from core.compliance import gate, model, owner, rules
from core.odds import plan as P
from tests import compliance_fixtures as F
from tests import odds_fixtures as OF

_T5_START = dt.date(2026, 10, 23)                       # F.ctx's date, a Friday
_T5_NOW = dt.datetime(2026, 10, 23, 9, 0, tzinfo=model.KST)
_T5_UTC = dt.timezone.utc
_T5_SHA = "a" * 64
_T5_OPTION = "AAPL261218C00300000"                      # fixture-only symbol; the shipped map has no option
_T5_KRX_DAYS = ("2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28")
_T5_KIS = {"symbol": "005930", "source": "KIS", "price": 70_000.0}
_T5_YAHOO = {"symbol": "AAPL", "source": "YAHOO:AAPL*YAHOO:KRW=X", "price": 300_000.0}


class _T5Date(dt.date):
    """A date subclass: equal to the date it names, but not a plain date."""


class _T5Leg(P.Leg):
    """A Leg subclass: every Leg field, but not exactly a Leg (pre-flight P29)."""


class _T5BadTZ(dt.tzinfo):
    """A tzinfo whose utcoffset is not a timedelta, so datetime.utcoffset() raises TypeError."""

    def utcoffset(self, moment):
        return 5


def _t5_code(refusal) -> tuple[str, str] | None:
    return None if refusal is None else (refusal.code, refusal.sub)


def _t5_days(first: dt.date, n: int) -> tuple[str, ...]:
    return tuple((first + dt.timedelta(days=i)).isoformat() for i in range(n))


def _t5_md5(s: P.Series) -> P.Series:
    """`s` with its md5 recomputed (left as it was when a price has no canonical JSON, such as NaN)."""
    try:
        return dataclasses.replace(s, md5=P.series_md5(s.symbol, s.source, s.dates, s.open, s.close, s.adjustment,
                                                         s.status))
    except (TypeError, ValueError):
        return s


def _t5_series(base: P.Series | None = None, **changes) -> P.Series:
    """`base` (OF.series(n=300) by default) with `changes`; the md5 is recomputed unless `md5` is one of them."""
    s = dataclasses.replace(base if base is not None else OF.series(n=300), **changes)
    return s if "md5" in changes else _t5_md5(s)


def _t5_ending(last: str, n: int = 300, **kwargs) -> P.Series:
    """OF.series of n daily bars whose last bar is dated `last`."""
    first = dt.date.fromisoformat(last) - dt.timedelta(days=n - 1)
    return OF.series(n=n, start=first.isoformat(), **kwargs)


def _t5_inputs(series: P.Series, **changes) -> P.Inputs:
    """Inputs of a 10-day crypto horizon from 2026-10-23 (Task 9 adds the public OF.inputs)."""
    fields = dict(now=_T5_NOW, series=series, sessions=_t5_days(_T5_START, 10), price_limits=(),
                  calendar_sha256="", calendar_version="", calendar_md5s=(), calendar_error="", replay=None,
                  comparison_id="c000001", run_counter=1, comparison_plans=1, comparison_typed=0, plan_runs=1,
                  provenance=P.Provenance(repo_anchor="git:" + "0" * 40, tree_hash="f" * 64, cryptography="49.0.0"))
    fields.update(changes)
    return P.Inputs(**fields)


def _t5_krx(series: P.Series | None = None, **changes) -> P.Inputs:
    """Inputs of a KRX horizon: four sessions, a 30% limit each, a 64-hex calendar sha."""
    fields = {"sessions": _T5_KRX_DAYS, "price_limits": (0.3,) * 4, "calendar_sha256": _T5_SHA, **changes}
    return _t5_inputs(series if series is not None else OF.series(**_T5_KIS), **fields)


def _t5_us(series: P.Series | None = None, **changes) -> P.Inputs:
    """Inputs of a US horizon: two New York sessions, no limits, a 64-hex calendar sha."""
    fields = {"sessions": ("2026-10-23", "2026-10-26"), "calendar_sha256": _T5_SHA, **changes}
    return _t5_inputs(series if series is not None else OF.series(**_T5_YAHOO), **fields)


def _t5_ctx_with(entries: dict) -> model.Context:
    """OF.odds_ctx() whose APPROVED map has `entries` applied ((section, symbol) -> Instrument, or None to drop)."""
    state = F.approved(venues=OF.ODDS_VENUES)
    new = dict(state.instruments.entries)
    for key, inst in entries.items():
        if inst is None:
            del new[key]
        else:
            new[key] = inst
    return OF.odds_ctx(active=dataclasses.replace(state, instruments=dataclasses.replace(state.instruments,
                                                                                          entries=new)))


def _t5_option_ctx() -> model.Context:
    """OF.odds_ctx() whose approved map is the shipped one plus a US option, parsed by the real loader."""
    raw = F.shipped_bytes("instruments")
    assert raw.count(b"\ncrypto:\n") == 1
    entry = (f"  {_T5_OPTION}:\n    asset: us_option\n    multiple: 1.0\n    underlying: null\n    class: option\n"
             "    cost_book: null\n    currency: USD\n    tax_basis: unsupported\n"
             '    source: "fixture: not a real listing"\n').encode("utf-8")
    state = F.approved(instruments=raw.replace(b"\ncrypto:\n", b"\n" + entry + b"crypto:\n"), venues=OF.ODDS_VENUES)
    assert state.valid, state.reason
    assert state.instruments.entries[("us", _T5_OPTION)].cls == "option"
    return OF.odds_ctx(active=state)


def _t5_owner(**changes) -> model.OwnerState:
    return dataclasses.replace(OF.odds_ctx().owner, **changes)


# --------------------------------------------------------------------------- #
# Constants, types and fixtures
# --------------------------------------------------------------------------- #
def test_constants_are_the_contracts():
    assert P.REFUSALS == ("PARTIAL_CHUNK", "UNSUPPORTED_PRODUCT", "MULTI_LEG_UNSUPPORTED", "STATE_UNUSABLE",
                          "LIMITS_UNSET", "CALENDAR_UNSIGNED", "CALENDAR_COVERAGE", "DATA_INVALID",
                          "SYNTHETIC_REFUSED", "NOT_TRADABLE", "SPECIAL_REGIME", "SHORT_HISTORY",
                          "CARD_NOT_REPRODUCED", "MODEL_NOT_FOR_LIMITED_VENUE", "COST_DOMINATED", "STUCK_AT_START",
                          "SCREEN_BLOCKED", "ASSUMED_EDGE_UNREACHABLE", "MODEL_CHECK_FAILED")
    assert P.VENUES_OK == ("kis", "upbit", "okx") and set(P.VENUES_OK) <= rules.VENUES
    assert P.CLASSES_OK == ("share", "etp_1x", "coin") and set(P.CLASSES_OK) <= rules.CLASSES
    assert P.TAX_BASES_OK == ("krx_small_holder_exempt", "overseas_22pct_over_2.5m", "crypto_22pct_from_2027")
    assert set(P.TAX_BASES_OK) == rules.TAX_BASES - {"unsupported"}
    assert P.TRACKS == ("moonshot", "compounding") and P.MODELS == ("bootstrap", "garch_t")
    assert P.SIZINGS == ("floor_safe", "stop_based") and P.FRACTION_KINDS == ("fixed", "kelly", "bold")
    assert P.REPLAY_SOURCE == "replay:S_C3_crypto_trend_krwbtc"
    assert P.EDGE_SOURCES == ("none", "assumed", P.REPLAY_SOURCE)
    assert (P.MAX_HORIZON_DAYS, P.MIN_BARS, P.SPECIAL_REGIME_BARS) == (366, 250, 60)
    assert P.STALE_DAYS == {"CRYPTO": 3, "KR": 14, "US": 14}                          # R2-8
    assert P.LIMIT_KEYS == owner._LIMIT_KEYS == ("total_loss_floor_krw", "daily_loss_krw")
    assert P.OKX_CAP_KEY == "okx_equity_share" and P.OKX_CAP_KEY in OF.odds_ctx().owner.caps
    assert P.FEEDS == {("kis", "krx"): "kis_daily", ("kis", "us"): "yfinance", ("upbit", "crypto"): "upbit_daily",
                       ("okx", "crypto"): "binance_x_upbit_usdt"}
    assert P.MARKET == {("kis", "krx"): "KR", ("kis", "us"): "US", ("upbit", "crypto"): "CRYPTO",
                        ("okx", "crypto"): "CRYPTO"}
    assert set(P.MARKET.values()) == set(P.STALE_DAYS) and set(P.MARKET) == set(P.FEEDS)


def test_types_are_frozen_kw_only_dataclasses():
    for cls in (P.Bracket, P.Fraction, P.Leg, P.Plan, P.Refusal, P.Series, P.Provenance, P.ReplayInput, P.Inputs):
        assert dataclasses.is_dataclass(cls) and cls.__dataclass_params__.frozen, cls
        assert all(f.kw_only for f in dataclasses.fields(cls)), cls
    assert P.fixed(1) == P.Fraction(kind="fixed", value=1.0) and type(P.fixed(1).value) is float
    assert P.kelly(0.5) == P.Fraction(kind="kelly", value=0.5) and P.bold() == P.Fraction(kind="bold")
    assert P.bold().value is None
    refusal = P.Refusal(code="LIMITS_UNSET")
    assert (refusal.sub, dict(refusal.slots), refusal.detail) == ("", {}, "")
    leg = P.Leg(venue="upbit", symbol="BTC", model="bootstrap")
    assert (leg.bracket, leg.sizing, leg.edge_source, leg.assumed_p) == (None, "floor_safe", "none", None)
    s = OF.series(n=3)
    assert (s.components, s.proxy_dates) == ((), None)
    try:
        leg.venue = "okx"
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("Leg is not frozen")


def test_odds_venues_parse_valid_with_every_odds_key():
    state = F.approved(venues=OF.ODDS_VENUES)
    assert state.valid, state.reason
    assert set(state.venues.venues) == {"kis", "upbit", "okx"}
    kis, upbit, okx = (state.venues.venues[v] for v in ("kis", "upbit", "okx"))
    assert kis.lot == (("005930", 1.0), ("069500", 1.0), ("default", 1.0))           # the KRX codes stay text
    assert upbit.lot == okx.lot == (("default", 1e-8),)
    assert (kis.min_order, upbit.min_order, okx.min_order) == ((("KRW", 0.0), ("USD", 0.0)), (("KRW", 5000.0),),
                                                               (("USDT", 1.0),))
    assert (kis.lot_for("005930"), kis.lot_for("069500"), kis.lot_for("AAPL")) == (1.0, 1.0, 1.0)
    assert (kis.min_order_for("KRW"), kis.min_order_for("USD")) == (0.0, 0.0)
    assert kis.fee_extras == upbit.fee_extras == okx.fee_extras == (0.0, 0.0)
    assert kis.ladder_for("KRX_stock_book") == ("2026-10-02", ((0.0, 1.0), (2000.0, 5.0), (5000.0, 10.0),
                                                              (20000.0, 50.0), (50000.0, 100.0), (200000.0, 500.0),
                                                              (500000.0, 1000.0)))
    assert (upbit.lot_for("BTC"), upbit.lot_for("USDT"), upbit.min_order_for("KRW")) == (1e-8, 1e-8, 5000.0)
    assert (okx.lot_for("BTC"), okx.min_order_for("USDT"), okx.min_order_for("USDC")) == (1e-8, 1.0, None)
    assert upbit.ladder_for("crypto_venue") is None and okx.ladder_for("crypto_venue") is None
    assert {key for key, _src in kis.odds_sources} == {"lot", "min_order", "fee_extras", "tick_ladder"}
    assert {key for key, _src in upbit.odds_sources} == {key for key, _src in okx.odds_sources} == {
        "lot", "min_order", "fee_extras"}
    assert {src for v in (kis, upbit, okx) for _key, src in v.odds_sources} == {
        "UNVERIFIED: owner to confirm before approval"}


def test_venues_with_replaces_or_removes_one_venues_odds_keys():
    assert OF.venues_with() == OF.ODDS_VENUES
    raw = OF.venues_with(upbit={"fee_extras": None, "lot": {"units": {"BTC": 0.0001}}})
    state = F.approved(venues=raw)
    assert state.valid, state.reason
    upbit = state.venues.venues["upbit"]
    assert upbit.fee_extras is None and upbit.lot_for("BTC") == 0.0001 and upbit.lot_for("USDT") is None
    assert upbit.min_order_for("KRW") == 5000.0
    assert dict(upbit.odds_sources)["lot"] == "UNVERIFIED: owner to confirm before approval"
    full = F.approved(venues=OF.ODDS_VENUES).venues.venues
    assert state.venues.venues["kis"] == full["kis"] and state.venues.venues["okx"] == full["okx"]
    gone = F.approved(venues=OF.venues_with(kis={"tick_ladder": None})).venues.venues["kis"]
    assert gone.ladder_for("KRX_stock_book") is None and gone.lot_for("005930") == 1.0
    for bad in ({"bithumb": {"lot": None}}, {"upbit": {"markets": None}}):
        try:
            OF.venues_with(**bad)
        except KeyError:
            continue
        raise AssertionError(f"venues_with accepted {bad}")


def test_fixture_defaults_pass_every_check():
    p, ctx = OF.plan(), OF.odds_ctx()
    assert model.is_sealed(ctx) and ctx.date == p.start == _T5_START and ctx.equity_krw == 42_000.0
    assert ctx.code_signed is True and ctx.active.valid
    assert dict(ctx.owner.limits) == {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}
    assert dict(ctx.owner.caps) == {"okx_equity_share": 0.10}
    assert (p.track, p.stake_krw, p.target_krw, p.fx_krw_per_usd, p.horizon_days) == (
        "compounding", 42_000.0, 42_000_000.0, 1_400.0, 10)
    assert p.leg == P.Leg(venue="upbit", symbol="BTC", model="bootstrap") and p.fraction == P.fixed(1.0)
    s = OF.series()
    assert len(s.dates) == 600 and s.dates[-1] == "2026-10-22" and s.dates[0] == "2025-03-02"
    assert s == OF.series() and s.md5 == _t5_md5(s).md5 and s.status == "final" and s.adjustment == ""
    assert s.open[0] == 50_000_000.0 and s.open[1:] == s.close[:-1]                  # open_gap 0
    assert OF.series(start="2024-01-01", n=3).dates == ("2024-01-01", "2024-01-02", "2024-01-03")
    inputs = _t5_inputs(s)
    assert P.check_plan(p, ctx) is None and P.check_state(p, ctx) is None and P.check_now(ctx, _T5_NOW) is None
    assert P.check_data(p, ctx, inputs, "CRYPTO") is None and P.check_history(p, inputs, "CRYPTO") is None
    widened = OF.plan(stake_krw=50_000, target_krw=60_000, fx_krw_per_usd=1_350)
    assert (widened.stake_krw, widened.target_krw, widened.fx_krw_per_usd) == (50_000.0, 60_000.0, 1_350.0)
    assert all(type(x) is float for x in (widened.stake_krw, widened.target_krw, widened.fx_krw_per_usd))
    assert OF.plan(venue="kis", symbol="005930").leg == P.Leg(venue="kis", symbol="005930", model="bootstrap")


# --------------------------------------------------------------------------- #
# Product checks (Q4, Q7, Q24 step 2, Q25)
# --------------------------------------------------------------------------- #
def test_whitelist_passes_the_supported_legs():
    ctx = OF.odds_ctx()
    for venue, symbol, sect in (("kis", "005930", "krx"), ("kis", "069500", "krx"), ("kis", "AAPL", "us"),
                                ("kis", "SPY", "us"), ("upbit", "BTC", "crypto"), ("upbit", "USDT", "crypto"),
                                ("okx", "BTC", "crypto")):
        p = OF.plan(venue=venue, symbol=symbol)
        assert P.check_plan(p, ctx) is None, (venue, symbol, P.check_plan(p, ctx))
        facts, inst = P.instrument(p, ctx)
        assert facts is ctx.active.venues.venues[venue], (venue, symbol)
        assert inst is ctx.active.instruments.entries[(sect, symbol)], (venue, symbol)
        assert P.section(p, ctx) == sect and P.MARKET[(venue, sect)] in P.STALE_DAYS


def test_whitelist_refuses_everything_else_with_its_sub():
    ctx = _t5_option_ctx()
    cases = {("bithumb", "BTC"): "venue", ("coinone", "BTC"): "venue", ("korbit", "BTC"): "venue",
             ("gopax", "BTC"): "venue", ("binance", "BTC"): "venue", ("nowhere", "BTC"): "venue",
             ("okx", "USDT"): "feed", ("okx", "USDC"): "feed", ("kis", "TQQQ"): "class", ("kis", "252670"): "class",
             ("kis", "114800"): "class", ("kis", "SH"): "class", ("kis", "IBIT"): "class", ("kis", "BITO"): "class",
             ("kis", _T5_OPTION): "class", ("upbit", "DOGE"): "symbol", ("upbit", "005930"): "symbol",
             ("kis", "BTC"): "symbol", ("upbit", "USDC"): "symbol"}
    for (venue, symbol), sub in cases.items():
        got = P.check_plan(OF.plan(venue=venue, symbol=symbol), ctx)
        assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", sub), (venue, symbol, got)
        assert got.detail and not got.slots, (venue, symbol)
    assert P.check_plan(OF.plan(venue="kis", symbol="AAPL"), ctx) is None        # the option map keeps the rest


def test_instrument_facts_come_from_the_approved_map_never_the_draft():
    shipped = rules.parse_instruments(F.shipped_bytes("instruments")).entries
    assert ("us", "AAPL") in shipped                                   # the draft lists AAPL,
    ctx = _t5_ctx_with({("us", "AAPL"): None})                          # the approved map does not
    got = P.check_plan(OF.plan(venue="kis", symbol="AAPL"), ctx)
    assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", "symbol"), got
    assert P.instrument(OF.plan(venue="kis", symbol="AAPL"), ctx)[1] is None
    base = F.approved(venues=OF.ODDS_VENUES).instruments.entries
    edits = {"class": (("krx", "005930"), {"cls": "etp_leveraged"}),          # the draft says share
             "multiple": (("krx", "069500"), {"multiple": 2.0}),
             "tax": (("krx", "005930"), {"tax_basis": "unsupported"})}
    for sub, (key, change) in edits.items():
        ctx = _t5_ctx_with({key: dataclasses.replace(base[key], **change)})
        got = P.check_plan(OF.plan(venue="kis", symbol=key[1]), ctx)
        assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", sub), (sub, got)
    wide = F.approved(venues=OF.ODDS_VENUES.replace(b"sections: [krx, us]", b"sections: [krx, us, crypto]"))
    assert wide.valid, wide.reason                                     # a signed kis file may list crypto too,
    got = P.check_plan(OF.plan(venue="kis", symbol="BTC"), OF.odds_ctx(active=wide))
    assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", "feed"), got       # but (kis, crypto) has no price feed
    assert P.check_plan(OF.plan(venue="kis", symbol="005930"), OF.odds_ctx(active=wide)) is None


def test_instrument_checks_need_a_usable_approved_state():
    ctx = OF.odds_ctx(active=model.ApprovedState.invalid("unapproved: no signed approval for rules"))
    for symbol in ("TQQQ", "NOT-LISTED"):
        p = OF.plan(venue="kis", symbol=symbol)
        assert P.check_plan(p, ctx) is None, symbol                 # no class or symbol check without a state;
        assert _t5_code(P.check_state(p, ctx)) == ("STATE_UNUSABLE", ""), symbol   # the state step refuses
        assert P.instrument(p, ctx) == (None, None) and P.section(p, ctx) is None
    assert P.instrument(OF.plan(), None) == (None, None)


def test_multi_leg_unsupported_for_two_or_more_legs():
    ctx, leg = OF.odds_ctx(), OF.plan().leg
    for legs in ((leg, leg), [leg, leg], (leg, "not a leg"), (leg, leg, leg)):
        got = P.check_plan(OF.plan(leg=legs), ctx)
        assert _t5_code(got) == ("MULTI_LEG_UNSUPPORTED", ""), (legs, got)
    assert _t5_code(P.check_plan(OF.plan(leg=(leg, leg), horizon_days=0), ctx)) == ("MULTI_LEG_UNSUPPORTED", "")
    for legs in ((), [], ("not a leg",)):                              # no leg at all is not "more than one"
        assert _t5_code(P.check_plan(OF.plan(leg=legs), ctx)) == ("UNSUPPORTED_PRODUCT", "file"), legs
    sub_leg = _T5Leg(venue="upbit", symbol="BTC", model="bootstrap")     # P29: exactly a Leg, never a subclass
    for legs in (sub_leg, (sub_leg,), [sub_leg]):
        assert _t5_code(P.check_plan(OF.plan(leg=legs), ctx)) == ("UNSUPPORTED_PRODUCT", "file"), legs
    assert P.check_plan(OF.plan(leg=(leg,)), ctx) is None and P.check_plan(OF.plan(leg=[leg]), ctx) is None
    one_bad = dataclasses.replace(leg, venue="bithumb")
    assert _t5_code(P.check_plan(OF.plan(leg=(one_bad,)), ctx)) == ("UNSUPPORTED_PRODUCT", "venue")


def test_range_rules_each_refuse_with_their_sub():
    ctx, base = OF.odds_ctx(), OF.plan()
    br = P.Bracket(take_profit=0.10, stop=0.05)
    replay = P.REPLAY_SOURCE
    cases = [
        ("file", dataclasses.replace(base, name=None)), ("file", dataclasses.replace(base, name=7)),
        ("file", None), ("file", dataclasses.replace(base, leg={"venue": "upbit", "symbol": "BTC"})),
        ("track", OF.plan(track="lottery")), ("track", OF.plan(track=None)),
        ("numbers", dataclasses.replace(base, stake_krw=0.0)), ("numbers", dataclasses.replace(base, stake_krw=-1.0)),
        ("numbers", dataclasses.replace(base, stake_krw=42_000)),           # an int: the numbers are floats
        ("numbers", dataclasses.replace(base, stake_krw=math.nan)),
        ("numbers", dataclasses.replace(base, target_krw=42_000.0)),        # not above the stake
        ("numbers", dataclasses.replace(base, target_krw=math.inf)),
        ("numbers", dataclasses.replace(base, fx_krw_per_usd=0.0)),
        ("numbers", dataclasses.replace(base, fx_krw_per_usd=True)),
        ("start", dataclasses.replace(base, start="2026-10-23")),
        ("start", dataclasses.replace(base, start=dt.datetime(2026, 10, 23))),
        ("start", dataclasses.replace(base, start=_T5Date(2026, 10, 23))),  # equal to ctx.date, not a date: the gate
                                                                             # refuses it too (`type(start) is date`)
        ("start", dataclasses.replace(base, start=dt.date(2026, 10, 24))),   # not ctx.date (gate.py's own rule)
        ("start", dataclasses.replace(base, start=dt.date(2026, 10, 22))),
        ("horizon", OF.plan(horizon_days=0)), ("horizon", OF.plan(horizon_days=367)),
        ("horizon", OF.plan(horizon_days=10.0)), ("horizon", OF.plan(horizon_days=True)),
        ("model", OF.plan(model="gbm")), ("model", OF.plan(model=None)),
        ("sizing", OF.plan(sizing="aggressive")), ("sizing", OF.plan(sizing="stop_based")),   # stop_based, no bracket
        ("fraction", OF.plan(fraction=P.fixed(0.0))), ("fraction", OF.plan(fraction=P.fixed(1.5))),
        ("fraction", OF.plan(fraction=P.kelly(0.25))),                       # Kelly off the replay
        ("fraction", OF.plan(edge_source=replay, fraction=P.kelly(0.6))),
        ("fraction", OF.plan(fraction=P.bold())),                            # bold with no bracket
        ("fraction", OF.plan(fraction=P.Fraction(kind="bold", value=0.5), bracket=br)),
        ("fraction", OF.plan(edge_source=replay, bracket=br, fraction=P.bold())),   # bold never on the replay
        ("fraction", OF.plan(fraction=P.Fraction(kind="martingale", value=1.0))),
        ("fraction", OF.plan(bracket=br, fraction=P.Fraction(kind="martingale"))),  # no other kind, even bold-shaped
        ("fraction", OF.plan(fraction=1.0)),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=0.0, stop=0.05))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=1000.5, stop=0.05))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=0.1, stop=1.0))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=0.1, stop=0.0))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=math.nan, stop=0.05))),
        ("bracket", OF.plan(bracket=P.Bracket(take_profit=True, stop=0.05))),
        ("bracket", OF.plan(bracket=(0.1, 0.05))),
        ("edge", OF.plan(edge_source="magic")),
        ("edge", OF.plan(edge_source="assumed", assumed_p=0.55)),                            # no bracket
        ("edge", OF.plan(edge_source="assumed", assumed_p=0.55, bracket=br, model="garch_t")),
        ("edge", OF.plan(edge_source="assumed", assumed_p=1.0, bracket=br)),
        ("edge", OF.plan(edge_source="assumed", assumed_p=0.0, bracket=br)),
        ("edge", OF.plan(edge_source="assumed", assumed_p=None, bracket=br)),
        ("edge", OF.plan(assumed_p=0.5)),                                                    # a rate, no assumed edge
        ("replay", OF.plan(edge_source=replay, venue="okx")),
        ("replay", OF.plan(edge_source=replay, symbol="USDT")),
        ("replay", OF.plan(edge_source=replay, bracket=br)),
        ("replay", OF.plan(edge_source=replay, model="garch_t")),
        ("replay", OF.plan(edge_source=replay, bracket=br, sizing="stop_based")),
    ]
    for sub, p in cases:
        got = P.check_plan(p, ctx)
        assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", sub), (sub, p, got)
    passing = [OF.plan(bracket=br), OF.plan(bracket=br, sizing="stop_based"), OF.plan(bracket=br, fraction=P.bold()),
               OF.plan(bracket=P.Bracket(take_profit=1000.0, stop=0.99)), OF.plan(track="moonshot"),
               OF.plan(bracket=br, edge_source="assumed", assumed_p=0.55), OF.plan(model="garch_t"),
               OF.plan(edge_source=replay), OF.plan(edge_source=replay, fraction=P.kelly(0.5)),
               OF.plan(horizon_days=1), OF.plan(horizon_days=366), OF.plan(fraction=P.fixed(1e-9)),
               OF.plan(name="")]
    for p in passing:
        assert P.check_plan(p, ctx) is None, (p, P.check_plan(p, ctx))


def test_product_refusals_come_in_the_contract_order():
    ctx = OF.odds_ctx()
    first = [("file", dataclasses.replace(OF.plan(track="lottery"), name=None)),
             ("track", OF.plan(track="lottery", horizon_days=0)),
             ("start", OF.plan(start=dt.date(2026, 10, 24), horizon_days=0)),
             ("horizon", OF.plan(venue="bithumb", horizon_days=0)),              # every range rule before the venue
             ("model", OF.plan(venue="okx", symbol="USDT", model="gbm")),
             ("venue", OF.plan(venue="bithumb", symbol="USDT")),
             ("feed", OF.plan(venue="okx", symbol="DOGE"))]                       # the feed before the symbol
    for sub, p in first:
        assert _t5_code(P.check_plan(p, ctx)) == ("UNSUPPORTED_PRODUCT", sub), (sub, P.check_plan(p, ctx))
    # P23: two faults each, one per pair of neighbouring rules that can both fail; the earlier rule's sub wins
    bad_br, replay = P.Bracket(take_profit=0.0, stop=0.05), P.REPLAY_SOURCE
    pairs = [("track", OF.plan(track="lottery", stake_krw=0.0)),
             ("numbers", OF.plan(stake_krw=0.0, start=dt.date(2026, 10, 24))),
             ("horizon", OF.plan(leg=(), horizon_days=0)),                          # the empty leg list after horizon
             ("model", OF.plan(model="gbm", sizing="aggressive")),
             ("sizing", OF.plan(sizing="aggressive", fraction=P.fixed(0.0))),
             ("fraction", OF.plan(fraction=P.fixed(1.5), bracket=bad_br)),
             ("bracket", OF.plan(bracket=bad_br, edge_source="magic")),
             ("edge", OF.plan(edge_source=replay, assumed_p=0.5, venue="okx")),
             ("replay", OF.plan(edge_source=replay, venue="bithumb"))]
    for sub, p in pairs:
        assert _t5_code(P.check_plan(p, ctx)) == ("UNSUPPORTED_PRODUCT", sub), (sub, P.check_plan(p, ctx))
    base = F.approved(venues=OF.ODDS_VENUES).instruments.entries
    for sub, key, change in (("class", ("krx", "005930"), {"cls": "etp_leveraged", "multiple": 2.0}),
                             ("multiple", ("krx", "069500"), {"multiple": 2.0, "tax_basis": "unsupported"})):
        edited = _t5_ctx_with({key: dataclasses.replace(base[key], **change)})
        got = P.check_plan(OF.plan(venue="kis", symbol=key[1]), edited)
        assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", sub), (sub, got)
    wide = F.approved(venues=OF.ODDS_VENUES.replace(b"sections: [krx, us]", b"sections: [krx, us, crypto]"))
    entries = dict(wide.instruments.entries)
    entries[("crypto", "BTC")] = dataclasses.replace(entries[("crypto", "BTC")], cls="etp_leveraged")
    wide = dataclasses.replace(wide, instruments=dataclasses.replace(wide.instruments, entries=entries))
    got = P.check_plan(OF.plan(venue="kis", symbol="BTC"), OF.odds_ctx(active=wide))
    assert _t5_code(got) == ("UNSUPPORTED_PRODUCT", "feed"), got           # the section's feed before the class


def test_check_plan_never_raises():
    ctx, huge = OF.odds_ctx(), 10 ** 400                               # no float holds it: math.isfinite raises
    odd = [OF.plan(venue=None), OF.plan(venue=["kis"]), OF.plan(symbol=None), OF.plan(symbol=["BTC"]),
           OF.plan(venue="okx", symbol={"BTC": 1}), OF.plan(edge_source=["none"]), OF.plan(sizing={}),
           OF.plan(bracket=P.Bracket(take_profit=huge, stop=0.05)),
           OF.plan(edge_source="assumed", assumed_p=huge, bracket=P.Bracket(take_profit=0.1, stop=0.05)),
           OF.plan(fraction=P.Fraction(kind="fixed", value=huge)), "plan", 3, object()]
    for p in odd:
        got = P.check_plan(p, ctx)
        assert got is not None and got.code == "UNSUPPORTED_PRODUCT", (p, got)
    assert _t5_code(P.check_plan(OF.plan(), None)) == ("UNSUPPORTED_PRODUCT", "start")


# --------------------------------------------------------------------------- #
# State and limits (Q24 steps 3-4)
# --------------------------------------------------------------------------- #
def test_state_unusable_for_a_hand_built_context_a_broken_owner_or_an_invalid_state():
    p, good = OF.plan(), OF.odds_ctx()
    hand = dataclasses.replace(good)                                  # the same fields, never sealed
    assert not model.is_sealed(hand) and model.is_sealed(good)
    broken = OF.odds_ctx(owner=model.OwnerState.broken("no owner key yet: owner act 1"))
    invalid = OF.odds_ctx(active=model.ApprovedState.invalid("unapproved: no signed approval for rules"))
    for what, ctx in (("hand-built", hand), ("none", None), ("broken owner", broken), ("invalid state", invalid)):
        got = P.check_state(p, ctx)
        assert _t5_code(got) == ("STATE_UNUSABLE", ""), (what, got)
    assert "no owner key yet" in P.check_state(p, broken).detail
    assert "unapproved: no signed approval for rules" in P.check_state(p, invalid).detail
    for unsigned in (F.ctx(code_signed=False), OF.odds_ctx(code_signed=False)):
        got = P.check_state(p, unsigned)
        assert _t5_code(got) == ("STATE_UNUSABLE", "code"), got
    assert _t5_code(P.check_state(p, OF.odds_ctx(code_signed=False, owner=_t5_owner(limits={})))) == (
        "STATE_UNUSABLE", "code")                                      # unsigned code before the limits
    state = good.active                                                # P26: _usable is the gate's _usable
    states = (state, invalid.active, None, dataclasses.replace(state, valid=1),
              dataclasses.replace(state, rules=None), dataclasses.replace(state, instruments=None),
              dataclasses.replace(state, venues=None), types.SimpleNamespace(**vars(state)))
    assert [P._usable(x) for x in states] == [gate._usable(x) for x in states] == [True] + [False] * 7


def test_limits_unset_unless_both_limits_are_signed():
    p = OF.plan()
    for limits in ({"daily_loss_krw": 5_000.0}, {"total_loss_floor_krw": 21_000.0}, {}):
        got = P.check_state(p, OF.odds_ctx(owner=_t5_owner(limits=limits)))
        assert _t5_code(got) == ("LIMITS_UNSET", ""), (limits, got)
    zero = OF.odds_ctx(owner=_t5_owner(limits={"total_loss_floor_krw": 0.0, "daily_loss_krw": 5_000.0}))
    assert P.check_state(p, zero) is None                             # a floor of 0 is a set value


def test_an_okx_leg_needs_the_okx_cap():
    okx, upbit = OF.plan(venue="okx"), OF.plan()
    for caps in ({}, {"okx_equity_share": 0.0}, {"okx_equity_share": 1.5}, {"okx_equity_share": -0.1},
                 {"okx_equity_share": True}, {"okx_equity_share": "0.1"}, {"okx_equity_share": None},
                 {"another_cap": 0.1}):
        ctx = OF.odds_ctx(owner=_t5_owner(caps=caps))
        assert _t5_code(P.check_state(okx, ctx)) == ("LIMITS_UNSET", "cap"), caps
        assert P.check_state(upbit, ctx) is None, caps                # only an OKX leg needs the cap
    for cap in (0.10, 1.0, 1):
        assert P.check_state(okx, OF.odds_ctx(owner=_t5_owner(caps={"okx_equity_share": cap}))) is None, cap
    bare = OF.odds_ctx(owner=_t5_owner(caps={}, limits={}))
    assert _t5_code(P.check_state(okx, bare)) == ("LIMITS_UNSET", "")  # the limits first; no KeyError anywhere
    row = types.SimpleNamespace(cap_key=P.OKX_CAP_KEY)                 # P26: _cap_ok is the gate's _cap rule
    caps = (0.10, 1.0, 1, 1e-300, 0.0, 0, 1.5, 2, -0.1, True, "0.1", None, math.nan, math.inf, 10 ** 400)
    gate_ok = [gate._cap(row, types.SimpleNamespace(owner=types.SimpleNamespace(caps={P.OKX_CAP_KEY: c}))) is not None
               for c in caps]
    assert [P._cap_ok(c) for c in caps] == gate_ok == [True] * 4 + [False] * 11


def test_check_now_needs_an_aware_moment_on_the_context_date():
    ctx = OF.odds_ctx()
    for now in (_T5_NOW, dt.datetime(2026, 10, 22, 15, 0, tzinfo=_T5_UTC),
                dt.datetime(2026, 10, 23, 14, 59, tzinfo=_T5_UTC)):
        assert P.check_now(ctx, now) is None, now
    for now in (dt.datetime(2026, 10, 23, 9, 0), dt.date(2026, 10, 23), None, "2026-10-23T09:00:00+09:00",
                dt.datetime(2026, 10, 23, 15, 0, tzinfo=_T5_UTC),           # 2026-10-24 00:00 in Seoul
                dt.datetime(2026, 10, 22, 14, 59, tzinfo=_T5_UTC),          # 2026-10-22 23:59 in Seoul
                dt.datetime.max.replace(tzinfo=_T5_UTC), dt.datetime.min.replace(tzinfo=_T5_UTC),
                dt.datetime(2026, 10, 23, 9, 0, tzinfo=_T5BadTZ())):          # utcoffset() raises TypeError
        assert _t5_code(P.check_now(ctx, now)) == ("DATA_INVALID", "now"), now


# --------------------------------------------------------------------------- #
# Injected data (Q24 steps 7 and 9; Q8, Q23, Q39)
# --------------------------------------------------------------------------- #
def test_data_invalid_series():
    p, ctx = OF.plan(), OF.odds_ctx()
    good, later = OF.series(n=300), OF.series(n=290)              # 2025-12-27 .. and 2026-01-06 .. 2026-10-22
    dates, opens, closes = good.dates, good.open, good.close
    assert (dates[0], later.dates[1]) == ("2025-12-27", "2026-01-07") and dt.date.fromisoformat("2025-W52-6")
    bad = {"not a series": None, "a look-alike": types.SimpleNamespace(**dataclasses.asdict(good)),
           "lengths differ": _t5_series(open=opens[:-1]),
           "one bar": _t5_series(dates=dates[-1:], open=opens[-1:], close=closes[-1:]),
           "nan close": _t5_series(close=closes[:-1] + (math.nan,)),
           "inf open": _t5_series(open=(math.inf,) + opens[1:]),
           "zero open": _t5_series(open=(0.0,) + opens[1:]),
           "negative close": _t5_series(close=(-1.0,) + closes[1:]),
           "bool price": _t5_series(close=(True,) + closes[1:]),
           "text price": _t5_series(close=("1.0",) + closes[1:]),
           "huge int price": _t5_series(close=(10 ** 400,) + closes[1:]),     # refused, never made a float
           "repeated date": _t5_series(dates=dates[:-1] + (dates[-2],)),
           "dates out of order": _t5_series(dates=(dates[1], dates[0]) + dates[2:]),
           "not ISO": _t5_series(dates=dates[:-1] + ("2026/10/22",)),
           "not a calendar date": _t5_series(dates=dates[:-1] + ("2026-10-32",)),
           # the next three still increase and end before the start, so only the ISO rule refuses them
           "a time in a date": _t5_series(dates=(dates[0] + "T00",) + dates[1:]),
           "day 00": _t5_series(dates=(dates[0][:8] + "00",) + dates[1:]),
           "an ISO week date": _t5_series(later, dates=("2025-W52-6",) + later.dates[1:]),
           "a bar on the start": _t5_series(dates=dates[1:] + ("2026-10-23",)),
           "md5 differs": _t5_series(md5="0" * 32),
           "md5 of other fields": dataclasses.replace(good, source="BINANCE")}
    for what, s in bad.items():
        got = P.check_data(p, ctx, _t5_inputs(s), "CRYPTO")
        assert _t5_code(got) == ("DATA_INVALID", "series"), (what, got)
    assert P.check_data(p, ctx, _t5_inputs(good), "CRYPTO") is None
    assert P.check_data(p, ctx, _t5_inputs(OF.series(n=2)), "CRYPTO") is None          # two bars are enough here
    numbers = (1.0, 1, 0, -2, 0.0, 2 ** 63 - 1, 2 ** 63, -(2 ** 63), 10 ** 400, math.nan, math.inf, -math.inf, True,
               False, "1.0", None)                                     # P26: _real is the gate's _number rule
    assert [P._real(x) for x in numbers] == [gate._number(x) for x in numbers] == [True] * 6 + [False] * 10


def test_data_invalid_stale_after_three_crypto_and_fourteen_krx_or_us_days():
    ctx = OF.odds_ctx()
    crypto, krx, us = OF.plan(), OF.plan(venue="kis", symbol="005930"), OF.plan(venue="kis", symbol="AAPL")
    for last, want in (("2026-10-20", None), ("2026-10-19", ("DATA_INVALID", "stale"))):
        got = P.check_data(crypto, ctx, _t5_inputs(_t5_ending(last)), "CRYPTO")
        assert _t5_code(got) == want, (last, got)
    assert P.check_data(crypto, ctx, _t5_inputs(_t5_ending("2026-10-19")), "CRYPTO").slots == {"days": "3"}
    for last, want in (("2026-10-09", None), ("2026-10-08", ("DATA_INVALID", "stale"))):
        got = P.check_data(krx, ctx, _t5_krx(_t5_ending(last, **_T5_KIS)), "KR")
        assert _t5_code(got) == want, (last, got)
        got = P.check_data(us, ctx, _t5_us(_t5_ending(last, **_T5_YAHOO)), "US")
        assert _t5_code(got) == want, (last, got)
    assert P.check_data(krx, ctx, _t5_krx(_t5_ending("2026-10-08", **_T5_KIS)), "KR").slots == {"days": "14"}


def test_data_invalid_sessions_and_empty():
    ctx, s = OF.odds_ctx(), OF.series(n=300)
    crypto, krx, us = OF.plan(), OF.plan(venue="kis", symbol="005930"), OF.plan(venue="kis", symbol="AAPL")
    days = _t5_days(_T5_START, 10)                                     # 2026-10-23 .. 2026-11-01
    crypto_bad = {"out of order": days[::-1], "repeated": days[:2] + days[1:2], "not ISO": ("2026/10/23",),
                  "before the start": ("2026-10-22",) + days, "at start + horizon": days + ("2026-11-02",),
                  "not text": (_T5_START,)}
    for what, sessions in crypto_bad.items():
        got = P.check_data(crypto, ctx, _t5_inputs(s, sessions=sessions), "CRYPTO")
        assert _t5_code(got) == ("DATA_INVALID", "sessions"), (what, got)
    for what, changes in {"crypto with limits": {"price_limits": (0.3,) * 10},
                          "crypto with a calendar sha": {"calendar_sha256": _T5_SHA}}.items():
        got = P.check_data(crypto, ctx, _t5_inputs(s, **changes), "CRYPTO")
        assert _t5_code(got) == ("DATA_INVALID", "sessions"), (what, got)
    for what, changes in {"limits short": {"price_limits": (0.3,) * 3}, "limit 0": {"price_limits": (0.0,) * 4},
                          "limit 1": {"price_limits": (0.3, 0.3, 0.3, 1.0)},
                          "limit nan": {"price_limits": (0.3, math.nan, 0.3, 0.3)},
                          "limit bool": {"price_limits": (True, 0.3, 0.3, 0.3)},
                          "no sha": {"calendar_sha256": ""}, "upper-case sha": {"calendar_sha256": "A" * 64},
                          "short sha": {"calendar_sha256": "a" * 63}}.items():
        got = P.check_data(krx, ctx, _t5_krx(**changes), "KR")
        assert _t5_code(got) == ("DATA_INVALID", "sessions"), (what, got)
    for what, changes in {"US limits": {"price_limits": (0.3, 0.3)}, "US no sha": {"calendar_sha256": ""}}.items():
        got = P.check_data(us, ctx, _t5_us(**changes), "US")
        assert _t5_code(got) == ("DATA_INVALID", "sessions"), (what, got)
    assert P.check_data(krx, ctx, _t5_krx(), "KR") is None and P.check_data(us, ctx, _t5_us(), "US") is None
    assert P.check_data(crypto, ctx, _t5_inputs(s, sessions=days[3:5]), "CRYPTO") is None
    for market, p, inputs in (("CRYPTO", crypto, _t5_inputs(s, sessions=())),
                              ("KR", krx, _t5_krx(sessions=(), price_limits=())),
                              ("US", us, _t5_us(sessions=()))):
        got = P.check_data(p, ctx, inputs, market)
        assert _t5_code(got) == ("DATA_INVALID", "empty"), (market, got)
    stale = _t5_inputs(_t5_ending("2026-10-19"), sessions=("2026/10/23",))
    assert _t5_code(P.check_data(crypto, ctx, stale, "CRYPTO")) == ("DATA_INVALID", "stale")      # stale first,
    no_sha = _t5_krx(sessions=(), price_limits=(), calendar_sha256="")
    assert _t5_code(P.check_data(krx, ctx, no_sha, "KR")) == ("DATA_INVALID", "sessions")         # then sessions


def test_synthetic_series_are_refused_after_the_data_checks():
    p, ctx = OF.plan(), OF.odds_ctx()
    for change in ({"status": "SYNTHETIC"}, {"source": "SYNTHETIC"}):
        got = P.check_data(p, ctx, _t5_inputs(_t5_series(**change)), "CRYPTO")
        assert _t5_code(got) == ("SYNTHETIC_REFUSED", ""), (change, got)
    stale = _t5_series(_t5_ending("2026-10-19"), status="SYNTHETIC")
    assert _t5_code(P.check_data(p, ctx, _t5_inputs(stale), "CRYPTO")) == ("DATA_INVALID", "stale")


def test_special_regime_below_sixty_krx_bars():
    krx = OF.plan(venue="kis", symbol="005930")
    got = P.check_history(krx, _t5_krx(OF.series(n=59, **_T5_KIS)), "KR")
    assert _t5_code(got) == ("SPECIAL_REGIME", "") and got.slots == {"symbol": "005930"}, got
    assert _t5_code(P.check_history(krx, _t5_krx(OF.series(n=60, **_T5_KIS)), "KR")) == ("SHORT_HISTORY", "")
    assert _t5_code(P.check_history(OF.plan(), _t5_inputs(OF.series(n=59)), "CRYPTO")) == ("SHORT_HISTORY", "")
    assert _t5_code(P.check_history(OF.plan(venue="kis", symbol="AAPL"), _t5_us(OF.series(n=59, **_T5_YAHOO)),
                                    "US")) == ("SHORT_HISTORY", "")


def test_short_history_below_250_bars_before_the_start():
    for market, p, kwargs, make in (("CRYPTO", OF.plan(), {}, _t5_inputs),
                                    ("KR", OF.plan(venue="kis", symbol="005930"), _T5_KIS, _t5_krx),
                                    ("US", OF.plan(venue="kis", symbol="AAPL"), _T5_YAHOO, _t5_us)):
        got = P.check_history(p, make(OF.series(n=249, **kwargs)), market)
        assert _t5_code(got) == ("SHORT_HISTORY", "") and got.slots == {"symbol": p.leg.symbol}, (market, got)
        assert P.check_history(p, make(OF.series(n=250, **kwargs)), market) is None, market
    on_start = _t5_ending("2026-10-23", n=250)                          # 249 bars before the start, one on it
    assert _t5_code(P.check_history(OF.plan(), _t5_inputs(on_start), "CRYPTO")) == ("SHORT_HISTORY", "")


# --------------------------------------------------------------------------- #
# Hashes (spec 7.2 "Data rules"; 8.o 8)
# --------------------------------------------------------------------------- #
def test_series_md5_is_the_md5_of_the_canonical_json():
    body = {"symbol": "KRW-BTC", "source": "UPBIT", "dates": ["2026-10-21", "2026-10-22"],
            "open": [50_000_000.0, 50_100_000.5], "close": [50_100_000.5, 49_900_000.25], "adjustment": "",
            "status": "final"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    assert text.startswith('{"adjustment":"","close":[50100000.5,49900000.25],"dates":["2026-10-21",')
    want = hashlib.md5(text.encode("utf-8")).hexdigest()
    got = P.series_md5("KRW-BTC", "UPBIT", ("2026-10-21", "2026-10-22"), (50_000_000.0, 50_100_000.5),
                       (50_100_000.5, 49_900_000.25), "", "final")
    assert got == want
    assert P.series_md5("KRW-BTC", "UPBIT", ["2026-10-21", "2026-10-22"], [50_000_000.0, 50_100_000.5],
                        [50_100_000.5, 49_900_000.25], "", "final") == want            # lists hash like tuples
    assert P.series_md5("KRW-BTC", "UPBIT", ("2026-10-21", "2026-10-22"), (50_000_000.0, 50_100_000.5),
                        (50_100_000.5, 49_900_000.25), "", "SYNTHETIC") != want


def test_plan_hash_ignores_the_name_and_nothing_else():
    a = OF.plan(name="first")
    assert P.plan_hash(a) == P.plan_hash(OF.plan(name="a quite different name")) == P.plan_hash(OF.plan(name=""))
    assert P.plan_hash(a) == model.sha256_hex(model.canonical_json(dataclasses.replace(a, name="")))
    assert len(P.plan_hash(a)) == 64 and set(P.plan_hash(a)) <= set("0123456789abcdef")
    others = [OF.plan(stake_krw=42_001.0), OF.plan(target_krw=42_000_001.0), OF.plan(fx_krw_per_usd=1_401.0),
              OF.plan(track="moonshot"), OF.plan(horizon_days=11), OF.plan(symbol="USDT"), OF.plan(model="garch_t"),
              OF.plan(fraction=P.fixed(0.5)), OF.plan(bracket=P.Bracket(take_profit=0.1, stop=0.05)),
              OF.plan(start=dt.date(2026, 10, 24))]
    hashes = {P.plan_hash(x) for x in others}
    assert len(hashes) == len(others) and P.plan_hash(a) not in hashes
