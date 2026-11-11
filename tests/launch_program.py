"""Program schema v2 and the universe chooser (spec section 14); invented values only, no market data."""
from dataclasses import replace
from decimal import Decimal, localcontext
import hashlib
import json

from execution_launch.program import (ProgramError, ProgramSpec, parameters_json, parse_program,
    program_digest, program_json, target_fraction)
from execution_launch.strategy import _plain, evidence_digest

D = Decimal
ARTIFACT = b"fixture-program-artifact"
RULE = hashlib.sha256(b"fixture-universe-rule").hexdigest()
TREND = ProgramSpec(schema_version=1, strategy_id="test-strategy", kind="moving_average_trend",
                    fast_window=2, slow_window=4, exposure_fraction=D("0.5"))
CASH = ProgramSpec(schema_version=1, strategy_id="fixture-cash", kind="cash", fast_window=0, slow_window=0,
                   exposure_fraction=D("0"))


def rotation(**changes):
    values = dict(schema_version=2, strategy_id="fixture-rotation", kind="universe_top1_momentum",
                  fast_window=0, slow_window=0, exposure_fraction=D("0.5"), lookback_slots=3,
                  min_hold_slots=2, switch_margin=D("0.01"), max_candidates=3, universe_rule_sha256=RULE)
    return ProgramSpec(**(values | changes))


def rejected(call, code=None):
    try:
        call()
    except ProgramError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected program refusal")


def test_existing_kinds_keep_parameters_digests_and_plan_encoding_byte_for_byte():
    assert parameters_json(TREND) == ('{"exposure_fraction":"0.5","fast_window":2,"kind":"moving_average_trend",'
                                      '"schema_version":1,"slow_window":4,"strategy_id":"test-strategy"}')
    assert program_digest(TREND, ARTIFACT) == "19aefe2ec60beb021706e946813da7ac9c96802ebd72bc7c87c4fdf5739f9fff"
    assert program_digest(CASH, ARTIFACT) == "277aa374f681fc5c688ae28a4ed23d3cf148dbd27dfd83364598b94e78cf3d50"
    # Study plans and commitments encode programs through strategy._plain.
    assert evidence_digest(TREND) == "965a008190694d2821ffaaafff36e678bd474cb3495c4b0cbdcedb7a8cb9f433"
    assert sorted(_plain(TREND)) == ["exposure_fraction", "fast_window", "kind", "schema_version",
                                     "slow_window", "strategy_id"]
    for spec in (TREND, CASH):
        assert parse_program(program_json(spec)) == spec
        assert parse_program(json.dumps(_plain(spec))) == spec


def test_rotation_kind_is_schema_2_and_round_trips_through_every_encoding():
    spec = rotation()
    assert json.loads(parameters_json(spec)) == {
        "schema_version": 2, "strategy_id": "fixture-rotation", "kind": "universe_top1_momentum",
        "fast_window": 0, "slow_window": 0, "exposure_fraction": "0.5", "lookback_slots": 3,
        "min_hold_slots": 2, "switch_margin": "0.01", "max_candidates": 3, "universe_rule_sha256": RULE}
    assert parse_program(program_json(spec)) == spec
    assert parse_program(json.dumps(_plain(spec))) == spec
    digest = program_digest(spec, ARTIFACT)
    for changes in ({"lookback_slots": 4}, {"min_hold_slots": 3}, {"switch_margin": D("0.02")},
                    {"max_candidates": 2}, {"universe_rule_sha256": "f"*64}, {"exposure_fraction": D("0.4")}):
        assert program_digest(rotation(**changes), ARTIFACT) != digest, changes
    assert program_digest(rotation(switch_margin=D("0.010")), ARTIFACT) == digest


def test_rotation_parameters_are_validated_and_closed_to_the_other_kinds():
    for changes, code in (({"schema_version": 1}, "PROGRAM_SCHEMA_INVALID"),
                          ({"fast_window": 2}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"lookback_slots": 0}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"lookback_slots": True}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"min_hold_slots": 0}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"max_candidates": 0}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"universe_rule_sha256": "F"*64}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"universe_rule_sha256": None}, "PROGRAM_UNIVERSE_PARAMETERS_INVALID"),
                          ({"switch_margin": None}, "PROGRAM_DECIMAL_REQUIRED"),
                          ({"switch_margin": D("-0.01")}, "PROGRAM_AMOUNT_INVALID"),
                          ({"exposure_fraction": D("0")}, "PROGRAM_EXPOSURE_INVALID"),
                          ({"exposure_fraction": D("1.01")}, "PROGRAM_EXPOSURE_INVALID")):
        rejected(lambda changes=changes: parameters_json(rotation(**changes)), code)
    rejected(lambda: parameters_json(replace(TREND, schema_version=2)), "PROGRAM_SCHEMA_INVALID")
    rejected(lambda: parameters_json(replace(TREND, lookback_slots=3)), "PROGRAM_UNIVERSE_PARAMETERS_INVALID")
    rejected(lambda: target_fraction(rotation(), (D(1),)*8), "PROGRAM_KIND_UNSUPPORTED")
    body = json.loads(program_json(rotation()))
    for key in ("lookback_slots", "switch_margin", "universe_rule_sha256"):
        rejected(lambda key=key: parse_program(json.dumps({k: v for k, v in body.items() if k != key})),
                 "PROGRAM_JSON_SCHEMA_INVALID")
    rejected(lambda: parse_program(json.dumps(body | {"switch_margin": "1e-2"})), "PROGRAM_DECIMAL_STRING_REQUIRED")
    rejected(lambda: parse_program(json.dumps(body | {"switch_margin": None})), "PROGRAM_DECIMAL_STRING_REQUIRED")
    rejected(lambda: parse_program(json.dumps(body).replace('"0.01"', '0.01')), "PROGRAM_JSON_NUMBER_INVALID")
    trend = json.loads(program_json(TREND))
    rejected(lambda: parse_program(json.dumps(trend | {"lookback_slots": 3})), "PROGRAM_JSON_SCHEMA_INVALID")
    rejected(lambda: parse_program(json.dumps(trend | {k: v for k, v in body.items() if k not in trend})),
             "PROGRAM_UNIVERSE_PARAMETERS_INVALID")
