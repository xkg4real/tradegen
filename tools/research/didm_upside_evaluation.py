"""TRADEGEN archive adapters and CLI for normalized DIDM upside-event research."""
from __future__ import annotations
import argparse
import math
import re
from pathlib import Path

from tools.research.didm_upside_core import (
    BPS,
    FLAGS,
    PIN,
    check_terms,
    display,
    evaluate,
    integer,
    need,
    number,
)


def _load_doc(path, pin):
    from tools.research._study_common import read_strict_json_file, sha256_ascii
    need(type(pin) is str and PIN.fullmatch(pin), "ARTIFACT_PIN_REQUIRED")
    obj, _ = read_strict_json_file(path)
    need(sha256_ascii(obj) == pin, "ARTIFACT_PIN_MISMATCH")
    return obj


def _log(root, name, pin):
    from tools.research._study_common import read_verified_chained_log
    need(type(pin) is str and PIN.fullmatch(pin), "ARCHIVE_PIN_REQUIRED")
    rows, head = read_verified_chained_log(root, name, pinned_head=pin)
    need(head == pin and rows, "ARCHIVE_TAIL_CHANGED_OR_EMPTY")
    return [r["data"] for r in rows]


def recorded_quotes(root, pin, t):
    rows = _log(root, "quotes.jsonl", pin)
    first = rows[0]
    need(first["kind"] == "config" and first["schema"] == "tradegen-upbit-quote-recorder-v1",
         "QUOTE_ARCHIVE_CONFIG")
    c = first["config"]
    need(c["market"] == t["market"] and c["scope"] == t["scope"]
         and integer(c["interval_seconds"], 1, 3600) <= t["max_gap_seconds"]
         and type(c["app_running"]) is bool, "QUOTE_ARCHIVE_SCOPE")
    quotes = []
    for r in rows[1:]:
        if r["kind"] == "rate_limit_stop":
            continue   # subsequent missing intervals remain absent
        need(r["kind"] == "quote", "UNKNOWN_QUOTE_EVENT")
        o = r["observation"]
        need(o["scope"] == t["scope"] and o["as_of"] == r["as_of"]
             and o["sequence"] == len(quotes)+1 and c["app_running"] is r["app_running"], "QUOTE_ARCHIVE_BINDING")
        flags = [o["prior_block_active"], o["floor_halt"], o["daily_stop"], r["status_stale"]]
        need(all(type(v) is bool for v in flags) and type(r["stripped_causes"]) is list, "INVALID_QUOTE_FLAGS")
        quotes.append(dict(market=t["market"], scope=t["scope"], at=r["as_of"], same_second=r["same_second"], bid_at=o["bid_at"],
                      bid=o["bid"], ask=r["ask"], last_trade=o["last_trade"], last_trade_at=o["last_trade_at"],
                      blocked=any(flags) or bool(r["stripped_causes"])))
    return quotes


def recorded_signals(root, pin, t):
    from tools.research import direction_forecast_adapter as adapter
    from tools.research._study_common import sha256_ascii
    entries = _log(root, "prospective.jsonl", pin)
    first = entries[0]
    need(first["kind"] == "registered" and integer(first["at"]) < t["start"], "FORECAST_ARCHIVE_UNREGISTERED")
    def artifact(key):
        need(type(key) is str and PIN.fullmatch(key), "ARTIFACT_PIN_REQUIRED")
        return _load_doc(root / (key+".json"), key)
    study = artifact(first["terms"])
    roles = sorted({"M","B1"}.intersection(t["models"]))
    need(study["market"] == t["market"] and study["scope"] == t["scope"]
         and study["stage2_start"] <= t["start"] < t["end"] <= study["stage2_end"], "FORECAST_STUDY_SCOPE")
    for role in roles:
        model = study["forecast_model" if role == "M" else "b1_forecast_model"]
        need(model["sha256"] == t["models"][role], "FORECAST_STUDY_PIN")
    features = {}
    for role in roles:
        m = artifact(first["models"][role])
        need(m["role"] == role and m["sha256"] == t["models"][role] and type(m["feature_names"]) is list
             and len(m["feature_names"]) == len(set(m["feature_names"]))
             and all(type(f) is str for f in m["feature_names"]), "REGISTERED_FEATURE_MISMATCH")
        names = m["feature_names"]
        coefs = m["weights"]["coefficients"]
        need(sha256_ascii({k:v for k,v in m.items() if k != "sha256"}) == m["sha256"]
             and m["market"] == t["market"] and len(coefs) == 3 and all(type(row) is list and len(row) == len(names)
             and all(type(v) in (int,float) and math.isfinite(v) for v in row) for row in coefs),
             "REGISTERED_WEIGHTS_MISMATCH")
        # A softmax feature with the same coefficient in all classes cancels.
        active = [name for j,name in enumerate(names) if len({row[j] for row in coefs}) > 1]
        features[role] = {"declared":names,"class_differentiating_weights":active}
    updates, passed, last = [], False, first["at"]
    for event in entries[1:]:
        at = integer(event["at"])
        need(at >= last, "BACKDATED_ARCHIVE")
        last = at
        if event["kind"] == "final":
            passed = event["outcome"] == "PASS" and at < study["stage2_start"]
        if event["kind"] != "stage2_forecast":
            continue
        a = integer(event["first_as_of"])
        need(passed and a == event["last_as_of"] and study["stage2_start"] <= a < study["stage2_end"]
             and a <= at and set(event["models"]) == {"M","B1"}, "PROSPECTIVE_FORECAST_REQUIRED")
        for role in roles:
            ref = event["models"][role]
            snap, man = artifact(ref["forecast"]), artifact(ref["manifest"])
            adapter.check_snapshot(snap)
            model = snap["model"]
            need(model["sha256"] == t["models"][role] and model["frozen_at"] <= t["registered_at"]
                 and man["format"] == "tradegen-direction-forecast-manifest-v1"
                 and all(man.get(k) is v for k,v in FLAGS.items())
                 and man["manifest_sha256"] == sha256_ascii({k:v for k,v in man.items() if k != "manifest_sha256"})
                 and man["model"] == model and man["role"] == role and man["mode"] == "live"
                 and man["snapshot_sha256"] == snap["snapshot_sha256"]
                 and man["generated_at"] == snap["generated_at"] <= at
                 and a <= man["issued_at"] <= man["generated_at"]
                 and len(snap["forecasts"]) == man["forecast_count"] <= 1, "LIVE_MANIFEST_MISMATCH")
            direction, p = "unavailable", None
            if snap["forecasts"]:
                f, = snap["forecasts"]
                need(f["as_of"] == a and f["market"] == t["market"] and f["issued_at"] == man["issued_at"]
                     and (f["horizon_seconds"], f["hurdle_bps"]) == (study["horizon_seconds"], study["hurdle_bps"]),
                     "FORECAST_TARGET_MISMATCH")
                direction, p = f["direction"], f["probabilities"]["up"]
            updates.append(dict(arm=role, market=t["market"], model_sha256=t["models"][role], as_of=a,
                           issued_at=man["issued_at"], received_at=at, expires_at=a+study["horizon_seconds"],
                           direction=direction, p_up=p))
    return updates, features


def attribution(features):
    if "M" not in features or "B1" not in features:
        return "UNESTABLISHED"
    m, b = set(features["M"]["declared"]), set(features["B1"]["declared"])
    didm = {"D1","D2","D3"}
    incremental = set(features["M"]["class_differentiating_weights"])-b
    if not (incremental & didm):
        return "NO_EFFECTIVE_INCREMENTAL_DIDM_FEATURE"
    if "Q1" in m or (m-b)-didm or b-m:
        return "COMBINED_FEATURE_CONTRAST"
    return "DIDM_ONLY_FEATURE_CONTRAST_DESCRIPTIVE"


def main(argv=None):
    from tools.research._study_common import atomic_publish_json_ascii, sha256_ascii
    parser = argparse.ArgumentParser(description=__doc__)
    for k in ("terms","quotes","output"):
        parser.add_argument("--"+k, type=Path, required=True)
    for k in ("terms-sha256","quotes-head"):
        parser.add_argument("--"+k, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--forecast-head")
    parser.add_argument("--supplemental-signals", type=Path, action="append", default=[])
    parser.add_argument("--supplemental-sha256", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        t = _load_doc(args.terms, args.terms_sha256)
        check_terms(t)
        quotes = recorded_quotes(args.quotes, args.quotes_head, t)
        signals, features, support = [], {}, {}
        need(bool(args.archive) == bool(args.forecast_head) == bool({"M","B1"} & t["models"].keys()),
             "PAIRED_ARCHIVE_ARGUMENTS_REQUIRED")
        if args.archive:
            signals, features = recorded_signals(args.archive, args.forecast_head, t)
        need(bool(args.supplemental_signals) == bool(args.supplemental_sha256)
             == bool(t["models"].keys()-{"M","B1"}), "SUPPLEMENTAL_SIGNAL_ARGUMENTS_REQUIRED")
        need(len(args.supplemental_signals) == len(args.supplemental_sha256), "SUPPLEMENTAL_PIN_COUNT")
        for path, pin in zip(args.supplemental_signals, args.supplemental_sha256):
            extra = _load_doc(path, pin)
            need(extra["format"] == "tradegen-upside-signals-v1" and extra["market"] == t["market"]
                 and extra["scope"] == t["scope"] and type(extra["signals"]) is list
                 and all(f["arm"] in t["models"].keys()-{"M","B1"} for f in extra["signals"]),
                 "SUPPLEMENTAL_SIGNAL_SCOPE")
            signals.extend(extra["signals"])
            for q in extra.get("eligible_quotes", []):
                at=integer(q["at"])
                need(at not in support and type(q.get("blocked")) is bool, "DUPLICATE_OR_INVALID_SUPPORT")
                support[at]=q
        if t.get("quote_gate") == "corroborated":
            for q in quotes:
                overlay=support.pop(q["at"], None)
                if overlay is None:
                    q["corroborated"]=False
                    continue
                need(set(overlay) == set(q) and all(overlay[k] == q[k] for k in q if k != "blocked"),
                     "SUPPORT_BOOK_MISMATCH")
                q["blocked"] = q["blocked"] or overlay["blocked"]
                q["corroborated"] = True
            need(not support, "SUPPORT_QUOTE_MISSING")
        report = evaluate(t, quotes, signals)
        report["registered_features"] = features
        report["attribution"] = attribution(features)
        report["inputs"] = {"terms_sha256":args.terms_sha256,"quotes_head":args.quotes_head,
                            "forecast_head":args.forecast_head,"supplemental_sha256":args.supplemental_sha256}
        report["report_sha256"] = sha256_ascii(report)
        atomic_publish_json_ascii(args.output, report)
        print(report["status"], report["report_sha256"])
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        detail = str(exc)
        print("Upside evaluation refused.", detail if re.fullmatch(r"[A-Z][A-Z0-9_]{1,90}", detail) else type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
