### Task 4: Compliance helpers for the odds engine (`calendar_in_force`, `grey_rows`, signed-home fixtures)

**Files:**
- Modify: `core/compliance/owner.py` (LF, kept; a D14 closure file). Anchor: `_context`, the last function of the
  file, its closing `return model.seal_context(...)` statement; the two new functions go after it, below
  `_owner_now` and `load_context`, whose checks they reuse (Edit O1).
- Modify: `core/compliance/rules.py` (LF, kept; a D14 closure file). Anchor: `_calendar_line(ctx, root, moment)`,
  from its def line through its "missing or altered in the store" return (Edit R1).
- Modify: `core/compliance/gate.py` (LF, kept; a D14 closure file). Anchor: `_screening(d, flags, window)`, the last
  function of the file, its closing `return model.Screening(...)` statement (Edit G2).
- Modify: `tests/compliance_fixtures.py` (LF, kept). Anchor: `store_blob`, the last function of the file, its last
  three lines (Edit F1).
- Modify: `tests/compliance_store.py` (LF, kept). Anchors: the last two lines of the module's import block with the
  constants `ROOT` and `TABLES` below them (Edit S2); the "load_context (spec 6.4, 8.2; P19, P24)" section, from
  `NOW = ...` through the `return key` of `_full_home` (Edit S3); `test_decision_date_is_the_asia_seoul_date_of_now`,
  the last test of the file, its closing `with` block (Edit S1).
- Modify: `tests/compliance_gate.py` (LF, kept). Anchor: `test_gate_call_graph_has_no_clock_zone_file_or_socket`,
  the last test of the file, its closing `for module, scan in scans.items():` loop (Edit G1).
- Unchanged: `tests/compliance_cli.py` (its calendar-line tests build their own signed homes and need no import
  fix); its tests are run in Step 4. CONTRACT section 0 lists "Task 4, only for an import fix" for this file; none is
  needed: it imports the fixtures as `fx` (compliance_cli.py:24) and builds its own signed homes (`_write_home`,
  `_signed_home`, :53-89), so the new public fixture names collide with nothing.
- Test: `tests/compliance_store.py`, `tests/compliance_gate.py`

**Interfaces:**
- Consumes (all as of `5816d3c`; the follow-up renames none of them):
  - `core.compliance.owner`: `_owner_now(day: date, now_utc: str, session_id: str | None) -> tuple[model.OwnerState,
    LogCheck | None]` (BROKEN with `None` for a missing cryptography package, no key, an unreadable key, log, alerts
    or anchor file; else the `owner_state` of the verified log, KEY CHANGED included);
    `_up_to(check, now_utc) -> LogCheck`; `in_force(check) -> dict[str, tuple[str, int]]`;
    `store_get(kind, sha256) -> bytes | None` (for `calendar`, `rules.calendar_stream` of the stored folder, None
    when missing, holding a link or not hashing to its name); `home()` (`<state root>/compliance`), `store_dir()`,
    `log_path()`, `alerts_path()`, `PUBKEY_PATH`, `GENESIS_PREV`, `REPO_ROOT`, `code_files`, `code_hash`,
    `load_context`; the module imports `datetime as _dt` and `from core.compliance import model, rules`
    (owner.py:430-433), so the new code adds no import.
  - `core.compliance.model`: `iso_utc(moment) -> str` (ValueError on a naive one), `KST`, `sha256_hex`,
    `canonical_json`, `Positions`, `OwnerState.broken(reason)`, `ApprovedState.invalid(reason)`, `Context`,
    `is_sealed(ctx)`, `Intent` (financing defaults to `"cash"`). `model.py` imports only the stdlib at run time.
  - `core.compliance.gate` privates, reused unchanged: `_usable(state)`, `_is(value, members)`,
    `_lookup(state, venue, symbol, exits)`, `_in_force(state, intent, cls, on)`; `rules.VENUES`,
    `Venue.quote_for(inst)`.
  - `core.compliance.rules`: `calendar_stream(data_dir) -> bytes`, `calendar_sha256(data_dir) -> str`, `Invalid`.
  - `tests/compliance_fixtures.py`: `temp_home()` (a `tempfile.mkdtemp` dir, so inside `tempfile.gettempdir()`),
    `shipped_bytes(kind)`, `approved(...)`, `ctx(**overrides)`, `test_key()`,
    `signed_entry(key, seq, prev_sha256, kind, data, utc=...)` (unsigned when `key` is None),
    `write_pubkey(path, key=None)`, `store_blob(home, kind, raw, anchor)`; its top-level imports `contextlib`,
    `tempfile` and `pathlib.Path`.
  - `tests/compliance_store.py`: `ROOT`, `_raises(fn, exc)`, `F`; `tests/compliance_gate.py`: `_T8_DAY`,
    `_t8_row(row_id, state=None)`, `_t8_with_rows(state, changes)`, `_t9_plan(venue, symbol, start, horizon_days)`,
    `_t9_types` (the `types` module); `tests.macro_m1_calendars.fixture_set()` (a signed temp-dir `CalendarSet`
    whose `.data_dir` holds only regular files), imported inside the helper that needs it, as
    `tests/compliance_tables.py` does.
- Produces (Tasks 13, 16 and 18 and the E1 plan rely on these exact names):
  - `core.compliance.owner._calendar_approval(now: _dt.datetime) -> tuple[str, str]`: `("log", "")` when the owner
    state at `now` is not OK (no key, cryptography missing, an unreadable or broken log, KEY CHANGED) or on any
    internal error; `("none", "")` when no `approved {kind: calendar}` is stamped at or before `now`;
    `("store", sha)` when that approval's stored copy is missing or altered; `("ok", sha)` otherwise. ValueError for
    a non-datetime, naive or out-of-range `now`.
  - `core.compliance.owner.calendar_in_force(now: _dt.datetime) -> str | None`: the sha exactly when
    `_calendar_approval(now) == ("ok", sha)`, else None; the same ValueError.
  - `core.compliance.rules._calendar_line(ctx, root, moment)` keeps its signature and its four lines, now mapped from
    `owner._calendar_approval(moment)`.
  - `core.compliance.gate.grey_rows(plan, ctx) -> tuple[str, ...]`: pure, never raises.
  - In `tests/compliance_fixtures.py`, public: `TABLES`, `NOW` (2026-10-24 09:00 KST), `HELD`,
    `pubkey_at(path: Path)`, `owner_key(home: Path)` (AssertionError, before the pem is written, unless
    `owner.PUBKEY_PATH` lies inside both `home` and `tempfile.gettempdir()`),
    `sign(key, kind: str, data: dict, utc: str = "2026-10-23T00:00:00Z") -> tuple[int, str]` (AssertionError,
    before the owner log is read or written, when `owner.log_path()` is not inside `tempfile.gettempdir()`),
    `approve(home: Path, key, kind: str, raw: bytes) -> str` (AssertionError, before anything is written, when
    `owner.home()` is not inside `home`), `other_code(key, utc: str = "2026-10-23T00:00:00Z")`,
    `full_home(home: Path, *, rules_raw=None, venues_raw=None, calendar_raw=None, limits=None, cap=None)` (returns
    the key). Odds tests write `F.full_home(home, venues_raw=OF.ODDS_VENUES, limits={...}, cap=0.10)` (Task 18) and
    `F.full_home(home, calendar_raw=...)` (Task 16).
  - In `tests/compliance_store.py`: the bindings `_pubkey_at`, `_owner_key`, `_sign`, `_approve`, `_other_code`,
    `_full_home` (to the fixtures above), the helpers `_calendar_now(now)` and `_fixture_calendar()`, and the tests
    `test_signed_home_helpers_are_the_public_fixtures`, `test_full_home_signs_the_odds_keywords`,
    `test_calendar_in_force_is_the_sha_of_the_intact_signed_copy`,
    `test_calendar_in_force_is_none_without_an_ok_owner_log`,
    `test_calendar_in_force_counts_only_approvals_stamped_by_now`,
    `test_calendar_in_force_refuses_a_naive_or_out_of_range_now`,
    `test_calendar_line_maps_the_shared_calendar_approval`.
  - In `tests/compliance_gate.py`: the class `_T10Unreadable` and the tests
    `test_grey_rows_names_the_in_force_grey_rows_of_the_leg` and
    `test_grey_rows_is_empty_when_nothing_can_be_looked_up`.

**Plan decisions used:** Q3 (compliance-side prerequisites first, O3), Q19 (`calendar_in_force` and the shared
`_calendar_approval`, a recorded departure from O3's wording), Q20 (`grey_rows`), Q21 (the signed-home fixtures),
Q6 (O6: a KRX or US leg needs the signed calendar sha); RULINGS_ROUND2 R2-13 (the DRIFT RULE for `owner.py`,
`rules.py` and `tests/compliance_store.py`). Departure from CONTRACT 3.3 ("moved verbatim"; tests only, stricter):
`sign` and `approve` gain the temp-home guards, `owner_key` the temp-dir check, and the moved docstrings say so.

What this task does and why:
- The odds core may reach the disk only through `owner.calendar_in_force` (O1, O6). Spec 6.3 refuses a KRX or US plan
  without a signed calendar, and spec 4 "Calendars" checks the calendar set's hash. Today only `rules._calendar_line`
  (the `--check` line) reads the calendar approval, and it gives four lines, not a sha. After this task
  `owner._calendar_approval(now)` holds that reading, checked the way `load_context` checks the tables: the owner
  state at `now` via `_owner_now`, the approvals stamped by `now` via `_up_to` and `in_force`, the stored copy via
  `store_get`. `calendar_in_force(now)` keeps only its `"ok"` outcome. `_calendar_line` keeps its four exact lines
  by mapping the four outcomes. Q19 records this departure from O3's wording ("refactor `_calendar_line` to call
  it"): the line needs four outcomes and `calendar_in_force` returns two. A test pins, on every calendar case below,
  that `calendar_in_force(now)` is the sha exactly when `_calendar_approval(now)` is `("ok", sha)`.
- `calendar_in_force` is stricter than the old line on one point. It checks the whole owner state, KEY CHANGED
  included, where the old line verified the log alone. `_calendar_line` still asks `ctx.owner.ok` first, so every
  `--check` line stays exactly as it was.
- Spec 7.5 puts each grey leg's warning on the card (O3: "so GREY_LEG never needs gate privates").
  `gate.grey_rows(plan, ctx)` returns the in-force grey row ids of the leg, decided as the cash buy `screen` builds.
  It adds no import to `gate.py`, uses none of the `_T9_FORBIDDEN` names, and its docstring and comments never say
  `datetime` or `ZoneInfo`. So `test_gate_call_graph_has_no_clock_zone_file_or_socket`, which scans the whole gate
  source and its imports, covers it unchanged, and so does `test_purity_no_file_clock_zone_or_network`. In the
  shipped table the only grey row is `KR-OKX-SPOT` (in force from 2026-01-15 up to 2027-02-18; its `auto_off`
  2026-12-03 blocks new exposure but does not end it), so an OKX leg gives `("KR-OKX-SPOT",)` and every other venue
  `()`.
- The odds suite needs full signed temp homes, as `compliance_store` already builds them. The helpers move verbatim
  into `tests/compliance_fixtures.py`, renamed public (Q21), with four new keywords: `venues_raw` (approved instead of
  the shipped venues), `calendar_raw` (a `rules.calendar_stream` blob, approved as kind `calendar`), `limits`
  (a `limit_set`) and `cap` (a `cap_set` of `okx_equity_share`). The new entries come after the old ones, and every
  entry is stamped `2026-10-23T00:00:00Z`, so a limit or cap counts from NOW's date 2026-10-24 (D12). With no keyword,
  the log holds exactly what it held before. `compliance_store` imports `HELD`, `NOW` and `TABLES` back and binds its
  old private names, so no existing test body changes.
- Once public, the helpers are shared by Tasks 13, 16 and 18 and the E1 plan, so the moved copy gets three guards
  (hard rules: never write the real `~/.tradegen/compliance/owner.jsonl`, and never write the repo's trust anchor
  `core/compliance/owner_pubkey.pem` with the test key, whose seed, bytes 0..31, is public). `owner_key`, which
  writes the pem, refuses an `owner.PUBKEY_PATH` that is not inside both `home` and `tempfile.gettempdir()`. The old
  check, inside `home` only, let the caller's choice of `home` decide: `full_home(Path.home())` with `pubkey_at`
  forgotten passed it and wrote the anchor (the repo lies under `Path.home()`), and the rest of the home was then
  signed with no refusal, since a temp `TRADEGEN_HOME` also lies under `Path.home()`. The repo is never inside the
  temp dir, so that call is now refused before the pem is written. `sign`, which every log write goes through,
  refuses a log path that is not inside `tempfile.gettempdir()` before it reads or writes the log. With
  `TRADEGEN_HOME` unset (a direct call outside the harness), `owner.log_path()` is under the real `~/.tradegen`
  (core/isolation.py:108), so it is refused; `owner.log_path()` itself still walks the state root for links first
  (`scan_links`, read only). `approve` refuses a state root that is not inside its `home` before signing, so a
  mismatched home writes no log at all (`store_blob` checks only after `sign` has written). `full_home` adds no
  guard of its own, because each of its writes goes through one of these: the pem through `owner_key`, every log
  line through `sign`, every stored blob through `approve` and `store_blob`. `owner` is imported inside each helper,
  as `store_blob` does, so `temp_home`, which every wrapped compliance and odds test imports, never depends on
  `owner.py` or `rules.py` importing cleanly. `model` (stdlib only) and `json` stay at module level, because `NOW`
  and `HELD` need `model`. `test_signed_home_helpers_are_the_public_fixtures` pins the three guards safely: the
  mismatched home is a second temp home, and the `owner_key` and `sign` cases point `tempfile.tempdir` elsewhere
  with the pem and the log inside a temp home, so even a missing guard writes only inside a temp home. (The
  ancestor-home case itself is not run as a test: with the guard missing it would write the repo's anchor.)
- Code hash: `owner.py`, `rules.py` and `gate.py` are D14 closure files, so the code hash moves. No `code_approved`
  exists yet (owner act 2 is not done), so nothing is re-signed now. Once the owner signs, any later change to them
  needs a fresh signature. No import is added to any closure file, so the closure's file set is unchanged.
- Drift (R2-13): the follow-up changes `owner.py` (`_guards` is new and `_skipped`, `_import_nodes` and
  `_repo_imports` change, all above the anchor `_context`, whose text it leaves alone). It changes `rules.py` (`_row`
  and the constants above `_match`; `_calendar_line` is untouched and only moves down). It changes
  `tests/compliance_store.py`: `import ast` goes in above `import contextlib`, and
  `test_code_files_counts_lazy_imports_and_skips_main_and_type_checking` changes, so the signed-home helpers move down
  about 43 lines, `_pubkey_at` from 247 to about 290. It does not change `gate.py`, `tests/compliance_fixtures.py`,
  `tests/compliance_gate.py` or the end of `tests/compliance_store.py`. Re-read each file before each Edit. If an old
  text differs only because an earlier plan changed it, make the same change to the current text, keep the earlier
  plan's behaviour, and add one line under "Drift rulings" in the execution ledger. If the change no longer makes
  sense, stop and rule. Edit S3's helpers are moved from the merged file: if the follow-up changed anything inside
  `NOW` .. `_full_home` (it does not plan to), Edit F1 carries that change into the moved copy.
- Checked in a sandbox on 2026-10-27 (`.venv/Scripts/python.exe -I -B`, on a `git archive` copy of the `5816d3c`
  tree, before the follow-up). Each Edit's old text occurs exactly once, and every new line is ASCII and at most
  120 characters. After Step 1, Step 2's nine FAIL lines appear word for word. After Step 3: `compliance_store`
  36/36, `compliance_gate` 51/51, `compliance_cli` 35/35 (36 once the follow-up adds its test), `compliance_owner`
  52/52, `compliance_model` 10/10, `compliance_loader` 15/15, and every compliance guard that scans core files
  passes. The new signed-home tests take about 1 to 25 s each on the reference machine:
  `test_full_home_signs_the_odds_keywords`, with two full homes, two `load_context` calls and the process's first
  `fixture_set()` (about 4.5 s), is the slowest (8 s on an idle machine, 25 s under load), and the other calendar
  tests take up to about 10 s, so `compliance_store/` grows by up to about one minute. Every `full_home` and every
  `load_context` hashes the code (about 2.5 to 4 s). Re-run in `sandbox_revise4` with a fake user home: `sign`
  refuses the log under an unset `TRADEGEN_HOME`, `full_home` refuses a `TRADEGEN_HOME` that is not its `home`
  before any log line is written, and `test_signed_home_helpers_are_the_public_fixtures` and
  `test_full_home_signs_the_odds_keywords` pass. With `approve`'s guard removed the first test fails on its no-log
  assert, and with `sign`'s removed on `AssertionError not raised`. Re-run on 2026-10-28 (`sandbox_revise4/r3`, the
  same tree, fake user home): Step 2's nine FAIL lines are unchanged; after Step 3 `compliance_store` 36/36,
  `compliance_gate` 51/51 and the three calendar-line `compliance_cli` tests pass; `full_home(<an ancestor of the
  tree>)` with `pubkey_at` forgotten is refused by `owner_key` and writes no trust anchor. Each of these mutants
  fails its test: `owner_key` checking `home` only, a `limit_set` stamped 2026-10-22, an unsorted `grey_rows`, and
  `grey_rows` looking the symbol up with `exits=True`.
- Covers spec 8, odds item 6 (CALENDAR_UNSIGNED groundwork: files without a signed owner approval). RULINGS: O3
  (`calendar_in_force`, `grey_rows`, fixtures), O6 (the signed calendar sha); R2-13.

- [ ] **Step 1: Write the failing tests**

  Two Edit-tool replacements, both in LF files. Re-read each file first (DRIFT RULE).

  **Edit S1**, `tests/compliance_store.py`. Anchor: `test_decision_date_is_the_asia_seoul_date_of_now`, the last test
  of the file, its closing `with` block (the last four lines of the file at `5816d3c`). The new section goes after it,
  at the end of the file. Old text (exact):

```python
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        for before, after in pairs:
            assert owner.load_context(before, HELD).date == _dt.date(2026, 12, 2), before
            assert owner.load_context(after, HELD).date == _dt.date(2026, 12, 3), after
```

  New text:

```python
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        for before, after in pairs:
            assert owner.load_context(before, HELD).date == _dt.date(2026, 12, 2), before
            assert owner.load_context(after, HELD).date == _dt.date(2026, 12, 3), after


# --------------------------------------------------------------------------- #
# Odds plan Task 4 (Q19, Q21): calendar_in_force and the _calendar_approval it shares with the --check line, and the
# signed-home helpers as public fixtures. Every calendar case also checks that calendar_in_force(now) is the sha
# exactly when _calendar_approval(now) is ("ok", sha) (Q19).
# --------------------------------------------------------------------------- #
def _calendar_now(now: _dt.datetime) -> tuple[str, str]:
    """owner._calendar_approval(now), once calendar_in_force(now) is checked to agree with it (Q19)."""
    found = owner._calendar_approval(now)
    assert owner.calendar_in_force(now) == (found[1] if found[0] == "ok" else None), found
    return found


def _fixture_calendar() -> bytes:
    """The calendar stream of the signed temp-dir fixture set; imported here, as tests/compliance_tables.py does, so
    a broken macro module fails only the tests that need it."""
    from tests.macro_m1_calendars import fixture_set
    return rules.calendar_stream(fixture_set().data_dir)


def test_signed_home_helpers_are_the_public_fixtures():
    """Q21: the signed-home helpers live in tests/compliance_fixtures.py and this module's old names are bound to
    them, so these tests run the code the odds suite runs. They write only inside the temp home: approve refuses a
    state root other than its `home`, owner_key a pem and sign an owner log outside the temp dir (so never the
    repo's trust anchor or the real ~/.tradegen), each before writing. Every case stays inside temp homes even if a
    guard were missing."""
    import tempfile
    pairs = ((_pubkey_at, F.pubkey_at), (_owner_key, F.owner_key), (_sign, F.sign), (_approve, F.approve),
             (_other_code, F.other_code), (_full_home, F.full_home), (NOW, F.NOW), (HELD, F.HELD),
             (TABLES, F.TABLES))
    assert all(mine is theirs for mine, theirs in pairs), [mine for mine, theirs in pairs if mine is not theirs]
    assert TABLES == ("rules", "instruments", "venues") and NOW == _dt.datetime(2026, 10, 24, 9, 0, tzinfo=model.KST)
    assert HELD == model.Positions(equity_krw=1_000_000.0, holdings={("upbit", "BTC"): 0.01})
    with F.temp_home() as home, F.temp_home():                          # the state root is another temp home
        _raises(lambda: _approve(home, None, "rules", b"x"), AssertionError)
        assert not owner.home().exists() and not (home / "compliance").exists()
    with F.temp_home() as home, _pubkey_at(home / "k.pem"):
        saved, tempfile.tempdir = tempfile.tempdir, str(home / "elsewhere")  # the pem and the log are outside it
        try:
            _raises(lambda: _owner_key(home), AssertionError)
            _raises(lambda: _sign(None, "approved", {}), AssertionError)
        finally:
            tempfile.tempdir = saved
        assert not (home / "k.pem").exists() and not owner.log_path().exists()


def test_full_home_signs_the_odds_keywords():
    """Q21: full_home approves `venues_raw` instead of the shipped venues and `calendar_raw` as kind calendar, and
    signs `limits` as limit_set and `cap` as cap_set, after the entries it always signed. All are stamped
    2026-10-23T00:00:00Z, so the limits and the cap count from NOW's date on (D12). Without them the log is the
    same as before."""
    venues = F.shipped_bytes("venues") + b"\n# a signed venues version for the odds suite\n"
    stream = _fixture_calendar()
    limits = {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home, venues_raw=venues, calendar_raw=stream, limits=limits, cap=0.10)
        ctx = owner.load_context(NOW, HELD)
        assert ctx.owner.ok and ctx.active.valid and ctx.code_signed, (ctx.owner.reason, ctx.active.reason)
        assert ctx.active.hashes["venues"] == model.sha256_hex(venues) != model.sha256_hex(F.shipped_bytes("venues"))
        assert dict(ctx.owner.limits) == limits and dict(ctx.owner.caps) == {"okx_equity_share": 0.10}, ctx.owner
        assert _calendar_now(NOW) == ("ok", model.sha256_hex(stream))
        kinds = [json.loads(line)["kind"] for line in owner.log_path().read_bytes().splitlines()]
        assert kinds == ["approved"] * 3 + ["code_approved", "age_of_majority", "approved", "limit_set", "cap_set"]
        assert {json.loads(line)["utc"] for line in owner.log_path().read_bytes().splitlines()} == \
            {"2026-10-23T00:00:00Z"}
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home)
        ctx = owner.load_context(NOW, HELD)
        kinds = [json.loads(line)["kind"] for line in owner.log_path().read_bytes().splitlines()]
        assert kinds == ["approved"] * 3 + ["code_approved", "age_of_majority"], kinds
        assert dict(ctx.owner.limits) == {} and dict(ctx.owner.caps) == {}, ctx.owner
        assert ctx.active.hashes["venues"] == model.sha256_hex(F.shipped_bytes("venues"))
        assert _calendar_now(NOW) == ("none", "")


def test_calendar_in_force_is_the_sha_of_the_intact_signed_copy():
    """Q19, O6: under an OK owner state the latest calendar approval stamped by `now` is in force while its stored
    copy is intact. The stored folder is the set itself; one changed or missing file there makes it
    ("store", sha), so None."""
    stream = _fixture_calendar()
    sha = model.sha256_hex(stream)
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home, calendar_raw=stream)
        assert _calendar_now(NOW) == ("ok", sha) and owner.calendar_in_force(NOW) == sha
        assert _calendar_now(_dt.datetime(2026, 10, 24, 0, 0, tzinfo=_dt.timezone.utc)) == ("ok", sha)   # NOW in UTC
        stored = owner.store_dir() / "calendar" / sha
        assert rules.calendar_sha256(stored) == sha and rules.calendar_stream(stored) == stream
        first = sorted(stored.iterdir())[0]
        first.write_bytes(first.read_bytes() + b"# altered\n")
        assert _calendar_now(NOW) == ("store", sha) and owner.calendar_in_force(NOW) is None
        first.unlink()
        assert _calendar_now(NOW) == ("store", sha)


def test_calendar_in_force_is_none_without_an_ok_owner_log():
    """Q19: no owner key, an internal error, a changed key or a broken log give ("log", ""), so None, even with a
    calendar approval in the log."""
    stream = _fixture_calendar()
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        assert _calendar_now(NOW) == ("log", "")                     # before owner act 1 there is no key at all
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home, calendar_raw=stream)
        assert _calendar_now(NOW) == ("ok", model.sha256_hex(stream))

        def boom(*args):
            raise RuntimeError("an internal error")

        saved, owner._owner_now = owner._owner_now, boom
        try:
            assert _calendar_now(NOW) == ("log", "")                 # any error but the ValueError fails closed
        finally:
            owner._owner_now = saved
        row = {"utc": "2026-10-20T00:00:00Z", "channel": "toast", "result": "ok", "code": 3, "due": [],
               "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": "SHA256:" + "e" * 64}
        owner.alerts_path().write_bytes(model.canonical_json(row).encode("utf-8") + b"\n")
        assert owner.load_context(NOW, HELD).owner.reason == "KEY CHANGED since 2026-10-20"
        assert _calendar_now(NOW) == ("log", "")
        owner.alerts_path().unlink()
        assert _calendar_now(NOW)[0] == "ok"
        with open(owner.log_path(), "ab") as fh:
            fh.write(b'{"seq": 99}\n')
        assert not owner.load_context(NOW, HELD).owner.ok and _calendar_now(NOW) == ("log", "")


def test_calendar_in_force_counts_only_approvals_stamped_by_now():
    """Q19: with no calendar approval it is ("none", ""); one stamped after `now` counts only from its stamp on
    (load_context's cut-off, _up_to); the latest approval in log order among those stamped by `now` wins."""
    stream = _fixture_calendar()
    sha = model.sha256_hex(stream)
    other = b"holidays_KRX.yaml\0x: 1\n\0"                              # a one-file calendar set
    after = _dt.datetime(2026, 10, 25, 9, 0, tzinfo=model.KST)          # 2026-10-25T00:00:00Z
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        key = _full_home(home)
        assert _calendar_now(NOW) == ("none", "") and _calendar_now(after) == ("none", "")
        F.store_blob(home, "calendar", stream,
                     _sign(key, "approved", {"kind": "calendar", "sha256": sha}, "2026-10-25T00:00:00Z"))
        assert _calendar_now(NOW) == ("none", "") and _calendar_now(after) == ("ok", sha)
        newer = _approve(home, key, "calendar", other)                  # later in the log, stamped 2026-10-23
        assert _calendar_now(NOW) == ("ok", newer) and _calendar_now(after) == ("ok", newer)
        assert newer == model.sha256_hex(other) != sha


def test_calendar_in_force_refuses_a_naive_or_out_of_range_now():
    """Q19: a naive `now`, a non-datetime, or one that cannot be converted to UTC or Asia/Seoul is ValueError from
    calendar_in_force and _calendar_approval alike (load_context's checks); nothing else raises."""
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        for now in (_dt.datetime(2026, 10, 24, 9, 0), "2026-10-24", _dt.date(2026, 10, 24), None,
                    _dt.datetime(1, 1, 1, tzinfo=model.KST),
                    _dt.datetime(9999, 12, 31, 23, 59, tzinfo=_dt.timezone.utc)):
            _raises(lambda: owner.calendar_in_force(now), ValueError)
            _raises(lambda: owner._calendar_approval(now), ValueError)
        assert owner.calendar_in_force(NOW) is None


def test_calendar_line_maps_the_shared_calendar_approval():
    """Q19: rules._calendar_line (the --check line) reads owner._calendar_approval at the check's moment and maps its
    four outcomes onto its four lines; under an owner state that is not OK it reads nothing."""
    draft = rules.calendar_sha256(ROOT / "core" / "calendars" / "data")
    other, seen = "a" * 64, []
    cases = ((("log", ""), "calendar: not checked (owner log not usable)"),
             (("none", ""), "calendar: no signed approval, so KRX and US plans are refused (crypto plans only)"),
             (("store", other), f"calendar: the signed version {other[:16]} is missing or altered in the store"),
             (("ok", draft), f"calendar: the draft is the version in force ({draft[:16]})"),
             (("ok", other), f"calendar: the draft {draft[:16]} is not the version in force ({other[:16]}); it counts "
                             "only once signed"))
    saved = owner._calendar_approval
    try:
        for result, line in cases:
            owner._calendar_approval = lambda now, result=result: seen.append(now) or result
            assert rules._calendar_line(F.ctx(), ROOT, NOW) == line, result
        broken = F.ctx(owner=model.OwnerState.broken("bad signature on entry 4"))
        assert rules._calendar_line(broken, ROOT, NOW) == "calendar: not checked (owner log not usable)"
    finally:
        owner._calendar_approval = saved
    assert seen == [NOW] * len(cases), seen
```

  **Edit G1**, `tests/compliance_gate.py`. Anchor: `test_gate_call_graph_has_no_clock_zone_file_or_socket`, the last
  test of the file, its closing `for module, scan in scans.items():` loop (the last four lines of the file at
  `5816d3c`). The new section goes after it, at the end of the file. Old text (exact):

```python
    for module, scan in scans.items():
        assert len(scan) >= 3, (module, scan)
        for name, hits in scan.items():
            assert hits == set(), (module, name, hits)
```

  New text:

```python
    for module, scan in scans.items():
        assert len(scan) >= 3, (module, scan)
        for name, hits in scan.items():
            assert hits == set(), (module, name, hits)


# --------------------------------------------------------------------------- #
# Odds plan Task 4 (Q20): grey_rows, the in-force grey rows of a plan's leg as the cash buy screen() decides. Helpers
# are prefixed `_t10_`; the `_t8_` and `_t9_` helpers above are reused, never redefined.
# --------------------------------------------------------------------------- #
class _T10Unreadable:
    """A plan leg whose venue cannot be read: grey_rows answers () instead of raising."""

    @property
    def venue(self):
        raise RuntimeError("an unreadable leg")


def test_grey_rows_names_the_in_force_grey_rows_of_the_leg():
    """Q20: the sorted ids of the venue rows in force on ctx.date (effective_from <= date < effective_until) with
    treatment grey that match the leg as a cash buy. It reads the rows of the state in force, so a row signed grey is
    named too; plan.start, horizon_days and the signed code play no part (screen checks those)."""
    day, c = _T8_DAY, F.ctx()
    okx = _t9_plan("okx", "BTC", c.date, 5)
    assert gate.grey_rows(okx, c) == ("KR-OKX-SPOT",)
    assert gate.grey_rows(_t9_plan("okx", "USDT", c.date, 5), c) == ("KR-OKX-SPOT",)
    for venue, symbol in (("upbit", "BTC"), ("kis", "005930"), ("kis", "069500"), ("kis", "SPY")):
        assert gate.grey_rows(_t9_plan(venue, symbol, c.date, 5), c) == (), (venue, symbol)
    for on, ids in ((day(2026, 1, 14), ()), (day(2026, 1, 15), ("KR-OKX-SPOT",)),
                    (day(2026, 12, 3), ("KR-OKX-SPOT",)),          # auto_off blocks new exposure; still in force
                    (day(2027, 2, 17), ("KR-OKX-SPOT",)), (day(2027, 2, 18), ())):
        assert gate.grey_rows(okx, F.ctx(date=on)) == ids, on
    for odd in (_t9_plan("okx", "BTC", "2026-10-23", 0), _t9_types.SimpleNamespace(leg=okx.leg)):
        assert gate.grey_rows(odd, c) == ("KR-OKX-SPOT",), odd
    assert gate.grey_rows(okx, F.ctx(code_signed=False)) == ("KR-OKX-SPOT",)
    both = _t8_with_rows(F.approved(), {"KR-DOMESTIC-SPOT": {"treatment": "grey",
                                                             "match": _t8_row("KR-OKX-SPOT").match}})
    assert gate.grey_rows(okx, F.ctx(active=both)) == ("KR-DOMESTIC-SPOT", "KR-OKX-SPOT")
    # sorted, not in table order: in kr_rules.yaml KR-OKX-SPOT comes before KR-OKX-P2P
    p2p = _t8_with_rows(F.approved(), {"KR-OKX-P2P": {"treatment": "grey", "match": _t8_row("KR-OKX-SPOT").match}})
    assert gate.grey_rows(okx, F.ctx(active=p2p)) == ("KR-OKX-P2P", "KR-OKX-SPOT")
    kis = _t8_with_rows(F.approved(), {"KR-KIS-KRX-SHARE": {"treatment": "grey"}})
    assert gate.grey_rows(_t9_plan("kis", "005930", c.date, 5), F.ctx(active=kis)) == ("KR-KIS-KRX-SHARE",)


def test_grey_rows_is_empty_when_nothing_can_be_looked_up():
    """Q20: () for a context not from load_context, a broken owner log, an invalid state (a snapshot is for exits
    only), a malformed plan, a venue or symbol the state does not list, and any error reading the plan; it never
    raises. The symbol is looked up as screen() looks up a buy, in the map in force only: one that only an earlier
    approved map knows gives ()."""
    c = F.ctx()
    okx = _t9_plan("okx", "BTC", c.date, 5)
    hand = model.Context(**{f.name: getattr(c, f.name) for f in dataclasses.fields(model.Context)})
    dead = model.ApprovedState.invalid("rules: unapproved")
    for context in (None, "ctx", hand, F.ctx(owner=model.OwnerState.broken("bad signature on entry 4")),
                    F.ctx(active=dead), F.ctx(active=dead, snapshot=F.approved())):
        assert gate.grey_rows(okx, context) == (), context
    for plan in (None, "plan", _t9_types.SimpleNamespace(), _t9_types.SimpleNamespace(leg=None),
                 _t9_types.SimpleNamespace(leg=_T10Unreadable()),
                 _t9_plan("binance", "BTC", c.date, 5), _t9_plan("nowhere", "BTC", c.date, 5),
                 _t9_plan(5, "BTC", c.date, 5), _t9_plan("okx", "NOPE", c.date, 5), _t9_plan("okx", None, c.date, 5),
                 _t9_plan("okx", ["BTC"], c.date, 5), _t9_plan("kis", "BTC", c.date, 5)):
        assert gate.grey_rows(plan, c) == (), plan
    cur = F.approved()
    gone = dataclasses.replace(cur, instruments=dataclasses.replace(cur.instruments, entries={
        k: v for k, v in cur.instruments.entries.items() if k != ("crypto", "BTC")}), history_maps=(cur.instruments,))
    assert gate.grey_rows(okx, F.ctx(active=gone)) == ()               # BTC is in the earlier map only
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, from the repo root in Git Bash (these modules run through the compliance aggregator; the odds aggregator
  lists only `odds_*` modules). Give the Bash tool `timeout: 300000` (compliance_store/ builds many signed homes
  and can run past the 120 s default):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: tracebacks, and exactly these seven FAIL lines among the PASS lines (in this order, the harness's
  alphabetical order):

```
FAIL compliance_store/test_calendar_in_force_counts_only_approvals_stamped_by_now AttributeError: module 'core.compliance.owner' has no attribute '_calendar_approval'
FAIL compliance_store/test_calendar_in_force_is_none_without_an_ok_owner_log AttributeError: module 'core.compliance.owner' has no attribute '_calendar_approval'
FAIL compliance_store/test_calendar_in_force_is_the_sha_of_the_intact_signed_copy TypeError: _full_home() got an unexpected keyword argument 'calendar_raw'
FAIL compliance_store/test_calendar_in_force_refuses_a_naive_or_out_of_range_now AttributeError: module 'core.compliance.owner' has no attribute 'calendar_in_force'
FAIL compliance_store/test_calendar_line_maps_the_shared_calendar_approval AttributeError: module 'core.compliance.owner' has no attribute '_calendar_approval'
FAIL compliance_store/test_full_home_signs_the_odds_keywords TypeError: _full_home() got an unexpected keyword argument 'venues_raw'
FAIL compliance_store/test_signed_home_helpers_are_the_public_fixtures AttributeError: module 'tests.compliance_fixtures' has no attribute 'pubkey_at'
```

  then `29/36 passed, 7 failed, 0 not run` and exit code 1 (the follow-up's 29 tests pass; a different merged count
  gives that count plus 7 in all, still with exactly these 7 failing).

  Overlap check, then (Bash tool `timeout: 300000`):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_gate/
```

  Expected: tracebacks, and exactly these two FAIL lines among the PASS lines:

```
FAIL compliance_gate/test_grey_rows_is_empty_when_nothing_can_be_looked_up AttributeError: module 'core.compliance.gate' has no attribute 'grey_rows'
FAIL compliance_gate/test_grey_rows_names_the_in_force_grey_rows_of_the_leg AttributeError: module 'core.compliance.gate' has no attribute 'grey_rows'
```

  then `49/51 passed, 2 failed, 0 not run` and exit code 1.

- [ ] **Step 3: Implement**

  Six Edit-tool replacements, all in LF files. Re-read each file before its Edit (DRIFT RULE). Keep every new line
  ASCII and within 120 characters.

  **Edit F1**, `tests/compliance_fixtures.py`. Anchor: `store_blob`, the last function of the file, its last three
  lines (the follow-up does not change this file). The moved helpers go after it, at the end of the file. They are
  `tests/compliance_store.py`'s `NOW` .. `_full_home` and `TABLES` (as of `5816d3c`), renamed public, with `F.`
  dropped (they live in the fixtures module now), `model` and `json` imported at module level under private aliases
  like this file's other late imports, `owner` imported inside each helper that uses it (as `store_blob` does), the
  four new keywords of `full_home`, and the guards (`owner_key`: the pem must lie inside `home` and, new, inside the
  temp dir; `sign`, new: the log must lie inside the temp dir; `approve`, new: the state root must lie inside
  `home`). If the merged `compliance_store.py` shows a follow-up change inside those
  helpers, carry it into this copy and record a drift ruling. Old text (exact):

```python
    if not owner.store_dir().is_relative_to(home):
        raise AssertionError(f"store_blob: {owner.store_dir()} is outside the temp home {home}")
    return owner.store_put(kind, raw, anchor)
```

  New text:

```python
    if not owner.store_dir().is_relative_to(home):
        raise AssertionError(f"store_blob: {owner.store_dir()} is outside the temp home {home}")
    return owner.store_put(kind, raw, anchor)


# -- signed temp homes (moved from tests/compliance_store.py by the odds plan, Task 4, Q21) ---------------------
# compliance_store binds its old private names to these, so its tests are unchanged; the odds suite builds the same
# homes. A home is signed with the fixed test key only, inside a temp TRADEGEN_HOME: owner_key refuses a pem and
# sign an owner log outside the temp dir (so never the repo's trust anchor or the real ~/.tradegen), and approve a
# state root outside its `home`, each before it writes. owner is imported inside each helper, as in store_blob, so
# temp_home never depends on owner.py importing.
import datetime as _dt  # noqa: E402
import json as _json  # noqa: E402

from core.compliance import model as _model  # noqa: E402

TABLES = ("rules", "instruments", "venues")
NOW = _dt.datetime(2026, 10, 24, 9, 0, tzinfo=_model.KST)
HELD = _model.Positions(equity_krw=1_000_000.0, holdings={("upbit", "BTC"): 0.01})


@contextlib.contextmanager
def pubkey_at(path: Path):
    """owner.PUBKEY_PATH pointed at `path` for the block, restored afterwards."""
    from core.compliance import owner
    saved = owner.PUBKEY_PATH
    owner.PUBKEY_PATH = path
    try:
        yield path
    finally:
        owner.PUBKEY_PATH = saved


def owner_key(home: Path):
    """The test key, its pem written to owner.PUBKEY_PATH, which must lie inside the temp home `home` and inside the
    temp dir, so the repo's trust anchor is never written, even for a `home` that holds the repo. NotRun PENDING
    without cryptography."""
    from core.compliance import owner
    path = owner.PUBKEY_PATH
    if not (path.is_relative_to(home) and path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())):
        raise AssertionError(f"owner_key: {path} is outside the temp home {home}")
    key = test_key()
    write_pubkey(path, key)
    return key


def sign(key, kind: str, data: dict, utc: str = "2026-10-23T00:00:00Z") -> tuple[int, str]:
    """Appends one signed owner entry to the temp home's log; returns its anchor (seq, row_sha256). Refused before
    the owner log is read or written when it is not inside the temp dir, so the real ~/.tradegen is never written."""
    from core.compliance import owner
    path = owner.log_path()
    if not path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise AssertionError(f"sign: {path} is not inside a temp TRADEGEN_HOME")
    lines = path.read_bytes().splitlines() if path.is_file() else []
    prev = _json.loads(lines[-1])["row_sha256"] if lines else owner.GENESIS_PREV
    line = signed_entry(key, len(lines) + 1, prev, kind, data, utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as fh:
        fh.write(line)
    return len(lines) + 1, _json.loads(line)["row_sha256"]


def approve(home: Path, key, kind: str, raw: bytes) -> str:
    """Signs `approved {kind, sha256}` for `raw` and stores the bytes with that entry as their anchor; refused before
    anything is written when the state root is not the temp home `home`."""
    from core.compliance import owner
    if not owner.home().is_relative_to(home):
        raise AssertionError(f"approve: {owner.home()} is outside the temp home {home}")
    return store_blob(home, kind, raw, sign(key, "approved", {"kind": kind, "sha256": _model.sha256_hex(raw)}))


def other_code(key, utc: str = "2026-10-23T00:00:00Z") -> None:
    """Signs a code_approved that names a hash other than the code on disk."""
    from core.compliance import owner
    files = sorted([list(f) for f in owner.code_files(owner.REPO_ROOT)] + [["core/compliance/zz.py", "0" * 64]])
    sign(key, "code_approved", {"sha256": _model.sha256_hex(_model.canonical_json(files)), "files": files}, utc)


def full_home(home: Path, *, rules_raw: bytes | None = None, venues_raw: bytes | None = None,
              calendar_raw: bytes | None = None, limits: dict | None = None, cap: float | None = None):
    """The test key at owner.PUBKEY_PATH, the three shipped drafts (or `rules_raw`, `venues_raw`) approved and
    stored, the current code hash signed and the owner's age recorded; then, only when given, `calendar_raw` (a
    rules.calendar_stream blob) approved as kind calendar, `limits` signed as limit_set and `cap` as the
    okx_equity_share cap_set. Every entry is stamped 2026-10-23T00:00:00Z, so a limit or cap counts from NOW's date
    on (D12). Returns the key. NotRun PENDING without cryptography."""
    from core.compliance import owner
    key = owner_key(home)
    given = {"rules": rules_raw, "venues": venues_raw}
    for kind in TABLES:
        raw = given.get(kind)
        approve(home, key, kind, raw if raw is not None else shipped_bytes(kind))
    files = [list(f) for f in owner.code_files(owner.REPO_ROOT)]
    sign(key, "code_approved", {"sha256": owner.code_hash(owner.REPO_ROOT), "files": files})
    sign(key, "age_of_majority", {"birth_date": "2000-01-01", "evidence": "test fixture"})
    if calendar_raw is not None:
        approve(home, key, "calendar", calendar_raw)
    if limits is not None:
        sign(key, "limit_set", dict(limits))
    if cap is not None:
        sign(key, "cap_set", {"key": "okx_equity_share", "value": cap})
    return key
```

  **Edit S2**, `tests/compliance_store.py`. Anchor: the last two lines of the module's import block and the
  constants `ROOT` and `TABLES` below them (lines 17-21 at `5816d3c`; the follow-up's `import ast` goes in further up,
  above `import contextlib`). `TABLES` now comes from the fixtures. Old text (exact):

```python
from tests import compliance_fixtures as F
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
TABLES = ("rules", "instruments", "venues")
```

  New text:

```python
from tests import compliance_fixtures as F
from tests.compliance_fixtures import HELD, NOW, TABLES
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
```

  **Edit S3**, `tests/compliance_store.py`. Anchor: the "load_context (spec 6.4, 8.2; P19, P24)" section, from
  `NOW = ...` through the `return key` of `_full_home` (lines 242-299 at `5816d3c`, about 43 lines lower once the
  follow-up has merged). The section banner above it and `test_no_owner_key_blocks_every_new_exposure` below it stay.
  Old text (exact):

```python
NOW = _dt.datetime(2026, 10, 24, 9, 0, tzinfo=model.KST)
HELD = model.Positions(equity_krw=1_000_000.0, holdings={("upbit", "BTC"): 0.01})


@contextlib.contextmanager
def _pubkey_at(path: Path):
    """owner.PUBKEY_PATH pointed at `path` for the block, restored afterwards."""
    saved = owner.PUBKEY_PATH
    owner.PUBKEY_PATH = path
    try:
        yield path
    finally:
        owner.PUBKEY_PATH = saved


def _owner_key(home: Path):
    """The test key, its pem written to owner.PUBKEY_PATH, which must lie inside the temp home `home`: the repo's
    trust anchor is never written. NotRun PENDING without cryptography."""
    if not owner.PUBKEY_PATH.is_relative_to(home):
        raise AssertionError(f"{owner.PUBKEY_PATH} is outside the temp home {home}")
    key = F.test_key()
    F.write_pubkey(owner.PUBKEY_PATH, key)
    return key


def _sign(key, kind: str, data: dict, utc: str = "2026-10-23T00:00:00Z") -> tuple[int, str]:
    """Appends one signed owner entry to the temp home's log; returns its anchor (seq, row_sha256)."""
    path = owner.log_path()
    lines = path.read_bytes().splitlines() if path.is_file() else []
    prev = json.loads(lines[-1])["row_sha256"] if lines else owner.GENESIS_PREV
    line = F.signed_entry(key, len(lines) + 1, prev, kind, data, utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as fh:
        fh.write(line)
    return len(lines) + 1, json.loads(line)["row_sha256"]


def _approve(home: Path, key, kind: str, raw: bytes) -> str:
    """Signs `approved {kind, sha256}` for `raw` and stores the bytes with that entry as their anchor."""
    return F.store_blob(home, kind, raw, _sign(key, "approved", {"kind": kind, "sha256": model.sha256_hex(raw)}))


def _other_code(key, utc: str = "2026-10-23T00:00:00Z") -> None:
    """Signs a code_approved that names a hash other than the code on disk."""
    files = sorted([list(f) for f in owner.code_files(owner.REPO_ROOT)] + [["core/compliance/zz.py", "0" * 64]])
    _sign(key, "code_approved", {"sha256": model.sha256_hex(model.canonical_json(files)), "files": files}, utc)


def _full_home(home: Path, *, rules_raw: bytes | None = None):
    """The test key at owner.PUBKEY_PATH, the three shipped drafts (or `rules_raw`) approved and stored, the current
    code hash signed and the owner's age recorded. Returns the key. NotRun PENDING without cryptography."""
    key = _owner_key(home)
    for kind in TABLES:
        _approve(home, key, kind, rules_raw if kind == "rules" and rules_raw is not None else F.shipped_bytes(kind))
    files = [list(f) for f in owner.code_files(owner.REPO_ROOT)]
    _sign(key, "code_approved", {"sha256": owner.code_hash(owner.REPO_ROOT), "files": files})
    _sign(key, "age_of_majority", {"birth_date": "2000-01-01", "evidence": "test fixture"})
    return key
```

  New text:

```python
# NOW, HELD, TABLES and the signed-home helpers live in tests/compliance_fixtures.py (odds plan Task 4, Q21), so the
# odds suite builds the same homes; the old private names stay bound to them, so no test below changes.
_pubkey_at = F.pubkey_at
_owner_key = F.owner_key
_sign = F.sign
_approve = F.approve
_other_code = F.other_code
_full_home = F.full_home
```

  `import contextlib` stays in the import block: nothing in the module uses it after this Edit, but removing it
  would widen the diff in an import block the follow-up already edited, and an unused import is harmless here.

  **Edit O1**, `core/compliance/owner.py`. Anchor: `_context`, the last function of the file (below `_owner_now`,
  `_approved_now` and `load_context`), its closing `return model.seal_context(...)` statement. The follow-up changes
  only `_guards`, `_skipped`, `_import_nodes` and `_repo_imports`, far above. The two new functions go after it, at
  the end of the file. They use only names the module already has (`_dt`, `model`, `_owner_now`, `_up_to`,
  `in_force`, `store_get`), so no import is added. Old text (exact):

```python
    return model.seal_context(
        date=day, active=active, snapshot=snapshot, owner=owner, code_hash=current, code_signed=signed,
        session=model.SessionState(session_id=session_id, armed=session_id in owner.armed_sessions),
        equity_krw=equity, holdings=holdings, shorts=shorts, exposure=exposure)
```

  New text:

```python
    return model.seal_context(
        date=day, active=active, snapshot=snapshot, owner=owner, code_hash=current, code_signed=signed,
        session=model.SessionState(session_id=session_id, armed=session_id in owner.armed_sessions),
        equity_krw=equity, holdings=holdings, shorts=shorts, exposure=exposure)


# --------------------------------------------------------------------------- #
# The signed calendar set in force (odds plan Task 4, Q19; spec 4 "Calendars", 6.3; P21, O6)
# --------------------------------------------------------------------------- #
def _calendar_approval(now: _dt.datetime) -> tuple[str, str]:
    """The latest `approved {kind: calendar}` stamped at or before `now`, read the way load_context reads the
    tables: ("log", "") when the owner state at `now` is not OK (no key, cryptography missing, an unreadable or broken
    log, KEY CHANGED); ("none", "") when no calendar approval is stamped by then; ("store", sha256) when its stored
    copy is missing or altered; ("ok", sha256) otherwise. ValueError for a non-datetime, naive or out-of-range `now`
    (load_context's checks); any other failure is ("log", ""). rules._calendar_line maps the four outcomes onto its
    lines; calendar_in_force keeps "ok" only."""
    if not isinstance(now, _dt.datetime):
        raise ValueError(f"calendar approval: now must be an aware datetime, got {now!r}")
    try:
        now_utc = model.iso_utc(now)                   # ValueError on a naive datetime
        day = now.astimezone(model.KST).date()
    except OverflowError:
        raise ValueError(f"calendar approval: now is out of range, got {now!r}") from None
    try:
        state, check = _owner_now(day, now_utc, None)
        if not state.ok or check is None:
            return "log", ""
        sha = in_force(_up_to(check, now_utc)).get("calendar", ("", 0))[0]
        if not sha:
            return "none", ""
        return ("ok" if store_get("calendar", sha) is not None else "store"), sha
    except Exception:                                  # fail closed: an internal error counts as an unusable log
        return "log", ""


def calendar_in_force(now: _dt.datetime) -> str | None:
    """The sha256 of the calendar set in force at `now` (O6): the latest calendar approval stamped by `now`, under an
    OK owner state, whose stored copy is intact; None otherwise. The odds engine prices a KRX or US leg only when
    this is the sha of the calendar set it was given. Reads the owner log and the store as load_context does;
    ValueError for a non-datetime, naive or out-of-range `now`, and nothing else raises."""
    outcome, sha = _calendar_approval(now)
    return sha if outcome == "ok" else None
```

  **Edit R1**, `core/compliance/rules.py`. Anchor: `_calendar_line(ctx, root, moment)`, from its def line through its
  "missing or altered in the store" return. The follow-up leaves this function's text unchanged; it only moves down.
  The draft comparison after it stays as it is. Old text (exact):

```python
def _calendar_line(ctx, root: Path, moment) -> str:
    """The calendar draft (P21) against the latest calendar approval signed by `moment` (load_context's cut-off),
    whose stored copy must be intact. The Context does not carry it, so the log is read and verified once more."""
    from core.compliance import model, owner
    if not ctx.owner.ok:
        return "calendar: not checked (owner log not usable)"
    try:
        log = owner.verify_log(owner._log_lines(owner.log_path()), owner.read_pubkey(owner.PUBKEY_PATH),
                               owner.read_anchors())
    except (OSError, ValueError, RuntimeError):         # an unreadable key, anchor or log file means BROKEN (Task 11)
        return "calendar: not checked (owner log not usable)"
    if not log.ok:
        return "calendar: not checked (owner log not usable)"
    signed = owner.in_force(owner._up_to(log, model.iso_utc(moment))).get("calendar", ("", 0))[0]
    if not signed:
        return "calendar: no signed approval, so KRX and US plans are refused (crypto plans only)"
    if owner.store_get("calendar", signed) is None:
        return f"calendar: the signed version {signed[:16]} is missing or altered in the store"
```

  New text:

```python
def _calendar_line(ctx, root: Path, moment) -> str:
    """The calendar draft (P21) against the latest calendar approval signed by `moment` (load_context's cut-off),
    whose stored copy must be intact. The Context does not carry it, so owner._calendar_approval, which
    owner.calendar_in_force shares (odds plan Q19), reads and verifies the log once more."""
    from core.compliance import model, owner
    if not ctx.owner.ok:
        return "calendar: not checked (owner log not usable)"
    outcome, signed = owner._calendar_approval(moment)
    if outcome == "log":                                # an unreadable key, anchor or log file means BROKEN (Task 11)
        return "calendar: not checked (owner log not usable)"
    if outcome == "none":
        return "calendar: no signed approval, so KRX and US plans are refused (crypto plans only)"
    if outcome == "store":
        return f"calendar: the signed version {signed[:16]} is missing or altered in the store"
```

  **Edit G2**, `core/compliance/gate.py`. Anchor: `_screening(d, flags, window)`, the last function of the file, its
  closing `return model.Screening(...)` statement (the follow-up does not change `gate.py`). `grey_rows` goes after
  it, at the end of the file. It builds `state`, `venue`, `inst` and the intent exactly as `_screen` does (quantity
  and notional 1.0, since neither changes which rows match) and calls only the gate's own helpers, so it adds no
  import and no clock, zone, file or socket name. Old text (exact):

```python
    return model.Screening(decision=d, allowed=allowed, flags=flags, exit_date=exit_date,
                           screening_hash=model.sha256_hex(model.canonical_json(body)))
```

  New text:

```python
    return model.Screening(decision=d, allowed=allowed, flags=flags, exit_date=exit_date,
                           screening_hash=model.sha256_hex(model.canonical_json(body)))


def grey_rows(plan, ctx) -> tuple[str, ...]:
    """The ids, sorted, of the venue rows in force on ctx.date with treatment grey that match the plan's single leg
    as the cash buy screen() builds (P3: reads plan.leg.venue and plan.leg.symbol only), so the odds engine names a
    plan's grey rows without the gate's private helpers (odds plan Q20). () for a context not from load_context, an
    owner log that is not OK, an unusable state, a venue or symbol the state does not list, or any error. Pure;
    never raises."""
    try:
        leg = getattr(plan, "leg", None)
        venue_id, symbol = getattr(leg, "venue", None), getattr(leg, "symbol", None)
        if not (model.is_sealed(ctx) and ctx.owner.ok and _usable(ctx.active) and _is(venue_id, rules.VENUES)):
            return ()
        state = ctx.active
        venue = state.venues.venues.get(venue_id)
        inst = _lookup(state, venue, symbol, False) if venue is not None else None
        if inst is None:
            return ()
        intent = Intent(venue=venue_id, symbol=symbol, counter_symbol=venue.quote_for(inst), asset=inst.asset,
                        multiple=inst.multiple, action="buy", quantity=1.0, notional_krw=1.0)
        return tuple(sorted(row.id for row in _in_force(state, intent, inst.cls, ctx.date)
                            if row.treatment == "grey"))
    except Exception:
        return ()
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below; the two
  `--suite` lines carry it as the Git Bash prefix of Global Constraints instead. All run from the repo root in Git
  Bash. Give every Python command the Bash tool `timeout: 300000`, and the `--suite compliance` line
  `timeout: 600000`: `compliance_store/` alone can run past the 120 s default (every `full_home` and every
  `load_context` hashes the code), and a killed command skips whatever is chained after it.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: every line PASS, then `36/36 passed, 0 failed, 0 not run` (exit code 0; the follow-up's 29 plus this
  task's 7). `test_code_files_is_the_import_closure` still passes, because no closure file gained an import.

  Overlap check, then the gate, whose two purity tests (`test_gate_call_graph_has_no_clock_zone_file_or_socket` now
  scans `grey_rows` too; `test_purity_no_file_clock_zone_or_network`) must stay green unchanged:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_gate/
```

  Expected: every line PASS, then `51/51 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then the `--check` CLI. Its calendar-line tests (`test_check_calendar_signed_cut_off_and_store`,
  `test_check_calendar_draft_differs`, `test_check_code_3_broken_log`) now go through `owner._calendar_approval` and
  must pass unchanged:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected, ending: `36/36 passed, 0 failed, 0 not run` (exit code 0; 36 once the follow-up has merged).

  Overlap check, then the owner-log tests and the signer, whose `test_code_files_match_owner` compares the signer's
  copy of the closure scan with `owner.code_files` on the changed tree:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_owner/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected (with an overlap check before each): `52/52 passed, 0 failed, 0 not run` and
  `38/38 passed, 0 failed, 0 not run` (exit code 0 each; the signer's 38 once the follow-up has merged).

  Overlap check, then the static guards (Global Constraints: every task that touches `core/compliance`). A failure
  names the offending file and text: fix the new code, never the guard.

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Expected, ending: `16/16 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then the odds guards (owner.py, rules.py and gate.py are D14 closure files;
  `test_code_closure_holds_no_data_layer` recomputes the closure):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected: no FAIL line, then `18/18 passed, 0 failed, 0 not run` (exit code 0). If the merged count differs, the
  tail Task 1 recorded under "Runs" in the execution ledger is the one to match.

  Overlap check, then the core-wide scans (Global Constraints: every task that changes `core/`), one at a time with
  the overlap check before each:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
```

  Expected: no FAIL line and exit code 0 each, with these summary lines in this order: `11/11 passed, 0 failed,
  0 not run`, `20/22 passed, 0 failed, 2 not run`, `14/18 passed, 0 failed, 4 not run`, `17/23 passed, 0 failed,
  6 not run`, `14/16 passed, 0 failed, 2 not run` (the counts Task 1 recorded; the follow-up changes no
  `tests/macro_*.py` file). If a merged count differs, the tail Task 1 recorded under "Runs" is the one to match.

  Then the cockpit suite (test_08, test_09, test_16, test_18), and then the whole compliance suite, each as one
  Bash command that runs the overlap check first and restores the tracked results file afterwards whatever the run
  did (`timeout: 300000` for the cockpit line, `timeout: 600000` for the compliance line):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: the cockpit run ends `47/47 passed, 0 failed, 0 not run; <path of qa/acceptance_results.json>` (the
  count Task 1 recorded; if the merged count differs, match Task 1's tail under "Runs"), then `exit 0`. The
  compliance run lists every `compliance/...` row as PASS except the two REFDATA symlink rows (`compliance/compliance_isolation/
  test_symlinks_are_refused` and `compliance/compliance_tables/test_calendar_sha256_refuses_a_file_symlink`), and
  ends `339/341 passed, 0 failed, 2 not run; <path of qa/acceptance_results.json>` (Task 3's 332 rows plus this
  task's 9; with Developer Mode on, `341/341 passed, 0 failed, 0 not run`), then `exit 0`. An `exit 1` with no run
  output means the overlap check found a run: wait and run the line again.

  Then the text checks (git only; no overlap check needed):

```bash
git status --short
git diff -U0 -- core/compliance/owner.py core/compliance/rules.py core/compliance/gate.py | grep -E '^\+[[:space:]]*(import|from)[[:space:]]'
git grep -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode" -- core/compliance/owner.py core/compliance/rules.py core/compliance/gate.py
git grep -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|/uapi/|reference_only" -- core/compliance/owner.py core/compliance/rules.py core/compliance/gate.py
git grep -n -E "datetime|ZoneInfo" -- core/compliance/gate.py
git grep -n -E "^def (grey_rows|calendar_in_force|_calendar_approval)\(" -- core/compliance
```

  Expected: `git status --short` lists exactly ` M core/compliance/gate.py`, ` M core/compliance/owner.py`,
  ` M core/compliance/rules.py`, ` M tests/compliance_fixtures.py`, ` M tests/compliance_gate.py`,
  ` M tests/compliance_store.py` and `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`. The
  import grep, the two banned-text greps and the gate-word grep each print nothing (exit code 1): no closure file
  gained an import, none of the three files names a KIS account field, a trading path or a banned word, and
  `gate.py` still never says `datetime` or `ZoneInfo`. The last grep prints exactly three lines,
  `core/compliance/gate.py:<n>:def grey_rows(plan, ctx) -> tuple[str, ...]:`,
  `core/compliance/owner.py:<n>:def _calendar_approval(now: _dt.datetime) -> tuple[str, str]:` and
  `core/compliance/owner.py:<n>:def calendar_in_force(now: _dt.datetime) -> str | None:`.

  Append the tails of these runs, one line each, under "Runs" in the execution ledger (LF; it stays untracked).

- [ ] **Step 5: Commit**

```bash
git add core/compliance/owner.py core/compliance/rules.py core/compliance/gate.py tests/compliance_fixtures.py tests/compliance_store.py tests/compliance_gate.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (every file is LF). Then:

```bash
git commit -m "feat(compliance): calendar_in_force, grey_rows and public signed-home fixtures" -m "Odds plan Task 4 (Q19, Q20, Q21): the odds engine reads the signed calendar sha and a leg's grey rows through public helpers, and the odds suite builds full signed temp homes." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Afterwards `git status --short` prints only `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
