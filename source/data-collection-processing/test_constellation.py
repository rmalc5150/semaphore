"""Safety checks for bounded adapters, immutable readbacks and catalog lineage."""
from datetime import datetime, timezone
import io
import json
import threading
import unittest
from unittest.mock import Mock, patch

from constellation.catalog import build, coverage
from constellation.control import canonical, job_id
from constellation.sources import PROVIDERS, VERSION, request, parse, observation, validate_spec
from constellation.worker import collect, put_verified


def spec(source='usgs_earthquakes'):
    return {'source_key': source, 'dataset': PROVIDERS[source]['dataset'], 'geography': 'global',
        'start': '2016-01-01', 'end': '2016-01-02', 'edition': 'current_retrieval',
        'extractor_version': VERSION, 'parameters': {}}


def earthquake(identity='us2016a', time=1451606400000):
    return {'id': identity, 'properties': {'time': time, 'url': 'https://earthquake.usgs.gov/example'},
        'geometry': {'type': 'Point', 'coordinates': [0, 0, 10]}}


class SourceTests(unittest.TestCase):
    def test_news_expansion_preserves_daily_stream_identity(self):
        from news_operations import NewsOperations
        old = {'daily_config': 'daily.json', 'historical_config': 'history.json', 'historical_start': '2021-01-01'}
        new = {**old, 'historical_start': '2016-01-01', 'state_identity_historical_start': '2021-01-01'}
        documents = {'daily.json': {'universe': 'universe.json', 'taxonomy': 'taxonomy.json'},
            'history.json': {'universe': 'universe.json'}, 'universe.json': {}, 'taxonomy.json': {}}
        with patch('news_operations.load_json', side_effect=lambda p: documents[p.name]):
            self.assertEqual(NewsOperations(None, None, old).prefix, NewsOperations(None, None, new).prefix)

    def test_market_expansion_preserves_daily_stream_identity_and_old_progress(self):
        from market_operations import MarketOperations
        universe = {'listings': [], 'external_identifiers': []}
        old = {'historical_start': '2021-01-01'}
        new = {'historical_start': '2016-01-01', 'state_identity_historical_start': '2021-01-01'}
        previous = MarketOperations(None, None, old, universe, {})
        expanded = MarketOperations(None, None, new, universe, {})
        self.assertEqual(previous.prefix, expanded.prefix)
        item = {'next_date': '2026-09-01', 'last_complete': {'manifest': 'retained'}, 'excluded_windows': {'old': 'retained'}}
        actual = expanded.expand_historical_scope(item)
        self.assertEqual(actual['scan_next_date'], '2026-09-01')
        self.assertEqual(actual['last_complete'], item['last_complete'])
        self.assertEqual(actual['excluded_windows'], item['excluded_windows'])
        self.assertEqual(sorted(actual['gaps']), [str(year) + '-01-01' for year in range(2016, 2021)])
        self.assertEqual(expanded.expand_historical_scope(actual), actual)
        self.assertNotIn('gaps', item)

    def test_catalog_lineage_and_pauses(self):
        registry = build()
        self.assertEqual(len(registry['sources']), 158)
        self.assertEqual(sum(s['lineage'] == 'existing' for s in registry['sources']), 64)
        self.assertEqual({s['catalog_entry'] for s in registry['sources'] if s['readiness'] == 'paused'}, {12, 44, 59, 61})
        self.assertEqual(len(list(coverage(registry))), 158 * 11)
        self.assertFalse(any(r['verified_complete'] for r in coverage(registry)))

    def test_idempotent_spec_identity(self):
        self.assertEqual(job_id(spec()), job_id(dict(reversed(list(spec().items())))))
        self.assertNotEqual(job_id(spec()), job_id({**spec(), 'end': '2016-01-03'}))

    def test_no_arbitrary_endpoint_or_legacy_shared_runtime(self):
        for change in ({'parameters': {'url': 'https://example.com'}}, {'source_key': 'eodhd'},
                {'start': '2015-12-31'}, {'end': '2016-02-01'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_spec({**spec(), **change})

    def test_exclusive_usgs_boundary(self):
        _, params = request(spec(), None)
        self.assertEqual(params['endtime'], '2016-01-01T23:59:59.999')
        with self.assertRaises(ValueError):
            parse(spec(), canonical({'type': 'FeatureCollection', 'features': [earthquake(time=1451692800000)]}), None)

    def test_error_response_not_empty_success(self):
        for source, body in [('usgs_earthquakes', b'{"error":"unavailable"}'),
                ('nsf_awards', b'{"response":{"error":"denied"}}')]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse(spec(source), body, None)

    def test_only_documented_usgs_no_content_is_empty_success(self):
        self.assertEqual(parse(spec(), b'', None, http_status=204), ([], None))
        for source in ('nsf_awards', 'arxiv'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse(spec(source), b'', None, http_status=204)

    def test_usgs_pagination_and_missingness(self):
        rows, cursor = parse(spec(), canonical({'type': 'FeatureCollection', 'features': [earthquake()]}), None)
        self.assertIsNone(cursor)
        row = observation(spec(), rows[0], 's3://bucket/raw', '2026-10-26T00:00:00Z')
        self.assertIsNone(row['available_to_market_at'])
        self.assertEqual(row['observation_start_at'], '2016-01-01T00:00:00+00:00')
        self.assertIn('historical_vintage_not_verified', row['quality_flags'])

    def test_nsf_validates_award_date_not_project_start(self):
        row = {'id': '1', 'date': '01/01/2016', 'startDate': '01/01/2017'}
        self.assertEqual(parse(spec('nsf_awards'), canonical({'response': {'award': [row]}}), None)[0], [row])
        with self.assertRaises(ValueError):
            parse(spec('nsf_awards'), canonical({'response': {'award': [{**row, 'date': '01/02/2016'}]}}), None)

    def test_nsf_stable_zero_based_pagination_and_total(self):
        _,params=request(spec('nsf_awards'),None)
        self.assertEqual(params['offset'],0)
        self.assertEqual(params['sortKey'],'awardNumber')
        row={'id':'1','date':'01/01/2016'}
        body=canonical({'response':{'award':[row],'metadata':{'offset':25,'totalCount':26}}})
        self.assertIsNone(parse(spec('nsf_awards'),body,25)[1])
        with self.assertRaisesRegex(ValueError,'offset mismatch'):
            parse(spec('nsf_awards'),body,0)
        truncated=canonical({'response':{'award':[],'metadata':{'offset':25,'totalCount':26}}})
        with self.assertRaisesRegex(ValueError,'pagination incomplete'):
            parse(spec('nsf_awards'),truncated,25)

    def test_arxiv_empty_page_cannot_hide_remaining_results(self):
        body = b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:os="http://a9.com/-/spec/opensearch/1.1/"><os:totalResults>1</os:totalResults></feed>'
        with self.assertRaises(ValueError):
            parse(spec('arxiv'), body, None)

    def test_corrupt_s3_readback_rejected(self):
        control = Mock()
        control.config = {'bucket': 'bucket'}
        control.s3.get_object.return_value = {'Body': Mock(iter_chunks=lambda size: iter([b'corrupt']))}
        with self.assertRaises(ValueError):
            put_verified(control, 'raw', b'original', 'application/json')

    def test_duplicate_page_never_gets_complete_manifest(self):
        control = Mock()
        control.config = {'prefix': 'test', 'bucket': 'bucket'}
        from contextlib import nullcontext
        control.provider_connection.side_effect=lambda *args:nullcontext()
        response = Mock(status_code=200, url='https://earthquake.usgs.gov/', headers={})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = iter([b'{}'])
        saved = []
        def put(c, key, body, kind):
            saved.append(key)
            return {'uri': 's3://bucket/' + key, 'sha256': 'x'}
        with patch('constellation.worker.requests.get', return_value=response), patch('constellation.worker.put_verified', side_effect=put), patch('constellation.worker.parse', return_value=([earthquake(), earthquake()], None)):
            with self.assertRaises(ValueError):
                collect(control, spec(), 'token', threading.Event())
        self.assertFalse(any(k.endswith('/manifest.json') for k in saved))


if __name__ == '__main__':
    unittest.main()
