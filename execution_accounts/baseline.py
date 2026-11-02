"""Pure, checkpointed risk-baseline reduction over reviewed interval evidence.

Inputs are account-wide KRW valuations and complete interval extrema, not quote
endpoints. A hash proves consistency only. The caller must authenticate sources,
retain the expected checkpoint outside this reducer, and preserve its history.
No file, owner state, credential, network or wall clock is accessed here.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, DecimalException, Inexact, localcontext
import json
import re

from core.compliance.model import KST
from execution_accounts.model import RiskBaseline, canonical, content_digest
from execution_control.risk import RecoveryCheckpoint

_ZERO = Decimal(0)
_HASH = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Za-z0-9_.:/-]{1,128}")
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")


class BaselineError(ValueError):
    """Fixed codes; account values and source exceptions are never echoed."""


def _require(ok, code):
    if not ok:
        raise BaselineError(code)


def _amount(value, *, signed=False, positive=False):
    _require(type(value) is Decimal and value.is_finite(), "BASELINE_EXACT_DECIMAL_REQUIRED")
    _require(len(value.as_tuple().digits) <= 60 and -40 <= value.as_tuple().exponent <= 40,
             "BASELINE_NUMBER_OUT_OF_RANGE")
    _require(signed or (value > 0 if positive else value >= 0), "BASELINE_NUMBER_OUT_OF_RANGE")


def _instant(value):
    _require(type(value) is datetime and value.utcoffset() is not None, "BASELINE_AWARE_TIME_REQUIRED")
    _require(2 <= value.year <= 9998, "BASELINE_TIME_OUT_OF_RANGE")


def _hash(value):
    _require(type(value) is str and _HASH.fullmatch(value) is not None, "BASELINE_DIGEST_REQUIRED")


@dataclass(frozen=True, kw_only=True)
class BaselineConventions:
    # No default choice: the operator's approved policy must select these terms.
    daily_loss: str
    external_flows: str
    max_interval_seconds: int
    recovery_cutoff_seconds: int | None = None


@dataclass(frozen=True, kw_only=True)
class _V1Conventions:
    """The original digest representation; never silently migrate a trusted head."""
    daily_loss: str
    external_flows: str
    max_interval_seconds: int


@dataclass(frozen=True, kw_only=True)
class BaselineAnchor:
    """Reviewed opening/checkpoint evidence; never a process-start reset."""
    account_scope: str
    baseline: RiskBaseline
    equity_krw: Decimal
    realized_net_total_krw: Decimal
    day_open_realized_net_total_krw: Decimal
    previous_day_realized_net_krw: Decimal | None
    sequence: int


@dataclass(frozen=True, kw_only=True)
class BaselineInterval:
    """A complete half-open [start, end) account-history interval.

    Values at ``end`` are the opening snapshot immediately before events at that
    timestamp. Extrema include the prior and new snapshot values. This precise
    cut-off makes a midnight snapshot the new day's opening, not its first trade.
    The authenticated source must establish this convention and interval coverage.
    """
    account_scope: str
    sequence: int
    previous_state_digest: str
    start: datetime
    end: datetime
    equity_krw: Decimal
    minimum_equity_krw: Decimal
    maximum_equity_krw: Decimal
    realized_net_total_krw: Decimal
    gross_external_inflows_krw: Decimal | None
    gross_external_outflows_krw: Decimal | None
    source_sha256: str
    coverage_sha256: str


@dataclass(frozen=True, kw_only=True)
class BaselineState:
    schema_version: int
    account_scope: str
    conventions: BaselineConventions
    first_trading_day: date
    asof: datetime
    sequence: int
    equity_krw: Decimal
    day_start_equity: Decimal
    high_watermark: Decimal
    observed_daily_loss: Decimal
    realized_net_total_krw: Decimal
    day_open_realized_net_total_krw: Decimal
    previous_day_realized_net_krw: Decimal | None
    approved_effective_floor: Decimal | None
    anchor_sha256: str
    previous_state_digest: str
    last_interval_digest: str
    state_digest: str
    recovery_checkpoint: RecoveryCheckpoint | None = None


def _conventions(value):
    _require(type(value) is BaselineConventions, "BASELINE_CONVENTIONS_REQUIRED")
    _require(type(value.daily_loss) is str and value.daily_loss == "maximum_net_equity_loss_from_day_open",
             "BASELINE_DAILY_LOSS_CONVENTION_UNSUPPORTED")
    _require(type(value.external_flows) is str and value.external_flows == "no_external_flows",
             "BASELINE_FLOW_CONVENTION_UNSUPPORTED")
    _require(type(value.max_interval_seconds) is int and 1 <= value.max_interval_seconds <= 300,
             "BASELINE_INTERVAL_BOUND_REQUIRED")
    _require(value.recovery_cutoff_seconds is None
             or (type(value.recovery_cutoff_seconds) is int and value.recovery_cutoff_seconds == 79200),
             "BASELINE_RECOVERY_CUTOFF_UNSUPPORTED")


def _body(state):
    values = []
    for field in fields(BaselineState):
        if field.name == "state_digest" or (field.name == "recovery_checkpoint" and state.schema_version == 1):
            continue
        value = getattr(state, field.name)
        if field.name == "conventions" and state.schema_version == 1:
            value = _V1Conventions(daily_loss=value.daily_loss, external_flows=value.external_flows,
                                   max_interval_seconds=value.max_interval_seconds)
        values.append(value)
    return tuple(values)


def _required_cutoff(state):
    if state.conventions.recovery_cutoff_seconds is None:
        return None
    day = state.asof.astimezone(KST).date()
    if state.first_trading_day != day and state.previous_day_realized_net_krw != _ZERO:
        return None
    return datetime.combine(day, time(22), tzinfo=KST)


def _validate_recovery(state):
    checkpoint = state.recovery_checkpoint
    cutoff = _required_cutoff(state)
    if checkpoint is None:
        _require(cutoff is None or state.asof != cutoff, "BASELINE_RECOVERY_BOUNDARY_REQUIRED")
        return
    _require(type(checkpoint) is RecoveryCheckpoint and cutoff is not None,
             "BASELINE_RECOVERY_CHECKPOINT_INVALID")
    _instant(checkpoint.cutoff_at); _amount(checkpoint.equity_krw, positive=True); _hash(checkpoint.source_sha256)
    _require(checkpoint.cutoff_at == cutoff and cutoff <= state.asof,
             "BASELINE_RECOVERY_CHECKPOINT_INVALID")
    _require(state.high_watermark >= checkpoint.equity_krw
             and state.observed_daily_loss >= max(_ZERO, state.day_start_equity-checkpoint.equity_krw),
             "BASELINE_RECOVERY_HISTORY_CONTRADICTION")
    if state.asof == cutoff:
        _require(checkpoint.equity_krw == state.equity_krw, "BASELINE_RECOVERY_EQUITY_CONTRADICTION")


def _state(**values):
    empty = BaselineState(**values, state_digest="")
    return BaselineState(**values, state_digest=content_digest(_body(empty)))


def _validate(state):
    _require(type(state) is BaselineState and type(state.schema_version) is int
             and state.schema_version in (1, 2), "BASELINE_STATE_REQUIRED")
    _conventions(state.conventions); _instant(state.asof)
    _require((state.schema_version == 1) == (state.conventions.recovery_cutoff_seconds is None),
             "BASELINE_SCHEMA_CONVENTION_MISMATCH")
    _require(type(state.account_scope) is str and _ID.fullmatch(state.account_scope) is not None,
             "BASELINE_SCOPE_INVALID")
    _require(type(state.first_trading_day) is date
             and state.first_trading_day <= state.asof.astimezone(KST).date(), "BASELINE_FIRST_DAY_INVALID")
    _require(type(state.sequence) is int and 0 <= state.sequence < 2**63, "BASELINE_SEQUENCE_INVALID")
    for name in ("equity_krw", "day_start_equity", "high_watermark"):
        _amount(getattr(state, name), positive=True)
    _amount(state.observed_daily_loss)
    _amount(state.realized_net_total_krw, signed=True)
    _amount(state.day_open_realized_net_total_krw, signed=True)
    if state.previous_day_realized_net_krw is not None:
        _amount(state.previous_day_realized_net_krw, signed=True)
    _require((state.previous_day_realized_net_krw is None)
             == (state.first_trading_day == state.asof.astimezone(KST).date()),
             "BASELINE_PRIOR_DAY_PROFIT_REQUIRED")
    if state.approved_effective_floor is not None:
        _amount(state.approved_effective_floor)
    _require(state.high_watermark >= max(state.day_start_equity, state.equity_krw),
             "BASELINE_PEAK_CONTRADICTION")
    _require(state.observed_daily_loss >= max(_ZERO, state.day_start_equity-state.equity_krw),
             "BASELINE_DAILY_LOSS_CONTRADICTION")
    _validate_recovery(state)
    _hash(state.anchor_sha256); _hash(state.state_digest)
    _require(bool(state.previous_state_digest) == bool(state.last_interval_digest),
             "BASELINE_CHAIN_INVALID")
    if state.previous_state_digest:
        _hash(state.previous_state_digest); _hash(state.last_interval_digest)
    _require(state.state_digest == content_digest(_body(state)), "BASELINE_STATE_CHANGED")


def initialize_baseline(conventions: BaselineConventions, anchor: BaselineAnchor) -> BaselineState:
    """Start only from a reviewed source anchor, not from a current-balance shortcut."""
    try:
        with localcontext() as numeric:
            numeric.prec = 512; numeric.traps[Inexact] = True
            _conventions(conventions)
            _require(type(anchor) is BaselineAnchor and type(anchor.baseline) is RiskBaseline,
                     "BASELINE_REVIEWED_ANCHOR_REQUIRED")
            b = anchor.baseline
            _hash(b.source_sha256); _amount(anchor.equity_krw, positive=True)
            _amount(b.prior_high_watermark, positive=True)
            _amount(b.day_start_equity, positive=True)
            _require(b.prior_high_watermark >= b.day_start_equity, "BASELINE_PEAK_CONTRADICTION")
            state = _state(schema_version=1 if conventions.recovery_cutoff_seconds is None else 2,
                account_scope=anchor.account_scope, conventions=conventions,
                first_trading_day=b.first_trading_day, asof=b.asof, sequence=anchor.sequence,
                equity_krw=anchor.equity_krw, day_start_equity=b.day_start_equity,
                high_watermark=max(b.prior_high_watermark, anchor.equity_krw),
                observed_daily_loss=b.observed_daily_loss, realized_net_total_krw=anchor.realized_net_total_krw,
                day_open_realized_net_total_krw=anchor.day_open_realized_net_total_krw,
                previous_day_realized_net_krw=anchor.previous_day_realized_net_krw,
                approved_effective_floor=b.approved_effective_floor,
                anchor_sha256=content_digest(anchor), previous_state_digest="", last_interval_digest="")
            cutoff = _required_cutoff(state)
            checkpoint = (RecoveryCheckpoint(cutoff_at=cutoff, equity_krw=anchor.equity_krw,
                          source_sha256=b.source_sha256) if cutoff is not None and b.asof == cutoff else None)
            _require(b.recovery_checkpoint is None
                     or (type(b.recovery_checkpoint) is RecoveryCheckpoint and b.recovery_checkpoint == checkpoint),
                     "BASELINE_RECOVERY_ANCHOR_REFUSED")
            if checkpoint is not None:
                state = _state(**{field.name: (checkpoint if field.name == "recovery_checkpoint"
                                  else getattr(state, field.name)) for field in fields(BaselineState)
                                  if field.name != "state_digest"})
            _validate(state)
            return state
    except BaselineError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError):
        raise BaselineError("BASELINE_SCHEMA_OR_ARITHMETIC_INVALID") from None


def advance_baseline(state: BaselineState, interval: BaselineInterval) -> BaselineState:
    """Advance once; identical redelivery is idempotent and cannot refresh time."""
    try:
        with localcontext() as numeric:
            numeric.prec = 512; numeric.traps[Inexact] = True
            _validate(state)
            _require(type(interval) is BaselineInterval, "BASELINE_INTERVAL_REQUIRED")
            _instant(interval.start); _instant(interval.end)
            _hash(interval.previous_state_digest); _hash(interval.source_sha256); _hash(interval.coverage_sha256)
            _require(type(interval.account_scope) is str and interval.account_scope == state.account_scope,
                     "BASELINE_SCOPE_MISMATCH")
            _require(type(interval.sequence) is int and 0 <= interval.sequence < 2**63,
                     "BASELINE_SEQUENCE_INVALID")
            for name in ("equity_krw", "minimum_equity_krw", "maximum_equity_krw"):
                _amount(getattr(interval, name), positive=True)
            _amount(interval.realized_net_total_krw, signed=True)
            _require(interval.gross_external_inflows_krw is not None
                     and interval.gross_external_outflows_krw is not None,
                     "BASELINE_EXTERNAL_FLOW_COVERAGE_REQUIRED")
            _amount(interval.gross_external_inflows_krw); _amount(interval.gross_external_outflows_krw)
            _require(interval.gross_external_inflows_krw == 0 and interval.gross_external_outflows_krw == 0,
                     "BASELINE_EXTERNAL_FLOW_UNSUPPORTED")
            interval_sha = content_digest(interval)
            if interval.sequence == state.sequence:
                _require(interval_sha == state.last_interval_digest and interval.end == state.asof,
                         "BASELINE_DUPLICATE_CONTRADICTION")
                return state
            _require(interval.sequence == state.sequence+1 and interval.previous_state_digest == state.state_digest,
                     "BASELINE_CHAIN_GAP_OR_ROLLBACK")
            _require(interval.start == state.asof and timedelta(0) < interval.end-interval.start
                     <= timedelta(seconds=state.conventions.max_interval_seconds),
                     "BASELINE_TIME_GAP_OR_ROLLBACK")
            _require(interval.minimum_equity_krw <= min(state.equity_krw, interval.equity_krw)
                     and interval.maximum_equity_krw >= max(state.equity_krw, interval.equity_krw),
                     "BASELINE_INTERVAL_EXTREMA_CONTRADICTION")
            old_day, new_day = state.asof.astimezone(KST).date(), interval.end.astimezone(KST).date()
            next_open = datetime.combine(old_day+timedelta(days=1), time(), tzinfo=KST)
            _require(new_day == old_day or interval.end == next_open,
                     "BASELINE_MIDNIGHT_OPENING_REQUIRED")
            rollover = new_day != old_day
            cutoff = _required_cutoff(state)
            _require(cutoff is None or not (state.asof < cutoff < interval.end),
                     "BASELINE_RECOVERY_BOUNDARY_REQUIRED")
            checkpoint = None if rollover else state.recovery_checkpoint
            if cutoff is not None and interval.end == cutoff:
                checkpoint = RecoveryCheckpoint(cutoff_at=cutoff, equity_krw=interval.equity_krw,
                                                source_sha256=interval.source_sha256)
            opening = interval.equity_krw if rollover else state.day_start_equity
            loss = (_ZERO if rollover else
                    max(state.observed_daily_loss, opening-interval.minimum_equity_krw, _ZERO))
            out = _state(schema_version=state.schema_version, account_scope=state.account_scope, conventions=state.conventions,
                first_trading_day=state.first_trading_day, asof=interval.end, sequence=interval.sequence,
                equity_krw=interval.equity_krw, day_start_equity=opening,
                high_watermark=max(state.high_watermark, interval.maximum_equity_krw), observed_daily_loss=loss,
                realized_net_total_krw=interval.realized_net_total_krw,
                day_open_realized_net_total_krw=(interval.realized_net_total_krw if rollover
                                               else state.day_open_realized_net_total_krw),
                previous_day_realized_net_krw=(interval.realized_net_total_krw-state.day_open_realized_net_total_krw
                                               if rollover else state.previous_day_realized_net_krw),
                approved_effective_floor=state.approved_effective_floor, anchor_sha256=state.anchor_sha256,
                previous_state_digest=state.state_digest, last_interval_digest=interval_sha,
                recovery_checkpoint=checkpoint)
            _validate(out)
            return out
    except BaselineError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError):
        raise BaselineError("BASELINE_SCHEMA_OR_ARITHMETIC_INVALID") from None


def risk_baseline(state: BaselineState, *, now: datetime, expected_head: str) -> RiskBaseline:
    """Export the observed timestamp unchanged; refuse stale or untrusted checkpoints."""
    try:
        with localcontext() as numeric:
            numeric.prec = 512; numeric.traps[Inexact] = True
            _validate(state); _instant(now); _hash(expected_head)
            _require(state.state_digest == expected_head, "BASELINE_CHECKPOINT_MISMATCH")
            _require(timedelta(0) <= now-state.asof <= timedelta(seconds=30)
                     and now.astimezone(KST).date() == state.asof.astimezone(KST).date(),
                     "BASELINE_STALE_OR_FUTURE")
            cutoff = _required_cutoff(state)
            _require(cutoff is None or not (state.asof < cutoff <= now),
                     "BASELINE_RECOVERY_BOUNDARY_REQUIRED")
            return RiskBaseline(day_start_equity=state.day_start_equity, prior_high_watermark=state.high_watermark,
                observed_daily_loss=state.observed_daily_loss, approved_effective_floor=state.approved_effective_floor,
                first_trading_day=state.first_trading_day, asof=state.asof, source_sha256=state.state_digest,
                recovery_checkpoint=state.recovery_checkpoint)
    except BaselineError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError):
        raise BaselineError("BASELINE_SCHEMA_OR_ARITHMETIC_INVALID") from None


def state_json(state: BaselineState) -> str:
    """Private checkpoint serialization, containing account amounts; caller owns storage."""
    with localcontext() as numeric:
        numeric.prec = 512; numeric.traps[Inexact] = True
        _validate(state)
        body = canonical(state)
        if state.schema_version == 1:
            body.pop("recovery_checkpoint")
            body["conventions"].pop("recovery_cutoff_seconds")
        return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def restore_state(raw: str | bytes, *, expected_head: str) -> BaselineState:
    """Verify against the separately retained expected head; never infer the latest state."""
    try:
        _hash(expected_head)
        _require(type(raw) in (str, bytes) and len(raw) <= 65536, "BASELINE_CHECKPOINT_TOO_LARGE")
        def pairs(items):
            out = {}
            for key, value in items:
                _require(key not in out, "BASELINE_DUPLICATE_JSON_KEY")
                out[key] = value
            return out
        def bad_number(value):
            raise BaselineError("BASELINE_CHECKPOINT_NUMBER_INVALID")
        body = json.loads(raw, object_pairs_hook=pairs, parse_float=bad_number, parse_constant=bad_number)
        _require(type(body) is dict and type(body.get("schema_version")) is int
                 and body["schema_version"] in (1, 2), "BASELINE_CHECKPOINT_SCHEMA_INVALID")
        legacy = body["schema_version"] == 1
        state_fields = {f.name for f in fields(BaselineState)}
        convention_fields = {f.name for f in fields(BaselineConventions)}
        if legacy:
            state_fields.remove("recovery_checkpoint")
            convention_fields.remove("recovery_cutoff_seconds")
        _require(set(body) == state_fields,
                 "BASELINE_CHECKPOINT_SCHEMA_INVALID")
        convention = body["conventions"]
        _require(type(convention) is dict and set(convention) == convention_fields,
                 "BASELINE_CHECKPOINT_SCHEMA_INVALID")
        body["conventions"] = BaselineConventions(**convention)
        _require(type(body["asof"]) is str and type(body["first_trading_day"]) is str,
                 "BASELINE_CHECKPOINT_SCHEMA_INVALID")
        body["asof"] = datetime.fromisoformat(body["asof"])
        body["first_trading_day"] = date.fromisoformat(body["first_trading_day"])
        for name in ("equity_krw", "day_start_equity", "high_watermark", "observed_daily_loss",
                     "realized_net_total_krw", "day_open_realized_net_total_krw",
                     "previous_day_realized_net_krw", "approved_effective_floor"):
            value = body[name]
            if value is None and name in ("previous_day_realized_net_krw", "approved_effective_floor"):
                continue
            _require(type(value) is str and len(value) <= 128 and _NUMBER.fullmatch(value) is not None,
                     "BASELINE_CHECKPOINT_NUMBER_INVALID")
            body[name] = Decimal(value)
        if not legacy and body["recovery_checkpoint"] is not None:
            checkpoint = body["recovery_checkpoint"]
            _require(type(checkpoint) is dict and set(checkpoint) == {f.name for f in fields(RecoveryCheckpoint)}
                     and type(checkpoint["cutoff_at"]) is str, "BASELINE_CHECKPOINT_SCHEMA_INVALID")
            value = checkpoint["equity_krw"]
            _require(type(value) is str and len(value) <= 128 and _NUMBER.fullmatch(value) is not None,
                     "BASELINE_CHECKPOINT_NUMBER_INVALID")
            body["recovery_checkpoint"] = RecoveryCheckpoint(cutoff_at=datetime.fromisoformat(checkpoint["cutoff_at"]),
                equity_krw=Decimal(value), source_sha256=checkpoint["source_sha256"])
        state = BaselineState(**body)
        with localcontext() as numeric:
            numeric.prec = 512; numeric.traps[Inexact] = True
            _validate(state)
        _require(state.state_digest == expected_head, "BASELINE_CHECKPOINT_MISMATCH")
        return state
    except BaselineError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError, UnicodeError, RecursionError):
        raise BaselineError("BASELINE_CHECKPOINT_SCHEMA_INVALID") from None
