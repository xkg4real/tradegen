"""Pure, versioned first-trade profile parsing and prerequisite diagnostics.

A complete profile is configuration, not proof of account access or permission to
trade. Inputs are explicit; no file, environment, credential, owner-log, wall-clock
or network access occurs here. The existing owner fold remains the authority for
signed limits and their delayed effective dates.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import math
import re

from core.compliance import model as compliance
from execution_control.model import InstrumentRules, decimal_text, rules_digest
from execution_control.risk import RiskPolicy

MAX_PROFILE_BYTES = 65536
_SCHEMA_VERSION = 1
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:/-]{0,127}")
_INSTRUMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")
_SCOPE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")
_SHA = re.compile(r"[0-9a-f]{64}")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_POLICY_NUMBERS = ("initial_equity", "drawdown_activation_equity", "positive_profit_loss_fraction",
                   "peak_drawdown_fraction", "zero_profit_day_target_fraction",
                   "first_day_loss_budget", "zero_profit_day_loss_budget")
_CONVENTIONS = {
    "valuation": "marked_equity",
    "daily_loss": "externally_reconciled",
    "external_flows": "externally_cashflow_adjusted",
    "realized_profit": "fifo_all_fees_krw",
    "fx": "current_marks_execution_time_fills",
    "rounding": "fifo_floor_18dp_remainder_to_final",
    "day_boundary": "Asia/Seoul",
    "first_day_scope": "first_trading_day_only",
}


class ProfileError(ValueError):
    """Fixed error code and known field path; no raw profile values are echoed."""
    def __init__(self, code: str, field: str = "profile"):
        self.code, self.field = code, field
        super().__init__(code + ": " + field)


@dataclass(frozen=True, kw_only=True)
class PolicyInputs:
    version: str | None = None
    source_sha256: str | None = None
    initial_equity: Decimal | None = None
    drawdown_activation_equity: Decimal | None = None
    positive_profit_loss_fraction: Decimal | None = None
    peak_drawdown_fraction: Decimal | None = None
    zero_profit_day_target_fraction: Decimal | None = None
    first_day_loss_budget: Decimal | None = None
    zero_profit_day_loss_budget: Decimal | None = None


@dataclass(frozen=True, kw_only=True)
class AccountingConventions:
    valuation: str | None = None
    daily_loss: str | None = None
    external_flows: str | None = None
    realized_profit: str | None = None
    fx: str | None = None
    rounding: str | None = None
    day_boundary: str | None = None
    first_day_scope: str | None = None


@dataclass(frozen=True, kw_only=True)
class LaunchProfile:
    schema_version: int
    profile_id: str
    venue: str | None = None
    account_scope: str | None = None
    market: str | None = None
    symbol: str | None = None
    quote_currency: str | None = None
    time_in_force: str | None = None
    policy: PolicyInputs = PolicyInputs()
    conventions: AccountingConventions = AccountingConventions()
    instrument_rules: InstrumentRules | None = None
    strategy_id: str | None = None
    strategy_code_sha256: str | None = None

    def __post_init__(self):
        _validate_profile(self)


@dataclass(frozen=True, kw_only=True)
class ProfileIssue:
    code: str
    field: str
    action: str


@dataclass(frozen=True, kw_only=True)
class PreflightReport:
    profile_complete: bool
    prerequisites_ready: bool
    profile_digest: str
    issues: tuple[ProfileIssue, ...]
    execution_ready: bool = False

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(issue.code for issue in self.issues)


def _known_object(value, allowed, field):
    if type(value) is not dict or any(type(k) is not str for k in value) or set(value)-set(allowed):
        raise ProfileError("PROFILE_SCHEMA_INVALID", field)
    return value


def _text(value, field, pattern=_ID):
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ProfileError("PROFILE_TEXT_INVALID", field)
    return value


def _amount(value, field):
    if (type(value) is not Decimal or not value.is_finite() or value < 0
            or len(value.as_tuple().digits) > 60 or abs(value.as_tuple().exponent) > 40):
        raise ProfileError("PROFILE_DECIMAL_INVALID", field)
    return value


def _parse_amount(value, field):
    if value is None:
        return None
    if type(value) is not str or len(value) > 102 or _DECIMAL.fullmatch(value) is None:
        raise ProfileError("PROFILE_DECIMAL_STRING_REQUIRED", field)
    return _amount(Decimal(value), field)


def _aware(value, field):
    try:
        if type(value) is not datetime or value.utcoffset() is None:
            raise ValueError
        value.astimezone(timezone.utc)
        value.astimezone(compliance.KST)
    except (TypeError, ValueError, OverflowError):
        raise ProfileError("PROFILE_AWARE_TIME_REQUIRED", field)
    return value


def _validate_profile(profile):
    if type(profile) is not LaunchProfile or type(profile.schema_version) is not int or profile.schema_version != 1:
        raise ProfileError("PROFILE_VERSION_UNSUPPORTED")
    _text(profile.profile_id, "profile_id")
    for name in ("venue", "market", "symbol", "quote_currency", "time_in_force", "strategy_id"):
        value = getattr(profile, name)
        if value is not None:
            _text(value, name, _INSTRUMENT if name == "symbol" else _ID)
    if profile.account_scope is not None:
        _text(profile.account_scope, "account_scope", _SCOPE)
    if profile.strategy_code_sha256 is not None:
        _text(profile.strategy_code_sha256, "strategy_code_sha256", _SHA)
    if type(profile.policy) is not PolicyInputs or type(profile.conventions) is not AccountingConventions:
        raise ProfileError("PROFILE_SCHEMA_INVALID")
    for name in ("version", "source_sha256"):
        value = getattr(profile.policy, name)
        if value is not None:
            _text(value, "policy."+name, _SHA if name == "source_sha256" else _ID)
    for name in _POLICY_NUMBERS:
        value = getattr(profile.policy, name)
        if value is not None:
            _amount(value, "policy."+name)
    for name in _CONVENTIONS:
        value = getattr(profile.conventions, name)
        if value is not None:
            _text(value, "conventions."+name)
    if profile.instrument_rules is not None:
        try:
            rules_digest(profile.instrument_rules)
            for name in ("lot_size", "tick_size", "min_quantity", "min_notional_krw", "fee_fraction"):
                _amount(getattr(profile.instrument_rules, name), "instrument_rules."+name)
        except (TypeError, ValueError, AttributeError, ArithmeticError):
            raise ProfileError("PROFILE_INSTRUMENT_RULES_INVALID", "instrument_rules") from None


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ProfileError("PROFILE_DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _no_json_float(value):
    raise ProfileError("PROFILE_JSON_NUMBERS_REQUIRE_DECIMAL_STRINGS")


def parse_profile_json(raw: str | bytes) -> LaunchProfile:
    """Read bounded explicit JSON only; unknown fields and ambiguous numbers fail.

    Missing/null decision fields remain None and are listed by preflight. Monetary
    values and fractions use decimal strings; schema_version is the sole integer.
    """
    if type(raw) not in (str, bytes):
        raise ProfileError("PROFILE_JSON_REQUIRED")
    try:
        encoded = raw.encode("utf-8") if type(raw) is str else raw
        if len(encoded) > MAX_PROFILE_BYTES:
            raise ProfileError("PROFILE_JSON_TOO_LARGE")
        value = json.loads(encoded.decode("utf-8"), object_pairs_hook=_unique,
                           parse_float=_no_json_float, parse_constant=_no_json_float)
        value = _known_object(value, (f.name for f in fields(LaunchProfile)), "profile")
        policy = _known_object(value.get("policy", {}), (f.name for f in fields(PolicyInputs)), "policy")
        conventions = _known_object(value.get("conventions", {}), _CONVENTIONS, "conventions")
        policy = PolicyInputs(**{key: _parse_amount(item, "policy."+key) if key in _POLICY_NUMBERS else item
                                for key, item in policy.items()})
        rules = value.get("instrument_rules")
        if rules is not None:
            rules = _known_object(rules, (f.name for f in fields(InstrumentRules)), "instrument_rules")
            if set(rules) != {f.name for f in fields(InstrumentRules)}:
                raise ProfileError("PROFILE_INSTRUMENT_RULES_INCOMPLETE", "instrument_rules")
            converted = {}
            for key, item in rules.items():
                if key in ("lot_size", "tick_size", "min_quantity", "min_notional_krw", "fee_fraction"):
                    item = _parse_amount(item, "instrument_rules."+key)
                elif key == "asof":
                    if type(item) is not str:
                        raise ProfileError("PROFILE_AWARE_TIME_REQUIRED", "instrument_rules.asof")
                    item = _aware(datetime.fromisoformat(item), "instrument_rules.asof")
                converted[key] = item
            rules = InstrumentRules(**converted)
        args = {k: v for k, v in value.items() if k not in ("policy", "conventions", "instrument_rules")}
        return LaunchProfile(**args, policy=policy, conventions=AccountingConventions(**conventions), instrument_rules=rules)
    except ProfileError:
        raise
    except (UnicodeError, TypeError, ValueError, AttributeError, ArithmeticError, RecursionError):
        raise ProfileError("PROFILE_JSON_OR_SCHEMA_INVALID") from None


def profile_body(profile: LaunchProfile) -> dict:
    """Detached canonical values for private storage; this contains private inputs."""
    _validate_profile(profile)
    body = {f.name: getattr(profile, f.name) for f in fields(LaunchProfile)
            if f.name not in ("policy", "conventions", "instrument_rules")}
    body["policy"] = {f.name: decimal_text(v) if type(v := getattr(profile.policy, f.name)) is Decimal else v
                      for f in fields(PolicyInputs)}
    body["conventions"] = {f.name: getattr(profile.conventions, f.name) for f in fields(AccountingConventions)}
    rules = profile.instrument_rules
    body["instrument_rules"] = None if rules is None else {
        f.name: decimal_text(v) if type(v := getattr(rules, f.name)) is Decimal else
        v.astimezone(timezone.utc).isoformat(timespec="microseconds") if type(v) is datetime else v
        for f in fields(InstrumentRules)}
    return body


def profile_digest(profile: LaunchProfile) -> str:
    raw = json.dumps(profile_body(profile), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()



def rule_terms_digest(rules: InstrumentRules) -> str:
    """Stable economic rule identity; refresh time is checked separately by E2.

    The source digest and every lot/tick/minimum/fee/scope term remain bound.
    Only the observation's asof timestamp is omitted for prospective evidence.
    """
    try:
        rules_digest(rules)
    except (TypeError, ValueError, AttributeError, ArithmeticError):
        raise ProfileError("PROFILE_INSTRUMENT_RULES_INVALID", "instrument_rules") from None
    body = {f.name: decimal_text(v) if type(v := getattr(rules, f.name)) is Decimal else v
            for f in fields(InstrumentRules) if f.name != "asof"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def profile_contract_digest(profile: LaunchProfile) -> str:
    """Stable owner/strategy/economic contract for prospective qualification.

    This is not the complete runtime snapshot digest. Current asof is deliberately
    excluded so fresh identical rules do not invalidate multi-day research. The
    controller still enforces the full current rules_digest and five-minute age.
    """
    body = profile_body(profile)
    if body["instrument_rules"] is not None:
        del body["instrument_rules"]["asof"]
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _configuration_issues(profile, now):
    issues = []
    def add(code, field, action):
        issues.append(ProfileIssue(code=code, field=field, action=action))
    for name in ("venue", "account_scope", "market", "symbol", "quote_currency", "time_in_force",
                 "strategy_id", "strategy_code_sha256"):
        if getattr(profile, name) is None:
            add("PROFILE_FIELD_REQUIRED", name, "Choose and review this explicit launch-profile field.")
    venue, market, symbol, quote = profile.venue, profile.market, profile.symbol, profile.quote_currency
    markets = {"upbit": ("spot",), "okx": ("spot",), "kis": ("krx", "nasd", "nyse", "amex")}
    if venue is not None and venue not in markets:
        add("VENUE_UNSUPPORTED", "venue", "Select a supported cash venue.")
    if venue in markets and market is not None and market not in markets[venue]:
        add("MARKET_VENUE_MISMATCH", "market", "Use a supported cash market for the chosen venue.")
    if venue in markets and market in markets[venue]:
        expected_tif = "day" if venue == "kis" else "gtc"
        if profile.time_in_force is not None and profile.time_in_force != expected_tif:
            add("TIME_IN_FORCE_MISMATCH", "time_in_force", "Use the supported time in force for this venue.")
        pattern = (r"KRW-[A-Z0-9]{1,20}" if venue == "upbit" else r"[A-Z0-9]{1,20}-(?:USDT|USDC)"
                   if venue == "okx" else r"[0-9]{6}" if market == "krx" else r"[A-Z][A-Z0-9.-]{0,14}")
        if symbol is not None and re.fullmatch(pattern, symbol) is None:
            add("SYMBOL_VENUE_MISMATCH", "symbol", "Use the venue's supported exact instrument identifier.")
        expected_quote = ("KRW" if venue == "upbit" or (venue == "kis" and market == "krx") else
                          "USD" if venue == "kis" else symbol.rsplit("-", 1)[-1] if symbol else None)
        if quote is not None and expected_quote is not None and quote != expected_quote:
            add("QUOTE_CURRENCY_MISMATCH", "quote_currency", "Bind the actual settlement currency of the instrument.")
    policy = profile.policy
    for field in fields(PolicyInputs):
        if getattr(policy, field.name) is None:
            add("POLICY_INPUT_REQUIRED", "policy."+field.name,
                "Obtain this explicit owner policy choice; missing does not mean zero or unlimited.")
    if policy.initial_equity is not None and policy.initial_equity <= 0:
        add("PRINCIPAL_MUST_BE_POSITIVE", "policy.initial_equity", "Supply a positive original principal.")
    if (policy.initial_equity is not None and policy.drawdown_activation_equity is not None
            and policy.drawdown_activation_equity < policy.initial_equity):
        add("ACTIVATION_BELOW_PRINCIPAL", "policy.drawdown_activation_equity", "Review inconsistent policy thresholds.")
    for name, upper_inclusive in (("positive_profit_loss_fraction", True), ("peak_drawdown_fraction", False)):
        value = getattr(policy, name)
        if value is not None and (value > 1 if upper_inclusive else value >= 1):
            add("POLICY_FRACTION_OUT_OF_RANGE", "policy."+name, "Review the permitted fraction range.")
    for name, expected in _CONVENTIONS.items():
        value = getattr(profile.conventions, name)
        if value is None:
            add("ACCOUNTING_CONVENTION_REQUIRED", "conventions."+name, "Review and explicitly choose the accounting convention.")
        elif value != expected:
            add("ACCOUNTING_CONVENTION_UNSUPPORTED", "conventions."+name,
                "Implement and verify the chosen convention before using this profile.")
    rules = profile.instrument_rules
    if rules is None:
        add("INSTRUMENT_RULES_REQUIRED", "instrument_rules", "Collect exact current lot, tick, fee and minimum rules with provenance.")
    else:
        if (rules.venue, rules.market, rules.symbol) != (venue, market, symbol):
            add("INSTRUMENT_RULES_SCOPE_MISMATCH", "instrument_rules", "Collect rules for this exact venue/market/instrument.")
        if not timedelta(0) <= now-rules.asof <= timedelta(minutes=5):
            add("INSTRUMENT_RULES_STALE_OR_FUTURE", "instrument_rules.asof", "Refresh the instrument rules before preparation.")
    return issues


def risk_policy(profile: LaunchProfile) -> RiskPolicy:
    """Construct the existing policy without introducing new monetary defaults.

    This conversion checks policy/conventions only. Full scope, rule freshness,
    signed state, account evidence and strategy gates remain separate.
    """
    _validate_profile(profile)
    policy = profile.policy
    if any(getattr(policy, f.name) is None for f in fields(PolicyInputs)):
        raise ProfileError("POLICY_INPUTS_INCOMPLETE", "policy")
    if any(getattr(profile.conventions, name) != value for name, value in _CONVENTIONS.items()):
        raise ProfileError("ACCOUNTING_CONVENTIONS_INCOMPLETE_OR_UNSUPPORTED", "conventions")
    if (policy.initial_equity <= 0 or policy.drawdown_activation_equity < policy.initial_equity
            or not 0 <= policy.positive_profit_loss_fraction <= 1 or not 0 <= policy.peak_drawdown_fraction < 1):
        raise ProfileError("POLICY_INPUTS_INCONSISTENT", "policy")
    return RiskPolicy(version=policy.version, **{name: getattr(policy, name) for name in _POLICY_NUMBERS},
                      valuation_convention=profile.conventions.valuation,
                      daily_loss_convention=profile.conventions.daily_loss)


def preflight_profile(profile: LaunchProfile, *, now: datetime, context=None) -> PreflightReport:
    """Report configuration and supplied signed-context prerequisites, never a permit.

    A freshly loaded sealed Context already folds D12. First/looser limits apply
    only from a later Seoul date and cannot be inferred from a submitted form.
    This function neither loads that context nor certifies its external source.
    """
    _validate_profile(profile); _aware(now, "now")
    issues = _configuration_issues(profile, now)
    complete = not issues
    def add(code, field, action):
        issues.append(ProfileIssue(code=code, field=field, action=action))
    if context is None:
        add("SIGNED_CONTEXT_REQUIRED", "owner", "Load a fresh verified owner context in the owner's execution environment.")
    else:
        try:
            intact = (type(context) is compliance.Context and compliance.is_sealed(context)
                      and type(context.date) is date
                      and type(context.owner) is compliance.OwnerState
                      and isinstance(context.owner.limits, Mapping)
                      and type(context.active) is compliance.ApprovedState
                      and context.ctx_hash == compliance.sha256_hex(compliance.canonical_json({
                          f.name: getattr(context, f.name) for f in fields(compliance.Context) if f.name != "ctx_hash"})))
        except (TypeError, ValueError, AttributeError, ArithmeticError, RecursionError):
            intact = False
        if not intact:
            add("SIGNED_CONTEXT_INVALID", "owner", "Reload the intact context through the existing verified owner workflow.")
        else:
            if context.date != now.astimezone(compliance.KST).date():
                add("SIGNED_CONTEXT_WRONG_SEOUL_DAY", "owner", "Reload today's effective signed owner state.")
            if context.code_signed is not True or not context.owner.ok or context.active.valid is not True:
                add("OWNER_APPROVALS_INCOMPLETE", "owner", "Review and sign the final code and required rule tables.")
            if context.owner.halted_floors:
                add("OWNER_HALT_PRESENT", "owner", "Resolve the existing halt through the reviewed recovery procedure.")
            for key in ("total_loss_floor_krw", "daily_loss_krw"):
                value = context.owner.limits.get(key)
                try:
                    valid = type(value) in (int, float) and math.isfinite(value) and (value > 0 if key == "daily_loss_krw" else value >= 0)
                except (ValueError, OverflowError):
                    valid = False
                if not valid:
                    add("SIGNED_LIMIT_NOT_EFFECTIVE", "owner."+key,
                        "Check the signed limit's effective Seoul date; first and looser settings are deferred by D12.")
                elif (key == "total_loss_floor_krw" and profile.policy.initial_equity is not None
                      and Decimal(str(value)) < profile.policy.initial_equity):
                    add("SIGNED_PRINCIPAL_FLOOR_TOO_LOW", "owner."+key, "Review the effective principal-protection floor.")
    return PreflightReport(profile_complete=complete, prerequisites_ready=not issues,
                           profile_digest=profile_digest(profile), issues=tuple(issues))


def limit_change_earliest_date(*, key: str, previous: Decimal | None, proposed: Decimal,
                               signed_at: datetime) -> date:
    """Scheduling advisory only; verified owner-log order, halts and arming still govern.

    A first setting is a loosening. Tightening/equality may apply immediately;
    looser settings cannot apply before the following Asia/Seoul calendar date.
    """
    if key not in ("total_loss_floor_krw", "daily_loss_krw", "okx_equity_share"):
        raise ProfileError("SIGNED_LIMIT_KEY_UNSUPPORTED", "key")
    _amount(proposed, "proposed"); _aware(signed_at, "signed_at")
    if previous is not None:
        _amount(previous, "previous")
        if ((key == "daily_loss_krw" and previous <= 0)
                or (key == "okx_equity_share" and not 0 < previous <= 1)):
            raise ProfileError("SIGNED_LIMIT_VALUE_INVALID", "previous")
    if (key == "daily_loss_krw" and proposed <= 0) or (key == "okx_equity_share" and not 0 < proposed <= 1):
        raise ProfileError("SIGNED_LIMIT_VALUE_INVALID", "proposed")
    tighter = previous is not None and (proposed >= previous if key == "total_loss_floor_krw" else proposed <= previous)
    return signed_at.astimezone(compliance.KST).date() + timedelta(days=0 if tighter else 1)
