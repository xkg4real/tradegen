"""Sprint 8 package C tests: the Macro -> Model cards and Research register views, and the page hardening
(Strategy Lab card loader, Quant Lab caption and grading strip, Signals notice).

Renderers are walked without a page: a fake page runs threads inline; assertions read `ft.Text` values, chip
tags (`data`) and DataTable rows. Hermetic: reads the repository and temp directories only; nothing is written
under `~/.nextgen`, nothing is opened in a browser (the open buttons are inspected, never clicked).
"""
from __future__ import annotations

import json
import shutil
import tempfile
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import flet as ft

from core.quant import cards as K
from core.theme import active
from ui import components as C
from ui import macro_cards_view as MV
from ui import research_view as RV

ROOT = Path(__file__).resolve().parents[1]
FAKE = SimpleNamespace(run_thread=lambda fn, *a, **k: fn(*a, **k), update=lambda: None)
VERDICT_WORDS = {label for label, _ in C.VERDICT_STYLE.values()} | {"verdict invalid"}


def walk(c):
    yield c
    for attr in ("controls", "rows", "cells", "columns"):
        for child in getattr(c, attr, None) or []:
            yield from walk(child)
    for attr in ("content", "title", "label"):
        child = getattr(c, attr, None)
        if child is not None and not isinstance(child, str):
            yield from walk(child)


def everything(blocks):
    return [x for b in blocks for x in walk(b)]


def texts(blocks) -> list[str]:
    return [t.value for t in everything(blocks) if isinstance(t, ft.Text) and t.value]


def chip_text(c) -> str:
    return c.content.value


def tagged(blocks, tag: str) -> list:
    return [x for x in everything(blocks) if getattr(x, "data", None) == tag]


def by_card(blocks) -> dict:
    return {x.data[5:]: x for x in everything(blocks) if str(getattr(x, "data", "")).startswith("card:")}


def table_with(blocks, first_cols: tuple) -> ft.DataTable:
    for t in everything(blocks):
        if isinstance(t, ft.DataTable) and tuple(c.label.value for c in t.columns[:len(first_cols)]) == first_cols:
            return t
    raise AssertionError(f"no table with columns {first_cols}")


@contextmanager
def tmp_dirs():
    d = Path(tempfile.mkdtemp(prefix="qg_ui_"))
    try:
        (d / "root" / "cards").mkdir(parents=True)
        (d / "root" / "cards" / "verdicts.jsonl").write_bytes(b"")       # an empty verdicts file
        (d / "macro").mkdir()
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def render_cards(inputs: dict, **override) -> list:
    d = {**inputs, **override}
    return MV.cards_blocks(d["cards"], d["verdicts"], d["gate_status"], d["headers"], techfund=d["techfund"],
                           cry1=d["cry1"])


# --------------------------------------------------------------------------- #
# Model cards view
# --------------------------------------------------------------------------- #
def test_cards_view_registry_and_empty_verdicts_every_card_not_run_with_a_reason_gate_not_frozen():
    with tmp_dirs() as d:
        inputs = MV.load_inputs(macro_dir=d / "macro", cards_root=d / "root")
    assert inputs["verdicts"] == [] and inputs["gate_status"]["status"] == "NOT_FROZEN"
    blocks = render_cards(inputs)
    found = texts(blocks)
    assert "gate package NOT_FROZEN" in found
    reasons = [t for t in found if t.startswith("• NOT_FROZEN")]
    assert len(reasons) == 3 and any("anchor UNVERSIONED" in r for r in reasons), reasons
    rows = by_card(blocks)
    for spec in K.REGISTRY:
        row = rows[spec.card_id]
        words = [chip_text(v) for v in tagged([row], "verdict")]
        row_texts = texts([row])
        if spec.card_id == "MACRO-R06-US":
            assert words == ["REJECT"] and spec.label in row_texts
            assert any(r.startswith("Reason: registered card") for r in row_texts)
            continue
        assert words == ["NOT RUN"], (spec.card_id, words)
        assert "Reason: gate package NOT_FROZEN: no card runs before the freeze (P11)" in row_texts, spec.card_id
        assert f"instrument book: {spec.instrument_book}" in row_texts
        if spec.label:
            assert spec.label in row_texts, spec.card_id                  # verbatim
        if spec.notional_ref:
            assert "notional: null (owner input)" in row_texts, spec.card_id
    reg = tagged(blocks, "registered")
    assert len(reg) == 1 and "MACRO-R06-US" in texts(reg)


def test_forward_sim_and_refusal_groups_are_not_a_recommendation_and_never_success():
    with tmp_dirs() as d:
        blocks = render_cards(MV.load_inputs(macro_dir=d / "macro", cards_root=d / "root"))
    success = active().success
    want = {"forward_sim": {"MACRO-R28-US-TREND", "MACRO-R06-US-FUT"},
            "refusal": {"MACRO-R11-KR-KRW", "MACRO-R12-US-RATES"}}
    for key, ids in want.items():
        (group,) = tagged(blocks, key)
        assert set(by_card([group])) == ids, key
        found = texts([group])
        assert "not a recommendation" in found[0], found[0]
        for cid, row in by_card([group]).items():
            assert all("not a recommendation" in chip_text(c) for c in tagged([row], "disposition")), cid
        assert not [t for t in everything([group]) if isinstance(t, ft.Text) and t.color == success], key
    assert not ({"MACRO-R28-US-TREND", "MACRO-R06-US-FUT"} & set(by_card(tagged(blocks, "cards"))))


def test_build_as_insurance_is_a_disposition_chip_never_a_verdict_chip():
    with tmp_dirs() as d:
        inputs = MV.load_inputs(macro_dir=d / "macro", cards_root=d / "root")
    rows = [{"card_id": "MACRO-R06-KR-ETF", "revision": 2, "verdict": "PASS", "disposition": "BUILD_AS_INSURANCE"},
            {"card_id": "MACRO-R31-KR-ETF", "revision": 1, "verdict": "BUILD_AS_INSURANCE", "disposition": "INVARIANT_STEP"}]
    for verdicts in ([], rows):
        blocks = render_cards(inputs, verdicts=verdicts)
        words = [chip_text(c) for c in tagged(blocks, "verdict")]
        assert words and set(words) <= VERDICT_WORDS, set(words) - VERDICT_WORDS
        assert not any("INSURANCE" in w for w in words)
    kr = by_card(blocks)["MACRO-R06-KR-ETF"]
    assert [chip_text(c) for c in tagged([kr], "verdict")] == ["PASS"]
    assert [chip_text(c) for c in tagged([kr], "disposition")] == ["BUILD-AS-INSURANCE"]
    r31 = by_card(blocks)["MACRO-R31-KR-ETF"]
    assert [chip_text(c) for c in tagged([r31], "verdict")] == ["verdict invalid"]


def test_techfund_drafts_not_run_with_reasons_and_cry1_vendor_label():
    with tmp_dirs() as d:
        blocks = render_cards(MV.load_inputs(macro_dir=d / "macro", cards_root=d / "root"))
    (tf,) = tagged(blocks, "techfund")
    rows = by_card([tf])
    assert set(rows) == {"SCR-1", "SCR-2", "FS-1", "FS-2", "FS-3", "FS-4", "FS-5"}
    for cid, row in rows.items():
        assert [chip_text(c) for c in tagged([row], "verdict")] == ["NOT RUN"], cid
        assert any(t.startswith(("Reason: REFDATA", "Reason: PENDING")) for t in texts([row])), cid
    (cry,) = tagged(blocks, "cry1")
    label = "vendor data, labelled trial, not a formal card run"
    chips = [x for x in everything([cry]) if isinstance(x, ft.Container) and isinstance(x.content, ft.Text)
             and x.content.value == label]
    assert len(chips) == 4 and all(c.content.color == active().error for c in chips)
    assert any("upbit_KRW-BTC · c3_reproduction: PASS" in t for t in texts([cry]))


def test_cards_view_fails_closed_on_a_broken_chain_or_bad_inputs():
    bad = MV.cards_blocks(None, [], {}, [])
    assert len(bad) == 1 and "fail closed" in texts(bad)[0]
    with tmp_dirs() as d:
        (d / "root" / "cards" / "verdicts.jsonl").write_text('{"card_id": "X"}\n', encoding="utf-8")
        view = MV.view_shell(FAKE, lambda: MV.load_inputs(macro_dir=d / "macro", cards_root=d / "root"),
                             lambda x: render_cards(x))
    found = texts([view])
    assert any("chain broken" in t for t in found), found[:5]
    assert not any(t.startswith("gate package") for t in found)                     # no records shown


# --------------------------------------------------------------------------- #
# Research register view
# --------------------------------------------------------------------------- #
_RESEARCH = {}


def research():
    if not _RESEARCH:
        _RESEARCH.update(RV.load_inputs())
    return RV.research_blocks(_RESEARCH["tf"], _RESEARCH["backlog"], _RESEARCH["council"])


def test_research_weight_table_all_50_rows_korea_22_caption_verbatim():
    blocks = research()
    r3 = ROOT / "QUANTGEN_techfund_research_bundle" / "QUANTGEN_techfund_research" / "research_notes" / "R3_TF_neural_link.md"
    if r3.is_file():
        assert r3.read_text(encoding="utf-8").splitlines()[702] == RV.WEIGHT_CAPTION
    assert RV.WEIGHT_CAPTION in texts(blocks)
    market = next(x for x in everything(blocks) if isinstance(x, ft.Dropdown) and x.label == "Market")
    cols = ("Market", "Family", "Column", "Final", RV.W3_HEADER)
    assert len(table_with(blocks, cols).rows) == 50
    counts = Counter(r["market"] for r in _RESEARCH["tf"]["weights"])
    for m in ("Korea", "US", "Crypto", "Futures/FX"):
        market.value = m
        market.on_select(None)
        t = table_with(blocks, cols)
        assert len(t.rows) == counts[m] and {r.cells[0].content.value for r in t.rows} == {m}, m
    assert counts["Korea"] == 22
    market.value = "Other markets"
    market.on_select(None)
    assert any(isinstance(t, ft.DataTable) and len(t.rows) == 6 for t in everything(blocks))


def test_research_register_group_filter_table_and_detail():
    blocks = research()
    group = next(x for x in everything(blocks) if isinstance(x, ft.Dropdown) and x.label == "Group")
    cols = ("ID", "Item", "Market", "Decision")
    assert len(table_with(blocks, cols).rows) == 77
    want = {"BUILD": 9, "INVARIANT": 6, "GOVERNANCE": 14, "FORWARD-SIM": 5, "BACKLOG": 20, "OWNER DECISION": 3,
            "CONTEXT": 3, "DROP": 17}
    success = active().success
    for g, n in want.items():
        group.value = g
        group.on_select(None)
        t = table_with(blocks, cols)
        assert len(t.rows) == n, (g, len(t.rows))
        assert not [x for x in everything([t]) if isinstance(x, ft.Text) and x.color == success], g
        first = t.rows[0].cells[0].content.value
        assert any(s.startswith("What would change it:") for s in texts(blocks)) and first in texts(blocks)
    assert sum(want.values()) == 77


def test_research_dnb_37_plus_17_resolutions_12_and_open_buttons_point_at_files():
    blocks = research()
    macro = table_with(blocks, ("Item", "Label", "Refused"))
    tech = table_with(blocks, ("ID", "Label", "Refused"))
    assert len(macro.rows) == 37 and len(tech.rows) == 17
    assert all(r.cells[2].content.value != "—" for r in macro.rows)              # every spec title found
    assert {r.cells[0].content.value for r in tech.rows} == {f"DNB-TF-{i:02d}" for i in range(1, 18)}
    res = table_with(blocks, ("#", "Topic"))
    assert [r.cells[0].content.value for r in res.rows] == [str(i) for i in range(1, 13)]
    mods = table_with(blocks, ("ID", "Change"))
    assert len(mods.rows) == 35                                                  # 34 council modules + R-05
    buttons = {b.content: Path(b.data) for b in everything(blocks) if isinstance(b, ft.Button)}
    assert set(buttons) >= {"Open Quant Council page", "Open Macro Neural Link page"}
    for label in ("Open Quant Council page", "Open Macro Neural Link page"):
        assert buttons[label].is_file() and buttons[label].suffix == ".html", label
    readme = (ROOT / "docs" / "council" / "README.md").read_text(encoding="utf-8").splitlines()
    top = texts(blocks)[0]
    for line in readme[2:4]:
        assert line in top, line


def test_research_view_fails_closed_without_the_record():
    bad = RV.research_blocks({}, {}, {})
    assert len(bad) == 1 and "fail closed" in texts(bad)[0]


# --------------------------------------------------------------------------- #
# Page hardening
# --------------------------------------------------------------------------- #
def test_strategy_lab_builds_with_foreign_cards_in_a_temp_cards_dir():
    from ui import strategy_lab_page as S
    legacy = sorted((ROOT / "docs" / "asset_expansion" / "cards").glob("*.json"))[0]
    d = Path(tempfile.mkdtemp(prefix="qg_lab_"))
    saved = S.CARDS_DIR
    try:
        shutil.copy(legacy, d / legacy.name)
        foreign = {"macro.json": {"card_id": "MACRO-R06-KR-ETF", "class": "CARD-P", "verdict": "PASS", "claim": "c"},
                   "header.json": {"card_id": "HDR", "revision": 1},
                   "list.json": [1, 2],
                   "odd.json": {"card_id": "ODD", "decision": "PASS", "kind": "strategy", "hypothesis": "h",
                                "decision_reason": "r", "stats": {"sr_oos": 1.0, "dsr": "high", "pbo": None},
                                "tests": ["x"], "lines": "not a list", "citations": None}}
        for name, obj in foreign.items():
            (d / name).write_text(json.dumps(obj), encoding="utf-8")
        S.CARDS_DIR = d
        root = S.build_strategy_lab_page(FAKE)
        found = texts([root])
    finally:
        S.CARDS_DIR = saved
        shutil.rmtree(d, ignore_errors=True)
    assert any(t.startswith("v2 macro model cards (CARD-O / CARD-P) are under Macro → Model cards") for t in found)
    picker = next(x for x in walk(root) if isinstance(x, ft.Dropdown) and x.label == "Card")
    keys = {o.key for o in picker.options}
    assert {"MACRO-R06-KR-ETF", "HDR", "ODD"} <= keys and len(keys) == 4
    assert "MACRO-R06-KR-ETF — UNKNOWN" in {o.text for o in picker.options}       # a v2 PASS is not offered here


def test_signals_page_header_notice():
    from ui import signals_page as SP
    assert SP.SIGNALS_NOTICE == "Context only — not a v2 signal (DO-NOT-BUILD TF-12). Nothing here feeds a book."
    assert SP.SIGNALS_NOTICE in texts([SP.build_signals_page(FAKE)])


def test_quant_lab_fit_caption_and_grading_strip():
    from core.quant import lab
    from ui import quant_lab_page as Q
    assert "504" in Q.FIT_CAPTION and "not an R-16 graded fit" in Q.FIT_CAPTION
    assert Q._grade_blocks(None) == [] and Q._lab_grade("AAPL") is None and Q._lab_grade("../x") is None
    spy = Q._lab_grade("SPY")
    assert spy is not None and spy["gate"]["status"] == "FAIL"
    found = texts(Q._grade_blocks(spy))
    assert found[0] == Q.SMOKE_CHIP and found[1] == "M9 gate: FAIL"          # SMOKE leads, in red (rulings section 1)
    assert [t.split(":")[0] for t in found[2:7]] == ["Kupiec 99% VaR", "Christoffersen CC 99%", "ES 97.5% Z2",
                                                     "Basel last 250", "Fan PIT h21"]
    assert found[2].startswith("Kupiec 99% VaR: PASS") and found[5] == "Basel last 250: green"
    assert found[6].startswith("Fan PIT h21: FAIL")
    assert spy["label"] in found
    assert any("reported, not gated" in t for t in found) and any(t.startswith("• 1-day VaR") for t in found)
    # a SMOKE PASS on vendor data never reads as a gate pass: the one red chip is SMOKE, every other chip is muted
    kodex = Q._grade_blocks(Q._lab_grade("069500"))
    chips = [x for x in everything(kodex) if isinstance(x, ft.Container) and isinstance(x.content, ft.Text)]
    assert chip_text(chips[0]) == Q.SMOKE_CHIP and chips[0].content.color == active().error
    assert chip_text(chips[1]) == "M9 gate: PASS" and all(c.content.color == active().muted for c in chips[1:])
    g = lab.LabGrade("US", "fast_fhs", ("fast_fhs",), {}, {}, {}, {}, {}, "NOT_RUN", (),
                     gate={"status": "NOT_RUN", "lines": {k: None for k, _, _ in Q._GRADE_LINES}, "thresholds": {}})
    names = [n for _, _, n in Q._GRADE_LINES]
    assert texts(Q._grade_blocks(g)) == (["M9 gate: NOT RUN"] + [f"{n}: NOT RUN" for n in names[:3]]
                                         + ["Basel last 250: NOT RUN", f"{names[3]}: NOT RUN"])


def test_quant_lab_run_shows_caption_and_the_stored_grade():
    from ui import quant_lab_page as Q
    root = Q.build_quant_lab_page(FAKE)
    controls = list(walk(root))
    dd = {d.label: d for d in controls if isinstance(d, ft.Dropdown)}
    tf = {t.label: t for t in controls if isinstance(t, ft.TextField)}
    dd["Data source"].value, dd["Drift"].value, dd["Model"].value = "synthetic", "zero", "gbm"
    tf["Symbol"].value, tf["Paths"].value, tf["Horizon (sessions)"].value = "SPY", "300", "21"
    next(b for b in controls if isinstance(b, ft.Button)).on_click(None)
    found = texts([root])
    assert Q.FIT_CAPTION in found and "M9 gate: FAIL" in found, found[:8]


def test_new_ui_modules_pass_the_flet_api_guard():
    from tests import flet_api_guard
    for _name, fn in flet_api_guard.tests():
        fn()


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
