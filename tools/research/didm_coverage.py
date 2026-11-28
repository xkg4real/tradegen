"""Read-only D2 warm-up diagnostic for an hourly research decision.

python -m tools.research.didm_coverage --log-dir <DIDM log> --as-of <aware ISO time>
Optionally supply --price-archive <recorded hourly bar archive>. A pinned head can
be provided for each archive. Coverage never grants training, promotion or order authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from tools.research import didm_run_log as runs
from tools.research import direction_feature_builder as features
from tools.research import upbit_price_recorder as prices
from tools.research._study_common import (
    RESEARCH_FLAGS, StudyError, UTC, canonical_ascii_str, parse_aware_iso, require,
)


def _utc(epoch):
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def _window(known_at, cutoff, size, required):
    slots = range(cutoff - size * 900, cutoff, 900)
    known = [s for s in slots if s in known_at and known_at[s] <= cutoff]
    return {
        "first_slot_utc": _utc(slots[0]),
        "last_slot_utc": _utc(slots[-1]),
        "oldest_verified_slot_utc": _utc(known[0]) if known else None,
        "expected": size,
        "required": required,
        "verified_by_cutoff": len(known),
        "unresolved_at_cutoff": size - len(known),
        "deficit_to_required": max(0, required - len(known)),
    }


def coverage_report(log_dir, *, as_of, pinned_head=None, price_archive=None, price_head=None):
    instant = parse_aware_iso(as_of, error_code="INVALID_AS_OF")
    requested = int(instant.timestamp())
    cutoff = requested // 3600 * 3600
    require(cutoff > features.GDELT_DENOMINATOR_SLOTS * 900, "INVALID_AS_OF")
    require(price_head is None or price_archive is not None, "PRICE_ARCHIVE_REQUIRED")
    summary = runs.summarize_run_log(log_dir, pinned_head=pinned_head)
    known_at = summary["slot_known_epoch"]
    recent = _window(known_at, cutoff, features.GDELT_NUMERATOR_SLOTS, features.GDELT_NUMERATOR_SLOTS)
    full = _window(known_at, cutoff, features.GDELT_DENOMINATOR_SLOTS, features.GDELT_MIN_DENOMINATOR_SLOTS)
    eligible = recent["deficit_to_required"] == 0 and full["deficit_to_required"] == 0

    price = {"status": "NOT_SUPPLIED"}
    if price_archive is not None:
        cfg, bars, actual_head = prices.read_recorded_bars(price_archive, pinned_head=price_head)
        require(cfg.step_seconds == 3600, "HOURLY_PRICE_ARCHIVE_REQUIRED")
        before = {}
        for bar in bars:
            end, received = bar["end"], bar["known_at"]
            require(type(end) is int and type(received) is int, "INVALID_BAR_TIME")
            if cutoff - 24 * 3600 <= end < cutoff and received <= cutoff:
                require(end % 3600 == 0, "AS_OF_OFF_BAR_GRID")
                value = bar["return_bps"]
                require(type(value) is int and -9999 <= value <= 100_000, "INVALID_RETURN_BPS")
                before[end] = bar
        indicators = features.compute_price_features_at(before, cutoff, 3600)
        price = {"status": "AVAILABLE" if all(v is not None for v in indicators.values()) else "MISSING",
                 "market": cfg.market, "verified_bars_by_cutoff": len(before), "required_bars": 24,
                 "deficit_to_required": 24-len(before), "available": [k for k,v in indicators.items() if v is not None],
                 "archive_head_sha256": actual_head}

    return {
        "format": "tradegen-didm-coverage-v1", **RESEARCH_FLAGS,
        "requested_as_of": instant.astimezone(UTC).isoformat(), "hourly_decision_as_of": _utc(cutoff),
        "run_log_head_sha256": summary["head_sha256"], "last_24h": recent, "last_7d": full,
        "slot_coverage_eligible": eligible,
        "d2_status": "VOLUME_EVIDENCE_REQUIRED" if eligible else "MISSING_SLOT_COVERAGE",
        "d2_value": None, "volume_denominator_requirement": "POSITIVE_OBSERVED_VOLUME",
        "price_features": price,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, required=True)
    parser.add_argument("--as-of", required=True, help="Timezone-aware time, evaluated at its last hourly UTC boundary")
    parser.add_argument("--pinned-head", help="Expected SHA-256 head for the DIDM run log")
    parser.add_argument("--price-archive", type=Path, help="Optional explicit recorder archive for P1–P4")
    parser.add_argument("--price-head", help="Expected SHA-256 head for the price archive")
    args = parser.parse_args(argv)
    try:
        report = coverage_report(args.log_dir, as_of=args.as_of, pinned_head=args.pinned_head,
                                 price_archive=args.price_archive, price_head=args.price_head)
    except StudyError as exc:
        print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": str(exc)}))
        return 2
    except (OSError, KeyError, TypeError, ValueError, OverflowError):
        print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": "COVERAGE_INPUT_REFUSED"}))
        return 2
    print(canonical_ascii_str(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
