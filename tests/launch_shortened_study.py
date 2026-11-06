"""New-draft shortening with invented profiles, temporary files and no network."""
from contextlib import redirect_stdout
from dataclasses import fields, replace
from datetime import timedelta
from io import StringIO
import json
from pathlib import Path
import tempfile

from execution_launch import study
from execution_launch.profile import profile_body
from execution_launch.program import program_json
from execution_launch.strategy import ForwardProtocol, protocol_json
from tests import launch_study as F
from tools.research import prepare_shortened_study as S

NOW = F.START - timedelta(days=1)
START = NOW + timedelta(minutes=10)


def draft(**changes):
    template = F.template(observations=2016, **changes)
    return json.dumps({"schema_version": 1, "plan_id": "unexecuted-old-draft", "asset": "BTC",
                       "risk_group": "crypto-btc", "template": json.loads(protocol_json(template)),
                       "programs": [json.loads(program_json(p)) for p in F.PROGRAMS]})


def prepare(raw=None, profile=None, **changes):
    args = {"now": NOW, "capture_start": START, "plan_id": "new-48h-draft",
            "study_id": "new-48h-study"}
    args.update(changes)
    return S.prepare_draft(profile or F.profile(), raw or draft(), **args)


def test_new_window_retains_every_nonwindow_test_and_program():
    source = draft()
    original, programs, names = study._draft(source)
    raw, plan = prepare(source)
    revised, changed_programs, revised_names = study._draft(raw)
    allowed = {"study_id", "preregistered_at", "capture_start", "capture_end", "minimum_observations"}
    for field in fields(ForwardProtocol):
        if field.name not in allowed:
            assert getattr(original, field.name) == getattr(revised, field.name), field.name
    assert changed_programs == programs
    assert revised.capture_end - revised.capture_start == timedelta(hours=48)
    assert revised.minimum_observations == 576 and revised.bar_seconds == 300
    assert (revised.capture_end - revised.capture_start).total_seconds() / revised.bar_seconds + 1 == 577
    assert revised_names["plan_id"] != names["plan_id"]
    assert all(c.protocol.minimum_roundtrips == 20 and c.protocol.alpha == F.D("0.05")
               for c in plan.candidates)
    assert json.loads(source)["template"]["minimum_observations"] == 2016


def test_draft_passes_existing_freeze_without_new_runtime_authority():
    raw, expected = prepare()
    template, programs, names = study._draft(raw)
    actual = study.build_study_plan(F.profile(), programs, template=template, **names)
    assert study.validate_study_plan(actual) == study.validate_study_plan(expected)
    result = study.rank_market_evidence(actual, {}, profile=F.profile(), now=START)
    assert result.status == "NO_QUALIFIED_MARKET" and result.execution_ready is False


def test_new_ids_cadence_time_and_input_duration_are_required():
    for changes, code in (
        ({"plan_id": "unexecuted-old-draft"}, "SHORT_STUDY_NEW_IDS_REQUIRED"),
        ({"study_id": "fixture-study"}, "SHORT_STUDY_NEW_IDS_REQUIRED"),
        ({"capture_start": NOW + timedelta(seconds=119)}, "SHORT_STUDY_START_MARGIN_REQUIRED"),
        ({"now": NOW.replace(tzinfo=None)}, "SHORT_STUDY_AWARE_TIME_REQUIRED"),
        ({"plan_id": "../../private"}, "SHORT_STUDY_ID_INVALID"),
    ):
        F.refused(lambda: prepare(**changes), code)
    F.refused(lambda: prepare(draft(bar_seconds=60, minimum_fill_delay_seconds=1)),
              "SHORT_STUDY_FIVE_MINUTE_DRAFT_REQUIRED")
    too_short = json.loads(draft())
    too_short["template"]["minimum_observations"] = 575
    F.refused(lambda: prepare(json.dumps(too_short)), "SHORT_STUDY_INPUT_WINDOW_TOO_SHORT")


def test_no_relabeling_published_plans_or_captures():
    _, plan = prepare()
    F.refused(lambda: prepare(study.study_plan_json(plan)), "STUDY_PLAN_SCHEMA_INVALID")
    F.refused(lambda: prepare(study.commitment_json(plan)), "STUDY_PLAN_SCHEMA_INVALID")
    F.refused(lambda: prepare('{"source_kind":"prospective_paper_capture","bars":[]}'),
              "STUDY_PLAN_SCHEMA_INVALID")


def test_freshness_and_infeasible_tests_are_not_relaxed():
    stale = F.profile(instrument_rules=F.rules(asof=NOW - timedelta(minutes=5, seconds=1)))
    F.refused(lambda: prepare(profile=stale), "STUDY_PROFILE_INCOMPLETE")
    # A block that fit the old 7-day window does not fit 576 intervals. Refuse;
    # do not retune it or silently lower the frozen roundtrip threshold.
    F.refused(lambda: prepare(draft(block_length=300)), "STRATEGY_THRESHOLD_INVALID")
    F.refused(lambda: prepare(draft(minimum_roundtrips=400)), "STUDY_ROUNDTRIPS_INFEASIBLE")


def invoke(args):
    out = StringIO()
    with redirect_stdout(out):
        code = S.main(args)
    return code, out.getvalue()


def test_cli_defaults_to_redacted_output_and_emission_requires_flag():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)
        profile_path, draft_path = path / "profile.json", path / "draft.json"
        profile_path.write_text(json.dumps(profile_body(F.profile())), encoding="ascii")
        draft_path.write_text(draft(), encoding="ascii")
        args = ["--profile", str(profile_path), "--draft", str(draft_path), "--now", NOW.isoformat(),
                "--capture-start", START.isoformat(), "--plan-id", "new-48h-draft", "--study-id", "new-48h-study"]
        code, raw = invoke(args)
        body = json.loads(raw)
        assert code == 0 and body["draft_valid"] is True
        assert body["book_observations"] == 577 and body["return_intervals"] == 576
        assert body["execution_ready"] is False and body["published"] is False
        assert body["source_authenticated"] is False and body["owner_approval_verified"] is False
        assert F.PRINCIPAL not in raw and F.SCOPE not in raw and temp not in raw
        code, full = invoke(args + ["--emit-draft"])
        assert code == 0 and study._draft(full)[0].minimum_observations == 576
        assert sorted(p.name for p in path.iterdir()) == ["draft.json", "profile.json"]
        code, rejected = invoke(args + ["--emit-draft", "--emit-draft"])
        assert code == 2 and "SHORT_STUDY_ARGUMENTS_INVALID" in rejected
        assert F.PRINCIPAL not in rejected and temp not in rejected


def test_cli_failure_and_help_do_not_read_private_files():
    from unittest.mock import patch
    with patch.object(S, "_read_file", side_effect=AssertionError("unexpected read")):
        assert invoke(["--help"])[0] == 0
        code, raw = invoke([])
        assert code == 2 and json.loads(raw)["execution_ready"] is False
