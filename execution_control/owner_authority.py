"""Current owner authority for detached review verification; grants no session or order capability.

Each call runs the trusted owner.load_context and reads the current owner_pubkey.pem. This module has no
signer, network, environment read or file write of its own. The actual owner loader may snapshot a valid
state and durably anchor verified research restrictions. Review contexts use a fixed placeholder Positions
(P19, as execution/poll.py E24) and no session
id, so they are never gate, odds or session evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import threading

from core.compliance import model as compliance, owner

MAX_AUTHORITY_AGE_SECONDS = 30
_REVIEW_POSITIONS = compliance.Positions(equity_krw=1.0)         # review-only; never account evidence


class OwnerAuthorityError(ValueError):
    """Fixed diagnostics only: no path, key, fingerprint, log head or exception text."""


def _need(ok, code):
    if not ok:
        raise OwnerAuthorityError(code)


def _aware(value):
    return type(value) is datetime and value.utcoffset() is not None


@dataclass(frozen=True, kw_only=True)
class ReviewAuthority:
    """From the trusted owner loader, refreshed on every callback invocation.

    observed_at is the loader's observation time, never a relabelled cached state.
    Public-key bytes must belong to the current PEM verified by that loader.
    """
    context: compliance.Context
    public_key_raw: bytes
    observed_at: datetime


class CurrentOwnerAuthority:
    """authority_provider(now) for ReviewVerifiers. Pass the same trusted clock to both.

    The first accepted observation pins (key fingerprint, D14 code hash, owner-log head). Any later
    refusal is permanent for this instance: recovery is a new instance, new ReviewVerifiers and fresh
    preparation. A rotated key, changed code or rewritten log never resumes silently.
    """

    def __init__(self, *, clock):
        _need(callable(clock), "OWNER_AUTHORITY_CLOCK_REQUIRED")
        self._clock = clock
        self._lock = threading.Lock()
        self._pinned = None          # (fingerprint, code_hash, head); head advances only on verified growth
        self._last = None            # latest accepted now
        self._latched = ""

    def __call__(self, now) -> ReviewAuthority:
        _need(_aware(now), "OWNER_AUTHORITY_TIME_INVALID")
        _need(self._lock.acquire(blocking=False), "OWNER_AUTHORITY_CONCURRENT_REFUSED")
        try:
            return self._observe(now)
        except Exception as exc:
            code = str(exc) if type(exc) is OwnerAuthorityError else "OWNER_AUTHORITY_UNAVAILABLE"
            if self._pinned is not None and not self._latched:
                self._latched = code
            raise OwnerAuthorityError(code) from None
        finally:
            self._lock.release()

    def observe_checkpoint(self, now, *, key_fingerprint, code_hash, owner_head) -> ReviewAuthority:
        """Fresh actual observation restricted by a durable historical checkpoint.

        The checkpoint is not authority: its key/code must match the current
        loader and its head must be a prefix of the whole independently verified
        signed log. Only actual observations update this provider's normal pins.
        Caller retains trusted-time continuity from its own durable attempt.
        """
        _need(_aware(now), "OWNER_AUTHORITY_TIME_INVALID")
        def hexadecimal(value):
            return (type(value) is str and len(value) == 64
                    and all(char in "0123456789abcdef" for char in value))
        _need(type(key_fingerprint) is str and key_fingerprint.startswith("SHA256:")
              and hexadecimal(key_fingerprint[7:]) and hexadecimal(code_hash)
              and type(owner_head) is tuple and len(owner_head) == 2
              and type(owner_head[0]) is int and 1 <= owner_head[0] < 2**63
              and hexadecimal(owner_head[1]), "OWNER_AUTHORITY_CHECKPOINT_INVALID")
        _need(self._lock.acquire(blocking=False), "OWNER_AUTHORITY_CONCURRENT_REFUSED")
        try:
            completions = []
            observed = self._observe(now, _completion=completions)
            try:
                public = owner.read_pubkey(owner.PUBKEY_PATH)
            except Exception:
                raise OwnerAuthorityError("OWNER_AUTHORITY_KEY_UNREADABLE") from None
            _need(public == observed.public_key_raw
                  and owner.fingerprint(public) == observed.context.owner.fingerprint == key_fingerprint,
                  "OWNER_AUTHORITY_KEY_CHANGED")
            _need(observed.context.code_hash == code_hash, "OWNER_AUTHORITY_CODE_CHANGED")
            try:
                lines = owner._log_lines(owner.log_path())
            except (OSError, RuntimeError):
                raise OwnerAuthorityError("OWNER_AUTHORITY_LOG_UNREADABLE") from None
            check = owner.verify_log(lines, public, [owner_head])
            _need(check.ok, "OWNER_AUTHORITY_LOG_REWRITTEN")
            _need(check.head == observed.context.owner.head,
                  "OWNER_AUTHORITY_LOG_CHANGED_DURING_OBSERVATION")
            finished = self._clock()
            _need(_aware(finished), "OWNER_AUTHORITY_TIME_INVALID")
            _need(finished >= now and len(completions) == 1 and finished >= completions[0],
                  "OWNER_AUTHORITY_CLOCK_ROLLBACK")
            _need(finished-now <= timedelta(seconds=MAX_AUTHORITY_AGE_SECONDS),
                  "OWNER_AUTHORITY_OBSERVATION_LATE")
            _need(observed.context.date == finished.astimezone(compliance.KST).date(),
                  "OWNER_AUTHORITY_DAY_CHANGED")
            self._last = finished
            return observed
        except Exception as exc:
            code = str(exc) if type(exc) is OwnerAuthorityError else "OWNER_AUTHORITY_UNAVAILABLE"
            if self._pinned is not None and not self._latched:
                self._latched = code
            raise OwnerAuthorityError(code) from None
        finally:
            self._lock.release()

    def _observe(self, now, *, _completion=None):
        if self._latched:
            raise OwnerAuthorityError(self._latched)
        _need(self._last is None or now >= self._last, "OWNER_AUTHORITY_CLOCK_ROLLBACK")
        try:
            context = owner.load_context(now, _REVIEW_POSITIONS)
        except ValueError:
            raise OwnerAuthorityError("OWNER_AUTHORITY_TIME_INVALID") from None
        finished = self._clock()
        if _completion is not None:
            _completion.append(finished)
        _need(_aware(finished), "OWNER_AUTHORITY_TIME_INVALID")
        _need(finished >= now, "OWNER_AUTHORITY_CLOCK_ROLLBACK")
        _need(finished - now <= timedelta(seconds=MAX_AUTHORITY_AGE_SECONDS), "OWNER_AUTHORITY_OBSERVATION_LATE")
        _need(context.owner.ok, "OWNER_AUTHORITY_OWNER_STATE_BROKEN")
        _need(context.code_signed is True, "OWNER_AUTHORITY_CODE_NOT_SIGNED")
        try:
            public = owner.read_pubkey(owner.PUBKEY_PATH)
        except Exception:
            raise OwnerAuthorityError("OWNER_AUTHORITY_KEY_UNREADABLE") from None
        fp, head = owner.fingerprint(public), context.owner.head
        _need(fp == context.owner.fingerprint, "OWNER_AUTHORITY_KEY_CHANGED")
        if self._pinned is not None:
            pinned_fp, pinned_code, pinned_head = self._pinned
            _need(fp == pinned_fp, "OWNER_AUTHORITY_KEY_CHANGED")
            _need(context.code_hash == pinned_code, "OWNER_AUTHORITY_CODE_CHANGED")
            if head != pinned_head:
                _need(head[0] > pinned_head[0], "OWNER_AUTHORITY_LOG_REWRITTEN")
                try:
                    lines = owner._log_lines(owner.log_path())
                except (OSError, RuntimeError):
                    raise OwnerAuthorityError("OWNER_AUTHORITY_LOG_UNREADABLE") from None
                check = owner.verify_log(lines, public, [pinned_head])
                _need(check.ok, "OWNER_AUTHORITY_LOG_REWRITTEN")
                _need(check.head == head, "OWNER_AUTHORITY_LOG_CHANGED_DURING_OBSERVATION")
        self._pinned, self._last = (fp, context.code_hash, head), now
        return ReviewAuthority(context=context, public_key_raw=public, observed_at=now)
