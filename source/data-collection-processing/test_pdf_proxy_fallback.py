import json,tempfile,unittest,copy
from contextlib import contextmanager
from unittest.mock import Mock,patch
from collection_storage import LocalStore
from regulatory_collection import EvidenceClient,SourceIssue
from test_decodo_web_data import pdf,URL
import pdf_proxy_fallback as f
CFG={'enabled':True,'secret_id':'proxies','max_requests_per_day':4,'max_pdf_bytes':8*1024**2,'max_requests_per_client':1,'allowed_sources':['test','biorxiv_medrxiv_preprints']}
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.client=EvidenceClient(LocalStore(self.temp.name),'test')
  for target,value in [('settings',CFG),('eligible',True),('safe_url',True)]:
   p=patch.object(f,target,return_value=value);p.start();self.addCleanup(p.stop)
 def test_free_transport_wins_without_secret_or_quota(self):
  with patch.object(f,'fetch',return_value=pdf()),patch.object(f,'reserve')as reserve,patch.object(f,'proxy_url')as key:
   self.assertEqual(f.capture(self.client,URL,'source_http_403'),pdf())
  reserve.assert_not_called();key.assert_not_called()
 def test_paid_is_last_and_verified_success_is_reused(self):
  with patch.object(f,'fetch',side_effect=[SourceIssue('pdf_proxy_http_403'),pdf()])as get,patch.object(f,'reserve')as budget,patch.object(f,'proxy_url',return_value='https://safe-proxy'):
   first=f.capture(self.client,URL,'source_http_403');second=f.capture(self.client,URL,'source_http_403')
  self.assertEqual(first,second);self.assertEqual(get.call_count,2);budget.assert_called_once();self.assertEqual(self.client._pdf_proxy_requests,1)
 def test_not_found_rate_limit_or_oversize_never_spends(self):
  for code in ['pdf_proxy_http_404','pdf_proxy_http_410','pdf_proxy_http_429','pdf_proxy_http_401','pdf_proxy_size_limit']:
   with patch.object(f,'fetch',side_effect=SourceIssue(code)),patch.object(f,'reserve')as budget,self.assertRaises(SourceIssue):f.capture(self.client,URL,'source_http_403')
   budget.assert_not_called()
 def test_budget_denial_prevents_paid_http(self):
  with patch.object(f,'fetch',side_effect=SourceIssue('pdf_proxy_http_403'))as get,patch.object(f,'proxy_url',return_value='https://proxy'),patch.object(f,'reserve',side_effect=SourceIssue('pdf_proxy_daily_budget',True)),self.assertRaises(SourceIssue):f.capture(self.client,URL,'source_http_403')
  self.assertEqual(get.call_count,1);self.assertFalse(self.client.evidence)
 def test_client_budget_prevents_second_paid_attempt(self):
  self.client._pdf_proxy_requests=1
  with patch.object(f,'fetch',side_effect=SourceIssue('pdf_proxy_http_403')),patch.object(f,'reserve')as budget,self.assertRaisesRegex(SourceIssue,'client_budget'):f.capture(self.client,URL,'source_http_403')
  budget.assert_not_called()
 def test_corrupt_paid_pdf_is_not_archived(self):
  with patch.object(f,'fetch',side_effect=[SourceIssue('pdf_proxy_http_403'),b'%PDF-corrupt\n%%EOF']),patch.object(f,'reserve'),patch.object(f,'proxy_url',return_value='https://proxy'),self.assertRaises(SourceIssue):f.capture(self.client,URL,'source_http_403')
  self.assertFalse(self.client.evidence)
 def test_disabled_never_reads_cache_or_uses_http(self):
  with patch.object(f,'settings',return_value={**CFG,'enabled':False}),patch.object(f,'fetch')as get,self.assertRaises(SourceIssue):f.capture(self.client,URL,'source_http_403')
  get.assert_not_called()
 def test_non_enrolled_source_never_uses_fallback(self):
  self.client.source='unapproved-source'
  with patch.object(f,'fetch')as get,self.assertRaises(SourceIssue):f.capture(self.client,URL,'source_http_403')
  get.assert_not_called()
 def test_paid_redirect_does_not_make_another_paid_request(self):
  response=Mock(status_code=302,headers={'Location':'https://www.medrxiv.org/other.pdf'})
  response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
  with patch.object(f.requests,'Session')as cls:
   cls.return_value.get.return_value=response
   with self.assertRaisesRegex(SourceIssue,'redirect_not_retried'):f.fetch(URL,100,'https://proxy')
   self.assertEqual(cls.return_value.get.call_count,1)
 def test_known_oversize_stops_before_streaming_body(self):
  response=Mock(status_code=200,headers={'Content-Length':'101'})
  response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
  with patch.object(f.requests,'Session')as cls:
   cls.return_value.get.return_value=response
   with self.assertRaisesRegex(SourceIssue,'size_limit'):f.fetch(URL,100,'https://proxy')
  response.iter_content.assert_not_called()
 def test_sensitive_exception_text_is_discarded(self):
  with patch.object(f.requests,'Session')as cls:
   cls.return_value.get.side_effect=f.requests.exceptions.ProxyError('user:super-secret@gate.decodo.com')
   with self.assertRaises(SourceIssue)as caught:f.fetch(URL,100,'https://user:super-secret@gate.decodo.com')
  self.assertNotIn('super-secret',str(caught.exception))
 def test_generic_downloader_uses_direct_success_and_bypasses_paid(self):
  with patch.object(self.client,'_get_direct',return_value=pdf()),patch.object(f,'capture')as paid:self.assertEqual(self.client.get(URL),pdf())
  paid.assert_not_called()
 def test_generic_downloader_calls_last_resort_only_for_pdf(self):
  with patch.object(self.client,'_get_direct',side_effect=SourceIssue('source_http_403')),patch.object(f,'capture',return_value=pdf())as fallback:
   self.assertEqual(self.client.get(URL),pdf())
   with self.assertRaises(SourceIssue):self.client.get('https://www.medrxiv.org/api/metadata.json')
  self.assertEqual(fallback.call_count,1)
 def test_auth_headers_are_not_forwarded_to_proxy(self):
  with patch.object(self.client,'_get_direct',side_effect=SourceIssue('source_http_403')),patch.object(f,'capture')as fallback,self.assertRaises(SourceIssue):self.client.get(URL,api_key='private-key')
  fallback.assert_not_called()
 def test_exhausted_rate_limit_never_becomes_paid_fallback(self):
  error=SourceIssue('source_retries_exhausted',True,{'last_http_status':429})
  with patch.object(self.client,'_get_direct',side_effect=error),patch.object(f,'capture')as fallback,self.assertRaises(SourceIssue):self.client.get(URL)
  fallback.assert_not_called()

class QuotaTests(unittest.TestCase):
 def test_transactional_cross_host_caps_and_per_url_cooldown(self):
  class DB:
   def __init__(self):self.count={};self.current=None
   def execute(self,sql,args):
    if sql.startswith('INSERT'):self.count.setdefault(args[0],0)
    elif sql.startswith('SELECT'):self.current=args[0]
    else:self.count[args[1]]+=args[0]
   def fetchone(self):return {'used_requests':self.count[self.current]}
  db=DB()
  @contextmanager
  def connection():
   before=copy.deepcopy(db.count)
   try:yield db
   except Exception:db.count=before;raise
  control=Mock();control.db=connection
  with patch.object(f,'CONTROL',control):
   f.reserve(URL,CFG)
   with self.assertRaisesRegex(SourceIssue,'url_cooldown'):f.reserve(URL,CFG)
   for i in range(3):f.reserve(URL+str(i),CFG)
   with self.assertRaisesRegex(SourceIssue,'daily_budget'):f.reserve(URL+'extra',CFG)
  self.assertEqual(db.count['decodo_proxy_pdf_requests'],4);self.assertEqual(db.count['decodo_proxy_pdf_reserved_bytes'],32*1024**2)
class UrlTests(unittest.TestCase):
 def test_private_hosts_and_credential_urls_are_rejected(self):
  for url in ['https://localhost/a.pdf','https://u:p@www.medrxiv.org/a.pdf','https://www.medrxiv.org/a.pdf?api_key=secret','http://www.medrxiv.org/a.pdf']:
   self.assertFalse(f.safe_url(url))
  with patch.object(f.socket,'getaddrinfo',return_value=[(None,None,None,None,('127.0.0.1',443))]):self.assertFalse(f.safe_url('https://www.medrxiv.org/a.pdf'))
 def test_missing_and_rate_limited_are_not_eligible(self):
  with patch.object(f,'safe_url',return_value=True):
   for reason in ['source_http_404','source_http_429','source_http_401']:self.assertFalse(f.eligible(URL,reason))

if __name__=='__main__':unittest.main()
