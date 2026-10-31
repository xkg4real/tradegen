"""Immutable normalized account evidence; provenance hashes are not signatures.

An authenticated collector or audited broker import must establish the source
identity and opening cash anchor. These types never manufacture that authority.
Cursor chains make pagination claims inspectable instead of accepting a bare
``complete=True`` flag. Decimal strings must be decoded before constructing them.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json


def canonical(value):
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: canonical(getattr(value, f.name)) for f in fields(value)}
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("nonfinite evidence number")
        return format(value, "f")
    if type(value) is datetime:
        if value.utcoffset() is None:
            raise ValueError("aware evidence time required")
        return value.astimezone(timezone.utc).isoformat()
    if type(value) is date:
        return value.isoformat()
    if type(value) is tuple:
        return [canonical(v) for v in value]
    if value is None or type(value) in (str, bool, int):
        return value
    raise ValueError("unsupported evidence value")


def content_digest(value) -> str:
    raw = json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, kw_only=True)
class CashAmount:
    currency: str
    amount: Decimal


@dataclass(frozen=True, kw_only=True)
class CashBalance:
    currency: str
    total: Decimal
    settled: Decimal


@dataclass(frozen=True, kw_only=True)
class FxRate:
    currency: str
    krw: Decimal
    asof: datetime
    source_sha256: str


@dataclass(frozen=True, kw_only=True)
class Position:
    market: str
    symbol: str
    base_currency: str
    quote_currency: str
    units: Decimal
    price: Decimal
    asof: datetime


@dataclass(frozen=True, kw_only=True)
class ExternalFlow:
    flow_id: str
    currency: str
    kind: str
    amount: Decimal
    effective_at: datetime


@dataclass(frozen=True, kw_only=True)
class BrokerOrder:
    client_id: str
    order_id: str
    market: str
    symbol: str
    side: str
    quote_currency: str
    quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    limit_price: Decimal
    reserved_cash: Decimal
    status: str
    cancelable_quantity: Decimal | None = None
    order_date: str = ""
    broker_org_id: str = ""


@dataclass(frozen=True, kw_only=True)
class EvidencePage:
    kind: str
    cursor: str | None
    next_cursor: str | None
    start: datetime
    end: datetime
    rows: tuple
    source_sha256: str
    page_sha256: str = ""

    def __post_init__(self):
        object.__setattr__(self, "rows", tuple(self.rows))
        if not self.page_sha256:
            object.__setattr__(self, "page_sha256", page_digest(self))


def page_digest(page: EvidencePage) -> str:
    return content_digest(tuple(getattr(page, f.name) for f in fields(page) if f.name != "page_sha256"))


@dataclass(frozen=True, kw_only=True)
class AccountRestrictions:
    cash_mode: str
    borrowing_enabled: bool
    auto_loan: bool
    liabilities: tuple[CashAmount, ...]
    asof: datetime
    source_sha256: str

    def __post_init__(self):
        object.__setattr__(self, "liabilities", tuple(self.liabilities))


@dataclass(frozen=True, kw_only=True)
class MarketTradeDate:
    market: str
    trade_date: str
    asof: datetime
    source_sha256: str


@dataclass(frozen=True, kw_only=True)
class AccountEvidence:
    venue: str
    account_scope: str
    execution_quote: str
    origin: datetime
    opening_cash: tuple[CashAmount, ...]
    opening_source_sha256: str
    balances: tuple[CashBalance, ...]
    positions: tuple[Position, ...]
    fx: tuple[FxRate, ...]
    pages: tuple[EvidencePage, ...]
    restrictions: AccountRestrictions
    observed_at: datetime
    server_time: datetime
    trade_dates: tuple[MarketTradeDate, ...] = ()

    def __post_init__(self):
        for name in ("opening_cash", "balances", "positions", "fx", "pages", "trade_dates"):
            object.__setattr__(self, name, tuple(getattr(self, name)))


@dataclass(frozen=True, kw_only=True)
class RiskBaseline:
    day_start_equity: Decimal
    prior_high_watermark: Decimal
    observed_daily_loss: Decimal
    approved_effective_floor: Decimal | None
    first_trading_day: date
    asof: datetime
    source_sha256: str


@dataclass(frozen=True, kw_only=True)
class AccountBundle:
    accounts: tuple[AccountEvidence, ...]
    risk_baseline: RiskBaseline

    def __post_init__(self):
        object.__setattr__(self, "accounts", tuple(self.accounts))


@dataclass(frozen=True, kw_only=True)
class EvidenceAssessment:
    account_evidence_ready: bool
    execution_ready: bool
    reasons: tuple[str, ...]
    account_count: int
    fill_count: int
