"""Pure identities and restrictive-set checks for detached research documents.

A target identifies the purpose's existing canonical signing bytes, not a JSON
file spelling or a claim that its signature is trusted. These helpers never read
owner state, authenticate a key, issue evidence or authorize an action. Consumers
must obtain the restrictive set from their actual freshly sealed owner context.
Parser imports are local to avoid a cycle with the authentication consumers.
"""
from __future__ import annotations

import hashlib
import re


EVENT_KIND = 'research_attestation_revoked'
TARGET_DOMAIN = b'tradegen-research-attestation-revocation-target/1\n'
PURPOSES = frozenset({
    'research_archive_manifest_attestation',
    'strategy_source_and_fixed_implementation_review',
    'strategy_source_and_fixed_carry_implementation_review',
})
REASON_CODES = frozenset({'OWNER_WITHDRAWN', 'EVIDENCE_UNTRUSTED', 'REVIEW_ERROR'})
_HASH = re.compile(r'[0-9a-f]{64}')
_DATA = frozenset({'purpose', 'target_sha256', 'reason_code'})


class ResearchRevocationError(ValueError):
    """Fixed diagnostics only; no document, path or external exception text."""


def _need(condition, code):
    if not condition:
        raise ResearchRevocationError(code)


def _purpose(value):
    return type(value) is str and value in PURPOSES


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def revocation_target(document: bytes, *, purpose: str) -> str:
    """Identify a well-formed signed body; this performs no signature verification.

    Source documents may use their parser's supported whitespace/key ordering.
    Their canonical signed content still produces one target. Archive documents
    retain their existing strict byte codec. The existing purpose and signing
    domain remain intact, and the envelope cannot supply a trusted public key.
    """
    _need(_purpose(purpose), 'RESEARCH_REVOCATION_PURPOSE_INVALID')
    _need(type(document) is bytes, 'RESEARCH_REVOCATION_DOCUMENT_INVALID')
    try:
        if purpose == 'research_archive_manifest_attestation':
            from execution_launch.bundle_attestation import (
                attestation_signing_bytes, parse_attestation_document,
            )
            body = parse_attestation_document(document)['body']
            signing_bytes = attestation_signing_bytes(body)
        else:
            from execution_launch.review_auth import parse_review_document, review_signing_bytes
            body = parse_review_document(document)['body']
            signing_bytes = review_signing_bytes(body)
        _need(body['purpose'] == purpose, 'RESEARCH_REVOCATION_PURPOSE_INVALID')
    except ResearchRevocationError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError, RecursionError):
        raise ResearchRevocationError('RESEARCH_REVOCATION_DOCUMENT_INVALID') from None
    return hashlib.sha256(TARGET_DOMAIN + signing_bytes).hexdigest()


def validate_revocation_data(value: dict) -> dict:
    """Validate the event's exact data shape without granting signer authority."""
    _need(type(value) is dict and set(value) == _DATA, 'RESEARCH_REVOCATION_DATA_INVALID')
    _need(_purpose(value['purpose']) and _hash(value['target_sha256'])
          and type(value['reason_code']) is str and value['reason_code'] in REASON_CODES,
          'RESEARCH_REVOCATION_DATA_INVALID')
    return {name: value[name] for name in ('purpose', 'target_sha256', 'reason_code')}


def validate_revoked_targets(value) -> frozenset[tuple[str, str]]:
    """Check immutable owner-set structure only, not its origin or freshness."""
    _need(type(value) is frozenset and all(
        type(row) is tuple and len(row) == 2 and _purpose(row[0]) and _hash(row[1])
        for row in value), 'RESEARCH_REVOCATION_STATE_INVALID')
    return value


def target_is_revoked(revoked_targets, *, purpose: str, target_sha256: str) -> bool:
    """Pure membership; a caller-constructed empty set is never current authority."""
    _need(_purpose(purpose), 'RESEARCH_REVOCATION_PURPOSE_INVALID')
    _need(_hash(target_sha256), 'RESEARCH_REVOCATION_DATA_INVALID')
    return (purpose, target_sha256) in validate_revoked_targets(revoked_targets)
