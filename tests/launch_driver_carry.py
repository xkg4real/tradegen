"""Issued carry callbacks on invented source receipts; not live source authentication.

The final Coordinator integration separately exercises authenticated temporary
review documents and actual LiveHistory. These driver units use the existing
explicit invented verifier to test causal sizing and factory identity only.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from execution_launch import driver as D
from execution_launch import managed_behavior as B
from execution_launch.runner import StrategyDriver
from execution_launch.strategy import history_digest
from tests import launch_driver as L

Dec = Decimal


def fixture(index=4, *, cash=Dec('10000'), units=Dec(0), rising=True):
    env = L.fixture(index=index, cash=cash, units=units)
    env.protocol = replace(env.protocol, schema_version=2, evaluator_revision=B.CARRY_EVALUATOR_REVISION,
        behavior_revision=B.BEHAVIOR_REVISION, terminal_accounting=B.TERMINAL_ACCOUNTING,
        management_behavior_sha256=B.behavior_digest())
    env.bars = tuple(replace(row, bid=Dec(100+i if rising else 200-i),
                            ask=Dec(102+i if rising else 202-i), mark=Dec(101+i if rising else 201-i))
                     for i, row in enumerate(env.bars))
    frame_at(env, index, cash=cash, units=units)
    env.driver = D.make_fixed_carry_driver(env.program, env.protocol, env.profile, window=env.window,
        history_provider=env.provider, history_verifier=env.verifier, program_artifact=env.artifact)
    return env


def frame_at(env, index, *, cash=Dec('10000'), units=Dec(0)):
    L.next_frame(env, index, cash=cash, units=units)
    if index:
        prefix = env.frame.bars[:-1]
        prior = B.derive_fixed_decision_v2(env.program, tuple(row.mark for row in prefix),
            bar_index=index-1, decided_at=prefix[-1].received_at, history_sha256=history_digest(prefix))
        env.frame = replace(env.frame, prior_decision=prior)


def test_carry_factory_identity_is_separate_and_rejects_legacy_protocol_and_clones():
    env = fixture()
    identity = D.describe_fixed_carry_driver(env.driver)
    assert identity.factory_id == B.CARRY_FACTORY_ID
    assert D.describe_fixed_driver(env.driver) == identity
    assert D.fixed_history_dependencies(env.driver) == (env.provider, env.verifier)
    L.reject(lambda: D.make_fixed_driver(env.program, env.protocol, env.profile, window=env.window,
        history_provider=env.provider, history_verifier=env.verifier, program_artifact=env.artifact),
        'FIXED_DRIVER_FACTORY_PROTOCOL_MISMATCH')
    legacy = L.fixture()
    L.reject(lambda: D.describe_fixed_carry_driver(legacy.driver), 'FIXED_DRIVER_FACTORY_PROTOCOL_MISMATCH')
    L.reject(lambda: D.make_fixed_carry_driver(legacy.program, legacy.protocol, legacy.profile,
        window=legacy.window, history_provider=legacy.provider, history_verifier=legacy.verifier,
        program_artifact=legacy.artifact), 'FIXED_DRIVER_FACTORY_PROTOCOL_MISMATCH')
    clone = StrategyDriver(callback=env.driver.callback, artifact=env.driver.artifact,
                           parameters_json=env.driver.parameters_json)
    L.reject(lambda: D.describe_fixed_driver(clone), 'FIXED_DRIVER_NOT_ISSUED')


def test_carry_long_target_never_sells_an_overweight_holding_before_deadline():
    env = fixture(cash=Dec(1), units=Dec(100))
    signal = L.decide(env)
    assert signal.action == 'hold' and signal.decision_state == 'long_target'
    assert not signal.execution_block_reasons
    # The same original numerical target sizes a reducing rebalance in v1.
    legacy_signal = D._sized_signal(D.describe_fixed_driver(env.driver), env.frame,
                                   env.program.exposure_fraction, env.profile.instrument_rules, env.protocol)
    assert legacy_signal.action == 'exit'


def test_final_slot_holds_the_actual_inventory_instead_of_forcing_liquidation():
    env = fixture(index=60, cash=Dec(1), units=Dec(100))
    assert env.frame.bars[-1].observed_at == env.window.end
    signal = L.decide(env)
    assert signal.action == 'hold' and signal.decision_state == 'long_target'
    assert signal.execution_block_reasons == ('MANAGED_DEADLINE_REACHED',)
    assert env.frame.anchor.units == 100
    # Explicit legacy control: this old factory retains terminal target zero.
    legacy = L.fixture(index=60, cash=Dec(1), units=Dec(100))
    assert L.decide(legacy).action == 'exit'


def test_final_positive_target_cannot_make_a_new_buy_and_valid_sell_remains_visible():
    entry = fixture(index=60)
    signal = L.decide(entry)
    assert signal.action == 'hold' and signal.decision_state == 'long_target'
    assert signal.execution_block_reasons == ('MANAGED_DEADLINE_REACHED',)
    exit_env = fixture(index=60, cash=Dec(1), units=Dec(100), rising=False)
    sell = L.decide(exit_env)
    assert sell.action == 'hold' and sell.decision_state == 'cash_target' and sell.decision_cause == 'trend_not_above'
    assert sell.execution_block_reasons == ('MANAGED_DEADLINE_REACHED', 'MANAGED_AUTHORITY_UNAVAILABLE')


def test_before_deadline_valid_cash_can_propose_exit_but_warmup_cannot():
    sell_env = fixture(index=59, cash=Dec(1), units=Dec(100), rising=False)
    signal = L.decide(sell_env)
    assert signal.action == 'exit' and signal.decision_state == 'cash_target' and not signal.execution_block_reasons
    warmup = fixture(index=1, cash=Dec(1), units=Dec(100))
    signal = L.decide(warmup)
    assert signal.action == 'hold' and signal.decision_state == 'warmup'
    assert signal.decision_cause == 'insufficient_history'


def test_carry_terminal_dust_is_retained_without_a_fake_fill_or_legacy_dust_error():
    env = fixture(index=60, cash=Dec('9999'), units=Dec('0.01'))
    env.bars = tuple(replace(row, bid=Dec(10+i), ask=Dec(12+i), mark=Dec(11+i))
                     for i, row in enumerate(env.bars))
    frame_at(env, 60, cash=Dec('9999'), units=Dec('0.01'))
    assert env.frame.anchor.units * env.frame.bars[-1].bid < env.profile.instrument_rules.min_notional_krw
    signal = L.decide(env)
    assert signal.action == 'hold' and env.frame.anchor.units == Dec('0.01')
    assert signal.execution_block_reasons == ('MANAGED_DEADLINE_REACHED',)


def test_full_typed_decision_is_rederived_and_unavailable_cannot_hide_valid_evidence():
    env = fixture()
    prior = env.frame.prior_decision
    prefix = env.frame.bars[:-1]
    fabricated = B.derive_fixed_decision_v2(env.program, tuple(reversed(tuple(row.mark for row in prefix))),
        bar_index=prior.bar_index, decided_at=prior.decided_at, history_sha256=prior.history_sha256)
    env.frame = replace(env.frame, prior_decision=fabricated)
    L.reject(lambda: L.decide(env), 'FIXED_DRIVER_TARGET_MISMATCH')
    env.frame = replace(env.frame, prior_decision=B.derive_fixed_decision_v2(env.program,
        tuple(row.mark for row in prefix), bar_index=prior.bar_index, decided_at=prior.decided_at,
        history_sha256=prior.history_sha256, input_status='unavailable'))
    L.reject(lambda: L.decide(env), 'FIXED_DRIVER_TARGET_MISMATCH')
    env.frame = replace(env.frame, prior_decision=B.benchmark_fixed_decision_v2(bar_index=prior.bar_index,
        decided_at=prior.decided_at, history_sha256=prior.history_sha256))
    L.reject(lambda: L.decide(env), 'FIXED_DRIVER_TARGET_MISMATCH')


def test_carry_still_rejects_initial_inventory_and_copied_history_authentication():
    env = fixture(index=0, cash=Dec('9999'), units=Dec('0.01'))
    L.reject(lambda: L.decide(env), 'FIXED_DRIVER_INITIAL_STATE_INVALID')
    env = fixture()
    env.verifier = lambda *args: True
    driver = D.make_fixed_carry_driver(env.program, env.protocol, env.profile, window=env.window,
        history_provider=env.provider, history_verifier=env.verifier, program_artifact=env.artifact)
    L.reject(lambda: L.decide(env, driver), 'FIXED_DRIVER_HISTORY_UNVERIFIED')


def test_each_carry_source_dependency_change_invalidates_an_issued_driver_without_writing():
    env = fixture()
    root = Path(D.__file__).resolve().parent.parent
    original_open = Path.open
    extras = tuple(name for name in D._CARRY_SOURCE_FILES if name not in D._SOURCE_FILES)
    assert len(extras) == 3
    for name in extras:
        watched = root / name
        body = watched.read_bytes()
        def changed(path, *args, **kwargs):
            if path == watched and args == ('rb',):
                return BytesIO(body + b'\n# synthetic changed source\n')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', changed):
            L.reject(lambda: D.describe_fixed_carry_driver(env.driver), 'FIXED_DRIVER_DEPLOYMENT_CHANGED')
    assert D.describe_fixed_carry_driver(env.driver).factory_id == B.CARRY_FACTORY_ID


def test_shared_behavior_dependency_change_invalidates_both_factories_without_writing():
    legacy, carry = L.fixture(), fixture()
    assert len(D._SOURCE_FILES) == len(set(D._SOURCE_FILES)) == 46
    assert len(D._CARRY_SOURCE_FILES) == len(set(D._CARRY_SOURCE_FILES)) == 49
    name = 'execution_launch/managed_behavior.py'
    assert name in D._SOURCE_FILES
    watched = Path(D.__file__).resolve().parent.parent / name
    body, original_open = watched.read_bytes(), Path.open
    def changed(path, *args, **kwargs):
        if path == watched and args == ('rb',):
            return BytesIO(body + b'\n# synthetic shared behavior change\n')
        return original_open(path, *args, **kwargs)
    with patch.object(Path, 'open', changed):
        for env in (legacy, carry):
            L.reject(lambda env=env: D.describe_fixed_driver(env.driver), 'FIXED_DRIVER_DEPLOYMENT_CHANGED')
    assert D.describe_fixed_driver(legacy.driver).factory_id == D.FACTORY_ID
    assert D.describe_fixed_carry_driver(carry.driver).factory_id == B.CARRY_FACTORY_ID


def test_valid_sell_and_buy_below_minimum_remain_blocked_model_candidates():
    sell = fixture(index=4, cash=Dec('9999'), units=Dec('0.01'), rising=False)
    sell.bars = tuple(replace(row, bid=Dec(100-i), ask=Dec(102-i), mark=Dec(101-i))
                      for i, row in enumerate(sell.bars))
    frame_at(sell, 4, cash=Dec('9999'), units=Dec('0.01'))
    signal = L.decide(sell)
    assert signal.action == 'hold' and signal.decision_state == 'cash_target'
    assert signal.execution_block_reasons == ('MANAGED_ORDER_BELOW_MINIMUM',)
    buy = fixture(index=4, cash=Dec('0.001'), units=Dec(0))
    signal = L.decide(buy)
    assert signal.action == 'hold' and signal.decision_state == 'long_target'
    assert signal.execution_block_reasons == ('MANAGED_ORDER_BELOW_MINIMUM',)


def test_carry_deadline_is_issued_runtime_window_not_research_capture_end():
    env = fixture()
    assert env.protocol.capture_end != env.window.end
    assert D.fixed_carry_deadline(env.driver) == env.window.end
    legacy = L.fixture()
    L.reject(lambda: D.fixed_carry_deadline(legacy.driver), 'FIXED_DRIVER_FACTORY_PROTOCOL_MISMATCH')
    clone = StrategyDriver(callback=env.driver.callback, artifact=env.driver.artifact,
                           parameters_json=env.driver.parameters_json)
    L.reject(lambda: D.fixed_carry_deadline(clone), 'FIXED_DRIVER_NOT_ISSUED')
