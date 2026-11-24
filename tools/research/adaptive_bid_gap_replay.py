"""Replay BR-26 offline on a fixed research scenario. No persistence, network or order API."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.research import adaptive_bid_gap_preview as preview


SCHEMA = "tradegen-adaptive-bid-gap-replay-v1"
OBSERVATION_KEYS = {
    "sequence", "as_of", "scope", "last_trade_at", "last_trade", "bid_at", "bid",
    "prior_block_active", "floor_halt", "daily_stop",
}


def visible_history(history, now):
    """A shared bar prefix prevents later snapshots from rewriting past returns."""
    if not isinstance(history, dict) or not isinstance(history.get("bars"), list):
        return None
    bars = history["bars"]
    if len(bars) > 1024:
        return None
    visible = []
    for bar in bars:
        if not isinstance(bar, dict) or type(bar.get("end")) is not int or type(bar.get("known_at")) is not int:
            return None
        if bar["end"] >= now or bar["known_at"] >= now:
            break
        visible.append(bar)
    return {**history, "bars": visible}


def path_steps(model, visible):
    if not isinstance(model, dict) or not visible:
        return 0
    n, h, paths = (model.get(field) for field in ("lookback", "horizon", "paths"))
    if any(type(value) is not int for value in (n, h, paths)) or min(n, h, paths) < 1:
        return 0   # The single-observation evaluator refuses an invalid model.
    folds = max(0, len(visible["bars"]) - n) // h
    return (folds + 1) * h * paths


def replay(document):
    """Replay a single scoped policy from a supplied research starting state.

    Sequence numbers start at one and refer to this input series. Duplicates
    must be byte-equivalent under canonical JSON. A rejected series has no
    usable partial result. Absence of a known initial Y retains zero monitoring.
    """
    result = {"schema": SCHEMA, "execution_ready": False}
    try:
        preview.need(set(document) == {"schema", "terms", "model", "history", "observations"}
                     and document["schema"] == SCHEMA, "INPUT_SCHEMA")
        terms, model, history = (document[k] for k in ("terms", "model", "history"))
        observations = document["observations"]
        preview.need(type(observations) is list and 1 <= len(observations) <= 128, "REPLAY_SIZE")
        current, scope = None, None
        if terms is not None:
            preview.need(isinstance(terms, dict) and
                         set(terms) == {"scope", "ceiling_y", "current_y", "model_sha256"}, "FIXED_TERMS")
            cap = preview.bounds(terms["ceiling_y"])
            if terms["current_y"] is not None:
                current = preview.bounds(terms["current_y"])
                preview.need(current <= cap, "CURRENT_TERMS_OUTSIDE_ENVELOPE")
            scope = terms["scope"]
        latched = current is None
        seen, rows = {}, []
        pending = None
        previous_time, steps = -1, 0
        for observation in observations:
            preview.need(type(observation) is dict and set(observation) == OBSERVATION_KEYS, "OBSERVATION_SCHEMA")
            sequence = preview.integer(observation["sequence"], 1, 128)
            encoded = json.dumps(observation, sort_keys=True, separators=(",", ":"), allow_nan=False)
            if sequence in seen:
                preview.need(seen[sequence] == encoded, "CONFLICTING_REPEAT")
                continue
            now = preview.integer(observation["as_of"], 1, 2**39)
            preview.need(sequence == len(seen) + 1 and now > previous_time, "CHRONOLOGY_UNRESOLVED")
            seen[sequence] = encoded
            previous_time = now
            if scope is None and terms is None:
                scope = observation["scope"]
            preview.need(isinstance(scope, str) and scope and observation["scope"] == scope, "SCOPE_CHANGED")
            stop_values = tuple(observation[k] for k in ("prior_block_active", "floor_halt", "daily_stop"))
            preview.need(all(type(value) is bool for value in stop_values), "UNKNOWN_PRIOR_BLOCK")
            latched = latched or any(stop_values)
            visible = visible_history(history, now)
            if not latched:
                steps += path_steps(model, visible)
                preview.need(steps <= 2_000_000, "REPLAY_SIMULATION_BUDGET")
            prior = str(current) if current is not None else "0"
            snapshot_terms = None if terms is None else {**terms, "current_y": prior if current is not None else None}
            snapshot = preview.evaluate({"schema": preview.SCHEMA, "terms": snapshot_terms, "model": model,
                                         "history": visible, "observation": {**observation, "prior_block_active": latched}})
            latched = latched or snapshot.get("new_buys_blocked", False) or snapshot["quote_state"] == "UNKNOWN"
            target = snapshot["candidate_next_y"]
            transition = "KEEP"
            confirmed_sequence = None
            feature_end = visible["bars"][-1]["end"] if visible and visible["bars"] else None
            if target is not None and not latched and snapshot["quote_state"] == "NO_STALE_BID_GAP":
                candidate = preview.bounds(target)
                preview.need(current is not None and candidate <= cap, "UNBOUND_CANDIDATE")
                if candidate < current:
                    current, pending, transition = candidate, None, "TIGHTEN_FOR_NEXT"
                elif candidate > current and snapshot.get("direction") == "up":
                    if pending and pending["target"] == candidate and now < pending["expires"]:
                        confirmed_sequence = pending["sequence"]
                        current, pending, transition = candidate, None, "WIDEN_FOR_NEXT"
                    else:
                        # Independent confirmation is meaningful only while the first forecast is live.
                        expires = feature_end + model["horizon"] * model["step_seconds"]
                        if now < expires:
                            pending = {"target": candidate, "expires": expires, "sequence": sequence}
                            transition = "AWAIT_WIDEN_CONFIRMATION"
                        else:
                            pending, transition = None, "FORECAST_EXPIRED"
                else:
                    pending = None
            else:
                pending = None
            rows.append({
                "sequence": sequence, "as_of": now, "used_y": prior, "quote_state": snapshot["quote_state"],
                "snapshot_status": snapshot["status"], "snapshot_reason": snapshot["reason"], "candidate_next_y": target, "transition": transition,
                "next_y": str(current) if current is not None else "0", "entry_block_latched": latched,
                "feature_cutoff": feature_end, "confirmed_sequence": confirmed_sequence,
                "model_sha256": snapshot.get("model_sha256"), "probabilities": snapshot.get("probabilities"),
                "holdout": snapshot.get("holdout"),
            })
        return {**result, "status": "REPLAYED", "events": rows, "entry_block_latched": latched,
                "final_working_y": rows[-1]["next_y"], "duplicates_ignored": len(observations) - len(rows)}
    except (preview.Invalid, KeyError, ValueError, TypeError, ArithmeticError, RecursionError) as error:
        return {**result, "status": "REJECTED", "reason": str(error) if type(error) is preview.Invalid else "INVALID_REPLAY",
                "events": [], "entry_block_latched": True, "final_working_y": None}


def example():
    first = preview.example()
    bars = first["history"]["bars"]
    observations = []
    for i in range(3):
        if i:
            bar = bars[-1]
            step = first["model"]["step_seconds"]
            bars.append({**bar, "end": bar["end"] + step, "known_at": bar["known_at"] + step})
        now = bars[-1]["end"] + 1
        observations.append({**first["observation"], "sequence": i + 1, "as_of": now, "last_trade_at": now - 45,
                             "bid_at": now, "floor_halt": False, "daily_stop": False})
    return {"schema": SCHEMA, "model": first["model"], "terms": first["terms"],
            "history": first["history"], "observations": observations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--example", action="store_true", help="print a synthetic three-observation series")
    source.add_argument("--input", type=Path, help="explicit replay JSON file")
    args = parser.parse_args()
    try:
        report = example() if args.example else replay(preview.read_input(args.input))
    except (preview.Invalid, ValueError, OSError, RecursionError):
        parser.exit(2, "Could not read valid replay input.\n")
    print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
    if report.get("status") == "REJECTED":
        parser.exit(2)


if __name__ == "__main__":
    main()
