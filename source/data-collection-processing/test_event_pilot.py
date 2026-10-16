"""Offline pilot checks: commit gates, misleading snapshots, correlation and replay."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import event_pilot as pilot


ROOT = Path(__file__).resolve().parent
CONFIG = pilot.load(ROOT / 'config/event-pilot.v1.json')
TAXONOMY = pilot.load(ROOT / 'config/sectors.v1.json')


def sample(source, sid, data, dataset='specialist_inputs', identity='one', url='https://example.org/source'):
    return {'source_id': sid,
            'record': pilot.special_record(source, dataset, identity, data, url, '2026-10-15T00:00:00Z'),
            'provenance': {'kind': 'synthetic_fixture'}}


class Body(io.BytesIO):
    pass


class GetOnly:
    def __init__(self, values):
        self.values, self.calls = values, []

    def get_object(self, **kw):
        self.calls.append(kw['Key'])
        body = self.values[kw['Key']]
        return {'Body': Body(body), 'ContentLength': len(body), 'ETag': 'test'}


class EventPilotTests(unittest.TestCase):
    def test_inventory_covers_all_68_rules(self):
        inventory = pilot.load(ROOT / CONFIG['inventory'])
        self.assertEqual({r['source_id'] for r in inventory['sources']}, set(CONFIG['source_rules']))

    def test_first_prefers_official_top_level_identity(self):
        self.assertEqual(pilot.first({'assets': [{'id': 999}], 'id': 12}, {'id'})[1], 12)

    def test_identical_replay_does_not_duplicate_observation(self):
        s = sample('github_sdk', 'S46', {'id': 12, 'name': 'v1'})
        events, outcomes = pilot.construct([s, copy.deepcopy(s)], CONFIG, TAXONOMY)
        self.assertEqual((len(events), len(outcomes), len(events[0]['evidence'])), (1, 1, 1))
        self.assertFalse(events[0]['point_in_time_eligible'])
        self.assertEqual(events, pilot.construct([s], CONFIG, TAXONOMY)[0])

    def test_doi_correlates_across_collectors_but_retains_evidence(self):
        a = sample('europe_pmc', 'S28', {'doi': '10.1/ABC', 'title': 'Research'}, identity='a')
        b = sample('crossref_proceedings', 'S29', {'DOI': '10.1/abc', 'title': ['Research']},
                   dataset='conference_records', identity='b')
        events, _ = pilot.construct([a, b], CONFIG, TAXONOMY)
        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0]['evidence']), 2)
        self.assertIsNone(events[0]['independent_reporting_count'])
        self.assertIsNone(events[0]['occurrence'])

    def test_doi_in_references_does_not_identify_the_article(self):
        s = sample('europe_pmc', 'S28', {'title': 'New article', 'references': [{'doi': '10.1/other'}]})
        events, _ = pilot.construct([s], CONFIG, TAXONOMY)
        self.assertEqual(events, [])

    def test_pubmed_xml_extraction_uses_article_identifier(self):
        xml = '<PubmedArticle><MedlineCitation><Article><ArticleTitle>A test paper</ArticleTitle></Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1/own</ArticleId></ArticleIdList></PubmedData></PubmedArticle>'
        s = sample('pubmed_abstracts', 'S27', {'pmid': '123', 'article_xml': xml})
        e = pilot.construct([s], CONFIG, TAXONOMY)[0][0]
        self.assertEqual(e['match_key'], {'namespace': 'doi', 'value': '10.1/own'})
        self.assertEqual(e['summary'], 'A test paper')

    def test_conference_title_array_is_not_replaced_by_meeting_name(self):
        s = sample('crossref_proceedings', 'S29', {'DOI': '10.1/paper', 'title': ['Specific paper'],
                     'event': {'name': 'The whole meeting'}}, dataset='conference_records')
        self.assertEqual(pilot.construct([s], CONFIG, TAXONOMY)[0][0]['summary'], 'Specific paper')

    def test_allowance_notice_is_not_a_rejection_or_grant(self):
        s = sample('uspto_odp', 'S39', {'source_document_id': 'd1', 'application_number': '123', 'document_type': 'NOA'}, dataset='patent_office_actions')
        self.assertEqual(pilot.construct([s], CONFIG, TAXONOMY)[0][0]['event_type'], 'patent.allowance_notice')

    def test_historical_complete_response_letter_not_current_approval(self):
        s = sample('fda_openfda', 'S19', {'letter_type': 'COMPLETE RESPONSE', 'file_name': 'letter.pdf', 'approval_status': 'Approved'})
        e = pilot.construct([s], CONFIG, TAXONOMY)[0][0]
        self.assertEqual(e['event_type'], 'regulatory.letter_disclosure')
        self.assertIn('COMPLETE RESPONSE', e['summary'])
        self.assertNotIn('Approved', e['summary'])

    def test_search_receipt_scan_skips_raw_json_arrays(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / 'reports/weekly-readiness-2026-10-09/captures'
            p.mkdir(parents=True)
            (p / 'raw-response.json').write_text('[]')
            outcomes = []
            with patch.object(pilot, 'ROOT', Path(root)):
                pilot.capture_search(None, CONFIG, [], outcomes)
            self.assertEqual(outcomes[0]['status'], 'no_verified_sample')

    def test_separate_patent_documents_not_family_deduplicated(self):
        rows = [sample('google_patents_bigquery', 'S38', {
            'publication_number': number, 'publication_date': '2026-09-01', 'family_id': 'same'},
            dataset='patent_records', identity=number) for number in ['US-1-A1', 'US-2-A1']]
        self.assertEqual(len(pilot.construct(rows, CONFIG, TAXONOMY)[0]), 2)

    def test_application_snapshot_not_publication(self):
        s = sample('uspto_odp', 'S39', {'application_number': '123'}, dataset='patent_records')
        events, outcomes = pilot.construct([s], CONFIG, TAXONOMY)
        self.assertFalse(events)
        self.assertEqual(outcomes[0]['outcome'], 'needs_evidence')

    def test_prosecution_doc_key_is_not_application_only(self):
        rows = [sample('uspto_odp', 'S39', {'source_document_id': doc, 'application_number': '123', 'document_type': 'CTNF'},
                        dataset='patent_office_actions', identity=doc) for doc in ['d1', 'd2']]
        events, _ = pilot.construct(rows, CONFIG, TAXONOMY)
        self.assertEqual(len(events), 2)
        self.assertEqual({e['event_type'] for e in events}, {'patent.office_action'})

    def test_context_snapshots_do_not_manufacture_event(self):
        for source, sid in [('eodhd', 'S02'), ('trade_screening', 'S52'), ('cms_payments_catalog', 'S34'),
                            ('dataforseo', 'S65'), ('eia_battery_generators', 'S56')]:
            events, outcomes = pilot.construct([sample(source, sid, {'name': 'Company X', 'status': 'active'})], CONFIG, TAXONOMY)
            self.assertFalse(events, source)
            self.assertEqual(outcomes[0]['outcome'], 'context_only')

    def test_one_document_two_developments_remain_candidates(self):
        s = sample('finlight', 'S13', {'title': 'Company appointed a new CEO and launches a robot system.'}, dataset='news_articles')
        events, _ = pilot.construct([s], CONFIG, TAXONOMY)
        self.assertEqual({e['event_type'] for e in events}, {'personnel.appointment', 'product.launch'})
        self.assertTrue(all(e['review_status'] == 'pending' for e in events))

    def test_unrelated_text_not_converted_to_material_claim(self):
        s = sample('finlight', 'S13', {'title': 'A review of the industry'}, dataset='news_articles')
        events, outcomes = pilot.construct([s], CONFIG, TAXONOMY)
        self.assertEqual(events, [])
        self.assertEqual(outcomes[0]['outcome'], 'needs_evidence')

    def test_talent_acquisition_and_capital_tables_are_not_new_deals(self):
        for text in ['Trends shaping talent acquisition and R&D hiring.',
                     'FY23 FY24 FY25 FY26 Acquisition Capital Deployed $18.7B']:
            events, _ = pilot.construct([sample('personnel_archive', 'S15', {'text': text})], CONFIG, TAXONOMY)
            self.assertEqual(events, [])
        events, _ = pilot.construct([sample('finlight', 'S13', {'title': 'Acme announces acquisition of robotics maker Beta.'})], CONFIG, TAXONOMY)
        self.assertEqual(events[0]['event_type'], 'corporate.acquisition')

    def test_existing_incomplete_sqlite_cannot_be_endorsed_on_replay(self):
        import sqlite3
        events, outcomes = pilot.construct([sample('github_sdk', 'S46', {'id': 1, 'name': 'v1'})], CONFIG, TAXONOMY)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'events.sqlite3'
            pilot.create_sqlite(path, events, outcomes)
            pilot.create_sqlite(path, events, outcomes)
            with sqlite3.connect(path) as conn:
                conn.execute('DELETE FROM evidence')
            with self.assertRaisesRegex(ValueError, 'incomplete or changed'):
                pilot.create_sqlite(path, events, outcomes)

    def test_classifier_never_promotes_search_query_to_verified_sector(self):
        s = sample('github_sdk', 'S46', {'id': 4, 'name': 'SDK'})
        s['record']['payload']['candidate_sector_ids'] = ['robotics', 'invalid_sector']
        e = pilot.construct([s], CONFIG, TAXONOMY)[0][0]
        self.assertEqual(len(e['classifications']), 1)
        self.assertEqual(e['classifications'][0]['status'], 'candidate')
        self.assertIsNone(e['classifications'][0]['subsector_id'])

    def test_frozen_sample_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            pilot.jsonl(p / 'samples.jsonl', [])
            pilot.write(p / 'capture.json', {'status': 'complete', 'samples_sha256': 'wrong'})
            with self.assertRaisesRegex(ValueError, 'Sample file hash'):
                pilot.verify_capture(p)

    def test_bounded_reader_does_not_load_oversize_body(self):
        with tempfile.TemporaryDirectory() as root:
            reader = pilot.SnapshotReader(GetOnly({'prefix/file': b'123456'}), 'bucket', 'prefix', root, 20)
            with self.assertRaisesRegex(pilot.MissingEvidence, 'object_size'):
                reader.get('file', 3)
            self.assertEqual(reader.downloaded, 0)

    def test_commit_manifest_must_be_in_terminal_history(self):
        task = {'source': 'github_sdk', 'dataset': 'specialist_inputs'}
        tid = 'task_' + pilot.digest(task)
        key = 'raw/source=github_sdk/dataset=specialist_inputs/ingestion_date=2026-10-15/run_id=run_abc/page.jsonl'
        row = {'key': key, 'source': 'github_sdk', 'dataset': 'specialist_inputs', 'sha256': 'hash', 'records': 1, 'bytes': 10}
        manifest_key = 'manifests/collection_runs/source=github_sdk/dataset=specialist_inputs/run_abc/final.json'
        manifest = {'task': task, 'task_id': tid, 'pages': [{'batches': [row]}], 'status': 'complete'}
        head = {'task_id': tid, 'task': task, 'terminal_history': []}
        values = {'prefix/' + manifest_key: pilot.encoded(manifest),
                  'prefix/checkpoints/' + tid + '/head.json': pilot.encoded(head)}
        with tempfile.TemporaryDirectory() as root:
            reader = pilot.SnapshotReader(GetOnly(values), 'bucket', 'prefix', root, 10000)
            with self.assertRaisesRegex(pilot.MissingEvidence, 'uncommitted_terminal'):
                pilot.prove_batch(reader, row, 10000)
            head['terminal_history'].append(manifest_key)
            values['prefix/checkpoints/' + tid + '/head.json'] = pilot.encoded(head)
            reader = pilot.SnapshotReader(GetOnly(values), 'bucket', 'prefix', root, 10000)
            self.assertEqual(pilot.prove_batch(reader, row, 10000)['source_status'], 'complete')

    def test_feedback_rejects_stale_version_and_does_not_promote_event(self):
        events, _ = pilot.construct([sample('github_sdk', 'S46', {'id': 1, 'name': 'v1'})], CONFIG, TAXONOMY)
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            pilot.jsonl(p / 'events.jsonl', events)
            e = events[0]
            decision = {'event_id': e['event_id'], 'event_version_id': 'wrong',
                        'decision': 'accept_candidate', 'reviewer': 'tester', 'reason': 'Fixture check'}
            pilot.jsonl(p / 'bad.jsonl', [decision])
            with self.assertRaisesRegex(ValueError, 'stale version'):
                pilot.record_feedback(p, p / 'bad.jsonl')
            decision['event_version_id'] = e['event_version_id']
            pilot.jsonl(p / 'good.jsonl', [decision])
            target = pilot.record_feedback(p, p / 'good.jsonl')
            self.assertTrue(target.exists())
            self.assertEqual(json.loads((p / 'events.jsonl').read_text())['status'], 'candidate')


if __name__ == '__main__':
    unittest.main()
