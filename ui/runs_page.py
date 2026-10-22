"""Run history: what was executed, what it produced, and what it printed.

Artifacts live on disk under `~/.tradegen/runs/<run_id>/`, so this page is a
reader over that directory rather than a database view. That means a failed run
is still inspectable after NEXTGEN is closed, and an operator can hand the
folder to someone else without exporting anything.
"""
from __future__ import annotations

from typing import Optional

import flet as ft

from core.skills import runs
from core.theme import RADII, active
from ui.components import chip, empty_state, key_value, mono, open_path, run_status_chip, section


def build_runs_page(page: ft.Page) -> ft.Control:
    pal = active()
    records = runs.recent(limit=200)
    selected: dict[str, Optional[runs.RunRecord]] = {"run": None}
    list_host = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    detail_host = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    if not records:
        return ft.Column([
            section("Runs"),
            empty_state("No runs yet",
                        "Run a skill or a workflow and its transcript, exit code and "
                        "artifacts will be recorded here.",
                        icon=ft.Icons.HISTORY),
        ], spacing=14, expand=True)

    def open_folder(path) -> None:
        open_path(path)

    def row(record: runs.RunRecord) -> ft.Container:
        chosen = selected["run"] is not None and selected["run"].run_id == record.run_id
        return ft.Container(
            content=ft.Column([
                ft.Row([ft.Text(record.skill_id, size=13, weight=ft.FontWeight.W_600,
                                color=pal.text, expand=True, max_lines=1),
                        run_status_chip(record.status)], spacing=8),
                ft.Row([ft.Text(record.started_at, size=11, color=pal.muted),
                        ft.Text(f"{record.duration_s:.1f}s", size=11, color=pal.muted),
                        chip(record.workflow_id, "accent") if record.workflow_id else ft.Container()],
                       spacing=10),
            ], spacing=5),
            padding=12,
            bgcolor=pal.surface_2 if chosen else pal.surface,
            border=ft.Border.all(1, pal.accent if chosen else pal.border),
            border_radius=RADII["md"], ink=True,
            on_click=lambda e, r=record: select(r),
        )

    def select(record: runs.RunRecord) -> None:
        selected["run"] = record
        render()
        page.update()

    def render() -> None:
        list_host.controls = [row(r) for r in records]
        record = selected["run"]
        if record is None:
            detail_host.controls = [empty_state(
                "Select a run", "Transcripts and artifacts appear here.",
                icon=ft.Icons.RECEIPT_LONG_OUTLINED)]
            return
        transcript = record.transcript()
        detail_host.controls = [
            ft.Row([ft.Text(record.skill_id, size=20, weight=ft.FontWeight.BOLD,
                            color=pal.text, expand=True),
                    run_status_chip(record.status)]),
            ft.Column([
                key_value("Run id", record.run_id),
                key_value("Entrypoint", record.entrypoint),
                key_value("Workflow", record.workflow_id or "—"),
                key_value("Exit code", str(record.exit_code)),
                key_value("Started", record.started_at),
                key_value("Duration", f"{record.duration_s:.1f}s"),
                key_value("Error", record.error or "—"),
            ], spacing=6),
            ft.Row([
                ft.Button("Open run folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                          on_click=lambda e: open_folder(record.run_dir)),
                ft.Text(str(record.run_dir), size=11, color=pal.muted, selectable=True),
            ], spacing=10, wrap=True),
            ft.Divider(color=pal.border),
            ft.Text(f"Artifacts ({len(record.artifacts)})", size=14,
                    weight=ft.FontWeight.W_600, color=pal.text),
            ft.Row([chip(name) for name in record.artifacts] or
                   [ft.Text("This run wrote no files.", size=12, color=pal.muted)],
                   spacing=6, wrap=True),
            ft.Divider(color=pal.border),
            ft.Text("Transcript", size=14, weight=ft.FontWeight.W_600, color=pal.text),
            ft.Container(
                ft.Column([mono(line) for line in transcript.splitlines()[-500:]] or
                          [ft.Text("(empty)", size=12, color=pal.muted)],
                          spacing=2, scroll=ft.ScrollMode.AUTO, height=320),
                padding=12, bgcolor=pal.bg, border=ft.Border.all(1, pal.border),
                border_radius=RADII["md"]),
        ]

    render()

    return ft.Column([
        section("Runs", subtitle=f"{len(records)} recorded runs"),
        ft.ResponsiveRow([
            ft.Container(list_host, col={"xs": 12, "md": 5, "lg": 4}),
            ft.Container(detail_host, col={"xs": 12, "md": 7, "lg": 8}, padding=16,
                         bgcolor=pal.surface, border=ft.Border.all(1, pal.border),
                         border_radius=RADII["lg"]),
        ], spacing=12, run_spacing=12, expand=True),
    ], spacing=14, expand=True)
