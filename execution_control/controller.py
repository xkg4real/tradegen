"""Durable, exact-amount admission and one-attempt execution coordination.

All dependencies are explicit. Nothing here supplies credentials, signs an owner
entry, arms a session, or starts a background process. A journal recovered after a
send-in-progress never causes a repeated create request.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext, Inexact
import math
import re
from types import MappingProxyType
from functools import wraps

from core.compliance import gate, model as compliance, owner
from execution_control import risk
from execution_control.capability import _issue, digest, plain
from execution_control.model import Order, InstrumentRules, order_body, order_digest, validate_order
from execution_control.session import PreparedSession, verify_session
from execution_orders.model import AdapterResult, request_digest, validate_request

_ACTIVE = frozenset({'RESERVED', 'DISPATCHING', 'ACKNOWLEDGED', 'UNKNOWN', 'PARTIAL', 'CANCEL_REQUESTED'})
_TERMINAL = frozenset({'REJECTED', 'EXPIRED', 'CANCELLED_LOCAL', 'FILLED', 'CANCELED'})
_ORDER_EVENTS = frozenset({'reserved', 'dispatching', 'acknowledged', 'rejected', 'unknown', 'expired',
                          'cancelled_local', 'cancel_requested', 'reconciled', 'fill'})


@dataclass(frozen=True, kw_only=True)
class AccountObservation:
    positions: compliance.Positions
    account_scopes: Mapping[str, str]
    settled_cash_krw: Mapping[tuple[str, str], Decimal]
    holdings: Mapping[tuple[str, str, str, str], Decimal]
    risk: risk.RiskObservation
    asof: datetime
    server_time: datetime
    no_credit: bool
    fills: tuple = ()
    reconciled_client_ids: frozenset[str] = frozenset()
    venue_trade_dates: Mapping[tuple[str, str, str], str] = field(default_factory=dict)
    cancellable_quantities: Mapping[str, Decimal] = field(default_factory=dict)
    held_exposure_krw: Mapping[tuple[str,str], Decimal] = field(default_factory=dict)
    quote_currency_by_account: Mapping[tuple[str, str], str] = field(default_factory=dict)
    inventory_exposure_krw: Mapping[tuple[str, str], Decimal] = field(default_factory=dict)
    quote_rates_krw: Mapping[tuple[str, str, str], Decimal] = field(default_factory=dict)

    def __post_init__(self):
        for name in ('account_scopes', 'settled_cash_krw', 'holdings', 'venue_trade_dates', 'cancellable_quantities', 'held_exposure_krw', 'quote_currency_by_account', 'inventory_exposure_krw', 'quote_rates_krw'):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        object.__setattr__(self, 'fills', tuple(self.fills))
        object.__setattr__(self, 'reconciled_client_ids', frozenset(self.reconciled_client_ids))


@dataclass(frozen=True, kw_only=True)
class OrderState:
    client_id: str
    status: str
    order_digest: str
    venue_order_id: str = ''
    filled_quantity: Decimal = Decimal(0)


def _exact(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        with localcontext() as numeric:
            numeric.prec=2048
            numeric.traps[Inexact]=True
            return method(*args, **kwargs)
    return wrapped


def _fill_key(fill):
    identity=(fill.venue,fill.account_scope,fill.order_id,fill.fill_id)
    if fill.venue=='kis':
        identity+=(fill.market,fill.order_date,fill.broker_org_id)
    return digest(identity)


def _broker_key(obj,trade_date,venue_id,metadata):
    if type(venue_id) is not str or not venue_id:
        raise ValueError('broker identity required')
    if obj.venue!='kis':
        return (obj.venue,obj.account_scope,venue_id)
    _trade_date(trade_date)
    org=metadata.get('broker_org_id','')
    if (type(org) is not str or (org and re.fullmatch('[0-9]{1,20}',org) is None)
            or (obj.market=='krx' and not org) or re.fullmatch('[0-9]{1,20}',venue_id) is None):
        raise ValueError('invalid authoritative broker identity')
    return (obj.venue,obj.account_scope,obj.market,trade_date,org,venue_id)


def _instant(value):
    if type(value) is not datetime or value.utcoffset() is None:
        raise ValueError('aware control time required')
    compliance.iso_utc(value)
    return value


def _money(value):
    if type(value) is not Decimal or not value.is_finite() or value < 0:
        raise ValueError('invalid reconciled account amount')
    return value


def _trade_date(value):
    if type(value) is not str or re.fullmatch('[0-9]{8}',value) is None:
        raise ValueError('explicit broker trade date required')
    try:
        datetime.strptime(value,'%Y%m%d')
    except ValueError:
        raise ValueError('invalid broker trade date') from None
    return value


def _float(value):
    result = float(value)
    if not math.isfinite(result) or (value > 0 and result <= 0):
        raise ValueError('amount cannot enter legacy gate')
    return result


def _order(body):
    if type(body) is not dict or set(body) != {f.name for f in fields(Order)}:
        raise ValueError('invalid persisted order')
    values = dict(body)
    for key in ('quantity', 'limit_price', 'quote_krw'):
        if type(values[key]) is not str:
            raise ValueError('invalid persisted amount')
        values[key] = Decimal(values[key])
    return Order(**values)


def _rules(body):
    if type(body) is not dict or set(body) != {f.name for f in fields(InstrumentRules)}:
        raise ValueError('invalid persisted rules')
    values = dict(body)
    for key in ('lot_size', 'tick_size', 'min_quantity', 'min_notional_krw', 'fee_fraction'):
        values[key] = Decimal(values[key])
    values['asof'] = datetime.fromisoformat(values['asof'])
    return InstrumentRules(**values)


def _event_data(kind, data):
    pair = {'client_id', 'order_digest'}
    shapes = {
        'session_prepared': {f.name for f in fields(PreparedSession)},
        'risk_snapshot': {'policy_digest', 'day', 'high_watermark', 'day_start_equity', 'effective_floor',
                          'calculated_floor', 'daily_stopped', 'floor_relaxation_approved'},
        'kill': {'session_id', 'reason'}, 'halt': {'floor'},
        'reserved': pair | {'order', 'rules', 'session_id', 'request_digest', 'permit_digest', 'trade_date'},
        'dispatching': pair | {'request_digest', 'permit_digest'},
        'acknowledged': pair | {'venue_order_id', 'metadata'},
        'rejected': pair | {'venue_order_id', 'metadata'}, 'unknown': pair | {'venue_order_id', 'metadata'},
        'expired': pair, 'cancelled_local': pair, 'cancel_requested': pair,
        'reconciled': pair | {'status', 'filled_quantity', 'venue_order_id', 'metadata'},
        'fill': pair | {'fill_key', 'fill_digest', 'fill'},
    }
    if type(data) is not dict or kind not in shapes or set(data) != shapes[kind]:
        raise ValueError('invalid lifecycle event fields')
    for key in ('order_digest', 'request_digest', 'permit_digest', 'fill_digest', 'fill_key', 'policy_digest',
                'plan_hash','input_digest','rules_digest','code_hash','state_hash','seed_hex','selection_seed_hex','record_digest'):
        if key in data and (type(data[key]) is not str or re.fullmatch('[0-9a-f]{64}', data[key]) is None):
            raise ValueError('invalid lifecycle digest')


def _fill_record(body):
    if type(body) is not dict or set(body) != {f.name for f in fields(risk.Fill)}:
        raise ValueError('invalid persisted fill')
    body = dict(body)
    for name in ('quantity', 'price', 'quote_krw', 'fee_amount'):
        if body[name] is not None:
            body[name] = Decimal(body[name])
    body['executed_at'] = datetime.fromisoformat(body['executed_at'])
    fill = risk.Fill(**body)
    if risk._fill_error(fill) is not None:
        raise ValueError('invalid persisted fill fields')
    return fill


def _fold(events):
    orders, killed, halted, last = {}, set(), False, None
    broker_ids = {}
    risk_history, day_starts, stopped_days = [], {}, set()
    for row in events:
        now = datetime.fromisoformat(row['utc'])
        if last is not None and now < last:
            raise ValueError('journal time moved backward')
        last = now
        kind, data = row['kind'], row['data']
        _event_data(kind, data)
        if kind == 'kill':
            killed.add(data['session_id'])
        elif kind == 'halt':
            halted = True
        elif kind == 'risk_snapshot':
            high, start = _money(Decimal(data['high_watermark'])), _money(Decimal(data['day_start_equity']))
            floor = None if data['effective_floor'] is None else _money(Decimal(data['effective_floor']))
            if (data['day'] != now.astimezone(compliance.KST).date().isoformat() or start <= 0 or high < start
                    or type(data['daily_stopped']) is not bool or type(data['floor_relaxation_approved']) is not bool):
                raise ValueError('invalid persistent risk snapshot')
            if data['day'] in day_starts and day_starts[data['day']] != start:
                raise ValueError('day opening equity changed')
            if data['day'] in stopped_days and not data['daily_stopped']:
                raise ValueError('daily stop latch cleared')
            if risk_history:
                previous = risk_history[-1]
                old_floor = None if previous['effective_floor'] is None else Decimal(previous['effective_floor'])
                if high < Decimal(previous['high_watermark']):
                    raise ValueError('persistent peak decreased')
                if old_floor is not None and (floor is None or floor < old_floor):
                    pending = any(p['day'] < data['day'] and p['calculated_floor'] is not None
                                  and Decimal(p['calculated_floor']) == floor for p in risk_history)
                    if halted or not data['floor_relaxation_approved'] or not pending:
                        raise ValueError('unapproved floor reduction')
            day_starts[data['day']] = start
            if data['daily_stopped']:
                stopped_days.add(data['day'])
            risk_history.append(data)
            continue
        elif kind == 'session_prepared':
            continue
        elif kind in _ORDER_EVENTS:
            key = data.get('client_id')
            if type(key) is not str or not key:
                raise ValueError('order event identity missing')
            if kind == 'reserved':
                if key in orders:
                    raise ValueError('client identity reused')
                obj = _order(data['order']); rules = _rules(data['rules'])
                validate_order(obj, rules)
                if obj.venue=='kis':
                    _trade_date(data['trade_date'])
                if obj.client_id != key or order_digest(obj) != data['order_digest']:
                    raise ValueError('persisted order digest mismatch')
                orders[key] = dict(order=obj, rules=rules, digest=data['order_digest'],
                                   session_id=data['session_id'], status='RESERVED', filled=Decimal(0),
                                   venue_order_id='', metadata={}, fill_hashes={}, fill_quantities={}, cancel_pending=False,
                                   request_digest=data['request_digest'], trade_date=data.get('trade_date', ''),
                                   permit_digest=data['permit_digest'])
                continue
            if key not in orders or data.get('order_digest') != orders[key]['digest']:
                raise ValueError('unknown or changed order event')
            rec = orders[key]; state = rec['status']
            if kind == 'fill':
                fill_key, fill_hash = data.get('fill_key'), data.get('fill_digest')
                if state not in _ACTIVE or not rec['venue_order_id'] or type(fill_key) is not str:
                    raise ValueError('invalid fill transition')
                if fill_key in rec['fill_hashes']:
                    raise ValueError('duplicate fill journal event')
                fill = _fill_record(data['fill'])
                obj = rec['order']
                if ((fill.venue, fill.account_scope, fill.order_id, fill.market, fill.symbol, fill.side)
                        != (obj.venue,obj.account_scope,rec['venue_order_id'],obj.market,obj.symbol,obj.side)
                        or (obj.venue=='kis' and (fill.order_date!=rec['trade_date']
                            or fill.broker_org_id!=rec['metadata'].get('broker_org_id','')))
                        or digest(fill) != fill_hash
                        or _fill_key(fill) != fill_key):
                    raise ValueError('persisted fill identity mismatch')
                if fill.fee_amount is None or fill.fee_currency is None:
                    raise ValueError('persisted fill fee is unreconciled')
                rec['fill_hashes'][fill_key] = fill_hash
                rec['fill_quantities'][fill_key] = fill.quantity
                continue
            if kind == 'dispatching':
                if state != 'RESERVED' or data.get('request_digest') != rec['request_digest']:
                    raise ValueError('invalid dispatch transition')
                rec['status'] = 'DISPATCHING'
            elif kind in ('expired', 'cancelled_local'):
                if state != 'RESERVED':
                    raise ValueError('sent order cannot expire locally')
                rec['status'] = kind.upper()
            elif kind in ('acknowledged', 'rejected', 'unknown'):
                if state not in ('DISPATCHING', 'CANCEL_REQUESTED', 'UNKNOWN', 'ACKNOWLEDGED', 'PARTIAL'):
                    raise ValueError('invalid response transition')
                if kind == 'rejected' and state != 'DISPATCHING':
                    raise ValueError('late rejection cannot free reservation')
                rec['status'] = kind.upper()
            elif kind == 'cancel_requested':
                if state not in ('ACKNOWLEDGED', 'PARTIAL', 'UNKNOWN') or not rec['venue_order_id']:
                    raise ValueError('invalid cancellation transition')
                rec['status'] = 'CANCEL_REQUESTED'
                rec['cancel_pending'] = True
            elif kind == 'reconciled':
                if state not in _ACTIVE or state == 'RESERVED':
                    raise ValueError('invalid reconciliation transition')
                status = data.get('status'); quantity = Decimal(data['filled_quantity'])
                if (status not in ('ACKNOWLEDGED', 'PARTIAL', 'FILLED', 'CANCELED', 'REJECTED')
                        or not quantity.is_finite() or not rec['filled'] <= quantity <= rec['order'].quantity
                        or (status == 'FILLED' and quantity != rec['order'].quantity)
                        or (status == 'REJECTED' and quantity != 0)
                        or sum(rec['fill_quantities'].values(),Decimal(0))!=quantity):
                    raise ValueError('contradictory reconciliation')
                rec['filled'], rec['status'] = quantity, status
                rec['cancel_pending'] = False
            if 'metadata' in data and any(key in rec['metadata'] and rec['metadata'][key]!=value
                                             for key,value in data['metadata']):
                raise ValueError('persisted broker metadata changed')
            venue_id = data.get('venue_order_id', '')
            if venue_id:
                scope = _broker_key(rec['order'],rec['trade_date'],venue_id,
                                    rec['metadata']|dict(data.get('metadata',[])))
                if ((rec['venue_order_id'] and rec['venue_order_id'] != venue_id)
                        or (scope in broker_ids and broker_ids[scope] != key)):
                    raise ValueError('broker identity attached to another order')
                broker_ids[scope], rec['venue_order_id'] = key, venue_id
            if 'metadata' in data:
                rec['metadata'].update(dict(data['metadata']))
        else:
            raise ValueError('unsupported lifecycle event')
    return orders, killed, halted, last


def _view(rec):
    state = 'UNKNOWN' if rec['status'] == 'DISPATCHING' else rec['status']
    return OrderState(client_id=rec['order'].client_id, status=state, order_digest=rec['digest'],
                      venue_order_id=rec['venue_order_id'], filled_quantity=rec['filled'])


class Controller:
    """Explicit Journal/provider/policy/adapters/session-provider; no live defaults.

    account_provider(now) returns a complete AccountObservation. adapters[venue]
    supplies pure prepare/cancel/status methods and dispatch(request, capability,
    now=...). session_provider(session_id) returns this process's actual fresh-odds
    PreparedSession. An order's account scope must match the reconciled account.
    """
    def __init__(self, *, journal, account_provider, policy, adapters, session_provider):
        self.journal, self.account_provider, self.policy = journal, account_provider, policy
        self.adapters, self.session_provider = dict(adapters), session_provider
        self._permits = {}
        self._known = set()
        self._reconciled_at = {}

    def _account(self, now, events, order=None):
        _instant(now)
        obs = self.account_provider(now)
        if type(obs) is not AccountObservation:
            raise ValueError('account observation required')
        _instant(obs.asof); _instant(obs.server_time)
        if (not timedelta(0) <= now - obs.asof <= timedelta(seconds=30)
                or abs(now - obs.server_time) > timedelta(seconds=60)
                or now.astimezone(compliance.KST).date()!=obs.server_time.astimezone(compliance.KST).date()
                or now.astimezone(compliance.KST).date()!=obs.asof.astimezone(compliance.KST).date()
                or obs.risk.asof != obs.asof):
            raise ValueError('account or server clock is stale')
        if events and now < datetime.fromisoformat(events[-1]['utc']):
            raise ValueError('control clock moved backward')
        if order is not None and obs.account_scopes.get(order.venue) != order.account_scope:
            raise ValueError('account scope mismatch')
        if type(obs.no_credit) is not bool:
            raise ValueError('no-credit evidence required')
        for value in (tuple(obs.settled_cash_krw.values()) + tuple(obs.holdings.values())
                      + tuple(obs.held_exposure_krw.values()) + tuple(obs.inventory_exposure_krw.values())):
            _money(value)
        for key, rate in obs.quote_rates_krw.items():
            if (type(key) is not tuple or len(key) != 3 or any(type(v) is not str or not v for v in key)
                    or _money(rate) <= 0 or (key[2] == 'KRW' and rate != 1)):
                raise ValueError('invalid authoritative quote rate')
        for account, inventory in obs.inventory_exposure_krw.items():
            total = obs.held_exposure_krw.get(account)
            if total is None or inventory > total:
                raise ValueError('inventory exposure exceeds total venue exposure')
        if Decimal(str(obs.positions.equity_krw)) != obs.risk.equity:
            raise ValueError('account equity sources disagree')
        return obs

    def _snapshot_risk(self, tx, obs, now, orders, ctx):
        past = [e['data'] for e in tx.events if e['kind'] == 'risk_snapshot']
        today = now.astimezone(compliance.KST).date().isoformat()
        high = max([obs.risk.prior_high_watermark] + [Decimal(e['high_watermark']) for e in past])
        same = [e for e in past if e['day'] == today]
        start = Decimal(same[0]['day_start_equity']) if same else obs.risk.day_start_equity
        previous_floor = next((Decimal(e['effective_floor']) for e in reversed(past)
                               if e['effective_floor'] is not None), None)
        floor = obs.risk.approved_effective_floor
        if previous_floor is not None:
            floor = previous_floor if floor is None else max(floor, previous_floor)
        reservation_days = [datetime.fromisoformat(e['utc']).astimezone(compliance.KST).date().isoformat()
                            for e in tx.events if e['kind'] == 'reserved']
        first = obs.risk.is_first_trading_day and (not reservation_days or min(reservation_days) == today)
        view = replace(obs.risk, prior_high_watermark=high, day_start_equity=start,
                       approved_effective_floor=floor, is_first_trading_day=first)
        result = risk.evaluate(self.policy, view)
        signed_daily = ctx.owner.limits.get('daily_loss_krw') if ctx.owner.ok else None
        daily_stopped = (any(e['daily_stopped'] for e in same)
                         or 'DAILY_LOSS_BUDGET_REACHED' in result.reasons
                         or (signed_daily is not None and obs.risk.observed_daily_loss >= Decimal(str(signed_daily))))
        if daily_stopped and 'PERSISTENT_DAILY_STOP' not in result.reasons:
            result = replace(result, new_entry_blocked=True,
                             reasons=result.reasons + ('PERSISTENT_DAILY_STOP',), protective_action_needed=True)
        if result.high_watermark is not None:
            tx.append('risk_snapshot', {'policy_digest': digest(self.policy), 'day': today,
                      'high_watermark': str(result.high_watermark), 'day_start_equity': str(start),
                      'effective_floor': None if result.effective_floor is None else str(result.effective_floor),
                      'calculated_floor': None if result.calculated_floor is None else str(result.calculated_floor),
                      'daily_stopped': bool(daily_stopped), 'floor_relaxation_approved': False}, now=now)
        signed_floor = ctx.owner.limits.get('total_loss_floor_krw') if ctx.owner.ok else None
        floors = ([result.effective_floor] if result.effective_floor is not None else [])
        if signed_floor is not None:
            floors.append(Decimal(str(signed_floor)))
        breached = [f for f in floors if obs.risk.equity < f]
        if breached:
            if not any(e['kind'] == 'halt' for e in tx.events):
                tx.append('halt', {'floor': str(max(breached))}, now=now)
                try:
                    owner.append_system_entry('system_halt', {'floor_krw': _float(max(breached))}, now)
                except Exception:
                    pass  # local durable latch survives an owner-log failure
            result = replace(result, new_entry_blocked=True,
                             reasons=result.reasons + ('PERSISTENT_HALT',), protective_action_needed=True)
        return result

    @_exact
    def observe(self, *, now):
        """Persist risk latches independently of an order attempt; never place an exit."""
        with self.journal.transaction() as tx:
            orders, _, halted, _ = _fold(tx.events)
            obs = self._account(now, tx.events)
            ctx = owner.load_context(now, self._positions(obs, orders))
            if halted:
                obs = replace(obs, risk=replace(obs.risk, halted=True))
            return self._snapshot_risk(tx, obs, now, orders, ctx)

    @_exact
    def approve_floor_relaxation(self, *, floor, now, session_id):
        """Apply only a deferred reduction already signed in the owner limits.

        The pending target must have been observed on an earlier Seoul date.
        This records the effective transition; it creates no owner approval.
        """
        _money(floor); _instant(now)
        with self.journal.transaction() as tx:
            orders, killed, halted, _ = _fold(tx.events)
            if halted or any(e['kind'] == 'halt' for e in tx.events):
                raise ValueError('a halt cannot be relaxed')
            obs = self._account(now, tx.events)
            ctx = owner.load_context(now, self._positions(obs, orders), session_id=session_id)
            if (not ctx.owner.ok or not ctx.code_signed or ctx.owner.armed_sessions or ctx.owner.halted_floors
                    or Decimal(str(ctx.owner.limits.get('total_loss_floor_krw', '-1'))) != floor):
                raise ValueError('signed unarmed floor transition required')
            today = now.astimezone(compliance.KST).date().isoformat()
            past = [e['data'] for e in tx.events if e['kind'] == 'risk_snapshot']
            pending = [e for e in past if e['day'] < today and e['calculated_floor'] is not None
                       and e['effective_floor'] is not None and Decimal(e['calculated_floor']) == floor
                       and floor < Decimal(e['effective_floor'])]
            if not pending:
                raise ValueError('floor reduction is not eligible until a later Seoul day')
            high = max([obs.risk.prior_high_watermark] + [Decimal(e['high_watermark']) for e in past])
            result = risk.evaluate(self.policy, replace(obs.risk, prior_high_watermark=high,
                                                        approved_effective_floor=floor))
            if result.calculated_floor != floor or result.effective_floor != floor:
                raise ValueError('approved floor does not match current policy')
            same = [e for e in past if e['day'] == today]
            tx.append('risk_snapshot', {'policy_digest': digest(self.policy), 'day': today,
                      'high_watermark': str(high), 'day_start_equity': str(
                          Decimal(same[0]['day_start_equity']) if same else obs.risk.day_start_equity),
                      'effective_floor': str(floor), 'calculated_floor': str(floor),
                      'daily_stopped': any(e['daily_stopped'] for e in same),
                      'floor_relaxation_approved': True}, now=now)
            return result

    def _positions(self, obs, orders, exclude=None):
        exposures = {}
        for venue, old in obs.positions.exposure.items():
            exposures[venue] = [old.held_krw, dict(old.reservations), dict(old.promised_sell_units)]
        for key, rec in orders.items():
            if rec['status'] not in _ACTIVE or key == exclude:
                continue
            obj, rules = rec['order'], rec['rules']
            held, cash, sells = exposures.setdefault(obj.venue, [0.0, {}, {}])
            amount = obj.quantity - rec['filled']
            if obj.side == 'buy':
                if obs.account_scopes.get(obj.venue) != obj.account_scope:
                    raise ValueError('pending buy account requires reconciliation')
                rate=obs.quote_rates_krw.get((obj.venue,obj.account_scope,self._symbols(obj)[1]))
                if rate is None or _money(rate)<=0:
                    raise ValueError('current reservation FX evidence required')
                cash[key] = _float(amount * obj.limit_price * rate * (1 + rules.fee_fraction))
            else:
                symbol = self._symbols(obj)[0]
                sells[symbol] = sells.get(symbol, 0.0) + _float(amount)
        return replace(obs.positions, exposure={v: compliance.Exposure(held_krw=e[0], reservations=e[1],
                          promised_sell_units=e[2]) for v, e in exposures.items()})

    @staticmethod
    def _symbols(order):
        if order.venue == 'upbit':
            quote, base = order.symbol.split('-')
            return base, quote
        if order.venue == 'okx':
            return tuple(order.symbol.split('-'))
        return order.symbol, 'KRW' if order.market == 'krx' else 'USD'

    def _intent(self, order, ctx):
        symbol, quote = self._symbols(order)
        state = ctx.active if ctx.active.valid else ctx.snapshot
        if state is None or not state.valid:
            raise ValueError('approved instrument unavailable; manual handling required')
        venue = state.venues.venues.get(order.venue)
        inst = gate._lookup(state, venue, symbol, order.side == 'sell') if venue else None
        if inst is None or inst.multiple != 1:
            raise ValueError('approved cash instrument unavailable')
        return compliance.Intent(venue=order.venue, symbol=symbol, counter_symbol=quote,
                                 asset=inst.asset, multiple=1.0, action=order.side, financing='cash',
                                 quantity=_float(order.quantity),
                                 notional_krw=_float(order.quantity * order.limit_price * order.quote_krw),
                                 reservation_id=order.client_id)

    def _pending_buy_krw(self, obj, obs, orders, exclude=None):
        total=Decimal(0)
        quote=self._symbols(obj)[1]
        rate=obs.quote_rates_krw.get((obj.venue,obj.account_scope,quote))
        for key, rec in orders.items():
            old=rec['order']
            if key==exclude or rec['status'] not in _ACTIVE or old.venue!=obj.venue or old.side!='buy':
                continue
            if old.account_scope!=obj.account_scope or self._symbols(old)[1]!=quote:
                raise ValueError('pending buy account or quote requires reconciliation')
            if rate is None or _money(rate)<=0:
                raise ValueError('current reservation FX evidence required')
            total+=(old.quantity-rec['filled'])*old.limit_price*rate*(1+rec['rules'].fee_fraction)
        return total

    def _capacity(self, obj, rules, obs, orders, exclude=None):
        quote=self._symbols(obj)[1]
        rate=obs.quote_rates_krw.get((obj.venue,obj.account_scope,quote))
        if rate is None or _money(rate)<=0 or obj.quote_krw!=rate:
            raise ValueError('order FX differs from authoritative quote rate')
        same = [r for k, r in orders.items() if k != exclude and r['status'] in _ACTIVE
                and (r['order'].venue, r['order'].account_scope) == (obj.venue, obj.account_scope)]
        if obj.side == 'buy':
            if obs.quote_currency_by_account.get((obj.venue, obj.account_scope)) != self._symbols(obj)[1]:
                raise ValueError('settled cash currency is missing or mismatched')
            legacy = obs.positions.exposure.get(obj.venue)
            if legacy is not None and legacy.reservations:
                raise ValueError('broker cash reservations require reconciliation before new entry')
            if not obs.no_credit:
                raise ValueError('verified no-credit account required')
            available = obs.settled_cash_krw.get((obj.venue, obj.account_scope))
            if available is None:
                raise ValueError('settled cash unavailable')
            promised = self._pending_buy_krw(obj,obs,orders,exclude)
            needed = obj.quantity * obj.limit_price * obj.quote_krw * (1 + rules.fee_fraction)
            if needed > available - promised:
                raise ValueError('insufficient unreserved settled cash')
        else:
            available = obs.holdings.get((obj.venue, obj.account_scope, obj.market, obj.symbol))
            base=self._symbols(obj)[0]
            legacy=obs.positions.exposure.get(obj.venue)
            if legacy is not None and legacy.promised_sell_units:
                raise ValueError('external sell promises require manual reconciliation')
            legacy_held=obs.positions.holdings.get((obj.venue,base))
            if available is None or legacy_held is None or Decimal(str(legacy_held))!=available:
                raise ValueError('holding sources disagree; manual handling required')
            promised = sum((r['order'].quantity-r['filled'] for r in same
                            if r['order'].side == 'sell' and self._symbols(r['order'])[0] == base), Decimal(0))
            if obj.quantity > available - promised:
                raise ValueError('insufficient verified unpromised holdings; manual handling required')

    def _exact_caps(self,obj,obs,orders,ctx,intent,exclude=None):
        if obj.side!='buy':
            return
        state=ctx.active
        venue=state.venues.venues.get(obj.venue) if state.valid else None
        inst=gate._lookup(state,venue,self._symbols(obj)[0],False) if venue else None
        if inst is None:
            return  # the real gate supplies the refusal
        for row in gate._in_force(state,intent,inst.cls,ctx.date):
            if row.treatment!='grey':
                continue
            cap=ctx.owner.caps.get(row.cap_key)
            held=obs.held_exposure_krw.get((obj.venue,obj.account_scope))
            if cap is None or held is None:
                raise ValueError('exact venue cap evidence required')
            legacy=obs.positions.exposure.get(obj.venue)
            if legacy is None or Decimal(str(legacy.held_krw))!=held or legacy.reservations:
                raise ValueError('venue exposure must be independently reconciled')
            promised=self._pending_buy_krw(obj,obs,orders,exclude)
            amount=obj.quantity*obj.limit_price*obj.quote_krw
            if held+promised+amount>Decimal(str(cap))*obs.risk.equity:
                raise ValueError('exact venue cap exceeded')

    def _authorize(self, tx, obj, rules, session_id, now, orders, killed, halted, exclude=None):
        validate_order(obj, rules)
        if not timedelta(0) <= now-rules.asof <= timedelta(minutes=5):
            raise ValueError('instrument rules stale')
        obs = self._account(now, tx.events, obj)
        if not obs.risk.data_complete or not obs.risk.external_flows_known:
            raise ValueError('complete reconciled account required; manual handling required')
        self._capacity(obj, rules, obs, orders, exclude)
        positions = self._positions(obs, orders, exclude)
        ctx = owner.load_context(now, positions, session_id=session_id)
        if obj.side == 'buy':
            if halted or session_id in killed:
                raise ValueError('local no-entry latch active')
            if any(r['status'] in ('DISPATCHING','UNKNOWN','CANCEL_REQUESTED') or r['cancel_pending']
                   for r in orders.values()):
                raise ValueError('uncertain order needs reconciliation')
            if any(k not in self._known and r['status'] in ('ACKNOWLEDGED','PARTIAL')
                   for k,r in orders.items()):
                raise ValueError('restart requires order reconciliation')
            result = self._snapshot_risk(tx, obs, now, orders, ctx)
            if result.new_entry_blocked:
                raise ValueError('risk policy blocks new entry')
            signed_floor = ctx.owner.limits.get('total_loss_floor_krw')
            if signed_floor is not None and obs.risk.equity < Decimal(str(signed_floor)):
                raise ValueError('legacy signed floor conflict requires owner resolution')
            prepared = self.session_provider(session_id)
            verify_session(prepared, session_id=session_id, policy=self.policy, instrument_rules=rules, ctx=ctx, now=now,
                           order=obj, events=tx.events)
            held=obs.held_exposure_krw.get((obj.venue,obj.account_scope))
            inventory=obs.inventory_exposure_krw.get((obj.venue,obj.account_scope))
            if held is None or inventory is None or not 0 <= inventory <= held:
                raise ValueError('exact inventory and total venue exposure required for session capital')
            legacy=obs.positions.exposure.get(obj.venue)
            if (legacy is not None and (Decimal(str(legacy.held_krw))!=held or legacy.reservations)):
                raise ValueError('session exposure sources disagree')
            pending=self._pending_buy_krw(obj,obs,orders,exclude)
            if inventory+pending+obj.quantity*obj.limit_price*obj.quote_krw*(1+rules.fee_fraction)>Decimal(prepared.stake_krw):
                raise ValueError('aggregate exposure exceeds prepared session capital')
        intent = self._intent(obj, ctx)
        self._exact_caps(obj,obs,orders,ctx,intent,exclude)
        issued = gate.permit(intent, ctx)
        if issued is None:
            raise ValueError('compliance gate refused order')
        return obs, ctx, intent, issued

    def reserve(self, order, rules, *, session_id, now):
        with localcontext() as numeric:
            numeric.prec = 1024; numeric.traps[Inexact] = True
            with self.journal.transaction() as tx:
                orders, killed, halted, _ = _fold(tx.events)
                key, sha = order.client_id, order_digest(order)
                if key in orders:
                    if orders[key]['digest'] != sha:
                        raise ValueError('client identity reused with changed order')
                    return _view(orders[key])
                obs, ctx, intent, permit = self._authorize(tx,order,rules,session_id,now,orders,killed,halted)
                trade_date=obs.venue_trade_dates.get((order.venue,order.account_scope,order.market),'')
                if order.venue=='kis':
                    _trade_date(trade_date)
                request = self.adapters[order.venue].prepare(order,rules)
                validate_request(request)
                if request.order_digest != sha or request.operation != 'create':
                    raise ValueError('adapter request identity mismatch')
                tx.append('reserved', {'client_id':key,'order_digest':sha,'order':order_body(order),
                          'rules':plain(rules),'session_id':session_id,'request_digest':request_digest(request),
                          'permit_digest':digest(permit),'trade_date':trade_date}, now=now)
                self._permits[key] = (permit,digest(permit))
                self._known.add(key)
                return _view(_fold(tx.events)[0][key])

    def dispatch(self, client_id, *, now):
        with localcontext() as numeric:
            numeric.prec=1024; numeric.traps[Inexact]=True
            with self.journal.transaction() as tx:
                orders,killed,halted,_ = _fold(tx.events)
                rec = orders.get(client_id)
                if rec is None:
                    raise ValueError('unknown client identity')
                if rec['status'] != 'RESERVED':
                    return _view(rec)
                obj,rules=rec['order'],rec['rules']
                obs,ctx,intent,new_permit=self._authorize(tx,obj,rules,rec['session_id'],now,
                                                         orders,killed,halted,client_id)
                if obj.venue=='kis' and obs.venue_trade_dates.get((obj.venue,obj.account_scope,obj.market))!=rec['trade_date']:
                    raise ValueError('broker trade date changed before dispatch')
                issued,stored=self._permits.get(client_id,(new_permit,digest(new_permit)))
                if digest(issued)!=stored or not gate.verify_permit(issued,intent,ctx)[0]:
                    raise ValueError('issued permit changed or stale')
                request=self.adapters[obj.venue].prepare(obj,rules)
                validate_request(request)
                if request_digest(request)!=rec['request_digest']:
                    raise ValueError('prepared request changed')
                tx.append('dispatching',{'client_id':client_id,'order_digest':rec['digest'],
                          'request_digest':request_digest(request),'permit_digest':digest(issued)},now=now)
                self._permits.pop(client_id,None)
                result=self._send(obj,request,now)
                kind='rejected' if result.status=='rejected' else 'unknown' if result.status=='unknown' else 'acknowledged'
                self._result(tx,rec,kind,result,now)
                return _view(_fold(tx.events)[0][client_id])

    def _send(self,obj,request,now):
        try:
            result=self.adapters[obj.venue].dispatch(request,_issue(request),now=now)
            if type(result) is not AdapterResult or result.client_id != obj.client_id:
                raise ValueError('adapter identity mismatch')
            if result.status not in ('unknown','rejected') and not result.venue_order_id:
                raise ValueError('broker identity missing')
            return result
        except Exception:
            return AdapterResult(status='unknown',code='dispatch_uncertain',client_id=obj.client_id)

    @staticmethod
    def _result(tx,rec,kind,result,now):
        orders,_,_,_=_fold(tx.events)
        collision=False
        try:
            candidate=(_broker_key(rec['order'],rec['trade_date'],result.venue_order_id,
                                   rec['metadata']|dict(result.metadata)) if result.venue_order_id else None)
            collision=candidate is not None and any(key!=rec['order'].client_id and other['venue_order_id']
                and _broker_key(other['order'],other['trade_date'],other['venue_order_id'],other['metadata'])==candidate
                for key,other in orders.items())
        except ValueError:
            collision=True
        changed=bool(rec['venue_order_id'] and result.venue_order_id and rec['venue_order_id']!=result.venue_order_id)
        metadata=dict(result.metadata)
        changed=changed or any(key in rec['metadata'] and rec['metadata'][key]!=value for key,value in metadata.items())
        if collision or changed:
            kind='unknown'
            result=AdapterResult(status='unknown',code='broker_identity_conflict',client_id=rec['order'].client_id)
        tx.append(kind,{'client_id':rec['order'].client_id,'order_digest':rec['digest'],
                       'venue_order_id':result.venue_order_id,'metadata':plain(result.metadata)},now=now)

    @_exact
    def cancel(self,client_id,*,now):
        with self.journal.transaction() as tx:
            orders,_,_,last=_fold(tx.events); rec=orders.get(client_id)
            _instant(now)
            if last is not None and now<last:
                raise ValueError('control clock moved backward')
            if rec is None:
                raise ValueError('unknown client identity')
            if rec['status'] in _TERMINAL:
                return _view(rec)
            if rec['status']=='RESERVED':
                tx.append('cancelled_local',{'client_id':client_id,'order_digest':rec['digest']},now=now)
            else:
                obj=rec['order'];obs=self._account(now,tx.events,obj)
                if rec['cancel_pending'] or not rec['venue_order_id']:
                    return _view(rec)
                positions=self._positions(obs,orders)
                ctx=owner.load_context(now,positions,session_id=rec['session_id'])
                intent=self._intent(obj,ctx)
                approved=ctx.active if ctx.owner.ok and ctx.active.valid else ctx.snapshot
                if approved is None or not approved.valid or gate._conduct(intent,approved):
                    raise ValueError('known-order cancellation conduct check refused')
                extra={}
                if obj.venue=='kis':
                    residual=obs.cancellable_quantities.get(client_id)
                    if residual is None or not 0 < _money(residual) <= obj.quantity-rec['filled']:
                        raise ValueError('authoritative cancelable quantity unavailable')
                    extra={'broker_org_id':rec['metadata'].get('broker_org_id',''),
                           'remaining_quantity':residual}
                    reconciled = self._reconciled_at.get(client_id)
                    if reconciled is None or not timedelta(0) <= now-reconciled <= timedelta(seconds=5):
                        raise ValueError('reconcile cancellation residual first')
                request=self.adapters[obj.venue].prepare_cancel(obj,rec['venue_order_id'],**extra)
                validate_request(request)
                if request.operation!='cancel' or request.order_digest!=rec['digest']:
                    raise ValueError('cancel request mismatch')
                tx.append('cancel_requested',{'client_id':client_id,'order_digest':rec['digest']},now=now)
                result=self._send(obj,request,now)
                if result.venue_order_id and result.venue_order_id!=rec['venue_order_id']:
                    result=AdapterResult(status='unknown',code='cancel_identity_mismatch',client_id=client_id)
                self._result(tx,rec,'unknown' if result.status=='unknown' else 'acknowledged',result,now)
            return _view(_fold(tx.events)[0][client_id])

    @_exact
    def reconcile(self,client_id,*,now):
        with self.journal.transaction() as tx:
            orders,_,_,_=_fold(tx.events);rec=orders.get(client_id)
            if rec is None:
                raise ValueError('unknown client identity')
            if rec['status'] in _TERMINAL or rec['status']=='RESERVED':
                return _view(rec)
            obj=rec['order'];obs=self._account(now,tx.events,obj)
            extra={}
            if obj.venue=='kis':
                extra={'broker_org_id':rec['metadata'].get('broker_org_id',''),'order_date':rec['trade_date']}
            request=self.adapters[obj.venue].prepare_status(obj,rec['venue_order_id'],**extra)
            validate_request(request)
            if request.operation!='status' or request.order_digest!=rec['digest']:
                raise ValueError('status request mismatch')
            result=self._send(obj,request,now)
            if result.status=='unknown' or not result.venue_order_id or (rec['venue_order_id']
                    and result.venue_order_id!=rec['venue_order_id']):
                return _view(rec)
            if any(key in rec['metadata'] and rec['metadata'][key]!=value for key,value in result.metadata):
                return _view(rec)
            status={'filled':'FILLED','canceled':'CANCELED','rejected':'REJECTED','partial':'PARTIAL',
                    'open':'ACKNOWLEDGED','accepted':'ACKNOWLEDGED'}.get(result.status)
            quantity=result.filled_quantity
            if (status is None or quantity is None or (status=='FILLED' and quantity!=obj.quantity)
                    or (status=='REJECTED' and quantity!=0)):
                return _view(rec)
            ledger=risk.account_fills(obs.fills)
            matching=([f for f in ledger.accepted_fills if (f.venue,f.account_scope,f.order_id)==
                      (obj.venue,obj.account_scope,result.venue_order_id)
                      and (obj.venue!='kis' or (f.market==obj.market and f.order_date==rec['trade_date']
                           and f.broker_org_id==rec['metadata'].get('broker_org_id',dict(result.metadata).get('broker_org_id',''))))]
                      if ledger.ok else [])
            accounted=sum((f.quantity for f in matching),Decimal(0))
            current_hashes={_fill_key(f):digest(f) for f in matching}
            if any(current_hashes.get(key)!=sha for key,sha in rec['fill_hashes'].items()):
                raise ValueError('authoritative fill history omitted or changed')
            if (not ledger.ok or client_id not in obs.reconciled_client_ids or quantity is None
                    or quantity!=accounted or not rec['filled']<=quantity<=obj.quantity
                    or any((f.market,f.symbol,f.side)!=(obj.market,obj.symbol,obj.side) for f in matching)):
                return _view(rec)
            if result.average_price is not None and (
                    sum((f.quantity*f.price for f in matching),Decimal(0))!=quantity*result.average_price):
                return _view(rec)  # no unverified rounding tolerance for broker averages
            if result.fee is not None and (not result.fee_currency
                    or any(f.fee_currency!=result.fee_currency for f in matching)
                    or sum((f.fee_amount for f in matching),Decimal(0))!=result.fee):
                return _view(rec)
            # Establish identity before any fill row; an acknowledgment is not a terminal outcome.
            if not rec['venue_order_id']:
                self._result(tx,rec,'acknowledged',result,now)
                rec=_fold(tx.events)[0][client_id]
                if rec['venue_order_id']!=result.venue_order_id:
                    return _view(rec)
            for fill in matching:
                key=_fill_key(fill); sha=digest(fill)
                if key in rec['fill_hashes']:
                    if rec['fill_hashes'][key]!=sha:
                        raise ValueError('contradictory authoritative fill')
                else:
                    tx.append('fill',{'client_id':client_id,'order_digest':rec['digest'],
                              'fill_key':key,'fill_digest':sha,'fill':plain(fill)},now=now)
            tx.append('reconciled',{'client_id':client_id,'order_digest':rec['digest'],'status':status,
                      'filled_quantity':str(quantity),'venue_order_id':result.venue_order_id,
                      'metadata':plain(result.metadata)},now=now)
            self._known.add(client_id)
            self._reconciled_at[client_id] = now
            return _view(_fold(tx.events)[0][client_id])

    @_exact
    def kill(self,session_id,*,reason,now):
        if type(session_id) is not str or not session_id.strip():
            raise ValueError('session identity required')
        _instant(now)
        with self.journal.transaction() as tx:
            _,_,_,last=_fold(tx.events)
            clock_ok=False
            try:
                self._account(now,tx.events)
                clock_ok=True
            except Exception:
                pass
            stamp=now if clock_ok else last or datetime(1970,1,1,tzinfo=timezone.utc)
            tx.append('kill',{'session_id':session_id,'reason':'owner_requested' if clock_ok else 'clock_ambiguous'},now=stamp)
            if not clock_ok:
                return False
            try:
                owner.append_system_entry('system_disarm',{'session_id':session_id,'reason':'execution control kill'},now)
            except Exception:
                return False
            return True

    @_exact
    def halt(self,*,floor,now):
        _money(floor);_instant(now)
        with self.journal.transaction() as tx:
            _,_,_,last=_fold(tx.events)
            clock_ok=False
            try:
                self._account(now,tx.events);clock_ok=True
            except Exception:
                pass
            tx.append('halt',{'floor':str(floor)},now=now if clock_ok else last or datetime(1970,1,1,tzinfo=timezone.utc))
            if not clock_ok:
                return False
            try:
                owner.append_system_entry('system_halt',{'floor_krw':_float(floor)},now)
            except Exception:
                return False
            return True
