"""Acceptance checks for the rule engine, written against the service contract.

Each test names the clause it defends. These are the properties a client is
buying — "시작 시 비활성", "중복 처리 방지", "재시작 후 자동 재활성화 방지" —
so each one gets a test that fails loudly rather than a comment saying it is
handled.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from core.engine import (EngineMode, EngineState, Evaluator, HaltReason,
                         OrderBook, OrderStatus, Outcome, Quote)
from core.rules import (CancelCondition, Comparator, Limits, OrderKind,
                        PriceCondition, Rule, RuleStatus, Side, SizeMode,
                        validate)

NOW = datetime(2026, 8, 18, 6, 0, tzinfo=timezone.utc)


def _rule(**over) -> Rule:
    base = dict(
        name="test rule", symbol="005930", market="KRX", side=Side.BUY,
        size_mode=SizeMode.QUANTITY, size_value=Decimal(10),
        order_kind=OrderKind.MARKET,
        conditions=(PriceCondition(Comparator.AT_OR_BELOW, Decimal(70000)),),
        limits=Limits(max_triggers=3, max_order_amount=Decimal(10_000_000)),
        status=RuleStatus.ACTIVE,
    )
    base.update(over)
    return Rule(**base)


def _quote(price=68000, previous=None, age_s=0) -> Quote:
    return Quote("005930", Decimal(price),
                 Decimal(previous) if previous is not None else None,
                 NOW - timedelta(seconds=age_s), "test")


def _armed() -> tuple[EngineState, OrderBook, Evaluator]:
    state = EngineState()
    state.arm()
    book = OrderBook()
    return state, book, Evaluator(state, book)


# --------------------------------------------------------------------------- #
# §5 — start disarmed, manual re-arm, emergency stop
# --------------------------------------------------------------------------- #
def test_01_engine_starts_disarmed():
    assert EngineState().mode is EngineMode.DISARMED


def test_02_halt_requires_manual_acknowledgement_before_arming():
    state = EngineState()
    state.arm()
    state.halt(HaltReason.STALE_DATA, "quote 400s old")
    assert state.mode is EngineMode.HALTED
    ok, message = state.arm()
    assert not ok and "Acknowledge" in message
    state.acknowledge()
    assert state.mode is EngineMode.DISARMED, "acknowledging must not arm"
    ok, _ = state.arm()
    assert ok and state.is_armed


def test_03_restart_never_restores_armed():
    state = EngineState()
    state.arm()
    snapshot = state.snapshot()
    assert "mode" not in snapshot, "persisting the mode would re-arm on launch"
    restored = EngineState()
    restored.restore(snapshot)
    assert restored.mode is EngineMode.DISARMED


def test_04_unacknowledged_halt_survives_a_restart():
    state = EngineState()
    state.arm()
    state.halt(HaltReason.LIMIT_BREACH, "daily cap")
    restored = EngineState()
    restored.restore(state.snapshot())
    assert restored.requires_manual_rearm
    ok, _ = restored.arm()
    assert not ok, "a restart must not launder away an unacknowledged halt"


def test_05_emergency_stop_works_from_any_state_and_never_raises():
    for setup in (lambda s: None, lambda s: s.arm(),
                  lambda s: (s.arm(), s.halt())):
        state = EngineState()
        setup(state)
        state.halt(HaltReason.OPERATOR, "kill switch")
        state.halt(HaltReason.OPERATOR, "pressed twice")   # idempotent
        assert state.mode is EngineMode.HALTED


# --------------------------------------------------------------------------- #
# §3, §5 — guards
# --------------------------------------------------------------------------- #
def test_06_disarmed_engine_never_fires():
    state, book, ev = EngineState(), OrderBook(), None
    ev = Evaluator(state, book)
    decision = ev.evaluate(_rule(), _quote(), now=NOW)
    assert decision.outcome is Outcome.SKIPPED
    assert not book.all()


def test_07_stale_quote_halts_the_engine():
    state, book, ev = _armed()
    decision = ev.evaluate(_rule(), _quote(age_s=600), now=NOW)
    assert decision.outcome is Outcome.HALTED
    assert state.mode is EngineMode.HALTED
    assert state.halt_reason is HaltReason.STALE_DATA


def test_08_missing_quote_halts_rather_than_skipping():
    state, book, ev = _armed()
    decision = ev.evaluate(_rule(), None, now=NOW)
    assert decision.outcome is Outcome.HALTED
    assert state.halt_reason is HaltReason.NO_DATA


def test_09_duplicate_trigger_is_not_placed_twice():
    state, book, ev = _armed()
    rule = _rule()
    first = ev.evaluate(rule, _quote(), now=NOW)
    assert first.fired
    second = ev.evaluate(rule, _quote(), now=NOW)   # same trigger sequence
    assert second.outcome is Outcome.SKIPPED
    assert "already placed" in second.reason
    assert len(book.all()) == 1


def test_10_max_triggers_rejects_with_a_reason():
    state, book, ev = _armed()
    rule = _rule(limits=Limits(max_triggers=1), trigger_count=1)
    decision = ev.evaluate(rule, _quote(), now=NOW)
    assert decision.outcome is Outcome.REJECTED
    assert "already fired" in decision.reason
    assert book.all()[0].status is OrderStatus.REJECTED


def test_11_per_order_cap_rejects():
    state, book, ev = _armed()
    rule = _rule(limits=Limits(max_order_amount=Decimal(100_000)))
    decision = ev.evaluate(rule, _quote(price=68000), now=NOW)   # 10 x 68000
    assert decision.outcome is Outcome.REJECTED
    assert "exceeds this rule's maximum" in decision.reason


def test_12_daily_cap_counts_prior_orders():
    state, book, ev = _armed()
    rule = _rule(limits=Limits(max_daily_amount=Decimal(1_000_000)))
    first = ev.evaluate(rule, _quote(), now=NOW)
    assert first.fired
    nxt = rule.record_trigger()
    second = ev.evaluate(nxt, _quote(), now=NOW)
    assert second.outcome is Outcome.REJECTED
    assert "daily maximum" in second.reason


def test_13_rejected_orders_do_not_consume_the_daily_budget():
    book = OrderBook()
    state = EngineState(); state.arm()
    ev = Evaluator(state, book)
    rule = _rule(limits=Limits(max_order_amount=Decimal(1)))
    ev.evaluate(rule, _quote(), now=NOW)
    assert book.notional_today(now=NOW) == Decimal(0)


def test_14_a_skip_explains_itself():
    state, book, ev = _armed()
    rule = _rule(conditions=(PriceCondition(Comparator.AT_OR_BELOW, Decimal(60000)),))
    decision = ev.evaluate(rule, _quote(price=68000), now=NOW)
    assert decision.outcome is Outcome.SKIPPED
    assert "not met" in decision.reason and "60,000" in decision.reason


def test_15_closed_window_skips():
    state, book, ev = _armed()
    rule = _rule(valid_to=NOW - timedelta(hours=1))
    assert ev.evaluate(rule, _quote(), now=NOW).reason == "validity window has closed"


def test_16_crossing_needs_a_previous_observation():
    state, book, ev = _armed()
    rule = _rule(conditions=(PriceCondition(Comparator.CROSSES_DOWN, Decimal(69000)),))
    assert not ev.evaluate(rule, _quote(price=68000, previous=None), now=NOW).fired
    state2, book2, ev2 = _armed()
    assert ev2.evaluate(rule, _quote(price=68000, previous=70000), now=NOW).fired


def test_17_notional_sizing_rejects_when_below_one_share():
    state, book, ev = _armed()
    rule = _rule(size_mode=SizeMode.NOTIONAL, size_value=Decimal(1000),
                 limits=Limits())
    decision = ev.evaluate(rule, _quote(price=68000), now=NOW)
    assert decision.outcome is Outcome.REJECTED
    assert "smaller than one share" in decision.reason


# --------------------------------------------------------------------------- #
# §3 — simulated order lifecycle
# --------------------------------------------------------------------------- #
def test_18_orders_do_not_fill_themselves():
    state, book, ev = _armed()
    ev.evaluate(_rule(), _quote(), now=NOW)
    assert book.open_orders(), "a placed order must rest until acted on"
    assert all(o.status is OrderStatus.OPEN for o in book.all())


def test_19_manual_fill_and_double_settle_is_refused():
    state, book, ev = _armed()
    decision = ev.evaluate(_rule(), _quote(), now=NOW)
    ok, _ = book.fill(decision.order.id, Decimal(68000))
    assert ok and book.get(decision.order.id).status is OrderStatus.FILLED
    ok, message = book.cancel(decision.order.id)
    assert not ok and "already filled" in message


def test_20_practice_reset_clears_the_book():
    state, book, ev = _armed()
    ev.evaluate(_rule(), _quote(), now=NOW)
    book.reset()
    assert not book.all()


def test_21_cancel_sweep_applies_the_rules_own_condition():
    state, book, ev = _armed()
    rule = _rule(cancel=CancelCondition(after_seconds=1))
    decision = ev.evaluate(rule, _quote(), now=NOW)
    assert decision.fired
    # Age the order past its cancel window.
    from dataclasses import replace
    book._orders[decision.order.id] = replace(
        decision.order, created_at=NOW - timedelta(seconds=30))
    ev.sweep_cancellations({rule.id: rule}, {"005930": _quote()}, now=NOW)
    assert book.get(decision.order.id).status is OrderStatus.CANCELLED


# --------------------------------------------------------------------------- #
# §1, §2 — the rule is the operator's, and validation says so
# --------------------------------------------------------------------------- #
def test_22_a_new_rule_has_no_decision_defaults():
    blank = Rule()
    for attribute in ("side", "size_mode", "size_value", "order_kind", "limit_price"):
        assert getattr(blank, attribute) is None, \
            f"{attribute} has a default; the program must not choose it"
    assert blank.conditions == ()
    assert blank.limits.empty


def test_23_validation_reports_every_field_at_once():
    report = validate(Rule())
    fields = {i.field for i in report.errors}
    assert {"name", "symbol", "side", "size_value", "order_kind",
            "conditions"} <= fields
    assert not report.ok


def test_24_validation_never_suggests_a_value():
    report = validate(Rule())
    for issue in report.issues:
        text = issue.message.lower()
        for banned in ("try ", "we recommend", "suggested", "typically",
                       "usually", "e.g.", "for example"):
            assert banned not in text, f"validation hints a value: {issue.message}"


def test_25_contradictory_and_conditions_are_rejected():
    rule = _rule(conditions=(
        PriceCondition(Comparator.AT_OR_BELOW, Decimal(60000)),
        PriceCondition(Comparator.AT_OR_ABOVE, Decimal(70000)),
    ), require_all_conditions=True)
    report = validate(rule)
    assert not report.ok
    assert any("cannot all be true" in i.message for i in report.errors)


def test_26_editing_a_decision_field_revokes_confirmation():
    rule = _rule(status=RuleStatus.DRAFT).confirm()
    assert rule.is_confirmed
    edited = rule.edit(size_value=Decimal(20))
    assert edited.status is RuleStatus.DRAFT and edited.confirmed_at is None
    assert edited.revision == rule.revision + 1


def test_27_renaming_does_not_revoke_confirmation():
    rule = _rule(status=RuleStatus.DRAFT).confirm()
    renamed = rule.edit(name="clearer name")
    assert renamed.is_confirmed, "cosmetic edits must not train click-through"


def test_28_exhausting_max_triggers_changes_status():
    rule = _rule(limits=Limits(max_triggers=2))
    assert rule.record_trigger().status is RuleStatus.ACTIVE
    assert rule.record_trigger().record_trigger().status is RuleStatus.EXHAUSTED


def test_29_summary_reads_back_what_was_entered():
    text = _rule().summary()
    assert "005930" in text and "BUY" in text and "70,000" in text


# --------------------------------------------------------------------------- #
# Runtime — persistence, restart behaviour, concurrency
# --------------------------------------------------------------------------- #
# 11:00 KST on a Wednesday: KRX is open, so a fresh quote is evaluable.
# Freshness is judged against the venue's session, so these tests pin the clock
# rather than depending on when the suite happens to run.
TRADING_NOW = datetime(2026, 8, 19, 2, 0, tzinfo=timezone.utc)


def _runtime(tmp, price=68000):
    """A runtime wired to a fake gateway that always quotes `price` fresh."""
    from core.engine.feed import QuoteFeed
    from core.engine.runtime import EngineRuntime
    from core.rules.store import RuleStore

    class _Answer:
        def __init__(self, data, source):
            self.data, self.source, self.ok, self.reason = data, source, True, ""
        def __bool__(self):
            return True

    class _Quote:
        def __init__(self, p):
            self.price = p
            self.as_of = TRADING_NOW.isoformat()

    class _Gateway:
        def quote(self, ticker):
            return _Answer(_Quote(price), "TEST")

    store = RuleStore(tmp / "rules.json")
    runtime = EngineRuntime(store, QuoteFeed(_Gateway()), tick_seconds=999,
                            state_path=tmp / "engine.json",
                            clock=lambda: TRADING_NOW)
    return store, runtime


def _tmpdir():
    import tempfile
    from pathlib import Path
    return Path(tempfile.mkdtemp())


def test_30_runtime_increments_trigger_count_once_per_fire():
    tmp = _tmpdir()
    store, runtime = _runtime(tmp)
    rule = store.save(_rule(limits=Limits(max_triggers=5)))
    runtime.state.arm()                     # arm without starting the loop
    try:
        assert runtime.tick()[0].fired
        assert store.get(rule.id).trigger_count == 1
    finally:
        runtime.stop()


def test_31_concurrent_ticks_cannot_double_place():
    """Two overlapping passes must not place the same logical trigger twice.

    Regression: `arm()` starts the background loop, so a UI-initiated tick can
    run concurrently with a loop tick. Both read the same trigger_count, build
    the same order id, and without an atomic place() both inserted it.

    The pass that wins the tick lock is held open inside the quote fetch until
    the other seven ticks have bounced off the lock and returned. Without that
    gate the eight ticks only overlap by luck: under CPU load a thread starts
    after the first pass has finished, runs a legitimate *second* pass, and
    fires trigger 2 -- a different id, not a duplicate -- so the test failed
    while the engine was behaving correctly.
    """
    import threading
    tmp = _tmpdir()
    store, runtime = _runtime(tmp)
    store.save(_rule(limits=Limits()))
    runtime.state.arm()
    returned = threading.Semaphore(0)
    fetch = runtime.feed.fetch_many

    def gated_fetch(pairs):
        for _ in range(7):
            assert returned.acquire(timeout=10), "a sibling tick never returned"
        return fetch(pairs)
    runtime.feed.fetch_many = gated_fetch

    def attempt():
        runtime.tick()
        returned.release()
    try:
        threads = [threading.Thread(target=attempt) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(runtime.book.all()) == 1, (
            f"expected one order, got {len(runtime.book.all())}")
    finally:
        runtime.stop()


def test_32_order_book_place_refuses_a_duplicate_id():
    from dataclasses import replace
    book = OrderBook()
    state = EngineState(); state.arm()
    ev = Evaluator(state, book)
    decision = ev.evaluate(_rule(), _quote(), now=NOW)
    assert book.place(replace(decision.order, status=OrderStatus.OPEN)) is None


def test_33_restart_reloads_the_book_but_not_the_armed_mode():
    tmp = _tmpdir()
    store, runtime = _runtime(tmp)
    store.save(_rule(limits=Limits()))
    runtime.state.arm()
    try:
        runtime.tick()
        placed = len(runtime.book.all())
        assert placed == 1
    finally:
        runtime.stop()
    _store2, restored = _runtime(tmp)
    try:
        assert restored.mode is EngineMode.DISARMED
        assert len(restored.book.all()) == placed
    finally:
        restored.stop()


def test_34_disarmed_runtime_fires_nothing():
    tmp = _tmpdir()
    store, runtime = _runtime(tmp)
    store.save(_rule(limits=Limits()))
    try:
        assert all(not d.fired for d in runtime.tick())
        assert not runtime.book.all()
    finally:
        runtime.stop()


def test_35_feed_refuses_to_invent_a_timestamp():
    """A provider row with no `as_of` must read as missing data, not as fresh.

    Stamping it with "now" would defeat the staleness guard completely.
    """
    from core.engine.feed import QuoteFeed

    class _Answer:
        def __init__(self, data):
            self.data, self.source, self.ok, self.reason = data, "TEST", True, ""
        def __bool__(self):
            return True

    class _Undated:
        price = 68000
        as_of = ""

    class _Gateway:
        def quote(self, ticker):
            return _Answer(_Undated())

    feed = QuoteFeed(_Gateway())
    assert feed.fetch("005930", "KRX") is None
    assert "timestamp" in feed.last_error("005930")


def test_36_feed_tracks_previous_price_for_crossings():
    from core.engine.feed import QuoteFeed

    prices = iter([70000, 68000])

    class _Answer:
        def __init__(self, data):
            self.data, self.source, self.ok, self.reason = data, "TEST", True, ""
        def __bool__(self):
            return True

    class _Q:
        def __init__(self, p):
            self.price = p
            self.as_of = datetime.now(timezone.utc).isoformat()

    class _Gateway:
        def quote(self, ticker):
            return _Answer(_Q(next(prices)))

    feed = QuoteFeed(_Gateway())
    first = feed.fetch("005930", "KRX")
    second = feed.fetch("005930", "KRX")
    assert first.previous is None
    assert second.previous == Decimal(70000)


def test_37_unrouted_market_is_missing_data_not_a_crash():
    from core.engine.feed import QuoteFeed
    feed = QuoteFeed(None)
    assert feed.fetch("AAPL", "NASDAQ") is None
    assert "NASDAQ" in feed.last_error("AAPL")


def test_38_rule_store_round_trips_decimals_exactly():
    from core.rules.store import RuleStore
    tmp = _tmpdir()
    store = RuleStore(tmp / "rules.json")
    rule = store.save(_rule(order_kind=OrderKind.LIMIT,
                            limit_price=Decimal("68000.55")))
    reloaded = RuleStore(tmp / "rules.json").get(rule.id)
    assert reloaded.limit_price == Decimal("68000.55")


def test_39_saving_a_new_revision_keeps_the_previous_one():
    from core.rules.store import RuleStore
    tmp = _tmpdir()
    store = RuleStore(tmp / "rules.json")
    rule = store.save(_rule())
    store.save(rule.edit(size_value=Decimal(99)))
    history = store.history(rule.id)
    assert len(history) == 1 and history[0]["size_value"] == "10"


# --------------------------------------------------------------------------- #
# Market routing and the FMP provider
# --------------------------------------------------------------------------- #
class _FakeFMP:
    """Stands in for FMPQuoteClient with the same surface the feed uses."""

    def __init__(self, rows=None, error=None, blocked=None):
        self._rows = rows or {}
        self._error = error
        self._blocked = blocked or {}
        self.calls = []
        self.ready = True

    def status(self):
        return {"ready": True, "reason": "", "detail": "fake"}

    def error_for(self, symbol):
        return self._blocked.get(symbol.upper(), "")

    def plan_blocked(self):
        return dict(self._blocked)

    def quotes(self, symbols):
        self.calls.append(list(symbols))
        if self._error:
            raise RuntimeError(self._error)
        return {s.upper(): self._rows[s.upper()]
                for s in symbols if s.upper() in self._rows}


def _fmp_row(symbol, price, *, as_of=None):
    from data.fmp import FMPQuote
    stamp = as_of if as_of is not None else datetime.now(timezone.utc).isoformat()
    return FMPQuote(symbol=symbol, name=symbol, price=price, change=None,
                    change_pct=None, volume=None, market_cap=None, high=None,
                    low=None, open=None, previous_close=None,
                    exchange="TEST", as_of=stamp)


def test_40_market_registry_routes_every_offered_code():
    """The builder must not offer a venue the feed cannot route."""
    from core import markets
    for code in markets.codes():
        assert markets.provider_for(code) in (markets.KRX, markets.FMP), code


def test_41_provider_symbol_applies_a_suffix_once():
    from core import markets
    assert markets.provider_symbol("US", "AAPL") == "AAPL"
    assert markets.provider_symbol("TSE", "7203") == "7203.T"
    assert markets.provider_symbol("TSE", "7203.T") == "7203.T"      # idempotent
    assert markets.provider_symbol("TSE", "7203.t") == "7203.t"      # case-insensitive
    assert markets.provider_symbol("KRX", "005930") == "005930"


def test_42_unknown_market_is_reported_not_crashed():
    from core.engine.feed import QuoteFeed
    feed = QuoteFeed()
    assert feed.fetch("AAPL", "MARS") is None
    assert "not a known venue" in feed.last_error("AAPL")


def test_43_feed_maps_provider_symbols_back_to_the_rules_own_symbol():
    """A rule stores `7203`; FMP is asked for `7203.T`; the result must come
    back under `7203`, because that is the key the engine looks up."""
    from core.engine.feed import QuoteFeed
    fake = _FakeFMP({"7203.T": _fmp_row("7203.T", 2800.0)})
    feed = QuoteFeed(fmp_client=fake)
    quotes = feed.fetch_many([("7203", "TSE")])
    assert fake.calls == [["7203.T"]]
    assert quotes["7203"] is not None
    assert quotes["7203"].price == Decimal("2800.0")


def test_44_feed_groups_all_fmp_symbols_into_one_provider_call():
    from core.engine.feed import QuoteFeed
    fake = _FakeFMP({"AAPL": _fmp_row("AAPL", 100.0),
                     "MSFT": _fmp_row("MSFT", 200.0)})
    feed = QuoteFeed(fmp_client=fake)
    feed.fetch_many([("AAPL", "US"), ("MSFT", "US")])
    assert len(fake.calls) == 1, "the feed must hand the provider one list"
    assert sorted(fake.calls[0]) == ["AAPL", "MSFT"]


def test_45_plan_refusal_is_reported_verbatim_not_as_no_row():
    """A 402 must not surface as "no row" — the operator needs the real cause."""
    from core.engine.feed import QuoteFeed
    fake = _FakeFMP(rows={"AAPL": _fmp_row("AAPL", 100.0)},
                    blocked={"VOD.L": "FMP plan does not cover VOD.L (HTTP 402)."})
    feed = QuoteFeed(fmp_client=fake)
    quotes = feed.fetch_many([("AAPL", "US"), ("VOD", "LSE")])
    assert quotes["VOD"] is None
    assert "402" in feed.last_error("VOD")


def test_46_fmp_quote_without_a_timestamp_is_missing_data():
    from core.engine.feed import QuoteFeed
    fake = _FakeFMP({"AAPL": _fmp_row("AAPL", 100.0, as_of="")})
    feed = QuoteFeed(fmp_client=fake)
    assert feed.fetch("AAPL", "US") is None
    assert "timestamp" in feed.last_error("AAPL")


def test_47_fmp_client_never_leaks_the_key_in_an_error():
    from data.fmp.quote_client import _redact
    key = "vvtSECRETKEY1234567890abcdef"
    text = f"https://x/quote?symbol=A&apikey={key} failed"
    assert key not in _redact(text, key)
    assert "***" in _redact(text, key)


def test_48_fmp_client_throttles_repeat_fetches_of_one_symbol():
    """A 5s engine tick must not become a request per tick per symbol."""
    from data.fmp.quote_client import FMPQuoteClient
    now = [1000.0]
    client = FMPQuoteClient(api_key="k", min_interval_s=20,
                            clock=lambda: now[0])
    hits = []

    def fake_fetch(symbol):
        hits.append(symbol)
        return _fmp_row(symbol, 100.0)

    client._fetch_one = fake_fetch
    client.quotes(["AAPL"])
    now[0] += 5
    client.quotes(["AAPL"])          # inside the window -> cache
    assert hits == ["AAPL"]
    now[0] += 30                     # past the window -> refetch
    client.quotes(["AAPL"])
    assert hits == ["AAPL", "AAPL"]


def test_49_a_plan_blocked_symbol_is_not_retried_every_tick():
    from data.fmp.quote_client import FMPQuoteClient, FMPPlanError
    client = FMPQuoteClient(api_key="k")
    attempts = []

    def fake_fetch(symbol):
        attempts.append(symbol)
        raise FMPPlanError("HTTP 402")

    client._fetch_one = fake_fetch
    for _ in range(5):
        try:
            client.quotes(["VOD.L"])
        except Exception:
            pass
    assert len(attempts) == 1, "a subscription refusal is not a transient error"


def test_50_fmp_cache_window_cannot_outlast_the_staleness_guard():
    """If the throttle exceeded the staleness bound, the cache itself could
    make a quote stale and halt the engine."""
    import config
    assert config.FMP_MIN_INTERVAL_SECONDS < config.QUOTE_MAX_AGE_SECONDS


# --------------------------------------------------------------------------- #
# Per-market trading sessions and freshness
# --------------------------------------------------------------------------- #
KST = timezone(timedelta(hours=9))


def _mrule(market, symbol="AAPL"):
    return Rule(name="t", symbol=symbol, market=market, side=Side.BUY,
                size_mode=SizeMode.QUANTITY, size_value=Decimal(1),
                order_kind=OrderKind.MARKET,
                conditions=(PriceCondition(Comparator.AT_OR_BELOW,
                                           Decimal(10 ** 9)),),
                limits=Limits(), status=RuleStatus.ACTIVE)


def _mquote(as_of, symbol="AAPL"):
    return Quote(symbol, Decimal(300), None, as_of, "TEST")


def _judge(market, now, as_of, symbol="AAPL"):
    state = EngineState(); state.arm()
    book = OrderBook()
    decision = Evaluator(state, book).evaluate(
        _mrule(market, symbol), _mquote(as_of, symbol), now=now)
    return decision, state


def test_51_us_rule_does_not_halt_overnight():
    """The regression this whole feature exists for.

    09:00 KST is 20:00 ET the previous day. The quote is the US close, hours
    old and entirely correct. A single global age bound halted here every night.
    """
    decision, state = _judge(
        "US",
        datetime(2026, 8, 19, 9, 0, tzinfo=KST),
        datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc))
    assert decision.outcome is Outcome.SKIPPED
    assert state.mode is EngineMode.ARMED, "an overnight quote must not halt"
    assert "closed" in decision.reason


def test_52_fresh_quote_inside_the_session_fires():
    decision, state = _judge(
        "US",
        datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc),      # 11:00 ET
        datetime(2026, 8, 18, 14, 59, 30, tzinfo=timezone.utc))
    assert decision.fired and state.mode is EngineMode.ARMED


def test_53_frozen_feed_during_a_session_still_halts():
    """Loosening the bound must not cost us outage detection."""
    decision, state = _judge(
        "US",
        datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 18, 14, 40, tzinfo=timezone.utc))     # 20 min
    assert decision.outcome is Outcome.HALTED
    assert state.mode is EngineMode.HALTED


def test_54_no_print_this_session_skips_rather_than_halting():
    """Holiday or venue outage. A halt is global; the problem is one venue, so
    a US holiday must not stop Korean rules."""
    decision, state = _judge(
        "US",
        datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 17, 20, 0, tzinfo=timezone.utc))
    assert decision.outcome is Outcome.SKIPPED
    assert state.mode is EngineMode.ARMED
    assert "before today" in decision.reason


def test_55_a_truly_dead_feed_still_halts():
    """The backstop: no calendar explains nine days."""
    decision, state = _judge(
        "US",
        datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 9, 15, 0, tzinfo=timezone.utc))
    assert decision.outcome is Outcome.HALTED
    assert state.mode is EngineMode.HALTED


def test_56_a_lunch_break_is_not_a_frozen_feed():
    """Tokyo stops for an hour. Reading that as a stale feed halted every day."""
    decision, state = _judge(
        "TSE",
        datetime(2026, 8, 18, 3, 0, tzinfo=timezone.utc),       # 12:00 JST
        datetime(2026, 8, 18, 2, 20, tzinfo=timezone.utc),      # 40 min
        symbol="7203")
    assert decision.outcome is Outcome.SKIPPED
    assert state.mode is EngineMode.ARMED


def test_57_weekends_are_closed():
    decision, state = _judge(
        "KRX",
        datetime(2026, 8, 22, 2, 0, tzinfo=timezone.utc),       # Saturday
        datetime(2026, 8, 21, 6, 30, tzinfo=timezone.utc),
        symbol="005930")
    assert decision.outcome is Outcome.SKIPPED
    assert state.mode is EngineMode.ARMED


def test_58_every_market_declares_a_session():
    from core import markets
    for market in markets.all_markets():
        assert market.session is not None, f"{market.code} has no session"
        assert market.session.windows, f"{market.code} has no trading window"
        assert market.session.max_age_open_s < market.session.max_age_hard_s


def test_59_sessions_use_a_real_timezone_with_dst():
    """A fixed UTC offset would drift by an hour twice a year."""
    from core import markets
    session = markets.session_for("US")
    summer = datetime(2026, 7, 1, 16, 0, tzinfo=timezone.utc)   # 12:00 EDT
    winter = datetime(2026, 1, 5, 16, 0, tzinfo=timezone.utc)   # 11:00 EST
    assert session.is_open(summer) and session.is_open(winter)
    assert session.local(summer).tzname() == "EDT"
    assert session.local(winter).tzname() == "EST"


def test_60_market_without_a_session_falls_back_to_the_global_bound():
    from core.engine.evaluator import Evaluator
    state = EngineState(); state.arm()
    ev = Evaluator(state, OrderBook(), max_quote_age_s=60)
    rule = _mrule("KRX")
    object.__setattr__(rule, "market", "NOT_A_MARKET")
    now = datetime(2026, 8, 18, 6, 0, tzinfo=timezone.utc)
    decision = ev.evaluate(rule, _mquote(now - timedelta(seconds=300)), now=now)
    assert decision.outcome is Outcome.HALTED
    assert "limit 60s" in decision.reason


def test_61_a_closed_venue_with_no_quote_skips_rather_than_halting():
    """Regression: the missing-data check used to run before the session check,
    so an unquotable symbol on a shut market halted the whole engine — which
    also stopped every rule on every *other* venue."""
    state = EngineState(); state.arm()
    book = OrderBook()
    saturday = datetime(2026, 8, 22, 2, 0, tzinfo=timezone.utc)
    decision = Evaluator(state, book).evaluate(
        _mrule("KRX", "005930"), None, now=saturday,
        quote_error="provider unavailable")
    assert decision.outcome is Outcome.SKIPPED
    assert state.mode is EngineMode.ARMED


def test_62_missing_data_while_open_halts_and_names_the_cause():
    state = EngineState(); state.arm()
    decision = Evaluator(state, OrderBook()).evaluate(
        _mrule("US"), None, now=datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc),
        quote_error="FMP plan does not cover AAPL (HTTP 402).")
    assert decision.outcome is Outcome.HALTED
    assert "402" in decision.reason, "a halt must say what to fix"
    assert state.halt_reason is HaltReason.NO_DATA


def test_65_closed_venues_are_not_fetched():
    """Overnight, a closed market must not consume an API quota."""
    tmp = _tmpdir()
    store, runtime = _runtime(tmp)
    asked = []
    original = runtime.feed.fetch_many
    runtime.feed.fetch_many = lambda pairs: (asked.append(sorted(pairs)),
                                             original(pairs))[1]
    store.save(_rule(limits=Limits()))                       # KRX
    saturday = datetime(2026, 8, 22, 2, 0, tzinfo=timezone.utc)
    runtime._now = lambda: saturday
    runtime.state.arm()
    try:
        runtime.tick()
        assert asked == [] or asked == [[]], f"fetched on a closed venue: {asked}"
    finally:
        runtime.stop()


def test_66_an_unchanged_verdict_is_logged_once_not_every_tick():
    tmp = _tmpdir()
    store, runtime = _runtime(tmp)
    store.save(_rule(limits=Limits()))
    saturday = datetime(2026, 8, 22, 2, 0, tzinfo=timezone.utc)
    runtime._now = lambda: saturday
    runtime.state.arm()
    try:
        for _ in range(5):
            runtime.tick()
        closed = [d for d in runtime.decisions(50) if "closed" in d.reason]
        assert len(closed) == 1, f"logged the same skip {len(closed)} times"
    finally:
        runtime.stop()


# --------------------------------------------------------------------------- #
# Exchange holiday calendars
# --------------------------------------------------------------------------- #
def test_67_a_public_holiday_is_recognised_by_name():
    """The whole point of the calendar: a holiday is known, not inferred from
    an absence of prints."""
    decision, state = _judge(
        "US",
        datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc),   # Thanksgiving
        datetime(2026, 11, 25, 21, 0, tzinfo=timezone.utc))
    assert decision.outcome is Outcome.SKIPPED
    assert state.mode is EngineMode.ARMED
    assert "holiday" in decision.reason


def test_68_korean_holidays_are_covered():
    from core import markets
    seollal = datetime(2026, 2, 17, 2, 0, tzinfo=timezone.utc)   # 11:00 KST
    state, why = markets.trading_state("KRX", seollal)
    assert state == "closed" and "holiday" in why


def test_69_a_half_day_closes_early():
    """The US session after Thanksgiving ends at 13:00 ET, not 16:00."""
    from core import markets
    inside = datetime(2026, 11, 27, 16, 0, tzinfo=timezone.utc)   # 11:00 ET
    after = datetime(2026, 11, 27, 18, 30, tzinfo=timezone.utc)   # 13:30 ET
    assert markets.trading_state("US", inside)[0] == "open"
    assert markets.trading_state("US", after)[0] == "closed"
    windows = markets.get("US").windows_for(after)
    assert windows[0][1].strftime("%H:%M") == "13:00"


def test_70_a_half_day_does_not_halt_after_its_early_close():
    """Before the calendar, 13:30 ET on a half-day looked like a frozen feed."""
    decision, state = _judge(
        "US",
        datetime(2026, 11, 27, 18, 30, tzinfo=timezone.utc),
        datetime(2026, 11, 27, 18, 0, tzinfo=timezone.utc))
    assert decision.outcome is Outcome.SKIPPED
    assert state.mode is EngineMode.ARMED


def test_71_a_date_beyond_coverage_is_unknown_not_open():
    """An uncovered date must never be silently treated as a trading day."""
    from core import calendars
    from datetime import date
    covers = calendars.coverage("US")
    assert covers is not None
    beyond = date(covers[1].year + 5, 6, 15)
    assert calendars.is_trading_day("US", beyond) is None


def test_72_every_registered_market_has_calendar_data():
    from core import calendars, markets
    loaded = set(calendars.loaded_markets())
    missing = [c for c in markets.codes() if c not in loaded]
    assert not missing, f"no calendar data for: {missing}"


def test_73_calendar_coverage_is_not_already_expired():
    """Fails when the shipped data has run out, which is the moment holiday
    handling silently degrades to guesswork."""
    from core import calendars
    expired = [row["market"] for row in calendars.stale_markets() if row["expired"]]
    assert not expired, f"calendar data expired for: {expired}"


def test_74_calendars_record_their_provenance():
    from core import calendars
    for code in calendars.loaded_markets():
        cal = calendars.get(code)
        assert cal.source.get("library") == "exchange_calendars"
        assert cal.source.get("calendar") and cal.source.get("generated")


def test_75_holiday_check_is_a_constant_time_lookup():
    """It runs for every rule on every tick, so it must not scan."""
    import time as _time
    from core import calendars
    from datetime import date
    calendars.is_trading_day("US", date(2026, 6, 15))      # warm the cache
    started = _time.perf_counter()
    for _ in range(20000):
        calendars.is_trading_day("US", date(2026, 6, 15))
    elapsed = _time.perf_counter() - started
    assert elapsed < 1.0, f"20k lookups took {elapsed:.2f}s"


def test_76_the_regular_session_still_trades():
    decision, state = _judge(
        "US",
        datetime(2026, 8, 19, 15, 0, tzinfo=timezone.utc),      # 11:00 ET Wed
        datetime(2026, 8, 19, 14, 59, tzinfo=timezone.utc))
    assert decision.fired, decision.reason


# --------------------------------------------------------------------------- #
# Transient provider failures: a counted grace, then the same halt as before
# --------------------------------------------------------------------------- #
def _flaky_runtime(tmp, outcomes, grace):
    """A runtime whose gateway works through `outcomes` in order: a number is a
    fresh quote at that price, anything else is raised as a transport error."""
    from core.engine.feed import QuoteFeed
    from core.engine.runtime import EngineRuntime
    from core.rules.store import RuleStore
    script = list(outcomes)

    class _Quote:
        def __init__(self, p):
            self.price = p
            self.as_of = TRADING_NOW.isoformat()

    class _Answer:
        def __init__(self, data):
            self.data, self.source, self.reason = data, "TEST", ""

        def __bool__(self):
            return True

    class _Gateway:
        def quote(self, ticker):
            step = script.pop(0)
            if isinstance(step, (int, float)):
                return _Answer(_Quote(step))
            raise ConnectionError(step)

    store = RuleStore(tmp / "rules.json")
    runtime = EngineRuntime(store, QuoteFeed(_Gateway()), tick_seconds=999,
                            state_path=tmp / "engine.json",
                            clock=lambda: TRADING_NOW, no_data_grace=grace)
    return store, runtime


def test_77_a_transient_miss_is_skipped_and_counted_then_recovers():
    """One timeout used to cost the rest of the session. Now it costs a tick."""
    tmp = _tmpdir()
    store, runtime = _flaky_runtime(tmp, ["read timed out", "read timed out", 68000], grace=3)
    store.save(_rule(limits=Limits(max_triggers=5)))
    runtime.state.arm()
    try:
        first = runtime.tick()[0]
        assert first.outcome is Outcome.SKIPPED and "miss 1 of 3" in first.reason
        assert "read timed out" in first.reason, "the skip must name the provider's error"
        second = runtime.tick()[0]
        assert "miss 2 of 3" in second.reason and runtime.state.is_armed
        assert not runtime.book.all(), "nothing may be placed without a quote"
        assert runtime.tick()[0].fired, "the next good quote resumes evaluation"
        assert runtime.feed.misses("005930") == 1, "a good quote pays one miss back"
    finally:
        runtime.stop()


def test_78_a_miss_that_outlasts_the_grace_halts_and_still_needs_a_manual_rearm():
    tmp = _tmpdir()
    store, runtime = _flaky_runtime(tmp, ["gateway down"] * 3, grace=2)
    store.save(_rule(limits=Limits()))
    runtime.state.arm()
    try:
        assert runtime.tick()[0].outcome is Outcome.SKIPPED
        assert runtime.tick()[0].outcome is Outcome.SKIPPED
        third = runtime.tick()[0]
        assert third.outcome is Outcome.HALTED and "gateway down" in third.reason
        assert runtime.state.halt_reason is HaltReason.NO_DATA
        ok, message = runtime.arm()
        assert not ok and "Acknowledge" in message, "the grace must not weaken the halt"
    finally:
        runtime.stop()


def test_79_a_grace_of_zero_halts_on_the_first_miss():
    tmp = _tmpdir()
    store, runtime = _flaky_runtime(tmp, ["gateway down"], grace=0)
    store.save(_rule(limits=Limits()))
    runtime.state.arm()
    try:
        assert runtime.tick()[0].outcome is Outcome.HALTED
    finally:
        runtime.stop()


def test_80_a_plan_refusal_halts_at_once_whatever_the_grace():
    """Waiting cannot fix a subscription fact, so it gets no grace."""
    from core.engine.feed import QuoteFeed
    from core.engine.runtime import EngineRuntime
    from core.rules.store import RuleStore
    tmp = _tmpdir()
    refusal = "FMP plan does not cover AAPL (HTTP 402)."
    feed = QuoteFeed(fmp_client=_FakeFMP(rows={}, blocked={"AAPL": refusal}))
    store = RuleStore(tmp / "rules.json")
    us_open = datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc)      # 11:00 ET Tue
    runtime = EngineRuntime(store, feed, tick_seconds=999,
                            state_path=tmp / "engine.json",
                            clock=lambda: us_open, no_data_grace=3)
    store.save(_mrule("US"))
    runtime.state.arm()
    try:
        decision = runtime.tick()[0]
        assert decision.outcome is Outcome.HALTED and "402" in decision.reason
        assert feed.is_permanent("AAPL")
    finally:
        runtime.stop()


def test_81_history_clients_share_the_retrying_session_and_quote_clients_do_not():
    import requests as plain
    from data.net import session
    import core.ficc.data as ficc
    import core.quant.history as hist
    import data.crypto.crypto_client as crypto
    import data.fmp.quote_client as fmp
    import data.kis_markets as kis_markets
    import data.krx.kis_client as kis
    import data.krx.krx_market_client as krx
    import data.krx.opendart_client as dart
    for module, name in ((ficc, "_requests"), (hist, "_requests"), (crypto, "_requests"),
                         (kis_markets, "_requests"), (kis, "requests"), (dart, "requests")):
        assert getattr(module, name) is session, module.__name__
    # The engine's quote path makes one attempt: its grace window is the retry,
    # and stacking both would triple the time every failing pass takes.
    assert fmp._requests is plain and krx.requests is plain and kis._once is plain
    seen = {}
    client = kis.KISClient()
    client._get = lambda path, tr_id, params, **kw: (seen.update(kw), {"output": {}})[1]
    client.quote("005930")
    assert seen == {"retry": False}, "the KIS live quote must not go through the retrying session"
    retry = session.get_adapter("https://example.invalid/").max_retries
    assert retry.total == 2
    assert set(retry.allowed_methods) == {"GET"}, "a POST (the KIS token) must never be replayed"
    assert set(retry.status_forcelist) == {502, 503, 504}, "a 429 or a 500 must not be replayed"
    assert retry.respect_retry_after_header is False, "a quota 429 must not park the calling thread"


def test_82_a_get_survives_two_bad_gateways_but_a_429_a_500_and_a_post_are_sent_once():
    """The retry is real, not just configured: a local server answers 503
    twice, then 200."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from data.net import session
    hits = {}

    class _Flaky(BaseHTTPRequestHandler):
        def _answer(self, method):
            key = (method, self.path)
            hits[key] = hits.get(key, 0) + 1
            code = {"/quota": 429, "/broken": 500}.get(self.path, 200 if hits[key] > 2 else 503)
            self.send_response(code)
            self.send_header("Retry-After", "30")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def do_GET(self):
            self._answer("GET")

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            self._answer("POST")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), _Flaky)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert session.get(url + "/flaky", timeout=5).status_code == 200
        assert hits[("GET", "/flaky")] == 3
        assert session.get(url + "/quota", timeout=5).status_code == 429
        assert session.get(url + "/broken", timeout=5).status_code == 500
        assert hits[("GET", "/quota")] == 1 and hits[("GET", "/broken")] == 1
        assert session.post(url + "/flaky", json={}, timeout=5).status_code == 503
        assert hits[("POST", "/flaky")] == 1
        # A retry must not write the request URL (which carries the API key for
        # FMP and OpenDART) to any log handler, even one listening at DEBUG.
        import io
        import logging
        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        root = logging.getLogger()
        level = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            session.get(url + "/again?apikey=SECRETKEY", timeout=5)
        finally:
            root.removeHandler(handler)
            root.setLevel(level)
        assert hits[("GET", "/again?apikey=SECRETKEY")] == 3
        assert "SECRETKEY" not in captured.getvalue()
    finally:
        server.shutdown()
        server.server_close()


def test_83_a_feed_that_fails_most_passes_still_runs_out_of_grace():
    """A good quote pays one miss back; it does not wipe the slate. And a grace
    episode is one log line, so the misses cannot push a FIRED out of the log."""
    tmp = _tmpdir()
    store, runtime = _flaky_runtime(tmp, ["down", "down", "down", 68000, "down", "down"], grace=3)
    store.save(_rule(limits=Limits(max_triggers=5)))
    runtime.state.arm()
    try:
        outcomes = [runtime.tick()[0].outcome for _ in range(6)]
        assert outcomes == [Outcome.SKIPPED] * 3 + [Outcome.FIRED, Outcome.SKIPPED, Outcome.HALTED]
        logged = runtime.decisions()
        assert sum("miss" in d.reason for d in logged) == 2, "one line per grace episode"
        assert any(d.fired for d in logged)
    finally:
        runtime.stop()


def test_84_arming_starts_a_fresh_grace_window():
    tmp = _tmpdir()
    store, runtime = _flaky_runtime(tmp, ["down"] * 3, grace=1)
    runtime._ensure_thread = lambda: None          # keep the background loop out of this
    store.save(_rule(limits=Limits()))
    runtime.state.arm()
    try:
        assert runtime.tick()[0].outcome is Outcome.SKIPPED
        assert runtime.tick()[0].outcome is Outcome.HALTED
        runtime.acknowledge()
        ok, _ = runtime.arm()
        assert ok and runtime.feed.misses("005930") == 0
        assert runtime.tick()[0].outcome is Outcome.SKIPPED, "the first miss after arming is in grace"
    finally:
        runtime.stop()


def test_85_time_spent_fetching_counts_against_the_quote():
    """The clock is read again after the fetch: a quote taken at the start of a
    slow pass must not be judged as if no time had passed."""
    from core.engine.feed import QuoteFeed
    from core.engine.runtime import EngineRuntime
    from core.rules.store import RuleStore
    tmp = _tmpdir()
    clock = [TRADING_NOW]

    class _Quote:
        def __init__(self):
            self.price, self.as_of = 68000, clock[0].isoformat()

    class _Answer:
        def __init__(self):
            self.data, self.source, self.reason = _Quote(), "TEST", ""

        def __bool__(self):
            return True

    class _SlowGateway:
        def quote(self, ticker):
            answer = _Answer()
            clock[0] = clock[0] + timedelta(seconds=600)      # the provider took ten minutes
            return answer

    store = RuleStore(tmp / "rules.json")
    runtime = EngineRuntime(store, QuoteFeed(_SlowGateway()), tick_seconds=999,
                            state_path=tmp / "engine.json", clock=lambda: clock[0])
    store.save(_rule(limits=Limits()))
    runtime.state.arm()
    try:
        decision = runtime.tick()[0]
        assert decision.outcome is Outcome.HALTED, decision.reason
        assert runtime.state.halt_reason is HaltReason.STALE_DATA
        assert not runtime.book.all()
    finally:
        runtime.stop()


def test_86_a_symbol_shared_by_two_venues_is_one_miss_per_pass():
    from core.engine.feed import QuoteFeed
    feed = QuoteFeed(fmp_client=_FakeFMP(error="timeout"))
    feed.fetch_many([("SAN", "US"), ("SAN", "BME")])
    assert feed.misses("SAN") == 1
    # When every symbol fails, each keeps its own reason, not the first one's.
    refusal = "FMP plan does not cover VOD.L (HTTP 402)."
    feed = QuoteFeed(fmp_client=_FakeFMP(error="timeout", blocked={"VOD.L": refusal}))
    feed.fetch_many([("AAPL", "US"), ("VOD", "LSE")])
    assert feed.last_error("VOD") == refusal and "timeout" in feed.last_error("AAPL")
    assert feed.is_permanent("VOD") and not feed.is_permanent("AAPL")


def test_87_the_dashboard_names_a_symbol_the_armed_engine_cannot_see():
    tmp = _tmpdir()
    store, runtime = _flaky_runtime(tmp, ["read timed out", "read timed out", 68000], grace=3)
    store.save(_rule(limits=Limits(max_triggers=5)))
    runtime.state.arm()
    try:
        runtime.tick()
        runtime.tick()
        assert runtime.dashboard()["degraded"] == [("005930", 2, "ConnectionError: read timed out")]
        runtime.tick()
        assert runtime.feed.misses("005930") == 1, "one miss is still held against it"
        assert runtime.dashboard()["degraded"] == [], "but it is quoted again, so it is not degraded"
        # A venue that is shut is not reported either, whatever its count says.
        saturday = datetime(2026, 8, 22, 2, 0, tzinfo=timezone.utc)
        runtime.feed._fail("005930", "left over from Friday")
        runtime._now = lambda: saturday
        assert runtime.dashboard()["degraded"] == []
    finally:
        runtime.stop()


def test_90_a_venue_that_opens_mid_pass_does_not_halt_for_a_quote_never_asked_for():
    """The clock is read twice per pass. A rule whose venue was shut at the
    first read was not fetched, so it must not be judged 'open, no quote'."""
    from core.engine.feed import QuoteFeed
    from core.engine.runtime import EngineRuntime
    from core.rules.store import RuleStore
    tmp = _tmpdir()
    before_open = datetime(2026, 8, 18, 23, 59, 58, tzinfo=timezone.utc)     # 08:59:58 KST
    after_open = datetime(2026, 8, 19, 0, 0, 3, tzinfo=timezone.utc)         # 09:00:03 KST
    reads = [before_open]

    def clock():
        return reads.pop(0) if len(reads) > 1 else reads[0]

    class _Gateway:
        def quote(self, ticker):
            raise AssertionError("a shut venue must not be asked")

    store = RuleStore(tmp / "rules.json")
    runtime = EngineRuntime(store, QuoteFeed(_Gateway()), tick_seconds=999,
                            state_path=tmp / "engine.json", clock=clock)
    store.save(_rule(limits=Limits()))
    runtime.state.arm()
    reads[:] = [before_open, after_open]
    try:
        decision = runtime.tick()[0]
        assert decision.outcome is Outcome.SKIPPED and "closed" in decision.reason, decision.reason
        assert runtime.state.is_armed
    finally:
        runtime.stop()


def test_91_arming_an_armed_engine_does_not_reset_the_grace():
    tmp = _tmpdir()
    store, runtime = _flaky_runtime(tmp, ["down"] * 3, grace=2)
    runtime._ensure_thread = lambda: None
    store.save(_rule(limits=Limits()))
    runtime.state.arm()
    try:
        runtime.tick()
        runtime.tick()
        ok, message = runtime.arm()
        assert ok and "Already" in message and runtime.feed.misses("005930") == 2
        assert runtime.tick()[0].outcome is Outcome.HALTED
    finally:
        runtime.stop()


def test_88_the_grace_setting_is_capped():
    tmp = _tmpdir()
    _, runtime = _flaky_runtime(tmp, [], grace=10 ** 9)
    assert runtime.no_data_grace == 10, "a typo must not switch the missing-data halt off"
    runtime.stop()


def test_89_kis_calls_are_paced_and_a_rate_limit_reply_is_retried_once():
    """KIS answers a burst with HTTP 500 / EGW00201 (seen live: ten calls in a
    second). Calls are spaced out, and that one reply earns one more try."""
    import time as real_time
    import config
    import data.krx.kis_client as kis
    clock, slept, sent = [100.0], [], []

    class _Time:
        monotonic = staticmethod(lambda: clock[0])
        time = staticmethod(real_time.time)

        @staticmethod
        def sleep(seconds):
            slept.append(round(seconds, 3))
            clock[0] += seconds

    class _Resp:
        headers = {}

        def __init__(self, status, body):
            self.status_code, self._body = status, body

        def json(self):
            return self._body

    limited = _Resp(500, {"rt_cd": "1", "msg_cd": "EGW00201", "msg1": "초당 거래건수를 초과하였습니다."})
    fine = _Resp(200, {"rt_cd": "0", "output": {}})

    class _HTTP:
        def __init__(self, script):
            self.script = list(script)

        def get(self, url, **kwargs):
            sent.append(clock[0])
            return self.script.pop(0)

    saved = (kis.time, kis.requests, kis._once, kis._last_call[0], config.kis_credentials)
    kis.time = _Time
    kis._last_call[0] = 0.0
    config.kis_credentials = lambda: ("k", "s")
    client = kis.KISClient()
    client.token = lambda: "t"
    try:
        kis.requests = _HTTP([fine, fine, limited, fine])
        client._get("/p", "TR", {})
        client._get("/p", "TR", {})
        assert round(sent[1] - sent[0], 3) == kis._MIN_GAP_S, "back-to-back calls must be spaced"
        assert client._get("/p", "TR", {}) == {"rt_cd": "0", "output": {}}
        assert 1.0 in slept and len(sent) == 4, "a rate-limit reply waits a second and tries once more"
        # The live quote makes one attempt: the engine's grace window is its retry.
        kis._once = _HTTP([limited])
        try:
            client._get("/p", "TR", {}, retry=False)
        except kis.KISError as exc:
            assert "EGW00201" in str(exc), "the halt reason must carry KIS's own code"
        else:
            raise AssertionError("a rate-limited single attempt must raise")
        assert len(sent) == 5
    finally:
        kis.time, kis.requests, kis._once, kis._last_call[0], config.kis_credentials = saved


def tests():
    return sorted((n, v) for n, v in globals().items()
                  if n.startswith("test_") and callable(v))
