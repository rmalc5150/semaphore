import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
import tempfile
from collection_storage import LocalStore,write_json
from specialist_inputs import discover_children,fetch_page
from regulatory_collection import SourceIssue
from federal_register_enrichment import parse_notice,cas_numbers,stage,enrich,allowed

FIX=Path(__file__).parent/'tests/fixtures/federal_register'


class Tests(unittest.TestCase):
    def setUp(self):
        self.raw=(FIX/'2021-26683.xml').read_bytes()
        self.meta=json.loads((FIX/'2021-26683-metadata.json').read_text())
        self.ref={'sha256':hashlib.sha256(self.raw).hexdigest()}
        self.result=parse_notice(self.raw,self.meta,self.ref)

    def test_actual_full_notice_preserves_distinct_chemicals_and_exemptions(self):
        r=self.result
        self.assertEqual(r['policy_stage'],'final_rule');self.assertEqual(r['effective_date'],'2022-02-08')
        self.assertEqual(r['publication_date'],'2021-12-10')
        self.assertEqual(len(r['chemical_provisions']),45)
        sections=[p for p in r['chemical_provisions'] if 'P-19-168' in p['pmn_numbers']]
        self.assertEqual(len(sections),1)
        self.assertEqual(sections[0]['identity_status'],'generic_or_confidential')
        self.assertTrue(sections[0]['source_path'])
        self.assertFalse(any('semiconductor wafer' in p['text'] for p in sections[0]['exceptions_and_scope_limits']))
        wafer=next(p for p in r['chemical_provisions'] if 'P-16-539' in p['pmn_numbers'])
        self.assertTrue(any('semiconductor wafer' in p['text'] for p in wafer['exceptions_and_scope_limits']))
        self.assertEqual(r['product_applicability'],'unreviewed_requires_composition_and_use_evidence')

    def test_wrong_document_identity_rejected(self):
        with self.assertRaisesRegex(Exception,'identity_mismatch'):
            parse_notice(self.raw,{**self.meta,'document_number':'2021-99999'},self.ref)

    def test_cas_checksum_rejects_unrelated_numbers(self):
        self.assertEqual(cas_numbers('67-64-1; 67-64-2; 2021-26683'),['67-64-1'])

    def test_proposed_withdrawn_corrected_are_not_final(self):
        for action,expected in [('Proposed rule.','proposed_rule'),('Withdrawal of final rule','withdrawal'),('Final rule; correction.','correction')]:
            self.assertEqual(stage({'action':action,'type':'Rule'}),expected)

    def test_nonchemical_notice_retains_text_without_inventing_substances(self):
        xml=b'<NOTICE><PREAMB><P>A public meeting on robotics research.</P></PREAMB><FRDOC>2026-12345</FRDOC></NOTICE>'
        r=parse_notice(xml,{'document_number':'2026-12345','type':'Notice','publication_date':'2026-10-18'},self.ref)
        self.assertEqual(r['chemical_provisions'],[]);self.assertEqual(r['policy_stage'],'notice')

    def test_unsafe_urls_rejected(self):
        self.assertFalse(allowed('https://www.federalregister.gov.evil.example/x'))
        self.assertFalse(allowed('https://user@www.govinfo.gov/x'))
        self.assertTrue(allowed(self.meta['pdf_url']))

    def test_no_body_means_no_success(self):
        client=Mock();client.json.return_value={**self.meta,'full_text_xml_url':None,'body_html_url':None}
        with self.assertRaisesRegex(Exception,'no_valid_full_notice_body'):enrich(client,{'document_number':'2021-26683'})

    def test_daily_capture_queues_versioned_full_notice_work(self):
        with tempfile.TemporaryDirectory() as directory:
            store=LocalStore(Path(directory))
            row={'observation_id':'obs_example','payload':{'data':self.meta}}
            store.put('batch',(json.dumps(row)+'\n').encode())
            write_json(store,'manifest',{'pages':[{'batches':[{'key':'batch'}]}]})
            parent={'adapter':'federal_register','source':'federal_register','source_id':'S51','mode':'daily','start':'2026-10-18','end':'2026-10-19','parameters':{}}
            discover_children(store,'manifest',parent)
            paths=list((Path(directory)/'operations/federal-register/discovered-jobs').glob('*.json'))
            self.assertEqual(len(paths),1)
            queued=json.loads(paths[0].read_text())
            self.assertEqual(queued['source'],'federal_register_documents')
            self.assertEqual(queued['execution_lane'],'fr_enrichment')
            self.assertEqual(queued['parameters']['parent_observation_id'],'obs_example')
            discover_children(store,'manifest',parent)
            self.assertEqual(len(list(paths[0].parent.glob('*.json'))),1)

    def test_daily_pdf_failure_retries_then_retains_full_body_gap(self):
        client=Mock();notice=Mock(evidence=[])
        job={'adapter':'fr_enrichment','parameters':{'url':'https://www.federalregister.gov/api/v1/documents/2021-26683.json','listing':self.meta}}
        result={**self.result,'official_pdf_status':'missing','retrieval_status':'partial','artifact_gaps':[{'artifact':'official_pdf'}]}
        with patch('federal_register_enrichment.NoticeClient',return_value=notice),patch('federal_register_enrichment.enrich',return_value=result):
            with self.assertRaisesRegex(SourceIssue,'retry_required'):fetch_page(client,job,None)
            job['parameters']['allow_partial']=True
            rows,cursor=fetch_page(client,job,None)
            self.assertEqual(rows[0]['data']['enrichment']['retrieval_status'],'partial')
            self.assertIn('chemical_provisions',rows[0]['data']['enrichment'])

if __name__=='__main__':unittest.main()
