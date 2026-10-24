"""The --check CLI and the owner alerts (compliance plan Task 14; spec 5.4, 8 "compliance" items 2 and 10; P26).

Every test runs in a fresh temp TRADEGEN_HOME (tests.compliance_acceptance). A signed home is built from the test
key: its public key at a temp path swapped into owner.PUBKEY_PATH, the shipped drafts approved and stored, and the
current code hash signed. Every alerts.main call patches `_toast` and makes `subprocess.run` refuse, so PowerShell
never runs."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import runpy
import subprocess
import sys
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from core.compliance import alerts, owner, rules
from tests import compliance_fixtures as fx
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
OLD_UTC = "2026-01-01T00:00:00Z"            # every fixture entry predates every --today used here but one
UNIQUE = "Unique free text 7f3a9c: violet harbour lantern"
FP = "SHA256:" + "f" * 64
NO_CALENDAR = "calendar: no signed approval, so KRX and US plans are refused (crypto plans only)"


def _need_crypto() -> None:
    if importlib.util.find_spec("cryptography") is None:
        raise NotRun("PENDING: cryptography not installed (Task 10)")


@contextlib.contextmanager
def _patched(obj, name, value):
    saved = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield value
    finally:
        setattr(obj, name, saved)


def _home() -> Path:
    return Path(os.environ["TRADEGEN_HOME"])


def _write_home(*, rules_raw: bytes | None = None, instruments_raw: bytes | None = None,
                venues_raw: bytes | None = None, calendar_raw: bytes | None = None,
                sign_code: bool = True) -> list[bytes]:
    """Owner log in the temp home: approvals of the rules, instruments and venues (the shipped drafts unless given)
    and of `calendar_raw` when given, then code_approved for the current code hash. An anchor file is written only
    after its approved line is in owner.jsonl (Task 13's order), so the log is written first and store_blob then
    stores each blob with its anchor. The test key's PEM goes to owner.PUBKEY_PATH, which _signed_home has swapped
    to a file in the temp home."""
    assert owner.PUBKEY_PATH.resolve().is_relative_to(_home().resolve()), owner.PUBKEY_PATH   # never the repo key
    _need_crypto()
    key = fx.test_key()
    fx.write_pubkey(owner.PUBKEY_PATH, key)
    given = {"rules": rules_raw, "instruments": instruments_raw, "venues": venues_raw}
    raws = {kind: raw if raw is not None else fx.shipped_bytes(kind) for kind, raw in given.items()}
    if calendar_raw is not None:
        raws["calendar"] = calendar_raw
    entries = [("approved", {"kind": k, "sha256": rules.file_sha256(raw)}) for k, raw in raws.items()]
    if sign_code:
        entries.append(("code_approved", {"sha256": owner.code_hash(ROOT),
                                          "files": [list(f) for f in owner.code_files(ROOT)]}))
    lines, prev = [], owner.GENESIS_PREV
    for seq, (kind, data) in enumerate(entries, start=1):
        lines.append(fx.signed_entry(key, seq, prev, kind, data, utc=OLD_UTC))
        prev = json.loads(lines[-1])["row_sha256"]
    path = owner.log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(lines))
    for seq, (kind, data) in enumerate(entries, start=1):
        if kind == "approved":
            fx.store_blob(_home(), data["kind"], raws[data["kind"]], (seq, json.loads(lines[seq - 1])["row_sha256"]))
    return lines


@contextlib.contextmanager
def _signed_home(**kw):
    with _patched(owner, "PUBKEY_PATH", _home() / "test_pubkey.pem"):
        yield _write_home(**kw)


def _dates() -> tuple[date, date]:
    """(earliest review_by / auto_off / effective_until, latest review_by) of the shipped rules."""
    rows = rules.parse_rules(fx.shipped_bytes("rules")).rows
    first = min(d for r in rows for d in (r.review_by, r.auto_off, r.effective_until) if d is not None)
    return first, max(r.review_by for r in rows)


class _NoAliases(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def _dump(doc: dict) -> bytes:
    """YAML bytes the strict loader accepts: no anchors, quoted date strings, one line per long string."""
    return yaml.dump(doc, Dumper=_NoAliases, sort_keys=False, allow_unicode=True, width=1000).encode("utf-8")


def _shipped_doc(kind: str) -> dict:
    return yaml.safe_load(fx.shipped_bytes(kind).decode("utf-8"))


def _summary(out: dict) -> dict:
    return {k: out[k] for k in rules._SUMMARY_KEYS}


def _run_main(fn, argv) -> tuple[int, list[str], dict]:
    """(exit code, stdout lines, the parsed final line) of fn(argv), stdout and stderr captured."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = fn(argv)
    lines = out.getvalue().splitlines()
    assert lines and lines[-1].isascii(), lines
    return code, lines, json.loads(lines[-1])


def _check_main(argv) -> tuple[int, list[str], dict]:
    code, lines, last = _run_main(rules.main, argv)
    assert tuple(last) == rules._SUMMARY_KEYS, last              # exactly the summary keys, in order
    assert last["code"] == code, (last, code)                    # the JSON line matches the exit code
    return code, lines, last


def _boom(*_a, **_k):
    raise AssertionError("must not be called here")


def _run_module(name: str, argv: list[str]) -> tuple[int, list[str]]:
    """(exit code, stdout lines) of `python -m <name> <argv>` run in this process with runpy: the file executes as
    `__main__`, a second copy beside the module that owner.py and this test import. sys.argv, `__main__` and the
    module's own entry in sys.modules are restored afterwards."""
    keys = ("__main__", name)
    saved_argv, saved = sys.argv, {k: sys.modules.get(k) for k in keys}
    out, code = io.StringIO(), None
    sys.argv = [name, *argv]
    try:
        with contextlib.redirect_stdout(out), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)          # runpy: the module is already in sys.modules
            try:
                runpy.run_module(name, run_name="__main__", alter_sys=True)
            except SystemExit as exc:
                code = exc.code
    finally:
        sys.argv = saved_argv
        for key, module in saved.items():
            if module is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = module
    assert code is not None, "the module did not exit"
    return code, out.getvalue().splitlines()


def _sample(**over) -> dict:
    """A well-formed summary: by default nothing due and the head of an empty owner log, (0, "")."""
    base = {"code": 0, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": FP}
    return {**base, **over}


def _due_item(row="KR-OKX-SPOT", field="review_by", day=date(2026, 11, 22), today=date(2026, 11, 8)) -> dict:
    return {"row": row, "field": field, "date": day.isoformat(), "days_left": (day - today).days}


def _ok_row(summary: dict, result: str = "ok", utc: str = "2026-11-01T00:00:00Z") -> dict:
    return {"utc": utc, "channel": "email", "result": result, **summary}


def _alerts_lines() -> list[dict]:
    path = owner.alerts_path()
    return [json.loads(x) for x in path.read_bytes().splitlines()] if path.is_file() else []


def _refused(fn, *args) -> None:
    try:
        fn(*args)
    except ValueError:
        return
    raise AssertionError(f"accepted {args!r}")


# --------------------------------------------------------------------------- #
# rules.check / rules.main
# --------------------------------------------------------------------------- #
def test_check_code_0_and_alert_rows_are_accepted():
    first, _ = _dates()
    today = first - timedelta(days=15)
    with _signed_home() as lines:
        out = rules.check(today)
        assert out["code"] == 0, out["lines"]
        assert out["due"] == [] and out["overdue"] == [], out
        assert (out["head_seq"], out["head_sha256"]) == (4, json.loads(lines[-1])["row_sha256"]), out
        assert out["fingerprint"] == owner.fingerprint(owner.read_pubkey(owner.PUBKEY_PATH)), out
        for kind in ("rules", "instruments", "venues"):
            sha = rules.file_sha256(fx.shipped_bytes(kind))
            assert f"{kind}: the draft is the version in force ({sha[:16]})" in out["lines"], out["lines"]
        assert NO_CALENDAR in out["lines"], out["lines"]
        alerts.log("email", "ok", _summary(out), datetime(2026, 1, 2, tzinfo=timezone.utc))   # anchor + fingerprint
        again = rules.check(today)
        assert again["code"] == 0, again["lines"]                # the row's anchor and fingerprint verify
        code, printed, last = _check_main(["--check", "--today", today.isoformat()])
        assert code == 0 and last == _summary(again), (code, last)
        assert printed[:-1] == again["lines"], printed


def test_check_code_1_due_within_14_days():
    first, _ = _dates()
    today = first - timedelta(days=5)
    with _signed_home():
        out = rules.check(today)
    assert out["code"] == 1, out["lines"]
    assert out["overdue"] == [], out
    assert out["due"] and all(i["days_left"] <= 14 for i in out["due"]), out["due"]
    assert {"field", "date", "days_left", "row"} == set(out["due"][0]), out["due"]
    assert any(i["date"] == first.isoformat() and i["days_left"] == 5 for i in out["due"]), out["due"]
    assert out["due"] == sorted(out["due"], key=lambda i: (i["date"], i["row"], i["field"]))
    assert any(line.startswith("due: ") for line in out["lines"]), out["lines"]


def test_check_review_day_is_due_not_overdue():
    first, _ = _dates()
    assert first == min(r.review_by for r in rules.parse_rules(fx.shipped_bytes("rules")).rows), first
    with _signed_home():
        on_day = rules.check(first)
        window = rules.check(first - timedelta(days=14))
    assert on_day["code"] == 1 and on_day["overdue"] == [], on_day["lines"]      # stale only after the day (gate)
    assert any(i["field"] == "review_by" and i["date"] == first.isoformat() and i["days_left"] == 0
               for i in on_day["due"]), on_day["due"]
    assert window["code"] == 1 and any(i["days_left"] == 14 for i in window["due"]), window["lines"]   # 14 is due


def test_check_code_2_overdue():
    _, last_review = _dates()
    today = last_review + timedelta(days=1)
    with _signed_home():
        out = rules.check(today)
    assert out["code"] == 2, out["lines"]
    ids = {r.id for r in rules.parse_rules(fx.shipped_bytes("rules")).rows}
    assert {i["row"] for i in out["overdue"]} == ids, out["overdue"]          # every row's review date passed
    assert all(i["field"] == "review_by" and i["days_late"] >= 1 for i in out["overdue"]), out["overdue"]
    assert any(line.startswith("overdue: ") for line in out["lines"]), out["lines"]


def test_check_auto_off_and_effective_until_are_overdue_from_their_day():
    rows = rules.parse_rules(fx.shipped_bytes("rules")).rows
    with _signed_home():
        for name in ("auto_off", "effective_until"):
            row = min((r for r in rows if getattr(r, name) is not None), key=lambda r: (getattr(r, name), r.id))
            day = getattr(row, name)
            before, on_day, after = (rules.check(day + timedelta(days=d)) for d in (-1, 0, 1))
            item = {"row": row.id, "field": name, "date": day.isoformat()}
            assert {**item, "days_left": 1} in before["due"], (name, before["due"])
            assert {**item, "days_late": 0} in on_day["overdue"] and on_day["code"] == 2, (name, on_day["overdue"])
            assert not any(i["row"] == row.id and i["field"] == name for i in on_day["due"]), on_day["due"]
            assert f"overdue: {row.id} {name} {day.isoformat()} (0 days late)" in on_day["lines"], on_day["lines"]
            assert {**item, "days_late": 1} in after["overdue"], (name, after["overdue"])


def test_check_code_3_no_owner_key_reads_only():
    _need_crypto()
    home = _home()
    with _patched(owner, "PUBKEY_PATH", home / "absent_pubkey.pem"):
        out = rules.check(date(2026, 10, 23))
        code, _, last = _check_main(["--check", "--today", "2026-10-23"])
    assert out["code"] == 3 and code == 3, out["lines"]
    assert any("no owner key yet" in line for line in out["lines"]), out["lines"]           # P24
    assert "code: signature not checked (owner log not usable)" in out["lines"], out["lines"]
    assert not any(line.startswith("code: UNSIGNED") for line in out["lines"]), out["lines"]
    assert last["head_seq"] == 0 and last["fingerprint"] == "", last
    assert sorted(p.name for p in home.iterdir()) == [], list(home.iterdir())               # --check wrote nothing
    # no owner log and no snapshot: the gate sends every exit to the app, so exit 3 never says they stay open
    assert out["lines"][-1].startswith("exit 3: ") and "exits stay open" not in out["lines"][-1], out["lines"]
    assert "close or withdraw manually in the app" in out["lines"][-1], out["lines"]


def test_check_code_3_unsigned_code():
    first, _ = _dates()
    with _signed_home(sign_code=False):
        out = rules.check(first - timedelta(days=15))
    assert out["code"] == 3, out["lines"]
    assert any(line.startswith("code: UNSIGNED") for line in out["lines"]), out["lines"]


def test_check_code_3_broken_log():
    first, _ = _dates()
    with _signed_home() as lines:
        edited = lines[-1].replace(b'"code_approved"', b'"code_approved" ')                # no longer canonical
        owner.log_path().write_bytes(b"".join(lines[:-1]) + edited)
        out = rules.check(first - timedelta(days=15))
    assert out["code"] == 3, out["lines"]
    assert any(line.startswith("owner log: BROKEN") for line in out["lines"]), out["lines"]
    assert "calendar: not checked (owner log not usable)" in out["lines"], out["lines"]


def test_check_code_3_key_changed():
    first, _ = _dates()
    today = first - timedelta(days=15)
    with _signed_home():
        out = rules.check(today)
        assert out["code"] == 0, out["lines"]
        alerts.log("email", "ok", {**_summary(out), "fingerprint": "SHA256:" + "0" * 64},
                   datetime(2026, 1, 2, tzinfo=timezone.utc))            # the first fingerprint ever recorded
        changed = rules.check(today)
        code, _, last = _check_main(["--check", "--today", today.isoformat()])
        owed = alerts.due(_summary(changed), _alerts_lines(), today)
    assert changed["code"] == 3 and code == 3, changed["lines"]
    assert any("KEY CHANGED" in line for line in changed["lines"]), changed["lines"]
    assert owed == [{"kind": "key_changed", "since": "2026-01-02"}, {"kind": "state"}], owed     # due() agrees


def test_check_draft_diff_lists_changed_entries_and_sources():
    first, _ = _dates()
    doc = _shipped_doc("rules")
    ids = [doc["rows"][0]["id"], doc["rows"][1]["id"]]
    extra = "https://example.org/only-in-the-signed-version"
    doc["rows"][0]["reason"] = UNIQUE
    doc["rows"][1]["reason"] = UNIQUE + " (second)"
    doc["rows"][1]["sources"] = [*doc["rows"][1]["sources"], extra]
    inst = _shipped_doc("instruments")
    inst["crypto"]["BTC"]["source"] = "https://example.org/signed-btc-source"
    del inst["crypto"]["USDT"]                  # the venues draft lists USDT-KRW, so it is read with the map draft
    ven = _shipped_doc("venues")
    ven["venues"]["okx"]["markets"] = [["BTC", "USDT"]]
    ven["venues"]["upbit"]["markets"] = [["BTC", "KRW"]]
    signed = {"rules_raw": _dump(doc), "instruments_raw": _dump(inst), "venues_raw": _dump(ven)}
    assert any(r.reason == UNIQUE for r in rules.parse_rules(signed["rules_raw"]).rows)   # the edits load as intended
    with _signed_home(**signed):
        out = rules.check(first - timedelta(days=15))
    assert out["code"] == 0, out["lines"]
    for kind in ("rules", "instruments", "venues"):
        assert any(line.startswith(f"{kind}: the draft ") and "is not the version in force" in line
                   for line in out["lines"]), (kind, out["lines"])
    expected = []
    for rid in sorted(ids):
        expected += ([f"  rules row {rid}: reason, sources changed", f"  rules row {rid}: sources removed {extra!r}"]
                     if rid == ids[1] else [f"  rules row {rid}: reason changed"])
    assert [line for line in out["lines"] if line.startswith("  rules row ")] == expected, out["lines"]
    assert [line for line in out["lines"] if line.startswith(("  instrument ", "  venue "))] == [
        "  instrument crypto/BTC: source changed", "  instrument crypto/USDT: added",
        "  venue okx: markets changed", "  venue upbit: markets changed"], out["lines"]
    assert not any(UNIQUE in line for line in out["lines"]), out["lines"]       # ids, field names and sources only


def test_check_calendar_signed_cut_off_and_store():
    first, _ = _dates()
    today = first - timedelta(days=15)
    cal = ROOT / "core" / "calendars" / "data"
    stream = rules.calendar_stream(cal)                     # Task 13's one framing (owner._calendar_stream is gone)
    sha = rules.file_sha256(stream)
    assert sha == rules.calendar_sha256(cal), "the stored stream is what calendar_sha256 hashes (Task 13)"
    with _signed_home(calendar_raw=stream):
        signed = rules.check(today)
        early = rules.check(date(2025, 12, 31))                        # before every entry's utc stamp
        stored = next((owner.store_dir() / "calendar" / sha).iterdir())
        stored.write_bytes(stored.read_bytes() + b"# altered\n")
        altered = rules.check(today)
    assert f"calendar: the draft is the version in force ({sha[:16]})" in signed["lines"], signed["lines"]
    assert NO_CALENDAR in early["lines"], early["lines"]               # the same utc cut-off as load_context
    assert f"calendar: the signed version {sha[:16]} is missing or altered in the store" in altered["lines"]
    assert altered["code"] == 0, altered["lines"]                       # the calendar stays out of the exit code


def test_check_calendar_draft_differs():
    first, _ = _dates()
    other = b"holidays_KRX.yaml\0x: 1\n\0"                            # a one-file calendar set, not the draft
    draft = rules.calendar_sha256(ROOT / "core" / "calendars" / "data")
    with _signed_home(calendar_raw=other):
        out = rules.check(first - timedelta(days=15))
    line = (f"calendar: the draft {draft[:16]} is not the version in force ({rules.file_sha256(other)[:16]}); "
            "it counts only once signed")
    assert line in out["lines"], out["lines"]


def test_check_main_exit_4_on_injected_exception():
    _need_crypto()

    def boom(*_a, **_k):
        raise RuntimeError("injected")

    with _patched(owner, "load_context", boom):
        code, lines, last = _check_main(["--check", "--today", "2026-10-23"])
    assert code == 4, lines
    assert last == {"code": 4, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": ""}, last
    assert any("RuntimeError: injected" in line for line in lines), lines


def test_check_main_exit_4_on_bad_today_unknown_flag_or_no_check():
    for argv in (["--check", "--today", "2026-13-01"], ["--check", "--today", "20261023"],
                 ["--check", "--bogus"], [], ["--today", "2026-10-23"]):
        code, lines, _ = _check_main(argv)
        assert code == 4, (argv, lines)
        assert lines[0].startswith("check failed: "), (argv, lines)


def test_check_main_exit_4_on_help():
    try:
        code, lines, last = _check_main(["--check", "--help"])     # argparse prints usage, then raises SystemExit
    except SystemExit as exc:
        raise AssertionError(f"rules.main let SystemExit({exc.code}) escape") from None
    assert code == 4 and last["code"] == 4, lines


def test_check_main_exit_4_on_missing_cryptography():
    """A subprocess where `import cryptography` fails (spec 8 item 2): exit 4, not 3, and the JSON line says 4."""
    prog = (f"import sys; sys.path.insert(0, {str(ROOT)!r}); sys.modules['cryptography'] = None; "
            "from core.compliance import rules; raise SystemExit(rules.main(['--check', '--today', '2026-10-23']))")
    env = {**os.environ, "TRADEGEN_HOME": str(_home())}
    done = subprocess.run([sys.executable, "-I", "-B", "-c", prog], cwd=str(ROOT), env=env, capture_output=True,
                          timeout=180)
    out = done.stdout.decode("utf-8", errors="replace").splitlines()
    assert done.returncode == 4, (done.returncode, out, done.stderr[-2000:])
    assert json.loads(out[-1])["code"] == 4, out
    assert any("ImportError" in line or "ModuleNotFoundError" in line for line in out), out
    assert list(_home().iterdir()) == [], list(_home().iterdir())


def test_check_runs_as_main_module_with_a_differing_draft():
    """`python -m core.compliance.rules --check` runs the file as `__main__`, a second copy beside the module that
    owner.py imports, so the classes of the copy are not the ones in the approved state. A draft that differed from
    the signed table once made that run exit 4 (AttributeError in the diff). It must give the imported main's result."""
    first, _ = _dates()
    today = first - timedelta(days=15)
    doc = _shipped_doc("rules")
    rid = doc["rows"][0]["id"]
    doc["rows"][0]["reason"] = UNIQUE
    with _signed_home(rules_raw=_dump(doc)):
        code, lines = _run_module("core.compliance.rules", ["--check", "--today", today.isoformat()])
        want = rules.check(today)
    last = json.loads(lines[-1])
    assert tuple(last) == rules._SUMMARY_KEYS and last["code"] == code, (code, lines)
    assert code in (0, 1), lines                                       # not 4
    assert f"  rules row {rid}: reason changed" in lines, lines
    assert lines[:-1] == want["lines"] and last == _summary(want), lines


# --------------------------------------------------------------------------- #
# alerts.due / render / log / _toast / main
# --------------------------------------------------------------------------- #
def test_due_daily_on_overdue_and_on_codes_3_and_4():
    today = date(2026, 11, 24)
    item = {"row": "KR-OKX-SPOT", "field": "review_by", "date": "2026-11-22", "days_late": 2}
    summary = _sample(code=2, overdue=[item])
    yesterday = [_ok_row({**summary, "overdue": [{**item, "days_late": 1}]})]
    assert alerts.due(summary, yesterday, today) == [{"kind": "overdue", **item}]               # again, every day
    assert [a["kind"] for a in alerts.due(_sample(code=3), yesterday, today)] == ["state"]
    failed = _sample(code=4, fingerprint="")
    assert [a["kind"] for a in alerts.due(failed, [], today)] == ["failed"]
    assert alerts.due(_sample(), [], today) == []                                               # nothing owed


def test_due_thresholds_once_each():
    day = date(2026, 11, 22)
    at14 = _sample(code=1, due=[_due_item(today=day - timedelta(days=14))])
    first = alerts.due(at14, [], day - timedelta(days=14))
    assert first == [{"kind": "due", **at14["due"][0], "threshold": 14}], first
    history = [_ok_row(at14)]
    at13 = _sample(code=1, due=[_due_item(today=day - timedelta(days=13))])
    assert alerts.due(at13, history, day - timedelta(days=13)) == []                            # 14-day alert sent once
    at3 = _sample(code=1, due=[_due_item(today=day - timedelta(days=3))])
    assert [a["threshold"] for a in alerts.due(at3, history, day - timedelta(days=3))] == [3]
    history.append(_ok_row(at3))
    at2 = _sample(code=1, due=[_due_item(today=day - timedelta(days=2))])
    assert alerts.due(at2, history, day - timedelta(days=2)) == []                              # 3-day alert sent once
    failed = [_ok_row(at14, result="fail")]
    assert [a["threshold"] for a in alerts.due(at13, failed, day - timedelta(days=13))] == [14]  # a failed send repeats


def test_due_toast_alone_is_not_delivery():
    """The toast shows on the PC only. A threshold counts as sent when a push or email row is ok (the daily task logs
    those after it sends), so a toast ok beside an email fail is owed again the next day."""
    day = date(2026, 11, 22)
    at14 = _sample(code=1, due=[_due_item(today=day - timedelta(days=14))])
    at13 = _sample(code=1, due=[_due_item(today=day - timedelta(days=13))])
    toast = {**_ok_row(at14), "channel": "toast"}
    next_day = day - timedelta(days=13)
    assert [a["threshold"] for a in alerts.due(at13, [toast], next_day)] == [14]
    assert [a["threshold"] for a in alerts.due(at13, [toast, _ok_row(at14, result="fail")], next_day)] == [14]
    assert [a["threshold"] for a in alerts.due(at13, [{**toast, "channel": "sms"}], next_day)] == [14]
    assert alerts.due(at13, [toast, {**_ok_row(at14), "channel": "push"}], next_day) == []
    assert alerts.due(at13, [toast, _ok_row(at14)], next_day) == []


def test_due_missed_run_still_alerts():
    day = date(2026, 11, 22)
    at12 = _sample(code=1, due=[_due_item(today=day - timedelta(days=12))])
    assert [a["threshold"] for a in alerts.due(at12, [], day - timedelta(days=12))] == [14]   # 14-day run missed
    history = [_ok_row(_sample(code=1, due=[_due_item(today=day - timedelta(days=10))]))]
    at2 = _sample(code=1, due=[_due_item(today=day - timedelta(days=2))])
    assert [a["threshold"] for a in alerts.due(at2, history, day - timedelta(days=2))] == [3]   # 3-day run missed


def test_due_missing_or_malformed_summary_alerts():
    today = date(2026, 11, 8)
    assert alerts.due(None, [], today) == [{"kind": "summary_missing"}]
    for bad in ({}, _sample(code="0"), _sample(code=5), _sample(extra=1), _sample(due=[{"row": "X"}]),
                _sample(head_sha256="xyz"), {k: v for k, v in _sample().items() if k != "head_sha256"},
                _sample(head_seq=5), _sample(head_sha256="a" * 64),          # seq 0 if and only if sha "" (Task 11)
                _sample(fingerprint="x"),                                      # "" or SHA256:<64 hex>
                _sample(code=2), _sample(code=1), _sample(code=0, due=[_due_item()])):   # code against its lists
        assert alerts.due(bad, [], today) == [{"kind": "summary_missing"}], bad


def test_due_key_changed():
    """KEY CHANGED rides on exit 3 only: Task 12's owner_state walks signed key_rotated entries back (P20), so a
    rotation-consistent log is exit 0 and owes no key alert."""
    today = date(2026, 11, 8)
    one, two = "SHA256:" + "1" * 64, "SHA256:" + "2" * 64
    history = [_ok_row(_sample(fingerprint=""), utc="2026-10-20T00:00:00Z"),       # rows before the key carry none
               _ok_row(_sample(fingerprint=one), utc="2026-10-23T09:00:00Z"),      # the first one recorded (P20)
               _ok_row(_sample(fingerprint=two), utc="2026-10-30T09:00:00Z")]      # a later one sets no standard
    found = alerts.due(_sample(code=3), history, today)
    assert found == [{"kind": "key_changed", "since": "2026-10-23"}, {"kind": "state"}], found
    assert alerts.due(_sample(code=3, fingerprint=two), history, today) == found, "held to the FIRST fingerprint"
    assert alerts.due(_sample(code=0, fingerprint=two), history, today) == [], "a signed rotation keeps exit 0"
    assert alerts.due(_sample(code=3, fingerprint=one), history, today) == [{"kind": "state"}]
    assert alerts.due(_sample(code=3, fingerprint=""), history, today) == [{"kind": "state"}]   # no key, no claim
    subject, body = alerts.render(found[0], _sample(code=3))
    assert "KEY CHANGED" in subject and "KEY CHANGED since 2026-10-23" in body, (subject, body)
    assert "not the one first recorded on 2026-10-23" in body, body


def test_render_fixed_template_and_sanitises():
    summary = _sample(head_seq=12, head_sha256="a" * 64)
    alert = {"kind": "due", "row": "KR-OKX-SPOT", "field": "auto_off", "date": "2026-12-03", "days_left": 3,
             "threshold": 3}
    first = "SHA256:" + "1" * 64
    history = [_ok_row(_sample(fingerprint=""), utc="2026-10-20T00:00:00Z"),          # rows before the key carry none
               _ok_row(_sample(fingerprint=first), utc="2026-10-23T09:00:00Z"),       # the first one recorded
               _ok_row(_sample(), utc="2026-10-30T09:00:00Z")]
    subject, body = alerts.render(alert, summary, history)
    assert subject == "TRADEGEN compliance: KR-OKX-SPOT auto_off in 3 days", subject
    assert body.splitlines()[0] == "Rule KR-OKX-SPOT: auto_off 2026-12-03, 3 days left.", body
    assert "Owner log head: entry #12" in body, body
    assert f"Key now {FP}; first recorded {first} on 2026-10-23" in body, body           # spec 6.4: both, always
    assert f"Key now {FP}; first recorded none yet" in alerts.render(alert, summary)[1]
    junk = [{"fingerprint": "SHA256:" + "\n" * 64, "utc": "later"}, _ok_row(_sample())]    # never interpolated
    assert "first recorded unknown on (unrecognised date)" in alerts.render(alert, summary, junk)[1]
    assert f"Sent only to {alerts.OWNER_ALERT_EMAIL}." in body, body
    _, state = alerts.render({"kind": "state"}, summary, history)
    assert "exits stay open" not in state and "close or withdraw manually in the app" in state, state
    late = {"kind": "overdue", "row": "KR-OKX-SPOT", "field": "auto_off", "date": "2026-12-03", "days_late": 0}
    subject, body = alerts.render(late, summary)
    assert subject == "TRADEGEN compliance: KR-OKX-SPOT auto_off reached", subject
    assert body.splitlines()[0] == ("Rule KR-OKX-SPOT: auto_off 2026-12-03 is reached (0 days ago). New exposure "
                                    "under it is blocked; exits stay open."), body
    hostile = {"kind": "due", "row": "X\nrm -rf / && echo", "field": "reason", "date": "soon", "days_left": "3"}
    subject, body = alerts.render(hostile, _sample(fingerprint="not a fingerprint"))
    text = subject + body
    assert "rm -rf" not in text and "soon" not in text and "reason" not in text, text
    assert "(unrecognised id)" in text and "(unrecognised date)" in text and "Key now unknown" in text
    odd = {"kind": "overdue", "row": "KR-X", "field": ["review_by"], "date": "2026-11-22", "days_late": 1}
    assert "(unrecognised field)" in "".join(alerts.render(odd, summary))          # an unhashable field is no crash


def test_render_has_no_rule_free_text():
    summary = _sample(code=1, due=[_due_item()])
    for hostile in ({"kind": "due", "row": UNIQUE, "field": "review_by", "date": "2026-11-22", "days_left": 3},
                    {"kind": "overdue", "row": UNIQUE, "field": "review_by", "date": "2026-11-22", "days_late": 1},
                    {"kind": "key_changed", "since": UNIQUE}):
        subject, body = alerts.render(hostile, summary)
        assert UNIQUE[:20] not in subject + body, (hostile, subject, body)
    first, _ = _dates()
    today = first - timedelta(days=5)
    doc = _shipped_doc("rules")
    for row in doc["rows"]:
        row["reason"] = UNIQUE
        if row.get("warning"):
            row["warning"] = UNIQUE + " {cap}"
    raw = _dump(doc)
    assert all(r.reason == UNIQUE for r in rules.parse_rules(raw).rows)
    with _signed_home(rules_raw=raw):
        out = rules.check(today)
        assert out["code"] == 1 and out["due"], out["lines"]
        with _patched(alerts, "_toast", lambda title, body: True), _patched(subprocess, "run", _boom):
            code, _, shown = _run_main(alerts.main, ["--today", today.isoformat(),
                                                     "--summary", json.dumps(_summary(out))])
    assert code == 0 and shown["send"] is True, shown
    assert UNIQUE[:20] not in shown["subject"] + shown["body"], shown                   # never rule free text
    assert all(i["row"] in shown["body"] for i in out["due"]), shown["body"]
    assert not any(UNIQUE[:20] in line for line in out["lines"]), out["lines"]


def test_log_rows_carry_anchor_and_fingerprint():
    now = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)
    owner.append_system_entry("system_halt", {"floor_krw": 0}, now)
    seq, sha = owner.append_system_entry("system_halt", {"floor_krw": 0}, now)          # the owner log head
    summary = _sample(code=1, due=[_due_item()], head_seq=seq, head_sha256=sha)
    real_lock, held = owner._exclusive, []

    @contextlib.contextmanager
    def lock(path):
        with real_lock(path):
            before = len(_alerts_lines())
            yield
            held.append((path, before, len(_alerts_lines())))

    with _patched(owner, "_exclusive", lock):
        alerts.log("push", "ok", summary, now)
        alerts.log("email", "fail", summary, now)
        _refused(alerts.log, "push", "ok", {**summary, "head_sha256": "b" * 64}, now)   # not line 2's row_sha256
        _refused(alerts.log, "push", "ok", {**summary, "head_seq": seq + 1}, now)       # beyond the log
    assert held == [(owner.log_path(), 0, 1), (owner.log_path(), 1, 2)], held   # each append under the sidecar lock
    path = owner.alerts_path()
    assert path.parent == _home() / "compliance", path
    raw = path.read_bytes().splitlines(keepends=True)
    assert len(raw) == 2, raw
    for line, (channel, result) in zip(raw, (("push", "ok"), ("email", "fail"))):
        row = json.loads(line)
        assert line == _canonical_line(row), line                                           # canonical JSON + "\n"
        assert set(row) == {"utc", "channel", "result", *rules._SUMMARY_KEYS}, row
        assert (row["channel"], row["result"], row["utc"]) == (channel, result, "2026-10-23T00:00:00Z"), row
        assert (row["head_seq"], row["head_sha256"], row["fingerprint"]) == (seq, sha, FP), row
        assert row["due"] == summary["due"], row
    assert owner.read_anchors() == [(seq, sha)], owner.read_anchors()                       # Task 11 reads them


def _canonical_line(row: dict) -> bytes:
    from core.compliance import model
    return model.canonical_json(row).encode("utf-8") + b"\n"


def test_log_refuses_bad_input_and_writes_nothing():
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
    for args in (("sms", "ok", _sample(), now), ("push", "maybe", _sample(), now),
                 ("push", "ok", _sample(code=9), now), ("push", "ok", _sample(), datetime(2026, 10, 23)),
                 ("push", "ok", _sample(head_seq=5), now), ("push", "ok", _sample(head_sha256="a" * 64), now),
                 ("push", "ok", _sample(fingerprint="x"), now),
                 ("push", "ok", _sample(head_seq=1, head_sha256="a" * 64), now)):      # there is no owner log
        _refused(alerts.log, *args)
    assert not owner.alerts_path().exists()


def test_toast_seam_passes_text_by_env_only():
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["env"] = cmd, kw["env"]
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    with _patched(subprocess, "run", fake_run):
        assert alerts._toast("TITLE-9z", "BODY-8y") is True
    assert seen["cmd"][:4] == ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"], seen["cmd"]
    assert "TITLE-9z" not in seen["cmd"][-1] and "BODY-8y" not in seen["cmd"][-1], seen["cmd"]
    assert (seen["env"]["TRADEGEN_TOAST_TITLE"], seen["env"]["TRADEGEN_TOAST_BODY"]) == ("TITLE-9z", "BODY-8y")

    def fails(cmd, **kw):
        raise OSError("no powershell")

    with _patched(subprocess, "run", fails):
        assert alerts._toast("t", "b") is False
    with _patched(subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, b"", b"")):
        assert alerts._toast("t", "b") is False


def test_alerts_main_send_toasts_once_and_logs():
    calls = []

    def toast(title, body):
        calls.append((title, body))
        return True

    summary = _sample(code=1, due=[_due_item(today=date(2026, 11, 8))])
    with _patched(alerts, "_toast", toast), _patched(subprocess, "run", _boom):
        code, _, shown = _run_main(alerts.main, ["--today", "2026-11-08", "--summary", json.dumps(summary)])
    assert code == 0 and shown["send"] is True and set(shown) == {"send", "subject", "body"}, shown
    assert calls == [(shown["subject"], shown["body"])], calls                            # once, same text
    assert f"Key now {FP}; first recorded none yet" in shown["body"], shown["body"]      # nothing recorded before
    rows = _alerts_lines()
    assert [(r["channel"], r["result"]) for r in rows] == [("toast", "ok")], rows
    assert rows[0]["due"] == summary["due"], rows
    with _patched(alerts, "_toast", lambda title, body: False), _patched(subprocess, "run", _boom):
        code, _, shown = _run_main(alerts.main, ["--today", "2026-11-08", "--summary", json.dumps(_sample(code=3))])
    assert code == 0 and "The Windows toast could not be shown." in shown["body"], shown   # told on the others
    assert f"Key now {FP}; first recorded {FP} on {rows[0]['utc'][:10]}" in shown["body"], shown["body"]
    assert [(r["channel"], r["result"]) for r in _alerts_lines()][-1] == ("toast", "fail")


def test_alerts_main_still_prints_the_alert_when_logging_fails():
    calls = []
    owner.alerts_path().mkdir(parents=True)                       # alerts.jsonl cannot be opened as a file
    with _patched(alerts, "_toast", lambda title, body: calls.append(title) or True), \
            _patched(subprocess, "run", _boom):
        code, _, shown = _run_main(alerts.main, ["--today", "2026-10-23", "--summary", json.dumps(_sample(code=3))])
    assert code == 1 and shown["send"] is True and calls == [shown["subject"]], (code, shown, calls)
    assert shown["subject"] == "TRADEGEN compliance: new exposure is blocked (exit 3)", shown
    assert "Recording this alert in alerts.jsonl failed" in shown["body"], shown          # the push and email say so


def test_alerts_runs_as_main_module():
    """`python -m core.compliance.alerts` runs the file as `__main__`, a second copy: it must still use the
    module-level _toast seam of the imported module, so tests (and the daily task) go through one set of names."""
    calls = []
    summary = _sample(code=1, due=[_due_item(today=date(2026, 11, 8))])
    with _patched(alerts, "_toast", lambda title, body: calls.append((title, body)) or True),             _patched(subprocess, "run", _boom):
        code, lines = _run_module("core.compliance.alerts",
                                  ["--today", "2026-11-08", "--summary", json.dumps(summary)])
    shown = json.loads(lines[-1])
    assert code == 0 and shown["send"] is True and calls == [(shown["subject"], shown["body"])], (code, lines, calls)
    assert [(r["channel"], r["result"]) for r in _alerts_lines()] == [("toast", "ok")], _alerts_lines()


def test_alerts_main_nothing_owed_sends_nothing():
    with _patched(alerts, "_toast", _boom), _patched(subprocess, "run", _boom):
        code, _, shown = _run_main(alerts.main, ["--today", "2026-10-23", "--summary", json.dumps(_sample())])
    assert code == 0 and shown == {"send": False, "subject": "", "body": ""}, shown
    assert not owner.alerts_path().exists()


def test_alerts_main_summary_missing_or_mismatched():
    for argv in (["--today", "2026-10-23"], ["--today", "2026-10-23", "--summary", "not json"],
                 ["--today", "2026-10-23", "--summary", "[" * 100_000],           # RecursionError, not ValueError
                 ["--today", "2026-10-23", "--summary", json.dumps(_sample()), "--code", "3"]):
        with _patched(alerts, "_toast", lambda title, body: True), _patched(subprocess, "run", _boom):
            code, _, shown = _run_main(alerts.main, argv)
        assert code == 0 and shown["send"] is True, (argv[:3], shown)
        assert shown["subject"] == "TRADEGEN compliance: the daily check gave no usable summary", shown
    rows = _alerts_lines()
    assert len(rows) == 4 and all(r["code"] == 4 and r["head_seq"] == 0 for r in rows), rows


def test_alerts_main_log_mode():
    summary = _sample(code=2, overdue=[{"row": "KR-X", "field": "review_by", "date": "2026-11-22", "days_late": 1}])
    with _patched(alerts, "_toast", _boom), _patched(subprocess, "run", _boom):           # --log never shows a toast
        code, _, shown = _run_main(alerts.main, ["--log", "email", "ok", "--summary", json.dumps(summary)])
        assert code == 0 and shown == {"logged": "email", "result": "ok"}, shown
        code, _, shown = _run_main(alerts.main, ["--log", "sms", "ok", "--summary", json.dumps(summary)])
        assert code == 1 and "error" in shown, shown
        code, _, shown = _run_main(alerts.main, ["--log", "push", "ok", "--bogus"])
        assert code == 1 and "error" in shown, shown
    rows = _alerts_lines()
    assert [(r["channel"], r["result"], r["overdue"]) for r in rows] == [("email", "ok", summary["overdue"])], rows


def test_owner_alert_email_is_literal():
    assert alerts.OWNER_ALERT_EMAIL == "sapientia@korea.ac.kr"
    assert tuple(alerts._MISSING) == rules._SUMMARY_KEYS
