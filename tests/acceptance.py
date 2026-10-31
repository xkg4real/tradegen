"""Acceptance checks for the NEXTGEN skill cockpit.

Three groups:

  * **Catalogue** — the app's reading of someone else's repository. These break
    when the trading-skills repo changes shape, which is exactly when we want to
    know.
  * **Safety** — the invariants this build promises: no broker order path, no
    credential ever written to a transcript, no key printed to a screen.
  * **Regression** — the two defects found in the previous build's review. Both
    were silent failures, so both get a test that fails loudly.

Every file read here passes `encoding="utf-8"` explicitly. The previous suite
did not, and five of its tests died with `UnicodeDecodeError: 'cp949'` on this
machine — the target machine — because Windows Korean locale picks cp949 as the
default and `main.py` contains an em dash.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _code_only(path: Path) -> str:
    """Source with docstrings and comments stripped.

    Several checks below assert that a token does not appear in the code. The
    same token is discussed in prose in the very files being checked — naming
    the defect is the point of the comment — so scanning raw text produces false
    positives. `ast` gives us the executable surface instead.
    """
    import ast
    tree = ast.parse(_read(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)) and ast.get_docstring(node):
            node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def runtime_py() -> list[Path]:
    files: list[Path] = []
    for base in (ROOT / "core", ROOT / "data", ROOT / "ui", ROOT / "execution",
                 ROOT / "execution_control", ROOT / "execution_orders"):
        if base.is_dir():
            files.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
    files.extend([ROOT / "main.py", ROOT / "config.py"])
    return [p for p in files if p.is_file()]


# --------------------------------------------------------------------------- #
# Catalogue
# --------------------------------------------------------------------------- #
def test_01_skills_index_parses():
    from core.skills import all_skills
    skills = all_skills()
    assert len(skills) >= 60, f"expected the full catalogue, parsed {len(skills)}"
    assert all(s.id and s.display_name for s in skills)


def test_02_workflows_parse():
    from core.skills.workflows import all_workflows
    workflows = all_workflows()
    assert len(workflows) >= 8, f"parsed only {len(workflows)} workflows"
    assert all(w.steps for w in workflows), "a workflow with no steps is unusable"


def test_03_every_runnable_skill_resolves_one_primary():
    from core.skills import all_skills, primary
    from core.skills.entrypoints import entrypoints
    for skill in all_skills():
        eps = entrypoints(skill.id, skill.directory)
        if not eps:
            continue
        assert primary(skill.id, skill.directory) is not None, \
            f"{skill.id} has {len(eps)} scripts and no primary"


def test_04_curated_primaries_still_exist():
    """A curated entrypoint that has been renamed upstream must fail loudly."""
    from core.skills.entrypoints import _PRIMARY
    from core.skills import by_id
    for skill_id, script in _PRIMARY.items():
        skill = by_id(skill_id)
        if skill is None:
            continue                       # skill removed upstream; not our bug
        assert (skill.directory / "scripts" / script).is_file(), \
            f"curated entrypoint {skill_id}/{script} no longer exists"


def test_05_workflow_steps_reference_real_skills():
    from core.skills import by_id
    from core.skills.workflows import all_workflows
    for wf in all_workflows():
        for step in wf.steps:
            assert by_id(step.skill) is not None, \
                f"{wf.id} step {step.step} references unknown skill {step.skill}"


def test_06_readiness_states_are_exhaustive():
    from core.skills import all_skills, evaluate
    from core.skills.readiness import State
    for skill in all_skills():
        assert evaluate(skill).state in set(State)


def test_07_missing_key_is_reported_with_the_env_var_name():
    """A blocked skill must name the variable to set, not just say 'unavailable'."""
    import config
    from core.skills import by_id, evaluate
    from core.skills.readiness import State
    saved = {n: os.environ.pop(n, None) for n in ("FMP_API_KEY", "FINVIZ_API_KEY")}
    try:
        config._clean.__wrapped__ if hasattr(config._clean, "__wrapped__") else None
        skill = by_id("vcp-screener")
        assert skill is not None
        verdict = evaluate(skill)
        assert verdict.state is State.MISSING_KEY, verdict.state
        assert "FMP_API_KEY" in verdict.missing_credentials
    finally:
        for name, value in saved.items():
            if value is not None:
                os.environ[name] = value


def test_07b_undeclared_credentials_are_detected_from_code():
    """skills-index.yaml under-declares: five skills read FMP_API_KEY without
    declaring an `fmp` integration. Trusting the manifest alone reported them
    Ready and they then failed at run time."""
    import config
    from core.skills import by_id, evaluate
    from core.skills.readiness import State
    # Blank it rather than pop it. `config` calls load_dotenv() at import, so
    # reloading the module re-reads .env — a popped variable comes straight
    # back and the test silently asserts against a configured key. An empty
    # string still counts as "present" to dotenv (override=False), so the
    # value stays suppressed, while config._clean() reads it as absent.
    saved = os.environ.get("FMP_API_KEY")
    os.environ["FMP_API_KEY"] = ""
    try:
        import importlib
        importlib.reload(config)
        skill = by_id("market-top-detector")
        if skill is None:
            return                          # skill removed upstream
        assert not any(i.id == "fmp" for i in skill.integrations), \
            "index now declares fmp; this test has served its purpose"
        verdict = evaluate(skill)
        assert verdict.state is State.MISSING_KEY, verdict.state
        assert "FMP_API_KEY" in verdict.undeclared
    finally:
        if saved is not None:
            os.environ["FMP_API_KEY"] = saved
        else:
            os.environ.pop("FMP_API_KEY", None)
        import importlib
        importlib.reload(config)


# --------------------------------------------------------------------------- #
# Safety
# --------------------------------------------------------------------------- #
def test_08_no_broker_order_path():
    """Order endpoint text is confined to the exact reviewed E3 codec; all other tokens remain forbidden."""
    needles = ["order_cash", "order-cash", "place_order", "submit_order",
               "TTTC0802U", "TTTC0801U", "VTTC0802U"]
    exceptions = {"execution_orders/kis.py": frozenset({"order-cash"})}
    hits = []
    for path in runtime_py():
        rel = path.relative_to(ROOT).as_posix()
        low = _read(path).lower()
        hits.extend(f"{rel}: {n}" for n in needles if n.lower() in low
                    and n.lower() not in exceptions.get(rel, ()))
    assert not hits, f"broker order surface present: {hits}"


def test_09_no_account_credentials_requested():
    """Account fields stay in E1 inquiry and E3's credential boundary, each with exact guard coverage."""
    exceptions = {"execution/kis_inquiry.py": frozenset({"KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD"}),
                  "execution_orders/transport.py": frozenset({"CANO", "ACNT_PRDT_CD"})}
    for path in runtime_py():
        rel = path.relative_to(ROOT).as_posix()
        text = _read(path)
        for name in ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD"):
            assert name not in text or name in exceptions.get(rel, ()), f"{rel}: {name} outside credential boundary"


def test_10_redaction_masks_configured_secret():
    import importlib
    import config
    from core.skills import runner
    os.environ["FMP_API_KEY"] = "abcdef0123456789abcdef0123456789"
    importlib.reload(config)
    try:
        masked = runner._redact("apikey=abcdef0123456789abcdef0123456789 done")
        assert "abcdef0123456789abcdef0123456789" not in masked
        assert "done" in masked
    finally:
        os.environ.pop("FMP_API_KEY", None)
        importlib.reload(config)


def test_11_redaction_preserves_artifact_filenames():
    """An earlier regex masked every report filename in the transcript."""
    from core.skills import runner
    line = "JSON report saved to: market_breadth_2026-08-18_152347.json"
    assert runner._redact(line) == line


def test_12_skill_env_never_leaks_into_a_record():
    from core.skills.runner import RunResult
    from pathlib import Path as _P
    result = RunResult(
        run_id="r", skill_id="s", entrypoint="e.py", argv=("--x",), status="ok",
        exit_code=0, started_at="", finished_at="", duration_s=0.0, run_dir=_P("."),
    )
    assert "env" not in result.to_record(), "the persisted record must not carry an env"


def test_13_settings_page_shows_presence_not_values():
    """No credential value may reach a widget."""
    source = _read(ROOT / "ui" / "settings_page.py")
    assert "kis_credentials()" not in source
    assert "opendart_key()" not in source
    assert "_clean(" not in source


# --------------------------------------------------------------------------- #
# Regression — defects found reviewing the previous build
# --------------------------------------------------------------------------- #
def test_14_page_resize_handler_matches_the_flet_api():
    """The old build assigned a handler to an attribute Flet 0.85 does not
    define, so the compact layout never ran at any width. Assert against the
    live API and against the assignment in code, not against prose — the
    misspelling is named in comments here and in main.py on purpose."""
    import flet as ft
    assert hasattr(ft.Page, "on_resize"), "Flet renamed the resize event again"
    source = _code_only(ROOT / "main.py")
    assert re.search(r"page\.on_resize\s*=", source), "no resize handler is attached"
    assert not re.search(r"page\.on_resiz(ed|e_d)\s*=", source), \
        "main.py attaches a handler to an attribute Flet does not define"


def test_15_views_are_cached_across_navigation():
    """Rebuilding a view on every nav click discarded live state."""
    source = _read(ROOT / "main.py")
    assert "cache" in source and "cache[name] = build(" in source


def test_16_every_source_file_is_utf8_readable():
    """The previous suite read files with the platform default and died on cp949."""
    for path in runtime_py() + [ROOT / "tests" / "acceptance.py", ROOT / "tests" / "run_all.py"]:
        try:
            _read(path)
        except UnicodeDecodeError as exc:
            raise AssertionError(f"{path} is not valid UTF-8: {exc}") from None


def test_17_tests_never_read_without_an_encoding():
    """Lock the cp949 fix: reading a file with no explicit encoding here is what
    killed five tests in the previous suite."""
    for name in ("acceptance.py", "run_all.py"):
        source = _code_only(ROOT / "tests" / name)
        assert not re.search(r"read_text\(\s*\)", source), \
            f"{name} reads a file without specifying an encoding"


def test_18_eodhd_is_gone_from_the_runtime():
    """No EODHD *usage*. The name still appears in prose that explains what this
    build replaced, which is why this scans code rather than raw text."""
    blob = "\n".join(_code_only(p) for p in runtime_py()).lower()
    for token in ("eodhd", "quartr"):
        assert token not in blob, f"{token} is still used in the runtime surface"


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #
def test_19_runner_executes_an_offline_skill_and_captures_artifacts():
    from core.skills import by_id, primary, runner, runs
    skill = by_id("futures-position-sizer")
    assert skill is not None
    entry = primary(skill.id, skill.directory)
    assert entry is not None
    result = runner.run_skill(entry, [
        "--symbol", "ES", "--direction", "LONG", "--entry", "5500",
        "--stop", "5450", "--account-size", "100000", "--risk-pct", "1",
        "--format", "both",
    ], timeout_s=90)
    assert result.status == "ok", f"{result.status}: {result.error}\n{result.stdout[-400:]}"
    assert result.artifacts, "the run produced no artifact"
    record = runs.record(result)
    assert (result.run_dir / "run.json").is_file()
    assert (result.run_dir / "transcript.log").is_file()
    assert runs.by_id(record.run_id) is not None


def test_20_runner_survives_a_missing_interpreter():
    """A bad interpreter must return an ERROR result, not raise into the UI."""
    import config
    from core.skills import by_id, primary, runner
    skill = by_id("futures-position-sizer")
    entry = primary(skill.id, skill.directory)
    saved = os.environ.get("NEXTGEN_SKILL_PYTHON")
    os.environ["NEXTGEN_SKILL_PYTHON"] = str(ROOT / "no-such-python.exe")
    try:
        import importlib
        importlib.reload(config)
        result = runner.run_skill(entry, [], timeout_s=20)
        assert result.status == "error"
        assert result.error
    finally:
        if saved is None:
            os.environ.pop("NEXTGEN_SKILL_PYTHON", None)
        else:
            os.environ["NEXTGEN_SKILL_PYTHON"] = saved
        import importlib
        importlib.reload(config)


def test_21_krx_gateway_degrades_with_a_reason():
    """No provider configured must yield an actionable reason, never a blank."""
    from data.krx import KRXGateway
    gateway = KRXGateway()
    for answer in (gateway.daily("005930"), gateway.filings("005930")):
        if not answer.ok:
            assert answer.reason.strip(), "a failed answer must explain itself"


def test_22_krx_status_is_reported_per_provider():
    from data.krx import KRXGateway
    providers = {s["provider"] for s in KRXGateway().status()}
    assert providers == {"KIS", "OpenDART", "KRX"}


# --------------------------------------------------------------------------- #
# Arguments
#
# Twenty-five of the sixty-six runnable skills reject an empty command line and
# exit 2 in about 0.15 seconds. The cockpit used to offer only a free-text
# arguments box and to report those skills as Ready, so the failure looked like
# a broken skill rather than a missing input. These tests hold the three parts
# of the fix in place: the parameters are read from the script, readiness tells
# the truth about them, and the failure explains itself.
# --------------------------------------------------------------------------- #
def test_23_required_arguments_are_read_from_the_script():
    from core.skills import by_id, primary
    from core.skills.params import spec_for
    expected = {
        "position-sizer": ("--account-size",),
        "trading-skills-navigator": ("--query",),
        "data-quality-checker": ("--file",),
        "residual-edge-analyzer": ("--input", "--config", "--output-json"),
        "contrarian-setup-gate": ("--symbol", "--detector-json", "--as-of"),
    }
    for skill_id, flags in expected.items():
        skill = by_id(skill_id)
        if skill is None:
            continue
        entry = primary(skill.id, skill.directory)
        assert entry is not None, f"{skill_id} has no entrypoint"
        missing = spec_for(entry.path).missing()
        assert missing == flags, f"{skill_id}: read {missing}, expected {flags}"


def test_24_mutually_exclusive_groups_need_exactly_one_member():
    """`--drafts-dir` or `--draft`, not both required and not neither."""
    from core.skills import by_id, primary
    from core.skills.params import spec_for
    skill = by_id("edge-strategy-reviewer")
    if skill is None:
        return
    spec = spec_for(primary(skill.id, skill.directory).path)
    assert spec.missing(), "an empty call must be reported as incomplete"
    assert not spec.missing({"draft": "x.json"}), \
        "supplying one member of the group must satisfy it"
    assert not spec.missing({"drafts_dir": "drafts/"}), \
        "either member must satisfy the group"


def test_25_subcommand_arguments_are_scoped_to_their_subcommand():
    """Choosing `scan` must not demand the flags only `backfill` takes."""
    from core.skills import by_id, primary
    from core.skills.params import spec_for
    skill = by_id("stockbee-20pct-study")
    if skill is None:
        return
    spec = spec_for(primary(skill.id, skill.directory).path)
    assert spec.subcommands, "the subcommands were not detected"
    assert spec.missing() == (spec.subcommand_dest,), \
        "with no subcommand chosen, that is the only thing missing"
    first = spec.subcommands[0]
    scoped = {p.dest for p in spec.for_subcommand(first)}
    other = spec.subcommands[-1]
    assert first == other or scoped != {p.dest for p in spec.for_subcommand(other)}, \
        "two different subcommands resolved to identical parameter sets"


def test_26_a_composed_command_line_satisfies_the_real_parser():
    """The end-to-end claim: what the form builds, argparse accepts.

    Static extraction is only worth having if the argv it produces actually
    runs. This fills the required parameters and asserts the script does not
    reject the call — exit 2 here would mean the form is still lying.
    """
    from core.skills import by_id, primary, runner
    from core.skills.params import spec_for
    skill = by_id("position-sizer")
    entry = primary(skill.id, skill.directory)
    spec = spec_for(entry.path)
    values = {"account_size": "100000", "entry": "50", "stop": "48",
              "risk_pct": "1"}
    argv = spec.build_argv(values)
    assert "--account-size" in argv and "100000" in argv
    result = runner.run_skill(entry, argv, timeout_s=60)
    assert result.exit_code != 2, (
        "the composed command line was rejected by argparse:\n"
        + result.stdout[-500:])


def test_27_no_skill_is_ready_while_its_script_demands_arguments():
    """The regression that made twenty skills look broken.

    Readiness considered only credentials, so a skill whose script requires
    `--query` was reported Ready and then failed instantly. A skill that cannot
    be launched as-is must never be READY.
    """
    from core.skills import all_skills, primary
    from core.skills.params import spec_for
    from core.skills.readiness import State, evaluate
    liars = []
    for skill in all_skills():
        verdict = evaluate(skill)
        if verdict.state is not State.READY:
            continue
        entry = primary(skill.id, skill.directory)
        if entry is None:
            continue
        spec = spec_for(entry.path)
        if spec.needs_arguments or not spec.parsed:
            liars.append(skill.id)
    assert not liars, "reported Ready but cannot run unaided: " + ", ".join(liars)


def test_28_the_argument_reader_still_understands_these_scripts():
    """Drift alarm: static reading must keep covering nearly every script.

    Two of sixty-six build their parser in a way `ast` cannot follow, and those
    fall back to the raw arguments box. If that number grows, the form is
    quietly turning into the free-text box it replaced.
    """
    from core.skills import all_skills, primary
    from core.skills.params import spec_for
    unparsed = []
    total = 0
    for skill in all_skills():
        entry = primary(skill.id, skill.directory)
        if entry is None:
            continue
        total += 1
        if not spec_for(entry.path).parsed:
            unparsed.append(skill.id)
    if total == 0:
        return
    assert len(unparsed) <= 4, (
        f"{len(unparsed)} of {total} scripts are unreadable: "
        + ", ".join(unparsed))


# --------------------------------------------------------------------------- #
# Failure legibility
# --------------------------------------------------------------------------- #
def test_29_a_rejected_command_line_names_the_argument():
    """`exit code 2` was the original complaint. It must never be the answer."""
    from core.skills import by_id, primary, runner
    from core.skills.diagnose import Cause
    skill = by_id("trading-skills-navigator")
    if skill is None:
        return
    entry = primary(skill.id, skill.directory)
    result = runner.run_skill(entry, (), timeout_s=45)
    assert result.exit_code == 2, "expected argparse to reject the empty call"
    assert result.cause is Cause.MISSING_ARGS, f"classified as {result.cause}"
    assert "--query" in result.headline, result.headline
    assert "--query" in result.diagnosis.fields, result.diagnosis.fields
    assert "exit code" not in result.headline.lower(), \
        "the headline fell back to the exit code"


def test_30_an_empty_result_is_not_reported_as_a_failure():
    """A screener that matched nothing has not malfunctioned."""
    from core.skills.diagnose import Cause, diagnose
    verdict = diagnose(status="failed", exit_code=1,
                       stdout="Screening complete! Found 0 qualified stocks.")
    assert verdict.cause is Cause.NO_RESULTS
    assert verdict.benign, "an empty result must not be painted as an error"

    crash = diagnose(status="failed", exit_code=1,
                     stdout="Traceback (most recent call last):\n"
                            "ValueError: bad input")
    assert crash.cause is Cause.CRASH and not crash.benign


def test_31_every_failure_class_produces_a_sentence():
    """No diagnosis may be blank, whatever the transcript looks like."""
    from core.skills.diagnose import diagnose
    samples = [
        ("failed", 2, "app.py: error: the following arguments are required: --x"),
        ("failed", 1, "Error: FMP API returned 402 Payment Required"),
        ("failed", 1, "requests.exceptions.ConnectionError: Max retries exceeded"),
        ("failed", 1, "FileNotFoundError: [Errno 2] No such file: 'a.json'"),
        ("timeout", None, "still working..."),
        ("cancelled", None, ""),
        ("failed", 1, ""),
        ("ok", 0, "done"),
    ]
    for status, code, text in samples:
        verdict = diagnose(status=status, exit_code=code, stdout=text)
        assert verdict.headline.strip(), f"no headline for {status}/{code}"
        assert len(verdict.headline) < 400


def test_32_workflow_steps_are_never_launched_with_an_empty_command_line():
    """The workflow runner passed `()` to every step unconditionally.

    Forty-two of the repository's sixty-seven workflow steps require arguments,
    so those steps could not succeed at all. This reads the UI source rather
    than the behaviour, because the failure was a hard-coded literal.
    """
    import ast
    offenders = []
    for path in sorted((ROOT / "ui").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "run_skill"
                    and len(node.args) >= 2):
                continue
            second = node.args[1]
            empty = ((isinstance(second, ast.Tuple) and not second.elts)
                     or (isinstance(second, ast.List) and not second.elts))
            if empty:
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, ("run_skill called with a hard-coded empty argv at "
                           + ", ".join(offenders))


# --------------------------------------------------------------------------- #
# Decision gates: the answers, the evidence, and the chart
# --------------------------------------------------------------------------- #
def test_33_every_gate_option_is_a_word_the_question_used():
    """The governing rule of `core.skills.decisions`.

    No workflow declares its answers — there is no `decision_options` key in any
    of the eleven YAML files — so the options have to be read out of the prose
    of `decision_question`. That is only defensible while every option is a
    verbatim slice of the author's own sentence. The moment NEXTGEN adds a word,
    it is inventing a contract on the workflow author's behalf.
    """
    from core.skills.decisions import options_for
    from core.skills.workflows import all_workflows

    checked = 0
    for wf in all_workflows():
        for step in wf.decision_gates:
            choice = options_for(step.decision_question)
            haystack = " ".join(step.decision_question.split()).lower()
            for option in choice.options:
                assert option.value.lower() in haystack, (
                    f"{wf.id} step {step.step}: option {option.value!r} does not "
                    f"appear in the question")
                checked += 1
    assert checked, "no gate produced any options at all"


def test_34_the_exposure_gate_offers_the_three_postures_it_asks_about():
    """The reported defect, in one assertion.

    `market-regime-daily` step 4 asks whether new swing trade risk is allowed,
    restricted, or cash-priority, and the cockpit answered with `Continue` and
    `Stop here` — two buttons that answer a different question.
    """
    from core.skills.decisions import options_for
    from core.skills.workflows import by_id

    wf = by_id("market-regime-daily")
    assert wf is not None, "market-regime-daily is missing from the repository"
    gates = [s for s in wf.steps if s.decision_gate]
    assert len(gates) == 1, f"expected one gate, found {len(gates)}"

    choice = options_for(gates[0].decision_question)
    assert choice.closed, "the exposure gate produced no options"
    labels = [o.label for o in choice.options]
    assert labels == ["Allowed", "Restricted", "Cash-priority"], labels
    assert "continue" not in [label.lower() for label in labels]


def test_35_an_open_question_is_not_given_invented_answers():
    """Twenty of the thirty gates ask something no button can answer.

    "Which candidates have a clean weekly setup … and pass the manual chart
    review?" is answered per candidate. Offering two or three buttons for it
    would be worse than the generic pair it replaced, because it would look
    authoritative. Those gates must fall through to a written answer.
    """
    from core.skills.decisions import options_for
    from core.skills.workflows import by_id

    open_questions = [
        ("swing-opportunity-daily", 7),
        ("core-portfolio-weekly", 2),
        ("stockbee-20pct-study-daily", 5),
        ("multi-asset-opportunity-daily", 6),
    ]
    for workflow_id, number in open_questions:
        wf = by_id(workflow_id)
        assert wf is not None, f"{workflow_id} is missing"
        step = next(s for s in wf.steps if s.step == number)
        choice = options_for(step.decision_question)
        assert not choice.closed, (
            f"{workflow_id} step {number} was given options it did not name: "
            + ", ".join(choice.values))


def test_36_a_checklist_is_not_mistaken_for_an_answer_set():
    """`pass the written-plan, predefined-stop, position-size, … checks?` has
    the same comma shape as a genuine enumeration but lists things to verify,
    not answers to give. The determiner in front of it is the tell."""
    from core.skills.decisions import options_for

    checklist = ("Before placing any manual broker order, does each actionable "
                 "candidate pass the written-plan, predefined-stop, "
                 "position-size, recent-loss, market-regime, and "
                 "circuit-breaker discipline checks?")
    assert not options_for(checklist).closed

    instruction = ("Register each fade whose sizer output is sizing_status "
                   "SIZED — never a NO_TRADE result — in this order: create "
                   "the IDEA thesis first, then attach the SIZED report.")
    assert not options_for(instruction).closed, (
        "an imperative with no question mark asks the operator nothing")

    enumeration = ("Which next-session operating rules should the trader "
                   "accept, modify, defer, or journal only?")
    assert [o.label for o in options_for(enumeration).options] == \
        ["Accept", "Modify", "Defer", "Journal only"]

    # Preparatory states and output formats are not choices for a later question.
    preamble = "Reconcile ACTIVE / PARTIALLY_CLOSED snapshots. Save the JSON report. "
    assert not options_for(preamble + "What reallocation does the trader propose?").closed
    assert options_for(preamble + enumeration).values == options_for(enumeration).values
    verdict = ("Does the verdict reach CLEAN-PASS / PASS-CAUTION / CONDITIONAL-PASS? "
               "HOLD-REVIEW, STEP1-RECHECK, or FAIL stops here.")
    assert options_for(preamble + verdict).values == (
        "CLEAN-PASS", "PASS-CAUTION", "CONDITIONAL-PASS", "HOLD-REVIEW", "STEP1-RECHECK", "FAIL")


def test_37_a_gate_can_always_name_the_steps_it_depends_on():
    """The gate summary is built by resolving each `consumes` id back to the
    step that produced it. If an id resolves to nothing the summary silently
    loses a panel, so every consumed artifact must have a declared producer."""
    from core.skills.workflows import all_workflows

    orphans = []
    for wf in all_workflows():
        producers = {a.id: a.produced_by_step for a in wf.artifacts
                     if a.produced_by_step}
        for step in wf.steps:
            for artifact_id in step.consumes:
                if artifact_id in producers:
                    continue
                if any(artifact_id in other.produces for other in wf.steps):
                    continue
                orphans.append(f"{wf.id} step {step.step} consumes {artifact_id}")
    assert not orphans, "consumed artifact with no producer: " + "; ".join(orphans)


def test_38_a_report_is_read_into_components_that_can_be_drawn():
    """`core.skills.insights` against a real report shape.

    The scoring skills share a convention — a composite plus weighted
    components, each with a score and a one-line signal — and the chart and the
    gate summary both depend on it being read faithfully.
    """
    import json
    import tempfile
    from pathlib import Path as _Path
    from core.skills.insights import read

    report = {
        "composite": {
            "composite_score": 79.2,
            "zone": "Healthy",
            "exposure_guidance": "75-90%",
            "data_quality": {"label": "Complete (6/6 components)"},
            "active_warnings": [{"flag": "late_cycle", "label": "LATE CYCLE WARNING"}],
            "component_scores": {
                "breadth_level_trend": {"score": 90, "weight": 0.25,
                                        "label": "Current Breadth Level & Trend"},
                "historical_percentile": {"score": 60, "weight": 0.10,
                                          "label": "Historical Percentile"},
            },
        },
        "components": {
            "breadth_level_trend": {"signal": "STRONG: broad participation"},
        },
        "metadata": {"detail_url": "https://example.invalid/x.csv"},
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = _Path(tmp) / "market_breadth_2026-08-21.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        found = read(path, skill_id="market-breadth-analyzer")

    assert found is not None and not found.empty
    assert found.score == 79.2 and found.zone == "Healthy"
    assert found.guidance == "75-90%"
    assert [c.score for c in found.components] == [90.0, 60.0]
    assert found.components[0].label == "Current Breadth Level & Trend"
    assert found.components[0].weight == 0.25
    assert found.components[0].signal == "STRONG: broad participation"
    assert found.components[0].band == "success"
    assert found.components[1].band == "accent"
    assert found.warnings == ("LATE CYCLE WARNING",)
    # Plumbing is not a finding.
    assert not any("url" in k.lower() for k, _ in found.facts)


def test_39_a_missing_score_is_never_drawn_as_zero():
    """A report with no composite must render as "no score", not as a full-width
    red bar at zero. Absent and bad are different facts about a market."""
    import json
    import tempfile
    from pathlib import Path as _Path
    from core.skills.insights import Insight, read

    blank = Insight()
    assert blank.score is None and blank.band == "muted" and blank.empty
    assert "0" not in blank.headline

    with tempfile.TemporaryDirectory() as tmp:
        path = _Path(tmp) / "verdict.json"
        path.write_text(json.dumps({"recommendation": "REDUCE_ONLY",
                                    "exposure_ceiling_pct": 28}), encoding="utf-8")
        found = read(path)
    assert found is not None and found.score is None
    assert found.band == "muted"
    assert ("Recommendation", "REDUCE_ONLY") in found.facts
    assert ("Exposure ceiling pct", "28%") in found.facts


def test_40_a_step_is_handed_the_reports_the_earlier_steps_wrote():
    """`market-regime-daily` step 4 takes `--breadth` and `--uptrend`, and steps
    1 and 2 write exactly those reports. Making the operator paste the paths by
    hand is why step 4 used to report missing inputs on a run where nothing was
    missing. Parameters with nothing to match must be left alone."""
    from pathlib import Path as _Path
    from core.skills import wiring
    from core.skills.entrypoints import primary
    from core.skills.index import by_id as skill_by_id
    from core.skills.params import spec_for
    from core.skills.workflows import by_id

    wf = by_id("market-regime-daily")
    step = next(s for s in wf.steps if s.step == 4)
    meta = skill_by_id(step.skill)
    if meta is None:
        return
    entry = primary(meta.id, meta.directory)
    if entry is None:
        return
    spec = spec_for(entry.path)
    if not spec.parsed:
        return

    produced = {
        "market_breadth_report": _Path("/runs/a/market_breadth_2026-08-21.json"),
        "uptrend_report": _Path("/runs/b/uptrend_analysis_2026-08-21.json"),
    }
    filled = wiring.match(spec, produced, consumes=step.consumes)
    assert "breadth" in filled and "market_breadth" in filled["breadth"]
    assert "uptrend" in filled and "uptrend_analysis" in filled["uptrend"]
    # Nothing produced these, so nothing may be invented for them.
    for untouched in ("regime", "ftd", "theme", "sector", "institutional",
                      "output_dir"):
        assert untouched not in filled, f"{untouched} was filled from nowhere"


def test_41_an_ambiguous_artifact_is_left_for_the_operator():
    """Two artifacts fitting one parameter equally well is a question, not a
    match. Picking one would put a file the operator never chose on the command
    line of a script that reports on the market."""
    from pathlib import Path as _Path
    from core.skills.params import Kind, Param, Spec
    from core.skills import wiring

    spec = Spec(script="x.py", parsed=True, params=(
        Param(dest="report", flags=("--report",), kind=Kind.FILE),
    ))
    tie = {"daily_report": _Path("/a/daily.json"),
           "weekly_report": _Path("/b/weekly.json")}
    assert wiring.match(spec, tie) == {}

    spec2 = Spec(script="x.py", parsed=True, params=(
        Param(dest="daily", flags=("--daily",), kind=Kind.FILE),
    ))
    clear = {"daily_report": _Path("/a/daily.json")}
    assert wiring.match(spec2, clear) == {"daily": str(_Path("/a/daily.json"))}


def test_42_the_gate_reads_its_answers_rather_than_hard_coding_them():
    """The defect was a literal pair of buttons in the source. This asserts the
    gate is built from the question, not from a list in the UI file."""
    import ast
    tree = ast.parse(_read(ROOT / "ui" / "workflows_page.py"))
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "options_for"]
    assert calls, "workflows_page never asks what the question's answers are"

    gate = next((n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == "show_gate"), None)
    assert gate is not None, "show_gate is gone"
    inside = {n.func.id for n in ast.walk(gate)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "options_for" in inside, "the gate does not read the question's answers"
    assert "_digest" in inside, "the gate does not summarise the steps before it"


def test_43_a_run_that_exited_cleanly_is_not_reported_as_a_failure():
    """Found by driving `market-regime-daily` end to end.

    `market-breadth-analyzer` prints "6-Component Health Scoring (No API Key
    Required)" as its banner, scores every component, writes both reports and
    exits 0. Because the classifiers scanned the whole transcript, the phrase in
    the banner was read as the verdict and a successful step was labelled "A
    credential is missing". A run's narration is not its outcome.
    """
    from core.skills.diagnose import Cause, diagnose

    banner = (
        "======================================================\n"
        "Market Breadth Analyzer\n"
        "6-Component Health Scoring (No API Key Required)\n"
        "======================================================\n"
        "  Composite Score: 79.2/100\n"
        "  Health Zone: Healthy\n"
    )
    verdict = diagnose(status="ok", exit_code=0, stdout=banner)
    assert verdict.cause is Cause.OK, verdict.headline
    assert verdict.benign

    # The same transcript with a non-zero exit is a genuine credential failure.
    failed = diagnose(status="failed", exit_code=1,
                      stdout="ERROR: FMP API key required. Set FMP_API_KEY.")
    assert failed.cause is Cause.MISSING_KEY, failed.headline

    # A clean exit that matched nothing stays benign, and keeps saying so.
    empty = diagnose(status="ok", exit_code=0,
                     stdout="Scanning...\nFound 0 qualified stocks")
    assert empty.cause is Cause.NO_RESULTS and empty.benign


def test_44_the_traceback_outranks_a_provider_error_the_run_survived():
    """Also found by driving the workflow.

    `market-top-detector` logs four HTTP 403 "Legacy Endpoint" complaints,
    recovers from every one, completes all six components — and then dies
    writing its report into a directory that does not exist. Naming the 403 as
    the cause points the operator at something the run got past.
    """
    from core.skills.diagnose import Cause, diagnose

    transcript = (
        "Fetching NASDAQ (QQQ) data... ERROR: API request failed: 403 - "
        '{"Error Message": "Legacy Endpoint : no longer supported"}\n'
        "  OK ($710.93, 260 days)\n"
        "  [6/6] Sentiment & Speculation... Score: 25 (MIXED)\n"
        "  Composite Score: 41.9/100\n"
        "Traceback (most recent call last):\n"
        '  File "market_top_detector.py", line 812, in main\n'
        "FileNotFoundError: [Errno 2] No such file or directory: "
        "'reports/market_top_2026-08-21.json'\n"
    )
    verdict = diagnose(status="failed", exit_code=1, stdout=transcript)
    assert verdict.cause is Cause.MISSING_INPUT, verdict.headline
    assert "legacy" not in verdict.headline.lower()
    assert "reports" in verdict.headline

    # The same crash with the write visible in the frame is the skill failing to
    # create its own output directory, and must not tell the operator to fix a
    # path field they were never given.
    writing = transcript.replace(
        '  File "market_top_detector.py", line 812, in main\n',
        '  File "market_top_detector.py", line 812, in main\n'
        '    with open(output_file, "w", encoding="utf-8") as f:\n')
    wrote = diagnose(status="failed", exit_code=1, stdout=writing)
    assert wrote.cause is Cause.CRASH, wrote.headline
    assert "could not write" in wrote.headline
    assert "defect in the skill" in wrote.detail

    # A run killed *by* the provider still reads as a provider problem.
    provider = diagnose(
        status="failed", exit_code=1,
        stdout='requests.HTTPError: 402 - {"Error Message": "payment required"}')
    assert provider.cause is Cause.PLAN_LIMIT, provider.headline


def test_45_only_a_file_parameter_is_handed_a_file():
    """Also found by driving the workflow.

    `market-top-detector` takes `--breadth-200dma-date`, which shares the word
    "breadth" with `market_breadth_report` and wants `YYYY-MM-DD`. On a real run
    the wiring put a JSON path into it, and into its sibling. Free text is where
    a script asks for anything at all, so it is where a guess is least safe.
    """
    from pathlib import Path as _Path
    from core.skills import wiring
    from core.skills.params import Kind, Param, Spec

    spec = Spec(script="market_top_detector.py", parsed=True, params=(
        Param(dest="breadth_200dma_date", flags=("--breadth-200dma-date",),
              kind=Kind.TEXT, help="Date of breadth 200DMA data (YYYY-MM-DD)"),
        Param(dest="breadth_50dma", flags=("--breadth-50dma",),
              kind=Kind.NUMBER, help="Percent of S&P 500 stocks above 50DMA"),
        Param(dest="output_dir", flags=("--output-dir",), kind=Kind.DIR),
    ))
    produced = {"market_breadth_report": _Path("/runs/a/market_breadth.json")}
    assert wiring.match(spec, produced) == {}, (
        "a date, a number or an output directory must never be handed a report")


def test_46_a_failed_step_is_summarised_by_its_diagnosis_not_its_traceback():
    """The gate summary shows every step it depends on, including the ones that
    failed. Six lines of caret rows from the middle of a traceback tell the
    operator nothing; the sentence `diagnose` already produced tells them what
    happened."""
    from core.skills.diagnose import diagnose
    from core.skills.insights import digest, from_transcript

    transcript = (
        "  Composite Score: 41.9/100\n"
        "Traceback (most recent call last):\n"
        '  File "market_top_detector.py", line 812, in main\n'
        "    generate_json_report(analysis, json_file)\n"
        "    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\n"
        "FileNotFoundError: [Errno 2] No such file or directory: 'reports/x.json'\n"
    )

    class _Result:
        skill_id = "market-top-detector"
        artifacts = ()
        stdout = transcript
        diagnosis = diagnose(status="failed", exit_code=1, stdout=transcript)

    found = digest(_Result())
    assert found.lines, "a failed step summarised as nothing"
    joined = " ".join(found.lines)
    assert "^^^" not in joined and "~~~" not in joined
    assert 'File "' not in joined
    assert "does not exist" in joined

    # The plain transcript fallback drops the scaffolding too.
    plain = from_transcript(transcript)
    assert not any("^^^" in line or line.startswith('File "') for line in plain.lines)


def tests():
    return sorted((n, v) for n, v in globals().items()
                  if n.startswith("test_") and callable(v))
