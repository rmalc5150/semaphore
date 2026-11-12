import unittest,json,io,hashlib,copy
from metadata_engine.mhra import evidence
from metadata_engine.evidence import RawFailure
from research_contract import digest
class MHRA(unittest.TestCase):
 def setUp(self):
  self.body=b'Product name,Designation number,Active substance\nExample,PLGB 12345/0001/OD1,substance\n';self.url='https://assets.publishing.service.gov.uk/media/test/Orphan_Register.csv';self.row={'Product name':'Example','Designation number':'PLGB 12345/0001/OD1','Active substance':'substance'};self.record={'source_record_id':'orphan:'+digest(['plgb 12345/0001/od1','example']),'source_url':self.url,'payload':{'data':{'category':'orphan','registerStatus':'current_orphan_register','record':copy.deepcopy(self.row)},'source_evidence':[{'key':'source_documents/uk_mhra/sample','source_url':self.url,'sha256':hashlib.sha256(self.body).hexdigest()}]}}
 def check(self,record=None,body=None):
  data=self.body if body is None else body
  class Store:
   def get_object(self,**kw):return {'Body':io.BytesIO(data),'ContentLength':len(data)}
  return evidence(record or self.record,Store(),'bucket')
 def test_original_row_and_cp1252(self):self.assertTrue(self.check()[0]['validation']['matching_original_row'])
 def test_reject_modified_row_identity_and_receipt(self):
  r=copy.deepcopy(self.record);r['payload']['data']['record']['Active substance']='Wrong'
  with self.assertRaises(RawFailure):self.check(r)
  r=copy.deepcopy(self.record);r['source_record_id']='orphan:other'
  with self.assertRaises(RawFailure):self.check(r)
  r=copy.deepcopy(self.record);r['payload']['source_evidence']=[]
  with self.assertRaises(RawFailure):self.check(r)
 def test_expired_status_is_not_current(self):
  r=copy.deepcopy(self.record);r['source_url']=self.url.replace('Orphan','Expired_Orphan');r['payload']['source_evidence'][0]['source_url']=r['source_url']
  with self.assertRaises(RawFailure):self.check(r)
  r['payload']['data']['registerStatus']='expired_or_removed_orphan_register';r['source_record_id']=r['source_record_id'].replace('orphan:','orphan_expired:');self.check(r)
 def test_discovery_and_corrupt_bytes(self):
  r=copy.deepcopy(self.record);r['source_url']='https://www.gov.uk/discovery'
  with self.assertRaises(RawFailure):self.check(r)
  with self.assertRaises(RawFailure):self.check(body=b'corrupt')
 def test_product_requires_original_catalogue_and_pdf(self):
  from pypdf import PdfWriter
  writer=PdfWriter();writer.add_blank_page(width=100,height=100);buffer=io.BytesIO();writer.write(buffer);pdf=buffer.getvalue();url='https://mhraproducts4853.blob.core.windows.net/docs/abc';doc={'metadata_storage_path':url,'doc_type':'Spc','pl_number':['PL123450001']};catalogue=json.dumps({'value':[doc]}).encode();bodies={'research-data/catalogue':catalogue,'research-data/pdf':pdf}
  class Store:
   def get_object(self,**kw):return {'Body':io.BytesIO(bodies[kw['Key']]),'ContentLength':len(bodies[kw['Key']])}
  refs=[{'key':'catalogue','sha256':hashlib.sha256(catalogue).hexdigest(),'source_url':'https://mhraproducts4853.search.windows.net/indexes/products-index/docs'}, {'key':'pdf','sha256':hashlib.sha256(pdf).hexdigest(),'source_url':url}]
  record={'source_url':url,'source_record_id':'product_document:'+hashlib.sha256(url.encode()).hexdigest(),'payload':{'data':{'category':'medicine_document','catalogue_record':doc,'document_sha256':hashlib.sha256(pdf).hexdigest(),'text':''},'source_evidence':refs}}
  self.assertEqual({a['artifact_kind']for a in evidence(record,Store(),'bucket')},{'provider_record','primary_document'})
  record['payload']['source_evidence']=refs[:1]
  with self.assertRaises(RawFailure):evidence(record,Store(),'bucket')
 def test_legacy_expired_identity_retains_source_provenance(self):
  r=copy.deepcopy(self.record);r['source_url']=self.url.replace('Orphan','Expired_Orphan');r['payload']['source_evidence'][0]['source_url']=r['source_url'];r['payload']['data'].pop('registerStatus');out=self.check(r)
  self.assertEqual(out[0]['validation']['register'],'expired_or_removed_orphan_register')

 def test_bad_product_document_does_not_stop_next_capture(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  from pypdf import PdfWriter
  from collection_storage import StorageSettings
  from research_contract import ROOT,load_json
  import mhra_products_worker as worker
  writer=PdfWriter();writer.add_blank_page(width=100,height=100);buffer=io.BytesIO();writer.write(buffer);pdf=buffer.getvalue();url='https://mhraproducts4853.blob.core.windows.net/docs/good'
  entries=[{'metadata_storage_path':'https://untrusted.example/bad'}, {'metadata_storage_path':url,'metadata_storage_name':'good','product_name':'Example','doc_type':'Spc'}]
  response={'@odata.count':2,'value':entries};body=json.dumps(response).encode()
  class Client:
   def __init__(self,*args):self.evidence=[]
   def json(self,url,params,**kwargs):
    assert params['search']=='*'and '$filter'not in params
    self.evidence.append({'key':'source_documents/uk_mhra/index','sha256':hashlib.sha256(body).hexdigest(),'source_url':url});return response
   def get(self,url):
    self.evidence.append({'key':'source_documents/uk_mhra/pdf','sha256':hashlib.sha256(pdf).hexdigest(),'source_url':url});return pdf
  universe=load_json(ROOT/'examples/sec-filings/universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
  with tempfile.TemporaryDirectory()as tmp:
   cfg=StorageSettings(local_root=tmp+'/store')
   with open(Path(tmp)/'lock','a')as lock,patch.object(worker,'open',return_value=lock,create=True),patch.object(worker.StorageSettings,'load',return_value=cfg),patch.object(worker,'load_json',side_effect=lambda p:taxonomy if p.name=='sectors.v1.json'else universe),patch.object(worker,'EvidenceClient',Client),patch.object(worker,'public_search_key',return_value='test-key'),patch.object(worker.signal,'signal'),patch.object(worker.signal,'alarm'):
    worker.main()
   state=json.loads(cfg.store().get(worker.PREFIX+'/state.json').body)
   self.assertEqual(state['failed'],1);self.assertEqual(state['captured'],1)
   self.assertEqual([x['status']for x in state['last_outcomes']],['gap','complete'])

if __name__=='__main__':unittest.main()
