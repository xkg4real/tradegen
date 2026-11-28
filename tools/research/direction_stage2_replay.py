"""Stage 2 3-arm (static, M, B1) replay with 128-obs carry-over, Row 17, S5/S6/S7 & Criterion 3.

Research only. Carries locked Stage 1 gate history, propagates working Y and latches
across 128-observation chunks, enforces non-model Row 17(a)/(b) boundary latch conventions,
S5 illegal-widening bug trap, S6 ceiling-change truncation, S7 voided-day state carry,
and episode-based early-warning vs excess-alert trade-off evaluation.
Zero imports from core.compliance, core.odds, execution*, tools.owner, config, or main.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from tools.research import adaptive_bid_gap_preview as preview
from tools.research import adaptive_bid_gap_replay as replay_tool
from tools.research import direction_forecast_adapter as adapter
from tools.research import direction_stage1_evaluator as s1e
from tools.research import upbit_quote_recorder as uqr
from tools.research._study_common import (
    DEFAULT_MAX_BYTES,
    RESEARCH_FLAGS,
    StudyError,
    atomic_publish_json_ascii,
    canonical_ascii_str,
    kst_date_iso,
    parse_decimal_str,
    parse_epoch_int,
    read_strict_json_file,
    require,
    sha256_ascii,
)


STAGE2_REPORT_FORMAT = "tradegen-direction-stage2-report-v1"
CHUNK_MAX_OBS = 128


def _has_live_forecast_at(
    forecasts: Sequence[Mapping[str, Any]],
    *,
    market: str,
    horizon_seconds: int,
    hurdle_bps: int,
    evaluation_start: int,
    now: int,
) -> bool:
    for f in forecasts:
        if (
            f["market"] == market
            and f["horizon_seconds"] == horizon_seconds
            and f["hurdle_bps"] == hurdle_bps
            and f["as_of"] >= evaluation_start
            and int(f.get("_effective_issued_at", f["issued_at"])) <= now < int(f["as_of"]) + horizon_seconds
        ):
            return True
    return False


def _prepare_forecasts_for_adapter(
    snapshots: Sequence[Mapping[str, Any]],
    receipt_times: Sequence[int | None] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Merge snapshots and replace issued_at with effective max(issued_at, receipt_at) per Rule 7."""
    model, merged = s1e._merge_with_receipts(snapshots, receipt_times)
    effective_list: list[dict[str, Any]] = []
    for f in merged:
        eff_f = {k: v for k, v in f.items() if k != "_effective_issued_at"}
        eff_f["issued_at"] = int(f["_effective_issued_at"])
        effective_list.append(eff_f)
    return model, effective_list


def _static_direction_source(_document: Any, terms: Any, _scope: str, _cap: Decimal, _now: int, out: dict[str, Any]) -> None:
    out["model_sha256"] = terms["model_sha256"] if isinstance(terms, Mapping) else None
    out["reason"] = "STATIC_BASELINE"
    return None


def _gated_direction_source(
    forecast_model: Mapping[str, Any],
    forecasts: list[dict[str, Any]],
    allowed_directions: frozenset[str] | None = None,
) -> Callable[..., Any]:
    base_source = adapter.forecast_source(dict(forecast_model), forecasts)

    def wrapped(document: Any, terms: Any, scope: str, cap: Decimal, now: int, out: dict[str, Any]) -> Any:
        found = base_source(document, terms, scope, cap, now, out)
        if found is None:
            return None
        direction, stats, config = found
        if allowed_directions is not None and direction not in allowed_directions:
            out["reason"] = "DIRECTION_NOT_IN_STAGE1_PASS"
            return None
        return direction, stats, config

    return wrapped


def _is_boundary_quote_clean(obs: Mapping[str, Any], active_y: Decimal) -> bool:
    """Row 17(a) strictly non-model check: clean quote under active_y and every recorded flag false."""
    if obs["prior_block_active"] or obs["floor_halt"] or obs["daily_stop"]:
        return False
    now = int(obs["as_of"])
    if obs["bid"] is None or obs["bid_at"] != now or type(obs["bid_at"]) is not int:
        return False
    stale_trade = (now - int(obs["last_trade_at"])) > 30
    if stale_trade:
        bid_dec = Decimal(str(obs["bid"]))
        mark_dec = Decimal(str(obs["last_trade"]))
        if Fraction(bid_dec) <= Fraction(mark_dec) * (1 - Fraction(active_y)):
            return False
    return True


def _check_s5_illegal_widening(
    chunk_obs: Sequence[Mapping[str, Any]],
    chunk_events: Sequence[Mapping[str, Any]],
    carried_latch_at_start: bool,
) -> bool:
    """Return True if any event widened Y while a block, stop, or non-clean quote was active (S5 bug)."""
    running_latch = carried_latch_at_start
    for ev in chunk_events:
        seq = int(ev["sequence"])
        obs = chunk_obs[seq - 1]
        running_latch = (
            running_latch
            or bool(obs["prior_block_active"])
            or bool(obs["floor_halt"])
            or bool(obs["daily_stop"])
            or ev["quote_state"] != "NO_STALE_BID_GAP"
        )
        widened = Decimal(str(ev["next_y"])) > Decimal(str(ev["used_y"])) or ev["transition"] == "WIDEN_FOR_NEXT"
        if widened and (running_latch or bool(ev["entry_block_latched"])):
            return True
        running_latch = running_latch or bool(ev["entry_block_latched"])
    return False


def _replay_arm_chunks(
    *,
    arm_name: str,
    observations: Sequence[Mapping[str, Any]],
    stage1_history: Mapping[str, Any],
    model_study: Mapping[str, Any],
    direction_source: Callable[..., Any],
    ceiling_y_str: str,
    latch_convention: str,
    interval_seconds: int,
    replay_fn: Callable[..., dict[str, Any]] = replay_tool.replay,
) -> dict[str, Any]:
    """Replay an arbitrarily long quote record in 128-observation chunks with state carry-over."""
    scope = str(model_study["scope"])
    model_sha = preview.model_id(dict(model_study))
    current_y = ceiling_y_str
    carried_latch = False
    ever_latched_runtime = False
    first_latch_at: int | None = None
    dropped_pending_widenings = 0
    boundary_latch_releases = 0
    lenient_unblocked_seconds = 0

    all_events: list[dict[str, Any]] = []
    global_idx = 0

    for offset in range(0, len(observations), CHUNK_MAX_OBS):
        raw_chunk = observations[offset: offset + CHUNK_MAX_OBS]
        chunk_obs: list[dict[str, Any]] = []
        for local_seq, obs in enumerate(raw_chunk, start=1):
            c_obs = dict(obs)
            c_obs["sequence"] = local_seq
            if local_seq == 1 and carried_latch:
                c_obs["prior_block_active"] = True
            chunk_obs.append(c_obs)

        doc = {
            "schema": replay_tool.SCHEMA,
            "terms": {
                "scope": scope,
                "ceiling_y": ceiling_y_str,
                "current_y": current_y,
                "model_sha256": model_sha,
            },
            "model": dict(model_study),
            "history": dict(stage1_history),
            "observations": chunk_obs,
        }
        chunk_rep = replay_fn(doc, direction_source)
        if chunk_rep.get("status") != "REPLAYED":
            return {
                "arm": arm_name,
                "status": "REJECTED",
                "reason": chunk_rep.get("reason", "CHUNK_REPLAY_REJECTED"),
            }

        chunk_events = chunk_rep["events"]
        if _check_s5_illegal_widening(raw_chunk, chunk_events, carried_latch):
            return {
                "arm": arm_name,
                "status": "BUG_S5_ILLEGAL_WIDENING",
                "reason": "S5_WIDENED_WHILE_BLOCKED_OR_TRIGGERED",
            }

        for local_i, ev in enumerate(chunk_events):
            raw_o = raw_chunk[local_i]
            now_ts = int(ev["as_of"])
            dt = interval_seconds if global_idx == 0 else max(0, now_ts - int(observations[global_idx - 1]["as_of"]))
            if ev["entry_block_latched"] and not ever_latched_runtime:
                ever_latched_runtime = True
                first_latch_at = now_ts
            elif ever_latched_runtime and not ev["entry_block_latched"]:
                lenient_unblocked_seconds += dt

            enriched = {
                **ev,
                "global_sequence": global_idx + 1,
                "kst_date": kst_date_iso(now_ts),
                "last_trade": raw_o["last_trade"],
                "last_trade_at": raw_o["last_trade_at"],
                "bid": raw_o["bid"],
                "bid_at": raw_o["bid_at"],
                "recorded_prior_block": bool(raw_o["prior_block_active"]),
                "floor_halt": bool(raw_o["floor_halt"]),
                "daily_stop": bool(raw_o["daily_stop"]),
            }
            all_events.append(enriched)
            global_idx += 1

        # Count pending widening dropped at boundary when more chunks follow
        has_more_chunks = (offset + CHUNK_MAX_OBS) < len(observations)
        if has_more_chunks and chunk_events:
            last_ev = chunk_events[-1]
            if last_ev["transition"] == "AWAIT_WIDEN_CONFIRMATION":
                dropped_pending_widenings += 1

        current_y = str(chunk_rep["final_working_y"])
        end_latched = bool(chunk_rep["entry_block_latched"])
        if has_more_chunks and end_latched:
            if latch_convention == "17a":
                # Strictly non-model Row 17(a) boundary check on the original recorded observation
                if _is_boundary_quote_clean(raw_chunk[-1], Decimal(current_y)):
                    carried_latch = False
                    boundary_latch_releases += 1
                else:
                    carried_latch = True
            else:
                carried_latch = True
        else:
            carried_latch = end_latched

    return {
        "arm": arm_name,
        "status": "REPLAYED",
        "events": all_events,
        "final_working_y": current_y,
        "final_latched": carried_latch,
        "first_latch_at": first_latch_at,
        "dropped_pending_widenings": dropped_pending_widenings,
        "boundary_latch_releases": boundary_latch_releases,
        "lenient_unblocked_seconds": lenient_unblocked_seconds,
    }


def _extract_episodes(
    events: Sequence[Mapping[str, Any]],
    *,
    valid_kst_dates: set[str],
    latch_convention: str,
    first_latch_at: int | None,
) -> list[dict[str, Any]]:
    """Extract alert episodes (first BID_GAP_TRIGGERED after a clean NO_STALE_BID_GAP)."""
    episodes: list[dict[str, Any]] = []
    in_episode = False
    for ev in events:
        if latch_convention == "17b" and first_latch_at is not None and int(ev["as_of"]) > first_latch_at:
            break
        qs = ev["quote_state"]
        if qs == "BID_GAP_TRIGGERED":
            if not in_episode:
                in_episode = True
                if ev["kst_date"] in valid_kst_dates:
                    episodes.append({
                        "start_as_of": int(ev["as_of"]),
                        "kst_date": ev["kst_date"],
                        "mark_at_start": str(ev["last_trade"]),
                        "used_y": str(ev["used_y"]),
                    })
        elif qs == "NO_STALE_BID_GAP":
            in_episode = False
    return episodes


def _evaluate_criterion3(
    *,
    static_events: Sequence[Mapping[str, Any]],
    adaptive_events: Sequence[Mapping[str, Any]],
    adaptive_episodes: Sequence[Mapping[str, Any]],
    ceiling_y: Decimal,
    early_warning_window_seconds: int,
) -> dict[str, Any]:
    """Classify each adaptive episode into coincident_static, early_warning, or excess_alert."""
    static_triggered_times = sorted(
        int(e["as_of"]) for e in static_events if e["quote_state"] == "BID_GAP_TRIGGERED"
    )
    static_trig_set = set(static_triggered_times)

    # Index prices by timestamp for adverse-move lookup in (t_ep, t_ep + T]
    price_points: list[tuple[int, Fraction]] = []
    for e in static_events:
        ts = int(e["as_of"])
        price_points.append((ts, Fraction(Decimal(str(e["last_trade"])))))
        if e["bid"] is not None and e["bid_at"] == ts:
            price_points.append((ts, Fraction(Decimal(str(e["bid"])))))

    coincident = 0
    early_warnings = 0
    excess_alerts = 0

    for ep in adaptive_episodes:
        t0 = int(ep["start_as_of"])
        if t0 in static_trig_set:
            coincident += 1
            continue
        t_limit = t0 + early_warning_window_seconds
        future_static = any(t0 < st <= t_limit for st in static_triggered_times)
        adverse_limit = Fraction(Decimal(ep["mark_at_start"])) * (1 - Fraction(ceiling_y))
        future_adverse = any(
            t0 < ts <= t_limit and px <= adverse_limit
            for ts, px in price_points
        )
        if future_static or future_adverse:
            early_warnings += 1
        else:
            excess_alerts += 1

    # Verify zero missed static alerts by construction (every static triggered obs is triggered in adaptive)
    adaptive_trig_set = {int(e["as_of"]) for e in adaptive_events if e["quote_state"] == "BID_GAP_TRIGGERED"}
    missed_static = sum(1 for st in static_triggered_times if st not in adaptive_trig_set)

    return {
        "total_episodes": len(adaptive_episodes),
        "coincident_static_episodes": coincident,
        "early_warnings": early_warnings,
        "excess_alerts": excess_alerts,
        "missed_static_alert_observations": missed_static,
    }


def _auxiliary_arm_metrics(
    events: Sequence[Mapping[str, Any]],
    static_events: Sequence[Mapping[str, Any]],
    *,
    valid_kst_dates: set[str],
    ceiling_y: Decimal,
    interval_seconds: int,
    live_forecast_flags: Mapping[int, bool],
) -> dict[str, Any]:
    valid_evs = [e for e in events if e["kst_date"] in valid_kst_dates]
    valid_static = [e for e in static_events if e["kst_date"] in valid_kst_dates]
    n_obs = len(valid_evs)
    if n_obs == 0:
        return {
            "observation_count": 0,
            "stale_trade_observations": 0,
            "bid_unavailable_observations": 0,
            "floor_halt_observations": 0,
            "daily_stop_observations": 0,
            "latched_observations": 0,
            "excess_blocked_observations": 0,
            "adverse_moves_count": 0,
            "restart_gaps_count": 0,
            "max_observation_gap_seconds": 0,
            "live_forecast_share": 0.0,
        }

    stale_cnt = sum(1 for e in valid_evs if (int(e["as_of"]) - int(e["last_trade_at"])) > 30)
    bid_unavail = sum(1 for e in valid_evs if e["quote_state"] == "BID_UNAVAILABLE")
    floor_cnt = sum(1 for e in valid_evs if e["floor_halt"])
    dstop_cnt = sum(1 for e in valid_evs if e["daily_stop"])
    latched_cnt = sum(1 for e in valid_evs if e["entry_block_latched"])
    excess_blk = sum(
        1 for e, se in zip(valid_evs, valid_static)
        if e["entry_block_latched"] and not se["entry_block_latched"]
    )
    adverse_cnt = 0
    prev_mark: Fraction | None = None
    for e in valid_evs:
        cur_mark = Fraction(Decimal(str(e["last_trade"])))
        if prev_mark is not None and cur_mark <= prev_mark * (1 - Fraction(ceiling_y)):
            adverse_cnt += 1
        prev_mark = cur_mark

    gaps = [
        int(valid_evs[i]["as_of"]) - int(valid_evs[i - 1]["as_of"])
        for i in range(1, len(valid_evs))
    ]
    restart_gaps = sum(1 for g in gaps if g > 2 * interval_seconds)
    max_gap = max(gaps, default=0)
    live_share = sum(1 for e in valid_evs if live_forecast_flags.get(int(e["as_of"]), False)) / float(n_obs)

    return {
        "observation_count": n_obs,
        "stale_trade_observations": stale_cnt,
        "bid_unavailable_observations": bid_unavail,
        "floor_halt_observations": floor_cnt,
        "daily_stop_observations": dstop_cnt,
        "latched_observations": latched_cnt,
        "excess_blocked_observations": excess_blk,
        "adverse_moves_count": adverse_cnt,
        "restart_gaps_count": restart_gaps,
        "max_observation_gap_seconds": max_gap,
        "live_forecast_share": round(live_share, 6),
    }


def run_stage2_replay(
    *,
    study: Mapping[str, Any],
    stage1_report: Mapping[str, Any],
    stage1_history: Mapping[str, Any],
    daily_quote_records: Sequence[Mapping[str, Any]],
    m_snapshots: Sequence[Mapping[str, Any]],
    b1_snapshots: Sequence[Mapping[str, Any]],
    m_receipt_times: Sequence[int | None] | None = None,
    b1_receipt_times: Sequence[int | None] | None = None,
    ceiling_events: Sequence[Mapping[str, Any]] = (),
    replay_fn: Callable[..., dict[str, Any]] = replay_tool.replay,
) -> dict[str, Any]:
    """Run 3-arm Stage 2 replay (static, M, B1) and evaluate Criterion 3."""
    require(type(stage1_report) is dict and stage1_report.get("outcome") == "PASS", "STAGE1_NOT_PASSED")
    require(stage1_report.get("format") == s1e.STAGE1_REPORT_FORMAT and stage1_report.get("mode") == "final",
            "INVALID_STAGE1_REPORT")
    require(sha256_ascii({k: v for k, v in stage1_report.items() if k != "report_sha256"})
            == stage1_report.get("report_sha256"), "STAGE1_REPORT_HASH_MISMATCH")
    evidence = stage1_report.get("gate_evidence")
    require(type(evidence) is dict, "STAGE1_EVIDENCE_MISSING")
    fields = evidence["study_fields"]
    require(all(k in study for k in fields) and sha256_ascii({k: study[k] for k in fields}) == evidence["study_sha256"],
            "STAGE1_STUDY_CHANGED")
    require(sha256_ascii(stage1_history) == evidence["history_sha256"], "STAGE1_HISTORY_CHANGED")
    passing_m_dirs = frozenset(stage1_report.get("passing_directions", ()))
    require(len(passing_m_dirs) >= 1, "STAGE1_NOT_PASSED")

    ceiling_y_str = str(study["ceiling_y"])
    ceiling_y = preview.bounds(ceiling_y_str)
    up_y_str = str(study["up_y"])
    down_y_str = str(study["down_y"])
    require(preview.bounds(up_y_str) <= ceiling_y and preview.bounds(down_y_str) <= ceiling_y, "MODEL_TARGET_OUTSIDE_ENVELOPE")

    latch_conv = str(study.get("latch_convention", "17a"))
    require(latch_conv in ("17a", "17b"), "INVALID_LATCH_CONVENTION")
    interval_sec = int(study.get("quote_interval_seconds", 10))
    min_quote_cov = float(study.get("min_daily_quote_coverage", 0.95))
    min_live_cov = float(study.get("min_daily_live_forecast_coverage", 0.95))
    min_stage2_days = int(study.get("min_stage2_days", 14))
    ew_window_sec = int(study.get("early_warning_window_seconds", 1800))
    max_excess_per_day = float(study.get("max_excess_alerts_per_day", 1.0))
    min_early_warnings = int(study.get("min_early_warnings", 1))
    ceiling_mode = str(study.get("ceiling_mode", "7a"))  # "7a" private research ceiling vs "7b" signed ceiling

    # Flatten daily quote records in chronological order
    all_obs: list[dict[str, Any]] = []
    expected_per_day: dict[str, int] = {}
    prev_ts = -1
    for drec in daily_quote_records:
        kdate = str(drec["kst_date"])
        require(kdate not in expected_per_day and drec.get("market") == study["market"]
                and drec.get("scope") == study["scope"] and drec.get("interval_seconds") == interval_sec,
                "QUOTE_STUDY_MISMATCH")
        uqr.verify_daily_quotes(drec)
        expected_per_day[kdate] = int(drec.get("expected_observations", 86400 // interval_sec))
        for obs in drec["observations"]:
            ts = parse_epoch_int(obs["as_of"], low=1, error_code="CHRONOLOGY_UNRESOLVED")
            require(ts > prev_ts and ts > evidence["evaluated_at"] and kst_date_iso(ts) == kdate,
                    "CHRONOLOGY_UNRESOLVED")
            prev_ts = ts
            all_obs.append(dict(obs))
    require(len(all_obs) > 0, "NO_STAGE2_OBSERVATIONS")

    # S6 check: signed Y below research ceiling (7a) or signed ceiling changed (7b)
    s6_cutoff: int | None = None
    for cev in sorted(ceiling_events, key=lambda x: int(x["at"])):
        ev_at = parse_epoch_int(cev["at"], error_code="INVALID_S6_EVENT")
        signed_y = parse_decimal_str(cev["signed_y"], Decimal("0"), Decimal("1"), inclusive_low=False, error_code="INVALID_S6_EVENT")
        triggers_s6 = (signed_y < ceiling_y) if ceiling_mode == "7a" else (signed_y != ceiling_y)
        if triggers_s6:
            s6_cutoff = ev_at
            break

    if s6_cutoff is not None and s6_cutoff <= int(all_obs[0]["as_of"]):
        rep = {
            "format": STAGE2_REPORT_FORMAT,
            **RESEARCH_FLAGS,
            "outcome": "STOPPED_S6_BEFORE_START",
            "stop_rule": "S6",
            "truncated_by_s6": True,
            "s6_truncated_at": s6_cutoff,
        }
        rep["report_sha256"] = sha256_ascii(rep)
        return rep

    truncated_by_s6 = False
    if s6_cutoff is not None:
        all_obs = [o for o in all_obs if int(o["as_of"]) < s6_cutoff]
        truncated_by_s6 = True

    m_model, m_forecasts = _prepare_forecasts_for_adapter(m_snapshots, m_receipt_times)
    b1_model, b1_forecasts = _prepare_forecasts_for_adapter(b1_snapshots, b1_receipt_times)

    for arm, model, forecasts, pin in (("M", m_model, m_forecasts, "forecast_model"),
                                       ("B1", b1_model, b1_forecasts, "b1_forecast_model")):
        require({k: model[k] for k in ("name", "version", "sha256")} == study[pin], "STAGE1_MODEL_CHANGED")
        require(s1e.gate_forecasts_digest(forecasts, study) == evidence[arm + "_sha256"], "STAGE1_FORECASTS_CHANGED")

    def eligible_in_replay(forecasts):
        # A batch that was unavailable at the stage 1 decision never gains a holdout vote.
        return [f for f in forecasts if f["as_of"] + horizon > study["evaluation_end"]
                or f["issued_at"] <= evidence["evaluated_at"]]

    horizon = study["horizon_seconds"]
    m_forecasts = eligible_in_replay(m_forecasts)
    b1_forecasts = eligible_in_replay(b1_forecasts)
    # Later prices cannot contribute new holdout evidence to the frozen gate.
    stage1_history = {**stage1_history, "bars": [b for b in stage1_history["bars"] if b["end"] <= study["evaluation_end"]]}
    market = str(study["market"])
    step_sec = int(study["step_seconds"])
    horizon_sec = int(study["horizon_seconds"])
    hurdle_bps = int(study["hurdle_bps"])
    eval_start = int(study["evaluation_start"])
    scope = str(study["scope"])
    source_id = str(study["source_id"])

    common_study_fields = {
        "scope": scope,
        "rule_version": adapter.RULE,
        "source_id": source_id,
        "market": market,
        "evaluation_start": eval_start,
        "step_seconds": step_sec,
        "horizon_seconds": horizon_sec,
        "hurdle_bps": hurdle_bps,
        "confidence": str(study["confidence"]),
        "min_validation_calls": int(study["min_validation_calls"]),
        "max_calibration_gap": str(study["max_calibration_gap"]),
    }

    study_static = {
        **common_study_fields,
        "forecast_model": {k: m_model[k] for k in ("name", "version", "sha256")},
        "up_y": ceiling_y_str,
        "down_y": ceiling_y_str,
    }
    study_m = {
        **common_study_fields,
        "forecast_model": {k: m_model[k] for k in ("name", "version", "sha256")},
        "up_y": up_y_str,
        "down_y": down_y_str,
    }
    study_b1 = {
        **common_study_fields,
        "forecast_model": {k: b1_model[k] for k in ("name", "version", "sha256")},
        "up_y": up_y_str,
        "down_y": down_y_str,
    }

    arm_static = _replay_arm_chunks(
        arm_name="static",
        observations=all_obs,
        stage1_history=stage1_history,
        model_study=study_static,
        direction_source=_static_direction_source,
        ceiling_y_str=ceiling_y_str,
        latch_convention=latch_conv,
        interval_seconds=interval_sec,
        replay_fn=replay_fn,
    )
    arm_m = _replay_arm_chunks(
        arm_name="M",
        observations=all_obs,
        stage1_history=stage1_history,
        model_study=study_m,
        direction_source=_gated_direction_source(m_model, m_forecasts, passing_m_dirs),
        ceiling_y_str=ceiling_y_str,
        latch_convention=latch_conv,
        interval_seconds=interval_sec,
        replay_fn=replay_fn,
    )
    arm_b1 = _replay_arm_chunks(
        arm_name="B1",
        observations=all_obs,
        stage1_history=stage1_history,
        model_study=study_b1,
        direction_source=_gated_direction_source(b1_model, b1_forecasts, frozenset(stage1_report["b1_passing_directions"])),
        ceiling_y_str=ceiling_y_str,
        latch_convention=latch_conv,
        interval_seconds=interval_sec,
        replay_fn=replay_fn,
    )

    for arm_res in (arm_static, arm_m, arm_b1):
        if arm_res["status"] == "BUG_S5_ILLEGAL_WIDENING":
            rep = {
                "format": STAGE2_REPORT_FORMAT,
                **RESEARCH_FLAGS,
                "outcome": "BUG_S5_ILLEGAL_WIDENING",
                "stop_rule": "S5",
                "faulting_arm": arm_res["arm"],
                "reason": arm_res["reason"],
            }
            rep["report_sha256"] = sha256_ascii(rep)
            return rep
        require(arm_res["status"] == "REPLAYED", arm_res.get("reason", "STAGE2_REPLAY_REJECTED"))

    # Compute live forecast presence per observation timestamp for M and B1
    live_m_map = {
        int(o["as_of"]): _has_live_forecast_at(
            m_forecasts,
            market=market,
            horizon_seconds=horizon_sec,
            hurdle_bps=hurdle_bps,
            evaluation_start=eval_start,
            now=int(o["as_of"]),
        )
        for o in all_obs
    }
    live_b1_map = {
        int(o["as_of"]): _has_live_forecast_at(
            b1_forecasts,
            market=market,
            horizon_seconds=horizon_sec,
            hurdle_bps=hurdle_bps,
            evaluation_start=eval_start,
            now=int(o["as_of"]),
        )
        for o in all_obs
    }

    # S7 per-KST-day coverage check (voided days were ALREADY replayed above for state carry!)
    obs_by_day: dict[str, list[dict[str, Any]]] = {}
    for o in all_obs:
        kd = kst_date_iso(int(o["as_of"]))
        obs_by_day.setdefault(kd, []).append(o)

    valid_days: set[str] = set()
    voided_days: dict[str, dict[str, Any]] = {}
    for kd, day_obs in sorted(obs_by_day.items()):
        exp_n = expected_per_day.get(kd, max(1, len(day_obs)))
        valid_q = sum(1 for o in day_obs if o["bid"] is not None and o["bid_at"] == o["as_of"])
        q_cov = valid_q / float(exp_n)
        live_cov = sum(1 for o in day_obs if live_m_map[int(o["as_of"])]) / float(len(day_obs))
        if q_cov + 1e-12 >= min_quote_cov and live_cov + 1e-12 >= min_live_cov:
            valid_days.add(kd)
        else:
            voided_days[kd] = {
                "quote_coverage": round(q_cov, 6),
                "live_m_forecast_coverage": round(live_cov, 6),
            }

    ep_static = _extract_episodes(
        arm_static["events"],
        valid_kst_dates=valid_days,
        latch_convention=latch_conv,
        first_latch_at=arm_static["first_latch_at"],
    )
    ep_m = _extract_episodes(
        arm_m["events"],
        valid_kst_dates=valid_days,
        latch_convention=latch_conv,
        first_latch_at=arm_m["first_latch_at"],
    )
    ep_b1 = _extract_episodes(
        arm_b1["events"],
        valid_kst_dates=valid_days,
        latch_convention=latch_conv,
        first_latch_at=arm_b1["first_latch_at"],
    )

    c3_m = _evaluate_criterion3(
        static_events=arm_static["events"],
        adaptive_events=arm_m["events"],
        adaptive_episodes=ep_m,
        ceiling_y=ceiling_y,
        early_warning_window_seconds=ew_window_sec,
    )
    c3_b1 = _evaluate_criterion3(
        static_events=arm_static["events"],
        adaptive_events=arm_b1["events"],
        adaptive_episodes=ep_b1,
        ceiling_y=ceiling_y,
        early_warning_window_seconds=ew_window_sec,
    )

    n_valid_days = len(valid_days)
    excess_per_day_m = (c3_m["excess_alerts"] / float(n_valid_days)) if n_valid_days > 0 else 0.0
    excess_per_day_b1 = (c3_b1["excess_alerts"] / float(n_valid_days)) if n_valid_days > 0 else 0.0

    arms_summary = {}
    for name, arm_data, ep_list, live_map in (
        ("static", arm_static, ep_static, {int(o["as_of"]): False for o in all_obs}),
        ("M", arm_m, ep_m, live_m_map),
        ("B1", arm_b1, ep_b1, live_b1_map),
    ):
        aux = _auxiliary_arm_metrics(
            arm_data["events"],
            arm_static["events"],
            valid_kst_dates=valid_days,
            ceiling_y=ceiling_y,
            interval_seconds=interval_sec,
            live_forecast_flags=live_map,
        )
        arms_summary[name] = {
            "final_working_y": arm_data["final_working_y"],
            "final_latched": arm_data["final_latched"],
            "first_latch_at": arm_data["first_latch_at"],
            "dropped_pending_widenings": arm_data["dropped_pending_widenings"],
            "boundary_latch_releases": arm_data["boundary_latch_releases"],
            "lenient_unblocked_seconds": arm_data["lenient_unblocked_seconds"],
            "episode_count": len(ep_list),
            **aux,
        }

    if n_valid_days < min_stage2_days:
        outcome = "INCONCLUSIVE"
        stop_rule: str | None = "S7"
        passed_c3 = False
    else:
        stop_rule = "S6" if truncated_by_s6 else None
        passed_c3 = bool(
            c3_m["missed_static_alert_observations"] == 0
            and excess_per_day_m <= max_excess_per_day + 1e-12
            and c3_m["early_warnings"] >= min_early_warnings
            and c3_m["early_warnings"] >= c3_b1["early_warnings"]
            and c3_m["excess_alerts"] <= c3_b1["excess_alerts"]
        )
        outcome = "PASS" if passed_c3 else "NOT SHOWN"

    report = {
        "format": STAGE2_REPORT_FORMAT,
        **RESEARCH_FLAGS,
        "execution_costs_measured": False,
        "m11_t5_fill_check_closed": False,
        "outcome": outcome,
        "stop_rule": stop_rule,
        "passed_criterion3": passed_c3,
        "latch_convention": latch_conv,
        "truncated_by_s6": truncated_by_s6,
        "s6_truncated_at": s6_cutoff if truncated_by_s6 else None,
        "valid_day_count": n_valid_days,
        "valid_kst_dates": sorted(valid_days),
        "voided_days_s7": voided_days,
        "criterion3": {
            "early_warning_window_seconds": ew_window_sec,
            "max_excess_alerts_per_day": max_excess_per_day,
            "static_episodes": len(ep_static),
            "M": {**c3_m, "excess_alerts_per_day": round(excess_per_day_m, 6)},
            "B1": {**c3_b1, "excess_alerts_per_day": round(excess_per_day_b1, 6)},
        },
        "arms": arms_summary,
    }
    report["report_sha256"] = sha256_ascii(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--stage1-report", type=Path, required=True)
    parser.add_argument("--stage1-history", type=Path, required=True)
    parser.add_argument("--daily-quotes", action="append", required=True, type=Path)
    parser.add_argument("--m-snapshot", action="append", required=True, metavar="PATH=SHA256[@RECEIPT]")
    parser.add_argument("--b1-snapshot", action="append", required=True, metavar="PATH=SHA256[@RECEIPT]")
    parser.add_argument("--ceiling-events", type=Path, help="Optional JSON list of S6 ceiling change events")
    parser.add_argument("--output", type=Path)
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
        s1_rep, _ = read_strict_json_file(args.stage1_report, max_bytes=DEFAULT_MAX_BYTES)
        s1_hist, _ = read_strict_json_file(args.stage1_history, max_bytes=DEFAULT_MAX_BYTES)
        dquotes = [uqr.read_daily_quotes(p) for p in args.daily_quotes]
        m_snaps, m_recs = load_snaps(args.m_snapshot)
        b1_snaps, b1_recs = load_snaps(args.b1_snapshot)
        c_events = read_strict_json_file(args.ceiling_events, max_bytes=DEFAULT_MAX_BYTES)[0] if args.ceiling_events else []

        report = run_stage2_replay(
            study=study_doc,
            stage1_report=s1_rep,
            stage1_history=s1_hist,
            daily_quote_records=dquotes,
            m_snapshots=m_snaps,
            b1_snapshots=b1_snaps,
            m_receipt_times=m_recs,
            b1_receipt_times=b1_recs,
            ceiling_events=c_events,
        )
        if args.output is not None:
            atomic_publish_json_ascii(args.output, report)
        print(canonical_ascii_str(report))
        return 0
    except (StudyError, preview.Invalid) as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError, KeyError):
        reason = "STAGE2_REPLAY_REFUSED"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
