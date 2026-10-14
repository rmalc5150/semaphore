"""Textless pages are skipped under the user-selected collection policy."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from disclosure_collection import document_text
from regulatory_collection import SourceIssue
from collection_alerts import outcome_issues,evaluate
from test_collection_alerts import CONFIG,NOW,UNIT,health

class PageSkipTests(unittest.TestCase):
    def extract(self,texts):
        reader=SimpleNamespace(is_encrypted=False,pages=[Mock(extract_text=Mock(return_value=t)) for t in texts])
        with patch('pypdf.PdfReader',return_value=reader):
            return document_text(b'%PDF-test',{'source':'hkex_news'})
    def test_skips_empty_pages_preserving_text_order(self):
        text,info=self.extract(['First','',' \n',None,'Last'])
        self.assertEqual(text,'First\nLast');self.assertEqual(info['skipped_pages'],[2,3,4]);self.assertEqual(info['text_pages'],2)
    def test_image_only_document_does_not_block_collection(self):
        text,info=self.extract(['',''])
        self.assertEqual(text,'');self.assertEqual(info['skipped_pages'],[1,2])
    def test_zero_page_document_still_fails(self):
        with self.assertRaisesRegex(SourceIssue,'empty_or_unparseable_document'):self.extract([])
    def test_normal_text_unchanged(self):
        text,info=self.extract(['First','Second']);self.assertEqual(text,'First\nSecond');self.assertEqual(info['skipped_pages'],[])
    def test_legacy_page_alert_is_silent(self):
        code='document_requires_ocr_or_page_review'
        self.assertFalse(outcome_issues({'status':'failed','reason':code}))
        item={'unit':UNIT,'code':code,'severity':'low','detail':code,'at':NOW}
        current,_=evaluate(health(issues=[item]),{'active':{UNIT+':'+code:item}},CONFIG,NOW)
        self.assertNotIn(UNIT+':'+code,current)
        self.assertTrue(outcome_issues({'status':'failed','reason':'checksum_mismatch'}))
if __name__=='__main__':unittest.main()
