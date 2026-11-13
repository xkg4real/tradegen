"""Actual sealed research selection; detached results never grant order authority.

Original captures are evaluated once, every eligible source review is checked,
then the selected registered factory is bound to actual independently headed
LiveHistory. This can create its ordinary pre-window binding journal, but never
initializes a head or creates a session, order, recovery permit or signing key.
The final owner/graph observation is finite, not a persistent storage lease.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from core.compliance import model as compliance
from execution_control.owner_authority import CurrentOwnerAuthority, MAX_AUTHORITY_AGE_SECONDS
from execution_launch import bundle_attestation as A, bundle_auth as U
from execution_launch import research_bundle as B, research_bundle_format as F, study_review as S
from execution_launch import coordinator as C
from execution_launch.driver import DeploymentWindow
from execution_launch.history_storage import HistoryStoragePolicy, parse_policy, policy_bytes
from execution_launch.live_history import LiveHistory
from execution_launch.profile import (LaunchProfile, parse_profile_json, profile_body,
    profile_contract_digest, rule_terms_digest, preflight_profile)
from execution_launch.program import program_digest
from execution_launch.research_bundle_store import BundleStore
from execution_launch.research_revocation import revocation_target, target_is_revoked
from execution_launch.review_auth import (MAX_DOCUMENT_BYTES, parse_review_document,
    verify_source_review, verify_implementation_review)
from execution_launch.runner import ImplementationBinding
from execution_launch.strategy import evidence_digest
from execution_launch.study import MarketSelection


class SealedStudyReviewError(ValueError):
    """Fixed diagnostics only; no original data, paths, accounts or owner details."""


def _need(ok, code):
    if not ok:
        raise SealedStudyReviewError(code)


def _time(value):
    _need(type(value) is datetime and value.utcoffset() is not None, 'SEALED_SELECTION_TIME_INVALID')
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class SealedSelectionAssessment:
    scope: str
    bundle_digest: str
    input_archive_digest: str
    attestation_sha256: str
    revocation_target_sha256: str
    revocation_owner_head: tuple[int, str]
    selection: MarketSelection
    evaluated_at: datetime
    verified_at: datetime
    authenticated_study_ids: tuple[str, ...]
    archive_identity_authenticated: bool
    source_reviews_authenticated: bool
    selected_implementation_authenticated: bool
    research_selection_ready: bool
    revocation_status: str = 'NOT_REVOKED_AT_HEAD'
    execution_ready: bool = False
    current_operational_use: bool = False
    automatic_recovery_supported: bool = False


def _documents(source_reviews, audit_logical_ids):
    _need(isinstance(source_reviews, Mapping) and isinstance(audit_logical_ids, Mapping),
          'SEALED_SELECTION_DOCUMENT_FAMILY_INVALID')
    def bounded(source):
        _need(len(source) <= 128, 'SEALED_SELECTION_DOCUMENT_FAMILY_INVALID')
        result = {}
        for index, (key, value) in enumerate(source.items()):
            _need(index < 128 and type(key) is str and 0 < len(key) <= 128
                  and key not in result, 'SEALED_SELECTION_DOCUMENT_FAMILY_INVALID')
            result[key] = value
        return result
    documents, audits = bounded(source_reviews), bounded(audit_logical_ids)
    _need(len(documents) <= 128 and set(documents) == set(audits)
          and all(type(key) is str and 0 < len(key) <= 128 for key in documents)
          and all(type(raw) is bytes and 0 < len(raw) <= MAX_DOCUMENT_BYTES for raw in documents.values())
          and all(type(value) is str and 0 < len(value) <= 128 for value in audits.values()),
          'SEALED_SELECTION_DOCUMENT_FAMILY_INVALID')
    bodies = {key:parse_review_document(raw)['body'] for key,raw in documents.items()}
    _need(all(body['request']['study_id'] == key for key,body in bodies.items()),
          'SEALED_SELECTION_DOCUMENT_ID_MISMATCH')
    return documents, audits, bodies


def _archive(document, authority, now, target):
    U._authority(document, authority, now)
    _need(not target_is_revoked(U._revocations(authority.context), purpose=A.PURPOSE, target_sha256=target),
          'SEALED_SELECTION_ARCHIVE_REVOKED')


def _audit_files(manifest, files, bodies, audits):
    inventory = {item.logical_id:item for item in manifest.files}
    for identifier, body in bodies.items():
        logical = audits[identifier]
        item = inventory.get(logical)
        _need(item is not None and item.role == 'report' and item.required is True
              and item.byte_count > 0 and item.study_id in (None, identifier),
              'SEALED_SELECTION_AUDIT_FILE_INVALID')
        _need(hashlib.sha256(files[logical]).hexdigest() == body['audit_sha256'],
              'SEALED_SELECTION_AUDIT_HASH_MISMATCH')


def _implementation(candidate, result, variant, composition, document, authority, now):
    binding = ImplementationBinding(program_digest=variant.strategy_code_sha256,
        protocol_digest=evidence_digest(candidate.protocol), evidence_digest=evidence_digest(result),
        profile_contract_digest=profile_contract_digest(variant),
        rule_terms_digest=rule_terms_digest(variant.instrument_rules))
    return verify_implementation_review(binding, composition.driver, document, authority=authority, now=now,
        approved_history_provider=composition.history.provider,
        approved_history_verifier=composition.history.verifier)


def _authenticate_sealed_study_selection(store, bundle_digest, *, archive_attestation,
        source_reviews, audit_logical_ids, current_profile, window, history_head_root,
        history_storage_policy=None, clock, authority_provider, final_dependency_guard=None,
        completion_dependency_guard=None):
    """Evaluate sealed originals once and authenticate a fixed research selection.

    Caller-created assessments/results/providers are not accepted as trust. The
    current profile is supplied configuration, not account or market provenance.
    A selected implementation is authenticated for its exact deployment window;
    all operational gates remain outside this display-only result.
    """
    _need(type(store) is BundleStore, 'SEALED_SELECTION_STORE_REQUIRED')
    _need(type(authority_provider) is CurrentOwnerAuthority and callable(clock)
          and getattr(authority_provider, '_clock', None) is clock, 'SEALED_SELECTION_ACTUAL_PROVIDER_REQUIRED')
    _need(type(archive_attestation) is bytes, 'SEALED_SELECTION_DOCUMENT_BYTES_REQUIRED')
    envelope = A.parse_attestation_document(archive_attestation)
    request = envelope['body']['request']
    _need(type(bundle_digest) is str and bundle_digest == request['bundle_digest']
          and request['bundle_kind'] == 'VERIFIED_UNAPPROVED', 'SEALED_SELECTION_VERIFIED_TARGET_REQUIRED')
    _need(type(current_profile) is LaunchProfile and type(window) is DeploymentWindow
          and isinstance(history_head_root, Path) and history_head_root.is_absolute(),
          'SEALED_SELECTION_CONFIGURATION_REQUIRED')
    profile = parse_profile_json(json.dumps(profile_body(current_profile), allow_nan=False))
    window = replace(window)
    start, end = _time(window.start), _time(window.end)
    _need(timedelta(0) < end-start <= timedelta(hours=24), 'SEALED_SELECTION_WINDOW_INVALID')
    _need(profile.venue == 'upbit' and profile.market == 'spot' and profile.quote_currency == 'KRW'
          and profile.universe_rule_sha256 is None and profile.instrument_rules is not None,
          'SEALED_SELECTION_SCOPE_UNSUPPORTED')
    if history_storage_policy is not None:
        _need(type(history_storage_policy) is HistoryStoragePolicy, 'SEALED_SELECTION_STORAGE_POLICY_INVALID')
        history_storage_policy = parse_policy(policy_bytes(history_storage_policy))
    documents, audits, bodies = _documents(source_reviews, audit_logical_ids)

    # This is the only arithmetic/issuance path. Its actual family is never
    # reconstructed from a manifest or supplied report and never evaluated twice.
    snapshot = B._evaluate_sealed_study_snapshot(store, bundle_digest)
    manifest = F.parse_verified_bundle(snapshot.verified_manifest_bytes, limits=store.limits.format_limits)
    graph = (snapshot.raw_manifest_bytes, snapshot.verified_manifest_bytes, tuple(sorted(snapshot.files.items())))
    artifact = next(snapshot.files[item.logical_id] for item in manifest.files if item.role == 'program_source')
    candidates = {candidate.protocol.study_id:candidate for candidate in snapshot.plan.candidates}
    results = {row.study_id:row.result for row in snapshot.family.rows}
    variants = {}
    for identifier, candidate in candidates.items():
        variant = replace(profile, strategy_id=candidate.program.strategy_id,
                          strategy_code_sha256=program_digest(candidate.program, artifact))
        _need(candidate.protocol.universe_rule_sha256 is None
              and profile_contract_digest(variant) == candidate.protocol.profile_contract_digest
              and rule_terms_digest(variant.instrument_rules) == candidate.protocol.rule_terms_digest,
              'SEALED_SELECTION_CURRENT_CONTRACT_MISMATCH')
        variants[identifier] = variant
    _audit_files(manifest, snapshot.files, bodies, audits)
    target = revocation_target(archive_attestation, purpose=A.PURPOSE)
    document_digest = A.attestation_document_digest(archive_attestation)

    # Heavy research is outside the authorization transaction. Every subsequent
    # expensive read/hash/signature stays bounded by the FIRST actual observation.
    started = _time(clock())
    for variant in variants.values():
        _need(set(preflight_profile(variant, now=started).reasons) <= {'SIGNED_CONTEXT_REQUIRED'},
              'SEALED_SELECTION_PROFILE_NOT_CURRENT')
    first = authority_provider(started)
    _archive(archive_attestation, first, started, target)
    _need(U._graph(store, bundle_digest, request, deployment_code_hash=first.context.code_hash) == graph,
          'SEALED_SELECTION_GRAPH_CHANGED')
    authenticated = S._authenticate_evaluated_selection(snapshot.plan, profile=profile, evaluated=snapshot.family,
        reviews=documents, evaluated_at=snapshot.evaluated_at, clock=clock,
        authority_provider=authority_provider, initial_now=started)
    family_stamp = S._family_stamp(snapshot.family)
    selected = authenticated.selection.selected_study_id
    composition = None
    last_observation = authenticated.verified_at
    if authenticated.selection.status == 'SELECTED':
        _need(selected in documents and selected in candidates, 'SEALED_SELECTION_SELECTED_REVIEW_REQUIRED')
        composition = C._compose_driver(profile=variants[selected], program=candidates[selected].program,
            protocol=candidates[selected].protocol, window=window, clock=clock, head_root=history_head_root,
            storage_policy=history_storage_policy)
        _need(type(composition.history) is LiveHistory, 'SEALED_SELECTION_ACTUAL_HISTORY_REQUIRED')
        at = _time(clock())
        _need(at >= authenticated.verified_at, 'SEALED_SELECTION_CLOCK_ROLLBACK')
        last_observation = at
        observed = authority_provider(at)
        _archive(archive_attestation, observed, at, target)
        _implementation(candidates[selected], results[selected], variants[selected], composition,
                        documents[selected], observed, at)

    _need(U._graph(store, bundle_digest, request, deployment_code_hash=first.context.code_hash) == graph,
          'SEALED_SELECTION_GRAPH_CHANGED')
    if composition is not None:
        # _durable_unchanged alone checks only size/head for legacy v1. Replaying
        # actual journal bytes additionally catches same-size legacy corruption.
        composition.history._durable_unchanged()
        composition.history._replay(composition.identity, install=False)
    if final_dependency_guard is not None:
        final_dependency_guard()
    observed_at = _time(clock())
    _need(observed_at >= last_observation, 'SEALED_SELECTION_CLOCK_ROLLBACK')
    latest = authority_provider(observed_at)
    _archive(archive_attestation, latest, observed_at, target)
    _archive(archive_attestation, first, observed_at, target)
    for identifier in authenticated.authenticated_study_ids:
        verify_source_review(S._binding(candidates[identifier], results[identifier]), documents[identifier],
                             authority=latest, now=observed_at)
    if composition is not None:
        _implementation(candidates[selected], results[selected], variants[selected], composition,
                        documents[selected], latest, observed_at)
    _need(S._family_stamp(snapshot.family) == family_stamp, 'SEALED_SELECTION_EVALUATION_CHANGED')
    observations = tuple((_time(authority.observed_at), authority.context.date) for authority in (first, latest))
    periods = tuple((_time(datetime.fromisoformat(body['issued_at'])),
                     _time(datetime.fromisoformat(body['expires_at']))) for body in (envelope['body'], *bodies.values()))
    rule_observed_at = _time(profile.instrument_rules.asof)
    revocation_head = latest.context.owner.head
    if completion_dependency_guard is not None:
        completion_dependency_guard()
    # Only bounded primitive comparisons follow this completion clock.
    finished = _time(clock())
    _need(finished >= observed_at, 'SEALED_SELECTION_CLOCK_ROLLBACK')
    day = finished.astimezone(compliance.KST).date()
    for original_at, original_day in observations:
        _need(timedelta(0) <= finished-original_at <= timedelta(seconds=MAX_AUTHORITY_AGE_SECONDS),
              'SEALED_SELECTION_OWNER_AUTHORITY_STALE')
        _need(original_day == day, 'SEALED_SELECTION_OWNER_DAY_CHANGED')
    _need(all(issued <= finished < expires for issued,expires in periods), 'SEALED_SELECTION_EXPIRED_OR_FUTURE')
    _need(timedelta(0) <= finished-rule_observed_at <= timedelta(minutes=5), 'SEALED_SELECTION_PROFILE_NOT_CURRENT')
    return SealedSelectionAssessment(scope='sealed_research_selection', bundle_digest=bundle_digest,
        input_archive_digest=snapshot.input_archive_digest, attestation_sha256=document_digest,
        revocation_target_sha256=target, revocation_owner_head=revocation_head,
        selection=authenticated.selection, evaluated_at=snapshot.evaluated_at, verified_at=finished,
        authenticated_study_ids=authenticated.authenticated_study_ids, archive_identity_authenticated=True,
        source_reviews_authenticated=authenticated.source_reviews_authenticated,
        selected_implementation_authenticated=composition is not None,
        research_selection_ready=composition is not None and authenticated.source_reviews_authenticated)


def authenticate_sealed_study_selection(store, bundle_digest, *, archive_attestation,
        source_reviews, audit_logical_ids, current_profile, window, history_head_root,
        history_storage_policy=None, clock, authority_provider):
    """Existing research-only API; no incident namespace or callback is accepted."""
    return _authenticate_sealed_study_selection(store, bundle_digest,
        archive_attestation=archive_attestation, source_reviews=source_reviews,
        audit_logical_ids=audit_logical_ids, current_profile=current_profile, window=window,
        history_head_root=history_head_root, history_storage_policy=history_storage_policy,
        clock=clock, authority_provider=authority_provider)
