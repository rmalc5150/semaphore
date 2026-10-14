from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collection_storage import StorageSettings, write_json
from market_operations import MarketOperations
from market_coverage_exclusions import Exclusions, reconcile_state, report
from collection_alerts import outcome_issues
from research_contract import ROOT, load_json


class ExclusionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.settings = StorageSettings(local_root=temp.name); self.store = self.settings.store()
        config = load_json(ROOT/'config/market-operations.json')
        self.runner = MarketOperations(self.store, self.settings, config,
            load_json(ROOT/'config/company-universe.v0.3.json'), load_json(ROOT/'config/sectors.v1.json'))
        self.runner.symbols = {'A.US': ['listing-a']}
        raw = b'{"IPODate":"2025-02-13"}'
        self.store.put('proof/ipo.json', raw)
        self.registry = Exclusions(self.store, self.runner.prefix, self.runner.symbols)
        self.decision = {'stream_id': self.runner.identity, 'source': 'eodhd_market', 'symbol': 'A.US',
            'listing_ids': ['listing-a'], 'start': '2021-01-01', 'end_exclusive': '2025-02-13',
            'reason': 'pre_ipo', 'boundary_date': '2025-02-13', 'explanation': 'Listing had not begun trading.',
            'evidence': [{'key': 'proof/ipo.json', 'sha256': hashlib.sha256(raw).hexdigest(), 'source_url': 'https://example.test/ipo'}],
            'reviewer': 'test-reviewer', 'reviewed_at': '2026-09-27T19:00:00Z'}

    def state(self):
        return {'symbols': {'A.US': {'scan_next_date': '2026-09-01', 'next_date': '2021-01-01',
            'window_start': '2021-01-01', 'window_end_exclusive': '2022-01-01',
            'last_result': {'status': 'partial', 'reason': 'market_empty_price_window_unverified', 'manifest': 'old-proof'},
            'gaps': {'2021-01-01': {'end_exclusive': '2022-01-01', 'manifest': 'old-proof', 'reason': 'market_empty_price_window_unverified'}}}}}

    def test_exact_listing_full_interval_only_and_evidence_required(self):
        identity = self.registry.add(self.decision)
        self.assertEqual(self.registry.match('A.US', '2021-01-01', '2022-01-01')['id'], identity)
        self.assertIsNone(self.registry.match('B.US', '2021-01-01', '2022-01-01'))
        self.assertIsNone(self.registry.match('A.US', '2025-01-01', '2026-01-01'))
        self.registry.listings = {'A.US': ['replacement-listing']}
        self.assertIsNone(self.registry.match('A.US', '2021-01-01', '2022-01-01'))
        self.registry.listings = self.runner.symbols
        for change in [{'end_exclusive': '2026-01-01'}, {'explanation': ''}, {'evidence': []},
                       {'stream_id': 'another-stream'}]:
            with self.assertRaises(ValueError):
                self.registry.add({**self.decision, **change})
        bad = deepcopy(self.decision); bad['evidence'][0]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'evidence hash mismatch'):
            self.registry.add(bad)

    def test_review_moves_gap_without_faking_collection_and_revoke_restores_it(self):
        identity = self.registry.add(self.decision)
        original = self.state()
        updated = reconcile_state(original, 'historical', self.registry)
        item = updated['symbols']['A.US']
        self.assertEqual(item['gaps'], {})
        self.assertEqual(item['next_date'], '2026-09-01')
        self.assertEqual(item['last_result']['status'], 'excluded')
        self.assertEqual(item['excluded_windows']['2021-01-01']['prior_manifest'], 'old-proof')
        self.assertNotIn('last_complete', item)
        self.assertEqual(outcome_issues(updated), set())
        self.assertEqual(reconcile_state(updated, 'historical', self.registry), updated)
        self.assertTrue(original['symbols']['A.US']['gaps'])
        self.registry.revoke(identity, 'reviewer', 'Corrected listing date requires collection')
        restored = reconcile_state(updated, 'historical', self.registry)['symbols']['A.US']
        self.assertEqual(restored['next_date'], '2021-01-01')
        self.assertEqual(restored['gaps']['2021-01-01']['manifest'], 'old-proof')
        self.assertEqual(restored['excluded_windows'], {})
        self.assertEqual(restored['last_result']['reason'], 'coverage_exclusion_revoked')
        self.assertTrue(self.store.get(self.registry.document['latest_event']))
        with self.assertRaisesRegex(ValueError, 'new review'):
            self.registry.add(self.decision)

    def test_skips_provider_and_publication_only_for_excluded_windows(self):
        self.registry.add(self.decision)
        calls = []
        def collect(*args):
            calls.append((args[7], str(args[5])))
            return {'status': 'complete', 'manifest': 'real-data'}
        with patch('market_operations.collect_eodhd', side_effect=collect), patch('market_operations.enqueue') as publish:
            result = self.runner.run(None, date(2026,9,27))
        self.assertEqual(calls, [('daily', '2026-09-01')])
        self.assertEqual(publish.call_count, 1)
        self.assertEqual(result['excluded_windows']['historical'], 1)
        state = json.loads(self.store.get(self.runner.prefix+'/historical.json').body)['symbols']['A.US']
        self.assertEqual(state['next_date'], '2022-01-01')
        self.assertNotIn('last_complete', state)
        self.assertEqual(outcome_issues(result), set())

    def test_reconciliation_reopens_revoked_daily_windows(self):
        identity = self.registry.add(self.decision)
        state = self.state(); state['symbols']['A.US'].pop('gaps')
        state['symbols']['A.US'].pop('scan_next_date')  # Legacy daily state.
        updated = reconcile_state(state, 'daily', self.registry)
        self.assertEqual(updated['symbols']['A.US']['next_date'], '2022-01-01')
        self.registry.revoke(identity, 'reviewer', 'Wrong IPO date')
        reopened = reconcile_state(updated, 'daily', self.registry)
        self.assertEqual(reopened['symbols']['A.US']['next_date'], '2021-01-01')
        self.assertEqual(reopened['symbols']['A.US']['last_result']['status'], 'partial')

    def test_daily_gap_review_and_revocation_preserve_forward_scan(self):
        identity = self.registry.add(self.decision)
        updated = reconcile_state(self.state(), 'daily', self.registry)
        item = updated['symbols']['A.US']
        self.assertEqual(item['next_date'], '2026-09-01')
        self.assertEqual(item['gaps'], {})
        self.registry.revoke(identity, 'reviewer', 'Wrong IPO date')
        reopened = reconcile_state(updated, 'daily', self.registry)['symbols']['A.US']
        self.assertEqual(reopened['next_date'], '2021-01-01')
        self.assertEqual(reopened['scan_next_date'], '2026-09-01')
        self.assertEqual(reopened['gaps']['2021-01-01']['manifest'], 'old-proof')

    def test_holiday_exclusion_does_not_hide_first_reopened_trading_day(self):
        decision = {k: v for k, v in self.decision.items() if k != 'boundary_date'}
        decision.update(start='2026-10-01', end_exclusive='2026-10-08',
                        reason='documented_unavailable', explanation='Official exchange closure.')
        self.registry.add(decision)
        key = self.runner.prefix + '/daily.json'
        from collection_storage import write_json
        write_json(self.store, key, {'symbols': {'A.US': {'next_date': '2026-10-01'}}})
        with patch('market_operations.collect_eodhd', return_value={'status': 'complete', 'manifest': 'prices'}) as collect, \
             patch('market_operations.enqueue') as publish:
            self.runner.run(None, date(2026,10,8))
            self.assertFalse(any(c.args[7] == 'daily' for c in collect.call_args_list))
            collect.reset_mock(); publish.reset_mock()
            self.runner.run(None, date(2026,10,9))
            daily = [c for c in collect.call_args_list if c.args[7] == 'daily']
            self.assertEqual(len(daily), 1)
            self.assertEqual(daily[0].args[5:7], (date(2026,10,1), date(2026,10,9)))
            self.assertTrue(any(c.args[5] == 'daily' for c in publish.call_args_list))

    def test_other_gap_and_overlap_remain_unresolved(self):
        self.registry.add(self.decision)
        state = self.state(); state['symbols']['A.US']['gaps']['2025-01-01'] = {
            'end_exclusive': '2026-01-01', 'reason': 'market_empty_price_window_unverified'}
        updated = reconcile_state(state, 'historical', self.registry)
        self.assertEqual(updated['symbols']['A.US']['next_date'], '2025-01-01')
        review = report({'historical': updated}, self.registry)
        self.assertEqual(review['lanes']['historical']['unresolved_symbols'], 1)
        self.assertEqual(len(review['lanes']['historical']['excluded_windows']), 1)

    def test_monitor_uses_scoped_review_not_stale_journal_or_fake_collection(self):
        from collection_health_exporter import inspect_job
        from datetime import datetime, timezone
        self.registry.add(self.decision)
        history = self.state()
        daily = {'symbols': {'A.US': {'next_date': '2026-09-27',
                                     'last_result': {'status': 'complete', 'manifest': 'real'}}}}
        docs = {self.registry.key: self.registry.document,
                self.runner.prefix + '/historical.json': history,
                self.runner.prefix + '/daily.json': daily}
        class Evidence:
            def read(self, key):
                return docs.get(key), None, '2026-09-27T18:00:00Z'
            def confirmed(self, value):
                return []
        stale = [{'at': '2026-09-27T18:00:00Z', 'value': {'status': 'partial',
                  'reason': 'market_empty_price_window_unverified',
                  'symbols_with_unresolved_windows': {'historical': 1}}}]
        policy = {'progress_keys': [self.runner.prefix + '/' + lane + '.json' for lane in ('daily', 'historical')]}
        props = [{'ActiveState': 'inactive', 'Result': 'success', 'ExecMainStatus': '0'},
                 {'UnitFileState': 'enabled', 'ActiveState': 'active'}]
        with patch('collection_health_exporter.properties', side_effect=props), patch(
                'collection_health_exporter.json_reports', return_value=(stale, [], None)):
            result = inspect_job('optima-market-collection.service', policy, Evidence(), 0,
                                 datetime(2026,9,27,20,tzinfo=timezone.utc).timestamp())
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['coverage_review']['excluded_windows'], 1)
        self.assertIn('unresolved_market_coverage', result['coverage_resolutions'])
        self.assertIsNone(result['progress']['last_verified_at'])
        self.assertFalse(result['progress']['pending'])

    def test_review_recovers_only_supported_coverage_alerts_not_service_failures(self):
        from collection_alerts import evaluate, stamp
        from test_collection_alerts import health, CONFIG, UNIT, NOW
        unit = 'optima-market-collection.service'
        config = deepcopy(CONFIG); config['jobs'][unit] = config['jobs'].pop(UNIT)
        snapshot = health(progress={'pending': False, 'token': 'one', 'last_verified_at': None})
        snapshot['jobs'][unit] = snapshot['jobs'].pop(UNIT)
        resolutions = {code: {'at': stamp(NOW), 'basis': 'reviewed_scoped_exclusions', 'registry_keys': ['registry']}
                       for code in ['market_empty_price_window_unverified', 'unresolved_market_coverage', 'service_failed']}
        snapshot['jobs'][unit]['coverage_resolutions'] = resolutions
        prior = {'active': {unit + ':' + code: {'unit': unit, 'code': code, 'severity': 'low',
                   'detail': code, 'evidence_at': stamp(NOW-60)} for code in resolutions}}
        alerts, _ = evaluate(snapshot, prior, config, NOW)
        self.assertEqual(set(alerts), {unit + ':service_failed'})
        snapshot['jobs'][unit]['issues'] = [{'code': 'unresolved_market_coverage', 'severity': 'low', 'detail': 'Another gap'}]
        alerts, _ = evaluate(snapshot, prior, config, NOW)
        self.assertIn(unit + ':unresolved_market_coverage', alerts)

    def test_tampered_registry_rejected_and_repeated_apply_idempotent(self):
        identity = self.registry.add(self.decision)
        first = self.registry.document['latest_event']
        self.assertEqual(self.registry.add(self.decision), identity)
        self.assertEqual(self.registry.document['latest_event'], first)
        doc = deepcopy(self.registry.document); doc['decisions'][identity]['decision']['end_exclusive'] = '2024-01-01'
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
            Exclusions(None, self.runner.prefix, document=doc)


if __name__ == '__main__':
    unittest.main()
