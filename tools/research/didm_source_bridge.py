"""Offline, read-only QUANTGEN DIDM snapshot inspection; never an order input.

Use --help for the explicit input/output paths. No application, credential,
network, model, owner-log or trading imports. See docs/didm-source-bridge.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile

QG_COMMIT = "dec979a7fae65d5f749e12193fad3d0a9ce8ddf3"
CONTRACT = {
    "repository": "xkg4real/quantgen", "commit": QG_COMMIT,
    "store_blob": "9067a11727d57a3dc33162285451f5b309bf292e",
    "score_blob": "759872cccce6c2c1e034125b30ff8e6fa76061ad",
}
EXPORT_FORMAT = "tradegen-didm-exchange-v1"
REPORT_FORMAT = "tradegen-didm-inspection-v1"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_BYTES = 256 * 1024 * 1024
MAX_PAYLOAD_BYTES = 1024 * 1024
MAX_ROWS = 250_000
MAX_SCORES = 25_000
MAX_DEPTH = 32
MAX_NODES = 2_000_000
HASH = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:\-/]{0,127}\Z")
ROW_KEYS = frozenset(("seq", "source_id", "item_id", "kind", "published_at",
                      "valid_at", "received_at", "payload", "payload_sha256"))
SOURCE_KINDS = {
    "gdelt-events2": {"gdelt_event"}, "gdelt-gkg2": {"gdelt_gkg"},
    "alfred": {"alfred_vintage"}, "sec-edgar": {"filing"},
    "opendart": {"filing"}, "ecos": {"ecos_observation"},
    "kalshi": {"kalshi_snapshot", "kalshi_candle"},
    "finbert-baseline": {"finbert_baseline"},
    "alphavantage-news": {"news"}, "tiingo-news": {"news"},
    "cryptopanic": {"news"},
}
HELD_SOURCES = {"alphavantage-news", "tiingo-news", "cryptopanic"}
EVENT_TYPES = frozenset(("monetary_policy", "inflation", "employment", "growth",
    "fiscal", "trade_tariffs", "geopolitics", "election_policy", "earnings",
    "mergers_acquisitions", "management", "regulation_litigation", "supply_chain",
    "crypto_regulation_hack", "none"))
SCORE_KEYS = frozenset(("record_id", "source_id", "target_kind", "entity_id",
    "published_at", "received_at", "relevance_0_100", "ess_like_0_100",
    "novelty_0_100", "origin_cluster_id", "event_type", "direction_probs",
    "uncertainty_entropy", "p_credibility", "market_confirmation", "model_version",
    "prompt_sha256"))
# Exact schema created by the pinned QG PointInTimeStore, whitespace-insensitive.
ITEMS_SQL = """CREATE TABLE items (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL, item_id TEXT NOT NULL, kind TEXT NOT NULL,
    published_at TEXT NOT NULL, valid_at TEXT NOT NULL, received_at TEXT NOT NULL,
    payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
    UNIQUE (source_id, item_id, received_at, payload_sha256)
)"""
SCHEMA_SQL = {
    ("table", "items", "items"): ITEMS_SQL,
    ("table", "sqlite_sequence", "sqlite_sequence"): "CREATE TABLE sqlite_sequence(name,seq)",
    ("index", "sqlite_autoindex_items_1", "items"): None,
    ("index", "items_received", "items"): "CREATE INDEX items_received ON items (received_at)",
    ("index", "items_key", "items"): "CREATE INDEX items_key ON items (source_id, item_id, received_at)",
}


class BridgeError(ValueError):
    """Only fixed, non-sensitive reason codes cross the CLI boundary."""


def require(condition, code):
    if not condition:
        raise BridgeError(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "DIDM_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _finite_tree(value):
    pending, nodes = [(value, 0)], 0
    while pending:
        node, depth = pending.pop()
        nodes += 1
        require(nodes <= MAX_NODES and depth <= MAX_DEPTH, "DIDM_JSON_LIMIT")
        if type(node) is dict:
            require(all(type(k) is str for k in node), "DIDM_JSON_INVALID")
            pending.extend((v, depth + 1) for v in node.values())
        elif type(node) is list:
            pending.extend((v, depth + 1) for v in node)
        elif type(node) is float:
            require(math.isfinite(node), "DIDM_NONFINITE_VALUE")
        elif type(node) is str:
            try:
                node.encode("utf-8", "strict")
            except UnicodeError:
                raise BridgeError("DIDM_JSON_INVALID") from None
        else:
            require(type(node) in (int, bool, type(None)), "DIDM_JSON_INVALID")


def strict_json(raw):
    def bad_constant(_):
        raise BridgeError("DIDM_NONFINITE_VALUE")
    try:
        result = json.loads(raw, object_pairs_hook=_pairs, parse_constant=bad_constant)
        _finite_tree(result)
        return result
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError):
        raise BridgeError("DIDM_JSON_INVALID") from None


def timestamp(value):
    require(type(value) is str and len(value) <= 64, "DIDM_TIME_INVALID")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(t.utcoffset() is not None, "DIDM_AWARE_TIME_REQUIRED")
        return t.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        if type(exc) is BridgeError:
            raise
        raise BridgeError("DIDM_TIME_INVALID") from None


def _metadata(st):
    # Python's Windows path stat and handle fstat can disagree about ctime.
    # Match the repository's PR63 repair: creation time is st_birthtime_ns.
    # Do not import owner/application modules into this offline-only tool.
    require(type(st.st_ino) is int and st.st_ino > 0 and
            type(st.st_dev) is int and st.st_dev >= 0, "DIDM_FILE_IDENTITY_UNSUPPORTED")
    if os.name == "nt":
        created = getattr(st, "st_birthtime_ns", None)
        require(type(created) is int, "DIDM_FILE_IDENTITY_UNSUPPORTED")
    else:
        created = st.st_ctime_ns
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, created)


def _no_sidecars(path):
    require(not any(os.path.lexists(str(path) + suffix)
                    for suffix in ("-wal", "-shm", "-journal")),
            "DIDM_OFFLINE_SQLITE_SNAPSHOT_REQUIRED")


def read_snapshot(path, *, database=False):
    """Read one bounded file without opening a live DB; do not follow its symlink."""
    path = Path(path).absolute()
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode), "DIDM_REGULAR_INPUT_REQUIRED")
    require(0 < before.st_size <= MAX_INPUT_BYTES, "DIDM_INPUT_SIZE_LIMIT")
    if database:
        _no_sidecars(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        require(_metadata(os.fstat(fd)) == _metadata(before), "DIDM_INPUT_CHANGED")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        require(len(raw) == before.st_size, "DIDM_INPUT_CHANGED")
        require(_metadata(os.fstat(fd)) == _metadata(before), "DIDM_INPUT_CHANGED")
        require(_metadata(path.lstat()) == _metadata(before), "DIDM_INPUT_CHANGED")
        if database:
            _no_sidecars(path)
    finally:
        os.close(fd)
    return raw


def _sql_shape(value):
    return re.sub(r"\s+", "", value).lower() if value is not None else None


def sqlite_rows(raw):
    """Query only an isolated copy. The original's WAL/SHM are never opened."""
    require(raw.startswith(b"SQLite format 3\x00"), "DIDM_SQLITE_INVALID")
    try:
        with tempfile.TemporaryDirectory(prefix="tradegen-didm-snapshot-") as directory:
            path = Path(directory) / "snapshot.sqlite"
            path.write_bytes(raw)
            os.chmod(path, 0o400)
            connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
            try:
                connection.execute("PRAGMA query_only=ON")
                connection.execute("PRAGMA trusted_schema=OFF")
                require(connection.execute("PRAGMA query_only").fetchone() == (1,),
                        "DIDM_SQLITE_READ_ONLY_REQUIRED")
                require(connection.execute("PRAGMA trusted_schema").fetchone() == (0,),
                        "DIDM_SQLITE_UNTRUSTED_SCHEMA_REQUIRED")
                ticks = [0]
                def budget():
                    ticks[0] += 1
                    return ticks[0] > 50_000
                connection.set_progress_handler(budget, 1000)
                connection.execute("BEGIN")
                schema = {(r[0], r[1], r[2]): _sql_shape(r[3]) for r in
                          connection.execute("SELECT type,name,tbl_name,sql FROM sqlite_master")}
                require(schema == {k: _sql_shape(v) for k, v in SCHEMA_SQL.items()},
                        "DIDM_SQLITE_SCHEMA_MISMATCH")
                require(connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                        "DIDM_SQLITE_CORRUPT")
                count = connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]
                require(count <= MAX_ROWS, "DIDM_RECORD_LIMIT")
                keys = ("seq", "source_id", "item_id", "kind", "published_at", "valid_at",
                        "received_at", "payload", "payload_sha256")
                result = [dict(zip(keys, row)) for row in connection.execute(
                    "SELECT seq,source_id,item_id,kind,published_at,valid_at,received_at,"
                    "payload,payload_sha256 FROM items ORDER BY seq")]
                connection.execute("ROLLBACK")
                return result
            finally:
                connection.close()
                os.chmod(path, 0o600)  # permits private temporary cleanup on Windows
    except sqlite3.Error:
        raise BridgeError("DIDM_SQLITE_INVALID_OR_LIMIT") from None


def validate_rows(rows):
    require(type(rows) is list and len(rows) <= MAX_ROWS, "DIDM_RECORD_LIMIT")
    result, sequences, versions, digests = [], set(), set(), set()
    for row in rows:
        require(type(row) is dict and set(row) == ROW_KEYS, "DIDM_RECORD_SCHEMA_MISMATCH")
        seq = row["seq"]
        require(type(seq) is int and 0 < seq < 2**63 and seq not in sequences,
                "DIDM_SEQUENCE_INVALID")
        sequences.add(seq)
        source, kind, item = row["source_id"], row["kind"], row["item_id"]
        require(type(source) is str and source in SOURCE_KINDS and
                type(kind) is str and kind in SOURCE_KINDS[source], "DIDM_SOURCE_KIND_UNSUPPORTED")
        require(type(item) is str and 0 < len(item) <= 512 and
                all(ord(c) >= 32 for c in item), "DIDM_ITEM_ID_INVALID")
        times = {key: timestamp(row[key]) for key in ("published_at", "valid_at", "received_at")}
        payload = row["payload"]
        require(type(payload) is str and len(payload.encode("utf-8")) <= MAX_PAYLOAD_BYTES,
                "DIDM_PAYLOAD_LIMIT")
        digest = row["payload_sha256"]
        require(type(digest) is str and HASH.fullmatch(digest) and
                sha256(payload.encode("utf-8")) == digest, "DIDM_PAYLOAD_HASH_MISMATCH")
        parsed = strict_json(payload)
        require(type(parsed) is dict and canonical(parsed) == payload, "DIDM_PAYLOAD_NOT_CANONICAL")
        if "parser" in parsed:
            expected = "kalshi-v0.2" if source == "kalshi" else "news-v0.1" if kind == "news" else None
            require(expected is not None and parsed["parser"] == expected, "DIDM_PARSER_VERSION_UNSUPPORTED")
        if "schema_version" in parsed:
            raise BridgeError("DIDM_SOURCE_PAYLOAD_SCHEMA_UNSUPPORTED")
        version = (source, item, times["received_at"], digest)
        require(version not in versions, "DIDM_DUPLICATE_VERSION")
        versions.add(version)
        record_digest = sha256(canonical(row).encode("utf-8"))
        require(record_digest not in digests, "DIDM_DUPLICATE_VERSION")
        digests.add(record_digest)
        result.append({"record_sha256": record_digest, "row": dict(row), "times": times,
                       "parsed": parsed})
    return sorted(result, key=lambda record: record["row"]["seq"])


def _number(value, low, high):
    require(type(value) in (int, float), "DIDM_SCORE_NUMBER_INVALID")
    require(math.isfinite(value) and low <= value <= high, "DIDM_SCORE_RANGE_INVALID")
    return value


def validate_score(score):
    """Exact QG V0 fields/formulas, with no implicit operational permissions."""
    require(type(score) is dict and SCORE_KEYS <= set(score) and
            set(score) <= SCORE_KEYS | {"schema_version"}, "DIDM_SCORE_SCHEMA_MISMATCH")
    require(score.get("schema_version", "didm-score-v0") == "didm-score-v0",
            "DIDM_SCORE_VERSION_UNSUPPORTED")
    for key in ("record_id", "source_id", "origin_cluster_id"):
        require(type(score[key]) is str and IDENT.fullmatch(score[key]), "DIDM_SCORE_ID_INVALID")
    require(score["target_kind"] in ("firm", "macro", "none"), "DIDM_SCORE_TARGET_INVALID")
    if score["target_kind"] == "none":
        require(score["entity_id"] is None, "DIDM_SCORE_TARGET_INVALID")
    else:
        require(type(score["entity_id"]) is str and IDENT.fullmatch(score["entity_id"]),
                "DIDM_SCORE_TARGET_INVALID")
    require(type(score["event_type"]) is str and score["event_type"] in EVENT_TYPES,
            "DIDM_SCORE_EVENT_INVALID")
    require(score["market_confirmation"] in ("CONFIRMED", "CONTRADICTED", "ALREADY_PRICED", "PENDING"),
            "DIDM_SCORE_CONFIRMATION_INVALID")
    for key in ("relevance_0_100", "novelty_0_100", "ess_like_0_100"):
        _number(score[key], 0, 100)
    _number(score["p_credibility"], 0, 1)
    probs = score["direction_probs"]
    require(type(probs) is list and len(probs) == 3, "DIDM_SCORE_PROBABILITIES_INVALID")
    for value in probs:
        _number(value, 0, 1)
    require(abs(sum(probs) - 1) <= 1e-6 and probs[0] + probs[1] <= 1 + 1e-9,
            "DIDM_SCORE_PROBABILITIES_INVALID")
    require(abs(score["ess_like_0_100"] - (50 + 50 * (probs[0] - probs[1]))) <= 1e-6,
            "DIDM_SCORE_ESS_MISMATCH")
    uncertainty = _number(score["uncertainty_entropy"], 0, math.inf)
    expected = -sum(p * math.log(p) for p in probs if p > 0)
    require(abs(uncertainty - expected) <= 1e-6, "DIDM_SCORE_ENTROPY_MISMATCH")
    require(type(score["model_version"]) is str and 0 < len(score["model_version"].strip()) <= 512,
            "DIDM_MODEL_VERSION_INVALID")
    require(type(score["prompt_sha256"]) is str and HASH.fullmatch(score["prompt_sha256"]),
            "DIDM_PROMPT_HASH_INVALID")
    timestamp(score["published_at"])
    timestamp(score["received_at"])
    return score


def inspect_snapshot(raw, *, input_kind, as_of):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_INPUT_BYTES, "DIDM_INPUT_SIZE_LIMIT")
    cutoff = timestamp(as_of)
    if input_kind == "sqlite":
        rows, scores = sqlite_rows(raw), []
    elif input_kind == "export":
        exchange = strict_json(raw)
        require(type(exchange) is dict and set(exchange) == {"format", "contract", "rows", "scores"},
                "DIDM_EXCHANGE_SCHEMA_MISMATCH")
        require(exchange["format"] == EXPORT_FORMAT and exchange["contract"] == CONTRACT,
                "DIDM_EXCHANGE_CONTRACT_MISMATCH")
        rows, scores = exchange["rows"], exchange["scores"]
        require(type(scores) is list and len(scores) <= MAX_SCORES, "DIDM_SCORE_LIMIT")
    else:
        raise BridgeError("DIDM_INPUT_KIND_INVALID")
    records = validate_rows(rows)
    by_digest = {entry["record_sha256"]: entry for entry in records}
    latest, gaps = {}, {"SOURCE_AUTHENTICATION_UNVERIFIED", "DATA_RIGHTS_UNVERIFIED",
        "CONTINUOUS_COLLECTION_UNVERIFIED", "MODEL_APPROVAL_UNVERIFIED", "EXPIRY_POLICY_UNCONFIGURED",
        "STRATEGY_RESEARCH_NOT_VALIDATED", "APP_INTEGRATION_PENDING", "LIVE_ACTIVATION_NOT_PERFORMED"}
    for record in records:
        row, times, payload = record["row"], record["times"], record["parsed"]
        if row["source_id"] in HELD_SOURCES:
            gaps.add("HELD_NEWS_SOURCE_PRESENT")
        if row["source_id"] == "kalshi" and "parser" not in payload:
            gaps.add("LEGACY_KALSHI_PARSER_UNVERIFIED")
        if row["source_id"] in {"alfred", "opendart", "ecos"}:
            gaps.add("PRECISE_RELEASE_TIME_UNAVAILABLE")
        if times["published_at"] > times["received_at"]:
            gaps.add("SOURCE_CLOCK_ORDER_ANOMALY")
        if times["received_at"] > cutoff:
            continue
        key = (row["source_id"], row["item_id"])
        rank = (times["received_at"], row["payload_sha256"])
        if key not in latest or rank > latest[key][0]:
            latest[key] = (rank, record)
    selected = [value[1] for value in latest.values()]
    selected.sort(key=lambda entry: (entry["times"]["valid_at"], entry["row"]["source_id"], entry["row"]["item_id"]))
    selected_ids = {entry["record_sha256"] for entry in selected}
    score_records, seen_scores = [], set()
    for wrapper in scores:
        require(type(wrapper) is dict and set(wrapper) == {"source_record_sha256", "score"},
                "DIDM_SCORE_LINK_SCHEMA_MISMATCH")
        link = wrapper["source_record_sha256"]
        require(type(link) is str and link in by_digest, "DIDM_SCORE_SOURCE_LINK_MISSING")
        score = validate_score(wrapper["score"])
        source = by_digest[link]
        require(score["source_id"] == source["row"]["source_id"] and
                timestamp(score["published_at"]) == source["times"]["published_at"] and
                timestamp(score["received_at"]) >= source["times"]["received_at"],
                "DIDM_SCORE_PROVENANCE_MISMATCH")
        identity = (score["record_id"], score["model_version"], timestamp(score["received_at"]))
        require(identity not in seen_scores, "DIDM_DUPLICATE_SCORE")
        seen_scores.add(identity)
        score_records.append({"source_record_sha256": link, "score": score,
            "score_sha256": sha256(canonical(score).encode("utf-8")),
            "known_at_as_of": timestamp(score["received_at"]) <= cutoff and link in selected_ids})
    if not scores:
        gaps.add("V0_MODEL_SCORES_MISSING")
    known_scores = sum(item["known_at_as_of"] for item in score_records)
    if not known_scores:
        gaps.add("NO_V0_SCORES_KNOWN_AT_AS_OF")
    if not selected:
        gaps.add("NO_RECORDS_KNOWN_AT_AS_OF")
    if not rows:
        gaps.add("SOURCE_DATA_EMPTY")
    return {"format": REPORT_FORMAT, "research_only": True, "live_eligible": False,
        "execution_ready": False, "source_authenticated": False, "owner_approval_verified": False,
        "contract_reference": dict(CONTRACT), "input_kind": input_kind,
        "input_sha256": sha256(raw), "as_of": cutoff.isoformat(timespec="microseconds"),
        "record_count": len(records), "selected_count": len(selected), "score_count": len(score_records),
        "known_score_count": known_scores,
        "future_received_count": sum(entry["times"]["received_at"] > cutoff for entry in records),
        "records": [{"record_sha256": entry["record_sha256"], "row": entry["row"]} for entry in records],
        "selected_record_sha256": [entry["record_sha256"] for entry in selected],
        "scores": score_records, "gaps": sorted(gaps)}


def publish_report(report, destination):
    """No partial final file and no overwrite, including concurrent publishers."""
    data = (canonical(report) + "\n").encode("utf-8")
    require(len(data) <= MAX_OUTPUT_BYTES, "DIDM_OUTPUT_SIZE_LIMIT")
    destination = Path(destination).absolute()
    require(not os.path.lexists(destination), "DIDM_OUTPUT_EXISTS")
    require(destination.parent.is_dir(), "DIDM_OUTPUT_DIRECTORY_REQUIRED")
    fd, temporary = tempfile.mkstemp(prefix=".didm-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link is an atomic no-clobber publication on supported local filesystems.
        # Unsupported filesystems refuse; there is no overwrite fallback.
        os.link(temporary, destination)
    finally:
        os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--database", help="Explicit offline copy of the QUANTGEN DIDM SQLite store")
    source.add_argument("--export", help="Explicit tradegen-didm-exchange-v1 JSON file")
    parser.add_argument("--as-of", required=True, help="Timezone-aware ISO 8601 knowledge cutoff")
    parser.add_argument("--output", required=True, help="New PRIVATE report path; never overwritten")
    args = parser.parse_args(argv)
    try:
        raw = read_snapshot(args.database or args.export, database=bool(args.database))
        report = inspect_snapshot(raw, input_kind="sqlite" if args.database else "export", as_of=args.as_of)
        publish_report(report, args.output)
        print(canonical({key: report[key] for key in ("format", "record_count", "selected_count",
            "score_count", "known_score_count", "future_received_count", "input_sha256", "research_only", "live_eligible", "gaps")}))
        return 0
    except BridgeError as exc:
        code = str(exc)
    except (OSError, TypeError, ValueError, OverflowError, RecursionError):
        code = "DIDM_INPUT_OR_OUTPUT_REFUSED"
    print(canonical({"research_only": True, "live_eligible": False, "execution_ready": False,
                     "reason": code}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
