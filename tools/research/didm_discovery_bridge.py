"""Match selected discovery records to independent, dated listing receipts for offline research."""
import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from tools.research import didm_global_ranking as ranking


FAMILIES = {
    "equity": "stock", "etf": "etf", "fund": "fund", "money_market_fund": "fund",
    "sovereign_fixed_rate": "bond", "sovereign_inflation_linked": "bond",
    "reported_debt_security": "bond", "corporate_bond": "bond", "corporate_fixed_rate": "bond", "equity_linked_note": "eln",
    "commodity_future": "future", "equity_index_future": "future", "equity_etf_option": "option",
    "prediction_market": "prediction", "spot": "crypto", "future": "future",
    "swap": "swap", "option": "option",
}
REFERENCE_CLASSES = {"native_asset", "chain_token", "index_reference", "fx_reference", "crypto_quote"}
IDENTITY = ("dataset", "source_id", "unit", "product_class", "symbol_or_contract", "venue_or_chain", "side")
ARCHIVE_FIELDS = {"record_key", *IDENTITY, "parent_contract", "mic", "asof_basis", "source_status",
                  "source_ref", "execution_status"}


def _eligible(row, binding, decision, clock, folder):
    if row["unit"] == "chain_asset_reference" or row["product_class"] in REFERENCE_CLASSES:
        return None, "REFERENCE_ONLY"
    if row["unit"] == "payoff_side" and row["side"].upper() not in {"YES", "NO"}:
        return None, "UNMODELED_PAYOFF"
    family = FAMILIES.get(row["product_class"])
    if family is None:
        return None, "UNMODELED_CLASS"
    if not binding.get("listing"):
        return None, "MISSING_DATED_LISTING"
    receipt = ranking._receipt(folder, binding["listing"], "listing")
    ranking.require(all(receipt.get(key) == row[key] for key in IDENTITY), "listing identity mismatch")
    for name in ("outcome_token_id", "settlement_group"):
        if row.get(name):
            ranking.require(receipt.get(name) == row[name], "listing token or settlement group mismatch")
    ranking.require(receipt["source_uri"] != row["source_ref"], "independent listing source required")
    as_of = ranking.time(receipt, "as_of")
    valid_through = ranking.time(receipt, "valid_through")
    ranking.require(as_of <= receipt["published_at"] and as_of <= valid_through, "invalid listing interval")
    if ranking._available(receipt, clock) > decision or not as_of <= decision <= valid_through:
        return None, "LISTING_UNAVAILABLE_AT_DECISION"
    if row["dataset"] == "listed" and row["source_status"] == "flagged_delisted":
        # The provider supplies a date but no intraday time. Be conservative on that day.
        try:
            snapshot_date = date.fromisoformat(row["asof_basis"].split()[0])
        except (ValueError, IndexError):
            return None, "UNRESOLVED_DELISTING"
        if datetime.fromtimestamp(decision, timezone.utc).date() >= snapshot_date:
            return None, "DELISTED_AT_SNAPSHOT"
    status = ranking.text(receipt, "listing_status")
    if status in ranking.INACTIVE_STATES:
        return None, "INACTIVE_AT_DECISION"
    ranking.require(status == "listed", "invalid dated listing status")
    candidate = {key: ranking.text(receipt, key) for key in
                 ("instrument_id", "family", "venue", "symbol", "payoff_id")}
    ranking.require(candidate["family"] == family and candidate["symbol"] == row["symbol_or_contract"],
                    "candidate product or symbol mismatch")
    if row["venue_or_chain"]:
        ranking.require(candidate["venue"].casefold() in {row["venue_or_chain"].casefold(), row["mic"].casefold()},
                        "candidate venue mismatch")
    if row["unit"] == "payoff_side":
        ranking.require(candidate["payoff_id"].upper() == row["side"].upper(),
                        "candidate payoff mismatch")
    candidate.update(market_access="unknown", listing_status=status, response=binding.get("response"),
                     costs=binding.get("costs"), terms_sha256=binding.get("terms_sha256"))
    return candidate, "SUBMITTED_TO_RANKING"


def evaluate(archive, manifest, study, folder):
    """Read the full pinned registry, retaining detailed rows only for requested record keys."""
    ranking.require(study["schema"] == "tradegen.global_didm.v1", "unsupported study schema")
    ranking.require(study.get("candidates") == [] and "catalogue_sha256" not in study, "use a bridge-only study")
    decision = ranking.time(study, "decision_at")
    clock = study.get("information_clock", "receipt")
    ranking.require(clock in {"receipt", "public_reconstruction"}, "unknown information clock")
    ranking.require(isinstance(manifest["bindings"], list), "invalid bindings")
    bindings = {}
    for binding in manifest["bindings"]:
        key = ranking.text(binding, "record_key")
        ranking.require(ranking.PIN.fullmatch(key) and key not in bindings, "invalid or duplicate binding")
        bindings[key] = binding

    found = {}
    counts = Counter()
    with Path(archive).open("rb") as raw:
        digest = hashlib.file_digest(raw, "sha256").hexdigest()
        ranking.require(digest == manifest["archive_sha256"], "archive hash mismatch")
        raw.seek(0)
        with gzip.GzipFile(fileobj=raw) as gz, io.TextIOWrapper(gz, encoding="utf-8-sig", newline="") as data:
            reader = csv.DictReader(data)
            ranking.require(ARCHIVE_FIELDS.issubset(reader.fieldnames or []), "missing archive fields")
            for row in reader:
                counts[row["unit"]] += 1
                key = row["record_key"]
                if key in bindings:
                    ranking.require(key not in found, "duplicate archive record")
                    found[key] = row
    candidates = []
    records = []
    for key, binding in bindings.items():
        row = found.get(key)
        item = {"record_key": key, "listing": binding.get("listing"), "status": "ABSENT_FROM_ARCHIVE"}
        if row is not None:
            candidate, status = _eligible(row, binding, decision, clock, folder)
            item.update(discovery=row, status=status)
            if candidate:
                candidates.append(candidate)
                item["instrument_id"] = candidate["instrument_id"]
        records.append(item)
    ranked = ranking.rank(dict(study, candidates=candidates), folder) if candidates else None
    return {"archive_sha256": digest, "archive_records_by_unit": dict(counts),
            "requested": len(bindings), "matched": len(found), "submitted": len(candidates),
            "scored": ranked["scored_count"] if ranked else 0, "records": records,
            "submitted_subset_ranking": ranked, "research_only": True, "execution_ready": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "manifest", "study", "evidence_dir"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    def load(path):
        return json.loads(path.read_bytes(), object_pairs_hook=ranking._unique_pairs)
    print(json.dumps(evaluate(args.archive, load(args.manifest), load(args.study), args.evidence_dir),
                     ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
