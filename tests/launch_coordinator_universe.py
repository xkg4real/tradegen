"""Universe coordinator (spec sections 7, 9, 10, 12 and 15): construction, trade-coin choice and renewal, the slot
unit, events, toasts, status and the console odds step, over tests/launch_coordinator.py's fixture with a universe
profile and doubles for the slot reads, terms, history and toasts. Offline; temporary state only."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import threading
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from execution_accounts.model import Position
from execution_accounts.universe import FlagRead, TickerRead
from execution_launch import coordinator as C
from execution_launch import runner as R
from execution_launch.coordinator import CoordinatorError
from execution_launch.driver import DeploymentWindow
from execution_launch.toast_queue import ToastQueue
from tests.control_session import selected
from tests.launch_coordinator import HOLD, PRICE, Books, build, fixture, refused, seconds
from tests.launch_runner_universe import RULE, SNAPSHOT, universe_profile, universe_snapshot

D = Decimal
BTC, XRP, ETH = "KRW-BTC", "KRW-XRP", "KRW-ETH"
RED = "TRADEGEN universe red"


class FixtureRefusal(ValueError):
    """A fixed-code refusal from a double (a ValueError subclass, so the coordinator's _code passes the code)."""


class SlotSource:
    """UniverseSlotSource double: the flag read lists `flags` (BTC and XRP unflagged unless changed); `fail` names
    the reads that return ok=False; prices trade `age` before the read; `calls` records each read."""
    def __init__(self, fake):
        self.fake, self.fail, self.calls, self.age = fake, set(), [], timedelta(0)
        self.flags = {BTC: "unflagged", XRP: "unflagged"}

    def read_flags(self):
        self.calls.append("flags")
        if "flags" in self.fail:
            return FlagRead(ok=False, received_at=None, sha256=None, flags=MappingProxyType({}))
        return FlagRead(ok=True, received_at=self.fake.now, sha256="f" * 64, flags=MappingProxyType(dict(self.flags)))

    def read_tickers(self, markets):
        self.calls.append(("tickers", tuple(markets)))
        if "tickers" in self.fail:
            return TickerRead(ok=False, received_at=None, sha256=None, prices=MappingProxyType({}))
        traded = self.fake.now - self.age
        return TickerRead(ok=True, received_at=self.fake.now, sha256="7" * 64,
                          prices=MappingProxyType({market: (PRICE, traded) for market in markets}))


class UniverseBooks(Books):
    """Books whose read names the trade coin (spec section 10); `symbols` records each name, `fail` raises."""
    def __init__(self, fake):
        super().__init__(fake)
        self.symbols, self.fail = [], False

    def read(self, symbol=None):
        self.symbols.append(symbol)
        if self.fail:
            raise RuntimeError("BOOK-SECRET-1")
        return super().read()


class Terms:
    """Terms source double: read(symbol) records the name; the observation names the coin and whether it is within
    its buy cap (renewals(env) patches renew_profile and within_buy_cap to read these); `fail` raises."""
    def __init__(self):
        self.reads, self.fail, self.within = [], None, True

    def read(self, symbol=None):
        self.reads.append(symbol)
        if self.fail is not None:
            raise self.fail
        return SimpleNamespace(symbol=symbol, within=self.within)


class History:
    """Universe LiveHistory double: record_slot keeps its keywords and sets recorded_allow; decided_symbol returns
    `decided`; `fail` raises."""
    def __init__(self):
        self.rows, self.fail, self.decided, self.recorded_allow = [], None, None, None

    def record_slot(self, book, account, **options):
        if self.fail is not None:
            raise self.fail
        self.rows.append((book, options))
        self.recorded_allow = options["universe"].allow
        return "a" * 64

    def decided_symbol(self):
        return self.decided


class Recorder:
    """A synchronous stand-in for the coordinator's ToastQueue."""
    def __init__(self):
        self.puts = []

    def put(self, title, body):
        self.puts.append((title, body))


def program(**changes):
    """The reviewed program fields the coordinator reads (PR 4b's ProgramSpec v2 carries them)."""
    return SimpleNamespace(**({"kind": C.UNIVERSE_KIND, "universe_rule_sha256": RULE, "max_candidates": 2} | changes))


def position(symbol, units, price, at):
    return Position(market="spot", symbol=symbol, base_currency=symbol[4:], quote_currency="KRW", units=D(units),
                    price=D(price), asof=at)


@contextmanager
def universe_fixture():
    """tests/launch_coordinator.fixture with a universe profile and the doubles above; the driver decides HOLD.
    `_assess` is pinned to the fixed profile's assessment because the universe evaluator is PR 5 (PR 4b refuses
    forward-universe-v1 evidence); every universe check runs after it."""
    with fixture() as env:
        assessment, binding = R._assess(env.profile, env.evidence, env.driver, env.review, env.t0)
        env.fixed_profile, env.profile = env.profile, universe_profile(env.profile)
        env.universe, env.signal[0] = universe_snapshot(env.t0), HOLD
        env.slots, env.books, env.terms = SlotSource(env.fake), UniverseBooks(env.fake), Terms()
        env.history, env.toasts = History(), Recorder()
        with patch.object(R, "_assess", lambda *args: (assessment, binding)):
            yield env


def build_universe(env, **changes):
    """build() with the universe profile and doubles. After checking that construction started no toast worker, the
    queue is swapped for env.toasts; controller.observe carries env.universe as RiskResult.universe (PR 4a)."""
    options = {"profile": env.profile, "slot_source": env.slots, "program": program(), "terms_source": env.terms,
               "history": env.history, "toast": lambda title, body: True}
    c = build(env, **(options | changes))
    assert type(c._toasts) is ToastQueue and c._toasts._thread is None
    c._toasts = env.toasts
    observe = c._controller.observe
    c._controller.observe = lambda *, now: replace(observe(now=now), universe=env.universe)
    return c


@contextmanager
def renewals(env):
    """renew_profile issues a renewal to the observation's coin (only fields the universe contract digest leaves out
    change), validate_renewal accepts it and within_buy_cap reads the double's flag. env.renewed records
    (symbol, allow_symbol_change). create=True: the coordinator imports within_buy_cap only from Task 9 on."""
    env.renewed = []

    def renew(profile, observation, *, now, allow_symbol_change=False):
        symbol = observation.symbol or profile.symbol
        env.renewed.append((symbol, allow_symbol_change))
        rules = replace(profile.instrument_rules, symbol=symbol, asof=now)
        return SimpleNamespace(profile=replace(profile, symbol=symbol, instrument_rules=rules))
    with patch.object(C, "renew_profile", renew), \
            patch.object(C, "within_buy_cap", lambda observation: observation.within, create=True), \
            patch.object(R, "validate_renewal", lambda renewal, *, previous_profile, now: renewal.profile):
        yield env


def reframe(c, positions):
    """Every later _publish keeps the real provider observation, but the frame the coordinator reads
    (`_latest_frame.accounts[0]`) holds `positions`."""
    publish = c._publish

    def wrapped(previous, now, book):
        observation = publish(previous, now, book)
        frame = c._latest_frame
        c._latest_frame = SimpleNamespace(interval=frame.interval,
                                          accounts=(replace(frame.accounts[0], positions=tuple(positions)),))
        return observation
    c._publish = wrapped


def run_slot(env, c, slot):
    """One slot unit outside run(): the clock at the prefetch lead, then _slot."""
    env.fake.now = slot - seconds(3)
    c._slot(slot)


def allow_seen(c):
    """The entry_allow of every Runner.run call."""
    seen, run = [], c._runner.run

    def wrapped(timestamps, **options):
        seen.append(options.get("entry_allow"))
        return run(timestamps, **options)
    c._runner.run = wrapped
    return seen


def stub_kill(c, recorded):
    """A prepared-session stand-in and a Controller.kill recorder returning `recorded` (PR 4a tests the real kill)."""
    kills = []
    c._launch = SimpleNamespace(prepared=SimpleNamespace(session_id="Lfixture-universe"))
    c._controller.kill = lambda session_id, *, reason, now: kills.append(reason) or recorded
    return kills


def test_universe_construction_is_inert_and_status_starts_empty():
    with universe_fixture() as env:
        before = threading.active_count()
        c = build_universe(env)
        assert threading.active_count() == before and env.producer.prefetches == [] and env.slots.calls == []
        s = c.status()
        assert (s.held_symbol, s.trade_symbol, s.snapshot_day, s.snapshot_sha256, s.universe_state, s.held_flag,
                s.allow_count, s.buy_block_reasons, s.disarm_failed, s.window_ended_missed_slot) == (
                    None, None, None, None, None, None, 0, (), False, False)
        assert c._holding()                         # no frame read yet: fail closed


def test_a_universe_coordinator_needs_its_slot_source_program_terms_and_history():
    with universe_fixture() as env:
        for changes in ({"slot_source": None}, {"slot_source": SimpleNamespace(read_flags=lambda: None)},
                        {"program": None}, {"program": program(kind="fixed")},
                        {"program": program(universe_rule_sha256="f" * 64)}, {"program": program(max_candidates=0)},
                        {"program": program(max_candidates=True)}, {"terms_source": None},
                        {"history": SimpleNamespace(record_slot=lambda *args, **kwargs: None)}, {"toast": None}):
            refused(lambda: build_universe(env, **changes), "COORDINATOR_INTEGRATIONS_REQUIRED")


def test_a_universe_window_is_at_most_72_hours():
    with universe_fixture() as env:
        def code(profile, hours):
            window = DeploymentWindow(deployment_id="coord-universe", start=env.window.start,
                                      end=env.window.start + timedelta(hours=hours))
            try:
                build_universe(env, profile=profile, window=window, monitor_until=window.end)
            except CoordinatorError as exc:
                return str(exc)
            return None
        assert code(env.profile, 73) == "COORDINATOR_WINDOW_INVALID"
        assert code(env.profile, 72) != "COORDINATOR_WINDOW_INVALID"     # other checks may still refuse it
        with patch.object(C, "UNIVERSE_WINDOW_MAX", timedelta(hours=1)):
            assert code(env.fixed_profile, 2) != "COORDINATOR_WINDOW_INVALID"


def test_disarm_locked_runs_under_the_held_lock_and_the_owner_disarm_still_republishes():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        kills, published = stub_kill(c, True), []
        publish = c._board.publish
        c._board.publish = lambda frame, book: published.append(frame) or publish(frame, book)
        with c._work:
            result = c._disarm_locked(reason="market_vanished", code="COORDINATOR_UNIVERSE_DISARM", republish=False)
        assert result.session_prepared and result.owner_disarm_recorded and published == []
        assert kills == ["market_vanished"] and c.status().reasons == ("COORDINATOR_UNIVERSE_DISARM",)
        c.disarm(timeout=0)
        assert kills == ["market_vanished", "owner_requested"] and published == [c._latest_frame]
        assert c.status().reasons == ("COORDINATOR_OWNER_DISARM_RECORDED",) and c.status().strategy_stopped


def test_toasts_are_queued_once_per_key_and_never_wait_for_the_toast():
    with universe_fixture() as env:
        c = build_universe(env)
        c._toast_once("extra:2026-11-11", "red", "body-1")
        c._toast_once("extra:2026-11-11", "red", "body-2")
        c._toast_once("held-flag:2026-11-11", "amber", "body-3")
        assert env.toasts.puts == [(RED, "body-1"), ("TRADEGEN universe amber", "body-3")]
        shown, release = [], threading.Event()
        c._toasts = ToastQueue(lambda title, body: release.wait(5) and shown.append(title))
        c._toast_once("missed", "red", "body-4")    # returns while the toast is still showing
        worker = c._toasts._thread
        assert shown == [] and worker.is_alive()
        release.set()
        worker.join(5)
        assert shown == [RED]


def test_book_and_terms_reads_name_the_trade_coin():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        c.bootstrap()
        assert c._read_book() is not None and env.books.symbols == [BTC]
        c.refresh_instrument_rules()
        assert env.terms.reads == [BTC] and env.renewed == [(BTC, False)]


def test_monitors_track_held_coins_extra_holdings_and_the_snapshot():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        s = c.status()
        assert (s.held_symbol, s.trade_symbol, c._held, c._extra) == (BTC, BTC, (BTC,), False)
        assert (s.snapshot_day, s.snapshot_sha256, s.universe_state) == (env.universe.day, SNAPSHOT, "in_force")
        reframe(c, [position(BTC, "0.001", PRICE, env.fake.now), position(XRP, "100", "1000", env.fake.now)])
        env.universe = None
        env.fake.now += seconds(20)
        c._monitor("monitor")
        s = c.status()
        assert c._held == (BTC, XRP) and c._extra and (s.universe_state, s.snapshot_day) == ("no_snapshot", None)
        assert [title for title, _ in env.toasts.puts] == [RED] and any(k.startswith("extra:") for k in c._toasted)
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert len(env.toasts.puts) == 1                 # once per day


def test_held_coins_and_universe_state_are_pure():
    at = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)
    account = SimpleNamespace(positions=(position(XRP, "100", "1000", at), position(BTC, "0.001", PRICE, at),
                                         position(ETH, "1", "0", at), position("KRW-SOL", "0.01", "100000", at)))
    assert C.held_coins(account, D("5000")) == (BTC, XRP)          # equal values: by symbol; unlisted and dust out
    snapshot = universe_snapshot(at)
    assert C.universe_state(snapshot, RULE, at) == "in_force"
    assert C.universe_state(snapshot, "f" * 64, at) == "rule_mismatch"
    assert C.universe_state(None, RULE, at) == "no_snapshot"
    assert C.universe_state(snapshot, RULE, snapshot.valid_until) == "no_snapshot"


def test_terms_failures_block_slots_only_while_a_coin_is_held():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        env.terms.fail = FixtureRefusal("TERMS_INQUIRY_FAILED")
        refused(c.refresh_instrument_rules, "TERMS_INQUIRY_FAILED")
        assert c._terms_blocked                          # no frame read yet: fail closed
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        c.bootstrap()                                    # BTC held
        env.terms.fail = FixtureRefusal("TERMS_INQUIRY_FAILED")
        refused(c.refresh_instrument_rules, "TERMS_INQUIRY_FAILED")
        assert c._terms_blocked and not c._terms_unavailable and not c._vanished
        env.terms.fail = FixtureRefusal("TERMS_MARKET_INACTIVE")
        refused(c.refresh_instrument_rules, "TERMS_MARKET_INACTIVE")
        assert c._vanished                               # the vanish event of the next slot unit
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [])
        c.bootstrap()                                    # nothing held
        env.terms.fail = FixtureRefusal("TERMS_INQUIRY_FAILED")
        refused(c.refresh_instrument_rules, "TERMS_INQUIRY_FAILED")
        assert not c._terms_blocked and c._terms_unavailable
        env.fake.now += seconds(20)
        c._monitor("monitor")                            # retried at the next monitor, still failing
        assert c.status().new_entry_blocked and c.status().instrument_source == "TERMS_INQUIRY_FAILED"
        env.terms.fail = None
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert not c._terms_unavailable and env.terms.reads == [BTC, BTC, BTC]


def test_a_previously_held_coin_marked_unlisted_latches_the_vanish_event():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        assert c._held == (BTC,) and not c._vanished
        reframe(c, [position(BTC, "0.001", "0", env.fake.now)])
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert c._held == () and c._vanished and c.status().held_symbol is None


def test_choose_trade_coin_follows_rules_1_to_3():
    assert C.choose_trade_coin((XRP,), BTC, None, False) == XRP
    assert C.choose_trade_coin((XRP, BTC), BTC, None, True) == BTC
    assert C.choose_trade_coin((XRP, ETH), BTC, BTC, True) == XRP
    assert C.choose_trade_coin((), BTC, XRP, True) == XRP
    assert C.choose_trade_coin((), BTC, XRP, False) == BTC
    assert C.choose_trade_coin((), BTC, None, True) == BTC


def test_a_flat_account_renews_to_the_decided_coin_and_dust_does_not_count():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [position(BTC, "0.00001", PRICE, env.fake.now)])       # 1,000 KRW of BTC: dust
        env.history.decided = XRP
        c.bootstrap()
        assert env.terms.reads == [XRP] and env.renewed == [(XRP, True)]
        assert c._profile.symbol == XRP and c._runner.profile.symbol == XRP and c.status().trade_symbol == XRP
        c._read_book()
        assert env.books.symbols == [XRP]


def test_an_uncertain_sell_in_the_trade_coin_holds_the_switch_while_the_trade_coin_keeps_renewing():
    """Spec section 19: no symbol change while an IOC sell in A is uncertain with zero A balance; not flat is a
    normal outcome; A keeps renewing; once no order in A is live the next monitor renews to B."""
    from execution_control.controller import OrderState
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [])                                   # zero BTC balance in the frame
        env.history.decided = XRP
        uncertain = OrderState(client_id="fixture-ioc-sell", status="UNKNOWN", order_digest="d" * 64,
                               side="sell", symbol=BTC, updated_at=env.t0)
        reconciled = []
        c._controller.states = lambda: (uncertain,)
        c._controller.reconcile = lambda client_id, *, now: reconciled.append(client_id)
        c.bootstrap()
        s = c.status()
        assert reconciled == ["fixture-ioc-sell"] and s.universe_state == "in_force"   # the monitor ran through
        assert env.terms.reads == [] and env.renewed == [] and c._profile.symbol == BTC
        assert (s.instrument_source, s.account_source, s.reasons) == ("", "", ())
        c.refresh_instrument_rules()                     # A keeps renewing
        assert env.terms.reads == [BTC] and env.renewed == [(BTC, False)] and c._profile.symbol == BTC
        c._controller.states = lambda: ()                # no order in BTC any more
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert env.terms.reads == [BTC, XRP] and env.renewed == [(BTC, False), (XRP, True)]
        assert c._profile.symbol == XRP


def test_a_restart_holding_another_coin_renews_to_it():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [position(XRP, "100", "1000", env.fake.now)])
        c.bootstrap()
        assert c._held == (XRP,) and env.renewed == [(XRP, True)] and c._profile.symbol == XRP
        assert c.status().held_symbol == XRP


def test_a_failed_cross_coin_renewal_blocks_buys_and_is_retried():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [])
        env.history.decided = XRP
        env.terms.fail = FixtureRefusal("TERMS_INQUIRY_FAILED")
        c.bootstrap()
        assert c._terms_unavailable and not c._terms_blocked and c._profile.symbol == BTC
        assert c.status().instrument_source == "TERMS_INQUIRY_FAILED" and c.status().new_entry_blocked
        env.terms.fail = None
        env.fake.now += seconds(20)
        c._monitor("monitor")                    # the trade coin's terms first, then the switch again
        assert env.terms.reads == [XRP, BTC, XRP] and env.renewed == [(BTC, False), (XRP, True)]
        assert c._profile.symbol == XRP and not c._terms_unavailable
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [])
        env.history.decided = XRP
        calls = []

        def validate(renewal, *, previous_profile, now):
            calls.append(renewal.profile.symbol)
            if len(calls) == 1:
                raise FixtureRefusal("RENEWAL_HEAD_CHANGED")
            return renewal.profile
        with patch.object(R, "validate_renewal", validate):
            c.bootstrap()
            assert c._pending_terms is not None and c._terms_unavailable and c._profile.symbol == BTC
            env.fake.now += seconds(20)
            c._monitor("monitor")                # the issued renewal is retried, never re-read
        assert calls == [XRP, XRP] and env.terms.reads == [XRP] and c._profile.symbol == XRP
        assert c._pending_terms is None and not c._terms_unavailable


def test_a_coin_held_after_the_window_end_raises_one_toast():
    with universe_fixture() as env:
        c = build_universe(env)
        env.fake.now = env.window.end + seconds(11)
        c.bootstrap()
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert [title for title, _ in env.toasts.puts] == [RED] and c._toasted == {"window-end"}


def test_decided_symbol_is_the_latest_decision_coin():
    from execution_launch.live_history import LiveHistory
    from execution_launch.program import ChooserState
    h = object.__new__(LiveHistory)
    h._universe, h._slots, h._state = True, (), ChooserState(held=None, hold_count=0)
    assert h.decided_symbol() is None
    h._slots, h._state = (SimpleNamespace(decision=object()),), ChooserState(held=XRP, hold_count=1)
    assert h.decided_symbol() == XRP
    h._slots += (SimpleNamespace(decision=None),)              # the window-end slot decides nothing
    assert h.decided_symbol() is None
    h._universe, h._slots = False, (SimpleNamespace(decision=object()),)
    assert h.decided_symbol() is None


def test_events_list_vanish_warning_and_an_uncertain_held_flag_in_table_order():
    with universe_fixture() as env:
        c = build_universe(env)
        at = env.fake.now
        account = SimpleNamespace(positions=(position(BTC, "0.001", PRICE, at), position(ETH, "0.0001", "1000", at),
                                             position(XRP, "0", "1000", at)))
        c._held = (BTC,)
        flags = FlagRead(ok=True, received_at=at, sha256="f" * 64,
                         flags=MappingProxyType({ETH: "warning", XRP: "warning"}))
        events = c._events(flags, account, "2026-11-11")
        assert [code for code, _ in events] == ["UNIVERSE_OTHER_COIN_WARNING", "UNIVERSE_HELD_FLAG_UNCERTAIN"]
        for _ in range(2):
            for _, action in events:
                action()
        assert c._toasted == {"warning:KRW-ETH:2026-11-11", "held-flag:2026-11-11"} and len(env.toasts.puts) == 2
        c._vanished = True
        failed = FlagRead(ok=False, received_at=None, sha256=None, flags=MappingProxyType({}))
        assert [code for code, _ in c._events(failed, account, "2026-11-11")] == ["UNIVERSE_MARKET_VANISHED"]


def test_vanish_stops_and_disarms_once_and_a_failed_kill_is_sticky():
    for recorded, failure in ((True, None), (False, None), (None, FixtureRefusal("FIXTURE_KILL_FAILED"))):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            kills = stub_kill(c, recorded)
            if failure is not None:
                def kill(session_id, *, reason, now):
                    kills.append(reason)
                    raise failure
                c._controller.kill = kill
            with c._work:
                assert c._vanish() == ("COORDINATOR_UNIVERSE_DISARM",)
                assert c._vanish() == ()
            assert kills == ["market_vanished"] and c.status().strategy_stopped
            assert c.status().disarm_failed is (recorded is not True)
            assert c._toasted == ({"vanished"} if recorded is True else {"disarm-failed"})


def test_the_remainder_block_needs_two_hold_ticks_in_a_row_while_the_trade_coin_is_held():
    with universe_fixture() as env:
        c = build_universe(env)
        c._held = (BTC,)
        hold, submitted = SimpleNamespace(status="hold"), SimpleNamespace(status="submitted")
        c._after_tick(hold, None, "d1")
        c._after_tick(submitted, None, "d1")
        c._after_tick(hold, BTC, "d1")             # the decision is the trade coin itself
        c._after_tick(hold, XRP, "d1")
        assert not c._remainder and c._remainder_ticks == 1
        c._after_tick(hold, None, "d1")
        assert c._remainder and c._toasted == {"remainder:d1"}
        c._after_tick(hold, None, "d1")
        assert len(env.toasts.puts) == 1


def test_a_slot_records_its_universe_inputs_and_ticks_with_the_recorded_allow_list():
    for flag_map, markets, allow in (({BTC: "unflagged", XRP: "unflagged"}, (BTC, XRP), {BTC, XRP}),
                                     ({BTC: "unflagged", XRP: "caution"}, (BTC, XRP), {BTC}),
                                     ({BTC: "unflagged"}, (BTC,), {BTC})):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            env.slots.flags = flag_map
            seen = allow_seen(c)
            run_slot(env, c, env.window.start)
            assert env.slots.calls == ["flags", ("tickers", markets)] and env.books.symbols == [BTC]
            (book, options), = env.history.rows
            u = options["universe"]
            assert book is not None and options["trade_symbol"] == BTC
            assert options["tick_size"] == env.profile.instrument_rules.tick_size
            assert options["positions"] == c._latest_frame.accounts[0].positions
            assert u.snapshot is env.universe and u.allow == frozenset(allow) and u.reasons == () and u.events == ()
            s = c.status()
            assert (s.allow_count, s.buy_block_reasons, s.held_flag) == (len(allow), (), "unflagged")
            assert s.last_tick.status == "hold" and s.reasons == () and seen == [frozenset(allow)]


def test_a_stale_ticker_price_leaves_the_coin_out():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.slots.age = seconds(120)
        run_slot(env, c, env.window.start)
        assert env.history.rows[0][1]["universe"].allow == frozenset()


def test_a_failed_flag_or_ticker_read_blocks_buys_only():
    for failed, calls, reasons in (({"flags"}, ["flags"],
                                    ("UNIVERSE_FLAGS_UNAVAILABLE", "UNIVERSE_TICKERS_UNAVAILABLE")),
                                   ({"tickers"}, ["flags", ("tickers", (BTC, XRP))],
                                    ("UNIVERSE_TICKERS_UNAVAILABLE",))):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            env.slots.fail = failed
            seen = allow_seen(c)
            run_slot(env, c, env.window.start)
            u = env.history.rows[0][1]["universe"]
            assert env.slots.calls == calls and u.allow == frozenset() and u.reasons == reasons
            assert type(u.tickers) is TickerRead and not u.tickers.ok
            s = c.status()
            assert seen == [frozenset()] and s.last_tick.status == "hold" and s.buy_block_reasons == reasons
            assert not s.window_ended_missed_slot


def test_no_trade_book_records_the_slot_and_skips_the_tick():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.books.fail = True
        seen = allow_seen(c)
        run_slot(env, c, env.window.start)
        (book, options), = env.history.rows
        s = c.status()
        assert book is None and seen == [] and s.last_tick is None
        assert s.reasons == ("COORDINATOR_NO_TRADE_BOOK",) and not s.window_ended_missed_slot
        assert "BOOK-SECRET" not in repr(s)


def test_a_failed_record_skips_the_tick_and_ends_the_window():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.history.fail = FixtureRefusal("HISTORY_INPUT_REQUIRED")
        seen = allow_seen(c)
        run_slot(env, c, env.window.start)
        s = c.status()
        assert seen == [] and s.last_tick is None and s.window_ended_missed_slot and not c._runner.stopped
        assert s.reasons == ("HISTORY_INPUT_REQUIRED",) and c._toasted == {"missed"}


def test_an_off_tick_or_wrong_market_book_is_recorded_without_the_book_and_skips_the_tick():
    """PR 4d contract: these two refusals write nothing, so the slot is recorded again with book=None."""
    for code in ("HISTORY_BOOK_OFF_TICK", "HISTORY_BOOK_MARKET_MISMATCH"):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            record, books = env.history.record_slot, []

            def refusing(book, account, **options):
                books.append(book)
                if book is not None:
                    raise FixtureRefusal(code)
                return record(book, account, **options)
            env.history.record_slot = refusing
            seen = allow_seen(c)
            run_slot(env, c, env.window.start)
            (book, _), = env.history.rows
            s = c.status()
            assert books[0] is not None and books[1:] == [None] and book is None and seen == []
            assert s.reasons == ("COORDINATOR_NO_TRADE_BOOK",) and s.last_tick is None
            assert not s.window_ended_missed_slot and not c._runner.stopped
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.history.fail = FixtureRefusal("HISTORY_BOOK_OFF_TICK")     # the retry is refused too: the slot is missed
        run_slot(env, c, env.window.start)
        s = c.status()
        assert env.history.rows == [] and s.window_ended_missed_slot and s.reasons == ("HISTORY_BOOK_OFF_TICK",)


def test_terms_blocked_refuses_the_slot_only_while_a_coin_is_held():
    for positions, recorded in ((None, False), ([], True)):
        with universe_fixture() as env:
            c = build_universe(env)
            if positions is not None:
                reframe(c, positions)
            c.bootstrap()
            c._terms_blocked = True
            run_slot(env, c, env.window.start)
            s = c.status()
            if recorded:
                assert env.history.rows[0][1]["universe"].reasons == ("TERMS_TARGET_UNAVAILABLE",)
                assert s.last_tick.status == "hold" and not s.window_ended_missed_slot
            else:
                assert env.history.rows == [] and s.reasons == ("COORDINATOR_CURRENT_TERMS_REQUIRED",)
                assert s.window_ended_missed_slot and env.slots.calls == []


def test_an_extra_holding_blocks_buys():
    with universe_fixture() as env:
        c = build_universe(env)
        reframe(c, [position(BTC, "0.001", PRICE, env.fake.now), position(XRP, "100", "1000", env.fake.now)])
        c.bootstrap()
        seen = allow_seen(c)
        run_slot(env, c, env.window.start)
        u = env.history.rows[0][1]["universe"]
        assert u.allow == frozenset() and u.reasons == ("UNIVERSE_EXTRA_HOLDING",) and seen == [frozenset()]
        assert c.status().last_tick.status == "hold" and not c._runner.stopped


def test_a_trade_coin_below_its_buy_cap_is_left_out_of_the_allow_list():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        c.bootstrap()
        env.terms.within = False
        c.refresh_instrument_rules()
        run_slot(env, c, env.window.start)
        assert env.history.rows[0][1]["universe"].allow == frozenset({XRP})


def test_after_a_partial_sell_leaves_dust_the_next_slot_reads_and_allows_the_new_coin():
    """Spec section 19: a partial IOC sell leaves under 5,000 KRW of A, the monitor renews to B, and the next slot
    reads B's book, records B as the trade coin and allows B. The buy itself is not run here (the book double is a
    KRW-BTC book; runner buys are tested up to Controller.reserve in tests/launch_runner_universe.py)."""
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        reframe(c, [position(BTC, "0.00001", PRICE, env.fake.now)])       # 1,000 KRW of BTC left: dust
        env.history.decided = XRP
        c.bootstrap()
        assert c._profile.symbol == XRP
        run_slot(env, c, env.window.start)
        (_, options), = env.history.rows
        assert env.books.symbols == [XRP] and options["trade_symbol"] == XRP
        assert options["universe"].allow == frozenset({BTC, XRP})


def test_slot_allow_is_the_unflagged_priced_top_n_or_empty_with_reasons():
    at = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)
    snapshot = universe_snapshot(at)
    flags = FlagRead(ok=True, received_at=at, sha256="f" * 64,
                     flags=MappingProxyType({BTC: "unflagged", XRP: "unflagged"}))
    prices = TickerRead(ok=True, received_at=at, sha256="7" * 64,
                        prices=MappingProxyType({BTC: (PRICE, at - seconds(60)), XRP: (D(1000), at - seconds(61))}))
    common = dict(snapshot=snapshot, rule_sha256=RULE, flags=flags, tickers=prices, slot=at)
    assert C.slot_allow(n=2, **common) == (frozenset({BTC}), ())
    assert C.slot_allow(n=1, **(common | {"tickers": replace(prices, prices=MappingProxyType(
        {XRP: (D(1000), at)}))})) == (frozenset(), ())
    no_flags = FlagRead(ok=False, received_at=None, sha256=None, flags=MappingProxyType({}))
    no_prices = TickerRead(ok=False, received_at=None, sha256=None, prices=MappingProxyType({}))
    assert C.slot_allow(snapshot=None, rule_sha256=RULE, n=2, flags=no_flags, tickers=no_prices, slot=at,
                        blocks=("UNIVERSE_EXTRA_HOLDING",)) == (frozenset(), (
        "UNIVERSE_EXTRA_HOLDING", "UNIVERSE_NO_SNAPSHOT", "UNIVERSE_FLAGS_UNAVAILABLE", "UNIVERSE_TICKERS_UNAVAILABLE"))
    assert C.slot_allow(n=2, **(common | {"rule_sha256": "f" * 64})) == (frozenset(), ("UNIVERSE_RULE_MISMATCH",))


def test_a_vanished_held_coin_disarms_once_after_the_record_and_skips_the_tick():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        kills = stub_kill(c, True)
        reframe(c, [position(BTC, "0.001", "0", env.fake.now)])
        seen = allow_seen(c)
        run_slot(env, c, env.window.start)
        (_, options), = env.history.rows
        assert options["universe"].events == ("UNIVERSE_MARKET_VANISHED",)
        assert kills == ["market_vanished"] and seen == [] and c.status().strategy_stopped and c._disarmed
        assert c.status().reasons == ("COORDINATOR_UNIVERSE_DISARM",) and c._toasted == {"vanished"}


def test_a_failed_universe_disarm_is_sticky_and_the_row_is_still_recorded():
    """A kill that records no system disarm, and (spec section 19) Controller.kill raising inside _disarm_locked."""
    for raising in (False, True):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            kills = stub_kill(c, False)
            if raising:
                def kill(session_id, *, reason, now):
                    kills.append(reason)
                    raise FixtureRefusal("FIXTURE_KILL_FAILED")
                c._controller.kill = kill
            reframe(c, [position(BTC, "0.001", "0", env.fake.now)])
            run_slot(env, c, env.window.start)
            s = c.status()
            assert len(env.history.rows) == 1 and kills == ["market_vanished"] and s.strategy_stopped
            assert s.disarm_failed and c._toasted == {"disarm-failed"} and env.toasts.puts[0][0] == RED
            assert s.reasons == ("COORDINATOR_UNIVERSE_DISARM",) and s.last_tick is None


def test_a_slow_toast_never_delays_the_slot():
    with universe_fixture() as env:
        c = build_universe(env)
        reframe(c, [position(BTC, "0.001", PRICE, env.fake.now), position(XRP, "100", "1000", env.fake.now)])
        release, shown = threading.Event(), []
        c._toasts = ToastQueue(lambda title, body: release.wait(5) and shown.append(title))
        c.bootstrap()                                    # queues the extra-holding toast; the worker blocks in it
        worker = c._toasts._thread
        run_slot(env, c, env.window.start)
        assert len(env.history.rows) == 1 and c.status().last_tick.status == "hold"
        assert shown == [] and worker.is_alive()
        release.set()
        worker.join(5)
        assert shown == [RED]


def test_a_failing_event_sets_a_reason_and_a_toast_and_the_tick_still_runs():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.slots.flags = {BTC: "unflagged", XRP: "unflagged", ETH: "warning"}
        reframe(c, [position(BTC, "0.001", PRICE, env.fake.now), position(ETH, "0.0001", "1000", env.fake.now)])
        toast_once = c._toast_once

        def failing(key, level, body):
            if key.startswith("warning:"):
                raise RuntimeError("TOAST-SECRET-1")
            toast_once(key, level, body)
        c._toast_once = failing
        run_slot(env, c, env.window.start)
        s = c.status()
        assert env.history.rows[0][1]["universe"].events == ("UNIVERSE_OTHER_COIN_WARNING",)
        assert s.reasons == ("COORDINATOR_EVENT_FAILED",) and s.last_tick.status == "hold"
        assert [k for k in c._toasted if k.startswith("event-failed:UNIVERSE_OTHER_COIN_WARNING:")]
        assert "TOAST-SECRET" not in repr(s)


def test_an_uncertain_held_flag_blocks_buys_and_forces_no_sale():
    for flag_map, held_flag in (({XRP: "unflagged"}, "absent"), ({BTC: "unknown", XRP: "unflagged"}, "unknown")):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            env.slots.flags = flag_map
            seen = allow_seen(c)
            run_slot(env, c, env.window.start)
            u = env.history.rows[0][1]["universe"]
            assert u.events == ("UNIVERSE_HELD_FLAG_UNCERTAIN",) and u.allow == frozenset()
            assert u.reasons == ("UNIVERSE_HELD_FLAG_UNCERTAIN",) and seen == [frozenset()]
            assert c.status().held_flag == held_flag and env.adapter.requests == []
            assert [k for k in c._toasted if k.startswith("held-flag:")]


def test_two_hold_ticks_on_another_decision_set_the_remainder_block():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        env.history.decided = XRP                 # each tick acts on a decision for another coin and holds
        for k in range(3):
            run_slot(env, c, env.window.start + seconds(60 * k))
        reasons = [options["universe"].reasons for _, options in env.history.rows]
        assert reasons == [(), (), ("UNIVERSE_REMAINDER_UNSELLABLE",)]
        assert c._remainder and [k for k in c._toasted if k.startswith("remainder:")]


def test_a_failed_record_still_runs_the_events():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        kills = stub_kill(c, True)
        env.history.fail = FixtureRefusal("HISTORY_INPUT_REQUIRED")
        reframe(c, [position(BTC, "0.001", "0", env.fake.now)])
        run_slot(env, c, env.window.start)
        s = c.status()
        assert kills == ["market_vanished"] and env.history.rows == [] and s.window_ended_missed_slot
        assert s.reasons == ("HISTORY_INPUT_REQUIRED", "COORDINATOR_UNIVERSE_DISARM")


def test_a_suspend_that_misses_slots_sets_the_sticky_field_and_one_toast():
    with universe_fixture() as env:
        c = build_universe(env)
        env.fake.at(env.t0 + seconds(50), lambda: setattr(env.fake, "now", env.fake.now + seconds(120)))
        status = c.run()
        assert status.missed_slots == 2 and status.window_ended_missed_slot and "missed" in c._toasted
    with universe_fixture() as env:
        c = build_universe(env)
        status = c.run()
        assert status.missed_slots == 0 and not status.window_ended_missed_slot and len(env.history.rows) == 3
        assert "missed" not in c._toasted


def test_the_odds_batch_runs_off_the_work_lock_over_the_snapshot_top_n():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        seen, result = [], []

        def read_bars(markets, *, now, clock):
            seen.append(("bars", markets, now))
            return {"bars": markets}

        def run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof):
            seen.append(("batch", controller is c._controller, template, bars, n, now))
            return "BATCH"
        with patch.object(C, "run_batch", run_batch), c._work:
            worker = threading.Thread(target=lambda: result.append(c.odds_batch("TEMPLATE", read_bars)))
            worker.start()
            worker.join(5)
        now = seen[0][2]
        assert result == ["BATCH"]
        assert seen[0] == ("bars", (BTC, XRP), now)
        assert seen[1][:-1] == ("batch", True, "TEMPLATE", {"bars": (BTC, XRP)}, 2)
        assert seen[1][-1] >= now                 # fresh post-I/O clock, never the prefetch timestamp

        def broken(markets, *, now, clock):
            raise RuntimeError("CANDLE-SECRET-1")
        refused(lambda: c.odds_batch("TEMPLATE", broken), "COORDINATOR_ODDS_BATCH_FAILED")
    with universe_fixture() as env:
        refused(lambda: build_universe(env).odds_batch("TEMPLATE", None), "UNIVERSE_NO_SNAPSHOT")
    with fixture() as env:
        refused(lambda: build(env).odds_batch("TEMPLATE", None), "COORDINATOR_UNIVERSE_REQUIRED")


def test_prepare_passes_the_batch_to_prepare_launch_session():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        seen = []

        def prepare(**kwargs):
            seen.append(kwargs["universe_batch"])
            raise FixtureRefusal("FIXTURE_PREPARE_REACHED")
        plan, inputs, seed = selected(env.fake.now)
        with patch.object(C, "prepare_launch_session", prepare):
            refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed,
                                      universe_batch="BATCH"), "FIXTURE_PREPARE_REACHED")
            refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed),
                    "FIXTURE_PREPARE_REACHED")
        assert seen == ["BATCH", None]



def test_exact_holding_value_breaks_a_decimal_context_rounded_tie():
    """Synthetic adjacent values whose products round to the same value in the default Decimal context."""
    from decimal import localcontext
    at = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)
    account = SimpleNamespace(positions=(
        position(BTC, "1000000000000", "1000000000000", at),
        position(XRP, "1000000000000.0000000000000001", "1000000000000", at)))
    with localcontext() as ctx:
        ctx.prec = 28
        assert account.positions[0].units * account.positions[0].price == account.positions[1].units * account.positions[1].price
        assert C.held_coins(account, D("5000")) == (XRP, BTC)


def test_notification_queue_failure_does_not_prevent_record_or_disarm():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        kills = stub_kill(c, True)
        reframe(c, [position(BTC, "0.001", "0", env.fake.now)])

        def fail_queue(*args):
            raise RuntimeError("PRIVATE-NOTIFICATION-ERROR")
        c._toasts = SimpleNamespace(put=fail_queue)
        seen = allow_seen(c)
        run_slot(env, c, env.window.start)
        assert len(env.history.rows) == 1 and kills == ["market_vanished"] and seen == []
        assert c.status().notification_failed and c.status().strategy_stopped
        assert not c.status().disarm_failed and env.adapter.requests == []
        assert "PRIVATE-NOTIFICATION" not in repr(c.status())


def test_unrelated_inactive_terms_do_not_mark_a_different_held_coin_vanished():
    with universe_fixture() as env, renewals(env):
        c = build_universe(env)
        c.bootstrap()
        c._held = (XRP,)               # restart has not yet switched the trade coin from BTC
        env.terms.fail = FixtureRefusal("TERMS_MARKET_INACTIVE")
        refused(c.refresh_instrument_rules, "TERMS_MARKET_INACTIVE")
        assert env.terms.reads == [BTC] and not c._vanished and c._terms_blocked
        assert env.adapter.requests == []


def test_explicit_capture_updates_holding_facts_before_its_action():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        reframe(c, [position(BTC, "0.001", "0", env.fake.now)])
        facts = []
        c._explicit(lambda now: facts.append((c._held, c._vanished)), with_book=False)
        assert facts == [((), True)] and c.status().held_symbol is None
        assert env.adapter.requests == []


def test_history_failure_keeps_entry_blocked_and_phase_monitoring_after_valid_monitors():
    from tests.launch_coordinator import observe_at
    with universe_fixture() as env:
        c = build_universe(env)
        env.history.fail = FixtureRefusal("HISTORY_STORAGE_LIMIT_EXCEEDED")
        observed = observe_at(env, c, 90, 150)
        c.run()
        for state in observed.values():
            assert state.window_ended_missed_slot and state.new_entry_blocked and state.strategy_stopped
            assert state.phase == "monitoring"
        assert observed[150].published_units > observed[90].published_units
        assert len(env.books.symbols) == 1 and env.adapter.requests == []


def test_deadline_notice_requests_management_without_extending_permissions_or_orders():
    """Only the notification/monitor handler: the terminal driver behavior needs its separate versioned revision."""
    with universe_fixture() as env:
        c = build_universe(env)
        env.fake.now = env.window.end + seconds(11)
        end = c._window.end
        c.bootstrap()
        env.fake.now += seconds(20)
        c._monitor("monitor")
        assert c._window.end == end and c.status().new_entry_blocked
        assert len(env.toasts.puts) == 1 and "new management approval" in env.toasts.puts[0][1]
        assert env.adapter.requests == [] and env.decisions == []
        plan, inputs, seed = selected(env.fake.now)
        refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed),
                "COORDINATOR_MANAGEMENT_RENEWAL_REQUIRED")


def test_vanish_without_a_prepared_session_does_not_claim_a_recorded_disarm():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        assert c._launch is None
        kills = []
        c._controller.kill = lambda *args, **kwargs: kills.append(args)
        with c._work:
            c._vanish()
        assert kills == [] and c.status().strategy_stopped and not c.status().disarm_failed
        assert len(env.toasts.puts) == 1 and "Check the reported session disarm status" in env.toasts.puts[0][1]
        assert "session disarmed" not in env.toasts.puts[0][1] and env.adapter.requests == []
