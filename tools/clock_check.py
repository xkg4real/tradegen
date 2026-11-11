"""Read-only check of this PC's clock against Upbit public orderbook stamps.

    .\\.venv\\Scripts\\python.exe -X utf8 -m tools.clock_check [--symbol KRW-BTC] [--samples 20] [--interval-seconds 1]

Run it from the repository root in a normal terminal (not sign.py). It reuses execution_launch.quote_diagnostics over
the credential-free E1 quote source: public orderbook GETs only, with the transport's 0.2 s pacing and 1 s between
samples. It reads no key, .env or owner state, creates no file and never sets or syncs the clock. Every line holds
fixed codes and whole milliseconds (floored, so a negative stays negative): never a time of day, price or host name.

  CLOCK_CHECK  samples measured/requested, how many parse_orderbook admitted, and the stop reason
  LAG_MS       PC receipt minus book stamp. The PC runs at most LAG min ahead of Upbit; a negative min means it runs
               behind by at least that much, and such a book is refused (QUOTE_BOOK_STALE_OR_FUTURE)
  DATE_MS      PC receipt minus the HTTP Date header (one-second resolution)
  RTT_MS       request start to PC receipt
  REFUSED      samples parse_orderbook refused, per time code
  W32TM        `w32tm /query /status`, read only: leap (3 = not synchronized), source, seconds since the last
               successful sync (never = none since the time service started), poll interval

Medians are the lower middle sample. Exit 0: every requested sample was measured; exit 2 otherwise.
No clock offset estimate, synchronization proof or trading permission. Not legal or investment advice.
"""
from __future__ import annotations

from datetime import datetime
import re
from statistics import median_low
import subprocess
import sys
import time

from execution_accounts import quotes as Q
from execution_launch import quote_diagnostics as D

_REFUSALS = ("QUOTE_BOOK_STALE_OR_FUTURE", "QUOTE_RECEIPT_STALE_OR_FUTURE", "QUOTE_SERVER_CLOCK_MISMATCH")
_SOURCES = {"Local CMOS Clock": "LOCAL_CMOS", "Free-running System Clock": "FREE_RUNNING"}


def _ms(name: str, values_us: list[int]) -> str:
    if not values_us:
        return f"{name} min=none median=none max=none"
    return f"{name} min={min(values_us) // 1000} median={median_low(values_us) // 1000} max={max(values_us) // 1000}"


def lines(report: dict, symbol: str) -> list[str]:
    """The summary of one collect_timing report: fixed codes and floored milliseconds only."""
    samples = report["samples"]
    reasons = [sample["strict_quote_reason"] for sample in samples]
    rtt = [D._micros(datetime.fromisoformat(s["received_at"]) - datetime.fromisoformat(s["requested_at"]))
           for s in samples]
    return [f"CLOCK_CHECK symbol={symbol} samples={report['measured_samples']}/{report['requested_samples']} "
            f"admitted={report['strictly_admitted_samples']} reason={report['reason'] or 'none'}",
            _ms("LAG_MS", [sample["apparent_book_age_us"] for sample in samples]),
            _ms("DATE_MS", [sample["received_minus_http_date_us"] for sample in samples]),
            _ms("RTT_MS", rtt),
            "REFUSED " + " ".join(f"{code}={reasons.count(code)}" for code in _REFUSALS)]


def w32tm_line(run, local_now) -> str:
    """Windows time service status, read only; the source host name is never printed."""
    try:
        done = run(["w32tm", "/query", "/status"], capture_output=True, timeout=10, check=False)
    except (OSError, ValueError, subprocess.SubprocessError):
        return "W32TM status=unavailable"
    if done.returncode != 0 or type(done.stdout) is not bytes:
        return "W32TM status=unavailable"
    text = done.stdout.decode("ascii", "replace")
    leap = re.search(r"^Leap Indicator: *([0-3])\b", text, re.M)
    source = re.search(r"^Source: *(.+?)\s*$", text, re.M)
    poll = re.search(r"^Poll Interval: *-?\d+ \((\d+)s\)", text, re.M)
    sync = re.search(r"^Last Successful Sync Time: *(.+?)\s*$", text, re.M)
    kind = "unreadable" if source is None else _SOURCES.get(
        source[1], "VM" if source[1].startswith("VM IC ") else "SERVER")
    if sync is None:
        age = "unreadable"
    elif sync[1] == "unspecified":
        age = "never"
    else:
        try:   # ponytail: en-US date format only (this PC's); any other locale prints unparsed
            age = str(int((local_now() - datetime.strptime(sync[1], "%m/%d/%Y %I:%M:%S %p")).total_seconds()))
        except ValueError:
            age = "unparsed"
    return (f"W32TM status=ok leap={leap[1] if leap else 'unreadable'} source={kind} last_sync_age_s={age} "
            f"poll_s={poll[1] if poll else 'unreadable'}")


def main(argv=None, *, run=subprocess.run, local_now=datetime.now) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if values in (["--help"], ["-h"]):
        print(__doc__)
        return 0
    if "--symbol" not in values:
        values += ["--symbol", "KRW-BTC"]
    try:
        args = D._arguments(["capture", *values])
    except D.DiagnosticError as exc:
        code = str(exc) if str(exc) in D._DIAGNOSTIC_CODES else "QUOTE_DIAGNOSTIC_ARGUMENTS_INVALID"
        print("CLOCK_CHECK reason=" + code)
        return 2
    try:
        source = Q.E1UpbitQuoteSource(symbol=args["symbol"], clock=D._wall_clock)
        report = D.collect_timing(source=source, symbol=args["symbol"], samples=args["samples"],
                                  interval_seconds=args["interval-seconds"], monotonic_ns=time.monotonic_ns,
                                  wait=time.sleep)
        print("\n".join(lines(report, args["symbol"]) + [w32tm_line(run, local_now)]))
    except (Exception, KeyboardInterrupt):     # a traceback would print local paths: fixed code only
        print("CLOCK_CHECK reason=CLOCK_CHECK_FAILED")
        return 2
    return 0 if report["diagnostic_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
