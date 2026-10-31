"""D16 live evidence (E1 spec 6 and 8; plan Tasks 9 and 10). Task 9: the pure fold owner.evidence_in_force over
execution/evidence.jsonl, its chain check owner.evidence_chain, and load_context reading the file into
Context.live_evidence. Task 10 appends the writer's tests. Lines are built here without owner.py, as
tests.compliance_fixtures.signed_entry builds owner-log lines. Helpers are prefixed `_t9_`; Task 10 reuses them."""
from __future__ import annotations

import json
import os
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core import isolation
from core.compliance import model, owner, rules
from execution import evidence as E
from execution import snapshot as S
from tests import execution_fixtures as F

_T9_SNAP = "5" * 64                                     # a snapshot_sha256; the fold checks only its form
_T9_MET = 100_000_000.0                                 # at or above every threshold
_T9_TODAY = date(2026, 10, 24)


def _t9_sealed(body: dict) -> bytes:
    """`body` plus the row_sha256 over it, as one canonical JSON line."""
    row = model.sha256_hex(model.canonical_json(body))
    return (model.canonical_json({**body, "row_sha256": row}) + "\n").encode("utf-8")


def _t9_body(seq: int, prev: str, utc: str, requirement: str, met, value_krw=None) -> dict:
    """One record in the spec 6 format; value_krw defaults to a value that agrees with `met`."""
    if value_krw is None:
        value_krw = _T9_MET if met else 0.0
    return {"seq": seq, "prev_sha256": prev, "utc": utc, "requirement": requirement, "met": met,
            "value_krw": value_krw, "snapshot_sha256": _T9_SNAP}


def _t9_chain(*records) -> list[bytes]:
    """Chained lines, seq from 1, from (utc, requirement, met) or (utc, requirement, met, value_krw) tuples."""
    lines, prev = [], "0" * 64
    for seq, record in enumerate(records, start=1):
        lines.append(_t9_sealed(_t9_body(seq, prev, *record)))
        prev = _t9_prev(lines)
    return lines


def _t9_prev(lines: list[bytes]) -> str:
    """The row_sha256 of the last line, which the next line's prev_sha256 must name."""
    return json.loads(lines[-1])["row_sha256"]


def test_vocabulary_is_the_four_deposit_items_inside_live_requirements():
    assert list(owner.EVIDENCE_THRESHOLDS_KRW.items()) == [               # Task 10 judges and writes in this order
        ("deposit_krw_10m", 10_000_000.0), ("deposit_krw_15m", 15_000_000.0), ("deposit_krw_20m", 20_000_000.0),
        ("cash_krw_30m", 30_000_000.0)]
    assert set(owner.EVIDENCE_THRESHOLDS_KRW) <= rules.LIVE_REQUIREMENTS
    assert not {"broker_approval", "collateral_105pct"} & set(owner.EVIDENCE_THRESHOLDS_KRW)   # never E1 evidence
    assert owner.EVIDENCE_KEYS == ("seq", "prev_sha256", "utc", "requirement", "met", "value_krw", "snapshot_sha256")
    assert owner.EVIDENCE_MAX_AGE_DAYS == 7
    assert owner.evidence_path() == isolation.state_root() / "execution" / "evidence.jsonl"
    assert not owner.evidence_path().parent.exists()                 # computing the path creates nothing
    try:
        owner.EVIDENCE_THRESHOLDS_KRW["deposit_krw_10m"] = 1.0
    except TypeError:
        pass
    else:
        raise AssertionError("the thresholds can be changed at run time")


def test_a_met_record_counts_from_the_next_asia_seoul_day():
    """23:59:59 KST on 2026-10-23 counts from 2026-10-24; 00:00:00 KST on 2026-10-24 counts only from 2026-10-25."""
    before = _t9_chain(("2026-10-23T14:59:59Z", "deposit_krw_10m", True))
    after = _t9_chain(("2026-10-23T15:00:00Z", "deposit_krw_10m", True))
    assert owner.evidence_in_force(before, date(2026, 10, 23)) == frozenset()
    assert owner.evidence_in_force(before, _T9_TODAY) == {"deposit_krw_10m"}
    assert owner.evidence_in_force(after, _T9_TODAY) == frozenset()
    assert owner.evidence_in_force(after, date(2026, 10, 25)) == {"deposit_krw_10m"}
    at = _t9_chain(("2026-10-20T00:00:00Z", "deposit_krw_15m", True, 15_000_000.0))       # exactly the threshold
    assert owner.evidence_in_force(at, _T9_TODAY) == {"deposit_krw_15m"}
    unmet = _t9_chain(("2026-10-20T00:00:00Z", "deposit_krw_15m", False, 14_999_999.0))
    assert owner.evidence_in_force(unmet, _T9_TODAY) == frozenset()
    assert owner.evidence_in_force([], _T9_TODAY) == frozenset()


def test_a_later_unmet_record_removes_the_item_at_once():
    lifted = (("2026-10-20T00:00:00Z", "deposit_krw_10m", True), ("2026-10-20T00:00:00Z", "deposit_krw_15m", True))
    assert owner.evidence_in_force(_t9_chain(*lifted), _T9_TODAY) == {"deposit_krw_10m", "deposit_krw_15m"}
    dropped = _t9_chain(*lifted, ("2026-10-24T01:00:00Z", "deposit_krw_15m", False))     # 10:00 KST today
    assert owner.evidence_in_force(dropped, _T9_TODAY) == {"deposit_krw_10m"}
    regained = _t9_chain(*lifted, ("2026-10-22T01:00:00Z", "deposit_krw_15m", False),
                         ("2026-10-23T01:00:00Z", "deposit_krw_15m", True))
    assert owner.evidence_in_force(regained, date(2026, 10, 23)) == {"deposit_krw_10m"}   # a new run starts that day
    assert owner.evidence_in_force(regained, _T9_TODAY) == {"deposit_krw_10m", "deposit_krw_15m"}


def test_the_latest_met_record_expires_after_seven_days():
    once = _t9_chain(("2026-10-16T03:00:00Z", "cash_krw_30m", True))                      # 12:00 KST on 2026-10-16
    assert owner.evidence_in_force(once, date(2026, 10, 23)) == {"cash_krw_30m"}            # 7 days old: counts
    assert owner.evidence_in_force(once, _T9_TODAY) == frozenset()                         # 8 days old: expired
    renewed = _t9_chain(("2026-10-16T03:00:00Z", "cash_krw_30m", True),
                        ("2026-10-23T03:00:00Z", "cash_krw_30m", True))                     # a daily heartbeat
    assert owner.evidence_in_force(renewed, _T9_TODAY) == {"cash_krw_30m"}
    assert owner.evidence_in_force(renewed, date(2026, 10, 30)) == {"cash_krw_30m"}
    assert owner.evidence_in_force(renewed, date(2026, 10, 31)) == frozenset()


def test_records_stamped_ahead_or_back_are_dated_as_late_as_the_log_allows():
    ahead = _t9_chain(("2026-10-20T00:00:00Z", "deposit_krw_20m", True),
                      ("2026-10-25T00:00:00Z", "deposit_krw_20m", True))                    # 09:00 KST tomorrow
    assert owner.evidence_in_force(ahead, _T9_TODAY) == frozenset()                        # latest record is ahead
    assert owner.evidence_in_force(ahead, date(2026, 10, 25)) == {"deposit_krw_20m"}
    back = _t9_chain(("2026-10-24T01:00:00Z", "deposit_krw_15m", False),                   # 10:00 KST today
                     ("2026-10-20T00:00:00Z", "deposit_krw_10m", True))                    # appended, stamped back
    assert owner.evidence_in_force(back, _T9_TODAY) == frozenset()                         # dated today, not 10-20
    assert owner.evidence_in_force(back, date(2026, 10, 25)) == {"deposit_krw_10m"}
    stale_back = _t9_chain(("2026-10-24T01:00:00Z", "deposit_krw_15m", False),
                           ("2026-10-10T00:00:00Z", "deposit_krw_10m", True))              # stamped 15 days back
    assert owner.evidence_in_force(stale_back, date(2026, 10, 25)) == frozenset()          # expiry reads its own stamp


def test_every_chain_defect_gives_no_evidence_at_all():
    good = _t9_chain(("2026-10-20T00:00:00Z", "deposit_krw_10m", True),
                     ("2026-10-20T00:00:00Z", "deposit_krw_15m", True))
    rows, why = owner.evidence_chain(good)
    assert why == "" and [r["seq"] for r in rows] == [1, 2] and rows[1]["requirement"] == "deposit_krw_15m", why
    assert owner.evidence_in_force(good, _T9_TODAY) == {"deposit_krw_10m", "deposit_krw_15m"}
    first = good[0]
    body = _t9_body(2, _t9_prev(good[:1]), "2026-10-20T00:00:00Z", "deposit_krw_15m", True)
    stale = json.loads(good[1])
    stale["utc"] = "2026-10-19T00:00:00Z"                                    # row_sha256 left as it was
    seconds = {
        "torn last line": good[1][:-1],
        "carriage return": good[1][:-1] + b"\r\n",
        "two lines in one": good[1] + good[1],
        "not bytes": good[1].decode("utf-8"),
        "not UTF-8": b"\xff\n",
        "not JSON": b"{\n",
        "deeply nested": b"[" * 100_000 + b"\n",
        "not an object": b"[]\n",
        "duplicate key": good[1].replace(b'{"met":true,', b'{"met":true,"met":true,'),
        "not canonical": good[1].replace(b",", b", ", 1),
        "NaN": good[1].replace(b'"value_krw":100000000.0', b'"value_krw":NaN'),
        "extra key": _t9_sealed({**body, "note": "x"}),
        "extra key on a sound row": (model.canonical_json({**json.loads(good[1]), "note": "x"}) + "\n").encode("utf-8"),
        "missing key": _t9_sealed({k: v for k, v in body.items() if k != "snapshot_sha256"}),
        "seq skips": _t9_sealed({**body, "seq": 3}),
        "prev does not chain": _t9_sealed({**body, "prev_sha256": "0" * 64}),
        "utc with an offset": _t9_sealed({**body, "utc": "2026-10-20T00:00:00+00:00"}),
        "utc past the last Seoul date": _t9_sealed({**body, "utc": "9999-12-31T15:00:00Z"}),
        "broker_approval": _t9_sealed({**body, "requirement": "broker_approval"}),
        "collateral_105pct": _t9_sealed({**body, "requirement": "collateral_105pct"}),
        "unknown item": _t9_sealed({**body, "requirement": "deposit_krw_1m"}),
        "met not a bool": _t9_sealed({**body, "met": 1}),
        "value a bool": _t9_sealed({**body, "value_krw": True}),
        "value below zero": _t9_sealed({**body, "met": False, "value_krw": -1.0}),
        "met below the threshold": _t9_sealed({**body, "value_krw": 14_999_999.0}),
        "unmet at the threshold": _t9_sealed({**body, "met": False, "value_krw": 15_000_000.0}),
        "snapshot not lower hex": _t9_sealed({**body, "snapshot_sha256": "A" * 64}),
        "row_sha256 stale": (model.canonical_json(stale) + "\n").encode("utf-8"),
    }
    texts = {"not one newline-terminated line", "unreadable", "not a JSON object", "not its canonical JSON",
             "not exactly the evidence keys", "seq does not count up from 1",
             "prev_sha256 does not chain to the line before", "utc is not YYYY-MM-DDTHH:MM:SSZ",
             "utc has no Asia/Seoul date", "requirement is not an E1 evidence item", "met is not true or false",
             "value_krw is not a number at or above zero", "met disagrees with value_krw",
             "snapshot_sha256 is not lower-case hex", "row_sha256 does not recompute", "RecursionError"}
    for defect, second in seconds.items():
        lines = [first, second]
        rows, why = owner.evidence_chain(lines)
        assert rows == [] and why[:8] == "line 2: " and why[8:] in texts, (defect, why)   # fixed text, no value
        assert owner.evidence_in_force(lines, _T9_TODAY) == frozenset(), defect      # not even the sound line 1
    for defect, text in (("extra key on a sound row", "not exactly the evidence keys"),
                         ("broker_approval", "requirement is not an E1 evidence item"),
                         ("utc past the last Seoul date", "utc has no Asia/Seoul date"),
                         ("met below the threshold", "met disagrees with value_krw")):
        assert owner.evidence_chain([first, seconds[defect]])[1] == f"line 2: {text}", defect
    edge = _t9_sealed({**body, "utc": "9999-12-31T14:59:59Z"})          # the last stamp with a Seoul date: sound
    assert owner.evidence_chain([first, edge])[1] == ""
    assert owner.evidence_in_force([first, edge], _T9_TODAY) == {"deposit_krw_10m"}   # line 2 is only ahead
    bool_seq = _t9_sealed({**_t9_body(1, "0" * 64, "2026-10-20T00:00:00Z", "deposit_krw_10m", True), "seq": True})
    assert owner.evidence_chain([bool_seq])[1].startswith("line 1: ")
    assert owner.evidence_chain(None) == ([], "line 0: TypeError")
    for junk in (None, 5, [None]):
        assert owner.evidence_in_force(junk, _T9_TODAY) == frozenset(), junk
    assert owner.evidence_in_force(good, "2026-10-24") == frozenset()             # a today that is not a date


def test_load_context_reads_live_evidence_and_creates_no_file():
    home = isolation.state_root()
    path = home / "execution" / "evidence.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"".join(_t9_chain(("2026-10-23T14:59:59Z", "deposit_krw_10m", True),
                                        ("2026-10-23T14:59:59Z", "deposit_krw_15m", False, 14_999_999.0))))
    listing = sorted(p.relative_to(home).as_posix() for p in home.rglob("*"))
    placeholder = model.Positions(equity_krw=1.0)                    # E24: what the poller passes
    same_day = owner.load_context(datetime(2026, 10, 23, 14, 59, 59, tzinfo=timezone.utc), placeholder)
    next_day = owner.load_context(datetime(2026, 10, 23, 15, 0, 0, tzinfo=timezone.utc), placeholder)
    assert model.is_sealed(same_day) and model.is_sealed(next_day)
    assert (same_day.date, next_day.date) == (date(2026, 10, 23), _T9_TODAY)
    assert (same_day.live_evidence, next_day.live_evidence) == (frozenset(), {"deposit_krw_10m"}), \
        (same_day.live_evidence, next_day.live_evidence)
    fallback = owner.load_context(datetime(2026, 10, 23, 15, 0, 0, tzinfo=timezone.utc), placeholder, session_id="")
    assert fallback.owner.reason == "load_context: internal error TypeError", fallback.owner.reason
    assert model.is_sealed(fallback) and fallback.live_evidence == frozenset()     # the fallback lifts nothing
    assert sorted(p.relative_to(home).as_posix() for p in home.rglob("*")) == listing, "load_context wrote a file"


def test_a_missing_unreadable_or_refused_file_gives_no_evidence():
    path = owner.evidence_path()
    assert owner._live_evidence(_T9_TODAY) == frozenset() and not path.parent.exists()   # missing; nothing created
    path.mkdir(parents=True)                                        # a folder where the file belongs: unreadable
    assert owner._live_evidence(_T9_TODAY) == frozenset()
    path.rmdir()
    path.write_bytes(b"".join(_t9_chain(("2026-10-20T00:00:00Z", "deposit_krw_10m", True))))
    assert owner._live_evidence(_T9_TODAY) == {"deposit_krw_10m"}                       # the positive control
    os.link(path, path.parent / "second-name.jsonl")                # a hard link under the state root (A0)
    isolation._LINK_SCAN.clear()                                    # state_root() keeps its scan per process
    assert owner._live_evidence(_T9_TODAY) == frozenset()


# --------------------------------------------------------------------------- #
# Task 10: the writer, execution/evidence.py (spec 6 "Evidence (E1-D4)"; E18, E33, E1R2-3)
# --------------------------------------------------------------------------- #
_T10_RATE = 1_250.0                                     # KRW per USD in these fixtures: 8,000 USD is 10,000,000 KRW


def _t10_home() -> Path:
    """The suite's temp TRADEGEN_HOME (tests.compliance_fixtures.temp_home names it tradegen_home_*). Any other state
    root is refused before a record is written, so a direct call outside the wrapper never writes real evidence."""
    root = isolation.state_root()
    if not root.name.startswith("tradegen_home_"):
        raise AssertionError(f"not inside the suite's temp home: {root}")
    return root


def _t10_kis(deposit=21_000_000.0, **fields) -> S.Snapshot:
    """An ok KIS snapshot stamped NOW whose deposit_krw (KIS dnca_tot_amt) is `deposit`; `fields` override."""
    return F.snap("kis", **({"deposit_krw": deposit} | fields))


def _t10_usd(usd: float, deposit=21_000_000.0, **fields) -> S.Snapshot:
    """_t10_kis with `usd` US dollars of foreign cash, priced at _T10_RATE."""
    return _t10_kis(deposit, cash={"KRW": 1.0, "USD": usd}, prices_krw={"USD": _T10_RATE, "005930": 61_000.0},
                    **fields)


def _t10_at(utc: str) -> datetime:
    """An aware instant from a stamp "YYYY-MM-DDTHH:MM:SSZ"."""
    return datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _t10_lines() -> list[bytes]:
    """evidence.jsonl split as owner._live_evidence splits it; [] when there is no file."""
    path = owner.evidence_path()
    return path.read_bytes().splitlines(keepends=True) if path.exists() else []


def _t10_items(rows) -> list[tuple]:
    """(requirement, met, value_krw) of each row."""
    return [(r["requirement"], r["met"], r["value_krw"]) for r in rows]


def test_judge_meets_each_threshold_at_it_and_not_one_won_below():
    items = ["deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m", "cash_krw_30m"]
    assert list(owner.EVIDENCE_THRESHOLDS_KRW) == items
    for item, threshold in owner.EVIDENCE_THRESHOLDS_KRW.items():
        for value, met in ((threshold - 1.0, False), (threshold, True)):
            judged = {i: (m, v) for i, m, v in E.judge(_t10_kis(value))}
            assert list(judged) == items, judged              # no foreign cash: cash_krw_30m is the deposit alone
            assert judged[item] == (met, value), (item, value, judged[item])
    assert E.judge(_t10_kis(15_000_000)) == [("deposit_krw_10m", True, 15e6), ("deposit_krw_15m", True, 15e6),
                                             ("deposit_krw_20m", False, 15e6), ("cash_krw_30m", False, 15e6)]
    assert all(type(v) is float for _i, _m, v in E.judge(_t10_kis(15_000_000)))   # an int deposit is written as float
    assert E.judge(_t10_kis(0.0)) == [(i, False, 0.0) for i in items]
    assert E.judge(_t10_kis(-1.0)) == [(i, False, 0.0) for i in items]       # below zero: unmet, written as 0.0


def test_cash_krw_30m_adds_foreign_cash_at_the_kis_rate():
    def cash(kis):
        return [(m, v) for i, m, v in E.judge(kis) if i == "cash_krw_30m"]

    assert cash(_t10_usd(8_000.0, 20_000_000.0)) == [(True, 30_000_000.0)]   # 20M + 8,000 x 1,250: at the threshold
    assert cash(_t10_usd(7_999.0, 20_000_000.0)) == [(False, 29_998_750.0)]  # KRW cash (D+2) is not added again
    two = _t10_kis(20_000_000.0, cash={"KRW": 9e6, "USD": 4_000.0, "JPY": 500_000.0},
                   prices_krw={"USD": _T10_RATE, "JPY": 10.0})
    assert cash(two) == [(True, 30_000_000.0)]
    assert [m for i, m, _v in E.judge(_t10_usd(8_000.0, 20_000_000.0)) if i != "cash_krw_30m"] == [True, True, True]
    no_rate = _t10_kis(20_000_000.0, cash={"KRW": 1.0, "USD": 8_000.0}, prices_krw={"005930": 61_000.0})
    assert [i for i, _m, _v in E.judge(no_rate)] == ["deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m"]
    lower = _t10_kis(1_000_000.0, cash={"USD": -100.0}, prices_krw={"USD": _T10_RATE})
    assert cash(lower) == [(False, 875_000.0)]                                # only the total is checked
    below_zero = _t10_kis(1_000_000.0, cash={"USD": -1_000.0}, prices_krw={"USD": _T10_RATE})
    assert cash(below_zero) == [(False, 0.0)]                                 # a total below zero: unmet, 0.0
    overflow = _t10_kis(1_000_000.0, cash={"USD": 1e300}, prices_krw={"USD": 1e300})
    assert cash(overflow) == [(False, 0.0)]                                   # inf: unmet, 0.0
    assert [(m, v) for i, m, v in E.judge(overflow) if i != "cash_krw_30m"] == [(False, 1e6)] * 3
    assert E.judge(_t10_usd(8_000.0, -1.0)) == [("deposit_krw_10m", False, 0.0), ("deposit_krw_15m", False, 0.0),
                                                ("deposit_krw_20m", False, 0.0), ("cash_krw_30m", False, 9_999_999.0)]
    assert E.judge(_t10_usd(8_000.0, None)) == []                             # no deposit_krw: nothing at all
    assert E.judge(_t10_usd(8_000.0, ok=False)) == []                         # a not-ok snapshot: nothing
    assert E.judge(S.failed("kis", "2026-10-24T00:00:00Z", "kis: x")) == []
    assert E.judge(F.snap("upbit", deposit_krw=50_000_000.0)) == []           # only KIS evidence counts


def test_a_snapshot_with_nothing_to_judge_touches_no_file():
    home = _t10_home()
    before = sorted(home.rglob("*"))
    for kis in (S.failed("kis", "2026-10-24T00:00:00Z", "code not signed", flags={"code_unsigned"}),
                _t10_kis(None), F.snap("okx", deposit_krw=21e6)):
        assert E.record(kis, F.NOW) == []
        assert sorted(home.rglob("*")) == before                              # no folder, no lock, no file
    broken = _t9_chain(("2026-10-20T00:00:00Z", "deposit_krw_10m", True))[0][:-1]     # a torn line
    owner.evidence_path().parent.mkdir(exist_ok=True)
    owner.evidence_path().write_bytes(broken)
    assert E.record(_t10_kis(None), F.NOW) == [] and owner.evidence_path().read_bytes() == broken   # not read


def test_record_on_an_empty_file_appends_one_chained_line_per_judged_item():
    home = _t10_home()
    owner.evidence_path().parent.mkdir(exist_ok=True)
    owner.evidence_path().write_bytes(b"")              # an empty file (a missing one: the tests below)
    kis = _t10_kis(21_000_000.0)
    rows = E.record(kis, F.NOW)
    assert _t10_items(rows) == [("deposit_krw_10m", True, 21e6), ("deposit_krw_15m", True, 21e6),
                                ("deposit_krw_20m", True, 21e6), ("cash_krw_30m", False, 21e6)]
    lines = _t10_lines()
    assert lines == [(model.canonical_json(r) + "\n").encode("utf-8") for r in rows]
    chain, why = owner.evidence_chain(lines)
    assert why == "" and chain == rows, why
    assert [r["seq"] for r in rows] == [1, 2, 3, 4] and rows[0]["prev_sha256"] == "0" * 64
    assert all(rows[n]["prev_sha256"] == rows[n - 1]["row_sha256"] for n in (1, 2, 3))
    assert {r["utc"] for r in rows} == {"2026-10-24T00:00:00Z"}
    assert {r["snapshot_sha256"] for r in rows} == {kis.snapshot_sha256}
    assert all(set(r) == set(owner.EVIDENCE_KEYS) | {"row_sha256"} for r in rows)
    assert lines[0] == ('{"met":true,"prev_sha256":"' + "0" * 64 + '","requirement":"deposit_krw_10m",'
                        f'"row_sha256":"{rows[0]["row_sha256"]}","seq":1,"snapshot_sha256":"{kis.snapshot_sha256}",'
                        '"utc":"2026-10-24T00:00:00Z","value_krw":21000000.0}\n').encode("utf-8")   # contract 14
    assert sorted(p.name for p in (home / "execution").iterdir()) == ["evidence.jsonl", "evidence.jsonl.lock"]


def test_the_same_seoul_day_appends_only_a_first_record_or_a_flipped_met():
    _t10_home()
    first = E.record(_t10_kis(21_000_000.0, cash={"USD": 8_000.0}, prices_krw={}), F.NOW)     # no rate: no cash
    assert [r["requirement"] for r in first] == ["deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m"]
    later = F.NOW + timedelta(minutes=5)
    assert _t10_items(E.record(_t10_usd(8_000.0), later)) == [("cash_krw_30m", True, 31e6)]   # its first record
    before = owner.evidence_path().read_bytes()
    assert E.record(_t10_usd(8_000.0), F.NOW + timedelta(minutes=10)) == []                    # nothing changed
    assert E.record(_t10_usd(9_000.0, 25_000_000.0), F.NOW + timedelta(minutes=15)) == []     # value_krw alone
    assert owner.evidence_path().read_bytes() == before
    flipped = E.record(_t10_usd(18_000.0, 12_000_000.0), F.NOW + timedelta(minutes=20))     # cash stays met
    assert _t10_items(flipped) == [("deposit_krw_15m", False, 12e6), ("deposit_krw_20m", False, 12e6)]
    assert [r["seq"] for r in flipped] == [5, 6] and owner.evidence_path().read_bytes().startswith(before)
    dropped = E.record(_t10_usd(0.0, 12_000_000.0), F.NOW + timedelta(minutes=25))
    assert _t10_items(dropped) == [("cash_krw_30m", False, 12e6)]
    rows, why = owner.evidence_chain(_t10_lines())
    assert why == "" and [r["seq"] for r in rows] == [1, 2, 3, 4, 5, 6, 7], why
    assert {r["utc"][:10] for r in rows} == {"2026-10-24"}


def test_the_first_poll_of_the_next_seoul_day_is_a_heartbeat_for_every_judged_item():
    _t10_home()
    late = _t10_at("2026-10-24T14:59:59Z")                                    # 23:59:59 KST on 24 October
    assert len(E.record(_t10_usd(8_000.0), late)) == 4
    assert E.record(_t10_usd(8_000.0), late) == []
    beat = E.record(_t10_usd(8_000.0), _t10_at("2026-10-24T15:00:00Z"))       # 00:00:00 KST on 25 October
    assert _t10_items(beat) == [("deposit_krw_10m", True, 21e6), ("deposit_krw_15m", True, 21e6),
                                ("deposit_krw_20m", True, 21e6), ("cash_krw_30m", True, 31e6)]
    assert [r["seq"] for r in beat] == [5, 6, 7, 8] and {r["utc"] for r in beat} == {"2026-10-24T15:00:00Z"}
    assert E.record(_t10_usd(8_000.0), _t10_at("2026-10-24T15:05:00Z")) == []
    no_rate = _t10_kis(21_000_000.0, cash={"USD": 8_000.0}, prices_krw={})
    next_beat = E.record(no_rate, _t10_at("2026-10-25T15:00:00Z"))            # 00:00 KST on 26 October
    assert [r["requirement"] for r in next_beat] == ["deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m"]
    assert owner.evidence_chain(_t10_lines())[1] == "" and len(_t10_lines()) == 11


def test_due_on_synthetic_rows():
    rows = [{"requirement": "deposit_krw_10m", "met": True, "utc": "2026-10-23T03:00:00Z"},
            {"requirement": "deposit_krw_15m", "met": False, "utc": "2026-10-24T14:59:59Z"},
            {"requirement": "deposit_krw_10m", "met": False, "utc": "2026-10-24T14:59:59Z"}]
    same_day, next_day = _t10_at("2026-10-24T14:59:59Z"), _t10_at("2026-10-24T15:00:00Z")
    assert E.due([], "deposit_krw_10m", True, same_day)                       # no record yet
    assert E.due(rows, "cash_krw_30m", False, same_day)                       # none of that item
    assert not E.due(rows, "deposit_krw_10m", False, same_day)                # the LAST record of the item counts
    assert E.due(rows, "deposit_krw_10m", True, same_day)                     # met flipped
    assert not E.due(rows, "deposit_krw_15m", False, same_day)
    assert E.due(rows, "deposit_krw_15m", False, next_day)                    # 00:00:00 KST: the daily heartbeat
    assert E.due(rows, "deposit_krw_10m", False, next_day)
    assert E.due(rows, "deposit_krw_15m", False, _t10_at("2026-10-23T03:00:00Z"))   # dated after now: re-stamped now
    assert not E.due(rows[:1], "deposit_krw_10m", True, _t10_at("2026-10-23T14:59:59Z"))
    assert E.due(rows[:1], "deposit_krw_10m", True, _t10_at("2026-10-23T15:00:00Z"))
    for some in ([], rows):                                                   # no record, then a record to compare
        try:
            E.due(some, "deposit_krw_15m", False, datetime(2026, 10, 25, 9, 0, 0))   # naive: refused, as iso_utc does
        except ValueError:
            pass
        else:
            raise AssertionError(f"a naive now was accepted with {len(some)} rows")


def test_records_written_on_day_d_lift_on_day_d_plus_one_and_expire_when_polls_stop():
    _t10_home()
    E.record(_t10_kis(21_000_000.0), F.NOW)                                   # 09:00 KST on 24 October
    lines = _t10_lines()
    assert owner.evidence_chain(lines)[1] == ""
    assert owner.evidence_in_force(lines, date(2026, 10, 24)) == frozenset()
    lifted = {"deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m"}
    assert owner.evidence_in_force(lines, date(2026, 10, 25)) == lifted
    assert owner._live_evidence(date(2026, 10, 25)) == lifted                 # load_context's reader agrees
    for day in (25, 26, 27):                                                  # one poll a day: the heartbeats
        assert len(E.record(_t10_kis(21_000_000.0), datetime(2026, 10, day, 0, 0, 0, tzinfo=timezone.utc))) == 4
    lines = _t10_lines()
    assert owner.evidence_in_force(lines, date(2026, 11, 3)) == lifted        # 7 days after the last heartbeat
    assert owner.evidence_in_force(lines, date(2026, 11, 4)) == frozenset()   # 8 days: a stopped poller fails closed
    E.record(_t10_kis(12_000_000.0), datetime(2026, 10, 28, 1, 0, 0, tzinfo=timezone.utc))
    assert owner.evidence_in_force(_t10_lines(), date(2026, 10, 28)) == {"deposit_krw_10m"}   # tightened at once


def test_a_deposit_below_zero_is_recorded_unmet_and_tightens_at_once():
    _t10_home()
    assert len(E.record(_t10_kis(21_000_000.0), F.NOW)) == 4                 # 09:00 KST on 24 October
    lifted = {"deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m"}
    assert owner.evidence_in_force(_t10_lines(), date(2026, 10, 26)) == lifted
    below = E.record(_t10_kis(-5_000_000.0), F.NOW + timedelta(days=2))     # ok, with dnca_tot_amt below zero
    assert _t10_items(below) == [(i, False, 0.0) for i in owner.EVIDENCE_THRESHOLDS_KRW]   # 3 flips, 1 heartbeat
    lines = _t10_lines()
    assert owner.evidence_chain(lines)[1] == "" and len(lines) == 8          # the chain stays sound
    assert owner.evidence_in_force(lines, date(2026, 10, 26)) == frozenset()  # removed at once, not 7 days later
    assert owner.evidence_in_force(lines, date(2026, 10, 31)) == frozenset()


def _t10_history(rng: random.Random, polls: int) -> list[tuple[datetime, S.Snapshot]]:
    """One random KIS history after the manner of e1/sandbox_round2/fold_probe.py: 5-minute steps, gaps of 7 hours,
    2 days and 9 days, 1-second steps, polls with KIS not ok, a missing deposit_krw or a missing USD rate. The deposit
    is drawn afresh at each poll, so every threshold is crossed both ways."""
    now, out = datetime(2026, 10, 20, 14, 50, 0, tzinfo=timezone.utc), []    # 23:50 KST on 20 October
    steps = [timedelta(minutes=5)] * 6 + [timedelta(hours=7), timedelta(days=2), timedelta(days=9),
                                          timedelta(seconds=1)]
    for _ in range(polls):
        now += rng.choice(steps)
        deposit = rng.choice([9e6, 12e6, 16e6, 21e6])                   # below 10M, and past 10M, 15M and 20M
        fields = {"utc": model.iso_utc(now), "cash": {"KRW": 1.0, "USD": rng.choice([0.0, 8_000.0, 12_000.0])},
                  "prices_krw": {"USD": _T10_RATE}}
        roll, shown = rng.random(), deposit
        if roll < 0.1:
            fields["ok"] = False
        elif roll < 0.15:
            shown = None
        elif roll < 0.25:
            fields["prices_krw"] = {}
        out.append((now, _t10_kis(shown, **fields)))
    return out


def _t10_midnight() -> list[tuple[datetime, S.Snapshot]]:
    """1-second steps across Seoul midnight with met flipping on each side, then gaps of 2 and 8 Seoul days (the
    second crosses the 7-day expiry)."""
    script = (("2026-10-23T14:59:58Z", 21e6, 8_000.0), ("2026-10-23T14:59:59Z", 12e6, 8_000.0),
              ("2026-10-23T15:00:00Z", 21e6, 8_000.0), ("2026-10-23T15:00:01Z", 21e6, 0.0),
              ("2026-10-23T15:00:02Z", None, 0.0), ("2026-10-24T14:59:59Z", 21e6, 8_000.0),
              ("2026-10-24T15:00:00Z", 16e6, 8_000.0), ("2026-10-26T15:00:00Z", 16e6, 8_000.0),
              ("2026-11-04T00:00:00Z", 9e6, 0.0), ("2026-11-04T00:05:00Z", 21e6, 8_000.0))
    return [(_t10_at(utc), _t10_usd(usd, deposit, utc=utc)) for utc, deposit, usd in script]


def _t10_backclock() -> list[tuple[datetime, S.Snapshot]]:
    """The PC clock runs 5 days ahead at the second poll and is set right before the third; then the poller stops."""
    script = ("2026-10-20T01:00:00Z", "2026-10-30T01:00:00Z", "2026-10-25T01:00:00Z", "2026-10-25T02:00:00Z")
    return [(_t10_at(utc), _t10_kis(21e6, utc=utc)) for utc in script]


def _t10_run(polls, folder: Path, every_poll: bool) -> tuple[list[bytes], list[int]]:
    """`polls` through evidence.record with the state root moved to `folder` (save/restore). With `every_poll`,
    evidence.due is patched to return True: one record per judged item per poll, as spec 6 rev 1 wrote them.
    Returns the file's lines and the line count after each poll."""
    saved_home, saved_due = os.environ["TRADEGEN_HOME"], E.due
    os.environ["TRADEGEN_HOME"] = str(folder)
    if every_poll:
        E.due = lambda rows, requirement, met, now: True
    try:
        counts = []
        for now, kis in polls:
            counts.append((counts[-1] if counts else 0) + len(E.record(kis, now)))
        lines = _t10_lines()
    finally:
        E.due = saved_due
        os.environ["TRADEGEN_HOME"] = saved_home
    assert len(lines) == counts[-1] and owner.evidence_chain(lines)[1] == ""
    return lines, counts


def test_change_and_heartbeat_records_give_the_same_evidence_as_one_record_per_poll():
    """E1R2-3 (spec rev 2): for every prefix of each history and every Asia/Seoul day from the prefix's last poll to
    9 days after, owner.evidence_in_force reads the same live_evidence from the lines record writes as from one record
    per judged item per poll (the same polls with evidence.due patched to always return True)."""
    home = _t10_home()
    histories = [_t10_midnight(), _t10_history(random.Random(8), 12), _t10_backclock()]   # seed 8: every kind
    compared, kept = 0, 0
    for n, polls in enumerate(histories):
        lean, lean_counts = _t10_run(polls, home / f"lean{n}", every_poll=False)
        full, full_counts = _t10_run(polls, home / f"full{n}", every_poll=True)
        assert len(lean) <= len(full), (n, len(lean), len(full))
        kept += len(full) - len(lean)
        lifted = 0
        for (now, _kis), a, b in zip(polls, lean_counts, full_counts):
            last = now.astimezone(model.KST).date()
            for k in range(10):
                today = last + timedelta(days=k)
                mine, every = owner.evidence_in_force(lean[:a], today), owner.evidence_in_force(full[:b], today)
                assert mine == every, (n, model.iso_utc(now), today, mine, every)
                compared += 1
                lifted += bool(mine)
        assert 0 < lifted < 10 * len(polls), (n, lifted)                   # each history: neither side vacuous
        assert {json.loads(line)["requirement"] for line in full} <= set(owner.EVIDENCE_THRESHOLDS_KRW)
    assert compared == 260 and kept > 0, (compared, kept)                 # 10, 12 and 4 polls, 10 days each


def test_a_broken_chain_raises_evidence_broken_and_appends_nothing():
    assert issubclass(E.EvidenceBroken, Exception)
    assert not issubclass(E.EvidenceBroken, (RuntimeError, ValueError, OSError))   # poll_once catches only this
    _t10_home()
    path = owner.evidence_path()
    path.parent.mkdir(exist_ok=True)
    good = _t9_chain(("2026-10-20T00:00:00Z", "deposit_krw_10m", True))
    body = _t9_body(2, _t9_prev(good), "2026-10-20T00:00:00Z", "deposit_krw_15m", True)
    second = {
        "torn last line": _t9_sealed(body)[:-1],
        "met below the threshold": _t9_sealed({**body, "value_krw": 14_999_999.0}),
        "broker_approval": _t9_sealed({**body, "requirement": "broker_approval"}),
        "collateral_105pct": _t9_sealed({**body, "requirement": "collateral_105pct"}),
        "seq skips": _t9_sealed({**body, "seq": 3}),
        "not canonical": _t9_sealed(body).replace(b",", b", ", 1),
        "utc past the last Seoul date": _t9_sealed({**body, "utc": "9999-12-31T15:00:00Z"}),   # not OverflowError
    }
    for defect, line in second.items():
        path.write_bytes(good[0] + line)
        try:
            E.record(_t10_kis(), F.NOW)
        except E.EvidenceBroken as exc:
            text = str(exc)
        else:
            raise AssertionError(f"{defect}: no EvidenceBroken")
        assert text.startswith("evidence.jsonl is broken (line 2: ") and text.endswith("); nothing appended"), text
        assert "14999999" not in text and "100000000" not in text, text          # names a defect, never a value
        assert path.read_bytes() == good[0] + line, defect                       # nothing appended
    path.write_bytes(good[0])
    assert len(E.record(_t10_kis(), F.NOW)) == 4                              # the positive control: sound again


def test_a_linked_evidence_file_is_refused_before_it_is_read():
    home = _t10_home()
    path = owner.evidence_path()                        # the state-root link scan runs now, on a clean root
    path.parent.mkdir(exist_ok=True)
    for victim_bytes in (b"".join(_t9_chain(("2026-10-20T00:00:00Z", "deposit_krw_10m", True))),   # a sound chain
                         b"another file's bytes: E1 never writes them\n"):                          # not a chain
        victim = home / "victim.jsonl"
        victim.write_bytes(victim_bytes)
        os.link(victim, path)
        try:
            E.record(_t10_kis(), F.NOW)
        except E.EvidenceBroken:
            raise AssertionError("a hard link read as a broken chain") from None
        except RuntimeError as exc:
            assert "is a hard link" in str(exc), str(exc)
        else:
            raise AssertionError("a hard-linked evidence.jsonl was written")
        assert victim.read_bytes() == victim_bytes and path.read_bytes() == victim_bytes
        path.unlink()
        victim.unlink()
    path.mkdir()                                        # a folder in place of the file: a crash too, never amber
    try:
        E.record(_t10_kis(), F.NOW)
    except E.EvidenceBroken:
        raise AssertionError("a folder read as a broken chain") from None
    except OSError:
        pass
    else:
        raise AssertionError("a folder in place of evidence.jsonl was accepted")
    path.rmdir()


def test_record_checks_every_target_before_it_opens_it():
    _t10_home()
    seen, real_s, real_e, refuse = [], S.checked_target, E.checked_target, 0

    def spy(path, what="path", **kw):
        seen.append((Path(path).name, what))
        if refuse and what == "E1 evidence log" and len([s for s in seen if s[1] == what]) == refuse:
            raise RuntimeError(f"{what} {path} is refused here")
        return real_s(path, what, **kw)

    S.checked_target = E.checked_target = spy
    try:
        assert len(E.record(_t10_kis(), F.NOW)) == 4
        assert seen == [("execution", "E1 state folder"), ("evidence.jsonl.lock", "E1 lock file"),
                        ("evidence.jsonl", "E1 evidence log"), ("evidence.jsonl", "E1 evidence log")], seen
        before = owner.evidence_path().read_bytes()
        for refuse in (1, 2):                           # refused before the read, then before the write
            seen.clear()
            try:
                E.record(_t10_kis(12_000_000.0), F.NOW)
            except RuntimeError as exc:
                assert "is refused here" in str(exc) and not isinstance(exc, E.EvidenceBroken), str(exc)
            else:
                raise AssertionError(f"refusal {refuse} was swallowed")
            assert owner.evidence_path().read_bytes() == before, refuse          # nothing appended
    finally:
        S.checked_target, E.checked_target = real_s, real_e


def test_broker_approval_and_collateral_are_never_written():
    _t10_home()
    rich = _t10_kis(1e12, cash={"KRW": 1e12, "USD": 1e9, "JPY": 1e9}, prices_krw={"USD": 1_500.0, "JPY": 10.0})
    assert [i for i, met, _v in E.judge(rich) if met] == list(owner.EVIDENCE_THRESHOLDS_KRW)   # every item met
    for day in range(3):
        assert len(E.record(rich, F.NOW + timedelta(days=day))) == 4
    written = {json.loads(line)["requirement"] for line in _t10_lines()}
    assert written == set(owner.EVIDENCE_THRESHOLDS_KRW), written
    raw = owner.evidence_path().read_bytes()
    assert b"broker_approval" not in raw and b"collateral_105pct" not in raw
