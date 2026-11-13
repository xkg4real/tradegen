"""Persisted archive-confirmation engine; no operational approval channel.

All expected WebAuthn values come from this engine's actual backed ledger.
Historical APPLIED/EXACT_RETRY facts never authorize an app consumer or an order.
No private key, injectable verifier, arbitrary owner callback or caller clock is
accepted by an operation. The constructor is explicit trusted composition only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets

from . import authority_contract as A, contract as C, webauthn_verify as V
from .bootstrap import verify_bootstrap, verify_disable_document, verify_grant_document
from .ledger import AuthorityLedger
from .owner_view import OwnerReader, require_grant_eligibility
from .packet import read_packet, recheck_packet, archive_target
from .release import verify_release

_KST = timezone(timedelta(hours=9))
_TTL = timedelta(seconds=300)
_AGE = timedelta(seconds=30)
_STATUSES = frozenset(('PENDING', 'APPLIED', 'EXACT_RETRY', 'EXPIRED', 'REJECTED', 'INVALIDATED', 'INDETERMINATE'))
_REASONS = frozenset('PASSKEY_PENDING PASSKEY_APPLIED PASSKEY_EXACT_RETRY PASSKEY_EXPIRED PASSKEY_REVOKED '
    'PASSKEY_GRANT_INVALID PASSKEY_REGISTRY_CHANGED PASSKEY_TARGET_CHANGED PASSKEY_ORIGIN_RP_INVALID '
    'PASSKEY_UV_REQUIRED PASSKEY_SIGNATURE_INVALID PASSKEY_REQUEST_REUSED PASSKEY_CLOCK_INVALID '
    'PASSKEY_OWNER_CHANGED PASSKEY_RESOURCE_LIMIT PASSKEY_STORE_INDETERMINATE PASSKEY_FORMAT_INVALID '
    'PASSKEY_CHANNEL_REFUSED PASSKEY_SCOPE_UNSUPPORTED PASSKEY_BOOTSTRAP_REQUIRED'.split())


class _EngineOnly:
    __slots__ = ()

    @property
    def observation_scope(self): return 'ENGINE_STATE_ONLY'
    @property
    def operational_channel_ready(self): return False
    @property
    def current_use_eligible(self): return False
    @property
    def source_authenticated(self): return False
    @property
    def research_selection_ready(self): return False
    @property
    def execution_ready(self): return False


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationResult(_EngineOnly):
    status: str
    request_id: str | None
    application_id: str | None
    head: A.Head | None
    reason: str

    def __post_init__(self):
        C.need(self.status in _STATUSES and self.reason in _REASONS)
        for value in (self.request_id, self.application_id):
            if value is not None: C.hashed(value)
        C.need(self.head is None or type(self.head) is A.Head)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProposalReceipt(_EngineOnly):
    proposal_sha256: str
    byte_count: int
    sha256: str


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalEngineSummary(_EngineOnly):
    authority_id: str
    head: A.Head
    grant_sha256: str | None
    registry_epoch: int
    credential_count: int
    pending_request_count: int
    application_count: int
    pending_notification_count: int
    disabled: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineCurrentObservation(_EngineOnly):
    authority_id: str
    application_id: str
    grant_sha256: str
    registry_epoch: int
    authority_head: A.Head
    owner_checkpoint: A.OwnerCheckpoint
    request_sha256: str
    evidence_sha256: str
    packet_sha256: str
    status: str
    observed_at: datetime
    completed_at: datetime
    expires_at: datetime

    def __post_init__(self):
        C.need(self.status in ('ACTIVE', 'EXPIRED', 'REVOKED', 'INVALIDATED'))
        for value in (self.authority_id, self.application_id, self.grant_sha256,
                      self.request_sha256, self.evidence_sha256, self.packet_sha256): C.hashed(value)
        C.need(type(self.authority_head) is A.Head and type(self.owner_checkpoint) is A.OwnerCheckpoint)
        C.need(C.instant(self.observed_at) <= C.instant(self.completed_at))
        C.instant(self.expires_at)


def _body(raw):
    return A.decode(raw, maximum=A.MAX_EVENT_BYTES)


def _notification(authority, kind, *, request_id=None, application_id=None, status, at):
    identity = dict(authority_id=authority, request_id=request_id, application_id=application_id, kind=kind)
    return A.parse_notification(A.canonical(identity | dict(
        intent_id=A.record_digest('notification-id', A.canonical(identity)), status=status, created_at=C.stamp(at))))


def _request(config, grant, epoch, kind, target, at, approval_expires_at=None):
    display = dict(schema=1, authority_id=config.authority_id, kind=kind, target=target,
        requested_at=C.stamp(at), challenge_expires_at=C.stamp(at+_TTL),
        approval_expires_at=None if approval_expires_at is None else C.stamp(approval_expires_at))
    nonce = secrets.token_bytes(32)
    core = display | dict(request_id=secrets.token_hex(32), grant_sha256=grant.digest,
        registry_epoch=epoch, nonce=C.b64(nonce), display_sha256=A.record_digest('display', A.canonical(display)))
    request_sha = A.record_digest('request', A.canonical(core))
    challenge = hashlib.sha256(b'tradegen-passkey-archive/challenge/1\n'+nonce+bytes.fromhex(request_sha)).digest()
    return A.parse_request(A.canonical(core | dict(request_sha256=request_sha, challenge=C.b64(challenge))))


class Engine:
    def __init__(self, *, config, ledger, owner_reader, broker_release_root, broker_release,
                 rp_release_root, rp_release, dependency_roots, clock):
        C.need(type(config) is A.BrokerConfig and type(ledger) is AuthorityLedger
               and type(owner_reader) is OwnerReader and type(broker_release) is A.ReleaseManifest
               and type(rp_release) is A.ReleaseManifest and callable(clock))
        C.need(owner_reader.clock is clock, 'PASSKEY_CLOCK_INVALID')
        C.need(type(dependency_roots) is tuple and all(isinstance(p, Path) and p.is_absolute() for p in dependency_roots))
        C.need(isinstance(broker_release_root, Path) and broker_release_root.is_absolute()
               and isinstance(rp_release_root, Path) and rp_release_root.is_absolute())
        self.config, self.ledger, self.owner_reader = config, ledger, owner_reader
        self.broker_release_root, self.broker_release = broker_release_root, broker_release
        self.rp_release_root, self.rp_release = rp_release_root, rp_release
        self.dependency_roots, self.clock = dependency_roots, clock
        self._pins = (config, ledger, owner_reader, broker_release_root, broker_release,
                      rp_release_root, rp_release, dependency_roots, clock)
        self._config_digest = config.digest
        self._release_digests = (broker_release.digest, rp_release.digest)
        self._installation = ledger.installation
        self._last = None
        self._installation_path = None
        self._installation_digest = None
        from .cli import checked_directory
        self._directories = (broker_release_root, rp_release_root, Path(config.packet_inbox))+dependency_roots
        self._directory_ids = tuple(checked_directory(p) for p in self._directories)
        self._configuration()

    @classmethod
    def open(cls, config_path):
        from .cli import load_installation
        installation = load_installation(config_path)
        clock = lambda: datetime.now(timezone.utc)
        ledger = AuthorityLedger(roots=installation.ledger_roots, installation=installation.ledger_installation)
        reader = OwnerReader(locations=installation.locations, roots=installation.trust_roots, clock=clock)
        result = cls(config=installation.config, ledger=ledger, owner_reader=reader,
            broker_release_root=installation.broker_release_root, broker_release=installation.broker_release,
            rp_release_root=installation.rp_release_root, rp_release=installation.rp_release,
            dependency_roots=installation.dependency_roots, clock=clock)
        result._installation_path, result._installation_digest = config_path, installation.sidecar_sha256
        AuthorityLedger.inspect(ledger)  # only explicitly prepared stores; never initialize/adopt missing files
        return result

    def _configuration(self):
        from .cli import checked_directory
        C.need(tuple(checked_directory(p) for p in self._directories) == self._directory_ids,
               'PASSKEY_OWNER_CHANGED')
        C.need(all(a is b for a,b in zip(self._pins, (self.config, self.ledger, self.owner_reader,
            self.broker_release_root, self.broker_release, self.rp_release_root, self.rp_release,
            self.dependency_roots, self.clock))), 'PASSKEY_OWNER_CHANGED')
        C.need(self.config.digest == self._config_digest
               and (self.broker_release.digest, self.rp_release.digest) == self._release_digests
               and self.broker_release.role == 'BROKER' and self.rp_release.role == 'RP'
               and self.owner_reader.clock is self.clock and self.ledger.installation is self._installation
               and self._installation.config_sha256 == self.config.digest
               and self._installation.authority_id == self.config.authority_id
               and self._installation.roots == self.owner_reader.roots
               and self.owner_reader.locations.app_repo == Path(self.config.app_repo)
               and (self.ledger.roots.primary, self.ledger.roots.backup, self.ledger.roots.head) ==
                   (Path(self.config.authority_root), Path(self.config.backup_root), Path(self.config.head_root)),
               'PASSKEY_OWNER_CHANGED')
        if self._installation_path is not None:
            from .cli import load_installation
            installed = load_installation(self._installation_path)
            C.need(installed.sidecar_sha256 == self._installation_digest
                   and installed.config.digest == self._config_digest, 'PASSKEY_OWNER_CHANGED')

    def _time(self, retained=None):
        try:
            now = C.instant(self.clock())
        except Exception:
            raise C.PasskeyError('PASSKEY_CLOCK_INVALID') from None
        C.need((self._last is None or now >= self._last) and (retained is None or now >= retained),
               'PASSKEY_CLOCK_INVALID')
        self._last = now
        return now

    def _complete(self, completed):
        C.need(self._last is None or C.instant(completed) >= self._last, 'PASSKEY_CLOCK_INVALID')
        self._last = completed

    def _releases(self):
        self._configuration()
        verify_release(self.broker_release_root, self.broker_release, dependency_roots=self.dependency_roots)
        verify_release(self.rp_release_root, self.rp_release, dependency_roots=self.dependency_roots)
        self._configuration()

    def _commit(self, op, snapshot, kind, payload):
        return op.commit(A.ProposedEvent(kind=kind, observed_at=self._time(snapshot.state.last_trusted_at),
            payload_bytes=A.canonical(payload)), expected_head=snapshot.head)

    def _owner(self, op, snapshot):
        previous_clock = self._last
        observation = OwnerReader.observe(self.owner_reader, retained=snapshot.state.owner_evidence)
        C.need(previous_clock is None or observation.evidence.observed_at >= previous_clock,
               'PASSKEY_CLOCK_INVALID')
        self._complete(observation.completed_at)
        old = snapshot.state.owner_evidence
        if old is None or old.head != observation.evidence.head:
            try:
                snapshot = self._commit(op, snapshot, 'OWNER_CHECKPOINT_ADVANCED',
                                        {'evidence':A.owner_evidence_document(observation.evidence)})
            except Exception:
                # A verified restrictive head must not be forgotten as a normal
                # eligibility failure when its durable checkpoint is uncertain.
                raise C.PasskeyError('PASSKEY_STORE_INDETERMINATE') from None
        return snapshot, observation

    def _eligible(self, snapshot, observation, *, allow_disabled=False):
        grant = snapshot.state.grant
        C.need(grant is not None, 'PASSKEY_BOOTSTRAP_REQUIRED')
        C.need(allow_disabled or not snapshot.state.disabled, 'PASSKEY_REVOKED')
        body = _body(grant.body_bytes)
        C.need(body['authority_id'] == self.config.authority_id and body['config_sha256'] == self.config.digest
               and body['broker_release_sha256'] == self.broker_release.digest
               and body['rp_release_sha256'] == self.rp_release.digest, 'PASSKEY_GRANT_INVALID')
        return require_grant_eligibility(grant, observation, at=self._time())

    def _begin(self, op, *, grant=True, allow_disabled=False):
        self._configuration()
        snapshot = op.load()
        self._time(snapshot.state.last_trusted_at)
        snapshot, observation = self._owner(op, snapshot)
        if grant:
            self._eligible(snapshot, observation, allow_disabled=allow_disabled)
        else:
            C.need(snapshot.state.grant is None and not snapshot.state.disabled, 'PASSKEY_SCOPE_UNSUPPORTED')
            C.need(observation.deployment_problem is None, 'PASSKEY_OWNER_CHANGED')
        self._releases()
        self._fresh(observation.evidence.observed_at, observation.completed_at)
        return snapshot, observation

    def _fresh(self, first, completed, expires=()):
        now = self._time()
        C.need(first <= completed <= now and now-first <= _AGE
               and now.astimezone(_KST).date() == first.astimezone(_KST).date(), 'PASSKEY_CLOCK_INVALID')
        C.need(all(now < C.instant(expiry) for expiry in expires), 'PASSKEY_EXPIRED')
        return now

    def _next_code_change(self, observation, checkpoint):
        """Bound a verified future code schedule before the final clock read.

        The owner reader has authenticated these exact bytes. This is temporal
        narrowing only, never another owner authenticity or deployment issuer.
        Any different signed future code conservatively closes this observation.
        """
        if checkpoint is None:
            return None
        deadlines = []
        for line in observation.evidence.log_bytes.splitlines():
            row = json.loads(line)
            if row['kind'] == 'code_approved' and row['data']['sha256'] != checkpoint.code_sha256:
                at = datetime.strptime(row['utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                if at > self._last:
                    deadlines.append(at)
        return min(deadlines) if deadlines else None

    def _final(self, op, first, *, grant=True, candidate_grant=None, allow_disabled=False, expires=(), packet=None):
        snapshot = op.load()
        self._releases()
        if packet is not None:
            directory, original = packet
            recheck_packet(directory, original)
        # Full historical replay and expensive packet/release reads precede the
        # final actual owner observation. It may retain a new restrictive head.
        final = op.load()
        C.need(final.head == snapshot.head, 'PASSKEY_STORE_INDETERMINATE')
        final, observation = self._owner(op, final)
        checkpoint = None
        if grant:
            checkpoint = self._eligible(final, observation, allow_disabled=allow_disabled)
        elif candidate_grant is not None:
            checkpoint = require_grant_eligibility(candidate_grant, observation, at=self._time())
        else:
            C.need(observation.deployment_problem is None, 'PASSKEY_OWNER_CHANGED')
        if packet is not None and checkpoint is not None:
            target = _body(archive_target(original))
            C.need(target['archive_request']['deployment_code_hash'] == checkpoint.code_sha256,
                   'PASSKEY_OWNER_CHANGED')
        code_deadline = self._next_code_change(observation, checkpoint)
        op.check()
        self._configuration()
        if grant:
            expires = tuple(expires)+(C.time_value(_body(final.state.grant.body_bytes)['expires_at']),)
        finish = self._fresh(first, observation.completed_at, expires)
        C.need(code_deadline is None or finish < code_deadline, 'PASSKEY_OWNER_CHANGED')
        return final, checkpoint, finish

    @staticmethod
    def _pending(state, identifier, *, proof=False):
        if proof:
            values = [p for p in state.enrollments
                      if p.proof_request is not None and p.proof_request.request_id == identifier]
        else:
            values = [p for p in state.enrollments if p.enrollment.enrollment_id == identifier]
        C.need(len(values) == 1, 'PASSKEY_TARGET_CHANGED')
        return values[0]

    @staticmethod
    def _proposal(pending):
        C.need(pending.proof is not None and pending.initial_credential is not None, 'PASSKEY_BOOTSTRAP_REQUIRED')
        return A.BootstrapProposal(enrollment=pending.enrollment, registration=pending.registration,
            registration_received_at=pending.registration_received_at, proof_request=pending.proof_request,
            proof=pending.proof, initial_credential=pending.initial_credential)

    def prepare_initial_enrollment(self):
        with AuthorityLedger.operation(self.ledger) as op:
            snapshot, observation = self._begin(op, grant=False)
            C.need(len(snapshot.state.enrollments) < 128, 'PASSKEY_RESOURCE_LIMIT')
            now = self._time()
            request = C.EnrollmentRequest(authority_id=self.config.authority_id, enrollment_id=secrets.token_hex(32),
                grant_sha256=None, registry_epoch=0, rp=C.RelyingParty(rp_id=self.config.rp_id, origin=self.config.rp_origin),
                user_handle=secrets.token_bytes(32), nonce=secrets.token_bytes(32), requested_at=now, expires_at=now+_TTL)
            self._commit(op, snapshot, 'ENROLLMENT_OPENED', {'enrollment':request.document()})
            self._final(op, observation.evidence.observed_at, grant=False, expires=(request.expires_at,))
            return request

    def submit_registration(self, enrollment_id, document):
        C.hashed(enrollment_id)
        response = C.parse_registration(document)
        received = self._time()
        with AuthorityLedger.operation(self.ledger) as op:
            snapshot, observation = self._begin(op, grant=False)
            pending = self._pending(snapshot.state, enrollment_id)
            if pending.registration is not None:
                C.need(C.registration_bytes(pending.registration) == document, 'PASSKEY_REQUEST_REUSED')
                return pending.proof_request
            verified = V.verify_registration(pending.enrollment, response, now=received)
            now = self._time()
            proof = C.ProofRequest(authority_id=self.config.authority_id, request_id=secrets.token_hex(32),
                grant_sha256=None, registry_epoch=0, target=C.ProofTarget(
                    credential_sha256=verified.credential.credential_sha256,
                    registration_evidence_sha256=verified.registration_evidence_sha256),
                nonce=secrets.token_bytes(32), requested_at=now, expires_at=now+_TTL)
            snapshot, _, _ = self._final(op, observation.evidence.observed_at, grant=False,
                                         expires=(pending.enrollment.expires_at,proof.expires_at))
            self._commit(op, snapshot, 'REGISTRATION_RECORDED', dict(enrollment_sha256=pending.enrollment.digest,
                registration=response.document(), registration_received_at=C.stamp(received),
                registration_evidence_sha256=verified.registration_evidence_sha256, proof_request=proof.document()))
            self._final(op, observation.evidence.observed_at, grant=False, expires=(proof.expires_at,))
            return proof

    def submit_initial_proof(self, request_id, document):
        C.hashed(request_id)
        response = C.parse_assertion(document)
        with AuthorityLedger.operation(self.ledger) as op:
            snapshot, observation = self._begin(op, grant=False)
            pending = self._pending(snapshot.state, request_id, proof=True)
            if pending.proof is not None:
                C.need(C.assertion_bytes(pending.proof.assertion) == document, 'PASSKEY_REQUEST_REUSED')
                return self._proposal(pending)
            registration = V.verify_registration(pending.enrollment, pending.registration,
                                                  now=pending.registration_received_at)
            received = self._time()
            verified = V.verify_assertion(C.proof_context(pending.proof_request, registration.credential),
                                          response, now=received)
            evidence = A.WebAuthnEvidence(request_sha256=pending.proof_request.digest,
                                          assertion=response, received_at=received)
            material = registration.credential
            credential = A.parse_credential(A.canonical(dict(schema=1, credential_id=C.b64(material.credential_id),
                credential_sha256=material.credential_sha256, public_key_cose=C.b64(material.public_key_cose),
                algorithm=-7, user_handle=C.b64(material.user_handle), rp_id=material.rp.rp_id, origin=material.rp.origin,
                registration_evidence_sha256=material.registration_evidence_sha256,
                proof_evidence_sha256=evidence.digest, created_at=C.stamp(pending.registration_received_at),
                backup_eligible=verified.backup_eligible, last_backed_up=verified.backed_up,
                last_counter=verified.counter, state='ACTIVE', revoked_at=None)))
            proposal = A.BootstrapProposal(enrollment=pending.enrollment, registration=pending.registration,
                registration_received_at=pending.registration_received_at, proof_request=pending.proof_request,
                proof=evidence, initial_credential=credential)
            verify_bootstrap(proposal)
            snapshot, _, _ = self._final(op, observation.evidence.observed_at, grant=False,
                                         expires=(pending.proof_request.expires_at,))
            self._commit(op, snapshot, 'INITIAL_PROOF_RECORDED', dict(enrollment_sha256=pending.enrollment.digest,
                proof=_body(A.evidence_bytes(evidence)), initial_credential=_body(A.credential_bytes(credential)),
                proposal_sha256=proposal.digest))
            self._final(op, observation.evidence.observed_at, grant=False, expires=(pending.proof_request.expires_at,))
            return proposal

    def export_grant_proposal(self, proposal_id, output):
        from .cli import write_new_file
        C.hashed(proposal_id)
        with AuthorityLedger.operation(self.ledger) as op:
            snapshot, observation = self._begin(op, grant=False)
            values = [p for p in snapshot.state.enrollments if p.proposal_sha256 == proposal_id]
            C.need(len(values) == 1, 'PASSKEY_TARGET_CHANGED')
            proposal = self._proposal(values[0])
            verify_bootstrap(proposal)
            raw = A.proposal_bytes(proposal)
            write_new_file(output, raw)
            self._final(op, observation.evidence.observed_at, grant=False)
            return ProposalReceipt(proposal_sha256=proposal.digest, byte_count=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def install_grant(self, document, proposal_id):
        C.hashed(proposal_id)
        grant = A.parse_grant(document)
        with AuthorityLedger.operation(self.ledger) as op:
            snapshot, observation = self._begin(op, grant=False)
            values = [p for p in snapshot.state.enrollments if p.proposal_sha256 == proposal_id]
            C.need(len(values) == 1, 'PASSKEY_TARGET_CHANGED')
            proposal = self._proposal(values[0])
            credential = verify_bootstrap(proposal)
            body = _body(grant.body_bytes)
            C.need(body['grant_epoch'] == 1 and body['previous_grant_sha256'] is None
                   and body['authority_id'] == self.config.authority_id
                   and body['config_sha256'] == self.config.digest
                   and body['broker_release_sha256'] == self.broker_release.digest
                   and body['rp_release_sha256'] == self.rp_release.digest
                   and body['initial_credential_sha256'] == credential.digest
                   and body['recovery_fingerprint'] == 'SHA256:'+hashlib.sha256(
                       self.owner_reader.roots.recovery_public_key_raw).hexdigest(),
                   'PASSKEY_GRANT_INVALID')
            verify_grant_document(grant, signer_public_key_raw=observation.evidence.public_key_raw)
            require_grant_eligibility(grant, observation, at=self._time())
            snapshot, _, _ = self._final(op, observation.evidence.observed_at, grant=False, candidate_grant=grant,
                                        expires=(C.time_value(body['expires_at']),))
            self._commit(op, snapshot, 'AUTHORITY_INSTALLED', dict(grant=_body(A.grant_bytes(grant)),
                config_sha256=self.config.digest, initial_credential=_body(A.credential_bytes(credential)),
                enrollment_request=proposal.enrollment.document(), registration=proposal.registration.document(),
                proof_request=proposal.proof_request.document(), proof=_body(A.evidence_bytes(proposal.proof))))
            final, _, _ = self._final(op, observation.evidence.observed_at)
            return OperationResult(status='APPLIED', request_id=None, application_id=None,
                                   head=final.head, reason='PASSKEY_APPLIED')

    def _packet(self, directory):
        from .cli import checked_directory
        inbox = Path(self.config.packet_inbox)
        checked_directory(inbox)
        C.need(isinstance(directory, Path) and directory.is_absolute() and directory.parent == inbox,
               'PASSKEY_TARGET_CHANGED')
        packet = read_packet(directory)
        C.need(directory.name == 'packet-'+packet.packet_sha256, 'PASSKEY_TARGET_CHANGED')
        return packet

    def _request_packet(self, request):
        body = _body(request.raw)
        C.need(body['kind'] == 'ARCHIVE_CONFIRM', 'PASSKEY_SCOPE_UNSUPPORTED')
        directory = Path(self.config.packet_inbox)/('packet-'+body['target']['packet_sha256'])
        packet = self._packet(directory)
        C.need(archive_target(packet) == A.canonical(body['target']), 'PASSKEY_TARGET_CHANGED')
        return directory, packet

    def open_archive_request(self, packet_directory, *, approval_expires_at):
        C.instant(approval_expires_at)
        with AuthorityLedger.operation(self.ledger) as op:
            snapshot, observation = self._begin(op)
            packet = self._packet(packet_directory)
            target = _body(archive_target(packet))
            snapshot, checkpoint, now = self._final(op, observation.evidence.observed_at,
                                                    packet=(packet_directory,packet))
            archive_expiry = C.time_value(target['archive_request']['expires_at'])
            C.need(now < approval_expires_at <= min(archive_expiry, now+timedelta(days=1)), 'PASSKEY_EXPIRED')
            request = _request(self.config, snapshot.state.grant, snapshot.state.registry_epoch,
                               'ARCHIVE_CONFIRM', target, now, approval_expires_at)
            notification = _notification(self.config.authority_id, 'REQUEST_READY', request_id=request.request_id,
                                         status='PENDING', at=now)
            self._commit(op, snapshot, 'REQUEST_OPENED', dict(request=_body(request.raw),
                notification=_body(A.notification_bytes(notification))))
            self._final(op, observation.evidence.observed_at, expires=(request.challenge_expires_at,approval_expires_at),
                        packet=(packet_directory,packet))
            return request

    def open_revoke_request(self, credential_sha256, *, reason):
        C.hashed(credential_sha256)
        C.need(reason in ('OWNER_WITHDRAWN','DEVICE_LOST','CREDENTIAL_SUSPECTED'), 'PASSKEY_SCOPE_UNSUPPORTED')
        with AuthorityLedger.operation(self.ledger) as op:
            snapshot, observation = self._begin(op)
            credential = self._credential(snapshot.state, credential_sha256)
            C.need(credential.state == 'ACTIVE', 'PASSKEY_REVOKED')
            snapshot, _, now = self._final(op, observation.evidence.observed_at)
            request = _request(self.config, snapshot.state.grant, snapshot.state.registry_epoch,
                               'REVOKE_CREDENTIAL', dict(credential_sha256=credential_sha256, reason=reason), now)
            notification = _notification(self.config.authority_id, 'REQUEST_READY', request_id=request.request_id,
                                         status='PENDING', at=now)
            self._commit(op, snapshot, 'REQUEST_OPENED', dict(request=_body(request.raw),
                notification=_body(A.notification_bytes(notification))))
            self._final(op, observation.evidence.observed_at, expires=(request.challenge_expires_at,))
            return request

    @staticmethod
    def _credential(state, digest):
        values = [c for c in state.credentials if c.credential_sha256 == digest]
        C.need(len(values) == 1, 'PASSKEY_REVOKED')
        return values[0]

    @staticmethod
    def _stored_request(state, request_id):
        values = [r for r in state.requests if r.request.request_id == request_id]
        C.need(len(values) == 1, 'PASSKEY_TARGET_CHANGED')
        return values[0]

    @staticmethod
    def _retry(state, request, response):
        if request.state != 'APPLIED':
            return False
        for event in state.events:
            if event.kind not in ('ARCHIVE_APPLIED', 'CREDENTIAL_REVOKED'):
                continue
            payload = _body(event.payload_bytes)
            evidence = A.parse_evidence(A.canonical(payload['evidence']))
            if evidence.request_sha256 == request.request.request_sha256:
                C.need(C.assertion_bytes(evidence.assertion) == C.assertion_bytes(response), 'PASSKEY_REQUEST_REUSED')
                return True
        raise C.PasskeyError('PASSKEY_STORE_INDETERMINATE')

    def submit_assertion(self, document):
        response = C.parse_assertion(document)
        with AuthorityLedger.operation(self.ledger) as op:
            self._configuration()
            initial = op.load()
            stored = self._stored_request(initial.state, response.request_id)
            # Compare the persisted raw assertion before constructing ANY new
            # received_at/evidence. Historical retry is distinct from current use.
            if self._retry(initial.state, stored, response):
                return OperationResult(status='EXACT_RETRY', request_id=response.request_id,
                    application_id=stored.application_id, head=initial.head, reason='PASSKEY_EXACT_RETRY')
            snapshot, observation = self._begin(op)
            stored = self._stored_request(snapshot.state, response.request_id)
            C.need(stored.state == 'PENDING', 'PASSKEY_REGISTRY_CHANGED')
            request = stored.request
            body = _body(request.raw)
            now = self._time()
            if (now >= request.challenge_expires_at or
                    (request.approval_expires_at is not None and now >= request.approval_expires_at)):
                kind = 'APPLICATION_RESULT' if request.kind == 'ARCHIVE_CONFIRM' else 'CREDENTIAL_RESULT'
                note = _notification(self.config.authority_id, kind, request_id=request.request_id,
                                     status='EXPIRED', at=now)
                snapshot = self._commit(op, snapshot, 'REQUEST_CLOSED', dict(
                    request_sha256=request.request_sha256, state='EXPIRED', reason='PASSKEY_EXPIRED',
                    evidence_sha256=None, notification=_body(A.notification_bytes(note))))
                final, _, _ = self._final(op, observation.evidence.observed_at)
                return OperationResult(status='EXPIRED', request_id=request.request_id, application_id=None,
                                       head=final.head, reason='PASSKEY_EXPIRED')
            C.need(body['grant_sha256'] == snapshot.state.grant.digest
                   and body['registry_epoch'] == snapshot.state.registry_epoch, 'PASSKEY_REGISTRY_CHANGED')
            credential = self._credential(snapshot.state, hashlib.sha256(response.credential_id).hexdigest())
            C.need(credential.state == 'ACTIVE', 'PASSKEY_REVOKED')
            C.need(body['kind'] in ('ARCHIVE_CONFIRM','REVOKE_CREDENTIAL'), 'PASSKEY_SCOPE_UNSUPPORTED')
            packet = self._request_packet(request) if body['kind'] == 'ARCHIVE_CONFIRM' else None
            if body['kind'] == 'REVOKE_CREDENTIAL':
                C.need(body['target']['credential_sha256'] == credential.credential_sha256, 'PASSKEY_TARGET_CHANGED')
            received = self._time()
            context = C.AssertionContext(purpose=request.kind, request_id=request.request_id,
                request_sha256=request.request_sha256, rp=credential.material().rp, challenge=request.challenge,
                user_handle=credential.material().user_handle, credential=credential.material(),
                requested_at=C.time_value(body['requested_at']), expires_at=request.challenge_expires_at)
            V.verify_assertion(context, response, now=received)
            evidence = A.WebAuthnEvidence(request_sha256=request.request_sha256, assertion=response, received_at=received)
            snapshot, checkpoint, now = self._final(op, observation.evidence.observed_at,
                expires=(request.challenge_expires_at,)+((request.approval_expires_at,) if packet else ()), packet=packet)
            application_id = None
            if packet is not None:
                target, archive = body['target'], body['target']['archive_request']
                application_id = A.record_digest('application-id', A.canonical(dict(authority_id=self.config.authority_id,
                    request_sha256=request.request_sha256, evidence_sha256=evidence.digest)))
                application = dict(schema=1, purpose='passkey_archive_manifest_confirmation',
                    application_id=application_id, authority_id=self.config.authority_id,
                    grant_sha256=snapshot.state.grant.digest, registry_epoch=snapshot.state.registry_epoch,
                    request_sha256=request.request_sha256, evidence_sha256=evidence.digest,
                    credential_sha256=credential.credential_sha256, bundle_digest=archive['bundle_digest'],
                    input_archive_digest=archive['input_archive_digest'], file_set_sha256=archive['file_set_sha256'],
                    archive_request_sha256=target['archive_request_sha256'], packet_sha256=target['packet_sha256'],
                    owner_checkpoint=A.owner_checkpoint_document(checkpoint), applied_at=C.stamp(now),
                    expires_at=C.stamp(request.approval_expires_at))
                application = _body(A.application_bytes(A.parse_application(A.canonical(application))))
                note = _notification(self.config.authority_id, 'APPLICATION_RESULT', request_id=request.request_id,
                                     application_id=application_id, status='APPLIED', at=now)
                snapshot = self._commit(op,snapshot,'ARCHIVE_APPLIED', dict(application=application,
                    evidence=_body(A.evidence_bytes(evidence)), notification=_body(A.notification_bytes(note))))
            else:
                note = _notification(self.config.authority_id, 'CREDENTIAL_RESULT', request_id=request.request_id,
                                     status='APPLIED', at=now)
                snapshot = self._commit(op,snapshot,'CREDENTIAL_REVOKED',dict(request_sha256=request.request_sha256,
                    evidence=_body(A.evidence_bytes(evidence)), credential_sha256=credential.credential_sha256,
                    reason=body['target']['reason'], new_registry_epoch=snapshot.state.registry_epoch+1,
                    notification=_body(A.notification_bytes(note))))
            final, _, _ = self._final(op, observation.evidence.observed_at,
                expires=(request.challenge_expires_at,)+( (request.approval_expires_at,) if packet else ()), packet=packet)
            return OperationResult(status='APPLIED', request_id=request.request_id, application_id=application_id,
                                   head=final.head, reason='PASSKEY_APPLIED')

    def install_disable(self, document):
        """Independent recovery-root restriction only; no replacement/reset grant."""
        disable = A.parse_disable(document)
        body = _body(disable.body_bytes)
        with AuthorityLedger.operation(self.ledger) as op:
            self._configuration()
            snapshot = op.load()
            C.need(snapshot.state.grant is not None and not snapshot.state.disabled, 'PASSKEY_BOOTSTRAP_REQUIRED')
            C.need(body['authority_id'] == self.config.authority_id
                   and body['grant_sha256'] == snapshot.state.grant.digest
                   and A.parse_head(body['expected_head']) == snapshot.head, 'PASSKEY_GRANT_INVALID')
            verify_disable_document(disable, recovery_public_key_raw=self.owner_reader.roots.recovery_public_key_raw)
            now = self._time(snapshot.state.last_trusted_at)
            C.at_time(C.time_value(body['issued_at']), C.time_value(body['expires_at']), now)
            note = _notification(self.config.authority_id, 'CREDENTIAL_RESULT', status='APPLIED', at=now)
            snapshot = self._commit(op,snapshot,'AUTHORITY_DISABLED',dict(disable=_body(A.disable_bytes(disable)),
                notification=_body(A.notification_bytes(note))))
            checked = op.load()
            C.need(checked.head == snapshot.head and checked.state.disabled, 'PASSKEY_STORE_INDETERMINATE')
            self._fresh(now, now, (C.time_value(body['expires_at']),))
            return OperationResult(status='APPLIED',request_id=None,application_id=None,head=checked.head,reason='PASSKEY_APPLIED')

    def read_current(self, application_id):
        C.hashed(application_id)
        with AuthorityLedger.operation(self.ledger) as op:
            snapshot, observation = self._begin(op, allow_disabled=True)
            applications = [a for a in snapshot.state.applications if a.application_id == application_id]
            C.need(len(applications) == 1, 'PASSKEY_TARGET_CHANGED')
            application = _body(applications[0].raw)
            requests = [r.request for r in snapshot.state.requests
                        if r.request.request_sha256 == application['request_sha256']]
            C.need(len(requests) == 1, 'PASSKEY_STORE_INDETERMINATE')
            packet = self._request_packet(requests[0])
            final, checkpoint, now = self._final(op, observation.evidence.observed_at,
                                                 allow_disabled=True, packet=packet)
            credential = self._credential(final.state, application['credential_sha256'])
            expiry = C.time_value(application['expires_at'])
            status = ('INVALIDATED' if final.state.disabled or application['grant_sha256'] != final.state.grant.digest else
                      'REVOKED' if credential.state == 'REVOKED' else 'EXPIRED' if now >= expiry else 'ACTIVE')
            return EngineCurrentObservation(authority_id=self.config.authority_id, application_id=application_id,
                grant_sha256=final.state.grant.digest, registry_epoch=final.state.registry_epoch,
                authority_head=final.head, owner_checkpoint=checkpoint, request_sha256=application['request_sha256'],
                evidence_sha256=application['evidence_sha256'], packet_sha256=application['packet_sha256'],status=status,
                observed_at=observation.evidence.observed_at, completed_at=now, expires_at=expiry)

    def inspect(self):
        self._configuration()
        snapshot = AuthorityLedger.inspect(self.ledger)
        state = snapshot.state
        return HistoricalEngineSummary(authority_id=self.config.authority_id, head=snapshot.head,
            grant_sha256=None if state.grant is None else state.grant.digest, registry_epoch=state.registry_epoch,
            credential_count=len(state.credentials), pending_request_count=sum(r.state=='PENDING' for r in state.requests),
            application_count=len(state.applications), pending_notification_count=len(self._pending_notifications(state)),
            disabled=state.disabled)

    @staticmethod
    def _pending_notifications(state):
        sent = {_body(raw)['intent_id'] for raw in state.deliveries if _body(raw)['outcome']=='SENT'}
        return tuple(n for n in state.notifications if n.intent_id not in sent)

    def pending_notifications(self):
        self._configuration()
        return self._pending_notifications(AuthorityLedger.inspect(self.ledger).state)
