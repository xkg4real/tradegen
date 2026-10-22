"""Instrument books, tick floor and card-header checks — R-26 rules 1–5 (P10, P15; DNB 23, 32, 33).

Costs come from one table, `core.quant.validate.COST_BP_PER_SIDE`; this module only applies the
floor `max(table, commission + ½·tick/price + tax_side)` (spec L2794), which can raise a cost and
never lower it, and exposes the 2× line beside every quote. Metadata the spec does not give
(lot sizes, contract multipliers, tick tables other than the KRX ETF table from 2023-12-11) is a
typed `None` = OWNER_INPUT and fails closed. Rule 6 (printed lines) is M7. Pure: no clock, no I/O.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Optional

from core.quant.validate import COST_BP_PER_SIDE, GATE, cost_bp

OWNER_INPUT = None                 # the spec gives no value; listed under "Open owner actions"
COMMISSION_BP = 1.4                # EX2 desk quote; owner confirms against the broker schedule (L2797)
SELL_TAX_BP = {2026: 20.0}         # 0.20 % on stock sells in 2026, ETFs exempt (L2798); other years: R-20 / owner
GRANULARITY_MAX_SHARE = 0.05       # one contract ≤ 5 % of the sleeve notional, exactly 5 % allowed (L2816)
REBALANCE = ("daily", "weekly", "monthly")
NO_TRADE_BANDS = (0.0, 0.10)
NAV_FX_ROLES = ("acting_exposure", "forward_sim")
# effective-from date -> ladder of (price strictly below, tick). Rows before 2023-12-11 are KRX notices (owner).
TICK_TABLES: dict[str, tuple[tuple[date, tuple[tuple[float, float], ...]], ...]] = {
    "KRX_ETF": ((date(2023, 12, 11), ((2000.0, 1.0), (math.inf, 5.0))),),
}


class NotTradable(ValueError):
    """MissingInput-style refusal: the instrument cannot be costed or valued from what is known."""
    status = "missing"   # == core.ficc.pit.REASONS[0]: the MissingInput reason the store-level read would carry


class CostLowered(ValueError):
    """A header or schedule tries to lower a pre-registered cost (DNB 23)."""


@dataclass(frozen=True)
class InstrumentBook:
    book_id: str
    market: Optional[str]                   # section 6.1 enum; None for multi_line
    venue: Optional[str]
    currency: Optional[str]                 # "KRW" or not; a non-KRW book needs nav_fx (L2812)
    cost_class: Optional[str]               # key of COST_BP_PER_SIDE or KRX_LI_ETF
    kind: str                               # etf | stock | futures | spot | multi
    tick_table: Optional[str]               # key of TICK_TABLES; None = owner input, not tradable
    tax_side: Optional[str]                 # "sell" on stock books
    lot_size: Optional[int]                 # OWNER_INPUT
    contract_multiplier: Optional[float]    # OWNER_INPUT
    contract_notional_krw: Optional[float]  # header check only, as of 2026-10-02 (L2816-2819)
    band_allowed: bool = False              # the 0.10 band only on stock and US-share books (L2810)


@dataclass(frozen=True)
class Instrument:
    code: str
    name: str
    book_id: str
    cost_class: str
    leverage: Optional[float]               # OWNER_INPUT (L is not given numerically by the spec)


_B = InstrumentBook
INSTRUMENT_BOOKS: dict[str, InstrumentBook] = {b.book_id: b for b in (
    _B("KRX_ETF_line", "KR", "KRX", "KRW", "krx_etf", "etf", "KRX_ETF", None, OWNER_INPUT, None, None),
    _B("KRX_stock_book", "KR", "KRX", "KRW", "krx_stock", "stock", OWNER_INPUT, "sell", OWNER_INPUT, None, None, True),
    _B("KOSPI200_futures", "KR", "KRX", "KRW", "futures", "futures", OWNER_INPUT, None, None, OWNER_INPUT, 280e6),
    _B("mini_KOSPI200_futures", "KR", "KRX", "KRW", "futures", "futures", OWNER_INPUT, None, None, OWNER_INPUT, 56e6),
    _B("CME_micro_ES", "US", "CME", "USD", "futures", "futures", OWNER_INPUT, None, None, OWNER_INPUT, 52e6),
    _B("US_shares_KIS", "US", "US", "USD", "us", "stock", OWNER_INPUT, None, OWNER_INPUT, None, None, True),
    _B("KRX_listed_SP500_ETF", "US", "KRX", "KRW", "krx_etf", "etf", "KRX_ETF", None, OWNER_INPUT, None, None),
    _B("crypto_venue", "CRYPTO", OWNER_INPUT, OWNER_INPUT, "crypto", "spot", OWNER_INPUT, None, OWNER_INPUT, None, None),
    # fx (10 bp) is the higher of fx and futures: never lowered (proposed reading, brief A-14)
    _B("FX_KRX_USD_futures", "FX", "KRX", "KRW", "fx", "futures", OWNER_INPUT, None, None, OWNER_INPUT, OWNER_INPUT),
    _B("FX_broker_spot", "FX", OWNER_INPUT, "USD", "fx", "spot", OWNER_INPUT, None, OWNER_INPUT, None, None),
    _B("multi_line", None, None, None, None, "multi", None, None, None, None, None),
)}
del _B
INSTRUMENTS: dict[str, Instrument] = {i.code: i for i in (
    Instrument("252670", "KODEX 200 Futures Inverse 2X", "KRX_ETF_line", "KRX_LI_ETF", OWNER_INPUT),
    Instrument("069500", "KODEX 200", "KRX_ETF_line", "krx_etf", OWNER_INPUT),
)}
FUTURES_BOOKS = frozenset(b for b, v in INSTRUMENT_BOOKS.items() if v.kind == "futures")
STOCK_BOOKS = frozenset(b for b, v in INSTRUMENT_BOOKS.items() if v.kind == "stock")
FX_BOOKS = frozenset(b for b, v in INSTRUMENT_BOOKS.items() if v.market == "FX")   # R-17 / P10: FX_KRX_USD_futures, FX_broker_spot
HEADER_REQUIRED = ("instrument_book", "rebalance", "no_trade_band", "notional_nav", "fill_model")


def owner_inputs() -> list[str]:
    """Every typed-None datum of this module, for the Macro page's "Open owner actions"."""
    out = ["instruments.cost_floor.commission_bp 1.4: confirm against the broker schedule",
           "KRX ETF tick table before 2023-12-11 (KRX notices)", "stock sell tax outside 2026 (R-20)",
           "sleeves.<market>.notional_nav (owner-signed, before the M7 header commit)"]
    for b in INSTRUMENT_BOOKS.values():
        fields = {"futures": ("tick_table", "contract_multiplier"), "multi": ()}.get(b.kind, ("tick_table", "lot_size"))
        out += [f"{b.book_id}.{f}" for f in fields if getattr(b, f) is None]
    return out


# --------------------------------------------------------------------------- #
# Rule 1–2: tick floor
# --------------------------------------------------------------------------- #
def tick_size(table: Optional[str], price: float, on: Optional[date] = None) -> float:
    """Effective-dated tick; `on=None` reads the latest shipped row. No row -> NotTradable (L2863)."""
    if table is None or table not in TICK_TABLES:
        raise NotTradable(f"tick table {table!r} is an owner input; not tradable in the simulated book")
    rows = [r for r in TICK_TABLES[table] if on is None or r[0] <= on]
    if not rows:
        raise NotTradable(f"{table}: no tick row effective on {on}; earlier ticks are KRX notices (owner input)")
    for below, tick in max(rows, key=lambda r: r[0])[1]:
        if price < below:
            return float(tick)
    raise NotTradable(f"{table}: no tick for price {price}")


def tick_floor_bp(price: float, tick: float, *, commission_bp: float = COMMISSION_BP, tax_bp: float = 0.0) -> float:
    """commission + ½·tick/price + tax_side, in bp (L2794-2795)."""
    if not (math.isfinite(price) and price > 0) or not (math.isfinite(tick) and tick >= 0):
        raise ValueError(f"price {price} and tick {tick} must be finite and positive")
    return commission_bp + 0.5 * tick / price * 1e4 + tax_bp


def stress(bp: float) -> float:
    """The 2× line printed beside every result (P10; GATE['cost_stress'])."""
    return bp * float(GATE["cost_stress"])


def stress_cost_line(bp: float, sigma20: float, sigma_median: float, *, etf_close_fill: bool = False,
                     abs_ret: float = 0.0) -> float:
    """cost × clip(σ20/σ_median, 1, 5) + 10 bp on ETF close fills when |r| ≥ 3 % (L2831); printed, never gated,
    never below `bp`."""
    if not (sigma_median > 0 and math.isfinite(sigma20)):
        raise ValueError("stress line needs a positive sigma_median and a finite sigma20")
    return bp * min(max(sigma20 / sigma_median, 1.0), 5.0) + (10.0 if etf_close_fill and abs_ret >= 0.03 else 0.0)


@dataclass(frozen=True)
class CostQuote:
    bp: float
    floor_bp: Optional[float]     # None for a class-only quote (no instrument, no tick)
    source: str                   # "table" | "tick_floor"
    table_bp: float
    stress_bp: float              # the 2× line


def _sell_tax_bp(on: Optional[date]) -> float:
    year = on.year if on is not None else max(SELL_TAX_BP)
    if year not in SELL_TAX_BP:
        raise NotTradable(f"stock sell tax for {year} is an owner input (R-20 sell_tax_pct)")
    return SELL_TAX_BP[year]


def _resolve(x: Any) -> tuple[str, InstrumentBook, str]:
    """-> (label, book, cost_class) from a book id, an instrument code, or either dataclass."""
    if isinstance(x, Instrument):
        return x.code, INSTRUMENT_BOOKS[x.book_id], x.cost_class
    if isinstance(x, InstrumentBook):
        return x.book_id, x, x.cost_class
    if isinstance(x, str) and x in INSTRUMENTS:
        return _resolve(INSTRUMENTS[x])
    if isinstance(x, str) and x in INSTRUMENT_BOOKS:
        return _resolve(INSTRUMENT_BOOKS[x])
    raise NotTradable(f"unknown instrument or book {x!r}")


def cost_per_side(instrument_book: Any, price: Optional[float] = None, nav_fx: Any = None, *,
                  on: Optional[date] = None, side: str = "buy") -> CostQuote:
    """max(table rate, tick floor) per side; the floor only raises. `price=None` is a class-only quote."""
    label, book, cost_class = _resolve(instrument_book)
    if cost_class is None:
        raise NotTradable(f"{label}: no cost class of its own (declare one line per market)")
    table_bp = cost_bp(cost_class)
    if price is None:
        return CostQuote(table_bp, None, "table", table_bp, stress(table_bp))
    if book.currency != "KRW" and nav_fx is None:
        raise NotTradable(f"{label}: a non-KRW book is valued through nav_fx (L2812); none given")
    tax_bp = _sell_tax_bp(on) if (side == "sell" and book.tax_side == "sell") else 0.0
    floor_bp = tick_floor_bp(price, tick_size(book.tick_table, price, on), tax_bp=tax_bp)
    bp = max(table_bp, floor_bp)
    return CostQuote(bp, floor_bp, "tick_floor" if floor_bp > table_bp else "table", table_bp, stress(bp))


# --------------------------------------------------------------------------- #
# Rules 1, 3–5: header checks (pure; the store comes in as an accessor)
# --------------------------------------------------------------------------- #
def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def check_cost_policy(header: dict, book: InstrumentBook) -> None:
    """Raises CostLowered: rates are read from the gate, and any declared number or schedule row may only
    raise the book's own table rate (L2800, L4090)."""
    costs = header.get("costs")
    if not isinstance(costs, dict) or costs.get("per_side") != "read_from_gate" or costs.get("floor") != "tick_floor":
        raise CostLowered("costs must be {per_side: read_from_gate, floor: tick_floor}; a card never sets its own rate")
    if book.cost_class is None:
        return
    table_bp = cost_bp(book.cost_class)
    declared = {k: v for k, v in costs.items() if k != "stress" and _is_num(v)}
    if _is_num(header.get("cost_bp")):
        declared["cost_bp"] = header["cost_bp"]
    for row in costs.get("schedule") or ():
        if not isinstance(row, dict) or "cost_class" not in row:
            raise CostLowered("a schedule row needs a cost_class")
        try:
            declared[f"schedule[{row['cost_class']}]"] = cost_bp(row["cost_class"])
        except KeyError as exc:
            raise CostLowered(str(exc)) from None
        for k, v in row.items():
            if k != "cost_class" and _is_num(v):
                declared[f"schedule[{row['cost_class']}].{k}"] = v
    low = {k: v for k, v in declared.items() if v < table_bp}
    if low:
        raise CostLowered(f"{low} below the {book.cost_class} table rate {table_bp} bp (DNB 23: lowering a cost is never a fix)")


def _notional(header: dict, book: InstrumentBook, lines: list, store_get: Callable[[str], Any],
              out: list[str]) -> Optional[float]:
    nav = header.get("notional_nav")
    markets = [book.market] if book.market else [l.get("market") for l in lines]
    key = None
    if isinstance(nav, dict):
        key = nav.get("ref") if set(nav) == {"ref"} else None
        parts = str(key).split(".")
        if not (key and len(parts) == 3 and parts[0] == "sleeves" and parts[2] == "notional_nav" and parts[1] in markets):
            out.append(f"2 notional_nav: a ref must be exactly {{ref: sleeves.<market>.notional_nav}} for {markets}, got {nav}")
            return None
    elif not _is_num(nav) or nav <= 0:
        out.append(f"2 notional_nav: must be > 0 (got {nav!r})")
        return None
    elif book.market is None:
        out.append("2 notional_nav: multi_line declares its notional via {ref: sleeves.<market>.notional_nav}")
        return None
    else:
        key = f"sleeves.{book.market}.notional_nav"
    stored = store_get(key)
    if stored is None:
        out.append(f"2 notional_nav: {key} is null (owner input: owner-signed sleeve notional)")
        return None
    if not _is_num(stored) or stored <= 0:
        out.append(f"2 notional_nav: {key} must be a positive number, got {stored!r}")
        return None
    if _is_num(nav) and nav != stored:
        out.append(f"2 notional_nav: {nav} differs from {key} = {stored} at commit (a card cannot declare its own notional)")
        return None
    return float(stored)


def fx_instrument_check(header: dict, rule: Any) -> list[str]:
    """R-17 / P10 / T-FX-01 (L1756): "An FX sleeve card declares its instrument, KRX USD futures or broker spot,
    before the run. A card without it is refused." Refused: an FX-market rule whose header book is missing, null or
    outside `FX_BOOKS`; a `multi_line` header with an FX line outside `FX_BOOKS`; an FX book on a card whose rule is
    not an FX-market rule (fail closed when the rule carries no market). FX costs 10 bp per side from the gate table
    (`cost_bp("fx")`), never a header literal (`check_cost_policy`). Nothing is written here."""
    tag = "13 FX instrument (R-17 / T-FX-01)"
    market = rule.get("market") if isinstance(rule, dict) else None
    book_id = header.get("instrument_book")
    lines = header.get("instrument_lines") or []
    out: list[str] = []
    if market == "FX" and book_id != "multi_line" and book_id not in FX_BOOKS:
        out.append(f"{tag}: an FX sleeve card declares its instrument before the run, one of {sorted(FX_BOOKS)}; got {book_id!r}")
    if book_id == "multi_line" and isinstance(lines, list):
        bad = [l for l in lines if isinstance(l, dict) and l.get("market") == "FX" and l.get("instrument_book") not in FX_BOOKS]
        if bad:
            out.append(f"{tag}: every FX line declares one of {sorted(FX_BOOKS)}; got {bad}")
    if book_id in FX_BOOKS and market != "FX":
        out.append(f"{tag}: {book_id} is an FX instrument but the rule's market is {market!r}, not 'FX'")
    return out


def header_checks(header: dict, store_get: Callable[[str], Any], *, rule: Optional[dict] = None,
                  contract_notional_krw: Optional[float] = None) -> list[str]:
    """The twelve R-26 header checks; an empty list is a clean header. `store_get(dotted_key)` reads the macro
    store (None when absent); `rule` is the §7.1 rule object of `header['rule_id']` (looked up as
    `rules.<rule_id>` when not passed); `contract_notional_krw` = price × multiplier × nav_fx at the commit."""
    out: list[str] = []
    missing = [f for f in HEADER_REQUIRED if header.get(f) is None]
    if missing:
        out.append(f"1 required: missing or null {missing}")
    rule = rule if rule is not None else store_get(f"rules.{header.get('rule_id')}")   # integration: provided by core/rules/macro_rules
    out += fx_instrument_check(header, rule)
    book = INSTRUMENT_BOOKS.get(header.get("instrument_book"))
    if header.get("instrument_book") is not None and book is None:
        out.append(f"1 instrument_book: unknown {header.get('instrument_book')!r}; known {sorted(INSTRUMENT_BOOKS)}")
    if book is None:
        return out
    lines = header.get("instrument_lines") or []
    lines = lines if isinstance(lines, list) else [None]
    line_books = [INSTRUMENT_BOOKS.get(l.get("instrument_book")) if isinstance(l, dict) else None for l in lines]
    if book.kind == "multi":
        markets = [l.get("market") for l in lines if isinstance(l, dict)]
        if not lines or len(set(markets)) != len(lines) or None in markets:
            out.append("12 multi_line: instrument_lines[] required, exactly one declared line per market")
        if any(b is None or b.kind == "multi" for b in line_books):
            out.append("12 multi_line: every line names a known single-line instrument book")
    elif lines:
        out.append("12 multi_line: instrument_lines[] only on multi_line")
    if header.get("rebalance") not in REBALANCE:
        out.append(f"3 rebalance: must be one of {REBALANCE}, got {header.get('rebalance')!r}")
    band = header.get("no_trade_band")
    if band not in NO_TRADE_BANDS or isinstance(band, bool):
        out.append(f"4 no_trade_band: must be 0 or 0.10, got {band!r}")
    elif band == 0.10 and not book.band_allowed:
        out.append(f"4 no_trade_band: 0.10 only on {sorted(STOCK_BOOKS)}, not {book.book_id}")
    notional = _notional(header, book, lines, store_get, out)
    costs = header.get("costs") if isinstance(header.get("costs"), dict) else {}
    if costs.get("per_side") != "read_from_gate" or costs.get("floor") != "tick_floor":
        out.append("5 costs: must reference the gate table with the tick floor (per_side: read_from_gate, floor: tick_floor)")
    if costs.get("stress") != GATE["cost_stress"] or costs.get("stress_line") != "printed":
        out.append(f"11 stress: every result also runs at {GATE['cost_stress']}x (costs.stress) with the stress line printed")
    try:
        check_cost_policy(header, book)
    except CostLowered as exc:
        out.append(f"10 cost: {exc}")
    printed = header.get("printed_lines") or costs.get("printed_lines") or []
    if "exec_variants_ABC" not in printed:
        out.append("7 execution variants: printed_lines must declare exec_variants_ABC (A same close, B next open, C one-session lag)")
    if book.kind == "futures":
        if header.get("roll_calendar") is None:
            out.append("6 futures: roll_calendar required")
        one = contract_notional_krw if contract_notional_krw is not None else book.contract_notional_krw
        if one is None:
            out.append(f"6 granularity: one contract's KRW notional for {book.book_id} is an owner input (multiplier); pass contract_notional_krw")
        elif notional is not None and one > GRANULARITY_MAX_SHARE * notional:
            out.append(f"6 granularity: one contract {one:,.0f} KRW > {GRANULARITY_MAX_SHARE:.0%} of the sleeve notional {notional:,.0f} (the ETF line is the book)")
    if not isinstance(rule, dict):
        out.append(f"8 rule object {header.get('rule_id')!r} not in the store; the market-scalar check needs its exposure_basis")
    elif (rule.get("exposure_basis") == "total" or rule.get("applies_to") == "market_gross") and (
            book.kind == "stock" or any(b is not None and b.kind == "stock" for b in line_books)):
        out.append("8 stock book as a market-gross scalar is refused (DNB 33; the US 50 bp rate is for single names only)")
    non_krw = [b.book_id for b in [book, *line_books] if b is not None and b.kind != "multi" and b.currency != "KRW"]
    if non_krw:
        fx = header.get("nav_fx")
        if not isinstance(fx, dict) or not fx.get("series"):
            out.append(f"9 nav_fx: non-KRW book {non_krw} needs nav_fx {{series, history, conversion_instant, role}}")
        elif fx.get("role") not in NAV_FX_ROLES:
            out.append(f"9 nav_fx.role: must be the role of the book it values {NAV_FX_ROLES}, got {fx.get('role')!r}")
    return out
