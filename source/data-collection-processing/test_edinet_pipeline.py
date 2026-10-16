from datetime import date
import copy
import io
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from collection_storage import LocalStore, StorageSettings
from regulatory_collection import EvidenceClient, SourceIssue
from research_contract import ROOT, load_json, validate_record
import edinet_pipeline as e


def bundle(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return stream.getvalue()


def metadata(n=1):
    return {'docID': 'S100Z55' + str(n), 'seqNumber': n, 'edinetCode': 'E31678', 'JCN': '9010601038669',
        'filerName': 'ちばぎんアセットマネジメント株式会社', 'docDescription': '臨時報告書', 'secCode': None,
        'submitDateTime': '2026-10-07 09:31', 'disclosureStatus': '0', 'withdrawalStatus': '0',
        'xbrlFlag': '1', 'pdfFlag': '0', 'attachDocFlag': '0', 'englishDocFlag': '0', 'csvFlag': '0'}


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LocalStore(self.temp.name)
        self.settings = StorageSettings()
        self.universe = load_json(ROOT / 'examples/sec-filings/universe.json')
        self.taxonomy = load_json(ROOT / 'config/sectors.v1.json')
        self.job = {'source': 'edinet_filings', 'source_id': 'S10', 'adapter': 'edinet', 'mode': 'historical',
            'start': '2026-10-07', 'end': '2026-10-08', 'coverage_note': e.COVERAGE,
            'parameters': {'date': '2026-10-07', 'url': e.API + '/documents.json', 'pipeline_version': e.VERSION}}
        self.client = EvidenceClient(self.store, 'edinet_filings', sleeper=lambda _: None)
        self.zip = bundle({'XBRL/PublicDoc/report.htm': '<html><head><meta charset="utf-8"></head><body>日本語の報告書 本文と財務情報</body></html>'.encode()})

    def requester(self, rows):
        def get(client, *args):
            data = {'metadata': {'status': '200', 'resultset': {'count': len(rows)}}, 'results': rows}
            client.save(json.dumps(data, ensure_ascii=False).encode(), e.API + '/documents.json?date=2026-10-07&type=2')
            return data
        return Mock(side_effect=get)

    def downloader(self, client, doc, kind):
        client.save(self.zip, e.API + '/documents/' + doc + '?type=' + kind, 'application/zip')
        return self.zip

    def collect(self, rows, pages=10, downloader=None, requester=None):
        return e.collect(self.job, self.store, self.settings, self.universe, self.taxonomy, pages,
            self.client, requester or self.requester(rows), downloader or self.downloader)

    def records(self, result):
        manifest = json.loads(self.store.get(result['manifest']).body)
        return [json.loads(line) for page in manifest['pages'] for batch in page['batches']
                for line in self.store.get(batch['key']).body.splitlines()]

    def test_decoding_repairs_losslessly_and_preserves_good_japanese(self):
        good = 'ちばぎんアセットマネジメント株式会社'
        bad = good.encode().decode('latin1')
        self.assertEqual(e.repair_japanese(bad), good)
        self.assertEqual(e.repair_japanese(good), good)
        self.assertEqual(e.repair_japanese('Café'), 'Café')
        self.assertEqual(e.decode_text(good.encode('cp932'))[0], good)
        self.assertEqual(e.decode_text(good.encode('utf-16'))[0], good)

    def test_extracts_xbrl_context_units_and_csv(self):
        xml = '''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:j="urn:jp"><context id="c"><period><instant>2026-03-31</instant></period></context><unit id="JPY"><measure>JPY</measure></unit><j:Assets contextRef="c" unitRef="JPY" decimals="-3">123000</j:Assets></xbrl>'''
        raw = bundle({'report.xbrl': xml, 'facts.csv': '項目\t値\n資産\t123000\n'.encode('utf-16')})
        extracted = e.extract(raw, '1')
        self.assertEqual(extracted['xbrl_facts'], 1)
        self.assertEqual(extracted['files'][0]['facts'][0]['value'], '123000')
        self.assertIn('c', extracted['files'][0]['contexts'])
        self.assertEqual(extracted['files'][1]['rows'][0]['項目'], '資産')

    def test_downloads_and_extraction_have_verified_evidence(self):
        row = metadata()
        row['filerName'] = row['filerName'].encode().decode('latin1')
        result = self.collect([row])
        self.assertEqual(result['status'], 'complete', result)
        record, = self.records(result)
        self.assertEqual(validate_record(record, self.universe), [])
        payload = record['payload']
        self.assertEqual(payload['data']['filerName'], metadata()['filerName'])
        self.assertEqual(payload['decoding']['repaired_fields'], ['filerName'])
        ref = payload['documents'][0]['extraction']['source_evidence'][0]
        extracted = json.loads(self.store.get(ref['key']).body)
        self.assertIn('日本語', extracted['files'][0]['text'])
        self.assertEqual(payload['document_capture_status'], 'captured')

    def test_resume_pins_inventory_and_does_not_repeat_committed_document(self):
        first = self.collect([metadata(1), metadata(2)], pages=1)
        self.assertEqual(first['status'], 'partial', first)
        requester = Mock(side_effect=AssertionError('inventory must stay pinned'))
        downloader = Mock(side_effect=self.downloader)
        second = self.collect([], pages=2, downloader=downloader, requester=requester)
        self.assertEqual(second['status'], 'complete', second)
        self.assertEqual(len(self.records(second)), 2)
        self.assertEqual(downloader.call_count, 1)
        self.assertEqual(downloader.call_args.args[1], metadata(2)['docID'])

    def test_failed_download_does_not_commit_missing_content(self):
        result = self.collect([metadata()], downloader=Mock(side_effect=SourceIssue('edinet_document_http_503')))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(self.records(result), [])
        self.assertEqual(self.collect([metadata()])['status'], 'complete')

    def test_all_advertised_formats_requested(self):
        row = metadata()
        row.update(attachDocFlag='1', englishDocFlag='1', csvFlag='1')
        downloader = Mock(side_effect=self.downloader)
        result = self.collect([row], downloader=downloader)
        self.assertEqual(result['status'], 'complete', result)
        self.assertEqual([c.args[2] for c in downloader.call_args_list], ['1', '3', '4', '5'])

    def test_unavailable_report_retained_as_explicit_gap(self):
        row = metadata()
        row['disclosureStatus'] = '1'
        downloader = Mock()
        result = self.collect([row], downloader=downloader)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(self.records(result)[0]['payload']['document_capture_status'], 'source_unavailable')
        downloader.assert_not_called()

    def test_unique_verified_identifier_confirms_and_conflicts_do_not(self):
        cid = self.universe['companies'][0]['company_id']
        self.universe['external_identifiers'].append({'system': 'edinet_code', 'value': 'E31678',
            'entity_id': cid, 'review_status': 'verified'})
        self.assertEqual(e.Matcher(self.universe).match(metadata())['company_ids'], [cid])
        other = self.universe['companies'][1]['company_id']
        self.universe['external_identifiers'].append({'system': 'jcn', 'value': metadata()['JCN'],
            'entity_id': other, 'review_status': 'verified'})
        match = e.Matcher(self.universe).match(metadata())
        self.assertEqual(match['company_ids'], [])
        self.assertTrue(match['conflicting_identifiers'])

    def test_name_match_remains_candidate(self):
        self.universe['companies'][0]['canonical_name'] = metadata()['filerName']
        match = e.Matcher(self.universe).match(metadata())
        self.assertEqual(match['company_ids'], [])
        self.assertEqual(match['entity_link_status'], 'candidate')

    def test_xml_entities_rejected_without_replacement_or_fetch(self):
        with self.assertRaisesRegex(SourceIssue, 'entities'):
            e.xml_facts('<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a>&x;</a>')

    def test_public_pdf_with_permissions_and_empty_password_is_readable(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt('', 'owner-password')
        stream = io.BytesIO()
        writer.write(stream)
        extracted = e.extract_file(stream.getvalue(), 'report.pdf')
        self.assertEqual(extracted['skipped_pages'], [1])
        self.assertFalse(extracted['ocr_performed'])


if __name__ == '__main__':
    unittest.main()
