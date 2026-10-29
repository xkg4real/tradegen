"""Fixtures for the compliance suite (compliance plan, contract section 3). Task 1 adds `temp_home`; later tasks add
the shipped-table, context, intent, owner-log and store fixtures."""
from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterator

from core import isolation


@contextlib.contextmanager
def temp_home() -> Iterator[Path]:
    """A fresh TRADEGEN_HOME for one test; the previous value comes back and the dir is removed afterwards. The
    state-root link memo is cleared on the way in and out, so no verdict leaks between tests."""
    home = Path(tempfile.mkdtemp(prefix="tradegen_home_"))
    saved = os.environ.get("TRADEGEN_HOME")
    os.environ["TRADEGEN_HOME"] = str(home)
    isolation._LINK_SCAN.clear()
    try:
        yield home
    finally:
        if saved is None:
            os.environ.pop("TRADEGEN_HOME", None)
        else:
            os.environ["TRADEGEN_HOME"] = saved
        isolation._LINK_SCAN.clear()
        shutil.rmtree(home, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Task 6: the shipped drafts, approved states, sealed contexts and intents (contract 5.4)
# --------------------------------------------------------------------------- #
import functools as _functools  # noqa: E402
from datetime import date as _date  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_REPO = _Path(__file__).resolve().parents[1]
_SHIPPED = {"rules": _REPO / "core" / "compliance" / "kr_rules.yaml",
            "instruments": _REPO / "core" / "compliance" / "instruments.yaml",
            "venues": _REPO / "core" / "odds" / "venues.yaml"}


def shipped_bytes(kind: str) -> bytes:
    """Bytes of the shipped draft: "rules", "instruments" or "venues"."""
    return _SHIPPED[kind].read_bytes()


@_functools.lru_cache(maxsize=32, typed=True)       # typed: seq=True must not reuse the entry for seq=1
def _approved(rules_raw: bytes, instruments_raw: bytes, venues_raw: bytes, seq: int, history: tuple):
    from core.compliance import rules as R
    return R.approved_state(rules_raw, instruments_raw, venues_raw, seq=seq, history_raws=history)


def approved(rules=None, instruments=None, venues=None, *, seq=3, history=()):
    """rules.approved_state over the given bytes (the shipped drafts by default); cached, so treat it as frozen."""
    return _approved(shipped_bytes("rules") if rules is None else rules,
                     shipped_bytes("instruments") if instruments is None else instruments,
                     shipped_bytes("venues") if venues is None else venues, seq, tuple(history))


def ctx(**overrides):
    """A sealed Context for gate tests (contract 5.4); any field can be overridden."""
    from core.compliance import model as M
    fields = dict(
        date=_date(2026, 10, 23), snapshot=None,
        owner=M.OwnerState(status="OK", head=(10, "a" * 64), caps={"okx_equity_share": 0.10},
                           limits={"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0},
                           flags=frozenset({"age_of_majority"}), fingerprint="SHA256:test"),
        code_hash="c" * 64, code_signed=True, session=M.SessionState(session_id="S1", armed=True),
        equity_krw=1_000_000.0, holdings={}, shorts={}, exposure={})
    fields.update(overrides)
    if "active" not in fields:
        fields["active"] = approved()
    return M.seal_context(**fields)


def intent(**overrides):
    """An Upbit BTC buy for KRW, 0.001 BTC at KRW 50,000; any field can be overridden."""
    from core.compliance import model as M
    fields = dict(venue="upbit", symbol="BTC", counter_symbol="KRW", asset="crypto_coin", multiple=1.0,
                  action="buy", quantity=0.001, notional_krw=50_000.0)
    fields.update(overrides)
    return M.Intent(**fields)


# -- owner log fixtures (Task 11) --------------------------------------------------------------------------------
# Never `from tests.compliance_fixtures import test_key` in a test module: the harness would collect it as a test.
_OWNER_FIXTURES: dict = {}


def test_key():
    """The fixed test signing key (seed bytes 0..31), cached. NotRun PENDING until cryptography is installed."""
    import importlib.util
    from tests.notrun import NotRun
    if "key" not in _OWNER_FIXTURES:
        if importlib.util.find_spec("cryptography") is None:
            raise NotRun("PENDING: cryptography not installed (Task 10)")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        _OWNER_FIXTURES["key"] = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    return _OWNER_FIXTURES["key"]


def signed_entry(key, seq, prev_sha256, kind, data, utc="2026-10-23T00:00:00Z") -> bytes:
    """One owner-log line in the spec 6.4 format, built independently of owner.py; signed by `key` unless None."""
    import base64
    from core.compliance import model
    body = {"seq": seq, "prev_sha256": prev_sha256, "utc": utc, "kind": kind, "data": data}
    row = model.sha256_hex(model.canonical_json(body))
    line = {**body, "row_sha256": row}
    if key is not None:
        line["sig"] = base64.b64encode(key.sign(b"tradegen-owner-log/1\n" + row.encode("ascii"))).decode("ascii")
    return (model.canonical_json(line) + "\n").encode("utf-8")


def write_log(home: "Path", entries: "list[tuple[str, dict]]", key=None) -> "list[bytes]":
    """Write `entries` as home/compliance/owner.jsonl chained from seq 1: owner kinds signed with `key` (default
    test_key()), system kinds unsigned. Returns the lines written."""
    import json
    lines, prev = [], "0" * 64
    for seq, (kind, data) in enumerate(entries, start=1):
        signer = None if kind in ("system_halt", "system_disarm") else (key if key is not None else test_key())
        lines.append(signed_entry(signer, seq, prev, kind, data))
        prev = json.loads(lines[-1])["row_sha256"]
    path = home / "compliance" / "owner.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(lines))
    return lines


def write_pubkey(path: "Path", key=None) -> None:
    """Write the PEM SubjectPublicKeyInfo of `key` (default test_key()) to `path`."""
    key = key if key is not None else test_key()
    from cryptography.hazmat.primitives import serialization
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                   serialization.PublicFormat.SubjectPublicKeyInfo))


# -- approved store fixture (Task 13) ----------------------------------------------------------------------------
def store_blob(home: Path, kind: str, raw: bytes, anchor: tuple[int, str]) -> str:
    """owner.store_put into the temp home `home` (refused for any other home); returns the blob's sha256."""
    from core.compliance import owner
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
    if not path.is_relative_to(home):
        raise AssertionError(f"owner_key: {path} is outside the temp home {home}")
    if not path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise AssertionError(f"owner_key: {path} is outside the temp dir {tempfile.gettempdir()}")
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
