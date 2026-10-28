### Task 2: keys.py, the allowlists and the refusal order

**Files:**
- Create: `execution/keys.py` (LF, UTF-8, no BOM)
- Create: `execution/transport.py` (LF, UTF-8, no BOM)
- Create: `execution/kis_inquiry.py` (LF, UTF-8, no BOM)
- Create: `execution/upbit_inquiry.py` (LF, UTF-8, no BOM)
- Create: `execution/okx_inquiry.py` (LF, UTF-8, no BOM)
- Create: `tests/execution_keys.py` (LF, UTF-8, no BOM)
- Create: `tests/execution_transport.py` (LF, UTF-8, no BOM; Task 3 appends to it)
- Modify: `tests/execution_fixtures.py` (anchors: the import block; the head of `isolated()`, its docstring through
  the line `patches = [(alerts, "_toast", _record_toast)]`; the tail of `isolated()`, its key-restoring loop; LF)
- Modify: `tests/execution_guards.py` (anchors: the last line of `test_suite_runs_hermetic_in_a_temp_home_with_seams`;
  the last two lines of `test_suite_is_registered_in_run_all_and_readme`, the end of the file; LF)
- Modify, only when this task records a drift ruling: `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`
  (anchor: its "Drift rulings" section; LF)
- Test: `tests/execution_keys.py`, `tests/execution_transport.py`, `tests/execution_guards.py`

**Interfaces:**
- Consumes:
  - Task 1 (as this plan's Task 1 writes them): `tests/execution_fixtures.py` `NOW`, `FAKE_KEYS`, `KEY_NAMES`,
    `_MISSING`, `class Refused(RuntimeError)`, `TOASTS`, `SLEEPS`, `STRAYS`, `REAL_SEND = None`, `_record_toast`,
    `isolated(home)` and its patch loop (`saved.append((obj, name, vars(obj).get(name, _MISSING)))`, restored in
    reverse); `tests/execution_acceptance.py` `_wrap(fn)` (`hermetic()`, `temp_home()`, `isolated(home)`);
    `tests/execution_guards.py` `ROOT`, `EXECUTION`, `X = "execution/x.py"`, `TRANSPORT = "execution/transport.py"`,
    `CG` (`tests.compliance_guards`), `_sources()` (rel path -> raw text of every `execution/**/*.py`) and the
    imports `ast`, `re`, `types`; `execution/__init__.py` (0 bytes); `tests.macro_m0_harness.TEXT_EXCEPTIONS` (the
    file-exact T-RO-01 exceptions for `execution/kis_inquiry.py` and `execution/upbit_inquiry.py`); test_09 skipping
    exactly `execution/kis_inquiry.py`.
  - Repo: `tests.compliance_guards._walk(node, funcs=())` (yields `(node, names of the functions whose BODY encloses
    it)`, parents before children) and `_imports(rel, tree)` (yields `(node, absolute module, imported names,
    funcs)`, relative imports resolved); `requests` 2.34.2 (`Session`, `Session.merge_environment_settings`,
    `Session.prepare_request`, `Request`, `exceptions`); `urllib.parse.quote`.
  - Contract sections 5 (keys.py), 6 (the Task 2 half of transport.py) and 7 (the three allowlists).
- Produces (later tasks rely on these exact names):
  - `execution/keys.py`: `_ENV_FILE` (seam; default `Path(__file__).resolve().parents[1] / ".env"`), `_NAME`,
    `class KeyMissing(Exception)` with `.name` and the message `"<NAME> is not set in .env or the environment"`,
    `read(names: Sequence[str]) -> tuple[str, ...]` (a str or any name not matching `_NAME` is
    `ValueError("keys: bad name")`, raised before anything is read; a name present in `os.environ` decides alone;
    `.env` is parsed at most once per call, only when a name is absent from the environment), `_parse(text) ->
    dict[str, str]`, `_clean(value) -> str`.
  - `execution/transport.py`: `HOSTS`, `CREDENTIALS`, `KIS_TOKEN_PATH`, `TIMEOUT_S`, `RETRY_AFTER_S`, `PACE_S`,
    `OKX_SKEW_LIMIT_S`, `TOKEN_REUSE_MARGIN_S`, `TOKEN_MIN_GAP_S`, `TOKEN_REISSUE_BLOCK_S`, `KIS_TOKEN_CODES`,
    `AUTH_CODES`, `_KEY`; `KeyMissing` (re-exported from keys); `InquiryRefused(reason)` (`.reason`, `args ==
    (reason,)`), `InquiryError`, `AuthError(InquiryError)`; `Answer(*, body, server_utc, received_utc, sha256)`
    (frozen, keyword-only, `body` not in the repr); `request(venue, method, path, params=None, *, tr_id=None) ->
    Answer` running steps 1-6 of contract section 6 and then `raise InquiryError("transport: sending arrives in Task
    3")`, the one line Task 3 replaces with the sending half; `require_keys(venue) -> None`; `_send` (final, pinned);
    `_sleep = time.sleep`; `_clock()` (raises `RuntimeError("transport: no clock; poll.main sets one")`);
    `_next_issue_at = None`, `_okx_offset_s = None`, `_bad_tokens = set()`; `_rules(venue) -> (ENDPOINTS, TR_IDS or
    frozenset(), PUBLIC)`; `_query(venue, path, params) -> str`. A private choice of this task (the contract is
    silent): anything in `params` that is not a 2-tuple with a str key is refused with the fixed reason
    `"<venue>: parameters must be (key, value) pairs"`, so a stray value never reaches a reason text (E37). A
    venue, method, path or TR id that is not a str gets no step of its own (callers pass literals; the guards hold
    the method to `"GET"`): it is refused as unknown or not listed, or an unhashable one raises TypeError, in both
    cases before any key is read or anything is sent.
  - `execution/kis_inquiry.py`: `ENDPOINTS`, `TR_IDS`, `PUBLIC = frozenset()`, `ACCOUNT_NAMES`; `upbit_inquiry.py`:
    `ENDPOINTS`, `PUBLIC`; `okx_inquiry.py`: `ENDPOINTS`, `PUBLIC`, `ALGO_TYPES` (contract section 7, verbatim).
    Tasks 5, 6 and 7 add the snapshots below these constants.
  - `tests/execution_fixtures.py`: `_refuse_send(method, url, *, headers, params, json_body, timeout)` (appends
    `"METHOD path"` to `STRAYS`, the path only, and raises `Refused("E1 transport send inside the execution suite")`);
    `fake_keys(**overrides)`; `isolated(home)` now also patches `REAL_SEND` (the unpatched `_send`, kept from an outer
    `isolated()` when nested), `transport._send -> _refuse_send`, `transport._sleep -> SLEEPS.append`,
    `transport._clock -> lambda: NOW`, `transport._next_issue_at -> None`, `transport._okx_offset_s -> None`,
    `transport._bad_tokens -> set()`, `keys._ENV_FILE -> home / "no-such.env"`. Task 3's `serve()` replaces
    `transport._send` inside `isolated()`, which restores `_refuse_send` on its way out.
  - `tests/execution_transport.py`: the helpers `_t2_seams`, `_t2_boom`, `_t2_reached`, `_T2Reached`, `_t2_refused`,
    `_t2_passes`, `_t2_patched` and the constants `_T2_BALANCE`, `_T2_CCNL`, `_T2_ORDER`, `_T2_MOCK`, `_T2_SKEW`
    (prefixed so Task 3's appended tests cannot shadow them; Task 3 may reuse them). These tests stay true once Task 3
    fills the sending half in: `_t2_passes` counts a key read or a send attempt as "past every check".
  - `tests/execution_guards.py`: the constants `KIS_FILE`, `UPBIT_FILE`, `POLL`, `KIS_ORDER_WORDS`, `UPBIT_EXACT`,
    `UPBIT_TOKEN`, `KIS_TOKEN`, `KIS_GET_PATHS`, `KIS_TRS`, `TR_SHAPE`, `ORDER_TR`, `OKX_ORDER_PATH`,
    `TRANSPORT_NAMES`, `CREDENTIAL_NAMES`, `SEND_SOURCE`, `TRANSPORT_ONLY`, `SEAM_ATTRS`, `GLOBALS_OK`, `DUNDERS`,
    `FRAME_ATTRS`, `REBINDERS`, `BINDERS`, `SEND_TEMPLATE`; the checkers `_upbit_token_hits`, `_kis_token_hits`,
    `_tr_hits`, `_token_hits`, `_path_hits`, `_import_path_hits`, `_send_def`, `_requests_hits` (private:
    `_targets`, `_rebind_ok`); six tests (24 in the module). What these guards demand of every later file under `execution/`:
    - transport.py uses `requests` only in its plain `import requests`, the `requests.Session()` in `_send` and
      `requests.exceptions.ConnectionError` (Task 3's retry); its only `global` names are `_next_issue_at` and
      `_okx_offset_s`;
    - outside transport.py: no name or attribute in `TRANSPORT_ONLY` (`requests`, `HOSTS`, `CREDENTIALS`, `_send`,
      `_rules`, `_query`, `_upbit_jwt`, `_okx_timestamp`, `_okx_sign`, `_kis_token`, `_read_token`, `_write_token`,
      `_check_answer`, `_next_issue_at`, `_okx_offset_s`, `_bad_tokens`); no `_clock`, `_sleep`, `transport`,
      `request` or `keys` attribute (a zero-argument `.keys()` call aside; poll.py's one `transport._clock = ...` in
      `main` aside); transport only as `from execution.transport import <TRANSPORT_NAMES>` with no alias; every
      `request(...)` call passes the literal `"GET"` as its second positional argument and the name `request` is
      used for nothing else; `from execution import keys` only in kis_inquiry.py, whose name `keys` appears only in
      its one `keys.read(ACCOUNT_NAMES)` call (Task 5); `from execution import transport` only in poll.py, whose
      name `transport` appears only in `transport._clock = ...` inside `main` (Task 12); no credential name, even in
      a docstring or comment; no string constant equal to a `TRANSPORT_ONLY` name (so `d["_send"] = f` fails too);
    - every file: an attribute is assigned only as `self.<name> = ...` in an `__init__`, `session.trust_env = False`
      in `transport._send` or `transport._clock = ...` in `poll.main`; `object.__setattr__(self, ...)` only in a
      `__post_init__` (Task 4); no `global` outside transport.py; no `setattr`, `delattr`, `vars`, `globals`, no
      `sys.modules`, no `__globals__`/`__dict__`/`__builtins__`/`__code__`/`__closure__`/`__subclasses__`/
      `__getattribute__`/`__getstate__`/`__self__` (a module's `__getstate__()` is its real namespace, a builtin's
      `__self__` is the builtins module); no frame or traceback attribute (`FRAME_ATTRS`: `f_globals`, `f_locals`,
      `f_back`, `f_builtins`, `f_code`, `tb_frame`, `tb_next`, `gi_frame`, `cr_frame`, `ag_frame`, `_getframe`; a
      frame reaches another module's globals), while `exc.__traceback__` itself stays allowed for Task 12's
      `traceback.extract_tb(exc.__traceback__)`; `getattr` only with a string constant that does not start with `_`
      and is not in `TRANSPORT_ONLY`, `SEAM_ATTRS` or `FRAME_ATTRS`;
    - raw text, docstrings and comments included: no `/uapi/` text but the nine GET paths, and only in
      kis_inquiry.py; no `/v1/order...` or `/v1/withdraw...` text but the four exact paths, and only in
      upbit_inquiry.py; no TR-shaped token (four letters, four digits, a letter) but the nine pinned ids, and only in
      kis_inquiry.py; nothing matching four letters, four digits and `U` in any case anywhere; no string constant
      equal to `/api/v5/trade/order`.

**Plan decisions used:** E2 (imports; keys.py rules), E3 (transport: one public `request`, the `_send` seam, the
allowlists, the hosts), E6 (the file-exact exceptions, held exact by the token rules), E10 (the allowlists live in the
venue modules; `_rules` imports them at call time), E12 (the query built once; `params=None` to `_send`; the pinned
Session with `trust_env = False` and `allow_redirects=False`), E13 (the refusal order, before any key is read), E14
(the account names only in kis_inquiry.py, the one `keys` importer besides transport), E27 (`export `, quotes,
inline comments, `<placeholder>`, `utf-8-sig`), E28 (the wrapper isolates keys and every transport seam), E36
(transport is the only way out), E37 (reasons from names only), E1R2-11 (the Session with `trust_env = False`).
Contract sections 0.2, 0.5, 3.2 (the Task 2 part of `isolated()`, `fake_keys()`), 4.5 (the Task 2 tests), 5, 6
(the Task 2 half) and 7.

Notes for the implementer (read before starting):
- This task runs on branch `e1-account-inquiry` right after Task 1's commit; `git status --short` prints nothing
  first. Run every command from the repo root `C:/Users/whydi/OneDrive/Desktop/TRADEGEN` in Git Bash (the Bash tool).
- Never open, print or edit `.env`. No test here reads it: `isolated()` points `keys._ENV_FILE` at a missing file in
  the temp home, and the key tests write their own small `.env` files inside the temp home.
- No test sends anything. The real `_send` runs once, with `transport.requests` swapped for a recorder; the
  trust_env test builds a real `requests.Session()` and asks it for its settings without sending; `hermetic()`
  refuses every socket connect anyway.
- The edits below are to Task 1's two new files, which no earlier plan touches. Re-read each file first (DRIFT RULE,
  contract 0.6): the quoted old text is the anchor. If Task 1 was executed with different text at an anchor, apply
  the same change to the current text, keep Task 1's behaviour, and record a one-line ruling in the ledger.
- `tests/` is outside every repo-wide scan, so the test files may spell the strings they look for (`order-cash`,
  `TTTC0802U`, `openapivts`, `/v1/orders`, ...). Never copy them into `execution/`. The token rules of
  `tests/execution_guards.py` read docstrings and comments too: in `execution/`, never write a `/uapi/` path, a
  `/v1/order...` or `/v1/withdraw...` path, a TR-shaped id or a credential name outside the places named above, not
  even in prose.
- QUANTGEN overlap check before EVERY test command (contract 0.3). Each test command below is one Git Bash command
  that starts with the check, so nothing runs while a `run_all` process is alive; when the check finds a process the
  command prints no summary line (only `exit 1`): wait, then run it again.
- Give every `--suite` command (Step 4 runs two) the Bash tool's `timeout: 300000`: the default 120 s is too close
  (contract 0.3).

- [ ] **Step 1: Write the failing tests**

First confirm the inputs (Git Bash, repo root; contract 0.4: `git ls-files --eol` before the first edit of a file):

```bash
git branch --show-current
git status --short
git ls-files --eol tests/execution_fixtures.py tests/execution_guards.py execution/__init__.py
ls execution/*.py
tail -n 1 tests/execution_fixtures.py tests/execution_guards.py
```

Expected: `e1-account-inquiry`; `git status --short` prints nothing; the two test files read
`i/lf    w/lf    attr/-text` and `execution/__init__.py` reads `i/none  w/none  attr/-text` (0 bytes, so git sees no
line ending); `ls` prints only `execution/__init__.py`; and the two last lines are the end-of-file anchors of
fixtures Edit 3 and guards Edit 2 below:

```
==> tests/execution_fixtures.py <==
                os.environ[name] = value

==> tests/execution_guards.py <==
        assert "execution" in CG._suite_names(path.read_text(encoding="utf-8")), path.name
```

A dirty tree or another branch: stop. Any other difference: apply the DRIFT RULE (contract 0.6) before editing.

1. `tests/execution_fixtures.py` (LF; Edit tool). Re-read the file first.

Edit 1, anchor: the import block at the top of the module. Old text:

```python
import contextlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
```

New text (adds `sys`, for the module's own `REAL_SEND` patch, and `urlsplit`, for the stray record):

```python
import contextlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit
```

Edit 2, anchor: the head of `isolated()`, from its docstring through the line
`    patches = [(alerts, "_toast", _record_toast)]`. Old text:

```python
    """The E1 seams for one test (E28), inside the wrapper's temp home `home` (Task 2 points keys._ENV_FILE there):
    the recorders are cleared, every name of KEY_NAMES leaves os.environ (config's load_dotenv put the real values
    there) and alerts._toast is the recorder. On the way out each patch is undone in reverse order and each key name
    gets its value from before the test back (one that was absent is removed again, whatever the test set). A test
    that returns normally with an entry left in STRAYS fails here."""
    from core.compliance import alerts
    patches = [(alerts, "_toast", _record_toast)]
```

New text (the same patch loop saves and restores every new seam; `REAL_SEND or transport._send` keeps an outer
`isolated()`'s value when Task 1's self-tests nest `_wrap`, so a nested exit never loses the real `_send`):

```python
    """The E1 seams for one test (E28), inside the wrapper's temp home `home`: the recorders are cleared, every name
    of KEY_NAMES leaves os.environ (config's load_dotenv put the real values there), alerts._toast is the recorder,
    and (Task 2) transport._send refuses and records a stray, REAL_SEND holds the unpatched _send (an outer
    isolated()'s, when nested), transport._sleep records into SLEEPS, transport._clock returns NOW, no token gap, OKX
    offset or bad token carries over, and keys._ENV_FILE is a missing file in `home`, so the repo .env is never
    read. On the way out each patch is undone in reverse order and each key name gets its value from before the
    test back (one that was absent is removed again, whatever the test set). A test that returns normally with an
    entry left in STRAYS fails here."""
    from core.compliance import alerts
    from execution import keys, transport
    patches = [(alerts, "_toast", _record_toast),
               (sys.modules[__name__], "REAL_SEND", REAL_SEND or transport._send),
               (transport, "_send", _refuse_send), (transport, "_sleep", SLEEPS.append),
               (transport, "_clock", lambda: NOW), (transport, "_next_issue_at", None),
               (transport, "_okx_offset_s", None), (transport, "_bad_tokens", set()),
               (keys, "_ENV_FILE", home / "no-such.env")]
```

Edit 3, anchor: the tail of `isolated()`, its key-restoring loop (the last five lines of the file). old_string is
these five lines, with no newline after the last:

```python
        for name, value in env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
```

new_string = those five lines, then `\n\n\n` (one newline ending the old last line, then two empty lines), then the
block from `def _refuse_send` up to and including the last line of `fake_keys()`,
`                os.environ[name] = value`, with NO newline after it. The file's existing final newline, which
old_string left outside the match, then closes the block, so the file still ends in exactly one newline. The whole
new_string, as it reads in the file:

```python
        for name, value in env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _refuse_send(method, url, *, headers, params, json_body, timeout):
    """Stands in for execution.transport._send under the suite (Task 2): records "METHOD path" in STRAYS (the
    path only: a KIS query holds the account number) and raises Refused, so no test can reach a venue."""
    STRAYS.append(f"{method} {urlsplit(url).path}")
    raise Refused("E1 transport send inside the execution suite")


@contextlib.contextmanager
def fake_keys(**overrides) -> Iterator[None]:
    """os.environ holds FAKE_KEYS with `overrides` applied (a None override removes that name); every name touched
    is back in its state at entry afterwards."""
    values = FAKE_KEYS | overrides
    saved = {name: os.environ.get(name) for name in values}
    try:
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
```

Check the end of the file from the repo root; it must print `True False False` (the block ends the file, no blank
line after it, no CR anywhere). The check matches the whole `saved.items()` loop of `fake_keys()`, because its last
line alone also ended the file before this edit:

```bash
.venv/Scripts/python.exe -c "import pathlib; b = pathlib.Path('tests/execution_fixtures.py').read_bytes(); print(b.endswith(b'        for name, value in saved.items():\n            if value is None:\n                os.environ.pop(name, None)\n            else:\n                os.environ[name] = value\n'), b.endswith(b'\n\n'), b'\r' in b)"
```

2. Create `tests/execution_keys.py` (LF) with exactly:

```python
"""execution/keys.py, the .env reader (E1 Task 2; contract section 5; E2, E27, E28).

Every test runs with every E1 key name out of os.environ and keys._ENV_FILE at a missing file in the temp home
(tests.execution_fixtures.isolated), so the repo .env is never read. A test that needs a file writes one in the temp
home and points _ENV_FILE at it with `_env_file`, which restores it. Only E1 key names are used: isolated() restores
each of them, whatever a test sets. No assertion message ever holds a value read by keys.read.
"""
from __future__ import annotations

import ast
import contextlib
import os
from pathlib import Path

from execution import keys
from tests import execution_fixtures as F

ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def _env_file(data: bytes):
    """keys._ENV_FILE -> a temp-home file holding exactly `data` (bytes, so a BOM and CRLF stay as written)."""
    path = Path(os.environ["TRADEGEN_HOME"]) / "test.env"
    path.write_bytes(data)
    keep = keys._ENV_FILE
    keys._ENV_FILE = path
    try:
        yield path
    finally:
        keys._ENV_FILE = keep


def _missing(names) -> keys.KeyMissing:
    """The KeyMissing that keys.read(names) raises; fails, without printing anything read, when values come back."""
    try:
        keys.read(names)
    except keys.KeyMissing as exc:
        return exc
    raise AssertionError(f"keys.read{tuple(names)!r} returned values")


def test_an_absent_name_falls_back_to_the_file():
    """A name absent from os.environ comes from .env, and the file is parsed at most once per call."""
    with _env_file(b"KIS_APP_KEY=file-value\nKIS_APP_SECRET=other\n"):
        assert "KIS_APP_KEY" not in os.environ
        assert keys.read(("KIS_APP_KEY",)) == ("file-value",)
        parsed, real_parse = [], keys._parse
        keys._parse = lambda text: parsed.append(1) or real_parse(text)
        try:
            assert keys.read(("KIS_APP_KEY", "KIS_APP_SECRET")) == ("file-value", "other")
        finally:
            keys._parse = real_parse
        assert parsed == [1], parsed


def test_parser_handles_export_quotes_comments_and_no_expansion():
    data = (b"# a full-line comment\n"
            b"   # an indented comment: KIS_APP_SECRET=hidden\n"
            b"#KIS_APP_SECRET=hidden-too\n"
            b"\n"
            b"export UPBIT_ACCESS_KEY=exported\n"
            b'UPBIT_SECRET_KEY="double # kept" ignored after the quote\n'
            b"OKX_API_KEY='single'\n"
            b"OKX_API_SECRET=ab+c/d== # an inline comment\n"
            b"OKX_API_PASSPHRASE=pa#ss\n"
            b"KIS_APP_KEY=tabbed\t# a tab comment\n"
            b"KIS_BASE_URL=${KIS_APP_KEY}$HOME\n"
            b"  KIS_ACCOUNT_8 =  spaced  \n"
            b"a line without an equals sign\n"
            b"KIS_ACCOUNT_PD=first\n"
            b"KIS_ACCOUNT_PD=second\n")
    with _env_file(data):
        assert keys.read(("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY", "OKX_API_KEY", "OKX_API_SECRET",
                          "OKX_API_PASSPHRASE", "KIS_APP_KEY", "KIS_BASE_URL", "KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")) == (
            "exported", "double # kept", "single", "ab+c/d==", "pa#ss", "tabbed", "${KIS_APP_KEY}$HOME", "spaced",
            "second")
        assert _missing(("KIS_APP_SECRET",)).name == "KIS_APP_SECRET"       # only ever in comments
    assert keys._parse("A=1\nA=2\n") == {"A": "2"}
    assert keys._parse("export B='x' # y\n") == {"B": "x"}
    assert keys._parse("S=a=b==\n") == {"S": "a=b=="}                         # split at the first =
    assert keys._parse("#A=1\n  # B=2\n") == {}                              # comment lines never become keys


def test_a_bom_and_crlf_lines_are_read():
    with _env_file(b"\xef\xbb\xbfKIS_APP_KEY=first\r\nKIS_APP_SECRET=second\r\n"):
        assert keys.read(("KIS_APP_KEY", "KIS_APP_SECRET")) == ("first", "second")


def test_blank_placeholder_and_missing_values_raise_key_missing_with_names_only():
    data = (b"KIS_APP_KEY=\nKIS_APP_SECRET=   \nUPBIT_ACCESS_KEY=<your Upbit access key>\n"
            b"UPBIT_SECRET_KEY='<unset>'\nOKX_API_KEY=\"\"\nKIS_BASE_URL=set\n")
    with _env_file(data):
        for name in ("KIS_APP_KEY", "KIS_APP_SECRET", "UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY", "OKX_API_KEY",
                     "OKX_API_SECRET"):                                         # the last is not in the file
            exc = _missing((name,))
            assert exc.name == name and exc.args == (f"{name} is not set in .env or the environment",), exc.args
            assert "<" not in str(exc) and "unset" not in str(exc), str(exc)
        assert _missing(("KIS_BASE_URL", "UPBIT_SECRET_KEY", "KIS_APP_KEY")).name == "UPBIT_SECRET_KEY"   # the first
    assert not keys._ENV_FILE.exists()                                          # the suite's missing file
    assert _missing(("OKX_API_PASSPHRASE",)).name == "OKX_API_PASSPHRASE"


def test_the_environment_decides_alone():
    """A name present in os.environ is never looked up in .env: '<unset>' or a blank value there is missing even
    when the file holds the name, so the KEYLESS prefix keeps E1 keyless."""
    with _env_file(b"".join(f"{n}=file-{n.lower()}\n".encode("ascii") for n in F.FAKE_KEYS)):
        for value in ("<unset>", "", "   ", " <unset> "):
            os.environ["KIS_APP_KEY"] = value
            assert _missing(("KIS_APP_KEY",)).name == "KIS_APP_KEY", repr(value)
        os.environ["KIS_APP_KEY"] = "  env-value  "
        assert keys.read(("KIS_APP_KEY", "KIS_APP_SECRET")) == ("env-value", "file-kis_app_secret")
        for name in F.FAKE_KEYS:                                                 # the KEYLESS prefix
            os.environ[name] = "<unset>"
        for name in F.FAKE_KEYS:
            assert _missing((name,)).name == name
    keep = keys._ENV_FILE
    try:
        keys._ENV_FILE = Path(os.environ["TRADEGEN_HOME"])                      # a folder: reading it fails
        os.environ["KIS_APP_KEY"], os.environ["KIS_APP_SECRET"] = "a", "b"
        assert keys.read(("KIS_APP_KEY", "KIS_APP_SECRET")) == ("a", "b")       # so the file was not read
        try:
            keys.read(("KIS_APP_KEY", "KIS_BASE_URL"))                         # KIS_BASE_URL is not in os.environ
        except OSError:
            pass                                                                # only an unreadable file fails
        else:
            raise AssertionError("a name absent from os.environ did not read .env")
    finally:
        keys._ENV_FILE = keep


def test_only_the_requested_names_come_back():
    with _env_file(b"KIS_APP_KEY=k\nKIS_APP_SECRET=s\nOKX_API_SECRET=o\n"):
        assert keys.read(("OKX_API_SECRET", "KIS_APP_KEY")) == ("o", "k")
        assert keys.read(["KIS_APP_SECRET"]) == ("s",)
        assert keys.read(()) == ()


def test_a_bad_name_is_refused_before_anything_is_read():
    keep = keys._ENV_FILE
    try:
        keys._ENV_FILE = Path(os.environ["TRADEGEN_HOME"])                      # reading it would raise OSError
        for names in (("kis_app_key",), ("1ABC",), ("A-B",), ("A B",), ("",), ("A=B",), ("KIS_APP_KEY", "x"),
                      (None,), ("_A",), "KIS_APP_KEY", "ABC"):              # "ABC": each letter is a good name
            try:
                keys.read(names)
            except ValueError as exc:
                assert str(exc) == "keys: bad name", str(exc)
            else:
                raise AssertionError(f"keys.read({names!r}) was not refused")
    finally:
        keys._ENV_FILE = keep


def test_the_suite_never_reads_the_repo_env():
    home = Path(os.environ["TRADEGEN_HOME"])
    assert keys._ENV_FILE == home / "no-such.env" and not keys._ENV_FILE.exists(), keys._ENV_FILE
    assert keys._ENV_FILE.resolve() != (ROOT / ".env").resolve()
    for name in F.KEY_NAMES:
        assert name not in os.environ, name
        assert _missing((name,)).name == name


def test_the_default_env_file_is_the_repo_root_env():
    """Checked from the source text: a reload would point _ENV_FILE back at the real .env in the middle of the suite
    (contract 0.2)."""
    tree = ast.parse((ROOT / "execution" / "keys.py").read_text(encoding="utf-8"))
    found = [ast.unparse(n.value) for n in tree.body
             if isinstance(n, ast.Assign) and [ast.unparse(t) for t in n.targets] == ["_ENV_FILE"]]
    assert found == ["Path(__file__).resolve().parents[1] / '.env'"], found
    assert Path(keys.__file__).resolve().parents[1] == ROOT, keys.__file__
```

3. Create `tests/execution_transport.py` (LF) with exactly:

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

ROOT = Path(__file__).resolve().parents[1]
_T2_BALANCE = "/uapi/domestic-stock/v1/trading/inquire-balance"
_T2_CCNL = "/uapi/overseas-stock/v1/trading/inquire-ccnl"
_T2_ORDER = "/uapi/domestic-stock/v1/trading/order-cash"
_T2_MOCK = "https://openapivts.koreainvestment.com:29443"
_T2_SKEW = "okx: the PC clock offset from OKX time is unknown or above 25 s; OKX requests not sent"


class _T2Reached(Exception):
    """Raised by the seams `_t2_passes` installs: request got past every check."""


@contextlib.contextmanager
def _t2_seams(read, send):
    """keys.read and transport._send replaced for one block, restored on exit."""
    keep = keys.read, T._send
    keys.read, T._send = read, send
    try:
        yield
    finally:
        keys.read, T._send = keep


def _t2_boom(*_a, **_k):
    raise AssertionError("a key was read or a send was made before the checks finished")


def _t2_reached(*_a, **_k):
    raise _T2Reached


def _t2_refused(venue, method, path, params=None, *, tr_id=None) -> str:
    """The reason of the InquiryRefused that request(...) raises while keys.read and _send both fail the test."""
    with _t2_seams(_t2_boom, _t2_boom):
        try:
            T.request(venue, method, path, params, tr_id=tr_id)
        except T.InquiryRefused as exc:
            assert exc.args == (exc.reason,), exc.args
            return exc.reason
        except T.InquiryError:
            pass
    raise AssertionError(f"not refused: {venue} {method} {path} tr_id={tr_id!r}")


def _t2_passes(venue, method, path, params=None, *, tr_id=None) -> bool:
    """True when request(...) gets past every check: Task 2 then fails closed with InquiryError; from Task 3 on it
    reads a key or tries to send, which the seams installed here turn into _T2Reached (no stray is recorded)."""
    with _t2_seams(_t2_reached, _t2_reached):
        try:
            T.request(venue, method, path, params, tr_id=tr_id)
        except T.InquiryRefused:
            return False
        except (T.InquiryError, _T2Reached):
            return True
    return True


@contextlib.contextmanager
def _t2_patched(module, name, value):
    """module.name = value for one block, restored on exit."""
    keep = getattr(module, name)
    setattr(module, name, value)
    try:
        yield
    finally:
        setattr(module, name, keep)


def test_constants_errors_and_answer_have_the_contract_shape():
    """Contract section 6: the constants Task 3 sends with, the three errors, the frozen keyword-only Answer whose
    repr never shows the body, and the module defaults the suite replaces, read from the source because isolated()
    has replaced them: _clock raises until poll.main binds one, _sleep is time.sleep, no token gap, no OKX offset,
    no bad token."""
    assert (T.TIMEOUT_S, T.RETRY_AFTER_S, T.PACE_S, T.OKX_SKEW_LIMIT_S) == (10.0, 2.0, 0.2, 25.0)
    assert (T.TOKEN_REUSE_MARGIN_S, T.TOKEN_MIN_GAP_S, T.TOKEN_REISSUE_BLOCK_S) == (120.0, 70.0, 21600.0)
    assert T.KIS_TOKEN_CODES == frozenset({"EGW00121", "EGW00122", "EGW00123"})
    assert type(T.AUTH_CODES) is types.MappingProxyType and dict(T.AUTH_CODES) == {
        "kis": frozenset({"EGW00103", "EGW00105", "EGW00205", "EGW00206", "EGW00304"}),
        "upbit": frozenset({"invalid_query_payload", "jwt_verification", "expired_access_key", "nonce_used",
                            "no_authorization_ip", "no_authorization_token", "out_of_scope"}),
        "okx": frozenset({"50030", "50035", "50100", "50101", "50103", "50104", "50105", "50106", "50107", "50110",
                          "50111", "50112", "50113", "50114", "50119", "50120", "50121", "50123"})}
    assert issubclass(T.AuthError, T.InquiryError) and not issubclass(T.InquiryRefused, T.InquiryError)
    exc = T.InquiryRefused("upbit: GET /x is not on the E1 allowlist")
    assert exc.reason == str(exc) == "upbit: GET /x is not on the E1 allowlist"
    answer = T.Answer(body={"access_token": "test-token-1"}, server_utc=None, received_utc=F.NOW, sha256="0" * 64)
    assert "test-token-1" not in repr(answer) and "body" not in repr(answer), repr(answer)
    try:
        answer.sha256 = "1" * 64
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("Answer is not frozen")
    try:
        T.Answer({"a": 1}, None, F.NOW, "0" * 64)
    except TypeError:
        pass
    else:
        raise AssertionError("Answer takes positional arguments")
    tree = ast.parse((ROOT / "execution" / "transport.py").read_text(encoding="utf-8"))
    defaults = {ast.unparse(n.targets[0] if isinstance(n, ast.Assign) else n.target): ast.unparse(n.value)
                for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None}
    assert [defaults[k] for k in ("_sleep", "_next_issue_at", "_okx_offset_s", "_bad_tokens")] == [
        "time.sleep", "None", "None", "set()"], defaults
    clock = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_clock"]
    assert len(clock) == 1 and ast.unparse(clock[0].body[-1]) == (
        "raise RuntimeError('transport: no clock; poll.main sets one')"), ast.dump(clock[0])


def test_every_refusal_comes_before_any_key_is_read():
    """Spec 9 "Transport": an unknown venue, a pair off the allowlist (order paths, a POST to an inquiry path, the
    mock host, a lowercase method), the token POST with parameters, a KIS TR that is an order TR, a mock TR, pinned
    to another path or missing, a TR id outside KIS, and a parameter that is not plain, each refused with its exact
    reason while reading a key or sending would fail the test."""
    not_listed = "is not on the E1 allowlist"
    cases = [
        (("binance", "GET", "/api/v3/account"), "unknown venue 'binance'"),
        (("KIS", "GET", _T2_BALANCE, None, "TTTC8434R"), "unknown venue 'KIS'"),
        (("kis", "POST", _T2_ORDER, None, "TTTC0802U"), f"kis: POST {_T2_ORDER} {not_listed}"),
        (("kis", "GET", _T2_ORDER, None, "TTTC0802U"), f"kis: GET {_T2_ORDER} {not_listed}"),
        (("kis", "POST", _T2_BALANCE, None, "TTTC8434R"), f"kis: POST {_T2_BALANCE} {not_listed}"),
        (("kis", "GET", "/oauth2/tokenP"), f"kis: GET /oauth2/tokenP {not_listed}"),
        (("kis", "POST", "/oauth2/tokenP", [("grant_type", "client_credentials")]),
         "kis: the token POST takes no parameters"),
        (("kis", "POST", "/oauth2/tokenP", []), "kis: the token POST takes no parameters"),
        (("kis", "POST", "/oauth2/tokenP", None, "TTTC8434R"), "kis: a TR id belongs only to a KIS inquiry"),
        (("kis", "GET", _T2_BALANCE, None, "TTTC0802U"),
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'TTTC0802U'"),
        (("kis", "GET", _T2_BALANCE, None, "VTTC8434R"),
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'VTTC8434R'"),
        (("kis", "GET", _T2_BALANCE, None, "TTTC0084R"),
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'TTTC0084R'"),
        (("kis", "GET", _T2_BALANCE, None, "tttc8434r"),
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'tttc8434r'"),
        (("kis", "GET", _T2_BALANCE, None, "tttc8434R"),                       # no case folding before the lookup
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'tttc8434R'"),
        (("kis", "GET", _T2_BALANCE), f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got None"),
        (("kis", "GET", _T2_MOCK + _T2_BALANCE, None, "TTTC8434R"), f"kis: GET {_T2_MOCK}{_T2_BALANCE} {not_listed}"),
        (("kis", "get", _T2_BALANCE, None, "TTTC8434R"), f"kis: get {_T2_BALANCE} {not_listed}"),
        (("upbit", "POST", "/v1/orders"), f"upbit: POST /v1/orders {not_listed}"),
        (("upbit", "DELETE", "/v1/orders/open"), f"upbit: DELETE /v1/orders/open {not_listed}"),
        (("upbit", "GET", "/v1/orders"), f"upbit: GET /v1/orders {not_listed}"),
        (("upbit", "GET", "/v1/order"), f"upbit: GET /v1/order {not_listed}"),
        (("upbit", "GET", "/v1/deposits/generate_coin_address"),
         f"upbit: GET /v1/deposits/generate_coin_address {not_listed}"),
        (("upbit", "GET", "/v1/withdraws/coin"), f"upbit: GET /v1/withdraws/coin {not_listed}"),
        (("upbit", "get", "/v1/accounts"), f"upbit: get /v1/accounts {not_listed}"),
        (("upbit", "GET", "/v1/accounts", None, "TTTC8434R"), "upbit: a TR id belongs only to a KIS inquiry"),
        (("okx", "GET", "/api/v5/trade/order"), f"okx: GET /api/v5/trade/order {not_listed}"),
        (("okx", "POST", "/api/v5/trade/order"), f"okx: POST /api/v5/trade/order {not_listed}"),
        (("okx", "GET", "/api/v5/asset/deposit-address"), f"okx: GET /api/v5/asset/deposit-address {not_listed}"),
        (("okx", "GET", "/api/v5/public/time", None, "TTTC8434R"), "okx: a TR id belongs only to a KIS inquiry"),
        (("upbit", "GET", "/v1/withdraws", [("limit ", "100")]), "upbit: parameter 'limit ' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("limit=1&x", "100")]), "upbit: parameter 'limit=1&x' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("ord-type", "1")]), "upbit: parameter 'ord-type' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("a.b", "1")]), "upbit: parameter 'a.b' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("a%41", "1")]), "upbit: parameter 'a%41' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("limit", 100)]), "upbit: parameter 'limit' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("limit",)]), "upbit: parameters must be (key, value) pairs"),
        (("upbit", "GET", "/v1/withdraws", {"limit": "100"}), "upbit: parameters must be (key, value) pairs"),
        (("upbit", "GET", "/v1/withdraws", "limit=100"), "upbit: parameters must be (key, value) pairs"),
        (("kis", "GET", _T2_BALANCE, [["PDNO", "005930"]], "TTTC8434R"), "kis: parameters must be (key, value) pairs"),
        (("kis", "GET", _T2_BALANCE, [(12345678, "01")], "TTTC8434R"), "kis: parameters must be (key, value) pairs"),
        (("kis", "GET", _T2_BALANCE, [("PDNO", None)], "TTTC8434R"), "kis: parameter 'PDNO' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("limit", "1 0")]), "upbit: parameter 'limit' is not plain"),
        (("upbit", "GET", "/v1/orders/closed", [("states[]", "done&cancel")]),
         "upbit: parameter 'states[]' is not plain"),
        (("upbit", "GET", "/v1/deposits", [("limit", "100%")]), "upbit: parameter 'limit' is not plain"),
        (("okx", "GET", "/api/v5/asset/asset-valuation", [("ccy", "US DT")]), "okx: parameter 'ccy' is not plain"),
        (("okx", "GET", "/api/v5/account/config"), _T2_SKEW),
    ]
    for args, reason in cases:
        assert T._okx_offset_s is None
        got = _t2_refused(*args[:4], tr_id=args[4] if len(args) > 4 else None)
        assert got == reason, (args, got)


def test_a_signed_okx_request_needs_a_known_offset_within_25_s():
    """Step 6 (E3): no offset, 26 s either way or NaN refuse every signed OKX request before any key is read; 25 s
    passes; the two public paths need no offset."""
    for offset in (None, 26.0, -26.0, 25.001, math.inf, math.nan):
        with _t2_patched(T, "_okx_offset_s", offset):
            assert _t2_refused("okx", "GET", "/api/v5/account/balance") == _T2_SKEW, offset
            assert _t2_refused("okx", "GET", "/api/v5/trade/orders-algo-pending",
                               [("ordType", "conditional")]) == _T2_SKEW, offset
            assert _t2_passes("okx", "GET", "/api/v5/public/time"), offset
            assert _t2_passes("okx", "GET", "/api/v5/market/ticker", [("instId", "BTC-USDT")]), offset
    for offset in (0.0, 25.0, -25.0):
        with _t2_patched(T, "_okx_offset_s", offset):
            assert _t2_passes("okx", "GET", "/api/v5/account/config"), offset
    assert T._okx_offset_s is None


def test_the_not_get_rule_holds_on_its_own():
    """Step 3 refuses a non-GET pair even when an edit puts it on a venue's allowlist."""
    with _t2_patched(upbit_inquiry, "ENDPOINTS", upbit_inquiry.ENDPOINTS | {("DELETE", "/v1/orders/open")}):
        assert _t2_refused("upbit", "DELETE", "/v1/orders/open") == "upbit: DELETE is not GET"
    with _t2_patched(kis_inquiry, "ENDPOINTS", kis_inquiry.ENDPOINTS | {("POST", _T2_BALANCE)}):
        assert _t2_refused("kis", "POST", _T2_BALANCE, tr_id="TTTC8434R") == "kis: POST is not GET"
    with _t2_patched(upbit_inquiry, "ENDPOINTS", upbit_inquiry.ENDPOINTS | {("POST", "/oauth2/tokenP")}):
        assert _t2_refused("upbit", "POST", "/oauth2/tokenP") == "upbit: POST is not GET"   # the exception is KIS's
    assert ("DELETE", "/v1/orders/open") not in upbit_inquiry.ENDPOINTS


def test_the_r_rule_holds_on_its_own():
    """Step 4 refuses a TR id that does not end in R even when an edit pins it to the path."""
    with _t2_patched(kis_inquiry, "TR_IDS", kis_inquiry.TR_IDS | {(_T2_BALANCE, "TTTC8434U")}):
        assert _t2_refused("kis", "GET", _T2_BALANCE, tr_id="TTTC8434U") == (
            f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'TTTC8434U'")
    assert all(tr.endswith("R") for _p, tr in kis_inquiry.TR_IDS)


def test_every_allowlisted_request_passes_the_checks():
    """The positive side: each pinned KIS pair, the token POST without parameters, every Upbit pair (signed values
    that quoting leaves alone), and every OKX pair once an offset is known. KIS values may need quoting."""
    for path, tr in sorted(kis_inquiry.TR_IDS):
        assert _t2_passes("kis", "GET", path, [("PDNO", "%"), ("INQR_DVSN", "01"), ("CTX_AREA_FK100", "")],
                          tr_id=tr), path
    assert _t2_passes("kis", "POST", "/oauth2/tokenP")
    for method, path in sorted(upbit_inquiry.ENDPOINTS):
        assert _t2_passes("upbit", method, path, [("states[]", "wait"), ("states[]", "watch"), ("limit", "100")])
    assert _t2_passes("upbit", "GET", "/v1/ticker", [("markets", "KRW BTC")])       # public: quoted, not refused
    from execution import okx_inquiry
    with _t2_patched(T, "_okx_offset_s", 0.0):
        for method, path in sorted(okx_inquiry.ENDPOINTS):
            assert _t2_passes("okx", method, path, [("ordType", "move_order_stop"), ("ccy", "USDT")]), path


def test_the_query_is_built_once_and_sent_as_built():
    """E12: ordered pairs, array keys repeated and unencoded, values quoted with safe=",", nothing reordered."""
    assert T._query("upbit", "/v1/orders/open", [("states[]", "wait"), ("states[]", "watch"), ("limit", "100")]) == (
        "states[]=wait&states[]=watch&limit=100")
    assert T._query("kis", _T2_CCNL, [("PDNO", "%"), ("ORD_DT", ""), ("X", "a/b c")]) == "PDNO=%25&ORD_DT=&X=a%2Fb%20c"
    assert T._query("upbit", "/v1/ticker", [("markets", "KRW-BTC,KRW-USDT")]) == "markets=KRW-BTC,KRW-USDT"
    assert T._query("upbit", "/v1/ticker", [("markets", "KRW BTC")]) == "markets=KRW%20BTC"
    assert T._query("okx", "/api/v5/trade/orders-algo-pending", [("ordType", "move_order_stop")]) == (
        "ordType=move_order_stop")
    assert T._query("okx", "/api/v5/account/balance", [("b", "2"), ("a", "1")]) == "b=2&a=1"
    assert T._query("kis", _T2_BALANCE, None) == "" and T._query("kis", _T2_BALANCE, []) == ""


def test_require_keys_names_the_first_missing_key_and_returns_nothing():
    for venue, first in (("kis", "KIS_APP_KEY"), ("upbit", "UPBIT_ACCESS_KEY"), ("okx", "OKX_API_KEY")):
        try:
            T.require_keys(venue)
        except T.KeyMissing as exc:
            assert exc.name == first, exc.name
        else:
            raise AssertionError(f"require_keys({venue!r}) passed with no keys")
    for venue, override, name in (("okx", {"OKX_API_SECRET": None}, "OKX_API_SECRET"),
                                  ("okx", {"OKX_API_PASSPHRASE": "<unset>"}, "OKX_API_PASSPHRASE"),
                                  ("upbit", {"UPBIT_SECRET_KEY": ""}, "UPBIT_SECRET_KEY"),
                                  ("kis", {"KIS_APP_SECRET": "  "}, "KIS_APP_SECRET")):
        with F.fake_keys(**override):
            try:
                T.require_keys(venue)
            except T.KeyMissing as exc:
                assert exc.name == name and "test-" not in str(exc), str(exc)
            else:
                raise AssertionError(f"require_keys({venue!r}) passed without {name}")
    seen = []
    real_read = keys.read
    with F.fake_keys():
        with _t2_patched(keys, "read", lambda names: seen.append(tuple(names)) or real_read(names)):
            assert [T.require_keys(v) for v in ("kis", "upbit", "okx")] == [None, None, None]
    assert seen == [("KIS_APP_KEY", "KIS_APP_SECRET"), ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"),
                    ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")], seen
    assert T.KeyMissing is keys.KeyMissing
    assert not any(name in os.environ for name in F.KEY_NAMES)                  # fake_keys restored every name


def test_send_opens_one_session_with_trust_env_off_and_no_redirects():
    """E1R2-11: the real _send runs against a recorder standing in for `requests` (no socket): one Session per
    call, trust_env already False when request runs, redirects off, the arguments passed through unchanged, the
    body read before the session closes, and (status, headers, content) returned."""
    calls = []

    class FakeResponse:
        status_code = 200
        headers = {"Date": F.DATE_HEADER}

        @property
        def content(self):
            calls.append(("content",))
            return b'{"ok": true}'

    class FakeSession:
        trust_env = True

        def __init__(self):
            calls.append(("session",))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            calls.append(("closed",))
            return False

        def request(self, method, url, **kw):
            calls.append(("request", method, url, self.trust_env, kw))
            return FakeResponse()

    assert F.REAL_SEND is not None and F.REAL_SEND is not T._send
    headers = {"Accept": "application/json"}
    body = {"grant_type": "client_credentials"}
    with _t2_patched(T, "requests", types.SimpleNamespace(Session=FakeSession, exceptions=requests.exceptions)):
        got = F.REAL_SEND("POST", "https://openapi.koreainvestment.com:9443/oauth2/tokenP", headers=headers,
                          params=None, json_body=body, timeout=10.0)
        got_get = F.REAL_SEND("GET", "https://api.upbit.com/v1/accounts", headers=headers, params=None,
                              json_body=None, timeout=10.0)
    assert T.requests is requests
    assert got == (200, {"Date": F.DATE_HEADER}, b'{"ok": true}') and got_get == got, (got, got_get)
    want = [("session",),
            ("request", "POST", "https://openapi.koreainvestment.com:9443/oauth2/tokenP", False,
             {"headers": headers, "params": None, "json": body, "timeout": 10.0, "allow_redirects": False}),
            ("content",), ("closed",),
            ("session",),
            ("request", "GET", "https://api.upbit.com/v1/accounts", False,
             {"headers": headers, "params": None, "json": None, "timeout": 10.0, "allow_redirects": False}),
            ("content",), ("closed",)]
    assert calls == want, calls


def test_trust_env_off_ignores_proxy_ca_bundle_and_netrc_settings():
    """What trust_env = False buys, checked offline on a real requests.Session (nothing is sent): with HTTPS_PROXY,
    REQUESTS_CA_BUNDLE, CURL_CA_BUNDLE and a NETRC file entry for the host in the environment, the settings a request
    would use hold no proxy, verify=True and no Authorization header; the same session with trust_env on picks
    each of them up (the control)."""
    home = Path(os.environ["TRADEGEN_HOME"])
    netrc = home / "netrc"
    netrc.write_text("machine api.upbit.com login someone password not-a-key\n", encoding="utf-8")
    url = "https://api.upbit.com/v1/accounts"
    names = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy", "NO_PROXY",
             "no_proxy", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NETRC")
    saved = {n: os.environ.get(n) for n in names}
    try:
        for n in names:
            os.environ.pop(n, None)
        os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9"
        os.environ["REQUESTS_CA_BUNDLE"] = os.environ["CURL_CA_BUNDLE"] = str(home / "no-such-bundle.pem")
        os.environ["NETRC"] = str(netrc)
        seen = {}
        for trust in (False, True):
            with requests.Session() as session:
                session.trust_env = trust
                settings = session.merge_environment_settings(url, {}, None, None, None)
                prepared = session.prepare_request(requests.Request("GET", url))
            seen[trust] = (settings["proxies"], settings["verify"], "Authorization" in prepared.headers)
    finally:
        for n, v in saved.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
    assert seen[False] == ({}, True, False), seen
    proxies, verify, auth = seen[True]
    assert (proxies.get("https"), verify, auth) == ("http://127.0.0.1:9", str(home / "no-such-bundle.pem"), True), seen


def test_unpatched_send_is_refused_under_the_suite():
    """The probe of spec 9: under the suite, transport._send itself (not patched by this test) refuses and records
    one stray. The test asserts the stray and clears it, so the wrapper passes."""
    assert F.REAL_SEND is not None and T._send is not F.REAL_SEND, "the suite did not patch transport._send"
    try:
        T._send("GET", "https://api.upbit.com/v1/ticker?markets=KRW-BTC", headers={}, params=None, json_body=None,
                timeout=10.0)
    except F.Refused as exc:
        assert str(exc) == "E1 transport send inside the execution suite", str(exc)
    else:
        raise AssertionError("an unpatched transport._send was not refused under the suite")
    assert F.STRAYS == ["GET /v1/ticker"], F.STRAYS
    F.STRAYS.clear()
```

4. `tests/execution_guards.py` (LF; Edit tool). Re-read the file first.

Edit 1, anchor: the last line of `test_suite_runs_hermetic_in_a_temp_home_with_seams` (contract 4.5: "from Task 2
also `transport._send` raises `Refused` and records a stray, `REAL_SEND` is the unpatched function and
`keys._ENV_FILE` is inside the temp home"). Old text:

```python
    assert alerts._toast("after", "the nested call") is True and F.TOASTS[-1] == ("after", "the nested call")
```

New text:

```python
    assert alerts._toast("after", "the nested call") is True and F.TOASTS[-1] == ("after", "the nested call")
    # Task 2: the transport and key seams
    from execution import keys, transport
    real, stub, bad = F.REAL_SEND, transport._send, transport._bad_tokens
    assert real is not None and (real.__module__, real.__name__) == ("execution.transport", "_send"), real
    assert (stub.__module__, stub.__name__) == (F.__name__, "_refuse_send"), stub
    try:
        stub("GET", "https://api.upbit.com/v1/ticker?markets=KRW-BTC", headers={}, params=None, json_body=None,
             timeout=10.0)
    except F.Refused:
        pass
    else:
        raise AssertionError("transport._send sent inside the suite")
    assert F.STRAYS == ["GET /v1/ticker"], F.STRAYS
    F.STRAYS.clear()
    assert keys._ENV_FILE == home / "no-such.env" and not keys._ENV_FILE.exists(), keys._ENV_FILE
    assert transport._clock() == F.NOW and transport._next_issue_at is None and transport._okx_offset_s is None
    assert bad == set() and F.SLEEPS == []
    transport._sleep(2.0)
    assert F.SLEEPS == [2.0], F.SLEEPS
    nested = []
    transport._next_issue_at, transport._okx_offset_s = 1.0, 2.0                # so the inner reset is visible
    try:
        EA._wrap(lambda: nested.append((F.REAL_SEND, transport._send, keys._ENV_FILE, transport._bad_tokens,
                                        transport._next_issue_at, transport._okx_offset_s)))()
        assert (transport._next_issue_at, transport._okx_offset_s) == (1.0, 2.0), "a nested exit lost a value"
    finally:
        transport._next_issue_at = transport._okx_offset_s = None
    assert nested[0][0] is real and nested[0][1] is stub and nested[0][3] is not bad, nested
    assert nested[0][2].parent != home and nested[0][2].name == "no-such.env", nested
    assert nested[0][4:] == (None, None), "isolated() carried a token gap or an OKX offset into the test"
    assert F.REAL_SEND is real and transport._send is stub and transport._bad_tokens is bad
    assert keys._ENV_FILE == home / "no-such.env"
```

Edit 2, anchor: the last two lines of `test_suite_is_registered_in_run_all_and_readme`, which end the file.
old_string is these two lines, with no newline after the second:

```python
    for path in (ROOT / "tests" / "run_all.py", ROOT / "README.md"):
        assert "execution" in CG._suite_names(path.read_text(encoding="utf-8")), path.name
```

new_string = those two lines, then `\n\n\n` (one newline ending the old last line, then two empty lines), then the
block from its first `#` up to and including the last line of `test_send_is_pinned`,
`    assert not _requests_hits(src), _requests_hits(src)`, with NO newline after it. The file's existing final
newline, which old_string left outside the match, then closes the block, so the file still ends in exactly one
newline. The whole new_string, as it reads in the file:

```python
    for path in (ROOT / "tests" / "run_all.py", ROOT / "README.md"):
        assert "execution" in CG._suite_names(path.read_text(encoding="utf-8")), path.name


# --------------------------------------------------------------------------- #
# Task 2: the pinned allowlists, the exact-string rules, the transport-only path and the pinned _send
# (contract 0.5, 4.5 and 7; spec 5, 8 "Read-only guards", 11; E10, E36, E1R2-11)
# --------------------------------------------------------------------------- #
KIS_FILE = "execution/kis_inquiry.py"      # the one file that may name KIS account fields and /trading/ paths
UPBIT_FILE = "execution/upbit_inquiry.py"  # the one file that may name the Upbit order and withdrawal paths
POLL = "execution/poll.py"                 # the one importer of the transport module (for transport._clock)
KIS_ORDER_WORDS = ("order-cash", "order-credit", "order-rvsecncl", "order-resv", "daytime-order", "/trading/order",
                   "/trading/daytime")                       # raw, lower-cased, in kis_inquiry.py
UPBIT_EXACT = frozenset({"/v1/orders/open", "/v1/orders/closed", "/v1/withdraws", "/v1/withdraws/coin_addresses"})
UPBIT_TOKEN = re.compile(r"(?i)/v1/(?:order|withdraw)[A-Za-z0-9_/\-]*")
KIS_TOKEN = re.compile(r"/uapi/[^\s'\"]*")
KIS_GET_PATHS = frozenset({                # the nine GET paths of contract section 7, written out here (never read
    "/uapi/domestic-stock/v1/trading/inquire-balance",          # from kis_inquiry.ENDPOINTS)
    "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl",
    "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
    "/uapi/domestic-stock/v1/trading/inquire-account-balance",
    "/uapi/domestic-stock/v1/trading/intgr-margin",
    "/uapi/overseas-stock/v1/trading/inquire-balance",
    "/uapi/overseas-stock/v1/trading/inquire-nccs",
    "/uapi/overseas-stock/v1/trading/inquire-ccnl",
    "/uapi/overseas-stock/v1/trading/inquire-present-balance",
})
KIS_TRS = frozenset({"TTTC8434R", "TTTC0084R", "TTTC0081R", "CTRP6548R", "TTTC0869R", "TTTS3012R", "TTTS3018R",
                     "TTTS3035R", "CTRP6504R"})            # the nine TR ids of contract section 7, written out here
TR_SHAPE = re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z]{4}[0-9]{4}[A-Z](?![A-Za-z0-9])")
ORDER_TR = re.compile(r"(?i)[A-Z]{4}[0-9]{4}U")
OKX_ORDER_PATH = "/api/v5/trade/order"     # the GET also serves the order POST: never a string constant (spec 5)
TRANSPORT_NAMES = frozenset({"request", "require_keys", "Answer", "InquiryRefused", "InquiryError", "AuthError",
                             "KeyMissing"})  # what other modules may import from execution.transport
CREDENTIAL_NAMES = ("KIS_APP_KEY", "KIS_APP_SECRET", "UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY", "OKX_API_KEY",
                    "OKX_API_SECRET", "OKX_API_PASSPHRASE")
SEND_SOURCE = ("def _send(method, url, *, headers, params, json_body, timeout):\n"     # ast.unparse of the whole
               "    with requests.Session() as session:\n"                               # _send of section 6
               "        session.trust_env = False\n"                                     # (E1R2-11; checked with
               "        resp = session.request(method, url, headers=headers, params=params, json=json_body, "
               "timeout=timeout, allow_redirects=False)\n"                               # the venv's ast.unparse)
               "        return (resp.status_code, resp.headers, resp.content)")
# transport.py's own names: outside it, none of them is a name, an attribute, an imported name or a getattr string
TRANSPORT_ONLY = frozenset({"requests", "HOSTS", "CREDENTIALS", "_send", "_rules", "_query", "_upbit_jwt",
                            "_okx_timestamp", "_okx_sign", "_kis_token", "_read_token", "_write_token",
                            "_check_answer", "_next_issue_at", "_okx_offset_s", "_bad_tokens"})
# attributes no module but transport.py reads or writes (poll.py's one `transport._clock = ...` aside): the two
# send-time seams, the modules a getattr chain would reach, and request (so it is always called by its own name)
SEAM_ATTRS = frozenset({"_clock", "_sleep", "transport", "keys", "request"})
GLOBALS_OK = frozenset({"_next_issue_at", "_okx_offset_s"})   # the only `global` names, in transport.py only
DUNDERS = frozenset({"__globals__", "__dict__", "__builtins__", "__code__", "__closure__", "__subclasses__",
                     "__getattribute__", "__getstate__", "__self__"})   # a module's __getstate__() is its namespace
FRAME_ATTRS = frozenset({"f_globals", "f_locals", "f_back", "f_builtins", "f_code", "tb_frame", "tb_next",
                         "gi_frame", "cr_frame", "ag_frame", "_getframe"})   # a frame reaches another module's globals
REBINDERS = frozenset({"setattr", "delattr", "vars", "globals"})
BINDERS = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Delete, ast.For, ast.AsyncFor, ast.withitem,
           ast.comprehension)
SEND_TEMPLATE = ("import requests\n\n"                # contract section 6's _send, wrapped and commented as written
                 "def _send(method, url, *, headers, params, json_body, timeout):\n"
                 "    with requests.Session() as session:\n"
                 "        session.trust_env = False                  # no proxy, CA bundle or .netrc\n"
                 "        resp = session.request(method, url, headers=headers, params=params, json=json_body,\n"
                 "                               timeout=timeout, allow_redirects=False)\n"
                 "        return resp.status_code, resp.headers, resp.content\n")


def _upbit_token_hits(rel: str, src: str) -> list[str]:
    """Raw text: every Upbit order or withdrawal path token is one of the four exact paths, in upbit_inquiry.py."""
    return [f"{rel}: {m.group(0)!r}: only the four exact Upbit inquiry paths, only in {UPBIT_FILE}"
            for m in UPBIT_TOKEN.finditer(src) if rel != UPBIT_FILE or m.group(0) not in UPBIT_EXACT]


def _kis_token_hits(rel: str, src: str) -> list[str]:
    """Raw text: every /uapi/ token is one of the nine GET paths, in kis_inquiry.py, which names no order path."""
    hits = [f"{rel}: {m.group(0)!r}: only the nine KIS GET paths, only in {KIS_FILE}"
            for m in KIS_TOKEN.finditer(src) if rel != KIS_FILE or m.group(0) not in KIS_GET_PATHS]
    if rel == KIS_FILE:
        hits += [f"{rel}: {w!r}: a KIS order path word" for w in KIS_ORDER_WORDS if w in src.lower()]
    return hits


def _tr_hits(rel: str, src: str) -> list[str]:
    """Raw text: every TR-shaped token is one of the nine pinned TR ids, in kis_inquiry.py; no order TR shape (four
    letters, four digits, U) in any file, in any case; and no string constant equal to the OKX single-order path."""
    hits = [f"{rel}: {m.group(0)!r}: only the nine pinned TR ids, only in {KIS_FILE}"
            for m in TR_SHAPE.finditer(src) if rel != KIS_FILE or m.group(0) not in KIS_TRS]
    hits += [f"{rel}: {m.group(0)!r}: a KIS order TR shape" for m in ORDER_TR.finditer(src)]
    return hits + [f"{rel}:{n.lineno}: {OKX_ORDER_PATH!r}" for n in ast.walk(ast.parse(src))
                   if isinstance(n, ast.Constant) and n.value == OKX_ORDER_PATH]


def _token_hits(rel: str, src: str) -> list[str]:
    """The Upbit, KIS-path, TR and order-TR rules of contract 0.5, docstrings and comments included."""
    return _upbit_token_hits(rel, src) + _kis_token_hits(rel, src) + _tr_hits(rel, src)


def _targets(node: ast.AST) -> list[ast.expr]:
    """The binding targets of an assignment, del, for, with-item or comprehension node, tuples flattened."""
    if isinstance(node, (ast.Assign, ast.Delete)):
        todo = list(node.targets)
    elif isinstance(node, ast.withitem):
        todo = [node.optional_vars] if node.optional_vars is not None else []
    else:                                   # AugAssign, AnnAssign, For, AsyncFor, comprehension
        todo = [node.target]
    out = []
    while todo:
        target = todo.pop()
        if isinstance(target, (ast.Tuple, ast.List)):
            todo.extend(target.elts)
        elif isinstance(target, ast.Starred):
            todo.append(target.value)
        else:
            out.append(target)
    return out


def _rebind_ok(rel: str, node: ast.AST, target: ast.Attribute, funcs: tuple[str, ...]) -> bool:
    """The only attribute targets allowed: `session.trust_env = False` in transport._send, `transport._clock = ...`
    in poll.main, and `self.<name> = ...` in an __init__ (an exception's own fields)."""
    text = ast.unparse(target)
    if isinstance(node, ast.Assign) and (rel, funcs, text) in ((TRANSPORT, ("_send",), "session.trust_env"),
                                                               (POLL, ("main",), "transport._clock")):
        return True
    return (isinstance(node, (ast.Assign, ast.AnnAssign)) and funcs[-1:] == ("__init__",)
            and isinstance(target.value, ast.Name) and target.value.id == "self")


def _import_path_hits(rel: str, tree: ast.AST) -> list[str]:
    """Outside transport.py: transport only as `from execution.transport import <TRANSPORT_NAMES>` with no alias,
    the module only as `from execution import transport` in poll.py, execution.keys only as `from execution import
    keys` in kis_inquiry.py, and no transport-only name imported from any execution module."""
    hits = []
    for node, module, names, _f in CG._imports(rel, tree):
        aliased = {a.name for a in node.names if a.asname}
        if isinstance(node, ast.Import):
            if any(module == m or module.startswith(m + ".") for m in ("execution.transport", "execution.keys")):
                hits.append(f"{rel}:{node.lineno}: import {module}")
        elif module == "execution.transport":
            bad = sorted(n for n in names if n not in TRANSPORT_NAMES or n in aliased)
            if bad:
                hits.append(f"{rel}:{node.lineno}: from execution.transport import {', '.join(bad)}")
        elif module == "execution.keys" or module.startswith("execution.keys."):
            hits.append(f"{rel}:{node.lineno}: from {module} import ...")
        elif module == "execution" or module.startswith("execution."):
            for name in names:
                allowed = module == "execution" and name not in aliased and (
                    (name == "transport" and rel == POLL) or (name == "keys" and rel == KIS_FILE))
                if (name in ("transport", "keys") or name in TRANSPORT_ONLY) and not allowed:
                    hits.append(f"{rel}:{node.lineno}: from {module} import {name}")
    return hits


def _path_hits(rel: str, src: str) -> list[str]:
    """Transport is the only way out, and nothing rebinds from outside (contract 0.5, E36).

    Every file: no `global` but transport.py's two; no attribute as the target of an assignment, augmented or
    annotated assignment, del, for, with or comprehension, except the three of `_rebind_ok`; no setattr, delattr,
    vars or globals; getattr only with a string-constant name that does not start with `_` and is not a
    transport-only, seam or frame name; no DUNDERS attribute (__globals__, __dict__, __getstate__, __self__ and the
    rest) and no FRAME_ATTRS attribute (a frame or traceback reaches another module's globals; exc.__traceback__
    itself is allowed); `object.__setattr__(self, ...)` only in a __post_init__; no sys.modules in any form.
    Outside transport.py also: no transport-only name (requests, the hosts, the credentials, _send, the signing and
    token helpers) as a name, an attribute or a string constant; no `_clock`, `_sleep`, `transport`, `request` or
    `keys` attribute (a `.keys()` call aside); the
    import rules of `_import_path_hits`; every `request` name the function of a call whose second positional
    argument is the literal "GET"; in poll.py the name transport only in `transport._clock = ...` in main; in
    kis_inquiry.py the name keys only in its one `keys.read(ACCOUNT_NAMES)` call; no credential name, even in a
    docstring or comment."""
    tree, hits, ok = ast.parse(src), [], set()     # ok: id() of the nodes an allowed form covers
    outside = rel != TRANSPORT
    if rel == KIS_FILE:
        reads = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) == "keys.read"
                 and [ast.unparse(a) for a in n.args] == ["ACCOUNT_NAMES"] and not n.keywords]
        ok.update({id(reads[0].func.value)} if len(reads) == 1 else set())
    for node, funcs in CG._walk(tree):              # parents come before their children, so `ok` is ready
        if isinstance(node, ast.Global) and (outside or not set(node.names) <= GLOBALS_OK):
            hits.append(f"{rel}:{node.lineno}: global {', '.join(node.names)}")
        elif isinstance(node, BINDERS):
            for target in _targets(node):
                if isinstance(target, ast.Attribute) and _rebind_ok(rel, node, target, funcs):
                    ok.update({id(target), id(target.value)})
                elif isinstance(target, ast.Attribute):
                    hits.append(f"{rel}:{target.lineno}: rebinds {ast.unparse(target)}")
        elif isinstance(node, ast.Call):
            func, args = ast.unparse(node.func), node.args
            first_two_plain = len(args) >= 2 and not any(isinstance(a, ast.Starred) for a in args[:2])
            if (func == "getattr" and first_two_plain and isinstance(args[1], ast.Constant)
                    and isinstance(args[1].value, str) and not args[1].value.startswith("_")
                    and args[1].value not in TRANSPORT_ONLY | SEAM_ATTRS | FRAME_ATTRS):
                ok.add(id(node.func))
            elif func == "request" and first_two_plain and isinstance(args[1], ast.Constant) and args[1].value == "GET":
                ok.add(id(node.func))
            elif func == "object.__setattr__" and funcs[-1:] == ("__post_init__",) and args and (
                    ast.unparse(args[0]) == "self"):
                ok.add(id(node.func))
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "keys" and not args and not node.keywords:
                ok.add(id(node.func))                                   # a mapping's .keys()
        if isinstance(node, ast.Name):
            name, seen = node.id, id(node) in ok
            if name in REBINDERS or name in DUNDERS or (name == "getattr" and not seen):
                hits.append(f"{rel}:{node.lineno}: {name}")
            elif outside and (name in TRANSPORT_ONLY or (name == "request" and not seen)
                              or (name == "transport" and rel == POLL and not seen)
                              or (name == "keys" and rel == KIS_FILE and not seen)):
                hits.append(f"{rel}:{node.lineno}: {name} outside its one allowed use")
        elif isinstance(node, ast.Attribute):
            if node.attr in DUNDERS or node.attr in FRAME_ATTRS or ast.unparse(node) == "sys.modules" or (
                    node.attr in ("__setattr__", "__delattr__") and id(node) not in ok):
                hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
            elif outside and id(node) not in ok and (node.attr in TRANSPORT_ONLY or node.attr in SEAM_ATTRS):
                hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)} outside {TRANSPORT}")
        elif outside and isinstance(node, ast.Constant) and node.value in TRANSPORT_ONLY:
            hits.append(f"{rel}:{node.lineno}: the string {node.value!r} outside {TRANSPORT}")
    if outside:
        hits += _import_path_hits(rel, tree)
        hits += [f"{rel}: names the credential {n}" for n in CREDENTIAL_NAMES if n in src]
    return hits


def _send_def(src: str) -> str | None:
    """ast.unparse of the one module-level `def _send` of `src`; None when there is not exactly one or the name
    `_send` is bound anywhere else."""
    tree = ast.parse(src)
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_send"]
    rebound = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "_send"
               and isinstance(n.ctx, (ast.Store, ast.Del))]
    return ast.unparse(defs[0]) if len(defs) == 1 and not rebound else None


def _requests_hits(src: str) -> list[str]:
    """Every `requests` in transport.py is its plain `import requests`, the requests.Session in _send or
    requests.exceptions.ConnectionError (E1R2-11)."""
    tree, hits, allowed = ast.parse(src), [], set()
    for node, funcs in CG._walk(tree):
        if isinstance(node, ast.Import):
            hits += [f"{node.lineno}: import {a.name}" + (f" as {a.asname}" if a.asname else "")
                     for a in node.names if a.name.split(".")[0] == "requests" and (a.asname or a.name != "requests")]
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "requests":
            hits.append(f"{node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Attribute):
            text = ast.unparse(node)
            if text == "requests.Session" and funcs == ("_send",):
                allowed.add(id(node.value))
            elif text == "requests.exceptions.ConnectionError":
                allowed.add(id(node.value.value))
        elif isinstance(node, ast.Name) and node.id == "requests" and id(node) not in allowed:
            hits.append(f"{node.lineno}: requests used outside its three allowed forms")
    return hits


def test_allowlists_are_pinned():
    """Contract 7 (spec 5: "a test pins each one exactly"): every allowlist equals the set written out here, the hosts
    are the real ones, the KIS token POST is the only entry that is not a GET, every KIS GET path has exactly one TR
    id and it ends in R, and the OKX single-order path is not listed."""
    from execution import kis_inquiry, okx_inquiry, transport, upbit_inquiry
    kis_tr_ids = frozenset({
        ("/uapi/domestic-stock/v1/trading/inquire-balance", "TTTC8434R"),
        ("/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl", "TTTC0084R"),
        ("/uapi/domestic-stock/v1/trading/inquire-daily-ccld", "TTTC0081R"),
        ("/uapi/domestic-stock/v1/trading/inquire-account-balance", "CTRP6548R"),
        ("/uapi/domestic-stock/v1/trading/intgr-margin", "TTTC0869R"),
        ("/uapi/overseas-stock/v1/trading/inquire-balance", "TTTS3012R"),
        ("/uapi/overseas-stock/v1/trading/inquire-nccs", "TTTS3018R"),
        ("/uapi/overseas-stock/v1/trading/inquire-ccnl", "TTTS3035R"),
        ("/uapi/overseas-stock/v1/trading/inquire-present-balance", "CTRP6504R"),
    })
    upbit = frozenset({("GET", "/v1/accounts"), ("GET", "/v1/orders/open"), ("GET", "/v1/orders/closed"),
                       ("GET", "/v1/withdraws"), ("GET", "/v1/withdraws/coin_addresses"), ("GET", "/v1/deposits"),
                       ("GET", "/v1/api_keys"), ("GET", "/v1/status/wallet"), ("GET", "/v1/ticker")})
    okx = frozenset({("GET", "/api/v5/account/config"), ("GET", "/api/v5/account/balance"),
                     ("GET", "/api/v5/account/positions"), ("GET", "/api/v5/asset/balances"),
                     ("GET", "/api/v5/asset/asset-valuation"), ("GET", "/api/v5/finance/savings/balance"),
                     ("GET", "/api/v5/finance/flexible-loan/loan-info"), ("GET", "/api/v5/trade/orders-pending"),
                     ("GET", "/api/v5/trade/orders-algo-pending"), ("GET", "/api/v5/trade/fills"),
                     ("GET", "/api/v5/asset/deposit-history"), ("GET", "/api/v5/asset/withdrawal-history"),
                     ("GET", "/api/v5/public/time"), ("GET", "/api/v5/market/ticker")})
    assert {p for p, _t in kis_tr_ids} == KIS_GET_PATHS and {t for _p, t in kis_tr_ids} == KIS_TRS
    sets = (kis_inquiry.ENDPOINTS, kis_inquiry.TR_IDS, kis_inquiry.PUBLIC, upbit_inquiry.ENDPOINTS,
            upbit_inquiry.PUBLIC, okx_inquiry.ENDPOINTS, okx_inquiry.PUBLIC)
    assert all(type(s) is frozenset for s in sets), [type(s).__name__ for s in sets]
    kis = frozenset({("POST", "/oauth2/tokenP")} | {("GET", p) for p in KIS_GET_PATHS})
    assert kis_inquiry.ENDPOINTS == kis, sorted(kis_inquiry.ENDPOINTS ^ kis)
    assert kis_inquiry.TR_IDS == kis_tr_ids, sorted(kis_inquiry.TR_IDS ^ kis_tr_ids)
    assert kis_inquiry.PUBLIC == frozenset() and kis_inquiry.ACCOUNT_NAMES == ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")
    assert upbit_inquiry.ENDPOINTS == upbit, sorted(upbit_inquiry.ENDPOINTS ^ upbit)
    assert upbit_inquiry.PUBLIC == frozenset({"/v1/ticker"})
    assert okx_inquiry.ENDPOINTS == okx, sorted(okx_inquiry.ENDPOINTS ^ okx)
    assert okx_inquiry.PUBLIC == frozenset({"/api/v5/public/time", "/api/v5/market/ticker"})
    assert okx_inquiry.ALGO_TYPES == ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")
    assert type(transport.HOSTS) is types.MappingProxyType and dict(transport.HOSTS) == {
        "kis": "https://openapi.koreainvestment.com:9443", "upbit": "https://api.upbit.com",
        "okx": "https://www.okx.com"}, dict(transport.HOSTS)
    assert type(transport.CREDENTIALS) is types.MappingProxyType and dict(transport.CREDENTIALS) == {
        "kis": ("KIS_APP_KEY", "KIS_APP_SECRET"), "upbit": ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"),
        "okx": ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")}
    assert transport.KIS_TOKEN_PATH == "/oauth2/tokenP"
    assert sorted(e for e in kis_inquiry.ENDPOINTS if e[0] != "GET") == [("POST", "/oauth2/tokenP")]
    assert all(m == "GET" for m, _p in upbit_inquiry.ENDPOINTS | okx_inquiry.ENDPOINTS)
    gets = {p for m, p in kis_inquiry.ENDPOINTS if m == "GET"}
    assert {p for p, _t in kis_inquiry.TR_IDS} == gets and len(kis_inquiry.TR_IDS) == len(gets)   # one TR per path
    assert all(p.startswith("/uapi/") for p in gets) and all(t.endswith("R") for _p, t in kis_inquiry.TR_IDS)
    assert ("GET", OKX_ORDER_PATH) not in okx_inquiry.ENDPOINTS
    for module in (upbit_inquiry, okx_inquiry):
        assert module.PUBLIC <= {p for _m, p in module.ENDPOINTS}, module.__name__


def test_kis_strings_are_exact():
    """Contract 0.5 and spec 8 "KIS exception": every /uapi/ string in execution/ is one of the nine GET paths, in
    kis_inquiry.py only, and that file holds no order path word, raw text included. The nine paths are written out
    here, never read from kis_inquiry.ENDPOINTS, so an edit that adds an order path to the file and to its
    allowlist still fails."""
    for path in sorted(KIS_GET_PATHS):
        assert not _kis_token_hits(KIS_FILE, f'P = "{path}"\n'), path
        assert _kis_token_hits(X, f'P = "{path}"\n') and _kis_token_hits(TRANSPORT, f'"""{path}"""\n'), path
    for src in ('P = "/uapi/overseas-stock/v1/trading/order"\n',
                'P = "/uapi/domestic-stock/v1/trading/inquire-psbl-order"\n',
                'P = "/uapi/overseas-stock/v1/trading/"\n',
                'P = "/uapi/domestic-stock/v1/trading/" + "order-cash"\n',
                '"""reads `/uapi/domestic-stock/v1/trading/inquire-balance` only"""\n',   # the backtick is in it
                'P = "/uapi/domestic-stock/v1/trading/inquire-balance?x=1"\n'):
        assert _kis_token_hits(KIS_FILE, src), src
    for word in KIS_ORDER_WORDS:
        assert _kis_token_hits(KIS_FILE, f"# {word.upper()}\n"), word
    real = (EXECUTION / "kis_inquiry.py").read_text(encoding="utf-8")
    order = '    ("GET", "/uapi/overseas-stock/v1/trading/order"),\n'
    patched = real.replace("ENDPOINTS = frozenset({\n", "ENDPOINTS = frozenset({\n" + order, 1)
    assert patched != real and _kis_token_hits(KIS_FILE, patched)
    from execution import kis_inquiry
    keep = kis_inquiry.ENDPOINTS
    try:
        kis_inquiry.ENDPOINTS = keep | {("GET", "/uapi/overseas-stock/v1/trading/order")}
        assert _kis_token_hits(KIS_FILE, patched)            # the rule never reads the module's allowlist
    finally:
        kis_inquiry.ENDPOINTS = keep
    files = _sources()
    assert KIS_FILE in files and TRANSPORT in files, sorted(files)
    hits = [h for rel, src in files.items() for h in _kis_token_hits(rel, src)]
    assert not hits, hits


def test_upbit_strings_are_exact():
    """Contract 0.5 and spec 8 "Upbit exception": every Upbit order or withdrawal path token in execution/ is one of
    /v1/orders/open, /v1/orders/closed, /v1/withdraws and /v1/withdraws/coin_addresses, in upbit_inquiry.py only."""
    for path in sorted(UPBIT_EXACT):
        assert not _upbit_token_hits(UPBIT_FILE, f'P = "{path}"\n'), path
    for path in ("/v1/withdraws/coin", "/v1/withdraws/krw", "/v1/withdraws/chance", "/v1/orders", "/v1/order",
                 "/v1/orders/uuids", "/v1/orders/chance", "/v1/orders/cancel_and_new", "/V1/ORDERS/OPEN",
                 "/v1/orders/open/x"):
        assert _upbit_token_hits(UPBIT_FILE, f'P = "{path}"\n'), path
    assert _upbit_token_hits(X, 'P = "/v1/orders/open"\n') and _upbit_token_hits(TRANSPORT, "# /v1/withdraws\n")
    assert not _upbit_token_hits(X, 'A = "/v1/accounts"\nD = "/v1/deposits"\nO = "/api/v5/trade/orders-pending"\n'
                                    'K = "/uapi/domestic-stock/v1/trading/inquire-balance"\n')
    files = _sources()
    assert UPBIT_FILE in files, sorted(files)
    hits = [h for rel, src in files.items() for h in _upbit_token_hits(rel, src)]
    assert not hits, hits


def test_no_order_tr_anywhere():
    """Contract 0.5: every TR-shaped token is one of the nine pinned ids, upper-case, in kis_inquiry.py only; no
    file in execution/ holds the order TR shape (four letters, four digits, U) in any case, raw text included; and
    no file holds the OKX single-order path as a string constant."""
    for tr in sorted(KIS_TRS):
        assert not _tr_hits(KIS_FILE, f'T = "{tr}"\n'), tr
        assert _tr_hits(X, f'T = "{tr}"\n'), tr
    for src in ('T = "tttc0012u"\n', "# TTTT1002U\n", '"""ttts1002u"""\n', 'T = "TTTC0802U"\n', 'T = "xTTTC0011U"\n'):
        for rel in (X, KIS_FILE, UPBIT_FILE, TRANSPORT):
            assert _tr_hits(rel, src), (rel, src)
    assert _tr_hits(KIS_FILE, 'T = "TTTC0084X"\n') and _tr_hits(KIS_FILE, 'T = "tttc8434r"\n')
    assert not _tr_hits(TRANSPORT, 'C = {"EGW00121", "KIOK0510", "HS512", "SHA512", "50120", "dead1234beef"}\n')
    for rel in (X, "execution/okx_inquiry.py", TRANSPORT):
        assert _tr_hits(rel, f'P = "{OKX_ORDER_PATH}"\n'), rel
    assert not _tr_hits("execution/okx_inquiry.py", 'P = "/api/v5/trade/orders-pending"\n')
    assert _token_hits(X, 'T = "TTTC8434R"\nP = "/v1/orders/open"\nK = "/uapi/x"\n') and not _token_hits(X, "x = 1\n")
    files = _sources()
    assert KIS_FILE in files and TRANSPORT in files, sorted(files)
    hits = [h for rel, src in files.items() for h in _tr_hits(rel, src)]
    assert not hits, hits


def test_transport_is_the_only_path():
    """E36: no execution module but transport.py can reach requests, _send, the signing helpers, the hosts or a
    credential name, and nothing rebinds a seam or an allowlist from outside (contract 0.5)."""
    for src in ("from execution.transport import _send\n", "from execution import transport\n",
                "import execution.transport\n", "import execution.transport as t\n",
                "from execution.transport import request as r\n", "from execution.transport import HOSTS\n",
                "from . import transport\n", "from execution.kis_inquiry import keys\n",
                "from execution.poll import transport\n", "x = execution.transport.Answer\n",
                "transport._send(m, u)\n", 'request("kis", "POST", p)\n', 'request("kis", m, p)\n',
                "request(*a)\n", 'request(*a, "GET")\n', "r = request\n", "from execution import keys\n",
                "import execution.keys\n", "from execution.keys import KeyMissing\n",
                'keys.read(("KIS_APP_KEY",))\n', 'n = "KIS_APP_SECRET"\n', "# reads OKX_API_PASSPHRASE\n",
                "requests.get(u)\n", "x.requests.Session()\n", 'HOSTS["kis"]\n', "c = CREDENTIALS\n",
                "m.keys.read(n)\n", "f = m.request\n", "c = poll.transport\n", "s = transport._sleep\n",
                "kis_inquiry.ENDPOINTS = s\n", "t._clock = c\n", "t.x += 1\n", "t.x: int = 1\n", "del t.x\n",
                "for t.x in y:\n    pass\n", "with f() as t.x:\n    pass\n", "a, t.x = 1, 2\n",
                "[0 for t.x in y]\n", "setattr(t, n, v)\n", "delattr(t, n)\n", "f = setattr\n", "getattr(t, n)\n",
                'getattr(request, "__globals__")\n', 'getattr(t, "_send")\n', 'getattr(m, "keys")\n',
                'getattr(m, "HOSTS")\n', "g = getattr\n", "vars(t)\n", "globals()\n", "request.__globals__\n",
                "f.__code__\n", "m.__dict__\n", "b = __builtins__\n", "m = sys.modules.get(n)\n",
                "def f():\n    global _send\n", "session.trust_env = False\n", "def f(self):\n    self.x = 1\n",
                'object.__setattr__(self, "a", 1)\n', "def f(self):\n    object.__setattr__(self, 'a', 1)\n",
                "def __post_init__(self):\n    object.__setattr__(t, '_send', f)\n",
                "exc.__traceback__.tb_next.tb_frame.f_globals['_send'] = f\n", "g = sys._getframe(1).f_globals\n",
                'getattr(fr, "f_globals")\n', 'd["_send"] = f\n',
                'g = object.__getattribute__(f, "__glo" + "bals__")\n',
                'kis_inquiry.__getstate__()["ENDPOINTS"] = e\n', "b = len.__self__\n"):
        assert _path_hits(X, src), src
    reads = ("from execution import keys\nACCOUNT_NAMES = ('A', 'B')\n"
             "def snapshot():\n    a = keys.read(ACCOUNT_NAMES)\n")
    assert not _path_hits(KIS_FILE, reads), _path_hits(KIS_FILE, reads)
    for extra in ("    b = keys.read(ACCOUNT_NAMES)\n", '    keys._parse("x")\n', "    k = keys\n",
                  "    keys.read(ACCOUNT_NAMES[:1])\n"):
        assert _path_hits(KIS_FILE, reads + extra), extra
    assert _path_hits(KIS_FILE, "from execution import keys as k\n")
    assert _path_hits(KIS_FILE, "from execution.keys import read\n")
    clock = "from execution import transport\ndef main():\n    transport._clock = lambda: now()\n"
    assert not _path_hits(POLL, clock), _path_hits(POLL, clock)
    for bad in ("from execution import transport\ntransport._clock = c\n",
                "from execution import transport\ndef main():\n    transport._send = f\n",
                "from execution import transport\ndef main():\n    e = transport.InquiryError\n",
                "from execution import transport as t\ndef main():\n    t._clock = c\n"):
        assert _path_hits(POLL, bad), bad
    send = "def _send(m, u):\n    with S() as session:\n        session.trust_env = False\n"
    assert not _path_hits(TRANSPORT, send)
    assert _path_hits(TRANSPORT, "def _other(m, u):\n    with S() as session:\n        session.trust_env = False\n")
    assert _path_hits(TRANSPORT, "def f():\n    global _clock\n")
    assert not _path_hits(TRANSPORT, "def f():\n    global _next_issue_at, _okx_offset_s\n")
    for ok in ('x = getattr(y, "name")\n', "from execution.transport import request, Answer, KeyMissing\n"
               'a = request("upbit", "GET", "/v1/accounts")\n',
               "class E(Exception):\n    def __init__(self, n):\n        super().__init__(n)\n        self.name = n\n",
               "class S:\n    def __post_init__(self):\n        object.__setattr__(self, 'h', 1)\n",
               "from execution import snapshot\nfrom execution.snapshot import Snapshot\nd = {}\nd['k'] = 1\n",
               "names = sorted(d.keys())\n", '"""Ten requests a second at most."""\n',
               "frames = traceback.extract_tb(exc.__traceback__)\n"):                  # Task 12's crash line
        assert not _path_hits(X, ok), ok
    files = _sources()
    shipped = {TRANSPORT, KIS_FILE, UPBIT_FILE, "execution/okx_inquiry.py", "execution/keys.py"}
    assert shipped <= set(files), sorted(files)
    hits = [h for rel, src in files.items() for h in _path_hits(rel, src)]
    assert not hits, hits


def test_send_is_pinned():
    """E1R2-11: `_send` is exactly the function of contract section 6 (one requests.Session() with trust_env off,
    one session.request(..., allow_redirects=False), nothing else), compared as ast.unparse text, and transport.py
    uses `requests` in no other way than its import, that Session and requests.exceptions.ConnectionError."""
    assert _send_def(SEND_TEMPLATE) == SEND_SOURCE
    variants = {
        "no trust_env line": ("        session.trust_env = False                  # no proxy, CA bundle or .netrc\n",
                              ""),
        "trust_env True": ("trust_env = False", "trust_env = True"),
        "redirects on": ("allow_redirects=False", "allow_redirects=True"),
        "verify off": ("allow_redirects=False)", "allow_redirects=False, verify=False)"),
        "proxies": ("allow_redirects=False)", "allow_redirects=False, proxies=p)"),
        "auth": ("allow_redirects=False)", "allow_redirects=False, auth=a)"),
        "hooks": ("allow_redirects=False)", "allow_redirects=False, hooks=h)"),
        "stream": ("allow_redirects=False)", "allow_redirects=False, stream=True)"),
        "cert": ("allow_redirects=False)", "allow_redirects=False, cert=c)"),
        "requests.request": ("session.request(", "requests.request("),
        "a docstring": ("    with requests", '    """Send."""\n    with requests'),
        "a second send": ("resp.content\n", "resp.content\n\n_send = print\n"),
    }
    for label, (old, new) in variants.items():
        src = SEND_TEMPLATE.replace(old, new, 1)
        assert src != SEND_TEMPLATE and _send_def(src) != SEND_SOURCE, label
    assert _send_def("import requests\n") is None
    for src in ("from requests import Session\n", "import requests as r\n", "import requests.adapters\n",
                "import requests\ndef f():\n    return requests.get(u)\n",
                "import requests\ndef f():\n    return requests.Session()\n", "import requests\nx = requests\n"):
        assert _requests_hits(src), src
    assert not _requests_hits(SEND_TEMPLATE + "E = requests.exceptions.ConnectionError\n")
    src = (EXECUTION / "transport.py").read_text(encoding="utf-8")
    assert _send_def(src) == SEND_SOURCE, _send_def(src)
    assert not _requests_hits(src), _requests_hits(src)
```

Check the end of the file from the repo root; it must print `True False False` (the block ends the file, no blank
line after it, no CR anywhere):

```bash
.venv/Scripts/python.exe -c "import pathlib; b = pathlib.Path('tests/execution_guards.py').read_bytes(); print(b.endswith(b'    assert not _requests_hits(src), _requests_hits(src)\n'), b.endswith(b'\n\n'), b'\r' in b)"
```

The appended block uses `ast`, `re` and `types`, which Task 1's module already imports, and Task 1's `ROOT`,
`EXECUTION`, `X`, `TRANSPORT`, `CG` and `_sources()`.

- [ ] **Step 2: Run to verify it fails**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_keys/; echo "exit $?"
```

Expected (a traceback on stderr, then):

```
FAIL execution_keys/import ImportError: cannot import name 'keys' from 'execution' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\execution\__init__.py)

0/1 passed, 1 failed, 0 not run
exit 1
```

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_transport/; echo "exit $?"
```

Expected: the same single line for `execution_transport/import` (its module imports `execution.keys` first), then
`0/1 passed, 1 failed, 0 not run` and `exit 1`.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/; echo "exit $?"
```

Expected: all 24 tests FAIL with the same `ImportError: cannot import name 'keys' from 'execution' (...)`, raised
by `isolated()`'s new import before any test body runs (Task 1's 18 tests included: the wrapper is shared), then
`0/24 passed, 24 failed, 0 not run` and `exit 1`. A test that fails here for any other reason means a copy error in
Step 1: fix the copy, never a control.

- [ ] **Step 3: Implement**

1. Create `execution/keys.py` (LF) with exactly:

```python
"""The E1 key reader (E1 spec 4; contract section 5; E2, E27): named values from the repo-root .env, read by a small
standard-library parser. A name present in the environment decides alone, so a blank or <placeholder> value there is
missing even when .env holds that name (the KEYLESS prefix relies on it). Values go back only to the caller; nothing
here logs, prints or stores one, and an error names the key, never its value."""
from __future__ import annotations

import os
import re
from collections.abc import Sequence
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"     # seam: the suite points it at a missing temp file
_NAME = re.compile(r"[A-Z][A-Z0-9_]*")


class KeyMissing(Exception):
    """A named key is not set; the message names it and never holds a value."""

    def __init__(self, name: str):
        super().__init__(f"{name} is not set in .env or the environment")
        self.name = name


def read(names: Sequence[str]) -> tuple[str, ...]:
    """The values of `names`, in order. A name in os.environ decides alone (blank or <placeholder> is missing); any
    other name comes from .env, which is read at most once per call and only then (a missing file is empty).
    KeyMissing names the first missing name; anything but a sequence of upper-case variable names is
    ValueError("keys: bad name"), raised before anything is read."""
    if isinstance(names, str):
        raise ValueError("keys: bad name")
    names = tuple(names)
    if not all(isinstance(n, str) and _NAME.fullmatch(n) for n in names):
        raise ValueError("keys: bad name")
    values, file = [], None
    for name in names:
        if name in os.environ:
            value = _clean(os.environ[name])
        else:
            if file is None:
                try:
                    text = _ENV_FILE.read_text(encoding="utf-8-sig")     # utf-8-sig: a Notepad BOM (E27)
                except FileNotFoundError:
                    text = ""
                file = _parse(text)
            value = _clean(file.get(name, ""))
        if not value:
            raise KeyMissing(name)
        values.append(value)
    return tuple(values)


def _parse(text: str) -> dict[str, str]:
    """KEY=VALUE lines: blank lines and # comments skipped, a leading `export ` dropped, a quoted value ends at its
    matching quote (anything after it is ignored), an unquoted one at the first whitespace followed by # (as
    python-dotenv, which config.py applies to the same file); no expansion; a later line wins."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, sep, value = line.partition("=")
        if not sep:
            continue
        value = value.strip()
        if value[:1] in ("'", '"'):
            value = value[1:].partition(value[0])[0]
        else:
            value = re.split(r"\s#", value, maxsplit=1)[0].rstrip()
        out[key.strip()] = value
    return out


def _clean(value: str) -> str:
    """`value` stripped; an unedited <placeholder> reads as "" (missing), as config._clean reads it."""
    value = value.strip()
    return "" if value.startswith("<") and value.endswith(">") else value
```

2. Create `execution/transport.py` (LF) with exactly (Task 3 replaces the last line of `request` and adds the
sending half; `_send` is final and pinned by `test_send_is_pinned`):

```python
"""The only network path of execution/ (E1 spec 5 "The choke point"; contract section 6; E3, E10, E12, E13, E36).

`request` refuses, before any key is read, everything outside the venue's frozen allowlist, which it reads at call
time from the venue module (E10): an unknown venue, a (method, path) pair not listed, any method but GET except the
one KIS token POST, a KIS inquiry without its pinned TR id ending in R, a TR id anywhere else, a parameter that is
not plain, and a signed OKX request without a known clock offset within 25 s. Only then are credentials read and one
request sent through the seam `_send`, which ignores the environment's proxy, CA-bundle and .netrc settings and
never follows a redirect (E1R2-11). The hosts are the real ones; no mock host is listed. Nothing here logs, prints or
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

HOSTS = MappingProxyType({"kis": "https://openapi.koreainvestment.com:9443",
                          "upbit": "https://api.upbit.com",
                          "okx": "https://www.okx.com"})
CREDENTIALS = MappingProxyType({"kis": ("KIS_APP_KEY", "KIS_APP_SECRET"),
                                "upbit": ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"),
                                "okx": ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")})
KIS_TOKEN_PATH = "/oauth2/tokenP"
TIMEOUT_S = 10.0
RETRY_AFTER_S = 2.0
PACE_S = 0.2                          # sleep after every attempt: at most 5 requests a second
OKX_SKEW_LIMIT_S = 25.0
TOKEN_REUSE_MARGIN_S = 120.0
TOKEN_MIN_GAP_S = 70.0
TOKEN_REISSUE_BLOCK_S = 6 * 3600.0    # KIS returned a token it had called bad: issue nothing for 6 hours
KIS_TOKEN_CODES = frozenset({"EGW00121", "EGW00122", "EGW00123"})
AUTH_CODES = MappingProxyType({
    "kis": frozenset({"EGW00103", "EGW00105", "EGW00205", "EGW00206", "EGW00304"}),
    "upbit": frozenset({"invalid_query_payload", "jwt_verification", "expired_access_key", "nonce_used",
                        "no_authorization_ip", "no_authorization_token", "out_of_scope"}),
    "okx": frozenset({"50030", "50035", "50100", "50101", "50103", "50104", "50105", "50106", "50107", "50110",
                      "50111", "50112", "50113", "50114", "50119", "50120", "50121", "50123"})})
_KEY = re.compile(r"[A-Za-z0-9_\[\]]+")


class InquiryRefused(Exception):
    """A request E1 may not make, refused before any key is read (spec 5 steps 1-3). `reason` names the venue,
    method, path, TR id or parameter key, never a value."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class InquiryError(Exception):
    """The venue or the network failed after the checks; the text holds names, paths and venue codes only."""


class AuthError(InquiryError):
    """An authentication or permission answer (KEY_HEALTH)."""


@dataclass(frozen=True, kw_only=True)
class Answer:
    """One checked answer (E3, E39)."""
    body: object = field(repr=False)  # the parsed JSON (a token, balances or addresses: never in a repr)
    server_utc: datetime | None       # from the Date header, aware UTC; None when absent or unreadable
    received_utc: datetime            # _clock() right after _send returned (E39)
    sha256: str                       # hex over the raw body bytes


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


def require_keys(venue: str) -> None:
    """KeyMissing (names only) unless every credential of `venue` is set; the values are read and dropped, never
    returned (E32)."""
    keys.read(CREDENTIALS[venue])


def _send(method, url, *, headers, params, json_body, timeout):
    with requests.Session() as session:
        session.trust_env = False                  # no proxy, CA bundle or .netrc from the environment
        resp = session.request(method, url, headers=headers, params=params, json=json_body, timeout=timeout,
                               allow_redirects=False)
        return resp.status_code, resp.headers, resp.content


_sleep = time.sleep                   # seam: pacing and retry wait through it; it reads no clock


def _clock() -> datetime:
    """The send-time clock (E11): poll.main binds one; until then nothing in E1 reads the time."""
    raise RuntimeError("transport: no clock; poll.main sets one")


_next_issue_at: float | None = None   # epoch seconds before which this process issues no KIS token
_okx_offset_s: float | None = None    # OKX server time minus the PC clock at the last public/time answer
_bad_tokens: set[str] = set()         # KIS tokens the venue called invalid or expired in this process


def _rules(venue: str) -> tuple[frozenset, frozenset, frozenset]:
    """(ENDPOINTS, TR_IDS or frozenset(), PUBLIC) of `venue`, read from its module at call time (E10). The venue
    modules import this one, so the import waits until a request is made."""
    from execution import kis_inquiry, okx_inquiry, upbit_inquiry
    module = {"kis": kis_inquiry, "upbit": upbit_inquiry, "okx": okx_inquiry}[venue]
    return module.ENDPOINTS, (kis_inquiry.TR_IDS if module is kis_inquiry else frozenset()), module.PUBLIC


def _query(venue: str, path: str, params) -> str:
    """The query string, built once and sent as built (E12): ordered (key, value) tuples joined as
    key=quote(value, safe=","). A key must fully match _KEY (`states[]` included) and a value must be a str; for a
    signed Upbit or OKX request a value that quoting would change is refused, so the hashed or signed string is
    byte for byte the one sent. A KIS value is quoted (PDNO=% goes out as %25). Anything but a sequence of 2-tuples
    with a str key is refused with a fixed text, so a stray value never reaches the reason."""
    if params is None:
        return ""
    signed = venue != "kis" and path not in _rules(venue)[2]
    parts = []
    for pair in params:
        if not (isinstance(pair, tuple) and len(pair) == 2 and isinstance(pair[0], str)):
            raise InquiryRefused(f"{venue}: parameters must be (key, value) pairs")
        key, value = pair
        if not (_KEY.fullmatch(key) and isinstance(value, str)) or (
                signed and quote(value, safe=",") != value):
            raise InquiryRefused(f"{venue}: parameter {key!r} is not plain")
        parts.append(f"{key}={quote(value, safe=',')}")
    return "&".join(parts)
```

3. Create `execution/kis_inquiry.py` (LF) with exactly (contract section 7; no `/uapi/` text and no TR id in the
docstring):

```python
"""KIS read-only inquiry (E1 spec 5, the KIS table; contract section 7; E10, E14): the endpoint allowlist, the one
pinned TR id per inquiry path (each ends in R) and the names of the two account-number keys. transport.request reads
ENDPOINTS, TR_IDS and PUBLIC at call time. This is the only file in execution/ that may name the KIS account fields
or a KIS trading-domain path; tests/execution_guards.py pins every path and TR id written here. Task 5 adds the
snapshot."""
from __future__ import annotations

ENDPOINTS = frozenset({
    ("POST", "/oauth2/tokenP"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-balance"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"),
    ("GET", "/uapi/domestic-stock/v1/trading/inquire-account-balance"),
    ("GET", "/uapi/domestic-stock/v1/trading/intgr-margin"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-balance"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-nccs"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-ccnl"),
    ("GET", "/uapi/overseas-stock/v1/trading/inquire-present-balance"),
})
TR_IDS = frozenset({
    ("/uapi/domestic-stock/v1/trading/inquire-balance", "TTTC8434R"),
    ("/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl", "TTTC0084R"),
    ("/uapi/domestic-stock/v1/trading/inquire-daily-ccld", "TTTC0081R"),
    ("/uapi/domestic-stock/v1/trading/inquire-account-balance", "CTRP6548R"),
    ("/uapi/domestic-stock/v1/trading/intgr-margin", "TTTC0869R"),
    ("/uapi/overseas-stock/v1/trading/inquire-balance", "TTTS3012R"),
    ("/uapi/overseas-stock/v1/trading/inquire-nccs", "TTTS3018R"),
    ("/uapi/overseas-stock/v1/trading/inquire-ccnl", "TTTS3035R"),
    ("/uapi/overseas-stock/v1/trading/inquire-present-balance", "CTRP6504R"),
})
PUBLIC = frozenset()
ACCOUNT_NAMES = ("KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")
```

4. Create `execution/upbit_inquiry.py` (LF) with exactly (no Upbit order or withdrawal path in the docstring):

```python
"""Upbit read-only inquiry (E1 spec 5, the Upbit table; contract section 7; E10, E22): the endpoint allowlist and its
one public path. transport.request reads ENDPOINTS and PUBLIC at call time. This is the only file in execution/ that
may name the Upbit order and withdrawal inquiry paths, and tests/execution_guards.py holds each of them to the four
exact paths listed here. Task 6 adds the snapshot."""
from __future__ import annotations

ENDPOINTS = frozenset({
    ("GET", "/v1/accounts"), ("GET", "/v1/orders/open"), ("GET", "/v1/orders/closed"), ("GET", "/v1/withdraws"),
    ("GET", "/v1/withdraws/coin_addresses"), ("GET", "/v1/deposits"), ("GET", "/v1/api_keys"),
    ("GET", "/v1/status/wallet"), ("GET", "/v1/ticker"),
})
PUBLIC = frozenset({"/v1/ticker"})
```

5. Create `execution/okx_inquiry.py` (LF) with exactly (the single-order trade path is named in prose, never written):

```python
"""OKX read-only inquiry (E1 spec 5, the OKX table; contract section 7; E10, E25): the endpoint allowlist, its two
public paths and the algo order types, read one per call. transport.request reads ENDPOINTS and PUBLIC at call time.
The single-order trade path is not listed: the same path also serves the order POST. Task 7 adds the
self-check and the snapshot."""
from __future__ import annotations

ENDPOINTS = frozenset({
    ("GET", "/api/v5/account/config"), ("GET", "/api/v5/account/balance"), ("GET", "/api/v5/account/positions"),
    ("GET", "/api/v5/asset/balances"), ("GET", "/api/v5/asset/asset-valuation"),
    ("GET", "/api/v5/finance/savings/balance"), ("GET", "/api/v5/finance/flexible-loan/loan-info"),
    ("GET", "/api/v5/trade/orders-pending"), ("GET", "/api/v5/trade/orders-algo-pending"),
    ("GET", "/api/v5/trade/fills"), ("GET", "/api/v5/asset/deposit-history"),
    ("GET", "/api/v5/asset/withdrawal-history"), ("GET", "/api/v5/public/time"), ("GET", "/api/v5/market/ticker"),
})
PUBLIC = frozenset({"/api/v5/public/time", "/api/v5/market/ticker"})
ALGO_TYPES = ("conditional", "oco", "trigger", "move_order_stop", "iceberg", "twap", "chase")
```

- [ ] **Step 4: Run to verify it passes**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_keys/; echo "exit $?"
```

Expected: 9 PASS lines, then `9/9 passed, 0 failed, 0 not run` and `exit 0`.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_transport/; echo "exit $?"
```

Expected: 11 PASS lines, then `11/11 passed, 0 failed, 0 not run` and `exit 0`.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/; echo "exit $?"
```

Expected (`exit 0`; the runner sorts by name):

```
PASS execution_guards/test_a_stray_send_fails_a_passing_test
PASS execution_guards/test_acting_prefix_covers_execution
PASS execution_guards/test_aggregator_skips_missing_and_isolates_broken_modules
PASS execution_guards/test_allowlists_are_pinned
PASS execution_guards/test_every_write_goes_through_checked_target
PASS execution_guards/test_harness_flags_a_change_to_the_real_homes
PASS execution_guards/test_imports_stay_on_the_allowlist
PASS execution_guards/test_init_is_empty_and_main_blocks_are_one_line
PASS execution_guards/test_kis_and_upbit_exceptions_are_file_exact
PASS execution_guards/test_kis_strings_are_exact
PASS execution_guards/test_no_def_named_transfer_withdraw_or_deposit_address
PASS execution_guards/test_no_dynamic_import
PASS execution_guards/test_no_order_tr_anywhere
PASS execution_guards/test_no_raw_banned_words
PASS execution_guards/test_no_wall_clock_outside_poll_main
PASS execution_guards/test_only_evidence_names_evidence_path
PASS execution_guards/test_only_transport_send_calls_requests_request
PASS execution_guards/test_runtime_py_scans_execution
PASS execution_guards/test_send_is_pinned
PASS execution_guards/test_suite_is_registered_in_run_all_and_readme
PASS execution_guards/test_suite_runs_hermetic_in_a_temp_home_with_seams
PASS execution_guards/test_tests_start_no_process
PASS execution_guards/test_transport_is_the_only_path
PASS execution_guards/test_upbit_strings_are_exact

24/24 passed, 0 failed, 0 not run
exit 0
```

A guard failure names the file and the text: fix `execution/`, never the guard or a control.

T-RO-01 alone on the real tree (it now reads the five new files, with the file-exact exceptions of Task 1):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; t(); u(); print('T-RO-01 ok')"
```

Expected: `T-RO-01 ok`.

The execution suite through the real runner (KEYLESS; restore the results file; `timeout: 300000`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite execution; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

Expected last lines: `44/44 passed, 0 failed, 0 not run; ...qa\acceptance_results.json` and `exit 0`.

The cockpit suite, whose test_08, test_09, test_16 and test_18 now read the venue constants (KEYLESS; restore;
`timeout: 300000`):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

Expected last lines: `47/47 passed, 0 failed, 0 not run; ...qa\acceptance_results.json` and `exit 0`, exactly Task
1's Step 4b cockpit line. Any other count is a drift ruling recorded in the ledger, not a fix.

- [ ] **Step 5: Commit**

```bash
git status --short
```

Expected exactly these entries, in any order (`qa/acceptance_results.json` must NOT be among them):

```
 M tests/execution_fixtures.py
 M tests/execution_guards.py
?? execution/keys.py
?? execution/kis_inquiry.py
?? execution/okx_inquiry.py
?? execution/transport.py
?? execution/upbit_inquiry.py
?? tests/execution_keys.py
?? tests/execution_transport.py
```

plus ` M docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` if this task recorded a drift
ruling.

The stat comparison cannot see a CRLF or a BOM in a NEW file, so check the seven new files directly first:

```bash
.venv/Scripts/python.exe -c "import pathlib; [print(p, pathlib.Path(p).read_bytes().count(b'\r'), pathlib.Path(p).read_bytes()[:3] == b'\xef\xbb\xbf') for p in ('execution/keys.py', 'execution/transport.py', 'execution/kis_inquiry.py', 'execution/upbit_inquiry.py', 'execution/okx_inquiry.py', 'tests/execution_keys.py', 'tests/execution_transport.py')]"
```

Expected, one line per file, each ending `0 False` (no carriage return, no BOM). Otherwise rewrite that file with LF
endings and no BOM before staging.

If this task recorded a drift ruling, first `git add docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`.
Then:

```bash
git add execution/keys.py execution/transport.py execution/kis_inquiry.py execution/upbit_inquiry.py execution/okx_inquiry.py tests/execution_keys.py tests/execution_transport.py tests/execution_fixtures.py tests/execution_guards.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

The two stat outputs must be identical, with these counts (git scales the +/- bars to the terminal; compare the
counts; a drift ruling recorded in the ledger adds the ledger to the list):

```
 execution/keys.py            |   78 +
 execution/kis_inquiry.py     |   32 +
 execution/okx_inquiry.py     |   16 +
 execution/transport.py       |  156 +
 execution/upbit_inquiry.py   |   12 +
 tests/execution_fixtures.py  |   51 +-
 tests/execution_guards.py    |  505 +
 tests/execution_keys.py      |  171 +
 tests/execution_transport.py |  398 +
 9 files changed, 1413 insertions(+), 6 deletions(-)
```

Then commit. In the trailer, replace `<the committing model>` with the name of the model that writes this commit,
for example `Claude Sonnet 5.5` or `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "feat(execution): key reader, transport checks and the pinned venue allowlists" -m "Adds execution/keys.py, the checking half of execution/transport.py (refusals before any key is read, the pinned trust_env-off _send), the three venue allowlists, the wrapper's transport seams and their tests and guards." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

Expected: the new commit on `e1-account-inquiry`, and `git status --short` prints nothing.
