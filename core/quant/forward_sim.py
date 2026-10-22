"""R-28 trend axis and R-29 MACRO-R06-US-FUT as FORWARD-SIM books (TASK-M8-09/10/11; L2964-3154; section 8.3;
section 10 items 22, 23, 32, 37; D5).

Both cards are FORWARD-SIM in the specification book until a US or other non-Korean sleeve exists (D5 pending,
`sleeves.US.line: none`, `sleeves.US.notional_nav: null`): their multipliers exist only for their own
`forward_sim:<rule>` books (`assert_forward_sim_book`), are never read by the recommended book (I-03) and never
reach `engine_feed` (R-35). No header can be committed today (the gate package is NOT_FROZEN, the notional is
a typed null), so no forward record starts; the rule state is display only (`macro_state.forward_sim`).

R-28: trend(t_m) = 0.5 if the month-end official close < SMA10m (mean of the last 10 month-end closes including
t_m) else 1.0, decided at the month-end close, held to the next month-end decision, composed by min() with vt;
a Korea instance is refused (item 37; the KOSPI trend state is a context_log item, never computed here).
R-29: vt_US(t) = min(1.0, 0.15 / sigma_SMA20(t)) on CME_micro_ES at 5 bp; integer contracts only with a declared
notional and a nav_fx read; the 1926+ settling run cannot run without the frozen French daily fixture and never
falls back to the 1990 file; promotion needs the US line, the settling pass and the v2 package pass.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

import numpy as np

from core.ficc import pit as P
from core.quant import cardp
from core.quant import risk_layer as RL
from core.quant.sleeves import Multiplier
from core.rules.macro_rules import MacroRefusal, dnb_item

BOOK_R28, BOOK_R29 = "forward_sim:R-28", "forward_sim:R-29"
FORWARD_SIM_BOOKS = (BOOK_R28, BOOK_R29)
CLAIM_R28 = "slow-bear protection via the volatility state"                          # L2986, verbatim
POOLING_INDICES = ("SPX", "N225", "HSI", "DAX", "FTSE100", "TAIEX")
SMA_MONTHS, TREND_BELOW, DECLUSTER_MONTHS = 10, 0.5, 10
VT_TARGET, VT_WINDOW, VT_CAP = 0.15, 20, 1.0
CONTRACT_NOTIONAL_KRW, MAX_CONTRACT_SHARE = 52e6, 0.05                               # instruments.futures_granularity
US_FUT_CARD, US_FUT_FAMILY, US_FUT_BOOK, US_FUT_COST_BP = "MACRO-R06-US-FUT", "R-06", "CME_micro_ES", 5.0
SETTLING_FIXTURE = "french_daily_mktrf_rf_1926-07_2026-08.csv"
NEVER_FALLBACK = "french_daily_mom_1990-01-02_2026-08-31.csv"
DECADE_STARTS = 10
LOGGED_TRIALS = ("monthly_50bp", "band_0p10_50bp")
D5_LINES = ("CME_micro_ES", "KRX_listed_SP500_ETF")
NAV_FX = {"live": ("USDKRW_1530_SNAPSHOT", "nav_fx"), "replay": ("USDKRW_1530_SNAPSHOT", "nav_fx"),
          "backtest": ("ECOS_1530_CLOSE", "nav_fx_backtests")}
CARD_R28 = {"card_id": "MACRO-R28-US-TREND", "class": "CARD-P", "verdict": "NOT_RUN", "disposition": "FORWARD_SIM",
            "displayed_as": "descriptive", "label": "FORWARD-SIM until a US sleeve exists (D5)", "results_md5": None}
CARD_R29 = {"card_id": US_FUT_CARD, "class": "CARD-P", "verdict": "NOT_RUN", "disposition": "FORWARD_SIM",
            "displayed_as": "descriptive", "label": "FORWARD-SIM pending the 1926+ settling run and D5", "results_md5": None}


class SettlingRunUnavailable(RuntimeError):
    """The frozen 1926-07 -> 2026-08 fixture is absent: the card stays FORWARD-SIM (never the 1990 file)."""


class MacroRefused(MacroRefusal):
    """A refusal with its reasons listed (`.reasons`)."""

    def __init__(self, reasons: Sequence[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = list(reasons)


def assert_forward_sim_book(book: str, rule: str) -> None:
    """A FORWARD-SIM multiplier exists for its own `forward_sim:<rule>` book only (I-03; T-TREND-04)."""
    if book != f"forward_sim:{rule}":
        raise MacroRefusal(f"{rule}: a FORWARD-SIM multiplier is produced for forward_sim:{rule} only, not {book!r} "
                           "(section 10 item 22; never the recommended or specification book, never engine_feed)")


def _refuse_kr(market: str) -> None:
    if market == "KR":
        it = dnb_item(37)
        raise MacroRefusal(f"R-28 instance for KR refused: section 10 item {it['item']} ({it['label']}_{it['basis']}) "
                           "[r28_instance_market_kr]: a KOSPI trend card never acts; the KOSPI trend state is context only")


# --------------------------------------------------------------------------- #
# R-28 trend axis
# --------------------------------------------------------------------------- #
def below_sma10m(closes_monthly: Sequence[float], n: int = SMA_MONTHS) -> bool | None:
    """flag = close(t_m) < mean of the last n month-end closes including t_m; None with fewer than n closes."""
    c = [float(x) for x in closes_monthly]
    if len(c) < n or any(not math.isfinite(x) for x in c[-n:]):
        return None
    return c[-1] < sum(c[-n:]) / n


def trend_multiplier(closes_monthly: Sequence[float], *, previous: float = 1.0) -> tuple[float, bool | None, str]:
    """(value, flag, status): 0.5 below trend, 1.0 above; a missing month-end close leaves the multiplier
    unchanged and fails closed (R-19)."""
    flag = below_sma10m(closes_monthly)
    if flag is None:
        return float(previous), None, "fail_closed"
    return (TREND_BELOW if flag else 1.0), flag, "ok"


def trend_axis(market: str, decision_utc: datetime, *, closes_monthly: Sequence[float], book: str = BOOK_R28,
               previous: float = 1.0, inputs: tuple = ()) -> Multiplier:
    """The R-28 gross overlay (value in {0.5, 1.0}, exposure_basis total) for the `forward_sim:R-28` book only;
    a Korea instance raises before any read (T-TREND-03); composition is min() with vt (the caller composes)."""
    _refuse_kr(market)
    assert_forward_sim_book(book, "R-28")
    value, flag, status = trend_multiplier(closes_monthly, previous=previous)
    reason = (f"R-28: month-end close {'<' if flag else '>='} SMA10m -> {value} (decided at the month-end close, "
              f"holds to the next; min() with vt; FORWARD-SIM book only)" if flag is not None
              else "R-28: month-end official close missing -> multiplier unchanged, fail_closed (R-19)")
    return Multiplier("R-28", value, "total", "market_gross", status=status, book=book, reasons=(reason,),
                      inputs=tuple(inputs), card=dict(CARD_R28), factor="overlay",
                      flags={"R28_below_sma10m": flag, "market": market, "decision_utc": decision_utc.isoformat()})


def declustered_onsets_monthly(flags: Sequence[bool], gap_months: int = DECLUSTER_MONTHS) -> int:
    """Onsets (flag 0 -> 1) kept only when >= gap_months after the previous kept onset (brief F-35)."""
    f = [bool(x) for x in flags]
    kept, last = 0, None
    for i in range(1, len(f)):
        if f[i] and not f[i - 1] and (last is None or i - last >= gap_months):
            kept, last = kept + 1, i
    return kept


def check_trend_header(header: Mapping) -> list[str]:
    """T-TREND-01: refuse a header missing monthly SMA10m, gross 0.5x below trend, min() composition, the claim
    verbatim or a pooled-onset rule, or one with a Sharpe / return / predictability claim; all before any run."""
    out = []
    p = header.get("parameters") or {}
    if p.get("signal") != "month_end_close_below_sma10m" or header.get("rebalance") != "monthly" or p.get("decided") != "month_end_close":
        out.append("monthly SMA10m signal not declared (parameters.signal month_end_close_below_sma10m, rebalance monthly, decided month_end_close)")
    if p.get("multiplier_below") != TREND_BELOW or p.get("multiplier_above") != 1.0:
        out.append("gross 0.5x below trend / 1.0 above not declared (parameters.multiplier_below 0.5, multiplier_above 1.0)")
    if p.get("composition") != "min" or p.get("exposure_basis") != "total":
        out.append("min() composition on total exposure not declared (parameters.composition min, exposure_basis total)")
    claim = header.get("claim")
    if claim != CLAIM_R28:
        out.append(f"claim must read {CLAIM_R28!r} verbatim, got {claim!r}")
    if header.get("claim_type", "protection") != "protection" or any(w in str(claim).lower() for w in ("sharpe", "return", "predict")):
        out.append("a Sharpe, return or predictability claim on a protective rule is refused (P1, L4851)")
    pool = header.get("pooling_rule") or {}
    if not (pool.get("declared_before_any_run") is True and pool.get("decluster_gap_months") == DECLUSTER_MONTHS
            and pool.get("indices") and pool.get("own_market_veto") is True):
        out.append("pooled-onset rule not declared before the run (pooling_rule: decluster_gap_months 10, indices, own_market_veto true, declared_before_any_run true)")
    if any("KR" in str(x) or "KOSPI" in str(x) for x in (pool.get("indices") or ())):
        out.append("a Korean index in the pooled set is refused (item 37)")
    lines = header.get("claim_lines") or []
    if not any(l.get("line") == "stacked_dMDD_on_VT" and l.get("min_pp") == 3.0 and l.get("failure") == "cap_INSUFFICIENT" for l in lines):
        out.append("claim line stacked_dMDD_on_VT >= 3 pp (failure cap_INSUFFICIENT, never REJECT) not declared")
    return out


def register_trend_card(header: Mapping, market: str) -> dict:
    """Registration guard: KR raises (item 37); a header failing `check_trend_header` raises; the card is
    FORWARD_SIM until D5 names a US or other non-Korean sleeve."""
    _refuse_kr(market)
    reasons = check_trend_header(header)
    if reasons:
        raise MacroRefused(reasons)
    return {"card_id": header.get("card_id", CARD_R28["card_id"]), "market": market, "status": "FORWARD_SIM",
            "book": BOOK_R28, "claim": CLAIM_R28, "pooling_rule": dict(header["pooling_rule"]),
            "logged_trials_same_ledger": ("BAND200",)}


def overlay_forward_sim_entry(m: Multiplier) -> dict:
    """The `overlay_decision.forward_sim[]` record (display only; never `multipliers[]` while FORWARD-SIM)."""
    if not m.book.startswith("forward_sim:"):
        raise MacroRefusal(f"{m.rule_id}: not a FORWARD-SIM multiplier")
    would = "US market gross on the CME_micro_ES vt book (FORWARD-SIM)" if m.rule_id == "R-28" else "US futures line vt (FORWARD-SIM)"
    return {"rule_id": m.rule_id, "value": m.value, "would_apply_to": would, "card": dict(m.card)}


def macro_state_forward_sim(r28: Multiplier | None, r29: Multiplier | None) -> dict:
    """`macro_state.forward_sim` (display; never the recommended book)."""
    return {"R28_below_sma10m": None if r28 is None else r28.flags.get("R28_below_sma10m"),
            "R29_vt_weight_next": None if r29 is None else (r29.value if r29.status == "ok" else None)}


# --------------------------------------------------------------------------- #
# R-29 US index-futures vol target
# --------------------------------------------------------------------------- #
def vt_us(closes_daily: Sequence[float], *, target: float = VT_TARGET, window: int = VT_WINDOW, cap: float = VT_CAP) -> tuple[float | None, float | None]:
    """(vt, sigma_ann): vt = min(cap, target / sigma_SMA20) on the simple returns of the closes; cap 1.0, no floor
    (R-06 formula, L3083); None with fewer than window + 1 closes."""
    if cap > 1.0:
        raise MacroRefusal(f"vt cap {cap} > 1.0 refused (P2; section 10 item 2)")
    c = np.asarray(list(closes_daily), dtype=float)
    if c.size < window + 1 or not np.all(np.isfinite(c)) or np.any(c <= 0):
        return None, None
    sigma = RL.sma_vol(c[1:] / c[:-1] - 1.0, window)
    if sigma is None or not sigma > 0:
        return None, sigma
    return min(cap, target / sigma), sigma


def vt_futures_multiplier(decision_utc: datetime, *, closes_daily: Sequence[float], book: str = BOOK_R29,
                          previous: float | None = None, inputs: tuple = ()) -> Multiplier:
    """The R-29 vt factor for `forward_sim:R-29` only; a missing close carries the previous weight fail-closed."""
    assert_forward_sim_book(book, "R-29")
    vt, sigma = vt_us(closes_daily)
    if vt is None:
        return Multiplier("R-29", 1.0 if previous is None else float(previous), "total", "market_gross", status="fail_closed",
                          book=book, reasons=("R-29: SMA20 window not available -> weight carried, fail_closed (R-19)",),
                          inputs=tuple(inputs), card=dict(CARD_R29), factor="vt", flags={"sigma_ann": sigma})
    return Multiplier("R-29", float(vt), "total", "market_gross", status="ok", book=book,
                      reasons=(f"VT: sigma_SMA20 {sigma:.1%} -> min(1, 0.15/{sigma:.3f}) = {vt:.3f} (CME_micro_ES, 5 bp, daily; FORWARD-SIM)",),
                      inputs=tuple(inputs), card=dict(CARD_R29), factor="vt", flags={"sigma_ann": sigma})


def round_half_away_from_zero(x: float) -> int:
    return int(math.copysign(math.floor(abs(x) + 0.5), x))


def nav_fx_rate(store, decision_utc: datetime, knowledge_utc: datetime, *, run_mode: str = "live", registry=None):
    """USDKRW_t for the futures line: the latest usable `USDKRW_1530_SNAPSHOT` (consumer nav_fx; `ECOS_1530_CLOSE`
    in a backtest). Fails closed: a MissingInput is returned, never a proxy."""
    sid, consumer = NAV_FX[run_mode]
    return P.pit_value(store, sid, decision_utc, knowledge_utc, consumer, run_mode=run_mode, registry=registry)


def micro_es_contracts(vt: float | None, notional_nav_krw: float | None, index_level: float | None, usdkrw,
                       *, multiplier_usd: float | None = None) -> dict:
    """contracts = round_half_away_from_zero(vt x notional_KRW / (multiplier_USD x index level x USDKRW_t)); every
    owner null (notional, contract multiplier) or a failed nav_fx read gives contracts None (fail closed)."""
    fx = getattr(usdkrw, "value", usdkrw) if not isinstance(usdkrw, P.MissingInput) else None
    out = {"contracts": None, "usdkrw": fx, "notional_nav": notional_nav_krw, "index_level": index_level, "vt": vt,
           "status": "ok", "reason": None}
    missing = [n for n, v in (("notional_nav", notional_nav_krw), ("contract_multiplier", multiplier_usd), ("index_level", index_level),
                              ("vt", vt), ("usdkrw", fx)) if v is None]
    if missing:
        out.update(status="fail_closed", reason="owner input / nav_fx unavailable: " + ", ".join(missing))
        return out
    if notional_nav_krw * MAX_CONTRACT_SHARE < CONTRACT_NOTIONAL_KRW:
        out.update(status="refused", reason=f"one Micro ES (KRW {CONTRACT_NOTIONAL_KRW:,.0f}) exceeds {MAX_CONTRACT_SHARE:.0%} of the "
                                            f"notional {notional_nav_krw:,.0f}: a live book below the granularity floor is refused (R-26)")
        return out
    out["contracts"] = round_half_away_from_zero(vt * notional_nav_krw / (multiplier_usd * index_level * fx))
    return out


# --------------------------------------------------------------------------- #
# Settling run, promotion, registration (R-29 rules 4-6; T-USFUT-01..04)
# --------------------------------------------------------------------------- #
def settling_pass(pc1p_1x: bool, pc1p_2x: bool, start_verdicts: Sequence[str], h1: str, h2: str, full_span: str) -> bool:
    """PASS only if PC-1' holds at 1x and 2x, >= 8 of the 10 decade-spaced starts PASS, no REJECT at any start or
    in either midpoint half, and the full span is PASS (settling_run.full_span_must_pass; L3089-3091)."""
    sv = list(start_verdicts)
    return (bool(pc1p_1x) and bool(pc1p_2x) and len(sv) == DECADE_STARTS
            and sum(v == "PASS" for v in sv) >= 8
            and "REJECT" not in sv and "REJECT" not in (h1, h2)
            and full_span == "PASS")


def settling_result(*, span: str, pc1p_1x: bool, pc1p_2x: bool, starts: Sequence[str], start_verdicts: Sequence[str],
                    h1: str, h2: str, full_span: str) -> dict:
    """The `model_card.macro.settling_run` block: `verdict` is the full-span verdict after the caps (brief F-32), the
    pass flag is `settling_pass`; a failed condition never returns PASS."""
    ok = settling_pass(pc1p_1x, pc1p_2x, start_verdicts, h1, h2, full_span)
    sv = list(start_verdicts)
    floor_ok = len(sv) == DECADE_STARTS and sum(v == "PASS" for v in sv) >= 8 and "REJECT" not in sv
    verdict, _ = cardp.combine_card_verdict({"full_span": full_span, "pc1_prime_1x_2x": bool(pc1p_1x and pc1p_2x),
                                             "floor": floor_ok, "halves": "REJECT" not in (h1, h2)})
    return {"span": span, "verdict": verdict,
            "pc1_prime_1x": bool(pc1p_1x), "pc1_prime_2x": bool(pc1p_2x), "starts": list(starts),
            "n_pass": sum(v == "PASS" for v in sv), "n_starts": len(sv), "n_reject": sum(v == "REJECT" for v in sv),
            "midpoint_halves": {"h1": h1, "h2": h2}, "settling_pass": ok}


def settling_run(data=None, *, starts: str = "decade", cost_bp: float = US_FUT_COST_BP):
    """R-29 rule 4 on French daily Mkt-RF 1926-07 -> 2026-08 at 5 bp. The fixture is not on this machine (TASK-M8-11:
    HTTP 403; licence, owner and md5 to be recorded): without it the run raises `SettlingRunUnavailable` and the
    card stays FORWARD-SIM. The 1990 file is never a fallback."""
    if data is None:
        raise SettlingRunUnavailable(f"REFDATA: {SETTLING_FIXTURE} absent (tests/fixtures/macro/MANIFEST.csv); the card stays "
                                     f"FORWARD-SIM; {NEVER_FALLBACK} is never a fallback (L3126)")
    name = str(getattr(data, "name", data))
    if NEVER_FALLBACK in name or "1990" in name:
        raise SettlingRunUnavailable(f"{name}: the settling run never falls back to the 1990 file (L3126)")
    if starts != "decade":
        raise MacroRefusal("settling_run starts must be decade_spaced (R-22 frozen shape)")
    # REFDATA + freeze (TASK-M8-11): once the frozen 1926 fixture is listed, build the books (cardp.build_books at 5 bp), run
    # cardp.cardp_evaluate on the full span, the 10 decade-spaced starts and the midpoint halves under the frozen
    # package, and return settling_result(...). Nothing is computed before the freeze (P11).
    raise SettlingRunUnavailable("the settling run needs the frozen gate package (P11) and the listed fixture; not runnable here")


@dataclass(frozen=True)
class PromotionCheck:
    ok: bool
    reasons: tuple


def promotion_ok(*, settling_pass: bool, v2_full_span: str, us_line: str | None, notional_nav_krw: float | None,
                 contract_notional_krw: float = CONTRACT_NOTIONAL_KRW, max_share: float = MAX_CONTRACT_SHARE) -> PromotionCheck:
    """Promotion to BUILD-AS-INSURANCE requires all of: a US sleeve with a notional at which one Micro ES is <= 5 %
    (~KRW 1bn) or another D5 line; the settling run passing; the v2 full-span verdict PASS (L3092-3095)."""
    reasons = []
    line_ok = us_line in D5_LINES
    if us_line == "CME_micro_ES":
        if notional_nav_krw is None:
            line_ok, _ = False, reasons.append("sleeves.US.notional_nav is null (owner input)")
        elif notional_nav_krw * max_share < contract_notional_krw:
            line_ok, _ = False, reasons.append(f"notional {notional_nav_krw:,.0f} below ~KRW {contract_notional_krw / max_share:,.0f}: one Micro ES > {max_share:.0%}")
    if not line_ok and us_line not in ("CME_micro_ES",):
        reasons.append(f"no US sleeve or owner line (D5: sleeves.US.line {us_line!r})")
    if not settling_pass:
        reasons.append("the 1926+ settling run has not passed")
    if v2_full_span != "PASS":
        reasons.append(f"v2 full-span verdict {v2_full_span!r} is not PASS")
    return PromotionCheck(line_ok and settling_pass and v2_full_span == "PASS", tuple(reasons))


def card_status(check: PromotionCheck) -> str:
    return "BUILD_AS_INSURANCE" if check.ok else "FORWARD_SIM"


def _us_fut_row(header: Mapping, *, run_utc: str, cost_bp: float, rebalance: str, band: float, kind: str = "trial",
                card_id: str | None = US_FUT_CARD, script: str = "core/quant/forward_sim.py") -> dict:
    p = dict(header.get("parameters") or {})
    return {"rule": "R-29", "params": {**p, "cost_bp": cost_bp, "rebalance": rebalance, "no_trade_band": band},
            "timing_class": "COMPLIANT", "span": [str((header.get("data_span") or {}).get("start", "1926-07-01")),
                                                   str((header.get("data_span") or {}).get("end", "2026-08-31"))],
            "market": "US", "run_utc": run_utc, "phase": "card", "script": script, "instrument_book": header.get("instrument_book"),
            "rebalance": rebalance, "cost": cost_bp, "card_id": card_id, "run_kind": kind, "estimator": "sma20"}


def register_us_fut(ledger, header: Mapping, *, run_utc: str) -> dict:
    """Register MACRO-R06-US-FUT once as a new card: one trial in the R-06 family ledger with a Micro ES 5 bp book
    and a notional field. A second registration under the family with another book or cost raises (DNB 23/32:
    the instrument book never switches after results; the 50 bp card stays its own REJECT)."""
    if header.get("card_id") != US_FUT_CARD or header.get("family_id", US_FUT_FAMILY) != US_FUT_FAMILY:
        raise MacroRefusal(f"R-29 registers {US_FUT_CARD} in family {US_FUT_FAMILY} only")
    if "notional_nav" not in header:
        raise MacroRefusal("a header without notional_nav is refused (L3127); the value may be the owner's typed null")
    if header.get("instrument_book") != US_FUT_BOOK:
        raise MacroRefusal(f"R-29 is the {US_FUT_BOOK} line, not {header.get('instrument_book')!r}")
    cost = float((header.get("costs") or {}).get("cost_bp", US_FUT_COST_BP))
    if cost != US_FUT_COST_BP:
        it = dnb_item(23)
        raise MacroRefusal(f"{US_FUT_CARD} at {cost:g} bp refused: section 10 item {it['item']} ({it['label']}_{it['basis']}); "
                           f"the Micro ES book is pre-registered at {US_FUT_COST_BP:g} bp and never re-costed")
    prior = [r for r in ledger.rows() if r.get("card_id") == US_FUT_CARD]
    if prior:
        it = dnb_item(23)
        raise MacroRefusal(f"{US_FUT_CARD} is already registered ({prior[0]['instrument_book']} at {prior[0]['cost']} bp): a second "
                           f"registration is an instrument-book switch, section 10 item {it['item']} ({it['label']}_{it['basis']}) "
                           "[header_edit_after_results_md5]; a different book is a new card id")
    res = ledger.append(_us_fut_row(header, run_utc=run_utc, cost_bp=cost, rebalance="daily", band=0.0))
    return res.row


def log_variant_trials(ledger, header: Mapping, *, run_utc: str) -> list[dict]:
    """The monthly 50 bp and banded 50 bp variants: logged R-06 trials (`run_kind: variant`, no card id), never a
    revision of this card and never a rescue (DNB 23)."""
    rows = [_us_fut_row(header, run_utc=run_utc, cost_bp=50.0, rebalance="monthly", band=0.0, kind="variant", card_id=None),
            _us_fut_row(header, run_utc=run_utc, cost_bp=50.0, rebalance="daily", band=0.10, kind="variant", card_id=None)]
    for r, name in zip(rows, LOGGED_TRIALS):
        r["params"]["variant"] = name
        r["instrument_book"] = "US_shares_KIS"
    return [ledger.append(r).row for r in rows]


def display_books(store, decision_utc: datetime, knowledge_utc: datetime, *, market: str, registry=None,
                  run_mode: str = "live", previous: Mapping | None = None) -> dict:
    """R-28 / R-29 on the US decision for the display and their own `forward_sim:` books only (wired by
    core/skills/macro_daily.py `_forward_display`): SPX_MONTH_END_CLOSE (consumer R-28_R-29) -> `trend_axis`,
    SPX_OFFICIAL_CLOSE -> `vt_futures_multiplier`; forward_sim:R-28 = compose(vt_R29, [trend], 1, 1) (min()).
    Official closes only in a live run. `previous` is the last `macro_state.forward_sim` (the carried values of a
    fail-closed read). Another market has neither card (R-28 KR refused, item 37). Never engine_feed (TASK-M8-05)."""
    if market != "US":
        return {"forward_sim": None, "forward_entries": [], "books": {}}
    prev = previous or {}
    st = ("official_close",) if run_mode == "live" else P.CLOSE_STATUSES
    monthly = P.pit_window(store, "SPX_MONTH_END_CLOSE", decision_utc, knowledge_utc, n=SMA_MONTHS, registry=registry, statuses=st)
    daily = P.pit_window(store, "SPX_OFFICIAL_CLOSE", decision_utc, knowledge_utc, n=VT_WINDOW + 1, registry=registry, statuses=st)
    r28 = trend_axis("US", decision_utc, closes_monthly=[v.value for v in monthly],
                     previous=TREND_BELOW if prev.get("R28_below_sma10m") else 1.0)
    r29 = vt_futures_multiplier(decision_utc, closes_daily=[v.value for v in daily], previous=prev.get("R29_vt_weight_next"))
    return {"forward_sim": macro_state_forward_sim(r28, r29), "forward_entries": [overlay_forward_sim_entry(m) for m in (r28, r29)],
            "books": {BOOK_R28: RL.compose(r29.value, [r28.value], 1.0, 1.0), BOOK_R29: r29.value}}
