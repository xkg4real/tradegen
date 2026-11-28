"""Audit paired, costed returns from an existing research_lab.run output directory."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

FIELDS = {"date", "asset", "currency", "candidate_id", "split", "net_return", "gross_return",
          "position", "held_weight", "turnover", "cost", "benchmark_return"}
NUMERIC = ("net_return", "gross_return", "benchmark_return", "position", "held_weight",
           "turnover", "cost")
TOL = 1e-12


def close(left, right):
    return math.isclose(left, right, rel_tol=1e-10, abs_tol=TOL)


def series_stats(returns):
    wealth = peak = 1.0
    worst = 0.0
    for change in returns:
        wealth *= 1 + change
        if not math.isfinite(wealth) or wealth <= 0:
            raise ValueError("nonpositive or nonfinite compounded wealth")
        peak = max(wealth, peak)
        worst = max(worst, 1 - wealth / peak)
    return 100 * (wealth - 1), 100 * worst


def read_ledger(path, assets):
    grouped = defaultdict(list)
    previous_day = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if len(set(columns)) != len(columns) or not FIELDS.issubset(columns):
            raise ValueError("missing or duplicate daily ledger columns")
        for row in reader:
            asset, split = row["asset"], row["split"]
            spec = assets.get(asset, {})
            selected = spec.get("selected") or {}
            if (None in row or split not in spec.get("phases", {}) or not selected or
                    row["currency"] != spec["currency"] or row["candidate_id"] != selected["candidate_id"]):
                raise ValueError(f"row {reader.line_num}: unexpected asset, split, currency or candidate")
            day = row["date"]
            span = spec["phases"][split]
            if (date.fromisoformat(day).isoformat() != day or day <= previous_day.get(asset, "") or
                    not span["start"] <= day <= span["end"]):
                raise ValueError(f"row {reader.line_num}: invalid, duplicate or out-of-order date for {asset}")
            previous_day[asset] = day
            values = {key: float(row[key]) for key in NUMERIC}
            if not all(map(math.isfinite, values.values())):
                raise ValueError(f"row {reader.line_num}: nonfinite daily observation")
            net, gross, benchmark, position, held, turnover, cost = (values[k] for k in NUMERIC)
            if (min(net, gross, benchmark) <= -1 or not 0 <= position <= 1 + TOL or
                    not 0 <= held <= 1 + TOL or turnover < 0 or not 0 <= cost < 1):
                raise ValueError(f"row {reader.line_num}: invalid return, exposure, turnover or cost")
            if held == 0 and not close(gross, 0):
                raise ValueError(f"row {reader.line_num}: uninvested day has gross return")
            if (not close((1 + gross) * (1 - cost), 1 + net) or
                    not close(cost, turnover * spec["cost_bps_per_side"] / 10000)):
                raise ValueError(f"row {reader.line_num}: inconsistent post-move cost or net return")
            values["date"] = day
            grouped[asset, split].append(values)
    return grouped


def summarize(rows, spec, split):
    # Phase paths start in cash; the simulator already charged final liquidation.
    previous = 0.0
    for row in rows:
        if not close(row["held_weight"], previous):
            raise ValueError("held exposure does not match previous close position")
        previous = row["position"]
    if not close(previous, 0):
        raise ValueError("completed study phase did not liquidate")
    strategy, drawdown = series_stats(r["net_return"] for r in rows)
    benchmark, benchmark_drawdown = series_stats(r["benchmark_return"] for r in rows)
    gross_path, _ = series_stats(r["gross_return"] for r in rows)
    for key, value in [(split, strategy), (split + "_benchmark", benchmark)]:
        if key in spec and not close(value / 100, spec[key]["total_return"]):
            raise ValueError(f"{key}: compounded ledger differs from stored summary")
    held = sum(r["held_weight"] > TOL for r in rows)
    trades = sum(r["turnover"] > TOL for r in rows)
    result = dict(status="active" if held or trades else "cash_throughout",
                  strategy_return_pct=strategy, costed_buy_hold_return_pct=benchmark,
                  strategy_minus_buy_hold_pp=strategy - benchmark, strategy_max_drawdown_pct=drawdown,
                  buy_hold_max_drawdown_pct=benchmark_drawdown, average_held_exposure_pct=
                  100 * math.fsum(r["held_weight"] for r in rows) / len(rows),
                  days_with_exposure=held, turnover_days=trades,
                  total_turnover=math.fsum(r["turnover"] for r in rows),
                  same_exposure_fee_drag_pp=gross_path - strategy)
    for direction in ("up", "down"):
        if direction == "up":
            sample = [r for r in rows if r["benchmark_return"] > 0]
        else:
            sample = [r for r in rows if r["benchmark_return"] < 0]
        result[f"benchmark_{direction}_days"] = len(sample)
        exposed = sum(r["held_weight"] > TOL for r in sample)
        result[f"exposed_on_benchmark_{direction}_days_pct"] = 100 * exposed / len(sample) if sample else None
    return result


def audit(directory):
    summary_path = directory / "summary.json"
    ledger_path = directory / "selected_daily.csv"
    summary = json.loads(summary_path.read_bytes())
    if summary.get("schema_version") != 1 or not summary.get("assets"):
        raise ValueError("unsupported or empty study summary")
    assets = summary["assets"]
    groups = read_ledger(ledger_path, assets)
    reports = []
    for asset, spec in sorted(assets.items()):
        for split, span in spec["phases"].items():
            rows = groups.get((asset, split), [])
            selected = spec.get("selected")
            entry = dict(asset=asset, currency=spec["currency"], split=split,
                         candidate_id=selected["candidate_id"] if selected else None,
                         start=span["start"], end=span["end"], expected_rows=span["n"],
                         supplied_rows=len(rows))
            if not selected:
                entry["status"] = "insufficient_data" if spec["status"] == "insufficient_data" else "no_selected_candidate"
            elif (not rows or len(rows) != span["n"] or rows[0]["date"] != span["start"]
                  or rows[-1]["date"] != span["end"]):
                entry["status"] = "incomplete_selected_ledger"
            else:
                entry.update(summarize(rows, spec, split))
            reports.append(entry)
    return dict(schema="research-lab-performance-audit-v1", study_id=summary["study_id"],
                input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (summary_path, ledger_path)}, phases=reports)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_directory", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.results_directory)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if any(p["status"] == "incomplete_selected_ledger" for p in result["phases"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
