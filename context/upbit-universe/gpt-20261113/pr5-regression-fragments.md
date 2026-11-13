# Prepared regression fragments — not implemented or executed

These are source-reading worksheets for the existing approved plans. Reconcile helper contracts and review each assertion after dependencies merge. AST syntax checks are not RED/GREEN test results. No production source or policy was changed.

## pr5-causality-tests-fragment.py

````python
# Scratch only: append to tests/launch_universe_study.py after PR5 Task 6 helpers exist.
# Uses that plan's Feed/uplan/rotation/scripted/RULES_ROWS fixture and imported S, timedelta, patch, replace.
# Not executed during preparation. No authenticated failed-outcome amendment is assumed.


def test_universe_decision_times_follow_each_candidates_actual_computation():
    plan = uplan(programs=(rotation("fixture-clock-a"), rotation("fixture-clock-b", margin="0.1")))
    feed = Feed(plan, scripted(RULES_ROWS))
    original = S.choose
    counts, completed = {}, {}

    def measured_choose(program, *args, **kwargs):
        answer = original(program, *args, **kwargs)
        feed.now[0] += timedelta(milliseconds=1)
        index = counts.get(program.strategy_id, 0)
        counts[program.strategy_id] = index + 1
        completed[program.strategy_id, index] = feed.now[0]
        return answer

    with patch.object(S, "choose", measured_choose):
        result = feed.run()
    assert result.complete, result.reason
    for candidate, archive in zip(plan.candidates, result.archives):
        protocol = candidate.protocol
        for index, decision in enumerate(archive.decisions):
            decided = T._date(decision["decided_at"])
            deadline = (protocol.capture_start + timedelta(seconds=(index + 1) * protocol.bar_seconds)
                        - timedelta(seconds=protocol.minimum_fill_delay_seconds))
            assert completed[candidate.program.strategy_id, index] <= decided <= deadline


def test_universe_decision_completion_deadline_accepts_equality_and_refuses_one_microsecond_late():
    for excess in (timedelta(0), timedelta(microseconds=1)):
        plan = uplan()
        feed = Feed(plan, scripted(RULES_ROWS))
        protocol = plan.candidates[0].protocol
        deadline = (protocol.capture_start + timedelta(seconds=protocol.bar_seconds)
                    - timedelta(seconds=protocol.minimum_fill_delay_seconds))
        original = S.choose
        first = True

        def delayed_choose(*args, **kwargs):
            nonlocal first
            answer = original(*args, **kwargs)
            if first:
                first = False
                feed.now[0] = deadline + excess
            return answer

        with patch.object(S, "choose", delayed_choose):
            result = feed.run()
        if excess == timedelta(0):
            assert result.complete, result.reason
            assert T._date(result.archives[0].decisions[0]["decided_at"]) == deadline
        else:
            assert not result.complete and result.reason == "STUDY_CAPTURE_DECISION_TOO_LATE"
            assert json.loads(feed.lines[-1]) == {"end": "STUDY_CAPTURE_DECISION_TOO_LATE"}


def test_universe_tick_receipt_must_arrive_by_its_execution_slot():
    feed = Feed(uplan(), scripted(RULES_ROWS))
    feed.now[0] = START
    asked = [BTC]
    books, ticks = feed.read_books(asked), feed.read_ticks(asked)
    for lag in (timedelta(0), timedelta(microseconds=1), timedelta(seconds=1)):
        changed = replace(ticks, received_at=START + lag, server_time=START + lag)
        rows = S._book_rows(START, asked, books, changed)
        if lag == timedelta(0):
            assert rows[BTC] == ["99", "101", "1", books.sha256]
        else:
            assert rows == {BTC: "unavailable"}
````

## pr5-listing-tests-fragment.py

````python
# Scratch only: append to tests/accounts_universe.py after PR5 Task 3 Answer fields exist.
# Uses its existing synthetic F.serve/answered/market/unavailable/BUILT fixtures.
# Not executed during preparation.


def test_slot_flags_reject_malformed_market_identifiers_and_preserve_raw_evidence():
    source = U.UniverseSlotSource(clock=lambda: BUILT)
    malformed = (
        [{}], [{"market": None}], [{"market": 1}], [market("KRW-btc")], [market("BTC")],
        [market("KRW-BTC"), market("KRW-BTC")],
        [market("BTC-ETH"), market("BTC-ETH")],
        [market("KRW-BTC"), {}],
    )
    for rows in malformed:
        raw = json.dumps(rows).encode("utf-8")
        with F.serve({("GET", "/v1/market/all"): answered(raw)}):
            result = source.read_flags()
        assert unavailable(result), rows
        assert result.answer is not None and result.answer.raw_body == raw
        assert result.answer.sha256 == hashlib.sha256(raw).hexdigest()


def test_slot_flags_distinguish_valid_empty_or_non_krw_listings_from_unknown_flags():
    source = U.UniverseSlotSource(clock=lambda: BUILT)
    cases = (
        ([], {}),
        ([market("BTC-ETH")], {}),
        ([market("BTC-ETH"), market("KRW-BTC")], {"KRW-BTC": "unflagged"}),
        ([{"market": "KRW-BTC"}], {"KRW-BTC": "unknown"}),
        ([market("KRW-BTC", warning=True)], {"KRW-BTC": "warning"}),
    )
    for rows, expected in cases:
        raw = json.dumps(rows).encode("utf-8")
        with F.serve({("GET", "/v1/market/all"): answered(raw)}):
            result = source.read_flags()
        assert result.ok is True and dict(result.flags) == expected
        assert result.answer is not None and result.answer.raw_body == raw
````

## pr5-market-index-fixture.py

````python
# Scratch only, NOT an auto-discovered test. Uses PR5 Task 6 _frame and imported S, START, SimpleNamespace.
# The final handling of cumulative index exhaustion must be made explicit before integration.
# These inputs and postconditions do not choose a new format, index recycling, or failure-outcome policy.


def cumulative_market_index_churn_fixture(new_flag="unflagged"):
    old = ["KRW-BTC"] + ["KRW-X" + format(n, "03d") for n in range(319)]
    assert len(old) == S.MAX_FRAME_MARKETS == 320
    names = {coin: index for index, coin in enumerate(old)}
    new = "KRW-NEW"
    current = old[:-1] + [new]
    flags = {coin: "unflagged" for coin in current}
    flags[new] = new_flag
    prices = {coin: ("100", -1000) for coin in current}
    books = {"KRW-BTC": ["99", "101", "1", "e" * 64]}
    snapshot = SimpleNamespace(snapshot_sha256="1" * 64)
    return names, snapshot, flags, prices, books, (new,)


def assert_returned_capacity_frame_has_no_silent_price_truncation(frame, names, expected_prices, old_names):
    # Apply only if capture returns a frame. An explicit bounded-format refusal needs its own named assertion.
    assert len(names) <= S.MAX_FRAME_MARKETS
    assert all(names.get(coin) == index for coin, index in old_names.items())
    if frame["prices"] is not None:
        order = list(names)
        assert {order[row[0]] for row in frame["prices"]} == set(expected_prices)
    assert any(row[0] == names["KRW-BTC"] for row in frame["books"])
````

