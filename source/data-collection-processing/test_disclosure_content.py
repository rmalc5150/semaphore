import binascii
import hashlib
import io
import json
from unittest.mock import Mock

from test_disclosure_collection import DisclosureTests, Client, row, page
import disclosure_collection as d
import disclosure_content as content
from regulatory_collection import SourceIssue


class ContentTests(DisclosureTests):
    def test_8k_form_without_supporting_passage_is_not_a_press_release(self):
        parent = {'payload': {'form': '8-K', 'data': {'text': 'A director resigned from the board effective today.'}}}
        self.assertEqual(d.candidate('press-releases', parent), [])

    def test_full_content_and_chunk_citations_survive_candidate_stage(self):
        filings = self.collect([page([row()])])
        url = self.read(filings)[0]['record']['source_url']
        text = 'Example Robotics issued a press release on June 2, 2024 announcing a proposed license agreement for $12 million.'
        docs = self.derive('documents', [filings['manifest']], Client(self.store, documents={url: ('<html><body>' + text + '</body></html>').encode()}))
        candidates = self.derive('licensing-agreements', [docs['manifest']])
        candidate = self.read(candidates)[0]['record']['payload']
        reference = candidate['content_reference']
        stored = json.loads(self.store.get(reference['key']).body)
        self.assertEqual(stored['text'], text)
        match = candidate['data']['matches'][0]
        self.assertEqual(match['excerpt'], stored['text'][match['start']:match['end']])
        self.assertTrue(match['chunk_ids'])
        self.assertEqual(match['document']['filename'], 'report.html')
        self.assertEqual(match['context_signals']['amount_mentions'], ['$12 million'])
        self.assertTrue(match['context_signals']['proposed_language'])

    def test_long_content_has_no_truncation_and_late_passage_is_found(self):
        text = 'Ordinary operating information. ' * 4000 + 'The company signed an exclusive license agreement for new robot technology.'
        artifact = content.extract(('<html>' + text + '</html>').encode(), {'source': 'hkex_news'})
        self.assertEqual(artifact['text'], text)
        self.assertGreater(len(artifact['chunks']), 25)
        parent = {'payload': {'data': {'text': artifact['text'], 'document_spans': artifact['document_spans']}}}
        matches = d.candidate('licensing-agreements', parent)
        self.assertGreater(matches[0]['match_start'], 100000)
        for chunk in artifact['chunks']:
            unit = next(u for u in artifact['documents'] if u['document_id'] == chunk['document_id'])
            self.assertLessEqual(chunk['end'], len(unit['text']))

    def test_submission_preserves_all_text_files_and_structured_content(self):
        parent = {'source': 'sec_edgar', 'source_record_id': '0000000001-26-000001', 'payload': {'form': '8-K'}}
        raw = b'ACCESSION NUMBER: 0000000001-26-000001\n<DOCUMENT><TYPE>8-K\n<FILENAME>main.htm\n<TEXT>Company announces a detailed operating update for shareholders.</TEXT></DOCUMENT><DOCUMENT><TYPE>EX-99.1\n<FILENAME>release.htm\n<TEXT>A press release announces the completed acquisition of a robotics business.</TEXT></DOCUMENT><DOCUMENT><TYPE>EX-101.INS\n<FILENAME>facts.xml\n<TEXT><Assets>123</Assets></TEXT></DOCUMENT>'
        artifact = content.extract(raw, parent)
        self.assertEqual(len(artifact['documents']), 3)
        self.assertEqual(artifact['documents'][2]['text'], '<Assets>123</Assets>')
        self.assertNotIn('<Assets>', artifact['text'])
        parent['payload']['data'] = {'text': artifact['text'], 'document_spans': artifact['document_spans']}
        match = d.candidate('ma-announcements', parent)[0]
        self.assertEqual(match['document']['filename'], 'release.htm')
        self.assertTrue(match['context_signals']['completion_language'])

    def test_negated_context_is_flagged_without_verifying_event(self):
        parent = {'payload': {'data': {'text': 'The company has not completed the proposed acquisition and may cancel it.'}}}
        signal = d.candidate('ma-announcements', parent)[0]['context_signals']
        self.assertTrue(signal['negation_language'])
        self.assertTrue(signal['proposed_language'])
        self.assertEqual(signal['verification_status'], 'unreviewed_passage_signals')

    def test_large_document_is_consumed_from_full_reference(self):
        filings = self.collect([page([row()])])
        url = self.read(filings)[0]['record']['source_url']
        text = 'Ordinary operating information. ' * 40000 + 'An exclusive license agreement was signed.'
        docs = self.derive('documents', [filings['manifest']], Client(self.store,
            documents={url: ('<html>' + text + '</html>').encode()}))
        parent = self.read(docs)[0]['record']['payload']
        self.assertIsNone(parent['data']['text'])
        content_object = json.loads(self.store.get(parent['content_reference']['key']).body)
        self.assertEqual(content_object['text'], text)
        candidates = self.derive('licensing-agreements', [docs['manifest']])
        match = self.read(candidates)[0]['record']['payload']['data']['matches'][0]
        self.assertGreater(match['match_start'], 1000000)
        self.assertTrue(match['chunk_ids'])

    def test_historical_reprocessing_reuses_saved_original_without_network(self):
        filings = self.collect([page([row()])])
        url = self.read(filings)[0]['record']['source_url']
        first = self.derive('documents', [filings['manifest']], Client(self.store,
            documents={url: b'<html>Example Robotics announces a detailed corporate update to investors.</html>'}))
        offline = Client(self.store)
        second = self.derive('documents', [filings['manifest']], offline, refresh=True)
        self.assertEqual(second['status'], 'complete')
        self.assertEqual(offline.calls, [])
        self.assertEqual(self.read(first)[0]['record']['payload']['content_reference']['sha256'],
                         self.read(second)[0]['record']['payload']['content_reference']['sha256'])
