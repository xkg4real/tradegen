"""PC clock check (tools/clock_check.py): invented receipts, the hermetic E1 HTTP seam and fake w32tm output only."""
import ast
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner
from execution import keys
from execution_accounts import quotes as Q
from execution_launch import quote_diagnostics as D
from execution_launch.study import CAPTURE_FILES
from tests import accounts_quotes as B, execution_fixtures as F
from tests.launch_quote_diagnostics import NOW, SYMBOL, collect, reading
from tools import clock_check as C

ROOT = Path(__file__).resolve().parents[1]
LOCAL = datetime(2026, 11, 12, 3, 0, 0)                      # naive local time, as w32tm prints it
UNSYNCED = (b"Leap Indicator: 3(not synchronized)\r\nStratum: 0 (unspecified)\r\n"
            b"Precision: -23 (119.209ns per tick)\r\nRoot Delay: 0.0000000s\r\nRoot Dispersion: 0.0000000s\r\n"
            b"ReferenceId: 0x00000000 (unspecified)\r\nLast Successful Sync Time: unspecified\r\n"
            b"Source: Local CMOS Clock\r\nPoll Interval: 10 (1024s)\r\n\r\n")
SYNCED = (b"Leap Indicator: 0(no warning)\r\nStratum: 4 (secondary reference - syncd by (S)NTP)\r\n"
          b"Last Successful Sync Time: 11/12/2026 2:37:12 AM\r\nSource: private-ntp-host.example,0x9\r\n"
          b"Poll Interval: 15 (32768s)\r\n")


def w32tm(stdout=UNSYNCED, returncode=0):
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if isinstance(stdout, BaseException):
            raise stdout
        return SimpleNamespace(returncode=returncode, stdout=stdout)
    return run, calls


def invoke(*args, run=None):
    run = run or w32tm()[0]
    output = StringIO()
    with redirect_stdout(output):
        code = C.main(list(args), run=run, local_now=lambda: LOCAL)
    return code, output.getvalue()


def test_lines_floor_to_ms_keep_negative_lag_and_count_refusals():
    report, _, _ = collect([reading(age_ms=20), reading(shifted=1, age_ms=35), reading(shifted=2, age_ms=-2),
                            reading(shifted=3, received_at=NOW+timedelta(seconds=3, microseconds=600), age_ms=-1)])
    lines = C.lines(report, SYMBOL)
    assert lines[0] == "CLOCK_CHECK symbol=KRW-BTC samples=4/4 admitted=2 reason=none"
    assert lines[1] == "LAG_MS min=-2 median=-1 max=35", lines[1]   # -0.4 ms floors to -1: a negative stays negative
    assert lines[2] == "DATE_MS min=0 median=0 max=0", lines[2]
    assert lines[3] == "RTT_MS min=40 median=40 max=40", lines[3]
    assert lines[4] == ("REFUSED QUOTE_BOOK_STALE_OR_FUTURE=2 QUOTE_RECEIPT_STALE_OR_FUTURE=0 "
                        "QUOTE_SERVER_CLOCK_MISMATCH=0")


def test_no_sample_prints_none_and_the_fixed_reason():
    report, _, _ = collect([RuntimeError("private-provider-secret")])
    lines = C.lines(report, SYMBOL)
    assert lines[0] == "CLOCK_CHECK symbol=KRW-BTC samples=0/1 admitted=0 reason=QUOTE_DIAGNOSTIC_SOURCE_FAILED"
    assert lines[1:4] == ["LAG_MS min=none median=none max=none", "DATE_MS min=none median=none max=none",
                          "RTT_MS min=none median=none max=none"]
    assert "private-provider-secret" not in "\n".join(lines)


def test_w32tm_status_is_read_only_and_printed_as_codes():
    run, calls = w32tm()
    assert C.w32tm_line(run, lambda: LOCAL) == (
        "W32TM status=ok leap=3 source=LOCAL_CMOS last_sync_age_s=never poll_s=1024")
    assert calls[0][0] == ["w32tm", "/query", "/status"] and calls[0][1]["timeout"] > 0
    line = C.w32tm_line(w32tm(SYNCED)[0], lambda: LOCAL)
    assert line == "W32TM status=ok leap=0 source=SERVER last_sync_age_s=1368 poll_s=32768", line
    assert "private-ntp-host" not in line
    for stdout, expected in ((b"Source: Free-running System Clock\r\n", "source=FREE_RUNNING"),
                             (b"Source: VM IC Time Synchronization Provider\r\n", "source=VM"),
                             (b"Last Successful Sync Time: 2026-11-12 \xec\x98\xa4\xec\xa0\x84 2:37:12\r\n",
                              "last_sync_age_s=unparsed"),
                             (b"\xff private-junk\r\n", "leap=unreadable source=unreadable last_sync_age_s=unreadable "
                                                       "poll_s=unreadable")):
        line = C.w32tm_line(w32tm(stdout)[0], lambda: LOCAL)
        assert expected in line and "private" not in line, line
    for run in (w32tm(returncode=1)[0], w32tm(OSError("private-path"))[0], w32tm(TimeoutError())[0]):
        assert C.w32tm_line(run, lambda: LOCAL) == "W32TM status=unavailable"


def test_cli_sends_only_the_public_get_and_reads_no_key():
    raw = B.receipt().raw_body
    with patch.object(keys, "read", side_effect=AssertionError("credentials forbidden")) as credentials, \
            patch.object(D, "_wall_clock", return_value=NOW), \
            F.serve({("GET", Q.ORDERBOOK_PATH): lambda call: (200, {"Date": F.DATE_HEADER}, raw)}) as calls:
        code, text = invoke("--samples", "1")
    assert code == 0 and not credentials.called, text
    assert len(calls) == 1 and calls[0]["method"] == "GET" and calls[0]["json_body"] is None
    assert calls[0]["url"] == "https://api.upbit.com/v1/orderbook?markets=KRW-BTC&level=0&count=30"
    assert "Authorization" not in calls[0]["headers"]
    rows = text.splitlines()
    assert [row.split()[0] for row in rows] == ["CLOCK_CHECK", "LAG_MS", "DATE_MS", "RTT_MS", "REFUSED", "W32TM"]
    assert rows[0] == "CLOCK_CHECK symbol=KRW-BTC samples=1/1 admitted=1 reason=none", rows[0]
    for sensitive in ("ask_price", "bid_price", "orderbook_units", "account_scope", "raw_body", "2026", "+00:00"):
        assert sensitive not in text, sensitive


def test_help_and_bad_arguments_are_offline_and_not_echoed():
    run, calls = w32tm()
    with patch.object(Q, "E1UpbitQuoteSource", side_effect=AssertionError("unexpected request")):
        code, text = invoke("--help", run=run)
        assert code == 0 and "clock_check" in text
        for args in (("secret-value",), ("--symbol", "secret-value"), ("--samples", "61"), ("--samples", "0"),
                     ("--symbol", SYMBOL, "--symbol", SYMBOL), ("--url", "secret-value")):
            code, text = invoke(*args, run=run)
            assert code == 2 and text in ("CLOCK_CHECK reason=QUOTE_DIAGNOSTIC_ARGUMENTS_INVALID\n",
                                          "CLOCK_CHECK reason=QUOTE_DIAGNOSTIC_SYMBOL_INVALID\n"), (args, text)
    assert not calls, "w32tm ran for an offline invocation"


def test_tool_is_outside_every_signed_closure_and_imports_no_writer_or_key_reader():
    tree = ast.parse((ROOT / "tools" / "clock_check.py").read_text(encoding="utf-8"))
    assert "tools/clock_check.py" not in {name for name, _ in owner.code_files(ROOT)}
    assert "tools/clock_check.py" not in CAPTURE_FILES
    imported = {(node.module if isinstance(node, ast.ImportFrom) else alias.name).split(".")[0]
                for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert imported <= {"__future__", "datetime", "re", "statistics", "subprocess", "sys", "time",
                        "execution_accounts", "execution_launch"}, imported
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"open", "exec", "eval", "__import__", "getattr"}, names
