"""Prospective paper validation, not an execution permit or source authenticator.

Pure explicit inputs only. Frozen protocol registration precedes the captured
window. The evaluator computes delayed, lot-rounded cash/units/fees itself;
assessment requires a trusted external review of capture authenticity,
independence, preregistration and decision-code fidelity. Hashes alone prove
none of these. Existing owner/session/compliance checks remain indispensable.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import random
import re

from execution_control.model import InstrumentRules, rules_digest
from execution_launch.profile import rule_terms_digest as economic_rules_digest

_HASH = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
EVALUATOR_REVISION = "forward-paper-v1"
_MAX_ROWS = 20000
_MAX_CAPTURE_BYTES = 16 * 1024 * 1024
_EVALUATED: dict[int, tuple[object, str]] = {}


class StrategyEvidenceError(ValueError):
    """Fixed diagnostic codes; no raw provider records or exceptions."""


def _require(condition, code):
    if not condition:
        raise StrategyEvidenceError(code)


def _hash(value):
    _require(type(value) is str and _HASH.fullmatch(value) is not None, "STRATEGY_DIGEST_INVALID")
    return value


def _id(value):
    _require(type(value) is str and _ID.fullmatch(value) is not None, "STRATEGY_ID_INVALID")
    return value


def _instant(value):
    _require(type(value) is datetime and value.utcoffset() is not None, "STRATEGY_TIME_INVALID")
    return value


def _amount(value, *, positive=False):
    _require(type(value) is Decimal and value.is_finite(), "STRATEGY_DECIMAL_REQUIRED")
    _require(len(value.as_tuple().digits) <= 40 and abs(value.as_tuple().exponent) <= 30,
             "STRATEGY_DECIMAL_RANGE")
    _require(value > 0 if positive else value >= 0, "STRATEGY_AMOUNT_INVALID")
    return value


def _plain(value):
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if type(value) is Decimal:
        _amount(value)
        text = format(value, 'f')
        return (text.rstrip('0').rstrip('.') if '.' in text else text) if value else '0'
    if type(value) is datetime:
        return _instant(value).astimezone(timezone.utc).isoformat(timespec='microseconds')
    if type(value) in (tuple, list):
        return [_plain(v) for v in value]
    if type(value) is dict:
        _require(all(type(k) is str for k in value), "STRATEGY_SCHEMA_INVALID")
        return {k: _plain(v) for k, v in value.items()}
    if type(value) is float:
        _require(math.isfinite(value), "STRATEGY_NONFINITE_RESULT")
        return value
    if value is None or type(value) in (str, int, bool):
        return value
    raise StrategyEvidenceError("STRATEGY_SCHEMA_INVALID")


def evidence_digest(value) -> str:
    raw = json.dumps(_plain(value), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode('ascii')).hexdigest()


def _rule_terms(rules):
    rules_digest(rules)  # Revalidate even deliberately mutated frozen inputs.
    return economic_rules_digest(rules)


@dataclass(frozen=True, kw_only=True)
class ForwardProtocol:
    schema_version: int
    study_id: str
    strategy_id: str
    strategy_code_sha256: str
    capture_source_id: str
    capture_source_code_sha256: str
    evaluator_revision: str
    profile_contract_digest: str
    rule_terms_digest: str
    venue: str
    market: str
    symbol: str
    quote_currency: str
    preregistered_at: datetime
    capture_start: datetime
    capture_end: datetime
    initial_cash_quote: Decimal
    fee_fraction: Decimal
    slippage_bps: Decimal
    bar_seconds: int
    minimum_fill_delay_seconds: int
    minimum_observations: int
    minimum_roundtrips: int
    block_length: int
    bootstrap_replications: int
    family_members: tuple[str, ...]
    alpha: Decimal
    max_drawdown: Decimal
    review_max_age_seconds: int
    seed: int


def _protocol(protocol):
    _require(type(protocol) is ForwardProtocol and type(protocol.schema_version) is int
             and protocol.schema_version == 1, "STRATEGY_PROTOCOL_REQUIRED")
    _id(protocol.study_id); _id(protocol.strategy_id); _id(protocol.capture_source_id)
    _require(protocol.evaluator_revision == EVALUATOR_REVISION, 'STRATEGY_EVALUATOR_UNSUPPORTED')
    for name in ('strategy_code_sha256', 'capture_source_code_sha256', 'profile_contract_digest', 'rule_terms_digest'):
        _hash(getattr(protocol, name))
    for name in ('preregistered_at', 'capture_start', 'capture_end'):
        _instant(getattr(protocol, name))
    _require(protocol.preregistered_at < protocol.capture_start < protocol.capture_end,
             "STRATEGY_PREREGISTRATION_NOT_BEFORE_CAPTURE")
    _require(protocol.venue == 'upbit' and protocol.market == 'spot'
             and protocol.quote_currency == 'KRW' and type(protocol.symbol) is str
             and re.fullmatch(r'KRW-[A-Z0-9]{1,20}', protocol.symbol) is not None,
             'STRATEGY_EVALUATOR_SCOPE_UNSUPPORTED')
    for name in ('initial_cash_quote', 'fee_fraction', 'slippage_bps', 'alpha', 'max_drawdown'):
        _amount(getattr(protocol, name), positive=name in ('initial_cash_quote', 'alpha'))
    _require(protocol.fee_fraction <= Decimal('0.1') and protocol.slippage_bps <= 1000
             and protocol.alpha <= Decimal('0.1') and protocol.max_drawdown <= 1,
             "STRATEGY_THRESHOLD_INVALID")
    _require(type(protocol.minimum_observations) is int and 60 <= protocol.minimum_observations < _MAX_ROWS,
             'STRATEGY_THRESHOLD_INVALID')
    bounds = {'bar_seconds': (60, 86400), 'minimum_fill_delay_seconds': (1, 86400),
              'minimum_observations': (60, _MAX_ROWS-1), 'minimum_roundtrips': (20, _MAX_ROWS//2),
              'block_length': (1, protocol.minimum_observations//2),
              'bootstrap_replications': (999, 9999), 'review_max_age_seconds': (60, 30*86400),
              'seed': (1, 2**63-1)}
    for name, (low, high) in bounds.items():
        value = getattr(protocol, name)
        _require(type(value) is int and low <= value <= high, "STRATEGY_THRESHOLD_INVALID")
    _require(protocol.minimum_fill_delay_seconds < protocol.bar_seconds,
             "STRATEGY_FILL_DELAY_INVALID")
    family = protocol.family_members
    _require(type(family) is tuple and 0 < len(family) <= 1000
             and all(type(v) is str for v in family) and family == tuple(sorted(set(family))) and protocol.strategy_id in family,
             "STRATEGY_FAMILY_INVALID")
    for member in family:
        _id(member)
    _require(protocol.capture_end-protocol.capture_start >=
             timedelta(seconds=protocol.bar_seconds*protocol.minimum_observations),
             "STRATEGY_CAPTURE_WINDOW_TOO_SHORT")
    return evidence_digest(protocol)


@dataclass(frozen=True, kw_only=True)
class Registration:
    study_id: str
    protocol_digest: str
    registered_at: datetime
    previous_digest: str
    entry_digest: str


def _registration_fields(row):
    return {f.name: getattr(row, f.name) for f in fields(row) if f.name != 'entry_digest'}


def validate_registry(registry):
    _require(type(registry) is tuple and len(registry) <= 1000, "STRATEGY_REGISTRY_INVALID")
    previous, studies, last = '', set(), None
    for row in registry:
        _require(type(row) is Registration, "STRATEGY_REGISTRY_INVALID")
        _id(row.study_id); _hash(row.protocol_digest); _instant(row.registered_at)
        _require(row.study_id not in studies and row.previous_digest == previous
                 and row.entry_digest == evidence_digest(_registration_fields(row))
                 and (last is None or row.registered_at >= last), "STRATEGY_REGISTRY_CHAIN_INVALID")
        studies.add(row.study_id); previous = row.entry_digest; last = row.registered_at
    return previous


def register_protocol(protocol: ForwardProtocol, registry: tuple[Registration, ...] = ()):
    """Return a new append-only registry value. Publication/time authenticity is external."""
    sha = _protocol(protocol); previous = validate_registry(registry)
    _require(all(r.study_id != protocol.study_id for r in registry), "STRATEGY_STUDY_ALREADY_REGISTERED")
    _require(not registry or protocol.preregistered_at >= registry[-1].registered_at,
             "STRATEGY_REGISTRATION_CLOCK_ROLLBACK")
    body = dict(study_id=protocol.study_id, protocol_digest=sha,
                registered_at=protocol.preregistered_at, previous_digest=previous)
    result = registry + (Registration(**body, entry_digest=evidence_digest(body)),)
    validate_registry(result)
    return result


@dataclass(frozen=True, kw_only=True)
class PaperBar:
    observed_at: datetime
    received_at: datetime
    bid: Decimal
    ask: Decimal
    mark: Decimal
    quote_krw: Decimal
    source_sha256: str


@dataclass(frozen=True, kw_only=True)
class PaperDecision:
    bar_index: int
    decided_at: datetime
    history_sha256: str
    target_fraction: Decimal


def history_digest(bars):
    """Digest exactly the prefix the decision could have observed, never future rows."""
    chain = ''
    for row in bars:
        chain = evidence_digest((chain, row))
    return chain


def capture_history_digests(bars):
    """Incremental prefix identities used by recorded decisions, in linear time."""
    chain, output = '', []
    for row in bars:
        chain = evidence_digest((chain, row)); output.append(chain)
    return tuple(output)


@dataclass(frozen=True, kw_only=True)
class PaperMetrics:
    observations: int
    completed_roundtrips: int
    rejected_small_orders: int
    total_return: float
    mean_return: float
    max_drawdown: float
    total_fees_quote: float
    turnover_quote: float
    terminal_units: str
    cash_nonnegative: bool


@dataclass(frozen=True, kw_only=True)
class ValidationResult:
    protocol_digest: str
    registry_digest: str
    inputs_digest: str
    source_kind: str
    started_at: datetime
    ended_at: datetime
    evaluated_at: datetime
    primary: PaperMetrics
    double_cost: PaperMetrics
    extra_bar_delay: PaperMetrics
    benchmark: PaperMetrics
    benchmark_excess_mean: float
    benchmark_p: float
    family_adjusted_p: float
    net_returns: tuple[float, ...]
    benchmark_returns: tuple[float, ...]


def _validate_capture(protocol, bars, decisions, rules):
    _require(type(bars) is tuple and 2 <= len(bars) <= _MAX_ROWS,
             "STRATEGY_CAPTURE_ROWS_INVALID")
    _require(type(decisions) is tuple and len(decisions) == len(bars)-1,
             "STRATEGY_DECISION_COVERAGE_INCOMPLETE")
    _require(type(rules) is InstrumentRules and _rule_terms(rules) == protocol.rule_terms_digest,
             "STRATEGY_RULES_MISMATCH")
    _require((rules.venue, rules.market, rules.symbol) == (protocol.venue, protocol.market, protocol.symbol)
             and protocol.fee_fraction >= rules.fee_fraction, "STRATEGY_RULES_MISMATCH")
    _require(all(type(row) is PaperBar for row in bars), 'STRATEGY_BAR_INVALID')
    _require(bars[0].observed_at == protocol.capture_start and bars[-1].observed_at == protocol.capture_end,
             "STRATEGY_CAPTURE_WINDOW_INCOMPLETE")
    for i, row in enumerate(bars):
        _require(type(row) is PaperBar, "STRATEGY_BAR_INVALID")
        _instant(row.observed_at); _instant(row.received_at); _hash(row.source_sha256)
        _require(row.received_at >= row.observed_at and row.received_at-row.observed_at <
                 timedelta(seconds=protocol.bar_seconds), "STRATEGY_CAPTURE_CLOCK_INVALID")
        for name in ('bid', 'ask', 'mark', 'quote_krw'):
            _amount(getattr(row, name), positive=True)
        _require(row.bid <= row.mark <= row.ask, "STRATEGY_QUOTE_SPREAD_INVALID")
        _require(protocol.quote_currency != 'KRW' or row.quote_krw == 1, "STRATEGY_QUOTE_FX_INVALID")
        _require((Fraction(row.bid)/Fraction(rules.tick_size)).denominator == 1
                 and (Fraction(row.ask)/Fraction(rules.tick_size)).denominator == 1,
                 "STRATEGY_QUOTE_OFF_TICK")
        if i:
            _require(row.observed_at-bars[i-1].observed_at == timedelta(seconds=protocol.bar_seconds),
                     "STRATEGY_CAPTURE_GAP_OR_DUPLICATE")
    prefixes = capture_history_digests(bars)
    for i, decision in enumerate(decisions):
        _require(type(decision) is PaperDecision and type(decision.bar_index) is int
                 and decision.bar_index == i, "STRATEGY_DECISION_ORDER_INVALID")
        _instant(decision.decided_at); _hash(decision.history_sha256)
        _amount(decision.target_fraction)
        _require(decision.target_fraction <= 1, "STRATEGY_LEVERAGE_UNSUPPORTED")
        _require(decision.history_sha256 == prefixes[i],
                 "STRATEGY_DECISION_INPUT_MISMATCH")
        _require(bars[i].received_at <= decision.decided_at
                 and decision.decided_at+timedelta(seconds=protocol.minimum_fill_delay_seconds)
                 <= bars[i+1].observed_at, "STRATEGY_DECISION_LOOKAHEAD_OR_LATE")


def _floor_lots(value, lot):
    return (value // lot) * lot


def _ceil_lots(value, lot):
    return -((-value) // lot) * lot


def _simulate(protocol, bars, decisions, rules, *, cost_multiple=1, lag=1, buy_hold=False):
    cash, units = Fraction(protocol.initial_cash_quote), Fraction(0)
    fee = Fraction(protocol.fee_fraction)*cost_multiple
    slip = Fraction(protocol.slippage_bps)*cost_multiple/10000
    lot, tick = Fraction(rules.lot_size), Fraction(rules.tick_size)
    fees, turnover, trips, rejected = Fraction(0), Fraction(0), 0, 0
    navs = [cash]
    was_open = False
    for i, row in enumerate(bars):
        if i == 0:
            continue
        mark = Fraction(row.mark)
        ask = _ceil_lots(Fraction(row.ask)*(1+slip), tick)
        bid = _floor_lots(Fraction(row.bid)*(1-slip), tick)
        _require(bid > 0, "STRATEGY_SLIPPAGE_INVALID")
        terminal = i == len(bars)-1
        target = (Fraction(0) if terminal else Fraction(1) if buy_hold and i >= lag else
                  Fraction(decisions[i-lag].target_fraction) if not buy_hold and i >= lag else None)
        if target is not None:
            nav = cash+units*mark
            gap = target*nav-units*mark
            if gap > 0:
                quantity = _floor_lots(gap/(ask*(1+fee)-target*(ask*(1+fee)-mark)), lot)
                quantity = min(quantity, _floor_lots(cash/(ask*(1+fee)), lot))
                side, price = 'buy', ask
            elif gap < 0:
                quantity = min(units, _ceil_lots(-gap/(mark-target*(mark-bid*(1-fee))), lot))
                side, price = 'sell', bid
            else:
                quantity, side, price = Fraction(0), 'none', mark
            if quantity:
                if (quantity < Fraction(rules.min_quantity)
                        or quantity*price*Fraction(row.quote_krw) < Fraction(rules.min_notional_krw)):
                    rejected += 1
                    if terminal:
                        raise StrategyEvidenceError("STRATEGY_TERMINAL_DUST_UNLIQUIDATED")
                else:
                    charge = quantity*price*fee
                    cash += quantity*price-charge if side == 'sell' else -quantity*price-charge
                    units += quantity if side == 'buy' else -quantity
                    fees += charge; turnover += quantity*price
                    _require(cash >= 0 and units >= 0, "STRATEGY_CASH_OR_POSITION_NEGATIVE")
                    if was_open and units == 0:
                        trips += 1
                    was_open = units > 0
        nav = cash+units*mark
        _require(0 < nav <= 10**100, 'STRATEGY_NAV_OUT_OF_RANGE')
        navs.append(nav)
    _require(units == 0, "STRATEGY_TERMINAL_DUST_UNLIQUIDATED")
    returns = tuple(float(b/a-1) for a, b in zip(navs, navs[1:]))
    _require(all(math.isfinite(v) and v > -1 for v in returns), "STRATEGY_RETURN_INVALID")
    peak, drawdown = navs[0], Fraction(0)
    for nav in navs:
        peak = max(peak, nav); drawdown = max(drawdown, 1-nav/peak)
    metrics = PaperMetrics(observations=len(returns), completed_roundtrips=trips,
        rejected_small_orders=rejected, total_return=float(navs[-1]/navs[0]-1),
        mean_return=math.fsum(returns)/len(returns), max_drawdown=float(drawdown),
        total_fees_quote=float(fees), turnover_quote=float(turnover), terminal_units='0', cash_nonnegative=True)
    return metrics, returns


def _block_p(differences, block_length, replications, seed):
    n = len(differences); mean = math.fsum(differences)/n
    centered = [v-mean for v in differences]
    doubled = centered+centered
    prefix = [0.0]
    for value in doubled:
        prefix.append(prefix[-1]+value)
    whole, remainder = divmod(n, block_length)
    blocks = [prefix[i+block_length]-prefix[i] for i in range(n)]
    tails = [prefix[i+remainder]-prefix[i] for i in range(n)] if remainder else ()
    rng = random.Random(seed); exceed = 0
    for _ in range(replications):
        draw = math.fsum(blocks[rng.randrange(n)] for _ in range(whole))
        if remainder:
            draw += tails[rng.randrange(n)]
        exceed += draw/n >= mean
    return (exceed+1)/(replications+1)


def run_paper_validation(protocol, bars, decisions, rules, *, registry, source_kind, now):
    """Evaluate one completely captured future window; no network or live operation.

    A result can be serialized for audit, but imported summary claims are never
    accepted by assessment. Replay the archived inputs with this evaluator.
    """
    sha = _protocol(protocol); _instant(now)
    registry_sha = validate_registry(registry)
    _require(any(r.study_id == protocol.study_id and r.protocol_digest == sha
                 and r.registered_at == protocol.preregistered_at for r in registry),
             "STRATEGY_PROTOCOL_NOT_REGISTERED")
    _require(source_kind in ('prospective_paper_capture', 'synthetic', 'retrospective_replay'),
             "STRATEGY_SOURCE_KIND_INVALID")
    _validate_capture(protocol, bars, decisions, rules)
    _require(now >= max(r.received_at for r in bars) and now >= protocol.capture_end,
             "STRATEGY_CAPTURE_NOT_FINISHED")
    _require(len(bars)-1 >= protocol.minimum_observations, "STRATEGY_OBSERVATIONS_INSUFFICIENT")
    _require(protocol.bootstrap_replications*((len(bars)-1)//protocol.block_length+1) <= 10000000,
             'STRATEGY_INFERENCE_WORK_LIMIT')
    primary, net = _simulate(protocol, bars, decisions, rules)
    doubled, _ = _simulate(protocol, bars, decisions, rules, cost_multiple=2)
    delayed, _ = _simulate(protocol, bars, decisions, rules, lag=2)
    benchmark, buy_hold = _simulate(protocol, bars, decisions, rules, buy_hold=True)
    differences = tuple(a-b for a, b in zip(net, buy_hold))
    p = _block_p(differences, protocol.block_length, protocol.bootstrap_replications, protocol.seed)
    result = ValidationResult(protocol_digest=sha, registry_digest=registry_sha,
        inputs_digest=evidence_digest((bars, decisions)), source_kind=source_kind,
        started_at=bars[0].observed_at, ended_at=bars[-1].observed_at, evaluated_at=now,
        primary=primary, double_cost=doubled, extra_bar_delay=delayed, benchmark=benchmark,
        benchmark_excess_mean=math.fsum(differences)/len(differences), benchmark_p=p,
        family_adjusted_p=min(1.0, p*len(protocol.family_members)),
        net_returns=net, benchmark_returns=buy_hold)
    _require(len(_EVALUATED) < 128, "STRATEGY_EVALUATION_REGISTRY_FULL")
    _EVALUATED[id(result)] = (result, evidence_digest(result))
    return result


@dataclass(frozen=True, kw_only=True)
class ReviewBinding:
    protocol_digest: str
    evidence_digest: str
    registry_digest: str
    inputs_digest: str
    strategy_id: str
    strategy_code_sha256: str
    profile_contract_digest: str
    rule_terms_digest: str
    capture_end: datetime


@dataclass(frozen=True, kw_only=True)
class ReviewReceipt:
    binding_digest: str
    reviewer_id: str
    source_review_sha256: str
    reviewed_at: datetime
    expires_at: datetime


@dataclass(frozen=True, kw_only=True)
class StrategyAssessment:
    strategy_id: str
    strategy_code_sha256: str
    profile_contract_digest: str
    rule_terms_digest: str
    protocol_digest: str
    evidence_digest: str
    math_qualified: bool
    research_review_ready: bool
    reasons: tuple[str, ...]
    execution_ready: bool = False


def assess_strategy(protocol, result, *, profile_contract_digest, rule_terms_digest,
                    strategy_code_sha256, now, review_verifier: Callable | None = None):
    """Require computed evidence and an explicit trusted external review receipt.

    The verifier must authenticate original capture, actual publication before
    capture, independent source windows, registered trial family, and faithful
    decisions from the frozen strategy code. A caller's boolean or a matching
    hash is not that review. E2 independently grants or refuses order capability.
    """
    sha = _protocol(protocol); _instant(now)
    for value in (profile_contract_digest, rule_terms_digest, strategy_code_sha256):
        _hash(value)
    _require(type(result) is ValidationResult, "STRATEGY_COMPUTED_RESULT_REQUIRED")
    issued = _EVALUATED.get(id(result))
    _require(issued is not None and issued[0] is result and issued[1] == evidence_digest(result),
             "STRATEGY_RESULT_NOT_ISSUED_OR_MUTATED")
    reasons = []
    if (result.protocol_digest != sha or result.started_at != protocol.capture_start
            or result.ended_at != protocol.capture_end):
        reasons.append('STRATEGY_PROTOCOL_RESULT_MISMATCH')
    if (profile_contract_digest != protocol.profile_contract_digest
            or rule_terms_digest != protocol.rule_terms_digest
            or strategy_code_sha256 != protocol.strategy_code_sha256):
        reasons.append('STRATEGY_DEPLOYMENT_BINDING_MISMATCH')
    if not result.ended_at <= result.evaluated_at <= now <= result.ended_at+timedelta(seconds=protocol.review_max_age_seconds):
        reasons.append('STRATEGY_EVIDENCE_STALE_OR_FUTURE')
    math_ok = (result.primary.observations >= protocol.minimum_observations
               and result.primary.completed_roundtrips >= protocol.minimum_roundtrips
               and result.primary.total_return > 0 and result.primary.mean_return > 0
               and result.benchmark_excess_mean > 0
               and 0 < result.family_adjusted_p <= float(protocol.alpha)
               and result.double_cost.total_return > 0 and result.double_cost.mean_return > 0
               and result.extra_bar_delay.total_return > 0 and result.extra_bar_delay.mean_return > 0
               and result.primary.max_drawdown <= float(protocol.max_drawdown)
               and result.double_cost.max_drawdown <= float(protocol.max_drawdown)
               and result.extra_bar_delay.max_drawdown <= float(protocol.max_drawdown))
    if not math_ok:
        reasons.append('STRATEGY_PROSPECTIVE_CRITERIA_NOT_MET')
    if result.source_kind != 'prospective_paper_capture':
        reasons.append('STRATEGY_NONPROSPECTIVE_SOURCE')
    binding = ReviewBinding(protocol_digest=sha, evidence_digest=issued[1], registry_digest=result.registry_digest,
        inputs_digest=result.inputs_digest, strategy_id=protocol.strategy_id,
        strategy_code_sha256=protocol.strategy_code_sha256, profile_contract_digest=protocol.profile_contract_digest,
        rule_terms_digest=protocol.rule_terms_digest, capture_end=result.ended_at)
    if review_verifier is None:
        reasons.append('STRATEGY_TRUSTED_REVIEW_REQUIRED')
    elif reasons:
        reasons.append('STRATEGY_REVIEW_NOT_REQUESTED_FOR_REFUSED_EVIDENCE')
    else:
        try:
            receipt = review_verifier(binding)
            _require(type(receipt) is ReviewReceipt, 'STRATEGY_TRUSTED_REVIEW_REQUIRED')
            _id(receipt.reviewer_id); _hash(receipt.source_review_sha256)
            _instant(receipt.reviewed_at); _instant(receipt.expires_at)
            _require(receipt.binding_digest == evidence_digest(binding)
                     and result.evaluated_at <= receipt.reviewed_at <= now < receipt.expires_at
                     <= result.ended_at+timedelta(seconds=protocol.review_max_age_seconds),
                     'STRATEGY_REVIEW_MISMATCH_OR_EXPIRED')
        except Exception:
            reasons.append('STRATEGY_TRUSTED_REVIEW_UNVERIFIED')
    return StrategyAssessment(strategy_id=protocol.strategy_id,
        strategy_code_sha256=protocol.strategy_code_sha256, profile_contract_digest=protocol.profile_contract_digest,
        rule_terms_digest=protocol.rule_terms_digest, protocol_digest=sha, evidence_digest=issued[1],
        math_qualified=math_ok, research_review_ready=not reasons, reasons=tuple(reasons))


def _json(raw, maximum):
    _require(type(raw) in (str, bytes) and len(raw) <= maximum, 'STRATEGY_JSON_SIZE_OR_TYPE')
    def pairs(rows):
        out = {}
        for key, value in rows:
            _require(key not in out, 'STRATEGY_JSON_DUPLICATE_KEY')
            out[key] = value
        return out
    def invalid(value):
        raise StrategyEvidenceError('STRATEGY_JSON_NUMBER_INVALID')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_float=invalid, parse_constant=invalid)
    except (ValueError, TypeError, RecursionError):
        raise StrategyEvidenceError('STRATEGY_JSON_INVALID') from None


def _object(value, cls):
    _require(type(value) is dict and set(value) == {f.name for f in fields(cls)}, 'STRATEGY_JSON_SCHEMA_INVALID')
    return dict(value)


def _date(value):
    _require(type(value) is str, 'STRATEGY_TIME_INVALID')
    try:
        return _instant(datetime.fromisoformat(value))
    except ValueError:
        raise StrategyEvidenceError('STRATEGY_TIME_INVALID') from None


def _decimal(value):
    _require(type(value) is str and re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value) is not None
             and len(value) <= 72, 'STRATEGY_DECIMAL_STRING_REQUIRED')
    return _amount(Decimal(value))


def parse_protocol(raw) -> ForwardProtocol:
    body = _object(_json(raw, 65536), ForwardProtocol)
    for name in ('preregistered_at', 'capture_start', 'capture_end'):
        body[name] = _date(body[name])
    for name in ('initial_cash_quote', 'fee_fraction', 'slippage_bps', 'alpha', 'max_drawdown'):
        body[name] = _decimal(body[name])
    _require(type(body['family_members']) is list, 'STRATEGY_FAMILY_INVALID')
    body['family_members'] = tuple(body['family_members'])
    protocol = ForwardProtocol(**body); _protocol(protocol)
    return protocol


def protocol_json(protocol):
    _protocol(protocol)
    return json.dumps(_plain(protocol), sort_keys=True, indent=2)+'\n'


def evaluate_capture_json(protocol, raw, rules, *, now):
    """Strict evidence import reruns arithmetic, never imports a precomputed PASS."""
    data = _json(raw, _MAX_CAPTURE_BYTES)
    _require(type(data) is dict and set(data) == {'registry', 'source_kind', 'bars', 'decisions'},
             'STRATEGY_CAPTURE_JSON_SCHEMA_INVALID')
    _require(all(type(data[k]) is list for k in ('registry', 'bars', 'decisions')),
             'STRATEGY_CAPTURE_JSON_SCHEMA_INVALID')
    registry, bars, decisions = [], [], []
    for item in data['registry']:
        body = _object(item, Registration); body['registered_at'] = _date(body['registered_at'])
        registry.append(Registration(**body))
    for item in data['bars']:
        body = _object(item, PaperBar)
        for name in ('observed_at', 'received_at'):
            body[name] = _date(body[name])
        for name in ('bid', 'ask', 'mark', 'quote_krw'):
            body[name] = _decimal(body[name])
        bars.append(PaperBar(**body))
    for item in data['decisions']:
        body = _object(item, PaperDecision); body['decided_at'] = _date(body['decided_at'])
        body['target_fraction'] = _decimal(body['target_fraction']); decisions.append(PaperDecision(**body))
    return run_paper_validation(protocol, tuple(bars), tuple(decisions), rules,
                               registry=tuple(registry), source_kind=data['source_kind'], now=now)
