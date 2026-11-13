"""Research-only sealed selection with mandatory independent incident checks.

The configured namespace is an explicitly retained dependency, not a global
oracle. No public callback, cached assessment or caller verdict can bypass the
initial/final actual store checks. The final head is a finite observation, never
a lease or order permission. Existing direct sealed selection remains a separate
research-only API and is not represented as incident protected.
"""
from __future__ import annotations

from dataclasses import dataclass

from execution_launch import research_incident_monitor as M
from execution_launch import sealed_study_review as S


@dataclass(frozen=True, kw_only=True)
class IncidentAwareSelectionAssessment:
    selection_assessment: S.SealedSelectionAssessment
    incident_context_sha256: str
    incident_head: str
    incident_sequence: int
    execution_ready: bool = False
    current_operational_use: bool = False
    automatic_recovery_supported: bool = False


def _usable(value):
    M._need(type(value) is M.IncidentCheck and value.registered, 'INCIDENT_ACTUAL_CHECK_REQUIRED')
    M._need(not value.held, 'INCIDENT_SELECTION_QUARANTINED')
    M._need(value.graph_checked, 'INCIDENT_SELECTION_UNCHECKED')


def authenticate_incident_aware_selection(bundle_store, bundle_digest, *, incident_store,
        archive_attestation, source_reviews, audit_logical_ids, current_profile, window,
        history_head_root, history_storage_policy=None, clock, authority_provider):
    namespace = M.namespace_identity(incident_store)
    context_sha256 = incident_store.context_sha256
    initial = M.check_target(incident_store, bundle_store, bundle_digest, clock=clock)
    _usable(initial)
    final_check = None
    guard_started = False

    def final_dependency_guard():
        nonlocal final_check, guard_started
        guard_started = True
        M._need(M.namespace_identity(incident_store) == namespace, 'INCIDENT_NAMESPACE_CHANGED')
        final_check = M.check_target(incident_store, bundle_store, bundle_digest, clock=clock)
        _usable(final_check)
        M._need(final_check.store_binding_sha256 == initial.store_binding_sha256,
                'INCIDENT_STORE_BINDING_CHANGED')

    def completion_dependency_guard():
        M._need(final_check is not None, 'INCIDENT_SELECTION_FINAL_CHECK_REQUIRED')
        M._need(M.namespace_identity(incident_store) == namespace, 'INCIDENT_NAMESPACE_CHANGED')
        # _pinned validates bounded root/lock metadata only; BaselineHead.read
        # reads its small retained record and never invokes chain replay.
        with incident_store._pinned() as pins:
            head = incident_store.head.read()
            pins.check()
        M._need(head == final_check.incident_head, 'INCIDENT_FINAL_HEAD_CHANGED')

    try:
        selection = S._authenticate_sealed_study_selection(bundle_store, bundle_digest,
            archive_attestation=archive_attestation, source_reviews=source_reviews,
            audit_logical_ids=audit_logical_ids, current_profile=current_profile, window=window,
            history_head_root=history_head_root, history_storage_policy=history_storage_policy,
            clock=clock, authority_provider=authority_provider, final_dependency_guard=final_dependency_guard,
            completion_dependency_guard=completion_dependency_guard)
    except ValueError:
        if not guard_started:
            # A failed source/eligibility/numerical/authority check is NOT itself
            # evidence corruption. Only a new actual store observation may create
            # an incident; otherwise preserve the original research diagnostic.
            M._need(M.namespace_identity(incident_store) == namespace, 'INCIDENT_NAMESPACE_CHANGED')
            _usable(M.check_target(incident_store, bundle_store, bundle_digest, clock=clock))
        raise
    # No heavy reads or new authorization timestamp after the original backend's
    # final owner/expiry/completion-clock checks. The guard precedes those checks.
    M._need(type(selection) is S.SealedSelectionAssessment and final_check is not None,
            'INCIDENT_SELECTION_FINAL_CHECK_REQUIRED')
    return IncidentAwareSelectionAssessment(selection_assessment=selection,
        incident_context_sha256=context_sha256,
        incident_head=final_check.incident_head, incident_sequence=final_check.incident_sequence)
