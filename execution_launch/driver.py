"""Fixed cash/trend execution adapter, with explicit authenticated input boundaries.

No network, implicit clock, account read, owner signature or order dispatch occurs
here. The trusted history verifier must authenticate real sources AND a durable,
immutable execution anchor for each slot. A hash or prospective label alone does
not do that. Factory registration authenticates this callback's local identity,
not the source, profitability, reviewer or permission to trade.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
from pathlib import Path
import re
from threading import RLock
from typing import Callable

from execution_control.capability import digest
from execution_control.controller import AccountObservation
from execution_control.model import Order, decimal_text, validate_order
from execution_launch.profile import (LaunchProfile, profile_contract_digest,
    profile_digest, rule_terms_digest)
from execution_launch.program import (ProgramSpec, parameters_json,
    program_digest, target_fraction)
from execution_launch.runner import DecisionInput, Quote, Signal, StrategyDriver
from execution_launch.strategy import (ForwardProtocol, PaperBar, PaperDecision,
    evidence_digest, history_digest, parse_protocol, protocol_json)

FACTORY_ID = "tradegen-fixed-cash-trend-v1"
_HASH = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
_SOURCE_FILES = ("execution_launch/driver.py", "execution_launch/program.py",
    "execution_launch/strategy.py", "execution_launch/runner.py",
    "execution_launch/profile.py", "execution_control/model.py",
    "execution_control/capability.py", "execution_control/controller.py")
_LOCK = RLock()
_ISSUED = {}
_CALLBACKS = {}


class FixedDriverError(ValueError):
    """Sanitized reason codes only."""


def _require(value, code):
    if not value:
        raise FixedDriverError(code)


def _instant(value):
    try:
        _require(type(value) is datetime and value.utcoffset() is not None,
                 "FIXED_DRIVER_TIME_INVALID")
        value.astimezone(timezone.utc)
    except (ValueError, OverflowError, TypeError):
        raise FixedDriverError("FIXED_DRIVER_TIME_INVALID") from None


def _sha(value):
    _require(type(value) is str and _HASH.fullmatch(value) is not None,
             "FIXED_DRIVER_DIGEST_INVALID")


def _amount(value, *, positive=False):
    _require(type(value) is Decimal and value.is_finite()
             and len(value.as_tuple().digits) <= 40 and abs(value.as_tuple().exponent) <= 30
             and (value > 0 if positive else value >= 0), "FIXED_DRIVER_AMOUNT_INVALID")


@dataclass(frozen=True, kw_only=True)
class DeploymentWindow:
    deployment_id: str
    start: datetime
    end: datetime


@dataclass(frozen=True, kw_only=True)
class AccountAnchor:
    """Original reconciled sizing inputs, durably fixed before the slot is used."""
    cash_quote: Decimal
    units: Decimal
    account_asof: datetime


@dataclass(frozen=True, kw_only=True)
class HistoryFrame:
    """Complete prefix including this slot, and the decision from the prior slot.

    The verifier must reject rewritten anchors, backfilled slots, invented source
    receipts and imported synthetic/replay records, including after a restart.
    The current bar prices size the order; its mark never enters its target.
    """
    deployment_window_digest: str
    source_kind: str
    bars: tuple[PaperBar, ...]
    prior_decision: PaperDecision | None
    anchor: AccountAnchor


@dataclass(frozen=True, kw_only=True)
class HistoryReceipt:
    frame_digest: str
    driver_identity_digest: str
    source_audit_sha256: str
    verified_at: datetime
    expires_at: datetime


@dataclass(frozen=True, kw_only=True)
class FixedDriverIdentity:
    factory_id: str
    program_digest: str
    deployment_code_sha256: str
    protocol_digest: str
    profile_contract_digest: str
    rule_terms_digest: str
    deployment_window_digest: str


def _sources():
    """Read bounded, fixed public code paths only, on explicit construction/check."""
    root = Path(__file__).resolve().parent.parent
    bodies = {}
    try:
        for name in _SOURCE_FILES:
            path = root / name
            _require(not path.is_symlink() and path.is_file()
                     and 0 < path.stat().st_size <= 1048576,
                     "FIXED_DRIVER_SOURCE_INVALID")
            with path.open("rb") as stream:
                body = stream.read(1048577)
            _require(0 < len(body) <= 1048576, "FIXED_DRIVER_SOURCE_INVALID")
            bodies[name] = body
    except OSError:
        raise FixedDriverError("FIXED_DRIVER_SOURCE_UNAVAILABLE") from None
    manifest = {name: hashlib.sha256(body).hexdigest() for name, body in bodies.items()}
    return digest({"factory_id": FACTORY_ID, "files": manifest}), bodies["execution_launch/program.py"]


def _window(window, protocol):
    _require(type(window) is DeploymentWindow and type(window.deployment_id) is str
             and _ID.fullmatch(window.deployment_id) is not None, "FIXED_DRIVER_WINDOW_INVALID")
    _instant(window.start); _instant(window.end)
    step = timedelta(seconds=protocol.bar_seconds)
    span = window.end-window.start
    _require(span > timedelta(0) and span % step == timedelta(0)
             and 2 <= span // step + 1 <= 20000, "FIXED_DRIVER_WINDOW_INVALID")
    return digest(window)


def _identity(program, protocol, profile, window, artifact, code_sha):
    _require(type(program) is ProgramSpec and type(protocol) is ForwardProtocol
             and type(profile) is LaunchProfile, "FIXED_DRIVER_INPUT_REQUIRED")
    parse_protocol(protocol_json(protocol))
    code = program_digest(program, artifact)
    _require(program.strategy_id == protocol.strategy_id == profile.strategy_id
             and code == protocol.strategy_code_sha256 == profile.strategy_code_sha256,
             "FIXED_DRIVER_PROGRAM_BINDING_MISMATCH")
    _require((profile.venue, profile.market, profile.symbol, profile.quote_currency, profile.time_in_force)
             == (protocol.venue, protocol.market, protocol.symbol, "KRW", "gtc")
             and profile.account_scope is not None and profile.instrument_rules is not None,
             "FIXED_DRIVER_SCOPE_MISMATCH")
    terms = rule_terms_digest(profile.instrument_rules)
    contract = profile_contract_digest(profile)
    _require(terms == protocol.rule_terms_digest and contract == protocol.profile_contract_digest
             and profile.policy.initial_equity == protocol.initial_cash_quote
             and protocol.fee_fraction >= profile.instrument_rules.fee_fraction,
             "FIXED_DRIVER_CONTRACT_MISMATCH")
    return FixedDriverIdentity(factory_id=FACTORY_ID, program_digest=code,
        deployment_code_sha256=code_sha, protocol_digest=evidence_digest(protocol),
        profile_contract_digest=contract, rule_terms_digest=terms,
        deployment_window_digest=_window(window, protocol))


def history_frame_digest(frame: HistoryFrame) -> str:
    _require(type(frame) is HistoryFrame and type(frame.bars) is tuple
             and 1 <= len(frame.bars) <= 20000, "FIXED_DRIVER_HISTORY_REQUIRED")
    return evidence_digest(frame)


def _finite_decimal(value: Fraction) -> Decimal:
    """Exact conversion after lot/tick rounding, independent of Decimal context."""
    denominator, twos, fives = value.denominator, 0, 0
    while denominator % 2 == 0:
        denominator //= 2; twos += 1
    while denominator % 5 == 0:
        denominator //= 5; fives += 1
    _require(denominator == 1, "FIXED_DRIVER_NONDECIMAL_RESULT")
    scale = max(twos, fives)
    numerator = value.numerator * 2**(scale-twos) * 5**(scale-fives)
    result = Decimal((1 if numerator < 0 else 0, tuple(int(c) for c in str(abs(numerator))), -scale))
    # Same model validation as the eventual Order; no rounded string conversion.
    decimal_text(result)
    return result


def _floor(value, increment):
    return (value // increment) * increment


def _ceil(value, increment):
    return -((-value) // increment) * increment


def _sized_signal(identity, frame, target, rules, protocol):
    """The base-cost, one-bar-delay allocation equations of strategy._simulate."""
    row = frame.bars[-1]
    cash, units = Fraction(frame.anchor.cash_quote), Fraction(frame.anchor.units)
    fee, slip = Fraction(protocol.fee_fraction), Fraction(protocol.slippage_bps)/10000
    lot, tick, mark = Fraction(rules.lot_size), Fraction(rules.tick_size), Fraction(row.mark)
    ask = _ceil(Fraction(row.ask)*(1+slip), tick)
    bid = _floor(Fraction(row.bid)*(1-slip), tick)
    _require(bid > 0, "FIXED_DRIVER_SLIPPAGE_INVALID")
    target = Fraction(target)
    nav = cash+units*mark
    _require(0 < nav <= 10**100, "FIXED_DRIVER_NAV_INVALID")
    gap = target*nav-units*mark
    if gap > 0:
        quantity = min(_floor(gap/(ask*(1+fee)-target*(ask*(1+fee)-mark)), lot),
                       _floor(cash/(ask*(1+fee)), lot))
        action, price = "entry", ask
    elif gap < 0:
        quantity = min(units, _ceil(-gap/(mark-target*(mark-bid*(1-fee))), lot))
        action, price = "exit", bid
    else:
        quantity, action, price = Fraction(0), "hold", mark
    signal_id = "fixed:"+digest({"identity":identity, "slot":row.observed_at})
    if not quantity:
        return Signal(signal_id=signal_id, action="hold")
    if quantity < Fraction(rules.min_quantity) or quantity*price < Fraction(rules.min_notional_krw):
        _require(row.observed_at != frame.bars[0].observed_at, "FIXED_DRIVER_INITIAL_STATE_INVALID")
        return Signal(signal_id=signal_id, action="hold")
    return Signal(signal_id=signal_id, action=action,
                  quantity=_finite_decimal(quantity), limit_price=_finite_decimal(price))


def _validate_frame(callback, frame, observation):
    _require(type(observation) is DecisionInput and type(observation.quote) is Quote
             and type(observation.account) is AccountObservation, "FIXED_DRIVER_OBSERVATION_REQUIRED")
    _instant(observation.now)
    identity, protocol, window = callback.identity, callback.protocol, callback.window
    profile = observation.profile
    # The runner swaps in each renewed profile; a same-terms renewal changes only
    # instrument_rules.asof, which the contract digest leaves out.
    _require(type(profile) is LaunchProfile
             and (profile.venue, profile.market, profile.account_scope)
             == (protocol.venue, protocol.market, callback.profile.account_scope),
             "FIXED_DRIVER_SCOPE_MISMATCH")
    _require(profile_contract_digest(profile) == identity.profile_contract_digest,
             "FIXED_DRIVER_PROFILE_CHANGED")
    frame_sha = history_frame_digest(frame)
    _require(frame.deployment_window_digest == identity.deployment_window_digest
             and frame.source_kind == "prospective_paper_capture", "FIXED_DRIVER_HISTORY_SOURCE_INVALID")
    step = timedelta(seconds=protocol.bar_seconds)
    rules = profile.instrument_rules
    for index, row in enumerate(frame.bars):
        _require(type(row) is PaperBar, "FIXED_DRIVER_BAR_REQUIRED")
        _instant(row.observed_at); _instant(row.received_at); _sha(row.source_sha256)
        _require(row.observed_at == window.start+index*step and row.observed_at <= window.end
                 and row.observed_at <= row.received_at <= row.observed_at+timedelta(seconds=10)
                 and row.received_at <= observation.now, "FIXED_DRIVER_HISTORY_TIME_INVALID")
        for value in (row.bid, row.ask, row.mark, row.quote_krw):
            _amount(value, positive=True)
        _require(row.quote_krw == 1 and row.bid <= row.ask
                 and Fraction(row.mark) == (Fraction(row.bid)+Fraction(row.ask))/2
                 and (Fraction(row.bid)/Fraction(rules.tick_size)).denominator == 1
                 and (Fraction(row.ask)/Fraction(rules.tick_size)).denominator == 1,
                 "FIXED_DRIVER_BAR_PRICE_INVALID")
    current = frame.bars[-1]
    _require(current.observed_at <= observation.now <= current.observed_at+timedelta(seconds=10),
             "FIXED_DRIVER_EXECUTION_SLOT_EXPIRED")
    quote = observation.quote
    _instant(quote.asof)
    _amount(quote.bid, positive=True); _amount(quote.ask, positive=True)
    _require((quote.venue, quote.market, quote.symbol) == (protocol.venue, protocol.market, protocol.symbol)
             and (quote.bid, quote.ask, quote.source_sha256) == (current.bid, current.ask, current.source_sha256)
             and timedelta(0) <= current.observed_at-quote.asof <= timedelta(seconds=10)
             and timedelta(0) <= observation.now-quote.asof <= timedelta(seconds=10),
             "FIXED_DRIVER_QUOTE_ANCHOR_MISMATCH")
    if len(frame.bars) == 1:
        _require(frame.prior_decision is None, "FIXED_DRIVER_INITIAL_DECISION_INVALID")
        target = Decimal(0)
    else:
        prior = frame.prior_decision
        _require(type(prior) is PaperDecision and type(prior.bar_index) is int
                 and prior.bar_index == len(frame.bars)-2, "FIXED_DRIVER_PRIOR_DECISION_REQUIRED")
        _instant(prior.decided_at); _sha(prior.history_sha256); _amount(prior.target_fraction)
        _require(prior.history_sha256 == history_digest(frame.bars[:-1])
                 and frame.bars[-2].received_at <= prior.decided_at
                 and prior.decided_at+timedelta(seconds=protocol.minimum_fill_delay_seconds)
                 <= current.observed_at, "FIXED_DRIVER_DECISION_LOOKAHEAD_OR_CHANGED")
        expected = target_fraction(callback.program, tuple(row.mark for row in frame.bars[:-1]))
        _require(prior.target_fraction == expected, "FIXED_DRIVER_TARGET_MISMATCH")
        target = Decimal(0) if current.observed_at == window.end else expected
    anchor, account = frame.anchor, observation.account
    _require(type(anchor) is AccountAnchor, "FIXED_DRIVER_ACCOUNT_ANCHOR_REQUIRED")
    _amount(anchor.cash_quote); _amount(anchor.units); _instant(anchor.account_asof)
    _require(timedelta(0) <= current.received_at-anchor.account_asof <= timedelta(seconds=30)
             and timedelta(0) <= observation.now-anchor.account_asof <= timedelta(seconds=30)
             and anchor.account_asof == account.asof, "FIXED_DRIVER_ACCOUNT_ANCHOR_TIME_INVALID")
    _instant(account.server_time)
    _require(abs(observation.now-account.server_time) <= timedelta(seconds=60)
             and account.no_credit is True and account.risk.data_complete is True
             and account.risk.external_flows_known is True and account.risk.asof == account.asof,
             "FIXED_DRIVER_ACCOUNT_INCOMPLETE")
    key = (protocol.venue, callback.profile.account_scope)
    holding_key = (*key, protocol.market, protocol.symbol)
    _amount(account.settled_cash_krw.get(key))
    _amount(account.quote_rates_krw.get((*key, "KRW")), positive=True)
    _require(account.account_scopes.get(protocol.venue) == key[1]
             and account.quote_currency_by_account.get(key) == "KRW"
             and account.quote_rates_krw.get((*key, "KRW")) == 1
             and account.settled_cash_krw.get(key) == anchor.cash_quote
             and account.holdings.get(holding_key, Decimal(0)) == anchor.units,
             "FIXED_DRIVER_ACCOUNT_ANCHOR_MISMATCH")
    for held_key, units in account.holdings.items():
        _amount(units)
        _require(type(held_key) is tuple and len(held_key) == 4, "FIXED_DRIVER_ACCOUNT_SCOPE_INVALID")
        _require(held_key[:2] != key or held_key == holding_key or units == 0,
                 "FIXED_DRIVER_OTHER_INVENTORY_UNSUPPORTED")
    equity, inventory = account.held_exposure_krw.get(key), account.inventory_exposure_krw.get(key)
    _amount(equity); _amount(inventory)
    _require(Fraction(equity)-Fraction(inventory) == Fraction(anchor.cash_quote),
             "FIXED_DRIVER_RESERVED_CASH_UNSUPPORTED")
    for quantity in account.cancellable_quantities.values():
        _amount(quantity)
        _require(quantity == 0, "FIXED_DRIVER_OUTSTANDING_ORDER_UNSUPPORTED")
    _require((Fraction(anchor.units)/Fraction(rules.lot_size)).denominator == 1,
             "FIXED_DRIVER_INVENTORY_OFF_LOT")
    if len(frame.bars) == 1:
        _require(anchor.units == 0 and anchor.cash_quote == protocol.initial_cash_quote,
                 "FIXED_DRIVER_INITIAL_STATE_INVALID")
    return frame_sha, target


@dataclass(frozen=True, eq=False)
class _FixedCallback:
    program: ProgramSpec
    protocol: ForwardProtocol
    profile: LaunchProfile
    window: DeploymentWindow
    identity: FixedDriverIdentity
    profile_sha: str
    history_provider: Callable
    history_verifier: Callable
    seen: dict = field(default_factory=dict)
    lock: object = field(default_factory=RLock)

    def __call__(self, observation, parameters):
        with self.lock:
            with _LOCK:
                driver = _CALLBACKS.get(id(self))
            identity = describe_fixed_driver(driver)
            _require(parameters == driver.parameters_json, "FIXED_DRIVER_PARAMETERS_CHANGED")
            try:
                frame = self.history_provider(observation)
            except Exception:
                raise FixedDriverError("FIXED_DRIVER_HISTORY_PROVIDER_FAILED") from None
            frame_sha, target = _validate_frame(self, frame, observation)
            before = frame_sha
            try:
                receipt = self.history_verifier(frame, identity, observation.now)
            except Exception:
                raise FixedDriverError("FIXED_DRIVER_HISTORY_AUTH_FAILED") from None
            _require(type(receipt) is HistoryReceipt, "FIXED_DRIVER_HISTORY_UNVERIFIED")
            _instant(receipt.verified_at); _instant(receipt.expires_at); _sha(receipt.source_audit_sha256)
            _require(receipt.frame_digest == frame_sha and receipt.driver_identity_digest == digest(identity)
                     and frame.bars[-1].received_at <= receipt.verified_at <= observation.now < receipt.expires_at,
                     "FIXED_DRIVER_HISTORY_UNVERIFIED")
            # Recheck injected dependencies cannot mutate frozen nested values during verification.
            frame_sha, target = _validate_frame(self, frame, observation)
            _require(before == frame_sha, "FIXED_DRIVER_HISTORY_CHANGED")
            describe_fixed_driver(driver)
            slot = frame.bars[-1].observed_at
            previous = self.seen.get(slot)
            _require(previous is None or previous[0] == frame_sha, "FIXED_DRIVER_SLOT_REWRITTEN")
            if self.seen:
                last = max(self.seen)
                _require(slot >= last, "FIXED_DRIVER_SLOT_ROLLBACK")
                old = self.seen[last]
                _require(history_digest(frame.bars[:old[1]]) == old[2],
                         "FIXED_DRIVER_PREFIX_REWRITTEN")
            self.seen[slot] = (frame_sha, len(frame.bars), history_digest(frame.bars))
            profile = observation.profile
            signal = _sized_signal(identity, frame, target, profile.instrument_rules, self.protocol)
            _require(not (slot == self.window.end and frame.anchor.units > 0 and signal.action == "hold"),
                     "FIXED_DRIVER_TERMINAL_DUST_UNLIQUIDATED")
            if signal.action != "hold":
                validate_order(Order(client_id="fixedvalidation", account_scope=profile.account_scope,
                    venue=profile.venue, market=profile.market, symbol=profile.symbol,
                    side="buy" if signal.action == "entry" else "sell", quantity=signal.quantity,
                    limit_price=signal.limit_price, quote_krw=Decimal(1), time_in_force=profile.time_in_force),
                    profile.instrument_rules)
            return signal


def make_fixed_driver(program: ProgramSpec, protocol: ForwardProtocol, profile: LaunchProfile, *,
                      window: DeploymentWindow, history_provider: Callable,
                      history_verifier: Callable, program_artifact: bytes) -> StrategyDriver:
    """Construct the fixed adapter; grants no source, research or execution approval.

    Providers receive DecisionInput. The trusted verifier receives
    (HistoryFrame, FixedDriverIdentity, now) and must return HistoryReceipt only
    after source authentication and durable per-slot anchor verification.
    """
    _require(callable(history_provider) and callable(history_verifier),
             "FIXED_DRIVER_AUTHENTICATED_HISTORY_REQUIRED")
    code_sha, actual_program = _sources()
    _require(type(program_artifact) is bytes and program_artifact == actual_program,
             "FIXED_DRIVER_ARTIFACT_NOT_INSTALLED_PROGRAM")
    identity = _identity(program, protocol, profile, window, program_artifact, code_sha)
    callback = _FixedCallback(program, protocol, profile, window, identity,
                              profile_digest(profile), history_provider, history_verifier)
    driver = StrategyDriver(callback=callback, artifact=program_artifact,
                            parameters_json=parameters_json(program))
    with _LOCK:
        _require(len(_ISSUED) < 1024, "FIXED_DRIVER_REGISTRY_LIMIT")
        _ISSUED[id(driver)] = (driver, callback, identity, history_provider, history_verifier)
        _CALLBACKS[id(callback)] = driver
    return driver


def describe_fixed_driver(driver: StrategyDriver) -> FixedDriverIdentity:
    """Identify only an unchanged factory-issued instance, never arbitrary code.

    A copied StrategyDriver or replacement callback fails even with equal bytes.
    This process-local registry is application discipline, not a Python sandbox.
    Deployment approval must separately bind this identity and actual code hash.
    """
    with _LOCK:
        record = _ISSUED.get(id(driver))
    _require(record is not None and record[0] is driver and type(driver) is StrategyDriver,
             "FIXED_DRIVER_NOT_ISSUED")
    _, callback, identity, provider, verifier = record
    _require(driver.callback is callback and type(callback) is _FixedCallback
             and callback.identity is identity and callback.history_provider is provider
             and callback.history_verifier is verifier, "FIXED_DRIVER_CALLBACK_CHANGED")
    code_sha, actual_program = _sources()
    _require(driver.artifact == actual_program and driver.parameters_json == parameters_json(callback.program)
             and profile_digest(callback.profile) == callback.profile_sha,
             "FIXED_DRIVER_REGISTERED_INPUT_CHANGED")
    rebuilt = _identity(callback.program, callback.protocol, callback.profile, callback.window,
                        driver.artifact, code_sha)
    _require(rebuilt == identity, "FIXED_DRIVER_DEPLOYMENT_CHANGED")
    return identity


def fixed_history_dependencies(driver: StrategyDriver) -> tuple[Callable, Callable]:
    """Return exact upstream callables for explicit trusted deployment selection.

    An implementation verifier must compare these identities with its explicitly
    approved provider and verifier. Equality of function identity does not prove
    source authenticity or that those integrations were reviewed.
    """
    describe_fixed_driver(driver)
    with _LOCK:
        record = _ISSUED[id(driver)]
    return record[3], record[4]
