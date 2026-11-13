"""Current research selection for one exactly restored, still-held destination.

Actual destination evidence, current approvals and the complete family are
rechecked on every call. A release record is historical scoped evidence, never
an owner signature, global incident release, trading permission or storage lease.
The original source is not reopened. No recovery, provisioning or order occurs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_attestation as A, bundle_auth as U, bundle_recovery as B
from execution_launch import research_bundle_format as BF, research_bundle_store as BS
from execution_launch import research_incidents as I, research_incident_monitor as M
from execution_launch import research_incident_store as IS
from execution_launch import research_recovery as R, research_recovery_attempts as F
from execution_launch import sealed_study_review as S
from execution_launch import research_recovery_store as RS
from execution_launch.research_recovery_store import RecoveryAttemptStore
from execution_launch.recovery_artifact import build_recovery_artifact


class RecoveredSelectionError(ValueError):
    """Fixed diagnostics only; never supplied paths, keys or evidence contents."""


def _need(ok, code):
    if not ok:
        raise RecoveredSelectionError('RECOVERED_SELECTION_'+code)


@dataclass(frozen=True, kw_only=True)
class RecoveredSelectionAssessment:
    scope: str
    selection_assessment: S.SealedSelectionAssessment
    route_id: str
    attempt_id: str
    incident_id: str
    outcome_event_id: str
    recovery_artifact_digest: str
    destination_store_binding_sha256: str
    release_record_id: str | None
    incident_context_sha256: str
    incident_head: str
    incident_sequence: int
    attempt_head: str
    attempt_sequence: int
    research_selection_ready: bool
    current_operational_use: bool = False
    execution_ready: bool = False
    automatic_operational_recovery_supported: bool = False


def _destination_prefix(store, required):
    """Observe a historical head inside the actual bounded current catalog chain."""
    failure = None
    with store._locked():
        catalog = store._load()
        try:
            raw = store._read_catalog()
            _need(len(raw) == catalog.size and raw.count(b'\n') == catalog.sequence,
                  'DESTINATION_CHANGED')
            head, found = store.genesis_digest, False
            for number, line in enumerate(raw.split(b'\n')[:-1], 1):
                row = BS._decode(line)
                _need(row['sequence'] == number and row['previous_sha256'] == head
                      and row['context_sha256'] == store.context_sha256
                      and row['row_sha256'] == BS._digest('row', {k:v for k,v in row.items()
                                                                if k != 'row_sha256'}),
                      'DESTINATION_CHANGED')
                head = row['row_sha256']
                found = found or (number, head) == required
            _need(found and head == catalog.head, 'DESTINATION_CHANGED')
        except RecoveredSelectionError as exc:
            failure = exc
        _need_after = store._load() == catalog
        # Owned business diagnostics must not be relabelled by store cleanup.
        if not _need_after:
            failure = RecoveredSelectionError('RECOVERED_SELECTION_DESTINATION_CHANGED')
    if failure is not None:
        raise failure
    return catalog.sequence, catalog.head


def _release_provenance(store, event, snapshot):
    """The release's claimed prior head must match its actual backed Journal row."""
    failure = None
    with store._locked() as (pins, anchor):
        current = store._load(pins)
        try:
            _need(current[0] == snapshot, 'DEPENDENCY_CHANGED')
            raw = store._read(pins, store.root, 'journal.jsonl', store.limits.max_journal_bytes)
            _need(len(raw) == current[1] and raw.count(b'\n') == snapshot.sequence,
                  'RELEASE_BINDING_CHANGED')
            head, matches = store.genesis_digest, 0
            for number, line in enumerate(raw.split(b'\n')[:-1], 1):
                row = IS._decode(line, store._row_max())
                _need(row['sequence'] == number and row['previous_sha256'] == head
                      and row['context_sha256'] == store.context_sha256
                      and row['row_sha256'] == IS._digest('row', {k:v for k,v in row.items()
                                                                if k != 'row_sha256'}),
                      'RELEASE_BINDING_CHANGED')
                if row['event']['event_id'] == event.event_id:
                    _need(IS._canonical(row['event']) == I.event_bytes(event, limits=store.limits.format_limits)
                          and tuple(event.payload['incident_head']) == (number-1, head),
                          'RELEASE_BINDING_CHANGED')
                    matches += 1
                head = row['row_sha256']
            _need(matches == 1 and head == snapshot.head, 'RELEASE_BINDING_CHANGED')
        except RecoveredSelectionError as exc:
            failure = exc
        if store._load(pins) != current:
            failure = RecoveredSelectionError('RECOVERED_SELECTION_DEPENDENCY_CHANGED')
        store._check_anchor(pins, anchor)
    if failure is not None:
        raise failure



def _attempt_prefix(store, required, snapshot):
    """A reused record may name a genuine older global attempt-store prefix."""
    failure = None
    with store._locked() as (pins, anchor):
        current = store._load(pins)
        try:
            _need(current[0] == snapshot, 'DEPENDENCY_CHANGED')
            raw = store._read(pins, store.root, 'journal.jsonl', store.limits.max_journal_bytes)
            _need(len(raw) == current[1] and raw.count(b'\n') == snapshot.sequence,
                  'RELEASE_BINDING_CHANGED')
            head, found = store.genesis_digest, False
            for number, line in enumerate(raw.split(b'\n')[:-1], 1):
                row = RS._decode(line, store._row_max())
                _need(row['sequence'] == number and row['previous_sha256'] == head
                      and row['context_sha256'] == store.context_sha256
                      and row['row_sha256'] == RS._digest('row', {k:v for k,v in row.items()
                                                                if k != 'row_sha256'}),
                      'RELEASE_BINDING_CHANGED')
                head = row['row_sha256']
                found = found or (number,head) == required
            _need(found and head == snapshot.head, 'RELEASE_BINDING_CHANGED')
        except RecoveredSelectionError as exc:
            failure = exc
        if store._load(pins) != current:
            failure = RecoveredSelectionError('RECOVERED_SELECTION_DEPENDENCY_CHANGED')
        store._check_anchor(pins, anchor)
    if failure is not None:
        raise failure

def _configuration(destination, incidents, attempts, route):
    namespace, binding = M._inputs(incidents, destination, route.registration.bundle_digest)
    attempt_namespace = R._attempt_namespace(attempts)
    R._not_latched(attempt_namespace)
    _need(namespace == route.incident_namespace_sha256
          and attempt_namespace == route.attempt_namespace_sha256, 'DEPENDENCY_CHANGED')
    destination._configuration()
    _need(R._destination_configuration(destination) == route.destination_configuration_sha256
          and destination.context_sha256 == route.destination_context_sha256
          and destination._root_ids == route.destination_root_ids
          and destination.limits.policy_sha256 == route.storage_policy_sha256
          and destination.limits.object_limits.policy_sha256 == route.object_policy_sha256,
          'DESTINATION_CHANGED')
    roots = (destination.roots.sealed_root, destination.roots.backup_root,
             *incidents._roots, *attempts._roots)
    expected = (*route.destination_root_ids, *incidents._root_ids, *attempts._root_ids)
    identities = tuple(B._directory(path) for path in roots)
    _need(identities == expected, 'DESTINATION_CHANGED')
    for index, path in enumerate(roots):
        for other_index, other in enumerate(roots[:index]):
            _need(not path.is_relative_to(other) and not other.is_relative_to(path)
                  and identities[index] != identities[other_index], 'DESTINATION_CHANGED')
    return namespace, attempt_namespace, binding


def _selection_document(basis):
    _need(type(basis) is S._SelectionRecordBasis, 'ACTUAL_INPUT_REQUIRED')
    names = ('bundle_digest','input_archive_digest','attestation_sha256','revocation_target_sha256',
        'family_sha256','selected_study_id','program_sha256','protocol_sha256','evidence_sha256',
        'profile_contract_sha256','rule_terms_sha256','window_sha256','driver_identity_sha256')
    result = {name:getattr(basis,name) for name in names}
    result['source_reviews'] = [asdict(item) for item in basis.source_reviews]
    result['evaluated_at'] = I._stamp(basis.evaluated_at)
    result['approval_expires_at'] = I._stamp(basis.approval_expires_at)
    return result


def authenticate_recovered_study_selection(destination, bundle_digest, *, incident_store,
        attempts, route_id, incident_id, archive_attestation, source_reviews,
        audit_logical_ids, current_profile, window, history_head_root,
        history_storage_policy=None, clock, authority_provider):
    """Revalidate one restored research route; never accepts a caller verdict."""
    _need(type(destination) is BS.BundleStore and type(incident_store) is IS.IncidentStore
          and type(attempts) is RecoveryAttemptStore and type(authority_provider) is CurrentOwnerAuthority
          and callable(clock) and authority_provider._clock is clock
          and all(R._hash(value) for value in (bundle_digest, route_id, incident_id))
          and type(archive_attestation) is bytes, 'ACTUAL_INPUT_REQUIRED')
    attempt_snapshot = attempts.inspect()
    route = R._route_in(attempt_snapshot.state, route_id)
    _need(route is not None and route.registration.bundle_digest == bundle_digest, 'ROUTE_REQUIRED')
    attempt = R._attempt_in(attempt_snapshot.state, route_id, incident_id)
    _need(attempt is not None and attempt.terminal and attempt.phase == 'EXACT_ARCHIVE_RESTORED'
          and attempt.outcomes and attempt.attempt_id == F.attempt_id(route, incident_id)
          and attempt.artifact_incident_id == F.artifact_incident_id(incident_id), 'RESTORED_ATTEMPT_REQUIRED')
    outcome = attempt.outcomes[-1]
    _need(outcome.status == 'EXACT_ARCHIVE_RESTORED' and outcome.checkpoint is not None
          and outcome.destination_head is not None and outcome.recovery_artifact_digest is not None
          and outcome.revocation_status == 'NOT_REVOKED_AT_HEAD', 'RESTORED_ATTEMPT_REQUIRED')
    body, request = R._document_binding(archive_attestation, route)
    _need(route.registration.bundle_kind == request['bundle_kind'] == 'VERIFIED_UNAPPROVED',
          'VERIFIED_TARGET_REQUIRED')
    namespace, attempt_namespace, binding = _configuration(destination, incident_store, attempts, route)
    # These are structural/actual graph observations only. No owner clock window
    # is started and then reset across the potentially heavy family evaluation.
    M.register_target(incident_store, destination, bundle_digest, clock=clock)
    destination_head = _destination_prefix(destination, outcome.destination_head)
    registered = M._existing(incident_store.inspect().state, binding, bundle_digest)
    _need(registered is not None, 'DEPENDENCY_CHANGED')
    source = route.registration
    graph_fields = ('bundle_digest','input_archive_digest','bundle_kind','raw_manifest_sha256',
                    'verified_manifest_sha256','graph_sha256','objects')
    _need(all(getattr(registered, name) == getattr(source,name) for name in graph_fields),
          'DESTINATION_CHANGED')
    artifact, artifact_bytes, artifact_files = build_recovery_artifact(archive_attestation,
        incident_id=attempt.artifact_incident_id, limits=destination.limits)
    artifact_digest = BF.raw_archive_digest(artifact, limits=destination.limits.format_limits)
    _need(artifact_digest == outcome.recovery_artifact_digest, 'DOCUMENT_CHANGED')
    checkpoint = R._required_checkpoint(route, attempt)
    release = None
    final_snapshot = None
    final_check = None
    completion_watermark = None
    guard_started = False

    def dependencies():
        nonlocal final_snapshot, final_check
        _need(_configuration(destination, incident_store, attempts, route)
              == (namespace, attempt_namespace, binding), 'DEPENDENCY_CHANGED')
        _need(attempts.inspect() == attempt_snapshot, 'DEPENDENCY_CHANGED')
        final_check = M._check_recovered_target(incident_store, destination, bundle_digest, clock=clock)
        final_snapshot = incident_store.inspect()
        _need(M._existing(final_snapshot.state, binding, bundle_digest) == registered
              and M._existing(final_snapshot.state, source.store_binding_sha256, bundle_digest) == source,
              'DEPENDENCY_CHANGED')
        for registration in (registered, source):
            _need(tuple(item.incident_id for item in I.blocked_incidents(final_snapshot.state, registration))
                  == (incident_id,), 'ADDITIONAL_INCIDENT')
        _need(final_check.graph_checked and final_check.incident_head == final_snapshot.head,
              'DEPENDENCY_CHANGED')
        _need(_destination_prefix(destination, outcome.destination_head) == destination_head,
              'DESTINATION_CHANGED')

    def artifact_check():
        # Only an actual read/mismatch is an artifact incident. Expiry, revocation,
        # profile/number failures and supplied-document mismatch are not damage.
        try:
            retained = destination.read_raw(artifact_digest, require_backup=True)
            if retained.manifest_bytes != artifact_bytes or dict(retained.files) != dict(artifact_files):
                raise B.BundleRecoveryError('BUNDLE_RECOVERY_SIGNATURE_BACKUP_MISMATCH')
        except (*M._READ_ERRORS, B.BundleRecoveryError) as cause:
            snapshot = incident_store.inspect()
            M._record_failure(incident_store, destination, namespace, registered, snapshot,
                M._GraphFailure('graph',cause), M._observed(clock,snapshot.state.last_trusted_at))
            raise RecoveredSelectionError('RECOVERED_SELECTION_DEPENDENCY_CHANGED') from None

    def current_restore():
        nonlocal completion_watermark
        artifact_check()
        at = R._clock(clock, checkpoint.observed_at)
        actual = authority_provider.observe_checkpoint(at, key_fingerprint=checkpoint.key_fingerprint,
            code_hash=checkpoint.code_hash, owner_head=checkpoint.owner_head)
        U._authority(archive_attestation, actual, at)
        completion_watermark = U._time(authority_provider._last)
        try:
            verification = B.verify_restored_archive(destination, bundle_digest, archive_attestation,
                incident_id=attempt.artifact_incident_id, authority_provider=authority_provider, clock=clock)
        except ValueError:
            # Attribute a new actual storage fault if present; current approval
            # rejection alone leaves the incident set unchanged.
            artifact_check()
            dependencies()
            raise
        _need(verification.revocation_status == 'NOT_REVOKED_AT_HEAD', 'ATTESTATION_REVOKED')
        _need(verification.recovery_artifact_digest == artifact_digest
              and verification.attestation_sha256 == route.attestation_sha256
              and verification.revocation_target_sha256 == route.revocation_target_sha256,
              'DOCUMENT_CHANGED')
        completion_watermark = max(completion_watermark, verification.verified_at)
        return actual

    dependencies()

    def record(basis):
        nonlocal release, final_snapshot, guard_started, completion_watermark
        guard_started = True
        dependencies()
        authority = current_restore()
        selection = _selection_document(basis)
        release_binding = dict(route_id=route_id,attempt_id=attempt.attempt_id,
            outcome_event_id=outcome.event_id,incident_id=incident_id,
            incident_namespace_sha256=namespace,attempt_namespace_sha256=attempt_namespace,
            source_store_binding_sha256=source.store_binding_sha256,
            source_registration_sha256=I.registration_digest(source,limits=incident_store.limits.format_limits),
            destination_store_binding_sha256=binding,
            destination_registration_sha256=I.registration_digest(registered,limits=incident_store.limits.format_limits),
            bundle_digest=bundle_digest,input_archive_digest=source.input_archive_digest,
            graph_sha256=registered.graph_sha256,recovery_artifact_digest=artifact_digest,selection=selection)
        digest = I.research_release_binding_digest(release_binding, limits=incident_store.limits.format_limits)
        # Recheck dependencies after the potentially slow current-owner/graph work.
        dependencies()
        previous = I.research_route_releases(final_snapshot.state, route_id=route_id,
            incident_id=incident_id,destination_store_binding_sha256=binding,
            limits=incident_store.limits.format_limits)
        release = next((event for event in previous if event.payload['binding_sha256'] == digest),None)
        if release is not None:
            _release_provenance(incident_store,release,final_snapshot)
            _attempt_prefix(attempts,tuple(release.payload['attempt_head']),attempt_snapshot)
            _need(_destination_prefix(destination,tuple(release.payload['destination_head'])) == destination_head,
                  'RELEASE_BINDING_CHANGED')
            saved = F.parse_checkpoint(I._plain(release.payload['owner_checkpoint']))
            at = R._clock(clock,max(completion_watermark,saved.observed_at))
            prior = authority_provider.observe_checkpoint(at,key_fingerprint=saved.key_fingerprint,
                code_hash=saved.code_hash,owner_head=saved.owner_head)
            U._authority(archive_attestation,prior,at)
            completion_watermark = max(completion_watermark,U._time(authority_provider._last))
            return
        at = R._clock(clock, completion_watermark)
        event = I.make_event('RESEARCH_ROUTE_RELEASE', dict(release_schema=1,
            scope='recovered_research_selection',binding=release_binding,binding_sha256=digest,
            incident_head=[final_snapshot.sequence,final_snapshot.head],
            attempt_head=[attempt_snapshot.sequence,attempt_snapshot.head],
            destination_head=list(destination_head),
            owner_checkpoint=F.checkpoint_document(R._checkpoint(authority))),observed_at=at)
        try:
            final_snapshot = incident_store.commit(event, expected_head=final_snapshot.head)
        except Exception:
            M._latch(namespace)
            raise RecoveredSelectionError('RECOVERED_SELECTION_RECORD_UNCONFIRMED') from None
        _release_provenance(incident_store,event,final_snapshot)
        release = event

    def final_dependency_guard():
        nonlocal guard_started
        guard_started = True
        dependencies()
        current_restore()
        dependencies()
        if release is not None:
            _release_provenance(incident_store,release,final_snapshot)

    def completion_dependency_guard():
        _need(final_snapshot is not None and completion_watermark is not None, 'DEPENDENCY_CHANGED')
        _need(_configuration(destination,incident_store,attempts,route)
              == (namespace,attempt_namespace,binding), 'DEPENDENCY_CHANGED')
        with incident_store._pinned() as pins:
            incident_matches = incident_store.head.read() == final_snapshot.head
            pins.check()
        _need(incident_matches, 'DEPENDENCY_CHANGED')
        with attempts._pinned() as pins:
            attempt_matches = attempts.head.read() == attempt_snapshot.head
            pins.check()
        _need(attempt_matches, 'DEPENDENCY_CHANGED')
        with destination._locked():
            destination_matches = destination.head.read() == destination_head[1]
        _need(destination_matches, 'DESTINATION_CHANGED')
        return completion_watermark

    try:
        selection = S._authenticate_sealed_study_selection(destination,bundle_digest,
            archive_attestation=archive_attestation,source_reviews=source_reviews,
            audit_logical_ids=audit_logical_ids,current_profile=current_profile,window=window,
            history_head_root=history_head_root,history_storage_policy=history_storage_policy,
            clock=clock,authority_provider=authority_provider,selection_record_guard=record,
            final_dependency_guard=final_dependency_guard,completion_dependency_guard=completion_dependency_guard)
    except ValueError:
        if not guard_started:
            # Attribute only actual storage damage, not a failed numeric/review
            # check; preserve the original research diagnostic when graph is sound.
            dependencies()
        raise
    _need(type(selection) is S.SealedSelectionAssessment and final_snapshot is not None,
          'ACTUAL_INPUT_REQUIRED')
    selected = selection.research_selection_ready
    _need(not selected or release is not None, 'RECORD_UNCONFIRMED')
    return RecoveredSelectionAssessment(scope='recovered_research_selection',selection_assessment=selection,
        route_id=route_id,attempt_id=attempt.attempt_id,incident_id=incident_id,outcome_event_id=outcome.event_id,
        recovery_artifact_digest=artifact_digest,destination_store_binding_sha256=binding,
        release_record_id=None if not selected else release.event_id,
        incident_context_sha256=incident_store.context_sha256,incident_head=final_snapshot.head,
        incident_sequence=final_snapshot.sequence,attempt_head=attempt_snapshot.head,
        attempt_sequence=attempt_snapshot.sequence,research_selection_ready=selected and release is not None)
