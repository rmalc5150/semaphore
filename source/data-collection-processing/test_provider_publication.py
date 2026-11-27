"""Publication claims require an explicit first-party release field."""
from datetime import date
import json
import unittest

from provider_publication import from_bytes, publication_date


TODAY = date(2026, 11, 22)


class ProviderPublicationTests(unittest.TestCase):
    def test_date_precision_and_validation(self):
        self.assertEqual(publication_date('2016-01', TODAY), ('2016-01', 'month'))
        self.assertEqual(publication_date(20160104, TODAY), ('2016-01-04', 'day'))
        self.assertIsNone(publication_date('2016-02-30', TODAY))
        self.assertIsNone(publication_date('2016-02-01 reporting period', TODAY))
        self.assertIsNone(publication_date('2099-01-01', TODAY))

    def test_historical_publications_use_the_public_posted_field(self):
        rows = {'results': [
            {'dt_posted': '2015-12-20T11:00:00Z'},
            {'dt_posted': '2016-02-10T11:00:00Z', 'date': '2016-01-01'},
            {'dt_posted': '2016-01-20T11:00:00Z', 'dt_updated': '2026-01-01'},
        ]}
        result = from_bytes('market_source_219', json.dumps(rows).encode(), 'json',
                            as_of=TODAY, not_before=date(2016, 1, 1))
        self.assertEqual(result, {'value': '2016-01-20', 'precision': 'day',
                                  'basis': 'results.*.dt_posted', 'scope': 'record_in_file'})
        self.assertIsNone(from_bytes('unknown', json.dumps(rows).encode(), 'json', as_of=TODAY))

    def test_html_uses_one_unambiguous_publication_date(self):
        head = b'<html><head><meta property="article:published_time" content="2024-02-03T08:30:00Z">'
        modification = b'<meta property="article:modified_time" content="2026-01-01">'
        end = b'</head><body><meta property="article:published_time" content="2016-01-01"></body></html>'
        self.assertEqual(from_bytes('test', head + modification + end, 'html', as_of=TODAY)['value'], '2024-02-03')
        conflict = b'<meta name="dcterms.issued" content="2024-02-04">'
        self.assertIsNone(from_bytes('test', head + conflict + end, 'html', as_of=TODAY))

    def test_fda_enforcement_uses_report_date(self):
        body = b'{"RESULT":[{"ENFORCEMENTREPORTDT":"02/10/2016","RECALLINITIATIONDT":"01/01/2016"}]}'
        result = from_bytes('fda_ires_recalls', body, 'json', as_of=TODAY)
        self.assertEqual(result['value'], '2016-02-10')

    def test_a3_uses_the_primary_article_calendar(self):
        body = b'''<h1 class="title">North American Robotics Market</h1>
        <div class="meta"><div class="meta-item"><i class="fa-regular fa-calendar"></i> 04/28/2016</div></div>
        <div class="articleContent">2016 first-quarter figures</div>
        <div class="meta-item"><i class="fa-regular fa-calendar"></i> 01/01/2015</div>'''
        self.assertEqual(from_bytes('market_source_270', body, 'html', as_of=TODAY)['value'], '2016-04-28')
        self.assertIsNone(from_bytes('market_source_270',body.replace(b'04/28/2016',b'02/30/2016'),'html',as_of=TODAY))

    def test_ema_day_first_publication_field(self):
        body = b'{"data":[{"first_published_date":"07/01/2016","last_updated_date":"01/05/2026"}]}'
        self.assertEqual(from_bytes('ema_medicines', body, 'json', as_of=TODAY)['value'], '2016-01-07')

    def test_patent_publication_field_uses_query_schema(self):
        document = {'schema': {'fields': [{'name': 'filing_date'}, {'name': 'publication_date'}]},
                    'rows': [{'f': [{'v': '2012-01-01'}, {'v': '2016-01-05'}]}]}
        result = from_bytes('google_patents_bigquery', json.dumps(document).encode(), 'json', as_of=TODAY)
        self.assertEqual(result['value'], '2016-01-05')
