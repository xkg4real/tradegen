"""M0 integration: `validate_card_header` wires the schema layer (core.ficc.macro_schema), the R-26 checks
(core.quant.instruments) and the section 10.3 predicates (core.rules.macro_rules) into one commit-time report
(T-BOOK-01 header clauses; T-OWNER-01 "checked only at commit"). Hermetic: a temporary store copy carries the
sleeve notional, nothing else is written.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core.ficc import macro_schema as S
from core.rules import macro_rules as M
from core.rules.macro_rules import RuleInput, RuleObject
from tests.macro_m0_schemas import filled

SLEEVE = 1.12e9


def _store(tmp: Path, sleeve=SLEEVE) -> M.MacroStore:
    doc = json.loads(M.SHIPPED_STORE_PATH.read_text(encoding="utf-8"))
    doc["sleeves"]["KR"]["notional_nav"] = sleeve                # the owner input, signed for this test only
    path = tmp / "rules.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return M.load_store(path)


def _rule(**over) -> RuleObject:
    base = dict(rule_id="R-06-KR-VT20", kind="CARD-P", output_range=(0.0, 1.0), exposure_basis="total",
                applies_to="market_gross", composition="min", books=("specification",),
                inputs=(RuleInput("KOSPI_OFFICIAL_CLOSE", "acting_exposure", ("specification",), "publication", "market_price"),),
                estimator={"name": "sma20", "kind": "sma"}, label_layer="none", instrument_book="KRX_ETF_line",
                market="KR", card_id="MACRO-R06-KR-ETF", tier="A", n_rule=M.N_GATE, factor="vt")
    base.update(over)
    return RuleObject(**base)


def _header(**over) -> dict:
    h = dict(filled()["model_card_header"])
    h["notional_nav"] = SLEEVE
    h["printed_lines"] = [*h["printed_lines"], "exec_variants_ABC", "overnight_intraday"]   # R-26 rule 6 (check 7)
    h.update(over)
    h["header_md5"] = S.header_md5(h)
    return h


def _fields(report, needle: str) -> list[str]:
    return [i.field for i in report.errors if needle in i.message]


def test_validate_card_header_wires_schema_instruments_and_dnb():
    with tempfile.TemporaryDirectory() as tmp:
        store = _store(Path(tmp))
        clean = M.validate_card_header(_header(), store, rule=_rule())
        assert clean.ok, [i.message for i in clean.errors]
        # schema layer (H4): a header whose md5 is not its own, or not the committed one
        r = M.validate_card_header({**_header(), "header_md5": "0" * 32}, store, rule=_rule())
        assert _fields(r, "H4") == ["header_md5"]
        assert _fields(M.validate_card_header(_header(), store, rule=_rule(), committed_md5="0" * 32), "H4")
        # store layer: gate.card_header_required and owner_decisions at commit (T-OWNER-01 clause)
        r = M.validate_card_header(_header(cash_convention=None), store, rule=_rule())
        assert "cash_convention" in _fields(r, "gate.card_header_required")
        r = M.validate_card_header(_header(owner_decisions={"risk_layer.korea_caps.template": "pair_35"}), store, rule=_rule())
        assert _fields(r, "at commit") == ["owner_decisions"]
        # instruments layer: the twelve R-26 checks run with the store's sleeves and the rule's basis
        r = M.validate_card_header(_header(notional_nav=1.0e9), store, rule=_rule())
        assert "notional_nav" in _fields(r, "differs from sleeves.KR.notional_nav")
        r = M.validate_card_header(_header(instrument_book="KRX_stock_book"), store, rule=_rule(instrument_book="KRX_stock_book"))
        assert _fields(r, "DNB 33") and _fields(r, "[krx_stock_book_on_market_gross_scalar]")   # check 8 and item 33
        assert _fields(M.validate_card_header(_header(), store, rule=None), "rule object")         # no rule: fail closed
        assert _fields(M.validate_card_header(_header(), store, rule={"rule_id": "R-06-KR-VT20"}), "incomplete")
        # dnb layer: a header edit after results_md5 under the same card id (items 23/32)
        prev = M.rule_of_header(_rule(results_md5="a" * 32), _header())
        assert prev.extras["rebalance"] == "daily" and prev.extras["notional_nav"] == SLEEVE and prev.tier == "A"
        r = M.validate_card_header(_header(rebalance="weekly"), store, rule=_rule(), previous=prev)
        assert _fields(r, "[header_edit_after_results_md5]") == ["card_id"]
        assert M.validate_card_header(_header(), store, rule=_rule(), previous=prev).ok
    # the shipped store: the sleeve notional is an owner input, so a commit is refused, never guessed
    r = M.validate_card_header(_header(), M.load_store(), rule=_rule())
    assert _fields(r, "owner input") == ["notional_nav"] and not r.ok


test_validate_card_header_wires_schema_instruments_and_dnb.test_ids = ["T-BOOK-01", "T-OWNER-01"]


def tests():
    return [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
