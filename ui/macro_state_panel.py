"""Macro -> Overlay state: the v2 `macro_state` view (02_ui_design sections 2 and 4; code_ui D.1 / D.4; rulings 1, 7).

`macro_state_blocks(...)` is a pure renderer: validated artifact dicts in, controls out, testable without a page.
It never computes exposure: composed / gross / vt / overlay values are printed from the artifacts (the composition
line substitutes the recorded terms; the number after "=" is the artifact's own `composed`). It fails closed: no
artifact, a quarantine record, or an artifact whose errors touch an acting field -> an error notice and no numbers;
display-only errors (written with `extras.validation_errors`, R-32) are shown in a notice and the view renders.
No regime state is displayed (P19): the two volatility labels are captioned "volatility labels (display only)".
FORWARD-SIM and refusal values sit in their own "not a recommendation" group, never beside the recommended book.

`load_view(root, market)` reads the latest artifacts under `root` (`config.macro_dir()` or its `dry_run/`) through
the S6 readers; `build_overlay_view(page)` is the interactive view the Macro page's selector hosts: its own
Refresh, the Run dropdown (dry run / live), Acknowledge -> core (the UI holds no alert state).
"""
from __future__ import annotations

import copy
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import flet as ft

import config
from core.engine import books as BK
from core.ficc import contracts as CT
from core.ficc.context_log import read_context_log
from core.ficc.macro_artifacts import GIT_HASH, acts_in_recommended, default_relpath
from core.ficc.macro_schema import check_artifact
from core.skills import macro_daily as MD
from core.skills.alerts import AlertStore
from core.theme import active
from ui.components import (ENGINE_STYLE, INPUT_STATUS_STYLE, VERDICT_STYLE, card, chip, data_table,
                           disposition_chip, empty_state, key_value, mono, multiplier_bar, notice, stat,
                           status_chip, verdict_chip)

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ("D1", "D2", "D3", "D4", "D5", "D6")
DRY_RUN_CHIP = "VENDOR DATA · DRY RUN · not an official close · not a card run"
VOL_LABEL_CAPTION = "volatility labels (display only)"
DRY_LABEL = "Dry run (local vendor data)"
LIVE_LABEL = "Live (needs KIS, signed calendars)"
RUNNING_TEXT = "Running… (hermetic, local data)"
SEVERITY_ORDER = {"page": 0, "warn": 1, "info": 2}
SEVERITY_STYLE = {"page": ("PAGE", "error"), "warn": ("WARN", "warning"), "info": ("INFO", "muted")}
OWNER_STATUS_STYLE = {"default": ("default", "muted"), "owner_set": ("owner set", "success"),
                      "pending": ("pending", "accent")}
VT_STATUS_STYLE = {"ok": ("vt ok", "success"), "warmup": ("vt warmup", "accent"),
                   "fail_closed": ("vt fail closed", "error")}
B5_STYLE = {"PASS": ("B5 PASS", "success"), "FAIL": ("B5 FAIL", "error"), "NOT_RUN": ("B5 NOT RUN", "muted")}
HARD_STOP_STYLE = {"armed": ("hard stop armed", "muted"), "halted": ("hard stop HALTED", "error"),
                   "rearm_refused": ("re-arm refused", "error"), "post_rearm_cap": ("post-re-arm cap", "warning")}
VALUE_STATUS_TOKEN = {"official_close": "success", "first_release": "success", "revised": "accent",
                      "live_snapshot": "accent"}            # vendor_* / provisional_intraday -> warning
BOUND_KEY = {"absolute_single_name": "absolute_bound", "active_single_name": "active_bound",
             "aggregate": "aggregate_bound", "semis": "semis_bound"}
WEIGHT_BOOKS = ("recommended", "specification")


# --------------------------------------------------------------------------- #
# formatting (the core hands over decimals; nothing here composes a number)
# --------------------------------------------------------------------------- #
def _isnum(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _num(x, d: int = 3) -> str:
    return f"{x:.{d}f}" if _isnum(x) else "—"


def _pct(x) -> str:
    return f"{x * 100:.1f}%" if _isnum(x) else "—"


def _val(x) -> str:
    if _isnum(x):
        return f"{x:,.6g}"
    if isinstance(x, (list, tuple)):
        return "[" + ", ".join(_val(v) for v in x) + "]"
    return "—" if x is None or x == "" else str(x)


def _verdict_word(v) -> str:
    return VERDICT_STYLE.get(v, (str(v), ""))[0]


def _yn(x) -> str:
    return "—" if x is None else ("yes" if x else "no")


def _h(title: str, subtitle: str = "") -> ft.Control:
    pal = active()
    rows = [ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=pal.text)]
    if subtitle:
        rows.append(ft.Text(subtitle, size=12, color=pal.muted))
    return ft.Column(rows, spacing=2)


def _line(text: str, *, muted: bool = True) -> ft.Text:
    pal = active()
    return ft.Text(text, size=12, color=pal.muted if muted else pal.text, selectable=True)


def _scroll(table: ft.Control) -> ft.Control:
    return ft.Row([table], scroll=ft.ScrollMode.AUTO)


def _labelled(label: str, chips: list[ft.Control]) -> ft.Control:
    return ft.Row([ft.Text(label, size=12, color=active().muted, width=92), ft.Row(chips, spacing=6, wrap=True, expand=True)],
                  spacing=8, vertical_alignment=ft.CrossAxisAlignment.START)


def verdict_of(kind: str, obj) -> tuple[str, list[str]]:
    """'ok' | 'display' (display-only errors: render, with a notice) | 'refused' (an error notice, no numbers)."""
    if not isinstance(obj, dict):
        return "refused", [f"{kind}: not an artifact object"]
    if "quarantined_utc" in obj:                                   # a quarantine record (macro_artifacts.quarantine)
        return "refused", ([f"quarantined {obj.get('quarantined_utc')} (class {obj.get('class')})"]
                           + [str(i) for i in obj.get("issues") or []])
    ok, issues, acting = check_artifact(kind, obj)
    if ok:
        return "ok", []
    return ("refused" if acting or kind in ("context_log", "event_calendar") else "display"), issues


def _issues_text(issues: list[str], n: int = 8) -> str:
    more = f" (+{len(issues) - n} more)" if len(issues) > n else ""
    return "; ".join(issues[:n]) + more


# --------------------------------------------------------------------------- #
# the renderer
# --------------------------------------------------------------------------- #
def macro_state_blocks(state: dict | None, overlays: list[dict], context_log: dict | None,
                       event_calendar: dict | None, alerts: list[dict], owner_items: dict, *,
                       on_ack: Callable[[str, str], None], on_run: Callable[[str], None]) -> list[ft.Control]:
    """The Overlay state view, in the brief's order (02_ui_design section 2). `owner_items` =
    {decisions: [{decision, key, value, status, title}], inputs: [str], proposals: [{id, text, status}], errors: [str]};
    `on_ack(kind, id)` with kind "alert" / "live_alert" (alert_id), "alerts" (a warn/info group's alert_ids) or "halt"
    (book_id); `on_run(mode)` with "dry_run". Warn / info alerts are grouped by (severity, code), display only."""
    if state is None:
        return [notice("No macro_state artifact for this market: nothing is shown (fail closed, no numbers).", "error",
                       icon=ft.Icons.ERROR_OUTLINE),
                empty_state("No macro state yet",
                            "Run macro_daily (dry run on local vendor data) to see the pipeline end to end; books stay "
                            "DISARMED until official closes and signed calendars exist.",
                            icon=ft.Icons.PUBLIC_OUTLINED,
                            action=ft.Button(DRY_LABEL, icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                             on_click=lambda e: on_run("dry_run"))),
                *_alert_blocks(alerts, on_ack), *_owner_blocks(None, owner_items), _calendar_tile(event_calendar)]
    verdict, issues = verdict_of("macro_state", state)
    if verdict == "refused":
        return [notice("macro_state refused: no numbers are shown (fail closed). " + _issues_text(issues), "error",
                       icon=ft.Icons.ERROR_OUTLINE),
                *_alert_blocks(alerts, on_ack), *_owner_blocks(None, owner_items), _calendar_tile(event_calendar)]

    usable, refused = [], []
    for o in overlays or []:
        v, iss = verdict_of("overlay_decision", o)
        (refused if v == "refused" else usable).append((o, iss))
    usable.sort(key=lambda t: t[0].get("family") != "market_gross")          # the market line first
    mg =next((o for o, _ in usable if o.get("family") == "market_gross"), None)
    ids, rt, by_book = _book_ids(state)
    blocks = _head(state, issues)                                              # 1 run chips
    blocks += _books(state, ids, rt, by_book, on_ack)                          # 2 book tiles + HALT banners
    blocks += _composition(state, ids, rt, by_book, mg)                        # 3 composition line + bar
    blocks += _overlay_blocks(usable, refused, state)                          # 4 overlays + display-only books
    blocks += _vol(state)                                                      # 5 vol strip
    blocks += _flags(state)                                                    # 6 flags
    blocks += _alert_blocks(alerts, on_ack)                                    # 7 alerts
    blocks += _inputs(state)                                                   # 8 inputs
    blocks += _owner_blocks(state.get("owner_decisions"), owner_items)         # 9 owner decisions / inputs / proposals
    blocks += [_context_tile(context_log), _calendar_tile(event_calendar)]     # 10 collapsed
    blocks += _footer(state)                                                   # 11 provenance
    return blocks


def _head(state: dict, issues: list[str]) -> list[ft.Control]:
    ex = state.get("extras") or {}
    dry = ex.get("dry_run") if isinstance(ex, dict) else None
    chips = []
    if state.get("run_mode") == "backtest" and dry:
        tip = " · ".join(str(dry.get(k)) for k in ("chip", "source", "calendar") if dry.get(k)) if isinstance(dry, dict) else ""
        chips.append(chip(DRY_RUN_CHIP, "error", tooltip=tip))
    snap = str(state.get("data_snapshot_id") or "")
    ro = state.get("read_only") is True
    chips += [chip(f"market {state.get('market')}", "accent"), chip(f"decided {state.get('decided_session')}"),
              chip(f"effective {state.get('effective_session')}"), chip(f"decision {state.get('decision_utc')}"),
              chip(f"run_mode {state.get('run_mode')}", "muted" if state.get("run_mode") == "live" else "warning"),
              chip("read-only" if ro else "read_only not set", "success" if ro else "error"),
              chip(f"snapshot {snap[:8] or '—'}", tooltip=snap)]
    if state.get("fail_closed"):
        chips.append(chip("FAIL CLOSED", "error", tooltip="an acting input or component failed closed at this decision"))
    out: list[ft.Control] = [ft.Row(chips, spacing=6, wrap=True)]
    if issues:
        out.append(notice("Display-only validation errors (written with extras.validation_errors; never acting): "
                          + _issues_text(issues), "warning", icon=ft.Icons.WARNING_AMBER_OUTLINED))
    return out


def _book_ids(state: dict) -> tuple[list[str], dict, dict]:
    rt = {e.get("book_id"): e for e in state.get("runtime") or [] if isinstance(e, dict)}
    by_book = (state.get("concentration") or {}).get("by_book") or {}
    ids = [b for b in dict.fromkeys(list(rt) + list(by_book)) if str(b).split(":", 1)[0] in WEIGHT_BOOKS]
    return sorted(ids, key=lambda b: (not str(b).startswith("recommended"), str(b))), rt, by_book


def _books(state: dict, ids: list[str], rt: dict, by_book: dict, on_ack) -> list[ft.Control]:
    pal = active()
    failing = {}
    for f in ((state.get("extras") or {}).get("fail_closed_inputs") or []):
        for b in f.get("books") or []:
            failing.setdefault(b, []).append(str(f.get("series_id")))
    cols = []
    for b in ids:
        entry, bb = rt.get(b) or {}, by_book.get(b) or {}
        engine, bf = entry.get("engine_state") or "—", bb.get("binding_factor")
        extra = [chip(f"{len(failing[b])} failing input(s)", "error", tooltip=", ".join(failing[b]))] if b in failing else []
        tile = card(ft.Column([
            ft.Row([ft.Text(b, size=13, weight=ft.FontWeight.W_600, color=pal.text), status_chip(ENGINE_STYLE, engine)],
                   spacing=8, wrap=True),
            ft.Text("composed", size=10, color=pal.muted),
            ft.Text(_num(bb.get("composed")), size=24, weight=ft.FontWeight.BOLD, color=pal.text),
            ft.Row([chip(f"gross {_num(bb.get('gross'))}"),
                    chip(f"binding: {bf or '—'}", "muted" if bf in (None, "none") else "warning")] + extra,
                   spacing=6, wrap=True),
        ], spacing=4))
        items = [tile]
        if engine == "HALTED":
            items.append(_halt_banner(b, entry.get("halt") or {}, on_ack))
        cols.append(ft.Column(items, spacing=8, col={"xs": 12, "md": 6}))
    if not cols:
        return [notice("No weight book in this artifact's runtime[] or concentration.by_book.", "error")]
    return [ft.ResponsiveRow(cols, spacing=10, run_spacing=10)]


def halt_text(book_id: str, halt: dict) -> str:
    g = lambda k: halt.get(k) or "—"                               # noqa: E731
    return (f"{book_id} HALTED · class {g('class')} · reason {g('reason_code')} · since {g('since_utc')} · "
            f"re-arm {g('rearm_mode')}, not before {g('rearm_not_before')}. This view never re-arms a book.")


def _halt_banner(book_id: str, halt: dict, on_ack) -> ft.Control:
    text = halt_text(book_id, halt)
    if halt.get("ack_utc"):
        return notice(f"{text} Acknowledged by {halt.get('ack_by')} at {halt.get('ack_utc')}.", "error",
                      icon=ft.Icons.REPORT_PROBLEM_OUTLINED)
    return notice(text, "error", icon=ft.Icons.REPORT_PROBLEM_OUTLINED,
                  action=ft.Button("Acknowledge", on_click=lambda e, b=book_id: on_ack("halt", b)))


def composition_lines(state: dict, book_id: str, entry: dict, bb: dict, mg: dict | None) -> tuple[str, str]:
    """The binding composition text with the artifact's numbers substituted (rulings 3.3): factor terms from the
    market_gross overlay_decision, `= composed` / `= gross` from `concentration.by_book` (never recomputed)."""
    vol, flags, conc = state.get("vol") or {}, state.get("flags") or {}, state.get("concentration") or {}
    spec = book_id.startswith("specification")
    vt = vol.get("vt_weight_next" if spec else "vt_weight_recommended_book")
    if mg is None:
        terms = ["no valid market_gross overlay_decision"]
    else:
        mults = [m for m in mg.get("multipliers") or [] if spec or acts_in_recommended(m.get("card"))]
        steps_here = spec or flags.get("ladder_steps_act_in") == "recommended"
        ladder = _num(mg.get("ladder"), 2) if steps_here else "1.00 (steps act in specification)"
        terms = ([f"{m.get('rule_id')} {_num(m.get('value'), 2)}" for m in mults]
                 + [f"ladder {ladder}", f"post_rearm_cap {_num(mg.get('post_rearm_cap'), 2)}"])
    halted = " (HALTED: the book is at 0×; HALTED is never a min() argument)" if entry.get("engine_state") == "HALTED" else ""
    bf = bb.get("binding_factor")
    first = f"{book_id}: composed = {_num(vt)} × min(1.0, {', '.join(terms)}) = {_num(bb.get('composed'))}{halted}"
    second = (f"gross = min(composed {_num(bb.get('composed'))}, bound {_num(conc.get(BOUND_KEY.get(bf, '')))} "
              f"[{bf or '—'}]) = {_num(bb.get('gross'))}")
    return first, second


def _composition(state: dict, ids: list[str], rt: dict, by_book: dict, mg: dict | None) -> list[ft.Control]:
    vol = state.get("vol") or {}
    rows = []
    for b in ids:
        bb = by_book.get(b) or {}
        first, second = composition_lines(state, b, rt.get(b) or {}, bb, mg)
        vt = vol.get("vt_weight_next" if b.startswith("specification") else "vt_weight_recommended_book")
        rows.append(ft.Column([mono(first, size=12), mono(second, size=12), multiplier_bar(bb.get("composed"), vt)],
                              spacing=4))
    return [_h("Composition", "composed = vt × min(1.0, overlays…, ladder, post_rearm_cap); gross = min(composed, bound). "
                              "Values as recorded in the artifacts; nothing is recomputed here."),
            card(ft.Column(rows, spacing=14))]


def _overlay_blocks(usable: list, refused: list, state: dict) -> list[ft.Control]:
    out: list[ft.Control] = [_h("Overlays", "One overlay_decision per family; composition by min(), floor 0.5, cap 1.0.")]
    for o, iss in refused:
        out.append(notice(f"overlay_decision {o.get('family') if isinstance(o, dict) else '?'} refused: no numbers "
                          f"(fail closed). " + _issues_text(iss), "error", icon=ft.Icons.ERROR_OUTLINE))
    if not usable and not refused:
        out.append(notice("No overlay_decision artifacts for this decision's effective session.", "error"))
    rows, reasons = [], []
    for o, iss in usable:
        c = o.get("vol_scale_card") or {}
        mults = "; ".join(f"{m.get('rule_id')} {_num(m.get('value'), 2)} ({_verdict_word((m.get('card') or {}).get('verdict'))})"
                          for m in o.get("multipliers") or []) or "—"
        rows.append([o.get("family"), o.get("exposure_basis"), _num(o.get("vol_scale")),
                     _num(o.get("vol_scale_recommended_book")),
                     verdict_chip(c.get("verdict"), tooltip=f"{c.get('card_id')} · {c.get('disposition')} · {c.get('label') or ''}"),
                     mults, _num(o.get("ladder"), 2), _num(o.get("post_rearm_cap"), 2), _num(o.get("overlay_min")),
                     _num(o.get("overlay_applied_spec_book")), _num(o.get("overlay_applied_recommended_book")),
                     ", ".join(o.get("binding") or []) or "—"])
        reasons += [f"{o.get('family')}: {r}" for r in o.get("reasons") or []]
        if iss:
            reasons.append(f"{o.get('family')}: display-only validation errors: {_issues_text(iss)}")
    if rows:
        out.append(_scroll(data_table(("Family", "Basis", "vol_scale", "vol_scale (rec.)", "Card", "Multipliers",
                                       "Ladder", "Post-re-arm cap", "Min", "Spec. book", "Rec. book", "Binding"), rows)))
    out += [_line(r) for r in reasons]
    out += _display_only_books([o for o, _ in usable], state)
    return out


def _display_only_books(overlays: list[dict], state: dict) -> list[ft.Control]:
    rows, labels = [], []
    for o in overlays:
        for kind in ("forward_sim", "refusal"):
            for x in o.get(kind) or []:
                c = x.get("card") or {}
                rows.append([x.get("rule_id"), _num(x.get("value"), 2), x.get("would_apply_to"), c.get("card_id"),
                             disposition_chip(c.get("disposition") or ("FORWARD_SIM" if kind == "forward_sim" else "REFUSAL_BOOK"),
                                              tooltip=str(c.get("label") or ""))])
                if c.get("label"):                 # long card labels wrap on their own line, never inside a table row
                    labels.append(_line(f"{x.get('rule_id')}: {c['label']}"))
    fs, rb = state.get("forward_sim") or {}, state.get("refusal_books") or {}
    out = [_h("Display-only books — not a recommendation",
              "FORWARD-SIM and refusal books never enter a weight book's min() and never share its stat strip.")]
    if rows:
        out.append(_scroll(data_table(("Rule", "Value", "Would apply to", "Card", "Disposition"), rows)))
    out += labels
    out += [key_value(k, _val(v)) for k, v in list(fs.items()) + list(rb.items())]
    return out


def _vol(state: dict) -> list[ft.Control]:
    v = state.get("vol") or {}
    gate = v.get("estimator_gate") or {}
    tiles = [stat("σ̂ annualised", _pct(v.get("sigma_ann"))), stat("target", _pct(v.get("target_ann"))),
             stat("vt next (specification)", _num(v.get("vt_weight_next"))),
             stat("vt (recommended book)", _num(v.get("vt_weight_recommended_book")))]
    chips = [status_chip(VT_STATUS_STYLE, v.get("vt_status")), chip(f"estimator {v.get('estimator')}"),
             status_chip(B5_STYLE, v.get("estimator_b5")),
             chip(f"gate {gate.get('status')}", tooltip=str(gate.get("reason") or "")),
             chip(f"{v.get('instrument_book')} · {v.get('rebalance')}")]
    why = v.get("label_status") if v.get("label_status") not in (None, "", "ok") else ""   # why a label is null (warm-up)
    labels = ft.Row([ft.Text(VOL_LABEL_CAPTION, size=11, color=active().muted),
                     chip(f"relative: {v.get('display_label_rel') or '—'}", tooltip=str(why or v.get("label_method_rel") or "")),
                     chip(f"absolute: {v.get('display_label_abs') or '—'}", tooltip=str(why or v.get("label_method_abs") or ""))],
                    spacing=6, wrap=True)
    return ([_h("Volatility target"), ft.Row(tiles, spacing=10, wrap=True), ft.Row(chips, spacing=6, wrap=True), labels]
            + ([_line(f"Volatility labels undefined: {why}")] if why else []))


def _flags(state: dict) -> list[ft.Control]:
    f, an, lag = state.get("flags") or {}, state.get("annotations") or {}, state.get("lag_audit") or {}
    hco = f.get("hedge_credit_off")
    hedge = [chip("hedge credit off" if hco else "hedge credit on", "warning" if hco else "success"),
             chip(f"hedge failure: {_yn(f.get('hedge_failure'))}", "error" if f.get("hedge_failure") else "muted"),
             chip(f"classic risk-off: {_yn(f.get('classic_risk_off'))}"),
             chip(f"fx hedge credit: {_yn(f.get('fx_hedge_credit'))}")]
    hedge += [chip(r) for r in f.get("hedge_reasons") or []]
    if f.get("hedge_stale_inputs"):
        hedge.append(chip(f"stale: {', '.join(f['hedge_stale_inputs'])}", "warning"))
    step, bne = f.get("ladder_step"), f.get("block_new_entries")
    ladder = [chip(f"ladder {step or '—'}", "muted" if step in (None, "none") else "warning"),
              chip(f"dwell left {f.get('ladder_dwell_left', '—')}"),
              chip("blocks new entries" if bne else "new entries allowed", "warning" if bne else "muted"),
              chip(f"steps act in {f.get('ladder_steps_act_in') or '—'}"),
              status_chip(HARD_STOP_STYLE, f.get("hard_stop")), chip(f"hard-stop level {_pct(f.get('hard_stop_level'))}")]
    if "dm_bear_state" in f:
        ladder.append(chip(f"D-M bear state: {_yn(f.get('dm_bear_state'))}"))
    gap = [chip(f"KR open gap event: {_yn(f.get('kr_open_gap_event'))}", "warning" if f.get("kr_open_gap_event") else "muted"),
           chip(f"gap sessions {f.get('gap_sessions', '—')}"), chip(f"VaR display scale {_num(f.get('var_display_scale'), 4)}")]
    viol = lag.get("violations") or []
    notes = [chip(f"VIX ≥ VIX3M: {_yn(an.get('vix_ge_vix3m'))}"),
             chip(f"lag audit: {lag.get('checked', '—')} checked, {len(viol)} violation(s)", "error" if viol else "muted")]
    return [_h("Flags"), _labelled("Hedge", hedge), _labelled("Ladder", ladder), _labelled("Gap", gap),
            _labelled("Annotation", notes)] + [_line(str(n)) for n in an.get("notes") or []]


def _alert_text(a: dict) -> str:
    series = f" · {a.get('series_id')}" if a.get("series_id") else ""
    books = ", ".join(a.get("books") or []) or "no book"
    return (f"{str(a.get('severity')).upper()} · {a.get('code')} · {a.get('component')}{series} · count {a.get('count')} · "
            f"first seen {a.get('first_seen_utc')} · {books}" + (f" · {a['detail']}" if a.get("detail") else ""))


def _ack_button(a: dict, on_ack) -> ft.Control:
    if a.get("ack_utc"):
        return ft.Text(f"acknowledged {a['ack_utc']}", size=12, color=active().muted)
    kind = "live_alert" if a.get("store") == "live" else "alert"          # a live page alert shown in the dry-run view
    return ft.Button("Acknowledge", on_click=lambda e, k=kind, i=a.get("alert_id"): on_ack(k, i))


def _alert_blocks(alerts: list[dict], on_ack) -> list[ft.Control]:
    rows = sorted((a for a in alerts or [] if isinstance(a, dict)),
                  key=lambda a: (SEVERITY_ORDER.get(a.get("severity"), 3), str(a.get("first_seen_utc") or "")))
    if not rows:
        return [_h("Alerts"), _line("No open alerts.")]
    out: list[ft.Control] = [_h(f"Alerts ({len(rows)} open)", "Page alerts persist until acknowledged; "
                                                              "Acknowledge records ack_utc in the alert store.")]
    for a in rows:
        if a.get("severity") == "page":
            live = " · live store" if a.get("store") == "live" else ""
            out.append(notice(_alert_text(a) + live, "error", icon=ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,
                              action=_ack_button(a, on_ack)))
    groups: dict[tuple, list[dict]] = {}                  # warn / info: one row per (severity, code); display only
    for a in rows:
        if a.get("severity") != "page":
            groups.setdefault((a.get("severity"), a.get("code")), []).append(a)
    table = []
    for (sev, code), g in groups.items():
        ids = [a.get("alert_id") for a in g]
        detail = "\n".join(f"{a.get('component')}{' · ' + a['series_id'] if a.get('series_id') else ''} · count {a.get('count')}"
                           for a in g)
        books = sorted({b for a in g for b in a.get("books") or []})
        table.append([status_chip(SEVERITY_STYLE, sev), ft.Text(str(code), size=12, color=active().text, tooltip=detail),
                      f"×{len(g)}", ", ".join(books) or "—", min(str(a.get("first_seen_utc") or "") for a in g),
                      ft.Button("Acknowledge" + (f" {len(g)}" if len(g) > 1 else ""),
                                on_click=lambda e, i=ids: on_ack("alerts", i))])
    if table:
        out.append(_scroll(data_table(("Severity", "Code", "Open", "Books", "First seen (UTC)", ""), table)))
    return out


def _inputs(state: dict) -> list[ft.Control]:
    rows = []
    for i in state.get("inputs") or []:
        vs = i.get("value_status")
        rows.append([i.get("name"), i.get("series_id"), i.get("source"), i.get("obs_date"), _val(i.get("value")),
                     chip(vs or "—", VALUE_STATUS_TOKEN.get(vs, "warning" if vs else "muted")), i.get("role"),
                     status_chip(INPUT_STATUS_STYLE, i.get("status")), i.get("stale_deadline_utc"), _yn(i.get("dispute"))])
    for f in (state.get("extras") or {}).get("fail_closed_inputs") or []:
        rows.append([f.get("series_id"), f.get("series_id"), "—", "—", "—", chip("no value"),
                     "acting: " + (", ".join(f.get("books") or []) or "—"), status_chip(INPUT_STATUS_STYLE, f.get("status")),
                     "—", "—"])
    out: list[ft.Control] = [_h("Inputs", "Recorded inputs, then the acting inputs that failed closed.")]
    if rows:
        out.append(_scroll(data_table(("Name", "Series", "Source", "Obs date", "Value", "Value status", "Role", "Status",
                                       "Stale deadline (UTC)", "Dispute"), rows)))
    else:
        out.append(_line("No inputs recorded."))
    return out


def _owner_blocks(state_od: dict | None, owner_items: dict) -> list[ft.Control]:
    oi = owner_items or {}
    store = {d.get("decision"): d for d in oi.get("decisions") or [] if isinstance(d, dict)}
    art = {v.get("decision"): {"key": k, **v} for k, v in (state_od or {}).items() if isinstance(v, dict)}
    rows = []
    for d in DECISIONS:
        e, src = (art[d], "artifact") if d in art else (store.get(d), "rules store")
        title = (store.get(d) or {}).get("title") or ""
        if e is None:
            rows.append([d, title, "—", "—", chip("not in the artifact or the store", "error"), "—"])
        else:
            rows.append([d, title, e.get("key"), _val(e.get("value")), status_chip(OWNER_STATUS_STYLE, e.get("status")), src])
    out: list[ft.Control] = [_h("Open owner actions and decisions", "Read-only: the owner rules through the rules store.")]
    out += [notice(err, "error", icon=ft.Icons.ERROR_OUTLINE) for err in oi.get("errors") or []]
    out.append(_scroll(data_table(("Decision", "Title", "Canonical key", "Value", "Status", "Source"), rows)))
    inputs = oi.get("inputs") or []
    out.append(_h(f"Owner inputs the build needs ({len(inputs)})"))
    out += [ft.Text(f"• {t}", size=12, color=active().text, selectable=True) for t in inputs] or [_line("None listed.")]
    props = oi.get("proposals") or []
    out.append(_h(f"Proposals pending owner confirmation ({len(props)})", "Tech-fund XS / OQ items: none changes an acting parameter."))
    for p in props:
        out.append(ft.Text(f"{p.get('id')} · {p.get('status')} · {p.get('text')}", size=12, color=active().text,
                           max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, tooltip=str(p.get("text") or "")))
    return out


def _context_tile(ctx: dict | None) -> ft.Control:
    pal = active()
    if ctx is None:
        body, sub = [_line("No context_log artifact for this decision.")], "none"
    else:
        v, iss = verdict_of("context_log", ctx)
        if v == "refused":
            body, sub = [notice("context_log refused: nothing shown. " + _issues_text(iss), "error", icon=ft.Icons.ERROR_OUTLINE)], "refused"
        else:
            items = [i for i in ctx.get("items") or [] if isinstance(i, dict)]
            rows = [[i.get("name"), i.get("series_id"), i.get("obs_date"),
                     _val(i.get("value") if i.get("value") is not None else i.get("range")), i.get("value_status"),
                     _yn(i.get("stale")), i.get("note")] for i in items]
            body = [_line("Context only — never acts, feeds no book (R-13).")]
            body.append(_scroll(data_table(("Name", "Series", "Obs date", "Value", "Value status", "Stale", "Note"), rows, wide_last=True))
                        if rows else _line("No items."))
            sub = f"{len(items)} item(s) · as of {ctx.get('as_of_utc')}"
    return ft.ExpansionTile(title=ft.Text("Context log", size=14, weight=ft.FontWeight.W_600, color=pal.text),
                            subtitle=ft.Text(sub, size=12, color=pal.muted), controls=body, expanded=False)


def _calendar_tile(cal: dict | None) -> ft.Control:
    pal = active()
    if cal is None:
        body, sub = [_line("No event_calendar artifact yet (the calendar set is unsigned).")], "none"
    else:
        v, iss = verdict_of("event_calendar", cal)
        if v == "refused":
            body, sub = [notice("event_calendar refused: nothing shown. " + _issues_text(iss), "error", icon=ft.Icons.ERROR_OUTLINE)], "refused"
        else:
            events = [e for e in cal.get("events") or [] if isinstance(e, dict)]
            rows = [[e.get("event_id"), e.get("type"), e.get("region"), e.get("scheduled_utc"), e.get("status"),
                     e.get("kr_open_gap_session"),
                     "; ".join(f"{w.get('market')} {w.get('start_utc')} → {w.get('end_utc')} {w.get('action')}"
                               for w in e.get("windows") or []) or "—"] for e in events]
            body = [_scroll(data_table(("Event", "Type", "Region", "Scheduled (UTC)", "Status", "KR gap session", "Windows"),
                                       rows, wide_last=True)) if rows else _line("No events.")]
            sub = f"{len(events)} event(s) · version {cal.get('calendar_version')}"
    return ft.ExpansionTile(title=ft.Text("Event calendar", size=14, weight=ft.FontWeight.W_600, color=pal.text),
                            subtitle=ft.Text(sub, size=12, color=pal.muted), controls=body, expanded=False)


def _footer(state: dict) -> list[ft.Control]:
    git, tree = str(state.get("git_hash") or "—"), str(state.get("tree_hash") or "")
    snap, cfg = str(state.get("data_snapshot_id") or ""), str(state.get("config_hash") or "")
    return [ft.Divider(height=1, color=active().border), ft.Row([
        chip(f"{state.get('schema')} v{state.get('schema_version')}"),
        chip(f"git {git}", "warning" if git == "UNVERSIONED" else "muted",
             tooltip="owner action: place the repository under git" if git == "UNVERSIONED" else ""),
        chip(f"tree {tree[:12] or '—'}", tooltip=tree), chip(f"knowledge {state.get('knowledge_utc')}"),
        chip(f"snapshot {snap[:12] or '—'}", tooltip=snap), chip(f"config {cfg[:12] or '—'}", tooltip=cfg),
        chip(f"generated {state.get('generated_at_utc')}")], spacing=6, wrap=True)]


# --------------------------------------------------------------------------- #
# readers (the S6 artifact layout; read-only)
# --------------------------------------------------------------------------- #
def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _newest_quarantine(root: Path, market: str, state: dict | None) -> dict | None:
    """A quarantined macro_state of this market at or after the latest written one wins (fail closed)."""
    best, key = None, None
    for p in sorted((root / "quarantine").glob("macro_state__*.json")):
        rec = _read(p)
        art = rec.get("artifact") if isinstance(rec.get("artifact"), dict) else {}
        if art.get("market") != market:
            continue
        k = (str(art.get("decided_session")), str(rec.get("quarantined_utc")))
        if state is not None and k[0] < str(state.get("decided_session")):
            continue
        if key is None or k > key:
            best, key = rec, k
    return best


def _with_live_acks(root: Path, state: dict) -> dict:
    """The HALT banner's acknowledgement is the live book state (books.acknowledge writes it; the artifact is the
    decision-time snapshot): copy ack_by / ack_utc from the registry onto a copy of the HALTED entries."""
    if not any(isinstance(e, dict) and e.get("engine_state") == "HALTED" for e in state.get("runtime") or []):
        return state
    if not (root / "books").is_dir():
        return state
    reg, out = BK.BookRegistry(root), copy.deepcopy(state)
    for e in out.get("runtime") or []:
        if e.get("engine_state") == "HALTED" and e.get("book_id") in reg.ids() and isinstance(e.get("halt"), dict):
            live = reg.get(e["book_id"]).halt or {}
            if live.get("ack_utc"):
                e["halt"].update(ack_by=live.get("ack_by"), ack_utc=live.get("ack_utc"))
    return out


def owner_items() -> dict:
    """D1-D6 from the rules store (with the backlog titles), the owner inputs the build needs, and the tech-fund
    proposals pending owner confirmation (OQ, XS). A failing reader is reported in `errors`, never hidden."""
    out: dict = {"decisions": [], "inputs": [], "proposals": [], "errors": []}
    try:
        from core.rules import backlog_registry as BR
        import config
        from core.rules import macro_rules as R
        from core.skills.macro_daily import GOVERNANCE_LOG
        store = R.load_store(rulings_log=config.macro_dir() / GOVERNANCE_LOG)   # owner rulings replayed (S1)
        titles = {r.get("item_id"): r.get("title", "") for r in BR.load_registry().get("owner_decision", [])}
        out["decisions"] = [{"decision": d, **R.owner_decision(store, d), "title": titles.get(d, "")} for d in DECISIONS]
        out["inputs"] += [f"sleeves.{m}.notional_nav: owner-signed notional NAV (typed null; fails closed)"
                          for m in MD.MARKETS if store.get(f"sleeves.{m}.notional_nav") is None]
    except Exception as exc:                                       # noqa: BLE001 - reported, never raised into the view
        out["errors"].append(f"rules store: {type(exc).__name__}: {exc}")
    try:
        from core.calendars import store as CS
        unsigned = [r["file"] for r in CS.describe() if r.get("status") != "signed"]
        if unsigned:
            out["inputs"].insert(0, f"Sign the calendar set ({len(unsigned)} file(s) unsigned: {', '.join(unsigned[:3])}…): "
                                    "every live run refuses CalendarUnsigned")
    except Exception as exc:                                       # noqa: BLE001
        out["errors"].append(f"calendar store: {type(exc).__name__}: {exc}")
    if not any((ROOT / "docs" / "kis_quote_check").glob("*.json")):
        out["inputs"].append("KIS quote-field check not run: run docs/kis_quote_check.py with KIS credentials over "
                             "~20 live sessions (T-RO-02)")
    try:
        out["inputs"] += [f"{sid}: {s.get('channel')}" for sid, s in CT.default_registry().series.items()
                          if "OWNER" in str(s.get("channel", "")).upper()]
    except Exception as exc:                                       # noqa: BLE001
        out["errors"].append(f"series registry: {type(exc).__name__}: {exc}")
    if GIT_HASH == "UNVERSIONED":
        out["inputs"].append("Place the repository under git: the M7 freeze and verdict_filter check (iii) refuse UNVERSIONED")
    try:
        from core.quant import instruments as INS
        items = INS.owner_inputs()
        if items:
            out["inputs"].append(f"Instrument books ({len(items)} typed nulls): " + "; ".join(items))
    except Exception as exc:                                       # noqa: BLE001
        out["errors"].append(f"instrument books: {type(exc).__name__}: {exc}")
    try:
        from core import techfund as TF
        out["proposals"] = ([{"id": q.get("id"), "text": q.get("question"), "status": q.get("owner_status")}
                             for q in TF.open_questions()]
                            + [{"id": x.get("id"), "text": x.get("amendment"), "status": f"{x.get('status')} · {x.get('owner_status')}"}
                               for x in TF.cross_spec_amendments()])
    except Exception as exc:                                       # noqa: BLE001
        out["errors"].append(f"tech-fund register: {type(exc).__name__}: {exc}")
    return out


def load_view(root, market: str) -> dict:
    """Latest artifacts of one market under `root`; the renderer validates them (fail closed)."""
    root = Path(root)
    files = sorted((root / "macro_state" / market).glob("*.json"))
    state = _read(files[-1]) if files else None
    state = _newest_quarantine(root, market, state) or state
    overlays, ctx = [], None
    if isinstance(state, dict) and "quarantined_utc" not in state:
        overlays = [_read(p) for p in sorted((root / "overlay_decision" / market / str(state.get("effective_session"))).glob("*.json"))]
        cpath = root / default_relpath("context_log", {"decision_utc": state.get("decision_utc")})
        ctx = read_context_log(cpath) if cpath.is_file() else None
        state = _with_live_acks(root, state)
    cals = sorted((root / "event_calendar").glob("*.json"), key=lambda p: p.stat().st_mtime)
    alerts, live = AlertStore(root).open(), config.macro_dir()
    if root.resolve() != live.resolve():                  # live page alerts stay visible from any root (rulings 12)
        alerts += [dict(a, store="live") for a in AlertStore(live).open("page")]
    return {"state": state, "overlays": overlays, "context_log": ctx, "event_calendar": _read(cals[-1]) if cals else None,
            "alerts": alerts, "owner_items": owner_items()}


def live_missing() -> list[str]:
    """What a live macro_daily run still needs on this machine (the Live option stays disabled while any is missing)."""
    out = []
    try:
        from core.calendars import store as CS
        rows = CS.describe()
        unsigned = sum(r.get("status") != "signed" for r in rows)
        if unsigned:
            out.append(f"signed calendars ({unsigned} of {len(rows)} files unsigned)")
    except Exception as exc:                                       # noqa: BLE001
        out.append(f"calendar store unreadable ({type(exc).__name__})")
    if not config.kis_ready():
        out.append("KIS credentials (KIS_APP_KEY / KIS_APP_SECRET)")
    return out


# --------------------------------------------------------------------------- #
# the interactive view (hosted by ui/macro_page.py's view selector)
# --------------------------------------------------------------------------- #
def build_overlay_view(page: ft.Page) -> ft.Control:
    pal = active()
    base = config.macro_dir()
    market = ft.Dropdown(label="Market", width=120, value=MD.MARKETS[0],
                         options=[ft.dropdown.Option(m, m) for m in MD.MARKETS])
    source = ft.Dropdown(label="Artifacts", width=240, value="live" if (base / "macro_state").is_dir() else "dry_run",
                         options=[ft.dropdown.Option("live", "Live (macro dir)"),
                                  ft.dropdown.Option("dry_run", "Dry run (macro dir/dry_run)")])
    live_opt = ft.dropdown.Option("live", LIVE_LABEL, disabled=True, tooltip="checking what a live run needs…")
    mode = ft.Dropdown(label="Run macro_daily", width=300, value="dry_run",
                       options=[ft.dropdown.Option("dry_run", DRY_LABEL), live_opt])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    status = ft.Text("", size=12, color=pal.muted)
    host = ft.Column(spacing=14)
    refresh_btn = ft.Button("Refresh", icon=ft.Icons.REFRESH)
    run_btn = ft.Button("Run", icon=ft.Icons.PLAY_ARROW_ROUNDED)
    lock = threading.Lock()                                # one worker at a time: Run / Acknowledge write state

    def root() -> Path:
        return config.macro_dir() / "dry_run" if source.value == "dry_run" else config.macro_dir()

    def set_busy(on: bool, label: str = "") -> None:
        busy.visible, status.value = on, label
        for c in (market, source, refresh_btn, mode, run_btn):   # no selector change mid-read (view matches selectors)
            c.disabled = on

    def guarded(work: Callable[[], list], label: str) -> None:
        if not lock.acquire(blocking=False):
            status.value = "Busy: wait for the current run"
            page.update()
            return
        set_busy(True, label)
        page.update()

        def worker():
            try:
                try:
                    blocks = work()
                except Exception as exc:                           # noqa: BLE001 - never raise out of a worker
                    blocks = [notice(f"{type(exc).__name__}: {exc}", "error", icon=ft.Icons.ERROR_OUTLINE)]
                host.controls = blocks
                set_busy(False)
                page.update()
            finally:
                lock.release()

        page.run_thread(worker)

    def render() -> list:
        missing = live_missing()
        live_opt.disabled = bool(missing)
        live_opt.tooltip = ("Missing: " + "; ".join(missing)) if missing else "Runs one live decision of the selected market"
        v = load_view(root(), market.value or MD.MARKETS[0])
        return macro_state_blocks(v["state"], v["overlays"], v["context_log"], v["event_calendar"], v["alerts"],
                                  v["owner_items"], on_ack=ack, on_run=run)

    def refresh(e=None) -> None:
        guarded(render, "Reading artifacts…")

    def run(which: str | None = None) -> None:
        which = which or mode.value or "dry_run"
        if which == "live" and live_opt.disabled:
            host.controls = [notice("Live run unavailable. " + (live_opt.tooltip or ""), "error", icon=ft.Icons.ERROR_OUTLINE)]
            page.update()
            return

        def work() -> list:
            now = datetime.now(timezone.utc)                       # the button's one wall-clock read, pinned for the run
            if which == "dry_run":
                MD.dry_run(config.macro_dir(), clock=lambda: now)
                source.value = "dry_run"
            else:
                MD.run_decision(MD.default_services(config.macro_dir(), lambda: now), market.value or MD.MARKETS[0],
                                now.date(), run_mode="live")
                source.value = "live"
            return render()

        guarded(work, RUNNING_TEXT if which == "dry_run" else "Running one live decision…")

    def ack(kind: str, ident) -> None:
        """kind "halt" (book id), "alert" (one id), "alerts" (a group's ids) under root(); "live_alert" (one id) in
        the live store (a live page alert shown while Artifacts is Dry run)."""
        def work() -> list:
            now, r = datetime.now(timezone.utc), root()
            store = AlertStore(config.macro_dir() if kind == "live_alert" else r)
            if kind == "halt":
                BK.acknowledge(BK.BookRegistry(r), ident, "operator", now)
                for a in store.open():
                    if str(a.get("code", "")).startswith("HALT_") and ident in (a.get("books") or []):
                        store.acknowledge(a["alert_id"], "operator", now)
            else:
                for i in (ident if kind == "alerts" else [ident]):
                    store.acknowledge(i, "operator", now)
            return render()

        guarded(work, "Acknowledging…")

    market.on_select = refresh
    source.on_select = refresh
    refresh_btn.on_click = refresh
    run_btn.on_click = lambda e: run()
    view = ft.Column([
        ft.Row([market, source, refresh_btn, mode, run_btn, busy, status], spacing=10, wrap=True),
        ft.Column([host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)
    refresh()
    return view
