"""One frozen, reproducible retrospective research run; no live data or orders.

    python -m research_lab.run --freeze-commit <40-hex SHA> --output <new folder>

The protocol, all engine source, data manifest and catalogue must already be
committed byte-for-byte before any market-data return evaluation is allowed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import time

import numpy as np
import pandas as pd
import scipy

from research_lab import data, inference
from research_lab.backtest import buy_hold, select_validation, simulate_window
from research_lab.candidates import annual_volatility, catalogue, catalogue_bytes, raw_rules, signal_matrix

ROOT = Path(__file__).resolve().parents[1]
FROZEN_FILES = tuple("research_lab/" + name for name in
                     ("__init__.py", "candidates.py", "backtest.py", "run.py", "data.py", "inference.py",
                      "protocol.json", "data_manifest.json", "catalogue.json"))
METRIC_NAMES = ("n", "mean_daily", "annualized_mean", "cagr", "annual_vol", "sharpe", "max_drawdown",
                "turnover", "entries", "completed_trades", "total_return", "avg_exposure")


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8")


def verify_freeze(commit, *, root=ROOT):
    if type(commit) is not str or re.fullmatch("[0-9a-f]{40}", commit) is None:
        raise ValueError("immutable full commit SHA required")
    hashes = {}
    for relative in FROZEN_FILES:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("frozen source file missing or linked")
        raw = path.read_bytes()
        committed = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=root)
        if raw != committed:
            raise ValueError("research source changed after computation preregistration: " + relative)
        hashes[relative] = _hash(raw)
    if (root / "research_lab/catalogue.json").read_bytes() != catalogue_bytes():
        raise ValueError("candidate catalogue does not match frozen source")
    protocol = json.loads((root / "research_lab/protocol.json").read_bytes())
    if (protocol["assets"] != list(data.ASSETS)
            or protocol["data_manifest_sha256"] != data.manifest_digest(root=root)
            or protocol["configurations_per_asset"] != len(catalogue())
            or protocol["raw_rules_per_asset"] != len(raw_rules())
            or protocol["total_configurations"] != len(catalogue()) * len(data.ASSETS)
            or protocol["rebalance_bars"] != [1, 5, 21] or protocol["caps"] != [0.5, 1.0]
            or protocol["vol_targets"] != [None, 0.15] or protocol["warmup_bars"] != 500):
        raise ValueError("frozen protocol disagrees with catalogue or data manifest")
    return protocol, hashes


def phase_indices(dates, protocol):
    dates = np.asarray(dates, dtype=str)
    raw_index = np.arange(len(dates))
    windows = {}
    for name, span in protocol["splits"].items():
        included = (raw_index >= protocol["warmup_bars"]) & (dates <= span["end"])
        if span["start"] is not None:
            included &= dates >= span["start"]
        windows[name] = raw_index[included]
    return windows


def _phase_span(dates, indices):
    return dict(start=dates[int(indices[0])] if len(indices) else None,
                end=dates[int(indices[-1])] if len(indices) else None, n=len(indices))


def _metrics_return_path(values, annualization):
    values = np.asarray(values, dtype=float)
    equity = np.r_[1.0, np.cumprod(1 + values)]
    mean = float(values.mean())
    std = float(values.std(ddof=1))
    return dict(n=len(values), annualization=annualization, mean_daily=mean,
                cagr=float(equity[-1] ** (annualization / len(values)) - 1),
                annual_vol=std * np.sqrt(annualization),
                sharpe=mean / std * np.sqrt(annualization) if std > 0 else None,
                max_drawdown=float((equity / np.maximum.accumulate(equity) - 1).min()),
                total_return=float(equity[-1] - 1))


def run_study(*, freeze_commit, output, root=ROOT):
    # This verification occurs before loading or evaluating any market series.
    protocol, hashes = verify_freeze(freeze_commit, root=root)
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("new empty output directory required; never overwrite a completed or partial study")
    if output == root or not output.is_relative_to(root / "docs/research"):
        raise ValueError("research output must be an isolated directory under docs/research")
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    candidates = catalogue()
    series = data.load_assets(root=root)
    metadata = {asset: {k: v for k, v in values.items() if k not in ("close", "dates")}
                for asset, values in series.items()}
    _write_json(output / "run_manifest.json", dict(schema_version=1, freeze_commit=freeze_commit,
        frozen_file_sha256=hashes, protocol=protocol, data=metadata,
        environment=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__),
        purpose="retrospective exploratory internal holdout; no account, trading or live-validation path"))
    assets = {}
    phase_metrics = {}
    selections = {}
    windows_by_asset = {}
    for asset_number, asset in enumerate(data.ASSETS):
        item = series[asset]
        windows = phase_indices(item["dates"], protocol)
        windows_by_asset[asset] = windows
        ann = item["annualization"]
        if ann != protocol["annualization"][asset]:
            raise ValueError("annualization mismatch")
        cost = protocol["cost_bps_per_side"][asset] / 10000
        result = dict(status="evaluated", currency=item["currency"], annualization=ann,
                      cost_bps_per_side=protocol["cost_bps_per_side"][asset],
                      phases={name: _phase_span(item["dates"], idx) for name, idx in windows.items()},
                      candidate_count=len(candidates), economic_families=8, selected=None,
                      production_status="NOT_VALIDATED_FOR_PRODUCTION")
        assets[asset] = result
        insufficient = [name for name, idx in windows.items() if len(idx) < protocol["minimum_scored_rows"][name]]
        if insufficient:
            result.update(status="insufficient_data", reason="insufficient_scored_rows:" + ",".join(insufficient))
            selections[asset] = None
            continue
        print(f"TRAIN/VALIDATION {asset} ({len(candidates)} configurations)", flush=True)
        signals = signal_matrix(item["close"])
        vol = annual_volatility(item["close"], ann)
        train = simulate_window(item["close"], signals, vol, candidates, windows["train"],
                                annualization=ann, cost_per_side=cost)
        phase_metrics[asset] = {"train": train.metrics}
        del train
        validation = simulate_window(item["close"], signals, vol, candidates, windows["validation"],
                                     annualization=ann, cost_per_side=cost)
        phase_metrics[asset]["validation"] = validation.metrics
        benchmark = buy_hold(item["close"], windows["validation"], annualization=ann, cost_per_side=cost)
        chosen = select_validation(candidates, validation.metrics)
        selections[asset] = chosen
        result["eligible_validation_candidates"] = sum(m["mean_daily"] > 0 and m["completed_trades"] >= 20
            and m["sharpe"] is not None for m in validation.metrics)
        result["distinct_validation_return_paths"] = len({_hash(np.ascontiguousarray(validation.returns[:, i]).tobytes())
                                                        for i in range(len(candidates))})
        result["validation_family_test"] = inference.evaluate_validation(validation.returns,
            benchmark.returns[:, 0], ann, seed=protocol["seed"] + asset_number * 100)
        result["validation_benchmark"] = benchmark.metrics[0]
        if chosen is not None:
            result["selected"] = candidates[chosen].mapping()
            result["train"] = phase_metrics[asset]["train"][chosen]
            result["validation"] = validation.metrics[chosen]
        else:
            result["status"] = "no_eligible_validation_candidate"
        del validation, signals, vol, benchmark
    adjusted = inference.holm_adjust([assets[a].get("validation_family_test", {}).get("primary", {}).get("p_value", 1.0)
                                      for a in data.ASSETS])
    for asset, adjusted_p in zip(data.ASSETS, adjusted):
        assets[asset]["validation_holm_p"] = adjusted_p
    registry = dict(schema_version=1, freeze_commit=freeze_commit, candidate_catalogue_sha256=_hash(catalogue_bytes()),
                    selection_rule=protocol["selection"], holdout_evaluated=False,
                    selections={a: assets[a]["selected"] for a in data.ASSETS},
                    validation_holm={a: assets[a]["validation_holm_p"] for a in data.ASSETS})
    _write_json(output / "selection_registry.json", registry)
    selection_hash = _hash((output / "selection_registry.json").read_bytes())
    print("ALL VALIDATION CHOICES FROZEN; starting internal holdout", flush=True)

    all_columns = ["asset", "currency", "candidate_id", "family", "parameters", "rebalance_bars", "target_cap",
                   "volatility_target", "selected_on_validation"] + [f"{phase}_{name}" for phase in
                   ("train", "validation", "holdout") for name in METRIC_NAMES]
    daily_columns = ["date", "asset", "currency", "candidate_id", "split", "net_return", "gross_return",
                     "position", "held_weight", "turnover", "cost", "benchmark_return"]
    selected_holdout = {}
    with (output / "candidates_all.csv").open("w", newline="", encoding="utf-8") as fullfile, \
            (output / "selected_daily.csv").open("w", newline="", encoding="utf-8") as dailyfile:
        writer = csv.DictWriter(fullfile, fieldnames=all_columns, lineterminator="\n")
        writer.writeheader()
        daily = csv.DictWriter(dailyfile, fieldnames=daily_columns, lineterminator="\n")
        daily.writeheader()
        for asset_number, asset in enumerate(data.ASSETS):
            item, result = series[asset], assets[asset]
            if result["status"] == "insufficient_data":
                continue
            print(f"INTERNAL HOLDOUT {asset}", flush=True)
            ann, cost = item["annualization"], protocol["cost_bps_per_side"][asset] / 10000
            windows = windows_by_asset[asset]
            signals, vol = signal_matrix(item["close"]), annual_volatility(item["close"], ann)
            holdout = simulate_window(item["close"], signals, vol, candidates, windows["holdout"],
                                      annualization=ann, cost_per_side=cost)
            benchmark = buy_hold(item["close"], windows["holdout"], annualization=ann, cost_per_side=cost)
            result["holdout_benchmark"] = benchmark.metrics[0]
            chosen = selections[asset]
            for i, candidate in enumerate(candidates):
                row = dict(asset=asset, currency=item["currency"], candidate_id=candidate.candidate_id,
                    family=candidate.family, parameters=json.dumps(dict(candidate.parameters), sort_keys=True),
                    rebalance_bars=candidate.rebalance_bars, target_cap=candidate.target_cap,
                    volatility_target=candidate.volatility_target, selected_on_validation=i == chosen)
                for phase, records in (("train", phase_metrics[asset]["train"]),
                                       ("validation", phase_metrics[asset]["validation"]), ("holdout", holdout.metrics)):
                    row.update({f"{phase}_{key}": records[i][key] for key in METRIC_NAMES})
                writer.writerow(row)
            if chosen is not None:
                selected = candidates[chosen]
                result["holdout"] = holdout.metrics[chosen]
                result["holdout_inference"] = inference.holdout_diagnostics(holdout.returns[:, chosen],
                    benchmark.returns[:, 0], ann, seed=protocol["seed"] + asset_number * 100 + 1)
                result["stress"] = {}
                for multiplier in protocol["cost_stress_multipliers"]:
                    stress = simulate_window(item["close"], signals, vol, (selected,), windows["holdout"],
                        annualization=ann, cost_per_side=cost * multiplier)
                    result["stress"][f"cost_{multiplier:g}x"] = stress.metrics[0]
                stress = simulate_window(item["close"], signals, vol, (selected,), windows["holdout"],
                    annualization=ann, cost_per_side=cost, lag=2)
                result["stress"]["lag_2"] = stress.metrics[0]
                for phase, idx in windows.items():
                    trace = simulate_window(item["close"], signals, vol, (selected,), idx,
                        annualization=ann, cost_per_side=cost, capture=True)
                    bh = buy_hold(item["close"], idx, annualization=ann, cost_per_side=cost)
                    for step, raw_index in enumerate(idx):
                        daily.writerow(dict(date=item["dates"][int(raw_index)], asset=asset, currency=item["currency"],
                            candidate_id=selected.candidate_id, split=phase, net_return=trace.returns[step, 0],
                            benchmark_return=bh.returns[step, 0],
                            **{key: values[step, 0] for key, values in trace.trace.items()}))
                    if phase == "holdout":
                        selected_holdout[asset] = (tuple(item["dates"][int(i)] for i in idx), trace.returns[:, 0].copy(), bh.returns[:, 0].copy())
            else:
                selected_holdout[asset] = (tuple(item["dates"][int(i)] for i in windows["holdout"]),
                                           np.zeros(len(windows["holdout"])), benchmark.returns[:, 0].copy())
            del holdout, signals, vol, benchmark
    holdout_adjusted = inference.holm_adjust([assets[a].get("holdout_inference", {}).get("mean_diff_p_value", 1.0)
                                            for a in data.ASSETS])
    cash_adjusted = inference.holm_adjust([assets[a].get("holdout_inference", {}).get("mean_p_value", 1.0)
                                         for a in data.ASSETS])
    for asset, adjusted_p, cash_p in zip(data.ASSETS, holdout_adjusted, cash_adjusted):
        result = assets[asset]
        result["holdout_holm_p"] = adjusted_p
        result["holdout_cash_holm_p"] = cash_p
        if result["selected"] is None:
            result["research_label"] = result["status"]
            continue
        conditions = dict(validation_familywise=result["validation_holm_p"] <= 0.05,
                          holdout_vs_benchmark_familywise=adjusted_p <= 0.05,
                          positive_holdout_mean=result["holdout"]["mean_daily"] > 0,
                          positive_double_cost_mean=result["stress"]["cost_2x"]["mean_daily"] > 0,
                          sufficient_holdout_activity=result["holdout"]["completed_trades"] >= 30)
        result["research_gate_conditions"] = conditions
        result["research_label"] = "promising_exploratory" if all(conditions.values()) else "not_supported_by_preregistered_screen"
    basket_assets = protocol["basket"]["assets"]
    basket = dict(status="unavailable", currency="USD", interpretation=protocol["basket"]["status"])
    if all(a in selected_holdout for a in basket_assets):
        paths = [selected_holdout[a] for a in basket_assets]
        if all(path[0] == paths[0][0] for path in paths):
            wealth = np.column_stack([np.cumprod(1 + path[1]) for path in paths]).mean(axis=1)
            bhwealth = np.column_stack([np.cumprod(1 + path[2]) for path in paths]).mean(axis=1)
            returns = wealth / np.r_[1.0, wealth[:-1]] - 1
            bhreturns = bhwealth / np.r_[1.0, bhwealth[:-1]] - 1
            basket.update(status="descriptive_only", assets=basket_assets,
                          selected_metrics=_metrics_return_path(returns, 252),
                          buy_hold_metrics=_metrics_return_path(bhreturns, 252))
            with (output / "usd_basket_daily.csv").open("w", newline="", encoding="utf-8") as stream:
                out = csv.writer(stream, lineterminator="\n")
                out.writerow(("date", "currency", "selected_return", "buy_hold_return"))
                out.writerows((date, "USD", float(r), float(b)) for date, r, b in zip(paths[0][0], returns, bhreturns))
    summary = dict(schema_version=1, study_id=protocol["study_id"], mode="retrospective_exploratory_internal_holdout",
        production_status="NOT_VALIDATED_FOR_PRODUCTION", freeze_commit=freeze_commit,
        protocol_sha256=hashes["research_lab/protocol.json"], data_manifest_sha256=hashes["research_lab/data_manifest.json"],
        catalogue_sha256=_hash(catalogue_bytes()), selection_registry_sha256=selection_hash,
        raw_rule_count=len(raw_rules()), configurations_per_asset=len(candidates),
        declared_asset_configurations=len(candidates) * len(data.ASSETS),
        evaluated_asset_configurations=sum(r["status"] != "insufficient_data" for r in assets.values()) * len(candidates),
        economic_family_count=8, warmup_bars=protocol["warmup_bars"], assets=assets, usd_basket=basket,
        owner_policy_status=protocol["owner_policy"], elapsed_seconds=round(time.perf_counter() - start, 3),
        limitations=["Previously inspected historical caches; no independent or prospective confirmation.",
                     "Long/cash fractional shares, close-only next-close execution and synthetic cost floors.",
                     "Per-asset native currency; no mixed-currency or realized account P&L claim.",
                     "No leverage, account credentials, live data, order routing, intraday stop or limit-fill validation."])
    if _hash((output / "selection_registry.json").read_bytes()) != selection_hash:
        raise AssertionError("pre-holdout selection registry changed")
    _write_json(output / "summary.json", summary)
    print(json.dumps(dict(status="complete", configurations=summary["evaluated_asset_configurations"],
                          selected=sum(r["selected"] is not None for r in assets.values()),
                          promising=sum(r["research_label"] == "promising_exploratory" for r in assets.values()),
                          elapsed_seconds=summary["elapsed_seconds"])), flush=True)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    run_study(freeze_commit=args.freeze_commit, output=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
