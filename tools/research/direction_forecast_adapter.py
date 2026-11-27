"""Offline BR-26 replay of external direction forecasts (tradegen-direction-forecast-v1). Research only.

Reads explicit local files. No network, model execution, credential, owner-log, signing or order API.
See docs/direction-forecast-contract.md.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import re
import stat

from tools.research import adaptive_bid_gap_preview as preview
from tools.research import adaptive_bid_gap_replay as replay_tool


FORMAT = "tradegen-direction-forecast-v1"
RULE = "external-forecast-v1"
MAX_BYTES = 16 * 1024 * 1024
MAX_FORECASTS = 50_000
RESEARCH_FLAGS = {"research_only": True, "live_eligible": False, "execution_ready": False,
                  "source_authenticated": False, "owner_approval_verified": False}
SNAPSHOT_KEYS = {"format", "producer", "model", "generated_at", "forecasts", "snapshot_sha256"}
MODEL_KEYS = {"name", "version", "sha256", "training_cutoff", "frozen_at"}
FORECAST_KEYS = {"market", "as_of", "issued_at", "horizon_seconds", "hurdle_bps", "probabilities", "direction"}
STUDY_KEYS = {"scope", "rule_version", "source_id", "market", "forecast_model", "evaluation_start", "step_seconds",
              "horizon_seconds", "hurdle_bps", "confidence", "min_validation_calls", "max_calibration_gap",
              "up_y", "down_y"}
CLASSES = ("up", "down", "neutral")
HEX64 = r"[0-9a-f]{64}"
MARKET = r"KRW-[A-Z0-9]{1,20}"
need, integer = preview.need, preview.integer


def matches(value, pattern, reason):
    need(type(value) is str and re.fullmatch(pattern, value), reason)
    return value


def moment(value):
    return integer(value, 0, 2**39)


def check_snapshot(snapshot):
    """Validate one snapshot against the contract. Any defect refuses the whole file."""
    need(type(snapshot) is dict and set(snapshot) == SNAPSHOT_KEYS and snapshot["format"] == FORMAT, "SNAPSHOT_FORMAT")
    matches(snapshot["producer"], r"[a-z0-9-]{1,64}", "SNAPSHOT_FORMAT")
    model = snapshot["model"]
    need(type(model) is dict and set(model) == MODEL_KEYS, "MODEL_FORMAT")
    need(all(type(model[k]) is str and 0 < len(model[k]) <= 128 for k in ("name", "version")), "MODEL_FORMAT")
    matches(model["sha256"], HEX64, "MODEL_FORMAT")
    need(moment(model["training_cutoff"]) <= moment(model["frozen_at"]), "MODEL_TIME_ORDER")
    generated = moment(snapshot["generated_at"])
    forecasts = snapshot["forecasts"]
    need(type(forecasts) is list and len(forecasts) <= MAX_FORECASTS, "SNAPSHOT_SIZE")
    for forecast in forecasts:
        need(type(forecast) is dict and set(forecast) == FORECAST_KEYS, "FORECAST_FORMAT")
        matches(forecast["market"], MARKET, "FORECAST_MARKET")
        need(moment(forecast["as_of"]) <= moment(forecast["issued_at"]) <= generated, "FORECAST_TIME_ORDER")
        integer(forecast["horizon_seconds"], 60, 2_592_000)
        integer(forecast["hurdle_bps"], 0, 9999)
        probabilities = forecast["probabilities"]
        need(type(probabilities) is dict and set(probabilities) == set(CLASSES), "FORECAST_FORMAT")
        values = {k: preview.fraction(probabilities[k], 0, 1) for k in CLASSES}
        need(sum(values.values()) == 1, "PROBABILITIES_NOT_ONE")
        top = max(values.values())
        need([k for k in CLASSES if values[k] == top] == [forecast["direction"]], "DIRECTION_NOT_ARGMAX")
    body = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    need(snapshot["snapshot_sha256"] == preview.model_id(body), "SNAPSHOT_SHA256_MISMATCH")
    return snapshot


def read_snapshot(path, expected_sha256, budget=None):
    """Read an explicit local snapshot whose SHA-256 the producer published in its interface note.

    budget is the number of forecasts the run may still read; it defaults to the whole run limit."""
    budget = MAX_FORECASTS if budget is None else budget
    matches(expected_sha256, HEX64, "SNAPSHOT_SHA256_MISMATCH")
    info = path.stat()
    need(path.suffix.lower() == ".json" and stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BYTES, "SNAPSHOT_FILE")
    with path.open("rb") as file:
        raw = file.read(MAX_BYTES + 1)
    need(len(raw) <= MAX_BYTES and not raw.startswith(b"\xef\xbb\xbf"), "SNAPSHOT_FILE")

    def unique(items):
        result = dict(items)
        need(len(result) == len(items), "DUPLICATE_JSON_KEY")
        return result

    def reject(_):
        raise preview.Invalid("NONFINITE_JSON_NUMBER")

    # A forecast has 2 objects, 10 keys and 9 separators. Counting the bytes bounds how many containers, keys and
    # values the parser can build; braces, colons or commas inside strings only make the count stricter.
    need(raw.count(b"{") + raw.count(b"[") <= 2 * budget + 1024 and raw.count(b":") <= 10 * budget + 1024
         and raw.count(b",") <= 9 * budget + 1024, "SNAPSHOT_SIZE")
    snapshot = check_snapshot(json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject))
    need(len(snapshot["forecasts"]) <= budget, "SNAPSHOT_SIZE")
    need(snapshot["snapshot_sha256"] == expected_sha256, "SNAPSHOT_SHA256_MISMATCH")
    return snapshot


def merge(snapshots):
    """Combine snapshots of one model version in receipt order. A revised forecast refuses the later file."""
    need(type(snapshots) is list and snapshots, "NO_SNAPSHOT")
    model, seen, total = None, {}, 0
    for snapshot in snapshots:
        check_snapshot(snapshot)
        total += len(snapshot["forecasts"])
        need(total <= MAX_FORECASTS, "SNAPSHOT_SIZE")   # across all files of one run
        need(model is None or snapshot["model"] == model, "MODEL_VERSION_MIXED")
        model = snapshot["model"]
        for forecast in snapshot["forecasts"]:
            key = (forecast["market"], forecast["as_of"], forecast["horizon_seconds"])
            need(seen.setdefault(key, forecast) == forecast, "FORECAST_REVISED")
    return model, list(seen.values())


def study_config(study, cap, forecast_model):
    """The study's preregistered terms, pinned by terms.model_sha256."""
    need(type(study) is dict and set(study) == STUDY_KEYS and study["rule_version"] == RULE, "MODEL_FORMAT")
    pinned = {k: forecast_model[k] for k in ("name", "version", "sha256")}
    need(study["forecast_model"] == pinned, "FORECAST_MODEL_NOT_PINNED")
    matches(study["market"], MARKET, "FORECAST_MARKET")
    need(type(study["source_id"]) is str and 0 < len(study["source_id"]) <= 140, "INVALID_SOURCE_ID")
    step = integer(study["step_seconds"], 1, 86400)
    horizon = integer(study["horizon_seconds"], 2 * step, 2_592_000)
    need(horizon % step == 0, "HORIZON_NOT_WHOLE_BARS")   # every outcome window is a run of whole bars
    integer(study["hurdle_bps"], 0, 9999)
    integer(study["min_validation_calls"], 1, 1000)
    need(forecast_model["frozen_at"] < moment(study["evaluation_start"]), "MODEL_NOT_FROZEN_BEFORE_EVALUATION")
    config = dict(study, threshold=float(preview.fraction(study["confidence"], Decimal("0.5"), 1, inclusive_low=False)),
                  max_gap=float(preview.fraction(study["max_calibration_gap"], 0, 1)))
    for key in ("up_y", "down_y"):
        config[key] = preview.bounds(study[key])
        need(config[key] <= cap, "MODEL_TARGET_OUTSIDE_ENVELOPE")
    return config


def price_record(history, step, now):
    """TRADEGEN's own contiguous bars known before now, as log returns."""
    bars = history["bars"]
    need(type(bars) is list and 0 < len(bars) <= 1024, "HISTORY_SIZE")
    first = integer(bars[0]["end"], 0, now - 1)
    returns = []
    for i, bar in enumerate(bars):
        end = integer(bar["end"], 0, now - 1)
        need(end == first + i * step, "MISSING_OR_DUPLICATE_BAR")
        integer(bar["known_at"], end, now - 1)
        returns.append(math.log1p(integer(bar["return_bps"], -9999, 100000) / 10000))
    return first, returns


def called(forecast, config):
    direction = forecast["direction"]
    if direction != "neutral" and Decimal(forecast["probabilities"][direction]) >= Decimal(config["confidence"]):
        return direction
    return None


def forecast_source(forecast_model, forecasts):
    """A preview direction source that reads merged snapshot forecasts instead of simulating."""
    def source(document, terms, scope, cap, now, out):
        study, history = document["model"], document["history"]
        need(terms["model_sha256"] is not None and preview.model_id(study) == terms["model_sha256"], "MODEL_NOT_BOUND")
        need(study["scope"] == scope == history["scope"], "MODEL_OR_HISTORY_SCOPE_MISMATCH")
        config = study_config(study, cap, forecast_model)
        out["model_sha256"] = terms["model_sha256"]
        need(history["source_id"] == config["source_id"], "EVIDENCE_SOURCE_MISMATCH")
        step, horizon = config["step_seconds"], config["horizon_seconds"]
        first, returns = price_record(history, step, now)
        need(first <= config["evaluation_start"], "HISTORY_BEFORE_EVALUATION_MISSING")
        # Visible from issued_at; in-sample and pre-window forecasts never count.
        usable = sorted((f for f in forecasts if f["market"] == config["market"] and f["horizon_seconds"] == horizon
                         and f["hurdle_bps"] == config["hurdle_bps"] and f["as_of"] >= config["evaluation_start"]
                         and f["issued_at"] <= now), key=lambda f: (f["as_of"], f["issued_at"]))
        # On the bar grid, a window's last bar ends at as_of + horizon, so it is scored only after the window.
        need(all((f["as_of"] - first) % step == 0 for f in usable), "FORECAST_OFF_BAR_GRID")
        up_bar, down_bar = math.log1p(config["hurdle_bps"] / 10000), math.log1p(-config["hurdle_bps"] / 10000)
        stats = {d: {"calls": 0, "hits": 0, "prob_sum": 0.0} for d in ("up", "down")}
        last, windows = None, 0
        for forecast in usable:   # earliest first, non-overlapping outcome windows only
            if last is not None and forecast["as_of"] < last + horizon:
                continue
            last = forecast["as_of"]
            start = (forecast["as_of"] - first) // step + 1   # first bar after as_of
            stop = (forecast["as_of"] + horizon - first) // step   # bar ending at as_of + horizon
            if stop >= len(returns):
                continue   # last bar not known before now, so the window has not ended before now
            windows += 1
            direction = called(forecast, config)
            if direction:
                realized = math.fsum(returns[start:stop + 1])
                values = stats[direction]
                values["calls"] += 1
                values["hits"] += int(realized > up_bar if direction == "up" else realized < down_bar)
                values["prob_sum"] += float(forecast["probabilities"][direction])
        out["nonoverlap_forecasts"] = windows
        live = [f for f in usable if now < f["as_of"] + horizon]
        if not live:
            out["reason"] = "NO_LIVE_FORECAST"
            return None
        current = max(live, key=lambda f: (f["issued_at"], f["as_of"]))
        out.update(forecast_as_of=current["as_of"], forecast_expires=current["as_of"] + horizon,
                   probabilities=current["probabilities"])
        direction = called(current, config)
        if not direction:
            out["reason"] = "MODEL_UNCERTAIN"
            return None
        return direction, stats, config
    return source


def run(document, snapshots):
    """Replay one study with external forecasts. Never an order, approval or signed input."""
    try:
        forecast_model, forecasts = merge(snapshots)
    except (preview.Invalid, KeyError, TypeError, ValueError, ArithmeticError) as error:
        return {"schema": replay_tool.SCHEMA, "status": "REJECTED", "events": [], "entry_block_latched": True,
                "final_working_y": None, **RESEARCH_FLAGS,
                "reason": str(error) if type(error) is preview.Invalid else "INVALID_SNAPSHOT"}
    report = replay_tool.replay(document, forecast_source(forecast_model, forecasts))
    return {**report, **RESEARCH_FLAGS, "forecast_model": forecast_model,
            "snapshot_sha256": [s["snapshot_sha256"] for s in snapshots]}


def example():
    """Synthetic hourly study and snapshot for tests. Not a model result or a suggested setting."""
    step, horizon, t0, scope = 3600, 7200, 1_700_000_000, "synthetic-upbit-krw-spot"
    bars = [{"end": t0 + step * i, "known_at": t0 + step * i + 30, "return_bps": 18 + i % 4} for i in range(200)]
    model = {"name": "synthetic-direction", "version": "0.0.1", "sha256": "ab" * 32,
             "training_cutoff": t0 + 4 * step, "frozen_at": t0 + 5 * step}
    forecasts = [{"market": "KRW-BTC", "as_of": bar["end"], "issued_at": bar["end"] + 60, "horizon_seconds": horizon,
                  "hurdle_bps": 10, "probabilities": {"up": "0.95", "down": "0.02", "neutral": "0.03"},
                  "direction": "up"} for bar in bars[10:]]
    snapshot = {"format": FORMAT, "producer": "synthetic", "model": model,
                "generated_at": forecasts[-1]["issued_at"], "forecasts": forecasts}
    snapshot["snapshot_sha256"] = preview.model_id(snapshot)
    study = {"scope": scope, "rule_version": RULE, "source_id": "synthetic-hourly-v1", "market": "KRW-BTC",
             "forecast_model": {k: model[k] for k in ("name", "version", "sha256")},
             "evaluation_start": t0 + 10 * step, "step_seconds": step, "horizon_seconds": horizon, "hurdle_bps": 10,
             "confidence": "0.75", "min_validation_calls": 16, "max_calibration_gap": "0.10",
             "up_y": "0.03", "down_y": "0.01"}
    observations = [{"sequence": i + 1, "as_of": now, "scope": scope, "last_trade_at": now - 45,
                     "last_trade": "10000", "bid_at": now, "bid": "9900", "prior_block_active": False,
                     "floor_halt": False, "daily_stop": False}
                    for i, now in enumerate((bars[-1]["end"] + 120, bars[-1]["end"] + 600))]
    document = {"schema": replay_tool.SCHEMA, "model": study, "observations": observations,
                "terms": {"scope": scope, "ceiling_y": "0.05", "current_y": "0.02", "model_sha256": preview.model_id(study)},
                "history": {"scope": scope, "source_id": study["source_id"], "bars": bars}}
    return document, snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, required=True, help="explicit replay study JSON file")
    parser.add_argument("--snapshot", action="append", required=True, metavar="PATH=SHA256",
                        help="snapshot file and the SHA-256 from the producer's interface note, in receipt order")
    args = parser.parse_args()
    try:
        snapshots = []
        for item in args.snapshot:
            path, separator, digest = item.rpartition("=")
            need(separator == "=", "SNAPSHOT_ARGUMENT")
            left = MAX_FORECASTS - sum(len(s["forecasts"]) for s in snapshots)   # checked before parsing the next file
            snapshots.append(read_snapshot(Path(path), digest, left))
        report = run(preview.read_input(args.replay), snapshots)
    except (preview.Invalid, OSError, ValueError, RecursionError) as error:
        parser.exit(2, "Refused: %s\n" % (error if type(error) is preview.Invalid else "UNREADABLE_INPUT"))
    print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
    if report["status"] == "REJECTED":
        parser.exit(2)


if __name__ == "__main__":
    main()
