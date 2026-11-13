"""Universe windows of the fixed driver and LiveHistory (spec section 12): invented books, flag and ticker reads,
snapshots and account anchors over a temporary state root and head root; no network, credentials or real home."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from core.isolation import state_root
from core.compliance.model import Universe
from execution_accounts.collector import SourceReceipt
from execution_accounts.model import Position
from execution_accounts.quotes import parse_orderbook, to_runner_quote
from execution_accounts.universe import FlagRead, TickerRead
from execution_control.controller import AccountObservation
from execution_control.risk import RiskObservation
from execution_control.capability import digest
from execution_control.store import GENESIS, MAX_ROW_BYTES, _canonical, _utc
from execution_launch.baseline_head import BaselineHead
from execution_launch.driver import ChooserInputs, UniverseBar, chooser_decision, describe_fixed_driver
from execution_launch.live_history import SIZE_FALLBACK, HistoryChain, LiveHistory, SlotUniverse
from execution_launch.evidence_objects import EvidenceObjectStore, ObjectLimits, PayloadReference
from execution_launch.history_storage import (HistoryStoragePolicy, SlotContext, decode_slot_payload, policy_digest)
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


def policy(**changes):
    """Explicit synthetic window budgets, never owner operating defaults."""
    values = dict(schema_version=1, history_version=3,
                  object_limits=ObjectLimits(chunk_bytes=65536, max_payload_bytes=2 * 1024 * 1024,
                                             max_chunks=32, max_manifest_bytes=65536),
                  max_window_bytes=128 * 1024 * 1024, max_window_objects=8192,
                  max_journal_bytes=64 * 1024 * 1024)
    return HistoryStoragePolicy(**(values | changes))


def universe_env(storage_policy=None):
    """LD.fixture() as a universe deployment: the rotation program (L=1, m=1, margin 0, N=2), an IOC profile with
    the rule, and a protocol whose symbol stays the benchmark KRW-BTC."""
    e = LD.fixture()
    storage_policy = policy() if storage_policy is None else storage_policy
    program = ProgramSpec(schema_version=2, strategy_id=e.program.strategy_id, kind="universe_top1_momentum",
                          fast_window=0, slow_window=0, exposure_fraction=D("0.5"), lookback_slots=1,
                          min_hold_slots=1, switch_margin=D(0), max_candidates=2, universe_rule_sha256=RULE)
    code = program_digest(program, e.artifact)
    profile = replace(e.profile, strategy_code_sha256=code, time_in_force="ioc", universe_rule_sha256=RULE)
    protocol = replace(e.protocol, strategy_code_sha256=code, evaluator_revision=UNIVERSE_EVALUATOR_REVISION,
                       universe_rule_sha256=RULE, history_storage_sha256=policy_digest(storage_policy),
                       profile_contract_digest=profile_contract_digest(profile),
                       rule_terms_digest=rule_terms_digest(profile.instrument_rules, universe_rule_sha256=RULE))
    return SimpleNamespace(program=program, protocol=protocol, profile=profile, artifact=e.artifact,
                           window=replace(e.window, deployment_id="invented-universe-deployment"),
                           provider=e.provider, verifier=e.verifier, storage_policy=storage_policy)


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


def chain_for(env):
    return HistoryChain(root=state_root().absolute(), window=env.window, storage_policy=env.storage_policy)


def attach(env, **changes):
    """Use one explicitly bound policy at the chain, history and protocol boundaries."""
    env.h = LiveHistory(env.e.program, env.e.protocol, env.e.profile, window=env.window,
                        root=state_root().absolute(), clock=lambda: env.clock(), trusted_head=env.head,
                        storage_policy=env.storage_policy)
    env.d = LD.construct(env.e, window=env.window, history_provider=env.h.provider,
                         history_verifier=env.h.verifier, **changes)


def restart(env):
    env.head = BaselineHead(root=env.hroot, name=env.name, chain=chain_for(env))
    attach(env)
    env.identity = env.h.bind(env.d)
    return env.identity


def observed(env, now):
    """Deliver an ordinary provider observation at its actual fake-clock time; never backdate the clock."""
    assert now >= env.c[0]
    env.c[0] = now
    return LH.obs(env, now)


def objects(env):
    return EvidenceObjectStore(root=LH.directory(env.window) / "payload-objects",
                               limits=env.storage_policy.object_limits)


def payload(env, row):
    return objects(env).read(PayloadReference(**row["data"]["payload_ref"]))


def logical_rows(env):
    """Resolve real v3 references; retain each outer row's metadata, replacing only data for logical assertions."""
    result = []
    for row in LH.rows(env):
        if row["kind"] == "slot":
            data = row["data"]
            assert set(data) == {"history_version", "index", "payload_ref"} and data["history_version"] == 3
            context = SlotContext(window_digest=digest(env.window), driver_identity_digest=digest(env.identity),
                                  index=data["index"], sampled_at=datetime.fromisoformat(row["utc"]))
            row = dict(row, data=decode_slot_payload(payload(env, row), context=context, policy=env.storage_policy))
        result.append(row)
    return result


def rewrite_slot(env, seq, change):
    """Forge only synthetic payload+row hashes; the independent head is deliberately never advanced."""
    row = LH.rows(env)[seq - 1]
    wrapper = json.loads(payload(env, row))
    change(wrapper["slot"])
    # Deliberately bypass the slot encoder: malformed inner data must reach the real replay validation boundary.
    reference = objects(env).stage(_canonical(wrapper))
    LH.rewrite(env, seq, lambda item: item["data"].update(payload_ref=asdict(reference)), rehash=True)


def ubuild(hroot, name=NAME, end=None, *, storage_policy=None, bind=True):
    """A bound universe LiveHistory and its fixed driver over the temporary roots (LH.build's shape); `end`
    shortens the window to that many minutes after its start."""
    e = universe_env(storage_policy)
    if end is not None:
        e.window = replace(e.window, end=e.window.start + timedelta(minutes=end))
    start = e.window.start
    env = SimpleNamespace(e=e, profile=e.profile, window=e.window, hroot=hroot, name=name, start=start,
                          storage_policy=e.storage_policy,
                          c=[start - timedelta(minutes=5)], T=lambda i: start + timedelta(minutes=i))
    env.clock = lambda: env.c[0]
    env.head = BaselineHead(root=hroot, name=name, chain=chain_for(env))
    env.head.initialize_reviewed_head(GENESIS)
    attach(env)
    if bind:
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
        assert len(logical_rows(env)) == 1 and env.h.recorded_allow is None
        env.h.record_slot(None, acct, **options)
        assert logical_rows(env)[1]["data"]["receipt"] == "unavailable"
        assert env.h.recorded_allow == frozenset({BTC, ETH})


def test_history_row_v2_records_the_slot_universe_and_frames_carry_it():
    """The complete legacy logical slot is retained inside v3, with independently authenticated small references."""
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
        actual = LH.rows(env)
        assert set(actual[0]["data"]) == {"identity", "history_version", "history_storage"}
        assert actual[0]["data"]["history_version"] == 3
        assert all(set(row["data"]) == {"history_version", "index", "payload_ref"} for row in actual[1:])
        data = [row["data"] for row in logical_rows(env)[1:]]
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
        frame = env.h.provider(observed(env, env.T(4) + LH.seconds(2)))
        assert frame.universe_sha256 == evidence_digest(data[4]["universe"])
        assert frame.bars[3] == UniverseBar(observed_at=env.T(3), received_at=env.T(3) + LH.seconds(1), symbol=BTC,
                                            tick_size=D(1), bid=None, ask=None, mark=None, source_sha256=None)
        assert (frame.bars[1].symbol, frame.bars[1].bid, frame.bars[1].ask) == (ETH, D(101), D(103))
        assert frame.chooser_inputs == ChooserInputs(held=BTC, hold_count=2, top_n=(BTC, ETH), flags=ALL_UNFLAGGED,
                                                     prices=pairs(SWITCH[3]), lag_prices=pairs(SWITCH[2]))


def test_oversized_logical_row_preserves_valid_flags_tickers_allow_and_book():
    with head_root() as hroot:
        env = ubuild(hroot)
        extra = tuple("KRW-X%05d" % n for n in range(8000))
        prices = {market: D("1234567.12345678") for market in extra} | SWITCH[0]
        snap = snapshot(env, listed=(BTC, ETH, XRP) + extra)
        record(env, 0, prices, slot_universe=reads(env, 0, prices, snap=snap))
        assert len(LH.journal(env).read_bytes().splitlines(keepends=True)[1]) <= MAX_ROW_BYTES
        stored = logical_rows(env)[1]["data"]
        assert len(_canonical(stored)) > MAX_ROW_BYTES
        assert stored["receipt"]["sha256"] == book(env, 0).receipt.sha256
        assert stored["universe"] == {
            "snapshot": {"day": env.window.start.date().isoformat(), "sha256": "e" * 64, "top_n": [BTC, ETH]},
            "flags": {"sha256": "1" * 64, "exceptions": []},
            "tickers": {"sha256": "2" * 64,
                        "prices": [[market, format(price, "f"), -2000] for market, price in sorted(prices.items())]},
            "allow": [BTC, ETH], "reasons": [], "events": []}
        assert SIZE_FALLBACK not in stored["universe"]["reasons"]
        assert env.h.recorded_allow == frozenset({BTC, ETH})
        frame = env.h.provider(observed(env, env.T(0) + LH.seconds(2)))
        restart(env)
        assert logical_rows(env)[1]["data"] == stored
        assert env.h.provider(observed(env, env.T(0) + LH.seconds(2))) == frame
        record(env, 1, SWITCH[1])
        assert logical_rows(env)[2]["data"]["universe"]["tickers"]["prices"][0] == [BTC, "110", -2000]
        assert env.h.recorded_allow == frozenset({BTC, ETH})


def test_two_slot_switch_sells_the_old_coin_then_buys_the_new_one():
    with head_root() as hroot:
        env = ubuild(hroot)
        holdings = ({}, {}, {}, {BTC: D(45)}, {BTC: D(45)}, {BTC: D("0.01")})
        cash = (D(10000), D(10000), D(10000), D(5000), D(5000), D(9600))
        signals = []
        for i in range(6):
            symbol = ETH if i == 5 else BTC   # the coordinator renews to ETH once the account is flat in BTC
            record(env, i, SWITCH[i], symbol=symbol, cash=cash[i], holdings=holdings[i])
            signals.append(tick(env, i, symbol=symbol, cash=cash[i], holdings=holdings[i]))
        assert [(s.action, s.quantity, s.limit_price) for s in signals] == [
            ("hold", D(0), D(0)), ("hold", D(0), D(0)), ("entry", D("48.05"), D(105)),
            ("entry", D("1.52"), D(106)), ("exit", D(45), D(103)), ("entry", D("44.83"), D(108))]
        frame = env.h.provider(observed(env, env.T(5) + LH.seconds(2)))
        assert [(bar.symbol, bar.tick_size) for bar in frame.bars] == [(BTC, D(1))] * 5 + [(ETH, D(1))]
        assert frame.chooser_inputs == ChooserInputs(held=ETH, hold_count=1, top_n=(BTC, ETH), flags=ALL_UNFLAGGED,
                                                     prices=pairs(SWITCH[4]), lag_prices=pairs(SWITCH[3]))
        assert [row["data"]["decision"]["coin"] for row in logical_rows(env)[1:]] == [None, BTC, BTC, ETH, ETH, ETH]


def test_prior_decision_is_recomputed_from_the_inputs_the_frame_carries():
    with head_root() as hroot:
        env = ubuild(hroot)
        for i in range(3):
            record(env, i, SWITCH[i])
        frame = env.h.provider(observed(env, env.T(2) + LH.seconds(2)))
        carried = frame.chooser_inputs
        assert carried == ChooserInputs(held=None, hold_count=1, top_n=(BTC, ETH), flags=ALL_UNFLAGGED,
                                        prices=pairs(SWITCH[1]), lag_prices=pairs(SWITCH[0]))
        assert frame.prior_decision.target_fraction == D("0.5")
        signal = tick(env, 2)
        assert (signal.action, signal.quantity, signal.limit_price) == ("entry", D("48.05"), D(105))
        # The same frame whose carried prices make ETH the decision gives BTC a target of 0.
        swapped = replace(carried, prices=((BTC, D(105)), (ETH, D(110)), (XRP, D(200))))
        assert tick(env, 2, driver=substitute(env, replace(frame, chooser_inputs=swapped))).action == "hold"
        for changes, code in (({"chooser_inputs": replace(carried, lag_prices=None)}, "FIXED_DRIVER_TARGET_MISMATCH"),
                              ({"chooser_inputs": None}, "FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED"),
                              ({"universe_sha256": None}, "FIXED_DRIVER_DIGEST_INVALID")):
            LH.refused(lambda: tick(env, 2, driver=substitute(env, replace(frame, **changes))), code)
        fixed = LD.fixture()
        base = fixed.frame
        for changes in ({"chooser_inputs": carried}, {"universe_sha256": "e" * 64}):
            fixed.frame = replace(base, **changes)
            LD.reject(lambda: LD.decide(fixed), "FIXED_DRIVER_HISTORY_SOURCE_INVALID")
        # A fixed profile still refuses another coin's holding in its own account.
        other = LD.fixture()
        key = (other.profile.venue, other.profile.account_scope)
        held = dict(other.observation.account.holdings) | {(*key, "spot", ETH): D(1)}
        other.observation = replace(other.observation, account=replace(other.observation.account, holdings=held))
        LD.reject(lambda: LD.decide(other), "FIXED_DRIVER_OTHER_INVENTORY_UNSUPPORTED")


def test_each_bar_is_checked_at_its_own_coin_and_tick_and_a_bookless_bar_never_anchors():
    with head_root() as hroot:
        env = ubuild(hroot)
        record(env, 0, SWITCH[0])
        record(env, 1, SWITCH[1], symbol=ETH, tick=D("0.5"), bid=D("100.5"), ask=D("101.5"))
        record(env, 2, SWITCH[2], booked=False)
        LH.refused(lambda: tick(env, 2), "FIXED_DRIVER_BOOK_UNAVAILABLE")
        record(env, 3, SWITCH[3])
        frame = env.h.provider(observed(env, env.T(3) + LH.seconds(2)))
        assert [(bar.symbol, bar.tick_size, bar.bid) for bar in frame.bars] == [
            (BTC, D(1), D(100)), (ETH, D("0.5"), D("100.5")), (BTC, D(1), None), (BTC, D(1), D(103))]
        signal = tick(env, 3)
        assert (signal.action, signal.quantity, signal.limit_price) == ("entry", D("47.59"), D(106))
        assert tick(env, 3, driver=substitute(env, frame)) == signal
        bars = list(frame.bars)
        for index, change, code in ((1, {"tick_size": D(1)}, "FIXED_DRIVER_BAR_PRICE_INVALID"),
                                    (2, {"bid": D(102)}, "FIXED_DRIVER_BAR_REQUIRED"),
                                    (2, {"symbol": "BTC"}, "FIXED_DRIVER_BAR_REQUIRED"),
                                    (3, {"tick_size": D("0.5")}, "FIXED_DRIVER_QUOTE_ANCHOR_MISMATCH")):
            changed = replace(frame, bars=tuple(bars[:index] + [replace(bars[index], **change)] + bars[index + 1:]))
            LH.refused(lambda: tick(env, 3, driver=substitute(env, changed)), code)


def test_window_end_targets_zero_and_records_no_decision():
    with head_root() as hroot:
        env = ubuild(hroot, end=2)
        record(env, 0, SWITCH[0])
        record(env, 1, SWITCH[1])
        record(env, 2, SWITCH[2], cash=D(5000), holdings={BTC: D(45)})
        assert [row["data"]["decision"] for row in logical_rows(env)[2:]] == [
            {"coin": BTC, "target_fraction": "0.5", "held": BTC, "hold_count": 1}, None]
        signal = tick(env, 2, cash=D(5000), holdings={BTC: D(45)})
        assert (signal.action, signal.quantity, signal.limit_price) == ("exit", D(45), D(101))
        LH.refused(lambda: record(env, 3, SWITCH[3]), "HISTORY_WINDOW_COMPLETE")


# Original Task4 test fragment; root appends after Task2/3 shared helpers.
def test_restart_replays_v2_rows_and_restores_the_chooser_state():
    with head_root() as hroot:
        env = ubuild(hroot)
        held = (Position(market="spot", symbol=BTC, base_currency="BTC", quote_currency="KRW", units=D(45),
                         price=D(104), asof=env.T(3) - LH.seconds(3)),)
        holdings = ({}, {}, {}, {BTC: D(45)}, {BTC: D(45)})
        cash = (D(10000), D(10000), D(10000), D(5000), D(5000))
        for i in range(5):
            record(env, i, SWITCH[i], booked=i != 1, cash=cash[i], holdings=holdings[i],
                   positions=held if i == 3 else (),
                   slot_universe=reads(env, 2, SWITCH[2], flags={XRP: "caution"}) if i == 2 else None)
        frame = env.h.provider(observed(env, env.T(4) + LH.seconds(2)))
        signal = tick(env, 4, cash=D(5000), holdings={BTC: D(45)})
        assert (signal.action, signal.quantity, signal.limit_price) == ("exit", D(45), D(103))
        restart(env)
        assert env.h.provider(observed(env, env.T(4) + LH.seconds(2))) == frame
        assert env.h.recorded_allow == frozenset({BTC, ETH})
        assert tick(env, 4, cash=D(5000), holdings={BTC: D(45)}) == signal
        # The next decisions read the restored state (ETH held for two decisions) and price vectors: BTC jumps, so
        # slot 5 switches to BTC, and slot 6, flat over one slot, goes to cash.
        jump = {BTC: D(150), ETH: D(120), XRP: D(200)}
        record(env, 5, jump)
        record(env, 6, jump)
        assert [row["data"]["decision"]["coin"] for row in logical_rows(env)[1:]] == [None, BTC, BTC, ETH, ETH, BTC, None]
        later = env.h.provider(observed(env, env.T(6) + LH.seconds(2)))
        assert later.chooser_inputs == ChooserInputs(held=ETH, hold_count=2, top_n=(BTC, ETH), flags=ALL_UNFLAGGED,
                                                     prices=pairs(jump), lag_prices=pairs(SWITCH[4]))
        with patch("execution_launch.live_history.chooser_decision",
                   return_value=(XRP, ChooserState(held=XRP, hold_count=1))):
            LH.refused(lambda: restart(env), "HISTORY_STORE_RECORD_INVALID")
        restart(env)
        assert env.h.provider(observed(env, env.T(6) + LH.seconds(2))) == later
        # A slot missed across a restart is never backfilled: slot 7 recorded at slot 8 + 1 s refuses, and the
        # window has no later row (the coordinator's status field for it is PR 4e).
        LH.refused(lambda: record(env, 8, jump), "HISTORY_SLOT_MISSED")
        assert len(logical_rows(env)) == 8


def test_restart_replays_every_row_v2_variant():
    """Replay of a coin on another tick, unlisted and dust holdings, a bookless slot with a flag exception and a
    slot whose universe reads all failed."""
    with head_root() as hroot:
        env = ubuild(hroot)
        stamp = env.T(1) - LH.seconds(3)
        positions = (Position(market="spot", symbol=ETH, base_currency="ETH", quote_currency="KRW", units=D(2),
                              price=D(105), asof=stamp),
                     Position(market="spot", symbol="KRW-OLD", base_currency="OLD", quote_currency="KRW",
                              units=D(7), price=D(0), asof=stamp, unlisted=True))
        record(env, 0, SWITCH[0])
        record(env, 1, SWITCH[1], symbol=ETH, tick=D("0.5"), bid=D("100.5"), ask=D("101.5"), holdings={ETH: D(2)},
               positions=positions)
        record(env, 2, SWITCH[2], booked=False, slot_universe=reads(env, 2, SWITCH[2], flags={XRP: "caution"}))
        record(env, 3, SWITCH[3], slot_universe=down(env, 3))
        frame = env.h.provider(observed(env, env.T(3) + LH.seconds(2)))
        restart(env)
        assert env.h.provider(observed(env, env.T(3) + LH.seconds(2))) == frame
        assert env.h.recorded_allow == frozenset()


def test_restart_refuses_malformed_v2_fields_before_the_independent_head_check():
    with head_root() as hroot:
        env = ubuild(hroot)
        held = (Position(market="spot", symbol=BTC, base_currency="BTC", quote_currency="KRW", units=D(2),
                         price=D(100), asof=env.T(0) - LH.seconds(3)),)
        record(env, 0, SWITCH[0], holdings={BTC: D(2)}, positions=held)
        original = LH.journal(env).read_bytes()
        head = env.head.read()
        changes = (
            lambda d: d.pop("trade_symbol"),
            lambda d: d.update(trade_symbol=ETH),
            lambda d: d.update(tick_size="0"),
            lambda d: d.update(tick_size="1.0"),
            lambda d: d["holdings"][0].__setitem__(1, "2.0"),
            lambda d: d["holdings"][0].__setitem__(3, "not-a-time"),
            lambda d: d["holdings"][0].__setitem__(4, not d["holdings"][0][4]),
            lambda d: d["holdings"][0].__setitem__(5, not d["holdings"][0][5]),
            lambda d: d["holdings"].append(list(d["holdings"][0])),
            lambda d: d["universe"]["snapshot"].update(top_n=[BTC, BTC]),
            lambda d: d["universe"]["flags"].update(exceptions=[[BTC, "unflagged"]]),
            lambda d: d["universe"]["flags"].update(exceptions=[[BTC, "warning"], [BTC, "warning"]]),
            lambda d: d["universe"].update(flags="unavailable"),
            lambda d: d["universe"]["tickers"]["prices"][0].__setitem__(1, "0"),
            lambda d: d["universe"]["tickers"]["prices"][0].__setitem__(2, True),
            lambda d: d["universe"]["tickers"]["prices"][0].__setitem__(2, 60_001),
            lambda d: d["decision"].update(coin=XRP),
        )
        for change in changes:
            try:
                # New synthetic object hashes and a rehashed reference row leave the independent head unchanged.
                # Parser-invalid logical inputs must fail before that final head mismatch, just as inline v2 did.
                rewrite_slot(env, 2, change)
                LH.refused(lambda: restart(env), "HISTORY_STORE_RECORD_INVALID")
                assert env.head.read() == head
            finally:
                LH.journal(env).write_bytes(original)
        restart(env)
        assert env.head.read() == head and LH.journal(env).read_bytes() == original


def test_legacy_v2_logical_replay_is_read_only_and_old_identity_never_resumes_new_code():
    """An explicitly synthetic old-format bundle, not an approved historical deployment or real observation."""
    with head_root() as hroot:
        source = ubuild(hroot)
        for i in range(3):
            record(source, i, SWITCH[i], booked=i != 1)
        expected = source.h.provider(observed(source, source.T(2) + LH.seconds(2)))
        table = logical_rows(source)
        window = replace(source.window, deployment_id="invented-legacy-v2-read-only")
        protocol = replace(source.e.protocol, history_storage_sha256=None)
        e = SimpleNamespace(**(vars(source.e) | {"window": window, "protocol": protocol, "storage_policy": None}))
        env = SimpleNamespace(e=e, window=window, profile=e.profile, hroot=hroot,
                              name="legacy-v2-read-only", storage_policy=None, c=list(source.c), T=source.T)
        env.clock = lambda: env.c[0]
        env.head = BaselineHead(root=hroot, name=env.name, chain=chain_for(env))
        env.head.initialize_reviewed_head(GENESIS)
        attach(env)
        current = describe_fixed_driver(env.d)
        # Hash of a54a390's actual eight-file driver closure; only the source binding is historical. All records
        # here are invented fixture data in temporary roots, and no old review/signature is imported or reused.
        historical = replace(current, deployment_code_sha256=
                             "552b5c225a8735930d7025811699b04f01558070b09645c25276d37215334460")
        assert historical != current
        table[0]["data"] = {"identity": asdict(historical)}
        directory = LH.directory(window)
        directory.mkdir(parents=True, exist_ok=True)
        journal = LH.journal(env)
        previous = GENESIS
        for row in table:
            row["prev_sha256"] = previous
            row["row_sha256"] = hashlib.sha256(_canonical({k: v for k, v in row.items()
                                                          if k != "row_sha256"})).hexdigest()
            with journal.open("ab") as stream:
                stream.write(_canonical(row) + b"\n")
            assert env.head.compare_and_set(previous, row["row_sha256"]) is True
            previous = row["row_sha256"]
        original, head = journal.read_bytes(), env.head.read()
        state = (env.h._slots, env.h._chain, env.h._marks, env.h._prices, env.h._state, env.h._inputs,
                 env.h.recorded_allow, env.h._head, env.h._size, env.h._seq, env.h._bound)
        replayed = env.h._replay(historical, install=False)
        assert tuple(slot.bar for slot in replayed[0]) == expected.bars
        assert replayed[4] == source.h._state and replayed[5] == source.h._inputs
        assert replayed[6] == source.h.recorded_allow
        assert (replayed[7], replayed[8], replayed[9]) == (head, len(original), len(table))
        assert state == (env.h._slots, env.h._chain, env.h._marks, env.h._prices, env.h._state, env.h._inputs,
                         env.h.recorded_allow, env.h._head, env.h._size, env.h._seq, env.h._bound)
        LH.refused(lambda: env.h.provider(LH.obs(env, env.T(2) + LH.seconds(2))), "HISTORY_NOT_BOUND")
        LH.refused(lambda: env.h.bind(env.d), "HISTORY_IDENTITY_CHANGED")
        assert journal.read_bytes() == original and env.head.read() == head
