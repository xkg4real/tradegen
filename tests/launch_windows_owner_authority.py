"""Current owner authority adapter over the real owner loader in signed temp homes; invented keys and data only.

One signed home is built per module (R4) and copied into each test's fresh TRADEGEN_HOME, so no test shares
state with another and F.full_home runs once. Nothing here arms, orders, signs with a real key or reads a
credential; the only key is the fixed test key and the review key of tests.launch_review_auth.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

from core.compliance import model as M, owner
from execution_control import session
from execution_control.owner_authority import CurrentOwnerAuthority, OwnerAuthorityError
from execution_control.session import PreparedSession
from execution_launch.review_auth import (ReviewAuthenticationError, ReviewVerifiers, review_body,
    verify_implementation_review, verify_source_review)
from execution_launch.strategy import ReviewReceipt
from tests import compliance_fixtures as F
from tests.launch_review_auth import (document, implementation_binding, invented_provider, invented_verifier,
    review_fixture, source_binding)
from tests.launch_strategy import START

NOW = START + timedelta(days=250, seconds=1)          # review_fixture()[4]; the log entries are stamped 2026-10-23
_TEMPLATE: list = []


@lru_cache(maxsize=1)
def keys():
    """K1 is the fixed test key (also the review key bytes(range(32))); K2 is another disposable key."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return F.test_key(), Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))


def raw(key):
    return key.public_key().public_bytes_raw()


def b64(data):
    return base64.b64encode(data).decode("ascii")


def _template() -> Path:
    """The one signed home of this module: log seq 1-5 from F.full_home (tables, the real D14 hash, majority)."""
    if not _TEMPLATE:
        keep = tempfile.TemporaryDirectory(prefix="tradegen_home_signed_")      # removed at interpreter exit
        with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
            F.full_home(home)
            shutil.copytree(home, keep.name, dirs_exist_ok=True)
        _TEMPLATE.append(keep)
    return Path(_TEMPLATE[0].name)


@contextmanager
def signed_home():
    template = _template()
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        assert owner.home().is_relative_to(home) and owner.PUBKEY_PATH.is_relative_to(home)
        shutil.copytree(template, home, dirs_exist_ok=True)
        yield home


@lru_cache(maxsize=1)
def real_code_hash():
    return owner.code_hash(owner.REPO_ROOT)


@lru_cache(maxsize=1)
def genuine_document():
    """The fixture review re-bound to the real D14 hash, signed by the review key (K1)."""
    body = review_fixture()[-1]
    return document(review_body(body["request"], body["driver_identity"], deployment_code_hash=real_code_hash(),
        audit_sha256=body["audit_sha256"], owner_fingerprint=body["owner_fingerprint"], issued_at=NOW,
        expires_at=NOW + timedelta(hours=1)))


def denied(call, code):
    try:
        call()
    except (OwnerAuthorityError, ReviewAuthenticationError, ValueError) as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("authority accepted")


def no_load():
    return patch.object(owner, "load_context", side_effect=AssertionError("latched call loaded"))


def clock_at(when):
    cell = [when]
    return cell, (lambda: cell[0])


def verifiers(provider, clock):
    return ReviewVerifiers(genuine_document(), clock=clock, authority_provider=provider,
        approved_history_provider=invented_provider, approved_history_verifier=invented_verifier)


def files_under(home):
    return {p.relative_to(home).as_posix() for p in home.rglob("*") if p.is_file()}


def log_lines():
    return owner.log_path().read_bytes().splitlines(keepends=True)


def truncate_log(keep):
    owner.log_path().write_bytes(b"".join(log_lines()[:keep]))


def test_genuine_signed_home_issues_fresh_authority_and_both_review_receipts():
    assert review_fixture()[4] == NOW
    K1, _ = keys()
    with signed_home() as home:
        before = files_under(home)
        _, clock = clock_at(NOW)
        a = CurrentOwnerAuthority(clock=clock)
        v = verifiers(a, clock)
        receipt = v.source(source_binding())
        assert type(receipt) is ReviewReceipt
        assert receipt.reviewer_id == "owner:" + hashlib.sha256(raw(K1)).hexdigest()
        assert receipt.reviewed_at == NOW
        driver = review_fixture()[6]
        assert v.implementation(implementation_binding(), driver).callback is driver.callback
        x, y = a(NOW), a(NOW)
        assert x is not y and x.context is not y.context
        for authority in (x, y):
            assert M.is_sealed(authority.context) and authority.context.code_signed is True
            assert authority.context.code_hash == real_code_hash()
            assert authority.public_key_raw == raw(K1)
            assert authority.observed_at == NOW
            assert authority.context.session == M.SessionState()
            assert authority.context.equity_krw == 1.0
            assert authority.context.owner.ok and authority.context.owner.head[0] == 5
        new = files_under(home) - before
        assert new and all(name.startswith("compliance/snapshots/") for name in new), new


def test_stale_late_or_rolled_back_authority_refuses_and_latches():
    with signed_home():
        cell, clock = clock_at(NOW)
        a = CurrentOwnerAuthority(clock=clock)
        x = a(NOW)
        denied(lambda: verify_source_review(source_binding(), genuine_document(), authority=x,
                                            now=NOW + timedelta(seconds=31)), "REVIEW_OWNER_AUTHORITY_STALE")
        cell[0] = NOW + timedelta(seconds=30)
        assert a(NOW).observed_at == NOW                    # the observation bound is inclusive
        cell[0] = NOW + timedelta(seconds=31)
        denied(lambda: a(NOW), "OWNER_AUTHORITY_OBSERVATION_LATE")
        cell[0] = NOW + timedelta(seconds=32)
        with no_load():                                     # latched: this call would otherwise pass
            denied(lambda: a(NOW + timedelta(seconds=32)), "OWNER_AUTHORITY_OBSERVATION_LATE")
        _, clock = clock_at(NOW + timedelta(seconds=10))
        b = CurrentOwnerAuthority(clock=clock)
        b(NOW + timedelta(seconds=10))
        with no_load():
            denied(lambda: b(NOW + timedelta(seconds=5)), "OWNER_AUTHORITY_CLOCK_ROLLBACK")
        cell, clock = clock_at(NOW - timedelta(seconds=1))
        c = CurrentOwnerAuthority(clock=clock)
        denied(lambda: c(NOW), "OWNER_AUTHORITY_CLOCK_ROLLBACK")
        cell[0] = NOW
        assert c(NOW).observed_at == NOW                    # a refusal before the pin does not latch


def test_rotated_or_replaced_owner_key_refuses():
    K1, K2 = keys()
    with signed_home():
        _, clock = clock_at(NOW)
        a = CurrentOwnerAuthority(clock=clock)
        a(NOW)
        F.sign(K1, "key_rotated", {"old_pubkey_b64": b64(raw(K1)), "new_pubkey_b64": b64(raw(K2))})
        F.write_pubkey(owner.PUBKEY_PATH, K2)
        assert owner.load_context(NOW, M.Positions(equity_krw=1.0)).owner.ok    # the loader's walk verifies
        denied(lambda: a(NOW), "OWNER_AUTHORITY_KEY_CHANGED")
        d = CurrentOwnerAuthority(clock=clock)
        v = verifiers(d, clock)
        denied(lambda: v.source(source_binding()), "REVIEW_CURRENT_KEY_MISMATCH")   # the review names fp(K1)
        F.write_pubkey(owner.PUBKEY_PATH, K1)                                        # rolled back, no log entry
        denied(lambda: v.source(source_binding()), "OWNER_AUTHORITY_OWNER_STATE_BROKEN")
    with signed_home():
        e = CurrentOwnerAuthority(clock=lambda: NOW)
        with patch.object(owner, "read_pubkey", side_effect=[raw(K1), raw(K2)]):   # loader K1, adapter K2
            denied(lambda: e(NOW), "OWNER_AUTHORITY_KEY_CHANGED")
        with patch.object(owner, "read_pubkey", side_effect=[raw(K1), PermissionError("invented")]):
            denied(lambda: e(NOW), "OWNER_AUTHORITY_KEY_UNREADABLE")
        assert e(NOW).public_key_raw == raw(K1)             # no pin yet, so neither refusal latched


def test_owner_log_counts_only_as_a_verified_extension():
    K1, _ = keys()
    _, clock = clock_at(NOW)
    with signed_home():
        a = CurrentOwnerAuthority(clock=clock)
        assert a(NOW).context.owner.head[0] == 5
        F.sign(K1, "session_armed", {"session_id": "Linvented-session"})
        grown = a(NOW)
        assert grown.context.owner.head[0] == 6 and grown.context.session == M.SessionState()
        owner.append_system_entry("system_halt", {"floor_krw": 1.0}, NOW)
        denied(lambda: verifiers(a, clock).source(source_binding()), "REVIEW_OWNER_APPROVAL_REQUIRED")
        truncate_log(6)                                     # the halt removed
        assert owner.load_context(NOW, M.Positions(equity_krw=1.0)).owner.ok    # its anchor is still (5, h5)
        denied(lambda: a(NOW), "OWNER_AUTHORITY_LOG_REWRITTEN")
    with signed_home():
        b = CurrentOwnerAuthority(clock=clock)
        b(NOW)
        F.sign(K1, "session_armed", {"session_id": "Linvented-session"})
        assert b(NOW).context.owner.head[0] == 6
        truncate_log(5)
        for _ in range(2):
            owner.append_system_entry("system_disarm", {"session_id": "Lother", "reason": "invented rewrite"}, NOW)
        denied(lambda: b(NOW), "OWNER_AUTHORITY_LOG_REWRITTEN")      # longer, but the anchor (6, h6) fails
        c = CurrentOwnerAuthority(clock=clock)
        assert c(NOW).context.owner.head[0] == 7
        _, h8 = F.sign(K1, "session_armed", {"session_id": "Linvented-session"})
        real = log_lines()
        forged = F.signed_entry(None, 9, h8, "system_disarm", {"session_id": "Lx", "reason": "invented"})
        with patch.object(owner, "_log_lines", side_effect=[real, real + [forged]]):
            denied(lambda: c(NOW), "OWNER_AUTHORITY_LOG_CHANGED_DURING_OBSERVATION")
        e = CurrentOwnerAuthority(clock=clock)
        assert e(NOW).context.owner.head[0] == 8
        F.sign(K1, "session_armed", {"session_id": "Linvented-session"})
        with patch.object(owner, "_log_lines", side_effect=[log_lines(), PermissionError("invented")]):
            denied(lambda: e(NOW), "OWNER_AUTHORITY_LOG_UNREADABLE")


def test_lost_or_changed_code_approval_refuses_and_latches():
    K1, _ = keys()
    with signed_home():
        a, b = CurrentOwnerAuthority(clock=lambda: NOW), CurrentOwnerAuthority(clock=lambda: NOW)
        assert a(NOW).context.code_hash == b(NOW).context.code_hash == real_code_hash()
        F.other_code(K1)
        other = json.loads(log_lines()[-1])["data"]["sha256"]
        assert other != real_code_hash()
        denied(lambda: a(NOW), "OWNER_AUTHORITY_CODE_NOT_SIGNED")
        with patch.object(owner, "code_hash", lambda root: other):          # signed, but another closure
            denied(lambda: b(NOW), "OWNER_AUTHORITY_CODE_CHANGED")
        with no_load():
            denied(lambda: b(NOW), "OWNER_AUTHORITY_CODE_CHANGED")


def test_forged_or_copied_review_and_prepared_objects_refuse_under_current_authority():
    _, K2 = keys()
    registry = dict(session._PREPARED)
    with signed_home():
        x = CurrentOwnerAuthority(clock=lambda: NOW)(NOW)
        doc = genuine_document()

        def src(**changes):
            return verify_source_review(**(dict(binding=source_binding(), document=doc, authority=x, now=NOW)
                                           | changes))
        assert src().reviewer_id == json.loads(doc)["body"]["reviewer_id"]
        denied(lambda: src(authority=replace(x, context=replace(x.context))), "REVIEW_OWNER_CONTEXT_INVALID")
        denied(lambda: src(document=document(json.loads(doc)["body"], key=K2)), "REVIEW_SIGNATURE_UNVERIFIED")
        denied(lambda: src(binding=replace(source_binding(), evidence_digest="f" * 64)),
               "REVIEW_SOURCE_BINDING_MISMATCH")
        denied(lambda: verify_implementation_review(replace(implementation_binding(), evidence_digest="f" * 64),
                   review_fixture()[6], doc, authority=x, now=NOW, approved_history_provider=invented_provider,
                   approved_history_verifier=invented_verifier), "REVIEW_IMPLEMENTATION_BINDING_MISMATCH")
        denied(lambda: src(document=document()), "REVIEW_DEPLOYMENT_CODE_MISMATCH")   # 'c' * 64 closure
        forged = PreparedSession(session_id="Lforged-" + "0" * 64, plan_hash="0" * 64, input_digest="0" * 64,
            policy_digest="0" * 64, rules_digest="0" * 64, code_hash=x.context.code_hash,
            state_hash=x.context.active.state_hash, seed_hex="1" * 64, selection_seed_hex="2" * 64, venue="upbit",
            symbol="BTC", account_scope="invented-account", market="spot", quote_currency="KRW", stake_krw="1000",
            prepared_at=NOW, expires_at=NOW + timedelta(minutes=30), record_digest="0" * 64)
        for prepared in (forged, replace(forged)):
            denied(lambda prepared=prepared: session.verify_session(prepared, session_id=prepared.session_id,
                       policy=None, instrument_rules=None, ctx=x.context, now=NOW, order=None, events=()),
                   "session preparation not issued in this process")
        assert dict(session._PREPARED) == registry


def test_unsigned_first_observation_does_not_pin_and_retry_succeeds():
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        a = CurrentOwnerAuthority(clock=lambda: NOW)
        denied(lambda: a(NOW), "OWNER_AUTHORITY_OWNER_STATE_BROKEN")      # no owner key yet
        shutil.copytree(_template(), home, dirs_exist_ok=True)
        assert a(NOW).context.owner.ok


def test_constructor_time_and_reentrant_calls_refuse():
    denied(lambda: CurrentOwnerAuthority(clock=None), "OWNER_AUTHORITY_CLOCK_REQUIRED")
    with signed_home():
        a = CurrentOwnerAuthority(clock=lambda: NOW)
        with no_load():
            for bad in (datetime(2030, 9, 8), "2030-09-08T00:00:01+00:00", None):
                denied(lambda bad=bad: a(bad), "OWNER_AUTHORITY_TIME_INVALID")
        denied(lambda: CurrentOwnerAuthority(clock=lambda: 1 // 0)(NOW), "OWNER_AUTHORITY_UNAVAILABLE")
        inner, made = [], []

        def reentrant():
            try:
                made[0](NOW)
            except OwnerAuthorityError as exc:
                inner.append(str(exc))
            return NOW
        made.append(CurrentOwnerAuthority(clock=reentrant))
        assert made[0](NOW).observed_at == NOW
        assert made[0](NOW).observed_at == NOW              # the inner refusal did not latch
        assert inner == ["OWNER_AUTHORITY_CONCURRENT_REFUSED"] * 2
