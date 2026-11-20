"""Passkey archive-authority signing commands, moved out of tools/signer/sign.py.

Spec 6.4 keeps the owner's D14 signer to the standard library and cryptography, never the repo. These commands
need the broker package (and fido2 through it), so they live here. This is not the D14 signer: it imports broker
code and a second copy of the signer, which the owner's off-PC hash of sign.py does not cover. D14 lets only the
owner-kept signer unlock the owner or recovery key, so main() always refuses; the handlers are kept only for
tests/launch_passkey_bootstrap.py until the owner decides how passkey grants are signed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import secrets
import sys

from tools.signer.sign import (CODE_ALPHABET, _bundle_code_approval_at, _bundle_read, _bundle_write_new,
                               _exclusive, _home, _key_path, _read_typed, _review_path, _typed_ok,
                               _unlock, fingerprint, sha256_hex)


def _cmd_archive_authority_grant(args):
    from tools.approval_broker import contract as C
    try:
        return _archive_authority_grant(args)
    except C.PasskeyError:
        raise
    except (ValueError,RuntimeError,OSError,ImportError,TypeError,AttributeError,OverflowError):
        raise C.PasskeyError('PASSKEY_GRANT_SIGNING_REFUSED') from None


def _passkey_output(path, installation):
    from tools.approval_broker import bootstrap as B, contract as C
    target = _review_path(path)
    forbidden = (installation.locations.app_repo,installation.locations.app_environment,
        installation.locations.compliance_root,Path(B.__file__).resolve().parents[2],
        installation.broker_release_root,installation.rp_release_root,installation.ledger_roots.primary,
        installation.ledger_roots.backup,installation.ledger_roots.head,
        Path(installation.config.packet_inbox),*installation.dependency_roots)
    C.need(target.suffix.lower()=='.json' and not target.exists() and target.parent.is_dir()
           and not any(target.is_relative_to(root) for root in forbidden),'PASSKEY_OUTPUT_REFUSED')
    return target


def _archive_authority_grant(args):
    """Independent archive-only bootstrap grant; no owner-log or registry write.

    The separately installed reviewed package must be importable through the
    isolated interpreter. No repo/packet path is ever inserted into sys.path.
    Existing main() terminal/isolation/unlock/typed-confirmation gates remain.
    """
    from tools.approval_broker import authority_contract as A, bootstrap as B, contract as C
    from tools.approval_broker.cli import load_installation
    from tools.approval_broker.owner_view import OwnerReader
    from tools.approval_broker.release import verify_release
    installation = load_installation(Path(args.config))
    repo = installation.locations.app_repo
    C.need(installation.locations.compliance_root == _home(), 'PASSKEY_OWNER_LOCATION_INVALID')
    if Path(__file__).resolve().is_relative_to(repo) or Path(B.__file__).resolve().is_relative_to(repo):
        raise C.PasskeyError('PASSKEY_INDEPENDENT_SIGNER_REQUIRED')
    signer_path = _review_path(__file__)
    signer_raw,signer_identity = _bundle_read(signer_path,2*1024*1024)
    C.need(_bundle_read(installation.broker_release_root/'tools'/'approval_broker'/'owner_sign.py',2*1024*1024)[0]==signer_raw,
           'PASSKEY_RELEASE_CHANGED')
    clock = lambda: datetime.now(timezone.utc)
    reader = OwnerReader(locations=installation.locations,roots=installation.trust_roots,clock=clock)
    proposal_path = _review_path(args.proposal)
    raw,identity = _bundle_read(proposal_path,2*1024*1024)
    proposal = A.parse_proposal(raw)
    B.verify_bootstrap(proposal)
    first = reader.observe(retained=None)
    C.need(first.deployment_problem is None,'PASSKEY_DEPLOYMENT_REFUSED')
    output = _passkey_output(args.output,installation)
    C.need(output != proposal_path,'PASSKEY_OUTPUT_REFUSED')
    expiry = C.time_value(args.expires_at)
    verify_release(installation.broker_release_root,installation.broker_release,
                   dependency_roots=installation.dependency_roots)
    verify_release(installation.rp_release_root,installation.rp_release,dependency_roots=())
    confirmed = reader.observe(retained=first.evidence)
    C.need(confirmed.deployment_problem is None,'PASSKEY_DEPLOYMENT_REFUSED')
    checkpoint = A.OwnerCheckpoint(fingerprint=fingerprint(confirmed.evidence.public_key_raw),
        code_sha256=confirmed.deployment_code_sha256,owner_head=confirmed.evidence.head,
        observed_at=confirmed.evidence.observed_at)
    issued = clock()
    body = B.build_grant_body(proposal,config=installation.config,
        broker_release=installation.broker_release,rp_release=installation.rp_release,owner=checkpoint,
        recovery_fingerprint=fingerprint(installation.trust_roots.recovery_public_key_raw),
        issued_at=issued,expires_at=expiry)
    rows = tuple(json.loads(line) for line in confirmed.evidence.log_bytes.split(b'\n') if line)
    approvals = tuple((row['utc'],row['data']['sha256']) for row in rows if row['kind']=='code_approved')
    before_confirmation = clock()
    C.need(confirmed.completed_at <= issued <= before_confirmation < expiry
           and before_confirmation-confirmed.evidence.observed_at <= timedelta(seconds=30), 'PASSKEY_EXPIRED')
    C.need(_bundle_code_approval_at(approvals,before_confirmation)==confirmed.deployment_code_sha256,
           'PASSKEY_DEPLOYMENT_CHANGED')
    print('Archive-manifest identity authority only. No trading, source approval or current operational channel.')
    print(json.dumps(json.loads(body),indent=2,sort_keys=True,ensure_ascii=True))
    print('RP:',installation.config.rp_origin,'RP ID:',installation.config.rp_id)
    print('Credential public-key SHA256:',sha256_hex(proposal.initial_credential.public_key_cose))
    code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    typed,stamps = _read_typed(f'Type this code to grant archive authority (do not paste): {code}\n> ')
    C.need(_typed_ok(code,typed,stamps),'PASSKEY_CONFIRMATION_REFUSED')
    key = _unlock(_key_path(args))
    with _exclusive(installation.locations.compliance_root/'owner.jsonl'):
        current = load_installation(Path(args.config))
        C.need(current == installation,'PASSKEY_INSTALLATION_CHANGED')
        C.need(_bundle_read(signer_path,2*1024*1024)==(signer_raw,signer_identity),'PASSKEY_RELEASE_CHANGED')
        C.need(_bundle_read(proposal_path,2*1024*1024)==(raw,identity),'PASSKEY_TARGET_CHANGED')
        B.verify_bootstrap(proposal)
        verify_release(installation.broker_release_root,installation.broker_release,
                       dependency_roots=installation.dependency_roots)
        verify_release(installation.rp_release_root,installation.rp_release,dependency_roots=())
        latest = reader.observe(retained=confirmed.evidence)
        C.need(latest.deployment_problem is None,'PASSKEY_DEPLOYMENT_REFUSED')
        public = latest.evidence.public_key_raw
        C.need(key.public_key().public_bytes_raw()==public,'PASSKEY_OWNER_KEY_CHANGED')
        C.need(latest.evidence.head==confirmed.evidence.head and public==confirmed.evidence.public_key_raw
               and latest.deployment_code_sha256==confirmed.deployment_code_sha256,'PASSKEY_OWNER_CHANGED')
        rows = tuple(json.loads(line) for line in latest.evidence.log_bytes.split(b'\n') if line)
        approvals = tuple((row['utc'],row['data']['sha256']) for row in rows if row['kind']=='code_approved')
        signing = A.grant_signing_bytes(body)
        now = clock()
        C.need(issued <= latest.completed_at <= now < min(expiry,issued+timedelta(minutes=5))
               and now-latest.evidence.observed_at <= timedelta(seconds=30),
               'PASSKEY_EXPIRED')
        C.need(_bundle_code_approval_at(approvals,now)==latest.deployment_code_sha256,'PASSKEY_DEPLOYMENT_CHANGED')
        document = A.GrantDocument(body_bytes=body,signature=key.sign(signing))
        B.verify_grant_document(document,signer_public_key_raw=public)
        encoded = A.grant_bytes(document)
        finish = clock()
        C.need(now <= finish < min(expiry,issued+timedelta(minutes=5))
               and finish-latest.evidence.observed_at <= timedelta(seconds=30),
               'PASSKEY_EXPIRED')
        C.need(_bundle_code_approval_at(approvals,finish)==latest.deployment_code_sha256,'PASSKEY_DEPLOYMENT_CHANGED')
        _bundle_write_new(output,encoded)
    print('Signed archive authority grant; operational channel is not implemented; trading remains disabled.')
    return 0


def _cmd_archive_authority_disable(args):
    from tools.approval_broker import contract as C
    try:
        return _archive_authority_disable(args)
    except C.PasskeyError:
        raise
    except (ValueError,RuntimeError,OSError,ImportError,TypeError,AttributeError,OverflowError):
        raise C.PasskeyError('PASSKEY_DISABLE_SIGNING_REFUSED') from None


def _archive_authority_disable(args):
    """Sign a restrictive exact-head document; installation is a separate action."""
    from tools.approval_broker import authority_contract as A, bootstrap as B, contract as C
    from tools.approval_broker.cli import load_installation
    from tools.approval_broker.ledger import AuthorityLedger
    from tools.approval_broker.release import verify_release
    C.need(type(args.key) is str and bool(args.key),'PASSKEY_RECOVERY_KEY_REQUIRED')
    C.need(args.reason in ('DEVICE_LOST','AUTHORITY_COMPROMISED'),'PASSKEY_FORMAT_INVALID')
    installation = load_installation(Path(args.config))
    repo = installation.locations.app_repo
    C.need(not Path(__file__).resolve().is_relative_to(repo) and not Path(B.__file__).resolve().is_relative_to(repo),
           'PASSKEY_INDEPENDENT_SIGNER_REQUIRED')
    signer_path = _review_path(__file__)
    signer_raw,signer_identity = _bundle_read(signer_path,2*1024*1024)
    C.need(_bundle_read(installation.broker_release_root/'tools'/'approval_broker'/'owner_sign.py',2*1024*1024)[0]==signer_raw,
           'PASSKEY_RELEASE_CHANGED')
    output = _passkey_output(args.output,installation)
    ledger = AuthorityLedger(roots=installation.ledger_roots,installation=installation.ledger_installation)
    snapshot = ledger.inspect()
    C.need(snapshot.state.grant is not None and not snapshot.state.disabled,'PASSKEY_BOOTSTRAP_REQUIRED')
    recovery = installation.trust_roots.recovery_public_key_raw
    C.need(snapshot.state.grant.body['recovery_fingerprint']==fingerprint(recovery),'PASSKEY_RECOVERY_KEY_REQUIRED')
    verify_release(installation.broker_release_root,installation.broker_release,
                   dependency_roots=installation.dependency_roots)
    clock = lambda: datetime.now(timezone.utc)
    issued,expiry = clock(),C.time_value(args.expires_at)
    body = A.canonical(dict(schema=1,purpose='passkey_archive_authority_disable',
        authority_id=installation.config.authority_id,grant_sha256=snapshot.state.grant.digest,
        expected_head=A.head_document(snapshot.head),reason=args.reason,
        issued_at=C.stamp(issued),expires_at=C.stamp(expiry)))
    signing = A.disable_signing_bytes(body)  # Exact reason and <=300-second TTL.
    print('Restrict this exact archive authority only; no reset, replacement grant or trading authority.')
    print(json.dumps(json.loads(body),indent=2,sort_keys=True,ensure_ascii=True))
    print('Required recovery-key fingerprint:',fingerprint(recovery))
    code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    typed,stamps = _read_typed(f'Type this code to sign the restriction (do not paste): {code}\n> ')
    C.need(_typed_ok(code,typed,stamps),'PASSKEY_CONFIRMATION_REFUSED')
    key = _unlock(_key_path(args))
    C.need(key.public_key().public_bytes_raw()==recovery,'PASSKEY_RECOVERY_KEY_REQUIRED')
    with ledger.operation() as operation:
        current = load_installation(Path(args.config))
        C.need(current==installation,'PASSKEY_INSTALLATION_CHANGED')
        C.need(_bundle_read(signer_path,2*1024*1024)==(signer_raw,signer_identity),'PASSKEY_RELEASE_CHANGED')
        verify_release(installation.broker_release_root,installation.broker_release,
                       dependency_roots=installation.dependency_roots)
        latest = operation.load()
        C.need(latest.head==snapshot.head and latest.context_sha256==snapshot.context_sha256
               and latest.state.grant is not None and latest.state.grant.digest==snapshot.state.grant.digest
               and not latest.state.disabled,'PASSKEY_TARGET_CHANGED')
        operation.check()
        now = clock()
        C.need(issued <= now < expiry,'PASSKEY_EXPIRED')
        document = A.DisableDocument(body_bytes=body,signature=key.sign(signing))
        B.verify_disable_document(document,recovery_public_key_raw=recovery)
        encoded = A.disable_bytes(document)
        finish = clock()
        C.need(now <= finish < expiry,'PASSKEY_EXPIRED')
        _bundle_write_new(output,encoded)
    print('Signed recovery restriction only; apply this document separately; ledger is unchanged.')
    return 0


def main(argv=None) -> int:
    """Always refuses (D14: only the owner-kept signer unlocks a key). The handlers above stay for the tests."""
    print("owner_sign.py refused: not the owner-kept signer (spec 6.4, D14); no owner or recovery key is unlocked "
          "here until the owner decides how passkey grants are signed", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
