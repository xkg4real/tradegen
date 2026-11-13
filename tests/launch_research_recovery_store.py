"""Actual recovery-attempt journal/head/version-copy tests in disposable explicit roots.

Routes and outcomes below are invented model data, not source verification
or current approval. No research source, credentials, network, notification send
or real home is opened. Native Windows behavior is not claimed by these tests.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch

from execution_launch import research_recovery_attempts as F
from tests.launch_research_incident_store import registration
from execution_launch import research_recovery_store as S
from execution_launch.baseline_head import BaselineHead
from tests import compliance_fixtures as CF

NOW = datetime(2026, 11, 13, 10, tzinfo=timezone.utc)


INCIDENT = "9" * 64


def checkpoint(at=NOW):
    return F.OwnerCheckpoint(key_fingerprint="SHA256:" + "a" * 64,
        code_hash="b" * 64, owner_head=(1, "c" * 64), observed_at=at)


def route():
    return F.RecoveryRoute(incident_namespace_sha256="1" * 64,
        attempt_namespace_sha256="2" * 64, incident_head=(2, "3" * 64),
        registration=registration(), source_configuration_sha256="4" * 64,
        source_root_ids=((1, 10), (1, 11)), destination_configuration_sha256="5" * 64,
        destination_root_ids=((1, 20), (1, 21)), destination_context_sha256="6" * 64,
        storage_policy_sha256="7" * 64, object_policy_sha256="8" * 64,
        attestation_sha256="9" * 64, request_sha256="a" * 64,
        file_set_sha256="b" * 64, revocation_target_sha256="c" * 64,
        issued_at=NOW - timedelta(seconds=10), expires_at=NOW + timedelta(hours=1),
        checkpoint=checkpoint())


def register_event(value=None):
    return F.make_event("ROUTE_REGISTERED", F.route_document(value or route()), observed_at=NOW)


def failure_event(*, observed_at=NOW + timedelta(seconds=1), reason="RECOVERY_SOURCE_UNAVAILABLE"):
    unknown = observed_at is None
    return F.make_event("PREFLIGHT_REFUSED", dict(route_id=route().route_id,
        incident_id=INCIDENT, execution_number=1, incident_head=[2, "3" * 64],
        status="AUTHORITY_REFUSED" if unknown else "READ_UNAVAILABLE", reason_code=reason,
        checkpoint=None if unknown else F.checkpoint_document(checkpoint(observed_at)),
        revocation_status="UNOBSERVED" if unknown else "NOT_REVOKED_AT_HEAD"),
        observed_at=observed_at)


def started_event():
    at = NOW + timedelta(seconds=1)
    return F.make_event("ATTEMPT_STARTED", dict(route_id=route().route_id,
        incident_id=INCIDENT, incident_head=[2, "3" * 64],
        checkpoint=F.checkpoint_document(checkpoint(at))), observed_at=at)


def outcome_event():
    at = NOW + timedelta(seconds=2)
    return F.make_event("ATTEMPT_OBSERVED", dict(attempt_id=F.attempt_id(route(), INCIDENT),
        execution_number=1, status="EXACT_ARCHIVE_RESTORED", reason_code="RECOVERY_EXACT_RESTORED",
        checkpoint=F.checkpoint_document(checkpoint(at)), revocation_status="NOT_REVOKED_AT_HEAD",
        verified_at=F.checkpoint_document(checkpoint(at))["observed_at"],
        recovery_artifact_digest="d" * 64, destination_head=[3, "e" * 64]), observed_at=at)


def limits(**changes):
    return S.RecoveryStoreLimits(format_limits=F.DEFAULT_LIMITS, **changes)


@contextmanager
def stack(*, provision=True, initialize=True, store_limits=None):
    with CF.temp_home(), tempfile.TemporaryDirectory(prefix="tradegen-recovery-store-") as temporary:
        base = Path(temporary)
        roots = tuple(base / name for name in ("primary", "backup", "heads"))
        for root in roots:
            root.mkdir()
        store = S.RecoveryAttemptStore(root=roots[0], backup_root=roots[1], head_root=roots[2],
            head_name="research-recovery", limits=store_limits or limits())
        if provision:
            store.provision_empty()
        if initialize:
            store.head.initialize_reviewed_head(store.genesis_digest)
        yield SimpleNamespace(store=store, base=base, roots=roots)


def files(s):
    return {str(path.relative_to(s.base)): path.read_bytes()
            for path in s.base.rglob("*") if path.is_file()}


def refused(call, code=None):
    try:
        call()
    except S.RecoveryStoreError as exc:
        assert str(exc).startswith("RECOVERY_STORE_"), str(exc)
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError("expected recovery store refusal")


def test_explicit_provision_does_not_seed_and_runtime_does_not_create_missing_state():
    with stack(provision=False, initialize=False) as s:
        assert files(s) == {}
        refused(s.store.inspect)
        refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
        assert files(s) == {}
        s.store.provision_empty()
        assert not s.store.head._dir.exists()
        before = files(s)
        refused(s.store.inspect)
        assert files(s) == before
        s.store.head.initialize_reviewed_head(s.store.genesis_digest)
        current = s.store.inspect()
        assert current.sequence == 0 and current.head == s.store.genesis_digest
        assert current.state.events == () and current.execution_ready is False
        refused(s.store.provision_empty)


def test_real_registration_failure_and_outbox_are_one_durable_transition():
    with stack() as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        second = s.store.commit(failure_event(), expected_head=first.head)
        assert first.sequence == 1 and second.sequence == 2
        assert len(second.state.attempts) == len(second.state.outbox) == 1
        assert second.state.outbox[0].attempt_id == second.state.attempts[0].attempt_id
        assert len(second.state.pending_notifications) == 1
        rows = (s.store.root / "journal.jsonl").read_bytes().splitlines()
        assert len(rows) == 2
        for raw in rows:
            row = json.loads(raw)
            assert (s.store.backup_root / "versions" / (row["row_sha256"] + ".json")).read_bytes() == raw
        assert s.store.head.read() == second.head
        restarted = S.RecoveryAttemptStore(root=s.roots[0], backup_root=s.roots[1], head_root=s.roots[2],
            head_name="research-recovery", limits=s.store.limits)
        assert restarted.inspect() == second


def test_start_then_outcome_publishes_one_result_intent_and_no_execution_authority():
    with stack() as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        second = s.store.commit(started_event(), expected_head=first.head)
        assert second.state.attempts[0].phase == "IN_PROGRESS" and second.state.outbox == ()
        third = s.store.commit(outcome_event(), expected_head=second.head)
        assert third.sequence == 3 and third.state.attempts[0].phase == "EXACT_ARCHIVE_RESTORED"
        assert third.state.attempts[0].terminal and len(third.state.outbox) == 1
        assert third.state.outbox[0].quarantine == "REMAINS"
        assert third.state.outbox[0].current_use == "NOT_GRANTED" and third.execution_ready is False
        before = files(s)
        assert s.store.commit(outcome_event(), expected_head=second.head) == third
        assert files(s) == before


def test_restart_preserves_same_attempt_resume_budget_and_due_time():
    with stack() as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        current = s.store.commit(started_event(), expected_head=first.head)
        def resume(number, second):
            at = NOW + timedelta(seconds=second)
            return F.make_event("RESUME_STARTED", dict(attempt_id=F.attempt_id(route(), INCIDENT),
                execution_number=number, incident_head=[2, "3" * 64],
                checkpoint=F.checkpoint_document(checkpoint(at))), observed_at=at)
        before = files(s)
        refused(lambda: s.store.commit(resume(2, 60), expected_head=current.head))
        assert files(s) == before
        current = s.store.commit(resume(2, 61), expected_head=current.head)
        restarted = S.RecoveryAttemptStore(root=s.roots[0], backup_root=s.roots[1], head_root=s.roots[2],
            head_name="research-recovery", limits=s.store.limits)
        assert restarted.inspect() == current
        current = restarted.commit(resume(3, 121), expected_head=current.head)
        assert len(current.state.attempts) == 1 and current.state.attempts[0].execution_count == 3
        before = files(s)
        # The finite codec refuses a fourth execution before store admission.
        try:
            resume(4, 181)
        except F.RecoveryAttemptError as exc:
            assert str(exc) == "RECOVERY_FORMAT_INVALID"
        else:
            raise AssertionError("fourth execution must fail in the codec")
        # A structurally valid repeated execution still reaches and fails the store.
        refused(lambda: restarted.commit(resume(3, 181), expected_head=current.head),
                "RECOVERY_STORE_TRANSITION_REFUSED")
        assert files(s) == before and restarted.inspect() == current


def test_actual_model_attempt_capacity_is_classified_before_any_write():
    capped = S.RecoveryStoreLimits(format_limits=replace(F.DEFAULT_LIMITS, max_attempts=1))
    with stack(store_limits=capped) as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        current = s.store.commit(failure_event(), expected_head=first.head)
        at = NOW + timedelta(seconds=2)
        extra = F.make_event("PREFLIGHT_REFUSED", dict(route_id=route().route_id,
            incident_id="8" * 64, execution_number=1, incident_head=[2, "3" * 64],
            status="READ_UNAVAILABLE", reason_code="RECOVERY_SOURCE_UNAVAILABLE",
            checkpoint=F.checkpoint_document(checkpoint(at)),
            revocation_status="NOT_REVOKED_AT_HEAD"), observed_at=at)
        before = files(s)
        refused(lambda: s.store.admit(extra, expected_head=current.head), "RECOVERY_STORE_LIMIT_EXCEEDED")
        refused(lambda: s.store.commit(extra, expected_head=current.head), "RECOVERY_STORE_LIMIT_EXCEEDED")
        assert files(s) == before and s.store.inspect() == current


def test_actual_model_execution_limit_is_a_transition_refusal_not_storage_capacity():
    capped = S.RecoveryStoreLimits(format_limits=replace(F.DEFAULT_LIMITS, max_resumes=0))
    with stack(store_limits=capped) as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        current = s.store.commit(started_event(), expected_head=first.head)
        at = NOW + timedelta(seconds=61)
        extra = F.make_event("RESUME_STARTED", dict(attempt_id=F.attempt_id(route(), INCIDENT),
            execution_number=2, incident_head=[2, "3" * 64],
            checkpoint=F.checkpoint_document(checkpoint(at))), observed_at=at)
        before = files(s)
        refused(lambda: s.store.admit(extra, expected_head=current.head), "RECOVERY_STORE_TRANSITION_REFUSED")
        refused(lambda: s.store.commit(extra, expected_head=current.head), "RECOVERY_STORE_TRANSITION_REFUSED")
        assert files(s) == before and s.store.inspect() == current


def test_actual_persisted_invalid_transition_has_replay_diagnostic_and_preserves_bytes():
    with stack() as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        current = s.store.commit(started_event(), expected_head=first.head)
        at = NOW + timedelta(seconds=121)
        # Canonical event and row bytes with exact backup, but no execution 2.
        # Keep the actual head at the last committed prefix: no synthetic CAS.
        invalid = F.make_event("RESUME_STARTED", dict(attempt_id=F.attempt_id(route(), INCIDENT),
            execution_number=3, incident_head=[2, "3" * 64],
            checkpoint=F.checkpoint_document(checkpoint(at))), observed_at=at)
        body = dict(schema=1, sequence=current.sequence + 1, previous_sha256=current.head,
            context_sha256=s.store.context_sha256, event=json.loads(F.event_bytes(invalid)))
        digest = S._digest("row", body)
        raw = S._canonical(body | {"row_sha256": digest})
        journal = s.store.root / "journal.jsonl"
        journal.write_bytes(journal.read_bytes() + raw + b"\n")
        (s.store.backup_root / "versions" / (digest + ".json")).write_bytes(raw)
        before = files(s)
        refused(s.store.inspect, "RECOVERY_STORE_REPLAY_REFUSED")
        assert files(s) == before and s.store.head.read() == current.head


def test_duplicate_and_response_loss_retry_do_not_append_or_duplicate_notifications():
    with stack() as s:
        event = register_event()
        first = s.store.commit(event, expected_head=s.store.genesis_digest)
        before = files(s)
        assert s.store.commit(event, expected_head=s.store.genesis_digest) == first
        assert files(s) == before
        incident = failure_event()
        second = s.store.commit(incident, expected_head=first.head)
        before = files(s)
        assert s.store.commit(incident, expected_head=first.head) == second
        assert s.store.commit(event, expected_head=second.head) == second
        assert files(s) == before and len(second.state.outbox) == 1


def test_changed_event_or_stale_unrelated_head_refuses_without_writes():
    with stack() as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        event = failure_event()
        try:
            replace(event, event_id="a" * 64)
        except F.RecoveryAttemptError as exc:
            assert str(exc) == "RECOVERY_EVENT_ID_MISMATCH"
        else:
            raise AssertionError("constructor accepted an invalid event identity")
        # Simulate corruption after construction to reach the actual store boundary.
        malformed = replace(event)
        object.__setattr__(malformed, "event_id", "a" * 64)
        before = files(s)
        refused(lambda: s.store.commit(malformed, expected_head=first.head), "RECOVERY_STORE_COMMIT_REFUSED")
        refused(lambda: s.store.commit(event, expected_head=s.store.genesis_digest), "RECOVERY_STORE_EXPECTED_HEAD_CHANGED")
        assert files(s) == before


def test_unknown_clock_failure_keeps_restriction_and_prior_trusted_time():
    with stack() as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        second = s.store.commit(failure_event(observed_at=None), expected_head=first.head)
        assert second.state.last_trusted_at == NOW and second.state.attempts[0].outcomes[0].observed_at is None
        assert second.state.attempts[0].terminal and second.state.attempts[0].phase == "AUTHORITY_REFUSED"
        assert len(second.state.outbox) == 1


def test_reported_delivery_preserves_incident_and_unknown_can_retry_after_restart():
    with stack() as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        second = s.store.commit(failure_event(), expected_head=first.head)
        message = second.state.outbox[0].message_id
        unknown = F.make_event("DELIVERY_REPORTED", dict(message_id=message, delivery_attempt_id="fixture_first", outcome="unknown"),
                               observed_at=NOW + timedelta(seconds=2))
        third = s.store.commit(unknown, expected_head=second.head)
        assert len(third.state.pending_notifications) == 1
        delivered = F.make_event("DELIVERY_REPORTED", dict(message_id=message, delivery_attempt_id="fixture_retry", outcome="delivered"),
                                 observed_at=NOW + timedelta(seconds=3))
        fourth = s.store.commit(delivered, expected_head=s.store.inspect().head)
        assert fourth.state.pending_notifications == ()
        assert len(fourth.state.attempts) == 1 and fourth.state.outbox[0].quarantine == "REMAINS"


def test_admission_is_read_only_and_returns_current_not_proposed_state():
    with stack() as s:
        before = files(s)
        with patch.object(BaselineHead, "compare_and_set", side_effect=AssertionError("unexpected CAS")), \
             patch.object(S.RecoveryAttemptStore, "_append", side_effect=AssertionError("unexpected append")), \
             patch.object(S.RecoveryAttemptStore, "_backup", side_effect=AssertionError("unexpected backup")):
            result = s.store.admit(register_event(), expected_head=s.store.genesis_digest)
        assert result.sequence == 0 and result.state.events == ()
        assert files(s) == before and result.head == s.store.genesis_digest


def test_pair_admission_checks_both_records_and_outbox_without_publishing_forecast():
    for maximum in (2, 3):
        with stack(store_limits=limits(max_records=maximum)) as s:
            current = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
            before = files(s)
            assert s.store.admit(started_event(), expected_head=current.head) == current
            with patch.object(BaselineHead, "compare_and_set", side_effect=AssertionError("unexpected CAS")), \
                 patch.object(S.RecoveryAttemptStore, "_append", side_effect=AssertionError("unexpected append")), \
                 patch.object(S.RecoveryAttemptStore, "_backup", side_effect=AssertionError("unexpected backup")):
                if maximum == 2:
                    refused(lambda: s.store.admit_pair(started_event(), outcome_event(), expected_head=current.head),
                            "RECOVERY_STORE_LIMIT_EXCEEDED")
                else:
                    assert s.store.admit_pair(started_event(), outcome_event(), expected_head=current.head) == current
            assert files(s) == before and s.store.inspect().state.attempts == ()
            if maximum == 3:
                started = s.store.commit(started_event(), expected_head=current.head)
                result = s.store.commit(outcome_event(), expected_head=started.head)
                assert result.sequence == 3 and len(result.state.outbox) == 1


def test_pair_admission_combined_journal_and_backup_byte_boundary_is_exact():
    with stack() as s:
        current = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        current = s.store.commit(started_event(), expected_head=current.head)
        s.store.commit(outcome_event(), expected_head=current.head)
        exact = (s.store.root / "journal.jsonl").stat().st_size
    for delta in (-1, 0, 1):
        with stack(store_limits=limits(max_journal_bytes=exact + delta)) as s:
            current = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
            before = files(s)
            if delta < 0:
                refused(lambda: s.store.admit_pair(started_event(), outcome_event(), expected_head=current.head),
                        "RECOVERY_STORE_LIMIT_EXCEEDED")
            else:
                assert s.store.admit_pair(started_event(), outcome_event(), expected_head=current.head) == current
            assert files(s) == before


def test_pair_admission_rejects_invalid_second_event_and_rereads_actual_storage():
    with stack() as s:
        current = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        corrupted = replace(outcome_event())
        object.__setattr__(corrupted, "event_id", "a" * 64)
        before = files(s)
        refused(lambda: s.store.admit_pair(started_event(), corrupted, expected_head=current.head))
        assert files(s) == before
        real = S.RecoveryAttemptStore._prepare
        count = []
        def damaged(store, *args):
            result = real(store, *args)
            count.append(1)
            if len(count) == 2:
                next((store.backup_root / "versions").iterdir()).write_bytes(b"changed evidence")
            return result
        with patch.object(S.RecoveryAttemptStore, "_prepare", damaged):
            refused(lambda: s.store.admit_pair(started_event(), outcome_event(), expected_head=current.head))
        assert len(count) == 2 and s.store.head.read() == current.head
        assert (s.store.root / "journal.jsonl").read_bytes() == before["primary/journal.jsonl"]


def test_exact_journal_capacity_and_record_count_are_admitted_before_any_write():
    with stack() as s:
        s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        exact = (s.store.root / "journal.jsonl").stat().st_size
    for delta in (-1, 0, 1):
        with stack(store_limits=limits(max_journal_bytes=exact + delta)) as s:
            before = files(s)
            if delta < 0:
                refused(lambda: s.store.admit(register_event(), expected_head=s.store.genesis_digest))
                refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
                assert files(s) == before
            else:
                assert s.store.commit(register_event(), expected_head=s.store.genesis_digest).sequence == 1
    with stack(store_limits=limits(max_records=1)) as s:
        first = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        before = files(s)
        refused(lambda: s.store.admit(failure_event(), expected_head=first.head))
        refused(lambda: s.store.commit(failure_event(), expected_head=first.head))
        assert files(s) == before


def test_crash_after_primary_append_preserves_partial_and_never_catches_up():
    with stack() as s:
        with patch.object(S.RecoveryAttemptStore, "_backup", side_effect=OSError("invented private failure")):
            refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
        retained = files(s)
        assert (s.store.root / "journal.jsonl").stat().st_size > 0
        assert s.store.head.read() == s.store.genesis_digest
        refused(s.store.inspect)
        refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
        assert files(s) == retained


def test_failed_head_cas_preserves_both_copies_but_does_not_publish_or_adopt():
    with stack() as s:
        with patch.object(BaselineHead, "compare_and_set", return_value=False):
            refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
        assert s.store.head.read() == s.store.genesis_digest
        retained = files(s)
        assert len(list((s.store.backup_root / "versions").iterdir())) == 1
        refused(s.store.inspect)
        refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
        assert files(s) == retained


def test_response_failure_after_actual_head_commit_can_retry_exact_last_event():
    with stack() as s:
        real = BaselineHead.compare_and_set
        def lost(head, old, new):
            assert real(head, old, new)
            raise OSError("invented response loss")
        with patch.object(BaselineHead, "compare_and_set", lost):
            refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
        actual = s.store.inspect()
        before = files(s)
        assert actual.sequence == 1
        assert s.store.commit(register_event(), expected_head=s.store.genesis_digest) == actual
        assert files(s) == before


def test_backup_corruption_before_cas_prevents_publication():
    with stack() as s:
        real = S.RecoveryAttemptStore._backup
        def corrupt(store, pins, name, raw):
            real(store, pins, name, raw)
            (store.backup_root / "versions" / name).write_bytes(b"broken")
        with patch.object(S.RecoveryAttemptStore, "_backup", corrupt):
            refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
        assert s.store.head.read() == s.store.genesis_digest
        refused(s.store.inspect)


def test_truncated_journal_or_backup_and_each_one_sided_rollback_refuse():
    for damage in ("torn", "journal-rollback", "head-rollback", "backup-corrupt", "backup-missing"):
        with stack() as s:
            old_head = (s.store.head._dir / "head.json").read_bytes()
            s.store.commit(register_event(), expected_head=s.store.genesis_digest)
            journal = s.store.root / "journal.jsonl"
            backup = next((s.store.backup_root / "versions").iterdir())
            if damage == "torn":
                journal.write_bytes(journal.read_bytes()[:-1])
            elif damage == "journal-rollback":
                journal.write_bytes(b"")
            elif damage == "head-rollback":
                (s.store.head._dir / "head.json").write_bytes(old_head)
            elif damage == "backup-corrupt":
                backup.write_bytes(b"changed")
            else:
                backup.unlink()
            retained = files(s)
            refused(s.store.inspect)
            assert files(s) == retained


def test_foreign_or_orphan_version_is_preserved_and_refused():
    with stack() as s:
        orphan = s.store.backup_root / "versions" / ("a" * 64 + ".json")
        orphan.write_bytes(b"orphan evidence")
        before = files(s)
        refused(s.store.inspect)
        refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
        assert files(s) == before


def test_replaced_root_or_runtime_head_configuration_cannot_continue_namespace():
    with stack() as s:
        original = s.store.root
        moved = original.with_name("retained-primary")
        original.rename(moved); original.mkdir()
        refused(s.store.inspect)
        assert (moved / "journal.jsonl").exists()
    with stack() as s:
        actual = s.store.head
        s.store.head = SimpleNamespace(read=lambda: s.store.genesis_digest)
        refused(s.store.inspect)
        s.store.head = actual
        assert s.store.inspect().sequence == 0


def test_linked_root_and_hardlinked_journal_are_refused():
    if os.name == "nt":
        return  # native Windows link privileges/semantics are NOT_RUN here
    with stack() as s:
        linked = s.base / "linked"
        linked.symlink_to(s.store.root, target_is_directory=True)
        refused(lambda: S.RecoveryAttemptStore(root=linked, backup_root=s.roots[1], head_root=s.roots[2],
                                       head_name="research-recovery", limits=limits()))
        os.link(s.store.root / "journal.jsonl", s.base / "second-name")
        refused(s.store.inspect)


def test_overlapping_roots_are_refused_without_creating_files():
    with stack(provision=False, initialize=False) as s:
        child = s.roots[0] / "nested"
        child.mkdir()
        refused(lambda: S.RecoveryAttemptStore(root=s.roots[0], backup_root=child, head_root=s.roots[2],
                                       head_name="research-recovery", limits=limits()))
        assert not any(p.is_file() for p in s.base.rglob("*"))


def test_real_os_lock_contention_refuses_and_releases_after_inspection():
    if os.name == "nt":
        return  # actual Windows process/byte-lock behavior is not tested on POSIX
    import fcntl
    with stack() as s:
        with (s.store.root / "session.lock").open("r+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                refused(s.store.inspect, "RECOVERY_STORE_LOCKED")
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        assert s.store.inspect().sequence == 0


def test_operation_does_not_provision_and_missing_operation_lock_is_not_recreated():
    def enter(store):
        with store.operation():
            raise AssertionError("unprovisioned operation must refuse")
    with stack(provision=False, initialize=False) as s:
        refused(lambda: enter(s.store))
        assert files(s) == {}
    with stack() as s:
        (s.store.root / "operation.lock").unlink()
        before = files(s)
        refused(lambda: enter(s.store))
        assert files(s) == before


def test_operation_allows_real_nested_store_calls_without_holding_session_or_head_lock():
    with stack() as s:
        refused(s.store.check_operation, "RECOVERY_STORE_OPERATION_REQUIRED")
        with s.store.operation() as actual:
            assert actual is s.store
            assert s.store.check_operation() is None
            assert s.store.head.read() == s.store.genesis_digest
            if os.name != "nt":
                import fcntl
                with (s.store.root / "session.lock").open("r+b") as unlocked:
                    fcntl.flock(unlocked.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(unlocked.fileno(), fcntl.LOCK_UN)
            before = s.store.inspect()
            assert s.store.admit(register_event(), expected_head=before.head) == before
            committed = s.store.commit(register_event(), expected_head=before.head)
            assert s.store.inspect() == committed
            def nested():
                with s.store.operation():
                    raise AssertionError("nested operation must refuse")
            refused(nested, "RECOVERY_STORE_OPERATION_LOCKED")
        refused(s.store.check_operation, "RECOVERY_STORE_OPERATION_REQUIRED")
        with s.store.operation():
            assert s.store.inspect() == committed


def test_operation_real_os_contention_is_independent_of_session_mutex():
    if os.name == "nt":
        return  # Actual native Windows byte-lock behavior is NOT_RUN on POSIX.
    import fcntl
    with stack() as s:
        def enter():
            with s.store.operation():
                raise AssertionError("OS-held operation must refuse")
        with (s.store.root / "operation.lock").open("r+b") as held:
            fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                assert s.store.inspect().sequence == 0
                refused(enter, "RECOVERY_STORE_OPERATION_LOCKED")
            finally:
                fcntl.flock(held.fileno(), fcntl.LOCK_UN)
        with s.store.operation():
            assert s.store.check_operation() is None


def test_operation_preserves_controller_body_errors_after_actual_cleanup():
    with stack() as s:
        for error in (ValueError("RECOVERY_RETRY_NOT_DUE"), RuntimeError("RECOVERY_ROUTE_CHANGED")):
            try:
                with s.store.operation():
                    raise error
            except type(error) as actual:
                assert actual is error
            else:
                raise AssertionError("body refusal swallowed")
            with s.store.operation():
                assert s.store.inspect().sequence == 0


def test_operation_lock_replacement_blocks_nested_commit_before_append_and_final_return():
    with stack() as s:
        journal = (s.store.root / "journal.jsonl").read_bytes()
        try:
            with s.store.operation():
                lock = s.store.root / "operation.lock"
                lock.rename(s.base / "retained-operation-lock")
                lock.write_bytes(b"0")
                refused(s.store.check_operation, "RECOVERY_STORE_STORAGE_CHANGED")
                refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest),
                        "RECOVERY_STORE_STORAGE_CHANGED")
                assert (s.store.root / "journal.jsonl").read_bytes() == journal
                raise ValueError("RECOVERY_BODY_REFUSAL")
        except S.RecoveryStoreError as exc:
            assert str(exc) == "RECOVERY_STORE_STORAGE_CHANGED"
        else:
            raise AssertionError("replacement must override body refusal")
        assert s.store._operation_state is None and not S._OPERATION_LOCK.locked()


def test_lock_replacement_during_commit_never_reports_success():
    with stack() as s:
        real = S.RecoveryAttemptStore._backup
        def changed(store, pins, name, raw):
            real(store, pins, name, raw)
            lock = store.root / "session.lock"
            lock.rename(s.base / "retained-lock")
            lock.write_bytes(b"0")
        with patch.object(S.RecoveryAttemptStore, "_backup", changed):
            refused(lambda: s.store.commit(register_event(), expected_head=s.store.genesis_digest))
        assert s.store.head.read() == s.store.genesis_digest


def test_non_lf_separators_do_not_expand_the_admitted_record_count():
    with stack(store_limits=limits(max_records=1)) as s:
        (s.store.root / "journal.jsonl").write_bytes(b"\r\v\f" * 10000 + b"\n")
        real = S._decode
        calls = []
        def tracked(raw, maximum):
            calls.append(len(raw))
            return real(raw, maximum)
        with patch.object(S, "_decode", tracked):
            refused(s.store.inspect)
        assert len(calls) <= 1


def test_limits_codec_rejects_extra_keys_noncanonical_and_boolean_counts():
    value = limits()
    raw = S.limits_bytes(value)
    assert S.parse_limits(raw) == value
    body = json.loads(raw)
    for changed in (body | {"extra": 1}, body | {"max_records": True}, body | {"max_records": 16385}):
        refused(lambda changed=changed: S.parse_limits(S._canonical(changed)))
    refused(lambda: S.parse_limits(raw + b"\n"))


def test_full_int64_dependency_length_has_matching_admission_and_replay_codec():
    with stack() as s:
        dependency = replace(registration().objects[0], byte_count=2 ** 63 - 1)
        reg = replace(registration(), objects=(dependency,))
        event = register_event(replace(route(), registration=reg))
        assert s.store.admit(event, expected_head=s.store.genesis_digest).sequence == 0
        result = s.store.commit(event, expected_head=s.store.genesis_digest)
        assert s.store.inspect() == result
        assert result.state.routes[0].registration.objects[0].byte_count == 2 ** 63 - 1


def test_deep_store_json_is_refused_and_imported_diagnostics_are_normalized():
    with stack() as s:
        raw = b'{"event":' + b'[' * 18 + b'0' + b']' * 18 + b'}\n'
        (s.store.root / "journal.jsonl").write_bytes(raw)
        before = files(s)
        assert refused(s.store.inspect) == "RECOVERY_STORE_RECORD_LIMIT_EXCEEDED"
        assert files(s) == before


def test_root_disappearance_after_constructor_path_check_has_fixed_diagnostic():
    with stack(provision=False, initialize=False) as s:
        original = S.RecoveryAttemptStore._paths
        def vanished(store, **kwargs):
            original(store, **kwargs)
            store.root.rename(s.base / "retained-root")
        with patch.object(S.RecoveryAttemptStore, "_paths", vanished):
            refused(lambda: S.RecoveryAttemptStore(root=s.roots[0], backup_root=s.roots[1], head_root=s.roots[2],
                head_name="research-recovery", limits=limits()), "RECOVERY_STORE_CONSTRUCTION_REFUSED")


def test_larger_actual_journal_replays_each_transition_once_without_prefix_revalidation():
    with stack() as s:
        current = s.store.commit(register_event(), expected_head=s.store.genesis_digest)
        current = s.store.commit(failure_event(), expected_head=current.head)
        message = current.state.outbox[0].message_id
        for index in range(62):
            event = F.make_event("DELIVERY_REPORTED", dict(message_id=message, delivery_attempt_id="bounded_" + str(index),
                outcome="unknown"), observed_at=NOW + timedelta(seconds=index + 2))
            current = s.store.commit(event, expected_head=current.head)
        assert current.sequence == 64 and len(current.state.events) == 64
        original = F._apply
        applied = []
        def counted(*args, **kwargs):
            applied.append(args[1].event_id)
            return original(*args, **kwargs)
        before = files(s)
        with patch.object(F, "_apply", counted), patch.object(F, "reduce", side_effect=AssertionError(
                "journal replay must not validate every prior state again")):
            replayed = s.store.inspect()
        assert replayed == current and len(applied) == len(set(applied)) == 64
        assert files(s) == before


def test_posix_pin_open_failure_closes_every_prior_directory_descriptor():
    if os.name == "nt":
        return
    with stack() as s:
        real_open = os.open
        opened = []
        def fail_later(*args, **kwargs):
            if len(opened) == 2:
                raise OSError("invented directory open failure")
            fd = real_open(*args, **kwargs)
            opened.append(fd)
            return fd
        with patch.object(S.os, "open", fail_later):
            try:
                with S._Pins(s.roots):
                    raise AssertionError("unexpected successful pin")
            except OSError:
                pass
        assert len(opened) == 2
        for fd in opened:
            try:
                os.fstat(fd)
            except OSError:
                continue
            raise AssertionError("directory descriptor leaked")


def test_windows_existing_pin_adapter_receives_strings_and_retains_all_three_roots():
    # Contract wiring only: no claim of native CreateFileW or power-loss testing.
    from execution_launch import bundle_review as B
    with stack() as s:
        events = []
        class Pin:
            def __init__(self, path):
                self.path = path
            def __enter__(self):
                events.append(("enter", self.path)); return self
            def check(self):
                events.append(("check", self.path))
            def __exit__(self, *_):
                events.append(("exit", self.path))
        def supplied(path):
            assert type(path) is str
            return Pin(path)
        with patch.object(B, "pin_windows_directory", supplied), patch.object(S.os, "name", "nt"):
            with S._Pins(s.roots) as pins:
                pins.check()
                assert not any(kind == "exit" for kind, _ in events)
        assert [path for kind, path in events if kind == "enter"] == [str(p) for p in s.roots]
        assert [path for kind, path in events if kind == "exit"] == [str(p) for p in reversed(s.roots)]
