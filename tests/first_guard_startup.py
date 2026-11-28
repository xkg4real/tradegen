"""Native launcher and committed preparation regressions with disposable accounts and journals."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stdout
from dataclasses import asdict, replace
from datetime import timedelta
from io import StringIO
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from execution_launch.driver import DeploymentWindow
from execution_launch.profile import profile_body
from tests import launch_committed_producer as Producer
from tests import launch_coordinator_committed as Scheduler
from tests import launch_guard_generation_archive as Archive
from tests.control_session import selected
from tests.launch_committed_startup import snapshot
from tests.launch_owner_rehearsal import plain, write_audit
from tools.owner import live


def request(folder, e, *, unit=None):
    def document(name, value):
        path = folder / (name + ".json")
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)
    stamp = e.clock()
    window = DeploymentWindow(deployment_id="startup-inspection", start=stamp, end=stamp+timedelta(minutes=10))
    state = e.baseline_store.load(expected_head=e.baseline_head.read())
    audit = write_audit(folder, state, window)
    args = e.storage.args
    input_digest = e.input.archive_digest if unit is None else unit.input_archive_digest
    if unit is None:
        completion_digest = None if e.completion is None else e.completion.archive_digest
    else:
        completion_digest = unit.completion_archive_digest
    store_request = {"schema_version": 1, "sealed_root": str(args["roots"].sealed_root),
        "backup_root": str(args["roots"].backup_root), "archive_head": args["head_name"],
        "archive_limits": document("limits", asdict(args["limits"])), "guard_head": e.guard_head._dir.name,
        "baseline_head": e.baseline_head._dir.name, "input_archive_sha256": input_digest,
        "completion_archive_sha256": completion_digest}
    config = dict.fromkeys(live._CONFIG_FIELDS, "unneeded-for-local-inspection")
    config.update(schema_version=1, kind="tradegen-controlled-live/1", state_root=str(e.home),
        head_root=str(e.head_root), profile=document("profile", profile_body(e.profile)),
        account_audit=document("audit", audit), window=document("window", plain(asdict(window))),
        evaluated_at=stamp.isoformat(), monitor_until=window.end.isoformat())
    return document("live", config), document("record", store_request)


def test_native_inspect_checks_record_and_never_calls_owner_or_trading_services():
    for complete in (False, True):
        with Archive.fixture(completed=complete) as e, tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            config, record = request(Path(tmp), e)
            before = snapshot(e)
            for target in (live.owner, live):
                for name in (("load_context", "load_owner_snapshot") if target is live.owner
                             else ("build_live", "_LiveLock", "VenueOrderTransport", "_AccountSource")):
                    stack.enter_context(patch.object(target, name, side_effect=AssertionError("unexpected live I/O")))
            # The CLI clock is genuine; these fixtures are historical, so inspect stays stale.
            output = StringIO()
            with redirect_stdout(output):
                assert live.main(["--config", config, "--inspect-startup", record]) == 2, output.getvalue()
            result = json.loads(output.getvalue())
            assert not result["execution_ready"] and result["new_entries_blocked"] and not result["source_authenticated"]
            assert result["durable_status"] == ("CONSISTENT" if complete else "FRESH")
            assert result["current_status"] != "FRESH" and config not in output.getvalue()
            assert snapshot(e) == before
            current = live.inspect_startup(config, record, clock=e.clock)
            if complete:
                assert current["current_status"] == "FRESH"
                # This flat fixture contains two completed orders whose origins were
                # never recorded in the control journal.
                assert current["origin_reason"] == "OWNERSHIP_ORDER_ORIGIN_UNKNOWN", current
                assert current["unknown_order_count"] == 2
                assert not current["permanent_halt"] and not current["daily_stop_at_checkpoint"]
            assert snapshot(e) == before


def test_inspect_refuses_foreign_account_anchor_and_damaged_archive_without_repair():
    with Archive.fixture(completed=True) as e, tempfile.TemporaryDirectory() as tmp:
        config, record = request(Path(tmp), e)
        audit_path = Path(json.loads(Path(config).read_text(encoding="utf-8"))["account_audit"])
        initial = audit_path.read_bytes()
        audit = json.loads(initial)
        audit["baseline_anchor_sha256"] = "f" * 64
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        before = snapshot(e)
        try:
            live.inspect_startup(config, record, clock=e.clock)
        except live.LiveError as exc:
            assert str(exc) == "LIVE_STARTUP_BINDING_CHANGED"
        else:
            raise AssertionError("foreign anchor accepted")
        audit_path.write_bytes(initial)
        e.journal._root.joinpath("control.lock").unlink()
        after = snapshot(e)
        output = StringIO()
        with redirect_stdout(output):
            assert live.main(["--config", config, "--inspect-startup", record]) == 2
        assert not json.loads(output.getvalue())["execution_ready"]
        assert snapshot(e) == after and before != after


def test_held_unattributed_filled_order_stops_preparation_before_strategy_build():
    with Producer.fixture(held=True, bind_startup=False) as e:
        coordinator = Scheduler.build(e)
        Producer.arm_interval(e)
        coordinator.bootstrap()
        before = e.journal.snapshot()
        def unavailable(_):
            raise AssertionError("builder ran before origin reconciliation")
        Scheduler.refuse(lambda: coordinator.prepare(build=unavailable), "COORDINATOR_PREPARATION_ORDER_ORIGIN_UNVERIFIED")
        assert e.journal.snapshot() == before and not Scheduler.creates(e)


def test_permanent_halt_after_startup_is_read_before_strategy_build():
    with Producer.fixture(bind_startup=False, untraded=True) as e:
        coordinator = Scheduler.build(e)
        Producer.arm_interval(e)
        coordinator.bootstrap()
        with e.journal.transaction() as tx:
            tx.append("halt", {"floor": "0"}, now=e.clock())
        before = e.journal.snapshot()
        def unavailable(_):
            raise AssertionError("builder ran before current halt check")
        try:
            coordinator.prepare(build=unavailable)
        except ValueError:
            pass
        else:
            raise AssertionError("permanent halt accepted")
        assert e.journal.snapshot() == before and not Scheduler.creates(e)


def test_generation_change_after_builder_blocks_locked_preparation_without_receipt():
    from tests.launch_committed_producer_integration import actual_reviewed_producer_fixture
    from tools.owner.launch import PreparationInputs
    with actual_reviewed_producer_fixture(bind_startup=False, untraded=True) as e:
        coordinator = Scheduler.reviewed_build(e)
        Producer.arm_interval(e)
        status = coordinator.bootstrap()
        assert coordinator._ready, status
        seen = []
        def build(at):
            plan, inputs, seed = selected(at)
            # The generic odds fixture models a smaller account than this
            # signed synthetic floor. Use this study's actual starting capital.
            plan = replace(plan, stake_krw=float(e.profile.policy.initial_equity))
            # Represents a second process committing a journal row after the
            # coordinator selected its generation but before session receipt append.
            with e.journal.transaction() as tx:
                tx.append("kill", {"session_id": "UnrelatedSyntheticSession", "reason": "independent stop"}, now=e.clock())
            seen.append(at)
            return PreparationInputs(selected_plan=plan, inputs=inputs, selection_seed_hex=seed,
                                     expires_at=at+timedelta(minutes=10))
        try:
            coordinator.prepare(build=build)
        except ValueError as exc:
            assert str(exc) == "COORDINATOR_PREPARATION_GENERATION_CHANGED", (str(exc), str(exc.__context__))
        else:
            raise AssertionError("changed control head accepted")
        assert seen and e.journal.snapshot()[-1]["kind"] == "kill"
        assert not any(r["kind"] == "session_prepared" for r in e.journal.snapshot())
        assert not Scheduler.creates(e)

def test_legitimate_untraded_account_has_a_consistent_inspection_without_execution_authority():
    with Producer.fixture(untraded=True) as e, tempfile.TemporaryDirectory() as tmp:
        unit = Producer.advance(e)
        config, record = request(Path(tmp), e, unit=unit)
        before = Producer.durable(e)
        report = live.inspect_startup(config, record, clock=e.clock)
        assert report["local_status"] == "CONSISTENT", report
        assert report["origin_ready"] and report["unknown_order_count"] == report["app_open_count"] == 0
        assert not report["execution_ready"] and report["new_entries_blocked"]
        assert Producer.durable(e) == before and not e.adapter.requests


def test_session_preparation_refuses_an_arbitrary_callback_without_passing_a_transaction():
    from execution_control.session import PreparationError, prepare_session
    called = []
    def foreign(*args):
        called.append(args)
        raise AssertionError("untrusted callable reached")
    try:
        prepare_session(journal=None, session_id="", selected_plan=None, inputs=None, positions=None, policy=None,
            instrument_rules=None, now=None, selection_seed_hex="", account_scope="", market="", quote_currency="",
            clock=lambda: None, positions_asof=None, committed_preparation=foreign)
    except PreparationError as exc:
        assert str(exc) == "COMMITTED_PREPARATION_INPUT_INVALID"
    else:
        raise AssertionError("arbitrary callback accepted")
    assert not called
