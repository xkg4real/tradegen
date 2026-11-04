"""Private temporary checkpoints and invented authenticated-adapter interfaces."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext
import os
from pathlib import Path
import stat
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance.model import KST
from execution_accounts.baseline import (
    BaselineAnchor, BaselineConventions, BaselineError, BaselineInterval,
    advance_baseline, initialize_baseline,
)
from execution_accounts.baseline_bridge import (
    BaselineBridgeError, BaselineFrame, ContinuousAccountProvider,
    advance_account_baseline, initialize_account_baseline,
)
from execution_accounts.baseline_store import CheckpointError, CheckpointStore
from execution_accounts.model import ExternalFlow, RiskBaseline, content_digest
from tests import compliance_fixtures as F
from tests.accounts_provider import NOW, SHA, SCOPE, bundle, fill

D = Decimal


def anchor_fixture(*, previous=None, day_open=D("0"), now=NOW):
    accounts = bundle(now=now, opening=D("1000")).accounts
    first_day = now.astimezone(KST).date() - timedelta(days=0 if previous is None else 1)
    baseline = RiskBaseline(day_start_equity=D("1000"), prior_high_watermark=D("1000"),
        observed_daily_loss=D("0"), approved_effective_floor=D("700"), first_trading_day=first_day,
        asof=now, source_sha256=content_digest(accounts))
    anchor = BaselineAnchor(account_scope=SCOPE, baseline=baseline, equity_krw=D("1000"),
        realized_net_total_krw=D("0"), day_open_realized_net_total_krw=day_open,
        previous_day_realized_net_krw=previous, sequence=0)
    conventions = BaselineConventions(daily_loss="maximum_net_equity_loss_from_day_open",
        external_flows="no_external_flows", max_interval_seconds=30)
    return conventions, anchor, accounts


def initial():
    conventions, anchor, accounts = anchor_fixture()
    return initialize_account_baseline(conventions, anchor, accounts, now=NOW).state


def frame_for(state, *, accounts=None, **changes):
    end = changes.get("end", state.asof+timedelta(seconds=10))
    if accounts is None:
        accounts = bundle(now=end, opening=D("1000")).accounts
    values = dict(account_scope=SCOPE, sequence=state.sequence+1, previous_state_digest=state.state_digest,
        start=state.asof, end=end, equity_krw=D("1000"), minimum_equity_krw=D("1000"),
        maximum_equity_krw=D("1000"), realized_net_total_krw=D("0"),
        gross_external_inflows_krw=D("0"), gross_external_outflows_krw=D("0"),
        source_sha256=content_digest(accounts), coverage_sha256="c"*64)
    return BaselineFrame(interval=BaselineInterval(**(values | changes)), accounts=accounts)


def profit_frame(state):
    end = state.asof+timedelta(seconds=10)
    buy = fill(quantity=D("1"), fee=D("1"), at=state.asof+timedelta(seconds=1))
    sell = fill(side="sell", quantity=D("1"), price=D("120"), fee=D("1"),
                order="sell1", fid="sell-fill", at=state.asof+timedelta(seconds=2))
    accounts = bundle(now=end, opening=D("1000"), cash=D("1018"), fills=(buy, sell)).accounts
    return frame_for(state, accounts=accounts, equity_krw=D("1018"), minimum_equity_krw=D("999"),
                     maximum_equity_krw=D("1018"), realized_net_total_krw=D("18"))


def refused(call, code=None):
    try:
        call()
    except (CheckpointError, BaselineError, BaselineBridgeError) as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected checkpoint or bridge refusal")


class Head:
    """Only a test double; the product does not implement external authority."""
    def __init__(self, value):
        self.value = value
        self.commits = []

    def read(self):
        return self.value

    def compare_and_set(self, previous, new):
        if self.value != previous:
            return False
        self.commits.append((previous, new))
        self.value = new
        return True


def test_anchor_bridge_reconciles_first_actual_balance_profit_and_explicit_source_binding():
    conventions, anchor, accounts = anchor_fixture()
    update = initialize_account_baseline(conventions, anchor, accounts, now=NOW)
    assert update.observation.risk.equity == D("1000")
    assert update.state.first_trading_day == NOW.astimezone(KST).date()
    assert update.state.realized_net_total_krw == 0
    bad = replace(anchor, equity_krw=D("1001"))
    refused(lambda: initialize_account_baseline(conventions, bad, accounts, now=NOW),
            "BASELINE_BRIDGE_EQUITY_MISMATCH")
    bad = replace(anchor, realized_net_total_krw=D("1"))
    refused(lambda: initialize_account_baseline(conventions, bad, accounts, now=NOW),
            "BASELINE_BRIDGE_CUMULATIVE_PROFIT_MISMATCH")
    bad = replace(anchor, baseline=replace(anchor.baseline, source_sha256=SHA))
    refused(lambda: initialize_account_baseline(conventions, bad, accounts, now=NOW),
            "BASELINE_BRIDGE_ENDPOINT_CHANGED")


def test_checkpoint_construct_and_missing_load_create_nothing_then_explicit_seed_roundtrips():
    state = initial()
    with F.temp_home() as home:
        store = CheckpointStore(root=home)
        assert not (home / "execution-baseline").exists()
        refused(lambda: store.load(expected_head=state.state_digest), "BASELINE_STORE_IO_REFUSED")
        assert not (home / "execution-baseline").exists()
        receipt = store.seed(state, expected_head=state.state_digest)
        assert receipt.previous_head is None and receipt.new_head == state.state_digest
        assert store.load(expected_head=state.state_digest) == state
        assert sorted(p.name for p in (home / "execution-baseline").iterdir()) == ["checkpoint.json", "checkpoint.lock"]
        refused(lambda: store.seed(state, expected_head=state.state_digest), "BASELINE_STORE_ALREADY_INITIALIZED")


def test_store_root_must_be_absolute_explicit_and_equal_selected_state_root():
    with F.temp_home() as home:
        refused(lambda: CheckpointStore(root=Path("relative")), "BASELINE_STORE_EXPLICIT_ROOT_REQUIRED")
        refused(lambda: CheckpointStore(root=str(home)), "BASELINE_STORE_EXPLICIT_ROOT_REQUIRED")
        refused(lambda: CheckpointStore(root=home / "other"), "BASELINE_STORE_ROOT_MISMATCH")


def test_store_commit_requires_exact_prior_head_and_preserves_restart_state():
    state = initial(); frame = frame_for(state)
    update = advance_account_baseline(state, frame.interval, frame.accounts, now=frame.interval.end)
    with F.temp_home() as home:
        store = CheckpointStore(root=home)
        store.seed(state, expected_head=state.state_digest)
        refused(lambda: store.commit(update.state, expected_previous_head="d"*64), "BASELINE_CHECKPOINT_MISMATCH")
        assert store.load(expected_head=state.state_digest) == state
        receipt = store.commit(update.state, expected_previous_head=state.state_digest)
        assert receipt.sequence == state.sequence+1
        restarted = CheckpointStore(root=home)
        assert restarted.load(expected_head=receipt.new_head) == update.state
        refused(lambda: restarted.load(expected_head=state.state_digest), "BASELINE_CHECKPOINT_MISMATCH")
        refused(lambda: restarted.commit(state, expected_previous_head=receipt.new_head),
                "BASELINE_STORE_TRANSITION_REFUSED")


def test_store_refuses_non_anchor_seed_and_duplicate_commit_without_reset():
    state = initial(); frame = frame_for(state); next_state = advance_baseline(state, frame.interval)
    with F.temp_home() as home:
        store = CheckpointStore(root=home)
        refused(lambda: store.seed(next_state, expected_head=next_state.state_digest), "BASELINE_STORE_ANCHOR_REQUIRED")
        assert not (home / "execution-baseline").exists()
        store.seed(state, expected_head=state.state_digest)
        store.commit(next_state, expected_previous_head=state.state_digest)
        refused(lambda: store.commit(next_state, expected_previous_head=next_state.state_digest),
                "BASELINE_STORE_TRANSITION_REFUSED")


def test_atomic_replace_failure_keeps_old_checkpoint_and_refuses_interrupted_temporary_file():
    state = initial(); frame = frame_for(state); next_state = advance_baseline(state, frame.interval)
    with F.temp_home() as home:
        store = CheckpointStore(root=home); store.seed(state, expected_head=state.state_digest)
        path = home / "execution-baseline" / "checkpoint.json"
        before = path.read_bytes()
        with patch("execution_accounts.baseline_store.os.replace", side_effect=OSError("private detail")):
            refused(lambda: store.commit(next_state, expected_previous_head=state.state_digest),
                    "BASELINE_STORE_IO_REFUSED")
        assert path.read_bytes() == before
        assert (path.parent / "checkpoint.tmp").is_file()
        refused(lambda: store.load(expected_head=state.state_digest), "BASELINE_STORE_INTERRUPTED_WRITE")


def test_store_refuses_hardlinked_checkpoint_and_linked_directory():
    state = initial()
    with F.temp_home() as home:
        store = CheckpointStore(root=home); store.seed(state, expected_head=state.state_digest)
        path = home / "execution-baseline" / "checkpoint.json"
        os.link(path, home / "copy")
        refused(lambda: store.load(expected_head=state.state_digest))
    with F.temp_home() as home:
        target = home / "elsewhere"; target.mkdir()
        F.directory_link(home / "execution-baseline", target)
        refused(lambda: CheckpointStore(root=home))
        assert list(target.iterdir()) == []


def test_store_bounded_regular_descriptors_and_malformed_content_are_required():
    state = initial()
    for raw in (b"x"*65537, b"{\"truncated\":"):
        with F.temp_home() as home:
            store = CheckpointStore(root=home); store.seed(state, expected_head=state.state_digest)
            (home / "execution-baseline" / "checkpoint.json").write_bytes(raw)
            refused(lambda: store.load(expected_head=state.state_digest))
    with F.temp_home() as home:
        store = CheckpointStore(root=home); store.seed(state, expected_head=state.state_digest)
        bad = SimpleNamespace(st_mode=stat.S_IFIFO, st_nlink=1, st_size=0)
        with patch("execution_accounts.baseline_store.os.fstat", return_value=bad):
            refused(lambda: store.load(expected_head=state.state_digest), "BASELINE_STORE_FILE_REFUSED")


def test_bridge_fifo_profit_equity_and_exact_arithmetic_reconcile_without_dummy_baseline():
    state = initial(); frame = profit_frame(state)
    with localcontext() as numeric:
        numeric.prec = 3
        result = advance_account_baseline(state, frame.interval, frame.accounts, now=frame.interval.end)
    assert result.state.realized_net_total_krw == D("18")
    assert result.observation.risk.current_day_realized_net_profit == D("18")
    assert result.observation.risk.equity == D("1018")
    assert result.state.observed_daily_loss == D("1")
    assert result.bundle.risk_baseline.source_sha256 == result.state.state_digest


def test_bridge_rejects_cumulative_daily_and_prior_day_accounting_contradictions():
    state = initial(); frame = profit_frame(state)
    refused(lambda: advance_account_baseline(state, replace(frame.interval, realized_net_total_krw=D("17")),
            frame.accounts, now=frame.interval.end), "BASELINE_BRIDGE_CUMULATIVE_PROFIT_MISMATCH")
    conventions, anchor, _ = anchor_fixture(day_open=D("1"))
    state = initialize_baseline(conventions, anchor); frame = profit_frame(state)
    refused(lambda: advance_account_baseline(state, frame.interval, frame.accounts, now=frame.interval.end),
            "BASELINE_BRIDGE_DAILY_PROFIT_MISMATCH")
    conventions, anchor, _ = anchor_fixture(previous=D("1"))
    state = initialize_baseline(conventions, anchor); frame = frame_for(state)
    refused(lambda: advance_account_baseline(state, frame.interval, frame.accounts, now=frame.interval.end),
            "BASELINE_BRIDGE_PRIOR_PROFIT_MISMATCH")


def test_bridge_midnight_opening_matches_real_prior_day_profit_without_first_day_reset():
    now = NOW.replace(hour=14, minute=59, second=50)
    conventions, anchor, accounts = anchor_fixture(now=now)
    state = initialize_account_baseline(conventions, anchor, accounts, now=now).state
    frame = profit_frame(state)
    update = advance_account_baseline(state, frame.interval, frame.accounts, now=frame.interval.end)
    assert update.state.day_start_equity == D("1018")
    assert update.state.day_open_realized_net_total_krw == D("18")
    assert update.state.observed_daily_loss == 0
    assert update.observation.risk.current_day_realized_net_profit == 0
    assert update.observation.risk.prior_day_realized_net_profit == D("18")
    assert not update.observation.risk.is_first_trading_day
    assert update.state.first_trading_day == state.first_trading_day


def test_bridge_rejects_hidden_external_flow_and_inclusive_endpoint_fill():
    state = initial(); end = state.asof+timedelta(seconds=10)
    deposit = ExternalFlow(flow_id="deposit", currency="KRW", kind="deposit", amount=D("1"),
                           effective_at=state.asof+timedelta(seconds=1))
    accounts = bundle(now=end, opening=D("1000"), cash=D("1001"), flows=(deposit,)).accounts
    frame = frame_for(state, accounts=accounts, equity_krw=D("1001"), maximum_equity_krw=D("1001"))
    refused(lambda: advance_account_baseline(state, frame.interval, accounts, now=end),
            "BASELINE_BRIDGE_INTERVAL_FLOW_REFUSED")
    buy = fill(quantity=D("1"), fee=D("1"), at=end)
    accounts = bundle(now=end, opening=D("1000"), cash=D("899"), units=D("1"), price=D("100"), fills=(buy,)).accounts
    frame = frame_for(state, accounts=accounts, equity_krw=D("999"), minimum_equity_krw=D("999"))
    refused(lambda: advance_account_baseline(state, frame.interval, accounts, now=end),
            "BASELINE_BRIDGE_CUTOFF_MISMATCH")


def test_provider_commits_before_head_cas_and_returns_only_after_readback_then_restarts():
    state = initial(); frame = profit_frame(state)
    with F.temp_home() as home:
        store = CheckpointStore(root=home); store.seed(state, expected_head=state.state_digest)
        head = Head(state.state_digest); original = head.compare_and_set
        def checked_cas(old, new):
            assert store.load(expected_head=new).sequence == 1
            return original(old, new)
        head.compare_and_set = checked_cas
        provider = ContinuousAccountProvider(source=lambda previous, now: frame, store=store, trusted_head=head)
        observed = provider(frame.interval.end)
        assert observed.risk.equity == D("1018") and len(head.commits) == 1
        restarted = ContinuousAccountProvider(source=lambda previous, now: frame,
            store=CheckpointStore(root=home), trusted_head=head)
        again = restarted(frame.interval.end)
        assert again == observed and len(head.commits) == 1
        assert store.load(expected_head=head.value).first_trading_day == state.first_trading_day


def test_same_tick_exact_redelivery_is_idempotent_but_changed_endpoint_is_not_cached():
    state = initial(); frame = frame_for(state); supplied = [frame]
    with F.temp_home() as home:
        store = CheckpointStore(root=home); store.seed(state, expected_head=state.state_digest)
        head = Head(state.state_digest); fetched = []
        def source(previous, now):
            fetched.append(previous.state_digest)
            return supplied[0]
        provider = ContinuousAccountProvider(source=source, store=store, trusted_head=head)
        first = provider(frame.interval.end)
        for _ in range(3):
            assert provider(frame.interval.end) == first
        assert len(fetched) == 4 and len(head.commits) == 1
        changed = replace(frame.accounts[0], opening_source_sha256="e"*64)
        supplied[0] = replace(frame, accounts=(changed,))
        refused(lambda: provider(frame.interval.end), "BASELINE_BRIDGE_ENDPOINT_CHANGED")
        assert len(fetched) == 5 and len(head.commits) == 1


def test_failed_external_cas_exposes_no_observation_and_requires_review_on_restart():
    state = initial(); frame = frame_for(state); fetched = []
    with F.temp_home() as home:
        store = CheckpointStore(root=home); store.seed(state, expected_head=state.state_digest)
        head = Head(state.state_digest)
        head.compare_and_set = lambda old, new: False
        def source(previous, now):
            fetched.append(previous.state_digest)
            return frame
        provider = ContinuousAccountProvider(source=source, store=store, trusted_head=head)
        refused(lambda: provider(frame.interval.end), "BASELINE_TRUSTED_HEAD_UPDATE_REFUSED")
        assert head.value == state.state_digest
        refused(lambda: provider(frame.interval.end), "BASELINE_PROVIDER_CHECKPOINT_REFUSED")
        assert len(fetched) == 1


def test_missing_store_and_naive_tick_fail_before_interval_source_or_implicit_seed():
    state = initial()
    with F.temp_home() as home:
        store = CheckpointStore(root=home); source = lambda previous, now: (_ for _ in ()).throw(AssertionError())
        provider = ContinuousAccountProvider(source=source, store=store, trusted_head=Head(state.state_digest))
        refused(lambda: provider(NOW.replace(tzinfo=None)), "BASELINE_PROVIDER_AWARE_TIME_REQUIRED")
        refused(lambda: provider(NOW), "BASELINE_PROVIDER_CHECKPOINT_REFUSED")
        assert not (home / "execution-baseline").exists()


def test_source_and_head_exceptions_are_sanitized_and_leave_previous_checkpoint():
    state = initial()
    def fail(*args):
        raise RuntimeError("private account detail")
    with F.temp_home() as home:
        store = CheckpointStore(root=home); store.seed(state, expected_head=state.state_digest)
        head = Head(state.state_digest)
        provider = ContinuousAccountProvider(source=fail, store=store, trusted_head=head)
        refused(lambda: provider(NOW), "BASELINE_INTERVAL_SOURCE_FAILED")
        head.read = fail
        refused(lambda: provider(NOW), "BASELINE_TRUSTED_HEAD_READ_FAILED")
        assert store.load(expected_head=state.state_digest) == state
