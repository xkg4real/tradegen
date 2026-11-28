"""Same-second 10s Upbit quote + orderbook recorder for Stage 2 BR-26 replay.

Research only. Public GET only when --allow-public-network is passed on CLI.
Supports --app-not-running or external --status-file (stripping BID_GAP_TRIGGERED),
shares TransientPublicBudget cooldown coordination, writes hash-chained quotes.jsonl,
and exports frozen per-KST-day quote JSON + manifest with RESEARCH_FLAGS.
Zero imports from core.compliance, core.odds, execution*, tools.owner, config, or main.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import dataclass
import math
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

from tools.research import upbit_price_recorder as upr
from tools.research._study_common import (
    DEFAULT_MAX_BYTES,
    HashChainedLog,
    MARKET_RE,
    RESEARCH_FLAGS,
    StudyError,
    atomic_publish_json_ascii,
    canonical_ascii_str,
    kst_date_iso,
    loads_strict_json,
    read_strict_json_file,
    read_verified_chained_log,
    require,
    sha256_ascii,
)


QUOTE_RECORDER_SCHEMA = "tradegen-upbit-quote-recorder-v1"
DAILY_QUOTE_FORMAT = "tradegen-stage2-daily-quotes-v1"
DAILY_QUOTE_MANIFEST_FORMAT = "tradegen-stage2-daily-quotes-manifest-v1"
STRIPPED_BID_GAP_CAUSES = frozenset({"BID_GAP_TRIGGERED", "STALE_BID_GAP"})


@dataclass(frozen=True)
class QuoteRecorderConfig:
    market: str
    scope: str
    interval_seconds: int = 10
    requests_per_second: float = 4.0
    app_running: bool = False

    def validate(self) -> QuoteRecorderConfig:
        require(type(self.market) is str and MARKET_RE.fullmatch(self.market) is not None, "INVALID_MARKET")
        require(type(self.scope) is str and 0 < len(self.scope) <= 140, "INVALID_SCOPE")
        require(type(self.interval_seconds) is int and 1 <= self.interval_seconds <= 3600, "INVALID_INTERVAL")
        require(
            type(self.requests_per_second) in (int, float)
            and math.isfinite(self.requests_per_second)
            and 0.0 < self.requests_per_second <= 5.0,
            "INVALID_RATE",
        )
        require(type(self.app_running) is bool, "INVALID_CONFIG")
        return self

    def document(self) -> dict[str, Any]:
        self.validate()
        return {
            "market": self.market,
            "scope": self.scope,
            "interval_seconds": int(self.interval_seconds),
            "requests_per_second": float(self.requests_per_second),
            "app_running": bool(self.app_running),
        }


def _parse_ticker_row(body: Any, market: str) -> tuple[str, int]:
    require(type(body) is list and len(body) == 1 and type(body[0]) is dict, "MALFORMED_TICKER")
    item = body[0]
    require(item.get("market") == market, "MALFORMED_TICKER")
    _price_dec, price_str = upr.parse_positive_price(item.get("trade_price"), "MALFORMED_TICKER")
    ts_ms = item.get("trade_timestamp")
    require(type(ts_ms) is int and ts_ms >= 0, "MALFORMED_TICKER")
    return price_str, ts_ms // 1000


def parse_external_status_flags(
    status_doc: Mapping[str, Any],
    *,
    expected_second: int | None = None,
) -> dict[str, Any]:
    """Read external runtime status snapshot and strip BID_GAP_TRIGGERED causes."""
    require(type(status_doc) is dict, "INVALID_STATUS_SNAPSHOT")
    if expected_second is not None:
        require(type(expected_second) is int and type(status_doc.get("as_of")) is int
                and {"floor_halt", "daily_stop"} <= status_doc.keys()
                and ("block_causes" in status_doc or "prior_block_active" in status_doc),
                "INVALID_STATUS_SNAPSHOT")

    floor_halt = status_doc.get("floor_halt", False)
    daily_stop = status_doc.get("daily_stop", False)
    require(type(floor_halt) is bool and type(daily_stop) is bool, "INVALID_STATUS_SNAPSHOT")

    stripped: list[str] = []
    if "block_causes" in status_doc:
        causes = status_doc["block_causes"]
        require(type(causes) is list and all(type(c) is str for c in causes), "INVALID_STATUS_SNAPSHOT")
        if expected_second is not None and "prior_block_active" in status_doc:
            require(type(status_doc["prior_block_active"]) is bool
                    and status_doc["prior_block_active"] == bool(causes), "INVALID_STATUS_SNAPSHOT")
        remaining = []
        for cause in causes:
            if cause in STRIPPED_BID_GAP_CAUSES:
                stripped.append(cause)
            else:
                remaining.append(cause)
        prior_block = bool(remaining)
    else:
        raw_prior = status_doc.get("prior_block_active", False)
        require(type(raw_prior) is bool, "INVALID_STATUS_SNAPSHOT")
        reason = status_doc.get("block_reason")
        if raw_prior and type(reason) is str and reason in STRIPPED_BID_GAP_CAUSES:
            stripped.append(reason)
            prior_block = False
        else:
            prior_block = raw_prior

    if expected_second is not None and status_doc["as_of"] != expected_second:
        return {"prior_block_active": True, "floor_halt": floor_halt, "daily_stop": daily_stop,
                "stripped_causes": [], "status_stale": True}

    return {
        "prior_block_active": prior_block,
        "floor_halt": floor_halt,
        "daily_stop": daily_stop,
        "stripped_causes": stripped,
        "status_stale": False,
    }


class UpbitQuoteRecorder:
    """Same-second public ticker + orderbook recorder for Stage 2 replay."""

    def __init__(
        self,
        archive_dir: Path | str,
        config: QuoteRecorderConfig,
        *,
        transport: Callable[[str, Mapping[str, str | int]], upr.HttpReply] = upr.public_get,
        coordination_dir: Path | str | None = None,
        status_file: Path | str | None = None,
        clock: upr.Clock | None = None,
    ) -> None:
        self.archive_dir = Path(archive_dir)
        self.config = config.validate()
        if self.config.app_running:
            require(status_file is not None, "STATUS_FILE_REQUIRED_WHEN_APP_RUNNING")
        self.transport = transport
        self.coordination_dir = Path(coordination_dir) if coordination_dir is not None else None
        self.status_file = Path(status_file) if status_file is not None else None
        self.clock = clock or upr.Clock()
        self._next_mono = 0.0

    def _call_api(
        self,
        path: str,
        params: Mapping[str, str | int],
        budget: upr.TransientPublicBudget | None,
        log: HashChainedLog,
    ) -> tuple[Any, float]:
        if budget is not None:
            budget.check_cooldown()
        wait = self._next_mono - self.clock.monotonic()
        if wait > 0:
            self.clock.sleep(wait)
        sent_wall = self.clock.wall()
        self._next_mono = self.clock.monotonic() + (1.0 / self.config.requests_per_second)
        reply = self.transport(path, dict(params))
        recv_wall = self.clock.wall()
        require(recv_wall >= sent_wall, "CLOCK_ROLLBACK")

        if reply.status in (418, 429):
            hold = (
                budget.record_rate_limit(reply.status, reply.headers, recv_wall)
                if budget is not None
                else "UNCOORDINATED_RATE_LIMIT"
            )
            log.append({
                "kind": "rate_limit_stop",
                "status": reply.status,
                "path": path,
                "received_at": math.ceil(recv_wall),
                "hold": hold,
            })
            raise StudyError(f"RATE_LIMIT_STOP_{reply.status}")
        if reply.error is not None:
            raise StudyError(reply.error)
        require(not reply.truncated, "RESPONSE_TOO_LARGE")
        require(200 <= reply.status < 300, "HTTP_REFUSED")
        parsed = loads_strict_json(reply.body, max_bytes=upr.MAX_HTTP_BODY, size_error="RESPONSE_TOO_LARGE")
        return parsed, recv_wall

    def capture_once(self) -> dict[str, Any]:
        budget_ctx = (
            upr.TransientPublicBudget(self.coordination_dir, clock=self.clock)
            if self.coordination_dir is not None
            else nullcontext(None)
        )
        with HashChainedLog(self.archive_dir, "quotes.jsonl", lock_name=".quotes.lock") as log:
            if not log.entries:
                log.append({
                    "kind": "config",
                    "schema": QUOTE_RECORDER_SCHEMA,
                    "config": self.config.document(),
                })
            else:
                first_data = log.entries[0]["data"]
                require(
                    first_data == {"kind": "config", "schema": QUOTE_RECORDER_SCHEMA, "config": self.config.document()},
                    "ARCHIVE_CONFIG_MISMATCH",
                )

            prior_quotes = [e["data"] for e in log.entries if e["data"].get("kind") == "quote"]
            prev_as_of = prior_quotes[-1]["as_of"] if prior_quotes else -1

            with budget_ctx as active_budget:
                start_sec = int(self.clock.wall())
                ticker_body, _t_recv = self._call_api(
                    "/v1/ticker",
                    {"markets": self.config.market},
                    active_budget,
                    log,
                )
                ob_body, ob_recv = self._call_api(
                    "/v1/orderbook",
                    {"markets": self.config.market},
                    active_budget,
                    log,
                )
                finish_sec = int(ob_recv)

            require(finish_sec > prev_as_of, "QUOTE_CHRONOLOGY_NOT_INCREASING")
            last_trade_str, raw_trade_sec = _parse_ticker_row(ticker_body, self.config.market)
            last_trade_at = min(finish_sec, raw_trade_sec)

            _bid_dec, bid_str, _ask_dec, ask_str = upr._parse_orderbook_top(ob_body, self.config.market)
            same_second = start_sec == finish_sec
            # If calls crossed a second boundary, record bid_at = start_sec (< as_of) so replay marks BID_UNAVAILABLE honestly!
            bid_at = finish_sec if same_second else start_sec

            if not self.config.app_running:
                flags = {
                    "prior_block_active": False,
                    "floor_halt": False,
                    "daily_stop": False,
                    "stripped_causes": [],
                    "status_stale": False,
                }
            else:
                assert self.status_file is not None
                status_doc, _ = read_strict_json_file(self.status_file, max_bytes=64 * 1024, path_error="STATUS_FILE_REFUSED")
                flags = parse_external_status_flags(status_doc, expected_second=finish_sec)

            obs = {
                "sequence": len(prior_quotes) + 1,
                "as_of": finish_sec,
                "scope": self.config.scope,
                "last_trade_at": last_trade_at,
                "last_trade": last_trade_str,
                "bid_at": bid_at,
                "bid": bid_str,
                "prior_block_active": flags["prior_block_active"],
                "floor_halt": flags["floor_halt"],
                "daily_stop": flags["daily_stop"],
            }
            entry_data = {
                "kind": "quote",
                "as_of": finish_sec,
                "kst_date": kst_date_iso(finish_sec),
                "same_second": same_second,
                "ask": ask_str,
                "app_running": self.config.app_running,
                "stripped_causes": flags["stripped_causes"],
                "status_stale": flags["status_stale"],
                "observation": obs,
            }
            appended = log.append(entry_data)
            return {
                **RESEARCH_FLAGS,
                "status": "CAPTURED",
                "as_of": finish_sec,
                "same_second": same_second,
                "app_running": self.config.app_running,
                "stripped_causes": flags["stripped_causes"],
                "log_seq": appended["seq"],
                "archive_head_sha256": log.head_sha256,
            }


def export_daily_quotes(
    archive_dir: Path | str,
    output_path: Path | str,
    *,
    kst_date: str,
    expected_observations: int | None = None,
    exported_at: int | None = None,
) -> dict[str, Any]:
    """Export one KST day's frozen quote record + sidecar .manifest.json with RESEARCH_FLAGS."""
    entries, head = read_verified_chained_log(archive_dir, "quotes.jsonl")
    require(len(entries) > 0, "EMPTY_QUOTE_ARCHIVE")
    cfg_doc = entries[0]["data"]["config"]
    cfg = QuoteRecorderConfig(
        market=cfg_doc["market"],
        scope=cfg_doc["scope"],
        interval_seconds=cfg_doc["interval_seconds"],
        requests_per_second=cfg_doc["requests_per_second"],
        app_running=cfg_doc["app_running"],
    ).validate()

    day_rows = [
        e["data"] for e in entries[1:]
        if e["data"].get("kind") == "quote" and e["data"].get("kst_date") == kst_date
    ]
    require(len(day_rows) > 0, "NO_QUOTES_FOR_KST_DAY")

    observations: list[dict[str, Any]] = []
    valid_same_second = 0
    for idx, row in enumerate(day_rows, start=1):
        obs = dict(row["observation"])
        obs["sequence"] = idx
        if obs["bid"] is not None and obs["bid_at"] == obs["as_of"]:
            valid_same_second += 1
        observations.append(obs)

    exp_obs = (86400 // cfg.interval_seconds) if expected_observations is None else int(expected_observations)
    require(exp_obs > 0, "INVALID_EXPECTED_OBSERVATIONS")
    coverage = valid_same_second / float(exp_obs)

    daily_body = {
        "format": DAILY_QUOTE_FORMAT,
        **RESEARCH_FLAGS,
        "market": cfg.market,
        "scope": cfg.scope,
        "kst_date": kst_date,
        "interval_seconds": cfg.interval_seconds,
        "expected_observations": exp_obs,
        "app_running": cfg.app_running,
        "observation_count": len(observations),
        "valid_same_second_count": valid_same_second,
        "quote_coverage": round(coverage, 6),
        "observations": observations,
    }
    daily_body["quote_sha256"] = sha256_ascii(daily_body)

    out_file = Path(output_path)
    man_file = out_file.with_suffix(".manifest.json") if out_file.suffix.lower() == ".json" else Path(f"{out_file}.manifest.json")
    atomic_publish_json_ascii(out_file, daily_body, max_bytes=64 * 1024 * 1024)

    manifest = {
        "format": DAILY_QUOTE_MANIFEST_FORMAT,
        **RESEARCH_FLAGS,
        "market": cfg.market,
        "scope": cfg.scope,
        "kst_date": kst_date,
        "app_running": cfg.app_running,
        "quote_file": out_file.name,
        "quote_sha256": daily_body["quote_sha256"],
        "archive_head_sha256": head,
        "observation_count": len(observations),
        "valid_same_second_count": valid_same_second,
        "expected_observations": exp_obs,
        "quote_coverage": round(coverage, 6),
        "exported_at": int(time.time()) if exported_at is None else int(exported_at),
    }
    manifest["manifest_sha256"] = sha256_ascii(manifest)
    atomic_publish_json_ascii(man_file, manifest)
    return manifest


def read_daily_quotes(path: Path | str, expected_sha256: str | None = None) -> dict[str, Any]:
    doc, _ = read_strict_json_file(path, max_bytes=64 * 1024 * 1024, path_error="QUOTE_FILE", size_error="QUOTE_FILE_SIZE")
    return verify_daily_quotes(doc, expected_sha256)


def verify_daily_quotes(doc: Any, expected_sha256: str | None = None) -> dict[str, Any]:
    require(type(doc) is dict and doc.get("format") == DAILY_QUOTE_FORMAT, "QUOTE_FILE_FORMAT")
    for k, v in RESEARCH_FLAGS.items():
        require(doc.get(k) is v, "QUOTE_FILE_FLAGS")
    sha = doc.get("quote_sha256")
    body = {k: v for k, v in doc.items() if k != "quote_sha256"}
    require(sha256_ascii(body) == sha, "QUOTE_SHA256_MISMATCH")
    if expected_sha256 is not None:
        require(sha == expected_sha256, "QUOTE_SHA256_MISMATCH")
    return doc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cap = sub.add_parser("capture", help="Capture 10s same-second Upbit ticker + orderbook quotes")
    p_cap.add_argument("--market", required=True)
    p_cap.add_argument("--scope", required=True)
    p_cap.add_argument("--archive-dir", type=Path, required=True)
    p_cap.add_argument("--interval-seconds", type=int, default=10)
    p_cap.add_argument("--coordination-dir", type=Path)
    p_cap.add_argument("--cycles", type=int, default=1)
    flags_grp = p_cap.add_mutually_exclusive_group(required=True)
    flags_grp.add_argument("--app-not-running", action="store_true")
    flags_grp.add_argument("--status-file", type=Path)
    p_cap.add_argument("--allow-public-network", action="store_true")

    p_exp = sub.add_parser("export-day", help="Export frozen KST-day quote JSON + manifest")
    p_exp.add_argument("--archive-dir", type=Path, required=True)
    p_exp.add_argument("--kst-date", required=True, help="YYYY-MM-DD in Asia/Seoul")
    p_exp.add_argument("--expected-observations", type=int)
    p_exp.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.cmd == "capture" and not args.allow_public_network:
        parser.error("public Upbit reads require --allow-public-network; no request was made")

    try:
        if args.cmd == "capture":
            cfg = QuoteRecorderConfig(
                market=args.market,
                scope=args.scope,
                interval_seconds=args.interval_seconds,
                app_running=not args.app_not_running,
            ).validate()
            rec = UpbitQuoteRecorder(
                args.archive_dir,
                cfg,
                coordination_dir=args.coordination_dir,
                status_file=args.status_file,
            )
            last_res: dict[str, Any] = {}
            for i in range(args.cycles):
                last_res = rec.capture_once()
                if i + 1 < args.cycles:
                    time.sleep(args.interval_seconds)
            print(canonical_ascii_str(last_res))
            return 0
        manifest = export_daily_quotes(
            args.archive_dir,
            args.output,
            kst_date=args.kst_date,
            expected_observations=args.expected_observations,
        )
        print(canonical_ascii_str(manifest))
        return 0
    except StudyError as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError, KeyError):
        reason = "QUOTE_RECORDER_REFUSED"
    print(canonical_ascii_str({**RESEARCH_FLAGS, "reason": reason}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
