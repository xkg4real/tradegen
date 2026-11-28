"""Command-line interface for `qlib_lab` (research only, zero network, explicit local paths).

Subcommands:
- `qrun`             : Run a declarative YAML/JSON experiment task into FileGovernanceRecorder & FamilyLedger.
- `rolling`          : Expand a task template via RollingGen and execute RollingTrainer.
- `routine`          : Execute an OnlineManager Champion vs Shadow Challenger routine step at `--as-of`.
- `propose-revision` : Generate bounded YAML/JSON TaskGen revision proposals from gate/drift reports.
- `export-snapshot`  : Export FrozenModelSpec + probabilities to `tradegen-direction-forecast-v1` + sidecars.
- `replay-br26`      : Replay exported snapshots + study JSON through `direction_forecast_adapter`.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import yaml

from core.isolation import checked_target
from qlib_lab import RESEARCH_FLAGS
from qlib_lab.data import DataHandlerLP, DatasetH, ExpressionDataLoader, StaticDataLoader
from qlib_lab.models import FrozenModelSpec, Model
from qlib_lab.online import (
    DriftMonitor,
    OnlineManager,
    RevisionProposer,
    RollingGen,
    RollingTrainer,
    SnapshotExporter,
)
from qlib_lab.registry import init_instance_by_config
from qlib_lab.workflow import R, RecordTemp
from tools.research import adaptive_bid_gap_preview as br26_preview
from tools.research import direction_forecast_adapter as br26_adapter


def _load_structured_file(path: Path) -> dict[str, Any]:
    target = checked_target(Path(path), "config_file")
    text = target.read_text(encoding="utf-8")
    if target.suffix.lower() in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration file {target} must contain a top-level mapping")
    return data


def _load_panel_file(path: Path) -> pd.DataFrame:
    target = checked_target(Path(path), "panel_file")
    if target.suffix.lower() == ".csv":
        df = pd.read_csv(target)
    else:
        payload = json.loads(target.read_text(encoding="utf-8"))
        rows = payload["rows"] if isinstance(payload, dict) and "rows" in payload else payload
        df = pd.DataFrame(rows)
    return df


def _hydrate_task_data(task: dict[str, Any], panel_path: Path | None) -> dict[str, Any]:
    if panel_path is None:
        return task
    raw_df = _load_panel_file(panel_path)
    ds_kw = task.setdefault("dataset", {}).setdefault("kwargs", {})
    handler_cfg = ds_kw.setdefault("handler", {"class": "DataHandlerLP", "kwargs": {}})
    if isinstance(handler_cfg, dict):
        h_kw = handler_cfg.setdefault("kwargs", {})
        dl_cfg = h_kw.get("data_loader")
        if isinstance(dl_cfg, dict) and dl_cfg.get("class") == "ExpressionDataLoader":
            dl_cfg.setdefault("kwargs", {})["raw_data"] = raw_df
        elif dl_cfg is None:
            h_kw["data_loader"] = StaticDataLoader(raw_df)
    return task


def run_qrun(
    *,
    config_path: Path,
    state_dir: Path,
    run_utc: str,
    panel_path: Path | None = None,
    experiment_name: str = "qrun_exp",
) -> dict[str, Any]:
    cfg = _load_structured_file(config_path)
    task = _hydrate_task_data(cfg.get("task", cfg), panel_path)

    dataset: DatasetH = init_instance_by_config(task["dataset"], accept_types=DatasetH)
    model: Model = init_instance_by_config(task["model"], accept_types=Model)
    reweighter = None
    if task.get("reweighter"):
        from qlib_lab.models.base import Reweighter
        reweighter = init_instance_by_config(task["reweighter"], accept_types=Reweighter)

    with R.start(experiment_name=experiment_name, uri=state_dir, run_utc=run_utc) as rec:
        model.fit(dataset, reweighter=reweighter)
        tc = dataset.effective_training_cutoff(include_valid="valid" in dataset.segments)
        proc_states = (
            dataset.handler.export_processor_states()
            if isinstance(dataset.handler, DataHandlerLP)
            else None
        )
        spec = model.to_frozen_spec(
            model_name=str(task.get("model_name") or model.__class__.__name__.lower()),
            model_version=str(task.get("model_version") or "0.1.0"),
            training_cutoff=tc,
            frozen_at=tc,
            processor_states=proc_states,
        )
        pred = model.predict(dataset, "test")
        rec.save_objects(frozen_model=spec, pred=pred)
        if model.task_type == "direction":
            rec.save_objects(proba=model.predict_proba(dataset, "test"))

        record_outputs: list[dict[str, Any]] = []
        for r_cfg in task.get("record", []):
            r_inst: RecordTemp = init_instance_by_config(
                r_cfg,
                accept_types=RecordTemp,
                extra_kwargs={"model": model, "dataset": dataset, "recorder": rec},
            )
            record_outputs.append(r_inst.generate(recorder=rec))

        return {
            "schema": "tradegen-qlib-cli-qrun-v1",
            "recorder_id": rec.id,
            "model_sha256": spec.model_sha256,
            "n_test_predictions": int(len(pred)),
            "records": record_outputs,
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }


def run_rolling(
    *,
    config_path: Path,
    state_dir: Path,
    run_utc: str,
    panel_path: Path | None = None,
    step: int = 24,
    rtype: str = RollingGen.ROLL_EX,
    train_mode: str = "retrain",
    embargo_bars: int = 1,
    horizon_bars: int = 2,
) -> dict[str, Any]:
    cfg = _load_structured_file(config_path)
    task = _hydrate_task_data(cfg.get("task", cfg), panel_path)
    probe_ds: DatasetH = init_instance_by_config(task["dataset"], accept_types=DatasetH)
    cal = probe_ds._calendar()

    rgen = RollingGen(
        calendar=cal,
        step=step,
        rtype=rtype,
        embargo_bars=embargo_bars,
        horizon_bars=horizon_bars,
    )
    tasks = rgen.generate(task)
    trainer = RollingTrainer(
        uri=state_dir,
        experiment_name="cli_rolling",
        train_mode=train_mode,
        run_utc=run_utc,
    )
    res = trainer.run(tasks, shared_handler=probe_ds.handler if isinstance(probe_ds.handler, DataHandlerLP) else None)
    return res.to_summary_dict()


def run_routine(
    *,
    config_path: Path,
    panel_path: Path,
    champion_path: Path,
    challenger_paths: list[str],
    state_dir: Path,
    as_of: str,
    run_utc: str,
) -> dict[str, Any]:
    cfg = _load_structured_file(config_path)
    task = _hydrate_task_data(cfg.get("task", cfg), panel_path)
    dataset: DatasetH = init_instance_by_config(task["dataset"], accept_types=DatasetH)

    champ_spec = FrozenModelSpec.load(champion_path)
    ch_map: dict[str, FrozenModelSpec] = {}
    for item in challenger_paths:
        if "=" in item:
            name, _, p_str = item.partition("=")
            ch_map[name] = FrozenModelSpec.load(Path(p_str))
        else:
            p = Path(item)
            ch_map[p.stem] = FrozenModelSpec.load(p)

    dm = DriftMonitor()
    tr_feat = dataset.prepare("train", col_set="feature", data_key=DataHandlerLP.DK_I)
    dm.fit_reference(tr_feat)

    mgr = OnlineManager(
        state_dir=state_dir,
        champion_spec=champ_spec,
        challengers=ch_map,
        drift_monitor=dm,
    )
    return mgr.routine(as_of, dataset, run_utc=run_utc)


def run_propose_revision(
    *,
    task_path: Path,
    output_dir: Path,
    gate_report_path: Path | None = None,
    drift_report_path: Path | None = None,
) -> dict[str, Any]:
    base_cfg = _load_structured_file(task_path)
    task = base_cfg.get("task", base_cfg)
    gate_rep = _load_structured_file(gate_report_path) if gate_report_path is not None else None
    drift_rep = _load_structured_file(drift_report_path) if drift_report_path is not None else None

    proposer = RevisionProposer(gate_report=gate_rep, drift_report=drift_rep)
    written = proposer.write_proposals(task, output_dir)
    return {
        "schema": "tradegen-qlib-cli-proposals-v1",
        "n_proposals": len(written),
        "files": [{"json": w["json_path"], "yaml": w["yaml_path"], "target": w["proposal"]["trigger_target"]} for w in written],
        "research_flags": dict(RESEARCH_FLAGS),
        **RESEARCH_FLAGS,
    }


def run_export_snapshot(
    *,
    frozen_model_path: Path,
    config_path: Path,
    panel_path: Path,
    output_path: Path,
    producer: str = "qlib-lab",
    horizon_seconds: int = 7200,
    hurdle_bps: int = 10,
    generated_at: int | None = None,
) -> dict[str, Any]:
    spec = FrozenModelSpec.load(frozen_model_path)
    model = Model.from_frozen_spec(spec)
    cfg = _load_structured_file(config_path)
    task = _hydrate_task_data(cfg.get("task", cfg), panel_path)
    dataset: DatasetH = init_instance_by_config(task["dataset"], accept_types=DatasetH)

    proba = model.predict_proba(dataset, "test")
    exporter = SnapshotExporter(
        producer=producer,
        horizon_seconds=horizon_seconds,
        hurdle_bps=hurdle_bps,
    )
    res = exporter.export(
        frozen_spec=spec,
        probabilities=proba,
        output_path=output_path,
        generated_at=generated_at,
    )
    return {
        "schema": "tradegen-qlib-cli-export-v1",
        "snapshot_path": str(res["snapshot_path"]),
        "snapshot_sha256": res["snapshot_sha256"],
        "manifest_path": str(res["manifest_path"]),
        "interface_note_path": str(res["interface_note_path"]),
        "counts": res["manifest"]["counts"],
        "research_flags": dict(RESEARCH_FLAGS),
        **RESEARCH_FLAGS,
    }


def run_replay_br26(*, replay_study_path: Path, snapshot_args: list[str]) -> dict[str, Any]:
    snapshots = []
    for item in snapshot_args:
        path_str, sep, digest = item.rpartition("=")
        if sep != "=":
            raise ValueError(f"Expected PATH=SHA256 for --snapshot, got {item!r}")
        left = br26_adapter.MAX_FORECASTS - sum(len(s["forecasts"]) for s in snapshots)
        snapshots.append(br26_adapter.read_snapshot(Path(path_str), digest, left))
    study_doc = br26_preview.read_input(Path(replay_study_path))
    return br26_adapter.run(study_doc, snapshots)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qlib_lab", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_qrun = sub.add_parser("qrun", help="Run declarative experiment config")
    p_qrun.add_argument("--config", type=Path, required=True)
    p_qrun.add_argument("--state-dir", type=Path, required=True)
    p_qrun.add_argument("--panel", type=Path, default=None)
    p_qrun.add_argument("--experiment-name", type=str, default="qrun_exp")
    p_qrun.add_argument("--run-utc", type=str, default=None)

    p_roll = sub.add_parser("rolling", help="Run RollingGen + RollingTrainer")
    p_roll.add_argument("--config", type=Path, required=True)
    p_roll.add_argument("--state-dir", type=Path, required=True)
    p_roll.add_argument("--panel", type=Path, default=None)
    p_roll.add_argument("--step", type=int, default=24)
    p_roll.add_argument("--rtype", choices=[RollingGen.ROLL_EX, RollingGen.ROLL_SD], default=RollingGen.ROLL_EX)
    p_roll.add_argument("--train-mode", choices=["retrain", "finetune"], default="retrain")
    p_roll.add_argument("--embargo-bars", type=int, default=1)
    p_roll.add_argument("--horizon-bars", type=int, default=2)
    p_roll.add_argument("--run-utc", type=str, default=None)

    p_rout = sub.add_parser("routine", help="Run OnlineManager routine at --as-of")
    p_rout.add_argument("--config", type=Path, required=True)
    p_rout.add_argument("--panel", type=Path, required=True)
    p_rout.add_argument("--champion", type=Path, required=True)
    p_rout.add_argument("--challenger", action="append", default=[])
    p_rout.add_argument("--state-dir", type=Path, required=True)
    p_rout.add_argument("--as-of", type=str, required=True)
    p_rout.add_argument("--run-utc", type=str, default=None)

    p_prop = sub.add_parser("propose-revision", help="Generate bounded revision task proposals")
    p_prop.add_argument("--task", type=Path, required=True)
    p_prop.add_argument("--output-dir", type=Path, required=True)
    p_prop.add_argument("--gate-report", type=Path, default=None)
    p_prop.add_argument("--drift-report", type=Path, default=None)

    p_exp = sub.add_parser("export-snapshot", help="Export tradegen-direction-forecast-v1 snapshot")
    p_exp.add_argument("--frozen-model", type=Path, required=True)
    p_exp.add_argument("--config", type=Path, required=True)
    p_exp.add_argument("--panel", type=Path, required=True)
    p_exp.add_argument("--output", type=Path, required=True)
    p_exp.add_argument("--producer", type=str, default="qlib-lab")
    p_exp.add_argument("--horizon-seconds", type=int, default=7200)
    p_exp.add_argument("--hurdle-bps", type=int, default=10)
    p_exp.add_argument("--generated-at", type=int, default=None)

    p_rep = sub.add_parser("replay-br26", help="Replay snapshots through direction_forecast_adapter")
    p_rep.add_argument("--replay", type=Path, required=True)
    p_rep.add_argument("--snapshot", action="append", required=True, metavar="PATH=SHA256")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Wall-clock fallback lives ONLY here in cli.py:main() when --run-utc / --generated-at is omitted!
    now_dt = datetime.now(timezone.utc).replace(microsecond=0)
    default_run_utc = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.command == "qrun":
        out = run_qrun(
            config_path=args.config,
            state_dir=args.state_dir,
            run_utc=args.run_utc or default_run_utc,
            panel_path=args.panel,
            experiment_name=args.experiment_name,
        )
    elif args.command == "rolling":
        out = run_rolling(
            config_path=args.config,
            state_dir=args.state_dir,
            run_utc=args.run_utc or default_run_utc,
            panel_path=args.panel,
            step=args.step,
            rtype=args.rtype,
            train_mode=args.train_mode,
            embargo_bars=args.embargo_bars,
            horizon_bars=args.horizon_bars,
        )
    elif args.command == "routine":
        out = run_routine(
            config_path=args.config,
            panel_path=args.panel,
            champion_path=args.champion,
            challenger_paths=args.challenger,
            state_dir=args.state_dir,
            as_of=args.as_of,
            run_utc=args.run_utc or default_run_utc,
        )
    elif args.command == "propose-revision":
        out = run_propose_revision(
            task_path=args.task,
            output_dir=args.output_dir,
            gate_report_path=args.gate_report,
            drift_report_path=args.drift_report,
        )
    elif args.command == "export-snapshot":
        out = run_export_snapshot(
            frozen_model_path=args.frozen_model,
            config_path=args.config,
            panel_path=args.panel,
            output_path=args.output,
            producer=args.producer,
            horizon_seconds=args.horizon_seconds,
            hurdle_bps=args.hurdle_bps,
            generated_at=args.generated_at,
        )
    elif args.command == "replay-br26":
        out = run_replay_br26(replay_study_path=args.replay, snapshot_args=args.snapshot)
        if out.get("status") == "REJECTED":
            sys.stdout.write(json.dumps(out, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n")
            return 2
    else:
        parser.error(f"Unknown command {args.command!r}")
        return 2

    sys.stdout.write(json.dumps(out, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
