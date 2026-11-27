import copy,hashlib,io,json,unittest
from pathlib import Path
from metadata_engine.federal_register import evidence, pdf, validate_listing, ProviderError
from metadata_engine.evidence import RawFailure
from federal_register_parser import parse_notice

FIX=Path(__file__).parent/'tests/fixtures/federal_register'

class S3:
 def __init__(self):self.files={}
 def add(self,body,url,source='federal_register_documents'):
  sha=hashlib.sha256(body).hexdigest();key='source_documents/'+source+'/'+sha
  self.files['research-data/'+key]=body
  return {'key':key,'sha256':sha,'source_url':url,'retrieved_at':'2026-11-13T10:00:00Z'}
 def get_object(self,**kw):
  body=self.files[kw['Key']];return {'Body':io.BytesIO(body),'ContentLength':len(body)}

class Tests(unittest.TestCase):
 def listing(self):
  data={'document_number':'2026-12345','title':'Notice','type':'Notice','publication_date':'2026-11-12',
        'agencies':[{'name':'Agency'}],'html_url':'https://www.federalregister.gov/documents/2026/11/12/2026-12345/notice','abstract':'Abstract'}
  raw=json.dumps({'count':1,'total_pages':1,'results':[data]}).encode();url='https://www.federalregister.gov/api/v1/documents.json?conditions%5Bterm%5D=robotics&conditions%5Bpublication_date%5D%5Bgte%5D=2026-11-01&conditions%5Bpublication_date%5D%5Blte%5D=2026-11-13&page=1&per_page=100'
  record={'source':'federal_register','source_record_id':'2026-12345','source_url':data['html_url'],'event_at':{'value':'2026-11-12'},
          'payload':{'data':data,'scope':{'query':{'conditions[term]':'robotics'}}}}
  return raw,record,url
 def document(self):
  s=S3();meta=json.loads((FIX/'2021-26683-metadata.json').read_text());number=meta['document_number'];xml=(FIX/'2021-26683.xml').read_bytes()
  api=s.add(json.dumps(meta).encode(),'https://www.federalregister.gov/api/v1/documents/'+number+'.json')
  body=s.add(xml,meta['full_text_xml_url']);p=s.add(b'%PDF-1.4\noriginal notice\n%%EOF',meta['pdf_url'])
  extraction={**parse_notice(xml,meta,body),'body_source':body,'official_pdf_source':p,'official_pdf_status':'downloaded','retrieval_status':'complete'}
  record={'source':'federal_register_documents','source_record_id':number,'source_url':meta['html_url'],'event_at':{'value':meta['publication_date']},
          'payload':{'data':{'enrichment':extraction},'scope':{'listing':{'document_number':number}},'source_evidence':[api,body,p]}}
  return s,record
 def test_exact_listing_is_metadata_not_full_notice(self):
  raw,r,u=self.listing();info=validate_listing(raw,r,u)
  self.assertEqual(info['record_type'],'federal_register_notice_listing')
  r['payload']['data']['title']='Changed'
  with self.assertRaisesRegex(ProviderError,'differs_from_original'):validate_listing(raw,r,u)
 def test_listing_rejects_projection_foreign_host_and_query_mismatch(self):
  raw,r,u=self.listing()
  for url in (u+'&fields[]=title',u.replace('www.federalregister.gov','evil.example'),u.replace('robotics','battery')):
   with self.assertRaises(ProviderError):validate_listing(raw,r,url)
 def test_listing_identity_date_and_url_are_checked(self):
  raw,r,u=self.listing()
  for field,value in [('source_record_id','2026-99999'),('event_at',{'value':'2026-11-11'}),('source_url','https://example.org/')]:
   bad=copy.deepcopy(r);bad[field]=value
   with self.assertRaises(ProviderError):validate_listing(raw,bad,u)
 def test_full_notice_replays_original_text_and_45_chemical_provisions(self):
  s,r=self.document();a=evidence(r,s,'bucket');self.assertEqual({x['artifact_kind']for x in a},{'provider_record','notice_body','official_pdf'})
  self.assertEqual(a[0]['validation']['chemical_provisions'],45);self.assertGreater(a[0]['validation']['full_text_characters'],1000)
 def test_mutated_text_provisions_or_legal_stage_are_rejected(self):
  for field,value in [('full_text','Invented text'),('chemical_provisions',[]),('policy_stage','proposed_rule')]:
   s,r=self.document();r['payload']['data']['enrichment'][field]=value
   with self.assertRaisesRegex(RawFailure,'differs_from_original'):evidence(r,s,'bucket')
 def test_missing_pdf_is_not_published_as_complete_notice(self):
  s,r=self.document();r['payload']['data']['enrichment']['official_pdf_status']='missing'
  with self.assertRaisesRegex(RawFailure,'capture_incomplete'):evidence(r,s,'bucket')
 def test_wrong_document_and_original_body_reference_are_rejected(self):
  s,r=self.document();r['payload']['data']['enrichment']['document_number']='2021-99999'
  with self.assertRaisesRegex(RawFailure,'identity_mismatch'):evidence(r,s,'bucket')
  s,r=self.document();r['payload']['source_evidence'].pop(1)
  with self.assertRaisesRegex(RawFailure,'body_reference_missing'):evidence(r,s,'bucket')
 def test_pdf_corruption_and_wrong_url_are_rejected(self):
  s,r=self.document();ref=r['payload']['data']['enrichment']['official_pdf_source'];s.files['research-data/'+ref['key']]+=b'corrupt'
  with self.assertRaisesRegex(RawFailure,'checksum_mismatch'):evidence(r,s,'bucket')
  s,r=self.document();r['payload']['data']['enrichment']['official_pdf_source']['source_url']='https://example.org/2021-26683.pdf'
  with self.assertRaises(RawFailure):evidence(r,s,'bucket')
 def test_externalized_extraction_is_revalidated_not_accepted_as_original(self):
  s,r=self.document();full=r['payload']['data']['enrichment'];ref=s.add(json.dumps(full).encode(),r['source_url'],'federal_register_extractions')
  reduced={k:v for k,v in full.items()if k not in ('full_text','paragraphs','chemical_provisions')}
  reduced.update(full_extraction_source=ref,extraction_storage='full_extraction_externalized_to_source_reference');r['payload']['data']['enrichment']=reduced
  self.assertEqual(evidence(r,s,'bucket')[0]['validation']['chemical_provisions'],45)
 def test_large_pdf_uses_bounded_reads(self):
  chunks=[b'%PDF-1.4\n']+[b'x'*(1024*1024)]*33+[b'\n%%EOF'];sha=hashlib.sha256()
  for part in chunks:sha.update(part)
  class Body:
   def __init__(self):self.parts=iter(chunks)
   def read(self,n):
    if n!=1024*1024:raise AssertionError('unbounded PDF read')
    return next(self.parts,b'')
   def close(self):pass
  class Reader:
   def get_object(self,**kw):return {'Body':Body(),'ContentLength':sum(map(len,chunks))}
  url='https://www.govinfo.gov/content/pkg/FR-2026-11-09/pdf/2026-22743.pdf';ref={'key':'source_documents/federal_register_documents/'+sha.hexdigest(),'sha256':sha.hexdigest(),'source_url':url}
  a=pdf(Reader(),'bucket',ref,'2026-22743',{'pdf_url':url});self.assertGreater(a['bytes'],32*1024*1024)
