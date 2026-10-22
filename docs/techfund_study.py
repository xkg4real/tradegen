"""Tech-fund card runner (Sprint 7, package C): the tech-fund card drafts and the CRY-1 controls of card C3.

    python docs/techfund_study.py                    # list the tech-fund cards and why each run is refused here
    python docs/techfund_study.py --write-drafts     # docs/techfund/<card>.draft.json (typed nulls)
    python docs/techfund_study.py --run SCR-1        # refused: the KRX all-stock panel is absent (exit 2)
    python docs/techfund_study.py --cry1 [--ledger-dir DIR] [--out DIR] [--run-utc ISO]

Rulings 3.8: SCR-1 / SCR-2 (CARD-O screen cards, G-01 / G-02) and the FORWARD-SIM cells FS-1..FS-5 (G-30..G-34) are
evaluated by the existing nine-step gate with the GOV amendments as tightenings; they need the KRX all-stock panel
(or the KOSPI official closes, or a composite card), so every run is NOT_RUN and this runner refuses it, prints the
reason and writes nothing. Their drafts carry typed nulls (`nulls`: path -> REFDATA / OWNER / PENDING reason).
Each draft is checked as a section 7.1 rule object (`rule_object` / `dnb_issues`: the Council's 17 shapes and the
store's DNB-TF-01..17 over the `tf_books.CARD_RULES` descriptor; a hit is the refusal reason) and against the Council
header schema where the fields overlap (`header_overlap`; the fields that closed schema refuses are declared in
docs/techfund/SCHEMA_AMENDMENT.md, the schema is not loosened).

CRY-1 (G-29, CR-10) is the only runnable item: on the local vendor caches (`docs/asset_expansion/cache`:
binance_BTCUSDT, upbit_KRW-BTC, binance_ETHUSDT) it runs card C3's rule (`strategies.crypto_trend`, the hysteresis
lattice, 10 bp per side, embargo 1) through `validate.walk_forward` / `score_strategy` and adds (a) a vol-scaled
long-only control, (b) the pre-registered split at 2024-01-10, (c) an ETH replication; the cut-time test needs
intraday candles and is NOT_RUN. The three additions are registered as trials of C3 in the trial registry
(R-23 family ledgers, `--ledger-dir`, default `<macro_dir>/ledgers`). Results are labelled trials on vendor data,
never a formal card run: C3's stored verdict and `docs/asset_expansion/cards` are never touched (D-24).
"""
from __future__ import annotations

import os
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):   # single-threaded BLAS before numpy
    os.environ.setdefault(_v, "1")

import argparse                                                  # noqa: E402
import dataclasses                                               # noqa: E402
import json                                                      # noqa: E402
import math                                                      # noqa: E402
import tempfile                                                  # noqa: E402
from datetime import datetime, timezone                          # noqa: E402
from pathlib import Path                                         # noqa: E402

import numpy as np                                               # noqa: E402
import pandas as pd                                              # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ficc import macro_schema as MS                         # noqa: E402
from core.quant import strategies as S                           # noqa: E402
from core.quant import tf_books as TB                            # noqa: E402
from core.quant import tf_gov as TG                              # noqa: E402
from core.quant import validate as V                             # noqa: E402
from core.rules import macro_rules as M                          # noqa: E402

OUT = ROOT / "docs" / "techfund"
CACHE = ROOT / "docs" / "asset_expansion" / "cache"
C3_CARD = ROOT / "docs" / "asset_expansion" / "cards" / "S_C3_crypto_trend_krwbtc.json"   # read only
FIXTURES = ROOT / "tests" / "fixtures" / "macro"
KRX_PANEL = ROOT / "data" / "techfund" / "marcap"     # the marcap yearly files (tests/macro_tf_screens.KRX_PANEL_PATHS)
KOSPI_FIXTURE = "krx_kospi_official_close_1997-01-03_2026-10-02.csv"            # F01 (macro MARKET_FIXTURES["KR"])

SEED = 11
B = 2000                                       # the gate's resamples; the run refuses a mutated validate.GATE
COST = V.COST_BP_PER_SIDE["crypto"]            # 10 bp per side, as card C3
C3_GRID = S.grid_from(hysteresis=[0.0, 0.222, 0.444, 0.667, 0.889])
C3_DOMAIN = {"hysteresis": (0.0, 0.889)}
C3_EMBARGO = 1
C3_HOLDING = 1                                 # GOV-4 floor 2 x holding = 2 sessions (dominated by 10)
SPLIT = "2024-01-10"                           # US spot-ETF date (R3:342), pre-registered
CONTROL = {"window": 22, "step": 1, "cap": 1.0, "band": 0.10}
FAMILY = "C3"
SERIES = {"binance_BTCUSDT": "vendor: Binance public daily close (USDT), not an official close",
          "upbit_KRW-BTC": "vendor: Upbit public daily close (KRW), not an official close",
          "binance_ETHUSDT": "vendor: Binance public daily close (USDT), not an official close"}
BTC_SERIES = ("binance_BTCUSDT", "upbit_KRW-BTC")
LABEL = "vendor data, labelled trial, not a formal card run"
LAB_LABEL = "lab, in sample, 1996-2026, price returns without dividends, rf 0; not a QUANTGEN gate result (D-31)"
PROPOSAL = "tech-fund values are proposals pending owner confirmation; Council v2.0 governs on conflict (rulings 3.7)"
BONFERRONI_NOTE = ("C3's step-5 p (0.038 KRW-BTC, 0.07 BTC-USD; cards of 2026-09-27) fails Bonferroni across the 16 "
                   "trading cards (0.10 / 16 = 0.00625; R3:291 prints 0.006); its Sharpe-vs-zero t 3.49 survives (P:L371). "
                   "Printed, not applied: C3 stays PASS (CR-10).")
CUT_TIMES = ("00:00 UTC", "00:00 KST", "21:00 UTC")
EXTRA_TRIALS = (("vol_scaled_long_only_control", {"addition": "vol_scaled_long_only_control", "tau": "c3_oos_realised_vol", **CONTROL}),
                ("split_2024-01-10", {"addition": "pre_registered_split", "split": SPLIT}),
                ("eth_replication", {"addition": "eth_replication", "series": "binance_ETHUSDT"}))


class CardRefused(RuntimeError):
    def __init__(self, card_id: str, reason: str) -> None:
        super().__init__(f"{card_id}: {reason}")
        self.card_id, self.reason = card_id, reason


# --------------------------------------------------------------------------- #
# KRX card drafts (SCR-1, SCR-2 CARD-O; FS-1..FS-5 FORWARD-SIM) and their refusal
# --------------------------------------------------------------------------- #
def _panel_reason() -> str:
    if KRX_PANEL.exists():
        return ("PENDING: data/techfund/marcap is present but no reviewed loader is written against its column layout; "
                "no vendor substitute (S5 deviation 7)")
    return ("REFDATA: KRX all-stock daily panel (marcap files 1995-2026: close, high, volume, amount, marcap, shares, "
            "market, name class; expected under data/techfund/marcap/) absent")


def refusal(card_id: str) -> str:
    """The typed reason a tech-fund card run is refused on this machine (every KRX card is NOT_RUN, rulings 3.8);
    a draft whose rule object meets a section 10 / DNB-TF shape is refused on that first (fail closed)."""
    if card_id not in DRAFTS:
        raise KeyError(f"unknown tech-fund card {card_id!r}; registered: {sorted(DRAFTS)}")
    dnb = dnb_issues(card_id)
    if dnb:
        return "DNB: " + "; ".join(dnb)
    if card_id == "FS-1":
        return (f"REFDATA: KRX official KOSPI closes ({KOSPI_FIXTURE}) / the rebuilt KOSPI are absent; the forward "
                "record starts at its first recorded session and is never back-filled (GOV-10)")
    if card_id == "FS-4":
        return "PENDING: no L0 composite card exists (ML-1, built with the first composite card); the ridge challenger runs after it"
    return _panel_reason()


def run_card(card_id: str):
    """Refuses every KRX card here (no panel, no formal run, nothing written)."""
    raise CardRefused(card_id, refusal(card_id))


def _gate_block(holding: int) -> dict:
    return {"gate": "nine-step gate, core.quant.validate (walk_forward 756/126, embargo = holding period)",
            "tightenings": ["GOV-1 long-only primary statistic vs the declared benchmark set (sign split EW / capped VW -> REVISE)",
                            "GOV-2 family gate if > 1 configuration (SPA consistent p <= 0.05 at 1x, BH q 0.10, persistence >= 60%)",
                            "GOV-4 block max(10, PW(d), PW(d^2), 2 x holding) for steps 2 and 5: the worse of it and the 10-session result",
                            "GOV-7 break-even pre-gate screen: REJECT if break-even < 2 x 35 bp",
                            "GOV-3 attribution block; GOV-9 stress table; GOV-5 minimum track record (reported)"],
            "holding_sessions": holding, "step8": "kept; 2-of-3 subperiods 1996-2005 / 2006-2015 / 2016-2026 reported (PX-T-05)",
            "step9": "expected live = 0.6 x OOS (reported, not gated)", "cpcv": "reported, not gating (GOV-10)"}


def _draft(card_id, cls, register_id, node, decision, ruling, build_status, hypothesis, rule, construction, *,
           holding=21, instrument_book="KRX_stock_book", lab_reference=None, settle=None, extra=None) -> dict:
    cost_key = "krx_etf" if instrument_book == "KRX_ETF_line" else "krx_stock"
    bp = V.COST_BP_PER_SIDE[cost_key]
    d = {"card_id": card_id, "class": cls, "register_id": register_id, "node": node, "register_decision": decision,
         "ruling": ruling, "build_status": build_status, "market": "KR", "instrument_book": instrument_book,
         "hypothesis": hypothesis, "rule": rule, "construction": construction,
         "costs": {"per_side": "read_from_gate", "floor": "tick_floor", "stress": 2.0, "stress_line": "printed",   # header form
                   "printed_lines": [f"{bp:g} bp per side (validate.COST_BP_PER_SIDE['{cost_key}'])",
                                     f"stress 2 x = {2 * bp:g} bp per side (printed)"]},
         "cost_detail": {"per_side_bp": bp, "stress_multiplier": 2.0,
                         "binding": "flat table rate until KIS quote calibration; an itemised total may only raise it (PX-T-07, D-28)",
                         "itemised": {"commission": None, "sell_tax": None, "half_tick_floor": None, "sqrt_impact": None}},
         "evaluation": _gate_block(holding),
         "attribution": {"factors": list(TG.FACTOR_SETS["KR"]), "tilt_threshold_t": TG.FACTOR_TILT_T, "status": TG.FACTOR_TILT_STATUS},
         "stress_windows": [w[0] for w in TG.STRESS_WINDOWS],
         "incubation": {"clock_start": str(TG.INCUBATION_START), "min_sessions": TG.INCUBATION_MIN_SESSIONS,
                        "first_recorded_session": None, "rule": "counted from the first recorded session, never back-filled"},
         "trials": {"N_registered": None}, "data_span": {"start": None, "end": None},
         "run_status": "NOT_RUN", "verdict": None, "blocked_by": None,
         "lab_reference": {"label": LAB_LABEL, "rows": lab_reference or []}, "what_would_change_it": settle,
         "proposal_status": PROPOSAL}
    d.update(extra or {})
    return d


def _nulls(d: dict, reason: str) -> dict:
    """Every null leaf of the draft with its typed reason (owner, reference data or the first formal run)."""
    out = {}

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{path}.{k}" if path else k)
        elif o is None:
            out[path] = ("OWNER: itemised cost inputs (sell-tax table, tick table, impact model) not signed" if ".itemised." in f".{path}."
                         else "PENDING: set at the first recorded forward session" if path.endswith("first_recorded_session")
                         else reason)
    walk({k: v for k, v in d.items() if k not in ("nulls", "lab_reference", "what_would_change_it")}, "")
    return out


def _screen_extra(break_even_ref: dict) -> dict:
    return {"comparator": "overlay_off", "comparator_text": "the unscreened base book on the same days (CR-06)",
            "base_books": {"B1": "EW ALL", "B2": "VW ALL capped 5%", "B3": "top-200 VW capped 5%", "B4": "MOM_12_1 top quintile EW"},
            "screen_weight_by_book": {"B1": 3, "B2": 1, "B3": 0, "B4": 3, "status": "prior (0-3), not a gate result (CR-06; D-26)"},
            "primary_statistic": "long_only_net_excess", "benchmarks": list(TG.BENCHMARK_SET_KRX),
            "sign_split_rule": "EW and capped-VW signs differ -> REVISE (GOV-1)", "long_short": "diagnostic only; short-leg share reported",
            "statistic_basis": "daily session differences (F-15 / C4-1); golden rows compared on the same basis only",
            "break_even": {"bp_per_side": None, "pre_gate_screen": "REJECT if < 2 x 35 bp (GOV-7)", "lab_reference": break_even_ref}}


def _drafts() -> dict[str, dict]:
    ref = TG.REFERENCE["SCR1_F4_B1"]
    scr1 = _draft("SCR-1", "CARD-O", "G-01", "TF-12", "BUILD NOW (screen card)", "CR-06", "SPECIFICATION_BOOK",
                  "excluding the worst decile of a volatility + MAX + turnover rank composite raises long-only net excess",
                  "F4: drop the worst 10% of rank(VOL_3M) + rank(MAX_1M) + rank(TURN_1M) at each monthly formation; same weighting rule",
                  "core.quant.tf_screens.p6_composite(vol_3m, max_1m, turn_1m, U, frac=0.10) -> screen_flags / screen_mask; "
                  "core.quant.tf_books.run_books(B1..B4 base and filtered books)",
                  lab_reference=[{"gv": "GV-001..004", "item": "B1 F4 gross / net 35 / net 70 %/yr; IR (monthly basis)", "value": "3.3884 / 3.0764 / 2.7645; IR 1.5295",
                                  "source": "r2_kr_excl_summary.csv lines 13 / 11 / 12"},
                                 {"gv": "G-TF-SCR-15", "item": "B1 F4 daily basis (QA recomputation)", "value": "3.43 / 3.12 / 2.80 %/yr; IR 1.64", "source": "qa_exact_costconv.json (not shipped)"},
                                 {"gv": "r2_kr_excl_gate.csv line 2", "item": "indicative 8-step gate", "value": "7 of 8, REVISE (pooled DSR 0.939 over 176 trials)", "source": "r2_kr_excl_gate.csv 2"}],
                  settle="forward IR <= 0 over 252 sessions of incubation; quote-calibrated impact pushing the break-even below 70 bp (R3:798)",
                  extra=_screen_extra({"bp_per_side": ref["break_even_bp"], "form": "gross diff / (turnover filtered - unfiltered)", "source": f"{ref['source']} line {ref['line']}"}))
    scr2 = _draft("SCR-2", "CARD-O", "G-02", "TF-13", "BUILD NOW (screen card)", "CR-06", "SPECIFICATION_BOOK",
                  "excluding heavy issuers (252-session share growth > 10%) raises long-only net excess",
                  "F6: drop names whose share count grew more than 10% over 252 sessions (split-like days ignored)",
                  "core.quant.tf_screens.dilution_at(P, t, window=252) -> dilution_flag(dil_lit, threshold=0.10) "
                  "(split-like days ignored); core.quant.tf_books.run_books(B1..B4 base and filtered books)",
                  lab_reference=[{"gv": "GV-014..017", "item": "B1 F6 gross / net 35 / net 70 %/yr; IR (monthly basis)", "value": "2.4164 / 2.3363 / 2.2563; IR 0.6453",
                                  "source": "r2_kr_excl_summary.csv lines 19 / 17 / 18"},
                                 {"gv": "G-TF-SCR-16", "item": "B1 F6 daily basis (QA recomputation)", "value": "2.56 / 2.48 / 2.40 %/yr; IR 1.03", "source": "qa_exact_costconv.json (not shipped)"}],
                  settle="post-2015 decay check pre-registered; drop to hygiene if 2016+ forward IR <= 0 (R3:799)",
                  extra=_screen_extra({"bp_per_side": 1057.0, "form": "gross diff / extra one-way turnover (QA 1,060)", "source": "r2_kr_excl_summary.csv line 19"}))
    fs = {
        "FS-1": _draft("FS-1", "CARD-P", "G-30", "TF-32", "FORWARD-SIM", "CR-02", "FORWARD_SIM",
                       "KOSPI floored trend x VT20 cuts drawdowns against the same-exposure static book S",
                       "vt x min(1, clip(ENS share of positive 20/60/120/250-session returns, 0.5, 1.0)); comparison cells: unbounded product (0 allowed), plain sleeve",
                       "core.quant.risk_layer.compose(vt, overlays=[trend_overlay]) (D-22: vt x min(1, overlay))", holding=1, instrument_book="KRX_ETF_line",
                       lab_reference=[{"gv": "GV-375..383", "item": "clip[0.5,1] primary, KOSPI rebuilt 1996-09..2026-09, net 3 bp",
                                       "value": "avg exposure 0.61, MDD -29.39%, PC-1 +15.4 pp vs own S, tail 0.64, dSR 0.156, PASS", "source": "r2_idx_overlay_vs_sleeve.csv line 12"}],
                       settle="start-date sweep REJECT from 2011, or plateau < 0.5 (R3:832)",
                       extra={"book": "forward_sim:FS-1", "comparator": "S_same_average_exposure",
                              "comparator_text": "S, the same-average-exposure static book (CARD-P)"}),
        "FS-2": _draft("FS-2", "CARD-O", "G-31", "TF-21", "FORWARD-SIM", "CR-05", "FORWARD_SIM",
                       "a constrained KRX momentum book (ex lottery / highest-turnover names) earns long-only net excess vs EW",
                       "Q5 MOM_12_1 ex F4, R-03 own-vol scaling, 5% name cap, long-only vs the EW universe; 2026 crash replay",
                       "core.quant.tf_books.fs2_momentum_book(mom, U, exclude=F4, k, vs=tf_books.fs2_vol_scale(...), cap=0.05) "
                       "(vs = core.quant.sleeves.sleeve_vol_scale, KR momentum)",
                       lab_reference=[{"gv": "GV-264 / GV-265", "item": "low-turnover 12-1 winners minus EW universe, net 35", "value": "+9.69%/yr, t 2.77",
                                       "source": "r2_kr_mom_grid_long.csv lines 1120 / 1123"}],
                       settle="forward net excess <= 0 after 252 sessions; 2026-type crash loss beyond the replay (R3:833)",
                       extra={"book": "forward_sim:FS-2", "primary_statistic": "long_only_net_excess", "benchmarks": list(TG.BENCHMARK_SET_KRX)}),
        "FS-3": _draft("FS-3", "descriptive", "G-32", "TF-16", "FORWARD-SIM (descriptive)", "CR-01", "FORWARD_SIM",
                       "a KRX low-volatility sleeve is protective against the same-beta static book S_beta",
                       "lowest-VOL_3M quintile vs S_beta = beta_hat x market + (1 - beta_hat) x cash; CARD-P checks PC-1 / PC-2 vs S_beta",
                       "core.quant.tf_gov.s_beta_book(market, cash, tf_gov.beta_hat(book, market, formation, window=252))",
                       lab_reference=[{"gv": "GV-469..475", "item": "low-vol Q1 EW vs VW ALL, net 35, rf 0", "value": "beta 0.631, dMDD vs S_beta -22.4 pp, tail 0.985",
                                       "source": "c12_lowvol_samebeta.csv line 2 (not in the bundle)"}],
                       settle="forward PC-1 and PC-2 pass vs S_beta (R3:834)",
                       extra={"book": "forward_sim:FS-3", "comparator": "S_beta", "beta_hat": {"value": None, "window_sessions": TG.BETA_WINDOW,
                                                                       "rule": "OLS daily beta over the prior 252 sessions, frozen in the header at each formation (OQ-03 proposal)"}}),
        "FS-4": _draft("FS-4", "forward_only", "G-33", "TF-63", "FORWARD-SIM", "CR-11", "FORWARD_SIM",
                       "a ridge / Fama-MacBeth challenger shrunk toward L0 adds net return over the L0 composite",
                       "ridge / FM shrunk toward L0 inside the ML harness: purge and embargo >= 63 sessions, <= 12 configurations",
                       "the ML harness after the ML-1 L0 card exists (core.quant.tf_screens.l0_composite(features, signs, U))", holding=63,
                       settle="forward net uplift over L0 > 0 for >= 252 sessions with no leakage findings -> gated card (R3:835)",
                       extra={"book": "forward_sim:FS-4"}),
        "FS-5": _draft("FS-5", "CARD-O", "G-34", "TF-42", "FORWARD-SIM (screen variant)", "CR-03", "FORWARD_SIM",
                       "excluding last month's top-decile winners adds to SCR-1 (a conditioning guard, weight 1)",
                       "exclude top 10% of REV_1M winners on B1 / B4 at 35 / 70 bp, gated like SCR-1",
                       "core.quant.tf_screens.reversal_guard(rev_1m, U, frac=0.10)",
                       lab_reference=[{"gv": "GV-505 / GV-506", "item": "1-month reversal EW deciles", "value": "+1.43%/month gross (t 3.1), +0.23% net 35",
                                       "source": "r2_kr_reversal.csv lines 47 / 52"}],
                       settle="R2-style race on B1 / B4 at 35 / 70 bp; keep only if it adds to SCR-1 (R3:836)",
                       extra={"book": "forward_sim:FS-5", "comparator": "overlay_off",
                              "comparator_text": "the SCR-1 book on the same days (guard off)"}),
    }
    return {"SCR-1": scr1, "SCR-2": scr2, **fs}


DRAFTS = _drafts()


def draft(card_id: str) -> dict:
    d = json.loads(json.dumps(DRAFTS[card_id]))
    reason = refusal(card_id)
    d["blocked_by"] = reason
    d["nulls"] = _nulls(d, reason)
    return d


# --------------------------------------------------------------------------- #
# The draft as a section 7.1 rule object (DNB-TF) and against the Council header schema
# --------------------------------------------------------------------------- #
RULE_KIND = {"CARD-O": "CARD-O", "CARD-P": "CARD-P", "descriptive": "CARD-P", "forward_only": "CARD-O"}
BOOK_OF = {"SPECIFICATION_BOOK": "specification", "FORWARD_SIM": "forward_sim"}


def rule_object(card_id: str) -> M.RuleObject:
    """The draft's card fields + the book's descriptor (`tf_books.CARD_RULES`, `extras["tf"]`)."""
    d = DRAFTS[card_id]
    return M.RuleObject.from_dict({"rule_id": card_id, "card_id": card_id, "kind": RULE_KIND[d["class"]],
                                   "market": d["market"], "instrument_book": d["instrument_book"],
                                   "books": [BOOK_OF[d["build_status"]]], "n_rule": M.N_GATE,
                                   **json.loads(json.dumps(TB.CARD_RULES[card_id]))})


def dnb_issues(card_id: str) -> list[str]:
    """`macro_rules.validate_rule_object` on the draft's rule object: the section 7.1 fields, the 17 Council shapes
    and the store's DNB-TF-01..17 predicates (empty = the draft is a buildable shape)."""
    return [i.message for i in M.validate_rule_object(rule_object(card_id)).errors]


# Values the closed Council header refuses, declared in docs/techfund/SCHEMA_AMENDMENT.md (None = every value).
HEADER_AMENDMENTS = {"benchmarks": None, "comparator": ("S_beta",), "class": ("descriptive", "forward_only")}


def header_overlap(d: dict) -> dict:
    """Validate a draft against model_card_header.macro.v2.0 on the fields both carry. Not checked: the declared
    value amendments, a header field the draft does not carry, and a typed null of `d["nulls"]` (`deferred`: filled
    at the first formal run). The schema itself is never loosened; `extensions` are the draft's own fields."""
    view = {k: v for k, v in d.items() if k in MS.HEADER_FIELDS}
    amended = sorted(k for k, v in view.items() if k in HEADER_AMENDMENTS
                     and (HEADER_AMENDMENTS[k] is None or v in HEADER_AMENDMENTS[k]))
    checked = {k: v for k, v in view.items() if k not in amended}
    nulls = d.get("nulls") or {}
    issues, deferred = [], []
    for ptr, msg in MS.registry().validate(MS.HEADER_ID, checked):
        key = ptr.strip("/").split("/")
        if msg == "required" and len(key) == 1 and key[0] not in checked:
            continue
        (deferred if ".".join(key) in nulls else issues).append(f"{ptr}: {msg}")
    return {"checked": sorted(checked), "amended": amended, "deferred": deferred, "issues": issues,
            "extensions": sorted(set(d) - MS.HEADER_FIELDS)}


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if math.isfinite(o) else None
    return o


def _write_json(path: Path, obj) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(_clean(obj), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def write_drafts(out_dir: Path = OUT) -> list[Path]:
    return [_write_json(Path(out_dir) / f"{cid}.draft.json", draft(cid)) for cid in DRAFTS]


# --------------------------------------------------------------------------- #
# CRY-1: C3 controls on the local vendor caches
# --------------------------------------------------------------------------- #
def load_close(name: str, cache: Path = CACHE) -> tuple[tuple[str, ...], np.ndarray, dict]:
    f = Path(cache) / f"{name}.csv"
    s = pd.read_csv(f, index_col=0).iloc[:, 0].dropna()
    s = s[s > 0]
    dates = tuple(str(d)[:10] for d in s.index)
    try:
        label = f.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        label = f.name
    return dates, s.to_numpy(dtype=float), {"file": label, "md5": V.md5_of(f), "start": dates[0], "end": dates[-1],
                                            "sessions": len(dates), "source": SERIES.get(name, "vendor")}


def _on(dates_all: tuple[str, ...], values: np.ndarray, wanted) -> np.ndarray:
    lookup = dict(zip(dates_all, values))
    return np.array([lookup[d] for d in wanted], dtype=float)


def c3_walk(prices: np.ndarray, dates: tuple[str, ...]):
    """Card C3's P&L matrix and walk-forward (strategy_card pipeline, ST:181-215): (wf, M)."""
    M, Ms, Tv = S.pnl_matrix(prices[:, None], S.crypto_trend, C3_GRID, cost_bps=COST)
    return V.walk_forward(M, list(dates[1:]), turnover=Tv, pnl_stress=Ms, embargo=C3_EMBARGO), M


def _score(wf, M, bench: np.ndarray, n_trials: int, seed: int):
    return V.score_strategy(wf, grid=C3_GRID, full_pnl=M, n_trials=n_trials, bench_daily=bench, seed=seed, domain=C3_DOMAIN)


SCORE_FIELDS = ("decision", "reason", "sr_oos", "ci90", "se_lo", "dsr", "pbo", "prob_loss_oos", "sr_stress", "bench_sr",
                "bench_diff", "bench_p", "bench_ci", "n_sessions", "n_trials", "n_trades", "years_positive", "plateau",
                "edge", "turnover_annual", "max_drawdown", "bench_mdd", "haircut_sr")


def _score_dict(s, wf) -> dict:
    out = {k: getattr(s, k) for k in SCORE_FIELDS}
    out.update(oos_start=wf.dates[0], oos_end=wf.dates[-1], walk_forward=wf.note,
               chosen_last=C3_GRID[wf.chosen[-1]] if wf.chosen else None)
    return out


def gov4_tightened(s, pnl: np.ndarray, bench: np.ndarray, seed: int) -> dict:
    """GOV-4 / D-01 reading: steps 2 and 5 at the worse of the 10-session result and the max(10, PW(d), PW(d^2),
    2 x holding) result; the decision re-derived by `validate._decide_strategy` (a tightening, never a loosening)."""
    b2 = TG.pw_block_dd2(pnl, C3_HOLDING)
    b5 = TG.pw_block_dd2(pnl - bench, C3_HOLDING)
    ci = V.block_bootstrap_ci(pnl, block=b2, B=B, level=0.90, seed=seed)
    bd = V.sharpe_diff_bootstrap(pnl, bench, block=b5, B=B, seed=seed)
    t = dataclasses.replace(s, ci90=(min(s.ci90[0], ci[0]), max(s.ci90[1], ci[1])), bench_p=max(s.bench_p, bd["p"]),
                            decision="", reason="", revise_target=None, lines=[])
    V._decide_strategy(t)
    return {"block_step2": b2, "block_step5": b5, "ci90_pw": ci, "bench_p_pw": bd["p"], "ci90_worse": t.ci90,
            "bench_p_worse": t.bench_p, "decision": t.decision, "reason": t.reason,
            "reading": "GOV-4 / D-01: the worse of the 10-session and the max(10, PW(d), PW(d^2), 2 x holding) result (a tightening)"}


def gov_block(s, wf, bench: np.ndarray, seed: int) -> dict:
    """The GOV report lines every tech-fund card prints (rulings 3.8): attribution, LW test, GOV-4, GOV-5, step 8 / 9,
    stress table. Reporting only; the verdict is the gate's (`decision`) and its GOV-4 tightened reading."""
    lw = TG.ledoit_wolf_sharpe_test(wf.pnl, bench, B, seed, holding=C3_HOLDING)
    return {"attribution": TG.attribution_block(wf.pnl, None, bench),
            "lw_sharpe_test": {k: lw[k] for k in ("dSR", "se", "t_obs", "p", "p_hac", "block", "B", "seed", "ci")},
            "gov4": gov4_tightened(s, wf.pnl, bench, seed),
            "min_track_record": TG.min_track_record_line(s.sr_oos, s.n_sessions),
            "step8": TG.step8_subperiods(wf.pnl, wf.dates),
            "step9": TG.expected_live(s.sr_oos),
            "stress": TG.stress_table(wf.pnl, wf.dates, benchmark=bench)}


def split_lines(wf, bench: np.ndarray, seed: int) -> dict:
    """(b) the pre-registered split at 2024-01-10 of C3's OOS record vs buy-and-hold on the same sessions."""
    d = np.array(wf.dates)
    out = {}
    for name, m in (("pre", d < SPLIT), ("post", d >= SPLIT)):
        a, b = wf.pnl[m], bench[m]
        lw = TG.ledoit_wolf_sharpe_test(a, b, B, seed, holding=C3_HOLDING)
        b10 = V.sharpe_diff_bootstrap(a, b, block=10, B=B, seed=seed)
        out[name] = {"start": str(d[m][0]), "end": str(d[m][-1]), "sessions": int(m.sum()), "sr_c3": V.sharpe(a),
                     "sr_buy_hold": V.sharpe(b), "dSR": V.sharpe(a) - V.sharpe(b), "p_block10": b10["p"],
                     "p_lw": lw["p"], "block_pw": lw["block"]}
    out["post_dsr_le_0"] = bool(out["post"]["dSR"] <= 0)
    out["trigger"] = ("post-ETF sub-period dSR <= 0: the R3 'what would change it' condition is met; reported for "
                      "the owner, C3's verdict is not rewritten (D-24)") if out["post_dsr_le_0"] else None
    return out


def _check_gate() -> None:
    want = {"bootstrap_B": B, "block": 10, "w_is": 756, "w_oos": 126, "haircut": 0.6}
    bad = {k: V.GATE.get(k) for k, v in want.items() if V.GATE.get(k) != v}
    if bad:
        raise RuntimeError(f"validate.GATE was mutated in this process ({bad}); the CRY-1 run refuses (C3 settings)")


def run_cry1(*, cache: Path = CACHE, out_dir: Path = OUT, registry_dir: Path, run_utc: str, seed: int = SEED) -> dict:
    """Run the CRY-1 controls and write `out_dir/cry1_*.json`; register the three extra trials of C3 in the trial
    registry at `registry_dir` (duplicates are the same trial). Returns {file name: payload}."""
    _check_gate()
    card = json.loads(Path(C3_CARD).read_text(encoding="utf-8"))
    n_card = int(card["trials"]["N_total"])
    n_after = n_card + len(EXTRA_TRIALS)
    data, runs = {}, {}
    for name in SERIES:
        dates, px, info = load_close(name, cache)
        data[name] = info
        wf, M = c3_walk(px, dates)
        bh = _on(dates[1:], px[1:] / px[:-1] - 1.0, wf.dates)
        runs[name] = {"dates": dates, "px": px, "wf": wf, "M": M, "bh": bh}
    # trial registry: one row per addition (the cut-time test is not run, so not counted; D-24)
    reg = TG.trial_registry(registry_dir)
    before = reg.n_rows
    span = [min(i["start"] for i in data.values()), max(i["end"] for i in data.values())]
    for _key, params in EXTRA_TRIALS:
        reg.register(FAMILY, {"rule": "C3", "params": {**params, "hysteresis_grid": [g["hysteresis"] for g in C3_GRID]},
                              "timing_class": "COMPLIANT", "span": span, "market": "CRYPTO", "run_utc": run_utc,
                              "phase": "research", "script": "docs/techfund_study.py", "run_kind": "variant",
                              "cost": COST, "card_id": "S_C3_crypto_trend",
                              "source": "vendor: Binance / Upbit public daily closes (docs/asset_expansion/cache)"})
    trials = {"card_N_total": n_card, "extra_trials": len(EXTRA_TRIALS), "N_after_cry1": n_after,
              "registered_rows_appended": reg.n_rows - before, "family": FAMILY, "family_rows": reg.ledger(FAMILY).n_raw,
              "global_N": reg.global_n(), "registry_dir": str(registry_dir),
              "cut_time_trial": "not counted: not run (D-24 counts four trials only if it runs)"}

    def header(addition: str, series) -> dict:
        return {"item": "CRY-1", "addition": addition, "register_id": "G-29", "node": "TF-67", "ruling": "CR-10",
                "card": "S_C3_crypto_trend", "c3_verdict": f"{card['decision']}, unchanged (D-24: additions are governance lines; the stored verdict is not rewritten)",
                "label": LABEL, "run_mode": "labelled_trial", "value_status": "vendor_close", "seed": seed, "B": B,
                "cost_bp_per_side": COST, "stress_multiplier": 2.0,
                "gate": "core.quant.validate nine-step gate (walk_forward 756/126, embargo 1, hysteresis lattice) + GOV report lines",
                "trials": trials, "bonferroni_note": BONFERRONI_NOTE, "data": {k: data[k] for k in series},
                "run_utc": run_utc, "script": "docs/techfund_study.py", "what_would_change_it": "post-ETF sub-period dSR <= 0 (R3:826)",
                "proposal_status": PROPOSAL}

    out = {}
    control = {}
    for name in BTC_SERIES:
        r = runs[name]
        wf, M = r["wf"], r["M"]
        tau = float(np.std(wf.pnl, ddof=1) * math.sqrt(V.TRADING_DAYS))
        W = S.vol_target(r["px"][:, None], target=tau, **CONTROL)
        ctrl_pnl, _ = S.simulate(r["px"][:, None], W, cost_bps=COST)
        ctrl = _on(r["dates"][1:], ctrl_pnl, wf.dates)
        repro = _score(wf, M, r["bh"], n_card, seed)
        vs = _score(wf, M, ctrl, n_after, seed)
        control[name] = {"c3_reproduction": {**_score_dict(repro, wf), "benchmark": "buy_and_hold"},
                         "c3_vs_control": {**_score_dict(vs, wf), "benchmark": "vol_scaled_long_only_control",
                                           "gov": gov_block(vs, wf, ctrl, seed)},
                         "control": {"tau": tau, "sr": V.sharpe(ctrl), "avg_exposure": float(np.mean(_on(r["dates"][1:], W[:-1, 0], wf.dates))),
                                     "max_drawdown": float(np.min(np.cumprod(1 + ctrl) / np.maximum.accumulate(np.cumprod(1 + ctrl)) - 1))}}
    out["cry1_volscaled_control.json"] = {**header("vol-scaled long-only control", BTC_SERIES),
                                          "pre_registration": {"control": "w_t = min(1, tau / sigma22_t), long-only, daily (step 1), band 0.10, 10 bp per side",
                                                               "tau": "annualised realised vol of C3's walk-forward OOS book on the same series (vol-matched, P2 F0)",
                                                               "n_trials": n_after},
                                          "results": control}
    out["cry1_split_2024-01-10.json"] = {**header("pre-registered split at 2024-01-10 (US spot-ETF date)", BTC_SERIES),
                                         "results": {n: split_lines(runs[n]["wf"], runs[n]["bh"], seed) for n in BTC_SERIES}}
    e = runs["binance_ETHUSDT"]
    eth = _score(e["wf"], e["M"], e["bh"], n_after, seed)
    out["cry1_eth_replication.json"] = {**header("ETH replication", ("binance_ETHUSDT",)),
                                        "results": {"binance_ETHUSDT": {**_score_dict(eth, e["wf"]), "benchmark": "buy_and_hold",
                                                                        "gov": gov_block(eth, e["wf"], e["bh"], seed)}}}
    out["cry1_cut_time.json"] = {**header("daily-bar cut-time sensitivity", ()), "status": "NOT_RUN", "cut_times": list(CUT_TIMES),
                                 "reason": ("REFDATA: intraday candles absent from docs/asset_expansion/cache (daily closes only); "
                                            "the 00:00 UTC / 00:00 KST / 21:00 UTC cut-time test needs hourly bars (a LIVE fetch, never made here)")}
    for fname, payload in out.items():
        _write_json(Path(out_dir) / fname, payload)
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def listing() -> list[tuple[str, str, str, str]]:
    return [(cid, d["class"], d["register_decision"], refusal(cid)) for cid, d in DRAFTS.items()]


def main(argv=None) -> int:
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--write-drafts", action="store_true")
    ap.add_argument("--run", default="", help="comma-separated tech-fund card ids (refused here)")
    ap.add_argument("--cry1", action="store_true", help="run the CRY-1 controls on the local caches")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--cache", default=str(CACHE))
    ap.add_argument("--ledger-dir", default=None, help="trial registry; defaults to <config.macro_dir()>/ledgers")
    ap.add_argument("--run-utc", default=None, help="run instant (ISO-8601 Z); defaults to the CLI clock")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)
    rc = 0
    if args.write_drafts:
        for p in write_drafts(Path(args.out)):
            print(f"draft written: {p}")
    for cid in [c for c in args.run.split(",") if c]:
        try:
            run_card(cid)
        except (CardRefused, KeyError) as exc:
            rc = 2
            print(f"run refused: {exc}")
    if args.cry1:
        if args.ledger_dir is None:
            import config
            args.ledger_dir = str(config.macro_dir() / "ledgers")
        run_utc = args.run_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")   # CLI clock only
        res = run_cry1(cache=Path(args.cache), out_dir=Path(args.out), registry_dir=Path(args.ledger_dir),
                       run_utc=run_utc, seed=args.seed)
        print(BONFERRONI_NOTE)
        t = res["cry1_volscaled_control.json"]["trials"]
        print(f"trials: C3 N {t['card_N_total']} + {t['extra_trials']} CRY-1 = {t['N_after_cry1']}; registry rows appended "
              f"{t['registered_rows_appended']}; global N {t['global_N']} ({t['registry_dir']})")
        for f, payload in res.items():
            print(f"written: {Path(args.out) / f}  [{payload['label']}]")
    if not (args.write_drafts or args.run or args.cry1):
        for cid, cls, decision, why in listing():
            print(f"{cid:6s} {cls:13s} {decision:30s} NOT_RUN  {why}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
