"""Odds plan Task 16: calendar, sessions, provenance and the persisted odds state in core/oddsdata/inputs.py (spec 4
"Calendars", "Provenance", 7.3 "Seeds"; O1, O6, O12; R2-6; Q6, Q12, Q22, Q34, Q36).

Every test runs inside tests.odds_acceptance._wrap (hermetic, a temp TRADEGEN_HOME). Owner logs are built only in
temp homes signed with the fixed test key (tests.compliance_fixtures.full_home). The provenance originals
(core.quant.gate_ledger, core.ficc.macro_artifacts) are imported here, by the tests, never by the module under test."""
from __future__ import annotations

import ast
import contextlib
import dataclasses
import hashlib
import importlib.metadata
import json
import math
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from core import isolation
from core.calendars import clocks
from core.calendars.store import CalendarSet
from core.compliance import model, owner, rules
from core.odds import plan as P
from core.oddsdata import inputs
from tests import compliance_fixtures as F
from tests import compliance_guards as CG
from tests.macro_m1_calendars import fixture_set

ROOT = Path(__file__).resolve().parents[1]
KST = model.KST
START = date(2026, 10, 24)                     # F.NOW's Asia/Seoul date, a Saturday
NO_APPROVAL = "unsigned: no signed calendar approval"
ALTERED = "unsigned: the stored calendar set does not hash to its approval"
KRX_30 = ("2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03",
          "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12",
          "2026-11-13", "2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20")
H1, H2, H3 = "1" * 64, "2" * 64, "3" * 64       # plan hashes (64 hex)


def _raises(fn, exc=Exception) -> Exception:
    try:
        fn()
    except exc as e:
        return e
    raise AssertionError(f"expected {exc.__name__}")


def _stream(folder: Path) -> bytes:
    return rules.calendar_stream(folder)


@contextlib.contextmanager
def _home(calendar_raw: bytes | None = None, *, signed: bool = True):
    """A fresh temp home: with signed=True the test key's owner log approves the shipped tables, signs the code hash
    and, when given, approves `calendar_raw` as the calendar set (all stamped 2026-10-23T00:00:00Z); with
    signed=False nothing is signed at all."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        if signed:
            F.full_home(home, calendar_raw=calendar_raw)
        yield home


def _plan() -> P.Plan:
    return P.Plan(name="inputs test", track="compounding", stake_krw=42_000.0, target_krw=42_000_000.0,
                  fx_krw_per_usd=1_400.0, start=START, horizon_days=30,
                  leg=P.Leg(venue="upbit", symbol="BTC", model="bootstrap"), fraction=P.fixed(1.0))


# --------------------------------------------------------------------------- #
# The calendar set (O6, Q6) and the sessions (Q22)
# --------------------------------------------------------------------------- #
def test_calendar_for_takes_only_an_owner_approved_set_from_the_store():
    """CALENDAR_UNSIGNED's inputs: with nothing signed, and with a verified owner log that approves the tables but no
    calendar (`_calendar_approval` says "none", not "log"), there is no set. A set already in the store whose
    approval is not yet in force is the NOW - 2 days check of the next test. The shipped drafts approved by the owner
    do give a set, but no session: their own files are unsigned."""
    shipped = _stream(ROOT / "core" / "calendars" / "data")
    with _home(signed=False):
        assert inputs.calendar_for(F.NOW) == (None, "", NO_APPROVAL)
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        key = F.owner_key(home)                                       # a verified log that approves no calendar
        for kind in F.TABLES:
            F.approve(home, key, kind, F.shipped_bytes(kind))
        assert owner._calendar_approval(F.NOW) == ("none", ""), owner._calendar_approval(F.NOW)
        assert inputs.calendar_for(F.NOW) == (None, "", NO_APPROVAL)
    with _home(shipped):
        cal, sha, err = inputs.calendar_for(F.NOW)
        assert cal is not None and sha == model.sha256_hex(shipped) and err == "", (sha, err)
        for market in ("KR", "US"):
            got = inputs.sessions(market, START, 30, cal)
            assert got[:4] == ((), (), (), "") and got[4].startswith("unsigned: "), (market, got)


def test_the_approved_fixture_set_gives_sessions_limits_and_md5s():
    """One full temp home approves fixture_set(). The set comes from the store under the sha calendar_in_force
    names, with the files sessions() reads already loaded: a stored copy overwritten right after calendar_for
    returned never reaches sessions(). With core.calendars' three `default` functions patched to raise (clocks.py and
    regime.py bind the name at import), every call passes cal=: KRX sessions of [2026-10-24, 2026-11-23) with the
    dated price limit 0.30 and the three KR md5s; US sessions whose scheduled closes (EDT, EST, the 13:00 early close
    of 2026-11-27) fall on the Asia/Seoul date d + 1; a horizon past 2027-12-31 gives "coverage: ..." and the last
    one inside it passes. The next calendar_for refuses the edited copy, and so does one whose calendar_in_force
    check came before the edit."""
    from core.calendars import regime, store
    fixture = _stream(fixture_set().data_dir)
    sha = model.sha256_hex(fixture)
    ref = fixture_set()

    def boom():
        raise AssertionError("a core.calendars default() was called")
    with _home(fixture):
        cal, got_sha, err = inputs.calendar_for(F.NOW)
        assert got_sha == sha == owner.calendar_in_force(F.NOW) and err == "", (got_sha, err)
        assert isinstance(cal, CalendarSet) and cal.data_dir == owner.store_dir() / "calendar" / sha, cal
        assert inputs.calendar_for(F.NOW - timedelta(days=2)) == (None, "", NO_APPROVAL)   # before it was signed
        _raises(lambda: inputs.calendar_for(datetime(2026, 10, 24, 9, 0)), ValueError)   # naive
        stored = cal.data_dir / "holidays_KRX.yaml"
        approved = stored.read_bytes()
        stored.write_bytes(b"\xff not the approved file\n")          # after calendar_for: sessions() never reads it
        saved = (store.default, clocks.default, regime.default)
        store.default = clocks.default = regime.default = boom
        try:
            kr = inputs.sessions("KR", START, 30, cal)
            us = inputs.sessions("US", START, 60, cal)
            closes = {d: clocks.decision_time_utc("US", date.fromisoformat(d), cal=cal) for d in us[0]}
            late = {m: inputs.sessions(m, date(2027, 12, 20), 30, cal) for m in ("KR", "US")}
            last = {m: inputs.sessions(m, date(2027, 12, 2), 30, cal) for m in ("KR", "US")}   # [12-02, 2028-01-01)
        finally:
            store.default, clocks.default, regime.default = saved
        assert inputs.calendar_for(F.NOW) == (None, "", NO_APPROVAL)         # calendar_in_force sees the edit
        stored.write_bytes(approved + b"# edited after approval\n")
        keep = owner.calendar_in_force
        owner.calendar_in_force = lambda now: sha                            # an edit after that check
        try:
            assert inputs.calendar_for(F.NOW) == (None, "", ALTERED)
            for malformed in (b"\xff not UTF-8\n", b"[broken YAML\n"):
                stored.write_bytes(malformed)
                assert inputs.calendar_for(F.NOW) == (None, "", ALTERED)
        finally:
            owner.calendar_in_force = keep
    dates, limits, md5s, version, error = kr
    assert (dates, limits, version, error) == (KRX_30, (0.30,) * 20, "1.0.0-fixture", ""), kr
    closed = ref.holiday_set("KRX")[0]
    assert dates == tuple(d.isoformat() for d in (START + timedelta(days=i) for i in range(30))
                          if d.weekday() < 5 and d not in closed)
    assert md5s == tuple((fid, ref.file(fid).md5) for fid in ("holidays_KRX", "kr_regime_tags", "kr_sessions")), md5s
    assert all(re.fullmatch(r"[0-9a-f]{32}", m) for _fid, m in md5s), md5s
    dates, limits, md5s, version, error = us
    assert (len(dates), dates[0], dates[-1]) == (41, "2026-10-26", "2026-12-22") and "2026-11-26" not in dates, us
    assert (limits, md5s, version, error) == ((), (("holidays_NYSE", ref.file("holidays_NYSE").md5),),
                                              "1.0.0-fixture", ""), us
    for d, close in closes.items():
        assert close.astimezone(KST).date() == date.fromisoformat(d) + timedelta(days=1), (d, close)
    assert date(2026, 11, 27) in ref.holiday_set("NYSE")[1] and "2026-11-27" in dates
    assert [closes[d].astimezone(KST).hour for d in ("2026-10-26", "2026-11-02", "2026-11-27")] == [5, 6, 3]
    for market in ("KR", "US"):
        got, ok = late[market], last[market]
        assert got[:4] == ((), (), (), "") and got[4].startswith("coverage: ") and "2028-01-01" in got[4], got
        assert ok[4] == "" and ok[0] and ok[0][-1] <= "2027-12-31", (market, ok)


def test_crypto_sessions_and_a_missing_calendar():
    """Crypto: every date of the half-open horizon, no calendar. A KR or US leg without a set is "unsigned: ..."
    (never core.calendars' default set); any other market is a ValueError."""
    assert inputs.sessions("CRYPTO", START, 3, None) == (("2026-10-24", "2026-10-25", "2026-10-26"), (), (), "", "")
    assert len(inputs.sessions("CRYPTO", START, 366, None)[0]) == 366
    for market in ("KR", "US"):
        assert inputs.sessions(market, START, 30, None) == ((), (), (), "", "unsigned: no signed calendar set")
    _raises(lambda: inputs.sessions("JP", START, 30, None), ValueError)


# --------------------------------------------------------------------------- #
# Provenance (R2-6)
# --------------------------------------------------------------------------- #
def test_provenance_strings_and_versions():
    p = inputs.provenance()
    assert re.fullmatch(r"git:[0-9a-f]{40}", p.repo_anchor) or p.repo_anchor == "UNVERSIONED", p
    assert re.fullmatch(r"[0-9a-f]{64}", p.tree_hash), p
    assert p.cryptography == importlib.metadata.version("cryptography"), p
    saved = importlib.metadata.version

    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)
    importlib.metadata.version = missing
    try:
        assert inputs.provenance().cryptography == "absent"
    finally:
        importlib.metadata.version = saved


def test_the_provenance_copies_equal_the_originals_on_the_repo():
    """R2-6: the copies, their constants and their default root equal the originals', which this test imports and
    core/oddsdata/inputs.py never does."""
    from core.ficc import macro_artifacts as MA
    from core.quant import gate_ledger as GL
    rel = "core/oddsdata/inputs.py"
    targets = {f"{module}.{name}" if name else module for _node, module, names, _f
               in CG._imports(rel, ast.parse((ROOT / rel).read_text(encoding="utf-8"))) for name in names or ("",)}
    assert not [t for t in targets if t.startswith(("core.quant.gate_ledger", "core.ficc.macro_artifacts"))], targets
    assert inputs.UNVERSIONED == GL.UNVERSIONED and inputs.TREE_GLOBS == MA.TREE_GLOBS
    assert inputs.REPO == GL.REPO_ROOT == MA.REPO_ROOT == ROOT
    assert inputs.repo_anchor() == GL.repo_anchor() and inputs.tree_hash() == MA.tree_hash()


def test_the_provenance_copies_equal_the_originals_on_synthetic_roots():
    """No .git, a ref: HEAD (loose, packed-refs only, neither), a detached sha, a non-hex HEAD, an unreadable HEAD;
    a small tree with files inside and outside TREE_GLOBS."""
    from core.ficc import macro_artifacts as MA
    from core.quant import gate_ledger as GL
    root = Path(os.environ["TRADEGEN_HOME"]) / "synthetic_repo"
    git = root / ".git"
    root.mkdir()

    def anchor(want: str) -> None:
        got = inputs.repo_anchor(root)
        assert got == GL.repo_anchor(root) == want, (got, GL.repo_anchor(root), want)
    anchor("UNVERSIONED")
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    anchor("UNVERSIONED")                                           # no loose ref and no packed-refs
    (git / "packed-refs").write_text(f"# pack-refs with: peeled\n{'c' * 40} refs/heads/other\n"
                                     f"{'d' * 40} refs/heads/main\n", encoding="utf-8")
    anchor("git:" + "d" * 40)
    (git / "refs" / "heads" / "main").write_text("a" * 40 + "\n", encoding="utf-8")
    anchor("git:" + "a" * 40)                                       # the loose ref wins
    (git / "HEAD").write_text("b" * 40, encoding="utf-8")
    anchor("git:" + "b" * 40)                                       # detached
    (git / "HEAD").write_text("not a sha\n", encoding="utf-8")
    anchor("UNVERSIONED")
    (git / "HEAD").unlink()
    (git / "HEAD").mkdir()
    anchor("UNVERSIONED")                                           # reading HEAD raises OSError
    (root / "core" / "x").mkdir(parents=True)
    (root / "core" / "x" / "a.py").write_bytes(b"x = 1\r\n")
    (root / "core" / "b.py").write_bytes(b"")
    (root / "data" / "macro" / "sub").mkdir(parents=True)
    (root / "data" / "macro" / "f.yaml").write_bytes(b"k: v\n")
    (root / "data" / "macro" / "sub" / "g.bin").write_bytes(bytes(range(256)))
    (root / "config.py").write_bytes(b"A = 1\n")
    first = inputs.tree_hash(root)
    assert first == MA.tree_hash(root) and re.fullmatch(r"[0-9a-f]{64}", first), first
    (root / "core" / "notes.txt").write_bytes(b"outside the globs")
    (root / "data" / "other.yaml").write_bytes(b"outside the globs")
    assert inputs.tree_hash(root) == MA.tree_hash(root) == first
    (root / "data" / "macro" / "h.yaml").write_bytes(b"inside")
    assert inputs.tree_hash(root) == MA.tree_hash(root) != first
    (root / "empty").mkdir()
    assert inputs.tree_hash(root / "empty") == MA.tree_hash(root / "empty") == hashlib.sha256().hexdigest()


# --------------------------------------------------------------------------- #
# The comparison state (O12, Q12, Q34, Q36)
# --------------------------------------------------------------------------- #
def test_begin_run_numbers_comparisons_and_keeps_each_ones_run():
    """Q12: new comparisons are c000001, c000002, ...; runs grows on every call; an issued id keeps its own run
    counter, so every invocation of it returns the same (id, run counter), the comparison's two inputs to the market
    seed (Q34), while K and J accumulate under it; R counts the comparisons that hold each plan hash."""
    assert inputs.begin_run(None, [H1], []) == ("c000001", 1, 1, 0, {H1: 1})
    assert inputs.begin_run(None, [H2, H1], [0.55]) == ("c000002", 2, 2, 1, {H2: 1, H1: 2})
    first = inputs.begin_run("c000001", [H2], [0.6])
    second = inputs.begin_run("c000001", [H2], [0.6])
    assert first == second == ("c000001", 1, 2, 1, {H2: 2}), (first, second)
    assert inputs.begin_run("c000001", [H3], [0.65]) == ("c000001", 1, 3, 2, {H3: 1})
    path = inputs.state_path()
    raw = path.read_bytes()
    doc = json.loads(raw)
    assert doc == {"schema": "tradegen.odds_state/1", "runs": 5, "comparisons": {
        "c000001": {"run": 1, "plans": [H1, H2, H3], "typed": [0.6, 0.65]},
        "c000002": {"run": 2, "plans": [H1, H2], "typed": [0.55]}}}, doc
    assert raw == (model.canonical_json(doc) + "\n").encode("utf-8") and not path.with_name("state.json.tmp").exists()
    assert inputs.begin_run(None, [H1], []) == ("c000006", 6, 1, 0, {H1: 3})     # a new comparison, a new counter


def test_begin_run_refuses_unknown_and_malformed_ids_writing_nothing():
    path = inputs.state_path()
    _raises(lambda: inputs.begin_run("c000001", [H1], []), ValueError)     # never issued: nothing exists yet
    assert not path.exists() and not path.parent.exists()
    inputs.begin_run(None, [H1], [])
    before = path.read_bytes()
    for comparison, hashes, typed in (("c000002", [H1], []), ("c1", [H1], []), ("C000001", [H1], []),
                                      ("c0000001", [H1], []), ("c000001\n", [H1], []), (1, [H1], []),
                                      (None, ["abc"], []), (None, ["F" * 64], []), (None, [H1], [math.nan]),
                                      (None, [H1], [True]), (None, [H1], ["0.5"]), (None, [H1], [10**400])):
        _raises(lambda: inputs.begin_run(comparison, hashes, typed), ValueError)
        assert path.read_bytes() == before, (comparison, hashes, typed)


def test_begin_run_fails_closed_on_a_bad_state_file():
    """Q36: a state file that does not parse, has another schema, or holds a comparison without its own "run" (the
    earlier layout), with a run past `runs`, or under an id other than c<its run:06d> (after a hand-lowered `runs`, the
    next new id would be one already issued) is RuntimeError, and is never rewritten."""
    path = inputs.state_path()
    path.parent.mkdir(parents=True)
    good = {"schema": inputs.STATE_SCHEMA, "runs": 1, "comparisons": {"c000001": {"run": 1, "plans": [H1],
                                                                                   "typed": []}}}
    bad = [b"not json\n", b"\xff\xfe\n", b"[]\n"]
    for change in ({"schema": "tradegen.odds_state/0"}, {"runs": "1"}, {"runs": True}, {"comparisons": []},
                   {"extra": 1}, {"comparisons": {"c000001": {"plans": [H1], "typed": []}}},
                   {"comparisons": {"c000002": {"run": 2, "plans": [H1], "typed": []}}},
                   {"runs": 2, "comparisons": {"c000003": {"run": 1, "plans": [H1], "typed": []}}},
                   {"comparisons": {"c000001": {"run": 1, "plans": [H2, H1], "typed": []}}},
                   {"comparisons": {"c000001": {"run": 1, "plans": [H1], "typed": [10**400]}}},
                   {"comparisons": {"c1": {"run": 1, "plans": [H1], "typed": []}}}):
        bad.append((model.canonical_json({**good, **change}) + "\n").encode("utf-8"))
    for raw in bad:
        path.write_bytes(raw)
        _raises(lambda: inputs.begin_run(None, [H1], []), RuntimeError)
        assert path.read_bytes() == raw, raw
    path.write_bytes((model.canonical_json(good) + "\n").encode("utf-8"))
    assert inputs.begin_run("c000001", [H2], []) == ("c000001", 1, 2, 0, {H2: 1})    # the control parses


def test_begin_run_writes_through_checked_target():
    """A0: state_path() runs state_root()'s link scan first, on a clean temp home (memoised), so each refusal below
    comes from begin_run's own checked_target calls: a hard-linked state file is never rewritten, and an odds folder
    that became a junction after that scan is never written through."""
    path = inputs.state_path()
    inputs.begin_run(None, [H1], [])
    os.link(path, path.with_name("second_name.json"))
    before = path.read_bytes()
    err = _raises(lambda: inputs.begin_run(None, [H1], []), RuntimeError)
    assert "writing it would change another file" in str(err), err
    assert path.read_bytes() == before
    for name in ("second_name.json", "state.json"):
        path.with_name(name).unlink()
    path.parent.rmdir()
    elsewhere = path.parent.with_name("elsewhere")
    elsewhere.mkdir()
    F.directory_link(path.parent, elsewhere)
    err = _raises(lambda: inputs.begin_run(None, [H1], []), RuntimeError)
    assert "is a symlink or junction" in str(err) and not any(elsewhere.iterdir()), err


def test_build_inputs_fills_every_field():
    plan = _plan()
    series = P.Series(symbol="KRW-BTC", source="UPBIT", dates=("2026-10-22", "2026-10-23"), open=(1.0, 2.0),
                      close=(1.5, 2.5), adjustment="", status="final",
                      md5=P.series_md5("KRW-BTC", "UPBIT", ("2026-10-22", "2026-10-23"), (1.0, 2.0), (1.5, 2.5), "",
                                       "final"))
    info = (("2026-10-26", "2026-10-27"), (0.3, 0.3), (("holidays_KRX", "a" * 32),), "1.0.0-fixture", "")
    run = ("c000003", 2, 3, 1, {P.plan_hash(plan): 2, H3: 1})
    got = inputs.build_inputs(plan, F.NOW, series=series, sessions_info=info, calendar_sha="b" * 64, replay=None,
                              run=run)
    want = {"now": F.NOW, "series": series, "sessions": info[0], "price_limits": info[1], "calendar_sha256": "b" * 64,
            "calendar_version": "1.0.0-fixture", "calendar_md5s": info[2], "calendar_error": "", "replay": None,
            "comparison_id": "c000003", "run_counter": 2, "comparison_plans": 3, "comparison_typed": 1,
            "plan_runs": 2, "provenance": inputs.provenance()}
    assert {f.name for f in dataclasses.fields(P.Inputs)} == set(want)
    assert {name: getattr(got, name) for name in want} == want, got
    _raises(lambda: inputs.build_inputs(plan, F.NOW, series=series, sessions_info=info, calendar_sha="", replay=None,
                                        run=("c000003", 2, 1, 0, {H3: 1})), KeyError)   # R must hold this plan


def test_the_state_path_stays_under_the_tradegen_home():
    """The odds twin of macro_m0_rules.test_every_state_path_stays_out_of_quantgen for state.json."""
    real = Path.home() / ".tradegen"
    existed = (real / "odds").exists()
    saved = os.environ.pop("TRADEGEN_HOME")
    try:
        assert inputs.state_path() == real / "odds" / "state.json"
        assert inputs.state_path().resolve().is_relative_to(real.resolve())
        os.environ["TRADEGEN_HOME"] = str(isolation.QUANTGEN_STATE / "odds_home")
        _raises(inputs.state_path, RuntimeError)
    finally:
        os.environ["TRADEGEN_HOME"] = saved
    assert (real / "odds").exists() == existed
