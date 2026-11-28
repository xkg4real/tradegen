"""Pure parser for the shared tradegen.odds_plan/1 file format."""
from __future__ import annotations

from datetime import date
import json

from core.odds import plan


_SCHEMA = "tradegen.odds_plan/1"
_PLAN_KEYS = frozenset({"name", "track", "stake_krw", "target_krw", "fx_krw_per_usd", "start", "horizon_days",
                        "fraction"})
_LEG_KEYS = frozenset({"venue", "symbol", "model", "bracket", "sizing", "edge_source", "assumed_p"})


class _Bad(ValueError):
    """A plan object the file format does not allow (CONTRACT 14.2)."""


def _no_constant(name: str):
    raise ValueError(f"{name} is not a JSON number")


def _no_repeats(pairs: list) -> dict:
    """A JSON object; a key given twice is refused, never silently overwritten."""
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError("a key appears twice in one object")
    return obj


def _obj(value, keys: frozenset, where: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise _Bad(f"{where}: expected an object with exactly the keys {sorted(keys)}")
    return value


def _str(value, where: str) -> str:
    if type(value) is not str:
        raise _Bad(f"{where}: expected text")
    return value


def _num(value, where: str, *, optional: bool = False) -> float | None:
    """A JSON number as a float (an int is converted, a bool is no number); None only when `optional`."""
    if value is None and optional:
        return None
    if type(value) not in (int, float):
        raise _Bad(f"{where}: expected a number")
    try:
        return float(value)
    except OverflowError:
        raise _Bad(f"{where}: too large for a float") from None


def _day(text: str) -> date | str:
    """An exact YYYY-MM-DD as a date; any other text unchanged, for plan.check_plan to refuse (sub "start")."""
    try:
        day = date.fromisoformat(text)
    except ValueError:
        return text
    return day if day.isoformat() == text else text


def _leg(value, where: str) -> plan.Leg:
    obj = _obj(value, _LEG_KEYS, where)
    bracket = obj["bracket"]
    if bracket is not None:
        b = _obj(bracket, frozenset({"take_profit", "stop"}), f"{where}.bracket")
        bracket = plan.Bracket(take_profit=_num(b["take_profit"], f"{where}.bracket.take_profit"),
                               stop=_num(b["stop"], f"{where}.bracket.stop"))
    return plan.Leg(venue=_str(obj["venue"], f"{where}.venue"), symbol=_str(obj["symbol"], f"{where}.symbol"),
                    model=_str(obj["model"], f"{where}.model"), bracket=bracket,
                    sizing=_str(obj["sizing"], f"{where}.sizing"),
                    edge_source=_str(obj["edge_source"], f"{where}.edge_source"),
                    assumed_p=_num(obj["assumed_p"], f"{where}.assumed_p", optional=True))


def _plan(value, where: str) -> plan.Plan:
    """One plan object as a Plan whose values plan.check_plan judges. A `legs` list of one is that leg; a longer one
    stays a tuple, which check_plan refuses MULTI_LEG_UNSUPPORTED; an empty one is no readable plan. horizon_days
    stays the JSON number it is, so check_plan refuses a float (sub "horizon")."""
    many = type(value) is dict and "legs" in value
    obj = _obj(value, _PLAN_KEYS | {"legs" if many else "leg"}, where)
    if many:
        if type(obj["legs"]) is not list or not obj["legs"]:
            raise _Bad(f"{where}.legs: expected a non-empty list")
        legs = tuple(_leg(x, f"{where}.legs[{n}]") for n, x in enumerate(obj["legs"]))
        leg = legs[0] if len(legs) == 1 else legs
    else:
        leg = _leg(obj["leg"], f"{where}.leg")
    if type(obj["horizon_days"]) not in (int, float):
        raise _Bad(f"{where}.horizon_days: expected a number")
    fraction = _obj(obj["fraction"], frozenset({"kind", "value"}), f"{where}.fraction")
    return plan.Plan(name=_str(obj["name"], f"{where}.name"), track=_str(obj["track"], f"{where}.track"),
                     stake_krw=_num(obj["stake_krw"], f"{where}.stake_krw"),
                     target_krw=_num(obj["target_krw"], f"{where}.target_krw"),
                     fx_krw_per_usd=_num(obj["fx_krw_per_usd"], f"{where}.fx_krw_per_usd"),
                     start=_day(_str(obj["start"], f"{where}.start")), horizon_days=obj["horizon_days"], leg=leg,
                     fraction=plan.Fraction(kind=_str(fraction["kind"], f"{where}.fraction.kind"),
                                            value=_num(fraction["value"], f"{where}.fraction.value", optional=True)))


def load_plans(raw: bytes) -> list[plan.Plan | plan.Refusal]:
    """The plans of a plan file (CONTRACT 14.2) in file order: each a plan.Plan, or a plan.Refusal
    UNSUPPORTED_PRODUCT sub "file" for a plan object the format does not allow; one such Refusal for the whole file
    when it is not UTF-8 JSON (NaN, Infinity and repeated keys refused) holding exactly `schema`
    (tradegen.odds_plan/1) and a non-empty `plans` list. Only shapes and JSON types are checked here."""
    try:
        doc = json.loads(raw.decode("utf-8"), parse_constant=_no_constant, object_pairs_hook=_no_repeats)
        if type(doc) is not dict or set(doc) != {"schema", "plans"} or doc["schema"] != _SCHEMA:
            raise ValueError(f"expected exactly the keys schema ({_SCHEMA}) and plans")
        if type(doc["plans"]) is not list or not doc["plans"]:
            raise ValueError("plans: expected a non-empty list")
    except (ValueError, RecursionError) as exc:        # UnicodeDecodeError, JSONDecodeError; nesting too deep
        return [plan.Refusal(code="UNSUPPORTED_PRODUCT", sub="file", detail=f"plan file: {exc}")]
    out = []
    for n, value in enumerate(doc["plans"]):
        try:
            out.append(_plan(value, f"plans[{n}]"))
        except _Bad as exc:
            out.append(plan.Refusal(code="UNSUPPORTED_PRODUCT", sub="file", detail=str(exc)))
    return out
