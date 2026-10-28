### Task 9: Compliance changes, signed (`Context.live_evidence`, the evidence fold in `owner.py`, the D16 rule, `execution/` in the D14 code hash)

**Files:**
- Modify: `core/compliance/model.py` (anchors: the last two fields of `class Context`; the body of `seal_context`;
  LF)
- Modify: `core/compliance/owner.py` (anchors: the `return model.seal_context(` call that ends `_context`, right
  after which the new evidence block goes; the docstring and `todo` seed line of `code_files`; LF)
- Modify: `core/compliance/gate.py` (anchor: the D16 `if row.requires_live:` block in `_row_check`; LF)
- Modify: `tools/signer/sign.py` (anchors: the section comment "The D14 code hash: a copy of owner.code_files (P6)"
  above `_RECORD_DISTS`; the docstring and `todo` seed line of the signer's `code_files`; LF)
- Modify: `tests/compliance_model.py` (anchor: the last entry of the `changes` dict in
  `test_seal_context_registers_and_hand_built_is_refused`; LF)
- Modify: `tests/compliance_gate.py` (anchors: the TQQQ / 252670 assert in `test_verdicts_follow_the_rows`; the loop
  of `test_d16_rows_stay_blocked_with_every_owner_flag_signed`, right after which the new test goes; LF)
- Modify: `tests/compliance_store.py` (anchor: the docstring and `expected` set of
  `test_code_files_is_the_import_closure`; LF)
- Modify: `tests/compliance_signer.py` (anchor: the `core/compliance` subset assert of `test_code_files_match_owner`;
  LF)
- Create: `tests/execution_evidence.py` (LF, UTF-8, no BOM; Task 10 appends to it)
- Modify, only when this task records a drift ruling (Steps 1a, 3d or 4d, or an anchor an earlier plan moved):
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (anchor: the `## Deferred minors`
  heading; one line above it, in the `## Drift rulings` section; LF)
- Test: `tests/compliance_model.py`, `tests/execution_evidence.py`, `tests/compliance_store.py`,
  `tests/compliance_signer.py`, `tests/compliance_gate.py`

This is the only task that edits the compliance package. It runs in four red-green cycles, a to d (model, evidence
fold, code closure, gate; Steps 1a to 4a through 1d to 4d), and commits once in Step 5. Every edit of an existing
file follows the DRIFT RULE (Global Constraints 0.6): re-read the file first; the anchor is the quoted old text, a
line number only a hint at `5816d3c`. If the old text differs only because the compliance follow-up plan or the odds
plan changed it, apply the same change to the current text, keep their behaviour, and add a one-line ruling to
`docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`; if the change no longer makes sense, stop
and rule.

**Interfaces:**
- Consumes:
  - `core.compliance.model` (repo): `Context`, `seal_context(**fields)`, `is_sealed(ctx)`, `canonical_json(obj)`,
    `sha256_hex(data)`, `Positions(equity_krw)`, `KST`, `ALLOW`, `BLOCK`; the module import `dataclasses` (model.py
    top).
  - `core.compliance.owner` (repo): `GENESIS_PREV` (`"0" * 64`), `_no_duplicates(pairs)`, `_utc(v)`, `_number(v)`,
    `_hex64(v)`, `_seoul_date(utc) -> date`; the module-level names `json`, `Path`, `state_root` (from
    `core.isolation`), `_dt` (`import datetime as _dt`), `model`, `canonical_json`, `sha256_hex`;
    `load_context(now, positions, *, session_id=None)`, `_context(day, now_utc, positions, session_id)`,
    `code_files(repo_root)`, `code_hash(repo_root)`.
  - `core.compliance.rules` (repo): `LIVE_REQUIREMENTS`, `OWNER_REQUIREMENTS`; `Row.requires_live`, `Row.id`.
  - `core.isolation` (repo): `state_root()`, `_LINK_SCAN` (the per-process scan memo; tests only).
  - `tests/compliance_gate.py` (repo): `_t8_with_instruments`, `_t8_fixture`, `_t8_owner`; `tests.compliance_fixtures`
    as `F`: `F.ctx(**overrides)`, `F.approved()`, `F.intent(**overrides)`.
  - Task 1: `tests/execution_acceptance.py` (`MODULES` already lists `"execution_evidence"`; `_wrap` runs each test
    in `hermetic()`, a fresh `temp_home()` and `isolated(home)`); `tests/execution_guards.py` (its process rule scans
    every `tests/execution_*.py`, this new file included).
  - Tasks 1 to 8: the files `execution/__init__.py`, `keys.py`, `transport.py`, `kis_inquiry.py`, `upbit_inquiry.py`,
    `okx_inquiry.py`, `snapshot.py`, `positions.py` (here only as members of the code closure).
- Produces:
  - `model.Context.live_evidence: frozenset = frozenset()` (between `exposure` and `ctx_hash`);
    `model.seal_context(**fields)` now hashes every field of `Context` except `ctx_hash`, defaults included.
  - `core/compliance/owner.py`: `EVIDENCE_THRESHOLDS_KRW` (a `MappingProxyType`, in this order: `deposit_krw_10m`
    10,000,000.0, `deposit_krw_15m` 15,000,000.0, `deposit_krw_20m` 20,000,000.0, `cash_krw_30m` 30,000,000.0),
    `EVIDENCE_KEYS = ("seq", "prev_sha256", "utc", "requirement", "met", "value_krw", "snapshot_sha256")`,
    `EVIDENCE_MAX_AGE_DAYS = 7`, `evidence_path() -> Path` (`state_root() / "execution" / "evidence.jsonl"`, creates
    nothing), `evidence_chain(lines: list[bytes]) -> tuple[list[dict], str]` (`(rows, "")` when sound, else
    `([], "line N: <defect>")`, the defect named by field, never by value; never raises; one check stricter than
    the list in contract 13.3: a `utc` with no Asia/Seoul date, `9999-12-31T15:00:00Z` and later, is the defect
    `utc has no Asia/Seoul date`, because the fold and Task 10's `due` date every row it returns),
    `evidence_in_force(lines: list[bytes], today: date) -> frozenset[str]` (E18; never raises),
    `_live_evidence(day: date) -> frozenset[str]` (creates nothing). Private helpers of this task (not in the
    contract, so private): `_EVIDENCE_LINE_KEYS` (`EVIDENCE_KEYS` plus `"row_sha256"`, a frozenset) and
    `_evidence_row(n: int, line, prev: str) -> dict` (one line checked; `ValueError` naming the defect).
  - `owner._context` seals `live_evidence=_live_evidence(day)`; the internal-error fallback of `load_context` keeps
    the default `frozenset()`.
  - Gate reason for a D16 row whose `requires_live` items are not all in `ctx.live_evidence`:
    `f"needs live broker evidence: {row.id}: {', '.join(missing)}"`, `missing` sorted.
  - `owner.code_files` and `tools/signer/sign.py` `code_files` seed `core/compliance/*.py`, `core/odds/*.py` and
    `execution/*.py` (non-recursive); the D14 code hash now covers every `execution/*.py`.
  - For Task 10 (`tests/execution_evidence.py`, reused, never redefined): `_T9_SNAP` (`"5" * 64`), `_T9_MET`
    (100,000,000.0), `_T9_TODAY` (`date(2026, 10, 24)`), `_t9_sealed(body: dict) -> bytes`,
    `_t9_body(seq, prev, utc, requirement, met, value_krw=None) -> dict`, `_t9_chain(*records) -> list[bytes]`,
    `_t9_prev(lines) -> str`. Task 10's `evidence.record` checks the chain with `owner.evidence_chain` and puts its
    `why` string into the `EvidenceBroken` text.

**Plan decisions used:** E1 (order and the DRIFT RULE), E4 (canonical JSON, the evidence line format, the fold in
`owner.py`, `load_context` reads `state_root()/"execution"/"evidence.jsonl"`, a missing, refused or unreadable file is
`frozenset()`), E5 (the `Context` field, the gate reason, the `code_files` seeds, the signer lockstep, the closure
tests), E18 (vocabulary, thresholds, next Seoul day, tighten at once, 7-day expiry, dated as late as the log allows,
a broken chain is empty), E24 (the `Positions(equity_krw=1.0)` placeholder `load_context` is called with), E1R2-3
(the fold is unchanged by the change-and-heartbeat writer of Task 10).

- [ ] **Step 1a: Write the failing test (cycle a of 4: the `Context` field and `seal_context`)**

  First the pre-checks, from the repo root in Git Bash (git, grep and test only, no Python). The owner key, before
  anything else (owner gate 2 of the header: this task changes the D14 code hash):

```bash
test -f core/compliance/owner_pubkey.pem && echo "owner key present" || echo "no owner key"
```

  Expected: `no owner key` (nothing is signed yet, so the hash change blocks nothing). If it prints
  `owner key present`, stop before any edit and tell the owner: this task changes the D14 code hash, so from its
  commit on the checked-out code counts as unsigned (the gate blocks new exposure, the daily compliance check alerts,
  and KIS stays unread, E42) until they re-verify the signer copy and sign again (E1 owner act 5). End the message
  with: "The real odds are unchanged by E1: no plan without a real edge that keeps the floor can beat about 1 in
  1,000 (1 in 2,000 with the floor at half the stake), and the research estimates the practical chance of 1,000x in
  a month at 0.01% or less. This is not legal or investment advice; I am not a licensed advisor." Go on only after
  their yes in chat.

  Line endings:

```bash
git ls-files --eol core/compliance/model.py core/compliance/owner.py core/compliance/gate.py tools/signer/sign.py tests/compliance_gate.py tests/compliance_model.py tests/compliance_store.py tests/compliance_signer.py
```

  Expected: eight lines, each starting `i/lf    w/lf    attr/-text`. Any other ending is a drift ruling (0.6).

  The execution files the closure will take in (Tasks 1 to 8):

```bash
ls execution/*.py
```

  Expected exactly: `execution/__init__.py`, `execution/keys.py`, `execution/kis_inquiry.py`,
  `execution/okx_inquiry.py`, `execution/positions.py`, `execution/snapshot.py`, `execution/transport.py`,
  `execution/upbit_inquiry.py`. A missing one means an earlier task is not done: stop.

  Every pinned use of the old D16 reason (contract 13.5):

```bash
grep -rn --include=*.py "needs live broker evidence (execution spec)" tests/ core/
```

  Expected at `5816d3c` exactly three hits: `core/compliance/gate.py` (`_row_check`), and `tests/compliance_gate.py`
  twice (`test_verdicts_follow_the_rows`, `test_d16_rows_stay_blocked_with_every_owner_flag_signed`). Each is
  changed in this task. Any other hit (an earlier plan's test) is a drift ruling: change its expected text to the
  new reason, built as in Edit G1 of Step 3d, and record it with the file's path in its ledger line (Step 5 adds
  that file); stop and rule if it is not a pinned reason. (`--include=*.py` keeps
  the `__pycache__` binaries out.)

  Every pinned hash value (contract 0.6 "Model users"): `seal_context`'s change alters every `ctx_hash` once, and with
  it every `Decision.decision_id` and `Screening.screening_hash` built from a context.

```bash
git grep -n -E "[0-9a-f]{64}" -- tests core
```

  Expected at `5816d3c`: `tests/compliance_model.py:156` (the sha256 of `"abc"`) and six lines of
  `tests/macro_tf_data.py` (`:32` to `:37`, data-file hashes). After the odds plan, also `tests/odds_report.py`
  `_CATALOGUE_SHA256` (odds Task 12: the sha256 of the catalogue text, not of a context): record it as checked. A hit
  beyond these, in a file the compliance follow-up or the odds plan added or changed, is a drift ruling: if the value
  is derived from a sealed `Context` (a `ctx_hash`, a `decision_id`, a `screening_hash`, an odds card or report hash
  over a context), stop and rule before editing; otherwise record it as checked.

  The two suite baselines Step 4d compares against, taken before any edit. Each is a Python run: first the overlap
  check (the PowerShell block of Step 2a; it must print nothing), then from the repo root in Git Bash one command
  line, keyless (the checkout restores the results file). The compliance suite (timeout: 300000):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Overlap check, then the odds suite (registered by the odds plan; `5816d3c` has none; timeout: 600000):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite odds; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected for each: no `FAIL` line, a summary `P/T passed, 0 failed, K not run;` followed by the results-file path,
  then `exit 0`. Keep both summary lines for Step 4d (the compliance one reads `315/317 passed, 0 failed, 2 not run`
  at `5816d3c` counts). A `FAIL` line here means the tree is red before this task: stop and rule.

  Now the test. **Edit T0.** `tests/compliance_model.py`, anchor: the last entry of the `changes` dict of
  `test_seal_context_registers_and_hand_built_is_refused` (hint :95), which gets a `live_evidence` case. Old text
  (Edit tool; LF):

```python
               "exposure": {"upbit": model.Exposure(held_krw=1.0)}}
```

  New text:

```python
               "exposure": {"upbit": model.Exposure(held_krw=1.0)}, "live_evidence": frozenset({"deposit_krw_10m"})}
```

- [ ] **Step 2a: Run to verify it fails (cycle a)**

  QUANTGEN overlap check with the PowerShell tool (it must print nothing; if it prints a process, wait and run it
  again):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_model/
```

  Expected: a traceback, then among the PASS lines exactly one FAIL line

```
FAIL compliance_model/test_seal_context_registers_and_hand_built_is_refused AssertionError: a new Context field needs a case
```

  and the last line `9/10 passed, 1 failed, 0 not run` (the module's count at `5816d3c`; if an earlier plan added a
  test here, both numbers grow by the same amount), exit code 1.

- [ ] **Step 3a: Implement (cycle a)**

  Both edits go in together: with the field alone the same test still fails, one assert earlier, at
  `again.ctx_hash == sealed.ctx_hash` (`AssertionError` with no text), because today's `seal_context` hashes only the
  fields it is passed: `F.ctx()` does not pass `live_evidence`, the test's rebuilt `fields` do (contract 13.1).

  **Edit M1.** `core/compliance/model.py`, anchor: the last two fields of `class Context` (hint :177-178; LF). Old
  text:

```python
    exposure: Mapping[str, Exposure]
    ctx_hash: str = ""                                # set by seal_context
```

  New text:

```python
    exposure: Mapping[str, Exposure]
    live_evidence: frozenset = frozenset()            # E1: live D16 requirements in force (owner.evidence_in_force)
    ctx_hash: str = ""                                # set by seal_context
```

  **Edit M2.** `core/compliance/model.py`, anchor: the body of `seal_context` (hint :232-233; its docstring stays;
  LF). Old text:

```python
    fields.pop("ctx_hash", None)
    ctx = Context(**fields, ctx_hash=sha256_hex(canonical_json(fields)))
```

  New text:

```python
    fields.pop("ctx_hash", None)
    draft = Context(**fields)                         # defaults filled in; an unknown field is still a TypeError
    body = {f.name: getattr(draft, f.name) for f in dataclasses.fields(Context) if f.name != "ctx_hash"}
    ctx = Context(**body, ctx_hash=sha256_hex(canonical_json(body)))
```

  The next line, `_SEALED[id(ctx)] = ctx`, stays. A NaN still raises `ValueError` in `canonical_json`, and a missing
  or unknown field still raises `TypeError` in the `draft` call. The docstring ("hash every field into ctx_hash") is
  now true of default fields too. `dataclasses` is already imported at the top of model.py.

- [ ] **Step 4a: Run to verify it passes (cycle a)**

  Overlap check (the PowerShell block of Step 2a; it must print nothing), then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_model/
```

  Expected, ending: `10/10 passed, 0 failed, 0 not run` (the Step 2a total, every entry PASS), exit code 0.

- [ ] **Step 1b: Write the failing tests (cycle b of 4: the evidence fold and `load_context`)**

  **Whole file `tests/execution_evidence.py`** (create; LF, UTF-8, no BOM; Task 10 appends after its last line):

```python
"""D16 live evidence (E1 spec 6 and 8; plan Tasks 9 and 10). Task 9: the pure fold owner.evidence_in_force over
execution/evidence.jsonl, its chain check owner.evidence_chain, and load_context reading the file into
Context.live_evidence. Task 10 appends the writer's tests. Lines are built here without owner.py, as
tests.compliance_fixtures.signed_entry builds owner-log lines. Helpers are prefixed `_t9_`; Task 10 reuses them."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

from core import isolation
from core.compliance import model, owner, rules

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
```

- [ ] **Step 2b: Run to verify it fails (cycle b)**

  Overlap check (the PowerShell block of Step 2a; it must print nothing), then:

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_evidence/
```

  Expected: a traceback per test, then these 8 lines in this order, then `0/8 passed, 8 failed, 0 not run` (exit
  code 1):

```
FAIL execution_evidence/test_a_later_unmet_record_removes_the_item_at_once AttributeError: module 'core.compliance.owner' has no attribute 'evidence_in_force'
FAIL execution_evidence/test_a_met_record_counts_from_the_next_asia_seoul_day AttributeError: module 'core.compliance.owner' has no attribute 'evidence_in_force'
FAIL execution_evidence/test_a_missing_unreadable_or_refused_file_gives_no_evidence AttributeError: module 'core.compliance.owner' has no attribute 'evidence_path'
FAIL execution_evidence/test_every_chain_defect_gives_no_evidence_at_all AttributeError: module 'core.compliance.owner' has no attribute 'evidence_chain'
FAIL execution_evidence/test_load_context_reads_live_evidence_and_creates_no_file AssertionError: (frozenset(), frozenset())
FAIL execution_evidence/test_records_stamped_ahead_or_back_are_dated_as_late_as_the_log_allows AttributeError: module 'core.compliance.owner' has no attribute 'evidence_in_force'
FAIL execution_evidence/test_the_latest_met_record_expires_after_seven_days AttributeError: module 'core.compliance.owner' has no attribute 'evidence_in_force'
FAIL execution_evidence/test_vocabulary_is_the_four_deposit_items_inside_live_requirements AttributeError: module 'core.compliance.owner' has no attribute 'EVIDENCE_THRESHOLDS_KRW'
```

  (`load_context` already seals the cycle-a default `live_evidence=frozenset()`; it does not read the file yet.)

- [ ] **Step 3b: Implement (cycle b)**

  **Edit O1.** `core/compliance/owner.py`, anchor: the `return model.seal_context(` call that ends `_context` (hint
  :1014-1017). The fallback call inside `load_context`, which starts
  `return model.seal_context(date=day, active=model.ApprovedState.invalid(why),`, is a different call and stays as it
  is, with the default `live_evidence`. The new text puts the evidence block right after `_context`. At `5816d3c`
  that is the end of the file; if an earlier plan added code after `_context` (the odds plan adds
  `_calendar_approval` and `calendar_in_force`), the block still goes right after `_context`, before that code, with
  no other change: module-level names resolve at call time. Old text (LF):

```python
    return model.seal_context(
        date=day, active=active, snapshot=snapshot, owner=owner, code_hash=current, code_signed=signed,
        session=model.SessionState(session_id=session_id, armed=session_id in owner.armed_sessions),
        equity_krw=equity, holdings=holdings, shorts=shorts, exposure=exposure)
```

  New text (at the end of the file it keeps its single trailing newline; before other code, two blank lines follow
  the block, as between every top-level def here):

```python
    return model.seal_context(
        date=day, active=active, snapshot=snapshot, owner=owner, code_hash=current, code_signed=signed,
        session=model.SessionState(session_id=session_id, armed=session_id in owner.armed_sessions),
        equity_krw=equity, holdings=holdings, shorts=shorts, exposure=exposure, live_evidence=_live_evidence(day))


# --------------------------------------------------------------------------- #
# Live D16 evidence (E1 spec 6 and 8): the pure fold of execution/evidence.jsonl
# --------------------------------------------------------------------------- #
from types import MappingProxyType  # noqa: E402

EVIDENCE_THRESHOLDS_KRW = MappingProxyType({"deposit_krw_10m": 10_000_000.0, "deposit_krw_15m": 15_000_000.0,
                                            "deposit_krw_20m": 20_000_000.0, "cash_krw_30m": 30_000_000.0})
EVIDENCE_KEYS = ("seq", "prev_sha256", "utc", "requirement", "met", "value_krw", "snapshot_sha256")
EVIDENCE_MAX_AGE_DAYS = 7
_EVIDENCE_LINE_KEYS = frozenset(EVIDENCE_KEYS) | {"row_sha256"}


def evidence_path() -> Path:
    """`<state root>/execution/evidence.jsonl`, which only execution/evidence.py writes. Creates nothing."""
    return state_root() / "execution" / "evidence.jsonl"


def _evidence_row(n: int, line, prev: str) -> dict:
    """Line `n` of evidence.jsonl checked against the row_sha256 of the line before it; ValueError naming the first
    defect by field name, never by value."""
    if not isinstance(line, bytes) or not line.endswith(b"\n") or b"\n" in line[:-1] or b"\r" in line:
        raise ValueError("not one newline-terminated line")
    try:
        obj = json.loads(line[:-1].decode("utf-8"), object_pairs_hook=_no_duplicates)
    except ValueError:                                  # UnicodeDecodeError and a duplicate key included
        raise ValueError("unreadable") from None
    if not isinstance(obj, dict):
        raise ValueError("not a JSON object")
    try:
        same = canonical_json(obj).encode("utf-8") == line[:-1]
    except (TypeError, ValueError):
        same = False
    if not same:
        raise ValueError("not its canonical JSON")
    if set(obj) != _EVIDENCE_LINE_KEYS:
        raise ValueError("not exactly the evidence keys")
    if type(obj["seq"]) is not int or obj["seq"] != n:
        raise ValueError("seq does not count up from 1")
    if obj["prev_sha256"] != prev:
        raise ValueError("prev_sha256 does not chain to the line before")
    if not _utc(obj["utc"]):
        raise ValueError("utc is not YYYY-MM-DDTHH:MM:SSZ")
    try:
        _seoul_date(obj["utc"])
    except OverflowError:                               # 9999-12-31T15:00:00Z and later: past date.max in Seoul
        raise ValueError("utc has no Asia/Seoul date") from None
    if not isinstance(obj["requirement"], str) or obj["requirement"] not in EVIDENCE_THRESHOLDS_KRW:
        raise ValueError("requirement is not an E1 evidence item")
    if type(obj["met"]) is not bool:
        raise ValueError("met is not true or false")
    if not _number(obj["value_krw"]) or obj["value_krw"] < 0:
        raise ValueError("value_krw is not a number at or above zero")
    if obj["met"] != (obj["value_krw"] >= EVIDENCE_THRESHOLDS_KRW[obj["requirement"]]):
        raise ValueError("met disagrees with value_krw")
    if not _hex64(obj["snapshot_sha256"]):
        raise ValueError("snapshot_sha256 is not lower-case hex")
    if obj["row_sha256"] != sha256_hex(canonical_json({k: obj[k] for k in EVIDENCE_KEYS})):
        raise ValueError("row_sha256 does not recompute")
    return obj


def evidence_chain(lines: list[bytes]) -> tuple[list[dict], str]:
    """(every evidence.jsonl row in order, "") when every line is sound, else ([], "line N: <defect>"). Never raises.
    execution/evidence.py checks the chain with it before it appends."""
    rows, prev, n = [], GENESIS_PREV, 0
    try:
        for n, line in enumerate(lines, start=1):
            rows.append(_evidence_row(n, line, prev))
            prev = rows[-1]["row_sha256"]
    except ValueError as exc:
        return [], f"line {n}: {exc}"
    except Exception as exc:                            # RecursionError on a deeply nested line, and the like
        return [], f"line {n}: {type(exc).__name__}"
    return rows, ""


def evidence_in_force(lines: list[bytes], today: _dt.date) -> frozenset[str]:
    """The live D16 items in force on Asia/Seoul `today` (E1 spec 6): an item counts when its latest record is met,
    is stamped on or before `today` and at most EVIDENCE_MAX_AGE_DAYS before it, and the unbroken run of met records
    ending there began before `today`. A record is dated as late as the log allows, by the latest Asia/Seoul date
    among the lines up to and including it (as _owner_fold dates a loosening), so a record stamped back counts from
    no earlier than the line before it. A later unmet record removes the item at once. A broken chain gives
    frozenset(). Never raises."""
    try:
        rows, why = evidence_chain(lines)
        if why:
            return frozenset()
        late, seen = [], _dt.date.min
        for row in rows:
            seen = max(seen, _seoul_date(row["utc"]))
            late.append(seen)
        out = set()
        for item in EVIDENCE_THRESHOLDS_KRW:
            mine = [i for i, row in enumerate(rows) if row["requirement"] == item]
            if not mine or not rows[mine[-1]]["met"]:
                continue
            on = _seoul_date(rows[mine[-1]]["utc"])
            if not (on <= today and (today - on).days <= EVIDENCE_MAX_AGE_DAYS):
                continue
            first = mine[-1]
            for i in reversed(mine):
                if not rows[i]["met"]:
                    break
                first = i
            if late[first] < today:
                out.add(item)
        return frozenset(out)
    except Exception:
        return frozenset()


def _live_evidence(day: _dt.date) -> frozenset[str]:
    """evidence_in_force over execution/evidence.jsonl for load_context: frozenset() when the file is missing,
    unreadable or refused (A0). Creates nothing."""
    try:
        path = evidence_path()
        if not path.exists():
            return frozenset()
        lines = path.read_bytes().splitlines(keepends=True)
    except (OSError, RuntimeError):                     # RuntimeError: the state root holds a link (A0)
        return frozenset()
    return evidence_in_force(lines, day)
```

  `MappingProxyType` is already imported by the `load_context` section above (`from types import MappingProxyType
  # noqa: E402`); the block imports it again, as each section of this file imports what it uses. Every other name
  (`json`, `Path`, `state_root`, `_dt`, `GENESIS_PREV`, `_no_duplicates`, `_utc`, `_number`, `_hex64`,
  `_seoul_date`, `canonical_json`, `sha256_hex`) is already bound at module level. The `utc` date check after
  `_utc` is the one check beyond the list in contract 13.3 (see Interfaces): `_utc` accepts `9999-12-31T15:00:00Z`,
  whose Asia/Seoul date would be past `date.max` (`OverflowError`). The block reads no clock (the day
  comes from `load_context`'s `now`), writes nothing, holds `canonical` only in lower case, and names none of the
  follow-up closure scan's route names (`setattr`, `vars`, `globals`, `modules`, `__dict__`, ...), so owner.py keeps
  its `TYPE_CHECKING` and `__main__` skips.

- [ ] **Step 4b: Run to verify it passes (cycle b)**

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_evidence/
```

  Expected: these 8 lines in this order, then `8/8 passed, 0 failed, 0 not run` (exit code 0):

```
PASS execution_evidence/test_a_later_unmet_record_removes_the_item_at_once
PASS execution_evidence/test_a_met_record_counts_from_the_next_asia_seoul_day
PASS execution_evidence/test_a_missing_unreadable_or_refused_file_gives_no_evidence
PASS execution_evidence/test_every_chain_defect_gives_no_evidence_at_all
PASS execution_evidence/test_load_context_reads_live_evidence_and_creates_no_file
PASS execution_evidence/test_records_stamped_ahead_or_back_are_dated_as_late_as_the_log_allows
PASS execution_evidence/test_the_latest_met_record_expires_after_seven_days
PASS execution_evidence/test_vocabulary_is_the_four_deposit_items_inside_live_requirements
```

- [ ] **Step 1c: Write the failing tests (cycle c of 4: `execution/*.py` in the D14 code closure)**

  **Edit T1.** `tests/compliance_store.py`, anchor: the docstring and the `expected` set of
  `test_code_files_is_the_import_closure` (hint :130-140; LF). Old text:

```python
    """P6 on the real tree: core/__init__.py, core/isolation.py, core/compliance/*.py, core/odds/*.py and the RECORD
    files of PyYAML and cryptography; never config.py or data/ (the import allowlist keeps the closure small)."""
    files = owner.code_files(ROOT)
    names = [name for name, _ in files]
    assert names == sorted(set(names)), "not sorted, or a repeat"
    repo = {name for name in names if not name.startswith("venv:")}
    expected = {"core/__init__.py", "core/isolation.py"} | {
        f"core/{sub}/{p.name}" for sub in ("compliance", "odds") for p in (ROOT / "core" / sub).glob("*.py")}
    assert repo == expected, sorted(repo ^ expected)
    assert "config.py" not in repo and not any(name.startswith("data/") for name in repo)
```

  New text:

```python
    """P6 on the real tree: core/__init__.py, core/isolation.py, core/compliance/*.py, core/odds/*.py, execution/*.py
    (E1 spec 8) and the RECORD files of PyYAML and cryptography; never config.py, data/, core/quant/, core/calendars/
    or core/engine/ (the import allowlists keep the closure small)."""
    files = owner.code_files(ROOT)
    names = [name for name, _ in files]
    assert names == sorted(set(names)), "not sorted, or a repeat"
    repo = {name for name in names if not name.startswith("venv:")}
    expected = {"core/__init__.py", "core/isolation.py"} | {
        f"core/{sub}/{p.name}" for sub in ("compliance", "odds") for p in (ROOT / "core" / sub).glob("*.py")} | {
        f"execution/{p.name}" for p in (ROOT / "execution").glob("*.py")}
    assert repo == expected, sorted(repo ^ expected)
    assert "config.py" not in repo and not any(name.startswith("data/") for name in repo)
    assert not any(name.startswith(("core/quant/", "core/calendars/", "core/engine/")) for name in repo), repo
```

  **Edit T2.** `tests/compliance_signer.py`, anchor: the `core/compliance` subset assert of
  `test_code_files_match_owner` (hint :637; the follow-up plan rewrites the synthetic tree further down the same
  function, which this edit does not touch; LF). Old text:

```python
    assert {f"core/compliance/{p.name}" for p in (ROOT / "core" / "compliance").glob("*.py")} <= paths, paths
```

  New text:

```python
    assert {f"core/compliance/{p.name}" for p in (ROOT / "core" / "compliance").glob("*.py")} <= paths, paths
    assert {f"execution/{p.name}" for p in (ROOT / "execution").glob("*.py")} <= paths, paths      # E1 spec 8
    assert not any(p.startswith(("core/quant/", "core/calendars/", "core/engine/")) for p in paths), paths
```

  (The next line of the function, `assert "config.py" not in paths and not any(p.startswith("data/") ...`, already
  keeps `config.py` and `data/` out.)

- [ ] **Step 2c: Run to verify it fails (cycle c)**

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: a traceback, then among the PASS lines exactly one FAIL line

```
FAIL compliance_store/test_code_files_is_the_import_closure AssertionError: ['execution/__init__.py', 'execution/keys.py', 'execution/kis_inquiry.py', 'execution/okx_inquiry.py', 'execution/positions.py', 'execution/snapshot.py', 'execution/transport.py', 'execution/upbit_inquiry.py']
```

  and the last line `28/29 passed, 1 failed, 0 not run` at `5816d3c` counts (the odds plan adds `calendar_in_force`
  tests to this module, so the totals are larger, still with exactly this one FAIL), exit code 1.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected: a traceback, then among the PASS lines exactly one FAIL line, which starts
  `FAIL compliance_signer/test_code_files_match_owner AssertionError: {` and prints the closure's path set (names
  under `core/` and the two `venv:` RECORD rows, no name under `execution/`; the first assert, `mine == theirs`,
  still holds because neither copy changed yet), and the last line `36/37 passed, 1 failed, 0 not run` at `5816d3c`
  counts (`37/38` after the follow-up plan's added test), exit code 1.

- [ ] **Step 3c: Implement (cycle c)**

  owner.py and the signer's copy change in lockstep: with Edit O2 alone, `test_code_files_match_owner` fails at its
  first assert, `mine == theirs`, listing the eight `execution/` rows only owner.py then has. The docstring and the
  comment are rewrapped to 120 columns (the edited first lines would otherwise be 130).

  **Edit O2.** `core/compliance/owner.py`, anchor: the docstring and the `todo` seed line of `code_files` (hint
  :767-773; the loop below stays). Old text (LF):

```python
    """Sorted (relative POSIX path, sha256) of the D14 code closure (P6): core/compliance/*.py and core/odds/*.py,
    every in-repo file they import at any depth, every ancestor package __init__.py, and the RECORD files of the
    cryptography and PyYAML installs of the running interpreter as venv:<dist>-<version>.dist-info/RECORD (absent
    when not installed)."""
    root = Path(repo_root)
    todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]
```

  New text:

```python
    """Sorted (relative POSIX path, sha256) of the D14 code closure (P6): core/compliance/*.py, core/odds/*.py and
    execution/*.py, every in-repo file they import at any depth, every ancestor package __init__.py, and the RECORD
    files of the cryptography and PyYAML installs of the running interpreter as venv:<dist>-<version>.dist-info/RECORD
    (absent when not installed)."""
    root = Path(repo_root)
    todo = [p for base in (root / "core" / "compliance", root / "core" / "odds", root / "execution")
            for p in sorted(base.glob("*.py"))]
```

  **Edit S1.** `tools/signer/sign.py`, anchor: the section comment above `_RECORD_DISTS = ("cryptography", "PyYAML")`
  (hint :598-601; the follow-up plan keeps it, its contract 6.3; LF). Old text:

```python
# The D14 code hash: a copy of owner.code_files (P6). core/compliance and core/odds .py files, every in-repo file
# they import at any depth (function bodies included), every ancestor package __init__.py, and the RECORD files of
# the cryptography and PyYAML installs. An `if` body that never runs at import is skipped (see _skipped); every
# other body is scanned.
```

  New text:

```python
# The D14 code hash: a copy of owner.code_files (P6). core/compliance, core/odds and execution .py files, every
# in-repo file they import at any depth (function bodies included), every ancestor package __init__.py, and the
# RECORD files of the cryptography and PyYAML installs. An `if` body that never runs at import is skipped (see
# _skipped); every other body is scanned.
```

  **Edit S2.** `tools/signer/sign.py`, anchor: the docstring and `todo` seed line of the signer's `code_files` (hint
  :691-693; LF). Old text:

```python
    """Sorted (relative POSIX path, sha256) of the D14 closure, with venv:<dist>-<version>.dist-info/RECORD rows."""
    root = Path(repo_root)
    todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]
```

  New text:

```python
    """Sorted (relative POSIX path, sha256) of the D14 closure, with venv:<dist>-<version>.dist-info/RECORD rows."""
    root = Path(repo_root)
    todo = [p for base in (root / "core" / "compliance", root / "core" / "odds", root / "execution")
            for p in sorted(base.glob("*.py"))]
```

  A tree with no `execution/` folder (the synthetic trees of `tests/compliance_store.py` and
  `tests/compliance_signer.py`) seeds nothing from it: `Path.glob` on a missing folder yields nothing. Neither file's
  `_binds`, `_typing_flag`, `_guards`, `_skipped`, `_import_nodes`, `_module_file` or `_repo_imports` changes, so the
  follow-up's source-equality test of those helpers stays green.

- [ ] **Step 4c: Run to verify it passes (cycle c)**

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected, ending: `29/29 passed, 0 failed, 0 not run` at `5816d3c` counts (the Step 2c total, every entry PASS),
  exit code 0.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected, ending: `37/37 passed, 0 failed, 0 not run` at `5816d3c` counts (`38/38` after the follow-up plan; the
  Step 2c total, every entry PASS), exit code 0.

- [ ] **Step 1d: Write the failing tests (cycle d of 4: the D16 rule reads `ctx.live_evidence`)**

  **Edit T3.** `tests/compliance_gate.py`, anchor: the TQQQ / 252670 assert of `test_verdicts_follow_the_rows` (hint
  :582; LF). Old text:

```python
            "needs live broker evidence (execution spec): KR-KIS-ETP-LEV" in d.reasons, (symbol, d.reasons)
```

  New text:

```python
            "needs live broker evidence: KR-KIS-ETP-LEV: deposit_krw_10m" in d.reasons, (symbol, d.reasons)
```

  **Edit T4.** `tests/compliance_gate.py`, anchor: the loop of `test_d16_rows_stay_blocked_with_every_owner_flag_signed`
  from its `every = F.ctx(` line to its last assert (hint :917-923). The new text ends with the new test, so it sits
  right after this one (at `5816d3c` before `test_leverage_above_max_leverage_blocks`; LF). Old text:

```python
    every = F.ctx(active=state, owner=_t8_owner(flags=frozenset(rules.OWNER_REQUIREMENTS)))
    for row_id, i in (("KR-KIS-SHORT", kis("005930", action="sell_short")), ("KR-KIS-ETP-LEV", kis("252670")),
                      ("KR-KIS-SINGLE-ETP", kis("ZSINGLE")), ("KR-KIS-KRX-DERIV", kis("ZFUT")),
                      ("KR-KIS-ELW", kis("ZELW"))):
        d = gate.decide(i, every)
        assert d.verdict == model.BLOCK and d.kind == "new_exposure", (row_id, d.reasons)
        assert d.reasons == (f"needs live broker evidence (execution spec): {row_id}",), (row_id, d.reasons)
```

  New text:

```python
    every = F.ctx(active=state, owner=_t8_owner(flags=frozenset(rules.OWNER_REQUIREMENTS)))
    missing = {"KR-KIS-SHORT": "broker_approval, collateral_105pct", "KR-KIS-ETP-LEV": "deposit_krw_10m",
               "KR-KIS-SINGLE-ETP": "cash_krw_30m", "KR-KIS-ELW": "deposit_krw_15m",
               "KR-KIS-KRX-DERIV": "broker_approval, deposit_krw_10m, deposit_krw_20m"}   # requires.live, sorted
    for row_id, i in (("KR-KIS-SHORT", kis("005930", action="sell_short")), ("KR-KIS-ETP-LEV", kis("252670")),
                      ("KR-KIS-SINGLE-ETP", kis("ZSINGLE")), ("KR-KIS-KRX-DERIV", kis("ZFUT")),
                      ("KR-KIS-ELW", kis("ZELW"))):
        d = gate.decide(i, every)
        assert d.verdict == model.BLOCK and d.kind == "new_exposure", (row_id, d.reasons)
        assert d.reasons == (f"needs live broker evidence: {row_id}: {missing[row_id]}",), (row_id, d.reasons)


def test_d16_rows_lift_only_on_live_deposit_evidence():
    """E1 (spec 6 and 8): ctx.live_evidence, which load_context folds from execution/evidence.jsonl, lifts a D16 row
    once it holds every requires.live item, and lifts nothing else. E1 never writes broker_approval or
    collateral_105pct, so KRX-DERIV and SHORT stay blocked, naming what is missing."""
    from core.compliance import owner
    state = _t8_with_instruments(F.approved(), _t8_fixture("ZSINGLE", "krx_etp", -1.0, "single"),
                                 _t8_fixture("ZFUT", "krx_derivative", 1.0, None),
                                 _t8_fixture("ZELW", "elw", 1.0, None))

    def kis(symbol: str, **changes) -> model.Intent:
        inst = state.instruments.entries[("krx", symbol)]
        return F.intent(**{"venue": "kis", "symbol": symbol, "counter_symbol": "KRW", "asset": inst.asset,
                           "multiple": inst.multiple, "quantity": 1.0, "notional_krw": 30_000.0, **changes})
    flags = _t8_owner(flags=frozenset(rules.OWNER_REQUIREMENTS))
    full = frozenset(owner.EVIDENCE_THRESHOLDS_KRW)
    every = F.ctx(active=state, owner=flags, live_evidence=full)
    for row_id, i in (("KR-KIS-ETP-LEV", kis("252670")), ("KR-KIS-SINGLE-ETP", kis("ZSINGLE")),
                      ("KR-KIS-ELW", kis("ZELW"))):
        d = gate.decide(i, every)
        assert d.verdict == model.ALLOW and d.kind == "new_exposure" and d.reasons == (), (row_id, d.reasons)
    for row_id, i, missing in (("KR-KIS-KRX-DERIV", kis("ZFUT"), "broker_approval"),
                               ("KR-KIS-SHORT", kis("005930", action="sell_short"),
                                "broker_approval, collateral_105pct")):
        d = gate.decide(i, every)
        assert d.verdict == model.BLOCK and \
            d.reasons == (f"needs live broker evidence: {row_id}: {missing}",), (row_id, d.reasons)
    only_10m = F.ctx(active=state, owner=flags, live_evidence=frozenset({"deposit_krw_10m"}))
    assert gate.decide(kis("252670"), only_10m).verdict == model.ALLOW
    elw = gate.decide(kis("ZELW"), only_10m)
    assert elw.verdict == model.BLOCK and \
        elw.reasons == ("needs live broker evidence: KR-KIS-ELW: deposit_krw_15m",), elw.reasons
    course = gate.decide(kis("252670"), F.ctx(active=state, live_evidence=full))     # the owner flags still count
    assert course.verdict == model.BLOCK and \
        course.reasons == ("requires kofia_leveraged_1h: KR-KIS-ETP-LEV",), course.reasons
```

- [ ] **Step 2d: Run to verify it fails (cycle d)**

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_gate/
```

  Expected: a traceback per failure, then among the PASS lines exactly these three FAIL lines, in this order:

```
FAIL compliance_gate/test_d16_rows_lift_only_on_live_deposit_evidence AssertionError: ('KR-KIS-ETP-LEV', ('needs live broker evidence (execution spec): KR-KIS-ETP-LEV',))
FAIL compliance_gate/test_d16_rows_stay_blocked_with_every_owner_flag_signed AssertionError: ('KR-KIS-SHORT', ('needs live broker evidence (execution spec): KR-KIS-SHORT',))
FAIL compliance_gate/test_verdicts_follow_the_rows AssertionError: ('TQQQ', ('needs live broker evidence (execution spec): KR-KIS-ETP-LEV', 'requires kofia_leveraged_1h: KR-KIS-ETP-LEV'))
```

  and the last line `47/50 passed, 3 failed, 0 not run` at `5816d3c` counts (the odds plan appends `grey_rows` tests
  to this module, so the totals are larger, still with exactly these three FAILs), exit code 1.

- [ ] **Step 3d: Implement (cycle d)**

  **Edit G1.** `core/compliance/gate.py`, anchor: the D16 block of `_row_check` (hint :307-308; LF). Old text:

```python
    if row.requires_live:                                              # D16: no owner event satisfies these
        out.append(f"needs live broker evidence (execution spec): {row.id}")
```

  New text:

```python
    missing = sorted(set(row.requires_live) - ctx.live_evidence)       # D16: only live broker evidence lifts these
    if missing:
        out.append(f"needs live broker evidence: {row.id}: {', '.join(missing)}")
```

  Every other gate rule is unchanged (D11 exits, D15, the floor, grey rows, the odds plan's `grey_rows`). The change
  adds no import, no clock and no file read, and gate.py still never holds the words `datetime` or `ZoneInfo`
  (`test_gate_call_graph_has_no_clock_zone_file_or_socket`). An unsealed context never reaches `_row_check`, and a
  `live_evidence` that is not a set makes the subtraction raise, which `decide()` turns into a BLOCK. The reason no
  longer ends with the row id: the odds core's `_screen_refusal` (odds Task 13) reads the row from the text after
  the last `": "`, so it would give a D16 refusal the sub `other` instead of `row`; that is unreachable while the
  odds whitelist (odds O4: shares, 1x ETFs, coins) refuses every D16 class before screening.

- [ ] **Step 4d: Run to verify it passes (cycle d), then the whole task**

  Run the overlap check before EACH Python command below. All run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_gate/
```

  Expected, ending: `50/50 passed, 0 failed, 0 not run` at `5816d3c` counts (the Step 2d total, every entry PASS),
  exit code 0.

  Overlap check, then the compliance static guards, whose scans cover the new owner.py, gate.py and model.py (no
  clock outside a CLI `main`, allowlisted imports, no `CANO`, `seal_context` called only in owner.py):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Expected: every line `PASS`, ending `N/N passed, 0 failed, 0 not run` (exit code 0), N the count this module
  printed before this task (`15/15` at `5816d3c`; the follow-up plan adds guards). A failure names the offending file
  and text: fix the code, never the guard.

  Overlap check, then the E1 suite parts this task touches (the new test file is scanned by the process rule of
  `tests/execution_guards.py`), one command at a time, each after its own overlap check:

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_evidence/
```

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/
```

  Expected: `8/8 passed, 0 failed, 0 not run` for the first (exit code 0); every line `PASS` for the second, ending
  `N/N passed, 0 failed, 0 not run`, N the count Task 8's last run of `execution_guards/` printed (exit code 0).

  Overlap check, then the repo-wide read-only guards (T-RO-01, test_08, test_09; this calls the test functions
  directly, starts no `tests/run_all.py` and writes nothing):

```bash
.venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; from tests.acceptance import test_08_no_broker_order_path as t8, test_09_no_account_credentials_requested as t9; t(); u(); t8(); t9(); print('T-RO-01 ok')"
```

  Expected: `T-RO-01 ok` (exit code 0).

  Overlap check, then the whole compliance suite, keyless (one command line; the checkout restores the results file,
  which Task 13 commits; timeout: 300000):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: no `FAIL` line; the summary reads `P/T passed, 0 failed, K not run;` followed by the results-file path,
  with P and T each one more than the Step 1a compliance baseline (the lift test) and K unchanged (at `5816d3c`
  counts it would read `316/318 passed, 0 failed, 2 not run`: `compliance_isolation/test_symlinks_are_refused` and
  `compliance_tables/test_calendar_sha256_refuses_a_file_symlink` without Developer Mode), then `exit 0`.

  Overlap check, then the odds suite, keyless (the odds core screens through `Context`, `gate` and `owner`;
  timeout: 600000):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite odds; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: no `FAIL` line, the same `P/T passed, 0 failed, K not run` as the Step 1a odds baseline, and `exit 0`.
  Two kinds of odds test read what this task changes: `odds_guards/test_code_closure_holds_no_data_layer` (the
  closure must hold nothing under `core/oddsdata/`, `data/`, `config.py`, `core/quant/`, `core/calendars/`,
  `core/engine/`; `execution/*.py` is none of these, so it passes) and any odds test that compares a whole
  `owner.code_files` list or a hash derived from a `ctx_hash`. If one fails because it pins the closure as exactly
  `core/__init__.py`, `core/isolation.py`, `core/compliance/*.py` and `core/odds/*.py`, widen its expected set by
  `{f"execution/{p.name}" for p in (ROOT / "execution").glob("*.py")}` exactly as Edit T1 does, keep its exclusions,
  and record the drift ruling with the file's path (Step 5 adds that file). An odds failure that names
  `SCREEN_BLOCKED` with the sub `other` for a D16 row comes from the new reason text (the Step 3d note): stop and
  rule; the reason itself stays (contract E5). Any other odds failure: stop and rule.

  Then the text checks (git and grep only, no overlap check needed):

```bash
grep -rn --include=*.py "needs live broker evidence (execution spec)" tests/ core/
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|ZoneInfo|datetime" -- core/compliance/gate.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD" -- core/compliance tools/signer/sign.py tests/execution_evidence.py
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|context_log/|reference_mode|tests\.reference" -- core/compliance tests/execution_evidence.py
git grep --untracked -n -E "datetime\.now|date\.today|time\.time|monotonic|subprocess|importlib\.reload" -- core/compliance/owner.py core/compliance/model.py core/compliance/gate.py tests/execution_evidence.py
```

  Expected: all five print nothing (exit code 1 each).

- [ ] **Step 5: Commit**

```bash
git add core/compliance/model.py core/compliance/gate.py core/compliance/owner.py tools/signer/sign.py tests/compliance_gate.py tests/compliance_model.py tests/compliance_store.py tests/compliance_signer.py tests/execution_evidence.py
```

  If a drift ruling was recorded in this task, also
  `git add docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` and every file a drift ruling of
  this task edited (each is named in its ledger line: a test that pinned the old reason, Step 1a; an odds test whose
  closure set was widened, Step 4d). Then check that nothing is left out:

```bash
git diff --name-only
git ls-files --others --exclude-standard
```

  Expected: the first prints nothing; the second prints nothing or only
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry.md` (the untracked plan file, never staged). Every change is
  staged, no other new file is untracked, and `qa/acceptance_results.json` was restored after each suite run. A
  listed file that a ledger line names is staged as above; any other listed file (the plan file aside) is a stray
  change: stop and rule before committing. Then:

```bash
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two outputs must be identical (every file here is LF). Then commit. In the trailer, replace
  `<the committing model>` with the name of the model that writes this commit, for example `Claude Sonnet 5.5` or
  `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "feat(compliance): live D16 evidence in Context; execution/ joins the code hash" -m "Task 9 (E1 spec 6, 8): Context.live_evidence, seal_context hashing every field, owner.evidence_in_force read by load_context, the D16 rule naming missing items, and owner.code_files plus the signer copy seeding execution/*.py. The D14 code hash changes: owner act 5 re-verifies the signer copy, act 2 re-signs." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
```

  Owner gate 2 of the header applies from here: Step 1a found no owner key (or the owner said yes to the hash
  change), so nothing new is blocked today; once the owner
  has a signing key (main-spec owner act 1), the owner re-verifies `tools/signer/sign.py` and signs the new code hash
  (E1 owner act 5), and until then KIS stays unread (E42).
