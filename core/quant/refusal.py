"""R-11 (S1 USD/KRW leg) and R-12 (S2 US rates-stress leg): RETIRED, display-only refusal books (TASK-M8-12/13;
L1639-1666; section 8.9 rows; section 10 item 22; I-03).

Both legs are REJECT on long history at every timing (DL-A; the records below are archived council evidence,
not reproduced on this machine). They persist only as labelled refusal books `refusal:R-11` / `refusal:R-12`
that no recommended or specification book reads: this module is a PROTECTED module of the T-CTX-01 / I-03
static scan (`core.ficc.context_log.PROTECTED_MODULES`) and every leg calls `assert_not_acting_caller()`
first, so an acting module cannot import or call it. The module-level marker `__refusal_book__` is what the
I-03 static check keys on.

Inputs are read through `pit_window` on the context bindings (consumer `R-11_refusal_book` /
`R-12_refusal_book`); a missing ECOS / KIS input gives a null flag and a 1.0 multiplier, never a proxy: DEXKOUS
and DGS10-as-of-same-day are never read in `run_mode = live` (T-H10-01; item 19/26).
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Mapping

from core.ficc import pit as P
from core.ficc.context_log import assert_not_acting_caller
from core.quant.sleeves import Multiplier
from core.rules.macro_rules import MacroRefusal

__refusal_book__ = True                       # I-03 static marker: display only, read by no book
BOOK_KIND = "refusal"
STATUS = "REFUSAL"
REFUSAL_BOOKS = ("refusal:R-11", "refusal:R-12")
CONSUMER_S1, CONSUMER_S2 = "R-11_refusal_book", "R-12_refusal_book"
S1_SERIES = ("USDKRW_1530_SNAPSHOT", "ECOS_1530_CLOSE")        # the 15:30 KST snapshot, else the ECOS 15:30 close
S2_SERIES = {"live": "US10Y_KIS_QUOTE", "replay": "US10Y_KIS_QUOTE", "backtest": "DGS10"}   # DGS10 only off-line
NEVER_READ = ("DEXKOUS",)                                       # labelled proxy; production_reads_dexkous: false
S1 = {"lookback_obs": 20, "threshold_dlog": 0.03, "multiplier": 0.75, "target": "KR_market_gross", "one_sided": True,
      "verdict": "REJECT", "regate_queue": False}               # refusal_books.S1_krw (L4409)
S2 = {"lookback_obs": 20, "threshold_pp": 0.40, "multiplier": 0.5, "target": "US_duration_sensitive_gross",
      "excludes": ("momentum", "ls_factor_sleeves", "KR"), "verdict": "REJECT", "regate_queue": False}   # S2_rates
S2_EXCLUDED_FAMILIES = ("momentum", "reversal", "quality", "flow", "ts_trend", "ls_factor_sleeves")
S2_STATE_REASON = "S2 refusal book: strict-H.15 flag on from the close of 2026-09-25 (data date 2026-09-23); display only"
G_US_02A_LABEL = "compliant via Treasury with logged posting time"
RECORD_SOURCE = "DL-A; not reproduced on this machine"

CARD_S1 = {"card_id": "MACRO-R11-KR-KRW", "class": "CARD-P", "verdict": "REJECT", "disposition": "REFUSAL_BOOK",
           "displayed_as": "refusal", "label": "RETIRED: REJECT at every timing on KOSPI 1997-04 -> 2026-10 (refusal book, display only)",
           "results_md5": None}
CARD_S2 = {"card_id": "MACRO-R12-US-RATES", "class": "CARD-P", "verdict": "REJECT", "disposition": "REFUSAL_BOOK",
           "displayed_as": "refusal", "label": "RETIRED: REJECT at every timing and cost on US 1990-02 -> 2026-09 (refusal book, display only)",
           "results_md5": None}

# Archived council records (L1647, L1661; section 9.3 G-REF-01/02): values are records, never recomputed here.
REFUSAL_RECORDS = {
    "R-11": {"card_id": CARD_S1["card_id"], "verdict": "REJECT", "span": "KOSPI 1997-04 -> 2026-10", "source": RECORD_SOURCE,
             "backlog": {"BL-S01": "closed", "BL-G04": "P3", "BL-D13": "P3"}, "regate_queue": False,
             "timings": {"strict_H10": {"onsets": 54, "dMDD_pp": -1.3, "tail": 1.004, "tail_label": "tail 1.00"},
                         "strict_H10_holiday_aware": {"onsets": 54, "dMDD_pp": -1.3, "tail": 1.004},
                         "value": {"onsets": 74, "dMDD_pp": -1.7, "tail": 0.996},
                         "yahoo_KRWX_lag2": {"onsets": 69, "dMDD_pp": 0.3, "tail": 0.996}},
             "fragility_ratio": 0.49, "golden_ids": ("G-KR-05", "G-KR-05s", "G-REF-01", "G-POST-01")},
    "R-12": {"card_id": CARD_S2["card_id"], "verdict": "REJECT", "span": "US 1990-02 -> 2026-09", "source": RECORD_SOURCE,
             "backlog": {"BL-S02": "closed"}, "regate_queue": False, "onsets": 71, "onsets_split": {"1990-2007": 39, "2008-2026": 32},
             "timings": {"treasury_plus_1bd": {"compliant": True, "dMDD_pp_50bp": -3.1, "dSR_50bp": -0.105, "label": G_US_02A_LABEL},
                         "strict_H15_plus_2bd": {"compliant": True, "dMDD_pp_50bp": -3.5, "dSR_50bp": -0.120},
                         "value": {"compliant": False, "dMDD_pp_50bp": -0.8},
                         "tnx_live_proxy": {"dMDD_pp_50bp": -1.5}},
             "fragility_ratio": 0.75, "timing_fragile": True, "golden_ids": ("G-REF-02", "G-US-02a")},
}


def regate_queue(rules: Mapping | None = None) -> dict[str, bool]:
    """FORWARD-SIM re-gate queue membership of S1 / S2: both False (BL-S01 / BL-S02 closed)."""
    rb = (rules.get("refusal_books") if isinstance(rules, Mapping) else None) or {"S1_krw": S1, "S2_rates": S2}
    return {"S1_krw": bool(rb["S1_krw"].get("regate_queue", False)), "S2_rates": bool(rb["S2_rates"].get("regate_queue", False))}


def _window(store, sid: str, decision_utc: datetime, knowledge_utc: datetime, consumer: str, n: int, *, registry=None):
    """The last n + 1 visible observations of `sid` through its context binding (the consumer must be bound)."""
    reg = registry if registry is not None else P._registry(None)
    reg.resolve_binding(sid, consumer)                           # UnboundConsumer when the registry lacks the binding
    return P.pit_window(store, sid, decision_utc, knowledge_utc, n=n + 1, registry=reg)


def _record(vals, name: str, role: str = "context") -> tuple:
    return tuple({"series_id": v.series_id, "obs_date": v.obs_date.isoformat(), "value": v.value, "value_status": v.value_status,
                  "available_at_utc": v.available_at_utc.isoformat() if v.available_at_utc else None, "role": role,
                  "name": name} for v in vals)


def refusal_krw_leg(store, decision_utc: datetime, knowledge_utc: datetime, *, registry=None, run_mode: str = "live",
                    lookback: int = S1["lookback_obs"]) -> Multiplier:
    """R-11: krw20 = ln(USDKRW(t) / USDKRW(t - 20 obs)) on the 15:30 KST snapshot or the ECOS 15:30 close stamped
    <= the KRX close of t; flag = krw20 > 0.03 -> 0.75 on Korea market gross in `refusal:R-11` only, one-sided.
    Inputs absent -> flag None, value 1.0, status REFUSAL (never DEXKOUS)."""
    assert_not_acting_caller()
    if run_mode not in P.RUN_MODES:
        raise MacroRefusal(f"run_mode {run_mode!r}")
    used, vals = None, []
    for sid in S1_SERIES:
        vals = _window(store, sid, decision_utc, knowledge_utc, CONSUMER_S1, lookback, registry=registry)
        if len(vals) >= lookback + 1:
            used = sid
            break
    flags: dict = {"S1_krw_flag": None, "krw20": None, "series": used, "fx_regime": "recorded_with_input",
                   "one_sided": True, "regate_queue": False, "backlog": dict(REFUSAL_RECORDS["R-11"]["backlog"])}
    value, reasons = 1.0, []
    if used is None:
        reasons.append(f"S1 refusal book: ECOS / KIS USDKRW input absent ({' / '.join(S1_SERIES)}); flag null; display only")
        inputs = ()
    else:
        a, b = vals[-1].value, vals[-1 - lookback].value
        krw20 = math.log(a / b)
        flag = krw20 > S1["threshold_dlog"]
        value = S1["multiplier"] if flag else 1.0
        flags.update({"S1_krw_flag": bool(flag), "krw20": krw20, "obs_date": vals[-1].obs_date.isoformat()})
        reasons.append(f"S1 refusal book: krw20 {krw20:+.4f} {'>' if flag else '<='} 0.03 on {used} -> {value} "
                       f"(refusal:R-11 only; one-sided; display only)")
        inputs = _record((vals[-1 - lookback], vals[-1]), "usdkrw")
    return Multiplier("R-11-S1", value, "total", "market_gross", status=STATUS, book="refusal:R-11",
                      reasons=tuple(reasons), inputs=inputs, card=dict(CARD_S1), factor="overlay", flags=flags)


def refusal_rates_leg(store, decision_utc: datetime, knowledge_utc: datetime, *, applies_to: str = "market_gross",
                      market: str = "US", registry=None, run_mode: str = "live", lookback: int = S2["lookback_obs"]) -> Multiplier:
    """R-12: d10 = y10(t) - y10(t - 20 obs) in pp on the KIS US 10y quote stamped <= the US close of t (DGS10 only in
    a backtest, strict H.15 timing through the store); flag = d10 > 0.40 -> 0.5 on US duration-sensitive gross
    in `refusal:R-12` only. Raises unless (US, market_gross): momentum and other L/S sleeves (T-BASIS-01 S2 clause)
    and Korea are excluded. Inputs absent -> flag None, value 1.0."""
    assert_not_acting_caller()
    if applies_to != "market_gross" or applies_to in S2_EXCLUDED_FAMILIES:
        raise MacroRefusal(f"R-12-S2 applies to US duration-sensitive gross only, never to {applies_to!r} "
                           f"(excludes {S2['excludes']}; T-BASIS-01)")
    if market != "US":
        raise MacroRefusal(f"R-12-S2 is a US leg: market {market!r} refused (Korea excluded, only 12 onsets)")
    if run_mode not in P.RUN_MODES:
        raise MacroRefusal(f"run_mode {run_mode!r}")
    sid = S2_SERIES[run_mode]
    vals = _window(store, sid, decision_utc, knowledge_utc, CONSUMER_S2, lookback, registry=registry)
    flags: dict = {"S2_rates_flag": None, "d10_pp": None, "series": sid, "timing": "strict_H15_plus_2bd" if sid == "DGS10" else "KIS_quote_le_close",
                   "treasury_channel": G_US_02A_LABEL, "regate_queue": False, "backlog": dict(REFUSAL_RECORDS["R-12"]["backlog"])}
    value, reasons = 1.0, []
    if len(vals) < lookback + 1:
        reasons.append(f"S2 refusal book: {sid} input absent ({len(vals)} of {lookback + 1} obs); flag null; display only")
        inputs = ()
    else:
        d10 = vals[-1].value - vals[-1 - lookback].value
        flag = d10 > S2["threshold_pp"]
        value = S2["multiplier"] if flag else 1.0
        flags.update({"S2_rates_flag": bool(flag), "d10_pp": d10, "obs_date": vals[-1].obs_date.isoformat()})
        reasons.append(f"S2 refusal book: d10 {d10:+.3f} pp {'>' if flag else '<='} 0.40 on {sid} (data date "
                       f"{vals[-1].obs_date.isoformat()}) -> {value}; flag applies from the close of "
                       f"{decision_utc.date().isoformat()}; display only")
        inputs = _record((vals[-1 - lookback], vals[-1]), "us10y")
    return Multiplier("R-12-S2", value, "total", "market_gross", status=STATUS, book="refusal:R-12",
                      reasons=tuple(reasons), inputs=inputs, card=dict(CARD_S2), factor="overlay", flags=flags)


def overlay_refusal_entry(m: Multiplier) -> dict:
    """The `overlay_decision.refusal[]` record of a leg (display only)."""
    if m.status != STATUS or not m.book.startswith("refusal:"):
        raise MacroRefusal(f"{m.rule_id}: not a refusal-book multiplier")
    would = ("Korea market gross (refusal book)" if m.rule_id == "R-11-S1" else "US duration-sensitive gross (refusal book)")
    return {"rule_id": m.rule_id, "value": m.value, "would_apply_to": would, "card": dict(m.card)}


def macro_state_flags(s1: Multiplier | None, s2: Multiplier | None) -> dict:
    """`macro_state.refusal_books` (display only; read by no book)."""
    return {"S1_krw_flag": None if s1 is None else s1.flags.get("S1_krw_flag"),
            "S2_rates_flag": None if s2 is None else s2.flags.get("S2_rates_flag")}


def display_legs(store, decision_utc: datetime, knowledge_utc: datetime, *, market: str, registry=None,
                 run_mode: str = "live") -> dict:
    """The refusal books of `market` for the artifacts' display fields and the `refusal:` books only: R-11 on the KR
    decision, R-12 on the US decision (`macro_state.refusal_books`, `overlay_decision.refusal[]`). The orchestrator's
    display hook calls this inside `run_context_step`; each leg's acting-caller guard still runs first."""
    s1 = refusal_krw_leg(store, decision_utc, knowledge_utc, registry=registry, run_mode=run_mode) if market == "KR" else None
    s2 = refusal_rates_leg(store, decision_utc, knowledge_utc, registry=registry, run_mode=run_mode) if market == "US" else None
    legs = [m for m in (s1, s2) if m is not None]
    return {"refusal_books": macro_state_flags(s1, s2), "refusal_entries": [overlay_refusal_entry(m) for m in legs],
            "books": {m.book: m.value for m in legs}}
