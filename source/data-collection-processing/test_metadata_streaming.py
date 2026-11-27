import hashlib,io,json,tempfile,unittest,zipfile
from pathlib import Path
from metadata_engine.streaming import session,download,validate_file,evidence,StreamingRequired,JSONStream
from metadata_engine.evidence import RawFailure
class Body(io.BytesIO):
 def read(self,n=-1):
  if n<0 or n>1024*1024:raise AssertionError('unbounded read')
  return super().read(n)
class S3:
 def __init__(self,body,length=None):self.body=body;self.length=len(body)if length is None else length;self.calls=0
 def get_object(self,**kwargs):self.calls+=1;return {'Body':Body(self.body),'ContentLength':self.length}
class Streaming(unittest.TestCase):
 def test_source_lanes_can_run_together_but_reject_duplicate_claimers(self):
  from metadata_engine.streaming_worker import OPENDART,lane_lock,lane_sources
  self.assertEqual(lane_sources({},'opendart'),[OPENDART])
  self.assertIn(OPENDART,lane_sources({OPENDART:True},'shared'))
  self.assertNotIn(OPENDART,lane_sources({OPENDART:True},'general'))
  with tempfile.TemporaryDirectory() as tmp:
   directory=Path(tmp)
   with lane_lock(directory,'general') as general, lane_lock(directory,'opendart') as dart:
    self.assertTrue(general and dart)
    with lane_lock(directory,'general') as duplicate, lane_lock(directory,'shared') as shared:
     self.assertFalse(duplicate or shared)
   with lane_lock(directory,'shared') as shared, lane_lock(directory,'opendart') as blocked:
    self.assertTrue(shared)
    self.assertFalse(blocked)
 def test_download_requires_isolated_lane(self):
  with self.assertRaises(StreamingRequired):download(S3(b'a'),'bucket','key','sha')
 def test_chunks_hash_and_complete_csv(self):
  raw=b'id,value\n'+b'1,2\n'*300000;s=S3(raw)
  with session():
   e=download(s,'b','k',hashlib.sha256(raw).hexdigest());self.assertEqual(validate_file(e)['rows'],300000);self.assertIs(e,download(s,'b','k',e['sha256']));self.assertEqual(s.calls,1)
 def test_corrupt_checksum_rejected(self):
  with session(),self.assertRaisesRegex(RawFailure,'checksum'):download(S3(b'abc'),'b','k','0'*64)
 def test_truncated_object_rejected(self):
  with session(),self.assertRaisesRegex(RawFailure,'truncated'):download(S3(b'abc',4),'b','k',hashlib.sha256(b'abc').hexdigest())
 def test_csv_width_mismatch_rejected(self):
  raw=b'a,b\n1,2,3\n'
  with session(),self.assertRaisesRegex(RawFailure,'column_count'):validate_file(download(S3(raw),'b','k',hashlib.sha256(raw).hexdigest()))
 def test_zip_crc_and_dataset(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED)as z:z.writestr('data.csv','a,b\n1,2\n')
  raw=b.getvalue()
  with session():self.assertEqual(validate_file(download(S3(raw),'b','k',hashlib.sha256(raw).hexdigest()))['members'],1)
 def test_zip_traversal_rejected(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w')as z:z.writestr('../data.csv','a,b\n1,2\n')
  raw=b.getvalue()
  with session(),self.assertRaisesRegex(RawFailure,'unsafe'):validate_file(download(S3(raw),'b','k',hashlib.sha256(raw).hexdigest()))
 def test_zip_cordis_semicolon_csv(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w')as z:z.writestr('organization.csv','"projectID";"name"\n"123";"España"\n')
  raw=b.getvalue()
  with session():self.assertEqual(validate_file(download(S3(raw),'b','k',hashlib.sha256(raw).hexdigest()))['kind'],'dataset_file')
 def test_zip_hkex_native_report(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w')as z:z.writestr('rpi.lis','0 HKEX  20261013II40734202610130734U2             A  CLR\r\n'+'T CNYYHKDH0001172400\r\n'*10)
  raw=b.getvalue()
  with session():self.assertEqual(validate_file(download(S3(raw),'b','k',hashlib.sha256(raw).hexdigest()))['kind'],'dataset_file')
 def test_incremental_json_boundaries_and_unicode(self):
  class Slow(io.StringIO):
   def read(self,n=-1):return super().read(7)
  rows=[{'id':str(i),'name':'España, {café}', 'source':'official'}for i in range(8)];raw=json.dumps({'total':8,'results':rows,'complete':True},ensure_ascii=False)
  self.assertEqual(list(JSONStream(Slow(raw)).results()),rows)
 def test_json_trailing_garbage_and_truncation(self):
  for raw in ('{"results":[{}]}garbage','{"results":[{}]','{"results":[{},]}'):
   with self.assertRaises(RawFailure):list(JSONStream(io.StringIO(raw)).results())
 def test_sec_submission_streamed_with_identity(self):
  raw=b'<SEC-DOCUMENT>0000000001-26-000001\n<SEC-HEADER>\nACCESSION NUMBER: 0000000001-26-000001\nCENTRAL INDEX KEY: 0000000001\nCONFORMED SUBMISSION TYPE: 10-K\n</SEC-HEADER>\n<DOCUMENT>\n<TYPE>10-K\n<FILENAME>report.htm\n<TEXT>\n<html>Actual filing</html>\n</TEXT>\n</DOCUMENT>\n</SEC-DOCUMENT>\n'
  ref={'key':'source_documents/sec/a','sha256':hashlib.sha256(raw).hexdigest(),'source_url':'https://www.sec.gov/Archives/edgar/data/1/0000000001-26-000001.txt'}
  with session():
   self.assertEqual(evidence({'source':'disclosure_documents'},ref,{'allowed_hosts':['www.sec.gov']},S3(raw),'b','primary_document')['validation']['documents'],1)
   ref['source_url']=ref['source_url'].replace('/data/1/','/data/2/')
   with self.assertRaisesRegex(RawFailure,'identity'):evidence({'source':'disclosure_documents'},ref,{'allowed_hosts':['www.sec.gov']},S3(raw),'b','primary_document')
  broken=raw.replace(b'</DOCUMENT>',b'')
  with session(),self.assertRaisesRegex(RawFailure,'incomplete'):validate_file(download(S3(broken),'b','k',hashlib.sha256(broken).hexdigest()))
 def test_trade_entire_row_required(self):
  row={'id':'123','name':'Company','source':'SDN','programs':['X']};raw=json.dumps({'results':[row]}).encode();record={'source':'trade_screening','source_record_id':'123','payload':{'data':dict(row)}};ref={'key':'source_documents/trade/a','sha256':hashlib.sha256(raw).hexdigest(),'source_url':'https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.json'}
  with session():
   self.assertTrue(evidence(record,ref,{'allowed_hosts':['data.trade.gov']},S3(raw),'b')['validation']['streamed'])
   from research_contract import digest
   record.update(source_record_id=digest({'list':'SDN','id':'123'}),source_record_id_basis='documented_composite')
   self.assertTrue(evidence(record,ref,{'allowed_hosts':['data.trade.gov']},S3(raw),'b')['validation']['streamed'])
   record['source_record_id_basis']='provider'
   with self.assertRaisesRegex(RawFailure,'row_mismatch'):evidence(record,ref,{'allowed_hosts':['data.trade.gov']},S3(raw),'b')
   record['source_record_id_basis']='documented_composite';record['payload']['data']['programs']=[]
   with self.assertRaisesRegex(RawFailure,'row_mismatch'):evidence(record,ref,{'allowed_hosts':['data.trade.gov']},S3(raw),'b')
