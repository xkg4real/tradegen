"""DATA-6 investor-type flow log (R3 G-11 / TF-40, CR-03; backlog BL-D01 / BL-C06; R-13 context).

Logs final KRX investor-type daily net buys (foreign / institution / individual) with timestamps from day
one, so that an open-leg test can run after three years of history (G-11). A logged flow is history only:
a session's flows are usable for a decision strictly after that session (t-1 rule, BL-D01), and only
`final` rows count. There is no direction rule (DNB-TF-06 / macro DO-NOT-BUILD item 14): rows carry no sign,
side or signal field and nothing here returns one. Without an investor-flow provider (none is wired to KIS
in this repository) `record` writes one `not_available` row per investor type; it never fabricates a value.

No wall clock and no default path: `retrieved_at_utc` and the log path are the caller's. CONTEXT only.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Iterable, Mapping

INVESTOR_TYPES = ("foreign", "institution", "individual")
STATUSES = ("final", "preliminary", "not_available")
FIELDS = ("session_date", "investor_type", "net_buy_krw", "status", "source", "published_utc", "retrieved_at_utc",
          "detail")
ACTS = False


def record(session_date: date, retrieved_at_utc: datetime,
           fetch: Callable[[date], Mapping[str, Mapping]] | None = None) -> list[dict]:
    """One row per investor type for `session_date`. `fetch(session_date)` -> {investor_type: {net_buy_krw,
    status, source, published_utc}}; without it every row is `not_available`."""
    if retrieved_at_utc.tzinfo is None:
        raise ValueError("retrieved_at_utc must be tz-aware UTC")
    got = fetch(session_date) if fetch is not None else {}
    rows = []
    for t in INVESTOR_TYPES:
        v = got.get(t)
        status = v.get("status") if v else "not_available"
        if status not in STATUSES:
            raise ValueError(f"{t}: status {status!r} not in {STATUSES}")
        rows.append({"session_date": session_date.isoformat(), "investor_type": t,
                     "net_buy_krw": v.get("net_buy_krw") if v else None, "status": status,
                     "source": v.get("source") if v else None,
                     "published_utc": v.get("published_utc") if v else None,
                     "retrieved_at_utc": retrieved_at_utc.isoformat(),
                     "detail": "" if v else "no investor-flow provider wired (KIS investor-type endpoint not built)"})
    return rows


def append(path: Path | str, rows: Iterable[Mapping]) -> int:
    """Binary append, one JSON line per row (LF); raises on failure, never swallows. Returns rows written."""
    lines = []
    for r in rows:
        if set(r) != set(FIELDS):
            raise ValueError(f"flow row fields {sorted(r)} != {sorted(FIELDS)}")
        lines.append(json.dumps({k: r[k] for k in FIELDS}, sort_keys=True).encode("utf-8") + b"\n")
    with open(path, "ab") as fh:
        fh.write(b"".join(lines))
    return len(lines)


def read(path: Path | str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def usable_history(rows: Iterable[Mapping], decision_session: date) -> list[dict]:
    """The t-1 rule: final rows of sessions strictly before the decision session; history, never a signal."""
    cut = decision_session.isoformat()
    return [dict(r) for r in rows if r["status"] == "final" and r["session_date"] < cut]
