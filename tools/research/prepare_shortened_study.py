"""Prepare a NEW 48-hour study draft without collecting data or changing guards.

    python -m tools.research.prepare_shortened_study --profile PROFILE.json --draft DRAFT.json --now AWARE_ISO --capture-start AWARE_ISO --plan-id NEW_ID --study-id NEW_ID

The default output is a redacted diagnostic. Add --emit-draft to print the full
PRIVATE draft, for an explicit shell redirect outside the repository. The input
must be an unexecuted draft, not a published plan or capture. Nothing is written,
published, signed, armed or traded. Supplied times and new IDs do not authenticate
publication, prove unseen observations or establish a complete trial history.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
import json
import sys

from execution_launch.profile import ProfileError, parse_profile_json
from execution_launch.program import program_json
from execution_launch.strategy import _ID, protocol_json
from execution_launch.study import _draft, build_study_plan, validate_study_plan
from execution_launch.workflow import MAX_CONFIG_BYTES, _CODE, _read_file, _time

BAR_SECONDS = 300
RETURN_INTERVALS = 576
BOOK_OBSERVATIONS = RETURN_INTERVALS + 1
_DRAFT_LIMIT = 262144
_OPTIONS = ("profile", "draft", "now", "capture-start", "plan-id", "study-id")


class ShortenedStudyError(ValueError):
    """Fixed redacted diagnostics only."""


def _require(condition, code):
    if not condition:
        raise ShortenedStudyError(code)


def prepare_draft(profile, raw_draft, *, now, capture_start, plan_id, study_id):
    """Return (private draft JSON, validated NEW plan), preserving supplied tests.

    Only the identities, registration time, window and observation requirement
    change. All candidate programs and other template settings are retained.
    Existing build_study_plan binds current private capital, fee and rule terms,
    installed sources and the prior negative research digest as usual.
    """
    for value in (now, capture_start):
        _require(type(value) is datetime and value.utcoffset() is not None,
                 "SHORT_STUDY_AWARE_TIME_REQUIRED")
    _require(capture_start >= now + timedelta(minutes=2), "SHORT_STUDY_START_MARGIN_REQUIRED")
    for value in (plan_id, study_id):
        _require(type(value) is str and _ID.fullmatch(value) is not None,
                 "SHORT_STUDY_ID_INVALID")
    template, programs, names = _draft(raw_draft)
    _require(plan_id != names["plan_id"] and study_id != template.study_id,
             "SHORT_STUDY_NEW_IDS_REQUIRED")
    _require(template.bar_seconds == BAR_SECONDS, "SHORT_STUDY_FIVE_MINUTE_DRAFT_REQUIRED")
    _require(template.minimum_observations >= RETURN_INTERVALS
             and template.capture_end - template.capture_start >= timedelta(hours=48),
             "SHORT_STUDY_INPUT_WINDOW_TOO_SHORT")
    revised = replace(template, study_id=study_id, preregistered_at=now,
                      capture_start=capture_start, capture_end=capture_start + timedelta(hours=48),
                      minimum_observations=RETURN_INTERVALS)
    plan = build_study_plan(profile, programs, template=revised, plan_id=plan_id,
                            asset=names["asset"], risk_group=names["risk_group"])
    body = {"schema_version": 1, "plan_id": plan_id, "asset": names["asset"],
            "risk_group": names["risk_group"], "template": json.loads(protocol_json(revised)),
            "programs": [json.loads(program_json(program)) for program in programs]}
    return json.dumps(body, sort_keys=True, indent=2) + "\n", plan


def _arguments(argv):
    _require(type(argv) in (list, tuple) and all(type(v) is str for v in argv),
             "SHORT_STUDY_ARGUMENTS_INVALID")
    if tuple(argv) in (("--help",), ("-h",)):
        return None, False
    values = list(argv)
    emit = values[-1:] == ["--emit-draft"]
    if emit:
        values.pop()
    _require(len(values) == 2 * len(_OPTIONS), "SHORT_STUDY_ARGUMENTS_INVALID")
    result = {}
    for key, value in zip(values[::2], values[1::2]):
        _require(key.startswith("--") and key[2:] in _OPTIONS and key[2:] not in result
                 and value and not value.startswith("--"), "SHORT_STUDY_ARGUMENTS_INVALID")
        result[key[2:]] = value
    return result, emit


def main(argv=None):
    try:
        args, emit = _arguments(sys.argv[1:] if argv is None else argv)
        if args is None:
            print(__doc__)
            return 0
        now, start = _time(args["now"]), _time(args["capture-start"])
        profile = parse_profile_json(_read_file(args["profile"], MAX_CONFIG_BYTES))
        raw, plan = prepare_draft(profile, _read_file(args["draft"], _DRAFT_LIMIT), now=now,
                                  capture_start=start, plan_id=args["plan-id"], study_id=args["study-id"])
        if emit:
            print(raw, end="")
        else:
            print(json.dumps({"draft_valid": True, "plan_sha256": validate_study_plan(plan),
                "hours": 48, "bar_seconds": BAR_SECONDS, "return_intervals": RETURN_INTERVALS,
                "book_observations": BOOK_OBSERVATIONS, "candidates": len(plan.candidates),
                "execution_ready": False, "source_authenticated": False, "published": False,
                "owner_approval_verified": False,
                "reasons": ["SHORT_STUDY_NEW_PREREGISTRATION_REQUIRED",
                            "SHORT_STUDY_POWER_AND_INDEPENDENCE_UNVERIFIED"]}, sort_keys=True))
        return 0
    except ValueError as exc:
        code = exc.code if type(exc) is ProfileError else str(exc)
        if type(exc) is ValueError or _CODE.fullmatch(code) is None:
            code = "SHORT_STUDY_INPUT_REFUSED"
    except (OSError, TypeError, AttributeError, ArithmeticError, RecursionError, KeyError):
        code = "SHORT_STUDY_INPUT_REFUSED"
    print(json.dumps({"draft_valid": False, "execution_ready": False,
                      "owner_approval_verified": False, "reasons": [code]}, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
