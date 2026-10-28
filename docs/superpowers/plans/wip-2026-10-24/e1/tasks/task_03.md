### Task 3: Signing, sending, answers and the KIS token cache

**Files:**
- Modify: `execution/transport.py` (anchors: the last two lines of the module docstring through the end of the
  import block; the whole function `request`; the last three lines of `_query`, which end the file; LF)
- Modify: `tests/execution_fixtures.py` (anchors: the import block; the `finally:` block of `fake_keys()`, which
  ends the file; LF)
- Modify: `tests/execution_transport.py` (anchors: the module docstring through the end of the import block; the
  last four lines of `test_unpatched_send_is_refused_under_the_suite`, which end the file; LF)
- Modify: `tests/execution_guards.py` (anchor: the `TRANSPORT_ONLY` frozenset; LF)
- Test: `tests/execution_transport.py`, `tests/execution_guards.py`

No file is created. No CRLF file, no compliance file, no file under `data/` and no file outside these four changes.

**Interfaces:**
- Consumes:
  - Task 2, `execution/transport.py` (contract 6): `HOSTS`, `CREDENTIALS`, `KIS_TOKEN_PATH`, `TIMEOUT_S` (10.0),
    `RETRY_AFTER_S` (2.0), `PACE_S` (0.2), `OKX_SKEW_LIMIT_S`, `TOKEN_REUSE_MARGIN_S` (120.0), `TOKEN_MIN_GAP_S`
    (70.0), `TOKEN_REISSUE_BLOCK_S` (21600.0), `KIS_TOKEN_CODES`, `AUTH_CODES`; `InquiryRefused`, `InquiryError`,
    `AuthError(InquiryError)`; `Answer(*, body, server_utc, received_utc, sha256)` (frozen, `body` not in the repr);
    `request`'s refusal steps 1-6, unchanged; `require_keys`; `_send` (pinned by `test_send_is_pinned`, untouched);
    `_sleep`, `_clock`, `_next_issue_at`, `_okx_offset_s`, `_bad_tokens`; `_rules(venue)`; `_query(venue, path,
    params) -> str`.
  - Task 2, `execution.keys.read(names) -> tuple[str, ...]` (raises `KeyMissing(name)`).
  - Task 2, `tests/execution_guards.py`: `TRANSPORT_ONLY` (outside transport.py none of its names may be a name, an
    attribute, an imported name or a getattr string) and the six guard tests (24 in the module), unchanged in number.
  - Tasks 1 and 2, `tests/execution_fixtures.py`: `NOW`, `DATE_HEADER`, `FAKE_KEYS`, `_MISSING`, `Refused`, `SLEEPS`,
    `STRAYS`, `fake_keys(**overrides)`, and `isolated(home)` (the refusing `_send`, `_sleep` recording into
    `SLEEPS`, `_clock` returning `NOW`, a fresh `_next_issue_at`, `_okx_offset_s` and `_bad_tokens` per test,
    `keys._ENV_FILE` a missing file in the temp home).
  - Task 2, `tests/execution_transport.py`: `ROOT`, `_T2_BALANCE`, `_T2_SKEW`, `_t2_patched(module, name, value)`,
    `_t2_boom(*args, **kwargs)` (raises AssertionError), `_t2_passes(venue, method, path, params=None, *,
    tr_id=None) -> bool` and `_t2_refused(venue, method, path, params=None, *, tr_id=None) -> str`.
  - Repo: `core.isolation.state_root() -> Path` and `checked_target(path, what="path", *, within=None) -> Path`
    (core/isolation.py:40 and :105); tests only: `data.krx.kis_client._TOKEN_PATH` (kis_client.py:53, fixed at
    import), `KISClient._cached_token(self)` (:146, reuses while `time.time() < expires_at - 120`) and
    `KISClient._store_token(self, token, expires_in)` (:157, writes `{"access_token", "expires_at": time.time() +
    expires_in}` through `checked_target(_TOKEN_PATH)`); `requests.exceptions` (2.34.2: `ConnectTimeout` subclasses
    `ConnectionError`, `ReadTimeout` does not; every one is an `OSError`).
- Produces:
  - `execution/transport.py`:
    - `request(venue, method, path, params=None, *, tr_id=None) -> Answer`, complete: after steps 1-6, per attempt
      `headers, json_body, token = _headers(venue, method, path, query, tr_id, path in public)`, then
      `_send(method, url, headers=headers, params=None, json_body=json_body, timeout=TIMEOUT_S)` with
      `url = HOSTS[venue] + path + ("?" + query if query else "")`; `received_utc = _clock()` right after `_send`
      returns; `_sleep(PACE_S)` after every attempt; a GET once more after `_sleep(RETRY_AFTER_S)` on
      `requests.exceptions.ConnectionError`, HTTP 429 or status >= 500; a POST never; a `ValueError` or `OSError`
      from `_send` becomes `InquiryError(f"{venue} {path}: {type(exc).__name__}") from None`; anything else (the
      suite's `Refused`, the router's `AssertionError`) propagates; the last answer goes through `_check_answer`;
      after a good OKX `/api/v5/public/time`, `_okx_offset_s = int(body["data"][0]["ts"]) / 1000 -
      received_utc.timestamp()` (set to None first, so a malformed answer leaves no offset).
    - `_check_answer(venue, path, status, body_bytes) -> object` (E15): the parsed body of an HTTP 200 answer with
      the venue's success marker (KIS `rt_cd == "0"`, the token POST a non-empty str `access_token`; OKX
      `code == "0"`; Upbit no `error` key). Otherwise, in this order: a KIS inquiry (not the token POST) whose code
      is in `KIS_TOKEN_CODES`, on any status, raises `_TokenRejected` (an `InquiryError`, never an `AuthError`);
      HTTP 401 or 403, or a code in `AUTH_CODES[venue]`, raises `AuthError`; anything else, a 3xx included, raises
      `InquiryError`. Every text is exactly `f"{venue} {path}: HTTP {status}"` plus `f" {code}"` when the venue's
      code is a short plain word (`_CODE`, `[A-Za-z0-9_]{1,40}`), plus `": not JSON"` when the body did not parse.
      The venue's code: KIS `msg_cd`, else `error_code` (the token POST's error field); OKX `code`; Upbit
      `error.name`.
    - `_upbit_jwt(access_key, secret_key, query) -> str`, `_okx_timestamp(moment) -> str`,
      `_okx_sign(secret, timestamp, request_path) -> str`, `_kis_token() -> str`,
      `_read_token(path, now_epoch) -> str | None`, `_write_token(path, tmp, token, expires_at) -> None` (contract
      6, exactly), and the module globals `isolation` and `checked_target`, looked up at call time (tests patch
      `transport.checked_target`; Task 5 relies on it (Task 12 refuses kis_token.json with a hard link instead)).
    - Private to transport.py (the contract does not name them): `_headers(venue, method, path, query, tr_id,
      public) -> (headers, json_body, token)`, `_date(headers) -> datetime | None`, `class _TokenRejected
      (InquiryError)`, `_CODE`, `_code(venue, body) -> str`, `_succeeded(venue, path, body) -> bool`,
      `_b64url(raw) -> str`. `_headers` (it reads the keys and signs) and `_TokenRejected` join `TRANSPORT_ONLY`
      (E36: no other execution module reaches the signing helpers); the other five hold no key and stay off it.
    - Error texts later tasks may see in a snapshot's `error`: `"<venue> <path>: HTTP <status>[ <code>][: not
      JSON]"`, `"<venue> <path>: <ExceptionTypeName>"`, `"kis: no token may be issued yet; KIS skipped this poll"`
      (`InquiryError`) and `"kis: KIS issued a token it had called invalid; no token for 6 hours"` (`AuthError`).
      None holds a key, a token, a URL, a query or an answer's message.
  - `tests/execution_fixtures.py` (contract 3.2): `class Seq(tuple)` (`Seq(first, second)` answers the first call
    with `first`, the second with `second`; a third call is unrouted) and `serve(routes, *, date=DATE_HEADER)`, a
    context manager that yields the list of call records (`{"method", "url", "path", "query", "headers",
    "json_body", "params", "timeout"}`, `headers` a copy). A route
    maps `(method, path)` to a JSON body (dict or list, sent with HTTP 200), to `(status, body)`, to a `Seq` of
    answers or to a callable `call -> (status, headers, body_bytes)`; every answer but a callable's carries
    `{"Date": date}`. A call with params, a timeout other than 10.0 or no answer left appends `"METHOD path"` to
    `STRAYS` and raises `AssertionError("unrouted METHOD path")` (with `": params/timeout"` appended for the first
    two). `serve()` restores `transport._send` on exit, so one test may use it several times. Tasks 5 to 7 and 12
    send only through it; Task 4 appends after its last line.
  - `tests/execution_transport.py`: the `_t3_` helpers and constants and 19 tests (30 in the module).

**Plan decisions used:** E3 (transport: retry, pacing, the KIS token file and format, the 70 s rule, the Upbit JWT,
the OKX signature), E11 (the clock only through `transport._clock`), E12 (the query built once and sent as built;
`params=None` to `_send`), E15 (answer validation, the bad-token rule and the 6-hour block, the `(ValueError,
OSError)` wrapping), E39 (`received_utc` at receipt; the OKX offset from `public/time`), with E13 (the refusal order,
unchanged), E33 (a refused token-cache write is a crash, not a venue error), E36 (transport stays the only way out),
E37 (error text from names and codes only) and E1R2-11 (`_send` stays exactly as pinned). Contract sections 0.2,
0.5, 3.2 (`serve()`, the KIS token answer) and 6; spec 5 steps 3-5, "Token"; the ledger's "KIS token burnt on
refusal" (compliance ledger:239, spec 5 line 143).

Notes for the implementer (read before starting):
- This task runs on branch `e1-account-inquiry` right after Task 2's commit; `git status --short` prints nothing
  first. Run every command from the repo root `C:/Users/whydi/OneDrive/Desktop/TRADEGEN` in Git Bash (the Bash tool).
- Never open, print or edit `.env`. No test here reads it, and no test sends anything: every send goes to
  `tests.execution_fixtures.serve`, which answers synthetic bodies shaped like the venue docs (contract 3.2), and the
  one probe without `serve()` is refused by the suite's stub. `hermetic()` refuses every socket connect anyway.
- All four files were created by Tasks 1 and 2; no earlier plan touches them. Re-read each file before its first
  Edit (DRIFT RULE, contract 0.6): the quoted old text is the anchor. If Task 1 or 2 was executed with different text
  at an anchor, apply the same change to the current text, keep their behaviour, and record a one-line ruling in
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`.
- The kis_client names the shared-cache test reads must still exist (DRIFT RULE; the compliance follow-up changes
  only `token()` there). Step 1 greps them; if one was renamed, use the new name in the test and record the ruling;
  if one is gone, stop and rule.
- `_send` is not touched: `test_send_is_pinned` compares it with `SEND_SOURCE`. The guards of Tasks 1 and 2 hold
  transport.py to: `requests` only as `import requests`, the `requests.Session()` in `_send` and
  `requests.exceptions.ConnectionError` (so the retry check is `isinstance(exc, requests.exceptions.ConnectionError)`,
  which catches `ConnectTimeout` as its subclass); `global` only for `_next_issue_at` and `_okx_offset_s`; no
  attribute assignment (`_bad_tokens.add(token)` mutates the set); no wall clock (only `_clock()`; a datetime's
  `strftime` and `timestamp` read none); every write through `checked_target` (`open(checked_target(tmp, "KIS token
  temp"), "x", encoding="utf-8")`, `checked_target(path.parent, "KIS token folder").mkdir(parents=True,
  exist_ok=True)`, both `os.replace` arguments `checked_target` calls); no `/uapi/` path, Upbit order or withdrawal
  path or TR-shaped token anywhere in transport.py, docstrings and comments included (the venue codes `EGW00121`,
  `HS512` and `SHA512` are not TR-shaped). Step 4 runs those guards.
- Two private choices of this task, made where the contract is silent (both in the Interfaces block):
  `_check_answer` keeps the contract's four parameters, so it signals a token code with the private
  `_TokenRejected`, which `request` catches to put the token it sent into `_bad_tokens` before re-raising; and the
  token-code rule runs before the 401/403 rule, so a token KIS calls invalid is re-issued rather than reported as a
  key failure, whatever the HTTP status. The token is marked bad only when the last answer is judged, so a 5xx
  token-code answer (KIS answers an expired token with HTTP 500 and EGW00123) is retried once, 2 s later, with the
  same token; that is harmless: the snapshot fails with the token-code text and the next poll issues a fresh token.
  A venue code is named in an error text only when it is a short plain word (`_CODE`), so an answer can never put
  its own text into an alert (E37).
- `_write_token` deletes nothing (contract 0.5 bans `unlink` and `os.remove`), so a write that fails after the
  exclusive open (a disk error, or on Windows an `os.replace` refused while the quote client has `kis_token.json`
  open) leaves one uniquely named `.kis_token.<hex>.tmp` in `state_root()`. It is never read or reused; the OSError
  is a crash (E33, E38), and a later issue (the 70 s rule still applies in the same process) gets the same token
  back from KIS (within 6 hours) and writes it through a fresh temp name.
- The order inside `_kis_token` is the point of the ledger item: the folder, the cache and the temp file are checked
  BEFORE `_next_issue_at` is set and before the POST, so a refused target sends nothing and starts no 70 s gap. The
  same temp path, checked then, is the one `_write_token` opens. Headers, and so the KIS token, are rebuilt on every
  attempt (contract 6), so a retried KIS GET reads the cache the first attempt wrote.
- QUANTGEN overlap check before EVERY test command (contract 0.3). Each test command below is one Git Bash command
  that starts with the check, so nothing runs while a `run_all` process is alive; when the check finds a process the
  command prints no summary line (only `exit 1`): wait, then run it again.

- [ ] **Step 1: Write the failing tests**

First confirm the inputs (Git Bash, repo root):

```bash
git status --short
git ls-files --eol execution/transport.py tests/execution_fixtures.py tests/execution_transport.py tests/execution_guards.py
grep -c 'raise InquiryError("transport: sending arrives in Task 3")' execution/transport.py
grep -c '^TRANSPORT_ONLY = frozenset' tests/execution_guards.py
grep -n '^_TOKEN_PATH = \|def _cached_token(self)\|def _store_token(self, token: str, expires_in: float)' data/krx/kis_client.py
```

Expected: `git status --short` prints nothing; each of the four files reads `i/lf    w/lf    attr/-text`; both
counts are `1`; and exactly three kis_client lines, at `5816d3c`:

```
53:_TOKEN_PATH = config.state_root() / "kis_token.json"     # never QUANTGEN's ~/.nextgen token: a refresh would clobber it
146:    def _cached_token(self) -> Optional[str]:
157:    def _store_token(self, token: str, expires_in: float) -> None:
```

(another line number, or another comment after `_TOKEN_PATH`, is fine). A different answer is a drift ruling
(contract 0.6): stop and rule.

1. `tests/execution_fixtures.py` (LF; Edit tool). Re-read the file first.

Edit 1, anchor: the import block at the top of the module (as Task 2 left it). Old text:

```python
import contextlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit
```

New text (adds `json`, for the routed bodies, and `Mapping`, for `serve()`'s signature):

```python
import contextlib
import json
import os
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit
```

Edit 2, anchor: the `finally:` block of `fake_keys()`, the last six lines of the file. old_string is these six
lines, with no newline after the last one:

```python
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
```

new_string = those same six lines, then `\n\n\n` (one newline ending the old last line, then two empty lines), then
the block below from `class Seq(tuple):` up to and including `        transport._send = keep`, with NO newline after
it. The file's existing final newline, which old_string left outside the match, then closes the block, so the file
still ends in exactly one newline. The block (`Seq` and `serve()`):

```python
class Seq(tuple):
    """A serve() route answered one entry per call, in order (`Seq(first, second)` answers the first call with
    `first` and the second with `second`). A call after the last entry is unrouted."""

    def __new__(cls, *answers):
        return super().__new__(cls, answers)


@contextlib.contextmanager
def serve(routes: Mapping, *, date: str = DATE_HEADER) -> Iterator[list[dict]]:
    """transport._send -> a router over `routes` for one block (Task 3; contract 3.2), restored on exit (isolated()
    puts the refusing stub back in any case). A route maps (method, path) to a JSON body (a dict, or a list: Upbit
    answers with lists) sent with HTTP 200, to (status, body), to a Seq of these answers or to a callable
    `call -> (status, headers, body_bytes)`. Every call is recorded, in order, in the list this yields, as a dict of
    method, url, path, query, headers (a copy), json_body, params and timeout. A call with params, a timeout other
    than 10.0 or no answer left appends "METHOD path" to STRAYS and raises AssertionError. Every answer but a
    callable's carries the Date header `date`."""
    from execution import transport
    calls, used = [], {}

    def send(method, url, *, headers, params, json_body, timeout):
        parts = urlsplit(url)
        call = {"method": method, "url": url, "path": parts.path, "query": parts.query, "headers": dict(headers),
                "json_body": json_body, "params": params, "timeout": timeout}
        calls.append(call)
        key = (method, parts.path)
        answer = routes.get(key, _MISSING)
        if isinstance(answer, Seq):
            used[key] = used.get(key, 0) + 1
            answer = answer[used[key] - 1] if used[key] <= len(answer) else _MISSING
        if answer is _MISSING or params is not None or timeout != 10.0:
            STRAYS.append(f"{method} {parts.path}")
            why = "" if answer is _MISSING else ": params/timeout"
            raise AssertionError(f"unrouted {method} {parts.path}{why}")
        if callable(answer):
            return answer(call)
        status, body = answer if isinstance(answer, tuple) else (200, answer)
        return status, {"Date": date}, json.dumps(body).encode("utf-8")

    keep = transport._send
    transport._send = send
    try:
        yield calls
    finally:
        transport._send = keep
```

Check the end of the file from the repo root; it must print `True False False` (the block ends the file, no blank
line after it, no CR anywhere). Task 4's Edit anchors on these last four lines of `serve()`:

```bash
.venv/Scripts/python.exe -c "import pathlib; b = pathlib.Path('tests/execution_fixtures.py').read_bytes(); print(b.endswith(b'        transport._send = keep\n'), b.endswith(b'\n\n'), b'\r' in b)"
```

2. `tests/execution_transport.py` (LF; Edit tool). Re-read the file first.

Edit 1, anchor: the module docstring through the end of the import block (the first 24 lines). Old text:

```python
"""execution/transport.py, its checking half (E1 Task 2; spec 5 "The choke point" steps 1-3, the three endpoint tables;
contract sections 6 and 7; E3, E12, E13, E1R2-11). Task 3 appends the sending half to this file.

Every refusal is checked with keys.read and transport._send both replaced by a function that raises AssertionError,
so a refusal provably comes before any key is read and any send. Nothing here asserts a send or an answer: after
the checks, Task 2's request fails closed, and `_t2_passes` treats that, a key read and a send attempt alike as
"got past every check", so these tests stay true once Task 3 fills the sending half in. Helpers are prefixed `_t2_`
so that Task 3, appending to this file, cannot shadow them.
"""
from __future__ import annotations

import ast
import contextlib
import dataclasses
import math
import os
import types
from pathlib import Path

import requests

from execution import keys, kis_inquiry, upbit_inquiry
from execution import transport as T
from tests import execution_fixtures as F
```

New text (the docstring now covers both tasks; the imports gain `base64`, `hashlib`, `hmac`, `json`, `re`, `time`,
`uuid`, `datetime`, `timedelta`, `timezone` and `urlsplit`):

```python
"""execution/transport.py (E1 Tasks 2 and 3; spec 5 "The choke point", the three endpoint tables, Upbit and OKX
signing, KIS "Token"; contract sections 3.2, 6 and 7; E3, E11, E12, E13, E15, E37, E39, E1R2-11).

Task 2's tests check the refusals with keys.read and transport._send both replaced by a function that raises
AssertionError, so a refusal provably comes before any key is read and any send; `_t2_passes` treats a key read and
a send attempt alike as "got past every check". Task 3's tests (prefixed `_t3_`) send through
tests.execution_fixtures.serve, which records every call and answers from synthetic bodies shaped like the venue
docs (never a live answer); the probe at the end sends with no serve() and is refused by the suite's stub. Every
clock is transport._clock patched to a fixed or scripted moment, and every file is in the suite's temp home.
"""
from __future__ import annotations

import ast
import base64
import contextlib
import dataclasses
import hashlib
import hmac
import json
import math
import os
import re
import time
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

from execution import keys, kis_inquiry, upbit_inquiry
from execution import transport as T
from tests import execution_fixtures as F
```

Edit 2, anchor: the last four lines of `test_unpatched_send_is_refused_under_the_suite`, which end the file. Old
text:

```python
    else:
        raise AssertionError("an unpatched transport._send was not refused under the suite")
    assert F.STRAYS == ["GET /v1/ticker"], F.STRAYS
    F.STRAYS.clear()
```

New text (the same four lines, then the Task 3 block; the new part starts with two blank lines and ends the file with
one newline):

```python
    else:
        raise AssertionError("an unpatched transport._send was not refused under the suite")
    assert F.STRAYS == ["GET /v1/ticker"], F.STRAYS
    F.STRAYS.clear()


# --------------------------------------------------------------------------- #
# Task 3: signing, sending, answers and the KIS token cache (spec 5 steps 3-5, Upbit and OKX signing, KIS "Token";
# contract 3.2 serve(), 6; E3, E11, E12, E15, E37, E39). Every send goes to F.serve, the probe's to the suite's stub.
# --------------------------------------------------------------------------- #
_T3_TOKEN = {"access_token": "test-token-1", "token_type": "Bearer", "expires_in": 86400,
             "access_token_token_expired": "2026-10-25 09:00:00"}       # contract 3.2's KIS token answer
_T3_OK = {"rt_cd": "0", "msg_cd": "KIOK0510", "msg1": "", "output1": [], "output2": []}
_T3_OKX_OK = {"code": "0", "msg": "", "data": []}
_T3_POST = ("POST", "/oauth2/tokenP")
_T3_GET = ("GET", _T2_BALANCE)
_T3_TICKER = ("GET", "/v1/ticker")
_T3_ACCOUNTS = ("GET", "/v1/accounts")
_T3_TIME = "/api/v5/public/time"
_T3_KIS_HOST = "https://openapi.koreainvestment.com:9443"
_T3_TS = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z")
_T3_TMP = re.compile(r"\.kis_token\.[0-9a-f]{12}\.tmp")
_T3_WAIT = "kis: no token may be issued yet; KIS skipped this poll"
_T3_BLOCK = "kis: KIS issued a token it had called invalid; no token for 6 hours"


def _t3_token(name: str) -> dict:
    """The KIS token answer with another token."""
    return dict(_T3_TOKEN, access_token=name)


def _t3_kis():
    """One KIS balance inquiry (TTTC8434R, two parameters); its parsed body."""
    return T.request("kis", "GET", _T2_BALANCE, [("INQR_DVSN", "01"), ("PDNO", "%")], tr_id="TTTC8434R").body


def _t3_raises(kind, fn, *args, **kwargs):
    """The `kind` exception fn(*args, **kwargs) raises; anything else it raises propagates."""
    try:
        fn(*args, **kwargs)
    except kind as exc:
        return exc
    raise AssertionError(f"{getattr(fn, '__name__', fn)} did not raise {kind.__name__}")


def _t3_raise(exc):
    """A serve() route that raises `exc` where _send would."""
    def answer(call):
        raise exc
    return answer


def _t3_raw(status: int, raw: bytes, headers=None):
    """A serve() route answering `raw` bytes with `status` (the Date header unless `headers` are given)."""
    def answer(call):
        return status, {"Date": F.DATE_HEADER} if headers is None else headers, raw
    return answer


def _t3_b64(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _t3_jwt(call: dict) -> tuple[dict, dict]:
    """(header, payload) of the Upbit JWT a recorded call carried, once its HS512 signature over the base64url
    header and payload has been checked with the fake secret."""
    scheme, token = call["headers"]["Authorization"].split(" ")
    head, payload, signature = token.split(".")
    want = hmac.new(F.FAKE_KEYS["UPBIT_SECRET_KEY"].encode(), f"{head}.{payload}".encode(), hashlib.sha512).digest()
    assert scheme == "Bearer" and "=" not in token and _t3_b64(signature) == want, token
    return json.loads(_t3_b64(head)), json.loads(_t3_b64(payload))


def _t3_home() -> Path:
    return Path(os.environ["TRADEGEN_HOME"])


def test_serve_answers_records_and_refuses_strays():
    """The Task 3 fixture (contract 3.2), used through request: a body with HTTP 200 and the Date header, Seq answers
    in order, every call recorded with its params and timeout; a call with params, another timeout, no route or a
    used-up Seq is a stray, recorded and refused; afterwards transport._send is the suite's refusing stub again."""
    stub = T._send
    ticker = [{"market": "KRW-BTC", "trade_price": 100000000.0}]
    with F.fake_keys(), F.serve({_T3_TICKER: ticker, _T3_ACCOUNTS: F.Seq((503, {}), [])}) as calls:
        answer = T.request("upbit", "GET", "/v1/ticker", [("markets", "KRW-BTC")])
        assert answer.body == ticker and answer.server_utc == F.NOW, answer
        assert T.request("upbit", "GET", "/v1/accounts").body == []
        rows = [(c["method"], c["url"], c["path"], c["query"], c["params"], c["timeout"], c["json_body"])
                for c in calls]
        first = ("GET", "https://api.upbit.com/v1/ticker?markets=KRW-BTC", "/v1/ticker", "markets=KRW-BTC", None,
                 10.0, None)
        retried = ("GET", "https://api.upbit.com/v1/accounts", "/v1/accounts", "", None, 10.0, None)
        assert rows == [first, retried, retried], rows
        assert calls[0]["headers"] == {"Accept": "application/json"}, calls[0]["headers"]
        for url, params, timeout, why in (("https://api.upbit.com/v1/ticker", {"markets": "KRW-BTC"}, 10.0,
                                           ": params/timeout"),
                                          ("https://api.upbit.com/v1/ticker", None, 30.0, ": params/timeout"),
                                          ("https://api.upbit.com/v1/deposits", None, 10.0, ""),
                                          ("https://api.upbit.com/v1/accounts", None, 10.0, "")):   # Seq used up
            exc = _t3_raises(AssertionError, T._send, "GET", url, headers={}, params=params, json_body=None,
                             timeout=timeout)
            assert str(exc) == f"unrouted GET {urlsplit(url).path}{why}", str(exc)
        assert F.STRAYS == ["GET /v1/ticker", "GET /v1/ticker", "GET /v1/deposits", "GET /v1/accounts"], F.STRAYS
        F.STRAYS.clear()
    assert T._send is stub


def test_upbit_jwt_is_hs512_with_the_exact_query_hash_and_a_fresh_nonce():
    """Spec 5 Upbit (research upbit.md 2): HS512 over the base64url header and payload, checked here with the fake
    secret; query_hash is the SHA512 of the query exactly as it rides in the URL (states[] repeated, brackets not
    encoded) with query_hash_alg SHA512; no query_hash without parameters; no exp; a fresh uuid4 nonce on every
    attempt, a retried one included; keys.read names the two Upbit keys only."""
    seen, real_read = [], keys.read
    routes = {("GET", "/v1/orders/open"): [], _T3_ACCOUNTS: F.Seq((503, {}), [])}
    with (F.fake_keys(), _t2_patched(keys, "read", lambda names: seen.append(tuple(names)) or real_read(names)),
          F.serve(routes) as calls):
        T.request("upbit", "GET", "/v1/orders/open", [("states[]", "wait"), ("states[]", "watch"), ("limit", "100")])
        T.request("upbit", "GET", "/v1/accounts")
    query = urlsplit(calls[0]["url"]).query
    assert query == "states[]=wait&states[]=watch&limit=100", query
    head, payload = _t3_jwt(calls[0])
    assert head == {"alg": "HS512", "typ": "JWT"}, head
    assert payload == {"access_key": "test-upbit-access", "nonce": payload["nonce"],
                       "query_hash": hashlib.sha512(query.encode()).hexdigest(), "query_hash_alg": "SHA512"}, payload
    assert set(calls[0]["headers"]) == {"Authorization", "Accept"}, calls[0]["headers"]
    assert calls[0]["headers"]["Accept"] == "application/json"
    nonces = [payload["nonce"]]
    for call in calls[1:]:
        head, plain = _t3_jwt(call)
        assert head == {"alg": "HS512", "typ": "JWT"} and plain == {"access_key": "test-upbit-access",
                                                                   "nonce": plain["nonce"]}, plain
        nonces.append(plain["nonce"])
    assert len(calls) == 3 and len(set(nonces)) == 3, nonces
    assert all(uuid.UUID(n).version == 4 and str(uuid.UUID(n)) == n for n in nonces), nonces
    assert seen == [T.CREDENTIALS["upbit"]] * 3, seen


def test_okx_signs_the_timestamp_get_and_the_path_with_its_query():
    """Spec 5 OKX (research okx.md 2): the four OK-ACCESS headers and Content-Type and nothing else (never the demo
    header); OK-ACCESS-TIMESTAMP is ISO 8601 UTC with milliseconds and Z, from transport._clock; OK-ACCESS-SIGN is
    re-derived here as Base64(HMAC-SHA256(secret, timestamp + "GET" + path?query)); keys.read names the three OKX
    keys only."""
    seen, real_read = [], keys.read
    at = F.NOW + timedelta(microseconds=123987)
    algo = "/api/v5/trade/orders-algo-pending"
    with (_t2_patched(T, "_okx_offset_s", 0.0), _t2_patched(T, "_clock", lambda: at), F.fake_keys(),
          _t2_patched(keys, "read", lambda names: seen.append(tuple(names)) or real_read(names)),
          F.serve({("GET", algo): _T3_OKX_OK, ("GET", "/api/v5/account/balance"): _T3_OKX_OK}) as calls):
        T.request("okx", "GET", algo, [("ordType", "conditional")])
        T.request("okx", "GET", "/api/v5/account/balance")
    assert len(calls) == 2 and seen == [T.CREDENTIALS["okx"]] * 2, seen
    for call, request_path in zip(calls, (algo + "?ordType=conditional", "/api/v5/account/balance")):
        head = call["headers"]
        assert set(head) == {"OK-ACCESS-KEY", "OK-ACCESS-SIGN", "OK-ACCESS-TIMESTAMP", "OK-ACCESS-PASSPHRASE",
                             "Content-Type"}, head
        stamp = head["OK-ACCESS-TIMESTAMP"]
        assert stamp == "2026-10-24T00:00:00.123Z" and _T3_TS.fullmatch(stamp), stamp
        sign = hmac.new(b"test-okx-secret", (stamp + "GET" + request_path).encode(), hashlib.sha256).digest()
        assert head["OK-ACCESS-SIGN"] == base64.b64encode(sign).decode(), request_path
        assert (head["OK-ACCESS-KEY"], head["OK-ACCESS-PASSPHRASE"], head["Content-Type"]) == (
            "test-okx-key", "test-okx-pass", "application/json")
        assert call["url"] == "https://www.okx.com" + request_path and call["json_body"] is None, call["url"]
    kst = timezone(timedelta(hours=9))
    assert T._okx_timestamp(datetime(2026, 10, 24, 9, 0, 0, 999999, tzinfo=kst)) == "2026-10-24T00:00:00.999Z"
    assert T._okx_sign("s", "t", "/p?q=1") == base64.b64encode(hmac.new(b"s", b"tGET/p?q=1",
                                                                        hashlib.sha256).digest()).decode()


def test_the_okx_offset_comes_from_public_time_at_receipt():
    """E3, E39: a good public/time answer sets _okx_offset_s = ts / 1000 - received_utc, received_utc being the one
    clock read made right after _send returned; an answer 30 s off makes every signed request refused before any
    key is read; a malformed answer leaves no offset behind."""
    base_ms = 1792800000000                                          # F.NOW in milliseconds
    assert F.NOW.timestamp() * 1000 == base_ms
    reads, now = [], [F.NOW]

    def clock():
        reads.append(now[0])
        return now[0]

    def time_answer(ms):
        def answer(call):
            now[0] += timedelta(seconds=1)                           # the answer arrives a second later
            body = {"code": "0", "msg": "", "data": [{"ts": str(ms)}]}
            return 200, {"Date": F.DATE_HEADER}, json.dumps(body).encode("utf-8")
        return answer
    routes = {("GET", _T3_TIME): F.Seq(time_answer(base_ms + 3000), time_answer(base_ms + 32000), _T3_OKX_OK)}
    with _t2_patched(T, "_clock", clock), F.serve(routes):
        assert T._okx_offset_s is None
        answer = T.request("okx", "GET", _T3_TIME)
        assert answer.received_utc == F.NOW + timedelta(seconds=1) and reads == [answer.received_utc], reads
        assert T._okx_offset_s == 2.0, T._okx_offset_s
        assert _t2_passes("okx", "GET", "/api/v5/account/config")
        T.request("okx", "GET", _T3_TIME)
        assert T._okx_offset_s == 30.0, T._okx_offset_s
        assert _t2_refused("okx", "GET", "/api/v5/account/config") == _T2_SKEW
        _t3_raises(IndexError, T.request, "okx", "GET", _T3_TIME)    # "data": []
        assert T._okx_offset_s is None


def test_public_endpoints_read_no_key():
    """Spec 5: the Upbit ticker and the OKX public time and ticker carry only Accept; keys.read fails the test."""
    routes = {_T3_TICKER: [], ("GET", _T3_TIME): {"code": "0", "msg": "", "data": [{"ts": "1792800000000"}]},
              ("GET", "/api/v5/market/ticker"): _T3_OKX_OK}
    with _t2_patched(keys, "read", _t2_boom), F.serve(routes) as calls:
        T.request("upbit", "GET", "/v1/ticker", [("markets", "KRW-BTC,KRW-USDT")])
        T.request("okx", "GET", _T3_TIME)
        T.request("okx", "GET", "/api/v5/market/ticker", [("instId", "BTC-USDT")])
    assert [c["url"] for c in calls] == ["https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-USDT",
                                         "https://www.okx.com/api/v5/public/time",
                                         "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"], calls
    assert [c["headers"] for c in calls] == [{"Accept": "application/json"}] * 3, calls


def test_kis_inquiry_headers_carry_the_token_tr_id_and_app_key():
    """Spec 5 KIS: the token comes from the POST (content-type only, the client_credentials body, no parameters);
    the GET carries content-type, the bearer token, appkey, appsecret, the pinned tr_id and custtype P, with the
    query in the URL (PDNO=% as %25); each keys.read names the two KIS credentials only; the token POST's Answer
    shows no token in its repr."""
    seen, real_read = [], keys.read
    with (F.fake_keys(), _t2_patched(keys, "read", lambda names: seen.append(tuple(names)) or real_read(names)),
          F.serve({_T3_POST: _T3_TOKEN, _T3_GET: _T3_OK}) as calls):
        assert _t3_kis() == _T3_OK
        assert "test-token-1" not in repr(T.request("kis", "POST", "/oauth2/tokenP"))
    post, get = calls[:2]
    assert (post["method"], post["url"], post["headers"], post["json_body"]) == (
        "POST", _T3_KIS_HOST + "/oauth2/tokenP", {"content-type": "application/json; charset=utf-8"},
        {"grant_type": "client_credentials", "appkey": "test-kis-appkey", "appsecret": "test-kis-appsecret"}), post
    assert get["url"] == _T3_KIS_HOST + _T2_BALANCE + "?INQR_DVSN=01&PDNO=%25", get["url"]
    assert get["headers"] == {"content-type": "application/json; charset=utf-8", "authorization": "Bearer test-token-1",
                              "appkey": "test-kis-appkey", "appsecret": "test-kis-appsecret", "tr_id": "TTTC8434R",
                              "custtype": "P"}, get["headers"]
    assert get["json_body"] is None and len(calls) == 3
    assert seen == [T.CREDENTIALS["kis"]] * 3, seen


def test_a_get_is_retried_once_on_connection_errors_429_and_5xx():
    """Spec 5 step 4: a GET goes once more, after _sleep(2.0), on HTTP 503, 429, requests' ConnectionError and its
    subclass ConnectTimeout; every attempt is followed by _sleep(0.2); a second failure is final."""
    errors = requests.exceptions
    for first in ((503, {}), (429, {}), _t3_raise(errors.ConnectionError("x")), _t3_raise(errors.ConnectTimeout("x"))):
        F.SLEEPS.clear()
        with F.fake_keys(), F.serve({_T3_ACCOUNTS: F.Seq(first, [{"currency": "KRW"}])}) as calls:
            assert T.request("upbit", "GET", "/v1/accounts").body == [{"currency": "KRW"}]
        assert len(calls) == 2 and F.SLEEPS == [0.2, 2.0, 0.2], (first, F.SLEEPS)
    for twice, text in (((503, {}), "upbit /v1/accounts: HTTP 503"),
                        (_t3_raise(errors.ConnectionError("x")), "upbit /v1/accounts: ConnectionError")):
        F.SLEEPS.clear()
        with F.fake_keys(), F.serve({_T3_ACCOUNTS: F.Seq(twice, twice)}) as calls:
            assert str(_t3_raises(T.InquiryError, T.request, "upbit", "GET", "/v1/accounts")) == text
        assert len(calls) == 2 and F.SLEEPS == [0.2, 2.0, 0.2], (text, F.SLEEPS)


def test_no_retry_on_400_a_read_timeout_or_any_token_post():
    """A 400, a ReadTimeout (not a connection error: spec 5 names one) and every failure of the KIS token POST go
    out once, followed by the one _sleep(0.2)."""
    errors = requests.exceptions
    cases = ((("upbit", "GET", "/v1/accounts"), _T3_ACCOUNTS, (400, {"error": {"name": "validation_error"}}),
              "upbit /v1/accounts: HTTP 400 validation_error"),
             (("upbit", "GET", "/v1/accounts"), _T3_ACCOUNTS, _t3_raise(errors.ReadTimeout("x")),
              "upbit /v1/accounts: ReadTimeout"),
             (("kis", "POST", "/oauth2/tokenP"), _T3_POST, _t3_raise(errors.ConnectionError("x")),
              "kis /oauth2/tokenP: ConnectionError"),
             (("kis", "POST", "/oauth2/tokenP"), _T3_POST, _t3_raise(errors.ConnectTimeout("x")),
              "kis /oauth2/tokenP: ConnectTimeout"),
             (("kis", "POST", "/oauth2/tokenP"), _T3_POST, (503, {}), "kis /oauth2/tokenP: HTTP 503"),
             (("kis", "POST", "/oauth2/tokenP"), _T3_POST, (429, {}), "kis /oauth2/tokenP: HTTP 429"))
    for args, route, answer, text in cases:
        F.SLEEPS.clear()
        with F.fake_keys(), F.serve({route: answer}) as calls:
            exc = _t3_raises(T.InquiryError, T.request, *args)
        assert (type(exc), str(exc), len(calls), F.SLEEPS) == (T.InquiryError, text, 1, [0.2]), (text, str(exc))


def test_send_errors_become_type_names_and_suite_errors_propagate():
    """E15, E37: a ValueError or OSError out of _send (every requests exception is an OSError; http.client's latin-1
    UnicodeEncodeError on a header quotes the value) becomes InquiryError "<venue> <path>: <TypeName>" from None:
    no URL, no query, no exception text. The suite's Refused and the router's AssertionError propagate unchanged."""
    secret = F.FAKE_KEYS["KIS_APP_SECRET"]
    errors = requests.exceptions
    raised = (errors.ReadTimeout(f"https://api.upbit.com/v1/accounts?x={secret}"), errors.InvalidHeader(secret),
              UnicodeEncodeError("latin-1", secret + "\u20ac", len(secret), len(secret) + 1, "ordinal not in range"),
              OSError(secret), ValueError(secret))
    for exc in raised:
        with F.fake_keys(), F.serve({_T3_ACCOUNTS: _t3_raise(exc)}) as calls:
            got = _t3_raises(T.InquiryError, T.request, "upbit", "GET", "/v1/accounts")
        assert str(got) == f"upbit /v1/accounts: {type(exc).__name__}" and got.args == (str(got),), str(got)
        assert type(got) is T.InquiryError and got.__cause__ is None and got.__suppress_context__, repr(got)
        assert len(calls) == 1, type(exc).__name__
    with F.fake_keys(), F.serve({_T3_POST: _T3_TOKEN, _T3_GET: _t3_raise(raised[2])}):
        got = _t3_raises(T.InquiryError, _t3_kis)
    assert str(got) == f"kis {_T2_BALANCE}: UnicodeEncodeError", str(got)                 # no query, no value
    for exc in (F.Refused("E1 transport send inside the execution suite"), AssertionError("unrouted GET /x")):
        with F.fake_keys(), F.serve({_T3_ACCOUNTS: _t3_raise(exc)}) as calls:
            assert _t3_raises(type(exc), T.request, "upbit", "GET", "/v1/accounts") is exc
        assert len(calls) == 1


def test_answers_give_auth_errors_codes_and_no_text():
    """E15: HTTP 401 and 403, a code in AUTH_CODES (Upbit out_of_scope on any status, OKX 50120 and 50123 on HTTP
    200, KIS EGW00103) are AuthError; a KIS rt_cd or OKX code other than "0", an Upbit error body, a 3xx, a body
    that is not JSON and a token answer whose access_token is missing, empty or not a string are InquiryError. Each
    text is the venue, the path, the HTTP status and the venue's code: never a message, a header or an unplain
    code."""
    def upbit_error(name):
        return {"error": {"name": name, "message": "fixture text"}}

    def kis(code, rt_cd="1"):
        return {"rt_cd": rt_cd, "msg_cd": code, "msg1": "fixture text"}

    redirect = _t3_raw(302, b"[]", {"Date": F.DATE_HEADER, "Location": "https://elsewhere.example/v1/accounts?k=1"})
    cases = [
        ("upbit", "/v1/accounts", (401, upbit_error("out_of_scope")), T.AuthError, "HTTP 401 out_of_scope", 1),
        ("upbit", "/v1/accounts", (400, upbit_error("out_of_scope")), T.AuthError, "HTTP 400 out_of_scope", 1),
        ("upbit", "/v1/accounts", _t3_raw(403, b"<html>fixture text</html>"), T.AuthError, "HTTP 403", 1),
        ("upbit", "/v1/accounts", (400, upbit_error("validation_error")), T.InquiryError,
         "HTTP 400 validation_error", 1),
        ("upbit", "/v1/accounts", upbit_error("server_error"), T.InquiryError, "HTTP 200 server_error", 1),
        ("upbit", "/v1/accounts", redirect, T.InquiryError, "HTTP 302", 1),
        ("okx", "/api/v5/account/balance", (304, _T3_OKX_OK), T.InquiryError, "HTTP 304 0", 1),
        ("upbit", "/v1/accounts", _t3_raw(200, b"fixture text"), T.InquiryError, "HTTP 200: not JSON", 1),
        ("okx", "/api/v5/account/balance", {"code": "50120", "msg": "fixture text", "data": []}, T.AuthError,
         "HTTP 200 50120", 1),
        ("okx", "/api/v5/account/balance", {"code": "50123", "msg": "fixture text", "data": []}, T.AuthError,
         "HTTP 200 50123", 1),
        ("okx", "/api/v5/account/balance", (401, {"code": "50113", "msg": "fixture text"}), T.AuthError,
         "HTTP 401 50113", 1),
        ("okx", "/api/v5/account/balance", {"code": "51000", "msg": "fixture text", "data": []}, T.InquiryError,
         "HTTP 200 51000", 1),
        ("okx", "/api/v5/account/balance", {"code": "fixture text 12345678", "data": []}, T.InquiryError,
         "HTTP 200", 1),
        ("kis", _T2_BALANCE, kis("EGW00103"), T.AuthError, "HTTP 200 EGW00103", 1),
        ("kis", _T2_BALANCE, kis("APBK0013"), T.InquiryError, "HTTP 200 APBK0013", 1),
        ("kis", _T2_BALANCE, (500, kis("EGW00201")), T.InquiryError, "HTTP 500 EGW00201", 2),
        ("kis", _T2_BALANCE, {"msg_cd": "", "msg1": "fixture text"}, T.InquiryError, "HTTP 200", 1),
        ("kis", "/oauth2/tokenP", {"token_type": "Bearer", "expires_in": 86400}, T.InquiryError, "HTTP 200", 1),
        ("kis", "/oauth2/tokenP", dict(_T3_TOKEN, access_token=""), T.InquiryError, "HTTP 200", 1),
        ("kis", "/oauth2/tokenP", dict(_T3_TOKEN, access_token=7), T.InquiryError, "HTTP 200", 1),
        ("kis", "/oauth2/tokenP", (403, {"error_description": "fixture text", "error_code": "EGW00133"}),
         T.AuthError, "HTTP 403 EGW00133", 1),
        ("kis", "/oauth2/tokenP", (500, {"error_description": "fixture text", "error_code": "EGW00133"}),
         T.InquiryError, "HTTP 500 EGW00133", 1),
    ]
    for venue, path, answer, kind, tail, sent in cases:
        method = "POST" if path == "/oauth2/tokenP" else "GET"
        routes = {(method, path): answer} | ({_T3_POST: _T3_TOKEN} if venue == "kis" and method == "GET" else {})
        tr_id = "TTTC8434R" if method == "GET" and venue == "kis" else None
        with _t2_patched(T, "_okx_offset_s", 0.0), F.fake_keys(), F.serve(routes) as calls:
            exc = _t3_raises(T.InquiryError, T.request, venue, method, path, tr_id=tr_id)
        assert (type(exc), str(exc)) == (kind, f"{venue} {path}: {tail}"), (venue, path, tail, str(exc))
        assert len([c for c in calls if c["path"] == path]) == sent, (tail, calls)
        assert "fixture" not in str(exc) and "elsewhere" not in str(exc) and "test-" not in str(exc), str(exc)
    assert T._check_answer("upbit", "/v1/accounts", 200, b"[]") == []
    assert T._check_answer("okx", "/api/v5/account/balance", 200, b'{"code": "0", "data": []}') == {"code": "0",
                                                                                                  "data": []}


def test_the_answer_carries_body_server_time_receipt_and_sha256():
    """E3, E39: Answer.body is the parsed JSON, server_utc the Date header as aware UTC (the name in any case, an
    offset converted, -0000 read as UTC, None when absent or unreadable), received_utc the clock read after _send
    returned, sha256 the hex digest of the raw bytes; repr(answer) holds no body."""
    raw = b'[{"market": "KRW-BTC", "trade_price": 100000000.0}]'
    when = datetime(2026, 10, 24, 0, 0, 30, tzinfo=timezone.utc)
    for headers, want in (({"Date": "Sat, 24 Oct 2026 00:00:30 GMT"}, when),
                          ({"date": "Sat, 24 Oct 2026 09:00:30 +0900"}, when),
                          ({"DATE": "Sat, 24 Oct 2026 00:00:30 -0000"}, when),
                          ({"Date": "not a date"}, None), ({"Date": ""}, None), ({}, None)):
        now = [F.NOW]

        def answer(call, headers=headers, now=now):
            now[0] = F.NOW + timedelta(seconds=2)                    # the clock moves while the answer travels
            return 200, headers, raw
        with _t2_patched(T, "_clock", lambda now=now: now[0]), F.serve({_T3_TICKER: answer}):
            got = T.request("upbit", "GET", "/v1/ticker", [("markets", "KRW-BTC")])
        assert got.body == [{"market": "KRW-BTC", "trade_price": 100000000.0}], got.body
        assert got.server_utc == want and (want is None or got.server_utc.tzinfo == timezone.utc), (headers, got)
        assert got.received_utc == F.NOW + timedelta(seconds=2) and got.sha256 == hashlib.sha256(raw).hexdigest()
        assert "KRW-BTC" not in repr(got) and "trade_price" not in repr(got), repr(got)


def test_a_cached_token_is_reused_until_120_s_before_it_expires():
    """Spec 5 "Token": state_root()/kis_token.json is read first; its token is reused, with no POST, while now <
    expires_at - 120 and issued anew from there on; a missing, unreadable or malformed cache reads as none.
    _write_token opens its temp file exclusively: an existing one is FileExistsError, and the cache is untouched."""
    path = _t3_home() / "kis_token.json"
    now = F.NOW.timestamp()
    for expires_at, reused in ((now + 121, True), (now + 120.5, True), (now + 120, False), (now - 1, False)):
        path.write_text(json.dumps({"access_token": "test-token-0", "expires_at": expires_at}), encoding="utf-8")
        with (_t2_patched(T, "_next_issue_at", None), F.fake_keys(),
              F.serve({_T3_POST: _T3_TOKEN, _T3_GET: _T3_OK}) as calls):
            _t3_kis()
        assert [c["method"] for c in calls] == (["GET"] if reused else ["POST", "GET"]), (expires_at, calls)
        token = "test-token-0" if reused else "test-token-1"
        assert calls[-1]["headers"]["authorization"] == f"Bearer {token}", expires_at
    for text in ("", "not json", "[]", '{"access_token": "t"}', '{"access_token": "", "expires_at": 1e12}',
                 '{"access_token": 7, "expires_at": 1e12}', '{"access_token": "t", "expires_at": "x"}',
                 '{"access_token": "t", "expires_at": null}', '{"expires_at": 1e12}'):
        path.write_text(text, encoding="utf-8")
        assert T._read_token(path, now) is None, text
    assert T._read_token(_t3_home() / "no-such.json", now) is None and T._read_token(_t3_home(), now) is None
    path.write_text(json.dumps({"access_token": "t", "expires_at": now + 121}), encoding="utf-8")
    assert T._read_token(path, now) == "t" and T._read_token(path, now + 1) is None
    cache, tmp = path.read_text(encoding="utf-8"), _t3_home() / ".kis_token.0123456789ab.tmp"
    tmp.write_text("x", encoding="utf-8")
    _t3_raises(FileExistsError, T._write_token, path, tmp, "test-token-2", now + 3600)
    assert path.read_text(encoding="utf-8") == cache and tmp.read_text(encoding="utf-8") == "x"


def test_the_token_targets_are_checked_before_the_post_and_the_write_is_atomic():
    """The ledger's "KIS token burnt on refusal" (spec 5 "Token"): with no cache, the folder, the cache and the
    temp file pass checked_target BEFORE the token POST; the temp name checked then is the one written, fsynced and
    moved onto the cache by os.replace, each target checked again just before use; no temp file is left; the cache
    holds exactly {"access_token", "expires_at"} (epoch seconds, now + expires_in). The exclusive open is checked in
    test_a_cached_token_is_reused_until_120_s_before_it_expires."""
    home = _t3_home()
    path = home / "kis_token.json"
    events, real_check, real_replace, real_fsync = [], T.checked_target, os.replace, os.fsync

    def check(target, what="path", **kwargs):
        events.append(("check", Path(target), what))
        return real_check(target, what, **kwargs)

    def replace(src, dst):
        events.append(("replace", Path(src), Path(dst)))
        return real_replace(src, dst)

    def fsync(fd):
        events.append(("fsync",))
        return real_fsync(fd)

    def post(call):
        events.append(("POST",))
        return 200, {"Date": F.DATE_HEADER}, json.dumps(_t3_token("test-token-1") | {"expires_in": 600}).encode()
    os.replace, os.fsync = replace, fsync
    try:
        with (_t2_patched(T, "checked_target", check), F.fake_keys(),
              F.serve({_T3_POST: post, _T3_GET: _T3_OK}) as calls):
            assert _t3_kis() == _T3_OK
    finally:
        os.replace, os.fsync = real_replace, real_fsync
    tmp = events[2][1]
    assert _T3_TMP.fullmatch(tmp.name) and tmp.parent == home, tmp
    assert events == [("check", home, "KIS token folder"), ("check", path, "KIS token cache"),
                      ("check", tmp, "KIS token temp"), ("POST",),
                      ("check", home, "KIS token folder"), ("check", tmp, "KIS token temp"), ("fsync",),
                      ("check", tmp, "KIS token temp"), ("check", path, "KIS token cache"),
                      ("replace", tmp, path)], events
    assert [c["method"] for c in calls] == ["POST", "GET"]
    assert json.loads(path.read_text(encoding="utf-8")) == {"access_token": "test-token-1",
                                                            "expires_at": F.NOW.timestamp() + 600}
    assert sorted(p.name for p in home.iterdir()) == ["kis_token.json"], sorted(p.name for p in home.iterdir())
    assert T._next_issue_at == F.NOW.timestamp() + 70.0


def test_a_refused_token_target_sends_nothing_and_burns_no_issue():
    """A checked_target refusal of the folder, the cache or the temp file propagates as its RuntimeError (a crash,
    E33), before any send: no POST, no GET, no 70 s gap started, nothing written."""
    real = T.checked_target
    for refused in ("KIS token folder", "KIS token cache", "KIS token temp"):
        def check(target, what="path", refused=refused, **kwargs):
            if what == refused:
                raise RuntimeError(f"{what} refused (test)")
            return real(target, what, **kwargs)
        with (_t2_patched(T, "checked_target", check), F.fake_keys(),
              F.serve({_T3_POST: _T3_TOKEN, _T3_GET: _T3_OK}) as calls):
            exc = _t3_raises(RuntimeError, _t3_kis)
        assert str(exc) == f"{refused} refused (test)" and calls == [], (refused, calls)
        assert T._next_issue_at is None and list(_t3_home().iterdir()) == [], refused


def test_at_most_one_token_issue_per_70_s_and_the_post_is_never_retried():
    """E3: a second issue inside 70 s of the first is InquiryError with no POST; at 70 s it goes out. A token POST
    that fails to connect goes out once (never retried) and still starts the 70 s."""
    now = [F.NOW]
    path = _t3_home() / "kis_token.json"
    expired = json.dumps({"access_token": "test-token-0", "expires_at": F.NOW.timestamp()})
    routes = {_T3_POST: F.Seq(_T3_TOKEN, _t3_token("test-token-2")), _T3_GET: _T3_OK}
    with _t2_patched(T, "_clock", lambda: now[0]), F.fake_keys(), F.serve(routes) as calls:
        _t3_kis()
        path.write_text(expired, encoding="utf-8")                  # the cache ran out (or was replaced)
        now[0] = F.NOW + timedelta(seconds=69.999)
        exc = _t3_raises(T.InquiryError, _t3_kis)
        assert (type(exc), str(exc), len(calls)) == (T.InquiryError, _T3_WAIT, 2), str(exc)
        now[0] = F.NOW + timedelta(seconds=70)
        _t3_kis()
    assert [(c["method"], c["headers"].get("authorization")) for c in calls] == [
        ("POST", None), ("GET", "Bearer test-token-1"), ("POST", None), ("GET", "Bearer test-token-2")], calls
    path.write_text(expired, encoding="utf-8")
    F.SLEEPS.clear()
    connect = _t3_raise(requests.exceptions.ConnectionError("x"))
    with _t2_patched(T, "_next_issue_at", None), F.fake_keys(), F.serve({_T3_POST: connect, _T3_GET: _T3_OK}) as calls:
        assert str(_t3_raises(T.InquiryError, _t3_kis)) == "kis /oauth2/tokenP: ConnectionError"
        assert [c["method"] for c in calls] == ["POST"] and F.SLEEPS == [0.2], (calls, F.SLEEPS)
        assert T._next_issue_at == F.NOW.timestamp() + 70.0
        assert str(_t3_raises(T.InquiryError, _t3_kis)) == _T3_WAIT and len(calls) == 1


def test_a_token_code_marks_the_token_bad_and_the_next_issue_waits_70_s():
    """E15: EGW00121, EGW00122 and EGW00123 on a KIS inquiry, on any status, are InquiryError (never AuthError) and
    mark the token sent bad for this process: the cache holding it is not reused, and the next issue waits for the
    70 s rule. On the token POST itself such a code is a plain InquiryError. HTTP 500 with EGW00123 (how KIS answers
    an expired token) is retried once, 2 s later, with the same token, which is marked bad when the second answer is
    judged. The token never appears in an error text."""
    for code in sorted(T.KIS_TOKEN_CODES):
        for status in (200, 401, 500):
            body = json.dumps({"rt_cd": "1", "msg_cd": code, "msg1": "fixture text"}).encode()
            exc = _t3_raises(T.InquiryError, T._check_answer, "kis", _T2_BALANCE, status, body)
            assert isinstance(exc, T._TokenRejected) and not isinstance(exc, T.AuthError), (code, status)
            assert str(exc) == f"kis {_T2_BALANCE}: HTTP {status} {code}", str(exc)
        exc = _t3_raises(T.InquiryError, T._check_answer, "kis", "/oauth2/tokenP", 200,
                         json.dumps({"error_code": code}).encode())
        assert type(exc) is T.InquiryError and str(exc) == f"kis /oauth2/tokenP: HTTP 200 {code}", str(exc)
    now = [F.NOW]
    bad = {"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "fixture text"}
    routes = {_T3_POST: F.Seq(_T3_TOKEN, _t3_token("test-token-2")), _T3_GET: F.Seq(bad, _T3_OK)}
    with _t2_patched(T, "_clock", lambda: now[0]), F.fake_keys(), F.serve(routes) as calls:
        exc = _t3_raises(T.InquiryError, _t3_kis)
        assert str(exc) == f"kis {_T2_BALANCE}: HTTP 200 EGW00123" and T._bad_tokens == {"test-token-1"}, str(exc)
        now[0] = F.NOW + timedelta(seconds=69)
        wait = _t3_raises(T.InquiryError, _t3_kis)
        assert str(wait) == _T3_WAIT and len(calls) == 2, str(wait)            # the bad cached token is not reused
        now[0] = F.NOW + timedelta(seconds=70)
        assert _t3_kis() == _T3_OK
    assert [(c["method"], c["headers"].get("authorization")) for c in calls] == [
        ("POST", None), ("GET", "Bearer test-token-1"), ("POST", None), ("GET", "Bearer test-token-2")], calls
    cache = json.loads((_t3_home() / "kis_token.json").read_text(encoding="utf-8"))
    assert cache["access_token"] == "test-token-2" and "test-token" not in str(exc) + str(wait)
    F.SLEEPS.clear()
    expired = (500, {"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "fixture text"})
    with _t2_patched(T, "_bad_tokens", set()), F.fake_keys(), F.serve({_T3_GET: expired}) as calls:
        exc = _t3_raises(T._TokenRejected, _t3_kis)                  # the cached test-token-2, sent twice
        assert T._bad_tokens == {"test-token-2"}, T._bad_tokens
    assert str(exc) == f"kis {_T2_BALANCE}: HTTP 500 EGW00123" and F.SLEEPS == [0.2, 2.0, 0.2], (str(exc), F.SLEEPS)
    assert [(c["method"], c["headers"]["authorization"]) for c in calls] == [("GET", "Bearer test-token-2")] * 2


def test_a_reissued_bad_token_is_auth_error_and_blocks_issuing_for_6_hours():
    """E15: KIS hands back the same token for 6 hours, so a bad token that the POST returns again is AuthError, and
    no POST goes out for 6 hours after that issue (6 h - 1 s: none; 6 h: one)."""
    now = [F.NOW]
    bad = {"rt_cd": "1", "msg_cd": "EGW00121", "msg1": "fixture text"}
    routes = {_T3_POST: F.Seq(_T3_TOKEN, _T3_TOKEN, _t3_token("test-token-2")), _T3_GET: F.Seq(bad, _T3_OK)}
    with _t2_patched(T, "_clock", lambda: now[0]), F.fake_keys(), F.serve(routes) as calls:
        _t3_raises(T.InquiryError, _t3_kis)
        again = now[0] = F.NOW + timedelta(seconds=70)
        exc = _t3_raises(T.AuthError, _t3_kis)
        assert str(exc) == _T3_BLOCK and T._next_issue_at == again.timestamp() + 6 * 3600, str(exc)
        now[0] = again + timedelta(hours=6, seconds=-1)
        wait = _t3_raises(T.InquiryError, _t3_kis)
        assert (type(wait), str(wait)) == (T.InquiryError, _T3_WAIT), str(wait)
        assert [c["method"] for c in calls] == ["POST", "GET", "POST"], calls
        now[0] = again + timedelta(hours=6)
        assert _t3_kis() == _T3_OK
    assert [c["method"] for c in calls] == ["POST", "GET", "POST", "POST", "GET"], calls
    assert calls[-1]["headers"]["authorization"] == "Bearer test-token-2" and "test-token" not in str(exc)


def test_the_token_cache_is_shared_with_the_kis_quote_client_both_ways():
    """Spec 5 "Token" (E3): the same file and format as data.krx.kis_client. Its _TOKEN_PATH, fixed when kis_client
    was first imported, is pointed into the temp home and back: what its _store_token writes, E1's _read_token
    reads (with the same 120 s margin); what E1's _write_token writes, its _cached_token reads. Neither KISClient()
    nor .token() is used, and no file in execution/ imports data.* or config (the import guard, here directly)."""
    from data.krx import kis_client
    home = _t3_home()
    path = T.isolation.state_root() / "kis_token.json"
    assert path == home / "kis_token.json", path
    keep = kis_client._TOKEN_PATH
    try:
        kis_client._TOKEN_PATH = path
        client = object.__new__(kis_client.KISClient)                # no __init__: no config read, no session
        assert kis_client._TOKEN_PATH.is_relative_to(home)
        client._store_token("test-token-9", 3600.0)
        assert set(json.loads(path.read_text(encoding="utf-8"))) == {"access_token", "expires_at"}
        assert T._read_token(path, time.time()) == "test-token-9"
        assert T._read_token(path, time.time() + 3600 - 120) is None
        T._write_token(path, path.with_name(".kis_token.0123456789ab.tmp"), "test-token-8", time.time() + 3600)
        assert set(json.loads(path.read_text(encoding="utf-8"))) == {"access_token", "expires_at"}
        assert kis_client._TOKEN_PATH.is_relative_to(home)
        assert client._cached_token() == "test-token-8"
        T._write_token(path, path.with_name(".kis_token.0123456789ac.tmp"), "test-token-7", time.time() + 100)
        assert kis_client._TOKEN_PATH.is_relative_to(home)
        assert client._cached_token() is None                                # inside its 120 s margin too
    finally:
        kis_client._TOKEN_PATH = keep
    assert sorted(p.name for p in home.iterdir()) == ["kis_token.json"]
    for py in sorted((ROOT / "execution").glob("*.py")):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            assert not [n for n in names if n.split(".")[0] in ("data", "config")], (py.name, names)


def test_a_public_send_through_request_is_refused_under_the_suite():
    """The probe of spec 9, through request: with no serve() a public Upbit ticker reaches the suite's refusing
    _send, whose Refused propagates (it is never wrapped as an InquiryError); one stray, asserted and cleared."""
    exc = _t3_raises(F.Refused, T.request, "upbit", "GET", "/v1/ticker", [("markets", "KRW-BTC")])
    assert str(exc) == "E1 transport send inside the execution suite", str(exc)
    assert F.STRAYS == ["GET /v1/ticker"], F.STRAYS
    F.STRAYS.clear()
```

The block uses Task 2's `ROOT`, `_T2_BALANCE`, `_T2_SKEW`, `_t2_patched`, `_t2_boom`, `_t2_passes` and `_t2_refused`,
and `requests`, `keys` and `T`, which the module already imports.

- [ ] **Step 2: Run to verify it fails**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_transport/; echo "exit $?"
```

Expected (a traceback on stderr for each failure, then exactly these lines; Task 2's 11 tests still pass):

```
FAIL execution_transport/test_a_cached_token_is_reused_until_120_s_before_it_expires InquiryError: transport: sending arrives in Task 3
FAIL execution_transport/test_a_get_is_retried_once_on_connection_errors_429_and_5xx InquiryError: transport: sending arrives in Task 3
FAIL execution_transport/test_a_public_send_through_request_is_refused_under_the_suite InquiryError: transport: sending arrives in Task 3
FAIL execution_transport/test_a_refused_token_target_sends_nothing_and_burns_no_issue AttributeError: module 'execution.transport' has no attribute 'checked_target'
FAIL execution_transport/test_a_reissued_bad_token_is_auth_error_and_blocks_issuing_for_6_hours InquiryError: transport: sending arrives in Task 3
PASS execution_transport/test_a_signed_okx_request_needs_a_known_offset_within_25_s
FAIL execution_transport/test_a_token_code_marks_the_token_bad_and_the_next_issue_waits_70_s AttributeError: module 'execution.transport' has no attribute '_check_answer'
FAIL execution_transport/test_answers_give_auth_errors_codes_and_no_text AssertionError: ('upbit', '/v1/accounts', 'HTTP 401 out_of_scope', 'transport: sending arrives in Task 3')
FAIL execution_transport/test_at_most_one_token_issue_per_70_s_and_the_post_is_never_retried InquiryError: transport: sending arrives in Task 3
PASS execution_transport/test_constants_errors_and_answer_have_the_contract_shape
PASS execution_transport/test_every_allowlisted_request_passes_the_checks
PASS execution_transport/test_every_refusal_comes_before_any_key_is_read
FAIL execution_transport/test_kis_inquiry_headers_carry_the_token_tr_id_and_app_key InquiryError: transport: sending arrives in Task 3
FAIL execution_transport/test_no_retry_on_400_a_read_timeout_or_any_token_post AssertionError: ('upbit /v1/accounts: HTTP 400 validation_error', 'transport: sending arrives in Task 3')
FAIL execution_transport/test_okx_signs_the_timestamp_get_and_the_path_with_its_query InquiryError: transport: sending arrives in Task 3
FAIL execution_transport/test_public_endpoints_read_no_key InquiryError: transport: sending arrives in Task 3
PASS execution_transport/test_require_keys_names_the_first_missing_key_and_returns_nothing
FAIL execution_transport/test_send_errors_become_type_names_and_suite_errors_propagate AssertionError: transport: sending arrives in Task 3
PASS execution_transport/test_send_opens_one_session_with_trust_env_off_and_no_redirects
FAIL execution_transport/test_serve_answers_records_and_refuses_strays InquiryError: transport: sending arrives in Task 3
FAIL execution_transport/test_the_answer_carries_body_server_time_receipt_and_sha256 InquiryError: transport: sending arrives in Task 3
PASS execution_transport/test_the_not_get_rule_holds_on_its_own
FAIL execution_transport/test_the_okx_offset_comes_from_public_time_at_receipt InquiryError: transport: sending arrives in Task 3
PASS execution_transport/test_the_query_is_built_once_and_sent_as_built
PASS execution_transport/test_the_r_rule_holds_on_its_own
FAIL execution_transport/test_the_token_cache_is_shared_with_the_kis_quote_client_both_ways AttributeError: module 'execution.transport' has no attribute 'isolation'
FAIL execution_transport/test_the_token_targets_are_checked_before_the_post_and_the_write_is_atomic AttributeError: module 'execution.transport' has no attribute 'checked_target'
PASS execution_transport/test_trust_env_off_ignores_proxy_ca_bundle_and_netrc_settings
PASS execution_transport/test_unpatched_send_is_refused_under_the_suite
FAIL execution_transport/test_upbit_jwt_is_hs512_with_the_exact_query_hash_and_a_fresh_nonce InquiryError: transport: sending arrives in Task 3

11/30 passed, 19 failed, 0 not run
exit 1
```

A test that fails here for any other reason (a `NameError`, an `ImportError`, an `AssertionError` naming another
text) means a copy error in Step 1: fix the copy, never a control.

- [ ] **Step 3: Implement**

`execution/transport.py` (LF; Edit tool). Re-read the file first. Three edits.

Edit 1, anchor: the last two lines of the module docstring through the end of the import block. Old text:

```python
returns a key, and every error text holds names, paths, TR ids and venue codes only (E37). Task 3 adds the signing,
the sending, the answer checks and the KIS token cache; until then `request` stops after the checks."""
from __future__ import annotations

import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from urllib.parse import quote

import requests

from execution import keys
from execution.keys import KeyMissing  # noqa: F401  (re-exported: the venue modules import it from here, E36)
```

New text (the docstring's last sentence becomes a paragraph on the sending half; the imports gain `base64`,
`hashlib`, `hmac`, `json`, `os`, `uuid`, `timezone`, `parsedate_to_datetime`, `Path`, `isolation` and
`checked_target`, all on the E1 allowlist):

```python
returns a key, and every error text holds names, paths, TR ids and venue codes only (E37).

Each attempt builds its headers afresh (the KIS bearer token, an Upbit HS512 JWT with a new nonce, an OKX
HMAC-SHA256 signature over a new timestamp), sends once with a 10 s timeout and pauses 0.2 s (at most 5 requests a
second); a GET goes once more, 2 s later, after a connection error, HTTP 429 or 5xx, a POST never. `_check_answer`
turns each answer into its parsed body, AuthError or InquiryError (E15). The KIS token lives in
state_root()/kis_token.json, the file and format the KIS quote client uses: reused until 120 s before it expires,
issued at most once per 70 s per process with its targets checked before the token POST (the ledger's "KIS token
burnt on refusal"), and not issued for 6 hours after KIS hands back a token it had called bad."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from types import MappingProxyType
from urllib.parse import quote

import requests

from core import isolation
from core.isolation import checked_target
from execution import keys
from execution.keys import KeyMissing  # noqa: F401  (re-exported: the venue modules import it from here, E36)
```

Edit 2, anchor: the whole function `request` (from `def request(` through the line
`    raise InquiryError("transport: sending arrives in Task 3")`). Old text:

```python
def request(venue: str, method: str, path: str, params: Sequence[tuple[str, str]] | None = None, *,
            tr_id: str | None = None) -> Answer:
    """One allowlisted request (spec 5). Steps 1-6 of contract section 6 run first, in order, and each refusal is
    InquiryRefused before any key is read. After them this fails closed until Task 3 adds credentials, sending,
    retry and answers."""
    if venue not in HOSTS:
        raise InquiryRefused(f"unknown venue {venue!r}")
    endpoints, tr_ids, public = _rules(venue)
    if (method, path) not in endpoints:
        raise InquiryRefused(f"{venue}: {method} {path} is not on the E1 allowlist")
    if method != "GET":
        if (venue, method, path) != ("kis", "POST", KIS_TOKEN_PATH):
            raise InquiryRefused(f"{venue}: {method} is not GET")
        if params is not None:
            raise InquiryRefused("kis: the token POST takes no parameters")
    if venue == "kis" and method == "GET":
        if tr_id not in {t for p, t in tr_ids if p == path} or not tr_id.endswith("R"):
            raise InquiryRefused(f"kis: {path} needs its pinned TR id ending in R, got {tr_id!r}")
    elif tr_id is not None:
        raise InquiryRefused(f"{venue}: a TR id belongs only to a KIS inquiry")
    _query(venue, path, params)
    if venue == "okx" and path not in public and not (
            _okx_offset_s is not None and abs(_okx_offset_s) <= OKX_SKEW_LIMIT_S):
        raise InquiryRefused("okx: the PC clock offset from OKX time is unknown or above 25 s; OKX requests not sent")
    raise InquiryError("transport: sending arrives in Task 3")
```

New text (steps 1-6 unchanged, apart from `query = ` keeping the built query; `global _okx_offset_s` first, since the
function now sets it):

```python
def request(venue: str, method: str, path: str, params: Sequence[tuple[str, str]] | None = None, *,
            tr_id: str | None = None) -> Answer:
    """One allowlisted request (spec 5). Steps 1-6 of contract section 6 run first, in order, and each refusal is
    InquiryRefused before any key is read. Then each attempt builds its credentials and headers afresh (`_headers`)
    and goes out through `_send` with the query in the URL; `received_utc` is the clock read right after `_send`
    returns (E39), and every attempt is followed by `_sleep(PACE_S)`. A GET goes once more, after
    `_sleep(RETRY_AFTER_S)`, on requests' ConnectionError (ConnectTimeout included; a ReadTimeout is not one), HTTP
    429 or 5xx; a POST never. A ValueError or OSError out of `_send` becomes InquiryError naming the venue, the path
    and the exception type only (E15, E37); anything else propagates. `_check_answer` judges the last answer; a KIS
    token the venue calls invalid or expired goes into `_bad_tokens`; a good OKX public/time answer sets
    `_okx_offset_s` (its `ts` minus `received_utc`)."""
    global _okx_offset_s
    if venue not in HOSTS:
        raise InquiryRefused(f"unknown venue {venue!r}")
    endpoints, tr_ids, public = _rules(venue)
    if (method, path) not in endpoints:
        raise InquiryRefused(f"{venue}: {method} {path} is not on the E1 allowlist")
    if method != "GET":
        if (venue, method, path) != ("kis", "POST", KIS_TOKEN_PATH):
            raise InquiryRefused(f"{venue}: {method} is not GET")
        if params is not None:
            raise InquiryRefused("kis: the token POST takes no parameters")
    if venue == "kis" and method == "GET":
        if tr_id not in {t for p, t in tr_ids if p == path} or not tr_id.endswith("R"):
            raise InquiryRefused(f"kis: {path} needs its pinned TR id ending in R, got {tr_id!r}")
    elif tr_id is not None:
        raise InquiryRefused(f"{venue}: a TR id belongs only to a KIS inquiry")
    query = _query(venue, path, params)
    if venue == "okx" and path not in public and not (
            _okx_offset_s is not None and abs(_okx_offset_s) <= OKX_SKEW_LIMIT_S):
        raise InquiryRefused("okx: the PC clock offset from OKX time is unknown or above 25 s; OKX requests not sent")
    url = HOSTS[venue] + path + ("?" + query if query else "")
    for attempt in (1, 2):
        headers, json_body, token = _headers(venue, method, path, query, tr_id, path in public)
        try:
            status, answer_headers, content = _send(method, url, headers=headers, params=None, json_body=json_body,
                                                    timeout=TIMEOUT_S)
        except (ValueError, OSError) as exc:
            _sleep(PACE_S)
            if attempt == 1 and method == "GET" and isinstance(exc, requests.exceptions.ConnectionError):
                _sleep(RETRY_AFTER_S)
                continue
            raise InquiryError(f"{venue} {path}: {type(exc).__name__}") from None
        received_utc = _clock()
        _sleep(PACE_S)
        if attempt == 1 and method == "GET" and (status == 429 or status >= 500):
            _sleep(RETRY_AFTER_S)
            continue
        break
    try:
        body = _check_answer(venue, path, status, content)
    except _TokenRejected:
        _bad_tokens.add(token)
        raise
    if (venue, path) == ("okx", "/api/v5/public/time"):
        _okx_offset_s = None                          # a malformed answer leaves no stale offset behind
        _okx_offset_s = int(body["data"][0]["ts"]) / 1000 - received_utc.timestamp()
    return Answer(body=body, server_utc=_date(answer_headers), received_utc=received_utc,
                  sha256=hashlib.sha256(content).hexdigest())
```

Edit 3, anchor: the last three lines of `_query`, which end the file. Old text:

```python
            raise InquiryRefused(f"{venue}: parameter {key!r} is not plain")
        parts.append(f"{key}={quote(value, safe=',')}")
    return "&".join(parts)
```

New text (the same three lines, then the sending half's helpers; the new part starts with two blank lines and ends
the file with one newline):

```python
            raise InquiryRefused(f"{venue}: parameter {key!r} is not plain")
        parts.append(f"{key}={quote(value, safe=',')}")
    return "&".join(parts)


def _headers(venue: str, method: str, path: str, query: str, tr_id: str | None,
             public: bool) -> tuple[dict, dict | None, str | None]:
    """(headers, json_body, token) for one attempt, built afresh each time; each keys.read names exactly
    CREDENTIALS[venue], and a public path reads no key. Never the demo-trading header (E3)."""
    if public:
        return {"Accept": "application/json"}, None, None
    if venue == "kis" and method == "POST":
        app_key, app_secret = keys.read(CREDENTIALS["kis"])
        return ({"content-type": "application/json; charset=utf-8"},
                {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}, None)
    if venue == "kis":
        token = _kis_token()
        app_key, app_secret = keys.read(CREDENTIALS["kis"])
        return ({"content-type": "application/json; charset=utf-8", "authorization": f"Bearer {token}",
                 "appkey": app_key, "appsecret": app_secret, "tr_id": tr_id, "custtype": "P"}, None, token)
    if venue == "upbit":
        access_key, secret_key = keys.read(CREDENTIALS["upbit"])
        return ({"Authorization": f"Bearer {_upbit_jwt(access_key, secret_key, query)}",
                 "Accept": "application/json"}, None, None)
    api_key, secret, passphrase = keys.read(CREDENTIALS["okx"])
    timestamp = _okx_timestamp(_clock())
    return ({"OK-ACCESS-KEY": api_key,
             "OK-ACCESS-SIGN": _okx_sign(secret, timestamp, path + ("?" + query if query else "")),
             "OK-ACCESS-TIMESTAMP": timestamp, "OK-ACCESS-PASSPHRASE": passphrase,
             "Content-Type": "application/json"}, None, None)


def _date(headers) -> datetime | None:
    """The answer's Date header (its name in any case) as an aware UTC datetime; None when absent or unreadable."""
    value = next((v for k, v in headers.items() if k.lower() == "date"), None)
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:                         # "-0000": UTC with no local zone given (RFC 5322)
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


class _TokenRejected(InquiryError):
    """A KIS inquiry answered with one of KIS_TOKEN_CODES: request marks the token it sent bad."""


_CODE = re.compile(r"[A-Za-z0-9_]{1,40}")           # a venue code worth naming in an error text; nothing else is


def _check_answer(venue: str, path: str, status: int, body_bytes: bytes) -> object:
    """E15: the parsed body of an HTTP 200 answer that carries the venue's success marker (KIS rt_cd "0", or a
    non-empty access_token from the token POST; OKX code "0"; Upbit no error key). A KIS inquiry answered with a
    token code (on any status) raises _TokenRejected; HTTP 401 or 403, or a code in AUTH_CODES[venue], AuthError;
    anything else, a 3xx included, InquiryError. Each text names the venue, the path, the HTTP status and the
    venue's code only: never a message, a header or the body (E37)."""
    try:
        body, parsed = json.loads(body_bytes), True
    except ValueError:                                # not JSON, or not UTF-8: the bytes are never quoted
        body, parsed = None, False
    code = _code(venue, body)
    text = f"{venue} {path}: HTTP {status}" + (f" {code}" if code else "")
    if venue == "kis" and path != KIS_TOKEN_PATH and code in KIS_TOKEN_CODES:
        raise _TokenRejected(text)
    if status in (401, 403) or code in AUTH_CODES[venue]:
        raise AuthError(text)
    if status == 200 and parsed and _succeeded(venue, path, body):
        return body
    raise InquiryError(text if parsed else f"{text}: not JSON")


def _code(venue: str, body: object) -> str:
    """The venue's own code in a parsed body (KIS msg_cd, or the token answer's error_code; OKX code; Upbit
    error.name); "" when there is none or it is not a short plain word."""
    if not isinstance(body, dict):
        return ""
    if venue == "kis":
        raw = body.get("msg_cd") or body.get("error_code")
    elif venue == "okx":
        raw = body.get("code")
    else:
        raw = body["error"].get("name") if isinstance(body.get("error"), dict) else None
    return str(raw) if raw is not None and _CODE.fullmatch(str(raw)) else ""


def _succeeded(venue: str, path: str, body: object) -> bool:
    """The venue's success marker in a parsed HTTP 200 body (E15)."""
    if venue == "upbit":
        return not (isinstance(body, dict) and "error" in body)
    if not isinstance(body, dict):
        return False
    if venue == "okx":
        return body.get("code") == "0"
    if path == KIS_TOKEN_PATH:
        return isinstance(body.get("access_token"), str) and body["access_token"] != ""
    return body.get("rt_cd") == "0"


def _b64url(raw: bytes) -> str:
    """base64url without padding, as a JWT part."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _upbit_jwt(access_key: str, secret_key: str, query: str) -> str:
    """The Upbit JWT (research upbit.md 2): HS512 over the base64url header and payload with the secret used raw;
    the payload holds access_key and a fresh uuid4 nonce, plus query_hash (the SHA512 hex of `query`, the exact
    string sent in the URL) and query_hash_alg when there is a query. No exp claim."""
    payload = {"access_key": access_key, "nonce": str(uuid.uuid4())}
    if query:
        payload |= {"query_hash": hashlib.sha512(query.encode("utf-8")).hexdigest(), "query_hash_alg": "SHA512"}
    signing_input = ".".join(_b64url(json.dumps(part, separators=(",", ":")).encode("utf-8"))
                             for part in ({"alg": "HS512", "typ": "JWT"}, payload))
    signature = hmac.new(secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha512).digest()
    return f"{signing_input}.{_b64url(signature)}"


def _okx_timestamp(moment: datetime) -> str:
    """OK-ACCESS-TIMESTAMP: ISO 8601 UTC with milliseconds (truncated) and Z, for example 2026-10-24T00:00:00.000Z."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _okx_sign(secret: str, timestamp: str, request_path: str) -> str:
    """OK-ACCESS-SIGN (research okx.md 2): Base64 of HMAC-SHA256(secret, timestamp + "GET" + the request path with
    its query + an empty body)."""
    message = (timestamp + "GET" + request_path).encode("utf-8")
    return base64.b64encode(hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()).decode("ascii")


def _kis_token() -> str:
    """The KIS bearer token for one GET attempt (spec 5 "Token"): the cached one while it is not bad and now <
    expires_at - 120 s; else one issue through the token POST, at most once per 70 s per process. The folder, the
    cache and the temp file pass checked_target BEFORE the POST and before the 70 s starts, so a refused target
    sends nothing and burns no issuance (a refusal propagates: a crash, E33). KIS answers the same token for 6
    hours, so a token it had called bad that the POST hands back is AuthError and blocks issuing for 6 hours."""
    global _next_issue_at
    path = isolation.state_root() / "kis_token.json"
    now = _clock().timestamp()
    cached = _read_token(path, now)
    if cached is not None and cached not in _bad_tokens:
        return cached
    if _next_issue_at is not None and now < _next_issue_at:
        raise InquiryError("kis: no token may be issued yet; KIS skipped this poll")
    checked_target(path.parent, "KIS token folder")
    checked_target(path, "KIS token cache")
    tmp = checked_target(path.with_name(f".kis_token.{os.urandom(6).hex()}.tmp"), "KIS token temp")
    _next_issue_at = now + TOKEN_MIN_GAP_S
    answer = request("kis", "POST", KIS_TOKEN_PATH)
    token = answer.body["access_token"]
    if token in _bad_tokens:
        _next_issue_at = now + TOKEN_REISSUE_BLOCK_S
        raise AuthError("kis: KIS issued a token it had called invalid; no token for 6 hours")
    _write_token(path, tmp, token, now + float(answer.body.get("expires_in") or 86400))
    return token


def _read_token(path: Path, now_epoch: float) -> str | None:
    """The cached token when `path` holds a non-empty access_token and now_epoch < expires_at - 120 s (the quote
    client's reuse rule); None for a missing, unreadable or malformed file or a token that is about to expire."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        token, expires_at = data["access_token"], float(data["expires_at"])
    except (OSError, ValueError, TypeError, LookupError):
        return None
    return token if isinstance(token, str) and token and now_epoch < expires_at - TOKEN_REUSE_MARGIN_S else None


def _write_token(path: Path, tmp: Path, token: str, expires_at: float) -> None:
    """{"access_token", "expires_at"} (epoch seconds; the quote client's format) written atomically: to `tmp`, the
    temp name checked before the POST, opened exclusively and fsynced, then os.replace onto `path`, each target
    checked again just before it is used. An OSError propagates (a crash, E33): the next poll finds the old cache,
    or none, and may issue once the 70 s have passed. A write that fails after the open leaves its uniquely named
    temp file behind (nothing here deletes a file); it is never read or reused, and the next issue (KIS hands back
    the same token within 6 hours) writes a fresh one."""
    checked_target(path.parent, "KIS token folder").mkdir(parents=True, exist_ok=True)
    with open(checked_target(tmp, "KIS token temp"), "x", encoding="utf-8") as fh:
        fh.write(json.dumps({"access_token": token, "expires_at": expires_at}))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(checked_target(tmp, "KIS token temp"), checked_target(path, "KIS token cache"))
```

`tests/execution_guards.py` (LF; Edit tool; Task 2's guard file). Re-read the file first. One edit, anchor: the
`TRANSPORT_ONLY` frozenset (under the comment `# transport.py's own names: ...`). E36 says no other execution module
may reach the signing helpers; `_headers` returns the KIS app key and secret and the signed headers, so it and
`_TokenRejected` join the list (the import allowlist, poll.py's transport-name rule and the getattr and dunder bans
already keep them out; this is the same extra layer `_send` and `_kis_token` have). Old text:

```python
TRANSPORT_ONLY = frozenset({"requests", "HOSTS", "CREDENTIALS", "_send", "_rules", "_query", "_upbit_jwt",
                            "_okx_timestamp", "_okx_sign", "_kis_token", "_read_token", "_write_token",
                            "_check_answer", "_next_issue_at", "_okx_offset_s", "_bad_tokens"})
```

New text:

```python
TRANSPORT_ONLY = frozenset({"requests", "HOSTS", "CREDENTIALS", "_send", "_rules", "_query", "_upbit_jwt",
                            "_okx_timestamp", "_okx_sign", "_kis_token", "_read_token", "_write_token",
                            "_check_answer", "_next_issue_at", "_okx_offset_s", "_bad_tokens", "_headers",
                            "_TokenRejected"})
```

The guards scan only `execution/**/*.py` with this list, so a test helper of the same name (Task 6's `_headers` in
its test module) is unaffected.

- [ ] **Step 4: Run to verify it passes**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_transport/; echo "exit $?"
```

Expected: 30 PASS lines (the 19 tests of Step 2's FAIL lines and Task 2's 11), then `30/30 passed, 0 failed, 0 not
run` and `exit 0`.

The guards, which now read the full transport.py (the import allowlist, the verb, clock, write, token and
transport-only rules with the widened `TRANSPORT_ONLY`, the pinned `_send` and the `requests` forms):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/; echo "exit $?"
```

Expected: the 24 PASS lines of Task 2's Step 4, then `24/24 passed, 0 failed, 0 not run` and `exit 0`. A guard
failure names the file and the text: fix `execution/transport.py`, never the guard or a control.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_keys/; echo "exit $?"
```

Expected: `9/9 passed, 0 failed, 0 not run` and `exit 0`.

T-RO-01 alone on the real tree:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; t(); u(); print('T-RO-01 ok')"
```

Expected: `T-RO-01 ok`.

The execution suite through the real runner (KEYLESS; restore the results file; `timeout: 300000`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite execution; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

Expected last lines: `63/63 passed, 0 failed, 0 not run; ...qa\acceptance_results.json` (24 guards, 9 keys, 30
transport) and `exit 0`.

The cockpit suite, whose test_08, test_09, test_16 and test_18 read the grown transport.py (KEYLESS; restore;
`timeout: 300000`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

Expected last lines: exactly Task 1's Step 4b cockpit line, `47/47 passed, 0 failed, 0 not run;
...qa\acceptance_results.json`, and `exit 0`. Any other count is a drift ruling recorded in the ledger (Step 5 then
includes that file).

- [ ] **Step 5: Commit**

```bash
git status --short
```

Expected exactly these entries, in any order (`qa/acceptance_results.json` must NOT be among them):

```
 M execution/transport.py
 M tests/execution_fixtures.py
 M tests/execution_guards.py
 M tests/execution_transport.py
```

```bash
git add execution/transport.py tests/execution_fixtures.py tests/execution_guards.py tests/execution_transport.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

The two stat outputs must be identical, with these counts (git scales the +/- bars to the terminal; compare the
counts; a drift ruling recorded in the ledger adds the ledger to the list):

```
 execution/transport.py       | 242 +-
 tests/execution_fixtures.py  |  49 +
 tests/execution_guards.py    |   3 +-
 tests/execution_transport.py | 623 +-
 4 files changed, 901 insertions(+), 16 deletions(-)
```

Then commit. In the trailer, replace `<the committing model>` with the name of the model that writes this commit,
for example `Claude Sonnet 5.5` or `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "feat(execution): transport signing, sending, answer checks and the KIS token cache" -m "Completes execution/transport.py: per-attempt credentials, the Upbit HS512 JWT and OKX signature, one GET retry and 5 a second pacing, answer checks, and the shared KIS token cache checked before its POST; adds serve(), the tests and two transport-only guard names." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

Expected: the new commit on `e1-account-inquiry`, and `git status --short` prints nothing.
