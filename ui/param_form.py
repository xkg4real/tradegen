"""A generated input form for one skill script's command line.

The cockpit used to offer a single free-text "Arguments" box. That is only
usable by someone who already knows the flags, which is nobody on first
contact, and it is why twenty-five skills failed in a sixth of a second with
`exit code 2`: the operator had no way to discover that `--query` was
mandatory, and readiness cheerfully called the skill Ready.

This module turns `core.skills.params.Spec` into real controls — one per
argument, required ones first, with the script's own help text as the hint. The
form knows what is still missing, so Run can be disabled before the process is
spawned rather than after it has already failed.

DESIGN NOTES
------------
* **Nothing is invented.** Every field, its default, its choices and its help
  string come from the script's source. Where the parser cannot be read
  statically the form says so and falls back to the raw box, rather than
  presenting an empty form that implies the script takes no arguments.

* **The raw box stays.** Generated fields cover the declared arguments; the
  escape hatch covers everything else (a flag added since, an odd nargs form).
  Whatever is typed there is appended verbatim.

* **Path fields get a picker.** `--input`, `--tickets-dir` and friends are the
  arguments an operator is least able to type from memory. In web mode the
  platform picker returns no filesystem path, so the button reports that
  instead of silently doing nothing.

* **A failed run points at the field that caused it.** `highlight()` takes the
  flags from a `Diagnosis` and marks exactly those controls, which closes the
  loop between the error message and the thing to change.
"""
from __future__ import annotations

import shlex
from typing import Callable, Optional

import flet as ft

from core.skills.params import Kind, Param, Spec
from core.theme import RADII, active

_PLACEHOLDER = {
    Kind.FILE: "path to a file",
    Kind.DIR: "path to a folder",
    Kind.INTEGER: "whole number",
    Kind.NUMBER: "number",
}

# Flet 0.85 spells the sub-label differently per control: TextField takes
# `helper`, Dropdown takes `helper_text`. Setting the wrong one is accepted
# silently at construction and then does nothing, so ask the control.
_HELPER_ATTRS = ("helper", "helper_text")


def _set_helper(control: ft.Control, text: Optional[str]) -> None:
    for attr in _HELPER_ATTRS:
        if hasattr(control, attr):
            setattr(control, attr, text)
            return


def _get_helper(control: ft.Control) -> str:
    for attr in _HELPER_ATTRS:
        if hasattr(control, attr):
            return str(getattr(control, attr) or "")
    return ""


class ParamForm:
    """Controls for one `Spec`, plus the state needed to launch it."""

    def __init__(self, page: ft.Page, spec: Spec, *,
                 on_change: Optional[Callable[[], None]] = None,
                 initial: Optional[dict] = None) -> None:
        self.page = page
        self.spec = spec
        self._on_change = on_change
        self._values: dict[str, str] = dict(initial or {})
        self._fields: dict[str, ft.Control] = {}
        self._subcommand: Optional[str] = None
        self._picker: Optional[ft.FilePicker] = None
        self.pal = active()

        self.raw = ft.TextField(
            label="Additional arguments (optional)",
            hint_text="anything not listed above, passed through verbatim",
            dense=True, expand=True, border_radius=RADII["md"],
            on_change=self._changed)
        self.body = ft.Column(spacing=10)
        if spec.subcommands:
            self._subcommand = spec.subcommands[0]
        self._rebuild()

    # -- public surface ------------------------------------------------------
    @property
    def control(self) -> ft.Control:
        return self.body

    @property
    def subcommand(self) -> Optional[str]:
        return self._subcommand

    def values(self) -> dict:
        return dict(self._values)

    def missing(self) -> tuple[str, ...]:
        return self.spec.missing(self._values, self._subcommand)

    def argv(self) -> tuple[str, ...]:
        composed = list(self.spec.build_argv(self._values, self._subcommand))
        extra = (self.raw.value or "").strip()
        if extra:
            try:
                composed.extend(shlex.split(extra))
            except ValueError:
                composed.extend(extra.split())
        return tuple(composed)

    def preview(self) -> str:
        argv = self.argv()
        return " ".join(shlex.quote(a) for a in argv) if argv else "(no arguments)"

    def highlight(self, flags: tuple[str, ...]) -> None:
        """Mark the fields a failed run blamed; clear every other mark."""
        wanted = {f.lstrip("-").replace("-", "_") for f in flags}
        for param in self.spec.for_subcommand(self._subcommand):
            control = self._fields.get(param.dest)
            if control is None or not hasattr(control, "border_color"):
                continue
            blamed = param.dest in wanted
            control.border_color = self.pal.error if blamed else None
            if blamed:
                _set_helper(control, "named by the last failure")
            elif _get_helper(control) == "named by the last failure":
                _set_helper(control, param.help[:110] or None)

    # -- construction --------------------------------------------------------
    def _changed(self, e=None) -> None:
        if self._on_change is not None:
            self._on_change()

    def _set(self, dest: str, value) -> None:
        self._values[dest] = "" if value is None else str(value)
        self._changed()

    def _ensure_picker(self) -> Optional[ft.FilePicker]:
        if self._picker is None:
            try:
                self._picker = ft.FilePicker()
                self.page.services.append(self._picker)
                self.page.update()
            except Exception:
                self._picker = None
        return self._picker

    def _browse(self, param: Param, field: ft.TextField) -> Callable:
        def handler(e=None) -> None:
            picker = self._ensure_picker()
            if picker is None:
                _set_helper(field, "file picker unavailable — type the path")
                self.page.update()
                return
            try:
                if param.kind is Kind.DIR:
                    chosen = picker.get_directory_path(
                        dialog_title=f"Select a folder for {param.flag}")
                    path = chosen or ""
                else:
                    files = picker.pick_files(
                        dialog_title=f"Select a file for {param.flag}",
                        allow_multiple=False)
                    path = (files[0].path or "") if files else ""
                    if files and not path:
                        # Web mode never exposes a filesystem path, and the
                        # skill subprocess can only take a path.
                        _set_helper(field, "this build cannot read the file's "
                                           "path — type it instead")
                        self.page.update()
                        return
            except Exception as exc:
                _set_helper(field, f"picker failed: {type(exc).__name__}")
                self.page.update()
                return
            if path:
                field.value = path
                field.border_color = None
                _set_helper(field, param.help[:110] or None)
                self._set(param.dest, path)
            self.page.update()
        return handler

    def _field_for(self, param: Param) -> ft.Control:
        pal = self.pal
        current = self._values.get(param.dest, param.default or "")
        label = param.label + (" *" if param.required else "")
        helper = param.help[:110] or None

        if param.kind is Kind.FLAG:
            box = ft.Checkbox(
                label=param.label,
                value=str(current).strip().lower() in ("1", "true", "yes", "on"),
                on_change=lambda e, d=param.dest: self._set(
                    d, "true" if e.control.value else ""))
            self._fields[param.dest] = box
            row = [box]
            if param.help:
                row.append(ft.Text(param.help[:110], size=11, color=pal.muted,
                                   expand=True))
            return ft.Row(row, spacing=10)

        if param.kind is Kind.CHOICE:
            dropdown = ft.Dropdown(
                label=label, value=str(current) or None, expand=True,
                options=[ft.dropdown.Option(c, c) for c in param.choices],
                on_select=lambda e, d=param.dest: self._set(d, e.control.value))
            _set_helper(dropdown, helper)
            self._fields[param.dest] = dropdown
            return dropdown

        field = ft.TextField(
            label=label, value=str(current), dense=True, expand=True,
            border_radius=RADII["md"],
            hint_text=_PLACEHOLDER.get(param.kind, ""),
            keyboard_type=(ft.KeyboardType.NUMBER
                           if param.kind in (Kind.INTEGER, Kind.NUMBER)
                           else ft.KeyboardType.TEXT),
            on_change=lambda e, d=param.dest: self._set(d, e.control.value))
        _set_helper(field, helper)
        self._fields[param.dest] = field
        if current:
            self._values.setdefault(param.dest, str(current))

        if param.wants_path:
            return ft.Row([
                field,
                ft.Button("Browse", icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                          on_click=self._browse(param, field)),
            ], spacing=8)
        return field

    def _rebuild(self) -> None:
        pal = self.pal
        self._fields = {}
        blocks: list[ft.Control] = []

        if not self.spec.parsed:
            blocks.append(ft.Container(
                ft.Row([
                    ft.Icon(ft.Icons.HELP_OUTLINE, size=16, color=pal.accent),
                    ft.Text("This script does not use a readable argparse "
                            "definition, so its arguments cannot be listed. "
                            "Use Show --help, then type them below.",
                            size=12, color=pal.text, expand=True),
                ], spacing=8),
                padding=10, bgcolor=pal.bg, border_radius=RADII["md"],
                border=ft.Border.all(1, pal.border)))
            blocks.append(self.raw)
            self.body.controls = blocks
            return

        if self.spec.subcommands:
            picker = ft.Dropdown(
                label=(self.spec.subcommand_dest or "command") + " *",
                value=self._subcommand, width=260,
                options=[ft.dropdown.Option(s, s) for s in self.spec.subcommands],
                on_select=self._pick_subcommand)
            blocks.append(ft.Row([
                picker,
                ft.Text("Each command takes its own arguments.",
                        size=11, color=pal.muted, expand=True),
            ], spacing=10))

        active_params = self.spec.for_subcommand(self._subcommand)
        required = [p for p in active_params if p.required or p.group]
        optional = [p for p in active_params if not (p.required or p.group)]

        if required:
            blocks.append(ft.Text("Required", size=12, weight=ft.FontWeight.W_600,
                                  color=pal.text))
            groups_noted: set[str] = set()
            for param in required:
                group = self.spec.group_for(param)
                if group is not None and group.id not in groups_noted:
                    groups_noted.add(group.id)
                    members = [p.flag for p in active_params if p.group == group.id]
                    blocks.append(ft.Text(
                        ("Provide one of: " if group.required else "At most one of: ")
                        + ", ".join(members), size=11, color=pal.muted))
                blocks.append(self._field_for(param))

        if optional:
            blocks.append(ft.ExpansionTile(
                title=ft.Text(f"Optional arguments ({len(optional)})",
                              size=12, weight=ft.FontWeight.W_600, color=pal.text),
                controls=[ft.Container(
                    ft.Column([self._field_for(p) for p in optional], spacing=10),
                    padding=ft.Padding(4, 4, 4, 12))],
                expanded=False,
            ))

        blocks.append(self.raw)
        self.body.controls = blocks

    def _pick_subcommand(self, e) -> None:
        self._subcommand = e.control.value or None
        self._rebuild()
        self._changed()
        self.page.update()
