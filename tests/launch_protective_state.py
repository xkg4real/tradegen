"""Invented facts for the pure reducer, never signed owner evidence or trading authorization.

No key, home, clock, source, account or order provider is used. Eligibility values
are deliberate test inputs; these tests do not establish an operational verifier.
"""
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone

from execution_launch import protective_state as P

T = datetime(2031, 1, 1, tzinfo=timezone.utc)
_DEFAULT = object()


def policy(**changes):
    values = dict(management_id="invented-management", account_scope="invented-account", venue="upbit",
                  market="spot", quote_currency="KRW", symbol="KRW-BTC", code_sha256="1" * 64,
                  strategy_sha256="2" * 64, risk_policy_sha256="3" * 64,
                  holding_deadline=T + timedelta(hours=1), monitor_until=T + timedelta(hours=2))
    return P.ManagementPolicy(**(values | changes))


def authority(p, at=T, **changes):
    values = dict(policy_sha256=P.policy_digest(p), checked_at=at, issued_at=T - timedelta(days=1),
                  accepted=True, revoked=False, entry_until=T + timedelta(hours=1),
                  reduce_until=T + timedelta(minutes=90), cancel_until=T + timedelta(minutes=110),
                  monitor_until=T + timedelta(hours=2))
    return P.AuthorityFacts(**(values | changes))


def facts(p, at=T, **changes):
    values = dict(policy_sha256=P.policy_digest(p), evidence_sha256="4" * 64, checked_at=at,
                  monitoring_ok=True, account_ok=True, market_ok=True, recording_ok=True, strategy_ok=True,
                  risk_ok=True, orders_known=True, no_pending_reduce=True, entry_eligible=True,
                  reduce_eligible=True, recovery_complete=False, halted=False, strategy_verdict="hold",
                  risk_causes=())
    return P.ObservationFacts(**(values | changes))


def event(previous, kind="assessment", at=T, **changes):
    values = dict(sequence=previous.sequence + 1, previous_state_sha256=P.state_digest(previous), at=at, kind=kind)
    return P.ManagementEvent(**(values | changes))


def step(p, previous, kind="assessment", at=T, *, auth=_DEFAULT, obs=_DEFAULT, **event_changes):
    return P.reduce_management(p, previous, event(previous, kind, at, **event_changes),
                               authority=authority(p, at) if auth is _DEFAULT else auth,
                               observations=facts(p, at) if obs is _DEFAULT else obs)


def rejected(call, code=None, *, error=P.ProtectiveStateError):
    try:
        call()
    except error as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected rejection")


def reductions(effects):
    return tuple(item for item in effects if item.kind == "consider_reduce")


def test_unassessed_or_missing_facts_never_claim_permission_or_strategy_hold():
    p = policy()
    original = P.initial_state(p)
    assert original.strategy_verdict == "unavailable"
    assert not any((original.can_enter, original.can_reduce, original.can_cancel, original.can_observe))
    for auth, obs in ((None, None), (None, facts(p, strategy_verdict="sell")), (authority(p), None)):
        result, effects = step(p, original, auth=auth, obs=obs)
        assert result.strategy_verdict == "unavailable" and not result.can_enter and not result.can_reduce
        assert not reductions(effects)
    assert original.sequence == 0 and original.phase == "waiting_inputs"
    rejected(lambda: setattr(original, "phase", "monitoring"), error=FrozenInstanceError)


def test_valid_hold_is_distinct_from_unavailable_even_when_the_account_remains_held():
    p, start = policy(), P.initial_state(policy())
    held, effects = step(p, start)
    assert held.strategy_verdict == "hold" and held.phase == "monitoring" and held.can_enter
    assert not reductions(effects)
    for changes in ({"strategy_ok": False}, {"strategy_verdict": "unavailable"}, {"market_ok": False}):
        unknown, effects = step(p, start, obs=facts(p, **changes))
        assert unknown.strategy_verdict == "unavailable" and not unknown.can_enter
        assert not reductions(effects)


def test_deadline_with_even_sell_facts_only_blocks_entry_and_requests_management_once():
    p = policy()
    before = P.initial_state(p)
    at = p.holding_deadline
    evidence = facts(p, at, strategy_verdict="sell", risk_causes=("trailing_condition",))
    request = event(before, "deadline", at)
    after, effects = P.reduce_management(p, before, request, authority=authority(p, at), observations=evidence)
    assert after.deadline_seen and after.entry_blocked and not after.can_enter and after.phase == "renewal_pending"
    assert not reductions(effects)
    requests = [item for item in effects if item.kind == "request_management_approval"]
    assert len(requests) == 1 and requests[0].intent_id == after.renewal_request_id
    same, duplicate = P.reduce_management(p, after, request, authority=authority(p, at), observations=evidence)
    assert same is after and duplicate == ()
    later, repeated = step(p, after, "deadline", at + timedelta(seconds=1))
    assert later.renewal_request_id == after.renewal_request_id and not reductions(repeated)
    assert all(item.kind != "request_management_approval" for item in repeated)
    rejected(lambda: step(p, before, "deadline", at - timedelta(microseconds=1)), "PROTECTIVE_DEADLINE_NOT_DUE")


def test_a_missed_deadline_timer_still_blocks_entry_and_cannot_extend_the_policy():
    p = policy()
    at = p.holding_deadline + timedelta(seconds=20)
    after, effects = step(p, P.initial_state(p), at=at)
    assert after.deadline_seen and not after.can_enter and not reductions(effects)
    assert sum(item.kind == "request_management_approval" for item in effects) == 1
    updated, effects = step(p, after, "authority_updated", at + timedelta(seconds=1),
                           auth=authority(p, at + timedelta(seconds=1), entry_until=p.monitor_until))
    assert updated.entry_blocked and not updated.can_enter and not reductions(effects)
    rejected(lambda: step(p, updated, "entry_reauthorized", at + timedelta(seconds=2),
                          auth=authority(p, at + timedelta(seconds=2), entry_until=p.monitor_until)),
             "PROTECTIVE_ENTRY_REAUTHORIZATION_UNVERIFIED")


def test_each_operational_fault_is_never_a_sell_and_does_not_automatically_rearm():
    p = policy()
    for fault in ("inputs_missing", "strategy_error", "account_unavailable", "storage_unavailable",
                  "settings_missing", "clock_unreliable"):
        after, effects = step(p, P.initial_state(p), "fault", fault=fault,
                              obs=facts(p, strategy_verdict="sell", risk_causes=("daily_band_condition",)))
        assert after.entry_blocked and after.strategy_verdict == "unavailable"
        assert not after.can_enter and not after.can_reduce and not reductions(effects)
        recovered_inputs, effects = step(p, after, at=T + timedelta(seconds=1))
        assert recovered_inputs.strategy_verdict == "hold" and recovered_inputs.entry_blocked
        assert not recovered_inputs.can_enter and not reductions(effects)


def test_fault_categories_mask_contradictory_healthy_capability_facts():
    p = policy()
    storage, effects = step(p, P.initial_state(p), "fault", fault="storage_unavailable")
    assert not storage.can_record and not storage.can_cancel and not storage.can_reduce
    assert storage.can_observe and storage.can_evaluate_risk and not reductions(effects)
    account, effects = step(p, P.initial_state(p), "fault", fault="account_unavailable")
    assert account.can_observe and not account.can_evaluate_risk and not account.can_cancel
    assert account.strategy_verdict == "unavailable" and not reductions(effects)
    at = p.holding_deadline + timedelta(seconds=1)
    clock, effects = step(p, P.initial_state(p), "fault", at, fault="clock_unreliable")
    assert not any((clock.can_observe, clock.can_record, clock.can_cancel, clock.can_reduce, clock.can_enter))
    assert not clock.deadline_seen and clock.renewal_request_id is None and clock.last_event_at is None
    assert all(item.kind != "request_management_approval" for item in effects)


def test_unreliable_clock_jumps_do_not_poison_trusted_chronology_or_bypass_normal_rollback_checks():
    p = policy()
    trusted, _ = step(p, P.initial_state(p))
    for jumped in (T + timedelta(days=365), T - timedelta(days=365)):
        faulted, effects = step(p, trusted, "fault", jumped, fault="clock_unreliable")
        assert faulted.last_event_at == T and not faulted.deadline_seen and not reductions(effects)
        restored, effects = step(p, faulted, at=T + timedelta(seconds=1))
        assert restored.last_event_at == T + timedelta(seconds=1) and restored.entry_blocked
        assert not restored.can_enter and not reductions(effects)
        rejected(lambda: step(p, faulted, at=T - timedelta(microseconds=1)), "PROTECTIVE_CLOCK_ROLLBACK")
    initial_fault, _ = step(p, P.initial_state(p), "fault", T + timedelta(days=365), fault="clock_unreliable")
    assert initial_fault.last_event_at is None
    restored, _ = step(p, initial_fault, at=T)
    assert restored.last_event_at == T and restored.entry_blocked


def test_restart_requires_reconciliation_and_recovery_completion_does_not_rearm_or_sell():
    p = policy()
    stopped, effects = step(p, P.initial_state(p), "restart", obs=facts(p, strategy_verdict="sell"))
    assert stopped.recovering and stopped.phase == "recovering" and stopped.entry_blocked
    assert not reductions(effects) and sum(item.kind == "reconcile" for item in effects) == 1
    still, effects = step(p, stopped, at=T + timedelta(seconds=1),
                          obs=facts(p, T + timedelta(seconds=1), strategy_verdict="sell"))
    assert still.recovering and still.strategy_verdict == "unavailable" and not reductions(effects)
    rejected(lambda: step(p, still, "recovery_complete", T + timedelta(seconds=2)), "PROTECTIVE_RECOVERY_UNVERIFIED")
    ready, effects = step(p, still, "recovery_complete", T + timedelta(seconds=2),
                          obs=facts(p, T + timedelta(seconds=2), recovery_complete=True, strategy_verdict="sell"))
    assert not ready.recovering and ready.entry_blocked and not ready.can_enter and not reductions(effects)
    assessed, effects = step(p, ready, at=T + timedelta(seconds=3),
                             obs=facts(p, T + timedelta(seconds=3), strategy_verdict="sell"))
    assert assessed.can_reduce and len(reductions(effects)) == 1 and not assessed.can_enter


def test_separately_eligible_known_order_cancel_can_remain_available_during_recovery_without_an_effect():
    p = policy()
    recovering, effects = step(p, P.initial_state(p), "restart")
    assert recovering.can_cancel and not recovering.can_reduce
    assert {item.kind for item in effects} == {"block_entry", "reconcile"}
    for changes in ({"orders_known": False}, {"account_ok": False}, {"recording_ok": False}):
        blocked, effects = step(p, P.initial_state(p), "restart", obs=facts(p, **changes))
        assert not blocked.can_cancel and not reductions(effects)


def test_only_independent_strategy_or_risk_assessment_causes_reduction_consideration():
    p = policy()
    for changes, cause in (({"strategy_verdict": "sell"}, "strategy_sell"),
                            ({"risk_causes": ("trailing_condition",)}, "trailing_condition"),
                            ({"risk_causes": ("floor_band_condition",)}, "floor_band_condition"),
                            ({"risk_causes": ("daily_band_condition",)}, "daily_band_condition")):
        after, effects = step(p, P.initial_state(p), obs=facts(p, **changes))
        proposed = reductions(effects)
        assert after.phase == "exit_pending" and len(proposed) == 1
        assert proposed[0].reason == cause and proposed[0].evidence_sha256 == "4" * 64
        assert proposed[0].not_after == T + timedelta(minutes=90)
    # A valid independent risk cause can be assessed even while the strategy cannot decide.
    after, effects = step(p, P.initial_state(p), obs=facts(p, strategy_ok=False,
                          risk_causes=("daily_band_condition",)))
    assert after.strategy_verdict == "unavailable" and len(reductions(effects)) == 1


def test_a_known_risk_without_reducing_authority_is_distinct_from_an_ordinary_hold():
    p = policy()
    blocked, effects = step(p, P.initial_state(p), auth=authority(p, reduce_until=None),
                           obs=facts(p, risk_causes=("floor_band_condition",)))
    assert blocked.can_evaluate_risk and not blocked.can_reduce and not reductions(effects)
    assert "PROTECTIVE_KNOWN_RISK_REDUCTION_UNAVAILABLE" in blocked.reasons
    held, _ = step(p, P.initial_state(p), auth=authority(p, reduce_until=None))
    assert "PROTECTIVE_KNOWN_RISK_REDUCTION_UNAVAILABLE" not in held.reasons
    unknown, _ = step(p, P.initial_state(p), obs=facts(p, risk_ok=False,
                       risk_causes=("floor_band_condition",)))
    assert "PROTECTIVE_KNOWN_RISK_REDUCTION_UNAVAILABLE" not in unknown.reasons


def test_a_sell_verdict_cannot_also_claim_entry_eligibility():
    p = policy()
    selling, effects = step(p, P.initial_state(p), obs=facts(p, strategy_verdict="sell", entry_eligible=True))
    assert selling.strategy_verdict == "sell" and not selling.can_enter
    assert len(reductions(effects)) == 1
    blocked, _ = step(p, P.initial_state(p), "fault", fault="strategy_error")
    rejected(lambda: step(p, blocked, "entry_reauthorized", obs=facts(p, strategy_verdict="sell")),
             "PROTECTIVE_ENTRY_REAUTHORIZATION_UNVERIFIED")


def test_each_required_reduction_gate_blocks_consideration_without_fabricating_a_hold():
    p = policy()
    for name in ("monitoring_ok", "account_ok", "market_ok", "recording_ok", "risk_ok", "orders_known",
                 "no_pending_reduce", "reduce_eligible"):
        after, effects = step(p, P.initial_state(p), obs=facts(p, strategy_verdict="sell", **{name: False}))
        assert not after.can_reduce and not reductions(effects), name
    after, effects = step(p, P.initial_state(p), obs=facts(p, strategy_ok=False, strategy_verdict="sell"))
    assert after.strategy_verdict == "unavailable" and not reductions(effects)


def test_halt_blocks_entry_while_the_existing_reducing_gate_independently_decides_eligibility():
    p = policy()
    for allowed in (True, False):
        halted, effects = step(p, P.initial_state(p), obs=facts(p, halted=True, reduce_eligible=allowed,
                              strategy_verdict="sell"))
        assert halted.halted and halted.phase == "halted" and halted.entry_blocked and not halted.can_enter
        assert halted.can_reduce is allowed and bool(reductions(effects)) is allowed
        later, effects = step(p, halted, at=T + timedelta(seconds=1), obs=facts(p, T + timedelta(seconds=1)))
        assert later.halted and later.entry_blocked and not later.can_enter
        assert not reductions(effects)  # A halt alone is not an independent sell cause.


def test_authority_acceptance_revocation_scope_and_exact_expiry_are_all_required():
    p = policy()
    evidence = facts(p, strategy_verdict="sell")
    for changes in ({"accepted": False}, {"revoked": True}, {"reduce_until": None}, {"reduce_until": T},
                    {"monitor_until": None}, {"issued_at": T + timedelta(seconds=1)}):
        after, effects = step(p, P.initial_state(p), auth=authority(p, **changes), obs=evidence)
        assert not after.can_reduce and not reductions(effects)
    for changes, expected in (({"entry_until": T}, (False, True, True)),
                              ({"reduce_until": T}, (True, False, True)),
                              ({"cancel_until": T}, (True, True, False))):
        after, effects = step(p, P.initial_state(p), auth=authority(p, **changes))
        assert (after.can_enter, after.can_reduce, after.can_cancel) == expected
        assert not reductions(effects)
    immediately_before = T - timedelta(microseconds=1)
    after, effects = step(p, P.initial_state(p), at=immediately_before,
                          auth=authority(p, immediately_before, reduce_until=T),
                          obs=facts(p, immediately_before, strategy_verdict="sell"))
    assert after.can_reduce and len(reductions(effects)) == 1


def test_deadline_does_not_remove_a_separately_valid_reduce_scope_or_create_one():
    p = policy()
    at = p.holding_deadline
    pending, effects = step(p, P.initial_state(p), "deadline", at)
    assert not reductions(effects)
    at += timedelta(seconds=1)
    reduced, effects = step(p, pending, at=at, obs=facts(p, at, strategy_verdict="sell"))
    assert not reduced.can_enter and reduced.can_reduce and len(reductions(effects)) == 1
    denied, effects = step(p, pending, at=at, auth=authority(p, at, reduce_until=p.holding_deadline),
                          obs=facts(p, at, strategy_verdict="sell"))
    assert not denied.can_reduce and not reductions(effects)


def test_monitor_end_hands_management_back_without_sale_or_implicit_grace():
    p = policy()
    at = p.monitor_until
    late = authority(p, at, entry_until=at + timedelta(hours=1), reduce_until=at + timedelta(hours=1),
                     monitor_until=at + timedelta(hours=1))
    ended, effects = step(p, P.initial_state(p), at=at, auth=late, obs=facts(p, at, strategy_verdict="sell"))
    assert ended.phase == "owner_action_required" and not ended.can_observe and not ended.can_reduce
    assert ended.deadline_seen and ended.entry_blocked and not reductions(effects)
    assert p.monitor_until == at  # The longer fact cannot amend the frozen policy.


def test_pending_outbox_or_order_prevents_a_second_intent_even_with_new_evidence():
    p = policy()
    first, effects = step(p, P.initial_state(p), obs=facts(p, strategy_verdict="sell"))
    original = reductions(effects)[0]
    at = T + timedelta(seconds=1)
    pending, effects = step(p, first, at=at, obs=facts(p, at, strategy_verdict="sell", no_pending_reduce=False,
                            evidence_sha256="5" * 64))
    assert pending.phase == "exit_pending" and not pending.can_reduce and not reductions(effects)
    assert pending.last_reduce_intent_id == original.intent_id
    # Re-observing identical settled evidence does not duplicate the original consideration either.
    same, effects = step(p, first, at=at, obs=facts(p, at, strategy_verdict="sell"))
    assert not reductions(effects) and same.last_reduce_intent_id == original.intent_id


def test_pending_reduce_blocks_entry_and_rearm_when_a_later_strategy_returns_hold():
    p = policy()
    selling, effects = step(p, P.initial_state(p), obs=facts(p, strategy_verdict="sell"))
    assert len(reductions(effects)) == 1
    at = T + timedelta(seconds=1)
    # This fact covers both an unapplied queued intent and a partially filled sell:
    # a current broker-side entry gate alone cannot establish that the outbox is clear.
    holding, effects = step(p, selling, at=at, obs=facts(p, at, no_pending_reduce=False,
                            strategy_verdict="hold", entry_eligible=True, evidence_sha256="5" * 64))
    assert holding.strategy_verdict == "hold" and holding.phase == "exit_pending"
    assert not holding.can_enter and not holding.can_reduce and not reductions(effects)
    at += timedelta(seconds=1)
    rejected(lambda: step(p, holding, "entry_reauthorized", at,
                          obs=facts(p, at, no_pending_reduce=False)),
             "PROTECTIVE_ENTRY_REAUTHORIZATION_UNVERIFIED")
    cleared, effects = step(p, holding, "entry_reauthorized", at,
                           obs=facts(p, at, no_pending_reduce=True))
    assert cleared.can_enter and cleared.phase == "monitoring" and not reductions(effects)


def test_close_is_not_a_claim_of_flatness_and_cannot_be_reopened_by_new_facts():
    p = policy()
    closed, effects = step(p, P.initial_state(p), "close", obs=facts(p, strategy_verdict="sell"))
    assert closed.phase == "closed" and closed.entry_blocked
    assert not any((closed.can_enter, closed.can_reduce, closed.can_cancel, closed.can_observe))
    assert not reductions(effects)
    again, effects = step(p, closed, at=p.holding_deadline, obs=facts(p, p.holding_deadline, strategy_verdict="sell"))
    assert again.phase == "closed" and not effects and again.renewal_request_id is None
    assert not any("flat" in str(value).lower() for value in asdict(again).values())


def test_current_context_and_same_policy_are_required_before_any_eligibility():
    p, start = policy(), P.initial_state(policy())
    for auth, obs, code in ((authority(p, T + timedelta(microseconds=1)), facts(p), "PROTECTIVE_FACTS_NOT_CURRENT"),
                            (authority(p), facts(p, T - timedelta(microseconds=1)), "PROTECTIVE_FACTS_NOT_CURRENT"),
                            (authority(p, policy_sha256="0" * 64), facts(p), "PROTECTIVE_POLICY_BINDING_MISMATCH"),
                            (authority(p), facts(p, policy_sha256="0" * 64), "PROTECTIVE_POLICY_BINDING_MISMATCH")):
        rejected(lambda auth=auth, obs=obs: step(p, start, auth=auth, obs=obs), code)
    rejected(lambda: step(policy(account_scope="another-account"), start), "PROTECTIVE_POLICY_BINDING_MISMATCH")
    assert start.sequence == 0


def test_rewritten_duplicate_out_of_order_events_and_clock_rollback_refuse_without_state_change():
    p, original = policy(), P.initial_state(policy())
    first = event(original)
    after, effects = P.reduce_management(p, original, first, authority=authority(p), observations=facts(p))
    for modified in (facts(p, strategy_verdict="sell"), facts(p, evidence_sha256="5" * 64)):
        rejected(lambda modified=modified: P.reduce_management(p, after, first, authority=authority(p),
                                                               observations=modified), "PROTECTIVE_EVENT_REWRITTEN")
    rejected(lambda: P.reduce_management(p, after, first, authority=authority(p, revoked=True), observations=facts(p)),
             "PROTECTIVE_EVENT_REWRITTEN")
    rejected(lambda: step(p, after, sequence=after.sequence + 2), "PROTECTIVE_EVENT_SEQUENCE_INVALID")
    rejected(lambda: step(p, after, previous_state_sha256="0" * 64), "PROTECTIVE_EVENT_SEQUENCE_INVALID")
    rejected(lambda: step(p, after, at=T - timedelta(microseconds=1)), "PROTECTIVE_CLOCK_ROLLBACK")
    assert after.sequence == 1 and original.sequence == 0


def test_entry_reauthorization_is_explicit_current_and_never_implied_by_management_recovery():
    p = policy()
    blocked, _ = step(p, P.initial_state(p), "fault", fault="strategy_error")
    updated, _ = step(p, blocked, "authority_updated", at=T + timedelta(seconds=1))
    assert updated.entry_blocked and not updated.can_enter
    at = T + timedelta(seconds=2)
    rejected(lambda: step(p, updated, "entry_reauthorized", at, obs=facts(p, at, strategy_verdict="unavailable")),
             "PROTECTIVE_ENTRY_REAUTHORIZATION_UNVERIFIED")
    ready, effects = step(p, updated, "entry_reauthorized", at)
    assert not ready.entry_blocked and ready.can_enter and not reductions(effects)


def test_all_authority_scopes_are_explicit_and_closed_types_reject_coercion_or_fault_as_risk():
    p = policy()
    rejected(lambda: P.AuthorityFacts(), error=TypeError)
    rejected(lambda: authority(p, accepted=1), "PROTECTIVE_AUTHORITY_FACTS_INVALID")
    rejected(lambda: facts(p, no_pending_reduce=1), "PROTECTIVE_OBSERVATION_FACTS_INVALID")
    rejected(lambda: facts(p, risk_causes=("storage_unavailable",)), "PROTECTIVE_OBSERVATION_FACTS_INVALID")
    rejected(lambda: facts(p, risk_causes=["trailing_condition"]), "PROTECTIVE_OBSERVATION_FACTS_INVALID")
    rejected(lambda: facts(p, risk_causes=("trailing_condition", "trailing_condition")),
             "PROTECTIVE_OBSERVATION_FACTS_INVALID")
    rejected(lambda: event(P.initial_state(p), sequence=True), "PROTECTIVE_EVENT_INVALID")
    rejected(lambda: event(P.initial_state(p), "fault", fault="private provider exception"), "PROTECTIVE_EVENT_INVALID")
    rejected(lambda: policy(venue="kis"), "PROTECTIVE_SCOPE_UNSUPPORTED")
    rejected(lambda: policy(market="futures"), "PROTECTIVE_SCOPE_UNSUPPORTED")
    class StringSubclass(str):
        pass
    for key, value in (("venue", "upbit"), ("market", "spot"), ("quote_currency", "KRW")):
        rejected(lambda key=key, value=value: policy(**{key: StringSubclass(value)}), "PROTECTIVE_SCOPE_UNSUPPORTED")
    rejected(lambda: policy(holding_deadline=T.replace(tzinfo=None)), "PROTECTIVE_TIME_INVALID")
    rejected(lambda: policy(monitor_until=T), "PROTECTIVE_POLICY_INVALID")
    object.__setattr__(p, "symbol", "BTC")
    rejected(lambda: P.initial_state(p), "PROTECTIVE_SCOPE_UNSUPPORTED")
