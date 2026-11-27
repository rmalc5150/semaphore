from datetime import date
from io import BytesIO
import gzip
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from constellation import research_feeds as feeds


DAY = '2026-11-19'
WORK_ID = 'https://openalex.org/W123'


def work(identifier=WORK_ID, day=DAY):
    return {'id': identifier, 'publication_date': day, 'updated_date': '2026-11-20T08:00:00'}


class ResearchFeedTests(unittest.TestCase):
    def test_openalex_cursor_and_scope(self):
        page = {'results': [work()], 'meta': {'count': 2, 'next_cursor': 'next'}}
        rows, cursor, total = feeds.openalex_page(json.dumps(page), DAY, '*')
        self.assertEqual((rows[0][0], cursor, total), (WORK_ID, 'next', 2))
        with self.assertRaisesRegex(feeds.FeedError, 'did_not_advance'):
            feeds.openalex_page(json.dumps(page), DAY, 'next')
        with self.assertRaisesRegex(feeds.FeedError, 'outside_query'):
            feeds.openalex_page(json.dumps(page), '2026-11-18', '*')

    def test_invalid_openalex_page_is_not_complete(self):
        for next_cursor in ('', 'next'):
            page = {'results': [], 'meta': {'count': 2, 'next_cursor': next_cursor}}
            with self.assertRaises(feeds.FeedError):
                feeds.openalex_page(json.dumps(page), DAY, '*')

    def test_kaken_fiscal_window_and_offset(self):
        body = b'''<grantAwards>
            <totalResults>101</totalResults><startIndex>101</startIndex><itemsPerPage>100</itemsPerPage>
            <grantAward id="KAKENHI-PROJECT-19K20626" awardNumber="19K20626" projectType="project">
            <modified>2025-05-02T03:04:05Z</modified>
            <summary xml:lang="en"><title>Project</title>
                <periodOfAward searchStartFiscalYear="2019" searchEndFiscalYear="2022"/>
            </summary></grantAward></grantAwards>'''
        rows, cursor, total = feeds.kaken_page(body, 2022, 101, active=True)
        self.assertEqual((rows[0][0], rows[0][2], cursor, total),
                         ('KAKENHI-PROJECT-19K20626', '2025-05-02T03:04:05Z', None, 101))
        self.assertEqual(rows[0][-1]['fiscal_start'], 2019)
        with self.assertRaisesRegex(feeds.FeedError, 'outside_fiscal_scope'):
            feeds.kaken_page(body, 2022, 101)
        with self.assertRaisesRegex(feeds.FeedError, 'pagination_inconsistent'):
            feeds.kaken_page(body, 2019, 1)

    def test_kaken_xml_errors_do_not_create_an_empty_window(self):
        with self.assertRaisesRegex(feeds.FeedError, 'invalid_kaken_response'):
            feeds.kaken_page(b'<error>Forbidden</error>', 2016, 1)
        with self.assertRaisesRegex(feeds.FeedError, 'xml_declaration'):
            feeds.kaken_page(b'<!DOCTYPE doc><grantAwards />', 2016, 1)

    def test_kaken_start_year_is_valid_when_project_end_is_absent(self):
        body = b'''<grantAwards>
            <totalResults>1</totalResults><startIndex>1</startIndex><itemsPerPage>100</itemsPerPage>
            <grantAward id="KAKENHI-PROJECT-18H00006" awardNumber="18H00006" projectType="project">
                <summary xml:lang="ja"><periodOfAward searchStartFiscalYear="2018"/></summary>
                <grantList><grant fiscalYear="2018">
                    <periodOfAward searchStartFiscalYear="2018" searchEndFiscalYear="2018"/>
                </grant></grantList>
            </grantAward></grantAwards>'''
        rows, cursor, total = feeds.kaken_page(body, 2018, 1)
        self.assertEqual((rows[0][-1]['fiscal_start'], rows[0][-1]['fiscal_end'], cursor, total),
                         (2018, None, None, 1))
        with self.assertRaisesRegex(feeds.FeedError, 'outside_fiscal_scope'):
            feeds.kaken_page(body, 2019, 1, active=True)

    def test_kaken_fiscal_boundaries(self):
        self.assertEqual(feeds.fiscal_year(date(2026, 3, 31)), 2025)
        self.assertEqual(feeds.fiscal_year(date(2026, 4, 1)), 2026)

    def test_snapshot_filters_publication_dates_and_preserves_source_payload(self):
        candidates = [work(day=None), work(day='2015-12-31'), work(day='2016-01-01'),
                      work(day='2026-10-14'), work(day='2026-10-15')]
        raw = gzip.compress(b''.join(json.dumps(row).encode() + b'\n' for row in candidates))
        part = {'url': 's3://openalex/data/jsonl/works/updated_date=2026-10-14/part_0000.gz'}
        count = {'scanned': 0, 'retained': 0, 'undated': 0}
        records = [json.loads(line) for line in feeds.snapshot_rows(BytesIO(raw), part, count, '2026-10-14')]
        self.assertEqual(count, {'scanned': 5, 'retained': 2, 'undated': 1})
        self.assertEqual(records[0]['raw_uri'], part['url'])
        self.assertEqual(json.loads(records[0]['payload_json']), candidates[2])

    def test_completed_windows_distinguish_drift_and_duplicate_ids(self):
        evidence = SimpleNamespace()
        batches = [{'id_index': {'uri': 'first', 'sha256': '1'}},
                   {'id_index': {'uri': 'second', 'sha256': '2'}}]
        with patch.object(feeds, 'read_index', side_effect=[['x', 'y'], ['y', 'z']]):
            self.assertEqual(feeds.validate_window(evidence, batches, 4, 4, 4), (3, False))
        with patch.object(feeds, 'read_index', side_effect=[['x', 'y'], ['z']]):
            self.assertEqual(feeds.validate_window(evidence, batches, 3, 3, 4), (3, False))
        with patch.object(feeds, 'read_index', side_effect=[['x', 'y'], ['z']]):
            self.assertEqual(feeds.validate_window(evidence, batches, 3, 3, 3), (3, True))

    def test_pending_snapshot_counts_as_batch_work_only_when_enabled(self):
        control = SimpleNamespace(allowed=lambda: True)
        with patch.object(feeds, 'Evidence') as storage:
            storage.return_value.state.side_effect = [(None, None)]
            self.assertFalse(feeds.history_pending(control))
            storage.return_value.state.side_effect = [({'historical_enabled': True}, 'x'), (None, None)]
            self.assertTrue(feeds.history_pending(control))

    def test_partial_terminal_kaken_history_is_repair_work(self):
        control = SimpleNamespace(allowed=lambda: True)
        with patch.object(feeds, 'Evidence') as storage:
            storage.return_value.state.side_effect = [
                ({'historical_enabled': True}, 'x'), ({'next_part': feeds.SNAPSHOT_PARTS}, 'x'),
                ({'next': 2016}, 'x'), ({'exhausted': True, 'coverage_status': 'partial'}, 'x'),
            ]
            self.assertFalse(feeds.history_pending(control))


if __name__ == '__main__':
    unittest.main()
