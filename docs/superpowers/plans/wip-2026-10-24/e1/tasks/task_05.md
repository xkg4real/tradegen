### Task 5: KIS inquiry (`execution/kis_inquiry.py`)

**Files:**
- Modify: `execution/kis_inquiry.py` (anchors: the module docstring and the `from __future__ import annotations`
  line above `ENDPOINTS = frozenset({`, and the last constant line
  `ACCOUNT_NAMES = ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")`; LF)
- Modify: `tests/execution_fixtures.py` (anchors: the line `import contextlib` of Task 1's import block, and the
  file's last line, `    return Snapshot(**(base | fields))`, the end of Task 4's `snap()`; LF)
- Create: `tests/execution_kis.py` (LF, UTF-8, no BOM)
- Modify, only when this task records a drift ruling (Step 1, Edit 3a or the Step 4 cockpit run):
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (anchor: the `## Deferred minors`
  heading; one line above it, in the `## Drift rulings` section; LF)
- Test: `tests/execution_kis.py`

`tests/execution_acceptance.py` (Task 1) already lists `"execution_kis"` in MODULES and skips the module until this
task creates it. The guards of `tests/execution_guards.py` (Tasks 1 and 2) already scan `execution/kis_inquiry.py`;
from this task on they see its full text: the KIS token rule (every `/uapi/` string one of the nine GET paths), the
TR rule, the transport-only rule (one `keys.read(ACCOUNT_NAMES)`; every `request` call passes the literal `"GET"`),
the import allowlist and no clock. No CRLF file, no compliance file and no file outside the three above changes,
except the ledger line of a drift ruling.

**Interfaces:**
- Consumes:
  - Task 2 (`execution/kis_inquiry.py`, contract 7): `ENDPOINTS`, `TR_IDS` (a frozenset of nine `(path, tr_id)`
    pairs, every TR id ending in R), `PUBLIC = frozenset()`, `ACCOUNT_NAMES = ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")`.
  - Task 2 (`execution.keys`, contract 5): `read(names) -> tuple[str, ...]`, raising `KeyMissing(name)` (`.name` is
    the missing key's name; the message holds no value).
  - Tasks 2 and 3 (`execution.transport`, contract 6): `request(venue, method, path, params=None, *, tr_id=None) ->
    Answer` (`.body` the parsed JSON, `.server_utc` aware UTC from the Date header or None, `.received_utc`,
    `.sha256` hex over the raw body); `AuthError` (subclass of `InquiryError`), `InquiryError`, `InquiryRefused`,
    `KeyMissing` (re-exported from keys). Transport issues, caches and reuses the KIS token itself (one
    `POST /oauth2/tokenP` before the first GET when the cache in the state root holds no valid token), sends the
    pinned `tr_id` and `custtype: P` headers, raises `AuthError` on HTTP 401/403 or a code in `AUTH_CODES["kis"]`
    (`EGW00103` and `EGW00205` among them), adds the token to `_bad_tokens` and raises `InquiryError` on `EGW00121` to
    `EGW00123`, and raises `InquiryError` naming venue, path, HTTP status and `msg_cd` on `rt_cd != "0"` (E15).
    Tests only: `transport._bad_tokens` and `transport.checked_target` (module globals looked up at call time).
  - Task 4 (`execution.snapshot`, contract 8): `FieldError` (`args[0]` is the field's name), `Holding(units,
    locked=0.0, avg_cost=None)`, `Order(id, symbol, side, units, price=None)`, `Move(id, symbol, counter="", side,
    units)`, `Snapshot` (its `__post_init__` refuses a non-finite float and a flag outside `FLAGS`, which holds
    `keys_missing`, `code_unsigned` and `auth_error`), `failed(venue, utc, error, *, flags=frozenset(),
    server_utc=None, clock_offset_s=None)`.
  - `core.compliance.model` (repo, unchanged until Task 9): `Context`, `is_sealed(ctx)` (False for None and for a
    Context that `seal_context` did not build), `iso_utc(moment)`, `KST`.
  - Tests: `tests.compliance_fixtures.ctx(**overrides)` (`F.ctx()`: sealed, `code_signed=True`, any field
    overridable); `tests.execution_fixtures` (Tasks 1 to 4): `NOW` (2026-10-24 00:00:00 UTC, 09:00 KST),
    `DATE_HEADER`, `FAKE_KEYS` (`KIS_ACCOUNT_8` `"12345678"`, `KIS_ACCOUNT_PD` `"01"`), `Refused`, `STRAYS`,
    `fake_keys(**overrides)` (a None override removes that name from `os.environ`), `serve(routes, *,
    date=DATE_HEADER)` (routes map `(method, path)` to a body, a `(status, body)` pair or a callable
    `call -> (status, headers, body_bytes)`; it yields the list of call records, each with `"method"`, `"url"` and
    `"headers"`; an unrouted call records a stray and raises `AssertionError`), and the wrapper's `isolated()` (the
    refusing `_send`, `transport._clock = lambda: NOW`, a fresh `_next_issue_at`, `_okx_offset_s` and `_bad_tokens`
    per test, `keys._ENV_FILE` a missing file in the temp home).
- Produces:
  - `execution/kis_inquiry.py`: `snapshot(now: datetime, ctx: model.Context) -> Snapshot`. Its first statement
    returns `failed("kis", iso_utc(now), "code not signed", flags=frozenset({"code_unsigned"}))` unless
    `model.is_sealed(ctx) and ctx.code_signed is True` (E42): no key, account number or token is read and nothing is
    sent. Otherwise it reads `keys.read(ACCOUNT_NAMES)` (8 and 2 ASCII digits, else the failed snapshot
    `"kis: KIS account number is not 8 + 2 digits"` before any request), sends the nine GETs of contract 9 in
    order, and returns an ok snapshot with `holdings`, `cash` (`"KRW"`: the D+2 `prvs_rcdl_excc_amt`; each foreign
    currency: `frcr_dncl_amt_2`), `deposit_krw` (`dnca_tot_amt`), `prices_krw` (domestic `prpr`; overseas
    `now_pric2` times the currency's `frst_bltn_exrt`; each currency's rate), `open_orders`, `fills`
    (`f"{ord_dt}-{odno}"` ids), `loans` (exactly the keys `tot_loan_amt`, `loan_amt`, `crdt_fncg_amt`,
    `thdt_rcvb_amt`, `rcvb_amt`), `server_utc` and `clock_offset_s` from the first answer with a Date header, and
    `response_sha256` keyed by the nine paths (never a query). Venue errors (E38: `KeyMissing`, `AuthError`,
    `InquiryRefused`, `InquiryError`, `LookupError`, `ValueError` with `FieldError`, `TypeError`,
    `AttributeError`, `ArithmeticError`) give a failed snapshot: `keys missing: <name>` with flag `keys_missing`;
    `str(exc)` with flag `auth_error`; `str(exc)` of a refusal or an inquiry error; `kis: <path>: field <name>`;
    `kis: <path>: <TypeName>`. Anything else propagates (the suite's `Refused`, the router's `AssertionError`, a
    `checked_target` `RuntimeError`).
  - Private to `execution/kis_inquiry.py` (contract: a name the contract does not list is a private helper of its
    own module): the path constants `_BALANCE`, `_OPEN`, `_FILLS`, `_ASSETS`, `_MARGIN`, `_US_BALANCE`, `_US_OPEN`,
    `_US_FILLS`, `_US_CASH`; `_CONTAINED`; `_calls(cano, prdt, today)` (the nine `(path, params)` pairs in order);
    `_failed(utc, path, exc, answers) -> Snapshot`; `_clock_of(answers) -> (server_utc, clock_offset_s)`;
    `_field(row, name)`, `_text(row, name) -> str`, `_num(row, name) -> float`, `_one(body, name) -> dict`,
    `_list(body, name) -> list` (each raises `FieldError(name)`); `_side(row)`, `_holding(row, units)`,
    `_digits(value, n)`.
  - `tests/execution_fixtures.py`: `KIS_ROUTES` (route name -> `(method, path)`, the token POST included),
    `KIS_BODIES` (route name -> the contract 3.2 answer), `KIS_ROWS` (one row for each list the answers leave empty:
    `psbl_rvsecncl`, `nccs`, `ccnl`), `_routes(table, bodies, changes) -> dict` (Tasks 6 and 7 reuse it) and
    `kis_routes(**changes) -> dict`: `(method, path) -> answer` for `serve()` (contract 3.2; keyed as `serve()` takes
    them, so the three venues' routes merge with `|`), a fresh deep copy of each default answer, a keyword named
    after a `KIS_ROUTES` key replacing that answer with any `serve()` answer form, a None value dropping the route,
    an unknown name a `KeyError`.
  - Later users: Task 8 (`cash`, `holdings`, `prices_krw`), Task 10 (`deposit_krw`, `cash`, `prices_krw` of an ok
    KIS snapshot), Task 11 (`open_orders`, `fills`, `loans`, `flags`, `clock_offset_s`, the `code_unsigned` flag),
    Task 12 (`poll_once` calls `kis_inquiry.snapshot(now, ctx)` last with the context it loaded first; its tests
    route `EF.kis_routes() | EF.upbit_routes() | EF.okx_routes()`).

**Plan decisions used:** E42 and E24 (E1R2-9: KIS sends only under the poll's sealed, signed context), E14 (the
account number read only here, checked as 8 + 2 digits), E16 (D+2 cash, `deposit_krw`, the recent windows), E17
(US only, first page only; no rate, no price), E26 (the five KIS loan figures), E37 (error text from names only),
E38 (venue errors contained, nothing else), E39 (`clock_offset_s` at receipt), E10 and E36 (the allowlists stay in
this module; every `request` call passes the literal `"GET"`, and one `keys.read`), E15 (answers are checked in
transport), E2 (imports), E1R2-5 (`[assumed]` fixture fields accepted; a live mismatch fails KIS closed).

Design notes (read before Step 3):
- Contract 9 writes the gate's return through the module name, `snapshot.failed`; inside this module the function
  itself is named `snapshot`, so `failed` is imported from `execution.snapshot` and the gate reads
  `return failed("kis", model.iso_utc(now), "code not signed", flags=frozenset({"code_unsigned"}))`.
- The nine GETs go out in contract 9's order. The overseas cash answer (CTRP6504R) is parsed first because the
  overseas holdings' KRW prices need its rates; a holding whose currency has no rate gets no price, and positions then
  fail closed (E17).
- `_num` takes a string only (KIS sends every number as a string, contract 3.2): `""` is 0.0, commas are dropped
  (`"1,234,567"` is 1234567.0), and a JSON number, None, a bool, `"1,234,567KRW"`, `nan` or `inf` is
  `FieldError(name)`, whose text names the field and never the value (E37).
- A live mismatch fails KIS closed (E1R2-5) rather than passing as an odd value: every id, symbol and currency
  (`pdno`, `ovrs_pdno`, `crcy_cd`, `tr_crcy_cd`, `odno`, `ord_dt`) is read through `_text` (a non-empty string, else
  `FieldError(name)`), so no dict key is None or a number; `_holding` refuses an `ord_psbl_qty` below 0 or above the
  units held (`FieldError("ord_psbl_qty")`), so `locked` is never negative. `_side` keeps contract 9's mapping
  (`"01"` sell, anything else buy).
- A failed snapshot keeps the venue time read so far (`server_utc`, `clock_offset_s` from the answers already in),
  so CLOCK_SKEW still sees a poll that failed later (E39).
- The token POST is transport's: it is not in `answers`, so `response_sha256` and the venue time come from the nine
  GETs only. A test that removes `KIS_APP_KEY` runs last in its loop because that attempt starts transport's
  70-second issue gap (`_next_issue_at`, reset per test by `isolated()`).

- [ ] **Step 1: Write the failing test(s)**

  First confirm the inputs. Overlap check with the PowerShell tool (it must print nothing; otherwise wait and run it
  again):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
test ! -e tests/execution_kis.py && grep -c '"execution_kis"' tests/execution_acceptance.py
git ls-files --eol execution/kis_inquiry.py tests/execution_fixtures.py
grep -c '^ACCOUNT_NAMES = ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")$' execution/kis_inquiry.py
grep -n '^from __future__ import annotations$\|^ENDPOINTS = frozenset({$' execution/kis_inquiry.py
grep -c '^import contextlib$' tests/execution_fixtures.py; grep -c '^import copy$' tests/execution_fixtures.py; tail -n 1 tests/execution_fixtures.py
.venv/Scripts/python.exe -c "from execution import kis_inquiry as K, snapshot as S, transport as T; from tests import compliance_fixtures as F, execution_fixtures as EF; print(sorted(n for n in vars(K) if n.isupper()), hasattr(K, 'snapshot'), K.ACCOUNT_NAMES, len(K.TR_IDS), all(hasattr(T, n) for n in ('request', 'AuthError', 'InquiryError', 'InquiryRefused', 'KeyMissing', 'checked_target', '_bad_tokens')), all(callable(getattr(EF, n, None)) for n in ('isolated', 'fake_keys', 'serve', 'snap')), S.failed('kis', '2026-10-24T00:00:00Z', 'x', flags=frozenset({'code_unsigned'})).ok, F.ctx().code_signed)"
```

  Expected, line by line: `1`; `i/lf    w/lf` for both files; `1`; two lines `<n>:from __future__ import
  annotations` and `<n+2>:ENDPOINTS = frozenset({` (only the module docstring and that import above the constants,
  one blank line between, as Task 2 wrote them); `1`, `0` and `    return Snapshot(**(base | fields))`; then
  `['ACCOUNT_NAMES', 'ENDPOINTS', 'PUBLIC', 'TR_IDS'] False ('KIS_ACCOUNT_8', 'KIS_ACCOUNT_PD') 9 True True False True`.
  Apply the DRIFT RULE (contract 0.6) to any other answer: an `import copy` already present means skip Edit 1a; a
  different last line of `tests/execution_fixtures.py` means use that line as Edit 1b's old_string (the block still
  goes at the very end) and record a one-line ruling in
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`, as the last line of its
  `## Drift rulings` section (Steps 4 and 5 then include that file);
  anything else above `ENDPOINTS`, a missing name or a `snapshot` that already exists means stop and rule.

  Edit 1a, `tests/execution_fixtures.py`, anchor: Task 1's import block (LF). old_string:

```python
import contextlib
```

  new_string:

```python
import contextlib
import copy
```

  Edit 1b, `tests/execution_fixtures.py`, anchor: the end of the file, the last line of Task 4's `snap()` (LF).
  old_string is that line, with no newline after it:

```text
    return Snapshot(**(base | fields))
```

  new_string is the same line, then `\n\n\n` (one newline ending the old last line, then two empty lines), then the
  block below from its first `#` up to and including `    return _routes(KIS_ROUTES, KIS_BODIES, changes)`, with NO
  newline after it. The file's existing final newline, which old_string left outside the match, then closes the
  block, so the file still ends in exactly one newline. The block (the KIS answers; top-level code, so it starts in
  column 0 on the third line after the `return`):

```python
# --------------------------------------------------------------------------- #
# Task 5: the KIS answers (contract 3.2; shaped like the KIS docs' examples, never captured from a live account).
# Not in the research tables, accepted as [assumed] (E1R2-5; a live mismatch fails KIS closed): the output1/output2
# containers of inquire-account-balance, the output container of intgr-margin and inquire-ccnl, the inquire-nccs row
# fields, ord_dt and sll_buy_dvsn_cd of an inquire-ccnl row, and crcy_cd of inquire-present-balance.
# --------------------------------------------------------------------------- #
KIS_ROUTES = {
    "token": ("POST", "/oauth2/tokenP"),
    "balance": ("GET", "/uapi/domestic-stock/v1/trading/inquire-balance"),
    "psbl_rvsecncl": ("GET", "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"),
    "daily_ccld": ("GET", "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"),
    "account_balance": ("GET", "/uapi/domestic-stock/v1/trading/inquire-account-balance"),
    "intgr_margin": ("GET", "/uapi/domestic-stock/v1/trading/intgr-margin"),
    "ovrs_balance": ("GET", "/uapi/overseas-stock/v1/trading/inquire-balance"),
    "nccs": ("GET", "/uapi/overseas-stock/v1/trading/inquire-nccs"),
    "ccnl": ("GET", "/uapi/overseas-stock/v1/trading/inquire-ccnl"),
    "present_balance": ("GET", "/uapi/overseas-stock/v1/trading/inquire-present-balance"),
}
KIS_BODIES = {
    "token": {"access_token": "test-token-1", "token_type": "Bearer", "expires_in": 86400,
              "access_token_token_expired": "2026-10-25 09:00:00"},
    "balance": {"rt_cd": "0", "msg_cd": "KIOK0510", "msg1": "", "ctx_area_fk100": "", "ctx_area_nk100": "",
                "output1": [{"pdno": "005930", "prdt_name": "005930", "hldg_qty": "1", "ord_psbl_qty": "1",
                             "pchs_avg_pric": "60000.0000", "pchs_amt": "60000", "prpr": "61000", "evlu_amt": "61000",
                             "loan_dt": "", "loan_amt": "0"}],
                "output2": [{"dnca_tot_amt": "21000", "nxdy_excc_amt": "20000", "prvs_rcdl_excc_amt": "20000",
                             "tot_evlu_amt": "81000", "nass_amt": "81000", "scts_evlu_amt": "61000",
                             "tot_loan_amt": "0"}]},
    "psbl_rvsecncl": {"rt_cd": "0", "msg_cd": "", "msg1": "", "output": []},
    "daily_ccld": {"rt_cd": "0", "output1": [{"ord_dt": "20261023", "odno": "0000123455", "orgn_odno": "",
                                              "sll_buy_dvsn_cd": "02", "pdno": "005930", "ord_qty": "1",
                                              "ord_unpr": "61000", "ord_tmd": "093000", "tot_ccld_qty": "1",
                                              "avg_prvs": "61000", "tot_ccld_amt": "61000", "cncl_yn": "N",
                                              "rmn_qty": "0", "rjct_qty": "0"}], "output2": {}},
    "account_balance": {"rt_cd": "0", "output1": [],
                        "output2": {"tot_asst_amt": "81000", "nass_tot_amt": "81000", "tot_dncl_amt": "21000",
                                    "dncl_amt": "21000", "frcr_evlu_tota": "0", "ovrs_stck_evlu_amt1": "0",
                                    "thdt_rcvb_amt": "0", "crdt_fncg_amt": "0"}},
    "intgr_margin": {"rt_cd": "0", "output": {"acmga_rt": "20", "acmga_pct100_aptm_rson": "",
                                              "stck_cash_ord_psbl_amt": "20000", "rcvb_amt": "0"}},
    "ovrs_balance": {"rt_cd": "0", "output1": [{"ovrs_pdno": "AAPL", "ovrs_cblc_qty": "1", "ord_psbl_qty": "1",
                                                "pchs_avg_pric": "200.0000", "frcr_pchs_amt1": "200",
                                                "ovrs_stck_evlu_amt": "210", "now_pric2": "210.00000000",
                                                "frcr_evlu_pfls_amt": "10", "tr_crcy_cd": "USD",
                                                "ovrs_excg_cd": "NASD"}],
                     "output2": {"tot_evlu_pfls_amt": "10", "frcr_buy_amt_smtl1": "200"}},
    "nccs": {"rt_cd": "0", "output": []},
    "ccnl": {"rt_cd": "0", "output": []},
    "present_balance": {"rt_cd": "0", "output1": [],
                        "output2": [{"crcy_cd": "USD", "frcr_dncl_amt_2": "5.00", "frcr_drwg_psbl_amt_1": "5.00",
                                     "frst_bltn_exrt": "1390.50"}],
                        "output3": {"tot_asst_amt": "0", "tot_dncl_amt": "0", "wdrw_psbl_tot_amt": "0",
                                    "frcr_use_psbl_amt": "0", "frcr_evlu_tota": "0"}},
}
KIS_ROWS = {   # one row for each list the default answers leave empty
    "psbl_rvsecncl": {"odno": "0000123456", "orgn_odno": "", "pdno": "005930", "ord_qty": "1", "ord_unpr": "60000",
                      "tot_ccld_qty": "0", "psbl_qty": "1", "sll_buy_dvsn_cd": "02", "ord_dvsn_cd": "00",
                      "excg_id_dvsn_cd": "KRX"},
    "nccs": {"odno": "0000223456", "pdno": "AAPL", "ft_ord_qty": "1", "ft_ord_unpr3": "200", "nccs_qty": "1",
             "sll_buy_dvsn_cd": "02"},
    "ccnl": {"ord_dt": "20261023", "odno": "0000223455", "orgn_odno": "", "pdno": "AAPL", "ft_ord_qty": "1",
             "ft_ord_unpr3": "200", "ft_ccld_qty": "1", "ft_ccld_unpr3": "200", "ft_ccld_amt3": "200", "nccs_qty": "0",
             "prcs_stat_name": "", "rjct_rson": "", "tr_crcy_cd": "USD", "sll_buy_dvsn_cd": "02"},
}


def _routes(table: dict, bodies: dict, changes: dict) -> dict:
    """{(method, path): answer} for serve(): a fresh deep copy of every default answer, or the change named after its
    route (any answer form serve() takes, used as given); a None change drops that route. An unknown name is a
    KeyError, so a typo cannot pass silently."""
    unknown = sorted(set(changes) - set(table))
    if unknown:
        raise KeyError(f"no such route: {unknown}")
    out = {}
    for name, route in table.items():
        answer = changes[name] if name in changes else copy.deepcopy(bodies[name])
        if answer is not None:
            out[route] = answer
    return out


def kis_routes(**changes) -> dict:
    """serve() routes for every KIS call, the token POST included, keyed (method, path) as serve() takes them, so the
    three venues' routes merge with `|`. A keyword named after a KIS_ROUTES key replaces that answer."""
    return _routes(KIS_ROUTES, KIS_BODIES, changes)
```

  Check the end of the file from the repo root; it must print `True False False` (the block ends the file, no blank
  line after it, no CR anywhere):

```bash
.venv/Scripts/python.exe -c "import pathlib; b = pathlib.Path('tests/execution_fixtures.py').read_bytes(); print(b.endswith(b'    return _routes(KIS_ROUTES, KIS_BODIES, changes)\n'), b.endswith(b'\n\n'), b'\r' in b)"
```

  Edit 1c: create `tests/execution_kis.py` with exactly this content:

```python
"""KIS inquiry (E1 Task 5; contract C9; spec 5 KIS, 6; E14, E16, E17, E26, E37, E38, E39, E42).

Every send goes to `EF.serve` (the KIS answers of contract 3.2, never a live one); the suite's wrapper refuses any
other send. Every ok case passes `F.ctx()` (sealed, `code_signed=True`): KIS sends nothing under unsigned code.
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from core.compliance import model
from execution import keys, kis_inquiry, transport
from execution.snapshot import Holding, Move, Order
from tests import compliance_fixtures as F
from tests import execution_fixtures as EF

ROOT = Path(__file__).resolve().parents[1]
PATH = {name: route[1] for name, route in EF.KIS_ROUTES.items()}
GETS = ("balance", "psbl_rvsecncl", "daily_ccld", "account_balance", "intgr_margin", "ovrs_balance", "nccs", "ccnl",
        "present_balance")                          # the order of contract C9
ACCOUNT_ERROR = "kis: KIS account number is not 8 + 2 digits"


def _path(call: dict) -> str:
    return urlsplit(call["url"]).path


def _pairs(call: dict) -> list[tuple[str, str]]:
    """The sent query as (key, value) pairs, exactly as on the wire (not unquoted)."""
    return [tuple(p.split("=", 1)) for p in urlsplit(call["url"]).query.split("&")]


def _only(calls: list, name: str) -> dict:
    found = [c for c in calls if _path(c) == PATH[name]]
    assert len(found) == 1, (name, len(found))
    return found[0]


def _full() -> dict:
    """kis_routes() with one row in each list the defaults leave empty."""
    routes = EF.kis_routes()
    for name in ("psbl_rvsecncl", "nccs", "ccnl"):
        routes[EF.KIS_ROUTES[name]]["output"] = [dict(EF.KIS_ROWS[name])]
    return routes


def _run(routes: dict, ctx=None, **key_changes):
    """One snapshot at EF.NOW under the fake keys (a keyword changes one; None removes it); (snapshot, calls)."""
    with EF.fake_keys(**key_changes), EF.serve(routes) as calls:
        snap = kis_inquiry.snapshot(EF.NOW, F.ctx() if ctx is None else ctx)
    return snap, calls


def _no_key_read(names):
    raise AssertionError(f"keys.read({tuple(names)}) under unsigned code")


def _names_only(error: str) -> bool:
    """True when a failure text holds neither the fake account number nor the account field (E37)."""
    return EF.FAKE_KEYS["KIS_ACCOUNT_8"] not in error and "CANO" not in error


def test_the_signed_code_gate_is_the_first_statement():
    tree = ast.parse((ROOT / "execution" / "kis_inquiry.py").read_text(encoding="utf-8"))
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "snapshot"), None)
    assert fn is not None, "kis_inquiry.snapshot is not defined"
    body = fn.body[1:] if ast.get_docstring(fn) else fn.body
    gate = body[0]
    assert isinstance(gate, ast.If) and not gate.orelse, ast.unparse(gate)
    assert ast.unparse(gate.test) == "not (model.is_sealed(ctx) and ctx.code_signed is True)", ast.unparse(gate.test)
    assert [ast.unparse(s) for s in gate.body] == [
        "return failed('kis', model.iso_utc(now), 'code not signed', flags=frozenset({'code_unsigned'}))"]


def test_kis_sends_nothing_and_reads_no_key_unless_the_code_is_signed():
    unsealed = dataclasses.replace(F.ctx())
    assert not model.is_sealed(unsealed)
    for ctx in (F.ctx(code_signed=False), F.ctx(code_signed=1), unsealed, None):
        saved = keys.read
        keys.read = _no_key_read
        try:
            with EF.fake_keys(), EF.serve(_full()) as calls:
                snap = kis_inquiry.snapshot(EF.NOW, ctx)
        finally:
            keys.read = saved
        assert calls == [], [_path(c) for c in calls]                # not even the token POST
        assert not snap.ok and snap.error == "code not signed", snap.error
        assert snap.flags == frozenset({"code_unsigned"}) and snap.utc == "2026-10-24T00:00:00Z"
        assert snap.holdings == {} and snap.response_sha256 == {} and snap.server_utc is None
    snap, calls = _run(_full())
    assert snap.ok and snap.error is None and len(calls) == 10, snap.error   # signed: the token POST and nine GETs


def test_the_full_fixture_gives_every_field():
    snap, _calls = _run(_full())
    assert snap.ok and snap.error is None and snap.flags == frozenset(), snap.error
    assert snap.venue == "kis" and snap.utc == "2026-10-24T00:00:00Z"
    assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0
    assert dict(snap.holdings) == {"005930": Holding(units=1.0, locked=0.0, avg_cost=60000.0),
                                   "AAPL": Holding(units=1.0, locked=0.0, avg_cost=200.0)}
    assert dict(snap.cash) == {"KRW": 20000.0, "USD": 5.0}       # KRW: the D+2 prvs_rcdl_excc_amt, not dnca_tot_amt
    assert snap.deposit_krw == 21000.0                           # dnca_tot_amt (D16 evidence)
    assert dict(snap.prices_krw) == {"005930": 61000.0, "AAPL": 210.0 * 1390.5, "USD": 1390.5}
    assert snap.open_orders == (Order(id="0000123456", symbol="005930", side="buy", units=1.0, price=60000.0),
                                Order(id="0000223456", symbol="AAPL", side="buy", units=1.0, price=200.0))
    assert snap.fills == (Move(id="20261023-0000123455", symbol="005930", counter="KRW", side="buy", units=1.0),
                          Move(id="20261023-0000223455", symbol="AAPL", counter="USD", side="buy", units=1.0))
    assert dict(snap.loans) == {"tot_loan_amt": 0.0, "loan_amt": 0.0, "crdt_fncg_amt": 0.0, "thdt_rcvb_amt": 0.0,
                                "rcvb_amt": 0.0}
    assert snap.deposits == () and snap.withdrawals == () and snap.withdrawal_addresses == ()
    assert snap.key_expiry is None and dict(snap.earn) == {}
    assert set(snap.response_sha256) == {PATH[n] for n in GETS}  # one per path, no query (it holds the account)
    assert all("?" not in k for k in snap.response_sha256)
    assert all(re.fullmatch(r"[0-9a-f]{64}", v) for v in snap.response_sha256.values())


def test_every_call_is_a_get_with_its_pinned_tr_and_the_account_from_keys():
    reads, saved = [], keys.read

    def recording(names):
        reads.append(tuple(names))
        return saved(names)
    keys.read = recording
    try:
        snap, calls = _run(EF.kis_routes(), KIS_ACCOUNT_8="97654310", KIS_ACCOUNT_PD="37")
    finally:
        keys.read = saved
    assert snap.ok, snap.error
    assert reads[0] == ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD") == kis_inquiry.ACCOUNT_NAMES      # before any request
    assert reads.count(kis_inquiry.ACCOUNT_NAMES) == 1
    assert [(c["method"], _path(c)) for c in calls] == [("POST", "/oauth2/tokenP")] + [("GET", PATH[n]) for n in GETS]
    pinned = dict(kis_inquiry.TR_IDS)
    for call in calls[1:]:
        assert call["headers"]["tr_id"] == pinned[_path(call)] and call["headers"]["tr_id"].endswith("R")
        assert _pairs(call)[:2] == [("CANO", "97654310"), ("ACNT_PRDT_CD", "37")], _pairs(call)[:2]
    balance = _pairs(_only(calls, "balance"))
    assert ("INQR_DVSN", "01") in balance and [k for k, _v in balance].count("INQR_DVSN") == 1
    ccnl = _pairs(_only(calls, "ccnl"))
    assert ("PDNO", "%25") in ccnl                               # "%" goes out as %25
    assert ("OVRS_EXCG_CD", "NASD") in ccnl and ("TR_CRCY_CD", "USD") in _pairs(_only(calls, "ovrs_balance"))


def test_the_dates_are_seoul_dates():
    for now, d0, d1, d2 in ((datetime(2026, 10, 23, 14, 59, 59, tzinfo=timezone.utc), "20261023", "20261022",
                             "20261021"),
                            (datetime(2026, 10, 23, 15, 0, 0, tzinfo=timezone.utc), "20261024", "20261023",
                             "20261022")):
        with EF.fake_keys(), EF.serve(EF.kis_routes()) as calls:
            snap = kis_inquiry.snapshot(now, F.ctx())
        assert snap.ok and snap.utc == model.iso_utc(now), snap.error
        daily, ccnl = _pairs(_only(calls, "daily_ccld")), _pairs(_only(calls, "ccnl"))
        assert ("INQR_STRT_DT", d1) in daily and ("INQR_END_DT", d0) in daily, daily
        assert ("ORD_STRT_DT", d2) in ccnl and ("ORD_END_DT", d0) in ccnl, ccnl


def test_server_time_and_offset_come_from_the_first_answer_with_a_date_header():
    no_date = json.dumps(EF.KIS_BODIES["balance"]).encode("utf-8")
    later = json.dumps(EF.KIS_BODIES["present_balance"]).encode("utf-8")
    routes = EF.kis_routes(balance=lambda call: (200, {}, no_date),
                           present_balance=lambda call: (200, {"Date": "Sat, 24 Oct 2026 00:00:45 GMT"}, later))
    with EF.fake_keys(), EF.serve(routes, date="Sat, 24 Oct 2026 00:00:30 GMT"):
        snap = kis_inquiry.snapshot(EF.NOW, F.ctx())
    # the first dated answer (+30 s), not the last one (+45 s)
    assert snap.ok and snap.server_utc == "2026-10-24T00:00:30Z" and snap.clock_offset_s == 30.0, snap


def test_response_sha256_is_per_path_over_the_raw_body():
    raw = json.dumps(EF.KIS_BODIES["present_balance"]).encode("utf-8") + b" "
    snap, _calls = _run(EF.kis_routes(present_balance=lambda call: (200, {"Date": EF.DATE_HEADER}, raw)))
    assert snap.ok and snap.response_sha256[PATH["present_balance"]] == hashlib.sha256(raw).hexdigest()


def test_quantities_sides_and_commas():
    routes = _full()
    balance = routes[EF.KIS_ROUTES["balance"]]
    balance["output1"][0] |= {"hldg_qty": "3", "ord_psbl_qty": "1"}
    balance["output1"].append(dict(balance["output1"][0], pdno="000660", hldg_qty="0", ord_psbl_qty="0"))
    balance["output2"][0]["dnca_tot_amt"] = "1,234,567"
    ovrs = routes[EF.KIS_ROUTES["ovrs_balance"]]["output1"]
    ovrs.append(dict(ovrs[0], ovrs_pdno="MSFT", ovrs_cblc_qty="0"))
    routes[EF.KIS_ROUTES["psbl_rvsecncl"]]["output"] = [dict(EF.KIS_ROWS["psbl_rvsecncl"], sll_buy_dvsn_cd="01"),
                                                        dict(EF.KIS_ROWS["psbl_rvsecncl"], odno="0000123457",
                                                             psbl_qty="0")]
    routes[EF.KIS_ROUTES["nccs"]]["output"] = [dict(EF.KIS_ROWS["nccs"], nccs_qty="", ft_ord_qty="2")]
    fills = routes[EF.KIS_ROUTES["daily_ccld"]]["output1"]
    fills[0]["ord_qty"] = "2"                                    # ordered 2, filled 1: units are the filled ones
    fills.append(dict(fills[0], odno="0000123454", tot_ccld_qty="0"))
    routes[EF.KIS_ROUTES["ccnl"]]["output"] = [dict(EF.KIS_ROWS["ccnl"], sll_buy_dvsn_cd="01"),
                                               dict(EF.KIS_ROWS["ccnl"], odno="0000223454", ft_ccld_qty="0")]
    snap, _calls = _run(routes)
    assert snap.ok, snap.error
    assert dict(snap.holdings) == {"005930": Holding(units=3.0, locked=2.0, avg_cost=60000.0),
                                   "AAPL": Holding(units=1.0, locked=0.0, avg_cost=200.0)}   # zero rows skipped
    assert snap.deposit_krw == 1234567.0                         # KIS may group digits: commas are dropped
    assert snap.open_orders == (Order(id="0000123456", symbol="005930", side="sell", units=1.0, price=60000.0),
                                Order(id="0000223456", symbol="AAPL", side="buy", units=2.0, price=200.0))
    assert snap.fills == (Move(id="20261023-0000123455", symbol="005930", counter="KRW", side="buy", units=1.0),
                          Move(id="20261023-0000223455", symbol="AAPL", counter="USD", side="sell", units=1.0))


def test_the_five_loan_figures():
    routes = EF.kis_routes()
    balance = routes[EF.KIS_ROUTES["balance"]]
    balance["output2"][0]["tot_loan_amt"] = "100"
    balance["output1"].append(dict(balance["output1"][0], pdno="000660", hldg_qty="0", loan_amt="50"))
    balance["output1"][0]["loan_amt"] = "25"
    routes[EF.KIS_ROUTES["account_balance"]]["output2"] |= {"crdt_fncg_amt": "7", "thdt_rcvb_amt": "8"}
    routes[EF.KIS_ROUTES["intgr_margin"]]["output"]["rcvb_amt"] = "9"
    snap, _calls = _run(routes)
    assert snap.ok and dict(snap.loans) == {"tot_loan_amt": 100.0, "loan_amt": 75.0, "crdt_fncg_amt": 7.0,
                                            "thdt_rcvb_amt": 8.0, "rcvb_amt": 9.0}, snap.loans


def test_a_holding_without_a_rate_has_no_price():
    routes = EF.kis_routes()
    routes[EF.KIS_ROUTES["present_balance"]]["output2"] = []
    snap, _calls = _run(routes)
    assert snap.ok and "AAPL" in snap.holdings and "AAPL" not in snap.prices_krw and "USD" not in snap.cash


def test_a_malformed_account_number_fails_before_any_request():
    for acct8, pd in (("9999999", "01"), ("999999999", "01"), ("9999999x", "01"), ("９" * 8, "01"),
                      ("99999999", "1"), ("99999999", "0a"), ("99999999", "013")):
        snap, calls = _run(EF.kis_routes(), KIS_ACCOUNT_8=acct8, KIS_ACCOUNT_PD=pd)
        assert calls == [] and not snap.ok and snap.flags == frozenset(), (acct8, pd)
        assert snap.error == ACCOUNT_ERROR, snap.error
        assert acct8 not in snap.error and pd not in snap.error, snap.error            # names only, never the value


def test_missing_keys_give_keys_missing():
    for name in ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD", "KIS_APP_KEY"):   # the app key last: its attempt starts the 70 s
        snap, calls = _run(EF.kis_routes(), **{name: None})
        assert calls == [] and not snap.ok, name
        assert snap.flags == frozenset({"keys_missing"}) and snap.error == f"keys missing: {name}", snap.error


def test_auth_answers_give_auth_error():
    for answer in ((401, {"rt_cd": "1", "msg_cd": "EGW00205", "msg1": ""}),
                   {"rt_cd": "1", "msg_cd": "EGW00103", "msg1": ""}):
        snap, calls = _run(EF.kis_routes(balance=answer))
        assert not snap.ok and snap.flags == frozenset({"auth_error"}) and snap.error, snap
        assert _path(calls[-1]) == PATH["balance"]               # it stopped at the first GET
        assert "test-token-1" not in snap.error and "test-kis-app" not in snap.error and _names_only(snap.error)


def test_a_token_code_fails_the_snapshot_and_marks_the_token_bad():
    snap, calls = _run(EF.kis_routes(balance={"rt_cd": "1", "msg_cd": "EGW00123", "msg1": ""}))
    assert not snap.ok and snap.flags == frozenset() and snap.error, snap
    assert _path(calls[-1]) == PATH["balance"]
    assert "test-token-1" in transport._bad_tokens and "test-token-1" not in snap.error and _names_only(snap.error)


def test_a_missing_or_malformed_field_fails_closed_with_its_name():
    cases = (("balance", lambda b: b["output2"][0].pop("prvs_rcdl_excc_amt"), "prvs_rcdl_excc_amt"),
             ("present_balance", lambda b: b["output2"][0].pop("crcy_cd"), "crcy_cd"),
             ("intgr_margin", lambda b: b.pop("output"), "output"),
             ("daily_ccld", lambda b: b["output1"][0].pop("ord_dt"), "ord_dt"),
             ("ovrs_balance", lambda b: b.update(output1={}), "output1"),
             ("account_balance", lambda b: b.update(output2=[]), "output2"),
             # the field each value comes from, where the fixture gives a sibling field the same value
             ("present_balance", lambda b: b["output2"][0].pop("frcr_dncl_amt_2"), "frcr_dncl_amt_2"),
             ("ovrs_balance", lambda b: b["output1"][0].pop("now_pric2"), "now_pric2"),
             ("ovrs_balance", lambda b: b["output1"][0].pop("pchs_avg_pric"), "pchs_avg_pric"),
             ("nccs", lambda b: b["output"][0].pop("nccs_qty"), "nccs_qty"),
             ("ccnl", lambda b: b["output"][0].pop("tr_crcy_cd"), "tr_crcy_cd"),
             # a live mismatch fails closed (E1R2-5): more free than held, less than none, an id that is not text
             ("balance", lambda b: b["output1"][0].update(ord_psbl_qty="2"), "ord_psbl_qty"),
             ("ovrs_balance", lambda b: b["output1"][0].update(ord_psbl_qty="-1"), "ord_psbl_qty"),
             ("balance", lambda b: b["output1"][0].update(pdno=""), "pdno"),
             ("ccnl", lambda b: b["output"][0].update(odno=223455), "odno"))
    for name, change, field in cases:
        routes = _full()
        change(routes[EF.KIS_ROUTES[name]])
        snap, _calls = _run(routes)
        assert not snap.ok and snap.flags == frozenset(), (name, field)
        assert snap.error == f"kis: {PATH[name]}: field {field}", snap.error


def test_a_malformed_number_fails_closed_without_its_value():
    for value in ("1,234,567KRW", "9,876,543KRW", "nan", "inf", 21000, None, True):
        routes = EF.kis_routes()
        routes[EF.KIS_ROUTES["balance"]]["output2"][0]["dnca_tot_amt"] = value
        snap, _calls = _run(routes)
        assert not snap.ok and snap.error == f"kis: {PATH['balance']}: field dnca_tot_amt", snap.error
        assert str(value) not in snap.error and "KRW" not in snap.error          # names only, never the value


def test_an_rt_cd_error_fails_closed():
    snap, _calls = _run(EF.kis_routes(intgr_margin={"rt_cd": "1", "msg_cd": "APBK0013", "msg1": "fixture text"}))
    assert not snap.ok and snap.flags == frozenset() and "APBK0013" in snap.error, snap.error
    assert "fixture text" not in snap.error and _names_only(snap.error)
    assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0   # the venue time read so far


def test_a_refused_send_propagates():
    with EF.fake_keys():
        try:
            kis_inquiry.snapshot(EF.NOW, F.ctx())                # no serve(): the suite's refusing stub answers
        except EF.Refused:
            pass
        else:
            raise AssertionError("a refused send became a snapshot")
    assert len(EF.STRAYS) == 1, EF.STRAYS                         # the token POST, refused
    EF.STRAYS.clear()


def test_a_refused_write_propagates():
    def refuse(path, what="path", **kw):
        raise RuntimeError(f"{what} refused (test)")
    saved = transport.checked_target
    transport.checked_target = refuse
    try:
        with EF.fake_keys(), EF.serve(EF.kis_routes()) as calls:
            kis_inquiry.snapshot(EF.NOW, F.ctx())
    except RuntimeError as exc:
        assert "refused (test)" in str(exc) and calls == [], calls   # refused before the token POST, not contained
    else:
        raise AssertionError("a refused write became a snapshot")
    finally:
        transport.checked_target = saved
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check and the run, in one Git Bash command from the repo root:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_kis/
```

  Expected: 19 `FAIL` lines (each preceded by its traceback, on stderr, so the two streams may interleave), exit
  code 1:
  `FAIL execution_kis/test_the_signed_code_gate_is_the_first_statement AssertionError: kis_inquiry.snapshot is not
  defined`, and for each of the other 18 tests `FAIL execution_kis/<test> AttributeError: module
  'execution.kis_inquiry' has no attribute 'snapshot'`; the last line is `0/19 passed, 19 failed, 0 not run`. Any
  other failure (`execution_kis/import`, `KeyError: no such route`, a `NameError` in the fixtures) means Step 1 went
  wrong: fix it before Step 3.

- [ ] **Step 3: Implement**

  Re-read `execution/kis_inquiry.py` first. Two Edit-tool replacements; the file stays LF, and the constants Task 2
  wrote (`ENDPOINTS`, `TR_IDS`, `PUBLIC`, `ACCOUNT_NAMES`) stay byte for byte (Task 2's `test_allowlists_are_pinned`
  checks them).

  Edit 3a, anchor: the module docstring and the future import above `ENDPOINTS = frozenset({` (the file's first six
  lines, as Task 2 created them). old_string, with no newline after the last line:

```python
"""KIS read-only inquiry (E1 spec 5, the KIS table; contract section 7; E10, E14): the endpoint allowlist, the one
pinned TR id per inquiry path (each ends in R) and the names of the two account-number keys. transport.request reads
ENDPOINTS, TR_IDS and PUBLIC at call time. This is the only file in execution/ that may name the KIS account fields
or a KIS trading-domain path; tests/execution_guards.py pins every path and TR id written here. Task 5 adds the
snapshot."""
from __future__ import annotations
```

  DRIFT: if the Edit tool finds no match, an earlier plan reworded Task 2's docstring. Read the file, take its text
  from the first character through the end of the line `from __future__ import annotations` as old_string (Step 1
  already showed that only the docstring and that line sit above the constants), and record a one-line ruling in the
  execution ledger. new_string, with no newline after the last line:

```python
"""KIS read-only inquiry (E1 spec 5 and 6; plan C7, C9): the frozen allowlist, the pinned TR ids and the KIS snapshot
of one poll. The only E1 file that names the KIS account fields. A KIS key can also trade, so `snapshot` reads no
key and sends nothing unless the poll's sealed context says the code on disk is the code the owner signed (E42).
Every list is read on its first page only."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from core.compliance import model
from execution import keys
from execution.snapshot import FieldError, Holding, Move, Order, Snapshot, failed
from execution.transport import AuthError, InquiryError, InquiryRefused, KeyMissing, request
```

  Edit 3b, anchor: the last constant line. old_string:

```python
ACCOUNT_NAMES = ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")
```

  new_string (that line, one blank line, then the snapshot and its helpers):

```python
ACCOUNT_NAMES = ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")

_BALANCE = "/uapi/domestic-stock/v1/trading/inquire-balance"
_OPEN = "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
_FILLS = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
_ASSETS = "/uapi/domestic-stock/v1/trading/inquire-account-balance"
_MARGIN = "/uapi/domestic-stock/v1/trading/intgr-margin"
_US_BALANCE = "/uapi/overseas-stock/v1/trading/inquire-balance"
_US_OPEN = "/uapi/overseas-stock/v1/trading/inquire-nccs"
_US_FILLS = "/uapi/overseas-stock/v1/trading/inquire-ccnl"
_US_CASH = "/uapi/overseas-stock/v1/trading/inquire-present-balance"
_CONTAINED = (KeyMissing, InquiryRefused, InquiryError, LookupError, ValueError, TypeError, AttributeError,
              ArithmeticError)                      # E38: the venue's own errors (AuthError and FieldError included)


def snapshot(now: datetime, ctx: model.Context) -> Snapshot:
    """The KIS snapshot of the poll at `now` (C9); `ctx` is the context that poll loaded first (E24). A venue error
    gives a failed snapshot whose text holds names, paths and codes only (E37, E38); a refused write, the suite's
    refusing stub and a programming error propagate."""
    if not (model.is_sealed(ctx) and ctx.code_signed is True):
        return failed("kis", model.iso_utc(now), "code not signed", flags=frozenset({"code_unsigned"}))
    utc, path, answers = model.iso_utc(now), "", {}
    try:
        cano, prdt = keys.read(ACCOUNT_NAMES)
        if not (_digits(cano, 8) and _digits(prdt, 2)):
            return failed("kis", utc, "kis: KIS account number is not 8 + 2 digits")
        pinned = dict(TR_IDS)
        # ponytail: first page only; a 51st holding or 101st fill is missed; add tr_cont paging when the account grows
        for path, params in _calls(cano, prdt, now.astimezone(model.KST).date()):
            answers[path] = request("kis", "GET", path, params, tr_id=pinned[path])
        body = {p: a.body for p, a in answers.items()}
        path, cash, prices, rates = _US_CASH, {}, {}, {}    # first: the overseas prices need its rates
        for row in _list(body[path], "output2"):
            ccy = _text(row, "crcy_cd")
            cash[ccy] = _num(row, "frcr_dncl_amt_2")
            rates[ccy] = prices[ccy] = _num(row, "frst_bltn_exrt")
        path, holdings = _BALANCE, {}
        rows, total = _list(body[path], "output1"), _one(body[path], "output2")
        cash["KRW"] = _num(total, "prvs_rcdl_excc_amt")     # D+2: a buy not yet settled is not counted twice (E16)
        deposit = _num(total, "dnca_tot_amt")
        loans = {"tot_loan_amt": _num(total, "tot_loan_amt"),
                 "loan_amt": sum((_num(r, "loan_amt") for r in rows), 0.0)}
        for row in rows:
            units = _num(row, "hldg_qty")
            if units > 0:
                holdings[_text(row, "pdno")] = _holding(row, units)
                prices[_text(row, "pdno")] = _num(row, "prpr")
        path = _US_BALANCE
        for row in _list(body[path], "output1"):
            units = _num(row, "ovrs_cblc_qty")
            if units > 0:
                symbol, rate = _text(row, "ovrs_pdno"), rates.get(_text(row, "tr_crcy_cd"))
                holdings[symbol] = _holding(row, units)
                if rate is not None:                        # no rate, no price: positions then fail closed (E17)
                    prices[symbol] = _num(row, "now_pric2") * rate
        path, orders = _OPEN, []
        for row in _list(body[path], "output"):
            units = _num(row, "psbl_qty")
            if units > 0:
                orders.append(Order(id=_text(row, "odno"), symbol=_text(row, "pdno"), side=_side(row), units=units,
                                    price=_num(row, "ord_unpr")))
        path = _US_OPEN
        for row in _list(body[path], "output"):
            orders.append(Order(id=_text(row, "odno"), symbol=_text(row, "pdno"), side=_side(row),
                                units=_num(row, "nccs_qty") or _num(row, "ft_ord_qty"),
                                price=_num(row, "ft_ord_unpr3")))
        fills = []
        for path, rows_name, units_name in ((_FILLS, "output1", "tot_ccld_qty"), (_US_FILLS, "output", "ft_ccld_qty")):
            for row in _list(body[path], rows_name):
                units = _num(row, units_name)
                if units > 0:
                    counter = "KRW" if path == _FILLS else _text(row, "tr_crcy_cd")
                    fills.append(Move(id=f"{_text(row, 'ord_dt')}-{_text(row, 'odno')}", symbol=_text(row, "pdno"),
                                      counter=counter, side=_side(row), units=units))
        path = _ASSETS
        assets = _one(body[path], "output2")
        loans["crdt_fncg_amt"] = _num(assets, "crdt_fncg_amt")
        loans["thdt_rcvb_amt"] = _num(assets, "thdt_rcvb_amt")
        path = _MARGIN
        loans["rcvb_amt"] = _num(_one(body[path], "output"), "rcvb_amt")
        server_utc, offset = _clock_of(answers)
        return Snapshot(venue="kis", utc=utc, server_utc=server_utc, clock_offset_s=offset, ok=True,
                        holdings=holdings, cash=cash, deposit_krw=deposit, open_orders=tuple(orders),
                        fills=tuple(fills), loans=loans, prices_krw=prices,
                        response_sha256={p: a.sha256 for p, a in answers.items()})   # paths only, never a query
    except _CONTAINED as exc:
        return _failed(utc, path, exc, answers)


def _calls(cano: str, prdt: str, today: date) -> tuple[tuple[str, list[tuple[str, str]]], ...]:
    """(path, params) of the nine GETs in their order (C9); the dates are Seoul dates."""
    d0, d1, d2 = (f"{today - timedelta(days=n):%Y%m%d}" for n in (0, 1, 2))
    acct = [("CANO", cano), ("ACNT_PRDT_CD", prdt)]
    return (
        (_BALANCE, acct + [("AFHR_FLPR_YN", "N"), ("OFL_YN", ""), ("INQR_DVSN", "01"), ("UNPR_DVSN", "01"),
                           ("FUND_STTL_ICLD_YN", "N"), ("FNCG_AMT_AUTO_RDPT_YN", "N"), ("PRCS_DVSN", "00"),
                           ("CTX_AREA_FK100", ""), ("CTX_AREA_NK100", "")]),
        (_OPEN, acct + [("CTX_AREA_FK100", ""), ("CTX_AREA_NK100", ""), ("INQR_DVSN_1", "0"),
                        ("INQR_DVSN_2", "0")]),
        (_FILLS, acct + [("INQR_STRT_DT", d1), ("INQR_END_DT", d0), ("SLL_BUY_DVSN_CD", "00"), ("INQR_DVSN", "00"),
                         ("PDNO", ""), ("CCLD_DVSN", "01"), ("ORD_GNO_BRNO", ""), ("ODNO", ""),
                         ("INQR_DVSN_3", "00"), ("INQR_DVSN_1", ""), ("EXCG_ID_DVSN_CD", "ALL"),
                         ("CTX_AREA_FK100", ""), ("CTX_AREA_NK100", "")]),
        (_ASSETS, acct + [("INQR_DVSN_1", ""), ("BSPR_BF_DT_APLY_YN", "")]),
        (_MARGIN, acct + [("CMA_EVLU_AMT_ICLD_YN", "N"), ("WCRC_FRCR_DVSN_CD", "01"),
                          ("FWEX_CTRT_FRCR_DVSN_CD", "01")]),
        (_US_BALANCE, acct + [("OVRS_EXCG_CD", "NASD"), ("TR_CRCY_CD", "USD"), ("CTX_AREA_FK200", ""),
                              ("CTX_AREA_NK200", "")]),
        (_US_OPEN, acct + [("OVRS_EXCG_CD", "NASD"), ("SORT_SQN", "DS"), ("CTX_AREA_FK200", ""),
                           ("CTX_AREA_NK200", "")]),
        (_US_FILLS, acct + [("PDNO", "%"), ("ORD_STRT_DT", d2), ("ORD_END_DT", d0), ("SLL_BUY_DVSN", "00"),
                            ("CCLD_NCCS_DVSN", "01"), ("OVRS_EXCG_CD", "NASD"), ("SORT_SQN", "DS"), ("ORD_DT", ""),
                            ("ORD_GNO_BRNO", ""), ("ODNO", ""), ("CTX_AREA_NK200", ""), ("CTX_AREA_FK200", "")]),
        (_US_CASH, acct + [("WCRC_FRCR_DVSN_CD", "02"), ("NATN_CD", "000"), ("TR_MKET_CD", "00"),
                           ("INQR_DVSN_CD", "00")]),
    )


def _failed(utc: str, path: str, exc: Exception, answers: dict) -> Snapshot:
    """A contained venue error as a failed snapshot (E38), keeping the venue time read so far (E39); the text is
    built from names only, never str() of a parse or network error (E37)."""
    if isinstance(exc, KeyMissing):
        error, flags = f"keys missing: {exc.name}", frozenset({"keys_missing"})
    elif isinstance(exc, AuthError):
        error, flags = str(exc), frozenset({"auth_error"})
    elif isinstance(exc, (InquiryRefused, InquiryError)):
        error, flags = str(exc), frozenset()
    elif isinstance(exc, FieldError):
        error, flags = f"kis: {path}: field {exc.args[0]}", frozenset()
    else:
        error, flags = f"kis: {path}: {type(exc).__name__}", frozenset()
    server_utc, offset = _clock_of(answers)
    return failed("kis", utc, error, flags=flags, server_utc=server_utc, clock_offset_s=offset)


def _clock_of(answers: dict) -> tuple[str | None, float | None]:
    """server_utc and clock_offset_s from the first answer with a Date header (E39)."""
    for answer in answers.values():
        if answer.server_utc is not None:
            return model.iso_utc(answer.server_utc), (answer.server_utc - answer.received_utc).total_seconds()
    return None, None


def _field(row, name: str):
    """row[name]; FieldError(name) when row is not a dict or lacks it (E37)."""
    if not isinstance(row, dict) or name not in row:
        raise FieldError(name)
    return row[name]


def _text(row, name: str) -> str:
    """row[name] as a non-empty string (an id, a symbol, a currency or a date); otherwise FieldError(name)."""
    value = _field(row, name)
    if not isinstance(value, str) or not value:
        raise FieldError(name)
    return value


def _num(row, name: str) -> float:
    """A finite number from a KIS string ("" is 0, commas dropped); otherwise FieldError(name), never the value."""
    value = _field(row, name)
    if not isinstance(value, str):
        raise FieldError(name)
    try:
        number = 0.0 if value == "" else float(value.replace(",", ""))
    except ValueError:
        raise FieldError(name) from None
    if not math.isfinite(number):
        raise FieldError(name)
    return number


def _one(body, name: str) -> dict:
    """body[name] as one dict: the dict itself, or the first row of a non-empty list."""
    value = _field(body, name)
    if isinstance(value, list) and value:
        value = value[0]
    if not isinstance(value, dict):
        raise FieldError(name)
    return value


def _list(body, name: str) -> list:
    """body[name], which must be a list."""
    rows = _field(body, name)
    if not isinstance(rows, list):
        raise FieldError(name)
    return rows


def _side(row) -> str:
    return "sell" if _field(row, "sll_buy_dvsn_cd") == "01" else "buy"


def _holding(row, units: float) -> Holding:
    free = _num(row, "ord_psbl_qty")
    if not 0.0 <= free <= units:                    # more free than held is a field mismatch: fail closed (E1R2-5)
        raise FieldError("ord_psbl_qty")
    return Holding(units=units, locked=units - free, avg_cost=_num(row, "pchs_avg_pric"))


def _digits(value: str, n: int) -> bool:
    return len(value) == n and value.isascii() and value.isdigit()
```

  Write `canonical` in lower case if you touch a docstring or comment (the upper-case word holds the account-field
  text), and keep every `/uapi/` string exactly one of the nine paths with no punctuation after it in a comment (the
  KIS token rule reads comments too).

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check before EACH command below (the Git Bash prefix does it). All from the repo root.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_kis/
```

  Expected: 19 lines `PASS execution_kis/test_<name>`, then `19/19 passed, 0 failed, 0 not run` (exit code 0).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/
```

  Expected: only `PASS execution_guards/<name>` lines, then `G/G passed, 0 failed, 0 not run`, where G is the guard
  count recorded at the end of Task 4 (24 as drafted: 18 of Task 1 and 6 of Task 2; this task adds none). The KIS
  token, TR and transport-only rules now read the whole of `execution/kis_inquiry.py`.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; t(); u(); print('T-RO-01 ok')"
```

  Expected: `T-RO-01 ok` (`execution/kis_inquiry.py` holds the account fields and the `/trading/` paths under its
  file-exact text exception; every other T-RO-01 check still runs on it).

  The cockpit suite through the real runner (KEYLESS; restore the results file; `timeout: 300000`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected last lines: `47/47 passed, 0 failed, 0 not run; ...qa\acceptance_results.json` and `exit 0`, exactly
  Task 1's Step 4b cockpit line (test_08, test_09, test_16 and test_18 now read the full `execution/kis_inquiry.py`;
  test_09 accepts its account fields under the file-exact exception). Any other count is a drift ruling recorded in
  the ledger (a `FAIL` line is never a ruling: fix it). The `git checkout` restores the tracked results file
  (Task 13 commits it once).

```bash
git status --short
```

  Expected: exactly ` M execution/kis_inquiry.py`, ` M tests/execution_fixtures.py` and `?? tests/execution_kis.py`,
  plus ` M docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` if a step of this task recorded
  a ruling (nothing under `qa/`, no state file: every test wrote only under its temp home).

- [ ] **Step 5: Commit**

  If a step of this task recorded a ruling, first `git add docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`.
  Then:

```bash
git add execution/kis_inquiry.py tests/execution_fixtures.py tests/execution_kis.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git ls-files --eol execution/kis_inquiry.py tests/execution_fixtures.py tests/execution_kis.py
```

  The two stat outputs must be identical (they catch a CR added to a modified file). They cannot catch a CRLF new
  file, since both count each of its lines as one insertion and .gitattributes (`* -text`) stores it as written; the
  `--eol` lines do. Each of the three lines must start with `i/lf    w/lf` (the rest is `attr/-text` and the path;
  git lists them sorted by path). Any other start (`i/crlf`, `i/mixed`) means stop: rewrite that file with LF
  endings using the Write tool, `git add` it again and repeat all three checks. Then commit. In the trailer, replace
  `<the committing model>` with the name of the model that writes this commit, for example `Claude Sonnet 5.5` or
  `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "feat(execution): KIS read-only inquiry, sent only under signed code" -m "Task 5: kis_inquiry.snapshot (nine pinned GETs, D+2 cash, deposit, loans, fills; nothing read or sent unless the poll's sealed context says code_signed, E42), the KIS answers and tests/execution_kis.py." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
```
