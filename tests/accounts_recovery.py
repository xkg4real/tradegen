"""Exact invented recovery-boundary evidence; no owner state or live source."""
from dataclasses import fields, replace
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
import hashlib
import json

from core.compliance.model import KST
from execution_accounts.baseline import (
    BaselineAnchor, BaselineConventions, BaselineError, advance_baseline,
    initialize_baseline, restore_state, risk_baseline, state_json,
)
from execution_accounts.baseline_bridge import (
    ContinuousAccountProvider, advance_account_baseline, initialize_account_baseline,
)
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import RiskBaseline, content_digest
from execution_accounts.provider import EvidenceError, build_observation
from execution_control.risk import RecoveryCheckpoint
from tests import compliance_fixtures as F
from tests.accounts_baseline import interval, refuses
from tests.accounts_baseline_integration import Head, anchor_fixture, frame_for, refused

D = Decimal
CUTOFF = datetime(2026, 10, 26, 22, tzinfo=KST)


def anchor_at(now=CUTOFF-timedelta(seconds=10), *, previous=None):
    baseline = RiskBaseline(day_start_equity=D("1000"), prior_high_watermark=D("1100"),
        observed_daily_loss=D("100"), approved_effective_floor=D("700"),
        first_trading_day=now.astimezone(KST).date()-timedelta(days=0 if previous is None else 1),
        asof=now, source_sha256="a"*64)
    anchor = BaselineAnchor(account_scope="boundary-fixture", baseline=baseline, equity_krw=D("900"),
        realized_net_total_krw=D("80"), day_open_realized_net_total_krw=D("100"),
        previous_day_realized_net_krw=previous, sequence=7)
    conventions = BaselineConventions(daily_loss="maximum_net_equity_loss_from_day_open",
        external_flows="no_external_flows", max_interval_seconds=300, recovery_cutoff_seconds=79200)
    return conventions, anchor


def baseline_at(now=CUTOFF-timedelta(seconds=10), *, previous=None):
    return initialize_baseline(*anchor_at(now, previous=previous))


def test_original_schema_one_json_digest_roundtrips_without_new_fields_or_migration():
    # Original schema order and representation are fixed independently of the new dataclasses.
    body = dict(schema_version=1, account_scope="legacy-fixture",
        conventions=dict(daily_loss="maximum_net_equity_loss_from_day_open", external_flows="no_external_flows",
                         max_interval_seconds=30), first_trading_day="2026-10-22",
        asof="2026-10-25T01:00:00+00:00", sequence=7, equity_krw="900", day_start_equity="1000",
        high_watermark="1100", observed_daily_loss="100", realized_net_total_krw="80",
        day_open_realized_net_total_krw="100", previous_day_realized_net_krw="10",
        approved_effective_floor="700", anchor_sha256="a"*64, previous_state_digest="", last_interval_digest="")
    original_body = json.dumps(list(body.values()), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    head = hashlib.sha256(original_body.encode()).hexdigest()
    body["state_digest"] = head
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    state = restore_state(raw, expected_head=head)
    assert state.schema_version == 1 and state.conventions.recovery_cutoff_seconds is None
    assert state.recovery_checkpoint is None and state_json(state) == raw
    changed = replace(state, conventions=replace(state.conventions, recovery_cutoff_seconds=79200))
    refuses(lambda: state_json(changed), "BASELINE_SCHEMA_CONVENTION_MISMATCH")


def test_cutoff_configuration_is_explicit_strict_and_legacy_null_preserves_behavior():
    conventions, anchor = anchor_at()
    assert initialize_baseline(conventions, anchor).schema_version == 2
    for value in (True, 79200.0, "79200", 0, 79199, 86400):
        refuses(lambda: initialize_baseline(replace(conventions, recovery_cutoff_seconds=value), anchor),
                "BASELINE_RECOVERY_CUTOFF_UNSUPPORTED")
    legacy = initialize_baseline(replace(conventions, recovery_cutoff_seconds=None), anchor)
    advanced = advance_baseline(legacy, interval(legacy, end=CUTOFF+timedelta(seconds=10)))
    assert advanced.schema_version == 1 and advanced.recovery_checkpoint is None


def test_first_day_exact_boundary_captures_real_equity_and_keeps_lifetime_loss_history():
    start = baseline_at()
    sample = interval(start, end=CUTOFF, equity_krw=D("950"), minimum_equity_krw=D("800"),
                      maximum_equity_krw=D("1200"))
    state = advance_baseline(start, sample)
    checkpoint = state.recovery_checkpoint
    assert checkpoint == RecoveryCheckpoint(cutoff_at=CUTOFF, equity_krw=D("950"), source_sha256=sample.source_sha256)
    assert state.high_watermark == D("1200") and state.observed_daily_loss == D("200")
    assert state.day_start_equity == start.day_start_equity and state.approved_effective_floor == start.approved_effective_floor
    after = advance_baseline(state, interval(state, equity_krw=D("1100"), minimum_equity_krw=D("950"),
                                            maximum_equity_krw=D("1100")))
    assert after.recovery_checkpoint == checkpoint and after.observed_daily_loss == D("200")
    assert after.high_watermark == D("1200") and after.first_trading_day == start.first_trading_day
    assert risk_baseline(after, now=after.asof, expected_head=after.state_digest).recovery_checkpoint == checkpoint
    assert advance_baseline(state, sample) is state


def test_zero_prior_profit_needs_boundary_but_positive_or_negative_prior_profit_does_not():
    zero = baseline_at(previous=D("0"))
    refuses(lambda: advance_baseline(zero, interval(zero, end=CUTOFF+timedelta(seconds=1))),
            "BASELINE_RECOVERY_BOUNDARY_REQUIRED")
    assert advance_baseline(zero, interval(zero, end=CUTOFF)).recovery_checkpoint is not None
    for previous in (D("1"), D("-1")):
        state = baseline_at(previous=previous)
        after = advance_baseline(state, interval(state, end=CUTOFF+timedelta(seconds=10)))
        assert after.recovery_checkpoint is None


def test_missing_exact_boundary_refuses_and_pre_cutoff_observation_cannot_leak_after_deadline():
    state = baseline_at(CUTOFF-timedelta(seconds=1))
    assert risk_baseline(state, now=state.asof, expected_head=state.state_digest).asof == state.asof
    for now in (CUTOFF, CUTOFF+timedelta(seconds=1)):
        refuses(lambda: risk_baseline(state, now=now, expected_head=state.state_digest),
                "BASELINE_RECOVERY_BOUNDARY_REQUIRED")
    refuses(lambda: advance_baseline(state, interval(state, end=CUTOFF+timedelta(seconds=1))),
            "BASELINE_RECOVERY_BOUNDARY_REQUIRED")
    exact = advance_baseline(state, interval(state, end=CUTOFF))
    assert exact.recovery_checkpoint.cutoff_at == CUTOFF


def test_exact_anchor_can_capture_boundary_but_late_anchor_never_invents_recovery():
    exact = baseline_at(CUTOFF)
    assert exact.recovery_checkpoint.cutoff_at == CUTOFF
    assert exact.recovery_checkpoint.equity_krw == exact.equity_krw
    late = baseline_at(CUTOFF+timedelta(seconds=10))
    assert late.recovery_checkpoint is None
    assert risk_baseline(late, now=late.asof, expected_head=late.state_digest).recovery_checkpoint is None
    after = advance_baseline(late, interval(late, equity_krw=D("1000"), maximum_equity_krw=D("1000")))
    assert after.recovery_checkpoint is None
    conventions, anchor = anchor_at(late.asof)
    claimed = replace(anchor, baseline=replace(anchor.baseline, recovery_checkpoint=exact.recovery_checkpoint))
    refuses(lambda: initialize_baseline(conventions, claimed), "BASELINE_RECOVERY_ANCHOR_REFUSED")


def test_boundary_proof_survives_exact_serialization_and_refuses_tampering():
    state = baseline_at(); state = advance_baseline(state, interval(state, end=CUTOFF))
    with localcontext() as numeric:
        numeric.prec = 2
        restored = restore_state(state_json(state), expected_head=state.state_digest)
    assert restored == state and restored.schema_version == 2
    changed = replace(state, recovery_checkpoint=replace(state.recovery_checkpoint, source_sha256="d"*64))
    refuses(lambda: state_json(changed), "BASELINE_STATE_CHANGED")
    body = json.loads(state_json(state)); body["recovery_checkpoint"]["equity_krw"] = 900
    refuses(lambda: restore_state(json.dumps(body), expected_head=state.state_digest), "BASELINE_CHECKPOINT_NUMBER_INVALID")
    body = json.loads(state_json(state)); body["recovery_checkpoint"]["extra"] = True
    refuses(lambda: restore_state(json.dumps(body), expected_head=state.state_digest), "BASELINE_CHECKPOINT_SCHEMA_INVALID")
    body = json.loads(state_json(state)); body["recovery_checkpoint"] = None
    refuses(lambda: restore_state(json.dumps(body), expected_head=state.state_digest), "BASELINE_RECOVERY_BOUNDARY_REQUIRED")


def test_boundary_proof_resets_only_at_seoul_midnight_and_keeps_lifetime_anchor():
    start = baseline_at(); state = advance_baseline(start, interval(start, end=CUTOFF))
    proof = state.recovery_checkpoint
    midnight = CUTOFF+timedelta(hours=2)
    while state.asof < midnight:
        end = min(state.asof+timedelta(seconds=300), midnight)
        state = advance_baseline(state, interval(state, end=end))
        if end < midnight:
            assert state.recovery_checkpoint == proof and state.observed_daily_loss == D("100")
    assert state.recovery_checkpoint is None and state.observed_daily_loss == 0
    assert state.day_start_equity == D("900") and state.high_watermark == D("1100")
    assert state.first_trading_day == start.first_trading_day and state.anchor_sha256 == start.anchor_sha256
    assert state.previous_day_realized_net_krw == D("-20")


def test_boundary_bridge_and_durable_provider_reconcile_capture_repeat_and_restart():
    conventions, anchor, accounts = anchor_fixture(now=CUTOFF-timedelta(seconds=10))
    conventions = replace(conventions, recovery_cutoff_seconds=79200)
    state = initialize_account_baseline(conventions, anchor, accounts, now=anchor.baseline.asof).state
    frame = frame_for(state, end=CUTOFF)
    with F.temp_home() as home:
        store = CheckpointStore(root=home); store.seed(state, expected_head=state.state_digest)
        head = Head(state.state_digest)
        provider = ContinuousAccountProvider(source=lambda previous, now: frame, store=store, trusted_head=head)
        observation = provider(CUTOFF)
        checkpoint = observation.risk.recovery_checkpoint
        assert checkpoint.cutoff_at == CUTOFF and checkpoint.equity_krw == D("1000")
        assert checkpoint.source_sha256 == frame.interval.source_sha256
        restarted = ContinuousAccountProvider(source=lambda previous, now: frame,
            store=CheckpointStore(root=home), trusted_head=head)
        assert restarted(CUTOFF).risk.recovery_checkpoint == checkpoint and len(head.commits) == 1
        persisted = store.load(expected_head=head.value)
        following = frame_for(persisted)
        next_provider = ContinuousAccountProvider(source=lambda previous, now: following, store=store, trusted_head=head)
        assert next_provider(following.interval.end).risk.recovery_checkpoint == checkpoint
        assert store.load(expected_head=head.value).recovery_checkpoint == checkpoint and len(head.commits) == 2


def test_direct_store_commit_cannot_reset_daily_history_or_erase_established_proof():
    start = baseline_at()
    boundary = advance_baseline(start, interval(start, end=CUTOFF, minimum_equity_krw=D("800")))
    after = advance_baseline(boundary, interval(boundary, equity_krw=D("1000"), maximum_equity_krw=D("1000")))
    def reheaded(**changes):
        # A valid self-consistent local hash still cannot authorize a historical reset.
        candidate = replace(after, **changes)
        digest_body = tuple(getattr(candidate, field.name) for field in fields(candidate) if field.name != "state_digest")
        return replace(candidate, state_digest=content_digest(digest_body))
    with F.temp_home() as home:
        store = CheckpointStore(root=home); store.seed(start, expected_head=start.state_digest)
        store.commit(boundary, expected_previous_head=start.state_digest)
        for changes in (dict(observed_daily_loss=D("100")), dict(day_start_equity=D("900"))):
            candidate = reheaded(**changes)
            assert restore_state(state_json(candidate), expected_head=candidate.state_digest) == candidate
            refused(lambda: store.commit(candidate, expected_previous_head=boundary.state_digest),
                    "BASELINE_STORE_DAILY_HISTORY_CHANGED")
        candidate = reheaded(recovery_checkpoint=None)
        assert restore_state(state_json(candidate), expected_head=candidate.state_digest) == candidate
        refused(lambda: store.commit(candidate, expected_previous_head=boundary.state_digest),
                "BASELINE_STORE_RECOVERY_CHANGED")
        assert store.load(expected_head=boundary.state_digest) == boundary


def test_bridge_stale_pre_deadline_frame_and_changed_endpoint_never_create_proof():
    conventions, anchor, accounts = anchor_fixture(now=CUTOFF-timedelta(seconds=20))
    state = initialize_account_baseline(replace(conventions, recovery_cutoff_seconds=79200), anchor,
                                        accounts, now=anchor.baseline.asof).state
    frame = frame_for(state)
    refused(lambda: advance_account_baseline(state, frame.interval, frame.accounts, now=CUTOFF),
            "BASELINE_BRIDGE_EVIDENCE_REFUSED")
    exact = frame_for(state, end=CUTOFF)
    altered = (replace(exact.accounts[0], opening_source_sha256="e"*64),)
    refused(lambda: advance_account_baseline(state, exact.interval, altered, now=CUTOFF),
            "BASELINE_BRIDGE_ENDPOINT_CHANGED")


def test_provider_recovery_proof_must_match_day_timestamp_actual_equity_and_loss_history():
    conventions, anchor, accounts = anchor_fixture(now=CUTOFF)
    update = initialize_account_baseline(replace(conventions, recovery_cutoff_seconds=79200),
                                         anchor, accounts, now=CUTOFF)
    assert update.observation.risk.recovery_checkpoint.equity_krw == D("1000")
    checkpoint = update.state.recovery_checkpoint
    cases = (
        (replace(checkpoint, cutoff_at=CUTOFF-timedelta(days=1)), "RECOVERY_CHECKPOINT_INVALID", D("0")),
        (replace(checkpoint, cutoff_at=CUTOFF+timedelta(seconds=1)), "RECOVERY_CHECKPOINT_INVALID", D("0")),
        (replace(checkpoint, equity_krw=D("999")), "RECOVERY_HISTORY_CONTRADICTION", D("0")),
        (replace(checkpoint, equity_krw=D("999")), "RECOVERY_EQUITY_CONTRADICTION", D("1")),
    )
    for proof, code, loss in cases:
        bad = replace(update.bundle, risk_baseline=replace(update.bundle.risk_baseline,
                      recovery_checkpoint=proof, observed_daily_loss=loss))
        try:
            build_observation(bad, now=CUTOFF)
        except EvidenceError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected recovery evidence refusal")
