"""Sprint 8 B: the Macro page view selector and the Overlay state view (02_ui_design sections 1, 2, 4).

The renderer `ui.macro_state_panel.macro_state_blocks` runs on the S1 schema examples
(`tests/fixtures/macro/schema_examples.json`) plus a synthetic HALTED runtime entry, with no page: the control tree is
walked and the `ft.Text` values asserted (the quant_lab_page driver pattern). Hermetic: the one page build points
`TRADEGEN_MACRO_DIR` at a temp directory and asserts nothing was written there.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import flet as ft

from core.ficc.macro import Regime
from core.ficc.macro_schema import check_artifact
from core.skills import macro_daily as MD
from ui import macro_state_panel as P

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = json.loads((ROOT / "tests" / "fixtures" / "macro" / "schema_examples.json").read_text(encoding="utf-8"))
REC, SPEC = "recommended:KR", "specification:KR"
NUMBERS = ("0.694", "0.685", "28.8%", "0.755")          # the example state's exposure numbers
UTC_A, UTC_B = "2026-10-02T06:30:30Z", "2026-10-02T06:40:50Z"
HALT = {"class": "RISK", "reason_code": "hard_stop", "component": "core/engine/books", "series_id": None,
        "since_utc": UTC_A, "rearm_not_before": "2026-10-19", "rearm_mode": "auto",
        "causes": [{"class": "RISK", "reason_code": "hard_stop", "since_utc": UTC_A, "rearm_mode": "auto",
                    "rearm_not_before": "2026-10-19", "cleared_utc": None}], "ack_by": None, "ack_utc": None}


def walk(c):
    yield c
    for attr in ("controls", "rows", "cells", "columns"):
        v = getattr(c, attr, None)
        if isinstance(v, list):
            for child in v:
                yield from walk(child)
    for attr in ("content", "label", "title", "subtitle", "action"):
        child = getattr(c, attr, None)
        if isinstance(child, ft.Control):
            yield from walk(child)


def texts(blocks) -> list[str]:
    return [t.value for b in blocks for t in walk(b) if isinstance(t, ft.Text) and t.value]


def buttons(blocks) -> list[ft.Button]:
    return [x for b in blocks for x in walk(b) if isinstance(x, ft.Button)]


def state(engine: str = "DISARMED") -> dict:
    s = copy.deepcopy(EXAMPLES["macro_state"])
    for e in s["runtime"]:
        e["engine_state"] = engine
    s["flags"]["engine_state"] = engine
    return s


def halted(ack: bool = False) -> dict:
    s = state("ARMED")
    s["runtime"][0]["engine_state"] = "HALTED"
    s["runtime"][0]["halt"] = dict(copy.deepcopy(HALT), **({"ack_by": "operator", "ack_utc": UTC_B} if ack else {}))
    s["flags"].update(engine_state="HALTED", hard_stop="halted")
    return s


def overlays() -> list[dict]:
    """The example overlay (placeholders made valid) and a market_gross record built from it."""
    mom = copy.deepcopy(EXAMPLES["overlay_decision"])
    mom.update(generated_at_utc=UTC_B, knowledge_utc=UTC_B, market="KR", decision_utc=UTC_A, effective_session="2026-10-06")
    mom["inputs"][0].update(retrieved_at_utc=UTC_B, books=[SPEC])
    gross = copy.deepcopy(mom)
    gross.update(family="market_gross", exposure_basis="total", multipliers=[], ladder=1.0, post_rearm_cap=1.0,
                 vol_scale=0.694, vol_scale_recommended_book=1.0, overlay_min=1.0, overlay_applied_spec_book=1.0,
                 overlay_applied_recommended_book=1.0, binding=["R-06-VT"], reasons=["vt 0.694 binds"])
    return [mom, gross]


def blocks(s, *, ovs=None, alerts=(), owner=None, ctx=None, cal=None, acks=None, runs=None):
    return P.macro_state_blocks(s, overlays() if ovs is None else ovs, ctx, cal, list(alerts),
                                owner if owner is not None else {},
                                on_ack=lambda k, i: (acks if acks is not None else []).append((k, i)),
                                on_run=lambda m: (runs if runs is not None else []).append(m))


def test_fixtures_are_valid_artifacts():
    for s in (state(), halted(), halted(ack=True)):
        assert check_artifact("macro_state", s)[:2] == (True, []), check_artifact("macro_state", s)
    for o in overlays():
        assert check_artifact("overlay_decision", o)[:2] == (True, []), check_artifact("overlay_decision", o)


def test_fail_closed_no_state_or_invalid_state_shows_an_error_notice_and_no_numbers():
    runs = []
    none = blocks(None, runs=runs)
    assert isinstance(none[0], ft.Container) and "fail closed" in texts([none[0]])[0]
    assert "No macro state yet" in texts(none)
    run_button = next(b for b in buttons(none) if b.content == P.DRY_LABEL)
    run_button.on_click(None)
    assert runs == ["dry_run"]
    bad = state()
    bad["concentration"]["by_book"][REC]["composed"] = 1.7                       # an acting field out of bounds
    quarantined = {"quarantined_utc": UTC_B, "schema": "macro_state", "class": "acting", "issues": ["/vol: required"],
                   "artifact": state()}
    for s in (bad, quarantined, ["not", "a", "dict"]):
        out = blocks(s)
        found = texts(out)
        assert "refused" in found[0] and "no numbers" in found[0], found[:2]
        assert not any(n in t for t in found for n in NUMBERS + ("1.700",)), [t for t in found if any(n in t for n in NUMBERS)]
        assert "composed" not in found and not any(t.startswith("gross") for t in found)
    # a display-only error renders, with the errors in a notice (written with extras.validation_errors, R-32)
    shown = state()
    shown["flags"]["gap_sessions"] = "x"                                       # a display path (a null vol label is not
    found = texts(blocks(shown))                                               # an error since the S9 ruling (a))
    assert any(t.startswith("Display-only validation errors") and "gap_sessions" in t for t in found)
    assert "0.694" in found


def test_null_volatility_labels_say_why():
    s = state()
    s["vol"].update(display_label_rel=None, display_label_abs=None, label_status="rel: 300 < 756 sigma values")
    found = texts(P._vol(s))
    j = found.index(P.VOL_LABEL_CAPTION)
    assert found[j + 1:j + 3] == ["relative: —", "absolute: —"]
    assert "Volatility labels undefined: rel: 300 < 756 sigma values" in found
    s["vol"]["label_status"] = "ok"
    assert not any(t.startswith("Volatility labels undefined") for t in texts(P._vol(s)) + texts(P._vol(state())))


def test_refusal_book_labels_sit_on_their_own_line_not_in_a_table_row():
    label = "RETIRED: REJECT at every timing on KOSPI 1997-04 -> 2026-10 (refusal book, display only)"
    ovs = overlays()
    ovs[1]["refusal"] = [{"card": {"card_id": "MACRO-R11-KR-KRW", "class": "CARD-P", "displayed_as": "refusal",
                                   "disposition": "REFUSAL_BOOK", "label": label, "results_md5": None, "verdict": "REJECT"},
                          "rule_id": "R-11-S1", "value": 1.0, "would_apply_to": "Korea market gross (refusal book)"}]
    found = texts(blocks(state(), ovs=ovs))
    assert f"R-11-S1: {label}" in found and label not in found               # never inside a height-capped cell
    assert "REFUSAL BOOK · not a recommendation" in found


def test_a_disarmed_tile_for_each_book():
    out = blocks(state())
    tiles = out[1].controls                                                    # the ResponsiveRow of book tiles
    assert len(tiles) == 2
    for tile, book, composed in zip(tiles, (REC, SPEC), ("1.000", "0.694")):
        found = texts([tile])
        assert found[:2] == [book, "DISARMED"] and composed in found and "binding: active_single_name" in found, found


def test_halted_banner_names_class_reason_since_and_rearm_not_before_and_acknowledges():
    acks = []
    out = blocks(halted(), acks=acks)
    banner = next(t for t in texts(out) if "HALTED · class" in t)
    for part in ("recommended:KR HALTED", "class RISK", "reason hard_stop", f"since {UTC_A}", "re-arm auto",
                 "not before 2026-10-19"):
        assert part in banner, (part, banner)
    ack = next(b for b in buttons(out) if b.content == "Acknowledge")
    ack.on_click(None)
    assert acks == [("halt", REC)]
    assert any("HALTED: the book is at 0×" in t for t in texts(out))
    done = blocks(halted(ack=True))
    assert any("Acknowledged by operator at" in t for t in texts(done))
    assert not [b for b in buttons(done) if b.content == "Acknowledge"]


def test_the_composition_line_carries_the_artifact_numbers():
    found = texts(blocks(state()))
    assert "specification:KR: composed = 0.694 × min(1.0, ladder 1.00, post_rearm_cap 1.00) = 0.694" in found
    assert "gross = min(composed 0.694, bound 0.685 [active_single_name]) = 0.685" in found
    assert ("recommended:KR: composed = 1.000 × min(1.0, ladder 1.00 (steps act in specification), "
            "post_rearm_cap 1.00) = 1.000") in found
    assert "floor 0.35 (0.5 × vt)" in found and "cap 1.00" in found                 # the multiplier bar draws both
    no_gross = texts(blocks(state(), ovs=overlays()[:1]))
    assert any("min(1.0, no valid market_gross overlay_decision)" in t for t in no_gross)


def test_the_dry_run_chip_needs_backtest_and_the_marker():
    dry = state()
    dry.update(run_mode="backtest", extras={"dry_run": dict(MD.DRY_RUN_MARKER)})
    assert check_artifact("macro_state", dry)[0], check_artifact("macro_state", dry)
    assert texts(blocks(dry))[0] == P.DRY_RUN_CHIP
    live_marked = copy.deepcopy(dry)
    live_marked["run_mode"] = "live"
    unmarked = copy.deepcopy(dry)
    unmarked["extras"] = {}
    for s in (live_marked, unmarked, state()):
        assert P.DRY_RUN_CHIP not in texts(blocks(s))


def test_every_owner_decision_d1_to_d6_is_listed_with_value_and_status():
    owner = P.owner_items()
    assert not owner["errors"], owner["errors"]
    found = texts(blocks(state(), owner=owner))
    i = found.index("Open owner actions and decisions")
    rows = found[i:]
    for d, key, value, status, src in (("D1", "risk_layer.korea_caps.template", "msci_25_50", "default", "artifact"),
                                       ("D2", "risk_layer.drawdown.hard_stop.level", "-0.15", "default", "artifact"),
                                       ("D3", "families.reversal.calm_state_downweight", "not_adopted", "default", "rules store"),
                                       ("D4", "monitoring.false_demotion_budget_per_year", "0.1", "default", "rules store"),
                                       ("D5", "sleeves.US.line", "none", "pending", "rules store"),
                                       ("D6", "gate.acceptance_test.cdar_guard.calibration",
                                        "lowest_placebo_false_pass_rule", "default", "rules store")):
        j = rows.index(d)
        assert rows[j + 2:j + 6] == [key, value, status, src], (d, rows[j:j + 6])
    assert any(t.startswith("Owner inputs the build needs") for t in found)
    assert any("Sign the calendar set" in t for t in found) and any("repository under git" in t for t in found)
    assert any(t.startswith("OQ-01 · ") for t in found) and any(t.startswith("XS-01 · ") for t in found)
    # with no artifact the store still lists all six, never hidden
    found = texts(blocks(None, owner=owner))
    assert all(d in found for d in P.DECISIONS)


def test_alerts_are_ordered_page_then_warn_then_info_and_acknowledge_goes_to_core():
    def alert(aid, severity, code, series=None):
        return {"alert_id": aid, "code": code, "severity": severity, "component": "macro_daily", "series_id": series,
                "books": [REC], "first_seen_utc": UTC_A, "count": 1, "escalated": False, "ack_utc": None}
    acks = []
    out = blocks(state(), acks=acks, alerts=[alert("i1", "info", "INFO_CODE"), alert("p1", "page", "RUN_ERROR"),
                                            alert("w1", "warn", "WARN_CODE"), alert("p2", "page", "MISSED_DECISION"),
                                            alert("w2", "warn", "WARN_CODE", "S2"),
                                            dict(alert("p3", "page", "GOVERNANCE_LOG_BROKEN"), store="live")])
    found = texts(out)
    order = [next(k for k, t in enumerate(found) if code in t)
             for code in ("RUN_ERROR", "MISSED_DECISION", "GOVERNANCE_LOG_BROKEN", "WARN_CODE", "INFO_CODE")]
    assert order == sorted(order), order
    assert any(t.startswith("PAGE · RUN_ERROR") for t in found)
    assert any(t.startswith("PAGE · GOVERNANCE_LOG_BROKEN") and t.endswith("· live store") for t in found)
    assert found.count("WARN_CODE") == 1 and "×2" in found                    # identical codes grouped, display only
    for b in [b for b in buttons(out) if str(b.content).startswith("Acknowledge")]:
        b.on_click(None)
    assert acks == [("alert", "p1"), ("alert", "p2"), ("live_alert", "p3"), ("alerts", ["w1", "w2"]), ("alerts", ["i1"])]


test_alerts_are_ordered_page_then_warn_then_info_and_acknowledge_goes_to_core.test_ids = ["T-OBS-03"]


def test_descriptive_read_caption_volatility_labels_and_no_regime_state():
    from ui.macro_page import DESCRIPTIVE_CAPTION, read_row
    assert DESCRIPTIVE_CAPTION == "Descriptive read — not a regime model (P19)"
    row = read_row(Regime("bull steepener", "risk-off", "strong", "rising", "falling", "summary"))
    found = texts([row])
    assert found[0] == DESCRIPTIVE_CAPTION and "risk: risk-off" in found
    view = texts(blocks(state()))
    j = view.index(P.VOL_LABEL_CAPTION)
    assert view[j + 1:j + 3] == ["relative: elevated", "absolute: stressed"]
    assert not any("regime" in t.lower() for t in view), [t for t in view if "regime" in t.lower()]
    # FORWARD-SIM / refusal values live in their own group, never in the recommended book's stat strip
    assert "Display-only books — not a recommendation" in view


def test_view_selector_hosts_the_overlay_view_and_reads_nothing_into_home():
    from ui.macro_page import build_macro_page
    old = os.environ.get("TRADEGEN_MACRO_DIR")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["TRADEGEN_MACRO_DIR"] = tmp
        try:
            fake = SimpleNamespace(run_thread=lambda fn: fn(), update=lambda: None)
            root = build_macro_page(fake)
            view = next(c for c in walk(root) if isinstance(c, ft.Dropdown) and c.label == "View")
            switcher = next(c for c in walk(root) if isinstance(c, ft.AnimatedSwitcher))
            sheet = switcher.content
            assert view.value == "sheet" and [o.key for o in view.options] == ["sheet", "overlay", "cards", "research"]
            hosted = {}
            for key in ("cards", "research", "overlay"):            # S8 integration: every v2 view mounts with its own Refresh
                view.value = key
                view.on_select(None)
                hosted[key] = switcher.content
                assert hosted[key] is not sheet and sum(b.content == "Refresh" for b in buttons([hosted[key]])) == 1, key
            assert "Gate package" in texts([hosted["cards"]]) and "Tech-fund weight table (R3 design priors)" in texts([hosted["research"]])
            overlay = switcher.content
            found = texts([overlay])
            assert "No macro state yet" in found and P.LIVE_LABEL not in found
            mode = next(c for c in walk(overlay) if isinstance(c, ft.Dropdown) and c.label == "Run macro_daily")
            live = next(o for o in mode.options if o.key == "live")
            assert live.text == P.LIVE_LABEL and live.disabled and "signed calendars" in live.tooltip
            view.value = "sheet"
            view.on_select(None)
            assert switcher.content is sheet
            assert not any(Path(tmp).iterdir())                     # Refresh only reads
        finally:
            if old is None:
                os.environ.pop("TRADEGEN_MACRO_DIR", None)
            else:
                os.environ["TRADEGEN_MACRO_DIR"] = old


def test_the_run_button_dry_run_writes_only_the_temp_macro_dir_and_the_view_renders_it():
    """S8 integration: Macro -> Overlay state -> Run (dry run) end to end on the local vendor data (~15 s)."""
    from ui.macro_page import build_macro_page
    old = os.environ.get("TRADEGEN_MACRO_DIR")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["TRADEGEN_MACRO_DIR"] = tmp
        try:
            fake = SimpleNamespace(run_thread=lambda fn: fn(), update=lambda: None)
            root = build_macro_page(fake)
            view = next(c for c in walk(root) if isinstance(c, ft.Dropdown) and c.label == "View")
            view.value = "overlay"
            view.on_select(None)
            overlay = next(c for c in walk(root) if isinstance(c, ft.AnimatedSwitcher)).content
            mode = next(c for c in walk(overlay) if isinstance(c, ft.Dropdown) and c.label == "Run macro_daily")
            assert mode.value == "dry_run"
            next(b for b in buttons([overlay]) if b.content == "Run").on_click(None)
            written = {p.relative_to(tmp).parts[0] for p in Path(tmp).rglob("*") if p.is_file()}
            assert written == {"dry_run"}, written                # the dry run never writes a live artifact
            assert (Path(tmp) / "dry_run" / "macro_state" / "KR").is_dir()
            src = next(c for c in walk(overlay) if isinstance(c, ft.Dropdown) and c.label == "Artifacts")
            found = texts([overlay])
            assert src.value == "dry_run" and P.DRY_RUN_CHIP in found and P.RUNNING_TEXT not in found
            assert "DISARMED" in found and "ARMED" not in found and "HALTED" not in found
            assert any(t.startswith("recommended:KR: composed = ") for t in found)
            assert not any("macro_state refused" in t for t in found)
        finally:
            if old is None:
                os.environ.pop("TRADEGEN_MACRO_DIR", None)
            else:
                os.environ["TRADEGEN_MACRO_DIR"] = old


@contextmanager
def temp_macro_dir():
    old = os.environ.get("TRADEGEN_MACRO_DIR")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["TRADEGEN_MACRO_DIR"] = tmp
        try:
            yield Path(tmp)
        finally:
            if old is None:
                os.environ.pop("TRADEGEN_MACRO_DIR", None)
            else:
                os.environ["TRADEGEN_MACRO_DIR"] = old


def test_a_live_page_alert_shows_and_acknowledges_from_the_dry_run_view():
    from core.skills.alerts import AlertStore
    when = datetime(2026, 10, 7, 6, 0, tzinfo=timezone.utc)
    with temp_macro_dir() as tmp:
        AlertStore(tmp).raise_alert("GOVERNANCE_LOG_BROKEN", "page", "app_start", when=when)
        AlertStore(tmp).raise_alert("LIVE_WARN", "warn", "app_start", when=when)          # only page alerts cross over
        v = P.load_view(tmp / "dry_run", "KR")
        assert [(a["code"], a["store"]) for a in v["alerts"]] == [("GOVERNANCE_LOG_BROKEN", "live")]
        assert all("store" not in a for a in P.load_view(tmp, "KR")["alerts"])
        view = P.build_overlay_view(SimpleNamespace(run_thread=lambda fn: fn(), update=lambda: None))
        assert next(c for c in walk(view) if isinstance(c, ft.Dropdown) and c.label == "Artifacts").value == "dry_run"
        assert any(t.startswith("PAGE · GOVERNANCE_LOG_BROKEN") for t in texts([view]))
        next(b for b in buttons([view]) if b.content == "Acknowledge").on_click(None)
        assert AlertStore(tmp).open("page") == [] and "No open alerts." in texts([view])
        assert not (tmp / "dry_run").exists()                                           # the ack went to the live store


def test_the_overlay_view_runs_one_worker_at_a_time():
    with temp_macro_dir() as tmp:
        queued = []
        view = P.build_overlay_view(SimpleNamespace(run_thread=queued.append, update=lambda: None))
        assert len(queued) == 1                                                         # the build-time read, in flight
        run, refresh = (next(b for b in buttons([view]) if b.content == w) for w in ("Run", "Refresh"))
        assert run.disabled and refresh.disabled
        run.on_click(None)                                                              # a click that beat the disable
        assert len(queued) == 1 and "Busy: wait for the current run" in texts([view])
        queued.pop()()
        assert not run.disabled
        refresh.on_click(None)
        assert len(queued) == 1
        queued.pop()()
        assert not any(tmp.iterdir())                                                   # the refused Run wrote nothing


def test_the_flet_api_guard_passes_on_the_new_ui_modules():
    from tests import flet_api_guard as G
    for _, fn in G.tests():
        fn()


def tests():
    return [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
