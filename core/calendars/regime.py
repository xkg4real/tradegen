"""Korean market-structure regime tags (R-20 rules 4-5; TASK-M1-04; T-REGIME-01; tech-fund DATA-5).

`regime_tags('KR', d)` returns the effective value of every tag from the owner-signed
`core/calendars/data/kr_regime_tags.yaml` (one row per tag and effective range). The tags are dated facts for
printing, logging and labelling (R-22 regime lines, R-18 structure-break log, R-26 ban-period basis line,
episode tags); none changes exposure and none is a regime-model state (P19).

Fail closed (spec L2089): a date the file does not cover raises `CalendarCoverageError`; a card whose span is
not fully covered is refused (`require_regime_span`); a market without a tag file raises `KeyError`. At load,
every tag must have exactly one row for every date of the file's coverage (no gap, no overlap).

Units are verbatim: `price_limit` is a fraction (0.30), `sell_tax_pct` is percent (0.20 = 0.20%).
"""
from __future__ import annotations

import weakref
from datetime import date, timedelta

from core.calendars.store import CalendarCoverageError, CalendarSet, CalendarUnsigned, default

# R-20 rule 4 names (binding over the section 3.5 abbreviations) plus the two DATA-5 tags the task adds:
# `short_sale_regime` (none | full_ban | partial_ban_non_index; the boolean never encodes the partial period)
# and `value_up` (the 2024-02-26 split).
TAGS = ("price_limit", "saturday_session", "close_time_kst", "closing_call", "random_end", "lunch_break",
        "fx_regime", "etf_available", "short_sale_ban", "sell_tax_pct", "tick_regime", "letf_rules",
        "usdkrw_onshore_hours", "short_sale_regime", "value_up")
FILE_ID = "kr_regime_tags"
_TABLES: "weakref.WeakKeyDictionary[CalendarSet, dict]" = weakref.WeakKeyDictionary()


def _table(cal: CalendarSet) -> dict[str, list[tuple[date, date | None, object]]]:
    if cal in _TABLES:
        return _TABLES[cal]
    f = cal.file(FILE_ID)
    rows: dict[str, list[tuple[date, date | None, object]]] = {t: [] for t in TAGS}
    for i, row in enumerate(f.rows):
        tag = row.get("tag")
        if tag not in rows:
            raise CalendarUnsigned(f"{FILE_ID}: rows[{i}] tag {tag!r} is not one of {TAGS}")
        if "value" not in row:
            raise CalendarUnsigned(f"{FILE_ID}: rows[{i}] ({tag}) has no value")
        lo = date.fromisoformat(row["effective_from"]) if row["effective_from"] else f.covers_from
        hi = date.fromisoformat(row["effective_to"]) if row["effective_to"] else None
        rows[tag].append((lo, hi, row["value"]))
    for tag, spans in rows.items():
        spans.sort(key=lambda s: s[0])
        if not spans:
            raise CalendarUnsigned(f"{FILE_ID}: tag {tag!r} has no rows")
        if spans[0][0] > f.covers_from:
            raise CalendarUnsigned(f"{FILE_ID}: tag {tag!r} starts {spans[0][0]} after covers.from {f.covers_from}")
        for (lo, hi, _v), (nlo, _nhi, _nv) in zip(spans, spans[1:]):
            if hi is None or nlo != hi + timedelta(days=1):
                raise CalendarUnsigned(f"{FILE_ID}: tag {tag!r} rows are not contiguous at {nlo} "
                                       "(exactly one row per tag per date)")
        last_hi = spans[-1][1]
        if last_hi is not None and last_hi < f.covers_to:
            raise CalendarUnsigned(f"{FILE_ID}: tag {tag!r} ends {last_hi} before covers.to {f.covers_to}")
    _TABLES[cal] = rows
    return rows


def regime_tags(market: str, d: date, *, cal: CalendarSet | None = None) -> dict:
    """{tag: effective value} for every tag on date d; KR only."""
    cal = cal or default()
    if market != "KR":
        raise KeyError(f"regime_tags: no regime-tag file for market {market!r} (KR only)")
    f = cal.require_covered(FILE_ID, d)
    out = {}
    for tag, spans in _table(cal).items():
        hits = [v for lo, hi, v in spans if lo <= d and (hi is None or d <= hi)]
        if len(hits) != 1:
            raise CalendarUnsigned(f"{FILE_ID} v{f.version}: {len(hits)} rows for {tag!r} on {d.isoformat()}")
        out[tag] = hits[0]
    return out


def regime_span_covered(start: date, end: date, *, cal: CalendarSet | None = None) -> bool:
    cal = cal or default()
    try:
        f = cal.file(FILE_ID)
    except CalendarUnsigned:
        return False
    return f.covers_from <= start and end <= f.covers_to


def require_regime_span(start: date, end: date, *, cal: CalendarSet | None = None) -> None:
    """Refuse a card whose evidence span the regime-tag file does not fully cover (spec L2089)."""
    cal = cal or default()
    f = cal.file(FILE_ID)
    if not (f.covers_from <= start and end <= f.covers_to):
        raise CalendarCoverageError(f"card span {start}..{end} not fully covered by {FILE_ID} v{f.version} "
                                    f"({f.covers_from}..{f.covers_to}); the card is refused")
