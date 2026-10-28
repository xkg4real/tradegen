### Task 12: The poller and the alert CLI (`execution/poll.py`)

**Files:**
- Create: `execution/poll.py` (LF, UTF-8, no BOM)
- Create: `tests/execution_poll.py` (LF, UTF-8, no BOM)
- Modify: `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (anchor: the `## Deferred minors`
  heading; LF): two ruling lines, Step 5
- Test: `tests/execution_poll.py`

The only existing file this task edits is the ledger (Task 1 created it). Its anchor is the `## Deferred minors`
heading, so ruling lines that earlier tasks added above the heading do not affect the edit. The DRIFT RULE (Global
Constraints 0.6) still binds the names this task consumes (Step 1's pre-flight checks them). `MODULES` of
`tests/execution_acceptance.py` already lists `execution_poll` (Task 1, contract 3.1); the aggregator skipped it while
the file did not exist. If `execution/poll.py` or `tests/execution_poll.py` already exists, stop and rule.

**Interfaces:**
- Consumes (exact names; each was produced by the task named, or is in the repo):
  - Task 1, `tests.execution_fixtures` as `EF`: `NOW` (2026-10-24T00:00:00Z), `FAKE_KEYS`, `TOASTS`, `STRAYS`,
    `isolated(home)`; `tests.execution_acceptance._wrap` runs every test inside `hermetic()`, `temp_home()` and
    `isolated(home)`. `tests.execution_guards` as `EG`: `EXECUTION`, `X`, `CLOCK_MAIN`, `_clock_hits(rel, src)`.
  - Task 2: `execution.transport._clock` (a module seam; the default raises), `execution.keys._ENV_FILE`;
    `EF.fake_keys(**overrides)`; inside `isolated()`: `transport._send` refuses (and records in `STRAYS`),
    `transport._sleep` records, `transport._clock` is `lambda: NOW`, `_next_issue_at` and `_okx_offset_s` are None,
    `_bad_tokens` is empty, `keys._ENV_FILE` is a missing file in the temp home.
  - Task 3: `EF.serve(routes, *, date=DATE_HEADER)` yields the list of recorded calls (dicts with at least `"path"`);
    `transport.request` reads the KIS token cache `state_root()/kis_token.json` and calls
    `checked_target(path, "KIS token cache")` BEFORE the token POST (contract 6 `_kis_token`); a 401, 403 or a code
    of `AUTH_CODES` is `AuthError`; a GET answered 429 or >= 500 is retried once.
  - Task 4, `execution.snapshot`: `VENUES`, `Snapshot` (`ok`, `error`, `flags`, `holdings`, `open_orders`, `fills`,
    `deposits`, `withdrawals`, `withdrawal_addresses`, `prices_krw`, `snapshot_sha256`), `home()`,
    `inquiry_path(day)`, `failed(venue, utc, error, *, flags=frozenset(), server_utc=None, clock_offset_s=None)`,
    `dump(snap) -> bytes`, `load(obj) -> Snapshot`, `exclusive(path)` (a sidecar `<path>.lock`; one process-wide
    `threading.Lock`, so this task never nests two `exclusive` blocks), `write_lines(path, lines, what)` (opens and
    creates nothing when `lines` is empty), `read_all(path) -> list[dict]` (no lock, creates nothing, a missing
    file is `[]`).
  - Task 5: `kis_inquiry.snapshot(now, ctx) -> Snapshot` (it returns
    `snapshot.failed("kis", utc, "code not signed", flags=frozenset({"code_unsigned"}))` unless
    `model.is_sealed(ctx) and ctx.code_signed is True`); Task 6: `upbit_inquiry.snapshot(now)`; Task 7:
    `okx_inquiry.snapshot(now, usdt_krw)`. Their fixture routes `EF.kis_routes()`, `EF.upbit_routes()`,
    `EF.okx_routes()` (each a `(method, path) -> answer` map for `serve()`, built from the contract 3.2 bodies and
    merged with `|`; a keyword named after a key of
    `KIS_ROUTES`, `UPBIT_ROUTES` or `OKX_ROUTES` replaces that answer, and an unknown name is a `KeyError`).
  - Task 8: `positions.live_positions(snapshots, now) -> model.Positions | None`.
  - Task 9 (`core/compliance/owner.py`): `owner.evidence_path()`, `owner.evidence_chain(lines) -> (rows, why)`,
    `owner.EVIDENCE_THRESHOLDS_KRW` (the tests only; `poll.py` never names `evidence_path`, Task 1's guard).
  - Task 10, `execution.evidence`: `record(kis, now) -> list[dict]` (the due records it appended),
    `EvidenceBroken` (chain defects only; a `checked_target` refusal propagates).
  - Task 11, `execution.checks`: `Alert(venue, kind, level, text_key, slots={})` (frozen, kw_only: always named
    fields), `limits_from(owner, day_start)`, `priors(rows)`, `day_start(rows, now)`,
    `run_checks(prev, new, owner, limits, now)`, `evaluated(prev, new, owner, limits, now)`,
    `not_set(new, owner, limits, live)`, `due(raw, done, rows, now) -> (fresh, clears)` (fresh already sorted amber
    and info before red), `render(alert)`, `row(alert, utc)`, `verify_row(obj)`, `STAMP`, `TEXT`.
  - Repo: `core.compliance.owner.load_context(now, positions, *, session_id=None)` (owner.py:964; never raises for an
    aware `now`), `core.compliance.owner.PUBKEY_PATH` (owner.py:24, what `F.pubkey_at` points),
    `core.compliance.alerts._toast(title, body) -> bool` (the P26 seam, alerts.py:216, reached through
    the module, E2), `core.compliance.model` (`Positions`, `KST`, `iso_utc`, `canonical_json`),
    `core.isolation.checked_target(path, what)` and `core.isolation._LINK_SCAN` (isolation.py:16, 40);
    the odds plan's public `tests.compliance_fixtures` helpers `F.pubkey_at(path)`, `F.full_home(home, *,
    rules_raw=None, venues_raw=None, calendar_raw=None, limits=None, cap=None)` (odds contract 3.3) and
    `F.temp_home()` (contract 0.6; stop and rule if `pubkey_at` or `full_home` is not public).
- Produces (`execution/poll.py`, exactly contract section 16):
  - `DEFAULT_INTERVAL_MIN = 5`; `EXIT_OK, EXIT_LOCKED, EXIT_CRASH = 0, 0, 4` (E1R2-1);
    `PLACEHOLDER = model.Positions(equity_krw=1.0)`; `UNVERIFIED`; `_sleep = time.sleep`; `_unlogged: set`;
  - `alerts_path() -> Path`, `lock_path() -> Path`, `held_lock()` (context manager yielding True or False),
    `poll_once(now) -> dict` (the redacted summary of contract 16.3), `pending(rows) -> dict`,
    `mark_sent(utc) -> int`, `main(argv=None) -> int`, and the `__main__` block `raise SystemExit(main())`;
  - private helpers (this module only): `_LOCKED`, `_byte_lock`, `_counts`, `_record_alerts`, `_crash_line`,
    `_crash`, `_line`, `_row_of`, `_minutes`, `_stamp`, `_parser`.
  - What Tasks 13 and 14 rely on: `python -m execution.poll [--once] [--interval-min N]`; `--pending` prints one
    ASCII JSON line, `{"send": false}`, or `"send": true` with the keys `subject`, `body` and `utcs` (contract 16.4);
    `--mark-sent <utc>` prints `{"marked": n}`; exit 0 ok or another poller holds the lock, 4 a crash in `--once` or
    an argument error.

**Plan decisions used:** E7 (the CLI, exit codes, the loop catches every exception per poll), E11 (`main` is the
only clock reader and sets `transport._clock`), E19 (via `checks.due`: only evaluated kinds clear), E23 (`--pending`
and `--mark-sent`), E24 (the context first, once per poll, with `PLACEHOLDER`), E30 (daily inquiry files, two read
per poll), E31 (KEY_MISSING), E33 (EVIDENCE_BROKEN; a refused write is a crash), E34 (the day's start), E36
(`transport` only for `transport._clock` inside `main`), E37 (no secret, balance or exception text in any output),
E38 (venue errors stay in the snapshot), E40 (CRASH_UNLOGGED), E42 (KIS only under signed code), E43 (the NOT_SET
info row); rulings E1R2-1, E1R2-4, E1R2-8, E1R2-9, E1R2-12.

Design notes (read before Step 3; each is a choice inside contract 16 and changes no name; the sleep cap departs from
one sentence of contract 16.1, and Step 5 records it in the ledger as a ruling):
- **Alerts are named.** `checks.Alert` is kw_only (Task 11), so the poller's own alerts (EVIDENCE_BROKEN,
  OUTAGE_CRASH, CRASH_UNLOGGED, NOT_SET) name every field; contract 16.2 writes them positionally as shorthand.
- **Rows first, toasts second.** `_record_alerts` writes the fresh and clear rows under the alerts lock and only then
  toasts, so a refused `alerts.jsonl` toasts nothing but E40's one CRASH_UNLOGGED, and a toast never shows for a row
  that is not on disk.
- **The lock.** `held_lock` takes byte 0 of `poll.lock` without waiting and treats only `PermissionError` (msvcrt,
  probed offline: a second handle, in the same process too, gets errno 13) and `BlockingIOError` (fcntl) as "held
  elsewhere"; any other `OSError`, and a refused path, is a crash (`main` returns 4 through E40's path). It tries 5
  times, 0.2 s apart through `_sleep`, before it yields False: the test wrapper's probe of the real `poll.lock` holds
  byte 0 for an instant (msvcrt's LK_NBRLCK is exclusive, Task 1's deferred minor), and a logon poller starting in
  that instant would otherwise exit 0 and leave the PC unmonitored until the next logon (checked on Windows in a
  sandbox: a lock let go between two tries is taken). A real second poller exits 0.8 s later.
- **A clock stepped back sleeps one interval at most.**
  `_sleep(min(float(interval_s), max(0.0, interval_s - elapsed)))` is contract 16.1's
  `max(0, interval * 60 - elapsed)` capped at one interval (every sleep a float), so a clock stepped back an hour does
  not stall the poller for an hour. This departs from contract 16.1's sentence; the ruling goes in the ledger
  (Step 5), and in contract 16.1 when the contract is next revised.
- **`--pending` renders only verified rows.** `_line` renders a row only after `checks.verify_row`, which already
  guarantees a real instant with a Seoul date (Task 11), so its KST conversion cannot raise.
- **`mark_sent`** checks `alerts.jsonl` before it makes the temp file, so a refused log leaves no `.tmp` behind; it
  rewrites only rows whose `utc` matches and whose `sent` is False, so a repeat changes nothing (0).
- **Words poll.py never holds** (raw text, docstrings and comments included; the guards of contract 0.5): the name
  `requests`, any credential name, `evidence_path` (only `execution/evidence.py` names it), the upper-case KIS account
  field names (write "canonical" in lower case only), any 4-letters-4-digits-letter token. `transport` appears once as
  a name, the target of the one assignment `transport._clock = lambda: datetime.now(timezone.utc)` inside `main`. If
  you touch a docstring, keep it so.
- **Tests.** E40's refused alerts.jsonl is a real refusal (a hard link) in place of the patch TASKS names, so the
  whole `checked_target` path runs; a patch would have to replace `execution.snapshot.checked_target` (as Task 10's
  test does), because patching `core.isolation.checked_target` misses snapshot's import-time binding (`from
  core.isolation import checked_target`). Step 5 records this in the ledger. In a
  signed home `owner.load_context` costs about 1.5 s (it parses the approved tables; `F.full_home` about 2.2 s, an
  unsigned `load_context` about 0.45 s, measured on the owner's PC), so `_signed()` memoises `load_context` per Seoul date (`_one_context_a_day`, a `ponytail:` comment
  names the ceiling) to keep the suite under 60 s (X8); the owner log never changes inside a test and a poll reads
  only `ctx.owner` and `ctx.code_signed` (E24). The E24 test itself runs unsigned with the real `load_context`
  wrapped by a recorder, so "once per poll and before the first send" is proved on the real function.
  `_routes(kis=..., upbit=..., okx=...)` is only `EF.kis_routes(**kis) | EF.upbit_routes(**upbit) |
  EF.okx_routes(**okx)`: each change is named as Tasks 5 to 7 name the route, so a misnamed one is their `KeyError`.
- **`--help`** exits 0 (argparse's own `SystemExit(0)`); every argument error exits 4.

Scope covered (TASKS.md, Task 12), test by test:

| Scope bullet | Test(s) |
|---|---|
| signed home, every route: three inquiry lines, the first evidence lines, alert rows sent false, one toast each, a counts-only summary; no repeat a minute later; one venue failing; a broken evidence chain | `test_a_signed_poll_reads_every_venue_and_records_once` |
| signed code (E1R2-9): no KIS path, `code not signed`, one KIS_UNSIGNED, no OUTAGE after three, no evidence.jsonl (E42); `load_context` once per poll, before the first send | `test_unsigned_code_sends_nothing_to_kis_and_alerts_once_a_day` |
| daily files (E1R2-4): 23:59:59 and 00:00:00 KST, priors see yesterday, a file two days back unread, nothing deleted | `test_each_seoul_day_has_its_own_inquiry_file_and_a_poll_reads_two` |
| the info row (E1R2-12) | `test_the_not_set_row_is_written_once_a_day_and_never_sent` (and the forged-row test: an unsent info row is never listed) |
| refused writes: inquiry file, evidence.jsonl, kis_token.json, alerts.jsonl, a link before the first scan (TASKS says `checked_target` patched; a real refusal (a hard link) is used so the whole `checked_target` path runs; ledger, Step 5) | `test_a_hard_linked_inquiry_file_is_a_crash_alerted_for_every_venue`, `test_a_hard_linked_evidence_log_is_a_crash_not_evidence_broken`, `test_a_hard_linked_kis_token_cache_is_a_crash_before_any_token_post`, `test_unwritable_alerts_toast_crash_unlogged_once_per_seoul_day`, `test_a_link_before_the_first_scan_toasts_once_and_polls_nothing` |
| `--once` 0, 4 after a crash (no exception text), 0 under a held lock with the message and no poll (5 tries 0.2 s apart; a lock let go between tries is taken); argument errors 4 | `test_once_prints_one_summary_line_and_releases_the_lock`, `test_a_hard_linked_inquiry_file_is_a_crash_alerted_for_every_venue`, `test_a_second_poller_exits_0_and_polls_nothing`, `test_argument_errors_return_4_and_poll_nothing` |
| the loop: crash, success, Ctrl+C; `60 - elapsed`; lock released | `test_the_loop_survives_a_crash_sleeps_the_rest_and_stops_on_ctrl_c`, `test_the_interval_bounds_and_the_default` |
| `--pending` and `--mark-sent` (forged rows, empty home, byte-for-byte, idempotent, under a held lock; 4 on an error, no temp file left) | `test_pending_shows_only_verified_text_and_never_a_forged_row`, `test_pending_and_mark_sent_in_an_empty_home_create_nothing`, `test_mark_sent_marks_only_that_poll_and_keeps_every_other_byte`, `test_a_refused_alerts_log_makes_mark_sent_return_4_and_leaves_no_temp_file` |
| KEYLESS proven, signed and unsigned | `test_keyless_signed_home_sends_nothing_and_alerts_key_missing`, `test_keyless_unsigned_home_alerts_kis_unsigned_instead` |
| `test_no_secret_reaches_any_output` | `test_no_secret_reaches_any_output` |
| `main` sets `transport._clock` and is the only clock reader (guard) | `test_main_sets_the_transport_clock_and_is_the_only_clock_reader` |

- [ ] **Step 1: Write the failing test(s)**

  Pre-flight (Git Bash, repo root; nothing here writes; run the overlap check of Step 2 before the Python line).
  Every name this task consumes must be there; a missing name or a different signature is a drift ruling (Global
  Constraints 0.6): stop and rule, and record the ruling in the E1 execution ledger.

```bash
git status --short
ls execution/poll.py tests/execution_poll.py
grep -n '"execution_poll"' tests/execution_acceptance.py
.venv/Scripts/python.exe -c "import inspect; from tests import compliance_fixtures as F, execution_fixtures as EF, execution_guards as EG; from execution import checks, evidence, snapshot; from core.compliance import owner; print(sorted(inspect.signature(F.full_home).parameters), callable(F.pubkey_at)); print([n for n in ('isolated', 'fake_keys', 'serve', 'kis_routes', 'upbit_routes', 'okx_routes', 'TOASTS', 'STRAYS', 'FAKE_KEYS', 'NOW') if not hasattr(EF, n)]); print([n for n in ('Alert', 'limits_from', 'priors', 'day_start', 'run_checks', 'evaluated', 'not_set', 'due', 'render', 'row', 'verify_row', 'STAMP', 'TEXT') if not hasattr(checks, n)]); print([n for n in ('home', 'inquiry_path', 'failed', 'dump', 'load', 'exclusive', 'write_lines', 'read_all', 'VENUES') if not hasattr(snapshot, n)]); print([n for n in ('record', 'EvidenceBroken') if not hasattr(evidence, n)], [n for n in ('evidence_path', 'evidence_chain', 'EVIDENCE_THRESHOLDS_KRW') if not hasattr(owner, n)], [n for n in ('EXECUTION', 'X', 'CLOCK_MAIN', '_clock_hits') if not hasattr(EG, n)])"
.venv/Scripts/python.exe -c "import inspect; from core import isolation; from core.compliance import owner; from execution import keys, kis_inquiry, okx_inquiry, positions, snapshot, transport, upbit_inquiry; print([[n + ('*' if p.kind is p.KEYWORD_ONLY else '') for n, p in inspect.signature(f).parameters.items()] for f in (positions.live_positions, kis_inquiry.snapshot, upbit_inquiry.snapshot, okx_inquiry.snapshot, owner.load_context, snapshot.failed)], hasattr(transport, '_clock'), hasattr(keys, '_ENV_FILE'), hasattr(isolation, '_LINK_SCAN'), hasattr(owner, 'PUBKEY_PATH'))"
```

  Expected: `git status --short` prints nothing; `ls` reports `No such file or directory` for both paths; the grep
  prints the `MODULES` line holding `"execution_poll"`; the first Python line prints
  `['calendar_raw', 'cap', 'home', 'limits', 'rules_raw', 'venues_raw'] True` (the parameter list must hold `cap`,
  `home` and `limits`; extra keywords from the odds plan are fine) and then four lines of empty lists: `[]`,
  `[]`, `[]` and `[] [] []`. The second prints (a `*` marks a keyword-only parameter)
  `[['snapshots', 'now'], ['now', 'ctx'], ['now'], ['now', 'usdt_krw'], ['now', 'positions', 'session_id*'], ['venue', 'utc', 'error', 'flags*', 'server_utc*', 'clock_offset_s*']] True True True True`;
  an extra keyword-only parameter of `load_context` from an earlier plan is fine, any other difference is a ruling.

  Then create `tests/execution_poll.py` (whole file, LF):

```python
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
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (must print nothing; if it prints a process, wait):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, in Git Bash from the repo root (the same check as a prefix):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_poll/; echo "exit $?"
```

  Expected: a traceback, then
  `FAIL execution_poll/import ImportError: cannot import name 'poll' from 'execution'` (followed by the package path
  in parentheses), then
  `0/1 passed, 1 failed, 0 not run` and `exit 1`. Any other failure (a `NameError` or `AttributeError` naming a
  fixture, a checks or snapshot name) means an earlier task drifted: stop and rule.

- [ ] **Step 3: Implement**

  Create `execution/poll.py` (whole file, LF). It imports only `__future__`, `argparse`, `contextlib`, `json`, `os`,
  `time`, `traceback`, `collections.abc`, `datetime`, `pathlib`, `msvcrt` or `fcntl` (inside `_byte_lock`),
  `core.compliance` (`alerts`, `model`, `owner`), `core.isolation` and `execution.*`, all on the 0.5 allowlist, and
  `transport` only through `from execution import transport` for the one assignment in `main` (E36).

```python
"""The E1 poller and its alert CLI (E1 spec 4 "Data flow per poll", 7 "Alert records and delivery" and "The poller",
10; plan C16).

    python -m execution.poll [--once] [--interval-min N]   poll every N minutes (1 to 60, default 5), or once
    python -m execution.poll --pending                     the unsent alerts as one JSON line, for the 09:05 task
    python -m execution.poll --mark-sent UTC               mark the alert rows of that poll sent

main() is the only wall-clock reader in execution/ (E11): it reads the clock once per poll, passes `now` down and
sets transport._clock for the three send-time needs. One poller at a time: a second one finds poll.lock held, says
so and exits 0 (E1R2-1). A crashed poll is alerted (OUTAGE_CRASH for every venue) and the next poll runs as usual;
when even that alert cannot be written, one toast says so (E40). E1 only alerts: it never halts, disarms, sells or
withdraws."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import time
import traceback
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.compliance import alerts, model, owner
from core.isolation import checked_target
from execution import checks, evidence, kis_inquiry, okx_inquiry, positions, snapshot, upbit_inquiry
from execution import transport  # only for transport._clock inside main (E11, E36)

DEFAULT_INTERVAL_MIN = 5
EXIT_OK, EXIT_LOCKED, EXIT_CRASH = 0, 0, 4           # E1R2-1: a second poller exits 0 with a message (spec 4)
PLACEHOLDER = model.Positions(equity_krw=1.0)        # E24: the only positions load_context ever gets from E1
UNVERIFIED = "An E1 alert row did not verify; read ~/.tradegen/execution/alerts.jsonl on the PC."
_LOCKED = "another E1 poller holds poll.lock; exiting"
_sleep = time.sleep                                  # the loop's and held_lock's seam; reads no clock
_unlogged: set = set()                               # Seoul dates on which CRASH_UNLOGGED was toasted (E40)


def alerts_path() -> Path:
    """execution/alerts.jsonl, E1's alert rows (spec 7); core/compliance/alerts.py keeps its own file."""
    return snapshot.home() / "alerts.jsonl"


def lock_path() -> Path:
    """execution/poll.lock, held by the one running poller (spec 4)."""
    return snapshot.home() / "poll.lock"


def _byte_lock(fh, lock: bool) -> None:
    """Locks byte 0 of `fh` without waiting (PermissionError or BlockingIOError when another handle holds it), or
    unlocks it."""
    fh.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK if lock else msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB if lock else fcntl.LOCK_UN)


@contextlib.contextmanager
def held_lock() -> Iterator[bool]:
    """poll.lock: yields True when this handle took it (released on exit), False when another handle still holds it
    after 5 tries 0.2 s apart (so the test wrapper's instant probe of the real lock never makes a starting poller
    exit). A refused path (a link, QUANTGEN) raises before anything is opened."""
    checked_target(snapshot.home(), "E1 state folder").mkdir(parents=True, exist_ok=True)
    with open(checked_target(lock_path(), "E1 poll lock"), "a+b") as fh:
        got = False
        for attempt in range(5):
            if attempt:
                _sleep(0.2)
            try:
                _byte_lock(fh, True)
                got = True
                break
            except (PermissionError, BlockingIOError):  # another poller (or another handle here) holds it
                pass
        try:
            yield got
        finally:
            if got:
                _byte_lock(fh, False)


def _counts(snap: snapshot.Snapshot) -> dict:
    """How many records of each kind a snapshot holds: counts only, never an amount or an address (C16.3)."""
    return {"holdings": len(snap.holdings), "open_orders": len(snap.open_orders), "fills": len(snap.fills),
            "deposits": len(snap.deposits), "withdrawals": len(snap.withdrawals),
            "addresses": len(snap.withdrawal_addresses)}


def _record_alerts(raw: list, done: frozenset, now: datetime) -> list:
    """C16.2 steps 7 and 8: the once-a-day rule against alerts.jsonl under its lock, the fresh and clear rows
    appended, then one toast per fresh red or amber alert (an info row is never toasted). Returns the fresh alerts."""
    path, utc = alerts_path(), model.iso_utc(now)
    with snapshot.exclusive(path):
        fresh, clears = checks.due(raw, done, snapshot.read_all(path), now)
        snapshot.write_lines(path, [(model.canonical_json(checks.row(a, utc)) + "\n").encode("utf-8")
                                    for a in fresh + clears], "E1 alerts")
    for alert in fresh:
        if alert.level in ("red", "amber"):
            alerts._toast(f"TRADEGEN E1 {alert.level}", checks.render(alert))
    return fresh


def poll_once(now: datetime) -> dict:
    """One poll at `now` (spec 4 data flow; C16.2); returns the redacted summary (C16.3). Venue errors stay inside
    their snapshots (E38); anything else, a refused write included, propagates and main alerts it as a crash."""
    ctx = owner.load_context(now, PLACEHOLDER)           # first, before any venue is asked (E24, E42)
    today = now.astimezone(model.KST).date()
    upbit = upbit_inquiry.snapshot(now)
    okx = okx_inquiry.snapshot(now, upbit.prices_krw.get("USDT") if upbit.ok else None)
    kis = kis_inquiry.snapshot(now, ctx)                 # sends nothing unless ctx.code_signed is True (E42)
    new = {"kis": kis, "upbit": upbit, "okx": okx}
    # ponytail: only yesterday's and today's files are read (E30); a venue whose last ok snapshot is older is compared
    # again from its next ok snapshot. Read further back if a check ever needs a longer memory.
    rows = (snapshot.read_all(snapshot.inquiry_path(today - timedelta(days=1)))
            + snapshot.read_all(snapshot.inquiry_path(today)))
    prev, start = checks.priors(rows), checks.day_start(rows, now)
    with snapshot.exclusive(snapshot.home() / "inquiry"):
        snapshot.write_lines(snapshot.inquiry_path(today), [snapshot.dump(new[v]) for v in snapshot.VENUES],
                             "E1 inquiry log")
    own, done, recorded = [], set(), 0
    if kis.ok:
        try:
            recorded = len(evidence.record(kis, now))
        except evidence.EvidenceBroken:                  # fail closed: no live evidence counts (E33)
            recorded = "broken"
            own.append(checks.Alert(venue="kis", kind="EVIDENCE", level="amber", text_key="EVIDENCE_BROKEN"))
        done.add(("kis", "EVIDENCE"))
    live = positions.live_positions(new, now)
    if start is None and live is not None:               # the first live poll of the Seoul day is the start (E34)
        start = (live.equity_krw, model.iso_utc(now))
    limits = checks.limits_from(ctx.owner, start)
    raw = checks.run_checks(prev, new, ctx.owner, limits, now) + own
    done |= checks.evaluated(prev, new, ctx.owner, limits, now)
    skipped = checks.not_set(new, ctx.owner, limits, live)
    if skipped:                                          # E43: one info row a day, never toasted or sent
        raw.append(checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                                slots={"skipped": "; ".join(skipped)}))
    fresh = _record_alerts(raw, frozenset(done), now)
    return {"utc": model.iso_utc(now),
            "venues": {v: "ok" if new[v].ok else "error" for v in snapshot.VENUES},
            "errors": {v: new[v].error for v in snapshot.VENUES if not new[v].ok},
            "counts": {v: _counts(new[v]) for v in snapshot.VENUES},
            "evidence": recorded,
            "alerts": sum(a.level in ("red", "amber") for a in fresh),
            "not_set": list(skipped)}


def _crash_line(exc: BaseException) -> str:
    """{"crash": <type name>, "at": "<file name>:<line>"} of the innermost frame; never str(exc), which can quote a
    value (E37)."""
    frames = traceback.extract_tb(exc.__traceback__)
    at = f"{Path(frames[-1].filename).name}:{frames[-1].lineno}" if frames else ""
    return json.dumps({"crash": type(exc).__name__, "at": at}, ensure_ascii=True)


def _crash(now: datetime, exc: BaseException) -> None:
    """The crash path (C16.2; spec 7 "a crashed poll is logged and alerted"): the crash line, then OUTAGE_CRASH for
    every venue through the once-a-day rule. When that fails too, the toast-only CRASH_UNLOGGED, at most once per
    process per Seoul date, and the second crash line (E40)."""
    print(_crash_line(exc), flush=True)
    when = model.iso_utc(now)
    try:
        _record_alerts([checks.Alert(venue=v, kind="OUTAGE", level="amber", text_key="OUTAGE_CRASH",
                                     slots={"when": when}) for v in snapshot.VENUES], frozenset(), now)
    except Exception as again:                           # the alert rows cannot be written either
        day = now.astimezone(model.KST).date()
        if day not in _unlogged:
            _unlogged.add(day)
            alerts._toast("TRADEGEN E1 amber", checks.render(checks.Alert(
                venue="all", kind="OUTAGE", level="amber", text_key="CRASH_UNLOGGED", slots={"when": when})))
        print(_crash_line(again), flush=True)


def _line(row: dict) -> str | None:
    """`<KST time> <level>: <sentence>` for a row that verifies (verify_row also makes sure its utc is a real instant
    with a Seoul date); None otherwise."""
    if not checks.verify_row(row):
        return None
    kst = datetime.fromisoformat(row["utc"]).astimezone(model.KST)
    alert = checks.Alert(venue=row["venue"], kind=row["kind"], level=row["level"], text_key=row["text_key"],
                         slots=row["slots"])
    return f"{kst:%Y-%m-%d %H:%M} KST {row['level']}: {checks.render(alert)}"


def pending(rows: list) -> dict:
    """The --pending message (C16.4; E23): every unsent red or amber row in file order, each re-verified before it is
    rendered, since the 09:05 task forwards the text off the PC. Any row that fails gives the one UNVERIFIED line and
    none of its own text; a clear or info row never leaves the PC (E43)."""
    listed = [r for r in rows if isinstance(r, dict) and r.get("sent") is False
              and r.get("level") not in ("clear", "info")]
    if not listed:
        return {"send": False}
    body, red = [], 0
    for r in listed:
        line = _line(r)
        if line is None:
            if UNVERIFIED not in body:
                body.append(UNVERIFIED)
        else:
            body.append(line)
            red += r["level"] == "red"
    utcs = sorted({r["utc"] for r in listed if isinstance(r.get("utc"), str) and checks.STAMP.fullmatch(r["utc"])})
    return {"send": True, "subject": f"TRADEGEN E1: {len(listed)} alert(s), {red} red", "body": "\n".join(body),
            "utcs": utcs}


def _row_of(line: bytes) -> dict | None:
    """The JSON object on `line`, or None (a torn or foreign line, kept as it is)."""
    try:
        row = json.loads(line)
    except (ValueError, RecursionError):
        return None
    return row if isinstance(row, dict) else None


def mark_sent(utc: str) -> int:
    """Marks every unsent row of the poll stamped `utc` sent and keeps every other line byte for byte; returns how
    many rows changed (0 on a repeat). A missing alerts.jsonl is 0 and creates nothing. Takes the alerts lock, never
    poll.lock (E23)."""
    path = alerts_path()
    if not path.is_file():
        return 0
    with snapshot.exclusive(path):
        out, marked = [], 0
        for line in path.read_bytes().splitlines(keepends=True):
            row = _row_of(line)
            if row is not None and row.get("utc") == utc and row.get("sent") is False:
                line = (model.canonical_json({**row, "sent": True}) + "\n").encode("utf-8")
                marked += 1
            out.append(line)
        if marked:
            checked_target(path, "E1 alerts log")       # refused before a temp file exists
            tmp = path.with_name(f".alerts.jsonl.{os.urandom(6).hex()}.tmp")
            with open(checked_target(tmp, "E1 alerts temp"), "xb") as fh:
                fh.write(b"".join(out))
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(checked_target(tmp, "E1 alerts temp"), checked_target(path, "E1 alerts log"))
    return marked


def _minutes(text: str) -> int:
    """--interval-min: a whole number of minutes from 1 to 60."""
    if not (text.isascii() and text.isdigit() and 1 <= int(text) <= 60):
        raise argparse.ArgumentTypeError("takes a whole number of minutes from 1 to 60")
    return int(text)


def _stamp(text: str) -> str:
    """--mark-sent: a poll's utc exactly as alerts.jsonl holds it."""
    if not checks.STAMP.fullmatch(text):
        raise argparse.ArgumentTypeError("takes a UTC stamp YYYY-MM-DDTHH:MM:SSZ")
    return text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m execution.poll",
                                     description="E1 read-only account inquiry: poll, or hand over unsent alerts.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="one poll, then exit (0 ok, 4 after a crash)")
    mode.add_argument("--pending", action="store_true", help="print the unsent alerts as one JSON line")
    mode.add_argument("--mark-sent", metavar="UTC", type=_stamp, help="mark the alert rows of that poll sent")
    parser.add_argument("--interval-min", metavar="N", type=_minutes,
                        help=f"minutes between polls, 1 to 60 (default {DEFAULT_INTERVAL_MIN}); the loop only")
    return parser


def main(argv: list[str] | None = None) -> int:
    """The CLI (C16.1). Every wall-clock read of execution/ is in this body (E11)."""
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        if args.interval_min is not None and (args.once or args.pending or args.mark_sent is not None):
            parser.error("--interval-min applies to the loop only")
    except SystemExit as exc:                            # argparse printed the reason
        return EXIT_OK if exc.code == 0 else EXIT_CRASH
    if args.pending or args.mark_sent is not None:      # neither takes poll.lock or sets the clock
        try:
            out = pending(snapshot.read_all(alerts_path())) if args.pending else {"marked": mark_sent(args.mark_sent)}
        except Exception as exc:
            print(_crash_line(exc), flush=True)
            return EXIT_CRASH
        print(json.dumps(out, ensure_ascii=True), flush=True)
        return EXIT_OK
    transport._clock = lambda: datetime.now(timezone.utc)    # the OKX header and offset, the KIS token's age (E11)
    interval_s = (args.interval_min or DEFAULT_INTERVAL_MIN) * 60
    now = datetime.now(timezone.utc)
    try:
        with held_lock() as got:
            if not got:
                print(_LOCKED, flush=True)
                return EXIT_LOCKED
            while True:
                try:
                    print(json.dumps(poll_once(now), ensure_ascii=True), flush=True)
                    crashed = False
                except Exception as exc:                 # alerted; the next poll runs as usual (spec 7)
                    _crash(now, exc)
                    crashed = True
                if args.once:
                    return EXIT_CRASH if crashed else EXIT_OK
                elapsed = (datetime.now(timezone.utc) - now).total_seconds()
                # a clock stepped back (negative elapsed) still sleeps one interval at most (ledger ruling, Task 12)
                _sleep(min(float(interval_s), max(0.0, interval_s - elapsed)))
                now = datetime.now(timezone.utc)
    except KeyboardInterrupt:                            # Ctrl+C or the end of the task: the lock is released
        return EXIT_OK
    except Exception as exc:                             # poll.lock itself was refused (a link): E40
        _crash(now, exc)
        return EXIT_CRASH


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 before EACH Python command below (the prefix form is shown on the first; put the
  same prefix, everything up to and including its `&&`, in front of every other). All run from the repo root in Git
  Bash.

  The new module:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_poll/; echo "exit $?"
```

  Expected: 22 lines starting `PASS execution_poll/test_`, then `22/22 passed, 0 failed, 0 not run` and `exit 0`.
  Expect about 27 s on the owner's PC, computed from the unit costs in the design notes (not measured; the module
  cannot run before Tasks 3 to 11 exist): five signed homes at 3.7 s each (`F.full_home` 2.2 s plus one signed
  `load_context` 1.5 s) is 18.5 s, and 19 unsigned real `load_context` calls at 0.45 s is 8.6 s. A `NOT_RUN` line
  whose reason starts `PENDING` means cryptography is missing from the venv: stop and rule (it is pinned, 49.0.0).

  The execution guards, whose scans now include `execution/poll.py` (import allowlist, the wall clock outside
  `main`, writes only through `checked_target`, no verb call, the token rules, transport only for
  `transport._clock`, no rebinding, the one-line `__main__` block):

```bash
.venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/; echo "exit $?"
```

  Expected, ending: `N/N passed, 0 failed, 0 not run` and `exit 0`, with the same N as at the end of Task 11 (this
  task adds no guard test). A failure names the offending file and text: fix `execution/poll.py`,
  never the guard.

  The D14 code closure tests. Since Task 9 every `execution/*.py` is seeded into the closure, so `execution/poll.py`
  joins it now. poll.py imports only files already in the closure: `core/compliance/alerts.py`, `model.py`,
  `owner.py`, `core/isolation.py` and the `execution/*.py` modules it names. Each command carries the overlap check:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/; echo "exit $?"
```

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/; echo "exit $?"
```

  Expected for each: every line `PASS`, then `N/N passed, 0 failed, 0 not run` and `exit 0`, N the same total that
  Task 9's cycle-c Step 4 (Step 4c) printed for that module (Tasks 10 and 11 add no test to either). A FAIL of
  `test_code_files_is_the_import_closure` that names a path means poll.py pulled a new file into the closure: fix
  `execution/poll.py`, never the test.

  The whole execution suite with the KEYLESS prefix, under 60 s (X8; `timeout: 300000`); the seconds come from the
  results file before it is restored. The overlap check gates the whole `{ ...; }` group, so when another run_all is
  running nothing runs and nothing prints (wait, then run the line again), and a stale results file is never read:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && { KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite execution; echo "exit $?"; .venv/Scripts/python.exe -c "import json; rows = json.load(open('qa/acceptance_results.json', encoding='utf-8')); print(len(rows), 'rows', round(sum(r['seconds'] for r in rows), 1), 's', [r['test'] for r in rows if r['status'] == 'FAIL'], sorted({r.get('reason', '')[:8] for r in rows if r['status'] == 'NOT_RUN'}), [(r['test'], r['seconds']) for r in sorted(rows, key=lambda r: -r['seconds'])[:5]])"; git checkout -- qa/acceptance_results.json; }
```

  Expected: the last run_all line reads `228/228 passed, 0 failed, 0 not run;` followed by the results path, and
  `exit 0` (drafted: 24 guards, 9 keys, 30 transport, 17 snapshot, 19 KIS, 11 Upbit, 18 OKX, 13 positions, 22
  evidence, 43 checks, 22 poll; under G3-1 another count with 0 failed passes, and in Step 5 the ledger's `## Runs`
  section records the count and the reason, taken from the ledger line of the task that changed it); then
  `228 rows <s> s [] [<reasons>] [<five slowest>]` with `<s>` below 120.0 (60.0 is the target; see G3-2 below) and no
  failed row. The reasons list is normally `[]`; a `REFDATA:` reason (Task 4's junction test off Windows) is fine; any
  other reason is a ruling. `git status --short` afterwards lists only the two new files (the ledger is edited in
  Step 5). From 60 s up to 120 s the run passes: in Step 5, append one line to the ledger's `## Runs` section (the
  end of the file) recording the measured time and the five slowest rows with `(over the 60 s target, E8, G3-2)`; no
  test is changed or shrunk. At 120 s or more, stop: the controller rules (G3-2) and may split the module.

  The inherited T-RO-01 check and the cockpit text guards (test_08, test_09) over the runtime surface, `execution/`
  included (calls the test functions directly, writes nothing):

```bash
.venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; from tests.acceptance import test_08_no_broker_order_path as t8, test_09_no_account_credentials_requested as t9; t(); u(); t8(); t9(); print('T-RO-01 ok')"
```

  Expected: `T-RO-01 ok` (exit code 0).

  The cockpit suite with the KEYLESS prefix (its test_08, test_09, test_16 and test_18 scan `execution/`, and the
  prefix keeps `test_21`'s keyed KIS client off the network, Global Constraints 0.2; `timeout: 300000`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected last lines: `47/47 passed, 0 failed, 0 not run; ...qa\acceptance_results.json` and `exit 0`, exactly
  Task 1's Step 4b cockpit line. Any other count is a drift ruling recorded in the ledger.

  Then the raw-text checks (git only, no overlap check needed; `--untracked` because the files are not committed
  yet; the test file names KIS paths on purpose, to recognise them in the router's call log, so it is not in the
  first grep):

```bash
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|append_system_entry|system_halt|system_disarm|x-simulated-trading|openapivts|/v1/order|/v1/withdraw|/uapi/|context_log/|reference_mode|eodhd|quartr" -- execution/poll.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|KIS_APP|UPBIT_|OKX_API|requests|evidence_path|utcnow|date\.today|time\.time|monotonic|perf_counter|[A-Za-z]{4}[0-9]{4}[A-Za-z]|0\.4 \*" -- execution/poll.py
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|context_log/|reference_mode" -- tests/execution_poll.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|subprocess|multiprocessing|runpy|sys\.executable|os\.system|os\.popen|importlib" -- tests/execution_poll.py
```

  Expected: all four print nothing (exit code 1 each).

- [ ] **Step 5: Commit**

  First record the two departures in the ledger: the sleep cap (contract 16.1) and the real refusal in place of
  TASKS's patched `checked_target`. Use the Edit tool and keep LF. The anchor is the `## Deferred minors` heading. It
  occurs once, so any ruling lines that earlier tasks added above it stay as they are. Old text:

```text
## Deferred minors
```

  New text:

```text
- Task 12 (C16.1 drift): the loop sleeps `min(float(interval * 60), max(0.0, interval * 60 - elapsed))`, the
  contract's `max(0, interval * 60 - elapsed)` capped at one interval, so a clock stepped back never stalls the
  poller beyond one interval; contract 16.1 takes the cap when it is next revised.
- Task 12 (C16.1 drift, Task 1's deferred minor on the poller probe): `held_lock` tries byte 0 of poll.lock 5
  times, 0.2 s apart, before EXIT_LOCKED, so the wrapper's instant probe of the real lock never makes a starting
  logon poller or `--once` exit; a real second poller exits 0.8 s later. That deferred minor is resolved here.
- Task 12 (TASKS wording): E40's refused alerts.jsonl is a real refusal (a hard link) in place of the patch TASKS
  names, so the whole checked_target path runs; a patch would have to replace `execution.snapshot.checked_target`
  (as Task 10's test does), because patching `core.isolation.checked_target` misses snapshot's import-time binding.

## Deferred minors
```

  Then:

```bash
git status --short
git add execution/poll.py tests/execution_poll.py docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  `git status --short` lists exactly three lines:
  ` M docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`, `?? execution/poll.py` and
  `?? tests/execution_poll.py`. The two stat outputs must be identical, and both must read `3 files changed` (all
  three files are LF). Then commit. In the trailer, replace `<the committing model>` with the name of the model that
  writes this commit, for example `Claude Sonnet 5.5` or `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "feat(execution): the poller, alerts.jsonl and the alert CLI" -m "Task 12: execution/poll.py (python -m execution.poll: --once, the loop, --pending, --mark-sent; one poller per poll.lock, a second exits 0; KIS only under signed code) and tests/execution_poll.py, with the ledger noting the capped sleep and the real alerts refusal; execution/*.py is in the D14 code hash since Task 9, so the code hash changes again; the owner signs the final hash after the plan (spec 12)." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
```

  Afterwards `git status --short` prints nothing.
