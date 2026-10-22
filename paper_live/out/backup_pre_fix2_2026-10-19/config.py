"""Pre-registered parameters for the 5-hour live paper session (2026-10-07).

Everything that decides a trade is written here before the session starts; the
SHA-256 of this file is stamped into every output so a later edit is visible.
Nothing in paper_live places a real order: fills are simulated against delayed
yfinance 1-minute bars.
"""
from __future__ import annotations

from datetime import datetime, timezone

# --- session clock (user asked for "5 hours from now" at 2026-10-07 20:42 KST)
WINDOW_START_UTC = datetime(2026, 10, 7, 11, 42, tzinfo=timezone.utc)   # 20:42 KST
WINDOW_END_UTC = datetime(2026, 10, 7, 16, 42, tzinfo=timezone.utc)     # 01:42 KST

START_EQUITY = 500.0

# --- QUANTGEN pre-registered costs, read from core.quant.validate.COST_BP_PER_SIDE.
# 2026-10-18: was a copy of the table, with LSE charged the US 50 bp rate as a proxy. QUANTGEN has
# no LSE row, so LSE keys now declare cost="lse" and are signal-only: the engine refuses a fill on
# any class the table cannot cost instead of borrowing another venue's rate.
from core.quant.validate import cost_bp as _qg_cost_bp  # noqa: E402

COST_CLASS_BP = {k: _qg_cost_bp(k) for k in ("us", "futures", "fx")}

# --- sessions in UTC for 2026-10-07 (BST / EDT). CME and FX are open all window.
SESSIONS_UTC = {
    "LSE": ((7, 0), (15, 30)),
    "US": ((13, 30), (20, 0)),
    "CME": ((0, 0), (21, 0)),
    "FX": ((0, 0), (23, 59)),
}

# key: signal instrument. group = logistic-coefficient group; venue = session;
# cost = COST_CLASS_BP key; short = how a short is expressed
#   "direct"  -> negative notional (futures / FX synthetic notional, CFD-equivalent)
#   "<TICKER>" -> buy that 1x inverse ETF instead (a $500 cash account cannot short)
#   None      -> long-only
# quote_ccy: 'USD', or 'GBP' (P&L translated with GBPUSD=X); usd_base marks USDxxx pairs
UNIVERSE = {
    # CME futures (Yahoo continuous, ~10 min delayed)
    "ES=F": dict(group="equity", venue="CME", cost="futures", short="direct", name="E-mini S&P 500 fut"),
    "NQ=F": dict(group="equity", venue="CME", cost="futures", short="direct", name="E-mini Nasdaq-100 fut"),
    "RTY=F": dict(group="equity", venue="CME", cost="futures", short="direct", name="E-mini Russell 2000 fut"),
    "ZN=F": dict(group="rates", venue="CME", cost="futures", short="direct", name="10y T-Note fut"),
    "ZB=F": dict(group="rates", venue="CME", cost="futures", short="direct", name="30y T-Bond fut"),
    "GC=F": dict(group="commod", venue="CME", cost="futures", short="direct", name="Gold fut"),
    "CL=F": dict(group="commod", venue="CME", cost="futures", short="direct", name="WTI crude fut"),
    # FX spot (near real time)
    "EURUSD=X": dict(group="fx", venue="FX", cost="fx", short="direct", name="EUR/USD"),
    "GBPUSD=X": dict(group="fx", venue="FX", cost="fx", short="direct", name="GBP/USD"),
    "USDJPY=X": dict(group="fx", venue="FX", cost="fx", short="direct", name="USD/JPY", usd_base=True),
    "AUDUSD=X": dict(group="fx", venue="FX", cost="fx", short="direct", name="AUD/USD"),
    # LSE (~15-19 min delayed), long-only; signal-only since 2026-10-18 (no QUANTGEN cost row)
    "ISF.L": dict(group="equity", venue="LSE", cost="lse", short=None, quote_ccy="GBP", name="iShares Core FTSE 100"),
    "HSBA.L": dict(group="equity", venue="LSE", cost="lse", short=None, quote_ccy="GBP", name="HSBC"),
    "SHEL.L": dict(group="equity", venue="LSE", cost="lse", short=None, quote_ccy="GBP", name="Shell"),
    "AZN.L": dict(group="equity", venue="LSE", cost="lse", short=None, quote_ccy="GBP", name="AstraZeneca"),
    # NYSE / Nasdaq ETFs; shorts through 1x inverse ETFs
    "SPY": dict(group="equity", venue="US", cost="us", short="SH", name="SPDR S&P 500"),
    "QQQ": dict(group="equity", venue="US", cost="us", short="PSQ", name="Invesco QQQ"),
    "IWM": dict(group="equity", venue="US", cost="us", short="RWM", name="iShares Russell 2000"),
    "TLT": dict(group="rates", venue="US", cost="us", short="TBF", name="iShares 20+y Treasury"),
    "IEF": dict(group="rates", venue="US", cost="us", short=None, name="iShares 7-10y Treasury"),
    "HYG": dict(group="rates", venue="US", cost="us", short=None, name="iShares HY credit"),
    "GLD": dict(group="commod", venue="US", cost="us", short=None, name="SPDR Gold"),
    "USO": dict(group="commod", venue="US", cost="us", short=None, name="US Oil Fund"),
}
INVERSE_ETFS = ("SH", "PSQ", "RWM", "TBF")
FX_FOR_GBP = "GBPUSD=X"
GROUPS = ("equity", "rates", "commod", "fx")

# --- shared probability model (new, unvalidated intraday adaptation)
HORIZON_MIN = 60            # each "event" is: is the instrument up 60 minutes from now?
FEATURE_WINDOWS = (60, 15)  # momentum z-scores over these windows (minutes)
EWMA_HALFLIFE_BARS = 100    # causal EWMA of 5-minute squared returns for feature scaling
CALIB_TEST_DAYS = 12        # last N sessions of the 60-day 5m history are out-of-sample
LOGIT_L2 = 1e-2
P_CLIP = (0.05, 0.95)

# --- account Q: QUANTGEN rules
Q = dict(
    cadence_min=5,
    vol_target_ann=0.15,     # rules_v2.0.0 vol_target.US.target_ann
    slots=6,                 # risk budget split
    max_positions=6,
    max_weight=0.35,         # concentration cap per position
    gross_cap=1.0,           # P2: nothing exceeds 1.0x
    conviction_full=0.10,    # |p-0.5| at which the full slot budget is used
    min_edge_pp=0.02,        # ignore coin flips below 2 pp
    cost_gate_mult=1.0,      # expected move must exceed round-trip cost x this
    stop_sigma=2.0,          # protective stop at 2 sigma_H against
    ladder=((-0.08, 0.5), (-0.12, 0.5)),  # drawdown ladder steps (rules_v2.0.0)
    hard_stop=-0.15,
    flip_exit_pp=0.02,       # exit if p crosses 0.5 by more than this against the position
    min_minutes_to_close=60,
)

# --- account L: LAZYOWEN rules ported from the Polymarket guide
L = dict(
    cadence_min=10,
    edge_pp=0.08,            # trade only when |p - market| >= 8 pp (market = 0.5)
    half_kelly=True,
    max_stake=0.06,          # <= 6% of balance per trade
    max_positions=5,
    max_slippage=0.03,       # orderbook slippage <= 3% (cost per side as the proxy)
    decay_exit_pp=0.05,      # exit if fair probability moves 5 pp against entry
    halt_drawdown=-0.40,     # stop and report at -40% from peak
    min_minutes_to_close=120,  # skip markets that "end within 2 hours"
    min_bars_last_hour=20,   # liquidity proxy (>= 20 one-minute prints in the last hour)
)

MAX_STALENESS_MIN = 25.0     # no new entry on a quote older than this

# --- added after calibration, BEFORE the live start (2026-10-07 ~12:05 UTC):
# calibration showed out-of-sample AUC 0.50-0.53, so two more accounts separate the
# signal from cost drag and from plain market exposure. Same engine, same data.
LOWCOST_BP = {"us": 2.0, "futures": 1.0, "fx": 1.0}   # institutional-style costs (sensitivity only)

# account QG-CORE: QUANTGEN's evidence-backed mode -- risk-budgeted allocation, no timing.
# Inverse GARCH-t vol weights over long risk-premium sleeves on the cheapest open venue
# (CME futures, 5 bp), vol target 15% with gross <= 1.0, ladder as account Q, held to window end.
CORE = dict(
    sleeves=("ES=F", "NQ=F", "RTY=F", "ZN=F", "ZB=F", "GC=F", "CL=F"),
    vol_target_ann=0.15,
    avg_corr=0.2,
    gross_cap=1.0,
    cadence_min=5,
)

# --- second revision, still BEFORE the live start (~12:15 UTC):
# (1) the logistic is refit with NO intercept: QUANTGEN's drift study (docs/drift_study) found sample
#     drift useless (corr -0.01), and the first fit's rates intercept was exactly such a drift.
# (2) with a zero-drift calibrated p, |p-0.5| almost never reaches 8 pp, and the cost gate blocks
#     every tactical entry even at 1 bp; the LOWCOST account is dropped (the arithmetic is reported).
# (3) QG-TREND: QUANTGEN's only gate-PASS strategy family (card C3, core.quant.strategies.crypto_trend:
#     sign votes over lookbacks 7/14/21/28 and SMAs 10/20/50/100/200 with 0.2 hysteresis, long/flat),
#     transplanted unchanged to 5-minute bars on every venue. Out-of-domain and unvalidated intraday.
# (4) LAZYOWEN-NAIVE: the LAZYOWEN rules fed a deliberately uncalibrated "opinion" probability,
#     p_naive = Phi(0.5 * z60) (momentum persists), standing in for Grok's self-assessed fair
#     probability, which the guide itself says the bot cannot verify.
TREND = dict(
    cadence_min=5,
    vol_target_ann=0.15, slots=6, max_weight=0.35, gross_cap=1.0,
    ladder=((-0.08, 0.5), (-0.12, 0.5)), hard_stop=-0.15,
    min_minutes_to_close=30,   # no new entry in the last 30 minutes of a cash session
    min_bars=210,              # 5-minute bars needed before the 200-bar SMA is defined
)
NAIVE_KAPPA = 0.5

# --- 2026-10-18 revision, after Run 1 (10-07) and Run 2 (10-12), before any Run 3:
# (1) Shared cost gate, per account (gate_mult; None = off). A perfect up/down call over the
#     60-minute horizon earns on average the mean absolute move, sigma_h * sqrt(2/pi); a forecast
#     right with probability p earns |2p-1| of that. The engine refuses a fill when that expected move
#     cannot beat gate_mult x the round-trip cost of the ticker actually traded. A rule with no
#     probability (C3 trend) is held to the perfect-forecast bound. QG-TACTICAL had this test inline
#     at 1x on the signal's table rate; it now also runs at fill time on the traded ticker's cost.
#     The original accounts keep their rules; the gated LAZYOWEN-NAIVE twins are new trials at 1x
#     (the old QG-TACTICAL level) and 2x (QUANTGEN's GATE['cost_stress']), reported side by side.
#     The 2x level came from validate.GATE, not from these replays; the replay counterfactual that
#     motivated the gate (NAIVE -$5.66 -> -$0.07 a session) is what Run 3 must confirm out of sample.
# (2) QG-TREND (C3 on 5-minute bars) is retired from live runs. No bar length or hysteresis in either
#     frozen grid shows positive gross edge (max |gross t| 1.1 base, 1.8 KRX); slower bars only cut costs,
#     and the gate cuts its KRX loss only 25% at 1x (KRX ETFs are cheap enough to pass). C3 stays
#     validated on daily bars only. The rule stays in engine.step_trend so the grid keeps measuring it.
ACCOUNTS = (
    dict(name="QG-TACTICAL", rules="quantgen", costs="COST_CLASS_BP", prob="cal", gate_mult=1.0),
    dict(name="QG-CORE", rules="core", costs="COST_CLASS_BP", prob="cal"),
    dict(name="LAZYOWEN-CAL", rules="lazyowen", costs="COST_CLASS_BP", prob="cal"),
    dict(name="LAZYOWEN-NAIVE", rules="lazyowen", costs="COST_CLASS_BP", prob="naive"),
    dict(name="LAZYOWEN-NAIVE-G1", rules="lazyowen", costs="COST_CLASS_BP", prob="naive", gate_mult=1.0),
    dict(name="LAZYOWEN-NAIVE-G2", rules="lazyowen", costs="COST_CLASS_BP", prob="naive", gate_mult=2.0),
)


# --- profile switch (added 2026-10-12). PAPER_PROFILE=krx runs the KOSPI-hours session;
# every output then goes to out_krx/. The base profile (2026-10-07 run) is unchanged.
import os  # noqa: E402

PROFILE = os.environ.get("PAPER_PROFILE", "base")
FX_FOR = {"GBP": (FX_FOR_GBP, False)}      # quote ccy -> (USD-rate ticker, invert the quote)
CASH_VENUES = ("LSE", "US")
SESSION_MIN = {"US": 390, "LSE": 510}

if PROFILE == "krx":
    WINDOW_START_UTC = datetime(2026, 10, 12, 1, 20, tzinfo=timezone.utc)   # 10:20 KST
    WINDOW_END_UTC = datetime(2026, 10, 12, 6, 20, tzinfo=timezone.utc)     # 15:20 KST, KRX closing auction
    # ETFs also pay QUANTGEN's tick floor at the traded price (engine._bp; 6-12 bp on inverse ETFs)
    COST_CLASS_BP = {**COST_CLASS_BP, **{k: _qg_cost_bp(k) for k in ("krx_etf", "krx_stock")}}
    SESSIONS_UTC = {**SESSIONS_UTC, "KRX": ((0, 0), (6, 30))}
    CASH_VENUES = ("KRX",)
    SESSION_MIN = {"KRX": 390}
    FX_FOR = {"KRW": ("KRW=X", True)}
    MAX_STALENESS_MIN = 30.0    # Yahoo's KRX bars run ~20 min late (25 would reject most KRX entries)
    _k = dict(venue="KRX", quote_ccy="KRW")
    UNIVERSE = {
        "069500.KS": dict(group="equity", cost="krx_etf", short="114800.KS", name="KODEX 200", **_k),
        "229200.KS": dict(group="equity", cost="krx_etf", short="251340.KS", name="KODEX KOSDAQ150", **_k),
        "148070.KS": dict(group="rates", cost="krx_etf", short=None, name="KOSEF 10Y KTB", **_k),
        "132030.KS": dict(group="commod", cost="krx_etf", short=None, name="KODEX Gold Futures(H)", **_k),
        "261240.KS": dict(group="fx", cost="krx_etf", short="261250.KS", name="KODEX USD Futures", **_k),
        "005930.KS": dict(group="equity", cost="krx_stock", short=None, name="Samsung Electronics", **_k),
        "000660.KS": dict(group="equity", cost="krx_stock", short=None, name="SK hynix", **_k),
        "005380.KS": dict(group="equity", cost="krx_stock", short=None, name="Hyundai Motor", **_k),
        "105560.KS": dict(group="equity", cost="krx_stock", short=None, name="KB Financial", **_k),
        "ES=F": UNIVERSE["ES=F"], "NQ=F": UNIVERSE["NQ=F"], "ZN=F": UNIVERSE["ZN=F"],
        "GC=F": UNIVERSE["GC=F"], "CL=F": UNIVERSE["CL=F"],
        "KRW=X": dict(group="fx", venue="FX", cost="fx", short="direct", name="USD/KRW", usd_base=True),
        "USDJPY=X": UNIVERSE["USDJPY=X"], "EURUSD=X": UNIVERSE["EURUSD=X"], "AUDUSD=X": UNIVERSE["AUDUSD=X"],
    }
    INVERSE_ETFS = ("114800.KS", "251340.KS", "261250.KS")
    CORE = {**CORE, "sleeves": ("069500.KS", "229200.KS", "148070.KS", "132030.KS", "ES=F", "ZN=F")}
