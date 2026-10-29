"""Costs, venue terms, bands, affordability and stakes of the odds engine (spec 4 "Costs", 7.1, 7.2 "Bands"; plan
decisions Q11, Q27, Q28, Q41; RULINGS O1, O10, O11; R2-1, R2-2, R2-5).

The cost table, the tick floor, the KRX ETF tick table, the KRX stock sell tax and their date validity are copies of
core/quant/instruments.py and core/quant/validate.py (O1: the signed core imports neither), each pinned by an
equality test in tests/odds_costs.py. A per-side rate is max(table rate, commission + half a tick per price + that
year's sell tax on a KRX stock sell): the floor only raises a cost, and no separate sell tax is ever added on top.
Lots, minimums, fixed charges and the KRX stock tick ladder come from the signed venues file through `rules.Venue`;
a missing one raises NotTradable (NOT_TRADABLE), and an explicit 0 is allowed. Pure: no clock, no I/O.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np

from core.compliance import rules
from core.odds import plan as odds_plan

COMMISSION_BP = 1.4                       # == instruments.COMMISSION_BP
TABLE_BP = {"KRX_ETF_line": 3.0, "KRX_stock_book": 35.0, "US_shares_KIS": 50.0, "crypto_venue": 10.0}
                                          # == validate.COST_BP_PER_SIDE of each book's cost class
ETF_TICKS = ((date(2023, 12, 11), ((2000.0, 1.0), (math.inf, 5.0))),)   # == instruments.TICK_TABLES["KRX_ETF"]:
                                          # effective-from date -> rows of (price strictly below, tick)
SELL_TAX_BP = {2026: 20.0}                # == instruments.SELL_TAX_BP: the KRX stock sell tax in bp per year, inside
                                          # the tick floor of a sell (R2-1); a sell in a missing year is NotTradable
COST_STRESS = 2.0                         # == validate.GATE["cost_stress"]
LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0    # == the module-level assign in core/engine/orders.py (read by AST in tests)
DELIST_STRESS = (0.30, 1.00)              # == core.quant.tf_books.DELIST_STRESS
SCENARIOS = {"base": 1.0, "stress2x": COST_STRESS}
_SIDES = ("buy", "sell")
_KRX_BOOKS = ("KRX_ETF_line", "KRX_stock_book")
_USD_QUOTES = ("USD", "USDT", "USDC")     # priced in KRW through plan.fx_krw_per_usd


class NotTradable(ValueError):
    """The leg cannot be costed from what is signed (NOT_TRADABLE); local, never the instruments class."""


# --------------------------------------------------------------------------- #
# Venue terms (Q11, Q17, R2-5)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, kw_only=True)
class Terms:
    venue: str
    symbol: str
    book: str
    quote: str
    lot: float                    # units step
    min_quote: float              # signed minimum order in quote units
    min_krw: float                # min_quote x quote_krw
    phi_buy: float                # fixed charge per buy, KRW, base scenario
    phi_sell: float               # fixed charge per sell, KRW, base scenario
    ladder: tuple[tuple[float, float], ...] | None     # signed (price_from, tick) rows in the quote currency
    ladder_from: date | None
    quote_krw: float              # 1.0 for KRW; plan.fx_krw_per_usd for USD, USDT, USDC


def terms(venue: rules.Venue, inst: rules.Instrument, fx_krw_per_usd: float, *, replay: bool = False) -> Terms:
    """The signed terms of one leg. NotTradable when the book has no table rate, the quote has no KRW rate, or the
    lot, the minimum for the leg's quote, the fixed charges (unless `replay`) or the KRX stock ladder is missing. A
    replay leg (R2-5) never reads fee_extras: its card's 10 bp already includes fees, so phi_buy = phi_sell = 0.0."""
    book, where = inst.cost_book, f"{venue.id} {inst.symbol}"
    if book not in TABLE_BP:
        raise NotTradable(f"{where}: cost book {book!r} has no table rate")
    quote = venue.quote_for(inst)
    fx = float(fx_krw_per_usd)
    if quote == "KRW":
        quote_krw = 1.0
    elif quote in _USD_QUOTES and math.isfinite(fx) and fx > 0:
        quote_krw = fx
    else:
        raise NotTradable(f"{where}: quote {quote!r} has no KRW rate")
    lot = venue.lot_for(inst.symbol)
    if lot is None:
        raise NotTradable(f"{where}: no signed lot in the venues file")
    min_quote = venue.min_order_for(quote)
    if min_quote is None:
        raise NotTradable(f"{where}: no signed minimum order in {quote}")
    if replay:
        phi_buy = phi_sell = 0.0
    elif venue.fee_extras is None:
        raise NotTradable(f"{where}: no signed fixed charges (fee_extras; an explicit 0 is allowed)")
    else:
        phi_buy, phi_sell = venue.fee_extras
    entry = venue.ladder_for(book)
    if entry is None and book == "KRX_stock_book":
        raise NotTradable(f"{where}: no signed KRX stock tick ladder")
    return Terms(venue=venue.id, symbol=inst.symbol, book=book, quote=quote, lot=float(lot),
                 min_quote=float(min_quote), min_krw=float(min_quote) * quote_krw, phi_buy=float(phi_buy),
                 phi_sell=float(phi_sell),
                 ladder=None if entry is None else tuple((float(a), float(t)) for a, t in entry[1]),
                 ladder_from=None if entry is None else date.fromisoformat(entry[0]), quote_krw=quote_krw)


# --------------------------------------------------------------------------- #
# Per-side rate (Q11, R2-1)
# --------------------------------------------------------------------------- #
def _etf_rows(on: date) -> tuple[tuple[float, float], ...]:
    """The KRX ETF rows (price strictly below, tick) in force on `on`, as instruments.tick_size reads them."""
    rows = [r for r in ETF_TICKS if r[0] <= on]
    if not rows:
        raise NotTradable(f"KRX_ETF: no tick row effective on {on}; earlier ticks are KRX notices (owner input)")
    return max(rows, key=lambda r: r[0])[1]


def etf_tick(price: float, on: date) -> float:
    """instruments.tick_size("KRX_ETF", price, on), copied."""
    for below, tick in _etf_rows(on):
        if price < below:
            return float(tick)
    raise NotTradable(f"KRX_ETF: no tick for price {price}")


def ladder_tick(ladder, price: float) -> float:
    """The tick of the last (price_from, tick) row with price_from <= price."""
    tick = None
    for start, step in ladder:
        if start <= price:
            tick = step
    if tick is None:
        raise NotTradable(f"ladder: no tick for price {price}")
    return float(tick)


def tick_floor_bp(price: float, tick: float, *, commission_bp: float = COMMISSION_BP, tax_bp: float = 0.0) -> float:
    """commission + half a tick per price + tax, in bp; copied from instruments.tick_floor_bp."""
    if not (math.isfinite(price) and price > 0) or not (math.isfinite(tick) and tick >= 0):
        raise ValueError(f"price {price} and tick {tick} must be finite and positive")
    return commission_bp + 0.5 * tick / price * 1e4 + tax_bp


def _check_on(terms: Terms, on: date, side: str) -> None:
    """The copied date validity of one fill: NotTradable for a KRX ETF fill before the copied table's first row, a
    KRX stock sell in a year missing from SELL_TAX_BP (instruments._sell_tax_bp), and a fill before the signed
    ladder's effective_from (instruments.tick_size has no row then)."""
    if side not in _SIDES:
        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
    if terms.book == "KRX_ETF_line":
        _etf_rows(on)
    if terms.book == "KRX_stock_book" and terms.ladder is None:
        raise NotTradable("KRX_stock_book: no signed tick ladder")
    if terms.book == "KRX_stock_book" and side == "sell" and on.year not in SELL_TAX_BP:
        raise NotTradable(f"stock sell tax for {on.year} is an owner input (R-20 sell_tax_pct)")
    if terms.ladder is not None and on < terms.ladder_from:
        raise NotTradable(f"{terms.book}: no tick row effective on {on}; the signed ladder starts {terms.ladder_from}")


def side_bp(terms: Terms, price: float, on: date, *, side: str) -> float:
    """The per-side rate in bp of one fill at `price` KRW on the session date `on`: max(table, tick floor), the
    floor holding that year's sell tax on a KRX stock sell; the table rate alone for a book with no signed ladder."""
    _check_on(terms, on, side)
    if not (math.isfinite(price) and price > 0):
        raise ValueError(f"price {price} must be finite and > 0")
    table = TABLE_BP[terms.book]
    if terms.book == "KRX_ETF_line":
        return max(table, tick_floor_bp(price, etf_tick(price, on)))
    if terms.ladder is None:
        return table
    tax = SELL_TAX_BP[on.year] if (side == "sell" and terms.book == "KRX_stock_book") else 0.0
    q = price / terms.quote_krw
    return max(table, tick_floor_bp(q, ladder_tick(terms.ladder, q), tax_bp=tax))


def _rows(terms: Terms, on: date) -> tuple[tuple[float, float], ...]:
    """(price_from, tick) rows of the book on `on`: the copied ETF table with its bounds as row starts, or the
    signed ladder."""
    if terms.book == "KRX_ETF_line":
        rows = _etf_rows(on)
        return tuple(zip((0.0,) + tuple(below for below, _ in rows[:-1]), (tick for _, tick in rows)))
    return terms.ladder


def _ticks(terms: Terms, q: np.ndarray, on: date) -> np.ndarray:
    """The tick at each quote-currency price q (the last row whose price_from <= q)."""
    rows = _rows(terms, on)
    starts = np.array([r[0] for r in rows])
    steps = np.array([r[1] for r in rows])
    return steps[np.searchsorted(starts, q, side="right") - 1]


def _bp(terms: Terms, q: np.ndarray, on: date, side: str) -> np.ndarray:
    """side_bp's arithmetic, vectorised over quote-currency prices q."""
    _check_on(terms, on, side)
    table = TABLE_BP[terms.book]
    if terms.book != "KRX_ETF_line" and terms.ladder is None:
        return np.full(q.shape, table)
    tax = SELL_TAX_BP[on.year] if (side == "sell" and terms.book == "KRX_stock_book") else 0.0
    return np.maximum(table, COMMISSION_BP + 0.5 * _ticks(terms, q, on) / q * 1e4 + tax)


def kappa(terms: Terms, prices, on: date, mult: float, *, side: str) -> np.ndarray:
    """side_bp x 1e-4 x mult per price (mult applied here, once). Entries use side "buy"; exits, the liquidation
    value and every exit bound use side "sell". ValueError for a price that is not finite and > 0."""
    p = np.asarray(prices, dtype=float)
    if not np.all(np.isfinite(p) & (p > 0.0)):
        raise ValueError("kappa: every price must be finite and > 0")
    return _bp(terms, p / terms.quote_krw, on, side) * 1e-4 * mult


def check_validity(terms: Terms, dates) -> None:
    """NotTradable when a fill on any of `dates` would raise in the original: every check can hold a sell, so each
    date is checked as a sell (R2-1). simulate runs it over every horizon session date before any path is drawn."""
    for on in dates:
        _check_on(terms, on, "sell")


def kappa_bound(terms: Terms, p_min: float, dates, mult: float) -> float:
    """The largest rate (x 1e-4 x mult) on either side at any price >= p_min on any of `dates`. Within one row the
    tick is fixed and the rate falls as the price rises, so the maximum sits at p_min or at a row start above it.
    The table rate for a book with no ladder; inf when p_min is not > 0 (no bound under the tick floor)."""
    dates = tuple(dates)
    if not dates:
        raise ValueError("kappa_bound needs at least one date")
    if terms.book != "KRX_ETF_line" and terms.ladder is None:
        return TABLE_BP[terms.book] * 1e-4 * mult
    if not p_min > 0.0:
        return math.inf
    lo = p_min / terms.quote_krw
    best = 0.0
    for on in sorted(set(dates)):
        q = np.array((lo,) + tuple(start for start, _ in _rows(terms, on) if start > lo))
        for side in _SIDES:
            best = max(best, float(np.max(_bp(terms, q, on, side))))
    return best * 1e-4 * mult


# --------------------------------------------------------------------------- #
# Bands (Q10, Q41, R2-2)
# --------------------------------------------------------------------------- #
def band(ref, limit: float, terms: Terms, on: date) -> tuple[np.ndarray, np.ndarray]:
    """KRX legs: the session band [D, U] around `ref`, each edge rounded to the tick valid at its own price (D up,
    U down), then D <= ref <= U; at ETF ref 2,005 and limit 0.30 that is [1,404, 2,605]. Other legs: [0, inf).
    ValueError for a reference that is not finite and > 0 (as kappa)."""
    ref = np.asarray(ref, dtype=float)
    if not np.all(np.isfinite(ref) & (ref > 0.0)):
        raise ValueError("band: every reference must be finite and > 0")
    if terms.book not in _KRX_BOOKS:
        return np.zeros(ref.shape), np.full(ref.shape, math.inf)
    if not 0.0 < limit < 1.0:
        raise ValueError(f"price limit {limit} must be in (0, 1)")
    _check_on(terms, on, "buy")
    d, u = ref * (1.0 - limit), ref * (1.0 + limit)
    td, tu = _ticks(terms, d, on), _ticks(terms, u, on)
    lo = np.ceil(d / td - 1e-9) * td
    hi = np.floor(u / tu + 1e-9) * tu
    return np.minimum(lo, ref), np.maximum(hi, ref)


# --------------------------------------------------------------------------- #
# Affordability and stakes (Q11, Q27, Q28)
# --------------------------------------------------------------------------- #
def r_exit(terms: Terms) -> float:
    """The exit reserve kept in every scenario: COST_STRESS x LIMIT_DOWN_CARRY_COST_MULTIPLIER x phi_sell."""
    return COST_STRESS * LIMIT_DOWN_CARRY_COST_MULTIPLIER * terms.phi_sell


def afford(cash, floor, p, *, terms: Terms, on: date, mult: float, sizing: str, stop) -> np.ndarray:
    """The largest stake (KRW notional) the sizing rule allows at price p, clipped at 0. Always: cash after the
    entry covers the worst exit (r_exit). floor_safe: also cash after the entry >= floor + r_exit. stop_based: also
    an exit at the stop price leaves cash >= floor (before gaps)."""
    cash, p = np.asarray(cash, dtype=float), np.asarray(p, dtype=float)
    kb = kappa(terms, p, on, mult, side="buy")
    phib, phis, reserve = mult * terms.phi_buy, mult * terms.phi_sell, r_exit(terms)
    a = (cash - phib - reserve) / (1.0 + kb)
    if sizing == "floor_safe":
        a = np.minimum(a, (cash - floor - phib - reserve) / (1.0 + kb))
    elif sizing == "stop_based":
        ks = kappa(terms, p * (1.0 - stop), on, mult, side="sell")
        a = np.minimum(a, (cash - floor - phib - phis) / (stop + kb + ks * (1.0 - stop)))
    else:
        raise ValueError(f"sizing must be floor_safe or stop_based, got {sizing!r}")
    return np.maximum(a, 0.0)


def floor_units(stake, p, lot) -> np.ndarray:
    """The stake rounded down to whole lots, in units (1e-9 lot tolerance)."""
    return np.floor(np.asarray(stake, dtype=float) / (p * lot) + 1e-9) * lot


def ceil_units(stake, p, lot) -> np.ndarray:
    """The stake rounded up to whole lots, in units (1e-9 lot tolerance)."""
    return np.ceil(np.asarray(stake, dtype=float) / (p * lot) - 1e-9) * lot


def min_units(p, terms: Terms) -> np.ndarray:
    """The smallest bet in units: one lot or the signed minimum, whichever is larger, rounded up to lots."""
    p = np.asarray(p, dtype=float)
    return ceil_units(np.maximum(terms.min_krw, terms.lot * p), p, terms.lot)


def rule_units(fraction, cash, p, *, terms: Terms, on: date, mult: float, target: float, w0: float, take_profit,
               stop, sizing: str, floor: float, fstar: float | None, cap_krw: float | None
               ) -> tuple[np.ndarray, np.ndarray]:
    """(units to buy, at_floor mask) per path. fixed(f): f x cash; kelly(c): c x fstar x cash; bold: the reaching
    stake, rounded up to lots when affordable and cut to the affordable stake otherwise, and no bet where its net
    win coefficient is <= 0 or cash >= target. Every stake is cut by afford (and by cap_krw on OKX) and rounded down
    to lots; a stake below the minimum is no bet; a path whose affordable stake is below the minimum is at_floor and
    buys nothing. w0 (the plan's starting wealth) is part of the engine's call; no rule reads it."""
    cash, p = np.asarray(cash, dtype=float), np.asarray(p, dtype=float)
    a = afford(cash, floor, p, terms=terms, on=on, mult=mult, sizing=sizing, stop=stop)
    if cap_krw is not None:
        a = np.minimum(a, cap_krw)
    m = min_units(p, terms) * p
    at_floor = a < m
    if fraction.kind == "fixed":
        s = np.minimum(fraction.value * cash, a)
    elif fraction.kind == "kelly":
        if fstar is None:
            raise ValueError("a kelly stake needs fstar")
        s = np.minimum(fraction.value * fstar * cash, a)
    elif fraction.kind == "bold":
        kw = np.maximum(kappa(terms, p, on, mult, side="buy"),
                        kappa(terms, p * (1.0 + take_profit), on, mult, side="sell"))
        c_w = take_profit - kw * (2.0 + take_profit)
        bet = (c_w > 0.0) & (cash < target)
        reach = (target - cash + mult * terms.phi_buy + mult * terms.phi_sell) / np.where(bet, c_w, 1.0)
        s = np.minimum(ceil_units(np.maximum(reach, m), p, terms.lot) * p, floor_units(a, p, terms.lot) * p)
        s = np.where(bet, s, 0.0)
    else:
        raise ValueError(f"unknown fraction {fraction.kind!r}")
    units = floor_units(s, p, terms.lot)
    units = np.where(at_floor | (units * p < m), 0.0, units)
    return units, at_floor


def net_win_coefficient(terms: Terms, p0: float, on: date, take_profit: float, mult: float) -> float:
    """take_profit - kw (2 + take_profit), kw the larger of the buy rate at p0 and the sell rate at p0 (1 +
    take_profit): what a winning bracket nets per KRW staked."""
    p = np.array([float(p0)])
    kw = max(float(kappa(terms, p, on, mult, side="buy")[0]),
             float(kappa(terms, p * (1.0 + take_profit), on, mult, side="sell")[0]))
    return take_profit - kw * (2.0 + take_profit)


def first_stake(plan, terms: Terms, ctx, p0: float, on: date, *, fstar: float | None = None) -> float:
    """The base-scenario rule stake at W0 = plan.stake_krw and p0, as units x p0; 0.0 when no bet, at_floor, or an
    OKX cap that is not a number in (0, 1] (read with .get: never a KeyError). A replay leg (the zero-charge terms of
    terms(venue, inst, fx, replay=True)) is sized at mult 0.0 (Q38, R2-5)."""
    w0 = float(plan.stake_krw)
    cap_krw = None
    if plan.leg.venue == "okx":
        cap = ctx.owner.caps.get(odds_plan.OKX_CAP_KEY)
        if type(cap) not in (int, float) or not 0.0 < cap <= 1.0:     # gate._cap's set; nan, inf, 10**400 fail
            return 0.0
        cap_krw = cap * w0
    bracket = plan.leg.bracket
    units, at_floor = rule_units(
        plan.fraction, np.array([w0]), np.array([float(p0)]), terms=terms, on=on,
        mult=0.0 if plan.leg.edge_source == odds_plan.REPLAY_SOURCE else 1.0, target=float(plan.target_krw), w0=w0,
        take_profit=None if bracket is None else bracket.take_profit, stop=None if bracket is None else bracket.stop,
        sizing=plan.leg.sizing, floor=float(ctx.owner.limits["total_loss_floor_krw"]), fstar=fstar, cap_krw=cap_krw)
    if at_floor[0] or units[0] <= 0.0:
        return 0.0
    return float(units[0] * float(p0))


def cost_refusal(plan, terms: Terms, p0: float, on: date) -> str | None:
    """"4kappa" when 4 x the sell rate at p0 is >= 1 (the sell side is never below the buy side); "bold" when a bold
    plan's net win coefficient is <= 0 under base or 2x costs; else None. Both are COST_DOMINATED."""
    if 4.0 * float(kappa(terms, np.array([float(p0)]), on, 1.0, side="sell")[0]) >= 1.0:
        return "4kappa"
    if plan.fraction.kind == "bold":
        take_profit = plan.leg.bracket.take_profit
        if any(net_win_coefficient(terms, p0, on, take_profit, m) <= 0.0 for m in SCENARIOS.values()):
            return "bold"
    return None
