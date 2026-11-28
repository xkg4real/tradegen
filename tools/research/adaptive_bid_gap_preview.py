"""Offline BR-26 research. Run with --example or --input FILE.json. No order or signing API."""
from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
import re
import stat

from tools.research import _native_bridge


MAX_Y = Decimal("0.05")
MAX_FILE = 1024 * 1024
SCHEMA = "tradegen-adaptive-bid-gap-preview-v1"


class Invalid(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Invalid(reason)


def fraction(value, low, high, *, inclusive_low=True):
    need(isinstance(value, str) and re.fullmatch(r"(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,16})?", value),
         "INVALID_DECIMAL")
    number = Decimal(value)
    need((low <= number if inclusive_low else low < number) and number <= high, "DECIMAL_OUT_OF_RANGE")
    return number


def integer(value, low, high):
    need(type(value) is int and low <= value <= high, "INTEGER_OUT_OF_RANGE")
    return value


def model_id(model):
    raw = json.dumps(model, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def bounds(value):
    return fraction(value, 0, MAX_Y, inclusive_low=False)


def wilson_lower(successes, total):
    """Two-sided nominal 95% binomial interval lower endpoint, not a market guarantee."""
    if not total:
        return 0.0
    z = 1.959963984540054
    p = successes / total
    margin = z * math.sqrt(p * (1 - p) / total + z ** 2 / (4 * total ** 2))
    return (p + z ** 2 / (2 * total) - margin) / (1 + z ** 2 / total)


def sample_direction(log_returns, config, origin):
    native_counts = _native_bridge.sample_direction_native(log_returns, config, origin)
    if native_counts is not None:
        return native_counts
    length, horizon, draws = config["block"], config["horizon"], config["paths"]
    rng = random.Random((config["seed"] << 40) + origin)
    positive, negative = 0, 0
    for _ in range(draws):
        remaining, total = horizon, 0.0
        while remaining:
            take = min(remaining, length)
            start = rng.randrange(len(log_returns) - length + 1)
            total += math.fsum(log_returns[start:start + take])
            remaining -= take
        positive += total > config["up_barrier"]
        negative += total < config["down_barrier"]
    return positive, negative


def confidence(counts, config):
    for direction, count in zip(("up", "down"), counts):
        if wilson_lower(count, config["paths"]) >= config["threshold"]:
            return direction
    return None


def validate_model(model, cap):
    """Only these pinned choices participate in the v1 forecast."""
    required = {"scope", "source_id", "first_validation_origin", "rule_version", "frozen_at", "step_seconds", "lookback", "block", "horizon",
                "paths", "seed", "cost_bps", "confidence", "min_validation_calls", "max_calibration_gap",
                "up_y", "down_y"}
    need(set(model) == required and model["rule_version"] == "moving-block-v1", "MODEL_FORMAT")
    config = dict(model)
    for key, maximum in (("step_seconds", 86400), ("lookback", 512), ("block", 128), ("horizon", 32),
                         ("paths", 10000), ("min_validation_calls", 1000)):
        integer(model[key], 1, maximum)
    integer(model["seed"], 0, 2**31 - 1)
    integer(model["frozen_at"], 0, 2**39)
    integer(model["first_validation_origin"], 0, 2**39)
    need(type(model["source_id"]) is str and 0 < len(model["source_id"]) <= 140, "INVALID_SOURCE_ID")
    need(model["block"] <= min(model["lookback"], model["horizon"]), "MODEL_BLOCK")
    need(model["paths"] >= 64, "MODEL_PATHS")
    hurdle = integer(model["cost_bps"], 0, 9999) / 10000
    config["up_barrier"], config["down_barrier"] = math.log1p(hurdle), math.log1p(-hurdle)
    config["threshold"] = float(fraction(model["confidence"], Decimal("0.5"), 1, inclusive_low=False))
    config["max_gap"] = float(fraction(model["max_calibration_gap"], 0, 1))
    for key in ("up_y", "down_y"):
        config[key] = bounds(model[key])
        need(config[key] <= cap, "MODEL_TARGET_OUTSIDE_ENVELOPE")
    return config


def reviewed_counts(history, config, now):
    bars = history["bars"]
    need(type(bars) is list and 1 <= len(bars) <= 1024, "HISTORY_SIZE")
    step, n, h = config["step_seconds"], config["lookback"], config["horizon"]
    returns, known, ends = [], [], []
    for bar in bars:
        end = integer(bar["end"], 0, now - 1)
        published = integer(bar["known_at"], end, now - 1)
        need(not ends or end - ends[-1] == step, "MISSING_OR_DUPLICATE_BAR")
        value = integer(bar["return_bps"], -9999, 100000)
        ends.append(end)
        known.append(published)
        returns.append(math.log1p(value / 10000))
    need(now - ends[-1] <= step, "STALE_FEATURES")
    folds = (len(bars) - n) // h
    need(folds >= config["min_validation_calls"], "INSUFFICIENT_HOLDOUT")
    need((folds + 1) * h * config["paths"] <= 2_000_000, "SIMULATION_BUDGET")
    need(config["first_validation_origin"] == ends[n - 1], "HOLDOUT_WINDOW_MISMATCH")
    need(config["frozen_at"] < ends[n - 1], "MODEL_NOT_FROZEN_BEFORE_HOLDOUT")
    stats = {d: {"calls": 0, "hits": 0, "prob_sum": 0.0} for d in ("up", "down")}
    for split in range(n, len(bars) - h + 1, h):
        origin = ends[split - 1]
        # The fold forecasts once its last feature is published, before the next bar closes: the
        # same lag the current forecast allows (known_at < as_of <= last end + step).
        need(max(known[split-n:split]) < origin + step, "HOLDOUT_FEATURE_NOT_YET_KNOWN")
        counts = sample_direction(returns[split-n:split], config, origin)
        direction = confidence(counts, config)
        if direction:
            realized = math.fsum(returns[split:split+h])
            hit = realized > config["up_barrier"] if direction == "up" else realized < config["down_barrier"]
            values = stats[direction]
            values["calls"] += 1
            values["hits"] += int(hit)
            values["prob_sum"] += counts[0 if direction == "up" else 1] / config["paths"]
    current = sample_direction(returns[-n:], config, ends[-1])
    return current, stats, folds


def moving_block_direction(document, terms, scope, cap, now, out):
    """Built-in direction source: None (reason set) or (direction, holdout stats, pinned limits)."""
    model, history = document["model"], document["history"]
    need(terms["model_sha256"] is not None and model_id(model) == terms["model_sha256"], "MODEL_NOT_BOUND")
    need(model["scope"] == scope == history["scope"], "MODEL_OR_HISTORY_SCOPE_MISMATCH")
    config = validate_model(model, cap)
    out["model_sha256"] = terms["model_sha256"]
    need(history["source_id"] == config["source_id"], "EVIDENCE_SOURCE_MISMATCH")
    counts, stats, folds = reviewed_counts(history, config, now)
    up, down = counts
    out["path_counts"] = {"up": up, "down": down, "neutral": config["paths"] - up - down}
    paths = config["paths"]
    out["probabilities"] = {"up": up / paths, "down": down / paths, "neutral": (paths-up-down) / paths}
    out["nonoverlap_folds"] = folds
    direction = confidence(counts, config)
    if not direction:
        out["reason"] = "MODEL_UNCERTAIN"
        return None
    return direction, stats, config


def evaluate(document, direction_source=moving_block_direction):
    out = {"schema": SCHEMA, "status": "REVIEW", "current_y": None, "candidate_next_y": None,
           "quote_state": "UNKNOWN", "model_checks_passed": False, "execution_ready": False}
    try:
        need(document["schema"] == SCHEMA, "INPUT_SCHEMA")
        terms = document["terms"]
        if terms is None:
            out.update(status="NO_SIGNED_Y", current_y="0", new_buys_blocked=True)
            active = Decimal(0)
        else:
            cap = bounds(terms["ceiling_y"])
            if terms["current_y"] is None:
                active = Decimal(0)
                out.update(current_y="0", status="RECOVERY_REQUIRED", new_buys_blocked=True)
            else:
                active = bounds(terms["current_y"])
                need(active <= cap, "CURRENT_TERMS_OUTSIDE_ENVELOPE")
                out.update(current_y=str(active), status="HOLD_CURRENT")
        obs = document["observation"]
        scope = obs["scope"]
        need(type(scope) is str and 0 < len(scope) <= 140, "INVALID_SCOPE")
        if terms is not None:
            need(scope == terms["scope"], "OBSERVATION_SCOPE_MISMATCH")
        now = integer(obs["as_of"], 1, 2**39)
        trade_at = integer(obs["last_trade_at"], 0, now)
        mark = fraction(obs["last_trade"], 0, 10**16, inclusive_low=False)
        stored_block = obs["prior_block_active"]
        need(type(stored_block) is bool, "UNKNOWN_PRIOR_BLOCK")
        if stored_block:
            out["new_buys_blocked"] = True
        stale_trade = now - trade_at > 30
        if obs["bid"] is None or obs["bid_at"] != now or type(obs["bid_at"]) is not int:
            out.update(quote_state="BID_UNAVAILABLE", reason="BID_UNAVAILABLE")
            if stale_trade:
                out["new_buys_blocked"] = True
            return out
        bid = fraction(obs["bid"], 0, 10**16, inclusive_low=False)
        # Preserve the exact BR-10 equality boundary even on very small tick sizes.
        past_threshold = Fraction(bid) <= Fraction(mark) * (1 - Fraction(active))
        triggered = stale_trade and past_threshold
        out["quote_state"] = "BID_GAP_TRIGGERED" if triggered else "NO_STALE_BID_GAP"
        if triggered or stored_block or not active:
            out.update(new_buys_blocked=True, reason="BID_GAP_TRIGGERED" if triggered else
                       ("PRIOR_BLOCK" if stored_block else out["status"]))
            return out
        found = direction_source(document, terms, scope, cap, now, out)
        if found is None:
            return out
        direction, stats, config = found
        checked = stats[direction]
        calls, hits = checked["calls"], checked["hits"]
        lower = wilson_lower(hits, calls)
        gap = abs((checked["prob_sum"] - hits) / calls) if calls else None
        out["holdout"] = {"direction": direction, "calls": calls, "hits": hits, "hit_lower_95": lower,
                          "directional_calibration_gap": gap}
        if calls < config["min_validation_calls"] or lower < config["threshold"] or gap > config["max_gap"]:
            out["reason"] = "DIRECTION_NOT_VALIDATED"
            return out
        out["model_checks_passed"] = True
        target = min(active, config["down_y"]) if direction == "down" else config["up_y"]
        if target == active:
            out["reason"] = "AT_DIRECTIONAL_TARGET"
            return out
        if target > active and past_threshold:
            out["reason"] = "OBSERVED_BID_PRECLUDES_WIDENING"
            return out
        out.update(status="PROPOSAL_ONLY", candidate_next_y=str(target), direction=direction,
                   reason="FUTURE_CLEAN_OBSERVATION_REQUIRED", applies_after=now)
        return out
    except (Invalid, KeyError, TypeError, ValueError, ArithmeticError, RecursionError) as exc:
        if out["quote_state"] == "UNKNOWN":
            out["new_buys_blocked"] = True
        out["reason"] = str(exc) if type(exc) is Invalid else "MALFORMED_OR_MISSING_EVIDENCE"
        return out


def example():
    scope, start = "synthetic-upbit-krw-spot", 1_700_000_000
    model = {"scope": scope, "source_id": "synthetic-feed-v1", "first_validation_origin": start + 11*60,
             "rule_version": "moving-block-v1", "frozen_at": start - 1000,
             "step_seconds": 60, "lookback": 12, "block": 2, "horizon": 2, "paths": 400, "seed": 8,
             "cost_bps": 10, "confidence": "0.75", "min_validation_calls": 16, "max_calibration_gap": "0.10",
             "up_y": "0.03", "down_y": "0.01"}
    bars = [{"end": start+60*i, "known_at": start+60*i, "return_bps": 18 + i % 4} for i in range(60)]
    now = bars[-1]["end"] + 1
    return {"schema": SCHEMA, "terms": {"scope": scope, "ceiling_y": "0.05", "current_y": "0.02",
            "model_sha256": model_id(model)}, "model": model,
            "history": {"scope": scope, "source_id": model["source_id"], "bars": bars},
            "observation": {"scope": scope, "as_of": now, "last_trade_at": now - 45, "last_trade": "10000",
                            "bid": "9900", "bid_at": now, "prior_block_active": False}}


def read_input(path):
    def unique(items):
        result = dict(items)
        need(len(result) == len(items), "DUPLICATE_JSON_KEY")
        return result
    info = path.stat()
    need(path.suffix.lower() == ".json" and stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE, "INPUT_FILE")
    with path.open("rb") as file:
        raw = file.read(MAX_FILE + 1)
    need(len(raw) <= MAX_FILE, "INPUT_FILE")
    def reject_constant(_):
        raise Invalid("NONFINITE_JSON_NUMBER")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--example", action="store_true", help="print a synthetic illustrative JSON fixture")
    source.add_argument("--input", type=Path, help="explicit local research JSON file")
    args = parser.parse_args()
    try:
        report = example() if args.example else evaluate(read_input(args.input))
    except (Invalid, OSError, ValueError, RecursionError):
        parser.exit(2, "Could not read a bounded, valid research JSON input.\n")
    print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
