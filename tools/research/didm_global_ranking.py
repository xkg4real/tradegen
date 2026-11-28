"""Offline, evidence-bound DIDM study. Scores describe a declared universe at one instant."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

FAMILIES = frozenset({"stock", "bond", "etf", "eln", "crypto", "prediction", "other"})
CORE_FAMILIES = FAMILIES - {"other"}
REFERENCE_TYPES = frozenset({"company_guidance", "survey_consensus", "prior_observation", "preregistered_baseline"})
COSTS = ("execution_bps", "fx_bps", "tax_bps", "other_bps")
BASIS = "total_return_on_invested_cash"
PIN = re.compile(r"[0-9a-f]{64}")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(record, key):
    value = record[key]
    require(isinstance(value, str) and 0 < len(value.strip()) <= 1024, "invalid " + key)
    return value


def time(record, key):
    value = record[key]
    require(type(value) is int and value >= 0, "invalid " + key)
    return value


def number(record, key):
    value = record[key]
    require(isinstance(value, str) and len(value) <= 64, "decimal string required for " + key)
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid " + key) from exc
    require(result.is_finite() and -36 <= result.as_tuple().exponent <= 18 and result.adjusted() <= 18,
            "unbounded " + key)
    return result


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _put(folder, data, suffix):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    digest = _digest(data)
    path = folder / (digest + suffix)
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError:
        require(path.read_bytes() == data, "conflicting evidence bytes")
    return digest


def put_source(folder, data):
    """Archive raw source bytes separately from their extracted fields."""
    return _put(folder, data, ".blob")


def put_evidence(folder, record):
    """Store a new immutable record without replacing any prior version."""
    data = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return _put(folder, data, ".json")


def _read(folder, digest, suffix):
    require(isinstance(digest, str) and PIN.fullmatch(digest), "invalid evidence SHA256")
    data = (Path(folder) / (digest + suffix)).read_bytes()
    require(_digest(data) == digest, "evidence hash mismatch")
    return data


def _unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, "duplicate JSON key")
        result[k] = v
    return result


def _receipt(folder, pin, kind):
    r = json.loads(_read(folder, pin, ".json"), object_pairs_hook=_unique_pairs)
    require(isinstance(r, dict) and r.get("kind") == kind, "incorrect evidence kind")
    text(r, "source_uri")
    _read(folder, r.get("source_sha256"), ".blob")
    require(time(r, "published_at") <= time(r, "received_at"), "receipt predates publication")
    return r


def _available(record, clock):
    return record["published_at"] if clock == "public_reconstruction" else record["received_at"]


def _event(study, folder, decision, clock):
    fields = ("event_id", "metric", "unit", "period")
    scope = tuple(text(study, k) for k in fields)
    revisions = []
    for pin in study["observations"]:
        r = _receipt(folder, pin, "observation")
        require(tuple(text(r, k) for k in fields) == scope, "observation scope mismatch")
        revisions.append((time(r, "version"), pin, r))
    revisions.sort(key=lambda x: x[0])
    prev_pin = None
    previous_times = (-1, -1)
    for i, (v, pin, r) in enumerate(revisions, 1):
        times = (r["published_at"], r["received_at"])
        require(v == i and r.get("supersedes") == prev_pin, "invalid revision chain")
        require(all(new >= old for new, old in zip(times, previous_times)), "backdated revision")
        prev_pin, previous_times = pin, times
    eligible = [item for item in revisions if _available(item[2], clock) <= decision]
    if not eligible:
        return {"status": "EVENT_UNAVAILABLE"}, None
    version, pin, observed = eligible[-1]
    first_publication = revisions[0][2]["published_at"]
    event = dict(status="MISSING_REFERENCE", observation=pin, version=version,
                 reference=study["reference"], observed_value=str(number(observed, "value")),
                 published_at=observed["published_at"], archived_receipt_at=observed["received_at"])
    if study["reference"] is None:
        return event, first_publication
    ref = _receipt(folder, study["reference"], "reference")
    require(tuple(text(ref, k) for k in fields) == scope, "reference scope mismatch")
    require(ref.get("reference_type") in REFERENCE_TYPES, "unsupported reference type")
    if _available(ref, clock) >= first_publication:
        event["status"] = "REFERENCE_NOT_KNOWN_BEFORE_EVENT"
        return event, first_publication
    base = number(ref, "value")
    event.update(reference_value=str(base), reference_type=ref["reference_type"])
    if not base:
        event["status"] = "ZERO_REFERENCE"
        return event, first_publication
    raw = (number(observed, "value") - base) / abs(base)
    event.update(status="SCORED", raw_surprise=str(raw), score=str(min(Decimal(1), max(Decimal(-1), raw))))
    return event, first_publication


def _candidate_scope(c):
    identity = {key: text(c, key) for key in ("instrument_id", "family", "venue", "symbol", "payoff_id")}
    require(identity["family"] in FAMILIES, "unsupported family")
    require(c.get("market_access") in {"unknown", "unavailable", "paper_only", "reported_access"},
            "invalid market_access")
    return identity


def _evaluate(c, common, event, first_publication, decision, folder, clock):
    scope = _candidate_scope(c)
    row = dict(**scope, response=c["response"], costs=c["costs"], market_access=c["market_access"],
               execution_ready=False, net_excess_bps=None, rank=None)
    reason = event["status"] if event["status"] != "SCORED" else None
    for key, reason_missing in (("response", "MISSING_RESPONSE"), ("costs", "MISSING_COSTS")):
        if row[key] is None:
            reason = reason or reason_missing
    if c["family"] in {"eln", "prediction"} and not c.get("terms_sha256"):
        reason = reason or "MISSING_CONTRACT_TERMS"
    if c.get("listing_status", "listed") != "listed":
        require(c["listing_status"] in {"unverified", "placeholder"}, "invalid listing status")
        reason = "LISTING_NOT_VERIFIED"
    if reason:
        row["status"] = reason
        return row
    response = _receipt(folder, row["response"], "response")
    costs = _receipt(folder, row["costs"], "costs")
    expected = {**scope, **common}
    if c["family"] in {"eln", "prediction"}:
        _read(folder, c["terms_sha256"], ".blob")
        expected["terms_sha256"] = c["terms_sha256"]
    if any(any(type(record.get(k)) is not type(v) or record[k] != v for k, v in expected.items())
           for record in (response, costs)):
        row["status"] = "INCOMPARABLE_ESTIMATE"
        return row
    if (response.get("reference_type") != event["reference_type"]
            or response.get("score_method") != "relative_surprise_clamped_v1"):
        row["status"] = "INCOMPARABLE_ESTIMATE"
        return row
    if (_available(response, clock) >= first_publication
            or time(response, "training_end") > response["published_at"]):
        row["status"] = "RESPONSE_NOT_PRE_EVENT"
        return row
    if (_available(costs, clock) > decision or time(costs, "valid_through") < decision
            or time(response, "valid_through") < decision):
        row["status"] = "ESTIMATE_UNAVAILABLE_AT_DECISION"
        return row
    if any(costs.get(k) is None for k in COSTS):
        row["status"] = "INCOMPLETE_COSTS"
        return row
    charges = [number(costs, k) for k in COSTS]
    require(min(charges) >= 0, "negative expense")
    gross = number(response, "intercept_bps") + number(response, "beta_bps") * Decimal(event["score"])
    net = gross - sum(charges)
    row.update(status="POSITIVE" if net > 0 else "NONPOSITIVE", gross_excess_bps=str(gross),
               cost_bps=str(sum(charges)), net_excess_bps=str(net))
    return row


def rank(study, evidence_dir, catalogue=None):
    """Rank expected instrument-level excess on a common basis. No account access is performed."""
    require(study["schema"] == "tradegen.global_didm.v1", "unsupported schema")
    decision = time(study, "decision_at")
    clock = study.get("information_clock", "receipt")
    require(clock in {"receipt", "public_reconstruction"}, "unknown information clock")
    common = {key: text(study, key) for key in ("event_series", "metric", "unit", "benchmark", "numeraire")}
    require(re.fullmatch(r"[A-Z]{3}", common["numeraire"]), "invalid numeraire")
    horizon = time(study, "horizon_seconds")
    require(horizon > 0, "invalid horizon")
    common.update(horizon_seconds=horizon, return_basis=BASIS)
    require(isinstance(study["observations"], list) and isinstance(study["candidates"], list),
            "invalid study collections")
    candidates = list(study["candidates"])
    if "catalogue_sha256" in study:
        require(catalogue is not None, "pinned catalogue file required")
        candidates.extend(import_catalogue(catalogue, study["catalogue_sha256"]))
    else:
        require(catalogue is None, "unregistered catalogue")
    require(candidates, "empty candidate universe")
    with localcontext() as context:
        context.prec = 96
        event, first = _event(study, evidence_dir, decision, clock)
        rows = [_evaluate(c, common, event, first, decision, evidence_dir, clock) for c in candidates]
        require(len({r["instrument_id"] for r in rows}) == len(rows), "duplicate instrument identity")
        require(len({(r["venue"], r["symbol"], r["payoff_id"]) for r in rows}) == len(rows),
                "duplicate listed payoff")
        scored = sorted((r for r in rows if r["net_excess_bps"] is not None),
                        key=lambda r: (-Decimal(r["net_excess_bps"]), r["instrument_id"]))
        for i, row in enumerate(scored):
            row["rank"] = (scored[i - 1]["rank"] if i and Decimal(scored[i - 1]["net_excess_bps"])
                           == Decimal(row["net_excess_bps"]) else i + 1)
        top = [r["instrument_id"] for r in scored if r["rank"] == 1 and r["status"] == "POSITIVE"]
    return dict(schema="tradegen.global_didm.result.v1", event_id=study["event_id"], period=study["period"],
                catalogue_sha256=study.get("catalogue_sha256"), decision_at=decision, information_clock=clock, comparison=common, event=event, research_only=True, execution_ready=False,
                missing_families=sorted(CORE_FAMILIES - {r["family"] for r in rows
                                                          if r["status"] != "LISTING_NOT_VERIFIED"}),
                declared_count=len(rows), scored_count=len(scored), top_positive=top,
                best_among_scored=top[0] if len(top) == 1 else None,
                best_in_declared_universe=top[0] if len(top) == 1 and len(rows) == len(scored) else None,
                candidates=sorted(rows, key=lambda r: (r["rank"] is None, r["rank"] or 0, r["instrument_id"])))


def import_catalogue(path, expected_sha):
    """Load all rows of a hash-pinned, UTF-8 normalized candidate CSV, preserving omissions."""
    data = Path(path).read_bytes()
    require(_digest(data) == expected_sha, "catalogue hash mismatch")
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    columns = ["instrument_id", "family", "venue", "symbol", "payoff_id", "market_access", "response", "costs"]
    optional = ["listing_status", "terms_sha256"]
    require(reader.fieldnames in (columns, columns + optional), "invalid catalogue columns")
    result = []
    for r in reader:
        require(None not in r and None not in r.values(), "malformed catalogue row")
        for k in ("response", "costs"):
            r[k] = r[k] or None
        result.append(r)
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("study", type=Path)
    cli.add_argument("evidence_dir", type=Path)
    cli.add_argument("--catalogue", type=Path, help="append every row of a study-pinned normalized CSV")
    args = cli.parse_args()
    study = json.loads(args.study.read_bytes(), object_pairs_hook=_unique_pairs)
    print(json.dumps(rank(study, args.evidence_dir, args.catalogue), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
