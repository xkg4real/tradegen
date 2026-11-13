"""Actual temporary signed owner-prefix checks; no caller Context proves trust."""
from datetime import timedelta
import base64
from unittest.mock import patch

from core.compliance import owner, model
from execution_control.owner_authority import CurrentOwnerAuthority, OwnerAuthorityError
from tests import compliance_fixtures as CF
from tests.launch_bundle_auth import signed_owner, NOW


def checkpoint(authority):
    return dict(key_fingerprint=authority.context.owner.fingerprint,
                code_hash=authority.context.code_hash, owner_head=authority.context.owner.head)


def denied(call, code):
    try:
        call()
    except OwnerAuthorityError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('invalid recovery checkpoint accepted')


def observe(provider, expected, now=NOW):
    return provider.observe_checkpoint(now, **expected)


def test_actual_initial_and_longer_signed_prefix_are_verified_by_new_provider():
    with signed_owner() as e:
        clock = lambda:NOW
        initial = CurrentOwnerAuthority(clock=clock)(NOW)
        CF.sign(e.key, 'age_of_majority', {'birth_date':'2000-01-01', 'evidence':'temporary checkpoint test'})
        result = observe(CurrentOwnerAuthority(clock=clock), checkpoint(initial))
        assert model.is_sealed(result.context) and result.context.code_signed
        assert result.context.owner.head[0] > initial.context.owner.head[0]
        assert result.context.ctx_hash == model.context_hash(result.context)
        assert result.observed_at == NOW and not result.context.active.valid
        assert result.public_key_raw == e.key.public_key().public_bytes_raw()


def test_checkpoint_shape_is_rejected_before_owner_io():
    with signed_owner():
        clock = lambda:NOW
        expected = checkpoint(CurrentOwnerAuthority(clock=clock)(NOW))
        for changes in ({'key_fingerprint':'x'}, {'code_hash':'A'*64}, {'owner_head':(True,'a'*64)},
                        {'owner_head':(0,'')}, {'owner_head':[1,'a'*64]}):
            provider = CurrentOwnerAuthority(clock=clock)
            with patch.object(owner, 'load_context', side_effect=AssertionError('invalid shape reached owner')):
                denied(lambda:observe(provider, expected | changes), 'OWNER_AUTHORITY_CHECKPOINT_INVALID')


def test_wrong_expected_key_is_restrictive_and_latches_current_instance():
    with signed_owner():
        clock = lambda:NOW
        expected = checkpoint(CurrentOwnerAuthority(clock=clock)(NOW))
        provider = CurrentOwnerAuthority(clock=clock)
        denied(lambda:observe(provider, expected | {'key_fingerprint':'SHA256:'+'0'*64}),
               'OWNER_AUTHORITY_KEY_CHANGED')
        with patch.object(owner, 'load_context', side_effect=AssertionError('refused instance reloaded')):
            denied(lambda:observe(provider, expected), 'OWNER_AUTHORITY_KEY_CHANGED')


def test_wrong_expected_code_is_restrictive_without_changing_current_code():
    with signed_owner():
        clock = lambda:NOW
        expected = checkpoint(CurrentOwnerAuthority(clock=clock)(NOW))
        provider = CurrentOwnerAuthority(clock=clock)
        denied(lambda:observe(provider, expected | {'code_hash':'0'*64}), 'OWNER_AUTHORITY_CODE_CHANGED')
        with patch.object(owner, 'load_context', side_effect=AssertionError('refused instance reloaded')):
            denied(lambda:observe(provider, expected), 'OWNER_AUTHORITY_CODE_CHANGED')


def test_restart_cannot_forget_actually_verified_later_signed_prefix():
    with signed_owner() as e:
        clock = lambda:NOW
        first = owner.log_path().read_bytes()
        CF.sign(e.key, 'age_of_majority', {'birth_date':'2000-01-01', 'evidence':'prefix to retain'})
        expected = checkpoint(CurrentOwnerAuthority(clock=clock)(NOW))
        owner.log_path().write_bytes(first)
        denied(lambda:observe(CurrentOwnerAuthority(clock=clock), expected), 'OWNER_AUTHORITY_LOG_REWRITTEN')


def test_same_length_genuinely_signed_fork_is_not_the_required_prefix():
    with signed_owner() as e:
        clock = lambda:NOW
        first = owner.log_path().read_bytes()
        CF.sign(e.key, 'age_of_majority', {'birth_date':'2000-01-01', 'evidence':'original branch'})
        expected = checkpoint(CurrentOwnerAuthority(clock=clock)(NOW))
        owner.log_path().write_bytes(first)
        CF.sign(e.key, 'age_of_majority', {'birth_date':'2000-01-01', 'evidence':'different branch'})
        denied(lambda:observe(CurrentOwnerAuthority(clock=clock), expected), 'OWNER_AUTHORITY_LOG_REWRITTEN')


def test_actual_key_rotation_cannot_resume_original_key_checkpoint():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    with signed_owner() as e:
        clock = lambda:NOW
        expected = checkpoint(CurrentOwnerAuthority(clock=clock)(NOW))
        other = Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
        encode = lambda key:base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')
        CF.sign(e.key, 'key_rotated', {'old_pubkey_b64':encode(e.key), 'new_pubkey_b64':encode(other)})
        CF.write_pubkey(owner.PUBKEY_PATH, other)
        denied(lambda:observe(CurrentOwnerAuthority(clock=clock), expected), 'OWNER_AUTHORITY_KEY_CHANGED')


def test_original_actual_completion_then_backwards_final_clock_refuses():
    with signed_owner():
        expected = checkpoint(CurrentOwnerAuthority(clock=lambda:NOW)(NOW))
        values = iter((NOW+timedelta(seconds=5), NOW+timedelta(seconds=1)))
        provider = CurrentOwnerAuthority(clock=lambda:next(values))
        denied(lambda:observe(provider, expected), 'OWNER_AUTHORITY_CLOCK_ROLLBACK')
        with patch.object(owner, 'load_context', side_effect=AssertionError('rollback latch was cleared')):
            denied(lambda:observe(provider, expected), 'OWNER_AUTHORITY_CLOCK_ROLLBACK')


def test_checkpoint_full_verification_must_fit_original_thirty_seconds():
    with signed_owner():
        expected = checkpoint(CurrentOwnerAuthority(clock=lambda:NOW)(NOW))
        values = iter((NOW, NOW+timedelta(seconds=31)))
        denied(lambda:observe(CurrentOwnerAuthority(clock=lambda:next(values)), expected),
               'OWNER_AUTHORITY_OBSERVATION_LATE')


def test_actual_final_day_change_within_thirty_seconds_is_distinct_refusal():
    with signed_owner():
        now = NOW.replace(hour=14, minute=59, second=59)
        expected = checkpoint(CurrentOwnerAuthority(clock=lambda:now)(now))
        values = iter((now, now+timedelta(seconds=2)))
        denied(lambda:observe(CurrentOwnerAuthority(clock=lambda:next(values)), expected, now),
               'OWNER_AUTHORITY_DAY_CHANGED')


def test_optional_checkpoint_keeps_original_observed_at_and_retains_actual_completion():
    with signed_owner():
        expected = checkpoint(CurrentOwnerAuthority(clock=lambda:NOW)(NOW))
        values = iter((NOW+timedelta(seconds=2), NOW+timedelta(seconds=5)))
        provider = CurrentOwnerAuthority(clock=lambda:next(values))
        result = observe(provider, expected)
        assert result.observed_at == NOW and provider._last == NOW+timedelta(seconds=5)
        denied(lambda:provider(NOW+timedelta(seconds=4)), 'OWNER_AUTHORITY_CLOCK_ROLLBACK')


def test_ordinary_call_still_uses_its_existing_single_clock_observation():
    with signed_owner():
        calls = []
        def clock():
            calls.append(True)
            return NOW+timedelta(seconds=5)
        provider = CurrentOwnerAuthority(clock=clock)
        actual = provider(NOW)
        assert calls == [True] and provider._last == NOW
        assert actual.observed_at == NOW and model.is_sealed(actual.context) and actual.context.code_signed
