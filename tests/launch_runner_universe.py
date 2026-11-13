"""Universe runner checks (spec sections 7, 9 and 10): the buy allow-list, the snapshot in force, the session's bound
batch, the sell guard, the flat re-check of a cross-coin renewal and preparation with a batch. Invented data,
temporary signed homes and dry adapters only; no network."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from execution_launch import runner as R
from execution_launch.profile import profile_digest
from execution_launch.runner import LaunchSession, Runner, RunnerError
from tests.control_session import selected
from tests.launch_runner import creates, runner_fixture

D = Decimal
RULE, SNAPSHOT, BATCH = "e" * 64, "5" * 64, "b" * 64
BTC, XRP = "KRW-BTC", "KRW-XRP"


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected refusal " + code)


def universe_profile(profile):
    """`profile` as a universe launch profile: the rule sha256 and IOC orders (spec section 10; PR 4b, PR 4c)."""
    return replace(profile, universe_rule_sha256=RULE, time_in_force="ioc")


def universe_snapshot(now, *, rule=RULE, valid_from=None, valid_until=None):
    """A Universe in force from an hour before `now` for one day: BTC and XRP listed and eligible, BTC first."""
    start = now - timedelta(hours=1) if valid_from is None else valid_from
    return M.Universe(day=start.astimezone(timezone.utc).date(), rule_sha256=rule, snapshot_sha256=SNAPSHOT,
                      built_at=start - timedelta(minutes=10), valid_from=start,
                      valid_until=start + timedelta(days=1) if valid_until is None else valid_until,
                      listed=(BTC, XRP), eligible=((BTC, D("900000000000")), (XRP, D("100000000000"))))


def holding(env, units="0.001"):
    """env.observation holding `units` BTC, as tests/launch_runner.py's exit tests set it."""
    return replace(env.observation,
                   positions=replace(env.observation.positions, holdings={("upbit", "BTC"): float(units)}),
                   holdings={("upbit", "fixture-account", "spot", BTC): D(units)})


@contextmanager
def universe_runner(*, bound=True, coins=(BTC, XRP), batch_snapshot=SNAPSHOT):
    """runner_fixture (prepared and armed) with a universe profile. `_assess` is pinned to the fixed profile's
    assessment, because the universe evaluator is PR 5 (PR 4b refuses forward-universe-v1 evidence); every universe
    check runs after it. With `bound`, the prepared session carries BATCH and its wrapper the universe profile's
    digest; registered_batch returns a batch over `coins` for `batch_snapshot`. controller.observe returns
    env.universe as RiskResult.universe (PR 4a). env.fixed is the fixed profile."""
    with runner_fixture() as env:
        assessment, binding = R._assess(env.profile, env.evidence, env.driver, env.review, env.now)
        env.fixed, env.profile = env.profile, universe_profile(env.profile)
        env.universe = universe_snapshot(env.now)
        launch = env.launch
        if bound:
            env.prepared = replace(env.prepared, universe_batch_digest=BATCH)
            launch = LaunchSession(prepared=env.prepared, profile_digest=profile_digest(env.profile), binding=binding)
        batch = SimpleNamespace(batch_digest=BATCH, snapshot_sha256=batch_snapshot,
                                coins=tuple(SimpleNamespace(market=coin, passed=True) for coin in coins))
        observe = env.controller.observe
        with patch.object(R, "_assess", lambda *args: (assessment, binding)), \
                patch.object(R, "registered_batch", lambda digest: batch if digest == BATCH else None), \
                patch.object(env.controller, "observe",
                             lambda *, now: replace(observe(now=now), universe=env.universe)):
            env.runner = Runner(profile=env.profile, quote_provider=lambda now: env.quote,
                account_provider=env.controller.account_provider, evidence=env.evidence, driver=env.driver,
                implementation_verifier=env.review, mode="rehearsal", controller=env.controller,
                launch_session=launch, isolated_state_root=env.home)
            yield env


def reserve_reached(env):
    """Stand-in for Controller.reserve: a buy that gets here passed every runner check. The hand-made bound session
    is not in the session registry, so the real reserve and dispatch are not exercised for universe buys."""
    def reserve(order, rules, *, session_id, now):
        raise RunnerError("FIXTURE_RESERVE_REACHED")
    return patch.object(env.controller, "reserve", reserve)


def test_a_universe_buy_needs_the_coin_in_a_frozenset_allow_list():
    with universe_runner() as env, reserve_reached(env):
        for allow in (None, frozenset(), frozenset({XRP}), {BTC}):
            result = env.runner.tick(now=env.now, entry_allow=allow)
            assert (result.status, result.reasons) == ("blocked", ("RUNNER_UNIVERSE_ENTRY_NOT_ALLOWED",)), (allow, result)
        result = env.runner.tick(now=env.now, entry_allow=frozenset({BTC}))
        assert (result.status, result.reasons) == ("blocked", ("FIXTURE_RESERVE_REACHED",)), result
        assert not env.runner.stopped and creates(env) == []


def test_a_universe_buy_needs_the_snapshot_in_force_under_the_profile_rule():
    with universe_runner() as env, reserve_reached(env):
        for snapshot in (None, universe_snapshot(env.now, valid_until=env.now),
                         universe_snapshot(env.now, valid_from=env.now + timedelta(seconds=1)),
                         universe_snapshot(env.now, rule="f" * 64)):
            env.universe = snapshot
            result = env.runner.tick(now=env.now, entry_allow=frozenset({BTC}))
            assert (result.status, result.reasons) == ("blocked", ("RUNNER_UNIVERSE_SNAPSHOT_MISMATCH",)), result
        assert not env.runner.stopped and creates(env) == []


def test_a_universe_buy_needs_the_bound_batch_of_this_snapshot_and_coin():
    for coins, batch_snapshot, code in (((BTC, XRP), "6" * 64, "RUNNER_UNIVERSE_SNAPSHOT_MISMATCH"),
                                        ((XRP,), SNAPSHOT, "RUNNER_UNIVERSE_COIN_NOT_IN_BATCH")):
        with universe_runner(coins=coins, batch_snapshot=batch_snapshot) as env, reserve_reached(env):
            result = env.runner.tick(now=env.now, entry_allow=frozenset({BTC}))
            assert (result.status, result.reasons) == ("blocked", (code,)), result
            assert not env.runner.stopped
    with universe_runner() as env, reserve_reached(env), patch.object(R, "registered_batch", lambda digest: None):
        result = env.runner.tick(now=env.now, entry_allow=frozenset({BTC}))
        assert (result.status, result.reasons) == ("blocked", ("RUNNER_UNIVERSE_SNAPSHOT_MISMATCH",)), result


def test_universe_sells_and_explicit_exits_never_look_at_the_allow_list_or_snapshot():
    for explicit in (False, True):
        with universe_runner(bound=False) as env:
            env.universe = None
            env.observation = holding(env)
            exit_signal = replace(env.signal, action="exit")
            if explicit:
                env.runner.submit_exit(exit_signal, now=env.now)
            else:
                env.signal = exit_signal
                result = env.runner.tick(now=env.now)
                assert result.status == "submitted", result
            assert len(creates(env)) == 1 and not env.runner.stopped


def test_a_fixed_profile_ignores_entry_allow():
    with runner_fixture() as env:
        result = env.runner.tick(now=env.now, entry_allow=frozenset())
        assert result.status == "submitted" and len(creates(env)) == 1, result


def test_a_second_sell_of_the_same_coin_is_blocked_while_one_is_active():
    with runner_fixture() as env:
        env.observation = holding(env)
        env.signal = replace(env.signal, action="exit")
        first = env.runner.tick(now=env.now)
        assert first.status == "submitted" and first.order_status == "ACKNOWLEDGED", first
        env.signal = replace(env.signal, signal_id="fixed-second-exit")
        second = env.runner.tick(now=env.now)
        assert (second.status, second.reasons) == ("blocked", ("RUNNER_OUTSTANDING_ORDERS",)), second
        assert not env.runner.stopped and len(creates(env)) == 1



def test_dust_and_flat_in_follow_spec_section_7():
    from execution_accounts.model import Position
    from execution_control.controller import OrderState
    at, five = datetime(2026, 11, 11, tzinfo=timezone.utc), D("5000")

    def held(symbol, units, price):
        return Position(market="spot", symbol=symbol, base_currency=symbol[4:], quote_currency="KRW",
                        units=D(units), price=D(price), asof=at)

    def state(status, symbol, updated):
        return OrderState(client_id="c", status=status, order_digest="d" * 64, side="sell", symbol=symbol,
                          updated_at=updated)
    assert R.dust(held(BTC, "0.00004", "100000000"), five) and not R.dust(held(BTC, "0.00005", "100000000"), five)
    assert R.dust(held(XRP, "1000", "0"), five)                 # unlisted: marked 0, always dust
    positions = (held(BTC, "0.00004", "100000000"), held(XRP, "10", "1000"))
    earlier, later = at - timedelta(seconds=1), at + timedelta(seconds=1)
    assert R.flat_in(BTC, positions, (), asof=at, minimum=five)
    assert not R.flat_in(XRP, positions, (), asof=at, minimum=five)
    assert R.flat_in(BTC, positions, (state("FILLED", BTC, earlier), state("ACKNOWLEDGED", XRP, earlier)),
                     asof=at, minimum=five)
    for states in ((state("ACKNOWLEDGED", BTC, earlier),), (state("DISPATCHING", BTC, earlier),),
                   (state("PARTIAL", None, earlier),), (state("FILLED", BTC, at),), (state("CANCELED", BTC, later),)):
        assert not R.flat_in(BTC, positions, states, asof=at, minimum=five), states
    assert R.active(state("CANCEL_REQUESTED", BTC, at)) and not R.active(state("FILLED", BTC, at))


def test_a_renewal_to_another_coin_needs_a_flat_account():
    from tests.accounts_provider import bundle
    with universe_runner(bound=False) as env:
        env.runner.launch_session = None
        xrp = replace(env.profile, symbol=XRP, instrument_rules=replace(env.profile.instrument_rules, symbol=XRP))
        held = replace(bundle(env.now, units=D("0.001"), price=D("100000000")).accounts[0],
                       account_scope=env.profile.account_scope)
        flat = replace(bundle(env.now, units=D("0.00001"), price=D("100000000")).accounts[0],
                       account_scope=env.profile.account_scope)    # 1,000 KRW: dust
        with patch.object(R, "validate_renewal", lambda renewal, *, previous_profile, now: renewal.profile):
            same = env.profile
            assert env.runner.refresh_instrument_rules(SimpleNamespace(profile=same), now=env.now) is same
            for account in (None, held):
                refused(lambda: env.runner.refresh_instrument_rules(SimpleNamespace(profile=xrp), now=env.now,
                                                                    account=account), "RUNNER_UNIVERSE_NOT_FLAT")
                assert env.runner.profile.symbol == BTC
            assert env.runner.refresh_instrument_rules(SimpleNamespace(profile=xrp), now=env.now, account=flat) is xrp
            assert env.runner.profile is xrp


def test_the_session_rules_binding_holds_across_a_switch():
    """Spec section 19: Runner._session checks rules_binding_matches(prepared.rules_digest, current rules) on every
    tick, so a session prepared under one coin's rules must still match after renewals to another coin and back."""
    from execution_control.model import rules_digest
    from execution_launch import instrument_refresh as IR
    from tests.launch_instrument_refresh import registries, universe_authority, universe_observed
    from tests.launch_instrument_refresh import universe_profile as refresh_profile
    with registries():
        auth = universe_authority()
        p = refresh_profile(auth)
        bound = rules_digest(p.instrument_rules)
        o = universe_observed("KRW-ETH", auth=auth, tick="5")
        r = IR.renew_profile(p, o, now=o.checked_at, allow_symbol_change=True)
        assert IR.rules_binding_matches(bound, r.profile.instrument_rules, account_scope=p.account_scope,
                                        now=o.checked_at)
        back = universe_observed(BTC, o.checked_at + timedelta(seconds=10), auth=auth)
        again = IR.renew_profile(r.profile, back, now=back.checked_at, allow_symbol_change=True)
        assert IR.rules_binding_matches(bound, again.profile.instrument_rules, account_scope=p.account_scope,
                                        now=back.checked_at)



def test_universe_preparation_needs_a_batch_holding_the_template_coin():
    with universe_runner(bound=False) as env:
        plan, inputs, seed = selected(env.now)
        seen = []

        def prepare(**kwargs):
            seen.append(kwargs["universe_batch"])
            return env.prepared
        batch = SimpleNamespace(coins=(SimpleNamespace(market="KRW-" + plan.leg.symbol),))
        other = SimpleNamespace(coins=(SimpleNamespace(market=XRP),))

        def call(profile, universe_batch):
            return R.prepare_launch_session(profile=profile, evidence=env.evidence, driver=env.driver,
                implementation_verifier=env.review, journal=env.journal, selected_plan=plan, inputs=inputs,
                positions=env.observation.positions, now=env.now, selection_seed_hex=seed, clock=lambda: env.now,
                positions_asof=env.observation.asof, universe_batch=universe_batch)
        with patch.object(R, "prepare_session", prepare):
            for profile, value in ((env.profile, None), (env.profile, other), (env.fixed, batch)):
                refused(lambda: call(profile, value), "RUNNER_SELECTED_PLAN_SCOPE_MISMATCH")
            assert seen == []
            assert call(env.profile, batch).prepared is env.prepared
            assert call(env.fixed, None).prepared is env.prepared
        assert seen == [batch, None]


def test_run_forwards_the_slot_allow_list_without_turning_a_block_into_a_stop():
    with universe_runner() as env, reserve_reached(env):
        blocked = env.runner.run((env.now, env.now), max_steps=2, entry_allow=frozenset({XRP}))
        assert len(blocked) == 2
        assert all(row.reasons == ("RUNNER_UNIVERSE_ENTRY_NOT_ALLOWED",) for row in blocked)
        allowed = env.runner.run((env.now,), max_steps=1, entry_allow=frozenset({BTC}))
        assert allowed[0].reasons == ("FIXTURE_RESERVE_REACHED",)
        assert not env.runner.stopped and not creates(env)


def test_malformed_or_naive_universe_snapshot_blocks_without_latching_stop():
    with universe_runner() as env, reserve_reached(env):
        for snapshot in (object(), replace(env.universe, valid_from=env.now.replace(tzinfo=None)),
                         replace(env.universe, valid_until="not-an-instant")):
            env.universe = snapshot
            result = env.runner.tick(now=env.now, entry_allow=frozenset({BTC}))
            assert result.reasons == ("RUNNER_UNIVERSE_SNAPSHOT_MISMATCH",), result
            assert not env.runner.stopped
        assert not creates(env)


def test_explicit_second_exit_is_refused_without_stopping_or_resending():
    with universe_runner(bound=False) as env:
        env.observation = holding(env)
        first = replace(env.signal, action="exit")
        order = env.runner.submit_exit(first, now=env.now)
        assert order.status == "ACKNOWLEDGED"
        assert env.runner.submit_exit(first, now=env.now) == order
        refused(lambda: env.runner.submit_exit(replace(first, signal_id="distinct-exit"), now=env.now),
                "RUNNER_OUTSTANDING_ORDERS")
        assert not env.runner.stopped and len(creates(env)) == 1


def test_unsettled_or_recently_changed_orders_block_a_cross_coin_renewal():
    from execution_control.controller import OrderState
    from tests.accounts_provider import bundle
    with universe_runner(bound=False) as env:
        env.runner.launch_session = None
        xrp = replace(env.profile, symbol=XRP, instrument_rules=replace(env.profile.instrument_rules, symbol=XRP))
        flat = replace(bundle(env.now, units=D("0.00001"), price=D("100000000")).accounts[0],
                       account_scope=env.profile.account_scope)
        renewal = SimpleNamespace(profile=xrp)
        earlier, later = env.now - timedelta(seconds=1), env.now + timedelta(seconds=1)
        with patch.object(R, "validate_renewal", lambda value, *, previous_profile, now: value.profile):
            for status, symbol, updated in (("UNKNOWN", BTC, earlier), ("DISPATCHING", BTC, earlier),
                    ("PARTIAL", BTC, earlier), ("CANCEL_REQUESTED", BTC, earlier),
                    ("RESERVED", None, earlier), ("FILLED", BTC, env.now), ("CANCELED", BTC, later)):
                state = OrderState(client_id="synthetic-ioc", status=status, side="sell", symbol=symbol,
                                   order_digest="d" * 64, updated_at=updated)
                with patch.object(env.controller, "states", lambda: (state,)):
                    refused(lambda: env.runner.refresh_instrument_rules(renewal, now=env.now, account=flat),
                            "RUNNER_UNIVERSE_NOT_FLAT")
                assert env.runner.profile.symbol == BTC
            # A confirmed terminal order older than the account snapshot is no
            # longer an outstanding fill uncertainty; no order is sent here.
            settled = OrderState(client_id="synthetic-ioc", status="FILLED", side="sell", symbol=BTC,
                                 order_digest="d" * 64, updated_at=earlier)
            with patch.object(env.controller, "states", lambda: (settled,)):
                assert env.runner.refresh_instrument_rules(renewal, now=env.now, account=flat) is xrp
            assert not creates(env)


def test_cross_coin_renewal_needs_this_accounts_fresh_snapshot():
    from tests.accounts_provider import bundle
    with universe_runner(bound=False) as env:
        env.runner.launch_session = None
        xrp = replace(env.profile, symbol=XRP, instrument_rules=replace(env.profile.instrument_rules, symbol=XRP))
        flat = replace(bundle(env.now).accounts[0], account_scope=env.profile.account_scope)
        with patch.object(R, "validate_renewal", lambda value, *, previous_profile, now: value.profile):
            for invalid in (replace(flat, account_scope="some-other-account"), replace(flat, venue="kis"),
                            replace(flat, execution_quote="USD"),
                            replace(flat, observed_at=env.now + timedelta(microseconds=1)),
                            replace(flat, observed_at=env.now - timedelta(seconds=30, microseconds=1))):
                refused(lambda: env.runner.refresh_instrument_rules(SimpleNamespace(profile=xrp),
                            now=env.now, account=invalid), "RUNNER_UNIVERSE_NOT_FLAT")
                assert env.runner.profile.symbol == BTC
            boundary = replace(flat, observed_at=env.now - timedelta(seconds=30))
            assert env.runner.refresh_instrument_rules(SimpleNamespace(profile=xrp),
                                                       now=env.now, account=boundary) is xrp


def test_dust_uses_exact_boundary_and_rejects_invalid_marked_holdings():
    from execution_accounts.model import Position
    p = Position(market="spot", symbol=BTC, base_currency="BTC", quote_currency="KRW",
                 units=D("0.000049999999999999999999999999999"), price=D("100000000"),
                 asof=datetime(2026, 11, 11, tzinfo=timezone.utc))
    assert R.dust(p, D("5000"))
    assert not R.dust(replace(p, units=D("0.000050000000000000000000000000001")), D("5000"))
    for changed in (replace(p, units=D("-1")), replace(p, price=D("NaN")), replace(p, price=D("-1"))):
        refused(lambda: R.dust(changed, D("5000")), "RUNNER_HOLDING_INVALID")
