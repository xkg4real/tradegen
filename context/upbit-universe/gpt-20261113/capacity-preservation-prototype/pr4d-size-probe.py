"""Read-only synthetic proof of the planned fallback's retained-field size.

Uses real collector/provider/book validation and the plan's exact _holding body.
No live credentials, external I/O, runtime source mutation, signing or journal writes.
"""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal as D
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import textwrap
from types import SimpleNamespace

ROOT = Path('/workspace/tradegen-universe-1113')
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('collector_fixture', ROOT / 'tests/accounts_collector.py')
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
from core.compliance.rules import UNIVERSE_MARKET
from execution_accounts.collector import SourceReceipt
from execution_accounts.provider import build_observation
from execution_accounts.quotes import parse_orderbook
from execution_control.store import MAX_ROW_BYTES, _canonical, _utc
from execution_launch.live_history import _row, _receipt_body, _aware, _require
from execution_launch.paper_capture import sample_prefetched_book
from execution_launch.strategy import _plain


class ManyDustSource:
    account_scope = F.SCOPE

    def __init__(self, count):
        self.calls = []
        self.details = {}
        self.balances = [dict(currency='KRW', balance=str(100000-count), locked='0')]
        for i in range(count):
            base = 'X%011d' % i
            at = F.NOW - timedelta(seconds=3600-2*i)
            detail = F.order_fixture()
            detail.update(uuid='order-%d' % i, identifier='client-%d' % i,
                          market='KRW-'+base, created_at=at.isoformat(), price='1', paid_fee='0')
            detail['trades'][0].update(uuid='fill-%d' % i, market='KRW-'+base,
                                      price='1', funds='1', created_at=(at+timedelta(seconds=1)).isoformat())
            self.details[detail['uuid']] = detail
            self.balances.append(dict(currency=base, balance='1', locked='0'))

    def fetch(self, path, params):
        self.calls.append((path, params))
        args = dict(params)
        if path == '/v1/accounts':
            body = self.balances
        elif path == '/v1/orders/closed':
            lo, hi = int(args['start_time']), int(args['end_time'])
            matching = [item for item in self.details.values()
                        if lo <= int(F.datetime.fromisoformat(item['created_at']).timestamp()*1000) <= hi]
            body = [{k: v for k, v in item.items() if k != 'trades'} for item in matching[:1000]]
        elif path == '/v1/order':
            body = self.details[args['uuid']]
        elif path == '/v1/market/all':
            body = [dict(market='KRW-BTC'), dict(market='KRW-ETH')]
        elif path in ('/v1/orders/open', '/v1/deposits', '/v1/withdraws'):
            body = []
        else:
            raise AssertionError(path)
        return F.receipt(path, params, deepcopy(body))


source = ManyDustSource(1500)
collected = F.collect(source)
account = collected.bundle.accounts[0]
observation = build_observation(collected.bundle, now=F.NOW)
assert len(account.positions) == 1500
assert all(p.units == 1 and p.price == 0 and p.unlisted is True for p in account.positions)
assert all(len(p.symbol) == 16 for p in account.positions)
assert len(source.calls) < 2000
print('COLLECTOR_AND_PROVIDER_ACCEPTED', len(account.positions), 'positions;', len(source.calls), 'requests')
print('RECEIPT_MAX_BYTES', max(len(r.raw_body) for r in collected.receipts))

wire = [dict(market='KRW-BTC', level=0, timestamp=int(F.NOW.timestamp()*1000),
             total_ask_size=1, total_bid_size=1,
             orderbook_units=[dict(ask_price=102, bid_price=100, ask_size=1, bid_size=1)], padding='')]
raw = json.dumps(wire, separators=(',', ':')).encode()
wire[0]['padding'] = 'x' * (131072-len(raw))
raw = json.dumps(wire, separators=(',', ':')).encode()
assert len(raw) == 131072
receipt = SourceReceipt(path='/v1/orderbook', params=(('markets', 'KRW-BTC'), ('level', '0'), ('count', '30')),
    account_scope='public-upbit-orderbook', received_at=F.NOW, server_time=F.NOW,
    raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())
book = parse_orderbook(receipt, symbol='KRW-BTC', now=F.NOW)
sample_prefetched_book(book, slot=F.NOW, sampled_at=F.NOW)
print('BOOK_AND_SAMPLE_ACCEPTED', len(raw), 'raw bytes')

plan = (ROOT / 'docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4d-driver-history.md').read_text()
start = plan.index('    def _holding(self,')
end = plan.index('\n    def ', start+5)
holding_source = textwrap.dedent(plan[start:end])
ns = dict(Decimal=D, Fraction=Fraction, UNIVERSE_MARKET=UNIVERSE_MARKET,
          _aware=_aware, _require=_require, _plain=_plain, _utc=_utc)
exec(compile(holding_source, 'planned-_holding', 'exec'), ns)
receiver = SimpleNamespace(_profile=SimpleNamespace(instrument_rules=SimpleNamespace(min_notional_krw=D(5000))))
holdings = sorted(ns['_holding'](receiver, p.symbol, p.units, p.price, p.asof) for p in account.positions)
data = dict(index=0, trade_symbol='KRW-BTC', tick_size='1', receipt=_receipt_body(book.receipt),
            anchor=dict(cash_quote='98500', units='0', account_asof=_utc(F.NOW)), holdings=holdings,
            universe=dict(snapshot=dict(day=F.NOW.date().isoformat(), sha256='e'*64,
                                        top_n=['KRW-BTC', 'KRW-ETH']),
                          flags='unavailable', tickers='unavailable', allow=[],
                          reasons=['HISTORY_ROW_SIZE_FALLBACK'], events=[]),
            decision=dict(coin=None, target_fraction='0', held=None, hold_count=1))
line = _canonical(_row(2, '0'*64, 'slot', data, F.NOW)) + b'\n'
print('PLANNED_FALLBACK_ROW_BYTES', len(line), 'CAP', MAX_ROW_BYTES, 'OVER_BY', len(line)-MAX_ROW_BYTES)
assert len(line) > MAX_ROW_BYTES
print('HOLDINGS_BYTES', len(_canonical(holdings)))
print('RECEIPT_BYTES', len(_canonical(data['receipt'])))
print('PASS valid synthetic collector/provider/book inputs exceed planned fallback cap')
