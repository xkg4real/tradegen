"""Program schema v2 and the universe chooser (spec section 14); invented values only, no market data."""
from dataclasses import replace
from decimal import Decimal, localcontext
import hashlib
import json

from execution_launch.program import (ChooserSlot, ChooserState, ProgramError, ProgramSpec, choose,
    parameters_json, parse_program, program_digest, program_json, target_fraction)
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


COINS = ("KRW-AAA", "KRW-BBB", "KRW-CCC")
LAG = ChooserSlot(top_n=COINS, flags={coin: "unflagged" for coin in COINS}, prices={coin: D(100) for coin in COINS})
CASH_STATE = ChooserState(held=None, hold_count=3)


def at(prices, flags=None, top=COINS):
    """Slot k: decimal-string prices, every top-N coin unflagged unless flags says otherwise."""
    return ChooserSlot(top_n=top, flags={coin: "unflagged" for coin in top} if flags is None else flags,
                       prices={coin: D(value) for coin, value in prices.items()})


def held(coin, count=2):
    return ChooserState(held=coin, hold_count=count)


def decide(state, now, lag=LAG, **changes):
    """rotation() has L=3, m=2, switch_margin=0.01, N=3; LAG prices every coin at 100."""
    return choose(rotation(**changes), state, now, lag)


def test_rule_1_a_warning_on_the_held_coin_decides_cash_even_inside_the_minimum_hold():
    now = at({"KRW-AAA": "130", "KRW-BBB": "101"}, {"KRW-AAA": "warning", "KRW-BBB": "unflagged"})
    assert decide(held("KRW-AAA", 1), now) == (None, ChooserState(held=None, hold_count=1))
    unpriced = ChooserSlot(top_n=COINS, flags={"KRW-AAA": "warning"}, prices={})  # only the ticker read failed
    assert decide(held("KRW-AAA", 1), unpriced) == (None, ChooserState(held=None, hold_count=1))


def test_rule_2_a_held_coin_without_a_return_is_kept():
    for now, lag in ((at({"KRW-BBB": "150"}), LAG),                         # no price for the held coin now
                     (at({"KRW-AAA": "90", "KRW-BBB": "150"}), None),        # no slot L back yet
                     (ChooserSlot(top_n=COINS, flags={}, prices={}), LAG)):  # flag read unavailable
        assert decide(held("KRW-AAA"), now, lag) == ("KRW-AAA", ChooserState(held="KRW-AAA", hold_count=3))
    assert decide(held("KRW-ZZZ"), at({"KRW-BBB": "150"}))[0] == "KRW-ZZZ"   # left the top-N, still no return


def test_rule_3_best_is_the_largest_return_among_unflagged_top_n_coins_ties_by_symbol():
    flags = {"KRW-AAA": "caution", "KRW-BBB": "unflagged", "KRW-CCC": "unflagged"}
    now = at({"KRW-AAA": "200", "KRW-BBB": "110", "KRW-CCC": "110", "KRW-ZZZ": "300"}, flags)
    assert decide(CASH_STATE, now)[0] == "KRW-BBB"  # AAA is caution, ZZZ is outside the top-N, BBB ties CCC
    now = at({"KRW-AAA": "120", "KRW-CCC": "110"}, {**flags, "KRW-AAA": "unknown"})
    assert decide(CASH_STATE, now)[0] == "KRW-CCC"  # unknown is not unflagged; BBB has no price


def test_rule_4_from_cash_only_a_strictly_positive_best_is_bought():
    assert decide(CASH_STATE, at({"KRW-BBB": "101"})) == ("KRW-BBB", ChooserState(held="KRW-BBB", hold_count=1))
    assert decide(CASH_STATE, at({"KRW-BBB": "100", "KRW-CCC": "99"})) == (None, ChooserState(held=None, hold_count=4))
    odd_lag = ChooserSlot(top_n=(), flags={coin: "warning" for coin in COINS}, prices=LAG.prices)
    assert decide(CASH_STATE, at({"KRW-BBB": "101"}), odd_lag) == (   # the lag slot's top-N and flags are never read
        "KRW-BBB", ChooserState(held="KRW-BBB", hold_count=1))
    assert decide(CASH_STATE, at({"KRW-BBB": "150"}), None)[0] is None       # warm-up: no lag slot, no target
    assert decide(ChooserState(held=None, hold_count=0), at({}))[0] is None  # window start with an empty read


def test_rule_5_the_minimum_hold_counts_decisions_and_comes_before_rules_6_and_7():
    now = at({"KRW-AAA": "90", "KRW-BBB": "150"})
    assert decide(held("KRW-AAA", 1), now) == ("KRW-AAA", ChooserState(held="KRW-AAA", hold_count=2))
    assert decide(held("KRW-AAA", 2), now) == ("KRW-BBB", ChooserState(held="KRW-BBB", hold_count=1))
    assert decide(held("KRW-AAA", 1), now, min_hold_slots=1)[0] == "KRW-BBB"
    # r_h < 0 and r_best < 0: rule 6 alone would say cash, rule 5 keeps the coin inside the minimum hold
    assert decide(held("KRW-AAA", 1), at({"KRW-AAA": "90", "KRW-BBB": "99"})) == (
        "KRW-AAA", ChooserState(held="KRW-AAA", hold_count=2))


def test_a_held_coin_outside_the_top_n_with_a_defined_return_still_runs_rules_5_to_8():
    lag = ChooserSlot(top_n=COINS, flags=LAG.flags, prices={**LAG.prices, "KRW-ZZZ": D(100)})
    assert decide(held("KRW-ZZZ", 2), at({"KRW-ZZZ": "90", "KRW-BBB": "150"}), lag) == (
        "KRW-BBB", ChooserState(held="KRW-BBB", hold_count=1))


def test_rule_6_a_losing_hold_with_no_positive_target_goes_to_cash():
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "99", "KRW-BBB": "100"})) == (
        None, ChooserState(held=None, hold_count=1))
    flags = {"KRW-AAA": "unflagged", "KRW-BBB": "caution", "KRW-CCC": "warning"}
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "100", "KRW-BBB": "150", "KRW-CCC": "150"}, flags))[0] is None


def test_rule_7_switches_only_when_the_best_beats_the_held_return_by_more_than_the_margin():
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "101", "KRW-BBB": "103"})) == (
        "KRW-BBB", ChooserState(held="KRW-BBB", hold_count=1))
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "99", "KRW-BBB": "100.5"}))[0] == "KRW-BBB"


def test_rule_8_otherwise_the_held_coin_is_kept_including_a_caution_coin():
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "101", "KRW-BBB": "102"})) == (
        "KRW-AAA", ChooserState(held="KRW-AAA", hold_count=3))       # a gap of exactly the margin keeps h
    flags = {"KRW-AAA": "caution", "KRW-BBB": "unflagged", "KRW-CCC": "unflagged"}
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "110", "KRW-BBB": "105"}, flags))[0] == "KRW-AAA"
    assert decide(held("KRW-AAA"), at({"KRW-AAA": "110", "KRW-BBB": "102"}))[0] == "KRW-AAA"  # h is the best


def test_a_switch_path_counts_decisions_and_ignores_the_decimal_context():
    state, path = ChooserState(held=None, hold_count=0), []
    for prices in ({"KRW-AAA": "101"}, {"KRW-AAA": "101", "KRW-BBB": "120"}, {"KRW-AAA": "101", "KRW-BBB": "120"}):
        with localcontext() as numeric:
            numeric.prec = 2
            decision, state = decide(state, at(prices))
        path.append((decision, state.hold_count))
    assert path == [("KRW-AAA", 1), ("KRW-AAA", 2), ("KRW-BBB", 1)]


def test_chooser_refuses_other_kinds_bad_state_bad_prices_and_a_wider_candidate_set():
    rejected(lambda: choose(TREND, CASH_STATE, at({}), LAG), "PROGRAM_KIND_UNSUPPORTED")
    for state in (ChooserState(held=None, hold_count=-1), ChooserState(held=5, hold_count=1), (None, 0)):
        rejected(lambda state=state: decide(state, at({})), "PROGRAM_CHOOSER_INPUT_INVALID")
    rejected(lambda: decide(CASH_STATE, at({}, top=COINS+("KRW-DDD",))), "PROGRAM_CHOOSER_INPUT_INVALID")
    rejected(lambda: decide(CASH_STATE, at({}, {"KRW-AAA": "Warning"})), "PROGRAM_CHOOSER_INPUT_INVALID")
    rejected(lambda: decide(CASH_STATE, at({}), at({}, {"KRW-AAA": "bogus"})), "PROGRAM_CHOOSER_INPUT_INVALID")
    rejected(lambda: decide(CASH_STATE, at({}, {"KRW-AAA": 1})), "PROGRAM_CHOOSER_INPUT_INVALID")
    rejected(lambda: decide(CASH_STATE, at({"KRW-AAA": "0"})), "PROGRAM_AMOUNT_INVALID")
    rejected(lambda: decide(CASH_STATE, ChooserSlot(top_n=COINS, flags={}, prices={"KRW-AAA": 101.0})),
             "PROGRAM_DECIMAL_REQUIRED")


def test_the_chooser_flag_classes_match_the_compliance_rules():
    from core.compliance import rules
    from execution_launch import program
    assert program._FLAG_CLASSES == frozenset(rules.FLAG_CLASSES)
