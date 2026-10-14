from datetime import date
import tempfile
import unittest
from unittest.mock import Mock,patch
from collection_storage import StorageSettings, write_json
from collection_operations import load_stored
from market_operations import MarketOperations,Budget
from regulatory_collection import SourceIssue
from research_contract import ROOT,load_json

class RunnerTests(unittest.TestCase):
    def test_empty_closed_daily_month_does_not_block_current_month(self):
        self.runner.symbols = {'A.US': ['listing-a']}
        key = self.runner.prefix + '/daily.json'
        write_json(self.store, key, {'symbols': {'A.US': {
            'retry_after': '2026-10-06', 'empty_window_diagnosed': True,
            'window_start': '2026-09-01', 'window_end_exclusive': '2026-10-01',
            'last_result': {'status': 'partial', 'reason': 'market_empty_price_window_unverified'}}}})
        requests = []
        def collect(*args):
            if args[7] == 'daily':
                requests.append((str(args[5]), str(args[6])))
                if args[5].month == 9:
                    return {'status': 'partial', 'reason': 'market_empty_price_window_unverified', 'manifest': 'sept-gap'}
            return {'status': 'complete', 'manifest': 'prices'}
        with patch('market_operations.collect_eodhd', side_effect=collect), patch('market_operations.enqueue') as queue:
            self.runner.run(None, date(2026,10,5))
            result = self.runner.run(None, date(2026,10,5))
            self.runner.run(None, date(2026,10,5))
        item = load_stored(self.store, key)[0]['symbols']['A.US']
        self.assertEqual(requests, [('2026-09-01','2026-10-01'), ('2026-10-01','2026-10-05'),
                                    ('2026-09-01','2026-10-01')])
        self.assertEqual(item['scan_next_date'], '2026-10-05')
        self.assertEqual(item['next_date'], '2026-09-01')
        self.assertEqual(item['gaps']['2026-09-01']['manifest'], 'sept-gap')
        self.assertEqual(result['symbols_with_unresolved_windows']['daily'], 1)
        self.assertEqual(len([c for c in queue.call_args_list if c.args[5] == 'daily']), 1)

    def test_gap_retries_rotate_and_remove_only_verified_gap(self):
        self.runner.symbols = {'A.US': ['listing-a']}
        key = self.runner.prefix + '/historical.json'
        write_json(self.store, key, {'symbols': {'A.US': {
            'scan_next_date': '2026-09-01', 'next_date': '2021-01-01',
            'gaps': {'2021-01-01': {'manifest': 'old'}, '2022-01-01': {'manifest': 'later'}}}}})
        attempted = []
        def collect(*args):
            if args[7] == 'daily':
                return {'status': 'complete', 'manifest': 'daily'}
            attempted.append(str(args[5]))
            return ({'status': 'partial', 'reason': 'market_empty_price_window_unverified', 'manifest': 'empty'}
                    if args[5].year == 2021 else {'status': 'complete', 'manifest': 'recovered'})
        with patch('market_operations.collect_eodhd', side_effect=collect), patch('market_operations.enqueue'):
            self.runner.run(None, date(2026,9,27))
            self.runner.run(None, date(2026,9,28))
        state, _ = load_stored(self.store, key)
        self.assertEqual(attempted, ['2021-01-01', '2022-01-01'])
        self.assertEqual(list(state['symbols']['A.US']['gaps']), ['2021-01-01'])
        self.assertEqual(state['symbols']['A.US']['next_date'], '2021-01-01')

    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.settings=StorageSettings(local_root=t.name);self.store=self.settings.store()
        config=load_json(ROOT/'config/market-operations.json')
        self.runner=MarketOperations(self.store,self.settings,config,load_json(ROOT/'config/company-universe.v0.3.json'),load_json(ROOT/'config/sectors.v1.json'))
        self.runner.symbols={'A.US':['listing-a'],'B.US':['listing-b']}
    def test_failure_isolated_and_no_advance_or_publication(self):
        def collect(*args):return {'status':'failed','reason':'unavailable'} if args[4]=='A.US' else {'status':'complete','manifest':'m'}
        with patch('market_operations.collect_eodhd',side_effect=collect),patch('market_operations.enqueue') as queue:
            self.runner.run(None,date(2026,9,24))
        state,_=load_stored(self.store,self.runner.prefix+'/historical.json')
        self.assertNotIn('next_date',state['symbols']['A.US'])
        self.assertEqual(state['symbols']['B.US']['next_date'],'2022-01-01')
        self.assertEqual(queue.call_count,2)
    def test_daily_month_refresh_has_stable_partition_window(self):
        with patch('market_operations.collect_eodhd',return_value={'status':'complete','manifest':'m'}),patch('market_operations.enqueue') as queue:
            self.runner.run(None,date(2026,9,24))
            first=[c.args[3:6] for c in queue.call_args_list if c.args[5]=='daily'];queue.reset_mock()
            self.runner.run(None,date(2026,9,25))
            second=[c.args[3:6] for c in queue.call_args_list if c.args[5]=='daily']
        self.assertEqual(first,second)
    def test_ambiguous_request_consumes_budget_before_network(self):
        opener=Mock(side_effect=TimeoutError)
        b=Budget(self.store,{'max_requests_per_day':1},2,opener)
        with self.assertRaises(TimeoutError):b('url')
        with self.assertRaises(SourceIssue):b('url')
        self.assertEqual(opener.call_count,1)

    def test_empty_historical_year_does_not_block_later_prices_or_erase_gap(self):
        self.runner.symbols = {'A.US': ['listing-a']}
        def collect(*args):
            if args[7] == 'historical' and args[5].year == 2021:
                return {'status': 'partial', 'reason': 'market_empty_price_window_unverified', 'manifest': 'empty-proof'}
            return {'status': 'complete', 'manifest': 'prices'}
        with patch('market_operations.collect_eodhd', side_effect=collect), patch('market_operations.enqueue'):
            self.runner.run(None, date(2026,9,26))
            result = self.runner.run(None, date(2026,9,26))
        state, _ = load_stored(self.store, self.runner.prefix+'/historical.json')
        symbol = state['symbols']['A.US']
        self.assertEqual(symbol['scan_next_date'], '2023-01-01')
        self.assertEqual(symbol['next_date'], '2021-01-01')
        self.assertEqual(symbol['gaps']['2021-01-01']['manifest'], 'empty-proof')
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['symbols_with_unresolved_windows']['historical'], 1)

if __name__=='__main__':unittest.main()
