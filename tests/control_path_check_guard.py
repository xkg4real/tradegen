"""BR-6–9 receipt replay and durable entry protection over isolated control state."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D

from execution_accounts.provider import EvidenceError
from execution_control.session import prepare_session
from execution_control.store import Journal, JournalError, _utc
from execution_launch.path_check_guard import PathCheckRecorder
from tests.accounts_candle_audit import candle, verified
from tests.accounts_path_checks import Archive, MARKET, MINUTE, NOW, SCOPE, order, tick, window
from tests.control_continuous_guard import build
from tests.control_continuous_guard_commit import CONSISTENT, PREPARE, classify, commit, rows, stack
from tests.control_controller import reserve, restart, send, snapshot
from tests.control_session import _fixed_refusal, _preparation_args, signed_control


def recorder(scope=SCOPE):
    with Journal().transaction():
        pass
    return PathCheckRecorder(journal=Journal(require_existing=True), account_scope=scope,
                             deployment_sha256="a"*64, policy_sha256="b"*64)


def body(now):
    return dict(account_scope="fixture-account", deployment_sha256="a"*64, policy_sha256="b"*64,
                symbol=MARKET, cause="TICKER_MISMATCH", observed_at=_utc(now), price="1",
                occurrences=1, evidence_sha256="d"*64)


def test_confirmed_ticker_and_canary_replay_persist_independent_evidence_once():
    record = recorder()
    src = Archive([tick(MINUTE, 5, 4)])
    src.ticker = tick(MINUTE+timedelta(seconds=2), 50, 9)
    walk = window(src)
    own = order(src, "order-b", [("b", MINUTE+timedelta(seconds=1), 7, 1)])
    def check():
        return record.check_window(walk, (own,), expected_order_ids=frozenset({"order-b"}), now=NOW)
    findings = check()
    assert [f.kind for f in findings] == ["TICKER_MISMATCH", "OWN_FILL_MISS"]
    assert check() == findings
    records = [r["data"] for r in record.journal.snapshot()]
    assert [r["evidence_sha256"] for r in records] == [f.evidence_sha256 for f in findings]
    assert [r["price"] for r in records] == ["50", "7"]
    assert all(r["deployment_sha256"] == record.deployment_sha256 and r["policy_sha256"] == record.policy_sha256
               and r["account_scope"] == SCOPE for r in records)


def test_bad_private_capture_does_not_erase_an_already_confirmed_public_mismatch():
    record = recorder()
    src = Archive([tick(MINUTE, 5, 4)])
    src.ticker = tick(MINUTE, 7, 4)
    walk = window(src)
    try:
        record.check_window(walk, (), expected_order_ids=frozenset({"missing"}), now=NOW)
    except EvidenceError as exc:
        assert exc.code == "PATH_CHECK_ORDER_ROSTER_MISMATCH"
    else:
        raise AssertionError("missing private evidence accepted")
    assert len(record.journal.snapshot()) == 1
    tampered = replace(walk, proof_sha256="e"*64)
    try:
        record.check_window(tampered, (), expected_order_ids=frozenset(), now=NOW)
    except EvidenceError as exc:
        assert exc.code == "PATH_CHECK_WINDOW_REPLAY_MISMATCH"
    else:
        raise AssertionError("changed raw proof accepted")
    assert len(record.journal.snapshot()) == 1


def test_lagging_minute_requires_finality_for_latch_and_preserves_missing_price():
    record = recorder()
    walk = window(Archive([tick(MINUTE, 5, 4)]))
    args = dict(market=MARKET, first_minute=MINUTE, now=NOW)
    pending, = record.check_minutes((walk,), (candle(MINUTE),), **args)
    assert pending.status == "FINALITY_UNVERIFIED" and not record.journal.snapshot()
    final, = record.check_minutes((walk,), (candle(MINUTE),), **args, verify_finality=verified)
    row, = record.journal.snapshot()
    assert row["kind"] == "entry_block" and row["data"]["cause"] == "CANDLE_MINUTE"
    assert row["data"]["price"] is None and row["data"]["evidence_sha256"] == final.findings[0].evidence_sha256


def test_block_survives_restart_refuses_reserved_and_new_buy_without_triggering_sale():
    with signed_control() as env:
        pending = reserve(env)
        with env.journal.transaction() as tx:
            tx.append("entry_block", body(env.now), now=env.now)
        env.controller = restart(env)
        result = env.controller.observe(now=env.now)
        assert result.new_entry_blocked and "PATH_EVIDENCE_ENTRY_BLOCK" in result.reasons
        assert not result.protective_action_needed and not env.adapter.requests
        _fixed_refusal(lambda:reserve(env, replace(env.order, client_id="later")), "PATH_EVIDENCE_ENTRY_BLOCK")
        _fixed_refusal(lambda:send(env), "PATH_EVIDENCE_ENTRY_BLOCK")
        assert not env.adapter.requests
        # Existing local cancellation remains explicit and can release the reserved buy.
        env.controller.cancel(pending.client_id, now=env.now)
        assert not env.adapter.requests
        snapshot(env, positions=replace(env.observation.positions, holdings={("upbit","BTC"):0.001}),
                 holdings={("upbit","fixture-account","spot",MARKET):D("0.001")})
        sell = replace(env.order, side="sell", client_id="existing-authorized-exit")
        assert reserve(env, sell).status == "RESERVED"
        assert env.controller.dispatch(sell.client_id, now=env.now).status == "ACKNOWLEDGED"
        assert len(env.adapter.requests) == 1


def test_entry_block_stops_session_preparation_and_no_unsigned_release_can_be_appended():
    with signed_control(prepare=False,arm=False) as env:
        with env.journal.transaction() as tx:
            tx.append("entry_block", body(env.now), now=env.now)
            try:
                tx.append("entry_unblock", body(env.now), now=env.now)
            except JournalError:
                pass
            else:
                raise AssertionError("unverified release accepted")
        _fixed_refusal(lambda:prepare_session(**_preparation_args(env)), "PATH_EVIDENCE_ENTRY_BLOCK")
        assert [r["kind"] for r in env.journal.snapshot()] == ["entry_block"]


def test_restart_remains_consistent_after_post_commit_block_and_floor_halt_survives():
    for prices, halted in ((("101",),False), (("110","105","115"),True)):
        with stack() as s:
            package = build(s.state,s.policy,s.context,prices)
            receipt = commit(s,package)
            with s.journal.transaction() as tx:
                tx.append("entry_block",body(package["now"]),now=package["now"])
            result = classify(s)
            assert result.status == CONSISTENT and result.entry_blocked and result.new_entries_blocked
            assert result.permanently_halted is halted and result.transaction_id == receipt.transaction_id
            assert sum(r["kind"]=="halt" for r in rows(s)) == int(halted)


def test_malformed_future_or_in_transaction_entry_blocks_do_not_extend_journal():
    journal = Journal()
    with journal.transaction() as tx:
        for change in ({"cause":"CLEAR"},{"price":"0"},{"price":None},{"price":"1.0"},{"occurrences":True},
                       {"observed_at":_utc(NOW+timedelta(seconds=1))},{"policy_sha256":None}):
            try:
                tx.append("entry_block",body(NOW)|change,now=NOW)
            except JournalError:
                pass
            else:
                raise AssertionError(change)
        assert not tx.events
        tx.append(PREPARE,{},now=NOW)
        try:
            tx.append("entry_block",body(NOW),now=NOW)
        except JournalError:
            pass
        else:
            raise AssertionError("foreign row inserted inside pending commit")
        assert len(tx.events) == 1


def test_held_interval_records_raw_ticker_discrepancy_before_refusing_uncertain_extrema():
    from unittest.mock import patch

    from execution_accounts.upbit_collector import collect_trade_window
    from execution_launch.account_interval import UpbitIntervalSource
    from tests import launch_account_interval as fixture
    from tests.launch_committed_producer import START

    end = START + timedelta(seconds=5)
    settled = end + timedelta(seconds=3)

    class Capture(Archive):
        account_scope = fixture.SCOPE
        def fetch(self, path, params):
            return replace(super().fetch(path, params), account_scope=self.account_scope, received_at=settled, server_time=settled)

    source = Capture([tick(START-timedelta(seconds=2),10050,1), tick(START+timedelta(seconds=1),10050,2)])
    source.ticker = tick(START+timedelta(seconds=2),10049,3)
    def read_window(_, symbol, **args):
        args["clock"].now = settled
        return collect_trade_window(source, symbol, **args)
    exchange = fixture.FakeUpbit(cash="89995", btc="1", orders=(fixture.BUY,))
    with fixture.series(START, exchange=exchange, fees=(), realized=D(0)) as env:
        record = recorder(fixture.SCOPE)
        env.source = UpbitIntervalSource(trade_window_collector=read_window, path_check_recorder=record)
        with patch("tests.accounts_path_checks.NOW",end):
            _fixed_refusal(lambda:env.collect(end), "ACCOUNT_INTERVAL_TICKER_CHECK_BLOCK_ALERT_REQUIRED")
        row, = record.journal.snapshot()
        assert row["data"]["cause"] == "TICKER_MISMATCH" and row["data"]["price"] == "10049"
        assert not env.source.staged_frames and not env.source.execution_ready
