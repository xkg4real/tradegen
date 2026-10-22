"""Skills catalogue: browse 72 skills, see why one cannot run, run one.

The list is the cheap part. The two things that earn their keep here are:

  * **Readiness is computed, not asserted.** Each card says Ready / Needs input
    / Key required / Reference only, derived from the skill's own declared
    integrations joined against the credentials actually present. A blocked card
    names the missing environment variable instead of saying "unavailable".

  * **Arguments come from the script, not from a guess.** The run panel reads
    the entrypoint's argparse definition and renders one field per argument,
    with the script's own help text. Run stays disabled until the required
    ones are filled, so a skill can no longer fail in a sixth of a second for
    a reason the operator had no way to see. `Show --help` remains for the two
    scripts whose parser cannot be read statically.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

import flet as ft

from core.skills import runner, runs
from core.skills.diagnose import Cause
from core.skills.entrypoints import Entrypoint, entrypoints
from core.skills.index import SkillMeta, all_skills, categories
from core.skills.params import spec_for
from core.skills.readiness import State, evaluate
from core.theme import RADII, active
from ui.components import (card, chip, colour_for, empty_state, key_value, mono,
                           notice, readiness_chip, run_status_chip, section)
from ui.param_form import ParamForm

# How a finished run is presented. A screener that matched nothing has not
# malfunctioned, so it must not be painted the same red as a crash; a missing
# argument is the operator's next action, not a fault, so it reads as guidance.
_CAUSE_TOKEN: dict[Cause, str] = {
    Cause.OK: "success",
    Cause.NO_RESULTS: "muted",
    Cause.CANCELLED: "muted",
    Cause.MISSING_ARGS: "accent",
    Cause.INVALID_ARG: "accent",
    Cause.MISSING_INPUT: "accent",
    Cause.MISSING_KEY: "accent",
    Cause.PLAN_LIMIT: "accent",
    Cause.RATE_LIMIT: "accent",
}

_ICON_FOR: dict[Cause, str] = {
    Cause.OK: ft.Icons.CHECK_CIRCLE_OUTLINE,
    Cause.NO_RESULTS: ft.Icons.INBOX_OUTLINED,
    Cause.CANCELLED: ft.Icons.STOP_CIRCLE_OUTLINED,
    Cause.MISSING_ARGS: ft.Icons.EDIT_NOTE_OUTLINED,
    Cause.INVALID_ARG: ft.Icons.EDIT_NOTE_OUTLINED,
    Cause.MISSING_INPUT: ft.Icons.FOLDER_OFF_OUTLINED,
    Cause.MISSING_KEY: ft.Icons.KEY_OFF_OUTLINED,
    Cause.PLAN_LIMIT: ft.Icons.LOCK_OUTLINE,
    Cause.RATE_LIMIT: ft.Icons.HOURGLASS_EMPTY,
    Cause.NETWORK: ft.Icons.WIFI_OFF_OUTLINED,
    Cause.TIMEOUT: ft.Icons.TIMER_OFF_OUTLINED,
    Cause.CRASH: ft.Icons.BUG_REPORT_OUTLINED,
}


def build_skills_page(page: ft.Page, *, on_open_settings: Optional[Callable] = None,
                      focus_skill: str = "") -> ft.Control:
    pal = active()
    skills = all_skills()
    selected: dict[str, Optional[SkillMeta]] = {"skill": None}
    filters = {"query": "", "category": "all", "state": "all"}

    detail_host = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
    list_host = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    count_label = ft.Text("", size=12, color=pal.muted)

    if not skills:
        return _repo_missing(on_open_settings)

    # ---------------------------------------------------------------- filters
    def matches(skill: SkillMeta) -> bool:
        query = filters["query"].strip().casefold()
        if query and query not in f"{skill.display_name} {skill.id} {skill.summary}".casefold():
            return False
        if filters["category"] != "all" and skill.category != filters["category"]:
            return False
        if filters["state"] != "all" and evaluate(skill).state.value != filters["state"]:
            return False
        return True

    def render_list() -> None:
        visible = [s for s in skills if matches(s)]
        count_label.value = f"{len(visible)} of {len(skills)} skills"
        list_host.controls = [_row(s) for s in visible] or [
            ft.Container(ft.Text("No skill matches those filters.", size=13,
                                 color=pal.muted), padding=24)
        ]

    def _row(skill: SkillMeta) -> ft.Container:
        readiness = evaluate(skill)
        chosen = selected["skill"] is not None and selected["skill"].id == skill.id
        body = ft.Column([
            ft.Row([
                ft.Text(skill.display_name, size=13, weight=ft.FontWeight.W_600,
                        color=pal.text, expand=True, max_lines=1),
                readiness_chip(readiness.state),
            ], spacing=8),
            ft.Text(skill.summary or skill.id, size=11, color=pal.muted, max_lines=2),
        ], spacing=5)
        return ft.Container(
            content=body, padding=12,
            bgcolor=pal.surface_2 if chosen else pal.surface,
            border=ft.Border.all(1, pal.accent if chosen else pal.border),
            border_radius=RADII["md"], ink=True,
            on_click=lambda e, s=skill: select(s),
        )

    def select(skill: SkillMeta) -> None:
        selected["skill"] = skill
        render_list()
        render_detail()
        page.update()

    # ---------------------------------------------------------------- detail
    def render_detail() -> None:
        skill = selected["skill"]
        if skill is None:
            detail_host.controls = [empty_state(
                "Select a skill",
                "Pick a skill on the left to see what it needs, what it produces, "
                "and the arguments its own --help declares.",
                icon=ft.Icons.EXTENSION_OUTLINED)]
            return

        readiness = evaluate(skill)
        eps = entrypoints(skill.id, skill.directory)
        blocks: list[ft.Control] = [
            ft.Row([
                ft.Text(skill.display_name, size=22, weight=ft.FontWeight.BOLD,
                        color=pal.text, expand=True),
                readiness_chip(readiness.state),
            ]),
            ft.Text(skill.summary, size=13, color=pal.muted, selectable=True),
            ft.Row([chip(skill.category or "uncategorised"),
                    chip(skill.status or "unknown"),
                    chip(skill.timeframe or "—"),
                    chip(skill.difficulty or "—")], spacing=6, wrap=True),
        ]

        if readiness.state is State.MISSING_KEY:
            blocks.append(notice(
                "Blocked: set " + ", ".join(readiness.missing_credentials) +
                f" to enable {', '.join(readiness.missing_providers)}.",
                "error", icon=ft.Icons.KEY_OFF_OUTLINED,
                action=ft.Button("Open Settings",
                                 on_click=lambda e: on_open_settings and on_open_settings())
                if on_open_settings else None))
            if readiness.undeclared:
                # Without this note the card contradicts the Integrations row
                # below it, and the operator has no way to tell which is right.
                blocks.append(notice(
                    "skills-index.yaml does not declare " +
                    ", ".join(readiness.undeclared) +
                    ", but this skill's scripts read it. Requirement detected "
                    "from the code.",
                    "accent", icon=ft.Icons.FACT_CHECK_OUTLINED))
        elif readiness.state is State.NEEDS_INPUT:
            wants = []
            if readiness.required_arguments:
                wants.append("required arguments: "
                             + ", ".join(readiness.required_arguments))
            if readiness.input_integrations:
                wants.append("a file you supply ("
                             + ", ".join(readiness.input_integrations) + ")")
            if readiness.arguments_unknown:
                wants.append("arguments this build cannot read statically")
            blocks.append(notice(
                "Before this runs it needs " + "; ".join(wants)
                + ". The form below asks for them.",
                "accent", icon=ft.Icons.UPLOAD_FILE_OUTLINED))
        elif readiness.state is State.DOC_ONLY:
            blocks.append(notice(
                "Reference skill: it ships instructions, not a runnable script. "
                "Open SKILL.md to read it.",
                "muted", icon=ft.Icons.MENU_BOOK_OUTLINED))
        for warning in readiness.warnings:
            blocks.append(notice(warning, "accent", icon=ft.Icons.WARNING_AMBER_OUTLINED))

        blocks.append(ft.Divider(color=pal.border))
        blocks.append(ft.Column([
            key_value("Skill id", skill.id),
            key_value("Consumes", ", ".join(skill.inputs) or "—"),
            key_value("Produces", ", ".join(skill.outputs) or "—"),
            key_value("Integrations",
                      ", ".join(f"{i.id} ({i.requirement})" for i in skill.integrations) or "—"),
            key_value("Workflows", ", ".join(skill.workflows) or "—"),
            key_value("Location", str(skill.directory)),
        ], spacing=6))

        if eps:
            blocks.append(ft.Divider(color=pal.border))
            blocks.append(_run_panel(skill, eps))

        last = runs.latest_for_skill(skill.id)
        if last is not None:
            blocks.append(ft.Divider(color=pal.border))
            blocks.append(ft.Row([
                ft.Text("Last run", size=13, weight=ft.FontWeight.W_600, color=pal.text),
                run_status_chip(last.status),
                ft.Text(last.finished_at, size=11, color=pal.muted),
            ], spacing=10))

        detail_host.controls = blocks

    def _run_panel(skill: SkillMeta, eps: tuple[Entrypoint, ...]) -> ft.Control:
        """The run panel: a form built from the script's own argument list.

        Run stays disabled until every required argument is filled, which is
        the whole point — the alternative is the sub-second `exit code 2` that
        made these skills look broken rather than unconfigured.
        """
        script = ft.Dropdown(
            label="Script", width=280, value=eps[0].name,
            options=[ft.dropdown.Option(e.name, e.label + (" (primary)" if e.primary else ""))
                     for e in eps])
        console = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=240)
        status_row = ft.Row(spacing=8, wrap=True)
        verdict_host = ft.Column(spacing=4)
        form_host = ft.Column(spacing=10)
        preview = mono("", size=11)
        blocker = ft.Text("", size=11, color=pal.error)
        run_button = ft.Button("Run", icon=ft.Icons.PLAY_ARROW_ROUNDED)
        state: dict = {"handle": None, "form": None}

        def chosen_entry() -> Entrypoint:
            return next((x for x in eps if x.name == script.value), eps[0])

        def refresh() -> None:
            form: Optional[ParamForm] = state.get("form")
            if form is None:
                return
            gaps = form.missing()
            run_button.disabled = bool(gaps)
            blocker.value = ("Still needed: " + ", ".join(gaps)) if gaps else ""
            preview.value = f"{chosen_entry().name} {form.preview()}"
            try:
                page.update()
            except Exception:
                pass

        def build_form(e=None) -> None:
            entry = chosen_entry()
            form = ParamForm(page, spec_for(entry.path), on_change=refresh)
            state["form"] = form
            form_host.controls = [form.control]
            verdict_host.controls = []
            refresh()

        def show_help(e=None) -> None:
            entry = chosen_entry()
            console.controls = [mono("loading --help …")]
            page.update()

            def worker():
                text = runner.describe_args(entry)
                console.controls = [mono(line) for line in text.splitlines()[:200]]
                page.update()
            page.run_thread(worker)

        def stop(e=None) -> None:
            handle = state.get("handle")
            if handle is not None:
                handle.cancel()

        def report(result) -> None:
            """Say what happened in words, and point at the field to change."""
            verdict = result.diagnosis
            token = _CAUSE_TOKEN.get(result.cause, "error")
            colour = colour_for(token)
            verdict_host.controls = [
                ft.Row([ft.Icon(_ICON_FOR.get(result.cause,
                                              ft.Icons.ERROR_OUTLINE),
                                size=16, color=colour),
                        ft.Text(result.headline, size=12, color=colour,
                                selectable=True, expand=True)], spacing=8),
            ]
            if verdict is not None and verdict.detail:
                verdict_host.controls.append(
                    ft.Text(verdict.detail, size=11, color=pal.muted))
            if verdict is not None and verdict.excerpt and not verdict.benign:
                verdict_host.controls.append(ft.Container(
                    ft.Column([mono(line, size=10) for line in verdict.excerpt],
                              spacing=1),
                    padding=8, bgcolor=pal.bg, border_radius=RADII["sm"],
                    border=ft.Border.all(1, pal.border)))
            form: Optional[ParamForm] = state.get("form")
            if form is not None:
                form.highlight(verdict.fields if verdict else ())

        def start(e=None) -> None:
            form: Optional[ParamForm] = state.get("form")
            entry = chosen_entry()
            argv = list(form.argv()) if form is not None else []
            handle = runner.RunHandle()
            state["handle"] = handle
            console.controls = []
            verdict_host.controls = []
            status_row.controls = [run_status_chip("running"),
                                   ft.ProgressRing(width=16, height=16),
                                   ft.Button("Stop", icon=ft.Icons.STOP_CIRCLE_OUTLINED,
                                             on_click=stop)]
            page.update()

            def on_line(line: str) -> None:
                console.controls.append(mono(line))
                del console.controls[:-400]          # bound the transcript in memory
                try:
                    page.update()
                except Exception:
                    pass

            def worker():
                result = runner.run_skill(entry, argv, on_line=on_line, handle=handle)
                runs.record(result)
                status_row.controls = [
                    run_status_chip(result.status),
                    ft.Text(f"{result.duration_s:.1f}s", size=11, color=pal.muted),
                ]
                if result.artifacts:
                    status_row.controls.append(
                        ft.Text(f"{len(result.artifacts)} artifact(s) in {result.run_dir}",
                                size=11, color=pal.muted, selectable=True))
                report(result)
                state["handle"] = None
                page.update()

            page.run_thread(worker)

        script.on_select = build_form
        run_button.on_click = start
        build_form()

        return ft.Column([
            ft.Text("Run", size=15, weight=ft.FontWeight.W_600, color=pal.text),
            ft.Row([script,
                    ft.Button("Show --help", icon=ft.Icons.HELP_OUTLINE,
                              on_click=show_help)],
                   spacing=10, wrap=True),
            form_host,
            ft.Container(preview, padding=8, bgcolor=pal.bg,
                         border=ft.Border.all(1, pal.border),
                         border_radius=RADII["sm"]),
            ft.Row([blocker, run_button], spacing=12,
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            status_row,
            verdict_host,
            ft.Container(console, padding=12, bgcolor=pal.bg,
                         border=ft.Border.all(1, pal.border), border_radius=RADII["md"]),
        ], spacing=10)

    # ---------------------------------------------------------------- chrome
    search = ft.TextField(hint_text="Search skills", expand=True, dense=True,
                          prefix_icon=ft.Icons.SEARCH, border_radius=RADII["md"])
    category_dd = ft.Dropdown(label="Category", width=190, value="all",
                              options=[ft.dropdown.Option("all", "All categories")] +
                                      [ft.dropdown.Option(c, c) for c in categories()])
    state_dd = ft.Dropdown(label="Readiness", width=170, value="all",
                           options=[ft.dropdown.Option("all", "Any state"),
                                    ft.dropdown.Option("ready", "Ready"),
                                    ft.dropdown.Option("needs_input", "Needs input"),
                                    ft.dropdown.Option("missing_key", "Key required"),
                                    ft.dropdown.Option("doc_only", "Reference only")])

    def on_filter(e=None) -> None:
        filters["query"] = search.value or ""
        filters["category"] = category_dd.value or "all"
        filters["state"] = state_dd.value or "all"
        render_list()
        page.update()

    search.on_change = on_filter
    category_dd.on_select = on_filter
    state_dd.on_select = on_filter

    if focus_skill:
        match = next((s for s in skills if s.id == focus_skill), None)
        if match is not None:
            selected["skill"] = match

    render_list()
    render_detail()

    left = ft.Container(
        content=ft.Column([
            ft.Row([search], spacing=8),
            ft.Row([category_dd, state_dd], spacing=8, wrap=True),
            count_label,
            list_host,
        ], spacing=10, expand=True),
        col={"xs": 12, "md": 5, "lg": 4}, padding=ft.Padding(0, 0, 8, 0),
    )
    right = ft.Container(
        content=detail_host, col={"xs": 12, "md": 7, "lg": 8},
        padding=16, bgcolor=pal.surface, border=ft.Border.all(1, pal.border),
        border_radius=RADII["lg"],
    )

    return ft.Column([
        section("Skills", subtitle=f"{len(skills)} skills from your local trading-skills repository"),
        ft.ResponsiveRow([left, right], spacing=12, run_spacing=12, expand=True),
    ], spacing=14, expand=True)


def _repo_missing(on_open_settings: Optional[Callable]) -> ft.Control:
    import config
    return ft.Column([
        section("Skills"),
        empty_state(
            "No skills repository found",
            f"Expected skills-index.yaml under {config.skills_root()}.\n"
            "Set NEXTGEN_SKILLS_ROOT in .env to point at your clone.",
            icon=ft.Icons.FOLDER_OFF_OUTLINED,
            action=ft.Button("Open Settings",
                             on_click=lambda e: on_open_settings and on_open_settings())
            if on_open_settings else None),
    ], spacing=14, expand=True)
