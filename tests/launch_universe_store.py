"""The universe snapshot store and its command (spec section 5): temporary state only and synthetic public answers
through the fake transport._send; no venue call, key or real home."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner, rules
from core.isolation import state_root
from execution_launch import universe_store as US
from tests import accounts_universe as AU
from tests import execution_fixtures as EF

SHA_A, SHA_B = "a" * 64, "b" * 64


def refused(call, code):
    try:
        call()
    except US.UniverseStoreError as exc:
        assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError(f"not refused: {code}")


def names():
    return sorted(path.name for path in owner.universe_dir(AU.DAY).iterdir())


def test_a_rebuild_adds_a_file_and_leaves_the_earlier_one_intact():
    first = US.write_snapshot(b"first", AU.DAY, SHA_A)
    second = US.write_snapshot(b"second", AU.DAY, SHA_B)
    assert first == owner.universe_path(AU.DAY, SHA_A) and second == owner.universe_path(AU.DAY, SHA_B)
    assert first.read_bytes() == b"first" and second.read_bytes() == b"second"
    assert names() == [SHA_A + ".json", SHA_B + ".json"]


def test_an_existing_snapshot_is_refused_and_never_replaced():
    path = US.write_snapshot(b"first", AU.DAY, SHA_A)
    refused(lambda: US.write_snapshot(b"other", AU.DAY, SHA_A), "UNIVERSE_SNAPSHOT_EXISTS")
    assert path.read_bytes() == b"first" and names() == [SHA_A + ".json"]


def test_a_snapshot_that_appears_during_the_write_is_kept_and_the_temporary_file_removed():
    """Windows rename refuses an existing name (the owner PC); see the ponytail note in write_snapshot for POSIX."""
    if os.name != "nt":
        return
    real = US.checked_target

    def racing(path, what="path", *, within=None):
        if what == "universe snapshot":
            Path(path).write_bytes(b"racer")
        return real(path, what, within=within)

    with patch.object(US, "checked_target", racing):
        refused(lambda: US.write_snapshot(b"mine", AU.DAY, SHA_A), "UNIVERSE_SNAPSHOT_EXISTS")
    assert owner.universe_path(AU.DAY, SHA_A).read_bytes() == b"racer" and names() == [SHA_A + ".json"]


def test_bad_arguments_are_refused_before_any_write():
    for raw, day, sha256 in ((b"", AU.DAY, SHA_A), ("text", AU.DAY, SHA_A), (b"x", "2026-11-11", SHA_A),
                             (b"x", AU.DAY, "A" * 64), (b"x", AU.DAY, "a" * 63), (b"x", AU.DAY, None)):
        refused(lambda: US.write_snapshot(raw, day, sha256), "UNIVERSE_STORE_INPUT_INVALID")
    assert not owner.universe_dir(AU.DAY).parent.exists()


def run(argv):
    out = StringIO()
    with redirect_stdout(out):
        code = US.main(argv)
    return code, json.loads(out.getvalue())


def root_args():
    return ["snapshot", "--state-root", str(state_root().absolute())]


def not_written(reason):
    return 2, {"command": "snapshot", "written": False, "reasons": [reason]}


def test_command_writes_one_verified_snapshot_for_today():
    with patch.object(US, "_active_rule", return_value=AU.RULE), patch.object(US, "_wall_clock", return_value=AU.BUILT), \
            EF.serve(AU.routes()) as calls:
        code, out = run(root_args())
    assert code == 0 and out["written"] is True and out["day"] == "2026-11-11", out
    path = owner.universe_path(AU.DAY, out["snapshot_sha256"])
    universe = rules.verify_universe_snapshot(path.read_bytes(), rules.universe_rule_sha256(AU.RULE))
    assert universe.snapshot_sha256 == out["snapshot_sha256"] and len(calls) == 5
    assert names() == [path.name]


def test_command_refuses_another_root_or_bad_arguments_before_any_read():
    root = state_root().absolute()
    for argv, reason in ((["snapshot", "--state-root", str(root / "other")], "UNIVERSE_STATE_ROOT_MISMATCH"),
                         (["snapshot", "--state-root", "relative-root"], "UNIVERSE_STATE_ROOT_MISMATCH"),
                         (["snapshot"], "UNIVERSE_ARGUMENTS_INVALID"),
                         (["build", "--state-root", str(root)], "UNIVERSE_ARGUMENTS_INVALID"),
                         (["snapshot", "--state-root", str(root), "--force"], "UNIVERSE_ARGUMENTS_INVALID")):
        with patch.object(US, "_active_rule", return_value=AU.RULE):
            assert run(argv) == not_written(reason), argv
    assert not owner.universe_dir(AU.DAY).parent.exists()


def test_command_writes_nothing_when_a_read_fails():
    error = lambda call: (500, {"Date": AU.BUILT_HEADER}, b'{"error":{"name":"server_error"}}')
    with patch.object(US, "_active_rule", return_value=AU.RULE), patch.object(US, "_wall_clock", return_value=AU.BUILT), \
            EF.serve(AU.routes(error)):
        assert run(root_args()) == not_written("UNIVERSE_INQUIRY_FAILED")
    assert not owner.universe_dir(AU.DAY).parent.exists()


def test_command_takes_the_rule_from_the_newest_approved_venue_facts():
    assert run(root_args()) == not_written("UNIVERSE_NO_RULE")          # the temporary home holds no approved state

    def state(rule):
        return SimpleNamespace(venues=SimpleNamespace(venues={"upbit": SimpleNamespace(universe_rule=rule)}))

    with patch.object(owner, "latest_snapshot", return_value=state(AU.RULE)):
        assert US._active_rule() == AU.RULE
    for value in (state(None), SimpleNamespace(venues=None), SimpleNamespace(venues=SimpleNamespace(venues={}))):
        with patch.object(owner, "latest_snapshot", return_value=value):
            refused(US._active_rule, "UNIVERSE_NO_RULE")
    assert US._code(RuntimeError("C:/private/path")) == "UNIVERSE_SNAPSHOT_REFUSED"
    assert US._code(US.UniverseStoreError("UNIVERSE_SNAPSHOT_EXISTS")) == "UNIVERSE_SNAPSHOT_EXISTS"
