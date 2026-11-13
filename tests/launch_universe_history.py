"""Universe windows of the fixed driver and LiveHistory (spec section 12): invented books, flag and ticker reads,
snapshots and account anchors over a temporary state root and head root; no network, credentials or real home."""
from dataclasses import replace
from decimal import Decimal
import hashlib
from types import SimpleNamespace

from execution_launch.driver import ChooserInputs, chooser_decision
from execution_launch.profile import profile_contract_digest, rule_terms_digest
from execution_launch.program import ChooserState, ProgramSpec, program_digest
from execution_launch.strategy import UNIVERSE_EVALUATOR_REVISION
from tests import launch_driver as LD
from tests import launch_live_history as LH

D = Decimal
RULE = hashlib.sha256(b"fixture-universe-rule").hexdigest()
BTC, ETH, XRP = "KRW-BTC", "KRW-ETH", "KRW-XRP"


def universe_env():
    """LD.fixture() as a universe deployment: the rotation program (L=1, m=1, margin 0, N=2), an IOC profile with
    the rule, and a protocol whose symbol stays the benchmark KRW-BTC."""
    e = LD.fixture()
    program = ProgramSpec(schema_version=2, strategy_id=e.program.strategy_id, kind="universe_top1_momentum",
                          fast_window=0, slow_window=0, exposure_fraction=D("0.5"), lookback_slots=1,
                          min_hold_slots=1, switch_margin=D(0), max_candidates=2, universe_rule_sha256=RULE)
    code = program_digest(program, e.artifact)
    profile = replace(e.profile, strategy_code_sha256=code, time_in_force="ioc", universe_rule_sha256=RULE)
    protocol = replace(e.protocol, strategy_code_sha256=code, evaluator_revision=UNIVERSE_EVALUATOR_REVISION,
                       universe_rule_sha256=RULE, profile_contract_digest=profile_contract_digest(profile),
                       rule_terms_digest=rule_terms_digest(profile.instrument_rules, universe_rule_sha256=RULE))
    return SimpleNamespace(program=program, protocol=protocol, profile=profile, artifact=e.artifact,
                           window=replace(e.window, deployment_id="invented-universe-deployment"),
                           provider=e.provider, verifier=e.verifier)


def inputs(**changes):
    """The inputs of a decision with BTC held for two decisions and ETH well ahead over one slot."""
    values = dict(held=BTC, hold_count=2, top_n=(BTC, ETH), flags=((BTC, "unflagged"), (ETH, "unflagged")),
                  prices=((BTC, D(122)), (ETH, D(130))), lag_prices=((BTC, D(121)), (ETH, D(106))))
    return ChooserInputs(**(values | changes))


def test_chooser_decision_recomputes_one_decision_from_its_inputs():
    program = universe_env().program
    assert chooser_decision(program, inputs()) == (ETH, ChooserState(held=ETH, hold_count=1))
    assert chooser_decision(program, inputs(held=None, hold_count=0, lag_prices=None)) == (
        None, ChooserState(held=None, hold_count=1))
    assert chooser_decision(program, inputs(flags=((BTC, "warning"), (ETH, "unflagged")))) == (
        None, ChooserState(held=None, hold_count=1))
    for bad in (None, {"held": BTC}, inputs(top_n=[BTC, ETH]), inputs(flags=((BTC,),)),
                inputs(prices=((BTC, 122),)), inputs(top_n=(BTC, ETH, XRP))):
        LH.refused(lambda: chooser_decision(program, bad), "FIXED_DRIVER_CHOOSER_INPUTS_REQUIRED")
