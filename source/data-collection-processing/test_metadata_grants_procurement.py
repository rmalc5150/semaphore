import json,io,copy,unittest
from pathlib import Path
from metadata_engine.grants_awards import validate,ProviderError
BASE=Path('repair-notes/2026-11-11-grants-patents-procurement')
class Grants(unittest.TestCase):
 def test_original_three_feeds(self):
  for source in ('nih_reporter','usa_spending','uspto_assignment_histories'):
   r=json.loads((BASE/source/'sample-record.json').read_text());ref=r['payload']['source_evidence'][0]
   self.assertEqual(validate((BASE/source/'original-0.bin').read_bytes(),r,ref['source_url'])['source'],source)
 def test_whole_nih_record_required(self):
  source='nih_reporter';r=json.loads((BASE/source/'sample-record.json').read_text());del r['payload']['data']['principal_investigators']
  with self.assertRaises(ProviderError):validate((BASE/source/'original-0.bin').read_bytes(),r,r['payload']['source_evidence'][0]['source_url'])
 def test_assignment_chain_must_match(self):
  source='uspto_assignment_histories';r=json.loads((BASE/source/'sample-record.json').read_text());r['payload']['data']['original_chain']=[]
  with self.assertRaises(ProviderError):validate((BASE/source/'original-0.bin').read_bytes(),r,r['payload']['source_evidence'][0]['source_url'])
 def test_award_amount_cannot_change(self):
  source='usa_spending';r=json.loads((BASE/source/'sample-record.json').read_text());r['payload']['data']['Award Amount']=0
  with self.assertRaises(ProviderError):validate((BASE/source/'original-0.bin').read_bytes(),r,r['payload']['source_evidence'][0]['source_url'])
class Patents(unittest.TestCase):
 def test_bibliography_matches_original_fixed_job(self):
  from metadata_engine.patent_sources import validate_google
  p=BASE/'google_patents_bigquery';r=json.loads((p/'sample-record.json').read_text());raw=validate_google((p/'original-1.bin').read_bytes(),r,r['payload']['source_evidence'][1]['source_url']);self.assertEqual(raw['publication_number'],r['source_record_id'])
 def test_bibliography_wrong_job_rejected(self):
  from metadata_engine.patent_sources import validate_google,ProviderError
  p=BASE/'google_patents_bigquery';r=json.loads((p/'sample-record.json').read_text());url=r['payload']['source_evidence'][1]['source_url']+'wrong'
  with self.assertRaises(ProviderError):validate_google((p/'original-1.bin').read_bytes(),r,url)
 def test_office_action_matches_provider_text(self):
  from metadata_engine.patent_sources import validate_odp,ProviderError
  p=BASE/'uspto_odp';r=json.loads((p/'sample-record.json').read_text());url=r['payload']['source_evidence'][0]['url'];validate_odp((p/'original-0.bin').read_bytes(),r,url);r['payload']['data']['source_text']='altered'
  with self.assertRaises(ProviderError):validate_odp((p/'original-0.bin').read_bytes(),r,url)
class TED(unittest.TestCase):
 def test_content_chunk_matches_full_xml_and_api_record(self):
  from metadata_engine.ted_records import evidence
  p=BASE/'ted_notices';r=json.loads((p/'sample-record.json').read_text());index=json.loads((BASE/'original-index.json').read_text())['ted_notices'];bodies={'research-data/'+ref['reference']['key']:(p/('original-'+str(n)+'.bin')).read_bytes()for n,ref in enumerate(index)}
  class Reader:
   def get_object(self,**kw):return {'Body':io.BytesIO(bodies[kw['Key']])}
  artifacts=evidence(r,Reader(),'bucket');self.assertEqual([a['artifact_kind']for a in artifacts],['provider_record','primary_document']);r['payload']['data']['content_text']='altered'
  with self.assertRaises(ValueError):evidence(r,Reader(),'bucket')
class NIST(unittest.TestCase):
 def test_legacy_stub_reparses_original_but_remains_discovery(self):
  from metadata_engine.nist_methods import evidence
  p=BASE/'nist_robotics_methods';r=json.loads((p/'sample-record.json').read_text());body=(p/'original-0.bin').read_bytes()
  class Reader:
   def get_object(self,**kw):return {'Body':io.BytesIO(body)}
  a=evidence(r,Reader(),'bucket')[0];self.assertEqual(a['validation']['kind'],'discovery');self.assertGreater(len(a['validation']['parsed_document']['text']),100)

class PatentArtifactChecks(unittest.TestCase):
 def test_original_bigquery_page_becomes_verified_artifact(self):
  from metadata_engine.patent_sources import evidence
  p=BASE/'google_patents_bigquery';r=json.loads((p/'sample-record.json').read_text());refs=r['payload']['source_evidence'];bodies={'research-data/'+ref['key']:(p/('original-'+str(i)+'.bin')).read_bytes()for i,ref in enumerate(refs)}
  class Reader:
   def get_object(self,**kw):return {'Body':io.BytesIO(bodies[kw['Key']])}
  self.assertEqual(evidence(r,Reader(),'bucket')[0]['artifact_kind'],'provider_record')
 def test_original_office_action_pdf_required(self):
  from metadata_engine.patent_sources import evidence,ProviderError
  p=BASE/'uspto_odp';r=json.loads((p/'sample-record.json').read_text());index=json.loads((BASE/'original-index.json').read_text())['uspto_odp'];bodies={'research-data/'+entry['reference']['key']:(p/('original-'+str(i)+'.bin')).read_bytes()for i,entry in enumerate(index)}
  class Reader:
   def get_object(self,**kw):return {'Body':io.BytesIO(bodies[kw['Key']])}
  self.assertTrue(any(a['artifact_kind']=='primary_document'for a in evidence(r,Reader(),'bucket')))
  r['payload']['data']['documents']=[]
  with self.assertRaises(ProviderError):evidence(r,Reader(),'bucket')

class AssignmentLedger(unittest.TestCase):
 def test_normalized_ledger_preserves_provider_events(self):
  from metadata_engine.patent_sources import validate_odp,ProviderError
  p=BASE/'uspto_odp';r=json.loads((p/'sample-patent_assignment_records.json').read_text());body=(p/'assignment-original.json').read_bytes();ref=r['payload']['source_evidence'][0];url=ref.get('url')or ref.get('source_url');validate_odp(body,r,url)
  r['payload']['data']['assignment_history']['events'][0]['reel_frame']='changed'
  with self.assertRaises(ProviderError):validate_odp(body,r,url)

class ReviewedSourceIsolation(unittest.TestCase):
 def test_paused_source_is_not_claimed(self):
  from contextlib import contextmanager
  from metadata_engine.reviewed_continuation import claim
  class Cursor:
   def execute(self,*args):pass
   def fetchone(self):return {'state':'owner_paused'}
  class DB:
   @contextmanager
   def tx(self):yield Cursor()
  self.assertIsNone(claim(DB(),'nih_reporter'))
 def test_live_source_lease_is_not_stolen(self):
  from contextlib import contextmanager
  from metadata_engine.reviewed_continuation import claim
  class Cursor:
   rows=iter([{'state':'enabled'},{'job_id':'running-job'}])
   def execute(self,*args):pass
   def fetchone(self):return next(self.rows)
  class DB:
   @contextmanager
   def tx(self):yield Cursor()
  self.assertIsNone(claim(DB(),'nih_reporter'))

class DatabaseFailureReporting(unittest.TestCase):
 def test_broken_rollback_preserves_original_error_and_discards_connection(self):
  from metadata_engine.runtime_db import Database
  class Cursor:
   def __enter__(self):return self
   def __exit__(self,*args):return False
  class Connection:
   open=True
   closed=False
   def cursor(self):return Cursor()
   def rollback(self):raise RuntimeError('broken rollback')
   def close(self):self.closed=True
  db=Database({'region':'us-east-1'},session=object());db.credentials={};conn=Connection();db.local.connection=conn
  with self.assertRaisesRegex(TimeoutError,'original deadline'):
   with db.tx():raise TimeoutError('original deadline')
  self.assertTrue(conn.closed);self.assertIsNone(db.local.connection)

class LegacyCommitProof(unittest.TestCase):
 def test_missing_commit_head_remains_uncommitted(self):
  from botocore.exceptions import ClientError
  from metadata_engine.worker import load_input
  from metadata_engine.evidence import Uncommitted
  class Reader:
   def get_object(self,**kw):
    if kw['Key'].endswith('/final.json'):return {'Body':io.BytesIO(b'{"task_id":"task_missing"}')}
    raise ClientError({'Error':{'Code':'NoSuchKey'}},'GetObject')
  with self.assertRaisesRegex(Uncommitted,'checkpoint_head_missing'):load_input(Reader(),'bucket',{'input_key':'research-data/raw/source=nih_reporter/dataset=specialist_inputs/ingestion_date=2026-10-09/run_id=run_id/part.jsonl','input_format':'legacy_batch'})

class PublicationFairness(unittest.TestCase):
 def test_global_publisher_checks_only_eight_sources_and_advances_cursor(self):
  from contextlib import contextmanager
  from unittest.mock import patch
  from metadata_engine.controller import publish
  class Cursor:
   def execute(self,*args):pass
   def fetchall(self):return [{'source_key':s}for s in 'abcdefghijkl']
  class DB:
   saved=[]
   def cursor(self,*args):return {'after':'f'}
   def save_cursor(self,key,state):self.saved.append(state['after'])
   @contextmanager
   def tx(self):yield Cursor()
  db=DB()
  with patch('metadata_engine.controller.publish',return_value=0)as child:self.assertEqual(publish(db),0)
  self.assertEqual([c.kwargs['source_key']for c in child.call_args_list],list('ghijklab'))
  self.assertEqual(db.saved[-1],'b')
