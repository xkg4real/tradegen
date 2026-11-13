"""Owner operations over invented evidence, private temporary roots and dry adapters only."""
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from datetime import timedelta
from io import StringIO
import json
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch

from execution_accounts.baseline import state_json
from execution_accounts.baseline_store import CheckpointStore
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.coordinator import compose, compose_driver
from execution_launch.driver import describe_fixed_driver
from execution_launch.profile import profile_body
from execution_launch.program import program_json
from execution_launch.strategy import protocol_json
from tests import compliance_fixtures as F
from tests import launch_driver as LD
from tests.accounts_baseline_integration import initial
from tests.control_session import selected
from tests.launch_baseline_head import head_root
from tests.launch_coordinator import (HOLD, build, compose_args, fixture, history_journal,
                                      private_inputs, reviewed, seconds)
from tests.launch_windows_owner_authority import signed_home
from tools.owner import launch as O


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected refusal " + code)


def invoke(*args):
    output = StringIO()
    with redirect_stdout(output):
        result = O.main(list(args))
    return result, output.getvalue()


def test_cli_unknown_or_missing_commands_refuse_without_effects_or_echoes():
    with patch.object(O, "read_file", side_effect=AssertionError("file read")), \
            patch.object(O, "state_root", side_effect=AssertionError("state read")):
        code, text = invoke("--help")
        assert code == 0 and "setup-account" in text
        for args in (("activate",), ("setup-account", "--state", "secret-path"),
                     ("export-manifest", "--repo", "secret", "--repo", "second"),
                     ("run", "--plugin", "secret-module")):
            code, text = invoke(*args)
            assert code == 2 and "secret" not in text
            assert not json.loads(text)["execution_ready"]


def test_account_setup_binds_reviewed_digest_in_two_roots_and_never_reinitializes():
    state = initial()
    with F.temp_home() as home, head_root() as hroot, tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "anchor.json"
        path.write_text(state_json(state))
        kwargs = dict(state_path=str(path), reviewed_head=state.state_digest, state_directory=home,
                      head_directory=hroot, now=state.asof)
        report = O.setup_account(**kwargs)
        assert report["initialized"] and not report["source_authenticated"] and not report["execution_ready"]
        store = CheckpointStore(root=home)
        head = BaselineHead(root=hroot, name="account-baseline", chain=CheckpointChain(store))
        assert head.read() == state.state_digest
        assert store.load(expected_head=head.read()) == state
        before = (home / "execution-baseline" / "checkpoint.json").read_bytes()
        refused(lambda: O.setup_account(**kwargs), "OWNER_EXISTING_HEAD_REFUSED")
        assert (home / "execution-baseline" / "checkpoint.json").read_bytes() == before


def test_account_setup_bad_digest_stale_anchor_and_root_mismatch_write_nothing():
    state = initial()
    with F.temp_home() as home, head_root() as hroot, tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "anchor.json"
        path.write_text(state_json(state))
        kwargs = dict(state_path=str(path), reviewed_head=state.state_digest, state_directory=home,
                      head_directory=hroot, now=state.asof)
        refused(lambda: O.setup_account(**(kwargs | {"now": state.asof + seconds(31)})),
                "OWNER_ANCHOR_STALE_OR_FUTURE")
        refused(lambda: O.setup_account(**(kwargs | {"now": state.asof - seconds(1)})),
                "OWNER_ANCHOR_STALE_OR_FUTURE")
        refused(lambda: O.setup_account(**(kwargs | {"reviewed_head": "not-a-hash"})),
                "OWNER_REVIEWED_HEAD_REQUIRED")
        refused(lambda: O.setup_account(**(kwargs | {"state_directory": Path(folder)})),
                "OWNER_STATE_ROOT_MISMATCH")
        assert list(home.iterdir()) == [] and list(hroot.iterdir()) == []


def test_interrupted_account_setup_never_adopts_the_orphaned_checkpoint():
    state = initial()
    with F.temp_home() as home, head_root() as hroot, tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "anchor.json"
        path.write_text(state_json(state))
        kwargs = dict(state_path=str(path), reviewed_head=state.state_digest, state_directory=home,
                      head_directory=hroot, now=state.asof)
        with patch.object(BaselineHead, "initialize_reviewed_head", side_effect=O.OwnerOperationError("INTERRUPTED")):
            refused(lambda: O.setup_account(**kwargs), "INTERRUPTED")
        before = (home / "execution-baseline" / "checkpoint.json").read_bytes()
        refused(lambda: O.setup_account(**kwargs), "BASELINE_STORE_ALREADY_INITIALIZED")
        assert list(hroot.iterdir()) == []
        assert (home / "execution-baseline" / "checkpoint.json").read_bytes() == before


def test_partial_independent_head_directory_is_not_adopted_as_empty_setup():
    state = initial()
    with F.temp_home() as home, head_root() as hroot, tempfile.TemporaryDirectory() as folder:
        (hroot / "account-baseline").mkdir()
        (hroot / "account-baseline" / "head.lock").write_bytes(b"0")
        path = Path(folder) / "anchor.json"
        path.write_text(state_json(state))
        refused(lambda: O.setup_account(state_path=str(path), reviewed_head=state.state_digest,
            state_directory=home, head_directory=hroot, now=state.asof), "OWNER_EXISTING_HEAD_REFUSED")
        assert list(home.iterdir()) == []


def test_unsigned_driver_export_precedes_review_and_reuses_exact_history_identity():
    e = LD.fixture()
    with F.temp_home() as home, head_root() as hroot:
        kwargs = dict(window=e.window, state_directory=home, head_directory=hroot,
                      now=e.window.start - timedelta(minutes=1))
        assert O.setup_history(**kwargs)["initialized"]
        refused(lambda: O.setup_history(**kwargs), "OWNER_EXISTING_HEAD_REFUSED")
        files = {"profile.json": json.dumps(profile_body(e.profile)),
                 "program.json": program_json(e.program),
                 "protocol.json": protocol_json(e.protocol)}
        with private_inputs(files) as paths:
            args = dict(profile_path=paths["profile.json"], program_path=paths["program.json"],
                        protocol_path=paths["protocol.json"], window=e.window,
                        clock=lambda: kwargs["now"], head_root=hroot)
            with patch("execution_launch.coordinator.CurrentOwnerAuthority", side_effect=AssertionError("owner read")), \
                    patch("execution_launch.coordinator.ReviewVerifiers", side_effect=AssertionError("signed review")):
                result = compose_driver(**args)
                assert result.identity == describe_fixed_driver(result.driver)
                assert len(history_journal(home, e.window).read_bytes().splitlines()) == 1
                again = compose_driver(**args)
                assert again.identity == result.identity and again.driver is not result.driver
                assert len(history_journal(home, e.window).read_bytes().splitlines()) == 1


def test_history_setup_refuses_started_window_without_initializing_head():
    e = LD.fixture()
    with F.temp_home() as home, head_root() as hroot:
        refused(lambda: O.setup_history(window=e.window, state_directory=home, head_directory=hroot,
                                        now=e.window.start), "OWNER_HISTORY_WINDOW_ALREADY_STARTED_OR_INVALID")
        assert list(hroot.iterdir()) == [] and list(home.iterdir()) == []


def test_bootstrap_prepares_real_process_session_without_start_or_activation():
    with fixture() as env:
        c = build(env)
        calls = []

        def provider():
            calls.append(True)
            plan, inputs, seed = selected(env.fake.now)
            return O.PreparationInputs(selected_plan=plan, inputs=inputs, selection_seed_hex=seed)
        runtime = O.OwnerRuntime(c, preparation_provider=provider)
        assert not runtime.status()["worker_running"] and env.producer.prefetches == []
        report = runtime.bootstrap()
        assert report["published_units"] == 1 and env.books.reads == 0 and env.adapter.requests == []
        prepared = runtime.prepare()
        assert calls == [True] and c._session_for(prepared["session_id"]) is c._launch.prepared
        assert not prepared["owner_activation_performed"] and not prepared["execution_ready"]
        assert not runtime.status()["worker_running"] and env.adapter.requests == []


def test_disarm_records_local_kill_without_claiming_venue_cancel_or_fill():
    with fixture() as env:
        c = build(env)
        c.bootstrap()
        plan, inputs, seed = selected(env.fake.now)
        prepared = c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed)
        report = O.OwnerRuntime(c).disarm()
        assert report["local_strategy_stopped"] and report["journal_kill_written"]
        assert report["session_prepared"] and report["owner_disarm_recorded"]
        assert not report["venue_orders_cancelled"] and not report["positions_liquidated"]
        with c._journal.transaction() as tx:
            kills = [row for row in tx.events if row["kind"] == "kill"]
        assert len(kills) == 1 and kills[0]["data"]["session_id"] == prepared.session_id
        assert env.adapter.requests == [] and c.status().strategy_stopped
        refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed), "COORDINATOR_STOPPED")


def test_disarm_with_broken_account_still_kills_durably_and_reports_owner_record_missing():
    with fixture() as env:
        c = build(env)
        c.bootstrap()
        plan, inputs, seed = selected(env.fake.now)
        prepared = c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed)
        env.producer.fail = RuntimeError("private-account-error")
        env.fake.now += seconds(31)  # last published receipt has expired; disarm starts no fresh capture
        captures = len(env.producer.prefetches)
        report = O.OwnerRuntime(c).disarm()
        assert report["journal_kill_written"] and not report["owner_disarm_recorded"]
        with c._journal.transaction() as tx:
            kills = [row for row in tx.events if row["kind"] == "kill"]
        assert kills[-1]["data"] == {"session_id": prepared.session_id, "reason": "clock_ambiguous"}
        assert c.status().reasons == ("COORDINATOR_DISARM_JOURNAL_ONLY",)
        assert len(env.producer.prefetches) == captures
        assert env.adapter.requests == [] and "private-account-error" not in repr(report)


def test_disarm_clock_rollback_or_journal_failure_never_claims_owner_disarm():
    with fixture() as env:
        c = build(env)
        c.bootstrap()
        plan, inputs, seed = selected(env.fake.now)
        c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed)
        env.fake.now = env.t0 - seconds(1)
        report = O.OwnerRuntime(c).disarm()
        assert report["journal_kill_written"] and not report["owner_disarm_recorded"]
        assert c.status().strategy_stopped and c.status().new_entry_blocked
    with fixture() as env:
        c = build(env)
        c.bootstrap()
        plan, inputs, seed = selected(env.fake.now)
        c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed)
        with patch.object(c._controller, "kill", side_effect=RuntimeError("PRIVATE_JOURNAL_DETAIL")):
            refused(O.OwnerRuntime(c).disarm, "COORDINATOR_DISARM_RECORD_REFUSED")
        assert c.status().strategy_stopped and c.status().new_entry_blocked
        with c._journal.transaction() as tx:
            assert not any(row["kind"] == "kill" for row in tx.events)


def test_runtime_worker_runs_once_and_closes_with_bounded_lifecycle():
    with fixture() as env:
        env.signal[0] = HOLD
        c = build(env)
        runtime = O.OwnerRuntime(c)
        runtime.start()
        runtime._thread.join(10)
        assert not runtime._thread.is_alive()
        assert runtime.status()["phase"] == "closed" and not runtime.status()["worker_failure"]
        assert env.adapter.requests == []
        refused(runtime.start, "OWNER_RUNTIME_ALREADY_STARTED")
        assert runtime.close()["closed"]
        refused(lambda: runtime.close(timeout=float("inf")), "OWNER_CLOSE_TIMEOUT_INVALID")


def test_console_unknown_and_oversized_commands_are_redacted_and_close_runtime():
    with fixture() as env:
        runtime = O.OwnerRuntime(build(env))
        output = []
        O.serve(runtime, stream=StringIO("private-command\nstatus\nclose\n"), emit=output.append)
        assert output[0]["reasons"] == ["OWNER_COMMAND_INVALID"]
        assert output[1]["command"] == "status" and output[2]["closed"]
        assert "private-command" not in repr(output)
        assert runtime.status()["strategy_stopped"] and env.producer.prefetches == []
    with fixture() as env:
        runtime, output = O.OwnerRuntime(build(env)), []
        O.serve(runtime, stream=StringIO("x" * 5000 + "\nrun\n"), emit=output.append)
        assert output[0]["reasons"] == ["OWNER_COMMAND_TOO_LARGE"]
        assert runtime.status()["strategy_stopped"] and not runtime.status()["worker_running"]


def test_read_window_rejects_duplicate_keys_and_naive_times_without_echoes():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "window.json"
        path.write_text('{"deployment_id":"private","deployment_id":"second","start":"bad","end":"bad"}')
        refused(lambda: O.read_window(str(path)), "OWNER_JSON_DUPLICATE_KEY")
        path.write_text(json.dumps({"deployment_id": "private", "start": "2026-11-06T10:00:00",
                                   "end": "2026-11-06T10:10:00"}))
        refused(lambda: O.read_window(str(path)), "OWNER_TIME_REQUIRED")


def test_current_shipped_coordinator_still_refuses_controlled_without_coverage_proof():
    with fixture() as env:
        refused(lambda: build(env, mode="controlled"), "COORDINATOR_MODE_UNSUPPORTED")
        assert env.producer.prefetches == [] and env.adapter.requests == []


def test_failed_term_refresh_blocks_slots_but_keeps_account_monitoring_and_disarm():
    class FailedSource:
        def read(self):
            raise RuntimeError("private-current-terms-wire-error")
    with fixture() as env:
        env.profile = replace(env.profile, instrument_rules=replace(env.profile.instrument_rules,
                              asof=env.t0 - timedelta(minutes=5)))
        c = build(env, terms_source=FailedSource())
        report = O.OwnerRuntime(c).bootstrap()
        assert report["published_units"] == 1 and report["account_source"] == ""
        assert report["instrument_source"] == "COORDINATOR_TERMS_SOURCE_FAILED"
        assert report["new_entry_blocked"]
        c._slot(env.window.start)
        assert c.status().reasons == ("COORDINATOR_CURRENT_TERMS_REQUIRED",)
        assert env.books.reads == 0 and env.adapter.requests == []
        assert O.OwnerRuntime(c).disarm()["local_strategy_stopped"]
        assert "private-current-terms-wire-error" not in repr(report)


def test_issued_term_refresh_preserves_prepared_identity_and_updates_runtime_snapshots():
    from execution_accounts.instrument_terms import authority_digest
    from tests import launch_instrument_refresh as TF
    from tests.launch_runner import evidence_for
    with TF.registries(), fixture() as env:
        rules = env.profile.instrument_rules
        auth = TF.authority(account_scope=env.profile.account_scope, symbol=env.profile.symbol,
            lot_size=rules.lot_size, min_quantity=rules.min_quantity,
            valid_from=env.t0 - timedelta(days=1), valid_until=env.t0 + timedelta(days=1))
        env.profile = replace(env.profile, instrument_rules=replace(rules,
            source_digest=authority_digest(auth), asof=env.t0-timedelta(minutes=5)))
        env.evidence = evidence_for(env.profile, env.t0)
        chance, instruments = TF.bodies(auth)
        chance.update({key: str(rules.fee_fraction) for key in
                       ("bid_fee", "ask_fee", "maker_bid_fee", "maker_ask_fee")})
        chance["market"]["bid"]["min_total"] = str(rules.min_notional_krw)
        chance["market"]["ask"]["min_total"] = str(rules.min_notional_krw)
        instruments[0]["tick_size"] = str(rules.tick_size)

        class Source:
            def __init__(self): self.reads = 0
            def read(self):
                self.reads += 1
                return TF.observed(now=env.fake.now, auth=auth, chance=chance, instruments=instruments)
        source = Source()
        c = build(env, terms_source=source)
        c.bootstrap()
        assert source.reads == 1 and c.status().instrument_source == ""
        plan, inputs, seed = selected(env.fake.now)
        prepared = c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed)
        old = c._profile
        env.fake.now += seconds(1)
        c.refresh_instrument_rules()
        assert source.reads == 2 and c._profile.instrument_rules.asof > old.instrument_rules.asof
        assert c._runner.profile is c._profile and c._launch is c._runner.launch_session
        assert c._session_for(prepared.session_id) is prepared
        assert c._launch.prepared.expires_at == prepared.expires_at
        assert env.adapter.requests == []
        c.stop()
        env.fake.now += seconds(1)
        c.refresh_instrument_rules()
        assert source.reads == 3 and c.status().strategy_stopped and c._runner.stopped
        # A real issued renewal may outlive a transient failure to acquire the runner lock.
        # Retry that same issuance rather than consuming a fresh receipt from the old profile.
        from execution_launch.runner import RunnerError
        old_profile = c._profile
        env.fake.now += seconds(1)
        with patch.object(c._runner, "refresh_instrument_rules",
                          side_effect=RunnerError("RUNNER_CONCURRENT_TICK_REFUSED")):
            refused(c.refresh_instrument_rules, "RUNNER_CONCURRENT_TICK_REFUSED")
        pending = c._pending_terms
        assert pending is not None and c._profile is old_profile and source.reads == 4
        c.refresh_instrument_rules()
        assert c._pending_terms is None and c._profile is pending.profile and source.reads == 4
        c.close()
        env.fake.now += seconds(1)
        c.refresh_instrument_rules()
        assert source.reads == 5 and c._closing.is_set() and c._stopping.is_set() and c._runner.stopped


def test_busy_unit_disarm_is_bounded_pending_and_console_reports_unfinished_close():
    with fixture() as env:
        env.signal[0] = HOLD
        c = build(env)
        c.bootstrap()
        plan, inputs, seed = selected(env.fake.now)
        prepared = c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed)
        entered, release = threading.Event(), threading.Event()
        env.producer.block = entered, release
        runtime = O.OwnerRuntime(c)
        runtime.start()
        try:
            assert entered.wait(5), "fake unit did not block"
            before = time.monotonic()
            result = runtime.disarm(timeout=0.02)
            assert time.monotonic() - before < 0.5
            assert result["pending"] and result["local_strategy_stopped"]
            assert not result["journal_kill_written"] and not result["owner_disarm_recorded"]
            output = []
            O.serve(runtime, stream=StringIO(""), emit=output.append)
            assert output[-1]["command"] == "console-exit" and not output[-1]["closed"]
            assert output[-1]["worker_running"] and env.adapter.requests == []
        finally:
            release.set()
            runtime._thread.join(5)
        assert not runtime._thread.is_alive()
        result = runtime.disarm(timeout=0.1)
        assert not result["pending"] and result["journal_kill_written"]
        with c._journal.transaction() as tx:
            kills = [row for row in tx.events if row["kind"] == "kill"]
        assert len(kills) == 1 and kills[0]["data"]["session_id"] == prepared.session_id
        assert c._session_for(prepared.session_id) is prepared


def test_uppercase_provider_exception_text_is_not_an_authorized_diagnostic():
    def private_failure():
        raise ValueError("PRIVATE_ACCOUNT_ABC")
    with fixture() as env:
        runtime = O.OwnerRuntime(build(env), preparation_provider=private_failure)
        output = []
        O.serve(runtime, stream=StringIO("prepare\nclose\n"), emit=output.append)
        assert output[0]["reasons"] == ["OWNER_OPERATION_REFUSED"]
        assert "PRIVATE_ACCOUNT_ABC" not in repr(output)


def test_prepare_compares_both_account_and_input_age_to_actual_clock_before_simulation():
    from execution_control import session as S
    with fixture() as env:
        c = build(env)
        c.bootstrap()
        plan, inputs, seed = selected(env.fake.now)
        env.fake.now += timedelta(seconds=31)
        with patch.object(S.simulate, 'simulate', side_effect=AssertionError('stale account reached simulation')):
            refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed),
                    'COORDINATOR_PREPARATION_ACCOUNT_NOT_CURRENT')
        assert c._launch is None and not env.adapter.requests


def test_prepare_rechecks_current_implementation_review_and_stop_after_simulation():
    from execution_control import session as S
    for failure in ('review_expired', 'stop'):
        with fixture() as env:
            original = env.review
            if failure == 'review_expired':
                def review(binding, driver):
                    return replace(original(binding, driver), expires_at=env.t0+timedelta(seconds=1))
                env.review = review
            c = build(env)
            c.bootstrap()
            plan, inputs, seed = selected(env.fake.now)
            real, before = S.simulate.simulate, dict(S._PREPARED)
            def simulate(*a, **kw):
                report = real(*a, **kw)
                env.fake.now += timedelta(seconds=2)
                if failure == 'stop': c.stop()
                return report
            code = ('RUNNER_IMPLEMENTATION_REVIEW_UNVERIFIED' if failure == 'review_expired'
                    else 'SESSION_PREPARATION_CLOCK_REFUSED')
            with patch.object(S.simulate, 'simulate', side_effect=simulate):
                refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed), code)
            assert c._launch is None and S._PREPARED == before and not env.adapter.requests
            with c._journal.transaction() as tx:
                assert not any(row['kind'] == 'session_prepared' for row in tx.events)


def test_prepare_carries_verified_review_expiries_through_callbacks_and_final_owner_load():
    from core.compliance import owner
    from execution_control import session as S
    for review_kind in ('source', 'implementation'):
        for delayed in ('callback', 'final_owner'):
            with fixture() as env:
                counts = []
                deadline = env.fake.now+timedelta(seconds=5)
                original = env.evidence.review_verifier if review_kind == 'source' else env.review
                def review(*args):
                    receipt = replace(original(*args), expires_at=deadline)
                    counts.append(True)
                    if delayed == 'callback' and len(counts) == 2:
                        env.fake.now += timedelta(seconds=6)
                    return receipt
                if review_kind == 'source': env.evidence = replace(env.evidence, review_verifier=review)
                else: env.review = review
                c = build(env)
                c.bootstrap()
                plan, inputs, seed = selected(env.fake.now)
                real_context, loads, before = owner.load_context, [], dict(S._PREPARED)
                def context(*args, **kwargs):
                    result = real_context(*args, **kwargs)
                    loads.append(True)
                    if delayed == 'final_owner' and len(loads) == 2:
                        env.fake.now += timedelta(seconds=6)
                    return result
                with patch.object(owner, 'load_context', side_effect=context):
                    refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed),
                            'SESSION_PREPARATION_REVIEW_EXPIRED')
                assert len(counts) == 2 and c._launch is None and S._PREPARED == before
                with c._journal.transaction() as tx:
                    assert not any(row['kind'] == 'session_prepared' for row in tx.events)
                assert not env.adapter.requests


def test_prepare_never_issues_after_append_or_transaction_exit_expires_account_or_review():
    from contextlib import contextmanager
    from datetime import datetime
    from execution_control import session as S
    from execution_control.store import Transaction
    for deadline_kind in ('account', 'review'):
        for delayed_phase in ('append', 'exit'):
            with fixture() as env:
                if deadline_kind == 'review':
                    original = env.review
                    expires = env.fake.now+timedelta(seconds=5)
                    env.review = lambda *args: replace(original(*args), expires_at=expires)
                c = build(env)
                c.bootstrap()
                plan, inputs, seed = selected(env.fake.now)
                before, real_append, real_transaction = dict(S._PREPARED), Transaction.append, c._journal.transaction
                delay = timedelta(seconds=31 if deadline_kind == 'account' else 6)
                def append(tx, kind, data, *, now):
                    row = real_append(tx, kind, data, now=now)
                    if kind == 'session_prepared': env.fake.now += delay
                    return row
                @contextmanager
                def transaction():
                    with real_transaction() as tx:
                        yield tx
                    env.fake.now += delay
                seam = (patch.object(Transaction, 'append', append) if delayed_phase == 'append'
                        else patch.object(c._journal, 'transaction', transaction))
                code = ('SESSION_PREPARATION_INPUTS_STALE_OR_FUTURE' if deadline_kind == 'account'
                        else 'SESSION_PREPARATION_REVIEW_EXPIRED')
                with seam:
                    refused(lambda: c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed), code)
                assert c._launch is None and S._PREPARED == before and not env.adapter.requests
                rows = c._journal.snapshot()
                saved = [row for row in rows if row['kind'] == 'session_prepared']
                assert len(saved) == 1  # the already persisted evidence is retained, never rolled back
                body = dict(saved[0]['data'])
                for name in ('prepared_at', 'expires_at'): body[name] = datetime.fromisoformat(body[name])
                reconstructed = S.PreparedSession(**body)
                refused(lambda: S.verify_session(reconstructed, session_id=reconstructed.session_id,
                    policy=env.policy, instrument_rules=env.rules, ctx=None, now=env.fake.now,
                    order=env.order, events=rows), 'session preparation not issued in this process')


def history_storage_fixture():
    """Synthetic explicit policy, never an operational storage default."""
    from execution_launch.evidence_objects import ObjectLimits
    from execution_launch.history_storage import HistoryStoragePolicy, policy_digest
    from tests.launch_universe_history import universe_env
    env = universe_env()
    policy = HistoryStoragePolicy(schema_version=1, history_version=3,
        object_limits=ObjectLimits(chunk_bytes=32768, max_payload_bytes=2097152,
                                   max_chunks=64, max_manifest_bytes=65536),
        max_window_bytes=134217728, max_window_objects=4096, max_journal_bytes=16777216)
    env.protocol = replace(env.protocol, history_storage_sha256=policy_digest(policy))
    return env, policy


def test_universe_history_setup_and_export_share_explicit_frozen_policy():
    from execution_launch import coordinator as C
    from execution_launch.history_storage import policy_bytes, policy_digest
    env, policy = history_storage_fixture()
    now = env.window.start - timedelta(minutes=1)
    with F.temp_home() as home, head_root() as hroot:
        assert O.setup_history(window=env.window, protocol=env.protocol, storage_policy=policy,
            state_directory=home, head_directory=hroot, now=now)["initialized"]
        files = {"profile.json": json.dumps(profile_body(env.profile)),
                 "program.json": program_json(env.program), "protocol.json": protocol_json(env.protocol),
                 "history-storage.json": policy_bytes(policy).decode("ascii")}
        with private_inputs(files) as paths:
            args = dict(profile_path=paths["profile.json"], program_path=paths["program.json"],
                protocol_path=paths["protocol.json"], history_storage_path=paths["history-storage.json"],
                window=env.window, clock=lambda: now, head_root=hroot)
            with patch.object(C, "read_file", wraps=C.read_file) as reads:
                exported = compose_driver(**args)
            assert sum(call.args[0] == paths["history-storage.json"] for call in reads.call_args_list) == 1
            raw = history_journal(home, env.window).read_bytes()
            row = json.loads(raw.splitlines()[0])
            assert row["data"]["history_version"] == 3
            assert row["data"]["history_storage"] == json.loads(policy_bytes(policy))
            assert exported.protocol.history_storage_sha256 == policy_digest(policy)
            again = compose_driver(**args)
            assert again.identity == exported.identity and history_journal(home, env.window).read_bytes() == raw
            refused(lambda: O.setup_history(window=env.window, protocol=env.protocol, storage_policy=policy,
                state_directory=home, head_directory=hroot, now=now), "OWNER_EXISTING_HEAD_REFUSED")


def test_history_setup_policy_pairs_and_digest_refuse_before_head_creation():
    env, policy = history_storage_fixture()
    with F.temp_home() as home, head_root() as hroot:
        kwargs = dict(window=env.window, state_directory=home, head_directory=hroot,
                      now=env.window.start - timedelta(minutes=1))
        refused(lambda: O.setup_history(**kwargs, protocol=env.protocol), "OWNER_HISTORY_POLICY_PROTOCOL_REQUIRED")
        refused(lambda: O.setup_history(**kwargs, storage_policy=policy), "OWNER_HISTORY_POLICY_PROTOCOL_REQUIRED")
        refused(lambda: O.setup_history(**kwargs, protocol=env.protocol,
            storage_policy=replace(policy, max_window_bytes=policy.max_window_bytes + 1)),
            "OWNER_HISTORY_STORAGE_MISMATCH")
        refused(lambda: O.setup_history(**kwargs, protocol=LD.fixture().protocol, storage_policy=policy),
            "OWNER_HISTORY_STORAGE_MISMATCH")
        assert list(home.iterdir()) == [] and list(hroot.iterdir()) == []


def test_history_cli_requires_paired_protocol_policy_and_has_no_implicit_defaults():
    base = ["setup-history", "--window", "window.json", "--state-root", "/private-state", "--head-root", "/private-head"]
    assert O._arguments(base)[1].keys() == {"window", "state-root", "head-root"}
    for extra in (["--protocol", "protocol.json"], ["--history-storage", "storage.json"]):
        refused(lambda: O._arguments(base + extra), "OWNER_HISTORY_POLICY_PROTOCOL_REQUIRED")
    command, values = O._arguments(base + ["--protocol", "protocol.json", "--history-storage", "storage.json"])
    assert command == "setup-history" and values["protocol"] == "protocol.json"
    assert values["history-storage"] == "storage.json"
    duplicate = base + ["--protocol", "protocol.json", "--history-storage", "a.json", "--history-storage", "b.json"]
    refused(lambda: O._arguments(duplicate), "OWNER_ARGUMENTS_INVALID")
