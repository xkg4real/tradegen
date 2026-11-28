"""Capture public market directories and export research candidates. No account or order APIs."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KALSHI = 'https://external-api.kalshi.com/trade-api/v2'
# (read-only URL, response array, cursor-paginated)
SOURCES = {
    'kalshi_current': (KALSHI + '/markets', 'markets', True),
    'kalshi_historical': (KALSHI + '/historical/markets', 'markets', True),
    'kalshi_events': (KALSHI + '/events', 'events', True),
    'kalshi_multivariate_events': (KALSHI + '/events/multivariate', 'events', True),
    'kalshi_series': (KALSHI + '/series', 'series', False),
    'upbit': ('https://api.upbit.com/v1/market/all?is_details=true', None, False),
    'coinbase': ('https://api.exchange.coinbase.com/products', None, False),
    'binance_spot': ('https://data-api.binance.vision/api/v3/exchangeInfo', 'symbols', False),
    'binance_usdm': ('https://fapi.binance.com/fapi/v1/exchangeInfo', 'symbols', False),
    'binance_coinm': ('https://dapi.binance.com/dapi/v1/exchangeInfo', 'symbols', False),
    'coingecko': ('https://api.coingecko.com/api/v3/coins/list?include_platform=true', None, False),
}
FIELDS = ['instrument_id','family','venue','symbol','payoff_id','market_access','response','costs',
          'listing_status','terms_sha256']


def digest(value):
    return hashlib.sha256(value).hexdigest()


def identity(*parts):
    return '|'.join(urllib.parse.quote(s, safe='') for s in parts)


def identifier(obj, field):
    value = obj.get(field)
    return value.strip() if isinstance(value, str) else ''


def records(source, obj):
    """Return normalized observations. Every raw object is retained independently on disk."""
    if not isinstance(obj, dict):
        raise ValueError('object expected')
    if source == 'kalshi_series':
        return [dict(role='series', native=identifier(obj,'ticker'), category=obj.get('category'))]
    if source in ('kalshi_events', 'kalshi_multivariate_events'):
        return [dict(role='event', native=identifier(obj,'event_ticker'), series=obj.get('series_ticker'),
                     category=obj.get('category'))]
    if source in ('kalshi_current','kalshi_historical'):
        symbol = identifier(obj,'ticker'); kind = identifier(obj,'market_type'); event = obj.get('event_ticker')
        sides = ('YES','NO') if kind == 'binary' else ('UNVERIFIED_PAYOFF',)
        # The leg's side identifies how the combo settles. It is not a separate position in the combo.
        return [dict(role='instrument', native=symbol, venue='KALSHI', symbol=symbol, family='prediction',
                     payoff_id=side, event=event, series=obj.get('series_ticker'), kind=kind, status=obj.get('status'),
                     legs=obj.get('mve_selected_legs'), collection=obj.get('mve_collection_ticker'),
                     reason='CONTRACT_TERMS_UNVERIFIED' if kind == 'binary' else 'UNKNOWN_PAYOFF_TYPE',
                     close_time=obj.get('close_time'), source_open_time=obj.get('open_time')) for side in sides]
    if source == 'coingecko':
        native = identifier(obj,'id')
        return [dict(role='instrument', native=native, venue='COINGECKO', symbol=native,
                     family='asset_reference', payoff_id='REGISTRY_ENTRY', display_symbol=obj.get('symbol'),
                     platforms=obj.get('platforms'), reason='REFERENCE_ONLY')]
    if source == 'upbit':
        symbol = identifier(obj,'market'); quote, sep, base = symbol.partition('-')
        if not sep or not base or not quote:
            raise ValueError('invalid Upbit market')
        fields = dict(base=base, quote=quote, status=None, warning=obj.get('market_event', obj.get('market_warning')))
    elif source == 'coinbase':
        symbol = identifier(obj,'id')
        fields = dict(base=obj.get('base_currency'), quote=obj.get('quote_currency'), status=obj.get('status'),
                      trading_disabled=obj.get('trading_disabled'), cancel_only=obj.get('cancel_only'))
    else:
        symbol = identifier(obj,'symbol')
        fields = dict(base=obj.get('baseAsset'), quote=obj.get('quoteAsset'),
                      status=obj.get('status',obj.get('contractStatus')), margin=obj.get('marginAsset'),
                      contract_type=obj.get('contractType'), delivery_time=obj.get('deliveryDate'))
    venue = source.split('_')[0].upper(); family, payoff = 'crypto','SPOT'
    reason = 'ACCOUNT_ACCESS_AND_PRICE_UNVERIFIED'
    if source in ('binance_usdm','binance_coinm'):
        family = 'swap' if fields['contract_type'] == 'PERPETUAL' else 'future'
        payoff = ('USD_M_LINEAR' if source == 'binance_usdm' else 'COIN_M_INVERSE') + ':' + str(fields['contract_type'])
        reason = 'CONTRACT_TERMS_UNVERIFIED'
    if not fields['base'] or not fields['quote']:
        reason = 'PAIR_TERMS_INCOMPLETE'
    return [dict(role='instrument', native=symbol, venue=venue, symbol=symbol, family=family,
                 payoff_id=payoff, reason=reason, **fields)]


def get_bytes(url):
    request = urllib.request.Request(url, headers={'User-Agent':'TRADEGEN-public-research/1',
                                                  'Accept':'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def capture(source, dest, fetch=get_bytes, page_limit=None):
    """Store all received pages, including partial runs. SQLite bounds memory across cursor scans."""
    if page_limit is not None and page_limit < 1:
        raise ValueError('page limit must be positive')
    base, key, paged = SOURCES[source]; dest = Path(dest); dest.mkdir(parents=True, exist_ok=False)
    cursor = ''; seen = set()
    db = sqlite3.connect(dest/'observations.sqlite')
    db.execute('CREATE TABLE entries (id TEXT PRIMARY KEY, role TEXT, body TEXT)')
    db.execute('CREATE TABLE rejects (page INTEGER, slot INTEGER, reason TEXT)')
    summary = dict(source=source, endpoint=base, pages=0, objects=0, repeated=0, changed_duplicates=0,
                   malformed=0, endpoint_exhausted=False, complete=False, started_at=int(time.time()),
                   global_total=None, stop_reason='INTERRUPTED')
    try:
        with (dest/'pages.jsonl').open('x', encoding='utf-8') as receipts:
            while True:
                args = {'limit':200 if source in ('kalshi_events', 'kalshi_multivariate_events') else 1000} if paged else {}
                if cursor: args['cursor'] = cursor
                url = base + ('?' + urllib.parse.urlencode(args) if args else '')
                raw = fetch(url); received = int(time.time()); pin = digest(raw); page = summary['pages'] + 1
                with gzip.open(dest/(f'page-{page:08d}-{pin}.json.gz'),'wb') as f: f.write(raw)
                receipts.write(json.dumps(dict(page=page, url=url, sha256=pin, received_at=received))+'\n'); receipts.flush()
                summary['pages'] = page
                data = json.loads(raw); batch = data if key is None else data[key]
                if not isinstance(batch,list): raise ValueError('array expected')
                for i,obj in enumerate(batch):
                    summary['objects'] += 1
                    try:
                        for row in records(source,obj):
                            if not row['native']: raise ValueError('missing source identity')
                            if row['role'] == 'instrument':
                                name = identity(row['venue'],row['native'],row['payoff_id'])
                            else: name = identity('KALSHI',row['role'],row['native'])
                            body = json.dumps(row,sort_keys=True, ensure_ascii=False)
                            if not db.execute('INSERT OR IGNORE INTO entries VALUES (?,?,?)',(name,row['role'],body)).rowcount:
                                summary['repeated'] += 1
                                if db.execute('SELECT body FROM entries WHERE id=?',(name,)).fetchone()[0] != body:
                                    summary['changed_duplicates'] += 1
                    except (ValueError,TypeError,KeyError) as exc:
                        db.execute('INSERT INTO rejects VALUES (?,?,?)',(page,i,str(exc))); summary['malformed'] += 1
                db.commit()
                if paged and ('cursor' not in data or not isinstance(data['cursor'],str)):
                    raise ValueError('missing or malformed continuation cursor')
                cursor = data['cursor'] if paged else ''
                if not cursor:
                    summary['endpoint_exhausted'] = True; summary['stop_reason'] = 'END_OF_DIRECTORY'; break
                if cursor in seen:
                    summary['stop_reason'] = 'CURSOR_LOOP'; break
                seen.add(cursor)
                if page_limit and page >= page_limit:
                    summary['stop_reason'] = 'PAGE_LIMIT'; break
    except (OSError,ValueError,TypeError,KeyError) as exc:
        if isinstance(exc,urllib.error.HTTPError):
            summary['http_status'] = exc.code
        summary['stop_reason'] = f'{type(exc).__name__}: {exc}'
    finally:
        summary['finished_at'] = int(time.time())
        summary['complete'] = summary['endpoint_exhausted'] and not (summary['malformed'] or summary['changed_duplicates'])
        summary['unique_records'] = db.execute('SELECT COUNT(*) FROM entries').fetchone()[0]
        with (dest/'candidates.csv').open('x',encoding='utf-8',newline='') as out:
            writer=csv.DictWriter(out,fieldnames=FIELDS); writer.writeheader()
            for name,body in db.execute("SELECT id,body FROM entries WHERE role='instrument' ORDER BY id"):
                row=json.loads(body)
                listing='unverified' if row['reason'] in ('UNKNOWN_PAYOFF_TYPE','PAIR_TERMS_INCOMPLETE') else 'listed'
                access='unknown'
                if row.get('status') in {'settled','finalized','inactive','closed','determined','offline','BREAK','DELIVERED'} or row.get('trading_disabled') or row.get('cancel_only'):
                    access='unavailable'; listing='inactive'
                writer.writerow(dict(instrument_id=name, family=row['family'],venue=row['venue'],symbol=row['symbol'],
                                     payoff_id=row['payoff_id'],market_access=access,listing_status=listing))
        db.close(); (dest/'coverage.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',choices=SOURCES); parser.add_argument('new_dir',type=Path)
    parser.add_argument('--max-pages', type=int, help='capture a sample; a remaining cursor means incomplete')
    args=parser.parse_args(); result=capture(args.source,args.new_dir,page_limit=args.max_pages)
    print(json.dumps(result,ensure_ascii=False)); return 0 if result['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
