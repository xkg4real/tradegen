"""Universe windows of the fixed driver and LiveHistory (spec section 12): invented books, flag and ticker reads,
snapshots and account anchors over a temporary state root and head root; no network, credentials or real home."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import hashlib
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from core.compliance.model import Universe
from execution_accounts.collector import SourceReceipt
from execution_accounts.model import Position
from execution_accounts.quotes import parse_orderbook, to_runner_quote
from execution_accounts.universe import FlagRead, TickerRead
from execution_control.controller import AccountObservation
from execution_control.risk import RiskObservation
from execution_control.store import GENESIS, MAX_ROW_BYTES, _utc
from execution_launch.baseline_head import BaselineHead
from execution_launch.driver import ChooserInputs, UniverseBar, chooser_decision, describe_fixed_driver
from execution_launch.live_history import SIZE_FALLBACK, SlotUniverse
from execution_launch.profile import profile_contract_digest, rule_terms_digest
from execution_launch.program import ChooserState, ProgramSpec, program_digest
from execution_launch.runner import DecisionInput
from execution_launch.strategy import UNIVERSE_EVALUATOR_REVISION, evidence_digest
from tests import launch_driver as LD
from tests import launch_live_history as LH
from tests.launch_baseline_head import head_root

D = Decimal
RULE = hashlib.sha256(b"fixture-universe-rule").hexdigest()
BTC, ETH, XRP = "KRW-BTC", "KRW-ETH", "KRW-XRP"


def universe_env():
    """LD.fixture() as a universe deployment: the rotation program (L=1, m=1, margin 0, N=2), an IOC profile with
    the rule, and a protocol whose symbol stays the benchmark KRW-BTC."""
    e = LD.fixture()
    program = ProgramSpec(schema_version=2, strategy_id=e.program.strategy_id, kind="universe_top1_momentum",
                          fast_window=0, slow_window=0, exposure_fraction=D("0.5"), lookback_slots=1,
                          min_hold_slots=1, switch_margin=D(0), max_candidates=2, universe_rule_sha256=RULE)
    code = program_digest(program, e.artifact)
    profile = replace(e.profile, strategy_code_sha256=code, time_in_force="ioc", universe_rule_sha256=RULE)
    protocol = replace(e.protocol, strategy_code_sha256=code, evaluator_revision=UNIVERSE_EVALUATOR_REVISION,
                       universe_rule_sha256=RULE, profile_contract_digest=profile_contract_digest(profile),
                       rule_terms_digest=rule_terms_digest(profile.instrument_rules, universe_rule_sha256=RULE))
    return SimpleNamespace(program=program, protocol=protocol, profile=profile, artifact=e.artifact,
                           window=replace(e.window, deployment_id="invented-universe-deployment"),
                           provider=e.provider, verifier=e.verifier)


def inputs(**changes):
    """The inputs of a decision with BTC held for two decisions and ETH well ahead over one slot."""
    values = dict(held=BTC, hold_count=2, top_n=(BTC, ETH), flags=((BTC, "unflagged"), (ETH, "unflagged")),
                  prices=((BTC, D(122)), (ETH, D(130))), lag_prices=((BTC, D(121)), (ETH, D(106))))
    return ChooserInputs(**(values | changes))


def test_chooser_decision_recomputes_one_decision_from_its_inputs():
    program = universe_env().program
    assert chooser_decision(program, inputs()) == (ETH, ChooserState(held=ETH, hold_count=1))
    assert chooser_decision(program, inputs(held=None, hold_count=0, lag_prices=None)) == (
        None, ChooserState(held=None, hold_count=1))
    assert chooser_decision(program, inputs(flags=((BTC, "warning"), (ETH, "unflagged")))) == (
        None, ChooserState(held=None, hold_count=1))
    for bad in (None, {"held": BTC}, inputs(top_n=[BTC, ETH]), inputs(flags=((BTC,),)),
                inputs(prices=((BTC, 122),)), inputs(top_n=(BTC, ETH, XRP))):
        LH.refused(lambda: chooser_decision(program, bad), "FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED")


NAME = "universe-history"
# Under universe_env's program and the top-2 (BTC, ETH) these give the decisions cash, BTC, BTC, ETH, ETH, ETH.
SWITCH = ({BTC: D(100), ETH: D(100), XRP: D(100)}, {BTC: D(110), ETH: D(105), XRP: D(200)},
          {BTC: D(121), ETH: D(106), XRP: D(200)}, {BTC: D(122), ETH: D(130), XRP: D(200)},
          {BTC: D(122), ETH: D(131), XRP: D(200)}, {BTC: D(122), ETH: D(132), XRP: D(200)})
ALL_UNFLAGGED = ((BTC, "unflagged"), (ETH, "unflagged"), (XRP, "unflagged"))


def pairs(prices):
    return tuple(sorted(prices.items()))


def snapshot(env, listed=(BTC, ETH, XRP)):
    """An invented snapshot in force over the whole window; its top-2 is (BTC, ETH)."""
    start = env.window.start
    return Universe(day=start.date(), rule_sha256=RULE, snapshot_sha256="e" * 64, built_at=start - timedelta(hours=1),
                    valid_from=start - timedelta(hours=1), valid_until=start + timedelta(days=1),
                    listed=tuple(sorted(listed)), eligible=((BTC, D(3000)), (ETH, D(2000))))


def reads(env, i, prices, *, snap=None, flags=None, allow=frozenset({BTC, ETH})):
    """Slot i's universe inputs: the window's snapshot, every priced market unflagged unless `flags` says
    otherwise, each trade 2 s before the slot, invented raw-body digests."""
    slot = env.T(i)
    return SlotUniverse(snapshot=snapshot(env) if snap is None else snap,
                        flags=FlagRead(ok=True, received_at=slot, sha256="1" * 64,
                                       flags={market: "unflagged" for market in prices} | (flags or {})),
                        tickers=TickerRead(ok=True, received_at=slot, sha256="2" * 64,
                                           prices={market: (price, slot - LH.seconds(2))
                                                   for market, price in prices.items()}),
                        allow=allow, reasons=(), events=())


def down(env, i):
    """Slot i with every universe read unavailable: no snapshot, failed flag and ticker reads, nothing allowed."""
    return SlotUniverse(snapshot=None, flags=FlagRead(ok=False, received_at=None, sha256=None, flags={}),
                        tickers=TickerRead(ok=False, received_at=None, sha256=None, prices={}),
                        allow=frozenset(), reasons=("UNIVERSE_NO_SNAPSHOT",), events=())


def book(env, i, symbol=BTC, bid=None, ask=None):
    """LH.book_at's invented single-level book for any coin and price; the body text keeps exact decimals."""
    slot, when = env.T(i), env.T(i) - LH.seconds(1)
    bid, ask = (D(100 + i) if bid is None else bid), (D(102 + i) if ask is None else ask)
    raw = ('[{"market": "%s", "level": 0, "timestamp": %d, "total_ask_size": 3, "total_bid_size": 4, '
           '"orderbook_units": [{"ask_price": %s, "bid_price": %s, "ask_size": 3, "bid_size": 4}]}]'
           % (symbol, LH.ms(slot - LH.seconds(2)), ask, bid)).encode()
    receipt = SourceReceipt(path="/v1/orderbook", params=(("markets", symbol), ("level", "0"), ("count", "30")),
                            account_scope="public-upbit-orderbook", received_at=when, server_time=when,
                            raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())
    return parse_orderbook(receipt, symbol=symbol, now=when)


def account(env, i, *, cash=D(10000), holdings=None):
    """The account 1 s before slot i: settled cash and `holdings` (coin to units), each unit worth 101 KRW."""
    profile, asof, held = env.profile, env.T(i) - LH.seconds(1), holdings or {}
    key = (profile.venue, profile.account_scope)
    inventory = sum((units * D(101) for units in held.values()), D(0))
    equity = cash + inventory
    return AccountObservation(positions=M.Positions(equity_krw=float(equity), holdings={}, exposure={}),
        account_scopes={profile.venue: profile.account_scope}, settled_cash_krw={key: cash},
        holdings={(*key, profile.market, coin): units for coin, units in held.items()},
        held_exposure_krw={key: equity}, inventory_exposure_krw={key: inventory},
        quote_currency_by_account={key: "KRW"}, quote_rates_krw={(*key, "KRW"): D(1)},
        risk=RiskObservation(equity=equity, prior_high_watermark=equity, day_start_equity=equity,
            current_day_realized_net_profit=D(0), prior_day_realized_net_profit=D(10),
            observed_daily_loss=D(0), approved_effective_floor=None, is_first_trading_day=False, asof=asof),
        asof=asof, server_time=asof, no_credit=True)


def ubuild(hroot, name=NAME, end=None):
    """A bound universe LiveHistory and its fixed driver over the temporary roots (LH.build's shape); `end`
    shortens the window to that many minutes after its start."""
    e = universe_env()
    if end is not None:
        e.window = replace(e.window, end=e.window.start + timedelta(minutes=end))
    start = e.window.start
    env = SimpleNamespace(e=e, profile=e.profile, window=e.window, hroot=hroot, name=name, start=start,
                          c=[start - timedelta(minutes=5)], T=lambda i: start + timedelta(minutes=i))
    env.clock = lambda: env.c[0]
    env.head = BaselineHead(root=hroot, name=name, chain=LH.chain_for(env))
    env.head.initialize_reviewed_head(GENESIS)
    LH.attach(env)
    env.identity = env.h.bind(env.d)
    return env


def record(env, i, prices, *, symbol=BTC, booked=True, tick=D(1), bid=None, ask=None, cash=D(10000),
           holdings=None, positions=(), slot_universe=None):
    """Record slot i at slot + 1 s: `symbol`'s book (or none), the account and the slot's universe inputs."""
    env.c[0] = env.T(i) + LH.seconds(1)
    return env.h.record_slot(book(env, i, symbol, bid, ask) if booked else None,
                             account(env, i, cash=cash, holdings=holdings), trade_symbol=symbol,
                             universe=reads(env, i, prices) if slot_universe is None else slot_universe,
                             tick_size=tick, positions=positions)


def tick(env, i, *, symbol=BTC, tick_size=D(1), bid=None, ask=None, cash=D(10000), holdings=None, driver=None):
    """One driver tick at slot i + 2 s, with the profile renewed to `symbol` at `tick_size` (only fields the
    universe contract digest leaves out change) and the quote of the book `record` used."""
    now = env.T(i) + LH.seconds(2)
    env.c[0] = now
    driver = driver or env.d
    rules = replace(env.profile.instrument_rules, symbol=symbol, tick_size=tick_size)
    observation = DecisionInput(now=now, profile=replace(env.profile, symbol=symbol, instrument_rules=rules),
                                quote=to_runner_quote(book(env, i, symbol, bid, ask), now=now),
                                account=account(env, i, cash=cash, holdings=holdings))
    return driver.callback(observation, driver.parameters_json)


def substitute(env, frame):
    """Another issued driver of the same universe deployment, handed `frame` and the fixture's invented
    authentication, so only the driver's own frame checks can refuse."""
    return LD.construct(env.e, window=env.window, history_provider=lambda observation: frame,
                        history_verifier=LD.invented_authentication)


def test_universe_driver_construction_pins_benchmark_symbol_ioc_and_rule():
    e = universe_env()
    assert describe_fixed_driver(LD.construct(e)).profile_contract_digest == e.protocol.profile_contract_digest
    for changes in ({"time_in_force": "gtc"}, {"symbol": ETH}, {"universe_rule_sha256": "c" * 64}):
        changed = SimpleNamespace(**(vars(e) | {"profile": replace(e.profile, **changes)}))
        LD.reject(lambda: LD.construct(changed), "FIXED_DRIVER_SCOPE_MISMATCH")
    fixed = LD.fixture()
    changed = SimpleNamespace(**(vars(fixed) | {"profile": replace(fixed.profile, time_in_force="ioc")}))
    LD.reject(lambda: LD.construct(changed), "FIXED_DRIVER_SCOPE_MISMATCH")


def test_universe_slots_require_their_inputs_and_a_book_of_the_coin_at_its_tick():
    with head_root() as hroot:
        env = ubuild(hroot)
        env.c[0] = env.T(0) + LH.seconds(1)
        acct, slot = account(env, 0), reads(env, 0, SWITCH[0])
        for options in ({}, {"trade_symbol": BTC, "tick_size": D(1)}, {"universe": slot, "tick_size": D(1)},
                        {"trade_symbol": "BTC", "universe": slot, "tick_size": D(1)},
                        {"trade_symbol": BTC, "universe": slot, "tick_size": D(0)},
                        {"trade_symbol": BTC, "universe": slot, "tick_size": D(1), "positions": [()]},
                        {"trade_symbol": BTC, "universe": replace(slot, allow=[BTC]), "tick_size": D(1)}):
            LH.refused(lambda: env.h.record_slot(book(env, 0), acct, **options), "HISTORY_INPUT_REQUIRED")
        options = {"trade_symbol": BTC, "universe": slot, "tick_size": D(1)}
        LH.refused(lambda: env.h.record_slot(book(env, 0, ETH), acct, **options), "HISTORY_BOOK_MARKET_MISMATCH")
        LH.refused(lambda: env.h.record_slot(book(env, 0, BTC, D("100.5"), D(102)), acct, **options),
                   "HISTORY_BOOK_OFF_TICK")
        assert len(LH.rows(env)) == 1 and env.h.recorded_allow is None
        env.h.record_slot(None, acct, **options)
        assert LH.rows(env)[1]["data"]["receipt"] == "unavailable"
        assert env.h.recorded_allow == frozenset({BTC, ETH})


def test_history_row_v2_records_the_slot_universe_and_frames_carry_it():
    with head_root() as hroot:
        env = ubuild(hroot)
        stamp = env.T(1) - LH.seconds(3)
        positions = (Position(market="spot", symbol=ETH, base_currency="ETH", quote_currency="KRW", units=D(2),
                              price=D(105), asof=stamp),
                     Position(market="spot", symbol="KRW-OLD", base_currency="OLD", quote_currency="KRW",
                              units=D(7), price=D(0), asof=stamp, unlisted=True))
        record(env, 0, SWITCH[0])
        record(env, 1, SWITCH[1], symbol=ETH, holdings={ETH: D(2)}, positions=positions)
        record(env, 2, SWITCH[2], slot_universe=reads(env, 2, SWITCH[2], flags={XRP: "caution"}))
        record(env, 3, SWITCH[3], booked=False)
        assert env.h.recorded_allow == frozenset({BTC, ETH})
        record(env, 4, SWITCH[4], slot_universe=down(env, 4))
        data = [row["data"] for row in LH.rows(env)[1:]]
        assert all(set(item) == {"index", "trade_symbol", "tick_size", "receipt", "anchor", "holdings", "universe",
                                 "decision"} for item in data)
        assert [item["trade_symbol"] for item in data] == [BTC, ETH, BTC, BTC, BTC]
        assert data[1]["tick_size"] == "1" and data[1]["receipt"]["sha256"] == book(env, 1, ETH).receipt.sha256
        assert data[1]["anchor"] == {"cash_quote": "10000", "units": "2", "account_asof": _utc(env.T(1) - LH.seconds(1))}
        assert data[1]["holdings"] == [[ETH, "2", "105", _utc(stamp), False, False],
                                       ["KRW-OLD", "7", "0", _utc(stamp), True, True]]
        assert data[1]["universe"] == {
            "snapshot": {"day": env.window.start.date().isoformat(), "sha256": "e" * 64, "top_n": [BTC, ETH]},
            "flags": {"sha256": "1" * 64, "exceptions": []},
            "tickers": {"sha256": "2" * 64,
                        "prices": [[BTC, "110", -2000], [ETH, "105", -2000], [XRP, "200", -2000]]},
            "allow": [BTC, ETH], "reasons": [], "events": []}
        assert [item["decision"] for item in data] == [
            {"coin": None, "target_fraction": "0", "held": None, "hold_count": 1},
            {"coin": BTC, "target_fraction": "0.5", "held": BTC, "hold_count": 1},
            {"coin": BTC, "target_fraction": "0.5", "held": BTC, "hold_count": 2},
            {"coin": ETH, "target_fraction": "0.5", "held": ETH, "hold_count": 1},
            {"coin": ETH, "target_fraction": "0.5", "held": ETH, "hold_count": 2}]
        assert data[2]["universe"]["flags"]["exceptions"] == [[XRP, "caution"]]
        assert data[3]["receipt"] == "unavailable"
        assert data[4]["universe"] == {"snapshot": "unavailable", "flags": "unavailable", "tickers": "unavailable",
                                       "allow": [], "reasons": ["UNIVERSE_NO_SNAPSHOT"], "events": []}
        assert env.h.recorded_allow == frozenset()
        frame = env.h.provider(LH.obs(env, env.T(4) + LH.seconds(2)))
        assert frame.universe_sha256 == evidence_digest(data[4]["universe"])
        assert frame.bars[3] == UniverseBar(observed_at=env.T(3), received_at=env.T(3) + LH.seconds(1), symbol=BTC,
                                            tick_size=D(1), bid=None, ask=None, mark=None, source_sha256=None)
        assert (frame.bars[1].symbol, frame.bars[1].bid, frame.bars[1].ask) == (ETH, D(101), D(103))
        assert frame.chooser_inputs == ChooserInputs(held=BTC, hold_count=2, top_n=(BTC, ETH), flags=ALL_UNFLAGGED,
                                                     prices=pairs(SWITCH[3]), lag_prices=pairs(SWITCH[2]))


def test_oversized_row_drops_flag_and_ticker_parts_and_allows_no_buys():
    with head_root() as hroot:
        env = ubuild(hroot)
        extra = tuple("KRW-X%05d" % n for n in range(8000))
        prices = {market: D("1234567.12345678") for market in extra} | SWITCH[0]
        snap = snapshot(env, listed=(BTC, ETH, XRP) + extra)
        record(env, 0, prices, slot_universe=reads(env, 0, prices, snap=snap))
        assert len(LH.journal(env).read_bytes().splitlines()[1]) < MAX_ROW_BYTES
        assert LH.rows(env)[1]["data"]["universe"] == {
            "snapshot": {"day": env.window.start.date().isoformat(), "sha256": "e" * 64, "top_n": [BTC, ETH]},
            "flags": "unavailable", "tickers": "unavailable", "allow": [], "reasons": [SIZE_FALLBACK], "events": []}
        assert env.h.recorded_allow == frozenset()
        record(env, 1, SWITCH[1])
        assert LH.rows(env)[2]["data"]["universe"]["tickers"]["prices"][0] == [BTC, "110", -2000]
        assert env.h.recorded_allow == frozenset({BTC, ETH})
