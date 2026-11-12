import io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import Mock,patch
from disclosure_content import extract,issuer_removed_notice
from regulatory_collection import SourceIssue
from collection_storage import LocalStore,write_json
from specialist_inputs import nih_refresh_required
from research_contract import digest

class Tests(unittest.TestCase):
 def test_docx_text_and_table_paragraphs(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   z.writestr('[Content_Types].xml','<Types/>')
   z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Company announcement and important financial disclosure.</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Revenue USD 123 million</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
  r=extract(b.getvalue(),{'source':'hkex_news'})
  self.assertIn('Revenue USD 123 million',r['text']);self.assertEqual(r['extraction']['format'],'docx')
 def test_removed_notice_not_classification_text(self):
  raw=b'<html>The document that you are looking for has been removed by the listed issuer and is no longer available.</html>'
  parent={'source':'hkex_news','source_url':'https://www1.hkexnews.hk/listedco/listconews/sehk/dod/en.html'}
  r=extract(raw,parent);self.assertEqual(r['text'],'');self.assertFalse(r['documents'][0]['classification_eligible']);self.assertIn('removed',r['documents'][0]['text'])
  self.assertFalse(issuer_removed_notice(raw,{**parent,'source_url':'https://other.test/x.pdf'}))
  self.assertFalse(issuer_removed_notice(b'<html>Access denied</html>',parent))
 def test_caiso_error_is_valid_code_with_diagnostics(self):
  from caiso_enrichment import collect_rows
  c=Mock();c.get.return_value=b'bad';c.evidence=[]
  with patch('caiso_enrichment.parse_archive',side_effect=ValueError('CAISO report error: 1000; No data returned')):
   with self.assertRaises(SourceIssue) as e:collect_rows(c,{'parameters':{'url':'u','query':{}}},Mock())
  self.assertEqual(e.exception.code,'caiso_no_data_returned');self.assertIn('1000',e.exception.diagnostics['parser_message'])
 def test_nih_only_drift_refreshes(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=LocalStore(tmp);spec={'test':1};key='checkpoints/task_'+digest(spec)+'/head.json'
   write_json(store,key,{'terminal_manifest':'manifest.json'})
   write_json(store,'manifest.json',{'status':'failed','reason_code':'nih_split_count_changed'})
   self.assertTrue(nih_refresh_required(store,spec,{'adapter':'nih'}))
   self.assertFalse(nih_refresh_required(store,spec,{'adapter':'other'}))
 def test_paused_monitor_does_not_probe_service(self):
  from collection_health_exporter import inspect_job
  with patch('collection_health_exporter.properties',side_effect=AssertionError('Should not inspect')):
   self.assertTrue(inspect_job('optima-reddit-collection.service',{},None,0,0)['operator_paused'])

 def test_clinicaltrials_invalidated_token_is_refreshable_only_on_matching_error(self):
  from urllib.error import HTTPError
  from regulatory_collection import EvidenceClient
  with tempfile.TemporaryDirectory() as tmp:
   client=EvidenceClient(LocalStore(tmp),'clinicaltrials_gov',opener=Mock(side_effect=HTTPError('u',400,'bad',{},io.BytesIO(b'The data have probably changed while you were paginating. Please, start over from the first page.'))),sleeper=lambda x:None)
   with self.assertRaises(SourceIssue) as e:client.get('https://clinicaltrials.gov/api/v2/studies',params={'pageToken':'old'})
   self.assertEqual(e.exception.code,'source_changed_during_pagination')
   self.assertEqual(len(client.evidence),1)

 def test_caiso_retention_does_not_round_to_expired_month_start(self):
  from specialist_plan import jobs
  from datetime import date
  plan={'historical_start':'2021-01-01','backfill_end_exclusive':'2026-10-23','sources':[{'source_id':'S57','source':'caiso_prices','adapter':'caiso','enabled':True,'historical':True,'api':'u','nodes':['N']}]}
  scopes=list(jobs(plan,{'companies':[]},'historical',date(2026,10,23)))
  self.assertEqual(scopes[0]['start'],'2023-07-23')

 def test_monitor_requires_same_scope_and_verified_progress_to_supersede_error(self):
  from collection_health_exporter import reconcile_repaired_outcomes
  key='manifests/collection_runs/old';new='manifests/collection_runs/new'
  old={'task_id':'task_x','task':{'scope':'x'},'finished_at':'2026-10-22T01:00:00Z'}
  head={'task':old['task'],'terminal_manifest':new,'terminal_history':[key,new]}
  current={**old,'status':'partial','reason_code':'page_limit','finished_at':'2026-10-23T01:00:00Z'}
  docs={key:old,'checkpoints/task_x/head.json':head,new:current}
  e=Mock();e.read.side_effect=lambda k:(docs[k],None,None)
  e.checkpoint_commits.return_value=([('receipt','2026-10-23T00:59:00Z')],True)
  v={'manifest':key,'status':'failed','reason':'disclosure_unsupported_zip'}
  r,c=reconcile_repaired_outcomes(v,e);self.assertEqual(r['reason'],'page_limit');self.assertTrue(c)
  e.checkpoint_commits.return_value=([],True)
  self.assertEqual(reconcile_repaired_outcomes(v,e)[0],v)
  head['task']={'scope':'different'}
  self.assertEqual(reconcile_repaired_outcomes(v,e)[0],v)
