import unittest,json,tempfile
from pathlib import Path
from unittest.mock import Mock,patch
from reviewed_source_gaps import reviewed_gap
from collection_storage import StorageSettings
from specialist_inputs import collect
from credential_source_apis import fetch
from additional_source_apis import get_json
from additional_source_apis import fetch as additional_fetch

class GapTests(unittest.TestCase):
 def job(self):return {'source':'biorxiv_medrxiv_preprints','adapter':'additional_biorxiv','parameters':{'repository':'medrxiv'},'start':'2016-01-01','end':'2016-02-01'}
 def test_scope_and_boundary(self):
  j=self.job();self.assertIsNotNone(reviewed_gap(j))
  for change in ({'parameters':{'repository':'biorxiv'}},{'start':'2019-06-01','end':'2019-07-01'},{'source':'other'}):self.assertIsNone(reviewed_gap({**j,**change}))
 def test_gap_saved_without_network_or_false_completion(self):
  with tempfile.TemporaryDirectory() as root,patch('specialist_inputs.SpecialistClient') as client:
   s=StorageSettings(local_root=root);store=s.store();r=collect(self.job(),store,s,{}, {},1)
   self.assertEqual(r['status'],'accepted_unavailable');client.assert_not_called();self.assertIsNotNone(store.get(r['gap_receipt']));self.assertNotIn('manifest',r)
 def test_204_is_opt_in_and_evidenced(self):
  response=Mock(status_code=204,headers={},links={});response.iter_content.return_value=[];response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
  with patch('additional_source_apis.requests.get',return_value=response),patch('constellation.shared_limits.admit'):
   client=Mock();self.assertEqual(get_json(client,'https://api.wto.org/timeseries/v1/data',allow_empty=True),(None,None));client.save.assert_called_once()
   with self.assertRaises(Exception):get_json(client,'https://api.wto.org/timeseries/v1/data')
 def test_wto_empty_not_allowed_mid_pagination(self):
  j={'adapter':'additional_wto_timeseries','start':'2016-01-01','end':'2017-01-01','parameters':{'url':'https://api.wto.org/timeseries/v1/data','indicator':'X','year':2016}}
  with patch('credential_source_apis.get_json',return_value=(None,None)):
   c=Mock();self.assertEqual(fetch(c,j,None,Mock()),([],None));self.assertEqual(c.expected_records,0)
   with self.assertRaises(Exception):fetch(c,j,json.dumps({'offset':500}),Mock())

 def test_biorxiv_emits_version_matched_pdf_evidence(self):
  job={'adapter':'additional_biorxiv','start':'2020-01-01','end':'2020-02-01','parameters':{'repository':'biorxiv','full_text_per_page':1}}
  listing={'messages':[{'status':'ok','total':'2'}],'collection':[{'doi':'10.1101/2020.01.02.123456','version':'3','date':'2020-01-02'},{'doi':'10.1101/2020.01.03.123456','version':'1','date':'2020-01-03'}]}
  client=Mock();client.evidence=[]
  def pdf(url):
   client.evidence.append({'key':'source_documents/biorxiv/pdf','sha256':'a'*64,'source_url':url,'retrieved_at':'2026-10-30T00:00:00Z'})
   return b'%PDF-1.4\nbody\n%%EOF'
  client.get.side_effect=pdf
  with patch('additional_source_apis.get_json',return_value=(listing,None)):
   rows,cursor=additional_fetch(client,job,None,lambda *args,**kwargs:{'id':args[0],'data':args[1],'url':args[2],'date':args[3]})
  self.assertEqual(len(rows),1);self.assertIn('10.1101/2020.01.02.123456v3.full.pdf',rows[0]['url'])
  self.assertEqual(rows[0]['source_evidence'][0]['source_url'],rows[0]['url'])
  self.assertEqual(json.loads(cursor)['offset'],1)

 def test_monitor_suppresses_only_prelaunch_repository(self):
  from test_public_collection_operations import FakeControl
  from constellation.gaps import build
  j=self.job();row={'job':j,'source':j['source'],'source_id':'C145','start':j['start'],'end_exclusive':j['end'],'status':'failed','reason':'biorxiv_provider_error'}
  other={**row,'job':{**j,'parameters':{'repository':'biorxiv'}}}
  r=build(FakeControl([{'outcomes':[row,other]}]))
  self.assertEqual(r['flagged_gaps'],1);self.assertEqual(len(r['accepted_unavailable']),1)
