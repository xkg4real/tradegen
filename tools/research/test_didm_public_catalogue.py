import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

from tools.research import didm_public_catalogue as d


class PublicCatalogues(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root=Path(temp.name); self.record=dict(ticker='A:1',event_ticker='E',market_type='binary',status='active')

    def capture(self, payloads, *, source='kalshi_current', **kwargs):
        replies=iter(payloads); self.urls=[]
        def get(url):
            self.urls.append(url); response=next(replies)
            if isinstance(response,Exception): raise response
            return json.dumps(response).encode()
        dest=self.root/str(len(list(self.root.iterdir()))); result=d.capture(source,dest,fetch=get,**kwargs)
        with (dest/'candidates.csv').open() as f: rows=list(csv.DictReader(f))
        return result, rows, dest

    def test_cursor_exhaustion_mve_sides_and_deduplication(self):
        second=dict(self.record,ticker='A|1',status='settled',mve_selected_legs=[dict(market_ticker='L',side='no')])
        r,rows,dest=self.capture([dict(markets=[self.record],cursor='a+b'),dict(markets=[self.record,second],cursor='')]);
        self.assertTrue(r['complete']); self.assertIsNone(r['global_total']); self.assertIn('cursor=a%2Bb',self.urls[1]); self.assertNotIn('status=',self.urls[0])
        self.assertEqual(r['repeated'],2); self.assertEqual(len(rows),4); self.assertEqual(len({x['instrument_id'] for x in rows}),4)
        self.assertEqual({x['payoff_id'] for x in rows},{'YES','NO'}); self.assertEqual(rows[-1]['listing_status'],'inactive')
        with sqlite3.connect(dest/'observations.sqlite') as db:
            body=json.loads(db.execute("SELECT body FROM entries WHERE id=?",(d.identity('KALSHI','A|1','YES'),)).fetchone()[0]); self.assertEqual(body['legs'][0]['side'],'no')
        self.assertEqual(len(list(dest.glob('page-*.gz'))),2)

    def test_loop_page_limit_entitlement_and_missing_cursor(self):
        first=dict(markets=[self.record],cursor='a')
        for pages, kwargs, reason in (([first,first],{},'CURSOR_LOOP'),([first],{'page_limit':1},'PAGE_LIMIT'),
                                      ([first,HTTPError('https://example.test',403,'Forbidden',{},None)],{},'HTTPError'),
                                      ([dict(markets=[self.record])],{},'malformed continuation')):
            with self.subTest(reason=reason):
                result,rows,_=self.capture(pages,**kwargs); self.assertFalse(result['complete']); self.assertIn(reason,result['stop_reason']); self.assertEqual(len(rows),2)

    def test_changed_duplicates_and_bad_records_do_not_claim_coverage(self):
        r,rows,dest=self.capture([dict(markets=[self.record,None,dict(self.record,status='settled'),{'ticker':'unsupported','market_type':'new_type'}],cursor='')]); self.assertFalse(r['complete']); self.assertTrue(r['endpoint_exhausted']); self.assertEqual(r['malformed'],1); self.assertEqual(r['changed_duplicates'],2); self.assertEqual(len(rows),3); self.assertIn('unverified',{x['listing_status'] for x in rows})

    def test_distinct_crypto_payoffs_and_registry(self):
        sym=dict(symbol='BTCUSD',baseAsset='BTC',quoteAsset='USD',contractType='PERPETUAL',marginAsset='BTC',contractStatus='TRADING')
        sources=[('binance_spot',{'symbols':[sym]}),('binance_usdm',{'symbols':[sym]}),('binance_coinm',{'symbols':[sym]}),('upbit',[{'market':'KRW-BTC'}]),('coinbase',[{'id':'BTC-USD','base_currency':'BTC','quote_currency':'USD'}]),('coingecko',[{'id':'bitcoin','symbol':'btc','platforms':{}}])]
        rows=[]
        for source,data in sources:
            r,items,_=self.capture([data],source=source); self.assertTrue(r['complete']); rows+=items
        self.assertEqual(len({x['instrument_id'] for x in rows}),6); self.assertEqual(rows[-1]['family'],'asset_reference'); self.assertEqual(rows[2]['family'],'swap'); self.assertIn('INVERSE',rows[2]['payoff_id'])

    def test_event_and_series_are_not_payoffs(self):
        for source,key,record in [('kalshi_events','events',{'event_ticker':'E','series_ticker':'S'}),('kalshi_series','series',{'ticker':'S'}),('kalshi_multivariate_events','events',{'event_ticker':'E','series_ticker':'S'})]:
            r,rows,_=self.capture([{key:[record],'cursor':''}],source=source); self.assertTrue(r['complete']); self.assertEqual(r['unique_records'],1); self.assertEqual(rows,[])
