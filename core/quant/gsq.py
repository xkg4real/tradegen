"""gs_quant integration, in two tiers.

**Offline tier (always on when the package is installed).** gs_quant's
`timeseries` library runs without any session, and `core.quant.risk` already
routes realized volatility and max drawdown through it. This module reports
that status.

**Session tier (optional).** With `GS_CLIENT_ID` / `GS_CLIENT_SECRET`
configured, `connect()` opens a `GsSession` against the GS Marquee API, which
unlocks instrument resolution and pricing (IRSwap par rates, portfolio risk
measures). Those credentials come from a GS developer account; without them
every session-tier function reports exactly why it is unavailable instead of
raising an ImportError three screens later.

Nothing here is imported at app startup — the pages import lazily, so a broken
gs_quant install degrades one status card, not the application.
"""
from __future__ import annotations

from dataclasses import dataclass

import config

try:
    import gs_quant
    _INSTALLED = True
    _VERSION = getattr(gs_quant, "__version__", "?")
except Exception:                                     # pragma: no cover
    _INSTALLED = False
    _VERSION = ""


@dataclass(frozen=True)
class GsStatus:
    installed: bool
    version: str
    offline_analytics: bool           # timeseries usable without a session
    credentials_present: bool
    session_active: bool
    detail: str


_session_state = {"active": False, "detail": ""}


def status() -> GsStatus:
    offline = False
    if _INSTALLED:
        try:
            import gs_quant.timeseries  # noqa: F401
            offline = True
        except Exception:
            offline = False
    creds = bool(config.gs_client_id() and config.gs_client_secret())
    detail = ""
    if not _INSTALLED:
        detail = "gs-quant is not installed (pip install gs-quant)."
    elif not creds:
        detail = ("Offline analytics active. Set GS_CLIENT_ID and "
                  "GS_CLIENT_SECRET to enable Marquee pricing.")
    elif not _session_state["active"]:
        detail = _session_state["detail"] or "Credentials present; session not opened yet."
    else:
        detail = "Marquee session active."
    return GsStatus(installed=_INSTALLED, version=_VERSION,
                    offline_analytics=offline, credentials_present=creds,
                    session_active=_session_state["active"], detail=detail)


def connect() -> GsStatus:
    """Open a GsSession with the configured OAuth credentials. Safe to call
    repeatedly; failure is recorded in the status detail, never raised."""
    if not _INSTALLED:
        return status()
    cid, secret = config.gs_client_id(), config.gs_client_secret()
    if not (cid and secret):
        return status()
    try:
        from gs_quant.session import Environment, GsSession
        GsSession.use(Environment.PROD, client_id=cid, client_secret=secret,
                      scopes=("run_analytics",))
        _session_state.update(active=True, detail="")
    except Exception as exc:
        _session_state.update(active=False,
                              detail=f"Session failed: {type(exc).__name__}: {exc}")
    return status()


def price_example_swap(tenor: str = "10y", ccy: str = "USD") -> dict:
    """Resolve a par payer swap as a live smoke test of the session tier.
    Returns a dict with either the resolved fixed rate or the reason it
    could not be produced."""
    st = status()
    if not st.session_active:
        return {"ok": False, "detail": st.detail}
    try:
        from gs_quant.instrument import IRSwap
        swap = IRSwap("Pay", tenor, ccy)
        swap.resolve()
        return {"ok": True, "fixed_rate": float(swap.fixed_rate),
                "tenor": tenor, "ccy": ccy}
    except Exception as exc:
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
