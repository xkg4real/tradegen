"""The poller and the alert CLI (E1 plan Task 12; spec 4 "Data flow per poll", 7 "Alert records and delivery" and
"The poller", 10; E7, E11, E23, E24, E30, E33, E37, E40, E42, E43; E1R2-1, E1R2-4, E1R2-9, E1R2-12).

Every CLI case calls poll.main(argv) in this process (contract 0.2) through _main(), which scripts poll.datetime (the
one clock main() reads) and puts back transport._clock (which main() sets). An unsigned home points
owner.PUBKEY_PATH at an absent file, so KIS sends nothing (E42); a signed home is F.full_home's, so KIS sends through
EF.serve's router. No later task appends to this module.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core import isolation
from core.compliance import model, owner
from execution import checks, keys, poll, snapshot, transport
from tests import compliance_fixtures as F
from tests import execution_fixtures as EF
from tests import execution_guards as EG

NOW = EF.NOW                                        # 2026-10-24T00:00:00Z, 09:00 KST on a Saturday
UTC = model.iso_utc(NOW)
DAY = date(2026, 10, 24)                            # NOW's Seoul date
MINUTE = timedelta(minutes=1)
LIMITS = {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}
# Every fake value that must never reach a file, a summary, a toast or stdout (E37). The two-digit account product
# code is left out: any hex digest or timestamp may hold those two digits, so their absence cannot be scanned for.
SECRETS = tuple(v for v in EF.FAKE_KEYS.values() if len(v) >= 8) + ("test-token-1",)
BALANCES = ("20000", "21000", "61000", "0.0001", "1390", "bc1q")      # fixture amounts, a rate and the address
UNSET = ["FLOOR: not set", "DAILY_LOSS: not set", "OKX_CAP: not set"]
NO_LIVE = ["FLOOR: no live positions", "DAILY_LOSS: no live positions", "OKX_CAP: no live positions"]
# The contract 3.2 fixtures, counted: KIS 005930 and AAPL, one domestic fill; Upbit BTC, one closed order with
# volume, one deposit, one registered address; OKX USDT (trading) and BTC (funding), one fill, one deposit.
COUNTS = {"kis": {"holdings": 2, "open_orders": 0, "fills": 1, "deposits": 0, "withdrawals": 0, "addresses": 0},
          "upbit": {"holdings": 1, "open_orders": 0, "fills": 1, "deposits": 1, "withdrawals": 0, "addresses": 1},
          "okx": {"holdings": 2, "open_orders": 0, "fills": 1, "deposits": 1, "withdrawals": 0, "addresses": 0}}
ZERO = {"holdings": 0, "open_orders": 0, "fills": 0, "deposits": 0, "withdrawals": 0, "addresses": 0}
UPBIT_500 = (500, {"error": {"name": "server_error", "message": "x"}})
UPBIT_MORE_BTC = [{"currency": "KRW", "balance": "20000.0", "locked": "0", "avg_buy_price": "0",
                   "avg_buy_price_modified": False, "unit_currency": "KRW"},
                  {"currency": "BTC", "balance": "0.0002", "locked": "0", "avg_buy_price": "100000000",
                   "avg_buy_price_modified": False, "unit_currency": "KRW"}]
# One failure on every venue, as _routes() keywords (each route named as Tasks 5-7 name it).
AUTH_ERRORS = {"kis": {"balance": (401, {"rt_cd": "1", "msg_cd": "EGW00205", "msg1": "x"})},
               "upbit": {"accounts": (401, {"error": {"name": "out_of_scope", "message": "x"}})},
               "okx": {"config": {"code": "50120", "msg": "x", "data": []}}}
SERVER_ERRORS = {"kis": {"balance": (500, {"rt_cd": "1", "msg_cd": "", "msg1": ""})},
                 "upbit": {"accounts": UPBIT_500},
                 "okx": {"time": (500, {"code": "1", "msg": "", "data": []})}}
FIELD_ERRORS = {"kis": {"balance": {"rt_cd": "0", "msg_cd": "", "msg1": ""}},
                "upbit": {"accounts": [{"currency": "KRW"}]},
                "okx": {"balance": {"code": "0", "msg": "", "data": [{}]}}}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class _Clock(datetime):
    """poll.datetime for one main() call: now() gives the scripted instants in turn, then the last one for good."""
    times: list = []

    @classmethod
    def now(cls, tz=None):
        return cls.times.pop(0) if len(cls.times) > 1 else cls.times[0]


def _main(argv: list[str], *times: datetime) -> tuple[int, str, str]:
    """poll.main(argv) in this process with its clock scripted (NOW unless `times` are given); transport._clock,
    which main() sets, is put back. Returns (exit code, stdout, stderr)."""
    saved = (vars(poll)["datetime"], vars(transport)["_clock"])
    _Clock.times = list(times or (NOW,))
    out, err = io.StringIO(), io.StringIO()
    poll.datetime = _Clock
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = poll.main(argv)
    finally:
        poll.datetime, transport._clock = saved
    return code, out.getvalue(), err.getvalue()


def _home() -> Path:
    """The test's temp TRADEGEN_HOME (the suite wrapper's)."""
    return Path(os.environ["TRADEGEN_HOME"])


def _rows() -> list[dict]:
    return snapshot.read_all(poll.alerts_path())


@contextlib.contextmanager
def _unsigned() -> Iterator[None]:
    """No owner key: owner state BROKEN and code_signed False, so KIS sends nothing (E42)."""
    with F.pubkey_at(_home() / "absent.pem"):
        yield


@contextlib.contextmanager
def _signed(**kw) -> Iterator[None]:
    """A signed home (contract 3.2): the test key at home/owner_pubkey.pem, the shipped drafts approved and the code
    on disk signed, so load_context gives code_signed True; `kw` passes `limits` and `cap` to F.full_home. NotRun
    PENDING without cryptography. Inside the block load_context runs once per Seoul day (_one_context_a_day)."""
    with F.pubkey_at(_home() / "owner_pubkey.pem"):
        F.full_home(_home(), **kw)
        with _one_context_a_day():
            yield


@contextlib.contextmanager
def _one_context_a_day() -> Iterator[None]:
    """owner.load_context memoised per Seoul date for the block: the owner log does not change inside a test and a
    poll reads only ctx.owner and ctx.code_signed (E24), so each later poll of a day reuses that day's first
    context. ponytail: a signed load_context parses the approved tables (about 1.5 s on the owner's PC) and the
    suite has 60 s (X8); test_unsigned_code_sends_nothing_to_kis_and_alerts_once_a_day keeps the real one per poll."""
    real, memo = vars(owner)["load_context"], {}

    def per_day(now, positions, **kw):
        day = now.astimezone(model.KST).date()
        if day not in memo:
            memo[day] = real(now, positions, **kw)
        return memo[day]
    owner.load_context = per_day
    try:
        yield
    finally:
        owner.load_context = real


@contextlib.contextmanager
def _keyless() -> Iterator[None]:
    """The KEYLESS prefix in-process (contract 0.2): every E1 key name present as '<unset>', and keys._ENV_FILE at a
    temp .env holding the fake values, which a reader that fell back to the file would find."""
    env_file = _home() / "fake.env"
    env_file.write_text("".join(f"{k}={v}\n" for k, v in EF.FAKE_KEYS.items()), encoding="utf-8")
    saved, before = vars(keys)["_ENV_FILE"], {name: os.environ.get(name) for name in EF.FAKE_KEYS}
    os.environ.update(dict.fromkeys(EF.FAKE_KEYS, "<unset>"))
    keys._ENV_FILE = env_file
    try:
        yield
    finally:
        keys._ENV_FILE = saved
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _routes(kis: dict | None = None, upbit: dict | None = None, okx: dict | None = None) -> dict:
    """Every venue's fixture routes for EF.serve (Tasks 5-7), each venue's answers changed by route name."""
    return EF.kis_routes(**(kis or {})) | EF.upbit_routes(**(upbit or {})) | EF.okx_routes(**(okx or {}))


def _hard_link(path: Path) -> None:
    """Gives `path` a second name, so checked_target refuses to write it (A0). Called after the state root was
    scanned once (snapshot.home() or F.full_home): the scan is then remembered clean and only the final-target check
    sees the link."""
    other = _home() / f"other-{path.name}"
    other.write_bytes(b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.link(other, path)


def _crash_row(venue: str, utc: str) -> dict:
    return checks.row(checks.Alert(venue=venue, kind="OUTAGE", level="amber", text_key="OUTAGE_CRASH",
                                   slots={"when": utc}), utc)


def _unlogged_toast(moment: datetime) -> tuple[str, str]:
    return ("TRADEGEN E1 amber", checks.render(checks.Alert(venue="all", kind="OUTAGE", level="amber",
                                                            text_key="CRASH_UNLOGGED",
                                                            slots={"when": model.iso_utc(moment)})))


def _not_set_row(items: list[str], utc: str) -> dict:
    return checks.row(checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                                   slots={"skipped": "; ".join(items)}), utc)


# --------------------------------------------------------------------------- #
# One poll (spec 4 data flow; contract 16.2)
# --------------------------------------------------------------------------- #
def test_a_signed_poll_reads_every_venue_and_records_once():
    """A signed home with limits and the OKX cap: three inquiry lines, the first evidence records, the fresh alert
    rows (sent false) with one toast each, and a summary of counts without a balance. A minute later nothing repeats.
    A failed venue leaves the others ok, gives no live positions and clears nothing of its own (E19). A broken
    evidence chain appends nothing, raises the amber EVIDENCE_BROKEN and the poll completes (E33)."""
    with _signed(limits=LIMITS, cap=0.10), EF.fake_keys():
        with EF.serve(_routes()):
            first = poll.poll_once(NOW)
            rows1, toasts1, evidence1 = _rows(), list(EF.TOASTS), owner.evidence_path().read_bytes()
            second = poll.poll_once(NOW + MINUTE)
            rows2, evidence2 = _rows(), owner.evidence_path().read_bytes()
        with EF.serve(_routes(upbit={"accounts": UPBIT_500})):
            third = poll.poll_once(NOW + 2 * MINUTE)
        rows3, evidence3, toasts3 = _rows(), owner.evidence_path().read_bytes(), list(EF.TOASTS)
        owner.evidence_path().write_bytes(b"not a record\n")
        with EF.serve(_routes()):
            fourth = poll.poll_once(NOW + 3 * MINUTE)
        code, out, _ = _main(["--pending"])
    assert first == {"utc": UTC, "venues": dict.fromkeys(snapshot.VENUES, "ok"), "errors": {}, "counts": COUNTS,
                     "evidence": 4, "alerts": 1, "not_set": []}, first
    assert not any(b in json.dumps(first) for b in BALANCES)
    lines = snapshot.read_all(snapshot.inquiry_path(DAY))
    assert [(r["venue"], r["ok"], r["utc"]) for r in lines[:3]] == [(v, True, UTC) for v in snapshot.VENUES]
    assert [snapshot.load(r).venue for r in lines] == list(snapshot.VENUES) * 4          # every line re-hashes
    records, why = owner.evidence_chain(evidence1.splitlines(keepends=True))
    assert why == "" and [(r["requirement"], r["met"], r["snapshot_sha256"]) for r in records] == [
        (k, False, lines[0]["snapshot_sha256"]) for k in owner.EVIDENCE_THRESHOLDS_KRW], records
    unsigned = checks.Alert(venue="upbit", kind="ADDRESS_LIST", level="red", text_key="ADDRESS_UNSIGNED",
                            slots={"n": 1})
    assert rows1 == [checks.row(unsigned, UTC)] and rows1[0]["sent"] is False, rows1
    assert toasts1 == [("TRADEGEN E1 red", checks.render(unsigned))], toasts1
    assert (second["alerts"], second["evidence"], rows2, evidence2) == (0, 0, rows1, evidence1), second
    assert third["venues"] == {"kis": "ok", "upbit": "error", "okx": "ok"} and third["not_set"] == NO_LIVE, third
    assert rows3[len(rows2):] == [_not_set_row(NO_LIVE, model.iso_utc(NOW + 2 * MINUTE))]      # no clear row
    assert (third["evidence"], evidence3, toasts3) == (0, evidence1, toasts1), third
    broken = checks.Alert(venue="kis", kind="EVIDENCE", level="amber", text_key="EVIDENCE_BROKEN")
    assert fourth["evidence"] == "broken" and fourth["venues"] == dict.fromkeys(snapshot.VENUES, "ok"), fourth
    assert owner.evidence_path().read_bytes() == b"not a record\n"
    assert _rows()[len(rows3):] == [checks.row(broken, model.iso_utc(NOW + 3 * MINUTE))], _rows()
    assert EF.TOASTS == toasts1 + [("TRADEGEN E1 amber", checks.render(broken))], EF.TOASTS
    assert code == 0 and len(out.splitlines()) == 1 and out.isascii() and not any(b in out for b in BALANCES)
    assert json.loads(out) == {"send": True, "subject": "TRADEGEN E1: 2 alert(s), 1 red",
                               "body": f"2026-10-24 09:00 KST red: {checks.render(unsigned)}\n"
                                       f"2026-10-24 09:03 KST amber: {checks.render(broken)}",
                               "utcs": [UTC, model.iso_utc(NOW + 3 * MINUTE)]}


def test_unsigned_code_sends_nothing_to_kis_and_alerts_once_a_day():
    """E1R2-9 (E42): with every route served and the fake keys set, an unsigned home polls Upbit and OKX but sends
    nothing to KIS, the token POST included, and records no evidence; one amber KIS_UNSIGNED a day and no OUTAGE
    after three polls. Each poll loads its context once, first, with the placeholder positions (E24)."""
    loads, real = [], vars(owner)["load_context"]
    with _unsigned(), EF.fake_keys(), EF.serve(_routes()) as calls:
        def recording(now, positions, **kw):
            loads.append((now, len(calls), positions))
            return real(now, positions, **kw)
        owner.load_context = recording
        try:
            for i in range(3):
                before = len(calls)
                summary = poll.poll_once(NOW + 5 * i * MINUTE)
                assert len(loads) == i + 1 and loads[i][:2] == (NOW + 5 * i * MINUTE, before), loads
                assert loads[i][2] is poll.PLACEHOLDER
        finally:
            owner.load_context = real
    paths = {c["path"] for c in calls}
    assert not [p for p in paths if p.startswith("/uapi/") or p == "/oauth2/tokenP"], paths
    assert {"/v1/accounts", "/api/v5/account/balance"} <= paths, paths
    kis = [r for r in snapshot.read_all(snapshot.inquiry_path(DAY)) if r["venue"] == "kis"]
    assert [(r["ok"], r["error"], r["flags"]) for r in kis] == [(False, "code not signed", ["code_unsigned"])] * 3
    assert summary["venues"] == {"kis": "error", "upbit": "ok", "okx": "ok"}, summary
    assert summary["evidence"] == 0 and not owner.evidence_path().exists()          # no D16 evidence (E42)
    assert [(r["venue"], r["text_key"], r["level"]) for r in _rows()] == [("kis", "KIS_UNSIGNED", "amber"),
                                                                          ("all", "NOT_SET", "info")]
    assert EF.TOASTS == [("TRADEGEN E1 amber", checks.TEXT["KIS_UNSIGNED"][2])], EF.TOASTS


def test_each_seoul_day_has_its_own_inquiry_file_and_a_poll_reads_two():
    """E1R2-4 (E30): a poll at 23:59:59 KST and one at 00:00:00 KST write two files; the second poll compares with
    the first (yesterday's file) and opens only yesterday's and today's, so a file two days back is never read; no
    file is deleted or rewritten."""
    late = datetime(2026, 10, 24, 14, 59, 59, tzinfo=timezone.utc)      # 23:59:59 KST, 2026-10-24
    early = late + timedelta(seconds=1)                                  # 00:00:00 KST, 2026-10-25
    old = snapshot.inquiry_path(date(2026, 10, 23))                      # two days before `early`'s Seoul date
    planted = snapshot.dump(snapshot.failed("upbit", "2026-10-23T03:00:00Z", "upbit: /v1/accounts: InquiryError"))
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes(planted)
    reads, real_read = [], vars(snapshot)["read_all"]

    def recording(path):
        reads.append(Path(path).name)
        return real_read(path)
    with _unsigned(), EF.fake_keys():
        with EF.serve(_routes()):
            poll.poll_once(late)
        snapshot.read_all = recording
        try:
            with EF.serve(_routes(upbit={"accounts": UPBIT_MORE_BTC})):
                poll.poll_once(early)
        finally:
            snapshot.read_all = real_read
    first, second = snapshot.inquiry_path(date(2026, 10, 24)), snapshot.inquiry_path(date(2026, 10, 25))
    assert [r["utc"] for r in snapshot.read_all(first)] == ["2026-10-24T14:59:59Z"] * 3
    assert [r["utc"] for r in snapshot.read_all(second)] == ["2026-10-24T15:00:00Z"] * 3
    assert [n for n in reads if n.startswith("inquiry-")] == [first.name, second.name], reads
    assert old.read_bytes() == planted
    assert sorted(p.name for p in snapshot.home().glob("inquiry-*.jsonl")) == [
        "inquiry-20261023.jsonl", "inquiry-20261024.jsonl", "inquiry-20261025.jsonl"]
    changed = checks.Alert(venue="upbit", kind="HOLDINGS_CHANGED", level="red", text_key="HOLDINGS_UNEXPLAINED",
                           slots={"n": 1, "k": 1, "fills": 0, "deposits": 0, "withdrawals": 0})
    assert [r for r in _rows() if r["kind"] == "HOLDINGS_CHANGED"] == [checks.row(changed, model.iso_utc(early))]


def test_the_not_set_row_is_written_once_a_day_and_never_sent():
    """E1R2-12 (E43): the first poll of a Seoul day with skipped checks writes one NOT_SET row (info, sent true, its
    items the summary's not_set) and toasts nothing for it; a second poll that day writes none; the first poll of the
    next day writes one; --pending never lists it."""
    with _unsigned():
        first = poll.poll_once(NOW)
        rows1 = _rows()
        assert poll.poll_once(NOW + 5 * MINUTE)["alerts"] == 0 and _rows() == rows1
        poll.poll_once(NOW + timedelta(days=1))
    items = ["KIS: code not signed", "Upbit: keys not in .env", "OKX: keys not in .env", *UNSET,
             "ADDRESS_LIST: owner log not OK"]
    assert first["not_set"] == items and first["alerts"] == 3, first
    assert [r for r in rows1 if r["kind"] == "NOT_SET"] == [_not_set_row(items, UTC)], rows1
    rows = _rows()
    assert [r["kind"] for r in rows].count("NOT_SET") == 2 and all(checks.verify_row(r) for r in rows), rows
    assert len(EF.TOASTS) == 6 and not [b for _t, b in EF.TOASTS if b.startswith("Checks skipped")], EF.TOASTS
    message = poll.pending(rows)
    assert message["subject"] == "TRADEGEN E1: 6 alert(s), 0 red" and "Checks skipped" not in message["body"]
    assert message["utcs"] == [UTC, model.iso_utc(NOW + timedelta(days=1))], message


# --------------------------------------------------------------------------- #
# Refused writes and crashes (spec 10; E33, E40)
# --------------------------------------------------------------------------- #
def test_a_hard_linked_inquiry_file_is_a_crash_alerted_for_every_venue():
    """A refused inquiry write stops the poll: --once prints the crash line (type and place, never the exception's
    text), writes OUTAGE_CRASH for every venue, toasts each and returns 4."""
    with _unsigned():
        snapshot.home()                                  # the state-root scan, remembered clean
        _hard_link(snapshot.inquiry_path(DAY))
        code, out, _ = _main(["--once"])
    crash = json.loads(out.splitlines()[0])
    assert code == 4 and len(out.splitlines()) == 1, (code, out)
    assert set(crash) == {"crash", "at"} and crash["crash"] == "RuntimeError" and crash["at"].startswith(
        "isolation.py:"), crash
    assert "hard link" not in out and str(_home()) not in out
    assert _rows() == [_crash_row(v, UTC) for v in snapshot.VENUES]
    assert EF.TOASTS == [("TRADEGEN E1 amber", checks.render(checks.Alert(
        venue=v, kind="OUTAGE", level="amber", text_key="OUTAGE_CRASH", slots={"when": UTC}))) for v in snapshot.VENUES]
    assert snapshot.inquiry_path(DAY).read_bytes() == b""


def test_a_hard_linked_evidence_log_is_a_crash_not_evidence_broken():
    """E33: a refused evidence.jsonl write is a crash (OUTAGE_CRASH), never EVIDENCE_BROKEN; the inquiry lines of
    that poll were already written."""
    with _signed(), EF.fake_keys(), EF.serve(_routes()):
        snapshot.home()
        _hard_link(owner.evidence_path())
        code, out, _ = _main(["--once"])
    assert code == 4 and json.loads(out.splitlines()[0])["crash"] == "RuntimeError", out
    assert [r["text_key"] for r in _rows()] == ["OUTAGE_CRASH"] * 3
    assert owner.evidence_path().read_bytes() == b""
    assert len(snapshot.read_all(snapshot.inquiry_path(DAY))) == 3


def test_a_hard_linked_kis_token_cache_is_a_crash_before_any_token_post():
    """E33: the shared token cache is checked before the token POST, so a hard-linked kis_token.json crashes the poll
    with no KIS call at all."""
    with _signed(), EF.fake_keys(), EF.serve(_routes()) as calls:
        snapshot.home()
        _hard_link(_home() / "kis_token.json")
        code, out, _ = _main(["--once"])
    assert code == 4 and json.loads(out.splitlines()[0])["crash"] == "RuntimeError", out
    assert not [c for c in calls if c["path"] == "/oauth2/tokenP" or c["path"].startswith("/uapi/")], calls
    assert [r["text_key"] for r in _rows()] == ["OUTAGE_CRASH"] * 3
    assert not snapshot.inquiry_path(DAY).exists()


def test_unwritable_alerts_toast_crash_unlogged_once_per_seoul_day():
    """E40: when checked_target refuses alerts.jsonl (here a hard link), neither the poll's rows nor OUTAGE_CRASH
    land; main toasts CRASH_UNLOGGED directly, once per process per Seoul date, prints both crash lines and
    returns 4."""
    saved = set(poll._unlogged)
    poll._unlogged.clear()
    try:
        with _unsigned():
            snapshot.home()
            _hard_link(poll.alerts_path())
            runs = [_main(["--once"]), _main(["--once"], NOW + 5 * MINUTE)]
            assert EF.TOASTS == [_unlogged_toast(NOW)], EF.TOASTS
            runs.append(_main(["--once"], NOW + timedelta(days=1)))
    finally:
        poll._unlogged.clear()
        poll._unlogged.update(saved)
    assert [code for code, _o, _e in runs] == [4, 4, 4]
    for _code, out, _err in runs:
        assert [json.loads(line)["crash"] for line in out.splitlines()] == ["RuntimeError", "RuntimeError"], out
    assert EF.TOASTS == [_unlogged_toast(NOW), _unlogged_toast(NOW + timedelta(days=1))], EF.TOASTS
    assert poll.alerts_path().read_bytes() == b""


def test_a_link_before_the_first_scan_toasts_once_and_polls_nothing():
    """E40: a link present before this process first scans the home refuses every path, poll.lock included; each
    --once returns 4 and the one CRASH_UNLOGGED toast of the day is all that shows."""
    saved = set(poll._unlogged)
    poll._unlogged.clear()
    try:
        with _unsigned():
            stray = _home() / "execution" / "stray.txt"
            stray.parent.mkdir()
            stray.write_bytes(b"")
            os.link(stray, _home() / "stray-link.txt")
            isolation._LINK_SCAN.clear()                 # as if this process had not scanned the home yet
            runs = [_main(["--once"]), _main(["--once"], NOW + MINUTE)]
    finally:
        poll._unlogged.clear()
        poll._unlogged.update(saved)
    assert [code for code, _o, _e in runs] == [4, 4]
    assert EF.TOASTS == [_unlogged_toast(NOW)], EF.TOASTS
    assert sorted(p.name for p in (_home() / "execution").iterdir()) == ["stray.txt"]


# --------------------------------------------------------------------------- #
# The CLI (contract 16.1): exit codes, the lock, arguments, the loop
# --------------------------------------------------------------------------- #
def test_once_prints_one_summary_line_and_releases_the_lock():
    """--once polls once, prints the summary as one ASCII JSON line of counts and error names, returns 0 and leaves
    poll.lock free."""
    with _unsigned():
        code, out, err = _main(["--once"])
    assert (code, err) == (0, ""), (code, err)
    assert len(out.splitlines()) == 1 and out.isascii(), out
    summary = json.loads(out)
    assert summary["utc"] == UTC and summary["venues"] == dict.fromkeys(snapshot.VENUES, "error"), summary
    assert summary["errors"]["kis"] == "code not signed" and summary["errors"]["upbit"].startswith("keys missing")
    assert summary["counts"] == dict.fromkeys(snapshot.VENUES, ZERO) and summary["evidence"] == 0
    assert summary["alerts"] == 3 and len(EF.TOASTS) == 3
    assert [p.name for p in snapshot.home().glob("inquiry-*.jsonl")] == ["inquiry-20261024.jsonl"]
    with poll.held_lock() as got:
        assert got is True


def test_a_second_poller_exits_0_and_polls_nothing():
    """E1R2-1: while another handle holds poll.lock, --once and the loop try it 5 times 0.2 s apart, then print the
    message and return 0, having polled nothing: no inquiry or alert file, no send, poll_once never called. A lock
    let go between two tries (the wrapper's instant probe of the real poll.lock, Task 1) is taken."""
    locked = (0, "another E1 poller holds poll.lock; exiting\n")
    sleeps, saved_sleep, other = [], vars(poll)["_sleep"], contextlib.ExitStack()
    poll._sleep = sleeps.append
    try:
        with _unsigned(), poll.held_lock() as got:
            assert got is True and sleeps == [], sleeps
            code, out, _ = _main(["--once"])
            assert (code, out) == locked, (code, out)
            calls, saved = [], vars(poll)["poll_once"]
            poll.poll_once = calls.append
            try:
                assert _main(["--once"])[:2] == _main([])[:2] == locked
            finally:
                poll.poll_once = saved
        assert calls == [] and EF.TOASTS == [] and sleeps == [0.2] * 12, sleeps
        assert sorted(p.name for p in snapshot.home().iterdir()) == ["poll.lock"]
        assert other.enter_context(poll.held_lock()) is True
        taken = []
        poll._sleep = lambda seconds: (taken.append(seconds), other.close())
        with poll.held_lock() as got:
            assert got is True and taken == [0.2], (got, taken)
    finally:
        other.close()
        poll._sleep = saved_sleep


def test_argument_errors_return_4_and_poll_nothing():
    """Contract 16.1: a bad interval, two modes, an interval with a mode or a bad --mark-sent stamp prints argparse's
    reason and returns 4 (E23), before any path is computed or any poll runs."""
    calls, saved = [], vars(poll)["poll_once"]
    poll.poll_once = calls.append
    try:
        for argv in (["--interval-min", "0"], ["--interval-min", "61"], ["--interval-min", "x"],
                     ["--interval-min", "1.5"], ["--once", "--pending"], ["--pending", "--mark-sent", UTC],
                     ["--once", "--mark-sent", UTC], ["--once", "--interval-min", "5"],
                     ["--pending", "--interval-min", "5"], ["--mark-sent", "2026-10-24"],
                     ["--mark-sent", "2026-10-24 00:00:00"], ["--mark-sent"], ["--bogus"]):
            code, out, err = _main(argv)
            assert (code, out) == (4, "") and err, (argv, code, out, err)
    finally:
        poll.poll_once = saved
    assert calls == [] and not (_home() / "execution").exists()


def test_the_loop_survives_a_crash_sleeps_the_rest_and_stops_on_ctrl_c():
    """Spec 7 "The poller": a crashed poll is alerted (OUTAGE_CRASH) and the next one runs; after each poll the loop
    sleeps the interval minus the poll's time; Ctrl+C returns 0 and releases poll.lock."""
    polls, sleeps = [], []

    def fake_poll(now):
        polls.append(now)
        if len(polls) == 1:
            raise ValueError("the first poll fails")
        return {"utc": model.iso_utc(now)}

    def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise KeyboardInterrupt
    saved = (vars(poll)["poll_once"], vars(poll)["_sleep"])
    poll.poll_once, poll._sleep = fake_poll, fake_sleep
    try:
        code, out, _ = _main(["--interval-min", "1"], NOW, NOW + timedelta(seconds=5), NOW + MINUTE,
                             NOW + timedelta(seconds=63))
    finally:
        poll.poll_once, poll._sleep = saved
    assert code == 0 and polls == [NOW, NOW + MINUTE] and sleeps == [55.0, 57.0], (code, polls, sleeps)
    crash, summary = (json.loads(line) for line in out.splitlines())
    assert crash["crash"] == "ValueError" and crash["at"].startswith("execution_poll.py:"), crash
    assert summary == {"utc": model.iso_utc(NOW + MINUTE)} and "the first poll fails" not in out
    assert _rows() == [_crash_row(v, UTC) for v in snapshot.VENUES]
    with poll.held_lock() as got:
        assert got is True


def test_the_interval_bounds_and_the_default():
    """--interval-min 60 sleeps an hour less the poll's time, no flag sleeps 5 minutes, 1 accepts a poll longer than
    the interval (sleep 0) and a clock stepped back (sleep one interval, never more); Ctrl+C in the first sleep
    returns 0."""
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        raise KeyboardInterrupt
    saved = (vars(poll)["poll_once"], vars(poll)["_sleep"])
    poll.poll_once, poll._sleep = (lambda now: {}), fake_sleep
    try:
        for argv, took in ((["--interval-min", "60"], 2), ([], 2), (["--interval-min", "1"], 90),
                           (["--interval-min", "1"], -3600)):
            assert _main(argv, NOW, NOW + timedelta(seconds=took))[0] == 0, argv
    finally:
        poll.poll_once, poll._sleep = saved
    assert sleeps == [3598.0, 298.0, 0.0, 60.0], sleeps


# --------------------------------------------------------------------------- #
# --pending and --mark-sent (contract 16.4; E23)
# --------------------------------------------------------------------------- #
def test_pending_shows_only_verified_text_and_never_a_forged_row():
    """Every unsent row is re-verified before it is rendered: a slot holding text, an unknown text_key or a kind that
    disagrees gives the one UNVERIFIED line, none of its own text, and never counts as red; an info or clear row is
    never listed, even unsent (E43)."""
    with _unsigned():
        poll.poll_once(NOW)                              # three amber rows and the info row
    forged = [{"kind": "OUTAGE", "level": "amber", "sent": False, "slots": {"n": "FORGED-SLOT-TEXT", "when": UTC},
               "text_key": "OUTAGE", "utc": UTC, "venue": "upbit"},
              {"kind": "OUTAGE", "level": "red", "sent": False, "slots": {}, "text_key": "FORGED-TEXT-KEY",
               "utc": UTC, "venue": "kis"},
              {"kind": "FLOOR", "level": "red", "sent": False, "slots": {"n": 1}, "text_key": "FOREIGN_ORDER",
               "utc": UTC, "venue": "kis"},
              {"kind": "NOT_SET", "level": "info", "sent": False, "slots": {"skipped": "FLOOR: not set"},
               "text_key": "NOT_SET", "utc": UTC, "venue": "all"},           # verifies, but info never leaves the PC
              {"kind": "OUTAGE", "level": "clear", "sent": False, "slots": {}, "text_key": "OUTAGE", "utc": UTC,
               "venue": "okx"}]                                               # nor does a clear
    with open(poll.alerts_path(), "ab") as fh:
        fh.write(b"".join((json.dumps(row) + "\n").encode("utf-8") for row in forged))
    code, out, _ = _main(["--pending"])
    assert code == 0 and len(out.splitlines()) == 1 and out.isascii(), out
    message = json.loads(out)
    body = message["body"].split("\n")
    assert message["subject"] == "TRADEGEN E1: 6 alert(s), 0 red" and message["utcs"] == [UTC], message
    assert len(body) == 4 and body.count(poll.UNVERIFIED) == 1, body
    assert not [t for t in ("FORGED", "open order", "Checks skipped") if t in out], out
    assert sum(line.startswith("2026-10-24 09:00 KST amber: ") for line in body) == 3, body


def test_pending_and_mark_sent_in_an_empty_home_create_nothing():
    """A home with no alerts.jsonl: --pending prints {"send": false} and --mark-sent marks 0, and neither creates a
    file or a folder (no execution/)."""
    before = sorted(_home().rglob("*"))
    assert _main(["--pending"])[:2] == (0, '{"send": false}\n')
    assert _main(["--mark-sent", UTC])[:2] == (0, '{"marked": 0}\n')
    assert poll.mark_sent(UTC) == 0 and poll.pending([]) == {"send": False}
    assert sorted(_home().rglob("*")) == before and not (_home() / "execution").exists()


def test_mark_sent_marks_only_that_poll_and_keeps_every_other_byte():
    """--mark-sent UTC sets sent true on that poll's unsent rows only, leaves every other line byte for byte, prints
    the count and is idempotent; --pending and --mark-sent both work while poll.lock is held."""
    later = NOW + timedelta(days=1)
    with _unsigned():
        poll.poll_once(NOW)
        poll.poll_once(later)
    path = poll.alerts_path()
    before = path.read_bytes().splitlines(keepends=True)
    assert len(before) == 8                              # per day: three amber rows and the info row
    assert _main(["--mark-sent", UTC])[:2] == (0, '{"marked": 3}\n')
    after = path.read_bytes().splitlines(keepends=True)
    assert len(after) == 8
    for old, new in zip(before, after):
        row = json.loads(old)
        if row["utc"] == UTC and row["sent"] is False:
            assert new == (model.canonical_json({**row, "sent": True}) + "\n").encode("utf-8"), new
        else:
            assert new == old, (old, new)
    assert _main(["--mark-sent", UTC])[:2] == (0, '{"marked": 0}\n') and path.read_bytes() == b"".join(after)
    assert poll.pending(snapshot.read_all(path))["utcs"] == [model.iso_utc(later)]
    assert not list(path.parent.glob(".alerts.jsonl.*.tmp"))
    with poll.held_lock() as got:
        assert got is True
        assert _main(["--mark-sent", model.iso_utc(later)])[:2] == (0, '{"marked": 3}\n')
        assert _main(["--pending"])[:2] == (0, '{"send": false}\n')


def test_a_refused_alerts_log_makes_mark_sent_return_4_and_leaves_no_temp_file():
    """Contract 16.1 "(4 on an error)": when checked_target refuses alerts.jsonl (a second name), --mark-sent prints
    the crash line and returns 4; the log is checked before the temp file is made, so no .tmp is left behind and no
    byte changes."""
    with _unsigned():
        poll.poll_once(NOW)                              # three unsent amber rows at UTC; the home scanned clean
    path = poll.alerts_path()
    before = path.read_bytes()
    os.link(path, _home() / "other-alerts.jsonl")
    code, out, err = _main(["--mark-sent", UTC])
    crash = json.loads(out)
    assert (code, err, len(out.splitlines())) == (4, "", 1), (code, out, err)
    assert crash["crash"] == "RuntimeError" and crash["at"].startswith("isolation.py:"), crash
    assert path.read_bytes() == before and not list(path.parent.glob(".alerts.jsonl.*.tmp"))


# --------------------------------------------------------------------------- #
# KEYLESS, secrets and the clock (contract 0.2, E11, E37; E1R2-8)
# --------------------------------------------------------------------------- #
def test_keyless_signed_home_sends_nothing_and_alerts_key_missing():
    """With every key name set to '<unset>' and a .env holding fake values, a signed home (so KIS reaches its key
    read) sends nothing at all: every venue is keys_missing, not_set names the three venues, and the only rows are
    three amber KEY_MISSING and the NOT_SET info row (E1R2-8, E1R2-12)."""
    with _signed(), _keyless():
        summary = poll.poll_once(NOW)
    assert EF.STRAYS == []
    lines = snapshot.read_all(snapshot.inquiry_path(DAY))
    assert [(r["venue"], r["ok"], r["flags"]) for r in lines] == [(v, False, ["keys_missing"]) for v in
                                                                   snapshot.VENUES], lines
    items = ["KIS: keys not in .env", "Upbit: keys not in .env", "OKX: keys not in .env", *UNSET]
    assert summary["not_set"] == items, summary
    assert sorted((r["venue"], r["text_key"], r["level"], r["sent"]) for r in _rows()) == [
        ("all", "NOT_SET", "info", True), ("kis", "KEY_MISSING", "amber", False),
        ("okx", "KEY_MISSING", "amber", False), ("upbit", "KEY_MISSING", "amber", False)]
    assert [r for r in _rows() if r["kind"] == "NOT_SET"] == [_not_set_row(items, UTC)]


def test_keyless_unsigned_home_alerts_kis_unsigned_instead():
    """The same keyless poll in an unsigned home: KIS is code_unsigned (it never reads a key) and KIS_UNSIGNED takes
    the place of the KIS KEY_MISSING."""
    with _unsigned(), _keyless():
        summary = poll.poll_once(NOW)
    assert EF.STRAYS == []
    lines = snapshot.read_all(snapshot.inquiry_path(DAY))
    assert [(r["venue"], r["flags"]) for r in lines] == [("kis", ["code_unsigned"]), ("upbit", ["keys_missing"]),
                                                         ("okx", ["keys_missing"])], lines
    assert summary["not_set"][:3] == ["KIS: code not signed", "Upbit: keys not in .env", "OKX: keys not in .env"]
    assert sorted((r["venue"], r["text_key"]) for r in _rows()) == [
        ("all", "NOT_SET"), ("kis", "KIS_UNSIGNED"), ("okx", "KEY_MISSING"), ("upbit", "KEY_MISSING")]


def test_no_secret_reaches_any_output():
    """E37: polls that succeed, meet an auth error, a 500 and a malformed field on every venue, and crash leave no
    fake key, account number or token in any byte under execution/, the summaries, the toasts, stdout or the
    --pending output."""
    summaries, out = [], io.StringIO()
    with _signed(), EF.fake_keys(), contextlib.redirect_stdout(out):
        with EF.serve(_routes()):
            summaries.append(poll.poll_once(NOW))
        for i, changes in enumerate((AUTH_ERRORS, SERVER_ERRORS, FIELD_ERRORS), start=1):
            with EF.serve(_routes(**changes)):
                summaries.append(poll.poll_once(NOW + i * MINUTE))
        saved = vars(checks)["run_checks"]

        def leaky(*_args):
            raise RuntimeError(" ".join(SECRETS))
        checks.run_checks = leaky
        try:
            with EF.serve(_routes()):
                code, crashed, crash_err = _main(["--once"], NOW + 4 * MINUTE)
        finally:
            checks.run_checks = saved
        pending_code, pending_out, pending_err = _main(["--pending"])
    assert summaries[0]["venues"] == dict.fromkeys(snapshot.VENUES, "ok"), summaries[0]
    assert [s["venues"] for s in summaries[1:]] == [dict.fromkeys(snapshot.VENUES, "error")] * 3, summaries
    auth = [r for r in snapshot.read_all(snapshot.inquiry_path(DAY)) if r["utc"] == model.iso_utc(NOW + MINUTE)]
    assert [(r["venue"], r["flags"]) for r in auth] == [(v, ["auth_error"]) for v in snapshot.VENUES], auth
    assert code == 4 and json.loads(crashed.splitlines()[0])["crash"] == "RuntimeError", crashed
    assert crash_err == "" and pending_code == 0 and json.loads(pending_out)["send"] is True, crash_err
    blobs = [p.read_bytes() for p in (_home() / "execution").rglob("*") if p.is_file()]
    blobs += [json.dumps(summaries).encode("utf-8"), out.getvalue().encode("utf-8"), crashed.encode("utf-8"),
              crash_err.encode("utf-8"), pending_out.encode("utf-8"), pending_err.encode("utf-8")]
    blobs += [f"{t}\n{b}".encode("utf-8") for t, b in EF.TOASTS]
    leaks = [(s, n) for s in SECRETS for n, blob in enumerate(blobs) if s.encode("utf-8") in blob]
    assert leaks == [], leaks


def test_main_sets_the_transport_clock_and_is_the_only_clock_reader():
    """E11: main() points transport._clock at the wall clock it reads (here the scripted one) before it polls;
    --pending and --mark-sent leave transport._clock alone. The guard's clock checker finds every clock read of
    poll.py inside main() (none outside, and some inside: as any other file it would be flagged)."""
    saved = (vars(poll)["datetime"], vars(transport)["_clock"])
    _Clock.times = [NOW + timedelta(seconds=7)]
    poll.datetime = _Clock
    try:
        with _unsigned(), contextlib.redirect_stdout(io.StringIO()):
            assert poll.main(["--pending"]) == 0 and poll.main(["--mark-sent", UTC]) == 0
            assert transport._clock is saved[1]
            assert poll.main(["--once"]) == 0
            assert transport._clock is not saved[1] and transport._clock() == NOW + timedelta(seconds=7)
    finally:
        poll.datetime, transport._clock = saved
    source = (EG.EXECUTION / "poll.py").read_text(encoding="utf-8")
    assert EG._clock_hits(EG.CLOCK_MAIN, source) == [], EG._clock_hits(EG.CLOCK_MAIN, source)
    assert EG._clock_hits(EG.X, source), "poll.main() reads no clock"
