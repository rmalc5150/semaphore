import copy,hashlib,io,unittest
from unittest.mock import patch
from metadata_engine.pmda import evidence
from metadata_engine.evidence import RawFailure
class PMDA(unittest.TestCase):
 def setUp(self):
  self.url='https://www.pmda.go.jp/files/000235895.pdf';self.raw=b'%PDF-1.4\nfixture\n%%EOF';self.row={'designationDate':'2015-10-27','designationDateNative':'H27.10.27','listNumber':'1','recordText':'Product applicant holder source row','applicantName':'Applicant','marketingAuthorisationHolder':'Holder'};self.r={'source_record_id':'sakigake:2015-10-27:1','source_url':self.url,'payload':{'data':copy.deepcopy(self.row),'source_evidence':[{'key':'source_documents/japan_pmda/pdf','sha256':hashlib.sha256(self.raw).hexdigest(),'source_url':self.url}]}}
 def check(self,r=None,body=None):
  raw=self.raw if body is None else body
  class Store:
   def get_object(self,**kwargs):return {'Body':io.BytesIO(raw),'ContentLength':len(raw)}
  with patch('metadata_engine.pmda.parsed_pdf',return_value=[self.row]):return evidence(r or self.r,Store(),'bucket')
 def test_exact_identity_and_roles(self):
  self.assertTrue(self.check()[0]['validation']['original_pdf_and_row']);r=copy.deepcopy(self.r);r['payload']['data']['marketingAuthorisationHolder']='Applicant'
  with self.assertRaises(RawFailure):self.check(r)
 def test_legacy_text_is_not_promoted_to_roles(self):
  r=copy.deepcopy(self.r);r['payload']['data']={k:self.row[k]for k in ('designationDate','designationDateNative','listNumber','recordText')};self.check(r);r['payload']['data']['recordText']='wrong text'
  with self.assertRaises(RawFailure):self.check(r)
 def test_identity_origin_and_missing_pdf(self):
  for field,value in [('source_record_id','sakigake:2015-10-27:2'),('source_url','https://evil.example/files/000235895.pdf')]:
   r=copy.deepcopy(self.r);r[field]=value
   with self.assertRaises(RawFailure):self.check(r)
  r=copy.deepcopy(self.r);r['payload']['source_evidence']=[]
  with self.assertRaises(RawFailure):self.check(r)
  with self.assertRaises(RawFailure):self.check(body=b'corrupt')
if __name__=='__main__':unittest.main()
