### Task 16: Calendar, sessions, provenance and the persisted odds state (`core/oddsdata/inputs.py`)

**Files:**
- Create: `core/oddsdata/inputs.py` (LF, UTF-8, no BOM)
- Test: `tests/odds_inputs.py` (create; LF, UTF-8, no BOM)

No existing file is edited, so the DRIFT RULE has nothing to apply here. `tests/odds_acceptance.py` already lists
`odds_inputs` in MODULES (Task 1).

**Interfaces:**
- Consumes:
  - Task 4: `core.compliance.owner.calendar_in_force(now) -> str | None` (the sha256 of the latest calendar approval
    stamped at or before `now`, only with an OK owner state and an intact stored copy; ValueError for a naive or
    out-of-range `now`) and `owner._calendar_approval(now) -> tuple[str, str]` (`("none", "")` when a verified log
    approves no calendar by `now`; tests only); `tests.compliance_fixtures`: `NOW` (2026-10-24 09:00 KST), `TABLES`,
    `pubkey_at(path)`, `owner_key(home)`, `approve(home, key, kind, raw)`, `full_home(home, *, rules_raw=None,
    venues_raw=None, calendar_raw=None, limits=None, cap=None)` (every entry stamped 2026-10-23T00:00:00Z; only
    `calendar_raw` is used here), and the existing `temp_home()`, `shipped_bytes(kind)`.
  - Task 5 (`core.odds.plan`): `Provenance(repo_anchor, tree_hash, cryptography)`, `Inputs` (its 15 fields of
    contract 5.2), `Plan`, `Leg`, `fixed`, `Series`, `series_md5`, `plan_hash(plan) -> str` (64 hex).
  - Task 1: `tests.odds_acceptance._wrap` (hermetic, temp home); `tests.compliance_guards._imports(rel, tree)`.
  - Repo (read-only): `owner.store_dir()` (the approved store; a calendar set is the folder
    `calendar/<sha256>/`); `rules.calendar_sha256(folder)`, `rules.calendar_stream(folder)`, `rules.Invalid`;
    `core.calendars.store.CalendarSet(data_dir)` (`.file(file_id).md5`, `.refusal(file_id)` (loads and caches the
    file or its refusal, never raises on an unsigned file), `.version`, `.holiday_set(set_id)`, `.data_dir`),
    `CalendarUnsigned`, `CalendarCoverageError`; `core.calendars.clocks.sessions_between(market, lo, hi, *, cal)` and
    `decision_time_utc(market, d, *, cal)` (tests); `core.calendars.regime.regime_tags("KR", d, *, cal)`
    (`["price_limit"]`); `core.isolation.checked_target`, `state_root`; `tests.macro_m1_calendars.fixture_set()` (a
    signed temp-dir set, version "1.0.0-fixture", covering 1995-01-01 (NYSE 2006-01-01) to 2027-12-31); the
    originals `core.quant.gate_ledger.repo_anchor`, `UNVERSIONED`, `REPO_ROOT` and
    `core.ficc.macro_artifacts.tree_hash`, `TREE_GLOBS`, `REPO_ROOT` (tests only); `importlib.metadata.version`
    (exempt from the follow-up's DYNAMIC_MODULES ban as `importlib.metadata`).
- Produces (`core/oddsdata/inputs.py`, contract section 12), for Task 18's CLI:
  - `calendar_for(now) -> tuple[CalendarSet | None, str, str]`: `(set, sha, "")` with the files `sessions` reads
    already loaded, or `(None, "", "unsigned: no signed calendar approval")`, or `(None, "", "unsigned: the stored
    calendar set does not hash to its approval")`;
  - `sessions(market, start, horizon_days, cal) -> (dates, limits, md5s, version, error)` for `market` in KR, US,
    CRYPTO (ValueError otherwise); md5s are `(file id, md5)` pairs in file-id order: KR `holidays_KRX`,
    `kr_regime_tags`, `kr_sessions`; US `holidays_NYSE` (contract 12 names the KR files in another order; that order
    is prose only, and Step 4 records the ruling); error "" | "unsigned: ..." | "coverage: ..." (no dates then);
  - `REPO`, `UNVERSIONED`, `TREE_GLOBS`, `repo_anchor(root=REPO) -> str`, `tree_hash(root=REPO) -> str` (the R2-6
    copies), `provenance() -> plan.Provenance`;
  - `STATE_SCHEMA = "tradegen.odds_state/1"`, `CID_RE = r"c[0-9]{6}"`, `state_path() -> Path`, `begin_run(comparison,
    plan_hashes, typed) -> (cid, run_counter, K, J, R)` with `R: dict[str, int]` keyed by every plan hash passed;
  - `build_inputs(plan, now, *, series, sessions_info, calendar_sha, replay, run) -> plan.Inputs`;
  - module-private: `_MD5_FILES`, `_number`, `_hex64`, `_state_ok`, `_read_state`.

**Plan decisions used:** Q6 (CALENDAR_UNSIGNED and CALENDAR_COVERAGE inputs, the US close on Seoul d + 1), Q12 (the
comparison state; a comparison keeps its own run counter), Q19 (consumed), Q22 (half-open horizon, sessions from the
signed calendar, crypto every date), Q34 (the run counter that enters the seed), Q36 (state format, fail closed);
RULINGS O1, O6, O12; RULINGS_ROUND2 R2-6.

Design notes (read before Step 3):
- `calendar_for` takes the set only through the owner log: `owner.calendar_in_force(now)` names the sha (its store
  check hashes the folder once), the set is read only from `owner.store_dir()/calendar/<sha>`, the four files
  `sessions` reads (`_MD5_FILES`, and the manifest with the first of them) are parsed and cached, and only then is
  the folder hashed again with `rules.calendar_sha256`. So `sessions` uses only bytes that hashed to the approved sha:
  a store copy edited before that second hash is refused, and one edited after it is never read. The shipped
  `core/calendars/data` drafts are never read here. One input is not under the calendar sha: `CalendarSet(folder)`
  takes the `calendars` block of the shipped rules store (`data/macro/rules_v2.0.0.json`: the KR Saturday-session
  cut-off date, the close times), which `tree_hash` records and the owner does not sign. That is part of O1's stated
  limit that the session list is computed by unsigned code.
- `sessions` passes `cal=` on every call and returns "unsigned: no signed calendar set" for a KR or US leg without a
  set, so `core.calendars`' default set (the shipped drafts) is never reached; the test patches
  `store.default`, `clocks.default` and `regime.default` (clocks.py and regime.py bind the name at import) to raise.
- The horizon is half-open, `[start, start + horizon_days)`, so `sessions_between` gets `start + horizon_days - 1`
  as its inclusive end. A US session keeps its New York date; the simulator applies the Asia/Seoul close date d + 1
  (Q22), which the test checks against the fixture calendar's own scheduled closes.
- `repo_anchor` and `tree_hash` are copied verbatim (packed-refs branch included) and pinned by equality tests; this
  file imports neither original (Task 1's `test_oddsdata_never_imports_orders_or_the_study`, and an AST check here).
- `begin_run` validates its arguments and the id before it reads or writes, so an unknown or malformed id, a plan
  hash that is not 64 lowercase hex, or a typed rate that is not a finite number raises ValueError with nothing
  written. A new comparison's id and run counter are both the new `runs` value; an issued id keeps its stored `run`,
  so every invocation of it gives the same market seed (Q12, Q34). The state file is checked in full on read: every
  comparison needs its own `run` with `1 <= run <= runs`, an id equal to `c<run:06d>`, and sorted unique plans and
  rates. That makes every stored id and run unique and no larger than `runs`, so the next new id is never one
  already issued (a hand-lowered `runs` would otherwise merge a "new" comparison into an old one under its seed). A
  file of an earlier layout, a damaged one or a hand-edited one is RuntimeError, never rewritten. The write is
  `checked_target` on the odds folder (within `state_root()`, as `owner._write_new` checks its folder: this refuses an
  odds folder that became a junction after `state_root()`'s once-per-process link scan), then on `state.json` and
  `state.json.tmp` within that folder (contract 12), mkdir, the tmp, then `os.replace`. One writer at a time is
  assumed; the `# ponytail:` comment on `begin_run` names the lock to add if runs can ever overlap, and the c999999
  ceiling of the ids.
- `build_inputs` computes `provenance()` itself (about 0.2 s once the tree is in the OS cache), so every report carries
  the anchor, the tree hash and the cryptography version of the run that made it.
- Budget: the two full temp homes (code hash, signatures, the 17-file calendar store) and the first load of the
  calendar store's config dominate; the module takes about 12 s.

- [ ] **Step 1: Write the failing tests**

  Create `tests/odds_inputs.py` (whole file, LF):

```python
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
                                      (None, [H1], [True]), (None, [H1], ["0.5"])):
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
    import _winapi
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
    _winapi.CreateJunction(str(elsewhere), str(path.parent))
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
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_inputs/
```

  Expected: a traceback, then the lines below, where `<repo root>` is the folder the command runs in (only the text
  before the path has to match):

```
FAIL odds_inputs/import ImportError: cannot import name 'inputs' from 'core.oddsdata' (<repo root>\core\oddsdata\__init__.py)

0/1 passed, 1 failed, 0 not run
```

  and exit code 1.

- [ ] **Step 3: Implement**

  Create `core/oddsdata/inputs.py` (whole file, LF):

```python
"""Unsigned inputs of the odds engine besides the bars (spec 4 "Calendars", "Provenance", 7.3 "Seeds"; O1, O6, O12;
R2-6; Q6, Q12, Q22, Q34, Q36).

The calendar set comes only from the owner's approved store, and only when owner.calendar_in_force names it and the
stored copy, with the files sessions() reads already loaded from it, still hashes to that name; the horizon's
sessions and dated KRX price limits are read from that set with `cal=` on every call, never from core.calendars'
default set. The session rules of its `calendars` config block (the KR Saturday-session cut-off, the close times)
come from the shipped rules store, which tree_hash records and the calendar sha does not cover (O1: the session list
is computed by unsigned code). `repo_anchor` and `tree_hash` are copies of core.quant.gate_ledger.repo_anchor and
core.ficc.macro_artifacts.tree_hash (R2-6: this package imports neither; tests/odds_inputs.py pins each copy to its
original). The comparison state lives in state_root()/odds/state.json, written atomically through checked_target; a
file that does not parse fails closed and the owner deletes it."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from core.calendars import clocks, regime
from core.calendars.store import CalendarCoverageError, CalendarSet, CalendarUnsigned
from core.compliance import model, owner, rules
from core.isolation import checked_target, state_root
from core.odds import plan as P

REPO = Path(__file__).resolve().parents[2]
UNVERSIONED = "UNVERSIONED"                                    # == core.quant.gate_ledger.UNVERSIONED
TREE_GLOBS = ("core/**/*.py", "data/macro/**/*", "config.py")  # == core.ficc.macro_artifacts.TREE_GLOBS
STATE_SCHEMA = "tradegen.odds_state/1"
CID_RE = r"c[0-9]{6}"
_MD5_FILES = {"KR": ("holidays_KRX", "kr_regime_tags", "kr_sessions"), "US": ("holidays_NYSE",)}


# --------------------------------------------------------------------------- #
# Calendar and sessions (Q6, Q22)
# --------------------------------------------------------------------------- #
def calendar_for(now: datetime) -> tuple[CalendarSet | None, str, str]:
    """(set, sha, error): the calendar set the owner approved and that is in force at `now`, read from the owner's
    store; (None, "", "unsigned: ...") when there is none or the stored copy no longer hashes to its approval. The
    files sessions() reads are loaded before that hash, so an edit made after it is never read."""
    sha = owner.calendar_in_force(now)
    if sha is None:
        return None, "", "unsigned: no signed calendar approval"
    folder = owner.store_dir() / "calendar" / sha
    cal = CalendarSet(folder)
    try:
        for fid in sorted({f for files in _MD5_FILES.values() for f in files}):
            cal.refusal(fid)                   # loads and caches the file, or its refusal, with the manifest
        intact = rules.calendar_sha256(folder) == sha
    except (OSError, rules.Invalid):
        intact = False
    if not intact:
        return None, "", "unsigned: the stored calendar set does not hash to its approval"
    return cal, sha, ""


def sessions(market: str, start: date, horizon_days: int, cal: CalendarSet | None
             ) -> tuple[tuple[str, ...], tuple[float, ...], tuple[tuple[str, str], ...], str, str]:
    """(dates, KRX price limits, (file id, md5) pairs, calendar version, error) of the half-open horizon
    [start, start + horizon_days). CRYPTO: every date, no calendar. KR and US: the sessions of `cal` (KR with the
    price limit in force on each date); a missing or unsigned set gives "unsigned: ...", a horizon outside its
    coverage "coverage: ...", both with no dates."""
    if market == "CRYPTO":
        return tuple((start + timedelta(days=i)).isoformat() for i in range(horizon_days)), (), (), "", ""
    if market not in _MD5_FILES:
        raise ValueError(f"sessions: market {market!r} is not KR, US or CRYPTO")
    if cal is None:
        return (), (), (), "", "unsigned: no signed calendar set"
    try:
        found = clocks.sessions_between(market, start, start + timedelta(days=horizon_days - 1), cal=cal)
        limits = tuple(float(regime.regime_tags("KR", d, cal=cal)["price_limit"]) for d in found) \
            if market == "KR" else ()
        md5s = tuple((fid, cal.file(fid).md5) for fid in _MD5_FILES[market])
        version = cal.version
    except CalendarUnsigned as exc:
        return (), (), (), "", f"unsigned: {exc}"
    except CalendarCoverageError as exc:
        return (), (), (), "", f"coverage: {exc}"
    return tuple(d.isoformat() for d in found), limits, md5s, version, ""


# --------------------------------------------------------------------------- #
# Provenance (R2-6): copies of gate_ledger.repo_anchor and macro_artifacts.tree_hash
# --------------------------------------------------------------------------- #
def repo_anchor(root: Path = REPO) -> str:
    """`git:<sha>` of HEAD when the folder is a git repository, else UNVERSIONED (copy of gate_ledger's)."""
    head = Path(root) / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
        if text.startswith("ref:"):
            ref = text[4:].strip()
            loose = Path(root) / ".git" / ref
            if loose.is_file():
                text = loose.read_text(encoding="utf-8").strip()
            else:                                   # after `git gc` / `git pack-refs` the ref lives in packed-refs only
                packed = (Path(root) / ".git" / "packed-refs").read_text(encoding="utf-8").splitlines()
                text = next((ln.split()[0] for ln in packed if ln.endswith(" " + ref)), "")
        return f"git:{text}" if re.fullmatch(r"[0-9a-f]{40}", text) else UNVERSIONED
    except OSError:
        return UNVERSIONED


def tree_hash(root: Path = REPO) -> str:
    """sha256 over sorted relative paths + bytes of core/**/*.py, data/macro/**, config.py (macro_artifacts' copy)."""
    root = Path(root)
    files = sorted({p for g in TREE_GLOBS for p in root.glob(g) if p.is_file()},
                   key=lambda p: p.relative_to(root).as_posix())
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def provenance() -> P.Provenance:
    """The repo anchor, the tree hash and the installed cryptography version ("absent" when it is not installed)."""
    try:
        crypto = importlib.metadata.version("cryptography")
    except importlib.metadata.PackageNotFoundError:
        crypto = "absent"
    return P.Provenance(repo_anchor=repo_anchor(), tree_hash=tree_hash(), cryptography=crypto)


# --------------------------------------------------------------------------- #
# The comparison state (Q12, Q34, Q36)
# --------------------------------------------------------------------------- #
def state_path() -> Path:
    return state_root() / "odds" / "state.json"


def _number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _hex64(v) -> bool:
    return isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) is not None


def _state_ok(doc) -> bool:
    """A tradegen.odds_state/1 document: every comparison holds its own run counter (1 <= run <= runs, its id
    c<run:06d>, so ids and runs are unique and a new id is never an issued one), sorted unique plan hashes and sorted
    unique typed rates."""
    if not (isinstance(doc, dict) and set(doc) == {"schema", "runs", "comparisons"} and doc["schema"] == STATE_SCHEMA
            and isinstance(doc["runs"], int) and not isinstance(doc["runs"], bool) and doc["runs"] >= 0
            and isinstance(doc["comparisons"], dict)):
        return False
    for cid, comp in doc["comparisons"].items():
        if not (re.fullmatch(CID_RE, cid) and isinstance(comp, dict) and set(comp) == {"run", "plans", "typed"}
                and isinstance(comp["run"], int) and not isinstance(comp["run"], bool)
                and 1 <= comp["run"] <= doc["runs"] and cid == f"c{comp['run']:06d}"
                and isinstance(comp["plans"], list)
                and all(_hex64(h) for h in comp["plans"]) and comp["plans"] == sorted(set(comp["plans"]))
                and isinstance(comp["typed"], list) and all(_number(p) for p in comp["typed"])
                and comp["typed"] == sorted(set(comp["typed"]))):
            return False
    return True


def _read_state(path: Path) -> dict:
    if not path.exists():
        return {"schema": STATE_SCHEMA, "runs": 0, "comparisons": {}}
    try:
        doc = json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        doc = None
    if not _state_ok(doc):
        raise RuntimeError(f"odds state {path}: not a {STATE_SCHEMA} file; the owner deletes it before the next run")
    return doc


def begin_run(comparison: str | None, plan_hashes: list[str], typed: list[float]
              ) -> tuple[str, int, int, int, dict[str, int]]:
    """Opens one run: a new comparison (comparison None, id c<runs:06d>, its run counter fixed at creation) or an
    issued one (its own counter reused, so every invocation of it gets the same seed). Adds the plan hashes and typed
    win rates, writes the state atomically, and returns (id, run counter, K plans, J typed rates, R per plan hash:
    the number of comparisons whose plans hold it). ValueError, writing nothing, for an id that is malformed or was
    never issued, or a plan hash or rate that is not one."""
    # ponytail: one writer at a time. Two overlapping runs read the same `runs`, issue the same new id and counter
    # (one seed), and the later os.replace drops the other's plans; take an exclusive state.lock (open "x" after
    # checked_target) if runs can ever overlap. Ids stop at c999999: run 1,000,000 writes c1000000, which the next
    # read refuses; widen CID_RE before that.
    if comparison is not None and not (isinstance(comparison, str) and re.fullmatch(CID_RE, comparison)):
        raise ValueError(f"comparison id {comparison!r} is not c followed by six digits")
    if not all(_hex64(h) for h in plan_hashes) or not all(_number(p) for p in typed):
        raise ValueError("begin_run: plan hashes are 64 hex characters and typed rates finite numbers")
    path = state_path()
    state = _read_state(path)
    comps = state["comparisons"]
    if comparison is not None and comparison not in comps:
        raise ValueError(f"comparison {comparison} was never issued; leave --comparison out to start a new one")
    state["runs"] += 1
    cid = comparison or f"c{state['runs']:06d}"
    comp = comps.setdefault(cid, {"run": state["runs"], "plans": [], "typed": []})
    comp["plans"] = sorted(set(comp["plans"]) | set(plan_hashes))
    comp["typed"] = sorted(set(comp["typed"]) | {float(p) for p in typed})
    base = path.parent
    checked_target(base, "odds folder", within=state_root())     # a junction made after state_root()'s scan (A0)
    target = checked_target(path, "odds state", within=base)
    tmp = checked_target(base / "state.json.tmp", "odds state tmp", within=base)
    base.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes((model.canonical_json(state) + "\n").encode("utf-8"))
    os.replace(tmp, target)
    seen = {h: sum(h in c["plans"] for c in comps.values()) for h in plan_hashes}
    return cid, comp["run"], len(comp["plans"]), len(comp["typed"]), seen


def build_inputs(plan, now: datetime, *, series, sessions_info, calendar_sha: str, replay, run) -> P.Inputs:
    """plan.Inputs from the pieces: `sessions_info` is the 5-tuple of sessions(), `run` the 5-tuple of begin_run()."""
    dates, limits, md5s, version, error = sessions_info
    cid, counter, k, j, seen = run
    return P.Inputs(now=now, series=series, sessions=dates, price_limits=limits, calendar_sha256=calendar_sha,
                    calendar_version=version, calendar_md5s=md5s, calendar_error=error, replay=replay,
                    comparison_id=cid, run_counter=counter, comparison_plans=k, comparison_typed=j,
                    plan_runs=seen[P.plan_hash(plan)], provenance=provenance())
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_inputs/
```

  Expected: 12 `PASS odds_inputs/test_...` lines, then `12/12 passed, 0 failed, 0 not run` (exit code 0), in about
  12 s (`test_the_approved_fixture_set_gives_sessions_limits_and_md5s` about 6 s, the calendar_for test about 4 s).
  No test may be NOT_RUN: cryptography 49.0.0 is installed, so every signed temp home builds.

  Overlap check, then the bars tests again (the two modules share the wrapper and the temp-home helpers):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_bars/
```

  Expected, ending: `25/25 passed, 0 failed, 0 not run` (exit code 0), the count Task 15 recorded under "Runs".

  Overlap check, then the odds guards, which now scan `core/oddsdata/inputs.py` (raw words, the oddsdata import bans
  with `core.quant.gate_ledger` and `core.ficc.macro_artifacts` among them, dynamic imports with `importlib.metadata`
  exempt, the clock only in `run.py`'s `main()`, every write after `checked_target`):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected: no FAIL line, and the same tail Task 1 recorded under "Runs" in the execution ledger (exit code 0). A
  failure names the offending file and text: fix `inputs.py`, never the guard.

  Overlap check, then the compliance guards (their core-wide raw-word scan, `CORE_RAW_CI`, covers every file of
  `core/`):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Expected: no FAIL line and the tail Task 15 recorded under "Runs" (exit code 0).

  Overlap check, then the core-wide scans, one at a time with the overlap check before each:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
```

  Expected: each prints no FAIL line and ends with `0 failed` and exit code 0, with the counts Task 15 recorded.

  Overlap check, then the cockpit suite and the restore of the tracked results file:

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: the run ends with `0 failed` and the counts Task 15 recorded (exit code 0).

  Then (git only; no overlap check needed):

```bash
git status --short
```

  Expected: exactly `?? core/oddsdata/inputs.py`, `?? tests/odds_inputs.py` and
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`. Append the tails of these runs, one line
  each, under "Runs" in the execution ledger (LF; it stays untracked), and this one line under "Drift rulings":
  `Task 16: calendar_md5s are in file-id order (holidays_KRX, kr_regime_tags, kr_sessions); contract 12's order is prose only.`

- [ ] **Step 5: Commit**

```bash
git add core/oddsdata/inputs.py tests/odds_inputs.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are LF). Then:

```bash
git commit -m "feat(odds): calendar from the owner's store, sessions, provenance copies and the comparison state" -m "Task 16: core/oddsdata/inputs.py (calendar_for, sessions with dated KRX limits, the R2-6 repo_anchor and tree_hash copies, begin_run, build_inputs) and tests/odds_inputs.py." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
