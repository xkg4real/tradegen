"""M0 package D — R-26 instrument book, tick floor and header checks (T-COST-02, T-COST-03, T-BOOK-01 header
clauses). Hermetic: inline headers, an inline store accessor, no files, no network."""
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import numpy as np

from core.quant import validate as V
from core.quant.instruments import (COMMISSION_BP, INSTRUMENT_BOOKS, CostLowered, NotTradable, check_cost_policy,
                                    cost_per_side, header_checks, owner_inputs, stress, stress_cost_line,
                                    tick_floor_bp, tick_size)

from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
TABLE = {"krx_etf": 3.0, "krx_stock": 35.0, "us": 50.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}
SLEEVES = {"sleeves.KR.notional_nav": 1.12e9, "sleeves.US.notional_nav": 1.04e9, "sleeves.FX.notional_nav": 2e9}
RULE_ACTIVE = {"rule_id": "R-03", "exposure_basis": "active", "applies_to": "momentum"}
RULE_TOTAL = {"rule_id": "R-06", "exposure_basis": "total", "applies_to": "market_gross"}


def _store_get(key):
    return SLEEVES.get(key)


def _header(**over) -> dict:
    h = {"rule_id": "R-03", "instrument_book": "KRX_ETF_line", "rebalance": "daily", "no_trade_band": 0.0,
         "notional_nav": {"ref": "sleeves.KR.notional_nav"}, "fill_model": "KRX_close_auction",
         "costs": {"per_side": "read_from_gate", "floor": "tick_floor", "stress": 2.0, "stress_line": "printed"},
         "printed_lines": ["exec_variants_ABC", "overnight_intraday", "turnover_by_regime", "stress_cost_line"]}
    h.update(over)
    return h


def _refusals(**over) -> list[str]:
    return header_checks(_header(**over), _store_get, rule=RULE_ACTIVE)


def _has(refusals: list[str], check: str) -> bool:
    return any(r.startswith(check + " ") for r in refusals)


# --------------------------------------------------------------------------- #
# T-COST-02
# --------------------------------------------------------------------------- #
def test_cost02_worked_examples():
    """252670 at ₩69 -> 73.86 bp (≥ 72); KODEX 200 at ₩112,060 -> 3 bp table; both exact to 0.01 bp."""
    q = cost_per_side("252670", 69.0, on=date(2026, 6, 1))
    assert q.bp >= 72.0 and abs(q.bp - 73.86) <= 0.01 and q.source == "tick_floor", q
    assert abs(q.floor_bp - (COMMISSION_BP + 0.5 * 1 / 69 * 1e4)) < 1e-9 and q.table_bp == 3.0
    k = cost_per_side("069500", 112060.0, on=date(2026, 6, 1))
    assert k.bp == 3.0 and k.source == "table" and abs(k.floor_bp - 1.62) <= 0.01, k
    assert abs(cost_per_side("252670", 62.0).bp - 82.0) <= 0.05 and abs(cost_per_side("252670", 579.0).bp - 10.0) <= 0.05
    assert cost_per_side("KRX_ETF_line").bp == 3.0 and cost_per_side("KRX_ETF_line").floor_bp is None
    assert tick_size("KRX_ETF", 1999.0) == 1.0 and tick_size("KRX_ETF", 2000.0) == 5.0
    assert abs(tick_floor_bp(69.0, 1.0) - 73.8638) < 1e-3


test_cost02_worked_examples.test_ids = ["T-COST-02"]


def test_cost02_floor_never_lowers():
    """applied ≥ table for seeded random prices and every class; the sell tax only adds; KRX_LI_ETF falls back to 3 bp."""
    rng = np.random.default_rng(11)
    for price in rng.uniform(50.0, 500000.0, 200):
        q = cost_per_side("252670", float(price))
        assert q.bp >= q.table_bp == 3.0 and q.bp >= q.floor_bp - 1e-12, q
        assert q.stress_bp == stress(q.bp) == 2.0 * q.bp
    for cls, bp in TABLE.items():
        assert V.cost_bp(cls) == bp
    assert V.cost_bp("KRX_LI_ETF") == 3.0 and "KRX_LI_ETF" not in V.COST_BP_PER_SIDE
    try:
        V.cost_bp("bogus")
        raise AssertionError("unknown class must raise")
    except KeyError:
        pass
    assert V.COST_BP_PER_SIDE == TABLE
    buy = tick_floor_bp(50000.0, 50.0)
    assert tick_floor_bp(50000.0, 50.0, tax_bp=20.0) == buy + 20.0


test_cost02_floor_never_lowers.test_ids = ["T-COST-02", "T-COST-03"]


def test_cost02_owner_inputs_fail_closed():
    """ETF date before 2023-12-11, a book without a tick table, a non-KRW book without nav_fx and a sell
    tax outside 2026 are refusals, never guesses."""
    for bad in ((("252670", 69.0), {"on": date(2023, 12, 10)}),
                (("KRX_stock_book", 70000.0), {}),
                (("CME_micro_ES", 5000.0), {}),
                (("KRX_stock_book", 70000.0), {"on": date(2025, 1, 2), "side": "sell"}),
                (("multi_line",), {}), (("NOPE",), {})):
        try:
            cost_per_side(*bad[0], **bad[1])
            raise AssertionError(f"expected NotTradable for {bad}")
        except NotTradable as exc:
            assert exc.status == "missing"
    assert "KRX ETF tick table before 2023-12-11 (KRX notices)" in owner_inputs()
    assert "mini_KOSPI200_futures.contract_multiplier" in owner_inputs()
    assert set(INSTRUMENT_BOOKS) == {"KRX_ETF_line", "KRX_stock_book", "KOSPI200_futures", "mini_KOSPI200_futures",
                                     "CME_micro_ES", "US_shares_KIS", "KRX_listed_SP500_ETF", "crypto_venue",
                                     "FX_KRX_USD_futures", "FX_broker_spot", "multi_line"}


test_cost02_owner_inputs_fail_closed.test_ids = ["T-COST-02"]


# --------------------------------------------------------------------------- #
# T-COST-03
# --------------------------------------------------------------------------- #
def test_cost03_lowering_refused():
    """A header that lowers a cost raises; a schedule may only raise; the stress line never lowers."""
    etf = INSTRUMENT_BOOKS["KRX_ETF_line"]
    for lowered in (_header(cost_bp=2.0),
                    _header(costs={"per_side": 2.5, "floor": "tick_floor", "stress": 2.0, "stress_line": "printed"}),
                    _header(instrument_book="KRX_stock_book", costs={**_header()["costs"], "schedule": [{"to": "2002-10-13", "cost_class": "krx_etf"}]}),
                    _header(costs={**_header()["costs"], "schedule": [{"cost_class": "krx_etf", "bp": 1.0}]}),
                    _header(costs={**_header()["costs"], "schedule": [{"cost_class": "cheap"}]})):
        try:
            check_cost_policy(lowered, INSTRUMENT_BOOKS[lowered["instrument_book"]])
            raise AssertionError(f"expected CostLowered for {lowered}")
        except CostLowered:
            pass
        assert _has(header_checks(lowered, _store_get, rule=RULE_ACTIVE), "10")
    check_cost_policy(_header(cost_bp=4.0), etf)                                              # raising is allowed
    check_cost_policy(_header(costs={**_header()["costs"], "schedule": [{"to": "2002-10-13", "cost_class": "futures"}]}), etf)
    assert not _has(_refusals(cost_bp=3.0), "10")
    rng = np.random.default_rng(11)
    for s20, smed in rng.uniform(0.05, 0.6, (100, 2)):
        assert stress_cost_line(3.0, s20, smed) >= 3.0
    assert stress_cost_line(3.0, 0.1, 0.1, etf_close_fill=True, abs_ret=0.03) == 13.0
    assert stress_cost_line(3.0, 1.0, 0.1) == 15.0


test_cost03_lowering_refused.test_ids = ["T-COST-03"]


def test_cost02_every_result_at_2x():
    """The quote carries the 2× line for every class (P10 table); a header without the 2× line is refused."""
    for cls, bp in TABLE.items():
        book = next(b for b in INSTRUMENT_BOOKS if INSTRUMENT_BOOKS[b].cost_class == cls)
        q = cost_per_side(book)
        assert (q.bp, q.stress_bp) == (bp, 2 * bp), (cls, q)
    base = _header()["costs"]
    for costs in ({k: v for k, v in base.items() if k != "stress"}, {**base, "stress": 1.0},
                  {k: v for k, v in base.items() if k != "stress_line"}, {**base, "stress_line": "gated"}):
        assert _has(_refusals(costs=costs), "11"), costs
    assert not _has(_refusals(), "11")
    saved = V.GATE["cost_stress"]
    try:
        V.GATE["cost_stress"] = 3.0
        assert stress(3.0) == 9.0 and _has(_refusals(), "11")      # the helper and the check read the gate, not a copy
    finally:
        V.GATE["cost_stress"] = saved


test_cost02_every_result_at_2x.test_ids = ["T-COST-02"]


# --------------------------------------------------------------------------- #
# T-BOOK-01 (header clauses)
# --------------------------------------------------------------------------- #
def test_book01_required_fields():
    """Every header declares instrument book, notional NAV, rebalance rule and no-trade band (and the fill
    model); missing or null -> a refusal that names the field. A complete header is clean."""
    assert _refusals() == []
    for field in ("instrument_book", "rebalance", "no_trade_band", "notional_nav", "fill_model"):
        h = _header()
        del h[field]
        out = header_checks(h, _store_get, rule=RULE_ACTIVE)
        assert any(r.startswith("1 required") and field in r for r in out), (field, out)
        out = header_checks(_header(**{field: None}), _store_get, rule=RULE_ACTIVE)
        assert any(r.startswith("1 required") and field in r for r in out), (field, out)
    assert _has(_refusals(instrument_book="KRX_option_book"), "1")
    assert _has(_refusals(rebalance="quarterly"), "3")
    assert _has(_refusals(printed_lines=["overnight_intraday"]), "7")
    assert not _has(_refusals(printed_lines=None, costs={**_header()["costs"], "printed_lines": ["exec_variants_ABC"]}), "7")
    assert _has(_refusals(costs={"per_side": "5bp", "floor": "tick_floor", "stress": 2.0, "stress_line": "printed"}), "5")
    assert _has(header_checks(_header(), _store_get), "8")        # no rule object reachable: fail closed


test_book01_required_fields.test_ids = ["T-BOOK-01"]


def test_book01_notional_from_sleeve():
    """notional_nav comes from sleeves.<market>.notional_nav via {ref}; a differing literal, a wrong ref, a null
    sleeve and a non-positive value are refused."""
    assert _refusals(notional_nav=1.12e9) == []
    assert _has(_refusals(notional_nav=1.0e9), "2")
    assert _has(_refusals(notional_nav=0), "2") and _has(_refusals(notional_nav=-5), "2")
    assert _has(_refusals(notional_nav={"ref": "sleeves.US.notional_nav"}), "2")      # the KR book reads the KR sleeve
    assert _has(_refusals(notional_nav={"ref": "cards.R-03.notional"}), "2")
    assert _has(_refusals(notional_nav={"ref": "sleeves.KR.notional_nav", "x": 1}), "2")
    out = header_checks(_header(), lambda k: None, rule=RULE_ACTIVE)
    assert any(r.startswith("2 ") and "owner input" in r for r in out), out
    out = header_checks(_header(), lambda k: "1.12e9", rule=RULE_ACTIVE)
    assert _has(out, "2")


test_book01_notional_from_sleeve.test_ids = ["T-BOOK-01"]


def test_book01_granularity_floor():
    """One contract ≤ 5 % of the sleeve notional, exactly 5 % allowed; mini K200 (₩56m) refused on ₩0.1bn."""
    fut = dict(instrument_book="mini_KOSPI200_futures", roll_calendar={"rule": "roll_before_expiry"})
    assert _refusals(**fut) == []                                                        # 56e6 <= 0.05 * 1.12e9
    out = header_checks(_header(**fut), lambda k: 1e8, rule=RULE_ACTIVE)
    assert any(r.startswith("6 granularity") and "56,000,000" in r for r in out), out
    assert _has(header_checks(_header(**fut), lambda k: 1.1e9, rule=RULE_ACTIVE), "6")
    assert not _has(header_checks(_header(**fut), lambda k: 1.12e9 + 1, rule=RULE_ACTIVE), "6")
    k200 = dict(fut, instrument_book="KOSPI200_futures")
    assert not _has(header_checks(_header(**k200), lambda k: 5.6e9, rule=RULE_ACTIVE), "6")
    assert _has(header_checks(_header(**k200), lambda k: 5.6e9 - 1, rule=RULE_ACTIVE), "6")
    es = dict(fut, instrument_book="CME_micro_ES", notional_nav={"ref": "sleeves.US.notional_nav"},
              nav_fx={"series": "USDKRW_1530_SNAPSHOT", "history": "ECOS_1530_CLOSE", "role": "forward_sim"})
    assert _refusals(**es) == []                                                         # 52e6 <= 0.05 * 1.04e9
    assert _has(header_checks(_header(**es), lambda k: 1.0e9, rule=RULE_ACTIVE), "6")
    assert _has(header_checks(_header(**es), _store_get, rule=RULE_ACTIVE, contract_notional_krw=52.1e6), "6")
    assert _has(_refusals(instrument_book="mini_KOSPI200_futures"), "6")                  # roll_calendar missing
    fx = dict(fut, instrument_book="FX_KRX_USD_futures", notional_nav={"ref": "sleeves.FX.notional_nav"})
    assert any("owner input" in r and r.startswith("6 ") for r in _refusals(**fx))        # multiplier unknown
    assert not _has(header_checks(_header(**fx), _store_get, rule=RULE_ACTIVE, contract_notional_krw=1e8), "6")


test_book01_granularity_floor.test_ids = ["T-BOOK-01"]


def test_book01_stock_book_scalar_band_navfx_multi():
    """A stock book (KRX or US shares) as a market-gross scalar is refused; the 0.10 band only on stock books;
    non-KRW books need nav_fx with the book's role; multi_line declares one line per market."""
    stock = dict(instrument_book="KRX_stock_book", no_trade_band=0.10)
    assert header_checks(_header(**stock), _store_get, rule=RULE_ACTIVE) == []
    assert _has(header_checks(_header(**stock), _store_get, rule=RULE_TOTAL), "8")
    assert _has(header_checks(_header(**stock), _store_get, rule={"applies_to": "market_gross"}), "8")
    us = dict(instrument_book="US_shares_KIS", notional_nav={"ref": "sleeves.US.notional_nav"},
              nav_fx={"series": "USDKRW_1530_SNAPSHOT", "role": "acting_exposure"})
    assert _has(header_checks(_header(**us), _store_get, rule=RULE_TOTAL), "8")
    assert header_checks(_header(**us), _store_get, rule=RULE_ACTIVE) == []
    assert not _has(header_checks(_header(), _store_get, rule=RULE_TOTAL), "8")          # the ETF line may carry vt
    assert _has(_refusals(no_trade_band=0.10), "4") and _has(_refusals(no_trade_band=0.05), "4")
    assert _has(_refusals(no_trade_band=True), "4")
    assert _has(_refusals(**dict(us, nav_fx=None)), "9")
    assert _has(_refusals(**dict(us, nav_fx={"series": "USDKRW_1530_SNAPSHOT", "role": "context"})), "9")
    assert _has(_refusals(**dict(us, nav_fx={"role": "acting_exposure"})), "9")
    multi = dict(instrument_book="multi_line", notional_nav={"ref": "sleeves.KR.notional_nav"},
                 instrument_lines=[{"market": "KR", "instrument_book": "KRX_ETF_line"},
                                   {"market": "US", "instrument_book": "CME_micro_ES"}],
                 nav_fx={"series": "USDKRW_1530_SNAPSHOT", "role": "acting_exposure"})
    assert _refusals(**multi) == []
    assert _has(_refusals(**dict(multi, nav_fx=None)), "9")
    assert _has(_refusals(**dict(multi, instrument_lines=None)), "12")
    assert _has(_refusals(**dict(multi, instrument_lines=multi["instrument_lines"] * 2)), "12")
    assert _has(_refusals(**dict(multi, instrument_lines=[{"market": "KR", "instrument_book": "multi_line"}])), "12")
    assert _has(_refusals(**dict(multi, notional_nav=1.12e9)), "2")
    assert _has(_refusals(**dict(multi, notional_nav={"ref": "sleeves.FX.notional_nav"})), "2")
    assert _has(_refusals(instrument_lines=multi["instrument_lines"]), "12")
    lines = [{"market": "KR", "instrument_book": "KRX_stock_book"}]
    assert _has(header_checks(_header(**dict(multi, instrument_lines=lines, nav_fx=None)), _store_get, rule=RULE_TOTAL), "8")


test_book01_stock_book_scalar_band_navfx_multi.test_ids = ["T-BOOK-01"]


def test_book01_real_sleeve_notional_is_owner_input():
    """The shipped store holds sleeves.KR/US.notional_nav = null until the owner signs them (before the M7 commit)."""
    raise NotRun("OWNER: sleeves.<market>.notional_nav is null in the shipped store; the real commit check cannot run")


test_book01_real_sleeve_notional_is_owner_input.test_ids = ["T-BOOK-01"]


# --------------------------------------------------------------------------- #
# Single source: the study reads the gate's table
# --------------------------------------------------------------------------- #
def test_study_reads_the_gate_cost_table():
    """docs/asset_expansion_study.py still sees the same six numbers, now from core.quant.validate."""
    spec = importlib.util.spec_from_file_location("asset_expansion_study", ROOT / "docs" / "asset_expansion_study.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.COST == TABLE and mod.COST is V.COST_BP_PER_SIDE
    src = (ROOT / "docs" / "asset_expansion_study.py").read_text(encoding="utf-8")
    assert src.count('"krx_etf": 3.0') == 0, "the study must not keep a second copy of the table"


test_study_reads_the_gate_cost_table.test_ids = ["T-COST-03"]


def tests():
    return [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
