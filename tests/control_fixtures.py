"""Never-live seams for E2/E3 acceptance tests; no runtime import at module scope."""
from __future__ import annotations

import contextlib
from pathlib import Path

STRAYS: list[str] = []
REAL_SEND = None


class Refused(RuntimeError):
    """A default trading HTTP path was used inside a test."""


def _refuse(*args, **kwargs):
    # Do not retain URLs, arguments or headers: they can carry account fields.
    STRAYS.append("unmocked trading HTTP")
    raise Refused("unmocked trading HTTP")


@contextlib.contextmanager
def isolated(home: Path):
    """E1's wrapper supplies KEYLESS keys/temp home; block both E3 seam and raw requests.

    Individual protocol tests may replace these with their in-memory stubs and
    must restore them. A swallowed unmocked call still fails the enclosing test.
    """
    import requests
    from execution_orders import transport
    from execution_control import capability, session

    global REAL_SEND
    previous = list(STRAYS)
    STRAYS.clear()
    saved_send = transport._send
    saved_real_send = REAL_SEND
    REAL_SEND = REAL_SEND or saved_send
    saved_request = requests.sessions.Session.request
    saved_capabilities = dict(capability._ISSUED)
    saved_sessions = dict(session._PREPARED)
    transport._send = _refuse
    requests.sessions.Session.request = _refuse
    capability._ISSUED.clear()
    session._PREPARED.clear()
    try:
        yield
        assert not STRAYS, "test swallowed an unmocked trading HTTP attempt"
    finally:
        transport._send = saved_send
        REAL_SEND = saved_real_send
        requests.sessions.Session.request = saved_request
        capability._ISSUED.clear()
        capability._ISSUED.update(saved_capabilities)
        session._PREPARED.clear()
        session._PREPARED.update(saved_sessions)
        STRAYS[:] = previous
