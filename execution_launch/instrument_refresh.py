"""Issued same-contract instrument-rule renewals; no file or network access.

The stable authority/source digest is NOT the fresh receipt digest. A refresh
requires an observation issued by the E1 source in this process. It never
changes economics, scope, strategy, policy, owner approval or session expiry.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from fractions import Fraction
from threading import RLock

from execution_accounts.instrument_terms import (TermsObservation, UniverseTermsAuthority,
                                                  validate_issued_observation, observation_for_rules)
from execution_control.model import Order, InstrumentRules, rules_digest, validate_order
from execution_launch.profile import LaunchProfile, profile_digest, profile_contract_digest, rule_terms_digest

_MAX_ISSUED = 4096
_ISSUED = {}
_HEADS = {}
_BOUND = {}
_USED = set()
_LOCK = RLock()


class RenewalError(ValueError):
    """Fixed refusal codes; no private profile or provider content."""


def _require(ok, code):
    if not ok:
        raise RenewalError(code)


def _time(value):
    _require(type(value) is datetime and value.utcoffset() is not None,
             "RENEWAL_AWARE_TIME_REQUIRED")
    return value


@dataclass(frozen=True, kw_only=True)
class RulesRenewal:
    previous_profile_digest: str
    profile: LaunchProfile = field(repr=False)
    observation: TermsObservation = field(repr=False)
    original_rule_digests: frozenset[str]
    contract_digest: str
    old_rules_digest: str
    new_rules_digest: str
    issued_at: datetime


def renew_profile(profile, observation, *, now, allow_symbol_change=False):
    with _LOCK:
        return _renew_profile(profile, observation, now=now, allow_symbol_change=allow_symbol_change)


def _renew_profile(profile, observation, *, now, allow_symbol_change):
    """Create a fresh snapshot only for identical reviewed terms and scope.

    Initial stale profile snapshots can be replaced by a genuinely new read.
    Once a contract has a process-local head, forks and old snapshots refuse.
    A receipt cannot be reused to refresh another profile/strategy in this process.
    Only a universe profile may move to another coin, and only with allow_symbol_change
    (spec section 10); every refusing check below still runs before the head moves.
    """
    _time(now)
    _require(type(profile) is LaunchProfile and type(profile.instrument_rules) is InstrumentRules,
             "RENEWAL_PROFILE_RULES_REQUIRED")
    _require(type(allow_symbol_change) is bool
             and (not allow_symbol_change or profile.universe_rule_sha256 is not None),
             "RENEWAL_SYMBOL_CHANGE_REFUSED")
    _require((profile.venue, profile.market, profile.quote_currency) == ("upbit", "spot", "KRW"),
             "RENEWAL_VENUE_UNSUPPORTED")
    verified = validate_issued_observation(observation, now=now)
    _require(profile.account_scope == verified.authority.account_scope
             and (profile.symbol == verified.rules.symbol or allow_symbol_change),
             "RENEWAL_ACCOUNT_OR_SYMBOL_MISMATCH")
    # Both sides use the old profile's selector (spec section 10).
    _require(rule_terms_digest(profile.instrument_rules, universe_rule_sha256=profile.universe_rule_sha256)
             == rule_terms_digest(verified.rules, universe_rule_sha256=profile.universe_rule_sha256),
             "RENEWAL_ECONOMIC_OR_SOURCE_CHANGE")
    _require(verified.rules.asof > profile.instrument_rules.asof,
             "RENEWAL_OBSERVATION_NOT_NEWER")
    old_hash, old_rules = profile_digest(profile), rules_digest(profile.instrument_rules)
    contract = profile_contract_digest(profile)
    key = (profile.account_scope, contract)
    head = _HEADS.get(key)
    _require(head is None or head.new_rules_digest == old_rules,
             "RENEWAL_STALE_PROFILE_OR_FORK")
    if head is not None:
        _validate_renewal(head, now=head.issued_at)
        previous = validate_issued_observation(head.observation, now=head.issued_at)
        _require(verified.requested_at > previous.checked_at
                 and verified.chance_receipt.server_time > previous.chance_receipt.server_time
                 and verified.instruments_receipt.server_time > previous.instruments_receipt.server_time,
                 "RENEWAL_RECEIPT_REPLAY_OR_CLOCK_ROLLBACK")
    _require(observation.evidence_digest not in _USED, "RENEWAL_OBSERVATION_REPLAY")
    _require(len(_ISSUED) < _MAX_ISSUED, "RENEWAL_PROCESS_CAPACITY_REACHED")
    current = replace(profile, symbol=verified.rules.symbol, instrument_rules=verified.rules)
    _require(profile_contract_digest(current) == contract, "RENEWAL_CONTRACT_CHANGED")
    roots = frozenset({old_rules}) if head is None else head.original_rule_digests | {old_rules}
    renewal = RulesRenewal(previous_profile_digest=old_hash, profile=current,
        observation=observation, original_rule_digests=roots, contract_digest=contract,
        old_rules_digest=old_rules, new_rules_digest=rules_digest(current.instrument_rules), issued_at=now)
    _ISSUED[id(renewal)] = (renewal, old_hash, profile_digest(current), roots,
                           observation.evidence_digest, contract, old_rules, renewal.new_rules_digest, now)
    _HEADS[key] = renewal
    _BOUND[(profile.account_scope, renewal.new_rules_digest)] = renewal
    _USED.add(observation.evidence_digest)
    return renewal


def validate_renewal(renewal, *, previous_profile=None, now):
    with _LOCK:
        return _validate_renewal(renewal, previous_profile=previous_profile, now=now)


def _validate_renewal(renewal, *, previous_profile=None, now):
    _time(now)
    _require(type(renewal) is RulesRenewal, "RENEWAL_ISSUED_RECORD_REQUIRED")
    saved = _ISSUED.get(id(renewal))
    _require(saved is not None and saved[0] is renewal, "RENEWAL_NOT_ISSUED")
    observation = validate_issued_observation(renewal.observation, now=now)
    _require((renewal.previous_profile_digest, profile_digest(renewal.profile),
              renewal.original_rule_digests, renewal.observation.evidence_digest,
              renewal.contract_digest, renewal.old_rules_digest, renewal.new_rules_digest,
              renewal.issued_at) == saved[1:], "RENEWAL_RECORD_CHANGED")
    _require(renewal.issued_at <= now
             and _HEADS.get((renewal.profile.account_scope, renewal.contract_digest)) is renewal,
             "RENEWAL_NOT_CURRENT")
    _require(rules_digest(observation.rules) == renewal.new_rules_digest
             and profile_contract_digest(renewal.profile) == renewal.contract_digest,
             "RENEWAL_RECORD_CHANGED")
    if previous_profile is not None:
        _require(type(previous_profile) is LaunchProfile
                 and profile_digest(previous_profile) == renewal.previous_profile_digest,
                 "RENEWAL_PREVIOUS_PROFILE_MISMATCH")
    return renewal.profile


def rules_binding_matches(original_digest, current_rules, *, account_scope, now):
    """Keep original prepared/armed session identity while validating a renewal.

    Direct matches retain the existing v1 path. A different timestamp can match
    only through this process's current issued chain, never a supplied JSON claim.
    No owner expiry, code hash, state hash or arm requirement is relaxed here.
    """
    _time(now)
    current_digest = rules_digest(current_rules)
    if original_digest == current_digest:
        return True
    renewal = _BOUND.get((account_scope, current_digest))
    if renewal is None:
        return False
    try:
        validate_renewal(renewal, now=now)
        return original_digest in renewal.original_rule_digests
    except (ValueError, TypeError, ArithmeticError):
        return False


def validate_observed_order(order, rules, *, now):
    """Every order against the observed maximum; a v2 buy also against the cap (spec section 10)."""
    validate_order(order, rules)
    renewal = _BOUND.get((order.account_scope, rules_digest(rules)))
    if renewal is None:
        observation = observation_for_rules(rules, account_scope=order.account_scope, now=now)
        if observation is None:
            return  # legacy sources retain existing controller checks
    else:
        validate_renewal(renewal, now=now)
        observation = renewal.observation
    notional = Fraction(order.quantity) * Fraction(order.limit_price) * Fraction(order.quote_krw)
    _require(notional <= Fraction(observation.observed_maximum_krw), "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")
    _require(order.side != "buy" or type(observation.authority) is not UniverseTermsAuthority
             or notional <= Fraction(observation.authority.maximum_notional_krw), "RENEWAL_BUY_ABOVE_UNIVERSE_CAP")
