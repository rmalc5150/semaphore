import base64,io,json,unittest,hashlib
from unittest.mock import Mock,patch
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
from regulatory_collection import SourceIssue
import decodo_web_data as api
DOI='10.64898/2026.05.07.26352693'
URL='https://www.medrxiv.org/content/'+DOI+'v2.full.pdf'

def pdf():
 w=PdfWriter();p=w.add_blank_page(400,100);font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')});p[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):w._add_object(font)})});stream=DecodedStreamObject();stream.set_data(('BT /F1 9 Tf 5 50 Td ('+DOI+') Tj ET').encode());p[NameObject('/Contents')]=w._add_object(stream);o=io.BytesIO();w.write(o);return o.getvalue()

class WebData(unittest.TestCase):
 def setUp(self):
  self.config=patch.object(api,'settings',return_value={'enabled':True,'max_requests_per_day':24});self.config.start();self.addCleanup(self.config.stop)
 def test_old_basic_field_is_never_used_as_bearer(self):
  with self.assertRaisesRegex(SourceIssue,'bearer_missing'):api.parse_bearer({'decodo-web-scraping':'dXNlcjpwYXNz'})
  self.assertEqual(api.parse_bearer({'decodo-web-data-token':'Bearer opaque'}),'opaque')
  self.assertEqual(api.parse_bearer({'key':'opaque'},dedicated=True),'opaque')
  with self.assertRaisesRegex(SourceIssue,'bearer_invalid'):api.parse_bearer({'decodo-web-data-token':'a\nb'})
 def test_lossless_decoding_and_doi_validation(self):
  raw=pdf();body,proof=api.decode_pdf({'content':base64.b64encode(raw).decode()},DOI)
  self.assertEqual(body,raw);self.assertEqual(proof['sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(proof['pages'],1)
 def test_malformed_base64_html_corrupt_pdf_and_wrong_doi_are_rejected(self):
  for content in ('not base64!',base64.b64encode(b'<html>challenge</html>').decode(),base64.b64encode(b'%PDF-1.4\nbroken\n%%EOF').decode()):
   with self.assertRaises(SourceIssue):api.decode_pdf({'content':content},DOI)
  with self.assertRaisesRegex(SourceIssue,'doi_mismatch'):api.decode_pdf({'content':base64.b64encode(pdf()).decode()},'10.0000/wrong')
 def test_http_success_cannot_override_provider_failure(self):
  with self.assertRaisesRegex(SourceIssue,'target_http_403'):api.decode_pdf({'status_code':403,'content':base64.b64encode(pdf()).decode()},DOI)
 def test_only_reviewed_preprint_urls_are_permitted(self):
  api.validate_url(URL)
  for url in ('https://evil.example/a.pdf',URL+'?api_key=secret',URL.replace('https:','http:'),URL.replace('www.medrxiv.org','www.medrxiv.org@evil.example')):
   with self.assertRaises(SourceIssue):api.validate_url(url)
 def client(self):
  c=Mock();c.evidence=[]
  def save(raw,url,media):c.evidence.append({'key':'source_documents/test/'+hashlib.sha256(raw).hexdigest(),'sha256':hashlib.sha256(raw).hexdigest(),'source_url':url});return raw
  c.save.side_effect=save;return c
 def response(self,status=200,body=None):
  response=Mock(status_code=status);response.iter_content.return_value=[body if body is not None else json.dumps({'content':base64.b64encode(pdf()).decode()}).encode()];response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);return response
 def test_request_uses_new_endpoint_bearer_and_preserves_original_bytes(self):
  c=self.client()
  with patch.object(api,'bearer',return_value='new-token'),patch.object(api,'reserve')as budget,patch('constellation.shared_limits.admit'),patch.object(api.requests,'post',return_value=self.response())as post:
   raw,proof=api.capture(c,URL,DOI)
  self.assertEqual(raw,pdf());self.assertEqual(c.evidence[-1]['source_url'],URL);self.assertEqual(c.evidence[-2]['source_url'],api.API_URL)
  self.assertEqual(post.call_args.args[0],api.API_URL);self.assertEqual(post.call_args.kwargs['headers']['Authorization'],'Bearer new-token');self.assertEqual(post.call_args.kwargs['json'],{'url':URL});self.assertFalse(post.call_args.kwargs['allow_redirects']);budget.assert_called_once()
 def test_missing_token_does_not_make_paid_request(self):
  with patch.object(api,'bearer',side_effect=SourceIssue('decodo_web_data_bearer_missing')),patch.object(api,'reserve')as budget,patch.object(api.requests,'post')as post:
   with self.assertRaises(SourceIssue):api.capture(self.client(),URL,DOI)
  budget.assert_not_called();post.assert_not_called()
 def test_auth_error_is_safe_and_not_saved_as_pdf(self):
  c=self.client()
  with patch.object(api,'bearer',return_value='private-token'),patch.object(api,'reserve'),patch('constellation.shared_limits.admit'),patch.object(api.requests,'post',return_value=self.response(401)):
   with self.assertRaisesRegex(SourceIssue,'http_401')as exc:api.capture(c,URL,DOI)
  self.assertNotIn('private-token',str(exc.exception));c.save.assert_not_called()
 def test_paid_budget_failure_prevents_network_request(self):
  with patch.object(api,'bearer',return_value='token'),patch.object(api,'reserve',side_effect=SourceIssue('decodo_web_data_daily_budget')),patch.object(api.requests,'post')as post:
   with self.assertRaises(SourceIssue):api.capture(self.client(),URL,DOI)
  post.assert_not_called()
 def test_unverified_route_stays_disabled_without_paid_calls(self):
  with patch.object(api,'settings',return_value={'enabled':False}),patch.object(api,'bearer')as key,patch.object(api.requests,'post')as post:
   with self.assertRaisesRegex(SourceIssue,'pending_provider_validation'):api.capture(self.client(),URL,DOI)
  key.assert_not_called();post.assert_not_called()
 def test_gateway_commits_one_paper_and_resumes_without_skipping_second(self):
  from additional_source_apis import fetch
  from specialist_inputs import item
  c=self.client();c._pdf_proxy_requests=0;row={'doi':DOI,'version':2,'date':'2026-08-01'};second={**row,'doi':'10.64898/second'};job={'adapter':'additional_biorxiv','start':'2026-08-01','end':'2026-09-01','parameters':{'repository':'medrxiv'}}
  def gateway(url):
   c._pdf_proxy_requests+=1;c.save(pdf(),url,'application/pdf');return pdf()
  c.get.side_effect=gateway
  with patch('additional_source_apis.get_json',return_value=({'messages':[{'status':'ok','total':2}],'collection':[row,second]},None)):
   rows,cursor=fetch(c,job,None,item)
  self.assertEqual(len(rows),1);self.assertEqual(json.loads(cursor)['offset'],1);self.assertEqual(c.get.call_count,1);self.assertEqual(rows[0]['source_evidence'][0]['source_url'],URL)
  self.assertEqual(rows[0]['data']['full_text_capture']['transport'],'decodo_residential_proxy')

class LiveResponseRegressions(unittest.TestCase):
 def test_exact_configured_secret_field_is_used(self):
  self.assertEqual(api.parse_bearer({'decodo-web':'new-token','decodo-web-scraping':'old-token'},dedicated=True,field='decodo-web'),'new-token')
  with self.assertRaisesRegex(SourceIssue,'bearer_missing'):api.parse_bearer({'key':'unrelated','decodo-web-scraping':'old-token'},dedicated=True,field='decodo-web')
 def test_documented_results_envelope_accepts_only_valid_base64_pdf(self):
  raw=pdf();body,proof=api.decode_pdf({'results':[{'status_code':200,'content':base64.b64encode(raw).decode()}]},DOI)
  self.assertEqual(body,raw);self.assertTrue(proof['strict_pdf_validation'])
 def test_actual_raw_string_response_is_not_reencoded_as_original(self):
  with self.assertRaisesRegex(SourceIssue,'pdf_not_base64'):api.decode_pdf({'results':[{'status_code':200,'type':'raw','content':'%PDF-1.4\nnonbinary string\n%%EOF'}]},DOI)
 def test_gateway_error_cannot_be_hidden_by_base64_shaped_content(self):
  with self.assertRaisesRegex(SourceIssue,'target_http_403'):api.decode_pdf({'results':[{'status_code':403,'content':base64.b64encode(pdf()).decode()}]},DOI)
