import copy
from datetime import datetime,timezone
import hashlib,io,json,tempfile,unittest
from unittest.mock import Mock,patch
from pathlib import Path
from collection_storage import LocalStore,write_checked
from research_contract import load_json,ROOT,validate_record
from hkex_originals import OriginalError,language_notice,validate_original,resolve_notice,original_record
from test_disclosure_collection import Client,row,page
import disclosure_collection as d

NOTICE=b'<html><body><!--newscontent-->An announcement has just been published by the issuer in the Chinese section of this website, a corresponding version of which may or may not be published in this section.<!--/newscontent--></body></html>'
PDF=b'%PDF-1.4\nOriginal issuer filing\n%%EOF'

def fixture():
 r=json.loads(Path('repair-notes/2026-11-09-hkex-repair/blocked-record.json').read_text())
 r['universe_version']=load_json(ROOT/'examples/sec-filings/universe.json')['universe_version']
 return r

class Originals(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.store=LocalStore(temp.name)
  self.record=fixture();self.zh={**self.record['payload']['data'],'NEWS_ID':'12343954','FILE_LINK':'/listedco/listconews/sehk/2026/0923/2026092301925_c.pdf','FILE_TYPE':'PDF','TITLE':'原始公告'}
  self.client=Client(self.store,[page([self.zh])],{d.urljoin(d.HKEX_API,self.zh['FILE_LINK']):PDF})
 def test_notice_not_accepted_as_original(self):
  self.assertTrue(language_notice(NOTICE))
  with self.assertRaises(OriginalError):validate_original(NOTICE,self.record['source_url'])
 def test_realistic_large_pdf_is_accepted_without_html_parsing(self):
  body=b'%PDF-1.7\n'+b' '*(33*1024*1024)+b'\n%%EOF'
  with patch('hkex_originals.Text',side_effect=AssertionError('PDF bytes must not be parsed as HTML')):
   self.assertFalse(language_notice(body))
   self.assertEqual(validate_original(body,self.zh_url())['format'],'pdf')
 def zh_url(self):return d.urljoin(d.HKEX_API,self.zh['FILE_LINK'])
 def test_download_limit_and_empty_body_still_fail_with_measured_diagnostics(self):
  with patch('hkex_originals.MAX_ORIGINAL_BYTES',100):
   for body,kind in ((b'','empty'),(b'%PDF-'+b'x'*100+b'%%EOF','oversize')):
    with self.assertRaises(OriginalError)as raised:validate_original(body,self.zh_url())
    self.assertEqual(raised.exception.diagnostics['failure_kind'],kind)
    self.assertEqual(raised.exception.diagnostics['bytes'],len(body))
 def test_different_chinese_id_and_raw_provenance_retained(self):
  receipt=resolve_notice(self.record,NOTICE,self.client);r=original_record(self.record,receipt['originals'][0],receipt)
  self.assertEqual(r['source_record_id'],'12343954');self.assertEqual(r['payload']['data'],self.zh)
  self.assertEqual(r['payload']['language_notice_context']['notice_record_id'],'12343955')
  self.assertNotEqual(r['record_id'],self.record['record_id'])
  self.assertEqual(r['payload']['document_language'],'zh-Hant');self.assertIsNone(r['available_at'])
  self.assertEqual(self.client.calls[0][1]['lang'],'ZH')
  self.assertEqual(validate_record(r,load_json(ROOT/'examples/sec-filings/universe.json')),[])
 def test_other_issuer_or_minute_does_not_substitute(self):
  for change in ({'STOCK_CODE':'00001'},{'DATE_TIME':'23/09/2026 22:57'}):
   c=Client(self.store,[page([{**self.zh,**change}])])
   with self.assertRaisesRegex(OriginalError,'candidates_missing'):resolve_notice(self.record,NOTICE,c)
 def test_resolution_reuse_rechecks_document_checksum(self):
  receipt=resolve_notice(self.record,NOTICE,self.client)
  c=Client(self.store,[]);resolve_notice(self.record,NOTICE,c);self.assertEqual(c.calls,[])
  key=receipt['originals'][0]['document_evidence']['key'];self.store._path(key).write_bytes(PDF+b'bad')
  with self.assertRaisesRegex(OriginalError,'checksum'):resolve_notice(self.record,NOTICE,c)
 def test_index_body_or_incomplete_pdf_is_not_primary(self):
  for body in (b'{}',b'%PDF-1.4 no EOF',b'<html><body>just a title</body></html>'):
   with self.assertRaises(OriginalError):validate_original(body,'https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0923/1.pdf')
 def test_untrusted_document_links_rejected(self):
  with self.assertRaises(OriginalError):validate_original(PDF,'https://evil.example/1.pdf')
