"""Shared presentation atoms for the cockpit.

Kept in one place because the three pages must agree on what "ready" looks like.
A skill that is blocked on a key and a workflow that is blocked on a key should
be the same colour, the same word, and the same shape, or the operator has to
re-learn the interface on every tab.
"""
from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path
from typing import Callable, Optional, Sequence

import flet as ft

from core.skills.readiness import State
from core.theme import RADII, active

# One vocabulary for readiness, used by every surface.
STATE_STYLE: dict[State, tuple[str, str]] = {
    State.READY:       ("Ready", "success"),
    State.NEEDS_INPUT: ("Needs input", "accent"),
    State.MISSING_KEY: ("Key required", "error"),
    State.DOC_ONLY:    ("Reference only", "muted"),
}

RUN_STATUS_STYLE: dict[str, tuple[str, str]] = {
    "ok":        ("Succeeded", "success"),
    "failed":    ("Failed", "error"),
    "timeout":   ("Timed out", "error"),
    "cancelled": ("Cancelled", "muted"),
    "error":     ("Could not start", "error"),
    "running":   ("Running", "accent"),
}


def _colour(token: str) -> str:
    return getattr(active(), token)


def colour_for(token: str) -> str:
    """Resolve a palette token to a colour. Public so pages can tint text and
    icons with the same tokens the chips use, instead of picking their own."""
    return _colour(token)


def chip(text: str, token: str = "muted", *, tooltip: str = "") -> ft.Container:
    """Small status pill. Carries a text label, never colour alone."""
    pal = active()
    return ft.Container(
        content=ft.Text(text, size=11, color=_colour(token), weight=ft.FontWeight.W_500),
        padding=ft.Padding(8, 3, 8, 3),
        bgcolor=pal.surface_2,
        border=ft.Border.all(1, _colour(token)),
        border_radius=RADII["pill"],
        tooltip=tooltip or None,
    )


def readiness_chip(state: State, *, tooltip: str = "") -> ft.Container:
    label, token = STATE_STYLE[state]
    return chip(label, token, tooltip=tooltip)


def run_status_chip(status: str) -> ft.Container:
    label, token = RUN_STATUS_STYLE.get(status, (status or "unknown", "muted"))
    return chip(label, token)


def section(title: str, *, subtitle: str = "") -> ft.Column:
    pal = active()
    rows = [ft.Text(title, size=26, weight=ft.FontWeight.BOLD, color=pal.text)]
    if subtitle:
        rows.append(ft.Text(subtitle, size=13, color=pal.muted))
    return ft.Column(rows, spacing=4)


def card(content: ft.Control, *, on_click: Optional[Callable] = None,
         col: Optional[dict] = None, tooltip: str = "") -> ft.Container:
    pal = active()
    return ft.Container(
        content=content,
        padding=16,
        bgcolor=pal.surface,
        border=ft.Border.all(1, pal.border),
        border_radius=RADII["lg"],
        on_click=on_click,
        ink=on_click is not None,
        tooltip=tooltip or None,
        col=col,
    )


def notice(text: str, token: str = "accent", *, icon: str = ft.Icons.INFO_OUTLINE,
           action: Optional[ft.Control] = None) -> ft.Container:
    """Banner for a state the operator must act on. Loud enough to be read."""
    pal = active()
    row = [
        ft.Icon(icon, size=18, color=_colour(token)),
        ft.Text(text, size=13, color=pal.text, expand=True, selectable=True),
    ]
    if action is not None:
        row.append(action)
    return ft.Container(
        content=ft.Row(row, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=14,
        bgcolor=pal.surface_2,
        border=ft.Border.all(1, _colour(token)),
        border_radius=RADII["md"],
    )


def empty_state(title: str, detail: str, *, icon: str = ft.Icons.INBOX_OUTLINED,
                action: Optional[ft.Control] = None) -> ft.Container:
    """An empty screen must say what is missing and what to do about it."""
    pal = active()
    items = [
        ft.Icon(icon, size=40, color=pal.muted),
        ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=pal.text,
                text_align=ft.TextAlign.CENTER),
        ft.Text(detail, size=13, color=pal.muted, text_align=ft.TextAlign.CENTER),
    ]
    if action is not None:
        items.append(ft.Container(action, padding=ft.Padding(0, 8, 0, 0)))
    return ft.Container(
        content=ft.Column(items, spacing=10,
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        alignment=ft.Alignment.CENTER,
        padding=48,
        expand=True,
    )


def key_value(label: str, value: str, *, width: int = 132) -> ft.Row:
    pal = active()
    return ft.Row(
        [ft.Text(label, size=12, color=pal.muted, width=width),
         ft.Text(value or "—", size=12, color=pal.text, expand=True, selectable=True)],
        spacing=8, vertical_alignment=ft.CrossAxisAlignment.START,
    )


def mono(text: str, *, size: int = 11) -> ft.Text:
    return ft.Text(text, size=size, color=active().text, selectable=True,
                   font_family="Consolas, monospace")


def stat(label: str, value: str, *, token: str = "text", tooltip: str = "") -> ft.Container:
    """Metric tile: small muted label over a bold value. Every result strip in
    the app is a row of these, so they must look identical across pages."""
    pal = active()
    return ft.Container(
        ft.Column([
            ft.Text(label, size=10, color=pal.muted),
            ft.Text(value, size=16, weight=ft.FontWeight.W_600,
                    color=getattr(pal, token, pal.text)),
        ], spacing=2),
        padding=ft.Padding(14, 10, 14, 10), bgcolor=pal.surface_2,
        border=ft.Border.all(1, pal.border), border_radius=RADII["md"],
        tooltip=tooltip or None,
    )


# --------------------------------------------------------------------------- #
# v2 vocabularies (02_ui_design section 3): one map per enum, every chip carries its word.
# --------------------------------------------------------------------------- #
VERDICT_STYLE: dict[str, tuple[str, str]] = {
    "PASS":              ("PASS", "success"),
    "REVISE":            ("REVISE", "accent"),
    "REJECT":            ("REJECT", "error"),
    "INSUFFICIENT_DATA": ("INSUFFICIENT DATA", "muted"),
    "NOT_RUN":           ("NOT RUN", "muted"),
    "UNVERIFIED":        ("UNVERIFIED", "warning"),
}

DISPOSITION_STYLE: dict[str, tuple[str, str]] = {
    "RECOMMENDATION":     ("RECOMMENDATION", "success"),
    "BUILD_AS_INSURANCE": ("BUILD-AS-INSURANCE", "accent"),
    "INVARIANT_STEP":     ("INVARIANT", "accent"),
    "SPECIFICATION_ONLY": ("SPECIFICATION BOOK", "muted"),
    "FORWARD_SIM":        ("FORWARD-SIM · not a recommendation", "muted"),
    "REFUSAL_BOOK":       ("REFUSAL BOOK · not a recommendation", "muted"),
    "DESCRIPTIVE":        ("DESCRIPTIVE", "muted"),
}

ENGINE_STYLE: dict[str, tuple[str, str]] = {
    "DISARMED": ("DISARMED", "muted"),
    "ARMED":    ("ARMED", "success"),
    "HALTED":   ("HALTED", "error"),
}

INPUT_STATUS_STYLE: dict[str, tuple[str, str]] = {
    "ok": ("ok", "success"), "warmup": ("warmup", "accent"), "disputed": ("disputed", "warning"),
    "not_run": ("not run", "muted"),
    **{k: (k.replace("_", " "), "error") for k in (
        "stale", "stale_missed_release", "missing", "provisional_rejected", "session_mismatch",
        "synthetic_rejected", "fail_closed")},
}


def _key(value) -> str:
    """'not run' / 'INSUFFICIENT DATA' / 'build-as-insurance' -> the enum spelling the maps are keyed by."""
    return str(value or "").strip().upper().replace(" ", "_").replace("-", "_")


def status_chip(style_map: dict, key, *, tooltip: str = "") -> ft.Container:
    """Chip from any `{key: (label, token)}` map; an unknown key shows its own word in muted, never blank."""
    label, token = style_map.get(key, (str(key) if key not in (None, "") else "unknown", "muted"))
    return chip(label, token, tooltip=tooltip)


def verdict_chip(verdict, *, tooltip: str = "") -> ft.Container:
    k = _key(verdict)
    return status_chip(VERDICT_STYLE, k if k in VERDICT_STYLE else verdict, tooltip=tooltip)


def disposition_chip(disposition, *, tooltip: str = "") -> ft.Container:
    k = _key(disposition)
    return status_chip(DISPOSITION_STYLE, k if k in DISPOSITION_STYLE else disposition, tooltip=tooltip)


def data_table(columns: Sequence[str], rows: Sequence[Sequence], *, numeric_from: Optional[int] = None,
               wide_last: bool = False, row_height: int = 36) -> ft.DataTable:
    """The one DataTable helper. A cell is an `ft.Control` (placed as is, e.g. a chip) or a value shown as text
    ("—" for None). `numeric_from` right-aligns that column and every one after it; `wide_last` gives the last
    column 460 px and taller rows. Wrap in `ft.Row([t], scroll=ft.ScrollMode.AUTO)` where it may be wide."""
    pal = active()
    bad = [i for i, r in enumerate(rows) if len(r) != len(columns)]
    if bad:                                  # a ragged row is a paint-time crash in Flutter: refuse at build time
        raise ValueError(f"data_table: rows {bad[:5]} do not have {len(columns)} cells")
    last = len(columns) - 1

    def cell(i: int, v) -> ft.DataCell:
        if isinstance(v, ft.Control):
            return ft.DataCell(v)
        return ft.DataCell(ft.Text("—" if v is None else str(v), size=12, color=pal.text, selectable=True,
                                   width=460 if wide_last and i == last else None))

    return ft.DataTable(
        columns=[ft.DataColumn(ft.Text(c, size=12, color=pal.muted),
                               numeric=numeric_from is not None and i >= numeric_from)
                 for i, c in enumerate(columns)],
        rows=[ft.DataRow(cells=[cell(i, v) for i, v in enumerate(r)]) for r in rows],
        column_spacing=16, heading_row_height=34,
        data_row_min_height=row_height, data_row_max_height=88 if wide_last else row_height,
    )


def multiplier_bar(composed, vt, *, width: int = 260) -> ft.Control:
    """Track 0 -> 1.0 (the cap) with the fill at `composed`, a tick at `vt` and a tick at the floor 0.5 x vt,
    each printed as a number. Draws the artifact's values; computes no exposure. A missing, non-finite or
    out-of-[0, 1] value fails closed: an error notice and no numbers."""
    pal = active()
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0.0 <= x <= 1.0
               for x in (composed, vt)):
        return notice("Multiplier bar not drawn: composed or vt is missing or outside its bounds (fail closed).",
                      "error", icon=ft.Icons.ERROR_OUTLINE)
    floor, h = 0.5 * vt, 10

    def tick(x: float, colour: str, tip: str) -> ft.Container:
        return ft.Container(width=2, height=h + 8, bgcolor=colour, left=max(0.0, min(width - 2.0, x * width - 1)),
                            top=0, tooltip=tip)

    bar = ft.Stack([
        ft.Container(width=width, height=h, left=0, top=4, bgcolor=pal.surface_2,
                     border=ft.Border.all(1, pal.border), border_radius=RADII["sm"]),
        ft.Container(width=composed * width, height=h, left=0, top=4, bgcolor=pal.accent,
                     border_radius=RADII["sm"], tooltip=f"composed {composed:.2f}"),
        tick(floor, pal.warning, f"floor {floor:.2f} (0.5 × vt)"),
        tick(vt, pal.text, f"vt {vt:.2f}"),
    ], width=width, height=h + 8)
    labels = ft.Row([ft.Text(t, size=12, color=c) for t, c in (
        (f"composed {composed:.2f}", pal.text), (f"vt {vt:.2f}", pal.text),
        (f"floor {floor:.2f} (0.5 × vt)", pal.muted), ("cap 1.00", pal.muted))], spacing=12, wrap=True)
    return ft.Column([bar, labels], spacing=6)


def open_path(path) -> Optional[ft.Control]:
    """Open a local file or folder with the OS handler (operator-initiated). Returns None once handed to the OS;
    when the path is missing or cannot be opened, returns the path as selectable text for the caller to show."""
    p = Path(path)
    if p.exists():
        try:
            if os.name == "nt":
                os.startfile(str(p))          # noqa: S606 - operator-initiated
            else:
                subprocess.run(["xdg-open", str(p)], check=False)
            return None
        except Exception:
            pass
    return ft.Text(f"Not found or could not be opened: {p}", size=12, color=active().muted, selectable=True)
