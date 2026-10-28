### Task 6: Costs, venue terms, bands, affordability and stakes (`core/odds/costs.py`)

**Files:**
- Create: `core/odds/costs.py` (LF, UTF-8, no BOM; a signed D14 closure file: `owner.code_files` globs
  `core/odds/*.py`, so it joins the code hash with no other change)
- Create: `tests/odds_costs.py` (LF, UTF-8, no BOM; `odds_costs` is already in `tests/odds_acceptance.MODULES`, Task 1)
- Modify: none. No existing file is edited, so the DRIFT RULE (R2-13) applies only to the names this task reads from
  a file the follow-up changed (`core/compliance/rules.py`: `Venue`, `Instrument`, `COST_BOOKS`, and Task 2's
  `Venue` odds fields and lookups). If an earlier plan renamed one, use the current name and record a one-line
  ruling under "Drift rulings" in the execution ledger.
- Test: `tests/odds_costs.py`

**Interfaces:**
- Consumes:
  - Task 2 (`core.compliance.rules`): `Venue.id`, `.sections`, the odds fields `.lot`, `.min_order`, `.fee_extras`
    (`(phi_buy, phi_sell)` in KRW or None), `.tick_ladder` (an absent key is `()` or None; the tests replace these
    fields with `dataclasses.replace`), `Venue.quote_for(inst) -> str`, `Venue.lot_for(symbol) -> float | None`,
    `Venue.min_order_for(quote) -> float | None`, `Venue.ladder_for(book) -> tuple[str, tuple[tuple[float, float],
    ...]] | None` (effective_from as a "YYYY-MM-DD" string); `Instrument.symbol`, `.cost_book` (`str | None`);
    `InstrumentMap.lookup(sections, symbol)`; `COST_BOOKS` (rules.py:72 at `5816d3c`).
  - Task 3: the shipped kis ladder, `F.approved().venues.venues["kis"].ladder_for("KRX_stock_book") ==
    ("2026-10-02", ((0.0, 1.0), (2000.0, 5.0), (5000.0, 10.0), (20000.0, 50.0), (50000.0, 100.0), (200000.0, 500.0),
    (500000.0, 1000.0)))`.
  - Task 5: `core.odds.plan.OKX_CAP_KEY` (`"okx_equity_share"`), `REPLAY_SOURCE`, `Plan`, `Leg`, `Bracket`, `fixed`,
    `kelly`, `bold`, `Fraction.kind` and `.value`; `tests.odds_fixtures.ODDS_VENUES` (CONTRACT 3.2: kis lot 1 for
    005930, 069500 and `default`, min_order {KRW: 0, USD: 0}, fee_extras 0/0, the KRX stock ladder; upbit lot
    `default` 1e-8, min_order {KRW: 5000}, fee_extras 0/0; okx lot `default` 1e-8, min_order {USDT: 1}, fee_extras
    0/0).
  - `tests.compliance_fixtures`: `approved(venues=<bytes>)` (cached `ApprovedState` with `.valid`, `.reason`,
    `.venues.venues`, `.instruments`) and `ctx(**overrides)` (owner limits `total_loss_floor_krw` 21,000 and
    `daily_loss_krw` 5,000, caps `okx_equity_share` 0.10; `model.OwnerState` is a frozen dataclass).
  - The originals, imported by the test only (never by `core/odds`): `core.quant.instruments.COMMISSION_BP`,
    `SELL_TAX_BP`, `TICK_TABLES`, `INSTRUMENT_BOOKS` (frozen `InstrumentBook` with `.tick_table` None, `.tax_side`
    "sell" and `.cost_class` on `KRX_stock_book`), `NotTradable`, `tick_size(table, price, on)`,
    `tick_floor_bp(price, tick, *, commission_bp, tax_bp)`, `cost_per_side(book, price=None, nav_fx=None, *, on=None,
    side="buy").bp` (a price-less call is the class-only table quote, the only form US_shares_KIS and crypto_venue
    accept, since neither has a tick table); `core.quant.validate.COST_BP_PER_SIDE`, `GATE["cost_stress"]`;
    `core.quant.tf_books.DELIST_STRESS`; the module-level assign `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0` of
    `core/engine/orders.py`, read with `ast.literal_eval`, never imported.
- Produces (`core/odds/costs.py`, exactly CONTRACT 6; Tasks 9 to 14 and 17 call these names):
  - Constants `COMMISSION_BP = 1.4`, `TABLE_BP = {"KRX_ETF_line": 3.0, "KRX_stock_book": 35.0, "US_shares_KIS":
    50.0, "crypto_venue": 10.0}`, `ETF_TICKS = ((date(2023, 12, 11), ((2000.0, 1.0), (math.inf, 5.0))),)`,
    `SELL_TAX_BP = {2026: 20.0}`, `COST_STRESS = 2.0`, `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0`, `DELIST_STRESS =
    (0.30, 1.00)`, `SCENARIOS = {"base": 1.0, "stress2x": COST_STRESS}`; `class NotTradable(ValueError)`.
  - `Terms` (frozen, kw_only): `venue, symbol, book, quote: str; lot, min_quote, min_krw, phi_buy, phi_sell: float;
    ladder: tuple[tuple[float, float], ...] | None; ladder_from: date | None; quote_krw: float`.
  - `terms(venue, inst, fx_krw_per_usd, *, replay=False) -> Terms` (NotTradable texts `"<venue> <symbol>: cost book
    <book!r> has no table rate"`, `": quote <q!r> has no KRW rate"`, `": no signed lot in the venues file"`, `": no
    signed minimum order in <quote>"`, `": no signed fixed charges (fee_extras; an explicit 0 is allowed)"`, `": no
    signed KRX stock tick ladder"`).
  - `etf_tick(price, on) -> float`, `ladder_tick(ladder, price) -> float`, `tick_floor_bp(price, tick, *,
    commission_bp=COMMISSION_BP, tax_bp=0.0) -> float`, `side_bp(terms, price, on, *, side) -> float`,
    `kappa(terms, prices, on, mult, *, side) -> np.ndarray` (the shape of `prices`; ValueError for a price that is
    not finite and > 0; NotTradable for a date `check_validity` refuses, so `simulate` runs `check_validity` first),
    `check_validity(terms, dates) -> None`, `kappa_bound(terms, p_min, dates, mult) -> float` (ValueError for no
    dates; `math.inf` when a ladder or ETF book gets `p_min <= 0`, which `hidden_range` reads as `k_x >= 1`).
  - `band(ref, limit, terms, on) -> tuple[np.ndarray, np.ndarray]` (ValueError for a reference that is not finite
    and > 0, on every book; non-KRX books then return `(zeros, +inf)` without reading `limit`, so a `nan` limit is
    fine there; a KRX book needs `0 < limit < 1`, else ValueError).
  - `r_exit(terms) -> float`, `afford(cash, floor, p, *, terms, on, mult, sizing, stop) -> np.ndarray` (`stop` may
    be None under `floor_safe`), `floor_units(stake, p, lot)`, `ceil_units(stake, p, lot)`, `min_units(p, terms)`,
    `rule_units(fraction, cash, p, *, terms, on, mult, target, w0, take_profit, stop, sizing, floor, fstar,
    cap_krw) -> tuple[np.ndarray, np.ndarray]` (`take_profit` may be None except for bold; `w0` is accepted and not
    read), `net_win_coefficient(terms, p0, on, take_profit, mult) -> float`, `first_stake(plan, terms, ctx, p0, on,
    *, fstar=None) -> float` (a Python float; 0.0 for no bet, at_floor, or an OKX cap that is not a number in
    (0, 1]), `cost_refusal(plan, terms, p0, on) -> str | None` (`"4kappa"`, `"bold"` or None).
  - Private helpers (module-local; later tasks call only the public names): `_SIDES`, `_KRX_BOOKS`, `_USD_QUOTES`,
    `_etf_rows(on)`, `_check_on(terms, on, side)`, `_rows(terms, on)`, `_ticks(terms, q, on)`,
    `_bp(terms, q, on, side)`.

**Plan decisions used:** Q1 (copies with equality tests), Q10 (band rounding per edge), Q11, Q24 (item 8: this
module's NotTradable becomes NOT_TRADABLE in `simulate`; item 12: `cost_refusal` gives COST_DOMINATED and a zero
`first_stake` STUCK_AT_START), Q25 and Q38 (a replay leg: zero-charge terms, `mult` 0.0), Q27, Q28, Q32 (why the
ceiling rests on the gross mark), Q41; RULINGS O1, O10, O11; RULINGS_ROUND2 R2-1, R2-2, R2-5.

- [ ] **Step 1: Write the failing test(s)**

  First confirm, read-only, that the earlier tasks this one consumes have landed. It runs Python, so it carries the
  Git Bash overlap prefix (header, "Python and test runs"). From the repo root in Git Bash:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from core.compliance import rules; from core.odds import plan; from tests import odds_fixtures as OF; assert all(hasattr(rules.Venue, n) for n in ('lot_for', 'min_order_for', 'ladder_for')); assert plan.OKX_CAP_KEY == 'okx_equity_share' and plan.REPLAY_SOURCE == 'replay:S_C3_crypto_trend_krwbtc'; assert isinstance(OF.ODDS_VENUES, bytes) and isinstance(rules.COST_BOOKS, frozenset); print('inputs ok')"
```

  Expected: `inputs ok`. No output and exit code 1: the overlap check found a QUANTGEN run; wait and re-run.
  Anything else: stop and rule (a missing Task 2, 3 or 5 piece, or a renamed name under the DRIFT RULE).

  The tests cover TASKS Task 6 bullet by bullet: the copies (`test_copied_constants_equal_the_originals`,
  `test_carry_multiplier_equals_orders_by_ast`); `side_bp` against `cost_per_side` on the ETF line from 2023-12-11
  and its refusal the day before (`test_etf_rate_equals_cost_per_side`); the 2,005-KRW fill
  (`test_etf_fill_at_2005_costs_at_least_13_8_bp`); the KRX stock floor with the venues ladder swapped in as a
  test-local tick table, the 2027 buy and sell, 46.4 / 35 bp at 200 KRW, restored in `finally`
  (`test_krx_stock_floor_equals_cost_per_side_with_the_ladder_swapped_in`); US 50 bp and crypto 10 bp
  (`test_us_and_crypto_pay_the_table_rate_with_no_floor_until_a_ladder_is_signed`); no tax on top
  (`test_no_separate_sell_tax_on_top`); `kappa` against `side_bp` (`test_kappa_equals_side_bp_element_by_element`);
  `check_validity` (`test_check_validity_copies_the_original_dates`); `kappa_bound` against a brute-force maximum
  (`test_kappa_bound_equals_the_brute_force_maximum`); `terms` and its replay form (`test_terms_from_the_fixture_venues`,
  `test_terms_refuse_a_missing_value_and_accept_explicit_zeros`, `test_replay_terms_need_only_the_lot_and_the_minimum`);
  the bands (`test_band_at_the_etf_reference_2005_is_1404_to_2605`, `test_band_keeps_the_price_inside_across_sessions`,
  `test_band_contains_the_reference_on_random_inputs`); the affordability bounds
  (`test_afford_bounds_hold_under_both_scenarios_plus_the_carry`); lots, minimums, bold, the first stake and the cost
  refusal (`test_lot_rounding_down_and_up`,
  `test_a_stake_below_the_minimum_is_no_bet_and_an_unaffordable_one_is_at_floor`,
  `test_bold_rounds_its_reaching_stake_up_when_affordable_and_cuts_it_otherwise`, `test_first_stake`,
  `test_cost_refusal_names_4kappa_and_bold`); and the documentation test of Q32
  (`test_why_the_ceiling_rests_on_the_gross_mark`). Every number asserted below was computed on a sandbox copy
  of the tree with the Task 2, 3 and 5 drafts (`.venv/Scripts/python.exe -I -B`, 2026-10-27).

  Create `tests/odds_costs.py` (whole file, LF):

```python
"""Costs, venue terms, bands, affordability and stakes (odds plan Task 6; spec 4 "Costs", 7.1, 7.2 "Bands"; spec 8
odds items 1, 4, 5; plan decisions Q11, Q27, Q28, Q32, Q41; RULINGS O1, O10, O11; R2-1, R2-2, R2-5).

Every copied constant equals its original; the per-side rate equals `instruments.cost_per_side` on the KRX ETF line
and, with the venues ladder swapped in as a test-local tick table, on the KRX stock book (a 2027 sell included).
The originals are imported here only; core/odds never imports them (O1), and core/engine/orders.py is read by AST.
"""
from __future__ import annotations

import ast
import dataclasses
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from core.compliance import rules
from core.odds import costs
from core.odds import plan as P
from core.quant import instruments as I
from core.quant import tf_books, validate
from tests import compliance_fixtures as F
from tests import odds_fixtures as OF

ROOT = Path(__file__).resolve().parents[1]
_KRX_LADDER = ((0.0, 1.0), (2000.0, 5.0), (5000.0, 10.0), (20000.0, 50.0), (50000.0, 100.0), (200000.0, 500.0),
               (500000.0, 1000.0))                     # the KRX stock ladder of the KRX tick page (CONTRACT 4.2)
_D = date(2026, 11, 2)                                 # a 2026 session date (a Monday)
_D27 = date(2027, 1, 4)                                # a 2027 date (a Monday): no stock sell tax copied for 2027
_SIDES = ("buy", "sell")
_GRID = sorted({1.0, 2.0, 3.0, 7.5, 50.0, 99.0, 100.0, 148.0, 149.0, 150.0, 200.0, 367.0, 368.0, 369.0, 500.0,
                1000.0, 1999.0, 1999.99, 2000.0, 2000.01, 2001.0, 2005.0, 3125.0, 4999.0, 5000.0, 9999.0, 15625.0,
                19999.0, 20000.0, 49999.0, 50000.0, 70000.0, 199999.0, 200000.0, 499999.0, 500000.0, 1e6}
               | {round(float(x), 2) for x in np.geomspace(1.0, 1e6, 80)})      # 1 to 1e6, the row starts included


def _raises(fn, exc, text: str) -> str:
    try:
        fn()
    except exc as err:
        assert type(err) is exc, (type(err), exc)
        assert text in str(err), (text, str(err))
        return str(err)
    raise AssertionError(f"expected {exc.__name__}: {text}")


def _state():
    state = F.approved(venues=OF.ODDS_VENUES)          # cached; kis, upbit and okx with every odds key
    assert state.valid, state.reason
    return state


def _terms(venue_id: str, symbol: str, *, fx: float = 1400.0, replay: bool = False, inst_changes=None,
           **changes) -> costs.Terms:
    """costs.terms on the ODDS_VENUES venue with `changes` applied to its parsed fields (a missing value is () or
    None, exactly as the parser leaves an absent key)."""
    state = _state()
    venue = dataclasses.replace(state.venues.venues[venue_id], **changes)
    inst = state.instruments.lookup(venue.sections, symbol)
    if inst_changes:
        inst = dataclasses.replace(inst, **inst_changes)
    return costs.terms(venue, inst, fx, replay=replay)


def _t(name: str) -> costs.Terms:
    """The fixture legs: etf kis 069500, stock kis 005930, us kis AAPL, btc upbit BTC, okx okx BTC, and us_ladder
    (AAPL with a signed USD 0.01 tick from 2026-01-02, a ladder no shipped file has)."""
    if name == "us_ladder":
        return _terms("kis", "AAPL", tick_ladder=(("US_shares_KIS", "2026-01-02", ((0.0, 0.01),)),))
    venue, symbol = {"etf": ("kis", "069500"), "stock": ("kis", "005930"), "us": ("kis", "AAPL"),
                     "btc": ("upbit", "BTC"), "okx": ("okx", "BTC")}[name]
    return _terms(venue, symbol)


def _plan(venue: str = "upbit", symbol: str = "BTC", *, fraction=None, bracket=None, sizing: str = "floor_safe",
          edge_source: str = "none", stake: float = 42_000.0, target: float = 42_000_000.0) -> P.Plan:
    return P.Plan(name="costs", track="compounding", stake_krw=stake, target_krw=target, fx_krw_per_usd=1400.0,
                  start=date(2026, 10, 23), horizon_days=10,
                  leg=P.Leg(venue=venue, symbol=symbol, model="bootstrap", bracket=bracket, sizing=sizing,
                            edge_source=edge_source),
                  fraction=P.fixed(1.0) if fraction is None else fraction)


def _outcome(fn):
    """("ok", value) or ("raise", message) of one call; the two NotTradable classes compare by message."""
    try:
        return ("ok", fn())
    except (I.NotTradable, costs.NotTradable) as err:
        return ("raise", str(err))


# --------------------------------------------------------------------------- #
# Copied constants (O1)
# --------------------------------------------------------------------------- #
def test_copied_constants_equal_the_originals():
    assert costs.COMMISSION_BP == I.COMMISSION_BP == 1.4
    assert set(costs.TABLE_BP) == set(rules.COST_BOOKS)
    for book, bp in costs.TABLE_BP.items():
        assert bp == validate.COST_BP_PER_SIDE[I.INSTRUMENT_BOOKS[book].cost_class], book
        assert bp == I.cost_per_side(book).bp, book                     # the class-only quote
    assert costs.ETF_TICKS == I.TICK_TABLES["KRX_ETF"]
    assert costs.SELL_TAX_BP == I.SELL_TAX_BP == {2026: 20.0} and type(costs.SELL_TAX_BP) is dict
    assert costs.SELL_TAX_BP is not I.SELL_TAX_BP
    assert costs.COST_STRESS == validate.GATE["cost_stress"] == 2.0
    assert costs.DELIST_STRESS == tf_books.DELIST_STRESS == (0.30, 1.00)
    assert costs.SCENARIOS == {"base": 1.0, "stress2x": 2.0}
    assert issubclass(costs.NotTradable, ValueError) and not issubclass(costs.NotTradable, I.NotTradable)
    for p in _GRID:
        for tick in (0.0, 0.01, 1.0, 5.0, 1000.0):
            for tax in (0.0, 20.0):
                assert costs.tick_floor_bp(p, tick, tax_bp=tax) == I.tick_floor_bp(p, tick, tax_bp=tax), (p, tick)
    for p, tick in ((0.0, 1.0), (-1.0, 1.0), (math.nan, 1.0), (math.inf, 1.0), (100.0, -1.0), (100.0, math.inf)):
        want = _raises(lambda: I.tick_floor_bp(p, tick), ValueError, "must be finite and positive")
        assert _raises(lambda: costs.tick_floor_bp(p, tick), ValueError, "must be finite and positive") == want


def test_carry_multiplier_equals_orders_by_ast():
    tree = ast.parse((ROOT / "core" / "engine" / "orders.py").read_text(encoding="utf-8"))
    values = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "LIMIT_DOWN_CARRY_COST_MULTIPLIER" for t in node.targets)]
    assert values == [costs.LIMIT_DOWN_CARRY_COST_MULTIPLIER] == [2.0], values


# --------------------------------------------------------------------------- #
# Venue terms (Q11, Q17, R2-5)
# --------------------------------------------------------------------------- #
def test_terms_from_the_fixture_venues():
    state = _state()
    ladder_from, ladder = state.venues.venues["kis"].ladder_for("KRX_stock_book")
    assert ladder == _KRX_LADDER
    shipped = F.approved().venues.venues["kis"].ladder_for("KRX_stock_book")      # Task 3's sourced ladder
    assert shipped == (ladder_from, _KRX_LADDER), shipped
    base = dict(lot=1.0, min_quote=0.0, min_krw=0.0, phi_buy=0.0, phi_sell=0.0, ladder=None, ladder_from=None,
                quote_krw=1.0)
    want = {
        "etf": costs.Terms(venue="kis", symbol="069500", book="KRX_ETF_line", quote="KRW", **base),
        "stock": costs.Terms(venue="kis", symbol="005930", book="KRX_stock_book", quote="KRW",
                             **{**base, "ladder": _KRX_LADDER, "ladder_from": date.fromisoformat(ladder_from)}),
        "us": costs.Terms(venue="kis", symbol="AAPL", book="US_shares_KIS", quote="USD",
                          **{**base, "quote_krw": 1400.0}),
        "btc": costs.Terms(venue="upbit", symbol="BTC", book="crypto_venue", quote="KRW",
                           **{**base, "lot": 1e-8, "min_quote": 5000.0, "min_krw": 5000.0}),
        "okx": costs.Terms(venue="okx", symbol="BTC", book="crypto_venue", quote="USDT",
                           **{**base, "lot": 1e-8, "min_quote": 1.0, "min_krw": 1400.0, "quote_krw": 1400.0}),
    }
    for name, terms in want.items():
        assert _t(name) == terms, (name, _t(name))
    assert type(_t("stock").ladder_from) is date and type(_t("okx").min_krw) is float


def test_terms_refuse_a_missing_value_and_accept_explicit_zeros():
    cases = (("kis", "005930", {"lot": ()}, "kis 005930: no signed lot in the venues file"),
             ("kis", "AAPL", {"lot": (("005930", 1.0),)}, "kis AAPL: no signed lot in the venues file"),
             ("kis", "069500", {"min_order": ()}, "kis 069500: no signed minimum order in KRW"),
             ("kis", "AAPL", {"min_order": (("KRW", 0.0),)}, "kis AAPL: no signed minimum order in USD"),
             ("okx", "BTC", {"min_order": (("USDC", 1.0),)}, "okx BTC: no signed minimum order in USDT"),
             ("upbit", "BTC", {"fee_extras": None},
              "upbit BTC: no signed fixed charges (fee_extras; an explicit 0 is allowed)"),
             ("kis", "005930", {"tick_ladder": ()}, "kis 005930: no signed KRX stock tick ladder"))
    for venue_id, symbol, change, text in cases:
        _raises(lambda: _terms(venue_id, symbol, **change), costs.NotTradable, text)
    _raises(lambda: _terms("okx", "BTC", fx=math.nan), costs.NotTradable, "okx BTC: quote 'USDT' has no KRW rate")
    _raises(lambda: _terms("okx", "BTC", fx=math.inf), costs.NotTradable, "okx BTC: quote 'USDT' has no KRW rate")
    _raises(lambda: _terms("kis", "AAPL", fx=0.0), costs.NotTradable, "kis AAPL: quote 'USD' has no KRW rate")
    _raises(lambda: _terms("kis", "AAPL", inst_changes={"cost_book": None}), costs.NotTradable,
            "kis AAPL: cost book None has no table rate")
    assert _terms("kis", "069500", tick_ladder=()).ladder is None           # an ETF needs no venues ladder
    btc, stock = _t("btc"), _t("stock")
    assert (btc.phi_buy, btc.phi_sell, stock.min_quote, stock.min_krw) == (0.0, 0.0, 0.0, 0.0)   # signed zeros
    charged = _terms("upbit", "BTC", fee_extras=(300.0, 500.0))
    assert (charged.phi_buy, charged.phi_sell, costs.r_exit(charged)) == (300.0, 500.0, 2000.0)


def test_replay_terms_need_only_the_lot_and_the_minimum():
    replay = _terms("upbit", "BTC", fee_extras=None, replay=True)
    assert replay == dataclasses.replace(_t("btc"), phi_buy=0.0, phi_sell=0.0)
    assert _terms("upbit", "BTC", fee_extras=(300.0, 500.0), replay=True) == replay   # fee_extras is never read
    assert costs.r_exit(replay) == 0.0
    _raises(lambda: _terms("upbit", "BTC", fee_extras=None, lot=(), replay=True), costs.NotTradable,
            "upbit BTC: no signed lot in the venues file")
    _raises(lambda: _terms("upbit", "BTC", fee_extras=None, min_order=(), replay=True), costs.NotTradable,
            "upbit BTC: no signed minimum order in KRW")
    _raises(lambda: _terms("upbit", "BTC", fee_extras=None), costs.NotTradable, "no signed fixed charges")


# --------------------------------------------------------------------------- #
# Per-side rate (Q11, R2-1)
# --------------------------------------------------------------------------- #
def test_etf_rate_equals_cost_per_side():
    etf = _t("etf")
    dates = (date(2023, 12, 11), date(2024, 6, 3), date(2025, 1, 2), date(2026, 10, 26), date(2027, 12, 30))
    for on in dates:
        for p in _GRID:
            assert costs.etf_tick(p, on) == I.tick_size("KRX_ETF", p, on), (p, on)
            for side in _SIDES:
                want = I.cost_per_side("KRX_ETF_line", p, on=on, side=side).bp
                assert costs.side_bp(etf, p, on, side=side) == want, (p, on, side)
    early = date(2023, 12, 10)
    for side in _SIDES:
        _raises(lambda: I.cost_per_side("KRX_ETF_line", 2005.0, on=early, side=side), I.NotTradable,
                "no tick row effective on 2023-12-10")
        _raises(lambda: costs.side_bp(etf, 2005.0, early, side=side), costs.NotTradable,
                "KRX_ETF: no tick row effective on 2023-12-10")
    assert costs.etf_tick(1999.99, _D) == 1.0 and costs.etf_tick(2000.0, _D) == 5.0


def test_etf_fill_at_2005_costs_at_least_13_8_bp():
    for on in (date(2026, 10, 26), _D, date(2026, 12, 30)):
        for side in _SIDES:
            bp = costs.side_bp(_t("etf"), 2005.0, on, side=side)
            assert bp == costs.tick_floor_bp(2005.0, 5.0) == I.tick_floor_bp(2005.0, 5.0) == 13.868827930174565
            assert bp >= 13.8 and f"{bp:.4f}" == "13.8688"


def test_krx_stock_floor_equals_cost_per_side_with_the_ladder_swapped_in():
    stock = _t("stock")
    key = "ODDS_TEST_KRX_STOCK"
    rows = tuple((stock.ladder[i + 1][0] if i + 1 < len(stock.ladder) else math.inf, tick)
                 for i, (_start, tick) in enumerate(stock.ladder))    # the original's (price strictly below, tick)
    book = I.INSTRUMENT_BOOKS["KRX_stock_book"]
    assert book.tick_table is None and book.tax_side == "sell" and key not in I.TICK_TABLES
    try:                                        # both patches inside: a half-applied one is still undone
        I.TICK_TABLES[key] = ((stock.ladder_from, rows),)
        I.INSTRUMENT_BOOKS["KRX_stock_book"] = dataclasses.replace(book, tick_table=key)
        for on in (stock.ladder_from, _D, date(2026, 12, 30)):
            for p in _GRID:
                assert costs.ladder_tick(stock.ladder, p) == I.tick_size(key, p, on), (p, on)
                for side in _SIDES:
                    want = I.cost_per_side("KRX_stock_book", p, on=on, side=side).bp
                    assert costs.side_bp(stock, p, on, side=side) == want, (p, on, side)
        for p in _GRID:                         # 2027: buys equal, every sell raises where the original raises
            for side in _SIDES:
                want = _outcome(lambda: I.cost_per_side("KRX_stock_book", p, on=_D27, side=side).bp)
                assert _outcome(lambda: costs.side_bp(stock, p, _D27, side=side)) == want, (p, side)
                assert want[0] == ("raise" if side == "sell" else "ok"), (p, side, want)
        _raises(lambda: costs.side_bp(stock, 70000.0, _D27, side="sell"), costs.NotTradable,
                "stock sell tax for 2027 is an owner input")
        early = stock.ladder_from - timedelta(days=1)
        for side in _SIDES:
            _raises(lambda: I.cost_per_side("KRX_stock_book", 70000.0, on=early, side=side), I.NotTradable,
                    f"no tick row effective on {early}")
            _raises(lambda: costs.side_bp(stock, 70000.0, early, side=side), costs.NotTradable,
                    f"KRX_stock_book: no tick row effective on {early}")
        sell, buy = costs.side_bp(stock, 200.0, _D, side="sell"), costs.side_bp(stock, 200.0, _D, side="buy")
        assert sell == I.cost_per_side("KRX_stock_book", 200.0, on=_D, side="sell").bp and f"{sell:.1f}" == "46.4"
        assert buy == I.cost_per_side("KRX_stock_book", 200.0, on=_D, side="buy").bp == 35.0
    finally:
        I.INSTRUMENT_BOOKS["KRX_stock_book"] = book
        I.TICK_TABLES.pop(key, None)
    assert I.INSTRUMENT_BOOKS["KRX_stock_book"] is book and key not in I.TICK_TABLES
    _raises(lambda: I.cost_per_side("KRX_stock_book", 70000.0, on=_D), I.NotTradable, "owner input")   # T-COST-02


def test_us_and_crypto_pay_the_table_rate_with_no_floor_until_a_ladder_is_signed():
    for name, bp in (("us", 50.0), ("btc", 10.0), ("okx", 10.0)):
        terms = _t(name)
        assert terms.ladder is None and bp == I.cost_per_side(terms.book).bp
        for p in (0.5, 1.0, 1400.0, 1.4e6, 1.4e8):
            for side in _SIDES:
                assert costs.side_bp(terms, p, _D, side=side) == bp, (name, p, side)
    us = _t("us_ladder")
    assert us.ladder == ((0.0, 0.01),) and us.ladder_from == date(2026, 1, 2)
    for side in _SIDES:
        assert costs.side_bp(us, 700.0, _D, side=side) == costs.tick_floor_bp(0.5, 0.01)       # USD 0.50
        assert costs.side_bp(us, 700.0, _D, side=side) > 100.0
        assert costs.side_bp(us, 280_000.0, _D, side=side) == 50.0                             # USD 200
        _raises(lambda: costs.side_bp(us, 700.0, date(2026, 1, 1), side=side), costs.NotTradable,
                "US_shares_KIS: no tick row effective on 2026-01-01")


def test_no_separate_sell_tax_on_top():
    for name in ("etf", "us", "btc", "okx", "us_ladder"):
        terms = _t(name)
        for p in _GRID:
            assert costs.side_bp(terms, p, _D, side="sell") == costs.side_bp(terms, p, _D, side="buy"), (name, p)
    stock = _t("stock")
    for p in _GRID:
        sell, buy = costs.side_bp(stock, p, _D, side="sell"), costs.side_bp(stock, p, _D, side="buy")
        assert buy <= sell <= buy + costs.SELL_TAX_BP[2026], p          # the tax sits inside the floor's max
    for p in (368.0, 1000.0, 70000.0, 1e6):
        assert costs.side_bp(stock, p, _D, side="sell") == costs.side_bp(stock, p, _D, side="buy") == 35.0, p
    assert costs.side_bp(stock, 367.0, _D, side="sell") > 35.0 == costs.side_bp(stock, 149.0, _D, side="buy")
    assert costs.side_bp(stock, 148.0, _D, side="buy") > 35.0
    _raises(lambda: costs.side_bp(stock, 70000.0, _D, side="SELL"), ValueError, "side must be 'buy' or 'sell'")
    _raises(lambda: costs.side_bp(_t("btc"), 0.0, _D, side="buy"), ValueError, "must be finite and > 0")


def test_kappa_equals_side_bp_element_by_element():
    prices = np.array(_GRID)
    for name in ("etf", "stock", "us", "btc", "okx", "us_ladder"):
        terms = _t(name)
        for side in _SIDES:
            for mult in (0.0, 1.0, 2.0):
                got = costs.kappa(terms, prices, _D, mult, side=side)
                want = np.array([costs.side_bp(terms, p, _D, side=side) * 1e-4 * mult for p in _GRID])
                assert got.shape == prices.shape and np.array_equal(got, want), (name, side, mult)
    for bad in (np.nan, 0.0, -1.0):
        _raises(lambda: costs.kappa(_t("etf"), np.array([2005.0, bad]), _D, 1.0, side="buy"), ValueError,
                "every price must be finite and > 0")
    _raises(lambda: costs.kappa(_t("stock"), np.array([70000.0]), _D27, 1.0, side="sell"), costs.NotTradable,
            "stock sell tax for 2027")


def test_check_validity_copies_the_original_dates():
    horizon = tuple(date(2026, 10, 26) + timedelta(days=k) for k in range(66))      # 2026-10-26 .. 2026-12-30
    for name in ("etf", "stock", "us", "btc", "okx", "us_ladder"):
        assert costs.check_validity(_t(name), horizon) is None, name
    _raises(lambda: costs.check_validity(_t("etf"), (date(2023, 12, 10),)), costs.NotTradable,
            "KRX_ETF: no tick row effective on 2023-12-10")
    assert costs.check_validity(_t("etf"), (date(2023, 12, 11), date(2027, 6, 1))) is None   # ETFs pay no sell tax
    stock = _t("stock")
    _raises(lambda: costs.check_validity(stock, horizon + (_D27,)), costs.NotTradable,
            "stock sell tax for 2027 is an owner input")
    early = stock.ladder_from - timedelta(days=1)
    _raises(lambda: costs.check_validity(stock, (early,) + horizon), costs.NotTradable,
            f"KRX_stock_book: no tick row effective on {early}")
    _raises(lambda: costs.check_validity(_t("us_ladder"), (date(2026, 1, 1),)), costs.NotTradable,
            "US_shares_KIS: no tick row effective on 2026-01-01")
    assert costs.check_validity(_t("btc"), (date(2020, 1, 1), date(2027, 12, 31))) is None


def test_kappa_bound_equals_the_brute_force_maximum():
    dates = (date(2026, 10, 26), date(2026, 12, 30))
    for name, p_min, want_bp in (("etf", 1500.0, 13.9), ("etf", 2001.0, None), ("stock", 100.0, 71.4),
                                 ("stock", 1000.0, 35.0), ("stock", 2003.5, None), ("us_ladder", 70.0, None)):
        terms = _t(name)
        starts = np.array([0.0, 2000.0] if terms.book == "KRX_ETF_line" else [s * terms.quote_krw
                                                                             for s, _ in terms.ladder])
        grid = np.unique(np.concatenate([np.arange(p_min, p_min + 6000.0, 0.25), np.geomspace(p_min, 2e6, 20000),
                                         starts[starts >= p_min]]))
        for mult in (1.0, 2.0):
            brute = max(float(np.max(costs.kappa(terms, grid, on, mult, side=side))) for on in dates for side in _SIDES)
            assert costs.kappa_bound(terms, p_min, dates, mult) == brute, (name, p_min, mult)
        if want_bp is not None:
            assert f"{costs.kappa_bound(terms, p_min, dates, 1.0) * 1e4:.1f}" == f"{want_bp:.1f}", (name, p_min)
    stock = _t("stock")
    buy_only = float(np.max(costs.kappa(stock, np.arange(100.0, 6100.0, 0.25), _D, 1.0, side="buy")))
    assert f"{buy_only * 1e4:.1f}" == "51.4"                       # the bound at p_min 100 is the sell side's 71.4
    assert costs.kappa_bound(_t("btc"), 1e-300, dates, 2.0) == costs.TABLE_BP["crypto_venue"] * 1e-4 * 2.0
    assert costs.kappa_bound(stock, 0.0, dates, 1.0) == math.inf
    _raises(lambda: costs.kappa_bound(_t("etf"), 100.0, (), 1.0), ValueError, "kappa_bound needs at least one date")
    _raises(lambda: costs.kappa_bound(stock, 100.0, dates + (_D27,), 1.0), costs.NotTradable, "stock sell tax for 2027")


# --------------------------------------------------------------------------- #
# Bands (Q10, Q41, R2-2)
# --------------------------------------------------------------------------- #
def _tick_of(terms: costs.Terms, prices) -> np.ndarray:
    """The tick at each price from the public scalar lookups (an oracle independent of band's own)."""
    if terms.book == "KRX_ETF_line":
        return np.array([costs.etf_tick(float(x), _D) for x in prices])
    return np.array([costs.ladder_tick(terms.ladder, float(x)) for x in prices])


def test_band_at_the_etf_reference_2005_is_1404_to_2605():
    for name in ("etf", "stock"):
        lo, hi = costs.band(np.array([2005.0]), 0.30, _t(name), _D)
        assert (float(lo[0]), float(hi[0])) == (1404.0, 2605.0), name     # 1,405 only with the reference's tick 5
    lo, hi = costs.band(np.array([2005.0, 5e7]), 0.30, _t("btc"), _D)
    assert np.array_equal(lo, [0.0, 0.0]) and np.array_equal(hi, [math.inf, math.inf])
    _raises(lambda: costs.band(np.array([2005.0]), 1.0, _t("etf"), _D), ValueError, "price limit 1.0 must be in (0, 1)")
    lo, hi = costs.band(np.array([1.5]), 0.30, _t("etf"), _D)              # raw edges 2 and 1: clamped to the ref
    assert (float(lo[0]), float(hi[0])) == (1.5, 1.5)
    for name, bad in (("etf", 0.0), ("stock", -5.0), ("btc", math.nan)):   # never a silent wrap to the top row
        _raises(lambda: costs.band(np.array([2005.0, bad]), 0.30, _t(name), _D), ValueError,
                "band: every reference must be finite and > 0")


def test_band_keeps_the_price_inside_across_sessions():
    stock = _t("stock")
    steps = [(100.0, 70.0, 130.0), (70.0, 49.0, 91.0), (91.0, 64.0, 118.0)]       # 100 -> 70 -> at most 91 -> 100
    for ref, d, u in steps:
        lo, hi = costs.band(np.array([ref]), 0.30, stock, _D)
        assert (float(lo[0]), float(hi[0])) == (d, u), ref
    assert steps[2][1] <= 100.0 <= steps[2][2]                                     # back up to 100 inside that band
    rng = np.random.default_rng(6)
    for name in ("etf", "stock"):
        terms = _t(name)
        p = np.full(200, 2005.0)
        for _session in range(60):
            lo, hi = costs.band(p, 0.30, terms, _D)
            d, u = p * (1.0 - 0.30), p * (1.0 + 0.30)
            down, up = _tick_of(terms, d), _tick_of(terms, u)
            assert np.array_equal(lo, np.ceil(d / down - 1e-9) * down), name   # each edge at its own tick, and
            assert np.array_equal(hi, np.floor(u / up + 1e-9) * up), name      # for an on-tick ref no clamp fires
            assert np.all((lo <= p) & (p <= hi)), name                          # so the rounded edges contain it
            pick = rng.integers(0, 3, p.size)
            inside = lo + rng.random(p.size) * (hi - lo)
            tick = _tick_of(terms, inside)
            inside = np.clip(np.round(inside / tick) * tick, lo, hi)
            p = np.where(pick == 0, lo, np.where(pick == 1, hi, inside))       # an edge or an on-tick inner close


def test_band_contains_the_reference_on_random_inputs():
    rng = np.random.default_rng(7)
    for name in ("etf", "stock"):
        terms = _t(name)
        raw = np.exp(rng.uniform(0.0, math.log(1e6), 1000))
        tick = _tick_of(terms, raw)
        refs = np.maximum(np.round(raw / tick) * tick, tick)                   # closes sit on the tick grid
        for limit in rng.uniform(0.01, 0.99, 10):
            lo, hi = costs.band(refs, float(limit), terms, _D)
            assert np.all((0.0 < lo) & (lo <= refs) & (refs <= hi)), (name, limit)
            for edge in (lo, hi):
                own = _tick_of(terms, edge)
                assert np.all(np.abs(edge / own - np.round(edge / own)) < 1e-9), (name, limit)
        loose = rng.uniform(1.0, 1e6, 500)
        lo, hi = costs.band(loose, 0.30, terms, _D)
        assert np.all((lo <= loose) & (loose <= hi))                          # off-tick refs are clamped


# --------------------------------------------------------------------------- #
# Affordability and stakes (Q11, Q27, Q28)
# --------------------------------------------------------------------------- #
def test_afford_bounds_hold_under_both_scenarios_plus_the_carry():
    rng = np.random.default_rng(8)
    n, carry = 4000, costs.LIMIT_DOWN_CARRY_COST_MULTIPLIER
    for terms, lo_p, hi_p in ((dataclasses.replace(_t("stock"), phi_buy=150.0, phi_sell=250.0), 100.0, 1e6),
                              (dataclasses.replace(_t("etf"), phi_buy=0.0, phi_sell=700.0), 100.0, 1e5),
                              (dataclasses.replace(_t("btc"), phi_buy=1000.0, phi_sell=1000.0), 1e6, 1e8)):
        cash = rng.uniform(1e3, 1e7, n)
        floor = cash * rng.uniform(0.0, 0.95, n)
        p = np.exp(rng.uniform(math.log(lo_p), math.log(hi_p), n))
        stop = rng.uniform(0.01, 0.95, n)
        tol = 1e-7 * cash
        for mult in costs.SCENARIOS.values():
            kb = costs.kappa(terms, p, _D, mult, side="buy")
            for sizing in ("floor_safe", "stop_based"):
                a = costs.afford(cash, floor, p, terms=terms, on=_D, mult=mult, sizing=sizing, stop=stop)
                assert np.all(a >= 0.0) and np.mean(a > 0.0) > 0.5, (terms.book, mult, sizing)
                bet = a > 0.0
                left = cash - a * (1.0 + kb) - mult * terms.phi_buy        # cash right after the entry
                worst = left - mult * carry * terms.phi_sell               # a locked exit of a worthless position
                assert np.all(worst[bet] >= -tol[bet]), (terms.book, mult, sizing)   # the always rule
                if sizing == "floor_safe":
                    assert np.all(worst[bet] >= floor[bet] - tol[bet]), (terms.book, mult)   # >= L after a total loss
                    gap = left - costs.r_exit(terms) - floor               # zero where the stake is the largest
                    assert np.all(np.abs(gap[bet]) <= tol[bet]), (terms.book, mult)
                else:
                    ks = costs.kappa(terms, p * (1.0 - stop), _D, mult, side="sell")
                    at_stop = left + a * (1.0 - stop) * (1.0 - ks) - mult * terms.phi_sell
                    assert np.all(at_stop[bet] >= floor[bet] - tol[bet]), (terms.book, mult)
                    tight = np.minimum(left - costs.r_exit(terms), at_stop - floor)
                    assert np.all(np.abs(tight[bet]) <= tol[bet]), (terms.book, mult)
    assert costs.r_exit(dataclasses.replace(_t("btc"), phi_sell=250.0)) == 1000.0             # 4 x phi_sell
    _raises(lambda: costs.afford(1e6, 0.0, 5e7, terms=_t("btc"), on=_D, mult=1.0, sizing="always", stop=None),
            ValueError, "sizing must be floor_safe or stop_based")


def test_lot_rounding_down_and_up():
    assert costs.floor_units(10_000.0, 3_000.0, 1.0) == 3.0 and costs.ceil_units(10_000.0, 3_000.0, 1.0) == 4.0
    for k in range(1, 1000):
        for p, lot in ((3_000.0, 1.0), (2_005.0, 1.0), (5e7, 1e-8), (1.4e8, 1e-8)):
            stake = k * lot * p
            assert costs.floor_units(stake, p, lot) == costs.ceil_units(stake, p, lot) == k * lot, (k, p, lot)
    assert costs.floor_units(5_000.0, 5e7, 1e-8) == 10_000 * 1e-8
    assert np.array_equal(costs.min_units(np.array([5e7, 70_000.0]), _t("btc")),
                          [10_000 * 1e-8, 7_142_858 * 1e-8])          # KRW 5,000 rounded up to whole lots
    assert costs.min_units(70_000.0, _t("stock")) == 1.0 and costs.min_units(2_005.0, _t("etf")) == 1.0
    assert costs.min_units(1.4e8, _t("okx")) == 1_000 * 1e-8                     # USDT 1 = KRW 1,400 = 1,000 lots


def _rule(fraction, cash, p, *, terms=None, floor=21_000.0, target=42_000_000.0, take_profit=None, stop=None,
          sizing="floor_safe", fstar=None, cap_krw=None, mult=1.0):
    return costs.rule_units(fraction, np.asarray(cash, dtype=float), np.asarray(p, dtype=float),
                            terms=_t("btc") if terms is None else terms, on=_D, mult=mult, target=target, w0=42_000.0,
                            take_profit=take_profit, stop=stop, sizing=sizing, floor=floor, fstar=fstar,
                            cap_krw=cap_krw)


def test_a_stake_below_the_minimum_is_no_bet_and_an_unaffordable_one_is_at_floor():
    units, at_floor = _rule(P.fixed(0.1), [42_000.0, 25_000.0], [5e7, 5e7])
    assert units.tolist() == [0.0, 0.0] and at_floor.tolist() == [False, True]   # 4,200 < 5,000; afford 3,996
    units, at_floor = _rule(P.fixed(1.0), [42_000.0, 25_000.0], [5e7, 5e7])
    assert units[0] == 41_958 * 1e-8 and units[1] == 0.0 and at_floor.tolist() == [False, True]
    assert abs(float(units[0]) * 5e7 - 20_979.0) < 1e-6                    # (42,000 - 21,000) / 1.001, down to lots
    units, at_floor = _rule(P.fixed(1.0), [42_000.0], [5e7], cap_krw=4_200.0)
    assert units.tolist() == [0.0] and at_floor.tolist() == [True]          # a cap below the minimum
    units, at_floor = _rule(P.kelly(0.5), [42_000.0], [5e7], fstar=0.5)
    assert units[0] == 21_000 * 1e-8 and not at_floor[0]                     # 0.5 x 0.5 x 42,000 = KRW 10,500
    units, at_floor = _rule(P.kelly(0.5), [42_000.0], [5e7], fstar=0.2)
    assert units.tolist() == [0.0] and not at_floor[0]                       # KRW 4,200: below the minimum
    units, _ = _rule(P.fixed(0.5), [100_000.0], [5e7])                       # w0 stays 42,000: the rules read cash
    assert units.tolist() == [100_000 * 1e-8]                                # 0.5 x KRW 100,000
    units, _ = _rule(P.kelly(0.5), [100_000.0], [5e7], fstar=0.5)
    assert units.tolist() == [50_000 * 1e-8]                                 # 0.5 x 0.5 x KRW 100,000
    _raises(lambda: _rule(P.kelly(0.5), [42_000.0], [5e7]), ValueError, "a kelly stake needs fstar")
    _raises(lambda: _rule(P.Fraction(kind="half"), [42_000.0], [5e7]), ValueError, "unknown fraction 'half'")
    cash = 26_004.9999999999                                               # afford a hair below the KRW 5,000 minimum
    a = float(costs.afford(cash, 21_000.0, 5e7, terms=_t("btc"), on=_D, mult=1.0, sizing="floor_safe", stop=None))
    assert a < 5_000.0 and float(costs.floor_units(a, 5e7, 1e-8)) * 5e7 == 5_000.0   # the lot tolerance rounds it up
    units, at_floor = _rule(P.fixed(1.0), [cash], [5e7])
    assert units.tolist() == [0.0] and at_floor.tolist() == [True]          # at_floor buys nothing all the same


def test_bold_rounds_its_reaching_stake_up_when_affordable_and_cuts_it_otherwise():
    stock, p, tp = _t("stock"), 70_000.0, 1.0
    c_w = costs.net_win_coefficient(stock, p, _D, tp, 1.0)
    assert f"{c_w:.4f}" == "0.9895"                                          # 1 - 0.0035 x 3
    reach = (1_100_000.0 - 1_000_000.0) / c_w                                # KRW 101,061: 1.44 shares
    units, at_floor = _rule(P.bold(), [1e6], [p], terms=stock, floor=0.0, target=1_100_000.0, take_profit=tp,
                            stop=0.5)
    assert units.tolist() == [2.0] and not at_floor[0] and 2.0 * p > reach > 1.0 * p   # rounded up, affordable
    units, _ = _rule(P.bold(), [1e6], [p], terms=stock, floor=0.0, target=3_000_000.0, take_profit=tp, stop=0.5)
    a = costs.afford(1e6, 0.0, p, terms=stock, on=_D, mult=1.0, sizing="floor_safe", stop=0.5)
    assert units.tolist() == [14.0] and float(costs.floor_units(a, p, 1.0)) == 14.0   # cut to the affordable stake
    units, _ = _rule(P.bold(), [42_000.0], [5e7], target=50_000.0, take_profit=tp, stop=0.5)
    reach_btc = 8_000.0 / costs.net_win_coefficient(_t("btc"), 5e7, _D, tp, 1.0)
    assert units[0] == 16_049 * 1e-8 and units[0] * 5e7 >= reach_btc > (16_049 - 1) * 1e-8 * 5e7
    fee = dataclasses.replace(_t("btc"), phi_buy=300.0, phi_sell=500.0)
    for mult, lots in ((1.0, 17_653), (2.0, 19_316)):        # (8,000 + mult x (300 + 500)) / (1 - 0.003 mult), up
        units, _ = _rule(P.bold(), [42_000.0], [5e7], terms=fee, target=50_000.0, take_profit=tp, stop=0.5,
                         mult=mult)
        assert units.tolist() == [lots * 1e-8], (mult, units)
    units, at_floor = _rule(P.bold(), [42_000.0], [5e7], target=43_000.0, take_profit=tp, stop=0.5)
    assert units.tolist() == [10_000 * 1e-8] and not at_floor[0]      # a reach of 1,003 is raised to the KRW 5,000
    etf = _t("etf")                                                   # buy at 2,000 (13.9 bp) > sell at 3,000 (9.7)
    c_etf = costs.net_win_coefficient(etf, 2_000.0, _D, 0.5, 2.0)
    assert c_etf == 0.5 - costs.side_bp(etf, 2_000.0, _D, side="buy") * 1e-4 * 2.0 * 2.5
    units, _ = _rule(P.bold(), [1e6], [2_000.0], terms=etf, floor=0.0, target=1_100_000.0, take_profit=0.5, stop=0.5,
                     mult=2.0)
    assert units.tolist() == [102.0] and 101 * 2_000.0 < 100_000.0 / c_etf <= 102 * 2_000.0   # the buy side's kw
    units, at_floor = _rule(P.bold(), [1e6], [p], terms=stock, floor=0.0, target=1_100_000.0, take_profit=0.005,
                            stop=0.5)
    assert units.tolist() == [0.0] and not at_floor[0]                       # net win coefficient <= 0: no bet
    units, _ = _rule(P.bold(), [1e6], [p], terms=stock, floor=0.0, target=900_000.0, take_profit=tp, stop=0.5)
    assert units.tolist() == [0.0]                                           # cash already at the target


def test_first_stake():
    ctx = F.ctx()
    assert ctx.owner.limits["total_loss_floor_krw"] == 21_000.0 and ctx.owner.caps["okx_equity_share"] == 0.10
    btc, okx = _t("btc"), _t("okx")
    stake = costs.first_stake(_plan(), btc, ctx, 5e7, _D)
    assert type(stake) is float and abs(stake - 20_979.0) < 1e-6
    assert costs.first_stake(_plan(stake=25_000.0), btc, ctx, 5e7, _D) == 0.0          # at_floor: STUCK_AT_START
    assert costs.first_stake(_plan(fraction=P.fixed(0.1)), btc, ctx, 5e7, _D) == 0.0   # below the minimum
    capped = costs.first_stake(_plan("okx"), okx, ctx, 1.4e8, _D)
    assert abs(capped - 4_200.0) < 1e-6 and capped <= 4_200.0 + 1e-6                   # 0.10 x 42,000
    for caps in ({}, {"okx_equity_share": 1.5}, {"okx_equity_share": True}, {"okx_equity_share": "0.10"},
                 {"okx_equity_share": 0.0}, {"okx_equity_share": 10**400}):         # 10**400: no OverflowError
        unset = F.ctx(owner=dataclasses.replace(ctx.owner, caps=caps))
        assert costs.first_stake(_plan("okx"), okx, unset, 1.4e8, _D) == 0.0, caps        # .get: never a KeyError
    for cap in (1.0, 1):                                                   # gate._cap's (0, 1], an int 1 included
        full = F.ctx(owner=dataclasses.replace(ctx.owner, caps={"okx_equity_share": cap}))
        assert abs(costs.first_stake(_plan("okx"), okx, full, 1.4e8, _D) - 20_979.0) < 1e-6, cap
    stop_based = _plan(bracket=P.Bracket(take_profit=0.05, stop=0.1), sizing="stop_based")
    assert abs(costs.first_stake(stop_based, btc, ctx, 5e7, _D) - 41_958.0) < 1e-6   # 42,000 / 1.001: stop not binding
    replay = _terms("upbit", "BTC", fee_extras=None, replay=True)
    plan = _plan(fraction=P.kelly(0.5), edge_source=P.REPLAY_SOURCE)
    assert abs(costs.first_stake(plan, replay, ctx, 5e7, _D, fstar=1.0) - 21_000.0) < 1e-6   # mult 0: s <= W - L


def test_cost_refusal_names_4kappa_and_bold():
    etf, btc = _t("etf"), _t("btc")
    fixed = _plan("kis", "069500")
    assert costs.cost_refusal(fixed, etf, 2.0, _D) == "4kappa"              # 2,501.4 bp: 4 kappa >= 1
    assert costs.cost_refusal(fixed, etf, 3.0, _D) is None
    stock = _t("stock")                          # at 2.01 KRW, 4 kappa is 0.9956 on the buy side, 1.0036 on the sell
    assert 4.0 * costs.side_bp(stock, 2.01, _D, side="buy") * 1e-4 < 1.0
    assert costs.cost_refusal(_plan("kis", "005930"), stock, 2.01, _D) == "4kappa"
    bracket = P.Bracket(take_profit=0.003, stop=0.5)
    for tp, want in ((0.002, "bold"), (0.003, "bold"), (0.5, None)):
        plan = _plan(fraction=P.bold(), bracket=dataclasses.replace(bracket, take_profit=tp))
        assert costs.cost_refusal(plan, btc, 5e7, _D) == want, tp
    base, stress = (costs.net_win_coefficient(btc, 5e7, _D, 0.003, m) for m in (1.0, 2.0))
    assert base > 0.0 >= stress                                            # 0.000997 and -0.001006
    for terms, p0, tp in ((etf, 1_990.0, 0.01), (stock, 100.0, 0.5)):   # the sell side at p0 (1 + tp) is dearer
        sell = costs.side_bp(terms, p0 * (1.0 + tp), _D, side="sell")
        assert sell > costs.side_bp(terms, p0, _D, side="buy"), (terms.book, sell)
        assert costs.net_win_coefficient(terms, p0, _D, tp, 1.0) == tp - sell * 1e-4 * (2.0 + tp), terms.book
    assert costs.cost_refusal(_plan(fraction=P.fixed(1.0), bracket=bracket), btc, 5e7, _D) is None   # bold only
    assert costs.cost_refusal(_plan("kis", "069500", fraction=P.bold(), bracket=bracket), etf, 2.0, _D) == "4kappa"


def test_why_the_ceiling_rests_on_the_gross_mark():
    """Q32: a KRX ETF unit at 2,001 moving to 1,999 or 2,003 with probability 1/2 each keeps E[p] = p, while its
    liquidation value (p less one sell charge) rises in expectation by 1.00 KRW, because the tick, and so the
    rate, falls below 2,000. So the ceiling's proof uses the gross mark cash + units x p, never V."""
    etf = _t("etf")

    def value(p):
        return p - p * costs.side_bp(etf, p, _D, side="sell") * 1e-4

    assert (1_999.0 + 2_003.0) / 2 == 2_001.0
    expected = (value(1_999.0) + value(2_003.0)) / 2
    assert f"{value(2_001.0):,.2f}" == "1,998.22" and f"{expected:,.2f}" == "1,999.22"
    assert f"{expected - value(2_001.0):.2f}" == "1.00"
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_costs/
```

  Expected: a traceback, then

```
FAIL odds_costs/import ImportError: cannot import name 'costs' from 'core.odds' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\odds\__init__.py)

0/1 passed, 1 failed, 0 not run
```

  and exit code 1.

- [ ] **Step 3: Implement**

  Create `core/odds/costs.py` (whole file, LF). It imports only `math`, `dataclasses`, `datetime.date`, `numpy`,
  `core.compliance.rules` (annotations) and `core.odds.plan` (both module files, so no package re-export), reads no
  clock and opens no file:

```python
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
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_costs/
```

  Expected: these 23 lines, then `23/23 passed, 0 failed, 0 not run` (exit code 0; about 1.5 s of test time, inside
  the 2 s budget of CONTRACT 3.4):

```
PASS odds_costs/test_a_stake_below_the_minimum_is_no_bet_and_an_unaffordable_one_is_at_floor
PASS odds_costs/test_afford_bounds_hold_under_both_scenarios_plus_the_carry
PASS odds_costs/test_band_at_the_etf_reference_2005_is_1404_to_2605
PASS odds_costs/test_band_contains_the_reference_on_random_inputs
PASS odds_costs/test_band_keeps_the_price_inside_across_sessions
PASS odds_costs/test_bold_rounds_its_reaching_stake_up_when_affordable_and_cuts_it_otherwise
PASS odds_costs/test_carry_multiplier_equals_orders_by_ast
PASS odds_costs/test_check_validity_copies_the_original_dates
PASS odds_costs/test_copied_constants_equal_the_originals
PASS odds_costs/test_cost_refusal_names_4kappa_and_bold
PASS odds_costs/test_etf_fill_at_2005_costs_at_least_13_8_bp
PASS odds_costs/test_etf_rate_equals_cost_per_side
PASS odds_costs/test_first_stake
PASS odds_costs/test_kappa_bound_equals_the_brute_force_maximum
PASS odds_costs/test_kappa_equals_side_bp_element_by_element
PASS odds_costs/test_krx_stock_floor_equals_cost_per_side_with_the_ladder_swapped_in
PASS odds_costs/test_lot_rounding_down_and_up
PASS odds_costs/test_no_separate_sell_tax_on_top
PASS odds_costs/test_replay_terms_need_only_the_lot_and_the_minimum
PASS odds_costs/test_terms_from_the_fixture_venues
PASS odds_costs/test_terms_refuse_a_missing_value_and_accept_explicit_zeros
PASS odds_costs/test_us_and_crypto_pay_the_table_rate_with_no_floor_until_a_ladder_is_signed
PASS odds_costs/test_why_the_ceiling_rests_on_the_gross_mark
```

  Overlap check, then the odds-own guards, which now scan `core/odds/costs.py` (the O1 allowlist, no clock, no
  `__main__`, no file I/O, no package re-export, a flat package):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/
```

  Expected, ending: `0 failed` with the passed count Task 1 recorded under "Runs" (exit code 0). A failure names
  the offending file and text: fix `costs.py`, never the guard.

  Overlap check, then the compliance guards (raw words, forbidden and dynamic imports over `core/odds`) and the
  store (`test_code_files_is_the_import_closure` now finds `core/odds/costs.py` in the closure; it imports only
  closure files and numpy, which is never hashed):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected: each ends `0 failed` with the count the last earlier task recorded under "Runs" (exit code 0).

  Overlap check, then the core-wide scans (Global Constraints: every task that changes `core/`), one at a time:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
```

  Expected: each prints no FAIL line and ends with `0 failed` and exit code 0, with the passed and not-run counts
  Task 1 recorded.

  Overlap check, then the cockpit suite (test_08, test_09, test_16, test_18), followed by restoring the tracked
  results file:

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: the run ends with `0 failed` and the counts Task 1 recorded.

  Then the raw-text and line-ending checks. The greps and `git status` run no Python; the line-ending check does,
  so it carries the Git Bash overlap prefix:

```bash
git grep --untracked -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|/uapi/|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only" -- core/odds/costs.py
git grep --untracked -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|0\.4 *[*x×]|open\(|\.read_|\.write_|datetime\.(now|utcnow|today)|date\.today|time\.|__main__|__import__|import_module|exec|eval|compile|import os|import io|pathlib" -- core/odds/costs.py
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "import sys; bad = [f for f in ('core/odds/costs.py', 'tests/odds_costs.py') if b'\r' in open(f, 'rb').read() or open(f, 'rb').read(3) == b'\xef\xbb\xbf']; print(bad or 'LF ok'); sys.exit(1 if bad else 0)"
git status --short
```

  Expected: both greps print nothing (exit code 1); the line-ending check prints `LF ok` (no output and exit code 1:
  the overlap check found a QUANTGEN run; wait and re-run that line); `git status --short` lists
  exactly `?? core/odds/costs.py`, `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` and
  `?? tests/odds_costs.py`.

  Append the tail of each run above, one line each, under "Runs" in the execution ledger (LF; it stays untracked).

- [ ] **Step 5: Commit**

```bash
git add core/odds/costs.py tests/odds_costs.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are new and LF). Then:

```bash
git commit -m "feat(odds): costs, venue terms, bands, affordability and stakes" -m "Odds plan Task 6 (Q11, Q27, Q28, Q41; R2-1, R2-2, R2-5): core/odds/costs.py copies the cost table, tick floor, ETF ticks and KRX stock sell tax with equality tests in tests/odds_costs.py, and adds the venue terms, bands, affordability rules and stakes." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Afterwards `git status --short` prints only `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
