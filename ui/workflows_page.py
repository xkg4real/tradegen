"""Workflows: the multi-skill pipelines, run step by step with human gates.

This is the page the cockpit exists for. A workflow is not a script — it is an
ordered set of skills where later steps consume artifacts earlier steps made,
and where some steps end in a judgement a person has to make.

Four behaviours are non-negotiable here:

  * **`when_not_to_run` is shown before the Run button, not after.** Every
    workflow in the repository carries the author's own caveat, usually a
    variant of "this output is a posture, not a buy/sell signal". Burying it in
    a detail pane would be a misrepresentation of the thing being run.

  * **A `decision_gate` step halts the run.** The runner stops, shows the
    step's `decision_question`, and waits. Racing past a gate would turn a
    deliberately human-in-the-loop pipeline into an autopilot, which is
    precisely what these workflows are written not to be.

  * **The gate shows what the earlier steps found.** "Is new swing trade risk
    allowed, restricted, or cash-priority?" is unanswerable from a scroll-back
    of four hundred transcript lines, so the steps whose artifacts this one
    consumes are summarised right above the question — score, zone, and every
    component that went into them.

  * **The buttons are the question's own answers.** A gate asking for allowed /
    restricted / cash-priority offers those three, read verbatim out of
    `decision_question` by `core.skills.decisions`. Where a question does not
    name a closed set — most do not — the gate takes a written answer instead
    of pretending two generic buttons will do.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import flet as ft

from core.skills import insights, runner, runs, wiring
from core.skills.decisions import options_for
from core.skills.entrypoints import primary
from core.skills.index import by_id as skill_by_id
from core.skills.insights import Insight
from core.skills.params import spec_for
from core.skills.readiness import State, evaluate
from core.skills.workflows import Step, WorkflowMeta, all_workflows
from core.theme import RADII, active
from ui.charts import insight_chart
from ui.components import (card, chip, colour_for, empty_state, key_value, mono,
                           notice, readiness_chip, run_status_chip, section)
from ui.param_form import ParamForm


def build_workflows_page(page: ft.Page, *,
                         on_open_settings: Optional[Callable] = None,
                         on_open_skill: Optional[Callable] = None) -> ft.Control:
    pal = active()
    workflows = all_workflows()
    if not workflows:
        return ft.Column([
            section("Workflows"),
            empty_state("No workflows found",
                        "Expected workflows/*.yaml in the trading-skills repository.",
                        icon=ft.Icons.ACCOUNT_TREE_OUTLINED),
        ], spacing=14, expand=True)

    selected: dict[str, Optional[WorkflowMeta]] = {"wf": None}
    detail_host = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
    grid = ft.ResponsiveRow(spacing=12, run_spacing=12)

    def coverage(wf: WorkflowMeta) -> tuple[int, int, list[str]]:
        """(runnable, total, blockers) across the workflow's required steps."""
        ready = 0
        blockers: list[str] = []
        required = [s for s in wf.steps if not s.optional]
        for step in required:
            meta = skill_by_id(step.skill)
            if meta is None:
                blockers.append(f"{step.skill} (not in index)")
                continue
            verdict = evaluate(meta)
            if verdict.runnable:
                ready += 1
            elif verdict.state is State.MISSING_KEY:
                blockers.extend(verdict.missing_credentials)
            else:
                blockers.append(f"{step.skill} ({verdict.state.value})")
        return ready, len(required), list(dict.fromkeys(blockers))

    # ------------------------------------------------------------------ grid
    def render_grid() -> None:
        grid.controls = []
        for wf in workflows:
            ready, total, blockers = coverage(wf)
            token = "success" if ready == total else ("error" if ready == 0 else "accent")
            body = ft.Column([
                ft.Row([ft.Text(wf.display_name, size=15, weight=ft.FontWeight.W_600,
                                color=pal.text, expand=True),
                        chip(f"{ready}/{total} ready", token)], spacing=8),
                ft.Text(wf.when_to_run or "—", size=12, color=pal.muted, max_lines=3),
                ft.Row([chip(wf.cadence or "—"), chip(wf.api_profile or "—"),
                        chip(f"{len(wf.steps)} steps"),
                        chip(f"{len(wf.decision_gates)} gates"),
                        chip(f"~{wf.estimated_minutes}m" if wf.estimated_minutes else "—")],
                       spacing=6, wrap=True),
            ], spacing=8)
            grid.controls.append(card(body, on_click=lambda e, w=wf: select(w),
                                      col={"xs": 12, "md": 6, "xl": 4}))

    def select(wf: WorkflowMeta) -> None:
        selected["wf"] = wf
        render_detail()
        page.update()

    # ---------------------------------------------------------------- detail
    def render_detail() -> None:
        wf = selected["wf"]
        if wf is None:
            detail_host.controls = []
            return
        ready, total, blockers = coverage(wf)
        blocks: list[ft.Control] = [
            ft.Row([ft.Text(wf.display_name, size=22, weight=ft.FontWeight.BOLD,
                            color=pal.text, expand=True),
                    ft.IconButton(ft.Icons.CLOSE, tooltip="Close",
                                  on_click=lambda e: select_none())]),
        ]

        # The author's own guardrail, before anything can be launched.
        if wf.when_not_to_run:
            blocks.append(notice(wf.when_not_to_run, "error",
                                 icon=ft.Icons.REPORT_GMAILERRORRED_OUTLINED))
        if wf.when_to_run:
            blocks.append(notice(wf.when_to_run, "accent",
                                 icon=ft.Icons.SCHEDULE_OUTLINED))
        if blockers:
            blocks.append(notice(
                "Blocked: " + ", ".join(blockers[:6]),
                "error", icon=ft.Icons.KEY_OFF_OUTLINED,
                action=ft.Button("Settings",
                                 on_click=lambda e: on_open_settings and on_open_settings())
                if on_open_settings else None))

        blocks.append(ft.Column([
            key_value("Cadence", wf.cadence),
            key_value("API profile", wf.api_profile),
            key_value("Estimated", f"~{wf.estimated_minutes} min" if wf.estimated_minutes else "—"),
            key_value("Artifacts", ", ".join(a.id for a in wf.artifacts) or "—"),
            key_value("Journal to", wf.journal_destination or "—"),
        ], spacing=6))

        needs_input = _steps_needing_input(wf)
        if needs_input:
            blocks.append(notice(
                f"{len(needs_input)} of {len(wf.steps)} steps will ask for input "
                f"before they run: " + ", ".join(needs_input[:6])
                + ("…" if len(needs_input) > 6 else "")
                + ". The run pauses at each one.",
                "accent", icon=ft.Icons.EDIT_NOTE_OUTLINED))

        answered = _gates_with_options(wf)
        if wf.decision_gates:
            blocks.append(notice(
                f"{len(wf.decision_gates)} decision gate(s). "
                + (f"{answered} of them offer the answers the question names; "
                   if answered else "")
                + "the rest take a written answer. "
                  "Each gate summarises the steps it depends on.",
                "accent", icon=ft.Icons.PAN_TOOL_OUTLINED))

        blocks.append(ft.Divider(color=pal.border))
        blocks.append(_pipeline(wf))

        if wf.manual_review:
            blocks.append(ft.Divider(color=pal.border))
            blocks.append(ft.Text("Manual review", size=15, weight=ft.FontWeight.W_600,
                                  color=pal.text))
            blocks.extend(
                ft.Row([ft.Icon(ft.Icons.CHECK_BOX_OUTLINE_BLANK, size=15, color=pal.muted),
                        ft.Text(item, size=12, color=pal.muted, expand=True)], spacing=8)
                for item in wf.manual_review)

        detail_host.controls = blocks

    def _steps_needing_input(wf: WorkflowMeta) -> list[str]:
        """Steps whose script will not start without arguments.

        Surfaced before the Run button so a workflow's interactivity is known
        in advance: discovering one at a time mid-run is the worse experience.
        """
        names = []
        for step in wf.steps:
            meta = skill_by_id(step.skill)
            entry = primary(meta.id, meta.directory) if meta else None
            if entry is None:
                continue
            spec = spec_for(entry.path)
            if spec.needs_arguments or not spec.parsed:
                names.append(f"{step.step}. {step.skill}")
        return names

    def _gates_with_options(wf: WorkflowMeta) -> int:
        return sum(1 for s in wf.decision_gates
                   if options_for(s.decision_question).closed)

    def select_none() -> None:
        selected["wf"] = None
        detail_host.controls = []
        page.update()

    # -------------------------------------------------------------- pipeline
    def _pipeline(wf: WorkflowMeta) -> ft.Control:
        step_rows = ft.Column(spacing=8)
        state: dict = {"index": 0, "handle": None, "running": False,
                       "awaiting_gate": False, "awaiting_input": None,
                       "form": None, "gate_run_button": None, "gate_blocker": None,
                       # step number -> the arguments already supplied for it
                       "args": {},
                       # step number -> what that step concluded
                       "insights": {},
                       # step number -> the finished run, for its directory
                       "results": {},
                       # artifact id -> the file the producing step wrote
                       "produced": {},
                       # step number -> the operator's recorded answer
                       "decisions": {},
                       # step numbers whose chart the operator folded away
                       "collapsed": set()}
        console = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=220)
        controls_row = ft.Row(spacing=8)
        gate_host = ft.Column(spacing=8)

        # ------------------------------------------------------------ steps
        def toggle_chart(number: int) -> None:
            if number in state["collapsed"]:
                state["collapsed"].discard(number)
            else:
                state["collapsed"].add(number)
            render_steps()
            page.update()

        def step_control(step: Step, position: int) -> ft.Container:
            meta = skill_by_id(step.skill)
            verdict = evaluate(meta) if meta else None
            done = position < state["index"]
            active_step = position == state["index"] and state["running"]
            icon = (ft.Icons.CHECK_CIRCLE if done else
                    ft.Icons.PLAY_CIRCLE_FILL if active_step else
                    ft.Icons.RADIO_BUTTON_UNCHECKED)
            colour = pal.success if done else (pal.accent if active_step else pal.muted)
            tags = [chip("optional")] if step.optional else []
            if step.decision_gate:
                tags.append(chip("decision gate", "accent"))
            if verdict is not None:
                tags.append(readiness_chip(verdict.state))
            answer = state["decisions"].get(step.step)
            if answer:
                tags.append(chip(f"answered: {answer}", "success"))

            found: Optional[Insight] = state["insights"].get(step.step)
            header = ft.Row([
                ft.Icon(icon, size=18, color=colour),
                ft.Column([
                    ft.Row([ft.Text(f"{step.step}. {step.name}", size=13,
                                    weight=ft.FontWeight.W_600, color=pal.text),
                            *tags], spacing=6, wrap=True),
                    ft.Text(step.skill, size=11, color=pal.muted),
                    ft.Text("consumes: " + ", ".join(step.consumes), size=10,
                            color=pal.muted) if step.consumes else ft.Container(),
                    ft.Text(found.headline, size=11, color=colour_for(found.band),
                            weight=ft.FontWeight.W_500)
                    if found is not None and found.headline else ft.Container(),
                ], spacing=3, expand=True),
                ft.IconButton(
                    ft.Icons.EXPAND_MORE if step.step in state["collapsed"]
                    else ft.Icons.EXPAND_LESS,
                    icon_size=16,
                    tooltip="Show or hide this step's chart",
                    on_click=lambda e, n=step.step: toggle_chart(n),
                ) if found is not None else ft.Container(),
                ft.IconButton(ft.Icons.OPEN_IN_NEW, icon_size=15,
                              tooltip="Open skill",
                              on_click=lambda e, s=step: on_open_skill and on_open_skill(s.skill)),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

            body: list[ft.Control] = [header]
            if found is not None and step.step not in state["collapsed"]:
                chart = insight_chart(found)
                if chart is not None:
                    body.append(ft.Container(
                        chart, padding=ft.Padding(28, 10, 8, 4)))

            return ft.Container(
                content=ft.Column(body, spacing=4),
                padding=10,
                bgcolor=pal.surface_2 if active_step else pal.surface,
                border=ft.Border.all(1, pal.accent if active_step else pal.border),
                border_radius=RADII["md"],
            )

        def render_steps() -> None:
            step_rows.controls = [step_control(s, i) for i, s in enumerate(wf.steps)]

        def log(line: str) -> None:
            console.controls.append(mono(line))
            del console.controls[:-400]
            try:
                page.update()
            except Exception:
                pass

        def finish(message: str, token: str = "muted") -> None:
            state["running"] = False
            state["handle"] = None
            controls_row.controls = [
                ft.Button("Run workflow", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=start),
                chip(message, token),
            ]
            render_steps()
            page.update()

        # ------------------------------------------------------- input gate
        def show_input_gate(step: Step, index: int, entry, spec,
                            prefill: dict) -> None:
            """Pause and ask for this step's arguments before launching it.

            Workflow steps used to run with an empty command line uncondition-
            ally, so any step whose script requires an argument died instantly
            and took the workflow down with it. Asking here rather than up
            front keeps the question next to the step it belongs to.

            Anything the earlier steps already produced arrives pre-filled, in
            the visible field rather than behind it, so the operator can see and
            change what is about to be passed.
            """
            state["running"] = False
            state["awaiting_input"] = index
            remembered = state["args"].get(step.step, {}).get("values") or {}
            initial = {**prefill, **remembered}
            form = ParamForm(page, spec, on_change=lambda: refresh_gate(step, index),
                             initial=initial)
            state["form"] = form
            proceed = ft.Button("Run this step", icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                on_click=lambda e: accept_input(step, index, entry))
            skip = ft.Button("Skip step" if step.optional else "Stop here",
                             on_click=lambda e: (advance_after(step, index, ok=True)
                                                 if step.optional
                                                 else finish("stopped for input", "muted")))
            blocker = ft.Text("", size=11, color=pal.error, expand=True)
            state["gate_run_button"] = proceed
            state["gate_blocker"] = blocker

            heading = (f"Step {step.step} — {step.name} needs input before it can run."
                       if spec.needs_arguments or not spec.parsed
                       else f"Step {step.step} — {step.name} will read what the "
                            f"earlier steps produced. Review and run.")
            wired = [notice(
                "Filled in from earlier steps: "
                + ", ".join(f"{k} = {Path(v).name}" for k, v in prefill.items()),
                "success", icon=ft.Icons.LINK)] if prefill else []

            gate_host.controls = [ft.Container(
                ft.Column([
                    ft.Row([ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED, size=18,
                                    color=pal.accent),
                            ft.Text(heading, size=13, color=pal.text, expand=True)],
                           spacing=8),
                    *wired,
                    form.control,
                    ft.Row([blocker, skip, proceed], spacing=10),
                ], spacing=10),
                padding=14, bgcolor=pal.surface_2,
                border=ft.Border.all(1, pal.accent), border_radius=RADII["md"])]
            controls_row.controls = [chip("waiting for step input", "accent")]
            refresh_gate(step, index)
            render_steps()
            page.update()

        def refresh_gate(step: Step, index: int) -> None:
            form = state.get("form")
            button = state.get("gate_run_button")
            if form is None or button is None:
                return
            gaps = form.missing()
            button.disabled = bool(gaps)
            blocker = state.get("gate_blocker")
            if blocker is not None:
                blocker.value = ("Still needed: " + ", ".join(gaps)) if gaps else ""
            try:
                page.update()
            except Exception:
                pass

        def accept_input(step: Step, index: int, entry) -> None:
            form = state.get("form")
            argv = tuple(form.argv()) if form is not None else ()
            state["args"][step.step] = {"values": form.values() if form else {},
                                        "argv": argv}
            gate_host.controls = []
            state["awaiting_input"] = None
            state["running"] = True
            launch(step, index, entry, argv)

        # ----------------------------------------------------------- running
        def run_from(index: int) -> None:
            """Execute steps sequentially until a gate, a failure, or the end."""
            state["index"] = index
            if index >= len(wf.steps):
                finish("workflow complete", "success")
                return
            step = wf.steps[index]
            meta = skill_by_id(step.skill)
            entry = primary(meta.id, meta.directory) if meta else None

            if entry is None:
                log(f"# step {step.step} ({step.skill}) has no runnable script — skipping")
                advance_after(step, index, ok=True)
                return
            verdict = evaluate(meta)
            if not verdict.runnable:
                if step.optional:
                    log(f"# step {step.step} optional and not runnable — skipping")
                    advance_after(step, index, ok=True)
                    return
                finish(f"step {step.step} blocked: {verdict.state.value}", "error")
                return

            spec = spec_for(entry.path)
            # Hand this step the reports the earlier ones wrote, where the
            # workflow says it consumes them and a parameter plainly matches.
            prefill = wiring.match(spec, state["produced"], consumes=step.consumes)
            remembered = state["args"].get(step.step)
            if remembered is not None:
                launch(step, index, entry, remembered["argv"])
                return
            if spec.needs_arguments or not spec.parsed or prefill:
                show_input_gate(step, index, entry, spec, prefill)
                return

            launch(step, index, entry, ())

        def launch(step: Step, index: int, entry, argv) -> None:
            state["index"] = index
            state["running"] = True
            render_steps()
            handle = runner.RunHandle()
            state["handle"] = handle
            controls_row.controls = [
                run_status_chip("running"),
                ft.Text(f"step {step.step}/{len(wf.steps)} — {step.skill}",
                        size=12, color=pal.muted),
                ft.ProgressRing(width=16, height=16),
                ft.Button("Stop", icon=ft.Icons.STOP_CIRCLE_OUTLINED, on_click=stop),
            ]
            page.update()

            def worker():
                result = runner.run_skill(entry, argv, on_line=log, handle=handle)
                runs.record(result, workflow_id=wf.id)
                log(f"# step {step.step} {result.status} in {result.duration_s:.1f}s "
                    f"— {result.headline}")

                # Keep what this step concluded, and where it wrote it, so the
                # step row can chart it and the next gate can summarise it.
                state["results"][step.step] = result
                found = insights.digest(result)
                if not found.empty:
                    state["insights"][step.step] = found
                state["produced"].update(
                    wiring.produced_by(step.produces, result.artifacts))

                # A step that ran correctly and matched nothing has not failed;
                # halting the workflow there would be wrong.
                if result.status != "ok" and not result.diagnosis.benign \
                        and not step.optional:
                    finish(f"step {step.step}: {result.headline}", "error")
                    return
                advance_after(step, index, ok=True)

            page.run_thread(worker)

        def advance_after(step: Step, index: int, *, ok: bool) -> None:
            if step.decision_gate:
                show_gate(step, index)
                return
            run_from(index + 1)

        # ------------------------------------------------------ decision gate
        def _producer_of(artifact_id: str) -> Optional[int]:
            """Which step made this artifact, per the workflow's own registry."""
            for declared in wf.artifacts:
                if declared.id == artifact_id and declared.produced_by_step:
                    return declared.produced_by_step
            for candidate in wf.steps:
                if artifact_id in candidate.produces:
                    return candidate.step
            return None

        def _evidence(step: Step) -> list[tuple[Step, Optional[Insight]]]:
            """The steps this gate depends on, in order, with what they found."""
            numbers: list[int] = []
            for artifact_id in step.consumes:
                producer = _producer_of(artifact_id)
                if producer is not None and producer not in numbers:
                    numbers.append(producer)
            if step.step not in numbers:
                numbers.append(step.step)
            by_number = {s.step: s for s in wf.steps}
            found = []
            for number in sorted(numbers):
                source = by_number.get(number)
                if source is not None:
                    found.append((source, state["insights"].get(number)))
            return found

        def _digest(step: Step) -> ft.Control:
            """What the operator needs in front of them to answer the question.

            Without this the gate asks about "today's breadth, uptrend
            participation, and top risk" while showing none of the three.
            """
            rows: list[ft.Control] = []
            for source, found in _evidence(step):
                head = ft.Row([
                    ft.Text(f"{source.step}. {source.name}", size=12,
                            weight=ft.FontWeight.W_600, color=pal.text),
                    ft.Text(source.skill, size=10, color=pal.muted, expand=True),
                ], spacing=8)
                if found is None:
                    body: ft.Control = ft.Text(
                        "no output from this step — it was skipped, blocked, or "
                        "produced nothing to summarise",
                        size=11, color=pal.muted)
                else:
                    body = insight_chart(found) or ft.Text(
                        found.headline or "—", size=11, color=pal.muted)
                rows.append(ft.Container(
                    ft.Column([head, body], spacing=6),
                    padding=10, bgcolor=pal.surface,
                    border=ft.Border.all(1, pal.border),
                    border_radius=RADII["sm"]))
            if not rows:
                return ft.Text("No earlier output to summarise.", size=11,
                               color=pal.muted)
            return ft.Column([
                ft.Text("What the steps before this one found", size=12,
                        weight=ft.FontWeight.W_600, color=pal.text),
                *rows,
            ], spacing=8)

        def show_gate(step: Step, index: int) -> None:
            """Stop, show the evidence, and hand the decision to the operator."""
            state["running"] = False
            state["awaiting_gate"] = True
            state["index"] = index + 1
            choice = options_for(step.decision_question)
            question = (choice.question
                        or f"Step {step.step} requires your decision before continuing.")

            answers: list[ft.Control] = []
            written: Optional[ft.TextField] = None
            if choice.closed:
                answers = [
                    ft.Button(option.label,
                              tooltip=f"Records this step's answer as “{option.value}”",
                              on_click=lambda e, v=option.value:
                                  record_answer(step, index, v))
                    for option in choice.options
                ]
            else:
                # The question does not name a closed set, so no button can
                # answer it. Take the operator's words instead of pretending.
                written = ft.TextField(
                    label="Your answer", dense=True, multiline=True,
                    min_lines=1, max_lines=3, text_size=12,
                    on_submit=lambda e: record_answer(step, index,
                                                      (written.value or "").strip()))
                answers = [ft.Button(
                    "Continue", icon=ft.Icons.ARROW_FORWARD,
                    on_click=lambda e: record_answer(
                        step, index, (written.value or "").strip()))]
            answers.append(ft.Button("Stop here", on_click=lambda e: cancel_gate()))

            note = ("Answers read from the question itself."
                    if choice.closed
                    else "This question does not name a fixed set of answers, "
                         "so it takes one in your words.")

            gate_host.controls = [ft.Container(
                ft.Column([
                    _digest(step),
                    ft.Divider(color=pal.border),
                    ft.Row([ft.Icon(ft.Icons.PAN_TOOL_OUTLINED, size=18,
                                    color=pal.accent),
                            ft.Text(question, size=13, color=pal.text,
                                    expand=True, selectable=True)], spacing=10),
                    *( [written] if written is not None else [] ),
                    ft.Row(answers, spacing=8, wrap=True),
                    ft.Text(note, size=10, color=pal.muted),
                ], spacing=10),
                padding=14, bgcolor=pal.surface_2,
                border=ft.Border.all(1, pal.accent), border_radius=RADII["md"])]
            controls_row.controls = [chip("waiting for your decision", "accent")]
            render_steps()
            page.update()

        def record_answer(step: Step, index: int, answer: str) -> None:
            """Write the operator's answer down, then carry on.

            A decision that only moves the run forward leaves no trace of what
            was decided, which makes the journal step later in these workflows
            impossible to fill in honestly.
            """
            answer = (answer or "").strip()
            if answer:
                state["decisions"][step.step] = answer
                log(f"# step {step.step} decision: {answer}")
                _persist_decision(step, answer)
            else:
                log(f"# step {step.step} continued without a recorded answer")
            resume(index + 1)

        def _persist_decision(step: Step, answer: str) -> None:
            result = state["results"].get(step.step)
            if result is None:
                return
            choice = options_for(step.decision_question)
            payload = {
                "workflow": wf.id,
                "step": step.step,
                "step_name": step.name,
                "skill": step.skill,
                "question": choice.question,
                "options_offered": list(choice.values),
                "answer": answer,
                "answered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "produces": list(step.produces),
            }
            try:
                path = Path(result.run_dir) / f"decision_step{step.step}.json"
                path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                                encoding="utf-8")
                log(f"# recorded to {path.name}")
            except Exception as exc:
                log(f"# could not record the decision: {exc}")

        def resume(index: int) -> None:
            gate_host.controls = []
            state["awaiting_gate"] = False
            state["running"] = True
            run_from(index)

        def cancel_gate() -> None:
            gate_host.controls = []
            state["awaiting_gate"] = False
            finish("stopped at decision gate", "muted")

        def stop(e=None) -> None:
            handle = state.get("handle")
            if handle is not None:
                handle.cancel()
            finish("cancelled", "muted")

        def start(e=None) -> None:
            console.controls = []
            gate_host.controls = []
            state["insights"].clear()
            state["results"].clear()
            state["produced"].clear()
            state["decisions"].clear()
            state["collapsed"].clear()
            state["running"] = True
            run_from(0)

        render_steps()
        controls_row.controls = [
            ft.Button("Run workflow", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=start)
        ]

        return ft.Column([
            ft.Text("Pipeline", size=15, weight=ft.FontWeight.W_600, color=pal.text),
            step_rows,
            controls_row,
            gate_host,
            ft.Container(console, padding=12, bgcolor=pal.bg,
                         border=ft.Border.all(1, pal.border), border_radius=RADII["md"]),
        ], spacing=10)

    render_grid()
    render_detail()

    return ft.Column([
        section("Workflows",
                subtitle=f"{len(workflows)} pipelines. Decision gates pause for you."),
        grid,
        ft.Container(detail_host, padding=ft.Padding(0, 8, 0, 0), expand=True),
    ], spacing=14, expand=True, scroll=ft.ScrollMode.AUTO)
