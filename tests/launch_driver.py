"""Invented anchors/authentication only; no real history, credentials or orders."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from execution_control.capability import digest
from execution_control.controller import AccountObservation
from execution_control.risk import RiskObservation
from execution_launch.driver import (AccountAnchor, DeploymentWindow, FixedDriverError,
    HistoryFrame, HistoryReceipt, describe_fixed_driver, fixed_history_dependencies,
    history_frame_digest, make_fixed_driver)
from execution_launch.profile import profile_contract_digest
from execution_launch.program import program_digest, target_fraction
from execution_launch.runner import DecisionInput, Quote, StrategyDriver, program_digest as runner_digest
from execution_launch.strategy import PaperDecision, _simulate, history_digest
from tests.launch_capture import fixture as capture_fixture
from tests.launch_profile import fixture_profile

D = Decimal


def reject(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected refusal")


def invented_authentication(frame, identity, now):
    """Fixture stub, deliberately NOT usable as source authentication in production."""
    return HistoryReceipt(frame_digest=history_frame_digest(frame), driver_identity_digest=digest(identity),
        source_audit_sha256="f"*64, verified_at=now, expires_at=now+timedelta(seconds=1))


def observation(profile, row, cash, units):
    key = (profile.venue, profile.account_scope)
    inventory = units*row.mark
    equity = cash+inventory
    now = row.received_at
    account = AccountObservation(positions=M.Positions(equity_krw=float(equity), holdings={}, exposure={}),
        account_scopes={profile.venue:profile.account_scope}, settled_cash_krw={key:cash},
        holdings={(*key, profile.market, profile.symbol):units},
        held_exposure_krw={key:equity}, inventory_exposure_krw={key:inventory},
        quote_currency_by_account={key:"KRW"}, quote_rates_krw={(*key,"KRW"):D(1)},
        risk=RiskObservation(equity=equity, prior_high_watermark=equity, day_start_equity=equity,
            current_day_realized_net_profit=D(0), prior_day_realized_net_profit=D(10),
            observed_daily_loss=D(0), approved_effective_floor=None, is_first_trading_day=False, asof=now),
        asof=now, server_time=now, no_credit=True)
    return DecisionInput(now=now, profile=profile, account=account,
        quote=Quote(venue=profile.venue, market=profile.market, symbol=profile.symbol,
            bid=row.bid, ask=row.ask, asof=row.observed_at, source_sha256=row.source_sha256))


def next_frame(env, index, *, cash=D(10000), units=D(0)):
    prefix = env.bars[:index+1]
    prior = None if index == 0 else PaperDecision(bar_index=index-1,
        decided_at=prefix[-2].received_at, history_sha256=history_digest(prefix[:-1]),
        target_fraction=target_fraction(env.program, tuple(row.mark for row in prefix[:-1])))
    env.frame = HistoryFrame(deployment_window_digest=digest(env.window),
        source_kind="prospective_paper_capture", bars=prefix, prior_decision=prior,
        anchor=AccountAnchor(cash_quote=cash, units=units, account_asof=prefix[-1].received_at))
    env.observation = observation(env.profile, prefix[-1], cash, units)


def fixture(index=4, *, cash=D(10000), units=D(0), kind="moving_average_trend"):
    program, protocol, _, bars, rules = capture_fixture()
    if kind == "cash":
        program = replace(program, kind="cash", fast_window=0, slow_window=0, exposure_fraction=D(0))
    artifact = (Path(__file__).resolve().parents[1]/"execution_launch/program.py").read_bytes()
    code = program_digest(program, artifact)
    shift = timedelta(days=2)
    bars = tuple(replace(row, observed_at=row.observed_at+shift, received_at=row.received_at+shift)
                 for row in bars)
    rules = replace(rules, asof=bars[0].observed_at)
    base = fixture_profile(bars[0].observed_at)
    profile = replace(base, strategy_id=program.strategy_id, strategy_code_sha256=code,
        instrument_rules=rules, policy=replace(base.policy, initial_equity=protocol.initial_cash_quote))
    protocol = replace(protocol, strategy_code_sha256=code,
        profile_contract_digest=profile_contract_digest(profile), slippage_bps=D(20))
    window = DeploymentWindow(deployment_id="invented-deployment", start=bars[0].observed_at,
                              end=bars[-1].observed_at)
    env = SimpleNamespace(program=program, protocol=protocol, profile=profile, window=window,
                          bars=bars, artifact=artifact)
    next_frame(env, index, cash=cash, units=units)
    env.provider = lambda observation:env.frame
    env.verifier = invented_authentication
    env.driver = construct(env)
    return env


def construct(env, **changes):
    options = dict(window=env.window, history_provider=env.provider,
                   history_verifier=env.verifier, program_artifact=env.artifact)
    return make_fixed_driver(env.program, env.protocol, env.profile, **(options | changes))


def decide(env, driver=None):
    driver = driver or env.driver
    return driver.callback(env.observation, driver.parameters_json)


def test_registered_factory_identity_preserves_program_digest_and_rejects_clones():
    env = fixture()
    identity = describe_fixed_driver(env.driver)
    assert identity.program_digest == runner_digest(env.driver) == env.profile.strategy_code_sha256
    assert identity.deployment_window_digest == digest(env.window)
    assert identity.factory_id == "tradegen-fixed-cash-trend-v1"
    provider, verifier = fixed_history_dependencies(env.driver)
    assert provider is env.provider and verifier is env.verifier
    clone = StrategyDriver(callback=env.driver.callback, artifact=env.driver.artifact,
                           parameters_json=env.driver.parameters_json)
    reject(lambda:describe_fixed_driver(clone), "FIXED_DRIVER_NOT_ISSUED")
    reject(lambda:construct(env, program_artifact=b"claimed equivalent code"),
           "FIXED_DRIVER_ARTIFACT_NOT_INSTALLED_PROGRAM")
    reject(lambda:construct(env, history_verifier=None), "FIXED_DRIVER_AUTHENTICATED_HISTORY_REQUIRED")


def test_registered_callback_parameters_contract_and_code_are_rechecked():
    env = fixture()
    reject(lambda:env.driver.callback(env.observation, "{}"), "FIXED_DRIVER_PARAMETERS_CHANGED")
    object.__setattr__(env.driver, "callback", lambda *args:None)
    reject(lambda:describe_fixed_driver(env.driver), "FIXED_DRIVER_CALLBACK_CHANGED")
    env = fixture()
    with patch("execution_launch.driver._sources", return_value=("0"*64, env.artifact)):
        reject(lambda:describe_fixed_driver(env.driver), "FIXED_DRIVER_DEPLOYMENT_CHANGED")
    object.__setattr__(env.program, "fast_window", 1)
    reject(lambda:describe_fixed_driver(env.driver), "FIXED_DRIVER_REGISTERED_INPUT_CHANGED")


def test_missing_boolean_wrong_digest_expired_and_raising_source_authentication_refuse():
    env = fixture()
    for result in (True, None, replace(invented_authentication(env.frame, describe_fixed_driver(env.driver),
                                                            env.observation.now), frame_digest="0"*64)):
        driver = construct(env, history_verifier=lambda *args, result=result:result)
        reject(lambda:decide(env, driver), "FIXED_DRIVER_HISTORY_UNVERIFIED")
    driver = construct(env, history_verifier=lambda f,i,n:replace(invented_authentication(f,i,n),expires_at=n))
    reject(lambda:decide(env, driver), "FIXED_DRIVER_HISTORY_UNVERIFIED")
    def failure(*args):
        raise RuntimeError("private provider content must not escape")
    reject(lambda:decide(env, construct(env, history_provider=failure)), "FIXED_DRIVER_HISTORY_PROVIDER_FAILED")
    reject(lambda:decide(env, construct(env, history_verifier=failure)), "FIXED_DRIVER_HISTORY_AUTH_FAILED")


def test_cash_warmup_and_first_slot_never_create_an_entry():
    for index, kind in ((0,"moving_average_trend"),(2,"moving_average_trend"),(4,"cash")):
        env = fixture(index, kind=kind)
        assert decide(env).action == "hold"
    env = fixture(0, units=D("1"))
    reject(lambda:decide(env), "FIXED_DRIVER_INITIAL_STATE_INVALID")


def test_prior_decision_delay_prefix_target_and_source_label_are_mandatory():
    changes = (
        lambda f:replace(f, source_kind="retrospective_replay"),
        lambda f:replace(f, source_kind="synthetic"),
        lambda f:replace(f, prior_decision=replace(f.prior_decision, target_fraction=D(0))),
        lambda f:replace(f, prior_decision=replace(f.prior_decision, decided_at=f.bars[-1].observed_at)),
        lambda f:replace(f, prior_decision=replace(f.prior_decision, history_sha256="0"*64)),
        lambda f:replace(f, bars=(f.bars[0],)+f.bars[2:]),
    )
    for change in changes:
        env = fixture()
        env.frame = change(env.frame)
        reject(lambda:decide(env))


def test_current_quote_does_not_enter_delayed_target_and_future_slot_refuses():
    env = fixture()
    row = replace(env.frame.bars[-1], bid=D(9), ask=D(11), mark=D(10))
    env.frame = replace(env.frame, bars=env.frame.bars[:-1]+(row,))
    env.observation = observation(env.profile, row, D(10000), D(0))
    assert decide(env).action == "entry"  # Current crash cannot rewrite the prior trend decision.
    env = fixture()
    env.observation = replace(env.observation, now=env.frame.bars[-1].observed_at-timedelta(seconds=1))
    reject(lambda:decide(env))
    env = fixture()
    env.observation = replace(env.observation, now=env.observation.now+timedelta(seconds=10))
    reject(lambda:decide(env), "FIXED_DRIVER_EXECUTION_SLOT_EXPIRED")


def test_order_sizes_match_paper_evaluator_with_fees_slippage_lots_and_terminal_exit():
    env = fixture(0)
    cash, units, fees, turnover = D(10000), D(0), D(0), D(0)
    decisions = []
    for index, row in enumerate(env.bars):
        next_frame(env, index, cash=cash, units=units)
        signal = decide(env)
        if index:
            decisions.append(env.frame.prior_decision)
        if signal.action != "hold":
            notional = signal.quantity*signal.limit_price
            charge = notional*env.protocol.fee_fraction
            cash += notional-charge if signal.action == "exit" else -notional-charge
            units += signal.quantity if signal.action == "entry" else -signal.quantity
            fees += charge; turnover += notional
            assert cash >= 0 and units >= 0
    metrics, _ = _simulate(env.protocol, env.bars, tuple(decisions), env.profile.instrument_rules)
    assert units == 0
    assert metrics.total_return == float(Fraction(cash)/10000-1)
    assert metrics.total_fees_quote == float(fees)
    assert metrics.turnover_quote == float(turnover)


def test_exact_sizing_is_independent_of_ambient_decimal_precision():
    env = fixture()
    expected = decide(env)
    with localcontext() as numeric:
        numeric.prec = 2
        assert decide(env) == expected


def test_restart_reuses_same_signal_and_changed_post_fill_account_is_refused():
    env = fixture()
    signal = decide(env)
    assert signal.action == "entry" and decide(env) == signal
    restarted = construct(env)
    assert decide(env, restarted) == signal
    row = env.frame.bars[-1]
    env.observation = observation(env.profile, row, D(1000), D(50))
    reject(lambda:decide(env, restarted), "FIXED_DRIVER_ACCOUNT_ANCHOR_MISMATCH")


def test_same_slot_rewrite_and_later_prefix_rewrite_refuse_even_with_fixture_verifier():
    env = fixture()
    original = decide(env)
    next_frame(env, 4, cash=D(9999))
    reject(lambda:decide(env), "FIXED_DRIVER_SLOT_REWRITTEN")
    env = fixture()
    decide(env)
    next_frame(env, 5)
    first = replace(env.frame.bars[0], source_sha256="1"*64)
    bars = (first,)+env.frame.bars[1:]
    env.frame = replace(env.frame, bars=bars,
        prior_decision=replace(env.frame.prior_decision, history_sha256=history_digest(bars[:-1])))
    reject(lambda:decide(env), "FIXED_DRIVER_PREFIX_REWRITTEN")
    assert original.signal_id.startswith("fixed:")


def test_inventory_reservations_fx_and_quote_anchor_mismatch_refuse():
    for kind in ("other", "reserved", "open_order", "fx", "quote"):
        env = fixture()
        account = env.observation.account
        key = (env.profile.venue,env.profile.account_scope)
        if kind == "other":
            account = replace(account, holdings=dict(account.holdings) | {(*key,"spot","KRW-ETH"):D(1)})
        elif kind == "reserved":
            account = replace(account, held_exposure_krw={key:D(11000)})
        elif kind == "open_order":
            account = replace(account, cancellable_quantities={"invented-order":D(1)})
        elif kind == "fx":
            account = replace(account, quote_rates_krw={(*key,"KRW"):D(2)})
        else:
            env.observation = replace(env.observation, quote=replace(env.observation.quote, source_sha256="1"*64))
        env.observation = replace(env.observation, account=account)
        reject(lambda:decide(env))


def test_terminal_window_is_deployment_window_and_dust_is_not_reported_as_success():
    env = fixture(60, units=D(1))
    assert env.window.end != env.protocol.capture_end
    signal = decide(env)
    assert signal.action == "exit" and signal.quantity == 1
    env = fixture(60, units=D("0.01"))
    # Current bid is 100; 20bps adverse slippage rounds down to 99 => 0.99 below minimum 1.
    reject(lambda:decide(env), "FIXED_DRIVER_TERMINAL_DUST_UNLIQUIDATED")
