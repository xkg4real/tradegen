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
