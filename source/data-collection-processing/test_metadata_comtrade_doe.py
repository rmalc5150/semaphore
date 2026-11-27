"""Reject mismatched official data, incomplete pages and unsupported DOE claims."""
import copy
import hashlib
import io
import json
import unittest
from pathlib import Path

from research_contract import digest
from metadata_engine.comtrade import validate, IDENTITY_FIELDS
from metadata_engine.doe_storage import evidence, from_public_receipt
from metadata_engine.evidence import RawFailure
from metadata_engine.source_policies import build
from doe_storage_enrichment import parse_document, facts, VERSION


class ComtradeValidation(unittest.TestCase):
    def setUp(self):
        self.row = dict(typeCode='C', freqCode='A', period='2025', reporterCode=842, cmdCode='850760',
                        flowCode='M', partnerCode=0, partner2Code=0, customsCode='C00', motCode=0,
                        classificationCode='H6', primaryValue=0, qty=None, isQtyEstimated=True)
        self.record = {'source_record_id': digest({k: self.row.get(k) for k in IDENTITY_FIELDS}),
                       'payload': {'data': self.row, 'scope': {'year': 2025}}}
        self.url = 'https://comtradeapi.un.org/data/v1/get/C/A/HS?period=2025&maxRecords=500&reporterCode=842&cmdCode=850760&flowCode=M&partnerCode=0&partner2Code=0&customsCode=C00&motCode=0'
        self.response = {'data': [self.row], 'count': 1, 'error': ''}

    def run_validation(self):
        return validate(json.dumps(self.response).encode(), self.record, self.url)

    def test_complete_zero_value_and_flags_are_valid(self):
        self.assertEqual(self.run_validation()['record_type'], 'annual_trade_observation')

    def test_modified_row_rejected(self):
        self.record = copy.deepcopy(self.record);self.record['payload']['data']['primaryValue'] = 100
        with self.assertRaisesRegex(RawFailure, 'original_row_mismatch'):self.run_validation()

    def test_capped_response_rejected(self):
        self.url = self.url.replace('maxRecords=500', 'maxRecords=1')
        with self.assertRaisesRegex(RawFailure, 'truncated'):self.run_validation()

    def test_different_query_year_rejected(self):
        self.url = self.url.replace('period=2025', 'period=2024')
        with self.assertRaisesRegex(RawFailure, 'period_mismatch'):self.run_validation()

    def test_identity_rejected(self):
        self.record['source_record_id'] = 'wrong'
        with self.assertRaisesRegex(RawFailure, 'identity_mismatch'):self.run_validation()

    def test_untrusted_url_rejected(self):
        self.url = self.url.replace('comtradeapi.un.org', 'example.org')
        with self.assertRaisesRegex(RawFailure, 'untrusted'):self.run_validation()


class SavedObjects:
    def __init__(self):self.data = {}
    def add(self, body, prefix, url):
        sha = hashlib.sha256(body).hexdigest();key = 'source_documents/' + prefix + '/' + sha
        self.data['research-data/' + key] = body
        return {'key': key, 'sha256': sha, 'source_url': url}
    def get_object(self, Bucket, Key):
        return {'Body': io.BytesIO(self.data[Key]), 'ContentLength': len(self.data[Key])}


class DOEValidation(unittest.TestCase):
    def setUp(self):
        self.s3 = SavedObjects();self.url = 'https://www.energy.gov/oe/energy-storage'
        self.body = b'<html><main><h1>Energy Storage</h1><p>The program supports energy storage research. Testing capacity is 100 kW. Funding opportunities require review. Original report conditions must be checked before comparing technologies.</p></main></html>'
        self.document = parse_document(self.body, self.url, max_pages=250)
        self.record = {'source': 'doe_storage_program', 'source_url': self.url, 'source_record_id': digest(self.url),
                       'payload': {'data': self.document, 'source_evidence': [self.s3.add(self.body, 'doe_storage_program', self.url)]}}

    def test_landing_original_matches(self):
        self.assertEqual(evidence(self.record, self.s3, 'b')[0]['validation']['record_type'], 'storage_program_page')

    def test_old_discovery_stub_is_reparsed(self):
        self.record['payload']['data'] = {'document_kind': 'official source discovery page'}
        self.assertEqual(evidence(self.record, self.s3, 'b')[0]['validation']['parsed_document'], self.document)

    def test_forged_landing_text_rejected(self):
        self.record = copy.deepcopy(self.record);self.record['payload']['data']['text'] = 'wrong'
        with self.assertRaisesRegex(RawFailure, 'differs_from_original'):evidence(self.record, self.s3, 'b')

    def test_checksum_rejected(self):
        self.record['payload']['source_evidence'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(RawFailure, 'checksum_mismatch'):evidence(self.record, self.s3, 'b')

    def test_funding_statements_require_exact_original_extraction(self):
        ref = self.s3.add(self.body, 'doe_storage_documents', self.url)
        f = facts(self.document)
        extraction = {'document': self.document, 'facts': f, 'raw_sha256': ref['sha256'], 'source_url': self.url, 'version': VERSION}
        er = self.s3.add(json.dumps(extraction).encode(), 'doe_storage_extractions', self.url)
        er.update(raw_sha256=ref['sha256'], version=VERSION)
        identity = digest([self.url, self.document['semantic_hash']])
        self.record.update(source='doe_storage_funding', source_record_id=identity)
        data = {'document_id': identity, 'facts': f['funding'], 'table_references': f['funding_tables'],
                'tables': [], 'title': self.document['title'], 'source_date': self.document['source_date'], 'limits': []}
        self.record['payload'].update(data=data, source_evidence=[ref], extraction_reference=er)
        self.assertEqual(evidence(self.record, self.s3, 'b')[0]['validation']['record_type'], 'storage_funding_evidence')
        self.record = copy.deepcopy(self.record);self.record['payload']['data']['facts'][0]['actual_payment_confirmed'] = True
        with self.assertRaisesRegex(RawFailure, 'facts_mismatch'):evidence(self.record, self.s3, 'b')

    def test_companion_contracts_belong_to_entry_52(self):
        policies = build(Path(__file__).parent)
        for source in ('doe_storage_program', 'doe_storage_documents', 'doe_storage_benchmarks', 'doe_storage_funding'):
            self.assertEqual(policies[source]['catalog_entries'], [52])
            self.assertEqual(policies[source]['contract_version'], '2.0.3')

    def test_discovery_receipt_is_not_document(self):
        with self.assertRaisesRegex(RawFailure, 'discovery_is_not_document'):
            from_public_receipt({'artifact_kind': 'discovery_page'}, self.s3, 'b')

    def test_public_html_is_not_a_storage_report(self):
        ref = self.s3.add(self.body, 'doe_storage_program', self.url)
        public_key = 'research-data/constellation-backfill/public-capture/objects/doe_storage_program/' + ref['sha256']
        self.s3.data[public_key] = self.body
        receipt = {'artifact_kind': 'public_document', 'artifact_uri': 's3://b/' + public_key,
                   'sha256': ref['sha256'], 'source_url': self.url, 'retrieved_at': '2026-11-13T00:00:00Z'}
        with self.assertRaisesRegex(RawFailure, 'outside_storage_scope'):from_public_receipt(receipt, self.s3, 'b')

    def test_public_csv_original_is_connected_to_metadata(self):
        body = ('technology,cost,units\n' + 'Battery storage,250,USD/kWh\n' * 8).encode()
        sha = hashlib.sha256(body).hexdigest()
        key = 'research-data/constellation-backfill/public-capture/objects/doe_storage_program/' + sha
        self.s3.data[key] = body
        receipt = {'artifact_kind': 'public_document', 'artifact_uri': 's3://b/' + key, 'sha256': sha,
                   'source_url': 'https://www.energy.gov/storage-costs.csv', 'retrieved_at': '2026-11-13T00:00:00Z'}
        record = from_public_receipt(receipt, self.s3, 'b')[0]
        self.assertEqual(record['dataset'], 'specialist_inputs')
        self.assertEqual(evidence(record, self.s3, 'b')[0]['validation']['record_type'], 'storage_original_document')


if __name__ == '__main__':unittest.main()
