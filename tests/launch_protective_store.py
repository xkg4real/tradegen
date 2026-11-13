"""Protective-state persistence over invented model facts and isolated files.

Explicit fixture head initialization is not owner approval. AuthorityFacts and
LedgerReferences are synthetic test inputs, never authenticated live evidence or
order authority. No account, key, notification or exchange transport is used.
"""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import timedelta
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import evidence_objects as E
from execution_launch import protective_state as P
from execution_launch import protective_store as S
from execution_launch.baseline_head import BaselineHeadError
from tests import compliance_fixtures as CF
from tests import launch_protective_state as F


def limits(**changes):
    return S.StoreLimits(**(dict(
        object_limits=E.ObjectLimits(chunk_bytes=4096, max_payload_bytes=65536,
                                     max_chunks=16, max_manifest_bytes=4096),
        object_budget=E.StoreBudget(max_bytes=4 * 1024 * 1024, max_objects=512),
        max_journal_bytes=1024 * 1024, max_records=128) | changes))


def binding(**changes):
    return S.StoreBinding(**(dict(driver_identity_sha256="1" * 64,
                                 research_sha256="2" * 64, source_sha256="3" * 64) | changes))


def ledger(**changes):
    return S.LedgerReferences(**(dict(account_head_sha256="4" * 64, orders_head_sha256="5" * 64,
        risk_head_sha256="6" * 64, high_water_sha256="7" * 64, floor_sha256="8" * 64,
        halt_sha256=None, source_evidence_sha256="9" * 64) | changes))


@contextmanager
def fixture(*, provision=True, initialize=True, policy=None, storage_limits=None):
    with CF.temp_home() as home, tempfile.TemporaryDirectory(prefix="tradegen_protective_head_") as raw:
        args = dict(root=home / "protective", head_root=Path(raw), head_name="protective-head",
                    policy=F.policy() if policy is None else policy, binding=binding(),
                    limits=limits() if storage_limits is None else storage_limits)
        store = S.ProtectiveStore(**args)
        if provision:
            store.provision_empty()
        if initialize:
            store.head.initialize_reviewed_head(store.genesis_digest)
        yield SimpleNamespace(store=store, home=home, head_root=Path(raw), args=args,
                              root=args["root"], policy=args["policy"],
                              reopen=lambda **changes: S.ProtectiveStore(**(args | changes)))


def files(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def refused(call, *codes):
    try:
        call()
    except (S.ProtectiveStoreError, BaselineHeadError, E.EvidenceObjectError, P.ProtectiveStateError) as exc:
        assert re.fullmatch(r"[A-Z][A-Z0-9_]+", str(exc)), "diagnostic leaked non-code text"
        if codes:
            assert str(exc) in codes, (str(exc), codes)
        return str(exc)
    raise AssertionError("expected a protective store refusal")


def commit(writer, policy, *, kind="assessment", at=F.T, authority=None, observations=None,
           refs=None, **event_changes):
    """Ordinary fixture commits use invented facts; missing-fact tests call writer directly."""
    snapshot = writer.snapshot()
    return writer.commit(F.event(snapshot.state, kind, at, **event_changes),
        authority=F.authority(policy, at) if authority is None else authority,
        observations=F.facts(policy, at) if observations is None else observations,
        ledger_refs=ledger() if refs is None else refs)


def test_construction_and_storage_provisioning_never_seed_the_independent_head():
    with fixture(provision=False, initialize=False) as env:
        assert not env.root.exists() and files(env.head_root) == {}
        refused(env.store.inspect)
        assert not env.root.exists() and files(env.head_root) == {}
        env.store.provision_empty()
        before = files(env.root), files(env.head_root)
        assert files(env.head_root) == {}
        refused(env.store.inspect)
        assert (files(env.root), files(env.head_root)) == before
        env.store.head.initialize_reviewed_head(env.store.genesis_digest)
        empty = env.store.inspect()
        assert empty.state == P.initial_state(env.policy) and empty.outbox == ()
        assert not empty.state.can_enter


def test_committed_state_and_full_ledger_references_round_trip_without_mutability():
    with fixture() as env:
        with env.store.session() as writer:
            result = commit(writer, env.policy)
            assert result.state.can_enter
            assert result.ledger_refs == ledger()
        restored = env.reopen().inspect()
        assert restored.state == result.state and restored.head == result.head
        assert restored.ledger_refs == result.ledger_refs and restored.outbox == result.outbox
        assert restored.restart_required
        try:
            restored.state.can_enter = False
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError("restored state is mutable")


def test_nonempty_reopen_requires_a_restart_transition_before_any_new_assessment():
    with fixture() as env:
        with env.store.session() as writer:
            commit(writer, env.policy)
        with env.reopen().session() as writer:
            before = files(env.root), files(env.head_root)
            refused(lambda: commit(writer, env.policy, at=F.T + timedelta(seconds=1)))
            assert (files(env.root), files(env.head_root)) == before
            restart = commit(writer, env.policy, kind="restart", at=F.T + timedelta(seconds=1))
            assert restart.state.recovering and restart.state.entry_blocked and not restart.state.can_enter
            assert not any(item.kind == "consider_reduce" for item in restart.outbox)
            recovered = commit(writer, env.policy, kind="recovery_complete", at=F.T + timedelta(seconds=2),
                observations=F.facts(env.policy, F.T + timedelta(seconds=2), recovery_complete=True))
            assert not recovered.state.recovering and not recovered.state.can_enter


def test_deadline_request_and_delivery_receipt_never_grant_management_or_entry_authority():
    with fixture() as env:
        at = env.policy.holding_deadline
        with env.store.session() as writer:
            result = commit(writer, env.policy, kind="deadline", at=at)
            requests = [effect for effect in result.outbox if effect.kind == "request_management_approval"]
            assert len(requests) == 1 and not result.state.can_enter
            assert not any(effect.kind == "consider_reduce" for effect in result.outbox)
            receipt = S.NotificationReceipt(effect_id=requests[0].intent_id, attempt_id="a" * 64,
                                            outcome="delivered", at=at)
            delivered = writer.record_notification(receipt)
            assert delivered.state == result.state and delivered.ledger_refs == result.ledger_refs
            assert delivered.outbox == result.outbox and delivered.receipts == (receipt,)
            assert not delivered.state.can_enter and delivered.state.deadline_seen
        restored = env.reopen().inspect()
        assert restored.state == result.state and restored.receipts == (receipt,)


def test_notification_replay_is_idempotent_and_changed_same_attempt_is_refused():
    with fixture() as env:
        at = env.policy.holding_deadline
        with env.store.session() as writer:
            snapshot = commit(writer, env.policy, kind="deadline", at=at)
            request = next(item for item in snapshot.outbox if item.kind == "request_management_approval")
            failed = S.NotificationReceipt(effect_id=request.intent_id, attempt_id="a" * 64,
                                           outcome="failed", at=at)
            first = writer.record_notification(failed)
            before = files(env.root), files(env.head_root)
            replayed = writer.record_notification(failed)
            assert replayed == first and (files(env.root), files(env.head_root)) == before
            refused(lambda: writer.record_notification(replace(failed, outcome="delivered")))
            assert (files(env.root), files(env.head_root)) == before
            delivered = writer.record_notification(replace(failed, attempt_id="b" * 64, outcome="delivered"))
            assert delivered.state == snapshot.state and len(delivered.receipts) == 2
            assert not delivered.state.can_enter


def test_notification_receipt_cannot_acknowledge_a_reduce_intent_or_an_unknown_effect():
    with fixture() as env:
        with env.store.session() as writer:
            result = commit(writer, env.policy, observations=F.facts(env.policy, strategy_verdict="sell"))
            reduction = next(effect for effect in result.outbox if effect.kind == "consider_reduce")
            before = files(env.root), files(env.head_root)
            for effect_id in (reduction.intent_id, "f" * 64):
                receipt = S.NotificationReceipt(effect_id=effect_id, attempt_id="a" * 64,
                                                outcome="delivered", at=F.T)
                refused(lambda: writer.record_notification(receipt))
                assert (files(env.root), files(env.head_root)) == before


def test_global_effect_projection_deduplicates_a_b_a_without_claiming_order_settlement():
    """Projection-level boundary only: P2 cannot settle a pending reduction to accept A/B/A as live history."""
    policy, state, outbox = F.policy(), P.initial_state(F.policy()), ()
    for i, digest in enumerate(("a" * 64, "b" * 64, "a" * 64)):
        at = F.T + timedelta(seconds=i)
        state, effects = P.reduce_management(policy, state, F.event(state, at=at),
            authority=F.authority(policy, at),
            observations=F.facts(policy, at, evidence_sha256=digest, strategy_verdict="sell"))
        outbox = S._merge_effects(outbox, effects)
    assert len(outbox) == 2 and len({item.intent_id for item in outbox}) == 2
    assert [item.evidence_sha256 for item in outbox] == ["a" * 64, "b" * 64]
    refused(lambda: S._merge_effects(outbox, (replace(outbox[0], reason="different-reason"),)),
            "PROTECTIVE_STORE_EFFECT_ID_COLLISION")


def test_closed_session_writer_cannot_commit_or_record_notification():
    with fixture() as env:
        with env.store.session() as writer:
            commit(writer, env.policy, kind="deadline", at=env.policy.holding_deadline)
        before = files(env.root), files(env.head_root)
        refused(writer.snapshot)
        refused(lambda: writer.commit(F.event(env.store.inspect().state, "restart", env.policy.holding_deadline),
            authority=None, observations=None, ledger_refs=ledger()))
        refused(lambda: writer.record_notification(S.NotificationReceipt(effect_id="a" * 64,
            attempt_id="b" * 64, outcome="delivered", at=env.policy.holding_deadline)))
        assert (files(env.root), files(env.head_root)) == before


def test_bound_policy_code_research_and_source_cannot_be_swapped_on_reopen():
    with fixture() as env:
        with env.store.session() as writer:
            commit(writer, env.policy)
        before = files(env.root), files(env.head_root)
        for changes in (dict(policy=replace(env.policy, account_scope="other-synthetic-account")),
                        dict(policy=replace(env.policy, code_sha256="a" * 64)),
                        dict(binding=binding(research_sha256="b" * 64)),
                        dict(binding=binding(source_sha256="c" * 64)),
                        dict(binding=binding(driver_identity_sha256="d" * 64))):
            refused(lambda: env.reopen(**changes).inspect())
            assert (files(env.root), files(env.head_root)) == before


def test_failed_independent_head_compare_and_set_preserves_unconfirmed_evidence_without_adoption():
    with fixture() as env:
        head_before = env.store.head.read()
        with env.store.session() as writer:
            before = files(env.root), files(env.head_root)
            with patch.object(env.store.head, "compare_and_set", return_value=False):
                refused(lambda: commit(writer, env.policy, kind="deadline", at=env.policy.holding_deadline))
            assert env.store.head.read() == head_before
            assert files(env.root) != before[0], "unconfirmed durable evidence was silently discarded"
            assert files(env.head_root) == before[1]
            refused(writer.snapshot)
        retained = files(env.root), files(env.head_root)
        reopened = env.reopen()
        refused(reopened.inspect)
        refused(lambda: reopened.head.initialize_reviewed_head(reopened.genesis_digest))
        assert (files(env.root), files(env.head_root)) == retained


def test_interrupted_independent_head_replace_retains_temporary_evidence_and_refuses_restart():
    with fixture() as env:
        original_replace = os.replace

        def fail_head_replace(source, target, *args, **kwargs):
            if Path(target).name == "head.json":
                raise OSError("private OS detail must not escape")
            return original_replace(source, target, *args, **kwargs)

        with env.store.session() as writer:
            with patch("execution_launch.baseline_head.os.replace", fail_head_replace):
                refused(lambda: commit(writer, env.policy, kind="deadline", at=env.policy.holding_deadline))
        assert (env.head_root / "protective-head" / "head.tmp").is_file()
        retained = files(env.root), files(env.head_root)
        refused(env.reopen().inspect)
        assert (files(env.root), files(env.head_root)) == retained


def test_invalid_explicit_models_are_rejected_without_operational_defaults():
    for kwargs in (dict(max_records=0), dict(max_records=True), dict(max_journal_bytes=0),
                   dict(max_journal_bytes=True)):
        refused(lambda: limits(**kwargs))
    for name in ("driver_identity_sha256", "research_sha256", "source_sha256"):
        for value in (None, "", "X" * 64, 123):
            refused(lambda: binding(**{name: value}))
    for name in ("account_head_sha256", "orders_head_sha256", "risk_head_sha256", "high_water_sha256",
                 "floor_sha256", "halt_sha256", "source_evidence_sha256"):
        assert getattr(ledger(**{name: None}), name) is None
        refused(lambda: ledger(**{name: "not-a-hash"}))
    for changes in (dict(effect_id="x"), dict(attempt_id=""), dict(outcome="approved"),
                    dict(at=F.T.replace(tzinfo=None))):
        values = dict(effect_id="a" * 64, attempt_id="b" * 64, outcome="delivered", at=F.T) | changes
        refused(lambda: S.NotificationReceipt(**values))


def test_a_second_writer_and_inspector_cannot_enter_an_owned_session():
    with fixture() as env:
        with env.store.session() as writer:
            before = files(env.root), files(env.head_root)
            refused(env.reopen().inspect, "PROTECTIVE_STORE_LOCKED")

            def second_writer():
                with env.reopen().session():
                    raise AssertionError("a second writer acquired the session")

            refused(second_writer, "PROTECTIVE_STORE_LOCKED")
            outcomes = []

            def foreign_thread():
                outcomes.append(refused(writer.snapshot, "PROTECTIVE_STORE_SESSION_REQUIRED"))

            thread = threading.Thread(target=foreign_thread)
            thread.start()
            thread.join(5)
            assert not thread.is_alive() and outcomes == ["PROTECTIVE_STORE_SESSION_REQUIRED"]
            assert (files(env.root), files(env.head_root)) == before


def test_advanced_history_cannot_seed_a_new_independent_head_or_reprovision_storage():
    with fixture() as env:
        with env.store.session() as writer:
            commit(writer, env.policy)
        before = files(env.root), files(env.head_root)
        replacement = env.reopen(head_name="new-protective-head")
        refused(lambda: replacement.head.initialize_reviewed_head(replacement.genesis_digest), "HEAD_SEED_REQUIRED")
        refused(replacement.inspect, "PROTECTIVE_STORE_HEAD_REFUSED")
        refused(env.store.provision_empty, "PROTECTIVE_STORE_ALREADY_PROVISIONED")
        assert (files(env.root), files(env.head_root)) == before


def test_rollback_of_only_the_journal_or_only_the_independent_head_is_refused():
    with fixture() as env:
        journal = env.root / "journal.jsonl"
        head = env.head_root / "protective-head" / "head.json"
        with env.store.session() as writer:
            commit(writer, env.policy)
            journal1, head1 = journal.read_bytes(), head.read_bytes()
            commit(writer, env.policy, at=F.T + timedelta(seconds=1))
        journal2, head2 = journal.read_bytes(), head.read_bytes()
        for rolled_journal, rolled_head in ((journal1, head2), (journal2, head1)):
            journal.write_bytes(rolled_journal)
            head.write_bytes(rolled_head)
            before = files(env.root), files(env.head_root)
            refused(env.reopen().inspect, "PROTECTIVE_STORE_HEAD_MISMATCH")
            assert (files(env.root), files(env.head_root)) == before
        # A coherent rollback of both roots is explicitly outside this store's proof.
        # Do not falsely claim that local hashes provide an external freshness authority.


def test_truncated_duplicate_and_noncanonical_journal_records_are_retained_and_refused():
    transforms = (lambda raw: raw[:-1], lambda raw: raw + raw,
                  lambda raw: b" " + raw, lambda raw: raw.replace(b'"schema":1', b'"schema":true', 1),
                  lambda raw: raw[:-2] + b',"schema":1}\n')
    for transform in transforms:
        with fixture() as env:
            with env.store.session() as writer:
                commit(writer, env.policy)
            journal = env.root / "journal.jsonl"
            journal.write_bytes(transform(journal.read_bytes()))
            before = files(env.root), files(env.head_root)
            refused(env.reopen().inspect)
            assert (files(env.root), files(env.head_root)) == before


def test_referenced_object_mutation_or_absence_never_yields_a_partial_healthy_snapshot():
    for mode in ("changed", "missing"):
        with fixture() as env:
            with env.store.session() as writer:
                commit(writer, env.policy, kind="deadline", at=env.policy.holding_deadline)
            row = json.loads((env.root / "journal.jsonl").read_bytes())
            path = env.root / "payload-objects" / "objects" / (row["payload_ref"]["manifest_sha256"] + ".blob")
            if mode == "changed":
                path.write_bytes(path.read_bytes() + b" ")
            else:
                path.unlink()
            before = files(env.root), files(env.head_root)
            refused(env.reopen().inspect, "PROTECTIVE_STORE_REPLAY_REFUSED")
            assert (files(env.root), files(env.head_root)) == before


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def test_head_verifier_recomputes_state_and_effects_even_when_all_outer_hashes_are_valid():
    def changed_state(body):
        body["state"]["can_enter"] = True

    def missing_effect(body):
        body["effects"] = []

    def wrong_context(body):
        body["context_sha256"] = "e" * 64

    def missing_reference(body):
        del body["ledger_refs"]["floor_sha256"]

    def changed_input(body):
        body["event"]["previous_state_sha256"] = "f" * 64

    def integer_instead_of_boolean(body):
        body["state"]["entry_blocked"] = 1

    def extra_effect_field(body):
        body["effects"][0]["approval"] = True

    def invalid_effect_time(body):
        body["effects"][0]["not_after"] = 0

    for corrupt in (changed_state, missing_effect, wrong_context, missing_reference, changed_input,
                    integer_instead_of_boolean, extra_effect_field, invalid_effect_time):
        with fixture() as env:
            original_head = env.store.head.read()
            with env.store.session() as writer:
                with patch.object(env.store.head, "compare_and_set", return_value=False):
                    refused(lambda: commit(writer, env.policy, kind="deadline", at=env.policy.holding_deadline))
            journal = env.root / "journal.jsonl"
            row = json.loads(journal.read_bytes())
            objects = E.EvidenceObjectStore(root=env.root / "payload-objects", limits=env.args["limits"].object_limits)
            body = json.loads(objects.read(E.PayloadReference(**row["payload_ref"])))
            corrupt(body)
            new_ref = objects.stage(_canonical(body), budget=env.args["limits"].object_budget)
            row["payload_ref"] = asdict(new_ref)
            unsigned = {key: value for key, value in row.items() if key != "row_sha256"}
            row["row_sha256"] = hashlib.sha256(b"TRADEGEN-PROTECTIVE-STORE-v1\x00row\x00" + _canonical(unsigned)).hexdigest()
            journal.write_bytes(_canonical(row) + b"\n")
            before = files(env.root), files(env.head_root)
            refused(lambda: env.store.head.compare_and_set(original_head, row["row_sha256"]),
                    "HEAD_TRANSITION_UNVERIFIED")
            assert env.store.head.read() == original_head
            assert (files(env.root), files(env.head_root)) == before


def test_record_and_journal_byte_limits_refuse_before_staging_new_objects():
    with fixture(storage_limits=limits(max_records=1)) as env:
        with env.store.session() as writer:
            result = commit(writer, env.policy)
            before = files(env.root), files(env.head_root)
            refused(lambda: commit(writer, env.policy, at=F.T + timedelta(seconds=1)),
                    "PROTECTIVE_STORE_LIMIT_EXCEEDED")
            assert writer.snapshot() == result and (files(env.root), files(env.head_root)) == before
            first_bytes = len((env.root / "journal.jsonl").read_bytes())
    for delta, accepted in ((-1, False), (0, True), (1, True)):
        with fixture(storage_limits=limits(max_journal_bytes=first_bytes + delta)) as env:
            with env.store.session() as writer:
                before = files(env.root), files(env.head_root)
                if accepted:
                    commit(writer, env.policy)
                    assert len((env.root / "journal.jsonl").read_bytes()) == first_bytes
                else:
                    refused(lambda: commit(writer, env.policy), "PROTECTIVE_STORE_LIMIT_EXCEEDED")
                    assert (files(env.root), files(env.head_root)) == before


def test_unknown_ledger_references_remain_unknown_and_missing_facts_do_not_restore_permission():
    with fixture() as env:
        refs = ledger(**{name: None for name in ledger().__dataclass_fields__})
        with env.store.session() as writer:
            initial = writer.snapshot()
            result = writer.commit(F.event(initial.state), authority=None, observations=None, ledger_refs=refs)
            assert result.ledger_refs == refs and not result.state.can_enter and not result.state.can_reduce
            assert result.state.strategy_verdict == "unavailable" and not result.unresolved_reductions
        restored = env.reopen().inspect()
        assert restored.ledger_refs == refs and restored.state == result.state


def test_partial_append_and_journal_sync_failure_never_publish_state_or_outbox():
    for failure in ("short_write", "sync"):
        with fixture() as env:
            journal = env.root / "journal.jsonl"
            head_before = env.store.head.read()
            real_fdopen, real_fsync = os.fdopen, os.fsync

            class ShortAppend:
                def __init__(self, handle):
                    self.handle = handle

                def __enter__(self):
                    self.handle.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.handle.__exit__(*args)

                def __getattr__(self, name):
                    return getattr(self.handle, name)

                def write(self, raw):
                    return self.handle.write(raw[:len(raw) // 2])

            def fdopen(descriptor, mode, *args, **kwargs):
                handle = real_fdopen(descriptor, mode, *args, **kwargs)
                return ShortAppend(handle) if failure == "short_write" and mode == "ab" else handle

            def fsync(descriptor):
                info, expected = os.fstat(descriptor), journal.stat()
                if failure == "sync" and (info.st_dev, info.st_ino) == (expected.st_dev, expected.st_ino):
                    raise OSError("fake interrupted journal sync")
                return real_fsync(descriptor)

            with env.store.session() as writer:
                with patch("execution_launch.protective_store.os.fdopen", fdopen), \
                        patch("execution_launch.protective_store.os.fsync", fsync):
                    refused(lambda: commit(writer, env.policy, kind="deadline", at=env.policy.holding_deadline))
                refused(writer.snapshot, "PROTECTIVE_STORE_SESSION_FAILED")
                assert env.store.head.read() == head_before and journal.read_bytes()
            retained = files(env.root), files(env.head_root)
            refused(env.reopen().inspect)
            assert (files(env.root), files(env.head_root)) == retained


def test_object_staging_failure_cannot_advance_journal_head_or_pending_notification():
    with fixture() as env:
        with env.store.session() as writer:
            before = files(env.root), files(env.head_root)
            initial = writer.snapshot()
            with patch.object(E.EvidenceObjectStore, "stage",
                              side_effect=E.EvidenceObjectError("EVIDENCE_OBJECT_IO_REFUSED")):
                refused(lambda: commit(writer, env.policy, kind="deadline", at=env.policy.holding_deadline),
                        "PROTECTIVE_STORE_OBJECT_REFUSED")
            assert writer.snapshot() == initial and not writer.snapshot().pending_notifications
            assert (files(env.root), files(env.head_root)) == before


def test_object_budget_refusal_preserves_existing_snapshot_and_all_existing_bytes():
    for budget in (E.StoreBudget(max_bytes=1, max_objects=512),
                   E.StoreBudget(max_bytes=4 * 1024 * 1024, max_objects=1)):
        with fixture(storage_limits=limits(object_budget=budget)) as env:
            with env.store.session() as writer:
                initial = writer.snapshot()
                before = files(env.root), files(env.head_root)
                refused(lambda: commit(writer, env.policy), "PROTECTIVE_STORE_LIMIT_EXCEEDED")
                assert writer.snapshot() == initial
                assert (files(env.root), files(env.head_root)) == before


def test_path_alias_and_same_root_head_are_refused_without_touching_other_directories():
    with fixture(provision=False, initialize=False) as env:
        before = files(env.home), files(env.head_root)
        refused(lambda: env.reopen(head_root=env.home), "HEAD_ROOT_NOT_SEPARATE")
        assert (files(env.home), files(env.head_root)) == before
        target = env.home / "unrelated"
        target.mkdir()
        CF.directory_link(env.root, target)
        before = files(target), files(env.head_root)
        refused(lambda: env.reopen().provision_empty())
        assert (files(target), files(env.head_root)) == before


def test_exact_event_replay_does_not_append_and_cannot_change_ledger_dependencies():
    with fixture() as env:
        with env.store.session() as writer:
            event = F.event(writer.snapshot().state)
            args = dict(authority=F.authority(env.policy), observations=F.facts(env.policy), ledger_refs=ledger())
            result = writer.commit(event, **args)
            before = files(env.root), files(env.head_root)
            assert writer.commit(event, **args) == result
            assert (files(env.root), files(env.head_root)) == before
            refused(lambda: writer.commit(event, **(args | {"ledger_refs": ledger(floor_sha256="a" * 64)})),
                    "PROTECTIVE_STORE_DUPLICATE_CONTEXT_CHANGED")
            assert (files(env.root), files(env.head_root)) == before


def test_persisted_reduction_cannot_be_cleared_by_claimed_facts_restart_rearm_or_notification():
    with fixture() as env:
        with env.store.session() as writer:
            event = F.event(writer.snapshot().state)
            args = dict(authority=F.authority(env.policy),
                        observations=F.facts(env.policy, strategy_verdict="sell"), ledger_refs=ledger())
            first = writer.commit(event, **args)
            reduction = first.unresolved_reductions[0]
            before = files(env.root), files(env.head_root)
            assert writer.commit(event, **args) == first
            refused(lambda: commit(writer, env.policy, at=F.T + timedelta(seconds=1)),
                    "PROTECTIVE_STORE_PENDING_REDUCTION_CONFLICT")
            assert (files(env.root), files(env.head_root)) == before
        with env.reopen().session() as writer:
            at = F.T + timedelta(seconds=2)
            restarted = writer.commit(F.event(writer.snapshot().state, "restart", at),
                                      authority=None, observations=None, ledger_refs=ledger())
            assert not restarted.state.can_enter and restarted.unresolved_reductions == (reduction,)
            at += timedelta(seconds=1)
            recovered = commit(writer, env.policy, kind="recovery_complete", at=at,
                observations=F.facts(env.policy, at, recovery_complete=True, no_pending_reduce=False))
            assert not recovered.state.can_enter and recovered.unresolved_reductions == (reduction,)
            before = files(env.root), files(env.head_root)
            refused(lambda: commit(writer, env.policy, kind="entry_reauthorized", at=at + timedelta(seconds=1)),
                    "PROTECTIVE_STORE_PENDING_REDUCTION_CONFLICT")
            refused(lambda: writer.record_notification(S.NotificationReceipt(effect_id=reduction.intent_id,
                attempt_id="a" * 64, outcome="delivered", at=at)), "PROTECTIVE_STORE_RECEIPT_TARGET_INVALID")
            assert writer.snapshot() == recovered and (files(env.root), files(env.head_root)) == before
        assert env.reopen().inspect().unresolved_reductions == (reduction,)


def test_first_reduction_cannot_preserve_entry_permission_in_the_same_committed_state():
    with fixture() as env:
        with env.store.session() as writer:
            before = files(env.root), files(env.head_root)
            bad = F.facts(env.policy, risk_causes=("trailing_condition",))
            refused(lambda: commit(writer, env.policy, observations=bad),
                    "PROTECTIVE_STORE_PENDING_ENTRY_CONFLICT")
            assert (files(env.root), files(env.head_root)) == before
            result = commit(writer, env.policy, observations=replace(bad, entry_eligible=False))
            assert not result.state.can_enter and len(result.unresolved_reductions) == 1


def test_delivery_attempt_ids_are_global_and_a_delivered_effect_cannot_be_sent_again():
    with fixture() as env:
        with env.store.session() as writer:
            first = commit(writer, env.policy, kind="fault", fault="inputs_missing")
            one = next(item for item in first.outbox if item.kind == "notify")
            receipt = S.NotificationReceipt(effect_id=one.intent_id, attempt_id="a" * 64,
                                            outcome="delivered", at=F.T)
            delivered = writer.record_notification(receipt)
            assert one not in delivered.pending_notifications
            second = commit(writer, env.policy, kind="fault", fault="account_unavailable",
                            at=F.T + timedelta(seconds=1))
            two = next(item for item in second.outbox if item.kind == "notify" and item != one)
            before = files(env.root), files(env.head_root)
            refused(lambda: writer.record_notification(replace(receipt, effect_id=two.intent_id)),
                    "PROTECTIVE_STORE_RECEIPT_REWRITTEN")
            refused(lambda: writer.record_notification(replace(receipt, attempt_id="b" * 64)),
                    "PROTECTIVE_STORE_ALREADY_DELIVERED")
            assert (files(env.root), files(env.head_root)) == before
            assert two in writer.snapshot().pending_notifications and one not in writer.snapshot().pending_notifications


def test_replay_after_monitor_expiry_preserves_deadline_request_and_never_extends_authority():
    with fixture() as env:
        with env.store.session() as writer:
            deadline = commit(writer, env.policy, kind="deadline", at=env.policy.holding_deadline)
        at = env.policy.monitor_until + timedelta(seconds=1)
        with env.reopen().session() as writer:
            restored = writer.snapshot()
            assert restored.state == deadline.state
            expired = writer.commit(F.event(restored.state, "restart", at), authority=None,
                                    observations=None, ledger_refs=ledger())
            assert expired.state.phase == "owner_action_required"
            assert not expired.state.can_enter and not expired.state.can_reduce and not expired.state.can_observe
            assert expired.state.renewal_request_id == deadline.state.renewal_request_id
            assert sum(item.kind == "request_management_approval" for item in expired.outbox) == 1
            assert not expired.unresolved_reductions


def test_persisted_clock_fault_keeps_the_last_trusted_time_for_a_corrected_restart():
    with fixture() as env:
        with env.store.session() as writer:
            commit(writer, env.policy)
            wrong = F.T + timedelta(days=365)
            fault = commit(writer, env.policy, kind="fault", fault="clock_unreliable", at=wrong)
            assert fault.state.last_event_at == F.T and not fault.state.deadline_seen
            assert fault.state.renewal_request_id is None and not fault.unresolved_reductions
        restored = env.reopen().inspect()
        assert restored.state == fault.state and restored.state.last_event_at == F.T
        with env.reopen().session() as writer:
            corrected = commit(writer, env.policy, kind="restart", at=F.T + timedelta(seconds=1))
            assert corrected.state.last_event_at == F.T + timedelta(seconds=1)
            assert corrected.state.recovering and not corrected.state.can_enter
            assert not corrected.state.deadline_seen and not corrected.unresolved_reductions


def test_empty_journal_with_orphan_payloads_cannot_be_adopted_as_a_fresh_genesis():
    with fixture(initialize=False) as env:
        objects = E.EvidenceObjectStore(root=env.root / "payload-objects", limits=env.args["limits"].object_limits)
        objects.stage(b"synthetic orphan payload", budget=env.args["limits"].object_budget)
        assert (env.root / "journal.jsonl").read_bytes() == b""
        before = files(env.root), files(env.head_root)
        refused(lambda: env.store.head.initialize_reviewed_head(env.store.genesis_digest), "HEAD_SEED_REQUIRED")
        refused(env.reopen().inspect, "PROTECTIVE_STORE_HEAD_REFUSED")
        assert (files(env.root), files(env.head_root)) == before


def test_dense_journal_is_refused_before_allocating_or_decoding_all_records():
    class NoSplitBytes(bytes):
        def split(self, *args, **kwargs):
            raise AssertionError("over-limit journal was split before its record-count check")

    with fixture(storage_limits=limits(max_records=2)) as env:
        dense = b"\n" * 4096
        (env.root / "journal.jsonl").write_bytes(dense)
        before = files(env.root), files(env.head_root)
        refused(env.store.inspect, "PROTECTIVE_STORE_LIMIT_EXCEEDED")
        with patch.object(env.store, "_read_journal", return_value=NoSplitBytes(dense)):
            refused(env.store._replay, "PROTECTIVE_STORE_LIMIT_EXCEEDED")
        assert (files(env.root), files(env.head_root)) == before


def test_unavailable_lock_or_journal_file_identity_refuses_paths_and_open_handles():
    class Unidentified:
        st_ino = 0

        def __init__(self, original):
            self.original = original

        def __getattr__(self, name):
            return getattr(self.original, name)

    with fixture() as env:
        before = files(env.root), files(env.head_root)
        real_lstat, real_fstat = os.lstat, os.fstat
        for name in ("session.lock", "journal.jsonl"):
            target = env.root / name
            inode = real_lstat(target).st_ino

            def missing_path(path, *args, **kwargs):
                info = real_lstat(path, *args, **kwargs)
                return Unidentified(info) if Path(path) == target else info

            def missing_handle(fd):
                info = real_fstat(fd)
                return Unidentified(info) if info.st_ino == inode else info

            with patch.object(S.os, "lstat", side_effect=missing_path):
                refused(env.store.inspect, "PROTECTIVE_STORE_IDENTITY_UNAVAILABLE")
            with patch.object(S.os, "fstat", side_effect=missing_handle):
                refused(env.store.inspect, "PROTECTIVE_STORE_IDENTITY_UNAVAILABLE")
            assert (files(env.root), files(env.head_root)) == before


def test_active_writer_refuses_root_or_lock_replacement_while_another_writer_holds_the_new_lock():
    for mode in ("root_field", "lock_file", "whole_directory"):
        with fixture() as env:
            original_root = env.root
            displaced = env.home / "displaced-evidence"
            replacement = env.home / "replacement-evidence"
            with env.store.session() as first:
                initial = first.snapshot()
                event = F.event(initial.state)
                if mode == "root_field":
                    shutil.copytree(original_root, replacement)
                    env.store.root = replacement
                    second_store = env.reopen(root=replacement)
                elif mode == "lock_file":
                    (original_root / "session.lock").rename(displaced)
                    (original_root / "session.lock").write_bytes(b"0")
                    second_store = env.reopen()
                else:
                    original_root.rename(displaced)
                    shutil.copytree(displaced, original_root)
                    second_store = env.reopen()
                expected = ("PROTECTIVE_STORE_CONTEXT_CHANGED" if mode == "root_field"
                            else "PROTECTIVE_STORE_LOCK_CHANGED")
                try:
                    with second_store.session() as second:
                        second_snapshot = second.snapshot()
                        before = files(env.home), files(env.head_root)
                        refused(first.snapshot, expected)
                        refused(lambda: first.commit(event, authority=F.authority(env.policy),
                            observations=F.facts(env.policy), ledger_refs=ledger()), expected)
                        refused(lambda: first.record_notification(S.NotificationReceipt(
                            effect_id="a" * 64, attempt_id="b" * 64, outcome="delivered", at=F.T)), expected)
                        assert second.snapshot() == second_snapshot
                        assert (files(env.home), files(env.head_root)) == before
                finally:
                    if mode == "root_field":
                        env.store.root = original_root
                    elif mode == "lock_file":
                        (original_root / "session.lock").rename(replacement)
                        displaced.rename(original_root / "session.lock")
                    else:
                        original_root.rename(replacement)
                        displaced.rename(original_root)
                assert first.snapshot() == initial


def test_active_writer_pins_the_head_object_chain_and_head_location():
    with fixture() as env:
        with env.store.session() as writer:
            initial = writer.snapshot()
            head = env.store.head
            mutations = ((env.store, "head", env.reopen().head),
                         (head, "_root", env.head_root / "other"),
                         (head, "_dir", env.head_root / "other"),
                         (head, "_chain", env.reopen().head._chain),
                         (head._chain, "store", env.reopen()))
            for obj, attribute, changed in mutations:
                original = getattr(obj, attribute)
                before = files(env.root), files(env.head_root)
                try:
                    setattr(obj, attribute, changed)
                    refused(writer.snapshot, "PROTECTIVE_STORE_CONTEXT_CHANGED")
                    refused(lambda: writer.commit(F.event(initial.state), authority=F.authority(env.policy),
                        observations=F.facts(env.policy), ledger_refs=ledger()), "PROTECTIVE_STORE_CONTEXT_CHANGED")
                    assert (files(env.root), files(env.head_root)) == before
                finally:
                    setattr(obj, attribute, original)
            assert writer.snapshot() == initial


def test_lock_replacement_after_object_staging_cannot_publish_a_transition_or_advance_the_head():
    with fixture() as env:
        real_stage = E.EvidenceObjectStore.stage
        old_lock, new_lock = env.home / "displaced-lock", env.home / "replacement-lock"
        target = env.root / "session.lock"

        def stage_then_replace(objects, raw, *, budget):
            reference = real_stage(objects, raw, budget=budget)
            target.rename(old_lock)
            target.write_bytes(b"0")
            return reference

        with env.store.session() as writer:
            head_before = env.store.head.read()
            try:
                with patch.object(E.EvidenceObjectStore, "stage", new=stage_then_replace):
                    refused(lambda: commit(writer, env.policy), "PROTECTIVE_STORE_LOCK_CHANGED")
                assert (env.root / "journal.jsonl").read_bytes() == b""
                assert env.store.head.read() == head_before
                assert list((env.root / "payload-objects" / "objects").glob("*.blob")), "staged evidence vanished"
            finally:
                target.rename(new_lock)
                old_lock.rename(target)
            refused(writer.snapshot, "PROTECTIVE_STORE_SESSION_FAILED")
