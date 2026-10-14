from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from collection_storage import StorageSettings
from research_contract import ROOT,load_json,canonical_json,validate_record
from regulatory_collection import SourceIssue
from market_collection import collect_eodhd,collect_hkex,normalize
from hkex_historical_prices import Quote
from market_athena import prepare

class MarketTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.settings=StorageSettings(local_root=str(self.root/'store'),s3_bucket='test');self.store=self.settings.store()
        self.u=load_json(ROOT/'examples/sec-filings/universe.json');self.t=load_json(ROOT/'config/sectors.v1.json')
        self.client=Mock();self.calls=[]
        def get(path,params):
            self.calls.append((path,params))
            rows=([{'date':'2021-01-04','open':10,'high':12,'low':9,'close':11,'adjusted_close':5.5,'volume':100}] if path.startswith('eod/') else
                  [{'date':'2021-01-05','split':'2/1'}] if path.startswith('splits/') else [{'date':'2021-01-06','value':0.1,'currency':'USD'}])
            return rows,canonical_json(rows),'https://example.org/'+path
        self.client.get.side_effect=get
    def collect(self):return collect_eodhd(self.store,self.settings,self.u,self.t,'EXAMPLE.US',date(2021,1,1),date(2021,2,1),'historical',self.client)
    def test_raw_contract_exclusive_end_and_curated_actions(self):
        result=self.collect();self.assertEqual(result['status'],'complete',result)
        self.assertEqual(result['records'],3)
        self.assertEqual(self.calls[0][1]['to'],'2021-01-31')
        root=prepare(self.store,self.settings,load_json(ROOT/'config/market-athena.json'),[result['manifest']],self.root/'curated')
        report=load_json(root/'release.json');self.assertEqual(report['files']['corporate_actions']['rows'],2)
        self.assertEqual(self.collect()['already_complete'],True);self.assertEqual(len(self.calls),3)
    def test_denied_actions_resume_without_refetching_prices(self):
        good=self.client.get.side_effect
        def get(path,params):
            if path.startswith('div/'):raise SourceIssue('eodhd_endpoint_access_denied',True)
            return good(path,params)
        self.client.get.side_effect=get
        result=self.collect();self.assertEqual(result['status'],'partial')
        self.client.get.side_effect=good
        self.assertEqual(self.collect()['status'],'complete')
        self.assertEqual(sum(p.startswith('eod/') for p,_ in self.calls),1)
    def test_empty_prices_never_marked_complete(self):
        self.client.get.side_effect=lambda *a:([],b'[]','https://example.org')
        self.assertEqual(self.collect()['reason'],'market_empty_price_window_unverified')
    def test_invalid_ratio_and_out_of_window_rejected(self):
        for row in ({'date':'2021-01-04','split':'2/0'},{'date':'2020-01-01','split':'2/1'}):
            with self.assertRaises(SourceIssue):normalize(row,'splits',date(2021,1,1),date(2021,2,1))

    def test_hkex_wrong_date_never_commits(self):
        result=collect_hkex(self.store,self.settings,self.u,self.t,date(2021,1,4),'historical',
            loader=lambda *a:('05/01/2021','https://example.org/sheet'))
        self.assertEqual(result['reason'],'hkex_sheet_date_unverified')

    def test_hkex_partial_resumes_second_board(self):
        calls=[]
        def loader(day,board):
            calls.append(board);return '04/01/2021','https://example.org/sheet'
        def parse(document,day,board):
            return [Quote(str(day),board,'00001','Example','HKD','10','11','11','10','12','9','100','1100','')]
        with patch('market_collection.hkex.parse_sheet',side_effect=parse):
            first=collect_hkex(self.store,self.settings,self.u,self.t,date(2021,1,4),'historical',loader,1)
            self.assertEqual(first['reason'],'board_limit')
            second=collect_hkex(self.store,self.settings,self.u,self.t,date(2021,1,4),'historical',loader,1)
        self.assertEqual(second['status'],'complete',second)
        self.assertEqual(calls,['Main Board','GEM'])

if __name__=='__main__':unittest.main()
