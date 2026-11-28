"""Stage 1 evaluator for the Section-12 direction model study.

Research only. Implements S4 & S1 pre-checks (VOID), --mode interim S2 futility check
(STOPPED), Criterion 1 gate with bit-identical counting parity to direction_forecast_adapter,
S3 (INCONCLUSIVE), Criterion 2 conditional up-vs-down log-loss with 24-bar KST-day
cluster-weighted block bootstrap (10,000 replications, PCG64) vs B1 + point check vs B0,
Criterion 4 half-window stability, and B2 moving-block report (like_for_like_with_m=False).
Zero imports from core.compliance, core.odds, execution*, tools.owner, config, or main.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tools.research import adaptive_bid_gap_preview as preview
from tools.research import direction_feature_builder as dfb
from tools.research import direction_forecast_adapter as adapter
from tools.research._study_common import (
    DEFAULT_MAX_BYTES,
    RESEARCH_FLAGS,
    StudyError,
    atomic_publish_json_ascii,
    canonical_ascii_str,
    parse_decimal_str,
    parse_epoch_int,
    read_strict_json_file,
    require,
    sha256_ascii,
)


STAGE1_REPORT_FORMAT = "tradegen-direction-stage1-report-v1"
DEFAULT_Z95 = 1.959963984540054


def wilson_lower_z(successes: int, total: int, z: float = DEFAULT_Z95) -> float:
    if not total:
        return 0.0
    if z == DEFAULT_Z95:
        return preview.wilson_lower(successes, total)
    p = successes / total
    margin = z * math.sqrt(p * (1.0 - p) / total + (z ** 2) / (4.0 * (total ** 2)))
    return (p + (z ** 2) / (2.0 * total) - margin) / (1.0 + (z ** 2) / total)


def family_wise_false_pass_chance(judged_attempts: int, z: float = DEFAULT_Z95) -> float:
    """Section 6 approximate family-wise false-pass chance across judged 2-direction attempts."""
    if judged_attempts <= 0:
        return 0.0
    # Normal tail P(Z > z) per direction, two directions per attempt
    one_tail = 0.5 * math.erfc(z / math.sqrt(2.0))
    per_attempt = 1.0 - (1.0 - one_tail) ** 2
    return 1.0 - (1.0 - per_attempt) ** judged_attempts


def _merge_with_receipts(
    snapshots: Sequence[Mapping[str, Any]],
    receipt_times: Sequence[int | None] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Merge snapshots identically to adapter.merge while tracking effective issued_at = max(issued_at, receipt_at)."""
    model, _merged = adapter.merge(list(snapshots))
    eff_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    for idx, snap in enumerate(snapshots):
        rec_at = None if receipt_times is None else receipt_times[idx]
        if rec_at is not None:
            parse_epoch_int(rec_at, error_code="INVALID_RECEIPT_TIME")
        for f in snap["forecasts"]:
            key = (f["market"], f["as_of"], f["horizon_seconds"])
            eff_issued = int(f["issued_at"]) if rec_at is None else max(int(f["issued_at"]), int(rec_at))
            if key not in eff_by_key:
                eff_by_key[key] = {**f, "_effective_issued_at": eff_issued}
            else:
                eff_by_key[key]["_effective_issued_at"] = min(eff_by_key[key]["_effective_issued_at"], eff_issued)
    return model, list(eff_by_key.values())


def _score_criterion1_like_adapter(
    *,
    forecasts: Sequence[Mapping[str, Any]],
    first_bar_end: int,
    returns: Sequence[float],
    known_times: Sequence[int],
    market: str,
    step_seconds: int,
    horizon_seconds: int,
    hurdle_bps: int,
    evaluation_start: int,
    window_end: int,
    evaluated_at: int,
    confidence_str: str,
    min_validation_calls: int,
    max_calibration_gap_str: str,
    z_value: float = DEFAULT_Z95,
    midpoint_as_of: int | None = None,
) -> dict[str, Any]:
    """Reproduce direction_forecast_adapter's exact non-overlapping Criterion 1 counting."""
    usable = sorted(
        (
            f for f in forecasts
            if f["market"] == market
            and f["horizon_seconds"] == horizon_seconds
            and f["hurdle_bps"] == hurdle_bps
            and f["as_of"] >= evaluation_start
            and f["as_of"] + horizon_seconds <= window_end
            and int(f.get("_effective_issued_at", f["issued_at"])) < evaluated_at
        ),
        key=lambda f: (f["as_of"], int(f.get("_effective_issued_at", f["issued_at"]))),
    )
    if not all((f["as_of"] - first_bar_end) % step_seconds == 0 for f in usable):
        raise preview.Invalid("FORECAST_OFF_BAR_GRID")

    threshold = float(parse_decimal_str(confidence_str, Decimal("0.5"), Decimal("1"), inclusive_low=False))
    max_gap = float(parse_decimal_str(max_calibration_gap_str, Decimal("0"), Decimal("1")))
    cfg_for_called = {"confidence": confidence_str}

    up_bar = math.log1p(hurdle_bps / 10000.0)
    down_bar = math.log1p(-hurdle_bps / 10000.0)

    stats = {d: {"calls": 0, "hits": 0, "prob_sum": 0.0} for d in ("up", "down")}
    half_stats = {
        "half1": {d: {"calls": 0, "hits": 0} for d in ("up", "down")},
        "half2": {d: {"calls": 0, "hits": 0} for d in ("up", "down")},
    }
    last: int | None = None
    windows = 0

    for forecast in usable:
        if last is not None and forecast["as_of"] < last + horizon_seconds:
            continue
        last = forecast["as_of"]
        start = (forecast["as_of"] - first_bar_end) // step_seconds + 1
        stop = (forecast["as_of"] + horizon_seconds - first_bar_end) // step_seconds
        if stop >= len(returns) or max(known_times[start:stop + 1]) >= evaluated_at:
            continue
        windows += 1
        direction = adapter.called(forecast, cfg_for_called)
        if direction:
            realized = math.fsum(returns[start:stop + 1])
            hit = int(realized > up_bar if direction == "up" else realized < down_bar)
            values = stats[direction]
            values["calls"] += 1
            values["hits"] += hit
            values["prob_sum"] += float(forecast["probabilities"][direction])
            if midpoint_as_of is not None:
                h_key = "half1" if forecast["as_of"] < midpoint_as_of else "half2"
                half_stats[h_key][direction]["calls"] += 1
                half_stats[h_key][direction]["hits"] += hit

    per_dir: dict[str, Any] = {}
    for d in ("up", "down"):
        calls = stats[d]["calls"]
        hits = stats[d]["hits"]
        lower = wilson_lower_z(hits, calls, z=z_value)
        gap = abs((stats[d]["prob_sum"] - hits) / calls) if calls else None
        passed = bool(
            calls >= min_validation_calls
            and lower >= threshold
            and gap is not None
            and gap <= max_gap
        )
        h1_c, h1_h = half_stats["half1"][d]["calls"], half_stats["half1"][d]["hits"]
        h2_c, h2_h = half_stats["half2"][d]["calls"], half_stats["half2"][d]["hits"]
        h1_rate = (h1_h / h1_c) if h1_c > 0 else None
        h2_rate = (h2_h / h2_c) if h2_c > 0 else None
        per_dir[d] = {
            "direction": d,
            "calls": calls,
            "hits": hits,
            "hit_rate": (hits / calls) if calls else None,
            "hit_lower_95": lower,
            "directional_calibration_gap": gap,
            "passed_criterion1": passed,
            "half1": {"calls": h1_c, "hits": h1_h, "hit_rate": h1_rate},
            "half2": {"calls": h2_c, "hits": h2_h, "hit_rate": h2_rate},
            "passed_criterion4_hit_rate": bool(
                h1_rate is not None and h1_rate >= threshold
                and h2_rate is not None and h2_rate >= threshold
            ),
        }

    return {
        "nonoverlap_forecasts": windows,
        "directions": per_dir,
    }


def _cond_up_down_logloss(forecast: Mapping[str, Any], outcome: str) -> float:
    p_up = float(forecast["probabilities"]["up"])
    p_down = float(forecast["probabilities"]["down"])
    denom = p_up + p_down
    q_up = (p_up / denom) if denom > 0.0 else 0.5
    q_up = max(1e-12, min(1.0 - 1e-12, q_up))
    return -math.log(q_up) if outcome == "up" else -math.log(1.0 - q_up)


def _three_class_logloss(forecast: Mapping[str, Any], outcome: str) -> float:
    p = max(1e-12, min(1.0, float(forecast["probabilities"][outcome])))
    return -math.log(p)


def _compute_criterion2_and_half_logloss(
    *,
    m_forecasts: Sequence[Mapping[str, Any]],
    b1_forecasts: Sequence[Mapping[str, Any]],
    b0_forecasts: Sequence[Mapping[str, Any]] | None,
    first_bar_end: int,
    returns: Sequence[float],
    known_times: Sequence[int],
    market: str,
    step_seconds: int,
    horizon_seconds: int,
    hurdle_bps: int,
    evaluation_start: int,
    window_end: int,
    evaluated_at: int,
    midpoint_as_of: int,
    criterion2_margin: float,
    bootstrap_replications: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    """Criterion 2 conditional up-vs-down log-loss + 24-bar KST-day block bootstrap + half-window point check."""
    def index_by_as_of(f_list: Sequence[Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
        out: dict[int, Mapping[str, Any]] = {}
        for f in f_list:
            if (
                f["market"] == market
                and f["horizon_seconds"] == horizon_seconds
                and f["hurdle_bps"] == hurdle_bps
                and evaluation_start <= f["as_of"]
                and f["as_of"] + horizon_seconds <= window_end
                and int(f.get("_effective_issued_at", f["issued_at"])) < evaluated_at
            ):
                out[int(f["as_of"])] = f
        return out

    m_map = index_by_as_of(m_forecasts)
    b1_map = index_by_as_of(b1_forecasts)
    b0_map = index_by_as_of(b0_forecasts) if b0_forecasts is not None else None
    common_as_of = sorted(set(m_map) & set(b1_map))

    up_bar = math.log1p(hurdle_bps / 10000.0)
    down_bar = math.log1p(-hurdle_bps / 10000.0)

    all_3class_m: list[float] = []
    all_3class_b1: list[float] = []
    non_neutral_rows: list[dict[str, Any]] = []

    for as_of in common_as_of:
        start = (as_of - first_bar_end) // step_seconds + 1
        stop = (as_of + horizon_seconds - first_bar_end) // step_seconds
        if stop >= len(returns) or max(known_times[start:stop + 1]) >= evaluated_at:
            continue
        realized = math.fsum(returns[start:stop + 1])
        outcome = "up" if realized > up_bar else ("down" if realized < down_bar else "neutral")

        fm, fb1 = m_map[as_of], b1_map[as_of]
        all_3class_m.append(_three_class_logloss(fm, outcome))
        all_3class_b1.append(_three_class_logloss(fb1, outcome))

        if outcome != "neutral":
            loss_m = _cond_up_down_logloss(fm, outcome)
            loss_b1 = _cond_up_down_logloss(fb1, outcome)
            loss_b0 = _cond_up_down_logloss(b0_map[as_of], outcome) if (b0_map is not None and as_of in b0_map) else None
            # KST day block: 24 hourly bar closes per KST calendar day [00:00 KST, 24:00 KST)
            kst_block_id = (as_of + 9 * 3600) // 86400
            non_neutral_rows.append({
                "as_of": as_of,
                "kst_block": kst_block_id,
                "loss_m": loss_m,
                "loss_b1": loss_b1,
                "loss_b0": loss_b0,
                "diff_b1_minus_m": loss_b1 - loss_m,
            })

    # Group all common bar closes into KST-day blocks (including blocks that had 0 non-neutral outcomes)
    all_kst_blocks = sorted({(as_of + 9 * 3600) // 86400 for as_of in common_as_of})
    if not non_neutral_rows or not all_kst_blocks:
        return {
            "common_window_count": len(all_3class_m),
            "non_neutral_window_count": 0,
            "mean_up_down_logloss_M": None,
            "mean_up_down_logloss_B1": None,
            "mean_up_down_logloss_B0": None,
            "mean_improvement_over_B1": None,
            "bootstrap_95_lower_bound": None,
            "bootstrap_95_upper_bound": None,
            "passed_criterion2": False,
            "passed_criterion4_logloss": False,
            "half1_logloss": {"M": None, "B1": None},
            "half2_logloss": {"M": None, "B1": None},
            "three_class_logloss": {
                "M": (math.fsum(all_3class_m) / len(all_3class_m)) if all_3class_m else None,
                "B1": (math.fsum(all_3class_b1) / len(all_3class_b1)) if all_3class_b1 else None,
            },
        }

    n_nn = len(non_neutral_rows)
    mean_m = math.fsum(r["loss_m"] for r in non_neutral_rows) / n_nn
    mean_b1 = math.fsum(r["loss_b1"] for r in non_neutral_rows) / n_nn
    mean_diff = mean_b1 - mean_m

    b0_vals = [float(r["loss_b0"]) for r in non_neutral_rows if r["loss_b0"] is not None]
    mean_b0 = (math.fsum(b0_vals) / len(b0_vals)) if len(b0_vals) == n_nn else None

    block_map = {bid: idx for idx, bid in enumerate(all_kst_blocks)}
    n_blocks = len(all_kst_blocks)
    block_sums = np.zeros(n_blocks, dtype=np.float64)
    block_counts = np.zeros(n_blocks, dtype=np.float64)
    for r in non_neutral_rows:
        b_idx = block_map[r["kst_block"]]
        block_sums[b_idx] += float(r["diff_b1_minus_m"])
        block_counts[b_idx] += 1.0

    rng = np.random.Generator(np.random.PCG64(int(bootstrap_seed)))
    draws = rng.integers(0, n_blocks, size=(int(bootstrap_replications), n_blocks))
    sampled_sums = np.sum(block_sums[draws], axis=1)
    sampled_counts = np.sum(block_counts[draws], axis=1)
    valid_mask = sampled_counts > 0
    boot_deltas = sampled_sums[valid_mask] / sampled_counts[valid_mask]

    lower_95 = float(np.percentile(boot_deltas, 5.0)) if boot_deltas.size else -math.inf
    upper_95 = float(np.percentile(boot_deltas, 95.0)) if boot_deltas.size else -math.inf

    h1_rows = [r for r in non_neutral_rows if r["as_of"] < midpoint_as_of]
    h2_rows = [r for r in non_neutral_rows if r["as_of"] >= midpoint_as_of]
    h1_m = (math.fsum(r["loss_m"] for r in h1_rows) / len(h1_rows)) if h1_rows else None
    h1_b1 = (math.fsum(r["loss_b1"] for r in h1_rows) / len(h1_rows)) if h1_rows else None
    h2_m = (math.fsum(r["loss_m"] for r in h2_rows) / len(h2_rows)) if h2_rows else None
    h2_b1 = (math.fsum(r["loss_b1"] for r in h2_rows) / len(h2_rows)) if h2_rows else None

    b0_ok = True if mean_b0 is None else (mean_m < mean_b0)
    passed_c2 = bool(lower_95 > criterion2_margin and b0_ok)
    passed_c4_ll = bool(
        h1_m is not None and h1_b1 is not None and h1_m < h1_b1
        and h2_m is not None and h2_b1 is not None and h2_m < h2_b1
    )

    return {
        "common_window_count": len(all_3class_m),
        "non_neutral_window_count": n_nn,
        "kst_day_block_count": n_blocks,
        "bootstrap_replications": int(bootstrap_replications),
        "mean_up_down_logloss_M": mean_m,
        "mean_up_down_logloss_B1": mean_b1,
        "mean_up_down_logloss_B0": mean_b0,
        "mean_improvement_over_B1": mean_diff,
        "bootstrap_95_lower_bound": lower_95,
        "bootstrap_95_upper_bound": upper_95,
        "criterion2_margin": criterion2_margin,
        "beats_B0_point_estimate": b0_ok,
        "passed_criterion2": passed_c2,
        "passed_criterion4_logloss": passed_c4_ll,
        "half1_logloss": {"M": h1_m, "B1": h1_b1},
        "half2_logloss": {"M": h2_m, "B1": h2_b1},
        "three_class_logloss": {
            "M": (math.fsum(all_3class_m) / len(all_3class_m)) if all_3class_m else None,
            "B1": (math.fsum(all_3class_b1) / len(all_3class_b1)) if all_3class_b1 else None,
        },
    }


def _compute_b2_report(
    *,
    bars: Sequence[Mapping[str, Any]],
    study: Mapping[str, Any],
    evaluated_at: int,
) -> dict[str, Any]:
    """Section 5 B2 moving-block Criterion 1 report (explicitly like_for_like_with_m=False)."""
    step = int(study["step_seconds"])
    horizon_bars = int(study["horizon_seconds"]) // step
    lookback = int(study.get("b2_lookback", 24))
    block = int(study.get("b2_block", 2))
    paths = int(study.get("b2_paths", 1000))
    seed = int(study.get("b2_seed", 42))

    tail_bars = list(bars[-1024:])
    if len(tail_bars) < lookback + horizon_bars * int(study["min_validation_calls"]):
        return {
            "available": False,
            "like_for_like_with_m": False,
            "reason": "INSUFFICIENT_BARS_FOR_B2_MIN_CALLS",
        }

    # Ensure now is within 1 step of last bar end as moving-block's STALE_FEATURES check requires
    b2_now = max(tail_bars[-1]["end"] + 1, max(int(b["known_at"]) for b in tail_bars) + 1)
    if b2_now - tail_bars[-1]["end"] > step:
        return {
            "available": False,
            "like_for_like_with_m": False,
            "reason": "STALE_FEATURES_AT_B2_END",
        }

    b2_model = {
        "scope": study["scope"],
        "source_id": study["source_id"],
        "first_validation_origin": tail_bars[lookback - 1]["end"],
        "rule_version": "moving-block-v1",
        "frozen_at": min(int(study["evaluation_start"]) - 1, tail_bars[lookback - 1]["end"] - 1),
        "step_seconds": step,
        "lookback": lookback,
        "block": block,
        "horizon": horizon_bars,
        "paths": paths,
        "seed": seed,
        "cost_bps": int(study["hurdle_bps"]),
        "confidence": str(study["confidence"]),
        "min_validation_calls": int(study["min_validation_calls"]),
        "max_calibration_gap": str(study["max_calibration_gap"]),
        "up_y": str(study["up_y"]),
        "down_y": str(study["down_y"]),
    }
    try:
        cap = preview.bounds(str(study.get("ceiling_y", "0.05")))
        cfg = preview.validate_model(b2_model, cap)
        _current, stats, folds = preview.reviewed_counts({"bars": tail_bars}, cfg, b2_now)
    except preview.Invalid as exc:
        return {
            "available": False,
            "like_for_like_with_m": False,
            "reason": str(exc),
        }

    directions_out = {}
    for d in ("up", "down"):
        calls, hits = stats[d]["calls"], stats[d]["hits"]
        lower = preview.wilson_lower(hits, calls)
        gap = abs((stats[d]["prob_sum"] - hits) / calls) if calls else None
        directions_out[d] = {
            "calls": calls,
            "hits": hits,
            "hit_lower_95": lower,
            "directional_calibration_gap": gap,
            "passed_criterion1": bool(
                calls >= cfg["min_validation_calls"]
                and lower >= cfg["threshold"]
                and gap is not None
                and gap <= cfg["max_gap"]
            ),
        }
    return {
        "available": True,
        "like_for_like_with_m": False,
        "nonoverlap_folds": folds,
        "directions": directions_out,
    }


def evaluate_stage1(
    *,
    study: Mapping[str, Any],
    history: Mapping[str, Any],
    m_snapshots: Sequence[Mapping[str, Any]],
    b1_snapshots: Sequence[Mapping[str, Any]],
    b0_snapshots: Sequence[Mapping[str, Any]] | None = None,
    m_receipt_times: Sequence[int | None] | None = None,
    b1_receipt_times: Sequence[int | None] | None = None,
    b0_receipt_times: Sequence[int | None] | None = None,
    feature_table: Mapping[str, Any] | None = None,
    mode: str = "final",
    evaluated_at: int | None = None,
) -> dict[str, Any]:
    """Run Stage 1 evaluation (--mode interim | final) and return deterministic Stage 1 report."""
    require(mode in ("interim", "final"), "INVALID_EVALUATION_MODE")
    eval_start = parse_epoch_int(study["evaluation_start"], error_code="INVALID_EVALUATION_WINDOW")
    eval_end = parse_epoch_int(study["evaluation_end"], low=eval_start + 1, error_code="INVALID_EVALUATION_WINDOW")
    interim_at = int(study.get("interim_at", eval_start + (eval_end - eval_start) // 2))
    window_end = interim_at if mode == "interim" else eval_end
    midpoint = eval_start + (eval_end - eval_start) // 2

    step = int(study["step_seconds"])
    horizon = int(study["horizon_seconds"])
    hurdle_bps = int(study["hurdle_bps"])
    market = str(study["market"])
    min_calls = int(study["min_validation_calls"])
    conf_str = str(study["confidence"])
    max_gap_str = str(study["max_calibration_gap"])
    c2_margin = float(study.get("criterion2_margin", 0.0))
    boot_reps = int(study.get("bootstrap_replications", 10_000))
    boot_seed = int(study.get("bootstrap_seed", 20261124))
    z_val = float(study.get("z_value", DEFAULT_Z95))
    attempt_num = int(study.get("attempt_number", 1))
    attempt_budget = int(study.get("attempt_budget", 3))

    def finish(outcome: str, stop_rule: str | None, reason: str | None = None, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
        judged_attempts = attempt_num if outcome in ("PASS", "NOT SHOWN") else max(0, attempt_num - 1)
        rep = {
            "format": STAGE1_REPORT_FORMAT,
            **RESEARCH_FLAGS,
            "mode": mode,
            "outcome": outcome,
            "stop_rule": stop_rule,
            "reason": reason,
            "market": market,
            "evaluation_start": eval_start,
            "evaluation_end": eval_end,
            "window_end_evaluated": window_end,
            "attempt_number": attempt_num,
            "attempt_budget": attempt_budget,
            "family_wise_false_pass_chance": round(family_wise_false_pass_chance(judged_attempts, z=z_val), 6),
            "passing_directions": [],
            "b1_passing_directions": [],
            **(dict(extra) if extra else {}),
        }
        rep["report_sha256"] = sha256_ascii(rep)
        return rep

    # S4 check on study & feature definitions
    if feature_table is not None:
        if feature_table.get("market") != market or int(feature_table.get("step_seconds", -1)) != step:
            return finish("STOPPED", "S4", "S4_FEATURE_TABLE_MISMATCH")
        if "pinned_upstream_identities" in study and study["pinned_upstream_identities"] is not None:
            if feature_table.get("upstream_identities") != study["pinned_upstream_identities"]:
                return finish("STOPPED", "S4", "S4_UPSTREAM_IDENTITY_CHANGED")

    # Merge & S1 / S4 check on snapshots
    try:
        m_model, m_forecasts = _merge_with_receipts(m_snapshots, m_receipt_times)
        b1_model, b1_forecasts = _merge_with_receipts(b1_snapshots, b1_receipt_times)
        b0_forecasts: list[dict[str, Any]] | None = None
        if b0_snapshots:
            b0_model, b0_forecasts = _merge_with_receipts(b0_snapshots, b0_receipt_times)
            if "b0_forecast_model" in study and study["b0_forecast_model"] is not None:
                if {k: b0_model[k] for k in ("name", "version", "sha256")} != study["b0_forecast_model"]:
                    return finish("STOPPED", "S4", "S4_B0_MODEL_NOT_PINNED")
    except (preview.Invalid, StudyError, KeyError, TypeError, ValueError) as exc:
        return finish("VOID", "S1", str(exc) if isinstance(exc, (preview.Invalid, StudyError)) else "S1_INVALID_SNAPSHOT")

    pinned_m = {k: m_model[k] for k in ("name", "version", "sha256")}
    if study.get("forecast_model") != pinned_m:
        return finish("STOPPED", "S4", "S4_M_MODEL_NOT_PINNED")
    if "b1_forecast_model" in study and study["b1_forecast_model"] is not None:
        pinned_b1 = {k: b1_model[k] for k in ("name", "version", "sha256")}
        if study["b1_forecast_model"] != pinned_b1:
            return finish("STOPPED", "S4", "S4_B1_MODEL_NOT_PINNED")
    if int(m_model["frozen_at"]) >= eval_start or int(b1_model["frozen_at"]) >= eval_start:
        return finish("STOPPED", "S4", "MODEL_NOT_FROZEN_BEFORE_EVALUATION")

    # Validate contiguous price history (<= 1024 bars) -> S1 on any gap/defect
    bars = history.get("bars") if isinstance(history, Mapping) else None
    if type(bars) is not list or not 1 <= len(bars) <= 1024:
        return finish("VOID", "S1", "HISTORY_SIZE")

    max_bar_known = max((int(b.get("known_at", 0)) for b in bars if isinstance(b, Mapping)), default=0)
    max_f_issued = max(
        [int(f.get("_effective_issued_at", f["issued_at"])) for f in (*m_forecasts, *b1_forecasts)],
        default=window_end,
    )
    eff_now = evaluated_at if evaluated_at is not None else max(window_end, max_bar_known, max_f_issued) + 1

    try:
        first_end, returns = adapter.price_record({"bars": bars}, step, eff_now)
    except (preview.Invalid, KeyError, TypeError, ValueError) as exc:
        return finish("VOID", "S1", str(exc) if type(exc) is preview.Invalid else "S1_INVALID_BAR_HISTORY")

    known_times = [int(b["known_at"]) for b in bars]
    if first_end > eval_start or bars[-1]["end"] < window_end:
        return finish("VOID", "S1", "HISTORY_DOES_NOT_COVER_EVALUATION_WINDOW")

    # S1 <= 5% missing-feature check over [evaluation_start, window_end - horizon_seconds]
    missing_feature_rate: float | None = None
    if feature_table is not None:
        win_rows = [
            r for r in feature_table["rows"]
            if eval_start <= int(r["as_of"]) and int(r["as_of"]) + horizon <= window_end
        ]
        if win_rows:
            n_miss = sum(1 for r in win_rows if not r["complete"])
            missing_feature_rate = n_miss / float(len(win_rows))
            if missing_feature_rate > 0.05 + 1e-12:
                return finish("VOID", "S1", "S1_MISSING_FEATURES_EXCEED_5PCT", {"missing_feature_rate": missing_feature_rate})

    try:
        c1_m = _score_criterion1_like_adapter(
            forecasts=m_forecasts,
            first_bar_end=first_end,
            returns=returns,
            known_times=known_times,
            market=market,
            step_seconds=step,
            horizon_seconds=horizon,
            hurdle_bps=hurdle_bps,
            evaluation_start=eval_start,
            window_end=window_end,
            evaluated_at=eff_now,
            confidence_str=conf_str,
            min_validation_calls=min_calls,
            max_calibration_gap_str=max_gap_str,
            z_value=z_val,
            midpoint_as_of=midpoint,
        )
        c1_b1 = _score_criterion1_like_adapter(
            forecasts=b1_forecasts,
            first_bar_end=first_end,
            returns=returns,
            known_times=known_times,
            market=market,
            step_seconds=step,
            horizon_seconds=horizon,
            hurdle_bps=hurdle_bps,
            evaluation_start=eval_start,
            window_end=window_end,
            evaluated_at=eff_now,
            confidence_str=conf_str,
            min_validation_calls=min_calls,
            max_calibration_gap_str=max_gap_str,
            z_value=z_val,
            midpoint_as_of=midpoint,
        )
    except preview.Invalid as exc:
        return finish("VOID", "S1", str(exc))

    c2 = _compute_criterion2_and_half_logloss(
        m_forecasts=m_forecasts,
        b1_forecasts=b1_forecasts,
        b0_forecasts=b0_forecasts,
        first_bar_end=first_end,
        returns=returns,
        known_times=known_times,
        market=market,
        step_seconds=step,
        horizon_seconds=horizon,
        hurdle_bps=hurdle_bps,
        evaluation_start=eval_start,
        window_end=window_end,
        evaluated_at=eff_now,
        midpoint_as_of=midpoint,
        criterion2_margin=c2_margin,
        bootstrap_replications=boot_reps,
        bootstrap_seed=boot_seed,
    )

    if mode == "interim":
        upper = c2["bootstrap_95_upper_bound"]
        if upper is not None and upper <= 0.0:
            return finish(
                "STOPPED",
                "S2",
                "S2_INTERIM_FUTILITY",
                {"criterion1_M": c1_m, "criterion2": c2, "missing_feature_rate": missing_feature_rate},
            )
        return finish(
            "CONTINUE",
            None,
            "INTERIM_NOT_FUTILE",
            {"criterion1_M": c1_m, "criterion2": c2, "missing_feature_rate": missing_feature_rate},
        )

    b2_rep = _compute_b2_report(bars=bars, study=study, evaluated_at=eff_now)
    details = {
        "missing_feature_rate": missing_feature_rate,
        "criterion1_M": c1_m,
        "criterion1_B1": c1_b1,
        "criterion2": c2,
        "b2_report": b2_rep,
    }

    max_m_calls = max(c1_m["directions"]["up"]["calls"], c1_m["directions"]["down"]["calls"])
    if max_m_calls < min_calls:
        return finish("INCONCLUSIVE", "S3", "S3_INSUFFICIENT_CALLS", details)

    b1_passing_dirs = [
        d for d in ("up", "down")
        if c1_b1["directions"][d]["passed_criterion1"]
    ]
    m_passing_dirs = []
    if c2["passed_criterion2"] and c2["passed_criterion4_logloss"]:
        for d in ("up", "down"):
            d_info = c1_m["directions"][d]
            if d_info["passed_criterion1"] and d_info["passed_criterion4_hit_rate"]:
                m_passing_dirs.append(d)

    details["b1_passing_directions"] = b1_passing_dirs
    details["passing_directions"] = m_passing_dirs
    if m_passing_dirs:
        return finish("PASS", None, "STAGE1_CRITERIA_MET", details)
    return finish("NOT SHOWN", None, "NO_SKILL_SHOWN_AT_SAMPLE_SIZE", details)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True, help="M11-T4 Stage 1 study config JSON")
    parser.add_argument("--history", type=Path, required=True, help="Frozen Stage 1 price history JSON")
    parser.add_argument("--m-snapshot", action="append", required=True, metavar="PATH=SHA256[@RECEIPT]")
    parser.add_argument("--b1-snapshot", action="append", required=True, metavar="PATH=SHA256[@RECEIPT]")
    parser.add_argument("--b0-snapshot", action="append", default=[], metavar="PATH=SHA256[@RECEIPT]")
    parser.add_argument("--features", type=Path, help="Optional feature table JSON for S1/S4 verification")
    parser.add_argument("--mode", choices=["interim", "final"], default="final")
    parser.add_argument("--output", type=Path, help="Optional atomic output report path")
    args = parser.parse_args(argv)

    def load_snaps(specs: Sequence[str]) -> tuple[list[dict[str, Any]], list[int | None]]:
        snaps: list[dict[str, Any]] = []
        recs: list[int | None] = []
        remaining = adapter.MAX_FORECASTS
        for spec in specs:
            lhs, sep, rhs = spec.rpartition("=")
            require(sep == "=", "SNAPSHOT_ARGUMENT")
            sha_part, at_sep, rec_part = rhs.partition("@")
            rec_ts = int(rec_part) if at_sep else None
            snap = adapter.read_snapshot(Path(lhs), sha_part, budget=remaining)
            remaining -= len(snap["forecasts"])
            snaps.append(snap)
            recs.append(rec_ts)
        return snaps, recs

    try:
        study_doc, _ = read_strict_json_file(args.study, max_bytes=DEFAULT_MAX_BYTES)
        hist_doc, _ = read_strict_json_file(args.history, max_bytes=DEFAULT_MAX_BYTES)
        m_snaps, m_recs = load_snaps(args.m_snapshot)
        b1_snaps, b1_recs = load_snaps(args.b1_snapshot)
        b0_snaps, b0_recs = load_snaps(args.b0_snapshot) if args.b0_snapshot else ([], [])
        ftable = dfb.read_feature_table(args.features) if args.features is not None else None

        report = evaluate_stage1(
            study=study_doc,
            history=hist_doc,
            m_snapshots=m_snaps,
            b1_snapshots=b1_snaps,
            b0_snapshots=b0_snaps or None,
            m_receipt_times=m_recs,
            b1_receipt_times=b1_recs,
            b0_receipt_times=b0_recs if b0_snaps else None,
            feature_table=ftable,
            mode=args.mode,
        )
        if args.output is not None:
            atomic_publish_json_ascii(args.output, report)
        print(canonical_ascii_str(report))
        return 0
    except (StudyError, preview.Invalid) as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError, KeyError):
        reason = "STAGE1_EVALUATION_REFUSED"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
