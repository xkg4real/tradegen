"""Private, offline prospective DIDM study journal. Issuance uses the local clock."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import time

from tools.research import adaptive_bid_gap_preview as preview
from tools.research import direction_feature_builder as features
from tools.research import direction_forecast_adapter as adapter
from tools.research import direction_forecast_writer as writer
from tools.research import direction_model_fit as fit
from tools.research import direction_stage1_evaluator as stage1
from tools.research import direction_stage2_replay as stage2
from tools.research import upbit_quote_recorder as quotes
from tools.research import prospective_direction_inputs as inputs
from tools.research._study_common import (
    HEX64_RE, RESEARCH_FLAGS, HashChainedLog, StudyError, atomic_publish_json_ascii,
    canonical_ascii_str, check_safe_path, kst_date_iso, parse_epoch_int, read_strict_json_file,
    read_verified_chained_log, require, sha256_ascii,
)

JOURNAL = "prospective.jsonl"
ROLES = ("M", "B1", "B0")
PINS = dict(zip(ROLES, ("forecast_model", "b1_forecast_model", "b0_forecast_model")))
LIMIT = 64 * 1024 * 1024


def private_dir(path):
    path = check_safe_path(path)
    require(not any(p.casefold().startswith("onedrive") for p in path.parts)
            and not any((p / ".git").is_file() or (p / ".git" / "HEAD").is_file() for p in (path, *path.parents)),
            "PRIVATE_ARCHIVE_REQUIRED")
    return path


def read_doc(path):
    data, _ = read_strict_json_file(path, max_bytes=LIMIT)
    require(type(data) is dict, "OBJECT_REQUIRED")
    return data


def load(root, digest):
    require(type(digest) is str and HEX64_RE.fullmatch(digest), "EVIDENCE_DIGEST_INVALID")
    data = read_doc(root / (digest + ".json"))
    require(sha256_ascii(data) == digest, "EVIDENCE_HASH_MISMATCH")
    return data


def seal(root, data):
    digest = sha256_ascii(data)
    dest = root / (digest + ".json")
    if dest.exists():
        load(root, digest)
    else:
        atomic_publish_json_ascii(dest, data, max_bytes=LIMIT)
    return digest


def _integer(obj, field, lo, hi):
    return parse_epoch_int(obj[field], low=lo, high=hi, error_code="INVALID_" + field.upper())


def register(root, study, prerequisite_refs, fit_dir, inputs_path, now):
    supported = adapter.STUDY_KEYS | set(PINS.values()) | {
        "evaluation_end", "interim_at", "ceiling_y", "criterion2_margin", "bootstrap_replications",
        "bootstrap_seed", "z_value", "attempt_number", "attempt_budget", "b2_seed", "min_d1_events",
        "pinned_upstream_identities", "stage1_writer_mode", "latch_convention", "ceiling_mode",
        "stage2_start", "stage2_end", "quote_interval_seconds", "min_daily_quote_coverage",
        "min_daily_live_forecast_coverage", "early_warning_window_seconds", "max_excess_alerts_per_day",
        "min_stage2_days", "min_early_warnings"}
    require(set(study) <= supported, "UNSUPPORTED_STUDY_TERM")
    start = _integer(study, "evaluation_start", now + 1, 2**39)
    step = _integer(study, "step_seconds", 1, 86400)
    end = _integer(study, "evaluation_end", start + 2 * study["horizon_seconds"], start + 1023 * step)
    require((end - start) % (2 * step) == 0 and study["interim_at"] == (start + end) // 2, "INTERIM_GRID_INVALID")
    require(set(prerequisite_refs) == {"O28", "O38", "M9-T4", "section10"}
            and all(type(v) is str and HEX64_RE.fullmatch(v) for v in prerequisite_refs.values()),
            "PRIVATE_PREREQUISITE_REFERENCES_REQUIRED")
    roles = {role: read_doc(fit_dir / f"model_{role}.json") for role in ROLES}
    report = read_doc(fit_dir / "fit_report.json")
    require(report.get("format") == fit.FIT_REPORT_FORMAT and all(report.get(k) is v for k, v in RESEARCH_FLAGS.items())
            and sha256_ascii({k: v for k, v in report.items() if k != "report_sha256"}) == report.get("report_sha256")
            and type(report.get("m11_t4_call_estimate")) is dict, "INVALID_FIT_REPORT")
    study = dict(study)
    for role, model in roles.items():
        pin = report["models"][role]
        fit.verify_model_artifact(model, pin["sha256"])
        require(pin == {k: model[k] for k in ("name", "version", "sha256")} and model["role"] == role
                and all(model[k] == study[k] for k in ("market", "step_seconds", "horizon_seconds", "hurdle_bps"))
                and model["frozen_at"] == report["frozen_at"] <= now
                and model["training_cutoff"] == report["training_cutoff"], "FIT_STUDY_MISMATCH")
        require(study.setdefault(PINS[role], pin) == pin, "FIT_MODEL_PIN_MISMATCH")
    m = roles["M"]
    require(set(m["feature_names"]) - set(roles["B1"]["feature_names"]), "NO_INCREMENTAL_FEATURE")
    require(study.setdefault("pinned_upstream_identities", m["upstream_identities"]) == m["upstream_identities"],
            "UPSTREAM_IDENTITY_MISMATCH")
    adapter.study_config({k: study[k] for k in adapter.STUDY_KEYS}, preview.bounds(study["ceiling_y"]), m)
    require(study["stage1_writer_mode"] in ("batch", "live") and study["latch_convention"] in ("17a", "17b")
            and study["ceiling_mode"] in ("7a", "7b"), "UNSUPPORTED_STUDY_TERMS")
    for k in ("criterion2_margin", "max_excess_alerts_per_day"):
        require(type(study[k]) in (float, int) and study[k] >= 0, "INVALID_" + k.upper())
    for k in ("min_daily_quote_coverage", "min_daily_live_forecast_coverage"):
        require(type(study[k]) in (float, int) and 0 < study[k] <= 1, "INVALID_" + k.upper())
    for k in ("early_warning_window_seconds", "quote_interval_seconds"):
        _integer(study, k, 1, 86400)
    require(86400 % study["quote_interval_seconds"] == 0, "QUOTE_CADENCE_INVALID")
    _integer(study, "min_early_warnings", 1, 2**31)
    _integer(study, "b2_seed", 0, 2**32 - 1)
    _integer(study, "bootstrap_seed", 0, 2**32 - 1)
    _integer(study, "attempt_number", 1, _integer(study, "attempt_budget", 1, 2**31))
    require(study.setdefault("bootstrap_replications", 10000) == 10000, "BOOTSTRAP_PLAN_MISMATCH")
    require(type(study.get("z_value", stage1.DEFAULT_Z95)) in (int, float)
            and study.get("z_value", stage1.DEFAULT_Z95) >= stage1.DEFAULT_Z95, "INVALID_CONFIDENCE_BOUND")
    stage2_start = _integer(study, "stage2_start", end + 1, 2**39)
    stage2_end = _integer(study, "stage2_end", stage2_start + 86400, 2**39)
    require((stage2_start + 9 * 3600) % 86400 == 0 and (stage2_end - stage2_start) % 86400 == 0,
            "FULL_KST_DAYS_REQUIRED")
    _integer(study, "min_stage2_days", 1, (stage2_end - stage2_start) // 86400)
    table, hist, sources = inputs.rebuild(inputs_path, m, study, now, training=True)
    require(m["name"].endswith("-m"), "INVALID_MODEL_FAMILY")
    reproduced = fit.fit_and_freeze_models(
        feature_table=table, bars=hist["bars"], train_start=report["train_start"],
        train_end=report["train_end"], frozen_at=report["frozen_at"], horizon_seconds=study["horizon_seconds"],
        hurdle_bps=study["hurdle_bps"], l2_penalty=m["l2_penalty"], model_name_prefix=m["name"][:-2],
        model_version=m["version"], min_d1_events=study.get("min_d1_events", 8),
        heldout_seconds=report["m11_t4_call_estimate"]["heldout_seconds"])
    require(reproduced == {**roles, "report": report}, "TRAINING_EVIDENCE_DOES_NOT_REPRODUCE_FIT")
    return {"kind": "registered", "at": now, "terms": seal(root, study), "prerequisites": seal(root, prerequisite_refs),
            "training_history": seal(root, hist), "training_features": seal(root, table), "sources": seal(root, sources),
            "models": {r: seal(root, model) for r, model in roles.items()}, "fit": seal(root, report)}


def price_ancestor(root, entries):
    for event in reversed(entries):
        if "price_manifest" in event:
            return load(root, event["price_manifest"])["archive_head_sha256"]
        if "sources" in event:
            return load(root, event["sources"])["price_manifests"][-1]["archive_head_sha256"]
    raise StudyError("PRICE_ANCHOR_MISSING")


def issue(root, entries, study, phase, inputs_path, now):
    first = entries[0]
    model = load(root, first["models"]["M"])
    last_input = next(e for e in reversed(entries) if "sources" in e)
    last_head = load(root, last_input["sources"])["run_log_head"]
    table, hist, sources = inputs.rebuild(inputs_path, model, study, now, expected_ancestor=last_head,
                                         price_ancestor=price_ancestor(root, entries))
    verify_history(study, hist, now + 1)
    features.verify_feature_table(table)
    require(all(table[k] == model[k] for k in ("feature_names", "feature_definitions", "upstream_identities",
                                                "feature_builder_commit")), "FROZEN_FEATURE_CONTRACT_CHANGED")
    names = model["feature_names"]
    for row in table["rows"]:
        require(type(row["as_of"]) is int and row["as_of"] <= now and type(row["features"]) is dict
                and set(row["features"]) == set(names) and type(row["complete"]) is bool
                and row["complete"] == all(type(row["features"][k]) in (int, float) for k in names),
                "FEATURE_ROW_INVALID")
    timestamps = [r["as_of"] for r in table["rows"]]
    require(timestamps == sorted(set(timestamps)), "FEATURE_GRID_INVALID")
    if phase == "stage1":
        start, stop = study["evaluation_start"], study["evaluation_end"] - study["horizon_seconds"]
        mode = study["stage1_writer_mode"]
        if not gate(entries, "interim"):
            stop = study["interim_at"] - study["horizon_seconds"]
    else:
        start, stop, mode = study["stage2_start"], study["stage2_end"] - 1, "live"
    step = study["step_seconds"]
    already = [e for e in entries if e["kind"] == phase + "_forecast"]
    start_at = already[-1]["last_as_of"] + step if already else start
    available = [t for t in timestamps if start_at <= t <= stop]
    require(available and all((t - start) % step == 0 for t in available), "NO_NEW_GRID_ROWS")
    if mode == "live":
        available = [available[-1]]
        require(now < available[0] + step, "LIVE_ROW_ALREADY_STALE")
    role_docs = {}
    for role in (ROLES if phase == "stage1" else ROLES[:2]):
        artifact = load(root, first["models"][role])
        snap, receipt = writer.build_forecasts_from_model(
            artifact=artifact, feature_table=table, issued_at=now, mode=mode,
            start_as_of=available[0], end_as_of=available[-1])
        role_docs[role] = {"forecast": seal(root, snap), "manifest": seal(root, receipt)}
    return {"kind": phase + "_forecast", "at": now, "features": seal(root, table),
            "sources": seal(root, sources), "input_history": seal(root, hist),
            "first_as_of": available[0], "last_as_of": available[-1], "models": role_docs}


def gate(evidence, name):
    return next((e for e in evidence if e["kind"] == name), None)


def snapshots(root, entries, role, phases):
    inputs = [e for e in entries if e["kind"] in phases]
    pairs = [(load(root, e["models"][role]["forecast"]), e["at"]) for e in inputs]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def verify_history(study, hist, now):
    require(hist["scope"] == study["scope"] and hist["source_id"] == study["source_id"], "PRICE_SOURCE_CHANGED")
    adapter.price_record(hist, study["step_seconds"], now)


def score_stage1(root, entries, study, hist, mode, now):
    boundary = study["interim_at"] if mode == "interim" else study["evaluation_end"]
    require(now > boundary and (mode != "interim" or now < study["evaluation_end"]), "EVALUATION_WINDOW_CLOSED_OR_EARLY")
    require(mode == "interim" or gate(entries, "interim") is not None, "INTERIM_MISSING")
    verify_history(study, hist, now)
    require(hist["bars"][-1]["end"] == boundary, "PRICE_HISTORY_END_MISMATCH")
    if mode == "final":
        prior = load(root, gate(entries, "interim")["history"])
        by_end = {b["end"]: b for b in hist["bars"]}
        require(all(by_end.get(b["end"]) == b for b in prior["bars"] if b["end"] >= study["evaluation_start"]),
                "PREVIOUS_PRICE_REVISED")
    captures = [e for e in entries if e["kind"] == "stage1_forecast"]
    require(captures, "NO_FORECASTS_CAPTURED")
    # Measure coverage on exactly the rows used for forecasts. Never substitute a later feature rebuild.
    rows = []
    for e in captures:
        table = load(root, e["features"])
        rows.extend(r for r in table["rows"] if e["first_as_of"] <= r["as_of"] <= e["last_as_of"])
    table = {**table, "rows": rows, "row_count": len(rows), "complete_row_count": sum(r["complete"] for r in rows)}
    table["missing_row_count"] = len(rows) - table["complete_row_count"]
    table["table_sha256"] = sha256_ascii({k: v for k, v in table.items() if k != "table_sha256"})
    kwargs = {}
    for role in ROLES:
        docs, times = snapshots(root, entries, role, {"stage1_forecast"})
        kwargs[role.lower() + "_snapshots"] = docs
        kwargs[role.lower() + "_receipt_times"] = times
    report = stage1.evaluate_stage1(study=study, history=hist, feature_table=table, mode=mode, evaluated_at=now, **kwargs)
    return {"kind": mode, "at": now, "outcome": report["outcome"], "report": seal(root, report),
            "history": seal(root, hist), "scored_features": seal(root, table)}


def record_day(root, entries, study, doc, ceiling, now):
    quotes.verify_daily_quotes(doc)
    day = date.fromisoformat(doc["kst_date"])
    day_start = (day - date(1970, 1, 1)).days * 86400 - 9 * 3600
    require(study["stage2_start"] <= day_start < study["stage2_end"] and day_start + 86400 <= now,
            "INCOMPLETE_OR_OUT_OF_WINDOW_DAY")
    expected = 86400 // study["quote_interval_seconds"]
    require(doc["expected_observations"] == expected and doc["interval_seconds"] == study["quote_interval_seconds"]
            and doc["market"] == study["market"] and doc["scope"] == study["scope"], "QUOTE_STUDY_MISMATCH")
    obs = doc["observations"]
    seconds = [o["as_of"] for o in obs]
    require(doc["observation_count"] == len(obs) <= expected and seconds == sorted(set(seconds))
            and all(day_start <= t < day_start + 86400 for t in seconds)
            and len({(t - day_start) // doc["interval_seconds"] for t in seconds}) == len(seconds), "QUOTE_DAY_INVALID")
    require(set(ceiling) == {"kst_date", "events", "initial_signed_y", "source_sha256"}
            and ceiling["kst_date"] == doc["kst_date"] and type(ceiling["events"]) is list
            and type(ceiling["source_sha256"]) is str and HEX64_RE.fullmatch(ceiling["source_sha256"]), "CEILING_COVERAGE_REQUIRED")
    preview.bounds(ceiling["initial_signed_y"])
    times = []
    for ev in ceiling["events"]:
        require(set(ev) == {"at", "signed_y"}, "INVALID_S6_EVENT")
        times.append(parse_epoch_int(ev["at"], low=day_start + 1, high=day_start + 86399))
        preview.bounds(ev["signed_y"])
    require(times == sorted(set(times)), "INVALID_S6_EVENT")
    require(not any(e["kind"] == "quote_day" and e["date"] == doc["kst_date"] for e in entries), "DAY_ALREADY_CAPTURED")
    return {"kind": "quote_day", "at": now, "date": doc["kst_date"], "quotes": seal(root, doc),
            "ceiling": seal(root, ceiling)}


def score_stage2(root, entries, study, now):
    require(now >= study["stage2_end"], "STAGE2_NOT_FINISHED")
    days = sorted((e for e in entries if e["kind"] == "quote_day"), key=lambda e: e["date"])
    dates = [kst_date_iso(t) for t in range(study["stage2_start"], study["stage2_end"], 86400)]
    missing_days = sorted(set(dates) - {e["date"] for e in days})
    live_seen = any(e["kind"] == "stage2_forecast" for e in entries)
    if missing_days or not live_seen:
        report = {"format": stage2.STAGE2_REPORT_FORMAT, **RESEARCH_FLAGS, "outcome": "INCONCLUSIVE",
                  "stop_rule": "S7", "reason": "MISSING_CAPTURE", "missing_quote_or_ceiling_days": missing_days,
                  "any_live_forecast_capture": live_seen, "passed_criterion3": False, "execution_costs_measured": False,
                  "m11_t5_fill_check_closed": False}
        report["report_sha256"] = sha256_ascii(report)
        return {"kind": "stage2_review", "at": now, "outcome": report["outcome"], "report": seal(root, report)}
    events = []
    for day in days:
        coverage = load(root, day["ceiling"])
        start = (date.fromisoformat(day["date"]) - date(1970, 1, 1)).days * 86400 - 9 * 3600
        events.append({"at": start, "signed_y": coverage["initial_signed_y"]})
        events.extend(coverage["events"])
    final = gate(entries, "final")
    forecasts = {}
    for role in ROLES[:2]:
        docs, times = snapshots(root, entries, role, {"stage1_forecast", "stage2_forecast"})
        forecasts[role.lower() + "_snapshots"] = docs
        forecasts[role.lower() + "_receipt_times"] = times
    report = stage2.run_stage2_replay(study=study, stage1_report=load(root, final["report"]),
        stage1_history=load(root, final["history"]), daily_quote_records=[load(root, e["quotes"]) for e in days],
        ceiling_events=events, **forecasts)
    return {"kind": "stage2_review", "at": now, "outcome": report["outcome"], "report": seal(root, report)}


def advance(root, command, **opts):
    root = private_dir(root)
    with HashChainedLog(root, JOURNAL) as log:
        now = int(time.time())
        entries = [r["data"] for r in log.entries]
        if command == "register":
            require(not entries, "STUDY_ALREADY_REGISTERED")
            event = register(root, read_doc(opts["terms"]), read_doc(opts["prerequisites"]), opts["fit_dir"], opts["inputs"], now)
        else:
            require(entries and entries[0]["kind"] == "registered", "STUDY_NOT_REGISTERED")
            require(now >= entries[-1]["at"], "CLOCK_WENT_BACKWARDS")
            if command in ("interim", "final", "review"):
                verify_references(root, entries)
            study = load(root, entries[0]["terms"])
            interim, final = gate(entries, "interim"), gate(entries, "final")
            require(not gate(entries, "stage2_review") and (not interim or interim["outcome"] == "CONTINUE"),
                    "STUDY_CLOSED")
            if final:
                require(final["outcome"] == "PASS" and final["at"] < study["stage2_start"] <= final["at"] + 14 * 86400, "STAGE2_GATE_CLOSED")
            if command == "forecast":
                if final:
                    require(study["stage2_start"] <= now < study["stage2_end"], "OUTSIDE_STAGE2_WINDOW")
                elif not interim:
                    require(now < study["evaluation_end"], "MISSED_INTERIM")
                event = issue(root, entries, study, "stage2" if final else "stage1", opts["inputs"], now)
            elif command in ("interim", "final"):
                require(not final and (command != "interim" or not interim), "ALREADY_JUDGED")
                hist, manifest = inputs.price_export(opts["history"], study, now, opts["price_log"],
                                                      price_ancestor(root, entries))
                event = score_stage1(root, entries, study, hist, command, now)
                event["price_manifest"] = seal(root, manifest)
            elif command == "quote-day":
                require(final, "STAGE1_PASS_REQUIRED")
                prior = next((e for e in reversed(entries) if "quote_manifest" in e), None)
                anchor = load(root, prior["quote_manifest"])["archive_head_sha256"] if prior else None
                daily, manifest = inputs.quote_export(opts["quotes"], study, now, opts["quote_log"], anchor)
                event = record_day(root, entries, study, daily, read_doc(opts["ceiling"]), now)
                event["quote_manifest"] = seal(root, manifest)
            elif command == "review":
                require(final, "STAGE1_PASS_REQUIRED")
                event = score_stage2(root, entries, study, now)
            else:
                raise StudyError("INVALID_COMMAND")
        captured_at = int(time.time())
        require(captured_at >= now, "CLOCK_WENT_BACKWARDS")
        if command == "register":
            require(captured_at < load(root, event["terms"])["evaluation_start"], "REGISTRATION_MISSED_OPENING")
        event["at"] = captured_at
        row = log.append(event)
        return {**RESEARCH_FLAGS, "event": event["kind"], "at": captured_at, "journal_head": row["sha256"],
                **{k: event[k] for k in ("report", "outcome") if k in event}}


def status(root, pin=None):
    root = private_dir(root)
    rows, head = read_verified_chained_log(root, JOURNAL, pinned_head=pin)
    require(rows, "STUDY_NOT_REGISTERED")
    entries = [row["data"] for row in rows]
    verify_references(root, entries)
    return {**RESEARCH_FLAGS, "events": len(entries), "journal_head": head, "last_event": entries[-1],
            "registered_at": entries[0]["at"]}


def verify_references(root, entries):
    # Include negative decisions and earlier feature captures.
    for event in entries:
        for key in ("terms", "prerequisites", "fit", "training_features", "training_history", "sources", "input_history",
                    "features", "history", "price_manifest", "quote_manifest", "scored_features", "quotes", "ceiling", "report"):
            if key in event:
                load(root, event[key])
        for model in event.get("models", {}).values():
            for digest in (model.values() if isinstance(model, dict) else [model]):
                load(root, digest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    fields = {"register": ("terms", "prerequisites", "fit-dir", "inputs"), "forecast": ("inputs",),
              "interim": ("history", "price-log"), "final": ("history", "price-log"), "quote-day": ("quotes", "quote-log", "ceiling"), "review": ()}
    for name, options in fields.items():
        sub = commands.add_parser(name)
        for option in options:
            sub.add_argument("--" + option, required=True, type=Path)
    commands.add_parser("status").add_argument("--pinned-head")
    args = vars(parser.parse_args(argv))
    root, command = args.pop("archive"), args.pop("command")
    try:
        result = status(root, args["pinned_head"]) if command == "status" else advance(root, command, **args)
        print(canonical_ascii_str(result))
        return 0
    except (StudyError, preview.Invalid) as exc:
        reason = str(exc)
    except (ValueError, KeyError, IndexError, OSError, TypeError, OverflowError):
        reason = "STUDY_INPUT_INVALID"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
