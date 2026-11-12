import unittest,tempfile,json,hashlib,io
from unittest.mock import patch
from collection_storage import LocalStore
from regulatory_collection import SourceIssue
from people_rss_content import Capture
from metadata_engine.people_rss import evidence
from metadata_engine.evidence import RawFailure
BODY='The company appointed an experienced chief executive to lead its engineering team. '*15
HTML=('<html><body><article><p>'+BODY+'</p></article></body></html>').encode()
class Repair(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.store=LocalStore(t.name);self.row={'url':'https://publisher.example/article','title':'Appointment','text':'Short summary'}
 def test_direct_block_uses_decodo_and_preserves_native_proof(self):
  c=Capture(self.store,None,max_publisher_requests=4)
  with patch('finlight_content.Capture.publisher',side_effect=SourceIssue('article_publisher_http_403')),patch('people_rss_content.public_url'),patch('decodo_scraping_api.scrape_url',return_value=HTML.decode())as scrape:
   result=c.get(self.row,force=True)
  self.assertEqual(result['status'],'captured');self.assertEqual(result['capture_basis'],'decodo_rendered_html');scrape.assert_called_once()
  record={'source_url':self.row['url'],'payload':{'data':self.row,'full_text':result}}
  class S3:
   def get_object(inner,**kw):
    value=self.store.get(kw['Key'].removeprefix('research-data/')).body
    return {'Body':io.BytesIO(value),'ContentLength':len(value)}
  self.assertTrue(any(a['artifact_kind']=='full_text'for a in evidence(record,S3(),'bucket')))
  result['text_sha256']='bad'
  with self.assertRaises(RawFailure):evidence(record,S3(),'bucket')
 def test_paywall_does_not_trigger_decodo(self):
  c=Capture(self.store,None)
  with patch('finlight_content.Capture.publisher',side_effect=SourceIssue('article_access_restricted')),patch('decodo_scraping_api.scrape_url')as scrape:
   result=c.get(self.row,force=True)
  self.assertEqual(result['status'],'unavailable');scrape.assert_not_called()
 def test_summary_only_is_not_complete(self):
  with self.assertRaises(RawFailure):evidence({'source_url':self.row['url'],'payload':{'data':self.row}},None,'bucket')
 def test_explicit_rss_body_avoids_network(self):
  from people_movements import parse_feed
  xml=('<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><title>Appointment</title><link>'+self.row['url']+'</link><description>Short summary</description><content:encoded><![CDATA['+HTML.decode()+']]></content:encoded></item></channel></rss>').encode()
  row=parse_feed(xml,'Publisher')[0];sha=hashlib.sha256(xml).hexdigest();key='source_documents/people_rss/'+sha;self.store.put(key,xml);row['_feed_evidence']=[{'key':key,'sha256':sha,'source_url':'https://publisher.example/feed/'}]
  with patch('finlight_content.Capture.publisher')as direct,patch('decodo_scraping_api.scrape_url')as gateway:
   result=Capture(self.store,None).get(row,force=True)
  self.assertEqual(result['capture_basis'],'rss_full_content');direct.assert_not_called();gateway.assert_not_called()
