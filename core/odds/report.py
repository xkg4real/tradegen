"""The odds report (spec 7.5; odds plan contract section 10): column statistics, the bug checks, honest number
formats, the flags, the one sentence catalogue, rendering and the language guard. simulate imports report, never
the reverse. Pure: no clock, no file, no network (Q42)."""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
from scipy import stats

from core.odds import bold, costs, plan

LADDER = (1.10, 1.25, 2.0, 10.0)                  # x W0; then the target (simulate reads report.LADDER)
COST_DOMINATED_SHARE = 0.10                       # Q43 (simulate reads report.COST_DOMINATED_SHARE)
CP_LEVEL = 0.95
DELTA = 1e-4                                      # HIDDEN_EDGE's delta (spec 7.5)
RED_ALPHA = 0.001                                 # CEILING_BREACH red: one-sided 1 - RED_ALPHA / m
CARRY = costs.LIMIT_DOWN_CARRY_COST_MULTIPLIER


@dataclass(frozen=True, kw_only=True)
class ColumnStats:
    """One column: a member's model under one cost scenario, n paths (contract 10.1). Counts are paths; values are
    KRW. `brackets` holds arrays, so it stays out of ==, repr and the hash."""
    key: str
    member: str
    scenario: str
    n: int
    reached: int                  # first passage: liquidation value >= T at some check (the ceiling's quantity)
    reached_outcome: int          # moonshot REACHED outcomes (<= reached: a locked exit can miss T); 0 for compounding
    ended_at_or_above: int        # terminal value >= T
    at_floor: int
    running: int
    locked_at_horizon: int
    rungs: tuple[int, ...]        # counts of terminal value >= LADDER[i] x W0, then >= T
    median: float
    p5: float
    mean: float
    mean_se: float                # std(V_term, ddof 1) / sqrt(n)
    mean_cost: float
    g_se: float                   # std(V_term + cost_term, ddof 1) / sqrt(n): the SE of the average-line statistic
    kept_lo: float | None         # min and max terminal value of AT_FLOOR paths (None without one)
    kept_hi: float | None
    x_mean: float                 # HIDDEN_EDGE sample X = G_tau - W0 (ddof 1 variance) and its range R (section
    x_var: float                  # 10.3, fixed before the run; nan when no finite range was computed, inf unbounded)
    x_range: float
    wins: int                     # take-profit fills
    losses: int                   # stop fills
    unresolved: int               # brackets closed otherwise or still open at the horizon
    brackets: tuple[np.ndarray, np.ndarray] | None = field(default=None, compare=False, repr=False)
    # (r, d) of up to BRACKET_SAMPLE brackets of chunk 0; compare two columns through dataclasses.replace(col,
    # brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range) (contract 10.1 as Task 9 amends it)
    band_edge_share: float
    band_edge_sessions: int       # simulated sessions that opened at a band edge
    worst_gap: float              # the largest (stop - fill) / entry of a stop fill below its stop
    trades: int                   # paths with an entry fill


@dataclass(frozen=True, kw_only=True)
class HiddenEdge:
    """HIDDEN_EDGE on one no-edge column: a drift check of the simulator, never a check of the model (Q32)."""
    status: str      # "pass" | "red_gain" | "red_loss" | "unavailable" (GARCH-t) | "unbounded" (k_x >= 1, 10.3)
                     # | "not_applicable"
    mean: float
    bound: float
    range_: float
    n: int


@dataclass(frozen=True, kw_only=True)
class Flag:
    code: str
    level: str                     # "red" | "amber" | "info"
    key: str                       # a CATALOGUE key; "" for a flag another line carries (BELOW_RESOLUTION)
    slots: Mapping[str, str]


@dataclass(frozen=True, kw_only=True)
class OddsReport:
    """One plan card (spec 7.5). A refused report has no columns, no flags and no probability."""
    plan_hash: str
    plan_index: int
    plan_count: int
    refused: plan.Refusal | None
    track: str
    stake: float
    target: float
    floor: float
    l_min: float                   # the floor under floor_safe sizing (replay legs included), else 0.0 (Q32)
    horizon_days: int
    n: int
    sizing: str                    # "floor_safe" | "stop_based": picks the ceiling wording
    model_key: str                 # model.bootstrap | model.garch | model.replay
    model_slots: Mapping[str, str]     # the model line's slots; an OKX card adds cap and capkrw (okx.cap)
    columns: tuple[ColumnStats, ...]
    headline: str                  # the headline column's key
    spread: tuple[float, float] | None     # (lowest lower, highest upper) bound over the other base members
    spread_kind: str               # "other" | "krx" | "blocks" | "none" (Q31)
    notes: tuple[tuple[str, str], ...]     # (member, failed check) of each dropped member
    ceiling: float                 # bold.ceiling(stake, l_min, target)
    structural_cap: float | None
    structural_sessions: int | None
    tax_basis: str
    cost_words_key: str            # cost.tax for KRX_stock_book, else cost.fees (Q37)
    hidden: HiddenEdge | None
    flags: tuple[Flag, ...]
    assumed: Mapping[str, float] | None    # w, p0, u, nb (math.inf allowed), resolved, theta
    replay: Mapping[str, float] | None     # y0, y1, cut, bench_sr, haircut_sr, diff, ci_lo, ci_hi, fstar, h, growth,
                                           # growth_iid
    comparison: tuple[int, int, int]       # (K, J, R)
    provenance: Mapping[str, object]


CATALOGUE: Mapping[str, str] = MappingProxyType({
    # model and sizing
    "model.bootstrap": (
        "Model: a two-point bootstrap of the daily moves of {symbol} in won, {first} to {last} ({rows} sessions), in "
        "which nobody has an edge. Price checks at the open and the close only."
    ),
    "model.garch": (
        "Model: GARCH-t fitted to the daily won returns of {symbol}, {first} to {last} ({rows} sessions), in which "
        "nobody has an edge. Price checks at the close only."
    ),
    "model.replay": (
        "Model: the tested strategy's own out-of-sample daily results, {first} to {last} ({rows} sessions), resampled "
        "in blocks of about {block} days. Price checks at the close only."
    ),
    "sizing.floor": "Floor-protected sizing: your floor of KRW {floor} holds even if this position goes to zero.",
    "sizing.stop": "Stop-based sizing: a gap past the stop can take you below your floor of KRW {floor}.",
    "okx.cap": (
        "Each simulated OKX entry is capped at {cap} of this plan's stake (KRW {capkrw}), the cap the gate applies."
    ),
    "fx.us": (
        "US prices are turned into won with Yahoo's KRW=X rate: the open with the previous day's close and the close "
        "with the same day's close."
    ),
    "kelly.label": "This stake aims at long-run growth, not at reaching your target.",
    "period.month": "month",
    "period.months": "months",
    "period.day": "{h}-day period",
    "period.days": "{h}-day periods",
    # typical result and average
    "typical.median": "The middle {one} ends with KRW {median}.",
    "typical.floor": (
        "In {p} of {many} you end at your floor, keeping between KRW {lo} and KRW {hi}, and can no longer trade."
    ),
    "typical.nofloor": "No simulated {one} ended at your floor.",
    "average.agrees": (
        "Averaged over all simulated {many}: about KRW {expected} ({costwords} average KRW {cost}; the simulation's "
        "own average, KRW {mean} ± {se}, agrees). That average includes rare jackpots and is not what usually happens."
    ),
    "average.differs": (
        "The simulation's own average, KRW {mean} ± {se}, does not match your stake minus the average {costwords} (KRW "
        "{expected}); see the bug check below."
    ),
    "average.gain": (
        "Averaged over all simulated {many}: an average gain of KRW {gain}, only if the edge in this column is real."
    ),
    "average.loss": (
        "Averaged over all simulated {many}: an average loss of KRW {loss}, even with the edge in this column."
    ),
    "cost.fees": "fees",
    "cost.tax": "fees and the securities transaction tax",
    "cost.delist": "{base} and the delisting stress loss",
    # headline, ladder, plain sentence, precision
    "headline.moonshot": "Chance of reaching KRW {target} before income tax: {p}.",
    "headline.compounding": (
        "Was worth KRW {target} at some price check in {k} of {n} made-up {many} ({pk}); ended at or above it in {k2} "
        "({pk2})."
    ),
    "headline.floor": "Chance of ending at your floor: {p}.",
    "ladder.head": "Ended at or above:",
    "ladder.rung": "{label} (KRW {value}): {p}",
    "ladder.impossible": "{label} (KRW {value}): IMPOSSIBLE for this buy-and-hold plan",
    "ladder.p10": "+10%",
    "ladder.p25": "+25%",
    "ladder.x2": "2 times your stake",
    "ladder.x10": "10 times your stake",
    "ladder.target": "your target",
    "ladder.spread": "Middle result KRW {median}; 5th percentile KRW {p5}.",
    "plain.hit": (
        "In {n} made-up {many} (from a model in which nobody has an edge, not real history), this plan reached KRW "
        "{target} before income tax in {k}, {about} (counting noise alone: between {hi} and {lo}; {spread}; {bugs}, "
        "and nothing here covers the model being wrong)."
    ),
    "plain.none": (
        "In {n} made-up {many} (from a model in which nobody has an edge, not real history), this plan never reached "
        "KRW {target} before income tax (below resolution: under about 3 in {n}; {spread}; {bugs}, and nothing here "
        "covers the model being wrong)."
    ),
    "bugs.coarser": "the bug checks are coarser than these ranges",
    "bugs.finer": "the bug check's resolution is printed below",
    "cap.p": "at most {c}, the ceiling (the simulated {k} in {n} is above it only through counting noise)",
    "spread.other": "other models give {a} to {b}",
    "spread.krx": (
        "the same model with other block lengths gives {a} to {b}; no second model family is available for KRX"
    ),
    "spread.blocks": "the same model with other block lengths gives {a} to {b}",
    "spread.none": "no other model could be run here",
    "spread.dropped": "{member} was left out because its {check} check failed",
    "member.bootstrap": "the two-point bootstrap",
    "member.half": "the bootstrap at half the block length",
    "member.double": "the bootstrap at twice the block length",
    "member.garch": "GARCH-t",
    "member.refit": "the GARCH-t refit",
    "check.deterministic": "deterministic",
    "check.statistical": "statistical",
    "check.fit": "fit",
    "check.refit": "refit",
    "structural.impossible": (
        "IMPOSSIBLE for this buy-and-hold plan: KRX's daily band allows at most {cap}× in these {s} sessions."
    ),
    "structural.notrade": "No simulated {one} made a trade, so these numbers describe holding cash.",
    # tax, ceiling, base rates
    "tax.krx": (
        "Tax: this KRX holding is treated as a small holder's, so its gains pay no capital gains tax here; any "
        "securities transaction tax is inside the costs."
    ),
    "tax.overseas": (
        "Tax: overseas share gains above KRW 2.5 million a year are taxed at 22%. Not simulated: these numbers are "
        "before income tax."
    ),
    "tax.crypto": (
        "Tax: crypto gains are due to be taxed at 22% from 2027 (unless postponed again). Not simulated: these numbers "
        "are before income tax."
    ),
    "ceiling.noedge": "No plan without a real edge that keeps this floor can beat {c}.",
    "ceiling.nofloor": "No plan without a real edge can beat {c}.",
    "ceiling.edge": "Without the edge assumed here, no plan that keeps this floor can beat {c}.",
    "ceiling.edgenf": "Without the edge assumed here, no plan can beat {c}.",
    "research.estimate": (
        "The research found no measured chance of this account growing 1,000 times in a month. Its reasoned estimates: "
        "0.01% or less in general, roughly 0.01% to 0.03% for long far-out-of-the-money US options, and below 0.01% "
        "for domestic crypto spot."
    ),
    "baserate.kalshi": (
        "Kalshi takers lost about 32% of the amount staked and makers about 10% (Bürgi, Deng and Whelan working paper, "
        "2025-26; not re-verified)."
    ),
    "baserate.esma": "74-89% of EU retail CFD accounts lose money (national regulators' data, ESMA, 27 March 2018).",
    "baserate.sebi": "87.7% of Indian retail equity-derivatives traders lost in FY26 (SEBI).",
    "baserate.krderiv": (
        "Korean retail lost about KRW 458 billion a year on overseas derivatives, 2020 to H1 2025, with no profitable "
        "year."
    ),
    "baserate.kr2020": (
        "In a 2020 study of 204,004 Korean retail accounts, 46% lost money, and 62% of new investors did."
    ),
    # columns
    "column.stress": "With costs doubled:",
    "column.delist": "If {symbol} were delisted right after you buy, losing {h}% of its value:",
    "assumed.lead": (
        "These numbers are only as true as the win rate you typed ({w}). This bracket's no-edge win rate is {p0} ({u} "
        "of brackets end unresolved)."
    ),
    "assumed.nb": "Telling them apart would take about {nb} recorded brackets.",
    "assumed.nbmany": "Telling them apart would take more recorded brackets than the {r} this simulation resolved.",
    "assumed.ceiling": "Without the edge you typed, no plan that keeps this floor can beat {c}.",
    "assumed.ceilingnf": "Without the edge you typed, no plan can beat {c}.",
    "replay.lead": (
        "This replays a tested bitcoin trend strategy (S_C3) on its own {y0}–{y1} out-of-sample results, with {cut}% "
        "of its average return removed. Most of that return came from bitcoin rising in those years, which the no-edge "
        "column leaves out: just holding bitcoin then had a Sharpe ratio of {bench}, against {cutsr} for this replay "
        "after the cut. Its tested advantage over holding bitcoin was {diff} Sharpe (90% range {lo} to {hi}). Backtest "
        "edges often shrink or vanish in live trading; read this as the hopeful case."
    ),
    "replay.growth": (
        "Resampled in blocks that keep its streaks, this column's average growth over {h} days is {g}, against {g0} if "
        "its days were independent."
    ),
    "replay.noedge": (
        "No-edge column: the same strategy's daily moves, each given a fair coin for its direction, with its costs "
        "kept."
    ),
    # flags
    "hidden.gain": (
        "BUG CHECK FAILED: this plan makes money without any edge (average KRW {x}, limit KRW {b}). Do not use these "
        "numbers."
    ),
    "hidden.loss": (
        "BUG CHECK FAILED: this plan loses more than its costs explain (average KRW {x}, limit KRW {b}). Do not use "
        "these numbers."
    ),
    "hidden.pass": (
        "Bug check passed with a resolution of KRW {b} ({pct} of your stake): it would not notice a hidden edge (a "
        "simulator error that makes money without an edge) that raised the chance of the target by up to {m}. It does "
        "not test whether the model itself is right."
    ),
    "hidden.coarse": (
        "Bug check passed, but its resolution (KRW {b}, {pct} of your stake) is too coarse to say anything about the "
        "chance of the target. It does not test whether the model itself is right."
    ),
    "hidden.unavailable": (
        "The bug check is unavailable for GARCH-t: a bounded shock does not bound the volatility, so no finite range "
        "exists."
    ),
    "hidden.unbounded": (
        "The bug check is unavailable for this plan (no finite range): at the lowest price this model can reach, the "
        "cost rate has no useful bound."
    ),
    "hidden.na": "The bug check does not apply to edge columns.",
    "breach.amber": (
        "Preliminary evidence, about 5% false-alarm rate per check: rerun with more paths. A no-edge result's lower "
        "bound, {lb}, is above the ceiling of {c}."
    ),
    "breach.red": (
        "Do not use these numbers: a no-edge result beats the ceiling of {c} beyond counting noise ({lb}), so the "
        "model or the simulator has a bug."
    ),
    "flag.reference": (
        "Above the estimated reference: this plan's chance of the target is above what this bracket's simulated "
        "outcomes could reach with any stake ({ref}). The reference is an estimate, not a bound."
    ),
    "flag.grey": (
        "OKX is a grey venue (rule {row}): each armed session needs your acknowledgement of its warning, everything "
        "you hold there is capped at {cap} of your equity, and the gate turns it off on {off}."
    ),
    "flag.proxy": (
        "Prices for this leg are a stand-in: Binance BTCUSDT times Upbit KRW-USDT, because OKX's own prices are not "
        "loaded."
    ),
    "flag.proxyfx": "From {d0} to {d1}, before Upbit listed KRW-USDT, Yahoo's KRW=X rate stands in for it.",
    "flag.openclose": "Price checks at the open and the close only: a stop can fill well below its level after a gap.",
    "flag.closeonly": "Price checks at the close only.",
    "flag.bandedge": (
        "{count} simulated sessions ({share} of all) opened at a KRX daily limit and stayed there until the close."
    ),
    "flag.gap": "The worst stop fill was {gap} below its stop level.",
    "flag.locked": (
        "In {p} of {many} the position was still locked at the lower daily limit at the end, valued at the locked "
        "price less the doubled exit charge."
    ),
    "flag.cost": "Costs average KRW {cost}, {pct} of your stake.",
    "rule.review": (
        "From {date} this plan opens no new position unless you re-approve rule {row}; it keeps and may close what it "
        "holds."
    ),
    "rule.end": (
        "On {date} rule {row} ends ({what}), so the plan closes its position at the first price check on or after that "
        "date and opens no new one."
    ),
    "rule.auto": "the gate turns this venue off",
    "rule.until": "the rule expires",
    # refusals
    "refused.head": "Refused: {why}",
    "refused.none": "No numbers are shown for a refused plan.",
    "why.PARTIAL_CHUNK": "the path count must be a whole multiple of {chunk}.",
    "why.UNSUPPORTED_PRODUCT": "this plan uses something the odds engine does not support: {what}.",
    "sub.venue": "only KIS, Upbit and OKX legs",
    "sub.feed": "only BTC on OKX, the one OKX market with a price feed",
    "sub.symbol": "a symbol the signed instrument map lists for this venue",
    "sub.class": "only shares, 1x ETFs and coins",
    "sub.multiple": "only products that move one for one with their underlying",
    "sub.tax": "a tax basis the engine can describe",
    "sub.horizon": "a horizon of 1 to 366 days",
    "sub.start": "a plan that starts today (the Asia/Seoul date)",
    "sub.track": "a moonshot or compounding track",
    "sub.numbers": "a positive stake, a target above the stake and a positive won-dollar rate",
    "sub.model": "the two-point bootstrap or GARCH-t",
    "sub.sizing": "stop-based sizing only with a bracket",
    "sub.fraction": "Kelly only on the tested-strategy replay, bold play only with a bracket",
    "sub.bracket": "a take-profit above 0 and a stop between 0 and 100%",
    "sub.edge": "a typed win rate between 0 and 1, with a bracket and the two-point bootstrap",
    "sub.replay": "the tested-strategy replay only as an Upbit bitcoin holding",
    "sub.file": "a plan file the engine can read",
    "sub.comparison": "a comparison id this engine issued earlier",
    "why.MULTI_LEG_UNSUPPORTED": "this plan has more than one leg; only single-leg plans are supported.",
    "why.STATE_UNUSABLE": (
        "the signed owner state is not usable (no owner key yet, a broken owner log, unapproved tables, or code "
        "changed since you signed it), so nothing new is allowed."
    ),
    "why.LIMITS_UNSET": (
        "your total-loss floor and daily loss limit are not both set, or an OKX leg has no OKX cap. Limits you set "
        "take effect from the next day."
    ),
    "why.CALENDAR_UNSIGNED": (
        "KRX and US plans need the calendar set you signed; it is missing or does not match. Only crypto plans run "
        "until then."
    ),
    "why.CALENDAR_COVERAGE": "this horizon runs past the end of the signed calendar.",
    "why.DATA_INVALID": "the data given to the engine did not pass its checks: {what}.",
    "data.now": "the run's clock reading is not today's",
    "data.series": "the price history",
    "data.sessions": "the session list",
    "data.empty": "the horizon holds no trading session of this market",
    "data.stale": "the last price is more than {days} days before the start",
    "why.SYNTHETIC_REFUSED": "the price history is made-up data, not market prices.",
    "why.NOT_TRADABLE": (
        "{venue} {symbol} cannot be costed or sized from the signed venue table: a minimum order, lot size or fixed "
        "charge is missing, or a date in the horizon is outside a signed tick or tax table."
    ),
    "why.SPECIAL_REGIME": (
        "{symbol} has fewer than 60 KRX sessions of history before the start, so it may still be in a special "
        "reference-price regime."
    ),
    "why.SHORT_HISTORY": "{symbol} has fewer than 250 daily bars of history before the start.",
    "why.CARD_NOT_REPRODUCED": (
        "the tested strategy did not reproduce its validated card, so its column cannot be shown."
    ),
    "why.MODEL_NOT_FOR_LIMITED_VENUE": (
        "GARCH-t is not available for a KRX leg, whose daily band that model does not include."
    ),
    "why.MODEL_CHECK_FAILED": "the chosen model failed its {check} check, so no numbers are shown.",
    "why.COST_DOMINATED": "costs take the whole win of this bracket, or a single exit could cost the whole position.",
    "why.STUCK_AT_START": (
        "can't open: no first stake is affordable after your floor, the reserved exit charge and lot rounding; the "
        "largest stake is below the venue minimum."
    ),
    "why.SCREEN_BLOCKED": "the compliance gate blocks this leg: {what}.",
    "screen.row": "rule {row}",
    "screen.unsigned": "the current code is not signed yet",
    "screen.other": "see the gate's own check",
    "why.ASSUMED_EDGE_UNREACHABLE": "the win rate you typed ({w}) cannot be reached by tilting this bracket's moves.",
    # closing boxes
    "notin.title": "Not in these numbers:",
    "notin.tax": "income tax (estimated, not simulated)",
    "notin.fx": "won-dollar moves beyond the historical range in the data, and the timing of the KRW=X rate",
    "notin.upbit": "Upbit withdrawal holds after a KRW deposit, and the Upbit-to-OKX route closing without notice",
    "notin.freeze": "exchange freezes or failure",
    "notin.delist": "delistings and Upbit warnings (survivorship)",
    "notin.krx": "KRX halts, VI auctions, designations, resets and other special reference-price regimes",
    "notin.intraday": "intraday moves",
    "notin.unfilled": "unfilled orders beyond what is modelled",
    "notin.broker": "broker refusals",
    "notin.hacked": "hacked or locked accounts",
    "notin.rules": "rule changes",
    "notin.close": "Most of these make the real result worse; none makes a no-edge plan better.",
    "limits.injected": (
        "How these numbers were made: unsigned loading code supplies the price history, the session list and the "
        "replay. This report records their hashes but cannot check them against any signed source. The calendar files "
        "used carry the hash you signed; the session dates taken from them, and the KRX Saturday rule read from "
        "data/macro, are not re-checked here. The replay matches its pinned results; the card and results-file hashes "
        "it reports come from unsigned code. NumPy and SciPy are outside the signed code hash."
    ),
    "compare.caption": (
        "With no real edge, a higher chance of the target generally comes from putting more of your stake at risk, "
        "sooner. Check P(at your floor) beside it. Higher here means riskier, not better."
    ),
    "compare.k": (
        "You compared {k} plans (and tried {j} typed win rates) in this session. The highest-looking figure is the "
        "luckiest of {k}."
    ),
    "compare.r": (
        "This plan has been run in {r} comparisons, each on its own market seed; the highest-looking of its figures is "
        "the luckiest of {r}."
    ),
    "compare.fresh": (
        "Before arming, this plan must be run again on a fresh market seed; that rerun belongs to execution and is not "
        "built yet."
    ),
    "plan.head": "Plan {i} of {k} ({hash})",
    "prov.head": "Recorded with this report:",
    "prov.line": "{label}: {value}",
    "prov.code": "code hash",
    "prov.signed": "code signed",
    "prov.owner": "owner log entry",
    "prov.key": "key fingerprint",
    "prov.tables": "tables in force",
    "prov.data": "price history",
    "prov.calendar": "calendar",
    "prov.seed": "market seed",
    "prov.paths": "paths and chunk",
    "prov.versions": "NumPy, SciPy, cryptography",
    "prov.repo": "repository",
    "prov.tree": "tree hash",
    "prov.comparison": "comparison and run",
    "prov.model": "model and members",
    "prov.edge": "edge source",
    "label.bootstrap": "two-point bootstrap",
    "label.garch": "GARCH-t",
    "label.replay": "tested-strategy replay",
    "label.yes": "yes",
    "label.no": "no",
    "edge.none": "none",
    "edge.assumed": "a typed win rate",
    "edge.replay": "the S_C3 replay",
    "footer": (
        "These numbers describe rules you wrote, run in a model. They are not advice, and TRADEGEN does not recommend "
        "any plan. A higher chance of reaching the target does not make a plan better."
    ),
})
BANNED_WORDS = ("best", "optimal", "recommended", "safe", "guaranteed", "sure", "ideal", "risk-free", "low-risk",
                "proven", "should")
BANNED_PHRASES = ("worth trying", "good chance", "likely to reach")
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_CARD_ID = re.compile(r"\bS_C3\b")


def say(key: str, **slots) -> str:
    """CATALOGUE[key].format(**slots): KeyError on an unknown key or a missing slot."""
    return CATALOGUE[key].format(**slots)


def guard(text: str) -> list[str]:
    """The language guard (spec 7.5, Q14): banned whole words (a hyphenated token also part by part), banned
    phrases, any underscore outside the card id S_C3, any brace. Returns the hits; [] is clean."""
    low = text.lower()
    hits = []
    for token in _TOKEN.findall(low):
        parts = (token, *token.split("-")) if "-" in token else (token,)
        hits += [f"word: {p}" for p in parts if p in BANNED_WORDS]
    flat = " ".join(low.split())
    hits += [f"phrase: {p}" for p in BANNED_PHRASES if p in flat]
    if "_" in _CARD_ID.sub("", text):
        hits.append("underscore")
    if "{" in text or "}" in text:
        hits.append("brace")
    return hits


# statistics (section 10.2) ---------------------------------------------------- #
def cp_two_sided(k: int, n: int, level: float = CP_LEVEL) -> tuple[float, float]:
    """Clopper-Pearson: two-sided at `level` for k > 0; for k = 0 the one-sided upper bound (spec 7.5 item 7)."""
    if not 0 <= k <= n or n < 1:
        raise ValueError(f"report: need 0 <= k <= n and n >= 1, got k={k}, n={n}")
    if k == 0:
        return 0.0, float(stats.beta.ppf(level, 1, n))
    lo = float(stats.beta.ppf((1.0 - level) / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf((1.0 + level) / 2.0, k + 1, n - k))
    return lo, hi


def cp_lower(k: int, n: int, level: float) -> float:
    """The one-sided Clopper-Pearson lower bound at `level`; 0 at k = 0."""
    return 0.0 if k == 0 else float(stats.beta.ppf(1.0 - level, k, n - k + 1))


def bernstein(v: float, r: float, n: int, delta: float = DELTA) -> float:
    """The empirical Bernstein bound b_delta (Maurer-Pontil): v the ddof-1 sample variance, r the full range."""
    log_term = math.log(4.0 / delta)
    return math.sqrt(2.0 * v * log_term / n) + 7.0 * r * log_term / (3.0 * (n - 1))


def hidden_range(*, target, phi_buy, phi_sell, kappa_bound, m_max, n_checks, carry=CARRY) -> float:
    """HIDDEN_EDGE's range R of a bootstrap column, fixed before the run (section 10.3): phi_buy and phi_sell are
    scenario-scaled, kappa_bound is costs.kappa_bound (mult applied); inf when k_x = carry x kappa_bound >= 1."""
    k_x = carry * kappa_bound
    if k_x >= 1.0:
        return math.inf
    v_max = (target + carry * phi_sell) / (1.0 - k_x) * math.exp(m_max)
    c_max = k_x * v_max + carry * max(phi_buy, phi_sell)
    return v_max + n_checks * c_max


def replay_range(*, target, a_max, c_max, n_checks) -> float:
    """HIDDEN_EDGE's range R of a replay no-edge column (section 10.3); c_max is the scenario's largest daily c."""
    v_max = target * (1.0 + a_max)
    return v_max + n_checks * c_max * v_max


def hidden_edge(col, *, w0, target, l_min) -> HiddenEdge:
    """HIDDEN_EDGE on a column: red when |mean X| > bernstein(x_var, x_range, n); unavailable for GARCH-t (range
    nan), unbounded when the range fixed in advance is inf, not_applicable on an edge column (spec 7.5); DELTA is
    read at call time."""
    if not target > l_min or not w0 > 0:
        raise ValueError(f"report: hidden_edge needs target > l_min and w0 > 0, got {target}, {l_min}, {w0}")
    r = col.x_range
    if col.key.startswith(("assumed", "tested_replay")):
        return HiddenEdge(status="not_applicable", mean=col.x_mean, bound=math.nan, range_=r, n=col.n)
    if math.isnan(r):
        return HiddenEdge(status="unavailable", mean=col.x_mean, bound=math.nan, range_=r, n=col.n)
    if math.isinf(r):
        return HiddenEdge(status="unbounded", mean=col.x_mean, bound=math.inf, range_=r, n=col.n)
    b = bernstein(col.x_var, r, col.n, DELTA)
    status = "red_gain" if col.x_mean > b else "red_loss" if col.x_mean < -b else "pass"
    return HiddenEdge(status=status, mean=col.x_mean, bound=b, range_=r, n=col.n)


def ceiling_cells(cols, ceiling) -> tuple[str, float]:
    """CEILING_BREACH over the no-edge cells `cols` (first-passage counts; the caller leaves out delisting and edge
    columns): ("red", lb) when a one-sided 1 - RED_ALPHA/m lower bound is above the ceiling, ("amber", lb) when a
    95% one is, else ("", the worst 95% lower bound); m = len(cols); exact float comparisons."""
    cols = tuple(cols)
    if not cols:
        return "", 0.0
    red = max(cp_lower(c.reached, c.n, 1.0 - RED_ALPHA / len(cols)) for c in cols)
    if red > ceiling:
        return "red", red
    amber = max(cp_lower(c.reached, c.n, CP_LEVEL) for c in cols)
    return ("amber" if amber > ceiling else ""), amber


# number formats (section 10.2; Q32: no claim is rounded in its own favour) ----- #
def fmt_krw(x) -> str:
    return f"{round(float(x)):,}"


def _sf2(x: float, up: bool) -> int:
    """x (>= 10) to 2 significant figures, rounded up or down (12,406 -> 12,000 down; 20,656 -> 21,000 up)."""
    whole = math.ceil(x) if up else math.floor(x)
    q = 10 ** max(len(str(whole)) - 2, 0)
    return -(-whole // q) * q if up else whole // q * q


def _sf2_near(x: float) -> int:
    """x (>= 10) to the nearest 2 significant figures (15,873 -> 16,000)."""
    q = 10 ** max(len(str(math.floor(x))) - 2, 0)
    return math.floor(x / q + 0.5) * q


def _point(p: float, below_one: bool = True) -> str:
    """A point estimate p > 0, nearest: "about x.x%" from 1%, else "about 1 in N" (N to 2 significant figures)."""
    if p >= 0.01:
        text = f"{100.0 * p:.1f}"
        return "above 99.9%" if text == "100.0" and below_one else f"about {text}%"
    return f"about 1 in {_sf2_near(1.0 / p):,}"


def fmt_prob(k, n) -> str:
    """The point estimate k/n; k = 0 is "below about 3 in n", never zero."""
    return f"below about 3 in {n:,}" if k == 0 else _point(k / n, k < n)


def fmt_end(p: float, *, upper: bool) -> str:
    """An interval end rounded outward: an upper end up, a lower end down (Q32). p must be > 0."""
    if not p > 0:
        raise ValueError("report: an interval end of 0 prints through fmt_prob ('below about 3 in n')")
    if p >= 0.01:
        return f"{(math.ceil(1000.0 * p) if upper else math.floor(1000.0 * p)) / 10:.1f}%"
    return f"1 in {_sf2(1.0 / p, up=not upper):,}"


def fmt_ceiling(c: float) -> str:
    """The ceiling, an upper bound: "1 in floor(1/c)" below 1%, else "a ceil(1000 c)/10 % chance". The float 1/c can
    floor one off either way; a card's ceiling slot goes through _ceiling_text, whose N is exact."""
    if c < 0.01:
        return f"1 in {math.floor(1.0 / c):,}"
    return f"a {math.ceil(1000.0 * c) / 10:.1f}% chance"


def fmt_blind(x: float) -> str:
    """HIDDEN_EDGE's blind spot b / (T - L_min), an upper bound: "1 in floor(1/x)" below 1%, else points up."""
    if x < 0.01:
        return f"1 in {math.floor(1.0 / x):,}"
    return f"{math.ceil(1000.0 * x) / 10:.1f} percentage points"


def fmt_order(lb: float, c: float) -> tuple[str, str]:
    """Breach slots for lb > c, rounded so the printed order matches the comparison (an alarm is never hidden). The
    ceiling picks the format, so a ceiling below 1% never prints as 0.00%."""
    if c < 0.01:
        return f"1 in {math.floor(10.0 / lb) / 10:,.1f}", f"1 in {math.ceil(10.0 / c) / 10:,.1f}"
    return f"{math.ceil(10_000.0 * lb) / 100:.2f}%", f"{math.floor(10_000.0 * c) / 100:.2f}%"


def _pct(x: float) -> str:
    """A share or a typed rate: the nearest 0.1% from 1%, two significant figures below it (0.050%); a positive
    value never prints as 0.0% and never in scientific notation."""
    if 0 < x < 0.01:
        rounded = float(f"{100.0 * x:.2g}")
        return f"{rounded:.{1 - math.floor(math.log10(rounded))}f}%"
    return f"{100.0 * x:.1f}%"


def _pct_up(x: float) -> str:
    """A cost, a resolution, a share of sessions or a gap as a percentage rounded up to 0.1%."""
    return f"{math.ceil(1000.0 * x) / 10:.1f}%"


# the report object ----------------------------------------------------------- #
_MAPPINGS = ("model_slots", "assumed", "replay", "provenance")
_SPREAD_KINDS = ("other", "krx", "blocks", "none")


def build(**fields) -> OddsReport:
    """An OddsReport with every mapping frozen; ValueError when a refused report carries numbers, or an accepted one
    has duplicate column keys, a headline that is not a column, or a spread that disagrees with its kind."""
    for name in _MAPPINGS:
        if fields.get(name) is not None:
            fields[name] = MappingProxyType(dict(fields[name]))
    for name in ("columns", "flags", "notes"):
        if name in fields:
            fields[name] = tuple(fields[name])
    rep = OddsReport(**fields)
    keys = [c.key for c in rep.columns]
    if rep.refused is not None:
        if rep.columns or rep.flags or rep.hidden is not None or rep.spread is not None:
            raise ValueError("report: a refused report carries no numbers")
        return rep
    if len(set(keys)) != len(keys) or rep.headline not in keys:
        raise ValueError(f"report: headline {rep.headline!r} must be one of the unique column keys {keys}")
    if rep.spread_kind not in _SPREAD_KINDS or (rep.spread is None) != (rep.spread_kind == "none"):
        raise ValueError(f"report: spread {rep.spread!r} does not match its kind {rep.spread_kind!r}")
    return rep


def refusal_report(plan_obj, refusal: plan.Refusal, *, index: int = 1, count: int = 1,
                   provenance: Mapping[str, object] = MappingProxyType({})) -> OddsReport:
    """The report of a refused plan: no columns, no flags, no probability; plan_obj may be malformed or None."""
    try:
        digest = plan.plan_hash(plan_obj) if isinstance(plan_obj, plan.Plan) else ""
    except (TypeError, ValueError):        # a plan too malformed to hash (a non-finite number) still gets its card
        digest = ""
    return build(plan_hash=digest, plan_index=index, plan_count=count, refused=refusal,
                 track=str(getattr(plan_obj, "track", "")), stake=math.nan, target=math.nan, floor=math.nan,
                 l_min=math.nan, horizon_days=0, n=0, sizing="", model_key="", model_slots={}, columns=(),
                 headline="", spread=None, spread_kind="none", notes=(), ceiling=math.nan, structural_cap=None,
                 structural_sessions=None, tax_basis="", cost_words_key="", hidden=None, flags=(), assumed=None,
                 replay=None, comparison=(0, 0, 0), provenance=provenance)


# flags ----------------------------------------------------------------------- #
def flags_for(*, headline: ColumnStats, no_edge: tuple[ColumnStats, ...], engine: str, hidden: HiddenEdge | None,
              ceiling: float, structural: tuple[float, int] | None, target: float, stake: float,
              reference: float | None, rule_flags: tuple, grey: tuple[tuple[str, str, str], ...],
              series: plan.Series, okx: bool) -> tuple[Flag, ...]:
    """Every flag of the card in contract 10.1's order. rule_flags = Screening.flags; grey = (row id, cap text,
    auto_off ISO date) per grey row; structural = (cap, sessions) or None. There is no track argument, so the
    reference and below-resolution checks read the headline's first-passage count `reached` (the plain count on
    compounding cards, never below it on moonshot cards; the bracket reference estimates first passage too), and
    flag.locked's {many} is left to render, which knows the horizon."""
    flags: list[Flag] = []

    def add(code: str, level: str, key: str, **slots: str) -> None:
        flags.append(Flag(code=code, level=level, key=key, slots=MappingProxyType(slots)))

    span = (target - stake) / (1.0 - ceiling)       # = T - L_min, since ceiling = (W0 - L_min) / (T - L_min)
    if hidden is not None:
        b = hidden.bound
        if hidden.status in ("red_gain", "red_loss"):
            key = "hidden.gain" if hidden.status == "red_gain" else "hidden.loss"
            add("HIDDEN_EDGE", "red", key, x=fmt_krw(hidden.mean), b=fmt_krw(b))
        elif hidden.status == "pass" and b >= span:
            add("HIDDEN_EDGE", "info", "hidden.coarse", b=fmt_krw(b), pct=_pct_up(b / stake))
        elif hidden.status == "pass":
            add("HIDDEN_EDGE", "info", "hidden.pass", b=fmt_krw(b), pct=_pct_up(b / stake), m=fmt_blind(b / span))
        elif hidden.status in ("unavailable", "unbounded"):
            add("HIDDEN_EDGE", "info", "hidden." + hidden.status)
        else:
            add("HIDDEN_EDGE", "info", "hidden.na")
    level, lb = ceiling_cells(no_edge, ceiling)
    if level:
        shown_lb, shown_c = fmt_order(lb, ceiling)
        add("CEILING_BREACH", level, "breach." + level, lb=shown_lb, c=shown_c)
    k = headline.reached
    # a zero reference (its grid never reaches T) prints nothing: no probability slot renders as zero
    if reference is not None and reference > 0 and cp_two_sided(k, headline.n)[0] > reference:
        add("ABOVE_ESTIMATED_REFERENCE", "amber", "flag.reference", ref=_point(reference))
    if structural is not None and target > stake * structural[0]:
        add("IMPOSSIBLE", "info", "structural.impossible", cap=f"{math.ceil(structural[0]):,}",
            s=f"{structural[1]:,}")
    elif k == 0 and headline.trades > 0:
        add("BELOW_RESOLUTION", "info", "")
    for row, cap, off in grey:
        add("GREY_LEG", "amber", "flag.grey", row=row, cap=cap, off=off)
    if okx:
        add("PROXY_DATA", "info", "flag.proxy")
    if series.proxy_dates:
        add("PROXY_DATA", "info", "flag.proxyfx", d0=series.proxy_dates[0], d1=series.proxy_dates[1])
    if engine == "bootstrap":
        add("CHECKS_AT_OPEN_CLOSE", "info", "flag.openclose")
    else:
        add("CLOSE_ONLY_CHECKS", "info", "flag.closeonly")
    if headline.band_edge_sessions > 0:
        add("BAND_EDGE_SESSIONS", "info", "flag.bandedge", count=f"{headline.band_edge_sessions:,}",
            share=_pct_up(headline.band_edge_share))
    if headline.worst_gap > 0:
        add("LIMIT_GAP", "info", "flag.gap", gap=_pct_up(headline.worst_gap))
    if headline.locked_at_horizon > 0:
        add("LOCKED_AT_HORIZON", "info", "flag.locked", p=fmt_prob(headline.locked_at_horizon, headline.n))
    if headline.mean_cost >= COST_DOMINATED_SHARE * stake:
        add("COST_DOMINATED", "amber", "flag.cost", cost=fmt_krw(headline.mean_cost),
            pct=_pct_up(headline.mean_cost / stake))
    for when, what, row in rule_flags:
        if what == "review_by":
            add("RULE_CHANGE_IN_HORIZON", "amber", "rule.review", date=when.isoformat(), row=row)
        else:
            add("RULE_CHANGE_IN_HORIZON", "amber", "rule.end", date=when.isoformat(), row=row,
                what=say("rule.auto" if what == "auto_off" else "rule.until"))
    return tuple(flags)


# rendering (section 10.4 render order) --------------------------------------- #
_TAX_KEYS = {"krx_small_holder_exempt": "tax.krx", "overseas_22pct_over_2.5m": "tax.overseas",
             "crypto_22pct_from_2027": "tax.crypto"}
_MEMBER_KEYS = {"bootstrap": "member.bootstrap", "bootstrap_half": "member.half",
                "bootstrap_double": "member.double", "garch_t": "member.garch", "garch_refit": "member.refit"}
_LABEL_KEYS = {"bootstrap": "label.bootstrap", "garch_t": "label.garch", "replay": "label.replay"}
_EDGE_KEYS = {"none": "edge.none", "assumed": "edge.assumed", plan.REPLAY_SOURCE: "edge.replay"}
_RUNG_KEYS = ("ladder.p10", "ladder.p25", "ladder.x2", "ladder.x10")          # one per LADDER entry
_SUB_PREFIX = {"UNSUPPORTED_PRODUCT": "sub.", "DATA_INVALID": "data.", "SCREEN_BLOCKED": "screen."}
_BASE_RATES = ("baserate.kalshi", "baserate.esma", "baserate.sebi", "baserate.krderiv", "baserate.kr2020")
_NOT_IN = ("notin.tax", "notin.fx", "notin.upbit", "notin.freeze", "notin.delist", "notin.krx", "notin.intraday",
           "notin.unfilled", "notin.broker", "notin.hacked", "notin.rules")
_PROV_LINES = (("prov.code", ("code_hash",)), ("prov.signed", ("code_signed",)),
               ("prov.owner", ("owner_seq", "owner_row")), ("prov.key", ("fingerprint",)),
               ("prov.tables", ("rules_sha", "instruments_sha", "venues_sha", "state_hash")),
               ("prov.data", ("series_md5", "components", "proxy_dates")),
               ("prov.calendar", ("calendar_version", "calendar_sha", "calendar_md5s")),
               ("prov.seed", ("seed_hex",)), ("prov.paths", ("n", "chunk")),
               ("prov.versions", ("numpy", "scipy", "cryptography")), ("prov.repo", ("repo_anchor",)),
               ("prov.tree", ("tree_hash",)), ("prov.comparison", ("comparison_id", "run_counter")),
               ("prov.model", ("model", "members")), ("prov.edge", ("edge_source",)))
_PROV_HASHES = frozenset({"code_hash", "owner_row", "fingerprint", "rules_sha", "instruments_sha", "venues_sha",
                          "state_hash", "series_md5", "calendar_sha", "seed_hex", "tree_hash"})
_PROV_COUNTS = frozenset({"owner_seq", "n", "chunk", "run_counter"})


def _words(h: int) -> dict[str, str]:
    """The {one} / {many} slots: a month for a 28- to 31-day horizon, else an h-day period."""
    if 28 <= h <= 31:
        return {"one": say("period.month"), "many": say("period.months")}
    return {"one": say("period.day", h=h), "many": say("period.days", h=h)}


def _plain_count(track: str, col: ColumnStats) -> int:
    """Q32: REACHED outcomes on moonshot cards, first passages on compounding cards."""
    return col.reached_outcome if track == "moonshot" else col.reached


def _ceiling_text(rep: OddsReport) -> str:
    """The ceiling slot {c}: below 1% "1 in N" with N = bold.ceiling_one_in, exact (floor(1 / c) of the float
    ceiling can print N - 1 or N + 1), else fmt_ceiling's percentage."""
    if rep.ceiling < 0.01:
        return f"1 in {bold.ceiling_one_in(rep.stake, rep.l_min, rep.target):,}"
    return fmt_ceiling(rep.ceiling)


def _target_p(rep: OddsReport, col: ColumnStats, k: int) -> str:
    """A target probability slot: the point estimate, or cap.p when it is above the ceiling and no breach fired."""
    if k / col.n > rep.ceiling and not any(f.code == "CEILING_BREACH" for f in rep.flags):
        return say("cap.p", c=_ceiling_text(rep), k=f"{k:,}", n=f"{col.n:,}")
    return fmt_prob(k, col.n)


def _structural(rep: OddsReport, col: ColumnStats, words) -> str | None:
    """Q44: the IMPOSSIBLE or no-trade sentence that replaces every probability of the target, else None."""
    for f in rep.flags:
        if f.code == "IMPOSSIBLE":
            return say(f.key, **f.slots)
    return say("structural.notrade", **words) if col.trades == 0 else None


def _spread_text(rep: OddsReport, n: int) -> str:
    """Q31: the spread wording of the members actually run, outward ends, then each dropped member's note."""
    if rep.spread is None:
        text = say("spread.none")
    else:
        lo, hi = rep.spread
        low = fmt_prob(0, n) if lo <= 0 else fmt_end(lo, upper=False)
        text = say("spread." + rep.spread_kind, a=fmt_end(hi, upper=True), b=low)
    for member, check in rep.notes:
        text += "; " + say("spread.dropped", member=say(_MEMBER_KEYS[member]), check=say("check." + check))
    return text


def _bugs(rep: OddsReport, width: float) -> str:
    """Q32: bugs.finer only when HIDDEN_EDGE passed and its blind spot is below the headline interval's width."""
    h = rep.hidden
    if h is None or h.status != "pass" or not h.bound / (rep.target - rep.l_min) < width:
        return say("bugs.coarser")
    return say("bugs.finer")


def _typical(col: ColumnStats, words) -> list[str]:
    out = [say("typical.median", median=fmt_krw(col.median), **words)]
    if col.at_floor > 0:
        out.append(say("typical.floor", p=fmt_prob(col.at_floor, col.n), lo=fmt_krw(col.kept_lo),
                       hi=fmt_krw(col.kept_hi), **words))
    else:
        out.append(say("typical.nofloor", **words))
    return out


def _average(rep: OddsReport, col: ColumnStats, words, *, edge: bool, delist: bool = False) -> str:
    """Spec 7.5 item 2: agrees within 2 x g_se of the stake minus the average cost; edge columns state gain or loss."""
    if edge:
        if col.mean > rep.stake:
            return say("average.gain", gain=fmt_krw(col.mean - rep.stake), **words)
        return say("average.loss", loss=fmt_krw(rep.stake - col.mean), **words)
    costwords = say(rep.cost_words_key)
    if delist:
        costwords = say("cost.delist", base=costwords)
    expected = rep.stake - col.mean_cost
    if abs(col.mean - expected) <= 2.0 * col.g_se:
        return say("average.agrees", expected=fmt_krw(expected), costwords=costwords, cost=fmt_krw(col.mean_cost),
                   mean=fmt_krw(col.mean), se=fmt_krw(col.mean_se), **words)
    return say("average.differs", mean=fmt_krw(col.mean), se=fmt_krw(col.mean_se), costwords=costwords,
               expected=fmt_krw(expected))


def _headline_lines(rep: OddsReport, col: ColumnStats, words, structural: str | None) -> list[str]:
    """The headline pair; under a structural sentence (Q44) only the floor line (the sentence prints in the plain
    sentence's place, after the ladder)."""
    floor = say("headline.floor", p=fmt_prob(col.at_floor, col.n))
    if structural is not None:
        return [floor]
    if rep.track == "moonshot":
        head = say("headline.moonshot", target=fmt_krw(rep.target), p=_target_p(rep, col, col.reached_outcome))
    else:
        head = say("headline.compounding", target=fmt_krw(rep.target), k=f"{col.reached:,}", n=f"{col.n:,}",
                   pk=_target_p(rep, col, col.reached), k2=f"{col.ended_at_or_above:,}",
                   pk2=_target_p(rep, col, col.ended_at_or_above), **words)
    return [head, floor]


def _ladder_lines(rep: OddsReport, col: ColumnStats) -> list[str]:
    """The ladder: every rung above stake x the structural cap is IMPOSSIBLE; after no trade no rung prints."""
    tail = [say("ladder.spread", median=fmt_krw(col.median), p5=fmt_krw(col.p5))]
    if col.trades == 0:
        return tail
    cap = rep.structural_cap
    rungs = [(key, m * rep.stake) for key, m in zip(_RUNG_KEYS, LADDER)] + [("ladder.target", rep.target)]
    out = [say("ladder.head")]
    for (key, value), k in zip(rungs, col.rungs):
        label = say(key)
        if cap is not None and value > rep.stake * cap:
            out.append(say("ladder.impossible", label=label, value=fmt_krw(value)))
        else:
            p = _target_p(rep, col, k) if key == "ladder.target" else fmt_prob(k, col.n)
            out.append(say("ladder.rung", label=label, value=fmt_krw(value), p=p))
    return out + tail


def _plain_line(rep: OddsReport, col: ColumnStats, words) -> str:
    k = _plain_count(rep.track, col)
    lo, hi = cp_two_sided(k, col.n)
    common = {"n": f"{col.n:,}", "target": fmt_krw(rep.target), "spread": _spread_text(rep, col.n),
              "bugs": _bugs(rep, hi - lo), **words}
    if k == 0:
        return say("plain.none", **common)
    return say("plain.hit", k=f"{k:,}", about=_target_p(rep, col, k), hi=fmt_end(hi, upper=True),
               lo=fmt_end(lo, upper=False), **common)


def _ceiling_line(rep: OddsReport, floor_key: str, nofloor_key: str) -> str:
    return say(floor_key if rep.sizing == "floor_safe" else nofloor_key, c=_ceiling_text(rep))


def _replay_lines(rep: OddsReport) -> list[str]:
    """The tested column's lead and growth lines (Q38), from the replay card's own figures."""
    r = rep.replay
    return [say("replay.lead", y0=f"{int(r['y0'])}", y1=f"{int(r['y1'])}", cut=f"{round(100.0 * r['cut'])}",
                bench=f"{r['bench_sr']:.2f}", cutsr=f"{r['haircut_sr']:.2f}", diff=f"{r['diff']:+.2f}",
                lo=f"{r['ci_lo']:+.2f}", hi=f"{r['ci_hi']:+.2f}"),
            say("replay.growth", h=f"{int(r['h'])}", g=f"{100.0 * r['growth']:.1f}%",
                g0=f"{100.0 * r['growth_iid']:.1f}%")]


def _column_lines(rep: OddsReport, words) -> list[str]:
    """The other columns in report order: stress 2x, delisting, assumed, tested replay (Q29-Q31, Q38). The assumed
    column prints spec 7.5's three sentences together (lead, brackets, ceiling), then its typical and average."""
    stress = rep.headline.rsplit("/", 1)[0] + "/stress2x"
    out: list[str] = []
    for col in rep.columns:
        if col.key == stress:
            out += [say("column.stress"), *_typical(col, words), _average(rep, col, words, edge=False)]
        elif col.key in ("delist_30", "delist_100"):
            out += [say("column.delist", symbol=rep.model_slots["symbol"], h=col.key.split("_")[1]),
                    *_typical(col, words), _average(rep, col, words, edge=False, delist=True)]
        elif col.key == "assumed":
            a = rep.assumed
            if a["resolved"] <= 0:
                raise ValueError("report: assumed rates need a positive resolved bracket count")
            # At zero unresolved, all observed brackets are resolved, so both zero
            # slots use the same sample count instead of claiming a zero chance.
            p0 = fmt_prob(0, int(a["resolved"])) if a["p0"] == 0 else _pct(a["p0"])
            u = fmt_prob(0, int(a["resolved"])) if a["u"] == 0 else _pct(a["u"])
            out.append(say("assumed.lead", w=_pct(a["w"]), p0=p0, u=u))
            out.append(say("assumed.nb", nb=f"{math.ceil(a['nb']):,}") if a["nb"] <= a["resolved"]
                       else say("assumed.nbmany", r=f"{int(a['resolved']):,}"))
            out += [_ceiling_line(rep, "assumed.ceiling", "assumed.ceilingnf"), *_typical(col, words),
                    _average(rep, col, words, edge=True), say("hidden.na")]
        elif col.key == "tested_replay/base":
            out += [*_replay_lines(rep), *_typical(col, words), _average(rep, col, words, edge=True),
                    _ceiling_line(rep, "ceiling.edge", "ceiling.edgenf"), say("hidden.na")]
    return out


def _card(rep: OddsReport) -> list[str]:
    """Everything between the plan head and the footer of an accepted report, in section 10.4's order."""
    col = next(c for c in rep.columns if c.key == rep.headline)
    words = _words(rep.horizon_days)
    structural = _structural(rep, col, words)
    out = [say(f.key, **{**words, **f.slots}) for f in rep.flags if f.level == "red"]
    out.append(say(rep.model_key, **rep.model_slots))
    if rep.replay is not None:
        out.append(say("replay.noedge"))
    out.append(say("sizing.floor" if rep.sizing == "floor_safe" else "sizing.stop", floor=fmt_krw(rep.floor)))
    if "cap" in rep.model_slots:
        out.append(say("okx.cap", **rep.model_slots))
    if rep.tax_basis == "overseas_22pct_over_2.5m":
        out.append(say("fx.us"))
    if rep.replay is not None and math.isfinite(rep.replay.get("fstar", math.nan)):
        out.append(say("kelly.label"))
    out += _typical(col, words)
    out.append(_average(rep, col, words, edge=False))
    out += _headline_lines(rep, col, words, structural)
    out += _ladder_lines(rep, col)
    out.append(_plain_line(rep, col, words) if structural is None else structural)
    out.append(say(_TAX_KEYS[rep.tax_basis]))
    out.append(_ceiling_line(rep, "ceiling.noedge", "ceiling.nofloor"))
    out.append(say("research.estimate"))
    out += [say(key) for key in _BASE_RATES]
    out += _column_lines(rep, words)
    for level in ("amber", "info"):
        out += [say(f.key, **{**words, **f.slots}) for f in rep.flags
                if f.level == level and f.key and f.code != "IMPOSSIBLE"]
    out += [say("notin.title"), *("- " + say(key) for key in _NOT_IN), say("notin.close")]
    out.append(say("limits.injected"))
    k, j, r = rep.comparison
    out += [say("compare.k", k=f"{k:,}", j=f"{j:,}"), say("compare.r", r=f"{r:,}")]
    if rep.track == "moonshot":
        out.append(say("compare.caption"))
    out.append(say("compare.fresh"))
    return out


def _why(ref: plan.Refusal) -> str:
    """The refusal sentence: the code's why.* text with its sub-reason and its number, date, symbol or row slots."""
    slots = dict(ref.slots)
    if ref.code in _SUB_PREFIX:
        slots["what"] = say(_SUB_PREFIX[ref.code] + ref.sub, **slots)
    elif ref.code == "MODEL_CHECK_FAILED":
        slots["check"] = say("check." + (ref.sub or slots.get("check", "")))
    return say("why." + ref.code, **slots)


def _prov_value(key: str, value) -> str:
    if key in _PROV_HASHES:
        return str(value).removeprefix("SHA256:")[:16]
    if key in _PROV_COUNTS:
        return f"{int(value):,}"
    if key == "code_signed":
        return say("label.yes" if value is True else "label.no")
    if key in ("components", "calendar_md5s"):
        return ", ".join(str(md5)[:16] for _, md5 in value)       # never a label or a file id (they hold "_")
    if key == "proxy_dates":
        return " / ".join(value)
    if key == "model":
        return say(_LABEL_KEYS[value])
    if key == "members":
        return ", ".join(say(_MEMBER_KEYS[m]) for m in value)
    if key == "edge_source":
        return say(_EDGE_KEYS[value])
    return str(value)                  # versions, repo_anchor, comparison_id, calendar_version


def _prov_lines(prov: Mapping[str, object]) -> list[str]:
    """Q14: hashes (16 hex), versions, dates, counts, the repo anchor, the comparison id and catalogue labels only."""
    out = []
    for label, keys in _PROV_LINES:
        values = [_prov_value(k, prov[k]) for k in keys if prov.get(k) not in (None, "", ())]
        if values:
            out.append(say("prov.line", label=say(label), value=" / ".join(values)))
    return [say("prov.head"), *out] if out else []


def render(rep: OddsReport) -> str:
    """The card text (section 10.4's order); ValueError when the text fails the language guard (the CLI exits 4)."""
    lines = [say("plan.head", i=f"{rep.plan_index:,}", k=f"{rep.plan_count:,}",
                 hash=rep.plan_hash[:16] or say("edge.none"))]
    if rep.refused is not None:
        lines += [say("refused.head", why=_why(rep.refused)), say("refused.none")]
    else:
        lines += _card(rep)
    lines.append(say("footer"))
    lines += _prov_lines(rep.provenance)
    text = "\n".join(lines) + "\n"
    hits = guard(text)
    if hits:
        raise ValueError(f"rendered text failed the language guard: {hits[:5]}")
    return text
