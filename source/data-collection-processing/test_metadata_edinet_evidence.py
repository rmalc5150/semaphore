import hashlib,io,unittest
from metadata_engine.evidence import evidence_for,RawFailure
class EdinetEvidence(unittest.TestCase):
 def test_derived_large_extraction_is_not_loaded_as_provider_evidence(self):
  pdf=b'%PDF-1.4\nOriginal filing\n%%EOF';sha=hashlib.sha256(pdf).hexdigest();calls=[]
  class S3:
   def get_object(self,**kw):
    calls.append(kw['Key'])
    if 'extracted/' in kw['Key']:raise AssertionError('derived extraction must not be downloaded')
    return {'Body':io.BytesIO(pdf),'ContentLength':len(pdf)}
  record={'source':'edinet_filings','source_url':'https://api.edinet-fsa.go.jp/api/v2/documents/S100TEST','payload':{'source_evidence':[
   {'key':'source_documents/edinet_filings_extracted/large','sha256':'abc'},
   {'key':'source_documents/edinet_filings/'+sha,'sha256':sha}]}}
  contract={'adapter':'filings_xbrl','allowed_hosts':['api.edinet-fsa.go.jp'],'raw_requirements':{'required_artifact_kinds':['provider_record','primary_document']}}
  artifacts=evidence_for(record,contract,S3(),'bucket');self.assertEqual(len(artifacts),1);self.assertEqual(artifacts[0]['artifact_kind'],'primary_document');self.assertEqual(len(calls),1)
  record['payload']['source_evidence']=record['payload']['source_evidence'][:1]
  with self.assertRaisesRegex(RawFailure,'missing_verified_raw_artifacts'):evidence_for(record,contract,S3(),'bucket')
