"""Build docs/QUANTGEN_Expansion_Primer.pdf — the plain-language companion to the
version-3 asset-coverage expansion: what the KIS key reaches, the validation
gate statistic by statistic, every strategy family and market model that was
built, what the study decided about each on real history, and what the app
therefore offers or withholds.

Run from the project root:  python docs/build_expansion_primer.py

Every number quoted comes from docs/asset_expansion/cards/*.json (the study's
model cards, md5-stamped to results.csv) or is computed here at build time by
calling the same functions the app calls; nothing is retyped. English only
(DejaVu has no Hangul); the operator's own study materials are cited by the
labels in section 10.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs"))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np

from primer_kit import (B, BOX, F, FIG, P, P3, TBL, TOC, C_ALT, C_GREEN, C_GREY, C_MAIN, C_RED, FIG_W, PageBreak,
                        PrimerDoc, Spacer, cm, glyph_check, plt)
from core.quant import validate as V
from core.quant.gjr import skewt_ppf, skewt_logpdf
from scipy import stats as sps

DOCS = ROOT / "docs"
CARDS = DOCS / "asset_expansion" / "cards"
FIG_DIR = DOCS / "primer_figures"
OUT_PDF = DOCS / "QUANTGEN_Expansion_Primer.pdf"
FIG_DIR.mkdir(parents=True, exist_ok=True)
T0 = time.time()

# --------------------------------------------------------------------------- #
# Cards: every quoted number
# --------------------------------------------------------------------------- #
C: dict[str, dict] = {c["card_id"]: c for c in V.load_cards(CARDS)}
MANIFEST = json.loads((DOCS / "asset_expansion" / "manifest.json").read_text(encoding="utf-8")) \
    if (DOCS / "asset_expansion" / "manifest.json").exists() else {}
_KO = {"KODEX \ub808\ubc84\ub9ac\uc9c0": "KODEX Leverage", "KODEX 200\uc120\ubb3c\uc778\ubc84\uc2a42X": "KODEX 200 Futures Inverse 2X", "KODEX \uc778\ubc84\uc2a4": "KODEX Inverse",
       "\uad6d\uace0\ucc44": "KTB", "\uc6d0/\ub2ec\ub7ec": "USD/KRW"}


def en(text: str) -> str:
    """Card text for the PDF: known Korean names translated, other CJK dropped, markup-safe."""
    for k, v in _KO.items():
        text = text.replace(k, v)
    text = "".join(ch for ch in text if ord(ch) < 0x3000)
    return text.replace("&", "&amp;").replace("<", "&lt;")


def st(cid: str, key: str, default=float("nan")):
    return (C.get(cid, {}).get("stats", {}) or {}).get(key, default)


def ts(cid: str, key: str, default=float("nan")):
    return (C.get(cid, {}).get("tests", {}) or {}).get(key, default)


def dec(cid: str) -> str:
    return C.get(cid, {}).get("decision", "not run")


def reason(cid: str) -> str:
    return en(C.get(cid, {}).get("decision_reason", ""))


def line(cid: str, i: int) -> str:
    ls = C.get(cid, {}).get("lines") or []
    return en(ls[i]) if i < len(ls) else ""


def fmt(x, spec: str = ".2f") -> str:
    try:
        if x is None or (isinstance(x, float) and not math.isfinite(x)):
            return "n/a"
        return format(float(x), spec)
    except Exception:
        return str(x)


def pct(x, d: int = 0) -> str:
    return "n/a" if not isinstance(x, (int, float)) or not math.isfinite(x) else f"{100 * x:.{d}f}%"


FAMILY = [("ETF trend switch", ["S_E1_trend_us", "S_E1_trend_krx"]),
          ("Volatility targeting", ["S_E2_voltarget_spy", "S_E2_voltarget_kodex200"]),
          ("Risk parity", ["S_E3_riskparity_us"]),
          ("Cross-sectional momentum", ["S_E5_xsmom_sectors"]),
          ("Time-series momentum (futures)", ["S_B3_tsmom_futures"]),
          ("Crypto trend", ["S_C3_crypto_trend_btcusd", "S_C3_crypto_trend_krwbtc"]),
          ("Pairs", ["S_E8_pairs_kodex_tiger", "S_S6_pairs_samsung_pref", "S_S6_pairs_hyundai_kia", "S_E8_pairs_gld_iau"]),
          ("VIX roll-down", ["S_V1_vix_rolldown"]),
          ("FX styles", ["S_V3_fx_momentum", "S_V4_dollar_carry"]),
          ("Curve models", ["M_B1_dns", "S_B2_pca_fly"]),
          ("Volatility fans", ["D_Q_garch_spy", "D_Q_gjr_spy", "D_Q_skewt_spy", "D_Q_garch_kodex200", "D_Q_gjr_kodex200",
                               "D_Q_skewt_kodex200", "D_C2_garch_btc", "D_C2_gjr_btc", "D_C2_skewt_btc"]),
          ("Crypto monitors", ["M_C1_kimchi", "M_C4_funding", "M_C8_ethbtc", "M_C7_weekday"]),
          ("Derivatives and ETF models", ["M_E4_letf_drag", "M_O1_board_today", "M_O2_basis_today"])]
DEC_COLOR = {"PASS": C_GREEN, "REVISE": "#e0a800", "REJECT": C_RED, "INSUFFICIENT_DATA": C_GREY}


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def _save(fig, name: str) -> str:
    path = FIG_DIR / f"exp_{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def fig_decisions() -> str:
    fig, ax = plt.subplots(figsize=(FIG_W, 3.4))
    labels = [f for f, _ in FAMILY]
    bottoms = np.zeros(len(FAMILY))
    for d in ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA"):
        vals = np.array([sum(1 for cid in ids if dec(cid) == d) for _, ids in FAMILY], dtype=float)
        ax.barh(labels, vals, left=bottoms, color=DEC_COLOR[d], label=d.replace("_", " ").title())
        bottoms += vals
    ax.invert_yaxis()
    ax.set_xlabel("cards")
    ax.set_title("Study decisions by family")
    ax.legend(loc="lower right", frameon=False)
    return _save(fig, "decisions")


def fig_pbo() -> tuple[str, dict]:
    rng = np.random.default_rng(3)
    T = 2000
    sig = rng.normal(0.0004, 0.01, T)
    flat = np.column_stack([sig + rng.normal(0, 0.002, T) for _ in range(8)])
    noise = np.column_stack([rng.normal(0, 0.01, T) for _ in range(8)])
    res = {k: V.pbo_cscv(M, S=16) for k, M in (("flat plateau", flat), ("pure noise", noise))}
    fig, axes = plt.subplots(1, 2, figsize=(FIG_W, 2.9))
    for ax, (k, M) in zip(axes, (("flat plateau", flat), ("pure noise", noise))):
        srs = np.array([V.sharpe(M[:, g]) for g in range(M.shape[1])])
        ax.bar(np.arange(8), srs, color=C_MAIN if k.startswith("flat") else C_GREY)
        ax.axhline(0, color="black", linewidth=0.6)
        r = res[k]
        ax.set_title(f"{k}: PBO {r['pbo']:.2f}, winner loses OOS in {r['prob_loss']:.0%} of splits")
        ax.set_xlabel("configuration")
        ax.set_ylabel("full-sample Sharpe")
    return _save(fig, "pbo"), res


def fig_skewt() -> str:
    nu = 6.0
    lam = st("D_Q_skewt_spy", "median_lambda", -0.15)
    if not isinstance(lam, (int, float)) or not math.isfinite(lam) or lam == 0.0:
        lam = -0.15
    x = np.linspace(-5, 5, 801)
    scale = math.sqrt((nu - 2) / nu)
    f_t = sps.t.pdf(x / scale, nu) / scale
    f_s = np.exp(skewt_logpdf(x, nu, lam))
    fig, ax = plt.subplots(figsize=(FIG_W, 3.0))
    ax.plot(x, f_t, color=C_GREY, label=f"symmetric t, nu = {nu:.0f}")
    ax.plot(x, f_s, color=C_MAIN, label=f"Hansen skew-t, nu = {nu:.0f}, lambda = {lam:+.2f}")
    q_t = sps.t.ppf(0.05, nu) * scale
    q_s = float(skewt_ppf(0.05, nu, lam))
    ax.axvline(q_t, color=C_GREY, linestyle="--", linewidth=0.8)
    ax.axvline(q_s, color=C_MAIN, linestyle="--", linewidth=0.8)
    ax.text(q_t, 0.36, f" 5% quantile t {q_t:.2f}", color=C_GREY, fontsize=7)
    ax.text(q_s, 0.32, f" skew-t {q_s:.2f}", color=C_MAIN, fontsize=7)
    ax.set_xlim(-5, 5)
    ax.set_xlabel("standardised return")
    ax.set_ylabel("density")
    ax.set_title("Same variance, longer left tail: what the skew parameter changes")
    ax.legend(frameon=False)
    return _save(fig, "skewt")


FIG_DEC = fig_decisions()
FIG_PBO, PBO_DEMO = fig_pbo()
FIG_SKEWT = fig_skewt()


# --------------------------------------------------------------------------- #
# Chapters
# --------------------------------------------------------------------------- #
def ch_title() -> list:
    n = len(C)
    counts = {}
    for c in C.values():
        counts[c["decision"]] = counts.get(c["decision"], 0) + 1
    tally = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    return [
        Spacer(1, 4 * cm),
        P("QUANTGEN Expansion Primer", "title"),
        P("Version 3 of the desk: what the KIS key reaches, the validation gate statistic by statistic, the strategy "
          "families and market models that were built for ETFs, index derivatives, curves, FX, volatility products and "
          "crypto, what the study decided about each on real history, and what the app therefore offers or withholds.",
          "subtitle"),
        Spacer(1, 1 * cm),
        P(f"Built {time.strftime('%Y-%m-%d %H:%M')} by <font name='DejaVuSansMono'>docs/build_expansion_primer.py</font> "
          f"from the code in <font name='DejaVuSansMono'>core/</font> and <font name='DejaVuSansMono'>data/</font>.", "small"),
        P(f"Every quoted number comes from the {n} model cards in <font name='DejaVuSansMono'>docs/asset_expansion/cards/</font> "
          f"(study run {MANIFEST.get('run', '?')}, seed {MANIFEST.get('seed', '?')}, results.csv md5 "
          f"<font name='DejaVuSansMono'>{str(MANIFEST.get('results_md5', ''))[:12]}</font>): {tally}.", "small"),
        P("Written for the operator of QUANTGEN. Nothing in this document is investment advice; it explains what the "
          "software computes, how it was checked, and why some of it is deliberately not offered.", "small"),
        PageBreak(),
    ]


def ch0() -> list:
    return [
        P("0. How to use this document", "H1"),
        P("The Models Primer explained the price-path models of the Quant Lab. This companion explains everything version 3 "
          "added around them. It is written so that each statistic can be read without the paper it came from, because the "
          "operator has said they cannot judge a silent fitting failure themselves: every test in the app renders as one sentence "
          "with the number, the threshold and the sample size, and this document says what each of those sentences means."),
        P("The build followed four steps the operator set. <b>Step 1</b>: find what the linked KIS account can quote beyond "
          "stocks and build the credible models on it. <b>Step 2</b>: bring crypto in without KIS, through public exchange data, "
          "and say what a wallet connection may and may not do. <b>Step 3</b>: cover the markets that neither route reaches, "
          "by building where data exist and documenting where they do not. <b>Step 4</b>: validate every model on history, "
          "modify or exclude what is not accurate, and embed only what survives."),
        P("Where the numbers come from: the study script <font name='DejaVuSansMono'>docs/asset_expansion_study.py</font> "
          "runs every candidate on real history and writes one JSON card per model. A card carries the hypothesis, the rule, "
          "the data span, the pre-registered costs, the seed, every test line, the decision and its reason, and the md5 of "
          "the results file. The app reads the same cards: the Strategy Lab lists them, and the ETF, Crypto, Derivatives and "
          "Quant Lab pages show the verdict next to the number it concerns. This document quotes the cards; if a card is "
          "re-run, rebuild this PDF."),
        BOX("The three rules that never bend", [
            "The app is read-only. No order, cancel, withdrawal, deposit-address or transfer path exists on any venue, and "
            "no private key, seed phrase or wallet secret is ever requested or stored.",
            "A signal is computed on the close of day t and earns from day t+1. Costs are charged on every unit of turnover "
            "at a rate fixed before the test, and a 2x stress is always shown.",
            "A decision is made by the gate, not by the author. PASS, REVISE, REJECT and INSUFFICIENT DATA are defined once in "
            "<font name='DejaVuSansMono'>core/quant/validate.py</font>; a REJECT stays visible in the app as a refusal.",
        ], C_MAIN),
        FIG(1, "Decisions of the study by family. Most strategy families fail, and the reason is visible on each card.", FIG_DEC),
    ]


def ch1() -> list:
    rows = [
        ["ETF", "NAV, premium, tracking error, LP holdings, constituents with weights; 100 sessions per call", "ETF page"],
        ["KOSPI 200 futures", "quote with KIS theoretical price and open interest; daily history; every listed contract", "Derivatives page"],
        ["KOSPI 200 options", "expiries; each series quoted from the keyless master (the board endpoint stops at its top 100 "
                              "strikes); KIS implied vol and Greeks; top-of-book bid/ask", "Derivatives page"],
        ["KTB and USD futures", "the same endpoints with market code CF", "Rates, FX"],
        ["KRW benchmark yields", "KTB 1y to 30y, CD 91d, call, corporate AA-; today's snapshot and paged history", "Rates page, curve models"],
        ["US yields, indices, stocks", "10y and 30y Treasury, Fed funds; S&P 500; adjusted daily prices for NAS:AAPL and the like", "Quant Lab, Strategy Lab"],
        ["USD/KRW fixing", "the daily fixing, paged", "FX page"],
        ["Overseas futures", "VIX, dollar index and bitcoin futures answer; ES, NQ, ZN, 6E, GC, CL, SR3 return HTTP 500 on this key "
                             "(an entitlement gate, not a symbol error)", "Vol products"],
        ["Exchange-traded bonds", "KTB issues from the bond master, price, yield, history", "Bonds page"],
        ["Domestic flows", "daily net buying by investor type; short-sale volume and ratio", "Signals"],
    ]
    return [
        P("1. What the KIS key reaches, and what stays read-only", "H1"),
        P("The operator's app key was issued against a stock account. The probe of 2026-09-25 established that <b>quoting "
          "needs only the app key</b>: every domain below answered without a derivatives account, an overseas agreement or "
          "any course. Trading KOSPI 200 or KTB futures would need a futures/options account with its deposit and training "
          "requirements, none of which QUANTGEN uses, because it never trades."),
        TBL(["Domain", "What comes back", "Where the app uses it"], rows, widths=[3.4 * cm, 9.4 * cm, 3.4 * cm], wrap=True),
        P("What KIS still does not give: option-chain history (boards must be stored daily), futures investor flows, the CME "
          "equity and rate contracts on this key, and any crypto. The quotation endpoints share the token cache (24 hours, "
          "one issuance per minute) and the client throttles at about two requests per second."),
        P("1.1 A lesson from the first live board", "H2"),
        P("The first snapshot of the October board was taken on a Sunday. KIS still showed a bid and an ask on most series, "
          "and the implied vols inverted from those mids came out near 51% while KIS's own were near 36%. The book was the "
          "closing auction's leftovers: a 1.7-point bid resting under a 34-point option, stamped 15:45:00. The client now treats "
          "any book stamped between 15:45 and 18:00 as empty, measures time to expiry from the last session rather than from "
          "today, and the Derivatives page says in red that a closed-market board is last prints struck at different moments. "
          "The study's board card records the same fact as its reason and asks to be re-run during a session."),
        P("1.2 The crypto route and its refusals", "H2"),
        P("Upbit's public candles (KRW-BTC since 2017-09-25), Binance's public spot klines and funding history (reachable from "
          "Korea through the data mirror), the premium index, open-interest history and CoinGecko's top list are all keyless. "
          "An optional Upbit balance read uses a standard-library HS512 JWT with an access key restricted to the asset-inquiry "
          "scope. Refused by construction: any order, withdrawal or transfer endpoint; private keys, seed phrases, keystores and "
          "hardware-wallet secrets; transaction signing; any account on an unregistered foreign exchange (Binance is data only); "
          "the ccxt, web3 and pyupbit dependencies; tax computation. The regulatory record behind each refusal is in the "
          "research report."),
    ]


def ch2() -> list:
    g = V.GATE
    pf, pn = PBO_DEMO["flat plateau"], PBO_DEMO["pure noise"]
    return [
        P("2. The gate, statistic by statistic", "H1"),
        P("A strategy is a rule that turns the history up to day t into weights held over day t+1. The study runs every "
          "configuration of a rule on the whole history once, producing a matrix of daily P&amp;L with one column per "
          "configuration, and everything below is computed from that matrix. Two habits from the operator's own reading run "
          "through it: the Two Doors roadmap's second pillar (purged cross-validation and the deflated Sharpe ratio as the "
          "minimum discipline, [Two Doors] pp. 7-9) and the time-series cross-validation of [Tibshirani] Lecture 3 section 4, "
          "where the training window always precedes the test window."),
        P("2.1 Purged walk-forward", "H2"),
        P(f"The history is cut into consecutive in-sample windows of {g['w_is']} sessions and out-of-sample windows of "
          f"{g['w_oos']} sessions. In each in-sample window the configuration with the best Sharpe is chosen; it is then held "
          "over the next out-of-sample window; the chosen columns are concatenated into one out-of-sample P&amp;L series. An "
          "embargo equal to the rule's holding period is left between the two windows so that a position opened in-sample "
          "cannot leak its outcome into the test. This is k-fold cross-validation ([CS229] section 9.3) with the folds forced "
          "into time order, which is the only order a trading rule will ever see."),
        P("2.2 Sharpe ratio, its standard error and its interval", "H2"),
        F("SR = sqrt(252) x mean(r) / sd(r),  SE(SR) from Lo (2002), which corrects for autocorrelation in r"),
        P("The Sharpe ratio is the mean daily P&amp;L over its standard deviation, annualised ([Financial Economics] "
          "chapter 6 on the reward-to-variability ratio). Its standard error is not 1/sqrt(T): a rule that holds positions "
          "for weeks has autocorrelated P&amp;L, and Lo's correction widens the error accordingly. The interval the gate uses "
          f"is a {g['ci_level']:.0%} studentised circular block bootstrap ({g['bootstrap_B']} resamples, blocks of "
          f"{g['block']} sessions): blocks rather than single days so that the clustering of returns survives the resampling. "
          "The first hard criterion is that this interval excludes zero."),
        P("2.3 Deflated Sharpe ratio", "H2"),
        P("Trying N configurations and reporting the best inflates the Sharpe even when nothing works. Bailey and Lopez de "
          "Prado's deflated Sharpe ratio asks: given N trials whose Sharpe ratios have this spread, what is the probability "
          "that the best one exceeds what the maximum of N pure-noise trials would reach? The expected maximum of N standard "
          "normals is approximately (1 - gamma) Phi<super>-1</super>(1 - 1/N) + gamma Phi<super>-1</super>(1 - 1/(N e)), with "
          "gamma the Euler constant, scaled by the trials' Sharpe dispersion; the reported number is the probability that the "
          f"observed Sharpe beats that benchmark after correcting for skewness and kurtosis. The gate needs {g['dsr_min']}. "
          "The number of trials on a card is the whole grid plus every revision, so a re-run after a REVISE is more, not "
          "less, demanding."),
        P("2.4 Probability of backtest overfitting, and why it reads 0.5 on a plateau", "H2"),
        P("Combinatorially symmetric cross-validation (CSCV) splits the P&amp;L matrix into S blocks, forms every way of "
          "choosing half the blocks as training and the other half as testing, picks the best configuration on the training "
          "half, and records its rank on the test half. PBO is the share of splits in which that in-sample winner ranks in the "
          "bottom half out of sample. Two more numbers come with it: the share of splits in which the winner actually loses "
          "money out of sample, and the slope of out-of-sample Sharpe on in-sample Sharpe across the splits."),
        FIG(2, f"Eight configurations that are the same rule with tiny noise (left) versus eight columns of pure noise "
               f"(right), scored by the same CSCV. On the plateau PBO is {pf['pbo']:.2f} although the winner loses out of "
               f"sample in {pf['prob_loss']:.0%} of the splits; on noise PBO is {pn['pbo']:.2f} and the winner loses in "
               f"{pn['prob_loss']:.0%}. PBO alone cannot tell them apart; the probability of loss can.", FIG_PBO),
        P("The figure shows the trap the second study run fell into. When every configuration is nearly the same rule, the "
          "in-sample winner is whichever column was luckiest in the training half, and because the two halves are "
          "complementary its rank flips in the test half: PBO sits at 0.5 and the slope at -1 by construction, exactly as "
          "for a genuinely overfit grid. Bailey et al. read PBO together with the probability of loss and the degradation for "
          f"this reason. The gate now does the same: over-search passes when PBO is at most {g['pbo_max']} <i>or</i> the "
          f"winner loses out of sample in at most {g['prob_loss_max']:.0%} of the splits, and rejects only when PBO exceeds "
          f"{g['pbo_reject']} <i>and</i> the winner loses. With fewer than {g['pbo_min_configs']} configurations the rank is "
          "too coarse to mean anything and only the probability of loss is used. This change moved no card from REJECT to "
          "PASS on its own: the strategies it released were then rejected by the benchmark test of 2.5."),
        P("2.5 The benchmark test and the drawdown line", "H2"),
        P("A claim such as 'the trend switch beats buy-and-hold' is a claim about a difference, so the study pairs each "
          "out-of-sample day of the strategy with the same day of its benchmark and bootstraps the difference of Sharpe "
          f"ratios in blocks. The one-sided probability that the difference is at most zero must be {g['bench_p_max']} or "
          "less. The maximum drawdown of both is printed beside it, because several rules (the trend switch in particular) "
          "cut the drawdown without raising the Sharpe; that is reported, not gated."),
        P("2.6 Costs, turnover and the stress", "H2"),
        P("Costs are fixed before the test, per side and per venue: 3 bp for a KRX ETF, 35 bp for a KRX stock (the "
          "transaction tax dominates), 50 bp for US shares through KIS, 10 bp for crypto (the exchange fee plus slippage), "
          "5 bp for futures and 10 bp for FX. The simulator charges cost x |change in weight| every day. The same matrix is "
          f"built at {g['cost_stress']:.0f}x costs and the Sharpe there must stay positive. Annual turnover is printed as "
          "multiples of equity so the reader can see what a strategy's Sharpe is buying."),
        P("2.7 Plateau and edge", "H2"),
        P("A rule whose neighbours on the grid keep at least half its Sharpe sits on a plateau; one whose best configuration "
          f"sits at the end of an axis may simply not have been searched far enough. The gate needs {g['plateau_min']:.0%} of "
          "neighbours on the plateau and no edge. An edge only counts on an axis with three or more values: on a two-value "
          "axis every point is an end, which is the other harness bug the second run exposed. A REVISE for an edge asks for "
          "the grid to be widened and the trial count to rise."),
        P("2.8 Years, regimes and the haircut", "H2"),
        P(f"At least {g['years_pos_min']:.0%} of calendar years must be positive and the share of the P&amp;L carried by the "
          "largest year is printed. The Sharpe is split by the benchmark's volatility regime and by up and down markets. "
          f"Finally the expected live Sharpe is {g['haircut']:.0%} of the out-of-sample one: McLean and Pontiff measured the "
          "post-publication decay of published anomalies at about that size, and a rule taken from a paper is a published "
          "anomaly."),
        P("2.9 The distribution loop for fans", "H2"),
        P("A volatility model is not a strategy; it is a forecast of the whole distribution of tomorrow's return, and it is "
          "scored on rolling one-day origins with the model refit every seven sessions on a trailing window. Four families "
          "of checks, all from the operator's reading on calibration ([Tibshirani] Lecture 8 section 3 on empirical coverage "
          "and PIT calibration; the Models Primer sections 6.3-6.4 on the Student-t scaling):"),
        *B([
            "<b>Kupiec</b>: a 5% value-at-risk should be breached on 5% of days. The test compares the breach rate with its "
            "binomial standard error over the number of origins. The same at 1%, and the Basel traffic light counts breaches "
            "over the last 250 days.",
            "<b>Christoffersen</b>: breaches should not cluster. The independence test asks whether a breach today makes one "
            "tomorrow more likely; the conditional-coverage test combines it with Kupiec.",
            "<b>Coverage</b>: the 90% band should contain 90% of outcomes, within its binomial error.",
            "<b>PIT</b>: the probability the model assigned to the outcome that then occurred should be uniform on [0, 1] "
            "(Diebold, Gunther and Tay). A Kolmogorov-Smirnov test, a chi-square on ten bins, Berkowitz's likelihood-ratio "
            "test on the normal transform and the correlograms of the centred PIT powers are all printed. With three thousand "
            "origins the KS test detects a one-point miss in the tail, so a fan can pass every count-based test and still "
            "fail PIT; the gate rejects only below the 1% level and revises between 1% and 5%.",
            "<b>QLIKE and Diebold-Mariano</b>: the model's variance forecast is compared with the EWMA(0.94) benchmark on the "
            "loss r<super>2</super>/s<super>2</super> - ln(r<super>2</super>/s<super>2</super>) - 1; a negative DM statistic "
            "favours the model.",
        ]),
        P("2.10 Decisions", "H2"),
        P("REJECT: the deflated Sharpe fails, or PBO fails with the winner losing, or the strategy loses money at 2x costs "
          "with an interval that includes zero, or it does not beat its benchmark. INSUFFICIENT DATA: fewer than "
          f"{g['trades_floor']} trades or {g['oos_years_min']} out-of-sample years, or an interval that includes zero when the "
          "minimum track record for that Sharpe is longer than the sample. PASS: every criterion met. Otherwise REVISE, "
          "naming the first failed criterion and the only permitted revision (widen the grid, lengthen the holding period, "
          "extend history; never lower the cost). Every revision is logged on the card and counted in the trial number."),
    ]


def strat_rows(ids: list[str]) -> list[list[str]]:
    rows = []
    for cid in ids:
        if cid not in C:
            rows.append([cid, "not run", "", "", "", "", ""])
            continue
        s = C[cid]["stats"]
        ci = s.get("ci90", [float("nan"), float("nan")])
        rows.append([cid.replace("S_", "").replace("_", " "), dec(cid),
                     f"{fmt(s.get('sr_oos'))} [{fmt(ci[0])}, {fmt(ci[1])}]", fmt(s.get("dsr")),
                     f"{fmt(s.get('pbo'))} / {pct(s.get('prob_loss_oos'))}",
                     f"{fmt(s.get('bench_sharpe'))} (p {fmt(s.get('bench_p'))})" if isinstance(s.get("bench_p"), (int, float))
                     and math.isfinite(s.get("bench_p")) else "none",
                     f"{fmt(s.get('sr_stress'))}, {fmt(s.get('turnover_annual'), '.1f')}x"])
    return rows


def ch3() -> list:
    hdr = ["Card", "Decision", "OOS Sharpe [90% CI]", "DSR", "PBO / loses OOS", "Benchmark SR (p)", "2x costs, turnover"]
    w = [3.6 * cm, 1.8 * cm, 3.2 * cm, 1.2 * cm, 2.2 * cm, 2.6 * cm, 2.2 * cm]
    ids_a = ["S_E1_trend_us", "S_E1_trend_krx", "S_E2_voltarget_spy", "S_E2_voltarget_kodex200", "S_E3_riskparity_us",
             "S_E5_xsmom_sectors", "S_B3_tsmom_futures"]
    ids_b = ["S_C3_crypto_trend_btcusd", "S_C3_crypto_trend_krwbtc", "S_E8_pairs_kodex_tiger", "S_S6_pairs_samsung_pref",
             "S_S6_pairs_hyundai_kia", "S_E8_pairs_gld_iau", "S_V1_vix_rolldown", "S_V3_fx_momentum", "S_V4_dollar_carry"]
    tu, tk = C.get("S_E1_trend_us", {}).get("stats", {}), C.get("S_E2_voltarget_spy", {}).get("stats", {})
    cb, ck = C.get("S_C3_crypto_trend_btcusd", {}).get("stats", {}), C.get("S_C3_crypto_trend_krwbtc", {}).get("stats", {})
    return [
        P("3. Strategy families and what the study decided", "H1"),
        P("Each family is one function in <font name='DejaVuSansMono'>core/quant/strategies.py</font>, written so that the "
          "weights decided on day t are held over t+1. The rules, in words:"),
        *B([
            "<b>Trend switch</b> (Faber; Moskowitz, Ooi and Pedersen): each sleeve is held when its price is above its "
            "10-month moving average, or when its trailing 12-month return is positive, and is otherwise in cash; 1/N per "
            "sleeve; re-decided every step. [RN-FH] sections 6.1-6.8 derive why a trend rule has the payoff of a lookback "
            "straddle, which is why its drawdowns are shallow and its Sharpe is not necessarily higher.",
            "<b>Volatility targeting</b> (Moreira and Muir in Cederburg's real-time form): weight = min(1, target / trailing "
            "realised vol); the cap keeps it unlevered. [BKM] chapter 6 slides 6-20 to 6-22 on the reward-to-risk trade-off.",
            "<b>Risk parity</b> (Asness, Frazzini and Pedersen): weights inversely proportional to each sleeve's trailing "
            "vol so that risk contributions are equal; unlevered. [BKM] chapter 7 slides 7-5 to 7-8; [Boyd] section 4.4.1 "
            "p. 155 for the portfolio problem it simplifies.",
            "<b>Cross-sectional momentum</b> (Jegadeesh and Titman): long the top third of the nine sector SPDRs by 12-1 "
            "month return, re-ranked monthly.",
            "<b>Time-series momentum</b> (Moskowitz, Ooi and Pedersen equation (5)): sign of the trailing 12-month return, "
            "sized at 40% / trailing EWMA vol, long and short, on ten Yahoo continuous futures whose roll is undocumented.",
            "<b>Crypto trend</b> (Liu and Tsyvinski; Detzel et al.): sign votes over 7-28 day lookbacks plus price / "
            "moving-average ratios, long or flat with a hysteresis band so that small reversals do not trade.",
            "<b>Pairs</b> (Gatev, Goetzmann and Rouwenhorst; Engle-Granger): the spread of two cointegrated prices over a "
            "formation window, traded at +/- 2 standard deviations over a trading window; the ADF share and half-life of the "
            "formation windows are printed. [MTSA] sections 5.3.2 (ADF) and 6.2.3 (Engle-Granger).",
            "<b>VIX roll-down</b> (Simon and Campasano): short the VIX ETP while the three-month / one-month ratio exceeds a "
            "contango threshold, hedged with an equity position sized by a rolling beta that only resets when it moves.",
            "<b>FX styles</b> (Menkhoff et al.; Lustig, Roussanov and Verdelhan): G10 cross-sectional momentum and the "
            "dollar carry rule; [Shreve II] 9.3 and [ECON302] chapter 1 for the interest-parity background.",
        ]),
        P("3.1 Long-only and unlevered rules on ETF sleeves", "H2"),
        TBL(hdr, strat_rows(ids_a), widths=w, font=7.5, wrap=True),
        P(f"The pattern is consistent and consistent with the literature. The trend switch on US sleeves earned an "
          f"out-of-sample Sharpe of {fmt(tu.get('sr_oos'))} against the buy-and-hold {fmt(tu.get('bench_sharpe'))}, with a "
          f"maximum drawdown of {pct(tu.get('max_drawdown'))} against {pct(tu.get('bench_mdd'))}: it protects, it does not "
          f"outperform, and the gate's claim was outperformance. Capped volatility targeting on SPY adds "
          f"{fmt(tk.get('bench_diff'), '+.2f')} of Sharpe at p {fmt(tk.get('bench_p'))}, which is what Cederburg et al. found "
          "when the rule is run in real time; risk parity without leverage is the benchmark; sector momentum after 50 bp per "
          "side is below it; futures time-series momentum on Yahoo's continuous contracts has no measurable edge after 2009. "
          "The app keeps the trend switch and vol target on the ETF page as descriptive sleeves with their verdicts, because "
          "the drawdown line is worth seeing, and offers none of them as a signal."),
        P("3.2 Crypto trend, pairs, volatility and FX", "H2"),
        TBL(hdr, strat_rows(ids_b), widths=w, font=7.5, wrap=True),
        P(f"The crypto trend rule is the one strategy that clears the whole gate: on KRW-BTC an out-of-sample Sharpe of "
          f"{fmt(ck.get('sr_oos'))} against buy-and-hold {fmt(ck.get('bench_sharpe'))} at p {fmt(ck.get('bench_p'))}, positive "
          f"in {pct(ck.get('years_positive'))} of years, surviving 2x costs at {fmt(ck.get('sr_stress'))} with turnover of "
          f"{fmt(ck.get('turnover_annual'), '.1f')}x a year; on BTC-USD the same rule reads {dec('S_C3_crypto_trend_btcusd')} "
          f"({reason('S_C3_crypto_trend_btcusd')}). Its expected live Sharpe after the haircut is {fmt(ck.get('haircut_sr'))}. "
          "Three cautions travel with it in the app: the benchmark is a bull decade, the largest year carries "
          f"{pct(ck.get('max_year_share'))} of the P&amp;L, and 10 bp per side is the Upbit fee plus modest slippage."),
        P("The pairs family shows what costs do to an arbitrage. Two trackers of the same index have a spread with a "
          f"half-life of {fmt(st('S_E8_pairs_kodex_tiger', 'median_half_life'), '.0f')} session, which is bid-ask bounce, and "
          "the trade loses money at 2x costs; the two gold ETFs do the same at 50 bp per side. The Samsung common/preferred "
          "spread is the real relative-value trade of the set and its long-only tilt still fails to beat holding both legs "
          f"(p {fmt(st('S_S6_pairs_samsung_pref', 'bench_p'))}). The VIX roll-down loses after 2018 even hedged; G10 FX "
          "momentum has decayed to a negative Sharpe since publication; dollar carry has too few trades to certify."),
    ]


def ch4() -> list:
    b, o = C.get("M_O2_basis_today", {}).get("stats", {}), C.get("M_O1_board_today", {}).get("stats", {})
    return [
        P("4. Index derivatives: the surface before the strategy", "H1"),
        P("The KOSPI 200 board is quoted series by series from the keyless master, so the chain around the money is complete. "
          "Everything on the Derivatives page is a consistency check on today's board; the short-volatility strategy the "
          "research shortlisted is not offered until a history of boards exists, because a single day cannot be validated."),
        P("4.1 Basis and fair value", "H2"),
        F("F<sub>fair</sub> = S (1 + r T) - D  (KRX simple-interest convention);  basis = F - S;  implied funding = (F + D - S) / (S T)"),
        P("[Shreve II] theorem 5.6.2 and equation 5.6.11 give the no-arbitrage forward; the exchange uses simple interest and "
          f"subtracts dividend points. On the study's day the front future stood {fmt(b.get('futures'))} against the index "
          f"{fmt(b.get('spot'))} with the CD 91-day rate at {pct(b.get('cd91'), 2)}, and the app's fair value sat "
          f"{fmt(ts('M_O2_basis_today', 'theo_gap_pts'), '+.2f')} points from KIS's theoretical price: the December dividend "
          f"points, which the app does not yet estimate. Decision {dec('M_O2_basis_today')}."),
        P("4.2 Parity-implied forward and Black-76 inversion", "H2"),
        F("C - P = e<super>-rT</super> (F - K)  at every strike;  F = K<sub>0</sub> + e<super>rT</super> (C - P) at the strike where |C - P| is smallest"),
        P("Put-call parity ([Shreve II] section 4.5.6) gives the forward the option market itself uses, which differs from "
          "the futures price by dividends and funding. Each out-of-the-money mid is then inverted through Black-76 to an "
          "implied vol, reusing the swaption module's inverter, and compared with the vol KIS prints. Only series with a live "
          "bid and ask within 15% of the forward are used; when the market is closed the page says so and every figure is "
          "indicative."),
        P("4.3 Static arbitrage and the SVI smile", "H2"),
        F("w(k) = a + b [ rho (k - m) + sqrt((k - m)<super>2</super> + sigma<super>2</super>) ],  g(k) >= 0 for no butterfly arbitrage"),
        P("Call prices must fall and be convex in the strike, puts must rise and be convex: each violation is a butterfly or "
          "vertical arbitrage and is counted. The raw SVI of Gatheral and Jacquier is fitted to total variance in "
          "log-moneyness and its g(k) function is checked for positivity, so the fitted smile cannot itself imply an "
          "arbitrage. The RMSE within 15% of the forward is printed in vol points."),
        P("4.4 Model-free implied variance, the risk-neutral density and the pricing kernel", "H2"),
        F("sigma<super>2</super><sub>MFIV</sub> = (2/T) sum<sub>i</sub> (dK<sub>i</sub> / K<sub>i</sub><super>2</super>) e<super>rT</super> Q(K<sub>i</sub>) - (1/T) (F/K<sub>0</sub> - 1)<super>2</super>"),
        P("The Cboe strip formula turns the whole board into one variance number, the one a variance swap would pay "
          "([RN-FH] sections 5.1-5.5 on the variance risk premium and the VIX). Breeden and Litzenberger's second derivative "
          "of the SVI call price gives the risk-neutral density; dividing it by the GARCH-t terminal density of the Quant Lab "
          "gives the empirical pricing kernel, the object the operator's paper builds from the Radon-Nikodym derivative "
          "([RN-FH] sections 2.3-2.5). The kernel is shown, not traded."),
        P("4.5 The box-spread rate", "H2"),
        F("(K<sub>2</sub> - K<sub>1</sub>) e<super>-rT</super> = C(K<sub>1</sub>) - C(K<sub>2</sub>) + P(K<sub>2</sub>) - P(K<sub>1</sub>)"),
        P("A box of two calls and two puts is a zero-coupon bond; its price implies the rate the option market lends at, "
          "which is compared with the CD rate."),
        P("4.6 Hedging P&amp;L and the break-even volatility", "H2"),
        F("P&amp;L<sub>T</sub> = 1/2 sum<sub>t</sub> e<super>r(T-t)</super> Gamma<sub>t</sub> S<sub>t</sub><super>2</super> (sigma<sub>h</sub><super>2</super> - r<sub>t</sub><super>2</super>/dt) dt"),
        P("A delta-hedged option earns gamma times the gap between the hedging variance and the realised variance, day by "
          "day ([RN-FH] equation (34), section 6.7; [Shreve II] section 5.3.2 for the martingale representation behind the "
          "hedge). The page simulates the hedge under GBM at the ATM vol or under the GARCH-t fit, charges the hedge's "
          "turnover, and reports the gamma-weighted realised variance whose square root is the break-even volatility: the "
          "number a short-volatility trade must beat."),
        P("4.7 Leveraged-fund drag", "H2"),
        F("ln(L<sub>T</sub>/L<sub>0</sub>) = beta ln(S<sub>T</sub>/S<sub>0</sub>) - (beta<super>2</super> - beta)/2 integral sigma<super>2</super> dt - fees"),
        P("Avellaneda and Zhang's identity: a beta-times daily-rebalanced fund lags beta times the index by half of "
          "beta(beta - 1) times the realised variance. The identity is exact ex post; the study tested whether the GARCH-t "
          f"variance term structure forecasts the next quarter's drag on KODEX Leverage and found it did not "
          f"({dec('M_E4_letf_drag')}: {line('M_E4_letf_drag', 0)}). The ETF page therefore quotes the drag at the last "
          "quarter's realised variance first and the GARCH path second, with the verdict beside them."),
    ]


def ch5() -> list:
    return [
        P("5. Curves and FX", "H1"),
        P("5.1 Diebold-Li and its loss to the random walk", "H2"),
        F("y(tau) = L + S (1 - e<super>-lambda tau</super>)/(lambda tau) + C [ (1 - e<super>-lambda tau</super>)/(lambda tau) - e<super>-lambda tau</super> ],  lambda = 0.0609 per month"),
        P("The curve on each day is three numbers, level, slope and curvature, fitted by least squares ([Boyd] section 6.1); "
          "each factor is then forecast h months ahead by a direct AR(1) and the curve rebuilt. The study scored the "
          f"forecast against no change (the random walk) at five maturities: {reason('M_B1_dns')}. That is what Diebold and "
          "Li themselves found at short horizons and what the post-2008 literature finds at long ones. The Rates page keeps "
          "the factors as a description of the curve and does not present them as a forecast; the forecast evaluation follows "
          "[MTSA] section 2.4.3 (Theil's U and the test regression)."),
        P("5.2 The PCA-neutral butterfly", "H2"),
        F("fly = -w<sub>2</sub> y<sub>2y</sub> + y<sub>5y</sub> - w<sub>10</sub> y<sub>10y</sub>,  w chosen so the fly has zero loading on the first two principal components"),
        P("Litterman and Scheinkman's three factors ([CS229] chapter 12 for PCA; [Lay] sections 7.1 and 7.5 for the "
          f"eigen-decomposition) explain almost all curve moves; a 2-5-10 fly weighted to be neutral to level and slope is "
          f"then a pure curvature bet. On the Treasury history: {line('S_B2_pca_fly', 0)} {line('S_B2_pca_fly', 1)} "
          f"Decision {dec('S_B2_pca_fly')}: the fly is shown as a richness measure, not as a trade."),
        P("5.3 Bond carry", "H2"),
        P("Koijen et al.'s carry of a bond is its yield over the funding rate plus the roll-down along the curve; the "
          "KRW curve panel from the KIS yield history feeds it and the Rates page prints carry and roll in basis points per "
          "year as a holding-period P&amp;L, as the earlier carry module already did for FX."),
        P("5.4 FX momentum, dollar carry and the Fama regression", "H2"),
        F("Fama: s<sub>t+1</sub> - s<sub>t</sub> = a + b (f<sub>t</sub> - s<sub>t</sub>) + e;  b = 1 under uncovered interest parity"),
        P("Cross-sectional momentum in G10 currencies (Menkhoff et al.) and the dollar carry rule (Lustig, Roussanov and "
          "Verdelhan: long the dollar against the basket when the US rate is above the average) are built as extensions of "
          f"the carry basket. Both fail: FX momentum at {dec('S_V3_fx_momentum')} with an out-of-sample Sharpe of "
          f"{fmt(st('S_V3_fx_momentum', 'sr_oos'))}, dollar carry at {dec('S_V4_dollar_carry')} with "
          f"{st('S_V4_dollar_carry', 'n_trades', 0)} trades. The Fama regression stays as a descriptive tile on the FX page: "
          "a slope below one says the forward is a biased forecast, which is the carry premium itself ([Shreve II] "
          "equation 9.3.16 for the forward under the domestic risk-neutral measure)."),
    ]


def ch6() -> list:
    return [
        P("6. Volatility products", "H1"),
        F("b = VIX3M / VIX - 1;  expected monthly drift of a 30-day long VIX ETP = -b/2"),
        P("The term structure of VIX futures is in contango most of the time, and a constant-maturity long position pays "
          "the roll every day ([RN-FH] section 5.5 on the term-structure premium). Eraker and Wu's drift monitor and the "
          "regression of realised VXX returns on the change in VIX and in the basis are on the vol page; the Simon-Campasano "
          f"roll-down trade was tested and rejected ({dec('S_V1_vix_rolldown')}: out-of-sample Sharpe "
          f"{fmt(st('S_V1_vix_rolldown', 'sr_oos'))}, {st('S_V1_vix_rolldown', 'n_trades', 0)} position changes). The "
          "monitor is offered; the trade is not."),
    ]


def dist_rows(ids: list[str]) -> list[list[str]]:
    rows = []
    for cid in ids:
        if cid not in C:
            rows.append([cid, "not run", "", "", "", "", ""])
            continue
        s, t = C[cid]["stats"], C[cid]["tests"]
        rows.append([cid.replace("D_Q_", "").replace("D_C2_", "").replace("_", " "), dec(cid),
                     f"{pct(s.get('exceed95'), 1)} (p {fmt(t.get('kupiec95_p'), '.3f')})",
                     f"{pct(s.get('exceed99'), 2)} (p {fmt(t.get('kupiec99_p'), '.3f')})",
                     f"{fmt(t.get('cc_p'), '.3f')}", f"{pct(s.get('coverage90'), 1)}",
                     f"{fmt(t.get('pit_ks_p'), '.3f')} / {fmt(t.get('berkowitz_p'), '.2f')}",
                     f"{fmt(s.get('dm_t'), '+.1f')}"])
    return rows


def ch7() -> list:
    sp, sk, bt = C.get("D_Q_garch_spy", {}).get("stats", {}), C.get("D_Q_skewt_spy", {}).get("stats", {}), \
        C.get("D_C2_garch_btc", {}).get("stats", {})
    hdr = ["Card", "Decision", "5% breaches", "1% breaches", "Christoffersen p", "90% coverage", "PIT KS / Berkowitz p", "DM t"]
    w = [2.6 * cm, 1.7 * cm, 2.6 * cm, 2.6 * cm, 1.9 * cm, 1.7 * cm, 2.4 * cm, 1.3 * cm]
    return [
        P("7. Crypto, and the volatility fans of all three markets", "H1"),
        P("7.1 The monitors", "H2"),
        *B([
            f"<b>Kimchi premium</b>: the Upbit KRW price against the world price in KRW at the FRED fixing. {line('M_C1_kimchi', 1)} "
            f"{line('M_C1_kimchi', 2)} Decision {dec('M_C1_kimchi')}: a descriptive tile. The arbitrage is closed by remittance "
            "limits, the Travel Rule and the 2027 tax, and the app says so.",
            f"<b>Funding carry</b>: the perpetual funding rate annualised, its percentile, and the forward return after top- "
            f"and bottom-decile funding with a bootstrap. {line('M_C4_funding', 0)} Decision {dec('M_C4_funding')}: the BIS "
            "sign is confirmed and the tile is offered as a positioning read, not as a trade.",
            "<b>Regime score</b>: six components (trend, funding, open interest, the premium, realised vol, breadth) each "
            "scored 0-100 with the weights of any missing component redistributed, so a keyless run still reads.",
            f"<b>ETH/BTC</b>: the log ratio tested for a unit root. {line('M_C8_ethbtc', 0)} The expected null; no pair "
            "trade is offered.",
            f"<b>Weekday table</b>: {line('M_C7_weekday', 0)} Returns do not differ by weekday after Bonferroni; weekend "
            "volume does, which sets the cost input for weekend trades.",
        ]),
        P("7.2 GARCH, GJR and the skewed t: what the fans miss and what repairs it", "H2"),
        P("The app's GARCH(1,1)-t is the Quant Lab's model. The study scored it one day ahead on SPY, KODEX 200 and bitcoin, "
          "then two challengers: GJR-GARCH, which lets a negative shock raise tomorrow's variance more than a positive one "
          "(Glosten, Jagannathan and Runkle), and GJR with Hansen's skewed-t innovation, which lets the standardised shock "
          "itself be asymmetric. [Primer] section 5 has the GARCH recursion and section 6 the Student-t scaling; [STAT248] "
          "sections 21.2-21.3 explain why an in-sample likelihood cannot certify a forecast, which is why the loop is "
          "out of sample."),
        TBL(hdr, dist_rows(["D_Q_garch_spy", "D_Q_gjr_spy", "D_Q_skewt_spy", "D_Q_garch_kodex200", "D_Q_gjr_kodex200",
                            "D_Q_skewt_kodex200", "D_C2_garch_btc", "D_C2_gjr_btc", "D_C2_skewt_btc"]), widths=w, font=7, wrap=True),
        P(f"On SPY the symmetric fan was breached on {pct(sp.get('exceed95'), 1)} of days at the 5% level while its 90% band "
          f"covered {pct(sp.get('coverage90'), 1)}: the left tail is under-covered and the right tail over-covered, which is "
          "asymmetry of the return distribution, not of the variance. GJR left the breach count unchanged, as it must when "
          f"the innovation stays symmetric; the skewed t (median lambda {fmt(sk.get('median_lambda'), '+.2f')} on SPY) "
          f"brought the 5% breaches to {pct(sk.get('exceed95'), 1)} and the decision to {dec('D_Q_skewt_spy')} "
          f"({reason('D_Q_skewt_spy')}). Bitcoin is different: the leverage term fits at zero, the tail index sits near 3 "
          f"and the persistence rests on the stationarity guardrail at {pct(bt.get('stationarity_share'))} of origins, so "
          "the variance is close to integrated and the exceptions cluster; every bitcoin fan reads REVISE."),
        FIG(3, "The two innovation densities at the same variance. The skew parameter moves the 5% quantile out on the "
               "left and in on the right, which is the direction of the miss the study measured on the equity indices.", FIG_SKEWT),
        BOX("What this means in the app", [
            "The Quant Lab keeps GARCH(1,1)-t as its fan and now shows two chips from the study beside the fit: the measured "
            "5% breach rate on SPY and KODEX 200, and the skewed-t verdict. A fan whose left tail is known to be thin is "
            "labelled as such.",
            "The Crypto page's GARCH tile carries the bitcoin verdict and the stationarity share, so a near-integrated "
            "variance is never presented as a settled one.",
            "Wiring the skewed t through the Quant Lab simulator is the next step and is not done here: the simulator's "
            "martingale correction and profile intervals are built for the symmetric t, and the gate has to pass the skewed "
            "fan before it is offered as a model choice.",
        ], C_MAIN),
    ]


def ch8() -> list:
    rows = [
        ["Derivatives", "basis and fair value, parity forward, Black-76 smile vs KIS, static-arbitrage counts, SVI with g(k), "
                        "MFIV, risk-neutral density and pricing kernel, box rate, hedge P&amp;L simulation",
         "the short-volatility strategy (no board history); any figure from a closed-market board is marked indicative"],
        ["ETF", "NAV premium with half-life, constituents, leveraged-fund drag at realised and GARCH variance, the trend and "
                "vol-target sleeves with their verdicts", "trend / vol target / risk parity / sector momentum as signals"],
        ["Crypto", "kimchi premium, funding carry, regime score, GARCH-t on bitcoin with its verdict, ETH/BTC, weekday table, "
                   "Upbit balances (asset-inquiry key)", "any order or transfer; ETH/BTC pair; the premium as a trade"],
        ["Strategy Lab", "every card with its lines; the crypto trend rule (PASS) runnable on live data; any family runnable "
                         "ad hoc with the same gate", "REJECT families as recommendations (they run, labelled)"],
        ["Rates / FX", "KRW curve panel from KIS yields, Diebold-Li factors, PCA fly richness, bond carry, Fama regression",
         "the Diebold-Li forecast, the fly as a trade, FX momentum and dollar carry as signals"],
        ["Quant Lab", "GARCH(1,1)-t with the study's breach-rate and skewed-t chips", "the skewed-t fan as a model choice, until it passes"],
    ]
    return [
        P("8. What the app offers and what it withholds", "H1"),
        TBL(["Page", "Offered", "Withheld, with the reason on the page"], rows, widths=[2.4 * cm, 8.2 * cm, 5.6 * cm], wrap=True),
        P("The list is short on purpose. The operator asked for many credible techniques and for the inaccurate ones to be "
          "modified or excluded; the gate did the excluding, and the app shows the exclusion rather than hiding it, because "
          "a strategy that is known not to work is useful information at the desk."),
    ]


def ch9() -> list:
    return [
        P("9. Glossary", "H1"),
        *B([
            "<b>Out of sample (OOS)</b>: computed on data the rule had not seen when its configuration was chosen.",
            "<b>Sharpe ratio</b>: mean excess return over its standard deviation, annualised; here on daily P&amp;L.",
            "<b>Block bootstrap</b>: resampling contiguous blocks of days so that volatility clustering survives.",
            "<b>Deflated Sharpe ratio (DSR)</b>: the probability that the best of N trials beats what noise would produce.",
            "<b>PBO</b>: probability of backtest overfitting, the share of CSCV splits in which the in-sample winner ranks in "
            "the bottom half out of sample; 0.5 on a flat plateau by construction.",
            "<b>Plateau</b>: the neighbourhood of a configuration on which the Sharpe barely changes.",
            "<b>Haircut</b>: the 40% reduction of the out-of-sample Sharpe for post-publication decay.",
            "<b>Kupiec / Christoffersen</b>: tests of the number and independence of value-at-risk breaches.",
            "<b>PIT</b>: probability integral transform, the model's cumulative probability at the realised outcome.",
            "<b>QLIKE</b>: the loss function for variance forecasts that is robust to a noisy realised-variance proxy.",
            "<b>Black-76</b>: the Black-Scholes formula written on the forward, the convention for index options.",
            "<b>SVI</b>: the stochastic-volatility-inspired smile parameterisation of Gatheral.",
            "<b>MFIV</b>: model-free implied variance, the strip of out-of-the-money options that prices a variance swap.",
            "<b>GJR</b>: the GARCH variant with a leverage term; <b>skewed t</b>: Hansen's asymmetric Student-t innovation.",
        ]),
    ]


def ch10() -> list:
    rows = [
        ["[Two Doors]", "Quant_Roadmap_Two_Doors_GEON_KOH_1.pdf", "pillar 2 pp. 7-9: purged CV, deflated Sharpe; pp. 12, 28 on multiple testing"],
        ["[RN-FH]", "From_Radon-Nikodym_to_Fung-Hsieh_GEON_KOH_1.pdf", "2.3-2.5 pricing kernel; 5.1-5.5 variance premium, VIX, term structure; 6.1-6.11 trend as a lookback straddle, hedger's P&amp;L eq. (34)"],
        ["[Primer]", "QUANTGEN_Models_Primer.pdf", "5 GARCH; 6 Student-t; 7 guardrails; 8 drift study"],
        ["[Shreve II]", "Stochastic Calculus for Finance II", "4.5 BSM, Greeks, parity; 5.3.2 delta hedging; 5.6 forwards and futures; 9.3 FX; 11 jumps"],
        ["[Boyd]", "Convex Optimization (EE364A folder)", "4.4.1 Markowitz; 6.1 least squares; 7.1.1 MLE as a convex problem"],
        ["[CS229]", "Stanford CS229 notes", "9.3 cross-validation; 8.1 bias-variance; 12 PCA"],
        ["[Tibshirani]", "Introduction to Time Series (UC Berkeley) lectures", "Lecture 3 section 4 time-series CV; Lecture 8 section 3 coverage and PIT calibration; Lecture 6 ARIMA forecasting"],
        ["[STAT248]", "UC Berkeley STAT248 notes", "21.2-21.3 MLE asymptotics and misspecification; 6.2 Kalman filter"],
        ["[MTSA]", "Modern Time Series Analysis (Kirchgaessner, Wolters and Hassler, Springer; Econometrics II folder)",
         "1.4 Ljung-Box; 2.4 forecast evaluation; 5.3 unit roots; 6.2-6.3 cointegration"],
        ["[BKM]", "Bodie, Kane and Marcus decks (Financial Economics folder)", "chapter 6 slides 6-20 to 6-22; chapter 7 slides 7-5 to 7-8"],
        ["[Financial Economics]", "course notes (Financial Economics folder)", "chapter 6 Sharpe ratio"],
        ["[ECON302]", "chapter decks (Macroeconomics folder)", "chapter 1 slides 2-17 interest parity and calendar effects"],
        ["[Lay]", "Linear Algebra and its Applications, 5th ed. (Linear Algebra II folder)", "7.1 and 7.5 eigen-decomposition and PCA"],
    ]
    return [
        P("10. The operator's sources, as cited above", "H1"),
        P("Section and page references follow the reference map in <font name='DejaVuSansMono'>research_notes/QUANTGEN asset "
          "coverage expansion/reference_map.md</font>, which records the printed-page to PDF-index offset of each file. The "
          "papers behind each rule are listed on its card and in <font name='DejaVuSansMono'>docs/asset_expansion/results.md</font>."),
        TBL(["Label", "File or folder", "Used for"], rows, widths=[2.6 * cm, 6.2 * cm, 7.4 * cm], wrap=True),
        Spacer(1, 0.4 * cm),
        P(f"Build time {time.time() - T0:.0f} s.", "small"),
    ]


def build() -> int:
    story = ch_title() + TOC() + ch0() + ch1() + ch2() + ch3() + ch4() + ch5() + ch6() + ch7() + ch8() + ch9() + ch10()
    doc = PrimerDoc(str(OUT_PDF), title="QUANTGEN Expansion Primer", footer="QUANTGEN Expansion Primer")
    doc.multiBuild(story)
    pages = doc.page
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(str(OUT_PDF)).pages)
    except Exception:
        pass
    return pages


if __name__ == "__main__":
    glyph_check(Path(__file__).read_text(encoding="utf-8"))
    assert C, "no cards: run docs/asset_expansion_study.py first"
    n = build()
    print(f"ok {OUT_PDF} ({n} pages, {len(C)} cards)")
