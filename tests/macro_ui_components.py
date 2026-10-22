"""Sprint 8 package A: the warning token, the shared v2 components, the shell fixes and the README (02_ui_design 3, 5).

Renderers are built without a page and checked by walking the control tree for `ft.Text` values, as the
Quant Lab self-check does. Nothing here opens a file, starts a thread or touches the network.
"""
from __future__ import annotations

import ast
from pathlib import Path

import flet as ft

from core import theme
from ui import components as C

ROOT = Path(__file__).resolve().parents[1]
DISCLAIMERS = ("All panel members in these documents are simulated, fictional composites; nothing speaks for any real "
               "firm or person.", "Not investment advice: QUANTGEN is a read-only research desk with no order path.")


def walk(c):
    """Every control under `c` (controls / rows / cells / columns / content / label)."""
    if c is None:
        return
    yield c
    for attr in ("controls", "rows", "cells", "columns"):
        for child in getattr(c, attr, None) or ():
            yield from walk(child)
    for attr in ("content", "label"):
        child = getattr(c, attr, None)
        if isinstance(child, ft.Control):
            yield from walk(child)


def texts(c) -> list[str]:
    return [t.value for t in walk(c) if isinstance(t, ft.Text) and t.value]


def test_warning_token_is_last_with_a_default_and_in_both_palettes():
    names = theme.token_names()
    assert names[-1] == "warning" and "warning" in names
    assert theme.DARK.warning == "#d9a441" and theme.LIGHT.warning == "#8a5a00"
    legacy = theme.Palette(*[getattr(theme.DARK, n) for n in names[:-1]])     # the 11-field positional form still builds
    assert legacy.warning == "#d9a441"


def test_every_verdict_disposition_engine_and_input_chip_carries_its_word():
    for style_map, build in ((C.VERDICT_STYLE, C.verdict_chip), (C.DISPOSITION_STYLE, C.disposition_chip),
                             (C.ENGINE_STYLE, lambda k: C.status_chip(C.ENGINE_STYLE, k)),
                             (C.INPUT_STATUS_STYLE, lambda k: C.status_chip(C.INPUT_STATUS_STYLE, k))):
        for key, (label, token) in style_map.items():
            chip = build(key)
            assert isinstance(chip, ft.Container), key
            assert texts(chip) == [label], (key, texts(chip))
            assert chip.content.color == getattr(theme.active(), token), key
    assert set(C.VERDICT_STYLE) == {"PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA", "NOT_RUN", "UNVERIFIED"}
    assert C.VERDICT_STYLE["UNVERIFIED"][1] == "warning"
    assert set(C.DISPOSITION_STYLE) == {"RECOMMENDATION", "BUILD_AS_INSURANCE", "INVARIANT_STEP", "SPECIFICATION_ONLY",
                                        "FORWARD_SIM", "REFUSAL_BOOK", "DESCRIPTIVE"}
    for key in ("FORWARD_SIM", "REFUSAL_BOOK"):                               # never styled as a recommendation
        label, token = C.DISPOSITION_STYLE[key]
        assert "not a recommendation" in label and token != "success"
    # prose spellings reach the enum entry; an unknown value still shows its word, in muted
    assert texts(C.verdict_chip("not run")) == ["NOT RUN"]
    assert texts(C.verdict_chip("INSUFFICIENT DATA")) == ["INSUFFICIENT DATA"]
    assert texts(C.disposition_chip("BUILD-AS-INSURANCE")) == ["BUILD-AS-INSURANCE"]
    odd = C.verdict_chip("SMOKE", tooltip="vendor data")
    assert texts(odd) == ["SMOKE"] and odd.content.color == theme.active().muted and odd.tooltip == "vendor data"
    assert texts(C.verdict_chip(None)) == ["unknown"]


def test_multiplier_bar_draws_fill_floor_and_vt_ticks_and_prints_the_numbers():
    bar = C.multiplier_bar(0.6, 0.8, width=260)
    stack = next(c for c in walk(bar) if isinstance(c, ft.Stack))
    tips = {c.tooltip: c for c in stack.controls if c.tooltip}
    assert abs(tips["composed 0.60"].width - 0.6 * 260) < 1e-9                 # the fill
    assert abs(tips["vt 0.80"].left - (0.8 * 260 - 1)) < 1e-9                   # the vt tick
    assert abs(tips["floor 0.40 (0.5 × vt)"].left - (0.4 * 260 - 1)) < 1e-9    # the floor tick, drawn not implied
    assert any(c.width == 260 for c in stack.controls if not c.tooltip)       # the 0 -> 1.0 track
    shown = " ".join(texts(bar))
    for word in ("composed 0.60", "vt 0.80", "floor 0.40", "cap 1.00"):
        assert word in shown, (word, shown)
    edge = C.multiplier_bar(0.0, 1.0)                                         # HALTED book at 0x: fill width 0
    assert any(isinstance(c, ft.Stack) for c in walk(edge))


def test_multiplier_bar_fails_closed_without_numbers():
    for composed, vt in ((1.2, 0.8), (0.6, None), (float("nan"), 0.8), (0.6, -0.1), (True, 0.8)):
        out = C.multiplier_bar(composed, vt)
        assert not any(isinstance(c, ft.Stack) for c in walk(out)), (composed, vt)
        assert out.border is not None and texts(out), (composed, vt)          # the error notice
        shown = " ".join(texts(out))
        assert "1.20" not in shown and "0.60" not in shown and "0.80" not in shown, shown


def test_data_table_column_count_numeric_flags_controls_and_ragged_rows():
    t = C.data_table(("Family", "Basis", "vol_scale", "Card"),
                     [("momentum", "active", "0.75", C.verdict_chip("NOT_RUN")), ("reversal", "total", None, "—")],
                     numeric_from=2)
    assert isinstance(t, ft.DataTable)
    assert len(t.columns) == 4 and all(len(r.cells) == 4 for r in t.rows) and len(t.rows) == 2
    assert [col.numeric for col in t.columns] == [False, False, True, True]
    assert "NOT RUN" in texts(t) and "Family" in texts(t) and "—" in texts(t)
    wide = C.data_table(("Id", "Text"), [("G-01", "a long sentence")], wide_last=True)
    assert wide.rows[0].cells[1].content.width == 460 and wide.data_row_max_height == 88
    try:
        C.data_table(("a", "b"), [("1",)])
    except ValueError as exc:
        assert "do not have 2 cells" in str(exc)
    else:
        raise AssertionError("a ragged row must be refused at build time")


def test_open_path_on_a_missing_file_returns_the_selectable_path():
    missing = ROOT / "docs" / "council" / "__no_such_page__.html"
    out = C.open_path(missing)
    assert isinstance(out, ft.Text) and out.selectable and str(missing) in out.value


def test_shell_fixes_runs_page_delegates_and_the_rail_scrolls():
    runs_src = (ROOT / "ui" / "runs_page.py").read_text(encoding="utf-8")
    assert "open_path(path)" in runs_src and "startfile" not in runs_src
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    rail = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "Column"
            and any(isinstance(a, ast.Name) and a.id == "nav_host" for a in ast.walk(n))]
    assert rail and any(k.arg == "scroll" for k in rail[0].keywords), "the rail column must scroll (19 entries, 620 px)"
    assert "on_app_start(background=True)" in (ROOT / "main.py").read_text(encoding="utf-8")


def test_flet_api_guard_passes_with_the_warning_token():
    from tests import flet_api_guard
    names = [n for n, _ in flet_api_guard.tests()]
    assert len(names) == 4, names
    for _, fn in flet_api_guard.tests():
        fn()


def test_readme_carries_both_disclaimers_and_no_stale_counts():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for line in DISCLAIMERS:
        assert line in text, line
    for stale in ("229 checks", "245 checks", "the equity six", "FICC sixteen"):
        assert stale not in text, stale
    assert "Macro integration (Quant Council specification v2.0)" in text
    for p in range(11):
        assert f"**P{p}." in text, f"P{p} paragraph missing"
    assert "MACRO-R06-US" in text and "REJECT (instrument: US shares via KIS, 50 bp, daily)" in text


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
