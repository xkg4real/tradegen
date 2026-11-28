"""Fit and freeze multinomial logistic direction models (M, B1, B0) & M11-T4 call estimator.

Research only. Uses numpy and scipy pinned in constraints.txt; zero imports from
core.compliance, core.odds, execution*, tools.owner, config, or main.
Produces Regime A canonical tradegen-direction-model-v1 frozen artifacts.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_EVEN
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import minimize
from scipy.special import log_softmax

from tools.research import direction_feature_builder as dfb
from tools.research._study_common import (
    DEFAULT_MAX_BYTES,
    HEX40_RE,
    HEX64_RE,
    MARKET_RE,
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


MODEL_ARTIFACT_FORMAT = "tradegen-direction-model-v1"
FIT_REPORT_FORMAT = "tradegen-direction-fit-report-v1"
CLASSES = ("up", "down", "neutral")
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
PRICE_ONLY_FEATURES = ("P1", "P2", "P3", "P4")


# --------------------------------------------------------------------------- #
# Outcome Labeling & Probability Quantization (Exact Adapter/Writer Parity)
# --------------------------------------------------------------------------- #
def compute_outcome_label(
    bars_by_end: Mapping[int, Mapping[str, Any]],
    as_of: int,
    step_seconds: int,
    horizon_seconds: int,
    hurdle_bps: int,
    *,
    max_known_at: int | None = None,
) -> tuple[str, float]:
    """Compute ternary outcome ('up', 'down', 'neutral') identically to direction_forecast_adapter."""
    horizon_bars = horizon_seconds // step_seconds
    log_rets: list[float] = []
    for k in range(1, horizon_bars + 1):
        bar_end = as_of + k * step_seconds
        bar = bars_by_end.get(bar_end)
        require(bar is not None, "MISSING_OUTCOME_BAR")
        if max_known_at is not None:
            require(int(bar["known_at"]) <= max_known_at, "OUTCOME_BAR_KNOWN_AFTER_CUTOFF")
        log_rets.append(math.log1p(int(bar["return_bps"]) / 10000.0))

    realized = math.fsum(log_rets)
    up_bar = math.log1p(hurdle_bps / 10000.0)
    down_bar = math.log1p(-hurdle_bps / 10000.0)
    if realized > up_bar:
        return "up", realized
    if realized < down_bar:
        return "down", realized
    return "neutral", realized


def quantize_probabilities(p_up: float, p_down: float) -> tuple[dict[str, str], str] | None:
    """Section 5 probability quantization: 6-decimal ROUND_HALF_EVEN for up/down, neutral = 1 - up - down.

    Returns None when the highest class is tied after rounding (no forecast is written).
    """
    q_up = max(Decimal("0"), min(Decimal("1"), Decimal(repr(float(p_up))).quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)))
    q_down = max(Decimal("0"), min(Decimal("1"), Decimal(repr(float(p_down))).quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)))
    if q_up + q_down > Decimal("1.000000"):
        # Guard numerical edge if caller passed unnormalized floats
        q_down = Decimal("1.000000") - q_up
    q_neutral = Decimal("1.000000") - q_up - q_down
    dec_map = {"up": q_up, "down": q_down, "neutral": q_neutral}
    top = max(dec_map.values())
    winners = [c for c in CLASSES if dec_map[c] == top]
    if len(winners) != 1:
        return None
    str_map = {c: format(dec_map[c], "f") for c in CLASSES}
    return str_map, winners[0]


# --------------------------------------------------------------------------- #
# Convex L2-Penalized Multinomial Logistic Regression Solver
# --------------------------------------------------------------------------- #
def _fit_multinomial_l2(
    x_raw: np.ndarray,
    y_idx: np.ndarray,
    l2_penalty: float,
) -> tuple[list[float], list[float], list[list[float]], list[float], float]:
    """Fit 3-class multinomial logistic regression with train-only standardization & sum-to-zero intercepts."""
    require(x_raw.ndim == 2 and x_raw.shape[0] >= 6 and x_raw.shape[1] >= 1, "INSUFFICIENT_TRAINING_ROWS")
    require(math.isfinite(l2_penalty) and l2_penalty > 0.0, "INVALID_L2_PENALTY")

    n_samples, n_features = x_raw.shape
    means = np.mean(x_raw, axis=0, dtype=np.float64)
    raw_stds = np.std(x_raw, axis=0, ddof=0, dtype=np.float64)
    deviations = np.where(raw_stds > 1e-12, raw_stds, 1.0)
    z = (x_raw - means) / deviations

    y_onehot = np.zeros((n_samples, 3), dtype=np.float64)
    y_onehot[np.arange(n_samples), y_idx] = 1.0

    # Parameter vector: W (3 * F) + b_free (2), with b_2 = -(b_0 + b_1)
    init_theta = np.zeros(3 * n_features + 2, dtype=np.float64)

    def objective_and_grad(theta: np.ndarray) -> tuple[float, np.ndarray]:
        w = theta[: 3 * n_features].reshape(3, n_features)
        b0, b1 = float(theta[-2]), float(theta[-1])
        b = np.array([b0, b1, -(b0 + b1)], dtype=np.float64)

        logits = z @ w.T + b
        log_p = log_softmax(logits, axis=1)
        probs = np.exp(log_p)

        nll = -float(np.sum(log_p * y_onehot))
        reg = 0.5 * l2_penalty * float(np.sum(w * w))
        loss = nll + reg

        diff = probs - y_onehot  # (N, 3)
        grad_w = diff.T @ z + l2_penalty * w  # (3, F)
        grad_b_all = np.sum(diff, axis=0)  # (3,)
        grad_b_free = np.array(
            [grad_b_all[0] - grad_b_all[2], grad_b_all[1] - grad_b_all[2]],
            dtype=np.float64,
        )
        grad = np.concatenate([grad_w.ravel(), grad_b_free])
        return loss, grad

    opt = minimize(
        objective_and_grad,
        init_theta,
        method="L-BFGS-B",
        jac=True,
        options={"gtol": 1e-9, "ftol": 1e-13, "maxiter": 2000},
    )
    require(bool(opt.success) and math.isfinite(float(opt.fun)), "OPTIMIZER_DID_NOT_CONVERGE")

    w_final = opt.x[: 3 * n_features].reshape(3, n_features)
    b0_f, b1_f = float(opt.x[-2]), float(opt.x[-1])
    b_final = [b0_f, b1_f, -(b0_f + b1_f)]

    return (
        [float(v) for v in means.tolist()],
        [float(v) for v in deviations.tolist()],
        [[float(v) for v in row] for row in w_final.tolist()],
        b_final,
        float(opt.fun),
    )


# --------------------------------------------------------------------------- #
# Artifact Construction, Verification & Inference
# --------------------------------------------------------------------------- #
def seal_model_artifact(body_without_sha: Mapping[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in body_without_sha.items() if k != "sha256"}
    out = dict(body)
    out["sha256"] = sha256_ascii(body)
    return verify_model_artifact(out)


def verify_model_artifact(artifact: Any, expected_sha256: str | None = None) -> dict[str, Any]:
    require(type(artifact) is dict and artifact.get("format") == MODEL_ARTIFACT_FORMAT, "MODEL_ARTIFACT_FORMAT")
    for k, v in RESEARCH_FLAGS.items():
        require(artifact.get(k) is v, "MODEL_ARTIFACT_FLAGS")
    require(artifact.get("role") in ("M", "B1", "B0"), "MODEL_ARTIFACT_ROLE")
    require(artifact.get("classes") == list(CLASSES), "MODEL_ARTIFACT_CLASSES")
    require(type(artifact.get("market")) is str and MARKET_RE.fullmatch(artifact["market"]) is not None, "INVALID_MARKET")
    for k in ("name", "version"):
        require(type(artifact.get(k)) is str and 0 < len(artifact[k].strip()) <= 128, "MODEL_ARTIFACT_FORMAT")
    tc = parse_epoch_int(artifact.get("training_cutoff"), error_code="MODEL_TIME_ORDER")
    fa = parse_epoch_int(artifact.get("frozen_at"), error_code="MODEL_TIME_ORDER")
    require(tc < fa, "MODEL_TIME_ORDER")
    require(type(artifact.get("feature_builder_commit")) is str and HEX40_RE.fullmatch(artifact["feature_builder_commit"]) is not None, "INVALID_COMMIT_SHA")

    fnames = artifact.get("feature_names")
    require(type(fnames) is list and len(fnames) <= 8 and all(f in dfb.ALL_FEATURES for f in fnames), "INVALID_FEATURE_SET")
    std = artifact.get("standardization")
    weights = artifact.get("weights")
    require(type(std) is dict and type(weights) is dict, "MODEL_WEIGHTS_INVALID")

    if artifact["role"] == "B0":
        require(fnames == [], "B0_MUST_HAVE_NO_FEATURES")
        prior = weights.get("prior_probabilities")
        require(
            type(prior) is dict
            and set(prior) == set(CLASSES)
            and all(type(prior[c]) in (int, float) and 0.0 <= prior[c] <= 1.0 for c in CLASSES)
            and abs(sum(prior.values()) - 1.0) <= 1e-9,
            "MODEL_WEIGHTS_INVALID",
        )
    else:
        require(len(fnames) >= 1, "INVALID_FEATURE_SET")
        means, devs = std.get("means"), std.get("deviations")
        coefs, intercepts = weights.get("coefficients"), weights.get("intercepts")
        require(
            type(means) is list and len(means) == len(fnames)
            and type(devs) is list and len(devs) == len(fnames) and all(d > 0 for d in devs)
            and type(coefs) is list and len(coefs) == 3 and all(type(r) is list and len(r) == len(fnames) for r in coefs)
            and type(intercepts) is list and len(intercepts) == 3,
            "MODEL_WEIGHTS_INVALID",
        )

    sha = artifact.get("sha256")
    require(type(sha) is str and HEX64_RE.fullmatch(sha) is not None, "MODEL_SHA256_MISMATCH")
    body = {k: v for k, v in artifact.items() if k != "sha256"}
    require(sha256_ascii(body) == sha, "MODEL_SHA256_MISMATCH")
    if expected_sha256 is not None:
        require(sha == expected_sha256, "MODEL_SHA256_MISMATCH")
    return artifact


def read_model_artifact(path: Path | str, expected_sha256: str | None = None) -> dict[str, Any]:
    doc, _ = read_strict_json_file(path, max_bytes=DEFAULT_MAX_BYTES, path_error="MODEL_FILE", size_error="MODEL_FILE_SIZE")
    return verify_model_artifact(doc, expected_sha256)


def predict_raw_probabilities(artifact: Mapping[str, Any], features: Mapping[str, float | None]) -> dict[str, float] | None:
    """Return raw {'up', 'down', 'neutral'} probabilities, or None if any required feature is missing."""
    if artifact["role"] == "B0":
        prior = artifact["weights"]["prior_probabilities"]
        return {c: float(prior[c]) for c in CLASSES}

    fnames: list[str] = artifact["feature_names"]
    vals: list[float] = []
    for fname in fnames:
        v = features.get(fname)
        if v is None:
            return None
        require(type(v) in (int, float) and math.isfinite(v), "NONFINITE_FEATURE_VALUE")
        vals.append(float(v))

    means = np.asarray(artifact["standardization"]["means"], dtype=np.float64)
    devs = np.asarray(artifact["standardization"]["deviations"], dtype=np.float64)
    z = (np.asarray(vals, dtype=np.float64) - means) / devs
    w = np.asarray(artifact["weights"]["coefficients"], dtype=np.float64)
    b = np.asarray(artifact["weights"]["intercepts"], dtype=np.float64)
    logits = w @ z + b
    probs = np.exp(log_softmax(logits))
    return {"up": float(probs[0]), "down": float(probs[1]), "neutral": float(probs[2])}


# --------------------------------------------------------------------------- #
# M11-T4 Held-Out-Week Non-Overlapping Call & Hit-Autocorrelation Estimator
# --------------------------------------------------------------------------- #
def _lag1_autocorrelation(values: Sequence[int]) -> float | None:
    if len(values) < 3:
        return None
    arr = np.asarray(values, dtype=np.float64)
    x0, x1 = arr[:-1], arr[1:]
    s0, s1 = float(np.std(x0, ddof=0)), float(np.std(x1, ddof=0))
    if s0 <= 1e-12 or s1 <= 1e-12:
        return None
    corr = float(np.mean((x0 - np.mean(x0)) * (x1 - np.mean(x1))) / (s0 * s1))
    return max(-1.0, min(1.0, corr))


def estimate_heldout_week_calls(
    *,
    complete_rows: Sequence[Mapping[str, Any]],
    bars_by_end: Mapping[int, Mapping[str, Any]],
    feature_names: Sequence[str],
    train_start: int,
    train_end: int,
    step_seconds: int,
    horizon_seconds: int,
    hurdle_bps: int,
    l2_penalty: float,
    heldout_seconds: int = 7 * 86400,
    candidate_confidences: Sequence[str] = ("0.55", "0.60", "0.65", "0.75"),
) -> dict[str, Any]:
    """Section 6 M11-T4 call-count & hit-autocorrelation estimator on the held-out final week of training."""
    split_cutoff = train_end - heldout_seconds
    fit_rows = [r for r in complete_rows if train_start <= int(r["as_of"]) and int(r["as_of"]) + horizon_seconds <= split_cutoff]
    hold_rows = sorted(
        [r for r in complete_rows if split_cutoff <= int(r["as_of"]) and int(r["as_of"]) + horizon_seconds <= train_end],
        key=lambda r: int(r["as_of"]),
    )
    if len(fit_rows) < 6 or not hold_rows:
        return {
            "available": False,
            "reason": "TRAINING_WINDOW_SHORTER_THAN_HELDOUT_SPLIT",
            "split_cutoff": split_cutoff,
            "heldout_seconds": heldout_seconds,
        }

    x_fit = np.asarray([[float(r["features"][f]) for f in feature_names] for r in fit_rows], dtype=np.float64)
    y_fit = np.asarray([CLASS_TO_IDX[r["label"]] for r in fit_rows], dtype=np.int64)
    means, devs, coefs, intercepts, _ = _fit_multinomial_l2(x_fit, y_fit, l2_penalty)
    sub_model = {
        "role": "M",
        "feature_names": list(feature_names),
        "standardization": {"means": means, "deviations": devs},
        "weights": {"coefficients": coefs, "intercepts": intercepts},
    }

    # Walk held-out week in non-overlapping horizon_seconds windows, just like direction_forecast_adapter
    scored_windows: list[dict[str, Any]] = []
    last_as_of: int | None = None
    for r in hold_rows:
        as_of = int(r["as_of"])
        if last_as_of is not None and as_of < last_as_of + horizon_seconds:
            continue
        raw_p = predict_raw_probabilities(sub_model, r["features"])
        assert raw_p is not None
        quant = quantize_probabilities(raw_p["up"], raw_p["down"])
        if quant is None:
            continue  # tied after rounding -> no forecast written for this bar
        last_as_of = as_of
        probs_str, top_dir = quant
        label, _ = compute_outcome_label(bars_by_end, as_of, step_seconds, horizon_seconds, hurdle_bps)
        scored_windows.append({
            "as_of": as_of,
            "direction": top_dir,
            "probabilities": probs_str,
            "outcome": label,
        })

    by_cutoff: dict[str, dict[str, Any]] = {}
    for conf_str in candidate_confidences:
        cutoff_dec = parse_decimal_str(conf_str, Decimal("0.5"), Decimal("1"), inclusive_low=False)
        up_calls = down_calls = up_hits = down_hits = 0
        hit_seq: list[int] = []
        for w in scored_windows:
            d = w["direction"]
            if d in ("up", "down") and Decimal(w["probabilities"][d]) >= cutoff_dec:
                is_hit = int(w["outcome"] == d)
                hit_seq.append(is_hit)
                if d == "up":
                    up_calls += 1
                    up_hits += is_hit
                else:
                    down_calls += 1
                    down_hits += is_hit
        by_cutoff[conf_str] = {
            "nonoverlap_windows": len(scored_windows),
            "calls_up": up_calls,
            "calls_down": down_calls,
            "total_calls": up_calls + down_calls,
            "hits_up": up_hits,
            "hits_down": down_hits,
            "lag1_hit_autocorrelation": _lag1_autocorrelation(hit_seq),
        }

    return {
        "available": True,
        "split_cutoff": split_cutoff,
        "heldout_seconds": heldout_seconds,
        "fit_row_count": len(fit_rows),
        "nonoverlap_windows": len(scored_windows),
        "by_confidence": by_cutoff,
    }


# --------------------------------------------------------------------------- #
# Main Fit-and-Freeze Pipeline
# --------------------------------------------------------------------------- #
def _count_d1_training_events(
    feature_table: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    train_start: int,
    training_cutoff: int,
) -> int:
    d1_events = feature_table.get("d1_events")
    if type(d1_events) is list and d1_events:
        return sum(1 for ev in d1_events if (train_start - 86400) < int(ev["event_epoch"]) <= training_cutoff)
    # Fallback: count 0 -> 1 rising-edge episodes on D1 across candidate rows
    episodes = 0
    prev_active = False
    for row in candidate_rows:
        v = row["features"].get("D1")
        active = v is not None and float(v) >= 0.5
        if active and not prev_active:
            episodes += 1
        prev_active = active
    return episodes


def fit_and_freeze_models(
    *,
    feature_table: Mapping[str, Any],
    bars: Sequence[Mapping[str, Any]],
    train_start: int,
    train_end: int,
    frozen_at: int,
    horizon_seconds: int = 7200,
    hurdle_bps: int = 25,
    l2_penalty: float = 1.0,
    model_name_prefix: str = "tradegen-direction",
    model_version: str = "0.1.0",
    min_d1_events: int = 8,
    heldout_seconds: int = 7 * 86400,
) -> dict[str, Any]:
    """Fit M, B1, and B0 on the same purged training bars and return sealed frozen artifacts + fit report."""
    dfb.verify_feature_table(feature_table)
    step_seconds = int(feature_table["step_seconds"])
    market = str(feature_table["market"])
    feature_names: list[str] = list(feature_table["feature_names"])
    require(all(p in feature_names for p in PRICE_ONLY_FEATURES), "M_REQUIRES_PRICE_FEATURES")
    require(horizon_seconds >= 2 * step_seconds and horizon_seconds % step_seconds == 0, "HORIZON_NOT_WHOLE_BARS")
    require(type(hurdle_bps) is int and 0 <= hurdle_bps <= 9999, "INVALID_HURDLE_BPS")
    require(train_start < train_end, "INVALID_TRAINING_WINDOW")

    bars_by_end: dict[int, Mapping[str, Any]] = {}
    prev_end: int | None = None
    for b in bars:
        e = parse_epoch_int(b["end"], error_code="INVALID_BAR_TIME")
        k = parse_epoch_int(b["known_at"], low=e, error_code="INVALID_BAR_TIME")
        if prev_end is not None:
            require(e - prev_end == step_seconds, "MISSING_OR_DUPLICATE_BAR")
        prev_end = e
        bars_by_end[e] = b

    # Purge labels whose outcome window (as_of, as_of + horizon_seconds] extends past train_end
    candidate_rows = sorted(
        [
            r for r in feature_table["rows"]
            if train_start <= int(r["as_of"]) and int(r["as_of"]) + horizon_seconds <= train_end
        ],
        key=lambda r: int(r["as_of"]),
    )
    require(len(candidate_rows) >= 6, "INSUFFICIENT_TRAINING_ROWS")

    expected = {end for end in bars_by_end if train_start <= end <= train_end - horizon_seconds}
    observed = {r["as_of"] for r in candidate_rows}
    require(len(observed) == len(candidate_rows) and observed <= expected, "INVALID_TRAINING_FEATURE_GRID")
    complete_count = sum(1 for r in candidate_rows if r["complete"])
    missing_rate = (len(expected) - complete_count) / len(expected)
    require(missing_rate <= 0.05 + 1e-12, "S1_MISSING_FEATURES_EXCEED_5PCT")

    labeled_rows: list[dict[str, Any]] = []
    max_outcome_end = 0
    for r in candidate_rows:
        if not r["complete"]:
            continue
        as_of = int(r["as_of"])
        label, realized = compute_outcome_label(
            bars_by_end,
            as_of,
            step_seconds,
            horizon_seconds,
            hurdle_bps,
            max_known_at=frozen_at - 1,
        )
        max_outcome_end = max(max_outcome_end, as_of + horizon_seconds)
        labeled_rows.append({
            "as_of": as_of,
            "features": dict(r["features"]),
            "label": label,
            "realized_log_return": realized,
        })

    require(len(labeled_rows) >= 6, "INSUFFICIENT_TRAINING_ROWS")
    training_cutoff = max_outcome_end
    require(training_cutoff < frozen_at, "MODEL_TIME_ORDER")

    d1_event_count = 0
    if "D1" in feature_names:
        d1_event_count = _count_d1_training_events(feature_table, candidate_rows, train_start, training_cutoff)
        require(d1_event_count >= min_d1_events, "D1_INSUFFICIENT_EVENTS")

    # Fit M (full feature_names)
    x_m = np.asarray([[float(r["features"][f]) for f in feature_names] for r in labeled_rows], dtype=np.float64)
    y_all = np.asarray([CLASS_TO_IDX[r["label"]] for r in labeled_rows], dtype=np.int64)
    m_means, m_devs, m_coefs, m_intercepts, m_obj = _fit_multinomial_l2(x_m, y_all, l2_penalty)

    # Fit B1 (price-only P1..P4 on the exact same bars!)
    b1_features = list(PRICE_ONLY_FEATURES)
    x_b1 = np.asarray([[float(r["features"][f]) for f in b1_features] for r in labeled_rows], dtype=np.float64)
    b1_means, b1_devs, b1_coefs, b1_intercepts, b1_obj = _fit_multinomial_l2(x_b1, y_all, l2_penalty)

    # Fit B0 (empirical class frequencies on the exact same bars!)
    n_rows = len(labeled_rows)
    class_counts = {c: int(np.sum(y_all == CLASS_TO_IDX[c])) for c in CLASSES}
    b0_priors = {c: class_counts[c] / float(n_rows) for c in CLASSES}
    # Normalize exact floating sum to 1.0
    b0_priors["neutral"] = max(0.0, 1.0 - b0_priors["up"] - b0_priors["down"])

    common_meta = {
        "format": MODEL_ARTIFACT_FORMAT,
        **RESEARCH_FLAGS,
        "version": model_version,
        "market": market,
        "step_seconds": step_seconds,
        "horizon_seconds": horizon_seconds,
        "hurdle_bps": hurdle_bps,
        "l2_penalty": float(l2_penalty),
        "classes": list(CLASSES),
        "training_start": train_start,
        "training_cutoff": training_cutoff,
        "frozen_at": frozen_at,
        "n_training_rows": n_rows,
        "feature_builder_commit": feature_table["feature_builder_commit"],
    }

    artifact_m = seal_model_artifact({
        **common_meta,
        "name": f"{model_name_prefix}-m",
        "role": "M",
        "feature_names": feature_names,
        "feature_definitions": dict(feature_table["feature_definitions"]),
        "upstream_identities": dict(feature_table["upstream_identities"]),
        "standardization": {"means": m_means, "deviations": m_devs},
        "weights": {"coefficients": m_coefs, "intercepts": m_intercepts},
    })

    artifact_b1 = seal_model_artifact({
        **common_meta,
        "name": f"{model_name_prefix}-b1",
        "role": "B1",
        "feature_names": b1_features,
        "feature_definitions": {
            "d1_series": [], "d3_event_types": [], "q1_event_types": [],
            "d1_schedule_window_seconds": 0, "d3_cadence_seconds": 0, "q1_cadence_seconds": 0,
        },
        "upstream_identities": {"didm_v0": None, "quantgpt": None},
        "standardization": {"means": b1_means, "deviations": b1_devs},
        "weights": {"coefficients": b1_coefs, "intercepts": b1_intercepts},
    })

    artifact_b0 = seal_model_artifact({
        **common_meta,
        "name": f"{model_name_prefix}-b0",
        "role": "B0",
        "feature_names": [],
        "feature_definitions": {
            "d1_series": [], "d3_event_types": [], "q1_event_types": [],
            "d1_schedule_window_seconds": 0, "d3_cadence_seconds": 0, "q1_cadence_seconds": 0,
        },
        "upstream_identities": {"didm_v0": None, "quantgpt": None},
        "standardization": {"means": [], "deviations": []},
        "weights": {"prior_probabilities": b0_priors},
    })

    m11_t4_estimate = estimate_heldout_week_calls(
        complete_rows=labeled_rows,
        bars_by_end=bars_by_end,
        feature_names=feature_names,
        train_start=train_start,
        train_end=train_end,
        step_seconds=step_seconds,
        horizon_seconds=horizon_seconds,
        hurdle_bps=hurdle_bps,
        l2_penalty=l2_penalty,
        heldout_seconds=heldout_seconds,
    )

    report = {
        "format": FIT_REPORT_FORMAT,
        **RESEARCH_FLAGS,
        "market": market,
        "train_start": train_start,
        "train_end": train_end,
        "training_cutoff": training_cutoff,
        "frozen_at": frozen_at,
        "candidate_row_count": len(expected),
        "complete_row_count": n_rows,
        "missing_rate": missing_rate,
        "d1_event_count": d1_event_count,
        "class_counts": class_counts,
        "objectives": {"M": m_obj, "B1": b1_obj},
        "models": {
            "M": {"name": artifact_m["name"], "version": artifact_m["version"], "sha256": artifact_m["sha256"]},
            "B1": {"name": artifact_b1["name"], "version": artifact_b1["version"], "sha256": artifact_b1["sha256"]},
            "B0": {"name": artifact_b0["name"], "version": artifact_b0["version"], "sha256": artifact_b0["sha256"]},
        },
        "m11_t4_call_estimate": m11_t4_estimate,
    }
    report["report_sha256"] = sha256_ascii(report)

    return {
        "M": artifact_m,
        "B1": artifact_b1,
        "B0": artifact_b0,
        "report": report,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True, help="tradegen-direction-features-v1 JSON")
    parser.add_argument("--history", type=Path, required=True, help="Price history JSON")
    parser.add_argument("--train-start", type=int, required=True)
    parser.add_argument("--train-end", type=int, required=True)
    parser.add_argument("--frozen-at", type=int, required=True)
    parser.add_argument("--horizon-seconds", type=int, default=7200)
    parser.add_argument("--hurdle-bps", type=int, default=25)
    parser.add_argument("--l2-penalty", type=float, default=1.0)
    parser.add_argument("--model-version", default="0.1.0")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        ftable = dfb.read_feature_table(args.features)
        hist_doc, _ = read_strict_json_file(args.history, max_bytes=DEFAULT_MAX_BYTES)
        bars = hist_doc["bars"] if isinstance(hist_doc, dict) and "bars" in hist_doc else hist_doc

        fitted = fit_and_freeze_models(
            feature_table=ftable,
            bars=bars,
            train_start=args.train_start,
            train_end=args.train_end,
            frozen_at=args.frozen_at,
            horizon_seconds=args.horizon_seconds,
            hurdle_bps=args.hurdle_bps,
            l2_penalty=args.l2_penalty,
            model_version=args.model_version,
        )
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        atomic_publish_json_ascii(out_dir / "model_M.json", fitted["M"])
        atomic_publish_json_ascii(out_dir / "model_B1.json", fitted["B1"])
        atomic_publish_json_ascii(out_dir / "model_B0.json", fitted["B0"])
        atomic_publish_json_ascii(out_dir / "fit_report.json", fitted["report"])
        print(canonical_ascii_str(fitted["report"]))
        return 0
    except StudyError as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError, KeyError):
        reason = "MODEL_FIT_REFUSED"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
