"""Owner universe commands over synthetic doubles; no research, authority or market access is fabricated."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch.driver import DeploymentWindow
from tests import compliance_fixtures as F
from tests.control_session import selected
from tests.launch_baseline_head import head_root
from tests.launch_coordinator import build, fixture
from tests.launch_owner_ops import refused
from tools.owner import launch as O


def test_console_odds_keeps_only_preparation_batch_and_exports_universe_status():
    with fixture() as env:
        c = build(env)
        plan, inputs, seed = selected(env.fake.now)
        runtime = O.OwnerRuntime(c, preparation_provider=lambda: O.PreparationInputs(
            selected_plan=plan, inputs=inputs, selection_seed_hex=seed))
        batch = SimpleNamespace(batch_digest="b" * 64,
            coins=(SimpleNamespace(passed=True), SimpleNamespace(passed=False)))
        prepared = SimpleNamespace(session_id="Lsynthetic-universe", prepared_at=env.fake.now,
            expires_at=env.fake.now, record_digest="c" * 64)
        calls = []
        with patch.object(c, "odds_batch", side_effect=lambda template, read_bars:
                          calls.append((template, read_bars)) or batch), \
                patch.object(c, "prepare", side_effect=lambda **kwargs:
                             calls.append(kwargs["universe_batch"]) or prepared):
            assert runtime.command("odds") == {"command": "odds", "batch_digest": "b" * 64,
                "coins": 2, "passed": 1, "execution_ready": False}
            assert calls == [(plan, O.daily_bars)]
            result = runtime.command("prepare")
            assert result["session_id"] == "Lsynthetic-universe" and calls[-1] is batch
            assert result["owner_activation_performed"] is False and result["execution_ready"] is False
        status = replace(c.status(), held_symbol="KRW-BTC", trade_symbol="KRW-BTC",
            snapshot_day=date(2030, 1, 2), snapshot_sha256="a" * 64, universe_state="in_force",
            held_flag="warning", allow_count=2, buy_block_reasons=("SYNTHETIC_BLOCK",),
            disarm_failed=True, window_ended_missed_slot=True, notification_failed=True)
        with patch.object(c, "status", return_value=status):
            report = runtime.status()
        assert {key: report[key] for key in ("held_symbol", "trade_symbol", "snapshot_day", "snapshot_sha256",
            "universe_state", "held_flag", "allow_count", "buy_block_reasons", "disarm_failed",
            "window_ended_missed_slot")} == {
            "held_symbol": "KRW-BTC", "trade_symbol": "KRW-BTC", "snapshot_day": "2030-01-02",
            "snapshot_sha256": "a" * 64, "universe_state": "in_force", "held_flag": "warning", "allow_count": 2,
            "buy_block_reasons": ["SYNTHETIC_BLOCK"], "disarm_failed": True, "window_ended_missed_slot": True}
        assert report["notification_failed"] is True
        assert json.loads(json.dumps(report)) == report
        assert not report["worker_running"] and env.adapter.requests == [] and env.producer.prefetches == []


def test_failed_odds_replacement_clears_prior_batch_and_console_sanitizes_failure():
    with fixture() as env:
        c = build(env)
        plan, inputs, seed = selected(env.fake.now)
        runtime = O.OwnerRuntime(c, preparation_provider=lambda: O.PreparationInputs(
            selected_plan=plan, inputs=inputs, selection_seed_hex=seed))
        batch = SimpleNamespace(batch_digest="b" * 64, coins=())
        output = []
        with patch.object(c, "odds_batch", return_value=batch):
            runtime.odds()
        assert runtime._batch is batch
        with patch.object(c, "odds_batch", side_effect=RuntimeError("SYNTHETIC_PRIVATE_PROVIDER_TEXT")):
            O.serve(runtime, stream=StringIO("odds\nclose\n"), emit=output.append)
        assert runtime._batch is None
        assert output[0] == {"command": "refused", "execution_ready": False,
                             "reasons": ["OWNER_OPERATION_REFUSED"]}
        assert "SYNTHETIC_PRIVATE_PROVIDER_TEXT" not in json.dumps(output)
        assert env.adapter.requests == []


def test_no_preparation_provider_cannot_start_odds_or_prepare_or_reuse_a_batch():
    with fixture() as env:
        c = build(env)
        runtime = O.OwnerRuntime(c)
        runtime._batch = object()
        with patch.object(c, "odds_batch", side_effect=AssertionError("unexpected research")), \
                patch.object(c, "prepare", side_effect=AssertionError("unexpected preparation")):
            refused(runtime.odds, "OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED")
            refused(runtime.prepare, "OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED")
        assert runtime._batch is None and env.adapter.requests == []
        assert env.producer.prefetches == [] and not runtime.status()["worker_running"]


def test_window_loader_preserves_fixed_limit_and_requires_explicit_universe_for_72_hours():
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "window.json"
        def write(hours, microseconds=0):
            path.write_text(json.dumps({"deployment_id": "synthetic-owner-window", "start": start.isoformat(),
                "end": (start + timedelta(hours=hours, microseconds=microseconds)).isoformat()}))
        write(24)
        assert O.read_window(str(path)).end - start == timedelta(hours=24)
        write(24, 1)
        refused(lambda: O.read_window(str(path)), "OWNER_WINDOW_INVALID")
        assert O.read_window(str(path), universe=True).end > start + timedelta(hours=24)
        write(72)
        assert O.read_window(str(path), universe=True).end - start == timedelta(hours=72)
        refused(lambda: O.read_window(str(path)), "OWNER_WINDOW_INVALID")
        write(72, 1)
        refused(lambda: O.read_window(str(path), universe=True), "OWNER_WINDOW_INVALID")
        refused(lambda: O.read_window(str(path), universe=1), "OWNER_WINDOW_SCOPE_INVALID")


def test_fixed_history_setup_still_refuses_over_24_hours_before_writes():
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    window = DeploymentWindow(deployment_id="synthetic-too-long", start=start,
                              end=start + timedelta(hours=24, microseconds=1))
    with F.temp_home() as home, head_root() as heads:
        refused(lambda: O.setup_history(window=window, state_directory=home, head_directory=heads,
            now=start-timedelta(seconds=1)), "OWNER_HISTORY_WINDOW_ALREADY_STARTED_OR_INVALID")
        assert list(home.iterdir()) == [] and list(heads.iterdir()) == []


def test_universe_history_setup_accepts_exact_72_hours_and_rejects_overspan_before_writes():
    from tests.launch_owner_ops import history_storage_fixture
    env, policy = history_storage_fixture()
    window = replace(env.window, end=env.window.start + timedelta(hours=72))
    kwargs = dict(protocol=env.protocol, storage_policy=policy, now=window.start - timedelta(seconds=1))
    with F.temp_home() as home, head_root() as heads:
        result = O.setup_history(window=window, state_directory=home, head_directory=heads, **kwargs)
        assert result["initialized"] is True and result["execution_ready"] is False
    with F.temp_home() as home, head_root() as heads:
        refused(lambda: O.setup_history(window=replace(window, end=window.end+timedelta(microseconds=1)),
            state_directory=home, head_directory=heads, **kwargs),
            "OWNER_HISTORY_WINDOW_ALREADY_STARTED_OR_INVALID")
        assert list(home.iterdir()) == [] and list(heads.iterdir()) == []


def test_cli_derives_72_hour_scope_from_validated_protocol_and_keeps_storage_pair():
    from dataclasses import asdict
    from execution_launch.history_storage import policy_bytes
    from execution_launch.strategy import protocol_json
    from tests.launch_owner_ops import history_storage_fixture, invoke
    env, policy = history_storage_fixture()
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    window = replace(env.window, start=start, end=start+timedelta(hours=72))
    with F.temp_home() as home, head_root() as heads, tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        window_path, protocol_path, policy_path = (folder / n for n in ("window.json", "protocol.json", "storage.json"))
        window_path.write_text(json.dumps(asdict(window), default=lambda value: value.isoformat()))
        protocol_path.write_text(protocol_json(env.protocol))
        policy_path.write_bytes(policy_bytes(policy))
        args = ("setup-history", "--window", str(window_path), "--state-root", str(home), "--head-root", str(heads))
        code, text = invoke(*args)
        assert code == 2 and json.loads(text)["reasons"] == ["OWNER_WINDOW_INVALID"]
        assert list(home.iterdir()) == [] and list(heads.iterdir()) == []
        code, text = invoke(*args, "--protocol", str(protocol_path), "--history-storage", str(policy_path))
        result = json.loads(text)
        assert code == 0 and result["initialized"] is True and result["execution_ready"] is False


def test_actual_composition_preserves_fixed_24_hour_limit_before_driver_or_history():
    from execution_launch import coordinator as C
    from tests import launch_driver as LD
    env = LD.fixture()
    window = replace(env.window, end=env.window.start+timedelta(hours=24, microseconds=1))
    with F.temp_home() as home, head_root() as heads:
        refused(lambda: C._compose_driver(profile=env.profile, program=env.program, protocol=env.protocol,
            window=window, clock=lambda: window.start-timedelta(seconds=1), head_root=heads),
            "COORDINATOR_WINDOW_SPAN_UNSUPPORTED")
        assert list(home.iterdir()) == [] and list(heads.iterdir()) == []
