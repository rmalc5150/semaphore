import unittest
from unittest.mock import Mock, patch
from ted_enrichment import parse_xml, enrich_notice

class TedTests(unittest.TestCase):
    raw = b'<TED_EXPORT><CODED_DATA_SECTION><NOTICE_DATA><NO_DOC_OJS>0331738-2021</NO_DOC_OJS></NOTICE_DATA></CODED_DATA_SECTION><FORM_SECTION><F03_2014 LG="ES"><AWARD_CONTRACT><LOT_NO>1</LOT_NO><CONTRACTORS><OFFICIALNAME>Supplier A</OFFICIALNAME></CONTRACTORS><VAL_TOTAL CURRENCY="EUR">123.45</VAL_TOTAL><DATE_CONCLUSION_CONTRACT>2021-06-25</DATE_CONCLUSION_CONTRACT></AWARD_CONTRACT></F03_2014></FORM_SECTION></TED_EXPORT>'
    def test_legacy_context_and_decimal_currency_preserved(self):
        e=parse_xml(self.raw,'331738-2021')
        self.assertEqual(e['stage'],'award_notice')
        self.assertEqual(e['values'][0]['value'],'123.45')
        self.assertEqual(e['values'][0]['attributes']['CURRENCY'],'EUR')
        self.assertIn('/AWARD_CONTRACT/', e['values'][0]['path'])
        self.assertEqual(e['dates'][0]['value'],'2021-06-25')
    def test_wrong_identity_html_entities_empty_rejected(self):
        for raw in [self.raw.replace(b'0331738',b'999999'), b'<html/>', b'', b'<!DOCTYPE a><TED_EXPORT/>']:
            with self.assertRaises(Exception): parse_xml(raw,'331738-2021')
    def test_ubl_namespaces_and_unknown_stage(self):
        e=parse_xml(b'<ContractNotice xmlns="urn:ubl"><NoticePublicationID>331738-2021</NoticePublicationID><ContractFolderID>ABC</ContractFolderID></ContractNotice>','331738-2021')
        self.assertEqual(e['stage'],'competition')
        self.assertEqual(e['xml_tree']['tag'],'{urn:ubl}ContractNotice')
    def test_untrusted_link_not_requested(self):
        with patch('ted_enrichment.build_opener') as opener:
            with self.assertRaises(Exception): enrich_notice({'links':{'xml':{'MUL':'https://example.com/331738-2021/xml'}}},'331738-2021',Mock())
            opener.assert_not_called()
    def test_202_not_saved_or_parsed(self):
        client=Mock(evidence=[],last_request=0)
        response=Mock(status=202); response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch('ted_enrichment.build_opener') as opener, patch('ted_packages.package_xml', side_effect=RuntimeError('package_unavailable')):
            opener.return_value.open.return_value=response
            with self.assertRaisesRegex(Exception,'package_unavailable'): enrich_notice({},'331738-2021',client)
        client.save.assert_not_called()

class ChunkTests(unittest.TestCase):
    def test_large_notice_roundtrips_losslessly_and_distinguishes_children(self):
        import json,hashlib
        from ted_enrichment import bounded_notice_items
        data={'publication-number':'1-2021','notice_xml':'€漢字'*1000,
              'enrichment':{'stage':'award_notice','fields':[{'value':'123.45','currency':'EUR'}]}}
        make=lambda identity,data,url,day:{'id':identity,'data':data}
        rows=bounded_notice_items('1-2021',data,'https://ted.europa.eu','2021-01-01',make,threshold=100,chunk_chars=50)
        self.assertEqual(rows[0]['id'],'1-2021')
        text=''.join(r['data']['content_text'] for r in rows[1:])
        self.assertEqual(json.loads(text),data)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),rows[0]['data']['content_manifest']['sha256'])
        self.assertEqual(len({r['id'] for r in rows}),len(rows))
        self.assertTrue(all(r['data']['record_type']=='notice_content_chunk' for r in rows[1:]))
        self.assertFalse(rows[0]['data']['enrichment']['specialist_ready'])

if __name__=='__main__': unittest.main()
