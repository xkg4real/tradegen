### Task 10: The evidence writer (`execution/evidence.py`)

**Files:**
- Create: `execution/evidence.py` (LF, UTF-8, no BOM)
- Modify: `tests/execution_evidence.py` (anchors: the import block at the top of the file; the last three lines of
  Task 9's last test `test_a_missing_unreadable_or_refused_file_gives_no_evidence`, after which this task's block is
  appended; LF)
- Modify: `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (anchors: the `## Deferred
  minors` heading, above which Step 3 adds two ruling lines; the end of the file, the `## Runs` section, where Step 4
  appends one timing line; LF)
- Test: `tests/execution_evidence.py`

**Interfaces:**
- Consumes:
  - Task 9, `core/compliance/owner.py`: `EVIDENCE_THRESHOLDS_KRW` (a `MappingProxyType` in the order
    `deposit_krw_10m`, `deposit_krw_15m`, `deposit_krw_20m`, `cash_krw_30m`), `EVIDENCE_KEYS`, `evidence_path() ->
    Path` (creates nothing), `evidence_chain(lines: list[bytes]) -> tuple[list[dict], str]` (`(rows, "")` or
    `([], "line N: <defect>")`, the defect named by field, never by value; never raises; a `utc` stamped past
    `9999-12-31T14:59:59Z` is `line N: utc has no Asia/Seoul date`, so every row it returns has a Seoul date and
    `due`'s `_seoul_day(last["utc"])` never overflows; this task's broken-chain test pins it), `evidence_in_force(lines,
    today) -> frozenset[str]`, `_live_evidence(day)` (tests only: `load_context`'s reader, which splits the file with
    `read_bytes().splitlines(keepends=True)`); and the repo's public `owner.GENESIS_PREV` (`"0" * 64`,
    owner.py:31 at `5816d3c`). `owner._seoul_date` is private, so evidence.py computes the Seoul date itself from
    `model.KST`.
  - Task 9, `tests/execution_evidence.py` (reused, never redefined): `_t9_chain(*records) -> list[bytes]`,
    `_t9_body(seq, prev, utc, requirement, met, value_krw=None) -> dict`, `_t9_sealed(body) -> bytes`,
    `_t9_prev(lines) -> str`, `_T9_TODAY`; its imports `json`, `os`, `date`, `datetime`, `timezone`, `isolation`,
    `model`, `owner`, `rules`.
  - Task 4, `execution/snapshot.py`: `Snapshot` (frozen; `snapshot_sha256` always derived), `failed(venue, utc,
    error, *, flags=...)`, `exclusive(path)` (judges the folder with `checked_target(path.parent, "E1 state folder")`,
    then locks `checked_target(str(path) + ".lock", "E1 lock file")`; one process-wide lock, never nested),
    `write_lines(path, lines, what)` (no lines: opens nothing; else `open(checked_target(path, what), "a+b")`, fsync);
    the module-level name `snapshot.checked_target` (its `from core.isolation import checked_target`), which one test
    wraps (save/restore). Task 4 fixture `tests.execution_fixtures.snap(venue, **fields)` (an ok snapshot stamped
    `NOW`) and `NOW` (`2026-10-24T00:00:00Z`, 09:00 KST).
  - Task 5's KIS snapshot shape (contract 9): `deposit_krw` = `dnca_tot_amt`; `cash` = `{"KRW": prvs_rcdl_excc_amt}`
    plus `{crcy_cd: frcr_dncl_amt_2}`; `prices_krw[crcy_cd]` = `frst_bltn_exrt` (stock prices sit in the same map
    under their symbols).
  - `core.isolation.checked_target(path, what)` and `state_root()`; `core.compliance.model`: `KST`, `iso_utc`,
    `canonical_json`, `sha256_hex`.
  - Task 1: `tests/execution_acceptance.py` (`MODULES` lists `execution_evidence`; `_wrap` runs every test in
    `hermetic()`, a fresh `temp_home()` named `tradegen_home_*` and `isolated(home)`); `tests/execution_guards.py`,
    whose scans of every `execution/**/*.py` now see `execution/evidence.py` (`EVIDENCE_WRITER =
    "execution/evidence.py"` is the one file that may name `evidence_path`).
- Produces (`execution/evidence.py`, contract 14; Task 12 relies on these exact names):
  - `class EvidenceBroken(Exception)`: the chain does not verify; nothing was appended. Not a `RuntimeError`,
    `ValueError` or `OSError`, so `poll_once`'s `except evidence.EvidenceBroken` never swallows a `checked_target`
    refusal (E33). Its text is `f"evidence.jsonl is broken ({why}); nothing appended"` with `why` from
    `owner.evidence_chain`.
  - `judge(kis: Snapshot) -> list[tuple[str, bool, float]]` (pure; a value below zero or not finite is
    `(item, False, 0.0)`, Design note point 3).
  - `due(rows: list[dict], requirement: str, met: bool, now: datetime) -> bool` (pure; E1R2-3): True when the item
    has no record, its `met` differs, or its last record is dated on another Seoul day than `now` (`!=`, Design note
    point 5); a naive `now` is `ValueError` (from `model.iso_utc`, called first, whatever `rows` hold).
  - `record(kis: Snapshot, now: datetime) -> list[dict]`: appends the due records and returns them as dicts (the
    seven `EVIDENCE_KEYS` plus `row_sha256`); `[]` when nothing is due or nothing can be judged. Task 12 calls it only
    when `kis.ok` and counts `len(...)` as the summary's `evidence`.
  - Private: `_DEPOSIT_ITEMS`, `_seoul_day(utc: str) -> date`.

**Plan decisions used:** E18 (vocabulary and thresholds from owner.py; `collateral_105pct` and `broker_approval`
never written; a record only when an item has none, its `met` changes, or its last record is dated on an earlier
Seoul day, read here as any other Seoul day, Design note point 5; the fold unchanged), E1R2-3 (spec rev 2: change
plus daily heartbeat in place of one record per poll, and the test that the fold reads the same `live_evidence`
either way, on every history, a clock stepped back included), E33 (`EvidenceBroken` for chain defects only; a
refused write, `evidence.jsonl` included, propagates as a crash), E4 (canonical JSON, sha256 hex, the line format,
the sidecar lock with fsync), E16 (`deposit_krw` is `dnca_tot_amt`; `cash` is settled fiat), E37 (error text from
names only), E11 (no clock: the poller passes `now`), E2 (imports), E8 (the execution suite under 60 s); contract
sections 0.5, 2 and 14.

Design notes (read before Step 3):
- Five points refine contract 14. None renames anything; points 3 and 5 depart from its text, and the end of Step 3
  records each as a one-line ruling in the ledger.
  (1) `record` checks `evidence.jsonl` with `checked_target` BEFORE it reads it, inside the lock, and
  `write_lines` checks it again before it opens it for the append. A hard-linked file is therefore always
  `checked_target`'s `RuntimeError` (a crash, E33), whatever it holds; read first, a linked file that is not a sound
  chain would come out as `EvidenceBroken`, an amber alert in place of a crash. A folder in place of the file passes
  `checked_target`, and its read raises an `OSError` (`PermissionError` on Windows) that also propagates as a crash:
  `EvidenceBroken` is for chain defects only (E33). The linked-file test pins both. (2) `record` returns `[]` at once
  when `judge` gives nothing (a not-ok or non-KIS snapshot, no `deposit_krw`), creating no folder, lock or file;
  `poll_once` calls it only when `kis.ok`, and an ok KIS snapshot always has a `deposit_krw` (Task 5 parses
  `dnca_tot_amt` or fails the snapshot; Task 5's `_num` accepts a number below zero, so such a snapshot is ok).
  (3) A value below zero or not finite (a `deposit_krw` below zero, a cash total below zero, a product that
  overflows to inf) is judged unmet and written as `0.0`: `(item, False, 0.0)`. Contract 14's
  `(item, deposit >= threshold, deposit)` cannot be written for such a value, since `owner.evidence_chain` refuses
  the line (`value_krw` below zero, or `canonical_json`'s NaN/inf refusal) and the chain would then stay broken,
  EVIDENCE_BROKEN on every poll until the owner repaired the file by hand. Skipping the item instead would fail
  open: its last met record would stay the latest one and keep the D16 rows lifted for up to 7 days, against spec 6
  ("a `met: false` record removes it at once") and E18's tighten-at-once. Only the total is checked: a foreign
  amount below zero simply lowers `cash_krw_30m`'s sum. (4) The Seoul date comes from `model.KST` in evidence.py
  (`owner._seoul_date` is private); `due` dates `now` through `model.iso_utc(now)`, the same stamp the record would
  carry, before it looks at `rows`, so a naive `now` is always `ValueError`.
  (5) `due` compares Seoul days with `!=` where the E1R2-3 ruling says "earlier" (`<`; contract 14, E18 and the
  header's E1R2-3 bullet now name this note). The two agree
  whenever poll times never go backward. They part when the PC clock runs ahead at one poll and is then set right.
  With `<`, the item's last record keeps the date that ran ahead, nothing is due until real time passes it, and the
  7-day expiry counts from that date. If the poller then stops, the D16 rows stay lifted for up to the size of the
  jump past the day one record per poll expires them (fail open); before that, they are blocked on days one record
  per poll lifts them. With `!=`, a record dated after `now` is re-stamped at once, so an item's latest record always
  carries the Seoul day of its last judged poll, as one record per poll leaves it, and the fold reads the same
  `live_evidence` on every history. The equivalence test's third history is that clock step; with `<` it fails.
- The file is split with `read_bytes().splitlines(keepends=True)`, exactly as `owner._live_evidence` splits it, so the
  writer verifies the very lines `load_context` will fold.
- `cash_krw_30m`'s value is `deposit_krw` plus every non-KRW `cash` amount times its `prices_krw` rate (contract 14);
  the KRW entry of `cash` (the D+2 settled amount, E16) is not added, since `deposit_krw` already stands for domestic
  cash. One missing rate skips the item (nothing is judged from a partial sum).
- Every test that can write first calls `_t10_home()`, which refuses any state root whose folder name does not start
  with `tradegen_home_`; a test function called outside the wrapper therefore writes no real evidence (a met record
  in `~/.tradegen/execution/evidence.jsonl` would lift D16 rows the next day).
- The equivalence test runs three histories. `_t10_midnight()`: 1-second steps across Seoul midnight with `met`
  flipping on each side, a missing `deposit_krw`, then gaps of 2 and 8 Seoul days (the second crosses the 7-day
  expiry). One random history of 12 polls from `random.Random(8)`, drawn after the manner of
  `e1/sandbox_round2/fold_probe.py`: 5-minute steps, gaps of 7 hours, 2 days and 9 days, 1-second steps, polls with
  KIS not ok, a missing `deposit_krw` and a missing USD rate, and a deposit drawn afresh at each poll from 9, 12, 16
  and 21 million, so every threshold is crossed both ways (8 is the first seed whose 12 polls hold every one of these;
  measured on a sandbox copy, 37 of its 120 comparisons have something in force, all four items among them).
  `_t10_backclock()`: the clock 5 days ahead at one poll, then set right, then no more polls (Design note point 5).
  Each history must have something in force on some compared day and not on all of them, so none is vacuous. 26
  polls times 10 days is 260 comparisons: 52 `record` calls (`checked_target` stats every ancestor of each path it
  judges, and the real tree's `QUANTGEN_REPO` adds `samefile` checks) and 520 folds, 1.4 to 2.4 s measured on a
  sandbox copy (about 0.03 s a `record` call and 1 ms a fold that day; the 220-comparison draft measured 1.7 to 6.9 s
  on other days), so allow about 2 to 12 s on the real tree. Both runs go through `record`; the second with
  `evidence.due` patched to return True (save/restore), and each into its own folder under the temp home
  (`TRADEGEN_HOME` moved, save/restore). It is the bulk of this module's run time; keep it this size. E8 holds the
  whole execution suite under 60 s: Task 12's and Task 13's full runs check that total; over that target, round-3
  ruling G3-2 applies: record the time, weaken no test; at twice the target the controller rules.

- [ ] **Step 1: Write the failing tests**

  Pre-checks, from the repo root in Git Bash (git and ls only, no Python):

```bash
git ls-files --eol tests/execution_evidence.py
ls execution/evidence.py
```

  Expected: `i/lf    w/lf    attr/-text            	tests/execution_evidence.py` (Task 9 created and committed it);
  then `ls: cannot access 'execution/evidence.py': No such file or directory`. A different ending, or an existing
  `execution/evidence.py`, is a drift ruling (Global Constraints 0.6): stop and rule, and record it in
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`.

  Re-read `tests/execution_evidence.py` (DRIFT RULE). Both edits below quote Task 9's text; if Task 9 as executed
  changed it, apply the same change to the current text and record a one-line ruling.

  **Edit V1.** `tests/execution_evidence.py`, anchor: the import block at the top of the file (after the module
  docstring and `from __future__ import annotations`; LF). Old text:

```python
import json
import os
from datetime import date, datetime, timezone

from core import isolation
from core.compliance import model, owner, rules
```

  New text:

```python
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
```

  **Edit V2.** `tests/execution_evidence.py`, anchor: the last three lines of the file, which end Task 9's
  `test_a_missing_unreadable_or_refused_file_gives_no_evidence` (LF). One Edit-tool replacement:
  - `old_string` = the three lines below exactly, with NO newline after the third;
  - `new_string` = those same three lines, then `\n\n\n` (one newline ending the old last line, then two empty
    lines), then the block from its first `#` up to and including
    `    assert b"broker_approval" not in raw and b"collateral_105pct" not in raw`, with NO newline after it. The
    file's existing final newline, which `old_string` left outside the match, then closes the block, so the file
    still ends in exactly one newline.

  Old text (the three lines):

```python
    os.link(path, path.parent / "second-name.jsonl")                # a hard link under the state root (A0)
    isolation._LINK_SCAN.clear()                                    # state_root() keeps its scan per process
    assert owner._live_evidence(_T9_TODAY) == frozenset()
```

  New text (the three lines, two empty lines, then this task's block):

```python
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
```

  Check the end of the file from the repo root in Git Bash; it must print `True False False` (the block ends the
  file, no blank line after it, no CR anywhere). The prefix is the QUANTGEN overlap check of contract 0.3 (Step 2
  explains it); the Python runs only when it prints nothing:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "import pathlib; b = pathlib.Path('tests/execution_evidence.py').read_bytes(); print(b.endswith(b'b\"collateral_105pct\" not in raw\n'), b.endswith(b'\n\n'), b'\r' in b)"
```

- [ ] **Step 2: Run to verify it fails**

  QUANTGEN overlap check with the PowerShell tool (it must print nothing; if it prints a process, wait and run it
  again):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash (the prefix repeats the overlap check; the command runs only when it is
  empty):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_evidence/
```

  Expected (exit code 1): a traceback ending
  `ImportError: cannot import name 'evidence' from 'execution' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\execution\__init__.py)`,
  the line

```
FAIL execution_evidence/import ImportError: cannot import name 'evidence' from 'execution' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\execution\__init__.py)
```

  then `0/1 passed, 1 failed, 0 not run`. The module now imports `execution.evidence` at the top, so Task 9's eight
  tests are inside this one import entry until Step 3 (Python 3.13 reports a missing submodule named in
  `from execution import evidence` this way, checked on the venv). Any other failure (a `SyntaxError`, an
  `ImportError` naming `tests.execution_fixtures` or `snapshot`) means Step 1 went wrong: fix it before Step 3.

- [ ] **Step 3: Implement**

  Create `execution/evidence.py` (whole file, LF). It imports only `__future__`, `math`, `datetime`,
  `core.compliance` (`model`, `owner`), `core.isolation` (`checked_target`) and `execution` (`snapshot`), all on the
  0.5 allowlist; it reads no clock (`datetime.strptime` and `astimezone` are not clock reads), opens nothing for
  writing itself (`snapshot.write_lines` does, through `checked_target`), assigns no attribute and calls no
  `getattr`. Write the word "canonical" in lower case only, in code and docstrings (test_09 and T-RO-01 match the KIS
  account-field text case-sensitively, and the upper-case spelling of that word contains it).

```python
"""D16 deposit-type evidence (E1 spec 6 "Evidence (E1-D4)"; plan E18, E33, E1R2-3): the KIS snapshot judged against
the four E1 items of core.compliance.owner.EVIDENCE_THRESHOLDS_KRW, appended as hash-chained records to
execution/evidence.jsonl. The one writer of that file, inside a poll that holds poll.lock; owner.evidence_in_force
folds it into Context.live_evidence.

A record is appended for an item only when it has none yet, when its `met` changes, or when its last record is dated
on another Asia/Seoul day than this poll (a daily heartbeat; after a clock stepped back, a re-stamp): E1R2-3, spec
rev 2, in place of one record per item per poll; the fold gives the same live_evidence either way.
collateral_105pct and broker_approval are never written. No clock: the poller passes `now`."""
from __future__ import annotations

import math
from datetime import date, datetime, timezone

from core.compliance import model, owner
from core.isolation import checked_target
from execution import snapshot

_DEPOSIT_ITEMS = ("deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m")


class EvidenceBroken(Exception):
    """evidence.jsonl does not verify (owner.evidence_chain); nothing was appended (E33). The text names a line number
    and a defect, never a value."""


def _seoul_day(utc: str) -> date:
    """The Asia/Seoul date of a stamp "YYYY-MM-DDTHH:MM:SSZ"."""
    return datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(model.KST).date()


def judge(kis: snapshot.Snapshot) -> list[tuple[str, bool, float]]:
    """(item, met, value_krw) for every E1 item the snapshot can judge, in the order of EVIDENCE_THRESHOLDS_KRW;
    nothing unless it is an ok KIS snapshot with a deposit_krw. The deposit items read deposit_krw (KIS
    dnca_tot_amt); cash_krw_30m adds each foreign cash amount at its KIS rate in prices_krw and is skipped when a rate
    is missing. A value below zero or not finite is unmet and written as 0.0: owner.evidence_chain refuses the value
    itself, and an item left unjudged would keep its last met record in force for up to 7 days."""
    if kis.venue != "kis" or not kis.ok or kis.deposit_krw is None:
        return []
    deposit = float(kis.deposit_krw)
    values = dict.fromkeys(_DEPOSIT_ITEMS, deposit)
    foreign = [c for c in kis.cash if c != "KRW"]
    if all(c in kis.prices_krw for c in foreign):
        values["cash_krw_30m"] = deposit + sum(kis.cash[c] * kis.prices_krw[c] for c in foreign)
    out = []
    for item, threshold in owner.EVIDENCE_THRESHOLDS_KRW.items():
        value = values.get(item)
        if value is not None:
            value = value if 0 <= value < math.inf else 0.0   # below zero or not finite: unmet, as 0.0 (point 3)
            out.append((item, value >= threshold, value))
    return out


def due(rows: list[dict], requirement: str, met: bool, now: datetime) -> bool:
    """E1R2-3: True when `rows` (the verified chain) hold no record of `requirement`, when its last record's `met`
    differs, or when that record is dated on another Asia/Seoul day than `now`: an earlier one (the daily heartbeat),
    or a later one after the clock stepped back (re-stamped at once, so its latest record carries the day of its last
    poll, as one record per poll would). A change of value_krw alone is never due: the fold reads only met, the
    dates and the chain."""
    today = _seoul_day(model.iso_utc(now))           # first: a naive now is ValueError, whatever rows hold
    last = next((row for row in reversed(rows) if row["requirement"] == requirement), None)
    return last is None or last["met"] != met or _seoul_day(last["utc"]) != today


def record(kis: snapshot.Snapshot, now: datetime) -> list[dict]:
    """Append the due records of this poll to evidence.jsonl, under its sidecar lock, and return them (often none).
    The file is checked (checked_target) before it is read and again before it is written; a refusal propagates (a
    crash, E33). A chain that does not verify raises EvidenceBroken and nothing is appended. A snapshot with nothing
    to judge touches no file."""
    judged = judge(kis)
    if not judged:
        return []
    utc = model.iso_utc(now)
    path = owner.evidence_path()
    with snapshot.exclusive(path):
        try:
            lines = checked_target(path, "E1 evidence log").read_bytes().splitlines(keepends=True)
        except FileNotFoundError:
            lines = []
        rows, why = owner.evidence_chain(lines)       # the same split and check as owner._live_evidence
        if why:
            raise EvidenceBroken(f"evidence.jsonl is broken ({why}); nothing appended")
        prev = rows[-1]["row_sha256"] if rows else owner.GENESIS_PREV
        new = []
        for requirement, met, value in judged:
            if not due(rows, requirement, met, now):
                continue
            body = {"seq": len(rows) + len(new) + 1, "prev_sha256": prev, "utc": utc, "requirement": requirement,
                    "met": met, "value_krw": value, "snapshot_sha256": kis.snapshot_sha256}
            new.append({**body, "row_sha256": model.sha256_hex(model.canonical_json(body))})
            prev = new[-1]["row_sha256"]
        snapshot.write_lines(path, [(model.canonical_json(row) + "\n").encode("utf-8") for row in new],
                             "E1 evidence log")
    return new
```

  Then record the two departures from contract 14 in the ledger (Design notes points 3 and 5). Use the Edit tool and
  keep LF; read the ledger first (the Edit tool refuses a file it has not read). The anchor is the
  `## Deferred minors` heading. It occurs once, so ruling lines that earlier tasks added above it stay as they are.
  Old text:

```text
## Deferred minors
```

  New text:

```text
- Task 10 (C14 judge): a value below zero or not finite is written as `(item, False, 0.0)`; contract 14's
  `(item, deposit >= threshold, deposit)` would write a line that `owner.evidence_chain` refuses (`value_krw` below
  zero, or NaN/inf refused by canonical JSON), and the chain would stay broken on every later poll.
- Task 10 (C14 due, E18, E1R2-3 wording): the heartbeat compares Seoul days with `!=`, not "earlier" (`<`), so a
  record dated after `now` (the PC clock ran ahead, then was set right) is re-stamped at once; with `<` the fold
  could keep D16 rows lifted for up to the size of the jump after the poller stops. The two agree while poll times
  never go backward; contract 14, E18 and the E1R2-3 wording take `!=` when next revised.

## Deferred minors
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check before EACH Python command below (the Git Bash prefix does it). All from the repo root in
  Git Bash. `time` after the prefix times the Python run alone: Bash prints `real`, `user` and `sys` after its
  output, and `real` is the figure to record (`tests.run_all.run` prints no seconds, run_all.py:106).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && time .venv/Scripts/python.exe -m tests.execution_acceptance execution_evidence/
```

  Expected (exit code 0; `real` about 5 to 15 s: the equivalence test, about 1.3 s for the other 21 tests on a
  sandbox copy, and the import of every suite that `tests.run_all.run` pulls in): these 22 lines in this order
  (Task 9's 8 and this task's 14), then `22/22 passed, 0 failed, 0 not run`:

```
PASS execution_evidence/test_a_broken_chain_raises_evidence_broken_and_appends_nothing
PASS execution_evidence/test_a_deposit_below_zero_is_recorded_unmet_and_tightens_at_once
PASS execution_evidence/test_a_later_unmet_record_removes_the_item_at_once
PASS execution_evidence/test_a_linked_evidence_file_is_refused_before_it_is_read
PASS execution_evidence/test_a_met_record_counts_from_the_next_asia_seoul_day
PASS execution_evidence/test_a_missing_unreadable_or_refused_file_gives_no_evidence
PASS execution_evidence/test_a_snapshot_with_nothing_to_judge_touches_no_file
PASS execution_evidence/test_broker_approval_and_collateral_are_never_written
PASS execution_evidence/test_cash_krw_30m_adds_foreign_cash_at_the_kis_rate
PASS execution_evidence/test_change_and_heartbeat_records_give_the_same_evidence_as_one_record_per_poll
PASS execution_evidence/test_due_on_synthetic_rows
PASS execution_evidence/test_every_chain_defect_gives_no_evidence_at_all
PASS execution_evidence/test_judge_meets_each_threshold_at_it_and_not_one_won_below
PASS execution_evidence/test_load_context_reads_live_evidence_and_creates_no_file
PASS execution_evidence/test_record_checks_every_target_before_it_opens_it
PASS execution_evidence/test_record_on_an_empty_file_appends_one_chained_line_per_judged_item
PASS execution_evidence/test_records_stamped_ahead_or_back_are_dated_as_late_as_the_log_allows
PASS execution_evidence/test_records_written_on_day_d_lift_on_day_d_plus_one_and_expire_when_polls_stop
PASS execution_evidence/test_the_first_poll_of_the_next_seoul_day_is_a_heartbeat_for_every_judged_item
PASS execution_evidence/test_the_latest_met_record_expires_after_seven_days
PASS execution_evidence/test_the_same_seoul_day_appends_only_a_first_record_or_a_flipped_met
PASS execution_evidence/test_vocabulary_is_the_four_deposit_items_inside_live_requirements
```

  If Task 9 as executed left a different number of its own tests, the last line is `N/N passed, 0 failed, 0 not run`
  with N that number plus 14; put that count in the Runs line below. A FAIL of
  `test_a_broken_chain_raises_evidence_broken_and_appends_nothing` ending in `OverflowError: date value out of range`
  means Task 9's `_evidence_row` lacks the `utc has no Asia/Seoul date` check (Interfaces): stop and rule; never
  catch it in evidence.py.

  Then time the equivalence test alone (the same suite imports are in its `real`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && time .venv/Scripts/python.exe -m tests.execution_acceptance execution_evidence/test_change_and_heartbeat_records_give_the_same_evidence_as_one_record_per_poll
```

  Expected (exit code 0): `PASS execution_evidence/test_change_and_heartbeat_records_give_the_same_evidence_as_one_record_per_poll`,
  then `1/1 passed, 0 failed, 0 not run`, then the three `time` lines. Record both `real` figures for Task 12's and
  Task 13's 60 s check (E8): append one line to the ledger, which ends with its `## Runs` section, with `M1` and
  `M2` replaced by the module's and the test's `real` figures as Bash printed them (for example `0m7.412s`), and
  `22/22` by the count printed if it differed:

```bash
printf '%s\n' "- Task 10: execution_evidence/ 22/22 passed, real M1; the equivalence test alone real M2 (each includes the import of every suite; E8)" >> docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
tail -n 3 docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
```

  Expected: the line just written, with the two figures in it, is the last one printed.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/
```

  Expected: only `PASS execution_guards/<name>` lines, ending `N/N passed, 0 failed, 0 not run` (exit code 0), N the
  count Task 9's last run of `execution_guards/` printed (this task adds no guard test). The guards now scan
  `execution/evidence.py`: `test_only_evidence_names_evidence_path` (it is `EVIDENCE_WRITER`, so it may),
  `test_imports_stay_on_the_allowlist`, `test_every_write_goes_through_checked_target`,
  `test_no_wall_clock_outside_poll_main`, `test_transport_is_the_only_path` and the token rules. A failure names the
  file and the text: fix evidence.py, never the guard.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected: every line `PASS`, `0 failed` and exit code 0 for each, with the same totals Task 9's Step 4c (cycle c)
  printed for these two modules. `execution/evidence.py` joins the D14 code closure through the `execution/*.py`
  seed of Task 9 (`test_code_files_is_the_import_closure` expects every `execution/*.py` by its glob), and it imports
  only files already in the closure (`core/compliance/model.py`, `owner.py`, `core/isolation.py`,
  `execution/snapshot.py`).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; from tests.acceptance import test_08_no_broker_order_path as a, test_09_no_account_credentials_requested as b, test_16_every_source_file_is_utf8_readable as c, test_18_eodhd_is_gone_from_the_runtime as d; t(); u(); a(); b(); c(); d(); print('T-RO-01 ok')"
```

  Expected: `T-RO-01 ok` (T-RO-01 and the four text scans of `runtime_py()`, which holds `execution/**/*.py` since
  Task 1, over the real tree; this calls the test functions directly, starts no `tests/run_all.py` and writes
  nothing).

  Then the text checks (git only, no overlap check needed):

```bash
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD" -- execution/evidence.py tests/execution_evidence.py
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|context_log/|reference_mode|tests\.reference|0\.4 \*" -- execution/evidence.py tests/execution_evidence.py
git grep --untracked -n -E "datetime\.now|date\.today|time\.time|monotonic|perf_counter|subprocess|importlib\.reload" -- execution/evidence.py tests/execution_evidence.py
git grep --untracked -l "evidence_path" -- execution/
git status --short
```

  Expected: the first three print nothing (exit code 1 each); the fourth prints exactly `execution/evidence.py`;
  `git status --short` prints exactly these lines, in git's order (tracked changes first, untracked last), and
  nothing else (nothing under `qa/`; `__pycache__/` is ignored, .gitignore:3):

```
 M docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
 M tests/execution_evidence.py
?? execution/evidence.py
```

- [ ] **Step 5: Commit**

```bash
git add execution/evidence.py tests/execution_evidence.py docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (all three files are LF). Then commit. In the trailer, replace
  `<the committing model>` with the name of the model that writes this commit, for example `Claude Sonnet 5.5` or
  `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "feat(execution): D16 evidence writer, on change and a daily heartbeat" -m "E1 Task 10 (spec 6, E18, E33; E1R2-3, spec rev 2): execution/evidence.py judges the KIS snapshot against the four deposit items and appends hash-chained evidence.jsonl records only for a first record, a met change or a poll on another Seoul day; the tests prove the fold reads the same live_evidence as one record per poll, a clock stepped back included, and the ledger records the two departures from contract 14. evidence.py joins the D14 code hash: once the owner has a signing key, act 2 re-signs." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
```
