import unittest,json,hashlib,io
from unittest.mock import patch
from metadata_engine.personnel_archive import evidence
from metadata_engine.evidence import RawFailure
class Archive(unittest.TestCase):
 def setUp(self):
  self.parent={'source':'people_rss','dataset':'people_source_records','record_id':'rec_parent','observation_id':'obs_parent','source_url':'https://publisher.example/article','payload':{}};self.key='raw/source=people_rss/dataset=people_source_records/part.jsonl';self.raw=json.dumps(self.parent).encode()+b'\n';self.manifest='manifests/collection_runs/source=people_rss/dataset=people_source_records/run_parent/final.json';m={'status':'complete','exhausted':True,'task_id':'task_parent','pages':[{'batches':[{'key':self.key,'sha256':hashlib.sha256(self.raw).hexdigest()}]}]};self.mbody=json.dumps(m).encode();self.archive={'source_record_id':'obs_parent','source_url':self.parent['source_url'],'run_id':'run_archive','payload':{'data':self.parent,'parent_observation_id':'obs_parent','parent_record_id':'rec_parent','parent_manifest':self.manifest,'parent_batch_keys':[self.key]}}
  self.objects={'research-data/'+self.key:self.raw,'research-data/'+self.manifest:self.mbody,'research-data/checkpoints/task_parent/head.json':json.dumps({'terminal_history':[self.manifest]}).encode(),'research-data/manifests/collection_runs/source=personnel_archive/dataset=people_source_records/run_archive/final.json':json.dumps({'task':{'scope':{'parent_manifest':self.manifest,'parent_manifest_sha256':hashlib.sha256(self.mbody).hexdigest()}}}).encode()}
  outer=self
  class S3:
   def get_object(self,**kw):
    raw=outer.objects[kw['Key']];return {'Body':io.BytesIO(raw),'ContentLength':len(raw)}
  self.s3=S3()
 def test_committed_identity_delegates_original_body_validation(self):
  with patch('metadata_engine.people_rss.evidence',return_value=[{'artifact_kind':'full_text','sha256':'sha','s3_uri':'s3://bucket/text','origin':'first_party_source'}]):
   result=evidence(self.archive,self.s3,'bucket')
  self.assertEqual({a['artifact_kind']for a in result},{'parent_record','full_text','source_content'})
 def test_parent_identity_cannot_be_substituted(self):
  self.archive['payload']['parent_observation_id']='wrong'
  with self.assertRaisesRegex(RawFailure,'observation_mismatch'):evidence(self.archive,self.s3,'bucket')
 def test_uncommitted_parent_rejected(self):
  self.objects['research-data/checkpoints/task_parent/head.json']=b'{"terminal_history":[]}'
  with self.assertRaisesRegex(RawFailure,'not_committed'):evidence(self.archive,self.s3,'bucket')
 def test_missing_upstream_body_remains_a_gap(self):
  with patch('metadata_engine.people_rss.evidence',side_effect=RawFailure('rss_article_fulltext_missing')):
   with self.assertRaises(RawFailure):evidence(self.archive,self.s3,'bucket')
