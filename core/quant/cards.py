"""Card registry, blind header commits, verdict chain and snapshot archive (section 8.1.3 step 4, section 8.4,
R-35 verdict integrity, R-26 rule 6 re-export; TASK-M7-18, M7-19 write/append, M7-20, M7-23, M7-29, M7-30).

Nothing here computes a verdict. The registry is data: every macro card, its class, family, instrument book,
today's status (`NOT_RUN` everywhere; the R-06 US 50 bp card is the registered REJECT, `rerun: False`), its
disposition and its verbatim label. `draft_header` builds a header with typed nulls where an owner input, the
freeze, the ledger or a reference fixture is missing; `owner_nulls` says which fields are null and why;
`commit_header` refuses while `gate.package.status != FROZEN`, while the anchor is `UNVERSIONED` (ruling 3.1) or
while any owner input is null, and otherwise writes the immutable header with its `header_md5`,
`ledger_hash_at_registration` and `N_raw_at_registration` plus a `header_commit` governance event.
`write_card` / `append_verdict` / `archive_snapshot` are the R-35 integrity path M8's `verdict_filter` reads.

Clocks, roots, stores and the ledger are injected; this module never reads a wall clock or `config`.
reading: draft md5 = the header without VOLATILE_AT_COMMIT (brief spec_M7_cards F-02, L4815).
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.ficc import macro_artifacts as MA
from core.ficc.macro_schema import (HEADER_FIELDS, RESULT_FIELDS, VOLATILE_FIELDS, canonical_json, card_issues,
                                    header_md5, md5_hex, results_md5)
from core.quant.instruments import cost_per_side  # noqa: F401  re-export (ruling S1 deviation 5; R-26)
from core.rules import governance as G
from core.rules.macro_rules import N_GATE, MacroStore, RuleInput, RuleObject, log_refusal, validate_card_header

Clock = Callable[[], datetime]
VERDICTS = ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA")
NOT_RUN = "NOT_RUN"
REFUSAL_LOG = "rules_refusals.jsonl"                 # beside the governance log: one line per refused header
PASS_DISPOSITIONS = ("RECOMMENDATION", "BUILD_AS_INSURANCE")
# the header fields that necessarily change between the acceptance draft and the commit (F-02; L4815)
VOLATILE_AT_COMMIT = ("header_md5", "created_utc", "gate_package_version", "gate_package_md5",
                      "ledger_hash_at_registration", "N_raw_at_registration")
# a change of one of these is a new card id, never a revision (L4892, DNB 23/32); anything else is revision + 1
NEW_CARD_FIELDS = ("claim", "instrument_book", "rebalance", "no_trade_band", "fill_model")
VERDICT_ROW = ("card_id", "revision", "header_md5", "results_md5", "verdict", "disposition", "gate_package_md5",
               "data_snapshot_id", "git_hash", "ledger_hash_at_run", "prev_row_md5")
DEFAULT_CARDP_LABEL = "protective: reduces tail losses vs a same-exposure static book; not expected to outperform"
R06_KR_LABEL = ("Crisis-clustering insurance: reduces drawdown in volatility-clustering crises (1997–98, 2008, 2026); "
                "no help against gap shocks from calm states (2018-10, 2020-02, 2024-08); Sharpe non-inferiority is "
                "marginal — it pays a premium in calm decades (2016–25 alone: tail 0.95, ΔSR −0.079) and is "
                "short the post-crash rebound premium; not expected to outperform; cap 1.0 permanent.")
US_REJECT_LABEL = "REJECT (instrument: US shares via KIS, 50 bp, daily)"


class CardRefused(ValueError):
    """A header, card, chain or archive is refused; `.reasons` lists every reason. Nothing is written."""

    def __init__(self, reasons: Sequence[str]) -> None:
        self.reasons = [str(r) for r in reasons]
        super().__init__("; ".join(self.reasons))


class PackageNotFrozen(CardRefused):
    pass


class ArchiveLost(CardRefused):
    """A formal card's snapshot archive is missing or altered: an integrity failure, never a silent re-run (L6013)."""


# --------------------------------------------------------------------------- #
# Registry (data)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CardSpec:
    card_id: str
    cls: str                               # CARD-O | CARD-P
    family_id: str
    rule_id: str
    market: str | None
    instrument_book: str
    build_status: str                      # rulings 4 vocabulary
    disposition: str                       # today, before any formal run (section 8.1.2)
    displayed_as: str
    label: str | None                      # verbatim; shown beside the verdict
    verdict: str = NOT_RUN                 # today: NOT_RUN everywhere except the registered US REJECT
    revisions: tuple[int, ...] = (1,)
    data_sources: tuple[str, ...] = ()
    notional_ref: str | None = None        # {ref: sleeves.<market>.notional_nav}
    acting_long_sample: bool = True        # F-09: start_band / midpoint_halves required
    step4_header: bool = True              # committed blind in section 8.1.3 step 4
    rerun: bool = True                     # False only for the registered R-06 US card
    conditions: tuple[str, ...] = ()
    proposed: tuple[str, ...] = ()         # header values the spec leaves UNSPEC (brief B2)


R06_KR_CONDITIONS = (
    "(i) a v2 PASS on the full span (regime_line_results[full_span])",
    "(ii) a v2 PASS on the ETF-era line, first full month after the KODEX 200 listing to 2025-12",
    "(iii) no REJECT at any of the 32 monthly starts 1997-05..1999-12 and PASS in >= 22 (3*n_pass >= 2*n_starts)",
    "(iv) no REJECT in either pre-declared calendar-midpoint half",
    "all at the computed selection factor f; f = 1 and f = N_eff both printed; never rescued (R2-C1)",
)

REGISTRY: tuple[CardSpec, ...] = (
    CardSpec("MACRO-R06-KR-ETF", "CARD-P", "R-06", "R-06-KR-VT20", "KR", "KRX_ETF_line", "SPECIFICATION_BOOK",
             "SPECIFICATION_ONLY", "descriptive", R06_KR_LABEL, revisions=(2,),
             data_sources=("KRX_official_closes (F01)", "BOK_CALL_RATE (F02; ECOS code OWNER)", "KODEX 200 listing date (OWNER)"),
             notional_ref="sleeves.KR.notional_nav", conditions=R06_KR_CONDITIONS),
    CardSpec("MACRO-R03-US-MOM", "CARD-O", "R-03", "R-03-US-VS12", "US", "US_shares_KIS", "BUILD_NOW", "DESCRIPTIVE",
             "descriptive", "indicative PASS; step 3 borderline", revisions=(1, 2, 3),
             data_sources=("MOM_PAPER_LS_SERIES on QUANTGEN's own sleeve (OWNER: universe, history start, notional key; F-07)",),
             notional_ref="sleeves.US.notional_nav",
             proposed=("rule_id R-03-US-VS12", "estimator sd126", "fill_model NYSE_moc", "cash_series US_RF (F-08)")),
    CardSpec("MACRO-R04-US-DM", "CARD-O", "R-03", "R-04-DM", "US", "US_shares_KIS", "SPECIFICATION_BOOK",
             "SPECIFICATION_ONLY", "descriptive", "step 3 FAIL (indicative)",
             data_sources=("R-03 family ledger (step 3 add-on)",), step4_header=False, acting_long_sample=False,
             conditions=("not a step-4 header (F-13); specification book only, floor 0.5; "
                         "no pooled or A-provisional route (DNB 34)",)),
    CardSpec("MACRO-R14-MULTI-TREND", "CARD-O", "R-14", "R-14-MULTI-TREND", None, "multi_line", "BUILD_NOW",
             "DESCRIPTIVE", "descriptive", None, data_sources=("12 index lines (COUNCIL: list unspecified, F-10)",),
             acting_long_sample=False, proposed=("rule_id", "estimator sd12m", "cash per line market")),
    CardSpec("MACRO-R31-KR-ETF", "CARD-P", "R-31", "R-31-KR-STEP", "KR", "KRX_ETF_line", "SPECIFICATION_BOOK",
             "SPECIFICATION_ONLY", "descriptive", DEFAULT_CARDP_LABEL,
             data_sources=("KR book NAV history on KRX official closes (F01)",), notional_ref="sleeves.KR.notional_nav",
             acting_long_sample=False,
             conditions=("binding share frozen at the header commit on the recommended book without the steps; "
                         "> 0.10 -> specification book until PASS; <= 0.10 -> INVARIANT_STEP",),
             proposed=("rule_id", "build_status_on_pass BUILD_AS_INSURANCE (F-11)", "tier A", "estimator sma20")),
    CardSpec("MACRO-R28-US-TREND", "CARD-P", "R-28", "R-28-US-SMA10M", "US", "CME_micro_ES", "FORWARD_SIM",
             "FORWARD_SIM", "descriptive", DEFAULT_CARDP_LABEL,
             data_sources=("US month-end official closes on R-29's vt book (span UNSPEC, F-05)",),
             notional_ref="sleeves.US.notional_nav", acting_long_sample=False,
             proposed=("rule_id", "estimator sma20", "tier A via the pooled-onset rule")),
    CardSpec("MACRO-R06-US-FUT", "CARD-P", "R-06", "R-29-US-VT15", "US", "CME_micro_ES", "FORWARD_SIM",
             "FORWARD_SIM", "descriptive", DEFAULT_CARDP_LABEL,
             data_sources=("French daily Mkt-RF and RF 1926-07 -> 2026-08 (F12; HTTP 403, never the 1990 file)",),
             notional_ref="sleeves.US.notional_nav",
             proposed=("rule_id", "fill_model NYSE_moc", "claim text (a protection claim, no Sharpe claim)")),
    CardSpec("MACRO-R06-US", "CARD-P", "R-06", "R-06-US-VT15", "US", "US_shares_KIS", "RETIRED", "DESCRIPTIVE",
             "descriptive", US_REJECT_LABEL, verdict="REJECT", step4_header=False, rerun=False,
             conditions=("registered card: never re-run, never rebuilt (L1575, L4291); monthly and banded 50 bp "
                         "variants are R-06 ledger trials, never rescues (DNB 23)",)),
    CardSpec("MACRO-STACK-KR", "CARD-P", "R-02", "R-02-STACK", "KR", "KRX_ETF_line", "SPECIFICATION_BOOK",
             "DESCRIPTIVE", "descriptive", DEFAULT_CARDP_LABEL, step4_header=False, acting_long_sample=False,
             conditions=("generated by maybe_generate_stack_card before a second de-risk factor joins the recommended "
                         "book (R-02 rule 6, section 8.7); dormant: no de-risk factor is PASS",)),
)
BY_ID: dict[str, CardSpec] = {c.card_id: c for c in REGISTRY}

# section 9.4 pending values (L5996-6014): computed at their first run, md5-frozen, never invented or asserted
# against the research number; golden ids are the P94-nn rows of tests/fixtures/macro/goldens.csv
PENDING_VALUES: tuple[dict, ...] = tuple({"item": i, "golden_id": f"P94-{i:02d}", "title": t, "owner": o, "when": w,
                                          "status": "pending", "package_dependent": i in (1, 4, 11, 12, 14)}
                                         for i, t, o, w in (
    (1, "excess-return restatement of every section 9.3.1 golden (R-22)", "TASK-M7-30", "first formal runs"),
    (2, "official-close reruns DL-A did not recompute after the 2-Oct patch", "TASK-M2-09", "rerun md5-frozen"),
    (3, "R-29 settling run on French daily Mkt-RF 1926-07 -> 2026-08 at 5 bp", "TASK-M8-11", "file acquired"),
    (4, "the Korea card's ES126 z", "TASK-M7-30", "first formal run"),
    (5, "the formal R-06 KR card (I-16) and every formal card under the frozen package", "TASK-M7-21", "frozen package"),
    (6, "event-conditional variance test; 2027-28 post-holiday VaR breach check", "M5/M8", "run"),
    (7, "bootstraps for the section 10 E labels -> B labels", "TASK-M0-15", "run"),
    (8, "R-31 reference run with separate hwm_hard / ref_step references", "TASK-M7-27", "run"),
    (9, "I-04b KOSPI VT20 1997-2026 HALT count under the v2 rule", "TASK-M5-14", "computed, pinned"),
    (10, "G-LAD-04 invariants-only KOSPI book with/without the hard stop", "TASK-M5-14", "computed"),
    (11, "T-POWER-01 years line restated to a point (T_years = sessions/252, SE = SE_plateau)", "TASK-M7-30", "before the freeze"),
    (12, "R-06 KR selection factor under any_overlap, every row-set reading, maximum binding", "TASK-M7-30", "acceptance report"),
    (13, "M1 measurements: KODEX basket instant, NYSE print bound, FRED VIX posting lag", "OWNER", "measured"),
    (14, "frozen-package values of T-EXCESS-01 / I-09, T-GATE-02 p_ni, T-ES-02 z", "TASK-M7-30", "first run"),
    (15, "anchored timestamps for gate.step3.spec_versions and seed run_utc", "OWNER (git)", "anchored"),
    (16, "archive each formal card's snapshot rows, md5-listed", "TASK-M7-20", "built"),
    (17, "atomic engine_feed per book", "M8", "built")))

# typed nulls a draft may carry, with the reason the commit is refused (path -> reason prefix)
NULL_REASONS: dict[str, str] = {
    "notional_nav": "OWNER: sleeves.<market>.notional_nav is null in the store (owner-signed before the header commit)",
    "created_utc": "COMMIT: set from the injected clock at commit",
    "header_md5": "COMMIT: computed at commit over the header fields",
    "gate_package_md5": "FREEZE: gate.package.definitions_md5 is written_at_freeze (status NOT_FROZEN)",
    "ledger_hash_at_registration": "LEDGER: family ledger hash at commit (section 9.5 seeds REFDATA)",
    "N_raw_at_registration": "LEDGER: family ledger row count at commit (section 9.5 seeds REFDATA)",
    "costs.schedule[0].to": "OWNER: the day before the KODEX 200 listing, from the KRX listing record",
    "costs.schedule[1].from": "OWNER: the KODEX 200 listing date, from the KRX listing record",
    "gating_lines.etf_era.from": "OWNER: first day of the first full month after the KODEX 200 listing",
    "data.history_file": "REFDATA: the frozen reference fixture is not on this machine",
    "history_first_close": "OWNER: the sleeve's history start is not declared (F-05 / F-07 / F-10)",
    "data_span.start": "OWNER: the sleeve's declared history is not declared (F-05 / F-07 / F-10)",
    "midpoint_halves.split_date": "OWNER: follows from the declared history start, which is not declared (F-07)",
    "instrument_lines": "COUNCIL: the 12-index list and its lines are not in the spec (F-10)",
    "roll_calendar.calendar": "OWNER: the futures roll calendar (expiry dates) is an owner input",
    "nav_fx.conversion_instant": "OWNER: the nav_fx conversion instant is an owner input",
}


# --------------------------------------------------------------------------- #
# Section 7.1 rule objects the headers instantiate (validate_card_header needs the basis of each rule)
# --------------------------------------------------------------------------- #
def rule_object(card_id: str) -> RuleObject:
    spec = BY_ID[card_id]
    vt = dict(output_range=(0.0, 1.0), exposure_basis="total", applies_to="market_gross", composition="min", factor="vt")
    kinds = {
        "MACRO-R06-KR-ETF": dict(vt, inputs=(RuleInput("KOSPI_OFFICIAL_CLOSE", "acting_exposure", ("specification",), "publication", "market_price"),),
                                 estimator={"name": "sma20", "kind": "sma"}),
        "MACRO-R03-US-MOM": dict(output_range=(0.0, 1.0), exposure_basis="active", applies_to="momentum", composition="min",
                                 factor="vs", inputs=(RuleInput("MOM_PAPER_LS_SERIES", "acting_exposure", ("specification",), "publication", "derived"),),
                                 estimator={"name": "sd126", "kind": "sma"}),
        "MACRO-R04-US-DM": dict(output_range=(0.5, 1.0), exposure_basis="active", applies_to="momentum", composition="min",
                                factor="overlay", inputs=(RuleInput("DM_MKT_RET_24M", "acting_exposure", ("specification",), "publication", "derived"),)),
        "MACRO-R14-MULTI-TREND": dict(output_range=None, exposure_basis="active", applies_to="ts_trend", composition=None,
                                      factor="none", inputs=(RuleInput("NON_KR_INDEX_MONTH_END_CLOSES", "acting_exposure", ("specification",), "publication", "market_price"),),
                                      estimator={"name": "sd12m", "kind": "sma"}),
        "MACRO-R31-KR-ETF": dict(output_range=(0.5, 1.0), exposure_basis="total", applies_to="market_gross", composition="min",
                                 factor="ladder", inputs=(RuleInput("KOSPI_OFFICIAL_CLOSE", "acting_exposure", ("specification",), "publication", "market_price"),)),
        "MACRO-R28-US-TREND": dict(output_range=(0.5, 1.0), exposure_basis="total", applies_to="market_gross", composition="min",
                                   factor="overlay", inputs=(RuleInput("SPX_MONTH_END_CLOSE", "forward_sim", ("forward_sim",), "publication", "market_price"),),
                                   estimator={"name": "sma20", "kind": "sma"}),
        "MACRO-R06-US-FUT": dict(vt, inputs=(RuleInput("SPX_OFFICIAL_CLOSE", "forward_sim", ("forward_sim",), "publication", "market_price"),),
                                 estimator={"name": "sma20", "kind": "sma"}),
        "MACRO-R06-US": dict(vt, inputs=(RuleInput("SPX_OFFICIAL_CLOSE", "history", (), "publication", "market_price"),),
                             estimator={"name": "sma20", "kind": "sma"}, results_md5=None),
        "MACRO-STACK-KR": dict(vt, factor="overlay", output_range=(0.5, 1.0)),
    }[card_id]
    books = ("forward_sim",) if spec.build_status == "FORWARD_SIM" else ("specification",)
    return RuleObject(rule_id=spec.rule_id, kind=spec.cls, books=books, label_layer="none", instrument_book=spec.instrument_book,
                      market=spec.market, card_id=spec.card_id, tier="A", n_rule=N_GATE, **kinds)


# --------------------------------------------------------------------------- #
# Header drafts (section 8.4; brief B2)
# --------------------------------------------------------------------------- #
def _get(store: MacroStore | None, key: str, default=None):
    if store is None:
        return default
    try:
        return store.get(key)
    except KeyError:
        return default


def calendar_midpoint(start: str, end: str) -> str:
    """The calendar midpoint of a fixed span (L2342): start + floor(days / 2); KR 1997-04-01..2026-10-02 -> 2012-01-01."""
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    return (a + timedelta(days=(b - a).days // 2)).isoformat()


def _common(spec: CardSpec, store, *, revision: int) -> dict:
    pkg = _get(store, "gate.package", {}) or {}
    md5 = pkg.get("definitions_md5")
    return {
        "card_id": spec.card_id, "family_id": spec.family_id, "rule_id": spec.rule_id, "revision": revision, "class": spec.cls,
        "label": spec.label, "tier": "A", "created_utc": None, "header_md5": None,
        "gate_package_version": pkg.get("version", "2.0.0"),
        "gate_package_md5": None if md5 in (None, "written_at_freeze") else md5,
        "searched_parameters": [], "notional_nav": _get(store, spec.notional_ref) if spec.notional_ref else None,
        "costs": {"per_side": "read_from_gate", "floor": "tick_floor", "stress": 2.0, "stress_line": "printed"},
        "episode_rule_version": "1", "regime_lines": "from_R20_tags",
        "printed_lines": ["exec_variants_ABC", "overnight_intraday", "turnover_by_regime", "stress_cost_line", "with_risk_layer"],
        "benchmarks": ["buy_and_hold", "overlay_off", "static_same_avg_exposure", "ewma_derisk"],
        "checks": "gate_package_%s" % pkg.get("version", "2.0.0"),
        "ledger_hash_at_registration": None, "N_raw_at_registration": None,
        "timing": {"decision": "close_t_earn_t_plus_1", "inputs": {}},
        "seed": _get(store, "reproducibility.seed_study", 11),
    }


def _r06_kr(store, revision):
    vt = _get(store, "vol_target.KR", {}) or {}
    h = {"claim": R06_KR_LABEL, "claim_type": "protection", "build_status_on_pass": "BUILD_AS_INSURANCE",
         "hypothesis": "VT20 lowers tail losses vs a same-average-exposure static book without a Sharpe loss beyond 0.10",
         "mechanism": "variance reduction (variance ratio 0.59); implicitly short the rebound premium (timing return -1.8%/yr)",
         "rule": "vt = min(1.0, 0.20 / sigma_SMA20(t)); decided at the KRX close of t (available_at <= close_print_bound_utc(KR, t)); earns from t+1",
         "parameters": {"estimator": vt.get("estimator", "sma"), "window": vt.get("window", 20), "target_ann": vt.get("target_ann", 0.20),
                        "cap": vt.get("cap", 1.0), "floor": "none"},
         "estimator": "sma20", "instrument_book": "KRX_ETF_line", "rebalance": "daily", "no_trade_band": 0.0,
         "fill_model": "KRX_close_auction",
         "costs_extra": {"schedule": [{"to": None, "cost_class": "futures"}, {"from": None, "cost_class": "krx_etf"}],
                         "printed_lines": ["krx_etf_3bp_throughout"]},
         "data": {"source": "KRX_official_closes", "value_status": "official_close", "history_file": None,
                  "reconciliation": "R-01: index 1 bp, stocks exact",
                  "golden_tolerance": "Level-2, only for I-16's raw-flag data check vs G-KR-L01; the formal run's differences are printed, never gated",
                  "saturday_sessions_before": "1998-12-12"},
         "history_first_close": _get(store, "gate.evaluation.history_start.KR", "1997-04-01"),
         "data_span": {"start": "first_close_plus_20_session_warmup", "end": _get(store, "gate.evaluation.data_cutoff.KR", "2026-10-02")},
         "cash_convention": {"returns": "excess", "cash_series": "BOK_CALL_RATE", "day_count": "act_365"},
         "gating_lines": {"full_span": "v2_PASS", "etf_era": {"from": None, "to": "2025-12-31", "require": "v2_PASS"}},
         "start_band": {"shape": "R-06_KR", "from": "1997-05", "to": "1999-12", "step": "month", "starts": 32,
                        "require": {"no_reject": True, "pass_share_min": "2/3"}},
         "midpoint_halves": {"split": "calendar_midpoint", "require": "no_reject"},
         "printed_lines_extra": ["etf_era_to_present", "pre_design_2002-10_to_2015-12", "1997_to_2002_alone", "2016_to_2025_alone",
                                 "rolling_decades", "pc4_under_section_8_6", "ewma094_line", "timing_return", "years_lagging_S",
                                 "h1_2026_bull_tax", "median_reentry_lag", "per_regime_table"],
         "primary_oos_line": "etf_era", "comparator": "S_same_average_exposure",
         "timing_inputs": {"KOSPI": {"series": "KOSPI_OFFICIAL_CLOSE", "value_status": "official_close", "available_at": "<= close_print_bound_utc(KR, t)"}},
         "outcomes": {"PASS": "BUILD-AS-INSURANCE", "INSUFFICIENT_DATA": "specification_book_control_regated_on_new_objective_episode", "REJECT": "archive"},
         "owner_decisions": {"risk_layer.korea_caps.template": _get(store, "risk_layer.korea_caps.template", "msci_25_50")}}
    h["midpoint_halves"]["split_date"] = calendar_midpoint(h["history_first_close"], h["data_span"]["end"])
    return h


def _r03(store, revision):
    own = _get(store, "families.momentum.own_vol_scale", {}) or {}
    params = {"window": own.get("window", 126), "target_ann": own.get("target_ann", 0.12), "cap": own.get("cap", 1.0),
              "floor": own.get("floor", 0.0), "min_obs": own.get("min_obs", 126), "series": "paper_unit_gross_long_short",
              "apply_to": "sleeve_budget"}
    rule = "vs = min(1.0, 0.12 / sigma126(t)) on the paper unit-gross long/short series; daily; applies to the sleeve budget"
    if revision == 2:
        params.update(own.get("revisions", {}).get("2", {"target": "expanding_median_sigma126", "min_obs": 252}))
        rule = "vs = min(1.0, median_expanding(sigma126) / sigma126(t)), min 252 obs, cap 1.0"
    elif revision == 3:
        params.update(own.get("revisions", {}).get("3", {"vs": "min(1, (0.12/sigma126)^2)"}))
        rule = "vs = min(1, (0.12 / sigma126(t))^2)"
    return {"claim": "own-vol scaling of the momentum sleeve outperforms the same sleeve unscaled (L1515, L1526)",
            "claim_type": "outperformance", "build_status_on_pass": "BUILD_NOW",
            "hypothesis": "scaling the sleeve budget by 0.12 / sigma126 raises its net Sharpe vs the unscaled sleeve",
            "mechanism": "second-moment scaling of the sleeve budget; no directional signal", "rule": rule, "parameters": params,
            "estimator": "sd126", "instrument_book": "US_shares_KIS", "rebalance": "daily", "no_trade_band": 0.0, "fill_model": "NYSE_moc",
            "nav_fx": {"series": "USDKRW_1530_SNAPSHOT", "history": "ECOS_1530_CLOSE", "conversion_instant": None, "role": "acting_exposure"},
            "data": {"source": "MOM_PAPER_LS_SERIES", "value_status": "official_close", "history_file": None},
            "history_first_close": None, "data_span": {"start": None, "end": _get(store, "gate.evaluation.data_cutoff.US", "2026-10-01")},
            "cash_convention": {"returns": "excess", "cash_series": "US_RF"},
            "start_band": {"shape": "default", "step": "month", "starts": 33, "require": {"no_reject": True, "pass_share_min": "2/3"}},
            "midpoint_halves": {"split": "calendar_midpoint", "split_date": None, "require": "no_reject"},
            "primary_oos_line": "full_span", "comparator": "overlay_off",
            "timing_inputs": {"MOM": {"series": "MOM_PAPER_LS_SERIES", "value_status": "official_close"}},
            "outcomes": {"PASS": "recommended book through verdict_filter with the step-3-borderline flag", "INSUFFICIENT_DATA": "specification_book", "REJECT": "specification_book"}}


def _r14(store, revision):
    ts = _get(store, "families.ts_trend", {}) or {}
    return {"claim": "diversification, i.e. correlation and drawdown behaviour against the equal-weight long-only basket, not outperformance",
            "claim_type": "diversification", "build_status_on_pass": "BUILD_NOW",
            "hypothesis": "a 12-1 sign TS-trend sleeve lowers correlation and drawdown vs the equal-weight basket of the same indices",
            "mechanism": "sign of the 12-1 month return times min(1, 0.15 / sigma_12m); second-moment sizing per asset",
            "rule": "signal = sign(12-1 month return), monthly; per-asset weight = signal x min(1.0, 0.15 / sigma_12m)",
            "parameters": {"signal": ts.get("signal", "sign_12_1"), "rebalance": "monthly", "vol_window_months": ts.get("vol_window_months", 12),
                           "target_ann": ts.get("target_ann", 0.15), "cap": ts.get("cap", 1.0), "overlay_exempt": True},
            "estimator": "sd12m", "instrument_book": "multi_line", "instrument_lines": None, "rebalance": "monthly", "no_trade_band": 0.0,
            "fill_model": "per_line", "data": {"source": "NON_KR_INDEX_MONTH_END_CLOSES", "value_status": "official_close", "history_file": None},
            "history_first_close": None, "data_span": {"start": None, "end": _get(store, "gate.evaluation.data_cutoff.US", "2026-10-01")},
            "cash_convention": {"returns": "excess", "cash_series": "US_RF"}, "start_band": None, "midpoint_halves": None,
            "primary_oos_line": "full_span", "comparator": "overlay_off",
            "printed_lines_extra": ["failure_mode: not fast-crash protection", "correlation_with_SP500_2001_2026", "correlation_with_SP500_2013_2026"],
            "timing_inputs": {"indices": {"series": "NON_KR_INDEX_MONTH_END_CLOSES", "value_status": "official_close"}},
            "outcomes": {"PASS": "sleeve acts (ts_trend admissible)", "INSUFFICIENT_DATA": "displayed descriptively", "REJECT": "displayed descriptively"}}


def _r31(store, revision):
    c = _get(store, "cards.R-31_step_down", {}) or {}
    return {"claim": c.get("claim", "protection in persistent drawdowns; time-boxed; no Sharpe claim"), "claim_type": "protection",
            "build_status_on_pass": "BUILD_AS_INSURANCE",
            "hypothesis": "time-boxed step-downs after -8% / -12% drawdowns lower tail losses vs the same book without steps",
            "mechanism": "exposure halved for 21 sessions after a drawdown step; no mean claim",
            "rule": "steps -8% -> 0.5x; -12% -> 0.5x + new-entry block; dwell 21 sessions; step reference = running peak since last reset",
            "parameters": {"steps": c.get("steps"), "dwell_sessions": c.get("dwell_sessions", 21), "step_reference": c.get("step_reference"),
                           "hard_stop_reference_resets_at_dwell_end": c.get("hard_stop_reference_resets_at_dwell_end", False),
                           "composition": c.get("composition", "min"), "denominator": c.get("denominator", "whole_book_nav")},
            "estimator": "sma20", "instrument_book": "KRX_ETF_line", "rebalance": "daily", "no_trade_band": 0.0, "fill_model": "KRX_close_auction",
            "data": {"source": "KRX_official_closes", "value_status": "official_close", "history_file": None, "saturday_sessions_before": "1998-12-12"},
            "history_first_close": _get(store, "gate.evaluation.history_start.KR", "1997-04-01"),
            "data_span": {"start": "first_close_plus_20_session_warmup", "end": _get(store, "gate.evaluation.data_cutoff.KR", "2026-10-02")},
            "cash_convention": {"returns": "excess", "cash_series": "BOK_CALL_RATE", "day_count": "act_365"},
            "start_band": None, "midpoint_halves": None, "primary_oos_line": "full_span", "comparator": "S_same_average_exposure",
            "printed_lines_extra": ["binding_share", "binding_shares", "n_halts", "persistence_check"],
            "timing_inputs": {"KOSPI": {"series": "KOSPI_OFFICIAL_CLOSE", "value_status": "official_close"}},
            "outcomes": {"PASS": "steps act in the recommended book", "INSUFFICIENT_DATA": "specification_book_while_share_gt_0p10", "REJECT": "specification_book_while_share_gt_0p10"},
            "owner_decisions": {"risk_layer.drawdown.hard_stop.level": _get(store, "risk_layer.drawdown.hard_stop.level", -0.15)}}


def _r28(store, revision):
    c = _get(store, "cards.R-28_trend_axis", {}) or {}
    return {"claim": c.get("claim", "slow-bear protection via the volatility state"), "claim_type": "protection",
            "build_status_on_pass": "BUILD_AS_INSURANCE",
            "hypothesis": "a month-end close below SMA10m halves the vt book and lowers stacked drawdown by >= 3 pp",
            "mechanism": "exposure state on the vol-targeted book; decided at month end, applies next month",
            "rule": "month-end close < SMA10m -> 0.5 else 1.0; applies next month; composition min; incremental on R-29's vt book",
            "parameters": dict(c.get("rule") or {"signal": "month_end_close_below_sma10m", "multiplier_below": 0.5, "multiplier_above": 1.0,
                                                 "decided": "month_end_close", "applies": "next_month", "composition": "min", "exposure_basis": "total"}),
            "estimator": "sma20", "instrument_book": "CME_micro_ES", "rebalance": "monthly", "no_trade_band": 0.0, "fill_model": "NYSE_moc",
            "nav_fx": {"series": "USDKRW_1530_SNAPSHOT", "history": "ECOS_1530_CLOSE", "conversion_instant": None, "role": "forward_sim"},
            "roll_calendar": {"rule": "roll_before_expiry_fixed_calendar", "calendar": None},
            "data": {"source": "SPX_MONTH_END_CLOSE", "value_status": "official_close", "history_file": None},
            "history_first_close": None, "data_span": {"start": None, "end": _get(store, "gate.evaluation.data_cutoff.US", "2026-10-01")},
            "cash_convention": {"returns": "excess", "cash_series": "US_RF"}, "start_band": None, "midpoint_halves": None,
            "primary_oos_line": "full_span", "comparator": "S_same_average_exposure",
            "claim_lines": [{"line": "stacked_dMDD_on_VT", "min_pp": c.get("judged", {}).get("claim_line_stacked_dMDD_min_pp", 3.0),
                             "failure": "cap_INSUFFICIENT", "reason": "claim_not_shown"}],
            "pooling_rule": dict(c.get("pooling") or {}), "timing_inputs": {"SPX": {"series": "SPX_MONTH_END_CLOSE", "value_status": "official_close"}},
            "outcomes": {"PASS": "BUILD-AS-INSURANCE once D5 names a US sleeve", "INSUFFICIENT_DATA": "FORWARD_SIM", "REJECT": "FORWARD_SIM"},
            "owner_decisions": {"sleeves.US.line": _get(store, "sleeves.US.line", "none")}}


def _r29(store, revision):
    c = _get(store, "cards.R-29_US_FUT", {}) or {}
    start, end = "1926-07-01", "2026-08-31"
    return {"claim": "crisis-clustering insurance on the US futures line: lower tail losses vs a same-exposure static book; not expected to outperform; cap 1.0 permanent",
            "claim_type": "protection", "build_status_on_pass": "BUILD_AS_INSURANCE",
            "hypothesis": "VT15 on CME micro ES lowers tail losses vs S without a Sharpe loss beyond 0.10",
            "mechanism": "variance reduction through the SMA20 volatility state",
            "rule": "vt_US(t) = min(1.0, 0.15 / sigma_SMA20(t)); daily; earns from t+1",
            "parameters": dict(c.get("rule") or {"estimator": "sma", "window": 20, "target_ann": 0.15, "cap": 1.0, "floor": "none", "rebalance": "daily", "exposure_basis": "total"}),
            "estimator": "sma20", "instrument_book": "CME_micro_ES", "rebalance": "daily", "no_trade_band": 0.0, "fill_model": "NYSE_moc",
            "nav_fx": {**(c.get("nav_fx") or {"series": "USDKRW_1530_SNAPSHOT", "history": "ECOS_1530_CLOSE"}), "conversion_instant": None, "role": "forward_sim"},
            "roll_calendar": {"rule": "roll_before_expiry_fixed_calendar", "calendar": None},
            "data": {"source": "French_daily_MktRF_RF", "value_status": "official_close", "history_file": None},
            "history_first_close": start, "data_span": {"start": start, "end": end},
            "cash_convention": {"returns": "excess", "cash_series": "US_RF"},
            "start_band": {"shape": "decade_spaced", "step": "decade", "starts": 10, "require": {"no_reject": True, "pass_share_min": "4/5"}},
            "midpoint_halves": {"split": "calendar_midpoint", "split_date": calendar_midpoint(start, end), "require": "no_reject"},
            "primary_oos_line": "full_span", "comparator": "S_same_average_exposure",
            "timing_inputs": {"SPX": {"series": "SPX_OFFICIAL_CLOSE", "value_status": "official_close"}},
            "outcomes": {"PASS": "promotion only with a US sleeve, the settling run and the v2 package (L3092-3095)", "INSUFFICIENT_DATA": "FORWARD_SIM", "REJECT": "FORWARD_SIM"},
            "owner_decisions": {"sleeves.US.line": _get(store, "sleeves.US.line", "none")}}


_BUILDERS = {"MACRO-R06-KR-ETF": _r06_kr, "MACRO-R03-US-MOM": _r03, "MACRO-R14-MULTI-TREND": _r14,
             "MACRO-R31-KR-ETF": _r31, "MACRO-R28-US-TREND": _r28, "MACRO-R06-US-FUT": _r29}


def draft_header(card_id: str, store: MacroStore | None = None, *, revision: int | None = None) -> dict:
    """The section 8.4 header of a registered step-4 card with typed nulls for every missing owner input, freeze,
    ledger or fixture value (`owner_nulls` names them). Field values follow brief B2; UNSPEC cells use the brief's
    proposals, listed in `CardSpec.proposed`."""
    spec = BY_ID[card_id]
    if card_id not in _BUILDERS:
        raise CardRefused([f"{card_id}: not a step-4 header (section 8.1.3; {spec.conditions})"])
    rev = spec.revisions[0] if revision is None else revision
    if rev not in spec.revisions:
        raise CardRefused([f"{card_id}: revision {rev} is not registered {spec.revisions}"])
    h = _common(spec, store, revision=rev)
    body = _BUILDERS[card_id](store, rev)
    h["costs"].update(body.pop("costs_extra", {}))
    h["printed_lines"] = h["printed_lines"] + body.pop("printed_lines_extra", [])
    h["timing"]["inputs"] = body.pop("timing_inputs")
    h.update(body)
    return h


def _nulls(node, path="") -> list[str]:
    out = []
    if node is None:
        return [path]
    if isinstance(node, Mapping):
        for k, v in node.items():
            out += _nulls(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += _nulls(v, f"{path}[{i}]")
    return out


def owner_nulls(header: Mapping, *, skip: Sequence[str] = ()) -> dict[str, str]:
    """Every typed null of a draft with the reason the commit is refused (a null outside NULL_REASONS is unexplained,
    which is itself a refusal). `label: null` is a legal value (schema), never a typed null; `skip` names the
    fields the commit itself fills (VOLATILE_AT_COMMIT)."""
    out = {}
    for path in _nulls(dict(header)):
        if path in skip or path in ("label", "start_band", "midpoint_halves", "gating_lines", "claim_lines", "pooling_rule",
                                    "live_feeds", "nav_fx", "roll_calendar",
                                    "instrument_lines" if header.get("instrument_book") != "multi_line" else ""):
            continue
        out[path] = NULL_REASONS.get(path, "UNEXPLAINED: a null with no recorded reason is refused")
    return out


def draft_md5(header: Mapping) -> str:
    """md5 of the header fields without the package citation and the commit-time values (L4815; F-02)."""
    return md5_hex(canonical_json({k: v for k, v in header.items() if k in HEADER_FIELDS and k not in VOLATILE_AT_COMMIT}))


def next_header(previous: Mapping, changes: Mapping, *, new_card_id: str | None = None) -> dict:
    """A changed header is a new record: a class, threshold, window, estimator, cash-convention, start-band or
    episode-rule change is `revision + 1` under the same card id; a claim, instrument-book, rebalance, band or
    venue change is a new card id (L4890-4894, DNB 23/32). The previous header is never edited."""
    new_card = [k for k in changes if k in NEW_CARD_FIELDS and changes[k] != previous.get(k)]
    if new_card and not new_card_id:
        raise CardRefused([f"{previous.get('card_id')}: a change of {new_card} is a new card, not a revision; give new_card_id"])
    h = {**dict(previous), **dict(changes)}
    if new_card:
        h["card_id"], h["revision"] = new_card_id, 1
    else:
        h["revision"] = int(previous.get("revision") or 0) + 1
    for k in VOLATILE_AT_COMMIT:
        h[k] = None if k not in ("gate_package_version",) else previous.get(k)
    return h


# --------------------------------------------------------------------------- #
# Paths and chains
# --------------------------------------------------------------------------- #
def header_path(root, card_id: str, revision: int) -> Path:
    return Path(root) / "headers" / f"{card_id}.r{int(revision)}.header.json"


def draft_path(root, card_id: str, revision: int) -> Path:
    return Path(root) / "headers" / f"{card_id}.r{int(revision)}.draft.json"


def card_path(root, card_id: str, revision: int) -> Path:
    return Path(root) / "cards" / f"{card_id}.r{int(revision)}.json"


def verdicts_path(root) -> Path:
    return Path(root) / "cards" / "verdicts.jsonl"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def chain_rows(path) -> list[bytes]:
    p = Path(path)
    if not p.exists():
        return []
    rows = p.read_bytes().split(b"\n")
    return [r for r in rows if r != b""]


def chain_append(path, row: dict) -> str:
    """Append one canonical JSON line whose `prev_row_md5` is the md5 of the previous line's bytes (null first).
    Binary append, LF only, fsync; raises on failure. Returns the md5 of the written line."""
    p = Path(path)
    rows = chain_rows(p)
    row = dict(row)
    row["prev_row_md5"] = md5_hex(rows[-1]) if rows else None
    line = canonical_json(row).encode("utf-8")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "ab") as fh:
        fh.write(line + b"\n")
        fh.flush()
        os.fsync(fh.fileno())
    return md5_hex(line)


def chain_verify(path, required: Sequence[str] = ()) -> G.ChainCheck:
    """Re-hash every line; a hand edit, a reformat, a dropped line or a missing required field breaks the chain."""
    prev, n = None, 0
    for lineno, raw in enumerate(chain_rows(path), start=1):
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return G.ChainCheck(False, n, lineno)
        if (not isinstance(row, dict) or row.get("prev_row_md5") != prev or canonical_json(row).encode("utf-8") != raw
                or any(k not in row for k in required)):
            return G.ChainCheck(False, n, lineno)
        prev, n = md5_hex(raw), n + 1
    return G.ChainCheck(True, n, None)


def read_chain(path, required: Sequence[str] = ()) -> list[dict]:
    check = chain_verify(path, required)
    if not check.ok:
        raise CardRefused([f"chain broken at line {check.first_bad_line}: {path}"])
    return [json.loads(raw.decode("utf-8")) for raw in chain_rows(path)]


# --------------------------------------------------------------------------- #
# Commit (section 8.1.3 step 4; T-CARD-01)
# --------------------------------------------------------------------------- #
def package_block(store: MacroStore) -> dict:
    return store.get("gate.package")


def package_frozen(store: MacroStore, macro_dir=None) -> bool:
    """`gate_package.package_state(store, macro_dir) == "FROZEN"` (one home; BLOCKED after two failed attempts)."""
    from core.quant import gate_package as GP            # lazy: gate_package imports this module
    return GP.package_state(store, macro_dir) == "FROZEN"


def committed_headers(root) -> list[dict]:
    out = []
    for p in sorted((Path(root) / "headers").glob("*.header.json")):
        h = json.loads(p.read_text(encoding="utf-8"))
        if header_md5(h) != h.get("header_md5"):
            raise CardRefused([f"{p.name}: committed header re-hashes to {header_md5(h)} != {h.get('header_md5')} (T-CARD-01)"])
        out.append(h)
    return out


def load_header(root, card_id: str, revision: int) -> dict:
    """The committed header; re-hashed on every read, a mismatch is refused (T-CARD-01)."""
    p = header_path(root, card_id, revision)
    if not p.exists():
        raise CardRefused([f"{card_id}.r{revision}: no committed header at {p}"])
    h = json.loads(p.read_text(encoding="utf-8"))
    if header_md5(h) != h.get("header_md5"):
        raise CardRefused([f"{card_id}.r{revision}: header md5 {header_md5(h)} differs from the committed {h.get('header_md5')}"])
    return h


def commit_preconditions(draft: Mapping, store: MacroStore, anchor: str | None, *, macro_dir=None) -> list[str]:
    """The three refusal groups checked before anything else: the package is not frozen (`gate_package.package_state`:
    NOT_FROZEN, or BLOCKED after two failed acceptance attempts under `macro_dir`), the anchor is UNVERSIONED
    (ruling 3.1: 'owner must place the repository under git'), an owner input is null."""
    reasons = []
    pkg = package_block(store)
    if not package_frozen(store, macro_dir):
        from core.quant import gate_package as GP
        reasons.append(f"NOT_FROZEN: gate.package.status is {pkg.get('status')!r} (definitions_md5 {pkg.get('definitions_md5')!r}; "
                       f"package state {GP.package_state(store, macro_dir)}); no header is committed before the freeze (P11, L4821)")
    if not anchor or anchor == MA.GIT_HASH:
        reasons.append("UNVERSIONED: owner must place the repository under git (an external, timestamped anchor; ruling 3.1, L4820)")
    for path, why in owner_nulls(draft, skip=VOLATILE_AT_COMMIT).items():
        reasons.append(f"NULL {path}: {why}")
    return reasons


def ledger_state(ledger, family_id: str) -> tuple[str, int]:
    """(family hash, N_raw) from the R-23 ledger: a `{family_id: FamilyLedger}` mapping or one `FamilyLedger`
    (core.quant.gate_ledger: `.hash()`, `.n_raw`), or any object answering `hash(family_id)` / `n_raw(family_id)`."""
    fl = ledger[family_id] if isinstance(ledger, Mapping) else ledger
    if getattr(fl, "family_id", None) is not None or isinstance(ledger, Mapping):
        if getattr(fl, "family_id", family_id) != family_id:
            raise CardRefused([f"ledger of family {getattr(fl, 'family_id')!r} offered for {family_id}"])
        n = fl.n_raw
        return str(fl.hash()), int(n() if callable(n) else n)
    return str(fl.hash(family_id)), int(fl.n_raw(family_id))


def commit_header(draft: Mapping, store: MacroStore, ledger, clock: Clock, anchor: str | None, *, root, governance_log,
                  acceptance_draft_md5: str | None = None, rule: RuleObject | None = None, macro_dir=None) -> dict:
    """Commit one header blind (section 8.1.3 step 4). Refuses (CardRefused, nothing written) on any of: package not
    frozen (PackageNotFrozen), anchor UNVERSIONED, a typed null, a package citation other than the frozen one,
    validate_card_header issues (schema, R-26, DNB shapes, owner decisions at commit), a CARD-P draft md5 that
    differs from `acceptance_draft_md5`, the 8-parameter budget, or an existing header (immutable). Otherwise sets
    created_utc, gate_package_md5, ledger_hash_at_registration, N_raw_at_registration and header_md5, writes
    headers/<card_id>.r<rev>.header.json and appends a `header_commit` governance event. `ledger` is the R-23 family
    ledger: `{family_id: gate_ledger.FamilyLedger}` (the runner's `macro_dir/ledgers/<family>.jsonl`), one
    `FamilyLedger`, or any object answering `hash(family_id)` / `n_raw(family_id)`. The twelve R-26 checks run
    inside `validate_card_header` (`instruments.header_checks`)."""
    reasons = commit_preconditions(draft, store, anchor, macro_dir=macro_dir)
    if reasons:
        raise (PackageNotFrozen if reasons[0].startswith("NOT_FROZEN") else CardRefused)(reasons)
    spec = BY_ID.get(draft["card_id"])
    pkg = package_block(store)
    h = dict(draft)
    h["gate_package_version"] = pkg["version"]
    h["gate_package_md5"] = pkg["definitions_md5"]
    h["checks"] = f"gate_package_{pkg['version']}"
    h["created_utc"] = MA.utc_stamp(clock())
    h["ledger_hash_at_registration"], h["N_raw_at_registration"] = ledger_state(ledger, h["family_id"])
    h["header_md5"] = header_md5(h)
    if draft.get("gate_package_md5") not in (None, pkg["definitions_md5"]) or draft.get("gate_package_version") != pkg["version"]:
        reasons.append(f"PACKAGE: the draft cites package {draft.get('gate_package_version')!r} / {draft.get('gate_package_md5')!r}, "
                       f"the frozen package is {pkg['version']} / {pkg['definitions_md5']} (L2244)")
    report = validate_card_header(h, store, rule=rule or (rule_object(h["card_id"]) if spec else None),
                                  acting_long_sample=spec.acting_long_sample if spec else True)
    reasons += [f"{i.field}: {i.message}" for i in report.errors]
    if h.get("instrument_book") == "multi_line":
        from core.quant.instruments import INSTRUMENT_BOOKS
        stock = [ln.get("instrument_book") for ln in (h.get("instrument_lines") or []) if isinstance(ln, dict)
                 and getattr(INSTRUMENT_BOOKS.get(ln.get("instrument_book")), "kind", None) == "stock"]
        if stock:
            reasons.append(f"instrument_lines: a multi_line card is index, futures or ETF lines, never a stock book {stock} (L1702)")
    if h["class"] == "CARD-P" and acceptance_draft_md5 is not None and draft_md5(h) != acceptance_draft_md5:
        reasons.append(f"DRAFT: a CARD-P header must match its step-2 acceptance draft (L4826): {draft_md5(h)} != {acceptance_draft_md5}")
    budget = store.get("gate.parameter_budget_searched")
    searched = sum(len(x.get("searched_parameters") or ()) for x in committed_headers(root)) + len(h.get("searched_parameters") or ())
    if searched > budget:
        reasons.append(f"BUDGET: {searched} searched parameters over all macro cards > gate.parameter_budget_searched {budget} (L4896)")
    target = header_path(root, h["card_id"], h["revision"])
    if target.exists():
        reasons.append(f"IMMUTABLE: {target.name} exists; a committed header is never edited (L4876)")
    if reasons:
        if not report.ok:                                      # section 10.3: the refusal is logged with its item and label
            log_refusal(Path(governance_log).parent / REFUSAL_LOG, RuleObject(h.get("rule_id") or "", h.get("class") or "",
                                                                              card_id=h["card_id"]), report, clock)
        raise CardRefused(reasons)
    _write(target, canonical_json(h))
    G.append_event(Path(governance_log), {"kind": "header_commit", "book_id": None, "rule_id": h["rule_id"], "key": h["card_id"],
                                          "old": None, "new": h["header_md5"], "actor": "harness",
                                          "reason": f"section 8.1.3 step 4: {h['card_id']} r{h['revision']} committed blind under package "
                                                    f"{pkg['version']} {pkg['definitions_md5']}; anchor {anchor}",
                                          "refs": ["section 8.1.3 step 4", f"ledger:{h['ledger_hash_at_registration']}"]}, clock)
    return h


# --------------------------------------------------------------------------- #
# Disposition, status, revisions (section 6.2 card object; L4089)
# --------------------------------------------------------------------------- #
def disposition_for(header: Mapping, verdict: str, *, binding_share: float | None = None) -> tuple[str, str]:
    """(disposition, displayed_as) of brief B1: PASS -> RECOMMENDATION / BUILD_AS_INSURANCE; an R-31 step at a frozen
    share <= 0.10 -> INVARIANT_STEP (no PASS needed); R-28 / R-29 -> FORWARD_SIM; R-11 / R-12 -> REFUSAL_BOOK; a non-PASS
    factor held in the specification book -> SPECIFICATION_ONLY; everything else DESCRIPTIVE."""
    fam, rid = header.get("family_id", ""), header.get("rule_id", "")
    if verdict == "PASS":
        if header.get("build_status_on_pass") == "BUILD_AS_INSURANCE":
            return "BUILD_AS_INSURANCE", "insurance"
        return "RECOMMENDATION", "recommendation"
    if fam == "R-31" and binding_share is not None and binding_share <= 0.10 + 1e-12:
        return "INVARIANT_STEP", "invariant"
    if fam in ("R-28",) or header.get("card_id") == "MACRO-R06-US-FUT":
        return "FORWARD_SIM", "descriptive"
    if fam in ("R-11", "R-12") or rid.startswith(("R-11", "R-12")):
        return "REFUSAL_BOOK", "refusal"
    if fam in ("R-31", "R-04") or (fam == "R-06" and header.get("card_id") == "MACRO-R06-KR-ETF" and verdict in (NOT_RUN, "INSUFFICIENT_DATA")) \
            or rid.startswith("R-04"):
        return "SPECIFICATION_ONLY", "descriptive"
    return "DESCRIPTIVE", "descriptive"


def check_display_invariant(verdict: str, disposition: str, displayed_as: str) -> list[str]:
    """`disposition in {RECOMMENDATION, BUILD_AS_INSURANCE}` iff verdict == PASS; `displayed_as in {recommendation,
    insurance}` iff PASS and that disposition (L3764-3765, L4089)."""
    out = []
    if (disposition in PASS_DISPOSITIONS) != (verdict == "PASS"):
        out.append(f"disposition {disposition} with verdict {verdict}: a non-PASS card is never a recommendation (DNB 22)")
    if (displayed_as in ("recommendation", "insurance")) != (verdict == "PASS" and disposition in PASS_DISPOSITIONS):
        out.append(f"displayed_as {displayed_as} with verdict {verdict} / {disposition}")
    return out


def registered_reject(store: MacroStore | None = None) -> dict:
    """The R-06 US 50 bp card as a record, not a run: the verbatim instrument label, `rerun: False` (L1575, L4291)."""
    reg = _get(store, "vol_target.US.registered_card") or {"instrument_book": "US_shares_KIS", "verdict": "REJECT",
                                                            "label": US_REJECT_LABEL, "rerun": False}
    return {"card_id": "MACRO-R06-US", "class": "CARD-P", "verdict": reg["verdict"], "disposition": "DESCRIPTIVE",
            "displayed_as": "descriptive", "label": reg["label"], "results_md5": None, "rerun": bool(reg.get("rerun", False)),
            "instrument_book": reg["instrument_book"]}


def card_status(root, card_id: str, store: MacroStore | None = None) -> dict:
    """The section 6.2 card object {card_id, class, verdict, disposition, displayed_as, label, results_md5}: from the
    highest committed card file when one exists, else NOT_RUN from the registry (the registered US card: REJECT)."""
    spec = BY_ID[card_id]
    if card_id == "MACRO-R06-US":
        return registered_reject(store)
    files = sorted(card_path(root, card_id, 0).parent.glob(f"{card_id}.r*.json")) if root else []
    if files:
        card = json.loads(files[-1].read_text(encoding="utf-8"))
        if results_md5(card) != card.get("results_md5"):
            raise CardRefused([f"{files[-1].name}: results_md5 mismatch (R-35 check (i))"])
        d, s = disposition_for(card, card["verdict"])
        return {"card_id": card_id, "class": card["class"], "verdict": card["verdict"], "disposition": card.get("disposition", d),
                "displayed_as": s, "label": card.get("label"), "results_md5": card["results_md5"]}
    return {"card_id": card_id, "class": spec.cls, "verdict": spec.verdict, "disposition": spec.disposition,
            "displayed_as": spec.displayed_as, "label": spec.label, "results_md5": None}


def list_cards(root=None, store: MacroStore | None = None) -> list[dict]:
    out = []
    for spec in REGISTRY:
        row = {**card_status(root, spec.card_id, store), "family_id": spec.family_id, "rule_id": spec.rule_id, "market": spec.market,
               "instrument_book": spec.instrument_book, "build_status": spec.build_status, "revisions": list(spec.revisions),
               "step4_header": spec.step4_header, "rerun": spec.rerun, "data_sources": list(spec.data_sources),
               "notional": {"ref": spec.notional_ref} if spec.notional_ref else None, "conditions": list(spec.conditions),
               "proposed": list(spec.proposed)}
        if spec.step4_header:
            row["owner_nulls"] = owner_nulls(draft_header(spec.card_id, store))
        out.append(row)
    return out


def acting_revision(root, card_id: str) -> int | None:
    """The lowest PASSing registered revision (R-03 rule, L1519); None when no revision PASSes."""
    revs = []
    for p in sorted(card_path(root, card_id, 0).parent.glob(f"{card_id}.r*.json")):
        card = json.loads(p.read_text(encoding="utf-8"))
        if card.get("verdict") == "PASS":
            revs.append(int(card["revision"]))
    return min(revs) if revs else None


# --------------------------------------------------------------------------- #
# Cards, verdicts.jsonl, archive (R-35; TASK-M7-19/20)
# --------------------------------------------------------------------------- #
def _finite(node):
    if isinstance(node, float) and not math.isfinite(node):
        return None
    if isinstance(node, Mapping):
        return {k: _finite(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_finite(v) for v in node]
    return node


def write_card(root, header: Mapping, results: Mapping, clock: Clock, *, store: MacroStore | None = None) -> Path:
    """card = committed header U results, validated against model_card.macro (closed); non-finite numbers written as
    null; results_md5 over the result fields minus the volatile ones; the display invariant asserted. Written only
    through macro_artifacts.write_artifact (an invalid card is quarantined and refused, never partially written)."""
    card = {k: v for k, v in header.items() if k in HEADER_FIELDS}
    card.update({k: _finite(v) for k, v in results.items() if k in RESULT_FIELDS})
    card.update({"schema": "quantgen.model_card.macro", "schema_version": "2.0", "read_only": True})
    card.setdefault("git_hash", MA.GIT_HASH)
    card.setdefault("tree_hash", MA.tree_hash())                  # ruling 3.1 (volatile: never in results_md5)
    reasons = check_display_invariant(card.get("verdict"), card.get("disposition"),
                                      disposition_for(card, card.get("verdict", ""))[1])
    if card.get("verdict") not in VERDICTS:
        reasons.append(f"verdict {card.get('verdict')!r}: NOT_RUN is a card state, never written to a card file (F-14)")
    card["results_md5"] = results_md5(card)
    spec = BY_ID.get(card.get("card_id"))
    reasons += card_issues(card, committed_header=dict(header), acting_long_sample=spec.acting_long_sample if spec else True,
                           seed_study=_get(store, "reproducibility.seed_study"))
    if reasons:
        MA.quarantine(root, "model_card.macro", card, reasons, clock)     # R-32 L3370: the audit trail keeps it
        raise CardRefused(reasons)
    return MA.write_artifact(root, "model_card.macro", card, clock, relpath=f"cards/{card['card_id']}.r{int(card['revision'])}.json")


def append_verdict(root, card: Mapping) -> dict:
    """One hash-chained row of cards/verdicts.jsonl (R-35 R2-C4): the eleven fields of VERDICT_ROW."""
    disp, _ = disposition_for(card, card["verdict"])
    row = {k: card.get(k) for k in VERDICT_ROW if k not in ("prev_row_md5", "disposition")}
    row["disposition"] = card.get("disposition", disp)
    if results_md5(card) != card.get("results_md5"):
        raise CardRefused([f"{card.get('card_id')}: results_md5 does not re-hash; no verdict row"])
    chain_append(verdicts_path(root), row)
    return read_chain(verdicts_path(root), VERDICT_ROW)[-1]


def verify_verdict_chain(root) -> G.ChainCheck:
    return chain_verify(verdicts_path(root), VERDICT_ROW)


def rederive_snapshot_id(rows: Sequence[Mapping]) -> str:
    """md5 of the sorted content hashes (L5616) = core.ficc.pit.data_snapshot_id over the same rows."""
    return MA.data_snapshot_id([r["content_hash"] for r in rows])


def archive_dir(root, card: Mapping) -> Path:
    return Path(root) / "archive" / f"{card['card_id']}.r{int(card['revision'])}"


def archive_snapshot(root, card: Mapping, rows: Sequence[Mapping]) -> Path:
    """Archive the store rows behind the card's data_snapshot_id: rows.jsonl sorted by content hash, one canonical
    line each, plus MD5LIST (section 9.4 item 16). Refused when the rows do not re-derive the card's snapshot id."""
    got = rederive_snapshot_id(rows)
    if got != card.get("data_snapshot_id"):
        raise CardRefused([f"{card.get('card_id')}: archived rows re-derive {got}, card says {card.get('data_snapshot_id')}"])
    d = archive_dir(root, card)
    text = "".join(canonical_json(dict(r)) + "\n" for r in sorted(rows, key=lambda r: r["content_hash"]))
    _write(d / "rows.jsonl", text)
    _write(d / "MD5LIST", f"{md5_hex(text)}  rows.jsonl\n{card['results_md5']}  {card['card_id']}.r{int(card['revision'])}.json\n")
    return d


def verify_archive(root, card: Mapping) -> list[dict]:
    """The archived rows of a card; a lost or altered archive is an integrity failure (ArchiveLost), never a reason
    to re-run silently (L6013)."""
    d = archive_dir(root, card)
    rows_path, md5_path = d / "rows.jsonl", d / "MD5LIST"
    if not rows_path.exists() or not md5_path.exists():
        raise ArchiveLost([f"{card.get('card_id')}: archive missing at {d} (VERDICT_INTEGRITY; the factor leaves the recommended book)"])
    text = rows_path.read_text(encoding="utf-8")
    listed = dict(line.split("  ", 1) for line in md5_path.read_text(encoding="utf-8").splitlines() if "  " in line)
    if listed.get(md5_hex(text)) != "rows.jsonl":
        raise ArchiveLost([f"{card.get('card_id')}: rows.jsonl md5 not in MD5LIST (altered archive)"])
    rows = [json.loads(line) for line in text.splitlines() if line]
    if rederive_snapshot_id(rows) != card.get("data_snapshot_id"):
        raise ArchiveLost([f"{card.get('card_id')}: archived rows re-derive a different data_snapshot_id"])
    return rows


# --------------------------------------------------------------------------- #
# Stack CARD-P generator (R-02 rule 6; section 8.7; TASK-M7-29)
# --------------------------------------------------------------------------- #
INVARIANT_RULES = ("R-01", "R-02", "R-07", "R-09", "R-19", "R-20", "R-26")


def is_de_risk_factor(f: Mapping) -> bool:
    """A market-level (`exposure_basis: total`) factor carried by a PASS card that can take a value < 1.0 in the
    recommended book (L1506 (6)): vt (R-06 KR), R-28, R-29, R-31 steps once their card PASSes. Not: caps, the hard
    stop, the post-re-arm cap (invariants), INVARIANT_STEP steps, family-level vs."""
    card = f.get("card") or {}
    return (f.get("exposure_basis") == "total" and f.get("rule_id", "").split("-")[0:2] != [] and
            not any(f.get("rule_id", "").startswith(r) for r in INVARIANT_RULES) and
            card.get("verdict") == "PASS" and card.get("disposition") in PASS_DISPOSITIONS and f.get("disposition") != "INVARIANT_STEP")


def maybe_generate_stack_card(market: str, joining: Sequence[Mapping], recommended_book: Sequence[Mapping], *,
                              store: MacroStore | None = None) -> dict | None:
    """Before a second (or further) de-risk factor joins a market's recommended book, the stack CARD-P header draft
    (status NOT_RUN): (b) the composed book vs the invariants-only book, S = that book x the stack's mean multiplier.
    Returns None while fewer than `overlay.stack_card.when_de_risk_factors_ge` de-risk factors would act (dormant
    today). A product composition is refused (DNB 31)."""
    cfg = _get(store, "overlay.stack_card", {"when_de_risk_factors_ge": 2, "class": "CARD-P", "spec": "section 8.7"})
    for f in [*joining, *recommended_book]:
        if f.get("composition", "min") != "min":
            raise CardRefused([f"{f.get('rule_id')}: composition {f.get('composition')!r}; a product-composed stack is refused (DNB 31)"])
    acting = [f for f in recommended_book if is_de_risk_factor(f)]
    new = [f for f in joining if is_de_risk_factor(f)]
    if not new or len(acting) + len(new) < cfg["when_de_risk_factors_ge"]:
        return None
    order = sorted([*acting, *new], key=lambda f: (f.get("header_commit_utc") or "", f.get("rule_id", "")))
    spec = BY_ID["MACRO-STACK-KR"]
    h = _common(spec, store, revision=1)
    h.update({"card_id": f"MACRO-STACK-{market}", "rule_id": f"R-02-STACK-{market}", "claim": "the composed de-risk stack lowers tail losses vs "
              "the invariants-only book; composition by min(); not expected to outperform", "claim_type": "protection",
              "build_status_on_pass": "BUILD_AS_INSURANCE", "hypothesis": "vt x min(overlays, ladder, post_rearm_cap) with the hard stop and caps "
              "applied lowers tail losses vs the invariants-only book", "mechanism": "min() of second-moment factors",
              "rule": "composed = vt x min(1.0, overlay_1..k, ladder, post_rearm_cap); gross = min(composed, concentration_bound)",
              "parameters": {"factors": [f["rule_id"] for f in order], "composition": "min", "join_order": "header_commit"},
              "estimator": "sma20", "instrument_book": spec.instrument_book if market == "KR" else "CME_micro_ES", "rebalance": "daily",
              "no_trade_band": 0.0, "fill_model": "KRX_close_auction" if market == "KR" else "NYSE_moc",
              "data": {"source": "recommended_book_composition", "value_status": "official_close"},
              "history_first_close": _get(store, f"gate.evaluation.history_start.{market}", "1997-04-01"),
              "data_span": {"start": "first_close_plus_estimator_warmup", "end": None},
              "cash_convention": {"returns": "excess", "cash_series": _get(store, f"gate.evaluation.cash.{market}", "BOK_CALL_RATE")},
              "start_band": None, "midpoint_halves": None, "primary_oos_line": "full_span", "comparator": "S_same_average_exposure",
              "benchmarks": ["buy_and_hold", "overlay_off", "static_same_avg_exposure", "ewma_derisk", "current_recommended_book"],
              "printed_lines": h["printed_lines"] + ["low_exposure_share_le_0p25", "rebound_capture", "binding_shares", "with_risk_layer"],
              "outcomes": {"PASS": "the joining factor acts (both (a) and (b) PASS)", "INSUFFICIENT_DATA": "specification_book_labelled_with_stack_verdict",
                           "REJECT": "specification_book_labelled_with_stack_verdict"},
              "notional_nav": _get(store, f"sleeves.{market}.notional_nav"), "label": DEFAULT_CARDP_LABEL,
              "stack": {"status": NOT_RUN, "joining": [f["rule_id"] for f in new], "acting": [f["rule_id"] for f in acting],
                        "judged": ["(a) joining factor incremental on the current recommended book", "(b) composed book vs invariants-only"],
                        "own_panels_at_commit": "rule 9(a): 300 shifted + 20 per-card placebos, md5-frozen with the header"}})
    h["timing"]["inputs"] = {"book": {"series": "recommended_book", "value_status": "official_close"}}
    return h


def referenced_series_ids(root=None, store: MacroStore | None = None) -> set[str]:
    """Every series or group id the headers name (timing.inputs[*].series, cash_series, nav_fx series / history):
    from the files under <root>/headers when given, else from the drafts of the registry. T-SER-02 scans them."""
    heads: list[dict] = []
    if root is not None and (Path(root) / "headers").is_dir():
        heads = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((Path(root) / "headers").glob("*.json"))]
    else:
        heads = [draft_header(s.card_id, store, revision=r) for s in REGISTRY if s.step4_header for r in s.revisions]
    ids: set[str] = set()
    for h in heads:
        ids |= {v.get("series") for v in (h.get("timing") or {}).get("inputs", {}).values() if isinstance(v, dict)}
        ids.add((h.get("cash_convention") or {}).get("cash_series"))
        fx = h.get("nav_fx") or {}
        ids |= {fx.get("series"), fx.get("history")}
    return {i for i in ids if i}


# --------------------------------------------------------------------------- #
# Drafts on disk
# --------------------------------------------------------------------------- #
def write_drafts(root, store: MacroStore | None = None) -> list[Path]:
    """headers/<card_id>.r<rev>.draft.json for every step-4 card and revision (typed nulls kept)."""
    out = []
    for spec in REGISTRY:
        if not spec.step4_header:
            continue
        for rev in spec.revisions:
            p = draft_path(root, spec.card_id, rev)
            _write(p, json.dumps(draft_header(spec.card_id, store, revision=rev), indent=1, ensure_ascii=False, sort_keys=True) + "\n")
            out.append(p)
    return out
