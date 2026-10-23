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
