"""Offline, read-only QUANTGEN DIDM snapshot inspection; never an order input.

Use --help for the explicit input/output paths. No application, credential,
network, model, owner-log or trading imports. See docs/didm-source-bridge.md.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
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
from types import SimpleNamespace

QG_COMMIT = "dec979a7fae65d5f749e12193fad3d0a9ce8ddf3"
CONTRACT = {
    "repository": "xkg4real/quantgen", "commit": QG_COMMIT,
    "store_blob": "9067a11727d57a3dc33162285451f5b309bf292e",
    "score_blob": "759872cccce6c2c1e034125b30ff8e6fa76061ad",
}
EXPORT_FORMAT = "tradegen-didm-exchange-v1"
REPORT_FORMAT = "tradegen-didm-inspection-v1"
MAX_INPUT_BYTES = 64 * 1024 * 1024  # exchange JSON, parsed in memory
# A SQLite store is streamed to a private copy and read one row at a time; duplicate and
# selection state lives in a scratch SQLite file, so Python memory does not grow with it.
MAX_DATABASE_BYTES = 1024 ** 3
MAX_OUTPUT_BYTES = 2 * 1024 ** 3  # streamed to disk
CHUNK_BYTES = 1024 * 1024
MAX_PAYLOAD_BYTES = 1024 * 1024
MAX_ROWS = 2_000_000
# SQLite work budget, one tick per 1,000 virtual-machine steps, scaled to the copy's size.
# Measured on synthetic stores: 6,400 bytes per tick with 200-byte rows, 24,600 with GDELT-sized rows.
SQLITE_BASE_TICKS = 50_000
SQLITE_BYTES_PER_TICK = 256
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


def copy_snapshot(path, write, *, database=False, limit=None):
    """Stream one bounded file to write() without opening a live DB; do not follow its symlink.

    Returns the SHA-256 of exactly the bytes passed to write().
    """
    limit = MAX_INPUT_BYTES if limit is None else limit
    path = Path(path).absolute()
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode), "DIDM_REGULAR_INPUT_REQUIRED")
    require(0 < before.st_size <= limit, "DIDM_INPUT_SIZE_LIMIT")
    if database:
        _no_sidecars(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        require(_metadata(os.fstat(fd)) == _metadata(before), "DIDM_INPUT_CHANGED")
        digest, size = hashlib.sha256(), 0
        with os.fdopen(fd, "rb", closefd=False) as stream:
            while chunk := stream.read(CHUNK_BYTES):
                size += len(chunk)
                require(size <= before.st_size, "DIDM_INPUT_CHANGED")
                digest.update(chunk)
                write(chunk)
        require(size == before.st_size, "DIDM_INPUT_CHANGED")
        require(_metadata(os.fstat(fd)) == _metadata(before), "DIDM_INPUT_CHANGED")
        require(_metadata(path.lstat()) == _metadata(before), "DIDM_INPUT_CHANGED")
        if database:
            _no_sidecars(path)
    finally:
        os.close(fd)
    return digest.hexdigest()


def read_snapshot(path, *, database=False):
    """Read one file of at most MAX_INPUT_BYTES into memory (exchange JSON)."""
    chunks = []
    copy_snapshot(path, chunks.append, database=database)
    return b"".join(chunks)


def _sql_shape(value):
    return re.sub(r"\s+", "", value).lower() if value is not None else None


ROWS_SQL = ("SELECT seq,source_id,item_id,kind,published_at,valid_at,received_at,"
            "payload,payload_sha256 FROM items ORDER BY seq")
ROW_COLUMNS = ("seq", "source_id", "item_id", "kind", "published_at", "valid_at",
               "received_at", "payload", "payload_sha256")


def open_snapshot(path):
    """Query only the private copy. The original's WAL/SHM are never opened."""
    with open(path, "rb") as stream:
        require(stream.read(16) == b"SQLite format 3\x00", "DIDM_SQLITE_INVALID")
    os.chmod(path, 0o400)
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        # SQLite refuses an oversized value itself, before Python copies it into memory.
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_PAYLOAD_BYTES + 64 * 1024)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        require(connection.execute("PRAGMA query_only").fetchone() == (1,),
                "DIDM_SQLITE_READ_ONLY_REQUIRED")
        require(connection.execute("PRAGMA trusted_schema").fetchone() == (0,),
                "DIDM_SQLITE_UNTRUSTED_SCHEMA_REQUIRED")
        ticks = [0]
        allowed = SQLITE_BASE_TICKS + path.stat().st_size // SQLITE_BYTES_PER_TICK
        def budget():
            ticks[0] += 1
            return ticks[0] > allowed
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
        return connection
    except BaseException:
        connection.close()
        raise


def check_row(row):
    """Validate one record on its own; uniqueness is checked by the caller's state."""
    require(type(row) is dict and set(row) == ROW_KEYS, "DIDM_RECORD_SCHEMA_MISMATCH")
    seq = row["seq"]
    require(type(seq) is int and 0 < seq < 2**63, "DIDM_SEQUENCE_INVALID")
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
    # seq is part of the canonical row, so distinct sequences give distinct record digests.
    return {"record_sha256": sha256(canonical(row).encode("utf-8")), "times": times, "parsed": parsed}


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


STATE_SQL = """CREATE TABLE seen (
    seq INTEGER PRIMARY KEY, record_sha256 TEXT NOT NULL, source_id TEXT NOT NULL,
    item_id TEXT NOT NULL, published TEXT NOT NULL, valid TEXT NOT NULL,
    received TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
    UNIQUE (source_id, item_id, received, payload_sha256))"""
# Latest version per source/item known at the cutoff: QG's receipt time, then payload hash.
SELECT_SQL = """CREATE TABLE selected AS SELECT record_sha256, valid, source_id, item_id FROM (
    SELECT record_sha256, valid, source_id, item_id, row_number() OVER (
        PARTITION BY source_id, item_id ORDER BY received DESC, payload_sha256 DESC) AS latest
    FROM seen WHERE received <= ?) WHERE latest = 1"""


def _utc(moment):
    # Fixed-width UTC text sorts in time order, so SQLite compares it as the datetimes would.
    return moment.isoformat(timespec="microseconds")


@contextmanager
def inspection(source, *, input_kind, input_sha256, as_of, directory):
    """Validate every record, then yield the report fields and a streaming report writer.

    source is the private SQLite copy's path or the exchange JSON bytes. Rows are read one
    at a time. Duplicate, selection and score-link state lives in a scratch SQLite file in
    the private directory, so Python memory does not grow with the number of rows.
    """
    cutoff = timestamp(as_of)
    snapshot = state = None
    try:
        state = sqlite3.connect(Path(directory) / "state.sqlite", isolation_level=None)
        for pragma in ("journal_mode=OFF", "synchronous=OFF", "temp_store=FILE", "cache_size=-8192"):
            state.execute("PRAGMA " + pragma)
        state.execute(STATE_SQL)
        if input_kind == "sqlite":
            snapshot, scores = open_snapshot(source), []
            def rows():
                cursor = snapshot.execute(ROWS_SQL)
                try:
                    for values in cursor:
                        yield dict(zip(ROW_COLUMNS, values))
                finally:
                    cursor.close()
            ordered = rows
        elif input_kind == "export":
            exchange = strict_json(source)
            require(type(exchange) is dict and set(exchange) == {"format", "contract", "rows", "scores"},
                    "DIDM_EXCHANGE_SCHEMA_MISMATCH")
            require(exchange["format"] == EXPORT_FORMAT and exchange["contract"] == CONTRACT,
                    "DIDM_EXCHANGE_CONTRACT_MISMATCH")
            data, scores = exchange["rows"], exchange["scores"]
            require(type(scores) is list and len(scores) <= MAX_SCORES, "DIDM_SCORE_LIMIT")
            require(type(data) is list and len(data) <= MAX_ROWS, "DIDM_RECORD_LIMIT")
            def rows():
                return iter(data)
            def ordered():
                return iter(sorted(data, key=lambda row: row["seq"]))
        else:
            raise BridgeError("DIDM_INPUT_KIND_INVALID")
        gaps = {"SOURCE_AUTHENTICATION_UNVERIFIED", "DATA_RIGHTS_UNVERIFIED",
            "CONTINUOUS_COLLECTION_UNVERIFIED", "MODEL_APPROVAL_UNVERIFIED", "EXPIRY_POLICY_UNCONFIGURED",
            "STRATEGY_RESEARCH_NOT_VALIDATED", "APP_INTEGRATION_PENDING", "LIVE_ACTIVATION_NOT_PERFORMED"}
        record_count = future_count = 0
        state.execute("BEGIN")
        for row in rows():
            record = check_row(row)
            times, payload = record["times"], record["parsed"]
            if row["source_id"] in HELD_SOURCES:
                gaps.add("HELD_NEWS_SOURCE_PRESENT")
            if row["source_id"] == "kalshi" and "parser" not in payload:
                gaps.add("LEGACY_KALSHI_PARSER_UNVERIFIED")
            if row["source_id"] in {"alfred", "opendart", "ecos"}:
                gaps.add("PRECISE_RELEASE_TIME_UNAVAILABLE")
            if times["published_at"] > times["received_at"]:
                gaps.add("SOURCE_CLOCK_ORDER_ANOMALY")
            future_count += times["received_at"] > cutoff
            try:
                state.execute("INSERT INTO seen VALUES (?,?,?,?,?,?,?,?)", (
                    row["seq"], record["record_sha256"], row["source_id"], row["item_id"],
                    _utc(times["published_at"]), _utc(times["valid_at"]), _utc(times["received_at"]),
                    row["payload_sha256"]))
            except sqlite3.IntegrityError:
                taken = state.execute("SELECT 1 FROM seen WHERE seq=?", (row["seq"],)).fetchone()
                raise BridgeError("DIDM_SEQUENCE_INVALID" if taken else "DIDM_DUPLICATE_VERSION") from None
            record_count += 1
        state.execute(SELECT_SQL, (_utc(cutoff),))
        selected_count = state.execute("SELECT COUNT(*) FROM selected").fetchone()[0]
        if scores:
            state.execute("CREATE INDEX seen_record ON seen (record_sha256)")
            state.execute("CREATE INDEX selected_record ON selected (record_sha256)")
        score_records, seen_scores = [], set()
        for wrapper in scores:
            require(type(wrapper) is dict and set(wrapper) == {"source_record_sha256", "score"},
                    "DIDM_SCORE_LINK_SCHEMA_MISMATCH")
            link = wrapper["source_record_sha256"]
            linked = type(link) is str and state.execute(
                "SELECT source_id, published, received FROM seen WHERE record_sha256=?", (link,)).fetchone()
            require(linked, "DIDM_SCORE_SOURCE_LINK_MISSING")
            score = validate_score(wrapper["score"])
            received = _utc(timestamp(score["received_at"]))
            require(score["source_id"] == linked[0] and
                    _utc(timestamp(score["published_at"])) == linked[1] and
                    received >= linked[2], "DIDM_SCORE_PROVENANCE_MISMATCH")
            identity = (score["record_id"], score["model_version"], received)
            require(identity not in seen_scores, "DIDM_DUPLICATE_SCORE")
            seen_scores.add(identity)
            current = state.execute("SELECT 1 FROM selected WHERE record_sha256=?", (link,)).fetchone()
            score_records.append({"source_record_sha256": link, "score": score,
                "score_sha256": sha256(canonical(score).encode("utf-8")),
                "known_at_as_of": received <= _utc(cutoff) and current is not None})
        if not scores:
            gaps.add("V0_MODEL_SCORES_MISSING")
        known_scores = sum(item["known_at_as_of"] for item in score_records)
        if not known_scores:
            gaps.add("NO_V0_SCORES_KNOWN_AT_AS_OF")
        if not selected_count:
            gaps.add("NO_RECORDS_KNOWN_AT_AS_OF")
        if not record_count:
            gaps.add("SOURCE_DATA_EMPTY")
        fields = {"format": REPORT_FORMAT, "research_only": True, "live_eligible": False,
            "execution_ready": False, "source_authenticated": False, "owner_approval_verified": False,
            "contract_reference": dict(CONTRACT), "input_kind": input_kind,
            "input_sha256": input_sha256, "as_of": _utc(cutoff),
            "record_count": record_count, "selected_count": selected_count, "score_count": len(score_records),
            "known_score_count": known_scores, "future_received_count": future_count,
            "scores": score_records, "gaps": sorted(gaps)}

        def records():
            digests, second = state.execute("SELECT seq, record_sha256 FROM seen ORDER BY seq"), ordered()
            try:
                for row, (seq, digest) in zip(second, digests, strict=True):
                    # A second read of the private copy must match the validated first read.
                    require(row["seq"] == seq and sha256(canonical(row).encode("utf-8")) == digest,
                            "DIDM_INPUT_CHANGED")
                    yield {"record_sha256": digest, "row": row}
            finally:
                # A traceback keeps this frame alive. An open cursor would keep its connection
                # open after close(), and Windows could not delete the private files.
                digests.close()
                if hasattr(second, "close"):
                    second.close()

        def selected():
            return (digest for (digest,) in state.execute(
                "SELECT record_sha256 FROM selected ORDER BY valid, source_id, item_id"))

        def write_report(write):
            """The canonical JSON of the whole report, written one list item at a time."""
            streams = {"records": records, "selected_record_sha256": selected}
            for index, key in enumerate(sorted([*fields, *streams])):
                write(("," if index else "{") + canonical(key) + ":")
                if key in streams:
                    write("[")
                    for position, item in enumerate(streams[key]()):
                        write(("," if position else "") + canonical(item))
                    write("]")
                else:
                    write(canonical(fields[key]))
            write("}\n")

        yield SimpleNamespace(fields=fields, write=write_report)
    except sqlite3.Error:
        raise BridgeError("DIDM_SQLITE_INVALID_OR_LIMIT") from None
    finally:
        if snapshot is not None:
            snapshot.close()
        if state is not None:
            state.close()
        if input_kind == "sqlite":
            os.chmod(source, 0o600)  # permits private temporary cleanup on Windows


def inspect_snapshot(raw, *, input_kind, as_of):
    """The CLI's streamed report, parsed into memory (tests and small inputs)."""
    require(type(raw) is bytes and 0 < len(raw) <= MAX_INPUT_BYTES, "DIDM_INPUT_SIZE_LIMIT")
    parts = []
    with tempfile.TemporaryDirectory(prefix="tradegen-didm-snapshot-") as directory:
        source = raw
        if input_kind == "sqlite":
            source = Path(directory) / "snapshot.sqlite"
            source.write_bytes(raw)
        with inspection(source, input_kind=input_kind, input_sha256=sha256(raw),
                        as_of=as_of, directory=directory) as result:
            result.write(parts.append)
    return json.loads("".join(parts))


@contextmanager
def report_file(destination):
    """Yield write(text) into a temporary file beside destination; publish it only on a clean exit.

    No partial final file and no overwrite, including concurrent publishers. Any error inside
    the block, including a failed cleanup of private temporary files, publishes nothing.
    """
    destination = Path(destination).absolute()
    require(not os.path.lexists(destination), "DIDM_OUTPUT_EXISTS")
    require(destination.parent.is_dir(), "DIDM_OUTPUT_DIRECTORY_REQUIRED")
    fd, temporary = tempfile.mkstemp(prefix=".didm-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            size = 0
            def write(text):
                nonlocal size
                data = text.encode("utf-8")
                size += len(data)
                require(size <= MAX_OUTPUT_BYTES, "DIDM_OUTPUT_SIZE_LIMIT")
                stream.write(data)
            yield write
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link is an atomic no-clobber publication on supported local filesystems.
        # Unsupported filesystems refuse; there is no overwrite fallback.
        os.link(temporary, destination)
    finally:
        os.unlink(temporary)


def publish_report(report, destination):
    """Publish a report dict, or a function that streams the report text through write(text)."""
    with report_file(destination) as write:
        if callable(report):
            report(write)
        else:
            write(canonical(report) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--database", help="Explicit offline copy of the QUANTGEN DIDM SQLite store")
    source.add_argument("--export", help="Explicit tradegen-didm-exchange-v1 JSON file")
    parser.add_argument("--as-of", required=True, help="Timezone-aware ISO 8601 knowledge cutoff")
    parser.add_argument("--output", required=True, help="New PRIVATE report path; never overwritten")
    args = parser.parse_args(argv)
    try:
        # The report is published only after the private copy and scratch state are removed.
        with report_file(args.output) as write, \
                tempfile.TemporaryDirectory(prefix="tradegen-didm-snapshot-") as directory:
            if args.database:
                snapshot = Path(directory) / "snapshot.sqlite"
                with open(snapshot, "xb") as sink:
                    digest = copy_snapshot(args.database, sink.write, database=True,
                                           limit=MAX_DATABASE_BYTES)
            else:
                snapshot = read_snapshot(args.export)
                digest = sha256(snapshot)
            with inspection(snapshot, input_kind="sqlite" if args.database else "export",
                            input_sha256=digest, as_of=args.as_of, directory=directory) as result:
                result.write(write)
        report = result.fields
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
