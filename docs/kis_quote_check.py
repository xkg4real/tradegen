"""KIS quote-field check (TASK-M1-01; spec Quick start L44, section 8.10 L5483, section 12 L6363; T-RO-02 record
clause). Quotation-only: every request is a GET on a `/uapi/.../quotations/` path. No order, cancel, account or
transfer path exists here or anywhere in QUANTGEN (P0).

The owner runs it on about 20 live KRX sessions:
    python docs/kis_quote_check.py [--session YYYY-MM-DD] [--codes 069500,005930] [--at 15:19:59]
                                   [--app-key-can-trade yes|no|unknown] [--out docs/kis_quote_check]
At 15:19:59 KST it records, per code, the level-1 asking-price payload (bid/ask, sizes, the exchange time field
`aspr_acpt_hour`) beside the receipt instant; after the regular-session close (15:40:30 KST, the close print bound +
10 min) it records, per market-division code (J = KRX, NX = NXT, UN = integrated), the price fields the current-price
and daily-chart endpoints return, so the owner can mark which code and field equal the KRX regular-session official
close. The record is written to `<out>/<session>.json`.

Without KIS credentials it prints `not run: owner must run this with KIS credentials over ~20 live sessions`, writes
a `status: "not run"` record and exits 2; the dependent features (R-27 snapshots, R-08 spread snapshots, the R-26
stress-line calibration) stay labelled UNVERIFIED. Never run inside the test suite.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402

KST = timezone(timedelta(hours=9))
OUT_DIR = ROOT / "docs" / "kis_quote_check"
NOT_RUN_MESSAGE = "not run: owner must run this with KIS credentials over ~20 live sessions"
CODES = ("069500", "005930")
# Every path here is in config.KIS_QUOTATION_ALLOWLIST (the M1 read-only guard); the client refuses any other.
PATHS = {"asking_price": "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",
         "price": "/uapi/domestic-stock/v1/quotations/inquire-price",
         "daily": "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"}
TR_IDS = {"asking_price": "FHKST01010200", "price": "FHKST01010100", "daily": "FHKST03010100"}
MARKET_DIV_CODES = {"J": "KRX", "NX": "NXT", "UN": "integrated"}
LEVEL1_FIELDS = ("bidp1", "askp1", "bidp_rsqn1", "askp_rsqn1", "total_bidp_rsqn", "total_askp_rsqn", "aspr_acpt_hour")
PRICE_FIELDS = ("stck_prpr", "stck_oprc", "stck_hgpr", "stck_lwpr", "stck_prdy_clpr", "acml_vol", "stck_clpr")
UNVERIFIED = {"R-27 snapshots": "UNVERIFIED", "R-08 spread snapshots": "UNVERIFIED", "R-26 stress-line calibration": "UNVERIFIED"}


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def not_run_record(session: date, *, app_key_can_trade: str = "unknown") -> dict:
    return {"schema": "quantgen/kis_quote_check", "status": "not run", "reason": NOT_RUN_MESSAGE,
            "session": session.isoformat(), "codes": list(CODES), "requested_at_kst": None, "sessions": [],
            "level1_fields": [], "exchange_ts_field": None, "receipt_ts_field": "receipt_utc",
            "official_close": {"market_div_code": None, "price_field": None, "candidates": []},
            "app_key_can_trade": app_key_can_trade, "dependent_features": dict(UNVERIFIED), "evidence": [],
            "read_only": True, "paths": sorted(PATHS.values())}


def write_record(record: dict, out_dir: Path = OUT_DIR) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{record['session']}.json"
    fd, tmp = tempfile.mkstemp(dir=out_dir, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def snapshot(client, code: str, clock, *, market_div: str = "J") -> dict:
    """One level-1 asking-price GET: raw output beside the receipt instant (never a decision input)."""
    sent = clock()
    payload = client._get(PATHS["asking_price"], TR_IDS["asking_price"],
                          {"FID_COND_MRKT_DIV_CODE": market_div, "FID_INPUT_ISCD": code}, retry=False)
    received = clock()
    out = payload.get("output1") or payload.get("output") or {}
    return {"code": code, "market_div_code": market_div, "sent_utc": _iso(sent), "receipt_utc": _iso(received),
            "exchange_time_kst": out.get("aspr_acpt_hour"), "level1": {k: out.get(k) for k in LEVEL1_FIELDS},
            "raw_fields": sorted(out), "receipt_headers": dict(getattr(client, "last_headers", {}) or {})}


def official_close_probe(client, code: str, session: date, clock) -> list[dict]:
    """Per market-division code, the price fields of the current-price and daily-chart endpoints after the close."""
    rows = []
    for div, label in MARKET_DIV_CODES.items():
        for kind, params in (("price", {"FID_COND_MRKT_DIV_CODE": div, "FID_INPUT_ISCD": code}),
                             ("daily", {"FID_COND_MRKT_DIV_CODE": div, "FID_INPUT_ISCD": code,
                                        "FID_INPUT_DATE_1": session.strftime("%Y%m%d"), "FID_INPUT_DATE_2": session.strftime("%Y%m%d"),
                                        "FID_PERIOD_DIV_CODE": "D", "FID_ORG_ADJ_PRC": "1"})):
            try:
                payload = client._get(PATHS[kind], TR_IDS[kind], params, retry=False)
                outs = payload.get("output2") or [payload.get("output") or {}]
                out = outs[0] if isinstance(outs, list) and outs else outs
                rows.append({"code": code, "market_div_code": div, "venue": label, "endpoint": kind, "receipt_utc": _iso(clock()),
                             "fields": {k: out.get(k) for k in PRICE_FIELDS if k in out}, "error": None})
            except Exception as exc:                 # recorded, never raised: the owner reads the evidence
                rows.append({"code": code, "market_div_code": div, "venue": label, "endpoint": kind,
                             "receipt_utc": _iso(clock()), "fields": {}, "error": f"{type(exc).__name__}: {exc}"})
    return rows


def _wait_until(target_kst: datetime, clock, sleep=time.sleep) -> None:
    while clock() < target_kst:
        sleep(min(5.0, max(0.0, (target_kst - clock()).total_seconds())))


def run(client, session: date, clock, *, codes=CODES, at="15:19:59", app_key_can_trade="unknown", sleep=time.sleep) -> dict:
    h, m, s = (int(x) for x in at.split(":"))
    target = datetime(session.year, session.month, session.day, h, m, s, tzinfo=KST)
    _wait_until(target, clock, sleep)
    record = not_run_record(session, app_key_can_trade=app_key_can_trade)
    record.update({"status": "run", "reason": "", "requested_at_kst": target.isoformat(),
                   "level1_fields": list(LEVEL1_FIELDS), "exchange_ts_field": "aspr_acpt_hour"})
    record["sessions"] = [snapshot(client, c, clock) for c in codes]
    close_probe_at = datetime(session.year, session.month, session.day, 15, 40, 30, tzinfo=KST)   # close + 10 min (L1493)
    _wait_until(close_probe_at, clock, sleep)
    record["official_close"]["candidates"] = [row for c in codes for row in official_close_probe(client, c, session, clock)]
    record["evidence"].append("owner marks official_close.market_div_code / price_field after comparing the candidates "
                              "with the KRX marketplace regular-session close (not an NXT or integrated print)")
    return record


def main(argv=None, *, clock=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--session", default=None, help="KRX session date YYYY-MM-DD (default: today in KST)")
    p.add_argument("--codes", default=",".join(CODES))
    p.add_argument("--at", default="15:19:59", help="KST snapshot time")
    p.add_argument("--app-key-can-trade", choices=("yes", "no", "unknown"), default="unknown",
                   help="owner attestation from the KIS developer portal: QUANTGEN never probes trading (P0)")
    p.add_argument("--out", default=str(OUT_DIR))
    args = p.parse_args(argv)
    clock = clock or (lambda: datetime.now(timezone.utc))          # CLI entry only; library functions take `clock`
    session = date.fromisoformat(args.session) if args.session else clock().astimezone(KST).date()
    if not config.kis_ready():
        print(NOT_RUN_MESSAGE)
        path = write_record(not_run_record(session, app_key_can_trade=args.app_key_can_trade), Path(args.out))
        print(f"recorded: {path}")
        return 2
    from data.krx.kis_client import KISClient                   # imported only when credentials exist
    client = KISClient()
    record = run(client, session, clock, codes=tuple(c.strip() for c in args.codes.split(",") if c.strip()),
                 at=args.at, app_key_can_trade=args.app_key_can_trade)
    path = write_record(record, Path(args.out))
    print(f"recorded: {path} ({len(record['sessions'])} snapshots, {len(record['official_close']['candidates'])} close candidates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
